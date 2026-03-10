"""
Google Calendar Tool
Read, create, update, and delete calendar events.
Checks availability for appointment booking.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


# NOTE: Full Google Calendar OAuth implementation requires a multi-step flow.
# For Phase 1, we provide the core functions that will be connected to
# Google OAuth in Phase 2. For now, they work with a mock calendar.

# In-memory mock calendar for development
_mock_events = []


async def list_events(
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: int = 10,
) -> dict:
    """
    List upcoming calendar events.

    Args:
        time_min: Start of time range (default: now)
        time_max: End of time range (default: 7 days from now)
        max_results: Maximum events to return

    Returns:
        dict with 'events' list
    """
    now = datetime.now(timezone.utc)
    time_min = time_min or now
    time_max = time_max or now + timedelta(days=7)

    # Filter mock events in the time range
    filtered = [
        e for e in _mock_events
        if time_min <= e["start"] <= time_max
    ]
    filtered.sort(key=lambda x: x["start"])

    return {
        "events": [
            {
                "id": e["id"],
                "title": e["title"],
                "start": e["start"].isoformat(),
                "end": e["end"].isoformat(),
                "location": e.get("location", ""),
                "description": e.get("description", ""),
            }
            for e in filtered[:max_results]
        ]
    }


async def check_availability(
    date: datetime,
    duration_minutes: int = 60,
) -> dict:
    """
    Check available time slots on a given date.

    Args:
        date: The date to check
        duration_minutes: Duration of the needed slot

    Returns:
        dict with 'available_slots' list of {"start": ..., "end": ...}
    """
    # Business hours: 9 AM to 6 PM
    day_start = date.replace(hour=9, minute=0, second=0, microsecond=0)
    day_end = date.replace(hour=18, minute=0, second=0, microsecond=0)

    # Get existing events for the day
    result = await list_events(day_start, day_end)
    existing = result["events"]

    # Find available slots
    available = []
    current = day_start

    for event in existing:
        event_start = datetime.fromisoformat(event["start"])
        event_end = datetime.fromisoformat(event["end"])

        gap = (event_start - current).total_seconds() / 60
        if gap >= duration_minutes:
            available.append({
                "start": current.isoformat(),
                "end": (current + timedelta(minutes=duration_minutes)).isoformat(),
            })
        current = max(current, event_end)

    # Check remaining time after last event
    remaining = (day_end - current).total_seconds() / 60
    if remaining >= duration_minutes:
        available.append({
            "start": current.isoformat(),
            "end": (current + timedelta(minutes=duration_minutes)).isoformat(),
        })

    return {"available_slots": available, "date": date.strftime("%Y-%m-%d")}


async def create_event(
    title: str,
    start: datetime,
    end: datetime,
    location: Optional[str] = None,
    description: Optional[str] = None,
    reminder_minutes: int = 60,
) -> dict:
    """
    Create a new calendar event.

    Args:
        title: Event title
        start: Start datetime
        end: End datetime
        location: Optional location/address
        description: Optional details
        reminder_minutes: Minutes before event to send reminder

    Returns:
        dict with created event details
    """
    import uuid
    event = {
        "id": str(uuid.uuid4()),
        "title": title,
        "start": start,
        "end": end,
        "location": location or "",
        "description": description or "",
        "reminder_minutes": reminder_minutes,
    }
    _mock_events.append(event)

    return {
        "success": True,
        "event": {
            "id": event["id"],
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "location": location,
        },
        "message": f"✅ Event '{title}' created for {start.strftime('%B %d at %I:%M %p')}",
    }


async def delete_event(event_id: str) -> dict:
    """Delete a calendar event by ID."""
    global _mock_events
    before = len(_mock_events)
    _mock_events = [e for e in _mock_events if e["id"] != event_id]

    if len(_mock_events) < before:
        return {"success": True, "message": "Event deleted"}
    return {"success": False, "message": "Event not found"}
