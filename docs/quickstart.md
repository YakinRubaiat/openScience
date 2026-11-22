# Quickstart

Get openScience running in five minutes with Docker.

## 1. Clone and configure

```bash
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience
cp .env.example .env
```

Open `.env` and change the three default passwords
(`DB_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY`).

## 2. Start the stack

```bash
docker-compose up -d
```

This starts six services:

| Service | Port | Purpose |
|---------|------|---------|
| UI | 8080 | Web interface |
| API | 8000 | REST API |
| worker | — | Background task workers |
| db | 5432 | PostgreSQL database |
| redis | 6379 | Task queue and cache |
| flower | 5555 | Worker monitoring |

## 3. Verify

```bash
docker-compose ps
curl http://localhost:8000/api/v1/health
```

## 4. Open the UI

Navigate to <http://localhost:8080> and start a new analysis session.

## 5. Your first API call

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"task": "Quality control and clustering"}'
```

## 6. Stop everything

```bash
docker-compose down          # stop services
docker-compose down -v       # stop and delete data volumes
```

## Where next?

- [Getting Started](getting-started.md) — local installation, first analysis
- [Docker Guide](docker.md) — production deployment, testing compose files
- [Troubleshooting](troubleshooting.md) — common problems and fixes
- [FAQ](faq.md) — frequently asked questions
