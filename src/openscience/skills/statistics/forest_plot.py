"""Forest plot skill: render meta-analysis results with matplotlib."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _render(
    studies: list[dict[str, Any]],
    pooled: dict[str, Any] | None,
    path: Path,
    title: str,
    x_label: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_rows = len(studies) + (1 if pooled else 0)
    fig, ax = plt.subplots(figsize=(8, max(2, 0.5 * n_rows + 2)))

    ys = list(range(n_rows, 0, -1))
    for row, s in zip(ys[: len(studies)], studies):
        ax.plot([s["ci_lower"], s["ci_upper"]], [row, row], color="#444444", lw=1.5)
        ax.plot(s["effect"], row, "s", color="#1f77b4", ms=8)
    if pooled:
        row = ys[-1]
        mid, lo, hi = pooled["effect"], pooled["ci_lower"], pooled["ci_upper"]
        diamond = [(lo, row), (mid, row + 0.28), (hi, row), (mid, row - 0.28)]
        ax.add_patch(plt.Polygon(diamond, closed=True, color="#d62728", alpha=0.8))
    ax.axvline(0, color="#999999", lw=1, ls="--")

    labels = [s["label"] for s in studies] + ([pooled["label"]] if pooled else [])
    ax.set_yticks(ys, labels)
    ax.set_xlabel(x_label)
    ax.set_title(title)
    ax.set_xlim(auto=True)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def draw(
    studies: Any | None = None,
    pooled: Any | None = None,
    path: str = "forest_plot.png",
    title: str = "Forest plot",
    x_label: str = "Effect size",
    **kwargs: Any,
) -> dict[str, Any]:
    """Draw a forest plot from per-study dicts to a png/svg file."""
    out = Path(path)
    fmt = out.suffix.lstrip(".").lower() or "png"
    if fmt not in ("png", "svg"):
        raise ValueError(f"Unsupported format {fmt!r}; use .png or .svg")
    _render(list(studies or []), dict(pooled) if pooled else None, out, title, x_label)
    return result(
        path=str(out),
        format=fmt,
        n_studies=len(studies or []),
        has_pooled=pooled is not None,
    )


def save_png(**kwargs: Any) -> dict[str, Any]:
    """Alias for draw() that forces a .png filename."""
    path = kwargs.get("path", "forest_plot.png")
    if not str(path).lower().endswith(".png"):
        path = f"{path}.png"
    return draw(**{**kwargs, "path": path})


def save_svg(**kwargs: Any) -> dict[str, Any]:
    """Alias for draw() that forces a .svg filename."""
    path = kwargs.get("path", "forest_plot.svg")
    if not str(path).lower().endswith(".svg"):
        path = f"{path}.svg"
    return draw(**{**kwargs, "path": path})


def from_meta(meta: Any, path: str = "forest_plot.png", **kwargs: Any) -> dict[str, Any]:
    """Render a forest plot directly from ``statsmodels_meta`` forest_data output.

    Accepts the full forest_data result dict, or raw inputs (effect_sizes /
    variances or standard_errors) which are passed through ``statsmodels_meta``
    first.
    """
    from openscience.skills.statistics.meta_analysis import forest_data

    if isinstance(meta, dict) and "studies" in meta:
        data = meta
    else:
        kw = dict(meta or {})
        kw.update({k: v for k, v in kwargs.items() if k in ("variances", "standard_errors", "study_labels", "model", "alpha")})
        data = forest_data(**kw)
    out = draw(
        studies=data["studies"],
        pooled=data.get("pooled"),
        path=path,
        title=kwargs.get("title", "Forest plot"),
        x_label=kwargs.get("x_label", "Effect size"),
    )
    out["model"] = data.get("model")
    out["n_studies"] = data.get("n_studies")
    return out


run = skill_run(
    {
        "draw": draw,
        "save_png": save_png,
        "save_svg": save_svg,
        "from_meta": from_meta,
    }
)

register_skill("forest_plot", run)
