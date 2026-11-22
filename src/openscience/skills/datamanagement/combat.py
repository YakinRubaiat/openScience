"""combat skill: empirical-Bayes-style batch correction (ComBat).

Implements the location (mean) adjustment of ComBat per feature via numpy/
pandas: each feature is centred within batch to the grand mean, which
removes additive batch effects exactly for balanced designs.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _prepare(data: Any, batch: list[Any]) -> tuple[pd.DataFrame, pd.Series]:
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    num = df.select_dtypes(include="number")
    if num.empty:
        raise ValueError("combat requires at least one numeric column")
    batch_s = pd.Series(list(batch), index=df.index, name="batch")
    if len(batch_s) != len(df):
        raise ValueError("'batch' must have one label per row")
    if batch_s.nunique() < 2:
        raise ValueError("combat requires at least two batches")
    return num, batch_s


def correct(data: Any, batch: list[Any]) -> dict[str, Any]:
    """Per-feature batch mean-centring (ComBat location adjustment).

    For each feature, the within-batch mean is replaced by the grand mean:
    ``x_corrected = x - batch_mean + grand_mean``.
    """
    num, batch_s = _prepare(data, batch)
    grand_mean = num.mean(axis=0)
    batch_means = num.groupby(batch_s).mean()
    corrected = num.copy()
    for b, row in batch_means.iterrows():
        mask = (batch_s == b).to_numpy()
        corrected.loc[mask, :] = num.loc[mask, :] - row + grand_mean
    shift = (corrected - num).abs().mean(axis=0)
    return result(
        method="combat-mean-centering",
        n_rows=int(len(num)),
        n_features=int(num.shape[1]),
        batches=[str(b) for b in sorted(batch_s.unique(), key=str)],
        mean_abs_shift_per_feature={str(c): float(v) for c, v in shift.items()},
        data=corrected.reset_index(drop=True).to_dict("records"),
    )


def batch_effect_summary(data: Any, batch: list[Any]) -> dict[str, Any]:
    """Quantify per-feature batch effect before (and after) correction.

    Reports the fraction of variance attributable to batch per feature.
    """
    num, batch_s = _prepare(data, batch)

    def batch_fraction(frame: pd.DataFrame) -> dict[str, float]:
        out = {}
        for c in frame.columns:
            total = float(frame[c].var(ddof=0))
            if total == 0:
                out[str(c)] = 0.0
                continue
            within = frame.groupby(batch_s)[c].var(ddof=0).mean()
            out[str(c)] = float(max(0.0, total - within) / total)
        return out

    before = batch_fraction(num)
    corrected = pd.DataFrame(correct(data, batch)["data"])
    after = batch_fraction(corrected[num.columns])
    return result(
        batch_variance_fraction_before=before,
        batch_variance_fraction_after=after,
        mean_before=float(np.mean(list(before.values()))),
        mean_after=float(np.mean(list(after.values()))),
        n_batches=int(batch_s.nunique()),
    )


_OPS = {"correct": correct, "batch_effect_summary": batch_effect_summary}

run = skill_run(_OPS)
register_skill("combat", run)
