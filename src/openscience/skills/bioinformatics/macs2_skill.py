"""MACS2 skill: peak-calling CLI wrapper plus pure-python peak utilities.

- ``callpeak``       — run ``macs2 callpeak`` via subprocess; clear
  RuntimeError when the binary is missing
- ``parse_peaks``    — read a .narrowPeak/.broadPeak file into peak records
- ``summit_overlap`` — pure-python interval overlap between two peak sets
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap

_NARROWPEAK_COLS = [
    "chrom", "start", "end", "name", "score",
    "strand", "signal_value", "p_value", "q_value", "summit_offset",
]


def _binary() -> str:
    exe = shutil.which("macs2")
    if exe is None:
        raise RuntimeError(
            "The 'macs2' binary was not found on PATH. Install it with "
            "'pip install MACS2' or 'conda install -c bioconda macs2'."
        )
    return exe


def callpeak(treatment=None, control=None, name=None, format=None, genome_size=None, **kwargs: Any):
    kw = unwrap(kwargs)
    treatment = treatment or kw.get("treatment")
    if treatment is None:
        raise ValueError("callpeak requires 'treatment' (BAM/BED path)")
    exe = _binary()
    cmd = [exe, "callpeak", "-t", str(treatment)]
    control = control or kw.get("control")
    if control:
        cmd += ["-c", str(control)]
    name = name or kw.get("name") or "macs2_run"
    cmd += ["-n", str(name)]
    fmt = format or kw.get("format")
    if fmt:
        cmd += ["-f", str(fmt)]
    gs = genome_size or kw.get("genome_size") or kw.get("gsize")
    if gs:
        cmd += ["-g", str(gs)]
    if kw.get("outdir"):
        cmd += ["--outdir", str(kw["outdir"])]
    if kw.get("qvalue") is not None:
        cmd += ["-q", str(kw["qvalue"])]
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


def parse_peaks(peaks_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = peaks_path or kw.get("peaks_path") or kw.get("path")
    if p is None:
        raise ValueError("parse_peaks requires 'peaks_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"Peak file not found: {p}")
    df = pd.read_csv(p, sep="\t", header=None, comment="#")
    df = df.dropna(axis=1, how="all")
    cols = _NARROWPEAK_COLS[: df.shape[1]]
    df.columns = cols
    for c in ("start", "end"):
        df[c] = df[c].astype(int)
    widths = df["end"] - df["start"]
    out = kw.get("output_path")
    if out:
        df.to_csv(out, index=False)
    return {
        "path": str(p),
        "n_peaks": int(df.shape[0]),
        "columns": list(df.columns),
        "mean_width": float(widths.mean()),
        "median_width": float(widths.median()),
        "total_coverage_bp": int(widths.sum()),
        "chroms": sorted(df["chrom"].astype(str).unique().tolist()),
        "peaks": df.head(int(kw.get("top", 100))).to_dict(orient="records"),
        "output_path": out,
    }


def _intervals(peaks) -> pd.DataFrame:
    df = pd.DataFrame(peaks)
    need = {"chrom", "start", "end"}
    if not need.issubset(df.columns):
        raise ValueError(f"Peaks need columns {need}, got {list(df.columns)}")
    return df[["chrom", "start", "end"]].astype({"start": int, "end": int})


def summit_overlap(peaks_a=None, peaks_b=None, max_distance: int | None = None, **kwargs: Any):
    """Count A/B peaks whose intervals overlap (or are within max_distance)."""
    kw = unwrap(kwargs)
    a = _intervals(peaks_a if peaks_a is not None else kw.get("peaks_a"))
    b = _intervals(peaks_b if peaks_b is not None else kw.get("peaks_b"))
    max_distance = int(kw.get("max_distance", max_distance if max_distance is not None else 0))

    b_by_chrom: dict[str, list[tuple[int, int]]] = {}
    for chrom, start, end in b.itertuples(index=False):
        b_by_chrom.setdefault(str(chrom), []).append((int(start), int(end)))
    for v in b_by_chrom.values():
        v.sort()

    n_overlap = 0
    overlaps = []
    for chrom, start, end in a.itertuples(index=False):
        chrom = str(chrom)
        lo, hi = int(start) - max_distance, int(end) + max_distance
        hit = False
        for bs, be in b_by_chrom.get(chrom, []):
            if bs > hi:
                break
            if be >= lo:
                hit = True
                if len(overlaps) < 100:
                    overlaps.append({"chrom": chrom, "a_start": int(start), "a_end": int(end), "b_start": bs, "b_end": be})
                break
        n_overlap += int(hit)

    return {
        "n_peaks_a": int(a.shape[0]),
        "n_peaks_b": int(b.shape[0]),
        "max_distance": max_distance,
        "n_overlapping_a": int(n_overlap),
        "fraction_a_overlapping": float(n_overlap / max(a.shape[0], 1)),
        "examples": overlaps,
    }


def run(operation: str, **kwargs: Any):
    ops = {"callpeak": callpeak, "parse_peaks": parse_peaks, "summit_overlap": summit_overlap}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"macs2: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("macs2", run)
