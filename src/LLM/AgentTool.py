from typing import Callable, Any, Type, Optional
from pydantic import BaseModel


class AgentTool(BaseModel):
    tool_id: Optional[str] = None
    function: Callable[[Any], str]
    params: Type[BaseModel]
    pass_context: bool = False
    is_async: bool = False
    is_client_side_tool: bool = False

