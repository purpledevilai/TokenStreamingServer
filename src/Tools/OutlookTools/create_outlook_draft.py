import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class create_outlook_draft(BaseModel):
    """
    Create a draft email in the connected Outlook account. The draft can be edited later or sent 
    using the send_outlook_draft tool. All fields are optional - you can create an empty draft and 
    update it later.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    to: Optional[str] = Field(
        default=None,
        description="The recipient's email address."
    )
    subject: Optional[str] = Field(
        default=None,
        description="The subject line of the email."
    )
    body: Optional[str] = Field(
        default=None,
        description="The body content of the email. Can be plain text or HTML."
    )
    html: Optional[bool] = Field(
        default=False,
        description="Set to true if the body contains HTML content."
    )


def create_outlook_draft_func(integration_id: str, to: str = None, subject: str = None, 
                               body: str = None, html: bool = False) -> str:
    """
    Create a draft email.
    
    Args:
        integration_id: The Outlook integration ID
        to: Recipient email address (optional)
        subject: Email subject (optional)
        body: Email body (optional)
        html: Whether body is HTML
        
    Returns:
        JSON string with draft details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    result = OutlookService.create_draft(integration_id, to, subject, body, html=html)
    
    return json.dumps({
        "status": "created",
        "draft_id": result.get("id"),
        "to": to,
        "subject": subject,
    }, indent=2)


async def create_outlook_draft_func_async(integration_id: str, to: str = None, subject: str = None, 
                                          body: str = None, html: bool = False) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: create_outlook_draft_func(integration_id, to, subject, body, html)
    )


create_outlook_draft_tool = AgentTool(params=create_outlook_draft, function=create_outlook_draft_func_async, pass_context=False)

