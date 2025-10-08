# Claude MCP Server Infrastructure

> **Enterprise-grade Model Context Protocol servers that extend Claude with multi-platform integrations**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0+-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready MCP server infrastructure that enables Claude to interact with GitHub, Jira, Frappe, and the web through a sophisticated goal-based orchestration layer.

---

## Overview

This infrastructure provides Claude with intelligent task orchestration capabilities and direct integration with your development tools. Break down complex goals into actionable tasks, coordinate across multiple repositories, and automate project management—all through natural conversation.

### What Makes This Different

- **🎯 Goal-Oriented Architecture**: AI-driven goal decomposition with automatic dependency resolution
- **🔗 Multi-Platform Integration**: Unified interface across GitHub, Jira, Frappe, and web search
- **📊 Intelligent Orchestration**: Automatic execution planning with parallel task identification
- **🏢 Production-Ready**: Comprehensive logging, error handling, and security best practices

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Claude Desktop                        │
│              Natural Language Interface                   │
└───────────────────────┬──────────────────────────────────┘
                        │
                   MCP Protocol
                        │
        ┌───────────────┼───────────────┬─────────────┐
        │               │               │             │
┌───────▼──────┐ ┌─────▼─────┐  ┌─────▼──────┐ ┌───▼─────┐
│ Goal Agent   │ │   Jira    │  │   GitHub   │ │ Frappe  │
│              │ │           │  │            │ │         │
│ • Planning   │ │ • Issues  │  │ • Repos    │ │ • Docs  │
│ • Tracking   │ │ • Search  │  │ • Issues   │ │ • Data  │
│ • Execution  │ │ • Status  │  │ • Files    │ │ • CRUD  │
└──────────────┘ └───────────┘  └────────────┘ └─────────┘
        │               │               │             │
        └───────────────┴───────────────┴─────────────┘
                        │
                  Your Workflow
```

---

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Claude Desktop application
- API credentials (see [Configuration](#configuration))

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-mcp-setup.git
cd claude-mcp-setup

# Install dependencies
pip install -r requirements/goal_agent_requirements.txt
pip install -r requirements/jira_requirements.txt
pip install -r requirements/github_requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your credentials

# Start all servers
python scripts/start_all_servers.py
```

### Configure Claude Desktop

Edit your Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "goal-agent": {
      "command": "python",
      "args": ["/absolute/path/to/servers/goal_agent_server.py"]
    },
    "jira": {
      "command": "python",
      "args": ["/absolute/path/to/servers/jira_server.py"],
      "env": {
        "JIRA_BASE_URL": "https://your-domain.atlassian.net",
        "JIRA_EMAIL": "your@email.com",
        "JIRA_API_TOKEN": "your_token"
      }
    },
    "github": {
      "command": "python",
      "args": ["/absolute/path/to/servers/github_server.py"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token"
      }
    }
  }
}
```

Restart Claude Desktop.

---

## Core Capabilities

### 🎯 Goal-Based Orchestration

Transform high-level objectives into executable task plans with automatic dependency management.

```
User: "Create a goal to migrate authentication to OAuth 2.0"

Claude:
✓ Created GOAL-1: Migrate to OAuth 2.0
✓ Generated 8 tasks across 3 repositories
✓ Identified 3 execution phases
✓ Created Jira epic and linked tickets
```

**Key Features**:
- Automatic task breakdown with intelligent dependency detection
- Multi-repository coordination
- Parallel execution identification
- Progress tracking and status updates

### 🔗 Platform Integration

#### GitHub Integration
- Repository and file management
- Issue creation and tracking
- Pull request coordination
- Multi-repo operations

#### Jira Integration
- Issue creation with custom fields
- Advanced JQL search
- Status transitions and workflows
- Issue linking and epic management

#### Frappe Integration
- Document CRUD operations
- Custom DocType support
- Filter-based queries
- Real-time data access

#### Web Search
- Google Custom Search API
- Content fetching and parsing
- Research and documentation

---

## Usage Examples

### Example 1: Feature Development

```
User: "I need to add rate limiting to our API"

Claude: "I'll create a comprehensive plan for that."

[Uses: create_goal]
Created GOAL-1: Add rate limiting to API

[Uses: break_down_goal]
Created tasks:
  • TASK-1: Research rate limiting strategies
  • TASK-2: Design rate limiting architecture
  • TASK-3: Implement middleware (depends on TASK-2)
  • TASK-4: Add Redis for distributed limiting
  • TASK-5: Write integration tests (depends on TASK-3, TASK-4)
  • TASK-6: Update API documentation

[Uses: jira_create_issue × 6]
Created Jira tickets: PROJ-101 through PROJ-106

[Uses: generate_execution_plan]
Execution plan:
  Phase 1: TASK-1 (can start immediately)
  Phase 2: TASK-2 (after research)
  Phase 3: TASK-3, TASK-4 (parallel implementation)
  Phase 4: TASK-5, TASK-6 (final steps)
```

### Example 2: Multi-Repo Refactoring

```
User: "Refactor our authentication library from repo-api to shared-lib, 
       then update repo-api and repo-web to use it"

Claude: [Creates goal with 3 repos, generates 9 tasks with dependencies,
         creates execution plan, generates Jira tickets, links PRs]

Result: Complete migration plan with 4 execution phases
```

### Example 3: Sprint Planning

```
User: "Plan our Q4 Sprint 3 features"

Claude: [Creates goal, breaks into user stories, estimates effort,
         creates Jira sprint, assigns priorities]

Result: Sprint ready with estimated tasks and dependencies mapped
```

---

## MCP Tools Reference

### Goal Agent (9 tools)

| Tool | Purpose |
|------|---------|
| `create_goal` | Create high-level goals with metadata |
| `break_down_goal` | Decompose goals into executable tasks |
| `get_goal` | Retrieve goal details with tasks |
| `list_goals` | List goals with status/priority filters |
| `get_task` | Get specific task information |
| `get_next_tasks` | Find ready-to-execute tasks |
| `update_task_status` | Update task progress and results |
| `generate_execution_plan` | Create phased execution timeline |

### Jira Integration (9 tools)

| Tool | Purpose |
|------|---------|
| `jira_create_issue` | Create issues with custom fields |
| `jira_search_issues` | Search using JQL queries |
| `jira_get_issue` | Retrieve issue details |
| `jira_update_issue` | Update issue fields |
| `jira_transition_issue` | Change issue status |
| `jira_add_comment` | Add comments to issues |
| `jira_link_issues` | Create issue relationships |
| `jira_get_transitions` | List available status transitions |
| `jira_get_projects` | List accessible projects |

### GitHub Integration (4 tools)

| Tool | Purpose |
|------|---------|
| `list_repositories` | List user repositories |
| `get_file_content` | Read file contents |
| `list_issues` | List repository issues |
| `create_issue` | Create new issues |

### Frappe Integration (3 tools)

| Tool | Purpose |
|------|---------|
| `frappe_get_document` | Get specific documents |
| `frappe_get_list` | Query documents with filters |
| `frappe_create_document` | Create new documents |

### Internet Access (2 tools)

| Tool | Purpose |
|------|---------|
| `web_search` | Google Custom Search |
| `web_fetch` | Fetch webpage content |

---

## Configuration

### Environment Variables

Create `.env` in the project root:

```bash
# Jira Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=your_jira_token
JIRA_PROJECT_KEY=PROJ

# GitHub Configuration
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_github_token

# Google Search (Optional)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Frappe (Optional)
FRAPPE_SITE_URL=http://127.0.0.1:8005
FRAPPE_API_KEY=your_frappe_key
FRAPPE_API_SECRET=your_frappe_secret
```

### Obtaining API Credentials

**Jira**:
1. Visit https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API token
3. Use your Atlassian email and token

**GitHub**:
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `read:user`, `write:issues`

**Google Search**:
1. Enable Custom Search API in Google Cloud Console
2. Create search engine at https://cse.google.com/
3. Copy API key and Search Engine ID

---

## Project Structure

```
claude-mcp-setup/
├── servers/              # MCP server implementations
│   ├── goal_agent_server.py
│   ├── jira_server.py
│   ├── github_server.py
│   ├── frappe_server.py
│   └── internets_server.py
├── requirements/         # Dependency specifications
├── scripts/             # Management utilities
│   ├── start_all_servers.py
│   └── stop_all_servers.py
├── logs/                # Server logs (auto-created)
├── .env                 # Environment configuration
└── docs/               # Additional documentation
```

---

## Operations

### Server Management

```bash
# Start all servers
python scripts/start_all_servers.py

# Stop all servers
python scripts/stop_all_servers.py

# View logs
tail -f logs/goal_agent_server.log
tail -f logs/jira_server.log

# Check server status
ps aux | grep server.py
```

### Health Checks

```bash
# Test individual server
python servers/goal_agent_server.py

# Verify Jira connection
python -c "from servers.jira_server import JiraClient; JiraClient()"

# Check GitHub authentication
python -c "from servers.github_server import github_client; print(github_client.get_user().login)"
```

---

## Security

### Best Practices

- ✅ **Never commit `.env` files** - Add to `.gitignore`
- ✅ **Rotate credentials regularly** - Update tokens quarterly
- ✅ **Use minimal permissions** - Grant only required scopes
- ✅ **Monitor API usage** - Set up alerts for quota limits
- ✅ **Enable 2FA** - On all integrated services
- ✅ **Review logs** - Regular security audits

### API Rate Limits

| Service | Authenticated | Unauthenticated |
|---------|--------------|-----------------|
| GitHub | 5,000/hour | 60/hour |
| Jira | Varies by plan | N/A |
| Google Search | 100/day (free) | N/A |

---

## Troubleshooting

### Common Issues

**Servers won't start**
```bash
# Check logs
cat logs/goal_agent_server.log

# Verify dependencies
pip install -r requirements/goal_agent_requirements.txt

# Test Python path
which python
```

**Jira connection fails**
```bash
# Test credentials
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('URL:', os.getenv('JIRA_BASE_URL'))
print('Email:', os.getenv('JIRA_EMAIL'))
print('Token:', 'Set' if os.getenv('JIRA_API_TOKEN') else 'Missing')
"
```

**Tools not appearing in Claude**
1. Verify absolute paths in Claude Desktop config
2. Restart Claude Desktop completely
3. Check server logs for errors
4. Ensure servers started before launching Claude

---

## Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get running in 5 minutes
- **[Goal Agent Documentation](docs/README_GOAL_AGENT.md)** - Complete API reference
- **[Architecture Overview](docs/FILE_STRUCTURE.md)** - System design details
- **[Contributing Guide](CONTRIBUTING.md)** - Development guidelines

---

## Support & Community

- **Issues**: [GitHub Issues](https://github.com/yourusername/claude-mcp-setup/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/claude-mcp-setup/discussions)
- **Documentation**: [Full Docs](https://docs.yoursite.com)

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/) - AI assistant platform
- [MCP Protocol](https://modelcontextprotocol.io/) - Model Context Protocol
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework

Integrations:
- [GitHub API](https://docs.github.com/en/rest)
- [Jira REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Frappe Framework](https://frappeframework.com/)
- [Google Custom Search](https://developers.google.com/custom-search)

---

<div align="center">

**[Getting Started](docs/QUICKSTART.md)** • **[Documentation](docs/README_GOAL_AGENT.md)** • **[API Reference](#mcp-tools-reference)**

Made with ❤️ for developers who want AI-powered workflow automation

</div>