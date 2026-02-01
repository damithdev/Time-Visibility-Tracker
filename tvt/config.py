"""Configuration management for Time Visibility Tracker."""

import copy
import os
from pathlib import Path

import yaml


DEFAULT_CONFIG = {
    "database": {
        "path": "~/.tvt/data.db",
    },
    "collectors": {
        "slack": {
            "enabled": False,
            "interval_seconds": 30,
        },
        "teams": {
            "enabled": False,
            "interval_seconds": 30,
        },
    },
    "autostart": {
        "enabled": False,
        "last_enabled_at": None,
        "last_disabled_at": None,
    },
}


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    return Path.home() / ".tvt" / "config.yaml"


def get_credentials_path() -> Path:
    """Get the path to the credentials file."""
    return Path.home() / ".tvt" / "credentials.yaml"


def load_config() -> dict:
    """Load configuration from file, with defaults.

    Returns:
        Configuration dictionary.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)
    config_path = get_config_path()

    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
            # Deep merge user config into defaults
            for key, value in user_config.items():
                if isinstance(value, dict) and key in config:
                    config[key].update(value)
                else:
                    config[key] = value

    return config


def save_config(config: dict) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save.
    """
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def load_credentials() -> dict:
    """Load credentials from file.

    Returns:
        Credentials dictionary.
    """
    creds_path = get_credentials_path()

    if creds_path.exists():
        with open(creds_path) as f:
            return yaml.safe_load(f) or {}

    return {}


def save_credentials(credentials: dict) -> None:
    """Save credentials to file with restricted permissions.

    Args:
        credentials: Credentials dictionary to save.
    """
    creds_path = get_credentials_path()
    creds_path.parent.mkdir(parents=True, exist_ok=True)

    with open(creds_path, "w") as f:
        yaml.dump(credentials, f, default_flow_style=False)

    # Restrict permissions to owner only
    os.chmod(creds_path, 0o600)


def get_slack_token() -> str | None:
    """Get Slack token from credentials or environment.

    Returns:
        Slack token if available, None otherwise.
    """
    # Environment variable takes precedence
    env_token = os.environ.get("SLACK_USER_TOKEN")
    if env_token:
        return env_token

    # Fall back to credentials file
    creds = load_credentials()
    return creds.get("slack", {}).get("user_token")


def get_db_path() -> Path:
    """Get the database path from configuration.

    Returns:
        Path to the SQLite database file.
    """
    config = load_config()
    db_path = config.get("database", {}).get("path", "~/.tvt/data.db")
    return Path(db_path).expanduser()
