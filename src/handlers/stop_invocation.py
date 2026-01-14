from lib.Connection import Connection
from stores.connections import CONNECTIONS


async def stop_invocation(connection_id: str):
    """
    Stop any currently running invocation for this connection.
    Called by the Voice Server before set_last_messages to abort ongoing generation.
    """
    # Get the connection
    connection: Connection = CONNECTIONS[connection_id]
    
    # Check that connection has agent_chat
    if connection.agent_chat is None:
        raise Exception("No agent_chat set for connection")
    
    # Call stop_invocation on the agent
    connection.agent_chat.stop_invocation()
    
    return {"success": True}

