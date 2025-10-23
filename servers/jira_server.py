#!/usr/bin/env python3
"""
Jira MCP Server - Production Ready
Provides integration with Jira via REST API
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
from requests.auth import HTTPBasicAuth

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
    JiraConfig,
    validate_config,
    ConfigurationError,
)
from servers.base_client import BaseClient, handle_errors

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "jira_server.log"
logger = setup_logging("JiraServer", log_file=log_file)

load_env_file()
mcp = FastMCP("Jira Integration Server")


class JiraClient(BaseClient):
    """Jira API client with authentication and error handling."""

    def __init__(self, config: JiraConfig):
        super().__init__(
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
            logger=logger,
        )

        self.config = config
        self.auth = HTTPBasicAuth(config.email, config.api_token)
        self.last_request_time = None
        self.rate_limit_delay = config.rate_limit_delay
        self.agile_api_available = False

        # Set headers
        self.session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

        # Verify connection
        self._verify_connection()

        # Check Agile API availability
        self.agile_api_available = self._verify_agile_api()

        logger.info("Jira client initialized successfully")

    def _verify_connection(self):
        """Verify Jira connection."""
        try:
            response = self.get("/rest/api/3/myself", auth=self.auth)
            user_data = response.json()
            logger.info(f"Connected as: {user_data.get('displayName', 'Unknown')}")
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            raise

    def _verify_agile_api(self) -> bool:
        """Check if Agile API is available."""
        try:
            self._make_jira_request("GET", "/rest/agile/1.0/board", params={"maxResults": 1})
            logger.info("Agile API is available")
            return True
        except Exception as e:
            logger.warning(f"Agile API not available: {e}")
            return False

    def _rate_limit(self):
        """Implement basic rate limiting."""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)

        self.last_request_time = datetime.now()

    def _make_jira_request(self, method: str, endpoint: str, **kwargs):
        """Make request with rate limiting."""
        self._rate_limit()

        # Add auth if not present
        if "auth" not in kwargs:
            kwargs["auth"] = self.auth

        return self._make_request(method, endpoint, **kwargs)

    def _parse_jira_error(self, response) -> str:
        """Parse Jira error response for meaningful messages."""
        try:
            error_data = response.json()

            # Jira returns errors in various formats
            if "errorMessages" in error_data and error_data["errorMessages"]:
                return " | ".join(error_data["errorMessages"])

            if "errors" in error_data and error_data["errors"]:
                errors = [f"{field}: {msg}" for field, msg in error_data["errors"].items()]
                return " | ".join(errors)

            return error_data.get("message", response.text[:500])
        except Exception:
            return response.text[:500]

    def _format_description(self, description: str, rich_text: bool = False) -> Dict:
        """
        Format description for Atlassian Document Format.

        Args:
            description: Description text
            rich_text: If True, preserve line breaks and formatting

        Returns:
            Formatted ADF object
        """
        if not description:
            return {"type": "doc", "version": 1, "content": []}

        if rich_text:
            # Split by paragraphs and preserve structure
            paragraphs = description.split("\n\n")
            content = []

            for para in paragraphs:
                if para.strip():
                    content.append(
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": para.strip()}],
                        }
                    )

            return {
                "type": "doc",
                "version": 1,
                "content": (
                    content
                    if content
                    else [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ]
                ),
            }
        else:
            # Simple single paragraph
            return {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }

    def build_jql(
        self,
        project: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        issue_type: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Build JQL query from common parameters.

        Args:
            project: Project key
            status: Status name
            assignee: Assignee username or 'currentUser()'
            issue_type: Issue type name
            **kwargs: Additional JQL conditions

        Returns:
            JQL query string
        """
        conditions = []

        if project:
            conditions.append(f'project = "{project}"')
        if status:
            conditions.append(f'status = "{status}"')
        if assignee:
            conditions.append(f"assignee = {assignee}")
        if issue_type:
            conditions.append(f'issuetype = "{issue_type}"')

        for key, value in kwargs.items():
            conditions.append(f'{key} = "{value}"')

        jql = " AND ".join(conditions) if conditions else "order by created DESC"
        logger.debug(f"Built JQL: {jql}")
        return jql

    def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> Dict:
        """
        Get a specific Jira issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)
            fields: Optional list of fields to retrieve

        Returns:
            Issue data
        """
        logger.debug(f"Fetching issue: {issue_key}")

        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        response = self._make_jira_request("GET", f"/rest/api/3/issue/{issue_key}", params=params)
        data = response.json()

        logger.info(f"Retrieved issue: {issue_key}")
        return data

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
        start_at: int = 0,
    ) -> Dict:
        """
        Search for issues using JQL.

        Args:
            jql: JQL query string
            max_results: Maximum number of results
            fields: Optional list of fields to retrieve
            start_at: Starting index for pagination

        Returns:
            Search results
        """
        logger.debug(f"Searching with JQL: {jql}")

        payload = {"jql": jql, "maxResults": max_results, "startAt": start_at}

        if fields:
            payload["fields"] = fields

        response = self._make_jira_request("POST", "/rest/api/3/search", json=payload)
        data = response.json()

        count = len(data.get("issues", []))
        total = data.get("total", 0)
        logger.info(f"Search returned {count} of {total} issues")

        return data

    def get_project_issue_types(self, project_key: str) -> List[Dict]:
        """
        Get available issue types for a project.

        Args:
            project_key: Project key

        Returns:
            List of available issue types
        """
        logger.debug(f"Fetching issue types for project: {project_key}")

        response = self._make_jira_request(
            "GET", f"/rest/api/3/issue/createmeta/{project_key}/issuetypes"
        )
        data = response.json()

        issue_types = data.get("issueTypes", [])
        logger.info(f"Found {len(issue_types)} issue types for {project_key}")

        return issue_types

    def get_create_metadata(self, project_key: str, issue_type_id: str) -> Dict:
        """
        Get field metadata for creating issues.

        Args:
            project_key: Project key
            issue_type_id: Issue type ID

        Returns:
            Field metadata including required fields
        """
        logger.debug(f"Fetching create metadata: {project_key}/{issue_type_id}")

        response = self._make_jira_request(
            "GET",
            f"/rest/api/3/issue/createmeta/{project_key}/issuetypes/{issue_type_id}",
        )
        data = response.json()

        logger.info(f"Retrieved metadata for {project_key}/{issue_type_id}")
        return data

    def get_creatable_issue_types(self, project_key: str) -> List[Dict]:
        """
        Get issue types that can be created in a project with basic info.

        Args:
            project_key: Project key

        Returns:
            List of issue types with metadata
        """
        logger.debug(f"Fetching creatable issue types for: {project_key}")

        response = self._make_jira_request(
            "GET",
            "/rest/api/3/issue/createmeta",
            params={"projectKeys": project_key, "expand": "projects.issuetypes.fields"},
        )
        data = response.json()

        issue_types = []
        for project in data.get("projects", []):
            for issuetype in project.get("issuetypes", []):
                # Get required fields
                fields = issuetype.get("fields", {})
                required_fields = [
                    {"key": key, "name": field.get("name", key)}
                    for key, field in fields.items()
                    if field.get("required", False)
                ]

                issue_types.append(
                    {
                        "id": issuetype["id"],
                        "name": issuetype["name"],
                        "description": issuetype.get("description", ""),
                        "subtask": issuetype.get("subtask", False),
                        "required_fields": required_fields,
                    }
                )

        logger.info(f"Found {len(issue_types)} creatable issue types")
        return issue_types

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        additional_fields: Optional[Dict] = None,
        rich_text: bool = False,
    ) -> Dict:
        """
        Create a new Jira issue.

        Args:
            project_key: Project key
            summary: Issue summary
            description: Issue description
            issue_type: Issue type (Task, Bug, Story, etc.)
            priority: Priority name
            assignee: Assignee account ID
            labels: List of labels
            additional_fields: Additional field values (custom fields, etc.)
            rich_text: Preserve formatting in description

        Returns:
            Created issue data
        """
        logger.debug(f"Creating {issue_type} in {project_key}: {summary}")

        fields = {
            "project": {"key": project_key},
            "summary": summary,
            "description": self._format_description(description, rich_text),
            "issuetype": {"name": issue_type},
        }

        if priority:
            fields["priority"] = {"name": priority}

        if assignee:
            fields["assignee"] = {"accountId": assignee}

        if labels:
            fields["labels"] = labels

        # Merge additional fields - this is key for custom fields
        if additional_fields:
            fields.update(additional_fields)

        payload = {"fields": fields}

        logger.debug(f"Issue creation payload: {json.dumps(payload, indent=2)}")

        try:
            response = self._make_jira_request("POST", "/rest/api/3/issue", json=payload)
            data = response.json()

            logger.debug(f"Create response: {json.dumps(data, indent=2)}")

            # Validate response
            if "key" not in data:
                error_msg = data.get("errorMessages", ["Unknown error"])
                logger.error(f"Issue creation failed: {error_msg}")
                raise ValueError(f"Issue creation failed: {error_msg}")

            issue_key = data.get("key")
            issue_url = f"{self.config.base_url}/browse/{issue_key}"

            logger.info(f"Created issue: {issue_key}")

            # Return enhanced response
            return {
                "success": True,
                "key": issue_key,
                "id": data.get("id"),
                "self": data.get("self"),
                "url": issue_url,
            }

        except Exception as e:
            logger.error(f"Failed to create issue. Payload: {json.dumps(payload, indent=2)}")
            logger.error(f"Error: {str(e)}")
            raise

    def create_issues_bulk(self, issues: List[Dict]) -> Dict:
        """
        Create multiple issues in a single API call.

        Args:
            issues: List of issue definitions

        Returns:
            Results of bulk creation
        """
        logger.debug(f"Creating {len(issues)} issues in bulk")

        # Format issues for bulk creation
        issue_updates = []
        for issue in issues:
            fields = {
                "project": {"key": issue["project_key"]},
                "summary": issue["summary"],
                "description": self._format_description(issue.get("description", "")),
                "issuetype": {"name": issue.get("issue_type", "Task")},
            }

            if issue.get("priority"):
                fields["priority"] = {"name": issue["priority"]}

            if issue.get("labels"):
                fields["labels"] = issue["labels"]

            # Handle story points (REQUIRED for all issue types)
            if "story_points" in issue and issue["story_points"] is not None:
                fields["customfield_10031"] = issue["story_points"]

            if issue.get("additional_fields"):
                fields.update(issue["additional_fields"])

            issue_updates.append({"fields": fields})

        payload = {"issueUpdates": issue_updates}

        try:
            response = self._make_jira_request("POST", "/rest/api/3/issue/bulk", json=payload)
            data = response.json()

            successful = len(data.get("issues", []))
            errors = data.get("errors", [])

            logger.info(f"Bulk created: {successful} successful, {len(errors)} failed")

            if errors:
                logger.warning(f"Bulk creation errors: {errors}")

            return data

        except Exception as e:
            logger.error(f"Bulk creation failed: {str(e)}")
            raise

    def update_issue(self, issue_key: str, fields: Dict) -> bool:
        """
        Update an existing Jira issue.

        Args:
            issue_key: Issue key
            fields: Fields to update

        Returns:
            Success status
        """
        logger.debug(f"Updating issue: {issue_key}")
        logger.debug(f"Update fields: {json.dumps(fields, indent=2)}")

        payload = {"fields": fields}

        try:
            self._make_jira_request("PUT", f"/rest/api/3/issue/{issue_key}", json=payload)
            logger.info(f"Updated issue: {issue_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to update issue {issue_key}: {str(e)}")
            raise

    def delete_issue(self, issue_key: str) -> bool:
        """
        Delete a Jira issue.

        Args:
            issue_key: Issue key

        Returns:
            Success status
        """
        logger.debug(f"Deleting issue: {issue_key}")

        self._make_jira_request("DELETE", f"/rest/api/3/issue/{issue_key}")

        logger.info(f"Deleted issue: {issue_key}")
        return True

    def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None,
        fields: Optional[Dict] = None,
    ) -> bool:
        """
        Transition an issue to a different status.

        Args:
            issue_key: Issue key
            transition_id: Transition ID
            comment: Optional comment
            fields: Optional field updates

        Returns:
            Success status
        """
        logger.debug(f"Transitioning {issue_key} with transition {transition_id}")

        payload = {"transition": {"id": transition_id}}

        if comment:
            payload["update"] = {"comment": [{"add": {"body": self._format_description(comment)}}]}

        if fields:
            payload["fields"] = fields

        logger.debug(f"Transition payload: {json.dumps(payload, indent=2)}")

        self._make_jira_request("POST", f"/rest/api/3/issue/{issue_key}/transitions", json=payload)

        logger.info(f"Transitioned issue: {issue_key}")
        return True

    def get_transitions(self, issue_key: str) -> List[Dict]:
        """
        Get available transitions for an issue.

        Args:
            issue_key: Issue key

        Returns:
            List of available transitions
        """
        logger.debug(f"Fetching transitions for: {issue_key}")

        response = self._make_jira_request("GET", f"/rest/api/3/issue/{issue_key}/transitions")
        data = response.json()

        transitions = data.get("transitions", [])
        logger.info(f"Found {len(transitions)} transitions for {issue_key}")

        return transitions

    def add_comment(self, issue_key: str, comment: str, rich_text: bool = False) -> Dict:
        """
        Add a comment to an issue.

        Args:
            issue_key: Issue key
            comment: Comment text
            rich_text: Preserve formatting

        Returns:
            Created comment data
        """
        logger.debug(f"Adding comment to: {issue_key}")

        payload = {"body": self._format_description(comment, rich_text)}

        response = self._make_jira_request(
            "POST", f"/rest/api/3/issue/{issue_key}/comment", json=payload
        )
        data = response.json()

        logger.info(f"Added comment to issue: {issue_key}")
        return data

    def get_comments(self, issue_key: str) -> List[Dict]:
        """
        Get all comments for an issue.

        Args:
            issue_key: Issue key

        Returns:
            List of comments
        """
        logger.debug(f"Fetching comments for: {issue_key}")

        response = self._make_jira_request("GET", f"/rest/api/3/issue/{issue_key}/comment")
        data = response.json()

        comments = data.get("comments", [])
        logger.info(f"Found {len(comments)} comments for {issue_key}")

        return comments

    def link_issues(
        self, inward_issue: str, outward_issue: str, link_type: str = "Relates"
    ) -> bool:
        """
        Create a link between two issues.

        Args:
            inward_issue: Inward issue key
            outward_issue: Outward issue key
            link_type: Link type name

        Returns:
            Success status
        """
        logger.debug(f"Linking {inward_issue} <-> {outward_issue} ({link_type})")

        payload = {
            "type": {"name": link_type},
            "inwardIssue": {"key": inward_issue},
            "outwardIssue": {"key": outward_issue},
        }

        self._make_jira_request("POST", "/rest/api/3/issueLink", json=payload)

        logger.info(f"Linked issues: {inward_issue} <-> {outward_issue}")
        return True

    def get_projects(self) -> List[Dict]:
        """
        Get all accessible projects.

        Returns:
            List of projects
        """
        logger.debug("Fetching projects")

        response = self._make_jira_request("GET", "/rest/api/3/project")
        projects = response.json()

        logger.info(f"Retrieved {len(projects)} projects")
        return projects

    def assign_issue(self, issue_key: str, account_id: str) -> bool:
        """
        Assign an issue to a user.

        Args:
            issue_key: Issue key
            account_id: User account ID

        Returns:
            Success status
        """
        logger.debug(f"Assigning {issue_key} to {account_id}")

        payload = {"accountId": account_id}

        self._make_jira_request("PUT", f"/rest/api/3/issue/{issue_key}/assignee", json=payload)

        logger.info(f"Assigned issue {issue_key}")
        return True

    def get_issue_watchers(self, issue_key: str) -> Dict:
        """
        Get watchers for an issue.

        Args:
            issue_key: Issue key

        Returns:
            Watcher information
        """
        logger.debug(f"Fetching watchers for: {issue_key}")

        response = self._make_jira_request("GET", f"/rest/api/3/issue/{issue_key}/watchers")
        data = response.json()

        logger.info(f"Retrieved watchers for {issue_key}")
        return data

    def add_watcher(self, issue_key: str, account_id: str) -> bool:
        """
        Add a watcher to an issue.

        Args:
            issue_key: Issue key
            account_id: User account ID

        Returns:
            Success status
        """
        logger.debug(f"Adding watcher to {issue_key}")

        self._make_jira_request("POST", f"/rest/api/3/issue/{issue_key}/watchers", json=account_id)

        logger.info(f"Added watcher to {issue_key}")
        return True

    # Sprint and Board Management Methods

    def get_boards(self, project_key: Optional[str] = None, max_results: int = 50) -> List[Dict]:
        """
        Get boards, optionally filtered by project.

        Args:
            project_key: Optional project key filter
            max_results: Maximum number of results (default: 50)

        Returns:
            List of boards
        """
        if not self.agile_api_available:
            raise ValueError("Agile API is not available for this Jira instance")

        logger.debug(f"Fetching boards for project: {project_key}")

        params = {"maxResults": max_results, "startAt": 0}
        if project_key:
            params["projectKeyOrId"] = project_key

        response = self._make_jira_request("GET", "/rest/agile/1.0/board", params=params)
        data = response.json()

        boards = data.get("values", [])
        total = data.get("total", len(boards))
        logger.info(f"Found {len(boards)} boards (total: {total})")

        return boards

    def get_project_board(self, project_key: str) -> Optional[Dict]:
        """
        Get the primary board for a project.

        Args:
            project_key: Project key

        Returns:
            Board data or None if not found
        """
        logger.debug(f"Finding board for project: {project_key}")

        boards = self.get_boards(project_key)

        if boards:
            # Return the first board (usually the main board)
            logger.info(f"Found board {boards[0]['id']} for project {project_key}")
            return boards[0]

        logger.warning(f"No board found for project {project_key}")
        return None

    def get_board_sprints(
        self, board_id: str, state: str = "active", max_results: int = 50
    ) -> List[Dict]:
        """
        Get sprints for a board.

        Args:
            board_id: Board ID
            state: Sprint state (active, future, closed)
            max_results: Maximum number of results (default: 50)

        Returns:
            List of sprints
        """
        if not self.agile_api_available:
            raise ValueError("Agile API is not available for this Jira instance")

        logger.debug(f"Fetching {state} sprints for board: {board_id}")

        response = self._make_jira_request(
            "GET",
            f"/rest/agile/1.0/board/{board_id}/sprint",
            params={"state": state, "maxResults": max_results},
        )
        data = response.json()

        sprints = data.get("values", [])
        logger.info(f"Found {len(sprints)} {state} sprints")

        return sprints

    def get_active_sprints(self, board_id: str) -> List[Dict]:
        """
        Get active sprints for a board.

        Args:
            board_id: Board ID

        Returns:
            List of active sprints
        """
        return self.get_board_sprints(board_id, "active")

    def add_issues_to_sprint(self, sprint_id: int, issue_keys: List[str]) -> bool:
        """
        Add issues to a sprint using the Agile API.

        Args:
            sprint_id: Sprint ID
            issue_keys: List of issue keys to add

        Returns:
            Success status
        """
        if not self.agile_api_available:
            raise ValueError("Agile API is not available for this Jira instance")

        logger.debug(f"Adding {len(issue_keys)} issues to sprint {sprint_id}")

        payload = {"issues": issue_keys}

        self._make_jira_request("POST", f"/rest/agile/1.0/sprint/{sprint_id}/issue", json=payload)

        logger.info(f"Added issues to sprint {sprint_id}")
        return True

    def add_issue_to_active_sprint(self, issue_key: str, project_key: str) -> Dict:
        """
        Add an issue to the active sprint of its project.

        Args:
            issue_key: Issue key
            project_key: Project key

        Returns:
            Result with sprint information
        """
        if not self.agile_api_available:
            raise ValueError("Agile API is not available for this Jira instance")

        logger.debug(f"Adding {issue_key} to active sprint in {project_key}")

        # Get board
        board = self.get_project_board(project_key)
        if not board:
            raise ValueError(f"No board found for project {project_key}")

        # Get active sprints
        sprints = self.get_active_sprints(str(board["id"]))
        if not sprints:
            raise ValueError(f"No active sprint found for board {board['id']}")

        # Add to first active sprint
        sprint = sprints[0]
        self.add_issues_to_sprint(sprint["id"], [issue_key])

        logger.info(f"Added {issue_key} to sprint {sprint['name']}")

        return {
            "success": True,
            "sprint_id": sprint["id"],
            "sprint_name": sprint["name"],
            "board_id": board["id"],
            "board_name": board["name"],
        }


# Initialize client
try:
    config = JiraConfig()
    validate_config(config, logger)

    log_server_startup(
        logger,
        "Jira Server",
        {
            "Base URL": config.base_url,
            "Email": config.email,
            "Project Key": config.project_key or "Not set",
            "Timeout": config.timeout,
            "Max Retries": config.max_retries,
            "Rate Limit Delay": config.rate_limit_delay,
        },
    )

    jira_client = JiraClient(config)

except ConfigurationError as e:
    logger.critical(f"Configuration error: {e}")
    jira_client = None
except Exception as e:
    logger.critical(f"Failed to initialize Jira client: {e}", exc_info=True)
    jira_client = None


# MCP Tools
@mcp.tool()
@handle_errors(logger)
def jira_get_issue(issue_key: str, fields: Optional[str] = None) -> str:
    """
    Get detailed information about a Jira issue.

    Args:
        issue_key: Issue key (e.g., PROJ-123)
        fields: JSON array of fields to retrieve

    Returns:
        JSON string with issue data
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    fields_list = json.loads(fields) if fields else None
    issue = jira_client.get_issue(issue_key, fields_list)
    return json.dumps(issue, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_search_issues(
    jql: str, max_results: int = 50, fields: Optional[str] = None, start_at: int = 0
) -> str:
    """
    Search for Jira issues using JQL.

    Args:
        jql: JQL query string
        max_results: Maximum number of results (default: 50)
        fields: JSON array of fields to retrieve
        start_at: Starting index for pagination (default: 0)

    Returns:
        JSON string with search results
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    fields_list = json.loads(fields) if fields else None
    results = jira_client.search_issues(jql, max_results, fields_list, start_at)
    return json.dumps(results, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_build_jql(
    project: Optional[str] = None,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    issue_type: Optional[str] = None,
) -> str:
    """
    Build a JQL query from common parameters.

    Args:
        project: Project key
        status: Status name (e.g., "Open", "In Progress", "Done")
        assignee: Assignee (use "currentUser()" for current user)
        issue_type: Issue type name (e.g., "Bug", "Task", "Story")

    Returns:
        JSON string with built JQL query
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    jql = jira_client.build_jql(project, status, assignee, issue_type)
    return json.dumps({"jql": jql}, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_get_project_issue_types(project_key: str) -> str:
    """
    Get available issue types for a Jira project.

    Args:
        project_key: Project key (e.g., "CGV2")

    Returns:
        JSON string with available issue types and their IDs
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    issue_types = jira_client.get_project_issue_types(project_key)
    return json.dumps(issue_types, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_get_creatable_issue_types(project_key: str) -> str:
    """
    Get issue types that can be created in a project with their required fields.

    Args:
        project_key: Project key (e.g., "CGV2")

    Returns:
        JSON string with creatable issue types and required fields
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    issue_types = jira_client.get_creatable_issue_types(project_key)
    return json.dumps(issue_types, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_get_create_metadata(project_key: str, issue_type_id: str) -> str:
    """
    Get field metadata for creating issues in a project.

    Args:
        project_key: Project key
        issue_type_id: Issue type ID (get from jira_get_project_issue_types)

    Returns:
        JSON string with field metadata including required fields
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    metadata = jira_client.get_create_metadata(project_key, issue_type_id)
    return json.dumps(metadata, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_check_story_points_requirement(project_key: str, issue_type: str = "Story") -> str:
    """
    Check if story points are required for a specific issue type in a project.

    Args:
        project_key: Project key (e.g., "CGV2")
        issue_type: Issue type to check (default: "Story")

    Returns:
        JSON string with story points requirement information
    """
    if not jira_client:
        return json.dumps(
            {
                "error": "Jira client not initialized",
                "type": "configuration_error",
                "suggestion": "Check Jira configuration and credentials.",
            }
        )

    try:
        # Get issue types for the project
        issue_types = jira_client.get_project_issue_types(project_key)

        # Find the specific issue type
        target_issue_type = None
        for it in issue_types:
            if it.get("name", "").lower() == issue_type.lower():
                target_issue_type = it
                break

        if not target_issue_type:
            return json.dumps(
                {
                    "error": f"Issue type '{issue_type}' not found in project '{project_key}'",
                    "type": "not_found_error",
                    "suggestion": f"Use jira_get_project_issue_types to see available issue types for project '{project_key}'",
                    "available_issue_types": [it.get("name") for it in issue_types],
                }
            )

        # Get metadata for this issue type
        metadata = jira_client.get_create_metadata(project_key, target_issue_type["id"])

        # Check for story points fields
        story_points_fields = []
        required_fields = []

        if "projects" in metadata and len(metadata["projects"]) > 0:
            project_data = metadata["projects"][0]
            if "issuetypes" in project_data:
                for it_data in project_data["issuetypes"]:
                    if it_data.get("id") == target_issue_type["id"]:
                        if "fields" in it_data:
                            for field_id, field_data in it_data["fields"].items():
                                field_name = field_data.get("name", "").lower()
                                is_required = field_data.get("required", False)

                                # Check if this looks like a story points field
                                if any(
                                    keyword in field_name
                                    for keyword in [
                                        "story point",
                                        "point",
                                        "estimate",
                                        "effort",
                                    ]
                                ):
                                    story_points_fields.append(
                                        {
                                            "field_id": field_id,
                                            "field_name": field_data.get("name"),
                                            "required": is_required,
                                            "field_type": field_data.get("schema", {}).get("type"),
                                        }
                                    )

                                if is_required:
                                    required_fields.append(
                                        {
                                            "field_id": field_id,
                                            "field_name": field_data.get("name"),
                                            "field_type": field_data.get("schema", {}).get("type"),
                                        }
                                    )

        return json.dumps(
            {
                "project_key": project_key,
                "issue_type": issue_type,
                "story_points_required": any(field["required"] for field in story_points_fields),
                "story_points_fields": story_points_fields,
                "all_required_fields": required_fields,
                "suggestion": "Use the story_points parameter when creating issues if story points are required.",
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {
                "error": f"Failed to check story points requirement: {str(e)}",
                "type": "check_error",
                "suggestion": "Verify the project key and issue type are correct.",
            }
        )


@mcp.tool()
@handle_errors(logger)
def jira_create_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    labels: Optional[str] = None,
    story_points: Optional[int] = None,
    additional_fields: Optional[dict] = None,
    rich_text: bool = False,
) -> str:
    """
    Create a new Jira issue with improved story points handling.

    Args:
        project_key: Project key (e.g., "CGV2")
        summary: Issue summary/title
        description: Issue description
        issue_type: Issue type (Task, Bug, Story, Epic, etc.)
        priority: Priority name (High, Medium, Low, etc.)
        assignee: Assignee account ID
        labels: JSON array of labels
        story_points: Story points value (1-100, typically 1, 2, 3, 5, 8, 13, 21) - REQUIRED for all issue types
        additional_fields: Dict with custom field values (e.g., {"customfield_10031": 1})
        rich_text: Preserve paragraph formatting in description

    Returns:
        JSON string with created issue including issue key and URL

    Examples:
        Basic issue with story points:
        jira_create_issue("CGV2", "Bug in login", "Users cannot login", story_points=2)

        Full example:
        jira_create_issue("CGV2", "Test Issue", "Testing", "Task", "Low",
                          labels='["bug", "urgent"]', story_points=5)
    """
    if not jira_client:
        return json.dumps(
            {
                "error": "Jira client not initialized",
                "type": "configuration_error",
                "suggestion": "Check Jira configuration and credentials.",
            }
        )

    # Story points are REQUIRED for all issue types in this project
    if story_points is None:
        return json.dumps(
            {
                "error": f"Story points are required for all issue types in this project. Issue type '{issue_type}' requires story points.",
                "type": "required_field_error",
                "suggestion": "Provide story_points parameter (1-100). Common values: 1, 2, 3, 5, 8, 13, 21. Story points are mandatory for all issue types in this Jira project.",
                "story_points_required": True,
                "issue_type": issue_type,
            }
        )

    # Validate story points if provided
    if not isinstance(story_points, int) or story_points < 1 or story_points > 100:
        return json.dumps(
            {
                "error": f"Invalid story points value: {story_points}. Must be an integer between 1 and 100.",
                "type": "validation_error",
                "suggestion": "Use common story point values like 1, 2, 3, 5, 8, 13, 21, or provide a reasonable estimate.",
            }
        )

    # Parse labels
    labels_list = None
    if labels:
        try:
            labels_list = json.loads(labels)
            if not isinstance(labels_list, list):
                return json.dumps(
                    {
                        "error": f"Labels must be a JSON array, got: {type(labels_list).__name__}",
                        "type": "validation_error",
                        "suggestion": 'Provide labels as a JSON array, e.g., \'["bug", "urgent"]\'',
                    }
                )
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "error": f"Invalid JSON format for labels: {e}",
                    "type": "validation_error",
                    "suggestion": 'Provide labels as a JSON array, e.g., \'["bug", "urgent"]\'',
                }
            )

    # Prepare additional fields with story points
    final_additional_fields = additional_fields or {}

    # Add story points to additional fields (REQUIRED)
    story_points_fields = [
        "customfield_10031",  # Common Atlassian story points field
        "customfield_10002",  # Another common field
        "customfield_10003",  # Alternative field
    ]

    # Use the first available field or default to the most common one
    story_points_field = story_points_fields[0]
    final_additional_fields[story_points_field] = story_points

    try:
        issue = jira_client.create_issue(
            project_key,
            summary,
            description,
            issue_type,
            priority,
            assignee,
            labels_list,
            final_additional_fields,
            rich_text,
        )

        # Add helpful information to the response
        response_data = issue
        response_data["story_points"] = story_points
        response_data["story_points_field"] = story_points_field
        response_data["story_points_required"] = True

        return json.dumps(response_data, indent=2)

    except Exception as e:
        error_msg = str(e)

        # Check for common Jira errors and provide helpful suggestions
        if "required field" in error_msg.lower():
            if "story points" in error_msg.lower() or "customfield" in error_msg.lower():
                return json.dumps(
                    {
                        "error": f"Story points are required for this issue type: {error_msg}",
                        "type": "required_field_error",
                        "suggestion": "Provide story_points parameter (1-100). Story points are mandatory for all issue types in this Jira project.",
                        "story_points_required": True,
                    }
                )
            else:
                return json.dumps(
                    {
                        "error": f"Required field missing: {error_msg}",
                        "type": "required_field_error",
                        "suggestion": "Check the issue type requirements and provide all mandatory fields.",
                    }
                )
        elif "invalid" in error_msg.lower():
            return json.dumps(
                {
                    "error": f"Invalid data provided: {error_msg}",
                    "type": "validation_error",
                    "suggestion": "Check the provided values and ensure they match the expected format.",
                }
            )
        else:
            return json.dumps(
                {
                    "error": f"Failed to create issue: {error_msg}",
                    "type": "creation_error",
                    "suggestion": "Check the project key, issue type, and required fields.",
                }
            )


@mcp.tool()
@handle_errors(logger)
def jira_create_issues_bulk(issues: str) -> str:
    """
    Create multiple Jira issues in a single API call.

    Args:
        issues: JSON array of issue objects, each with:
               - project_key, summary, description (required)
               - issue_type, priority, labels, story_points (required), additional_fields (optional)

    Returns:
        JSON string with bulk creation results
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    try:
        issues_list = json.loads(issues)

        # Validate that all issues have story points
        for i, issue in enumerate(issues_list):
            if "story_points" not in issue or issue["story_points"] is None:
                return json.dumps(
                    {
                        "error": f"Issue {i+1} is missing required story_points field",
                        "type": "validation_error",
                        "suggestion": "All issues must include story_points parameter (1-100). Story points are mandatory for all issue types in this Jira project.",
                        "story_points_required": True,
                    }
                )

            # Validate story points value
            story_points = issue["story_points"]
            if not isinstance(story_points, int) or story_points < 1 or story_points > 100:
                return json.dumps(
                    {
                        "error": f"Issue {i+1} has invalid story_points value: {story_points}. Must be an integer between 1 and 100.",
                        "type": "validation_error",
                        "suggestion": "Use common story point values like 1, 2, 3, 5, 8, 13, 21, or provide a reasonable estimate.",
                    }
                )

        result = jira_client.create_issues_bulk(issues_list)
        return json.dumps(result, indent=2)

    except json.JSONDecodeError as e:
        return json.dumps(
            {
                "error": f"Invalid JSON format for issues: {e}",
                "type": "validation_error",
                "suggestion": "Provide issues as a JSON array with proper format.",
            }
        )


@mcp.tool()
@handle_errors(logger)
def jira_update_issue(issue_key: str, fields: str) -> str:
    """
    Update an existing Jira issue.

    Args:
        issue_key: Issue key (e.g., "CGV2-123")
        fields: JSON object with fields to update

    Returns:
        JSON string with success status
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    fields_dict = json.loads(fields)
    result = jira_client.update_issue(issue_key, fields_dict)
    return json.dumps({"success": result})


@mcp.tool()
@handle_errors(logger)
def jira_delete_issue(issue_key: str) -> str:
    """
    Delete a Jira issue.

    Args:
        issue_key: Issue key (e.g., "CGV2-123")

    Returns:
        JSON string with success status
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    result = jira_client.delete_issue(issue_key)
    return json.dumps({"success": result})


@mcp.tool()
@handle_errors(logger)
def jira_transition_issue(
    issue_key: str,
    transition_id: str,
    comment: Optional[str] = None,
    fields: Optional[str] = None,
) -> str:
    """
    Transition a Jira issue to a different status.

    Args:
        issue_key: Issue key
        transition_id: Transition ID (get from jira_get_transitions)
        comment: Optional comment to add during transition
        fields: JSON object with optional field updates

    Returns:
        JSON string with success status
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    fields_dict = json.loads(fields) if fields else None
    result = jira_client.transition_issue(issue_key, transition_id, comment, fields_dict)
    return json.dumps({"success": result})


@mcp.tool()
@handle_errors(logger)
def jira_get_transitions(issue_key: str) -> str:
    """
    Get available status transitions for an issue.

    Args:
        issue_key: Issue key

    Returns:
        JSON string with available transitions and their IDs
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    transitions = jira_client.get_transitions(issue_key)
    return json.dumps(transitions, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_add_comment(issue_key: str, comment: str, rich_text: bool = False) -> str:
    """
    Add a comment to a Jira issue.

    Args:
        issue_key: Issue key
        comment: Comment text
        rich_text: Preserve paragraph formatting

    Returns:
        JSON string with created comment
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    result = jira_client.add_comment(issue_key, comment, rich_text)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_get_comments(issue_key: str) -> str:
    """
    Get all comments for a Jira issue.

    Args:
        issue_key: Issue key

    Returns:
        JSON string with list of comments
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    comments = jira_client.get_comments(issue_key)
    return json.dumps(comments, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_link_issues(inward_issue: str, outward_issue: str, link_type: str = "Relates") -> str:
    """
    Create a link between two Jira issues.

    Args:
        inward_issue: Inward issue key
        outward_issue: Outward issue key
        link_type: Link type (Relates, Blocks, Clones, Duplicates)

    Returns:
        JSON string with success status
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    result = jira_client.link_issues(inward_issue, outward_issue, link_type)
    return json.dumps({"success": result})


@mcp.tool()
@handle_errors(logger)
def jira_get_projects() -> str:
    """
    Get all accessible Jira projects.

    Returns:
        JSON string with list of projects
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    projects = jira_client.get_projects()
    return json.dumps(projects, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_assign_issue(issue_key: str, account_id: str) -> str:
    """
    Assign a Jira issue to a user.

    Args:
        issue_key: Issue key
        account_id: User account ID

    Returns:
        JSON string with success status
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    result = jira_client.assign_issue(issue_key, account_id)
    return json.dumps({"success": result})


@mcp.tool()
@handle_errors(logger)
def jira_get_watchers(issue_key: str) -> str:
    """
    Get watchers for a Jira issue.

    Args:
        issue_key: Issue key

    Returns:
        JSON string with watcher information
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    watchers = jira_client.get_issue_watchers(issue_key)
    return json.dumps(watchers, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_add_watcher(issue_key: str, account_id: str) -> str:
    """
    Add a watcher to a Jira issue.

    Args:
        issue_key: Issue key
        account_id: User account ID

    Returns:
        JSON string with success status
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    result = jira_client.add_watcher(issue_key, account_id)
    return json.dumps({"success": result})


# Sprint and Board Management Tools


@mcp.tool()
@handle_errors(logger)
def jira_get_boards(project_key: Optional[str] = None) -> str:
    """
    Get Jira boards, optionally filtered by project.

    Args:
        project_key: Optional project key to filter boards

    Returns:
        JSON string with list of boards and their IDs
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    boards = jira_client.get_boards(project_key)
    return json.dumps(boards, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_get_active_sprints(board_id: str) -> str:
    """
    Get active sprints for a Jira board.

    Args:
        board_id: Board ID (get from jira_get_boards)

    Returns:
        JSON string with active sprints including sprint IDs and names
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    sprints = jira_client.get_active_sprints(board_id)
    return json.dumps(sprints, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_add_to_sprint(sprint_id: int, issue_keys: str) -> str:
    """
    Add issues to a sprint.

    Args:
        sprint_id: Sprint ID (get from jira_get_active_sprints)
        issue_keys: JSON array of issue keys (e.g., ["CGV2-880", "CGV2-881"])

    Returns:
        JSON string with success status
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    keys = json.loads(issue_keys)
    result = jira_client.add_issues_to_sprint(sprint_id, keys)
    return json.dumps({"success": result})


@mcp.tool()
@handle_errors(logger)
def jira_add_issue_to_active_sprint(issue_key: str, project_key: str) -> str:
    """
    Add an issue to the active sprint (automatic sprint detection).

    Args:
        issue_key: Issue key (e.g., "CGV2-880")
        project_key: Project key (e.g., "CGV2")

    Returns:
        JSON string with success status and sprint details

    Example:
        jira_add_issue_to_active_sprint("CGV2-880", "CGV2")
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})

    result = jira_client.add_issue_to_active_sprint(issue_key, project_key)
    return json.dumps(result, indent=2)


def main() -> None:
    """Main entry point for Frappe MCP Server."""
    try:
        if not jira_client:
            logger.error("Server starting with errors - some features unavailable")

        logger.info("Starting Frappe MCP Server...")
        mcp.run()

    except KeyboardInterrupt:
        log_server_shutdown(logger, "Frappe Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if jira_client:
            jira_client.close()


if __name__ == "__main__":
    main()
