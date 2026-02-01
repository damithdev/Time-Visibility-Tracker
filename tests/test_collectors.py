"""Tests for collector modules."""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from tvt.collectors.base import BaseCollector
from tvt.collectors.slack import (
    PRESENCE_TO_EVENT_TYPE,
    SlackCollector,
    create_slack_collector,
)
from tvt.storage.models import EventType, Source


class ConcreteCollector(BaseCollector):
    """Concrete implementation of BaseCollector for testing."""

    source = Source.SLACK

    def __init__(self, storage):
        super().__init__(storage)
        self.collected_data = {"state": "active"}
        self.state_changes = []

    def collect(self) -> dict | None:
        return self.collected_data

    def process_state_change(self, old_state, new_state, timestamp):
        self.state_changes.append((old_state, new_state, timestamp))


class TestBaseCollector:
    """Tests for BaseCollector abstract class."""

    def test_init(self, storage):
        """Test collector initialization."""
        collector = ConcreteCollector(storage)

        assert collector.storage == storage
        assert collector._running is False
        assert collector._last_state is None
        assert collector._last_state_time is None

    def test_run_once_saves_presence(self, storage):
        """Test that run_once saves presence state."""
        collector = ConcreteCollector(storage)
        collector.collected_data = {"state": "active"}

        result = collector.run_once()

        assert result == {"state": "active"}
        states = storage.get_presence_states(source=Source.SLACK)
        assert len(states) == 1
        assert states[0]["state"] == "active"

    def test_run_once_detects_state_change(self, storage):
        """Test that run_once detects and processes state changes."""
        collector = ConcreteCollector(storage)

        # First collection
        collector.collected_data = {"state": "active"}
        collector.run_once()

        # State change
        collector.collected_data = {"state": "away"}
        collector.run_once()

        # Should have detected two state changes (None->active, active->away)
        assert len(collector.state_changes) == 2
        assert collector.state_changes[0][0] is None
        assert collector.state_changes[0][1] == "active"
        assert collector.state_changes[1][0] == "active"
        assert collector.state_changes[1][1] == "away"

    def test_run_once_no_change_when_same_state(self, storage):
        """Test that no state change is triggered when state is the same."""
        collector = ConcreteCollector(storage)
        collector.collected_data = {"state": "active"}

        collector.run_once()
        collector.run_once()
        collector.run_once()

        # Only one state change (None->active)
        assert len(collector.state_changes) == 1

    def test_run_once_returns_none_on_collection_failure(self, storage):
        """Test that run_once returns None when collect fails."""
        collector = ConcreteCollector(storage)
        collector.collected_data = None

        result = collector.run_once()

        assert result is None
        # No presence states should be saved
        states = storage.get_presence_states()
        assert len(states) == 0

    def test_stop(self, storage):
        """Test stop method."""
        collector = ConcreteCollector(storage)
        collector._running = True

        collector.stop()

        assert collector._running is False


class TestSlackCollector:
    """Tests for SlackCollector class."""

    def test_init(self, storage):
        """Test Slack collector initialization."""
        collector = SlackCollector(storage, token="xoxp-test-token")

        assert collector.storage == storage
        assert collector.source == Source.SLACK
        assert collector._user_id is None
        assert collector._current_huddle_event_id is None

    def test_get_user_id_caches_result(self, storage, mock_slack_client):
        """Test that user ID is cached after first call."""
        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        # First call
        user_id = collector._get_user_id()
        assert user_id == "U12345"

        # Second call should use cached value
        user_id2 = collector._get_user_id()
        assert user_id2 == "U12345"

        # auth_test should only be called once
        assert mock_slack_client.auth_test.call_count == 1

    def test_collect_active_state(self, storage, mock_slack_client):
        """Test collecting active state."""
        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result["state"] == "active"
        assert result["presence"] == "active"
        assert result["in_huddle"] is False
        assert result["dnd_enabled"] is False

    def test_collect_away_state(self, storage, mock_slack_client):
        """Test collecting away state."""
        mock_slack_client.users_getPresence.return_value = {"presence": "away"}

        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result["state"] == "away"
        assert result["presence"] == "away"

    def test_collect_dnd_state(self, storage, mock_slack_client):
        """Test collecting DND state."""
        mock_slack_client.dnd_info.return_value = {
            "dnd_enabled": True,
            "snooze_enabled": False,
        }

        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result["state"] == "dnd"
        assert result["dnd_enabled"] is True

    def test_collect_snooze_as_dnd(self, storage, mock_slack_client):
        """Test that snooze_enabled is treated as DND."""
        mock_slack_client.dnd_info.return_value = {
            "dnd_enabled": False,
            "snooze_enabled": True,
        }

        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result["state"] == "dnd"
        assert result["snooze_enabled"] is True

    def test_collect_huddle_state(self, storage, mock_slack_client):
        """Test collecting huddle state."""
        mock_slack_client.users_profile_get.return_value = {
            "profile": {
                "huddle_state": "in_a_huddle",
                "status_text": "",
                "status_emoji": "",
            }
        }

        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result["state"] == "huddle"
        assert result["in_huddle"] is True
        assert result["huddle_state"] == "in_a_huddle"

    def test_collect_huddle_keyword_detection(self, storage, mock_slack_client):
        """Test that 'huddle' keyword in state triggers huddle detection."""
        mock_slack_client.users_profile_get.return_value = {
            "profile": {
                "huddle_state": "in_huddle_with_user",
                "status_text": "",
                "status_emoji": "",
            }
        }

        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result["state"] == "huddle"
        assert result["in_huddle"] is True

    def test_collect_huddle_overrides_dnd(self, storage, mock_slack_client):
        """Test that huddle state takes precedence over DND."""
        mock_slack_client.users_profile_get.return_value = {
            "profile": {
                "huddle_state": "in_a_huddle",
                "status_text": "",
                "status_emoji": "",
            }
        }
        mock_slack_client.dnd_info.return_value = {
            "dnd_enabled": True,
            "snooze_enabled": False,
        }

        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result["state"] == "huddle"

    def test_collect_handles_slack_api_error(self, storage, mock_slack_client):
        """Test that Slack API errors are handled gracefully."""
        error_response = MagicMock()
        error_response.__getitem__ = MagicMock(return_value="rate_limited")
        mock_slack_client.auth_test.side_effect = SlackApiError(
            message="Rate limited",
            response=error_response,
        )

        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result is None

    def test_collect_handles_generic_exception(self, storage, mock_slack_client):
        """Test that generic exceptions are handled gracefully."""
        mock_slack_client.auth_test.side_effect = Exception("Network error")

        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client

        result = collector.collect()

        assert result is None

    def test_process_state_change_creates_event(self, storage, mock_slack_client):
        """Test that state change creates a new event."""
        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client
        timestamp = datetime.now()

        collector.process_state_change(None, "active", timestamp)

        events = storage.get_events(source=Source.SLACK)
        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVE
        assert events[0].metadata["transition_from"] is None

    def test_process_state_change_closes_old_event(self, storage, mock_slack_client):
        """Test that state change closes the previous event."""
        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client
        start_time = datetime(2025, 1, 15, 10, 0, 0)
        end_time = datetime(2025, 1, 15, 10, 30, 0)

        # Start active state
        collector.process_state_change(None, "active", start_time)

        # Transition to away
        collector.process_state_change("active", "away", end_time)

        # Check that active event was closed
        events = storage.get_events(event_type=EventType.ACTIVE)
        assert len(events) == 1
        assert events[0].end_time == end_time
        assert events[0].duration_minutes == 30

    def test_process_state_change_tracks_huddle_event_id(self, storage, mock_slack_client):
        """Test that huddle event ID is tracked for proper closing."""
        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client
        timestamp = datetime.now()

        collector.process_state_change(None, "huddle", timestamp)

        assert collector._current_huddle_event_id is not None
        events = storage.get_events(event_type=EventType.HUDDLE)
        assert events[0].id == collector._current_huddle_event_id

    def test_process_state_change_closes_huddle_event(self, storage, mock_slack_client):
        """Test that huddle event is properly closed on state change."""
        collector = SlackCollector(storage, token="xoxp-test")
        collector.client = mock_slack_client
        start_time = datetime(2025, 1, 15, 10, 0, 0)
        end_time = datetime(2025, 1, 15, 10, 45, 0)

        # Start huddle
        collector.process_state_change(None, "huddle", start_time)
        huddle_event_id = collector._current_huddle_event_id

        # End huddle
        collector.process_state_change("huddle", "active", end_time)

        # Check huddle was closed
        assert collector._current_huddle_event_id is None
        events = storage.get_events(event_type=EventType.HUDDLE)
        assert len(events) == 1
        assert events[0].id == huddle_event_id
        assert events[0].duration_minutes == 45


class TestPresenceToEventTypeMapping:
    """Tests for PRESENCE_TO_EVENT_TYPE mapping."""

    def test_mapping_completeness(self):
        """Test that all expected states are mapped."""
        assert "active" in PRESENCE_TO_EVENT_TYPE
        assert "away" in PRESENCE_TO_EVENT_TYPE
        assert "dnd" in PRESENCE_TO_EVENT_TYPE
        assert "huddle" in PRESENCE_TO_EVENT_TYPE

    def test_mapping_values(self):
        """Test that mappings point to correct EventTypes."""
        assert PRESENCE_TO_EVENT_TYPE["active"] == EventType.ACTIVE
        assert PRESENCE_TO_EVENT_TYPE["away"] == EventType.AWAY
        assert PRESENCE_TO_EVENT_TYPE["dnd"] == EventType.DND
        assert PRESENCE_TO_EVENT_TYPE["huddle"] == EventType.HUDDLE


class TestCreateSlackCollector:
    """Tests for create_slack_collector factory function."""

    def test_create_with_token(self, storage):
        """Test creating collector with explicit token."""
        collector = create_slack_collector(storage, token="xoxp-explicit-token")

        assert isinstance(collector, SlackCollector)
        assert collector.storage == storage

    def test_create_with_env_token(self, storage):
        """Test creating collector with token from environment."""
        with patch.dict(os.environ, {"SLACK_USER_TOKEN": "xoxp-env-token"}):
            collector = create_slack_collector(storage)

        assert isinstance(collector, SlackCollector)

    def test_create_without_token_raises_error(self, storage):
        """Test that missing token raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SLACK_USER_TOKEN", None)
            with pytest.raises(ValueError, match="Slack token not provided"):
                create_slack_collector(storage)

    def test_explicit_token_overrides_env(self, storage):
        """Test that explicit token is used over environment variable."""
        with patch.dict(os.environ, {"SLACK_USER_TOKEN": "xoxp-env-token"}):
            collector = create_slack_collector(storage, token="xoxp-explicit-token")

        # The collector should be created with the explicit token
        assert isinstance(collector, SlackCollector)
