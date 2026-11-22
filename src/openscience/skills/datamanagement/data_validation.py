"""data_validation skill: real dataset quality checks."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_TYPE_MAP = {
    "int": "integer", "integer": "integer", "float": "numeric", "number": "numeric",
    "numeric": "numeric", "str": "string", "string": "string", "object": "string",
    "bool": "boolean", "boolean": "boolean", "datetime": "datetime",
}


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data
    return pd.DataFrame(data)


def _kind(dtype) -> str:
    if pd.api.types.is_integer_dtype(dtype):
        return "integer"
    if pd.api.types.is_float_dtype(dtype):
        return "numeric"
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "datetime"
    return "string"


def check_nulls(data: Any, columns: list[str] | None = None) -> dict[str, Any]:
    """Count nulls per column and flag columns that contain any."""
    df = _frame(data)
    cols = columns or list(df.columns)
    counts = {str(c): int(df[c].isna().sum()) for c in cols}
    return result(
        null_counts=counts,
        columns_with_nulls=[c for c, n in counts.items() if n > 0],
        total_nulls=int(sum(counts.values())),
        passed=all(n == 0 for n in counts.values()),
    )


def check_types(data: Any, expected: dict[str, str] | None = None) -> dict[str, Any]:
    """Report actual dtype kinds per column; optionally compare to expected.

    ``expected`` maps column names to one of: integer, numeric, string,
    boolean, datetime (aliases accepted).
    """
    df = _frame(data)
    actual = {str(c): _kind(dt) for c, dt in df.dtypes.items()}
    mismatches: dict[str, dict[str, str]] = {}
    if expected:
        for col, want in expected.items():
            want_kind = _TYPE_MAP.get(str(want).lower())
            if want_kind is None:
                raise ValueError(f"Unknown expected type {want!r}")
            if col not in df.columns:
                mismatches[col] = {"expected": want_kind, "actual": "missing"}
            elif actual[col] != want_kind:
                mismatches[col] = {"expected": want_kind, "actual": actual[col]}
    return result(actual_types=actual, mismatches=mismatches, passed=not mismatches)


def check_range(data: Any, column: str, min_value: float | None = None,
                max_value: float | None = None) -> dict[str, Any]:
    """Check that all non-null values of a column fall within [min, max]."""
    df = _frame(data)
    vals = pd.to_numeric(df[column], errors="raise").dropna()
    too_low = vals[vals < min_value] if min_value is not None else vals.iloc[0:0]
    too_high = vals[vals > max_value] if max_value is not None else vals.iloc[0:0]
    violations = {
        "below_min": too_low.tolist(),
        "above_max": too_high.tolist(),
    }
    return result(
        column=column,
        n_checked=int(len(vals)),
        min_observed=float(vals.min()) if len(vals) else None,
        max_observed=float(vals.max()) if len(vals) else None,
        violations=violations,
        passed=not violations["below_min"] and not violations["above_max"],
    )


def check_unique(data: Any, columns: list[str] | str) -> dict[str, Any]:
    """Check that a column (or column combination) holds unique values."""
    df = _frame(data)
    cols = [columns] if isinstance(columns, str) else list(columns)
    dup_mask = df.duplicated(subset=cols, keep=False)
    dupes = dup_mask.sum()
    return result(
        columns=cols,
        n_rows=int(len(df)),
        n_duplicate_rows=int(dupes),
        duplicate_rows=df.loc[dup_mask, cols].to_dict("records")[:100],
        passed=int(dupes) == 0,
    )


def schema_validate(data: Any, schema: dict[str, Any]) -> dict[str, Any]:
    """Validate a dataset against a schema dict.

    Schema format::

        {"columns": {"age": {"type": "integer", "required": True,
                             "min": 0, "max": 120, "allow_null": False}}}
    """
    df = _frame(data)
    errors: list[str] = []
    spec_cols = schema.get("columns", {})
    for col, spec in spec_cols.items():
        if spec.get("required", True) and col not in df.columns:
            errors.append(f"missing required column: {col}")
            continue
        if col not in df.columns:
            continue
        want = spec.get("type")
        if want and _kind(df[col].dtype) != _TYPE_MAP.get(str(want).lower(), want):
            errors.append(f"{col}: expected type {want}, got {_kind(df[col].dtype)}")
        if not spec.get("allow_null", True) and df[col].isna().any():
            errors.append(f"{col}: contains nulls but allow_null=False")
        try:
            vals = pd.to_numeric(df[col], errors="coerce") if _kind(df[col].dtype) in ("integer", "numeric") else None
        except (TypeError, ValueError):
            vals = None
        if vals is not None:
            if "min" in spec and bool((vals < spec["min"]).any()):
                errors.append(f"{col}: values below min {spec['min']}")
            if "max" in spec and bool((vals > spec["max"]).any()):
                errors.append(f"{col}: values above max {spec['max']}")
        if spec.get("unique") and bool(df[col].duplicated().any()):
            errors.append(f"{col}: values not unique")
    return result(passed=not errors, errors=errors,
                  n_rows=int(len(df)), columns_checked=list(spec_cols))


def report(data: Any) -> dict[str, Any]:
    """Full quality report: nulls, types, duplicates, numeric ranges."""
    df = _frame(data)
    nulls = check_nulls(data)
    types = check_types(data)
    numeric = df.select_dtypes(include="number")
    ranges = {
        str(c): {"min": float(np.nanmin(df[c])), "max": float(np.nanmax(df[c])),
                 "mean": float(np.nanmean(df[c]))}
        for c in numeric.columns if df[c].notna().any()
    }
    return result(
        n_rows=int(len(df)),
        n_cols=int(df.shape[1]),
        nulls=nulls["null_counts"],
        dup_rows=int(df.duplicated().sum()),
        dtypes=types["actual_types"],
        numeric_ranges=ranges,
    )


_OPS = {
    "check_nulls": check_nulls,
    "check_types": check_types,
    "check_range": check_range,
    "check_unique": check_unique,
    "schema_validate": schema_validate,
    "report": report,
}

run = skill_run(_OPS)
register_skill("data_validation", run)
