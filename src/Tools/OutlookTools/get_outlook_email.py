import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class get_outlook_email(BaseModel):
    """
    Get the full content of a specific email from Outlook including the complete body text.
    Use the message ID from list_outlook_emails to retrieve the full email.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    message_id: str = Field(description="The message ID from list_outlook_emails.")


def get_outlook_email_func(integration_id: str, message_id: str) -> str:
    """
    Get the full content of a specific email.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID
        
    Returns:
        JSON string with full email details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    message = OutlookService.get_message(integration_id, message_id)
    
    # Parse sender and recipient info
    from_addr = message.get("from", {}).get("emailAddress", {})
    to_recipients = message.get("toRecipients", [])
    cc_recipients = message.get("ccRecipients", [])
    
    to_list = [r.get("emailAddress", {}).get("address", "") for r in to_recipients]
    cc_list = [r.get("emailAddress", {}).get("address", "") for r in cc_recipients]
    
    return json.dumps({
        "id": message.get("id"),
        "conversation_id": message.get("conversationId"),
        "from": from_addr.get("address", ""),
        "from_name": from_addr.get("name", ""),
        "to": to_list,
        "cc": cc_list,
        "subject": message.get("subject", "(No Subject)"),
        "received_date": message.get("receivedDateTime", ""),
        "sent_date": message.get("sentDateTime", ""),
        "body": OutlookService.parse_message_body(message),
        "body_type": message.get("body", {}).get("contentType", ""),
        "snippet": message.get("bodyPreview", ""),
        "is_read": message.get("isRead", False),
        "is_draft": message.get("isDraft", False),
        "has_attachments": message.get("hasAttachments", False),
        "importance": message.get("importance", "normal"),
        "categories": message.get("categories", []),
        "flag": message.get("flag", {}).get("flagStatus", "notFlagged"),
        "parent_folder_id": message.get("parentFolderId", ""),
    }, indent=2)


async def get_outlook_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_outlook_email_func(integration_id, message_id)
    )


get_outlook_email_tool = AgentTool(params=get_outlook_email, function=get_outlook_email_func_async, pass_context=False)

