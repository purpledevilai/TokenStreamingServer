import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import OutlookService


class create_outlook_folder(BaseModel):
    """
    Create a new custom mail folder. You can create a top-level folder or a subfolder 
    within an existing folder.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    name: str = Field(description="Display name for the new folder.")
    parent_folder_id: Optional[str] = Field(
        default=None,
        description="Optional parent folder ID to create a subfolder. Leave empty for a top-level folder."
    )


def create_outlook_folder_func(integration_id: str, name: str, parent_folder_id: str = None) -> str:
    """
    Create a new mail folder.
    
    Args:
        integration_id: The Outlook integration ID
        name: Display name for the folder
        parent_folder_id: Optional parent folder ID for subfolders
        
    Returns:
        JSON string with created folder details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not name:
        raise Exception("name is required.")
    
    result = OutlookService.create_folder(integration_id, name, parent_folder_id)
    
    return json.dumps({
        "status": "created",
        "folder_id": result.get("id"),
        "name": result.get("displayName"),
        "parent_folder_id": result.get("parentFolderId"),
    }, indent=2)


async def create_outlook_folder_func_async(integration_id: str, name: str, parent_folder_id: str = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: create_outlook_folder_func(integration_id, name, parent_folder_id)
    )


create_outlook_folder_tool = AgentTool(params=create_outlook_folder, function=create_outlook_folder_func_async, pass_context=False)

