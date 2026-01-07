import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class get_email(BaseModel):
    """
    Get the full content of a specific email by its message ID. Returns the complete email 
    including sender, recipients, subject, date, and the full body text.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    message_id: str = Field(description="The unique ID of the email message to retrieve.")


def get_email_func(integration_id: str, message_id: str) -> str:
    """
    Get the full content of a specific email.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID
        
    Returns:
        JSON string with full email details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    # Get full message
    message = GmailService.get_message(integration_id, message_id, format="full")
    headers = GmailService.parse_message_headers(message)
    body = GmailService.parse_message_body(message)
    
    # Check if unread
    labels = message.get("labelIds", [])
    is_unread = "UNREAD" in labels
    
    email_data = {
        "id": message.get("id"),
        "thread_id": message.get("threadId"),
        "from": headers.get("from", "Unknown"),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", "(No Subject)"),
        "date": headers.get("date", ""),
        "body": body,
        "snippet": message.get("snippet", ""),
        "is_unread": is_unread,
        "labels": labels,
    }
    
    return json.dumps(email_data, indent=2)


async def get_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_email_func(integration_id, message_id)
    )


get_email_tool = AgentTool(params=get_email, function=get_email_func_async, pass_context=False)

