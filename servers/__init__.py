#!/usr/bin/env python3
"""
Production-Ready MCP Servers Package

A collection of industrial-standard Model Context Protocol (MCP) servers
for integration with Frappe, GitHub, Jira, Internet Search, and Goal Management.

Version: 2.3
"""

__version__ = "2.3.0"
__author__ = "Sourav Singh"
__license__ = "MIT"

# Import core components
from servers.base_client import (
    BaseClient,
    handle_errors,
    validate_non_empty,
    validate_positive_int,
)
from servers.config import (
    BaseConfig,
    CacheServerConfig,
    ConfigurationError,
    FrappeConfig,
    GitHubConfig,
    InternetConfig,
    JiraConfig,
    RedisConfig,
    load_env_file,
    validate_config,
)
from servers.logging_config import (
    log_server_shutdown,
    log_server_startup,
    setup_logging,
)

# Package metadata
__all__ = [
    # Base classes
    "BaseClient",
    "BaseConfig",
    # Configurations
    "FrappeConfig",
    "GitHubConfig",
    "JiraConfig",
    "InternetConfig",
    "RedisConfig",
    "CacheServerConfig",
    # Utilities
    "setup_logging",
    "log_server_startup",
    "log_server_shutdown",
    "handle_errors",
    "validate_non_empty",
    "validate_positive_int",
    "validate_config",
    "load_env_file",
    "ConfigurationError",
]

# Version info
VERSION_INFO = {"major": 2, "minor": 3, "patch": 0, "release": "stable"}

# Feature flags
FEATURES = {
    "retry_logic": True,
    "rate_limiting": True,
    "log_rotation": True,
    "error_handling": True,
    "config_validation": True,
    "cache_integration": True,
    "concurrent_processing": True,
}
