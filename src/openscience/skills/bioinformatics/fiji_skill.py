"""Fiji/ImageJ skill: macro runner plus measurement-table parsing.

- ``run_macro``     — run ``ImageJ``/``fiji`` headless with a macro; clear
  RuntimeError when the binary is missing
- ``measure_table`` — parse an ImageJ measurement CSV/TSV (Results table)
  into summary statistics (pure python)
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
    for name in ("fiji", "ImageJ", "imagej", "Fiji"):
        exe = shutil.which(name)
        if exe is not None:
            return exe
    raise RuntimeError(
        "No Fiji/ImageJ binary found on PATH. Install Fiji from "
        "https://fiji.sc and make the 'fiji' (or 'ImageJ') launcher available "
        "on PATH."
    )


def run_macro(macro=None, args=None, **kwargs: Any):
    kw = unwrap(kwargs)
    macro = macro or kw.get("macro") or kw.get("macro_path")
    if macro is None:
        raise ValueError("run_macro requires 'macro' (path or macro text)")
    exe = _binary()
    macro_text = kw.get("macro_text")
    cmd = [exe, "--headless", "--console"]
    if macro_text:
        cmd += ["-macro", str(macro_text)]
    else:
        cmd += ["-macro", str(macro)]
    extra = args if args is not None else kw.get("args")
    if extra:
        cmd += [str(a) for a in (extra if isinstance(extra, (list, tuple)) else [extra])]
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


def measure_table(csv_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = csv_path or kw.get("csv_path") or kw.get("path")
    if p is None:
        raise ValueError("measure_table requires 'csv_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"Measurements file not found: {p}")
    sep = "\t" if p.suffix.lower() in (".tsv", ".txt") else ","
    df = pd.read_csv(p, sep=sep)
    numeric = df.select_dtypes(include="number")
    preferred = [c for c in ("Area", "Mean", "Min", "Max", "IntDen", "RawIntDen", "Perim.") if c in numeric.columns]
    stats = {}
    for c in preferred or list(numeric.columns)[:10]:
        col = numeric[c]
        stats[str(c)] = {
            "mean": float(col.mean()),
            "sd": float(col.std(ddof=1)) if len(col) > 1 else 0.0,
            "min": float(col.min()),
            "max": float(col.max()),
        }
    return {
        "path": str(p),
        "n_measurements": int(df.shape[0]),
        "columns": [str(c) for c in df.columns],
        "stats": stats,
        "total_area": float(numeric["Area"].sum()) if "Area" in numeric.columns else None,
    }


def run(operation: str, **kwargs: Any):
    ops = {"run_macro": run_macro, "measure_table": measure_table}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"fiji: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("fiji", run)
