"""API Key Management Tests - Key CRUD operations."""

import hashlib

from tests.conftest import auth_header


class TestAPIKeyManagement:
    """Functional tests for key CRUD operations."""

    def test_create_and_list_keys(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={'name': 'func-test'},
            headers=auth_header(),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'func-test'
        assert 'key' in data
        # Raw key returned at creation; must not be masked
        assert not data['key'].startswith('***')

        resp_list = client.get('/api/keys', headers=auth_header())
        keys = resp_list.get_json()['keys']
        assert any(k['name'] == 'func-test' for k in keys)
        # Listed key must be masked
        k = next(k for k in keys if k['name'] == 'func-test')
        assert k['key'].startswith('***')

    def test_delete_key_returns_200(self, client, test_user, api_key_repo):
        raw_key, entry = api_key_repo.create_key('test-user-123', 'to-delete')
        # Use the hash-based id for deletion, not the raw key
        resp = client.delete(f'/api/keys/{entry.id}', headers=auth_header())
        assert resp.status_code == 200
        assert resp.get_json()['deleted'] is True

    def test_delete_nonexistent_key_returns_404(self, client, test_user):
        resp = client.delete(
            '/api/keys/nonexistent', headers=auth_header()
        )
        assert resp.status_code == 404

    def test_user_cannot_see_other_users_keys(
        self, client, test_user, api_key_repo, user_repo
    ):
        user_repo.create(
            id_='other-user', name='Other', email='o@e.com', picture=''
        )
        api_key_repo.create_key('other-user', 'private')

        resp = client.get('/api/keys', headers=auth_header())
        keys = resp.get_json()['keys']
        assert not any(k['name'] == 'private' for k in keys)

    def test_user_cannot_delete_other_users_key(
        self, client, test_user, api_key_repo, user_repo
    ):
        """A user must not be able to delete another user's key."""
        user_repo.create(
            id_='other-user', name='Other', email='o@e.com', picture=''
        )
        _, entry = api_key_repo.create_key('other-user', 'foreign')

        resp = client.delete(f'/api/keys/{entry.id}', headers=auth_header())
        assert resp.status_code == 404
