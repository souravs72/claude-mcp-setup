# How to Start MCP Servers

## Important: MCP Architecture

MCP (Model Context Protocol) servers are **not traditional background services**. They:

1. Use **stdio** (standard input/output) for communication
2. Run as **child processes** of Claude Desktop
3. **Cannot run independently** as daemons
4. Need Claude Desktop to provide stdin/stdout pipes

## The Dashboard Cannot Start Servers Independently

When you click "Start All" in the dashboard:
- Servers will initialize but **immediately exit**
- This is **normal behavior** - they need Claude Desktop's stdio pipes
- The dashboard shows this to help with testing, but servers won't stay running

## How to Properly Start MCP Servers

### Method 1: Start Claude Desktop (Recommended)

1. **Configure** servers in Claude Desktop config:
   - Linux: `~/.config/Claude/claude_desktop_config.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. **Restart Claude Desktop** completely (quit and reopen)

3. Servers will start automatically and show as "running" in the dashboard

### Method 2: Test Servers Independently (Testing Only)

For testing without Claude Desktop:

```bash
# Test individual server
python servers/memory_cache_server.py

# The server will start and wait for input
# Press Ctrl+C to stop
```

## Checking Server Status

Use the **Dashboard** at http://localhost:8000:

- If **Claude Desktop is open**: Servers show as "running" with PID
- If **Claude Desktop is closed**: Servers show as "stopped"

## Summary

✅ **To run MCP servers**: Open Claude Desktop  
❌ **Dashboard "Start" button**: Will not keep servers running  
✅ **Dashboard "Stop" button**: Works to kill running servers  
✅ **Dashboard monitoring**: Shows real server status  
