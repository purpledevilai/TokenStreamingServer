import os
import time
import requests
from AWS.CloudWatchLogs import get_logger
from Models import Integration

logger = get_logger(log_level=os.environ.get("LOG_LEVEL", "INFO"))

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


def _get_calendar_integration_by_id(integration_id: str) -> Integration.Integration:
    """Get a Google Calendar integration by its ID."""
    integration = Integration.get_integration(integration_id)
    if integration.type != "google_calendar":
        raise Exception(f"Integration {integration_id} is not a Google Calendar integration", 400)
    return integration


def _refresh_token(integration: Integration.Integration) -> Integration.Integration:
    """Refresh the access token using the refresh token."""
    refresh_token = integration.integration_config.get("refresh_token")
    if not refresh_token:
        raise Exception("No refresh token available", 400)
    
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": refresh_token,
    }
    resp = requests.post(GOOGLE_TOKEN_URL, data=payload)
    if resp.status_code != 200:
        logger.error(f"Failed to refresh Google Calendar token: {resp.text}")
        raise Exception("Failed to refresh Google Calendar token", resp.status_code)
    
    data = resp.json()
    integration.integration_config.update({
        "access_token": data["access_token"],
        "expires_in": data.get("expires_in"),
        "scope": data.get("scope"),
        "expires_at": int(time.time()) + data.get("expires_in", 0),
    })
    # Note: Google doesn't always return a new refresh_token
    if "refresh_token" in data:
        integration.integration_config["refresh_token"] = data["refresh_token"]
    
    Integration.save_integration(integration)
    return integration


def _ensure_token(integration: Integration.Integration) -> str:
    """Ensure the access token is valid, refreshing if necessary."""
    expires_at = integration.integration_config.get("expires_at")
    # Refresh if token expires in less than 60 seconds
    if expires_at and expires_at <= int(time.time()) + 60:
        integration = _refresh_token(integration)
    return integration.integration_config.get("access_token")


def calendar_api_request(integration_id: str, method: str, path: str, **kwargs):
    """Make an authenticated request to the Google Calendar API."""
    integration = _get_calendar_integration_by_id(integration_id)
    access_token = _ensure_token(integration)
    
    url = f"{CALENDAR_API_BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    })
    
    resp = requests.request(method, url, headers=headers, **kwargs)
    if resp.status_code >= 400:
        logger.error(f"Google Calendar API error: {resp.text}")
        raise Exception(f"Google Calendar API error: {resp.text}", resp.status_code)
    
    if resp.text:
        return resp.json()
    return {}


# ==================== Calendar List Functions ====================

def list_calendars(integration_id: str, max_results: int = 100):
    """
    List all calendars accessible by the user.
    
    Args:
        integration_id: The Google Calendar integration ID
        max_results: Maximum number of calendars to return (default 100)
    
    Returns:
        List of calendar metadata
    """
    params = {"maxResults": max_results}
    return calendar_api_request(integration_id, "GET", "/users/me/calendarList", params=params)


def get_calendar(integration_id: str, calendar_id: str = "primary"):
    """
    Get a specific calendar by ID.
    
    Args:
        integration_id: The Google Calendar integration ID
        calendar_id: The calendar ID (default "primary" for user's main calendar)
    
    Returns:
        Calendar metadata
    """
    return calendar_api_request(integration_id, "GET", f"/calendars/{calendar_id}")


# ==================== Event Functions ====================

def list_events(
    integration_id: str,
    calendar_id: str = "primary",
    time_min: str = None,
    time_max: str = None,
    query: str = None,
    max_results: int = 10,
    single_events: bool = True,
    order_by: str = "startTime"
):
    """
    List events from a calendar.
    
    Args:
        integration_id: The Google Calendar integration ID
        calendar_id: The calendar ID (default "primary")
        time_min: Lower bound for event start time (RFC3339 format)
        time_max: Upper bound for event start time (RFC3339 format)
        query: Free text search query
        max_results: Maximum number of events to return (default 10)
        single_events: Whether to expand recurring events (default True)
        order_by: Order by "startTime" or "updated" (default "startTime")
    
    Returns:
        List of event data
    """
    params = {
        "maxResults": max_results,
        "singleEvents": single_events,
        "orderBy": order_by,
    }
    if time_min:
        params["timeMin"] = time_min
    if time_max:
        params["timeMax"] = time_max
    if query:
        params["q"] = query
    
    return calendar_api_request(
        integration_id, 
        "GET", 
        f"/calendars/{calendar_id}/events", 
        params=params
    )


def get_event(integration_id: str, event_id: str, calendar_id: str = "primary"):
    """
    Get a specific event by ID.
    
    Args:
        integration_id: The Google Calendar integration ID
        event_id: The event ID
        calendar_id: The calendar ID (default "primary")
    
    Returns:
        Full event data
    """
    return calendar_api_request(
        integration_id, 
        "GET", 
        f"/calendars/{calendar_id}/events/{event_id}"
    )


def create_event(
    integration_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str = "primary",
    description: str = None,
    location: str = None,
    attendees: list = None,
    timezone: str = None,
    all_day: bool = False,
    recurrence: list = None
):
    """
    Create a new calendar event.
    
    Args:
        integration_id: The Google Calendar integration ID
        summary: Event title/summary
        start_time: Start time in RFC3339 format (or date for all-day events: YYYY-MM-DD)
        end_time: End time in RFC3339 format (or date for all-day events: YYYY-MM-DD)
        calendar_id: The calendar ID (default "primary")
        description: Event description (optional)
        location: Event location (optional)
        attendees: List of attendee email addresses (optional)
        timezone: Timezone for the event (optional, e.g., "America/New_York")
        all_day: Whether this is an all-day event (default False)
        recurrence: List of RRULE strings for recurring events (optional)
    
    Returns:
        Created event data
    """
    if all_day:
        event_body = {
            "summary": summary,
            "start": {"date": start_time},
            "end": {"date": end_time},
        }
    else:
        start_obj = {"dateTime": start_time}
        end_obj = {"dateTime": end_time}
        if timezone:
            start_obj["timeZone"] = timezone
            end_obj["timeZone"] = timezone
        event_body = {
            "summary": summary,
            "start": start_obj,
            "end": end_obj,
        }
    
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]
    if recurrence:
        event_body["recurrence"] = recurrence
    
    return calendar_api_request(
        integration_id,
        "POST",
        f"/calendars/{calendar_id}/events",
        json=event_body
    )


def update_event(
    integration_id: str,
    event_id: str,
    calendar_id: str = "primary",
    summary: str = None,
    start_time: str = None,
    end_time: str = None,
    description: str = None,
    location: str = None,
    attendees: list = None,
    timezone: str = None,
    all_day: bool = None,
    recurrence: list = None
):
    """
    Update an existing calendar event.
    
    Args:
        integration_id: The Google Calendar integration ID
        event_id: The event ID to update
        calendar_id: The calendar ID (default "primary")
        summary: New event title/summary (optional)
        start_time: New start time in RFC3339 format (optional)
        end_time: New end time in RFC3339 format (optional)
        description: New event description (optional)
        location: New event location (optional)
        attendees: New list of attendee email addresses (optional)
        timezone: Timezone for the event (optional)
        all_day: Whether this is an all-day event (optional)
        recurrence: List of RRULE strings for recurring events (optional, set to empty list to remove recurrence)
    
    Returns:
        Updated event data
    """
    event_body = {}
    
    if summary is not None:
        event_body["summary"] = summary
    if description is not None:
        event_body["description"] = description
    if location is not None:
        event_body["location"] = location
    if attendees is not None:
        event_body["attendees"] = [{"email": email} for email in attendees]
    if recurrence is not None:
        event_body["recurrence"] = recurrence
    
    # Handle time updates
    if start_time is not None:
        if all_day:
            event_body["start"] = {"date": start_time}
        else:
            start_obj = {"dateTime": start_time}
            if timezone:
                start_obj["timeZone"] = timezone
            event_body["start"] = start_obj
    
    if end_time is not None:
        if all_day:
            event_body["end"] = {"date": end_time}
        else:
            end_obj = {"dateTime": end_time}
            if timezone:
                end_obj["timeZone"] = timezone
            event_body["end"] = end_obj
    
    return calendar_api_request(
        integration_id,
        "PATCH",
        f"/calendars/{calendar_id}/events/{event_id}",
        json=event_body
    )


def delete_event(integration_id: str, event_id: str, calendar_id: str = "primary"):
    """
    Delete a calendar event.
    
    Args:
        integration_id: The Google Calendar integration ID
        event_id: The event ID to delete
        calendar_id: The calendar ID (default "primary")
    
    Returns:
        Empty dict on success
    """
    return calendar_api_request(
        integration_id,
        "DELETE",
        f"/calendars/{calendar_id}/events/{event_id}"
    )


# ==================== Helper Functions ====================

def parse_event_time(event: dict) -> dict:
    """
    Parse the start and end times from an event.
    
    Returns:
        Dict with start, end, and is_all_day fields
    """
    start = event.get("start", {})
    end = event.get("end", {})
    
    # Check if all-day event (has 'date' instead of 'dateTime')
    is_all_day = "date" in start
    
    return {
        "start": start.get("date") or start.get("dateTime"),
        "end": end.get("date") or end.get("dateTime"),
        "start_timezone": start.get("timeZone"),
        "end_timezone": end.get("timeZone"),
        "is_all_day": is_all_day,
    }


def format_event_summary(event: dict) -> dict:
    """
    Format an event into a summary dict with key fields.
    
    Returns:
        Dict with id, summary, start, end, location, etc.
    """
    time_info = parse_event_time(event)
    
    return {
        "id": event.get("id"),
        "summary": event.get("summary", "(No Title)"),
        "description": event.get("description"),
        "location": event.get("location"),
        "start": time_info["start"],
        "end": time_info["end"],
        "is_all_day": time_info["is_all_day"],
        "timezone": time_info["start_timezone"],
        "status": event.get("status"),
        "html_link": event.get("htmlLink"),
        "attendees": [
            {
                "email": a.get("email"),
                "response_status": a.get("responseStatus"),
                "display_name": a.get("displayName"),
            }
            for a in event.get("attendees", [])
        ],
        "organizer": event.get("organizer", {}).get("email"),
        "created": event.get("created"),
        "updated": event.get("updated"),
    }

