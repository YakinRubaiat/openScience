# openScience REST API

Production-ready REST API for the [openScience](../../README.md) AI workbench,
built with **FastAPI**, **SQLAlchemy**, **Pydantic v2**, **JWT auth**, **Alembic**
migrations and token-bucket **rate limiting**.

## Quick start

```bash
# Install with API extras
pip install -e ".[api]"

# Run migrations (creates openscience.db)
alembic upgrade head

# Start the server
openscience-api                     # or: uvicorn openscience.api.main:app --reload
```

Interactive docs:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health probe: `GET /health`

## Configuration

All settings come from environment variables prefixed with `OPENSCIENCE_API_`:

| Variable | Default | Description |
| --- | --- | --- |
| `OPENSCIENCE_API_SECRET_KEY` | dev key | **Set this in production** — signs JWTs |
| `OPENSCIENCE_API_ALGORITHM` | `HS256` | JWT signing algorithm |
| `OPENSCIENCE_API_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `OPENSCIENCE_API_DATABASE_URL` | `sqlite:///openscience.db` | SQLAlchemy URL |
| `OPENSCIENCE_API_CORS_ORIGINS` | `["*"]` | Allowed CORS origins (JSON list or single value) |
| `OPENSCIENCE_API_RATE_LIMIT` | `60/minute` | Per-IP request limit |
| `OPENSCIENCE_API_RATE_LIMIT_ENABLED` | `true` | Toggle rate limiting |
| `OPENSCIENCE_API_DEBUG` | `false` | Debug mode / uvicorn reload |

## Authentication (JWT)

1. Register: `POST /api/v1/auth/register`
2. Login: `POST /api/v1/auth/login` → returns `{ "access_token": "...", "token_type": "bearer" }`
3. Send the token on every request: `Authorization: Bearer <token>`

Passwords are hashed with `pbkdf2_sha256` (passlib). Tokens are short-lived JWTs
with `sub` (user id), `exp`, and `iat` claims.

```bash
curl -X POST localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username": "alice", "email": "alice@example.com", "password": "supersecret1"}'

TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "alice", "password": "supersecret1"}' | jq -r .access_token)
```

## Endpoints

All endpoints are versioned under `/api/v1` and (except `auth`) require a bearer token.

### Auth

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Create a user |
| `POST` | `/api/v1/auth/login` | Obtain a JWT |
| `GET` | `/api/v1/auth/me` | Current user profile |

### Agents

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/agents` | List all registered agents |
| `GET` | `/api/v1/agents/{name}` | Agent details (skills, input/output types) |

### Sessions

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/sessions` | Create a session |
| `GET` | `/api/v1/sessions/{id}` | Session metadata |
| `POST` | `/api/v1/sessions/{id}/load` | Load a dataset |
| `POST` | `/api/v1/sessions/{id}/analyze` | Run an analysis task |
| `POST` | `/api/v1/sessions/{id}/visualize` | Visualize an analysis result |
| `POST` | `/api/v1/sessions/{id}/write` | Generate a methods/write-up |
| `GET` | `/api/v1/sessions/{id}/results` | All results + task history |
| `DELETE` | `/api/v1/sessions/{id}` | Delete a session |

### Analysis

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/analysis/capabilities` | Analysis-capable agents |

### Example workflow

```bash
SID=$(curl -s -X POST localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name": "pbmc-study"}' | jq -r .id)

curl -X POST localhost:8000/api/v1/sessions/$SID/load \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"file_path": "data/pbmc_10k.h5ad", "format": "auto", "name": "pbmc"}'

curl -X POST localhost:8000/api/v1/sessions/$SID/analyze \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"task": "quality control and clustering", "specialist": "qc_analyzer"}'

curl -X POST localhost:8000/api/v1/sessions/$SID/visualize \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"type": "umap", "style": "publication"}'

curl -X POST localhost:8000/api/v1/sessions/$SID/write \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"style": "nature", "citation_format": "apa"}'

curl -s localhost:8000/api/v1/sessions/$SID/results -H "Authorization: Bearer $TOKEN" | jq
```

## Database & migrations

SQLAlchemy models live in `openscience/api/models/` (users, sessions, tasks,
agent registry). Schema migrations are managed with Alembic:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
alembic downgrade -1
```

`alembic/env.py` honors `OPENSCIENCE_API_DATABASE_URL`, so the same migration
history works against SQLite (dev) or PostgreSQL (production).

## Security

- All request bodies are validated with Pydantic (types, lengths, patterns);
  file paths are rejected when they contain traversal segments (`..`).
- Passwords hashed with `pbkdf2_sha256`; only hashes are persisted.
- Stateless JWT auth (`sub`/`exp`/`iat`), 401/403 on invalid or expired tokens.
- Session ownership is enforced on every session-scoped endpoint.
- Rate limiting via `slowapi` (token bucket per client IP).
- CORS middleware with configurable origins/methods/headers.
- Structured error responses; internal errors never leak stack traces.

## Tests

```bash
python -m pytest tests/api/ -v
```

The suite spins up the app against a throwaway SQLite database and covers
authentication, authorization, agent listing, the full session lifecycle,
validation errors, and the OpenAPI schema.
