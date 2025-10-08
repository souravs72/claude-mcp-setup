#!/usr/bin/env python3
"""
Goal-Based AI Agent MCP Server - Production Ready
Manages goals, tasks, and execution plans for AI-driven workflows
"""
import json
import sys
from pathlib import Path
from typing import Any, Optional, List, Dict
from datetime import datetime
from dataclasses import dataclass, field, asdict

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.logging_config import setup_logging, log_server_startup, log_server_shutdown
from servers.config import load_env_file
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
    repos: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
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
    dependencies: List[str] = field(default_factory=list)
    repo: Optional[str] = None
    jira_ticket: Optional[str] = None
    estimated_effort: Optional[str] = None
    assigned_tools: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class GoalAgent:
    """Manages goals and tasks for AI-driven workflows."""
    
    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.tasks: Dict[str, Task] = {}
        self.goal_counter = 0
        self.task_counter = 0
        
        logger.info("Goal agent initialized")
    
    def create_goal(
        self,
        description: str,
        priority: str = "medium",
        repos: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Goal:
        """
        Create a new goal.
        
        Args:
            description: Goal description
            priority: Priority level (high, medium, low)
            repos: List of repository names
            metadata: Additional metadata
            
        Returns:
            Created goal
        """
        self.goal_counter += 1
        goal_id = f"GOAL-{self.goal_counter:04d}"
        
        goal = Goal(
            id=goal_id,
            description=description,
            priority=priority,
            status="planned",
            repos=repos or [],
            metadata=metadata or {}
        )
        
        self.goals[goal_id] = goal
        logger.info(f"Created goal: {goal_id} - {description[:50]}")
        
        return goal
    
    def break_down_goal(self, goal_id: str, subtasks: List[Dict]) -> Goal:
        """
        Break down a goal into executable subtasks.
        
        Args:
            goal_id: Goal ID
            subtasks: List of subtask definitions
            
        Returns:
            Updated goal
            
        Raises:
            ValueError: If goal not found
        """
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")
        
        goal = self.goals[goal_id]
        
        for subtask_def in subtasks:
            self.task_counter += 1
            task_id = f"TASK-{self.task_counter:04d}"
            
            task = Task(
                id=task_id,
                goal_id=goal_id,
                description=subtask_def.get("description", ""),
                type=subtask_def.get("type", "general"),
                status="pending",
                priority=subtask_def.get("priority", "medium"),
                dependencies=subtask_def.get("dependencies", []),
                repo=subtask_def.get("repo"),
                jira_ticket=subtask_def.get("jira_ticket"),
                estimated_effort=subtask_def.get("estimated_effort"),
                assigned_tools=subtask_def.get("tools", [])
            )
            
            self.tasks[task_id] = task
            goal.tasks.append(task_id)
            
            logger.debug(f"Created task: {task_id} for goal {goal_id}")
        
        goal.updated_at = datetime.now().isoformat()
        goal.status = "in_progress"
        
        logger.info(f"Goal {goal_id} broken down into {len(subtasks)} tasks")
        return goal
    
    def get_goal(self, goal_id: str) -> Dict:
        """
        Get goal with all task details.
        
        Args:
            goal_id: Goal ID
            
        Returns:
            Goal with task details
            
        Raises:
            ValueError: If goal not found
        """
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")
        
        goal = self.goals[goal_id]
        result = goal.to_dict()
        
        result["task_details"] = [
            self.tasks[task_id].to_dict()
            for task_id in goal.tasks
            if task_id in self.tasks
        ]
        
        return result
    
    def list_goals(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Dict]:
        """
        List all goals with optional filters.
        
        Args:
            status: Filter by status
            priority: Filter by priority
            
        Returns:
            List of goals
        """
        goals = [goal.to_dict() for goal in self.goals.values()]
        
        if status:
            goals = [g for g in goals if g["status"] == status]
        
        if priority:
            goals = [g for g in goals if g["priority"] == priority]
        
        logger.debug(f"Listed {len(goals)} goals (filters: status={status}, priority={priority})")
        return goals
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Any] = None
    ) -> Task:
        """
        Update task status and result.
        
        Args:
            task_id: Task ID
            status: New status
            result: Task result
            
        Returns:
            Updated task
            
        Raises:
            ValueError: If task not found
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        old_status = task.status
        task.status = status
        
        if result:
            task.result = result
        
        if status == "completed":
            task.completed_at = datetime.now().isoformat()
        
        logger.info(f"Task {task_id} status: {old_status} -> {status}")
        
        # Update goal status if all tasks completed
        goal_id = task.goal_id
        if goal_id in self.goals:
            goal = self.goals[goal_id]
            all_tasks = [self.tasks[tid] for tid in goal.tasks if tid in self.tasks]
            
            if all_tasks and all(t.status == "completed" for t in all_tasks):
                goal.status = "completed"
                goal.updated_at = datetime.now().isoformat()
                logger.info(f"Goal {goal_id} completed")
        
        return task
    
    def get_next_tasks(self, goal_id: Optional[str] = None) -> List[Dict]:
        """
        Get next executable tasks (no pending dependencies).
        
        Args:
            goal_id: Optional goal ID to filter by
            
        Returns:
            List of executable tasks
        """
        tasks_to_check = []
        
        if goal_id:
            if goal_id not in self.goals:
                raise ValueError(f"Goal {goal_id} not found")
            task_ids = self.goals[goal_id].tasks
            tasks_to_check = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
        else:
            tasks_to_check = list(self.tasks.values())
        
        executable_tasks = []
        
        for task in tasks_to_check:
            if task.status != "pending":
                continue
            
            # Check if all dependencies are completed
            dependencies_met = all(
                self.tasks.get(dep_id, Task(id="", goal_id="", description="", type="", status="", priority="")).status == "completed"
                for dep_id in task.dependencies
            )
            
            if dependencies_met:
                executable_tasks.append(task.to_dict())
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        executable_tasks.sort(key=lambda t: priority_order.get(t["priority"], 1))
        
        logger.debug(f"Found {len(executable_tasks)} executable tasks")
        return executable_tasks
    
    def get_task(self, task_id: str) -> Dict:
        """
        Get task details.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task details
            
        Raises:
            ValueError: If task not found
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        return self.tasks[task_id].to_dict()
    
    def generate_execution_plan(self, goal_id: str) -> Dict:
        """
        Generate phased execution plan for a goal.
        
        Args:
            goal_id: Goal ID
            
        Returns:
            Execution plan with phases
            
        Raises:
            ValueError: If goal not found
        """
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")
        
        goal = self.goals[goal_id]
        tasks = [self.tasks[tid] for tid in goal.tasks if tid in self.tasks]
        
        # Build execution phases based on dependencies
        phases = []
        remaining_tasks = tasks.copy()
        completed_task_ids = set()
        
        while remaining_tasks:
            phase_tasks = []
            
            for task in remaining_tasks[:]:
                dependencies_met = all(
                    dep_id in completed_task_ids or dep_id not in [t.id for t in tasks]
                    for dep_id in task.dependencies
                )
                
                if dependencies_met:
                    phase_tasks.append(task.to_dict())
                    completed_task_ids.add(task.id)
                    remaining_tasks.remove(task)
            
            if not phase_tasks:
                # Circular dependency or orphaned tasks
                phases.append({
                    "phase": len(phases) + 1,
                    "tasks": [t.to_dict() for t in remaining_tasks],
                    "warning": "Possible circular dependencies detected"
                })
                logger.warning(f"Circular dependencies detected in goal {goal_id}")
                break
            
            phases.append({
                "phase": len(phases) + 1,
                "tasks": phase_tasks,
                "task_count": len(phase_tasks)
            })
        
        plan = {
            "goal_id": goal_id,
            "goal_description": goal.description,
            "total_tasks": len(tasks),
            "total_phases": len(phases),
            "execution_phases": phases
        }
        
        logger.info(f"Generated execution plan for {goal_id}: {len(phases)} phases")
        return plan


# Initialize agent
agent = GoalAgent()

log_server_startup(logger, "Goal Agent Server", {
    "Version": "2.0",
    "Features": "Goal management, task tracking, execution planning"
})


# MCP Tools
@mcp.tool()
@handle_errors(logger)
def create_goal(
    description: str,
    priority: str = "medium",
    repos: Optional[str] = None,
    metadata: Optional[str] = None
) -> str:
    """
    Create a new goal for the AI agent to work on.
    
    Args:
        description: Clear description of the goal
        priority: Priority level (high, medium, low)
        repos: JSON array of repository names
        metadata: Additional metadata as JSON object
        
    Returns:
        JSON string with created goal
    """
    repos_list = json.loads(repos) if repos else []
    metadata_dict = json.loads(metadata) if metadata else {}
    
    goal = agent.create_goal(description, priority, repos_list, metadata_dict)
    return json.dumps(goal.to_dict(), indent=2)


@mcp.tool()
@handle_errors(logger)
def break_down_goal(goal_id: str, subtasks: str) -> str:
    """
    Break down a goal into executable subtasks.
    
    Args:
        goal_id: Goal ID (e.g., GOAL-0001)
        subtasks: JSON array of subtask objects
        
    Returns:
        JSON string with updated goal
    """
    subtasks_list = json.loads(subtasks)
    goal = agent.break_down_goal(goal_id, subtasks_list)
    return json.dumps(goal.to_dict(), indent=2)


@mcp.tool()
@handle_errors(logger)
def get_goal(goal_id: str) -> str:
    """
    Get detailed information about a specific goal.
    
    Args:
        goal_id: Goal ID
        
    Returns:
        JSON string with goal and all task details
    """
    goal = agent.get_goal(goal_id)
    return json.dumps(goal, indent=2)


@mcp.tool()
@handle_errors(logger)
def list_goals(status: Optional[str] = None, priority: Optional[str] = None) -> str:
    """
    List all goals with optional filters.
    
    Args:
        status: Filter by status (planned, in_progress, completed)
        priority: Filter by priority (high, medium, low)
        
    Returns:
        JSON string with list of goals
    """
    goals = agent.list_goals(status, priority)
    return json.dumps(goals, indent=2)


@mcp.tool()
@handle_errors(logger)
def get_next_tasks(goal_id: Optional[str] = None) -> str:
    """
    Get next executable tasks (tasks with no pending dependencies).
    
    Args:
        goal_id: Optional goal ID to filter by
        
    Returns:
        JSON string with list of executable tasks
    """
    tasks = agent.get_next_tasks(goal_id)
    return json.dumps(tasks, indent=2)


@mcp.tool()
@handle_errors(logger)
def update_task_status(task_id: str, status: str, result: Optional[str] = None) -> str:
    """
    Update the status of a task.
    
    Args:
        task_id: Task ID (e.g., TASK-0001)
        status: New status (pending, in_progress, completed, failed)
        result: Optional task result as JSON
        
    Returns:
        JSON string with updated task
    """
    result_dict = json.loads(result) if result else None
    task = agent.update_task_status(task_id, status, result_dict)
    return json.dumps(task.to_dict(), indent=2)


@mcp.tool()
@handle_errors(logger)
def get_task(task_id: str) -> str:
    """
    Get detailed information about a specific task.
    
    Args:
        task_id: Task ID
        
    Returns:
        JSON string with task details
    """
    task = agent.get_task(task_id)
    return json.dumps(task, indent=2)


@mcp.tool()
@handle_errors(logger)
def generate_execution_plan(goal_id: str) -> str:
    """
    Generate a phased execution plan for a goal based on task dependencies.
    
    Args:
        goal_id: Goal ID
        
    Returns:
        JSON string with execution plan organized by phases
    """
    plan = agent.generate_execution_plan(goal_id)
    return json.dumps(plan, indent=2)


if __name__ == "__main__":
    try:
        logger.info("Starting Goal Agent MCP Server...")
        mcp.run()
        
    except KeyboardInterrupt:
        log_server_shutdown(logger, "Goal Agent Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise