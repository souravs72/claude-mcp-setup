# Production MCP Servers for Claude AI

Enterprise-grade Model Context Protocol servers extending Claude with GitHub, Jira, Frappe, and web capabilities through intelligent goal-based orchestration.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0+-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What This Does

Transforms Claude into a full-stack development assistant with:
- **Goal-Based Task Orchestration** - Break complex projects into executable tasks with dependency resolution
- **Multi-Platform Integration** - GitHub (code), Jira (tickets), Frappe (ERP), Google (search)
- **Persistent State Management** - Redis-backed caching with automatic state persistence
- **Production-Ready Architecture** - Connection pooling, retry logic, rate limiting, comprehensive logging

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      Claude Desktop                              │
│              Natural Language Interface + MCP Client             │
└────────────────────────────┬─────────────────────────────────────┘
                             │ stdio (MCP Protocol)
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌──────────────┐    ┌──────────────┐
│  Goal Agent   │    │ Memory Cache │    │   Internet   │
│               │    │              │    │              │
│ • Planning    │    │ • Redis      │    │ • Google     │
│ • Tasks       │◄───┤ • TTL        │    │   Search     │
│ • Deps        │    │ • Patterns   │    │ • Web Fetch  │
│ • Execution   │    │ • Bulk Ops   │    │ • Batch      │
└───────┬───────┘    └──────────────┘    └──────────────┘
        │
        │ Orchestrates
        │
    ┌───┴──────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  Jira  │ │ GitHub │ │ Frappe │ │  ...   │
│        │ │        │ │        │ │        │
│Issues  │ │Code    │ │ERP     │ │Custom  │
│Sprints │ │PRs     │ │DocType │ │Tools   │
└────────┘ └────────┘ └────────┘ └────────┘
```

### Request Flow

```
User: "Create a goal to add OAuth to our API"
   │
   ▼
┌─────────────────────────────────────────────┐
│         Claude Desktop (MCP Client)         │
│  1. Parses intent                           │
│  2. Routes to goal-agent-server             │
└─────────────┬───────────────────────────────┘
              │ create_goal() via stdio
              ▼
┌─────────────────────────────────────────────┐
│      Goal Agent Server (MCP Server)         │
│  1. Validates request                       │
│  2. Creates GOAL-0001                       │
│  3. Returns with cache metadata             │
└─────────────┬───────────────────────────────┘
              │ Response with _cache_status
              ▼
┌─────────────────────────────────────────────┐
│         Claude Desktop (MCP Client)         │
│  1. Sees cache metadata                     │
│  2. Auto-routes to memory-cache server      │
└─────────────┬───────────────────────────────┘
              │ cache_set() via stdio
              ▼
┌─────────────────────────────────────────────┐
│    Memory Cache Server (MCP Server)         │
│  1. Stores in Redis (TTL: 7 days)           │
│  2. Returns success                         │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
```bash
# Required
Python 3.10+
Redis 5.0+
Claude Desktop

# Optional
GitHub account + token
Jira Cloud instance + API token
Google Cloud project + API keys
Frappe/ERPNext instance
```

### Installation (5 minutes)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd claude-mcp-setup

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env - see CONFIGURATION.md for details

# 4. Start Redis (required for caching)
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:alpine

# 5. Test configuration
python scripts/start_all_servers.py
```

### Claude Desktop Configuration

**Config Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Add to config file:**
```json
{
  "mcpServers": {
    "memory-cache": {
      "command": "python",
      "args": ["/absolute/path/to/servers/memory_cache_server.py"],
      "env": {
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379"
      }
    },
    "goal-agent": {
      "command": "python",
      "args": ["/absolute/path/to/servers/goal_agent_server.py"],
      "env": {
        "GOAL_AGENT_MAX_WORKERS": "10",
        "CACHE_ENABLED": "true"
      }
    },
    "github": {
      "command": "python",
      "args": ["/absolute/path/to/servers/github_server.py"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token",
        "GITHUB_DEFAULT_BRANCH": "main"
      }
    },
    "jira": {
      "command": "python",
      "args": ["/absolute/path/to/servers/jira_server.py"],
      "env": {
        "JIRA_BASE_URL": "https://company.atlassian.net",
        "JIRA_EMAIL": "dev@company.com",
        "JIRA_API_TOKEN": "your_token",
        "JIRA_PROJECT_KEY": "PROJ"
      }
    }
  }
}
```

**Restart Claude Desktop completely** (Quit + Reopen)

## 🧪 Test Installation

```
# In Claude Desktop:

"Create a goal to test the system"
Expected: ✓ Created GOAL-0001: Test the system

"Store 'hello world' in cache with key 'test'"
Expected: ✓ Cached successfully

"Get value from cache for key 'test'"
Expected: ✓ Retrieved: hello world

"List my repositories"  # If GitHub configured
Expected: ✓ Found N repositories
```

## 📦 Available Servers

| Server | Purpose | Tools | Dependencies | Status |
|--------|---------|-------|--------------|--------|
| **memory-cache** | Redis caching with TTL | 12 | redis | Required |
| **goal-agent** | Task orchestration | 13 | - | Required |
| **github** | Code management | 10 | PyGithub | Optional |
| **jira** | Issue tracking | 18 | - | Optional |
| **internet** | Web search/fetch | 6 | - | Optional |
| **frappe** | ERP integration | 5 | - | Optional |

## 🎓 Real-World Example

```
User: "Create a goal to add rate limiting to our API"

Claude: ✓ Created GOAL-0001: Add rate limiting to our API

User: "Break it down into tasks"

Claude: ✓ Created 6 tasks:
  • TASK-0001: Research rate limiting strategies
  • TASK-0002: Design rate limit middleware (depends: TASK-0001)
  • TASK-0003: Implement Redis-based limiter (depends: TASK-0002)
  • TASK-0004: Add tests (depends: TASK-0003)
  • TASK-0005: Update documentation (depends: TASK-0003)
  • TASK-0006: Security review (depends: TASK-0004, TASK-0005)

User: "Generate execution plan"

Claude: ✓ 4-phase execution plan:
  Phase 1: TASK-0001 (research) - Start now
  Phase 2: TASK-0002 (design) - After phase 1
  Phase 3: TASK-0003 (implement) - After phase 2
           TASK-0004 (tests) - Parallel
           TASK-0005 (docs) - Parallel
  Phase 4: TASK-0006 (review) - Final gate

User: "Create Jira tickets for each task and add to current sprint"

Claude: ✓ Created 6 Jira issues: PROJ-101 through PROJ-106
        ✓ Linked dependencies in Jira
        ✓ Added to Sprint 3

User: "Create a branch for the implementation task"

Claude: ✓ Created branch: feature/rate-limiting
        ✓ Branch ready at: github.com/your-org/api/tree/feature/rate-limiting
```

## 📂 Project Structure

```
claude-mcp-setup/
├── servers/                    # MCP Server implementations
│   ├── __init__.py            # Package exports
│   ├── base_client.py         # Shared HTTP client with retry logic
│   ├── config.py              # Configuration management + validation
│   ├── logging_config.py      # Centralized logging setup
│   │
│   ├── memory_cache_server.py # Redis integration (12 tools)
│   ├── goal_agent_server.py   # Task orchestration (13 tools)
│   ├── github_server.py       # GitHub API (10 tools)
│   ├── jira_server.py         # Jira API (18 tools)
│   ├── internet_server.py     # Web search (6 tools)
│   └── frappe_server.py       # Frappe/ERPNext (5 tools)
│
├── requirements/              # Modular dependencies
│   ├── common.txt            # Shared dependencies
│   ├── redis_requirements.txt
│   ├── github_requirements.txt
│   └── ...
│
├── scripts/                   # Management scripts
│   ├── setup.py              # Automated setup wizard
│   ├── test_servers.py       # Comprehensive test suite
│   ├── start_all_servers.py  # Configuration checker
│   └── stop_all_servers.py   # Process manager
│
├── logs/                      # Auto-generated logs
│   ├── goal_agent_server.log
│   ├── memory_cache_server.log
│   └── ...
│
├── docs/                      # Documentation
│   ├── README.md             # This file
│   ├── QUICKSTART.md         # 5-minute setup
│   ├── CONFIGURATION.md      # Environment setup
│   └── README_GOAL_AGENT.md  # API reference
│
├── .env.example              # Template configuration
├── .env                      # Your configuration (gitignored)
├── requirements.txt          # All dependencies
└── pyproject.toml            # Package metadata
```

## 🔧 Technical Architecture

### Base Client Pattern

All servers inherit from `BaseClient` for consistent behavior:

```python
class BaseClient:
    """Production-ready HTTP client with:
    - Retry logic (exponential backoff)
    - Connection pooling (configurable)
    - Timeout management
    - Error parsing
    - Request logging
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        pool_connections: int = 10,
        pool_maxsize: int = 20
    ):
        # Creates session with HTTPAdapter + Retry
        # Mounts to both http:// and https://
```

**Features:**
- Automatic retries on 5xx errors and 429 (rate limits)
- Connection pooling for performance
- Structured error responses
- Request/response logging

### Configuration Management

Type-safe configuration with validation:

```python
@dataclass
class GitHubConfig(BaseConfig):
    token: str
    timeout: int = 30
    max_retries: int = 3
    default_branch: str = "main"
    
    def __post_init__(self):
        # Validates token format
        if not self.token.startswith(("ghp_", "github_pat_")):
            raise ValueError("Invalid token format")
    
    def get_required_fields(self) -> list[str]:
        return ["token"]
```

**Validation:**
- Required field checking
- URL format validation
- Credential format verification
- Type safety with dataclasses

### Error Handling

Consistent error handling across all tools:

```python
@handle_errors(logger)
def tool_function(...) -> str:
    # Tool implementation
    # Automatic JSON response
    # Error types: timeout, connection, http_error, validation
```

**Error Response Format:**
```json
{
  "error": "Description of what went wrong",
  "type": "validation|timeout|connection|http_error",
  "status_code": 404  // Only for HTTP errors
}
```

### Logging Strategy

Multi-level logging with rotation:

```python
# Console: ERROR+ only (to stderr)
# File: DEBUG+ (10MB files, 5 backups)
# Format: timestamp | level | module | function:line | message

logger.debug("Fetching issue: PROJ-123")  # Development
logger.info("Created issue: PROJ-123")    # Operations
logger.warning("Rate limit approaching")  # Attention
logger.error("API request failed")        # Errors
logger.critical("Redis connection lost")  # Fatal
```

## 🔑 Key Features Explained

### 1. Dependency Resolution

Tasks can depend on other tasks - the Goal Agent automatically:
- Validates all dependencies exist
- Detects circular dependencies
- Calculates execution phases
- Identifies parallel execution opportunities

```python
# Example: Complex dependency graph
[
  {"id": "TASK-1", "description": "Research", "dependencies": []},
  {"id": "TASK-2", "description": "Design", "dependencies": ["TASK-1"]},
  {"id": "TASK-3", "description": "Backend", "dependencies": ["TASK-2"]},
  {"id": "TASK-4", "description": "Frontend", "dependencies": ["TASK-2"]},
  {"id": "TASK-5", "description": "Tests", "dependencies": ["TASK-3", "TASK-4"]}
]

# Execution plan:
# Phase 1: TASK-1
# Phase 2: TASK-2
# Phase 3: TASK-3, TASK-4 (parallel!)
# Phase 4: TASK-5
```

### 2. State Persistence

All goals and tasks are automatically cached to Redis:

```python
# Automatic caching on create
create_goal(...)
# → Stored in Redis with 7-day TTL
# → Key: goal_agent:goal:GOAL-0001

# Restored on server restart
# → Loads full state from cache
# → All goals/tasks available immediately
```

**Cache Keys:**
- `goal_agent:goal:{id}` - Individual goals
- `goal_agent:task:{id}` - Individual tasks  
- `goal_agent:state:full` - Complete state snapshot

### 3. Thread Safety

All operations use RLock for thread safety:

```python
@with_lock
def create_goal(...):
    self.goal_counter += 1  # Thread-safe increment
    goal = Goal(...)
    self.goals[goal.id] = goal  # Thread-safe write
```

Batch operations use ThreadPoolExecutor:

```python
def batch_update_tasks(updates):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(update_task, u) for u in updates]
        results = [f.result() for f in as_completed(futures)]
```

### 4. Rate Limiting (Jira)

Automatic rate limiting prevents API throttling:

```python
def _rate_limit(self):
    if self.last_request_time:
        elapsed = (now() - self.last_request_time).total_seconds()
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
    self.last_request_time = now()
```

Configurable via `JIRA_RATE_LIMIT_DELAY` (default: 0.5s)

### 5. Connection Pooling

Efficient connection reuse:

```python
session = requests.Session()
adapter = HTTPAdapter(
    max_retries=Retry(...),
    pool_connections=10,   # Pool size
    pool_maxsize=20        # Max connections
)
session.mount("https://", adapter)
```

Reduces latency and resource usage for repeated requests.

## 📊 Performance Characteristics

| Operation | Latency | Throughput | Notes |
|-----------|---------|------------|-------|
| `create_goal` | <1ms | 1000+/s | In-memory only |
| `cache_set` | <5ms | 10k+/s | Redis local |
| `github:create_branch` | ~200ms | Limited by API | Network + GitHub |
| `jira:create_issue` | ~300ms | Limited by API | Network + Jira |
| `batch_update_tasks(10)` | ~50ms | Parallel | ThreadPoolExecutor |
| `generate_execution_plan` | <10ms | Fast | Dependency DAG traversal |

**Optimization Tips:**
- Use batch operations for multiple updates
- Increase `GOAL_AGENT_MAX_WORKERS` for more parallelism
- Configure connection pool sizes for high throughput
- Use Redis for frequently accessed data

## 🔒 Security Considerations

1. **Credentials Storage**
   - `.env` file (gitignored)
   - Environment variables only
   - No hardcoded secrets

2. **API Tokens**
   - Personal access tokens (limited scope)
   - API keys with least privilege
   - Regular rotation recommended

3. **Network Security**
   - HTTPS for all external APIs
   - Redis on localhost only (default)
   - No exposed ports

4. **Validation**
   - Input sanitization
   - Type checking with Pydantic
   - URL validation

## 🧰 Operations Guide

### Monitoring

```bash
# View logs in real-time
tail -f logs/goal_agent_server.log
tail -f logs/memory_cache_server.log

# Check Redis health
redis-cli ping  # Should return PONG
redis-cli info stats

# Check process status
ps aux | grep "server.py"
```

### Troubleshooting

```bash
# Test servers independently
python servers/memory_cache_server.py  # Should start without errors
python servers/goal_agent_server.py

# Verify configuration
python -c "from servers.config import *; print('OK')"

# Check Redis connection
python -c "import redis; r=redis.Redis(); print(r.ping())"

# Test GitHub auth
python -c "from servers.github_server import github_client; print('OK')"
```

### Maintenance

```bash
# Clear Redis cache
redis-cli FLUSHDB

# Rotate logs (automatic at 10MB)
# Or manually:
rm logs/*.log.1 logs/*.log.2

# Update dependencies
pip install -r requirements.txt --upgrade

# Stop all servers
python scripts/stop_all_servers.py
```

## 📚 Documentation

- **[QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute setup guide
- **[CONFIGURATION.md](docs/CONFIGURATION.md)** - Environment configuration
- **[README_GOAL_AGENT.md](docs/README_GOAL_AGENT.md)** - Goal Agent API reference
- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Production deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

## 🛠️ Technology Stack

- **MCP Framework**: [FastMCP](https://github.com/jlowin/fastmcp)
- **HTTP Client**: [requests](https://requests.readthedocs.io/) with connection pooling
- **GitHub**: [PyGithub](https://github.com/PyGithub/PyGithub)
- **Redis**: [redis-py](https://github.com/redis/redis-py)
- **Validation**: [Pydantic](https://docs.pydantic.dev/)
- **Logging**: Python logging with rotation
