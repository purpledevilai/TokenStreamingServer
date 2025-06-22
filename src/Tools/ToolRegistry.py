from Tools.PassEvent import pass_event_tool

from Tools.MemoryTools.append_memory import append_memory_tool
from Tools.MemoryTools.read_memory import read_memory_tool
from Tools.MemoryTools.view_memory_shape import view_memory_shape_tool
from Tools.MemoryTools.delete_memory import delete_memory_tool
from Tools.MemoryTools.write_memory import write_memory_tool

from Tools.WebSearchTools.web_search import web_search_tool
from Tools.WebSearchTools.view_url import view_url_tool

tool_registry = {
    # Pass Event Tool
    "pass_event": pass_event_tool,

    # Memory Tools
    "append_memory": append_memory_tool,
    "read_memory": read_memory_tool,
    "view_memory_shape": view_memory_shape_tool,
    "delete_memory": delete_memory_tool,
    "write_memory": write_memory_tool,

    # Web Search Tools
    "web_search": web_search_tool,
    "view_url": view_url_tool
}
