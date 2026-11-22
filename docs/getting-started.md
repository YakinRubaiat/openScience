---
layout: default
title: Getting Started
nav_order: 2
description: "Installation and setup guide for openScience"
---

# Getting Started

This guide walks you through installing openScience and setting up your first project. Choose the path that fits your environment:

- **[Docker](#option-1-docker-installation-recommended)** — fastest, all dependencies included
- **[Local Python](#option-2-local-python-installation)** — full control, best for development

---

## 📋 Prerequisites

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | macOS 13+, Ubuntu 20.04+, RHEL 8+ | Latest stable |
| **Python** | 3.10 | 3.12 |
| **RAM** | 16 GB | 32 GB |
| **Storage** | 50 GB free | 100+ GB SSD |
| **Docker** (if using Docker) | 20.10+ with Compose v2 | Latest stable |

> **Note for HPC users:** openScience can dispatch workload to SLURM clusters. See [Configuration](configuration.md#compute-backends).

---

## 🐳 Option 1: Docker Installation (Recommended)

Docker packages openScience with PostgreSQL, Redis, and all scientific dependencies.

### Step 1 — Clone the repository

```bash
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience
```

### Step 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```ini
# Required for LLM-driven features
OPENAI_API_KEY=sk-your-key-here
# or
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional but recommended
NCBI_API_KEY=your-ncbi-key
```

See [Configuration](configuration.md) for the full list of options. Defaults work out-of-the-box for local Docker use.

### Step 3 — Start services

```bash
docker-compose up -d
```

### Step 4 — Verify

```bash
# Check service status
docker-compose ps

# Expected output:
# openscience-ui       running   0.0.0.0:8080->3000/tcp
# openscience-api      running   0.0.0.0:8000->8080/tcp
# openscience-worker   running
# postgres             running   0.0.0.0:5432->5432/tcp
# redis                running   0.0.0.0:6379->6379/tcp
```

Open the web UI:

```bash
open http://localhost:8080
```

You should see the openScience dashboard listing all available agents.

### Step 5 — Next steps

Continue to the [5-Minute Quickstart](quickstart.md) to run your first analysis.

---

## 🐍 Option 2: Local Python Installation

### Step 1 — Clone and create environment

```bash
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### Step 2 — Install openScience

```bash
# Core install
pip install -e .

# With scientific extras (recommended)
pip install -e ".[all]"

# Or pick specific extras
pip install -e ".[bio]"    # Biopython, Scanpy, anndata, pysam
pip install -e ".[chem]"   # RDKit, OpenMM
pip install -e ".[ml]"     # PyTorch, TensorFlow, XGBoost
pip install -e ".[viz]"    # Dash, Bokeh, Altair
```

### Step 3 — Optional system dependencies

Some agents require external tools. Install them via conda for the smoothest experience:

```bash
# Create an analysis environment with common tools
conda create -n openscience-tools -c bioconda \
  blast deseq2 seurat gatk4 macs2 cellranger samtools
conda activate openscience-tools
```

Individual agent requirements are listed in the [Agent Catalog](agents.md).

### Step 4 — Initialize a project

```bash
mkdir my-research && cd my-research
openscience init
```

This creates:

```
my-research/
├── openscience.yaml      # Project configuration
├── data/
│   ├── raw/
│   └── processed/
├── results/
├── figures/
├── notebooks/
└── config/
```

### Step 5 — Set API keys

```bash
cp ../openScience/.env.example .env
# Edit .env with your keys
```

Or use encrypted storage:

```bash
openscience credentials set openai_api_key sk-your-key
```

### Step 6 — Start the server

```bash
openscience start --host 127.0.0.1 --port 8080
```

Open http://localhost:8080 in your browser.

---

## ✅ Verify the Installation

### Check the CLI

```bash
openscience --version
openscience agents   # Should list all 100 agents grouped by category
```

### Run a smoke test

```python
from openscience import ScienceSession

session = ScienceSession()
print("✅ openScience is working!")
print(f"📂 Project dir: {session.project_dir}")
print(f"⚙️  Compute backend: {session.compute_backend}")
```

### Run the test suite (local installs)

```bash
pytest tests/ -v
```

All tests should pass. If not, see [Troubleshooting](troubleshooting.md).

---

## 🔑 Setting Up API Keys

openScience uses LLMs and external databases. Keys you may want:

| Service | Why | Get a key |
|---------|-----|-----------|
| **OpenAI** or **Anthropic** | LLM-backed agents (summarization, writing) | [OpenAI](https://platform.openai.com/api-keys) / [Anthropic](https://console.anthropic.com/) |
| **NCBI** | Higher PubMed/SRA rate limits | [NCBI Account](https://www.ncbi.nlm.nih.gov/account/) |
| **Semantic Scholar** | Citation network analysis | [API](https://www.semanticscholar.org/product/api) |
| **Unpaywall** | Open-access full text | Just your email |

Store keys in `.env` (git-ignored) or in the system keyring with `openscience credentials set`.

---

## 🗂️ Project Layout After Init

After `openscience init`, your project looks like this:

```
my-research/
├── openscience.yaml     # Project settings (compute, dirs, sandbox)
├── .env                 # Secrets (never commit!)
├── data/
│   ├── raw/             # Original, immutable data
│   └── processed/       # Cleaned and transformed data
├── results/             # Analysis outputs (tables, models)
├── figures/             # Generated figures
├── notebooks/           # Jupyter notebooks
└── config/              # Additional config files
```

Best practice: keep `data/raw/` **read-only**. Agents write derived data to `data/processed/`.

---

## ⚙️ Compute Backend Quick Reference

By default, agents run locally. To use HPC or cloud resources:

| Backend | Best for | Quick setup |
|---------|----------|-------------|
| `local` | Laptop/workstation | Default — nothing to configure |
| `slurm` | HPC clusters | Set partition in `openscience.yaml` |
| `ssh` | Remote servers | Add host in `openscience.yaml` |
| `kubernetes` | Elastic cloud | Provide kubeconfig |
| `cloud-gpu` | Deep learning | Set provider + credentials |

Full details: [Configuration](configuration.md#compute-backends).

---

## 🚨 Common Setup Issues

| Symptom | Fix |
|---------|-----|
| `docker-compose: command not found` | Install Docker Desktop or `docker-compose-plugin` |
| Port 8080 already in use | Change the port in `docker-compose.yml` or pass `--port` to `openscience start` |
| `Permission denied` on Docker socket | Add your user to the `docker` group: `sudo usermod -aG docker $USER` (re-login) |
| ModuleNotFoundError after install | Re-activate the virtualenv and reinstall: `pip install -e ".[all]"` |
| API key errors | Check `.env` is loaded; verify keys with `openscience config` |

More in [Troubleshooting](troubleshooting.md).

---

## ➡️ Next Steps

- **[5-Minute Quickstart](quickstart.md)** — run your first analysis
- **[Configuration](configuration.md)** — customize compute, sandbox, and credentials
- **[Agent Catalog](agents.md)** — explore the 100 agents
- **[Tutorial Examples](examples/literature-review.md)** — complete workflows
