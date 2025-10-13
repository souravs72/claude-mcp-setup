# mcpctl - Interactive CLI Toolkit

**mcpctl** is a unified command-line interface for managing MCP servers locally and in CI/CD environments.

## Installation

### Quick Install

```bash
# Install in development mode (recommended for local development)
pip install -e .

# Or install normally
pip install .

# Or install with all dependencies
pip install -e ".[all]"
```

### Verify Installation

```bash
mcpctl --version
mcpctl --help
```

## Commands

### `mcpctl start`

Validates server configuration and checks if servers are ready to run.

**Note:** MCP servers are automatically started by Claude Desktop via stdio protocol. This command validates your configuration without actually starting servers as background processes.

```bash
# Check configuration
mcpctl start

# Only check configuration without displaying startup info
mcpctl start --check-only
```

**What it checks:**
- ✓ Server files exist
- ✓ Environment variables are configured
- ✓ Redis is running (for Memory Cache Server)
- ✓ Dependencies are installed

---

### `mcpctl stop`

Stops all running MCP server processes (useful for development/testing).

```bash
# Stop all servers gracefully
mcpctl stop
```

**Features:**
- Finds all running MCP server processes
- Attempts graceful shutdown (SIGTERM)
- Force kills if necessary after timeout
- Shows detailed progress

---

### `mcpctl status`

Lists all running MCP servers with detailed status information.

```bash
# Basic status
mcpctl status

# Detailed status with log file info
mcpctl status --verbose
mcpctl status -v
```

**Output includes:**
- Server name and PID
- Uptime (minutes and seconds)
- Log file location and size (verbose mode)
- Redis status (verbose mode)

---

### `mcpctl logs`

View and tail logs for specific servers.

```bash
# View last 50 lines of GitHub server logs
mcpctl logs github

# Follow logs in real-time (like tail -f)
mcpctl logs github --follow
mcpctl logs github -f

# View last 100 lines
mcpctl logs github --lines 100
mcpctl logs github -n 100

# View logs for all servers
mcpctl logs --all
mcpctl logs -a
```

**Available server names:**
- `memory-cache` - Memory Cache Server
- `goal-agent` - Goal Agent Server
- `internet` - Internet Server
- `github` - GitHub Server
- `frappe` - Frappe Server
- `jira` - Jira Server

---

### `mcpctl test`

Runs quick integration checks on all servers.

```bash
# Run all tests
mcpctl test

# Show detailed test output
mcpctl test --verbose
mcpctl test -v

# Custom timeout per server (default: 3s)
mcpctl test --timeout 5
mcpctl test -t 5
```

**What it tests:**
- Server script execution
- Import validation
- Basic startup checks
- Error detection

**Output:**
- ✓ OK - Server started successfully
- ✗ FAIL - Server failed to start
- Detailed logs saved to `logs/test_results/`

---

### `mcpctl config`

Shows current configuration and environment status.

```bash
mcpctl config
```

**Displays:**
- Project paths
- Available servers
- Environment variable status
- Redis connection status

---

### `mcpctl restart`

Restarts a specific server (stops if running, ready for Claude to restart).

```bash
# Restart GitHub server
mcpctl restart github

# Restart Memory Cache server
mcpctl restart memory-cache
```

---

## Common Workflows

### Initial Setup

```bash
# 1. Install mcpctl
pip install -e .

# 2. Check configuration
mcpctl start

# 3. Run integration tests
mcpctl test

# 4. View current status
mcpctl status
```

### Development

```bash
# Check what's running
mcpctl status -v

# View logs during development
mcpctl logs github -f

# Test changes
mcpctl test

# Restart specific server
mcpctl restart github
```

### Debugging

```bash
# Check configuration
mcpctl config

# View recent logs
mcpctl logs github -n 100

# View all server logs
mcpctl logs --all

# Test all servers
mcpctl test -v
```

### CI/CD Integration

```bash
# Validate configuration
mcpctl start --check-only || exit 1

# Run integration tests
mcpctl test || exit 1

# Check status
mcpctl status
```

---

## Environment Variables

mcpctl automatically loads environment variables from `.env` file in the project root.

### Required Variables by Server

**Memory Cache Server:**
- `REDIS_HOST` (default: localhost)
- `REDIS_PORT` (default: 6379)

**Internet Server:**
- `GOOGLE_API_KEY`
- `GOOGLE_SEARCH_ENGINE_ID`

**GitHub Server:**
- `GITHUB_PERSONAL_ACCESS_TOKEN`

**Frappe Server:**
- `FRAPPE_SITE_URL`
- `FRAPPE_API_KEY`
- `FRAPPE_API_SECRET`

**Jira Server:**
- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`

**Goal Agent Server:**
- No environment variables required

---

## Log Files

Logs are stored in `logs/` directory:

```
logs/
├── memory_cache_server.log
├── goal_agent_server.log
├── internet_server.log
├── github_server.log
├── frappe_server.log
├── jira_server.log
└── test_results/
    ├── Memory_Cache_Server.log
    ├── Goal_Agent_Server.log
    ├── Internet_Server.log
    ├── GitHub_Server.log
    ├── Frappe_Server.log
    └── Jira_Server.log
```

---

## Examples

### Example 1: Daily Development

```bash
# Morning - check what's running
mcpctl status

# Start working on GitHub integration
mcpctl logs github -f

# In another terminal, make changes and test
mcpctl restart github
```

### Example 2: Troubleshooting

```bash
# Server not working? Check config
mcpctl config

# Check if Redis is running
mcpctl status -v

# View error logs
mcpctl logs github -n 200

# Run full test suite
mcpctl test -v
```

### Example 3: CI/CD Pipeline

```yaml
# .github/workflows/test.yml
- name: Validate MCP Configuration
  run: mcpctl start --check-only

- name: Run Integration Tests
  run: mcpctl test

- name: Check Server Status
  run: mcpctl status
```

---

## Troubleshooting

### "mcpctl: command not found"

```bash
# Reinstall in development mode
pip install -e .

# Or add to PATH
export PATH="$PATH:$(pwd)/mcp-env/bin"
```

### "psutil not installed"

```bash
# Install psutil
pip install psutil

# Or reinstall with all dependencies
pip install -e ".[all]"
```

### "Redis not running"

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

### Servers not showing in status

MCP servers are managed by Claude Desktop and run via stdio protocol. They won't appear as background processes unless manually started for testing.

---

## Advanced Usage

### Custom Log Analysis

```bash
# Find errors in all logs
for server in memory-cache goal-agent internet github frappe jira; do
    echo "=== $server ==="
    mcpctl logs $server | grep -i error
done

# Monitor multiple servers
watch -n 2 'mcpctl status -v'
```

### Scripting with mcpctl

```bash
#!/bin/bash
# health-check.sh

echo "Running MCP health check..."

if ! mcpctl start --check-only; then
    echo "Configuration check failed!"
    exit 1
fi

if ! mcpctl test; then
    echo "Integration tests failed!"
    exit 1
fi

echo "All checks passed!"
mcpctl status
```

---

## Features

✅ **Unified Interface** - Single command for all MCP operations  
✅ **Color Output** - Easy-to-read colored terminal output  
✅ **Process Management** - Start, stop, and restart servers  
✅ **Log Management** - View and tail logs with ease  
✅ **Integration Tests** - Quick validation of all servers  
✅ **Status Monitoring** - Real-time server status  
✅ **CI/CD Ready** - Perfect for automation pipelines  
✅ **Environment Validation** - Checks all required variables  
✅ **Redis Integration** - Monitors Redis status  

---

## Related Documentation

- [Quick Start Guide](QUICKSTART.md) - Getting started with MCP servers
- [Configuration Guide](CONFIGURATION.md) - Setting up Claude Desktop
- [Goal Agent README](README_GOAL_AGENT.md) - Goal Agent documentation
- [Main README](README.md) - Project overview

---

## Support

For issues or questions:
1. Check logs with `mcpctl logs <server> -v`
2. Validate configuration with `mcpctl config`
3. Run tests with `mcpctl test -v`
4. Review documentation in the `docs/` directory

---

**Version:** 1.0.0  
**License:** MIT

