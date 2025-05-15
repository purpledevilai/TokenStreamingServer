from typing import List
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, AIMessage

def base_messages_to_dict_messages(messages: List[BaseMessage]) -> List[dict]:
  return [message.model_dump() for message in messages]

def dict_messages_to_base_messages(messages: List[dict]) -> List[BaseMessage]:
  base_messages = []
  for message in messages:
    if message["type"] == "human":
      base_messages.append(HumanMessage(**message))
    elif message["type"] == "ai":
      base_messages.append(AIMessage(**message))
    elif message["type"] == "tool":
      base_messages.append(ToolMessage(**message))
  return base_messages