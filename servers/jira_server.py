#!/usr/bin/env python3
"""
Jira MCP Server - Production Ready
Provides integration with Jira via REST API
"""
import json
import sys
from pathlib import Path
from typing import Optional, List, Dict
from requests.auth import HTTPBasicAuth

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.logging_config import setup_logging, log_server_startup, log_server_shutdown
from servers.config import load_env_file, JiraConfig, validate_config, ConfigurationError
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
            logger=logger
        )
        
        self.config = config
        self.auth = HTTPBasicAuth(config.email, config.api_token)
        
        # Set headers
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Verify connection
        self._verify_connection()
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
    
    def _format_description(self, description: str) -> Dict:
        """Format description for Atlassian Document Format."""
        return {
            'type': 'doc',
            'version': 1,
            'content': [
                {
                    'type': 'paragraph',
                    'content': [
                        {
                            'type': 'text',
                            'text': description
                        }
                    ]
                }
            ]
        }
    
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
            params['fields'] = ','.join(fields)
        
        response = self.get(f"/rest/api/3/issue/{issue_key}", params=params, auth=self.auth)
        data = response.json()
        
        logger.info(f"Retrieved issue: {issue_key}")
        return data
    
    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
        start_at: int = 0
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
        
        payload = {
            'jql': jql,
            'maxResults': max_results,
            'startAt': start_at
        }
        
        if fields:
            payload['fields'] = fields
        
        response = self.post("/rest/api/3/search", json=payload, auth=self.auth)
        data = response.json()
        
        count = len(data.get('issues', []))
        total = data.get('total', 0)
        logger.info(f"Search returned {count} of {total} issues")
        
        return data
    
    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Task",
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        custom_fields: Optional[Dict] = None
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
            custom_fields: Custom field values
            
        Returns:
            Created issue data
        """
        logger.debug(f"Creating {issue_type} in {project_key}: {summary}")
        
        fields = {
            'project': {'key': project_key},
            'summary': summary,
            'description': self._format_description(description),
            'issuetype': {'name': issue_type}
        }
        
        if priority:
            fields['priority'] = {'name': priority}
        
        if assignee:
            fields['assignee'] = {'accountId': assignee}
        
        if labels:
            fields['labels'] = labels
        
        if custom_fields:
            fields.update(custom_fields)
        
        payload = {'fields': fields}
        
        response = self.post("/rest/api/3/issue", json=payload, auth=self.auth)
        data = response.json()
        
        issue_key = data.get('key', 'Unknown')
        logger.info(f"Created issue: {issue_key}")
        
        return data
    
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
        
        payload = {'fields': fields}
        response = self.put(f"/rest/api/3/issue/{issue_key}", json=payload, auth=self.auth)
        
        logger.info(f"Updated issue: {issue_key}")
        return True
    
    def delete_issue(self, issue_key: str) -> bool:
        """
        Delete a Jira issue.
        
        Args:
            issue_key: Issue key
            
        Returns:
            Success status
        """
        logger.debug(f"Deleting issue: {issue_key}")
        
        response = self.delete(f"/rest/api/3/issue/{issue_key}", auth=self.auth)
        
        logger.info(f"Deleted issue: {issue_key}")
        return True
    
    def transition_issue(
        self,
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None,
        fields: Optional[Dict] = None
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
        
        payload = {
            'transition': {'id': transition_id}
        }
        
        if comment:
            payload['update'] = {
                'comment': [
                    {
                        'add': self._format_description(comment)
                    }
                ]
            }
        
        if fields:
            payload['fields'] = fields
        
        response = self.post(
            f"/rest/api/3/issue/{issue_key}/transitions",
            json=payload,
            auth=self.auth
        )
        
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
        
        response = self.get(f"/rest/api/3/issue/{issue_key}/transitions", auth=self.auth)
        data = response.json()
        
        transitions = data.get('transitions', [])
        logger.info(f"Found {len(transitions)} transitions for {issue_key}")
        
        return transitions
    
    def add_comment(self, issue_key: str, comment: str) -> Dict:
        """
        Add a comment to an issue.
        
        Args:
            issue_key: Issue key
            comment: Comment text
            
        Returns:
            Created comment data
        """
        logger.debug(f"Adding comment to: {issue_key}")
        
        payload = {
            'body': self._format_description(comment)
        }
        
        response = self.post(
            f"/rest/api/3/issue/{issue_key}/comment",
            json=payload,
            auth=self.auth
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
        
        response = self.get(f"/rest/api/3/issue/{issue_key}/comment", auth=self.auth)
        data = response.json()
        
        comments = data.get('comments', [])
        logger.info(f"Found {len(comments)} comments for {issue_key}")
        
        return comments
    
    def link_issues(
        self,
        inward_issue: str,
        outward_issue: str,
        link_type: str = "Relates"
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
            'type': {'name': link_type},
            'inwardIssue': {'key': inward_issue},
            'outwardIssue': {'key': outward_issue}
        }
        
        response = self.post("/rest/api/3/issueLink", json=payload, auth=self.auth)
        
        logger.info(f"Linked issues: {inward_issue} <-> {outward_issue}")
        return True
    
    def get_projects(self) -> List[Dict]:
        """
        Get all accessible projects.
        
        Returns:
            List of projects
        """
        logger.debug("Fetching projects")
        
        response = self.get("/rest/api/3/project", auth=self.auth)
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
        
        payload = {
            'accountId': account_id
        }
        
        response = self.put(
            f"/rest/api/3/issue/{issue_key}/assignee",
            json=payload,
            auth=self.auth
        )
        
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
        
        response = self.get(f"/rest/api/3/issue/{issue_key}/watchers", auth=self.auth)
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
        
        response = self.post(
            f"/rest/api/3/issue/{issue_key}/watchers",
            json=account_id,
            auth=self.auth
        )
        
        logger.info(f"Added watcher to {issue_key}")
        return True


# Initialize client
try:
    config = JiraConfig()
    validate_config(config, logger)
    
    log_server_startup(logger, "Jira Server", {
        "Base URL": config.base_url,
        "Email": config.email,
        "Project Key": config.project_key or "Not set",
        "Timeout": config.timeout,
        "Max Retries": config.max_retries
    })
    
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
    jql: str,
    max_results: int = 50,
    fields: Optional[str] = None,
    start_at: int = 0
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
def jira_create_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str = "Task",
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    labels: Optional[str] = None,
    custom_fields: Optional[str] = None
) -> str:
    """
    Create a new Jira issue.
    
    Args:
        project_key: Project key
        summary: Issue summary
        description: Issue description
        issue_type: Issue type (Task, Bug, Story, etc.)
        priority: Priority name
        assignee: Assignee account ID
        labels: JSON array of labels
        custom_fields: JSON object with custom field values
        
    Returns:
        JSON string with created issue
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})
    
    labels_list = json.loads(labels) if labels else None
    custom_dict = json.loads(custom_fields) if custom_fields else None
    
    issue = jira_client.create_issue(
        project_key, summary, description, issue_type,
        priority, assignee, labels_list, custom_dict
    )
    return json.dumps(issue, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_update_issue(issue_key: str, fields: str) -> str:
    """
    Update an existing Jira issue.
    
    Args:
        issue_key: Issue key
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
        issue_key: Issue key
        
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
    fields: Optional[str] = None
) -> str:
    """
    Transition a Jira issue to a different status.
    
    Args:
        issue_key: Issue key
        transition_id: Transition ID
        comment: Optional comment
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
        JSON string with available transitions
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})
    
    transitions = jira_client.get_transitions(issue_key)
    return json.dumps(transitions, indent=2)


@mcp.tool()
@handle_errors(logger)
def jira_add_comment(issue_key: str, comment: str) -> str:
    """
    Add a comment to a Jira issue.
    
    Args:
        issue_key: Issue key
        comment: Comment text
        
    Returns:
        JSON string with created comment
    """
    if not jira_client:
        return json.dumps({"error": "Jira client not initialized"})
    
    result = jira_client.add_comment(issue_key, comment)
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
def jira_link_issues(
    inward_issue: str,
    outward_issue: str,
    link_type: str = "Relates"
) -> str:
    """
    Create a link between two Jira issues.
    
    Args:
        inward_issue: Inward issue key
        outward_issue: Outward issue key
        link_type: Link type name (Relates, Blocks, Clones, Duplicates)
        
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


if __name__ == "__main__":
    try:
        if not jira_client:
            logger.error("Server starting with errors - some features unavailable")
        
        logger.info("Starting Jira MCP Server...")
        mcp.run()
        
    except KeyboardInterrupt:
        log_server_shutdown(logger, "Jira Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if jira_client:
            jira_client.close()