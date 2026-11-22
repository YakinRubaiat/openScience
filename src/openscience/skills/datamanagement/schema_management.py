"""schema_management skill: infer and validate dataset schemas."""

from __future__ import annotations

from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_KIND = {
    "integer": "integer", "int": "integer",
    "numeric": "numeric", "float": "numeric", "number": "numeric",
    "boolean": "boolean", "bool": "boolean",
    "datetime": "datetime",
    "string": "string", "str": "string", "object": "string",
}


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


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data
    return pd.DataFrame(data)


def infer_schema(data: Any, max_enum: int = 20) -> dict[str, Any]:
    """Infer a column-type schema from a dataset.

    Per column reports dtype kind, nullability, uniqueness and, for
    low-cardinality string columns, the observed value set (enum).
    """
    df = _frame(data)
    columns: dict[str, Any] = {}
    for col in df.columns:
        s = df[col]
        kind = _kind(s.dtype)
        spec: dict[str, Any] = {
            "type": kind,
            "nullable": bool(s.isna().any()),
            "unique": bool(s.is_unique),
            "n_nulls": int(s.isna().sum()),
        }
        if kind == "string" and s.nunique(dropna=True) <= max_enum:
            spec["enum"] = sorted({str(v) for v in s.dropna().unique()})
        if kind in ("integer", "numeric") and s.notna().any():
            spec["min"] = float(s.min())
            spec["max"] = float(s.max())
        columns[str(col)] = spec
    return result(n_rows=int(len(df)), n_cols=int(df.shape[1]), columns=columns)


def validate_against_schema(data: Any, schema: dict[str, Any]) -> dict[str, Any]:
    """Validate a dataset against a schema produced by :func:`infer_schema`.

    Checks presence, dtype kind, nullability, uniqueness and min/max bounds.
    """
    df = _frame(data)
    errors: list[str] = []
    spec_cols = schema.get("columns", schema)
    for col, spec in spec_cols.items():
        if col not in df.columns:
            errors.append(f"missing column: {col}")
            continue
        s = df[col]
        want = _KIND.get(str(spec.get("type", "string")).lower(), "string")
        actual = _kind(s.dtype)
        if actual != want:
            errors.append(f"{col}: type {actual} != expected {want}")
        if not spec.get("nullable", True) and s.isna().any():
            errors.append(f"{col}: contains nulls")
        if spec.get("unique") and s.duplicated().any():
            errors.append(f"{col}: not unique")
        if actual in ("integer", "numeric") and s.notna().any():
            if "min" in spec and float(s.min()) < float(spec["min"]):
                errors.append(f"{col}: min {float(s.min())} < expected {spec['min']}")
            if "max" in spec and float(s.max()) > float(spec["max"]):
                errors.append(f"{col}: max {float(s.max())} > expected {spec['max']}")
    return result(passed=not errors, errors=errors,
                  columns_checked=[str(c) for c in spec_cols],
                  n_rows=int(len(df)))


_OPS = {"infer_schema": infer_schema, "validate_against_schema": validate_against_schema}

run = skill_run(_OPS)
register_skill("schema_management", run)
