from typing import List, Callable, Awaitable, Optional
import json
from LLM.AgentTool import AgentTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, AIMessage
from Models import DataWindow


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
    ):
        # Instance variables
        self.messages = messages
        self.context = context
        self.on_tool_call = on_tool_call
        self.on_tool_response = on_tool_response

        # Prompt Arguments
        if context.get("prompt_args") and context["prompt_args"]:
            for key in context["prompt_args"].keys():
                context["prompt_args"][key] = context["prompt_args"][key].replace(
                    "{", "{{").replace("}", "}}")
            prompt = prompt.format(**context["prompt_args"])
        else:
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

        # placeholder vars for tool calls if any
        tool_calls = {}
        currently_collecting_tool_id = ""

        # Start the async stream!
        response_generator = self.prompt_chain.astream({"messages": self.messages})
        print(f"Created response generator")

        # Iterate through stream chunks with async for
        async for chunk in response_generator:
            print(f"Received chunk")

            # 1.) Content -  means its a response for the human!
            if chunk.content:

                # Create an async generator for the response
                async def async_response_generator():
                    # Initialize ai message
                    ai_message = ''

                    # Add and send first chunk
                    ai_message += chunk.content
                    yield chunk.content

                    # Then for each other chunk, add and send
                    async for res_chunk in response_generator:
                        ai_message += res_chunk.content
                        yield res_chunk.content

                    # Add message after streaming is complete
                    self.messages.append(AIMessage(content=ai_message))

                # Return the async generator
                return async_response_generator()

            # 2.) Tool call chunks - means we're going to receive tool chunks
            elif chunk.tool_call_chunks:

                # All tool chunks have always been in first index...
                tool_chunk = chunk.tool_call_chunks[0]

                # 2.a) Tool Chunk ID - First chunk contains tool name and ID, arg chunks will follow.
                if tool_chunk['id']:
                    currently_collecting_tool_id = tool_chunk['id']
                    tool_calls[currently_collecting_tool_id] = {
                        "name": tool_chunk['name'],
                        "args": ''
                    }

                # 2.b) Tool Args - else we know chunk will have args to append
                else:
                    tool_calls[currently_collecting_tool_id]['args'] += tool_chunk['args']

        # 3.) Tool Section - We didn't return the content stream in section 1. This means we have tools to call

        # 3.a) Add tool call message to messages
        self.messages.append(AIMessage(
            content='',
            additional_kwargs={
                'tool_calls': [
                    {
                        'id': tool_call_id,
                        'function': {
                            'name': tool_call['name'],
                            'arguments': tool_call['args']
                        }
                    } for tool_call_id, tool_call in tool_calls.items()
                ]
            }
        ))

        # 3.b) Loop through tool calls
        for tool_call_id, tool_call in tool_calls.items():
            try:
                # Args
                tool_call['args'] = json.loads(tool_call['args'])

                # Get the tool
                tool = self.name_to_tool[tool_call["name"]]

                # Notify callback if provided
                if self.on_tool_call:
                    await self.on_tool_call(
                        id=tool_call_id,
                        tool_name=tool_call['name'],
                        tool_input=tool_call['args']
                    )

                # Build params starting with tool call args
                params = {**tool_call['args']}
                
                # Add tool_call_id for async tools
                if tool.is_async:
                    params['tool_call_id'] = tool_call_id
                
                # Add context if tool needs it
                if tool.pass_context:
                    params['context'] = self.context
                
                # Call the tool
                tool_response = await tool.function(**params)

                # Notify callback if provided
                if self.on_tool_response:
                    await self.on_tool_response(
                        id=tool_call_id,
                        tool_name=tool_call['name'],
                        tool_output=tool_response
                    )

                # Create the tool message
                tool_message = ToolMessage(
                    tool_call_id=tool_call_id,
                    content=tool_response
                )

            except Exception as e:
                # Error - Create tool message with error
                tool_message = ToolMessage(
                    tool_call_id=tool_call_id,
                    content=f"Issue calling tool: {tool_call['name']}, error: {e}"
                )

            # Add tool message
            self.messages.append(tool_message)

        # 3.c) With the AI and Tool Messages added, invoke again, recursively
        return await self.invoke(load_data_windows=False)

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
        Refresh all DataWindow tool messages with fresh data from the database.
        Scans through messages to find open_data_window tool calls and updates their corresponding ToolMessages.
        """
        
        # Build a mapping of tool_call_id -> (message_index, data_window_id)
        datawindow_mapping = {}
        
        for i, message in enumerate(self.messages):
            # Check if this is an AI message with tool calls
            if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.get("name") == "open_data_window":
                        tool_call_id = tool_call.get("id")
                        data_window_id = tool_call.get("args", {}).get("data_window_id")
                        
                        if tool_call_id and data_window_id:
                            # Find the corresponding ToolMessage
                            for j in range(i + 1, len(self.messages)):
                                if isinstance(self.messages[j], ToolMessage) and self.messages[j].tool_call_id == tool_call_id:
                                    datawindow_mapping[tool_call_id] = (j, data_window_id)
                                    break
        
        # Fetch and update DataWindows
        for tool_call_id, (msg_index, data_window_id) in datawindow_mapping.items():
            try:
                data_window = DataWindow.get_data_window(data_window_id)
                self.messages[msg_index].content = data_window.data
            except Exception as e:
                self.messages[msg_index].content = f"Error refreshing DataWindow: {e}"
