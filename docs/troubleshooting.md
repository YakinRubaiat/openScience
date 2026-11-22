---
layout: default
title: Troubleshooting
nav_order: 12
description: "Common issues and their solutions"
---

# Troubleshooting

Common problems and their solutions. If yours isn't listed, [open an issue](https://github.com/YakinRubaiat/openScience/issues) with the diagnostic output described below.

---

## 🩺 Diagnostics First

Before diving into specific issues, collect this info:

```bash
# Version info
openscience --version
python --version
docker --version

# Configuration (safe to share)
openscience config

# Recent logs
ls -la logs/
tail -100 logs/openscience.log
```

---

## 📦 Installation Issues

### `pip install` fails with compilation errors

**Symptoms**: `error: command 'gcc' failed` or missing header messages.

**Fix**:

```bash
# macOS
xcode-select --install

# Ubuntu/Debian
sudo apt-get install build-essential python3-dev

# RHEL/CentOS
sudo yum groupinstall "Development Tools"
```

For packages like `rdkit`, prefer conda:

```bash
conda install -c conda-forge rdkit
```

### `ModuleNotFoundError` after installation

Usually means the virtualenv isn't active or you installed into a different Python.

```bash
which python          # should point to venv
which openscience     # should also point to venv
pip install -e ".[all]"    # reinstall in the active venv
```

### `openscience: command not found`

The CLI entry point wasn't installed. This happens when installing from source without `-e`:

```bash
pip install -e .       # editable install (recommended for dev)
# or
pip install openscience
```

---

## 🐳 Docker Issues

### `docker-compose: command not found`

Docker Compose v2 is a plugin, not a standalone binary:

```bash
# Check plugin
docker compose version

# Use space instead of hyphen
docker compose up -d

# Install on Linux if plugin isn't available
sudo apt-get install docker-compose-plugin
```

### Port already in use

```bash
# Find the offender
lsof -i :8080

# Change the port
# Edit docker-compose.yml:
#   ports:
#     - "9090:3000"
```

### Containers exit immediately

```bash
docker-compose ps                    # see which service
docker-compose logs <service>        # read its output
```

Common causes: missing `.env`, invalid YAML, Postgres init error. Check the logs.

### "Cannot connect to Docker daemon"

```bash
# macOS: start Docker Desktop
open -a Docker

# Linux
sudo systemctl start docker
sudo usermod -aG docker $USER    # then re-login
```

### Image build is slow or fails

```bash
# Enable BuildKit (faster, better caching)
DOCKER_BUILDKIT=1 docker-compose build

# Clean rebuild
docker-compose build --no-cache

# Inspect disk usage
docker system df
docker system prune -a            # ⚠️ removes unused images
```

---

## 🧠 LLM Issues

### "Authentication failed" / 401 from OpenAI

Check the key:

```bash
echo $OPENAI_API_KEY | head -c 10       # starts with sk-
openscience config | grep -A3 llm
```

If you set it in `.env`, ensure that file is in the project root and `python-dotenv` is loading it.

### "Rate limit exceeded"

```yaml
# openscience.yaml
llm:
  max_retries: 5
  backoff_factor: 2
```

Or reduce parallel workers:

```yaml
agents:
  parallel_workers: 2
```

### "Model not found"

Your key may not have access to the requested model. Verify the model name in `openscience.yaml` matches what's available to your account (`gpt-4-turbo`, `gpt-3.5-turbo`, `claude-3-opus`, …).

### Responses are empty or weird

Lower `temperature` in `openscience.yaml`, and check for prompts overflowing the context window (`max_tokens`).

---

## 🧬 Agent Issues

### "Agent not found"

```bash
openscience agents        # check exact name
```

Names are `snake_case`. Common typos:

| Wrong | Right |
|-------|-------|
| `scanpy` | `scanpy_specialist` |
| `deseq2` | `deseq2_specialist` |
| `umap_visualizer` | `publication_formatter` (with `type="umap"`) |

### "Required skill not available"

Install the underlying tool. What's missing is printed in the error.

```bash
# Scanpy chain
pip install scanpy anndata

# DESeq2 chain (needs R)
conda install -c bioconda bioconductor-deseq2 rpy2

# Cell Ranger (external binary)
# Download from 10x Genomics
```

### Agent stalls without progress

```bash
# Check what it's doing
tail -f logs/openscience.log

# Increase verbosity temporarily
# openscience.yaml:
# logging:
#   level: DEBUG
```

Kill with Ctrl+C and try a smaller input first.

### `scanpy_specialist` runs out of memory

- Use a HPC backend for >100k cells
- Or downsample as a pre-step

```python
# Before analysis
subsampled = session.analyze(
    "Subsample to 50000 cells for initial exploration",
    specialist="scanpy_specialist",
)
```

---

## 📊 Data Issues

### "Format not recognized"

Specify explicitly:

```python
session.load_data("file.txt", format="csv", sep="\t")
```

Supported formats are listed per-agent in the [Agent Catalog](agents.md).

### h5ad file won't load

- Check AnnData version compatibility
- Older `AnnData` files sometimes need conversion:

```python
import anndata
adata = anndata.read_h5ad("old.h5ad")
adata.write_h5ad("converted.h5ad")
```

### Dates/timestamps in CSV are parsed as strings

Pass `parse_dates` through kwargs:

```python
session.load_data("data.csv", format="csv", parse_dates=["date_col"])
```

---

## 🌐 Connector Issues

### PubMed / NCBI rate-limits

Register for an [NCBI API key](https://www.ncbi.nlm.nih.gov/account/) and set `NCBI_API_KEY`. NCBI raises the limit from 3 to 10 req/sec with a key.

Then tune the connector:

```yaml
connectors:
  pubmed:
    rate_limit: 10
```

### Connector returns stale results

Cache TTL too long:

```yaml
connectors:
  pubmed:
    cache_ttl: 3600        # 1 hour instead of 24
```

Or flush the cache:

```bash
docker-compose exec redis redis-cli FLUSHDB
```

---

## 🖥️ Server Issues

### Flask won't start

```bash
# Port conflict?
lsof -i :8080

# Run with explicit host/port
openscience start --host 127.0.0.1 --port 9090
```

### "Connection refused" from the UI

The UI expects the API on the configured port. If you changed ports, update the UI config or use the same override in both services.

### CORS errors in browser console

For local development the server allows cross-origin requests from `localhost:*`. In production put the UI and API behind the same proxy origin.

---

## 🗄️ Database Issues

### Postgres refuses connections in Docker

Wait for readiness:

```bash
docker-compose exec postgres pg_isready -U openscience
```

If it stays unhealthy, check Postgres logs:

```bash
docker-compose logs postgres
```

Most common root cause: a `POSTGRES_PASSWORD` set after the volume was initialized. Recreate:

```bash
docker-compose down -v          # ⚠️ deletes data
docker-compose up -d
```

### Migrations fail

```bash
docker-compose exec api flask db upgrade
# or
openscience db migrate
```

---

## 💾 Session Issues

### "Cannot pickle" errors on `session.save()`

Some artifacts (open file handles, generators) can't be pickled. Close resources before saving, or store only paths.

```python
session.save("checkpoint.pkl")     # may fail on open handles
```

### Session restores but data is missing

`session.load()` restores paths, not file contents. If you deleted the underlying files, reload them.

---

## 🧪 Test Issues

### Tests fail with sandbox errors

The test suite mocks the sandbox in most cases. If you see real sandbox denials in tests:

```bash
SANDBOX_ENABLED=false pytest tests/
```

(For local dev only — CI always runs with the sandbox on.)

### Slow tests

```bash
pytest -m "not slow"        # skip marked-slow tests
pytest -n auto              # parallel (needs pytest-xdist)
```

---

## 🆘 Still Stuck?

1. Search [existing issues](https://github.com/YakinRubaiat/openScience/issues)
2. Check the [FAQ](faq.md)
3. Open a new issue with:
   - What you tried
   - Output of the diagnostics at the top of this page
   - Minimal reproduction script

---

## ➡️ See Also

- [Getting Started](getting-started.md)
- [Configuration](configuration.md)
- [FAQ](faq.md)
