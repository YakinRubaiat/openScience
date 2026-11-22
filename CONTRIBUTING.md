# Contributing to openScience

Thank you for your interest in contributing to openScience! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/openScience.git
   cd openScience
   ```
3. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/my-feature
   ```
4. **Set up the development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=openscience --cov-report=html

# Specific category
pytest tests/agents/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/

# Type checking
mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

## Adding a New Agent

1. **Choose the right category**: literature, experiment, data_management, analysis, visualization, or writing

2. **Create the agent file**:
   ```python
   # src/openscience/agents/analysis/my_agent.py
   
   from openscience.core.agent import BaseAgent, AgentMetadata
   
   class MyAgent(BaseAgent):
       metadata = AgentMetadata(
           name="my_agent",
           category="analysis",
           description="Description of what this agent does",
           required_skills=["skill1", "skill2"],
           input_types=["input_type"],
           output_types=["output_type"],
       )
       
       async def execute(self, task, context):
           # Implementation
           result = await self.run_skill("skill1", operation="process")
           return self.format_result(result)
   ```

3. **Add tests**:
   ```python
   # tests/agents/analysis/test_my_agent.py
   
   import pytest
   from openscience.agents.analysis.my_agent import MyAgent
   
   class TestMyAgent:
       @pytest.mark.asyncio
       async def test_execute(self):
           agent = MyAgent()
           # Test implementation
   ```

4. **Update documentation** in `docs/agents.md`

## Adding a New Connector

1. **Create the connector file**:
   ```python
   # src/openscience/connectors/my_database.py
   
   from openscience.core.connector import BaseConnector, ConnectorMetadata
   
   class MyDatabaseConnector(BaseConnector):
       metadata = ConnectorMetadata(
           name="my_database",
           base_url="https://api.mydatabase.org",
           auth_type="api_key",
           rate_limit=100,  # requests per minute
       )
       
       async def search(self, query: str, **kwargs):
           # Implementation
           pass
   ```

2. **Add credentials handling** (if required)
3. **Add tests and documentation**

## Pull Request Process

1. **Update documentation** for any new features
2. **Add tests** for new functionality
3. **Ensure all tests pass** and code quality checks pass
4. **Describe your changes** in the PR description
5. **Link related issues** using GitHub keywords (closes #123)

### PR Title Format

- `feat: Add new feature`
- `fix: Fix bug in component`
- `docs: Update documentation`
- `test: Add tests for feature`
- `refactor: Refactor component`

## Release Process

1. Version bump in `pyproject.toml`
2. Update CHANGELOG.md
3. Create GitHub release
4. Publish to PyPI

## Questions?

- Open an issue for bug reports or feature requests
- Start a discussion for questions or ideas
- Join our community chat (link in README)
