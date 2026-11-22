---
layout: default
title: Docker Deployment
nav_order: 8
description: "Deploy openScience with Docker and Docker Compose"
---

# Docker Deployment Guide

Docker is the recommended way to run openScience. This guide covers everything from the 30-second quick start to production deployments.

---

## Quick Start

```bash
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience

cp .env.example .env          # add your API keys
docker-compose up -d

open http://localhost:8080
```

Five services come up:

| Service | Container | Port | Purpose |
|---------|-----------|-----:|---------|
| **Web UI** | `openscience-ui` | 8080 | React front end |
| **API** | `openscience-api` | 8000 | Flask REST API |
| **Worker** | `openscience-worker` | — | Background jobs (Celery) |
| **PostgreSQL** | `postgres` | 5432 | Metadata and provenance |
| **Redis** | `redis` | 6379 | Cache and task queue |

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                  Docker Compose Network                     │
│                                                             │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│   │ openscience- │   │ openscience- │   │ openscience- │  │
│   │     ui       │──▶│     api      │──▶│   worker     │  │
│   │   :3000      │   │   :8080      │   │              │  │
│   └──────────────┘   └──────┬───────┘   └──────┬───────┘  │
│                             │                  │           │
│                      ┌──────▼───────┐   ┌──────▼───────┐  │
│                      │    Redis     │   │  PostgreSQL  │  │
│                      │    :6379     │   │    :5432     │  │
│                      └──────────────┘   └──────────────┘  │
│                                                             │
│   Named volumes: postgres_data, redis_data, artifacts       │
└─────────────────────────────────────────────────────────────┘
```

---

## Compose Files

openScience ships three compose files:

| File | Use case |
|------|----------|
| `docker-compose.yml` | Development (default) — hot-reload, debug logging |
| `docker-compose.prod.yml` | Production — optimized images, health checks, TLS-ready |
| `docker-compose.test.yml` | CI — runs the test suite in containers |

### Development

```bash
docker-compose up -d                # start everything
docker-compose up -d --build        # rebuild after code changes
docker-compose logs -f api          # tail API logs
docker-compose down                 # stop
docker-compose down -v              # stop and remove volumes (⚠️ deletes data)
```

### Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Differences from dev:

- Multi-stage built images (smaller, no dev deps)
- Read-only root filesystems
- Health checks with auto-restart
- Resource limits (CPU, memory)
- No source code mounts

### Testing

```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

Spins up ephemeral Postgres/Redis, runs `pytest`, exits.

---

## Configuration

### Environment variables

`.env` drives the stack:

```ini
# LLM
OPENAI_API_KEY=sk-...

# Postgres
POSTGRES_USER=openscience
POSTGRES_PASSWORD=change-me-in-production
POSTGRES_DB=openscience

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Compute
COMPUTE_BACKEND=local
SANDBOX_ENABLED=true

# API
API_HOST=0.0.0.0
API_PORT=8080
WORKERS=4
```

### Resource limits

```yaml
# docker-compose.prod.yml (excerpt)
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          memory: 2G
```

### Custom ports

```yaml
services:
  ui:
    ports:
      - "9090:3000"     # host:container
```

---

## Persistent Data

Named volumes survive `docker-compose down`:

```bash
docker volume ls | grep openscience
# openscience_postgres_data
# openscience_redis_data
# openscience_artifacts
```

### Back up

```bash
# Postgres dump
docker-compose exec postgres pg_dump -U openscience openscience > backup.sql

# Artifacts
docker run --rm -v openscience_artifacts:/data -v $(pwd):/backup \
  alpine tar czf /backup/artifacts.tar.gz /data
```

### Restore

```bash
cat backup.sql | docker-compose exec -T postgres psql -U openscience openscience
```

---

## Building Images Manually

```bash
# API image
docker build -f docker/Dockerfile.api -t openscience/api:latest .

# UI image
docker build -f docker/Dockerfile.ui -t openscience/ui:latest .

# Worker image
docker build -f docker/Dockerfile.worker -t openscience/worker:latest .
```

### Multi-stage build (production)

```dockerfile
# docker/Dockerfile.api — simplified
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir build && python -m build

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/dist/*.whl .
RUN pip install --no-cache-dir *.whl
USER 1000
CMD ["openscience", "start", "--host", "0.0.0.0"]
```

---

## Production Deployment

### Behind nginx (recommended)

```nginx
server {
    listen 80;
    server_name openscience.example.edu;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_read_timeout 300s;   # long-running analyses
    }
}
```

Add TLS with certbot:

```bash
sudo certbot --nginx -d openscience.example.edu
```

### Docker Swarm

```bash
docker swarm init
docker stack deploy -c docker-compose.prod.yml openscience
```

### Kubernetes

Helm chart skeleton:

```bash
helm install openscience ./charts/openscience \
  --set api.replicas=3 \
  --set worker.replicas=5 \
  --set postgres.persistence.size=100Gi
```

### Health checks

The API exposes:

```bash
curl http://localhost:8080/api/health
# {"status": "healthy", "version": "0.1.0"}
```

Compose's health check:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## Monitoring

### Logs

```bash
docker-compose logs -f
docker-compose logs -f --tail 100 api worker
```

### Metrics (Prometheus)

Enable in `.env`:

```ini
METRICS_ENABLED=true
METRICS_PORT=9090
```

Scrape config:

```yaml
scrape_configs:
  - job_name: openscience
    static_configs:
      - targets: ['api:9090', 'worker:9090']
```

---

## Troubleshooting

### Containers fail to start

```bash
docker-compose ps                 # which service is down?
docker-compose logs <service>     # check its logs
```

### "Port already in use"

```bash
# Find what's holding the port
lsof -i :8080

# Either kill it or change the port in docker-compose.yml
```

### "Cannot connect to Docker daemon"

```bash
# macOS: start Docker Desktop
open -a Docker

# Linux: start the service
sudo systemctl start docker
```

### Out of disk space

```bash
docker system df
docker system prune -a --volumes   # ⚠️ destructive
```

### Slow first build

The base images are ~2 GB. Subsequent builds use the layer cache. To speed up further:

```bash
DOCKER_BUILDKIT=1 docker-compose build
```

### Database connection refused

Postgres isn't ready yet. The API already retries; wait 10–20 s. If it persists:

```bash
docker-compose exec postgres pg_isready -U openscience
```

### Worker not processing tasks

```bash
docker-compose logs -f worker
docker-compose exec worker celery -A openscience inspect active
```

---

## Production Checklist

- [ ] Changed default `POSTGRES_PASSWORD`
- [ ] TLS termination at reverse proxy
- [ ] `SANDBOX_ENABLED=true`
- [ ] Resource limits set
- [ ] Regular backups configured
- [ ] Log rotation enabled
- [ ] Secrets in a vault, not `.env` on disk
- [ ] Monitoring and alerting wired up

---

## See Also

- [Getting Started](getting-started.md) — first-time setup
- [Configuration](configuration.md) — environment variables
- [Security](security.md) — hardening guidance
- [Troubleshooting](troubleshooting.md) — common issues
