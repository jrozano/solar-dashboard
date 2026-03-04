"""ClearAlerts command — remove all CEP alerts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClearAlerts:
    """Command to clear all CEP alerts."""

    user_id: str
