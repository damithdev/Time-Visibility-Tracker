"""Tests for storage module."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from tvt.storage.models import Event, EventType, Source
from tvt.storage.sqlite import SQLiteStorage


class TestSQLiteStorageInit:
    """Tests for SQLiteStorage initialization."""

    def test_create_storage_with_path(self, temp_dir):
        """Test creating storage with explicit path."""
        db_path = temp_dir / "test.db"
        storage = SQLiteStorage(db_path)

        assert storage.db_path == db_path
        assert db_path.exists()

    def test_create_storage_default_path(self):
        """Test that default path is used when not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily change home directory
            import os
            original_home = os.environ.get("HOME")
            os.environ["HOME"] = tmpdir

            try:
                storage = SQLiteStorage()
                expected_path = Path(tmpdir) / ".tvt" / "data.db"
                assert storage.db_path == expected_path
            finally:
                if original_home:
                    os.environ["HOME"] = original_home

    def test_create_storage_creates_parent_dirs(self, temp_dir):
        """Test that parent directories are created."""
        db_path = temp_dir / "deep" / "nested" / "path" / "test.db"
        storage = SQLiteStorage(db_path)

        assert db_path.exists()
        assert db_path.parent.exists()

    def test_storage_creates_tables(self, storage):
        """Test that database tables are created."""
        # Execute a query to check tables exist
        with storage._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row["name"] for row in cursor.fetchall()}

        assert "events" in tables
        assert "presence_states" in tables

    def test_storage_creates_indexes(self, storage):
        """Test that database indexes are created."""
        with storage._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            indexes = {row["name"] for row in cursor.fetchall()}

        assert "idx_events_time" in indexes
        assert "idx_events_source" in indexes
        assert "idx_presence_timestamp" in indexes


class TestEventStorage:
    """Tests for event storage operations."""

    def test_save_event(self, storage):
        """Test saving an event."""
        event = Event(
            source=Source.SLACK,
            event_type=EventType.HUDDLE,
            start_time=datetime(2025, 1, 15, 10, 0, 0),
            end_time=datetime(2025, 1, 15, 10, 30, 0),
            metadata={"channel": "general"},
        )

        storage.save_event(event)

        # Verify by querying directly
        with storage._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM events")
            assert cursor.fetchone()["count"] == 1

    def test_save_event_without_end_time(self, storage):
        """Test saving an event without end time (open event)."""
        event = Event(
            source=Source.SLACK,
            event_type=EventType.ACTIVE,
            start_time=datetime.now(),
        )

        storage.save_event(event)
        retrieved = storage.get_events()[0]

        assert retrieved.end_time is None
        assert retrieved.duration_minutes is None

    def test_save_event_replaces_existing(self, storage):
        """Test that saving event with same ID replaces it."""
        event = Event(
            id="test-id",
            source=Source.SLACK,
            event_type=EventType.HUDDLE,
            start_time=datetime(2025, 1, 15, 10, 0, 0),
        )

        storage.save_event(event)

        # Update and save again
        event.end_time = datetime(2025, 1, 15, 10, 30, 0)
        storage.save_event(event)

        events = storage.get_events()
        assert len(events) == 1
        assert events[0].end_time is not None

    def test_get_events_no_filters(self, storage):
        """Test getting all events."""
        events = [
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 15, 10, 0, 0)),
            Event(Source.TEAMS, EventType.MEETING, datetime(2025, 1, 15, 11, 0, 0)),
            Event(Source.SLACK, EventType.ACTIVE, datetime(2025, 1, 15, 12, 0, 0)),
        ]
        for e in events:
            storage.save_event(e)

        retrieved = storage.get_events()
        assert len(retrieved) == 3

    def test_get_events_filter_by_source(self, storage):
        """Test filtering events by source."""
        events = [
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 15, 10, 0, 0)),
            Event(Source.TEAMS, EventType.MEETING, datetime(2025, 1, 15, 11, 0, 0)),
            Event(Source.SLACK, EventType.ACTIVE, datetime(2025, 1, 15, 12, 0, 0)),
        ]
        for e in events:
            storage.save_event(e)

        slack_events = storage.get_events(source=Source.SLACK)
        teams_events = storage.get_events(source=Source.TEAMS)

        assert len(slack_events) == 2
        assert len(teams_events) == 1
        assert all(e.source == Source.SLACK for e in slack_events)

    def test_get_events_filter_by_event_type(self, storage):
        """Test filtering events by event type."""
        events = [
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 15, 10, 0, 0)),
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 15, 11, 0, 0)),
            Event(Source.SLACK, EventType.ACTIVE, datetime(2025, 1, 15, 12, 0, 0)),
        ]
        for e in events:
            storage.save_event(e)

        huddles = storage.get_events(event_type=EventType.HUDDLE)
        assert len(huddles) == 2

    def test_get_events_filter_by_date_range(self, storage):
        """Test filtering events by date range."""
        events = [
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 10, 10, 0, 0)),
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 15, 10, 0, 0)),
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 20, 10, 0, 0)),
        ]
        for e in events:
            storage.save_event(e)

        filtered = storage.get_events(
            start_date=datetime(2025, 1, 12),
            end_date=datetime(2025, 1, 18),
        )
        assert len(filtered) == 1
        assert filtered[0].start_time.day == 15

    def test_get_events_ordered_by_start_time_desc(self, storage):
        """Test that events are returned in descending order by start time."""
        events = [
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 15, 10, 0, 0)),
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 15, 12, 0, 0)),
            Event(Source.SLACK, EventType.HUDDLE, datetime(2025, 1, 15, 11, 0, 0)),
        ]
        for e in events:
            storage.save_event(e)

        retrieved = storage.get_events()
        times = [e.start_time for e in retrieved]
        assert times == sorted(times, reverse=True)

    def test_update_event_end_time(self, storage):
        """Test updating an event's end time."""
        start = datetime(2025, 1, 15, 10, 0, 0)
        event = Event(Source.SLACK, EventType.HUDDLE, start)
        storage.save_event(event)

        end = datetime(2025, 1, 15, 10, 45, 0)
        storage.update_event_end_time(event.id, end)

        retrieved = storage.get_events()[0]
        assert retrieved.end_time == end
        assert retrieved.duration_minutes == 45

    def test_update_event_end_time_nonexistent(self, storage):
        """Test updating end time for nonexistent event."""
        # Should not raise, just do nothing
        storage.update_event_end_time("nonexistent-id", datetime.now())

    def test_get_open_event(self, storage):
        """Test finding open events."""
        open_event = Event(Source.SLACK, EventType.HUDDLE, datetime.now())
        closed_event = Event(
            Source.SLACK,
            EventType.HUDDLE,
            datetime.now() - timedelta(hours=1),
            datetime.now() - timedelta(minutes=30),
        )

        storage.save_event(open_event)
        storage.save_event(closed_event)

        result = storage.get_open_event(Source.SLACK, EventType.HUDDLE)
        assert result is not None
        assert result.id == open_event.id

    def test_get_open_event_none_when_all_closed(self, storage):
        """Test that None is returned when all events are closed."""
        event = Event(
            Source.SLACK,
            EventType.HUDDLE,
            datetime.now() - timedelta(hours=1),
            datetime.now() - timedelta(minutes=30),
        )
        storage.save_event(event)

        result = storage.get_open_event(Source.SLACK, EventType.HUDDLE)
        assert result is None

    def test_get_open_event_filters_by_source_and_type(self, storage):
        """Test that get_open_event respects source and type filters."""
        slack_huddle = Event(Source.SLACK, EventType.HUDDLE, datetime.now())
        teams_meeting = Event(Source.TEAMS, EventType.MEETING, datetime.now())

        storage.save_event(slack_huddle)
        storage.save_event(teams_meeting)

        # Should find Slack huddle
        result = storage.get_open_event(Source.SLACK, EventType.HUDDLE)
        assert result.id == slack_huddle.id

        # Should not find Teams huddle
        result = storage.get_open_event(Source.TEAMS, EventType.HUDDLE)
        assert result is None


class TestPresenceStateStorage:
    """Tests for presence state storage operations."""

    def test_save_presence_state(self, storage):
        """Test saving a presence state."""
        storage.save_presence_state(
            source=Source.SLACK,
            state="active",
            timestamp=datetime(2025, 1, 15, 10, 0, 0),
            raw_data={"presence": "active"},
        )

        with storage._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM presence_states")
            assert cursor.fetchone()["count"] == 1

    def test_save_presence_state_without_raw_data(self, storage):
        """Test saving presence state without raw data."""
        storage.save_presence_state(
            source=Source.SLACK,
            state="active",
            timestamp=datetime.now(),
        )

        states = storage.get_presence_states()
        assert len(states) == 1
        assert states[0]["raw_data"] is None

    def test_get_presence_states_no_filters(self, storage):
        """Test getting all presence states."""
        for i in range(5):
            storage.save_presence_state(
                Source.SLACK,
                "active",
                datetime.now() + timedelta(minutes=i),
            )

        states = storage.get_presence_states()
        assert len(states) == 5

    def test_get_presence_states_filter_by_source(self, storage):
        """Test filtering presence states by source."""
        storage.save_presence_state(Source.SLACK, "active", datetime.now())
        storage.save_presence_state(Source.TEAMS, "available", datetime.now())

        slack_states = storage.get_presence_states(source=Source.SLACK)
        teams_states = storage.get_presence_states(source=Source.TEAMS)

        assert len(slack_states) == 1
        assert len(teams_states) == 1
        assert slack_states[0]["source"] == "slack"

    def test_get_presence_states_filter_by_date_range(self, storage):
        """Test filtering presence states by date range."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        for i in range(10):
            storage.save_presence_state(
                Source.SLACK,
                "active",
                base + timedelta(hours=i),
            )

        filtered = storage.get_presence_states(
            start_date=base + timedelta(hours=3),
            end_date=base + timedelta(hours=7),
        )
        assert len(filtered) == 5

    def test_get_presence_states_ordered_by_timestamp_asc(self, storage):
        """Test that presence states are ordered by timestamp ascending."""
        times = [
            datetime(2025, 1, 15, 12, 0, 0),
            datetime(2025, 1, 15, 10, 0, 0),
            datetime(2025, 1, 15, 11, 0, 0),
        ]

        for t in times:
            storage.save_presence_state(Source.SLACK, "active", t)

        states = storage.get_presence_states()
        timestamps = [s["timestamp"] for s in states]
        assert timestamps == sorted(timestamps)


class TestDailySummary:
    """Tests for daily summary generation."""

    def test_daily_summary_structure(self, storage):
        """Test that daily summary has expected structure."""
        summary = storage.get_daily_summary(datetime.now())

        assert "date" in summary
        assert "events" in summary
        assert "presence" in summary
        assert "total_tracked_minutes" in summary

    def test_daily_summary_empty_day(self, storage):
        """Test summary for a day with no data."""
        summary = storage.get_daily_summary(datetime(2020, 1, 1))

        assert summary["presence"] == {}
        assert summary["events"] == []
        assert summary["total_tracked_minutes"] == 0

    def test_daily_summary_calculates_presence_duration(self, storage):
        """Test that presence durations are calculated correctly."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        # 30 minutes active, then 30 minutes away
        storage.save_presence_state(Source.SLACK, "active", base)
        storage.save_presence_state(Source.SLACK, "away", base + timedelta(minutes=30))
        storage.save_presence_state(Source.SLACK, "active", base + timedelta(minutes=60))

        summary = storage.get_daily_summary(base)

        assert "active" in summary["presence"]
        assert "away" in summary["presence"]
        # Away should be approximately 30 minutes
        assert summary["presence"]["away"] == 30

    def test_daily_summary_includes_events(self, storage):
        """Test that completed events are included in summary."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        event = Event(
            Source.SLACK,
            EventType.HUDDLE,
            base,
            base + timedelta(minutes=45),
        )
        storage.save_event(event)

        summary = storage.get_daily_summary(base)

        assert len(summary["events"]) == 1
        assert summary["events"][0]["total_minutes"] == 45

    def test_daily_summary_aggregates_events_by_type(self, storage):
        """Test that events are aggregated by type and source."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        # Two huddles
        storage.save_event(Event(
            Source.SLACK, EventType.HUDDLE, base, base + timedelta(minutes=30)
        ))
        storage.save_event(Event(
            Source.SLACK, EventType.HUDDLE,
            base + timedelta(hours=1),
            base + timedelta(hours=1, minutes=30),
        ))

        summary = storage.get_daily_summary(base)

        # Should be aggregated
        huddle_summary = next(
            (e for e in summary["events"] if e["event_type"] == "huddle"),
            None
        )
        assert huddle_summary is not None
        assert huddle_summary["total_minutes"] == 60


class TestConnectionManagement:
    """Tests for database connection management."""

    def test_connection_rollback_on_error(self, storage):
        """Test that transactions are rolled back on error."""
        initial_count = len(storage.get_events())

        try:
            with storage._get_connection() as conn:
                conn.execute(
                    "INSERT INTO events (id, source, event_type, start_time) "
                    "VALUES (?, ?, ?, ?)",
                    ("test", "slack", "huddle", datetime.now().isoformat()),
                )
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Event should not be committed
        assert len(storage.get_events()) == initial_count

    def test_multiple_connections(self, storage):
        """Test that multiple operations use separate connections."""
        # This should not cause connection issues
        storage.save_event(Event(Source.SLACK, EventType.ACTIVE, datetime.now()))
        storage.get_events()
        storage.save_presence_state(Source.SLACK, "active", datetime.now())
        storage.get_presence_states()
        storage.get_daily_summary(datetime.now())
