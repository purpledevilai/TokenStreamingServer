import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class create_outlook_reply_draft(BaseModel):
    """
    Create a draft reply to the sender of an email without sending it. The draft is threaded 
    in the same conversation as the original message and can be reviewed, edited, and sent later 
    using the send_outlook_draft tool. By default the reply is addressed to the original sender, 
    but you can override the recipient using the 'to' parameter (useful when the original sender 
    is a system/notification address and you need to reply to the actual customer).
    Use 'comment' for a simple text reply above the quoted original, or 'body' for full 
    control over the reply content. Do not specify both.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    shared_mailbox_email: Optional[str] = Field(
        default=None,
        description="Email address of a shared mailbox to access. Leave empty to use your own mailbox."
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
        description="Override the recipient email address. If not provided, the reply is addressed to the original sender. "
                    "Use this when the original sender is a system address and you need to reply to a different person."
    )
    cc: Optional[str] = Field(
        default=None,
        description="CC recipient email address (optional)."
    )


def create_outlook_reply_draft_func(integration_id: str, shared_mailbox_email: str = None,
                                     message_id: str = None, comment: str = None, body: str = None,
                                     html: bool = False, to: str = None, cc: str = None) -> str:
    """
    Create a draft reply to the sender of a message.
    
    Args:
        integration_id: The Outlook integration ID
        shared_mailbox_email: Email address of a shared mailbox to access (optional)
        message_id: The ID of the message to reply to
        comment: Simple text comment (mutually exclusive with body)
        body: Full body content (mutually exclusive with comment)
        html: Whether body is HTML
        to: Override recipient email address (optional)
        cc: CC recipient email address (optional)
        
    Returns:
        JSON string with reply draft details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = OutlookService.create_reply_draft(
        integration_id, message_id,
        comment=comment, body=body, html=html,
        to=to, cc=cc,
        shared_mailbox_email=shared_mailbox_email
    )
    
    return json.dumps({
        "status": "created",
        "draft_id": result.get("id"),
        "message_id": message_id,
        "to": to or "(original sender)",
        "subject": result.get("subject"),
    }, indent=2)


async def create_outlook_reply_draft_func_async(integration_id: str, shared_mailbox_email: str = None,
                                                 message_id: str = None, comment: str = None, body: str = None,
                                                 html: bool = False, to: str = None, cc: str = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: create_outlook_reply_draft_func(integration_id, shared_mailbox_email, message_id, comment, body, html, to, cc)
    )


create_outlook_reply_draft_tool = AgentTool(params=create_outlook_reply_draft, function=create_outlook_reply_draft_func_async, pass_context=False)
