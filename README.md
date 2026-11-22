# openScience

<div align="center">

**An Open-Source AI Workbench for Scientific Research**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Inspired by [Claude Science](https://claude.com/product/claude-science) — An open-source agentic research environment*

[🌐 GitHub Repository](https://github.com/YakinRubaiat/openScience) • [📚 Documentation](docs/index.md) • [🐳 Docker](docker/)

[Quick Start](docs/getting-started.md) • [Agent Catalog](docs/agents.md) • [API Reference](docs/api.md) • [Contributing](CONTRIBUTING.md)

</div>

---

## ⚡ Quick Start with Docker

The fastest way to get started with openScience:

```bash
# Clone the repository
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience

# Copy environment configuration
cp .env.example .env

# Start all services (dev environment)
./docker/quick-start.sh

# Or use docker-compose directly
docker-compose up -d

# Access the services
open http://localhost:3000    # Web UI
open http://localhost:5000    # API
open http://localhost:5555    # Celery monitoring
```

That's it! See [Docker Guide](docker/README.md) for details on development, testing, and production deployments.

### Manual Docker Commands

```bash
# Validate configuration
./docker/validate.sh

# Development
docker-compose up -d              # Start services
docker-compose logs -f            # View logs
docker-compose down               # Stop services

# Testing
docker-compose -f docker-compose.test.yml run --rm test

# Production
docker-compose -f docker-compose.prod.yml up -d

# Management utilities
./docker/docker-utils.sh help     # View all commands
```

---

## 🎯 What is openScience?

**openScience** is an open-source AI workbench that brings agentic AI capabilities to computational biology, chemistry, neuroscience, and ML research. It automates the toil between scientific questions and answers—handling database schemas, format conversions, and package interoperability—so researchers can focus on design decisions and interpretation.

### The Six Workflow Archetypes

| Workflow | Description | Agents |
|----------|-------------|--------|
| **📚 Literature Review** | Systematic search, summarization, synthesis | 15 agents |
| **🧪 Experiment Planning** | Protocol design, power analysis, optimization | 15 agents |
| **💾 Data Management** | Organization, validation, transformation | 15 agents |
| **📈 Data Analysis** | Statistical analysis, visualization, ML | 20 agents |
| **📊 Figure Generation** | Publication-quality figures | 15 agents |
| **✍️ Scientific Writing** | Drafting, editing, formatting | 20 agents |

**Total: 100 specialized agents**

---

## 🏗️ Architecture

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

---

## 🚀 Features

### 🧬 Domain Expertise
- **60+ Scientific Database Connectors**: PubMed, bioRxiv, AlphaFold DB, PDB, ChEMBL, GEO, SRA
- **150+ Curated Skills**: BLAST, DESeq2, Seurat, Scanpy, AlphaFold2, GROMACS, RDKit, PyMOL
- **Field-Specific Templates**: Genomics, proteomics, metabolomics, drug discovery

### 🔒 Security & Biosecurity
- **OS-Level Sandbox**: Deny-by-default network egress
- **Human-Approval Broker**: Gates code execution, network access, deletions
- **Biosecurity Safeguards**: Built-in dual-use review
- **Encrypted Credentials**: Local keyring storage

### 🚀 Flexible Compute
- **Local Execution**: Laptop, workstation, HPC login node
- **Remote Dispatch**: SLURM clusters, SSH hosts, cloud GPU
- **Environment Management**: Per-specialist Conda environments
- **Persistent Sessions**: Kernels and artifacts survive reboots

### 📊 Auditable Artifacts
- **Full Provenance**: Every result links to code, data, parameters
- **Versioned Outputs**: Track iterations of analyses
- **Reproducible Pipelines**: Export complete workflows

---

## 🐳 Docker Installation (Recommended)

### Quick Start

```bash
# Clone repository
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access web UI
open http://localhost:8080
```

### Services Included

| Service | Port | Description |
|---------|------|-------------|
| **openscience-ui** | 8080 | Web interface |
| **openscience-api** | 8000 | REST API |
| **openscience-worker** | - | Background workers |
| **postgres** | 5432 | Database |
| **redis** | 6379 | Task queue |

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service]

# Rebuild after changes
docker-compose up -d --build

# Run tests
docker-compose -f docker-compose.test.yml up

# Enter container
docker-compose exec openscience-api bash
```

See [Docker Guide](docs/docker.md) for complete documentation.

---

## 💻 Local Development

### Prerequisites

- **OS**: macOS 13+ or Linux (Ubuntu 20.04+, RHEL 8+)
- **Python**: 3.10 or higher
- **Memory**: 16GB RAM minimum
- **Storage**: 50GB free space

### Installation

```bash
# Clone repository
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your API keys and configuration

# Initialize database
openscience init-db

# Start development server
openscience start --dev
```

### Your First Analysis

```python
from openscience import ScienceSession

# Initialize session
session = ScienceSession()

# Load data
session.load_data("data/pbmc_10k.h5ad", format="anndata")

# Run analysis
result = session.analyze(
    task="Quality control and clustering",
    specialist="scanpy_specialist"
)

# Generate figure
figure = session.visualize(
    result,
    type="umap",
    output="figures/umap.pdf"
)

# Write methods
methods = session.write_methods(result)
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation and first steps |
| [Architecture](docs/architecture.md) | System design and components |
| [Agent Catalog](docs/agents.md) | All 100 agents documented |
| [API Reference](docs/api.md) | REST API documentation |
| [Docker Guide](docs/docker.md) | Docker deployment guide |
| [Configuration](docs/configuration.md) | Settings and options |
| [Security](docs/security.md) | Security policies and sandbox |
| [Contributing](CONTRIBUTING.md) | Contribution guidelines |

---

## 🤖 Agent Catalog

### Literature Review (15 agents)

| Agent | Description |
|-------|-------------|
| `pubmed_search` | PubMed/PMC systematic literature search |
| `biorxiv_monitor` | Preprint tracking and notifications |
| `semantic_scholar` | Citation network analysis |
| `systematic_review` | PRISMA-compliant review automation |
| `meta_analysis` | Meta-analysis and forest plots |
| [See all](docs/agents.md#literature-review) | ... |

### Experiment Planning (15 agents)

| Agent | Description |
|-------|-------------|
| `power_analysis` | Statistical power calculation |
| `experimental_design` | Factorial and response surface designs |
| `protocol_optimizer` | Experimental protocol optimization |
| `preregistration_writer` | Preregistration document drafting |
| [See all](docs/agents.md#experiment-planning) | ... |

### Data Management (15 agents)

| Agent | Description |
|-------|-------------|
| `data_ingestor` | Multi-format data import |
| `batch_corrector` | Batch effect correction |
| `data_integrator` | Multi-omics data integration |
| `provenance_tracker` | Complete data lineage tracking |
| [See all](docs/agents.md#data-management) | ... |

### Data Analysis (20 agents)

| Agent | Description |
|-------|-------------|
| `qc_analyzer` | Quality control metrics |
| `scanpy_specialist` | Single-cell analysis (Scanpy) |
| `deseq2_specialist` | Bulk RNA-seq differential expression |
| `proteomics_analyzer` | Mass spec proteomics |
| [See all](docs/agents.md#data-analysis) | ... |

### Figure Generation (15 agents)

| Agent | Description |
|-------|-------------|
| `publication_formatter` | Journal-specific formatting |
| `interactive_dashboard` | Web-based dashboard creation |
| `3d_visualizer` | 3D structure visualization |
| [See all](docs/agents.md#figure-generation) | ... |

### Scientific Writing (20 agents)

| Agent | Description |
|-------|-------------|
| `abstract_writer` | Abstract drafting and optimization |
| `methods_writer` | Methods section documentation |
| `grant_proposal_writer` | Grant proposal development |
| [See all](docs/agents.md#scientific-writing) | ... |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=openscience --cov-report=html

# Run specific tests
pytest tests/agents/
pytest tests/integration/

# Run in Docker
docker-compose -f docker-compose.test.yml up
```

---

## 🛠️ Development

### Project Structure

```
openScience/
├── docker/                 # Docker configuration
│   ├── Dockerfile.api
│   ├── Dockerfile.ui
│   └── Dockerfile.worker
├── docker-compose.yml      # Development compose
├── docker-compose.prod.yml # Production compose
├── src/openscience/        # Main source code
│   ├── agents/             # 100 specialized agents
│   ├── core/               # Core framework
│   ├── connectors/         # Database connectors
│   ├── skills/             # Scientific tools
│   └── api/                # REST API
├── tests/                  # Test suite
├── docs/                   # Documentation
└── scripts/                # Utility scripts
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/

# Type checking
mypy src/

# Pre-commit hooks
pre-commit install
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Adding a New Agent

```python
# src/openscience/agents/analysis/my_agent.py

from openscience.core.agent import BaseAgent, AgentMetadata

class MyAgent(BaseAgent):
    """Custom analysis agent."""
    
    metadata = AgentMetadata(
        name="my_agent",
        category="analysis",
        description="Description",
        required_skills=["tool1"],
        input_types=["anndata"],
        output_types=["figure"],
    )
    
    async def execute(self, task, context):
        result = await self.run_skill("tool1", context.data)
        return self.format_result(result)
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by [Claude Science](https://claude.com/product/claude-science) from Anthropic
- Built on the shoulders of giants: NumPy, SciPy, pandas, scikit-learn, Biopython, Scanpy, Seurat
- The scientific Python community

---

## 📖 Citation

```bibtex
@software{openscience2025,
  title = {openScience: An Open-Source AI Workbench for Scientific Research},
  author = {openScience Contributors},
  year = {2025},
  url = {https://github.com/YakinRubaiat/openScience},
  version = {0.1.0}
}
```

---

<div align="center">

**[Get Started](docs/getting-started.md)** • **[Docker Guide](docs/docker.md)** • **[Agent Catalog](docs/agents.md)**

🧬 **openScience** — Accelerating scientific discovery through open, agentic AI 🧬

</div>
