"""CORS Tests - Origin allowlist validation."""


class TestCORS:
    """CORS must restrict origins to the configured allowlist."""

    def test_allowed_origin_gets_cors_header(self, client):
        resp = client.get(
            '/api/me',
            headers={'Origin': 'http://localhost:5000'},
        )
        acao = resp.headers.get('Access-Control-Allow-Origin', '')
        assert acao == 'http://localhost:5000'

    def test_disallowed_origin_no_cors_header(self, client):
        resp = client.get(
            '/api/me',
            headers={'Origin': 'https://evil.com'},
        )
        acao = resp.headers.get('Access-Control-Allow-Origin')
        assert acao is None or 'evil.com' not in acao
