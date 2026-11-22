"""risk_analysis skill: likelihood x impact risk scoring (pure python).

Scores risks on a likelihood*impact matrix, ranks them, and lists which
ones require mitigation.

Operations: ``score_risks``, ``top_risks``, ``mitigation_required``.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

_DEFAULT_THRESHOLD = 9.0  # e.g. 3x3 on a 5x5 scale


def _score_one(risk: dict[str, Any], index: int) -> dict[str, Any]:
    likelihood = float(risk.get("likelihood", 0))
    impact = float(risk.get("impact", 0))
    score = likelihood * impact
    if score >= 15:
        band = "high"
    elif score >= _DEFAULT_THRESHOLD:
        band = "medium"
    else:
        band = "low"
    return {"id": risk.get("id", f"R{index}"),
            "name": risk.get("name", risk.get("risk", f"risk-{index}")),
            "likelihood": likelihood, "impact": impact,
            "score": score, "band": band}


def score_risks(risks: list, **kwargs: Any) -> dict[str, Any]:
    """Score each risk as likelihood*impact and assign a band."""
    if not isinstance(risks, list):
        raise ValueError("'risks' must be a list of {name, likelihood, impact} dicts")
    scored = [_score_one(r, i + 1) for i, r in enumerate(risks)]
    scored.sort(key=lambda r: r["score"], reverse=True)
    return {"status": "ok", "n_risks": len(scored), "risks": scored}


def top_risks(risks: list, n: int = 5, **kwargs: Any) -> dict[str, Any]:
    """The ``n`` highest-scoring risks."""
    scored = score_risks(risks)["risks"]
    return {"status": "ok", "n": min(int(n), len(scored)), "top": scored[: int(n)]}


def mitigation_required(risks: list, threshold: float = _DEFAULT_THRESHOLD,
                        **kwargs: Any) -> dict[str, Any]:
    """Risks whose score meets/exceeds ``threshold`` (need mitigation)."""
    scored = score_risks(risks)["risks"]
    required = [r for r in scored if r["score"] >= float(threshold)]
    return {"status": "ok", "threshold": float(threshold),
            "n_requiring_mitigation": len(required), "risks": required}


run = skill_run({"score_risks": score_risks, "top_risks": top_risks,
                 "mitigation_required": mitigation_required})
register_skill("risk_analysis", run)
