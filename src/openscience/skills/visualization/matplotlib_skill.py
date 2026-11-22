"""Real ``matplotlib`` skill.

Operations
----------
``render``       : build a figure panel (volcano, heatmap, kaplan_meier,
                   correlation_matrix, box) from a pandas DataFrame
``apply_style``  : apply a journal style sheet to an existing figure

Helpers ``_apply_rc`` and ``_save_all`` are used by sibling skills too.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ----------------------------------------------------------------------
# Journal rc presets
# ----------------------------------------------------------------------
_NATURE_RC: dict[str, Any] = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7,
    "axes.titlesize": 8,
    "axes.labelsize": 7,
    "axes.linewidth": 0.5,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "legend.fontsize": 6,
    "legend.frameon": False,
    "lines.linewidth": 0.75,
    "lines.markersize": 3,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42,                 # TrueType — editable in Illustrator
    "ps.fonttype": 42,
    "svg.fonttype": "none",             # keep text as text in SVG
    "axes.spines.top": False,
    "axes.spines.right": False,
}

STYLE_PRESETS = {"nature": _NATURE_RC, "publication": _NATURE_RC}


def _apply_rc(style: str) -> None:
    plt.rcParams.update(STYLE_PRESETS.get(style.lower(), _NATURE_RC))


# ----------------------------------------------------------------------
# Plot builders — each returns (fig, ax)
# ----------------------------------------------------------------------
def _volcano(df: pd.DataFrame, ax=None, palette=None, **kw):
    """Volcano plot: x = log2FoldChange, y = -log10(padj)."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(3.5, 3.0))
    else:
        fig = ax.figure

    df = df.copy()
    log2fc = df["log2FoldChange"].to_numpy()
    neg_log10p = -np.log10(np.clip(df["padj"].to_numpy(), 1e-300, 1.0))

    sig = (df["padj"] < 0.05) & (np.abs(df["log2FoldChange"]) > 1)
    up = sig & (df["log2FoldChange"] > 0)
    dn = sig & (df["log2FoldChange"] < 0)
    ns = ~sig

    pal = palette or {}
    c_ns = pal.get("ns", "#BFBFBF")
    c_up = pal.get("up", "#D55E00")
    c_dn = pal.get("down", "#0072B2")

    ax.scatter(log2fc[ns], neg_log10p[ns], s=4, c=c_ns, alpha=0.5,
               linewidths=0, label="NS")
    ax.scatter(log2fc[up], neg_log10p[up], s=6, c=c_up, alpha=0.85,
               linewidths=0, label=f"Up (n={int(up.sum())})")
    ax.scatter(log2fc[dn], neg_log10p[dn], s=6, c=c_dn, alpha=0.85,
               linewidths=0, label=f"Down (n={int(dn.sum())})")

    ax.axhline(-np.log10(0.05), color="0.4", linewidth=0.5, linestyle="--")
    ax.axvline(1.0, color="0.4", linewidth=0.5, linestyle="--")
    ax.axvline(-1.0, color="0.4", linewidth=0.5, linestyle="--")

    label_n = int(kw.get("label_top", 6))
    if "gene" in df.columns and label_n > 0:
        top = df.loc[sig].nsmallest(label_n, "padj").reset_index(drop=True)

        # Compute y-range to convert offset points -> data coords.
        y_pts = (-np.log10(np.clip(top["padj"].to_numpy(float),
                                   1e-300, None)))
        x_pts = top["log2FoldChange"].to_numpy(float)
        y_range = float(neg_log10p.max() - 0) or 1.0

        # Try to use adjustText when available; otherwise fall back to a
        # simple bounded stagger in fractions of the y-axis range.
        try:
            from adjustText import adjust_text  # type: ignore
            texts = []
            for x, y, name in zip(x_pts, y_pts, top["gene"]):
                texts.append(ax.text(x, y, str(name), fontsize=5,
                                     style="italic"))
            adjust_text(texts, ax=ax, arrowprops=dict(
                arrowstyle="-", lw=0.3, color="0.4"))
        except ImportError:
            # No adjustText: spread labels in data coords to avoid overlap.
            for side_mask, ha, x_off in ((x_pts > 0, "left", 0.05),
                                        (x_pts <= 0, "right", -0.05)):
                sub = top.loc[side_mask].sort_values("padj")
                n_side = len(sub)
                if n_side == 0:
                    continue
                # distribute labels evenly across the top half of the y-axis
                slots = np.linspace(0.55, 0.97, n_side) * y_range
                for (idx, row), slot_y in zip(sub.iterrows(), slots):
                    x = float(row["log2FoldChange"])
                    y = -np.log10(max(float(row["padj"]), 1e-300))
                    ax.annotate(
                        str(row["gene"]),
                        xy=(x, y),
                        xytext=(x + x_off * y_range if side_mask.any() and x > 0
                                else x + x_off * y_range, slot_y),
                        fontsize=5, style="italic", ha=ha, va="center",
                        arrowprops=dict(arrowstyle="-", lw=0.3, color="0.4",
                                        shrinkA=0, shrinkB=1),
                    )

    ax.set_xlabel(r"log$_2$ fold change")
    ax.set_ylabel(r"$-\log_{10}$ adjusted $P$")
    # place legend below the axes so it can't collide with point labels
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.18), ncol=3,
              markerscale=1.3, handletextpad=0.3, columnspacing=1.0,
              borderaxespad=0.0, frameon=False)
    y_max = max(neg_log10p.max(), -np.log10(0.05))
    ax.set_ylim(0, y_max * 1.15)
    return fig, ax


def _heatmap(df: pd.DataFrame, ax=None, palette=None, **kw):
    """Row z-scored gene-expression heatmap."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(3.5, 3.2))
    else:
        fig = ax.figure

    mat = df.to_numpy(dtype=float)
    mu = mat.mean(axis=1, keepdims=True)
    sd = mat.std(axis=1, keepdims=True)
    sd[sd == 0] = 1.0
    z = (mat - mu) / sd

    cmap = (palette or {}).get("cmap") or kw.get("cmap", "RdBu_r")
    vmax = float(np.percentile(np.abs(z), 98))
    im = ax.imshow(z, aspect="auto", cmap=cmap, vmin=-vmax, vmax=vmax,
                   interpolation="nearest")

    ax.set_xlabel("Sample")
    ax.set_ylabel("Gene")
    n_genes = z.shape[0]
    if n_genes <= 30 and df.index is not None:
        ax.set_yticks(range(n_genes))
        ax.set_yticklabels([str(g) for g in df.index], fontsize=5,
                           style="italic")
    else:
        ax.set_yticks([])
    ax.set_xticks([])
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("z-score", fontsize=6)
    cbar.ax.tick_params(labelsize=5, width=0.5, length=2)
    cbar.outline.set_linewidth(0.5)
    return fig, ax


def _kaplan_meier(df: pd.DataFrame, ax=None, palette=None, **kw):
    """Kaplan–Meier curve from df with columns time, event, group."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(3.5, 3.0))
    else:
        fig = ax.figure

    groups = list(dict.fromkeys(df["group"]))
    pal = palette or {}
    if isinstance(pal, dict) and "colors" in pal:
        pal = pal["colors"] if isinstance(pal["colors"], dict) else {
            g: pal["colors"][i % len(pal["colors"])]
            for i, g in enumerate(groups)
        }
    default_colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"]

    for gi, g in enumerate(groups):
        sub = df[df["group"] == g].sort_values("time")
        times = np.concatenate([[0.0], sub["time"].to_numpy()])
        surv = [1.0]
        at_risk = len(sub)
        for t in sub["time"]:
            n_ev = int(((sub["time"] == t) & (sub["event"] == 1)).sum())
            n_ce = int(((sub["time"] == t) & (sub["event"] == 0)).sum())
            if at_risk > 0 and n_ev > 0:
                surv.append(surv[-1] * (1.0 - n_ev / at_risk))
            else:
                surv.append(surv[-1])
            at_risk -= (n_ev + n_ce)
        color = pal.get(str(g), default_colors[gi % len(default_colors)])
        ax.step(times, surv, where="post", color=color, linewidth=1.0,
                label=str(g))
        cens = sub[sub["event"] == 0]["time"].to_numpy()
        if len(cens):
            cens_y = np.interp(cens, times, surv)
            ax.plot(cens, cens_y, "|", color=color, markersize=3)

    pval = _logrank_pvalue(df)
    ax.text(0.03, 0.05, f"log-rank $P$ = {pval:.3g}",
            transform=ax.transAxes, fontsize=6)

    ax.set_xlabel("Time (months)")
    ax.set_ylabel("Overall survival")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(left=0)
    ax.legend(loc="upper right")
    return fig, ax


def _logrank_pvalue(df: pd.DataFrame) -> float:
    """Two-group log-rank chi^2 p-value (Peto)."""
    groups = list(dict.fromkeys(df["group"]))
    if len(groups) != 2:
        return float("nan")
    g0, g1 = groups
    O1 = E1 = V1 = 0.0
    event_times = np.sort(df.loc[df["event"] == 1, "time"].unique())
    for t in event_times:
        n0 = int(((df["group"] == g0) & (df["time"] >= t)).sum())
        n1 = int(((df["group"] == g1) & (df["time"] >= t)).sum())
        d0 = int(((df["group"] == g0) & (df["time"] == t) &
                  (df["event"] == 1)).sum())
        d1 = int(((df["group"] == g1) & (df["time"] == t) &
                  (df["event"] == 1)).sum())
        n = n0 + n1
        d = d0 + d1
        if n <= 1 or d == 0:
            continue
        E1 += d * n1 / n
        O1 += d1
        V1 += n0 * n1 * d * (n - d) / (n * n * (n - 1))
    if V1 <= 0:
        return float("nan")
    chi2 = (O1 - E1) ** 2 / V1
    from math import erfc, sqrt
    return float(erfc(sqrt(chi2 / 2.0)))


def _correlation_matrix(df: pd.DataFrame, ax=None, palette=None, **kw):
    """Lower-triangle Pearson correlation heatmap with annotations."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(3.2, 3.0))
    else:
        fig = ax.figure

    corr = df.corr(method="pearson")
    n = corr.shape[0]
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    display = corr.mask(mask)

    cmap = (palette or {}).get("cmap") or kw.get("cmap", "RdBu_r")
    im = ax.imshow(display, cmap=cmap, vmin=-1, vmax=1,
                   interpolation="nearest")

    labels = [str(c) for c in corr.columns]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=5)
    ax.set_yticklabels(labels, fontsize=5)

    for i in range(n):
        for j in range(n):
            if not mask[i, j]:
                val = corr.iloc[i, j]
                color = "white" if abs(val) > 0.6 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=5, color=color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("Pearson $r$", fontsize=6)
    cbar.ax.tick_params(labelsize=5, width=0.5, length=2)
    cbar.outline.set_linewidth(0.5)

    # rotate long y tick labels so they don't clip the right edge
    for lbl in ax.get_yticklabels():
        lbl.set_rotation(0)
        lbl.set_ha("right")
    ax.tick_params(axis="y", pad=1)
    return fig, ax


def _box(df: pd.DataFrame, ax=None, palette=None, **kw):
    """Boxplot across numeric columns."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(3.5, 3.0))
    else:
        fig = ax.figure
    data = [df[c].dropna().to_numpy() for c in df.columns]
    bp = ax.boxplot(data, labels=[str(c) for c in df.columns],
                    patch_artist=True, widths=0.6, showfliers=False,
                    medianprops=dict(color="black", linewidth=0.8),
                    boxprops=dict(linewidth=0.6),
                    whiskerprops=dict(linewidth=0.6),
                    capprops=dict(linewidth=0.6))
    default_colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7",
                      "#F0E442", "#56B4E9"]
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(
            (palette or {}).get(str(df.columns[i]),
                                default_colors[i % len(default_colors)]))
        patch.set_alpha(0.7)
    return fig, ax


_PLOT_BUILDERS = {
    "volcano": _volcano,
    "heatmap": _heatmap,
    "kaplan_meier": _kaplan_meier,
    "km": _kaplan_meier,
    "survival": _kaplan_meier,
    "correlation_matrix": _correlation_matrix,
    "correlation": _correlation_matrix,
    "box": _box,
    "boxplot": _box,
}


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def render(
    figure_data: Any = None,
    viz_type: str = "auto",
    style: str = "publication",
    output_path: Optional[str] = None,
    palette: Optional[dict] = None,
    ax=None,
    **kwargs,
):
    """Render a panel figure. Returns the figure (or the axes if ``ax`` given).
    """
    _apply_rc(style)

    if isinstance(figure_data, dict) and "data" in figure_data:
        palette = palette or figure_data.get("palette")
        figure_data = figure_data["data"]

    builder = _PLOT_BUILDERS.get(viz_type)
    if builder is None:
        raise ValueError(
            f"Unsupported viz_type '{viz_type}'. "
            f"Available: {sorted(_PLOT_BUILDERS)}")

    fig, ax = builder(figure_data, ax=ax, palette=palette, **kwargs)

    if output_path and fig is not None:
        _save_all(fig, output_path)

    return ax if ax is not None else fig


def apply_style(figure: Any = None, style: str = "nature",
                save_path: Optional[str] = None, **_):
    """Apply journal style to an existing figure (mutates it) and optionally save."""
    _apply_rc(style)
    saved: Optional[str] = None
    if figure is not None:
        for ax in figure.get_axes():
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            ax.tick_params(width=0.5, length=2.5)
        figure.canvas.draw_idle()
        if save_path:
            _save_all(figure, save_path)
            saved = save_path
    return {
        "style": style,
        "saved_to": saved,
        "figure_attached": figure is not None,
    }


def _save_all(fig, output_path: str):
    """Save ``fig`` as PDF/PNG/SVG. If ``output_path`` has a known extension,
    only that one is written; otherwise it's treated as a stem."""
    known = (".pdf", ".png", ".svg")
    root, ext = os.path.splitext(output_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if ext.lower() in known:
        fig.savefig(output_path)
        return
    for e in known:
        fig.savefig(root + e)


def run(operation: str, **kwargs):
    """Dispatch shim so the orchestrator can call one entry point."""
    if operation == "render":
        return render(**kwargs)
    if operation == "apply_style":
        return apply_style(**kwargs)
    raise ValueError(f"matplotlib skill: unknown operation '{operation}'")
