#!/usr/bin/env python3
"""
File System MCP Server - Production Ready
Provides local file system operations including reading, writing, and directory listing
Python >=3.10 compatible
"""

import json
import sys
import mimetypes
import hashlib
import fnmatch
from pathlib import Path
from typing import Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.logging_config import (
    setup_logging,
    log_server_startup,
    log_server_shutdown,
)
from servers.config import load_env_file
from servers.base_client import validate_non_empty
from servers.error_handler import MCPErrorHandler, safe_json_dumps, validate_file_path

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "file_server.log"
logger = setup_logging("FileServer", log_file=log_file)

load_env_file()
mcp = FastMCP("File System Server")


class FileSystemClient:
    """File system client with security and error handling."""

    def __init__(self, allowed_paths: list[str] | None = None) -> None:
        """
        Initialize file system client with security restrictions.

        Args:
            allowed_paths: List of allowed base paths for security (None = no restrictions)
        """
        self.allowed_paths = allowed_paths or []
        self.logger = logger

        # Default allowed paths for security - expanded to include common user directories
        if not self.allowed_paths:
            home_dir = str(Path.home())
            self.allowed_paths = [
                home_dir,  # User home directory
                "/tmp",  # Temporary directory
                str(project_root),  # Current project
                "/home",  # All user home directories
                "/opt",  # Optional software packages
                "/usr/local",  # Local installations
                "/var/log",  # Log files (read-only)
                "/media",  # Removable media
                "/mnt",  # Mount points
            ]

        # Define restricted paths that should never be accessible
        self.restricted_paths = [
            "/etc",  # System configuration
            "/sys",  # System files
            "/proc",  # Process information
            "/dev",  # Device files
            "/root",  # Root home (security)
            "/boot",  # Boot files
            "/lib",  # System libraries
            "/lib64",  # System libraries (64-bit)
            "/sbin",  # System binaries
            "/usr/sbin",  # System binaries
        ]

        self.logger.info(f"File server initialized with allowed paths: {self.allowed_paths}")
        self.logger.info(f"Restricted paths: {self.restricted_paths}")

    def _validate_path(self, file_path: str, allow_write: bool = False) -> Path:
        """
        Validate and resolve file path with security checks.

        Args:
            file_path: Path to validate
            allow_write: Whether write operations are allowed (stricter checks)

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is not allowed or invalid
        """
        try:
            if not file_path or not file_path.strip():
                raise ValueError("Path cannot be empty")

            # Handle relative paths and expand user home
            path = Path(file_path).expanduser().resolve()
            path_str = str(path)

            # Security check: ensure path is not in restricted directories
            for restricted_path in self.restricted_paths:
                if path_str.startswith(restricted_path):
                    raise ValueError(
                        f"Access denied: '{file_path}' (resolved to '{path}') is in restricted directory '{restricted_path}'. "
                        f"This directory contains system files and cannot be accessed for security reasons."
                    )

            # Security check: ensure path is within allowed directories
            if self.allowed_paths:
                is_allowed = any(
                    path_str.startswith(allowed_path) for allowed_path in self.allowed_paths
                )
                if not is_allowed:
                    raise ValueError(
                        f"Path '{file_path}' (resolved to '{path}') is not in allowed directories. "
                        f"Allowed directories: {self.allowed_paths}. "
                        f"Please use a path within these directories."
                    )

            # Additional write protection for system directories
            if allow_write:
                write_restricted = [
                    "/var/log",  # Log files should be read-only
                    "/usr",  # System directories
                    "/bin",  # System binaries
                ]
                for restricted in write_restricted:
                    if path_str.startswith(restricted):
                        raise ValueError(
                            f"Write access denied: '{file_path}' (resolved to '{path}') is in protected system directory '{restricted}'. "
                            f"Writing to system directories is not allowed for security reasons."
                        )

            return path
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Invalid path '{file_path}': {e}")

    def read_file(self, file_path: str, encoding: str = "utf-8") -> dict[str, Any]:
        """
        Read file contents with metadata.

        Args:
            file_path: Path to file to read
            encoding: Text encoding (default: utf-8)

        Returns:
            Dictionary with file contents and metadata
        """
        try:
            path = self._validate_path(file_path)

            if not path.exists():
                # Check if it's a directory
                if path.parent.exists() and path.parent.is_dir():
                    # Suggest similar files
                    try:
                        similar_files = [
                            f.name
                            for f in path.parent.iterdir()
                            if f.is_file() and path.name.lower() in f.name.lower()
                        ]
                        suggestion = f"File not found: '{file_path}' (resolved to '{path}'). "
                        if similar_files:
                            suggestion += (
                                f"Similar files in the same directory: {similar_files[:5]}"
                            )
                        else:
                            suggestion += (
                                f"Directory '{path.parent}' exists but contains no similar files."
                            )
                    except (OSError, PermissionError):
                        suggestion = f"File not found: '{file_path}' (resolved to '{path}'). Please check the path."
                else:
                    suggestion = f"File not found: '{file_path}' (resolved to '{path}'). The parent directory does not exist."

                raise FileNotFoundError(suggestion)

            if not path.is_file():
                if path.is_dir():
                    raise ValueError(
                        f"Path '{file_path}' (resolved to '{path}') is a directory, not a file. Use list_directory to see its contents."
                    )
                else:
                    raise ValueError(
                        f"Path '{file_path}' (resolved to '{path}') exists but is not a regular file."
                    )

            # Check file size before reading
            stat = path.stat()
            if stat.st_size > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError(
                    f"File '{file_path}' is too large ({stat.st_size} bytes). Maximum file size is 10MB."
                )

            # Read file contents
            try:
                with open(path, "r", encoding=encoding) as f:
                    content = f.read()
            except UnicodeDecodeError as e:
                raise ValueError(
                    f"Cannot read file '{file_path}' with encoding '{encoding}': {e}. Try using a different encoding like 'latin-1' or 'cp1252'."
                )

            # Get file metadata
            mime_type, _ = mimetypes.guess_type(str(path))

            # Calculate file hash
            with open(path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            return {
                "content": content,
                "metadata": {
                    "path": str(path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "mime_type": mime_type,
                    "encoding": encoding,
                    "hash": file_hash,
                    "permissions": oct(stat.st_mode)[-3:],
                },
            }

        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            raise

    def write_file(
        self,
        file_path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True,
    ) -> dict[str, Any]:
        """
        Write content to file.

        Args:
            file_path: Path to file to write
            content: Content to write
            encoding: Text encoding (default: utf-8)
            create_dirs: Create parent directories if they don't exist

        Returns:
            Dictionary with write result and metadata
        """
        try:
            # Use stricter validation for write operations
            path = self._validate_path(file_path, allow_write=True)

            # Create parent directories if needed
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, "w", encoding=encoding) as f:
                f.write(content)

            # Get updated metadata
            stat = path.stat()

            return {
                "success": True,
                "path": str(path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "encoding": encoding,
            }

        except Exception as e:
            self.logger.error(f"Error writing file {file_path}: {e}")
            raise

    def list_directory(
        self, dir_path: str, include_hidden: bool = False, recursive: bool = False
    ) -> dict[str, Any]:
        """
        List directory contents.

        Args:
            dir_path: Path to directory to list
            include_hidden: Include hidden files and directories
            recursive: List contents recursively

        Returns:
            Dictionary with directory contents and metadata
        """
        try:
            path = self._validate_path(dir_path)

            if not path.exists():
                raise FileNotFoundError(f"Directory not found: {path}")

            if not path.is_dir():
                raise ValueError(f"Path is not a directory: {path}")

            items = []
            errors = []

            # Use rglob for recursive, iterdir for non-recursive
            iterator = path.rglob("*") if recursive else path.iterdir()

            for item in iterator:
                try:
                    # Skip hidden files if not included
                    if not include_hidden and item.name.startswith("."):
                        continue

                    # Validate each path
                    try:
                        self._validate_path(str(item))
                    except ValueError as e:
                        self.logger.debug(f"Skipping {item}: {e}")
                        continue

                    stat = item.stat()
                    items.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size if item.is_file() else None,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "permissions": oct(stat.st_mode)[-3:],
                        }
                    )
                except (PermissionError, OSError) as e:
                    error_msg = f"Cannot access {item}: {e}"
                    self.logger.warning(error_msg)
                    errors.append(error_msg)
                    continue

            return {
                "directory": str(path),
                "items": sorted(items, key=lambda x: (x["type"], x["name"])),
                "count": len(items),
                "errors": errors if errors else None,
            }

        except Exception as e:
            self.logger.error(f"Error listing directory {dir_path}: {e}")
            raise

    def get_file_info(self, file_path: str) -> dict[str, Any]:
        """
        Get detailed file or directory information.

        Args:
            file_path: Path to file or directory

        Returns:
            Dictionary with file/directory information
        """
        try:
            path = self._validate_path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"Path not found: {path}")

            stat = path.stat()
            mime_type, _ = mimetypes.guess_type(str(path))

            info = {
                "path": str(path),
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size": stat.st_size if path.is_file() else None,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
                "mime_type": mime_type if path.is_file() else None,
            }

            # Add parent directory info
            if path.parent != path:
                info["parent"] = str(path.parent)

            return info

        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {e}")
            raise

    def search_files(
        self,
        dir_path: str,
        pattern: str,
        include_hidden: bool = False,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """
        Search for files matching a pattern in a directory.

        Args:
            dir_path: Directory to search in
            pattern: File pattern to match (supports * and ? wildcards)
            include_hidden: Include hidden files
            max_depth: Maximum recursion depth (default: 5)

        Returns:
            Dictionary with matching files
        """
        try:
            path = self._validate_path(dir_path)

            if not path.exists():
                raise FileNotFoundError(f"Directory not found: {path}")

            if not path.is_dir():
                raise ValueError(f"Path is not a directory: {path}")

            matches = []
            errors = []
            searched_dirs = []

            def search_recursive(current_path: Path, current_depth: int = 0):
                """Recursively search directories with depth limit."""
                if current_depth >= max_depth:
                    self.logger.debug(f"Max depth reached at {current_path}")
                    return

                searched_dirs.append(str(current_path))

                try:
                    for item in current_path.iterdir():
                        try:
                            # Skip hidden files if not included
                            if not include_hidden and item.name.startswith("."):
                                continue

                            # Validate path access
                            try:
                                self._validate_path(str(item))
                            except ValueError as e:
                                self.logger.debug(f"Skipping {item}: {e}")
                                continue

                            # Check if item matches pattern
                            if fnmatch.fnmatch(item.name, pattern):
                                stat = item.stat()
                                matches.append(
                                    {
                                        "name": item.name,
                                        "path": str(item),
                                        "type": "directory" if item.is_dir() else "file",
                                        "size": stat.st_size if item.is_file() else None,
                                        "modified": datetime.fromtimestamp(
                                            stat.st_mtime
                                        ).isoformat(),
                                    }
                                )

                            # Recurse into subdirectories
                            if item.is_dir():
                                search_recursive(item, current_depth + 1)

                        except (PermissionError, OSError) as e:
                            error_msg = f"Cannot access {item}: {e}"
                            self.logger.debug(error_msg)
                            errors.append(error_msg)
                            continue

                except (PermissionError, OSError) as e:
                    error_msg = f"Cannot list directory {current_path}: {e}"
                    self.logger.warning(error_msg)
                    errors.append(error_msg)

            # Start recursive search
            search_recursive(path)

            return {
                "directory": str(path),
                "pattern": pattern,
                "matches": sorted(matches, key=lambda x: x["name"]),
                "count": len(matches),
                "max_depth": max_depth,
                "searched_directories": len(searched_dirs),
                "errors": errors if errors else None,
            }

        except Exception as e:
            self.logger.error(f"Error searching files in {dir_path}: {e}")
            raise

    def search_files_system_wide(
        self, pattern: str, include_hidden: bool = False, max_depth: int = 3
    ) -> dict[str, Any]:
        """
        Search for files system-wide within allowed directories.

        Args:
            pattern: File pattern to match (supports * and ? wildcards)
            include_hidden: Include hidden files
            max_depth: Maximum search depth per directory

        Returns:
            Dictionary with matching files from all allowed directories
        """
        try:
            matches = []
            errors = []
            searched_paths = []

            for allowed_path in self.allowed_paths:
                path = Path(allowed_path)

                # Skip if path doesn't exist
                if not path.exists():
                    self.logger.debug(f"Skipping non-existent path: {path}")
                    continue

                searched_paths.append(str(path))

                try:

                    def search_recursive(current_path: Path, current_depth: int = 0):
                        """Recursively search with depth limit."""
                        if current_depth >= max_depth:
                            return

                        try:
                            for item in current_path.iterdir():
                                try:
                                    # Skip hidden files if not included
                                    if not include_hidden and item.name.startswith("."):
                                        continue

                                    # Validate path
                                    try:
                                        self._validate_path(str(item))
                                    except ValueError:
                                        continue

                                    # Check pattern match
                                    if fnmatch.fnmatch(item.name, pattern):
                                        stat = item.stat()
                                        matches.append(
                                            {
                                                "name": item.name,
                                                "path": str(item),
                                                "type": "directory" if item.is_dir() else "file",
                                                "size": stat.st_size if item.is_file() else None,
                                                "modified": datetime.fromtimestamp(
                                                    stat.st_mtime
                                                ).isoformat(),
                                            }
                                        )

                                    # Recurse into subdirectories
                                    if item.is_dir():
                                        search_recursive(item, current_depth + 1)

                                except (PermissionError, OSError) as e:
                                    self.logger.debug(f"Cannot access {item}: {e}")
                                    continue

                        except (PermissionError, OSError) as e:
                            error_msg = f"Cannot list {current_path}: {e}"
                            self.logger.debug(error_msg)
                            errors.append(error_msg)

                    # Start search for this allowed path
                    search_recursive(path)

                except (PermissionError, OSError) as e:
                    error_msg = f"Permission denied accessing {path}: {e}"
                    self.logger.warning(error_msg)
                    errors.append(error_msg)
                    continue

            return {
                "pattern": pattern,
                "matches": sorted(matches, key=lambda x: x["name"]),
                "count": len(matches),
                "searched_paths": searched_paths,
                "max_depth": max_depth,
                "errors": errors if errors else None,
            }

        except Exception as e:
            self.logger.error(f"Error in system-wide search: {e}")
            raise


# Initialize client and error handler
file_client = FileSystemClient()
error_handler = MCPErrorHandler(logger)


@mcp.tool()
def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    Read the contents of a file from the local file system.

    Args:
        file_path: Path to the file to read (supports relative paths and ~ for home directory)
        encoding: Text encoding (default: utf-8). Common encodings: utf-8, latin-1, cp1252, ascii

    Returns:
        JSON string with file contents and metadata. Includes helpful error messages if file is not found.
    """
    try:
        # Validate file path first
        path_validation = validate_file_path(file_path, must_exist=True)
        if not path_validation["valid"]:
            error_response = error_handler.handle_file_operation_error(
                path_validation["error"], "read", file_path
            )
            return safe_json_dumps(error_response)

        validate_non_empty(file_path, "file_path")
        result = file_client.read_file(file_path, encoding)
        return safe_json_dumps(error_handler.create_success_response(result))

    except FileNotFoundError as e:
        logger.error(f"File not found in read_file: {e}")
        error_response = error_handler.handle_file_operation_error(str(e), "read", file_path)
        return safe_json_dumps(error_response)
    except ValueError as e:
        logger.error(f"Validation error in read_file: {e}")
        error_response = error_handler.handle_validation_error(str(e), "file_path", file_path)
        return safe_json_dumps(error_response)
    except Exception as e:
        logger.error(f"Unexpected error in read_file: {e}")
        error_response = error_handler.create_error_response(
            str(e), "unexpected_error", "Please check the file path and try again."
        )
        return safe_json_dumps(error_response)


@mcp.tool()
def write_file(
    file_path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True
) -> str:
    """
    Write content to a file on the local file system.

    Args:
        file_path: Path to the file to write (supports relative paths and ~ for home directory)
        content: Content to write to the file
        encoding: Text encoding (default: utf-8). Common encodings: utf-8, latin-1, cp1252, ascii
        create_dirs: Create parent directories if they don't exist (default: True)

    Returns:
        JSON string with write result and metadata. Includes helpful error messages if write fails.
    """
    try:
        validate_non_empty(file_path, "file_path")
        validate_non_empty(content, "content")
        result = file_client.write_file(file_path, content, encoding, create_dirs)
        return json.dumps(result, indent=2)
    except ValueError as e:
        logger.error(f"Validation error in write_file: {e}")
        return json.dumps(
            {
                "error": str(e),
                "type": "validation_error",
                "suggestion": "Check the file path and ensure it's within allowed directories. Writing to system directories is not allowed.",
            },
            indent=2,
        )
    except PermissionError as e:
        logger.error(f"Permission error in write_file: {e}")
        return json.dumps(
            {
                "error": str(e),
                "type": "permission_error",
                "suggestion": "Check file permissions or try writing to a different location.",
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Unexpected error in write_file: {e}")
        return json.dumps(
            {
                "error": str(e),
                "type": "unexpected_error",
                "suggestion": "Please check the file path and try again.",
            },
            indent=2,
        )


@mcp.tool()
def list_directory(dir_path: str, include_hidden: bool = False, recursive: bool = False) -> str:
    """
    List the contents of a directory.

    Args:
        dir_path: Path to the directory to list
        include_hidden: Include hidden files and directories (default: False)
        recursive: List contents recursively (default: False)

    Returns:
        JSON string with directory contents
    """
    try:
        validate_non_empty(dir_path, "dir_path")
        result = file_client.list_directory(dir_path, include_hidden, recursive)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in list_directory: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def get_file_info(file_path: str) -> str:
    """
    Get detailed information about a file or directory without reading its contents.

    Args:
        file_path: Path to the file or directory

    Returns:
        JSON string with file information
    """
    try:
        validate_non_empty(file_path, "file_path")
        result = file_client.get_file_info(file_path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_file_info: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def search_files(
    dir_path: str, pattern: str, include_hidden: bool = False, max_depth: int = 5
) -> str:
    """
    Search for files matching a pattern in a directory.

    Args:
        dir_path: Directory to search in
        pattern: File pattern to match (supports * and ? wildcards)
        include_hidden: Include hidden files (default: False)
        max_depth: Maximum search depth (default: 5)

    Returns:
        JSON string with matching files
    """
    try:
        validate_non_empty(dir_path, "dir_path")
        validate_non_empty(pattern, "pattern")

        result = file_client.search_files(dir_path, pattern, include_hidden, max_depth)
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error in search_files: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def search_files_system_wide(pattern: str, include_hidden: bool = False, max_depth: int = 3) -> str:
    """
    Search for files system-wide within allowed directories.

    Args:
        pattern: File pattern to match (supports * and ? wildcards)
        include_hidden: Include hidden files (default: False)
        max_depth: Maximum search depth to prevent infinite recursion (default: 3)

    Returns:
        JSON string with matching files from all allowed directories
    """
    try:
        validate_non_empty(pattern, "pattern")
        result = file_client.search_files_system_wide(pattern, include_hidden, max_depth)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in search_files_system_wide: {e}")
        return json.dumps({"error": str(e)}, indent=2)


def main():
    """Main entry point for the file server."""
    try:
        config = {
            "Allowed Paths": file_client.allowed_paths,
            "Security": "Path validation enabled",
            "Python Version": f"{sys.version_info.major}.{sys.version_info.minor}",
        }
        log_server_startup(logger, "File System Server", config)
        logger.info("File System MCP Server starting...")

        # Run the server
        mcp.run()

    except KeyboardInterrupt:
        logger.info("File System Server stopped by user")
    except Exception as e:
        logger.error(f"File System Server error: {e}")
        raise
    finally:
        log_server_shutdown(logger, "File System Server")


if __name__ == "__main__":
    main()
