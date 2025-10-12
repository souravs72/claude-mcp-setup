#!/usr/bin/env python3
"""
Goal-Based AI Agent MCP Server
Manages goals, tasks, and execution plans with automatic Redis cache persistence
Goals and plans are automatically cached so LLM sessions remember them instantly
"""

import json
import sys
import atexit
from pathlib import Path
from typing import Any, Callable
from datetime import datetime
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
import threading

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.logging_config import (
    setup_logging,
    log_server_startup,
    log_server_shutdown,
)
from servers.config import (
    load_env_file,
    GoalAgentConfig,
    validate_config,
    ConfigurationError,
)
from servers.base_client import handle_errors

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
    Redis-based cache layer for goal agent persistence.
    Automatically persists goals and tasks to Redis for cross-session memory.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.cache_prefix = "goal_agent"
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
                    f"Redis cache connected - {redis_config.host}:{redis_config.port}"
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

    def cache_set(self, key: str, value: dict[str, Any], ttl: int = 604800) -> bool:
        """
        Set a value in Redis cache.

        Args:
            key: Cache key
            value: Dictionary to cache
            ttl: Time to live in seconds (default: 7 days)
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

    def cache_keys(self, pattern: str) -> list[str]:
        """
        Get all keys matching a pattern.

        Args:
            pattern: Key pattern with wildcards

        Returns:
            List of matching keys
        """
        if not self.enabled or not self.redis_client:
            return []

        try:
            keys = self.redis_client.keys(pattern)
            return [k.decode() if isinstance(k, bytes) else k for k in keys]
        except Exception as e:
            logger.error(f"Cache keys error: {e}")
            return []

    def is_available(self) -> bool:
        """Check if cache is available."""
        if not self.enabled or not self.redis_client:
            return False

        try:
            return bool(self.redis_client.ping())
        except Exception:
            return False


class GoalAgent:
    """Manages goals and tasks with automatic Redis cache persistence."""

    def __init__(self, config: GoalAgentConfig) -> None:
        self.config = config
        self.goals: dict[str, Goal] = {}
        self.tasks: dict[str, Task] = {}
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
            f"Cache: {config.cache_enabled}"
        )

        # Load state from cache on initialization
        self._load_from_cache()

    @property
    def executor(self) -> ThreadPoolExecutor:
        """Get executor instance."""
        if self._executor is None:
            raise RuntimeError("Executor not initialized")
        return self._executor

    def _load_from_files(self) -> bool:
        """Load goals and tasks from JSON files."""
        goals_file = project_root / "data" / "goals" / "goals.json"
        tasks_file = project_root / "data" / "goals" / "tasks.json"
        counters_file = project_root / "data" / "goals" / "counters.json"

        loaded_any = False

        try:
            # Load goals
            if goals_file.exists():
                with open(goals_file, "r") as f:
                    goals_data = json.load(f)
                    for goal_id, goal_dict in goals_data.items():
                        self.goals[goal_id] = Goal(**goal_dict)
                    logger.info(f"Loaded {len(goals_data)} goals from file")
                    loaded_any = True

            # Load tasks
            if tasks_file.exists():
                with open(tasks_file, "r") as f:
                    tasks_data = json.load(f)
                    for task_id, task_dict in tasks_data.items():
                        self.tasks[task_id] = Task(**task_dict)
                    logger.info(f"Loaded {len(tasks_data)} tasks from file")
                    loaded_any = True

            # Load counters
            if counters_file.exists():
                with open(counters_file, "r") as f:
                    counters = json.load(f)
                    self.goal_counter = counters.get("goal", 0)
                    self.task_counter = counters.get("task", 0)
                    logger.info(
                        f"Loaded counters: goal={self.goal_counter}, task={self.task_counter}"
                    )

            return loaded_any

        except Exception as e:
            logger.error(f"Failed to load from files: {e}")
            return False

    def _load_from_cache(self) -> None:
        """Load goals and tasks from cache on startup."""
        # First try to load from files
        loaded_from_files = self._load_from_files()

        if loaded_from_files:
            logger.info("Loaded state from files, syncing to cache...")
            # Save to cache so Redis is updated
            self._save_full_state()
            return

        # If no files, try cache
        if not self.cache.is_available():
            logger.info("Cache not available and no files found, starting fresh")
            return

        try:
            cache_key = self.cache.get_cache_key("state", "full")
            state = self.cache.cache_get(cache_key)

            if state:
                logger.info("Found cached state, restoring...")
                self.restore_from_cache(state)
            else:
                logger.info("No cached state or files found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load from cache: {e}")

    def _persist_to_cache(
        self, entity_type: str, entity_id: str, data: dict[str, Any]
    ) -> None:
        """
        Persist an entity to cache.

        Args:
            entity_type: 'goal' or 'task'
            entity_id: ID of the entity
            data: Data to cache
        """
        if not self.cache.is_available():
            return

        try:
            cache_key = self.cache.get_cache_key(entity_type, entity_id)
            self.cache.cache_set(cache_key, data, ttl=604800)  # 7 days

            # Also update full state
            self._save_full_state()
        except Exception as e:
            logger.error(f"Failed to persist {entity_type} {entity_id}: {e}")

    def _save_full_state(self) -> None:
        """Save complete state to cache."""
        if not self.cache.is_available():
            return

        try:
            state = self.get_cache_state()
            cache_key = self.cache.get_cache_key("state", "full")
            self.cache.cache_set(cache_key, state, ttl=2592000)  # 30 days
            logger.debug("Full state persisted to cache")
        except Exception as e:
            logger.error(f"Failed to save full state: {e}")

    @with_lock
    def create_goal(
        self,
        description: str,
        priority: str = "medium",
        repos: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Goal:
        """Create a new goal and cache it."""
        if not description or not description.strip():
            raise ValueError("Goal description cannot be empty")

        if priority not in ["high", "medium", "low"]:
            raise ValueError("Priority must be 'high', 'medium', or 'low'")

        self.goal_counter += 1
        goal_id = f"GOAL-{self.goal_counter:04d}"

        goal = Goal(
            id=goal_id,
            description=description.strip(),
            priority=priority,
            status="planned",
            repos=repos or [],
            metadata=metadata or {},
        )

        self.goals[goal_id] = goal
        logger.info(f"Created goal: {goal_id} - {description[:50]}")

        # Persist to cache
        self._persist_to_cache("goal", goal_id, goal.to_dict())

        return goal

    @with_lock
    def break_down_goal(self, goal_id: str, subtasks: list[dict[str, Any]]) -> Goal:
        """Break down a goal into executable subtasks and cache."""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")

        if not subtasks:
            raise ValueError("At least one subtask must be provided")

        goal = self.goals[goal_id]

        for subtask_def in subtasks:
            if not subtask_def.get("description"):
                raise ValueError("Each subtask must have a description")

            self.task_counter += 1
            task_id = f"TASK-{self.task_counter:04d}"

            priority = subtask_def.get("priority", "medium")
            if priority not in ["high", "medium", "low"]:
                priority = "medium"

            task = Task(
                id=task_id,
                goal_id=goal_id,
                description=subtask_def.get("description", "").strip(),
                type=subtask_def.get("type", "general"),
                status="pending",
                priority=priority,
                dependencies=subtask_def.get("dependencies", []),
                repo=subtask_def.get("repo"),
                jira_ticket=subtask_def.get("jira_ticket"),
                estimated_effort=subtask_def.get("estimated_effort"),
                assigned_tools=subtask_def.get("tools", []),
            )

            # Validate dependencies
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    logger.warning(f"Dependency {dep_id} not found for task {task_id}")

            self.tasks[task_id] = task
            goal.tasks.append(task_id)

            # Persist task to cache
            self._persist_to_cache("task", task_id, task.to_dict())

            logger.debug(f"Created task: {task_id} for goal {goal_id}")

        goal.updated_at = datetime.now().isoformat()
        goal.status = "in_progress"

        # Persist updated goal to cache
        self._persist_to_cache("goal", goal_id, goal.to_dict())

        logger.info(f"Goal {goal_id} broken down into {len(subtasks)} tasks")
        return goal

    def get_goal(self, goal_id: str) -> dict[str, Any]:
        """Get goal with all task details."""
        with self.lock:
            if goal_id not in self.goals:
                raise ValueError(f"Goal {goal_id} not found")

            goal = self.goals[goal_id]
            result = goal.to_dict()

            result["task_details"] = [
                self.tasks[task_id].to_dict()
                for task_id in goal.tasks
                if task_id in self.tasks
            ]

            # Add cache info
            result["_cache_status"] = {
                "enabled": self.cache.is_available(),
                "key": self.cache.get_cache_key("goal", goal_id),
            }

            return result

    def list_goals(
        self, status: str | None = None, priority: str | None = None
    ) -> list[dict[str, Any]]:
        """List all goals with optional filters."""
        with self.lock:
            goals = [goal.to_dict() for goal in self.goals.values()]

        if status:
            if status not in ["planned", "in_progress", "completed", "cancelled"]:
                logger.warning(f"Invalid status filter: {status}")
            else:
                goals = [g for g in goals if g["status"] == status]

        if priority:
            if priority not in ["high", "medium", "low"]:
                logger.warning(f"Invalid priority filter: {priority}")
            else:
                goals = [g for g in goals if g["priority"] == priority]

        logger.debug(f"Listed {len(goals)} goals")
        return goals

    @with_lock
    def update_task_status(
        self, task_id: str, status: str, result: Any | None = None
    ) -> Task:
        """Update task status and result."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        if status not in ["pending", "in_progress", "completed", "failed", "blocked"]:
            raise ValueError(f"Invalid status: {status}")

        task = self.tasks[task_id]
        old_status = task.status
        task.status = status

        if result:
            task.result = result

        if status == "completed":
            task.completed_at = datetime.now().isoformat()

        logger.info(f"Task {task_id} status: {old_status} -> {status}")

        # Persist updated task to cache
        self._persist_to_cache("task", task_id, task.to_dict())

        # Update goal and persist
        goal_id = task.goal_id
        if goal_id in self.goals:
            goal = self.goals[goal_id]
            all_tasks = [self.tasks[tid] for tid in goal.tasks if tid in self.tasks]

            if all_tasks and all(t.status == "completed" for t in all_tasks):
                goal.status = "completed"
                goal.updated_at = datetime.now().isoformat()
                logger.info(f"Goal {goal_id} completed")

            self._persist_to_cache("goal", goal_id, goal.to_dict())

        return task

    def get_next_tasks(self, goal_id: str | None = None) -> list[dict[str, Any]]:
        """Get next executable tasks."""
        with self.lock:
            tasks_to_check: list[Task] = []

            if goal_id:
                if goal_id not in self.goals:
                    raise ValueError(f"Goal {goal_id} not found")
                task_ids = self.goals[goal_id].tasks
                tasks_to_check = [
                    self.tasks[tid] for tid in task_ids if tid in self.tasks
                ]
            else:
                tasks_to_check = list(self.tasks.values())

            executable_tasks = []

            for task in tasks_to_check:
                if task.status != "pending":
                    continue

                dependencies_met = all(
                    self.tasks.get(
                        dep_id,
                        Task(
                            id="",
                            goal_id="",
                            description="",
                            type="",
                            status="",
                            priority="",
                        ),
                    ).status
                    == "completed"
                    for dep_id in task.dependencies
                )

                if dependencies_met:
                    executable_tasks.append(task.to_dict())

            priority_order = {"high": 0, "medium": 1, "low": 2}
            executable_tasks.sort(key=lambda t: priority_order.get(t["priority"], 1))

            logger.debug(f"Found {len(executable_tasks)} executable tasks")
            return executable_tasks

    def get_task(self, task_id: str) -> dict[str, Any]:
        """Get task details."""
        with self.lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")

            task = self.tasks[task_id].to_dict()
            task["_cache_status"] = {
                "enabled": self.cache.is_available(),
                "key": self.cache.get_cache_key("task", task_id),
            }
            return task

    def generate_execution_plan(self, goal_id: str) -> dict[str, Any]:
        """Generate phased execution plan."""
        with self.lock:
            if goal_id not in self.goals:
                raise ValueError(f"Goal {goal_id} not found")

            goal = self.goals[goal_id]
            tasks = [self.tasks[tid] for tid in goal.tasks if tid in self.tasks]

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
                    {"task_id": task_id, "status": updated_task.status}
                )
            except Exception as e:
                results["failed"].append({"task_id": task_id, "error": str(e)})
                logger.error(f"Failed to update {task_id}: {e}")

        logger.info(
            f"Batch update complete: {len(results['successful'])} successful, {len(results['failed'])} failed"
        )
        return results

    def batch_get_tasks(self, task_ids: list[str]) -> dict[str, Any]:
        """Retrieve multiple tasks concurrently."""
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
        """Delete a task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        goal_id = task.goal_id

        # Check if other tasks depend on this one
        dependent_tasks = [
            t.id for t in self.tasks.values() if task_id in t.dependencies
        ]

        if dependent_tasks:
            logger.warning(f"Task {task_id} has dependent tasks: {dependent_tasks}")

        del self.tasks[task_id]

        if goal_id in self.goals:
            goal = self.goals[goal_id]
            if task_id in goal.tasks:
                goal.tasks.remove(task_id)
                goal.updated_at = datetime.now().isoformat()
                self._persist_to_cache("goal", goal_id, goal.to_dict())

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
        """Delete a goal and all tasks."""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")

        goal = self.goals[goal_id]
        task_ids = goal.tasks.copy()

        # Delete all tasks
        for task_id in task_ids:
            if task_id in self.tasks:
                del self.tasks[task_id]
                # Delete task from cache
                task_cache_key = self.cache.get_cache_key("task", task_id)
                self.cache.cache_delete([task_cache_key])

        del self.goals[goal_id]

        # Delete goal from cache
        goal_cache_key = self.cache.get_cache_key("goal", goal_id)
        self.cache.cache_delete([goal_cache_key])

        # Update full state
        self._save_full_state()

        logger.info(f"Deleted goal {goal_id} and {len(task_ids)} tasks")

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
    ) -> Goal:
        """Update an existing goal."""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")

        goal = self.goals[goal_id]

        if description:
            if not description.strip():
                raise ValueError("Description cannot be empty")
            goal.description = description.strip()

        if priority:
            if priority not in ["high", "medium", "low"]:
                raise ValueError("Priority must be 'high', 'medium', or 'low'")
            goal.priority = priority

        if status:
            if status not in ["planned", "in_progress", "completed", "cancelled"]:
                raise ValueError(f"Invalid status: {status}")
            goal.status = status

        if repos is not None:
            goal.repos = repos

        if metadata:
            goal.metadata.update(metadata)

        goal.updated_at = datetime.now().isoformat()

        # Persist to cache
        self._persist_to_cache("goal", goal_id, goal.to_dict())

        logger.info(f"Updated goal: {goal_id}")
        return goal

    def get_cache_state(self) -> dict[str, Any]:
        """Get current state for caching."""
        with self.lock:
            return {
                "goals": {gid: goal.to_dict() for gid, goal in self.goals.items()},
                "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
                "goal_counter": self.goal_counter,
                "task_counter": self.task_counter,
                "timestamp": datetime.now().isoformat(),
            }

    def restore_from_cache(self, state: dict[str, Any]) -> bool:
        """Restore state from cache."""
        try:
            with self.lock:
                # Restore goals
                self.goals = {
                    gid: Goal(**goal_data)
                    for gid, goal_data in state.get("goals", {}).items()
                }

                # Restore tasks
                self.tasks = {
                    tid: Task(**task_data)
                    for tid, task_data in state.get("tasks", {}).items()
                }

                # Restore counters
                self.goal_counter = state.get("goal_counter", 0)
                self.task_counter = state.get("task_counter", 0)

                logger.info(
                    f"Restored {len(self.goals)} goals and {len(self.tasks)} tasks from cache"
                )
                return True

        except Exception as e:
            logger.error(f"Failed to restore from cache: {e}", exc_info=True)
            return False

    def shutdown(self) -> None:
        """Shutdown the executor gracefully."""
        logger.info("Shutting down Goal Agent...")

        if self._executor:
            try:
                logger.info("Shutting down ThreadPoolExecutor...")
                self._executor.shutdown(wait=True, cancel_futures=False)
                logger.info("ThreadPoolExecutor shutdown complete")
            except Exception as e:
                logger.error(f"Error during executor shutdown: {e}")

        logger.info("Goal Agent shutdown complete")


# Initialize agent
try:
    config = GoalAgentConfig()
    validate_config(config, logger)

    log_server_startup(
        logger,
        "Goal Agent Server",
        {
            "Version": "2.3 (Fixed Cache)",
            "Thread Pool Workers": config.max_workers,
            "Cache Enabled": config.cache_enabled,
            "Timeout": config.timeout,
        },
    )

    agent = GoalAgent(config)

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
    Goal will be automatically cached to Redis for persistence across Claude sessions.

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

    goal = agent.create_goal(description, priority, repos_list, metadata_dict)
    result = goal.to_dict()

    result["_cache_status"] = {
        "persisted": agent.cache.is_available(),
        "message": "Goal automatically saved to Redis"
        if agent.cache.is_available()
        else "Cache disabled",
    }

    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def break_down_goal(goal_id: str, subtasks: str) -> str:
    """Break down a goal into executable subtasks with validation."""
    subtasks_list = json.loads(subtasks)
    goal = agent.break_down_goal(goal_id, subtasks_list)
    result = goal.to_dict()

    result["_cache_status"] = {
        "persisted": agent.cache.is_available(),
        "message": "Tasks automatically saved to Redis"
        if agent.cache.is_available()
        else "Cache disabled",
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
    task = agent.update_task_status(task_id, status, result_dict)
    task_result = task.to_dict()

    task_result["_cache_status"] = {
        "persisted": agent.cache.is_available(),
        "message": "Task status saved to Redis"
        if agent.cache.is_available()
        else "Cache disabled",
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

    goal = agent.update_goal(
        goal_id, description, priority, status, repos_list, metadata_dict
    )
    result = goal.to_dict()

    result["_cache_status"] = {
        "persisted": agent.cache.is_available(),
        "message": "Goal updated in Redis"
        if agent.cache.is_available()
        else "Cache disabled",
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
def save_state_to_cache() -> str:
    """Manually save all goals and tasks to cache."""
    if not agent.cache.is_available():
        return json.dumps({"success": False, "error": "Cache not available"})

    agent._save_full_state()
    state = agent.get_cache_state()

    result = {
        "success": True,
        "state_snapshot": {
            "goals_count": len(state["goals"]),
            "tasks_count": len(state["tasks"]),
            "timestamp": state["timestamp"],
        },
        "message": "Full state saved to Redis cache",
    }

    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def restore_state_from_cache(state_json: str) -> str:
    """Restore all goals and tasks from cached state."""
    try:
        state = json.loads(state_json)
        success = agent.restore_from_cache(state)

        result = {
            "success": success,
            "restored": {"goals": len(agent.goals), "tasks": len(agent.tasks)},
            "message": "State restored successfully"
            if success
            else "Failed to restore state",
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
@handle_errors(logger)
def get_cache_status() -> str:
    """Get current cache integration status."""
    state = agent.get_cache_state()

    result = {
        "cache_integration": {
            "enabled": agent.cache.enabled,
            "available": agent.cache.is_available(),
            "backend": "Redis",
            "description": "Direct Redis integration for automatic persistence",
        },
        "current_state": {
            "goals": len(state["goals"]),
            "tasks": len(state["tasks"]),
            "goal_counter": state["goal_counter"],
            "task_counter": state["task_counter"],
        },
        "agent_config": {
            "max_workers": agent.config.max_workers,
            "timeout": agent.config.timeout,
            "cache_enabled": agent.config.cache_enabled,
        },
        "usage_guide": {
            "automatic": "All goals and tasks are automatically persisted to Redis",
            "manual_save": "Use save_state_to_cache() for explicit full state backup",
            "manual_restore": "Use restore_state_from_cache() with state JSON to restore",
            "persistence": "State persists across Claude sessions and restarts",
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
