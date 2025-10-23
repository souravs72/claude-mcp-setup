#!/usr/bin/env python3
"""
MCP Dashboard Server - Real-time Operations Console
Provides a web interface for monitoring MCP servers, Redis cache, goals, and logs.
"""

import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import psutil
import redis
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.config import PostgresConfig, RedisConfig, load_env_file
from servers.database import DatabaseManager


# Pydantic models for request validation
class CreateGoalRequest(BaseModel):
    description: str
    priority: str = "medium"
    repos: list[str] = []
    metadata: dict = {}


class AddTasksRequest(BaseModel):
    subtasks: list[dict]


class UpdateTaskStatusRequest(BaseModel):
    status: str
    result: dict | None = None


# Initialize paths
PROJECT_ROOT = Path(__file__).parent.parent
SERVERS_DIR = PROJECT_ROOT / "servers"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
STATIC_DIR = SERVERS_DIR / "static"

# Load environment
load_env_file()

# Initialize database manager for goal/task access
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> Optional[DatabaseManager]:
    """Get or create database manager for accessing goals/tasks."""
    global _db_manager
    if _db_manager is None:
        try:
            postgres_config = PostgresConfig()
            database_url = postgres_config.get_connection_string()
            _db_manager = DatabaseManager(
                database_url=database_url,
                pool_size=5,  # Smaller pool for dashboard
                max_overflow=10,
            )
        except Exception as e:
            print(f"Warning: Could not initialize database manager: {e}")
            return None
    return _db_manager


# Background task reference
broadcast_task = None

# Server definitions (from mcpctl.py)
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
}


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global broadcast_task

    # Startup
    print("Starting background tasks...")
    broadcast_task = asyncio.create_task(broadcast_updates())

    yield

    # Shutdown
    print("Stopping background tasks...")
    if broadcast_task:
        broadcast_task.cancel()
        try:
            await broadcast_task
        except asyncio.CancelledError:
            pass


# Initialize FastAPI
app = FastAPI(
    title="MCP Operations Dashboard",
    description="Real-time monitoring for MCP servers, Redis cache, and goal tracking",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client cache
_redis_client: Optional[redis.Redis] = None


# WebSocket Connection Manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"✓ New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        print(f"✗ WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        try:
            config = RedisConfig()
            _redis_client = redis.Redis(
                host=config.host,
                port=config.port,
                db=config.db,
                password=config.password,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            _redis_client.ping()
        except Exception:
            return None
    return _redis_client


def find_server_processes() -> List[Dict[str, Any]]:
    """Find all running MCP server processes."""
    server_processes = []
    server_names = [s.replace("-", "_") + "_server" for s in SERVERS.keys()]

    for proc in psutil.process_iter(
        ["pid", "name", "cmdline", "create_time", "memory_info", "cpu_percent"]
    ):
        try:
            if proc.info["cmdline"] and len(proc.info["cmdline"]) >= 2:
                if "python" in proc.info["cmdline"][0].lower():
                    for arg in proc.info["cmdline"]:
                        if "_server.py" in arg:
                            server_name = Path(arg).stem
                            if server_name in server_names:
                                server_key = server_name.replace("_server", "").replace(
                                    "_", "-"
                                )

                                # Get memory info
                                memory_mb = (
                                    proc.info["memory_info"].rss / (1024 * 1024)
                                    if proc.info.get("memory_info")
                                    else 0
                                )

                                server_processes.append(
                                    {
                                        "key": server_key,
                                        "name": SERVERS[server_key]["name"],
                                        "pid": proc.info["pid"],
                                        "uptime": time.time()
                                        - proc.info["create_time"],
                                        "memory_mb": round(memory_mb, 2),
                                        "cpu_percent": proc.info.get("cpu_percent", 0),
                                    }
                                )
                            break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return server_processes


def get_log_tail(log_file: Path, lines: int = 50) -> List[Dict[str, Any]]:
    """Get last N lines from a log file with error detection."""
    if not log_file.exists():
        return []

    try:
        with open(log_file, "r") as f:
            log_lines = f.readlines()[-lines:]

        parsed_logs = []
        for line in log_lines:
            line = line.strip()
            if not line:
                continue

            # Detect log level
            level = "info"
            if "ERROR" in line.upper() or "CRITICAL" in line.upper():
                level = "error"
            elif "WARNING" in line.upper() or "WARN" in line.upper():
                level = "warning"
            elif "DEBUG" in line.upper():
                level = "debug"

            parsed_logs.append(
                {
                    "text": line,
                    "level": level,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return parsed_logs
    except Exception:
        return []


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main dashboard HTML."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse(
        "<h1>Dashboard not found. Run setup first.</h1>", status_code=404
    )


@app.get("/api/status")
async def get_status():
    """Get overall system status."""
    running_servers = find_server_processes()
    redis_client = get_redis_client()
    redis_connected = redis_client is not None

    # Check Redis stats
    redis_stats = {}
    if redis_connected and redis_client:
        try:
            info = redis_client.info()
            redis_stats = {
                "connected": True,
                "version": info.get("redis_version", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0),
                "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
                "total_keys": redis_client.dbsize(),
                "connected_clients": info.get("connected_clients", 0),
                "ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            }
        except Exception:
            redis_stats = {"connected": False, "error": "Failed to get Redis info"}
    else:
        redis_stats = {"connected": False}

    return {
        "timestamp": datetime.now().isoformat(),
        "servers": {
            "total": len(SERVERS),
            "running": len(running_servers),
            "stopped": len(SERVERS) - len(running_servers),
        },
        "redis": redis_stats,
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        },
    }


@app.get("/api/servers")
async def get_servers():
    """Get detailed server status."""
    running_processes = find_server_processes()
    running_keys = {p["key"]: p for p in running_processes}

    servers_status = []
    for key, server in SERVERS.items():
        status = "stopped"
        details = {}

        if key in running_keys:
            status = "running"
            proc = running_keys[key]
            details = {
                "pid": proc["pid"],
                "uptime": proc["uptime"],
                "memory_mb": proc["memory_mb"],
                "cpu_percent": proc["cpu_percent"],
            }

        # Check environment variables
        env_configured = (
            all(os.getenv(var) for var in server["env_vars"])
            if server["env_vars"]
            else True
        )

        servers_status.append(
            {
                "key": key,
                "name": server["name"],
                "status": status,
                "env_configured": env_configured,
                "required_env_vars": server["env_vars"],
                "log_file": str(server["log"]),
                "details": details,
            }
        )

    return {"servers": servers_status}


@app.get("/api/redis/stats")
async def get_redis_stats():
    """Get detailed Redis statistics."""
    redis_client = get_redis_client()

    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    try:
        info = redis_client.info()

        # Get keyspace info
        keyspace = {}
        for key, value in info.items():
            if key.startswith("db"):
                keyspace[key] = value

        return {
            "server": {
                "version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "uptime_days": info.get("uptime_in_days"),
            },
            "memory": {
                "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
                "used_memory_peak_mb": round(
                    info.get("used_memory_peak", 0) / (1024 * 1024), 2
                ),
                "memory_fragmentation_ratio": info.get("mem_fragmentation_ratio", 0),
            },
            "clients": {
                "connected_clients": info.get("connected_clients", 0),
                "blocked_clients": info.get("blocked_clients", 0),
            },
            "stats": {
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            },
            "keyspace": keyspace,
            "total_keys": redis_client.dbsize(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get Redis stats: {str(e)}"
        )


@app.get("/api/goals")
async def get_goals():
    """Get active goals and tasks from PostgreSQL database."""
    try:
        db = get_db_manager()
        if not db:
            return {
                "summary": {
                    "total_goals": 0,
                    "total_tasks": 0,
                    "goals_by_status": {
                        "pending": 0,
                        "in_progress": 0,
                        "completed": 0,
                        "cancelled": 0,
                    },
                    "tasks_by_status": {
                        "pending": 0,
                        "in_progress": 0,
                        "completed": 0,
                        "cancelled": 0,
                    },
                },
                "recent_goals": [],
                "active_tasks": [],
                "error": "Database not available",
            }

        # Get all goals and tasks from database
        goals = db.list_goals()
        tasks = db.list_tasks()

        # Convert to dicts
        goals_data = {g.id: g.to_dict() for g in goals}
        tasks_data = {t.id: t.to_dict() for t in tasks}

        # Aggregate stats
        total_goals = len(goals_data)
        total_tasks = len(tasks_data)

        goals_by_status = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0,
        }
        tasks_by_status = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0,
        }

        for goal in goals_data.values():
            status = goal.get("status", "pending")
            goals_by_status[status] = goals_by_status.get(status, 0) + 1

        for task in tasks_data.values():
            status = task.get("status", "pending")
            tasks_by_status[status] = tasks_by_status.get(status, 0) + 1

        # Get recent goals
        recent_goals = sorted(
            goals_data.values(), key=lambda x: x.get("updated_at", ""), reverse=True
        )[:5]

        # Get active tasks
        active_tasks = [
            task
            for task in tasks_data.values()
            if task.get("status") in ["in_progress", "pending"]
        ][:10]

        return {
            "summary": {
                "total_goals": total_goals,
                "total_tasks": total_tasks,
                "goals_by_status": goals_by_status,
                "tasks_by_status": tasks_by_status,
            },
            "recent_goals": recent_goals,
            "active_tasks": active_tasks,
            "source": "PostgreSQL",
        }
    except Exception as e:
        return {
            "summary": {
                "total_goals": 0,
                "total_tasks": 0,
                "goals_by_status": {
                    "pending": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "cancelled": 0,
                },
                "tasks_by_status": {
                    "pending": 0,
                    "in_progress": 0,
                    "completed": 0,
                    "cancelled": 0,
                },
            },
            "recent_goals": [],
            "active_tasks": [],
            "error": str(e),
        }


@app.get("/api/logs")
async def get_logs(server: Optional[str] = None, lines: int = 50):
    """Get recent logs from servers."""
    if lines > 500:
        lines = 500  # Limit to prevent huge responses

    if server and server in SERVERS:
        log_file = SERVERS[server]["log"]
        logs = get_log_tail(log_file, lines)
        return {
            "server": server,
            "logs": logs,
        }

    # Get logs from all servers
    all_logs = {}
    error_count = 0
    warning_count = 0

    for key, srv in SERVERS.items():
        logs = get_log_tail(srv["log"], lines)
        all_logs[key] = logs

        # Count errors and warnings
        for log in logs:
            if log["level"] == "error":
                error_count += 1
            elif log["level"] == "warning":
                warning_count += 1

    return {
        "all_servers": all_logs,
        "summary": {
            "total_errors": error_count,
            "total_warnings": warning_count,
        },
    }


@app.get("/api/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/servers/control-all")
async def control_all_servers(request: dict):
    """Control all MCP servers (start/stop/restart)."""
    import os
    import subprocess

    action = request.get("action", "").lower()
    if action not in ["start", "stop", "restart"]:
        raise HTTPException(
            status_code=400, detail="Invalid action. Use 'start', 'stop', or 'restart'"
        )

    try:
        results = {}

        if action == "stop":
            # Stop all MCP server processes
            for server_name, server_info in SERVERS.items():
                script_name = server_info["script"].name
                try:
                    # Find processes
                    result = subprocess.run(
                        ["pgrep", "-f", script_name], capture_output=True, text=True
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split("\n")
                        for pid in pids:
                            subprocess.run(["kill", "-9", pid], check=False)
                        results[server_name] = f"✓ Stopped {len(pids)} process(es)"
                    else:
                        results[server_name] = "Already stopped"
                except Exception as e:
                    results[server_name] = f"Error: {str(e)}"

        elif action == "start":
            # Start servers via Claude Desktop's stdio mechanism
            # We'll use the start script that checks Claude Desktop config
            python_path = PROJECT_ROOT / "mcp-env" / "bin" / "python"

            for server_name, server_info in SERVERS.items():
                script_path = server_info["script"]
                log_file = server_info["log"]

                try:
                    # Check if already running
                    check = subprocess.run(
                        ["pgrep", "-f", script_path.name],
                        capture_output=True,
                        text=True,
                    )

                    if check.returncode == 0 and check.stdout.strip():
                        results[server_name] = "⚠️ Already running"
                        continue

                    # Start the server in background with nohup
                    cmd = f"cd {PROJECT_ROOT} && nohup {python_path} {script_path} > {log_file} 2>&1 &"

                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                        env=os.environ.copy(),
                    )

                    # Give it a moment to start
                    import time

                    time.sleep(0.5)

                    # Check if it started successfully
                    verify = subprocess.run(
                        ["pgrep", "-f", script_path.name],
                        capture_output=True,
                        text=True,
                    )

                    if verify.returncode == 0 and verify.stdout.strip():
                        pid = verify.stdout.strip().split("\n")[0]
                        results[server_name] = f"✓ Started (PID: {pid})"
                    else:
                        results[server_name] = "❌ Failed to start - check logs"

                except Exception as e:
                    results[server_name] = f"❌ Error: {str(e)}"

        elif action == "restart":
            # Stop then start
            for server_name, server_info in SERVERS.items():
                script_name = server_info["script"].name
                script_path = server_info["script"]
                log_file = server_info["log"]
                python_path = PROJECT_ROOT / "mcp-env" / "bin" / "python"

                try:
                    # Stop first
                    result = subprocess.run(
                        ["pgrep", "-f", script_name], capture_output=True, text=True
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split("\n")
                        for pid in pids:
                            subprocess.run(["kill", "-9", pid], check=False)

                    # Wait a moment
                    import time

                    time.sleep(0.5)

                    # Start
                    cmd = f"cd {PROJECT_ROOT} && nohup {python_path} {script_path} > {log_file} 2>&1 &"

                    subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                        env=os.environ.copy(),
                    )

                    time.sleep(0.5)

                    # Verify
                    verify = subprocess.run(
                        ["pgrep", "-f", script_name], capture_output=True, text=True
                    )

                    if verify.returncode == 0 and verify.stdout.strip():
                        pid = verify.stdout.strip().split("\n")[0]
                        results[server_name] = f"✓ Restarted (PID: {pid})"
                    else:
                        results[server_name] = "❌ Failed to restart - check logs"

                except Exception as e:
                    results[server_name] = f"❌ Error: {str(e)}"

        # Add explanatory note based on action
        if action == "start":
            note = "⚠️ MCP servers use stdio communication and cannot run independently. They will start but exit immediately without Claude Desktop. To use MCP servers with Claude, they must be started by Claude Desktop via the config file."
        elif action == "restart":
            note = "⚠️ MCP servers use stdio communication. Servers restarted from dashboard will exit immediately. For full functionality, restart Claude Desktop instead."
        else:
            note = "Servers stopped successfully."

        return {
            "status": "success" if action == "stop" else "warning",
            "action": action,
            "results": results,
            "note": note,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/redis/keys")
async def get_redis_keys(pattern: str = "*", limit: int = 100):
    """Get Redis keys matching pattern with metadata."""
    try:
        client = get_redis_client()
        if not client:
            return {"error": "Redis not connected", "keys": [], "count": 0}

        keys = client.scan_iter(match=pattern, count=limit)
        keys_list = []

        for i, key in enumerate(keys):
            if i >= limit:
                break

            # Decode key if bytes
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key

            # Get key type and TTL
            try:
                key_type = (
                    client.type(key).decode("utf-8")
                    if isinstance(client.type(key), bytes)
                    else client.type(key)
                )
                ttl = client.ttl(key)
            except Exception:
                key_type = "unknown"
                ttl = -1

            keys_list.append({"key": key_str, "type": key_type, "ttl": ttl})

        return {
            "keys": keys_list,
            "count": len(keys_list),
            "pattern": pattern,
            "limited": len(keys_list) >= limit,
        }
    except Exception as e:
        return {"error": str(e), "keys": [], "count": 0}


@app.get("/api/redis/key/{key_name:path}")
async def get_redis_key(key_name: str):
    """Get a specific Redis key's value and metadata."""
    try:
        client = get_redis_client()
        if not client:
            raise HTTPException(status_code=503, detail="Redis not connected")

        # Check if key exists
        if not client.exists(key_name):
            raise HTTPException(status_code=404, detail=f"Key '{key_name}' not found")

        # Get key type
        key_type = client.type(key_name)
        if isinstance(key_type, bytes):
            key_type = key_type.decode("utf-8")

        # Get TTL
        ttl = client.ttl(key_name)

        # Get value based on type
        value = None
        if key_type == "string":
            value = client.get(key_name)
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            # Try to parse as JSON
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        elif key_type == "list":
            value = client.lrange(key_name, 0, -1)
            value = [v.decode("utf-8") if isinstance(v, bytes) else v for v in value]
        elif key_type == "set":
            value = list(client.smembers(key_name))
            value = [v.decode("utf-8") if isinstance(v, bytes) else v for v in value]
        elif key_type == "hash":
            value = client.hgetall(key_name)
            value = {
                k.decode("utf-8") if isinstance(k, bytes) else k: (
                    v.decode("utf-8") if isinstance(v, bytes) else v
                )
                for k, v in value.items()
            }
        elif key_type == "zset":
            value = client.zrange(key_name, 0, -1, withscores=True)
            value = [
                {"member": m.decode("utf-8") if isinstance(m, bytes) else m, "score": s}
                for m, s in value
            ]
        else:
            value = f"Unsupported type: {key_type}"

        return {
            "key": key_name,
            "type": key_type,
            "ttl": ttl,
            "value": value,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/env")
async def get_environment():
    """Get environment configuration status."""
    env_status = {}

    for server_name, server_info in SERVERS.items():
        env_vars = server_info.get("env_vars", [])
        server_env = {}

        for var in env_vars:
            value = os.getenv(var)
            is_set = value is not None and value != ""

            # Mask the value for security (show first 4 chars + ***)
            masked_value = None
            if is_set and value:
                if len(value) > 6:
                    masked_value = value[:4] + "***"
                else:
                    masked_value = "***"

            server_env[var] = {
                "configured": is_set,
                "masked_value": masked_value if is_set else "Not set",
            }

        # Convert to the expected format with env_vars at top level
        env_status[server_name] = {
            "name": server_info["name"],
            "env_vars": server_env,
            "all_set": all(os.getenv(var) for var in env_vars) if env_vars else True,
        }

    return {
        "servers": env_status,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/tasks/list")
async def list_tasks():
    """Get list of all tasks from PostgreSQL database."""
    try:
        db = get_db_manager()
        if not db:
            return {"error": "Database not available", "tasks": [], "count": 0}

        # Get all tasks from database
        tasks = db.list_tasks()
        tasks_list = [task.to_dict() for task in tasks]

        return {
            "tasks": tasks_list,
            "count": len(tasks_list),
            "source": "PostgreSQL",
        }
    except Exception as e:
        return {"error": str(e), "tasks": [], "count": 0}


@app.get("/api/goals/list")
async def list_goals():
    """Get list of all goals with full details from PostgreSQL database."""
    try:
        db = get_db_manager()
        if not db:
            return {"error": "Database not available", "goals": [], "count": 0}

        # Get all goals from database
        goals = db.list_goals()
        goals_list = [goal.to_dict() for goal in goals]

        return {
            "goals": goals_list,
            "count": len(goals_list),
            "source": "PostgreSQL",
        }
    except Exception as e:
        return {"error": str(e), "goals": [], "count": 0}


@app.get("/api/goals/{goal_id}")
async def get_goal_details(goal_id: str):
    """Get detailed information about a specific goal including all its tasks from PostgreSQL."""
    try:
        db = get_db_manager()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get goal from database
        goal = db.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")

        # Get all tasks for this goal
        tasks = db.list_tasks(goal_id=goal_id)
        goal_tasks = [task.to_dict() for task in tasks]

        # Sort tasks by created_at
        goal_tasks.sort(key=lambda x: x.get("created_at", ""), reverse=False)

        return {
            "goal": goal.to_dict(),
            "tasks": goal_tasks,
            "task_count": len(goal_tasks),
            "tasks_by_status": {
                "pending": sum(1 for t in goal_tasks if t.get("status") == "pending"),
                "in_progress": sum(
                    1 for t in goal_tasks if t.get("status") == "in_progress"
                ),
                "completed": sum(
                    1 for t in goal_tasks if t.get("status") == "completed"
                ),
                "cancelled": sum(
                    1 for t in goal_tasks if t.get("status") == "cancelled"
                ),
            },
            "source": "PostgreSQL",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: str):
    """Delete a goal and all its tasks from PostgreSQL."""
    try:
        db = get_db_manager()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get goal info before deletion
        goal = db.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")

        # Get tasks count before deletion
        tasks = db.list_tasks(goal_id=goal_id)
        task_count = len(tasks)

        # Delete goal (cascades to tasks)
        success = db.delete_goal(goal_id)

        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete goal {goal_id}"
            )

        return {
            "success": True,
            "deleted_goal_id": goal_id,
            "deleted_tasks_count": task_count,
            "message": f"Goal {goal_id} and {task_count} task(s) deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task from PostgreSQL."""
    try:
        db = get_db_manager()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        # Get task info before deletion
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        goal_id = task.goal_id

        # Delete task
        success = db.delete_task(task_id)

        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete task {task_id}"
            )

        return {
            "success": True,
            "deleted_task_id": task_id,
            "goal_id": goal_id,
            "message": f"Task {task_id} deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/goals")
async def create_goal(goal_data: CreateGoalRequest):
    """Create a new goal in PostgreSQL."""
    try:
        db = get_db_manager()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        # Validate priority
        if goal_data.priority not in ["high", "medium", "low"]:
            raise HTTPException(
                status_code=400, detail="Invalid priority. Must be high, medium, or low"
            )

        # Initialize goal agent to use its create_goal logic
        from servers.goal_agent_server import agent

        new_goal = agent.create_goal(
            description=goal_data.description,
            priority=goal_data.priority,
            repos=goal_data.repos,
            metadata=goal_data.metadata,
        )

        return {
            "success": True,
            "goal": new_goal,
            "message": f"Goal {new_goal['id']} created successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/goals/{goal_id}/tasks")
async def add_tasks_to_goal(goal_id: str, tasks_data: AddTasksRequest):
    """Add tasks to a goal in PostgreSQL."""
    try:
        db = get_db_manager()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        # Verify goal exists
        goal = db.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")

        # Validate subtasks
        if not tasks_data.subtasks:
            raise HTTPException(status_code=400, detail="At least one task is required")

        # Use goal agent to break down goal
        from servers.goal_agent_server import agent

        result = agent.break_down_goal(goal_id, tasks_data.subtasks)

        return {
            "success": True,
            "goal_id": goal_id,
            "tasks_added": len(tasks_data.subtasks),
            "goal_status": result["status"],
            "message": f"Added {len(tasks_data.subtasks)} task(s) to {goal_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/tasks/{task_id}/status")
async def update_task_status(task_id: str, status_data: UpdateTaskStatusRequest):
    """Update task status in PostgreSQL."""
    try:
        db = get_db_manager()
        if not db:
            raise HTTPException(status_code=503, detail="Database not available")

        # Validate status
        if status_data.status not in [
            "pending",
            "in_progress",
            "completed",
            "failed",
            "blocked",
        ]:
            raise HTTPException(status_code=400, detail="Invalid status")

        # Get task to verify it exists
        task = db.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Update task
        from servers.goal_agent_server import agent

        updated_task = agent.update_task_status(
            task_id, status_data.status, status_data.result
        )

        return {
            "success": True,
            "task": updated_task,
            "message": f"Task {task_id} updated to {status_data.status}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)

    try:
        # Send initial data
        initial_data = await collect_dashboard_data()
        await websocket.send_json(
            {
                "type": "initial",
                "data": initial_data,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for messages from client (e.g., manual refresh request)
                message = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

                if message.get("type") == "refresh":
                    # Client requested a refresh
                    data = await collect_dashboard_data()
                    await websocket.send_json(
                        {
                            "type": "update",
                            "data": data,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
            except WebSocketDisconnect:
                break

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


async def collect_dashboard_data(include_system_stats: bool = True) -> dict:
    """Collect all dashboard data for broadcasting.

    Args:
        include_system_stats: If True, includes CPU/memory/disk stats (expensive).
                             Should be False for fast updates (100ms), True for slow updates (1000ms).
    """
    try:
        # Collect status
        running_servers = find_server_processes()
        redis_client = get_redis_client()
        redis_connected = redis_client is not None

        # Check Redis stats
        redis_stats = {}
        if redis_connected and redis_client:
            try:
                # Always get key count (fast operation)
                total_keys = redis_client.dbsize()
                redis_stats = {
                    "connected": True,
                    "total_keys": total_keys,
                }

                # Only get expensive stats (INFO command) on slow cycles
                if include_system_stats:
                    info = redis_client.info()
                    redis_stats.update(
                        {
                            "version": info.get("redis_version", "unknown"),
                            "uptime_days": info.get("uptime_in_days", 0),
                            "used_memory_mb": round(
                                info.get("used_memory", 0) / (1024 * 1024), 2
                            ),
                            "connected_clients": info.get("connected_clients", 0),
                            "ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                        }
                    )
            except Exception:
                redis_stats = {"connected": False, "error": "Failed to get Redis info"}
        else:
            redis_stats = {"connected": False}

        # Build status data (no timestamp here - added during broadcast)
        status_data = {
            "servers": {
                "total": len(SERVERS),
                "running": len(running_servers),
                "stopped": len(SERVERS) - len(running_servers),
            },
            "redis": redis_stats,
        }

        # Only include expensive system stats every 1000ms
        if include_system_stats:
            status_data["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            }

        # Collect server details
        running_processes = find_server_processes()
        running_keys = {p["key"]: p for p in running_processes}

        servers_status = []
        for key, server in SERVERS.items():
            status = "stopped"
            details = {}

            if key in running_keys:
                status = "running"
                proc = running_keys[key]
                details = {
                    "pid": proc["pid"],
                    "uptime": proc["uptime"],
                    "memory_mb": proc["memory_mb"],
                    "cpu_percent": proc["cpu_percent"],
                }

            # Check environment variables
            env_configured = (
                all(os.getenv(var) for var in server["env_vars"])
                if server["env_vars"]
                else True
            )

            servers_status.append(
                {
                    "key": key,
                    "name": server["name"],
                    "status": status,
                    "env_configured": env_configured,
                    "required_env_vars": server["env_vars"],
                    "log_file": str(server["log"]),
                    "details": details,
                }
            )

        # Collect goals summary from PostgreSQL
        goals_data = {}
        tasks_data = {}

        try:
            db = get_db_manager()
            if db:
                # Get from database
                goals = db.list_goals()
                tasks = db.list_tasks()
                goals_data = {g.id: g.to_dict() for g in goals}
                tasks_data = {t.id: t.to_dict() for t in tasks}
        except Exception:
            pass  # Silent fail - will show empty goals/tasks

        total_goals = len(goals_data)
        total_tasks = len(tasks_data)

        goals_by_status = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0,
        }
        tasks_by_status = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0,
        }

        for goal in goals_data.values():
            status = goal.get("status", "pending")
            goals_by_status[status] = goals_by_status.get(status, 0) + 1

        for task in tasks_data.values():
            status = task.get("status", "pending")
            tasks_by_status[status] = tasks_by_status.get(status, 0) + 1

        goals_summary = {
            "summary": {
                "total_goals": total_goals,
                "total_tasks": total_tasks,
                "goals_by_status": goals_by_status,
                "tasks_by_status": tasks_by_status,
            }
        }

        # Collect recent logs
        all_logs = {}
        error_count = 0
        warning_count = 0

        for key, srv in SERVERS.items():
            logs = get_log_tail(srv["log"], 30)  # Reduced from 50 for efficiency
            all_logs[key] = logs

            for log in logs:
                if log["level"] == "error":
                    error_count += 1
                elif log["level"] == "warning":
                    warning_count += 1

        logs_data = {
            "all_servers": all_logs,
            "summary": {
                "total_errors": error_count,
                "total_warnings": warning_count,
            },
        }

        return {
            "status": status_data,
            "servers": {"servers": servers_status},
            "goals": goals_summary,
            "logs": logs_data,
        }
    except Exception as e:
        print(f"Error collecting dashboard data: {e}")
        return {}


# Background task for broadcasting updates
async def broadcast_updates():
    """Background task that broadcasts updates to all connected clients."""
    previous_data = {}
    cycle_count = 0

    while True:
        try:
            await asyncio.sleep(0.1)  # Check every 100ms for near-instant updates

            if not manager.active_connections:
                cycle_count = 0  # Reset counter when no clients
                previous_data = {}
                continue  # No clients connected, skip

            cycle_count += 1
            update_system_stats = cycle_count % 10 == 0  # Every 1000ms (10 cycles)

            # Collect current data (with optional system stats)
            current_data = await collect_dashboard_data(
                include_system_stats=update_system_stats
            )

            # Smart comparison: only broadcast if meaningful changes occurred
            has_changes = False

            # Check if data structure is different or has meaningful changes
            if not previous_data:
                has_changes = True
            else:
                # Check servers count
                if current_data.get("status", {}).get("servers") != previous_data.get(
                    "status", {}
                ).get("servers"):
                    has_changes = True

                # Check Redis connection or key count
                curr_redis = current_data.get("status", {}).get("redis", {})
                prev_redis = previous_data.get("status", {}).get("redis", {})
                if curr_redis.get("connected") != prev_redis.get(
                    "connected"
                ) or curr_redis.get("total_keys") != prev_redis.get("total_keys"):
                    has_changes = True

                # Check system stats (only if included, with rounding to prevent minor fluctuations)
                if update_system_stats:
                    curr_sys = current_data.get("status", {}).get("system")
                    prev_sys = previous_data.get("status", {}).get("system")
                    if curr_sys and prev_sys:
                        # Round to 1 decimal to prevent 2.1% vs 2.2% triggering updates
                        if (
                            round(curr_sys.get("cpu_percent", 0), 1)
                            != round(prev_sys.get("cpu_percent", 0), 1)
                            or round(curr_sys.get("memory_percent", 0), 1)
                            != round(prev_sys.get("memory_percent", 0), 1)
                            or round(curr_sys.get("disk_percent", 0), 1)
                            != round(prev_sys.get("disk_percent", 0), 1)
                        ):
                            has_changes = True
                    elif curr_sys != prev_sys:
                        has_changes = True

                # Check server details (running status, PIDs, etc.)
                if current_data.get("servers") != previous_data.get("servers"):
                    has_changes = True

                # Check goals
                if current_data.get("goals") != previous_data.get("goals"):
                    has_changes = True

                # Check logs (new entries)
                if current_data.get("logs") != previous_data.get("logs"):
                    has_changes = True

            # Only broadcast if there are actual changes
            if has_changes:
                await manager.broadcast(
                    {
                        "type": "update",
                        "data": current_data,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                previous_data = current_data

        except Exception as e:
            print(f"Error in broadcast task: {e}")
            await asyncio.sleep(1)  # Brief pause on error before retrying


# Serve static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def main():
    """Run the dashboard server."""
    # Create static directory if it doesn't exist
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("MCP Operations Dashboard".center(60))
    print("=" * 60)
    print()
    print("📊 Dashboard URL: http://localhost:8000")
    print(f"📁 Project Root: {PROJECT_ROOT}")
    print(f"📁 Logs Directory: {LOGS_DIR}")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
