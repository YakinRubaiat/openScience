"""Grammar-of-graphics skill (``plotnine``).

plotnine (Python ggplot) is an optional dependency. When it is missing
every operation raises a clear, actionable error; a separate
``capabilities`` probe stays available via ``has_module``.
"""

from __future__ import annotations

import os
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, result, skill_run


def _require_plotnine():
    return optional_import("plotnine")


def ggplot_scatter(**kwargs) -> dict:
    """Build a ggplot scatter: ``ggplot(data, aes(x, y, color)) + geom_point()``.

    Parameters: ``data`` (DataFrame, optional — a synthetic one is used when
    omitted), ``x``, ``y``, ``color`` (column name), ``title``,
    ``output_path``.
    """
    p9 = _require_plotnine()
    data = kwargs.get("data")
    if data is None:
        import numpy as np
        import pandas as pd

        rng = np.random.default_rng(0)
        data = pd.DataFrame({
            "x": rng.normal(size=50),
            "y": rng.normal(size=50),
            "group": ["a"] * 25 + ["b"] * 25,
        })
    x = kwargs.get("x") or data.columns[0]
    y = kwargs.get("y") or data.columns[1]
    color = kwargs.get("color")

    aes_kw: dict[str, Any] = {"x": x, "y": y}
    if color:
        aes_kw["color"] = color
    plot = p9.ggplot(data, p9.aes(**aes_kw)) + p9.geom_point(size=2)
    if kwargs.get("title"):
        plot = plot + p9.ggtitle(str(kwargs["title"]))
    plot = plot + p9.theme_minimal()

    output_path = kwargs.get("output_path")
    saved_to = None
    if output_path:
        saved_to = save(plot=plot, output_path=output_path)["saved_to"]
    return result(plot_type="ggplot_scatter", saved_to=saved_to,
                  figure_attached=output_path is None,
                  n_rows=len(data))


def save(**kwargs) -> dict:
    """Save a plotnine ggplot object to PNG/PDF/SVG."""
    _require_plotnine()
    plot = kwargs.get("plot") or kwargs.get("fig") or kwargs.get("figure")
    output_path = kwargs.get("output_path") or kwargs.get("save_path")
    if plot is None:
        raise ValueError("save requires plot=<plotnine ggplot>")
    if not output_path:
        raise ValueError("save requires output_path")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    plot.save(output_path, dpi=int(kwargs.get("dpi", 150)), verbose=False)
    return result(saved_to=output_path,
                  format=os.path.splitext(output_path)[1].lstrip("."))


def capabilities(**_) -> dict:
    return result(plotnine_installed=has_module("plotnine"),
                  install_hint=None if has_module("plotnine")
                  else "pip install plotnine")


_OPS = {"ggplot_scatter": ggplot_scatter, "save": save,
        "capabilities": capabilities}

run = skill_run(_OPS)
register_skill("plotnine", run)
