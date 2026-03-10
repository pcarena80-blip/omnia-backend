"""
Conversation & Message Models
Stores chat history across devices with multi-device sync support.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, JSON, Enum, Boolean
from app.core.database import Base
import enum


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="New Conversation")
    summary = Column(Text, nullable=True)  # AI-generated summary of conversation

    # Metadata
    device_id = Column(String, nullable=True)  # Which device started this
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String, ForeignKey("conversations.id"), nullable=False, index=True
    )
    role = Column(String, nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)

    # Optional metadata
    tool_name = Column(String, nullable=True)  # If role=tool, which tool
    tool_result = Column(JSON, nullable=True)   # Tool execution result
    token_count = Column(Integer, nullable=True)
    model_used = Column(String, nullable=True)  # Which LLM model was used

    # Voice metadata
    is_voice = Column(Boolean, default=False)  # Was this a voice message?
    audio_duration_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        preview = self.content[:50] if self.content else ""
        return f"<Message {self.role}: {preview}...>"
