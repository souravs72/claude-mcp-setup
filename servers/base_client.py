#!/usr/bin/env python3
"""
Base client class with retry logic, error handling, rate limiting, and connection pooling.
"""
import json
import logging
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

P = ParamSpec("P")
R = TypeVar("R")


class RetryStrategy:
    """Configurable retry strategy."""

    def __init__(
        self,
        total: int = 3,
        backoff_factor: float = 0.5,
        status_forcelist: tuple[int, ...] = (500, 502, 503, 504, 429),
    ) -> None:
        self.total = total
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist

    def get_retry(self) -> Retry:
        """Get urllib3 Retry object."""
        return Retry(
            total=self.total,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.status_forcelist,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )


class BaseClient:
    """Base client with common functionality for all API integrations."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        logger: logging.Logger | None = None,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize

        # Initialize session with retry strategy and connection pooling
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic and connection pooling."""
        session = requests.Session()

        retry_strategy = RetryStrategy(total=self.max_retries)
        adapter = HTTPAdapter(
            max_retries=retry_strategy.get_retry(),
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _parse_error_response(self, response: requests.Response) -> str:
        """
        Parse error response. Override this method in subclasses for custom error parsing.

        Args:
            response: Response object with error

        Returns:
            Error message string
        """
        try:
            error_data = response.json()

            # Try common error formats
            if "error" in error_data:
                if isinstance(error_data["error"], dict):
                    return error_data["error"].get("message", str(error_data["error"]))
                return str(error_data["error"])

            if "message" in error_data:
                return str(error_data["message"])

            if "errorMessages" in error_data and error_data["errorMessages"]:
                return " | ".join(str(msg) for msg in error_data["errorMessages"])

            if "errors" in error_data and error_data["errors"]:
                if isinstance(error_data["errors"], dict):
                    errors = [f"{field}: {msg}" for field, msg in error_data["errors"].items()]
                    return " | ".join(errors)
                return str(error_data["errors"])

            return response.text[:500]
        except Exception:
            return response.text[:500]

    def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """
        Make HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: On request failure
        """
        url = f"{self.base_url}{endpoint}"

        # Set timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        self.logger.debug(f"{method} {url}")

        response: requests.Response | None = None

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            self.logger.debug(f"Response: {response.status_code}")
            return response

        except requests.exceptions.Timeout:
            self.logger.error(f"Request timeout: {url}")
            raise
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Connection error: {url}")
            raise
        except requests.exceptions.HTTPError as e:
            if response is not None:
                error_msg = self._parse_error_response(response)
                self.logger.error(f"HTTP error {response.status_code}: {error_msg}")

                # Create a new exception with the parsed error message
                enhanced_error = requests.exceptions.HTTPError(
                    f"{response.status_code} - {error_msg}", response=response
                )
                raise enhanced_error from e
            else:
                self.logger.error(f"HTTP error: {url}")
                raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make GET request."""
        return self._make_request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make POST request."""
        return self._make_request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make PUT request."""
        return self._make_request("PUT", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Make DELETE request."""
        return self._make_request("DELETE", endpoint, **kwargs)

    def close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()
            self.logger.debug("Session closed")

    def __enter__(self) -> "BaseClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def handle_errors(
    logger: logging.Logger | None = None,
) -> Callable[[Callable[P, R]], Callable[P, str]]:
    """
    Decorator for handling errors in MCP tool functions.

    Args:
        logger: Optional logger instance

    Returns:
        Decorated function that returns JSON with error handling
    """

    def decorator(func: Callable[P, R]) -> Callable[P, str]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
            _logger = logger or logging.getLogger(func.__module__)

            try:
                result = func(*args, **kwargs)
                return result if isinstance(result, str) else json.dumps(result)

            except requests.exceptions.Timeout:
                error_msg = f"Request timeout in {func.__name__}"
                _logger.error(error_msg)
                return json.dumps({"error": error_msg, "type": "timeout"})

            except requests.exceptions.ConnectionError:
                error_msg = f"Connection error in {func.__name__}"
                _logger.error(error_msg)
                return json.dumps({"error": error_msg, "type": "connection"})

            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error in {func.__name__}: {str(e)}"
                _logger.error(error_msg)
                return json.dumps(
                    {
                        "error": error_msg,
                        "type": "http_error",
                        "status_code": e.response.status_code if e.response else None,
                    }
                )

            except ValueError as e:
                error_msg = f"Validation error in {func.__name__}: {str(e)}"
                _logger.error(error_msg)
                return json.dumps({"error": error_msg, "type": "validation"})

            except Exception as e:
                error_msg = f"Unexpected error in {func.__name__}: {str(e)}"
                _logger.exception(error_msg)
                return json.dumps({"error": error_msg, "type": "unexpected"})

        return wrapper

    return decorator


def validate_non_empty(value: Any, field_name: str) -> None:
    """Validate that a value is not empty."""
    if not value:
        raise ValueError(f"{field_name} cannot be empty")


def validate_positive_int(value: int, field_name: str) -> None:
    """Validate that a value is a positive integer."""
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
