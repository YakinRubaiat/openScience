# Configuration

openScience is configured through environment variables, typically loaded
from a `.env` file at the repository root. Copy the template to get started:

```bash
cp .env.example .env
```

## Required Settings

These must be changed from their defaults before any non-trivial deployment.

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_USER` | PostgreSQL user | `openscience` |
| `DB_PASSWORD` | PostgreSQL password | generate a strong secret |
| `DB_NAME` | PostgreSQL database name | `openscience` |
| `REDIS_PASSWORD` | Redis password | generate a strong secret |
| `SECRET_KEY` | Flask/application secret | `openssl rand -hex 32` |

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `WARNING` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DOMAIN` | `localhost` | Public hostname (used for SSL) |
| `SSL_EMAIL` | — | Contact email for certificate issuance |

## Optional Integrations

| Variable | Description |
|----------|-------------|
| `SENTRY_DSN` | Error monitoring — leave empty to disable |
| `FLOWER_USER` | Celery Flower monitoring UI username |
| `FLOWER_PASSWORD` | Celery Flower monitoring UI password |

## Port Map

Ports are fixed by the Compose files; change them there if you have conflicts.

| Service | Port | Set in |
|---------|------|--------|
| Web UI | 8080 | `docker-compose.yml` |
| REST API | 8000 | `docker-compose.yml` |
| PostgreSQL | 5432 | `docker-compose.yml` |
| Redis | 6379 | `docker-compose.yml` |
| Flower | 5555 | `docker-compose.yml` |
| Docs (mkdocs) | 8001 | `mkdocs serve --dev-addr 127.0.0.1:8001` |

> **Note:** the docs dev server would collide with the API on port 8000 —
> always pass an explicit `--dev-addr` when both run at once.

## Connector Credentials

Database connectors (PubMed, ChEMBL, cloud storage, …) read credentials from
the OS keyring, **not** from `.env`:

```bash
openscience credentials set ncbi
openscience credentials set aws
```

## Example `.env`

```bash
# Database Configuration
DB_USER=openscience
DB_PASSWORD=change-me-in-production
DB_NAME=openscience

# Redis Configuration
REDIS_PASSWORD=change-me-in-production

# Application Secret
SECRET_KEY=generate-a-random-secret-key-here

# Logging
LOG_LEVEL=WARNING

# Monitoring (optional)
SENTRY_DSN=

# Flower (Celery monitoring)
FLOWER_USER=admin
FLOWER_PASSWORD=change-me-in-production

# Domain Configuration (for SSL)
DOMAIN=localhost
SSL_EMAIL=admin@example.com
```

## Related

- [Docker Guide](docker.md) — per-service environment in Compose files
- [Security](security.md) — credential storage and sandbox policy
- [Troubleshooting](troubleshooting.md) — configuration pitfalls
