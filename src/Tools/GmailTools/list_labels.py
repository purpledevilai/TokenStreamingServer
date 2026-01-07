import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GmailService


class list_labels(BaseModel):
    """
    List all labels in the connected Gmail account. Returns both system labels (like INBOX, 
    SENT, TRASH) and user-created labels with their IDs and properties.
    """
    integration_id: str = Field(description="The Gmail integration ID to use for authentication.")


def list_labels_func(integration_id: str) -> str:
    """
    List all labels in the mailbox.
    
    Args:
        integration_id: The Gmail integration ID
        
    Returns:
        JSON string with list of labels
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    result = GmailService.get_labels(integration_id)
    labels = result.get("labels", [])
    
    # Categorize labels
    system_labels = []
    user_labels = []
    
    for label in labels:
        label_info = {
            "id": label.get("id"),
            "name": label.get("name"),
            "type": label.get("type"),
        }
        
        if label.get("type") == "system":
            system_labels.append(label_info)
        else:
            user_labels.append(label_info)
    
    return json.dumps({
        "system_labels": system_labels,
        "user_labels": user_labels,
        "total_count": len(labels),
    }, indent=2)


async def list_labels_func_async(integration_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: list_labels_func(integration_id)
    )


list_labels_tool = AgentTool(params=list_labels, function=list_labels_func_async, pass_context=False)

