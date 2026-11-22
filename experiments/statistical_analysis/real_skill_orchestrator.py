#!/usr/bin/env python
"""Orchestrator binding REAL skill implementations to openScience agents.

The stock ``AgentOrchestrator.execute_skill`` is a passthrough stub that echoes
its keyword arguments — agents return their inputs, not results. This subclass
dispatches skill names to real implementations backed by scipy/statsmodels/
lifelines/matplotlib.

Some agents request operations their domain skill doesn't own (e.g.
``matplotlib_stylist`` calls the ``matplotlib`` skill, ``abstract_writer``
calls ``scientific_writing``); the alias map handles that.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from openscience.core.orchestrator import AgentOrchestrator
from openscience.skills.statistics import lifelines_skill, scipy_stats_skill, statsmodels_skill
from openscience.skills.visualization import matplotlib_skill
from openscience.skills.writing import scientific_writing_skill


class RealSkillOrchestrator(AgentOrchestrator):
    """AgentOrchestrator with real (non-stub) skill dispatch."""

    SKILL_MODULES = {
        "statsmodels": statsmodels_skill,
        "numpy_stats": scipy_stats_skill,  # declared by power_analysis agent
        "scipy_stats": scipy_stats_skill,
        "lifelines": lifelines_skill,
        "survival_analysis": lifelines_skill,
        "matplotlib": matplotlib_skill,
        "style_sheets": matplotlib_skill,
        "scientific_writing": scientific_writing_skill,
        "text_summarization": scientific_writing_skill,
    }

    # Agent-requested operation -> real skill-module operation
    OPERATION_ALIASES = {
        ("statsmodels", "run"): "ttest",
        ("lifelines", "run"): "kaplan_meier",
        ("scientific_writing", "write_results"): "write_results",
    }

    def execute_skill(self, skill_name: str, operation: str, **kwargs: Any) -> Any:
        module = self.SKILL_MODULES.get(skill_name)
        if module is None:
            # Unknown skill: fall back to the stub so unknown agents don't crash.
            return {
                "skill": skill_name,
                "operation": operation,
                "status": "stub",
                "data": kwargs,
            }

        real_op = self.OPERATION_ALIASES.get((skill_name, operation), operation)
        try:
            data = module.run(real_op, **kwargs)
        except TypeError:
            # Some agents wrap their parameters; retry with the inner dict.
            inner = kwargs.get("parameters") or kwargs
            data = module.run(real_op, **inner)
        return {"skill": skill_name, "operation": real_op, "status": "ok", "data": data}
