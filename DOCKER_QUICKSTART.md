# Docker Setup - Quick Reference

## ✅ Your Current Setup

### PostgreSQL (Docker Container)

- **Container Name**: `mcp-postgres`
- **Image**: `postgres:15-alpine`
- **Host Port**: `5433` (to avoid conflict with local PostgreSQL)
- **Container Port**: `5432`
- **Database**: `mcp_goals`
- **User**: `postgres`
- **Password**: `mcp_secure_password`
- **Status**: ✅ Running and initialized

### Redis (Your Existing Container)

- **Container Name**: `condescending_jang`
- **Port**: `6379`
- **Status**: ✅ Already running

## 📝 Environment Configuration

Your `.env` file is configured with:

```bash
# PostgreSQL (Docker - Port 5433)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433  # Note: Using 5433 to avoid conflicts
POSTGRES_DB=mcp_goals
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mcp_secure_password

# Redis (Your existing container)
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
```

## 🚀 Quick Commands

### Start/Stop Containers

```bash
# Start PostgreSQL
docker compose up -d

# Stop PostgreSQL
docker compose down

# View logs
docker compose logs -f postgres

# Check status
docker compose ps
```

### Database Operations

```bash
# Connect to PostgreSQL
docker exec -it mcp-postgres psql -U postgres -d mcp_goals

# Run queries
docker exec mcp-postgres psql -U postgres -d mcp_goals -c "SELECT COUNT(*) FROM goals;"

# Backup database
docker exec mcp-postgres pg_dump -U postgres mcp_goals > backup.sql

# Restore database
docker exec -i mcp-postgres psql -U postgres mcp_goals < backup.sql
```

### Using Makefile

```bash
# View all commands
make help

# Start PostgreSQL
make docker-up

# Initialize database (already done)
make init-db

# Test connection
make test-db

# Open PostgreSQL shell
make psql

# Open Redis CLI
make redis

# Backup database
make backup

# Check container status
make docker-status
```

## 🎯 Start MCP Servers

Now that PostgreSQL and Redis are set up, start your MCP servers:

```bash
# Activate virtual environment
source mcp-env/bin/activate

# Start all servers
mcpctl run

# Or start Goal Agent specifically
python -m servers.goal_agent_server
```

## 📊 Verify Setup

```bash
# 1. Check PostgreSQL tables
docker exec mcp-postgres psql -U postgres -d mcp_goals -c "\dt"

# 2. Check Redis
docker exec condescending_jang redis-cli ping

# 3. Test Python connection
source mcp-env/bin/activate
python -c "from servers.config import *; from servers.database import *; load_env_file(); db = DatabaseManager(PostgresConfig().get_connection_string()); print('✓ Connection successful!' if db.health_check() else '✗ Failed')"
```

## 📁 Database Schema

### Goals Table

- `id` (VARCHAR 20) - Primary key
- `description` (TEXT) - Goal description
- `priority` (VARCHAR 10) - high/medium/low
- `status` (VARCHAR 20) - planned/in_progress/completed/cancelled
- `repos` (JSON) - Array of repository names
- `created_at` (TIMESTAMP) - Creation time
- `updated_at` (TIMESTAMP) - Last update time
- `metadata` (JSON) - Custom metadata

### Tasks Table

- `id` (VARCHAR 20) - Primary key
- `goal_id` (VARCHAR 20) - Foreign key to goals
- `description` (TEXT) - Task description
- `type` (VARCHAR 50) - Task type
- `status` (VARCHAR 20) - pending/in_progress/completed/failed/blocked
- `priority` (VARCHAR 10) - high/medium/low
- `dependencies` (JSON) - Array of task IDs
- `repo` (VARCHAR 255) - Repository name
- `jira_ticket` (VARCHAR 50) - Jira ticket ID
- `estimated_effort` (VARCHAR 50) - Effort estimate
- `assigned_tools` (JSON) - Array of tool names
- `created_at` (TIMESTAMP) - Creation time
- `updated_at` (TIMESTAMP) - Last update time
- `completed_at` (TIMESTAMP) - Completion time
- `result` (JSON) - Task result data

## 🔧 Troubleshooting

### PostgreSQL not starting?

```bash
# Check logs
docker compose logs postgres

# Restart
docker compose restart postgres
```

### Can't connect from Python?

```bash
# Verify .env has correct port
cat .env | grep POSTGRES_PORT
# Should show: POSTGRES_PORT=5433

# Test connection
psql -h localhost -p 5433 -U postgres -d mcp_goals
# Password: mcp_secure_password
```

### Need to reset database?

```bash
# Stop container and remove data
docker compose down -v

# Recreate
docker compose up -d

# Re-initialize
python scripts/init_database.py
```

## 📚 Documentation

- **Full Docker Guide**: See `DOCKER_SETUP.md`
- **PostgreSQL Setup**: See `SETUP_POSTGRES.md`
- **Migration Guide**: See `MIGRATION_V3.md`
- **Main README**: See `README.md`

## 🎉 Next Steps

1. ✅ PostgreSQL running in Docker on port 5433
2. ✅ Redis already running on port 6379
3. ✅ Database tables initialized
4. ✅ Environment configured

**You're ready to go!**

Run: `mcpctl run` to start all MCP servers!
