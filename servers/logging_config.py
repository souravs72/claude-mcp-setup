#!/usr/bin/env python3
"""
Centralized logging configuration for all MCP servers.
Provides consistent logging format, rotation, and error handling.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class CustomFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""

    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + reset,
        logging.INFO: blue + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s" + reset,
        logging.CRITICAL: bold_red
        + "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(
    logger_name: str,
    log_level: str = "INFO",
    log_file: Path | None = None,
    max_bytes: int = 10485760,  # 10 MB
    backup_count: int = 5,
    console_level: str = "ERROR",  # Only log errors/critical to console by default
    use_colors: bool = False,
) -> logging.Logger:
    """
    Set up logging configuration for MCP servers.

    Args:
        logger_name: Name of the logger
        log_level: File logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        max_bytes: Max size of log file before rotation
        backup_count: Number of backup log files to keep
        console_level: Console logging level
        use_colors: Whether to use colored console output

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear any existing handlers
    logger.handlers.clear()
    logger.propagate = False  # Don't propagate to root logger

    # Console handler - stderr only, configurable level
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.ERROR))

    # Use colored formatter if requested, otherwise simple
    if use_colors:
        console_handler.setFormatter(CustomFormatter())
    else:
        simple_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(simple_formatter)

    logger.addHandler(console_handler)

    # File handler for everything
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)

        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def log_server_startup(logger: logging.Logger, server_name: str, config: dict[str, Any]) -> None:
    """Log server startup information."""
    logger.info("=" * 70)
    logger.info(f"{server_name} Starting")
    logger.info("=" * 70)
    logger.info(f"Python Version: {sys.version.split()[0]}")
    logger.info(f"Log Level: {logging.getLevelName(logger.level)}")

    for key, value in config.items():
        # Mask sensitive information
        if any(secret in key.lower() for secret in ["token", "secret", "password", "key", "api"]):
            logger.info(f"{key}: {'*' * 8}")
        else:
            logger.info(f"{key}: {value}")

    logger.info("=" * 70)


def log_server_shutdown(logger: logging.Logger, server_name: str) -> None:
    """Log server shutdown information."""
    logger.info("=" * 70)
    logger.info(f"{server_name} Shutting Down")
    logger.info("=" * 70)
