import asyncio
import uuid
from lib.Connection import Connection
from stores.connections import CONNECTIONS
from AWS import Cognito
from Models import User, Context, Agent, Tool, APIKey
from LLM.TokenStreamingAgentChat import TokenStreamingAgentChat
from LLM.CreateLLM import create_llm
from LLM.BaseMessagesConverter import base_messages_to_dict_messages, dict_messages_to_base_messages


async def connect_to_context(connection_id: str, context_id: str, access_token: str = None):

    # Get the connection - used later
    connection = CONNECTIONS[connection_id]

    # Set the user if access_token is provided
    user = None
    if access_token:
        # Try API key authentication first
        if APIKey.validate_api_key(access_token):
            contents = APIKey.get_api_key_contents(access_token)
            user = User.get_user(contents["user_id"])
        else:
            # Fall back to Cognito authentication
            cognito_user = Cognito.get_user_from_cognito(access_token)
            user = User.get_user(cognito_user.sub)
        

    # Get the context id
    if (context_id == None):
        raise Exception("No context_id provided")

    # Get the context and agent
    context = None
    agent = None
    if (user):
        # Private
        context = Context.get_context_for_user(context_id, user.user_id)
        agent = Agent.get_agent_for_user(context.agent_id, user)
    else:
        # Public
        context = Context.get_public_context(context_id)
        agent = Agent.get_public_agent(context.agent_id)

    # Context dict - passed to agent for events
    context_dict = context.model_dump()

    # Tool call listener - tool call notification used in agent
    async def on_tool_call(id, tool_name, tool_input):
        print(f"Tool call: {id} {tool_name} {tool_input}")
        await connection.peer.call(
            method="on_tool_call",
            params={
                "tool_call_id": id,
                "tool_name": tool_name,
                "tool_input": tool_input,
            }
        )

    # Tool response listener - tool response notification used in agent
    async def on_tool_response(id, tool_name, tool_output):
        print(f"Tool response: {id} {tool_name} {tool_output}")
        await connection.peer.call(
            method="on_tool_response",
            params={
                "tool_call_id": id,
                "tool_name": tool_name,
                "tool_output": tool_output,
            }
        )

    # Create the agent chat stream
    agent_chat = TokenStreamingAgentChat(
        create_llm(),
        agent.prompt,
        messages=dict_messages_to_base_messages(context.messages),
        tools=[Tool.get_agent_tool_with_id(tool) for tool in agent.tools] if agent.tools else [],
        context=context_dict,
        on_tool_call=on_tool_call,
        on_tool_response=on_tool_response
    )

    # Set the connection's context and agent_chat - used later in message calls
    connection.context = context
    connection.agent_chat = agent_chat

    # Invoke the first message if agent speaks first and no previous messages
    generate_first_message = agent.agent_speaks_first and not context.messages
    if (generate_first_message):
        asyncio.create_task(send_first_message(connection))

    # Return acknowledgement
    return {
        "success": True,
        "agent_speaks_first": generate_first_message,
        "agent": agent.model_dump(),
    }

    
async def send_first_message(connection: Connection):
    # Get the agent
    agent = connection.agent_chat

    # Generate uuid for the response
    response_id = str(uuid.uuid4())

    # Stream tokens from agent invocation - now using async for
    token_stream = await agent.invoke()
    async for token in token_stream:
        await connection.peer.call(method="on_token", params={"token": token, "response_id": response_id})

    # Save the new message to context 
    connection.context.messages = base_messages_to_dict_messages(connection.agent_chat.messages)
    Context.save_context(connection.context)