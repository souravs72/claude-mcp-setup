#!/usr/bin/env python3
"""
MCP Server Health Check Script
Tests all servers for proper initialization and basic functionality
"""

import sys
from pathlib import Path
from typing import Tuple, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from servers.logging_config import setup_logging

logger = setup_logging("ServerHealthCheck")


def test_imports() -> Tuple[bool, List[str]]:
    """Test if all server modules can be imported."""
    logger.info("Testing module imports...")
    errors = []

    modules = [
        ("servers.logging_config", "Logging Config"),
        ("servers.config", "Configuration Management"),
        ("servers.base_client", "Base Client"),
        ("servers.frappe_server", "Frappe Server"),
        ("servers.github_server", "GitHub Server"),
        ("servers.jira_server", "Jira Server"),
        ("servers.internet_server", "Internet Server"),
        ("servers.goal_agent_server", "Goal Agent Server"),
    ]

    for module_name, display_name in modules:
        try:
            __import__(module_name)
            logger.info(f"✓ {display_name}")
        except ImportError as e:
            error_msg = f"✗ {display_name}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"✗ {display_name}: Unexpected error - {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return len(errors) == 0, errors


def test_configurations() -> Tuple[bool, List[str]]:
    """Test configuration loading and validation."""
    logger.info("Testing configurations...")
    errors = []

    from servers.config import (
        FrappeConfig,
        GitHubConfig,
        JiraConfig,
        InternetConfig,
        load_env_file,
    )

    # Load environment
    load_env_file()

    configs = [
        (FrappeConfig, "Frappe"),
        (GitHubConfig, "GitHub"),
        (JiraConfig, "Jira"),
        (InternetConfig, "Internet"),
    ]

    for config_class, name in configs:
        try:
            config = config_class()
            is_valid, validation_errors = config.validate()

            if is_valid:
                logger.info(f"✓ {name} Configuration: Valid")
            else:
                error_msg = f"✗ {name} Configuration: {', '.join(validation_errors)}"
                logger.warning(error_msg)
                errors.append(error_msg)
        except Exception as e:
            error_msg = f"✗ {name} Configuration: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return len(errors) == 0, errors


def test_client_initialization() -> Tuple[bool, List[str]]:
    """Test if clients can be initialized."""
    logger.info("Testing client initialization...")
    errors = []

    clients = [
        ("frappe_server", "frappe_client", "Frappe"),
        ("github_server", "github_client", "GitHub"),
        ("jira_server", "jira_client", "Jira"),
        ("internet_server", "internet_client", "Internet"),
        ("goal_agent_server", "agent", "Goal Agent"),
    ]

    for module_name, client_name, display_name in clients:
        try:
            module = __import__(f"servers.{module_name}", fromlist=[client_name])
            client = getattr(module, client_name)

            if client is not None:
                logger.info(f"✓ {display_name} Client: Initialized")
            else:
                error_msg = (
                    f"⚠ {display_name} Client: Not initialized (check configuration)"
                )
                logger.warning(error_msg)
                errors.append(error_msg)
        except Exception as e:
            error_msg = f"✗ {display_name} Client: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return len(errors) == 0, errors


def test_logging_setup() -> Tuple[bool, List[str]]:
    """Test logging configuration."""
    logger.info("Testing logging setup...")
    errors = []

    log_dir = Path("logs")

    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True)
            logger.info("✓ Created logs directory")
        except Exception as e:
            error_msg = f"✗ Could not create logs directory: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors

    if not log_dir.is_dir():
        error_msg = "✗ logs path exists but is not a directory"
        logger.error(error_msg)
        errors.append(error_msg)
        return False, errors

    # Test write permissions
    test_file = log_dir / "test.log"
    try:
        test_file.write_text("test")
        test_file.unlink()
        logger.info("✓ Logs directory writable")
    except Exception as e:
        error_msg = f"✗ Logs directory not writable: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
        return False, errors

    logger.info("✓ Logging setup complete")
    return True, []


def test_mcp_tools() -> Tuple[bool, List[str]]:
    """Test if MCP tools are properly registered."""
    logger.info("Testing MCP tool registration...")
    errors = []

    servers = [
        (
            "frappe_server",
            ["frappe_get_document", "frappe_get_list", "frappe_create_document"],
        ),
        ("github_server", ["list_repositories", "get_file_content", "create_issue"]),
        ("jira_server", ["jira_get_issue", "jira_search_issues", "jira_create_issue"]),
        ("internet_server", ["web_search", "web_fetch"]),
        ("goal_agent_server", ["create_goal", "break_down_goal", "get_next_tasks"]),
        ("memory_cache_server", ["cache_set", "cache_get", "cache_delete"]),
    ]

    for module_name, expected_tools in servers:
        try:
            module = __import__(f"servers.{module_name}", fromlist=["mcp"])
            mcp = getattr(module, "mcp")

            # Check if tools are registered (FastMCP uses _tool_manager._tools)
            registered_tools = []
            if hasattr(mcp, "_tool_manager") and hasattr(mcp._tool_manager, "_tools"):
                registered_tools = list(mcp._tool_manager._tools.keys())
            elif hasattr(mcp, "_tools"):
                # Fallback for other MCP implementations
                registered_tools = list(mcp._tools.keys())

            missing_tools = [
                tool for tool in expected_tools if tool not in registered_tools
            ]

            if not missing_tools:
                logger.info(
                    f"✓ {module_name}: All tools registered ({len(registered_tools)} total)"
                )
            else:
                error_msg = (
                    f"✗ {module_name}: Missing tools - {', '.join(missing_tools)}"
                )
                logger.error(error_msg)
                errors.append(error_msg)

        except Exception as e:
            error_msg = f"✗ {module_name}: Could not check tools - {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return len(errors) == 0, errors


def print_summary(results: dict):
    """Print test summary."""
    print("\n" + "=" * 70)
    print("SERVER HEALTH CHECK SUMMARY")
    print("=" * 70)

    all_passed = True

    for test_name, (passed, errors) in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"\n{test_name}: {status}")

        if errors:
            all_passed = False
            for error in errors:
                print(f"  {error}")

    print("\n" + "=" * 70)

    if all_passed:
        print("✓ All tests passed! Servers are ready for production.")
    else:
        print("⚠ Some tests failed. Please review errors above.")
        print("\nNext steps:")
        print("  1. Check your .env file for missing variables")
        print("  2. Verify API credentials are correct")
        print("  3. Ensure all dependencies are installed")
        print("  4. Check logs/ directory permissions")

    print("=" * 70 + "\n")

    return all_passed


def main():
    """Run all health checks."""
    print("\n" + "=" * 70)
    print("MCP SERVER HEALTH CHECK")
    print("=" * 70 + "\n")

    results = {}

    # Run tests
    results["1. Module Imports"] = test_imports()
    results["2. Configuration Loading"] = test_configurations()
    results["3. Logging Setup"] = test_logging_setup()
    results["4. Client Initialization"] = test_client_initialization()
    results["5. MCP Tool Registration"] = test_mcp_tools()

    # Print summary
    all_passed = print_summary(results)

    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error during health check: {e}", exc_info=True)
        sys.exit(1)
