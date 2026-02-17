import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class get_outlook_email(BaseModel):
    """
    Get the full content of a specific email from Outlook including the complete body text.
    Use the message ID from list_outlook_emails to retrieve the full email.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    shared_mailbox_email: Optional[str] = Field(
        default=None,
        description="Email address of a shared mailbox to access. Leave empty to access your own mailbox."
    )
    message_id: str = Field(description="The message ID from list_outlook_emails.")


def get_outlook_email_func(integration_id: str, shared_mailbox_email: str = None,
                           message_id: str = None) -> str:
    """
    Get the full content of a specific email.
    
    Args:
        integration_id: The Outlook integration ID
        shared_mailbox_email: Email address of a shared mailbox to access (optional)
        message_id: The message ID
        
    Returns:
        JSON string with full email details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    message = OutlookService.get_message(integration_id, message_id, 
                                          shared_mailbox_email=shared_mailbox_email)
    
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


async def get_outlook_email_func_async(integration_id: str, shared_mailbox_email: str = None,
                                        message_id: str = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_outlook_email_func(integration_id, shared_mailbox_email, message_id)
    )


get_outlook_email_tool = AgentTool(params=get_outlook_email, function=get_outlook_email_func_async, pass_context=False)

