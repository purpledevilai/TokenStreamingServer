from typing import List
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, AIMessage
from LLM.AgentTool import AgentTool

class AgentChat:
  def __init__(
      self,
      llm: BaseChatModel,
      prompt: str,
      tools: List[AgentTool] = None,
      messages: List[BaseMessage] = [],
      context: dict = None,
  ):
    self.messages = messages
    self.context = context
    if context.get("prompt_args") and context["prompt_args"]:
      for key in context["prompt_args"].keys():
        context["prompt_args"][key] = context["prompt_args"][key].replace("{", "{{").replace("}", "}}")
      prompt = prompt.format(**context["prompt_args"])
    else:
      prompt = prompt.replace("{", "{{").replace("}", "}}")
    chat_prompt_template = ChatPromptTemplate.from_messages([
        ("system", prompt),
        (MessagesPlaceholder(variable_name="messages"))
    ])
    if tools:
      tool_params_list = []
      self.name_to_tool = {}
      for tool in tools:
        tool_params_list.append(tool.params)
        self.name_to_tool[tool.params.__name__] = tool
      llm = llm.bind_tools(tool_params_list)
    self.prompt_chain = chat_prompt_template | llm

  def invoke(self, load_data_windows: bool = True):
    # Refresh DataWindows if enabled
    if load_data_windows:
      self._refresh_data_windows()
    
    response = self.prompt_chain.invoke({"messages": self.messages})
    self.messages.append(response)
    
    if len(response.tool_calls) > 0:
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
      
      # Recursively invoke after processing tool calls
      return self.invoke(load_data_windows=False)
    
    return response.content
  
  def _refresh_data_windows(self):
    """
    Refresh all DataWindow tool messages with fresh data from the database.
    Scans through messages to find open_data_window tool calls and updates their corresponding ToolMessages.
    """
    from Models import DataWindow
    
    # Build a mapping of tool_call_id -> (message_index, data_window_id)
    datawindow_mapping = {}
    
    for i, message in enumerate(self.messages):
      # Check if this is an AI message with tool calls
      if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
        for tool_call in message.tool_calls:
          if tool_call.get("name") == "open_data_window":
            tool_call_id = tool_call.get("id")
            data_window_id = tool_call.get("args", {}).get("data_window_id")
            
            if tool_call_id and data_window_id:
              # Find the corresponding ToolMessage
              for j in range(i + 1, len(self.messages)):
                if isinstance(self.messages[j], ToolMessage) and self.messages[j].tool_call_id == tool_call_id:
                  datawindow_mapping[tool_call_id] = (j, data_window_id)
                  break
    
    # Fetch and update DataWindows
    for tool_call_id, (msg_index, data_window_id) in datawindow_mapping.items():
      try:
        data_window = DataWindow.get_data_window(data_window_id)
        self.messages[msg_index].content = data_window.data
      except Exception as e:
        self.messages[msg_index].content = f"Error refreshing DataWindow: {e}"

  def add_human_message_and_invoke(self, message: str):
    self.messages.append(HumanMessage(content=message))
    return self.invoke()