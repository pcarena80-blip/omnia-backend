"""
User Model
Stores user accounts, preferences, and authentication data.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Profile
    full_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    timezone = Column(String, default="UTC")
    location = Column(String, nullable=True)  # Default city/area

    # Preferences (JSON blob for flexibility)
    preferences = Column(JSON, default=lambda: {
        "voice_speed": 1.0,
        "voice_id": "default",
        "formality": "professional",        # casual, professional, formal
        "proactivity": "balanced",           # passive, balanced, proactive
        "verbosity": "concise",             # brief, concise, detailed
        "default_llm": "gemini",
        "dark_mode": True,
    })

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"
