import asyncio
from enum import Enum
from pydantic import Field, BaseModel
import json
from LLM.AgentChat import AgentTool
from Models import JSONDocument
from Tools.MemoryTools.helper_retrive_and_cache_doc import retrieve_and_cache_doc


class MemoryValueType(str, Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    json = "json"

class write_memory(BaseModel):
    """
    Write a value to a persisted JSON document at a specified path. This tool will set or overwrite the value at the given location. The value is always passed as a string and must be parsed according to the provided type. This ensures the memory remains structured and queryable.

    When working with lists, it is preferred to use key-based storage rather than index-based list updates to avoid off-by-one errors or overwriting unintended values. In cases where indexed updates are appropriate, they must follow 0-based indexing.
    """
    document_id: str = Field(description="The unique identifier for the memory document to modify.")
    path: str = Field(description="A dot-separated string specifying where to store the value within the memory document (e.g., user.preferences.theme). Use 0-based indexes for targeting items in lists (e.g., projects.1.status updates the second project's status).")
    value: str = Field(description="The value to be written, passed as a string.")
    type: MemoryValueType = Field(description="""
The type that the string value should be parsed into. Accepted values are:
"string": Store the raw string as-is.
"number": Parse and store the value as a numeric type (integer or float).
"boolean": Parse and store the value as a boolean (true or false).
"json": Parse the string as valid JSON (either an object or a list).
""")


def write_memory_func(document_id: str, path: str, value: str, type: str, context: dict) -> str:
    # Check parameters
    if not document_id:
        raise Exception("document_id is required.")
    if not path:
        path = ""
    if value is None:
        raise Exception("value is required.")
    if type not in MemoryValueType.__members__:
        raise Exception(f"Invalid type '{type}'. Must be one of: {', '.join(MemoryValueType.__members__)}")
    
    # Retrieve the memory document
    document = retrieve_and_cache_doc(document_id, context)

    parsed = JSONDocument._parse_value(value, type)
    parent, last = JSONDocument._navigate_to_parent(document.data, path.split(".") if path else [], True)
    if last.isdigit():
        idx = int(last)
        if not isinstance(parent, list):
            raise Exception("Expected list at final segment", 400)
        if idx >= len(parent):
            raise Exception("List index out of range", 400)
        parent[idx] = parsed
    else:
        if not isinstance(parent, dict):
            raise Exception("Expected object at final segment", 400)
        parent[last] = parsed

    JSONDocument.save_json_document(document)
    
    return "Memory updated successfully."


async def write_memory_func_async(document_id: str, path: str, value: str, type: str, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: write_memory_func(document_id, path, value, type, context)
    )


write_memory_tool = AgentTool(params=write_memory, function=write_memory_func_async, pass_context=True)