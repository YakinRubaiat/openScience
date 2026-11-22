"""pgbadger skill: PostgreSQL log analysis.

``analyze`` wraps the pgbadger CLI when on PATH (clear RuntimeError
otherwise). ``parse_log_slow_queries`` parses postgres log lines with a
regex into a table of slow queries.

Operations: ``analyze``, ``parse_log_slow_queries``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

_DURATION_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\s*[A-Z]+)?)"
    r".*?duration:\s*(?P<ms>[\d.]+)\s*ms\s+"
    r"(?:statement|execute\s+\S+)\s*:\s*(?P<query>.*)",
    re.IGNORECASE)


def analyze(log_path: str, out_html: str = "pgbadger_report.html",
            extra_args: list | None = None, **kwargs: Any) -> dict[str, Any]:
    """Run pgbadger against a postgres log file."""
    if shutil.which("pgbadger") is None:
        raise RuntimeError("install with: brew install pgbadger  # or from pgbadger sources")
    if not Path(log_path).is_file():
        raise FileNotFoundError(f"Log not found: {log_path}")
    cmd = ["pgbadger", "-o", out_html, *(extra_args or []), log_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return {"status": "ok" if proc.returncode == 0 else "error",
            "returncode": proc.returncode, "report": out_html,
            "stderr_tail": proc.stderr[-500:]}


def parse_log_slow_queries(content: str | None = None, path: str | None = None,
                           min_duration_ms: float = 0.0, **kwargs: Any) -> dict[str, Any]:
    """Extract slow queries (``duration: N ms ... : <query>``) from a log.

    Provide log ``content`` directly or a ``path`` to a log file.
    """
    if content is None:
        if path is None:
            raise ValueError("Provide log 'content' or a 'path'")
        content = Path(path).read_text(encoding="utf-8", errors="replace")
    rows = []
    for m in _DURATION_RE.finditer(content):
        ms = float(m.group("ms"))
        if ms >= min_duration_ms:
            rows.append({"timestamp": m.group("ts"), "duration_ms": ms,
                         "query": m.group("query").strip()})
    rows.sort(key=lambda r: r["duration_ms"], reverse=True)
    return {"status": "ok", "n_queries": len(rows),
            "slowest_ms": rows[0]["duration_ms"] if rows else 0.0,
            "queries": rows}


run = skill_run({"analyze": analyze, "parse_log_slow_queries": parse_log_slow_queries})
register_skill("pgbadger", run)
