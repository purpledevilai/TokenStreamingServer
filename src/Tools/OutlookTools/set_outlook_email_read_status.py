import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class set_outlook_email_read_status(BaseModel):
    """
    Mark an email as read or unread using a single boolean parameter.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    message_id: str = Field(description="The message ID to modify.")
    mark_as_read: bool = Field(description="`true` to mark as read, `false` to mark as unread.")


def set_outlook_email_read_status_func(integration_id: str, message_id: str, mark_as_read: bool) -> str:
    """
    Set the read status of an email.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID
        mark_as_read: True to mark as read, False to mark as unread
        
    Returns:
        JSON string with status confirmation
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = OutlookService.update_message(integration_id, message_id, {"isRead": mark_as_read})
    
    action = "marked_as_read" if mark_as_read else "marked_as_unread"
    
    return json.dumps({
        "status": "success",
        "message_id": result.get("id"),
        "action": action,
        "is_read": result.get("isRead"),
    }, indent=2)


async def set_outlook_email_read_status_func_async(integration_id: str, message_id: str, mark_as_read: bool) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: set_outlook_email_read_status_func(integration_id, message_id, mark_as_read)
    )


set_outlook_email_read_status_tool = AgentTool(params=set_outlook_email_read_status, function=set_outlook_email_read_status_func_async, pass_context=False)

