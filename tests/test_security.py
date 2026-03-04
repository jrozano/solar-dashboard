"""Security-focused unit tests for the SSD Solar REST API.

Validates the security controls required by the OWASP-aligned audit:
 - Access control (authentication enforcement)
 - JWT authentication (valid / expired / tampered tokens)
 - API-key authentication (X-API-Key header; no query-param support)
 - Input validation (marshmallow schema on POST /api/keys)
 - Content-Type enforcement (415 on non-JSON POST)
 - API-key hashing (raw key stored as SHA-256 hash, never in plain text)
 - Sensitive-data protection (raw key not in GET /api/keys)
 - JSON error handlers (404, 405)
 - Security headers (Talisman)
 - CORS (restricted origins)
 - Generic error messages (no stack traces)
 - HTTP method restriction (405 on undeclared methods)
 - Audit logging
"""

import hashlib
import logging

import pytest

from tests.conftest import auth_header, make_jwt


# ------------------------------------------------------------------ #
# 1. Access Control - all protected routes require authentication
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# 2. JWT Authentication
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# 3. API-Key Authentication
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# 4. Input Validation (marshmallow)
# ------------------------------------------------------------------ #

class TestInputValidation:
    """POST /api/keys must validate the 'name' field with marshmallow."""

    def test_valid_name_accepted(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={'name': 'my-key_01'},
            headers=auth_header(),
        )
        assert resp.status_code == 201

    def test_empty_name_rejected(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={'name': ''},
            headers=auth_header(),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert 'error' in data

    def test_name_too_long_rejected(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={'name': 'a' * 65},
            headers=auth_header(),
        )
        assert resp.status_code == 400

    def test_name_with_special_chars_rejected(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={'name': '<script>alert(1)</script>'},
            headers=auth_header(),
        )
        assert resp.status_code == 400

    def test_name_with_sql_injection_rejected(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={'name': "'; DROP TABLE keys; --"},
            headers=auth_header(),
        )
        assert resp.status_code == 400

    def test_default_name_used_when_omitted(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={},
            headers=auth_header(),
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'default'


# ------------------------------------------------------------------ #
# 5. Content-Type Enforcement
# ------------------------------------------------------------------ #

class TestContentType:
    """POST endpoints must reject requests without application/json."""

    def test_post_keys_requires_json_content_type(self, client, test_user):
        resp = client.post(
            '/api/keys',
            data='name=test',
            content_type='application/x-www-form-urlencoded',
            headers=auth_header(),
        )
        assert resp.status_code == 415

    def test_post_keys_accepts_json(self, client, test_user):
        resp = client.post(
            '/api/keys',
            json={'name': 'test'},
            headers=auth_header(),
        )
        assert resp.status_code == 201


# ------------------------------------------------------------------ #
# 6. API-Key Storage
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# 7. Sensitive Data Protection
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# 8. JSON Error Handlers
# ------------------------------------------------------------------ #

class TestJSONErrorHandlers:
    """HTTP errors must return JSON, not HTML."""

    def test_404_returns_json(self, client):
        resp = client.get('/api/nonexistent')
        assert resp.status_code == 404
        data = resp.get_json()
        assert 'error' in data

    def test_405_returns_json(self, client, test_user):
        resp = client.patch('/api/stats', headers=auth_header())
        assert resp.status_code == 405
        data = resp.get_json()
        assert 'error' in data

    def test_404_no_stack_trace(self, client):
        resp = client.get('/api/nonexistent')
        body = resp.get_data(as_text=True)
        assert 'Traceback' not in body
        assert 'File "' not in body


# ------------------------------------------------------------------ #
# 9. Security Headers (Talisman)
# ------------------------------------------------------------------ #

class TestSecurityHeaders:
    """Talisman must inject standard security headers."""

    def test_x_frame_options_deny(self, client):
        resp = client.get('/api/me')
        assert resp.headers.get('X-Frame-Options') == 'DENY'

    def test_x_content_type_options_nosniff(self, client):
        resp = client.get('/api/me')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_referrer_policy(self, client):
        resp = client.get('/api/me')
        assert 'strict-origin' in resp.headers.get('Referrer-Policy', '')

    def test_csp_header_present(self, client):
        """CSP header must be present on API responses."""
        resp = client.get('/api/me')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert csp, 'Content-Security-Policy header is missing'

    def test_csp_frame_ancestors_none(self, client):
        """CSP must include frame-ancestors 'none' to prevent clickjacking."""
        resp = client.get('/api/me')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert "frame-ancestors 'none'" in csp

    def test_csp_script_src_no_unsafe_inline(self, client):
        """CSP script-src must NOT contain 'unsafe-inline' on non-Swagger paths."""
        resp = client.get('/api/me')
        csp = resp.headers.get('Content-Security-Policy', '')
        script_src = [p for p in csp.split(';') if 'script-src' in p]
        assert script_src, 'script-src directive is missing from CSP'
        assert 'unsafe-inline' not in script_src[0]

    def test_session_cookie_flags(self, app):
        """Flask session cookie must have Secure, HttpOnly and SameSite flags."""
        assert app.config['SESSION_COOKIE_SECURE'] is True
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


# ------------------------------------------------------------------ #
# 10. CORS
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# 11. HTTP Method Restriction
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# 12. Audit Logging
# ------------------------------------------------------------------ #

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


# ------------------------------------------------------------------ #
# 13. API Key Management - functional tests
# ------------------------------------------------------------------ #

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
