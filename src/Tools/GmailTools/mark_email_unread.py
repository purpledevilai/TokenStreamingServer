import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class mark_email_unread(BaseModel):
    """
    Mark an email as unread. This adds the UNREAD label to the specified email message.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    message_id: str = Field(description="The unique ID of the email message to mark as unread.")


def mark_email_unread_func(integration_id: str, message_id: str) -> str:
    """
    Mark an email as unread.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID
        
    Returns:
        JSON string confirming the action
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = GmailService.mark_as_unread(integration_id, message_id)
    
    return json.dumps({
        "status": "success",
        "message_id": result.get("id"),
        "action": "marked_as_unread",
        "labels": result.get("labelIds", []),
    }, indent=2)


async def mark_email_unread_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: mark_email_unread_func(integration_id, message_id)
    )

mark_email_unread_tool = AgentTool(params=mark_email_unread, function=mark_email_unread_func_async, pass_context=False)

