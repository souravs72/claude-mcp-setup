#!/usr/bin/env python3
import json
import logging
import os
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
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

mcp = FastMCP("Jira Integration Server")

class JiraClient:
    def __init__(self):
        self.base_url = os.environ.get('JIRA_BASE_URL', '').rstrip('/')
        self.email = os.environ.get('JIRA_EMAIL')
        self.api_token = os.environ.get('JIRA_API_TOKEN')
        self.project_key = os.environ.get('JIRA_PROJECT_KEY')
        
        if not all([self.base_url, self.email, self.api_token]):
            logger.error("Jira credentials not properly configured")
            logger.info(f"JIRA_BASE_URL: {'✓' if self.base_url else '✗'}")
            logger.info(f"JIRA_EMAIL: {'✓' if self.email else '✗'}")
            logger.info(f"JIRA_API_TOKEN: {'✓' if self.api_token else '✗'}")
            return
        
        self.auth = HTTPBasicAuth(self.email, self.api_token)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        logger.info("Jira client initialized successfully")
    
    def get_issue(self, issue_key: str) -> dict:
        """Get a specific Jira issue"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        response = requests.get(url, headers=self.headers, auth=self.auth)
        response.raise_for_status()
        return response.json()
    
    def search_issues(self, jql: str, max_results: int = 50, fields: list[str] | None = None) -> dict:
        """Search for issues using JQL"""
        url = f"{self.base_url}/rest/api/3/search"
        
        payload = {
            'jql': jql,
            'maxResults': max_results
        }
        
        if fields:
            payload['fields'] = fields
        
        response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
        response.raise_for_status()
        return response.json()
    
    def create_issue(self, project_key: str, summary: str, description: str,
                    issue_type: str = "Task", priority: str | None = None, 
                    assignee: str | None = None, labels: list[str] | None = None,
                    custom_fields: dict | None = None) -> dict:
        """Create a new Jira issue"""
        url = f"{self.base_url}/rest/api/3/issue"
        
        fields = {
            'project': {'key': project_key},
            'summary': summary,
            'description': {
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
            },
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
        
        response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
        response.raise_for_status()
        return response.json()
    
    def update_issue(self, issue_key: str, fields: dict) -> bool:
        """Update an existing Jira issue"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        payload = {'fields': fields}
        response = requests.put(url, headers=self.headers, auth=self.auth, json=payload)
        response.raise_for_status()
        return True
    
    def transition_issue(self, issue_key: str, transition_id: str, 
                        comment: str | None = None) -> bool:
        """Transition an issue to a different status"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        
        payload = {
            'transition': {'id': transition_id}
        }
        
        if comment:
            payload['update'] = {
                'comment': [
                    {
                        'add': {
                            'body': {
                                'type': 'doc',
                                'version': 1,
                                'content': [
                                    {
                                        'type': 'paragraph',
                                        'content': [
                                            {
                                                'type': 'text',
                                                'text': comment
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    }
                ]
            }
        
        response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
        response.raise_for_status()
        return True
    
    def get_transitions(self, issue_key: str) -> list[dict]:
        """Get available transitions for an issue"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions"
        response = requests.get(url, headers=self.headers, auth=self.auth)
        response.raise_for_status()
        return response.json().get('transitions', [])
    
    def add_comment(self, issue_key: str, comment: str) -> dict:
        """Add a comment to an issue"""
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}/comment"
        
        payload = {
            'body': {
                'type': 'doc',
                'version': 1,
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {
                                'type': 'text',
                                'text': comment
                            }
                        ]
                    }
                ]
            }
        }
        
        response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
        response.raise_for_status()
        return response.json()
    
    def link_issues(self, inward_issue: str, outward_issue: str, 
                   link_type: str = "Relates") -> bool:
        """Create a link between two issues"""
        url = f"{self.base_url}/rest/api/3/issueLink"
        
        payload = {
            'type': {'name': link_type},
            'inwardIssue': {'key': inward_issue},
            'outwardIssue': {'key': outward_issue}
        }
        
        response = requests.post(url, headers=self.headers, auth=self.auth, json=payload)
        response.raise_for_status()
        return True
    
    def get_projects(self) -> list[dict]:
        """Get all accessible projects"""
        url = f"{self.base_url}/rest/api/3/project"
        response = requests.get(url, headers=self.headers, auth=self.auth)
        response.raise_for_status()
        return response.json()

jira_client = JiraClient()

@mcp.tool("jira_get_issue")
def jira_get_issue(issue_key: str) -> str:
    """Get detailed information about a Jira issue"""
    try:
        issue = jira_client.get_issue(issue_key)
        return json.dumps(issue, indent=2)
    except Exception as e:
        logger.error(f"Jira get issue error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("jira_search_issues")
def jira_search_issues(jql: str, max_results: int = 50, fields: str | None = None) -> str:
    """Search for Jira issues using JQL (Jira Query Language)"""
    try:
        fields_list = json.loads(fields) if fields else None
        results = jira_client.search_issues(jql, max_results, fields_list)
        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Jira search error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("jira_create_issue")
def jira_create_issue(project_key: str, summary: str, description: str,
                     issue_type: str = "Task", priority: str | None = None,
                     assignee: str | None = None, labels: str | None = None,
                     custom_fields: str | None = None) -> str:
    """Create a new Jira issue"""
    try:
        labels_list = json.loads(labels) if labels else None
        custom_dict = json.loads(custom_fields) if custom_fields else None
        
        issue = jira_client.create_issue(
            project_key, summary, description, issue_type,
            priority, assignee, labels_list, custom_dict
        )
        return json.dumps(issue, indent=2)
    except Exception as e:
        logger.error(f"Jira create issue error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("jira_update_issue")
def jira_update_issue(issue_key: str, fields: str) -> str:
    """Update an existing Jira issue"""
    try:
        fields_dict = json.loads(fields)
        result = jira_client.update_issue(issue_key, fields_dict)
        return json.dumps({"success": result})
    except Exception as e:
        logger.error(f"Jira update issue error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("jira_transition_issue")
def jira_transition_issue(issue_key: str, transition_id: str, 
                         comment: str | None = None) -> str:
    """Transition a Jira issue to a different status"""
    try:
        result = jira_client.transition_issue(issue_key, transition_id, comment)
        return json.dumps({"success": result})
    except Exception as e:
        logger.error(f"Jira transition error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("jira_get_transitions")
def jira_get_transitions(issue_key: str) -> str:
    """Get available status transitions for an issue"""
    try:
        transitions = jira_client.get_transitions(issue_key)
        return json.dumps(transitions, indent=2)
    except Exception as e:
        logger.error(f"Jira get transitions error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("jira_add_comment")
def jira_add_comment(issue_key: str, comment: str) -> str:
    """Add a comment to a Jira issue"""
    try:
        result = jira_client.add_comment(issue_key, comment)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Jira add comment error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("jira_link_issues")
def jira_link_issues(inward_issue: str, outward_issue: str, 
                    link_type: str = "Relates") -> str:
    """Create a link between two Jira issues"""
    try:
        result = jira_client.link_issues(inward_issue, outward_issue, link_type)
        return json.dumps({"success": result})
    except Exception as e:
        logger.error(f"Jira link issues error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("jira_get_projects")
def jira_get_projects() -> str:
    """Get all accessible Jira projects"""
    try:
        projects = jira_client.get_projects()
        return json.dumps(projects, indent=2)
    except Exception as e:
        logger.error(f"Jira get projects error: {str(e)}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    logger.info("Starting Jira Integration Server")
    if jira_client.base_url:
        logger.info("Jira authentication configured")
    else:
        logger.warning("Jira client not properly initialized - check your .env file")
    mcp.run()