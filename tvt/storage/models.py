"""Data models for Time Visibility Tracker."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Source(str, Enum):
    """Event source types."""

    SLACK = "slack"
    TEAMS = "teams"
    CALENDAR = "calendar"
    MANUAL = "manual"


class EventType(str, Enum):
    """Event types tracked by the system."""

    # Presence states
    ACTIVE = "active"
    AWAY = "away"
    DND = "dnd"

    # Communication types
    HUDDLE = "huddle"
    VOICE_CALL = "voice_call"
    MEETING = "meeting"

    # Work states
    FOCUS_TIME = "focus_time"
    BREAK = "break"


@dataclass
class Event:
    """Represents a tracked time event."""

    source: Source
    event_type: EventType
    start_time: datetime
    end_time: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def duration_minutes(self) -> int | None:
        """Calculate duration in minutes if end_time is set."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for storage."""
        return {
            "id": self.id,
            "source": self.source.value,
            "event_type": self.event_type.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create an Event from a dictionary."""
        return cls(
            id=data["id"],
            source=Source(data["source"]),
            event_type=EventType(data["event_type"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=(
                datetime.fromisoformat(data["end_time"])
                if data["end_time"]
                else None
            ),
            metadata=json.loads(data["metadata"]) if data["metadata"] else {},
            created_at=datetime.fromisoformat(data["created_at"]),
        )
