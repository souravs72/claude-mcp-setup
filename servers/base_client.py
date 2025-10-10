#!/usr/bin/env python3
"""
Base client class with retry logic, error handling, and rate limiting.
"""
import time
import logging
from typing import Any, Callable, Optional
from functools import wraps
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class RetryStrategy:
    """Configurable retry strategy."""
    
    def __init__(
        self,
        total: int = 3,
        backoff_factor: float = 0.5,
        status_forcelist: tuple = (500, 502, 503, 504, 429)
    ):
        self.total = total
        self.backoff_factor = backoff_factor
        self.status_forcelist = status_forcelist
    
    def get_retry(self) -> Retry:
        """Get urllib3 Retry object."""
        return Retry(
            total=self.total,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.status_forcelist,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )


class BaseClient:
    """Base client with common functionality for all API integrations."""
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Initialize session with retry strategy
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        
        retry_strategy = RetryStrategy(total=self.max_retries)
        adapter = HTTPAdapter(max_retries=retry_strategy.get_retry())
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _parse_error_response(self, response: requests.Response) -> str:
        """
        Parse error response. Can be overridden by subclasses for custom error parsing.
        
        Args:
            response: Response object with error
            
        Returns:
            Error message string
        """
        # Check if subclass has a custom parser
        if hasattr(self, '_parse_jira_error'):
            return self._parse_jira_error(response)
        
        # Default error parsing
        try:
            error_data = response.json()
            
            # Try common error formats
            if 'error' in error_data:
                if isinstance(error_data['error'], dict):
                    return error_data['error'].get('message', str(error_data['error']))
                return str(error_data['error'])
            
            if 'message' in error_data:
                return error_data['message']
            
            return response.text[:500]
        except:
            return response.text[:500]
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
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
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        self.logger.debug(f"{method} {url}")
        
        response = None
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            self.logger.debug(f"Response: {response.status_code}")
            return response
            
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Request timeout: {url}")
            raise
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error: {url}")
            raise
        except requests.exceptions.HTTPError as e:
            if response is not None:
                error_msg = self._parse_error_response(response)
                self.logger.error(f"HTTP error {response.status_code}: {error_msg}")
                
                # Create a new exception with the parsed error message
                enhanced_error = requests.exceptions.HTTPError(
                    f"{response.status_code} - {error_msg}",
                    response=response
                )
                raise enhanced_error from e
            else:
                self.logger.error(f"HTTP error: {url}")
                raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make GET request."""
        return self._make_request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make POST request."""
        return self._make_request("POST", endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make PUT request."""
        return self._make_request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make DELETE request."""
        return self._make_request("DELETE", endpoint, **kwargs)
    
    def close(self):
        """Close the session."""
        if self.session:
            self.session.close()
            self.logger.debug("Session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def handle_errors(logger: Optional[logging.Logger] = None):
    """
    Decorator for handling errors in MCP tool functions.
    
    Args:
        logger: Optional logger instance
        
    Returns:
        Decorated function that returns JSON with error handling
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            import json
            
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
                return json.dumps({
                    "error": error_msg,
                    "type": "http_error",
                    "status_code": e.response.status_code if e.response else None
                })
                
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