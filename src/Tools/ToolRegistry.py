from Tools.PassEvent import pass_event_tool

from Tools.MemoryTools.append_memory import append_memory_tool
from Tools.MemoryTools.read_memory import read_memory_tool
from Tools.MemoryTools.view_memory_shape import view_memory_shape_tool
from Tools.MemoryTools.delete_memory import delete_memory_tool
from Tools.MemoryTools.write_memory import write_memory_tool
from Tools.MemoryTools.open_memory_window import open_memory_window_tool

from Tools.WebSearchTools.web_search import web_search_tool
from Tools.WebSearchTools.view_url import view_url_tool
from Tools.DataWindowTools.open_data_window import open_data_window_tool

from Tools.GmailTools.list_emails import list_emails_tool
from Tools.GmailTools.get_email import get_email_tool
from Tools.GmailTools.send_email import send_email_tool
from Tools.GmailTools.mark_email_read import mark_email_read_tool
from Tools.GmailTools.mark_email_unread import mark_email_unread_tool

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
    "view_url": view_url_tool,
    
    # DataWindow Tools
    "open_data_window": open_data_window_tool,

    # Open Memory Window Tool
    "open_memory_window": open_memory_window_tool,

    # Gmail Tools
    "list_emails": list_emails_tool,
    "get_email": get_email_tool,
    "send_email": send_email_tool,
    "mark_email_read": mark_email_read_tool,
    "mark_email_unread": mark_email_unread_tool,
}
