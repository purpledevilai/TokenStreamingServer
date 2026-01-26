import asyncio
import json
from pydantic import Field, BaseModel
from typing import Optional, List
from LLM.AgentTool import AgentTool
from Services import GoogleMapsService


class search_places(BaseModel):
    """
    Search for places using Google Places API. Returns places matching the query
    with details like name, address, rating, price level, and opening hours.
    
    This tool uses natural language search and is very flexible with what you can query.
    
    Example output:
    {
      "places": [
        {
          "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
          "name": "Trattoria Lisina",
          "address": "123 Congress Ave, Austin, TX 78701",
          "location": {"latitude": 30.2655, "longitude": -97.7425},
          "rating": 4.7,
          "review_count": 1842,
          "price_level": "PRICE_LEVEL_MODERATE",
          "type": "Italian restaurant",
          "open_now": true,
          "hours": ["Monday: 11:00 AM – 10:00 PM", "Tuesday: 11:00 AM – 10:00 PM", ...],
          "phone": "(512) 555-0123",
          "website": "https://example.com",
          "google_maps_url": "https://maps.google.com/?cid=...",
          "description": "Upscale Italian eatery with handmade pasta and wine list."
        }
      ],
      "count": 1,
      "query": "Italian restaurants in Austin"
    }
    
    The 'id' field is the Google Place ID which can be used with get_place_details for more info.
    """
    text_query: str = Field(
        description="Natural language search query. This is very flexible and can include:\n"
                    "- Place types: 'restaurants', 'coffee shops', 'museums', 'parks', 'bars', 'gyms'\n"
                    "- Qualifiers: 'best', 'cheap', 'fancy', 'family-friendly', 'romantic'\n"
                    "- Features: 'with outdoor seating', 'with wifi', 'pet-friendly', 'with live music'\n"
                    "- Location in text: 'in downtown Austin', 'near Central Park', 'in Melbourne Australia'\n"
                    "- Time-based: 'open late', 'open on Sunday', 'open now', '24 hour'\n"
                    "- Combinations: 'highly rated Italian restaurants in San Francisco with outdoor seating'\n"
                    "- Exact addresses: '123 Main St, Austin, TX' - returns the location with coordinates and place ID\n"
                    "- Specific place names: 'Empire State Building' or 'Sydney Opera House'\n"
                    "When location is included in the query, latitude/longitude parameters are optional. "
                    "Use exact addresses or place names to get coordinates/place IDs for use in other tools."
    )
    latitude: Optional[float] = Field(
        default=None,
        description="Latitude for location bias. Helps refine results to a geographic area. "
                    "Use with longitude. Not required if location is specified in text_query."
    )
    longitude: Optional[float] = Field(
        default=None,
        description="Longitude for location bias. Use with latitude."
    )
    radius: Optional[float] = Field(
        default=None,
        description="Search radius in meters. If not provided, Google infers an appropriate "
                    "radius based on the query context. Only used when latitude/longitude is provided."
    )
    min_rating: Optional[float] = Field(
        default=None,
        description="Minimum rating filter (1.0 to 5.0). Example: 4.5 for highly rated places only."
    )
    open_now: Optional[bool] = Field(
        default=None,
        description="Set to true to only return places that are currently open."
    )
    price_levels: Optional[List[str]] = Field(
        default=None,
        description="Filter by price level(s). Values: PRICE_LEVEL_INEXPENSIVE, "
                    "PRICE_LEVEL_MODERATE, PRICE_LEVEL_EXPENSIVE, PRICE_LEVEL_VERY_EXPENSIVE"
    )
    max_results: Optional[int] = Field(
        default=10,
        description="Maximum number of results to return (1-20)."
    )
    rank_by: Optional[str] = Field(
        default=None,
        description="How to rank results. Options:\n"
                    "- RELEVANCE: Best match for the query (default)\n"
                    "- DISTANCE: Closest first (requires latitude/longitude)\n"
                    "- POPULARITY: Most popular/well-known first"
    )


def search_places_func(
    text_query: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[float] = None,
    min_rating: Optional[float] = None,
    open_now: Optional[bool] = None,
    price_levels: Optional[List[str]] = None,
    max_results: Optional[int] = 10,
    rank_by: Optional[str] = None
) -> str:
    """
    Search for places using natural language text query.
    
    Args:
        text_query: Natural language search query
        latitude: Latitude for location bias (optional)
        longitude: Longitude for location bias (optional)
        radius: Search radius in meters (optional)
        min_rating: Minimum rating filter 1.0-5.0 (optional)
        open_now: Only return places currently open (optional)
        price_levels: List of price levels to filter by (optional)
        max_results: Maximum number of results (default 10)
        rank_by: Ranking preference (optional)
    
    Returns:
        JSON string with list of place summaries
    """
    if not text_query:
        raise Exception("text_query is required.")
    
    # Call the service
    result = GoogleMapsService.search_places(
        text_query=text_query,
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        min_rating=min_rating,
        open_now=open_now,
        price_levels=price_levels,
        max_results=max_results,
        rank_by=rank_by
    )
    
    places = result.get("places", [])
    
    if not places:
        return json.dumps({"places": [], "count": 0, "query": text_query})
    
    # Format places into summaries
    place_summaries = []
    for place in places:
        place_summaries.append(GoogleMapsService.format_place_summary(place))
    
    return json.dumps({
        "places": place_summaries,
        "count": len(place_summaries),
        "query": text_query,
    }, indent=2)


async def search_places_func_async(
    text_query: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[float] = None,
    min_rating: Optional[float] = None,
    open_now: Optional[bool] = None,
    price_levels: Optional[List[str]] = None,
    max_results: Optional[int] = 10,
    rank_by: Optional[str] = None
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: search_places_func(
            text_query, latitude, longitude, radius, min_rating,
            open_now, price_levels, max_results, rank_by
        )
    )


search_places_tool = AgentTool(params=search_places, function=search_places_func_async, pass_context=False)

