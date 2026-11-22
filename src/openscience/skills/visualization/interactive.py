"""Interactive-visualization skill (``interactive_viz``).

Produces HTML interactive figures. Uses plotly when available; otherwise
falls back to a matplotlib PNG embedded as base64 in a minimal HTML page,
so the operation always produces *something* viewable in a browser.
"""

from __future__ import annotations

import base64
import io
import os
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, result, skill_run


def _mpl_fig_to_html(fig, title: str = "figure") -> str:
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title></head><body>"
        f"<h3>{title}</h3>"
        f"<img src='data:image/png;base64,{b64}' alt='{title}'>"
        "</body></html>"
    )


def _write_html(html: str, output_path: str) -> dict:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return result(saved_to=output_path, format="html", bytes=len(html))


def scatter_matrix_html(**kwargs):
    """Plotly scatter-matrix (splom) if plotly exists, else a static
    matplotlib scatter matrix embedded in HTML."""
    data = kwargs.get("data")
    output_path = kwargs.get("output_path") or kwargs.get("save_path")
    if data is None:
        raise ValueError("scatter_matrix_html requires data=<DataFrame>")

    if has_module("plotly"):
        px = optional_import("plotly.express", "plotly")
        dims = kwargs.get("dimensions") or list(data.columns)
        fig = px.scatter_matrix(data, dimensions=list(dims),
                                color=kwargs.get("color"))
        fig.update_layout(title=kwargs.get("title", "Scatter matrix"))
        html = fig.to_html(include_plotlyjs="cdn")
        backend = "plotly"
    else:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        pd_plot = optional_import("pandas.plotting", "pandas")
        cols = kwargs.get("dimensions") or list(data.columns)
        axes = pd_plot.scatter_matrix(data[list(cols)], figsize=(8, 8),
                                      diagonal="hist")
        fig = axes[0, 0].figure
        html = _mpl_fig_to_html(fig, kwargs.get("title", "Scatter matrix"))
        backend = "matplotlib"

    if output_path:
        out = _write_html(html, output_path)
        out["backend"] = backend
        return out
    return result(html=html, backend=backend)


def heatmap_html(**kwargs):
    """Annotated correlation-heatmap HTML (plotly if present, else static)."""
    data = kwargs.get("data")
    output_path = kwargs.get("output_path") or kwargs.get("save_path")
    if data is None:
        raise ValueError("heatmap_html requires data=<DataFrame>")

    corr = data.corr(numeric_only=True)

    if has_module("plotly"):
        px = optional_import("plotly.express", "plotly")
        fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                        zmin=-1, zmax=1, title=kwargs.get("title", ""))
        html = fig.to_html(include_plotlyjs="cdn")
        backend = "plotly"
    else:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(5, 4))
        im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1,
                       interpolation="nearest")
        ax.set_xticks(range(len(corr)))
        ax.set_yticks(range(len(corr)))
        ax.set_xticklabels([str(c) for c in corr.columns], rotation=45,
                           ha="right", fontsize=7)
        ax.set_yticklabels([str(c) for c in corr.columns], fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        fig.tight_layout()
        html = _mpl_fig_to_html(fig, kwargs.get("title", "Heatmap"))
        backend = "matplotlib"

    if output_path:
        out = _write_html(html, output_path)
        out["backend"] = backend
        return out
    return result(html=html, backend=backend)


def save(**kwargs):
    """Save a figure (plotly or matplotlib) as self-contained HTML.

    Accepts ``fig=`` plus ``output_path=``. Detects the figure type and
    serializes accordingly; matplotlib figures are embedded as base64 PNG.
    """
    fig = kwargs.get("fig") or kwargs.get("figure")
    output_path = kwargs.get("output_path") or kwargs.get("save_path")
    if fig is None:
        raise ValueError("save requires fig=<plotly or matplotlib figure>")
    if not output_path:
        raise ValueError("save requires output_path")

    if has_module("plotly"):
        go = optional_import("plotly.graph_objects", "plotly")
        if isinstance(fig, go.Figure):
            return _write_html(fig.to_html(include_plotlyjs="cdn"),
                               output_path) | {"backend": "plotly"}
    html = _mpl_fig_to_html(fig, kwargs.get("title", "figure"))
    return _write_html(html, output_path) | {"backend": "matplotlib"}


_OPS = {
    "scatter_matrix_html": scatter_matrix_html,
    "heatmap_html": heatmap_html,
    "save": save,
}

run = skill_run(_OPS)
register_skill("interactive_viz", run)
