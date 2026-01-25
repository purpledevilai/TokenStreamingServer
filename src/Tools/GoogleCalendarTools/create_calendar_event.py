import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional, List
from LLM.AgentTool import AgentTool
from Services import GoogleCalendarService


class create_calendar_event(BaseModel):
    """
    Create a new event in Google Calendar. Supports timed events, all-day events, and recurring events.
    
    Time format examples (RFC3339 for timed events):
    - With timezone offset: '2026-01-25T10:00:00-05:00' (Eastern Time)
    - With UTC: '2026-01-25T15:00:00Z'
    
    Date format for all-day events:
    - Simple date: '2026-01-25' (YYYY-MM-DD)
    
    Examples:
    - 1-hour meeting: start='2026-01-25T10:00:00Z', end='2026-01-25T11:00:00Z', all_day=False
    - All-day event: start='2026-01-25', end='2026-01-26', all_day=True (end date is exclusive)
    - Multi-day event: start='2026-01-25', end='2026-01-28', all_day=True (3 days)
    
    Recurrence examples (RRULE format):
    - Daily: ['RRULE:FREQ=DAILY']
    - Every weekday: ['RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR']
    - Weekly on Monday & Wednesday: ['RRULE:FREQ=WEEKLY;BYDAY=MO,WE']
    - Every 2 weeks: ['RRULE:FREQ=WEEKLY;INTERVAL=2']
    - Monthly on the 15th: ['RRULE:FREQ=MONTHLY;BYMONTHDAY=15']
    - Weekly for 10 occurrences: ['RRULE:FREQ=WEEKLY;COUNT=10']
    - Daily until a date: ['RRULE:FREQ=DAILY;UNTIL=20260331T000000Z']
    """
    integration_id: str = Field(description="The Google Calendar integration ID to use for authentication.")
    summary: str = Field(description="The title/summary of the event.")
    start_time: str = Field(
        description="Start time in RFC3339 format (e.g., '2026-01-25T10:00:00Z') or date for all-day events (e.g., '2026-01-25')."
    )
    end_time: str = Field(
        description="End time in RFC3339 format (e.g., '2026-01-25T11:00:00Z') or date for all-day events (e.g., '2026-01-26'). For all-day events, end date is exclusive."
    )
    calendar_id: Optional[str] = Field(
        default="primary",
        description="The calendar ID the event belongs to. Use 'primary' for the user's main calendar. "
                    "For other calendars, use the FULL calendar ID including the domain "
                    "(e.g., 'abc123@group.calendar.google.com'), not just the hash portion."
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed description of the event."
    )
    location: Optional[str] = Field(
        default=None,
        description="Location of the event (address or place name)."
    )
    attendees: Optional[List[str]] = Field(
        default=None,
        description="List of attendee email addresses to invite to the event."
    )
    timezone: Optional[str] = Field(
        default=None,
        description="Timezone for the event (e.g., 'America/New_York', 'Europe/London'). If not set, uses calendar's default timezone."
    )
    all_day: Optional[bool] = Field(
        default=False,
        description="Set to True for all-day events. When True, use date format (YYYY-MM-DD) for start_time and end_time."
    )
    recurrence: Optional[List[str]] = Field(
        default=None,
        description="List of RRULE strings for recurring events. Common patterns: "
                    "'RRULE:FREQ=DAILY' (daily), "
                    "'RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR' (Mon/Wed/Fri), "
                    "'RRULE:FREQ=WEEKLY;INTERVAL=2' (every 2 weeks), "
                    "'RRULE:FREQ=MONTHLY;BYMONTHDAY=15' (15th of month), "
                    "'RRULE:FREQ=WEEKLY;COUNT=10' (10 occurrences), "
                    "'RRULE:FREQ=DAILY;UNTIL=20260331T000000Z' (until date)."
    )


def create_calendar_event_func(
    integration_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str = "primary",
    description: str = None,
    location: str = None,
    attendees: List[str] = None,
    timezone: str = None,
    all_day: bool = False,
    recurrence: List[str] = None
) -> str:
    """
    Create a new calendar event.
    
    Args:
        integration_id: The Google Calendar integration ID
        summary: Event title
        start_time: Start time (RFC3339 or date)
        end_time: End time (RFC3339 or date)
        calendar_id: The calendar ID (default "primary")
        description: Event description
        location: Event location
        attendees: List of attendee emails
        timezone: Event timezone
        all_day: Whether this is an all-day event
        recurrence: List of RRULE strings for recurring events
        
    Returns:
        JSON string with created event details
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    if not summary:
        raise Exception("summary (event title) is required.")
    if not start_time:
        raise Exception("start_time is required.")
    if not end_time:
        raise Exception("end_time is required.")
    
    result = GoogleCalendarService.create_event(
        integration_id,
        summary=summary,
        start_time=start_time,
        end_time=end_time,
        calendar_id=calendar_id,
        description=description,
        location=location,
        attendees=attendees,
        timezone=timezone,
        all_day=all_day,
        recurrence=recurrence
    )
    
    response = {
        "status": "created",
        "event_id": result.get("id"),
        "summary": result.get("summary"),
        "html_link": result.get("htmlLink"),
        "start": result.get("start"),
        "end": result.get("end"),
        "attendees_count": len(result.get("attendees", [])),
    }
    
    if result.get("recurrence"):
        response["recurrence"] = result.get("recurrence")
        response["is_recurring"] = True
    
    return json.dumps(response, indent=2)


async def create_calendar_event_func_async(
    integration_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str = "primary",
    description: str = None,
    location: str = None,
    attendees: List[str] = None,
    timezone: str = None,
    all_day: bool = False,
    recurrence: List[str] = None
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: create_calendar_event_func(
            integration_id, summary, start_time, end_time, calendar_id,
            description, location, attendees, timezone, all_day, recurrence
        )
    )


create_calendar_event_tool = AgentTool(params=create_calendar_event, function=create_calendar_event_func_async, pass_context=False)

