import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class send_outlook_email(BaseModel):
    """
    Send an email from the connected Outlook account. Composes and sends an email to the 
    specified recipient with the given subject and body.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    shared_mailbox_email: Optional[str] = Field(
        default=None,
        description="Email address of a shared mailbox to send from. Leave empty to send from your own mailbox."
    )
    to: str = Field(description="The recipient's email address.")
    subject: str = Field(description="The subject line of the email.")
    body: str = Field(description="The body content of the email. Can be plain text or HTML.")
    html: Optional[bool] = Field(
        default=False,
        description="Set to true if the body contains HTML content."
    )


def send_outlook_email_func(integration_id: str, shared_mailbox_email: str = None,
                            to: str = None, subject: str = None, body: str = None, 
                            html: bool = False) -> str:
    """
    Send an email.
    
    Args:
        integration_id: The Outlook integration ID
        shared_mailbox_email: Email address of a shared mailbox to send from (optional)
        to: Recipient email address
        subject: Email subject
        body: Email body
        html: Whether body is HTML
        
    Returns:
        JSON string confirming the sent message
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not to:
        raise Exception("to (recipient email) is required.")
    if not subject:
        raise Exception("subject is required.")
    if not body:
        raise Exception("body is required.")
    
    OutlookService.send_message(integration_id, to, subject, body, html=html,
                                shared_mailbox_email=shared_mailbox_email)
    
    return json.dumps({
        "status": "sent",
        "to": to,
        "subject": subject,
    }, indent=2)


async def send_outlook_email_func_async(integration_id: str, shared_mailbox_email: str = None,
                                         to: str = None, subject: str = None, body: str = None, 
                                         html: bool = False) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: send_outlook_email_func(integration_id, shared_mailbox_email, to, subject, body, html)
    )


send_outlook_email_tool = AgentTool(params=send_outlook_email, function=send_outlook_email_func_async, pass_context=False)

