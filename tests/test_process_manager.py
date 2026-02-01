"""Tests for process manager module."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tvt.process_manager import (
    cleanup_stale_pid_file,
    clear_pid_file,
    get_daemon_pid,
    get_pid_file_path,
    is_process_running,
    read_pid_file,
    write_pid_file,
)


@pytest.fixture
def mock_home_dir(tmp_path, monkeypatch):
    """Mock the home directory for tests."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def test_get_pid_file_path(mock_home_dir):
    """Test that PID file path is correctly constructed."""
    pid_file = get_pid_file_path()
    assert pid_file == mock_home_dir / ".tvt" / "daemon.pid"


def test_write_and_read_pid_file(mock_home_dir):
    """Test writing and reading PID file."""
    test_pid = 12345

    # Write PID
    write_pid_file(test_pid)
    pid_file = get_pid_file_path()
    assert pid_file.exists()

    # Read PID
    read_pid = read_pid_file()
    assert read_pid == test_pid


def test_read_pid_file_nonexistent(mock_home_dir):
    """Test reading PID file that doesn't exist."""
    read_pid = read_pid_file()
    assert read_pid is None


def test_read_pid_file_invalid_content(mock_home_dir):
    """Test reading PID file with invalid content."""
    pid_file = get_pid_file_path()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text("not_a_number")

    read_pid = read_pid_file()
    assert read_pid is None


def test_read_pid_file_empty(mock_home_dir):
    """Test reading empty PID file."""
    pid_file = get_pid_file_path()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text("")

    read_pid = read_pid_file()
    assert read_pid is None


def test_clear_pid_file(mock_home_dir):
    """Test clearing PID file."""
    write_pid_file(12345)
    pid_file = get_pid_file_path()
    assert pid_file.exists()

    clear_pid_file()
    assert not pid_file.exists()


def test_clear_pid_file_nonexistent(mock_home_dir):
    """Test clearing non-existent PID file doesn't raise error."""
    # Should not raise any exceptions
    clear_pid_file()


@patch("tvt.process_manager.subprocess.run")
def test_is_process_running_true(mock_run, mock_home_dir):
    """Test is_process_running returns True when process exists."""
    test_pid = 12345
    mock_run.return_value = MagicMock(stdout=f"python.exe    {test_pid}")

    result = is_process_running(test_pid)
    assert result is True
    mock_run.assert_called_once()


@patch("tvt.process_manager.subprocess.run")
def test_is_process_running_false(mock_run, mock_home_dir):
    """Test is_process_running returns False when process doesn't exist."""
    test_pid = 12345
    mock_run.return_value = MagicMock(stdout="INFO: No tasks are running")

    result = is_process_running(test_pid)
    assert result is False


@patch("tvt.process_manager.subprocess.run")
def test_is_process_running_timeout(mock_run, mock_home_dir):
    """Test is_process_running handles timeout gracefully."""
    import subprocess

    mock_run.side_effect = subprocess.TimeoutExpired("tasklist", 5)

    result = is_process_running(12345)
    assert result is False


@patch("tvt.process_manager.subprocess.run")
def test_is_process_running_not_found(mock_run, mock_home_dir):
    """Test is_process_running handles FileNotFoundError gracefully."""
    mock_run.side_effect = FileNotFoundError()

    result = is_process_running(12345)
    assert result is False


@patch("tvt.process_manager.is_process_running")
def test_get_daemon_pid_running(mock_is_running, mock_home_dir):
    """Test get_daemon_pid when daemon is running."""
    test_pid = 12345
    write_pid_file(test_pid)
    mock_is_running.return_value = True

    result = get_daemon_pid()
    assert result == test_pid


@patch("tvt.process_manager.is_process_running")
def test_get_daemon_pid_not_running(mock_is_running, mock_home_dir):
    """Test get_daemon_pid when daemon is not running."""
    test_pid = 12345
    write_pid_file(test_pid)
    mock_is_running.return_value = False

    result = get_daemon_pid()
    assert result is None


def test_get_daemon_pid_no_pid_file(mock_home_dir):
    """Test get_daemon_pid when no PID file exists."""
    result = get_daemon_pid()
    assert result is None


@patch("tvt.process_manager.is_process_running")
def test_cleanup_stale_pid_file(mock_is_running, mock_home_dir):
    """Test cleanup_stale_pid_file removes file for dead process."""
    test_pid = 12345
    write_pid_file(test_pid)
    pid_file = get_pid_file_path()
    assert pid_file.exists()

    # Process is not running
    mock_is_running.return_value = False

    cleanup_stale_pid_file()
    assert not pid_file.exists()


@patch("tvt.process_manager.is_process_running")
def test_cleanup_stale_pid_file_running_process(mock_is_running, mock_home_dir):
    """Test cleanup_stale_pid_file keeps file for running process."""
    test_pid = 12345
    write_pid_file(test_pid)
    pid_file = get_pid_file_path()

    # Process is still running
    mock_is_running.return_value = True

    cleanup_stale_pid_file()
    assert pid_file.exists()
