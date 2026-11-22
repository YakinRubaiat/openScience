"""Pathway database skill: load and summarise pathway collections.

- ``load_pathways``    — from a .gmt file or a plain dict
- ``pathway_summary``  — size distribution / coverage stats
- ``genes_in_pathway`` — member genes of one pathway (with optional filters)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _load(gmt_path=None, pathways=None, kw=None):
    kw = kw or {}
    gmt_path = gmt_path or kw.get("gmt_path") or kw.get("path")
    pathways = pathways if pathways is not None else kw.get("pathways")
    if gmt_path:
        p = Path(gmt_path)
        if not p.exists():
            raise FileNotFoundError(f"GMT file not found: {p}")
        out = {}
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            out[parts[0]] = [g for g in parts[2:] if g]
        return out, str(p)
    if pathways is not None:
        return {str(k): [str(g) for g in v] for k, v in dict(pathways).items()}, "dict"
    raise ValueError("Provide 'gmt_path' or 'pathways' dict")


def load_pathways(gmt_path=None, pathways=None, **kwargs: Any):
    kw = unwrap(kwargs)
    pws, source = _load(gmt_path, pathways, kw)
    if not pws:
        raise ValueError("No pathways loaded")
    return {
        "source": source,
        "n_pathways": len(pws),
        "pathway_names": list(pws)[:100],
        "pathways": pws,
    }


def pathway_summary(gmt_path=None, pathways=None, **kwargs: Any):
    kw = unwrap(kwargs)
    pws, source = _load(gmt_path, pathways, kw)
    sizes = np.array([len(v) for v in pws.values()], dtype=float)
    all_genes = set().union(*(set(v) for v in pws.values()))
    overlaps = sorted(pws, key=lambda k: len(pws[k]), reverse=True)[:10]
    return {
        "source": source,
        "n_pathways": len(pws),
        "n_unique_genes": len(all_genes),
        "mean_size": float(sizes.mean()),
        "median_size": float(np.median(sizes)),
        "min_size": int(sizes.min()),
        "max_size": int(sizes.max()),
        "largest_pathways": [{"pathway": k, "size": len(pws[k])} for k in overlaps],
    }


def genes_in_pathway(pathway=None, gmt_path=None, pathways=None, **kwargs: Any):
    kw = unwrap(kwargs)
    pathway = pathway if pathway is not None else kw.get("pathway")
    pws, _source = _load(gmt_path, pathways, kw)
    if pathway is None:
        raise ValueError("genes_in_pathway requires 'pathway' name")
    if pathway not in pws:
        close = [k for k in pws if pathway.lower() in k.lower()][:10]
        raise ValueError(f"Pathway {pathway!r} not found. Similar: {close}")
    genes = pws[pathway]
    present = kw.get("present_in")
    if present is not None:
        keep = {str(g) for g in present}
        genes = [g for g in genes if g in keep]
    return {
        "pathway": str(pathway),
        "n_genes": len(genes),
        "genes": genes,
        "total_in_pathway": len(pws[pathway]),
    }


def run(operation: str, **kwargs: Any):
    ops = {
        "load_pathways": load_pathways,
        "pathway_summary": pathway_summary,
        "genes_in_pathway": genes_in_pathway,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"pathway_databases: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("pathway_databases", run)
