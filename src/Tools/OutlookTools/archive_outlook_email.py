import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class archive_outlook_email(BaseModel):
    """
    Archive an email by moving it to the Archive folder. The email is not deleted and can 
    still be found in the Archive folder or by searching.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    shared_mailbox_email: Optional[str] = Field(
        default=None,
        description="Email address of a shared mailbox to access. Leave empty to access your own mailbox."
    )
    message_id: str = Field(description="The message ID to archive.")


def archive_outlook_email_func(integration_id: str, shared_mailbox_email: str = None,
                                message_id: str = None) -> str:
    """
    Archive an email by moving it to the Archive folder.
    
    Args:
        integration_id: The Outlook integration ID
        shared_mailbox_email: Email address of a shared mailbox to access (optional)
        message_id: The message ID to archive
        
    Returns:
        JSON string confirming the archive
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = OutlookService.move_message(integration_id, message_id, "archive",
                                          shared_mailbox_email=shared_mailbox_email)
    
    return json.dumps({
        "status": "archived",
        "message_id": result.get("id"),
        "parent_folder_id": result.get("parentFolderId"),
    }, indent=2)


async def archive_outlook_email_func_async(integration_id: str, shared_mailbox_email: str = None,
                                            message_id: str = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: archive_outlook_email_func(integration_id, shared_mailbox_email, message_id)
    )


archive_outlook_email_tool = AgentTool(params=archive_outlook_email, function=archive_outlook_email_func_async, pass_context=False)

