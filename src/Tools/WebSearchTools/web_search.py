import asyncio
import os
import json
import requests
from pydantic import Field, BaseModel
from LLM.AgentChat import AgentTool


class web_search(BaseModel):
    """
    Perform a web search using Google Custom Search API. This tool searches the web for information related to your query and returns a list of relevant results with titles and URLs. Use this when you need to find current information, news, or resources from the internet.
    
    The search returns up to 10 results by default, showing the most relevant web pages for your query.
    """
    query: str = Field(description="The search query to look for on the web. Be specific and use relevant keywords for better results.")
    num_results: int = Field(description="Number of search results to return (1-10)", default=5, ge=1, le=10)


def web_search_func(query: str, num_results: int, context: dict) -> str:
    # Check parameters
    if not query:
        raise Exception("query is required.")
    if not query.strip():
        raise Exception("query cannot be empty.")
    
    # Get API credentials from environment variables
    api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
    search_engine_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
    
    if not api_key:
        raise Exception("GOOGLE_SEARCH_API_KEY environment variable is not set.")
    if not search_engine_id:
        raise Exception("GOOGLE_SEARCH_ENGINE_ID environment variable is not set.")
    
    try:
        # Make the API request
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": search_engine_id,
            "q": query,
            "num": num_results
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        results = response.json()
        
        # Check if we got results
        items = results.get("items", [])
        if not items:
            return json.dumps({
                "query": query,
                "total_results": 0,
                "message": "No search results found for the given query.",
                "results": {}
            })
        
        # Format the results
        final = {}
        for item in items:
            title = item.get("title", "No title")
            link = item.get("link", "No link")
            snippet = item.get("snippet", "No description available")
            
            final[title] = {
                "url": link,
                "description": snippet
            }
        
        # Return structured results
        search_results = {
            "query": query,
            "total_results": len(final),
            "results": final
        }
        
        return json.dumps(search_results, indent=2)
        
    except requests.exceptions.Timeout:
        raise Exception("Search request timed out. Please try again.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error making search request: {str(e)}")
    except Exception as e:
        raise Exception(f"Error performing web search: {str(e)}")


async def web_search_func_async(query: str, num_results: int, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: web_search_func(query, num_results, context)
    )


web_search_tool = AgentTool(params=web_search, function=web_search_func_async, pass_context=True)