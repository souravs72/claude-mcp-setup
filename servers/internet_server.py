#!/usr/bin/env python3
import json
import logging
import os
from pathlib import Path
import requests
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
except ImportError:
    print("python-dotenv not installed. Using system environment variables.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Internet Access Server")

@mcp.tool("web_search")
def web_search(query: str, max_results: int = 10) -> str:
    """Search the web using Google Custom Search API"""
    try:
        api_key = os.environ.get('GOOGLE_API_KEY')
        search_engine_id = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')
        
        if not api_key or not search_engine_id:
            return json.dumps({
                "error": "Google API credentials not configured",
                "missing": {
                    "api_key": not api_key,
                    "search_engine_id": not search_engine_id
                }
            })
        
        base_url = "https://www.googleapis.com/customsearch/v1"
        
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': min(max_results, 10)
        }
        
        response = requests.get(base_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            formatted_results = {
                'query': query,
                'total_results': data.get('searchInformation', {}).get('totalResults', 0),
                'search_time': data.get('searchInformation', {}).get('searchTime', 0),
                'items': []
            }
            
            for item in data.get('items', []):
                formatted_results['items'].append({
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'displayLink': item.get('displayLink', '')
                })
            
            return json.dumps(formatted_results)
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            return json.dumps({
                "error": f"Google Search API error: {response.status_code}",
                "details": error_data
            })
            
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("web_fetch")
def web_fetch(url: str) -> str:
    """Fetch content from a specific URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=15, headers=headers)
        
        return json.dumps({
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get('content-type', 'unknown'),
            "content": response.text[:8000],
            "content_length": len(response.text)
        })
    except Exception as e:
        logger.error(f"Web fetch error: {str(e)}")
        return json.dumps({"error": str(e), "url": url})

if __name__ == "__main__":
    logger.info("Starting Internet Access Server with Google Custom Search")
    
    # Check if credentials are available
    api_key = os.environ.get('GOOGLE_API_KEY')
    search_engine_id = os.environ.get('GOOGLE_SEARCH_ENGINE_ID')
    
    if api_key and search_engine_id:
        logger.info("Google API credentials loaded successfully")
    else:
        logger.warning("Google API credentials missing - check your .env file")
    
    mcp.run()