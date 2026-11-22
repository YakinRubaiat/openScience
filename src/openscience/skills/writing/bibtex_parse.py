"""BibTeX parsing skill (deterministic, pure ``re``).

Implements ``bibtex_parsing``:

- ``parse``: parse BibTeX text into a list of entry dicts with keys
  ``entry_type``, ``key`` and one key per BibTeX field (lowercased).
  Handles braces and quoted field values with nested braces.
- ``get``: fetch a field from a parsed entry with an optional default.
"""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, unwrap

_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.IGNORECASE)
_FIELD_NAME_RE = re.compile(r"(\w+)\s*=", re.IGNORECASE)


def _read_value(body: str, pos: int) -> tuple[str, int]:
    """Read a field value starting at ``pos`` (after '='). Returns (value, end)."""
    n = len(body)
    while pos < n and body[pos] in " \t\n":
        pos += 1
    if pos >= n:
        return "", pos
    if body[pos] == "{":
        depth = 0
        start = pos + 1
        i = pos
        while i < n:
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
                if depth == 0:
                    return body[start:i], i + 1
            i += 1
        return body[start:], n
    if body[pos] == '"':
        start = pos + 1
        i = start
        depth = 0
        while i < n:
            ch = body[i]
            if ch == "{":
                depth += 1
            elif ch == "}" and depth:
                depth -= 1
            elif ch == '"' and depth == 0:
                return body[start:i], i + 1
            i += 1
        return body[start:], n
    # bare token (number or macro)
    start = pos
    while pos < n and body[pos] not in ",\n":
        pos += 1
    return body[start:pos].strip(), pos


def parse(text: str = "", **_: Any) -> dict[str, Any]:
    """Parse BibTeX ``text`` into a list of entry dicts."""
    entries: list[dict[str, Any]] = []
    for m in _ENTRY_RE.finditer(text):
        entry_type = m.group(1).lower()
        key = m.group(2)
        body_start = m.end()
        # find the matching closing brace for this entry
        depth = 1
        i = body_start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[body_start:i - 1]

        entry: dict[str, Any] = {"entry_type": entry_type, "key": key}
        pos = 0
        for fm in _FIELD_NAME_RE.finditer(body):
            value, _ = _read_value(body, fm.end())
            value = re.sub(r"\s+", " ", value).strip()
            entry[fm.group(1).lower()] = value
        entries.append(entry)
    return result(entries=entries, count=len(entries))


def get(entry: Any = None, field: str = "", default: Any = None, **_: Any) -> dict[str, Any]:
    """Return ``entry[field]`` (case-insensitive) or ``default``."""
    if not isinstance(entry, dict):
        return result(value=default, found=False, field=field)
    field_l = field.lower()
    if field_l in entry:
        return result(value=entry[field_l], found=True, field=field_l)
    return result(value=default, found=False, field=field_l)


_OPERATIONS = {"parse": parse, "get": get}


def run(operation: str = "run", **kwargs: Any) -> Any:
    op = _OPERATIONS.get(operation) or _OPERATIONS["parse"]
    if operation not in _OPERATIONS and operation != "run":
        raise ValueError(
            f"Unknown operation {operation!r}. Available: {sorted(_OPERATIONS)}"
        )
    return op(**unwrap(kwargs))


register_skill("bibtex_parsing", run)
