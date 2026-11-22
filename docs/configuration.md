---
layout: default
title: Configuration
nav_order: 6
description: "Complete guide to openScience configuration"
---

# Configuration Guide

openScience is highly configurable. This guide covers every knob, from API keys to compute backends and security policies.

---

## 📁 Configuration Files

| File | Purpose | Location | Committed to git? |
|------|---------|----------|-------------------|
| `openscience.yaml` | Project settings | Project root | ✅ Yes |
| `.env` | Secrets, API keys | Project root | ❌ No (in `.gitignore`) |
| `~/.openscience/config.yaml` | Global user defaults | Home directory | N/A |
| `~/.openscience/credentials` | Encrypted keyring | Home directory | N/A |

**Precedence** (highest wins):

```
Project openscience.yaml  >  Environment variables  >  Global config  >  Built-in defaults
```

---

## 🔑 API Keys & Credentials

### `.env` file

Store secrets in `.env`, never in source code:

```ini
# --- LLM providers (pick one or both) ---
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# --- Literature databases ---
NCBI_API_KEY=your-ncbi-key
SEMANTIC_SCHOLAR_API_KEY=your-ss-key

# --- Cloud (for remote compute) ---
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-key.json

# --- Misc ---
UNPAYWALL_EMAIL=you@institution.edu
```

Load in Python:

```python
from dotenv import load_dotenv
load_dotenv()   # reads .env into os.environ
```

The `openscience` CLI auto-loads `.env` from the current directory.

### Encrypted credentials

For long-lived deployments, prefer the system keyring:

```bash
openscience credentials set openai_api_key sk-your-key
openscience credentials get openai_api_key
openscience credentials list
openscience credentials delete openai_api_key
```

Storage backends:

| OS | Backend |
|----|---------|
| macOS | Keychain |
| Linux | Secret Service (GNOME Keyring, KWallet) |
| Windows | Credential Locker |

---

## ⚙️ Project Configuration (`openscience.yaml`)

A full annotated example:

```yaml
# ═══════════════════════════════════════════════════════════
# openScience project configuration
# ═══════════════════════════════════════════════════════════

project:
  name: my-research
  description: "PBMC atlas construction"

# ── Compute ──────────────────────────────────────────────
compute:
  default: local            # local|slurm|ssh|kubernetes|cloud

  backends:
    local:
      max_workers: 4
    slurm:
      partition: main
      account: mylab
      time_limit: "24:00:00"
    ssh:
      host: cluster.university.edu
      user: researcher
      key_file: ~/.ssh/id_ed25519
    cloud:
      provider: aws
      region: us-east-1
      instance_type: p3.2xlarge

# ── Data locations ───────────────────────────────────────
data:
  raw_dir: data/raw           # treated as read-only
  processed_dir: data/processed
  cache_dir: .cache/openscience

# ── Outputs ──────────────────────────────────────────────
output:
  results_dir: results
  figures_dir: figures
  notebooks_dir: notebooks

# ── Sandbox (security) ───────────────────────────────────
sandbox:
  enabled: true
  network_policy: deny_all    # deny_all|allowlist|permissive
  allowed_hosts:
    - pubmed.ncbi.nlm.nih.gov
    - api.semanticscholar.org
  require_approval_for:
    - code_execution
    - file_deletion
    - network_egress

# ── LLM ──────────────────────────────────────────────────
llm:
  provider: openai            # openai|anthropic
  model: gpt-4-turbo
  temperature: 0.1
  max_tokens: 4096

# ── Agents ───────────────────────────────────────────────
agents:
  auto_route: true            # false → require explicit specialist
  confidence_threshold: 0.7
  parallel_workers: 4

# ── Connectors ───────────────────────────────────────────
connectors:
  pubmed:
    rate_limit: 10            # requests/second
    cache_ttl: 86400          # seconds
  geo:
    rate_limit: 5
    cache_ttl: 604800

# ── Logging ──────────────────────────────────────────────
logging:
  level: INFO                 # DEBUG|INFO|WARNING|ERROR
  file: logs/openscience.log
  rotation: 100MB
  retention_days: 30
```

Apply with the CLI:

```bash
openscience config          # show merged configuration
```

---

## 🖥️ Compute Backends

### Local (default)

Runs agents on the local machine.

```yaml
compute:
  default: local
  backends:
    local:
      max_workers: 4
```

### SLURM

Dispatch agents as SLURM jobs.

```yaml
compute:
  default: slurm
  backends:
    slurm:
      partition: gpu           # or cpu, bigmem, …
      account: mylab
      time_limit: "24:00:00"
      nodes: 1
      ntasks: 8
      mem: "32G"
```

The router automatically packages each agent call as an `sbatch` submission.

### SSH

Submit work to a remote server.

```yaml
compute:
  backends:
    ssh:
      host: workstation.lab.edu
      user: researcher
      key_file: ~/.ssh/id_ed25519
      remote_dir: /scratch/openscience
```

### Kubernetes

Schedule agents as pods.

```yaml
compute:
  backends:
    kubernetes:
      kubeconfig: ~/.kube/config
      namespace: openscience
      image: openscience/worker:latest
```

### Cloud GPU

For AlphaFold, deep learning, etc.

```yaml
compute:
  backends:
    cloud:
      provider: aws
      region: us-east-1
      instance_type: p3.2xlarge
      spot: true
```

---

## 🔐 Sandbox Policies

Three presets:

| Policy | Network | Filesystem | Use case |
|--------|---------|-----------|----------|
| `deny_all` | Blocked entirely | project dir only | Untrusted code |
| `allowlist` (default) | Listed hosts only | project + cache dirs | Most research |
| `permissive` | Open | Open | Local development |

Fine-tune:

```yaml
sandbox:
  network_policy: allowlist
  allowed_hosts:
    - pubmed.ncbi.nlm.nih.gov
    - eutils.ncbi.nlm.nih.gov
    - api.semanticscholar.org

  file_system:
    read:
      - data/raw
      - reference/
    write:
      - data/processed
      - results/
      - figures/
```

---

## 🤖 LLM Configuration

```yaml
llm:
  provider: openai          # or anthropic
  model: gpt-4-turbo
  temperature: 0.1          # lower → deterministic
  max_tokens: 4096
  timeout: 120              # seconds
  retries: 3
```

Use a local model:

```yaml
llm:
  provider: ollama
  model: llama3:70b
  base_url: http://localhost:11434
```

---

## 🔬 Agent Tuning

```yaml
agents:
  auto_route: true
  confidence_threshold: 0.7   # below → ask for clarification
  parallel_workers: 4

  # Per-agent overrides
  overrides:
    scanpy_specialist:
      n_jobs: 8
    gsea_analyzer:
      permutation_num: 1000
```

---

## 🌍 Connector Tuning

```yaml
connectors:
  pubmed:
    rate_limit: 10         # respect NCBI guidelines
    cache_ttl: 86400
  geo:
    rate_limit: 5
    cache_ttl: 604800
  enable_cache: true
  cache_backend: redis     # memory | redis | disk
```

---

## 📋 Logging

```yaml
logging:
  level: INFO
  file: logs/openscience.log
  rotation: 100MB
  retention_days: 30
  format: "%(asctime)s %(name)s %(levelname)s %(message)s"
```

View live logs:

```bash
# Local
tail -f logs/openscience.log

# Docker
docker-compose logs -f openscience-api
docker-compose logs -f openscience-worker
```

---

## 🧪 Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `NCBI_API_KEY` | — | NCBI E-utilities key |
| `COMPUTE_BACKEND` | `local` | Default compute |
| `SANDBOX_ENABLED` | `true` | Toggle sandbox |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `POSTGRES_HOST` | `postgres` | Docker database host |
| `POSTGRES_USER` | `openscience` | DB user |
| `POSTGRES_PASSWORD` | `openscience` | DB password |
| `POSTGRES_DB` | `openscience` | DB name |
| `REDIS_HOST` | `redis` | Cache host |
| `REDIS_PORT` | `6379` | Cache port |

Environment variables override `openscience.yaml`.

---

## 🛠️ Common Recipes

### Use OpenAI for routing, Anthropic for writing

```yaml
llm:
  router:
    provider: openai
    model: gpt-4-turbo
  writers:
    provider: anthropic
    model: claude-3-opus
```

### Run analysis on a GPU cluster, everything else locally

```yaml
compute:
  default: local
  task_routing:
    deep_learning_specialist: slurm
    3d_visualizer: local
```

### Sharing a project across a lab

Commit `openscience.yaml`, ignore `.env`, and document required keys in `README.md`:

```bash
# .gitignore
.env
*.pkl
.cache/
```

---

## ⚠️ Common Pitfalls

- 🔴 **Editing the wrong file** — `openscience config` shows the merged result of *all* config layers. Use it to diagnose.
- 🔴 **Committing `.env`** — secrets leak. Always check `.gitignore`.
- 🔴 **Setting rate limits too high** — your API key can be banned. Defaults are conservative for a reason.
- 🔴 **Forgetting the sandbox** — long-running pipelines sometimes need broader FS access; scope it narrowly with `read:`/`write:` lists rather than disabling.

---

## ➡️ See Also

- [Getting Started](getting-started.md)
- [Security](security.md)
- [Docker Deployment](docker.md)
