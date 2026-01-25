import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GoogleCalendarService


class get_calendar_event(BaseModel):
    """
    Get the full details of a specific calendar event by its event ID. Returns complete event 
    information including title, description, start/end times, location, attendees, and organizer.
    """
    integration_id: str = Field(description="The Google Calendar integration ID to use for authentication.")
    event_id: str = Field(description="The unique ID of the calendar event to retrieve.")
    calendar_id: Optional[str] = Field(
        default="primary",
        description="The calendar ID the event belongs to. Use 'primary' for the user's main calendar. "
                    "For other calendars, use the FULL calendar ID including the domain "
                    "(e.g., 'abc123@group.calendar.google.com'), not just the hash portion."
    )


def get_calendar_event_func(integration_id: str, event_id: str, calendar_id: str = "primary") -> str:
    """
    Get the full details of a specific calendar event.
    
    Args:
        integration_id: The Google Calendar integration ID
        event_id: The event ID
        calendar_id: The calendar ID (default "primary")
        
    Returns:
        JSON string with full event details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not event_id:
        raise Exception("event_id is required.")
    
    # Get full event
    event = GoogleCalendarService.get_event(integration_id, event_id, calendar_id=calendar_id)
    
    # Format event with all details
    event_data = GoogleCalendarService.format_event_summary(event)
    
    # Add additional fields not in summary
    event_data["recurrence"] = event.get("recurrence")
    event_data["recurring_event_id"] = event.get("recurringEventId")
    event_data["visibility"] = event.get("visibility")
    event_data["conference_data"] = event.get("conferenceData")
    event_data["reminders"] = event.get("reminders")
    event_data["attachments"] = event.get("attachments")
    
    return json.dumps(event_data, indent=2)


async def get_calendar_event_func_async(integration_id: str, event_id: str, calendar_id: str = "primary") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_calendar_event_func(integration_id, event_id, calendar_id)
    )


get_calendar_event_tool = AgentTool(params=get_calendar_event, function=get_calendar_event_func_async, pass_context=False)

