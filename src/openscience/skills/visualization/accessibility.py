"""Colour-accessibility skill (``accessibility_checking``).

WCAG contrast ratios and colour-vision-deficiency (CVD) simulation on plain
RGB math — no heavy dependencies. Complements ``colorbrewer`` (which picks
safe palettes) by *checking* arbitrary palettes.
"""

from __future__ import annotations

import itertools
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    h = color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Not a hex colour: {color!r}")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{int(round(min(max(c, 0.0), 1.0) * 255)):02X}"
                         for c in rgb)


def _lin(c: float) -> float:
    """Linearize one sRGB channel (IEC 61966-2-1)."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(color: str) -> float:
    r, g, b = _hex_to_rgb(color)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


# Viénot, Brettel & Mollon (1999) simplified dichromat transforms.
_CVD_MATRICES = {
    "protanopia": ((0.0, 2.02344, -2.52581),
                   (0.0, 1.0, 0.0),
                   (0.0, 0.0, 1.0)),
    "deuteranopia": ((1.0, 0.0, 0.0),
                     (0.494207, 0.0, 1.24827),
                     (0.0, 0.0, 1.0)),
    "tritanopia": ((1.0, 0.0, 0.0),
                   (0.0, 1.0, 0.0),
                   (-0.395913, 0.801109, 0.0)),
}


def _simulate_one(color: str, deficiency: str) -> str:
    if deficiency not in _CVD_MATRICES:
        raise ValueError(
            f"Unknown deficiency {deficiency!r}. "
            f"Available: {sorted(_CVD_MATRICES)}")
    r, g, b = (_lin(c) for c in _hex_to_rgb(color))
    m = _CVD_MATRICES[deficiency]

    def row(w):
        return w[0] * r + w[1] * g + w[2] * b

    sim = tuple(min(max(row(w), 0.0), 1.0) for w in m)

    def gamma(c):
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055

    return _rgb_to_hex(tuple(gamma(c) for c in sim))


def contrast_ratio(**kwargs) -> dict:
    """WCAG 2.x contrast ratio between two colours (1.0–21.0).

    Parameters: ``color1``, ``color2`` (hex). Also accepts ``foreground`` /
    ``background``. AA thresholds: 4.5 (normal text), 3.0 (large text).
    """
    c1 = kwargs.get("color1") or kwargs.get("foreground") or "#000000"
    c2 = kwargs.get("color2") or kwargs.get("background") or "#FFFFFF"
    l1, l2 = _relative_luminance(c1), _relative_luminance(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    ratio = (hi + 0.05) / (lo + 0.05)
    return result(
        color1=c1, color2=c2,
        contrast_ratio=round(ratio, 3),
        wcag_aa_normal=ratio >= 4.5,
        wcag_aa_large=ratio >= 3.0,
        wcag_aaa_normal=ratio >= 7.0,
    )


def simulate_cb(**kwargs) -> dict:
    """Simulate colour-vision deficiency on one or more colours.

    Parameters: ``colors`` (list of hex, or single ``color`` hex string),
    ``deficiency`` in {deuteranopia, protanopia, tritanopia}. Returns the
    transformed colours as a viewer with that deficiency would see them.
    """
    colors = kwargs.get("colors")
    if colors is None:
        single = kwargs.get("color", "#E69F00")
        colors = [single]
    if isinstance(colors, str):
        colors = [colors]
    deficiency = str(kwargs.get("deficiency") or "deuteranopia")

    transformed = {c: _simulate_one(c, deficiency) for c in colors}
    return result(deficiency=deficiency, original=list(colors),
                  transformed=transformed)


def check_palette(**kwargs) -> dict:
    """Check a palette for CVD safety via deuteranopia simulation.

    Parameters: ``colors`` (list of hex). Reports the minimum pairwise
    perceptual distance (approximate, linear-RGB Euclidean) under each of
    the three deficiencies and flags palettes whose minimum deuteranopia
    distance falls below ``threshold`` (default 0.10).
    """
    colors = kwargs.get("colors") or ["#0072B2", "#D55E00", "#009E73"]
    if isinstance(colors, str):
        colors = [colors]
    threshold = float(kwargs.get("threshold", 0.10))

    def min_dist(deficiency: str) -> float:
        sims = [_hex_to_rgb(_simulate_one(c, deficiency)) for c in colors]
        dists = [sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
                 for a, b in itertools.combinations(sims, 2)]
        return round(min(dists), 4) if dists else 1.0

    distances = {d: min_dist(d) for d in _CVD_MATRICES}
    deut = distances["deuteranopia"]
    return result(
        colors=list(colors),
        n_colors=len(colors),
        min_pairwise_distance=distances,
        colorblind_safe=deut >= threshold,
        threshold=threshold,
        note="Distance is Euclidean in linearized RGB after dichromat "
             "simulation (Viénot et al. 1999); >= ~0.10 is usually "
             "distinguishable.",
    )


_OPS = {
    "check_palette": check_palette,
    "contrast_ratio": contrast_ratio,
    "simulate_cb": simulate_cb,
}

run = skill_run(_OPS)
register_skill("accessibility_checking", run)
