# Goal-Based AI MCP Agent

A sophisticated Model Context Protocol (MCP) server that enables AI-driven goal planning, task breakdown, and execution across multiple platforms including GitHub, Jira, and Frappe.

## Features

- **Goal Management**: Create and track high-level goals with priorities
- **Task Breakdown**: Automatically decompose goals into executable subtasks
- **Dependency Management**: Handle task dependencies and execution order
- **Multi-Platform Integration**: Works with GitHub, Jira, and Frappe
- **Execution Planning**: Generate phased execution plans based on dependencies
- **Status Tracking**: Monitor progress of goals and tasks in real-time

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Goal-Based AI Agent Server             │
│  (Orchestrates goals, tasks, and execution)     │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        │             │             │             │
┌───────▼──────┐ ┌───▼──────┐ ┌───▼──────┐ ┌────▼─────┐
│   GitHub     │ │   Jira   │ │  Frappe  │ │ Internet │
│   Server     │ │  Server  │ │  Server  │ │  Server  │
└──────────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Installation

1. **Install Python dependencies** for each server:

```bash
# Goal Agent Server
pip install -r requirements/goal_agent_requirements.txt

# Jira Server
pip install -r requirements/jira_requirements.txt

# Other servers (if not already installed)
pip install -r requirements/github_requirements.txt
pip install -r requirements/frappe_requirements.txt
pip install -r requirements/internet_requirements.txt
```

2. **Configure environment variables** in `.env`:

```bash
cp .env.template .env
# Edit .env with your credentials
```

3. **Start all servers**:

```bash
python scripts/start_all_servers.py
```

## Configuration

### Jira Setup

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create an API token
3. Add to `.env`:
   - `JIRA_BASE_URL`: Your Jira instance URL
   - `JIRA_EMAIL`: Your Jira email
   - `JIRA_API_TOKEN`: Generated API token
   - `JIRA_PROJECT_KEY`: Default project key

### MCP Settings

Add the servers to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "goal-agent-server": {
      "command": "python",
      "args": ["/absolute/path/to/servers/goal_agent_server.py"]
    },
    "jira-server": {
      "command": "python",
      "args": ["/absolute/path/to/servers/jira_server.py"],
      "env": {
        "JIRA_BASE_URL": "https://your-domain.atlassian.net",
        "JIRA_EMAIL": "your@email.com",
        "JIRA_API_TOKEN": "your_token",
        "JIRA_PROJECT_KEY": "PROJ"
      }
    }
  }
}
```

## Usage Examples

### Example 1: Simple Feature Development

```
User: "I need to add a user authentication feature to my app. Create a goal for this."

AI uses: create_goal
Goal: GOAL-1 created with priority "high"

User: "Break this down into tasks."

AI uses: break_down_goal
Tasks created:
- TASK-1: Design authentication schema (repo: backend)
- TASK-2: Implement API endpoints (repo: backend, depends on TASK-1)
- TASK-3: Create login UI (repo: frontend, depends on TASK-2)
- TASK-4: Write tests (repo: backend, depends on TASK-2)
- TASK-5: Update documentation (depends on TASK-2, TASK-3)

User: "Show me the execution plan."

AI uses: generate_execution_plan
Returns phased plan:
- Phase 1: TASK-1 (can start immediately)
- Phase 2: TASK-2, TASK-4 (parallel, after TASK-1)
- Phase 3: TASK-3, TASK-5 (after Phase 2)
```

### Example 2: Bug Fix Workflow

```
User: "Create a goal to fix the payment processing bug in PROJ-456."

AI uses: 
1. create_goal (with metadata: jira_ticket: "PROJ-456")
2. jira_get_issue (to understand the bug)
3. break_down_goal with tasks:
   - TASK-1: Investigate root cause
   - TASK-2: Write failing test
   - TASK-3: Implement fix (depends on TASK-1, TASK-2)
   - TASK-4: Update Jira ticket with resolution

User: "Start working on the first task."

AI uses: 
1. get_next_tasks (returns TASK-1)
2. update_task_status (TASK-1, "in_progress")
3. GitHub tools to search codebase
4. update_task_status (TASK-1, "completed", with findings)
```

### Example 3: Multi-Repo Refactoring

```
User: "I want to migrate our authentication from repo-a to a shared library repo-b, 
       then update repo-a and repo-c to use it."

AI uses: create_goal with repos: ["repo-a", "repo-b", "repo-c"]

AI uses: break_down_goal
Tasks:
- TASK-1: Extract auth code from repo-a (repo: repo-a)
- TASK-2: Create library structure in repo-b (repo: repo-b, depends on TASK-1)
- TASK-3: Publish library package (repo: repo-b, depends on TASK-2)
- TASK-4: Update repo-a to use library (repo: repo-a, depends on TASK-3)
- TASK-5: Update repo-c to use library (repo: repo-c, depends on TASK-3)
- TASK-6: Create migration guide (depends on TASK-4, TASK-5)
- TASK-7: Create Jira tickets for teams

User: "Create Jira tickets for each repo update."

AI uses:
1. jira_create_issue for repo-a work
2. jira_create_issue for repo-c work
3. jira_link_issues to connect them
4. Updates tasks with Jira ticket references
```

### Example 4: Continuous Workflow

```
User: "What should I work on next?"

AI uses: get_next_tasks
Returns: TASK-3, TASK-5 (ready to start)

User: "I'll work on TASK-3. Update the status."

AI uses: update_task_status(TASK-3, "in_progress")

User: "I've completed TASK-3. Here's the PR link."

AI uses: 
1. update_task_status(TASK-3, "completed", {pr: "link"})
2. get_next_tasks (now TASK-7 is available)
3. Suggests: "TASK-7 is now ready! It depends on the work you just completed."
```

## API Reference

### Goal Management Tools

#### `create_goal`
Creates a new goal with description, priority, and metadata.

**Parameters:**
- `description` (string): Clear description of the goal
- `priority` (string): "high" | "medium" | "low"
- `repos` (JSON array): List of repository names
- `metadata` (JSON object): Additional metadata

**Returns:** Goal object with ID

#### `get_goal`
Retrieves detailed information about a specific goal.

**Parameters:**
- `goal_id` (string): The goal ID (e.g., "GOAL-1")

**Returns:** Goal object with task details

#### `list_goals`
Lists all goals with optional filters.

**Parameters:**
- `status` (string, optional): Filter by status
- `priority` (string, optional): Filter by priority

**Returns:** Array of goal objects

### Task Management Tools

#### `break_down_goal`
Breaks down a goal into executable subtasks.

**Parameters:**
- `goal_id` (string): The goal to break down
- `subtasks` (JSON array): Array of task objects with:
  - `description`: Task description
  - `type`: "code" | "documentation" | "testing" | "review"
  - `priority`: "high" | "medium" | "low"
  - `repo`: Repository name
  - `dependencies`: Array of task IDs
  - `tools`: Array of required tools
  - `estimated_effort`: Effort estimate
  - `jira_ticket`: Associated Jira ticket

**Returns:** Updated goal object

#### `get_task`
Retrieves detailed information about a specific task.

**Parameters:**
- `task_id` (string): The task ID (e.g., "TASK-1")

**Returns:** Task object

#### `update_task_status`
Updates the status of a task.

**Parameters:**
- `task_id` (string): The task ID
- `status` (string): "pending" | "in_progress" | "completed" | "failed" | "blocked"
- `result` (JSON object, optional): Execution result data

**Returns:** Updated task object

#### `get_next_tasks`
Gets next executable tasks (no pending dependencies).

**Parameters:**
- `goal_id` (string, optional): Filter by specific goal

**Returns:** Array of ready-to-execute tasks

#### `generate_execution_plan`
Generates a phased execution plan based on dependencies.

**Parameters:**
- `goal_id` (string): The goal to plan

**Returns:** Execution plan with phases

### Jira Integration Tools

#### `jira_create_issue`
Creates a new Jira issue.

**Parameters:**
- `project_key`: Project key
- `summary`: Issue title
- `description`: Detailed description
- `issue_type`: "Task" | "Bug" | "Story" | "Epic"
- `priority`: "Highest" | "High" | "Medium" | "Low" | "Lowest"
- `assignee`: Assignee account ID
- `labels`: JSON array of labels

#### `jira_search_issues`
Search issues using JQL.

**Parameters:**
- `jql`: JQL query string
- `max_results`: Maximum results to return
- `fields`: Fields to include

#### `jira_get_issue`
Get details of a specific issue.

**Parameters:**
- `issue_key`: Issue key (e.g., "PROJ-123")

#### `jira_transition_issue`
Change issue status.

**Parameters:**
- `issue_key`: Issue key
- `transition_id`: Transition ID
- `comment`: Optional comment

#### `jira_add_comment`
Add comment to an issue.

**Parameters:**
- `issue_key`: Issue key
- `comment`: Comment text

#### `jira_link_issues`
Create link between two issues.

**Parameters:**
- `inward_issue`: First issue key
- `outward_issue`: Second issue key
- `link_type`: "Relates" | "Blocks" | "Duplicates"

## Best Practices

1. **Start with Clear Goals**: Write descriptive goals that capture the intent
2. **Break Down Wisely**: Create tasks that are independently testable
3. **Use Dependencies**: Properly model task dependencies for accurate planning
4. **Tag with Repos**: Always specify which repositories are involved
5. **Link Jira Tickets**: Connect tasks to Jira for project management
6. **Update Status**: Keep task status current for accurate progress tracking
7. **Review Plans**: Use `generate_execution_plan` to validate task breakdown

## Troubleshooting

### Server Won't Start
- Check log files in `logs/` directory
- Verify environment variables in `.env`
- Ensure all dependencies are installed

### Jira Connection Failed
- Verify API token is valid
- Check base URL format (should include https://)
- Ensure email matches Jira account

### Tasks Not Appearing
- Check goal status with `get_goal`
- Verify task dependencies are correctly set
- Use `get_next_tasks` to see executable tasks

## Advanced Patterns

### Pattern 1: Sprint Planning
```python
# Create goal for sprint
goal = create_goal("Complete Q1 Sprint Features", priority="high")

# Break down with estimated efforts
break_down_goal(goal_id, [
    {"description": "Feature A", "estimated_effort": "3d"},
    {"description": "Feature B", "estimated_effort": "2d"},
    {"description": "Feature C", "estimated_effort": "5d"}
])

# Generate plan and create Jira tickets
plan = generate_execution_plan(goal_id)
# Create Jira issues for each task
# Link to Jira sprint
```

### Pattern 2: Release Management
```python
# Create release goal with multiple repos
goal = create_goal(
    "Release v2.0",
    repos=["api", "web", "mobile", "docs"],
    metadata={"version": "2.0.0", "release_date": "2025-11-01"}
)

# Break down by repo and type
break_down_goal(goal_id, [
    # API tasks
    {"description": "API: Update version", "repo": "api", "type": "code"},
    {"description": "API: Run tests", "repo": "api", "type": "testing", 
     "dependencies": ["TASK-1"]},
    
    # Web tasks
    {"description": "Web: Update dependencies", "repo": "web", "type": "code"},
    {"description": "Web: Build production", "repo": "web", "type": "code",
     "dependencies": ["TASK-3"]},
    
    # Documentation
    {"description": "Update changelog", "repo": "docs", "type": "documentation",
     "dependencies": ["TASK-2", "TASK-4"]}
])
```

### Pattern 3: Investigation & Fix
```python
# Create investigation goal
goal = create_goal("Investigate Performance Issue", priority="high")

# Break into investigation then fix
break_down_goal(goal_id, [
    {"description": "Profile application", "type": "testing"},
    {"description": "Identify bottlenecks", "dependencies": ["TASK-1"]},
    {"description": "Create fix proposal", "dependencies": ["TASK-2"]},
    {"description": "Implement optimizations", "dependencies": ["TASK-3"]},
    {"description": "Benchmark improvements", "type": "testing", 
     "dependencies": ["TASK-4"]}
])
```

## Contributing

Contributions are welcome! Please:
1. Test your changes with multiple scenarios
2. Update documentation
3. Follow the existing code style
4. Add examples for new features

## License

MIT License - See LICENSE file for details