import json
from typing import List, Optional, Callable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, AIMessage, SystemMessage
from LLM.AgentTool import AgentTool
from LLM.TerminatingConfig import TerminatingConfig
from Models import DataWindow, JSONDocument
from Tools.MemoryTools.helper_retrive_and_cache_doc import retrieve_and_cache_doc
from AWS.APIGateway import default_type_error_handler

class AgentChat:
  def __init__(
      self,
      llm: BaseChatModel,
      prompt: str,
      tools: List[AgentTool] = None,
      messages: List[BaseMessage] = [],
      context: dict = None,
      prompt_arg_names: List[str] = [],
      terminating_config: Optional[TerminatingConfig] = None,
      on_response: Optional[Callable] = None,
  ):
    self.messages = messages
    self.context = context
    self.terminating_config = terminating_config
    self.on_response = on_response
    self._invocation_count = 0
    self._consecutive_nudge_count = 0
    
    # Replace prompt arguments using explicit prompt_arg_names
    # Simple string find-and-replace - arg names can be any format (e.g., ARG_USER_NAME or {user_name})
    for arg_name in prompt_arg_names:
      if context and context.get("prompt_args") and arg_name in context["prompt_args"]:
        prompt = prompt.replace(arg_name, str(context["prompt_args"][arg_name]))
    
    # Escape any remaining curly brackets for ChatPromptTemplate
    prompt = prompt.replace("{", "{{").replace("}", "}}")
    
    chat_prompt_template = ChatPromptTemplate.from_messages([
        ("system", prompt),
        (MessagesPlaceholder(variable_name="messages"))
    ])
    if tools:
      tool_params_list = []
      self.name_to_tool = {}
      self.name_to_tool_id = {}
      for tool in tools:
        tool_params_list.append(tool.params)
        tool_name = tool.params.__name__
        self.name_to_tool[tool_name] = tool
        # Map tool name to tool_id (from the tool itself)
        if tool.tool_id:
          self.name_to_tool_id[tool_name] = tool.tool_id
      llm = llm.bind_tools(tool_params_list)
    self.prompt_chain = chat_prompt_template | llm

  def invoke(self, load_data_windows: bool = True):
    # Check max invocations limit
    if self.terminating_config:
      self._invocation_count += 1
      if self._invocation_count > self.terminating_config.max_invocations:
        raise Exception(f"Max invocations exceeded: {self.terminating_config.max_invocations}")
    
    # Refresh DataWindows if enabled
    if load_data_windows:
      self._refresh_data_windows()
    
    response = self.prompt_chain.invoke({"messages": self.messages})
    self.messages.append(response)

    if self.on_response:
      self.on_response(response)
    
    if len(response.tool_calls) > 0:
      # Reset consecutive nudge count since agent is calling tools
      if self.terminating_config:
        self._consecutive_nudge_count = 0
      
      # Track called tools for terminating config cleanup
      called_tool_calls = []
      
      for tool_call in response.tool_calls:
        try:
          tool = self.name_to_tool[tool_call["name"]]
          
          # Build params starting with tool call args
          params = {**tool_call['args']}
          
          # Add tool_call_id for async tools
          if tool.is_async:
            params['tool_call_id'] = tool_call['id']
          
          # Add context if tool needs it
          if tool.pass_context:
            params['context'] = self.context
          
          # Call the tool and get response
          tool_response = tool.function(**params)
          tool_message = ToolMessage(tool_call_id=tool_call['id'], content=tool_response)
          self.messages.append(tool_message)
            
        except Exception as e:
          # General error handling (e.g., tool not found)
          tool_message = ToolMessage(tool_call_id=tool_call['id'], content=f"Issue calling tool: {tool_call['name']}, error: {e}")
          self.messages.append(tool_message)
          tool_response = tool_message.content
        
        # Check for terminating tool after execution
        if self.terminating_config:
          called_tool_calls.append(tool_call)
          
          # Look up the tool_id from the tool name
          tool_id = self.name_to_tool_id.get(tool_call["name"])
          if tool_id and tool_id in self.terminating_config.tool_ids:
            # Update AIMessage to only include called tools
            response.tool_calls = called_tool_calls
            # Return the terminating tool's response
            return tool_response
      
      # Recursively invoke after processing tool calls
      return self.invoke(load_data_windows=True)
    
    # No tool calls - content only response
    if self.terminating_config:
      # Agent returned content instead of calling terminating tool
      self._consecutive_nudge_count += 1
      
      if self._consecutive_nudge_count > self.terminating_config.consecutive_nudges:
        raise Exception(f"Max consecutive nudges exceeded: {self.terminating_config.consecutive_nudges}. Agent failed to call a terminating tool.")
      
      # Add nudge message and re-invoke
      nudge_message = SystemMessage(content=self.terminating_config.nudge_message)
      self.messages.append(nudge_message)
      return self.invoke(load_data_windows=True)
    
    return response.content
  
  def _refresh_data_windows(self):
    """
    Refresh all DataWindow and MemoryWindow tool messages with the latest data.
    Scans through messages to find open_data_window and open_memory_window tool calls 
    and updates their corresponding ToolMessages.
    """
    # Build mappings of tool_call_id -> (message_index, resource_id, path)
    datawindow_mapping = {}
    memorywindow_mapping = {}
    
    for i, message in enumerate(self.messages):
      # Check if this is an AI message with tool calls
      if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
        for tool_call in message.tool_calls:
          tool_name = tool_call.get("name")
          tool_call_id = tool_call.get("id")
          args = tool_call.get("args", {})
          
          if tool_name == "open_data_window" and tool_call_id:
            data_window_id = args.get("data_window_id")
            if data_window_id:
              # Find the corresponding ToolMessage
              for j in range(i + 1, len(self.messages)):
                if isinstance(self.messages[j], ToolMessage) and self.messages[j].tool_call_id == tool_call_id:
                  datawindow_mapping[tool_call_id] = (j, data_window_id)
                  break
          
          elif tool_name == "open_memory_window" and tool_call_id:
            document_id = args.get("document_id")
            path = args.get("path", "")
            if document_id:
              # Find the corresponding ToolMessage
              for j in range(i + 1, len(self.messages)):
                if isinstance(self.messages[j], ToolMessage) and self.messages[j].tool_call_id == tool_call_id:
                  memorywindow_mapping[tool_call_id] = (j, document_id, path)
                  break
    
    # Fetch and update DataWindows
    for tool_call_id, (msg_index, data_window_id) in datawindow_mapping.items():
      try:
        data_window = DataWindow.get_data_window(data_window_id)
        self.messages[msg_index].content = data_window.data
      except Exception as e:
        self.messages[msg_index].content = f"Error refreshing DataWindow: {e}"
    
    # Fetch and update MemoryWindows from cached documents
    for tool_call_id, (msg_index, document_id, path) in memorywindow_mapping.items():
      try:
        # Get document (checks cache first, then fetches from DB)
        memory_document = retrieve_and_cache_doc(document_id, self.context)
        
        # Resolve path if specified
        if path:
          try:
            value = JSONDocument._resolve_path(memory_document.data, path.split("."))
          except Exception:
            self.messages[msg_index].content = f"Error: The specified memory path '{path}' is no longer available."
            continue
        else:
          value = memory_document.data
        
        self.messages[msg_index].content = json.dumps(value, default=default_type_error_handler, indent=2)
      except Exception as e:
        self.messages[msg_index].content = f"Error refreshing MemoryWindow: {e}"

  def add_human_message_and_invoke(self, message: str):
    self.messages.append(HumanMessage(content=message))
    return self.invoke()