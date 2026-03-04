"""OAuth + JWT auth helpers - infrastructure layer.

Contains the ``auth_bp`` Blueprint with OAuth redirect flows that
issue JWT tokens, and the ``login_required`` decorator used by API
routes.  The frontend stores the JWT in localStorage and sends it
via the ``Authorization: Bearer <token>`` header.

Dependencies are injected automatically by the ``dependency-injector``
container.
"""

import logging
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from authlib.integrations.flask_client import OAuth
from flask import (
    Blueprint,
    Flask,
    g,
    jsonify,
    redirect,
    request,
    url_for,
)


from dependency_injector.wiring import inject, Provide

from config import settings
from infrastructure.storage.api_key_repo import APIKeyRepository
from infrastructure.storage.user_repo import UserRepository

JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_HOURS = 24

LOG = logging.getLogger('infrastructure.api.auth')


oauth = OAuth()
auth_bp = Blueprint('auth', __name__)


# Auth routes

@auth_bp.route('/login')
def login():
    redirect_uri = url_for('auth.authorize', _external=True, _scheme='https')
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/api/login')
def api_login():
    redirect_uri = url_for('auth.authorize', _external=True, _scheme='https')
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/authorize')
@auth_bp.route('/api/authorize')
@inject
def authorize(
    user_repo: UserRepository = Provide['user_repo'],
):
    token = oauth.google.authorize_access_token()
    userinfo = token.get('userinfo')
    if not userinfo:
        userinfo = oauth.google.userinfo()
    domain_user = user_repo.get_or_create_from_userinfo(userinfo)
    LOG.info(
        'LOGIN_SUCCESS user_id=%s email=%s ip=%s',
        domain_user.id,
        domain_user.email,
        request.remote_addr,
    )

    now = datetime.now(timezone.utc)
    jwt_token = jwt.encode(
        {
            'sub': domain_user.id,
            'name': domain_user.name,
            'email': domain_user.email,
            'picture': domain_user.picture,
            'iat': now,
            'exp': now + timedelta(hours=JWT_EXPIRY_HOURS),
        },
        settings.SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    return redirect(f'/#token={jwt_token}')


@auth_bp.route('/api/logout')
def logout():
    """No server state to clear - the frontend simply drops the JWT."""
    return redirect('/')


def init_auth(app: Flask) -> None:
    """Configure OAuth provider and register the auth blueprint."""

    app.secret_key = settings.SECRET_KEY

    oauth.init_app(app)
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        client_kwargs={'scope': 'openid email profile'},
    )

    app.register_blueprint(auth_bp)


def _resolve_jwt_user():
    """Populate ``g.current_user`` from the Bearer token if present."""
    g.current_user = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        try:
            payload = jwt.decode(
                auth_header[7:],
                settings.SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
            )
            g.current_user = {
                'id': payload['sub'],
                'name': payload.get('name', ''),
                'email': payload.get('email', ''),
                'picture': payload.get('picture', ''),
            }
        except jwt.ExpiredSignatureError:
            LOG.warning('JWT_EXPIRED ip=%s', request.remote_addr)
        except jwt.InvalidTokenError as exc:
            LOG.warning('JWT_INVALID ip=%s reason=%s', request.remote_addr, exc)


def register_jwt_hook(app: Flask) -> None:
    """Register the before-request hook that resolves JWT tokens."""
    app.before_request(_resolve_jwt_user)


def login_required(f):
    """Guard that checks JWT Bearer token *or* X-API-Key header.

    On successful API-key authentication ``g.current_user`` is populated
    from the user repository so that downstream routes behave identically
    regardless of auth method.  The ``?api_key`` query parameter is NOT
    supported - query params are recorded in server/proxy access logs.
    """

    @wraps(f)
    @inject
    def wrapper(
        *args,
        api_key_repo: APIKeyRepository = Provide['api_key_repo'],
        user_repo: UserRepository = Provide['user_repo'],
        **kwargs,
    ):
        if g.current_user is not None:
            return f(*args, **kwargs)

        api_key = request.headers.get('X-API-Key')
        if api_key:
            user_id = api_key_repo.user_for_key(api_key)
            if user_id is not None:
                user = user_repo.get(user_id)
                if user:
                    g.current_user = {
                        'id': user.id,
                        'name': user.name,
                        'email': user.email,
                        'picture': user.picture,
                    }
                else:
                    # User profile not in repo (e.g. server restart
                    # cleared the in-memory store).  The API key is
                    # still valid — grant access with minimal context.
                    g.current_user = {
                        'id': user_id,
                        'name': '',
                        'email': '',
                        'picture': '',
                    }
                LOG.info(
                    'API_KEY_AUTH_SUCCESS user_id=%s ip=%s',
                    user_id,
                    request.remote_addr,
                )
                return f(*args, **kwargs)
            LOG.warning(
                'API_KEY_AUTH_FAIL ip=%s path=%s',
                request.remote_addr,
                request.path,
            )

        LOG.warning('AUTH_FAIL ip=%s path=%s', request.remote_addr, request.path)
        return jsonify({'message': 'Authentication required'}), 401

    return wrapper
