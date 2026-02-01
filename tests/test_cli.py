"""Tests for CLI module."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from tvt import __version__
from tvt.cli import main
from tvt.storage.models import Source


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def isolated_config(temp_dir):
    """Set up isolated configuration directory."""
    config_dir = temp_dir / ".tvt"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.yaml"
    creds_path = config_dir / "credentials.yaml"
    db_path = config_dir / "data.db"

    return {
        "config_dir": config_dir,
        "config_path": config_path,
        "creds_path": creds_path,
        "db_path": db_path,
    }


class TestMainGroup:
    """Tests for main CLI group."""

    def test_help_option(self, cli_runner):
        """Test --help displays help text."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Time Visibility Tracker" in result.output
        assert "invisible work time visible" in result.output

    def test_version_option(self, cli_runner):
        """Test --version displays version."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output

    def test_available_commands(self, cli_runner):
        """Test that all expected commands are available."""
        result = cli_runner.invoke(main, ["--help"])

        expected_commands = ["init", "collect", "summary", "export", "status", "dashboard"]
        for cmd in expected_commands:
            assert cmd in result.output


class TestSummaryCommand:
    """Tests for summary command."""

    def test_summary_help(self, cli_runner):
        """Test summary --help."""
        result = cli_runner.invoke(main, ["summary", "--help"])

        assert result.exit_code == 0
        assert "Display time visibility summary" in result.output

    def test_summary_daily_default(self, cli_runner, temp_dir, isolated_config):
        """Test daily summary with default date."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["summary"])

        assert result.exit_code == 0

    def test_summary_with_specific_date(self, cli_runner, isolated_config):
        """Test summary for specific date."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["summary", "--date", "2025-01-15"])

        assert result.exit_code == 0

    def test_summary_invalid_date_format(self, cli_runner, isolated_config):
        """Test summary with invalid date format."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["summary", "--date", "invalid"])

        assert result.exit_code == 1
        assert "Invalid date format" in result.output

    def test_summary_weekly(self, cli_runner, isolated_config):
        """Test weekly summary."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["summary", "--weekly"])

        assert result.exit_code == 0


class TestExportCommand:
    """Tests for export command."""

    def test_export_help(self, cli_runner):
        """Test export --help."""
        result = cli_runner.invoke(main, ["export", "--help"])

        assert result.exit_code == 0
        assert "Export time data to CSV" in result.output

    def test_export_requires_start_date(self, cli_runner):
        """Test that --start is required."""
        result = cli_runner.invoke(main, ["export"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_export_to_stdout(self, cli_runner, isolated_config):
        """Test export to stdout."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["export", "--start", "2025-01-01"])

        assert result.exit_code == 0
        assert "Date,State,Minutes,Source" in result.output

    def test_export_to_file(self, cli_runner, temp_dir, isolated_config):
        """Test export to file."""
        output_file = temp_dir / "export.csv"

        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(
                main,
                ["export", "--start", "2025-01-01", "--output", str(output_file)],
            )

        assert result.exit_code == 0
        assert "exported" in result.output.lower()
        assert output_file.exists()

    def test_export_with_date_range(self, cli_runner, isolated_config):
        """Test export with start and end dates."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(
                main,
                ["export", "--start", "2025-01-01", "--end", "2025-01-07"],
            )

        assert result.exit_code == 0

    def test_export_invalid_start_date(self, cli_runner, isolated_config):
        """Test export with invalid start date."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["export", "--start", "invalid"])

        assert result.exit_code == 1
        assert "Invalid start date" in result.output

    def test_export_invalid_end_date(self, cli_runner, isolated_config):
        """Test export with invalid end date."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(
                main,
                ["export", "--start", "2025-01-01", "--end", "invalid"],
            )

        assert result.exit_code == 1
        assert "Invalid end date" in result.output

    def test_export_end_before_start(self, cli_runner, isolated_config):
        """Test export fails when end date is before start date."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(
                main,
                ["export", "--start", "2025-01-15", "--end", "2025-01-01"],
            )

        assert result.exit_code == 1
        assert "cannot be before start date" in result.output.lower()


class TestStatusCommand:
    """Tests for status command."""

    def test_status_help(self, cli_runner):
        """Test status --help."""
        result = cli_runner.invoke(main, ["status", "--help"])

        assert result.exit_code == 0

    def test_status_shows_database_info(self, cli_runner, temp_dir, isolated_config):
        """Test status shows database information."""
        # Create a database file
        isolated_config["db_path"].touch()

        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            with patch("tvt.cli.get_config_path", return_value=isolated_config["config_path"]):
                with patch("tvt.cli.load_config", return_value={"collectors": {}}):
                    with patch("tvt.cli.get_slack_token", return_value=None):
                        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "Database" in result.output

    def test_status_shows_collector_status(self, cli_runner, isolated_config):
        """Test status shows collector configuration."""
        config = {
            "collectors": {
                "slack": {"enabled": True},
                "teams": {"enabled": False},
            }
        }

        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            with patch("tvt.cli.get_config_path", return_value=isolated_config["config_path"]):
                with patch("tvt.cli.load_config", return_value=config):
                    with patch("tvt.cli.get_slack_token", return_value=None):
                        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "slack" in result.output.lower()
        assert "teams" in result.output.lower()

    def test_status_shows_credentials_status(self, cli_runner, isolated_config):
        """Test status shows credentials status."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            with patch("tvt.cli.get_config_path", return_value=isolated_config["config_path"]):
                with patch("tvt.cli.load_config", return_value={"collectors": {}}):
                    # Test with credentials configured
                    with patch("tvt.cli.get_slack_token", return_value="xoxp-test"):
                        result = cli_runner.invoke(main, ["status"])

        assert result.exit_code == 0
        assert "credentials" in result.output.lower()


class TestCollectCommand:
    """Tests for collect command."""

    def test_collect_help(self, cli_runner):
        """Test collect --help."""
        result = cli_runner.invoke(main, ["collect", "--help"])

        assert result.exit_code == 0
        assert "collecting" in result.output.lower()

    def test_collect_no_token_configured(self, cli_runner, isolated_config):
        """Test collect fails when no token is configured."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            with patch("tvt.cli.get_slack_token", return_value=None):
                result = cli_runner.invoke(main, ["collect"])

        assert result.exit_code == 1
        assert "token not configured" in result.output.lower()

    def test_collect_unknown_source(self, cli_runner, isolated_config):
        """Test collect with unknown source."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["collect", "--source", "unknown"])

        assert result.exit_code == 1
        assert "Unknown source" in result.output

    def test_collect_single_run(self, cli_runner, isolated_config):
        """Test single collection run."""
        mock_collector = MagicMock()
        mock_collector.run_once.return_value = {"state": "active", "in_huddle": False}

        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            with patch("tvt.cli.get_slack_token", return_value="xoxp-test"):
                with patch("tvt.collectors.slack.SlackCollector", return_value=mock_collector):
                    result = cli_runner.invoke(main, ["collect"])

        assert result.exit_code == 0
        assert "active" in result.output.lower()
        mock_collector.run_once.assert_called_once()

    def test_collect_shows_huddle_status(self, cli_runner, isolated_config):
        """Test that huddle status is shown."""
        mock_collector = MagicMock()
        mock_collector.run_once.return_value = {"state": "huddle", "in_huddle": True}

        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            with patch("tvt.cli.get_slack_token", return_value="xoxp-test"):
                with patch("tvt.collectors.slack.SlackCollector", return_value=mock_collector):
                    result = cli_runner.invoke(main, ["collect"])

        assert result.exit_code == 0
        assert "huddle" in result.output.lower()

    def test_collect_no_data(self, cli_runner, isolated_config):
        """Test collect when no data is returned."""
        mock_collector = MagicMock()
        mock_collector.run_once.return_value = None

        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            with patch("tvt.cli.get_slack_token", return_value="xoxp-test"):
                with patch("tvt.collectors.slack.SlackCollector", return_value=mock_collector):
                    result = cli_runner.invoke(main, ["collect"])

        assert result.exit_code == 0
        assert "No data collected" in result.output

    def test_collect_interval_too_small(self, cli_runner, isolated_config):
        """Test collect fails with interval less than 10 seconds."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["collect", "--interval", "5"])

        assert result.exit_code == 1
        assert "at least 10 seconds" in result.output.lower()

    def test_collect_interval_too_large(self, cli_runner, isolated_config):
        """Test collect fails with interval greater than 3600 seconds."""
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            result = cli_runner.invoke(main, ["collect", "--interval", "7200"])

        assert result.exit_code == 1
        assert "cannot exceed 3600" in result.output.lower()

    def test_collect_interval_valid_bounds(self, cli_runner, isolated_config):
        """Test collect accepts valid interval values."""
        mock_collector = MagicMock()
        mock_collector.run_once.return_value = {"state": "active", "in_huddle": False}

        # Test minimum valid interval
        with patch("tvt.cli.get_db_path", return_value=isolated_config["db_path"]):
            with patch("tvt.cli.get_slack_token", return_value="xoxp-test"):
                with patch("tvt.collectors.slack.SlackCollector", return_value=mock_collector):
                    result = cli_runner.invoke(main, ["collect", "--interval", "10"])

        assert result.exit_code == 0


class TestDashboardCommand:
    """Tests for dashboard command."""

    def test_dashboard_shows_coming_soon(self, cli_runner):
        """Test dashboard shows coming soon message."""
        result = cli_runner.invoke(main, ["dashboard"])

        assert result.exit_code == 0
        assert "Phase 1" in result.output
        assert "tvt summary" in result.output


class TestInitCommand:
    """Tests for init command."""

    def test_init_help(self, cli_runner):
        """Test init --help."""
        result = cli_runner.invoke(main, ["init", "--help"])

        assert result.exit_code == 0
        assert "Initialize" in result.output
