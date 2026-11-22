"""Tests for openscience.core.orchestrator — Task, Result, AgentOrchestrator."""

from unittest.mock import MagicMock

import pytest

from openscience.core.agent import AgentMetadata, BaseAgent
from openscience.core.orchestrator import AgentOrchestrator, Result, Task

# ---------------------------------------------------------------------------
# Concrete agent stubs for registration
# ---------------------------------------------------------------------------


class QCStub(BaseAgent):
    metadata = AgentMetadata(name="qc_analyzer", category="analysis", description="QC")

    async def execute(self, task, context):
        return Result(data="qc_done", metadata={}, artifacts=[])


class ScanpyStub(BaseAgent):
    metadata = AgentMetadata(name="scanpy_specialist", category="analysis", description="sc")

    async def execute(self, task, context):
        return Result(data="clustered", metadata={}, artifacts=[])


class Deseq2Stub(BaseAgent):
    metadata = AgentMetadata(name="deseq2_specialist", category="analysis", description="DE")

    async def execute(self, task, context):
        return Result(data="degs", metadata={}, artifacts=[])


class PubmedStub(BaseAgent):
    metadata = AgentMetadata(name="pubmed_search", category="literature", description="Lit")

    async def execute(self, task, context):
        return Result(data="papers", metadata={}, artifacts=[])


class VizStub(BaseAgent):
    metadata = AgentMetadata(name="matplotlib_stylist", category="viz", description="Fig")

    async def execute(self, task, context):
        return Result(data="figure", metadata={}, artifacts=[])


class WriterStub(BaseAgent):
    metadata = AgentMetadata(name="abstract_writer", category="writing", description="Abs")

    async def execute(self, task, context):
        return Result(data="abstract", metadata={}, artifacts=[])


class MethodsStub(BaseAgent):
    metadata = AgentMetadata(name="methods_writer", category="writing", description="Meth")

    async def execute(self, task, context):
        return Result(data="methods", metadata={}, artifacts=[])


class LitSummarizerStub(BaseAgent):
    metadata = AgentMetadata(name="lit_summarizer", category="literature", description="QA")

    async def execute(self, task, context):
        return Result(data=f"answer: {task.parameters.get('question')}", metadata={}, artifacts=[])


class DataIngestorStub(BaseAgent):
    metadata = AgentMetadata(name="data_ingestor", category="data", description="Load")

    async def execute(self, task, context):
        return Result(data="loaded", metadata={}, artifacts=[])


FULL_REGISTRY: dict[str, type[BaseAgent]] = {
    "qc_analyzer": QCStub,
    "scanpy_specialist": ScanpyStub,
    "deseq2_specialist": Deseq2Stub,
    "pubmed_search": PubmedStub,
    "matplotlib_stylist": VizStub,
    "abstract_writer": WriterStub,
    "methods_writer": MethodsStub,
    "lit_summarizer": LitSummarizerStub,
    "data_ingestor": DataIngestorStub,
}


# ===================================================================
# Task dataclass
# ===================================================================


class TestTask:
    """Tests for the Task dataclass."""

    def test_basic_construction(self):
        t = Task(description="do something", parameters={}, context={})
        assert t.description == "do something"
        assert t.parameters == {}
        assert t.context == {}
        assert t.specialist is None

    def test_specialist_field(self):
        t = Task(description="t", parameters={}, context={}, specialist="agent_x")
        assert t.specialist == "agent_x"

    def test_parameters_and_context(self):
        params = {"alpha": 1}
        ctx = {"beta": 2}
        t = Task(description="t", parameters=params, context=ctx)
        assert t.parameters is params
        assert t.context is ctx


# ===================================================================
# Result dataclass
# ===================================================================


class TestResult:
    """Tests for the Result dataclass."""

    def test_basic_construction(self):
        r = Result(data=42, metadata={"a": 1}, artifacts=["f.png"])
        assert r.data == 42
        assert r.metadata == {"a": 1}
        assert r.artifacts == ["f.png"]

    def test_empty_artifacts(self):
        r = Result(data=None, metadata={}, artifacts=[])
        assert r.artifacts == []


# ===================================================================
# AgentOrchestrator — Initialisation
# ===================================================================


class TestOrchestratorInit:
    """Tests for AgentOrchestrator initialization."""

    def test_default_backend_is_local(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        assert orch.compute_backend == "local"

    def test_custom_backend(self):
        orch = AgentOrchestrator(compute_backend="slurm", agent_registry=FULL_REGISTRY)
        assert orch.compute_backend == "slurm"

    def test_sandbox_stored(self):
        sb = MagicMock()
        orch = AgentOrchestrator(sandbox=sb, agent_registry=FULL_REGISTRY)
        assert orch.sandbox is sb

    def test_sandbox_defaults_to_none(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        assert orch.sandbox is None

    def test_custom_registry_is_used(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        assert orch.agents is FULL_REGISTRY

    def test_agent_cache_starts_empty(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        assert orch._agent_cache == {}


# ===================================================================
# AgentOrchestrator — Agent registry loading (_load_agents)
# ===================================================================


class TestLoadAgents:
    """Tests for the _load_agents method (discovery from agents package)."""

    def test_load_agents_returns_dict(self):
        """Default loading produces a dict."""
        orch = AgentOrchestrator.__new__(AgentOrchestrator)
        # Call _load_agents directly
        registry = orch._load_agents()
        assert isinstance(registry, dict)

    def test_load_agents_contains_known_agents(self):
        """The auto-discovered registry should include hard-coded agents."""
        orch = AgentOrchestrator.__new__(AgentOrchestrator)
        registry = orch._load_agents()
        # These agents exist in the codebase (qc_analyzer.py etc.)
        assert "qc_analyzer" in registry
        assert "data_ingestor" in registry
        assert "pubmed_search" in registry

    def test_load_agents_values_are_base_agent_subclasses(self):
        """Every value in the registry is a BaseAgent subclass."""
        orch = AgentOrchestrator.__new__(AgentOrchestrator)
        registry = orch._load_agents()
        for name, cls in registry.items():
            assert issubclass(cls, BaseAgent), f"{name} is not a BaseAgent subclass"

    def test_load_agents_keys_match_metadata_names(self):
        """Registry keys match the metadata.name of each class."""
        orch = AgentOrchestrator.__new__(AgentOrchestrator)
        registry = orch._load_agents()
        for key, cls in registry.items():
            assert key == cls.metadata.name


# ===================================================================
# AgentOrchestrator — Agent selection (_select_agent)
# ===================================================================


class TestSelectAgent:
    """Tests for keyword-based and specialist-based agent selection."""

    def test_explicit_specialist(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="anything", parameters={}, context={}, specialist="qc_analyzer")
        agent = orch._select_agent(task)
        assert isinstance(agent, QCStub)

    def test_unknown_specialist_raises(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="anything", parameters={}, context={}, specialist="nonexistent")
        with pytest.raises(ValueError, match="Unknown specialist"):
            orch._select_agent(task)

    def test_keyword_qc(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="Run quality control on the data", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, QCStub)

    def test_keyword_qc_short(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="qc this dataset", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, QCStub)

    def test_keyword_clustering(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="perform clustering", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, ScanpyStub)

    def test_keyword_single_cell(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="analyze single cell data", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, ScanpyStub)

    def test_keyword_rna_seq(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="rna-seq analysis", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, Deseq2Stub)

    def test_keyword_differential_expression(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="find differential expression", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, Deseq2Stub)

    def test_keyword_literature(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="search literature", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, PubmedStub)

    def test_keyword_papers(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="find related papers", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, PubmedStub)

    def test_keyword_figure(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="make a figure for publication", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, VizStub)

    def test_keyword_plot(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="plot the results", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, VizStub)

    def test_keyword_write(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="write the abstract", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, WriterStub)

    def test_keyword_methods(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="generate methods section", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, MethodsStub)

    def test_no_match_defaults_to_qc(self):
        """An unrecognized description defaults to qc_analyzer."""
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="xyzzy nonsense", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, QCStub)

    def test_case_insensitive_matching(self):
        """Keyword matching is case-insensitive (description is lowered)."""
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="Run QC on the DATA", parameters={}, context={})
        agent = orch._select_agent(task)
        assert isinstance(agent, QCStub)


# ===================================================================
# AgentOrchestrator — _get_agent_instance
# ===================================================================


class TestGetAgentInstance:
    """Tests for agent instance caching."""

    def test_creates_instance(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        agent = orch._get_agent_instance(QCStub)
        assert isinstance(agent, QCStub)
        assert agent.orchestrator is orch

    def test_caches_instances(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        a1 = orch._get_agent_instance(QCStub)
        a2 = orch._get_agent_instance(QCStub)
        assert a1 is a2

    def test_different_agents_get_separate_instances(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        a1 = orch._get_agent_instance(QCStub)
        a2 = orch._get_agent_instance(ScanpyStub)
        assert a1 is not a2


# ===================================================================
# AgentOrchestrator — execute_task
# ===================================================================


class TestExecuteTask:
    """Tests for the execute_task public method."""

    def test_executes_with_no_sandbox(self):
        """Without sandbox, agent.execute is called directly."""
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        result = orch.execute_task("run quality control")
        # The stub returns a Result
        assert isinstance(result, Result)
        assert result.data == "qc_done"

    def test_specialist_routing(self):
        """A named specialist routes to the correct agent."""
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        result = orch.execute_task("do anything", specialist="pubmed_search")
        assert result.data == "papers"

    def test_execute_task_with_sandbox(self):
        """When a sandbox is present its execute() is used."""
        sb = MagicMock()
        sb.execute = MagicMock(return_value=Result(data="sandboxed", metadata={}, artifacts=[]))
        orch = AgentOrchestrator(sandbox=sb, agent_registry=FULL_REGISTRY)

        result = orch.execute_task("run quality control")
        sb.execute.assert_called_once()
        assert result.data == "sandboxed"

    def test_parameters_and_context_forwarded(self):
        """Parameters/context land in the Task passed to the agent."""
        captured = {}

        class CaptureAgent(BaseAgent):
            metadata = AgentMetadata(name="capture", category="t", description="d")

            async def execute(self, task, context):
                captured["params"] = task.parameters
                captured["ctx"] = task.context
                return Result(data=None, metadata={}, artifacts=[])

        orch = AgentOrchestrator(agent_registry={**FULL_REGISTRY, "qc_analyzer": CaptureAgent})
        orch.execute_task("qc check", parameters={"p": 1}, context={"c": 2})
        assert captured["params"] == {"p": 1}
        assert captured["ctx"] == {"c": 2}


# ===================================================================
# AgentOrchestrator — execute_agent
# ===================================================================


class TestExecuteAgent:
    """Tests for executing a named agent directly."""

    def test_known_agent(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        result = orch.execute_agent("qc_analyzer", parameters={}, context={})
        assert isinstance(result, Result)
        assert result.data == "qc_done"

    def test_unknown_agent_raises_value_error(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        with pytest.raises(ValueError, match="Unknown agent"):
            orch.execute_agent("does_not_exist", parameters={}, context={})

    def test_execute_agent_with_sandbox(self):
        sb = MagicMock()
        sb.execute = MagicMock(return_value=Result(data="sb_data", metadata={}, artifacts=[]))
        orch = AgentOrchestrator(sandbox=sb, agent_registry=FULL_REGISTRY)
        result = orch.execute_agent("qc_analyzer", parameters={}, context={})
        sb.execute.assert_called_once()
        assert result.data == "sb_data"

    def test_execute_agent_creates_correct_task(self):
        """Verify the Task object constructed inside execute_agent."""
        captured = {}

        class CaptureAgent(BaseAgent):
            metadata = AgentMetadata(name="qc_analyzer", category="t", description="d")

            async def execute(self, task, context):
                captured["task"] = task
                captured["ctx"] = context
                return Result(data=None, metadata={}, artifacts=[])

        orch = AgentOrchestrator(agent_registry={**FULL_REGISTRY, "qc_analyzer": CaptureAgent})
        orch.execute_agent(
            "qc_analyzer",
            parameters={"x": 99},
            context={"y": 88},
        )
        t = captured["task"]
        assert t.specialist == "qc_analyzer"
        assert "qc_analyzer" in t.description
        assert t.parameters == {"x": 99}


# ===================================================================
# AgentOrchestrator — answer_question
# ===================================================================


class TestAnswerQuestion:
    """Tests for the answer_question convenience method."""

    def test_delegates_to_lit_summarizer(self):
        """answer_question invokes lit_summarizer."""
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        answer = orch.answer_question("What is scRNA-seq?", context={})
        assert "answer" in answer

    def test_question_in_result(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        q = "How many cells pass QC?"
        answer = orch.answer_question(q, context={})
        assert q in answer

    def test_missing_lit_summarizer_falls_back(self):
        """Without lit_summarizer the orchestrator falls back to any available agent."""
        reg = {k: v for k, v in FULL_REGISTRY.items() if k != "lit_summarizer"}
        orch = AgentOrchestrator(agent_registry=reg)
        # Falls back to the first registered agent — must not raise.
        answer = orch.answer_question("any question", context={})
        assert isinstance(answer, str)

    def test_empty_registry_returns_message(self):
        """An empty registry yields a friendly 'no agents' message, not an exception."""
        orch = AgentOrchestrator(agent_registry={})
        answer = orch.answer_question("any question", context={})
        assert "No agents" in answer


# ===================================================================
# AgentOrchestrator — Additional edge cases
# ===================================================================


class TestOrchestratorEdgeCases:
    """Miscellaneous edge-case tests."""

    def test_empty_registry(self):
        """Orchestrator with an empty registry raises ValueError on default selection."""
        orch = AgentOrchestrator(agent_registry={})
        task = Task(description="anything unmatched", parameters={}, context={})
        with pytest.raises(ValueError, match="No agents available"):
            orch._select_agent(task)

    def test_empty_description_no_crash(self):
        orch = AgentOrchestrator(agent_registry=FULL_REGISTRY)
        task = Task(description="", parameters={}, context={})
        agent = orch._select_agent(task)
        # Falls through to default qc_analyzer
        assert isinstance(agent, QCStub)
