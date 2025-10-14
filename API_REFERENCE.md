# API Reference

Complete API documentation for all MCP servers in the Claude MCP Setup.

## 📋 Table of Contents

- [Goal Agent Server](#goal-agent-server)
- [GitHub Server](#github-server)
- [Jira Server](#jira-server)
- [Internet Server](#internet-server)
- [Memory Cache Server](#memory-cache-server)
- [Frappe Server](#frappe-server)
- [File Server](#file-server)

---

## 🎯 Goal Agent Server

### Core Operations

#### Create Goal

```python
create_goal(description: str, priority: str = "medium", repos: str = null, metadata: str = null)
```

Creates a new goal with automatic task breakdown and dependency resolution.

**Example:**

```python
create_goal("Add OAuth2 authentication to the API", "high", '["repo1", "repo2"]', '{"deadline": "2024-01-15"}')
```

#### Break Down Goal

```python
break_down_goal(goal_id: str, subtasks: str)
```

Breaks down a goal into executable subtasks with validation.

#### Get Goal

```python
get_goal(goal_id: str)
```

Retrieves detailed information about a specific goal.

#### List Goals

```python
list_goals(status: str = null, priority: str = null)
```

Lists all goals with optional filtering.

#### Update Goal

```python
update_goal(goal_id: str, description: str = null, priority: str = null, status: str = null, repos: str = null, metadata: str = null)
```

Updates an existing goal with validation.

### Task Management

#### Get Next Tasks

```python
get_next_tasks(goal_id: str = null)
```

Gets next executable tasks (tasks with no pending dependencies).

#### Update Task Status

```python
update_task_status(task_id: str, status: str, result: str = null)
```

Updates the status of a task with validation.

#### Get Task

```python
get_task(task_id: str)
```

Gets detailed information about a specific task.

#### Delete Task

```python
delete_task(task_id: str)
```

Deletes a single task from a goal.

#### Batch Update Tasks

```python
batch_update_tasks(updates: str)
```

Updates multiple tasks concurrently.

#### Batch Get Tasks

```python
batch_get_tasks(task_ids: str)
```

Retrieves multiple tasks concurrently.

### Execution Planning

#### Generate Execution Plan

```python
generate_execution_plan(goal_id: str)
```

Generates a phased execution plan for a goal.

#### Get Agent Status

```python
get_agent_status(random_string: str)
```

Gets current goal agent status and statistics.

#### Delete Goal

```python
delete_goal(goal_id: str)
```

Deletes a goal and all its associated tasks.

---

## 🐙 GitHub Server

### Repository Management

#### List Repositories

```python
list_repositories(username: str = null, sort: str = "updated", limit: int = 20)
```

Lists repositories for a user or authenticated user.

#### Get Directory Tree

```python
get_directory_tree(repo_name: str, path: str = "", branch: str = "main", recursive: bool = False)
```

Gets directory structure of a repository.

#### List Branches

```python
list_branches(repo_name: str, limit: int = 20)
```

Lists branches in a repository.

#### Get Branch Info

```python
get_branch_info(repo_name: str, branch_name: str)
```

Gets information about a specific branch.

#### Create Branch

```python
create_branch(repo_name: str, branch_name: str, source_branch: str = "main")
```

Creates a new branch from a source branch.

### File Operations

#### Get File Content

```python
get_file_content(repo_name: str, file_path: str, branch: str = "main")
```

Gets content of a specific file from a repository.

#### Create or Update File

```python
create_or_update_file(repo_name: str, file_path: str, content: str, commit_message: str, branch: str = null, sha: str = null)
```

Creates or updates a file in the repository.

#### Delete File

```python
delete_file(repo_name: str, file_path: str, commit_message: str, branch: str = "dev-sourav", sha: str = null)
```

Deletes a file from the repository.

#### Commit Multiple Files

```python
commit_multiple_files(repo_name: str, branch: str, files: str, commit_message: str, base_branch: str = null)
```

Commits multiple file changes in a single commit.

### Issues and Pull Requests

#### List Issues

```python
list_issues(repo_name: str, state: str = "open", labels: str = null, limit: int = 10)
```

Lists issues from a repository.

#### Create Issue

```python
create_issue(repo_name: str, title: str, body: str = "", labels: str = null, assignees: str = null)
```

Creates a new issue in a repository.

#### Create Pull Request

```python
create_pull_request(repo_name: str, title: str, head: str, base: str, body: str = "")
```

Creates a pull request.

---

## 🎫 Jira Server

### Issue Management

#### Get Issue

```python
get_issue(issue_key: str, fields: str = null)
```

Gets detailed information about a Jira issue.

#### Search Issues

```python
search_issues(jql: str, max_results: int = 50, fields: str = null, start_at: int = 0)
```

Searches for Jira issues using JQL.

#### Build JQL

```python
build_jql(project: str = null, status: str = null, assignee: str = null, issue_type: str = null)
```

Builds a JQL query from common parameters.

#### Create Issue

```python
create_issue(project_key: str, summary: str, description: str, issue_type: str = "Task", priority: str = null, assignee: str = null, labels: str = null, additional_fields: object = null, rich_text: bool = False)
```

Creates a new Jira issue.

#### Create Issues Bulk

```python
create_issues_bulk(issues: str)
```

Creates multiple Jira issues in a single API call.

#### Update Issue

```python
update_issue(issue_key: str, fields: str)
```

Updates an existing Jira issue.

#### Delete Issue

```python
delete_issue(issue_key: str)
```

Deletes a Jira issue.

### Workflow Management

#### Get Transitions

```python
get_transitions(issue_key: str)
```

Gets available status transitions for an issue.

#### Transition Issue

```python
transition_issue(issue_key: str, transition_id: str, comment: str = null, fields: str = null)
```

Transitions a Jira issue to a different status.

#### Add Comment

```python
add_comment(issue_key: str, comment: str, rich_text: bool = False)
```

Adds a comment to a Jira issue.

#### Get Comments

```python
get_comments(issue_key: str)
```

Gets all comments for a Jira issue.

#### Link Issues

```python
link_issues(inward_issue: str, outward_issue: str, link_type: str = "Relates")
```

Creates a link between two Jira issues.

### Project and Sprint Management

#### Get Projects

```python
get_projects(random_string: str)
```

Gets all accessible Jira projects.

#### Get Project Issue Types

```python
get_project_issue_types(project_key: str)
```

Gets available issue types for a Jira project.

#### Get Creatable Issue Types

```python
get_creatable_issue_types(project_key: str)
```

Gets issue types that can be created in a project with their required fields.

#### Get Create Metadata

```python
get_create_metadata(project_key: str, issue_type_id: str)
```

Gets field metadata for creating issues in a project.

#### Assign Issue

```python
assign_issue(issue_key: str, account_id: str)
```

Assigns a Jira issue to a user.

#### Get Watchers

```python
get_watchers(issue_key: str)
```

Gets watchers for a Jira issue.

#### Add Watcher

```python
add_watcher(issue_key: str, account_id: str)
```

Adds a watcher to a Jira issue.

### Sprint Management

#### Get Boards

```python
get_boards(project_key: str = null)
```

Gets Jira boards, optionally filtered by project.

#### Get Active Sprints

```python
get_active_sprints(board_id: str)
```

Gets active sprints for a Jira board.

#### Add to Sprint

```python
add_to_sprint(sprint_id: int, issue_keys: str)
```

Adds issues to a sprint.

#### Add Issue to Active Sprint

```python
add_issue_to_active_sprint(issue_key: str, project_key: str)
```

Adds an issue to the active sprint (automatic sprint detection).

---

## 🌐 Internet Server

### Search Operations

#### Web Search

```python
web_search(query: str, max_results: int = 10, search_type: str = null, file_type: str = null, date_restrict: str = null)
```

Searches the web using Google Custom Search API.

#### Web Fetch

```python
web_fetch(url: str, timeout: int = null)
```

Fetches content from a specific URL.

#### Batch Fetch URLs

```python
batch_fetch_urls(urls: str, timeout: int = null)
```

Fetches multiple URLs concurrently.

#### Batch Search

```python
batch_search(queries: str, max_results: int = 10)
```

Performs multiple searches concurrently.

#### Search and Fetch

```python
search_and_fetch(query: str, max_results: int = 5, fetch_content: bool = True)
```

Searches and fetches full content from top results in one operation.

#### Parallel Search with Filters

```python
parallel_search_with_filters(query: str, filters: str)
```

Performs the same search with multiple filter combinations concurrently.

---

## 💾 Memory Cache Server

### Basic Operations

#### Set Cache

```python
cache_set(key: str, value: str, ttl: int = null)
```

Sets a value in cache with optional TTL.

#### Get Cache

```python
cache_get(key: str)
```

Gets a value from cache.

#### Delete Cache

```python
cache_delete(keys: str)
```

Deletes one or more keys from cache.

#### Check Exists

```python
cache_exists(keys: str)
```

Checks if keys exist in cache.

### Advanced Operations

#### Set Expiration

```python
cache_expire(key: str, seconds: int)
```

Sets expiration time on a key.

#### Get TTL

```python
cache_ttl(key: str)
```

Gets time to live for a key.

#### Get Keys

```python
cache_keys(pattern: str = "*")
```

Gets all keys matching a pattern.

#### Scan Keys

```python
cache_scan(cursor: int = 0, match: str = null, count: int = 10)
```

Incrementally scans keys (production-safe alternative to cache_keys).

#### Multi Get/Set

```python
cache_mget(keys: str)
cache_mset(data: str)
```

Gets/sets multiple values at once.

#### Numeric Operations

```python
cache_incr(key: str, amount: int = 1)
cache_decr(key: str, amount: int = 1)
```

Increments/decrements a numeric key.

### System Operations

#### Flush Cache

```python
cache_flush(random_string: str)
```

Clears all keys in current database.

#### Cache Info

```python
cache_info(random_string: str)
```

Gets Redis server information and statistics.

#### Ping Cache

```python
cache_ping(random_string: str)
```

Pings Redis to check connection status.

---

## 🏢 Frappe Server

### Document Operations

#### Get Document

```python
frappe_get_document(doctype: str, name: str)
```

Gets a specific document from Frappe.

#### Get List

```python
frappe_get_list(doctype: str, filters: str = null, fields: str = null, limit: int = 20, order_by: str = null)
```

Gets a list of documents from Frappe.

#### Create Document

```python
frappe_create_document(doctype: str, data: str)
```

Creates a new document in Frappe.

#### Update Document

```python
frappe_update_document(doctype: str, name: str, data: str)
```

Updates an existing document in Frappe.

#### Delete Document

```python
frappe_delete_document(doctype: str, name: str)
```

Deletes a document from Frappe.

---

## 📁 File Server

### File Operations

#### Read File

```python
read_file(file_path: str, encoding: str = "utf-8")
```

Reads the contents of a file from the local file system.

#### Write File

```python
write_file(file_path: str, content: str, encoding: str = "utf-8", create_dirs: bool = True)
```

Writes content to a file on the local file system.

#### Get File Info

```python
get_file_info(file_path: str)
```

Gets detailed information about a file or directory without reading its contents.

### Directory Operations

#### List Directory

```python
list_directory(dir_path: str, include_hidden: bool = False, recursive: bool = False)
```

Lists the contents of a directory.

#### Search Files

```python
search_files(dir_path: str, pattern: str, include_hidden: bool = False)
```

Searches for files matching a pattern in a directory.

#### Search Files System Wide

```python
search_files_system_wide(pattern: str, include_hidden: bool = False, max_depth: int = 3)
```

Searches for files system-wide within allowed directories.

---

## 🔧 Error Handling

All servers implement consistent error handling:

- **Validation Errors**: Invalid parameters or missing required fields
- **Authentication Errors**: Invalid API keys or tokens
- **Permission Errors**: Insufficient permissions for operations
- **Network Errors**: Connection timeouts or network issues
- **Rate Limiting**: API rate limit exceeded

## 📊 Response Formats

All API responses follow a consistent JSON format:

```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2024-01-01T00:00:00Z",
    "server": "goal-agent",
    "version": "1.0.0"
  }
}
```

Error responses:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid parameter: goal_id is required",
    "details": { ... }
  }
}
```

---

## 🚀 Performance Considerations

- **Connection Pooling**: All servers use connection pooling for database and API connections
- **Caching**: Redis caching layer for frequently accessed data
- **Batch Operations**: Support for bulk operations to reduce API calls
- **Async Operations**: Non-blocking operations where possible
- **Rate Limiting**: Built-in rate limiting to respect API quotas

## 🔒 Security

- **API Key Management**: Secure storage and rotation of API keys
- **Input Validation**: Comprehensive input validation and sanitization
- **Path Validation**: File system access restrictions and validation
- **Error Handling**: Secure error messages that don't expose sensitive information
