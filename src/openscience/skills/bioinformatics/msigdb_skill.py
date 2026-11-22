"""MSigDB gene-set skill: parse and filter .gmt files.

- ``load_gmt``        — parse a .gmt file into ``{name: {"description": ...,
  "genes": [...]}}`` plus a flat ``gene_sets`` mapping
- ``filter_gene_sets``— filter gene sets by size and/or member genes
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def load_gmt(gmt_path=None, path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = gmt_path or path or kw.get("gmt_path") or kw.get("path")
    if p is None:
        raise ValueError("load_gmt requires 'gmt_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"GMT file not found: {p}")
    gene_sets: dict[str, dict] = {}
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        name, desc = parts[0], (parts[1] if len(parts) > 1 else "")
        genes = [g for g in parts[2:] if g]
        gene_sets[name] = {"description": desc, "genes": genes}
    if not gene_sets:
        raise ValueError(f"No gene sets parsed from {p}")
    sizes = [len(v["genes"]) for v in gene_sets.values()]
    return {
        "path": str(p),
        "n_gene_sets": len(gene_sets),
        "gene_sets": {k: v["genes"] for k, v in gene_sets.items()},
        "descriptions": {k: v["description"] for k, v in gene_sets.items()},
        "min_size": min(sizes),
        "max_size": max(sizes),
        "example_names": list(gene_sets)[:10],
    }


def filter_gene_sets(gene_sets=None, min_size: int | None = None, max_size: int | None = None, genes=None, **kwargs: Any):
    kw = unwrap(kwargs)
    gene_sets = gene_sets if gene_sets is not None else kw.get("gene_sets")
    if gene_sets is None:
        raise ValueError("filter_gene_sets requires 'gene_sets' (dict of lists)")
    min_size = int(kw.get("min_size", min_size if min_size is not None else 0))
    max_size = int(kw.get("max_size", max_size if max_size is not None else 10**9))
    required = {str(g) for g in (genes if genes is not None else kw.get("genes") or [])}

    kept = {}
    for name, gs in gene_sets.items():
        gs_list = [str(g) for g in gs]
        if not (min_size <= len(gs_list) <= max_size):
            continue
        if required and not required.issubset(set(gs_list)):
            continue
        kept[str(name)] = gs_list
    return {
        "n_input": len(gene_sets),
        "n_kept": len(kept),
        "filtered_gene_sets": kept,
        "kept_names": list(kept)[:100],
    }


def run(operation: str, **kwargs: Any):
    ops = {"load_gmt": load_gmt, "filter_gene_sets": filter_gene_sets}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"msigdb: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("msigdb", run)
