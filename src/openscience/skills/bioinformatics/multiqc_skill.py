"""MultiQC-style aggregation skill.

MultiQC aggregates QC outputs from many tools into one report. This skill
provides the pure-python core:

- ``aggregate``        — merge per-file QC dicts (or JSON files) into one
  tidy summary table
- ``report_dataframe`` — pivot the merged metrics into a samples x metrics
  table (returned as records, optionally written to CSV)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _load_qc_dicts(samples=None, json_files=None) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    if samples:
        for name, qc in samples.items():
            merged[str(name)] = dict(qc)
    if json_files:
        for f in json_files:
            p = Path(f)
            if not p.exists():
                raise FileNotFoundError(f"QC JSON not found: {p}")
            data = json.loads(p.read_text())
            if isinstance(data, dict):
                merged[p.stem] = data
    if not merged:
        raise ValueError("Provide 'samples' (dict of dicts) and/or 'json_files'")
    return merged


def aggregate(samples=None, json_files=None, **kwargs: Any):
    kw = unwrap(kwargs)
    merged = _load_qc_dicts(
        samples if samples is not None else kw.get("samples"),
        json_files if json_files is not None else kw.get("json_files"),
    )
    rows = []
    for name, qc in merged.items():
        numeric = {k: v for k, v in qc.items() if isinstance(v, (int, float))}
        rows.append({"sample": name, "n_metrics": len(numeric), "metrics": numeric})
    return {
        "n_samples": len(rows),
        "samples": rows,
        "sample_names": [r["sample"] for r in rows],
    }


def report_dataframe(samples=None, json_files=None, output_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    merged = _load_qc_dicts(
        samples if samples is not None else kw.get("samples"),
        json_files if json_files is not None else kw.get("json_files"),
    )
    df = pd.DataFrame.from_dict(
        {
            name: {k: v for k, v in qc.items() if isinstance(v, (int, float))}
            for name, qc in merged.items()
        },
        orient="index",
    )
    df.index.name = "sample"
    df = df.sort_index()
    out = output_path or kw.get("output_path")
    if out:
        df.reset_index().to_csv(out, index=False)
    return {
        "n_samples": int(df.shape[0]),
        "n_metrics": int(df.shape[1]),
        "metrics": [str(c) for c in df.columns],
        "table": df.reset_index().to_dict(orient="records"),
        "output_path": out,
    }


def run(operation: str, **kwargs: Any):
    ops = {"aggregate": aggregate, "report_dataframe": report_dataframe}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"multiqc: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("multiqc", run)
