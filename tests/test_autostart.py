"""Tests for autostart CLI commands."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tvt.cli import autostart, main


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_home_dir(tmp_path, monkeypatch):
    """Mock the home directory for tests."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@patch("tvt.cli.platform.system")
def test_autostart_enable_non_windows(mock_platform, cli_runner):
    """Test enabling autostart on non-Windows platform shows error."""
    mock_platform.return_value = "Linux"

    result = cli_runner.invoke(main, ["autostart", "enable"])
    assert result.exit_code == 1
    assert "Windows" in result.output


@patch("tvt.cli.platform.system")
@patch("tvt.cli.create_scheduled_task")
def test_autostart_enable_success(mock_create_task, mock_platform, cli_runner, mock_home_dir):
    """Test successfully enabling autostart."""
    mock_platform.return_value = "Windows"
    mock_create_task.return_value = True

    result = cli_runner.invoke(main, ["autostart", "enable"])
    assert result.exit_code == 0
    assert "Autostart enabled" in result.output
    mock_create_task.assert_called_once()


@patch("tvt.cli.platform.system")
@patch("tvt.cli.create_scheduled_task")
def test_autostart_enable_failure(mock_create_task, mock_platform, cli_runner, mock_home_dir):
    """Test handling of task creation failure."""
    mock_platform.return_value = "Windows"
    mock_create_task.return_value = False

    result = cli_runner.invoke(main, ["autostart", "enable"])
    assert result.exit_code == 1
    assert "Failed" in result.output


@patch("tvt.cli.platform.system")
@patch("tvt.cli.create_scheduled_task")
@patch("tvt.cli.get_daemon_pid")
@patch("tvt.cli.subprocess.Popen")
def test_autostart_enable_with_start_now(
    mock_popen, mock_get_pid, mock_create_task, mock_platform, cli_runner, mock_home_dir
):
    """Test enabling autostart and starting daemon immediately."""
    mock_platform.return_value = "Windows"
    mock_create_task.return_value = True
    mock_get_pid.return_value = None
    mock_popen.return_value = MagicMock()

    result = cli_runner.invoke(main, ["autostart", "enable", "--start-now"])
    assert result.exit_code == 0
    assert "Autostart enabled" in result.output
    assert "Daemon started" in result.output
    mock_popen.assert_called_once()


@patch("tvt.cli.platform.system")
@patch("tvt.cli.create_scheduled_task")
@patch("tvt.cli.get_daemon_pid")
def test_autostart_enable_with_start_now_already_running(
    mock_get_pid, mock_create_task, mock_platform, cli_runner, mock_home_dir
):
    """Test enabling autostart when daemon is already running."""
    mock_platform.return_value = "Windows"
    mock_create_task.return_value = True
    mock_get_pid.return_value = 12345  # Daemon is running

    result = cli_runner.invoke(main, ["autostart", "enable", "--start-now"])
    assert result.exit_code == 0
    assert "already running" in result.output


@patch("tvt.cli.platform.system")
@patch("tvt.cli.delete_scheduled_task")
def test_autostart_disable_success(mock_delete_task, mock_platform, cli_runner, mock_home_dir):
    """Test successfully disabling autostart."""
    mock_platform.return_value = "Windows"
    mock_delete_task.return_value = True

    result = cli_runner.invoke(main, ["autostart", "disable"])
    assert result.exit_code == 0
    assert "Autostart disabled" in result.output
    mock_delete_task.assert_called_once()


@patch("tvt.cli.platform.system")
@patch("tvt.cli.delete_scheduled_task")
def test_autostart_disable_failure(mock_delete_task, mock_platform, cli_runner, mock_home_dir):
    """Test handling of task deletion failure."""
    mock_platform.return_value = "Windows"
    mock_delete_task.return_value = False

    result = cli_runner.invoke(main, ["autostart", "disable"])
    assert result.exit_code == 1
    assert "Failed" in result.output


@patch("tvt.cli.platform.system")
@patch("tvt.cli.delete_scheduled_task")
@patch("tvt.cli.get_daemon_pid")
@patch("os.kill")
def test_autostart_disable_with_stop_daemon(
    mock_kill, mock_get_pid, mock_delete_task, mock_platform, cli_runner, mock_home_dir
):
    """Test disabling autostart and stopping daemon."""
    mock_platform.return_value = "Windows"
    mock_delete_task.return_value = True
    mock_get_pid.return_value = 12345

    result = cli_runner.invoke(main, ["autostart", "disable", "--stop-daemon"])
    assert result.exit_code == 0
    assert "Autostart disabled" in result.output
    assert "Daemon stopped" in result.output
    mock_kill.assert_called_once_with(12345, 15)


@patch("tvt.cli.platform.system")
@patch("tvt.cli.delete_scheduled_task")
@patch("tvt.cli.get_daemon_pid")
def test_autostart_disable_with_stop_daemon_not_running(
    mock_get_pid, mock_delete_task, mock_platform, cli_runner, mock_home_dir
):
    """Test disabling autostart when daemon is not running."""
    mock_platform.return_value = "Windows"
    mock_delete_task.return_value = True
    mock_get_pid.return_value = None

    result = cli_runner.invoke(main, ["autostart", "disable", "--stop-daemon"])
    assert result.exit_code == 0
    assert "Daemon not running" in result.output


@patch("tvt.cli.platform.system")
@patch("tvt.cli.is_task_scheduled")
@patch("tvt.cli.get_daemon_pid")
@patch("tvt.cli.load_config")
def test_autostart_status_all_enabled(
    mock_load_config, mock_get_pid, mock_is_scheduled, mock_platform, cli_runner, mock_home_dir
):
    """Test status when everything is enabled and running."""
    mock_platform.return_value = "Windows"
    mock_is_scheduled.return_value = True
    mock_get_pid.return_value = 12345
    mock_load_config.return_value = {
        "autostart": {
            "enabled": True,
            "last_enabled_at": "2025-02-01T10:00:00",
            "last_disabled_at": None,
        }
    }

    result = cli_runner.invoke(main, ["autostart", "status"])
    assert result.exit_code == 0
    assert "Autostart Status" in result.output
    assert "enabled" in result.output
    assert "exists" in result.output
    assert "12345" in result.output
    assert "Everything is configured and running" in result.output


@patch("tvt.cli.platform.system")
@patch("tvt.cli.is_task_scheduled")
@patch("tvt.cli.get_daemon_pid")
def test_autostart_status_all_disabled(
    mock_get_pid, mock_is_scheduled, mock_platform, cli_runner, mock_home_dir
):
    """Test status when everything is disabled."""
    mock_platform.return_value = "Windows"
    mock_is_scheduled.return_value = False
    mock_get_pid.return_value = None

    result = cli_runner.invoke(main, ["autostart", "status"])
    assert result.exit_code == 0
    assert "Autostart Status" in result.output
    assert "not configured" in result.output


@patch("tvt.cli.platform.system")
@patch("tvt.cli.is_task_scheduled")
@patch("tvt.cli.get_daemon_pid")
def test_autostart_status_config_out_of_sync(
    mock_get_pid, mock_is_scheduled, mock_platform, cli_runner, mock_home_dir
):
    """Test status when config is out of sync with actual state."""
    mock_platform.return_value = "Windows"
    mock_is_scheduled.return_value = False
    mock_get_pid.return_value = None

    # First enable autostart in config
    cli_runner.invoke(main, ["autostart", "enable"])

    # Then check status when task doesn't exist
    result = cli_runner.invoke(main, ["autostart", "status"])
    assert result.exit_code == 0
    assert "Config says enabled but task not found" in result.output


@patch("tvt.cli.platform.system")
def test_autostart_status_non_windows(mock_platform, cli_runner):
    """Test status command on non-Windows platform shows error."""
    mock_platform.return_value = "Darwin"

    result = cli_runner.invoke(main, ["autostart", "status"])
    assert result.exit_code == 1
    assert "Windows" in result.output
