"""compression skill: gzip/zip compression via the standard library."""

from __future__ import annotations

import gzip
import shutil
import zipfile
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def compress(source_path: str, dest_path: str | None = None,
             algorithm: str = "gzip") -> dict[str, Any]:
    """Compress a file with gzip (``source.csv.gz``) or zip.

    Returns original/compressed sizes and the compression ratio.
    """
    src = Path(source_path)
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")
    if algorithm == "gzip":
        dest = Path(dest_path) if dest_path else src.with_suffix(src.suffix + ".gz")
        with src.open("rb") as f_in, gzip.open(dest, "wb", compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)
    elif algorithm == "zip":
        dest = Path(dest_path) if dest_path else src.with_suffix(".zip")
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.write(src, arcname=src.name)
    else:
        raise ValueError(f"Unsupported algorithm {algorithm!r}; use 'gzip' or 'zip'")
    original = src.stat().st_size
    compressed = dest.stat().st_size
    return result(
        source=str(src), dest=str(dest), algorithm=algorithm,
        original_bytes=int(original), compressed_bytes=int(compressed),
        ratio=float(compressed / original) if original else 0.0,
        space_saved_pct=float((1 - compressed / original) * 100) if original else 0.0,
    )


def decompress(source_path: str, dest_path: str | None = None) -> dict[str, Any]:
    """Decompress a .gz or .zip file back to its original content."""
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as zf:
            names = zf.namelist()
            if not names:
                raise ValueError("Empty zip archive")
            dest = Path(dest_path) if dest_path else src.parent / names[0]
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(names[0]) as f_in, dest.open("wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        algorithm = "zip"
    elif src.suffix == ".gz":
        dest = Path(dest_path) if dest_path else src.with_suffix("")
        with gzip.open(src, "rb") as f_in, dest.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        algorithm = "gzip"
    else:
        raise ValueError(f"Cannot detect compression format of {src}")
    return result(source=str(src), dest=str(dest), algorithm=algorithm,
                  size_bytes=int(dest.stat().st_size))


def ratio_report(paths: list[str]) -> dict[str, Any]:
    """Report each file's size and estimate gzip compressibility.

    Uses a zlib probe so no temp files are written.
    """
    import zlib

    entries = []
    for raw in paths:
        p = Path(raw)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {p}")
        blob = p.read_bytes()
        compressed = zlib.compress(blob, 9)
        entries.append({
            "path": str(p),
            "size_bytes": len(blob),
            "estimated_gzip_bytes": len(compressed),
            "estimated_ratio": float(len(compressed) / len(blob)) if blob else 0.0,
        })
    return result(files=entries, n_files=len(entries))


_OPS = {"compress": compress, "decompress": decompress, "ratio_report": ratio_report}

run = skill_run(_OPS)
register_skill("compression_algorithms", run)
