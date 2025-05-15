from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

def llm_extract(extract_object: BaseModel, prompt: str, llm: BaseChatModel) -> dict:
  llm_with_tools = llm.bind_tools([extract_object], tool_choice="any")
  response = llm_with_tools.invoke(prompt)
  return response.tool_calls[0]["args"]