"""ListKeys query — retrieve API keys for a user."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ListKeys:
    """Query to list all API keys belonging to a user."""

    user_id: str
