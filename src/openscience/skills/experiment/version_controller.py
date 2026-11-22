"""Version controller skill: filesystem snapshots with manifests, diffs, and log."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_MANIFEST_NAME = "manifest.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _scan(root: Path) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != _MANIFEST_NAME:
            rel = p.relative_to(root).as_posix()
            files[rel] = {"size": p.stat().st_size, "sha256": _sha256(p)}
    return files


def _versions_root(versions_dir: str) -> Path:
    return Path(versions_dir)


def snapshot(
    source_dir: str = "",
    versions_dir: str = "",
    label: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Copy ``source_dir`` into a timestamped snapshot with a manifest json."""
    src = Path(source_dir)
    if not src.is_dir():
        raise FileNotFoundError(f"source_dir not a directory: {source_dir}")
    vroot = _versions_root(versions_dir)
    vroot.mkdir(parents=True, exist_ok=True)

    timestamp = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    name = f"{timestamp}_{label}" if label else timestamp
    target = vroot / name
    i = 1
    while target.exists():
        target = vroot / f"{name}_{i}"
        i += 1
    shutil.copytree(src, target)

    files = _scan(target)
    manifest_data = {
        "version": target.name,
        "timestamp": _dt.datetime.now().isoformat(),
        "label": label,
        "n_files": len(files),
        "total_bytes": sum(m["size"] for m in files.values()),
        "files": files,
    }
    with (target / _MANIFEST_NAME).open("w", encoding="utf-8") as fh:
        json.dump(manifest_data, fh, indent=2, sort_keys=True)
    return result(
        version=target.name,
        snapshot_path=str(target),
        manifest=manifest_data,
    )


def _load_manifest(versions_dir: str, version: str) -> dict[str, Any]:
    path = _versions_root(versions_dir) / version / _MANIFEST_NAME
    if not path.exists():
        raise FileNotFoundError(f"no snapshot manifest for version {version!r}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def diff_manifests(
    versions_dir: str = "",
    old_version: str = "",
    new_version: str = "",
    old_manifest: dict[str, Any] | None = None,
    new_manifest: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Diff two snapshot manifests (or two manifest dicts): added/removed/changed."""
    if old_manifest is None:
        old_manifest = _load_manifest(versions_dir, old_version)
    if new_manifest is None:
        new_manifest = _load_manifest(versions_dir, new_version)
    old_files = old_manifest.get("files", {})
    new_files = new_manifest.get("files", {})

    added = sorted(f for f in new_files if f not in old_files)
    removed = sorted(f for f in old_files if f not in new_files)
    changed = sorted(
        f for f in old_files if f in new_files and old_files[f] != new_files[f]
    )
    return result(
        added=added,
        removed=removed,
        changed=changed,
        n_added=len(added),
        n_removed=len(removed),
        n_changed=len(changed),
        identical=not (added or removed or changed),
    )


def log(
    versions_dir: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """List all snapshots in a versions directory (oldest first)."""
    vroot = _versions_root(versions_dir)
    entries: list[dict[str, Any]] = []
    if vroot.is_dir():
        for d in sorted(vroot.iterdir()):
            mfile = d / _MANIFEST_NAME
            if d.is_dir() and mfile.exists():
                with mfile.open("r", encoding="utf-8") as fh:
                    m = json.load(fh)
                entries.append(
                    {
                        "version": d.name,
                        "timestamp": m.get("timestamp"),
                        "label": m.get("label"),
                        "n_files": m.get("n_files"),
                        "total_bytes": m.get("total_bytes"),
                    }
                )
    return result(versions_dir=str(vroot), n_versions=len(entries), log=entries)


run = skill_run(
    {
        "snapshot": snapshot,
        "diff_manifests": diff_manifests,
        "log": log,
    }
)

register_skill("version_controller", run)
