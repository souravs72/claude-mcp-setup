# Setup Guide

## Prerequisites

- Python 3.10+
- Git
- Redis server
- PostgreSQL (optional, for goal tracking)

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/souravs72/claude-mcp-setup.git
cd claude-mcp-setup
```

### 2. Create Virtual Environment
```bash
python -m venv mcp-env
source mcp-env/bin/activate  # On Windows: mcp-env\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Services

**Redis (Required)**
```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Windows
# Download from https://redis.io/download
```

**PostgreSQL (Optional)**
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# macOS
brew install postgresql
brew services start postgresql

# Windows
# Download from https://www.postgresql.org/download/
```

### 5. Configure Credentials
```bash
cp config/mcp_settings.json.template config/mcp_settings.json
nano config/mcp_settings.json
```

**Required API Keys:**
- GitHub Personal Access Token
- Jira API Token (if using Jira)
- Google API Key (if using web search)

### 6. Start Servers
```bash
make start
```

### 7. Verify Setup
```bash
make status
```

## Troubleshooting

**Port conflicts?** Check if ports 8000-8007 are available:
```bash
netstat -tulpn | grep :800
```

**Redis connection issues?**
```bash
redis-cli ping
# Should return "PONG"
```

**Permission errors?** Ensure your user has access to the project directory:
```bash
chmod -R 755 /path/to/claude-mcp-setup
```

## Next Steps

1. Test individual servers: `python servers/github_server.py`
2. Check logs: `tail -f logs/*.log`
3. Use with Claude Desktop or your MCP client
