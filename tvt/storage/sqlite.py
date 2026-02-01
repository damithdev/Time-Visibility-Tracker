"""SQLite storage backend for Time Visibility Tracker."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from tvt.storage.models import Event, EventType, Source

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_minutes INTEGER,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_time ON events(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);

CREATE TABLE IF NOT EXISTS presence_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    state TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    raw_data JSON
);

CREATE INDEX IF NOT EXISTS idx_presence_timestamp ON presence_states(timestamp);
CREATE INDEX IF NOT EXISTS idx_presence_source ON presence_states(source);
"""


class SQLiteStorage:
    """SQLite storage backend for events and presence data."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.tvt/data.db
        """
        if db_path is None:
            db_path = Path.home() / ".tvt" / "data.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_event(self, event: Event) -> None:
        """Save an event to the database."""
        with self._get_connection() as conn:
            data = event.to_dict()
            conn.execute(
                """
                INSERT OR REPLACE INTO events
                (id, source, event_type, start_time, end_time, duration_minutes, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["id"],
                    data["source"],
                    data["event_type"],
                    data["start_time"],
                    data["end_time"],
                    data["duration_minutes"],
                    data["metadata"],
                    data["created_at"],
                ),
            )

    def save_presence_state(
        self,
        source: Source,
        state: str,
        timestamp: datetime,
        raw_data: dict | None = None,
    ) -> None:
        """Save a presence state snapshot."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO presence_states (source, state, timestamp, raw_data)
                VALUES (?, ?, ?, ?)
                """,
                (
                    source.value,
                    state,
                    timestamp.isoformat(),
                    json.dumps(raw_data) if raw_data else None,
                ),
            )

    def get_events(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        source: Source | None = None,
        event_type: EventType | None = None,
    ) -> list[Event]:
        """Query events with optional filters."""
        query = "SELECT * FROM events WHERE 1=1"
        params: list = []

        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND start_time <= ?"
            params.append(end_date.isoformat())
        if source:
            query += " AND source = ?"
            params.append(source.value)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)

        query += " ORDER BY start_time DESC"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [Event.from_dict(dict(row)) for row in rows]

    def get_presence_states(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        source: Source | None = None,
    ) -> list[dict]:
        """Query presence states with optional filters."""
        query = "SELECT * FROM presence_states WHERE 1=1"
        params: list = []

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        if source:
            query += " AND source = ?"
            params.append(source.value)

        query += " ORDER BY timestamp ASC"

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_daily_summary(self, date: datetime) -> dict:
        """Get a summary of time spent in each state for a given day."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        with self._get_connection() as conn:
            # Get completed events summary
            cursor = conn.execute(
                """
                SELECT event_type, source, SUM(duration_minutes) as total_minutes
                FROM events
                WHERE start_time >= ? AND start_time <= ? AND duration_minutes IS NOT NULL
                GROUP BY event_type, source
                ORDER BY total_minutes DESC
                """,
                (start_of_day.isoformat(), end_of_day.isoformat()),
            )
            events_summary = [dict(row) for row in cursor.fetchall()]

            # Get presence state transitions for time calculation
            cursor = conn.execute(
                """
                SELECT state, timestamp, source
                FROM presence_states
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
                """,
                (start_of_day.isoformat(), end_of_day.isoformat()),
            )
            presence_records = [dict(row) for row in cursor.fetchall()]

        # Calculate time in each presence state
        state_durations: dict[str, int] = {}
        for i, record in enumerate(presence_records):
            state = record["state"]
            current_time = datetime.fromisoformat(record["timestamp"])

            if i + 1 < len(presence_records):
                next_time = datetime.fromisoformat(presence_records[i + 1]["timestamp"])
            else:
                next_time = min(datetime.now(), end_of_day)

            duration_minutes = int((next_time - current_time).total_seconds() / 60)
            state_durations[state] = state_durations.get(state, 0) + duration_minutes

        return {
            "date": date.date().isoformat(),
            "events": events_summary,
            "presence": state_durations,
            "total_tracked_minutes": sum(state_durations.values()),
        }

    def update_event_end_time(self, event_id: str, end_time: datetime) -> None:
        """Update the end time of an existing event."""
        with self._get_connection() as conn:
            # First get the start time to calculate duration
            cursor = conn.execute(
                "SELECT start_time FROM events WHERE id = ?", (event_id,)
            )
            row = cursor.fetchone()
            if row:
                start_time = datetime.fromisoformat(row["start_time"])
                duration = int((end_time - start_time).total_seconds() / 60)
                conn.execute(
                    """
                    UPDATE events SET end_time = ?, duration_minutes = ?
                    WHERE id = ?
                    """,
                    (end_time.isoformat(), duration, event_id),
                )

    def get_open_event(self, source: Source, event_type: EventType) -> Event | None:
        """Get an open (no end_time) event of a specific type."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE source = ? AND event_type = ? AND end_time IS NULL
                ORDER BY start_time DESC
                LIMIT 1
                """,
                (source.value, event_type.value),
            )
            row = cursor.fetchone()
            if row:
                return Event.from_dict(dict(row))
        return None
