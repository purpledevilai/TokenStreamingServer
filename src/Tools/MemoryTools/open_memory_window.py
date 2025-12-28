import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Models import JSONDocument
from Tools.MemoryTools.helper_retrive_and_cache_doc import retrieve_and_cache_doc
from AWS.APIGateway import default_type_error_handler


class open_memory_window(BaseModel):
    """
    Open a Memory Window to access a persisted JSON memory document. Memory Windows provide continuous access to 
    memory data that automatically refreshes with the latest values on each subsequent invocation. This is useful 
    when you need to repeatedly reference memory data that may be modified by other tools (write_memory, append_memory, 
    delete_memory) without making repeated read_memory calls.
    
    You can optionally specify a path to open only a specific section of the memory document. If no path is provided,
    the entire document data will be available.
    """
    document_id: str = Field(description="The unique identifier for the memory document to open.")
    path: Optional[str] = Field(
        default="",
        description="A dot-separated string specifying the path to a specific section within the memory document "
                    "(e.g., user.preferences, tasks.0.details). If left blank, the entire document will be opened. "
                    "Use 0-based indexing for array elements."
    )


def open_memory_window_func(document_id: str, path: str = "", context: dict = {}) -> str:
    """
    Opens a Memory Window and returns its current data.
    
    Args:
        document_id: The unique identifier for the memory document
        path: Optional dot-separated path to a specific section
        context: The context dict containing user_id for permission validation
        
    Returns:
        The current data from the memory document (or path within it) as a JSON string
        
    Raises:
        Exception: If document doesn't exist or user doesn't have access
    """
    if not document_id:
        raise Exception("document_id is required.")
    
    if not path:
        path = ""

    # Retrieve the memory document (handles permissions and caching)
    memory_document = retrieve_and_cache_doc(document_id, context)
    
    # Resolve path if specified
    if path:
        try:
            value = JSONDocument._resolve_path(memory_document.data, path.split("."))
        except Exception as e:
            raise Exception(f"OpenMemoryWindow: Path '{path}' not found in document: {e}")
    else:
        value = memory_document.data
    
    return json.dumps(value, default=default_type_error_handler, indent=2)


async def open_memory_window_func_async(document_id: str, path: str, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: open_memory_window_func(document_id, path, context)
    )


# This is the tool that will be used in the agent chat
open_memory_window_tool = AgentTool(params=open_memory_window, function=open_memory_window_func_async, pass_context=True)

