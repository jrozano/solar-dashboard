"""Access Control Tests - Authentication enforcement on protected routes."""

import pytest


PROTECTED_ROUTES = [
    ('GET', '/api/stats'),
    ('GET', '/api/cep/alerts'),
    ('DELETE', '/api/cep/alerts'),
    ('GET', '/api/keys'),
    ('POST', '/api/keys'),
    ('DELETE', '/api/keys/some-key'),
]


class TestAccessControl:
    """Every protected endpoint must return 401 without credentials."""

    @pytest.mark.parametrize('method,path', PROTECTED_ROUTES)
    def test_returns_401_without_auth(self, client, method, path):
        resp = client.open(path, method=method)
        assert resp.status_code == 401

    def test_me_returns_401_without_auth(self, client):
        resp = client.get('/api/me')
        data = resp.get_json()
        assert resp.status_code == 401
        assert data['authenticated'] is False
