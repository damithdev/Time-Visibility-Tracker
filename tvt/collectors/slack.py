"""Slack presence collector for Time Visibility Tracker."""

from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from tvt.collectors.base import BaseCollector
from tvt.storage.models import Event, EventType, Source
from tvt.storage.sqlite import SQLiteStorage


# Mapping of Slack presence/status to EventType
PRESENCE_TO_EVENT_TYPE = {
    "active": EventType.ACTIVE,
    "away": EventType.AWAY,
    "dnd": EventType.DND,
    "huddle": EventType.HUDDLE,
}


class SlackCollector(BaseCollector):
    """Collector for Slack presence and huddle status."""

    source = Source.SLACK

    def __init__(self, storage: SQLiteStorage, token: str):
        """Initialize Slack collector.

        Args:
            storage: SQLiteStorage instance.
            token: Slack user OAuth token (xoxp-*).
        """
        super().__init__(storage)
        self.client = WebClient(token=token)
        self._user_id: str | None = None
        self._current_huddle_event_id: str | None = None

    def _get_user_id(self) -> str:
        """Get the authenticated user's ID."""
        if self._user_id is None:
            response = self.client.auth_test()
            self._user_id = response["user_id"]
        return self._user_id

    def collect(self) -> dict | None:
        """Collect current Slack presence and status.

        Returns:
            Dictionary with presence state and metadata.
        """
        try:
            user_id = self._get_user_id()

            # Get user presence
            presence_response = self.client.users_getPresence(user=user_id)
            presence = presence_response.get("presence", "unknown")

            # Get user profile for status and huddle info
            profile_response = self.client.users_profile_get(user=user_id)
            profile = profile_response.get("profile", {})

            # Check for DND status
            dnd_response = self.client.dnd_info(user=user_id)
            dnd_enabled = dnd_response.get("dnd_enabled", False)
            snooze_enabled = dnd_response.get("snooze_enabled", False)

            # Check if user is in a huddle
            huddle_state = profile.get("huddle_state", "")
            in_huddle = huddle_state == "in_a_huddle" or "huddle" in huddle_state.lower()

            # Determine effective state
            if in_huddle:
                state = "huddle"
            elif dnd_enabled or snooze_enabled:
                state = "dnd"
            else:
                state = presence  # "active" or "away"

            return {
                "state": state,
                "presence": presence,
                "in_huddle": in_huddle,
                "huddle_state": huddle_state,
                "dnd_enabled": dnd_enabled,
                "snooze_enabled": snooze_enabled,
                "status_text": profile.get("status_text", ""),
                "status_emoji": profile.get("status_emoji", ""),
            }

        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            return None
        except Exception as e:
            print(f"Error collecting Slack data: {e}")
            return None

    def process_state_change(
        self, old_state: str | None, new_state: str, timestamp: datetime
    ) -> None:
        """Process a Slack state transition and create/close events.

        Args:
            old_state: Previous state.
            new_state: Current state.
            timestamp: Time of state change.
        """
        # Close any open event for the old state
        if old_state:
            old_event_type = PRESENCE_TO_EVENT_TYPE.get(old_state)
            if old_event_type:
                open_event = self.storage.get_open_event(self.source, old_event_type)
                if open_event:
                    self.storage.update_event_end_time(open_event.id, timestamp)

        # Special handling for huddles - track as distinct events
        if old_state == "huddle" and self._current_huddle_event_id:
            self.storage.update_event_end_time(self._current_huddle_event_id, timestamp)
            self._current_huddle_event_id = None

        # Create new event for the new state
        new_event_type = PRESENCE_TO_EVENT_TYPE.get(new_state)
        if new_event_type:
            event = Event(
                source=self.source,
                event_type=new_event_type,
                start_time=timestamp,
                metadata={"transition_from": old_state},
            )
            self.storage.save_event(event)

            # Track huddle event ID for proper closing
            if new_state == "huddle":
                self._current_huddle_event_id = event.id


def create_slack_collector(storage: SQLiteStorage, token: str | None = None) -> SlackCollector:
    """Factory function to create a Slack collector.

    Args:
        storage: SQLiteStorage instance.
        token: Slack token. If not provided, reads from SLACK_USER_TOKEN env var.

    Returns:
        Configured SlackCollector instance.
    """
    import os

    if token is None:
        token = os.environ.get("SLACK_USER_TOKEN")
        if not token:
            raise ValueError(
                "Slack token not provided. Set SLACK_USER_TOKEN environment variable "
                "or pass token directly."
            )

    return SlackCollector(storage=storage, token=token)
