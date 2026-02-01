"""Tests for summary generation module."""

import io
from datetime import datetime, timedelta

from rich.console import Console

from tvt.storage.models import Source
from tvt.summary import (
    export_summary_csv,
    format_duration,
    generate_daily_summary,
    generate_weekly_summary,
    get_state_emoji,
)


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_minutes_only(self):
        """Test formatting when less than an hour."""
        assert format_duration(0) == "0m"
        assert format_duration(1) == "1m"
        assert format_duration(30) == "30m"
        assert format_duration(59) == "59m"

    def test_hours_only(self):
        """Test formatting when exact hours."""
        assert format_duration(60) == "1h"
        assert format_duration(120) == "2h"
        assert format_duration(180) == "3h"

    def test_hours_and_minutes(self):
        """Test formatting with hours and minutes."""
        assert format_duration(61) == "1h 1m"
        assert format_duration(90) == "1h 30m"
        assert format_duration(150) == "2h 30m"
        assert format_duration(375) == "6h 15m"

    def test_large_durations(self):
        """Test formatting large durations."""
        assert format_duration(480) == "8h"  # Full workday
        assert format_duration(600) == "10h"
        assert format_duration(1440) == "24h"  # Full day


class TestGetStateEmoji:
    """Tests for get_state_emoji function."""

    def test_known_states(self):
        """Test emoji output for known states."""
        assert "green" in get_state_emoji("active")
        assert "yellow" in get_state_emoji("away")
        assert "red" in get_state_emoji("dnd")
        assert "blue" in get_state_emoji("huddle")

    def test_case_insensitive(self):
        """Test that state matching is case insensitive."""
        assert get_state_emoji("Active") == get_state_emoji("active")
        assert get_state_emoji("AWAY") == get_state_emoji("away")
        assert get_state_emoji("DND") == get_state_emoji("dnd")

    def test_unknown_state(self):
        """Test fallback for unknown states."""
        assert get_state_emoji("unknown") == "•"
        assert get_state_emoji("custom_state") == "•"


class TestGenerateDailySummary:
    """Tests for generate_daily_summary function."""

    def test_returns_summary_dict(self, storage):
        """Test that function returns summary dictionary."""
        date = datetime.now()
        console = Console(file=io.StringIO(), force_terminal=True)

        result = generate_daily_summary(storage, date, console)

        assert isinstance(result, dict)
        assert "date" in result
        assert "presence" in result
        assert "events" in result
        assert "total_tracked_minutes" in result

    def test_uses_today_as_default(self, storage):
        """Test that today's date is used when not specified."""
        console = Console(file=io.StringIO(), force_terminal=True)

        result = generate_daily_summary(storage, console=console)

        assert result["date"] == datetime.now().date().isoformat()

    def test_displays_presence_data(self, populated_storage):
        """Test that presence data is displayed when available."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        date = datetime.now()

        generate_daily_summary(populated_storage, date, console)

        output_text = output.getvalue()
        assert "Time by State" in output_text

    def test_displays_no_data_message(self, storage):
        """Test message when no data available."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        # Use a date far in the past with no data
        date = datetime(2020, 1, 1)

        generate_daily_summary(storage, date, console)

        output_text = output.getvalue()
        assert "No presence data" in output_text

    def test_displays_completed_events(self, populated_storage):
        """Test that completed events are shown."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        date = datetime.now()

        result = generate_daily_summary(populated_storage, date, console)

        # The populated_storage fixture includes a completed huddle event
        assert len(result["events"]) > 0


class TestGenerateWeeklySummary:
    """Tests for generate_weekly_summary function."""

    def test_returns_seven_summaries(self, storage):
        """Test that function returns 7 daily summaries."""
        console = Console(file=io.StringIO(), force_terminal=True)

        result = generate_weekly_summary(storage, console=console)

        assert len(result) == 7

    def test_summaries_in_chronological_order(self, storage):
        """Test that summaries are in chronological order."""
        end_date = datetime(2025, 1, 15)
        console = Console(file=io.StringIO(), force_terminal=True)

        result = generate_weekly_summary(storage, end_date, console)

        dates = [r["date"] for r in result]
        assert dates == sorted(dates)

    def test_displays_weekly_table(self, storage):
        """Test that weekly table is displayed."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        generate_weekly_summary(storage, console=console)

        output_text = output.getvalue()
        assert "Weekly Overview" in output_text

    def test_displays_insights_when_data_available(self, storage):
        """Test that insights are shown when there's data."""
        # Add enough data to trigger insights display
        base = datetime(2025, 1, 15, 10, 0, 0)
        for i in range(5):
            day = base - timedelta(days=i)
            storage.save_presence_state(
                Source.SLACK, "active", day.replace(hour=9, minute=0)
            )
            storage.save_presence_state(
                Source.SLACK, "huddle", day.replace(hour=10, minute=0)
            )
            storage.save_presence_state(
                Source.SLACK, "active", day.replace(hour=11, minute=0)
            )

        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        generate_weekly_summary(storage, base, console)

        output_text = output.getvalue()
        # Insights should mention percentages when total > 0
        assert "%" in output_text

    def test_calculates_week_totals(self, storage):
        """Test that week totals are accumulated correctly."""
        # Add data for multiple days
        now = datetime.now()
        for i in range(3):
            day = now - timedelta(days=i)
            storage.save_presence_state(
                source=Source.SLACK,
                state="active",
                timestamp=day.replace(hour=9, minute=0),
            )
            storage.save_presence_state(
                source=Source.SLACK,
                state="away",
                timestamp=day.replace(hour=10, minute=0),
            )

        output = io.StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        generate_weekly_summary(storage, now, console)

        output_text = output.getvalue()
        assert "Total" in output_text


class TestExportSummaryCsv:
    """Tests for export_summary_csv function."""

    def test_exports_csv_header(self, storage):
        """Test that CSV has correct header."""
        output = io.StringIO()
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 1)

        export_summary_csv(storage, start, end, output)

        output.seek(0)
        header = output.readline().strip()
        assert header == "Date,State,Minutes,Source"

    def test_exports_presence_data(self, storage):
        """Test that presence data is exported."""
        date = datetime(2025, 1, 15, 10, 0, 0)
        storage.save_presence_state(Source.SLACK, "active", date)
        storage.save_presence_state(
            Source.SLACK, "away", date + timedelta(minutes=60)
        )

        output = io.StringIO()
        export_summary_csv(storage, date, date, output)

        output.seek(0)
        content = output.read()
        assert "2025-01-15" in content
        assert "presence" in content

    def test_exports_event_data(self, populated_storage):
        """Test that event data is exported."""
        date = datetime.now()
        output = io.StringIO()

        export_summary_csv(populated_storage, date, date, output)

        output.seek(0)
        content = output.read()
        # The populated_storage has a huddle event
        assert "huddle" in content.lower() or "slack" in content.lower()

    def test_exports_date_range(self, storage):
        """Test exporting multiple days."""
        start = datetime(2025, 1, 10)
        end = datetime(2025, 1, 12)

        # Add data for each day
        for i in range(3):
            day = start + timedelta(days=i)
            storage.save_presence_state(
                Source.SLACK,
                "active",
                day.replace(hour=9, minute=0),
            )

        output = io.StringIO()
        export_summary_csv(storage, start, end, output)

        output.seek(0)
        content = output.read()
        assert "2025-01-10" in content
        assert "2025-01-11" in content
        assert "2025-01-12" in content

    def test_handles_empty_days(self, storage):
        """Test that empty days don't cause errors."""
        start = datetime(2020, 1, 1)
        end = datetime(2020, 1, 3)
        output = io.StringIO()

        # Should not raise
        export_summary_csv(storage, start, end, output)

        output.seek(0)
        lines = output.readlines()
        # Should have at least the header
        assert len(lines) >= 1


class TestSummaryIntegration:
    """Integration tests for summary generation."""

    def test_full_day_workflow(self, storage):
        """Test a full day of state transitions."""
        base_date = datetime(2025, 1, 15, 8, 0, 0)

        # Simulate a workday
        transitions = [
            ("active", 0),      # 8:00 - Start work
            ("huddle", 60),     # 9:00 - Morning standup
            ("active", 75),     # 9:15 - Back to work
            ("away", 180),      # 11:00 - Lunch
            ("active", 240),    # 12:00 - Back from lunch
            ("dnd", 300),       # 13:00 - Focus time
            ("active", 360),    # 14:00 - Available again
            ("huddle", 420),    # 15:00 - Afternoon meeting
            ("active", 480),    # 16:00 - Wrap up
            ("away", 540),      # 17:00 - End of day
        ]

        for state, minutes_offset in transitions:
            timestamp = base_date + timedelta(minutes=minutes_offset)
            storage.save_presence_state(Source.SLACK, state, timestamp)

        # Generate summary
        console = Console(file=io.StringIO(), force_terminal=True)
        result = generate_daily_summary(storage, base_date, console)

        # Verify totals make sense
        assert result["total_tracked_minutes"] > 0
        assert "active" in result["presence"]
        assert "huddle" in result["presence"]
        assert "away" in result["presence"]
        assert "dnd" in result["presence"]

    def test_weekly_with_varying_data(self, storage):
        """Test weekly summary with varying daily data."""
        end_date = datetime(2025, 1, 17)

        # Add varying amounts of data for each day
        for i in range(7):
            day = end_date - timedelta(days=i)
            # Weekdays have more activity
            if day.weekday() < 5:  # Monday-Friday
                storage.save_presence_state(
                    Source.SLACK, "active", day.replace(hour=9)
                )
                storage.save_presence_state(
                    Source.SLACK, "huddle", day.replace(hour=10)
                )
                storage.save_presence_state(
                    Source.SLACK, "active", day.replace(hour=11)
                )
            else:  # Weekend
                storage.save_presence_state(
                    Source.SLACK, "away", day.replace(hour=10)
                )

        console = Console(file=io.StringIO(), force_terminal=True)
        result = generate_weekly_summary(storage, end_date, console)

        # All 7 days should be included
        assert len(result) == 7
