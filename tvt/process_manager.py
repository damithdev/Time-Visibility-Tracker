"""Process management for Time Visibility Tracker daemon."""

import os
import subprocess
from pathlib import Path


def get_pid_file_path() -> Path:
    """Get the path to the daemon PID file.

    Returns:
        Path to the PID file at ~/.tvt/daemon.pid
    """
    return Path.home() / ".tvt" / "daemon.pid"


def write_pid_file(pid: int) -> None:
    """Write the current process ID to the PID file.

    Args:
        pid: The process ID to write.
    """
    pid_file = get_pid_file_path()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pid_file, "w") as f:
        f.write(str(pid))


def read_pid_file() -> int | None:
    """Read the daemon PID from the PID file.

    Returns:
        The PID if the file exists and is readable, None otherwise.
    """
    pid_file = get_pid_file_path()
    if not pid_file.exists():
        return None

    try:
        with open(pid_file, "r") as f:
            pid_str = f.read().strip()
            return int(pid_str) if pid_str else None
    except (ValueError, IOError):
        return None


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running.

    Uses Windows tasklist command to check if process exists.

    Args:
        pid: The process ID to check.

    Returns:
        True if the process is running, False otherwise.
    """
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # If tasklist found the process, output will contain the PID line
        return str(pid) in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def get_daemon_pid() -> int | None:
    """Get the PID of the running daemon if it exists.

    Returns:
        The daemon PID if it's running, None otherwise.
    """
    pid = read_pid_file()
    if pid and is_process_running(pid):
        return pid
    return None


def clear_pid_file() -> None:
    """Remove the PID file."""
    pid_file = get_pid_file_path()
    if pid_file.exists():
        try:
            pid_file.unlink()
        except OSError:
            pass


def cleanup_stale_pid_file() -> None:
    """Remove the PID file if the process is not running.

    Useful to clean up after a crash or forced termination.
    """
    pid = read_pid_file()
    if pid and not is_process_running(pid):
        clear_pid_file()
