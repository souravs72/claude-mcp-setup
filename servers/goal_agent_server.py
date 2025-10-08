#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from typing import Any
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Load environment variables
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'
    load_dotenv(env_path)
    print(f"Loaded environment from: {env_path}")
except ImportError:
    print("python-dotenv not installed. Using system environment variables.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("Goal-Based AI Agent Server")

class GoalAgent:
    def __init__(self):
        self.goals = {}
        self.tasks = {}
        self.goal_counter = 0
        self.task_counter = 0
        
    def create_goal(self, description: str, priority: str = "medium", 
                   repos: list[str] = None, metadata: dict = None) -> dict:
        """Create a new goal"""
        self.goal_counter += 1
        goal_id = f"GOAL-{self.goal_counter}"
        
        goal = {
            "id": goal_id,
            "description": description,
            "priority": priority,
            "status": "planned",
            "repos": repos or [],
            "tasks": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.goals[goal_id] = goal
        logger.info(f"Created goal: {goal_id}")
        return goal
    
    def break_down_goal(self, goal_id: str, subtasks: list[dict]) -> dict:
        """Break down a goal into smaller tasks"""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")
        
        goal = self.goals[goal_id]
        
        for subtask in subtasks:
            self.task_counter += 1
            task_id = f"TASK-{self.task_counter}"
            
            task = {
                "id": task_id,
                "goal_id": goal_id,
                "description": subtask.get("description"),
                "type": subtask.get("type", "general"),
                "status": "pending",
                "priority": subtask.get("priority", "medium"),
                "dependencies": subtask.get("dependencies", []),
                "repo": subtask.get("repo"),
                "jira_ticket": subtask.get("jira_ticket"),
                "estimated_effort": subtask.get("estimated_effort"),
                "assigned_tools": subtask.get("tools", []),
                "created_at": datetime.now().isoformat(),
                "completed_at": None,
                "result": None
            }
            
            self.tasks[task_id] = task
            goal["tasks"].append(task_id)
        
        goal["updated_at"] = datetime.now().isoformat()
        goal["status"] = "in_progress"
        
        return goal
    
    def get_goal(self, goal_id: str) -> dict:
        """Get a specific goal with all its tasks"""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")
        
        goal = self.goals[goal_id].copy()
        goal["task_details"] = [
            self.tasks[task_id] for task_id in goal["tasks"] 
            if task_id in self.tasks
        ]
        return goal
    
    def list_goals(self, status: str = None, priority: str = None) -> list[dict]:
        """list all goals with optional filters"""
        goals = list(self.goals.values())
        
        if status:
            goals = [g for g in goals if g["status"] == status]
        if priority:
            goals = [g for g in goals if g["priority"] == priority]
        
        return goals
    
    def update_task_status(self, task_id: str, status: str, result: Any = None) -> dict:
        """Update task status and result"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        task["status"] = status
        
        if result:
            task["result"] = result
        
        if status == "completed":
            task["completed_at"] = datetime.now().isoformat()
        
        # Update goal status if all tasks are completed
        goal_id = task["goal_id"]
        goal = self.goals[goal_id]
        all_tasks = [self.tasks[tid] for tid in goal["tasks"] if tid in self.tasks]
        
        if all(t["status"] == "completed" for t in all_tasks):
            goal["status"] = "completed"
            goal["updated_at"] = datetime.now().isoformat()
        
        return task
    
    def get_next_tasks(self, goal_id: str = None) -> list[dict]:
        """Get next executable tasks (no pending dependencies)"""
        tasks_to_check = []
        
        if goal_id:
            if goal_id not in self.goals:
                raise ValueError(f"Goal {goal_id} not found")
            task_ids = self.goals[goal_id]["tasks"]
            tasks_to_check = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
        else:
            tasks_to_check = list(self.tasks.values())
        
        executable_tasks = []
        
        for task in tasks_to_check:
            if task["status"] != "pending":
                continue
            
            # Check if all dependencies are completed
            dependencies_met = all(
                self.tasks.get(dep_id, {}).get("status") == "completed"
                for dep_id in task["dependencies"]
            )
            
            if dependencies_met:
                executable_tasks.append(task)
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        executable_tasks.sort(key=lambda t: priority_order.get(t["priority"], 1))
        
        return executable_tasks
    
    def get_task(self, task_id: str) -> dict:
        """Get a specific task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        return self.tasks[task_id]
    
    def generate_execution_plan(self, goal_id: str) -> dict:
        """Generate an execution plan for a goal"""
        if goal_id not in self.goals:
            raise ValueError(f"Goal {goal_id} not found")
        
        goal = self.goals[goal_id]
        tasks = [self.tasks[tid] for tid in goal["tasks"] if tid in self.tasks]
        
        # Build execution phases based on dependencies
        phases = []
        remaining_tasks = tasks.copy()
        
        while remaining_tasks:
            phase_tasks = []
            
            for task in remaining_tasks[:]:
                dependencies_met = all(
                    dep_id not in [t["id"] for t in remaining_tasks]
                    for dep_id in task["dependencies"]
                )
                
                if dependencies_met:
                    phase_tasks.append(task)
                    remaining_tasks.remove(task)
            
            if not phase_tasks:
                # Circular dependency or orphaned tasks
                phases.append({
                    "phase": len(phases) + 1,
                    "tasks": remaining_tasks,
                    "note": "Warning: Possible circular dependencies"
                })
                break
            
            phases.append({
                "phase": len(phases) + 1,
                "tasks": phase_tasks
            })
        
        return {
            "goal_id": goal_id,
            "goal_description": goal["description"],
            "total_tasks": len(tasks),
            "total_phases": len(phases),
            "execution_phases": phases
        }

agent = GoalAgent()

@mcp.tool("create_goal")
def create_goal(description: str, priority: str = "medium", 
                repos: str = None, metadata: str = None) -> str:
    """
    Create a new goal for the AI agent to work on.
    
    Args:
        description: Clear description of the goal
        priority: Priority level (high, medium, low)
        repos: JSON array of repository names involved
        metadata: Additional metadata as JSON object
    """
    try:
        repos_list = json.loads(repos) if repos else []
        metadata_dict = json.loads(metadata) if metadata else {}
        
        goal = agent.create_goal(description, priority, repos_list, metadata_dict)
        return json.dumps(goal, indent=2)
    except Exception as e:
        logger.error(f"Error creating goal: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("break_down_goal")
def break_down_goal(goal_id: str, subtasks: str) -> str:
    """
    Break down a goal into executable subtasks.
    
    Args:
        goal_id: The ID of the goal to break down
        subtasks: JSON array of subtask objects with structure:
                  [{
                    "description": "Task description",
                    "type": "code|documentation|testing|review",
                    "priority": "high|medium|low",
                    "repo": "repo-name",
                    "dependencies": ["TASK-1", "TASK-2"],
                    "tools": ["github", "jira", "frappe"],
                    "estimated_effort": "1h|2h|1d",
                    "jira_ticket": "PROJ-123"
                  }]
    """
    try:
        subtasks_list = json.loads(subtasks)
        goal = agent.break_down_goal(goal_id, subtasks_list)
        return json.dumps(goal, indent=2)
    except Exception as e:
        logger.error(f"Error breaking down goal: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("get_goal")
def get_goal(goal_id: str) -> str:
    """Get detailed information about a specific goal"""
    try:
        goal = agent.get_goal(goal_id)
        return json.dumps(goal, indent=2)
    except Exception as e:
        logger.error(f"Error getting goal: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("list_goals")
def list_goals(status: str = None, priority: str = None) -> str:
    """
    list all goals with optional filters.
    
    Args:
        status: Filter by status (planned, in_progress, completed)
        priority: Filter by priority (high, medium, low)
    """
    try:
        goals = agent.list_goals(status, priority)
        return json.dumps(goals, indent=2)
    except Exception as e:
        logger.error(f"Error listing goals: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("get_next_tasks")
def get_next_tasks(goal_id: str = None) -> str:
    """
    Get next executable tasks (tasks with no pending dependencies).
    
    Args:
        goal_id: Optional goal ID to filter tasks by goal
    """
    try:
        tasks = agent.get_next_tasks(goal_id)
        return json.dumps(tasks, indent=2)
    except Exception as e:
        logger.error(f"Error getting next tasks: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("update_task_status")
def update_task_status(task_id: str, status: str, result: str = None) -> str:
    """
    Update the status of a task.
    
    Args:
        task_id: The task ID to update
        status: New status (pending, in_progress, completed, failed, blocked)
        result: JSON object with task execution result
    """
    try:
        result_dict = json.loads(result) if result else None
        task = agent.update_task_status(task_id, status, result_dict)
        return json.dumps(task, indent=2)
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("get_task")
def get_task(task_id: str) -> str:
    """Get detailed information about a specific task"""
    try:
        task = agent.get_task(task_id)
        return json.dumps(task, indent=2)
    except Exception as e:
        logger.error(f"Error getting task: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("generate_execution_plan")
def generate_execution_plan(goal_id: str) -> str:
    """
    Generate a phased execution plan for a goal based on task dependencies.
    Shows which tasks can be executed in parallel and which must wait.
    """
    try:
        plan = agent.generate_execution_plan(goal_id)
        return json.dumps(plan, indent=2)
    except Exception as e:
        logger.error(f"Error generating execution plan: {str(e)}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    logger.info("Starting Goal-Based AI Agent Server")
    mcp.run()