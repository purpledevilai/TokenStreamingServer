import asyncio
import json
from pydantic import Field, BaseModel
from typing import List
from LLM.AgentTool import AgentTool
from Services import OutlookService


class modify_outlook_email_categories(BaseModel):
    """
    Set categories (colored tags) on an email. Categories in Outlook work similarly to Gmail labels - 
    an email can have multiple categories. This tool replaces all existing categories with the 
    provided list.
    
    Common preset category names:
    - 'Red category'
    - 'Orange category'  
    - 'Yellow category'
    - 'Green category'
    - 'Blue category'
    - 'Purple category'
    
    You can also use custom category names if they've been created in the user's Outlook.
    To remove all categories, pass an empty list.
    """
    integration_id: str = Field(description="The Outlook integration ID to use for authentication.")
    message_id: str = Field(description="The message ID to modify.")
    categories: List[str] = Field(
        description="List of category names to set on the email. Pass an empty list [] to remove all categories."
    )


def modify_outlook_email_categories_func(integration_id: str, message_id: str, categories: List[str]) -> str:
    """
    Set categories on an email.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID
        categories: List of category names to set
        
    Returns:
        JSON string with category update confirmation
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not message_id:
        raise Exception("message_id is required.")
    if categories is None:
        raise Exception("categories is required (can be an empty list).")
    
    result = OutlookService.update_message_categories(integration_id, message_id, categories)
    
    return json.dumps({
        "status": "success",
        "message_id": result.get("id"),
        "categories": result.get("categories", []),
    }, indent=2)


async def modify_outlook_email_categories_func_async(integration_id: str, message_id: str, categories: List[str]) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: modify_outlook_email_categories_func(integration_id, message_id, categories)
    )


modify_outlook_email_categories_tool = AgentTool(params=modify_outlook_email_categories, function=modify_outlook_email_categories_func_async, pass_context=False)

