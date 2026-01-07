import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class archive_email(BaseModel):
    """
    Archive an email by removing it from the inbox. The email is not deleted and can still
    be found in 'All Mail' or by searching. This is equivalent to removing the INBOX label.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    message_id: str = Field(description="The unique ID of the email message to archive.")


def archive_email_func(integration_id: str, message_id: str) -> str:
    """
    Archive an email by removing the INBOX label.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID to archive
        
    Returns:
        JSON string confirming the action
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    
    result = GmailService.modify_message(integration_id, message_id, remove_labels=["INBOX"])
    
    return json.dumps({
        "status": "archived",
        "message_id": result.get("id"),
        "thread_id": result.get("threadId"),
        "labels": result.get("labelIds", []),
    }, indent=2)


async def archive_email_func_async(integration_id: str, message_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: archive_email_func(integration_id, message_id)
    )


archive_email_tool = AgentTool(params=archive_email, function=archive_email_func_async, pass_context=False)

