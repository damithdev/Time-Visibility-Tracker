"""Base collector interface for Time Visibility Tracker."""

from abc import ABC, abstractmethod
from datetime import datetime

from tvt.storage.models import Source
from tvt.storage.sqlite import SQLiteStorage


class BaseCollector(ABC):
    """Abstract base class for data collectors."""

    source: Source

    def __init__(self, storage: SQLiteStorage):
        """Initialize collector with storage backend.

        Args:
            storage: SQLiteStorage instance for persisting data.
        """
        self.storage = storage
        self._running = False
        self._last_state: str | None = None
        self._last_state_time: datetime | None = None

    @abstractmethod
    def collect(self) -> dict | None:
        """Collect current state from the source.

        Returns:
            Dictionary with current state data, or None if collection failed.
        """
        pass

    @abstractmethod
    def process_state_change(
        self, old_state: str | None, new_state: str, timestamp: datetime
    ) -> None:
        """Process a state transition.

        Args:
            old_state: Previous state (None if first collection).
            new_state: Current state.
            timestamp: Time of the state change.
        """
        pass

    def run_once(self) -> dict | None:
        """Run a single collection cycle.

        Returns:
            Current state data if successful, None otherwise.
        """
        data = self.collect()
        if data is None:
            return None

        current_state = data.get("state")
        current_time = datetime.now()

        # Save presence state
        self.storage.save_presence_state(
            source=self.source,
            state=current_state,
            timestamp=current_time,
            raw_data=data,
        )

        # Check for state change
        if self._last_state != current_state:
            self.process_state_change(self._last_state, current_state, current_time)
            self._last_state = current_state
            self._last_state_time = current_time

        return data

    def start(self, interval_seconds: int = 30) -> None:
        """Start continuous collection.

        Args:
            interval_seconds: Time between collection cycles.
        """
        import signal
        import time

        self._running = True

        def handle_signal(signum, frame):
            self._running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        while self._running:
            try:
                self.run_once()
            except Exception as e:
                # Log error but continue running
                print(f"Collection error: {e}")

            # Sleep in small increments to allow for quick shutdown
            for _ in range(interval_seconds):
                if not self._running:
                    break
                time.sleep(1)

    def stop(self) -> None:
        """Stop continuous collection."""
        self._running = False
