import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class list_outlook_folders(BaseModel):
    """
    List all mail folders in the Outlook account, including system folders (Inbox, Sent Items, etc.) 
    and user-created folders. This is similar to Gmail's list_labels but Outlook uses a folder-based 
    system where each email exists in exactly one folder.
    
    Common system folders:
    - Inbox: Main inbox
    - Drafts: Draft messages
    - Sent Items: Sent messages
    - Deleted Items: Trash/deleted messages
    - Junk Email: Spam folder
    - Archive: Archived messages
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")


def list_outlook_folders_func(integration_id: str) -> str:
    """
    List all mail folders.
    
    Args:
        integration_id: The Outlook integration ID
        
    Returns:
        JSON string with list of folders
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    result = OutlookService.list_folders(integration_id)
    folders = result.get("value", [])
    
    # Separate system folders from user folders
    system_folders = []
    user_folders = []
    
    # Well-known folder IDs that are typically system folders
    system_folder_patterns = [
        "inbox", "drafts", "sentitems", "deleteditems", 
        "junkemail", "archive", "outbox", "clutter"
    ]
    
    for folder in folders:
        folder_info = {
            "id": folder.get("id"),
            "name": folder.get("displayName"),
            "parent_folder_id": folder.get("parentFolderId"),
            "unread_count": folder.get("unreadItemCount", 0),
            "total_count": folder.get("totalItemCount", 0),
        }
        
        # Check if it's a system folder based on the display name
        display_name_lower = folder.get("displayName", "").lower().replace(" ", "")
        is_system = any(pattern in display_name_lower for pattern in system_folder_patterns)
        
        if is_system:
            folder_info["type"] = "system"
            system_folders.append(folder_info)
        else:
            folder_info["type"] = "user"
            user_folders.append(folder_info)
    
    return json.dumps({
        "system_folders": system_folders,
        "user_folders": user_folders,
        "total_count": len(folders),
    }, indent=2)


async def list_outlook_folders_func_async(integration_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: list_outlook_folders_func(integration_id)
    )


list_outlook_folders_tool = AgentTool(params=list_outlook_folders, function=list_outlook_folders_func_async, pass_context=False)

