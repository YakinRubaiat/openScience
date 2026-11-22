"""QIIME 2 skill: CLI wrapper plus pure-python TSV export parsing.

- ``run``             — execute ``qiime <args>`` via subprocess; clear
  RuntimeError when QIIME 2 is not installed
- ``import_data``     — convenience wrapper for ``qiime tools import``
- ``parse_tsv_export``— read a biom-converted TSV (feature table) into a
  dataframe summary (works without QIIME 2)
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _binary() -> str:
    exe = shutil.which("qiime")
    if exe is None:
        raise RuntimeError(
            "The 'qiime' binary was not found on PATH. QIIME 2 is distributed "
            "as a conda environment — see https://docs.qiime2.org and activate "
            "the environment so 'qiime' is on PATH."
        )
    return exe


def run_qiime(args=None, **kwargs: Any):
    kw = unwrap(kwargs)
    args = args if args is not None else kw.get("args")
    if not args:
        raise ValueError("qiime2.run requires 'args' (list after 'qiime')")
    exe = _binary()
    cmd = [exe] + [str(a) for a in args]
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


def import_data(input_path=None, output_path=None, type=None, **kwargs: Any):
    kw = unwrap(kwargs)
    input_path = input_path or kw.get("input_path")
    output_path = output_path or kw.get("output_path")
    type = type or kw.get("type")
    if not (input_path and output_path and type):
        raise ValueError("import_data requires 'input_path', 'output_path' and 'type'")
    exe = _binary()
    cmd = [
        exe, "tools", "import",
        "--type", str(type),
        "--input-path", str(input_path),
        "--output-path", str(output_path),
    ]
    if kw.get("input_format"):
        cmd += ["--input-format", str(kw["input_format"])]
    proc = subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=kw.get("cwd"), timeout=int(kw.get("timeout", 3600)),
    )
    return {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "ok": proc.returncode == 0,
    }


def parse_tsv_export(tsv_path=None, **kwargs: Any):
    """Parse a TSV exported from a .biom table (rows = features/OTUs)."""
    kw = unwrap(kwargs)
    p = tsv_path or kw.get("tsv_path") or kw.get("path")
    if p is None:
        raise ValueError("parse_tsv_export requires 'tsv_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"TSV export not found: {p}")
    # biom-converted tables start with a "#OTU ID" header, sometimes preceded
    # by a "# Constructed from biom file" comment line that must be skipped
    with p.open() as fh:
        first = fh.readline()
    skip = 1 if first.startswith("# Constructed") or (first.startswith("#") and "OTU" not in first) else 0
    df = pd.read_csv(p, sep="\t", index_col=0, skiprows=skip)
    numeric = df.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.dropna(axis=1, how="all")
    sample_sums = numeric.sum(axis=0)
    feature_counts = (numeric > 0).sum(axis=0)
    return {
        "path": str(p),
        "n_features": int(numeric.shape[0]),
        "n_samples": int(numeric.shape[1]),
        "sample_names": [str(c) for c in numeric.columns],
        "total_counts_per_sample": {str(k): float(v) for k, v in sample_sums.items()},
        "observed_features_per_sample": {str(k): int(v) for k, v in feature_counts.items()},
        "library_size_min": float(sample_sums.min()) if len(sample_sums) else 0.0,
        "library_size_max": float(sample_sums.max()) if len(sample_sums) else 0.0,
    }


def run(operation: str, **kwargs: Any):
    ops = {"run": run_qiime, "import_data": import_data, "parse_tsv_export": parse_tsv_export}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"qiime2: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("qiime2", run)
