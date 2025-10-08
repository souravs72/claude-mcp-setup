# Quick Start Guide - Goal-Based AI Agent

## 5-Minute Setup

### Step 1: Install Dependencies

```bash
cd your-project-directory

# Install all requirements
pip install -r requirements/goal_agent_requirements.txt
pip install -r requirements/jira_requirements.txt
pip install -r requirements/github_requirements.txt
pip install -r requirements/frappe_requirements.txt
pip install -r requirements/internet_requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit .env file with your credentials
nano .env  # or use your preferred editor
```

Required values:
```bash
# Jira (get from https://id.atlassian.com/manage-profile/security/api-tokens)
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=your_jira_token
JIRA_PROJECT_KEY=PROJ

# GitHub (get from https://github.com/settings/tokens)
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token

# Google Search (optional - for internet server)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Frappe (if using)
FRAPPE_SITE_URL=http://127.0.0.1:8005
FRAPPE_API_KEY=your_frappe_key
FRAPPE_API_SECRET=your_frappe_secret
```

### Step 3: Start Servers

```bash
# Start all servers at once
python scripts/start_all_servers.py

# Or start individually
python servers/goal_agent_server.py &
python servers/jira_server.py &
python servers/github_server.py &
```

### Step 4: Configure Claude Desktop

Edit `claude_desktop_config.json` (location varies by OS):
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Add:
```json
{
  "mcpServers": {
    "goal-agent": {
      "command": "python",
      "args": ["/full/path/to/your/servers/goal_agent_server.py"]
    },
    "jira": {
      "command": "python",
      "args": ["/full/path/to/your/servers/jira_server.py"],
      "env": {
        "JIRA_BASE_URL": "https://your-domain.atlassian.net",
        "JIRA_EMAIL": "your@email.com",
        "JIRA_API_TOKEN": "your_token",
        "JIRA_PROJECT_KEY": "PROJ"
      }
    },
    "github": {
      "command": "python",
      "args": ["/full/path/to/your/servers/github_server.py"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token"
      }
    }
  }
}
```

### Step 5: Restart Claude Desktop

Close and reopen Claude Desktop app.

## First Goal in 2 Minutes

Once configured, try this in Claude:

```
You: "Create a goal to add a new API endpoint for user profiles."

Claude: [Uses create_goal tool]
Created GOAL-1: Add API endpoint for user profiles

You: "Break this down into tasks across my backend and frontend repos."

Claude: [Uses break_down_goal tool]
Created 5 tasks:
- TASK-1: Design API schema (backend)
- TASK-2: Implement endpoint (backend, depends on TASK-1)
- TASK-3: Add tests (backend, depends on TASK-2)
- TASK-4: Update frontend to call endpoint (frontend, depends on TASK-2)
- TASK-5: Update API documentation (depends on TASK-2)

You: "Show me the execution plan and create Jira tickets."

Claude: [Uses generate_execution_plan and jira_create_issue tools]
Execution Plan:
- Phase 1: TASK-1 (start immediately)
- Phase 2: TASK-2, TASK-3 (parallel after Phase 1)
- Phase 3: TASK-4, TASK-5 (parallel after Phase 2)

Created Jira tickets:
- PROJ-101: Design API schema
- PROJ-102: Implement endpoint
- PROJ-103: Add tests
- PROJ-104: Update frontend
- PROJ-105: Update documentation
```

## Common Commands

### Check Server Status
```bash
# View logs
tail -f logs/goal_agent_server.log
tail -f logs/jira_server.log

# Check if servers are running
ps aux | grep server.py
```

### Stop Servers
```bash
# Stop all servers
python scripts/stop_all_servers.py

# Or manually
pkill -f goal_agent_server.py
pkill -f jira_server.py
```

### Troubleshooting

**Problem**: "Jira client not initialized"
```bash
# Check your .env file has correct values
cat .env | grep JIRA

# Test Jira connection manually
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('URL:', os.getenv('JIRA_BASE_URL'))
print('Email:', os.getenv('JIRA_EMAIL'))
print('Token:', 'Set' if os.getenv('JIRA_API_TOKEN') else 'Not set')
"
```

**Problem**: "GitHub client not initialized"
```bash
# Verify token
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('Token:', 'Set' if os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN') else 'Not set')
"
```

**Problem**: Servers not appearing in Claude
1. Check Claude Desktop config file path
2. Restart Claude Desktop completely
3. Check server logs for errors
4. Verify full absolute paths in config

## Next Steps

- Read [README_GOAL_AGENT.md](README_GOAL_AGENT.md) for detailed usage
- Try the example workflows
- Customize task types for your workflow
- Integrate with your CI/CD pipeline

## Support

For issues:
1. Check server logs in `logs/` directory
2. Verify environment variables
3. Test each server individually
4. Check Claude Desktop configuration

Happy goal crushing! 🎯