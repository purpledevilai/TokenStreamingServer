import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class send_outlook_draft(BaseModel):
    """
    Send an existing draft email. The draft must have a recipient (to address) to be sent.
    This removes the draft from the drafts folder and sends it.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    draft_id: str = Field(description="The draft ID to send.")


def send_outlook_draft_func(integration_id: str, draft_id: str) -> str:
    """
    Send an existing draft.
    
    Args:
        integration_id: The Outlook integration ID
        draft_id: The draft ID to send
        
    Returns:
        JSON string confirming the draft was sent
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not draft_id:
        raise Exception("draft_id is required.")
    
    OutlookService.send_draft(integration_id, draft_id)
    
    return json.dumps({
        "status": "sent",
        "draft_id": draft_id,
    }, indent=2)


async def send_outlook_draft_func_async(integration_id: str, draft_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: send_outlook_draft_func(integration_id, draft_id)
    )


send_outlook_draft_tool = AgentTool(params=send_outlook_draft, function=send_outlook_draft_func_async, pass_context=False)

