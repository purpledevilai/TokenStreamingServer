from pydantic import BaseModel
from typing import Optional, List, Union

class ChatInput(BaseModel):
    context_id: str
    message: str
    save_ai_messages: Optional[bool] = True

# Import message types from Context for use in ChatResponse
# We'll define them inline to avoid circular imports
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

class ChatResponse(BaseModel):
    response: str
    saved_ai_messages: bool
    generated_messages: List[MessageType]
    events: Optional[list[dict]] = None