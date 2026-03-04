# SSD Solar — Architecture & Security Design

> **Audience:** software architects and security engineers.
> **Scope:** full-stack description of the SSD Solar monitoring application, with primary focus on the security controls implemented across the API layer.

**Related Documents:**
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md) — Full OWASP Top 10 & Proactive Controls compliance matrix
- [README.md](README.md) — Installation, usage, and configuration

---

## 1. System Overview

SSD Solar is a real-time monitoring platform for a photovoltaic installation. It ingests sensor telemetry via MQTT, processes events through a Complex Event Processing (CEP) engine (Apache Siddhi), and exposes the data through a secured REST API consumed by a lightweight single-page application (SPA).

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT BROWSER                             │
│  SPA (Vanilla JS)  ──── Authorization: Bearer <JWT> ────►          │
│                    ──── X-API-Key: <token> ─────────────►          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FLASK APPLICATION                            │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  auth_bp     │  │  api_bp      │  │  frontend_bp             │  │
│  │  /login      │  │  /api/me     │  │  / → index.html          │  │
│  │  /authorize  │  │  /api/stats  │  └──────────────────────────┘  │
│  │  /api/logout │  │  /api/cep/.. │                                 │
│  └──────┬───────┘  │  /api/keys   │  ┌──────────────────────────┐  │
│         │          └──────┬───────┘  │  Flasgger (Swagger UI)   │  │
│  Google │                 │          │  /api/docs/               │  │
│  OAuth  │    DI Container │          └──────────────────────────┘  │
│         ▼                 ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │          In-Memory Repositories (thread-safe)                │   │
│  │   UserRepository  │  APIKeyRepository  │  AlertRepository    │   │
│  │                   │  StatsRepository                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌───────────────────────┐   ┌──────────────────────────────────┐   │
│  │  SensorMQTTClient     │   │  CEPMQTTClient                   │   │
│  │  (daemon thread)      │   │  (daemon thread)                 │   │
│  └──────────┬────────────┘   └──────────────┬───────────────────┘   │
└─────────────┼────────────────────────────────┼─────────────────────┘
              │ MQTT                           │ MQTT
              ▼                               ▼
     ┌────────────────┐             ┌──────────────────┐
     │  MQTT Broker   │◄────────────│  Siddhi CEP      │
     │  (Mosquitto)   │  publish    │  (Docker)        │
     └────────────────┘  alerts     └──────────────────┘
              ▲
              │ MQTT publish (sensor data)
     ┌────────────────┐
     │  Home Assistant│
     │  (solar sensors│
     └────────────────┘
```

---

## 2. Directory Structure

```
ssd-solar/
├── app.py                          ← Entry point (Flask app factory)
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── config/
│   └── settings.py                 ← Environment-driven configuration
├── domain/
│   ├── commands/                    ← Domain commands & queries (CQRS)
│   │   ├── get_stats.py
│   │   ├── list_alerts.py
│   │   ├── clear_alerts.py
│   │   ├── list_keys.py
│   │   ├── create_api_key.py
│   │   └── delete_api_key.py
│   ├── events/                     ← Domain events (CQRS-lite)
│   │   ├── api_key_created.py
│   │   └── sensor_data_received.py
│   ├── handlers/                   ← Command, query & event handlers
│   └── models/                     ← Pure domain dataclasses
│       ├── api_key.py
│       ├── user.py
│       ├── stats.py
│       └── cep.py
├── infrastructure/
│   ├── api/
│   │   ├── auth.py                 ← OAuth 2.0 flow + JWT + login_required
│   │   ├── resources.py            ← REST endpoints
│   │   └── static.py               ← SPA static file serving
│   ├── messaging/
│   │   ├── sensor_mqtt.py          ← HA sensor subscriber (daemon thread)
│   │   └── cep_mqtt.py             ← Siddhi CEP subscriber + publisher
│   └── storage/
│       ├── user_repo.py
│       ├── api_key_repo.py
│       ├── stats_repo.py
│       └── alert_repo.py
└── backend/
    ├── composition.py              ← Composition root (DI, CORS, Talisman, errors)
    └── container.py                ← dependency-injector container
```

---

## 3. Architecture Patterns

| Pattern | Implementation |
|---|---|
| **Layered architecture** | `domain` → `infrastructure` → `backend` (composition) |
| **Dependency Injection** | `dependency-injector` DeclarativeContainer; all repositories are singletons wired by `@inject` + `Provide[...]` |
| **CQRS / Mediator** | All API operations dispatched as domain commands/queries via `mediatr`; controllers never access repositories directly |
| **Blueprint decomposition** | `auth_bp` (OAuth flows), `api_bp` (REST), `frontend_bp` (SPA) registered independently |

---

## 4. Security Architecture

This section details each security control, its location in the codebase, and its rationale.

---

### 4.1 Access Control

**Location:** `infrastructure/api/auth.py` — `login_required` decorator  
**Coverage:** every `api_bp` route except `/api/me` (which is a status probe — returns `{"authenticated": false, 401}` when unauthenticated)

```
Request
  │
  ├─ Authorization: Bearer <jwt>  ──► _resolve_jwt_user() [before_request hook]
  │                                        │
  │                                   jwt.decode() with HS256
  │                                        │
  │                                   g.current_user = {id, name, email, picture}
  │
  └─ X-API-Key: <raw_token>  ──────► login_required wrapper
                                          │
                                     SHA-256 hash of raw_token → lookup in APIKeyRepository
                                          │
                                     user_repo.get(user_id) → g.current_user populated
                                          │
                                     audit log: API_KEY_AUTH_SUCCESS / API_KEY_AUTH_FAIL
```

`g.current_user` is always a fully populated dict (or `None`) regardless of auth method. Routes that use `g.current_user['id']` (key management) are safe under both JWT and API-key authentication.

**Principle applied:** *fail-closed* — `g.current_user` is initialised to `None` at the start of every request by the `before_request` hook, and only set upon successful cryptographic verification.

---

### 4.2 API Keys

**Location:** `domain/models/api_key.py`, `infrastructure/storage/api_key_repo.py`

| Property | Implementation |
|---|---|
| **Generation** | `secrets.token_urlsafe(32)` — cryptographically secure, 256 bits of entropy |
| **Storage** | SHA-256 hash of the raw key stored in-memory; only the hash and a 4-character display prefix are persisted |
| **Transmission** | Raw key returned **only** in the `POST /api/keys` `201` response; `GET /api/keys` responses show a masked prefix (`***xxxx`) |
| **Lookup** | Incoming `X-API-Key` header value is hashed with SHA-256 and looked up by hash |
| **Revocation** | `DELETE /api/keys/<key_id>` uses the stable SHA-256 hash as identifier; verifies `user_id` ownership before deletion |
| **Transport** | Accepted **only** via `X-API-Key` request header — query parameters are explicitly rejected (they appear in server/proxy access logs) |

```python
# api_key_repo.py — storage flow
raw = secrets.token_urlsafe(32)          # 43-char URL-safe base64
key_hash = hashlib.sha256(raw.encode()).hexdigest()
prefix = raw[-4:]                        # last 4 chars for masked display
ApiKey(id=key_hash, prefix=prefix, …)
# only the hash is stored; raw key returned once and discarded
```

---

### 4.3 JWT Authentication

**Location:** `infrastructure/api/auth.py`

- **Issuer:** Flask backend, after successful Google OAuth 2.0 callback
- **Algorithm:** HS256 with `SECRET_KEY` (loaded from environment)
- **Claims:** `sub` (user id), `name`, `email`, `picture`, `iat`, `exp` (24-hour expiry)
- **Delivery:** redirected as URL fragment (`/#token=<jwt>`) — fragment is never sent to the server in subsequent requests; stored in `localStorage` by the SPA
- **Verification:** `jwt.decode()` with explicit algorithm allowlist (`algorithms=['HS256']`) on every request via the `before_request` hook

**Error handling (audit-logged, not silently swallowed):**

```python
except jwt.ExpiredSignatureError:
    LOG.warning('JWT_EXPIRED ip=%s', request.remote_addr)
except jwt.InvalidTokenError as exc:
    LOG.warning('JWT_INVALID ip=%s reason=%s', request.remote_addr, exc)
```

---

### 4.4 HTTP Method Restriction

**Location:** `infrastructure/api/resources.py` — `@api_bp.route(..., methods=[...])`

Flask's Blueprint routing enforces the declared method allowlist. Any request with an undeclared method receives an automatic `405 Method Not Allowed`. The global error handler normalises this to JSON:

```json
{ "error": "Method not allowed" }
```

| Route | Allowed methods |
|---|---|
| `/api/me` | GET |
| `/api/stats` | GET |
| `/api/cep/alerts` | GET, DELETE |
| `/api/keys` | GET, POST |
| `/api/keys/<key>` | DELETE |

---

### 4.5 Input Validation

**Location:** `infrastructure/api/resources.py` — `KeyCreateSchema`  
**Library:** `marshmallow`

```python
class KeyCreateSchema(Schema):
    name = fields.Str(
        load_default='default',
        validate=[
            validate.Length(min=1, max=64,
                error='Name must be between 1 and 64 characters.'),
            validate.Regexp(r'^[\w\s\-]+$',
                error='Name may only contain letters, digits, spaces, underscores and hyphens.'),
        ],
    )
```

Validation failure returns `400 Bad Request` with a structured error body:

```json
{ "error": { "name": ["Length must be between 1 and 64."] } }
```

**Principle applied:** allowlist validation (positive pattern match) rather than denylist — the regex only permits known-safe characters, implicitly rejecting injection payloads (`<script>`, `'; DROP TABLE`, etc.).

---

### 4.6 Content-Type Validation

**Location:** `infrastructure/api/resources.py` — `POST /api/keys`

```python
if not request.is_json:
    return jsonify({'error': 'Content-Type must be application/json'}), 415
data = request.get_json()
```

`request.is_json` checks the `Content-Type` header strictly. Requests with missing or incorrect media type (e.g. `text/plain`, `multipart/form-data`) are rejected with `415 Unsupported Media Type` before any body parsing occurs.

This prevents:
- CSRF via form-encoded cross-origin POST (browsers cannot set `Content-Type: application/json` on cross-origin form submissions without a preflight)
- Silent acceptance of non-JSON bodies that could mask injection attempts

---

### 4.7 Error Handling

**Location:** `backend/composition.py` — `_register_error_handlers()`

All HTTP errors return a consistent JSON envelope. No stack traces or internal details are exposed to the client.

| Code | Error body |
|---|---|
| `400` | `{"error": "<werkzeug description>"}` |
| `401` | `{"error": "Authentication required"}` |
| `403` | `{"error": "Forbidden"}` |
| `404` | `{"error": "Not found"}` |
| `405` | `{"error": "Method not allowed"}` |
| `415` | `{"error": "Content-Type must be application/json"}` |
| `500` | `{"error": "Internal server error"}` + exception logged server-side |

The `500` handler calls `LOG.exception(...)` so the full traceback is captured in application logs while only a generic message is returned to the client — preventing Information Exposure (OWASP A05).

---

### 4.8 Audit Logging

**Location:** `infrastructure/api/auth.py`, `infrastructure/api/resources.py`  
**Mechanism:** Python standard `logging` module; level controlled via `LOGLEVEL` env var

| Event | Level | Fields logged |
|---|---|---|
| OAuth login success | INFO | `user_id`, `email`, `ip` |
| JWT expired | WARNING | `ip` |
| JWT invalid | WARNING | `ip`, `reason` |
| API key auth success | INFO | `user_id`, `ip` |
| API key auth failure | WARNING | `ip`, `path` |
| Generic auth failure | WARNING | `ip`, `path` |
| API key created | INFO | `user_id`, `name` |
| API key deleted | INFO | `user_id` |
| API key not found on delete | WARNING | `user_id` |
| CEP alerts cleared | INFO | `user_id`, `count` |

Log format example:
```
2026-02-28 12:00:00 INFO infrastructure.api.auth LOGIN_SUCCESS user_id=google|123 email=user@domain.com ip=192.168.1.10
2026-02-28 12:01:00 WARNING infrastructure.api.auth JWT_EXPIRED ip=10.0.0.5
```

---

### 4.9 Security Headers

**Location:** `backend/composition.py` — `Talisman(app, ...)`  
**Library:** `flask-talisman`

| Header | Value | Purpose |
|---|---|---|
| `X-Frame-Options` | `DENY` | Prevents clickjacking (iFrame embedding) |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter (defence in depth) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits referrer information leakage |
| `Content-Security-Policy` | Strict policy (see below) | Mitigates XSS, clickjacking, data injection |
| `Strict-Transport-Security` | disabled until TLS termination is confirmed | Prevents protocol downgrade |

**CSP policy (SPA):**

| Directive | Value | Rationale |
|---|---|---|
| `default-src` | `'self'` | Only same-origin resources by default |
| `script-src` | `'self'` + nonce | No `unsafe-inline`; inline handlers removed from HTML |
| `style-src` | `'self'` | External `style.css` file; no inline styles |
| `img-src` | `'self' data: https://*.googleusercontent.com` | User profile pictures from Google |
| `font-src` | `'self'` | Same-origin fonts only |
| `connect-src` | `'self'` | Fetch/XHR to own API only |
| `frame-ancestors` | `'none'` | Prevents embedding in iframes (clickjacking) |
| `base-uri` | `'self'` | Prevents `<base>` tag hijacking |
| `form-action` | `'self' https://accounts.google.com` | OAuth redirect forms |

A **relaxed CSP** is applied automatically to Swagger UI paths (`/api/docs/*`, `/flasgger_static/*`, `/apispec.json`) via an `after_request` hook registered **before** Talisman. Flask calls `after_request` hooks in reverse registration order (LIFO), so our hook runs **after** Talisman and can override the strict CSP on Swagger paths only:

```python
swagger_csp = {
    'default-src': "'self'",
    'script-src': "'self' 'unsafe-inline'",
    'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
    'img-src': "'self' data:",
    'font-src': "'self' https://fonts.gstatic.com",
    'connect-src': "'self'",
    'frame-ancestors': "'none'",
}
```

**Session cookie flags:**

| Flag | Value | Purpose |
|---|---|---|
| `Secure` | `True` | Cookie only sent over HTTPS |
| `HttpOnly` | `True` | Not accessible via JavaScript |
| `SameSite` | `Lax` | Mitigates CSRF and cross-site timing attacks |

```python
# Session cookie configuration (backend/__init__.py)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

# Talisman configuration (backend/composition.py)
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

Talisman(
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
```

---

### 4.10 Sensitive Information in HTTP Requests

| Risk | Mitigation |
|---|---|
| API key in server access logs | `?api_key=` query parameter **removed**; only `X-API-Key` header accepted |
| Raw API key persisted server-side | Keys stored as **SHA-256 hashes** in-memory; raw key returned only once at creation time |
| Raw API key exposed in listing | `GET /api/keys` returns a masked prefix (`***xxxx`); full key never retrievable after creation |
| JWT in server access logs | Delivered as URL fragment (`/#token=…`); fragments are not sent to servers in `Referer` or log requests |
| Secrets in source code | All secrets (`SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) loaded exclusively from `.env` file via `python-dotenv` |

---

### 4.11 CORS

**Location:** `backend/composition.py` — `CORS(app, ...)`  
**Library:** `flask-cors`  
**Configuration:** `config/settings.py` — `ALLOWED_ORIGINS`

```python
CORS(app, resources={r'/api/*': {'origins': settings.ALLOWED_ORIGINS}})
```

`ALLOWED_ORIGINS` is populated from the `ALLOWED_ORIGINS` environment variable (comma-separated). The default is restricted to `http://localhost:5000`. A wildcard (`*`) is never used.

`flask-cors` automatically handles `OPTIONS` preflight requests. Cross-origin calls from unlisted origins receive no `Access-Control-Allow-Origin` header, which browsers treat as a CORS block.

**Scope:** CORS policy applies only to `/api/*`. The frontend SPA (`/`) is served from the same origin, so no CORS header is needed there.

---

### 4.12 HTTP Response Codes

All endpoints return semantically correct HTTP status codes:

| Scenario | Code |
|---|---|
| Successful GET | `200 OK` |
| Resource created | `201 Created` |
| Authentication missing or invalid | `401 Unauthorized` |
| Resource not found | `404 Not Found` |
| Method not declared on route | `405 Method Not Allowed` |
| Wrong `Content-Type` on POST | `415 Unsupported Media Type` |
| Schema validation failure | `400 Bad Request` |
| Unhandled server exception | `500 Internal Server Error` |

---

### 4.13 API Documentation (Swagger / OpenAPI)

**Location:** `backend/composition.py` — `Swagger(app, template=SWAGGER_TEMPLATE, ...)`  
**Library:** `flasgger`  
**UI endpoint:** `/api/docs/`  
**Spec endpoint:** `/apispec.json`

All endpoints are documented with inline YAML docstrings (in English) following the Swagger 2.0 spec. Security schemes declared in the global template:

| Scheme | Type | Location | Header name |
|---|---|---|---|
| `bearerAuth` | `apiKey` | header | `Authorization` (format: `Bearer <token>`) |
| `apiKeyHeader` | `apiKey` | header | `X-API-Key` |

> **Note:** `apiKeyQuery` (the deprecated `?api_key=` scheme) has been removed from both the Swagger template and all endpoint security declarations.

---

## 5. Data Flow

### 5.1 Sensor telemetry ingest

```
Home Assistant ─── MQTT publish ──► ssd-solar/sensor/+/state
                                          │
                                   SensorMQTTClient (daemon thread)
                                          │
                                   SensorDataReceived event
                                          │
                                   Mediator → SensorDataReceivedHandler
                                          │
                                   StatsRepository.update_topic()
                                          │
                                   CEPMQTTClient.publish() ──► ssd-solar/events/sensor
                                                                      │
                                                               Siddhi CEP engine
                                                               (battery_power_high throttled
                                                                to 1 alert per 5 min)
                                                                      │
                                                               ssd-solar/cep/alerts
                                                                      │
                                                               CEPMQTTClient (subscribe)
                                                                      │
                                                               AlertRepository.add_alert()
```

### 5.2 Authenticated API request

```
Browser
  │ GET /api/stats
  │ Authorization: Bearer <jwt>
  ▼
_resolve_jwt_user()  [before_request]
  │ jwt.decode() → g.current_user populated
  ▼
login_required wrapper
  │ g.current_user is not None → passes
  ▼
stats() route handler
  │ @inject → StatsRepository injected by DI container
  ▼
StatsRepository.get_stats().to_dict()
  ▼
jsonify(200)
  ▼
Talisman after_request → security headers appended
  ▼
CORS after_request → Access-Control-Allow-Origin appended (if origin in allowlist)
  ▼
Response to browser
```

---

## 6. Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | **yes** | HMAC key for JWT signing — minimum 32 random bytes |
| `GOOGLE_CLIENT_ID` | **yes** | Google OAuth 2.0 client ID |
| `GOOGLE_CLIENT_SECRET` | **yes** | Google OAuth 2.0 client secret |
| `ALLOWED_ORIGINS` | no | Comma-separated CORS origin allowlist (default: `http://localhost:5000`) |
| `MQTT_BROKER` | no | MQTT broker hostname (default: `localhost`) |
| `MQTT_PORT` | no | MQTT broker port (default: `1883`) |
| `MQTT_USERNAME` | no | MQTT broker username |
| `MQTT_PASSWORD` | no | MQTT broker password |
| `LOGLEVEL` | no | Python log level (default: `INFO`) |

---

## 7. Known Limitations & Remaining Hardening

| Item | Status | Recommendation |
|---|---|---|
| In-memory storage | By design | All repositories are in-memory; data is lost on restart. Suitable for demo/PoC; replace with a persistent store (SQLite, PostgreSQL) for production. |
| API keys hashed with SHA-256 | Implemented | API keys are stored as SHA-256 hashes. The raw key is returned only once at creation time and cannot be recovered. A memory dump will not expose usable credentials. |
| MQTT without TLS | Open | MQTT connections use plain TCP. Enable TLS (`tls_set()`) on both MQTT clients and configure the broker with a certificate. |
| HSTS / force HTTPS | Disabled | Enable `force_https=True` and `strict_transport_security=True` in `Talisman` once TLS termination is confirmed at the Flask hop. |
| Content-Security-Policy | **Enabled** | Strict CSP for the SPA (`script-src 'self'`, `frame-ancestors 'none'`). Swagger UI paths receive a relaxed policy via `after_request` hook. Inline `onclick` handlers removed from HTML. |
| No rate limiting | Open | Add `flask-limiter` to throttle `/api/login`, `POST /api/keys`, and other mutating endpoints to mitigate brute-force and DoS. |
| Dependency pinning | Open | `requirements.txt` uses unpinned packages. Run `pip freeze > requirements.lock` and reference the lockfile in CI/CD. |
| Google account allowlist | Open | Any Google account can authenticate. Add an email domain or allowlist check in `user_repo.get_or_create_from_userinfo()`. |
| Production WSGI server | Open | `app.run(host='0.0.0.0')` uses Flask's development server. Deploy with Gunicorn or uWSGI behind a reverse proxy (nginx). |
