from dataclasses import dataclass
from datetime import datetime


@dataclass
class ApiKey:
    """Stores an API key as a SHA-256 hash.

    ``id``      SHA-256 hex digest of the raw key (stable identifier).
    ``prefix``  Last 4 characters of the raw key (for display only).
    """
    id: str
    prefix: str
    user_id: str
    name: str
    created_at: str

    def to_dict(self) -> dict:
        """Serialise for API responses (listing).

        The raw key is never included; only a masked prefix is shown.
        """
        return {
            'id': self.id,
            'key': f'***{self.prefix}',
            'name': self.name,
            'created_at': self.created_at,
        }
