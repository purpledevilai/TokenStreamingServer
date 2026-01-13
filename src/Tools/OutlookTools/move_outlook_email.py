import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class move_outlook_email(BaseModel):
    """
    Move an email to a different folder. Unlike Gmail's label system where an email can have 
    multiple labels, Outlook emails exist in exactly one folder at a time.
    
    Common destination folders:
    - 'inbox' - Move to Inbox
    - 'archive' - Archive the email
    - 'deleteditems' - Move to Trash
    - 'junkemail' - Mark as Spam
    - Or use a custom folder ID from list_outlook_folders
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    message_id: str = Field(description="The message ID to move.")
    destination_folder: str = Field(
        description="Destination folder ID or well-known name ('inbox', 'archive', 'deleteditems', 'junkemail', etc.)."
    )


def move_outlook_email_func(integration_id: str, message_id: str, destination_folder: str) -> str:
    """
    Move an email to a different folder.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID to move
        destination_folder: Destination folder ID or well-known name
        
    Returns:
        JSON string with move confirmation
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    if not destination_folder:
        raise Exception("destination_folder is required.")
    
    # Convert well-known folder names to proper IDs
    folder_id = OutlookService.get_well_known_folder_id(destination_folder)
    
    result = OutlookService.move_message(integration_id, message_id, folder_id)
    
    return json.dumps({
        "status": "moved",
        "message_id": result.get("id"),
        "destination_folder": destination_folder,
        "new_parent_folder_id": result.get("parentFolderId"),
    }, indent=2)


async def move_outlook_email_func_async(integration_id: str, message_id: str, destination_folder: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: move_outlook_email_func(integration_id, message_id, destination_folder)
    )


move_outlook_email_tool = AgentTool(params=move_outlook_email, function=move_outlook_email_func_async, pass_context=False)

