"""Flow-cytometry gating skill operating on event-level dataframes.

Operations
----------
- ``rectangle_gate``       — keep events inside channel min/max ranges
- ``percentage_positive``  — fraction of events above channel thresholds
- ``gate_tree_apply``      — apply a list of gates sequentially, reporting
  the surviving fraction per gate

These operate purely on dataframes of event intensities; FCS file I/O and
flowcore/flowjo wrappers belong to the bioinformatics skill family.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import skill_run, unwrap


def _get_df(kw: dict[str, Any]) -> pd.DataFrame:
    if "dataframe" in kw:
        return pd.DataFrame(kw["dataframe"])
    if "records" in kw:
        return pd.DataFrame(kw["records"])
    raise ValueError("Provide 'dataframe' (dict of columns) or 'records' (list of rows)")


def rectangle_gate(**kwargs: Any) -> dict[str, Any]:
    """Keep events within per-channel [min, max] ranges.

    Parameters: ``dataframe``/``records``; ``gates`` mapping channel name to
    ``{"min": …, "max": …}`` (either bound may be null/omitted).
    """
    kw = unwrap(kwargs)
    df = _get_df(kw)
    gates = kw.get("gates") or {}

    mask = np.ones(len(df), dtype=bool)
    applied: dict[str, Any] = {}
    for channel, bounds in gates.items():
        if channel not in df.columns:
            raise ValueError(f"Gate channel {channel!r} not in dataframe columns")
        lo = bounds.get("min")
        hi = bounds.get("max")
        vals = df[channel].to_numpy(dtype=float)
        m = np.ones(len(df), dtype=bool)
        if lo is not None:
            m &= vals >= float(lo)
        if hi is not None:
            m &= vals <= float(hi)
        mask &= m
        applied[channel] = {"min": lo, "max": hi}

    kept = df.loc[mask]
    n_in, n_kept = len(df), len(kept)
    return {
        "n_input": int(n_in),
        "n_kept": int(n_kept),
        "fraction_kept": float(n_kept / n_in) if n_in else 0.0,
        "gates": applied,
        "records": kept.to_dict(orient="records"),
    }


def percentage_positive(**kwargs: Any) -> dict[str, Any]:
    """Fraction of events above (or below) a threshold per channel.

    Parameters: ``dataframe``/``records``; ``thresholds`` mapping channel to
    numeric threshold; ``direction`` ``"above"`` (default) or ``"below"``.
    """
    kw = unwrap(kwargs)
    df = _get_df(kw)
    thresholds = kw.get("thresholds") or {}
    direction = kw.get("direction", "above")
    if direction not in ("above", "below"):
        raise ValueError("direction must be 'above' or 'below'")

    n = len(df)
    results: dict[str, Any] = {}
    for channel, thr in thresholds.items():
        if channel not in df.columns:
            raise ValueError(f"Channel {channel!r} not in dataframe columns")
        vals = df[channel].to_numpy(dtype=float)
        if direction == "above":
            pos = int(np.sum(vals > float(thr)))
        else:
            pos = int(np.sum(vals < float(thr)))
        results[channel] = {
            "threshold": float(thr),
            "n_positive": pos,
            "pct_positive": float(100.0 * pos / n) if n else 0.0,
        }
    return {"n_total": int(n), "direction": direction, "channels": results}


def gate_tree_apply(**kwargs: Any) -> dict[str, Any]:
    """Apply a named list of gates sequentially and report each step.

    Parameters: ``dataframe``/``records``; ``gates`` — list of
    ``{"name": …, "type": "rectangle"|"threshold", ...}``:
      - rectangle: ``{"channel": …, "min": …, "max": …}``
      - threshold: ``{"channel": …, "threshold": …, "direction": "above"|"below"}``
    """
    kw = unwrap(kwargs)
    df = _get_df(kw)
    gates = kw.get("gates") or []
    if not gates:
        raise ValueError("Provide a non-empty 'gates' list")

    current = df
    n_start = len(df)
    steps: list[dict[str, Any]] = []
    for i, gate in enumerate(gates):
        gtype = gate.get("type", "rectangle")
        name = gate.get("name") or f"gate_{i}"
        channel = gate.get("channel")
        if channel not in current.columns:
            raise ValueError(f"Gate {name!r}: channel {channel!r} not in columns")
        vals = current[channel].to_numpy(dtype=float)
        if gtype == "rectangle":
            lo = gate.get("min")
            hi = gate.get("max")
            mask = np.ones(len(current), dtype=bool)
            if lo is not None:
                mask &= vals >= float(lo)
            if hi is not None:
                mask &= vals <= float(hi)
        elif gtype == "threshold":
            thr = float(gate["threshold"])
            if gate.get("direction", "above") == "above":
                mask = vals > thr
            else:
                mask = vals < thr
        else:
            raise ValueError(f"Unknown gate type {gtype!r}")

        before = len(current)
        current = current.loc[mask]
        steps.append(
            {
                "name": name,
                "type": gtype,
                "n_before": int(before),
                "n_after": int(len(current)),
                "fraction_of_previous": float(len(current) / before) if before else 0.0,
                "fraction_of_total": float(len(current) / n_start) if n_start else 0.0,
            }
        )

    return {
        "n_start": int(n_start),
        "n_final": int(len(current)),
        "fraction_of_total": float(len(current) / n_start) if n_start else 0.0,
        "steps": steps,
        "records": current.to_dict(orient="records"),
    }


run = skill_run(
    {
        "rectangle_gate": rectangle_gate,
        "percentage_positive": percentage_positive,
        "gate_tree_apply": gate_tree_apply,
    }
)

register_skill("flow_gating", run)
