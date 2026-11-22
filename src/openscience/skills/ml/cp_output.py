"""CellProfiler output skill: read object CSV exports, per-image aggregates,
and border-cell filtering.

Operations
----------
- ``read_objects_csv``      — read a CellProfiler objects CSV into records
- ``per_image_aggregates``  — mean/median per numeric feature grouped by image
- ``filter_border_cells``   — drop objects touching the image border
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import skill_run, unwrap


def _read_df(kw: dict[str, Any]) -> pd.DataFrame:
    if "dataframe" in kw:
        return pd.DataFrame(kw["dataframe"])
    path = Path(kw.get("path") or kw.get("csv_path") or "")
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path)


def read_objects_csv(**kwargs: Any) -> dict[str, Any]:
    """Read a CellProfiler objects CSV, returning records and column info."""
    kw = unwrap(kwargs)
    df = _read_df(kw)
    max_rows = kw.get("max_rows")
    records = df.to_dict(orient="records")
    if max_rows is not None:
        records = records[: int(max_rows)]
    return {
        "n_rows": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
        "columns": [str(c) for c in df.columns],
        "records": records,
    }


def per_image_aggregates(**kwargs: Any) -> dict[str, Any]:
    """Mean/median per numeric feature grouped by image.

    Parameters: ``dataframe`` or ``path``/``csv_path``; optional
    ``image_col`` (default ``"ImageNumber"``) and ``features`` (default: all
    numeric columns except the image/object id columns).
    """
    kw = unwrap(kwargs)
    df = _read_df(kw)
    image_col = kw.get("image_col", "ImageNumber")
    if image_col not in df.columns:
        raise ValueError(f"Image column {image_col!r} not in CSV columns")

    features = kw.get("features")
    if features is None:
        skip = {image_col, "ObjectNumber"}
        features = [
            c for c in df.columns if c not in skip and pd.api.types.is_numeric_dtype(df[c])
        ]
    features = [str(f) for f in features]

    grouped = df.groupby(image_col)
    aggregates: dict[str, Any] = {}
    for image_id, sub in grouped:
        entry: dict[str, Any] = {"n_objects": int(len(sub))}
        for f in features:
            vals = sub[f].to_numpy(dtype=float, na_value=np.nan)
            vals = vals[np.isfinite(vals)]
            if vals.size == 0:
                entry[f] = {"mean": None, "median": None}
            else:
                entry[f] = {
                    "mean": float(np.mean(vals)),
                    "median": float(np.median(vals)),
                }
        aggregates[str(image_id)] = entry
    return {"image_col": image_col, "features": features, "per_image": aggregates}


def filter_border_cells(**kwargs: Any) -> dict[str, Any]:
    """Remove objects whose centroid lies within ``margin`` px of the border.

    Parameters: ``dataframe``/``path``; ``x_col`` (default
    ``"AreaShape_Center_X"``), ``y_col`` (default ``"AreaShape_Center_Y"``),
    ``width``/``height`` (image dimensions), ``margin`` (px, default 0, i.e.
    centroid exactly on the border counts as border).
    Returns the kept records plus counts.
    """
    kw = unwrap(kwargs)
    df = _read_df(kw)
    x_col = kw.get("x_col", "AreaShape_Center_X")
    y_col = kw.get("y_col", "AreaShape_Center_Y")
    width = float(kw["width"])
    height = float(kw["height"])
    margin = float(kw.get("margin", 0))

    for col in (x_col, y_col):
        if col not in df.columns:
            raise ValueError(f"Centroid column {col!r} not in CSV columns")

    x = df[x_col].to_numpy(dtype=float)
    y = df[y_col].to_numpy(dtype=float)
    keep = (x >= margin) & (x <= width - margin) & (y >= margin) & (y <= height - margin)

    kept = df.loc[keep]
    return {
        "n_input": int(len(df)),
        "n_kept": int(len(kept)),
        "n_removed": int(len(df) - len(kept)),
        "records": kept.to_dict(orient="records"),
    }


run = skill_run(
    {
        "read_objects_csv": read_objects_csv,
        "per_image_aggregates": per_image_aggregates,
        "filter_border_cells": filter_border_cells,
    }
)

register_skill("cellprofiler_output", run)
