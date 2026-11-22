"""Multi-panel figure composition skill (``matplotlib_gridspec``).

Takes a list of panel specifications and draws them into a single
publication-quality multi-panel figure with panel labels (a, b, c, ...).
"""

from __future__ import annotations

from typing import Iterable, Optional

import matplotlib.pyplot as plt
from matplotlib import gridspec

from . import matplotlib_skill

_PANEL_LABEL_KW = dict(fontsize=9, fontweight="bold", va="top", ha="left")


def _normalize_panels(panels: Iterable[dict]) -> list[dict]:
    """Accept either a list of dicts or a dict-of-dicts and normalize."""
    if isinstance(panels, dict):
        panels = [dict(v, name=k) for k, v in panels.items()]
    return [dict(p) for p in panels]


def run(
    parameters: Optional[dict] = None,
    context: Optional[dict] = None,
    output_path: Optional[str] = None,
    panels: Optional[Iterable[dict]] = None,
    layout: Optional[tuple[int, int]] = None,
    figsize: Optional[tuple[float, float]] = None,
    panel_labels: bool = True,
    style: str = "nature",
    title: Optional[str] = None,
    width_ratios: Optional[list[float]] = None,
    height_ratios: Optional[list[float]] = None,
    hspace: float = 0.35,
    wspace: float = 0.30,
    **kwargs,
):
    """Compose a multi-panel figure.

    Each panel dict has keys:
        viz_type   : one of the matplotlib_skill plot builders
        data       : pandas DataFrame
        palette    : optional dict of colours
        title      : optional panel title
        row/col    : optional explicit grid location
        rowspan/colspan : optional span
        kwargs     : optional dict of extra builder kwargs
    """
    params = dict(parameters or {})
    params.update(
        {
            k: v
            for k, v in dict(
                panels=panels,
                layout=layout,
                figsize=figsize,
                panel_labels=panel_labels,
                style=style,
                title=title,
                output_path=output_path,
                width_ratios=width_ratios,
                height_ratios=height_ratios,
                hspace=hspace,
                wspace=wspace,
            ).items()
            if v is not None
        }
    )
    params.update(kwargs)

    panels = _normalize_panels(params["panels"])
    n = len(panels)

    matplotlib_skill._apply_rc(params.get("style", "nature"))

    layout = params.get("layout")
    if layout is None:
        # auto: near-square grid
        import math

        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        layout = (rows, cols)
    rows, cols = layout

    figsize = params.get("figsize")
    if figsize is None:
        # Nature double-column ~183mm ≈ 7.2in; single ~89mm ≈ 3.5in
        figsize = (3.5 * cols, 2.8 * rows)

    fig = plt.figure(figsize=figsize)
    gs = gridspec.GridSpec(
        rows,
        cols,
        figure=fig,
        width_ratios=params.get("width_ratios"),
        height_ratios=params.get("height_ratios"),
        hspace=params.get("hspace", 0.35),
        wspace=params.get("wspace", 0.30),
        left=0.08,
        right=0.96,
        top=0.94,
        bottom=0.08,
    )

    letters = "abcdefghijklmnopqrstuvwxyz"
    for i, panel in enumerate(panels):
        row = panel.get("row", i // cols)
        col = panel.get("col", i % cols)
        rowspan = panel.get("rowspan", 1)
        colspan = panel.get("colspan", 1)
        ax = fig.add_subplot(gs[row : row + rowspan, col : col + colspan])

        viz = panel.get("viz_type")
        data = panel.get("data")
        palette = panel.get("palette")
        build_kw = dict(panel.get("kwargs", {}))

        matplotlib_skill.render(
            figure_data=data,
            viz_type=viz,
            style=params.get("style", "nature"),
            palette=palette,
            ax=ax,
            **build_kw,
        )

        if panel.get("title"):
            ax.set_title(panel["title"], fontsize=7, loc="left", pad=2)

        if params.get("panel_labels", True):
            ax.text(-0.18, 1.08, letters[i], transform=ax.transAxes, **_PANEL_LABEL_KW)

    if params.get("title"):
        fig.suptitle(params["title"], fontsize=9, y=0.99)

    out = params.get("output_path")
    if out:
        matplotlib_skill._save_all(fig, out)

    return fig
