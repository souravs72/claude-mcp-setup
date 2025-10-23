#!/usr/bin/env python3
"""
MCP Server Shutdown Script

Stops all running MCP server processes gracefully.
Excludes LSP servers which are managed by IDEs.
"""
import time
from pathlib import Path

import psutil

# Get the project root directory
project_root = Path(__file__).parent.parent

# MCP servers to manage (excludes lsp_server)
MCP_SERVERS = [
    "memory_cache_server",
    "goal_agent_server",
    "internet_server",
    "github_server",
    "frappe_server",
    "jira_server",
]


def find_server_processes() -> list[dict]:
    """Find all running MCP server processes (excludes lsp_server)"""
    server_processes = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["cmdline"] and len(proc.info["cmdline"]) >= 2:
                # Check if this is a Python process running one of our servers
                if "python" in proc.info["cmdline"][0].lower() and any(
                    "_server.py" in arg for arg in proc.info["cmdline"]
                ):

                    # Extract server name from command line
                    for arg in proc.info["cmdline"]:
                        if "_server.py" in arg:
                            server_name = Path(arg).stem

                            # Only include MCP servers, exclude lsp_server
                            if server_name in MCP_SERVERS:
                                server_processes.append(
                                    {
                                        "pid": proc.info["pid"],
                                        "name": server_name,
                                        "process": proc,
                                    }
                                )
                            break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return server_processes


def stop_servers() -> None:
    """Stop all MCP server processes"""
    print("Searching for running MCP server processes...")
    print("(Excluding lsp_server processes managed by IDEs)\n")

    server_processes = find_server_processes()

    if not server_processes:
        print("✓ No MCP server processes found running.")
        print("  All servers are already stopped.\n")
        return

    print(f"Found {len(server_processes)} MCP server process(es):")
    for server in server_processes:
        print(f"  • {server['name']} (PID: {server['pid']})")

    print("\nStopping servers...")

    # Try graceful shutdown first
    for server in server_processes:
        try:
            print(f"  → Sending SIGTERM to {server['name']} (PID: {server['pid']})")
            server["process"].terminate()
        except psutil.NoSuchProcess:
            print(f"  ✓ Process {server['name']} already terminated")
        except Exception as e:
            print(f"  ✗ Error terminating {server['name']}: {str(e)}")

    # Wait for graceful shutdown
    print("\nWaiting for graceful shutdown...")
    time.sleep(2)

    # Check which processes are still running and force kill if necessary
    still_running = []
    for server in server_processes:
        try:
            if server["process"].is_running():
                still_running.append(server)
        except psutil.NoSuchProcess:
            pass

    if still_running:
        print(
            f"\n⚠  {len(still_running)} process(es) still running, forcing termination..."
        )
        for server in still_running:
            try:
                print(f"  → Force killing {server['name']} (PID: {server['pid']})")
                server["process"].kill()
                server["process"].wait(timeout=5)
                print(f"  ✓ Successfully killed {server['name']}")
            except psutil.NoSuchProcess:
                print(f"  ✓ Process {server['name']} already terminated")
            except psutil.TimeoutExpired:
                print(f"  ✗ Timeout waiting for {server['name']} to terminate")
            except Exception as e:
                print(f"  ✗ Error force killing {server['name']}: {str(e)}")
    else:
        print("✓ All servers stopped gracefully")

    print("\n" + "=" * 50)
    print("✓ Server shutdown complete")
    print("=" * 50 + "\n")


def stop_servers_by_pid_file() -> bool:
    """Alternative method using PID files if they exist"""
    pid_dir = project_root / "pids"
    if not pid_dir.exists():
        return False

    pid_files = list(pid_dir.glob("*.pid"))
    if not pid_files:
        return False

    print(f"Found {len(pid_files)} PID file(s), attempting shutdown...\n")

    stopped_count = 0
    for pid_file in pid_files:
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())

            server_name = pid_file.stem

            # Skip lsp_server PID files
            if server_name == "lsp_server":
                continue

            try:
                proc = psutil.Process(pid)
                print(f"  → Stopping {server_name} (PID: {pid})")
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  ✓ Successfully stopped {server_name}")
                stopped_count += 1
            except psutil.NoSuchProcess:
                print(f"  ✓ Process {server_name} (PID: {pid}) not found")
            except psutil.TimeoutExpired:
                print(f"  → Timeout stopping {server_name}, force killing...")
                proc.kill()
                stopped_count += 1

            # Remove PID file
            pid_file.unlink()

        except (ValueError, FileNotFoundError) as e:
            print(f"  ✗ Error reading PID file {pid_file}: {str(e)}")
        except Exception as e:
            print(f"  ✗ Error stopping process from {pid_file}: {str(e)}")

    if stopped_count > 0:
        print(f"\n✓ Stopped {stopped_count} server(s) using PID files\n")
        return True

    return False


def print_status() -> None:
    """Print status of MCP servers"""
    print("=" * 50)
    print("MCP Server Status")
    print("=" * 50 + "\n")

    server_processes = find_server_processes()

    if not server_processes:
        print("✓ All MCP servers are stopped\n")
        return

    print(f"⚠  {len(server_processes)} MCP server(s) still running:")
    for server in server_processes:
        print(f"  • {server['name']} (PID: {server['pid']})")
    print()


if __name__ == "__main__":
    import sys

    print()
    print("=" * 50)
    print("MCP Server Shutdown Script")
    print("=" * 50)
    print()

    # Check for status flag
    if "--status" in sys.argv or "-s" in sys.argv:
        print_status()
        sys.exit(0)

    # Try PID file method first, then process search
    if not stop_servers_by_pid_file():
        stop_servers()
    else:
        # Double-check with process search
        remaining = find_server_processes()
        if remaining:
            print("Some servers still running, attempting process search...")
            stop_servers()

    # Print final status
    print_status()
