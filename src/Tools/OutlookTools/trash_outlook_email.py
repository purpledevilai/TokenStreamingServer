import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class trash_outlook_email(BaseModel):
    """
    Move an email to the Deleted Items (trash) folder. The email can be restored using 
    untrash_outlook_email or will be permanently deleted according to the user's Outlook settings.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    message_id: str = Field(description="The message ID to trash.")


def trash_outlook_email_func(integration_id: str, message_id: str) -> str:
    """
    Move an email to the Deleted Items folder.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID to trash
        
    Returns:
        JSON string confirming the trash
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = OutlookService.move_message(integration_id, message_id, "deleteditems")
    
    return json.dumps({
        "status": "trashed",
        "message_id": result.get("id"),
        "parent_folder_id": result.get("parentFolderId"),
    }, indent=2)


async def trash_outlook_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: trash_outlook_email_func(integration_id, message_id)
    )


trash_outlook_email_tool = AgentTool(params=trash_outlook_email, function=trash_outlook_email_func_async, pass_context=False)

