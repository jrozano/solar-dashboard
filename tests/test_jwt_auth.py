"""JWT Authentication Tests - Bearer token validation."""

from tests.conftest import auth_header, make_jwt


class TestJWTAuth:
    """JWT bearer tokens must be validated correctly."""

    def test_valid_jwt_grants_access(self, client, test_user):
        resp = client.get('/api/stats', headers=auth_header())
        assert resp.status_code == 200

    def test_expired_jwt_returns_401(self, client, test_user):
        token = make_jwt(expired=True)
        resp = client.get('/api/stats', headers=auth_header(token))
        assert resp.status_code == 401

    def test_invalid_jwt_returns_401(self, client, test_user):
        resp = client.get(
            '/api/stats',
            headers={'Authorization': 'Bearer not-a-valid-token'},
        )
        assert resp.status_code == 401

    def test_wrong_secret_jwt_returns_401(self, client, test_user):
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        token = pyjwt.encode(
            {'sub': 'test-user-123', 'iat': now, 'exp': now + timedelta(hours=1)},
            'wrong-secret',
            algorithm='HS256',
        )
        resp = client.get('/api/stats', headers=auth_header(token))
        assert resp.status_code == 401

    def test_me_returns_user_info_with_valid_jwt(self, client, test_user):
        resp = client.get('/api/me', headers=auth_header())
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['authenticated'] is True
        assert data['email'] == 'test@example.com'
