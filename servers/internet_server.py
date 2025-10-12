#!/usr/bin/env python3
"""
Internet/Search MCP Server - Production Ready with ThreadPoolExecutor
Provides web search and fetch capabilities with concurrent processing.
"""

import json
import sys
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Any

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
    """Internet client for web search and page fetching with concurrent processing."""

    def __init__(self, config: InternetConfig, max_workers: int = 5) -> None:
        super().__init__(
            base_url="https://www.googleapis.com",
            timeout=config.timeout,
            max_retries=config.max_retries,
            logger=logger,
        )

        self.config = config
        self.search_endpoint = "/customsearch/v1"
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Internet")

        import atexit
        atexit.register(self.shutdown)

        logger.info(f"Internet client initialized with {max_workers} worker threads")

    def _generate_cache_key(self, url_or_query: str, params: dict[str, Any] | None = None) -> str:
        """Generate cache key for requests."""
        key_data = url_or_query
        if params:
            key_data += json.dumps(params, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()

    def search(
        self,
        query: str,
        max_results: int = 10,
        search_type: str | None = None,
        file_type: str | None = None,
        date_restrict: str | None = None,
    ) -> dict[str, Any]:
        """Search the web using Google Custom Search API."""
        logger.debug(f"Searching: {query} (max: {max_results})")

        params: dict[str, Any] = {
            "key": self.config.google_api_key,
            "cx": self.config.search_engine_id,
            "q": query,
            "num": min(max_results, 10),
        }

        if search_type:
            params["searchType"] = search_type
        if file_type:
            params["fileType"] = file_type
        if date_restrict:
            params["dateRestrict"] = date_restrict

        response = self.get(self.search_endpoint, params=params)
        data = response.json()

        formatted: dict[str, Any] = {
            "query": query,
            "total_results": data.get("searchInformation", {}).get("totalResults", "0"),
            "search_time": data.get("searchInformation", {}).get("searchTime", 0),
            "items": [],
        }

        for item in data.get("items", []):
            formatted["items"].append(
                {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "displayLink": item.get("displayLink", ""),
                    "formattedUrl": item.get("formattedUrl", ""),
                    "mime": item.get("mime", ""),
                    "fileFormat": item.get("fileFormat", ""),
                }
            )

        logger.info(f"Search returned {len(formatted['items'])} results")
        return formatted

    def fetch_url(self, url: str, timeout: int | None = None) -> dict[str, Any]:
        """Fetch content from a specific URL."""
        logger.debug(f"Fetching URL: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        try:
            response = requests.get(
                url, headers=headers, timeout=timeout or self.timeout, allow_redirects=True
            )
            response.raise_for_status()

            content = response.text
            content_length = len(content)
            max_content = 50_000  # 50 KB limit
            truncated = content_length > max_content

            if truncated:
                content = content[:max_content]

            result: dict[str, Any] = {
                "url": url,
                "final_url": response.url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "unknown"),
                "content": content,
                "content_length": content_length,
                "truncated": truncated,
                "encoding": response.encoding,
            }

            logger.info(f"Fetched {content_length} bytes from {url}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

    def batch_fetch_urls(self, urls: list[str], timeout: int | None = None) -> dict[str, Any]:
        """Fetch multiple URLs concurrently using ThreadPoolExecutor."""
        logger.info(f"Starting batch fetch for {len(urls)} URLs")

        futures: dict[Any, str] = {}
        results: dict[str, Any] = {"successful": [], "failed": [], "total": len(urls)}

        for url in urls:
            future = self.executor.submit(self.fetch_url, url, timeout)
            futures[future] = url

        for future in as_completed(futures):
            url = futures[future]
            try:
                fetch_result = future.result()
                results["successful"].append(fetch_result)
                logger.debug(f"Successfully fetched {url}")
            except Exception as e:
                results["failed"].append({"url": url, "error": str(e)})
                logger.error(f"Failed to fetch {url}: {e}")

        logger.info(
            f"Batch fetch complete: {len(results['successful'])} successful, "
            f"{len(results['failed'])} failed"
        )
        return results

    def batch_search(self, queries: list[str], max_results: int = 10) -> dict[str, Any]:
        """Perform multiple searches concurrently."""
        logger.info(f"Starting batch search for {len(queries)} queries")

        futures: dict[Any, str] = {}
        results: dict[str, Any] = {"searches": [], "failed": [], "total": len(queries)}

        for query in queries:
            future = self.executor.submit(self.search, query, max_results)
            futures[future] = query

        for future in as_completed(futures):
            query = futures[future]
            try:
                search_result = future.result()
                results["searches"].append(search_result)
                logger.debug(f"Successfully searched for: {query}")
            except Exception as e:
                results["failed"].append({"query": query, "error": str(e)})
                logger.error(f"Failed to search {query}: {e}")

        logger.info(
            f"Batch search complete: {len(results['searches'])} successful, "
            f"{len(results['failed'])} failed"
        )
        return results

    def search_and_fetch(
        self, query: str, max_results: int = 5, fetch_content: bool = True
    ) -> dict[str, Any]:
        """Search and optionally fetch content from top results concurrently."""
        logger.info(f"Search and fetch for: {query}")

        search_results = self.search(query, max_results)
        if not fetch_content or not search_results.get("items"):
            return search_results

        urls = [item["link"] for item in search_results["items"]]
        fetch_results = self.batch_fetch_urls(urls)

        url_to_content = {item["url"]: item for item in fetch_results["successful"]}

        for item in search_results["items"]:
            url = item["link"]
            if url in url_to_content:
                content_info = url_to_content[url]
                item.update(
                    {
                        "fetched_content": content_info["content"],
                        "content_length": content_info["content_length"],
                        "truncated": content_info["truncated"],
                    }
                )
            else:
                item["fetch_failed"] = True

        search_results["fetch_summary"] = {
            "attempted": len(urls),
            "successful": len(fetch_results["successful"]),
            "failed": len(fetch_results["failed"]),
        }

        logger.info(f"Search and fetch complete for: {query}")
        return search_results

    def parallel_search_with_filters(
        self, query: str, filters: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Perform the same search with multiple filter combinations concurrently."""
        logger.info(f"Parallel search with {len(filters)} filter combinations")

        futures: dict[Any, dict[str, Any]] = {}
        results: dict[str, Any] = {"searches": [], "failed": [], "total": len(filters)}

        for filter_set in filters:
            future = self.executor.submit(
                self.search,
                query,
                filter_set.get("max_results", 10),
                filter_set.get("search_type"),
                filter_set.get("file_type"),
                filter_set.get("date_restrict"),
            )
            futures[future] = filter_set

        for future in as_completed(futures):
            filter_set = futures[future]
            try:
                search_result = future.result()
                search_result["applied_filters"] = filter_set
                results["searches"].append(search_result)
                logger.debug(f"Search completed with filters: {filter_set}")
            except Exception as e:
                results["failed"].append({"filters": filter_set, "error": str(e)})
                logger.error(f"Search failed with filters {filter_set}: {e}")

        logger.info("Parallel search complete")
        return results

    def shutdown(self) -> None:
        """Shutdown the executor gracefully."""
        logger.info("Shutting down ThreadPoolExecutor...")
        self.executor.shutdown(wait=True, cancel_futures=False)
        logger.info("ThreadPoolExecutor shutdown complete")


# Initialize client
try:
    config = InternetConfig()
    validate_config(config, logger)

    log_server_startup(
        logger,
        "Internet Server",
        {"Timeout": config.timeout, "Max Retries": config.max_retries, "Thread Pool Workers": 5},
    )

    internet_client = InternetClient(config, max_workers=5)

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
    search_type: str | None = None,
    file_type: str | None = None,
    date_restrict: str | None = None,
) -> str:
    """Search the web using Google Custom Search API."""
    if not internet_client:
        return json.dumps({"error": "Internet client not initialized"})
    results = internet_client.search(query, max_results, search_type, file_type, date_restrict)
    return json.dumps(results, indent=2)


@mcp.tool()
@handle_errors(logger)
def web_fetch(url: str, timeout: int | None = None) -> str:
    """Fetch content from a specific URL."""
    if not internet_client:
        return json.dumps({"error": "Internet client not initialized"})
    result = internet_client.fetch_url(url, timeout)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def batch_fetch_urls(urls: str, timeout: int | None = None) -> str:
    """Fetch multiple URLs concurrently."""
    if not internet_client:
        return json.dumps({"error": "Internet client not initialized"})
    urls_list: list[str] = json.loads(urls)
    results = internet_client.batch_fetch_urls(urls_list, timeout)
    return json.dumps(results, indent=2)


@mcp.tool()
@handle_errors(logger)
def batch_search(queries: str, max_results: int = 10) -> str:
    """Perform multiple searches concurrently."""
    if not internet_client:
        return json.dumps({"error": "Internet client not initialized"})
    queries_list: list[str] = json.loads(queries)
    results = internet_client.batch_search(queries_list, max_results)
    return json.dumps(results, indent=2)


@mcp.tool()
@handle_errors(logger)
def search_and_fetch(query: str, max_results: int = 5, fetch_content: bool = True) -> str:
    """Search and fetch full content from top results in one operation."""
    if not internet_client:
        return json.dumps({"error": "Internet client not initialized"})
    results = internet_client.search_and_fetch(query, max_results, fetch_content)
    return json.dumps(results, indent=2)


@mcp.tool()
@handle_errors(logger)
def parallel_search_with_filters(query: str, filters: str) -> str:
    """Perform the same search with multiple filter combinations concurrently."""
    if not internet_client:
        return json.dumps({"error": "Internet client not initialized"})
    filters_list: list[dict[str, Any]] = json.loads(filters)
    results = internet_client.parallel_search_with_filters(query, filters_list)
    return json.dumps(results, indent=2)


def main() -> None:
    """Main entry point for Frappe MCP Server."""
    try:
        if not internet_client:
            logger.error("Server starting with errors - some features unavailable")

        logger.info("Starting Frappe MCP Server...")
        mcp.run()

    except KeyboardInterrupt:
        log_server_shutdown(logger, "Frappe Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if internet_client:
            internet_client.close()


if __name__ == "__main__":
    main()