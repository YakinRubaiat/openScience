"""integrity_checks skill: checksums, row counts and duplicate detection."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _hash_file(path: Path, algo: str, chunk_size: int = 1 << 20) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def checksums(file_path: str, algorithms: list[str] | None = None) -> dict[str, Any]:
    """Compute md5 and sha256 checksums of a file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    algos = algorithms or ["md5", "sha256"]
    for a in algos:
        if a not in hashlib.algorithms_available:
            raise ValueError(f"Unsupported hash algorithm {a!r}")
    return result(
        file=str(path),
        size_bytes=int(path.stat().st_size),
        checksums={a: _hash_file(path, a) for a in algos},
    )


def row_counts(file_path: str, format: str = "auto") -> dict[str, Any]:
    """Count data rows in a csv/tsv/json file (header excluded for csv/tsv)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    fmt = format if format != "auto" else path.suffix.lstrip(".").lower()
    if fmt == "csv":
        n = max(0, sum(1 for _ in path.open()) - 1)
    elif fmt == "tsv":
        n = max(0, sum(1 for _ in path.open()) - 1)
    elif fmt == "json":
        n = int(len(pd.read_json(path)))
    else:
        raise ValueError(f"row_counts: unsupported format {fmt!r}")
    return result(file=str(path), format=fmt, n_rows=n)


def detect_duplicates(data: Any, columns: list[str] | None = None) -> dict[str, Any]:
    """Detect duplicate rows (all columns or a subset)."""
    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    mask = df.duplicated(subset=columns, keep=False)
    dup_groups = (
        df.loc[mask].groupby(columns or list(df.columns), dropna=False).size()
        if mask.any() else pd.Series(dtype=int)
    )
    return result(
        n_rows=int(len(df)),
        n_duplicate_rows=int(mask.sum()),
        n_duplicate_groups=int(len(dup_groups)),
        duplicate_indices=[int(i) for i in df.index[mask]][:1000],
        passed=int(mask.sum()) == 0,
    )


def file_integrity(file_path: str, expected_checksum: str | None = None,
                   algorithm: str = "sha256") -> dict[str, Any]:
    """Verify a file: existence, readability, non-zero size, checksum match."""
    path = Path(file_path)
    issues: list[str] = []
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    size = path.stat().st_size
    if size == 0:
        issues.append("file is empty")
    try:
        digest = _hash_file(path, algorithm)
    except OSError as exc:
        issues.append(f"unreadable: {exc}")
        digest = None
    checksum_ok = None
    if expected_checksum is not None and digest is not None:
        checksum_ok = digest == expected_checksum
        if not checksum_ok:
            issues.append("checksum mismatch")
    return result(
        file=str(path),
        size_bytes=int(size),
        algorithm=algorithm,
        checksum=digest,
        checksum_matches=checksum_ok,
        issues=issues,
        passed=not issues,
    )


_OPS = {
    "checksums": checksums,
    "row_counts": row_counts,
    "detect_duplicates": detect_duplicates,
    "file_integrity": file_integrity,
}

run = skill_run(_OPS)
register_skill("integrity_checks", run)
