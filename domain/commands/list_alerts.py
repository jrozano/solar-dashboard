"""ListAlerts query — retrieve all CEP alerts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ListAlerts:
    """Query to retrieve the list of active CEP alerts."""
