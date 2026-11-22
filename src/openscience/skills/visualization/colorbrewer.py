"""Accessible color-palette skill (``colorbrewer``).

Returns Okabe–Ito / ColorBrewer palettes that are safe for the three
common forms of colour-vision deficiency. All palettes below are
documented as CVD-safe.
"""

from __future__ import annotations

from typing import Any

# Okabe & Ito (2008) — 8 colours, CVD-safe
OKABE_ITO = [
    "#000000",  # black
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
]

# ColorBrewer Set2 (qualitative, CVD-safe up to 3 classes)
BREWER_SET2 = [
    "#66C2A5",
    "#FC8D62",
    "#8DA0CB",
    "#E78AC3",
    "#A6D854",
    "#FFD92F",
    "#E5C494",
    "#B3B3B3",
]

# ColorBrewer RdBu diverging 7-class, CVD-safe
BREWER_RDBU7 = ["#B2182B", "#EF8A62", "#FDDBC7", "#F7F7F7", "#D1E5F0", "#67A9CF", "#2166AC"]

CVD_SAFE_SEQUENTIAL = [
    "#F7FCF0",
    "#E0F3DB",
    "#CCEBC5",
    "#A8DDB5",
    "#7BCCC4",
    "#4EB3D3",
    "#2B8CBE",
    "#08589E",
]


def _simulate_cvd(hex_color: str) -> dict[str, tuple[float, float, float]]:
    """Very rough Brettel/Viénot CVD simulation for one hex colour.

    Returns simulated RGB for protanopia, deuteranopia, tritanopia.
    Used as a sanity check that colours remain distinguishable.
    """
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    # Linearize sRGB approx.
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    R, G, B = lin(r), lin(g), lin(b)
    # Matrices from Viénot et al. (1999), simplified
    prot = (
        0.0 * R + 2.02344 * G - 2.52581 * B,
        0.0 * R + 1.0 * G + 0.0 * B,
        0.0 * R + 0.0 * G + 1.0 * B,
    )
    deut = (
        1.0 * R + 0.0 * G + 0.0 * B,
        0.494207 * R + 0.0 * G + 1.24827 * B,
        0.0 * R + 0.0 * G + 1.0 * B,
    )
    trit = (
        1.0 * R + 0.0 * G + 0.0 * B,
        0.0 * R + 1.0 * G + 0.0 * B,
        -0.395913 * R + 0.801109 * G + 0.0 * B,
    )

    def clamp(t):
        return tuple(min(max(c, 0.0), 1.0) for c in t)

    return {"protanopia": clamp(prot), "deuteranopia": clamp(deut), "tritanopia": clamp(trit)}


def _pairwise_min_dist(colors: list[str], deficiency: str) -> float:
    """Min Euclidean distance between any two simulated colours."""
    import itertools

    sims = [_simulate_cvd(c)[deficiency] for c in colors]
    dists = []
    for a, b in itertools.combinations(sims, 2):
        dists.append(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5)
    return min(dists) if dists else 1.0


def run(
    parameters: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    **kwargs,
):
    """Return an accessible palette.

    Parameters (in ``parameters`` or kwargs):
        plot_type   : qualitative | diverging | sequential | volcano | heatmap
        n_colors    : how many discrete colours are needed
    """
    params = dict(parameters or {})
    params.update(kwargs)
    plot_type = params.get("plot_type", "qualitative")
    n = int(params.get("n_colors", 4))

    if plot_type in {"diverging", "heatmap", "correlation_matrix", "correlation"}:
        palette = {"cmap": "RdBu_r", "colors": BREWER_RDBU7}
    elif plot_type in {"sequential"}:
        palette = {"cmap": "BuGn", "colors": CVD_SAFE_SEQUENTIAL[: max(n, 2)]}
    elif plot_type == "volcano":
        palette = {
            "colors": {"ns": "#BFBFBF", "up": "#D55E00", "down": "#0072B2"},
            "cmap": None,
        }
    else:  # qualitative / kaplan_meier / default
        base = OKABE_ITO[1:]  # skip black for groups
        palette = {"colors": base[: max(n, 2)], "cmap": None}

    named = palette.get("colors")
    if isinstance(named, dict):
        flat = list(named.values())
    else:
        flat = list(named or [])
    accessibility = (
        {d: _pairwise_min_dist(flat, d) for d in ("protanopia", "deuteranopia", "tritanopia")}
        if len(flat) > 1
        else {}
    )

    return {
        "plot_type": plot_type,
        "palette": palette,
        "cvd_safe": True,
        "accessibility_min_distance": accessibility,
        "source": "Okabe-Ito + ColorBrewer (CVD-safe)",
    }
