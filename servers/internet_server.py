#!/usr/bin/env python3
import asyncio
import json
import sys
import logging
from typing import Any, Dict
import requests
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Internet Access Server")

@mcp.tool("web_search")
def web_search(query: str, max_results: int = 10) -> str:
    """Search the web using Brave Search API"""
    try:
        api_key = os.environ.get('BRAVE_API_KEY')
        if not api_key:
            return json.dumps({"error": "BRAVE_API_KEY not configured"})
        
        headers = {"X-Subscription-Token": api_key}
        params = {"q": query, "count": max_results}
        
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            return json.dumps(response.json())
        else:
            return json.dumps({"error": f"Search failed: {response.status_code}"})
            
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("web_fetch")
def web_fetch(url: str) -> str:
    """Fetch content from a specific URL"""
    try:
        response = requests.get(url, timeout=10)
        return json.dumps({
            "url": url,
            "status_code": response.status_code,
            "content": response.text[:5000]  # Limit content size
        })
    except Exception as e:
        logger.error(f"Web fetch error: {str(e)}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    import os
    logger.info("Starting Internet Access Server")
    mcp.run()
