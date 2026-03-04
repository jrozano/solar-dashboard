"""CreateApiKey command — generate a new API key."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateApiKey:
    """Command to create a new API key for a user."""

    user_id: str
    name: str
