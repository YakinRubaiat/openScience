"""MaxQuant output skill (pure python).

- ``read_evidence``    — parse an evidence.txt file into a dataframe summary
- ``lfq_summary``      — LFQ intensity statistics per experiment
- ``contaminants_flag``— flag/remove MaxQuant contaminants ("CON__") and
  reverse hits ("REV__")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _read_txt(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", low_memory=False)


def read_evidence(evidence_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = evidence_path or kw.get("evidence_path") or kw.get("path")
    if p is None:
        raise ValueError("read_evidence requires 'evidence_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"evidence.txt not found: {p}")
    df = _read_txt(p)
    out = {
        "path": str(p),
        "n_rows": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
        "columns": [str(c) for c in df.columns][:100],
    }
    if "Experiment" in df.columns:
        out["n_experiments"] = int(df["Experiment"].nunique())
        out["experiments"] = sorted(str(e) for e in df["Experiment"].unique())
    if "Intensity" in df.columns:
        out["median_intensity"] = float(df["Intensity"].median())
    if "PEP" in df.columns:
        out["median_pep"] = float(df["PEP"].median())
    if "Retention time" in df.columns:
        rt = df["Retention time"].astype(float)
        out["retention_time_range"] = [float(rt.min()), float(rt.max())]
    return out


def lfq_summary(evidence_path=None, evidence_df=None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = evidence_df if evidence_df is not None else kw.get("evidence_df")
    if df is None:
        p = evidence_path or kw.get("evidence_path") or kw.get("path")
        if p is None:
            raise ValueError("lfq_summary requires 'evidence_path' or a dataframe")
        p = Path(p)
        if not p.exists():
            raise FileNotFoundError(f"evidence.txt not found: {p}")
        df = _read_txt(p)
    df = pd.DataFrame(df)
    lfq_cols = [c for c in df.columns if str(c).startswith("LFQ intensity")]
    exp_col = "Experiment" if "Experiment" in df.columns else None
    summary: dict[str, Any] = {"n_rows": int(df.shape[0])}
    if lfq_cols:
        medians = {str(c): float(df[c].replace(0, np.nan).median()) for c in lfq_cols}
        summary["lfq_columns"] = lfq_cols
        summary["lfq_medians"] = medians
    elif exp_col is not None and "Intensity" in df.columns:
        per_exp = df.groupby(exp_col)["Intensity"].median()
        summary["experiments"] = {str(k): float(v) for k, v in per_exp.items()}
    else:
        if "Intensity" not in df.columns:
            raise ValueError("No LFQ intensity columns or 'Intensity' column found")
        summary["median_intensity"] = float(df["Intensity"].replace(0, np.nan).median())
    return summary


def contaminants_flag(evidence_path=None, data=None, remove: bool | None = None, **kwargs: Any):
    kw = unwrap(kwargs)
    df = data if data is not None else kw.get("data")
    if df is None:
        p = evidence_path or kw.get("evidence_path") or kw.get("path")
        if p is None:
            raise ValueError("contaminants_flag requires 'evidence_path' or 'data'")
        p = Path(p)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        df = _read_txt(p)
    df = pd.DataFrame(df)
    prot_col = next((c for c in df.columns if str(c).lower().startswith("leading")), None)
    if prot_col is None:
        prot_col = next((c for c in df.columns if "protein" in str(c).lower()), None)
    if prot_col is None:
        raise ValueError("No protein column found (e.g. 'Leading proteins')")
    proteins = df[prot_col].astype(str)
    con_mask = proteins.str.contains("CON__")
    rev_mask = proteins.str.contains("REV__")
    flag_mask = con_mask | rev_mask
    remove = bool(kw.get("remove", remove if remove is not None else False))
    n_kept = int((~flag_mask).sum())
    result = {
        "protein_column": str(prot_col),
        "n_rows": int(df.shape[0]),
        "n_contaminants": int(con_mask.sum()),
        "n_reverse": int(rev_mask.sum()),
        "n_flagged": int(flag_mask.sum()),
        "flagged_proteins": sorted(set(proteins[flag_mask]))[:50],
    }
    if remove:
        cleaned = df.loc[~flag_mask]
        out = kw.get("output_path")
        if out:
            cleaned.to_csv(out, sep="\t", index=False)
        result["removed"] = True
        result["n_rows_clean"] = n_kept
        result["output_path"] = out
    return result


def run(operation: str, **kwargs: Any):
    ops = {
        "read_evidence": read_evidence,
        "lfq_summary": lfq_summary,
        "contaminants_flag": contaminants_flag,
    }
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"maxquant: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("maxquant", run)
