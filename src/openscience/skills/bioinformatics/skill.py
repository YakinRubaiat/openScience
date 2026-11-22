"""Real bioinformatics skill implementations backed by scanpy.

Supported skill names (dispatched from ``BioinformaticsSkill.execute``):

- ``bioio``      — multi-format data loading (10x mtx, h5ad, csv, ...)
- ``scanpy``     — QC metrics, filtering, clustering, UMAP, markers
- ``matplotlib`` — figure rendering with publication styles
- ``anndata``    — AnnData introspection helpers

Each operation returns JSON-serialisable dicts. AnnData objects travel
through the shared ``context`` dict under the ``"adata"`` key so agents
in a pipeline share state without serialising large matrices.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd


class BioinformaticsSkill:
    """Dispatch real bioinformatics operations."""

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #
    def execute(
        self,
        skill_name: str,
        operation: str,
        context: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        context = context if context is not None else {}
        handler = {
            "bioio": self._bioio,
            "scanpy": self._scanpy,
            "anndata": self._anndata,
            "matplotlib": self._matplotlib,
        }.get(skill_name)
        if handler is None:
            raise ValueError(f"Unknown skill: {skill_name}")
        return handler(operation, context=context, **kwargs)

    # ------------------------------------------------------------------ #
    # bioio — data loading
    # ------------------------------------------------------------------ #
    def _bioio(self, operation: str, context: dict, **kwargs):
        if operation != "load":
            raise ValueError(f"bioio: unknown operation '{operation}'")

        file_path = kwargs.get("file_path")
        fmt = kwargs.get("format", "auto")
        if not file_path:
            raise ValueError("bioio.load requires 'file_path'")

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        if fmt == "mtx":
            # A bare .mtx file — needs sibling genes/barcodes (10x layout)
            import scanpy as sc

            adata = sc.read_mtx(path)
            genes = path.parent / "genes.tsv"
            barcodes = path.parent / "barcodes.tsv"
            if genes.exists():
                g = pd.read_csv(genes, sep="\t", header=None)
                adata.var_names = g[0].astype(str).values
                if g.shape[1] > 1:
                    adata.var["gene_symbols"] = g[1].astype(str).values
            if barcodes.exists():
                adata.obs_names = pd.read_csv(barcodes, sep="\t", header=None)[0].astype(str).values
            adata.var_names_make_unique()
        elif fmt == "h5ad":
            import anndata as ad

            adata = ad.read_h5ad(path)
        elif fmt in ("csv", "tsv"):
            sep = "," if fmt == "csv" else "\t"
            df = pd.read_csv(path, sep=sep, index_col=0)
            context["dataframe"] = df
            return {
                "type": "dataframe",
                "n_rows": int(df.shape[0]),
                "n_cols": int(df.shape[1]),
                "columns": [str(c) for c in df.columns[:50]],
            }
        else:
            raise ValueError(f"bioio.load: unsupported format '{fmt}'")

        context["adata"] = adata
        return {
            "type": "anndata",
            "n_obs": int(adata.n_obs),
            "n_vars": int(adata.n_vars),
            "obs_columns": list(adata.obs.columns),
            "var_columns": list(adata.var.columns),
        }

    # ------------------------------------------------------------------ #
    # scanpy — QC / clustering
    # ------------------------------------------------------------------ #
    def _scanpy(self, operation: str, context: dict, **kwargs):
        import scanpy as sc

        adata = self._require_adata(context, kwargs)

        if operation == "qc_analysis":
            return self._qc(adata, context, **kwargs)
        if operation == "run":
            return self._cluster(adata, context, **kwargs)
        raise ValueError(f"scanpy: unknown operation '{operation}'")

    def _qc(self, adata, context, **kwargs):
        import scanpy as sc

        # ---- metrics --------------------------------------------------- #
        adata.var["mt"] = adata.var_names.str.upper().str.startswith("MT-")
        sc.pp.calculate_qc_metrics(
            adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True
        )

        n_cells_raw = int(adata.n_obs)
        n_genes_raw = int(adata.n_vars)

        stats = {
            "cells_raw": n_cells_raw,
            "genes_raw": n_genes_raw,
            "median_genes_per_cell": float(np.median(adata.obs["n_genes_by_counts"])),
            "median_counts_per_cell": float(np.median(adata.obs["total_counts"])),
            "median_pct_mito": float(np.median(adata.obs["pct_counts_mt"])),
            "cells_with_mt_detected": int((adata.obs["pct_counts_mt"] > 0).sum()),
        }

        # ---- filtering -------------------------------------------------- #
        min_genes = kwargs.get("min_genes", 200)
        min_cells = kwargs.get("min_cells", 3)
        max_pct_mt = kwargs.get("max_pct_mt", 5.0)
        max_genes = kwargs.get("max_genes", 2500)

        sc.pp.filter_cells(adata, min_genes=min_genes)
        sc.pp.filter_genes(adata, min_cells=min_cells)
        keep = (adata.obs["pct_counts_mt"] < max_pct_mt) & (
            adata.obs["n_genes_by_counts"] < max_genes
        )
        adata._inplace_subset_obs(keep)

        stats.update(
            {
                "cells_after_filter": int(adata.n_obs),
                "genes_after_filter": int(adata.n_vars),
                "filter_params": {
                    "min_genes": min_genes,
                    "min_cells": min_cells,
                    "max_pct_mt": max_pct_mt,
                    "max_genes": max_genes,
                },
            }
        )

        # Store distributions for the plotting step
        context["qc_distributions"] = {
            "n_genes": adata.obs["n_genes_by_counts"].tolist(),
            "total_counts": adata.obs["total_counts"].tolist(),
            "pct_mt": adata.obs["pct_counts_mt"].tolist(),
        }
        context["qc_stats"] = stats
        return stats

    def _cluster(self, adata, context, **kwargs):
        import scanpy as sc

        normalize = kwargs.get("normalize", True)
        if normalize and "log1p" not in adata.uns:
            sc.pp.normalize_total(adata, target_sum=1e4)
            sc.pp.log1p(adata)

        n_top = int(kwargs.get("n_top_genes", 2000))
        sc.pp.highly_variable_genes(adata, min_mean=0.0125, max_mean=3, min_disp=0.5)
        n_hvg = int(adata.var["highly_variable"].sum())
        adata.raw = adata
        adata._inplace_subset_var(adata.var["highly_variable"])

        sc.pp.regress_out(adata, ["total_counts", "pct_counts_mt"])
        sc.pp.scale(adata, max_value=10)

        n_comps = min(40, adata.n_vars - 1, adata.n_obs - 1)
        sc.tl.pca(adata, n_comps=n_comps, svd_solver="arpack")

        sc.pp.neighbors(adata, n_neighbors=10, n_pcs=min(40, n_comps))
        sc.tl.umap(adata, random_state=42)

        resolution = float(kwargs.get("resolution", 0.6))
        sc.tl.leiden(adata, resolution=resolution, flavor="igraph", n_iterations=2)

        clusters = adata.obs["leiden"].value_counts().sort_index()
        cluster_sizes = {str(k): int(v) for k, v in clusters.items()}

        # Marker genes (rank_genes_groups on the log-normalised full matrix)
        markers = {}
        try:
            sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon", n_genes=5)
            for group in adata.uns["rank_genes_groups"]["names"].dtype.names:
                names = adata.uns["rank_genes_groups"]["names"][group]
                scores = adata.uns["rank_genes_groups"]["scores"][group]
                markers[str(group)] = [
                    {"gene": str(n), "score": float(s)}
                    for n, s in zip(names[:5], scores[:5])
                ]
        except Exception as exc:  # pragma: no cover - don't kill pipeline on marker failure
            markers = {"error": str(exc)}

        result = {
            "n_clusters": int(len(cluster_sizes)),
            "cluster_sizes": cluster_sizes,
            "n_hvg": n_hvg,
            "n_pcs": n_comps,
            "resolution": resolution,
            "top_markers": markers,
        }
        context["clustering"] = result
        return result

    # ------------------------------------------------------------------ #
    # anndata — introspection
    # ------------------------------------------------------------------ #
    def _anndata(self, operation: str, context: dict, **kwargs):
        adata = self._require_adata(context, kwargs)
        if operation == "describe":
            return {
                "n_obs": int(adata.n_obs),
                "n_vars": int(adata.n_vars),
                "obs": list(adata.obs.columns),
                "var": list(adata.var.columns),
                "obsm": list(adata.obsm.keys()),
                "uns": list(adata.uns.keys()),
            }
        raise ValueError(f"anndata: unknown operation '{operation}'")

    # ------------------------------------------------------------------ #
    # matplotlib — figure rendering
    # ------------------------------------------------------------------ #
    def _matplotlib(self, operation: str, context: dict, **kwargs):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        style = kwargs.get("style", "publication")
        output_path = kwargs.get("output_path")

        if style in ("publication", "nature"):
            plt.rcParams.update(
                {
                    "font.size": 8,
                    "axes.titlesize": 9,
                    "axes.labelsize": 8,
                    "xtick.labelsize": 7,
                    "ytick.labelsize": 7,
                    "legend.fontsize": 7,
                    "axes.linewidth": 0.6,
                    "figure.dpi": 300,
                    "savefig.dpi": 300,
                    "savefig.bbox": "tight",
                }
            )
        return {"style_applied": style, "output_path": output_path, "backend": "Agg"}

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _require_adata(context: dict, kwargs: dict):
        adata = kwargs.get("data")
        if adata is None:
            adata = context.get("adata")
        if adata is None:
            raise ValueError(
                "No AnnData object supplied — pass one via context['adata'] "
                "or the 'data' kwarg (load data first)."
            )
        return adata


class BioinformaticsSkillJSONEncoder(json.JSONEncoder):
    """JSON encoder that survives numpy/pandas types in skill results."""

    def default(self, obj):  # noqa: D102
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (pd.Series, pd.Index)):
            return obj.tolist()
        return super().default(obj)
