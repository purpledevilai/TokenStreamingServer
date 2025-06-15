from typing import List, Callable, Awaitable, Optional
import json
from LLM.AgentTool import AgentTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, AIMessage


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
    async def invoke(self):

        # placeholder vars for tool calls if any
        tool_calls = {}
        currently_collecting_tool_id = ""

        # Start the stream!
        response_generator = self.prompt_chain.stream({"messages": self.messages})

        # Iterate through stream chunks
        for chunk in response_generator:

            # 1.) Content -  means its a response for the human!
            if chunk.content:

                # Recreate the whole generator, including first chunk
                def prepended_generator():
                    # Initialize ai message
                    ai_message = ''

                    # Add and send
                    ai_message += chunk.content
                    yield chunk.content

                    # Then for each other chunk, add and send
                    for res_chunk in response_generator:
                        ai_message += res_chunk.content
                        yield res_chunk.content

                    # Add message
                    self.messages.append(AIMessage(content=ai_message))

                # Return the generator
                return prepended_generator()

            # 2.) Tool call chunks - means we're going to recieve tool chunks
            elif chunk.tool_call_chunks:

                # All tool chunks have always been in first index...
                tool_chunk = chunk.tool_call_chunks[0]

                # 2.a) Tool Chunk ID - First chunk contians tool name and ID, arg chunks will follow.
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

        # 3.a ) Add tool call message to messages
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

                tool_response = await tool.function(
                    **tool_call['args'],
                    context=self.context # Either pass context
                ) if tool.pass_context else await tool.function(
                    **tool_call['args'] # or not
                )

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
        return await self.invoke()

    ######################################
    #                                    #
    # -- Add Human Message and Invoke -- #
    #                                    #
    ######################################
    async def add_human_message_and_invoke(self, message: str):
        self.messages.append(HumanMessage(content=message))
        return await self.invoke()
