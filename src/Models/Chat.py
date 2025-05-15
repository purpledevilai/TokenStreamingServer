from pydantic import BaseModel
from typing import Optional

class ChatInput(BaseModel):
    context_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    events: Optional[list[dict]] = None