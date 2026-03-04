"""JSON Error Handler Tests - JSON responses on errors."""


class TestJSONErrorHandlers:
    """HTTP errors must return JSON, not HTML."""

    def test_404_returns_json(self, client):
        resp = client.get('/api/nonexistent')
        assert resp.status_code == 404
        data = resp.get_json()
        assert 'error' in data

    def test_405_returns_json(self, client, test_user):
        from tests.conftest import auth_header
        resp = client.patch('/api/stats', headers=auth_header())
        assert resp.status_code == 405
        data = resp.get_json()
        assert 'error' in data

    def test_404_no_stack_trace(self, client):
        resp = client.get('/api/nonexistent')
        body = resp.get_data(as_text=True)
        assert 'Traceback' not in body
        assert 'File "' not in body
