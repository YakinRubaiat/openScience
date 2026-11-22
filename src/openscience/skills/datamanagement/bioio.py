"""bioio skill: multi-format biological data loading.

Supports csv/tsv/xlsx natively via pandas, .h5ad via optional anndata, and
10x Genomics mtx directories (matrix.mtx + genes + barcodes) via scipy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import optional_import, result, skill_run


def _df_payload(df: pd.DataFrame, fmt: str) -> dict[str, Any]:
    return result(
        type="dataframe",
        format=fmt,
        n_rows=int(df.shape[0]),
        n_cols=int(df.shape[1]),
        columns=[str(c) for c in df.columns],
        data=df.to_dict("records"),
    )


def load(file_path: str, format: str = "auto", **kwargs) -> dict[str, Any]:
    """Load a dataset, auto-detecting format from the file extension/directory.

    - ``.csv`` / ``.tsv`` / ``.xlsx`` -> pandas DataFrame payload
    - ``.h5ad`` -> AnnData summary (requires anndata)
    - directory or ``.mtx`` path -> 10x Genomics matrix (see :func:`mtx_10x`)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    fmt = format
    if fmt == "auto":
        if path.is_dir() or path.suffix == ".mtx" or path.name.endswith(".mtx.gz"):
            fmt = "mtx"
        else:
            fmt = path.suffix.lstrip(".").lower()

    if fmt == "csv":
        return _df_payload(pd.read_csv(path, **kwargs), "csv")
    if fmt == "tsv":
        return _df_payload(pd.read_csv(path, sep="\t", **kwargs), "tsv")
    if fmt in ("xlsx", "xls", "excel"):
        return _df_payload(pd.read_excel(path, **kwargs), "excel")
    if fmt == "h5ad":
        ad = optional_import("anndata")
        adata = ad.read_h5ad(path)
        return result(
            type="anndata",
            format="h5ad",
            n_obs=int(adata.n_obs),
            n_vars=int(adata.n_vars),
            obs_columns=list(adata.obs.columns),
            var_columns=list(adata.var.columns),
        )
    if fmt == "mtx":
        return mtx_10x(str(path))
    raise ValueError(f"bioio.load: unsupported format {fmt!r}")


def _read_10x_names(path: Path) -> list[str]:
    df = pd.read_csv(path, sep="\t", header=None, comment="%")
    return df[df.columns[-1]].astype(str).tolist()


def mtx_10x(file_path: str) -> dict[str, Any]:
    """Load a 10x Genomics matrix (matrix.mtx[.gz] + genes/features + barcodes).

    Accepts either the matrix file itself or its parent directory. Returns a
    genes x cells count matrix as dense records-of-dicts may be huge, so the
    payload carries the matrix shape and per-column (cell) totals instead.
    """
    scipy_io = optional_import("scipy.io", "scipy")

    path = Path(file_path)
    if path.is_dir():
        base = path
        mtx = None
        for cand in ("matrix.mtx.gz", "matrix.mtx"):
            if (base / cand).exists():
                mtx = base / cand
                break
        if mtx is None:
            raise FileNotFoundError(f"No matrix.mtx[.gz] found in {base}")
    else:
        mtx, base = path, path.parent
    if not mtx.exists():
        raise FileNotFoundError(f"Matrix file not found: {mtx}")

    mat = scipy_io.mmread(mtx)
    if not isinstance(mat, np.ndarray):
        mat = mat.toarray()
    # 10x matrices are genes x cells.
    mat = np.asarray(mat)

    genes_file, barcodes_file = None, None
    for cand in ("genes.tsv.gz", "genes.tsv", "features.tsv.gz", "features.tsv"):
        if (base / cand).exists():
            genes_file = base / cand
            break
    for cand in ("barcodes.tsv.gz", "barcodes.tsv"):
        if (base / cand).exists():
            barcodes_file = base / cand
            break

    n_rows, n_cols = mat.shape
    genes = _read_10x_names(genes_file) if genes_file else [f"gene_{i}" for i in range(n_rows)]
    barcodes = (
        _read_10x_names(barcodes_file) if barcodes_file else [f"cell_{i}" for i in range(n_cols)]
    )
    if len(genes) != n_rows or len(barcodes) != n_cols:
        raise ValueError(
            f"Dimension mismatch: matrix {mat.shape}, {len(genes)} genes, {len(barcodes)} barcodes"
        )

    return result(
        type="matrix",
        format="mtx_10x",
        n_genes=int(n_rows),
        n_cells=int(n_cols),
        genes=genes[:1000],
        barcodes=barcodes[:1000],
        total_counts=float(mat.sum()),
        counts_per_cell=np.asarray(mat.sum(axis=0)).ravel().tolist(),
        counts_per_gene=np.asarray(mat.sum(axis=1)).ravel().tolist(),
        matrix=mat.tolist(),
    )


def summary(file_path: str, format: str = "auto") -> dict[str, Any]:
    """Load ``file_path`` and return descriptive stats without raw records."""
    payload = load(file_path, format=format)
    if payload.get("type") == "dataframe":
        df = pd.DataFrame(payload["data"])
        numeric = df.select_dtypes(include="number")
        return result(
            type="dataframe",
            n_rows=payload["n_rows"],
            n_cols=payload["n_cols"],
            columns=payload["columns"],
            dtypes={str(c): str(t) for c, t in df.dtypes.items()},
            numeric_summary={
                str(c): {"mean": float(numeric[c].mean()), "std": float(numeric[c].std()),
                         "min": float(numeric[c].min()), "max": float(numeric[c].max())}
                for c in numeric.columns
            },
        )
    # matrix / anndata payloads are already summaries
    return payload


_OPS = {"load": load, "mtx_10x": mtx_10x, "summary": summary}

run = skill_run(_OPS)
register_skill("bioio", run)
