"""Shared test fixtures for the SSD Solar API test suite."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest

from config import settings


@pytest.fixture()
def app():
    """Create a Flask test app with MQTT clients disabled."""
    with (
        patch('backend.composition._start_cep_mqtt'),
        patch('backend.composition._start_sensor_mqtt'),
    ):
        from backend import create_app
        application = create_app()
        application.config['TESTING'] = True
        yield application


@pytest.fixture()
def client(app):
    """Flask test client bound to the test app."""
    return app.test_client()


@pytest.fixture()
def user_repo(app):
    """Return the singleton UserRepository from the DI container."""
    return app.container.user_repo()


@pytest.fixture()
def api_key_repo(app):
    """Return the singleton APIKeyRepository from the DI container."""
    return app.container.api_key_repo()


@pytest.fixture()
def test_user(user_repo):
    """Create and return a test user in the repository."""
    return user_repo.create(
        id_='test-user-123',
        name='Test User',
        email='test@example.com',
        picture='https://example.com/photo.jpg',
    )


def make_jwt(sub='test-user-123', expired=False, extra_claims=None):
    """Generate a JWT token for testing.

    Args:
        sub: Subject claim (user id).
        expired: If True the token is already expired.
        extra_claims: Dict merged into the payload.
    """
    now = datetime.now(timezone.utc)
    payload = {
        'sub': sub,
        'name': 'Test User',
        'email': 'test@example.com',
        'picture': 'https://example.com/photo.jpg',
        'iat': now,
        'exp': now + timedelta(hours=-1 if expired else 24),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def auth_header(token=None):
    """Return an Authorization header dict with a Bearer token."""
    if token is None:
        token = make_jwt()
    return {'Authorization': f'Bearer {token}'}
