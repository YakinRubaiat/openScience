"""archival_systems skill: tarball archive creation, listing, verification."""

from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def archive(source_dir: str, output_path: str | None = None) -> dict[str, Any]:
    """Create a ``.tar.gz`` archive of a directory tree."""
    src = Path(source_dir)
    if not src.exists() or not src.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src}")
    out = Path(output_path) if output_path else src.with_suffix(".tar.gz")
    out.parent.mkdir(parents=True, exist_ok=True)
    n_members = 0
    with tarfile.open(out, "w:gz", compresslevel=9) as tar:
        tar.add(src, arcname=src.name)
        names = tar.getnames()
        n_members = len(names)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    return result(
        source=str(src), archive=str(out),
        n_members=n_members,
        size_bytes=int(out.stat().st_size),
        sha256=digest,
    )


def list_archive(archive_path: str) -> dict[str, Any]:
    """List members of a ``.tar.gz`` archive with sizes."""
    path = Path(archive_path)
    if not path.exists():
        raise FileNotFoundError(f"Archive not found: {path}")
    if not tarfile.is_tarfile(path):
        raise ValueError(f"Not a tar archive: {path}")
    with tarfile.open(path, "r:*") as tar:
        members = [
            {"name": m.name, "size_bytes": int(m.size), "is_file": m.isfile()}
            for m in tar.getmembers()
        ]
    return result(
        archive=str(path),
        n_members=len(members),
        total_uncompressed_bytes=sum(m["size_bytes"] for m in members),
        members=members,
    )


def verify_archive(archive_path: str, source_dir: str | None = None) -> dict[str, Any]:
    """Verify archive integrity: gzip readability and (optionally) contents
    match the source tree file-for-file."""
    path = Path(archive_path)
    if not path.exists():
        raise FileNotFoundError(f"Archive not found: {path}")
    issues: list[str] = []
    try:
        with tarfile.open(path, "r:*") as tar:
            members = {m.name: m for m in tar.getmembers() if m.isfile()}
            # Force a full decompression read to catch corruption.
            for m in tar.getmembers():
                if m.isfile():
                    f = tar.extractfile(m)
                    if f is not None:
                        while f.read(1 << 20):
                            pass
    except (tarfile.TarError, OSError, EOFError) as exc:
        issues.append(f"corrupt archive: {exc}")
        return result(archive=str(path), passed=False, issues=issues)

    files_checked = len(members)
    if source_dir is not None:
        src = Path(source_dir)
        if src.exists():
            expected = {str(p.relative_to(src.parent)) for p in src.rglob("*") if p.is_file()}
            missing = expected - set(members)
            extra = set(members) - expected
            if missing:
                issues.append(f"missing files: {sorted(missing)[:10]}")
            if extra:
                issues.append(f"unexpected files: {sorted(extra)[:10]}")
        else:
            issues.append(f"source_dir not found: {src}")
    return result(
        archive=str(path),
        n_files=int(files_checked),
        files_checked=files_checked,
        issues=issues,
        passed=not issues,
    )


_OPS = {"archive": archive, "list_archive": list_archive, "verify_archive": verify_archive}

run = skill_run(_OPS)
register_skill("archival_systems", run)
