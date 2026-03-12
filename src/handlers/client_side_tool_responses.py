import uuid
from Models import Context
from LLM.BaseMessagesConverter import base_messages_to_dict_messages, dict_messages_to_base_messages
from lib.Connection import Connection
from stores.connections import CONNECTIONS
from langchain_core.messages import AIMessage, ToolMessage


async def client_side_tool_responses(connection_id: str, tool_responses: list):
    """
    Handle client-side tool responses. The client sends back results for tool calls
    that were marked as client-side. This handler validates the responses, adds
    ToolMessages, and continues invocation.
    """
    connection: Connection = CONNECTIONS[connection_id]

    if connection.context is None:
        raise Exception("No context set for connection")
    if connection.agent_chat is None:
        raise Exception("No agent_chat set for connection")
    if not tool_responses:
        raise Exception("No tool_responses provided")

    agent = connection.agent_chat

    # Build a map from tool_call_id -> response
    response_map = {tr["tool_call_id"]: tr["response"] for tr in tool_responses}

    # Find the last AIMessage with tool_calls
    last_ai_with_tools = None
    for message in reversed(agent.messages):
        if isinstance(message, AIMessage) and message.tool_calls:
            last_ai_with_tools = message
            break

    if not last_ai_with_tools:
        raise Exception("No AIMessage with tool_calls found in context")

    # Identify which tool_calls are client-side
    client_side_tool_call_ids = set()
    for tool_call in last_ai_with_tools.tool_calls:
        tool_name = tool_call["name"]
        tool = agent.name_to_tool.get(tool_name)
        if tool and tool.is_client_side_tool:
            client_side_tool_call_ids.add(tool_call["id"])

    if not client_side_tool_call_ids:
        raise Exception("No client-side tool calls found in the last AIMessage")

    # Validate ALL client-side tool calls have a response
    missing = client_side_tool_call_ids - set(response_map.keys())
    if missing:
        raise Exception(f"Missing responses for client-side tool call IDs: {missing}")

    # Clear pending state
    agent.pending_client_side_tool_calls = None

    # Append ToolMessages for client-side tool responses
    for tool_call in last_ai_with_tools.tool_calls:
        if tool_call["id"] in client_side_tool_call_ids:
            agent.messages.append(
                ToolMessage(
                    tool_call_id=tool_call["id"],
                    content=response_map[tool_call["id"]]
                )
            )

    # Continue invocation
    token_stream = await agent.invoke()

    response_id = str(uuid.uuid4())

    # Stream tokens if there are any
    if token_stream:
        async for token in token_stream:
            await connection.peer.call(method="on_token", params={"token": token, "response_id": response_id})

    # Send stop token signal
    await connection.peer.call(method="on_stop_token", params={"response_id": response_id})

    # Save context
    connection.context.messages = base_messages_to_dict_messages(agent.messages)
    Context.save_context(connection.context)

    # Check for another round of client-side tool calls
    if agent.pending_client_side_tool_calls:
        await connection.peer.call(
            method="on_client_side_tool_calls",
            params={
                "tool_calls": agent.pending_client_side_tool_calls,
                "response_id": response_id
            }
        )

    # Check if there are chat events to send
    if agent.context.get("events"):
        await connection.peer.call(method="on_events", params={"events": agent.context["events"], "response_id": response_id})
        agent.context["events"] = []
