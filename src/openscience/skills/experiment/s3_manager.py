"""S3 manager skill: local-only simulation of bucket sync, manifest, verification.

No boto3 dependency — "buckets" are plain directories on disk.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan(root: Path) -> dict[str, dict[str, Any]]:
    """Map relative path -> {size, md5} for every file under root."""
    files: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return files
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            files[rel] = {"size": p.stat().st_size, "md5": _md5(p)}
    return files


def local_sync(
    source_dir: str = "",
    bucket_path: str = "",
    delete: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Mirror ``source_dir`` into ``bucket_path`` (local 'S3 bucket' simulation)."""
    src = Path(source_dir)
    dst = Path(bucket_path)
    if not src.is_dir():
        raise FileNotFoundError(f"source_dir not a directory: {source_dir}")
    if not bucket_path:
        raise ValueError("bucket_path is required")
    dst.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    removed: list[str] = []
    src_files = _scan(src)
    dst_files = _scan(dst)

    for rel, meta in src_files.items():
        target = dst / rel
        if rel not in dst_files or dst_files[rel]["md5"] != meta["md5"]:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, target)
            copied.append(rel)
    if delete:
        for rel in dst_files:
            if rel not in src_files:
                (dst / rel).unlink()
                removed.append(rel)
        # prune empty directories left behind
        for d in sorted((d for d in dst.rglob("*") if d.is_dir()), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()
    return result(
        source_dir=str(src),
        bucket_path=str(dst),
        n_synced=len(src_files),
        n_copied=len(copied),
        n_removed=len(removed),
        copied=copied,
        removed=removed,
    )


def manifest(
    directory: str = "",
    bucket_path: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build a manifest of files with sizes and md5 hashes for a directory."""
    directory = directory or bucket_path or ""
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"directory not found: {directory}")
    files = _scan(root)
    return result(
        directory=str(root),
        n_files=len(files),
        total_bytes=sum(m["size"] for m in files.values()),
        files=files,
    )


def verify_sync(
    source_dir: str = "",
    bucket_path: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Verify a bucket directory exactly mirrors a source directory (by md5)."""
    src = _scan(Path(source_dir))
    dst = _scan(Path(bucket_path))
    missing_in_bucket = [r for r in src if r not in dst]
    extra_in_bucket = [r for r in dst if r not in src]
    mismatched = [r for r in src if r in dst and src[r]["md5"] != dst[r]["md5"]]
    ok = not missing_in_bucket and not extra_in_bucket and not mismatched
    return result(
        verified=ok,
        source_dir=str(source_dir),
        bucket_path=str(bucket_path),
        missing_in_bucket=missing_in_bucket,
        extra_in_bucket=extra_in_bucket,
        mismatched=mismatched,
        n_source_files=len(src),
        n_bucket_files=len(dst),
    )


run = skill_run(
    {
        "local_sync": local_sync,
        "manifest": manifest,
        "verify_sync": verify_sync,
    }
)

register_skill("s3_manager", run)
