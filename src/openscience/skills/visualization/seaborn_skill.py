"""Seaborn statistical-plot skill (``seaborn``).

Thin wrapper around seaborn for the plots the seaborn_stylist agent makes.
"""

from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from . import matplotlib_skill


def run(
    parameters: Optional[dict] = None,
    context: Optional[dict] = None,
    plot_type: str = "boxplot",
    data: Optional[pd.DataFrame] = None,
    x: Optional[str] = None,
    y: Optional[str] = None,
    hue: Optional[str] = None,
    output_path: Optional[str] = None,
    palette: Optional[dict] = None,
    ax=None,
    **kwargs,
):
    params = dict(parameters or {})
    params.update(
        {
            k: v
            for k, v in dict(
                plot_type=plot_type,
                data=data,
                x=x,
                y=y,
                hue=hue,
                output_path=output_path,
                palette=palette,
            ).items()
            if v is not None
        }
    )
    params.update(kwargs)

    data = params["data"]
    plot_type = params["plot_type"]

    matplotlib_skill._apply_rc(params.get("style", "nature"))
    sns.set_style(
        "ticks",
        {
            "axes.linewidth": 0.5,
            "xtick.major.width": 0.5,
            "ytick.major.width": 0.5,
        },
    )
    # seaborn resets rcParams; re-apply ours on top
    matplotlib_skill._apply_rc(params.get("style", "nature"))

    ax_was_provided = ax is not None
    if ax is None:
        fig, ax = plt.subplots(figsize=(3.5, 3.0))
    else:
        fig = ax.figure

    kw = dict(
        ax=ax,
        data=data,
        x=params.get("x"),
        y=params.get("y"),
        hue=params.get("hue"),
        palette=params.get("palette"),
    )
    kw = {k: v for k, v in kw.items() if v is not None}

    # Default to Okabe-Ito when caller did not provide an explicit palette
    if "palette" not in kw or kw["palette"] is None:
        kw["palette"] = ["#0072B2", "#D55E00", "#009E73", "#CC79A7",
                         "#E69F00", "#56B4E9", "#F0E442", "#000000"]

    if plot_type == "boxplot":
        sns.boxplot(**kw, linewidth=0.6, fliersize=1.5, width=0.6)
    elif plot_type == "violin":
        sns.violinplot(**kw, linewidth=0.6, inner="quartile")
    elif plot_type == "strip":
        sns.stripplot(**kw, size=2, alpha=0.6, jitter=0.25, edgecolor="none")
    elif plot_type == "swarm":
        sns.swarmplot(**kw, size=2.5)
    elif plot_type == "regplot":
        kw.pop("ax", None)
        sns.regplot(**kw, ax=ax, scatter_kws=dict(s=6, alpha=0.7), line_kws=dict(linewidth=1.0))
    elif plot_type == "clustermap":
        # clustermap creates its own fig; pass through
        cm = sns.clustermap(
            data.corr() if params.get("corr") else data,
            cmap="RdBu_r",
            center=0,
            figsize=(3.5, 3.5),
            linewidths=0,
        )
        out = params.get("output_path")
        if out:
            matplotlib_skill._save_all(cm.figure, out)
        return cm.figure
    else:
        raise ValueError(f"seaborn skill: unknown plot_type '{plot_type}'")

    sns.despine(ax=ax)

    out = params.get("output_path")
    if out:
        matplotlib_skill._save_all(fig, out)

    return ax if ax_was_provided else fig
