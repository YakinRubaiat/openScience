---
layout: default
title: Development Setup
nav_order: 8
description: "Set up a local development environment for openScience"
---

# Development Setup

This guide gets you from a fresh clone to running tests, formatting code, and submitting your first pull request.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Core language |
| Git | 2.x+ | Version control |
| Docker | 20.10+ | Integration tests |
| Node.js | 18+ | UI development *(optional)* |
| R | 4.x+ | DESeq2, Seurat agents *(optional)* |

---

## Five-Minute Setup

```bash
# 1. Fork on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/openScience.git
cd openScience

# 2. Track the upstream repo
git remote add upstream https://github.com/YakinRubaiat/openScience.git

# 3. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Install in development mode
pip install -e ".[dev,all]"

# 5. Install pre-commit hooks
pre-commit install

# 6. Run tests to verify
pytest tests/ -v
```

If the suite passes, you're ready to develop.

---

## Step by Step

### 1. Install dependencies

`pyproject.toml` defines several extras:

```bash
pip install -e ".[dev]"     # core development tools (pytest, black, ruff, mypy)
pip install -e ".[bio]"     # biopython, scanpy, anndata, pysam
pip install -e ".[chem]"    # rdkit, openmm
pip install -e ".[ml]"      # torch, tensorflow, xgboost
pip install -e ".[viz]"     # dash, bokeh, altair
pip install -e ".[all]"     # everything
```

Development dependencies:

- `pytest`, `pytest-asyncio`, `pytest-cov` — tests and coverage
- `black` — formatter
- `ruff` — linter
- `mypy` — static type checker
- `pre-commit` — git hooks

### 2. Pre-commit hooks

`.pre-commit-config.yaml` runs on every commit:

```bash
# Install
pre-commit install

# Run manually against all files
pre-commit run --all-files
```

Hooks include:

- `black` (code formatting)
- `ruff` (lint)
- `mypy` (type check on changed files)
- YAML/Markdown formatting checks
- Large-file and private-key detection

### 3. IDE configuration

**VS Code** (`.vscode/settings.json` — already in repo):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "ms-python.black-formatter",
  "[python]": {
    "editor.codeActionsOnSave": { "source.organizeImports": true }
  }
}
```

**PyCharm**: set the project interpreter to `./venv/bin/python` and enable pytest as the test runner.

---

## Project Layout

```text
openScience/
├── src/openscience/
│   ├── __init__.py
│   ├── cli.py                  # CLI entry point
│   ├── server.py               # Flask REST API
│   ├── core/
│   │   ├── session.py          # ScienceSession
│   │   ├── orchestrator.py     # AgentOrchestrator
│   │   ├── agent.py            # BaseAgent, AgentMetadata
│   │   └── sandbox.py          # OS-level sandbox
│   ├── agents/                 # 100 specialized agents
│   │   ├── literature/         #   15
│   │   ├── experiment/         #   15
│   │   ├── data_management/    #   15
│   │   ├── analysis/           #   20
│   │   ├── visualization/      #   15
│   │   └── writing/            #   20
│   ├── connectors/             # 60+ database connectors
│   ├── skills/                 # 150+ scientific tools
│   └── api/                    # REST endpoints
├── tests/
│   ├── agents/                 # per-agent tests
│   ├── integration/            # end-to-end tests
│   └── conftest.py             # shared fixtures
├── docs/                       # this documentation
├── examples/                   # example projects
├── scripts/                    # utility scripts
├── docker/                     # Dockerfiles
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## Testing

### Run tests

```bash
pytest                          # all tests
pytest tests/agents/            # agent tests only
pytest tests/integration/       # end-to-end tests
pytest -v                       # verbose
pytest -k "scanpy"              # filter by name
pytest --maxfail=1 -x           # stop on first failure
```

### Coverage

```bash
pytest --cov=openscience --cov-report=html
open htmlcov/index.html
```

Target: **>80% coverage** for new code.

### Async tests

```python
import pytest

class TestMyAgent:
    @pytest.mark.asyncio
    async def test_execute(self):
        agent = MyAgent()
        result = await agent.execute(task, context)
        assert result is not None
```

### Integration tests with Docker

```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## Code Quality

```bash
# Format
black src/ tests/

# Lint
ruff check src/
ruff check --fix src/         # auto-fix

# Type check
mypy src/
```

Configuration lives in `pyproject.toml`:

```toml
[tool.black]
line-length = 100
target-version = ["py310"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true
```

---

## Adding a New Agent

### Step 1 — Create the agent file

```python
# src/openscience/agents/analysis/my_agent.py

from openscience.core.agent import BaseAgent, AgentMetadata


class MyAgent(BaseAgent):
    """Short description of what this agent does."""

    metadata = AgentMetadata(
        name="my_agent",
        category="analysis",
        description="One-line description",
        required_skills=["scanpy"],       # tools it needs
        input_types=["anndata"],
        output_types=["results"],
    )

    async def execute(self, task, context):
        data = context["data"]
        result = await self.run_skill(
            "scanpy", operation="qc",
            data=data,
            **task.parameters,
        )
        return self.format_result(result, agent=self.metadata.name)
```

### Step 2 — Add tests

```python
# tests/agents/analysis/test_my_agent.py

import pytest
from openscience.agents.analysis.my_agent import MyAgent


@pytest.mark.asyncio
async def test_my_agent_metadata():
    assert MyAgent.metadata.name == "my_agent"

@pytest.mark.asyncio
async def test_my_agent_execute(sample_anndata):
    agent = MyAgent(orchestrator=None)
    # construct task/context, run, assert
```

### Step 3 — Document

Update `docs/agents.md` with the new agent following the existing format:

```markdown
### my_agent
**Category**: Data Analysis
**Description**: One-line description
**Skills**: scanpy
**Input**: anndata
**Output**: results
```

### Step 4 — Wire into orchestrator

The orchestrator auto-discovers agents in `src/openscience/agents/`. No registry edit needed if you follow the layout.

---

## Working with Branches

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create a feature branch
git checkout -b feat/my-agent

# Work, commit, push
git add -A
git commit -m "feat: add my_agent"
git push -u origin feat/my-agent
```

**Commit message format** (Conventional Commits):

```text
feat: add new agent
fix: resolve scanpy memory leak
docs: update quickstart
test: add integration test for orchestrator
refactor: simplify connector caching
chore: bump dependencies
```

---

## Building and Releasing

```bash
# Bump version in pyproject.toml

# Build distribution
python -m build

# Inspect
tar tzf dist/openscience-0.1.0.tar.gz

# Upload to PyPI (maintainers only)
twine upload dist/*
```

---

## Debugging Tips

### Log level

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or in `openscience.yaml`:

```yaml
logging:
  level: DEBUG
```

### Inspect the orchestrator

```python
from openscience.core.orchestrator import AgentOrchestrator

orch = AgentOrchestrator()
print(list(orch.agents.keys()))
print(orch.route("cluster my scRNA-seq data"))
```

### VS Code debugger

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "pytest current",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

---

## Keeping Your Fork in Sync

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

---

## See Also

- [Contributing Guide](contributing.md) — PR process and code of conduct
- [Architecture](architecture.md) — how it all fits together
- [Troubleshooting](troubleshooting.md) — dev environment issues
