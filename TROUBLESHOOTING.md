# Troubleshooting Guide

Common issues and solutions for MCP Servers.

---

## Table of Contents

1. [Server Won't Start](#server-wont-start)
2. [Database Issues](#database-issues)
3. [Redis Issues](#redis-issues)
4. [Claude Desktop Integration](#claude-desktop-integration)
5. [Performance Issues](#performance-issues)
6. [API Integration Issues](#api-integration-issues)
7. [Docker Issues](#docker-issues)
8. [Diagnostic Commands](#diagnostic-commands)

---

## Server Won't Start

### Python Version Issues

**Symptom**: `SyntaxError` or `ModuleNotFoundError`

**Cause**: Python version < 3.10

```bash
# Check Python version
python --version  # or python3 --version

# Should show: Python 3.10.x or higher
```

**Solution**:

```bash
# macOS (Homebrew)
brew install python@3.11

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install python3.11 python3.11-venv

# Update virtual environment
rm -rf mcp-env
python3.11 -m venv mcp-env
source mcp-env/bin/activate
pip install -e .[all]
```

### Missing Dependencies

**Symptom**: `ModuleNotFoundError: No module named 'mcp'`

**Solution**:

```bash
# Ensure virtual environment is activated
source mcp-env/bin/activate  # Linux/macOS
# OR
mcp-env\Scripts\activate     # Windows

# Reinstall dependencies
pip install -e .[all]

# Verify installation
pip list | grep -E "mcp|psycopg2|redis"
```

### Port Already in Use

**Symptom**: `OSError: [Errno 48] Address already in use`

**Solution**:

```bash
# Find process using port 8000 (dashboard)
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port
PORT=8001 python -m servers.dashboard_server
```

### Permission Denied

**Symptom**: `PermissionError: [Errno 13] Permission denied`

**Solution**:

```bash
# Fix file permissions
chmod +x scripts/*.py
chmod +x scripts/*.sh

# Fix directory permissions
chmod 755 logs/
chmod 755 data/

# If database permission issues
sudo chown -R $USER:$USER /path/to/mcp_data
```

---

## Database Issues

### Connection Refused

**Symptom**: `psycopg2.OperationalError: could not connect to server`

**Diagnosis**:

```bash
# Check if PostgreSQL is running
pg_isready

# Check PostgreSQL status
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS

# Check if listening on port 5432
ss -tlnp | grep 5432  # Linux
lsof -i :5432  # macOS
```

**Solution**:

```bash
# Start PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql@14  # macOS
docker start mcp-postgres  # Docker

# If still failing, check logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log  # Linux
tail -f ~/Library/Application\ Support/Postgres/var-14/postgres-server.log  # macOS
docker logs mcp-postgres  # Docker
```

### Authentication Failed

**Symptom**: `FATAL: password authentication failed for user "postgres"`

**Solution**:

```bash
# Check pg_hba.conf authentication settings
sudo nano /etc/postgresql/14/main/pg_hba.conf

# Add or modify this line:
# local   all   postgres   trust
# host    all   all   127.0.0.1/32   md5

# Restart PostgreSQL
sudo systemctl restart postgresql

# Reset password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'newpassword';"

# Update .env or mcp_settings.json with new password
```

### Database Does Not Exist

**Symptom**: `FATAL: database "mcp_goals" does not exist`

**Solution**:

```bash
# Create database
createdb mcp_goals

# Or using psql
sudo -u postgres psql -c "CREATE DATABASE mcp_goals;"

# Initialize schema
python scripts/init_database.py

# Verify
psql -d mcp_goals -c "SELECT COUNT(*) FROM goals;"
```

### Tables Don't Exist

**Symptom**: `relation "goals" does not exist`

**Solution**:

```bash
# Initialize database schema
python scripts/init_database.py

# Or manually run SQL
psql -d mcp_goals -f sql/schema.sql

# Verify tables exist
psql -d mcp_goals -c "\dt"
```

### Connection Pool Exhausted

**Symptom**: `psycopg2.pool.PoolError: connection pool exhausted`

**Solution**:

```python
# In servers/database.py, increase pool size
DB_POOL = psycopg2.pool.ThreadedConnectionPool(
    minconn=10,   # Increase from 5
    maxconn=50,   # Increase from 20
    ...
)
```

---

## Redis Issues

### Connection Refused

**Symptom**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**Diagnosis**:

```bash
# Check if Redis is running
redis-cli ping  # Should return: PONG

# Check Redis process
ps aux | grep redis-server

# Check port
ss -tlnp | grep 6379  # Linux
lsof -i :6379  # macOS
```

**Solution**:

```bash
# Start Redis
redis-server &  # Background mode

# Or using service manager
sudo systemctl start redis  # Linux
brew services start redis  # macOS
docker start mcp-redis  # Docker

# If can't start, check logs
tail -f /var/log/redis/redis-server.log  # Linux
```

### Redis Not Required

**Note**: Redis is optional for caching. System works without it (slightly slower).

```bash
# Disable Redis caching
# In config/mcp_settings.json, remove REDIS_* env vars

# System will fall back to PostgreSQL only
```

### Too Many Connections

**Symptom**: `ERR max number of clients reached`

**Solution**:

```bash
# Increase max clients in redis.conf
redis-cli CONFIG SET maxclients 10000

# Or edit redis.conf permanently
sudo nano /etc/redis/redis.conf
# Add: maxclients 10000

# Restart Redis
sudo systemctl restart redis
```

---

## Claude Desktop Integration

### Servers Not Showing in Claude

**Symptom**: MCP servers don't appear in Claude Desktop

**Diagnosis**:

```bash
# Check Claude config file exists
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json  # macOS
ls -la ~/.config/Claude/claude_desktop_config.json  # Linux
dir "%APPDATA%\Claude\claude_desktop_config.json"  # Windows

# Validate JSON syntax
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool
```

**Solution**:

1. Ensure config file is valid JSON
2. Use absolute paths for `command`
3. Restart Claude Desktop completely
4. Check Claude logs:

```bash
# macOS
tail -f ~/Library/Logs/Claude/main.log

# Linux
tail -f ~/.local/share/Claude/logs/main.log

# Windows
type %LOCALAPPDATA%\Claude\logs\main.log
```

### Server Crashes Immediately

**Symptom**: Server starts but crashes within seconds

**Diagnosis**:

```bash
# Run server manually to see error
source mcp-env/bin/activate
python -m servers.goal_agent_server

# Check logs
tail -f logs/goal_agent_server.log
```

**Common Causes**:

1. **Missing env vars**: Add all required vars to config
2. **Database not running**: Start PostgreSQL
3. **Port conflict**: Change port in configuration
4. **Import errors**: Reinstall dependencies

### stdio Communication Issues

**Symptom**: `ERROR: Failed to read from stdio`

**Solution**:

```json
// In claude_desktop_config.json
// Ensure command uses absolute path
{
  "mcpServers": {
    "goal-agent": {
      "command": "/full/path/to/mcp-env/bin/python",
      "args": ["-m", "servers.goal_agent_server"],
      "env": {...}
    }
  }
}
```

---

## Performance Issues

### Slow Queries

**Symptom**: Dashboard takes > 5 seconds to load

**Diagnosis**:

```sql
-- Enable query logging in PostgreSQL
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log queries > 100ms
SELECT pg_reload_conf();

-- Check slow queries
tail -f /var/log/postgresql/postgresql-14-main.log | grep "duration:"
```

**Solution**:

```sql
-- Add missing indexes
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_created_at ON goals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_goal_id ON tasks(goal_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);

-- Analyze tables
ANALYZE goals;
ANALYZE tasks;

-- Vacuum to reclaim space
VACUUM ANALYZE;
```

### High Memory Usage

**Symptom**: Server using > 500MB RAM

**Diagnosis**:

```bash
# Check memory usage
ps aux | grep python | grep servers

# Monitor in real-time
top -p $(pgrep -f "servers.goal_agent")  # Linux
```

**Solution**:

```python
# Reduce connection pool size
DB_POOL = psycopg2.pool.ThreadedConnectionPool(
    minconn=2,    # Reduce from 5
    maxconn=10,   # Reduce from 20
    ...
)

# Enable connection recycling
# In database.py
conn.set_session(autocommit=True, readonly=False)
```

### Dashboard Not Updating

**Symptom**: Dashboard shows stale data

**Diagnosis**:

```bash
# Check if SSE connection is active
curl -N http://localhost:8000/events

# Should show streaming updates every 5 seconds
```

**Solution**:

1. Clear browser cache
2. Restart dashboard server
3. Check firewall blocking SSE

```bash
# Restart dashboard
pkill -f dashboard_server
python -m servers.dashboard_server &
```

---

## API Integration Issues

### GitHub API Rate Limit

**Symptom**: `API rate limit exceeded`

**Solution**:

```bash
# Check rate limit status
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/rate_limit

# Use authenticated requests (higher limits)
# In config/mcp_settings.json:
"GITHUB_TOKEN": "ghp_your_token_here"

# Or wait for rate limit reset (shown in response)
```

### Jira Authentication Failed

**Symptom**: `401 Unauthorized` or `403 Forbidden`

**Solution**:

```bash
# Test Jira credentials
curl -u "email@example.com:API_TOKEN" \
  https://your-domain.atlassian.net/rest/api/3/myself

# If fails, generate new API token:
# https://id.atlassian.com/manage-profile/security/api-tokens

# Update config with new token
```

### Google API Quota Exceeded

**Symptom**: `Quota exceeded for quota metric`

**Solution**:

1. Check quota in Google Cloud Console
2. Request quota increase
3. Implement caching to reduce API calls
4. Use search result caching (5-minute TTL)

---

## Docker Issues

### Container Won't Start

**Symptom**: `docker-compose up` fails

**Diagnosis**:

```bash
# Check container logs
docker-compose logs postgres
docker-compose logs redis

# Check container status
docker-compose ps
```

**Solution**:

```bash
# Remove and recreate containers
docker-compose down -v
docker-compose up -d

# Check disk space
df -h

# Check Docker resources
docker system df
docker system prune  # Clean up
```

### Volume Permission Issues

**Symptom**: `Permission denied` in Docker containers

**Solution**:

```bash
# Fix volume permissions
docker-compose down
sudo chown -R $USER:$USER ./data
docker-compose up -d

# Or in docker-compose.yml:
services:
  postgres:
    user: "${UID}:${GID}"
```

### Network Issues

**Symptom**: Containers can't communicate

**Solution**:

```bash
# Check network
docker network ls
docker network inspect claude-mcp-setup_mcp-network

# Recreate network
docker-compose down
docker network prune
docker-compose up -d
```

---

## Diagnostic Commands

### Check All Services

```bash
# Quick health check
make status

# Or manually
mcpctl status

# Detailed check
curl http://localhost:8000/health
```

### View All Logs

```bash
# Tail all logs
tail -f logs/*.log

# Or specific server
tail -f logs/goal_agent_server.log

# Using mcpctl
mcpctl logs goal-agent --follow
```

### Test Database Connection

```bash
# Test PostgreSQL
psql -d mcp_goals -U postgres -c "SELECT 1;"

# Test with Python
python -c "
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    database='mcp_goals',
    user='postgres',
    password='postgres'
)
print('✓ Connected')
conn.close()
"
```

### Test Redis Connection

```bash
# Test Redis
redis-cli ping

# Test with Python
python -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()
print('✓ Connected')
"
```

### Check System Resources

```bash
# Disk space
df -h

# Memory usage
free -h  # Linux
vm_stat  # macOS

# CPU usage
top -bn1 | head -20

# PostgreSQL connections
psql -d mcp_goals -c "SELECT count(*) FROM pg_stat_activity;"

# Redis memory
redis-cli INFO memory | grep used_memory_human
```

### Generate Diagnostic Report

```bash
#!/bin/bash
# Save as diagnostic.sh

echo "=== System Info ==="
uname -a
python --version
psql --version
redis-cli --version

echo -e "\n=== Service Status ==="
make status

echo -e "\n=== PostgreSQL ==="
pg_isready
psql -d mcp_goals -c "\dt"

echo -e "\n=== Redis ==="
redis-cli ping
redis-cli INFO server | grep redis_version

echo -e "\n=== Disk Usage ==="
df -h

echo -e "\n=== Memory Usage ==="
free -h 2>/dev/null || vm_stat

echo -e "\n=== Recent Errors ==="
grep -i error logs/*.log | tail -20

echo -e "\n=== Configuration ==="
cat config/mcp_settings.json | python -m json.tool 2>&1 | head -30
```

---

## Getting Additional Help

### Before Opening an Issue

1. Check this troubleshooting guide
2. Search existing GitHub issues
3. Run diagnostic commands
4. Collect relevant logs

### When Opening an Issue

Include:

```markdown
**Environment:**
- OS: Ubuntu 22.04
- Python: 3.11.2
- PostgreSQL: 14.5
- Redis: 7.0.8
- Installation method: Docker / Manual

**Problem Description:**
[Clear description of the issue]

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. ...

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happens]

**Logs:**
```
[Paste relevant log excerpts]
```

**Configuration:**
[Sanitized config file without secrets]
```

### Debug Mode

Enable verbose logging:

```bash
# In config/mcp_settings.json, add to env:
"LOG_LEVEL": "DEBUG"

# Or set environment variable
export LOG_LEVEL=DEBUG
python -m servers.goal_agent_server
```

### Community Resources

- **GitHub Issues**: https://github.com/your-org/claude-mcp-setup/issues
- **Documentation**: [README.md](README.md), [GETTING_STARTED.md](GETTING_STARTED.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Configuration**: [CONFIGURATION.md](CONFIGURATION.md)

---

**Still stuck? Open a GitHub issue with diagnostic information!**

