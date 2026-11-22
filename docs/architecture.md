---
layout: default
title: Architecture
nav_order: 4
description: "openScience system architecture deep-dive"
---

# Architecture

This document explains how openScience's components interact to deliver agentic AI capabilities for scientific research.

---

## 📐 High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interfaces                        │
│         Web UI │ CLI │ Python API │ Jupyter Notebooks      │
├─────────────────────────────────────────────────────────────┤
│                       REST API                              │
│              Flask HTTP layer (port 8080)                   │
├─────────────────────────────────────────────────────────────┤
│                     Core Framework                          │
│    ScienceSession │ AgentOrchestrator │ Sandbox            │
├─────────────────────────────────────────────────────────────┤
│                        Agent Layer                          │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │Literature │ │Experiment │ │   Data    │ │   Data    │  │
│  │ Review 15 │ │Planning 15│ │Mgmt    15 │ │Analysis 20│  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│  ┌───────────┐ ┌───────────┐                               │
│  │  Figure   │ │Scientific │                               │
│  │ Gen    15 │ │Writing 20 │                               │
│  └───────────┘ └───────────┘                               │
├─────────────────────────────────────────────────────────────┤
│                      Skill Registry                         │
│        150+ scientific tools: BLAST, Seurat, PyMOL…        │
├─────────────────────────────────────────────────────────────┤
│                    Connector Framework                      │
│        60+ databases: PubMed, PDB, ChEMBL, GEO…            │
├─────────────────────────────────────────────────────────────┤
│                     OS-Level Sandbox                        │
│       Deny-by-default network & file system guards         │
├─────────────────────────────────────────────────────────────┤
│                 Compute Backend Router                      │
│        Local │ SSH │ SLURM │ Cloud GPU │ Kubernetes        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧱 Layer-by-Layer

### 1. User Interfaces

openScience meets users where they work:

| Interface | Purpose | Audience |
|-----------|---------|----------|
| **Python API** | Programmatic workflows, notebooks | Computational researchers |
| **CLI** | Shell scripting, HPC job files | Power users |
| **Web UI** | Interactive exploration, no code | Bench scientists |
| **REST API** | Integrations, pipelines | Developers |

All four surfaces call the same core framework — behavior is identical across interfaces.

### 2. REST API

A thin Flask layer (`openscience.server`) exposes:

- `GET /api/agents` — agent catalog with metadata
- `POST /api/session/load` — dataset loading
- `POST /api/session/analyze` — task execution
- (Additional endpoints in [API Reference](api.md))

The API layer is stateless apart from a session registry; long-running tasks are off-loaded to background workers.

### 3. Core Framework

Three classes form the heart of openScience:

#### `ScienceSession`

User-facing facade. Maintains state across steps: loaded datasets, results, artifacts.

```python
class ScienceSession:
    def __init__(self, project_dir, compute_backend="local",
                 sandbox_enabled=True, **kwargs): ...

    def load_data(self, file_path, format="auto", name=None): ...
    def analyze(self, task, specialist=None, **params): ...
    def visualize(self, result, type="auto", style="publication"): ...
    def write_methods(self, result, style="nature"): ...
    def ask(self, question): ...
    def save(self, path): ...
```

Design decisions:

- **Stateful** — datasets stay loaded between calls so agents can build on previous results.
- **Serializable** — `session.save()` pickles state; sessions survive kernel restarts.
- **Method chaining** — `load_data()` returns `self` for fluent pipelines.

#### `AgentOrchestrator`

The brain. Responsibilities:

1. **Task routing** — pick the right agent for a natural-language task
2. **Context assembly** — pass datasets, prior results, and config to agents
3. **Skill execution** — provide agents with tools from the Skill Registry
4. **Provenance logging** — record every call, parameter, version, and artifact

Routing algorithm (simplified):

```
def route(task_description):
    # 1. Explicit specialist requested? Use it.
    if specialist is not None:
        return agents[specialist]

    # 2. Embed the task and match against agent descriptions
    embedding = llm.embed(task_description)
    scores = cosine_sim(embedding, agent_description_embeddings)
    agent = argmax(scores)

    # 3. Confidence check — below threshold, ask for clarification
    if max(scores) < 0.7:
        raise AmbiguousTask(candidates=top_k(scores, k=3))

    return agent
```

#### `Sandbox`

OS-level enforcement of security policy. See [Security](security.md).

- **Network egress** — deny by default; allowlist for database connectors
- **File system** — read access to `data/raw/`; write access only to designated output dirs
- **Human-in-the-loop** — sensitive operations (deletions, external code exec) require approval

---

### 4. Agent Layer

100 specialized agents in six categories. Every agent subclasses `BaseAgent`:

```python
class BaseAgent(ABC):
    metadata: AgentMetadata  # name, category, description,
                             # required_skills, input_types, output_types

    @abstractmethod
    async def execute(self, task, context) -> Any: ...

    async def run_skill(self, skill_name, operation, **kwargs): ...

    def format_result(self, data, **metadata): ...
```

**Key invariants**:

- Agents declare their dependencies in `metadata.required_skills`. The orchestrator stalls execution if a required skill is missing.
- Agents never touch the network directly — all external access goes through **connectors**.
- All outputs are wrapped with metadata: `{agent, data, metadata}` for traceability.

#### Agent categories

| Category | Count | Focus |
|----------|:-----:|-------|
| Literature Review | 15 | Search → summarize → synthesize |
| Experiment Planning | 15 | Power, design, feasibility |
| Data Management | 15 | Import → validate → integrate |
| Data Analysis | 20 | QC → modeling → interpretation |
| Figure Generation | 15 | Publication-quality visuals |
| Scientific Writing | 20 | From abstract to grant proposals |

Full details: [Agent Catalog](agents.md).

---

### 5. Skill Registry

**Skills** are deterministic scientific tools — Scanpy, DESeq2, BLAST, PyMOL — wrapped in a uniform interface:

```python
class Skill(Protocol):
    name: str
    version: str
    async def execute(self, operation: str, **kwargs) -> Any: ...
```

Skills differ from agents:

| Aspect | Agent | Skill |
|--------|-------|-------|
| Intelligence | LLM-guided decisions | Deterministic algorithm |
| Example | `scanpy_specialist` | `scanpy` |
| Decides | *Why* and *which* parameters | *How* to run |

Agents compose skills; skills never call agents. This keeps the computational core auditable.

---

### 6. Connector Framework

**Connectors** handle external databases with:

- **Rate limiting** (per-source, configurable)
- **Caching** (TTL-based, in Redis)
- **Authentication** (via encrypted credentials)
- **Sandbox integration** (network allowlisting)

```python
class BaseConnector(ABC):
    metadata: ConnectorMetadata  # name, base_url, auth_type, rate_limit

    @abstractmethod
    async def search(self, query: str, **kwargs): ...
```

The sandbox grants each connector outbound access to exactly its own `base_url` — nothing else. A compromised agent cannot exfiltrate data.

---

### 7. Compute Backend Router

Tasks route to compute pools based on cost models and resource requirements:

```yaml
# openscience.yaml
compute:
  default: local
  backends:
    local:
      max_workers: 4
    slurm:
      partition: gpu
      account: mylab
    cloud:
      provider: aws
      instance_type: p3.2xlarge
```

The router chooses based on the **task signature**:

| Task | Typical backend |
|------|----------------|
| Literature search | Local (I/O-bound) |
| Single-cell clustering (10k cells) | Local (CPU) |
| Atlas-scale integration (1M cells) | SLURM or cloud |
| AlphaFold2 inference | Cloud GPU |
| Deep learning training | Kubernetes GPU pool |

Agents declare their resource class (`cpu_light`, `cpu_heavy`, `gpu_required`) in metadata; the router does the rest.

---

## 🔄 Data Flow: A Complete Example

Trace a request through the system:

```python
result = session.analyze(
    "QC and cluster this dataset",
    specialist="scanpy_specialist"
)
```

```
1. User code
       │
       ▼
2. ScienceSession.analyze()
   - builds context (data, prior results, config)
   - delegates to orchestrator
       │
       ▼
3. AgentOrchestrator.execute_task()
   - routes to scanpy_specialist
   - prepares task object
       │
       ▼
4. Sandbox.check()
   - verifies operation is allowed
   - opens required FS/network paths only
       │
       ▼
5. ScanpySpecialist.execute(task, context)
   - calls run_skill("scanpy", "qc", min_genes=200, ...)
   - calls run_skill("scanpy", "normalize", ...)
   - calls run_skill("scanpy", "cluster", resolution=0.5)
       │
       ▼
6. SkillRegistry.execute_skill()
   - spins up scanpy environment
   - runs operations inside sandbox
       │
       ▼
7. ProvenanceTracker
   - logs every call with params + versions
   - writes artifacts to results/
       │
       ▼
8. Result bubbles back up:
   Skill result → Agent result → Orchestrator result → Session
       │
       ▼
9. session._results["QC and cluster this dataset"] = result
```

At every arrow, the provenance system records inputs, outputs, timestamps, and tool versions.

---

## 🗄️ State and Persistence

```
ScienceSession
├── project_dir         # on disk
├── _data: Dict         # in memory (datasets)
├── _results: Dict      # in memory (analysis outputs)
└── _artifacts: List    # paths to files
    │
    │  session.save("checkpoint.pkl")
    ▼
    pickled state (data+results+artifacts)
    │
    │  ScienceSession.load("checkpoint.pkl")
    ▼
    restored session
```

For heavy datasets, the orchestrator stores **references** (paths) rather than full objects; the provenance graph records checksums.

---

## 🔒 Security by Design

| Threat | Mitigation |
|--------|-----------|
| Prompt injection via agent task | Sandbox denies unexpected egress |
| Data exfiltration | Per-connector network allowlists |
| Credential leakage | Keyring storage, never in code |
| Accidental deletions | Human approval broker |
| Dual-use research | Biosecurity screening layer |

Details: [Security Policies](security.md).

---

## 📈 Scalability

- **Vertical**: agents request CPU/RAM via metadata; backend router allocates
- **Horizontal**: tasks ship to SLURM/K8s workers
- **Caching**: connector layer caches API responses (Redis)
- **Async**: agents and skills are `asyncio`-native

---

## 🔭 Design Trade-offs

| Decision | Why | Alternative rejected |
|----------|-----|---------------------|
| Stateful `ScienceSession` | Iterative research workflows | Stateless API-only (loses context) |
| Agent + Skill split | Auditability of deterministic code | Pure LLM pipelines (opaque) |
| YAML config | Human-readable, diff-friendly | Database-only config |
| Flask REST API | Simple, well-understood | FastAPI (migration planned for v0.2) |
| Local-first | Privacy, works offline | Cloud-only |

---

## ➡️ Related Reading

- [Agent Catalog](agents.md) — what each agent does
- [API Reference](api.md) — calling conventions
- [Configuration](configuration.md) — knobs and switches
- [Security](security.md) — threat model and mitigations
