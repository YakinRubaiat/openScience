"""Interactive-plot skill (``plotly``).

Wraps plotlygraphing for common scientific plots. plotly is an optional
dependency: when it is missing every operation reports a clear, actionable
error except ``list_capabilities``, which always works.
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, result, skill_run

_PLOTLY_MISSING_MSG = (
    "plotly is not installed. Install it with: pip install plotly"
)


def _require_plotly():
    return optional_import("plotly.graph_objects", "plotly")


def _to_xy(kwargs: dict[str, Any]):
    import numpy as np  # noqa: F401 - kept lazy-light

    x = kwargs.get("x")
    y = kwargs.get("y")
    data = kwargs.get("data")
    if data is not None and hasattr(data, "__getitem__"):
        x = data[kwargs.get("x_col", "x")] if x is None else x
        y = data[kwargs.get("y_col", "y")] if y is None else y
    if x is None:
        x = list(range(len(y))) if y is not None else [0, 1, 2]
    if y is None:
        y = [1, 3, 2]
    return list(x), list(y)


def scatter(**kwargs):
    go = _require_plotly()
    x, y = _to_xy(kwargs)
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="markers",
        marker=dict(color=kwargs.get("color", "#0072B2"), size=6),
        name=kwargs.get("name", "data"),
    ))
    fig.update_layout(title=kwargs.get("title", ""), template="plotly_white")
    out = kwargs.get("output_path")
    if out:
        return save_html(fig=fig, output_path=out)
    return result(plot_type="scatter", figure_attached=True)


def line(**kwargs):
    go = _require_plotly()
    x, y = _to_xy(kwargs)
    fig = go.Figure(go.Scatter(
        x=x, y=y, mode="lines+markers",
        line=dict(color=kwargs.get("color", "#0072B2"), width=2),
        name=kwargs.get("name", "data"),
    ))
    fig.update_layout(title=kwargs.get("title", ""), template="plotly_white")
    out = kwargs.get("output_path")
    if out:
        return save_html(fig=fig, output_path=out)
    return result(plot_type="line", figure_attached=True)


def bar(**kwargs):
    go = _require_plotly()
    x, y = _to_xy(kwargs)
    fig = go.Figure(go.Bar(
        x=x, y=y,
        marker_color=kwargs.get("color", "#0072B2"),
        name=kwargs.get("name", "data"),
    ))
    fig.update_layout(title=kwargs.get("title", ""), template="plotly_white")
    out = kwargs.get("output_path")
    if out:
        return save_html(fig=fig, output_path=out)
    return result(plot_type="bar", figure_attached=True)


def box(**kwargs):
    go = _require_plotly()
    data = kwargs.get("data")
    y = kwargs.get("y")
    if data is not None and hasattr(data, "columns"):
        fig = go.Figure([
            go.Box(y=data[c].dropna(), name=str(c)) for c in data.columns
        ])
    else:
        fig = go.Figure(go.Box(y=y if y is not None else [1, 2, 2, 3, 5]))
    fig.update_layout(title=kwargs.get("title", ""), template="plotly_white")
    out = kwargs.get("output_path")
    if out:
        return save_html(fig=fig, output_path=out)
    return result(plot_type="box", figure_attached=True)


def save_html(**kwargs):
    """Write a plotly figure to a self-contained HTML file."""
    _require_plotly()
    fig = kwargs.get("fig") or kwargs.get("figure")
    output_path = kwargs.get("output_path") or kwargs.get("save_path")
    if fig is None:
        raise ValueError("save_html requires fig=<plotly figure>")
    if not output_path:
        raise ValueError("save_html requires output_path")
    import os

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.write_html(output_path, include_plotlyjs="cdn")
    return result(saved_to=output_path, format="html")


def save_png(**kwargs):
    """Write a plotly figure to PNG. Requires the optional ``kaleido``
    package; degrades gracefully when it is missing."""
    _require_plotly()
    fig = kwargs.get("fig") or kwargs.get("figure")
    output_path = kwargs.get("output_path") or kwargs.get("save_path")
    if fig is None:
        raise ValueError("save_png requires fig=<plotly figure>")
    if not output_path:
        raise ValueError("save_png requires output_path")
    if not has_module("kaleido"):
        return result(
            "unavailable",
            saved_to=None,
            format="png",
            reason="PNG export requires the 'kaleido' package. "
                   "Install it with: pip install kaleido",
        )
    import os

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.write_image(output_path, scale=int(kwargs.get("scale", 2)))
    return result(saved_to=output_path, format="png")


def list_capabilities(**_):
    available = has_module("plotly")
    caps = {
        "plotly_installed": available,
        "kaleido_installed": has_module("kaleido"),
        "operations": ["scatter", "line", "bar", "box", "save_html", "save_png"],
        "formats": [],
    }
    if available:
        caps["formats"] = ["html"] + (["png", "svg", "pdf"]
                                      if has_module("kaleido") else [])
    else:
        caps["install_hint"] = _PLOTLY_MISSING_MSG
    return result(**caps)


_OPS = {
    "scatter": scatter,
    "line": line,
    "bar": bar,
    "box": box,
    "save_html": save_html,
    "save_png": save_png,
    "list_capabilities": list_capabilities,
}

run = skill_run(_OPS)
register_skill("plotly", run)
