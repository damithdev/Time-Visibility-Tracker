"""Tests for Windows service integration."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tvt.windows_service import (
    create_scheduled_task,
    delete_scheduled_task,
    get_task_status,
    is_task_scheduled,
)


@patch("tvt.windows_service.subprocess.run")
def test_create_scheduled_task_success(mock_run):
    """Test creating a scheduled task successfully."""
    mock_run.return_value = MagicMock(returncode=0)

    result = create_scheduled_task()
    assert result is True

    # Verify schtasks was called with correct arguments
    call_args = mock_run.call_args[0][0]
    assert "schtasks" in call_args
    assert "/Create" in call_args
    assert "/TN" in call_args
    assert "TimeVisibilityTracker" in call_args


@patch("tvt.windows_service.subprocess.run")
def test_create_scheduled_task_with_custom_name(mock_run):
    """Test creating a scheduled task with custom name."""
    mock_run.return_value = MagicMock(returncode=0)

    result = create_scheduled_task("CustomTaskName")
    assert result is True

    call_args = mock_run.call_args[0][0]
    assert "CustomTaskName" in call_args


@patch("tvt.windows_service.subprocess.run")
def test_create_scheduled_task_failure(mock_run):
    """Test handling of task creation failure."""
    import subprocess

    mock_run.side_effect = subprocess.TimeoutExpired("schtasks", 10)

    result = create_scheduled_task()
    assert result is False


@patch("tvt.windows_service.subprocess.run")
def test_create_scheduled_task_command_not_found(mock_run):
    """Test handling when schtasks command is not found."""
    mock_run.side_effect = FileNotFoundError()

    result = create_scheduled_task()
    assert result is False


@patch("tvt.windows_service.subprocess.run")
def test_delete_scheduled_task_success(mock_run):
    """Test deleting a scheduled task successfully."""
    mock_run.return_value = MagicMock(returncode=0)

    result = delete_scheduled_task()
    assert result is True

    call_args = mock_run.call_args[0][0]
    assert "schtasks" in call_args
    assert "/Delete" in call_args
    assert "TimeVisibilityTracker" in call_args


@patch("tvt.windows_service.subprocess.run")
def test_delete_scheduled_task_failure(mock_run):
    """Test handling of task deletion failure."""
    import subprocess

    mock_run.side_effect = subprocess.TimeoutExpired("schtasks", 10)

    result = delete_scheduled_task()
    assert result is False


@patch("tvt.windows_service.subprocess.run")
def test_is_task_scheduled_true(mock_run):
    """Test checking if task is scheduled when it exists."""
    mock_run.return_value = MagicMock(returncode=0, stdout="TimeVisibilityTracker")

    result = is_task_scheduled()
    assert result is True

    call_args = mock_run.call_args[0][0]
    assert "schtasks" in call_args
    assert "/Query" in call_args


@patch("tvt.windows_service.subprocess.run")
def test_is_task_scheduled_false(mock_run):
    """Test checking if task is scheduled when it doesn't exist."""
    mock_run.return_value = MagicMock(returncode=1, stdout="")

    result = is_task_scheduled()
    assert result is False


@patch("tvt.windows_service.subprocess.run")
def test_is_task_scheduled_timeout(mock_run):
    """Test handling of timeout when checking task."""
    import subprocess

    mock_run.side_effect = subprocess.TimeoutExpired("schtasks", 10)

    result = is_task_scheduled()
    assert result is False


@patch("tvt.windows_service.subprocess.run")
def test_get_task_status_success(mock_run):
    """Test getting task status successfully."""
    mock_output = '"TaskName","Status"\n"TimeVisibilityTracker","Ready"'
    mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)

    result = get_task_status()
    assert result is not None
    assert result["exists"] is True


@patch("tvt.windows_service.subprocess.run")
def test_get_task_status_not_found(mock_run):
    """Test getting status when task doesn't exist."""
    mock_run.return_value = MagicMock(returncode=1, stdout="")

    result = get_task_status()
    assert result is None


@patch("tvt.windows_service.subprocess.run")
def test_get_task_status_empty_output(mock_run):
    """Test getting status with empty output."""
    mock_run.return_value = MagicMock(returncode=0, stdout="")

    result = get_task_status()
    assert result is None


@patch("tvt.windows_service.subprocess.run")
def test_get_task_status_timeout(mock_run):
    """Test handling timeout when getting status."""
    import subprocess

    mock_run.side_effect = subprocess.TimeoutExpired("schtasks", 10)

    result = get_task_status()
    assert result is None


@patch("tvt.windows_service.subprocess.run")
def test_create_task_includes_python_path(mock_run):
    """Test that created task includes correct Python executable path."""
    mock_run.return_value = MagicMock(returncode=0)

    create_scheduled_task()

    call_args = mock_run.call_args[0][0]
    # Check that sys.executable is included in the command
    command_str = " ".join(call_args)
    assert sys.executable in command_str or "python" in command_str
    assert "tvt collect --daemon" in command_str
