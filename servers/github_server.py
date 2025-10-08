#!/usr/bin/env python3
"""
GitHub MCP Server - Production Ready
Provides integration with GitHub via PyGithub library
"""
import json
import sys
from pathlib import Path
from typing import Optional, List
from github import Github, Auth, GithubException

from mcp.server.fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.logging_config import setup_logging, log_server_startup, log_server_shutdown
from servers.config import load_env_file, GitHubConfig, validate_config, ConfigurationError
from servers.base_client import handle_errors

# Initialize
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "github_server.log"
logger = setup_logging("GitHubServer", log_file=log_file)

load_env_file()
mcp = FastMCP("GitHub Integration Server")


class GitHubClient:
    """GitHub API client wrapper with error handling."""
    
    def __init__(self, config: GitHubConfig):
        self.config = config
        
        auth = Auth.Token(config.token)
        self.client = Github(
            auth=auth,
            timeout=config.timeout,
            retry=config.max_retries
        )
        
        # Verify authentication
        try:
            user = self.client.get_user()
            logger.info(f"Authenticated as: {user.login}")
        except GithubException as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def list_repositories(
        self,
        username: Optional[str] = None,
        sort: str = "updated",
        limit: int = 20
    ) -> List[dict]:
        """
        List repositories for a user or authenticated user.
        
        Args:
            username: GitHub username (None for authenticated user)
            sort: Sort order (updated, created, pushed, full_name)
            limit: Maximum number of repositories
            
        Returns:
            List of repository information
        """
        logger.debug(f"Listing repositories (user: {username or 'authenticated'}, limit: {limit})")
        
        try:
            if username:
                user = self.client.get_user(username)
            else:
                user = self.client.get_user()
            
            repos = user.get_repos(sort=sort)
            
            repo_list = []
            for i, repo in enumerate(repos):
                if i >= limit:
                    break
                
                repo_list.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "url": repo.html_url,
                    "description": repo.description,
                    "private": repo.private,
                    "language": repo.language,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "open_issues": repo.open_issues_count,
                    "default_branch": repo.default_branch,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
                })
            
            logger.info(f"Retrieved {len(repo_list)} repositories")
            return repo_list
            
        except GithubException as e:
            logger.error(f"Failed to list repositories: {e}")
            raise
    
    def get_file_content(
        self,
        repo_name: str,
        file_path: str,
        branch: str = "main"
    ) -> dict:
        """
        Get content of a specific file from a repository.
        
        Args:
            repo_name: Full repository name (owner/repo)
            file_path: Path to file in repository
            branch: Branch name (default: main)
            
        Returns:
            File information and content
        """
        logger.debug(f"Fetching file: {repo_name}/{file_path} (branch: {branch})")
        
        try:
            repo = self.client.get_repo(repo_name)
            file_content = repo.get_contents(file_path, ref=branch)
            
            # Handle directory
            if isinstance(file_content, list):
                logger.warning(f"Path is a directory: {file_path}")
                return {
                    "error": "Path is a directory",
                    "items": [item.path for item in file_content]
                }
            
            content = file_content.decoded_content.decode('utf-8')
            
            logger.info(f"Retrieved file: {file_path} ({file_content.size} bytes)")
            
            return {
                "path": file_path,
                "content": content,
                "size": file_content.size,
                "sha": file_content.sha,
                "url": file_content.html_url,
                "encoding": file_content.encoding
            }
            
        except GithubException as e:
            logger.error(f"Failed to get file content: {e}")
            raise
    
    def list_issues(
        self,
        repo_name: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[dict]:
        """
        List issues from a repository.
        
        Args:
            repo_name: Full repository name (owner/repo)
            state: Issue state (open, closed, all)
            labels: Filter by labels
            limit: Maximum number of issues
            
        Returns:
            List of issue information
        """
        logger.debug(f"Listing issues: {repo_name} (state: {state}, limit: {limit})")
        
        try:
            repo = self.client.get_repo(repo_name)
            issues = repo.get_issues(state=state, labels=labels or [])
            
            issue_list = []
            for i, issue in enumerate(issues):
                if i >= limit:
                    break
                
                # Truncate body if too long
                body = issue.body or ""
                if len(body) > 500:
                    body = body[:500] + "..."
                
                issue_list.append({
                    "number": issue.number,
                    "title": issue.title,
                    "body": body,
                    "state": issue.state,
                    "url": issue.html_url,
                    "user": issue.user.login,
                    "assignees": [a.login for a in issue.assignees],
                    "labels": [label.name for label in issue.labels],
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat(),
                    "comments": issue.comments
                })
            
            logger.info(f"Retrieved {len(issue_list)} issues from {repo_name}")
            return issue_list
            
        except GithubException as e:
            logger.error(f"Failed to list issues: {e}")
            raise
    
    def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> dict:
        """
        Create a new issue in a repository.
        
        Args:
            repo_name: Full repository name (owner/repo)
            title: Issue title
            body: Issue body/description
            labels: List of label names
            assignees: List of usernames to assign
            
        Returns:
            Created issue information
        """
        logger.debug(f"Creating issue in {repo_name}: {title}")
        
        try:
            repo = self.client.get_repo(repo_name)
            
            issue = repo.create_issue(
                title=title,
                body=body,
                labels=labels or [],
                assignees=assignees or []
            )
            
            logger.info(f"Created issue #{issue.number} in {repo_name}")
            
            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "state": issue.state,
                "created_at": issue.created_at.isoformat()
            }
            
        except GithubException as e:
            logger.error(f"Failed to create issue: {e}")
            raise
    
    def create_pull_request(
        self,
        repo_name: str,
        title: str,
        head: str,
        base: str,
        body: str = ""
    ) -> dict:
        """
        Create a pull request.
        
        Args:
            repo_name: Full repository name (owner/repo)
            title: PR title
            head: Branch containing changes
            base: Branch to merge into
            body: PR description
            
        Returns:
            Created pull request information
        """
        logger.debug(f"Creating PR in {repo_name}: {head} -> {base}")
        
        try:
            repo = self.client.get_repo(repo_name)
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )
            
            logger.info(f"Created PR #{pr.number} in {repo_name}")
            
            return {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "state": pr.state,
                "created_at": pr.created_at.isoformat()
            }
            
        except GithubException as e:
            logger.error(f"Failed to create pull request: {e}")
            raise
    
    def close(self):
        """Close the GitHub client."""
        if self.client:
            self.client.close()
            logger.debug("GitHub client closed")


# Initialize client
try:
    config = GitHubConfig()
    validate_config(config, logger)
    
    log_server_startup(logger, "GitHub Server", {
        "Timeout": config.timeout,
        "Max Retries": config.max_retries
    })
    
    github_client = GitHubClient(config)
    
except ConfigurationError as e:
    logger.critical(f"Configuration error: {e}")
    github_client = None
except Exception as e:
    logger.critical(f"Failed to initialize GitHub client: {e}", exc_info=True)
    github_client = None


# MCP Tools
@mcp.tool()
@handle_errors(logger)
def list_repositories(
    username: Optional[str] = None,
    sort: str = "updated",
    limit: int = 20
) -> str:
    """
    List repositories for a user or authenticated user.
    
    Args:
        username: GitHub username (None for authenticated user)
        sort: Sort order (updated, created, pushed, full_name)
        limit: Maximum number of repositories (default: 20)
        
    Returns:
        JSON string with list of repositories
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})
    
    repos = github_client.list_repositories(username, sort, limit)
    return json.dumps(repos, indent=2)


@mcp.tool()
@handle_errors(logger)
def get_file_content(repo_name: str, file_path: str, branch: str = "main") -> str:
    """
    Get content of a specific file from a repository.
    
    Args:
        repo_name: Full repository name (owner/repo)
        file_path: Path to file in repository
        branch: Branch name (default: main)
        
    Returns:
        JSON string with file content and metadata
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})
    
    content = github_client.get_file_content(repo_name, file_path, branch)
    return json.dumps(content, indent=2)


@mcp.tool()
@handle_errors(logger)
def list_issues(
    repo_name: str,
    state: str = "open",
    labels: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    List issues from a repository.
    
    Args:
        repo_name: Full repository name (owner/repo)
        state: Issue state (open, closed, all)
        labels: JSON array of label names to filter by
        limit: Maximum number of issues (default: 10)
        
    Returns:
        JSON string with list of issues
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})
    
    labels_list = json.loads(labels) if labels else None
    issues = github_client.list_issues(repo_name, state, labels_list, limit)
    return json.dumps(issues, indent=2)


@mcp.tool()
@handle_errors(logger)
def create_issue(
    repo_name: str,
    title: str,
    body: str = "",
    labels: Optional[str] = None,
    assignees: Optional[str] = None
) -> str:
    """
    Create a new issue in a repository.
    
    Args:
        repo_name: Full repository name (owner/repo)
        title: Issue title
        body: Issue body/description
        labels: JSON array of label names
        assignees: JSON array of usernames to assign
        
    Returns:
        JSON string with created issue information
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})
    
    labels_list = json.loads(labels) if labels else None
    assignees_list = json.loads(assignees) if assignees else None
    
    issue = github_client.create_issue(repo_name, title, body, labels_list, assignees_list)
    return json.dumps(issue, indent=2)


@mcp.tool()
@handle_errors(logger)
def create_pull_request(
    repo_name: str,
    title: str,
    head: str,
    base: str,
    body: str = ""
) -> str:
    """
    Create a pull request.
    
    Args:
        repo_name: Full repository name (owner/repo)
        title: PR title
        head: Branch containing changes
        base: Branch to merge into
        body: PR description
        
    Returns:
        JSON string with created pull request information
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})
    
    pr = github_client.create_pull_request(repo_name, title, head, base, body)
    return json.dumps(pr, indent=2)


if __name__ == "__main__":
    try:
        if not github_client:
            logger.error("Server starting with errors - some features unavailable")
        
        logger.info("Starting GitHub MCP Server...")
        mcp.run()
        
    except KeyboardInterrupt:
        log_server_shutdown(logger, "GitHub Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if github_client:
            github_client.close()