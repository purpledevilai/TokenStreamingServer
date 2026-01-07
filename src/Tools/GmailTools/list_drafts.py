import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GmailService


class list_drafts(BaseModel):
    """
    List all draft emails in the connected Gmail account. Returns a list of draft summaries
    including draft ID, recipient, subject, and snippet.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of drafts to return (default 10, max 100)."
    )


def list_drafts_func(integration_id: str, max_results: int = 10) -> str:
    """
    List draft emails.
    
    Args:
        integration_id: The Gmail integration ID
        max_results: Maximum number of results
        
    Returns:
        JSON string with list of draft summaries
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    if max_results > 100:
        max_results = 100
    
    # Get list of drafts
    result = GmailService.list_drafts(integration_id, max_results=max_results)
    drafts = result.get("drafts", [])
    
    if not drafts:
        return json.dumps({"drafts": [], "count": 0})
    
    # Fetch details for each draft
    draft_summaries = []
    for draft in drafts:
        try:
            draft_data = GmailService.get_draft(integration_id, draft["id"], format="metadata")
            message = draft_data.get("message", {})
            headers = GmailService.parse_message_headers(message)
            
            draft_summaries.append({
                "draft_id": draft["id"],
                "message_id": message.get("id"),
                "to": headers.get("to", ""),
                "subject": headers.get("subject", "(No Subject)"),
                "snippet": message.get("snippet", ""),
            })
        except Exception:
            # Skip drafts that fail to load
            continue
    
    return json.dumps({
        "drafts": draft_summaries,
        "count": len(draft_summaries),
        "result_size_estimate": result.get("resultSizeEstimate", len(draft_summaries))
    }, indent=2)


async def list_drafts_func_async(integration_id: str, max_results: int = 10) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: list_drafts_func(integration_id, max_results)
    )


list_drafts_tool = AgentTool(params=list_drafts, function=list_drafts_func_async, pass_context=False)

