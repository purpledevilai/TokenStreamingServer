import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GmailService


class list_emails(BaseModel):
    """
    List emails from a Gmail inbox. Returns a list of email summaries including sender, subject, 
    date, and whether the email is unread. Use the query parameter to filter emails 
    (e.g., "is:unread", "from:someone@example.com", "subject:meeting").
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    query: Optional[str] = Field(
        default=None,
        description="Gmail search query to filter emails. Examples: 'is:unread', 'from:boss@company.com', "
                    "'subject:urgent', 'after:2024/01/01', 'has:attachment'. Multiple filters can be combined."
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

