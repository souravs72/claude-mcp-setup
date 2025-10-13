#!/usr/bin/env python3
"""
MCP HTTP Proxy - Converts stdio MCP protocol to HTTP

This proxy enables Claude Desktop to communicate with cloud-hosted MCP servers
by converting the stdio-based MCP protocol to HTTP requests.

Usage:
    python mcp-http-proxy.py https://your-mcp-service.com

Claude Desktop Config:
    {
      "mcpServers": {
        "goal-agent": {
          "command": "python",
          "args": ["/path/to/mcp-http-proxy.py", "https://goal-agent.yourdomain.com"],
          "env": {}
        }
      }
    }
"""

import sys
import json
import logging
from typing import Any, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/tmp/mcp-http-proxy.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("mcp-http-proxy")


class MCPHTTPProxy:
    """Proxy that converts stdio MCP to HTTP"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = self._create_session()
        logger.info(f"Initialized MCP HTTP Proxy for {self.base_url}")

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry logic"""
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=5, pool_maxsize=10
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forward MCP request to HTTP endpoint and return response

        Args:
            request_data: MCP request from Claude Desktop

        Returns:
            MCP response to send back to Claude Desktop
        """
        try:
            # Log request (without sensitive data)
            logger.debug(f"Forwarding request: {request_data.get('method', 'unknown')}")

            # Forward to HTTP server
            response = self.session.post(
                f"{self.base_url}/mcp",
                json=request_data,
                timeout=60,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "MCP-HTTP-Proxy/1.0",
                },
            )

            # Check response status
            response.raise_for_status()

            # Return response data
            response_data = response.json()
            logger.debug(f"Received response with status {response.status_code}")

            return response_data

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {self.base_url}")
            return {
                "error": "Request timeout - server took too long to respond",
                "type": "timeout_error",
            }

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return {
                "error": f"Cannot connect to server at {self.base_url}",
                "type": "connection_error",
            }

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            return {
                "error": f"Server returned error: {e}",
                "type": "http_error",
                "status_code": e.response.status_code if e.response else None,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return {
                "error": "Server returned invalid JSON response",
                "type": "json_error",
            }

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {"error": f"Proxy error: {str(e)}", "type": "proxy_error"}

    def run(self):
        """Main loop - read from stdin, write to stdout"""
        logger.info("Starting MCP HTTP Proxy main loop")

        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse request from Claude Desktop
                    request_data = json.loads(line)

                    # Forward to HTTP server
                    response_data = self.handle_request(request_data)

                    # Send response back to Claude Desktop
                    sys.stdout.write(json.dumps(response_data) + "\n")
                    sys.stdout.flush()

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from stdin: {e}")
                    error_response = {
                        "error": "Invalid JSON in request",
                        "type": "json_error",
                    }
                    sys.stdout.write(json.dumps(error_response) + "\n")
                    sys.stdout.flush()

        except KeyboardInterrupt:
            logger.info("Proxy stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
            raise


def main():
    """Entry point"""
    if len(sys.argv) < 2:
        print("Usage: mcp-http-proxy.py <base_url>", file=sys.stderr)
        print(
            "Example: mcp-http-proxy.py https://goal-agent.yourdomain.com",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = sys.argv[1]

    # Validate URL
    if not base_url.startswith(("http://", "https://")):
        print(f"Error: Invalid URL: {base_url}", file=sys.stderr)
        print("URL must start with http:// or https://", file=sys.stderr)
        sys.exit(1)

    # Create and run proxy
    proxy = MCPHTTPProxy(base_url)
    proxy.run()


if __name__ == "__main__":
    main()
