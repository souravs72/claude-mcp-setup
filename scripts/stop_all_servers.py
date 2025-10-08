#!/usr/bin/env python3
import time
import psutil
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent

def find_server_processes() -> list[dict]:
    """Find all running MCP server processes"""
    server_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['cmdline'] and len(proc.info['cmdline']) >= 2:
                # Check if this is a Python process running one of our servers
                if ('python' in proc.info['cmdline'][0].lower() and 
                    any('_server.py' in arg for arg in proc.info['cmdline'])):
                    
                    # Extract server name from command line
                    for arg in proc.info['cmdline']:
                        if '_server.py' in arg:
                            server_name = Path(arg).stem
                            server_processes.append({
                                'pid': proc.info['pid'],
                                'name': server_name,
                                'process': proc
                            })
                            break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return server_processes

def stop_servers() -> None:
    """Stop all MCP server processes"""
    print("Searching for running MCP server processes...")
    
    server_processes = find_server_processes()
    
    if not server_processes:
        print("No MCP server processes found running.")
        return
    
    print(f"Found {len(server_processes)} MCP server process(es):")
    for server in server_processes:
        print(f"  - {server['name']} (PID: {server['pid']})")
    
    print("\nStopping servers...")
    
    # Try graceful shutdown first
    for server in server_processes:
        try:
            print(f"Sending SIGTERM to {server['name']} (PID: {server['pid']})")
            server['process'].terminate()
        except psutil.NoSuchProcess:
            print(f"Process {server['name']} already terminated")
        except Exception as e:
            print(f"Error terminating {server['name']}: {str(e)}")
    
    # Wait for graceful shutdown
    print("Waiting for graceful shutdown...")
    time.sleep(3)
    
    # Check which processes are still running and force kill if necessary
    still_running = []
    for server in server_processes:
        try:
            if server['process'].is_running():
                still_running.append(server)
        except psutil.NoSuchProcess:
            pass
    
    if still_running:
        print(f"\n{len(still_running)} process(es) still running, forcing termination...")
        for server in still_running:
            try:
                print(f"Force killing {server['name']} (PID: {server['pid']})")
                server['process'].kill()
                server['process'].wait(timeout=5)
                print(f"Successfully killed {server['name']}")
            except psutil.NoSuchProcess:
                print(f"Process {server['name']} already terminated")
            except psutil.TimeoutExpired:
                print(f"Timeout waiting for {server['name']} to terminate")
            except Exception as e:
                print(f"Error force killing {server['name']}: {str(e)}")
    
    print("\nServer shutdown complete.")

def stop_servers_by_pid_file() -> bool:
    """Alternative method using PID files if they exist"""
    pid_dir = project_root / "pids"
    if not pid_dir.exists():
        return False
    
    pid_files = list(pid_dir.glob("*.pid"))
    if not pid_files:
        return False
    
    print(f"Found {len(pid_files)} PID file(s), attempting shutdown...")
    
    for pid_file in pid_files:
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            server_name = pid_file.stem
            
            try:
                proc = psutil.Process(pid)
                print(f"Stopping {server_name} (PID: {pid})")
                proc.terminate()
                proc.wait(timeout=5)
                print(f"Successfully stopped {server_name}")
            except psutil.NoSuchProcess:
                print(f"Process {server_name} (PID: {pid}) not found")
            except psutil.TimeoutExpired:
                print(f"Timeout stopping {server_name}, force killing...")
                proc.kill()
            
            # Remove PID file
            pid_file.unlink()
            
        except (ValueError, FileNotFoundError) as e:
            print(f"Error reading PID file {pid_file}: {str(e)}")
        except Exception as e:
            print(f"Error stopping process from {pid_file}: {str(e)}")
    
    return True

if __name__ == "__main__":
    print("MCP Server Shutdown Script")
    print("=" * 30)
    
    # Try PID file method first, then process search
    if not stop_servers_by_pid_file():
        stop_servers()