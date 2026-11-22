"""VEP skill: CLI wrapper plus pure-python CSQ annotation parsing.

- ``run``                   — execute the ``vep`` CLI; clear RuntimeError when
  the binary is missing
- ``parse_vcf_annotations`` — parse VEP ``CSQ`` INFO sub-strings from an
  annotated VCF into tidy annotation records (works without VEP)
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _binary() -> str:
    exe = shutil.which("vep")
    if exe is None:
        raise RuntimeError(
            "The 'vep' binary was not found on PATH. Install Ensembl VEP from "
            "https://www.ensembl.org/info/docs/tools/vep (e.g. "
            "'conda install -c bioconda ensembl-vep') and ensure 'vep' is on PATH."
        )
    return exe


def run_vep(input_vcf=None, output_vcf=None, args=None, **kwargs: Any):
    kw = unwrap(kwargs)
    args = list(args or kw.get("args") or [])
    input_vcf = input_vcf or kw.get("input_vcf")
    output_vcf = output_vcf or kw.get("output_vcf")
    if input_vcf:
        args += ["-i", str(input_vcf)]
    if output_vcf:
        args += ["-o", str(output_vcf)]
    if not args:
        raise ValueError("vep.run requires 'args' and/or 'input_vcf'/'output_vcf'")
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


def _parse_csq_header(vcf_text_lines) -> list[str]:
    for line in vcf_text_lines:
        if line.startswith("##INFO=<ID=CSQ"):
            desc = line.split('Format: ', 1)[-1].rstrip('">\n')
            return desc.split("|")
    return []


def parse_vcf_annotations(vcf_path=None, max_records=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = vcf_path or kw.get("vcf_path") or kw.get("path")
    if p is None:
        raise ValueError("parse_vcf_annotations requires 'vcf_path'")
    vcf = Path(p)
    if not vcf.exists():
        raise FileNotFoundError(f"VCF not found: {vcf}")

    opener = open
    if vcf.suffix == ".gz":
        import gzip
        opener = gzip.open

    with opener(vcf, "rt") as fh:  # type: ignore[arg-type]
        lines = fh.read().splitlines()

    fields = _parse_csq_header(lines)
    consequences: dict[str, int] = {}
    genes: set[str] = set()
    records = []
    max_records = int(kw.get("max_records", max_records or 5000))
    n_variants_with_csq = 0

    for line in lines:
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        info = parts[7]
        csq = None
        for item in info.split(";"):
            if item.startswith("CSQ="):
                csq = item[4:]
                break
        if csq is None:
            continue
        n_variants_with_csq += 1
        for entry in csq.split(","):
            values = entry.split("|")
            ann = {fields[i]: values[i] for i in range(min(len(fields), len(values)))} if fields else {}
            if len(records) < max_records:
                records.append(
                    {
                        "chrom": parts[0],
                        "pos": int(parts[1]),
                        "ref": parts[3],
                        "alt": parts[4],
                        "gene": ann.get("Gene") or ann.get("SYMBOL") or "",
                        "symbol": ann.get("SYMBOL", ""),
                        "consequence": ann.get("Consequence", ""),
                        "impact": ann.get("IMPACT", ""),
                    }
                )
            cons = ann.get("Consequence", "")
            if cons:
                for c in cons.split("&"):
                    consequences[c] = consequences.get(c, 0) + 1
            sym = ann.get("SYMBOL") or ann.get("Gene")
            if sym:
                genes.add(sym)

    return {
        "vcf_path": str(vcf),
        "csq_fields": fields,
        "n_variants_with_csq": n_variants_with_csq,
        "n_annotations_returned": len(records),
        "n_unique_genes": len(genes),
        "consequence_counts": dict(sorted(consequences.items(), key=lambda kv: kv[1], reverse=True)),
        "annotations": records[: int(kw.get("return_limit", 200))],
    }


def run(operation: str, **kwargs: Any):
    ops = {"run": run_vep, "parse_vcf_annotations": parse_vcf_annotations}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"vep: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("vep", run)
