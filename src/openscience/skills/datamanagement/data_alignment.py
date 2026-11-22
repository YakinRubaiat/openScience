"""data_alignment skill: align datasets to shared sample sets and order."""

from __future__ import annotations

from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame(data)


def align_samples(data: Any, sample_order: list[Any],
                  id_column: str) -> dict[str, Any]:
    """Reorder and subset rows of ``data`` to match ``sample_order`` exactly.

    Missing samples raise KeyError-style errors so pipelines fail loudly
    instead of silently misaligning matrices.
    """
    df = _frame(data)
    if id_column not in df.columns:
        raise ValueError(f"Missing id column {id_column!r}")
    if df[id_column].duplicated().any():
        raise ValueError(f"Duplicate ids in {id_column!r}; alignment requires unique ids")
    indexed = df.set_index(id_column)
    missing = [s for s in sample_order if s not in indexed.index]
    if missing:
        raise ValueError(f"Samples not present in data: {missing[:10]}" +
                         ("..." if len(missing) > 10 else ""))
    aligned = indexed.loc[sample_order].reset_index()
    extra = [str(v) for v in indexed.index if v not in set(sample_order)]
    return result(
        n_samples=int(len(aligned)),
        n_dropped=len(extra),
        dropped_ids=extra[:100],
        sample_ids=[str(v) for v in aligned[id_column]],
        data=aligned.to_dict("records"),
    )


def join_on(left: Any, right: Any, on: str,
            how: str = "inner") -> dict[str, Any]:
    """Join two datasets on a shared key column."""
    ldf, rdf = _frame(left), _frame(right)
    if on not in ldf.columns or on not in rdf.columns:
        raise ValueError(f"Join key {on!r} must exist in both datasets")
    merged = ldf.merge(rdf, on=on, how=how)
    return result(
        n_rows=int(len(merged)),
        n_cols=int(merged.shape[1]),
        join=how,
        on=on,
        data=merged.to_dict("records"),
    )


def reorder(data: Any, columns: list[str] | None = None,
            sort_by: str | None = None, ascending: bool = True) -> dict[str, Any]:
    """Reorder columns and/or sort rows."""
    df = _frame(data)
    if columns is not None:
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise ValueError(f"Unknown columns: {missing}")
        rest = [c for c in df.columns if c not in columns]
        df = df[list(columns) + rest]
    if sort_by is not None:
        if sort_by not in df.columns:
            raise ValueError(f"Unknown sort column {sort_by!r}")
        df = df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)
    return result(n_rows=int(len(df)), columns=[str(c) for c in df.columns],
                  data=df.to_dict("records"))


_OPS = {"align_samples": align_samples, "join_on": join_on, "reorder": reorder}

run = skill_run(_OPS)
register_skill("data_alignment", run)
