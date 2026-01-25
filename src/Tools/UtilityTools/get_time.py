import asyncio
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool


class get_time(BaseModel):
    """
    Retrieve the current time. Returns UTC time by default, or the time in a specified timezone.
    Use this tool when you need to know the current date and/or time for scheduling, 
    time-sensitive operations, or providing time-aware responses.
    """
    timezone: Optional[str] = Field(
        default=None,
        description="Optional timezone name (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo'). "
                    "If not provided, returns UTC time. Use standard IANA timezone names."
    )


def get_time_func(timezone: Optional[str] = None, context: dict = None) -> str:
    try:
        if timezone:
            try:
                tz = ZoneInfo(timezone)
                current_time = datetime.now(tz)
                tz_label = timezone
            except Exception:
                return f"Error: Invalid timezone '{timezone}'. Please use a valid IANA timezone name (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo')."
        else:
            tz = ZoneInfo("UTC")
            current_time = datetime.now(tz)
            tz_label = "UTC"
        
        # Format the time in a readable way
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
        day_of_week = current_time.strftime("%A")
        
        return f"Current time ({tz_label}): {formatted_time} ({day_of_week})"
    
    except Exception as e:
        return f"Error retrieving time: {str(e)}"


async def get_time_func_async(timezone: Optional[str] = None, context: dict = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_time_func(timezone, context)
    )


get_time_tool = AgentTool(params=get_time, function=get_time_func_async, pass_context=False)

