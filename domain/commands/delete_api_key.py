"""DeleteApiKey command — revoke an existing API key."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeleteApiKey:
    """Command to delete an API key by its hash identifier."""

    user_id: str
    key_id: str
