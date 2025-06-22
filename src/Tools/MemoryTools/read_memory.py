import asyncio
from pydantic import Field, BaseModel
import json
from LLM.AgentChat import AgentTool
from Models import JSONDocument
from Tools.MemoryTools.helper_retrive_and_cache_doc import retrieve_and_cache_doc
from AWS.APIGateway import default_type_error_handler


class read_memory(BaseModel):
    """
    Retrieve information from a persisted JSON document. This tool reads either the entire memory object or a specific nested field by using a dot-separated path. If a path is provided, the tool will return only the value located at that path.
    """
    document_id: str = Field(description="The unique identifier for the memory document to retrieve.")
    path: str = Field(description="A dot-separated string specifying the path to the desired value within the memory document (e.g., user.profile.name). If left blank, the full memory document will be returned. If the target is within a list, use 0-based indexing (e.g., tasks.0.description retrieves the description of the first task in the tasks list).")


def read_memory_func(document_id: str, path: str, context: dict) -> str:

    # Check parameters
    if not document_id:
        raise Exception("document_id is required.")
    if not path:
        path = ""

    # Retrieve the memory document
    memory_document = retrieve_and_cache_doc(document_id, context)
    
    # Get the value
    print(f"Path to resolve: '{path}'")
    print(f"Splitting path: {path.split('.')}")
    value = JSONDocument._resolve_path(memory_document.data, path.split(".") if path else [])

    # Return
    return json.dumps(value, default=default_type_error_handler, indent=2) 


async def read_memory_func_async(document_id: str, path: str, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: read_memory_func(document_id, path, context)
    )


read_memory_tool = AgentTool(params=read_memory, function=read_memory_func_async, pass_context=True)
