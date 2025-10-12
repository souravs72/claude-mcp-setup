#!/usr/bin/env python3
"""
Configuration management for MCP servers.
Handles environment variables, validation, and defaults.
"""
import os
import re
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field


def load_env_file(env_path: Path | None = None) -> None:
    """Load environment variables from .env file."""
    try:
        from dotenv import load_dotenv

        if env_path is None:
            project_root = Path(__file__).parent.parent
            env_path = project_root / ".env"

        if env_path.exists():
            load_dotenv(env_path)
            return

    except ImportError:
        pass


def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return url_pattern.match(url) is not None


@dataclass
class BaseConfig:
    """Base configuration class."""

    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration. Returns (is_valid, errors)."""
        errors: list[str] = []
        required_fields = self.get_required_fields()

        for field_name in required_fields:
            value = getattr(self, field_name, None)
            if not value:
                errors.append(f"Missing required field: {field_name}")

        return len(errors) == 0, errors

    def get_required_fields(self) -> list[str]:
        """Override in subclasses to specify required fields."""
        return []

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}


@dataclass
class FrappeConfig(BaseConfig):
    """Frappe server configuration."""

    site_url: str = field(default_factory=lambda: os.getenv("FRAPPE_SITE_URL", ""))
    api_key: str = field(default_factory=lambda: os.getenv("FRAPPE_API_KEY", ""))
    api_secret: str = field(default_factory=lambda: os.getenv("FRAPPE_API_SECRET", ""))
    timeout: int = field(default_factory=lambda: int(os.getenv("FRAPPE_TIMEOUT", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("FRAPPE_MAX_RETRIES", "3")))
    pool_connections: int = field(default_factory=lambda: int(os.getenv("FRAPPE_POOL_CONNECTIONS", "5")))
    pool_maxsize: int = field(default_factory=lambda: int(os.getenv("FRAPPE_POOL_MAXSIZE", "10")))

    def __post_init__(self) -> None:
        self.site_url = self.site_url.rstrip("/")
        if self.site_url and not is_valid_url(self.site_url):
            raise ValueError(f"Invalid FRAPPE_SITE_URL: {self.site_url}")

    def get_required_fields(self) -> list[str]:
        return ["site_url", "api_key", "api_secret"]


@dataclass
class GoalAgentConfig(BaseConfig):
    """Goal agent configuration."""
    max_workers: int = field(default_factory=lambda: int(os.getenv("GOAL_AGENT_MAX_WORKERS", "5")))
    timeout: int = field(default_factory=lambda: int(os.getenv("GOAL_AGENT_TIMEOUT", "30")))
    cache_enabled: bool = field(
        default_factory=lambda: os.getenv("CACHE_ENABLED", "true").lower() == "true"
    )
    
    def get_required_fields(self) -> list[str]:
        return []

@dataclass
class GitHubConfig(BaseConfig):
    """GitHub server configuration."""
    token: str = field(default_factory=lambda: os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", ""))
    timeout: int = field(default_factory=lambda: int(os.getenv("GITHUB_TIMEOUT", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("GITHUB_MAX_RETRIES", "3")))
    # ADD THIS FIELD:
    default_branch: str = field(default_factory=lambda: os.getenv("GITHUB_DEFAULT_BRANCH", "main"))

    def __post_init__(self) -> None:
        if self.token and not self.token.startswith(("ghp_", "github_pat_")):
            raise ValueError(
                "Invalid GitHub token format (should start with 'ghp_' or 'github_pat_')"
            )

    def get_required_fields(self) -> list[str]:
        return ["token"]


@dataclass
class JiraConfig(BaseConfig):
    """Jira server configuration."""

    base_url: str = field(default_factory=lambda: os.getenv("JIRA_BASE_URL", ""))
    email: str = field(default_factory=lambda: os.getenv("JIRA_EMAIL", ""))
    api_token: str = field(default_factory=lambda: os.getenv("JIRA_API_TOKEN", ""))
    project_key: str = field(default_factory=lambda: os.getenv("JIRA_PROJECT_KEY", ""))
    timeout: int = field(default_factory=lambda: int(os.getenv("JIRA_TIMEOUT", "30")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("JIRA_MAX_RETRIES", "3")))
    rate_limit_delay: float = field(
        default_factory=lambda: float(os.getenv("JIRA_RATE_LIMIT_DELAY", "0.5"))
    )

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if self.base_url and not is_valid_url(self.base_url):
            raise ValueError(f"Invalid JIRA_BASE_URL: {self.base_url}")
        if self.base_url and not self.base_url.startswith("https://"):
            raise ValueError("JIRA_BASE_URL must use HTTPS")
        if self.email and "@" not in self.email:
            raise ValueError(f"Invalid JIRA_EMAIL format: {self.email}")

    def get_required_fields(self) -> list[str]:
        return ["base_url", "email", "api_token"]


@dataclass
class InternetConfig(BaseConfig):
    """Internet/search server configuration."""

    google_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    search_engine_id: str = field(default_factory=lambda: os.getenv("GOOGLE_SEARCH_ENGINE_ID", ""))
    timeout: int = field(default_factory=lambda: int(os.getenv("GOOGLE_TIMEOUT", "15")))
    max_retries: int = field(default_factory=lambda: int(os.getenv("GOOGLE_MAX_RETRIES", "3")))

    def get_required_fields(self) -> list[str]:
        return ["google_api_key", "search_engine_id"]


@dataclass
class RedisConfig(BaseConfig):
    """Redis server configuration."""

    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    password: str | None = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    decode_responses: bool = field(
        default_factory=lambda: os.getenv("REDIS_DECODE_RESPONSES", "true").lower() == "true"
    )
    socket_timeout: int = field(default_factory=lambda: int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")))
    socket_connect_timeout: int = field(
        default_factory=lambda: int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
    )
    max_connections: int = field(
        default_factory=lambda: int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
    )
    retry_on_timeout: bool = field(
        default_factory=lambda: os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
    )
    health_check_interval: int = field(
        default_factory=lambda: int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
    )

    def get_required_fields(self) -> list[str]:
        return ["host", "port"]


@dataclass
class CacheServerConfig(BaseConfig):
    """Cache server configuration for goal agent."""

    url: str = field(default_factory=lambda: os.getenv("CACHE_SERVER_URL", "http://localhost:8001"))
    timeout: int = field(default_factory=lambda: int(os.getenv("CACHE_SERVER_TIMEOUT", "5")))
    enabled: bool = field(
        default_factory=lambda: os.getenv("CACHE_ENABLED", "true").lower() == "true"
    )

    def __post_init__(self) -> None:
        self.url = self.url.rstrip("/")
        if self.url and not is_valid_url(self.url):
            raise ValueError(f"Invalid CACHE_SERVER_URL: {self.url}")

    def get_required_fields(self) -> list[str]:
        return [] if not self.enabled else ["url"]


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass


def validate_config(config: BaseConfig, logger: Any = None) -> None:
    """
    Validate configuration and raise exception if invalid.

    Args:
        config: Configuration object to validate
        logger: Optional logger for error messages

    Raises:
        ConfigurationError: If configuration is invalid
    """
    is_valid, errors = config.validate()

    if not is_valid:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
        if logger:
            logger.error(error_msg)
        raise ConfigurationError(error_msg)
