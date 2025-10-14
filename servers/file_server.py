#!/usr/bin/env python3
"""
File System MCP Server - Production Ready
Provides local file system operations including reading, writing, and directory listing
"""

import json
import sys
import mimetypes
import hashlib
from pathlib import Path
from typing import Any, Optional, List, Dict
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

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "file_server.log"
logger = setup_logging("FileServer", log_file=log_file)

load_env_file()
mcp = FastMCP("File System Server")


class FileSystemClient:
    """File system client with security and error handling."""

    def __init__(self, allowed_paths: Optional[List[str]] = None) -> None:
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

        self.logger.info(
            f"File server initialized with allowed paths: {self.allowed_paths}"
        )
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
            path = Path(file_path).resolve()
            path_str = str(path)

            # Security check: ensure path is not in restricted directories
            for restricted_path in self.restricted_paths:
                if path_str.startswith(restricted_path):
                    raise ValueError(
                        f"Access denied: {path} is in restricted directory {restricted_path}"
                    )

            # Security check: ensure path is within allowed directories
            if self.allowed_paths:
                is_allowed = any(
                    path_str.startswith(allowed_path)
                    for allowed_path in self.allowed_paths
                )
                if not is_allowed:
                    raise ValueError(
                        f"Path {path} is not in allowed directories: {self.allowed_paths}"
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
                            f"Write access denied: {path} is in protected system directory {restricted}"
                        )

            return path
        except Exception as e:
            raise ValueError(f"Invalid path {file_path}: {e}")

    def read_file(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
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
                raise FileNotFoundError(f"File not found: {path}")

            if not path.is_file():
                raise ValueError(f"Path is not a file: {path}")

            # Read file contents
            with open(path, "r", encoding=encoding) as f:
                content = f.read()

            # Get file metadata
            stat = path.stat()
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
        """
        List directory contents.

        Args:
            dir_path: Path to directory to list
            include_hidden: Include hidden files/directories
            recursive: List recursively

        Returns:
            Dictionary with directory contents
        """
        try:
            path = self._validate_path(dir_path)

            if not path.exists():
                raise FileNotFoundError(f"Directory not found: {path}")

            if not path.is_dir():
                raise ValueError(f"Path is not a directory: {path}")

            contents = []

            if recursive:
                for item in path.rglob("*"):
                    if not include_hidden and item.name.startswith("."):
                        continue

                    stat = item.stat()
                    contents.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size if item.is_file() else None,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "permissions": oct(stat.st_mode)[-3:],
                        }
                    )
            else:
                for item in path.iterdir():
                    if not include_hidden and item.name.startswith("."):
                        continue

                    stat = item.stat()
                    contents.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size if item.is_file() else None,
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "permissions": oct(stat.st_mode)[-3:],
                        }
                    )

            return {
                "directory": str(path),
                "count": len(contents),
                "contents": sorted(contents, key=lambda x: (x["type"], x["name"])),
            }

        except Exception as e:
            self.logger.error(f"Error listing directory {dir_path}: {e}")
            raise

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed file information without reading content.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file information
        """
        try:
            path = self._validate_path(file_path)

            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")

            stat = path.stat()
            mime_type, _ = mimetypes.guess_type(str(path))

            return {
                "path": str(path),
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "mime_type": mime_type,
                "permissions": oct(stat.st_mode)[-3:],
                "owner": stat.st_uid,
                "group": stat.st_gid,
            }

        except Exception as e:
            self.logger.error(f"Error getting file info {file_path}: {e}")
            raise

    def search_files_system_wide(
        self, pattern: str, include_hidden: bool = False, max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Search for files system-wide within allowed directories.

        Args:
            pattern: File pattern to match (supports * and ? wildcards)
            include_hidden: Include hidden files
            max_depth: Maximum search depth to prevent infinite recursion

        Returns:
            Dictionary with matching files
        """
        try:
            import fnmatch

            matches = []

            for allowed_path in self.allowed_paths:
                path = Path(allowed_path)
                if not path.exists():
                    continue

                try:
                    # Use rglob with depth limit
                    for item in path.rglob("*"):
                        # Check depth
                        depth = len(item.relative_to(path).parts)
                        if depth > max_depth:
                            continue

                        # Skip hidden files if not requested
                        if not include_hidden and item.name.startswith("."):
                            continue

                        # Check if path is still allowed (avoid restricted subdirectories)
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
                except (PermissionError, OSError) as e:
                    self.logger.warning(f"Permission denied accessing {path}: {e}")
                    continue

            return {
                "pattern": pattern,
                "matches": sorted(matches, key=lambda x: x["name"]),
                "count": len(matches),
                "searched_paths": self.allowed_paths,
            }

        except Exception as e:
            self.logger.error(f"Error in system-wide search: {e}")
            raise


# Initialize client
file_client = FileSystemClient()


@mcp.tool()
def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    Read the contents of a file from the local file system.

    Args:
        file_path: Path to the file to read
        encoding: Text encoding (default: utf-8)

    Returns:
        JSON string with file contents and metadata
    """
    try:
        validate_non_empty(file_path, "file_path")
        result = file_client.read_file(file_path, encoding)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in read_file: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def write_file(
    file_path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True
) -> str:
    """
    Write content to a file on the local file system.

    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        encoding: Text encoding (default: utf-8)
        create_dirs: Create parent directories if they don't exist (default: True)

    Returns:
        JSON string with write result and metadata
    """
    try:
        validate_non_empty(file_path, "file_path")
        validate_non_empty(content, "content")
        result = file_client.write_file(file_path, content, encoding, create_dirs)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in write_file: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def list_directory(
    dir_path: str, include_hidden: bool = False, recursive: bool = False
) -> str:
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
def search_files(dir_path: str, pattern: str, include_hidden: bool = False) -> str:
    """
    Search for files matching a pattern in a directory.

    Args:
        dir_path: Directory to search in
        pattern: File pattern to match (supports * and ? wildcards)
        include_hidden: Include hidden files (default: False)

    Returns:
        JSON string with matching files
    """
    try:
        validate_non_empty(dir_path, "dir_path")
        validate_non_empty(pattern, "pattern")

        path = file_client._validate_path(dir_path)

        if not path.exists() or not path.is_dir():
            raise ValueError(f"Directory not found: {path}")

        import fnmatch

        matches = []

        for item in path.rglob("*"):
            if not include_hidden and item.name.startswith("."):
                continue

            if fnmatch.fnmatch(item.name, pattern):
                stat = item.stat()
                matches.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        return json.dumps(
            {
                "directory": str(path),
                "pattern": pattern,
                "matches": sorted(matches, key=lambda x: x["name"]),
                "count": len(matches),
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in search_files: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
def search_files_system_wide(
    pattern: str, include_hidden: bool = False, max_depth: int = 3
) -> str:
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
        result = file_client.search_files_system_wide(
            pattern, include_hidden, max_depth
        )
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
