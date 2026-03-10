"""
Appointment Model
Stores booked appointments with full details and status tracking.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Float, JSON, Boolean, Integer
from app.core.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)

    # Provider details
    provider_name = Column(String, nullable=False)     # e.g., "Dr. Khan"
    provider_type = Column(String, nullable=True)       # dentist, doctor, etc.
    provider_address = Column(Text, nullable=True)
    provider_phone = Column(String, nullable=True)
    provider_rating = Column(Float, nullable=True)
    provider_reviews_count = Column(Integer, nullable=True)
    provider_google_maps_url = Column(String, nullable=True)

    # Appointment details
    appointment_datetime = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    notes = Column(Text, nullable=True)
    booking_method = Column(String, nullable=True)       # whatsapp, phone, website
    booking_confirmation = Column(Text, nullable=True)   # Confirmation message/code

    # Calendar sync
    calendar_event_id = Column(String, nullable=True)   # Google Calendar event ID
    reminder_set = Column(Boolean, default=False)

    # Status
    status = Column(String, default="confirmed")  # confirmed, cancelled, completed, no-show
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Appointment {self.provider_name} at {self.appointment_datetime}>"

