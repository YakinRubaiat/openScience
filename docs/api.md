---
layout: default
title: API Reference
nav_order: 5
description: "Python API, REST API, and CLI reference for openScience"
---

# API Reference

openScience provides three equivalent interfaces:

- **[Python API](#python-api)** — programmatic access for notebooks and scripts
- **[REST API](#rest-api)** — HTTP endpoints for web apps and integrations
- **[CLI](#cli-reference)** — command-line tool for terminals and schedulers

All three call the same core framework; results are identical regardless of interface.

---

## Python API

### `ScienceSession`

Main entry point. Maintains state across analysis steps.

```python
from openscience import ScienceSession

session = ScienceSession(
    project_dir=".",               # Optional[Union[str, Path]] = None
    compute_backend="local",       # "local" | "slurm" | "ssh" | "kubernetes"
    sandbox_enabled=True,          # bool
    **kwargs                       # additional config
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_dir` | `str \| Path \| None` | `Path.cwd()` | Root for all relative paths |
| `compute_backend` | `str` | `"local"` | Default compute target |
| `sandbox_enabled` | `bool` | `True` | OS-level sandboxing |

---

### `session.load_data()`

Load a dataset into the session.

```python
session.load_data(
    file_path="data/raw/pbmc_10k.h5ad",
    format="auto",
    name=None,
    **kwargs,
)
```

| Parameter | Description |
|-----------|-------------|
| `file_path` | Path to the data file |
| `format` | `"auto"`, `"anndata"`, `"csv"`, `"fastq"`, `"bam"`, `"tiff"`, … |
| `name` | Dataset key (defaults to filename without extension) |
| `**kwargs` | Format-specific options (e.g. `sep="\t"` for CSV) |

Returns `self` for chaining:

```python
session.load_data("a.h5ad").load_data("b.csv", sep="\t")
```

---

### `session.analyze()`

Run an analysis task.

```python
result = session.analyze(
    task="QC filtering and clustering",
    specialist=None,
    data_name=None,
    **parameters,
)
```

| Parameter | Description |
|-----------|-------------|
| `task` | Natural-language description |
| `specialist` | Agent name; if `None`, the orchestrator auto-routes |
| `data_name` | Key of dataset to use (defaults to most recently loaded) |
| `**parameters` | Agent-specific options |

Every result is stored in `session._results[task]`.

```python
result = session.analyze(
    "QC filtering and clustering",
    specialist="scanpy_specialist",
    min_genes=200,
    resolution=0.5,
)
```

---

### `session.visualize()`

Generate a figure from analysis results.

```python
figure = session.visualize(
    result,
    type="auto",
    style="publication",
    output=None,
    **kwargs,
)
```

| Parameter | Options |
|-----------|---------|
| `type` | `"umap"`, `"volcano"`, `"heatmap"`, `"boxplot"`, `"forest"`, … |
| `style` | `"publication"`, `"presentation"`, `"interactive"` |
| `output` | File path; format inferred from extension (`.pdf`, `.png`, `.svg`) |

```python
session.visualize(result, type="umap", output="figures/umap.pdf", color="leiden")
```

---

### `session.write_methods()`

Generate a methods section.

```python
methods = session.write_methods(
    result,
    style="nature",            # "nature" | "science" | "cell" | "plos"
    citation_format="apa",     # "apa" | "vancouver" | "harvard"
    **kwargs,
)
```

The generated text includes tool versions and parameters from the provenance graph.

---

### `session.ask()`

Ask a natural-language question about loaded data or results.

```python
answer = session.ask("How many clusters were found and what is the median gene count?")
```

---

### `session.save()` / `ScienceSession.load()`

Persist and restore session state.

```python
session.save("checkpoint.pkl")
restored = ScienceSession.load("checkpoint.pkl")
```

---

### `BaseAgent`

Subclass to create custom agents. See [Contributing](contributing.md#adding-a-new-agent).

```python
from openscience.core.agent import BaseAgent, AgentMetadata

class MyAgent(BaseAgent):
    metadata = AgentMetadata(
        name="my_agent",
        category="analysis",
        description="A short description",
        required_skills=["scanpy"],
        input_types=["anndata"],
        output_types=["results"],
    )

    async def execute(self, task, context):
        out = await self.run_skill("scanpy", "qc", data=context["data"])
        return self.format_result(out)
```

---

## REST API

The REST API runs at `http://localhost:8080` when started with `openscience start` or `docker-compose up`.

### Authentication

Currently the API trusts localhost. For remote deployment, put a reverse proxy (nginx + auth) in front. See [Security](security.md).

### Endpoints

#### `GET /api/agents`

List all registered agents.

```bash
curl http://localhost:8080/api/agents
```

```json
{
  "agents": [
    {
      "name": "scanpy_specialist",
      "category": "analysis",
      "description": "Single-cell analysis (Scanpy)"
    }
  ]
}
```

---

#### `POST /api/session/load`

Load data into the session.

```bash
curl -X POST http://localhost:8080/api/session/load \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "data/raw/pbmc_10k.h5ad",
    "format": "anndata"
  }'
```

Response:

```json
{ "status": "success" }
```

| Field | Type | Required |
|-------|------|:-----:|
| `file_path` | string | ✅ |
| `format` | string | — (default `"auto"`) |

---

#### `POST /api/session/analyze`

Execute an analysis task.

```bash
curl -X POST http://localhost:8080/api/session/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "task": "QC and clustering",
    "specialist": "scanpy_specialist"
  }'
```

Response:

```json
{
  "status": "success",
  "result": "{…serialized result object…}"
}
```

| Field | Type | Required |
|-------|------|:-----:|
| `task` | string | ✅ |
| `specialist` | string | — |
| `parameters` | object | — |

Error response (HTTP 400):

```json
{ "status": "error", "message": "Agent not found: foo" }
```

---

#### Error Codes

| Code | Meaning | Common cause |
|-----:|---------|--------------|
| 400 | Bad request | Missing/invalid fields |
| 404 | Not found | Unknown endpoint |
| 500 | Server error | Agent execution failure; check server logs |

---

#### Artifacts

Every analysis result and figure is stored as an **artifact** with a full
provenance graph: the code, data versions, parameters, and agent chain that
produced it.

##### `GET /api/artifacts/{id}`

Download an artifact file.

```bash
curl -O http://localhost:8080/api/artifacts/art_umap_pdf
```

##### `GET /api/artifacts/{id}/provenance`

Fetch the provenance graph for an artifact.

```bash
curl http://localhost:8080/api/artifacts/art_umap_pdf/provenance
```

```json
{
  "artifact": "art_umap_pdf",
  "code": "scanpy.tl.umap(...)",
  "parameters": {"resolution": 0.5},
  "inputs": ["pbmc_10k.h5ad"],
  "agent_chain": ["qc_analyzer", "scanpy_specialist"]
}
```

---

## CLI Reference

Installed as `openscience` via pip.

```bash
openscience --help
openscience --version
```

### `openscience init`

Initialize a project directory.

```bash
openscience init [--project-dir .] [--compute local]
```

Creates `openscience.yaml` and standard subdirectories (`data/`, `results/`, …).

### `openscience start`

Start the daemon.

```bash
openscience start [--host 127.0.0.1] [--port 8080] [--daemon]
```

### `openscience ui`

Open the web UI in the browser.

```bash
openscience ui [--no-browser]
```

### `openscience agents`

List all agents, grouped by category.

```bash
openscience agents
```

Output:

```text
🤖 Available Agents
==================================================

📁 ANALYSIS (20 agents)
--------------------------------------------------
  • atac_seq_analyzer         ATAC-seq analysis
  • chip_seq_analyzer         ChIP-seq peak calling
  • ...

✅ Total: 100 agents
```

### `openscience config`

Show the current project configuration.

```bash
openscience config
```

### `openscience credentials` *(planned)*

Manage encrypted credentials.

```bash
openscience credentials set <key> <value>
openscience credentials get <key>
openscience credentials list
openscience credentials delete <key>
```

---

## Async Usage

All agent and skill methods are `asyncio`-native. For custom pipelines:

```python
import asyncio
from openscience.agents.analysis.scanpy_specialist import ScanpySpecialist

async def main():
    agent = ScanpySpecialist(orchestrator=None)
    result = await agent.execute(task, context)

asyncio.run(main())
```

The synchronous `ScienceSession` API wraps async internals for convenience.

---

## Type Conventions

- **Paths** accept `str` or `pathlib.Path` — `Path` is canonical internally
- **Datasets** are keyed by string names inside a session
- **Results** are `dict`-like with `data`, `metadata`, and `agent` keys

---

## See Also

- [Quickstart](quickstart.md) — hands-on tutorial
- [Architecture](architecture.md) — internals
- [Agent Catalog](agents.md) — every agent and its skills
- [Troubleshooting](troubleshooting.md) — common API errors
