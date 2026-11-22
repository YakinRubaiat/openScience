"""fulltext_parser skill: parse JATS XML, extract methods and figure legends."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_METHODS_HINTS = ("method", "material", "experimental", "procedure", "protocol")


def parse_jats(**kwargs: Any) -> dict[str, Any]:
    """Parse JATS article XML into title + list of {heading, text} sections."""
    xml_text = unwrap(kwargs).get("xml") or ""
    sections: list[dict[str, str]] = []
    title = ""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return result(title=title, sections=sections, count=0)
    title_el = root.find(".//article-title")
    if title_el is not None:
        title = "".join(title_el.itertext()).strip()
    for sec in root.findall(".//body//sec"):
        head_el = sec.find("./title")
        heading = "".join(head_el.itertext()).strip() if head_el is not None else ""
        text = " ".join(
            " ".join("".join(p.itertext()).split()) for p in sec.iter() if p.tag == "p"
        ).strip()
        sections.append({"heading": heading, "text": text})
    return result(title=title, sections=sections, count=len(sections))


def extract_methods_section(**kwargs: Any) -> dict[str, Any]:
    """Return the concatenated text of likely-methods sections from JATS XML."""
    xml_text = unwrap(kwargs).get("xml") or ""
    parsed = parse_jats(xml=xml_text)
    texts = [
        s["text"]
        for s in parsed["sections"]
        if any(h in s["heading"].lower() for h in _METHODS_HINTS) and s["text"]
    ]
    return result(methods_text="\n\n".join(texts), count=len(texts))


def extract_fig_legends(**kwargs: Any) -> dict[str, Any]:
    """Return figure captions (label + caption text) from JATS XML."""
    xml_text = unwrap(kwargs).get("xml") or ""
    legends: list[dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return result(legends=legends, count=0)
    for fig in root.findall(".//fig"):
        label_el = fig.find("./label")
        cap_el = fig.find("./caption")
        legends.append(
            {
                "label": "".join(label_el.itertext()).strip() if label_el is not None else "",
                "caption": " ".join("".join(cap_el.itertext()).split())
                if cap_el is not None
                else "",
            }
        )
    return result(legends=legends, count=len(legends))


_OPS = {
    "parse_jats": parse_jats,
    "extract_methods_section": extract_methods_section,
    "extract_fig_legends": extract_fig_legends,
}


def run(operation: str = "run", **kwargs: Any) -> dict[str, Any]:
    """Dispatch to an operation; ``run`` defaults to ``parse_jats``."""
    op = _OPS.get(operation) or _OPS["parse_jats"]
    if operation not in _OPS and operation != "run":
        raise ValueError(f"Unknown operation {operation!r}. Available: {sorted(_OPS)}")
    return op(**kwargs)


register_skill("fulltext_parser", run)
