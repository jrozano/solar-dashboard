"""Backend package – Flask application factory."""

import logging
import os

from flask import Flask

from config import settings
from backend.composition import compose

LOG = logging.getLogger('backend')


def create_app() -> Flask:
    """Application factory: creates, configures and wires the Flask app."""

    logging.basicConfig(level=settings.LOGLEVEL)

    frontend_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'frontend',
    )
    # CSRF protection is intentionally not used here because this is a
    # stateless JSON REST API: all mutating endpoints require authentication
    # via 'Authorization: Bearer <jwt>' or 'X-API-Key' custom request headers.
    # Browsers cannot send custom headers cross-origin without a CORS preflight,
    # which is blocked by the strict CORS allowlist (settings.ALLOWED_ORIGINS).
    # The session cookie carries no auth state, and SESSION_COOKIE_SAMESITE=Lax
    # further protects it from cross-site request forgery.
    app = Flask(__name__, static_folder=frontend_path, static_url_path='')  # NOSONAR

    # Secure session cookie configuration
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )

    # Single composition call wires repos, services, auth, API, MQTT, …
    compose(app)

    return app
