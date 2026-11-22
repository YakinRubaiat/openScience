"""Methylation array analysis skill (pure python).

- ``beta_to_m``         — convert beta values to M-values (logit transform)
- ``compute_dmc_regions``— per-probe Welch t-test between two groups on
  M-values, BH FDR, and grouping of significant probes into DMR regions
- ``mds_plot_data``     — 2-D MDS/PCA coordinates of samples (sklearn PCA)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from openscience.skills import register_skill
from openscience.skills._common import unwrap

_EPS = 1e-6


def beta_to_m(betas=None, **kwargs: Any):
    kw = unwrap(kwargs)
    betas = betas if betas is not None else kw.get("betas")
    if betas is None:
        raise ValueError("beta_to_m requires 'betas'")
    df = pd.DataFrame(betas, dtype=float)
    b = df.clip(_EPS, 1 - _EPS)
    m = np.log2(b / (1 - b))
    return {
        "n_probes": int(m.shape[0]),
        "n_samples": int(m.shape[1]),
        "m_values": m.round(6).to_dict(),
    }


def _bh(p: np.ndarray) -> np.ndarray:
    order = np.argsort(p)
    q = p[order] * p.size / (np.arange(p.size) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = np.clip(q, 0, 1)
    return out


def compute_dmc_regions(betas=None, group_a=None, group_b=None, **kwargs: Any):
    kw = unwrap(kwargs)
    betas = betas if betas is not None else kw.get("betas")
    if betas is None:
        raise ValueError("compute_dmc_regions requires 'betas' (probes x samples)")
    df = pd.DataFrame(betas, dtype=float)
    group_a = group_a or kw.get("group_a")
    group_b = group_b or kw.get("group_b")
    if not (group_a and group_b):
        raise ValueError("Provide 'group_a' and 'group_b' sample names")
    missing = [s for s in list(group_a) + list(group_b) if s not in df.columns]
    if missing:
        raise ValueError(f"Samples not found: {missing}")

    b = df.clip(_EPS, 1 - _EPS)
    m = np.log2(b / (1 - b))
    a = m[list(group_a)].to_numpy(dtype=float)
    bb = m[list(group_b)].to_numpy(dtype=float)
    with np.errstate(invalid="ignore"):
        _t, p = stats.ttest_ind(bb, a, axis=1, equal_var=False)
    p = np.where(np.isfinite(p), p, 1.0)
    padj = _bh(p)
    delta_beta = df[list(group_b)].mean(axis=1) - df[list(group_a)].mean(axis=1)

    alpha = float(kw.get("alpha", 0.05))
    sig_mask = padj < alpha
    probes = np.asarray(df.index.astype(str))
    res = pd.DataFrame(
        {
            "probe": probes,
            "delta_beta": delta_beta.to_numpy(),
            "p_value": p,
            "padj": padj,
            "significant": sig_mask,
        }
    ).sort_values("padj")

    # naive DMR grouping: consecutive significant probes (by input order)
    regions = []
    run_probes: list[str] = []
    chroms = kw.get("probe_chroms")
    for i, ok in enumerate(sig_mask):
        if ok:
            run_probes.append(str(probes[i]))
        elif run_probes:
            if len(run_probes) >= int(kw.get("min_probes_per_region", 2)):
                regions.append(run_probes)
            run_probes = []
    if len(run_probes) >= int(kw.get("min_probes_per_region", 2)):
        regions.append(run_probes)

    return {
        "n_probes_tested": int(res.shape[0]),
        "n_significant": int(sig_mask.sum()),
        "alpha": alpha,
        "n_dmrs": len(regions),
        "dmc_regions": [
            {"n_probes": len(r), "probes": r[:20]} for r in regions[:50]
        ],
        "top_probes": res.head(int(kw.get("top", 25))).to_dict(orient="records"),
        "chrom_annotation_used": chroms is not None,
    }


def mds_plot_data(betas=None, n_components: int = 2, **kwargs: Any):
    kw = unwrap(kwargs)
    betas = betas if betas is not None else kw.get("betas")
    if betas is None:
        raise ValueError("mds_plot_data requires 'betas' (probes x samples)")
    df = pd.DataFrame(betas, dtype=float)
    from sklearn.decomposition import PCA

    n_components = int(kw.get("n_components", n_components))
    n_comp = min(n_components, df.shape[1], df.shape[0])
    pca = PCA(n_components=n_comp, random_state=0)
    coords = pca.fit_transform(df.T.to_numpy())
    return {
        "n_samples": int(df.shape[1]),
        "n_components": int(n_comp),
        "explained_variance_ratio": [float(v) for v in pca.explained_variance_ratio_],
        "coordinates": [
            {"sample": str(s), **{f"dim{i + 1}": float(c[i]) for i in range(n_comp)}}
            for s, c in zip(df.columns, coords)
        ],
    }


def run(operation: str, **kwargs: Any):
    ops = {
        "beta_to_m": beta_to_m,
        "compute_dmc_regions": compute_dmc_regions,
        "mds_plot_data": mds_plot_data,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"methylation_array: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("methylation_array", run)
