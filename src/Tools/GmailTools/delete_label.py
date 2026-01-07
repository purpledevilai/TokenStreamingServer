import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class delete_label(BaseModel):
    """
    Delete a custom label from the connected Gmail account. System labels (like INBOX, SENT, 
    TRASH) cannot be deleted. Use list_labels to get available label IDs.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")
    label_id: str = Field(description="The unique ID of the label to delete. System labels cannot be deleted.")


def delete_label_func(integration_id: str, label_id: str) -> str:
    """
    Delete a custom label.
    
    Args:
        integration_id: The Gmail integration ID
        label_id: The label ID to delete
        
    Returns:
        JSON string confirming deletion
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not label_id:
        raise Exception("label_id is required.")
    
    GmailService.delete_label(integration_id, label_id)
    
    return json.dumps({
        "status": "deleted",
        "label_id": label_id,
    }, indent=2)


async def delete_label_func_async(integration_id: str, label_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: delete_label_func(integration_id, label_id)
    )


delete_label_tool = AgentTool(params=delete_label, function=delete_label_func_async, pass_context=False)

