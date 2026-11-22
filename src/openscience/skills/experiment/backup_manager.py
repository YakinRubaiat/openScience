"""Backup manager skill: tar.gz create/restore/list/verify using stdlib tarfile."""

from __future__ import annotations

import datetime as _dt
import json
import tarfile
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_META_NAME = "backup_meta.json"


def create(
    source_dir: str = "",
    backup_dir: str = "",
    backup_name: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a gzipped tar backup of ``source_dir`` in ``backup_dir``."""
    src = Path(source_dir)
    if not src.is_dir():
        raise FileNotFoundError(f"source_dir not a directory: {source_dir}")
    bdir = Path(backup_dir)
    if not backup_dir:
        raise ValueError("backup_dir is required")
    bdir.mkdir(parents=True, exist_ok=True)

    timestamp = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    base = f"{backup_name}_{timestamp}" if backup_name else f"backup_{timestamp}"
    out = bdir / f"{base}.tar.gz"
    i = 1
    while out.exists():
        out = bdir / f"{base}_{i}.tar.gz"
        i += 1

    n_files = 0
    total_bytes = 0
    with tarfile.open(out, "w:gz") as tf:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                tf.add(p, arcname=p.relative_to(src.parent).as_posix())
                n_files += 1
                total_bytes += p.stat().st_size
    meta = {
        "backup": out.name,
        "source_dir": str(src),
        "timestamp": _dt.datetime.now().isoformat(),
        "n_files": n_files,
        "total_bytes": total_bytes,
    }
    with (bdir / f"{out.stem}_{_META_NAME}").open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return result(
        backup_path=str(out),
        compressed_bytes=out.stat().st_size,
        **meta,
    )


def list_backups(
    backup_dir: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """List backups (tar.gz files) found in ``backup_dir``."""
    bdir = Path(backup_dir)
    backups = []
    if bdir.is_dir():
        for p in sorted(bdir.glob("*.tar.gz")):
            backups.append(
                {"backup": p.name, "path": str(p), "size_bytes": p.stat().st_size}
            )
    return result(backup_dir=str(bdir), n_backups=len(backups), backups=backups)


def verify(
    backup_path: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Verify a tar.gz backup can be opened and enumerate its contents."""
    p = Path(backup_path)
    if not p.exists():
        raise FileNotFoundError(f"No such backup: {backup_path}")
    names: list[str] = []
    try:
        with tarfile.open(p, "r:gz") as tf:
            for member in tf.getmembers():
                if member.isfile():
                    names.append(member.name)
    except (tarfile.TarError, OSError) as exc:
        return result(status="error", verified=False, error=str(exc))
    return result(verified=True, backup_path=str(p), n_files=len(names), files=names)


def restore(
    backup_path: str = "",
    target_dir: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Restore a tar.gz backup into ``target_dir`` (created if missing)."""
    p = Path(backup_path)
    if not p.exists():
        raise FileNotFoundError(f"No such backup: {backup_path}")
    target = Path(target_dir)
    if not target_dir:
        raise ValueError("target_dir is required")
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(p, "r:gz") as tf:
        # guard against path traversal
        for member in tf.getmembers():
            dest = (target / member.name).resolve()
            if not str(dest).startswith(str(target.resolve())):
                raise ValueError(f"unsafe path in archive: {member.name}")
        tf.extractall(target)
    return result(backup_path=str(p), target_dir=str(target), restored=True)


run = skill_run(
    {
        "create": create,
        "list_backups": list_backups,
        "verify": verify,
        "restore": restore,
    }
)

register_skill("backup_manager", run)
