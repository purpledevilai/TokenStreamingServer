import asyncio
from pydantic import Field, BaseModel
import json
from LLM.AgentTool import AgentTool
from Models import JSONDocument
from Tools.MemoryTools.helper_retrive_and_cache_doc import retrieve_and_cache_doc
from AWS.APIGateway import default_type_error_handler


class view_memory_shape(BaseModel):
    """
    View the structure and data types of a persisted JSON document. This tool analyzes the document and returns a shape representation showing the data types and structure at each level. This is useful for understanding the format and organization of stored data before performing read or write operations.
    
    The shape shows data types like 'string', 'number', 'boolean', 'null', and nested structures for objects and arrays. For arrays with mixed types, it shows all possible types. For objects, it shows the structure with field names and their types.
    """
    document_id: str = Field(description="The unique identifier for the memory document to analyze.")
    path: str = Field(description="A dot-separated string specifying the path to analyze within the memory document (e.g., user.profile, tasks.0). If left blank, the shape of the entire document will be returned.", default="")


def view_memory_shape_func(document_id: str, path: str, context: dict) -> str:
    # Check parameters
    if not document_id:
        raise Exception("document_id is required.")
    if not path:
        path = ""

    # Retrieve the memory document
    memory_document = retrieve_and_cache_doc(document_id, context)
    
    # Get the value at the specified path (or root if no path)
    if path:
        try:
            value = JSONDocument._resolve_path(memory_document.data, path.split(".") if path else [])
        except Exception as e:
            raise Exception(f"Path '{path}' not found in document: {e}")
    else:
        value = memory_document.data
    
    # Get the shape of the value
    shape = JSONDocument._infer_shape(value)
    
    # Create a result with metadata
    result = {
        "document_id": document_id,
        "path": path if path else "root",
        "shape": shape,
        "analysis": _get_shape_analysis(shape)
    }
    
    return json.dumps(result, default=default_type_error_handler, indent=2)


def _get_shape_analysis(shape) -> dict:
    """Provide additional analysis about the shape."""
    analysis = {
        "type": _get_root_type(shape),
        "complexity": _calculate_complexity(shape)
    }
    
    if isinstance(shape, dict):
        analysis["field_count"] = len(shape)
        analysis["fields"] = list(shape.keys())
    elif isinstance(shape, list) and shape:
        analysis["array_types"] = len(shape)
        analysis["contains_objects"] = any(isinstance(s, dict) for s in shape)
    
    return analysis


def _get_root_type(shape) -> str:
    """Get the root type of the shape."""
    if isinstance(shape, dict):
        return "object"
    elif isinstance(shape, list):
        if not shape:
            return "empty_array"
        return "array"
    else:
        return str(shape)


def _calculate_complexity(shape, depth=0) -> int:
    """Calculate a complexity score for the shape."""
    if depth > 10:  # Prevent infinite recursion
        return 0
    
    if isinstance(shape, dict):
        return 1 + sum(_calculate_complexity(v, depth + 1) for v in shape.values())
    elif isinstance(shape, list):
        return 1 + sum(_calculate_complexity(s, depth + 1) for s in shape)
    else:
        return 1


async def view_memory_shape_func_async(document_id: str, path: str, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: view_memory_shape_func(document_id, path, context)
    )


view_memory_shape_tool = AgentTool(params=view_memory_shape, function=view_memory_shape_func_async, pass_context=True)