from typing import List, Tuple, Callable, Any, Type
from pydantic import BaseModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage

class AgentTool(BaseModel):
  function: Callable[[Any], str]
  params: Type[BaseModel]
  pass_context: bool = False

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

  def invoke(self):
    response = self.prompt_chain.invoke({"messages": self.messages})
    self.messages.append(response)
    if len(response.tool_calls) > 0:
      for tool_call in response.tool_calls:
        try:
          tool = self.name_to_tool[tool_call["name"]]
          tool_response = tool.function(**tool_call['args'], context=self.context) if tool.pass_context else tool.function(**tool_call['args'])
          tool_message = ToolMessage(tool_call_id=tool_call['id'], content=tool_response)
        except Exception as e:
          tool_message = ToolMessage(tool_call_id=tool_call['id'], content=f"Issue calling tool: {tool_call['name']}, error: {e}")
        self.messages.append(tool_message)
      return self.invoke()
    return response.content

  def add_human_message_and_invoke(self, message: str):
    self.messages.append(HumanMessage(content=message))
    return self.invoke()