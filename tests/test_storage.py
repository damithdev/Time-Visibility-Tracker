"""Tests for storage module."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tvt.storage.models import Event, EventType, Source
from tvt.storage.sqlite import SQLiteStorage


@pytest.fixture
def storage():
    """Create a temporary storage instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield SQLiteStorage(db_path)


def test_create_storage(storage):
    """Test that storage initializes correctly."""
    assert storage.db_path.exists()


def test_save_and_get_event(storage):
    """Test saving and retrieving an event."""
    event = Event(
        source=Source.SLACK,
        event_type=EventType.HUDDLE,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(minutes=30),
        metadata={"test": "value"},
    )

    storage.save_event(event)
    events = storage.get_events(source=Source.SLACK)

    assert len(events) == 1
    assert events[0].id == event.id
    assert events[0].source == Source.SLACK
    assert events[0].event_type == EventType.HUDDLE
    assert events[0].duration_minutes == 30


def test_save_presence_state(storage):
    """Test saving presence states."""
    now = datetime.now()
    storage.save_presence_state(
        source=Source.SLACK,
        state="active",
        timestamp=now,
        raw_data={"presence": "active"},
    )

    states = storage.get_presence_states(source=Source.SLACK)
    assert len(states) == 1
    assert states[0]["state"] == "active"


def test_daily_summary(storage):
    """Test daily summary generation."""
    now = datetime.now()

    # Add some presence states
    storage.save_presence_state(Source.SLACK, "active", now)
    storage.save_presence_state(
        Source.SLACK, "huddle", now + timedelta(minutes=30)
    )
    storage.save_presence_state(
        Source.SLACK, "active", now + timedelta(minutes=60)
    )

    summary = storage.get_daily_summary(now)

    assert summary["date"] == now.date().isoformat()
    assert "presence" in summary
    assert summary["total_tracked_minutes"] >= 0


def test_update_event_end_time(storage):
    """Test updating an event's end time."""
    start = datetime.now()
    event = Event(
        source=Source.SLACK,
        event_type=EventType.HUDDLE,
        start_time=start,
    )

    storage.save_event(event)
    end = start + timedelta(minutes=45)
    storage.update_event_end_time(event.id, end)

    events = storage.get_events()
    assert len(events) == 1
    assert events[0].duration_minutes == 45


def test_get_open_event(storage):
    """Test finding open events."""
    event = Event(
        source=Source.SLACK,
        event_type=EventType.HUDDLE,
        start_time=datetime.now(),
        # No end_time - open event
    )

    storage.save_event(event)

    open_event = storage.get_open_event(Source.SLACK, EventType.HUDDLE)
    assert open_event is not None
    assert open_event.id == event.id

    # Should return None for different type
    no_event = storage.get_open_event(Source.SLACK, EventType.ACTIVE)
    assert no_event is None
