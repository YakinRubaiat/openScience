"""CellProfiler skill: pipeline runner plus output parsing.

- ``run_pipeline``   — run ``cellprofiler`` in headless mode; clear
  RuntimeError when the binary is missing
- ``read_output_csv``— parse a CellProfiler objects/measurements CSV into
  per-image summary statistics (pure python)
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _binary() -> str:
    exe = shutil.which("cellprofiler")
    if exe is None:
        raise RuntimeError(
            "The 'cellprofiler' binary was not found on PATH. Install "
            "CellProfiler from https://cellprofiler.org and ensure "
            "'cellprofiler' is on PATH."
        )
    return exe


def run_pipeline(pipeline=None, output_dir=None, **kwargs: Any):
    kw = unwrap(kwargs)
    pipeline = pipeline or kw.get("pipeline") or kw.get("pipeline_path")
    if pipeline is None:
        raise ValueError("run_pipeline requires 'pipeline' (.cppipe path)")
    exe = _binary()
    cmd = [exe, "-c", "-r", "-p", str(pipeline)]
    out = output_dir or kw.get("output_dir")
    if out:
        cmd += ["-o", str(out)]
    if kw.get("images"):
        cmd += ["-i", str(kw["images"])]
    proc = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=kw.get("cwd"), timeout=int(kw.get("timeout", 86400)),
    )
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "ok": proc.returncode == 0,
    }


def read_output_csv(csv_path=None, group_by=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = csv_path or kw.get("csv_path") or kw.get("path")
    if p is None:
        raise ValueError("read_output_csv requires 'csv_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"Output CSV not found: {p}")
    df = pd.read_csv(p)
    numeric = df.select_dtypes(include="number")
    group_by = group_by or kw.get("group_by")
    if group_by is None and "ImageNumber" in df.columns:
        group_by = "ImageNumber"

    summary: dict[str, Any] = {
        "path": str(p),
        "n_rows": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
        "columns": [str(c) for c in df.columns][:100],
        "n_numeric_features": int(numeric.shape[1]),
    }
    if group_by is not None and group_by in df.columns:
        grouped = numeric.assign(_group=df[group_by]).groupby("_group")
        means = grouped.mean()
        counts = grouped.size()
        summary["group_by"] = str(group_by)
        summary["n_groups"] = int(counts.shape[0])
        summary["objects_per_group"] = {str(k): int(v) for k, v in counts.items()}
        # top-varying features
        if numeric.shape[1] > 1 and means.shape[0] > 1:
            var = means.var(axis=0).sort_values(ascending=False)
            top_feats = var.head(10).index
            summary["top_varying_features"] = [
                {"feature": str(f), "between_group_variance": float(var[f])} for f in top_feats
            ]
        summary["group_means_preview"] = means.round(6).head(10).to_dict()
    else:
        summary["feature_means"] = {
            str(c): float(v) for c, v in numeric.mean().head(20).items()
        }
    return summary


def run(operation: str, **kwargs: Any):
    ops = {"run_pipeline": run_pipeline, "read_output_csv": read_output_csv}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"cellprofiler: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("cellprofiler", run)
