import asyncio
from pydantic import Field, BaseModel
import json
from LLM.AgentTool import AgentTool
from Models import JSONDocument
from Tools.MemoryTools.helper_retrive_and_cache_doc import retrieve_and_cache_doc


class delete_memory(BaseModel):
    """
    Delete a value or field from a persisted JSON document at a specified path. This tool will remove the specified key from an object or remove an item from an array at the given index. If the path doesn't exist, an error will be raised.

    When deleting from arrays, use 0-based indexing (e.g., tasks.0 deletes the first task). When deleting from objects, specify the key name (e.g., user.profile.email deletes the email field).
    """
    document_id: str = Field(description="The unique identifier for the memory document to modify.")
    path: str = Field(description="A dot-separated string specifying the path to the value to delete within the memory document (e.g., user.profile.email, tasks.0). The path must point to an existing field or array index.")


def delete_memory_func(document_id: str, path: str, context: dict) -> str:
    # Check parameters
    if not document_id:
        raise Exception("document_id is required.")
    if not path:
        raise Exception("path is required for delete operation.")
    
    # Retrieve the memory document
    document = retrieve_and_cache_doc(document_id, context)

    # Split the path to get parent and target
    path_parts = path.split(".") if path else []
    
    if len(path_parts) == 1:
        # Deleting from root level
        target_key = path_parts[0]
        if target_key.isdigit():
            # Root is an array
            if not isinstance(document.data, list):
                raise Exception("Cannot delete by index: root document is not an array.")
            idx = int(target_key)
            if idx >= len(document.data):
                raise Exception(f"Array index {idx} is out of range. Array has {len(document.data)} items.")
            deleted_value = document.data.pop(idx)
            result_msg = f"Deleted item at index {idx} from root array."
        else:
            # Root is an object
            if not isinstance(document.data, dict):
                raise Exception("Cannot delete by key: root document is not an object.")
            if target_key not in document.data:
                raise Exception(f"Key '{target_key}' not found in root object.")
            deleted_value = document.data.pop(target_key)
            result_msg = f"Deleted key '{target_key}' from root object."
    else:
        # Navigate to parent and delete from there
        try:
            parent, last_key = JSONDocument._navigate_to_parent(document.data, path_parts, False)
        except Exception as e:
            raise Exception(f"Path '{path}' not found in document: {e}")
        
        if last_key.isdigit():
            # Deleting from array
            if not isinstance(parent, list):
                raise Exception(f"Cannot delete by index: parent at path is not an array. Found type: {type(parent).__name__}")
            idx = int(last_key)
            if idx >= len(parent):
                raise Exception(f"Array index {idx} is out of range. Array has {len(parent)} items.")
            deleted_value = parent.pop(idx)
            result_msg = f"Deleted item at index {idx} from array at path '{'.'.join(path_parts[:-1])}'."
        else:
            # Deleting from object
            if not isinstance(parent, dict):
                raise Exception(f"Cannot delete by key: parent at path is not an object. Found type: {type(parent).__name__}")
            if last_key not in parent:
                raise Exception(f"Key '{last_key}' not found in object at path '{'.'.join(path_parts[:-1])}'.")
            deleted_value = parent.pop(last_key)
            result_msg = f"Deleted key '{last_key}' from object at path '{'.'.join(path_parts[:-1])}'."
    
    # Save the updated document
    JSONDocument.save_json_document(document)
    
    return f"{result_msg} The deleted value was: {json.dumps(deleted_value)}"


async def delete_memory_func_async(document_id: str, path: str, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: delete_memory_func(document_id, path, context)
    )


delete_memory_tool = AgentTool(params=delete_memory, function=delete_memory_func_async, pass_context=True)