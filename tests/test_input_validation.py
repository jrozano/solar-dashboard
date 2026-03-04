"""Input Validation Tests - Marshmallow schema validation on POST /api/keys."""

from tests.conftest import auth_header


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
