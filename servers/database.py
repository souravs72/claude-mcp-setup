#!/usr/bin/env python3
"""
Database models and manager for PostgreSQL persistence.
Provides SQLAlchemy models for Goals and Tasks with relationship management.
"""

import json
from datetime import datetime
from typing import Any, Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()


class GoalModel(Base):
    """SQLAlchemy model for Goals."""

    __tablename__ = "goals"

    id = Column(String(20), primary_key=True)
    description = Column(Text, nullable=False)
    priority = Column(String(10), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    repos = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    meta_data = Column("metadata", JSON, default=dict)

    # Relationship to tasks
    tasks = relationship(
        "TaskModel",
        back_populates="goal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_goal_status_priority", "status", "priority"),
        Index("idx_goal_created_at", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "repos": self.repos or [],
            "tasks": [task.id for task in self.tasks],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.meta_data or {},
        }


class TaskModel(Base):
    """SQLAlchemy model for Tasks."""

    __tablename__ = "tasks"

    id = Column(String(20), primary_key=True)
    goal_id = Column(
        String(20),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    priority = Column(String(10), nullable=False, index=True)
    dependencies = Column(JSON, default=list)
    repo = Column(String(255), nullable=True)
    jira_ticket = Column(String(50), nullable=True)
    estimated_effort = Column(String(50), nullable=True)
    assigned_tools = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)

    # Relationship to goal
    goal = relationship("GoalModel", back_populates="tasks")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_task_status_priority", "status", "priority"),
        Index("idx_task_goal_status", "goal_id", "status"),
        Index("idx_task_created_at", "created_at"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "description": self.description,
            "type": self.type,
            "status": self.status,
            "priority": self.priority,
            "dependencies": self.dependencies or [],
            "repo": self.repo,
            "jira_ticket": self.jira_ticket,
            "estimated_effort": self.estimated_effort,
            "assigned_tools": self.assigned_tools or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "result": self.result,
        }


class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""

    def __init__(
        self, database_url: str, pool_size: int = 10, max_overflow: int = 20
    ) -> None:
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection string
            pool_size: Number of connections to keep in pool
            max_overflow: Maximum overflow connections
        """
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False,  # Set to True for SQL logging
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables (USE WITH CAUTION)."""
        Base.metadata.drop_all(bind=self.engine)

    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions.

        Usage:
            with db_manager.get_session() as session:
                session.query(GoalModel).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close database engine and cleanup resources."""
        if self.engine:
            self.engine.dispose()

    # Goal Operations
    def create_goal(
        self,
        goal_id: str,
        description: str,
        priority: str,
        repos: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new goal and return as dict."""
        with self.get_session() as session:
            goal = GoalModel(
                id=goal_id,
                description=description,
                priority=priority,
                status="planned",
                repos=repos,
                meta_data=metadata,
            )
            session.add(goal)
            session.flush()
            session.refresh(goal)
            # Convert to dict while session is still active
            return goal.to_dict()

    def get_goal(self, goal_id: str) -> Optional[GoalModel]:
        """Get a goal by ID."""
        with self.get_session() as session:
            goal = session.query(GoalModel).filter(GoalModel.id == goal_id).first()
            if goal:
                # Detach from session to use outside context
                session.expunge(goal)
            return goal

    def list_goals(
        self, status: Optional[str] = None, priority: Optional[str] = None
    ) -> list[GoalModel]:
        """List goals with optional filters."""
        with self.get_session() as session:
            query = session.query(GoalModel)

            if status:
                query = query.filter(GoalModel.status == status)
            if priority:
                query = query.filter(GoalModel.priority == priority)

            goals = query.order_by(GoalModel.created_at.desc()).all()

            # Detach from session
            for goal in goals:
                session.expunge(goal)

            return goals

    def update_goal(
        self,
        goal_id: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        repos: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[GoalModel]:
        """Update a goal."""
        with self.get_session() as session:
            goal = session.query(GoalModel).filter(GoalModel.id == goal_id).first()
            if not goal:
                return None

            if description is not None:
                goal.description = description
            if priority is not None:
                goal.priority = priority
            if status is not None:
                goal.status = status
            if repos is not None:
                goal.repos = repos
            if metadata is not None:
                if goal.meta_data:
                    goal.meta_data.update(metadata)
                else:
                    goal.meta_data = metadata

            goal.updated_at = datetime.utcnow()
            session.flush()
            session.refresh(goal)
            session.expunge(goal)
            return goal

    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal and all its tasks (cascading)."""
        with self.get_session() as session:
            goal = session.query(GoalModel).filter(GoalModel.id == goal_id).first()
            if not goal:
                return False
            session.delete(goal)
            return True

    # Task Operations
    def create_task(
        self,
        task_id: str,
        goal_id: str,
        description: str,
        task_type: str,
        priority: str,
        dependencies: list[str],
        repo: Optional[str] = None,
        jira_ticket: Optional[str] = None,
        estimated_effort: Optional[str] = None,
        assigned_tools: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Create a new task and return as dict."""
        with self.get_session() as session:
            task = TaskModel(
                id=task_id,
                goal_id=goal_id,
                description=description,
                type=task_type,
                status="pending",
                priority=priority,
                dependencies=dependencies,
                repo=repo,
                jira_ticket=jira_ticket,
                estimated_effort=estimated_effort,
                assigned_tools=assigned_tools or [],
            )
            session.add(task)
            session.flush()
            session.refresh(task)
            # Convert to dict while session is still active
            return task.to_dict()

    def get_task(self, task_id: str) -> Optional[TaskModel]:
        """Get a task by ID."""
        with self.get_session() as session:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if task:
                session.expunge(task)
            return task

    def list_tasks(
        self,
        goal_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> list[TaskModel]:
        """List tasks with optional filters."""
        with self.get_session() as session:
            query = session.query(TaskModel)

            if goal_id:
                query = query.filter(TaskModel.goal_id == goal_id)
            if status:
                query = query.filter(TaskModel.status == status)
            if priority:
                query = query.filter(TaskModel.priority == priority)

            tasks = query.order_by(TaskModel.created_at.desc()).all()

            # Detach from session
            for task in tasks:
                session.expunge(task)

            return tasks

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        result: Optional[Any] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[TaskModel]:
        """Update a task."""
        with self.get_session() as session:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not task:
                return None

            if status is not None:
                task.status = status
            if result is not None:
                task.result = result
            if completed_at is not None:
                task.completed_at = completed_at

            task.updated_at = datetime.utcnow()
            session.flush()
            session.refresh(task)
            session.expunge(task)
            return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        with self.get_session() as session:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if not task:
                return False
            session.delete(task)
            return True

    def get_task_count(self) -> int:
        """Get total number of tasks."""
        with self.get_session() as session:
            return session.query(TaskModel).count()

    def get_goal_count(self) -> int:
        """Get total number of goals."""
        with self.get_session() as session:
            return session.query(GoalModel).count()

    def health_check(self) -> bool:
        """Check database connection health."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False
