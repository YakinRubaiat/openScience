"""dvc skill: thin wrapper over the ``dvc`` CLI.

Uses a subprocess call to the dvc CLI when available on PATH (preferred,
handles all dvc versions uniformly) and otherwise returns a clear,
actionable error — dvc is an optional heavy dependency.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _dvc_available() -> bool:
    return shutil.which("dvc") is not None


def _require_dvc() -> str:
    exe = shutil.which("dvc")
    if exe is None:
        raise RuntimeError(
            "Skill dependency 'dvc' is not installed. "
            "Install it with: pip install dvc  (or: brew install dvc)"
        )
    return exe


def _run_cli(args: list[str], cwd: str | None = None) -> dict[str, Any]:
    import subprocess

    exe = _require_dvc()
    completed = subprocess.run(
        [exe, *args], cwd=cwd, capture_output=True, text=True, timeout=300
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"dvc {' '.join(args)} failed (exit {completed.returncode}): "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed


def init(repo_path: str = ".", no_scm: bool = False) -> dict[str, Any]:
    """Initialise a DVC repository in ``repo_path``."""
    Path(repo_path).mkdir(parents=True, exist_ok=True)
    args = ["init"] + (["--no-scm"] if no_scm else [])
    _run_cli(args, cwd=repo_path)
    dvc_dir = Path(repo_path) / ".dvc"
    return result(repo_path=str(Path(repo_path).resolve()),
                  dvc_dir_exists=dvc_dir.exists())


def add(repo_path: str, target: str) -> dict[str, Any]:
    """Track ``target`` with dvc; returns the generated .dvc file path."""
    _run_cli(["add", target], cwd=repo_path)
    dvc_file = Path(repo_path) / f"{target}.dvc"
    return result(target=target, dvc_file=str(dvc_file),
                  dvc_file_exists=dvc_file.exists())


def status(repo_path: str = ".") -> dict[str, Any]:
    """Return dvc pipeline status (JSON when supported, raw text otherwise)."""
    try:
        out = _run_cli(["data status", "--json"], cwd=repo_path)
        parsed: Any = json.loads(out.stdout or "{}")
    except (RuntimeError, json.JSONDecodeError):
        out = _run_cli(["status"], cwd=repo_path)
        parsed = out.stdout.strip()
    return result(repo_path=str(Path(repo_path).resolve()), status=parsed)


def pull(repo_path: str = ".", remote: str | None = None) -> dict[str, Any]:
    """Pull data from the configured dvc remote."""
    args = ["pull"] + (["-r", remote] if remote else [])
    out = _run_cli(args, cwd=repo_path)
    return result(repo_path=str(Path(repo_path).resolve()),
                  output=out.stdout.strip())


def available() -> dict[str, Any]:
    """Report whether the dvc CLI is usable (always works, no dvc needed)."""
    return result(available=_dvc_available(), executable=shutil.which("dvc"))


_OPS = {"init": init, "add": add, "status": status, "pull": pull, "available": available}

run = skill_run(_OPS)
register_skill("dvc", run)
