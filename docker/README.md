# openScience Docker Infrastructure

This directory contains the complete Docker infrastructure for running openScience in development, testing, and production environments.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Docker Files](#docker-files)
- [Environment Setup](#environment-setup)
- [Development Environment](#development-environment)
- [Testing Environment](#testing-environment)
- [Production Environment](#production-environment)
- [Monitoring and Logging](#monitoring-and-logging)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The openScience Docker infrastructure includes:

- **API Server**: Flask-based REST API
- **Web UI**: React-based user interface served by Nginx
- **Background Workers**: Celery workers for async task processing
- **PostgreSQL**: Primary database
- **Redis**: Task queue and caching
- **Nginx**: Reverse proxy and load balancer (production)
- **Prometheus**: Metrics collection (production)
- **Flower**: Celery monitoring (optional)

## 📦 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB of available RAM
- 10GB of disk space

### macOS/Windows

Install [Docker Desktop](https://www.docker.com/products/docker-desktop)

### Linux

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🚀 Quick Start

### Development Environment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Access Services

- **Web UI**: http://localhost:3000
- **API**: http://localhost:5000
- **API Health Check**: http://localhost:5000/health
- **Flower (Celery Monitor)**: http://localhost:5555

## 📁 Docker Files

### Dockerfiles

| File | Description |
|------|-------------|
| `Dockerfile.api` | Production-ready API server with Gunicorn |
| `Dockerfile.ui` | Multi-stage build for React UI with Nginx |
| `Dockerfile.worker` | Celery worker for background tasks |
| `Dockerfile.test` | Testing environment with Pytest |

### Docker Compose Files

| File | Description |
|------|-------------|
| `docker-compose.yml` | Development environment |
| `docker-compose.prod.yml` | Production environment |
| `docker-compose.test.yml` | Testing environment |

### Configuration Files

| File | Description |
|------|-------------|
| `nginx-ui.conf` | Nginx config for UI service |
| `nginx-prod.conf` | Nginx config for production reverse proxy |
| `init-db.sql` | Database initialization script |
| `prometheus.yml` | Prometheus monitoring config |
| `.dockerignore` | Files to exclude from Docker builds |
| `.env.example` | Example environment variables |

## 🔧 Environment Setup

### 1. Copy Environment File

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` and update the following:

```bash
# Database
DB_USER=openscience
DB_PASSWORD=your-secure-password
DB_NAME=openscience

# Redis
REDIS_PASSWORD=your-redis-password

# Security
SECRET_KEY=generate-a-random-secret-key

# Monitoring
SENTRY_DSN=your-sentry-dsn  # Optional
```

### 3. Generate SSL Certificates (Production)

For production with HTTPS:

```bash
# Create SSL directory
mkdir -p docker/ssl

# Generate self-signed certificate (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/ssl/key.pem \
  -out docker/ssl/cert.pem

# For production, use Let's Encrypt or your certificate authority
```

## 💻 Development Environment

### Start Services

```bash
# Build and start all services
docker-compose up --build

# Start in detached mode
docker-compose up -d

# Start specific services
docker-compose up api ui db redis
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
```

### Execute Commands

```bash
# Access API container
docker-compose exec api bash

# Access database
docker-compose exec db psql -U openscience -d openscience

# Access Redis
docker-compose exec redis redis-cli

# Run Python shell
docker-compose exec api python
```

### Database Operations

```bash
# Create migration
docker-compose exec api flask db migrate

# Apply migrations
docker-compose exec api flask db upgrade

# Reset database
docker-compose down -v
docker-compose up -d db
```

## 🧪 Testing Environment

### Run Tests

```bash
# Run all tests
docker-compose -f docker-compose.test.yml run --rm test

# Run specific test file
docker-compose -f docker-compose.test.yml run --rm test pytest tests/test_server.py

# Run with coverage
docker-compose -f docker-compose.test.yml run --rm test pytest --cov

# Run linting
docker-compose -f docker-compose.test.yml run --rm lint
```

### View Test Results

Test results and coverage reports are stored in the `test-results` volume:

```bash
# Copy results from container
docker-compose -f docker-compose.test.yml run --rm test \
  cp -r /app/results ./test-results

# View coverage report
open test-results/coverage/index.html
```

## 🏭 Production Environment

### Prerequisites

1. **Set strong passwords** in `.env`
2. **Generate SSL certificates**
3. **Configure domain name**
4. **Set up firewall rules**

### Deploy

```bash
# Build and start production services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=5
```

### Enable Monitoring

```bash
# Start with Prometheus
docker-compose -f docker-compose.prod.yml up -d prometheus

# Access Prometheus
open http://localhost:9090
```

### Backup Database

```bash
# Backup
docker-compose -f docker-compose.prod.yml exec db \
  pg_dump -U openscience openscience > backup.sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T db \
  psql -U openscience openscience < backup.sql
```

## 📊 Monitoring and Logging

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f api

# Production logs
docker-compose -f docker-compose.prod.yml logs -f

# Access log files
docker-compose exec api tail -f /var/log/openscience/api.log
```

### Metrics

- **Prometheus**: http://localhost:9090
- **Flower (Celery)**: http://localhost:5555

### Health Checks

```bash
# API health
curl http://localhost:5000/health

# Check all services
docker-compose ps

# Check service health
docker-compose ps --format json | jq .
```

## 🔒 Security Considerations

### Development

- ⚠️ Default passwords are used - **change them**
- ⚠️ Debug mode is enabled - **disable in production**
- ⚠️ No SSL/TLS - **use HTTPS in production**

### Production

1. **Change all default passwords**
2. **Use strong SECRET_KEY** (generate with `openssl rand -hex 32`)
3. **Enable SSL/TLS** with valid certificates
4. **Configure firewall** to restrict access
5. **Use secrets management** (Docker Secrets, Vault, etc.)
6. **Enable rate limiting** (already configured)
7. **Keep images updated**: `docker-compose pull`
8. **Run as non-root** (already configured)
9. **Scan images** for vulnerabilities:
   ```bash
   docker scan openscience-api
   ```

### Secrets Management

For production, use Docker Secrets:

```yaml
# docker-compose.prod.yml
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  api:
    secrets:
      - db_password
```

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs

# Rebuild images
docker-compose build --no-cache

# Remove volumes and restart
docker-compose down -v
docker-compose up --build
```

### Database Connection Issues

```bash
# Check database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Test connection
docker-compose exec db pg_isready

# Access database
docker-compose exec db psql -U openscience -d openscience
```

### Worker Not Processing Tasks

```bash
# Check worker logs
docker-compose logs worker

# Check Redis connection
docker-compose exec redis redis-cli ping

# Restart workers
docker-compose restart worker

# Inspect Celery
docker-compose exec worker celery -A openscience.workers.tasks inspect active
```

### Port Conflicts

```bash
# Check what's using a port
lsof -i :5000

# Change port in docker-compose.yml
ports:
  - "5001:5000"  # Use 5001 instead of 5000
```

### Out of Memory

```bash
# Check Docker resources
docker stats

# Increase Docker memory (macOS/Windows)
# Docker Desktop > Preferences > Resources

# Limit container memory
deploy:
  resources:
    limits:
      memory: 2G
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)

## 🤝 Contributing

When modifying Docker infrastructure:

1. Test changes in development first
2. Update this README if adding new services
3. Run security scan: `docker scan <image>`
4. Test production build: `docker-compose -f docker-compose.prod.yml build`
5. Update `.env.example` if adding new variables

## 📝 License

See the main project LICENSE file.
