# Development

Set up a local development environment and run the test suite.

## Prerequisites

- macOS 13+ or Linux (Ubuntu 20.04+, RHEL 8+)
- Python 3.10+
- Docker (optional, for the full stack)
- 16 GB RAM, 50 GB free disk

## Setup

```bash
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience

python3 -m venv venv
source venv/bin/activate

# Editable install with dev and test extras
pip install -e ".[dev,test]"
```

## Project Layout

```
openScience/
├── src/openscience/      # Package source (setuptools src layout)
│   ├── core/             # ScienceSession, AgentOrchestrator
│   ├── agents/           # Specialist agent definitions
│   ├── cli.py            # `openscience` command
│   └── server.py         # REST API
├── tests/                # pytest suite
│   ├── core/
│   └── api/
├── docs/                 # This documentation (mkdocs)
├── docker/               # nginx/prometheus/sql configs
├── scripts/              # Helper scripts
├── alembic/              # Database migrations
├── ui/                   # Web UI source
├── docker-compose.yml    # Dev stack
├── pyproject.toml        # Packaging + tool config
└── mkdocs.yml            # Docs site config
```

## Running Tests

```bash
# Full suite
pytest

# With coverage
pytest --cov=openscience --cov-report=term-missing

# One file
pytest tests/core/test_agent.py -v

# Smoke test only
pytest tests/test_smoke.py
```

Or in Docker:

```bash
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Code Quality

The project uses black, ruff, mypy, and bandit (all configured in
`pyproject.toml`):

```bash
# Format
black src tests

# Lint
ruff check src tests

# Type-check (strict mode)
mypy src

# Security scan
bandit -c pyproject.toml -r src
```

Style rules: line length 100, target Python 3.10.

## Database Migrations

Schema changes are managed with Alembic:

```bash
# Create a migration after changing models
alembic revision --autogenerate -m "describe the change"

# Apply migrations
openscience init-db   # or: alembic upgrade head
```

## Building the Docs

```bash
pip install mkdocs

# Serve at http://127.0.0.1:8000 (use 8001 if the API is running)
cd docs
mkdocs serve --dev-addr 127.0.0.1:8001

# Build a static site into site/
mkdocs build
```

## Releasing

```bash
# Version bump happens via CI tags; build artifacts locally with:
python -m build
twine check dist/*
```

## CI

GitHub Actions workflows in `.github/workflows/` cover CI (`ci.yml`), Docker
builds (`docker.yml`), docs (`docs.yml`), releases (`release.yml`), and
security scanning (`security.yml`).

## Related

- [Contributing](contributing.md) — PR process and commit conventions
- [Architecture](architecture.md) — system design
- [Security](security.md) — security testing expectations
