import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class untrash_outlook_email(BaseModel):
    """
    Restore an email from the Deleted Items (trash) folder back to the Inbox.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    message_id: str = Field(description="The message ID to restore from trash.")


def untrash_outlook_email_func(integration_id: str, message_id: str) -> str:
    """
    Restore an email from the Deleted Items folder to Inbox.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID to restore
        
    Returns:
        JSON string confirming the restore
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = OutlookService.move_message(integration_id, message_id, "inbox")
    
    return json.dumps({
        "status": "restored",
        "message_id": result.get("id"),
        "parent_folder_id": result.get("parentFolderId"),
    }, indent=2)


async def untrash_outlook_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: untrash_outlook_email_func(integration_id, message_id)
    )


untrash_outlook_email_tool = AgentTool(params=untrash_outlook_email, function=untrash_outlook_email_func_async, pass_context=False)

