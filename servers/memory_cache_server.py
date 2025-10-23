#!/usr/bin/env python3
"""
Memory Cache MCP Server - Production Ready
Provides Redis-based caching capabilities with TTL, patterns, and bulk operations
"""

import atexit
import json
import sys
from pathlib import Path
from typing import Any, Optional

import redis
from mcp.server.fastmcp import FastMCP
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.base_client import handle_errors, validate_non_empty, validate_positive_int
from servers.config import (
    ConfigurationError,
    RedisConfig,
    load_env_file,
    validate_config,
)
from servers.logging_config import (
    log_server_shutdown,
    log_server_startup,
    setup_logging,
)

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "memory_cache_server.log"
logger = setup_logging("MemoryCacheServer", log_file=log_file)

load_env_file()
mcp = FastMCP("Memory Cache Server")


class RedisCacheClient:
    """Redis cache client with connection pooling and error handling."""

    def __init__(self, config: RedisConfig) -> None:
        self.config = config
        self._pool: redis.ConnectionPool | None = None
        self._client: Any = None

        # Create connection pool
        self._pool = redis.ConnectionPool(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.password,
            decode_responses=config.decode_responses,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            max_connections=config.max_connections,
            retry_on_timeout=config.retry_on_timeout,
            health_check_interval=config.health_check_interval,
        )

        self._client = redis.Redis(connection_pool=self._pool)
        atexit.register(self.close)

        # Verify connection
        self._verify_connection()

        logger.info("Redis cache client initialized successfully")

    def _verify_connection(self) -> None:
        """Verify Redis connection."""
        try:
            if self._client:
                self._client.ping()
                logger.info(
                    f"Connected to Redis at {self.config.host}:{self.config.port}"
                )
        except RedisConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    @property
    def client(self) -> Any:
        """Get Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        return self._client

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Set a key-value pair in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            ttl: Time to live in seconds (optional, must be positive)

        Returns:
            Success status
        """
        validate_non_empty(key, "key")

        if ttl is not None:
            validate_positive_int(ttl, "ttl")

        logger.debug(f"Setting key: {key} (TTL: {ttl})")

        try:
            # Serialize non-string values
            serialized_value: str | bytes
            if not isinstance(value, str):
                serialized_value = json.dumps(value)
            else:
                serialized_value = value

            if ttl:
                result = self.client.setex(key, ttl, serialized_value)
            else:
                result = self.client.set(key, serialized_value)

            logger.info(f"Set key: {key}")
            return bool(result)

        except RedisError as e:
            logger.error(f"Failed to set key {key}: {e}")
            raise

    def get(self, key: str, deserialize: bool = True) -> Any | None:
        """
        Get a value from cache.

        Args:
            key: Cache key
            deserialize: Try to JSON deserialize the value

        Returns:
            Cached value or None if not found
        """
        validate_non_empty(key, "key")
        logger.debug(f"Getting key: {key}")

        try:
            value = self.client.get(key)

            if value is None:
                logger.debug(f"Key not found: {key}")
                return None

            # Try to deserialize JSON
            if deserialize and isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return value

        except RedisError as e:
            logger.error(f"Failed to get key {key}: {e}")
            raise

    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.

        Args:
            *keys: Keys to delete (at least one required)

        Returns:
            Number of keys deleted
        """
        if not keys:
            raise ValueError("At least one key must be provided")

        logger.debug(f"Deleting keys: {keys}")

        try:
            count = self.client.delete(*keys)
            logger.info(f"Deleted {count} keys")
            return count

        except RedisError as e:
            logger.error(f"Failed to delete keys: {e}")
            raise

    def exists(self, *keys: str) -> int:
        """
        Check if keys exist.

        Args:
            *keys: Keys to check (at least one required)

        Returns:
            Number of keys that exist
        """
        if not keys:
            raise ValueError("At least one key must be provided")

        logger.debug(f"Checking existence of keys: {keys}")

        try:
            count = self.client.exists(*keys)
            logger.debug(f"{count} keys exist")
            return count

        except RedisError as e:
            logger.error(f"Failed to check key existence: {e}")
            raise

    def expire(self, key: str, seconds: int) -> bool:
        """
        Set expiration time on a key.

        Args:
            key: Cache key
            seconds: Expiration time in seconds (must be positive)

        Returns:
            Success status
        """
        validate_non_empty(key, "key")
        validate_positive_int(seconds, "seconds")

        logger.debug(f"Setting expiration on {key}: {seconds}s")

        try:
            result = self.client.expire(key, seconds)
            logger.info(f"Set expiration on {key}")
            return bool(result)

        except RedisError as e:
            logger.error(f"Failed to set expiration on {key}: {e}")
            raise

    def ttl(self, key: str) -> int:
        """
        Get time to live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds (-1 if no expiration, -2 if key doesn't exist)
        """
        validate_non_empty(key, "key")
        logger.debug(f"Getting TTL for key: {key}")

        try:
            ttl_value = self.client.ttl(key)
            logger.debug(f"TTL for {key}: {ttl_value}s")
            return ttl_value

        except RedisError as e:
            logger.error(f"Failed to get TTL for {key}: {e}")
            raise

    def keys(self, pattern: str = "*") -> list[str]:
        """
        Get all keys matching a pattern.
        WARNING: Use scan() in production for large datasets.

        Args:
            pattern: Key pattern (supports wildcards)

        Returns:
            List of matching keys
        """
        logger.debug(f"Searching keys with pattern: {pattern}")

        try:
            keys_result = self.client.keys(pattern)
            # Handle both string and bytes return values
            keys_list = [k.decode() if isinstance(k, bytes) else k for k in keys_result]
            logger.info(f"Found {len(keys_list)} keys matching pattern")
            return keys_list

        except RedisError as e:
            logger.error(f"Failed to search keys: {e}")
            raise

    def scan(
        self, cursor: int = 0, match: str | None = None, count: int = 10
    ) -> dict[str, Any]:
        """
        Incrementally iterate over keys (production-safe).

        Args:
            cursor: Cursor position (0 to start)
            match: Key pattern to match
            count: Approximate number of keys to return (must be positive)

        Returns:
            Dictionary with cursor and keys
        """
        if cursor < 0:
            raise ValueError("Cursor must be non-negative")

        validate_positive_int(count, "count")

        logger.debug(f"Scanning keys (cursor: {cursor}, match: {match})")

        try:
            new_cursor, keys_result = self.client.scan(cursor, match=match, count=count)
            # Handle both string and bytes return values
            keys_list = [k.decode() if isinstance(k, bytes) else k for k in keys_result]
            logger.info(f"Scan returned {len(keys_list)} keys")

            return {
                "cursor": new_cursor,
                "keys": keys_list,
                "complete": new_cursor == 0,
            }

        except RedisError as e:
            logger.error(f"Failed to scan keys: {e}")
            raise

    def mget(self, keys: list[str], deserialize: bool = True) -> list[Any | None]:
        """
        Get multiple values at once.

        Args:
            keys: List of cache keys
            deserialize: Try to JSON deserialize values

        Returns:
            List of values (None for missing keys)
        """
        if not keys:
            raise ValueError("Keys list cannot be empty")

        logger.debug(f"Getting multiple keys: {keys}")

        try:
            values = self.client.mget(keys)

            # Deserialize if requested
            if deserialize:
                deserialized: list[Any | None] = []
                for value in values:
                    if value is not None and isinstance(value, str):
                        try:
                            deserialized.append(json.loads(value))
                        except json.JSONDecodeError:
                            deserialized.append(value)
                    else:
                        deserialized.append(value)
                return deserialized

            return values

        except RedisError as e:
            logger.error(f"Failed to get multiple keys: {e}")
            raise

    def mset(self, mapping: dict[str, Any]) -> bool:
        """
        Set multiple key-value pairs at once.

        Args:
            mapping: Dictionary of key-value pairs

        Returns:
            Success status
        """
        if not mapping:
            raise ValueError("Mapping cannot be empty")

        logger.debug(f"Setting multiple keys: {list(mapping.keys())}")

        try:
            # Serialize non-string values
            serialized: dict[str, str] = {}
            for key, value in mapping.items():
                if not key:
                    raise ValueError("Keys cannot be empty")
                if not isinstance(value, str):
                    serialized[key] = json.dumps(value)
                else:
                    serialized[key] = value

            result = self.client.mset(serialized)
            logger.info(f"Set {len(mapping)} keys")
            return bool(result)

        except RedisError as e:
            logger.error(f"Failed to set multiple keys: {e}")
            raise

    def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment a key's value.

        Args:
            key: Cache key
            amount: Amount to increment by (default: 1)

        Returns:
            New value after increment
        """
        validate_non_empty(key, "key")

        if amount == 0:
            raise ValueError("Amount cannot be zero")

        logger.debug(f"Incrementing key {key} by {amount}")

        try:
            value = self.client.incrby(key, amount)
            logger.info(f"Incremented {key} to {value}")
            return value

        except RedisError as e:
            logger.error(f"Failed to increment key {key}: {e}")
            raise

    def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement a key's value.

        Args:
            key: Cache key
            amount: Amount to decrement by (default: 1, must be positive)

        Returns:
            New value after decrement
        """
        validate_non_empty(key, "key")
        validate_positive_int(amount, "amount")

        logger.debug(f"Decrementing key {key} by {amount}")

        try:
            value = self.client.decrby(key, amount)
            logger.info(f"Decremented {key} to {value}")
            return value

        except RedisError as e:
            logger.error(f"Failed to decrement key {key}: {e}")
            raise

    def flush_db(self) -> bool:
        """
        Clear all keys in current database (USE WITH CAUTION).

        Returns:
            Success status
        """
        logger.warning("Flushing database - this will delete ALL keys")

        try:
            result = self.client.flushdb()
            logger.info("Database flushed")
            return bool(result)

        except RedisError as e:
            logger.error(f"Failed to flush database: {e}")
            raise

    def info(self) -> dict[str, Any]:
        """
        Get Redis server information.

        Returns:
            Server info dictionary
        """
        logger.debug("Getting server info")

        try:
            info = self.client.info()
            logger.info("Retrieved server info")
            return dict(info)

        except RedisError as e:
            logger.error(f"Failed to get server info: {e}")
            raise

    def ping(self) -> bool:
        """
        Test Redis connection.

        Returns:
            True if connection is alive
        """
        try:
            return bool(self.client.ping())
        except RedisError as e:
            logger.error(f"Ping failed: {e}")
            return False

    def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        try:
            if self._pool:
                self._pool.disconnect()
                logger.info("Redis connection pool disconnected")

            if self._client:
                self._client.close()
                logger.info("Redis client closed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Initialize client
try:
    config = RedisConfig()
    validate_config(config, logger)

    log_server_startup(
        logger,
        "Memory Cache Server",
        {
            "Redis Host": config.host,
            "Redis Port": config.port,
            "Redis DB": config.db,
            "Max Connections": config.max_connections,
            "Socket Timeout": config.socket_timeout,
            "Health Check Interval": config.health_check_interval,
        },
    )

    cache_client: RedisCacheClient | None = RedisCacheClient(config)

except ConfigurationError as e:
    logger.critical(f"Configuration error: {e}")
    cache_client = None
except Exception as e:
    logger.critical(f"Failed to initialize Redis client: {e}", exc_info=True)
    cache_client = None


# MCP Tools
@mcp.tool()
@handle_errors(logger)
def cache_set(key: str, value: str, ttl: Optional[int] = None) -> str:
    """
    Set a value in cache with optional TTL.

    Args:
        key: Cache key
        value: Value to cache (string or JSON)
        ttl: Time to live in seconds (optional, must be positive)

    Returns:
        JSON string with success status
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    # Try to parse as JSON for proper storage
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value

    result = cache_client.set(key, parsed_value, ttl)
    return json.dumps({"success": result, "key": key})


@mcp.tool()
@handle_errors(logger)
def cache_get(key: str) -> str:
    """
    Get a value from cache.

    Args:
        key: Cache key

    Returns:
        JSON string with cached value or null
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    value = cache_client.get(key)
    return json.dumps({"key": key, "value": value})


@mcp.tool()
@handle_errors(logger)
def cache_delete(keys: str) -> str:
    """
    Delete one or more keys from cache.

    Args:
        keys: JSON array of keys to delete

    Returns:
        JSON string with number of keys deleted
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    keys_list = json.loads(keys)
    if not keys_list:
        return json.dumps({"error": "Keys array cannot be empty"})

    count = cache_client.delete(*keys_list)
    return json.dumps({"deleted": count})


@mcp.tool()
@handle_errors(logger)
def cache_exists(keys: str) -> str:
    """
    Check if keys exist in cache.

    Args:
        keys: JSON array of keys to check

    Returns:
        JSON string with existence count
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    keys_list = json.loads(keys)
    if not keys_list:
        return json.dumps({"error": "Keys array cannot be empty"})

    count = cache_client.exists(*keys_list)
    return json.dumps({"exists": count, "total": len(keys_list)})


@mcp.tool()
@handle_errors(logger)
def cache_expire(key: str, seconds: int) -> str:
    """
    Set expiration time on a key.

    Args:
        key: Cache key
        seconds: Expiration time in seconds (must be positive)

    Returns:
        JSON string with success status
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    result = cache_client.expire(key, seconds)
    return json.dumps({"success": result, "key": key, "ttl": seconds})


@mcp.tool()
@handle_errors(logger)
def cache_ttl(key: str) -> str:
    """
    Get time to live for a key.

    Args:
        key: Cache key

    Returns:
        JSON string with TTL (-1 if no expiration, -2 if not found)
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    ttl = cache_client.ttl(key)

    status = "active"
    if ttl == -1:
        status = "no_expiration"
    elif ttl == -2:
        status = "not_found"

    return json.dumps({"key": key, "ttl": ttl, "status": status})


@mcp.tool()
@handle_errors(logger)
def cache_keys(pattern: str = "*") -> str:
    """
    Get all keys matching a pattern.
    WARNING: Use cache_scan for production with large datasets.

    Args:
        pattern: Key pattern (supports * and ? wildcards)

    Returns:
        JSON string with matching keys
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    keys = cache_client.keys(pattern)
    return json.dumps({"pattern": pattern, "keys": keys, "count": len(keys)})


@mcp.tool()
@handle_errors(logger)
def cache_scan(cursor: int = 0, match: Optional[str] = None, count: int = 10) -> str:
    """
    Incrementally scan keys (production-safe alternative to cache_keys).

    Args:
        cursor: Cursor position (0 to start new scan, must be non-negative)
        match: Key pattern to match
        count: Approximate number of keys per iteration (must be positive)

    Returns:
        JSON string with cursor and keys
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    result = cache_client.scan(cursor, match, count)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def cache_mget(keys: str) -> str:
    """
    Get multiple values at once.

    Args:
        keys: JSON array of cache keys

    Returns:
        JSON string with key-value pairs
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    keys_list = json.loads(keys)
    if not keys_list:
        return json.dumps({"error": "Keys array cannot be empty"})

    values = cache_client.mget(keys_list)

    # Create key-value mapping
    result = {key: value for key, value in zip(keys_list, values)}

    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def cache_mset(data: str) -> str:
    """
    Set multiple key-value pairs at once.

    Args:
        data: JSON object with key-value pairs

    Returns:
        JSON string with success status
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    mapping = json.loads(data)
    if not mapping:
        return json.dumps({"error": "Data object cannot be empty"})

    result = cache_client.mset(mapping)
    return json.dumps({"success": result, "keys_set": len(mapping)})


@mcp.tool()
@handle_errors(logger)
def cache_incr(key: str, amount: int = 1) -> str:
    """
    Increment a numeric key.

    Args:
        key: Cache key
        amount: Amount to increment by (default: 1, cannot be 0)

    Returns:
        JSON string with new value
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    value = cache_client.incr(key, amount)
    return json.dumps({"key": key, "value": value, "incremented_by": amount})


@mcp.tool()
@handle_errors(logger)
def cache_decr(key: str, amount: int = 1) -> str:
    """
    Decrement a numeric key.

    Args:
        key: Cache key
        amount: Amount to decrement by (default: 1, must be positive)

    Returns:
        JSON string with new value
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    value = cache_client.decr(key, amount)
    return json.dumps({"key": key, "value": value, "decremented_by": amount})


@mcp.tool()
@handle_errors(logger)
def cache_flush() -> str:
    """
    Clear all keys in current database (USE WITH EXTREME CAUTION).

    Returns:
        JSON string with success status
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    result = cache_client.flush_db()
    return json.dumps({"success": result, "warning": "All keys have been deleted"})


@mcp.tool()
@handle_errors(logger)
def cache_info() -> str:
    """
    Get Redis server information and statistics.

    Returns:
        JSON string with server info
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    info = cache_client.info()

    # Extract key metrics
    summary = {
        "version": info.get("redis_version"),
        "uptime_days": info.get("uptime_in_days"),
        "connected_clients": info.get("connected_clients"),
        "used_memory_human": info.get("used_memory_human"),
        "total_commands_processed": info.get("total_commands_processed"),
        "keyspace": info.get("db0", {}),
    }

    return json.dumps(summary, indent=2)


@mcp.tool()
@handle_errors(logger)
def cache_ping() -> str:
    """
    Ping Redis to check connection status.

    Returns:
        JSON string with connection status
    """
    if not cache_client:
        return json.dumps({"error": "Cache client not initialized"})

    try:
        result = cache_client.ping()
        return json.dumps({"success": result, "message": "Redis is responsive"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def main() -> None:
    """Main entry point for Frappe MCP Server."""
    try:
        if not cache_client:
            logger.error("Server starting with errors - some features unavailable")

        logger.info("Starting Frappe MCP Server...")
        mcp.run()

    except KeyboardInterrupt:
        log_server_shutdown(logger, "Frappe Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if cache_client:
            cache_client.close()


if __name__ == "__main__":
    main()
