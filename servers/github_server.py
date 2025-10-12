#!/usr/bin/env python3
"""
GitHub MCP Server
Provides full GitHub integration including code changes, branching, and commits
"""
import json
import sys
from pathlib import Path
from github import Github, Auth, GithubException, InputGitTreeElement

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
    """GitHub API client."""

    def __init__(self, config: GitHubConfig) -> None:
        self.config = config

        auth = Auth.Token(config.token)
        self.client = Github(auth=auth, timeout=config.timeout, retry=config.max_retries)
        self.default_branch = config.default_branch

        # Verify authentication
        try:
            user = self.client.get_user()
            logger.info(f"Authenticated as: {user.login}")
        except GithubException as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def list_repositories(
        self, username: str | None = None, sort: str = "updated", limit: int = 20
    ) -> list[dict]:
        """List repositories for a user or authenticated user."""
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

                repo_list.append(
                    {
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
                        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                    }
                )

            logger.info(f"Retrieved {len(repo_list)} repositories")
            return repo_list

        except GithubException as e:
            logger.error(f"Failed to list repositories: {e}")
            raise

    def get_file_content(self, repo_name: str, file_path: str, branch: str = "main") -> dict:
        """Get content of a specific file from a repository."""
        logger.debug(f"Fetching file: {repo_name}/{file_path} (branch: {branch})")

        try:
            repo = self.client.get_repo(repo_name)
            file_content = repo.get_contents(file_path, ref=branch)

            # Handle directory
            if isinstance(file_content, list):
                logger.warning(f"Path is a directory: {file_path}")
                return {
                    "error": "Path is a directory",
                    "items": [item.path for item in file_content],
                }

            content = file_content.decoded_content.decode("utf-8")

            logger.info(f"Retrieved file: {file_path} ({file_content.size} bytes)")

            return {
                "path": file_path,
                "content": content,
                "size": file_content.size,
                "sha": file_content.sha,
                "url": file_content.html_url,
                "encoding": file_content.encoding,
            }

        except GithubException as e:
            logger.error(f"Failed to get file content: {e}")
            raise

    def list_issues(
        self, repo_name: str, state: str = "open", labels: list[str] | None = None, limit: int = 10
    ) -> list[dict]:
        """List issues from a repository."""
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

                issue_list.append(
                    {
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
                        "comments": issue.comments,
                    }
                )

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
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> dict:
        """Create a new issue in a repository."""
        logger.debug(f"Creating issue in {repo_name}: {title}")

        try:
            repo = self.client.get_repo(repo_name)

            issue = repo.create_issue(
                title=title, body=body, labels=labels or [], assignees=assignees or []
            )

            logger.info(f"Created issue #{issue.number} in {repo_name}")

            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "state": issue.state,
                "created_at": issue.created_at.isoformat(),
            }

        except GithubException as e:
            logger.error(f"Failed to create issue: {e}")
            raise

    def create_pull_request(
        self, repo_name: str, title: str, head: str, base: str, body: str = ""
    ) -> dict:
        """Create a pull request."""
        logger.debug(f"Creating PR in {repo_name}: {head} -> {base}")

        try:
            repo = self.client.get_repo(repo_name)

            pr = repo.create_pull(title=title, body=body, head=head, base=base)

            logger.info(f"Created PR #{pr.number} in {repo_name}")

            return {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "state": pr.state,
                "created_at": pr.created_at.isoformat(),
            }

        except GithubException as e:
            logger.error(f"Failed to create pull request: {e}")
            raise

    def list_branches(self, repo_name: str, limit: int = 20) -> list[dict]:
        """
        List branches in a repository.

        Args:
            repo_name: Full repository name (owner/repo)
            limit: Maximum number of branches to return

        Returns:
            List of branch information
        """
        logger.debug(f"Listing branches in {repo_name}")

        try:
            repo = self.client.get_repo(repo_name)
            branches = repo.get_branches()

            branch_list = []
            for i, branch in enumerate(branches):
                if i >= limit:
                    break

                branch_list.append(
                    {
                        "name": branch.name,
                        "protected": branch.protected,
                        "commit_sha": branch.commit.sha,
                        "commit_url": branch.commit.html_url,
                    }
                )

            logger.info(f"Retrieved {len(branch_list)} branches from {repo_name}")
            return branch_list

        except GithubException as e:
            logger.error(f"Failed to list branches: {e}")
            raise

    def get_branch_info(self, repo_name: str, branch_name: str) -> dict:
        """
        Get information about a specific branch.

        Args:
            repo_name: Full repository name (owner/repo)
            branch_name: Branch name

        Returns:
            Branch information including latest commit
        """
        logger.debug(f"Getting branch info: {repo_name}/{branch_name}")

        try:
            repo = self.client.get_repo(repo_name)
            branch = repo.get_branch(branch_name)

            logger.info(f"Retrieved branch info: {branch_name}")

            return {
                "name": branch.name,
                "protected": branch.protected,
                "commit": {
                    "sha": branch.commit.sha,
                    "url": branch.commit.html_url,
                    "message": branch.commit.commit.message,
                    "author": branch.commit.commit.author.name,
                    "date": branch.commit.commit.author.date.isoformat(),
                },
            }

        except GithubException as e:
            if e.status == 404:
                logger.warning(f"Branch not found: {branch_name}")
                return {"error": f"Branch '{branch_name}' not found"}
            logger.error(f"Failed to get branch info: {e}")
            raise

    def create_branch(self, repo_name: str, branch_name: str, source_branch: str = "main") -> dict:
        """
        Create a new branch from a source branch.

        Args:
            repo_name: Full repository name (owner/repo)
            branch_name: New branch name
            source_branch: Source branch to branch from

        Returns:
            Created branch information
        """
        logger.debug(f"Creating branch {branch_name} from {source_branch} in {repo_name}")

        try:
            repo = self.client.get_repo(repo_name)

            # Check if branch already exists
            try:
                existing = repo.get_branch(branch_name)
                logger.warning(f"Branch {branch_name} already exists")
                return {
                    "success": False,
                    "error": f"Branch '{branch_name}' already exists",
                    "existing_branch": {"name": existing.name, "commit_sha": existing.commit.sha},
                }
            except GithubException as e:
                if e.status != 404:
                    raise

            # Get source branch reference
            source_ref = repo.get_git_ref(f"heads/{source_branch}")
            source_sha = source_ref.object.sha

            # Create new branch
            new_ref = repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_sha)

            logger.info(f"Created branch: {branch_name} at {source_sha[:7]}")

            return {
                "success": True,
                "branch_name": branch_name,
                "source_branch": source_branch,
                "sha": source_sha,
                "ref": new_ref.ref,
            }

        except GithubException as e:
            logger.error(f"Failed to create branch: {e}")
            raise

    def create_or_update_file(
        self,
        repo_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str | None = None,
        sha: str | None = None,
    ) -> dict:
        """Create or update a file in the repository.

        Args:
            repo_name: Full repository name (owner/repo)
            file_path: Path to file in repository
            content: File content
            commit_message: Commit message
            branch: Branch to commit to
            sha: File SHA (required for updates, obtained from get_file_content)

        Returns:
            Commit information
        """
        if branch is None:
            branch = self.default_branch

        logger.debug(f"Creating/updating file: {repo_name}/{file_path} on {branch}")

        try:
            repo = self.client.get_repo(repo_name)

            # Try to get existing file
            if not sha:
                try:
                    existing_file = repo.get_contents(file_path, ref=branch)
                    if not isinstance(existing_file, list):
                        sha = existing_file.sha
                        logger.debug(f"Found existing file with SHA: {sha[:7]}")
                except GithubException as e:
                    if e.status != 404:
                        raise
                    logger.debug(f"File does not exist, will create new")

            # Create or update file
            if sha:
                # Update existing file
                result = repo.update_file(
                    path=file_path, message=commit_message, content=content, sha=sha, branch=branch
                )
                action = "Updated"
            else:
                # Create new file
                result = repo.create_file(
                    path=file_path, message=commit_message, content=content, branch=branch
                )
                action = "Created"

            logger.info(f"{action} file: {file_path} on {branch}")

            return {
                "success": True,
                "action": action.lower(),
                "file_path": file_path,
                "branch": branch,
                "commit": {
                    "sha": result["commit"].sha,
                    "message": commit_message,
                    "url": result["commit"].html_url,
                },
                "content": {"sha": result["content"].sha, "url": result["content"].html_url},
            }

        except GithubException as e:
            logger.error(f"Failed to create/update file: {e}")
            raise

    def commit_multiple_files(
        self,
        repo_name: str,
        branch: str,
        files: list[dict[str, str]],
        commit_message: str,
        base_branch: str | None = None,
    ) -> dict:
        """
        Commit multiple file changes in a single commit.

        Args:
            repo_name: Full repository name (owner/repo)
            branch: Branch to commit to
            files: List of file dictionaries with 'path' and 'content' keys
            commit_message: Commit message
            base_branch: Base branch (if different from branch)

        Returns:
            Commit information
        """
        logger.debug(f"Committing {len(files)} files to {repo_name}/{branch}")

        try:
            repo = self.client.get_repo(repo_name)

            # Get base branch reference
            if base_branch:
                base_ref = repo.get_git_ref(f"heads/{base_branch}")
            else:
                base_ref = repo.get_git_ref(f"heads/{branch}")

            base_sha = base_ref.object.sha
            base_tree = repo.get_git_tree(base_sha)

            # Create tree elements for all files
            tree_elements = []
            for file_info in files:
                tree_elements.append(
                    InputGitTreeElement(
                        path=file_info["path"],
                        mode="100644",  # Regular file
                        type="blob",
                        content=file_info["content"],
                    )
                )

            # Create new tree
            new_tree = repo.create_git_tree(tree_elements, base_tree)

            # Create commit
            parent = repo.get_git_commit(base_sha)
            new_commit = repo.create_git_commit(
                message=commit_message, tree=new_tree, parents=[parent]
            )

            # Update branch reference
            branch_ref = repo.get_git_ref(f"heads/{branch}")
            branch_ref.edit(new_commit.sha)

            logger.info(f"Committed {len(files)} files to {branch}: {new_commit.sha[:7]}")

            return {
                "success": True,
                "branch": branch,
                "files_count": len(files),
                "commit": {
                    "sha": new_commit.sha,
                    "message": commit_message,
                    "author": new_commit.author.name,
                    "date": new_commit.author.date.isoformat(),
                },
            }

        except GithubException as e:
            logger.error(f"Failed to commit multiple files: {e}")
            raise

    def delete_file(
        self,
        repo_name: str,
        file_path: str,
        commit_message: str,
        branch: str = "dev-sourav",
        sha: str | None = None,
    ) -> dict:
        """
        Delete a file from the repository.

        Args:
            repo_name: Full repository name (owner/repo)
            file_path: Path to file in repository
            commit_message: Commit message
            branch: Branch to commit to
            sha: File SHA (required, obtained from get_file_content)

        Returns:
            Commit information
        """
        logger.debug(f"Deleting file: {repo_name}/{file_path} from {branch}")

        try:
            repo = self.client.get_repo(repo_name)

            # Get file SHA if not provided
            if not sha:
                existing_file = repo.get_contents(file_path, ref=branch)
                if isinstance(existing_file, list):
                    raise ValueError(f"Path is a directory: {file_path}")
                sha = existing_file.sha

            # Delete file
            result = repo.delete_file(
                path=file_path, message=commit_message, sha=sha, branch=branch
            )

            logger.info(f"Deleted file: {file_path} from {branch}")

            return {
                "success": True,
                "action": "deleted",
                "file_path": file_path,
                "branch": branch,
                "commit": {
                    "sha": result["commit"].sha,
                    "message": commit_message,
                    "url": result["commit"].html_url,
                },
            }

        except GithubException as e:
            logger.error(f"Failed to delete file: {e}")
            raise

    def get_directory_tree(
        self, repo_name: str, path: str = "", branch: str = "main", recursive: bool = False
    ) -> list[dict]:
        """
        Get directory structure.

        Args:
            repo_name: Full repository name (owner/repo)
            path: Directory path (empty for root)
            branch: Branch name
            recursive: Include subdirectories

        Returns:
            List of files and directories
        """
        logger.debug(f"Getting directory tree: {repo_name}/{path} on {branch}")

        try:
            repo = self.client.get_repo(repo_name)
            contents = repo.get_contents(path, ref=branch)

            if not isinstance(contents, list):
                contents = [contents]

            tree = []
            for item in contents:
                tree.append(
                    {
                        "path": item.path,
                        "name": item.name,
                        "type": item.type,
                        "size": item.size,
                        "sha": item.sha,
                        "url": item.html_url,
                    }
                )

                # Recursively get subdirectories
                if recursive and item.type == "dir":
                    subtree = self.get_directory_tree(repo_name, item.path, branch, True)
                    tree.extend(subtree)

            logger.info(f"Retrieved directory tree with {len(tree)} items")
            return tree

        except GithubException as e:
            logger.error(f"Failed to get directory tree: {e}")
            raise

    def close(self) -> None:
        """Close the GitHub client."""
        if self.client:
            self.client.close()
            logger.debug("GitHub client closed")


# Initialize client
try:
    config = GitHubConfig()
    validate_config(config, logger)

    log_server_startup(
        logger,
        "GitHub Server",
        {
            "Timeout": config.timeout,
            "Max Retries": config.max_retries,
            "Capabilities": "Read + Write + Branch + Commit",
        },
    )

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
def list_repositories(username: str | None = None, sort: str = "updated", limit: int = 20) -> str:
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
    repo_name: str, state: str = "open", labels: str | None = None, limit: int = 10
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
    labels: str | None = None,
    assignees: str | None = None,
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
def create_pull_request(repo_name: str, title: str, head: str, base: str, body: str = "") -> str:
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


@mcp.tool()
@handle_errors(logger)
def list_branches(repo_name: str, limit: int = 20) -> str:
    """
    List branches in a repository.

    Args:
        repo_name: Full repository name (owner/repo)
        limit: Maximum number of branches (default: 20)

    Returns:
        JSON string with list of branches
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})

    branches = github_client.list_branches(repo_name, limit)
    return json.dumps(branches, indent=2)


@mcp.tool()
@handle_errors(logger)
def get_branch_info(repo_name: str, branch_name: str) -> str:
    """
    Get information about a specific branch.

    Args:
        repo_name: Full repository name (owner/repo)
        branch_name: Branch name

    Returns:
        JSON string with branch information
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})

    branch_info = github_client.get_branch_info(repo_name, branch_name)
    return json.dumps(branch_info, indent=2)


@mcp.tool()
@handle_errors(logger)
def create_branch(repo_name: str, branch_name: str, source_branch: str = "main") -> str:
    """
    Create a new branch from a source branch.

    Args:
        repo_name: Full repository name (owner/repo)
        branch_name: New branch name (e.g., "dev-sourav")
        source_branch: Source branch to branch from (default: "main")

    Returns:
        JSON string with created branch information

    Example:
        create_branch("owner/repo", "dev-sourav", "main")
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})

    result = github_client.create_branch(repo_name, branch_name, source_branch)
    return json.dumps(result, indent=2)


@mcp.tool()
def create_or_update_file(
    repo_name: str,
    file_path: str,
    content: str,
    commit_message: str,
    branch: str | None = None,
    sha: str | None = None,
) -> str:
    """
    Create or update a file in the repository.
    IMPORTANT: Commit message must be concise and impactful.

    Args:
        repo_name: Full repository name (owner/repo)
        file_path: Path to file in repository
        content: File content
        commit_message: Commit message (must be concise and impactful)
        branch: Branch to commit to (default: "dev-sourav")
        sha: File SHA (required for updates, get from get_file_content)

    Returns:
        JSON string with commit information

    Example:
        create_or_update_file(
            "owner/repo",
            "src/utils/helper.py",
            "def helper(): pass",
            "Add helper function for data processing",
            "dev-sourav"
        )
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})

    result = github_client.create_or_update_file(
        repo_name, file_path, content, commit_message, branch, sha
    )
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def commit_multiple_files(
    repo_name: str, branch: str, files: str, commit_message: str, base_branch: str | None = None
) -> str:
    """
    Commit multiple file changes in a single commit.
    IMPORTANT: Commit message must be concise and impactful.
    Use this for atomic changes that span multiple files.

    Args:
        repo_name: Full repository name (owner/repo)
        branch: Branch to commit to (e.g., "dev-sourav")
        files: JSON array of file objects with 'path' and 'content' keys
        commit_message: Commit message (must be concise and impactful)
        base_branch: Base branch if different from branch

    Returns:
        JSON string with commit information

    Example:
        commit_multiple_files(
            "owner/repo",
            "dev-sourav",
            '[{"path": "src/user.py", "content": "..."}, {"path": "src/auth.py", "content": "..."}]',
            "Refactor authentication system"
        )
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})

    files_list = json.loads(files)
    result = github_client.commit_multiple_files(
        repo_name, branch, files_list, commit_message, base_branch
    )
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def delete_file(
    repo_name: str,
    file_path: str,
    commit_message: str,
    branch: str = "dev-sourav",
    sha: str | None = None,
) -> str:
    """
    Delete a file from the repository.

    Args:
        repo_name: Full repository name (owner/repo)
        file_path: Path to file in repository
        commit_message: Commit message
        branch: Branch to commit to (default: "dev-sourav")
        sha: File SHA (required, get from get_file_content)

    Returns:
        JSON string with commit information
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})

    result = github_client.delete_file(repo_name, file_path, commit_message, branch, sha)
    return json.dumps(result, indent=2)


@mcp.tool()
@handle_errors(logger)
def get_directory_tree(
    repo_name: str, path: str = "", branch: str = "main", recursive: bool = False
) -> str:
    """
    Get directory structure of a repository.

    Args:
        repo_name: Full repository name (owner/repo)
        path: Directory path (empty for root)
        branch: Branch name (default: "main")
        recursive: Include subdirectories (default: False)

    Returns:
        JSON string with directory structure
    """
    if not github_client:
        return json.dumps({"error": "GitHub client not initialized"})

    tree = github_client.get_directory_tree(repo_name, path, branch, recursive)
    return json.dumps(tree, indent=2)

def main() -> None:
    """Main entry point for Frappe MCP Server."""
    try:
        if not github_client:
            logger.error("Server starting with errors - some features unavailable")

        logger.info("Starting Frappe MCP Server...")
        mcp.run()

    except KeyboardInterrupt:
        log_server_shutdown(logger, "Frappe Server")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        if github_client:
            github_client.close()


if __name__ == "__main__":
    main()