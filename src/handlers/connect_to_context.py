import asyncio
import uuid
from lib.Connection import Connection
from stores.connections import CONNECTIONS
from AWS import Cognito
from Models import User, Context, Agent, Tool, APIKey
from Models.TokenTracking import build_tracking_callback
from LLM.TokenStreamingAgentChat import TokenStreamingAgentChat
from LLM.CreateLLM import create_llm
from LLM.BaseMessagesConverter import base_messages_to_dict_messages, dict_messages_to_base_messages


async def connect_to_context(connection_id: str, context_id: str, access_token: str = None):

    # Get the connection - used later
    connection = CONNECTIONS[connection_id]

    # Require authentication. Public contexts can no longer be connected to
    # without a token; an auto-minted client API key is issued at context
    # creation time for public-agent flows.
    if not access_token:
        raise Exception("access_token required")

    # Resolve the user and (if applicable) API key contents.
    key_contents = None
    user = None
    if APIKey.validate_api_key(access_token):
        key_contents = APIKey.get_api_key_contents(access_token)
        user = User.get_user(key_contents["user_id"])
    else:
        cognito_user = Cognito.get_user_from_cognito(access_token)
        user = User.get_user(cognito_user.sub)

    if context_id is None:
        raise Exception("No context_id provided")

    # Load the context and agent. get_agent_for_user already resolves public agents.
    context = Context.get_context(context_id)
    agent = Agent.get_agent_for_user(context.agent_id, user)

    # Authorization: if the API key is scoped to a client_id, it must match the
    # context's client_id. Otherwise fall back to the classic user_id ownership
    # check for backwards compatibility with older contexts / cognito callers.
    key_client_id = (key_contents or {}).get("client_id")
    if key_client_id:
        if context.client_id != key_client_id:
            raise Exception("API key client_id does not match context", 403)
    else:
        if context.user_id != "public" and context.user_id != user.user_id:
            raise Exception("Context does not belong to user", 403)

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

    # Combine agent tools with context additional_agent_tools (remove duplicates)
    agent_tool_ids = agent.tools if agent.tools else []
    context_tool_ids = context.additional_agent_tools if context.additional_agent_tools else []
    combined_tool_ids = list(dict.fromkeys(agent_tool_ids + context_tool_ids))  # Preserve order, remove duplicates
    
    # Get tool objects
    tools = [Tool.get_agent_tool_with_id(tool_id) for tool_id in combined_tool_ids] if combined_tool_ids else []

    # Create the agent chat stream
    agent_chat = TokenStreamingAgentChat(
        create_llm(context.model_id, for_streaming=True),
        agent.prompt,
        messages=dict_messages_to_base_messages(context.messages),
        tools=tools,
        context=context_dict,
        on_tool_call=on_tool_call,
        on_tool_response=on_tool_response,
        on_response=build_tracking_callback(agent.org_id, context.model_id),
        prompt_arg_names=agent.prompt_arg_names if agent.prompt_arg_names else []
    )

    # Set the connection's context and agent_chat - used later in message calls
    connection.context = context
    connection.agent_chat = agent_chat

    # Check if there are any AI messages with content (not just tool calls)
    has_ai_content = any(
        msg.get("type") == "ai" and msg.get("content")
        for msg in context.messages
    )

    # Invoke the first message if agent speaks first and no AI content messages exist
    generate_first_message = agent.agent_speaks_first and not has_ai_content
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
    if token_stream:
        async for token in token_stream:
            await connection.peer.call(method="on_token", params={"token": token, "response_id": response_id})

    # Send stop token signal
    await connection.peer.call(method="on_stop_token", params={"response_id": response_id})

    # Save the new message to context 
    connection.context.messages = base_messages_to_dict_messages(connection.agent_chat.messages)
    Context.save_context(connection.context)

    # Notify client of pending client-side tool calls
    if agent.pending_client_side_tool_calls:
        await connection.peer.call(
            method="on_client_side_tool_calls",
            params={
                "tool_calls": agent.pending_client_side_tool_calls,
                "response_id": response_id
            }
        )