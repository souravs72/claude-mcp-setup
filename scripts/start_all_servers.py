#!/usr/bin/env python3
import subprocess
import sys
import time
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent
servers_dir = project_root / "servers"
logs_dir = project_root / "logs"

# Ensure logs directory exists
logs_dir.mkdir(exist_ok=True)

servers = [
    {
        "name": "internet_server",
        "script": servers_dir / "internet_server.py",
        "log_file": logs_dir / "internet_server.log"
    },
    {
        "name": "github_server", 
        "script": servers_dir / "github_server.py",
        "log_file": logs_dir / "github_server.log"
    },
    {
        "name": "frappe_server",
        "script": servers_dir / "frappe_server.py", 
        "log_file": logs_dir / "frappe_server.log"
    },
    {
        "name": "jira_server",
        "script": servers_dir / "jira_server.py",
        "log_file": logs_dir / "jira_server.log"
    },
    {
        "name": "goal_agent_server",
        "script": servers_dir / "goal_agent_server.py",
        "log_file": logs_dir / "goal_agent_server.log"
    }
]

def start_servers():
    processes = []
    
    for server in servers:
        print(f"Starting {server['name']}...")
        
        with open(server['log_file'], 'w') as log_file:
            process = subprocess.Popen(
                [sys.executable, str(server['script'])],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=project_root
            )
        
        processes.append({
            'name': server['name'],
            'process': process,
            'log_file': server['log_file']
        })
        
        # Give each server a moment to start
        time.sleep(2)
    
    print("\nAll servers started. Check log files for status:")
    for proc in processes:
        print(f"  - {proc['name']}: {proc['log_file']}")
    
    return processes

if __name__ == "__main__":
    print("=" * 50)
    print("Starting MCP Server Infrastructure")
    print("=" * 50)
    start_servers()