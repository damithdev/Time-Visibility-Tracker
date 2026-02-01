"""Shared pytest fixtures for TVT tests."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tvt.storage.models import Event, EventType, Source
from tvt.storage.sqlite import SQLiteStorage


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def storage(tmp_path):
    """Create a temporary SQLite storage instance."""
    db_path = tmp_path / "test.db"
    return SQLiteStorage(db_path)


@pytest.fixture
def populated_storage(storage):
    """Create storage with sample data for testing summaries."""
    now = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)

    # Add presence states throughout the day
    states = [
        ("active", now),
        ("active", now + timedelta(minutes=30)),
        ("huddle", now + timedelta(minutes=60)),
        ("huddle", now + timedelta(minutes=90)),
        ("active", now + timedelta(minutes=120)),
        ("away", now + timedelta(minutes=150)),
        ("active", now + timedelta(minutes=180)),
        ("dnd", now + timedelta(minutes=210)),
        ("active", now + timedelta(minutes=240)),
    ]

    for state, timestamp in states:
        storage.save_presence_state(
            source=Source.SLACK,
            state=state,
            timestamp=timestamp,
            raw_data={"state": state},
        )

    # Add some completed events
    huddle_event = Event(
        source=Source.SLACK,
        event_type=EventType.HUDDLE,
        start_time=now + timedelta(minutes=60),
        end_time=now + timedelta(minutes=120),
        metadata={"participants": 3},
    )
    storage.save_event(huddle_event)

    return storage


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return Event(
        source=Source.SLACK,
        event_type=EventType.HUDDLE,
        start_time=datetime(2025, 1, 15, 10, 0, 0),
        end_time=datetime(2025, 1, 15, 10, 30, 0),
        metadata={"channel": "general"},
    )


@pytest.fixture
def mock_slack_client():
    """Create a mock Slack WebClient."""
    client = MagicMock()

    # Mock auth_test response
    client.auth_test.return_value = {"user_id": "U12345"}

    # Mock users_getPresence response
    client.users_getPresence.return_value = {"presence": "active"}

    # Mock users_profile_get response
    client.users_profile_get.return_value = {
        "profile": {
            "huddle_state": "",
            "status_text": "Working",
            "status_emoji": ":computer:",
        }
    }

    # Mock dnd_info response
    client.dnd_info.return_value = {
        "dnd_enabled": False,
        "snooze_enabled": False,
    }

    return client


@pytest.fixture
def config_dir(temp_dir):
    """Create a temporary config directory."""
    config_path = temp_dir / ".tvt"
    config_path.mkdir(parents=True, exist_ok=True)
    return config_path
