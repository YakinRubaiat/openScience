"""Journal style-sheet skill (``style_sheets``).

Applies journal rcParams presets (nature / science / ieee / minimal) to
matplotlib. Complements ``matplotlib_skill.apply_style`` (which only knows
the nature preset) — kept separate so style metadata can be listed and
inspected without touching pyplot state.
"""

from __future__ import annotations

from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_BASE: dict[str, Any] = {
    "font.family": "sans-serif",
    "axes.linewidth": 0.5,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
}

_NATURE: dict[str, Any] = {
    **_BASE,
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 7,
    "axes.titlesize": 8,
    "axes.labelsize": 7,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "legend.frameon": False,
    "lines.linewidth": 0.75,
    "lines.markersize": 3,
}

_SCIENCE: dict[str, Any] = {
    **_BASE,
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "legend.frameon": False,
    "lines.linewidth": 1.0,
    "lines.markersize": 4,
}

_IEEE: dict[str, Any] = {
    **_BASE,
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "lines.linewidth": 1.0,
    "lines.markersize": 4,
    "grid.linewidth": 0.4,
}

_MINIMAL: dict[str, Any] = {
    **_BASE,
    "font.sans-serif": ["DejaVu Sans"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.frameon": False,
    "axes.spines.left": False,
}

STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "nature": _NATURE,
    "science": _SCIENCE,
    "ieee": _IEEE,
    "minimal": _MINIMAL,
}


def list_styles(**_) -> dict:
    """List available journal style presets and their key font sizes."""
    return result(
        styles=sorted(STYLE_PRESETS),
        details={
            name: {"font.size": rc.get("font.size"),
                   "font.family": rc.get("font.family"),
                   "savefig.dpi": rc.get("savefig.dpi")}
            for name, rc in STYLE_PRESETS.items()
        },
    )


def rcparams_dict(**kwargs) -> dict:
    """Return the rcParams dict for a named style without applying it."""
    name = str(kwargs.get("name") or kwargs.get("style") or "nature").lower()
    if name not in STYLE_PRESETS:
        raise ValueError(
            f"Unknown style {name!r}. Available: {sorted(STYLE_PRESETS)}")
    return result(name=name, rcparams=dict(STYLE_PRESETS[name]))


def apply(**kwargs) -> dict:
    """Apply a journal style preset. Optionally mutates a figure and saves."""
    name = str(kwargs.get("name") or kwargs.get("style") or "nature").lower()
    if name not in STYLE_PRESETS:
        raise ValueError(
            f"Unknown style {name!r}. Available: {sorted(STYLE_PRESETS)}")
    plt.rcParams.update(STYLE_PRESETS[name])

    applied_to: list[str] = []
    saved_to = None
    ax = kwargs.get("ax")
    figure = kwargs.get("figure") or kwargs.get("fig")
    if ax is not None:
        for spine in ("top", "right"):
            if not STYLE_PRESETS[name].get(f"axes.spines.{spine}", True):
                ax.spines[spine].set_visible(False)
        ax.tick_params(width=STYLE_PRESETS[name].get("axes.linewidth", 0.5),
                       length=2.5)
        applied_to.append("axes")
    if figure is not None:
        for a in figure.get_axes():
            for spine in ("top", "right"):
                if not STYLE_PRESETS[name].get(f"axes.spines.{spine}", True):
                    a.spines[spine].set_visible(False)
        figure.canvas.draw_idle()
        applied_to.append("figure")

    save_path = kwargs.get("save_path") or kwargs.get("output_path")
    if save_path and figure is not None:
        import os

        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        figure.savefig(save_path)
        saved_to = save_path

    return result(style=name, applied_to=applied_to or ["rcParams"],
                  saved_to=saved_to)


_OPS = {"apply": apply, "list_styles": list_styles,
        "rcparams_dict": rcparams_dict}

run = skill_run(_OPS)
register_skill("style_sheets", run)
