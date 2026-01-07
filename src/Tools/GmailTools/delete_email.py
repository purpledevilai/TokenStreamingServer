import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class delete_email(BaseModel):
    """
    Permanently delete an email. WARNING: This action is irreversible - the email cannot 
    be recovered. Consider using trash_email instead for a safer option that allows recovery.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    message_id: str = Field(description="The unique ID of the email message to permanently delete.")


def delete_email_func(integration_id: str, message_id: str) -> str:
    """
    Permanently delete an email.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID to permanently delete
        
    Returns:
        JSON string confirming the deletion
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    GmailService.delete_message(integration_id, message_id)
    
    return json.dumps({
        "status": "permanently_deleted",
        "message_id": message_id,
        "warning": "This action is irreversible. The email has been permanently deleted.",
    }, indent=2)


async def delete_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: delete_email_func(integration_id, message_id)
    )


delete_email_tool = AgentTool(params=delete_email, function=delete_email_func_async, pass_context=False)

