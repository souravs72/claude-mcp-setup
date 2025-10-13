# mcpctl Quick Reference Card

## Installation

```bash
pip install -e .
```

## Common Commands

### 🚀 Quick Start (NEW!)

| Command                       | Description                           |
| ----------------------------- | ------------------------------------- |
| `mcpctl run`                  | Start all servers + dashboard (Best!) |
| `mcpctl run --dashboard-only` | Start dashboard only                  |
| `mcpctl run --servers-only`   | Start servers only (no dashboard)     |
| `mcpctl stop`                 | Stop all servers                      |

### Basic Operations

| Command            | Description                |
| ------------------ | -------------------------- |
| `mcpctl --version` | Show version               |
| `mcpctl --help`    | Show help                  |
| `mcpctl start`     | Validate configuration     |
| `mcpctl status`    | Check running servers      |
| `mcpctl config`    | Show configuration         |
| `mcpctl dashboard` | Start web dashboard (8000) |

### Testing

| Command            | Description           |
| ------------------ | --------------------- |
| `mcpctl test`      | Run integration tests |
| `mcpctl test -v`   | Verbose test output   |
| `mcpctl test -t 5` | Custom timeout (5s)   |

### Log Management

| Command                       | Description           |
| ----------------------------- | --------------------- |
| `mcpctl logs <server>`        | View last 50 lines    |
| `mcpctl logs <server> -f`     | Follow logs (tail -f) |
| `mcpctl logs <server> -n 100` | Last 100 lines        |
| `mcpctl logs --all`           | All server logs       |

### Status Monitoring

| Command            | Description     |
| ------------------ | --------------- |
| `mcpctl status`    | Basic status    |
| `mcpctl status -v` | Detailed status |

### Server Management

| Command                   | Description             |
| ------------------------- | ----------------------- |
| `mcpctl restart <server>` | Restart specific server |

## Server Names

- `memory-cache` - Memory Cache Server (Redis)
- `goal-agent` - Goal Agent Server
- `internet` - Internet Server (Google Search)
- `github` - GitHub Server
- `frappe` - Frappe Server (ERP)
- `jira` - Jira Server

## Examples

### Setup & Validation

```bash
# Initial setup
pip install -e .
mcpctl config
mcpctl start

# Run tests
mcpctl test
mcpctl status
```

### Daily Development (Easy Way - NEW!)

```bash
# Start everything with one command
mcpctl run

# Dashboard opens at http://localhost:8000
# Press CTRL+C to stop dashboard (servers keep running)

# Stop servers when done
mcpctl stop
```

### Daily Development (Traditional Way)

```bash
# Start web dashboard separately
mcpctl dashboard

# Check what's running
mcpctl status -v

# View logs
mcpctl logs github -f

# Restart server
mcpctl restart github
```

### Debugging

```bash
# Check configuration
mcpctl config

# View recent errors
mcpctl logs github -n 200

# Run verbose tests
mcpctl test -v

# Check all logs
mcpctl logs --all
```

### CI/CD

```bash
# Validate config
mcpctl start --check-only || exit 1

# Run tests
mcpctl test || exit 1

# Check status
mcpctl status
```

## Output Colors

- 🟢 **Green (✓)** - Success
- 🔴 **Red (✗)** - Error/Failure
- 🟡 **Yellow (⚠)** - Warning
- 🔵 **Cyan (ℹ)** - Information

## Tips

1. **Use verbose mode** for debugging: `-v` or `--verbose`
2. **Follow logs** in real-time: `-f` or `--follow`
3. **Check config first** when troubleshooting: `mcpctl config`
4. **Test after changes**: `mcpctl test`
5. **View all logs** to spot patterns: `mcpctl logs --all`

## Keyboard Shortcuts

- `Ctrl+C` - Stop following logs or cancel operation
- `Ctrl+D` - Exit (in some contexts)

## Environment Variables

mcpctl loads from `.env` file in project root. Use `mcpctl config` to verify.

## Log Locations

```
logs/
├── memory_cache_server.log
├── goal_agent_server.log
├── internet_server.log
├── github_server.log
├── frappe_server.log
└── jira_server.log
```

## Common Issues

### "mcpctl: command not found"

```bash
pip install -e .
# Or add to PATH
export PATH="$PATH:./mcp-env/bin"
```

### "psutil not installed"

```bash
pip install psutil
```

### "Redis not running"

```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

## For More Info

- Full Guide: [MCPCTL_GUIDE.md](MCPCTL_GUIDE.md)
- Project README: [README.md](README.md)
- Quick Start: [QUICKSTART.md](QUICKSTART.md)
