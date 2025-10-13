# Getting Started with MCP Servers

Complete setup guide to get Claude MCP servers running in **under 15 minutes**.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Setup (Automated)](#quick-setup-automated)
3. [Manual Setup](#manual-setup)
4. [Docker Setup](#docker-setup)
5. [Configuration](#configuration)
6. [Starting Servers](#starting-servers)
7. [Verification](#verification)
8. [Next Steps](#next-steps)

---

## Prerequisites

### Required

- **Python 3.10+** - Check version: `python --version` or `python3 --version`
- **PostgreSQL 12+** - For Goal Agent persistence
- **Claude Desktop** - Download from https://claude.ai/download
- **Git** - For cloning the repository

### Optional but Recommended

- **Redis 5.0+** - For caching (improves performance by ~50%)
- **Docker** - For containerized PostgreSQL/Redis
- **make** - For using Makefile commands

### API Keys (Optional, configure later)

- GitHub token (for GitHub integration)
- Jira API token (for Jira integration)
- Google API keys (for web search)
- Frappe credentials (for ERP integration)

---

## Quick Setup (Automated)

The fastest way to get started:

```bash
# 1. Clone repository
git clone https://github.com/your-org/claude-mcp-setup.git
cd claude-mcp-setup

# 2. Run automated setup (installs everything)
make setup

# This will:
# - Create virtual environment
# - Install all Python dependencies
# - Setup PostgreSQL database
# - Install mcpctl CLI tool
# - Create configuration templates

# 3. Configure your API tokens (optional, can skip for now)
nano config/mcp_settings.json

# 4. Start all servers
make start

# 5. Verify
make status
```

**That's it!** Skip to [Verification](#verification) section.

---

## Manual Setup

If you prefer step-by-step control:

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/claude-mcp-setup.git
cd claude-mcp-setup
```

### Step 2: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv mcp-env

# Activate it
source mcp-env/bin/activate  # Linux/macOS
# OR
mcp-env\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -e .[all]
```

### Step 3: Setup PostgreSQL

#### Option A: Local PostgreSQL

```bash
# macOS (Homebrew)
brew install postgresql@14
brew services start postgresql@14
createdb mcp_goals

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo -u postgres createdb mcp_goals

# Create user (optional)
sudo -u postgres psql -c "CREATE USER mcp_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE mcp_goals TO mcp_user;"
```

#### Option B: Docker PostgreSQL

```bash
# Start PostgreSQL in Docker
docker run -d \
  --name mcp-postgres \
  -e POSTGRES_DB=mcp_goals \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:14-alpine

# Verify
docker exec mcp-postgres psql -U postgres -d mcp_goals -c "SELECT 1;"
```

#### Option C: Use Docker Compose (Easiest)

```bash
# Start PostgreSQL and Redis together
docker-compose up -d postgres redis

# Check status
docker-compose ps
```

### Step 4: Initialize Database

```bash
# The database will be auto-initialized on first run
# Or manually initialize:
python scripts/init_database.py
```

### Step 5: Setup Redis (Optional)

```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Linux (Ubuntu/Debian)
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Docker
docker run -d --name mcp-redis -p 6379:6379 redis:7-alpine

# Verify
redis-cli ping  # Should return: PONG
```

### Step 6: Configure Settings

```bash
# Copy template
cp config/mcp_settings.json.template config/mcp_settings.json

# Edit configuration
nano config/mcp_settings.json
```

Minimum configuration:

```json
{
  "mcpServers": {
    "goal-agent": {
      "command": "python",
      "args": ["-m", "servers.goal_agent_server"],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "mcp_goals",
        "DB_USER": "postgres",
        "DB_PASSWORD": "postgres",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379"
      }
    },
    "memory-cache": {
      "command": "python",
      "args": ["-m", "servers.memory_cache_server"],
      "env": {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "0"
      }
    }
  }
}
```

---

## Docker Setup

Complete containerized setup using Docker Compose:

### Step 1: Review docker-compose.yml

```yaml
# docker-compose.yml includes:
# - PostgreSQL 14
# - Redis 7
# - All MCP servers
# - Persistent volumes
```

### Step 2: Configure Environment

```bash
# Create .env file for Docker
cat > .env << 'EOF'
# Database
DB_HOST=postgres
DB_PORT=5432
DB_NAME=mcp_goals
DB_USER=postgres
DB_PASSWORD=postgres

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Optional: API Keys
GITHUB_TOKEN=your_token_here
JIRA_API_TOKEN=your_token_here
JIRA_SERVER_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=your-email@example.com
EOF
```

### Step 3: Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f goal-agent
```

### Step 4: Access Services

```bash
# PostgreSQL
docker exec -it mcp-postgres psql -U postgres -d mcp_goals

# Redis
docker exec -it mcp-redis redis-cli

# Dashboard
open http://localhost:8000
```

### Docker Management

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Restart specific service
docker-compose restart goal-agent

# View resource usage
docker stats

# Clean up
docker-compose down --rmi all --volumes
```

---

## Configuration

### Claude Desktop Configuration

Add MCP servers to Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "goal-agent": {
      "command": "/path/to/mcp-env/bin/python",
      "args": ["-m", "servers.goal_agent_server"],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "mcp_goals",
        "DB_USER": "postgres",
        "DB_PASSWORD": "postgres"
      }
    },
    "github": {
      "command": "/path/to/mcp-env/bin/python",
      "args": ["-m", "servers.github_server"],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    },
    "jira": {
      "command": "/path/to/mcp-env/bin/python",
      "args": ["-m", "servers.jira_server"],
      "env": {
        "JIRA_API_TOKEN": "your_token_here",
        "JIRA_SERVER_URL": "https://your-domain.atlassian.net",
        "JIRA_USER_EMAIL": "your-email@example.com"
      }
    },
    "internet": {
      "command": "/path/to/mcp-env/bin/python",
      "args": ["-m", "servers.internet_server"],
      "env": {
        "GOOGLE_API_KEY": "your_api_key",
        "GOOGLE_SEARCH_ENGINE_ID": "your_search_engine_id"
      }
    },
    "memory-cache": {
      "command": "/path/to/mcp-env/bin/python",
      "args": ["-m", "servers.memory_cache_server"],
      "env": {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379"
      }
    }
  }
}
```

### Environment Variables Reference

See [CONFIGURATION.md](CONFIGURATION.md) for complete reference.

---

## Starting Servers

### Method 1: Using Makefile (Recommended)

```bash
# Start all servers
make start

# Start specific server
make start-goal-agent

# Check status
make status

# View logs
make logs

# Stop all servers
make stop
```

### Method 2: Using mcpctl

```bash
# Start all servers
mcpctl start

# Start specific server
mcpctl server start goal-agent

# Check status
mcpctl status

# View logs
mcpctl logs goal-agent --follow
```

### Method 3: Using Docker Compose

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d goal-agent
```

### Method 4: Manual Start

```bash
# Activate virtual environment
source mcp-env/bin/activate

# Start servers individually
python -m servers.goal_agent_server &
python -m servers.github_server &
python -m servers.jira_server &
python -m servers.internet_server &
python -m servers.memory_cache_server &
python -m servers.dashboard_server &

# View process IDs
ps aux | grep "servers\."
```

---

## Verification

### 1. Check Server Status

```bash
# Using mcpctl
mcpctl status

# Expected output:
# ✓ goal-agent     [running]  PID: 12345
# ✓ github         [running]  PID: 12346
# ✓ jira           [running]  PID: 12347
# ✓ internet       [running]  PID: 12348
# ✓ memory-cache   [running]  PID: 12349
# ✓ dashboard      [running]  PID: 12350
```

### 2. Test Goal Agent

```bash
# Create a test goal
mcpctl goal create "Test Goal" "Testing the system"

# List goals
mcpctl goal list

# Should see:
# GOAL-001 | Test Goal | pending
```

### 3. Test PostgreSQL Connection

```bash
# Check database
psql -d mcp_goals -U postgres -c "SELECT COUNT(*) FROM goals;"

# Should return: 1 (or more if you created multiple goals)
```

### 4. Test Redis Connection (if using)

```bash
# Check Redis
redis-cli ping

# Should return: PONG

# Check keys
redis-cli keys "*"
```

### 5. Access Dashboard

```bash
# Open in browser
open http://localhost:8000

# Or use curl
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "servers": {...}}
```

### 6. Test in Claude Desktop

Open Claude Desktop and try:

```
"Create a goal called 'Test MCP Integration' with the description 'Verify all servers are working correctly'"
```

Claude should respond with confirmation and a goal ID.

---

## Next Steps

### 1. Configure API Integrations

Add your API tokens for full functionality:

```bash
# Edit configuration
nano config/mcp_settings.json

# Add:
# - GITHUB_TOKEN (from https://github.com/settings/tokens)
# - JIRA_API_TOKEN (from your Jira instance)
# - GOOGLE_API_KEY (from Google Cloud Console)
```

See [CONFIGURATION.md](CONFIGURATION.md) for detailed setup instructions.

### 2. Explore Features

```bash
# Try these in Claude:

"Create a goal to build a REST API with 3 tasks"

"List all my goals"

"Show me tasks that are in progress"

"Search for goals tagged with 'backend'"

"Create a GitHub issue for bug fix"

"Search Google for PostgreSQL best practices"
```

### 3. Learn the API

Read [README_GOAL_AGENT.md](README_GOAL_AGENT.md) for complete API reference.

### 4. Monitor Performance

```bash
# View real-time dashboard
open http://localhost:8000

# Check logs
make logs

# Monitor database
watch -n 5 'psql -d mcp_goals -U postgres -c "SELECT COUNT(*) FROM goals;"'
```

### 5. Explore Advanced Features

- **Task Dependencies**: Create complex workflows
- **Batch Operations**: Bulk create/update tasks
- **Tags**: Organize goals and tasks
- **Search**: Full-text search across goals
- **Dashboard**: Real-time monitoring

---

## Common Issues

### PostgreSQL Connection Failed

```bash
# Check if PostgreSQL is running
pg_isready

# Check connection
psql -d mcp_goals -U postgres -c "SELECT 1;"

# If connection refused, check:
# 1. Is PostgreSQL running? sudo systemctl status postgresql
# 2. Is it listening on port 5432? ss -tlnp | grep 5432
# 3. Check pg_hba.conf authentication settings
```

### Redis Connection Failed

```bash
# Check if Redis is running
redis-cli ping

# If connection refused:
redis-server &  # Start Redis in background

# Or using Docker:
docker start mcp-redis
```

### Servers Won't Start

```bash
# Check Python version
python --version  # Must be 3.10+

# Check virtual environment
which python  # Should point to mcp-env/bin/python

# Check dependencies
pip list | grep -E "mcp|psycopg2|redis"

# Reinstall if needed
pip install -e .[all]
```

### Database Tables Don't Exist

```bash
# Initialize database
python scripts/init_database.py

# Or manually:
psql -d mcp_goals -U postgres -f sql/schema.sql
```

For more troubleshooting help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Uninstallation

```bash
# Stop all servers
make stop

# Or
docker-compose down

# Remove virtual environment
rm -rf mcp-env

# Remove data (optional, WARNING: deletes all goals/tasks)
docker-compose down -v  # If using Docker
# OR
psql -d postgres -U postgres -c "DROP DATABASE mcp_goals;"
redis-cli FLUSHALL
```

---

## Getting Help

- **Documentation**: Check [README.md](README.md) and other docs
- **Troubleshooting**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Configuration**: See [CONFIGURATION.md](CONFIGURATION.md)
- **API Reference**: See [README_GOAL_AGENT.md](README_GOAL_AGENT.md)
- **GitHub Issues**: Open an issue on GitHub
- **Logs**: Check `logs/` directory for detailed error messages

---

**You're all set!** Start using Claude with your new MCP servers. 🚀

