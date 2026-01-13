import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class archive_outlook_email(BaseModel):
    """
    Archive an email by moving it to the Archive folder. The email is not deleted and can 
    still be found in the Archive folder or by searching.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    message_id: str = Field(description="The message ID to archive.")


def archive_outlook_email_func(integration_id: str, message_id: str) -> str:
    """
    Archive an email by moving it to the Archive folder.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID to archive
        
    Returns:
        JSON string confirming the archive
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = OutlookService.move_message(integration_id, message_id, "archive")
    
    return json.dumps({
        "status": "archived",
        "message_id": result.get("id"),
        "parent_folder_id": result.get("parentFolderId"),
    }, indent=2)


async def archive_outlook_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: archive_outlook_email_func(integration_id, message_id)
    )


archive_outlook_email_tool = AgentTool(params=archive_outlook_email, function=archive_outlook_email_func_async, pass_context=False)

