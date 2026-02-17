import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class delete_outlook_folder(BaseModel):
    """
    Delete a custom mail folder. System folders (Inbox, Sent Items, Drafts, etc.) cannot be deleted.
    Any emails in the deleted folder will be permanently deleted.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    shared_mailbox_email: Optional[str] = Field(
        default=None,
        description="Email address of a shared mailbox to access. Leave empty to access your own mailbox."
    )
    folder_id: str = Field(description="The folder ID to delete (from list_outlook_folders).")


def delete_outlook_folder_func(integration_id: str, shared_mailbox_email: str = None,
                                folder_id: str = None) -> str:
    """
    Delete a mail folder.
    
    Args:
        integration_id: The Outlook integration ID
        shared_mailbox_email: Email address of a shared mailbox to access (optional)
        folder_id: The folder ID to delete
        
    Returns:
        JSON string confirming deletion
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not folder_id:
        raise Exception("folder_id is required.")
    
    OutlookService.delete_folder(integration_id, folder_id,
                                  shared_mailbox_email=shared_mailbox_email)
    
    return json.dumps({
        "status": "deleted",
        "folder_id": folder_id,
    }, indent=2)


async def delete_outlook_folder_func_async(integration_id: str, shared_mailbox_email: str = None,
                                            folder_id: str = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: delete_outlook_folder_func(integration_id, shared_mailbox_email, folder_id)
    )


delete_outlook_folder_tool = AgentTool(params=delete_outlook_folder, function=delete_outlook_folder_func_async, pass_context=False)

