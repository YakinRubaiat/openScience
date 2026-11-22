"""Experiment: real single-cell analysis of PBMC 3K with openScience agents.

Pipeline (every stage goes through a real openScience agent):
    data_ingestor   -> load 10x Genomics mtx
    qc_analyzer     -> compute QC metrics & filter
    scanpy_specialist -> normalise, HVGs, PCA, neighbors, UMAP, Leiden
    matplotlib_stylist / publication_formatter -> figure styling
    figures         -> saved via scanpy/matplotlib to experiments/data_analysis_report/figures

Run with:
    cd /Users/srubaiat/openScience
    .venv/bin/python scripts/run_scrna_experiment.py
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "experiments" / "data_analysis_report"
FIGS = OUT / "figures"
RESULTS = OUT / "results"
DATA = OUT / "data"
for d in (FIGS, RESULTS, DATA):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "src"))

from openscience.core.orchestrator import AgentOrchestrator
from openscience.skills.bioinformatics import BioinformaticsSkill


class RealBioOrchestrator(AgentOrchestrator):
    """Orchestrator whose skills are *real* scanpy/matplotlib calls."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bio_skill = BioinformaticsSkill()
        self.shared_context: dict = {}

    def execute_skill(self, skill_name: str, operation: str, **kwargs):
        ctx = kwargs.pop("context", None) or {}
        merged = {**self.shared_context, **ctx}
        result = self._bio_skill.execute(skill_name, operation, context=merged, **kwargs)
        self.shared_context.update(merged)
        return result


LOG: list[dict] = []


def record(step: str, status: str, detail: dict):
    LOG.append({"step": step, "status": status, "detail": detail, "ts": time.time()})
    print(f"\n[{status.upper():7s}] {step}")
    if status == "error":
        print("  " + detail.get("error", "").replace("\n", "\n  ")[:2000])
    else:
        print(json.dumps(detail, indent=2, default=str)[:1500])


def fail(step: str) -> None:
    tb = traceback.format_exc()
    (RESULTS / "error.txt").write_text(tb)
    record(step, "error", {"error": tb})


def main() -> int:
    import matplotlib

    matplotlib.use("Agg")

    orch = RealBioOrchestrator()
    mtx_path = DATA / "filtered_gene_bc_matrices" / "hg19" / "matrix.mtx"

    print("Agents discovered:", len(orch.agents))
    for needed in (
        "data_ingestor",
        "qc_analyzer",
        "scanpy_specialist",
        "matplotlib_stylist",
        "publication_formatter",
    ):
        assert needed in orch.agents, f"missing agent {needed}"

    # ------------------------------------------------------------------ #
    # STEP 1 - ingest
    # ------------------------------------------------------------------ #
    try:
        res = orch.execute_agent(
            "data_ingestor",
            parameters={"file_path": str(mtx_path), "format_hint": "mtx"},
            context=orch.shared_context,
        )
        ingest = res.data["data"] if isinstance(res.data, dict) and "data" in res.data else res.data
        record("1. data_ingestor (load 10x mtx)", "ok", ingest)
    except Exception:
        fail("1. data_ingestor")
        return 1

    # ------------------------------------------------------------------ #
    # STEP 2 - QC
    # ------------------------------------------------------------------ #
    try:
        res = orch.execute_agent(
            "qc_analyzer",
            parameters={"data_type": "single_cell"},
            context=orch.shared_context,
        )
        qc = res.data["data"] if isinstance(res.data, dict) and "data" in res.data else res.data
        record("2. qc_analyzer (metrics + filtering)", "ok", qc)
        (RESULTS / "qc_stats.json").write_text(json.dumps(qc, indent=2, default=str))
    except Exception:
        fail("2. qc_analyzer")
        return 1

    # ------------------------------------------------------------------ #
    # STEP 3 - clustering
    # ------------------------------------------------------------------ #
    try:
        res = orch.execute_agent(
            "scanpy_specialist",
            parameters={"resolution": 0.6, "n_top_genes": 2000},
            context=orch.shared_context,
        )
        clust = res.data["data"] if isinstance(res.data, dict) and "data" in res.data else res.data
        record(
            "3. scanpy_specialist (PCA/UMAP/Leiden + markers)",
            "ok",
            {k: v for k, v in clust.items() if k != "top_markers"},
        )
        (RESULTS / "clustering.json").write_text(json.dumps(clust, indent=2, default=str))
    except Exception:
        fail("3. scanpy_specialist")
        return 1

    # ------------------------------------------------------------------ #
    # STEP 4 - figures via the *visualization agents*
    # ------------------------------------------------------------------ #
    try:
        import scanpy as sc

        adata = orch.shared_context["adata"]

        # point scanpy's figure dir at our output dir
        sc.settings.figdir = FIGS

        style_res = orch.execute_agent(
            "matplotlib_stylist",
            parameters={"figure": None, "style": "nature"},
            context=orch.shared_context,
        )
        record(
            "4a. matplotlib_stylist (apply nature style)",
            "ok",
            style_res.data if isinstance(style_res.data, dict) else {"result": str(style_res.data)},
        )

        sc.pl.violin(
            adata,
            ["n_genes_by_counts", "total_counts", "pct_counts_mt"],
            jitter=0.4,
            multi_panel=True,
            save="_qc_violin.png",
            show=False,
        )
        sc.pl.scatter(
            adata, x="total_counts", y="n_genes_by_counts", save="_qc_scatter.png", show=False
        )
        sc.pl.umap(
            adata, color=["leiden"], legend_loc="on data", save="_umap_clusters.png", show=False
        )
        sc.pl.highly_variable_genes(adata, save="_hvg.png", show=False)
        if "rank_genes_groups" in adata.uns:
            sc.pl.rank_genes_groups(
                adata, n_genes=10, sharey=False, save="_marker_genes.png", show=False
            )

        # normalise scanpy's verbose filenames
        renames = {
            "violin_qc_violin.png": "fig1_qc_violin.png",
            "scatter_qc_scatter.png": "fig2_qc_scatter.png",
            "umap_umap_clusters.png": "fig3_umap_clusters.png",
            "filter_genes_dispersion_hvg.png": "fig4_highly_variable_genes.png",
            "rank_genes_groups_marker_genes.png": "fig5_marker_genes.png",
        }
        produced = []
        for src_name, dst_name in renames.items():
            src = FIGS / src_name
            if src.exists():
                src.rename(FIGS / dst_name)
                produced.append(dst_name)
        produced.extend(sorted(p.name for p in FIGS.glob("*.png") if p.name not in produced))

        fmt_res = orch.execute_agent(
            "publication_formatter",
            parameters={
                "figure_data": "scanpy_figures",
                "viz_type": "umap",
                "style": "publication",
                "output_path": str(FIGS),
            },
            context=orch.shared_context,
        )
        record(
            "4b. publication_formatter",
            "ok",
            fmt_res.data if isinstance(fmt_res.data, dict) else {"result": str(fmt_res.data)},
        )
        record("4c. figures written", "ok", {"figures": produced})
    except Exception:
        fail("4. figures")
        return 1

    # ------------------------------------------------------------------ #
    # STEP 5 - persist AnnData + report skeleton
    # ------------------------------------------------------------------ #
    try:
        adata.write_h5ad(RESULTS / "pbmc3k_processed.h5ad")
        (RESULTS / "pipeline_log.json").write_text(json.dumps(LOG, indent=2, default=str))
        record(
            "5. saved processed AnnData + pipeline log",
            "ok",
            {"paths": [str(RESULTS / "pbmc3k_processed.h5ad"), str(RESULTS / "pipeline_log.json")]},
        )
    except Exception:
        fail("5. persistence")
        return 1

    print("\n=== EXPERIMENT COMPLETE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
