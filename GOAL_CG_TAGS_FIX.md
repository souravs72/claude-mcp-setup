# Goal: Fix CG Tags Rendering Bug

## 🎯 Goal Overview

**Goal ID**: GOAL-0003  
**Priority**: HIGH  
**Status**: IN_PROGRESS  
**Created**: October 12, 2025

### Problem Statement

New tags added in the 'CG Tags' doctype are not rendering in the AddTaskSheet component. This affects both frontend and backend.

### Affected Components

- **Backend**: CG Tags doctype API
- **Frontend**: AddTaskSheet component
- **Repos**: frontend-app, backend-api

## 📋 Tasks Breakdown (7 Tasks)

### Investigation Tasks (3 tasks)

#### TASK-0001, TASK-0002: Investigate CG Tags Backend API

- **Type**: Investigation
- **Priority**: HIGH
- **Effort**: 1-2 hours
- **Tools**: frappe_server
- **Objective**: Check if new tags are being saved correctly to database
- **What to check**:
  - CG Tags doctype schema
  - Save/create API endpoint
  - Database queries
  - Response format

#### TASK-0003: Check AddTaskSheet Frontend Component

- **Type**: Investigation
- **Priority**: HIGH
- **Effort**: 1 hour
- **Objective**: Identify where tags are fetched and rendered
- **What to check**:
  - Tag fetching logic
  - State management
  - Render function
  - Data flow from API to UI

### Implementation Tasks (2 tasks)

#### TASK-0004: Fix Backend API Endpoint

- **Type**: Backend
- **Priority**: HIGH
- **Effort**: 2-3 hours
- **Repo**: backend-api
- **Objective**: Ensure newly added tags are returned in API response
- **Potential fixes**:
  - Update API query to include new tags
  - Fix caching that might exclude new tags
  - Update serialization/response format
  - Add proper ordering (newest first?)

#### TASK-0005: Fix Frontend AddTaskSheet Component

- **Type**: Frontend
- **Priority**: HIGH
- **Effort**: 2-3 hours
- **Repo**: frontend-app
- **Objective**: Update tag fetching logic to include new tags
- **Potential fixes**:
  - Refresh tags after creation
  - Fix state update logic
  - Clear component cache
  - Re-fetch tags on component mount/update

### Enhancement Tasks (1 task)

#### TASK-0006: Add Real-time Tag Refresh

- **Type**: Enhancement
- **Priority**: MEDIUM
- **Effort**: 1-2 hours
- **Objective**: Add real-time refresh mechanism or cache invalidation
- **Implementation ideas**:
  - WebSocket for real-time updates
  - Polling mechanism
  - Cache invalidation on tag creation
  - Event-driven tag refresh

### Testing Tasks (1 task)

#### TASK-0007: End-to-End Testing

- **Type**: Testing
- **Priority**: HIGH
- **Effort**: 1 hour
- **Objective**: Verify new tags render immediately after creation
- **Test cases**:
  - Create new tag in CG Tags doctype
  - Open AddTaskSheet component
  - Verify new tag appears in the list
  - Test with multiple tags
  - Test edge cases (special characters, long names, etc.)

## 🔄 Execution Plan

All tasks are currently **ready to execute** (no dependencies).

### Recommended Order:

1. **Phase 1: Investigation** (Parallel)

   - Start TASK-0001/0002 and TASK-0003 simultaneously
   - Goal: Understand the bug root cause

2. **Phase 2: Implementation** (After investigation)

   - Fix backend (TASK-0004)
   - Fix frontend (TASK-0005)
   - These can be done in parallel if you have separate devs

3. **Phase 3: Enhancement** (Optional)

   - Add real-time refresh (TASK-0006)
   - This can be done separately or skipped initially

4. **Phase 4: Testing** (Final)
   - Run end-to-end tests (TASK-0007)
   - Verify the fix works

## 📊 Progress Tracking

### View Goal Status

```bash
# Using PostgreSQL directly
docker exec mcp-postgres psql -U postgres -d mcp_goals -c \
  "SELECT * FROM goals WHERE id='GOAL-0003';"

# View all tasks
docker exec mcp-postgres psql -U postgres -d mcp_goals -c \
  "SELECT id, description, status FROM tasks WHERE goal_id='GOAL-0003';"
```

### Using Python/MCP Tools

```python
from servers.goal_agent_server import agent

# Get goal details
goal = agent.get_goal('GOAL-0003')

# Get next tasks to work on
next_tasks = agent.get_next_tasks('GOAL-0003')

# Update task status
agent.update_task_status('TASK-0001', 'in_progress')
agent.update_task_status('TASK-0001', 'completed', result={'findings': '...'})
```

## 🔍 Investigation Checklist

### Backend Investigation (TASK-0001, TASK-0002)

- [ ] Check CG Tags doctype definition
- [ ] Verify API endpoint for fetching tags
- [ ] Test tag creation in Frappe
- [ ] Check database to see if tags are saved
- [ ] Review API response format
- [ ] Check for any caching layers

### Frontend Investigation (TASK-0003)

- [ ] Locate AddTaskSheet component file
- [ ] Find tag fetching function/hook
- [ ] Check state management for tags
- [ ] Review tag rendering logic
- [ ] Check if tags are cached in frontend
- [ ] Verify API call for tags

## 🐛 Common Bug Patterns to Look For

### Backend Issues:

1. **Caching**: Tags cached and not refreshing
2. **Query**: SQL query not including recent tags
3. **Filtering**: Tags filtered out by date/status
4. **Serialization**: New tags not included in response

### Frontend Issues:

1. **State**: Component state not updating
2. **Cache**: Browser/React cache holding old data
3. **Lifecycle**: Tags fetched only on mount, not on update
4. **Timing**: Race condition between tag creation and fetch

## 💡 Suggested Approaches

### Quick Wins:

1. Add cache-busting to tag fetch
2. Force re-fetch after tag creation
3. Clear component cache on tag add

### Proper Solutions:

1. WebSocket subscription to tag changes
2. Event emitter on tag creation
3. Optimistic UI updates
4. Proper cache invalidation

## 📝 Update Task Status

When you complete a task, update its status:

```python
# Mark task as in progress
agent.update_task_status('TASK-0001', 'in_progress')

# Mark task as completed with results
agent.update_task_status('TASK-0001', 'completed', result={
    'findings': 'Tags are saved correctly, issue is in API query',
    'root_cause': 'Query filters out tags created in last 24h',
    'fix_location': 'api/v1/tags.py line 45'
})
```

## 🎯 Success Criteria

The bug is fixed when:

- ✅ New tag created in CG Tags doctype
- ✅ AddTaskSheet component opens
- ✅ New tag appears in the tag list immediately
- ✅ No page refresh required
- ✅ Works consistently across all scenarios

## 📚 Related Files

This goal is tracking these repositories:

- `frontend-app` - AddTaskSheet component
- `backend-api` - CG Tags API endpoints

## 🔗 Database Location

All goal and task data is stored in:

- **Database**: PostgreSQL (Docker container `mcp-postgres`)
- **Port**: 5433
- **Database Name**: mcp_goals
- **Tables**: goals, tasks

Access: `docker exec -it mcp-postgres psql -U postgres -d mcp_goals`

---

**Status as of**: October 13, 2025  
**Total Tasks**: 7  
**Completed**: 0  
**In Progress**: 0  
**Pending**: 7
