"""Run the 10 agent execution tests and emit EXPERIMENT_03_AGENTS.md.

This script executes each agent through the AgentOrchestrator with a
realistic task/context, measures wall-clock execution time, captures any
errors, and writes a Markdown report with the results.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

# Ensure src/ is on path when run from repo root
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openscience.core.orchestrator import AgentOrchestrator, Result

# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def _make_test_cases() -> list[dict[str, Any]]:
    """Build the 10 test specifications."""
    return [
        {
            "id": 1,
            "name": "Literature agent — pubmed_search",
            "agent": "pubmed_search",
            "description": "Search PubMed for single-cell RNA-seq batch effect papers",
            "parameters": {
                "query": "single-cell RNA-seq batch effect correction",
                "max_results": 10,
            },
            "context": {"user_id": "test-runner", "session": "exp03"},
        },
        {
            "id": 2,
            "name": "Experiment agent — power_analysis",
            "agent": "power_analysis",
            "description": "Compute required sample size for a two-group comparison",
            "parameters": {
                "effect_size": 0.5,
                "alpha": 0.05,
                "power": 0.8,
            },
            "context": {"study": "pilot_trial", "session": "exp03"},
        },
        {
            "id": 3,
            "name": "Data management agent — data_ingestor",
            "agent": "data_ingestor",
            "description": "Ingest a CSV expression matrix",
            "parameters": {
                "file_path": "/tmp/expression.csv",
                "format_hint": "csv",
            },
            "context": {"session": "exp03"},
        },
        {
            "id": 4,
            "name": "Analysis agent — qc_analyzer",
            "agent": "qc_analyzer",
            "description": "Run QC analysis on single-cell dataset",
            "parameters": {"data_type": "single_cell"},
            "context": {
                "session": "exp03",
                "data": {"n_cells": 1200, "n_genes": 20000},
            },
        },
        {
            "id": 5,
            "name": "Visualization agent — matplotlib_stylist",
            "agent": "matplotlib_stylist",
            "description": "Apply Nature-journal style to a figure",
            "parameters": {
                "figure": "<matplotlib.figure.Figure mock>",
                "style": "nature",
            },
            "context": {"session": "exp03"},
        },
        {
            "id": 6,
            "name": "Writing agent — abstract_writer",
            "agent": "abstract_writer",
            "description": "Draft an abstract for a single-cell study",
            "parameters": {
                "paper_content": (
                    "We applied scVI to integrate 1.2M PBMCs from 24 donors "
                    "across 3 batches and identified a novel CD14+ monocyte "
                    "subpopulation associated with severe COVID-19."
                ),
                "target_journal": "Nature",
                "word_limit": 200,
            },
            "context": {"session": "exp03"},
        },
        {
            "id": 7,
            "name": "Review agent — security_reviewer",
            "agent": "security_reviewer",
            "description": "Run security review on src/openscience",
            "parameters": {"target_path": "src/openscience/"},
            "context": {"session": "exp03"},
        },
        {
            "id": 8,
            "name": "Review agent — code_quality_reviewer",
            "agent": "code_quality_reviewer",
            "description": "Run code-quality review on src/openscience",
            "parameters": {"target_path": "src/openscience/"},
            "context": {"session": "exp03"},
        },
        {
            "id": 9,
            "name": "Agent chaining — pubmed_search → qc_analyzer → abstract_writer",
            "agent": None,  # multi-agent chain
            "description": "Chain: search literature → run QC → draft abstract",
            "params_chain": [
                ("pubmed_search", {"query": "scRNA-seq batch correction", "max_results": 5}, {}),
                (
                    "qc_analyzer",
                    {"data_type": "single_cell"},
                    {"data": {"n_cells": 5000, "n_genes": 18000}},
                ),
                (
                    "abstract_writer",
                    {
                        "paper_content": "Results from integrated scRNA-seq analysis.",
                        "target_journal": "Cell",
                        "word_limit": 150,
                    },
                    {},
                ),
            ],
        },
        {
            "id": 10,
            "name": "Concurrent agent execution — 4 agents in parallel",
            "agent": None,  # concurrent batch
            "description": (
                "Run pubmed_search, qc_analyzer, matplotlib_stylist, "
                "code_quality_reviewer concurrently via asyncio.gather"
            ),
            "params_batch": [
                ("pubmed_search", {"query": "spatial transcriptomics", "max_results": 3}, {}),
                ("qc_analyzer", {"data_type": "single_cell"}, {"data": {"n_cells": 8000}}),
                ("matplotlib_stylist", {"figure": "<fig>", "style": "nature"}, {}),
                ("code_quality_reviewer", {"target_path": "src/openscience/"}, {}),
            ],
        },
    ]


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------


def _summarize_result(result: Result, max_len: int = 200) -> str:
    """Produce a short, human-readable summary of an agent Result."""
    try:
        s = json.dumps(result.data, default=str)[:max_len]
    except Exception:
        s = str(result.data)[:max_len]
    return s


def _validate_result_structure(result: Result) -> dict[str, bool]:
    """Check that a Result has the expected fields."""
    return {
        "is_result": isinstance(result, Result),
        "has_data": hasattr(result, "data"),
        "has_metadata": isinstance(result.metadata, dict),
        "has_artifacts": isinstance(result.artifacts, list),
    }


async def _run_single_agent(
    orchestrator: AgentOrchestrator, case: dict[str, Any]
) -> dict[str, Any]:
    """Run a single-agent test (cases 1–8)."""
    started = time.perf_counter()
    error: str | None = None
    result: Result | None = None
    checks: dict[str, bool] = {}

    try:
        result = await asyncio.to_thread(
            orchestrator.execute_agent,
            case["agent"],
            case.get("parameters", {}),
            case.get("context", {}),
        )
        checks = _validate_result_structure(result)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        error += "\n" + traceback.format_exc(limit=4)

    elapsed = time.perf_counter() - started
    return {
        "case": case,
        "elapsed_s": elapsed,
        "error": error,
        "result": result,
        "summary": _summarize_result(result) if result else None,
        "checks": checks,
    }


async def _run_chain(orchestrator: AgentOrchestrator, case: dict[str, Any]) -> dict[str, Any]:
    """Run a sequential agent chain (case 9)."""
    started = time.perf_counter()
    error: str | None = None
    steps: list[dict[str, Any]] = []
    carry_over: dict[str, Any] = {}

    try:
        for agent_name, params, ctx in case["params_chain"]:
            merged_ctx = {**ctx, **carry_over}
            step_start = time.perf_counter()
            res = await asyncio.to_thread(
                orchestrator.execute_agent, agent_name, params, merged_ctx
            )
            steps.append(
                {
                    "agent": agent_name,
                    "elapsed_s": time.perf_counter() - step_start,
                    "result": res,
                    "summary": _summarize_result(res),
                }
            )
            # Propagate something from this step to the next
            carry_over["previous_agent"] = agent_name
            carry_over["previous_output"] = _summarize_result(res, max_len=80)
        checks = {
            "steps_completed": len(steps) == len(case["params_chain"]),
            "all_results_valid": all(isinstance(s["result"], Result) for s in steps),
        }
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        error += "\n" + traceback.format_exc(limit=4)
        checks = {"steps_completed": False, "all_results_valid": False}

    return {
        "case": case,
        "elapsed_s": time.perf_counter() - started,
        "error": error,
        "steps": steps,
        "checks": checks,
    }


async def _run_concurrent(orchestrator: AgentOrchestrator, case: dict[str, Any]) -> dict[str, Any]:
    """Run multiple agents concurrently (case 10)."""
    started = time.perf_counter()
    error: str | None = None
    steps: list[dict[str, Any]] = []

    async def _one(agent_name: str, params: dict, ctx: dict) -> dict[str, Any]:
        step_start = time.perf_counter()
        try:
            res = await asyncio.to_thread(orchestrator.execute_agent, agent_name, params, ctx)
            return {
                "agent": agent_name,
                "elapsed_s": time.perf_counter() - step_start,
                "result": res,
                "summary": _summarize_result(res),
                "error": None,
            }
        except Exception as exc:
            return {
                "agent": agent_name,
                "elapsed_s": time.perf_counter() - step_start,
                "result": None,
                "summary": None,
                "error": f"{type(exc).__name__}: {exc}",
            }

    try:
        steps = await asyncio.gather(*(_one(a, p, c) for a, p, c in case["params_batch"]))
        checks = {
            "all_succeeded": all(s["error"] is None for s in steps),
            "all_results_valid": all(isinstance(s["result"], Result) for s in steps),
            "count": len(steps),
        }
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        error += "\n" + traceback.format_exc(limit=4)
        checks = {"all_succeeded": False, "all_results_valid": False}

    return {
        "case": case,
        "elapsed_s": time.perf_counter() - started,
        "error": error,
        "steps": steps,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _write_report(out_path: Path, results: list[dict[str, Any]], total_s: float) -> None:
    """Write EXPERIMENT_03_AGENTS.md."""
    lines: list[str] = []
    lines.append("# Experiment 03 — Agent Execution Tests\n")
    lines.append("")
    lines.append("**Date:** 2026-11-22\n")
    lines.append(f"**Total runtime:** {total_s:.2f} s\n")
    lines.append(f"**Tests run:** {len(results)}\n")
    passed = sum(1 for r in results if r["error"] is None)
    lines.append(f"**Passed:** {passed}/{len(results)}\n")
    lines.append("")
    lines.append("## Summary Table\n")
    lines.append("")
    lines.append("| # | Test | Agent(s) | Time (s) | Status |")
    lines.append("|---|------|----------|---------:|--------|")
    for r in results:
        case = r["case"]
        if case["agent"]:
            agents = f"`{case['agent']}`"
        else:
            if "params_chain" in case:
                agents = " → ".join(f"`{a}`" for a, _, _ in case["params_chain"])
            else:
                agents = ", ".join(f"`{a}`" for a, _, _ in case["params_batch"])
        status = "❌ FAIL" if r["error"] else "✅ PASS"
        lines.append(
            f"| {case['id']} | {case['name']} | {agents} | " f"{r['elapsed_s']:.3f} | {status} |"
        )
    lines.append("")
    lines.append("---\n")

    for r in results:
        case = r["case"]
        lines.append(f"## Test {case['id']}: {case['name']}\n")
        lines.append("")
        lines.append(f"**Description:** {case['description']}\n")

        if case["agent"]:
            lines.append("**Parameters:**")
            lines.append("```json")
            lines.append(json.dumps(case.get("parameters", {}), indent=2, default=str))
            lines.append("```")
            lines.append("")
            lines.append("**Context:**")
            lines.append("```json")
            lines.append(json.dumps(case.get("context", {}), indent=2, default=str))
            lines.append("```")
            lines.append("")

        lines.append(f"**Execution time:** {r['elapsed_s']:.3f} s\n")

        if r["error"]:
            lines.append("**Status:** ❌ **FAILED**\n")
            lines.append("**Error:**")
            lines.append("```")
            lines.append(r["error"])
            lines.append("```")
        else:
            lines.append("**Status:** ✅ **PASSED**\n")
            lines.append("**Structure validation:**")
            for k, v in r["checks"].items():
                mark = "✅" if v else "❌"
                lines.append(f"- {mark} `{k}`: {v}")

            if "steps" in r:
                lines.append("")
                lines.append("**Steps:**")
                for s in r["steps"]:
                    err = f" — ❌ {s['error']}" if s.get("error") else ""
                    lines.append(
                        f"1. `{s['agent']}` ({s['elapsed_s']:.3f}s){err}\n"
                        f"   - Result summary: `{s['summary']}`"
                    )
            else:
                lines.append("")
                lines.append("**Result summary:**")
                lines.append("```json")
                lines.append(str(r["summary"]))
                lines.append("```")

        lines.append("")
        lines.append("---\n")

    lines.append("## Notes\n")
    lines.append("")
    lines.append(
        "- Tests 1–8 exercise one agent each via `AgentOrchestrator.execute_agent().`\n"
        "- Test 9 chains three agents sequentially, propagating each result's\n"
        "  summary into the next agent's context.\n"
        "- Test 10 runs four agents in parallel using `asyncio.gather()`.\n"
        "- Skills are provided by the orchestrator's default stub executor,\n"
        "  so return values are deterministic `{skill, operation, status, data}`\n"
        "  envelopes. Real tool bindings can be installed by subclassing\n"
        "  `AgentOrchestrator.execute_skill()`.\n"
    )

    out_path.write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def _main() -> int:
    orchestrator = AgentOrchestrator()
    tests = _make_test_cases()
    started = time.perf_counter()
    results: list[dict[str, Any]] = []

    for case in tests:
        print(f"→ Running test {case['id']}: {case['name']}", flush=True)
        if case["agent"]:
            r = await _run_single_agent(orchestrator, case)
        elif "params_chain" in case:
            r = await _run_chain(orchestrator, case)
        else:
            r = await _run_concurrent(orchestrator, case)
        results.append(r)
        status = "✅" if r["error"] is None else "❌"
        print(f"  {status} {r['elapsed_s']:.3f}s", flush=True)

    total_s = time.perf_counter() - started

    out_path = ROOT / "tests" / "integration" / "EXPERIMENT_03_AGENTS.md"
    _write_report(out_path, results, total_s)
    print(f"\nWrote report → {out_path}")

    return 0 if all(r["error"] is None for r in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
