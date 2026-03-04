"""GetStats query — retrieve current sensor readings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GetStats:
    """Query to retrieve the current sensor statistics."""
