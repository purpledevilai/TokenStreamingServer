import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class list_outlook_drafts(BaseModel):
    """
    List all draft emails in the Outlook account.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of drafts to return (default 10, max 100)."
    )


def list_outlook_drafts_func(integration_id: str, max_results: int = 10) -> str:
    """
    List drafts in the user's mailbox.
    
    Args:
        integration_id: The Outlook integration ID
        max_results: Maximum number of drafts to return
        
    Returns:
        JSON string with list of drafts
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    if max_results > 100:
        max_results = 100
    
    result = OutlookService.list_drafts(integration_id, max_results=max_results)
    messages = result.get("value", [])
    
    if not messages:
        return json.dumps({"drafts": [], "count": 0})
    
    # Parse drafts into summaries
    draft_summaries = []
    for msg in messages:
        try:
            to_recipients = msg.get("toRecipients", [])
            to_addr = to_recipients[0].get("emailAddress", {}).get("address", "") if to_recipients else ""
            
            draft_summaries.append({
                "draft_id": msg.get("id"),
                "to": to_addr,
                "subject": msg.get("subject", "(No Subject)"),
                "snippet": msg.get("bodyPreview", ""),
                "created_date": msg.get("createdDateTime", ""),
                "last_modified": msg.get("lastModifiedDateTime", ""),
            })
        except Exception as e:
            continue
    
    return json.dumps({
        "drafts": draft_summaries,
        "count": len(draft_summaries),
    }, indent=2)


async def list_outlook_drafts_func_async(integration_id: str, max_results: int = 10) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: list_outlook_drafts_func(integration_id, max_results)
    )


list_outlook_drafts_tool = AgentTool(params=list_outlook_drafts, function=list_outlook_drafts_func_async, pass_context=False)

