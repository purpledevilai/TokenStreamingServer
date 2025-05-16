import uuid
from Models import Context
from LLM.BaseMessagesConverter import base_messages_to_dict_messages
from lib.Connection import Connection
from stores.connections import CONNECTIONS

async def add_message(connection_id: str, message: str):

    # Get the connection
    connection: Connection = CONNECTIONS[connection_id]
    
    # Check that connection has context and agent_chat
    if (connection.context == None):
        raise Exception("No context set for connection")
    if (connection.agent_chat == None):
        raise Exception("No agent_chat set for connection")
    
    # Get the message
    if (message == None):
        raise Exception("No message provided")
    
    # Get the agent
    agent = connection.agent_chat
    
    # Invoke the agent chat stream
    token_stream = await agent.add_human_message_and_invoke(message)

    # Generate uuid for the response
    response_id = str(uuid.uuid4())

    # Stream tokens
    for token in token_stream:
        await connection.peer.call(method="on_token", params={"token": token, "response_id": response_id})

    # Save the new message to context 
    connection.context.messages = base_messages_to_dict_messages(connection.agent_chat.messages)
    Context.save_context(connection.context)

    # Check if there are chat events to send
    if (agent.context.get("events")):
        await connection.peer.call(method="on_events", params={"events": agent.context["events"], "response_id": response_id})
        agent.context["events"] = []
    