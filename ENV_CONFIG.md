# Environment Configuration Guide

## Quick Reference

### Your Current Setup

```bash
# PostgreSQL (Docker)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433  # ← Using 5433 to avoid conflicts
POSTGRES_DB=mcp_goals
POSTGRES_USER=postgres
POSTGRES_PASSWORD=mcp_secure_password

# Redis (Docker)
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
```

## 📁 Configuration Files

### `.env` (Your Active Config)

- **Location**: `/home/clapgrow/Desktop/claude-mcp-setup/.env`
- **Size**: 1.9 KB
- **Status**: ✅ Active and working
- **Git**: Ignored (not committed - secure)
- **Purpose**: Your personal credentials and settings

### `.env.template` (Template for Sharing)

- **Location**: `/home/clapgrow/Desktop/claude-mcp-setup/.env.template`
- **Size**: 5.1 KB
- **Status**: ✅ Created
- **Git**: Tracked (safe to commit)
- **Purpose**: Template for team members or future setup

## 🔄 How to Use

### For You (Resetting Config)

```bash
# Backup current config
cp .env .env.backup

# Reset from template
cp .env.template .env

# Edit with your values
nano .env
```

### For Team Members

```bash
# Clone the repository
git clone <your-repo>
cd claude-mcp-setup

# Copy template
cp .env.template .env

# Edit with their credentials
nano .env

# Start services
docker compose up -d
python scripts/init_database.py
mcpctl run
```

## 🔐 Security Best Practices

### What's Safe to Commit

✅ `.env.template` - Has placeholder values only  
✅ `docker-compose.yml` - No secrets  
✅ `Makefile` - Helper scripts

### What's Never Committed

❌ `.env` - Your actual credentials  
❌ `.env.local` - Local overrides  
❌ `.env.production` - Production secrets

### Gitignore Status

Your `.gitignore` already has:

```
.env
.env.local
.env.*.local
```

## 📝 Configuration Structure

### `.env.template` Contains:

```
PostgreSQL Configuration (Required)
├── Connection settings
├── Pool configuration
└── SSL settings

Redis Configuration (Optional)
├── Connection settings
├── Pool configuration
└── Timeout settings

Goal Agent Configuration
├── Worker threads
└── Timeout settings

Optional Integrations
├── GitHub (API token)
├── Jira (API credentials)
├── Frappe (API keys)
└── Google Search (API keys)
```

## 🎯 Key Differences

### PostgreSQL Ports

**Template**:

```bash
POSTGRES_PORT=5433  # Recommended to avoid conflicts
```

**Why 5433?**

- Avoids conflicts with local PostgreSQL (port 5432)
- Docker container internally uses 5432
- Mapped to 5433 on host

**If you want 5432**:

1. Stop local PostgreSQL: `sudo systemctl stop postgresql`
2. Edit `docker-compose.yml`: Change `"5432:5432"`
3. Edit `.env`: Change `POSTGRES_PORT=5432`
4. Restart: `docker compose down && docker compose up -d`

### SSL Mode

**For Docker (Local)**:

```bash
POSTGRES_SSL_MODE=disable  # No SSL needed locally
```

**For Production**:

```bash
POSTGRES_SSL_MODE=require  # Force SSL
```

## 🔧 Customization

### Change PostgreSQL Password

**In docker-compose.yml**:

```yaml
environment:
  POSTGRES_PASSWORD: your_secure_password_here
```

**In .env**:

```bash
POSTGRES_PASSWORD=your_secure_password_here
```

**Then restart**:

```bash
docker compose down -v  # Warning: deletes data!
docker compose up -d
python scripts/init_database.py
```

### Use External Database

If you want to use a managed PostgreSQL (not Docker):

**In .env**:

```bash
# Example: AWS RDS
POSTGRES_HOST=mydb.123456.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=mcp_goals
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_rds_password
POSTGRES_SSL_MODE=require

# Example: Heroku Postgres
POSTGRES_HOST=ec2-xxx.compute-1.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=d8xxx
POSTGRES_USER=username
POSTGRES_PASSWORD=password
POSTGRES_SSL_MODE=require
```

Then skip `docker compose up` - just run the init script.

## 📊 Validation

### Check Your Configuration

```bash
# Show current config (without passwords)
cat .env | grep -v PASSWORD

# Test PostgreSQL connection
psql -h localhost -p 5433 -U postgres -d mcp_goals
# Password: (from .env)

# Test Redis connection
docker exec condescending_jang redis-cli ping
# Should return: PONG

# Test from Python
python -c "from servers.config import *; load_env_file(); print(PostgresConfig().get_connection_string())"
```

## 🆘 Troubleshooting

### "Configuration validation failed"

**Check**: Required variables are set in `.env`

```bash
# Minimum required
grep -E "POSTGRES_HOST|POSTGRES_PORT|POSTGRES_DB|POSTGRES_USER" .env
```

### "Connection refused"

**Check**: Port number matches Docker mapping

```bash
# Check Docker port mapping
docker compose ps

# Should show: 0.0.0.0:5433->5432/tcp
```

### "Authentication failed"

**Check**: Password matches between docker-compose.yml and .env

```bash
# Check .env
cat .env | grep POSTGRES_PASSWORD

# Check docker-compose.yml
cat docker-compose.yml | grep POSTGRES_PASSWORD
```

## 📚 Related Documentation

- **DOCKER_QUICKSTART.md** - Quick Docker reference
- **DOCKER_SETUP.md** - Complete Docker guide
- **SETUP_POSTGRES.md** - PostgreSQL setup details
- **CONFIGURATION.md** - All configuration options

## 🎯 Summary

✅ `.env` - Your active configuration (ignored by git)  
✅ `.env.template` - Shareable template (tracked in git)  
✅ PostgreSQL on port 5433 (Docker)  
✅ Redis on port 6379 (Docker)  
✅ All secrets protected from git commits

Your configuration is production-ready! 🚀
