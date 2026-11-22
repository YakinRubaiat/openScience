# Troubleshooting

Common problems and how to fix them.

## Docker

### "port is already allocated"

Another process is using 8080, 8000, 5432, 6379, or 5555.

```bash
# Find what is using the port
lsof -i :8080

# Stop the process, or change the published port in docker-compose.yml:
ports:
  - "8081:8080"
```

### Services unhealthy or restarting

```bash
docker-compose ps
docker-compose logs api
docker-compose logs db
```

The API waits for PostgreSQL; if `db` failed (bad `DB_PASSWORD`, corrupted
volume), fix the root cause and recreate:

```bash
docker-compose down
docker-compose up -d
```

### Database won't initialize / authentication failed

The database password is baked into the `postgres-data` volume on first run.
If you changed `DB_PASSWORD` after the first `up`, reset the volume
(**deletes all data**):

```bash
docker-compose down -v
docker-compose up -d
```

### Changes to code not reflected

Containers run baked images:

```bash
docker-compose up -d --build
```

## Python / Local Install

### `openscience: command not found`

The virtual environment is not activated or the package wasn't installed:

```bash
source venv/bin/activate
pip install -e ".[dev]"
openscience --version
```

### `ModuleNotFoundError` after install

Install the optional extras you need:

```bash
pip install -e ".[bio]"   # scanpy, biopython, ...
pip install -e ".[all]"
```

### Python version too old

openScience requires Python 3.10+. Check with `python3 --version`. On macOS
use Homebrew (`brew install python@3.12`); on Ubuntu use a newer package or
pyenv.

## Docs

### `mkdocs serve` — port 8000 already in use

Port 8000 belongs to the REST API. Bind the docs server elsewhere:

```bash
cd docs
mkdocs serve --dev-addr 127.0.0.1:8001
```

### mkdocs: "Config value 'nav': ... file not found"

Every page listed in `mkdocs.yml`'s `nav` must exist under `docs/`. Create
the missing file or remove the nav entry.

## API

### Health check fails

```bash
curl http://localhost:8000/api/v1/health
docker-compose logs api
```

Most commonly the database is unreachable (`DB_USER`/`DB_PASSWORD` mismatch)
or migrations haven't run (`openscience init-db` in a local install).

### Task stuck in `awaiting_approval`

This is the human-approval broker working as designed — a privileged action
needs approval:

```bash
curl http://localhost:8000/api/v1/approvals
curl -X POST http://localhost:8000/api/v1/approvals/<id>/approve
```

See [Security](security.md).

## Tests

### pytest collects no tests

Ensure you're in the repo root with the test extra installed:

```bash
pip install -e ".[test]"
pytest tests/ -v
```

## Still stuck?

- Search existing [GitHub issues](https://github.com/YakinRubaiat/openScience/issues)
- Check the [FAQ](faq.md)
- Open a new issue with `docker-compose logs` output and your
  OS/Python/Docker versions
