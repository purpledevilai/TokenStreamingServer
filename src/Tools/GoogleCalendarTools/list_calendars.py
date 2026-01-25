import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional
from LLM.AgentTool import AgentTool
from Services import GoogleCalendarService


class list_calendars(BaseModel):
    """
    List all calendars accessible to the user. Returns calendar names, IDs, and access roles.
    
    Common calendar types:
    - Primary calendar: The user's main calendar (ID is usually their email address)
    - Secondary calendars: User-created additional calendars
    - Subscribed calendars: Calendars shared by others or public calendars
    
    Use the calendar_id from this list when working with events on non-primary calendars.
    The 'primary' shortcut can always be used for the user's main calendar.
    """
    integration_id: str = Field(description="The Google Calendar integration ID to use for authentication.")
    max_results: Optional[int] = Field(
        default=100,
        description="Maximum number of calendars to return (default 100)."
    )


def list_calendars_func(integration_id: str, max_results: int = 100) -> str:
    """
    List all calendars accessible to the user.
    
    Args:
        integration_id: The Google Calendar integration ID
        max_results: Maximum number of results
        
    Returns:
        JSON string with list of calendar summaries
    """
    if not integration_id:
        raise Exception("integration_id is required.")
    
    result = GoogleCalendarService.list_calendars(integration_id, max_results=max_results)
    
    calendars = result.get("items", [])
    
    if not calendars:
        return json.dumps({"calendars": [], "count": 0})
    
    # Format calendars into summaries
    calendar_summaries = []
    for cal in calendars:
        calendar_summaries.append({
            "id": cal.get("id"),
            "summary": cal.get("summary"),
            "description": cal.get("description"),
            "primary": cal.get("primary", False),
            "access_role": cal.get("accessRole"),
            "background_color": cal.get("backgroundColor"),
            "foreground_color": cal.get("foregroundColor"),
            "selected": cal.get("selected", False),
            "time_zone": cal.get("timeZone"),
        })
    
    return json.dumps({
        "calendars": calendar_summaries,
        "count": len(calendar_summaries),
    }, indent=2)


async def list_calendars_func_async(integration_id: str, max_results: int = 100) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: list_calendars_func(integration_id, max_results)
    )


list_calendars_tool = AgentTool(params=list_calendars, function=list_calendars_func_async, pass_context=False)

