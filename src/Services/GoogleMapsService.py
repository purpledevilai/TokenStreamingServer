import os
import requests
from typing import Optional, List
from AWS.CloudWatchLogs import get_logger

logger = get_logger(log_level=os.environ.get("LOG_LEVEL", "INFO"))

PLACES_API_BASE = "https://places.googleapis.com/v1"
ROUTES_API_BASE = "https://routes.googleapis.com"


def _get_api_key() -> str:
    """Get the Google Maps API key from environment variables."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise Exception("GOOGLE_MAPS_API_KEY environment variable is not set")
    return api_key


def _places_api_request(method: str, endpoint: str, field_mask: str = None, **kwargs) -> dict:
    """
    Make a request to the Google Places API.
    
    Args:
        method: HTTP method (GET, POST)
        endpoint: API endpoint path
        field_mask: Comma-separated list of fields to return
        **kwargs: Additional arguments to pass to requests
    
    Returns:
        JSON response as dict
    """
    api_key = _get_api_key()
    url = f"{PLACES_API_BASE}{endpoint}"
    
    headers = kwargs.pop("headers", {})
    headers.update({
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
    })
    
    if field_mask:
        headers["X-Goog-FieldMask"] = field_mask
    
    resp = requests.request(method, url, headers=headers, **kwargs)
    
    if resp.status_code >= 400:
        logger.error(f"Google Places API error: {resp.text}")
        raise Exception(f"Google Places API error: {resp.text}")
    
    if resp.text:
        return resp.json()
    return {}


# ==================== Places Search Functions ====================

def search_places(
    text_query: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[float] = None,
    min_rating: Optional[float] = None,
    open_now: Optional[bool] = None,
    price_levels: Optional[List[str]] = None,
    max_results: Optional[int] = 10,
    rank_by: Optional[str] = None
) -> dict:
    """
    Search for places using natural language text query.
    
    Args:
        text_query: Natural language search query
        latitude: Latitude for location bias (optional)
        longitude: Longitude for location bias (optional)
        radius: Search radius in meters (optional, Google infers if not provided)
        min_rating: Minimum rating filter 1.0-5.0 (optional)
        open_now: Only return places currently open (optional)
        price_levels: List of price levels to filter by (optional)
        max_results: Maximum number of results (default 10, max 20)
        rank_by: Ranking preference - RELEVANCE, DISTANCE, or POPULARITY (optional)
    
    Returns:
        Dict containing places array and metadata
    """
    # Build request body
    request_body = {
        "textQuery": text_query,
    }
    
    # Add location bias if coordinates provided
    if latitude is not None and longitude is not None:
        location_bias = {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                }
            }
        }
        # Only add radius if explicitly provided
        if radius is not None:
            location_bias["circle"]["radius"] = radius
        request_body["locationBias"] = location_bias
    
    # Add optional filters
    if min_rating is not None:
        request_body["minRating"] = min_rating
    
    if open_now is not None:
        request_body["openNow"] = open_now
    
    if price_levels is not None:
        request_body["priceLevels"] = price_levels
    
    if max_results is not None:
        # API max is 20
        request_body["maxResultCount"] = min(max_results, 20)
    
    if rank_by is not None:
        request_body["rankPreference"] = rank_by
    
    # Define fields to return
    field_mask = ",".join([
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.primaryType",
        "places.primaryTypeDisplayName",
        "places.currentOpeningHours",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.editorialSummary",
    ])
    
    return _places_api_request(
        "POST",
        "/places:searchText",
        field_mask=field_mask,
        json=request_body
    )


def get_place_details(place_id: str) -> dict:
    """
    Get detailed information about a specific place.
    
    Args:
        place_id: The Google Place ID
    
    Returns:
        Dict containing full place details
    """
    # Define comprehensive fields to return
    field_mask = ",".join([
        "id",
        "displayName",
        "formattedAddress",
        "location",
        "rating",
        "userRatingCount",
        "priceLevel",
        "primaryType",
        "primaryTypeDisplayName",
        "types",
        "currentOpeningHours",
        "regularOpeningHours",
        "nationalPhoneNumber",
        "internationalPhoneNumber",
        "websiteUri",
        "googleMapsUri",
        "editorialSummary",
        "reviews",
        "photos",
    ])
    
    return _places_api_request(
        "GET",
        f"/places/{place_id}",
        field_mask=field_mask
    )


# ==================== Helper Functions ====================

def format_place_summary(place: dict) -> dict:
    """
    Format a place into a summary dict with key fields.
    
    Args:
        place: Raw place data from API
    
    Returns:
        Formatted place summary
    """
    # Extract opening hours
    opening_hours = place.get("currentOpeningHours", {})
    weekday_descriptions = opening_hours.get("weekdayDescriptions", [])
    
    return {
        "id": place.get("id"),
        "name": place.get("displayName", {}).get("text"),
        "address": place.get("formattedAddress"),
        "location": place.get("location"),
        "rating": place.get("rating"),
        "review_count": place.get("userRatingCount"),
        "price_level": place.get("priceLevel"),
        "type": place.get("primaryTypeDisplayName", {}).get("text") or place.get("primaryType"),
        "open_now": opening_hours.get("openNow"),
        "hours": weekday_descriptions,
        "phone": place.get("nationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "google_maps_url": place.get("googleMapsUri"),
        "description": place.get("editorialSummary", {}).get("text"),
    }


def format_place_details(place: dict) -> dict:
    """
    Format a place with full details including reviews and photos.
    
    Args:
        place: Raw place data from API (from get_place_details)
    
    Returns:
        Formatted place with full details
    """
    # Start with the summary fields
    result = format_place_summary(place)
    
    # Add additional detail fields
    result["types"] = place.get("types", [])
    result["international_phone"] = place.get("internationalPhoneNumber")
    
    # Format regular opening hours (not just current)
    regular_hours = place.get("regularOpeningHours", {})
    result["regular_hours"] = regular_hours.get("weekdayDescriptions", [])
    
    # Format reviews
    reviews = place.get("reviews", [])
    result["reviews"] = [
        {
            "rating": review.get("rating"),
            "text": review.get("text", {}).get("text"),
            "author": review.get("authorAttribution", {}).get("displayName"),
            "relative_time": review.get("relativePublishTimeDescription"),
        }
        for review in reviews[:5]  # Limit to 5 reviews
    ]
    
    # Format photos (just include the reference names, not full URLs)
    photos = place.get("photos", [])
    result["photo_count"] = len(photos)
    
    return result


# ==================== Routes API Functions ====================

def _routes_api_request(method: str, endpoint: str, field_mask: str = None, **kwargs) -> dict:
    """
    Make a request to the Google Routes API.
    
    Args:
        method: HTTP method (GET, POST)
        endpoint: API endpoint path
        field_mask: Comma-separated list of fields to return
        **kwargs: Additional arguments to pass to requests
    
    Returns:
        JSON response as dict
    """
    api_key = _get_api_key()
    url = f"{ROUTES_API_BASE}{endpoint}"
    
    headers = kwargs.pop("headers", {})
    headers.update({
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
    })
    
    if field_mask:
        headers["X-Goog-FieldMask"] = field_mask
    
    resp = requests.request(method, url, headers=headers, **kwargs)
    
    if resp.status_code >= 400:
        logger.error(f"Google Routes API error: {resp.text}")
        raise Exception(f"Google Routes API error: {resp.text}")
    
    if resp.text:
        return resp.json()
    return {}


def _build_location_object(location: dict) -> dict:
    """
    Build a location object for the Routes API from a flexible input.
    
    Args:
        location: Dict with one of:
            - {"latitude": float, "longitude": float}
            - {"place_id": str}
            - {"address": str}
    
    Returns:
        Properly formatted location object for Routes API
    """
    if "latitude" in location and "longitude" in location:
        return {
            "location": {
                "latLng": {
                    "latitude": location["latitude"],
                    "longitude": location["longitude"]
                }
            }
        }
    elif "place_id" in location:
        return {"placeId": location["place_id"]}
    elif "address" in location:
        return {"address": location["address"]}
    else:
        raise Exception("Location must have (latitude, longitude), place_id, or address")


def compute_routes(
    origin: dict,
    destination: dict,
    waypoints: Optional[List[dict]] = None,
    travel_mode: str = "DRIVE",
    routing_preference: Optional[str] = "TRAFFIC_AWARE",
    avoid_tolls: bool = False,
    avoid_highways: bool = False,
    avoid_ferries: bool = False,
    optimize_waypoint_order: bool = False,
    departure_time: Optional[str] = None,
    arrival_time: Optional[str] = None,
    units: str = "METRIC",
    alternatives: bool = False
) -> dict:
    """
    Compute routes between origin and destination with optional waypoints.
    
    Args:
        origin: Location dict with (latitude, longitude), place_id, or address
        destination: Location dict with (latitude, longitude), place_id, or address
        waypoints: Optional list of intermediate location dicts
        travel_mode: DRIVE, WALK, BICYCLE, TWO_WHEELER, or TRANSIT
        routing_preference: TRAFFIC_UNAWARE, TRAFFIC_AWARE, or TRAFFIC_AWARE_OPTIMAL
        avoid_tolls: Avoid toll roads
        avoid_highways: Avoid highways
        avoid_ferries: Avoid ferries
        optimize_waypoint_order: Let Google optimize waypoint order
        departure_time: RFC3339 timestamp for departure
        arrival_time: RFC3339 timestamp for desired arrival (mainly for TRANSIT)
        units: METRIC or IMPERIAL
        alternatives: Return alternative routes
    
    Returns:
        Dict containing routes array with distance, duration, and steps
    """
    # Build request body
    request_body = {
        "origin": _build_location_object(origin),
        "destination": _build_location_object(destination),
        "travelMode": travel_mode,
        "units": units,
        "computeAlternativeRoutes": alternatives,
    }
    
    # Add waypoints if provided
    if waypoints:
        request_body["intermediates"] = [
            _build_location_object(wp) for wp in waypoints
        ]
        request_body["optimizeWaypointOrder"] = optimize_waypoint_order
    
    # Add routing preference (only for DRIVE and TWO_WHEELER)
    if routing_preference and travel_mode in ["DRIVE", "TWO_WHEELER"]:
        request_body["routingPreference"] = routing_preference
    
    # Add route modifiers
    route_modifiers = {}
    if avoid_tolls:
        route_modifiers["avoidTolls"] = True
    if avoid_highways:
        route_modifiers["avoidHighways"] = True
    if avoid_ferries:
        route_modifiers["avoidFerries"] = True
    if route_modifiers:
        request_body["routeModifiers"] = route_modifiers
    
    # Add time parameters
    if departure_time:
        request_body["departureTime"] = departure_time
    if arrival_time:
        request_body["arrivalTime"] = arrival_time
    
    # Define fields to return
    field_mask = ",".join([
        "routes.distanceMeters",
        "routes.duration",
        "routes.staticDuration",
        "routes.polyline.encodedPolyline",
        "routes.description",
        "routes.warnings",
        "routes.legs.distanceMeters",
        "routes.legs.duration",
        "routes.legs.staticDuration",
        "routes.legs.startLocation",
        "routes.legs.endLocation",
        "routes.legs.steps.distanceMeters",
        "routes.legs.steps.staticDuration",
        "routes.legs.steps.navigationInstruction",
        "routes.optimizedIntermediateWaypointIndex",
    ])
    
    return _routes_api_request(
        "POST",
        "/directions/v2:computeRoutes",
        field_mask=field_mask,
        json=request_body
    )


def _seconds_to_duration_string(seconds: int) -> str:
    """Convert seconds to a human-readable duration string."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _parse_duration(duration_str: str) -> int:
    """Parse duration string like '3600s' to seconds."""
    if duration_str and duration_str.endswith("s"):
        return int(duration_str[:-1])
    return 0


def format_route_summary(route: dict, units: str = "METRIC") -> dict:
    """
    Format a route into a summary dict with key fields.
    
    Args:
        route: Raw route data from API
        units: METRIC or IMPERIAL for display
    
    Returns:
        Formatted route summary
    """
    distance_meters = route.get("distanceMeters", 0)
    duration_seconds = _parse_duration(route.get("duration", "0s"))
    static_duration_seconds = _parse_duration(route.get("staticDuration", "0s"))
    
    # Convert distance based on units
    if units == "IMPERIAL":
        distance_value = round(distance_meters / 1609.34, 1)
        distance_unit = "miles"
    else:
        distance_value = round(distance_meters / 1000, 1)
        distance_unit = "km"
    
    # Format legs
    legs = []
    for leg in route.get("legs", []):
        leg_distance = leg.get("distanceMeters", 0)
        leg_duration = _parse_duration(leg.get("duration", "0s"))
        
        if units == "IMPERIAL":
            leg_distance_value = round(leg_distance / 1609.34, 1)
        else:
            leg_distance_value = round(leg_distance / 1000, 1)
        
        legs.append({
            "distance": leg_distance_value,
            "distance_unit": distance_unit,
            "duration_seconds": leg_duration,
            "duration": _seconds_to_duration_string(leg_duration),
            "start_location": leg.get("startLocation", {}).get("latLng"),
            "end_location": leg.get("endLocation", {}).get("latLng"),
        })
    
    result = {
        "distance": distance_value,
        "distance_unit": distance_unit,
        "duration_seconds": duration_seconds,
        "duration": _seconds_to_duration_string(duration_seconds),
        "duration_in_traffic_seconds": static_duration_seconds,
        "duration_in_traffic": _seconds_to_duration_string(static_duration_seconds),
        "description": route.get("description"),
        "warnings": route.get("warnings", []),
        "legs": legs,
        "polyline": route.get("polyline", {}).get("encodedPolyline"),
    }
    
    # Add optimized waypoint order if present
    if "optimizedIntermediateWaypointIndex" in route:
        result["optimized_waypoint_order"] = route["optimizedIntermediateWaypointIndex"]
    
    return result

