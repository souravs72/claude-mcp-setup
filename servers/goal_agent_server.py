#!/usr/bin/env python3
"""
Goal-Based AI Agent MCP Server
Manages goals, tasks, and execution plans with PostgreSQL persistence and Redis caching
Goals and plans are stored in PostgreSQL for durability, with Redis for temporary caching
"""

import atexit
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.base_client import handle_errors
from servers.config import (
    ConfigurationError,
    GoalAgentConfig,
    PostgresConfig,
    load_env_file,
    validate_config,
)
from servers.database import DatabaseManager
from servers.logging_config import (
    log_server_shutdown,
    log_server_startup,
    setup_logging,
)

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "goal_agent_server.log"
logger = setup_logging("GoalAgentServer", log_file=log_file)

load_env_file()
mcp = FastMCP("Goal-Based AI Agent Server")


@dataclass
class Goal:
    """Represents a high-level goal."""

    id: str
    description: str
    priority: str
    status: str
    repos: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Task:
    """Represents a specific task within a goal."""

    id: str
    goal_id: str
    description: str
    type: str
    status: str
    priority: str
    dependencies: list[str] = field(default_factory=list)
    repo: str | None = None
    jira_ticket: str | None = None
    estimated_effort: str | None = None
    assigned_tools: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    result: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


def with_lock(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to ensure thread-safe operations."""

    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        with self.lock:
            return func(self, *args, **kwargs)

    return wrapper


class CacheLayer:
    """
    Redis-based cache layer for temporary caching (NOT persistence).
    Used only for frequently accessed data to reduce database load.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.cache_prefix = "goal_agent_cache"
        self.enabled = enabled
        self.redis_client: Any = None

        if enabled:
            try:
                import redis

                from servers.config import RedisConfig

                # Initialize Redis with configuration
                redis_config = RedisConfig()
                self.redis_client = redis.Redis(
                    host=redis_config.host,
                    port=redis_config.port,
                    db=redis_config.db,
                    password=redis_config.password,
                    decode_responses=redis_config.decode_responses,
                    socket_timeout=redis_config.socket_timeout,
                    socket_connect_timeout=redis_config.socket_connect_timeout,
                )

                # Test connection
                self.redis_client.ping()
                logger.info(
                    f"Redis cache connected (caching only) - {redis_config.host}:{redis_config.port}"
                )

            except ImportError:
                logger.warning("Redis not installed - caching disabled")
                self.enabled = False
                self.redis_client = None
            except Exception as e:
                logger.warning(f"Redis connection failed - caching disabled: {e}")
                self.enabled = False
                self.redis_client = None
        else:
            logger.info("Cache layer disabled by configuration")

    def get_cache_key(self, key_type: str, identifier: str) -> str:
        """Generate cache key."""
        return f"{self.cache_prefix}:{key_type}:{identifier}"

    def cache_set(self, key: str, value: dict[str, Any], ttl: int = 3600) -> bool:
        """
        Set a value in Redis cache (temporary).

        Args:
            key: Cache key
            value: Dictionary to cache
            ttl: Time to live in seconds (default: 1 hour for temporary caching)
        """
        if not self.enabled or not self.redis_client:
            logger.debug("Cache disabled, skipping set")
            return False

        try:
            serialized = json.dumps(value)
            if ttl > 0:
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)
            logger.debug(f"Cached: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False

    def cache_get(self, key: str) -> dict[str, Any] | None:
        """
        Get a value from Redis cache.

        Args:
            key: Cache key

        Returns:
            Cached dictionary or None
        """
        if not self.enabled or not self.redis_client:
            logger.debug("Cache disabled, skipping get")
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Cache get error for {key}: {e}")
            return None

    def cache_delete(self, keys: list[str]) -> bool:
        """
        Delete keys from Redis cache.

        Args:
            keys: List of keys to delete
        """
        if not self.enabled or not self.redis_client:
            logger.debug("Cache disabled, skipping delete")
            return False

        try:
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    def is_available(self) -> bool:
        """Check if cache is available."""
        if not self.enabled or not self.redis_client:
            return False

        try:
            return bool(self.redis_client.ping())
        except Exception:
            return False


class GoalAgent:
    """Manages goals and tasks with PostgreSQL persistence and Redis caching."""

    def __init__(self, config: GoalAgentConfig, db_manager: DatabaseManager) -> None:
        self.config = config
        self.db = db_manager
        self.goal_counter = 0
        self.task_counter = 0
        self.max_workers = config.max_workers
        self._executor: ThreadPoolExecutor | None = None
        self.lock = threading.RLock()
        self.cache = CacheLayer(config.cache_enabled)

        # Initialize executor
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="GoalAgent"
        )

        # Register cleanup
        atexit.register(self.shutdown)

        logger.info(
            f"Goal agent initialized - Workers: {self.max_workers}, "
            f"Cache: {config.cache_enabled}, Persistence: PostgreSQL"
        )

        # Initialize counters from database
        self._initialize_counters()

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Get executor instance."""
        if self._executor is None:
            raise RuntimeError("Executor not initialized")
        return self._executor

    def _initialize_counters(self) -> None:
        """Initialize goal and task counters from database."""
        try:
            # Extract highest counter values from existing IDs
            goals = self.db.list_goals()
            tasks = self.db.list_tasks()

            if goals:
                goal_numbers = [int(g.id.split("-")[1]) for g in goals if "-" in g.id]
                self.goal_counter = max(goal_numbers) if goal_numbers else 0

            if tasks:
                task_numbers = [int(t.id.split("-")[1]) for t in tasks if "-" in t.id]
                self.task_counter = max(task_numbers) if task_numbers else 0

            logger.info(
                f"Initialized counters from database: goal={self.goal_counter}, task={self.task_counter}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize counters: {e}")
            self.goal_counter = 0
            self.task_counter = 0

    def _cache_goal(self, goal_dict: dict[str, Any]) -> None:
        """Cache a goal temporarily (1 hour)."""
        if not self.cache.is_available():
            return

        try:
            cache_key = self.cache.get_cache_key("goal", goal_dict["id"])
            self.cache.cache_set(cache_key, goal_dict, ttl=3600)  # 1 hour
        except Exception as e:
            logger.debug(f"Failed to cache goal {goal_dict.get('id', 'unknown')}: {e}")

    def _cache_task(self, task_dict: dict[str, Any]) -> None:
        """Cache a task temporarily (1 hour)."""
        if not self.cache.is_available():
            return

        try:
            cache_key = self.cache.get_cache_key("task", task_dict["id"])
            self.cache.cache_set(cache_key, task_dict, ttl=3600)  # 1 hour
        except Exception as e:
            logger.debug(f"Failed to cache task {task_dict.get('id', 'unknown')}: {e}")

    @with_lock
    def create_goal(
        self,
        description: str,
        priority: str = "medium",
        repos: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new goal and persist to database."""
        if not description or not description.strip():
            raise ValueError("Goal description cannot be empty")

        if priority not in ["high", "medium", "low"]:
            raise ValueError("Priority must be 'high', 'medium', or 'low'")

        self.goal_counter += 1
        goal_id = f"GOAL-{self.goal_counter:04d}"

        # Create in database
        goal = self.db.create_goal(
            goal_id=goal_id,
            description=description.strip(),
            priority=priority,
            repos=repos or [],
            metadata=metadata or {},
        )

        logger.info(f"Created goal: {goal_id} - {description[:50]}")

        # Cache temporarily (goal is already a dict from db)
        self._cache_goal(goal)

        return goal

    @with_lock
    def break_down_goal(
        self, goal_id: str, subtasks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Break down a goal into executable subtasks and persist to database."""
        goal = self.db.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        if not subtasks:
            raise ValueError("At least one subtask must be provided")

        for subtask_def in subtasks:
            if not subtask_def.get("description"):
                raise ValueError("Each subtask must have a description")

            self.task_counter += 1
            task_id = f"TASK-{self.task_counter:04d}"

            priority = subtask_def.get("priority", "medium")
            if priority not in ["high", "medium", "low"]:
                priority = "medium"

            # Create task in database
            task = self.db.create_task(
                task_id=task_id,
                goal_id=goal_id,
                description=subtask_def.get("description", "").strip(),
                task_type=subtask_def.get("type", "general"),
                priority=priority,
                dependencies=subtask_def.get("dependencies", []),
                repo=subtask_def.get("repo"),
                jira_ticket=subtask_def.get("jira_ticket"),
                estimated_effort=subtask_def.get("estimated_effort"),
                assigned_tools=subtask_def.get("tools", []),
            )

            # Validate dependencies
            for dep_id in task.get("dependencies", []):
                if not self.db.get_task(dep_id):
                    logger.warning(f"Dependency {dep_id} not found for task {task_id}")

            # Cache task (already a dict from db)
            self._cache_task(task)

            logger.debug(f"Created task: {task_id} for goal {goal_id}")

        # Update goal status
        updated_goal = self.db.update_goal(goal_id, status="in_progress")
        if updated_goal:
            goal_dict = updated_goal.to_dict()
            self._cache_goal(goal_dict)

        logger.info(f"Goal {goal_id} broken down into {len(subtasks)} tasks")

        # Refresh goal to get updated data
        goal = self.db.get_goal(goal_id)
        return goal.to_dict() if goal else {}

    def get_goal(self, goal_id: str) -> dict[str, Any]:
        """Get goal with all task details (cache-first strategy)."""
        with self.lock:
            # Try cache first
            if self.cache.is_available():
                cache_key = self.cache.get_cache_key("goal", goal_id)
                cached = self.cache.cache_get(cache_key)
                if cached:
                    cached["_cache_status"] = {
                        "enabled": True,
                        "persistence": "PostgreSQL",
                        "served_from": "Redis Cache",
                        "cache_hit": True,
                    }
                    logger.debug(f"Cache HIT for goal {goal_id}")
                    return cached

            # Cache miss - query database
            logger.debug(f"Cache MISS for goal {goal_id}, querying PostgreSQL")
            goal = self.db.get_goal(goal_id)
            if not goal:
                raise ValueError(f"Goal {goal_id} not found")

            result = goal.to_dict()

            # Get all tasks for this goal
            tasks = self.db.list_tasks(goal_id=goal_id)
            result["task_details"] = [task.to_dict() for task in tasks]

            # Cache for next time
            self._cache_goal(result)

            # Add cache info
            result["_cache_status"] = {
                "enabled": self.cache.is_available(),
                "persistence": "PostgreSQL",
                "served_from": "PostgreSQL",
                "cache_hit": False,
            }

            return result

    def list_goals(
        self, status: str | None = None, priority: str | None = None
    ) -> list[dict[str, Any]]:
        """List all goals with optional filters from database."""
        with self.lock:
            if status and status not in [
                "planned",
                "in_progress",
                "completed",
                "cancelled",
            ]:
                logger.warning(f"Invalid status filter: {status}")
                status = None

            if priority and priority not in ["high", "medium", "low"]:
                logger.warning(f"Invalid priority filter: {priority}")
                priority = None

            goals = self.db.list_goals(status=status, priority=priority)
            result = [goal.to_dict() for goal in goals]

            logger.debug(f"Listed {len(result)} goals from database")
            return result

    @with_lock
    def update_task_status(
        self, task_id: str, status: str, result: Any | None = None
    ) -> dict[str, Any]:
        """Update task status and result in database."""
        task = self.db.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if status not in ["pending", "in_progress", "completed", "failed", "blocked"]:
            raise ValueError(f"Invalid status: {status}")

        old_status = task.status

        # Update in database
        completed_at = datetime.utcnow() if status == "completed" else None
        updated_task = self.db.update_task(
            task_id=task_id,
            status=status,
            result=result,
            completed_at=completed_at,
        )

        if not updated_task:
            raise ValueError(f"Failed to update task {task_id}")

        logger.info(f"Task {task_id} status: {old_status} -> {status}")

        # Convert to dict and cache
        task_dict = updated_task.to_dict()
        self._cache_task(task_dict)

        # Check if all tasks in goal are completed
        goal_id = updated_task.goal_id
        all_tasks = self.db.list_tasks(goal_id=goal_id)

        if all_tasks and all(t.status == "completed" for t in all_tasks):
            updated_goal = self.db.update_goal(goal_id, status="completed")
            if updated_goal:
                logger.info(f"Goal {goal_id} completed")
                goal_dict = updated_goal.to_dict()
                self._cache_goal(goal_dict)

        return task_dict

    def get_next_tasks(self, goal_id: str | None = None) -> list[dict[str, Any]]:
        """Get next executable tasks from database."""
        with self.lock:
            if goal_id:
                goal = self.db.get_goal(goal_id)
                if not goal:
                    raise ValueError(f"Goal {goal_id} not found")
                tasks_to_check = self.db.list_tasks(goal_id=goal_id)
            else:
                tasks_to_check = self.db.list_tasks()

            executable_tasks = []

            for task in tasks_to_check:
                if task.status != "pending":
                    continue

                # Check if all dependencies are completed
                dependencies_met = all(
                    (dep_task := self.db.get_task(dep_id))
                    and dep_task.status == "completed"
                    for dep_id in task.dependencies
                )

                if dependencies_met:
                    executable_tasks.append(task.to_dict())

            # Sort by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            executable_tasks.sort(key=lambda t: priority_order.get(t["priority"], 1))

            logger.debug(f"Found {len(executable_tasks)} executable tasks")
            return executable_tasks

    def get_task(self, task_id: str) -> dict[str, Any]:
        """Get task details (cache-first strategy)."""
        with self.lock:
            # Try cache first
            if self.cache.is_available():
                cache_key = self.cache.get_cache_key("task", task_id)
                cached = self.cache.cache_get(cache_key)
                if cached:
                    cached["_cache_status"] = {
                        "enabled": True,
                        "persistence": "PostgreSQL",
                        "served_from": "Redis Cache",
                        "cache_hit": True,
                    }
                    logger.debug(f"Cache HIT for task {task_id}")
                    return cached

            # Cache miss - query database
            logger.debug(f"Cache MISS for task {task_id}, querying PostgreSQL")
            task = self.db.get_task(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            result = task.to_dict()

            # Cache for next time
            self._cache_task(result)

            result["_cache_status"] = {
                "enabled": self.cache.is_available(),
                "persistence": "PostgreSQL",
                "served_from": "PostgreSQL",
                "cache_hit": False,
            }
            return result

    def generate_execution_plan(self, goal_id: str) -> dict[str, Any]:
        """Generate phased execution plan from database."""
        with self.lock:
            goal = self.db.get_goal(goal_id)
            if not goal:
                raise ValueError(f"Goal {goal_id} not found")

            tasks = self.db.list_tasks(goal_id=goal_id)

            if not tasks:
                return {
                    "goal_id": goal_id,
                    "goal_description": goal.description,
                    "total_tasks": 0,
                    "total_phases": 0,
                    "execution_phases": [],
                    "message": "No tasks defined for this goal",
                }

            phases: list[dict[str, Any]] = []
            remaining_tasks = tasks.copy()
            completed_task_ids: set[str] = set()

            max_iterations = len(tasks) + 1
            iteration = 0

            while remaining_tasks and iteration < max_iterations:
                iteration += 1
                phase_tasks = []

                for task in remaining_tasks[:]:
                    dependencies_met = all(
                        dep_id in completed_task_ids
                        or dep_id not in [t.id for t in tasks]
                        for dep_id in task.dependencies
                    )

                    if dependencies_met:
                        phase_tasks.append(task.to_dict())
                        completed_task_ids.add(task.id)
                        remaining_tasks.remove(task)

                if not phase_tasks:
                    phases.append(
                        {
                            "phase": len(phases) + 1,
                            "tasks": [t.to_dict() for t in remaining_tasks],
                            "warning": "Circular dependencies detected",
                        }
                    )
                    logger.warning(f"Circular dependencies in goal {goal_id}")
                    break

                phases.append(
                    {
                        "phase": len(phases) + 1,
                        "tasks": phase_tasks,
                        "task_count": len(phase_tasks),
                        "parallel_execution_possible": len(phase_tasks) > 1,
                    }
                )

            plan = {
                "goal_id": goal_id,
                "goal_description": goal.description,
                "total_tasks": len(tasks),
                "total_phases": len(phases),
                "execution_phases": phases,
            }

            logger.info(f"Generated execution plan for {goal_id}")
            return plan

    def batch_update_tasks(self, updates: list[dict[str, Any]]) -> dict[str, Any]:
        """Update multiple tasks concurrently."""
        logger.info(f"Batch updating {len(updates)} tasks")

        futures: dict[Any, str] = {}
        results: dict[str, Any] = {
            "successful": [],
            "failed": [],
            "total": len(updates),
        }

        for update in updates:
            task_id = update.get("task_id")
            status = update.get("status")
            result = update.get("result")

            if not task_id or not status:
                results["failed"].append(
                    {"task_id": task_id, "error": "Missing task_id or status"}
                )
                continue

            future = self.executor.submit(
                self.update_task_status, task_id, status, result
            )
            futures[future] = task_id

        for future in as_completed(futures):
            task_id = futures[future]
            try:
                updated_task = future.result()
                results["successful"].append(
                    {"task_id": task_id, "status": updated_task["status"]}
                )
            except Exception as e:
                results["failed"].append({"task_id": task_id, "error": str(e)})
                logger.error(f"Failed to update {task_id}: {e}")

        logger.info(
            f"Batch update complete: {len(results['successful'])} successful, {len(results['failed'])} failed"
        )
        return results

    def batch_get_tasks(self, task_ids: list[str]) -> dict[str, Any]:
        """Retrieve multiple tasks concurrently from database."""
        logger.info(f"Batch retrieving {len(task_ids)} tasks")

        futures: dict[Any, str] = {}
        results: dict[str, Any] = {"tasks": [], "not_found": [], "total": len(task_ids)}

        for task_id in task_ids:
            future = self.executor.submit(self.get_task, task_id)
            futures[future] = task_id

        for future in as_completed(futures):
            task_id = futures[future]
            try:
                results["tasks"].append(future.result())
            except ValueError:
                results["not_found"].append(task_id)
            except Exception as e:
                logger.error(f"Failed to retrieve {task_id}: {e}")

        return results

    @with_lock
    def delete_task(self, task_id: str) -> dict[str, Any]:
        """Delete a task from database."""
        task = self.db.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        goal_id = task.goal_id

        # Check if other tasks depend on this one
        all_tasks = self.db.list_tasks()
        dependent_tasks = [t.id for t in all_tasks if task_id in t.dependencies]

        if dependent_tasks:
            logger.warning(f"Task {task_id} has dependent tasks: {dependent_tasks}")

        # Delete from database (this will also update the goal's tasks relationship)
        self.db.delete_task(task_id)

        # Delete from cache
        cache_key = self.cache.get_cache_key("task", task_id)
        self.cache.cache_delete([cache_key])

        logger.info(f"Deleted task: {task_id}")
        return {
            "deleted_task_id": task_id,
            "goal_id": goal_id,
            "dependent_tasks": dependent_tasks,
            "success": True,
        }

    @with_lock
    def delete_goal(self, goal_id: str) -> dict[str, Any]:
        """Delete a goal and all tasks from database."""
        goal = self.db.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        # Get task IDs before deletion
        tasks = self.db.list_tasks(goal_id=goal_id)
        task_ids = [t.id for t in tasks]

        # Delete from database (cascading will delete tasks automatically)
        self.db.delete_goal(goal_id)

        # Delete from cache
        goal_cache_key = self.cache.get_cache_key("goal", goal_id)
        self.cache.cache_delete([goal_cache_key])

        for task_id in task_ids:
            task_cache_key = self.cache.get_cache_key("task", task_id)
            self.cache.cache_delete([task_cache_key])

        logger.info(f"Deleted goal {goal_id} and {len(task_ids)} tasks from database")

        return {
            "deleted_goal_id": goal_id,
            "deleted_tasks": len(task_ids),
            "task_ids": task_ids,
            "success": True,
        }

    @with_lock
    def update_goal(
        self,
        goal_id: str,
        description: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        repos: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update an existing goal in database."""
        goal = self.db.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")

        if description:
            if not description.strip():
                raise ValueError("Description cannot be empty")

        if priority:
            if priority not in ["high", "medium", "low"]:
                raise ValueError("Priority must be 'high', 'medium', or 'low'")

        if status:
            if status not in ["planned", "in_progress", "completed", "cancelled"]:
                raise ValueError(f"Invalid status: {status}")

        # Update in database
        updated_goal = self.db.update_goal(
            goal_id=goal_id,
            description=description,
            priority=priority,
            status=status,
            repos=repos,
            metadata=metadata,
        )

        if not updated_goal:
            raise ValueError(f"Failed to update goal {goal_id}")

        # Convert to dict and cache
        goal_dict = updated_goal.to_dict()
        self._cache_goal(goal_dict)

        logger.info(f"Updated goal: {goal_id}")
        return goal_dict

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics from database."""
        with self.lock:
            return {
                "goals": self.db.get_goal_count(),
                "tasks": self.db.get_task_count(),
                "goal_counter": self.goal_counter,
                "task_counter": self.task_counter,
                "cache_enabled": self.cache.is_available(),
                "persistence": "PostgreSQL",
                "timestamp": datetime.now().isoformat(),
            }

    def shutdown(self) -> None:
        """Shutdown the executor and database connection gracefully."""
        logger.info("Shutting down Goal Agent...")

        if self._executor:
            try:
                logger.info("Shutting down ThreadPoolExecutor...")
                self._executor.shutdown(wait=True, cancel_futures=False)
                logger.info("ThreadPoolExecutor shutdown complete")
            except Exception as e:
                logger.error(f"Error during executor shutdown: {e}")

        # Close database connection
        try:
            self.db.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

        logger.info("Goal Agent shutdown complete")


# Initialize database and agent
try:
    config = GoalAgentConfig()
    validate_config(config, logger)

    # Initialize PostgreSQL database
    postgres_config = PostgresConfig()
    validate_config(postgres_config, logger)

    database_url = postgres_config.get_connection_string()
    db_manager = DatabaseManager(
        database_url=database_url,
        pool_size=postgres_config.pool_size,
        max_overflow=postgres_config.max_overflow,
    )

    # Create tables if they don't exist
    db_manager.create_tables()
    logger.info("Database tables initialized")

    log_server_startup(
        logger,
        "Goal Agent Server",
        {
            "Version": "3.0 (PostgreSQL Persistence)",
            "Thread Pool Workers": config.max_workers,
            "Cache Enabled": config.cache_enabled,
            "Timeout": config.timeout,
            "Database": f"{postgres_config.host}:{postgres_config.port}/{postgres_config.database}",
            "Persistence": "PostgreSQL",
        },
    )

    agent = GoalAgent(config, db_manager)

except ConfigurationError as e:
    logger.critical(f"Configuration error: {e}")
    sys.exit(1)
except Exception as e:
    logger.critical(f"Failed to initialize Goal Agent: {e}", exc_info=True)
    sys.exit(1)


# MCP Tools
@mcp.tool()
@handle_errors(logger)
def create_goal(
    description: str,
    priority: str = "medium",
    repos: str | None = None,
    metadata: str | None = None,
) -> str:
    """
    Create a new goal for the AI agent to work on.
    Goal is persisted to PostgreSQL database for durability.

    Args:
        description: Clear description of the goal (required, non-empty)
        priority: Priority level (high, medium, low) - default: medium
        repos: JSON array of repository names
        metadata: Additional metadata as JSON object

    Returns:
        JSON string with created goal
    """
    repos_list = json.loads(repos) if repos else []
    metadata_dict = json.loads(metadata) if metadata else {}

    result = agent.create_goal(description, priority, repos_list, metadata_dict)

    result["_persistence"] = {
        "database": "PostgreSQL",
        "cache_enabled": agent.cache.is_available(),
        "message": "Goal saved to PostgreSQL database",
    }

    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def break_down_goal(goal_id: str, subtasks: str) -> str:
    """Break down a goal into executable subtasks with validation."""
    subtasks_list = json.loads(subtasks)
    result = agent.break_down_goal(goal_id, subtasks_list)

    result["_persistence"] = {
        "database": "PostgreSQL",
        "cache_enabled": agent.cache.is_available(),
        "message": "Tasks saved to PostgreSQL database",
    }

    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def get_goal(goal_id: str) -> str:
    """Get detailed information about a specific goal."""
    goal = agent.get_goal(goal_id)
    return json.dumps(goal, indent=2)


@mcp.tool()
@handle_errors(logger)
def list_goals(status: str | None = None, priority: str | None = None) -> str:
    """List all goals with optional filters."""
    goals = agent.list_goals(status, priority)
    result = {
        "goals": goals,
        "count": len(goals),
        "persistence": "PostgreSQL",
        "cache_enabled": agent.cache.is_available(),
    }
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def get_next_tasks(goal_id: str | None = None) -> str:
    """Get next executable tasks (tasks with no pending dependencies)."""
    tasks = agent.get_next_tasks(goal_id)
    return json.dumps(tasks, indent=2)


@mcp.tool()
@handle_errors(logger)
def update_task_status(task_id: str, status: str, result: str | None = None) -> str:
    """Update the status of a task with validation."""
    result_dict = json.loads(result) if result else None
    task_result = agent.update_task_status(task_id, status, result_dict)

    task_result["_persistence"] = {
        "database": "PostgreSQL",
        "cache_enabled": agent.cache.is_available(),
        "message": "Task status saved to PostgreSQL database",
    }

    return json.dumps(task_result, indent=2)


@mcp.tool()
@handle_errors(logger)
def delete_task(task_id: str) -> str:
    """Delete a single task from a goal."""
    result = agent.delete_task(task_id)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def get_task(task_id: str) -> str:
    """Get detailed information about a specific task."""
    task = agent.get_task(task_id)
    return json.dumps(task, indent=2)


@mcp.tool()
@handle_errors(logger)
def generate_execution_plan(goal_id: str) -> str:
    """Generate a phased execution plan for a goal."""
    plan = agent.generate_execution_plan(goal_id)
    return json.dumps(plan, indent=2)


@mcp.tool()
@handle_errors(logger)
def delete_goal(goal_id: str) -> str:
    """Delete a goal and all its associated tasks."""
    result = agent.delete_goal(goal_id)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def update_goal(
    goal_id: str,
    description: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    repos: str | None = None,
    metadata: str | None = None,
) -> str:
    """Update an existing goal with validation."""
    repos_list = json.loads(repos) if repos else None
    metadata_dict = json.loads(metadata) if metadata else None

    result = agent.update_goal(
        goal_id, description, priority, status, repos_list, metadata_dict
    )

    result["_persistence"] = {
        "database": "PostgreSQL",
        "cache_enabled": agent.cache.is_available(),
        "message": "Goal updated in PostgreSQL database",
    }

    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def batch_update_tasks(updates: str) -> str:
    """Update multiple tasks concurrently."""
    updates_list = json.loads(updates)
    result = agent.batch_update_tasks(updates_list)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def batch_get_tasks(task_ids: str) -> str:
    """Retrieve multiple tasks concurrently."""
    ids_list = json.loads(task_ids)
    result = agent.batch_get_tasks(ids_list)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def get_agent_status() -> str:
    """Get current goal agent status and statistics."""
    stats = agent.get_stats()

    result = {
        "persistence": {
            "database": "PostgreSQL",
            "cache": "Redis (temporary, 5-minute TTL)",
            "description": "Data stored in PostgreSQL for durability, Redis for performance",
        },
        "current_state": {
            "goals": stats["goals"],
            "tasks": stats["tasks"],
            "goal_counter": stats["goal_counter"],
            "task_counter": stats["task_counter"],
        },
        "agent_config": {
            "max_workers": agent.config.max_workers,
            "timeout": agent.config.timeout,
            "cache_enabled": agent.config.cache_enabled,
        },
        "architecture": {
            "persistence": "PostgreSQL - Real persistent storage",
            "caching": "Redis - Temporary caching for performance (5 min TTL)",
            "note": "All data is permanently stored in PostgreSQL, Redis is optional",
        },
    }

    return json.dumps(result, indent=2)


def main() -> None:
    """Main entry point."""
    try:
        logger.info("Starting Goal Agent MCP Server...")
        mcp.run()

    except KeyboardInterrupt:
        log_server_shutdown(logger, "Goal Agent Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
