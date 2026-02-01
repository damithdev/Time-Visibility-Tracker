"""Collectors module for Time Visibility Tracker."""

from tvt.collectors.base import BaseCollector
from tvt.collectors.slack import SlackCollector

__all__ = ["BaseCollector", "SlackCollector"]
