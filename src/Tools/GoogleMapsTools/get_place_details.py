import asyncio
import json
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool
from Services import GoogleMapsService


class get_place_details(BaseModel):
    """
    Get detailed information about a specific place using its Google Place ID.
    Use this to get more comprehensive information about a place found via search_places,
    including full reviews, all opening hours, and additional contact information.
    
    Example output:
    {
      "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
      "name": "Trattoria Lisina",
      "address": "123 Congress Ave, Austin, TX 78701",
      "location": {"latitude": 30.2655, "longitude": -97.7425},
      "rating": 4.7,
      "review_count": 1842,
      "price_level": "PRICE_LEVEL_MODERATE",
      "type": "Italian restaurant",
      "types": ["italian_restaurant", "restaurant", "food", "point_of_interest"],
      "open_now": true,
      "hours": ["Monday: 11:00 AM – 10:00 PM", ...],
      "regular_hours": ["Monday: 11:00 AM – 10:00 PM", ...],
      "phone": "(512) 555-0123",
      "international_phone": "+1 512-555-0123",
      "website": "https://example.com",
      "google_maps_url": "https://maps.google.com/?cid=...",
      "description": "Upscale Italian eatery with handmade pasta and wine list.",
      "reviews": [
        {
          "rating": 5,
          "text": "Amazing food and great service!",
          "author": "John D.",
          "relative_time": "2 weeks ago"
        }
      ],
      "photo_count": 24
    }
    """
    place_id: str = Field(
        description="The Google Place ID to get details for. This ID is returned in the 'id' field "
                    "from search_places results. Example: 'ChIJN1t_tDeuEmsRUsoyG83frY4'"
    )


def get_place_details_func(place_id: str) -> str:
    """
    Get detailed information about a specific place.
    
    Args:
        place_id: The Google Place ID
    
    Returns:
        JSON string with full place details
    """
    if not place_id:
        raise Exception("place_id is required.")
    
    # Call the service
    result = GoogleMapsService.get_place_details(place_id)
    
    if not result:
        return json.dumps({"error": "Place not found", "place_id": place_id})
    
    # Format the detailed response
    place_details = GoogleMapsService.format_place_details(result)
    
    return json.dumps(place_details, indent=2)


async def get_place_details_func_async(place_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: get_place_details_func(place_id)
    )


get_place_details_tool = AgentTool(params=get_place_details, function=get_place_details_func_async, pass_context=False)

