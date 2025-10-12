# Docker Setup for MCP Servers

This guide shows how to run PostgreSQL and Redis using Docker containers for the MCP Goal Agent.

## Quick Start (2 minutes)

```bash
# 1. Start PostgreSQL and Redis in Docker
docker-compose up -d

# 2. Wait for containers to be healthy (5-10 seconds)
docker-compose ps

# 3. Copy Docker environment configuration
cp .env.docker .env
# Or if you have existing .env, merge the PostgreSQL settings

# 4. Initialize database tables
python scripts/init_database.py

# 5. Start MCP servers
mcpctl run
```

Done! PostgreSQL and Redis are running in Docker containers.

## What Gets Created

### Docker Containers

1. **mcp-postgres** - PostgreSQL 15 database

   - Port: 5432
   - Database: `mcp_goals`
   - User: `postgres`
   - Password: `mcp_secure_password`
   - Data persisted in Docker volume

2. **mcp-redis** - Redis 7 cache

   - Port: 6379
   - No persistence (cache only)
   - 5-minute TTL for cached data

3. **mcp-pgadmin** (optional) - Database GUI
   - Port: 5050
   - Start with: `docker-compose --profile tools up -d`
   - Access: http://localhost:5050

### Docker Volumes

- `postgres_data` - PostgreSQL database files
- `redis_data` - Redis data (not used, cache-only mode)
- `pgadmin_data` - pgAdmin configuration

## Environment Variables

Your `.env` file should have these settings for Docker:

```bash
# PostgreSQL (Docker container)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mcp_goals
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mcp_secure_password
POSTGRES_SSL_MODE=disable

# Redis (Docker container)
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
```

**Important**:

- Use `localhost` for POSTGRES_HOST and REDIS_HOST (not `postgres` or `redis`)
- This is because Python scripts run on your host machine, not in Docker

## Docker Commands

### Start Containers

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Start with pgAdmin too
docker-compose --profile tools up -d

# View startup logs
docker-compose logs -f
```

### Check Status

```bash
# List containers
docker-compose ps

# Check PostgreSQL health
docker exec mcp-postgres pg_isready -U postgres

# Check Redis health
docker exec mcp-redis redis-cli ping
```

### View Logs

```bash
# All logs
docker-compose logs -f

# PostgreSQL only
docker-compose logs -f postgres

# Redis only
docker-compose logs -f redis

# Last 50 lines
docker-compose logs --tail=50 postgres
```

### Access Containers

```bash
# PostgreSQL shell
docker exec -it mcp-postgres psql -U postgres -d mcp_goals

# Redis CLI
docker exec -it mcp-redis redis-cli

# Container bash
docker exec -it mcp-postgres bash
```

### Stop Containers

```bash
# Stop containers (keeps data)
docker-compose stop

# Stop and remove containers (keeps data volumes)
docker-compose down

# Stop and remove everything including data
docker-compose down -v
```

### Restart Containers

```bash
# Restart all
docker-compose restart

# Restart PostgreSQL only
docker-compose restart postgres

# Restart Redis only
docker-compose restart redis
```

## Database Management

### Initialize Database

```bash
# Create tables and indexes
python scripts/init_database.py
```

### Connect to Database

```bash
# Using docker exec
docker exec -it mcp-postgres psql -U postgres -d mcp_goals

# Using psql on host (if installed)
psql -h localhost -U postgres -d mcp_goals
```

### Database Operations

```sql
-- List tables
\dt

-- View goals
SELECT * FROM goals;

-- View tasks
SELECT * FROM tasks;

-- Count records
SELECT COUNT(*) FROM goals;
SELECT COUNT(*) FROM tasks;

-- Exit
\q
```

### Backup Database

```bash
# Backup to file
docker exec mcp-postgres pg_dump -U postgres mcp_goals > backup.sql

# Restore from file
docker exec -i mcp-postgres psql -U postgres mcp_goals < backup.sql

# Backup with docker-compose
docker-compose exec postgres pg_dump -U postgres mcp_goals > backup_$(date +%Y%m%d).sql
```

## Using pgAdmin (Optional)

pgAdmin provides a web-based GUI for PostgreSQL.

### Start pgAdmin

```bash
docker-compose --profile tools up -d pgadmin
```

### Access pgAdmin

1. Open browser: http://localhost:5050
2. Login:

   - Email: `admin@mcp.local`
   - Password: `admin`

3. Add PostgreSQL server:
   - Right-click "Servers" → Create → Server
   - General tab:
     - Name: `MCP PostgreSQL`
   - Connection tab:
     - Host: `postgres` (Docker network name)
     - Port: `5432`
     - Database: `mcp_goals`
     - Username: `postgres`
     - Password: `mcp_secure_password`
   - Click "Save"

### Browse Data

- Navigate: Servers → MCP PostgreSQL → Databases → mcp_goals → Schemas → public → Tables
- Right-click table → View/Edit Data

## Redis Management

### Check Redis Cache

```bash
# Connect to Redis CLI
docker exec -it mcp-redis redis-cli

# View all keys
KEYS *

# Get cache statistics
INFO stats

# Check specific key
GET goal_agent_cache:goal:GOAL-0001

# Clear all cache (if needed)
FLUSHDB

# Exit
exit
```

### Monitor Redis

```bash
# Real-time monitoring
docker exec -it mcp-redis redis-cli MONITOR

# Check memory usage
docker exec -it mcp-redis redis-cli INFO memory
```

## Troubleshooting

### "Connection refused" Error

**Problem**: Can't connect to PostgreSQL

**Solutions**:

```bash
# 1. Check container is running
docker-compose ps

# 2. Check health
docker exec mcp-postgres pg_isready -U postgres

# 3. View logs
docker-compose logs postgres

# 4. Restart container
docker-compose restart postgres
```

### "Authentication failed" Error

**Problem**: Wrong password in .env

**Solutions**:

```bash
# 1. Check password in .env matches docker-compose.yml
cat .env | grep POSTGRES_PASSWORD

# 2. Recreate container with correct password
docker-compose down
# Edit docker-compose.yml or .env
docker-compose up -d
```

### "Database does not exist" Error

**Problem**: Database not initialized

**Solutions**:

```bash
# 1. Check if database exists
docker exec mcp-postgres psql -U postgres -l

# 2. Create database if missing
docker exec mcp-postgres psql -U postgres -c "CREATE DATABASE mcp_goals;"

# 3. Run initialization script
python scripts/init_database.py
```

### "Port already in use" Error

**Problem**: Port 5432 or 6379 already in use

**Solutions**:

```bash
# Option 1: Stop conflicting service
sudo systemctl stop postgresql
sudo systemctl stop redis

# Option 2: Change ports in docker-compose.yml
# Edit docker-compose.yml:
# - "5433:5432"  # Use 5433 instead
# Then update POSTGRES_PORT in .env to 5433
```

### Container Won't Start

```bash
# View detailed logs
docker-compose logs postgres
docker-compose logs redis

# Check Docker daemon
docker info

# Remove and recreate
docker-compose down -v
docker-compose up -d
```

### Data Not Persisting

**Problem**: Data lost after container restart

**Cause**: Docker volumes not working

**Solutions**:

```bash
# Check volumes exist
docker volume ls | grep mcp

# Inspect volume
docker volume inspect claude-mcp-setup_postgres_data

# Ensure volume is mounted
docker-compose config | grep volumes -A 5
```

## Performance Tuning

### PostgreSQL Configuration

For better performance, you can customize PostgreSQL settings in `docker-compose.yml`:

```yaml
postgres:
  command: >
    postgres
    -c shared_buffers=256MB
    -c max_connections=200
    -c work_mem=4MB
    -c maintenance_work_mem=64MB
```

### Redis Configuration

Customize Redis in `docker-compose.yml`:

```yaml
redis:
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --appendonly no
```

## Production Considerations

### Security

1. **Change default passwords**:

   ```yaml
   # In docker-compose.yml
   POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
   ```

   Then set in `.env`:

   ```bash
   POSTGRES_PASSWORD=your_secure_random_password
   ```

2. **Don't expose ports publicly**:

   ```yaml
   # Only bind to localhost
   ports:
     - "127.0.0.1:5432:5432"
   ```

3. **Enable SSL for PostgreSQL**:
   ```yaml
   command: postgres -c ssl=on -c ssl_cert_file=/certs/server.crt
   ```

### Backups

Set up automated backups:

```bash
# Create backup script
cat > backup.sh <<'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec mcp-postgres pg_dump -U postgres mcp_goals | gzip > "backups/mcp_goals_$DATE.sql.gz"
# Keep only last 7 days
find backups/ -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

### Monitoring

Monitor container health:

```bash
# Check container stats
docker stats mcp-postgres mcp-redis

# Set up alerts
docker events --filter container=mcp-postgres --filter event=health_status
```

## Docker Compose Reference

### Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart service
docker-compose restart postgres

# Execute command
docker-compose exec postgres psql -U postgres

# View running containers
docker-compose ps

# Pull latest images
docker-compose pull

# Rebuild containers
docker-compose up -d --build
```

### Environment Variables

You can override settings with environment variables:

```bash
# Override PostgreSQL password
POSTGRES_PASSWORD=new_password docker-compose up -d

# Use different ports
docker-compose up -d -p 5433:5432
```

## Cleanup

### Remove Everything

```bash
# Stop and remove containers, networks
docker-compose down

# Also remove volumes (deletes data!)
docker-compose down -v

# Remove images
docker rmi postgres:15-alpine redis:7-alpine

# Clean up Docker system
docker system prune -a --volumes
```

## Summary

✅ **PostgreSQL**: Runs in Docker, data persists in volume  
✅ **Redis**: Runs in Docker, cache-only (no persistence)  
✅ **Easy Setup**: Single `docker-compose up -d` command  
✅ **Portable**: Works on any system with Docker  
✅ **Isolated**: No conflicts with local installations  
✅ **Optional GUI**: pgAdmin for database management

Your MCP servers run on the host, PostgreSQL and Redis run in Docker containers!
