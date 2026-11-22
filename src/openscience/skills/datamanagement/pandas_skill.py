"""Pandas skill: real DataFrame I/O and manipulation operations.

Operations work on files (read_*/to_*) or on data passed as records
(list-of-dicts) / column-dict for in-memory operations (describe, filter,
join, shape). Results are JSON-serialisable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _to_frame(data: Any) -> pd.DataFrame:
    """Coerce records / column-dict / DataFrame into a DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data
    if data is None:
        raise ValueError("pandas skill requires a 'data' argument (records or column dict)")
    return pd.DataFrame(data)


def _frame_summary(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "columns": [str(c) for c in df.columns],
    }


def _read(path: str | Path, **kwargs) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p, kwargs


def read_csv(file_path: str, **kwargs) -> dict[str, Any]:
    """Read a CSV file and return shape/columns plus the records."""
    p, kw = _read(file_path, **kwargs)
    df = pd.read_csv(p, **kw)
    return result(**_frame_summary(df), data=df.to_dict("records"))


def read_tsv(file_path: str, **kwargs) -> dict[str, Any]:
    """Read a tab-separated file."""
    p, kw = _read(file_path, **kwargs)
    df = pd.read_csv(p, sep="\t", **kw)
    return result(**_frame_summary(df), data=df.to_dict("records"))


def read_json(file_path: str, **kwargs) -> dict[str, Any]:
    """Read a JSON file (records-oriented by default)."""
    p, kw = _read(file_path, **kwargs)
    df = pd.read_json(p, **kw)
    return result(**_frame_summary(df), data=df.to_dict("records"))


def read_excel(file_path: str, **kwargs) -> dict[str, Any]:
    """Read an Excel workbook (first sheet by default)."""
    p, kw = _read(file_path, **kwargs)
    df = pd.read_excel(p, **kw)
    return result(**_frame_summary(df), data=df.to_dict("records"))


def describe(data: Any) -> dict[str, Any]:
    """Summary statistics for numeric columns plus dtype info."""
    df = _to_frame(data)
    desc = df.describe(include="all")
    stats = {
        str(col): {str(k): (None if pd.isna(v) else float(v) if isinstance(v, (int, float)) else str(v))
                   for k, v in desc[col].items()}
        for col in desc.columns
    }
    return result(**_frame_summary(df),
                  dtypes={str(c): str(t) for c, t in df.dtypes.items()},
                  stats=stats)


def shape(data: Any = None, file_path: str | None = None) -> dict[str, Any]:
    """Return shape, columns, dtypes of a dataset (alias: info)."""
    if file_path is not None:
        df = pd.read_csv(file_path)
    else:
        df = _to_frame(data)
    return result(**_frame_summary(df),
                  dtypes={str(c): str(t) for c, t in df.dtypes.items()},
                  null_counts={str(c): int(n) for c, n in df.isna().sum().items()})


def filter(data: Any, condition: str | None = None,
           column: str | None = None, value: Any = None,
           op: str = "==") -> dict[str, Any]:
    """Filter rows by a pandas query string or a single column comparison."""
    df = _to_frame(data)
    if condition:
        out = df.query(condition)
    elif column is not None:
        col = df[column]
        ops = {
            "==": col == value, "!=": col != value, ">": col > value,
            "<": col < value, ">=": col >= value, "<=": col <= value,
            "isin": col.isin(value if isinstance(value, list) else [value]),
            "contains": col.astype(str).str.contains(str(value), na=False),
        }
        if op not in ops:
            raise ValueError(f"Unknown filter op {op!r}; available: {sorted(ops)}")
        out = df[ops[op]]
    else:
        raise ValueError("filter requires 'condition' or 'column'")
    return result(n_rows=int(len(out)), data=out.to_dict("records"))


def join(left: Any, right: Any, on: str | list[str] | None = None,
         how: str = "inner", left_on: str | None = None,
         right_on: str | None = None) -> dict[str, Any]:
    """Join two datasets (records or column dicts)."""
    ldf, rdf = _to_frame(left), _to_frame(right)
    if how not in ("inner", "left", "right", "outer"):
        raise ValueError(f"Unknown join type {how!r}")
    merged = pd.merge(ldf, rdf, on=on, how=how,
                      left_on=left_on, right_on=right_on)
    return result(**_frame_summary(merged), data=merged.to_dict("records"))


def to_csv(data: Any, output_path: str, index: bool = False) -> dict[str, Any]:
    """Write records to CSV."""
    df = _to_frame(data)
    df.to_csv(output_path, index=index)
    return result(path=str(output_path), **_frame_summary(df))


def to_json(data: Any, output_path: str, orient: str = "records") -> dict[str, Any]:
    """Write records to JSON."""
    import json as _json

    df = _to_frame(data)
    if orient == "records":
        Path(output_path).write_text(_json.dumps(df.to_dict("records"), default=str))
    else:
        df.to_json(output_path, orient=orient)
    return result(path=str(output_path), **_frame_summary(df))


_OPS = {
    "read_csv": read_csv,
    "read_excel": read_excel,
    "read_json": read_json,
    "read_tsv": read_tsv,
    "describe": describe,
    "filter": filter,
    "join": join,
    "to_csv": to_csv,
    "to_json": to_json,
    "shape": shape,
    "info": shape,
}

run = skill_run(_OPS)
register_skill("pandas", run)
