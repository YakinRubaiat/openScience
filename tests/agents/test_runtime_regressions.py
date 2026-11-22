"""Regression tests for the three agent runtime errors fixed in Experiment 3.

Each test targets one historical bug:

1. ``code_quality_reviewer`` — ``AttributeError: 'str' object has no attribute 'get'``
   when skill returned a dict (iterated its string keys) instead of a list of
   complexity entries.
2. ``data_ingestor`` — ``AttributeError: 'DataIngestorAgent' object has no
   attribute 'detect_format'`` because the method was called but never
   implemented.
3. ``performance_reviewer`` — ``KeyError: slice(None, 3, None)`` when
   ``bottlenecks[:3]`` was attempted on a dict instead of a list.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from openscience.agents.data_management.data_ingestor import DataIngestorAgent
from openscience.agents.review.code_quality_reviewer import CodeQualityReviewerAgent
from openscience.agents.review.performance_reviewer import PerformanceReviewerAgent


def _task(parameters=None):
    return type(
        "Task",
        (),
        {
            "description": "test",
            "parameters": parameters or {},
            "context": {},
        },
    )()


def _orchestrator_returning(value):
    orch = MagicMock()
    orch.execute_skill = AsyncMock(return_value=value)
    return orch


# ---------------------------------------------------------------------------
# 1. code_quality_reviewer
# ---------------------------------------------------------------------------


class TestCodeQualityReviewerFix:
    @pytest.mark.asyncio
    async def test_dict_skill_output_does_not_raise(self):
        """Default stub dict output must not trigger AttributeError."""
        stub = {"skill": "x", "operation": "y", "status": "ok", "data": {}}
        agent = CodeQualityReviewerAgent(orchestrator=_orchestrator_returning(stub))
        result = await agent.execute(_task(), {})
        assert result["agent"] == "code_quality_reviewer"
        assert "recommendations" in result["data"]

    @pytest.mark.asyncio
    async def test_string_skill_output_does_not_raise(self):
        """Raw string outputs from any skill are tolerated."""
        agent = CodeQualityReviewerAgent(orchestrator=_orchestrator_returning("raw output"))
        result = await agent.execute(_task(), {})
        assert "recommendations" in result["data"]

    @pytest.mark.asyncio
    async def test_list_of_dict_complexity_produces_recommendation(self):
        """List of complexity dicts triggers refactor recommendation."""
        complexity_list = [
            {"name": "f1", "complexity": 15},
            {"name": "f2", "complexity": 3},
        ]

        async def skill(skill_name, operation, **kwargs):
            if skill_name == "radon":
                return complexity_list
            if skill_name == "pylint":
                return {"score": 9.5}
            if skill_name == "mypy":
                return {"error_count": 0}
            return {"issues": []}

        orch = MagicMock()
        orch.execute_skill = AsyncMock(side_effect=skill)
        agent = CodeQualityReviewerAgent(orchestrator=orch)
        result = await agent.execute(_task(), {})

        recs = result["data"]["recommendations"]
        complexity_recs = [r for r in recs if r["category"] == "complexity"]
        assert len(complexity_recs) == 1
        assert "f1" in complexity_recs[0]["functions"]

    def test_generate_recommendations_handles_str_complexity(self):
        """Direct call: string complexity must not raise AttributeError."""
        agent = CodeQualityReviewerAgent()
        # Should not raise; previously AttributeError: 'str' has no 'get'.
        recs = agent._generate_recommendations(
            pylint={"score": 9.0},
            complexity="not-a-list",
            formatting={},
            typing={},
        )
        assert isinstance(recs, list)


# ---------------------------------------------------------------------------
# 2. data_ingestor
# ---------------------------------------------------------------------------


class TestDataIngestorFix:
    @pytest.mark.asyncio
    async def test_execute_with_auto_format_does_not_raise(self):
        """Auto format detection must work — the historical missing method."""
        orch = _orchestrator_returning({"rows": [[1, 2]]})
        agent = DataIngestorAgent(orchestrator=orch)
        result = await agent.execute(_task({"file_path": "data.csv"}), {})
        assert result["data"]["format"] == "csv"

    def test_detect_format_exists(self):
        """The previously missing method exists and is callable."""
        assert hasattr(DataIngestorAgent, "detect_format")
        assert callable(DataIngestorAgent.detect_format)

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("file.csv", "csv"),
            ("file.tsv", "tsv"),
            ("file.h5ad", "h5ad"),
            ("file.parquet", "parquet"),
            ("file.unknown_ext", "csv"),
            ("no_extension", "csv"),
            (None, "csv"),
        ],
    )
    def test_detect_format_mappings(self, path, expected):
        assert DataIngestorAgent.detect_format(path) == expected

    @pytest.mark.asyncio
    async def test_explicit_format_hint_bypasses_detection(self):
        orch = _orchestrator_returning({})
        agent = DataIngestorAgent(orchestrator=orch)
        await agent.execute(_task({"file_path": "x.bin", "format_hint": "json"}), {})
        call_kwargs = orch.execute_skill.call_args.kwargs
        assert call_kwargs["format"] == "json"


# ---------------------------------------------------------------------------
# 3. performance_reviewer
# ---------------------------------------------------------------------------


class TestPerformanceReviewerFix:
    @pytest.mark.asyncio
    async def test_dict_bottlenecks_do_not_raise(self):
        """Dict-shaped skill output must not trigger KeyError slice."""
        stub = {"skill": "x", "operation": "y", "status": "ok", "data": {}}
        agent = PerformanceReviewerAgent(orchestrator=_orchestrator_returning(stub))
        result = await agent.execute(_task(), {})
        assert result["agent"] == "performance_reviewer"

    @pytest.mark.asyncio
    async def test_list_bottlenecks_slice_safely(self):
        """List bottlenecks produce a top-3 slice."""
        import sys

        print("PYTHON:", sys.version)

        async def skill(skill_name, operation, **kwargs):
            if skill_name == "py-spy":
                return [{"fn": f"f{i}"} for i in range(5)]
            return {"memory_leaks": []}

        orch = MagicMock()
        orch.execute_skill = AsyncMock(side_effect=skill)
        agent = PerformanceReviewerAgent(orchestrator=orch)
        result = await agent.execute(_task(), {})

        recs = result["data"]["recommendations"]
        perf = [r for r in recs if r["category"] == "performance"]
        assert len(perf) == 1
        assert len(perf[0]["top_bottlenecks"]) == 3

    def test_generate_recommendations_handles_dict_bottlenecks(self):
        """Direct call: dict bottlenecks must not raise KeyError."""
        agent = PerformanceReviewerAgent()
        # Should not raise; previously KeyError: slice(None, 3, None).
        recs = agent._generate_performance_recommendations(
            complexity={},
            bottlenecks={"some": "dict"},
            memory={"memory_leaks": []},
        )
        assert isinstance(recs, list)

    def test_generate_recommendations_handles_str_memory(self):
        """String memory output must not raise AttributeError."""
        agent = PerformanceReviewerAgent()
        recs = agent._generate_performance_recommendations(
            complexity={},
            bottlenecks=[],
            memory="not-a-dict",
        )
        assert isinstance(recs, list)
