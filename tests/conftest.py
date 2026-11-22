"""Shared pytest fixtures for the openScience test suite."""

import pickle
from unittest.mock import AsyncMock, MagicMock

import pytest

from openscience.core.agent import AgentMetadata, BaseAgent
from openscience.core.orchestrator import Result, Task

# ---------------------------------------------------------------------------
# Mock Agents
# ---------------------------------------------------------------------------


class MockAgent(BaseAgent):
    """Concrete mock agent for testing the BaseAgent interface."""

    metadata = AgentMetadata(
        name="mock_agent",
        category="testing",
        description="A mock agent for unit tests",
        required_skills=["mock_skill"],
        input_types=["any"],
        output_types=["any"],
    )

    async def execute(self, task, context):
        """Return a simple formatted result."""
        return self.format_result({"task": task.description, "params": task.parameters})


class AnotherMockAgent(BaseAgent):
    """A second mock agent with different metadata."""

    metadata = AgentMetadata(
        name="another_mock",
        category="testing",
        description="Another mock agent",
    )

    async def execute(self, task, context):
        return self.format_result("another_result")


@pytest.fixture
def mock_agent():
    """Provide an un-orchestrated MockAgent instance."""
    return MockAgent()


@pytest.fixture
def mock_agent_cls():
    """Provide the MockAgent class (not an instance)."""
    return MockAgent


@pytest.fixture
def another_mock_agent_cls():
    """Provide the AnotherMockAgent class."""
    return AnotherMockAgent


@pytest.fixture
def mock_orchestrator():
    """Provide a MagicMock orchestrator."""
    orch = MagicMock()
    orch.execute_skill = AsyncMock(return_value="skill_result")
    return orch


@pytest.fixture
def mock_agent_with_orchestrator(mock_orchestrator):
    """Provide a MockAgent wired to a mock orchestrator."""
    return MockAgent(orchestrator=mock_orchestrator)


# ---------------------------------------------------------------------------
# Tasks and Results
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_task():
    """Provide a basic Task for testing."""
    return Task(
        description="Run quality control",
        parameters={"data_type": "single_cell"},
        context={"data": [1, 2, 3]},
    )


@pytest.fixture
def sample_result():
    """Provide a basic Result for testing."""
    return Result(
        data={"qc_passed": True, "n_cells": 100},
        metadata={"agent": "qc_analyzer"},
        artifacts=["qc_report.html"],
    )


# ---------------------------------------------------------------------------
# Temporary directories and files
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Provide a temporary project directory."""
    project = tmp_path / "test_project"
    project.mkdir()
    return project


@pytest.fixture
def tmp_data_file(tmp_path):
    """Create a temporary CSV-like data file."""
    f = tmp_path / "test_data.csv"
    f.write_text("gene,cell1,cell2\nGAPDH,100,200\nACTB,150,250\n")
    return f


@pytest.fixture
def tmp_pickle_file(tmp_path):
    """Create a temporary pickle file with test data."""
    data = {"expression": [1, 2, 3], "metadata": {"type": "test"}}
    f = tmp_path / "test_data.pkl"
    with open(f, "wb") as fh:
        pickle.dump(data, fh)
    return f


# ---------------------------------------------------------------------------
# Database-like fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    """Provide a simple in-memory dict acting as a test database."""
    db = {}
    yield db
    db.clear()


# ---------------------------------------------------------------------------
# Agent registry fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_registry(mock_agent_cls, another_mock_agent_cls):
    """Provide a minimal agent registry for the orchestrator."""
    return {
        "mock_agent": mock_agent_cls,
        "another_mock": another_mock_agent_cls,
    }


# ---------------------------------------------------------------------------
# Sandbox fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def disabled_sandbox():
    """Provide a disabled Sandbox instance."""
    from openscience.core.sandbox import Sandbox

    return Sandbox(enabled=False)


@pytest.fixture
def enabled_sandbox_no_approval():
    """Provide an enabled Sandbox whose approval handler always returns True."""
    from openscience.core.sandbox import Sandbox

    return Sandbox(enabled=True, approval_handler=lambda agent, task: True)


@pytest.fixture
def enabled_sandbox_deny():
    """Provide an enabled Sandbox whose approval handler always returns False."""
    from openscience.core.sandbox import Sandbox

    return Sandbox(enabled=True, approval_handler=lambda agent, task: False)
