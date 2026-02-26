from LLM.AgentChat import AgentChat
from LLM.CreateLLM import create_llm
from LLM.BaseMessagesConverter import dict_messages_to_base_messages, base_messages_to_dict_messages
from Models import Context, Agent, Tool
from Models.TokenTracking import build_tracking_callback


def invoke_context(context: Context.Context, agent: Agent.Agent) -> Context.Context:
    agentChat: AgentChat = AgentChat(
        create_llm(context.model_id if hasattr(context, 'model_id') else None),
        agent.prompt,
        messages=dict_messages_to_base_messages(context.messages),
        tools=[Tool.get_agent_tool_with_id(tool) for tool in agent.tools] if agent.tools else [],
        context=context.model_dump(),
        prompt_arg_names=agent.prompt_arg_names if agent.prompt_arg_names else [],
        on_response=build_tracking_callback(agent.org_id),
    )
    agentChat.invoke()

    # Save the new message to context
    context.messages = base_messages_to_dict_messages(agentChat.messages)
    Context.save_context(context)

    return context