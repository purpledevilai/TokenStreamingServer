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
from Tools.GmailTools.archive_email import archive_email_tool
from Tools.GmailTools.trash_email import trash_email_tool
from Tools.GmailTools.untrash_email import untrash_email_tool
from Tools.GmailTools.delete_email import delete_email_tool
from Tools.GmailTools.set_email_read_status import set_email_read_status_tool
from Tools.GmailTools.modify_email_labels import modify_email_labels_tool
from Tools.GmailTools.list_labels import list_labels_tool
from Tools.GmailTools.create_label import create_label_tool
from Tools.GmailTools.delete_label import delete_label_tool
from Tools.GmailTools.list_drafts import list_drafts_tool
from Tools.GmailTools.get_draft import get_draft_tool
from Tools.GmailTools.create_draft import create_draft_tool
from Tools.GmailTools.update_draft import update_draft_tool
from Tools.GmailTools.send_draft import send_draft_tool
from Tools.GmailTools.delete_draft import delete_draft_tool

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

    # Gmail Tools - Email Operations
    "list_emails": list_emails_tool,
    "get_email": get_email_tool,
    "send_email": send_email_tool,
    "set_email_read_status": set_email_read_status_tool,
    "archive_email": archive_email_tool,
    "trash_email": trash_email_tool,
    "untrash_email": untrash_email_tool,
    "delete_email": delete_email_tool,
    "modify_email_labels": modify_email_labels_tool,

    # Gmail Tools - Label Operations
    "list_labels": list_labels_tool,
    "create_label": create_label_tool,
    "delete_label": delete_label_tool,

    # Gmail Tools - Draft Operations
    "list_drafts": list_drafts_tool,
    "get_draft": get_draft_tool,
    "create_draft": create_draft_tool,
    "update_draft": update_draft_tool,
    "send_draft": send_draft_tool,
    "delete_draft": delete_draft_tool,
}
