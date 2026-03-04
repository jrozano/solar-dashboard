"""Composition root - wires all application dependencies at startup.

Creates the DI ``Container``, starts background services, and
registers the Flask extensions (API, auth, blueprints).  No other
module should create repositories, engines or background threads
on its own.
"""

import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_talisman import Talisman
from flasgger import Swagger

from backend.container import Container
from config import settings
from infrastructure.api.auth import init_auth, register_jwt_hook
from infrastructure.api.resources import api_bp
from infrastructure.api.static import frontend_bp

LOG = logging.getLogger('backend.composition')

SWAGGER_TEMPLATE = {
    'swagger': '2.0',
    'info': {
        'title': 'SSD Solar API',
        'description': (
            'REST API for monitoring a photovoltaic solar installation.\n\n'
            'Authentication via JWT Bearer token (obtained after Google OAuth 2.0 login) '
            'or `X-API-Key` header.'
        ),
        'version': '1.0.0',
    },
    'basePath': '/api',
    'schemes': ['https', 'http'],
    'securityDefinitions': {
        'bearerAuth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'JWT token — format: Bearer <token> (obtained via OAuth at /api/login)',
        },
        'apiKeyHeader': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key',
            'description': 'API key generated from the dashboard',
        },
    },
}

SWAGGER_CONFIG = {
    'headers': [],
    'specs': [
        {
            'endpoint': 'apispec',
            'route': '/apispec.json',
            'rule_filter': lambda rule: rule.rule.startswith('/api'),
            'model_filter': lambda tag: True,
        },
    ],
    'static_url_path': '/flasgger_static',
    'swagger_ui': True,
    'specs_route': '/api/docs/',
}


def compose(app: Flask) -> None:
    """Wire every dependency and start background services."""

    container = Container()
    app.container = container

    _start_cep_mqtt(container)
    _start_sensor_mqtt(container)

    init_auth(app)
    register_jwt_hook(app)

    app.register_blueprint(api_bp)

    Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG)

    app.register_blueprint(frontend_bp)

    CORS(app, resources={r'/api/*': {'origins': settings.ALLOWED_ORIGINS}})

    # ---------- Content Security Policy ----------
    # Strict CSP for the SPA; Swagger UI paths get a relaxed policy
    # via the after_request hook below.
    csp = {
        'default-src': "'self'",
        'script-src': "'self'",
        'style-src': "'self'",
        'img-src': "'self' data: https://*.googleusercontent.com",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-ancestors': "'none'",
        'base-uri': "'self'",
        'form-action': "'self' https://accounts.google.com",
    }

    # Relaxed CSP for Swagger UI (flasgger) which needs inline scripts/styles
    # and external Google Fonts.  Registered BEFORE Talisman so that Flask's
    # reverse-order after_request chain lets this hook run AFTER Talisman,
    # allowing it to override the strict CSP on Swagger paths only.
    swagger_csp = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
        'img-src': "'self' data:",
        'font-src': "'self' https://fonts.gstatic.com",
        'connect-src': "'self'",
        'frame-ancestors': "'none'",
    }

    @app.after_request
    def _set_swagger_csp(response):
        """Apply a relaxed CSP only for Swagger UI paths."""
        if request.path.startswith('/api/docs') or request.path.startswith('/flasgger_static') or request.path == '/apispec.json':
            policy = '; '.join(f'{k} {v}' for k, v in swagger_csp.items())
            response.headers['Content-Security-Policy'] = policy
        return response

    talisman = Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        frame_options='DENY',
        x_content_type_options=True,
        referrer_policy='strict-origin-when-cross-origin',
        session_cookie_secure=True,
        session_cookie_http_only=True,
        session_cookie_samesite='Lax',
    )

    _register_error_handlers(app)



def _register_error_handlers(app: Flask) -> None:
    """Register JSON error handlers for all standard HTTP error codes."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': getattr(e, 'description', 'Bad request')}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Authentication required'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Forbidden'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Method not allowed'}), 405

    @app.errorhandler(415)
    def unsupported_media_type(e):
        return jsonify({'error': 'Content-Type must be application/json'}), 415

    @app.errorhandler(500)
    def internal_server_error(e):
        LOG.exception('Internal server error: %s', e)
        return jsonify({'error': 'Internal server error'}), 500


def _start_cep_mqtt(container: Container) -> None:
    """Start the CEP MQTT client (alert subscriber + event publisher)."""
    try:
        client = container.cep_mqtt()
        client.start()
        LOG.info('CEP MQTT client started')
    except Exception:
        LOG.exception('Could not start CEP MQTT client')


def _start_sensor_mqtt(container: Container) -> None:
    """Start the sensor MQTT client (HA topics subscriber)."""
    try:
        client = container.sensor_mqtt()
        client.start()
        LOG.info('Sensor MQTT client started')
    except Exception:
        LOG.exception('Could not start sensor MQTT client')

