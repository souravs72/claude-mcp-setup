#!/usr/bin/env python3
"""
Internet/Search MCP Server - Production Ready
Provides web search and fetch capabilities via Google Custom Search API
"""
import json
import sys
from pathlib import Path
from typing import Optional
import requests

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.logging_config import setup_logging, log_server_startup, log_server_shutdown
from servers.config import load_env_file, InternetConfig, validate_config, ConfigurationError
from servers.base_client import BaseClient, handle_errors

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "internet_server.log"
logger = setup_logging("InternetServer", log_file=log_file)

load_env_file()
mcp = FastMCP("Internet Search & Fetch Server")


class InternetClient(BaseClient):
    """Internet client for web search and page fetching."""
    
    def __init__(self, config: InternetConfig):
        super().__init__(
            base_url="https://www.googleapis.com",
            timeout=config.timeout,
            max_retries=config.max_retries,
            logger=logger
        )
        
        self.config = config
        self.search_endpoint = "/customsearch/v1"
        
        logger.info("Internet client initialized successfully")
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        search_type: Optional[str] = None,
        file_type: Optional[str] = None,
        date_restrict: Optional[str] = None
    ) -> dict:
        """
        Search the web using Google Custom Search API.
        
        Args:
            query: Search query
            max_results: Maximum number of results (1-10)
            search_type: Type of search (image, etc.)
            file_type: Filter by file type (pdf, doc, etc.)
            date_restrict: Date restriction (d[number], w[number], m[number], y[number])
            
        Returns:
            Search results
        """
        logger.debug(f"Searching: {query} (max: {max_results})")
        
        params = {
            'key': self.config.google_api_key,
            'cx': self.config.search_engine_id,
            'q': query,
            'num': min(max_results, 10)
        }
        
        if search_type:
            params['searchType'] = search_type
        
        if file_type:
            params['fileType'] = file_type
        
        if date_restrict:
            params['dateRestrict'] = date_restrict
        
        response = self.get(self.search_endpoint, params=params)
        data = response.json()
        
        # Format results
        formatted = {
            'query': query,
            'total_results': data.get('searchInformation', {}).get('totalResults', '0'),
            'search_time': data.get('searchInformation', {}).get('searchTime', 0),
            'items': []
        }
        
        for item in data.get('items', []):
            formatted['items'].append({
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'displayLink': item.get('displayLink', ''),
                'formattedUrl': item.get('formattedUrl', ''),
                'mime': item.get('mime', ''),
                'fileFormat': item.get('fileFormat', '')
            })
        
        logger.info(f"Search returned {len(formatted['items'])} results")
        return formatted
    
    def fetch_url(self, url: str, timeout: Optional[int] = None) -> dict:
        """
        Fetch content from a specific URL.
        
        Args:
            url: URL to fetch
            timeout: Request timeout (overrides default)
            
        Returns:
            Page content and metadata
        """
        logger.debug(f"Fetching URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout or self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Limit content size to prevent memory issues
            content = response.text
            content_length = len(content)
            max_content = 50000  # 50KB of text
            
            if content_length > max_content:
                content = content[:max_content]
                truncated = True
            else:
                truncated = False
            
            result = {
                'url': url,
                'final_url': response.url,
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type', 'unknown'),
                'content': content,
                'content_length': content_length,
                'truncated': truncated,
                'encoding': response.encoding
            }
            
            logger.info(f"Fetched {content_length} bytes from {url}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise


# Initialize client
try:
    config = InternetConfig()
    validate_config(config, logger)
    
    log_server_startup(logger, "Internet Server", {
        "Timeout": config.timeout,
        "Max Retries": config.max_retries
    })
    
    internet_client = InternetClient(config)
    
except ConfigurationError as e:
    logger.critical(f"Configuration error: {e}")
    internet_client = None
except Exception as e:
    logger.critical(f"Failed to initialize Internet client: {e}", exc_info=True)
    internet_client = None


# MCP Tools
@mcp.tool()
@handle_errors(logger)
def web_search(
    query: str,
    max_results: int = 10,
    search_type: Optional[str] = None,
    file_type: Optional[str] = None,
    date_restrict: Optional[str] = None
) -> str:
    """
    Search the web using Google Custom Search API.
    
    Args:
        query: Search query
        max_results: Maximum number of results (1-10, default: 10)
        search_type: Type of search (image, etc.)
        file_type: Filter by file type (pdf, doc, etc.)
        date_restrict: Date restriction (d[number], w[number], m[number], y[number])
        
    Returns:
        JSON string with search results
        
    Examples:
        web_search("python programming")
        web_search("machine learning", max_results=5)
        web_search("research paper", file_type="pdf")
        web_search("recent news", date_restrict="w1")
    """
    if not internet_client:
        return json.dumps({"error": "Internet client not initialized"})
    
    results = internet_client.search(query, max_results, search_type, file_type, date_restrict)
    return json.dumps(results, indent=2)


@mcp.tool()
@handle_errors(logger)
def web_fetch(url: str, timeout: Optional[int] = None) -> str:
    """
    Fetch content from a specific URL.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds (optional)
        
    Returns:
        JSON string with page content and metadata
        
    Examples:
        web_fetch("https://example.com")
        web_fetch("https://example.com/article", timeout=20)
    """
    if not internet_client:
        return json.dumps({"error": "Internet client not initialized"})
    
    result = internet_client.fetch_url(url, timeout)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    try:
        if not internet_client:
            logger.error("Server starting with errors - some features unavailable")
        
        logger.info("Starting Internet MCP Server...")
        mcp.run()
        
    except KeyboardInterrupt:
        log_server_shutdown(logger, "Internet Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if internet_client:
            internet_client.close()