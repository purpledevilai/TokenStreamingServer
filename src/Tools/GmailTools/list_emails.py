import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GmailService


class list_emails(BaseModel):
    """
    List emails from a Gmail account. Returns a list of email summaries including sender, subject, 
    date, and whether the email is unread. Use the query parameter to filter emails by various criteria.
    
    Content/keyword search:
    - Any keyword: 'meeting' (searches subject, body, sender name, etc.)
    - Exact phrase: '"project deadline"' (use quotes for exact match)
    - Multiple keywords (AND): 'budget report' (must contain both)
    - Either keyword (OR): '{budget OR report}' (contains either)
    - Exclude keyword: '-unsubscribe' (excludes emails with this word)
    
    Location/label filters:
    - Inbox only: 'in:inbox'
    - Trashed emails: 'in:trash'
    - Archived emails: '-in:inbox -in:trash -in:spam'
    - Sent emails: 'in:sent'
    - Spam: 'in:spam'
    - Starred: 'is:starred'
    - Specific label: 'label:YourLabelName'
    
    People filters:
    - From someone: 'from:email@example.com'
    - To someone: 'to:email@example.com'
    - CC'd: 'cc:email@example.com'
    - BCC'd: 'bcc:email@example.com'
    
    Other filters:
    - Unread: 'is:unread'
    - Subject contains: 'subject:keyword'
    - Has attachment: 'has:attachment'
    - Attachment filename: 'filename:pdf' or 'filename:report.xlsx'
    - Date range: 'after:2024/01/01 before:2024/12/31'
    - Larger than: 'larger:5M'
    - Smaller than: 'smaller:1M'
    
    Combine multiple filters with spaces (AND logic).
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    query: Optional[str] = Field(
        default=None,
        description="Gmail search query. Keywords search everywhere (subject, body, sender). "
                    "Use quotes for exact phrases: '\"exact phrase\"'. "
                    "Location: 'in:inbox', 'in:trash', 'in:sent', 'label:Name'. "
                    "People: 'from:email', 'to:email'. Status: 'is:unread', 'is:starred'. "
                    "Attachments: 'has:attachment', 'filename:pdf'. "
                    "Dates: 'after:2024/01/01', 'before:2024/12/31'. "
                    "Exclude with minus: '-keyword'. Combine with spaces for AND logic."
    )
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of emails to return (default 10, max 100)."
    )


def list_emails_func(integration_id: str, query: str = None, max_results: int = 10) -> str:
    """
    List emails from the Gmail inbox.
    
    Args:
        integration_id: The Gmail integration ID
        query: Gmail search query
        max_results: Maximum number of results
        
    Returns:
        JSON string with list of email summaries
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    if max_results > 100:
        max_results = 100
    
    # Get list of message IDs
    result = GmailService.list_messages(integration_id, query=query, max_results=max_results)
    messages = result.get("messages", [])
    
    if not messages:
        return json.dumps({"emails": [], "count": 0})
    
    # Fetch details for each message
    email_summaries = []
    for msg in messages:
        try:
            message = GmailService.get_message(integration_id, msg["id"], format="metadata")
            headers = GmailService.parse_message_headers(message)
            
            # Check if unread
            labels = message.get("labelIds", [])
            is_unread = "UNREAD" in labels
            
            email_summaries.append({
                "id": msg["id"],
                "thread_id": message.get("threadId"),
                "from": headers.get("from", "Unknown"),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", "(No Subject)"),
                "date": headers.get("date", ""),
                "snippet": message.get("snippet", ""),
                "is_unread": is_unread,
                "labels": labels,
            })
        except Exception as e:
            # Skip messages that fail to load
            continue
    
    return json.dumps({
        "emails": email_summaries,
        "count": len(email_summaries),
        "result_size_estimate": result.get("resultSizeEstimate", len(email_summaries))
    }, indent=2)


async def list_emails_func_async(integration_id: str, query: str = None, max_results: int = 10) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: list_emails_func(integration_id, query, max_results)
    )


list_emails_tool = AgentTool(params=list_emails, function=list_emails_func_async, pass_context=False)

