<div align="center">

# 🔬 openScience

**An Open-Source AI Workbench for Scientific Research**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-174%2B%20passing-brightgreen)](https://github.com/YakinRubaiat/openScience/actions)

*Inspired by [Claude Science](https://claude.com/product/claude-science) — An open-source agentic research environment*

</div>

---

## 🚀 Quick Start

```bash
# Clone and start with Docker (Recommended)
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience
docker-compose up -d

# Access Web UI
open http://localhost:8080

# Or run locally
pip install -e ".[all]"
openscience start
```

**Status**: ✅ Production Ready | ✅ Docker Working | ✅ API Tested | 🧪 Science Features In Development

---

## 🎯 What is openScience?

openScience is an agentic AI workbench that automates scientific workflows. Instead of just chatting with AI, you orchestrate **111 specialized agents** across six scientific domains:

| Workflow | Agents | What It Does |
|----------|--------|--------------|
| 📚 **Literature Review** | 15 agents | PubMed search, citation analysis, systematic reviews |
| 🧪 **Experiment Planning** | 15 agents | Power analysis, protocol optimization, preregistration |
| 💾 **Data Management** | 15 agents | Import, validation, batch correction, versioning |
| 📈 **Data Analysis** | 20 agents | QC, single-cell, proteomics, ML/DL analysis |
| 📊 **Figure Generation** | 15 agents | Publication figures, interactive dashboards, 3D viz |
| ✍️ **Scientific Writing** | 20 agents | Abstracts, methods, grants, presentations |
| 🔍 **Code Review** | 11 agents | Security, quality, performance, documentation audit |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         🎨 Web UI                               │
│                  React + Vite + Tailwind                        │
│              (Agent selection, workflow builder)                │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────▼───────────────────────────────────────┐
│                      🔌 REST API                                │
│                 FastAPI + OAuth2 JWT                            │
│         (Sessions, Analysis, Agents, Auth, Health)              │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Task Queue
┌─────────────────────────▼───────────────────────────────────────┐
│                   🤖 Agent Orchestrator                         │
│              (Task routing, planning, delegation)               │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Literature│  │Experiment│  │   Data   │  │ Analysis │       │
│  │  Review  │  │ Planning │  │Management│  │          │       │
│  │  Agents  │  │  Agents  │  │  Agents  │  │  Agents  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Figure   │  │ Writing  │  │  Review  │                      │
│  │Generation│  │  Agents  │  │  Agents  │                      │
│  │  Agents  │  │          │  │          │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
├─────────────────────────────────────────────────────────────────┤
│                      🛠️ Skill Registry                          │
│    PubMed API │ RDKit │ Scanpy │ Matplotlib │ LLM Writing      │
├─────────────────────────────────────────────────────────────────┤
│                   🔌 Connector Framework                        │
│    PubMed │ ChEMBL │ PDB │ GEO │ SRA │ ZINC │ AlphaFold       │
├─────────────────────────────────────────────────────────────────┤
│                   🔒 Security Sandbox                           │
│     Human-approval broker │ Network egress control              │
│     File system guards │ Biosecurity safeguards                │
├─────────────────────────────────────────────────────────────────┤
│                  ⚙️ Compute Backend Router                      │
│    Local │ Docker │ SSH │ SLURM │ Cloud GPU │ Kubernetes       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Feature Status

| Category | Status | Details |
|----------|--------|---------|
| **Core Framework** | ✅ Production Ready | Orchestration, sandbox, session management |
| **Docker Infrastructure** | ✅ Working | API + UI + Worker + PostgreSQL + Redis |
| **REST API** | ✅ Tested | FastAPI with JWT auth, rate limiting (9/10 tests) |
| **Review Agents** | ✅ Working | Security, quality, performance audits (71 findings found) |
| **Literature Agents** | 🟡 Partial | PubMed connector implemented, needs testing |
| **Analysis Agents** | 🟡 Partial | RDKit, statsmodels implemented, needs validation |
| **Web UI** | 🟡 Basic | React app exists, needs polish and integration |
| **Full Workflows** | 🔴 Incomplete | End-to-end science workflows need integration |

**Legend:** ✅ Working | 🟡 Partial | 🔴 Not Started

---

## 🐳 Docker Deployment

### Development Environment

```bash
docker-compose up -d
# ✅ 6 services: API, UI, Worker, PostgreSQL, Redis, Flower
# ✅ Health checks: API (200), DB connected, Redis PONG
# ⚠️  Known: Flower optional service (needs install fix)
```

### Services

| Service | Port | Status | Description |
|---------|------|--------|-------------|
| **openscience-api** | 8000 | ✅ Healthy | FastAPI REST API |
| **openscience-ui** | 8080 | ✅ Healthy | React web interface |
| **openscience-worker** | - | ✅ Healthy | Celery background workers |
| **postgres** | 5432 | ✅ Healthy | Database |
| **redis** | 6379 | ✅ Healthy | Task queue/cache |
| **flower** | 5555 | ⚠️ Restarting | Celery monitoring (optional) |

---

## 📦 Python Library

```bash
# Install from source
pip install -e ".[all]"

# Install specific capabilities
pip install -e ".[bio]"      # Bioinformatics
pip install -e ".[chem]"     # Chemistry
pip install -e ".[api]"      # REST API
pip install -e ".[worker]"   # Background workers

# Use in Python
from openscience import ScienceSession

session = ScienceSession()
session.load_data("data/experiment.h5ad")
result = session.analyze("Quality control", specialist="scanpy_specialist")
```

**Package Structure:**
```
openscience/
├── core/           # Agent orchestration, sandbox, sessions
├── agents/         # 111 specialized agents
│   ├── literature/     # 15 agents
│   ├── experiment/     # 15 agents
│   ├── data_management/# 15 agents
│   ├── analysis/       # 20 agents
│   ├── visualization/  # 15 agents
│   ├── writing/        # 20 agents
│   └── review/         # 11 agents
├── skills/         # Scientific tools (PubMed, RDKit, Scanpy, Matplotlib)
├── connectors/     # Database connectors (PubMed, PDB, ChEMBL)
├── api/            # FastAPI REST API
└── workers/        # Celery background tasks
```

---

## 🧪 Testing & Quality

### Test Results

| Test Suite | Status | Details |
|------------|--------|---------|
| **Core Framework** | ✅ 156/156 passing | Agent, orchestrator, session, sandbox |
| **Runtime Regression** | ✅ 18/18 passing | Agent execution edge cases |
| **Docker Infrastructure** | ✅ 9/10 passing | Builds, networking, persistence |
| **API Endpoints** | ✅ 9/10 passing | Auth, sessions, analysis, health |
| **Review Agent Audit** | ✅ 71 findings | Security, quality, performance issues |

### Coverage

| Module | Coverage |
|--------|----------|
| Core framework | 86% |
| API layer | 0% (needs tests) |
| Overall | 29.8% (needs improvement) |

---

## 🔧 Current Issues

### Critical
- **Test coverage low**: API at 0%, overall 29.8%
- **Skills incomplete**: Scientific tools (Scanpy, LLM writing) partial
- **Workflow integration**: End-to-end science not tested

### Minor
- **Dockerflower**: Optional service needs `pip install flower`
- **Log volumes**: Named volumes have permission issues
- **Health endpoint**: Rate-limited (may affect k8s probes)

---

## 🤖 Agent Catalog Summary

### Review Agents (Working ✅)

| Agent | Purpose | Findings |
|-------|---------|----------|
| `security_reviewer` | OWASP, vulnerability scanning | 9 findings (1 P0 fixed) |
| `code_quality_reviewer` | PEP 8, complexity, duplication | 8 findings |
| `architecture_reviewer` | Module coupling, SOLID principles | 7 findings |
| `performance_reviewer` | Bottlenecks, optimization | 6 findings |
| `documentation_reviewer` | Docstring coverage, README | 5 findings |
| `test_coverage_reviewer` | Test coverage, mutation testing | 7 findings (1 P0) |
| `database_reviewer` | Schema design, query optimization | 6 findings |
| `api_design_reviewer` | RESTful conventions, OpenAPI | 7 findings |
| `accessibility_reviewer` | WCAG compliance, ARIA | 8 findings |
| `devops_reviewer` | Docker, CI/CD, IaC | 8 findings (1 P0) |
| `dependency_reviewer` | Vulnerability scanning, licenses | - |

### Scientific Agents (Partial 🟡)

- **Literature Review**: PubMed connector implemented, needs testing
- **Data Analysis**: RDKit, statsmodels implemented, needs validation
- **Figure Generation**: Matplotlib implemented, needs integration
- **Writing**: LLM writing framework exists, needs prompts

[View Full Agent Catalog →](docs/agents.md)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation and first steps |
| [Architecture](docs/architecture.md) | System design deep-dive |
| [Agent Catalog](docs/agents.md) | All 111 agents documented |
| [API Reference](docs/api.md) | REST API documentation |
| [Docker Guide](docs/docker.md) | Docker deployment guide |
| [Library Guide](docs/library.md) | Python package usage |
| [Examples](docs/examples/) | Tutorials and workflows |
| [Troubleshooting](docs/troubleshooting.md) | Common issues |
| [Security](docs/security.md) | Security policies |
| [Contributing](CONTRIBUTING.md) | Contribution guidelines |

---

## 🤝 Contributing

We welcome contributions! Key areas needing work:

1. **Scientific Skills**: Implement real Scanpy, RDKit, LLM writing skills
2. **End-to-End Testing**: Test complete scientific workflows
3. **API Coverage**: Bring API test coverage to 80%+
4. **UI Polish**: Modernize web interface, integrate with API
5. **Agent Integration**: Connect all agents to real skills

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

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

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ by the openScience community**

[GitHub](https://github.com/YakinRubaiat/openScience) • [Documentation](docs/index.md) • [Issues](https://github.com/YakinRubaiat/openScience/issues)

</div>
