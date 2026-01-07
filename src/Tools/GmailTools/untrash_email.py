import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class untrash_email(BaseModel):
    """
    Restore an email from the trash. The email will be moved back to its previous location
    (typically the inbox).
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    message_id: str = Field(description="The unique ID of the email message to restore from trash.")


def untrash_email_func(integration_id: str, message_id: str) -> str:
    """
    Restore an email from the trash.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID to restore
        
    Returns:
        JSON string confirming the action
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = GmailService.untrash_message(integration_id, message_id)
    
    return json.dumps({
        "status": "restored",
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
        "labels": result.get("labelIds", []),
    }, indent=2)


async def untrash_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: untrash_email_func(integration_id, message_id)
    )


untrash_email_tool = AgentTool(params=untrash_email, function=untrash_email_func_async, pass_context=False)

