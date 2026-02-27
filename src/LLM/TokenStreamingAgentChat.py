from typing import List, Callable, Awaitable, Optional
import json
from LLM.AgentTool import AgentTool
from LLM.ContentNormalizer import normalize_content
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, AIMessage
from Models import DataWindow, JSONDocument
from Tools.MemoryTools.helper_retrive_and_cache_doc import retrieve_and_cache_doc
from AWS.APIGateway import default_type_error_handler


class TokenStreamingAgentChat:
    #####################
    #                   #
    # -- Constructor -- #
    #                   #
    #####################
    def __init__(
        self,
        llm: BaseChatModel,
        prompt: str,
        tools: List[AgentTool] = None,
        messages: List[BaseMessage] = [],
        context: dict = {},
        on_tool_call: Optional[Callable[[str, str, dict], Awaitable[None]]] = None,
        on_tool_response: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        on_response: Optional[Callable] = None,
        prompt_arg_names: List[str] = [],
    ):
        # Instance variables
        self.messages = messages
        self.context = context
        self.on_tool_call = on_tool_call
        self.on_tool_response = on_tool_response
        self.on_response = on_response

        # Replace prompt arguments using explicit prompt_arg_names
        # Simple string find-and-replace - arg names can be any format (e.g., ARG_USER_NAME or {user_name})
        for arg_name in prompt_arg_names:
            if context and context.get("prompt_args") and arg_name in context["prompt_args"]:
                prompt = prompt.replace(arg_name, str(context["prompt_args"][arg_name]))
        
        # Escape any remaining curly brackets for ChatPromptTemplate
        prompt = prompt.replace("{", "{{").replace("}", "}}")

        # Insert messages into prompt
        chat_prompt_template = ChatPromptTemplate.from_messages([
            ("system", prompt),
            (MessagesPlaceholder(variable_name="messages"))
        ])

        # Tools
        if tools:
            tool_params_list = []
            self.name_to_tool = {}
            for tool in tools:
                tool_params_list.append(tool.params)
                self.name_to_tool[tool.params.__name__] = tool
            llm = llm.bind_tools(tool_params_list)

        # The chain to invoke
        self.prompt_chain = chat_prompt_template | llm

    ################
    #              #
    # -- Invoke -- #
    #              #
    ################
    async def invoke(self, load_data_windows: bool = True):

        # Refresh data windows if enabled
        if load_data_windows:
            self._refresh_data_windows()

        accumulated_response = None

        # Start the async stream!
        response_generator = self.prompt_chain.astream({"messages": self.messages})

        # Iterate through stream chunks with async for
        async for chunk in response_generator:

            accumulated_response = chunk if accumulated_response is None else accumulated_response + chunk

            # 1.) Content - only enter the content path if there is actual text.
            #     Anthropic and reasoning models (codex) put tool_use / function_call /
            #     reasoning blocks in chunk.content as list items that are truthy but
            #     contain no user-facing text.
            if normalize_content(chunk.content):

                on_response_cb = self.on_response

                async def async_response_generator():
                    nonlocal accumulated_response
                    ai_message = ''

                    first_text = normalize_content(chunk.content)
                    ai_message += first_text
                    yield first_text

                    async for res_chunk in response_generator:
                        accumulated_response = accumulated_response + res_chunk
                        chunk_text = normalize_content(res_chunk.content)
                        if chunk_text:
                            ai_message += chunk_text
                            yield chunk_text

                    if on_response_cb:
                        on_response_cb(accumulated_response)

                    # Always save the streamed text as its own AI message
                    self.messages.append(AIMessage(
                        content=ai_message,
                        usage_metadata=accumulated_response.usage_metadata if not accumulated_response.tool_calls else None,
                        response_metadata=accumulated_response.response_metadata,
                        id=accumulated_response.id,
                    ))

                    # Some models (Anthropic) send text content followed by tool
                    # calls in the same response. Split into a separate AI message.
                    if accumulated_response.tool_calls:
                        self.messages.append(AIMessage(
                            content='',
                            tool_calls=accumulated_response.tool_calls,
                            usage_metadata=accumulated_response.usage_metadata,
                            response_metadata=accumulated_response.response_metadata,
                        ))
                        await self._process_tool_calls(accumulated_response.tool_calls)
                        recursive_gen = await self.invoke(load_data_windows=True)
                        if recursive_gen:
                            async for token in recursive_gen:
                                yield token

                return async_response_generator()

        # 2.) Tool Section - No text content was streamed.
        #     LangChain's chunk accumulation has already merged all tool_call_chunks
        #     into parsed tool_calls on the accumulated response, regardless of
        #     provider (OpenAI, Anthropic, reasoning models).

        if not accumulated_response or not accumulated_response.tool_calls:
            return None

        if self.on_response:
            self.on_response(accumulated_response)

        self.messages.append(self._chunk_to_ai_message(accumulated_response))
        await self._process_tool_calls(accumulated_response.tool_calls)
        return await self.invoke(load_data_windows=True)

    async def _process_tool_calls(self, tool_calls):
        """Execute tool calls and append ToolMessages to the conversation."""
        for tool_call in tool_calls:
            tool_call_id = tool_call['id']
            tool_call_name = tool_call['name']
            tool_call_args = tool_call['args']

            try:
                tool = self.name_to_tool[tool_call_name]

                if self.on_tool_call:
                    await self.on_tool_call(
                        id=tool_call_id,
                        tool_name=tool_call_name,
                        tool_input=tool_call_args
                    )

                params = {**tool_call_args}

                if tool.is_async:
                    params['tool_call_id'] = tool_call_id

                if tool.pass_context:
                    params['context'] = self.context

                tool_response = await tool.function(**params)

                if self.on_tool_response:
                    await self.on_tool_response(
                        id=tool_call_id,
                        tool_name=tool_call_name,
                        tool_output=tool_response
                    )

                tool_message = ToolMessage(
                    tool_call_id=tool_call_id,
                    content=tool_response
                )

            except Exception as e:
                tool_message = ToolMessage(
                    tool_call_id=tool_call_id,
                    content=f"Issue calling tool: {tool_call_name}, error: {e}"
                )

            self.messages.append(tool_message)

    @staticmethod
    def _chunk_to_ai_message(chunk) -> AIMessage:
        """Convert an accumulated AIMessageChunk to an AIMessage.

        AIMessageChunk serializes with type "AIMessageChunk" which the
        dict_to_base_messages converter doesn't recognise when the context
        is reloaded from the database. Converting to AIMessage ensures
        it persists with type "ai".
        """
        return AIMessage(
            content=chunk.content,
            additional_kwargs=chunk.additional_kwargs,
            response_metadata=chunk.response_metadata,
            tool_calls=chunk.tool_calls,
            invalid_tool_calls=chunk.invalid_tool_calls,
            usage_metadata=chunk.usage_metadata,
            id=chunk.id,
        )

    ######################################
    #                                    #
    # -- Add Human Message and Invoke -- #
    #                                    #
    ######################################
    async def add_human_message_and_invoke(self, message: str):
        self.messages.append(HumanMessage(content=message))
        return await self.invoke()


    ##############################
    #                            #
    # -- Refresh Data Windows -- #
    #                            #
    ##############################
    def _refresh_data_windows(self):
        """
        Refresh all DataWindow and MemoryWindow tool messages with the latest data.
        Scans through messages to find open_data_window and open_memory_window tool calls 
        and updates their corresponding ToolMessages.
        """
        # Build mappings of tool_call_id -> (message_index, resource_id, path)
        datawindow_mapping = {}
        memorywindow_mapping = {}
        
        for i, message in enumerate(self.messages):
            # Check if this is an AI message with tool calls
            if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.get("name")
                    tool_call_id = tool_call.get("id")
                    args = tool_call.get("args", {})
                    
                    if tool_name == "open_data_window" and tool_call_id:
                        data_window_id = args.get("data_window_id")
                        if data_window_id:
                            # Find the corresponding ToolMessage
                            for j in range(i + 1, len(self.messages)):
                                if isinstance(self.messages[j], ToolMessage) and self.messages[j].tool_call_id == tool_call_id:
                                    datawindow_mapping[tool_call_id] = (j, data_window_id)
                                    break
                    
                    elif tool_name == "open_memory_window" and tool_call_id:
                        document_id = args.get("document_id")
                        path = args.get("path", "")
                        if document_id:
                            # Find the corresponding ToolMessage
                            for j in range(i + 1, len(self.messages)):
                                if isinstance(self.messages[j], ToolMessage) and self.messages[j].tool_call_id == tool_call_id:
                                    memorywindow_mapping[tool_call_id] = (j, document_id, path)
                                    break
        
        # Fetch and update DataWindows
        for tool_call_id, (msg_index, data_window_id) in datawindow_mapping.items():
            try:
                data_window = DataWindow.get_data_window(data_window_id)
                self.messages[msg_index].content = data_window.data
            except Exception as e:
                self.messages[msg_index].content = f"Error refreshing DataWindow: {e}"
        
        # Fetch and update MemoryWindows from cached documents
        for tool_call_id, (msg_index, document_id, path) in memorywindow_mapping.items():
            try:
                # Get document (checks cache first, then fetches from DB)
                memory_document = retrieve_and_cache_doc(document_id, self.context)
                
                # Resolve path if specified
                if path:
                    try:
                        value = JSONDocument._resolve_path(memory_document.data, path.split("."))
                    except Exception:
                        self.messages[msg_index].content = f"Error: The specified memory path '{path}' is no longer available."
                        continue
                else:
                    value = memory_document.data
                
                self.messages[msg_index].content = json.dumps(value, default=default_type_error_handler, indent=2)
            except Exception as e:
                self.messages[msg_index].content = f"Error refreshing MemoryWindow: {e}"
