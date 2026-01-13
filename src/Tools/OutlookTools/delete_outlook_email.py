import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import OutlookService


class delete_outlook_email(BaseModel):
    """
    ⚠️ WARNING: Permanently delete an email. This action is irreversible.
    
    Consider using trash_outlook_email instead, which allows recovery from the Deleted Items folder.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    message_id: str = Field(description="The message ID to permanently delete.")


def delete_outlook_email_func(integration_id: str, message_id: str) -> str:
    """
    Permanently delete an email.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID to permanently delete
        
    Returns:
        JSON string confirming deletion
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    OutlookService.delete_message(integration_id, message_id)
    
    return json.dumps({
        "status": "permanently_deleted",
        "message_id": message_id,
        "warning": "This action is irreversible. The email has been permanently deleted.",
    }, indent=2)


async def delete_outlook_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: delete_outlook_email_func(integration_id, message_id)
    )


delete_outlook_email_tool = AgentTool(params=delete_outlook_email, function=delete_outlook_email_func_async, pass_context=False)

