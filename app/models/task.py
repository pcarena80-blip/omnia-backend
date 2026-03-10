"""
Task Model
Stores autonomous tasks the AI is executing (multi-step workflows).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON
from app.core.database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"  # Needs user confirmation
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(
        String, ForeignKey("conversations.id"), nullable=True
    )

    # Task details
    title = Column(String, nullable=False)  # e.g., "Book dentist appointment"
    description = Column(Text, nullable=True)
    task_type = Column(String, nullable=False)  # appointment, search, download, communicate
    status = Column(String, default=TaskStatus.PENDING)

    # Execution tracking
    steps = Column(JSON, default=list)  # List of step dicts with status
    current_step = Column(Integer, default=0)
    result = Column(JSON, nullable=True)  # Final output
    error = Column(Text, nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)  # For future tasks
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Task {self.title} [{self.status}]>"
