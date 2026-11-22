"""Tests for openscience.core.session — ScienceSession."""

import pickle
from pathlib import Path
from unittest.mock import patch

from openscience.core.agent import AgentMetadata, BaseAgent
from openscience.core.orchestrator import AgentOrchestrator, Result
from openscience.core.session import ScienceSession

# ---------------------------------------------------------------------------
# Concrete agent stubs
# ---------------------------------------------------------------------------


class DataIngestorStub(BaseAgent):
    metadata = AgentMetadata(name="data_ingestor", category="d", description="load")

    async def execute(self, task, context):
        return Result(
            data={"loaded": str(task.parameters.get("file_path", ""))},
            metadata={},
            artifacts=[],
        )


class QCStub(BaseAgent):
    metadata = AgentMetadata(name="qc_analyzer", category="a", description="qc")

    async def execute(self, task, context):
        return Result(data="qc_output", metadata={}, artifacts=[])


class MethodsWriterStub(BaseAgent):
    metadata = AgentMetadata(name="methods_writer", category="w", description="methods")

    async def execute(self, task, context):
        return Result(data="methods_text", metadata={}, artifacts=[])


class PubFormatterStub(BaseAgent):
    metadata = AgentMetadata(name="publication_formatter", category="v", description="viz")

    async def execute(self, task, context):
        return Result(data="figure_path", metadata={}, artifacts=[])


class LitSummarizerStub(BaseAgent):
    metadata = AgentMetadata(name="lit_summarizer", category="l", description="qa")

    async def execute(self, task, context):
        q = task.parameters.get("question", "")
        return Result(data=f"Answer to: {q}", metadata={}, artifacts=[])


STUB_REGISTRY: dict[str, type[BaseAgent]] = {
    "data_ingestor": DataIngestorStub,
    "qc_analyzer": QCStub,
    "methods_writer": MethodsWriterStub,
    "publication_formatter": PubFormatterStub,
    "lit_summarizer": LitSummarizerStub,
}


# ---------------------------------------------------------------------------
# Helper to inject a stub registry into ScienceSession
# ---------------------------------------------------------------------------


def _session_with_registry(registry, **kwargs):
    """Create a ScienceSession using a custom agent registry."""
    kwargs.setdefault("sandbox_enabled", False)
    with patch.object(AgentOrchestrator, "_load_agents", return_value=registry):
        return ScienceSession(**kwargs)


# ===================================================================
# ScienceSession — Initialisation
# ===================================================================


class TestSessionInit:
    """Tests for ScienceSession construction."""

    def test_default_project_dir_is_cwd(self):
        session = _session_with_registry(STUB_REGISTRY)
        assert session.project_dir == Path.cwd()

    def test_custom_project_dir_string(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=str(tmp_path))
        assert session.project_dir == tmp_path

    def test_custom_project_dir_path(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        assert session.project_dir == tmp_path

    def test_default_compute_backend(self):
        session = _session_with_registry(STUB_REGISTRY)
        assert session.compute_backend == "local"

    def test_custom_compute_backend(self):
        session = _session_with_registry(STUB_REGISTRY, compute_backend="slurm")
        assert session.compute_backend == "slurm"

    def test_sandbox_enabled(self):
        session = _session_with_registry(STUB_REGISTRY, sandbox_enabled=True)
        assert session.sandbox is not None
        assert session.sandbox_enabled is True

    def test_sandbox_disabled(self):
        session = _session_with_registry(STUB_REGISTRY, sandbox_enabled=False)
        assert session.sandbox is None
        assert session.sandbox_enabled is False

    def test_data_results_artifacts_start_empty(self):
        session = _session_with_registry(STUB_REGISTRY)
        assert session._data == {}
        assert session._results == {}
        assert session._artifacts == []

    def test_orchestrator_created(self):
        session = _session_with_registry(STUB_REGISTRY)
        assert isinstance(session.orchestrator, AgentOrchestrator)


# ===================================================================
# ScienceSession — load_data
# ===================================================================


class TestLoadData:
    """Tests for the load_data method."""

    def test_load_data_returns_self_for_chaining(self, tmp_data_file):
        session = _session_with_registry(STUB_REGISTRY)
        returned = session.load_data(tmp_data_file)
        assert returned is session

    def test_load_data_stores_with_stem_name(self, tmp_data_file):
        session = _session_with_registry(STUB_REGISTRY)
        session.load_data(tmp_data_file)
        assert "test_data" in session._data

    def test_load_data_with_explicit_name(self, tmp_data_file):
        session = _session_with_registry(STUB_REGISTRY)
        session.load_data(tmp_data_file, name="my_dataset")
        assert "my_dataset" in session._data

    def test_load_data_via_ingestor(self, tmp_data_file):
        """Data is loaded through the data_ingestor agent."""
        session = _session_with_registry(STUB_REGISTRY)
        session.load_data(tmp_data_file)
        data = session._data["test_data"]
        # Our stub returns {"loaded": "<path>"}
        assert str(tmp_data_file) in data["loaded"]

    def test_load_data_with_format_hint(self, tmp_data_file):
        session = _session_with_registry(STUB_REGISTRY)
        session.load_data(tmp_data_file, format="csv")
        assert "test_data" in session._data

    def test_multiple_loads(self, tmp_path):
        f1 = tmp_path / "a.csv"
        f1.write_text("x,1\n")
        f2 = tmp_path / "b.csv"
        f2.write_text("y,2\n")
        session = _session_with_registry(STUB_REGISTRY)
        session.load_data(f1)
        session.load_data(f2)
        assert "a" in session._data
        assert "b" in session._data


# ===================================================================
# ScienceSession — analyze
# ===================================================================


class TestAnalyze:
    """Tests for the analyze method."""

    def test_analyze_returns_result(self):
        session = _session_with_registry(STUB_REGISTRY)
        result = session.analyze("run quality control")
        assert isinstance(result, Result)

    def test_analyze_stores_result(self):
        session = _session_with_registry(STUB_REGISTRY)
        task = "run quality control"
        result = session.analyze(task)
        assert task in session._results
        assert session._results[task] is result

    def test_analyze_with_specialist(self):
        session = _session_with_registry(STUB_REGISTRY)
        result = session.analyze("anything", specialist="qc_analyzer")
        assert result.data == "qc_output"

    def test_analyze_uses_last_loaded_data(self, tmp_path):
        """When data_name is not given the most recent dataset is used."""
        captured = {}

        class ContextCapture(BaseAgent):
            metadata = AgentMetadata(name="qc_analyzer", category="t", description="d")

            async def execute(self, task, context):
                captured["data"] = context.get("data")
                return Result(data=None, metadata={}, artifacts=[])

        reg = {**STUB_REGISTRY, "qc_analyzer": ContextCapture}
        f = tmp_path / "data1.csv"
        f.write_text("col\n1\n")

        session = _session_with_registry(reg)
        session.load_data(f)
        session.analyze("qc it")
        assert "data" in captured

    def test_analyze_with_explicit_data_name(self, tmp_path):
        captured = {}

        class ContextCapture(BaseAgent):
            metadata = AgentMetadata(name="qc_analyzer", category="t", description="d")

            async def execute(self, task, context):
                captured["ctx_data"] = context.get("data")
                return Result(data=None, metadata={}, artifacts=[])

        reg = {**STUB_REGISTRY, "qc_analyzer": ContextCapture}
        f1 = tmp_path / "first.csv"
        f1.write_text("a\n1\n")
        f2 = tmp_path / "second.csv"
        f2.write_text("b\n2\n")

        session = _session_with_registry(reg)
        session.load_data(f1, name="first")
        session.load_data(f2, name="second")
        session.analyze("qc", data_name="first")

        # The context "data" key should hold the data for "first"
        assert captured["ctx_data"] is not None
        assert "first" in str(captured["ctx_data"])


# ===================================================================
# ScienceSession — visualize
# ===================================================================


class TestVisualize:
    """Tests for the visualize method."""

    def test_returns_result(self):
        session = _session_with_registry(STUB_REGISTRY)
        result = session.visualize("some_result")
        assert isinstance(result, Result)

    def test_default_type_and_style(self):
        session = _session_with_registry(STUB_REGISTRY)
        result = session.visualize("data")
        assert result.data == "figure_path"

    def test_custom_type_and_style(self):
        session = _session_with_registry(STUB_REGISTRY)
        result = session.visualize("data", type="umap", style="presentation")
        assert result.data == "figure_path"


# ===================================================================
# ScienceSession — write_methods
# ===================================================================


class TestWriteMethods:
    """Tests for the write_methods method."""

    def test_returns_string(self):
        session = _session_with_registry(STUB_REGISTRY)
        result = session.write_methods("some_analysis")
        assert isinstance(result, str)
        assert result == "methods_text"

    def test_custom_style_and_citation(self):
        session = _session_with_registry(STUB_REGISTRY)
        result = session.write_methods("analysis", style="science", citation_format="vancouver")
        assert result == "methods_text"


# ===================================================================
# ScienceSession — ask
# ===================================================================


class TestAsk:
    """Tests for the ask method."""

    def test_returns_answer_string(self):
        session = _session_with_registry(STUB_REGISTRY)
        answer = session.ask("What is the meaning of life?")
        assert isinstance(answer, str)
        assert "What is the meaning of life?" in answer


# ===================================================================
# ScienceSession — _build_context
# ===================================================================


class TestBuildContext:
    """Tests for the context builder."""

    def test_contains_expected_keys(self):
        session = _session_with_registry(STUB_REGISTRY)
        ctx = session._build_context()
        expected_keys = {"project_dir", "data", "results", "artifacts", "sandbox"}
        assert set(ctx.keys()) == expected_keys

    def test_project_dir_value(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        ctx = session._build_context()
        assert ctx["project_dir"] == tmp_path


# ===================================================================
# ScienceSession — save / load
# ===================================================================


class TestSaveLoad:
    """Tests for session persistence."""

    def test_save_creates_file(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        session._data["test"] = {"x": 1}
        save_path = tmp_path / "session.pkl"
        session.save(save_path)
        assert save_path.exists()

    def test_save_returns_path(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        save_path = tmp_path / "session.pkl"
        returned = session.save(save_path)
        assert returned == save_path

    def test_saved_content_is_pickle(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        session._data["sample"] = 42
        save_path = tmp_path / "session.pkl"
        session.save(save_path)

        with open(save_path, "rb") as f:
            state = pickle.load(f)
        assert state["data"]["sample"] == 42

    def test_load_restores_data(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        session._data["ds"] = [1, 2, 3]
        save_path = tmp_path / "state.pkl"
        session.save(save_path)

        with patch.object(AgentOrchestrator, "_load_agents", return_value=STUB_REGISTRY):
            loaded = ScienceSession.load(save_path)
        assert loaded._data["ds"] == [1, 2, 3]

    def test_load_restores_results(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        session._results["task1"] = "fake_result"
        save_path = tmp_path / "state.pkl"
        session.save(save_path)

        with patch.object(AgentOrchestrator, "_load_agents", return_value=STUB_REGISTRY):
            loaded = ScienceSession.load(save_path)
        assert loaded._results["task1"] == "fake_result"

    def test_load_restores_project_dir(self, tmp_path):
        project = tmp_path / "my_project"
        project.mkdir()
        session = _session_with_registry(STUB_REGISTRY, project_dir=project)
        save_path = tmp_path / "state.pkl"
        session.save(save_path)

        with patch.object(AgentOrchestrator, "_load_agents", return_value=STUB_REGISTRY):
            loaded = ScienceSession.load(save_path)
        assert loaded.project_dir == project

    def test_load_restores_artifacts(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        session._artifacts.append(Path(tmp_path / "plot.png"))
        save_path = tmp_path / "state.pkl"
        session.save(save_path)

        with patch.object(AgentOrchestrator, "_load_agents", return_value=STUB_REGISTRY):
            loaded = ScienceSession.load(save_path)
        assert len(loaded._artifacts) == 1

    def test_save_creates_parent_dirs(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        deep_path = tmp_path / "a" / "b" / "c" / "session.pkl"
        session.save(deep_path)
        assert deep_path.exists()

    def test_load_returns_correct_type(self, tmp_path):
        session = _session_with_registry(STUB_REGISTRY, project_dir=tmp_path)
        save_path = tmp_path / "state.pkl"
        session.save(save_path)

        with patch.object(AgentOrchestrator, "_load_agents", return_value=STUB_REGISTRY):
            loaded = ScienceSession.load(save_path)
        assert isinstance(loaded, ScienceSession)
