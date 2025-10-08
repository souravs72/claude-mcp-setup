#!/usr/bin/env python3
import json
import logging
import os
from pathlib import Path
from github import Github, Auth
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
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

mcp = FastMCP("GitHub Integration Server")

# Initialize GitHub client with new authentication method
github_token = os.environ.get('GITHUB_PERSONAL_ACCESS_TOKEN')
if github_token:
    auth = Auth.Token(github_token)
    github_client = Github(auth=auth)
    logger.info("GitHub client initialized successfully")
else:
    github_client = None
    logger.error("GitHub token not provided. Set GITHUB_PERSONAL_ACCESS_TOKEN environment variable.")

@mcp.tool("list_repositories")
def list_repositories(username: str | None = None) -> str:
    """List repositories for a user or authenticated user"""
    try:
        if not github_client:
            return json.dumps({"error": "GitHub client not initialized. Check your GITHUB_PERSONAL_ACCESS_TOKEN."})
            
        if username:
            user = github_client.get_user(username)
            repos = user.get_repos()
        else:
            repos = github_client.get_user().get_repos()
        
        repo_list = []
        for repo in repos[:20]:  # Limit to first 20 repos
            repo_list.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "url": repo.html_url,
                "description": repo.description,
                "private": repo.private,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count
            })
        
        return json.dumps(repo_list)
        
    except Exception as e:
        logger.error(f"Repository listing error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("get_file_content")
def get_file_content(repo_name: str, file_path: str, branch: str = "main") -> str:
    """Get content of a specific file from a repository"""
    try:
        if not github_client:
            return json.dumps({"error": "GitHub client not initialized. Check your GITHUB_PERSONAL_ACCESS_TOKEN."})
            
        repo = github_client.get_repo(repo_name)
        file = repo.get_contents(file_path, ref=branch)
        
        return json.dumps({
            "path": file_path,
            "content": file.decoded_content.decode('utf-8'),
            "size": file.size,
            "sha": file.sha
        })
        
    except Exception as e:
        logger.error(f"File content error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("list_issues")
def list_issues(repo_name: str, state: str = "open") -> str:
    """List issues from a repository"""
    try:
        if not github_client:
            return json.dumps({"error": "GitHub client not initialized. Check your GITHUB_PERSONAL_ACCESS_TOKEN."})
            
        repo = github_client.get_repo(repo_name)
        issues = repo.get_issues(state=state)
        
        issue_list = []
        for issue in issues[:10]:  # Limit to first 10 issues
            issue_list.append({
                "number": issue.number,
                "title": issue.title,
                "body": issue.body[:500] + "..." if len(issue.body or "") > 500 else issue.body,
                "state": issue.state,
                "url": issue.html_url,
                "user": issue.user.login,
                "created_at": issue.created_at.isoformat(),
                "labels": [label.name for label in issue.labels]
            })
        
        return json.dumps(issue_list)
        
    except Exception as e:
        logger.error(f"Issue listing error: {str(e)}")
        return json.dumps({"error": str(e)})

@mcp.tool("create_issue")
def create_issue(repo_name: str, title: str, body: str = "") -> str:
    """Create a new issue in a repository"""
    try:
        if not github_client:
            return json.dumps({"error": "GitHub client not initialized. Check your GITHUB_PERSONAL_ACCESS_TOKEN."})
            
        repo = github_client.get_repo(repo_name)
        issue = repo.create_issue(title=title, body=body)
        
        return json.dumps({
            "number": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "state": issue.state
        })
        
    except Exception as e:
        logger.error(f"Issue creation error: {str(e)}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    logger.info("Starting GitHub Integration Server")
    if github_client:
        logger.info("GitHub authentication successful")
    else:
        logger.warning("GitHub client not properly initialized - server will run with limited functionality")
    mcp.run()