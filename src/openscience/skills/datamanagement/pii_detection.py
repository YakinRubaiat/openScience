"""pii_detection skill: regex-based PII scanning over datasets."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_PATTERNS: dict[str, str] = {
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phone": r"(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
}

_COMPILED = {name: re.compile(pat) for name, pat in _PATTERNS.items()}


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data
    return pd.DataFrame(data)


def _scan_value(value: Any) -> dict[str, int]:
    if not isinstance(value, str):
        return {}
    hits: dict[str, int] = {}
    for name, rx in _COMPILED.items():
        matches = rx.findall(value)
        if matches:
            hits[name] = hits.get(name, 0) + len(matches)
    return hits


def scan(data: Any, columns: list[str] | None = None,
         sample_examples: bool = True) -> dict[str, Any]:
    """Scan string cells for email/phone/SSN/IP/credit-card patterns.

    Returns per-column PII type counts and (optionally) redacted examples.
    """
    df = _frame(data)
    cols = columns or [c for c in df.columns if df[c].dtype == object]
    findings: dict[str, dict[str, int]] = {}
    examples: dict[str, dict[str, list[str]]] = {}
    for col in cols:
        col_hits: dict[str, int] = {}
        col_examples: dict[str, set[str]] = {}
        for value in df[col].tolist():
            if not isinstance(value, str):
                continue
            for name, rx in _COMPILED.items():
                matches = rx.findall(value)
                if matches:
                    col_hits[name] = col_hits.get(name, 0) + len(matches)
                    col_examples.setdefault(name, set()).add(matches[0])
        if col_hits:
            findings[str(col)] = col_hits
            if sample_examples:
                examples[str(col)] = {
                    k: sorted(v)[:3] for k, v in col_examples.items()
                }
    total = sum(sum(v.values()) for v in findings.values())
    return result(
        n_rows=int(len(df)),
        columns_scanned=[str(c) for c in cols],
        findings=findings,
        examples=examples if sample_examples else {},
        total_pii_hits=int(total),
        pii_found=total > 0,
    )


def report_columns(data: Any) -> dict[str, Any]:
    """List only the columns that contain PII, with type counts."""
    res = scan(data, sample_examples=False)
    flagged = {
        col: hits for col, hits in res["findings"].items() if hits
    }
    return result(
        pii_columns=sorted(flagged),
        findings=flagged,
        n_pii_columns=len(flagged),
    )


_OPS = {"scan": scan, "report_columns": report_columns}

run = skill_run(_OPS)
register_skill("pii_detection", run)
