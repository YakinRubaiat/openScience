"""format_converters skill: convert datasets between tabular formats.

Supported tabular formats: csv, tsv, json, excel. ``h5ad-lite`` writes a
single-cell-style HDF5 (X matrix + obs/var tables) via anndata when
available, otherwise raises a clear dependency error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, result, skill_run

_FORMATS = ["csv", "tsv", "json", "excel", "h5ad-lite"]


def _read_any(path: Path, fmt: str) -> pd.DataFrame:
    if fmt == "csv":
        return pd.read_csv(path)
    if fmt == "tsv":
        return pd.read_csv(path, sep="\t")
    if fmt == "json":
        return pd.read_json(path)
    if fmt == "excel":
        return pd.read_excel(path)
    if fmt in ("h5ad", "h5ad-lite"):
        ad = optional_import("anndata")
        adata = ad.read_h5ad(path)
        df = pd.DataFrame(adata.obs.copy())
        for col in adata.var.columns:
            df[f"var_{col}"] = list(adata.var[col])
        x = adata.X
        df["X_sum"] = np.asarray(x.sum(axis=1)).ravel() if hasattr(x, "sum") else None
        return df
    raise ValueError(f"Unsupported source format {fmt!r}")


def _write_any(df: pd.DataFrame, path: Path, fmt: str) -> None:
    if fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "tsv":
        df.to_csv(path, sep="\t", index=False)
    elif fmt == "json":
        df.to_json(path, orient="records")
    elif fmt == "excel":
        df.to_excel(path, index=False)
    elif fmt == "h5ad-lite":
        ad = optional_import("anndata")
        import numpy as np

        obs = df[[c for c in df.columns if not str(c).startswith("var_")]].copy()
        var_cols = [c for c in df.columns if str(c).startswith("var_")]
        var = df[var_cols].copy() if var_cols else pd.DataFrame(index=df.index)
        adata = ad.AnnData(X=np.zeros((len(df), 1)), obs=obs.reset_index(drop=True), var=var)
        adata.write_h5ad(path)
    else:
        raise ValueError(f"Unsupported target format {fmt!r}")


def convert(source_path: str, target_path: str,
            source_format: str = "auto", target_format: str = "auto") -> dict[str, Any]:
    """Convert a dataset file from one format to another."""
    src, dst = Path(source_path), Path(target_path)
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")

    s_fmt = source_format if source_format != "auto" else src.suffix.lstrip(".").lower()
    t_fmt = target_format if target_format != "auto" else dst.suffix.lstrip(".").lower()
    alias = {"xlsx": "excel", "xls": "excel", "h5ad": "h5ad-lite"}
    s_fmt, t_fmt = alias.get(s_fmt, s_fmt), alias.get(t_fmt, t_fmt)

    df = _read_any(src, s_fmt)
    _write_any(df, dst, t_fmt)
    return result(
        source=str(src), target=str(dst),
        source_format=s_fmt, target_format=t_fmt,
        n_rows=int(df.shape[0]), n_cols=int(df.shape[1]),
        target_size_bytes=int(dst.stat().st_size),
    )


def list_formats() -> dict[str, Any]:
    """List supported formats and whether optional writers are available."""
    return result(
        formats=list(_FORMATS),
        h5ad_available=has_module("anndata"),
        excel_available=has_module("openpyxl"),
    )


_OPS = {"convert": convert, "list_formats": list_formats}

run = skill_run(_OPS)
register_skill("format_converters", run)
