"""backup skill: directory snapshots with rotation."""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_SNAPSHOT_RX = re.compile(r"^snapshot-(\d{8}T\d{6}(?:\.\d+)?)$")


def _is_snapshot(name: str) -> bool:
    return _SNAPSHOT_RX.match(name) is not None


def _snapshot_ts(name: str) -> datetime:
    raw = _SNAPSHOT_RX.match(name).group(1)  # type: ignore[union-attr]
    return datetime.strptime(raw.split(".")[0], "%Y%m%dT%H%M%S").replace(
        tzinfo=timezone.utc
    )


def snapshot(source_dir: str, backup_root: str) -> dict[str, Any]:
    """Copy ``source_dir`` into a timestamped ``snapshot-<UTC>`` folder."""
    src = Path(source_dir)
    if not src.exists() or not src.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src}")
    root = Path(backup_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f")
    dest = root / f"snapshot-{stamp}"
    shutil.copytree(src, dest)
    n_files = sum(1 for p in dest.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
    return result(
        source=str(src), backup=str(dest),
        n_files=int(n_files), size_bytes=int(size),
        created_at=stamp,
    )


def list_backups(backup_root: str) -> dict[str, Any]:
    """List snapshot folders under ``backup_root``, newest first."""
    root = Path(backup_root)
    if not root.exists():
        return result(backup_root=str(root), n_backups=0, backups=[])
    entries = [p for p in root.iterdir() if p.is_dir() and _is_snapshot(p.name)]
    entries.sort(key=lambda p: _snapshot_ts(p.name), reverse=True)
    return result(
        backup_root=str(root),
        n_backups=len(entries),
        backups=[
            {
                "path": str(p),
                "created_at": _snapshot_ts(p.name).isoformat(),
                "n_files": sum(1 for q in p.rglob("*") if q.is_file()),
                "size_bytes": sum(q.stat().st_size for q in p.rglob("*") if q.is_file()),
            }
            for p in entries
        ],
    )


def rotate(backup_root: str, keep: int = 3, dry_run: bool = False) -> dict[str, Any]:
    """Delete all but the ``keep`` newest snapshots."""
    if keep < 1:
        raise ValueError("keep must be >= 1")
    listing = list_backups(backup_root)
    stale = listing["backups"][keep:]
    removed: list[str] = []
    for entry in stale:
        removed.append(entry["path"])
        if not dry_run:
            shutil.rmtree(entry["path"])
    return result(
        keep=keep,
        n_removed=0 if dry_run else len(removed),
        dry_run=dry_run,
        removed=removed,
        remaining=[b["path"] for b in listing["backups"][:keep]],
    )


_OPS = {"snapshot": snapshot, "list_backups": list_backups, "rotate": rotate}

run = skill_run(_OPS)
register_skill("backup_strategies", run)
