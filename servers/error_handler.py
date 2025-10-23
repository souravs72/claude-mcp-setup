#!/usr/bin/env python3
"""
Enhanced Error Handling Utilities for MCP Servers
Provides better error handling, validation, and AI-agent friendly error messages
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class MCPErrorHandler:
    """Enhanced error handler for MCP operations with AI-agent friendly messages."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def handle_string_replacement_error(
        self,
        error_msg: str,
        file_path: str,
        old_string: str,
        new_string: str,
        context_lines: int = 3,
    ) -> Dict[str, Any]:
        """
        Handle string replacement errors with helpful suggestions.

        Args:
            error_msg: The error message from search_replace
            file_path: Path to the file being modified
            old_string: The string that was not found
            new_string: The replacement string
            context_lines: Number of context lines to show

        Returns:
            Dictionary with error information and suggestions
        """
        suggestions = []

        # Check if file exists
        if not Path(file_path).exists():
            suggestions.append(f"File '{file_path}' does not exist. Check the file path.")
            return {
                "error": f"File not found: {file_path}",
                "type": "file_not_found",
                "suggestion": "; ".join(suggestions),
                "file_path": file_path,
            }

        # Try to read the file and find similar strings
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find similar strings
            similar_strings = self._find_similar_strings(content, old_string)

            if similar_strings:
                suggestions.append(
                    f"Found similar strings in the file. Consider using one of these:"
                )
                suggestions.append(f"Similar strings: {similar_strings[:3]}")
            else:
                suggestions.append(
                    "No similar strings found. The exact text may not exist in the file."
                )

            # Check for common issues
            if len(old_string.strip()) == 0:
                suggestions.append("The old_string is empty. Provide the exact text to replace.")
            elif len(old_string) > 200:
                suggestions.append(
                    "The old_string is very long. Try using a shorter, unique portion."
                )
            elif "\n" in old_string and old_string.count("\n") > 5:
                suggestions.append(
                    "The old_string contains many newlines. Try using a smaller, unique portion."
                )

            # Provide context around the file
            lines = content.split("\n")
            suggestions.append(
                f"File has {len(lines)} lines. Use read_file to examine the content first."
            )

        except Exception as e:
            suggestions.append(f"Could not read file: {e}")

        return {
            "error": f"String replacement failed: {error_msg}",
            "type": "string_replacement_error",
            "suggestion": "; ".join(suggestions),
            "file_path": file_path,
            "old_string_preview": (
                old_string[:100] + "..." if len(old_string) > 100 else old_string
            ),
            "new_string_preview": (
                new_string[:100] + "..." if len(new_string) > 100 else new_string
            ),
        }

    def _find_similar_strings(self, content: str, target: str, threshold: float = 0.7) -> List[str]:
        """Find strings similar to the target in the content."""
        if not target.strip():
            return []

        lines = content.split("\n")
        similar = []

        # Simple similarity check based on common words
        target_words = set(target.lower().split())

        for line in lines:
            if len(line.strip()) < 5:  # Skip very short lines
                continue

            line_words = set(line.lower().split())
            if target_words and line_words:
                similarity = len(target_words.intersection(line_words)) / len(
                    target_words.union(line_words)
                )
                if similarity >= threshold:
                    similar.append(line.strip())

        return similar[:5]  # Return top 5 matches

    def handle_validation_error(
        self,
        error_msg: str,
        field_name: str,
        field_value: Any,
        expected_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle validation errors with helpful suggestions.

        Args:
            error_msg: The validation error message
            field_name: Name of the field that failed validation
            field_value: The value that failed validation
            expected_type: Expected type of the field

        Returns:
            Dictionary with error information and suggestions
        """
        suggestions = []

        # Type-specific suggestions
        if expected_type:
            if expected_type == "int" and isinstance(field_value, str):
                try:
                    int(field_value)
                    suggestions.append(
                        f"Convert string '{field_value}' to integer: int('{field_value}')"
                    )
                except ValueError:
                    suggestions.append(f"'{field_value}' is not a valid integer")
            elif expected_type == "list" and isinstance(field_value, str):
                suggestions.append(
                    f"Convert string to list: json.loads('{field_value}') or ['{field_value}']"
                )
            elif expected_type == "dict" and isinstance(field_value, str):
                suggestions.append(f"Convert string to dict: json.loads('{field_value}')")

        # Common validation issues
        if field_value is None:
            suggestions.append(f"Field '{field_name}' is required and cannot be None")
        elif field_value == "":
            suggestions.append(f"Field '{field_name}' cannot be empty")
        elif isinstance(field_value, str) and len(field_value.strip()) == 0:
            suggestions.append(f"Field '{field_name}' contains only whitespace")

        return {
            "error": f"Validation error for '{field_name}': {error_msg}",
            "type": "validation_error",
            "field_name": field_name,
            "field_value": str(field_value),
            "field_type": type(field_value).__name__,
            "expected_type": expected_type,
            "suggestion": (
                "; ".join(suggestions) if suggestions else "Check the field value and format"
            ),
        }

    def handle_file_operation_error(
        self, error_msg: str, operation: str, file_path: str
    ) -> Dict[str, Any]:
        """
        Handle file operation errors with helpful suggestions.

        Args:
            error_msg: The error message
            operation: The operation being performed (read, write, delete, etc.)
            file_path: Path to the file

        Returns:
            Dictionary with error information and suggestions
        """
        suggestions = []
        path = Path(file_path)

        if operation == "read":
            if not path.exists():
                suggestions.append(f"File '{file_path}' does not exist")
                if path.parent.exists():
                    suggestions.append(
                        f"Use list_directory('{path.parent}') to see available files"
                    )
            elif path.is_dir():
                suggestions.append(
                    f"'{file_path}' is a directory, not a file. Use list_directory instead"
                )
            elif not path.is_file():
                suggestions.append(f"'{file_path}' exists but is not a regular file")

        elif operation == "write":
            if not path.parent.exists():
                suggestions.append(f"Parent directory '{path.parent}' does not exist")
                suggestions.append("Use create_dirs=True to create parent directories")
            elif not path.parent.is_dir():
                suggestions.append(f"Parent path '{path.parent}' is not a directory")
            elif not path.parent.exists():
                suggestions.append("Check write permissions for the directory")

        elif operation == "delete":
            if not path.exists():
                suggestions.append(f"File '{file_path}' does not exist")
            elif path.is_dir():
                suggestions.append(f"'{file_path}' is a directory. Use rmdir or remove files first")

        return {
            "error": f"File {operation} error: {error_msg}",
            "type": "file_operation_error",
            "operation": operation,
            "file_path": file_path,
            "file_exists": path.exists(),
            "is_file": path.is_file() if path.exists() else False,
            "is_directory": path.is_dir() if path.exists() else False,
            "suggestion": (
                "; ".join(suggestions)
                if suggestions
                else f"Check the file path and permissions for {operation} operation"
            ),
        }

    def create_success_response(
        self,
        data: Any,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized success response.

        Args:
            data: The response data
            message: Optional success message
            metadata: Optional metadata

        Returns:
            Dictionary with success response
        """
        response = {"success": True, "data": data}

        if message:
            response["message"] = message

        if metadata:
            response["metadata"] = metadata

        return response

    def create_error_response(
        self,
        error_msg: str,
        error_type: str,
        suggestion: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized error response.

        Args:
            error_msg: The error message
            error_type: Type of error
            suggestion: Optional suggestion for fixing the error
            context: Optional context information

        Returns:
            Dictionary with error response
        """
        response = {"success": False, "error": error_msg, "type": error_type}

        if suggestion:
            response["suggestion"] = suggestion

        if context:
            response["context"] = context

        return response


def safe_json_dumps(data: Any, indent: int = 2) -> str:
    """
    Safely convert data to JSON string with error handling.

    Args:
        data: Data to convert to JSON
        indent: JSON indentation

    Returns:
        JSON string or error message
    """
    try:
        return json.dumps(data, indent=indent, default=str)
    except Exception as e:
        return json.dumps(
            {
                "error": f"Failed to serialize data to JSON: {e}",
                "type": "serialization_error",
                "suggestion": "Check if the data contains non-serializable objects",
            },
            indent=indent,
        )


def validate_file_path(file_path: str, must_exist: bool = False) -> Dict[str, Any]:
    """
    Validate a file path with helpful error messages.

    Args:
        file_path: Path to validate
        must_exist: Whether the file must exist

    Returns:
        Dictionary with validation result
    """
    if not file_path or not file_path.strip():
        return {
            "valid": False,
            "error": "File path cannot be empty",
            "suggestion": "Provide a valid file path",
        }

    try:
        path = Path(file_path).expanduser().resolve()

        if must_exist and not path.exists():
            return {
                "valid": False,
                "error": f"File does not exist: {file_path}",
                "resolved_path": str(path),
                "suggestion": "Check the file path or use list_directory to see available files",
            }

        return {
            "valid": True,
            "resolved_path": str(path),
            "exists": path.exists(),
            "is_file": path.is_file() if path.exists() else False,
            "is_directory": path.is_dir() if path.exists() else False,
        }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Invalid file path '{file_path}': {e}",
            "suggestion": "Check the file path format and ensure it's accessible",
        }
