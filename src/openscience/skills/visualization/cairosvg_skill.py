"""SVG rasterization skill (``cairosvg``).

``svg2png`` needs the optional ``cairosvg`` package; it degrades with a
clear, actionable error when missing. ``validate_svg`` is pure stdlib
(``xml.etree``) and always available.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import optional_import, result, skill_run

_SVG_NS = "{http://www.w3.org/2000/svg}"


def svg2png(**kwargs) -> dict:
    """Rasterize an SVG file/string to PNG. Requires ``cairosvg``."""
    csvg = optional_import("cairosvg")
    svg_path = kwargs.get("svg_path") or kwargs.get("input_path")
    svg_string = kwargs.get("svg_string") or kwargs.get("svg")
    output_path = kwargs.get("output_path") or kwargs.get("png_path")
    if not output_path:
        raise ValueError("svg2png requires output_path")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if svg_string is not None:
        csvg.svg2png(bytestring=svg_string.encode("utf-8"),
                     write_to=output_path,
                     scale=float(kwargs.get("scale", 1.0)))
    elif svg_path:
        csvg.svg2png(url=svg_path, write_to=output_path,
                     scale=float(kwargs.get("scale", 1.0)))
    else:
        raise ValueError("svg2png requires svg_path or svg_string")
    return result(saved_to=output_path, format="png")


def validate_svg(**kwargs) -> dict:
    """Validate that a file/string is well-formed SVG (stdlib XML parse).

    Returns the root tag, element count, width/height/viewBox if declared,
    and any parse error. Never raises for malformed input — reports instead.
    """
    svg_path = kwargs.get("svg_path") or kwargs.get("input_path")
    svg_string = kwargs.get("svg_string") or kwargs.get("svg")
    if svg_string is None:
        if not svg_path:
            raise ValueError("validate_svg requires svg_path or svg_string")
        try:
            with open(svg_path, "r", encoding="utf-8") as fh:
                svg_string = fh.read()
        except OSError as exc:
            return result("error", valid=False, error=str(exc))

    try:
        root = ET.fromstring(svg_string)
    except ET.ParseError as exc:
        return result("error", valid=False, error=f"XML parse error: {exc}")

    is_svg = root.tag in ("svg", f"{_SVG_NS}svg")
    return result(
        valid=is_svg,
        root_tag=root.tag,
        element_count=sum(1 for _ in root.iter()),
        width=root.get("width"),
        height=root.get("height"),
        viewBox=root.get("viewBox"),
    )


_OPS = {"svg2png": svg2png, "validate_svg": validate_svg}

run = skill_run(_OPS)
register_skill("cairosvg", run)
