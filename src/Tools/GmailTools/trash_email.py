import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class trash_email(BaseModel):
    """
    Move an email to the trash. The email will be automatically permanently deleted after 
    30 days. Use untrash_email to restore it before then, or delete_email to permanently 
    delete it immediately.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    message_id: str = Field(description="The unique ID of the email message to move to trash.")


def trash_email_func(integration_id: str, message_id: str) -> str:
    """
    Move an email to the trash.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID to trash
        
    Returns:
        JSON string confirming the action
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = GmailService.trash_message(integration_id, message_id)
    
    return json.dumps({
        "status": "trashed",
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
        "labels": result.get("labelIds", []),
    }, indent=2)


async def trash_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: trash_email_func(integration_id, message_id)
    )


trash_email_tool = AgentTool(params=trash_email, function=trash_email_func_async, pass_context=False)

