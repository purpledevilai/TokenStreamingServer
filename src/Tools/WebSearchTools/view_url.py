import asyncio
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pydantic import Field, BaseModel
from LLM.AgentTool import AgentTool


class view_url(BaseModel):
    """
    Directly view and extract text content and links from a web page using web scraping. This tool fetches a webpage, parses the HTML, and returns both the readable text content and all links found on the page. Unlike the Jina AI reader, this provides direct access to the raw content and structure.
    
    Returns both the main text content and a list of all links found on the page with their anchor text.
    """
    url: str = Field(description="The URL of the webpage to view and extract content from. Must be a valid HTTP/HTTPS URL.")
    include_links: bool = Field(description="Whether to include a list of all links found on the page", default=True)


def view_url_func(url: str, include_links: bool, context: dict) -> str:
    # Check parameters
    if not url:
        raise Exception("url is required.")
    if not url.strip():
        raise Exception("url cannot be empty.")
    
    # Basic URL validation
    if not (url.startswith("http://") or url.startswith("https://")):
        raise Exception("URL must start with http:// or https://")
    
    try:
        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else "No title found"
        
        # Extract main text content
        text_content = soup.get_text()
        
        # Clean up text - remove extra whitespace and empty lines
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Prepare result
        result = {
            "url": url,
            "title": title_text,
            "text_content": clean_text,
            "content_length": len(clean_text)
        }
        
        # Extract links if requested
        if include_links:
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Convert relative URLs to absolute URLs
                absolute_url = urljoin(url, href)
                link_text = link.get_text().strip()
                
                # Skip empty links or javascript links
                if href and not href.startswith('javascript:') and not href.startswith('mailto:'):
                    links.append({
                        "text": link_text if link_text else href,
                        "url": absolute_url
                    })
            
            result["links"] = links
            result["links_count"] = len(links)
        
        # Check if we got meaningful content
        if not clean_text or len(clean_text.strip()) < 10:
            result["warning"] = "Very little readable content found on this page"
        
        return json.dumps(result, indent=2)
        
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


async def view_url_func_async(url: str, include_links: bool, context: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: view_url_func(url, include_links, context)
    )


view_url_tool = AgentTool(params=view_url, function=view_url_func_async, pass_context=True)