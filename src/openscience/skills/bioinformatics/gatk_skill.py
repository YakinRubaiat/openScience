"""GATK skill: CLI wrapper plus pure-python VCF sanity validation.

- ``run``               — execute an arbitrary ``gatk`` subcommand; clear
  RuntimeError when the binary is missing
- ``haplotype_call``    — convenience wrapper for ``gatk HaplotypeCaller``
- ``index_validation``  — pure-python check that a VCF file and its index
  (.tbi/.idx) exist and that the VCF body parses (works without GATK)
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _binary() -> str:
    exe = shutil.which("gatk")
    if exe is None:
        raise RuntimeError(
            "The 'gatk' binary was not found on PATH. Install GATK from "
            "https://gatk.broadinstitute.org (e.g. 'conda install -c bioconda gatk4') "
            "and ensure 'gatk' is on PATH."
        )
    return exe


def run_gatk(args=None, **kwargs: Any):
    kw = unwrap(kwargs)
    args = args if args is not None else kw.get("args")
    if not args:
        raise ValueError("gatk.run requires 'args' (list of CLI arguments)")
    exe = _binary()
    cmd = [exe] + [str(a) for a in args]
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


def haplotype_call(reference=None, input_bam=None, output_vcf=None, **kwargs: Any):
    kw = unwrap(kwargs)
    reference = reference or kw.get("reference")
    input_bam = input_bam or kw.get("input_bam")
    output_vcf = output_vcf or kw.get("output_vcf")
    if not (reference and input_bam and output_vcf):
        raise ValueError("haplotype_call requires 'reference', 'input_bam', 'output_vcf'")
    exe = _binary()
    cmd = [
        exe, "HaplotypeCaller",
        "-R", str(reference),
        "-I", str(input_bam),
        "-O", str(output_vcf),
    ]
    if kw.get("intervals"):
        cmd += ["-L", str(kw["intervals"])]
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


def index_validation(vcf_path=None, **kwargs: Any):
    """Pure-python VCF + index sanity check (no GATK needed)."""
    kw = unwrap(kwargs)
    p = vcf_path or kw.get("vcf_path") or kw.get("path")
    if p is None:
        raise ValueError("index_validation requires 'vcf_path'")
    vcf = Path(p)
    if not vcf.exists():
        raise FileNotFoundError(f"VCF not found: {vcf}")

    gz = vcf.suffix == ".gz"
    opener = open
    if gz:
        import gzip
        opener = gzip.open
    n_variants = 0
    n_samples = 0
    contigs: list[str] = []
    n_header_lines = 0
    bad_lines: list[str] = []
    with opener(vcf, "rt") as fh:  # type: ignore[arg-type]
        for i, line in enumerate(fh):
            if line.startswith("##"):
                n_header_lines += 1
                if line.startswith("##contig=<ID="):
                    contigs.append(line.split("##contig=<ID=")[1].split(",")[0].split(">")[0])
                continue
            if line.startswith("#CHROM"):
                n_samples = max(len(line.rstrip("\n").split("\t")) - 9, 0)
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                bad_lines.append(f"line {i + 1}: only {len(parts)} columns")
                continue
            n_variants += 1
            if n_variants >= int(kw.get("max_variants", 100000)):
                break

    idx_candidates = [vcf.with_suffix(vcf.suffix + ".tbi"), vcf.with_suffix(vcf.suffix + ".idx")]
    index_path = next((c for c in idx_candidates if c.exists()), None)
    return {
        "vcf_path": str(vcf),
        "compressed": gz,
        "n_header_lines": n_header_lines,
        "n_variants_seen": n_variants,
        "n_samples": n_samples,
        "contigs": contigs[:50],
        "index_found": index_path is not None,
        "index_path": str(index_path) if index_path else None,
        "valid": not bad_lines,
        "problems": bad_lines[:10],
    }


def run(operation: str, **kwargs: Any):
    ops = {"run": run_gatk, "haplotype_call": haplotype_call, "index_validation": index_validation}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"gatk: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("gatk", run)
