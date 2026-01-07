import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class send_draft(BaseModel):
    """
    Send an existing draft email. This sends the draft and removes it from the drafts folder.
    The draft must have a recipient (to) address to be sent successfully.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    draft_id: str = Field(description="The unique ID of the draft to send.")


def send_draft_func(integration_id: str, draft_id: str) -> str:
    """
    Send an existing draft.
    
    Args:
        integration_id: The Gmail integration ID
        draft_id: The draft ID to send
        
    Returns:
        JSON string confirming the sent message
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not draft_id:
        raise Exception("draft_id is required.")
    
    result = GmailService.send_draft(integration_id, draft_id)
    
    return json.dumps({
        "status": "sent",
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
        "labels": result.get("labelIds", []),
    }, indent=2)


async def send_draft_func_async(integration_id: str, draft_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: send_draft_func(integration_id, draft_id)
    )


send_draft_tool = AgentTool(params=send_draft, function=send_draft_func_async, pass_context=False)

