"""Validation rules skill: required fields, type checks, range checks, regex checks, reports."""

from __future__ import annotations

import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_TYPE_MAP = {
    "int": int,
    "float": (int, float),
    "str": str,
    "bool": bool,
    "numeric": (int, float),
    "list": list,
    "dict": dict,
}


def _as_records(data: Any) -> list[dict[str, Any]]:
    """Accept a list of dicts, a dict of column->list, or a pandas DataFrame."""
    if hasattr(data, "to_dict"):  # pandas DataFrame
        return data.to_dict(orient="records")
    if isinstance(data, dict):
        keys = list(data)
        length = max((len(v) for v in data.values()), default=0)
        return [{k: data[k][i] for k in keys} for i in range(length)]
    if isinstance(data, list):
        return data
    raise ValueError("data must be a list of dicts, dict of columns, or a pandas DataFrame")


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def required(
    data: Any,
    fields: list[str] | None = None,
    required_fields: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Check that required fields are present and non-missing in every record."""
    fields = fields or required_fields
    if not fields:
        raise ValueError("provide fields=[...] of required field names")
    records = _as_records(data)
    violations: list[dict[str, Any]] = []
    for i, rec in enumerate(records):
        for f in fields:
            if f not in rec or _is_missing(rec.get(f)):
                violations.append({"row": i, "field": f, "error": "missing or empty"})
    return result(
        valid=not violations,
        n_records=len(records),
        violations=violations,
        n_violations=len(violations),
    )


def types(
    data: Any,
    schema: dict[str, str] | None = None,
    types_map: dict[str, str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Check column types: schema maps column -> one of int/float/str/bool/numeric/list/dict."""
    schema = schema or types_map
    if not schema:
        raise ValueError("provide schema={col: type}")
    records = _as_records(data)
    violations: list[dict[str, Any]] = []
    for i, rec in enumerate(records):
        for col, tname in schema.items():
            if col not in rec or _is_missing(rec.get(col)):
                continue  # missing handled by `required`
            py_types = _TYPE_MAP.get(tname)
            if py_types is None:
                raise ValueError(f"Unknown type {tname!r}. Use one of {sorted(_TYPE_MAP)}")
            val = rec[col]
            # bool is a subclass of int; exclude it for int/numeric checks
            if tname in ("int", "float", "numeric") and isinstance(val, bool):
                violations.append({"row": i, "field": col, "error": f"expected {tname}, got bool"})
                continue
            if not isinstance(val, py_types):
                violations.append(
                    {"row": i, "field": col, "error": f"expected {tname}, got {type(val).__name__}"}
                )
    return result(
        valid=not violations,
        n_records=len(records),
        violations=violations,
        n_violations=len(violations),
    )


def ranges(
    data: Any,
    rules: dict[str, dict[str, float]] | None = None,
    min: float | None = None,  # noqa: A002 - public API
    max: float | None = None,  # noqa: A002 - public API
    column: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Check numeric ranges. Either rules={col: {min, max}} or column=... min=... max=..."""
    if rules is None:
        if column is None:
            raise ValueError("provide rules={col: {min, max}} or column/min/max")
        rules = {column: {}}
        if min is not None:
            rules[column]["min"] = min
        if max is not None:
            rules[column]["max"] = max
    records = _as_records(data)
    violations: list[dict[str, Any]] = []
    for i, rec in enumerate(records):
        for col, bounds in rules.items():
            if col not in rec or _is_missing(rec.get(col)):
                continue
            val = rec[col]
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                violations.append({"row": i, "field": col, "error": "not numeric"})
                continue
            lo, hi = bounds.get("min"), bounds.get("max")
            if lo is not None and val < lo:
                violations.append({"row": i, "field": col, "error": f"{val} < min {lo}", "value": val})
            if hi is not None and val > hi:
                violations.append({"row": i, "field": col, "error": f"{val} > max {hi}", "value": val})
    return result(
        valid=not violations,
        n_records=len(records),
        violations=violations,
        n_violations=len(violations),
    )


def regex_rule(
    data: Any,
    column: str | None = None,
    pattern: str | None = None,
    rules: dict[str, str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Check that string values match a regex. rules={col: pattern} or column/pattern."""
    if rules is None:
        if column is None or pattern is None:
            raise ValueError("provide rules={col: pattern} or column=... pattern=...")
        rules = {column: pattern}
    compiled = {c: re.compile(p) for c, p in rules.items()}
    records = _as_records(data)
    violations: list[dict[str, Any]] = []
    for i, rec in enumerate(records):
        for col, rx in compiled.items():
            if col not in rec or _is_missing(rec.get(col)):
                continue
            val = rec[col]
            if not isinstance(val, str) or not rx.fullmatch(val):
                violations.append(
                    {"row": i, "field": col, "error": f"does not match /{rx.pattern}/", "value": val}
                )
    return result(
        valid=not violations,
        n_records=len(records),
        violations=violations,
        n_violations=len(violations),
    )


def report(
    data: Any,
    required_fields: list[str] | None = None,
    schema: dict[str, str] | None = None,
    range_rules: dict[str, dict[str, float]] | None = None,
    regex_rules: dict[str, str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run all selected checks and combine into one report."""
    records = _as_records(data)
    checks: dict[str, Any] = {}
    all_violations: list[dict[str, Any]] = []
    if required_fields:
        r = required(records, fields=required_fields)
        checks["required"] = r
        all_violations += [{"check": "required", **v} for v in r["violations"]]
    if schema:
        r = types(records, schema=schema)
        checks["types"] = r
        all_violations += [{"check": "types", **v} for v in r["violations"]]
    if range_rules:
        r = ranges(records, rules=range_rules)
        checks["ranges"] = r
        all_violations += [{"check": "ranges", **v} for v in r["violations"]]
    if regex_rules:
        r = regex_rule(records, rules=regex_rules)
        checks["regex"] = r
        all_violations += [{"check": "regex", **v} for v in r["violations"]]
    return result(
        valid=not all_violations,
        n_records=len(records),
        n_violations=len(all_violations),
        violations=all_violations,
        checks=checks,
    )


run = skill_run(
    {
        "required": required,
        "types": types,
        "ranges": ranges,
        "regex_rule": regex_rule,
        "report": report,
    }
)

register_skill("validation_rules", run)
