"""Real end-to-end figure-generation experiment for openScience.

Generates synthetic multi-omics data, binds real visualization skills to
the openScience orchestrator (replacing the stub ``execute_skill``), and
drives four different visualization agents plus layout_composer,
publication_formatter, and color_palette_designer.

Logs every step, all errors encountered, and the artifacts produced.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Make openscience importable (running from repo root without install)
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

import matplotlib
matplotlib.use("Agg")  # headless for reproducibility

import numpy as np
import pandas as pd

from openscience.core.agent import BaseAgent
from openscience.core.orchestrator import AgentOrchestrator, Result, Task
from openscience.core.sandbox import _run_awaitable
from openscience.skills.visualization import (
    colorbrewer,
    matplotlib_gridspec,
    matplotlib_skill,
    seaborn_skill,
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
OUTDIR = Path(__file__).resolve().parent
LOG = logging.getLogger("figure_experiment")
LOG.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(fmt)
LOG.addHandler(sh)
fh = logging.FileHandler(OUTDIR / "experiment.log", mode="w")
fh.setFormatter(fmt)
LOG.addHandler(fh)


# ---------------------------------------------------------------------------
# Skill binding orchestrator
# ---------------------------------------------------------------------------
class FigureOrchestrator(AgentOrchestrator):
    """Orchestrator that dispatches execute_skill to real Python functions."""

    _SKILL_TABLE = {  # skill_name -> dispatcher
        "matplotlib": matplotlib_skill.run,
        "seaborn": seaborn_skill.run,
        "colorbrewer": colorbrewer.run,
        "matplotlib_gridspec": matplotlib_gridspec.run,
    }

    def execute_skill(self, skill_name: str, operation: str, **kwargs) -> Any:
        dispatcher = self._SKILL_TABLE.get(skill_name)
        if dispatcher is None:
            LOG.warning("Skill '%s' has no real implementation; falling back to stub",
                        skill_name)
            return super().execute_skill(skill_name, operation, **kwargs)
        LOG.info("SKILL  %s.%s  kwargs keys=%s", skill_name, operation,
                 sorted(kwargs.keys()))
        return dispatcher(operation=operation, **kwargs)


# ---------------------------------------------------------------------------
# Synthetic multi-omics data generation
# ---------------------------------------------------------------------------
def generate_synthetic_data(seed: int = 42) -> dict[str, pd.DataFrame]:
    """Produce realistic-looking RNA-seq DE results, protein expression,
    clinical metadata, and survival data."""
    LOG.info("Generating synthetic multi-omics dataset (seed=%d)", seed)
    rng = np.random.default_rng(seed)

    n_genes = 150
    n_samples = 60  # 30 tumor + 30 normal
    groups = np.array(["tumor"] * 30 + ["normal"] * 30)

    # ---- RNA-seq counts -> pretend differential-expression results ----
    gene_names = [f"GENE{i:03d}" for i in range(n_genes)]
    # Sprinkle a few well-known names for the labels
    for i, g in enumerate(["TP53", "MYC", "EGFR", "KRAS", "BRCA1",
                           "PTEN", "AKT1", "VEGFA", "CDKN2A", "RB1"]):
        gene_names[i] = g

    log2fc = rng.normal(0.0, 0.7, size=n_genes)
    n_de = 25
    # make a real DE signal in a subset
    log2fc[:n_de // 2] = rng.normal(2.2, 0.5, size=n_de // 2)
    log2fc[n_de // 2:n_de] = rng.normal(-2.0, 0.5, size=n_de - n_de // 2)
    base_mean = rng.uniform(5, 15, size=n_genes)
    pvals = 10 ** (-(np.abs(log2fc) * 2.0 + rng.uniform(0.2, 1.5, n_genes)))
    pvals = np.clip(pvals, 1e-40, 1.0)
    # BH FDR (approximate)
    order = np.argsort(pvals)
    ranked = pvals[order]
    fdr = ranked * n_genes / (np.arange(n_genes) + 1)
    fdr = np.minimum.accumulate(fdr[::-1])[::-1]
    padj = np.empty(n_genes)
    padj[order] = np.clip(fdr, 0, 1)

    de_results = pd.DataFrame({
        "gene": gene_names,
        "baseMean": base_mean,
        "log2FoldChange": log2fc,
        "pvalue": pvals,
        "padj": np.clip(padj, 1e-20, 1.0),
    })

    # ---- Gene expression matrix for heatmap (top DE genes) ----
    top_genes = de_results.reindex(
        de_results["padj"].sort_values().index).head(20)
    expr = np.zeros((20, n_samples))
    for i, (_, row) in enumerate(top_genes.iterrows()):
        shift = row["log2FoldChange"]
        expr[i, :30] = rng.normal(5 + shift / 2, 0.4, 30)   # tumor
        expr[i, 30:] = rng.normal(5 - shift / 2, 0.4, 30)   # normal
    expr_df = pd.DataFrame(expr, index=top_genes["gene"].values,
                           columns=[f"S{i:02d}" for i in range(n_samples)])

    # ---- Clinical metadata + protein levels + survival ----
    age = rng.normal(62, 10, 40).round(0).astype(int)
    # High-MYC tumors do worse
    myc_idx = gene_names.index("MYC")
    # Use a slice of tumor samples for the clinical cohort
    tumor_idx = list(range(30)) + list(range(30, 40))  # 40 tumors
    protein = {
        "pERK": rng.normal(2.5, 0.8, 40),
        "pAKT": rng.normal(1.8, 0.6, 40),
        "MYC": rng.normal(3.0, 0.9, 40),
        "Ki67": rng.uniform(5, 60, 40).round(1),
    }
    # make MYC protein correlate with survival
    surv_time = np.clip(rng.normal(36, 18, 40) - 6 * protein["MYC"] + 24, 1, 60)
    surv_event = (rng.random(40) < 0.55).astype(int)
    group_surv = np.where(protein["MYC"] > np.median(protein["MYC"]),
                          "MYC-high", "MYC-low")

    clinical = pd.DataFrame({
        "sample_id": [f"T{i:02d}" for i in range(40)],
        "age": age,
        "stage": rng.choice(["I", "II", "III", "IV"], 40,
                            p=[0.2, 0.3, 0.35, 0.15]),
        **protein,
    })
    survival = pd.DataFrame({
        "time": surv_time.round(1),
        "event": surv_event,
        "group": group_surv,
    })

    # numeric clinical matrix for correlation
    corr_df = pd.DataFrame({
        "age": clinical["age"].to_numpy(dtype=float),
        **{k: np.asarray(v) for k, v in protein.items()},
        "survival_months": survival["time"].to_numpy(dtype=float),
    })

    LOG.info("  DE results      shape=%s  (DE genes padj<0.05 & |LFC|>1: %d)",
             de_results.shape,
             int(((de_results.padj < 0.05) & (de_results.log2FoldChange.abs() > 1)).sum()))
    LOG.info("  Expression mtx  shape=%s", expr_df.shape)
    LOG.info("  Clinical        shape=%s", clinical.shape)
    LOG.info("  Survival        shape=%s  (%d events)", survival.shape,
             int(survival.event.sum()))
    LOG.info("  Correlation mtx shape=%s", corr_df.shape)

    return {
        "de_results": de_results,
        "expression": expr_df,
        "clinical": clinical,
        "survival": survival,
        "correlation": corr_df,
    }


# ---------------------------------------------------------------------------
# Step runner with error capture
# ---------------------------------------------------------------------------
@dataclass
class StepLog:
    name: str
    ok: bool = False
    msg: str = ""
    error: Optional[str] = None
    artifacts: list[str] = field(default_factory=list)


STEPS: list[StepLog] = []


def record(step: StepLog):
    STEPS.append(step)
    if step.ok:
        LOG.info("OK    %-26s %s", step.name, step.msg)
    else:
        LOG.error("FAIL  %-26s %s", step.name, step.error or step.msg)


def list_artifacts(*patterns: str) -> list[str]:
    out = []
    for p in patterns:
        out.extend(str(f.relative_to(OUTDIR)) for f in sorted(OUTDIR.glob(p)))
    return out


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------
def main() -> int:
    LOG.info("=" * 70)
    LOG.info("openScience figure-generation experiment")
    LOG.info("Repo: %s", REPO)
    LOG.info("Output dir: %s", OUTDIR)
    LOG.info("=" * 70)

    orch = FigureOrchestrator(sandbox=None)
    LOG.info("Orchestrator initialized with %d agents loaded", len(orch.agents))
    for needed in ("matplotlib_stylist", "seaborn_stylist",
                   "publication_formatter", "layout_composer",
                   "color_palette_designer"):
        LOG.info("  agent %-28s present=%s", needed, needed in orch.agents)

    data = generate_synthetic_data()

    # ------------------------------------------------------------------
    # STEP 1 — color_palette_designer agent
    # ------------------------------------------------------------------
    step = StepLog(name="color_palette_designer")
    try:
        palettes: dict[str, Any] = {}
        for pt in ("volcano", "qualitative", "heatmap", "correlation_matrix"):
            res = orch.execute_agent(
                "color_palette_designer",
                parameters={"plot_type": pt, "n_colors": 4},
                context={},
            )
            palettes[pt] = res.data["palette"]
            LOG.info("  palette %-18s -> %s", pt, res.data["palette"])
        step.ok = True
        step.msg = f"got {len(palettes)} palettes"
    except Exception as e:
        step.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    record(step)
    if not step.ok:
        return 1

    # ------------------------------------------------------------------
    # STEP 2 — individual panels via publication_formatter agent
    # ------------------------------------------------------------------
    panel_specs = [
        ("volcano", data["de_results"], palettes["volcano"],
         "panel_a_volcano", dict(label_top=8)),
        ("heatmap", data["expression"], palettes["heatmap"],
         "panel_b_heatmap", {}),
        ("kaplan_meier", data["survival"], palettes["qualitative"],
         "panel_c_kaplan_meier", {}),
        ("correlation_matrix", data["correlation"], palettes["correlation_matrix"],
         "panel_d_correlation", {}),
    ]

    panels_for_layout = []
    individual_figs = []
    for i, (viz, df, palette, stem, extra) in enumerate(panel_specs):
        step = StepLog(name=f"panel_{viz}")
        try:
            out_path = str(OUTDIR / stem)
            res = orch.execute_agent(
                "publication_formatter",
                parameters={
                    "figure_data": {"data": df, "palette": palette},
                    "viz_type": viz,
                    "style": "nature",
                    "output_path": out_path,
                    **extra,
                },
                context={},
            )
            fig = res.data["figure"]
            individual_figs.append(fig)
            step.ok = True
            step.artifacts = list_artifacts(stem + ".*")
            step.msg = f"{len(step.artifacts)} file(s): {step.artifacts}"
            panels_for_layout.append({
                "viz_type": viz,
                "data": df,
                "palette": palette,
                "kwargs": extra,
            })
        except Exception as e:
            step.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        record(step)

    if len(panels_for_layout) != 4:
        LOG.error("Not all panels built; aborting before layout step")
        return 1

    # ------------------------------------------------------------------
    # STEP 3 — layout_composer agent: multi-panel figure
    # ------------------------------------------------------------------
    step = StepLog(name="layout_composer")
    try:
        res = orch.execute_agent(
            "layout_composer",
            parameters={
                "panels": panels_for_layout,
                "layout": (2, 2),
                "figsize": (7.2, 6.0),  # Nature double-column width
                "style": "nature",
                "panel_labels": True,
                "output_path": str(OUTDIR / "figure1_multipanel"),
            },
            context={},
        )
        fig = res.data
        step.ok = True
        step.artifacts = list_artifacts("figure1_multipanel.*")
        step.msg = f"panels={len(panels_for_layout)}, files={step.artifacts}"
        multi_fig = fig
    except Exception as e:
        step.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        record(step)
        return 1
    record(step)

    # ------------------------------------------------------------------
    # STEP 4 — matplotlib_stylist: apply Nature style to multi-panel fig
    # ------------------------------------------------------------------
    step = StepLog(name="matplotlib_stylist_restyle")
    try:
        from openscience.agents.visualization.matplotlib_stylist import (
            MatplotlibStylistAgent,
        )
        agent: BaseAgent = orch._get_agent_instance(MatplotlibStylistAgent)
        # The stylist calls matplotlib.apply_style which mutates the fig in place
        styled = orch.execute_skill(
            "matplotlib", "apply_style", figure=multi_fig, style="nature")
        # re-save the styled figure
        from openscience.skills.visualization.matplotlib_skill import _save_all
        _save_all(multi_fig, str(OUTDIR / "figure1_multipanel_nature_styled"))
        step.ok = True
        step.artifacts = list_artifacts("figure1_multipanel_nature_styled.*")
        step.msg = "re-styled + re-saved Nature format"
    except Exception as e:
        step.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        record(step)
        # non-fatal
    record(step)

    # ------------------------------------------------------------------
    # STEP 5 — seaborn_stylist: bonus boxplot driven by its own agent
    # ------------------------------------------------------------------
    step = StepLog(name="seaborn_stylist_boxplot")
    try:
        clinical = data["clinical"].copy()
        # melt protein columns for boxplot
        melted = clinical.melt(
            id_vars=["stage"], value_vars=["pERK", "pAKT", "MYC", "Ki67"],
            var_name="protein", value_name="level")
        # Make a small multi-stage plot rendered through the seaborn skill
        res = orch.execute_agent(
            "seaborn_stylist",
            parameters={
                "plot_type": "boxplot",
                "data": melted,
                "x": "protein", "y": "level",
                "output_path": str(OUTDIR / "panel_e_protein_boxplot"),
            },
            context={},
        )
        step.ok = True
        step.artifacts = list_artifacts("panel_e_protein_boxplot.*")
        step.msg = f"files={step.artifacts}"
    except Exception as e:
        step.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
    record(step)

    # ------------------------------------------------------------------
    # STEP 6 — verify all artifacts exist + non-trivial
    # ------------------------------------------------------------------
    step = StepLog(name="verify_artifacts")
    try:
        exts = ("pdf", "png", "svg")
        expected = [f"panel_a_volcano.{e}" for e in exts] + \
                   [f"panel_b_heatmap.{e}" for e in exts] + \
                   [f"panel_c_kaplan_meier.{e}" for e in exts] + \
                   [f"panel_d_correlation.{e}" for e in exts] + \
                   [f"figure1_multipanel.{e}" for e in exts] + \
                   [f"figure1_multipanel_nature_styled.{e}" for e in exts]
        problems = []
        sizes = {}
        for rel in expected:
            p = OUTDIR / rel
            if not p.exists():
                problems.append(f"missing {rel}")
            else:
                sz = p.stat().st_size
                sizes[rel] = sz
                if sz < 1000:
                    problems.append(f"suspiciously small {rel} ({sz} B)")
        if problems:
            raise RuntimeError("; ".join(problems))
        step.ok = True
        step.msg = f"all {len(expected)} files present, total "
        step.msg += f"{sum(sizes.values())/1024:.0f} KiB"
    except Exception as e:
        step.error = f"{type(e).__name__}: {e}"
    record(step)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    summary = {
        "repo": str(REPO),
        "outdir": str(OUTDIR),
        "agents_loaded": len(orch.agents),
        "steps": [
            {"name": s.name, "ok": s.ok,
             "msg": s.msg if s.ok else None,
             "error": s.error if not s.ok else None,
             "artifacts": s.artifacts}
            for s in STEPS
        ],
        "artifacts": sorted(
            str(p.relative_to(OUTDIR)) for p in OUTDIR.glob("*")
            if p.is_file()
        ),
    }
    summary_path = OUTDIR / "experiment_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    LOG.info("Wrote summary -> %s", summary_path)

    n_ok = sum(1 for s in STEPS if s.ok)
    LOG.info("=" * 70)
    LOG.info("DONE: %d/%d steps OK", n_ok, len(STEPS))
    LOG.info("=" * 70)
    return 0 if n_ok == len(STEPS) else 1


if __name__ == "__main__":
    sys.exit(main())
