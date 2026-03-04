# SSD Solar

Real-time monitoring platform for a photovoltaic solar installation. Ingests sensor telemetry via MQTT, processes it through a Complex Event Processing (CEP) engine, and exposes the data through a secure REST API consumed by a lightweight SPA.

> **Security:** For comprehensive security audit and OWASP Top 10 compliance matrix, see [SECURITY_AUDIT.md](SECURITY_AUDIT.md).
> For the technical architecture description and implemented security controls, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Features

- **Real-time telemetry** — MQTT subscription to 5 Home Assistant topics (PV power, load, grid, battery, and imported energy).
- **CEP engine** — Apache Siddhi integration for rule-based alert detection (e.g., battery power above threshold).
- **Secure REST API** — endpoints protected with JWT (Google OAuth 2.0) and/or API keys.
- **Lightweight SPA** — Vanilla JS web interface showing current sensor values and active alerts.
- **Interactive documentation** — Swagger UI available at `/api/docs/`.

---

## Project Structure

```
ssd-solar/
├── app.py                          ← Entry point (Flask app factory)
├── requirements.txt
├── docker-compose.yml              ← Backend + Siddhi CEP editor
├── Dockerfile
├── config/
│   └── settings.py                 ← Configuration from environment variables
├── domain/
│   ├── commands/                   ← Domain commands & queries (CQRS / Mediator)
│   ├── events/                     ← Domain events (ApiKeyCreated, SensorDataReceived)
│   ├── handlers/                   ← Command, query & event handlers (Mediator pattern)
│   └── models/                     ← Domain dataclasses (ApiKey, User, Stats, Cep)
├── frontend/
│   ├── index.html                  ← SPA entry point (links style.css)
│   ├── app.js                     ← SPA logic in Vanilla JS
│   └── style.css                  ← External styles (strict CSP compliant)
├── infrastructure/
│   ├── api/
│   │   ├── auth.py                 ← OAuth 2.0 + JWT + login_required decorator
│   │   ├── resources.py            ← REST endpoints — delegates to Mediator (no direct repo access)
│   │   └── static.py              ← Serve the SPA (/)
│   ├── messaging/
│   │   ├── sensor_mqtt.py          ← Sensor MQTT subscriber (daemon thread)
│   │   └── cep_mqtt.py            ← MQTT subscriber/publisher for Siddhi CEP
│   └── storage/
│       ├── user_repo.py            ← In-memory user repository
│       ├── api_key_repo.py         ← API keys repository (SHA-256 hashed)
│       ├── stats_repo.py           ← In-memory telemetry repository
│       └── alert_repo.py           ← CEP alerts repository
└── backend/
    ├── composition.py              ← Composition root (DI, CORS, Talisman, error handlers)
    └── container.py                ← Dependency-injector container
```

---

## Prerequisites

- Python 3.11+
- Accessible MQTT broker (Mosquitto or other)
- Google Cloud OAuth 2.0 credentials
- (Optional) Docker + Docker Compose for complete environment with Siddhi CEP

---

## Installation

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with actual values (see configuration table below)
```

---

## Configuration (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | **Yes** | `change-me` | HMAC key for JWT signing — minimum 32 random bytes |
| `GOOGLE_CLIENT_ID` | **Yes** | — | Google OAuth 2.0 application Client ID |
| `GOOGLE_CLIENT_SECRET` | **Yes** | — | Google OAuth 2.0 application Client Secret |
| `MQTT_BROKER` | No | `localhost` | MQTT broker hostname |
| `MQTT_PORT` | No | `1883` | MQTT broker port |
| `MQTT_USERNAME` | No | — | MQTT broker username |
| `MQTT_PASSWORD` | No | — | MQTT broker password |
| `ALLOWED_ORIGINS` | No | `http://localhost:5000` | Allowed CORS origins (comma-separated) |
| `LOGLEVEL` | No | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Configure Google OAuth 2.0 Credentials

1. Create a project at [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Identity / OpenID Connect** API.
3. Create credentials → **OAuth 2.0 → Web application**.
4. Add authorized redirect URIs:
   - `http://localhost:5000/authorize` (development)
   - `https://<your-domain>/authorize` (production)
5. Copy the Client ID and Client Secret to `.env`.

---

## Running

### Development Mode (Flask built-in server)

```bash
source .venv/bin/activate
python app.py
```

The application starts at `http://localhost:5000`.

### Tests

```bash
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -v
```

The test suite validates API security controls:

| Category | Description |
|---|---|
| Access Control | All protected routes return 401 without credentials |
| JWT Auth | Valid, expired, invalid, and wrong-secret tokens |
| API Key Auth | `X-API-Key` header, rejects `?api_key` query param |
| Input Validation | marshmallow schema on `POST /api/keys` (length, regex, injection) |
| Content-Type | 415 rejection if `Content-Type` is not `application/json` |
| API Key Hashing | SHA-256 hash stored; raw key never persisted |
| Sensitive Data | `GET /api/keys` does not expose keys; `POST` returns it once only |
| Error Handlers | 404, 405 return JSON without stack traces |
| Security Headers | `X-Frame-Options: DENY`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy` |
| Session Cookies | `Secure`, `HttpOnly`, and `SameSite=Lax` flags configured |
| CORS | Only origins in `ALLOWED_ORIGINS` |
| HTTP Methods | 405 on undeclared methods |
| Audit Logging | `KEY_CREATED`, `KEY_DELETED`, `API_KEY_AUTH_FAIL`, etc. |
| Key Management | Complete CRUD and user isolation |

### With Docker Compose (backend + Siddhi CEP editor)

```bash
docker compose up -d
```

| Service | URL |
|---|---|
| API + SPA | `http://localhost:5000` |
| Siddhi CEP editor | `http://localhost:9390` |

Siddhi apps from the `siddhi/apps/` directory are automatically mounted in the editor.

---

## Application Usage

### 1. Authentication

Navigate to `http://localhost:5000` → **Sign in with Google**. After the OAuth flow, the frontend receives and stores a JWT in `localStorage`. All API calls automatically include the `Authorization: Bearer <token>` header.

### 2. Sensor Dashboard

The SPA displays in real-time (polling every 5 s) the current values for:

| Metric | Description |
|---|---|
| **PV Power** (`pv_power`) | Power generated by solar panels (W) |
| **Load Power** (`load_power`) | Total installation consumption (W) |
| **Grid Power** (`grid_power`) | Exchange with the electrical grid (W, negative = export) |
| **Battery Power** (`battery_power`) | Battery charge/discharge (W) |
| **Imported Energy** (`battery`) | Accumulated energy imported from grid (kWh) |

### 3. CEP Alerts

The Siddhi engine evaluates rules defined in `siddhi/apps/SolarAlerts.siddhi` and publishes alerts via MQTT. The SPA lists active alerts and allows clearing them from the dashboard.

### 4. API Keys

From the dashboard you can generate API keys for programmatic API access without the OAuth flow. The full key is shown **only once** at creation time; subsequent queries show only an 8-character prefix.

API keys work independently of JWT / Google OAuth: once a valid key is presented via the `X-API-Key` header, the request is authenticated even if the user's full profile is no longer available in the in-memory store (e.g. after a server restart). In that case a minimal identity context (user ID only) is used.

---

## REST API

Complete interactive documentation is available at **`/api/docs/`** (Swagger UI).

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/api/me` | — | Current user authentication status |
| `GET` | `/api/stats` | ✓ | Current values for all sensors |
| `GET` | `/api/cep/alerts` | ✓ | List of active CEP alerts |
| `DELETE` | `/api/cep/alerts` | ✓ | Clear all CEP alerts |
| `GET` | `/api/keys` | ✓ | List user's API keys |
| `POST` | `/api/keys` | ✓ | Create a new API key |
| `DELETE` | `/api/keys/<key>` | ✓ | Revoke an API key |

### API Authentication

**JWT Bearer token** (obtained after OAuth login):
```
Authorization: Bearer <jwt>
```

**API key** (header only, not query param):
```
X-API-Key: <raw_key>
```

### Example — Get Telemetry

```bash
curl http://localhost:5000/api/stats \
  -H "Authorization: Bearer <your_jwt>"
```

```json
{
  "values": {
    "pv_power":      { "value": 3200.0, "timestamp": "2026-02-28T12:00:00+00:00" },
    "load_power":    { "value": 1100.0, "timestamp": "2026-02-28T12:00:00+00:00" },
    "grid_power":    { "value": -400.0, "timestamp": "2026-02-28T12:00:00+00:00" },
    "battery_power": { "value": 1700.0, "timestamp": "2026-02-28T12:00:00+00:00" }
  },
  "derived": {
    "pv_power": 3200.0,
    "load_power": 1100.0,
    "grid_power": -400.0,
    "battery_power": 1700.0
  }
}
```

### Example — Create API Key

```bash
curl -X POST http://localhost:5000/api/keys \
  -H "Authorization: Bearer <your_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-script"}'
```

```json
{
  "key": "abc123...xyz",
  "name": "my-script",
  "created_at": "2026-02-28T12:00:00+00:00"
}
```

> The `key` field only appears in this response. Store it in a secure location.

---

## MQTT Topics

| Topic | Direction | Description |
|---|---|---|
| `ssd-solar/sensor/energia_importada_de_red_battery/state` | Input | Imported energy (kWh) |
| `ssd-solar/sensor/energia_importada_de_red_battery_power/state` | Input | Battery power (W) |
| `ssd-solar/sensor/energia_importada_de_red_grid_power/state` | Input | Grid power (W) |
| `ssd-solar/sensor/energia_importada_de_red_load_power/state` | Input | Consumption power (W) |
| `ssd-solar/sensor/energia_importada_de_red_pv_power/state` | Input | PV power (W) |
| `ssd-solar/events/sensor` | Output → Siddhi | Sensor event serialized (JSON) |
| `ssd-solar/events/api_key` | Output → Siddhi | API key creation event |
| `ssd-solar/cep/alerts` | Input ← Siddhi | Alerts generated by CEP engine |

---

## Main Dependencies

| Package | Usage |
|---|---|
| `flask` | Web framework |
| `authlib` | OAuth 2.0 client (Google) |
| `PyJWT` | JWT generation and verification |
| `flasgger` | Swagger UI / OpenAPI |
| `Flask-Cors` | CORS policy per origin |
| `flask-talisman` | HTTP security headers |
| `marshmallow` | Input schema validation |
| `dependency-injector` | Dependency injection |
| `mediatr` | Event bus (CQRS-lite) |
| `paho-mqtt` | MQTT client |
| `python-dotenv` | Load `.env` |
