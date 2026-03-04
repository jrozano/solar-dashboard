"""Sensitive Data Protection Tests - Key exposure behavior."""

from tests.conftest import auth_header


class TestSensitiveDataProtection:
    """POST /api/keys returns raw key once; GET shows only masked prefix."""

    def test_list_keys_hides_raw_key(self, client, test_user, api_key_repo):
        raw_key, _ = api_key_repo.create_key('test-user-123', 'secret')
        resp = client.get('/api/keys', headers=auth_header())
        data = resp.get_json()
        keys = data['keys']
        assert len(keys) >= 1
        k = next(k for k in keys if k['name'] == 'secret')
        # Raw key must NOT be present in listing
        assert k['key'] != raw_key
        # Only a masked prefix must be shown
        assert k['key'].startswith('***')
        assert k['key'] == f'***{raw_key[-4:]}'

    def test_create_key_returns_raw_key_once(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={'name': 'once'},
            headers=auth_header(),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'key' in data
        assert len(data['key']) > 8
        # The raw key must NOT start with the mask
        assert not data['key'].startswith('***')
