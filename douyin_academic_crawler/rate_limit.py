"""Configurable request pacing for compliant comment collection."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class SleepInterval:
    """A random sleep range used between platform requests."""

    minimum_seconds: float = 1.0
    maximum_seconds: float = 2.0

    def sample(self) -> float:
        """Return a random duration inside the configured range."""

        if self.maximum_seconds < self.minimum_seconds:
            raise ValueError("maximum_seconds must be greater than or equal to minimum_seconds")
        return random.uniform(self.minimum_seconds, self.maximum_seconds)


class RateLimiter:
    """Sleep between requests using a configurable random interval."""

    def __init__(self, interval: SleepInterval | None = None) -> None:
        """Create a rate limiter with the default 1-2 second interval."""

        self.interval = interval or SleepInterval()

    def wait(self) -> None:
        """Pause before a request."""

        duration = self.interval.sample()
        if duration > 0:
            time.sleep(duration)
