"""Lightweight SVG vector-editing skill (``vector_editing``).

Pure-stdlib SVG manipulations: whitespace/metadata stripping, side-by-side
merging (via a translate transform wrapper) and byte serialization. No
external dependencies.
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)

_METADATA_TAGS = ("metadata", "title", "desc", "defs")


def _read_svg(kwargs: dict[str, Any]) -> str:
    svg_string = kwargs.get("svg_string") or kwargs.get("svg")
    if svg_string is not None:
        return svg_string
    svg_path = kwargs.get("svg_path") or kwargs.get("input_path")
    if not svg_path:
        raise ValueError("operation requires svg_path or svg_string")
    with open(svg_path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write_output(text: str, output_path: str | None) -> str | None:
    if not output_path:
        return None
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return output_path


def optimize(**kwargs) -> dict:
    """Strip comments, metadata/title/desc and inter-tag whitespace from an
    SVG to shrink file size. Geometry is untouched."""
    text = _read_svg(kwargs)
    before = len(text.encode("utf-8"))

    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r">\s+<", "><", text)
    for tag in _METADATA_TAGS:
        text = re.sub(rf"<(?:\w+:)?{tag}\b[^>]*>.*?</(?:\w+:)?{tag}>",
                      "", text, flags=re.DOTALL)
        text = re.sub(rf"<(?:\w+:)?{tag}\b[^>]*/>", "", text)
    text = text.strip()
    after = len(text.encode("utf-8"))

    saved_to = _write_output(text, kwargs.get("output_path"))
    out = result(bytes_before=before, bytes_after=after,
                 reduction_pct=round(100 * (1 - after / max(before, 1)), 1),
                 saved_to=saved_to)
    if saved_to is None:
        out["svg"] = text
    return out


def merge_svgs(**kwargs) -> dict:
    """Merge multiple SVGs side-by-side into one SVG.

    Each input is wrapped in ``<g transform="translate(x,0)">``; widths are
    taken from each SVG's ``width`` attribute or the second component of
    ``viewBox`` (default 600). Heights become the max of all inputs.
    """
    inputs = kwargs.get("inputs") or kwargs.get("svg_paths") or []
    if not inputs:
        raise ValueError("merge_svgs requires inputs=[svg paths]")
    gap = float(kwargs.get("gap", 10))

    def dims(text: str) -> tuple[float, float]:
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return 600.0, 400.0
        w, h = root.get("width"), root.get("height")
        vb = root.get("viewBox")
        if (w is None or h is None) and vb:
            parts = vb.split()
            if len(parts) == 4:
                w = w or parts[2]
                h = h or parts[3]
        return float(w or 600), float(h or 400)

    def inner_content(text: str) -> str:
        m = re.search(r"<svg\b[^>]*>(.*)</svg>", text, flags=re.DOTALL)
        return m.group(1) if m else text

    texts = []
    for inp in inputs:
        if os.path.exists(str(inp)):
            with open(str(inp), "r", encoding="utf-8") as fh:
                texts.append(fh.read())
        else:  # treat as raw SVG string
            texts.append(str(inp))

    sizes = [dims(t) for t in texts]
    total_w = sum(w for w, _ in sizes) + gap * (len(sizes) - 1)
    max_h = max(h for _, h in sizes)

    parts = []
    x = 0.0
    for text, (w, _h) in zip(texts, sizes):
        parts.append(f"<g transform=\"translate({x:g},0)\">"
                     f"{inner_content(text)}</g>")
        x += w + gap

    merged = (f'<svg xmlns="{_SVG_NS}" width="{total_w:g}" '
              f'height="{max_h:g}" viewBox="0 0 {total_w:g} {max_h:g}">'
              + "".join(parts) + "</svg>")

    saved_to = _write_output(merged, kwargs.get("output_path"))
    out = result(n_merged=len(texts), width=total_w, height=max_h,
                 saved_to=saved_to)
    if saved_to is None:
        out["svg"] = merged
    return out


def to_bytes(**kwargs) -> dict:
    """Return an SVG (file or string) as UTF-8 bytes, for pipelines that
    stream figures between steps."""
    text = _read_svg(kwargs)
    data = text.encode("utf-8")
    return result(n_bytes=len(data), svg_bytes=data, encoding="utf-8")


_OPS = {"optimize": optimize, "merge_svgs": merge_svgs, "to_bytes": to_bytes}

run = skill_run(_OPS)
register_skill("vector_editing", run)
