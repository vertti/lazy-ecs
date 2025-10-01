"""Data models for container operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class Action(Enum):
    """Actions for log tailing interaction."""

    STOP = "s"
    FILTER = "f"
    CLEAR = "c"

    @classmethod
    def from_key(cls, key: str) -> Action | None:
        """Convert keyboard key to action."""
        for action in cls:
            if action.value == key:
                return action
        return None


@dataclass
class LogEvent:
    """Represents a log event from CloudWatch."""

    timestamp: int | None
    message: str
    event_id: str | None = None

    @property
    def key(self) -> tuple[Any, ...] | str:
        """Get unique key for deduplication."""
        return self.event_id if self.event_id else (self.timestamp, self.message)

    def format(self) -> str:
        """Format the log event for display."""
        if self.timestamp:
            dt = datetime.fromtimestamp(self.timestamp / 1000)
            return f"[{dt.strftime('%H:%M:%S')}] {self.message}"
        return self.message
