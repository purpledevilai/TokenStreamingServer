import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class set_email_read_status(BaseModel):
    """
    Set the read status of an email. Use this to mark an email as read or unread.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    message_id: str = Field(description="The unique ID of the email message to modify.")
    mark_as_read: bool = Field(description="Set to true to mark the email as read, false to mark it as unread.")


def set_email_read_status_func(integration_id: str, message_id: str, mark_as_read: bool) -> str:
    """
    Set the read status of an email.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID
        mark_as_read: True to mark as read, False to mark as unread
        
    Returns:
        JSON string confirming the action
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    if mark_as_read:
        result = GmailService.mark_as_read(integration_id, message_id)
        action = "marked_as_read"
    else:
        result = GmailService.mark_as_unread(integration_id, message_id)
        action = "marked_as_unread"
    
    return json.dumps({
        "status": "success",
        "message_id": result.get("id"),
        "action": action,
        "labels": result.get("labelIds", []),
    }, indent=2)


async def set_email_read_status_func_async(integration_id: str, message_id: str, mark_as_read: bool) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: set_email_read_status_func(integration_id, message_id, mark_as_read)
    )


set_email_read_status_tool = AgentTool(params=set_email_read_status, function=set_email_read_status_func_async, pass_context=False)

