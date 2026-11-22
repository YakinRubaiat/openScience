"""HOMER motif-discovery skill.

- ``find_motifs``        — run ``findMotifsGenome.pl`` via subprocess; clear
  RuntimeError when HOMER is not installed
- ``parse_motif_results``— parse HOMER's ``knownResults.txt`` (or a homer
  motif HTML/TSV table) into ranked motif records (pure python)
"""

from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _binary(name: str = "findMotifsGenome.pl") -> str:
    exe = shutil.which(name)
    if exe is None:
        raise RuntimeError(
            f"The '{name}' binary (HOMER) was not found on PATH. Install HOMER "
            "from http://homer.ucsd.edu/homer/ and ensure its bin directory is on PATH."
        )
    return exe


def find_motifs(peaks=None, genome=None, output_dir=None, **kwargs: Any):
    kw = unwrap(kwargs)
    peaks = peaks or kw.get("peaks")
    genome = genome or kw.get("genome")
    output_dir = output_dir or kw.get("output_dir")
    if not (peaks and genome and output_dir):
        raise ValueError("find_motifs requires 'peaks', 'genome' and 'output_dir'")
    exe = _binary()
    cmd = [exe, str(peaks), str(genome), str(output_dir)]
    if kw.get("size"):
        cmd += ["-size", str(kw["size"])]
    if kw.get("n_motifs"):
        cmd += ["-S", str(kw["n_motifs"])]
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


def parse_motif_results(results_path=None, **kwargs: Any):
    """Parse HOMER knownResults.txt (tab-separated) into motif records."""
    kw = unwrap(kwargs)
    p = results_path or kw.get("results_path") or kw.get("path")
    if p is None:
        raise ValueError("parse_motif_results requires 'results_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"HOMER results not found: {p}")
    with p.open(newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        rows = list(reader)
    if not rows:
        raise ValueError(f"No motif rows parsed from {p}")

    def _f(row, *names):
        for n in names:
            for k in row:
                if k and k.strip().lower() == n:
                    try:
                        return float(str(row[k]).strip().rstrip("%"))
                    except ValueError:
                        return None
        return None

    motifs = []
    for row in rows:
        name = next(iter(row.values()), "")
        motifs.append(
            {
                "motif": str(name).strip(),
                "consensus": str(row.get("Consensus", "")).strip(),
                "p_value": _f(row, "p-value", "p_value") or 1.0,
                "log_p_value": _f(row, "log p-value", "log_p_value"),
                "q_value": _f(row, "q-value (benjamini)", "q-value", "q_value"),
                "target_percent": _f(row, "% of target sequences with motif", "target %", "% of targets"),
                "background_percent": _f(row, "% of background sequences with motif", "background %"),
            }
        )
    motifs.sort(key=lambda m: m["p_value"])
    return {
        "path": str(p),
        "n_motifs": len(motifs),
        "top_motifs": motifs[: int(kw.get("top", 25))],
        "best_motif": motifs[0]["motif"] if motifs else None,
    }


def run(operation: str, **kwargs: Any):
    ops = {"find_motifs": find_motifs, "parse_motif_results": parse_motif_results}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"homer: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("homer", run)
