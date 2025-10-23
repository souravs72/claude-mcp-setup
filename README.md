# Claude MCP Servers

A collection of Model Context Protocol (MCP) servers that extend Claude with real-world capabilities like GitHub, Jira, file operations, and web access.

## What is MCP?

**Model Context Protocol (MCP)** is a standard for connecting AI assistants to external tools and data sources. Think of it as a universal adapter that lets Claude interact with:

- **APIs** (GitHub, Jira, web services)
- **File systems** (read, write, search files)
- **Databases** (PostgreSQL, Redis)
- **Command line** (execute bash commands safely)

**Why build with MCP?** You'll learn:
- How AI assistants integrate with real systems
- Secure API design patterns
- Async programming with Python
- Error handling and validation
- Tool composition and orchestration

## Quick Setup

```bash
# 1. Clone and setup
git clone https://github.com/souravs72/claude-mcp-setup.git
cd claude-mcp-setup

# 2. Install dependencies
make setup

# 3. Configure credentials
cp config/mcp_settings.json.template config/mcp_settings.json
# Edit config/mcp_settings.json with your API keys

# 4. Start servers
make start
```

## Available Servers

| Server | Purpose | Key Features |
|--------|---------|--------------|
| **GitHub** | Repository management | Create repos, manage PRs, handle issues |
| **Jira** | Project management | Create issues, manage sprints, story points |
| **File** | File operations | Read/write files, search, directory listing |
| **Bash** | Command execution | Safe command running with validation |
| **Internet** | Web access | Google search, fetch web content |
| **Memory** | Caching | Redis-based data storage |
| **Frappe** | ERP integration | Connect to Frappe/ERPNext systems |

## Configuration

Edit `config/mcp_settings.json` with your credentials:

```json
{
  "mcpServers": {
    "github-server": {
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token_here"
      }
    },
    "jira-server": {
      "env": {
        "JIRA_BASE_URL": "https://yourcompany.atlassian.net",
        "JIRA_EMAIL": "your@email.com",
        "JIRA_API_TOKEN": "your_token_here",
        "JIRA_PROJECT_KEY": "PROJ"
      }
    }
  }
}
```

## Usage

Once configured, Claude can:

```bash
# GitHub operations
"Create a new repository called 'my-project'"
"List all open pull requests"
"Create an issue with title 'Bug fix needed'"

# Jira operations  
"Create a new task with 5 story points"
"List all issues in the current sprint"
"Update issue PROJ-123 status to 'In Progress'"

# File operations
"Read the contents of README.md"
"Search for all Python files in the project"
"Create a new file called 'config.py'"

# Web operations
"Search Google for 'Python async programming'"
"Fetch the content from https://example.com"
```

## Development

```bash
# Check server status
make status

# View logs
make logs

# Run tests
make test

# Stop all servers
make stop
```

## Key Features

- **🔒 Security First**: Command validation, path restrictions, API key protection
- **🤖 AI-Friendly**: Structured error messages, helpful suggestions
- **⚡ Fast**: Async operations, efficient caching
- **🛠️ Developer-Friendly**: Clear APIs, comprehensive logging
- **🔧 Extensible**: Easy to add new servers and capabilities

## Requirements

- Python 3.10+
- Redis (for caching)
- PostgreSQL (for persistent storage)
- API keys for external services

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**Learning MCP?** This project demonstrates real-world MCP server implementation with production-ready patterns for security, error handling, and AI integration.