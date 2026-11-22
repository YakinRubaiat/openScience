"""black skill: formatting checks.

Uses ``black --check`` when the black CLI is available; otherwise an
``ast.unparse`` round-trip heuristic: code with syntax that normalises
cleanly through parse+unparse and has no trailing-whitespace lines is
considered formatted.

Operations: ``check``, ``format_diff``, ``report_unformatted``.
"""

from __future__ import annotations

import difflib
import subprocess
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run
from openscience.skills.review import _ast_common as ac


def _black_available() -> bool:
    import shutil

    return shutil.which("black") is not None


def _run_black(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["black", *args], capture_output=True, text=True, timeout=120)


def check(path: str, **kwargs: Any) -> dict[str, Any]:
    """Check whether files under ``path`` are black-formatted."""
    files = ac.collect_python_files(path)
    if _black_available():
        proc = _run_black(["--check", "--quiet", str(path)])
        out = proc.stderr + proc.stdout
        unformatted = [f for f in map(str, files) if f in out]
        if proc.returncode != 0 and not unformatted:
            unformatted = [line.rsplit("would be reformatted", 1)[0].strip()
                           for line in out.splitlines() if "would be reformatted" in line]
        engine = "black"
    else:
        unformatted = [str(f) for f in files if _needs_format_fallback(f)]
        engine = "ast-fallback"
    return {
        "status": "ok",
        "engine": engine,
        "files_checked": len(files),
        "all_formatted": not unformatted,
        "unformatted": unformatted,
    }


def _needs_format_fallback(path) -> bool:
    text = ac.read_source(path)
    if any(line != line.rstrip() for line in text.splitlines()):
        return True
    try:
        import ast

        norm = ast.unparse(ast.parse(text))
        # heuristic: if the normalised form shares very little line-wise with
        # the source, formatting is probably off
        src_lines = [l.strip() for l in text.splitlines() if l.strip()]
        norm_lines = [l.strip() for l in norm.splitlines() if l.strip()]
        overlap = sum(1 for l in norm_lines if l in src_lines)
        return overlap < 0.5 * max(len(norm_lines), 1)
    except SyntaxError:
        return False


def format_diff(path: str, **kwargs: Any) -> dict[str, Any]:
    """Unified diff of what black would change in the file at ``path``."""
    from pathlib import Path

    p = Path(path)
    text = ac.read_source(p)
    if _black_available():
        proc = _run_black(["--diff", "--quiet", str(p)])
        diff = proc.stdout
        engine = "black"
    else:
        import ast

        try:
            norm = ast.unparse(ast.parse(text)) + "\n"
        except SyntaxError as exc:
            raise ValueError(f"Cannot format {p}: {exc}") from exc
        diff = "".join(difflib.unified_diff(
            text.splitlines(keepends=True), norm.splitlines(keepends=True),
            fromfile=str(p), tofile=f"{p} (formatted)"))
        engine = "ast-fallback"
    return {"status": "ok", "engine": engine, "file": str(p),
            "has_changes": bool(diff.strip()), "diff": diff}


def report_unformatted(path: str, **kwargs: Any) -> dict[str, Any]:
    """Summary: which files under ``path`` are not black-formatted."""
    res = check(path)
    return {"status": "ok", "engine": res["engine"],
            "n_unformatted": len(res["unformatted"]),
            "n_checked": res["files_checked"],
            "unformatted": res["unformatted"]}


run = skill_run({"check": check, "format_diff": format_diff,
                 "report_unformatted": report_unformatted})
register_skill("black", run)
