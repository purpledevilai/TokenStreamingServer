import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional, List
from LLM.AgentTool import AgentTool
from Services import GmailService


class modify_email_labels(BaseModel):
    """
    Add or remove labels from an email. Use this to organize emails by applying custom labels
    or system labels. Use list_labels to get available label IDs.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    message_id: str = Field(description="The unique ID of the email message to modify.")
    add_labels: Optional[List[str]] = Field(
        default=None,
        description="List of label IDs to add to the email. Can include system labels like 'STARRED' or custom label IDs."
    )
    remove_labels: Optional[List[str]] = Field(
        default=None,
        description="List of label IDs to remove from the email. Can include system labels like 'INBOX' (to archive) or custom label IDs."
    )


def modify_email_labels_func(integration_id: str, message_id: str, add_labels: List[str] = None, remove_labels: List[str] = None) -> str:
    """
    Modify labels on an email.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID
        add_labels: Labels to add
        remove_labels: Labels to remove
        
    Returns:
        JSON string with updated label information
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    if not add_labels and not remove_labels:
        raise Exception("At least one of add_labels or remove_labels is required.")
    
    result = GmailService.modify_message(integration_id, message_id, add_labels=add_labels, remove_labels=remove_labels)
    
    return json.dumps({
        "status": "success",
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
        "labels_added": add_labels or [],
        "labels_removed": remove_labels or [],
        "current_labels": result.get("labelIds", []),
    }, indent=2)


async def modify_email_labels_func_async(integration_id: str, message_id: str, add_labels: List[str] = None, remove_labels: List[str] = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: modify_email_labels_func(integration_id, message_id, add_labels, remove_labels)
    )


modify_email_labels_tool = AgentTool(params=modify_email_labels, function=modify_email_labels_func_async, pass_context=False)

