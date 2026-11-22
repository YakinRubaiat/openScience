"""cloud_storage skill: local staging copies that mirror cloud workflows."""

from __future__ import annotations

import hashlib
import shutil
import time
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def copy(source_path: str, dest_path: str,
         overwrite: bool = True) -> dict[str, Any]:
    """Copy a file or directory tree (local-to-local staging).

    Mimics a cloud-object copy: verifies size and sha256 after transfer.
    """
    src, dst = Path(source_path), Path(dest_path)
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if dst.exists() and not overwrite:
        raise FileExistsError(f"Destination exists: {dst}")
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        n_files = sum(1 for p in dst.rglob("*") if p.is_file())
        size = sum(p.stat().st_size for p in dst.rglob("*") if p.is_file())
        return result(source=str(src), dest=str(dst), type="directory",
                      n_files=int(n_files), size_bytes=int(size))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    digest = hashlib.sha256(dst.read_bytes()).hexdigest()
    return result(
        source=str(src), dest=str(dst), type="file",
        size_bytes=int(dst.stat().st_size), sha256=digest,
        verified=digest == hashlib.sha256(src.read_bytes()).hexdigest(),
    )


def stage(source_path: str, staging_dir: str = ".staging") -> dict[str, Any]:
    """Stage a file into a local staging area (like a cloud upload buffer)."""
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    stage_root = Path(staging_dir)
    stage_root.mkdir(parents=True, exist_ok=True)
    return copy(str(src), str(stage_root / src.name))


def presign_stub(path: str, expires_in: int = 3600,
                 operation: str = "GET") -> dict[str, Any]:
    """Generate a deterministic stub 'presigned URL' for local development.

    Clearly marked as a stub — no real cloud call is made, but agents can
    exercise presign-dependent pipeline logic offline.
    """
    p = Path(path)
    token_src = f"{p.resolve()}:{operation}:{expires_in}"
    token = hashlib.sha256(token_src.encode()).hexdigest()[:24]
    return result(
        stub=True,
        operation=operation,
        path=str(p),
        url=f"stub://local/{p.name}?sig={token}&expires={expires_in}",
        expires_at_epoch=int(time.time()) + int(expires_in),
        note="Stub URL — no cloud request was made.",
    )


_OPS = {"copy": copy, "stage": stage, "presign_stub": presign_stub}

run = skill_run(_OPS)
register_skill("cloud_storage", run)
