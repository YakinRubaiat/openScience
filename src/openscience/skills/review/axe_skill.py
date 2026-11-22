"""axe_core skill: HTML accessibility checks (pure python, html.parser).

Pure-python subset of axe-core checks: images without alt, form inputs
without labels, missing h1, missing lang attribute on <html>, and inline
styles that set tiny font sizes.

Operations: ``analyze_html``, ``violations_report``.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

_INPUT_TYPES_NEEDING_LABEL = {"text", "email", "password", "search", "tel",
                              "url", "number", "date", "checkbox", "radio", "file"}


class _A11yParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.violations: list[dict[str, Any]] = []
        self.has_h1 = False
        self.has_html_tag = False
        self.html_has_lang = False
        self.labels_for: set[str] = set()
        self.input_ids: list[tuple[str | None, int, str]] = []

    def _add(self, rule: str, impact: str, line: int, message: str,
             element: str) -> None:
        self.violations.append({"rule": rule, "impact": impact, "line": line,
                                "message": message, "element": element[:120]})

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k.lower(): (v or "") for k, v in attrs}
        line = self.getpos()[0]
        raw = f"<{tag} {' '.join(k for k, _ in attrs)}>"
        if tag == "html":
            self.has_html_tag = True
            if "lang" not in attr:
                self._add("html-has-lang", "serious", line,
                          "<html> element must have a lang attribute", raw)
        elif tag == "img":
            if "alt" not in attr and attr.get("role") not in ("presentation", "none"):
                self._add("image-alt", "critical", line,
                          "<img> element must have an alt attribute", raw)
        elif tag == "h1":
            self.has_h1 = True
        elif tag == "label":
            if attr.get("for"):
                self.labels_for.add(attr["for"])
        elif tag == "input":
            t = (attr.get("type") or "text").lower()
            if t in _INPUT_TYPES_NEEDING_LABEL:
                labelled = (attr.get("aria-label") or attr.get("aria-labelledby")
                            or attr.get("title"))
                if not labelled:
                    self.input_ids.append((attr.get("id") or None, line, raw))
        style = attr.get("style", "")
        m = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", style)
        if m and float(m.group(1)) < 12:
            self._add("small-font-inline-style", "minor", line,
                      f"inline style sets font-size {m.group(1)}px (<12px)", raw)

    def finalize(self) -> None:
        for input_id, line, raw in self.input_ids:
            if input_id is None or input_id not in self.labels_for:
                self._add("label", "critical", line,
                          "form input has no associated <label>", raw)


def analyze_html(content: str | None = None, path: str | None = None,
                 **kwargs: Any) -> dict[str, Any]:
    """Accessibility-check an HTML document (``content`` or file ``path``)."""
    if content is None:
        if path is None:
            raise ValueError("Provide HTML 'content' or a 'path' to a file")
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    parser = _A11yParser()
    parser.feed(content)
    parser.close()
    parser.finalize()
    if parser.has_html_tag and not parser.has_h1:
        parser._add("page-has-heading-one", "moderate", 1,
                    "page must contain a level-one heading (<h1>)", "<html>")
    return {"status": "ok", "n_violations": len(parser.violations),
            "violations": parser.violations}


def violations_report(content: str | None = None, path: str | None = None,
                      **kwargs: Any) -> dict[str, Any]:
    """Violations grouped by impact and rule."""
    res = analyze_html(content, path)
    by_impact: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    for v in res["violations"]:
        by_impact[v["impact"]] = by_impact.get(v["impact"], 0) + 1
        by_rule[v["rule"]] = by_rule.get(v["rule"], 0) + 1
    return {"status": "ok", "n_violations": res["n_violations"],
            "by_impact": by_impact, "by_rule": by_rule}


run = skill_run({"analyze_html": analyze_html, "violations_report": violations_report})
register_skill("axe_core", run)
