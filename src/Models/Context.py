import os
from datetime import datetime
import uuid
from AWS.DynamoDB import get_item, put_item, get_all_items_by_index, delete_item, get_latest_items_by_index
from AWS.CloudWatchLogs import get_logger
from pydantic import BaseModel, Field
from typing import List, Optional, Union
from Models import Agent, Tool
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage, HumanMessage
from LLM.BaseMessagesConverter import base_messages_to_dict_messages
from Tools.ToolRegistry import tool_registry

logger = get_logger(log_level=os.environ["LOG_LEVEL"])

CONTEXTS_TABLE_NAME = os.environ["CONTEXTS_TABLE_NAME"]
CONTEXTS_PRIMARY_KEY = os.environ["CONTEXTS_PRIMARY_KEY"]

class Context(BaseModel):
    context_id: str
    agent_id: str
    user_id: str
    messages: list[dict]
    created_at: int
    updated_at: int
    prompt_args: Optional[dict] = None
    user_defined: Optional[dict] = None
    additional_agent_tools: Optional[list[str]] = []

class InitializeTool(BaseModel):
    tool_id: str
    tool_input: dict

class CreateContextParams(BaseModel):
    agent_id: str
    invoke_agent_message: Optional[bool] = False
    prompt_args: Optional[dict] = None
    user_defined: Optional[dict] = None
    initialize_tools: Optional[List[InitializeTool]] = None
    additional_agent_tools: Optional[List[str]] = []

class FilteredMessage(BaseModel):
    sender: str
    message: str

class ToolCallMessage(BaseModel):
    type: str
    tool_call_id: str
    tool_name: str
    tool_input: Optional[dict] = None

class ToolResponseMessage(BaseModel):
    type: str
    tool_call_id: str
    tool_output: str

MessageType = Union[FilteredMessage, ToolCallMessage, ToolResponseMessage]

class FilteredContext(BaseModel):
    context_id: str
    agent_id: str
    user_id: str
    messages: List[MessageType]
    user_defined: Optional[dict] = None
    created_at: int
    updated_at: int

class HistoryContext(BaseModel):
    context_id: str
    user_id: str
    last_message: str
    created_at: int
    updated_at: int
    agent: Agent.HistoryAgent


def context_exists(context_id: str) -> bool:
    return get_item(CONTEXTS_TABLE_NAME, CONTEXTS_PRIMARY_KEY, context_id) != None
    
def create_context(
        agent_id: str,
        user_id: Optional[str] = None,
        prompt_args: Optional[dict] = None,
        user_defined: Optional[dict] = None,
        initialize_tools: Optional[List[InitializeTool]] = None,
        additional_agent_tools: Optional[List[str]] = None
    ) -> Context:
    contextData = {
        CONTEXTS_PRIMARY_KEY: str(uuid.uuid4()),
        "agent_id": agent_id,
        "user_id": user_id if user_id is not None else "public",
        "messages": [],
        "prompt_args": prompt_args,
        "user_defined": user_defined,
        "additional_agent_tools": additional_agent_tools if additional_agent_tools else [],
        "created_at": int(datetime.timestamp(datetime.now())),
        "updated_at": int(datetime.timestamp(datetime.now())),
    }

    context = Context(**contextData)

    agent = Agent.get_agent(agent_id)
    if not agent:
        raise Exception(f"Agent with id: {agent_id} does not exist", 404)
    
    # Validate additional_agent_tools if provided
    if additional_agent_tools:
        # Get org's tools for permission validation
        org_tools = Tool.get_tools_for_org(agent.org_id)
        org_tool_ids = [tool.tool_id for tool in org_tools]
        
        # Get registered tool names
        registered_tool_names = list(tool_registry.keys())
        
        for tool_id in additional_agent_tools:
            # Validate permissions - tool must be either in agent's org tools OR in registered tools
            if tool_id not in org_tool_ids and tool_id not in registered_tool_names:
                raise Exception(f"Tool {tool_id} does not belong to organization {agent.org_id}", 403)
    
    # Build list of tools to initialize
    tools_to_initialize = []
    
    # Add agent's initialize_tool_id first (for backwards compatibility)
    if agent.initialize_tool_id:
        tool = Tool.get_agent_tool_with_id(agent.initialize_tool_id)
        if len(tool.params.model_fields) > 0:
            raise Exception("Initialization tool cannot have parameters")
        tools_to_initialize.append({
            "tool_id": agent.initialize_tool_id,
            "tool_input": {}
        })
    
    # Add user-provided initialize_tools
    if initialize_tools:
        # Get org's tools for permission validation
        org_tools = Tool.get_tools_for_org(agent.org_id)
        org_tool_ids = [tool.tool_id for tool in org_tools]
        
        # Get registered tool names
        registered_tool_names = list(tool_registry.keys())
        
        for init_tool in initialize_tools:
            # Validate permissions - tool must be either in org's tools OR in registered tools
            if init_tool.tool_id not in org_tool_ids and init_tool.tool_id not in registered_tool_names:
                raise Exception(f"Tool {init_tool.tool_id} does not belong to organization {agent.org_id}", 403)
            
            tools_to_initialize.append({
                "tool_id": init_tool.tool_id,
                "tool_input": init_tool.tool_input
            })
    
    # Execute initialization tools
    if tools_to_initialize:
        initialization_messages = []
        tool_calls_for_ai_message = []
        
        # Build all tool calls for a single AI message
        for tool_data in tools_to_initialize:
            tool = Tool.get_agent_tool_with_id(tool_data["tool_id"])
            tool_call_id = str(uuid.uuid4())
            
            tool_calls_for_ai_message.append({
                "id": tool_call_id,
                "name": tool.params.__name__,
                "args": tool_data["tool_input"]
            })
        
        # Create single AI message with all tool calls
        ai_message = AIMessage(
            content="",
            tool_calls=tool_calls_for_ai_message
        )
        initialization_messages.append(ai_message)
        
        # Execute each tool and create tool messages
        for i, tool_data in enumerate(tools_to_initialize):
            tool = Tool.get_agent_tool_with_id(tool_data["tool_id"])
            tool_call_id = tool_calls_for_ai_message[i]["id"]
            
            try:
                if tool.pass_context:
                    result = tool.function(**tool_data["tool_input"], context=context.model_dump())
                else:
                    result = tool.function(**tool_data["tool_input"])
                tool_message = ToolMessage(tool_call_id=tool_call_id, content=result)
                initialization_messages.append(tool_message)
            except Exception as e:
                logger.error(f"Error running initialization tool {tool_data['tool_id']}: {e}")
                # Fail fast - raise the exception
                raise Exception(f"Initialization tool {tool_data['tool_id']} failed: {e}")
        
        context.messages = base_messages_to_dict_messages(initialization_messages)

    put_item(CONTEXTS_TABLE_NAME, context.model_dump())
    return context


def get_context(context_id: str) -> Context:
    item = get_item(CONTEXTS_TABLE_NAME, CONTEXTS_PRIMARY_KEY, context_id)
    if item is None:
        raise Exception(f"Context with id: {context_id} does not exist", 404)
    return Context(**item)
    
def get_context_for_user(context_id: str, user_id: str) -> Context:
    context = get_context(context_id)
    if (context.user_id == "public"):
        return context
    if (context.user_id == user_id):
        return context
    raise Exception(f"Context does not belong to user", 403)

def get_public_context(context_id: str) -> Context:
    context = get_context(context_id)
    if (context.user_id == "public"):
        return context
    raise Exception(f"Context is not public", 403)

def save_context(context: Context) -> None:
    context.updated_at = int(datetime.timestamp(datetime.now()))
    put_item(CONTEXTS_TABLE_NAME, context.model_dump())

def get_contexts_by_user_id(user_id: str) -> list[Context]:
    items = get_latest_items_by_index(CONTEXTS_TABLE_NAME, "user_id-updated_at-index", "user_id", user_id, 50)
    contexts = []
    for item in items:
        try:
            contexts.append(Context(**item))
        except Exception as e:
            logger.error(f"Error parsing context: {item}")
    return contexts

def delete_context(context_id: str) -> None:
    delete_item(CONTEXTS_TABLE_NAME, CONTEXTS_PRIMARY_KEY, context_id)

def delete_all_contexts_for_user(user_id: str) -> None:
    contexts = get_contexts_by_user_id(user_id)
    for context in contexts:
        delete_context(context.context_id)

def transform_to_filtered_context(context: Context, show_tool_calls: bool = False) -> FilteredContext:
    messages = transform_messages_to_filtered(context.messages, show_tool_calls)
                
    filtered_context = FilteredContext(**{
        "context_id": context.context_id,
        "agent_id": context.agent_id,
        "user_id": context.user_id,
        "messages": messages,
        "user_defined": context.user_defined if context.user_defined else {},
        "created_at": context.created_at,
        "updated_at": context.updated_at
    })
    return filtered_context

def transform_to_history_context(context: Context, agent: Agent.Agent) -> HistoryContext:
    return HistoryContext(**{
        "context_id": context.context_id,
        "user_id": context.user_id,
        "last_message": context.messages[-1]["content"] if len(context.messages) > 0 else "",
        "created_at": context.created_at,
        "updated_at": context.updated_at,
        "agent": Agent.transform_to_history_agent(agent)
    })

def add_human_message(context: Context, message: str) -> Context:
    context.messages.extend(base_messages_to_dict_messages([HumanMessage(content=message)]))
    save_context(context)
    return context

def add_ai_message(context: Context, message: str) -> Context:
    context.messages.extend(base_messages_to_dict_messages([AIMessage(content=message)]))
    save_context(context)
    return context

def add_system_message(context: Context, message: str) -> Context:
    context.messages.extend(base_messages_to_dict_messages([SystemMessage(content=message)]))
    save_context(context)
    return context

def transform_messages_to_filtered(messages: list[dict], show_tool_calls: bool = False) -> list[MessageType]:
    """
    Transform a list of dict messages to filtered message types.
    
    Args:
        messages: List of message dictionaries
        show_tool_calls: Whether to include tool call and tool response messages
        
    Returns:
        List of FilteredMessage, ToolCallMessage, or ToolResponseMessage objects
    """
    filtered_messages = []
    for message in messages:
        if (message["type"] == "human" or (message["type"] == "ai" and message["content"]) or message["type"] == "system"):
            filtered_messages.append(FilteredMessage(**{
                "sender": message["type"],
                "message": message["content"]
            }))
            continue
        if (show_tool_calls):
            if (message["type"] == "ai" and len(message["tool_calls"]) > 0):
                for tool_call in message["tool_calls"]:
                    filtered_messages.append(ToolCallMessage(**{
                        "type": "tool_call",
                        "tool_call_id": tool_call["id"],
                        "tool_name": tool_call["name"],
                        "tool_input": tool_call["args"]
                    }))
            if (message["type"] == "tool"):
                filtered_messages.append(ToolResponseMessage(**{
                    "type": "tool_response",
                    "tool_call_id": message["tool_call_id"],
                    "tool_output": message["content"]
                }))
    return filtered_messages

def validate_messages(filtered_messages: list[MessageType]) -> None:
    """
    Validate that tool call and tool response messages are properly paired and ordered.
    
    Args:
        filtered_messages: List of FilteredMessage, ToolCallMessage, or ToolResponseMessage objects
        
    Raises:
        ValueError: If validation fails
    """
    # Track tool call IDs in the order they appear
    tool_call_ids = set()
    tool_response_ids = set()
    seen_tool_call_ids = set()
    
    for msg in filtered_messages:
        if isinstance(msg, ToolCallMessage):
            tool_call_ids.add(msg.tool_call_id)
            seen_tool_call_ids.add(msg.tool_call_id)
        elif isinstance(msg, ToolResponseMessage):
            # Check that the tool call was seen before this response
            if msg.tool_call_id not in seen_tool_call_ids:
                raise ValueError(f"Tool response with ID '{msg.tool_call_id}' appears before its corresponding tool call")
            tool_response_ids.add(msg.tool_call_id)
    
    # Check that every tool call has a corresponding tool response
    missing_responses = tool_call_ids - tool_response_ids
    if missing_responses:
        raise ValueError(f"Tool calls found without corresponding responses: {missing_responses}")
    
    # Check that every tool response has a corresponding tool call
    orphaned_responses = tool_response_ids - tool_call_ids
    if orphaned_responses:
        raise ValueError(f"Tool responses found without corresponding tool calls: {orphaned_responses}")

def filtered_messages_to_dict_messages(filtered_messages: list[MessageType]) -> list[dict]:
    """
    Transform filtered message types back to dict messages that can be saved.
    
    Args:
        filtered_messages: List of FilteredMessage, ToolCallMessage, or ToolResponseMessage objects
        
    Returns:
        List of message dictionaries compatible with Context.messages
    """
    dict_messages = []
    
    # Group tool calls that belong together
    pending_tool_calls = []
    
    for msg in filtered_messages:
        if isinstance(msg, FilteredMessage):
            # Flush any pending tool calls first
            if pending_tool_calls:
                dict_messages.append({
                    "type": "ai",
                    "content": "",
                    "tool_calls": pending_tool_calls,
                    "response_metadata": {},
                    "id": None,
                    "usage_metadata": None
                })
                pending_tool_calls = []
            
            # Add the filtered message with appropriate fields based on type
            if msg.sender == "ai":
                dict_messages.append({
                    "type": "ai",
                    "content": msg.message,
                    "tool_calls": [],
                    "response_metadata": {},
                    "id": None,
                    "usage_metadata": None
                })
            elif msg.sender == "human":
                dict_messages.append({
                    "type": "human",
                    "content": msg.message
                })
            elif msg.sender == "system":
                dict_messages.append({
                    "type": "system",
                    "content": msg.message
                })
                
        elif isinstance(msg, ToolCallMessage):
            # Accumulate tool calls
            pending_tool_calls.append({
                "id": msg.tool_call_id,
                "name": msg.tool_name,
                "args": msg.tool_input if msg.tool_input else {}
            })
            
        elif isinstance(msg, ToolResponseMessage):
            # Flush any pending tool calls first
            if pending_tool_calls:
                dict_messages.append({
                    "type": "ai",
                    "content": "",
                    "tool_calls": pending_tool_calls,
                    "response_metadata": {},
                    "id": None,
                    "usage_metadata": None
                })
                pending_tool_calls = []
            
            # Add the tool response
            dict_messages.append({
                "type": "tool",
                "content": msg.tool_output,
                "tool_call_id": msg.tool_call_id
            })
    
    # Flush any remaining tool calls
    if pending_tool_calls:
        dict_messages.append({
            "type": "ai",
            "content": "",
            "tool_calls": pending_tool_calls,
            "response_metadata": {},
            "id": None,
            "usage_metadata": None
        })
    
    return dict_messages


    

