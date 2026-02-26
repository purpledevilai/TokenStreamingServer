import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class reply_all_outlook_email(BaseModel):
    """
    Reply to all recipients of an email and send immediately. The reply is threaded in the same 
    conversation as the original message and goes to the original sender plus all To and CC 
    recipients. You can override or add recipients using the 'to' and 'cc' parameters.
    Use 'comment' for a simple text reply above the quoted original, or 'body' for full 
    control over the reply content. Do not specify both.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    shared_mailbox_email: Optional[str] = Field(
        default=None,
        description="Email address of a shared mailbox to send from. Leave empty to send from your own mailbox."
    )
    message_id: str = Field(description="The ID of the message to reply to.")
    comment: Optional[str] = Field(
        default=None,
        description="Simple text reply that is prepended above the quoted original message. "
                    "Mutually exclusive with 'body' - do not specify both."
    )
    body: Optional[str] = Field(
        default=None,
        description="Full body content for the reply. Use this for rich/HTML replies. "
                    "Mutually exclusive with 'comment' - do not specify both."
    )
    html: Optional[bool] = Field(
        default=False,
        description="Set to true if the body contains HTML content. Only applies when using 'body', not 'comment'."
    )
    to: Optional[str] = Field(
        default=None,
        description="Override or add a recipient email address. If not provided, replies to all original recipients."
    )
    cc: Optional[str] = Field(
        default=None,
        description="CC recipient email address (optional)."
    )


def reply_all_outlook_email_func(integration_id: str, shared_mailbox_email: str = None,
                                  message_id: str = None, comment: str = None, body: str = None,
                                  html: bool = False, to: str = None, cc: str = None) -> str:
    """
    Reply to all recipients of a message and send immediately.
    
    Args:
        integration_id: The Outlook integration ID
        shared_mailbox_email: Email address of a shared mailbox to send from (optional)
        message_id: The ID of the message to reply to
        comment: Simple text comment (mutually exclusive with body)
        body: Full body content (mutually exclusive with comment)
        html: Whether body is HTML
        to: Override/additional recipient email address (optional)
        cc: CC recipient email address (optional)
        
    Returns:
        JSON string confirming the reply was sent
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    if not comment and not body:
        raise Exception("Either 'comment' or 'body' is required for a reply.")
    
    OutlookService.reply_all_to_message(
        integration_id, message_id,
        comment=comment, body=body, html=html,
        to=to, cc=cc,
        shared_mailbox_email=shared_mailbox_email
    )
    
    return json.dumps({
        "status": "sent",
        "message_id": message_id,
        "to": to or "(all original recipients)",
    }, indent=2)


async def reply_all_outlook_email_func_async(integration_id: str, shared_mailbox_email: str = None,
                                              message_id: str = None, comment: str = None, body: str = None,
                                              html: bool = False, to: str = None, cc: str = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: reply_all_outlook_email_func(integration_id, shared_mailbox_email, message_id, comment, body, html, to, cc)
    )


reply_all_outlook_email_tool = AgentTool(params=reply_all_outlook_email, function=reply_all_outlook_email_func_async, pass_context=False)
