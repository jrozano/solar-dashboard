"""Content-Type Enforcement Tests - JSON content-type requirement."""

from tests.conftest import auth_header


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
