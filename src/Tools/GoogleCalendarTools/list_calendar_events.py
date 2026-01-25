import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GoogleCalendarService


class list_calendar_events(BaseModel):
    """
    List events from a Google Calendar. Returns a list of event summaries including title, 
    start/end times, location, and attendees. Use time_min and time_max to filter by date range.
    
    Time format examples (RFC3339):
    - With timezone offset: '2026-01-25T10:00:00-05:00' (Eastern Time)
    - With UTC: '2026-01-25T15:00:00Z'
    - For all-day queries, use start of day: '2026-01-25T00:00:00Z'
    
    Query examples:
    - Search by keyword: 'meeting' (searches event titles and descriptions)
    - Search by person: 'john@example.com'
    
    Common use cases:
    - Today's events: Set time_min to start of today, time_max to end of today
    - This week: Set time_min to today, time_max to 7 days from now
    - Upcoming events: Set time_min to now (no time_max needed)
    """
    integration_id: str = Field(description="The Google Calendar integration ID to use for authentication.")
    calendar_id: Optional[str] = Field(
        default="primary",
        description="The calendar ID the event belongs to. Use 'primary' for the user's main calendar. "
                    "For other calendars, use the FULL calendar ID including the domain "
                    "(e.g., 'abc123@group.calendar.google.com'), not just the hash portion."
    )
    time_min: Optional[str] = Field(
        default=None,
        description="Lower bound (inclusive) for event start time in RFC3339 format. Example: '2026-01-25T00:00:00Z'"
    )
    time_max: Optional[str] = Field(
        default=None,
        description="Upper bound (exclusive) for event start time in RFC3339 format. Example: '2026-01-31T23:59:59Z'"
    )
    query: Optional[str] = Field(
        default=None,
        description="Free text search query to filter events by title, description, location, or attendee."
    )
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of events to return (default 10, max 250)."
    )


def list_calendar_events_func(
    integration_id: str,
    calendar_id: str = "primary",
    time_min: str = None,
    time_max: str = None,
    query: str = None,
    max_results: int = 10
) -> str:
    """
    List events from a Google Calendar.
    
    Args:
        integration_id: The Google Calendar integration ID
        calendar_id: The calendar ID (default "primary")
        time_min: Lower bound for event start time (RFC3339)
        time_max: Upper bound for event start time (RFC3339)
        query: Free text search query
        max_results: Maximum number of results
        
    Returns:
        JSON string with list of event summaries
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    if max_results > 250:
        max_results = 250
    
    # Get list of events
    result = GoogleCalendarService.list_events(
        integration_id,
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
        query=query,
        max_results=max_results
    )
    
    events = result.get("items", [])
    
    if not events:
        return json.dumps({"events": [], "count": 0})
    
    # Format events into summaries
    event_summaries = []
    for event in events:
        event_summaries.append(GoogleCalendarService.format_event_summary(event))
    
    return json.dumps({
        "events": event_summaries,
        "count": len(event_summaries),
        "calendar_id": calendar_id,
        "time_zone": result.get("timeZone"),
    }, indent=2)


async def list_calendar_events_func_async(
    integration_id: str,
    calendar_id: str = "primary",
    time_min: str = None,
    time_max: str = None,
    query: str = None,
    max_results: int = 10
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: list_calendar_events_func(integration_id, calendar_id, time_min, time_max, query, max_results)
    )


list_calendar_events_tool = AgentTool(params=list_calendar_events, function=list_calendar_events_func_async, pass_context=False)

