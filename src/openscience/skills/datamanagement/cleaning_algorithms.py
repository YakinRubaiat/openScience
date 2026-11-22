"""cleaning_algorithms skill: real pandas-based data cleaning operations."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame(data)


def _finished(df: pd.DataFrame, extra: dict[str, Any]) -> dict[str, Any]:
    return result(n_rows=int(len(df)), data=df.to_dict("records"), **extra)


def dropna(data: Any, columns: list[str] | None = None,
           how: str = "any", threshold: int | None = None) -> dict[str, Any]:
    """Drop rows (or columns via ``axis=1`` semantics) with missing values."""
    df = _frame(data)
    before = len(df)
    if threshold is not None:
        out = df.dropna(thresh=threshold, subset=columns)
    else:
        out = df.dropna(subset=columns, how=how)
    return _finished(out, {"n_dropped": int(before - len(out))})


def fillna(data: Any, value: Any = None, method: str | None = None,
           columns: list[str] | None = None) -> dict[str, Any]:
    """Fill missing values with a constant, a per-column dict, or a strategy.

    ``method`` may be ``mean``, ``median``, ``mode``, ``ffill`` or ``bfill``.
    """
    df = _frame(data)
    n_null_before = int(df.isna().sum().sum())
    cols = columns or list(df.columns)
    out = df.copy()
    for col in cols:
        if method in ("mean", "median") and pd.api.types.is_numeric_dtype(out[col]):
            filler = getattr(out[col], method)()
            out[col] = out[col].fillna(filler)
        elif method == "mode":
            mode = out[col].mode(dropna=True)
            if not mode.empty:
                out[col] = out[col].fillna(mode.iloc[0])
        elif method in ("ffill", "bfill"):
            out[col] = getattr(out[col], method)()
        elif method is None:
            fill_value = value.get(col) if isinstance(value, dict) else value
            out[col] = out[col].fillna(fill_value)
        else:
            raise ValueError(f"Unknown fillna method {method!r}")
    return _finished(out, {
        "n_nulls_before": n_null_before,
        "n_nulls_after": int(out.isna().sum().sum()),
    })


def drop_duplicates(data: Any, columns: list[str] | None = None,
                    keep: str = "first") -> dict[str, Any]:
    """Drop duplicate rows on all columns or a subset."""
    df = _frame(data)
    before = len(df)
    out = df.drop_duplicates(subset=columns, keep=keep)
    return _finished(out.reset_index(drop=True), {"n_dropped": int(before - len(out))})


def strip_strings(data: Any, columns: list[str] | None = None,
                  chars: str | None = None) -> dict[str, Any]:
    """Strip whitespace (or ``chars``) from string cells."""
    df = _frame(data)
    cols = columns or [c for c in df.columns if df[c].dtype == object]
    changed = 0
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            raise ValueError(f"Unknown column {col!r}")
        s = out[col].astype("string")
        stripped = s.str.strip(chars)
        changed += int((s != stripped).sum())
        out[col] = stripped
    return _finished(out, {"columns_stripped": [str(c) for c in cols], "n_cells_changed": changed})


def fix_dtypes(data: Any, schema: dict[str, str] | None = None) -> dict[str, Any]:
    """Convert column dtypes to an explicit schema or smart inference.

    ``schema`` maps column -> target type name (int/float/str/datetime/bool).
    Without a schema, uses pandas ``convert_dtypes`` plus numeric downcasting.
    """
    df = _frame(data)
    before = {str(c): str(t) for c, t in df.dtypes.items()}
    out = df.copy()
    if schema:
        for col, target in schema.items():
            if col not in out.columns:
                raise ValueError(f"Unknown column {col!r}")
            t = str(target).lower()
            if t in ("int", "integer"):
                out[col] = pd.to_numeric(out[col], errors="raise").astype("Int64")
            elif t in ("float", "numeric", "number"):
                out[col] = pd.to_numeric(out[col], errors="raise")
            elif t in ("str", "string"):
                out[col] = out[col].astype("string")
            elif t == "datetime":
                out[col] = pd.to_datetime(out[col], errors="raise")
            elif t == "bool":
                out[col] = out[col].astype(bool)
            else:
                raise ValueError(f"Unsupported target dtype {target!r}")
    else:
        out = out.convert_dtypes()
        for col in out.select_dtypes(include=["integer", "floating"]).columns:
            out[col] = pd.to_numeric(out[col], downcast="integer" if pd.api.types.is_integer_dtype(out[col]) else "float")
        out = out.replace({pd.NA: np.nan})
    after = {str(c): str(t) for c, t in out.dtypes.items()}
    changed = {c: {"from": before[c], "to": after[c]} for c in before if before[c] != after[c]}
    return _finished(out, {"dtypes_before": before, "dtypes_after": after, "changed": changed})


_OPS = {
    "dropna": dropna,
    "fillna": fillna,
    "drop_duplicates": drop_duplicates,
    "strip_strings": strip_strings,
    "fix_dtypes": fix_dtypes,
}

run = skill_run(_OPS)
register_skill("cleaning_algorithms", run)
