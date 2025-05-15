import asyncio
from lib.Connection import Connection
from stores.connections import CONNECTIONS
from AWS import Cognito
from Models import User, Context, Agent, Tool
from LLM.TokenStreamingAgentChat import TokenStreamingAgentChat
from LLM.CreateLLM import create_llm
from LLM.BaseMessagesConverter import dict_messages_to_base_messages


async def connect_to_context(connection_id: str, access_token: str, context_id: str):

    # Set the user if access_token is provided
    user = None
    if access_token:
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

    # Create the agent chat stream
    agent_chat = TokenStreamingAgentChat(
        create_llm(),
        agent.prompt,
        messages=dict_messages_to_base_messages(context.messages),
        tools=[Tool.get_agent_tool_with_id(tool) for tool in agent.tools] if agent.tools else [],
        context=context_dict
    )

    # Set the connection's context and agent_chat - used later in message calls
    connection = CONNECTIONS[connection_id]
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
    }

    
async def send_first_message(connection: Connection):
    # Get the agent
    agent = connection.agent_chat

    # Stream tokens from agent invocation
    for token in agent.invoke():
        await connection.peer.call(method="on_token", params={"token": token})