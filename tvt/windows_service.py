"""Windows Task Scheduler integration for Time Visibility Tracker."""

import subprocess
import sys
from pathlib import Path


def create_scheduled_task(task_name: str = "TimeVisibilityTracker") -> bool:
    """Create a Windows Task Scheduler task to run at user login.

    Args:
        task_name: The name of the task to create.

    Returns:
        True if the task was created successfully, False otherwise.
    """
    # Get the path to the Python executable
    python_exe = sys.executable

    # Create the command to run: python -m tvt collect --daemon
    command = f'"{python_exe}" -m tvt collect --daemon'

    try:
        subprocess.run(
            [
                "schtasks",
                "/Create",
                "/TN",
                task_name,
                "/TR",
                command,
                "/SC",
                "ONLOGON",
                "/RL",
                "HIGHEST",
                "/F",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def delete_scheduled_task(task_name: str = "TimeVisibilityTracker") -> bool:
    """Delete a Windows Task Scheduler task.

    Args:
        task_name: The name of the task to delete.

    Returns:
        True if the task was deleted successfully, False otherwise.
    """
    try:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", task_name, "/F"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def is_task_scheduled(task_name: str = "TimeVisibilityTracker") -> bool:
    """Check if a Task Scheduler task exists.

    Args:
        task_name: The name of the task to check.

    Returns:
        True if the task exists, False otherwise.
    """
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", task_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # If task exists, return code is 0 and output contains task name
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def get_task_status(task_name: str = "TimeVisibilityTracker") -> dict | None:
    """Get detailed information about a scheduled task.

    Args:
        task_name: The name of the task to query.

    Returns:
        A dictionary with task information if found, None otherwise.
    """
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", task_name, "/V", "/FO", "CSV"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout:
            # Parse CSV output - first row is headers, second is data
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                return {"exists": True, "raw_output": result.stdout}
            return None
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
