#!/usr/bin/env python3
"""
Configuration management for MCP servers.
Handles environment variables, validation, and defaults.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


def load_env_file(env_path: Optional[Path] = None) -> None:
    """Load environment variables from .env file."""
    try:
        from dotenv import load_dotenv
        
        if env_path is None:
            project_root = Path(__file__).parent.parent
            env_path = project_root / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
            return
            
    except ImportError:
        pass


@dataclass
class BaseConfig:
    """Base configuration class."""
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration. Returns (is_valid, errors)."""
        errors = []
        required_fields = self.get_required_fields()
        
        for field_name in required_fields:
            value = getattr(self, field_name, None)
            if not value:
                errors.append(f"Missing required field: {field_name}")
        
        return len(errors) == 0, errors
    
    def get_required_fields(self) -> list[str]:
        """Override in subclasses to specify required fields."""
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }


@dataclass
class FrappeConfig(BaseConfig):
    """Frappe server configuration."""
    site_url: str = field(default_factory=lambda: os.getenv('FRAPPE_SITE_URL', ''))
    api_key: str = field(default_factory=lambda: os.getenv('FRAPPE_API_KEY', ''))
    api_secret: str = field(default_factory=lambda: os.getenv('FRAPPE_API_SECRET', ''))
    timeout: int = field(default_factory=lambda: int(os.getenv('FRAPPE_TIMEOUT', '30')))
    max_retries: int = field(default_factory=lambda: int(os.getenv('FRAPPE_MAX_RETRIES', '3')))
    
    def __post_init__(self):
        self.site_url = self.site_url.rstrip('/')
    
    def get_required_fields(self) -> list[str]:
        return ['site_url', 'api_key', 'api_secret']


@dataclass
class GitHubConfig(BaseConfig):
    """GitHub server configuration."""
    token: str = field(default_factory=lambda: os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN', ''))
    timeout: int = field(default_factory=lambda: int(os.getenv('GITHUB_TIMEOUT', '30')))
    max_retries: int = field(default_factory=lambda: int(os.getenv('GITHUB_MAX_RETRIES', '3')))
    
    def get_required_fields(self) -> list[str]:
        return ['token']


@dataclass
class JiraConfig(BaseConfig):
    """Jira server configuration."""
    base_url: str = field(default_factory=lambda: os.getenv('JIRA_BASE_URL', ''))
    email: str = field(default_factory=lambda: os.getenv('JIRA_EMAIL', ''))
    api_token: str = field(default_factory=lambda: os.getenv('JIRA_API_TOKEN', ''))
    project_key: str = field(default_factory=lambda: os.getenv('JIRA_PROJECT_KEY', ''))
    timeout: int = field(default_factory=lambda: int(os.getenv('JIRA_TIMEOUT', '30')))
    max_retries: int = field(default_factory=lambda: int(os.getenv('JIRA_MAX_RETRIES', '3')))
    rate_limit_delay: float = field(default_factory=lambda: float(os.getenv('JIRA_RATE_LIMIT_DELAY', '0.5')))
    
    def __post_init__(self):
        self.base_url = self.base_url.rstrip('/')
    
    def get_required_fields(self) -> list[str]:
        return ['base_url', 'email', 'api_token']


@dataclass
class InternetConfig(BaseConfig):
    """Internet/search server configuration."""
    google_api_key: str = field(default_factory=lambda: os.getenv('GOOGLE_API_KEY', ''))
    search_engine_id: str = field(default_factory=lambda: os.getenv('GOOGLE_SEARCH_ENGINE_ID', ''))
    timeout: int = field(default_factory=lambda: int(os.getenv('GOOGLE_TIMEOUT', '15')))
    max_retries: int = field(default_factory=lambda: int(os.getenv('GOOGLE_MAX_RETRIES', '3')))
    
    def get_required_fields(self) -> list[str]:
        return ['google_api_key', 'search_engine_id']


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


def validate_config(config: BaseConfig, logger=None) -> None:
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