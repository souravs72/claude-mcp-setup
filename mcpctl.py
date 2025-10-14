#!/usr/bin/env python3
"""
mcpctl - Interactive CLI Toolkit for MCP Server Management

A unified command-line interface for managing MCP servers locally and in CI/CD.

Usage:
    mcpctl run          # Start all servers and dashboard (recommended)
    mcpctl start        # Validate server configuration
    mcpctl stop         # Stop all servers
    mcpctl status       # List running servers
    mcpctl dashboard    # Start dashboard only
    mcpctl logs github  # Tail logs for specific server
    mcpctl test         # Run quick integration checks
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from typing import List, Dict
import click

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
SERVERS_DIR = PROJECT_ROOT / "servers"
LOGS_DIR = PROJECT_ROOT / "logs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Server definitions
SERVERS = {
    "memory-cache": {
        "name": "Memory Cache Server",
        "script": SERVERS_DIR / "memory_cache_server.py",
        "log": LOGS_DIR / "memory_cache_server.log",
        "env_vars": ["REDIS_HOST", "REDIS_PORT"],
    },
    "goal-agent": {
        "name": "Goal Agent Server",
        "script": SERVERS_DIR / "goal_agent_server.py",
        "log": LOGS_DIR / "goal_agent_server.log",
        "env_vars": [],
    },
    "internet": {
        "name": "Internet Server",
        "script": SERVERS_DIR / "internet_server.py",
        "log": LOGS_DIR / "internet_server.log",
        "env_vars": ["GOOGLE_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"],
    },
    "github": {
        "name": "GitHub Server",
        "script": SERVERS_DIR / "github_server.py",
        "log": LOGS_DIR / "github_server.log",
        "env_vars": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    },
    "frappe": {
        "name": "Frappe Server",
        "script": SERVERS_DIR / "frappe_server.py",
        "log": LOGS_DIR / "frappe_server.log",
        "env_vars": ["FRAPPE_SITE_URL", "FRAPPE_API_KEY", "FRAPPE_API_SECRET"],
    },
    "jira": {
        "name": "Jira Server",
        "script": SERVERS_DIR / "jira_server.py",
        "log": LOGS_DIR / "jira_server.log",
        "env_vars": ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"],
    },
    "file-server": {
        "name": "File System Server",
        "script": SERVERS_DIR / "file_server.py",
        "log": LOGS_DIR / "file_server.log",
        "env_vars": [],
    },
}


# ANSI color codes
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(text: str) -> None:
    """Print a formatted header"""
    width = 60
    click.echo()
    click.echo(f"{Colors.BOLD}{'=' * width}{Colors.RESET}")
    click.echo(f"{Colors.BOLD}{text.center(width)}{Colors.RESET}")
    click.echo(f"{Colors.BOLD}{'=' * width}{Colors.RESET}")
    click.echo()


def print_success(text: str) -> None:
    """Print success message"""
    click.echo(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_error(text: str) -> None:
    """Print error message"""
    click.echo(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_warning(text: str) -> None:
    """Print warning message"""
    click.echo(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_info(text: str) -> None:
    """Print info message"""
    click.echo(f"{Colors.CYAN}ℹ{Colors.RESET} {text}")


def load_env() -> None:
    """Load environment variables from .env file"""
    try:
        from dotenv import load_dotenv

        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


def find_server_processes() -> List[Dict]:
    """Find all running MCP server processes"""
    try:
        import psutil
    except ImportError:
        print_error("psutil not installed. Install with: pip install psutil")
        return []

    server_processes = []
    server_names = [s.replace("-", "_") + "_server" for s in SERVERS.keys()]

    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            if proc.info["cmdline"] and len(proc.info["cmdline"]) >= 2:
                if "python" in proc.info["cmdline"][0].lower():
                    for arg in proc.info["cmdline"]:
                        if "_server.py" in arg:
                            server_name = Path(arg).stem
                            if server_name in server_names:
                                # Find the key in SERVERS
                                server_key = server_name.replace("_server", "").replace(
                                    "_", "-"
                                )
                                server_processes.append(
                                    {
                                        "key": server_key,
                                        "name": SERVERS[server_key]["name"],
                                        "pid": proc.info["pid"],
                                        "uptime": time.time()
                                        - proc.info["create_time"],
                                        "process": proc,
                                    }
                                )
                            break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return server_processes


def check_redis() -> bool:
    """Check if Redis is running"""
    try:
        import redis

        client = redis.Redis(host="localhost", port=6379, socket_connect_timeout=2)
        client.ping()
        return True
    except Exception:
        return False


# ──────────────────────────── CLI Commands ────────────────────────────


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--version", is_flag=True, help="Show version")
def cli(ctx, version):
    """mcpctl - MCP Server Management Toolkit"""
    if version:
        click.echo("mcpctl version 1.0.0")
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option(
    "--check-only", is_flag=True, help="Only check configuration without starting"
)
def start(check_only):
    """Start all MCP servers (validates configuration)"""
    print_header("MCP Server Configuration Check")

    load_env()

    # Check server files
    click.echo(f"{Colors.BOLD}Checking Server Files{Colors.RESET}")
    click.echo("─" * 60)

    all_found = True
    for key, server in SERVERS.items():
        if server["script"].exists():
            print_success(f"{server['name']}")
        else:
            print_error(f"{server['name']} - File not found")
            all_found = False
    click.echo()

    # Check environment variables
    click.echo(f"{Colors.BOLD}Checking Environment Variables{Colors.RESET}")
    click.echo("─" * 60)

    env_configured = True
    for key, server in SERVERS.items():
        if server["env_vars"]:
            click.echo(f"\n  {Colors.BOLD}{server['name']}{Colors.RESET}:")
            for var in server["env_vars"]:
                if os.getenv(var):
                    click.echo(f"    {Colors.GREEN}✓{Colors.RESET} {var}")
                else:
                    click.echo(f"    {Colors.RED}✗{Colors.RESET} {var}")
                    env_configured = False
    click.echo()

    # Check Redis
    click.echo(f"{Colors.BOLD}Checking Redis{Colors.RESET}")
    click.echo("─" * 60)
    redis_running = check_redis()
    if redis_running:
        print_success("Redis is running")
    else:
        print_warning("Redis is not running - Memory Cache Server will fail")
    click.echo()

    # Summary
    print_header("Configuration Summary")

    if all_found:
        print_success(f"Server Files: All {len(SERVERS)} found")
    else:
        print_error("Some server files are missing")

    if env_configured:
        print_success("Environment: All variables configured")
    else:
        print_warning("Some environment variables are missing")

    if redis_running:
        print_success("Redis: Running")
    else:
        print_warning("Redis: Not running")

    click.echo()

    if not all_found:
        print_error("Cannot start servers - configuration issues detected")
        sys.exit(1)

    if check_only:
        print_info("Configuration check complete (--check-only mode)")
        sys.exit(0)

    # Info about MCP servers
    click.echo(f"{Colors.BOLD}Important Note:{Colors.RESET}")
    click.echo("─" * 60)
    click.echo("MCP servers are started automatically by Claude Desktop via stdio.")
    click.echo("They don't need to be manually started as background processes.")
    click.echo()
    click.echo("To use these servers:")
    click.echo("  1. Configure Claude Desktop (see CONFIGURATION.md)")
    click.echo("  2. Restart Claude Desktop")
    click.echo("  3. Servers will auto-start when needed")
    click.echo()
    print_success("Configuration is ready for Claude Desktop integration")
    click.echo()


@cli.command()
def stop():
    """Stop all running MCP servers"""
    print_header("Stopping MCP Servers")

    try:
        import psutil
    except ImportError:
        print_error("psutil not installed. Install with: pip install psutil")
        sys.exit(1)

    click.echo("Searching for running server processes...")
    click.echo()

    server_processes = find_server_processes()

    if not server_processes:
        print_success("No MCP server processes found running")
        click.echo()
        return

    click.echo(f"Found {len(server_processes)} server(s) running:")
    for server in server_processes:
        click.echo(f"  • {server['name']} (PID: {server['pid']})")
    click.echo()

    click.echo("Stopping servers...")

    # Graceful shutdown
    for server in server_processes:
        try:
            click.echo(
                f"  → Sending SIGTERM to {server['name']} (PID: {server['pid']})"
            )
            server["process"].terminate()
        except psutil.NoSuchProcess:
            print_success(f"Process {server['name']} already terminated")
        except Exception as e:
            print_error(f"Error terminating {server['name']}: {e}")

    # Wait for graceful shutdown
    click.echo("\nWaiting for graceful shutdown...")
    time.sleep(2)

    # Force kill if necessary
    still_running = []
    for server in server_processes:
        try:
            if server["process"].is_running():
                still_running.append(server)
        except psutil.NoSuchProcess:
            pass

    if still_running:
        print_warning(
            f"{len(still_running)} process(es) still running, forcing termination..."
        )
        for server in still_running:
            try:
                click.echo(f"  → Force killing {server['name']} (PID: {server['pid']})")
                server["process"].kill()
                server["process"].wait(timeout=5)
                print_success(f"Killed {server['name']}")
            except Exception as e:
                print_error(f"Error force killing {server['name']}: {e}")
    else:
        print_success("All servers stopped gracefully")

    click.echo()
    print_success("Server shutdown complete")
    click.echo()


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def status(verbose):
    """List running MCP servers and their status"""
    print_header("MCP Server Status")

    load_env()

    server_processes = find_server_processes()

    if not server_processes:
        print_info("No MCP servers currently running")
        click.echo()

        if verbose:
            click.echo(f"{Colors.BOLD}Available Servers:{Colors.RESET}")
            click.echo("─" * 60)
            for key, server in SERVERS.items():
                click.echo(f"  • {server['name']}")
                click.echo(f"    Script: {server['script']}")
                if server["env_vars"]:
                    click.echo(f"    Env vars: {', '.join(server['env_vars'])}")
                click.echo()
    else:
        click.echo(
            f"{Colors.GREEN}{len(server_processes)} server(s) running:{Colors.RESET}\n"
        )

        for server in server_processes:
            uptime_mins = int(server["uptime"] / 60)
            uptime_secs = int(server["uptime"] % 60)

            click.echo(
                f"  {Colors.GREEN}●{Colors.RESET} {Colors.BOLD}{server['name']}{Colors.RESET}"
            )
            click.echo(f"    PID: {server['pid']}")
            click.echo(f"    Uptime: {uptime_mins}m {uptime_secs}s")

            if verbose:
                log_file = SERVERS[server["key"]]["log"]
                if log_file.exists():
                    size = log_file.stat().st_size / 1024  # KB
                    click.echo(f"    Log: {log_file} ({size:.1f} KB)")
                else:
                    click.echo(f"    Log: {str(log_file)} (not created yet)")

            click.echo()

    # Check Redis status
    if verbose:
        click.echo(f"{Colors.BOLD}Dependencies:{Colors.RESET}")
        click.echo("─" * 60)
        redis_running = check_redis()
        if redis_running:
            print_success("Redis is running")
        else:
            print_warning("Redis is not running")
        click.echo()


@cli.command()
@click.argument("server", required=False)
@click.option("--lines", "-n", default=50, help="Number of lines to show (default: 50)")
@click.option("--follow", "-f", is_flag=True, help="Follow log output (like tail -f)")
@click.option("--all", "-a", is_flag=True, help="Show logs for all servers")
def logs(server, lines, follow, all):
    """View logs for a specific server or all servers

    Examples:
        mcpctl logs github
        mcpctl logs github -f
        mcpctl logs github -n 100
        mcpctl logs --all
    """
    print_header("MCP Server Logs")

    if all:
        # Show logs for all servers
        for key, srv in SERVERS.items():
            log_file = srv["log"]
            click.echo(f"\n{Colors.BOLD}{'─' * 60}{Colors.RESET}")
            click.echo(f"{Colors.BOLD}{srv['name']}{Colors.RESET}")
            click.echo(f"{Colors.BOLD}{'─' * 60}{Colors.RESET}\n")

            if log_file.exists():
                try:
                    with open(log_file, "r") as f:
                        log_lines = f.readlines()
                        display_lines = log_lines[-lines:]
                        for line in display_lines:
                            click.echo(line.rstrip())
                except Exception as e:
                    print_error(f"Error reading log: {e}")
            else:
                print_warning(f"Log file not found: {log_file}")

        click.echo()
        return

    if not server:
        print_error("Please specify a server name or use --all")
        click.echo("\nAvailable servers:")
        for key, srv in SERVERS.items():
            click.echo(f"  • {key:15} - {srv['name']}")
        click.echo()
        sys.exit(1)

    # Normalize server name
    server_key = server.lower().replace(" ", "-")

    if server_key not in SERVERS:
        print_error(f"Unknown server: {server}")
        click.echo("\nAvailable servers:")
        for key, srv in SERVERS.items():
            click.echo(f"  • {key:15} - {srv['name']}")
        click.echo()
        sys.exit(1)

    log_file = SERVERS[server_key]["log"]

    if not log_file.exists():
        print_warning(f"Log file not found: {log_file}")
        print_info("Server may not have been started yet or logs are not being written")
        click.echo()
        sys.exit(1)

    click.echo(f"Log file: {log_file}")
    click.echo(f"{Colors.BOLD}{'─' * 60}{Colors.RESET}\n")

    if follow:
        # Follow mode (like tail -f)
        try:
            subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)])
        except KeyboardInterrupt:
            click.echo("\n")
            print_info("Stopped following logs")
    else:
        # Show last N lines
        try:
            with open(log_file, "r") as f:
                log_lines = f.readlines()
                display_lines = log_lines[-lines:]
                for line in display_lines:
                    click.echo(line.rstrip())
        except Exception as e:
            print_error(f"Error reading log: {e}")

    click.echo()


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed test output")
@click.option(
    "--timeout", "-t", default=3, help="Timeout for each server test (seconds)"
)
def test(verbose, timeout):
    """Run quick integration checks on all servers"""
    print_header("MCP Server Integration Tests")

    test_script = SCRIPTS_DIR / "test_server_startup.py"

    if not test_script.exists():
        print_error(f"Test script not found: {test_script}")
        sys.exit(1)

    click.echo("Running startup tests for all servers...")
    click.echo(f"Timeout: {timeout}s per server\n")

    try:
        result = subprocess.run(
            [sys.executable, str(test_script)],
            cwd=PROJECT_ROOT,
            capture_output=not verbose,
            text=True,
        )

        if result.returncode == 0:
            if not verbose and result.stdout:
                click.echo(result.stdout)
            print_success("All tests passed!")
        else:
            if not verbose and result.stdout:
                click.echo(result.stdout)
            if result.stderr:
                click.echo(result.stderr)
            print_error("Some tests failed")
            sys.exit(1)

    except Exception as e:
        print_error(f"Error running tests: {e}")
        sys.exit(1)

    click.echo()


@cli.command()
def dashboard():
    """Start the web dashboard for monitoring servers"""
    print_header("Starting MCP Dashboard")

    dashboard_script = SERVERS_DIR / "dashboard_server.py"

    if not dashboard_script.exists():
        print_error(f"Dashboard script not found: {dashboard_script}")
        sys.exit(1)

    print_info("Starting web dashboard on http://localhost:8000")
    print_info("Press CTRL+C to stop the dashboard")
    click.echo()

    try:
        subprocess.run([sys.executable, str(dashboard_script)], cwd=PROJECT_ROOT)
    except KeyboardInterrupt:
        click.echo("\n")
        print_success("Dashboard stopped")
    except Exception as e:
        print_error(f"Failed to start dashboard: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--dashboard-only",
    is_flag=True,
    help="Start only the dashboard without starting servers",
)
@click.option(
    "--servers-only", is_flag=True, help="Start only the servers without the dashboard"
)
def run(dashboard_only, servers_only):
    """Start all MCP servers and dashboard with a single command"""
    print_header("Starting MCP Environment")

    load_env()

    # Configuration check
    click.echo(f"{Colors.BOLD}Pre-flight Checks{Colors.RESET}")
    click.echo("─" * 60)

    # Check server files
    all_found = True
    for key, server in SERVERS.items():
        if not server["script"].exists():
            print_error(f"{server['name']} - File not found")
            all_found = False

    if not all_found:
        print_error("Some server files are missing")
        sys.exit(1)

    # Check Redis
    redis_running = check_redis()
    if redis_running:
        print_success("Redis is running")
    else:
        print_warning("Redis is not running - Memory Cache Server may not work")

    click.echo()

    # Start servers unless dashboard-only
    if not dashboard_only:
        click.echo(f"{Colors.BOLD}Starting MCP Servers{Colors.RESET}")
        click.echo("─" * 60)

        # Get virtual environment Python
        venv_python = PROJECT_ROOT / "mcp-env" / "bin" / "python"
        if not venv_python.exists():
            venv_python = sys.executable  # Fall back to current Python

        started_servers = []
        failed_servers = []

        for key, server in SERVERS.items():
            try:
                # Check if already running
                server_processes = find_server_processes()
                if any(p["key"] == key for p in server_processes):
                    print_warning(f"{server['name']} is already running")
                    continue

                # Start server in background
                log_file = server["log"]
                log_file.parent.mkdir(parents=True, exist_ok=True)

                cmd = f"nohup {venv_python} {server['script']} > {log_file} 2>&1 &"

                subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                )

                # Give it a moment to start
                time.sleep(0.3)

                # Verify it started
                server_processes = find_server_processes()
                if any(p["key"] == key for p in server_processes):
                    print_success(f"Started {server['name']}")
                    started_servers.append(key)
                else:
                    print_warning(f"Started {server['name']} but unable to verify")
                    started_servers.append(key)

            except Exception as e:
                print_error(f"Failed to start {server['name']}: {e}")
                failed_servers.append(key)

        click.echo()
        if started_servers:
            print_success(f"Started {len(started_servers)} server(s)")
        if failed_servers:
            print_error(f"Failed to start {len(failed_servers)} server(s)")
        click.echo()

    # Start dashboard unless servers-only
    if not servers_only:
        click.echo(f"{Colors.BOLD}Starting Dashboard{Colors.RESET}")
        click.echo("─" * 60)

        dashboard_script = SERVERS_DIR / "dashboard_server.py"

        if not dashboard_script.exists():
            print_error(f"Dashboard script not found: {dashboard_script}")
            sys.exit(1)

        print_info("Dashboard URL: http://localhost:8000")
        print_info("Press CTRL+C to stop the dashboard")
        click.echo()

        try:
            subprocess.run([sys.executable, str(dashboard_script)], cwd=PROJECT_ROOT)
        except KeyboardInterrupt:
            click.echo("\n")
            print_header("Shutting Down")
            print_info("Dashboard stopped")

            if not dashboard_only:
                click.echo("\nMCP servers are still running in the background.")
                click.echo("To stop them, run:")
                click.echo(f"  {Colors.CYAN}mcpctl stop{Colors.RESET}")
            click.echo()
        except Exception as e:
            print_error(f"Failed to start dashboard: {e}")
            sys.exit(1)
    else:
        click.echo()
        print_success("All servers started in background")
        click.echo()
        print_info("To view server status:")
        click.echo(f"  {Colors.CYAN}mcpctl status{Colors.RESET}")
        click.echo()
        print_info("To start the dashboard:")
        click.echo(f"  {Colors.CYAN}mcpctl dashboard{Colors.RESET}")
        click.echo()
        print_info("To stop all servers:")
        click.echo(f"  {Colors.CYAN}mcpctl stop{Colors.RESET}")
        click.echo()


@cli.command()
def config():
    """Show current configuration and environment"""
    print_header("MCP Configuration")

    load_env()

    # Project info
    click.echo(f"{Colors.BOLD}Project Information:{Colors.RESET}")
    click.echo("─" * 60)
    click.echo(f"  Project Root: {PROJECT_ROOT}")
    click.echo(f"  Servers Dir:  {SERVERS_DIR}")
    click.echo(f"  Logs Dir:     {LOGS_DIR}")
    click.echo()

    # Server list
    click.echo(f"{Colors.BOLD}Available Servers:{Colors.RESET}")
    click.echo("─" * 60)
    for key, server in SERVERS.items():
        exists = "✓" if server["script"].exists() else "✗"
        click.echo(f"  {exists} {server['name']}")
        click.echo(f"     Key: {key}")
        click.echo(f"     Script: {server['script'].name}")
        if server["env_vars"]:
            click.echo(f"     Env vars: {', '.join(server['env_vars'])}")
        click.echo()

    # Environment status
    click.echo(f"{Colors.BOLD}Environment Variables:{Colors.RESET}")
    click.echo("─" * 60)
    for key, server in SERVERS.items():
        if server["env_vars"]:
            click.echo(f"  {server['name']}:")
            for var in server["env_vars"]:
                is_set = bool(os.getenv(var))
                status = (
                    f"{Colors.GREEN}✓{Colors.RESET}"
                    if is_set
                    else f"{Colors.RED}✗{Colors.RESET}"
                )
                value = "***" if is_set else "not set"
                click.echo(f"    {status} {var}: {value}")
            click.echo()

    # Redis status
    click.echo(f"{Colors.BOLD}Dependencies:{Colors.RESET}")
    click.echo("─" * 60)
    redis_running = check_redis()
    if redis_running:
        print_success("Redis: Running on localhost:6379")
    else:
        print_warning("Redis: Not running")
    click.echo()


@cli.command()
@click.argument("server")
def restart(server):
    """Restart a specific server (stop then validate config)"""
    print_header(f"Restarting {server}")

    # Normalize server name
    server_key = server.lower().replace(" ", "-")

    if server_key not in SERVERS:
        print_error(f"Unknown server: {server}")
        click.echo("\nAvailable servers:")
        for key, srv in SERVERS.items():
            click.echo(f"  • {key:15} - {srv['name']}")
        click.echo()
        sys.exit(1)

    server_info = SERVERS[server_key]

    # Find and stop the server

    server_processes = find_server_processes()
    found = False

    for proc in server_processes:
        if proc["key"] == server_key:
            found = True
            click.echo(f"Stopping {server_info['name']} (PID: {proc['pid']})...")
            try:
                proc["process"].terminate()
                proc["process"].wait(timeout=5)
                print_success(f"Stopped {server_info['name']}")
            except Exception as e:
                print_error(f"Error stopping server: {e}")
                sys.exit(1)

    if not found:
        print_warning(f"{server_info['name']} is not currently running")

    click.echo()
    print_info("MCP servers are managed by Claude Desktop via stdio")
    print_info("The server will restart automatically when Claude Desktop needs it")
    click.echo()


def main():
    """Entry point for mcpctl"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n")
        print_warning("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
