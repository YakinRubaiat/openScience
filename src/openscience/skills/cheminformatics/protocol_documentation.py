"""Protocol documentation rendering skill.

Registers:
- ``protocol_documentation``
"""

from __future__ import annotations

from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _render_markdown(title: str, sections: dict[str, Any]) -> str:
    out = [f"# {title}", ""]
    for section_name, content in sections.items():
        out.append(f"## {section_name}")
        out.append("")
        if isinstance(content, list):
            for item in content:
                out.append(f"- {item}")
        else:
            out.append(str(content))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_markdown(
    title: str,
    sections: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Render a simple protocol document to Markdown.

    ``sections`` maps a section heading to either a string blob or a list
    of bullet lines.
    """
    if not title or not title.strip():
        raise ValueError("Empty title")
    if not isinstance(sections, dict) or not sections:
        raise ValueError("sections must be a non-empty dict")
    md = _render_markdown(title.strip(), sections)
    return result(markdown=md, title=title, n_sections=len(sections))


def checklist(
    steps: list[str],
    title: str = "Protocol checklist",
    **kwargs: Any,
) -> dict[str, Any]:
    """Render a numbered step list as a Markdown checkbox list."""
    if not steps:
        raise ValueError("steps must be a non-empty list")
    lines = [f"# {title}", ""]
    for i, step in enumerate(steps, start=1):
        lines.append(f"{i}. [ ] {step}")
    lines.append("")
    md = "\n".join(lines)
    return result(markdown=md, title=title, n_steps=len(steps))


def materials_table(
    reagents: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Render a list of reagent dicts as a Markdown table."""
    if not reagents:
        raise ValueError("reagents must be a non-empty list")
    keys = sorted({k for r in reagents for k in r.keys()})
    header = "| " + " | ".join(keys) + " |"
    sep = "|" + "|".join("---" for _ in keys) + "|"
    rows = [
        "| " + " | ".join(str(r.get(k, "")) for k in keys) + " |"
        for r in reagents
    ]
    md = "\n".join([header, sep] + rows) + "\n"
    return result(markdown=md, columns=keys, n_rows=len(rows))


run = skill_run(
    {
        "render_markdown": render_markdown,
        "checklist": checklist,
        "materials_table": materials_table,
    }
)

register_skill("protocol_documentation", run)
