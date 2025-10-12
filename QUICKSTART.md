# Quick Start Guide

Get Claude MCP servers running in **under 10 minutes**.

## Prerequisites Checklist

- [ ] Python 3.10 or higher (`python --version`)
- [ ] Redis installed (or Docker available)
- [ ] Claude Desktop installed
- [ ] Git installed

## Step 1: Install Dependencies (2 minutes)

```bash
# Clone repository
git clone <your-repo-url>
cd claude-mcp-setup

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies and CLI tool
pip install -e .[all]

# Verify installation
python -c "import mcp, redis, github; print('✓ All packages installed')"
mcpctl --version  # Should show: mcpctl version 1.0.0
```

## Step 2: Start Redis (1 minute)

Redis is required for the Memory Cache server.

### macOS (Homebrew)
```bash
brew install redis
brew services start redis

# Verify
redis-cli ping  # Should return: PONG
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Verify
redis-cli ping  # Should return: PONG
```

### Docker (All platforms)
```bash
docker run -d -p 6379:6379 --name redis redis:alpine

# Verify
docker exec redis redis-cli ping  # Should return: PONG
```

### Windows
```bash
# Download from: https://github.com/microsoftarchive/redis/releases
# Or use WSL2 with Linux instructions above
```

## Step 3: Configure Environment (2 minutes)

```bash
# Copy example configuration
cp .env.example .env

# Edit .env file
nano .env
```

### Minimum Configuration

For **basic functionality** (Goal Agent + Memory Cache):

```bash
# .env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

That's it! Goal Agent and Memory Cache work without external APIs.

### Optional: GitHub Integration

Get token: https://github.com/settings/tokens (scopes: `repo`, `workflow`)

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
GITHUB_DEFAULT_BRANCH=main
```

### Optional: Jira Integration

Get token: https://id.atlassian.com/manage-profile/security/api-tokens

```bash
JIRA_BASE_URL=https://your-company.atlassian.net
JIRA_EMAIL=your@email.com
JIRA_API_TOKEN=your_token_here
JIRA_PROJECT_KEY=PROJ
```

### Optional: Google Search

1. Enable API: https://console.cloud.google.com/apis/library/customsearch.googleapis.com
2. Create Search Engine: https://programmablesearchengine.google.com/

```bash
GOOGLE_API_KEY=your_key_here
GOOGLE_SEARCH_ENGINE_ID=your_id_here
```

### Optional: Frappe/ERPNext

```bash
FRAPPE_SITE_URL=http://127.0.0.1:8005
FRAPPE_API_KEY=your_key
FRAPPE_API_SECRET=your_secret
```

## Step 4: Test Configuration (1 minute)

```bash
# NEW: Use mcpctl for validation (recommended)
mcpctl config       # View detailed configuration
mcpctl start        # Validate all servers
mcpctl test         # Run integration tests

# Expected output:
# ✓ Server Files: All 6 found
# ✓ Redis: Running
# ✓ Environment: All variables configured
```

**Alternative (old method):**
```bash
python scripts/start_all_servers.py
```

If you see errors, check:
- Redis is running: `redis-cli ping` or `mcpctl config`
- Python version: `python --version` (need 3.10+)
- Dependencies installed: `pip list | grep mcp`
- Run: `mcpctl config` for detailed diagnostics

## Step 5: Configure Claude Desktop (2 minutes)

### Find Config File

**macOS:**
```bash
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```bash
notepad %APPDATA%\Claude\claude_desktop_config.json
```

### Add MCP Server Configuration

**IMPORTANT:** Use **absolute paths** (not relative).

Get your project path:
```bash
pwd  # Copy this output
```

Replace `/absolute/path/to/your/project` with the output from `pwd`:

```json
{
  "mcpServers": {
    "memory-cache": {
      "command": "python",
      "args": ["/absolute/path/to/your/project/servers/memory_cache_server.py"],
      "env": {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "0"
      }
    },
    "goal-agent": {
      "command": "python",
      "args": ["/absolute/path/to/your/project/servers/goal_agent_server.py"],
      "env": {
        "GOAL_AGENT_MAX_WORKERS": "10",
        "CACHE_ENABLED": "true"
      }
    }
  }
}
```

### Optional: Add GitHub Server

```json
{
  "mcpServers": {
    "memory-cache": { "..." },
    "goal-agent": { "..." },
    "github": {
      "command": "python",
      "args": ["/absolute/path/to/your/project/servers/github_server.py"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token",
        "GITHUB_DEFAULT_BRANCH": "main"
      }
    }
  }
}
```

### Optional: Add Jira Server

```json
{
  "mcpServers": {
    "memory-cache": { "..." },
    "goal-agent": { "..." },
    "jira": {
      "command": "python",
      "args": ["/absolute/path/to/your/project/servers/jira_server.py"],
      "env": {
        "JIRA_BASE_URL": "https://company.atlassian.net",
        "JIRA_EMAIL": "dev@company.com",
        "JIRA_API_TOKEN": "your_token",
        "JIRA_PROJECT_KEY": "PROJ"
      }
    }
  }
}
```

## Step 6: Restart Claude Desktop (1 minute)

**IMPORTANT:** Full restart required (not just refresh)

1. **Quit Claude Desktop completely**
   - macOS: Cmd+Q
   - Windows: File → Exit
   - Linux: Close all windows

2. **Verify it's closed**
   ```bash
   # macOS/Linux
   ps aux | grep Claude  # Should show nothing
   
   # Windows (PowerShell)
   Get-Process | Where-Object {$_.Name -like "*Claude*"}
   ```

3. **Restart Claude Desktop**
   - Launch from Applications/Start Menu

4. **Wait 10 seconds** for servers to initialize

## Step 7: Verify Installation (2 minutes)

### Command Line Verification

```bash
# Check if servers are running
mcpctl status

# View server logs
mcpctl logs --all

# Run integration tests
mcpctl test

# Expected:
# ✓ All servers responding
# ✓ Tests passing
```

### Claude Desktop Tests

Open Claude Desktop and try these tests:

### Test 1: Memory Cache

```
Store "hello world" in cache with key "test"
```

**Expected Response:**
```
✓ Successfully cached
Key: test
Value: hello world
```

### Test 2: Goal Agent

```
Create a goal to test the system
```

**Expected Response:**
```
✓ Created GOAL-0001: Test the system
Status: planned
Priority: medium
```

### Test 3: Cache + Goal Integration

```
Get the goal I just created from cache
```

**Expected Response:**
```
✓ Retrieved GOAL-0001 from cache
Description: Test the system
...
```

### Test 4: GitHub (if configured)

```
List my repositories
```

**Expected Response:**
```
✓ Found X repositories
- repo1 (stars: Y, forks: Z)
- repo2 ...
```

### Test 5: Jira (if configured)

```
Show my Jira projects
```

**Expected Response:**
```
✓ Found X projects
- PROJ: Project Name
- ...
```

## 🎉 Success!

You're now ready to use Claude with MCP servers. Try:

```
Create a goal to build a REST API with authentication
```

Claude will:
1. Create a goal
2. Cache it automatically
3. Be ready to break it down into tasks

## 🔍 Troubleshooting

### Quick Diagnostics with mcpctl

```bash
# 1. Check configuration
mcpctl config      # Shows all settings and env vars

# 2. Validate servers
mcpctl start       # Checks all prerequisites

# 3. Run tests
mcpctl test -v     # Detailed test output

# 4. Check status
mcpctl status -v   # Shows running servers

# 5. View logs
mcpctl logs --all  # All server logs
```

### Servers Not Appearing in Claude

**Symptom:** Claude says "I don't have access to..."

**Solutions:**
```bash
# 1. Quick check with mcpctl
mcpctl config      # Verify all paths and env vars
mcpctl status      # Check if servers are running

# 2. Check paths are absolute
grep "servers/" ~/Library/Application\ Support/Claude/claude_desktop_config.json
# All paths must start with / not ./

# 3. Check Claude Desktop fully restarted
ps aux | grep Claude  # macOS/Linux
# Should show process with recent start time

# 4. Check server files exist
mcpctl start       # Will show missing files

# 5. Check logs
mcpctl logs github -f     # Follow logs in real-time
mcpctl logs goal-agent    # View recent logs
```

### Redis Connection Errors

**Symptom:** "Redis connection refused" or "Cache client not initialized"

**Solutions:**
```bash
# 1. Quick check with mcpctl
mcpctl config      # Shows Redis status

# 2. Verify Redis is running
redis-cli ping
# Should return: PONG

# 3. Check Redis port
redis-cli -p 6379 ping
# Change port in .env if needed

# 4. View cache server logs
mcpctl logs memory-cache -f

# 5. Check Redis logs
tail -f /usr/local/var/log/redis.log  # macOS
journalctl -u redis  # Linux
docker logs redis  # Docker
```

### Import Errors

**Symptom:** "ModuleNotFoundError: No module named 'mcp'"

**Solutions:**
```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Reinstall dependencies
pip install -r requirements.txt

# 3. Verify installation
python -c "import mcp; print('OK')"

# 4. Check Python version
python --version  # Must be 3.10+
```

### Authentication Errors

**Symptom:** "Authentication failed" for GitHub/Jira

**Solutions:**

**GitHub:**
```bash
# 1. Verify token format
echo $GITHUB_PERSONAL_ACCESS_TOKEN
# Should start with ghp_ or github_pat_

# 2. Check token scopes
# Visit: https://github.com/settings/tokens
# Ensure: repo, workflow checked

# 3. Test token manually
curl -H "Authorization: token $GITHUB_PERSONAL_ACCESS_TOKEN" \
  https://api.github.com/user
```

**Jira:**
```bash
# 1. Verify credentials
echo $JIRA_BASE_URL
echo $JIRA_EMAIL
# Base URL should not have trailing /

# 2. Test token manually
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/3/myself"
```

### Server Logs Show Errors

**Check logs:**
```bash
# View all errors
grep -i error logs/*.log

# View specific server
tail -f logs/goal_agent_server.log

# Check for startup issues
head -20 logs/memory_cache_server.log
```

**Common fixes:**
- Configuration errors → Check .env file
- Port conflicts → Change ports in config
- Permission errors → Check file permissions

## 📊 What's Running

After setup, you should have:

```bash
# Check processes
ps aux | grep "server.py"

# Expected output:
python servers/memory_cache_server.py
python servers/goal_agent_server.py
# Plus any optional servers (github, jira, etc.)

# Check Redis
redis-cli info clients
# Should show connected_clients > 0
```

## 🚀 Next Steps

Now that everything is working:

1. **Read the full documentation**
   - [README.md](README.md) - System architecture
   - [CONFIGURATION.md](CONFIGURATION.md) - Advanced config
   - [README_GOAL_AGENT.md](README_GOAL_AGENT.md) - API reference

2. **Try real examples**
   ```
   Create a goal to add OAuth authentication to our API
   Break it down into 7 tasks
   Show me the execution plan
   Create a GitHub branch for task 1
   ```

3. **Explore integrations**
   - Set up GitHub for code management
   - Connect Jira for ticket tracking
   - Add Frappe if you use ERPNext

4. **Customize configuration**
   - Adjust connection pool sizes
   - Configure rate limiting
   - Tune cache TTLs

## 💡 Pro Tips

1. **Use mcpctl for all operations** - faster and more reliable
2. **Use absolute paths everywhere** in claude_desktop_config.json
3. **Always fully restart Claude Desktop** after config changes
4. **Check logs first** when troubleshooting: `mcpctl logs --all`
5. **Start minimal** (cache + goal agent only) then add integrations
6. **Test Redis separately** before blaming MCP servers

## 📝 Essential mcpctl Commands

```bash
# Configuration & Validation
mcpctl config        # Show all configuration
mcpctl start         # Validate servers
mcpctl test          # Run integration tests

# Monitoring & Status
mcpctl status        # List running servers
mcpctl status -v     # Detailed view with logs

# Log Management
mcpctl logs github -f           # Follow GitHub logs
mcpctl logs memory-cache -n 100 # Last 100 lines
mcpctl logs --all               # All server logs

# Server Management
mcpctl stop          # Stop all servers
mcpctl restart github # Restart specific server
```

## 📝 Other Useful Commands

```bash
# Check if Redis is running
redis-cli ping
mcpctl config  # Also shows Redis status

# View server processes
ps aux | grep server.py
mcpctl status  # Better alternative

# Restart Redis (if needed)
brew services restart redis  # macOS
sudo systemctl restart redis  # Linux
docker restart redis  # Docker

# Clear Redis cache (fresh start)
redis-cli FLUSHDB
```

## 🆘 Getting Help

If you're still stuck:

1. Run diagnostics: `mcpctl config` and `mcpctl test -v`
2. Check the [troubleshooting section](#-troubleshooting) above
3. Review logs: `mcpctl logs --all`
4. Verify Redis: `mcpctl config` or `redis-cli ping`
5. Check config: `cat claude_desktop_config.json`
6. Test Python environment: `python -c "import mcp; print('OK')"`

Most issues are due to:
- Relative paths instead of absolute paths
- Claude Desktop not fully restarted
- Redis not running
- Missing environment variables

**Use `mcpctl config` as your first diagnostic tool!**