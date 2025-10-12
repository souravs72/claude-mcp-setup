# Configuration Guide

Complete environment configuration reference for all MCP servers.

## Configuration Architecture

```
┌─────────────────────────────────────────────┐
│           .env File (gitignored)            │
│  Human-readable key=value pairs             │
└──────────────────┬──────────────────────────┘
                   │ loaded by python-dotenv
                   ▼
┌─────────────────────────────────────────────┐
│         Environment Variables               │
│  os.getenv() accessible to all servers      │
└──────────────────┬──────────────────────────┘
                   │ parsed by config.py
                   ▼
┌─────────────────────────────────────────────┐
│      Typed Configuration Classes            │
│  @dataclass with validation                 │
│  • FrappeConfig                             │
│  • GitHubConfig                             │
│  • JiraConfig                               │
│  • RedisConfig                              │
│  • InternetConfig                           │
└─────────────────────────────────────────────┘
```

## Quick Setup

```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or vim, code, etc.

# Validate configuration
python -c "from servers.config import *; print('✓ Valid')"
```

## Configuration by Server

### 🔴 Required: Redis (Memory Cache Server)

```bash
# Network
REDIS_HOST=localhost           # Redis server host
REDIS_PORT=6379                # Redis server port (default: 6379)
REDIS_DB=0                     # Database number (0-15)

# Security
REDIS_PASSWORD=                # Leave empty for no password

# Connection Pool
REDIS_MAX_CONNECTIONS=50       # Maximum connections in pool
REDIS_SOCKET_TIMEOUT=5         # Socket timeout in seconds
REDIS_SOCKET_CONNECT_TIMEOUT=5 # Connection timeout in seconds
REDIS_HEALTH_CHECK_INTERVAL=30 # Health check interval in seconds
REDIS_RETRY_ON_TIMEOUT=true    # Retry on timeout errors

# Response Format
REDIS_DECODE_RESPONSES=true    # Automatically decode bytes to strings
```

**Technical Details:**

| Parameter | Range | Impact | Default |
|-----------|-------|--------|---------|
| `MAX_CONNECTIONS` | 10-500 | Pool size, memory usage | 50 |
| `SOCKET_TIMEOUT` | 1-30s | Query timeout | 5s |
| `HEALTH_CHECK_INTERVAL` | 10-300s | Connection validation | 30s |

**Connection Pool Sizing:**
```python
# Formula: connections = workers * concurrent_operations
# Example: 10 workers * 5 ops = 50 connections

# Low traffic:  10-20 connections
# Medium:       50-100 connections
# High:         100-200 connections
# Very high:    200-500 connections
```

### 🔴 Required: Goal Agent Server

```bash
# Thread Pool
GOAL_AGENT_MAX_WORKERS=10      # ThreadPoolExecutor size
GOAL_AGENT_TIMEOUT=30          # Operation timeout in seconds

# Caching
CACHE_ENABLED=true             # Enable Redis caching
```

**Worker Sizing Guide:**

| Workload | Workers | Notes |
|----------|---------|-------|
| Development | 3-5 | Minimal resource usage |
| Light | 5-10 | Standard usage |
| Medium | 10-20 | Multiple concurrent goals |
| Heavy | 20-50 | Batch operations |

**Performance Impact:**
```python
# More workers = more concurrent operations
# But: Diminishing returns after ~20 workers
# And: Each worker consumes memory

# Memory per worker: ~10-50MB
# 10 workers = 100-500MB
# 50 workers = 500-2500MB
```

### 🟢 Optional: GitHub Server

```bash
# Authentication
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
# Get from: https://github.com/settings/tokens
# Required scopes: repo, workflow, read:org

# Configuration
GITHUB_DEFAULT_BRANCH=main     # Default branch for operations
GITHUB_TIMEOUT=30              # Request timeout in seconds
GITHUB_MAX_RETRIES=3           # Retry attempts on failure
```

**Token Scopes Explained:**

| Scope | Purpose | Required For |
|-------|---------|--------------|
| `repo` | Full repository access | Reading/writing code, creating PRs |
| `workflow` | GitHub Actions | Triggering workflows |
| `read:org` | Organization access | Private org repositories |
| `read:user` | User info | Profile information |

**Getting Your Token:**

1. Visit: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`, `read:org`
4. Generate and copy token
5. **Save immediately** - you won't see it again!

**Token Format:**
- Classic: `ghp_` followed by 40 characters
- Fine-grained: `github_pat_` followed by token

### 🟢 Optional: Jira Server

```bash
# Instance
JIRA_BASE_URL=https://your-company.atlassian.net
# No trailing slash!

# Authentication
JIRA_EMAIL=developer@company.com
JIRA_API_TOKEN=ATATTxxxxxxxxxxxxxxxxx
# Get from: https://id.atlassian.com/manage-profile/security/api-tokens

# Default Project
JIRA_PROJECT_KEY=PROJ          # Default project for operations

# Connection
JIRA_TIMEOUT=30                # Request timeout in seconds
JIRA_MAX_RETRIES=3             # Retry attempts

# Rate Limiting
JIRA_RATE_LIMIT_DELAY=0.5      # Seconds between requests
```

**Getting Jira Credentials:**

1. **Base URL:** 
   ```
   https://[your-domain].atlassian.net
   Example: https://acme-corp.atlassian.net
   ```

2. **API Token:**
   - Visit: https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Name it (e.g., "Claude MCP Server")
   - Copy token immediately

3. **Email:**
   - Must be the email associated with your Jira account
   - Check: https://id.atlassian.com/manage-profile/email

**Rate Limit Configuration:**

```python
# Jira Cloud rate limits (per IP):
# - 150 requests per minute (free/standard)
# - 300 requests per minute (premium)
# - 600 requests per minute (enterprise)

# Recommended delays:
# Free/Standard:  0.5s (120 req/min)
# Premium:        0.25s (240 req/min)
# Enterprise:     0.1s (600 req/min)
```

### 🟢 Optional: Internet/Search Server

```bash
# Google Custom Search API
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxx
GOOGLE_SEARCH_ENGINE_ID=xxxxxxxxxxx

# Connection
GOOGLE_TIMEOUT=15              # Request timeout
GOOGLE_MAX_RETRIES=3           # Retry attempts
```

**Setup Instructions:**

1. **Enable Custom Search API:**
   - Visit: https://console.cloud.google.com/apis/library/customsearch.googleapis.com
   - Click "Enable"

2. **Get API Key:**
   - Visit: https://console.cloud.google.com/apis/credentials
   - Create Credentials → API Key
   - Copy key

3. **Create Search Engine:**
   - Visit: https://programmablesearchengine.google.com/
   - Click "Add"
   - Search the entire web: ON
   - Create
   - Copy Search Engine ID

**Rate Limits (Free Tier):**
- 100 queries per day
- 10 queries per second

**Paid Tier:**
- $5 per 1,000 queries
- 10,000 queries per day
- Visit: https://console.cloud.google.com/billing

### 🟢 Optional: Frappe/ERPNext Server

```bash
# Instance
FRAPPE_SITE_URL=http://127.0.0.1:8005
# Or: https://yourcompany.erpnext.com

# Authentication
FRAPPE_API_KEY=xxxxxxxxxxxxxxxx
FRAPPE_API_SECRET=xxxxxxxxxxxxxxxx

# Connection
FRAPPE_TIMEOUT=30              # Request timeout
FRAPPE_MAX_RETRIES=3           # Retry attempts
FRAPPE_POOL_CONNECTIONS=5      # Connection pool size
FRAPPE_POOL_MAXSIZE=10         # Max pool size
```

**Getting Frappe Credentials:**

1. Log into your Frappe/ERPNext instance
2. Go to: User Menu → API Access
3. Click "Generate Keys"
4. Copy both API Key and API Secret
5. Store securely in `.env`

**Important:**
- Keep credentials secure - they provide full access
- Regenerate if compromised
- Use separate keys for development/production

## Performance Tuning

### Connection Pool Configuration

```bash
# Formula: Pool size ≈ concurrent requests * 1.5

# Low traffic (< 10 req/s):
FRAPPE_POOL_CONNECTIONS=5
FRAPPE_POOL_MAXSIZE=10

# Medium traffic (10-50 req/s):
FRAPPE_POOL_CONNECTIONS=10
FRAPPE_POOL_MAXSIZE=20

# High traffic (50-100 req/s):
FRAPPE_POOL_CONNECTIONS=20
FRAPPE_POOL_MAXSIZE=40
```

### Timeout Configuration

```bash
# Quick operations:
DEFAULT_TIMEOUT=10             # Simple queries

# Standard operations:
DEFAULT_TIMEOUT=30             # Most use cases

# Heavy operations:
DEFAULT_TIMEOUT=60             # Large file uploads, complex queries
```

### Retry Strategy

```bash
# Default retry logic:
DEFAULT_MAX_RETRIES=3          # Standard
# Retries on: 500, 502, 503, 504, 429

# Backoff formula:
# delay = backoff_factor * (2 ** retry_number)
# With backoff_factor=0.5:
# Retry 1: 0.5s
# Retry 2: 1.0s
# Retry 3: 2.0s

# For unreliable networks:
DEFAULT_MAX_RETRIES=5          # More retries

# For stable networks:
DEFAULT_MAX_RETRIES=1          # Fail fast
```

### Thread Pool Tuning

```bash
# Goal Agent workers:
# CPU-bound work:  workers = CPU_cores * 1
# I/O-bound work:  workers = CPU_cores * 2-4

# Examples:
# 4-core CPU (MacBook):      GOAL_AGENT_MAX_WORKERS=10
# 8-core CPU (Desktop):      GOAL_AGENT_MAX_WORKERS=20
# 16-core CPU (Server):      GOAL_AGENT_MAX_WORKERS=40
```

## Validation

All configuration is validated on server startup:

```python
# Automatic validation:
# 1. Required fields present
# 2. URLs properly formatted
# 3. Token formats correct
# 4. Numeric values in range

# Example validation error:
"""
Configuration validation failed:
  - Missing required field: api_key
  - Invalid JIRA_BASE_URL: must use HTTPS
  - Invalid token format: should start with 'ghp_'
"""
```

## Environment Files

### Development: `.env.development`

```bash
# Redis (local)
REDIS_HOST=localhost
REDIS_PORT=6379

# GitHub (development token)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_dev_token

# Jira (sandbox instance)
JIRA_BASE_URL=https://company-sandbox.atlassian.net

# Lower limits for dev
GOAL_AGENT_MAX_WORKERS=5
JIRA_RATE_LIMIT_DELAY=1.0
```

### Production: `.env.production`

```bash
# Redis (production instance)
REDIS_HOST=redis.company.internal
REDIS_PORT=6379
REDIS_PASSWORD=secure_password

# GitHub (production token)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_prod_token

# Jira (production instance)
JIRA_BASE_URL=https://company.atlassian.net

# Higher limits for prod
GOAL_AGENT_MAX_WORKERS=20
JIRA_RATE_LIMIT_DELAY=0.25
```

### Testing: `.env.test`

```bash
# Use test instances
REDIS_HOST=localhost
REDIS_PORT=6380  # Different port

# Mock credentials
GITHUB_PERSONAL_ACCESS_TOKEN=test_token
JIRA_API_TOKEN=test_token
```

## Security Best Practices

### 1. Credential Storage

```bash
# ✅ DO: Use .env file (gitignored)
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx

# ❌ DON'T: Hardcode in source
token = "ghp_xxx"  # NEVER DO THIS!

# ✅ DO: Use environment variables
token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
```

### 2. File Permissions

```bash
# Secure .env file
chmod 600 .env

# Verify
ls -la .env
# Should show: -rw-------
```

### 3. Git Configuration

```bash
# Ensure .env is gitignored
echo ".env" >> .gitignore
echo ".env.*" >> .gitignore

# Verify
git status  # Should not show .env
```

### 4. Token Rotation

```bash
# Rotate tokens regularly
# GitHub: 90 days
# Jira: 90 days
# Frappe: 180 days

# Script to check token age:
# python scripts/check_token_age.py
```

## Configuration Testing

### Test Individual Services

```bash
# Redis
python -c "
from servers.config import RedisConfig
c = RedisConfig()
print(f'✓ Redis: {c.host}:{c.port}')
"

# GitHub
python -c "
from servers.config import GitHubConfig
c = GitHubConfig()
print(f'✓ GitHub token: {c.token[:10]}...')
"

# Jira
python -c "
from servers.config import JiraConfig
c = JiraConfig()
print(f'✓ Jira: {c.base_url}')
"
```

### Test All Configuration

```bash
# Run comprehensive tests
python scripts/test_servers.py

# Expected output:
# ✓ Redis connection successful
# ✓ GitHub authentication successful
# ✓ Jira authentication successful
# ✓ All configurations valid
```

## Troubleshooting

### Missing Required Fields

```bash
# Error: Missing required field: api_key

# Solution:
# 1. Check .env file exists
ls -la .env

# 2. Check variable is set
grep GITHUB_PERSONAL_ACCESS_TOKEN .env

# 3. Check no typos
# Correct:   GITHUB_PERSONAL_ACCESS_TOKEN
# Incorrect: GITHUB_TOKEN
```

### Invalid URL Format

```bash
# Error: Invalid JIRA_BASE_URL

# Common issues:
# ❌ Trailing slash:  https://company.atlassian.net/
# ❌ HTTP instead:    http://company.atlassian.net
# ❌ Missing domain:  https://atlassian.net
# ❌ Wrong protocol:  company.atlassian.net

# ✅ Correct format:
JIRA_BASE_URL=https://company.atlassian.net
```

### Authentication Failures

```bash
# GitHub authentication failed

# Solutions:
# 1. Check token format
echo $GITHUB_PERSONAL_ACCESS_TOKEN
# Should start with ghp_ or github_pat_

# 2. Check token scopes
# Visit: https://github.com/settings/tokens
# Ensure: repo, workflow checked

# 3. Test manually
curl -H "Authorization: token $GITHUB_PERSONAL_ACCESS_TOKEN" \
  https://api.github.com/user
```

### Connection Issues

```bash
# Redis connection refused

# Solutions:
# 1. Check Redis is running
redis-cli ping

# 2. Check host/port
echo $REDIS_HOST:$REDIS_PORT

# 3. Test connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
```

## Complete Example Configuration

```bash
# ===========================================
# PRODUCTION CONFIGURATION
# ===========================================

# ===========================================
# REQUIRED: Redis (Memory Cache)
# ===========================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_HEALTH_CHECK_INTERVAL=30
REDIS_RETRY_ON_TIMEOUT=true
REDIS_DECODE_RESPONSES=true

# ===========================================
# REQUIRED: Goal Agent
# ===========================================
GOAL_AGENT_MAX_WORKERS=10
GOAL_AGENT_TIMEOUT=30
CACHE_ENABLED=true

# ===========================================
# OPTIONAL: GitHub
# ===========================================
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
GITHUB_DEFAULT_BRANCH=main
GITHUB_TIMEOUT=30
GITHUB_MAX_RETRIES=3

# ===========================================
# OPTIONAL: Jira
# ===========================================
JIRA_BASE_URL=https://company.atlassian.net
JIRA_EMAIL=developer@company.com
JIRA_API_TOKEN=your_token_here
JIRA_PROJECT_KEY=PROJ
JIRA_TIMEOUT=30
JIRA_MAX_RETRIES=3
JIRA_RATE_LIMIT_DELAY=0.5

# ===========================================
# OPTIONAL: Google Search
# ===========================================
GOOGLE_API_KEY=AIzaSy_your_key_here
GOOGLE_SEARCH_ENGINE_ID=your_id_here
GOOGLE_TIMEOUT=15
GOOGLE_MAX_RETRIES=3

# ===========================================
# OPTIONAL: Frappe/ERPNext
# ===========================================
FRAPPE_SITE_URL=http://127.0.0.1:8005
FRAPPE_API_KEY=your_key_here
FRAPPE_API_SECRET=your_secret_here
FRAPPE_TIMEOUT=30
FRAPPE_MAX_RETRIES=3
FRAPPE_POOL_CONNECTIONS=5
FRAPPE_POOL_MAXSIZE=10

# ===========================================
# GLOBAL SETTINGS
# ===========================================
CONNECTION_POOL_SIZE=10
DEFAULT_TIMEOUT=30
DEFAULT_MAX_RETRIES=3
```

## Reference

### All Configuration Classes

```python
from servers.config import (
    RedisConfig,      # Memory cache configuration
    GoalAgentConfig,  # Goal agent configuration
    GitHubConfig,     # GitHub API configuration
    JiraConfig,       # Jira API configuration
    InternetConfig,   # Google Search configuration
    FrappeConfig,     # Frappe/ERPNext configuration
)
```

### Validation Function

```python
from servers.config import validate_config

# Validate configuration
config = GitHubConfig()
validate_config(config, logger)
# Raises ConfigurationError if invalid
```