"""Cell Ranger skill: CLI wrapper plus pure-python metrics parsing.

- ``count``             — run ``cellranger count`` via subprocess; raises a
  clear RuntimeError when the binary is not installed.
- ``summarize_metrics`` — parse a Cell Ranger ``metrics_summary.csv`` file
  into a plain dict (works without the binary).
"""

from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _binary() -> str:
    exe = shutil.which("cellranger")
    if exe is None:
        raise RuntimeError(
            "The 'cellranger' binary was not found on PATH. Cell Ranger is "
            "proprietary 10x Genomics software — install it from "
            "https://www.10xgenomics.com/support/software/cell-ranger and "
            "ensure 'cellranger' is on PATH."
        )
    return exe


def count(**kwargs: Any):
    kw = unwrap(kwargs)
    sample_id = kw.get("id") or kw.get("sample_id")
    transcriptome = kw.get("transcriptome")
    fastqs = kw.get("fastqs")
    if not (sample_id and transcriptome and fastqs):
        raise ValueError("cellranger.count requires 'id', 'transcriptome' and 'fastqs'")
    exe = _binary()
    cmd = [exe, "count", f"--id={sample_id}", f"--transcriptome={transcriptome}", f"--fastqs={fastqs}"]
    if kw.get("sample"):
        cmd.append(f"--sample={kw['sample']}")
    if kw.get("expect_cells"):
        cmd.append(f"--expect-cells={int(kw['expect_cells'])}")
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=kw.get("cwd"),
        timeout=int(kw.get("timeout", 86400)),
    )
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "ok": proc.returncode == 0,
    }


def summarize_metrics(metrics_path=None, path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = metrics_path or path or kw.get("metrics_path") or kw.get("path")
    if p is None:
        raise ValueError("summarize_metrics requires 'metrics_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"metrics_summary file not found: {p}")
    with p.open(newline="") as fh:
        rows = list(csv.reader(fh))
    if len(rows) < 2:
        raise ValueError(f"Malformed metrics summary (expected header + 1 row): {p}")
    header, values = rows[0], rows[1]
    metrics = {}
    for k, v in zip(header, values):
        v2 = v.strip().rstrip("%")
        try:
            metrics[k.strip()] = float(v2.replace(",", ""))
        except ValueError:
            metrics[k.strip()] = v.strip()
    estimated = metrics.get("Estimated Number of Cells")
    mean_reads = metrics.get("Mean Reads per Cell")
    median_genes = metrics.get("Median Genes per Cell")
    return {
        "path": str(p),
        "n_metrics": len(metrics),
        "metrics": metrics,
        "estimated_cells": estimated,
        "mean_reads_per_cell": mean_reads,
        "median_genes_per_cell": median_genes,
    }


def run(operation: str, **kwargs: Any):
    ops = {"count": count, "summarize_metrics": summarize_metrics}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"cellranger: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("cellranger", run)
