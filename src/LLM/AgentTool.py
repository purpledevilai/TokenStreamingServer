from typing import Callable, Any, Type
from pydantic import BaseModel


class AgentTool(BaseModel):
    function: Callable[[Any], str]
    params: Type[BaseModel]
    pass_context: bool = False
    is_async: bool = False

