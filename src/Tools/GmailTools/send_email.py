import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GmailService


class send_email(BaseModel):
    """
    Send an email from the connected Gmail account. Composes and sends an email to the 
    specified recipient with the given subject and body.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    to: str = Field(description="The recipient's email address.")
    subject: str = Field(description="The subject line of the email.")
    body: str = Field(description="The body content of the email. Can be plain text or HTML.")
    html: Optional[bool] = Field(
        default=False,
        description="Set to true if the body contains HTML content."
    )


def send_email_func(integration_id: str, to: str, subject: str, body: str, html: bool = False) -> str:
    """
    Send an email.
    
    Args:
        integration_id: The Gmail integration ID
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
    
    result = GmailService.send_message(integration_id, to, subject, body, html=html)
    
    return json.dumps({
        "status": "sent",
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
        "to": to,
        "subject": subject,
    }, indent=2)


async def send_email_func_async(integration_id: str, to: str, subject: str, body: str, html: bool = False) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: send_email_func(integration_id, to, subject, body, html)
    )

send_email_tool = AgentTool(params=send_email, function=send_email_func_async, pass_context=False)

