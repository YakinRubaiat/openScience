"""Tests for openscience.core.agent — BaseAgent and AgentMetadata."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from openscience.core.agent import AgentMetadata, BaseAgent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class ConcreteAgent(BaseAgent):
    """Minimal concrete agent used across several tests."""

    metadata = AgentMetadata(
        name="concrete_agent",
        category="testing",
        description="Concrete agent for tests",
        required_skills=["skill_a"],
        input_types=["csv"],
        output_types=["json"],
    )

    async def execute(self, task, context):
        return {"executed": True}


class NoExecuteAgent(BaseAgent):
    """Agent that does NOT implement execute() — should fail instantiation."""

    metadata = AgentMetadata(
        name="no_execute",
        category="testing",
        description="Missing execute",
    )


# ===================================================================
# AgentMetadata
# ===================================================================


class TestAgentMetadata:
    """Tests for the AgentMetadata dataclass."""

    def test_basic_construction(self):
        """Metadata can be created with required fields only."""
        m = AgentMetadata(name="test", category="cat", description="desc")
        assert m.name == "test"
        assert m.category == "cat"
        assert m.description == "desc"

    def test_default_lists_are_empty(self):
        """Optional list fields default to empty lists."""
        m = AgentMetadata(name="a", category="b", description="c")
        assert m.required_skills == []
        assert m.input_types == []
        assert m.output_types == []

    def test_default_lists_are_not_shared(self):
        """Each instance gets its own mutable default (no shared state)."""
        m1 = AgentMetadata(name="a", category="b", description="c")
        m2 = AgentMetadata(name="x", category="y", description="z")
        m1.required_skills.append("skill")
        assert m2.required_skills == []

    def test_explicit_lists(self):
        """Lists can be provided explicitly."""
        m = AgentMetadata(
            name="a",
            category="b",
            description="c",
            required_skills=["scanpy"],
            input_types=["anndata"],
            output_types=["report"],
        )
        assert m.required_skills == ["scanpy"]
        assert m.input_types == ["anndata"]
        assert m.output_types == ["report"]

    def test_equality(self):
        """Two identical metadata objects are equal."""
        kwargs = dict(name="n", category="c", description="d")
        assert AgentMetadata(**kwargs) == AgentMetadata(**kwargs)

    def test_repr(self):
        """repr includes the name."""
        m = AgentMetadata(name="my_agent", category="c", description="d")
        assert "my_agent" in repr(m)


# ===================================================================
# BaseAgent — Instantiation
# ===================================================================


class TestBaseAgentInit:
    """Tests for BaseAgent construction."""

    def test_orchestrator_defaults_to_none(self):
        """Agent defaults to having no orchestrator."""
        agent = ConcreteAgent()
        assert agent.orchestrator is None

    def test_orchestrator_is_stored(self):
        """An orchestrator reference is retained."""
        fake = MagicMock()
        agent = ConcreteAgent(orchestrator=fake)
        assert agent.orchestrator is fake

    def test_skills_dict_initialized_empty(self):
        """Internal _skills dict starts empty."""
        agent = ConcreteAgent()
        assert agent._skills == {}

    def test_metadata_attribute(self):
        """Agent metadata class attribute is accessible on instances."""
        agent = ConcreteAgent()
        assert agent.metadata.name == "concrete_agent"

    def test_abc_enforcements(self):
        """BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent()


# ===================================================================
# BaseAgent — execute() enforcement
# ===================================================================


class TestBaseAgentExecuteAbstract:
    """Verify that execute() is enforced as abstract."""

    def test_execute_is_abstract(self):
        """BaseAgent.execute is marked abstract."""
        assert getattr(BaseAgent.execute, "__isabstractmethod__", False)

    def test_missing_execute_blocks_instantiation(self):
        """A subclass without execute() cannot be instantiated."""
        with pytest.raises(TypeError):
            NoExecuteAgent()


# ===================================================================
# BaseAgent — run_skill
# ===================================================================


class TestBaseAgentRunSkill:
    """Tests for the run_skill helper."""

    @pytest.mark.asyncio
    async def test_run_skill_delegates_to_orchestrator(self):
        """run_skill calls orchestrator.execute_skill with correct args."""
        orch = MagicMock()
        orch.execute_skill = AsyncMock(return_value="skill_out")
        agent = ConcreteAgent(orchestrator=orch)

        result = await agent.run_skill("scanpy", "qc", data=[1, 2])

        orch.execute_skill.assert_called_once_with(skill_name="scanpy", operation="qc", data=[1, 2])
        assert result == "skill_out"

    @pytest.mark.asyncio
    async def test_run_skill_raises_without_orchestrator(self):
        """run_skill raises RuntimeError if no orchestrator is set."""
        agent = ConcreteAgent()
        with pytest.raises(RuntimeError, match="not connected"):
            await agent.run_skill("any", "op")

    @pytest.mark.asyncio
    async def test_run_skill_passes_kwargs(self):
        """Extra **kwargs are forwarded to the orchestrator."""
        orch = MagicMock()
        orch.execute_skill = AsyncMock(return_value=None)
        agent = ConcreteAgent(orchestrator=orch)

        await agent.run_skill("tool", "op", alpha=1, beta=2)

        orch.execute_skill.assert_called_once_with(
            skill_name="tool", operation="op", alpha=1, beta=2
        )


# ===================================================================
# BaseAgent — format_result
# ===================================================================


class TestBaseAgentFormatResult:
    """Tests for the format_result helper."""

    def test_basic_format(self):
        """format_result returns agent name, data, and metadata keys."""
        agent = ConcreteAgent()
        out = agent.format_result("payload")
        assert out["agent"] == "concrete_agent"
        assert out["data"] == "payload"
        assert out["metadata"] == {}

    def test_extra_metadata(self):
        """Additional metadata kwargs are included."""
        agent = ConcreteAgent()
        out = agent.format_result("d", version=2, pipeline="test")
        assert out["metadata"]["version"] == 2
        assert out["metadata"]["pipeline"] == "test"

    def test_data_can_be_any_type(self):
        """format_result preserves arbitrary data types."""
        agent = ConcreteAgent()
        for val in (42, [1, 2], {"k": "v"}, None, b"bytes"):
            out = agent.format_result(val)
            assert out["data"] == val

    def test_returns_dict(self):
        """The return type is always a plain dict."""
        agent = ConcreteAgent()
        out = agent.format_result(None)
        assert isinstance(out, dict)


# ===================================================================
# Concrete subclass end-to-end
# ===================================================================


class TestConcreteAgentEndToEnd:
    """Sanity-check that a concrete agent can execute."""

    @pytest.mark.asyncio
    async def test_execute_returns_expected(self):
        agent = ConcreteAgent()
        result = await agent.execute(None, None)
        assert result == {"executed": True}
