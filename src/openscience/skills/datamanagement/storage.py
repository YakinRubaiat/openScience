"""storage skill: dtype optimisation and efficient serialisation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import has_module, result, skill_run


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame(data)


def optimize_dtypes(data: Any) -> dict[str, Any]:
    """Downcast numeric columns to the smallest safe dtype.

    Integer columns become the smallest signed/unsigned int that fits;
    float columns are downcast to float32 when lossless.
    """
    df = _frame(data)
    before = {str(c): str(t) for c, t in df.dtypes.items()}
    mem_before = int(df.memory_usage(deep=True).sum())
    for col in df.select_dtypes(include="number").columns:
        df[col] = pd.to_numeric(df[col], downcast="integer" if pd.api.types.is_integer_dtype(df[col]) else "float")
    for col in df.select_dtypes(include="object").columns:
        nunique = df[col].nunique(dropna=False)
        if len(df) and nunique / len(df) < 0.5:
            df[col] = df[col].astype("category")
    after = {str(c): str(t) for c, t in df.dtypes.items()}
    mem_after = int(df.memory_usage(deep=True).sum())
    return result(
        memory_before_bytes=mem_before,
        memory_after_bytes=mem_after,
        memory_saved_bytes=mem_before - mem_after,
        dtypes_before=before,
        dtypes_after=after,
        changed={c: {"from": before[c], "to": after[c]}
                 for c in before if before[c] != after[c]},
        data=df.to_dict("records"),
    )


def estimate_size(data: Any) -> dict[str, Any]:
    """Estimate in-memory and csv-serialised sizes of a dataset."""
    df = _frame(data)
    csv_bytes = len(df.to_csv(index=False).encode())
    return result(
        n_rows=int(len(df)),
        n_cols=int(df.shape[1]),
        memory_bytes=int(df.memory_usage(deep=True).sum()),
        csv_bytes=int(csv_bytes),
        per_column_memory={str(c): int(b) for c, b in df.memory_usage(deep=True).items()},
    )


def parquet(data: Any = None, file_path: str | None = None,
            output_path: str | None = None) -> dict[str, Any]:
    """Write a dataset as parquet when pyarrow is available, else csv fallback."""
    df = _frame(data) if data is not None else pd.read_csv(file_path)  # type: ignore[arg-type]
    if output_path is None:
        raise ValueError("parquet requires 'output_path'")
    out = Path(output_path)
    if has_module("pyarrow"):
        df.to_parquet(out, index=False)
        fmt = "parquet"
    else:
        out = out.with_suffix(".csv")
        df.to_csv(out, index=False)
        fmt = "csv-fallback (pyarrow not installed)"
    return result(output_path=str(out), format=fmt,
                  n_rows=int(len(df)), n_cols=int(df.shape[1]),
                  size_bytes=int(out.stat().st_size))


_OPS = {"optimize_dtypes": optimize_dtypes, "estimate_size": estimate_size, "parquet": parquet}

run = skill_run(_OPS)
register_skill("storage_optimization", run)
