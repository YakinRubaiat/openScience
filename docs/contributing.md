---
layout: default
title: Contributing
nav_order: 11
description: "How to contribute to openScience"
---

# Contributing to openScience

Thank you for your interest in contributing! openScience is a community project, and every contribution — whether a new agent, a bug fix, or documentation — makes it better.

> This page complements the [root CONTRIBUTING.md](https://github.com/YakinRubaiat/openScience/blob/main/CONTRIBUTING.md) with expanded guidance and examples.

---

## 🤝 Code of Conduct

By participating, you agree to:

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive criticism
- Respect differing viewpoints and experiences

---

## 🗺️ Ways to Contribute

| Type | Skill level | Examples |
|------|-------------|----------|
| 📖 Documentation | Beginner | Fix typos, clarify guides, add examples |
| 🐛 Bug reports | Beginner | File detailed issues with reproduction steps |
| ✅ Tests | Intermediate | Add coverage for untested agents |
| 🤖 New agents | Intermediate | Implement domain-specialized agents |
| 🔌 Connectors | Intermediate | Integrate new databases |
| 🏗️ Core framework | Advanced | Orchestrator, sandbox, backends |
| 🎨 Web UI | Intermediate | React components, dashboards |

---

## 🚀 Development Workflow

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_USERNAME/openScience.git
cd openScience
git remote add upstream https://github.com/YakinRubaiat/openScience.git
```

### 2. Set up the dev environment

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev,all]"
pre-commit install
```

Full instructions: [Development Setup](development.md).

### 3. Create a branch

```bash
git checkout -b feat/my-agent
# or
git checkout -b fix/scanpy-memory
```

### 4. Write code and tests

- Match the existing code style (black, 100 cols)
- Add type hints everywhere
- Write tests for new functionality
- Update documentation

### 5. Run checks locally

```bash
pytest
black --check src/ tests/
ruff check src/
mypy src/
```

### 6. Commit and push

Use [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add metabolomics_analyzer agent
fix: handle empty response in pubmed connector
docs: clarify docker memory requirements
test: add orchestrator routing tests
refactor: simplify provenance tracker
chore: bump scanpy to 1.10
```

### 7. Open a pull request

- Reference the issue: `Closes #123`
- Describe what changed and why
- Include screenshots for UI changes
- Keep PRs focused — one feature or fix per PR

---

## ➕ Adding a New Agent

### Step 1 — Pick a category

Agents live under `src/openscience/agents/<category>/`:

| Category | Directory |
|----------|-----------|
| Literature Review | `literature/` |
| Experiment Planning | `experiment/` |
| Data Management | `data_management/` |
| Data Analysis | `analysis/` |
| Figure Generation | `visualization/` |
| Scientific Writing | `writing/` |

### Step 2 — Implement

```python
# src/openscience/agents/analysis/my_agent.py

from openscience.core.agent import BaseAgent, AgentMetadata


class MyAgent(BaseAgent):
    """Analyzes X using Y algorithm."""

    metadata = AgentMetadata(
        name="my_agent",                  # snake_case, unique
        category="analysis",
        description="One-line description for the catalog",
        required_skills=["scanpy"],       # verified available at startup
        input_types=["anndata"],
        output_types=["results"],
    )

    async def execute(self, task, context):
        """Main entry point. Must be async."""
        data = context["data"]
        params = task.parameters

        result = await self.run_skill(
            "scanpy",
            operation="qc",
            data=data,
            **params,
        )
        return self.format_result(result)
```

**Agent contract**:

- Async `execute()` method
- Declare dependencies via `metadata.required_skills`
- Use `self.run_skill()` — never import tools directly
- Return via `self.format_result()` for consistent provenance

### Step 3 — Test

```python
# tests/agents/analysis/test_my_agent.py

import pytest
from openscience.agents.analysis.my_agent import MyAgent


class TestMyAgent:
    def test_metadata(self):
        assert MyAgent.metadata.name == "my_agent"
        assert "scanpy" in MyAgent.metadata.required_skills

    @pytest.mark.asyncio
    async def test_execute(self, sample_anndata, mock_orchestrator):
        agent = MyAgent(orchestrator=mock_orchestrator)
        task = make_task(params={"min_genes": 200})
        context = {"data": sample_anndata}
        result = await agent.execute(task, context)
        assert result["agent"] == "my_agent"
```

### Step 4 — Document

Append to `docs/agents.md`:

```markdown
### my_agent
**Category**: Data Analysis
**Description**: One-line description
**Skills**: scanpy
**Input**: anndata
**Output**: results
```

---

## 🔌 Adding a New Connector

```python
# src/openscience/connectors/my_database.py

from openscience.core.connector import BaseConnector, ConnectorMetadata


class MyDatabaseConnector(BaseConnector):
    metadata = ConnectorMetadata(
        name="my_database",
        base_url="https://api.mydatabase.org",
        auth_type="api_key",       # none | api_key | oauth
        rate_limit=100,            # requests per minute
    )

    async def search(self, query: str, **kwargs):
        """Search the database. Respect rate_limit."""
        ...
```

Remember:

- Respect rate limits; the connector framework helps, but you own correctness
- Cache sensibly (`cache_ttl`)
- Never bypass the sandbox — access goes through the allowlist

---

## 📖 Documentation Standards

When editing docs:

- Use clear, short sentences
- Prefer code examples over prose
- Add a table of contents for long pages
- Use the same YAML front matter as existing pages (`layout`, `title`, `nav_order`, `description`)
- For diagrams, use ASCII art in code blocks for diff-friendly reviews
- Link between related pages

---

## ✅ Pull Request Checklist

Before opening your PR, confirm:

- [ ] Tests pass: `pytest`
- [ ] Code formatted: `black src/ tests/`
- [ ] Lints clean: `ruff check src/`
- [ ] Types check: `mypy src/`
- [ ] Coverage maintained or improved
- [ ] Documentation updated (docs/, docstrings)
- [ ] CHANGELOG entry added (for user-facing changes)
- [ ] PR title follows Conventional Commits
- [ ] Linked issue(s) referenced

---

## 🔍 Review Process

1. Automated CI runs (tests, lint, type check)
2. At least one maintainer review
3. Address feedback with new commits (don't force-push during review)
4. Maintainer merges with squash commit

Typical review timeline: 3–7 days for small changes, up to 2 weeks for large PRs.

---

## 🏷️ Release Process

Releases follow [Semantic Versioning](https://semver.org/):

1. Version bump in `pyproject.toml`
2. CHANGELOG.md update
3. Create GitHub release
4. Publish to PyPI (automated)

Maintainers handle releases; contributors don't need to do anything special.

---

## 💬 Getting Help

- **Questions**: [GitHub Discussions](https://github.com/YakinRubaiat/openScience/discussions)
- **Bugs**: [Open an issue](https://github.com/YakinRubaiat/openScience/issues)
- **Design discussions**: comment on the relevant RFC issue

---

## ➡️ See Also

- [Development Setup](development.md)
- [Architecture](architecture.md)
- [Agent Catalog](agents.md) — patterns for existing agents
