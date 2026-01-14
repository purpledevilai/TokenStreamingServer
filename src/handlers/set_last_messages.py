import uuid
from Models import Context
from LLM.BaseMessagesConverter import base_messages_to_dict_messages, dict_messages_to_base_messages
from lib.Connection import Connection
from stores.connections import CONNECTIONS
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


async def set_last_messages(connection_id: str, human_message: str, ai_message: str = None):
    """
    Modify the message history and re-invoke the agent.
    Called after stop_invocation to handle voice interruption scenarios.
    
    Scenario 1 (human_message only):
    - Find last HumanMessage and replace its content
    - Remove trailing AI messages with tool_calls lacking responses or AI messages with content
    - Save context and re-invoke
    
    Scenario 2 (ai_message + human_message):
    - Find last AIMessage with content and replace its content
    - Keep any tool_calls intact
    - Append new HumanMessage to the end
    - Save context and re-invoke
    """
    # Get the connection
    connection: Connection = CONNECTIONS[connection_id]
    
    # Check that connection has context and agent_chat
    if connection.context is None:
        raise Exception("No context set for connection")
    if connection.agent_chat is None:
        raise Exception("No agent_chat set for connection")
    
    # Get the agent
    agent = connection.agent_chat
    
    # Get current messages
    messages = agent.messages
    
    if ai_message is None:
        # Scenario 1: Human message only
        messages = _handle_human_message_only(messages, human_message)
    else:
        # Scenario 2: AI message and human message
        messages = _handle_ai_and_human_message(messages, ai_message, human_message)
    
    # Update agent messages
    agent.messages = messages
    
    # Save context with updated messages to database (before re-invoke)
    connection.context.messages = base_messages_to_dict_messages(agent.messages)
    Context.save_context(connection.context)
    
    # Re-invoke the agent and stream tokens
    token_stream = await agent.invoke()
    
    # Generate uuid for the response
    response_id = str(uuid.uuid4())
    
    # Stream tokens
    async for token in token_stream:
        await connection.peer.call(method="on_token", params={"token": token, "response_id": response_id})
    
    # Send stop token signal
    await connection.peer.call(method="on_stop_token", params={"response_id": response_id})
    
    # Save the final messages to context after streaming completes
    connection.context.messages = base_messages_to_dict_messages(agent.messages)
    Context.save_context(connection.context)
    
    # Check if there are chat events to send
    if agent.context.get("events"):
        await connection.peer.call(method="on_events", params={"events": agent.context["events"], "response_id": response_id})
        agent.context["events"] = []


def _handle_human_message_only(messages: list, human_message: str) -> list:
    """
    Scenario 1: Handle voice interruption with human message only.
    
    Logic:
    - Find last HumanMessage
    - Check for completed tool calls after it
    - If NO completed tool calls: replace HumanMessage content, remove everything after
    - If HAS completed tool calls: keep completed tools, add NEW HumanMessage with delta
    """
    # Find the index of the last HumanMessage
    last_human_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break
    
    old_human_content = human_message
    if last_human_idx is not None:
        # Get the old human message content for delta calculation
        old_human_content = messages[last_human_idx].content
    
    # Build set of tool_call_ids that have ToolMessage responses after the human message
    completed_tool_call_ids = set()
    for i in range(last_human_idx + 1, len(messages)):
        if isinstance(messages[i], ToolMessage):
            completed_tool_call_ids.add(messages[i].tool_call_id)
    
    # Case A: No completed tool calls - simple replacement
    if not completed_tool_call_ids:
        messages[last_human_idx] = HumanMessage(content=human_message)
        # Truncate everything after the HumanMessage
        return messages[:last_human_idx + 1]
    
    # Case B: Has completed tool calls - keep them and add delta message
    new_messages = messages[:last_human_idx + 1]
    
    for i in range(last_human_idx + 1, len(messages)):
        msg = messages[i]
        
        if isinstance(msg, ToolMessage):
            # Only keep ToolMessages for completed tool calls
            if msg.tool_call_id in completed_tool_call_ids:
                new_messages.append(msg)
        
        elif isinstance(msg, AIMessage):
            # Get tool_calls from this AI message
            tool_calls = msg.additional_kwargs.get('tool_calls', [])
            
            if tool_calls:
                # Filter to keep only completed tool_calls
                completed_tool_calls = [
                    tc for tc in tool_calls 
                    if tc.get('id') in completed_tool_call_ids
                ]
                
                if completed_tool_calls:
                    # Modify AI message in place to only have completed tool_calls
                    new_additional_kwargs = {**msg.additional_kwargs}
                    new_additional_kwargs['tool_calls'] = completed_tool_calls
                    
                    modified_ai_msg = AIMessage(
                        content=msg.content,  # Keep any existing content
                        additional_kwargs=new_additional_kwargs
                    )
                    new_messages.append(modified_ai_msg)
                elif msg.content:
                    # No completed tool_calls but has content - keep the content
                    new_messages.append(AIMessage(content=msg.content))
                # else: no completed tool_calls and no content - skip entirely
            
            elif msg.content:
                # AI message with content but no tool_calls - skip (this was generated content)
                continue
    
    # Calculate delta: what the user said AFTER the tool calls were made
    # human_message = old_content + new_content, so delta = human_message - old_content
    if old_human_content and human_message.startswith(old_human_content):
        delta = human_message[len(old_human_content):].lstrip()
    else:
        # Edge case: old content is empty or not a prefix - use full human_message
        delta = human_message
    
    # Add NEW HumanMessage with the delta at the end
    if delta:
        new_messages.append(HumanMessage(content=delta))
    
    return new_messages


def _handle_ai_and_human_message(messages: list, ai_message: str, human_message: str) -> list:
    """
    Scenario 2: Find last AIMessage with content and replace its content.
    Keep any tool_calls intact. Append new HumanMessage to the end.
    If no AIMessage with content exists, create a new one.
    """
    # Find the index of the last AIMessage with content
    last_ai_content_idx = None
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage) and messages[i].content:
            last_ai_content_idx = i
            break
    
    if last_ai_content_idx is None:
        # No existing AIMessage with content, create new AI and Human messages
        messages.append(AIMessage(content=ai_message))
        messages.append(HumanMessage(content=human_message))
        return messages
    
    # Modify the existing AI message content in place
    messages[last_ai_content_idx].content = ai_message
    
    # Append the new human message to the end
    messages.append(HumanMessage(content=human_message))
    
    return messages

