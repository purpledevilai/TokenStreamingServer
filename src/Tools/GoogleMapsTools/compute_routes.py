import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional, List
from LLM.AgentTool import AgentTool
from Services import GoogleMapsService


class LocationInput(BaseModel):
    """
    A location can be specified in one of three ways:
    - latitude + longitude: {"latitude": 30.2672, "longitude": -97.7431}
    - place_id: {"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}
    - address: {"address": "123 Main St, Austin, TX"}
    """
    latitude: Optional[float] = Field(default=None, description="Latitude coordinate")
    longitude: Optional[float] = Field(default=None, description="Longitude coordinate")
    place_id: Optional[str] = Field(default=None, description="Google Place ID from search_places")
    address: Optional[str] = Field(default=None, description="Street address or place name")


class compute_routes(BaseModel):
    """
    Compute driving, walking, cycling, or transit routes between locations.
    Returns distance, travel time, and turn-by-turn directions.
    
    Use this tool to:
    - Get travel time estimates between two or more locations
    - Plan routes with multiple stops (waypoints)
    - Compare different travel modes (driving vs walking vs transit)
    - Get directions with step-by-step navigation instructions
    
    Example output:
    {
      "routes": [
        {
          "distance": 165.2,
          "distance_unit": "miles",
          "duration_seconds": 9360,
          "duration": "2h 36m",
          "duration_in_traffic_seconds": 10800,
          "duration_in_traffic": "3h 0m",
          "description": "I-35 S",
          "warnings": [],
          "legs": [
            {
              "distance": 82.5,
              "distance_unit": "miles",
              "duration_seconds": 4680,
              "duration": "1h 18m",
              "start_location": {"latitude": 30.2672, "longitude": -97.7431},
              "end_location": {"latitude": 29.4241, "longitude": -98.4936}
            }
          ],
          "optimized_waypoint_order": [1, 0],
          "polyline": "ipkcFfichV..."
        }
      ],
      "travel_mode": "DRIVE",
      "units": "IMPERIAL"
    }
    
    The 'optimized_waypoint_order' field appears when optimize_waypoint_order is true,
    showing the optimal order to visit the waypoints.
    """
    origin: dict = Field(
        description="Starting location. Provide ONE of:\n"
                    "- Coordinates: {\"latitude\": 30.2672, \"longitude\": -97.7431}\n"
                    "- Place ID: {\"place_id\": \"ChIJN1t_tDeuEmsRUsoyG83frY4\"}\n"
                    "- Address: {\"address\": \"123 Main St, Austin, TX\"}\n"
                    "You can get coordinates or place_id from search_places."
    )
    destination: dict = Field(
        description="Ending location. Same format as origin:\n"
                    "- Coordinates: {\"latitude\": ..., \"longitude\": ...}\n"
                    "- Place ID: {\"place_id\": \"...\"}\n"
                    "- Address: {\"address\": \"...\"}"
    )
    waypoints: Optional[List[dict]] = Field(
        default=None,
        description="Optional list of intermediate stops. Each waypoint uses the same format as origin/destination. "
                    "Example: [{\"address\": \"San Marcos, TX\"}, {\"address\": \"San Antonio, TX\"}]"
    )
    travel_mode: Optional[str] = Field(
        default="DRIVE",
        description="Mode of transportation:\n"
                    "- DRIVE: Car/automobile (default)\n"
                    "- WALK: Walking/pedestrian\n"
                    "- BICYCLE: Cycling\n"
                    "- TWO_WHEELER: Motorcycle/scooter\n"
                    "- TRANSIT: Public transportation (bus, rail, subway)"
    )
    routing_preference: Optional[str] = Field(
        default="TRAFFIC_AWARE",
        description="Route optimization preference (for DRIVE and TWO_WHEELER modes):\n"
                    "- TRAFFIC_UNAWARE: Fastest route ignoring current traffic\n"
                    "- TRAFFIC_AWARE: Considers current traffic conditions (default)\n"
                    "- TRAFFIC_AWARE_OPTIMAL: Best quality traffic routing (slower response)\n"
                    "Note: Pairs with departure_time for accurate traffic predictions."
    )
    avoid_tolls: Optional[bool] = Field(
        default=False,
        description="Avoid toll roads when possible."
    )
    avoid_highways: Optional[bool] = Field(
        default=False,
        description="Avoid highways/freeways when possible."
    )
    avoid_ferries: Optional[bool] = Field(
        default=False,
        description="Avoid ferry routes when possible."
    )
    optimize_waypoint_order: Optional[bool] = Field(
        default=False,
        description="When true, Google will reorder waypoints for the most efficient route. "
                    "Use this when the user wants the optimal order to visit multiple places. "
                    "Set to false when the user needs to visit locations in a specific order. "
                    "Infer from context: 'best route to visit all these places' = true, "
                    "'go to A, then B, then C' = false."
    )
    departure_time: Optional[str] = Field(
        default=None,
        description="Departure time in RFC3339 format (e.g., '2026-01-25T18:00:00Z'). "
                    "Used with routing_preference for traffic-aware routing."
    )
    arrival_time: Optional[str] = Field(
        default=None,
        description="Desired arrival time in RFC3339 format. Primarily used with TRANSIT mode "
                    "to find routes that arrive by a specific time."
    )
    units: Optional[str] = Field(
        default="METRIC",
        description="Unit system for distances:\n"
                    "- METRIC: Kilometers (default)\n"
                    "- IMPERIAL: Miles\n"
                    "Infer from location context: Use IMPERIAL for US locations, METRIC for most other countries."
    )
    alternatives: Optional[bool] = Field(
        default=False,
        description="Return alternative routes in addition to the primary route."
    )


def compute_routes_func(
    origin: dict,
    destination: dict,
    waypoints: Optional[List[dict]] = None,
    travel_mode: Optional[str] = "DRIVE",
    routing_preference: Optional[str] = "TRAFFIC_AWARE",
    avoid_tolls: Optional[bool] = False,
    avoid_highways: Optional[bool] = False,
    avoid_ferries: Optional[bool] = False,
    optimize_waypoint_order: Optional[bool] = False,
    departure_time: Optional[str] = None,
    arrival_time: Optional[str] = None,
    units: Optional[str] = "METRIC",
    alternatives: Optional[bool] = False
) -> str:
    """
    Compute routes between origin and destination.
    
    Args:
        origin: Starting location dict
        destination: Ending location dict
        waypoints: Optional intermediate stops
        travel_mode: Mode of transportation
        routing_preference: Traffic-aware routing option
        avoid_tolls: Avoid toll roads
        avoid_highways: Avoid highways
        avoid_ferries: Avoid ferries
        optimize_waypoint_order: Optimize waypoint order
        departure_time: Departure time (RFC3339)
        arrival_time: Arrival time (RFC3339)
        units: METRIC or IMPERIAL
        alternatives: Return alternative routes
    
    Returns:
        JSON string with route summaries
    """
    if not origin:
        raise Exception("origin is required.")
    if not destination:
        raise Exception("destination is required.")
    
    # Call the service
    result = GoogleMapsService.compute_routes(
        origin=origin,
        destination=destination,
        waypoints=waypoints,
        travel_mode=travel_mode,
        routing_preference=routing_preference,
        avoid_tolls=avoid_tolls,
        avoid_highways=avoid_highways,
        avoid_ferries=avoid_ferries,
        optimize_waypoint_order=optimize_waypoint_order,
        departure_time=departure_time,
        arrival_time=arrival_time,
        units=units,
        alternatives=alternatives
    )
    
    routes = result.get("routes", [])
    
    if not routes:
        return json.dumps({
            "routes": [],
            "count": 0,
            "error": "No routes found between the specified locations."
        })
    
    # Format routes into summaries
    route_summaries = []
    for route in routes:
        route_summaries.append(GoogleMapsService.format_route_summary(route, units))
    
    return json.dumps({
        "routes": route_summaries,
        "count": len(route_summaries),
        "travel_mode": travel_mode,
        "units": units,
    }, indent=2)


async def compute_routes_func_async(
    origin: dict,
    destination: dict,
    waypoints: Optional[List[dict]] = None,
    travel_mode: Optional[str] = "DRIVE",
    routing_preference: Optional[str] = "TRAFFIC_AWARE",
    avoid_tolls: Optional[bool] = False,
    avoid_highways: Optional[bool] = False,
    avoid_ferries: Optional[bool] = False,
    optimize_waypoint_order: Optional[bool] = False,
    departure_time: Optional[str] = None,
    arrival_time: Optional[str] = None,
    units: Optional[str] = "METRIC",
    alternatives: Optional[bool] = False
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: compute_routes_func(
            origin, destination, waypoints, travel_mode, routing_preference,
            avoid_tolls, avoid_highways, avoid_ferries, optimize_waypoint_order,
            departure_time, arrival_time, units, alternatives
        )
    )


compute_routes_tool = AgentTool(params=compute_routes, function=compute_routes_func_async, pass_context=False)

