---
layout: default
title: Library Build Guide
nav_order: 15
description: "Install and build the openScience library from source"
---

# Python Library Installation and Build Guide

## Building the openScience Library

### Prerequisites

```bash
# Install build tools
pip install build twine

# Install development dependencies
pip install -r requirements-dev.txt
```

### Building the Package

```bash
# Build source distribution and wheel
python -m build

# Output will be in dist/
# openscience-0.1.0.tar.gz
# openscience-0.1.0-py3-none-any.whl
```

### Installing the Package

```bash
# Install from source
pip install -e .

# Install from wheel
pip install dist/openscience-0.1.0-py3-none-any.whl

# Install with specific extras
pip install -e ".[api,ui,worker]"
pip install -e ".[bio,chem,ml]"

# Install all extras
pip install -e ".[all]"
```

### Verifying Installation

```bash
# Test import
python -c "import openscience; print(openscience.__version__)"

# Test CLI
openscience --version
openscience --help

# Run tests
pytest

# Check code quality
black --check src/
ruff check src/
mypy src/
```

### Package Structure

```text
openscience/
├── __init__.py          # Main package exports
├── __version__          # Version information
├── core/                # Core framework
│   ├── agent.py        # BaseAgent class
│   ├── orchestrator.py # AgentOrchestrator
│   ├── session.py      # ScienceSession
│   └── sandbox.py      # Security sandbox
├── agents/             # 111 specialized agents
│   ├── literature/     # 15 agents
│   ├── experiment/     # 15 agents
│   ├── data_management/# 15 agents
│   ├── analysis/       # 20 agents
│   ├── visualization/  # 15 agents
│   ├── writing/        # 20 agents
│   └── review/         # 11 agents
├── api/                # FastAPI REST API
│   ├── main.py         # API server
│   ├── routes/         # API endpoints
│   ├── models/         # Database models
│   ├── schemas/        # Pydantic schemas
│   └── middleware/     # Middleware
├── workers/            # Background workers
│   └── tasks.py        # Celery tasks
├── connectors/         # Database connectors
├── skills/             # Scientific tools
└── cli.py              # Command-line interface
```

### Available Extras

| Extra | Description | Dependencies |
|-------|-------------|--------------|
| `api` | FastAPI REST API | fastapi, uvicorn, sqlalchemy, pydantic |
| `ui` | Flask web interface | flask, flask-cors |
| `worker` | Background workers | celery, redis |
| `bio` | Bioinformatics | biopython, scanpy, anndata, pysam |
| `chem` | Chemistry | rdkit, openmm |
| `ml` | Machine Learning | torch, tensorflow, xgboost, transformers |
| `viz` | Visualization | dash, bokeh, altair, py3dmol |
| `dev` | Development | pytest, black, ruff, mypy, pre-commit |
| `docs` | Documentation | mkdocs, mkdocs-material |
| `all` | All extras | all of the above |

### Usage Examples

#### Basic Usage

```python
from openscience import ScienceSession

# Create a session
session = ScienceSession()

# Load data
session.load_data("data/experiment.h5ad", format="anndata")

# Run analysis
result = session.analyze(
    task="Quality control and clustering",
    specialist="scanpy_specialist"
)

# Generate figure
figure = session.visualize(result, type="umap")
```

#### Using Agents Directly

```python
import asyncio

from openscience import AgentOrchestrator

# Initialize orchestrator
orch = AgentOrchestrator()

# Get agent
agent = orch.agents["security_reviewer"]

# Execute
async def run():
    result = await agent.execute(task, context)
    return result

result = asyncio.run(run())
```

#### Using the CLI

```bash
# List all agents
openscience agents

# Initialize project
openscience init

# Start API server
openscience start --api --port 8000

# Start UI server
openscience start --ui --port 8080

# Run analysis
openscience run --task "quality control" --specialist qc_analyzer
```

### Development Workflow

```bash
# 1. Clone repository
git clone https://github.com/YakinRubaiat/openScience.git
cd openScience

# 2. Install in development mode
pip install -e ".[dev,docs]"

# 3. Run tests
pytest

# 4. Check code quality
black src/
ruff check src/
mypy src/

# 5. Build documentation
mkdocs build

# 6. Build package
python -m build

# 7. Upload to PyPI
twine upload dist/*
```

### Docker Development

```bash
# Build Docker image
docker build -t openscience:latest .

# Run container
docker run -p 8080:8080 openscience:latest

# Docker Compose
docker-compose up -d
```

### Contributing

See [CONTRIBUTING.md](https://github.com/YakinRubaiat/openScience/blob/main/CONTRIBUTING.md) for detailed guidelines on:

- Adding new agents
- Adding new connectors
- Adding new skills
- Running tests
- Code style
- Documentation

### License

MIT License - see [LICENSE](https://github.com/YakinRubaiat/openScience/blob/main/LICENSE) for details.
