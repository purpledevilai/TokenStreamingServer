import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GmailService


class update_draft(BaseModel):
    """
    Update an existing draft email. This replaces the entire draft content with the new values.
    Provide all fields you want in the updated draft, not just the changes.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    draft_id: str = Field(description="The unique ID of the draft to update.")
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


def update_draft_func(integration_id: str, draft_id: str, to: str = None, subject: str = None, body: str = None, html: bool = False) -> str:
    """
    Update an existing draft.
    
    Args:
        integration_id: The Gmail integration ID
        draft_id: The draft ID to update
        to: Recipient email address (optional)
        subject: Email subject (optional)
        body: Email body (optional)
        html: Whether body is HTML
        
    Returns:
        JSON string with updated draft details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not draft_id:
        raise Exception("draft_id is required.")
    
    result = GmailService.update_draft(integration_id, draft_id, to, subject, body, html=html)
    
    return json.dumps({
        "status": "updated",
        "draft_id": result.get("id"),
        "message_id": result.get("message", {}).get("id"),
        "to": to,
        "subject": subject,
    }, indent=2)


async def update_draft_func_async(integration_id: str, draft_id: str, to: str = None, subject: str = None, body: str = None, html: bool = False) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: update_draft_func(integration_id, draft_id, to, subject, body, html)
    )


update_draft_tool = AgentTool(params=update_draft, function=update_draft_func_async, pass_context=False)

