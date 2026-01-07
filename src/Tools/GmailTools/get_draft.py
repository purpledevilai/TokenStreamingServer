import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class get_draft(BaseModel):
    """
    Get the full content of a specific draft email by its draft ID. Returns the complete draft
    including recipient, subject, and body content.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    draft_id: str = Field(description="The unique ID of the draft to retrieve.")


def get_draft_func(integration_id: str, draft_id: str) -> str:
    """
    Get the full content of a draft.
    
    Args:
        integration_id: The Gmail integration ID
        draft_id: The draft ID
        
    Returns:
        JSON string with full draft details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not draft_id:
        raise Exception("draft_id is required.")
    
    # Get full draft
    draft_data = GmailService.get_draft(integration_id, draft_id, format="full")
    message = draft_data.get("message", {})
    headers = GmailService.parse_message_headers(message)
    body = GmailService.parse_message_body(message)
    
    draft_details = {
        "draft_id": draft_data.get("id"),
        "message_id": message.get("id"),
        "thread_id": message.get("threadId"),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", "(No Subject)"),
        "body": body,
        "snippet": message.get("snippet", ""),
        "labels": message.get("labelIds", []),
    }
    
    return json.dumps(draft_details, indent=2)


async def get_draft_func_async(integration_id: str, draft_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_draft_func(integration_id, draft_id)
    )


get_draft_tool = AgentTool(params=get_draft, function=get_draft_func_async, pass_context=False)

