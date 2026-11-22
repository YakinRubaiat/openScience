"""mitigation_planning skill: map risks to mitigation strategies.

Strategies: avoid, mitigate, transfer, accept. Sensible defaults based on
risk band, overridable per risk.

Operations: ``plan``, ``template``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

VALID_STRATEGIES = ("avoid", "mitigate", "transfer", "accept")


def _default_strategy(score: float) -> str:
    if score >= 15:
        return "avoid"
    if score >= 9:
        return "mitigate"
    if score >= 4:
        return "transfer"
    return "accept"


_DEFAULT_ACTIONS = {
    "avoid": "Redesign or re-scope to eliminate the risk entirely.",
    "mitigate": "Add controls, tests, or redundancy to reduce likelihood/impact.",
    "transfer": "Insure, outsource, or contractually shift the risk.",
    "accept": "Monitor; document acceptance rationale and revisit quarterly.",
}


def plan(risks: list, strategies: dict | None = None, **kwargs: Any) -> dict[str, Any]:
    """Assign a mitigation strategy to each risk.

    ``risks``: list of ``{name, likelihood, impact}`` (or pre-scored with
    a ``score`` field). ``strategies``: optional ``{name: strategy}`` map.
    """
    strategies = strategies or {}
    plan_items = []
    for i, risk in enumerate(risks, 1):
        name = risk.get("name", risk.get("risk", f"risk-{i}"))
        score = float(risk.get("score", float(risk.get("likelihood", 0))
                               * float(risk.get("impact", 0))))
        strategy = strategies.get(name) or _default_strategy(score)
        if strategy not in VALID_STRATEGIES:
            raise ValueError(f"Unknown strategy {strategy!r}; use {VALID_STRATEGIES}")
        plan_items.append({
            "id": risk.get("id", f"R{i}"), "name": name, "score": score,
            "strategy": strategy,
            "action": risk.get("action", _DEFAULT_ACTIONS[strategy]),
            "owner": risk.get("owner", "unassigned"),
        })
    plan_items.sort(key=lambda r: r["score"], reverse=True)
    by_strategy: dict[str, int] = {s: 0 for s in VALID_STRATEGIES}
    for item in plan_items:
        by_strategy[item["strategy"]] += 1
    return {"status": "ok", "n_items": len(plan_items),
            "by_strategy": by_strategy, "plan": plan_items}


def template(project: str = "Project", risks: list | None = None,
             **kwargs: Any) -> dict[str, Any]:
    """Markdown mitigation-plan template (optionally filled from a plan)."""
    lines = [f"# Mitigation Plan — {project}", "",
             "| ID | Risk | Score | Strategy | Action | Owner |",
             "|----|------|-------|----------|--------|-------|"]
    if risks:
        items = plan(risks)["plan"]
    else:
        items = [{"id": "R1", "name": "<risk>", "score": 0,
                  "strategy": "<avoid|mitigate|transfer|accept>",
                  "action": "<action>", "owner": "<owner>"}]
    for item in items:
        lines.append("| {id} | {name} | {score:.0f} | {strategy} | {action} | {owner} |"
                     .format(**item))
    lines += ["", "## Review Cadence", "",
              "- High risks: weekly review.", "- Medium: bi-weekly.", "- Low: monthly."]
    return {"status": "ok", "format": "markdown", "template": "\n".join(lines)}


run = skill_run({"plan": plan, "template": template})
register_skill("mitigation_planning", run)
