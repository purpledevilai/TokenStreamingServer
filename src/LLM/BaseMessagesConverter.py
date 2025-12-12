from typing import List
import json
from decimal import Decimal
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, AIMessage, SystemMessage

def decimal_to_serializable(obj):
    """Recursively convert Decimal objects to float/int for JSON serialization."""
    if isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    elif isinstance(obj, dict):
        return {key: decimal_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_serializable(item) for item in obj]
    else:
        return obj

def base_messages_to_dict_messages(messages: List[BaseMessage]) -> List[dict]:
    # Convert to dict and handle any Decimals that might be present
    dict_messages = []
    for message in messages:
        message_dict = message.model_dump()
        # Clean any Decimal objects that might be in the message
        cleaned_dict = decimal_to_serializable(message_dict)
        dict_messages.append(cleaned_dict)
    return dict_messages

def dict_messages_to_base_messages(messages: List[dict]) -> List[BaseMessage]:
    base_messages = []
    for message in messages:
        # Clean the message dict of any Decimal objects before creating BaseMessage
        cleaned_message = decimal_to_serializable(message)
        
        if cleaned_message["type"] == "human":
            base_messages.append(HumanMessage(**cleaned_message))
        elif cleaned_message["type"] == "ai":
            base_messages.append(AIMessage(**cleaned_message))
        elif cleaned_message["type"] == "tool":
            base_messages.append(ToolMessage(**cleaned_message))
        elif cleaned_message["type"] == "system":
            base_messages.append(SystemMessage(**cleaned_message))
        else:
            raise ValueError(f"Unknown message type: {cleaned_message['type']}")
    return base_messages