"""Tests for data models."""

import json
from datetime import datetime

import pytest

from tvt.storage.models import Event, EventType, Source


class TestSource:
    """Tests for Source enum."""

    def test_source_values(self):
        """Test that Source enum has expected values."""
        assert Source.SLACK.value == "slack"
        assert Source.TEAMS.value == "teams"
        assert Source.CALENDAR.value == "calendar"
        assert Source.MANUAL.value == "manual"

    def test_source_from_string(self):
        """Test creating Source from string value."""
        assert Source("slack") == Source.SLACK
        assert Source("teams") == Source.TEAMS

    def test_source_invalid_value(self):
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError):
            Source("invalid")


class TestEventType:
    """Tests for EventType enum."""

    def test_presence_states(self):
        """Test presence state event types."""
        assert EventType.ACTIVE.value == "active"
        assert EventType.AWAY.value == "away"
        assert EventType.DND.value == "dnd"

    def test_communication_types(self):
        """Test communication event types."""
        assert EventType.HUDDLE.value == "huddle"
        assert EventType.VOICE_CALL.value == "voice_call"
        assert EventType.MEETING.value == "meeting"

    def test_work_states(self):
        """Test work state event types."""
        assert EventType.FOCUS_TIME.value == "focus_time"
        assert EventType.BREAK.value == "break"

    def test_event_type_from_string(self):
        """Test creating EventType from string value."""
        assert EventType("active") == EventType.ACTIVE
        assert EventType("huddle") == EventType.HUDDLE


class TestEvent:
    """Tests for Event dataclass."""

    def test_create_event_minimal(self):
        """Test creating event with minimal required fields."""
        start = datetime.now()
        event = Event(
            source=Source.SLACK,
            event_type=EventType.ACTIVE,
            start_time=start,
        )

        assert event.source == Source.SLACK
        assert event.event_type == EventType.ACTIVE
        assert event.start_time == start
        assert event.end_time is None
        assert event.metadata == {}
        assert event.id is not None
        assert event.created_at is not None

    def test_create_event_full(self):
        """Test creating event with all fields."""
        start = datetime(2025, 1, 15, 10, 0, 0)
        end = datetime(2025, 1, 15, 10, 30, 0)
        metadata = {"channel": "general", "participants": 3}

        event = Event(
            source=Source.SLACK,
            event_type=EventType.HUDDLE,
            start_time=start,
            end_time=end,
            metadata=metadata,
            id="custom-id-123",
        )

        assert event.id == "custom-id-123"
        assert event.end_time == end
        assert event.metadata == metadata

    def test_duration_minutes_with_end_time(self):
        """Test duration calculation when end_time is set."""
        start = datetime(2025, 1, 15, 10, 0, 0)
        end = datetime(2025, 1, 15, 10, 45, 0)

        event = Event(
            source=Source.SLACK,
            event_type=EventType.HUDDLE,
            start_time=start,
            end_time=end,
        )

        assert event.duration_minutes == 45

    def test_duration_minutes_without_end_time(self):
        """Test duration is None when end_time not set."""
        event = Event(
            source=Source.SLACK,
            event_type=EventType.ACTIVE,
            start_time=datetime.now(),
        )

        assert event.duration_minutes is None

    def test_duration_minutes_partial_minute(self):
        """Test duration rounds down partial minutes."""
        start = datetime(2025, 1, 15, 10, 0, 0)
        end = datetime(2025, 1, 15, 10, 30, 45)  # 30 minutes 45 seconds

        event = Event(
            source=Source.SLACK,
            event_type=EventType.HUDDLE,
            start_time=start,
            end_time=end,
        )

        assert event.duration_minutes == 30

    def test_to_dict(self, sample_event):
        """Test converting event to dictionary."""
        data = sample_event.to_dict()

        assert data["source"] == "slack"
        assert data["event_type"] == "huddle"
        assert data["start_time"] == "2025-01-15T10:00:00"
        assert data["end_time"] == "2025-01-15T10:30:00"
        assert data["duration_minutes"] == 30
        assert json.loads(data["metadata"]) == {"channel": "general"}

    def test_to_dict_without_end_time(self):
        """Test to_dict when end_time is None."""
        event = Event(
            source=Source.SLACK,
            event_type=EventType.ACTIVE,
            start_time=datetime(2025, 1, 15, 10, 0, 0),
        )

        data = event.to_dict()
        assert data["end_time"] is None
        assert data["duration_minutes"] is None

    def test_from_dict(self):
        """Test creating event from dictionary."""
        data = {
            "id": "test-id-456",
            "source": "slack",
            "event_type": "huddle",
            "start_time": "2025-01-15T10:00:00",
            "end_time": "2025-01-15T10:30:00",
            "metadata": '{"channel": "general"}',
            "created_at": "2025-01-15T09:55:00",
        }

        event = Event.from_dict(data)

        assert event.id == "test-id-456"
        assert event.source == Source.SLACK
        assert event.event_type == EventType.HUDDLE
        assert event.start_time == datetime(2025, 1, 15, 10, 0, 0)
        assert event.end_time == datetime(2025, 1, 15, 10, 30, 0)
        assert event.metadata == {"channel": "general"}
        assert event.duration_minutes == 30

    def test_from_dict_without_end_time(self):
        """Test from_dict when end_time is None."""
        data = {
            "id": "test-id-789",
            "source": "slack",
            "event_type": "active",
            "start_time": "2025-01-15T10:00:00",
            "end_time": None,
            "metadata": "{}",
            "created_at": "2025-01-15T10:00:00",
        }

        event = Event.from_dict(data)

        assert event.end_time is None
        assert event.duration_minutes is None

    def test_from_dict_empty_metadata(self):
        """Test from_dict with empty metadata string."""
        data = {
            "id": "test-id",
            "source": "slack",
            "event_type": "active",
            "start_time": "2025-01-15T10:00:00",
            "end_time": None,
            "metadata": "",
            "created_at": "2025-01-15T10:00:00",
        }

        event = Event.from_dict(data)
        assert event.metadata == {}

    def test_roundtrip_to_from_dict(self, sample_event):
        """Test that to_dict and from_dict are inverse operations."""
        data = sample_event.to_dict()
        restored = Event.from_dict(data)

        assert restored.id == sample_event.id
        assert restored.source == sample_event.source
        assert restored.event_type == sample_event.event_type
        assert restored.start_time == sample_event.start_time
        assert restored.end_time == sample_event.end_time
        assert restored.metadata == sample_event.metadata
        assert restored.duration_minutes == sample_event.duration_minutes

    def test_unique_ids_generated(self):
        """Test that auto-generated IDs are unique."""
        events = [
            Event(
                source=Source.SLACK,
                event_type=EventType.ACTIVE,
                start_time=datetime.now(),
            )
            for _ in range(100)
        ]

        ids = [e.id for e in events]
        assert len(set(ids)) == 100  # All unique

    def test_event_with_complex_metadata(self):
        """Test event with nested metadata."""
        metadata = {
            "participants": ["user1", "user2", "user3"],
            "channel": {"id": "C123", "name": "general"},
            "tags": ["important", "followup"],
        }

        event = Event(
            source=Source.SLACK,
            event_type=EventType.HUDDLE,
            start_time=datetime.now(),
            metadata=metadata,
        )

        data = event.to_dict()
        restored = Event.from_dict(data)

        assert restored.metadata == metadata
