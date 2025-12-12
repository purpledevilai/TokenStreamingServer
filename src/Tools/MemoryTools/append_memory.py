import asyncio
from enum import Enum
from pydantic import Field, BaseModel
import json
from LLM.AgentTool import AgentTool
from Models import JSONDocument
from Tools.MemoryTools.helper_retrive_and_cache_doc import retrieve_and_cache_doc


class MemoryValueType(str, Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    json = "json"


class append_memory(BaseModel):
    """
    Append a value to an array in a persisted JSON document at a specified path. This tool will add the value to the end of an existing array at the given location. If the path doesn't exist or doesn't point to an array, an error will be raised.

    The value is always passed as a string and must be parsed according to the provided type. This ensures the memory remains structured and queryable.
    """
    document_id: str = Field(description="The unique identifier for the memory document to modify.")
    path: str = Field(description="A dot-separated string specifying the path to the array within the memory document (e.g., user.tasks, projects.0.subtasks). The path must point to an existing array.")
    value: str = Field(description="The value to be appended to the array, passed as a string.")
    type: MemoryValueType = Field(description="""
The type that the string value should be parsed into. Accepted values are:
"string": Store the raw string as-is.
"number": Parse and store the value as a numeric type (integer or float).
"boolean": Parse and store the value as a boolean (true or false).
"json": Parse the string as valid JSON (either an object or a list).
""")


def append_memory_func(document_id: str, path: str, value: str, type: str, context: dict) -> str:
    # Check parameters
    if not document_id:
        raise Exception("document_id is required.")
    if not path:
        raise Exception("path is required for append operation.")
    if value is None:
        raise Exception("value is required.")
    if type not in MemoryValueType.__members__:
        raise Exception(f"Invalid type '{type}'. Must be one of: {', '.join(MemoryValueType.__members__)}")
    
    # Retrieve the memory document
    document = retrieve_and_cache_doc(document_id, context)

    # Parse the value according to the specified type
    parsed = JSONDocument._parse_value(value, type)
    
    # Navigate to the target array
    try:
        target_array = JSONDocument._resolve_path(document.data, path.split(".") if path else [])
    except Exception as e:
        raise Exception(f"Path '{path}' not found in document: {e}")
    
    # Verify that the target is an array
    if not isinstance(target_array, list):
        raise Exception(f"Path '{path}' does not point to an array. Found type: {type(target_array).__name__}")
    
    # Append the parsed value to the array
    target_array.append(parsed)
    
    # Save the updated document
    JSONDocument.save_json_document(document)
    
    return f"Value successfully appended to array at path '{path}'. Array now has {len(target_array)} items."


async def append_memory_func_async(document_id: str, path: str, value: str, type: str, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: append_memory_func(document_id, path, value, type, context)
    )


append_memory_tool = AgentTool(params=append_memory, function=append_memory_func_async, pass_context=True)