"""FASTQ processing skill: pure-python read counting and QC statistics.

- ``count_reads`` — number of reads (gzip-aware)
- ``qc_stats``    — per-file QC: read count, mean/median Phred quality,
  GC %, read-length stats, N content
- ``peek``        — first N reads (id, sequence, mean quality)
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any, Iterator

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def _open_fastq(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open("r")


def _iter_reads(path: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (header, sequence, quality) tuples."""
    with _open_fastq(path) as fh:
        while True:
            header = fh.readline()
            if not header:
                break
            seq = fh.readline()
            plus = fh.readline()
            qual = fh.readline()
            if not qual:
                break
            yield header.strip(), seq.strip(), qual.strip()


def _phred(qual: str) -> list[int]:
    return [ord(c) - 33 for c in qual]


def _fastq_path(kwargs: dict, **extra) -> Path:
    p = extra.get("fastq_path") or extra.get("path") or kwargs.get("fastq_path") or kwargs.get("path")
    if p is None:
        raise ValueError("Provide 'fastq_path'")
    path = Path(p)
    if not path.exists():
        raise FileNotFoundError(f"FASTQ file not found: {path}")
    return path


def count_reads(fastq_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    path = _fastq_path(kw, fastq_path=fastq_path)
    n = sum(1 for _ in _iter_reads(path))
    return {"path": str(path), "n_reads": int(n)}


def qc_stats(fastq_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    path = _fastq_path(kw, fastq_path=fastq_path)
    n = 0
    lengths: list[int] = []
    total_q = 0
    total_q_bases = 0
    gc = 0
    n_bases = 0
    total_bases = 0
    min_len = None
    max_len = 0
    qual_scores_all: list[int] = []

    for _h, seq, qual in _iter_reads(path):
        n += 1
        L = len(seq)
        lengths.append(L)
        min_len = L if min_len is None else min(min_len, L)
        max_len = max(max_len, L)
        total_bases += L
        gc += seq.upper().count("G") + seq.upper().count("C")
        n_bases += seq.upper().count("N")
        qs = _phred(qual)
        total_q += sum(qs)
        total_q_bases += len(qs)
        if n <= 2000:  # keep memory bounded for the median estimate
            qual_scores_all.extend(qs)

    if n == 0:
        raise ValueError(f"No reads found in {path}")

    lengths_sorted = sorted(lengths)
    median_len = lengths_sorted[n // 2] if n % 2 else (lengths_sorted[n // 2 - 1] + lengths_sorted[n // 2]) / 2
    sorted_q = sorted(qual_scores_all)
    median_q = (
        sorted_q[len(sorted_q) // 2]
        if len(sorted_q) % 2
        else (sorted_q[len(sorted_q) // 2 - 1] + sorted_q[len(sorted_q) // 2]) / 2
    )
    return {
        "path": str(path),
        "n_reads": int(n),
        "total_bases": int(total_bases),
        "mean_read_length": float(total_bases / n),
        "median_read_length": float(median_len),
        "min_read_length": int(min_len),
        "max_read_length": int(max_len),
        "mean_quality": float(total_q / max(total_q_bases, 1)),
        "median_quality": float(median_q),
        "gc_percent": float(100.0 * gc / max(total_bases, 1)),
        "n_percent": float(100.0 * n_bases / max(total_bases, 1)),
    }


def peek(fastq_path=None, n: int = 4, **kwargs: Any):
    kw = unwrap(kwargs)
    path = _fastq_path(kw, fastq_path=fastq_path)
    n = int(kw.get("n", n))
    reads = []
    for i, (h, seq, qual) in enumerate(_iter_reads(path)):
        if i >= n:
            break
        qs = _phred(qual)
        reads.append(
            {
                "id": h.lstrip("@"),
                "sequence": seq[:80],
                "length": len(seq),
                "mean_quality": float(sum(qs) / max(len(qs), 1)),
            }
        )
    return {"path": str(path), "n_returned": len(reads), "reads": reads}


def run(operation: str, **kwargs: Any):
    ops = {"count_reads": count_reads, "qc_stats": qc_stats, "peek": peek}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"fastq_processing: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("fastq_processing", run)
