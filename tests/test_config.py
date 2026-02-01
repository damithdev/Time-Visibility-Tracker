"""Tests for configuration module."""

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from tvt import config


class TestConfigPaths:
    """Tests for configuration path functions."""

    def test_get_config_path(self):
        """Test default config path is in home directory."""
        path = config.get_config_path()
        assert path == Path.home() / ".tvt" / "config.yaml"

    def test_get_credentials_path(self):
        """Test default credentials path is in home directory."""
        path = config.get_credentials_path()
        assert path == Path.home() / ".tvt" / "credentials.yaml"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_defaults_when_no_file(self, temp_dir):
        """Test that defaults are returned when config file doesn't exist."""
        with patch.object(config, "get_config_path", return_value=temp_dir / "config.yaml"):
            result = config.load_config()

        assert result == config.DEFAULT_CONFIG
        assert result["database"]["path"] == "~/.tvt/data.db"
        assert result["collectors"]["slack"]["enabled"] is False
        assert result["collectors"]["slack"]["interval_seconds"] == 30

    def test_load_config_merges_user_config(self, temp_dir):
        """Test that user config is merged with defaults."""
        config_path = temp_dir / "config.yaml"
        user_config = {
            "collectors": {
                "slack": {
                    "enabled": True,
                    "interval_seconds": 60,
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(user_config, f)

        with patch.object(config, "get_config_path", return_value=config_path):
            result = config.load_config()

        # User values should override defaults
        assert result["collectors"]["slack"]["enabled"] is True
        assert result["collectors"]["slack"]["interval_seconds"] == 60
        # Other defaults should be preserved
        assert result["database"]["path"] == "~/.tvt/data.db"
        assert result["collectors"]["teams"]["enabled"] is False

    def test_load_config_handles_empty_file(self, temp_dir):
        """Test loading empty config file returns defaults."""
        config_path = temp_dir / "config.yaml"
        config_path.touch()

        with patch.object(config, "get_config_path", return_value=config_path):
            result = config.load_config()

        assert result == config.DEFAULT_CONFIG

    def test_load_config_custom_database_path(self, temp_dir):
        """Test loading config with custom database path."""
        config_path = temp_dir / "config.yaml"
        user_config = {
            "database": {
                "path": "/custom/path/data.db"
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(user_config, f)

        with patch.object(config, "get_config_path", return_value=config_path):
            result = config.load_config()

        assert result["database"]["path"] == "/custom/path/data.db"


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_file(self, temp_dir):
        """Test that save_config creates the config file."""
        config_path = temp_dir / ".tvt" / "config.yaml"

        with patch.object(config, "get_config_path", return_value=config_path):
            config.save_config({"database": {"path": "/test/db.db"}})

        assert config_path.exists()
        with open(config_path) as f:
            saved = yaml.safe_load(f)
        assert saved["database"]["path"] == "/test/db.db"

    def test_save_config_creates_parent_dirs(self, temp_dir):
        """Test that save_config creates parent directories."""
        config_path = temp_dir / "deep" / "nested" / "config.yaml"

        with patch.object(config, "get_config_path", return_value=config_path):
            config.save_config({"test": "value"})

        assert config_path.exists()

    def test_save_config_overwrites_existing(self, temp_dir):
        """Test that save_config overwrites existing config."""
        config_path = temp_dir / "config.yaml"

        # Create initial config
        with open(config_path, "w") as f:
            yaml.dump({"old": "value"}, f)

        with patch.object(config, "get_config_path", return_value=config_path):
            config.save_config({"new": "value"})

        with open(config_path) as f:
            saved = yaml.safe_load(f)
        assert "old" not in saved
        assert saved["new"] == "value"


class TestLoadCredentials:
    """Tests for load_credentials function."""

    def test_load_credentials_when_no_file(self, temp_dir):
        """Test that empty dict is returned when no credentials file."""
        with patch.object(config, "get_credentials_path", return_value=temp_dir / "creds.yaml"):
            result = config.load_credentials()

        assert result == {}

    def test_load_credentials_from_file(self, temp_dir):
        """Test loading credentials from file."""
        creds_path = temp_dir / "credentials.yaml"
        credentials = {
            "slack": {"user_token": "xoxp-test-token"},
            "teams": {"client_id": "test-client-id"},
        }
        with open(creds_path, "w") as f:
            yaml.dump(credentials, f)

        with patch.object(config, "get_credentials_path", return_value=creds_path):
            result = config.load_credentials()

        assert result == credentials

    def test_load_credentials_handles_empty_file(self, temp_dir):
        """Test loading empty credentials file returns empty dict."""
        creds_path = temp_dir / "credentials.yaml"
        creds_path.touch()

        with patch.object(config, "get_credentials_path", return_value=creds_path):
            result = config.load_credentials()

        assert result == {}


class TestSaveCredentials:
    """Tests for save_credentials function."""

    def test_save_credentials_creates_file(self, temp_dir):
        """Test that save_credentials creates the credentials file."""
        creds_path = temp_dir / ".tvt" / "credentials.yaml"

        with patch.object(config, "get_credentials_path", return_value=creds_path):
            config.save_credentials({"slack": {"user_token": "xoxp-test"}})

        assert creds_path.exists()
        with open(creds_path) as f:
            saved = yaml.safe_load(f)
        assert saved["slack"]["user_token"] == "xoxp-test"

    def test_save_credentials_restricts_permissions(self, temp_dir):
        """Test that credentials file has restricted permissions (600)."""
        creds_path = temp_dir / "credentials.yaml"

        with patch.object(config, "get_credentials_path", return_value=creds_path):
            config.save_credentials({"test": "secret"})

        file_stat = os.stat(creds_path)
        permissions = stat.S_IMODE(file_stat.st_mode)
        assert permissions == 0o600


class TestGetSlackToken:
    """Tests for get_slack_token function."""

    def test_get_slack_token_from_env(self, temp_dir):
        """Test that environment variable takes precedence."""
        creds_path = temp_dir / "credentials.yaml"
        with open(creds_path, "w") as f:
            yaml.dump({"slack": {"user_token": "xoxp-from-file"}}, f)

        with patch.object(config, "get_credentials_path", return_value=creds_path):
            with patch.dict(os.environ, {"SLACK_USER_TOKEN": "xoxp-from-env"}):
                result = config.get_slack_token()

        assert result == "xoxp-from-env"

    def test_get_slack_token_from_file(self, temp_dir):
        """Test getting token from credentials file."""
        creds_path = temp_dir / "credentials.yaml"
        with open(creds_path, "w") as f:
            yaml.dump({"slack": {"user_token": "xoxp-from-file"}}, f)

        with patch.object(config, "get_credentials_path", return_value=creds_path):
            with patch.dict(os.environ, {}, clear=True):
                # Remove SLACK_USER_TOKEN if it exists
                os.environ.pop("SLACK_USER_TOKEN", None)
                result = config.get_slack_token()

        assert result == "xoxp-from-file"

    def test_get_slack_token_returns_none_when_not_configured(self, temp_dir):
        """Test that None is returned when token not configured."""
        with patch.object(config, "get_credentials_path", return_value=temp_dir / "creds.yaml"):
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("SLACK_USER_TOKEN", None)
                result = config.get_slack_token()

        assert result is None


class TestGetDbPath:
    """Tests for get_db_path function."""

    def test_get_db_path_default(self, temp_dir):
        """Test default database path."""
        with patch.object(config, "get_config_path", return_value=temp_dir / "config.yaml"):
            result = config.get_db_path()

        assert result == Path.home() / ".tvt" / "data.db"

    def test_get_db_path_custom(self, temp_dir):
        """Test custom database path from config."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"database": {"path": "/custom/path/data.db"}}, f)

        with patch.object(config, "get_config_path", return_value=config_path):
            result = config.get_db_path()

        assert result == Path("/custom/path/data.db")

    def test_get_db_path_expands_tilde(self, temp_dir):
        """Test that tilde is expanded in database path."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"database": {"path": "~/custom/data.db"}}, f)

        with patch.object(config, "get_config_path", return_value=config_path):
            result = config.get_db_path()

        assert result == Path.home() / "custom" / "data.db"
