"""API-Key Authentication Tests - X-API-Key header validation."""

from tests.conftest import auth_header


class TestAPIKeyAuth:
    """X-API-Key header authentication must work; query param must not."""

    def test_valid_api_key_header_grants_access(
        self, client, test_user, api_key_repo
    ):
        raw_key, _ = api_key_repo.create_key('test-user-123', 'ci')
        resp = client.get('/api/stats', headers={'X-API-Key': raw_key})
        assert resp.status_code == 200

    def test_invalid_api_key_returns_401(self, client):
        resp = client.get(
            '/api/stats', headers={'X-API-Key': 'invalid-key'}
        )
        assert resp.status_code == 401

    def test_query_param_api_key_not_accepted(
        self, client, test_user, api_key_repo
    ):
        """The ?api_key query parameter must NOT grant access."""
        raw_key, _ = api_key_repo.create_key('test-user-123', 'leak')
        resp = client.get(f'/api/stats?api_key={raw_key}')
        assert resp.status_code == 401
