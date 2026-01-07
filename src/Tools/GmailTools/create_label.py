import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GmailService


class create_label(BaseModel):
    """
    Create a new custom label in the connected Gmail account. Labels can be used to organize
    and categorize emails.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    name: str = Field(description="The display name for the new label.")
    label_list_visibility: Optional[str] = Field(
        default="labelShow",
        description="Visibility in the label list: 'labelShow' (always visible), 'labelShowIfUnread' (visible if has unread), or 'labelHide' (hidden)."
    )
    message_list_visibility: Optional[str] = Field(
        default="show",
        description="Visibility in the message list: 'show' or 'hide'."
    )


def create_label_func(integration_id: str, name: str, label_list_visibility: str = "labelShow", message_list_visibility: str = "show") -> str:
    """
    Create a new label.
    
    Args:
        integration_id: The Gmail integration ID
        name: The label name
        label_list_visibility: Visibility in label list
        message_list_visibility: Visibility in message list
        
    Returns:
        JSON string with created label details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not name:
        raise Exception("name is required.")
    
    result = GmailService.create_label(integration_id, name, label_list_visibility, message_list_visibility)
    
    return json.dumps({
        "status": "created",
        "label_id": result.get("id"),
        "name": result.get("name"),
        "type": result.get("type"),
        "label_list_visibility": result.get("labelListVisibility"),
        "message_list_visibility": result.get("messageListVisibility"),
    }, indent=2)


async def create_label_func_async(integration_id: str, name: str, label_list_visibility: str = "labelShow", message_list_visibility: str = "show") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: create_label_func(integration_id, name, label_list_visibility, message_list_visibility)
    )


create_label_tool = AgentTool(params=create_label, function=create_label_func_async, pass_context=False)

