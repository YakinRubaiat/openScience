"""GSEApy-extended skill: prerank GSEA plus pure-python enrichment.

- ``prerank``      — run gseapy.prerank (requires the optional ``gseapy``
  package; raises a clear install error when absent)
- ``enrich2``      — pure-python over-representation analysis (Fisher exact
  test) of a gene list against a dict of gene sets, with BH FDR
- ``leading_edge`` — leading-edge subset of an enrichment result
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import optional_import, unwrap


def _bh_adjust(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    n = p.size
    order = np.argsort(p)
    q = p[order] * n / (np.arange(n) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = np.clip(q, 0, 1)
    return out


def prerank(ranked_genes=None, gene_sets=None, **kwargs: Any):
    kw = unwrap(kwargs)
    gseapy = optional_import("gseapy")
    ranked = ranked_genes if ranked_genes is not None else kw.get("ranked_genes")
    gene_sets = gene_sets if gene_sets is not None else kw.get("gene_sets")
    if ranked is None or gene_sets is None:
        raise ValueError("prerank requires 'ranked_genes' and 'gene_sets'")
    pre = gseapy.prerank(
        rnk=ranked,
        gene_sets=gene_sets,
        min_size=int(kw.get("min_size", 5)),
        max_size=int(kw.get("max_size", 2000)),
        permutation_num=int(kw.get("permutations", 1000)),
        outdir=kw.get("outdir"),
        seed=int(kw.get("seed", 42)),
        no_plot=kw.get("no_plot", True),
    )
    res = pre.res2d
    return {
        "n_terms": int(res.shape[0]),
        "columns": [str(c) for c in res.columns],
        "top_terms": res.head(int(kw.get("top", 10))).to_dict(orient="records"),
    }


def enrich2(gene_list=None, gene_sets=None, background=None, **kwargs: Any):
    """Fisher exact over-representation, BH-adjusted, on dict gene sets."""
    kw = unwrap(kwargs)
    genes = gene_list if gene_list is not None else kw.get("gene_list")
    gene_sets = gene_sets if gene_sets is not None else kw.get("gene_sets")
    background = background if background is not None else kw.get("background")
    if genes is None or gene_sets is None:
        raise ValueError("enrich2 requires 'gene_list' and 'gene_sets' (dict of lists)")

    query = {str(g) for g in genes}
    universe = {str(g) for g in background} if background else set().union(
        *({str(x) for x in gs} for gs in gene_sets.values())
    )
    universe |= query
    N = len(universe)
    q_in = len(query & universe)

    rows = []
    for name, gs in gene_sets.items():
        gs_set = {str(x) for x in gs} & universe
        a = len(query & gs_set)
        if a == 0:
            continue
        b = q_in - a
        c = len(gs_set) - a
        d = N - a - b - c
        odds, p = stats.fisher_exact([[a, b], [c, d]], alternative="greater")
        rows.append(
            {
                "term": str(name),
                "overlap": a,
                "set_size": len(gs_set),
                "query_size": q_in,
                "odds_ratio": float(odds) if np.isfinite(odds) else None,
                "p_value": float(p),
                "overlap_genes": sorted(query & gs_set),
            }
        )
    if not rows:
        return {"n_terms_tested": len(gene_sets), "n_terms_with_overlap": 0, "results": []}
    padj = _bh_adjust(np.array([r["p_value"] for r in rows]))
    for r, q in zip(rows, padj):
        r["fdr"] = float(q)
    rows.sort(key=lambda r: r["fdr"])
    sig = [r for r in rows if r["fdr"] < float(kw.get("alpha", 0.05))]
    return {
        "n_terms_tested": len(gene_sets),
        "n_terms_with_overlap": len(rows),
        "n_significant": len(sig),
        "results": rows[: int(kw.get("top", 50))],
    }


def leading_edge(term=None, ranked_genes=None, gene_sets=None, **kwargs: Any):
    """Leading-edge genes: the subset of a gene set appearing before the
    running-sum peak of a ranked list (GSEA definition)."""
    kw = unwrap(kwargs)
    term = term if term is not None else kw.get("term")
    ranked = ranked_genes if ranked_genes is not None else kw.get("ranked_genes")
    gene_sets = gene_sets if gene_sets is not None else kw.get("gene_sets")
    if term is None or ranked is None or gene_sets is None:
        raise ValueError("leading_edge requires 'term', 'ranked_genes' and 'gene_sets'")
    genes_in_set = {str(g) for g in gene_sets[term]}
    ranked_list = [str(g) for g in ranked_genes]
    hits = np.array([1 if g in genes_in_set else 0 for g in ranked_list], dtype=float)
    n_hit = hits.sum()
    if n_hit == 0:
        return {"term": str(term), "leading_edge_genes": [], "n_leading_edge": 0}
    n_miss = len(ranked_list) - n_hit
    running = np.cumsum(np.where(hits == 1, 1.0 / n_hit, -1.0 / max(n_miss, 1)))
    peak_idx = int(np.argmax(running))
    le = [g for g, h in zip(ranked_list[: peak_idx + 1], hits[: peak_idx + 1]) if h == 1]
    return {
        "term": str(term),
        "peak_rank": peak_idx + 1,
        "leading_edge_genes": le,
        "n_leading_edge": len(le),
        "n_genes_in_set": int(n_hit),
    }


def run(operation: str, **kwargs: Any):
    ops = {"prerank": prerank, "enrich2": enrich2, "leading_edge": leading_edge}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"gseapy: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("gseapy", run)
