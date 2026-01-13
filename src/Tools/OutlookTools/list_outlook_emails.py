import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class list_outlook_emails(BaseModel):
    """
    List emails from an Outlook account. Returns a list of email summaries including sender, subject, 
    date, and read status. Use filter and search parameters to find specific emails.
    
    Filter query examples (OData $filter syntax):
    - Unread emails: 'isRead eq false'
    - Read emails: 'isRead eq true'
    - With attachments: 'hasAttachments eq true'
    - From specific sender: "from/emailAddress/address eq 'email@example.com'"
    - After a date: "receivedDateTime ge 2024-01-01T00:00:00Z"
    - Before a date: "receivedDateTime lt 2024-12-31T23:59:59Z"
    - High importance: "importance eq 'high'"
    - Flagged: "flag/flagStatus eq 'flagged'"
    - Combine with 'and': "isRead eq false and hasAttachments eq true"
    
    Search query examples (full-text search):
    - Keywords: 'meeting' (searches subject, body, sender)
    - Multiple words: 'project deadline'
    
    Folder options:
    - 'inbox' - Main inbox
    - 'drafts' - Draft messages
    - 'sentitems' - Sent messages  
    - 'deleteditems' - Trash/deleted items
    - 'archive' - Archived messages
    - 'junkemail' - Spam/junk folder
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    folder: Optional[str] = Field(
        default=None,
        description="Folder to list emails from. Options: 'inbox', 'drafts', 'sentitems', 'deleteditems', 'archive', 'junkemail'. "
                    "Leave empty to search all messages."
    )
    filter_query: Optional[str] = Field(
        default=None,
        description="OData $filter query. Examples: 'isRead eq false', 'hasAttachments eq true', "
                    "'importance eq \"high\"'. Combine with 'and'/'or'."
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Full-text search query. Searches subject, body, and sender information."
    )
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of emails to return (default 10, max 100)."
    )


def list_outlook_emails_func(integration_id: str, folder: str = None, filter_query: str = None,
                              search_query: str = None, max_results: int = 10) -> str:
    """
    List emails from the Outlook mailbox.
    
    Args:
        integration_id: The Outlook integration ID
        folder: Optional folder to filter by
        filter_query: OData filter query
        search_query: Full-text search query
        max_results: Maximum number of results
        
    Returns:
        JSON string with list of email summaries
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    if max_results > 100:
        max_results = 100
    
    # Convert folder name to well-known folder ID if needed
    folder_id = None
    if folder:
        folder_id = OutlookService.get_well_known_folder_id(folder)
    
    # Get list of messages
    result = OutlookService.list_messages(
        integration_id, 
        folder_id=folder_id,
        filter_query=filter_query,
        search_query=search_query,
        max_results=max_results
    )
    
    messages = result.get("value", [])
    
    if not messages:
        return json.dumps({"emails": [], "count": 0})
    
    # Parse messages into summaries
    email_summaries = []
    for msg in messages:
        try:
            summary = OutlookService.parse_message_to_summary(msg)
            email_summaries.append(summary)
        except Exception as e:
            # Skip messages that fail to parse
            continue
    
    return json.dumps({
        "emails": email_summaries,
        "count": len(email_summaries),
    }, indent=2)


async def list_outlook_emails_func_async(integration_id: str, folder: str = None, filter_query: str = None,
                                          search_query: str = None, max_results: int = 10) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: list_outlook_emails_func(integration_id, folder, filter_query, search_query, max_results)
    )


list_outlook_emails_tool = AgentTool(params=list_outlook_emails, function=list_outlook_emails_func_async, pass_context=False)

