#!/usr/bin/env python3
"""
MCP Server Configuration Checker

Validates server files and environment setup.
MCP servers are started automatically by Claude Desktop via stdio protocol.

Usage:
    python scripts/start_all_servers.py          # Check configuration
    python scripts/start_all_servers.py --help   # Show detailed help
"""
import sys
import os
from pathlib import Path
from typing import NamedTuple

# Get the project root directory
project_root = Path(__file__).parent.parent
servers_dir = project_root / "servers"

class ServerConfig(NamedTuple):
    """Server configuration"""
    name: str
    script: Path
    env_vars: list[str]

# Server definitions
SERVERS = [
    ServerConfig(
        name="Internet Server",
        script=servers_dir / "internet_server.py",
        env_vars=["GOOGLE_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"]
    ),
    ServerConfig(
        name="GitHub Server",
        script=servers_dir / "github_server.py",
        env_vars=["GITHUB_PERSONAL_ACCESS_TOKEN"]
    ),
    ServerConfig(
        name="Frappe Server",
        script=servers_dir / "frappe_server.py",
        env_vars=["FRAPPE_SITE_URL", "FRAPPE_API_KEY", "FRAPPE_API_SECRET"]
    ),
    ServerConfig(
        name="Jira Server",
        script=servers_dir / "jira_server.py",
        env_vars=["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"]
    ),
    ServerConfig(
        name="Goal Agent Server",
        script=servers_dir / "goal_agent_server.py",
        env_vars=[]
    ),
]

def check_server_files() -> tuple[int, int]:
    """Check if server files exist"""
    print("Checking Server Files")
    print("─" * 60)
    
    found = 0
    total = len(SERVERS)
    
    for server in SERVERS:
        status = "✓" if server.script.exists() else "✗"
        print(f"  {status} {server.name}")
        if server.script.exists():
            found += 1
    
    print()
    return found, total

def check_environment() -> dict[str, dict[str, bool]]:
    """Check environment variables"""
    print("Checking Environment Variables")
    print("─" * 60)
    
    # Load .env if available
    try:
        from dotenv import load_dotenv
        env_path = project_root / '.env'
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass
    
    results = {}
    for server in SERVERS:
        if not server.env_vars:
            continue
            
        server_status = {}
        print(f"\n  {server.name}:")
        for var in server.env_vars:
            is_set = bool(os.getenv(var))
            status = "✓" if is_set else "✗"
            print(f"    {status} {var}")
            server_status[var] = is_set
        
        results[server.name] = server_status
    
    print()
    return results

def print_config_template() -> None:
    """Print Claude Desktop configuration template"""
    print("Claude Desktop Configuration")
    print("─" * 60)
    print(f"""
Add this to your claude_desktop_config.json:

Location:
  • macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
  • Windows: %APPDATA%\\Claude\\claude_desktop_config.json
  • Linux:   ~/.config/Claude/claude_desktop_config.json

Configuration:
{{
  "mcpServers": {{
    "goal-agent": {{
      "command": "python",
      "args": ["/absolute/path/to/servers/goal_agent_server.py"]
    }},
    "jira": {{
      "command": "python",
      "args": ["/absolute/path/to/servers/jira_server.py"],
      "env": {{
        "JIRA_BASE_URL": "https://your-domain.atlassian.net",
        "JIRA_EMAIL": "your@email.com",
        "JIRA_API_TOKEN": "your_token",
        "JIRA_PROJECT_KEY": "PROJ"
      }}
    }},
    "github": {{
      "command": "python",
      "args": ["/absolute/path/to/servers/github_server.py"],
      "env": {{
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token"
      }}
    }}
  }}
}}

Replace /absolute/path/to with your actual project path:
  Current path: {project_root}
""")

def print_next_steps() -> None:
    """Print next steps"""
    print("Next Steps")
    print("─" * 60)
    print("""
  1. Test server imports
     → Run: python scripts/test_servers.py

  2. Configure Claude Desktop
     → See: docs/SERVER_SETUP.md for detailed instructions
     → See: docs/QUICKSTART.md for quick setup

  3. Restart Claude Desktop
     → Completely quit and restart the application

  4. Test in Claude
     → Try: "Create a goal to test the system"
     → Try: "List my Jira projects"

Documentation:
  → Setup Guide:  docs/SERVER_SETUP.md
  → Quick Start:  docs/QUICKSTART.md
  → Goal Agent:   docs/README_GOAL_AGENT.md
""")

def print_summary(files_found: int, total_files: int, env_results: dict) -> bool:
    """Print summary and return success status"""
    print("Summary")
    print("─" * 60)
    
    # Check files
    all_files_found = files_found == total_files
    files_status = "✓" if all_files_found else "✗"
    print(f"  {files_status} Server Files: {files_found}/{total_files} found")
    
    # Check environment
    env_configured = True
    total_vars = 0
    set_vars = 0
    
    for server_name, vars_status in env_results.items():
        for var, is_set in vars_status.items():
            total_vars += 1
            if is_set:
                set_vars += 1
            else:
                env_configured = False
    
    if total_vars > 0:
        env_status = "✓" if env_configured else "⚠"
        print(f"  {env_status} Environment: {set_vars}/{total_vars} variables set")
    else:
        print(f"  ─ Environment: No variables required")
    
    print()
    
    if not all_files_found:
        print("  ✗ Some server files are missing")
        return False
    
    if not env_configured and total_vars > 0:
        print("  ⚠ Some environment variables are missing")
        print("    Servers will work but some features may be unavailable")
        print()
    
    if all_files_found and env_configured:
        print("  ✓ Configuration looks good!")
        print()
    
    return all_files_found

def main() -> None:
    """Main entry point"""
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print_next_steps()
        sys.exit(0)
    
    print()
    print("=" * 60)
    print("MCP Server Configuration Checker")
    print("=" * 60)
    print()
    
    # Check server files
    files_found, total_files = check_server_files()
    
    # Check environment
    env_results = check_environment()
    
    # Print summary
    success = print_summary(files_found, total_files, env_results)
    
    if not success:
        print("  Please fix the issues above before proceeding.")
        print()
        sys.exit(1)
    
    # Print next steps
    print_next_steps()
    
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()