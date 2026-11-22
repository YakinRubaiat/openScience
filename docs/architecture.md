# Architecture

openScience is a layered system that routes scientific questions to a catalog
of 100 specialist agents, each grounded by curated skills and database
connectors, inside a deny-by-default security sandbox.

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    openScience Web UI                        │
│                  (React + Flask Backend)                     │
├─────────────────────────────────────────────────────────────┤
│                   Agent Orchestrator                         │
│         Task routing, planning, and delegation              │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ Literature │ │ Experiment │ │    Data    │              │
│  │   Review   │ │  Planning  │ │ Management │              │
│  │  Agents    │ │   Agents   │ │   Agents   │              │
│  └────────────┘ └────────────┘ └────────────┘              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │    Data    │ │   Figure   │ │ Scientific │              │
│  │  Analysis  │ │ Generation │ │  Writing   │              │
│  │   Agents   │ │   Agents   │ │   Agents   │              │
│  └────────────┘ └────────────┘ └────────────┘              │
├─────────────────────────────────────────────────────────────┤
│                    Skill Registry                            │
│         150+ tools: BLAST, Seurat, PyMOL, etc.             │
├─────────────────────────────────────────────────────────────┤
│                  Connector Framework                         │
│    60+ databases: PubMed, PDB, ChEMBL, GEO, etc.           │
├─────────────────────────────────────────────────────────────┤
│                  OS-Level Sandbox                            │
│     Deny-by-default network, file system guards             │
├─────────────────────────────────────────────────────────────┤
│               Compute Backend Router                         │
│   Local │ SSH │ SLURM │ Cloud GPU │ Kubernetes             │
└─────────────────────────────────────────────────────────────┘
```

## Layers

### 1. Interfaces

- **Web UI** — React front end served by nginx, talking to the Flask REST API.
- **REST API** (`openscience.server`) — sessions, tasks, artifacts, and agent
  status. See the [API Reference](api.md).
- **CLI** (`openscience` entry point) — local session management, database
  initialization, and pipeline export.

### 2. Agent Orchestrator

The `AgentOrchestrator` receives a natural-language task, plans the workflow,
selects the right specialist agent(s), and mediates every skill invocation,
network call, and file write.

```python
from openscience import AgentOrchestrator

orchestrator = AgentOrchestrator()
plan = orchestrator.plan("Differential expression of treated vs control")
```

### 3. Specialist Agents

100 agents in six categories — Literature Review (15), Experiment Planning
(15), Data Management (15), Data Analysis (20), Figure Generation (15), and
Scientific Writing (20). The full catalog with inputs and outputs is in the
[Agent Catalog](agents.md).

### 4. Skill Registry

~150 curated tools (BLAST, DESeq2, Seurat, Scanpy, AlphaFold2, GROMACS, RDKit,
PyMOL, …) exposed to agents through a uniform, typed interface. Each skill
declares its resource needs so the compute router can place it correctly.

### 5. Connector Framework

60+ database connectors (PubMed, bioRxiv, AlphaFold DB, PDB, ChEMBL, GEO,
SRA, …) with shared auth, rate-limiting, and caching. Connector credentials
live in the local keyring — never in source.

### 6. OS-Level Sandbox

Deny-by-default network egress, file-system guards, and a human-approval
broker that gates code execution, outbound network access, and deletions.
Details in the [Security](security.md) document.

### 7. Compute Backend Router

Dispatches work to local processes, SSH hosts, SLURM clusters, cloud GPUs,
or Kubernetes, based on each skill's declared resource profile. Per-specialist
Conda environments keep dependencies isolated.

## Deployment Topology (Docker Compose)

The reference deployment (`docker-compose.yml`) runs:

- **api** — REST API container
- **ui** — web UI behind nginx
- **worker** — Celery worker executing long-running analyses
- **db** — PostgreSQL for sessions and artifacts
- **redis** — task queue broker and cache
- **flower** — worker monitoring

Production and test variants live in `docker-compose.prod.yml` and
`docker-compose.test.yml`; see the [Docker Guide](docker.md).

## Data Flow

1. A user submits a task through the UI, CLI, or REST API.
2. The orchestrator plans the workflow and selects agents.
3. Agents invoke skills; each invocation passes through the sandbox's
   approval broker.
4. Connectors fetch external data; results are cached in Redis and persisted
   in PostgreSQL.
5. Every artifact records full provenance: code, data, parameters, and the
   agent chain that produced it.
