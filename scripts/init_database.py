#!/usr/bin/env python3
"""
Database initialization script for MCP Goal Agent.
Creates PostgreSQL database and tables if they don't exist.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from servers.config import PostgresConfig, load_env_file
from servers.database import DatabaseManager
from servers.logging_config import setup_logging

# Setup logging
logger = setup_logging("DatabaseInit")


def main():
    """Initialize PostgreSQL database for Goal Agent."""
    try:
        # Load environment variables
        load_env_file()

        # Get database configuration
        logger.info("Loading PostgreSQL configuration...")
        postgres_config = PostgresConfig()

        logger.info(
            f"Connecting to PostgreSQL at {postgres_config.host}:{postgres_config.port}"
        )
        logger.info(f"Database: {postgres_config.database}")

        # Create database manager
        database_url = postgres_config.get_connection_string()
        db_manager = DatabaseManager(
            database_url=database_url,
            pool_size=postgres_config.pool_size,
            max_overflow=postgres_config.max_overflow,
        )

        # Test connection
        if not db_manager.health_check():
            logger.error("Failed to connect to PostgreSQL database")
            logger.error(
                "Please check your configuration and ensure PostgreSQL is running"
            )
            sys.exit(1)

        logger.info("Successfully connected to PostgreSQL")

        # Create tables
        logger.info("Creating database tables...")
        db_manager.create_tables()
        logger.info("✓ Database tables created successfully")

        # Verify tables
        logger.info("Verifying tables...")
        goal_count = db_manager.get_goal_count()
        task_count = db_manager.get_task_count()

        logger.info(f"✓ Goals table ready (current count: {goal_count})")
        logger.info(f"✓ Tasks table ready (current count: {task_count})")

        # Close connection
        db_manager.close()

        logger.info("=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)
        logger.info(f"Database: {postgres_config.database}")
        logger.info(f"Host: {postgres_config.host}:{postgres_config.port}")
        logger.info(f"Goals: {goal_count}")
        logger.info(f"Tasks: {task_count}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        logger.error("\nTroubleshooting:")
        logger.error("1. Ensure PostgreSQL is installed and running")
        logger.error("2. Check your .env file has correct PostgreSQL configuration")
        logger.error("3. Verify database user has CREATE TABLE permissions")
        logger.error("4. Test connection: psql -h HOST -U USER -d DATABASE")
        sys.exit(1)


if __name__ == "__main__":
    main()
