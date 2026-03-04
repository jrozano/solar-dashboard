"""API-Key Storage Tests - SHA-256 hashing verification."""

import hashlib


class TestAPIKeyStorage:
    """API keys must be stored as SHA-256 hashes, never in plain text."""

    def test_raw_key_not_stored_in_repository(self, api_key_repo, test_user):
        raw_key, entry = api_key_repo.create_key('test-user-123', 'stored')
        # The internal dict must NOT be keyed by the raw key
        assert raw_key not in api_key_repo._keys
        # It must be keyed by the SHA-256 hash
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        assert key_hash in api_key_repo._keys
        # The stored entry must not contain the raw key
        assert entry.id == key_hash

    def test_to_dict_masks_key(self, api_key_repo, test_user):
        raw_key, entry = api_key_repo.create_key('test-user-123', 'safe')
        d = entry.to_dict()
        assert 'key' in d
        # The key shown must be masked (only last 4 chars visible)
        assert d['key'].startswith('***')
        assert d['key'] == f'***{raw_key[-4:]}'
        # The raw key must NOT appear in the dict
        assert d['key'] != raw_key
        assert d['id'] != raw_key
