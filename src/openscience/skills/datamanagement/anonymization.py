"""anonymization skill: hashing, masking and k-anonymity checks."""

from __future__ import annotations

import hashlib
import re
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RX = re.compile(r"(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b")
_SSN_RX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def _frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    return pd.DataFrame(data)


def hash_columns(data: Any, columns: list[str],
                 algorithm: str = "sha256",
                 salt: str = "") -> dict[str, Any]:
    """Replace column values with salted hashes (deterministic pseudonymisation)."""
    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"Unsupported hash algorithm {algorithm!r}")
    df = _frame(data)
    for col in columns:
        if col not in df.columns:
            raise ValueError(f"Unknown column {col!r}")
        df[col] = df[col].map(
            lambda v: hashlib.new(algorithm, f"{salt}{v}".encode()).hexdigest()
            if pd.notna(v) else v
        )
    return result(hashed_columns=[str(c) for c in columns], algorithm=algorithm,
                  n_rows=int(len(df)), data=df.to_dict("records"))


def _mask_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    out = _EMAIL_RX.sub("x@x.com", value)
    out = _PHONE_RX.sub("XXX-XXX-XXXX", out)
    out = _SSN_RX.sub("XXX-XX-XXXX", out)
    return out


def mask(data: Any, columns: list[str] | None = None,
         replacement: str = "***") -> dict[str, Any]:
    """Mask PII-ish patterns in string cells (emails -> x@x.com, ...)."""
    df = _frame(data)
    cols = columns or [c for c in df.columns if df[c].dtype == object]
    n_masked = 0
    for col in cols:
        if col not in df.columns:
            raise ValueError(f"Unknown column {col!r}")
        masked = df[col].map(_mask_value)
        # generic catch-all: non-patterned columns get full masking
        if columns is not None and masked.equals(df[col]):
            masked = df[col].map(lambda v: replacement if isinstance(v, str) and v else v)
        n_masked += int((masked != df[col]).sum())
        df[col] = masked
    return result(masked_columns=[str(c) for c in cols], n_cells_masked=n_masked,
                  data=df.to_dict("records"))


def k_anonymity_check(data: Any, quasi_identifiers: list[str],
                      k: int = 2) -> dict[str, Any]:
    """Check that every combination of quasi-identifiers occurs >= k times."""
    if k < 1:
        raise ValueError("k must be >= 1")
    df = _frame(data)
    for col in quasi_identifiers:
        if col not in df.columns:
            raise ValueError(f"Unknown column {col!r}")
    sizes = df.groupby(quasi_identifiers, dropna=False).size()
    violations = sizes[sizes < k]
    return result(
        k=k,
        n_groups=int(len(sizes)),
        n_violating_groups=int(len(violations)),
        min_group_size=int(sizes.min()) if len(sizes) else 0,
        violating_groups=[
            {"key": tuple(map(str, idx if isinstance(idx, tuple) else (idx,))),
             "size": int(n)}
            for idx, n in list(violations.items())[:100]
        ],
        passed=int(len(violations)) == 0,
    )


_OPS = {
    "hash_columns": hash_columns,
    "mask": mask,
    "k_anonymity_check": k_anonymity_check,
}

run = skill_run(_OPS)
register_skill("anonymization", run)
