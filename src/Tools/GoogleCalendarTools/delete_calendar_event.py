import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GoogleCalendarService


class delete_calendar_event(BaseModel):
    """
    Delete a calendar event permanently. This action cannot be undone.
    
    Note: For recurring events, this will delete only the specified instance. 
    To delete all instances of a recurring event, you would need to delete each instance 
    or the original recurring event.
    """
    integration_id: str = Field(description="The Google Calendar integration ID to use for authentication.")
    event_id: str = Field(description="The unique ID of the event to delete.")
    calendar_id: Optional[str] = Field(
        default="primary",
        description="The calendar ID the event belongs to. Use 'primary' for the user's main calendar. "
                    "For other calendars, use the FULL calendar ID including the domain "
                    "(e.g., 'abc123@group.calendar.google.com'), not just the hash portion."
    )


def delete_calendar_event_func(integration_id: str, event_id: str, calendar_id: str = "primary") -> str:
    """
    Delete a calendar event.
    
    Args:
        integration_id: The Google Calendar integration ID
        event_id: The event ID to delete
        calendar_id: The calendar ID (default "primary")
        
    Returns:
        JSON string confirming deletion
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not event_id:
        raise Exception("event_id is required.")
    
    GoogleCalendarService.delete_event(integration_id, event_id, calendar_id=calendar_id)
    
    return json.dumps({
        "status": "deleted",
        "event_id": event_id,
        "calendar_id": calendar_id,
    }, indent=2)


async def delete_calendar_event_func_async(integration_id: str, event_id: str, calendar_id: str = "primary") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: delete_calendar_event_func(integration_id, event_id, calendar_id)
    )


delete_calendar_event_tool = AgentTool(params=delete_calendar_event, function=delete_calendar_event_func_async, pass_context=False)

