# Docker Guide

openScience ships with a complete containerized stack: web UI, REST API,
background workers, PostgreSQL, and Redis.

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Development stack |
| `docker-compose.prod.yml` | Production stack (nginx, SSL, monitoring) |
| `docker-compose.test.yml` | Test stack |
| `Dockerfile` | Base image |
| `Dockerfile.api` | REST API service |
| `Dockerfile.ui` | Web UI service |
| `Dockerfile.worker` | Celery worker |
| `Dockerfile.test` | Test runner image |
| `docker/init-db.sql` | Database bootstrap |
| `docker/nginx-ui.conf` | UI nginx config (dev) |
| `docker/nginx-prod.conf` | nginx config (prod) |
| `docker/prometheus.yml` | Metrics scraping config |

## Quick Start

```bash
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience
cp .env.example .env
# Edit .env — change DB_PASSWORD, REDIS_PASSWORD, SECRET_KEY

docker-compose up -d
docker-compose logs -f
open http://localhost:8080
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `ui` | 8080 | Web interface (nginx + React build) |
| `api` | 8000 | REST API |
| `worker` | — | Background Celery workers |
| `db` | 5432 | PostgreSQL |
| `redis` | 6379 | Task queue and cache |
| `flower` | 5555 | Worker monitoring |

## Everyday Commands

```bash
# Start and stop
docker-compose up -d
docker-compose down

# Stop and wipe all data (destructive!)
docker-compose down -v

# Follow logs for one service
docker-compose logs -f api

# Rebuild after code changes
docker-compose up -d --build

# Shell into the API container
docker-compose exec api bash

# Check service health
docker-compose ps
```

## Running Tests in Docker

```bash
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Production Deployment

The production compose file adds TLS termination, restart policies, resource
limits, and Prometheus metrics.

```bash
cp .env.example .env
# Set DOMAIN and SSL_EMAIL, and use strong passwords

docker-compose -f docker-compose.prod.yml up -d
```

Production checklist:

- [ ] All `.env` secrets changed from defaults
- [ ] `DOMAIN` and `SSL_EMAIL` set for certificate issuance
- [ ] PostgreSQL port 5432 not exposed publicly
- [ ] `LOG_LEVEL` set to `WARNING` or `ERROR`
- [ ] Volumes on backed-up storage (`postgres-data`, `redis-data`)

## Networking

All services share the `openscience-network` bridge network. Only the UI
(8080), API (8000), and Flower (5555) publish host ports by default.

## Volumes

| Volume | Contents |
|--------|----------|
| `postgres-data` | Database files |
| `redis-data` | Persistence data |
| `api-logs`, `worker-logs` | Application logs |

Back up the database:

```bash
docker-compose exec db pg_dump -U openscience openscience > backup.sql
```

Restore:

```bash
cat backup.sql | docker-compose exec -T db psql -U openscience openscience
```

## Troubleshooting

- **Port already in use** — change the published port in `docker-compose.yml`
  or stop the conflicting process.
- **Permission errors on logs** — the named volumes are managed by Docker;
  don't bind-mount host paths over them.
- **API unhealthy after startup** — check `docker-compose logs db`; the API
  waits for PostgreSQL to accept connections.

See [Troubleshooting](troubleshooting.md) for more fixes.
