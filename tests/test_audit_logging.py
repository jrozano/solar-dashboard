"""Audit Logging Tests - Security event logging verification."""

import logging

from tests.conftest import auth_header, make_jwt


class TestAuditLogging:
    """Security-relevant actions must emit structured log messages."""

    def test_key_creation_logged(self, client, test_user, caplog):
        with caplog.at_level(logging.INFO):
            client.post(
                '/api/keys',
                json={'name': 'audit'},
                headers=auth_header(),
            )
        assert any('KEY_CREATED' in r.message for r in caplog.records)

    def test_key_deletion_logged(
        self, client, test_user, api_key_repo, caplog
    ):
        raw_key, entry = api_key_repo.create_key('test-user-123', 'del')
        with caplog.at_level(logging.INFO):
            client.delete(f'/api/keys/{entry.id}', headers=auth_header())
        assert any('KEY_DELETED' in r.message for r in caplog.records)

    def test_failed_auth_logged(self, client, caplog):
        with caplog.at_level(logging.WARNING):
            client.get(
                '/api/stats',
                headers={'X-API-Key': 'bad-key'},
            )
        assert any('API_KEY_AUTH_FAIL' in r.message for r in caplog.records)

    def test_alerts_clear_logged(
        self, client, test_user, caplog
    ):
        with caplog.at_level(logging.INFO):
            client.delete('/api/cep/alerts', headers=auth_header())
        assert any('ALERTS_CLEARED' in r.message for r in caplog.records)

    def test_expired_jwt_logged(self, client, caplog):
        token = make_jwt(expired=True)
        with caplog.at_level(logging.WARNING):
            client.get('/api/stats', headers=auth_header(token))
        assert any('JWT_EXPIRED' in r.message for r in caplog.records)
