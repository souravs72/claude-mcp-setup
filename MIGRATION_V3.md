# Migration Guide: v2.x → v3.0 (PostgreSQL Persistence)

## Overview of Changes

Version 3.0 introduces a **major architectural change** to the Goal Agent server:

### Before (v2.x):

- **Redis**: Used for both caching AND persistence
- **Cost**: Expensive in production (Redis persistence)
- **Risk**: Data loss if Redis restarts without proper persistence configuration
- **JSON Files**: Backup persistence mechanism

### After (v3.0):

- **PostgreSQL**: Primary persistence layer (durable, reliable)
- **Redis**: Optional caching only (5-minute TTL)
- **Cost**: Much cheaper in production
- **Risk**: Minimal - PostgreSQL is designed for data persistence

## Why This Change?

### Problems with Redis-Only Persistence:

1. **Expensive**: Redis persistence (RDB/AOF) costs more in cloud environments
2. **Not Designed for It**: Redis is a cache, not a database
3. **Data Loss Risk**: Redis restart = potential data loss without careful configuration
4. **Scalability**: Limited by memory constraints

### Benefits of PostgreSQL + Redis:

1. **Cost-Effective**: PostgreSQL is cheaper for persistent storage
2. **Reliable**: ACID compliance, crash recovery, proven reliability
3. **Scalable**: Handle millions of goals/tasks
4. **Optional Caching**: Redis only used for performance, not required
5. **Industry Standard**: PostgreSQL is the standard for persistent data

## Breaking Changes

### 1. New Dependencies

**Added:**

```python
psycopg2-binary>=2.9.9
SQLAlchemy>=2.0.23
```

**Install:**

```bash
pip install -r requirements.txt
```

### 2. New Environment Variables Required

```bash
# PostgreSQL Configuration (Required)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mcp_goals
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_POOL_SIZE=10
POSTGRES_MAX_OVERFLOW=20
POSTGRES_SSL_MODE=prefer
```

### 3. Redis Now Optional

Redis is no longer required for the system to function. It only provides performance improvements:

```bash
# Optional - system works without it
CACHE_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 4. Cache TTL Changed

- **v2.x**: Redis TTL = 7 days (persistence-oriented)
- **v3.0**: Redis TTL = 5 minutes (cache-oriented)

### 5. API Response Changes

**Before (v2.x):**

```json
{
  "id": "GOAL-0001",
  "description": "...",
  "_cache_status": {
    "persisted": true,
    "message": "Goal automatically saved to Redis"
  }
}
```

**After (v3.0):**

```json
{
  "id": "GOAL-0001",
  "description": "...",
  "_persistence": {
    "database": "PostgreSQL",
    "cache_enabled": true,
    "message": "Goal saved to PostgreSQL database"
  }
}
```

### 6. MCP Tools Removed/Changed

**Removed Tools:**

- `save_state_to_cache()` - No longer needed (automatic PostgreSQL persistence)
- `restore_state_from_cache()` - No longer needed (data is always in PostgreSQL)

**Renamed Tools:**

- `get_cache_status()` → `get_agent_status()` - Shows PostgreSQL stats

### 7. Server Version String Changed

- **v2.x**: `"Version": "2.3 (Fixed Cache)"`
- **v3.0**: `"Version": "3.0 (PostgreSQL Persistence)"`

## Migration Steps

### Step 1: Install PostgreSQL

#### macOS:

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

Download from: https://www.postgresql.org/download/windows/

### Step 2: Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE mcp_goals;

# Optional: Create dedicated user
CREATE USER mcp_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mcp_goals TO mcp_user;

# Exit
\q
```

### Step 3: Update Dependencies

```bash
cd /path/to/claude-mcp-setup
pip install --upgrade -r requirements.txt
```

### Step 4: Update Environment Variables

Add to your `.env` file:

```bash
# PostgreSQL (Required)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mcp_goals
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here

# Redis (Optional - keep existing config)
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
```

### Step 5: Initialize Database

```bash
python scripts/init_database.py
```

This will:

- Create `goals` and `tasks` tables
- Set up indexes
- Verify the connection

### Step 6: Migrate Existing Data (Optional)

If you have existing goals/tasks in JSON files (`data/goals/`):

```bash
# Just start the server - it will auto-migrate
python -m servers.goal_agent_server
```

The server will:

1. Detect JSON files
2. Load them into memory
3. Save them to PostgreSQL
4. Log the migration

### Step 7: Verify Migration

```bash
# Check database
psql -U postgres -d mcp_goals -c "SELECT COUNT(*) FROM goals;"
psql -U postgres -d mcp_goals -c "SELECT COUNT(*) FROM tasks;"

# Start server
python -m servers.goal_agent_server

# Check logs
tail -f logs/goal_agent_server.log
```

### Step 8: Update Claude Desktop Config

No changes needed to `mcp_settings.json` - the Goal Agent server still works the same way from Claude's perspective.

## Rollback Plan

If you need to rollback to v2.x:

```bash
# 1. Checkout previous version
git checkout v2.3

# 2. Reinstall dependencies
pip install -r requirements.txt

# 3. Export data from PostgreSQL (if needed)
psql -U postgres -d mcp_goals -c "COPY goals TO '/tmp/goals_backup.json';"

# 4. Restart servers
mcpctl restart
```

## Testing Your Migration

### Test 1: Create a Goal

```python
# In Claude Desktop
"Create a goal to test PostgreSQL persistence"
```

Verify in PostgreSQL:

```bash
psql -U postgres -d mcp_goals -c "SELECT * FROM goals ORDER BY created_at DESC LIMIT 1;"
```

### Test 2: Create Tasks

```python
# In Claude Desktop
"Break down GOAL-0001 into 3 tasks"
```

Verify:

```bash
psql -U postgres -d mcp_goals -c "SELECT COUNT(*) FROM tasks WHERE goal_id='GOAL-0001';"
```

### Test 3: Server Restart

```bash
# Stop server
mcpctl stop goal-agent

# Start server
mcpctl start goal-agent

# Verify data persists
# In Claude: "List all goals"
```

Data should still be there (from PostgreSQL, not Redis).

### Test 4: Without Redis

```bash
# Stop Redis
brew services stop redis  # or sudo systemctl stop redis

# Restart Goal Agent
mcpctl restart goal-agent

# Try creating a goal - should still work
```

## Performance Comparison

### With Redis Caching:

- First query: ~20-50ms (PostgreSQL)
- Cached queries: ~5-10ms (Redis)
- Cache duration: 5 minutes

### Without Redis:

- All queries: ~20-50ms (PostgreSQL)
- Still very fast for typical use cases

## Troubleshooting

### "Failed to initialize Goal Agent"

**Cause**: PostgreSQL not configured or not running

**Solution**:

```bash
# Check PostgreSQL
systemctl status postgresql

# Verify connection
psql -h localhost -U postgres -d mcp_goals -c "SELECT 1;"

# Check .env has POSTGRES_* variables
```

### "relation 'goals' does not exist"

**Cause**: Database tables not created

**Solution**:

```bash
python scripts/init_database.py
```

### "password authentication failed"

**Cause**: Wrong password in .env

**Solution**:

```bash
# Update POSTGRES_PASSWORD in .env
# Or reset PostgreSQL password:
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'newpassword';"
```

### "too many clients already"

**Cause**: Connection pool exhausted

**Solution**:

```bash
# Increase PostgreSQL max_connections
# Edit postgresql.conf:
max_connections = 100

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## FAQ

### Q: Is Redis still required?

**A:** No, Redis is now optional. The system works without it, just slightly slower.

### Q: Will my existing goals/tasks be migrated?

**A:** Yes, if you have JSON files in `data/goals/`, they'll be auto-migrated to PostgreSQL on first startup.

### Q: What happens to Redis cache now?

**A:** Redis only caches for 5 minutes (not 7 days). It's purely for performance.

### Q: Can I still use Redis for persistence?

**A:** Not recommended. Use PostgreSQL for persistence. Redis v3.0 is cache-only.

### Q: What if I don't have PostgreSQL?

**A:** You must install PostgreSQL for v3.0. It's required for Goal Agent persistence.

### Q: Can I use MySQL instead?

**A:** Not currently supported, but SQLAlchemy makes it possible. File an issue if needed.

### Q: Will this affect other MCP servers?

**A:** No, only Goal Agent uses PostgreSQL. Other servers are unchanged.

### Q: What about backups?

**A:** Use standard PostgreSQL backup tools:

```bash
pg_dump -U postgres mcp_goals > backup.sql
```

### Q: Is this a breaking change?

**A:** Yes, but migration is straightforward. Follow the steps above.

## Support

For issues:

1. Check `logs/goal_agent_server.log`
2. Run `python scripts/init_database.py`
3. Verify `.env` has PostgreSQL configuration
4. See `SETUP_POSTGRES.md` for detailed PostgreSQL setup

## Summary

**You need to:**

1. ✅ Install PostgreSQL
2. ✅ Create `mcp_goals` database
3. ✅ Add `POSTGRES_*` env vars
4. ✅ Run `python scripts/init_database.py`
5. ✅ Restart Goal Agent server

**You get:**

- ✨ Reliable, durable persistence
- 💰 Lower production costs
- 🚀 Optional Redis for performance
- 📊 Industry-standard database
- 🔒 ACID compliance and data safety

**Version 3.0 brings production-grade persistence to your Goal Agent!**
