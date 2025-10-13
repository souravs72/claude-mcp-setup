# PostgreSQL Setup for MCP Goal Agent

## Overview

The MCP Goal Agent has been refactored to use **PostgreSQL for persistence** and **Redis for caching only**. This provides:

- **Durable persistence**: All goals and tasks are stored in PostgreSQL
- **Cost-effective**: Avoid expensive Redis persistence in production
- **Optional caching**: Redis provides performance boost but is not required
- **Production-ready**: PostgreSQL is designed for persistent data storage

## Architecture Change

### Before (v2.x):

```
Redis → Persistence + Caching (expensive in production)
```

### After (v3.0):

```
PostgreSQL → Persistence (reliable, cost-effective)
Redis → Caching only (optional, 5-minute TTL)
```

## Installation

### 1. Install PostgreSQL

#### macOS (Homebrew):

```bash
brew install postgresql@15
brew services start postgresql@15
```

#### Ubuntu/Debian:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Windows:

Download installer from: https://www.postgresql.org/download/windows/

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database for MCP goals
CREATE DATABASE mcp_goals;

# Create user (optional, for security)
CREATE USER mcp_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE mcp_goals TO mcp_user;

# Exit
\q
```

### 3. Install Python Dependencies

```bash
cd /path/to/claude-mcp-setup
pip install -r requirements.txt
```

This will install:

- `psycopg2-binary>=2.9.9` - PostgreSQL adapter
- `SQLAlchemy>=2.0.23` - ORM for database operations

### 4. Configure Environment Variables

Add these to your `.env` file:

```bash
# PostgreSQL Configuration (Required)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mcp_goals
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=20
POSTGRES_SSL_MODE=prefer

# Redis Configuration (Optional - for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CACHE_ENABLED=true

# Goal Agent Configuration
GOAL_AGENT_MAX_WORKERS=5
GOAL_AGENT_TIMEOUT=30
```

### 5. Initialize Database

```bash
python scripts/init_database.py
```

This will:

- Create the `goals` and `tasks` tables
- Set up indexes for performance
- Verify the connection

### 6. Verify Setup

```bash
# Check PostgreSQL is running
psql -h localhost -U postgres -d mcp_goals -c "SELECT version();"

# Check tables were created
psql -h localhost -U postgres -d mcp_goals -c "\dt"
```

You should see `goals` and `tasks` tables.

## Redis Configuration (Optional)

Redis is now **optional** and used only for temporary caching (5-minute TTL):

### Install Redis (Optional)

#### macOS:

```bash
brew install redis
brew services start redis
```

#### Ubuntu/Debian:

```bash
sudo apt install redis-server
sudo systemctl start redis
```

### Test Redis:

```bash
redis-cli ping
# Should return: PONG
```

**Note**: The system will work without Redis, but queries may be slightly slower.

## Database Schema

### Goals Table

```sql
CREATE TABLE goals (
    id VARCHAR(20) PRIMARY KEY,
    description TEXT NOT NULL,
    priority VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    repos JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);
```

### Tasks Table

```sql
CREATE TABLE tasks (
    id VARCHAR(20) PRIMARY KEY,
    goal_id VARCHAR(20) REFERENCES goals(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    priority VARCHAR(10) NOT NULL,
    dependencies JSON,
    repo VARCHAR(255),
    jira_ticket VARCHAR(50),
    estimated_effort VARCHAR(50),
    assigned_tools JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result JSON
);
```

## Migration from Redis-only Setup

If you were using the previous Redis-based persistence:

### 1. Export Existing Data (if any)

The old system may have saved data to JSON files in `data/goals/`. These will be automatically loaded if present.

### 2. Start Goal Agent Server

```bash
python -m servers.goal_agent_server
```

The server will:

- Connect to PostgreSQL
- Initialize tables
- Load any existing JSON data (if present)
- Migrate data to PostgreSQL

### 3. Verify Data

```bash
# Check goals count
psql -h localhost -U postgres -d mcp_goals -c "SELECT COUNT(*) FROM goals;"

# Check tasks count
psql -h localhost -U postgres -d mcp_goals -c "SELECT COUNT(*) FROM tasks;"
```

## Configuration Options

### PostgreSQL Connection String

The system builds connection string from environment variables:

```
postgresql://user:password@host:port/database?sslmode=prefer
```

### Connection Pooling

- `POSTGRES_POOL_SIZE=10` - Number of persistent connections
- `POSTGRES_MAX_OVERFLOW=20` - Additional connections when needed
- Total max connections: 30 (pool_size + max_overflow)

### SSL Mode Options

- `disable` - No SSL
- `allow` - Try SSL, fall back to non-SSL
- `prefer` - Try SSL, fall back to non-SSL (default)
- `require` - Require SSL connection

## Troubleshooting

### "Could not connect to server"

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Or on macOS:
brew services list | grep postgresql
```

### "database does not exist"

```bash
createdb -U postgres mcp_goals
```

### "password authentication failed"

Update `POSTGRES_PASSWORD` in `.env` with correct password.

### "permission denied for database"

```bash
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE mcp_goals TO your_user;"
```

### View PostgreSQL Logs

#### Ubuntu:

```bash
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

#### macOS:

```bash
tail -f /usr/local/var/log/postgresql@15.log
```

## Performance Considerations

### With Redis Caching

- Goal queries: ~5-10ms (from cache)
- Task queries: ~5-10ms (from cache)
- Cache TTL: 5 minutes

### Without Redis Caching

- Goal queries: ~20-50ms (from PostgreSQL)
- Task queries: ~20-50ms (from PostgreSQL)
- Still very fast for typical use cases

### Database Indexes

The system creates indexes on:

- `goals.status, goals.priority` - For filtered queries
- `tasks.goal_id, tasks.status` - For task lookups
- `tasks.status, tasks.priority` - For priority queries

## Production Deployment

### Recommended PostgreSQL Settings

For production, consider:

```bash
# In postgresql.conf
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB
```

### Backup Strategy

```bash
# Daily backup
pg_dump -U postgres mcp_goals > backup_$(date +%Y%m%d).sql

# Restore if needed
psql -U postgres mcp_goals < backup_20250112.sql
```

### Monitoring

```bash
# Check database size
psql -U postgres -d mcp_goals -c "
    SELECT pg_size_pretty(pg_database_size('mcp_goals'));
"

# Check table sizes
psql -U postgres -d mcp_goals -c "
    SELECT relname, pg_size_pretty(pg_relation_size(relid))
    FROM pg_stat_user_tables
    ORDER BY pg_relation_size(relid) DESC;
"

# Check connection count
psql -U postgres -c "
    SELECT count(*) FROM pg_stat_activity WHERE datname='mcp_goals';
"
```

## Support

For issues or questions:

1. Check logs: `logs/goal_agent_server.log`
2. Run database init: `python scripts/init_database.py`
3. Check PostgreSQL status: `systemctl status postgresql`
4. Verify .env configuration

## Benefits Summary

✅ **Cost-Effective**: PostgreSQL is designed for persistence  
✅ **Reliable**: ACID compliance, crash recovery  
✅ **Scalable**: Handle millions of records  
✅ **Optional Redis**: Only for performance, not required  
✅ **Production-Ready**: Industry standard for data storage  
✅ **Flexible**: Easy to query, backup, and migrate

Redis is now used only for what it does best: **temporary caching**.
