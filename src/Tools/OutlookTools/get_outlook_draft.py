import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class get_outlook_draft(BaseModel):
    """
    Get the full content of a specific draft from Outlook.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    draft_id: str = Field(description="The draft ID from list_outlook_drafts.")


def get_outlook_draft_func(integration_id: str, draft_id: str) -> str:
    """
    Get the full content of a specific draft.
    
    Args:
        integration_id: The Outlook integration ID
        draft_id: The draft ID
        
    Returns:
        JSON string with full draft details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not draft_id:
        raise Exception("draft_id is required.")
    
    message = OutlookService.get_draft(integration_id, draft_id)
    
    # Parse recipient info
    to_recipients = message.get("toRecipients", [])
    to_addr = to_recipients[0].get("emailAddress", {}).get("address", "") if to_recipients else ""
    
    return json.dumps({
        "draft_id": message.get("id"),
        "to": to_addr,
        "subject": message.get("subject", "(No Subject)"),
        "body": OutlookService.parse_message_body(message),
        "body_type": message.get("body", {}).get("contentType", ""),
        "snippet": message.get("bodyPreview", ""),
        "created_date": message.get("createdDateTime", ""),
        "last_modified": message.get("lastModifiedDateTime", ""),
        "categories": message.get("categories", []),
    }, indent=2)


async def get_outlook_draft_func_async(integration_id: str, draft_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_outlook_draft_func(integration_id, draft_id)
    )


get_outlook_draft_tool = AgentTool(params=get_outlook_draft, function=get_outlook_draft_func_async, pass_context=False)

