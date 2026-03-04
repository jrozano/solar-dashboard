"""HTTP Method Restriction Tests - 405 on unsupported methods."""

from tests.conftest import auth_header


class TestHTTPMethodRestriction:
    """Routes must only accept their declared HTTP methods."""

    def test_put_on_stats_returns_405(self, client, test_user):
        resp = client.put('/api/stats', headers=auth_header())
        assert resp.status_code == 405

    def test_delete_on_stats_returns_405(self, client, test_user):
        resp = client.delete('/api/stats', headers=auth_header())
        assert resp.status_code == 405

    def test_post_on_stats_returns_405(self, client, test_user):
        resp = client.post('/api/stats', headers=auth_header())
        assert resp.status_code == 405

    def test_get_on_keys_create_allowed(self, client, test_user):
        """GET on /api/keys should work (list keys), not 405."""
        resp = client.get('/api/keys', headers=auth_header())
        assert resp.status_code == 200

    def test_patch_on_keys_returns_405(self, client, test_user):
        resp = client.patch('/api/keys', headers=auth_header())
        assert resp.status_code == 405
