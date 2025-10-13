.PHONY: help docker-up docker-down docker-logs docker-status init-db test-db backup restore clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

docker-up: ## Start PostgreSQL and Redis containers
	@echo "Starting Docker containers..."
	docker-compose up -d
	@echo "Waiting for containers to be healthy..."
	@sleep 5
	docker-compose ps

docker-down: ## Stop Docker containers
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs: ## View Docker container logs
	docker-compose logs -f

docker-status: ## Check Docker container status
	@echo "Container Status:"
	docker-compose ps
	@echo ""
	@echo "PostgreSQL Health:"
	docker exec mcp-postgres pg_isready -U postgres || echo "PostgreSQL not ready"
	@echo ""
	@echo "Redis Health:"
	docker exec mcp-redis redis-cli ping || echo "Redis not ready"

init-db: ## Initialize PostgreSQL database tables
	@echo "Initializing database..."
	python scripts/init_database.py

test-db: ## Test database connection
	@echo "Testing PostgreSQL connection..."
	docker exec mcp-postgres psql -U postgres -d mcp_goals -c "SELECT version();"
	@echo ""
	@echo "Listing tables..."
	docker exec mcp-postgres psql -U postgres -d mcp_goals -c "\dt"

backup: ## Backup PostgreSQL database
	@echo "Creating backup..."
	@mkdir -p backups
	docker exec mcp-postgres pg_dump -U postgres mcp_goals > backups/mcp_goals_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/"

restore: ## Restore PostgreSQL database (requires BACKUP_FILE=path/to/backup.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Error: BACKUP_FILE not specified"; \
		echo "Usage: make restore BACKUP_FILE=backups/mcp_goals_20250112.sql"; \
		exit 1; \
	fi
	@echo "Restoring from $(BACKUP_FILE)..."
	docker exec -i mcp-postgres psql -U postgres mcp_goals < $(BACKUP_FILE)
	@echo "Restore complete"

clean: ## Remove containers and volumes (WARNING: deletes data!)
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose down -v; \
		echo "Cleaned up"; \
	else \
		echo "Cancelled"; \
	fi

setup: docker-up init-db ## Complete setup (start containers + initialize database)
	@echo ""
	@echo "Setup complete! Run 'mcpctl run' to start MCP servers"

psql: ## Open PostgreSQL shell
	docker exec -it mcp-postgres psql -U postgres -d mcp_goals

redis: ## Open Redis CLI
	docker exec -it mcp-redis redis-cli

stats: ## Show container resource usage
	docker stats mcp-postgres mcp-redis --no-stream
