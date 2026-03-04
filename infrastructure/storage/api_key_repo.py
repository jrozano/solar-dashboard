"""API-key repository - in-memory store for API keys.

The raw API key is generated with :func:`secrets.token_urlsafe` and
stored as a SHA-256 hash.  Only the hash and a 4-character display
prefix are persisted; the raw key is returned exactly once at creation
time and is never stored or retrievable afterwards.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from threading import Lock

from domain.models import ApiKey


def _hash_key(raw: str) -> str:
    """Return the SHA-256 hex digest of *raw*."""
    return hashlib.sha256(raw.encode()).hexdigest()


class APIKeyRepository:
    def __init__(self) -> None:
        self._lock = Lock()
        self._keys: dict[str, ApiKey] = {}  # keyed by SHA-256 hash

    def create_key(self, user_id: str, name: str) -> tuple[str, ApiKey]:
        """Create a new API key.

        Returns a ``(raw_key, ApiKey)`` tuple.  Only the SHA-256 hash
        of the raw key is stored; the caller must show the raw key to
        the user immediately — it cannot be recovered later.
        """
        raw = secrets.token_urlsafe(32)
        key_hash = _hash_key(raw)
        prefix = raw[-4:]
        created_at = datetime.now(timezone.utc).isoformat()
        ak = ApiKey(
            id=key_hash,
            prefix=prefix,
            user_id=user_id,
            name=name,
            created_at=created_at,
        )
        with self._lock:
            self._keys[key_hash] = ak
        return raw, ak

    def list_keys(self, user_id: str) -> list[ApiKey]:
        with self._lock:
            return [v for v in self._keys.values() if v.user_id == user_id]

    def delete_key(self, user_id: str, key_id: str) -> bool:
        """Delete a key by its stable *key_id* (SHA-256 hash)."""
        with self._lock:
            entry = self._keys.get(key_id)
            if entry and entry.user_id == user_id:
                del self._keys[key_id]
                return True
            return False

    def user_for_key(self, raw_key: str) -> str | None:
        """Return the ``user_id`` associated with *raw_key*, or ``None``.

        The incoming raw key is hashed with SHA-256 before lookup.
        """
        key_hash = _hash_key(raw_key)
        with self._lock:
            entry = self._keys.get(key_hash)
            return entry.user_id if entry else None
