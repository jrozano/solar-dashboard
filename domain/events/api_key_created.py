"""ApiKeyCreated domain event."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyCreated:
    """A user created a new API key."""

    user_id: str
    name: str
