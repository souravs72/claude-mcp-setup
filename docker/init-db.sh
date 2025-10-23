#!/bin/bash
# PostgreSQL initialization script for MCP Goal Agent
# This runs automatically when the container is first created

set -e

echo "Initializing MCP Goals database..."

# Database is already created by POSTGRES_DB env var
# This script is for any additional setup

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Ensure UTF-8 encoding
    ALTER DATABASE mcp_goals SET timezone TO 'UTC';

    -- Log initialization
    SELECT 'MCP Goals database initialized successfully!' as message;
EOSQL

echo "Database initialization complete!"
