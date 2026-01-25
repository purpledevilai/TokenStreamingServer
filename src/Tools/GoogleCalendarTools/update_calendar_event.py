import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional, List
from LLM.AgentTool import AgentTool
from Services import GoogleCalendarService


class update_calendar_event(BaseModel):
    """
    Update an existing calendar event. Only the fields you provide will be updated; 
    other fields will remain unchanged.
    
    Time format examples (RFC3339 for timed events):
    - With timezone offset: '2026-01-25T10:00:00-05:00'
    - With UTC: '2026-01-25T15:00:00Z'
    
    Date format for all-day events:
    - Simple date: '2026-01-25' (YYYY-MM-DD)
    
    Note: When changing between timed and all-day events, provide both start_time and end_time
    with the appropriate format, and set all_day accordingly.
    
    Recurrence examples (RRULE format):
    - Daily: ['RRULE:FREQ=DAILY']
    - Weekly on Mon/Wed/Fri: ['RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR']
    - Every 2 weeks: ['RRULE:FREQ=WEEKLY;INTERVAL=2']
    - Remove recurrence: [] (empty list)
    
    Note: To update a recurring event series, use the recurring event ID (not an instance ID).
    """
    integration_id: str = Field(description="The Google Calendar integration ID to use for authentication.")
    event_id: str = Field(description="The unique ID of the event to update. For recurring events, use the series ID to update all instances.")
    calendar_id: Optional[str] = Field(
        default="primary",
        description="The calendar ID the event belongs to. Use 'primary' for the user's main calendar. "
                    "For other calendars, use the FULL calendar ID including the domain "
                    "(e.g., 'abc123@group.calendar.google.com'), not just the hash portion."
    )
    summary: Optional[str] = Field(
        default=None,
        description="New title/summary for the event."
    )
    start_time: Optional[str] = Field(
        default=None,
        description="New start time in RFC3339 format or date for all-day events."
    )
    end_time: Optional[str] = Field(
        default=None,
        description="New end time in RFC3339 format or date for all-day events."
    )
    description: Optional[str] = Field(
        default=None,
        description="New description for the event."
    )
    location: Optional[str] = Field(
        default=None,
        description="New location for the event."
    )
    attendees: Optional[List[str]] = Field(
        default=None,
        description="New list of attendee email addresses. This replaces the existing attendee list."
    )
    timezone: Optional[str] = Field(
        default=None,
        description="Timezone for the event times (e.g., 'America/New_York')."
    )
    all_day: Optional[bool] = Field(
        default=None,
        description="Set to True if updating to an all-day event, False for timed event."
    )
    recurrence: Optional[List[str]] = Field(
        default=None,
        description="List of RRULE strings for recurring events. Set to empty list [] to remove recurrence. "
                    "Common patterns: 'RRULE:FREQ=DAILY', 'RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR', "
                    "'RRULE:FREQ=MONTHLY;BYMONTHDAY=15', 'RRULE:FREQ=WEEKLY;COUNT=10'."
    )


def update_calendar_event_func(
    integration_id: str,
    event_id: str,
    calendar_id: str = "primary",
    summary: str = None,
    start_time: str = None,
    end_time: str = None,
    description: str = None,
    location: str = None,
    attendees: List[str] = None,
    timezone: str = None,
    all_day: bool = None,
    recurrence: List[str] = None
) -> str:
    """
    Update an existing calendar event.
    
    Args:
        integration_id: The Google Calendar integration ID
        event_id: The event ID to update
        calendar_id: The calendar ID (default "primary")
        summary: New event title
        start_time: New start time
        end_time: New end time
        description: New event description
        location: New event location
        attendees: New list of attendee emails
        timezone: Event timezone
        all_day: Whether this is an all-day event
        recurrence: List of RRULE strings (empty list removes recurrence)
        
    Returns:
        JSON string with updated event details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not event_id:
        raise Exception("event_id is required.")
    
    result = GoogleCalendarService.update_event(
        integration_id,
        event_id=event_id,
        calendar_id=calendar_id,
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        description=description,
        location=location,
        attendees=attendees,
        timezone=timezone,
        all_day=all_day,
        recurrence=recurrence
    )
    
    response = {
        "status": "updated",
        "event_id": result.get("id"),
        "summary": result.get("summary"),
        "html_link": result.get("htmlLink"),
        "start": result.get("start"),
        "end": result.get("end"),
        "updated": result.get("updated"),
    }
    
    if result.get("recurrence"):
        response["recurrence"] = result.get("recurrence")
        response["is_recurring"] = True
    
    return json.dumps(response, indent=2)


async def update_calendar_event_func_async(
    integration_id: str,
    event_id: str,
    calendar_id: str = "primary",
    summary: str = None,
    start_time: str = None,
    end_time: str = None,
    description: str = None,
    location: str = None,
    attendees: List[str] = None,
    timezone: str = None,
    all_day: bool = None,
    recurrence: List[str] = None
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: update_calendar_event_func(
            integration_id, event_id, calendar_id, summary, start_time,
            end_time, description, location, attendees, timezone, all_day, recurrence
        )
    )


update_calendar_event_tool = AgentTool(params=update_calendar_event, function=update_calendar_event_func_async, pass_context=False)

