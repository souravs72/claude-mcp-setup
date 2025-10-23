#!/usr/bin/env python3
"""
Bash Execution MCP Server - Production Ready
Allows executing bash commands with proper working directory support and security restrictions
AI-Agent Friendly with improved error messages and validation
Python >=3.10 compatible
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.base_client import validate_non_empty
from servers.config import load_env_file
from servers.logging_config import (
    log_server_shutdown,
    log_server_startup,
    setup_logging,
)

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "bash_server.log"
logger = setup_logging("BashServer", log_file=log_file)

load_env_file()
mcp = FastMCP("Bash Execution Server")


class BashExecutorClient:
    """Bash command execution client with security and error handling."""

    def __init__(self, allowed_paths: List[str] | None = None) -> None:
        """
        Initialize bash executor client with security restrictions.

        Args:
            allowed_paths: List of allowed base paths for security (None = no restrictions)
        """
        self.allowed_paths = allowed_paths or []
        self.logger = logger
        self.default_cwd = str(Path.home())

        # Define restricted commands that should never be executed
        self.restricted_commands = [
            "rm -rf /",  # Dangerous deletion
            "mkfs",  # Format filesystem
            "dd if=",  # Disk operations
            "fdisk",  # Disk partitioning
            "parted",  # Disk partitioning
            "mount",  # Mount operations
            "umount",  # Unmount operations
            "chmod 777",  # Dangerous permissions
            "chown root",  # Ownership changes
            "passwd",  # Password changes
            "su ",  # User switching
            "sudo ",  # Privilege escalation
            "shutdown",  # System shutdown
            "reboot",  # System reboot
            "halt",  # System halt
            "init 0",  # System halt
            "init 6",  # System reboot
        ]

    def _validate_command(self, command: str) -> None:
        """
        Validate command for security and safety.

        Args:
            command: Command to validate

        Raises:
            ValueError: If command is restricted or dangerous
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")

        command_lower = command.lower().strip()

        # Check for restricted commands
        for restricted in self.restricted_commands:
            if command_lower.startswith(restricted.lower()):
                raise ValueError(
                    f"Command '{command}' is restricted for security reasons. "
                    f"Restricted pattern: '{restricted}'"
                )

        # Check for potentially dangerous patterns
        dangerous_patterns = [
            "rm -rf",
            "> /dev/",
            "&>/dev/",
            "exec",
            "eval",
            "source /",
            ". /",
        ]

        for pattern in dangerous_patterns:
            if pattern in command_lower:
                raise ValueError(
                    f"Command '{command}' contains potentially dangerous pattern '{pattern}'. "
                    f"Please use safer alternatives."
                )

    def _validate_path(self, path: str) -> Path:
        """
        Validate and resolve a path with security checks.

        Args:
            path: Path to validate

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is not allowed or invalid
        """
        if not path:
            raise ValueError("Path cannot be empty")

        try:
            resolved_path = Path(path).expanduser().resolve()
        except Exception as e:
            raise ValueError(f"Invalid path '{path}': {e}")

        # Security check: ensure path is within allowed directories
        if self.allowed_paths:
            is_allowed = any(
                str(resolved_path).startswith(str(allowed_path))
                for allowed_path in self.allowed_paths
            )
            if not is_allowed:
                raise ValueError(
                    f"Path '{path}' (resolved to '{resolved_path}') is not in allowed directories. "
                    f"Allowed directories: {self.allowed_paths}"
                )

        return resolved_path

    async def execute_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a bash command with proper error handling and security.

        Args:
            command: Bash command to execute
            cwd: Working directory (optional)
            timeout: Command timeout in seconds
            env: Environment variables to set

        Returns:
            Dictionary with execution results
        """
        try:
            # Validate command
            validate_non_empty(command, "command")
            self._validate_command(command)

            # Set working directory
            working_dir = cwd or self.default_cwd
            working_path = self._validate_path(working_dir)

            if not working_path.exists():
                return {
                    "success": False,
                    "error": f"Working directory does not exist: '{working_dir}' (resolved to '{working_path}')",
                    "command": command,
                    "suggestion": f"Please check if the directory exists or use a different path. Current working directory: {os.getcwd()}",
                }

            if not working_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: '{working_dir}' (resolved to '{working_path}')",
                    "command": command,
                    "suggestion": "Please provide a valid directory path for the working directory.",
                }

            # Validate timeout
            if timeout <= 0 or timeout > 300:  # Max 5 minutes
                return {
                    "success": False,
                    "error": f"Invalid timeout value: {timeout}. Must be between 1 and 300 seconds.",
                    "command": command,
                }

            # Prepare environment
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)

            self.logger.info(f"Executing command: '{command}' in '{working_path}'")

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(working_path),
                env=exec_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                self.logger.warning(f"Command timed out: {command}")
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "command": command,
                    "cwd": str(working_path),
                    "suggestion": "Try increasing the timeout value or breaking the command into smaller parts.",
                }

            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            result = {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "command": command,
                "cwd": str(working_path),
                "timestamp": datetime.now().isoformat(),
            }

            # Add helpful suggestions for common errors
            if not result["success"]:
                if "command not found" in stderr_text.lower():
                    result["suggestion"] = (
                        "The command was not found. Check if the command is installed or if the PATH is correct."
                    )
                elif "permission denied" in stderr_text.lower():
                    result["suggestion"] = (
                        "Permission denied. You may need to check file permissions or run with appropriate privileges."
                    )
                elif "no such file or directory" in stderr_text.lower():
                    result["suggestion"] = (
                        "File or directory not found. Check if the path exists and is accessible."
                    )

            if result["success"]:
                self.logger.info(f"Command succeeded: {command}")
            else:
                self.logger.warning(f"Command failed: {command} (exit code: {process.returncode})")

            return result

        except ValueError as e:
            # Validation errors
            error_msg = str(e)
            self.logger.error(f"Validation error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "command": command,
                "type": "validation_error",
            }
        except Exception as e:
            error_msg = f"Unexpected error executing command: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "command": command,
                "type": "execution_error",
            }

    async def execute_multiple_commands(
        self,
        commands: List[str | Dict[str, Any]],
        cwd: Optional[str] = None,
        stop_on_error: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute multiple bash commands in sequence.

        Args:
            commands: List of commands (strings or dicts with command, cwd, timeout)
            cwd: Default working directory
            stop_on_error: Whether to stop on first error

        Returns:
            Dictionary with execution results
        """
        results = []
        working_dir = cwd or self.default_cwd

        for i, cmd in enumerate(commands):
            if isinstance(cmd, dict):
                command = cmd.get("command")
                cmd_cwd = cmd.get("cwd", working_dir)
                timeout = cmd.get("timeout", 30)
            else:
                command = cmd
                cmd_cwd = working_dir
                timeout = 30

            result = await self.execute_command(command, cmd_cwd, timeout)
            result["index"] = i
            results.append(result)

            if stop_on_error and not result["success"]:
                self.logger.info(f"Stopping execution after error at command {i}")
                break

        success_count = sum(1 for r in results if r["success"])

        return {
            "success": success_count == len(commands),
            "total_commands": len(commands),
            "successful": success_count,
            "failed": len(commands) - success_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def check_directory(self, path: str) -> Dict[str, Any]:
        """
        Check if a directory exists and is accessible.

        Args:
            path: Directory path to check

        Returns:
            Dictionary with directory status
        """
        try:
            validate_non_empty(path, "path")
            dir_path = self._validate_path(path)

            return {
                "exists": dir_path.exists(),
                "is_directory": dir_path.is_dir() if dir_path.exists() else False,
                "readable": (os.access(dir_path, os.R_OK) if dir_path.exists() else False),
                "writable": (os.access(dir_path, os.W_OK) if dir_path.exists() else False),
                "path": str(dir_path),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            error_msg = f"Error checking directory: {str(e)}"
            self.logger.error(error_msg)
            return {
                "exists": False,
                "error": error_msg,
                "path": path,
            }

    async def list_directory(self, path: str) -> Dict[str, Any]:
        """
        List contents of a directory.

        Args:
            path: Directory path to list

        Returns:
            Dictionary with directory contents
        """
        try:
            validate_non_empty(path, "path")
            dir_path = self._validate_path(path)

            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Directory does not exist: {path}",
                    "path": str(dir_path),
                }

            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {path}",
                    "path": str(dir_path),
                }

            items = []
            for item in dir_path.iterdir():
                try:
                    stat_info = item.stat()
                    items.append(
                        {
                            "name": item.name,
                            "type": "directory" if item.is_dir() else "file",
                            "path": str(item),
                            "size": stat_info.st_size,
                            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                        }
                    )
                except (OSError, PermissionError):
                    # Skip items we can't access
                    continue

            return {
                "success": True,
                "path": str(dir_path),
                "items": items,
                "count": len(items),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            error_msg = f"Error listing directory: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "path": path,
            }

    async def which_command(self, command: str) -> Dict[str, Any]:
        """
        Find the full path of a command.

        Args:
            command: Command name to find

        Returns:
            Dictionary with command path information
        """
        try:
            validate_non_empty(command, "command")
            result = await self.execute_command(f"which {command}")

            return {
                "success": result["success"],
                "command": command,
                "path": result["stdout"].strip() if result["success"] else None,
                "found": result["success"],
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            error_msg = f"Error finding command: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "command": command,
            }


# Initialize client
bash_client = BashExecutorClient()


@mcp.tool()
async def execute_command(
    command: str,
    cwd: str | None = None,
    timeout: int = 30,
    env: dict[str, str] | None = None,
) -> str:
    """
    Execute a bash command with proper working directory support.

    Args:
        command: The bash command to execute
        cwd: Working directory (optional, defaults to home directory)
        timeout: Command timeout in seconds (default: 30)
        env: Environment variables to set (optional)

    Returns:
        JSON string with execution results including stdout, stderr, and return code
    """
    result = await bash_client.execute_command(command, cwd, timeout, env)
    return json.dumps(result, indent=2)


@mcp.tool()
async def execute_multiple_commands(
    commands: list[str | dict[str, Any]],
    cwd: str | None = None,
    stop_on_error: bool = True,
) -> str:
    """
    Execute multiple bash commands in sequence.

    Args:
        commands: List of commands (strings or dicts with command, cwd, timeout)
        cwd: Default working directory (optional)
        stop_on_error: Whether to stop execution on first error (default: True)

    Returns:
        JSON string with execution results for all commands
    """
    result = await bash_client.execute_multiple_commands(commands, cwd, stop_on_error)
    return json.dumps(result, indent=2)


@mcp.tool()
async def check_directory(path: str) -> str:
    """
    Check if a directory exists and is accessible.

    Args:
        path: Directory path to check

    Returns:
        JSON string with directory status information
    """
    result = await bash_client.check_directory(path)
    return json.dumps(result, indent=2)


@mcp.tool()
async def list_directory(path: str) -> str:
    """
    List contents of a directory.

    Args:
        path: Directory path to list

    Returns:
        JSON string with directory contents
    """
    result = await bash_client.list_directory(path)
    return json.dumps(result, indent=2)


@mcp.tool()
async def which_command(command: str) -> str:
    """
    Find the full path of a command using 'which'.

    Args:
        command: Command name to find

    Returns:
        JSON string with command path information
    """
    result = await bash_client.which_command(command)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    # Log startup
    config = {
        "default_cwd": bash_client.default_cwd,
        "allowed_paths": bash_client.allowed_paths,
    }
    log_server_startup(logger, "Bash Executor Server", config)

    try:
        # Run the server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        log_server_shutdown(logger, "Bash Executor Server")
