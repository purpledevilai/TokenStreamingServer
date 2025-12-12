import asyncio
import requests
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool


class view_url_jina(BaseModel):
    """
    View and extract the text content of a web page using Jina AI's reader service. This tool fetches a webpage and returns its readable text content, which is useful for analyzing articles, documentation, or any web content found through search results.
    
    The tool automatically handles various web page formats and returns clean, readable text without HTML markup.
    """
    url: str = Field(description="The URL of the webpage to view and extract content from. Must be a valid HTTP/HTTPS URL.")


def view_url_jina_func(url: str, context: dict) -> str:
    # Check parameters
    if not url:
        raise Exception("url is required.")
    if not url.strip():
        raise Exception("url cannot be empty.")
    
    # Basic URL validation
    if not (url.startswith("http://") or url.startswith("https://")):
        raise Exception("URL must start with http:// or https://")
    
    try:
        # Use Jina AI reader service to extract content
        jina_url = f"https://r.jina.ai/{url}"
        
        response = requests.get(jina_url, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        content = response.text
        
        # Check if we got content
        if not content or content.strip() == "":
            return f"No readable content found at URL: {url}"
        
        # Return the extracted text content
        return content
        
    except requests.exceptions.Timeout:
        raise Exception("Request timed out while fetching the webpage. The page may be slow to respond.")
    except requests.exceptions.ConnectionError:
        raise Exception("Could not connect to the webpage. Please check the URL and try again.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Exception("Webpage not found (404). Please check the URL.")
        elif e.response.status_code == 403:
            raise Exception("Access forbidden (403). The webpage may block automated access.")
        else:
            raise Exception(f"HTTP error {e.response.status_code} while fetching webpage.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error while viewing URL: {str(e)}")


async def view_url_jina_func_async(url: str, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: view_url_jina_func(url, context)
    )


view_url_jina_tool = AgentTool(params=view_url_jina, function=view_url_jina_func_async, pass_context=True)