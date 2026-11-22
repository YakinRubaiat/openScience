"""hadolint skill: Dockerfile linting (pure-python rule engine).

Parses Dockerfile text and flags: running as root (no USER), :latest tags,
apt-get install without cleaning apt lists, ADD used where COPY suffices,
and curl|sh piping.

Operations: ``lint``, ``score``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run


def _instructions(text: str) -> list[tuple[int, str, str]]:
    """(lineno, INSTRUCTION, args) with line continuations joined."""
    out = []
    buf = ""
    start = 0
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not buf and (not line or line.startswith("#")):
            continue
        if not buf:
            start = n
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        buf += line
        parts = buf.split(None, 1)
        out.append((start, parts[0].upper(), parts[1] if len(parts) > 1 else ""))
        buf = ""
    if buf:
        parts = buf.split(None, 1)
        out.append((start, parts[0].upper(), parts[1] if len(parts) > 1 else ""))
    return out


def _fallback_lint(text: str, fname: str) -> list[dict[str, Any]]:
    issues = []

    def add(rule: str, line: int, message: str) -> None:
        issues.append({"file": fname, "line": line, "rule": rule, "message": message})

    instrs = _instructions(text)
    ops = [op for _, op, _ in instrs]
    if "USER" not in ops:
        add("DL3002", 0, "Last USER should not be root — no USER instruction found")
    for line, op, args in instrs:
        if op == "FROM":
            image = args.split()[0] if args.split() else ""
            if "@" not in image and (":" not in image or image.endswith(":latest")):
                add("DL3007", line, f"Using latest is prone to errors if the image will ever update: {image}")
        elif op == "ADD":
            target_sources = args.split()
            if not any(re.match(r"https?://", s) or s.endswith(".tar") or s.endswith(".tar.gz")
                       for s in target_sources):
                add("DL3020", line, "Use COPY instead of ADD for files and folders")
        elif op == "RUN":
            if re.search(r"(curl|wget)\b[^;&|]*\|\s*(bash|sh)\b", args, re.IGNORECASE):
                add("DL4001", line, "Avoid piping curl/wget output directly into a shell")
            if re.search(r"\bapt(-get)?\s+install\b", args):
                if "rm -rf /var/lib/apt/lists" not in args:
                    add("DL3009", line, "Delete the apt-get lists after installing something")
                if "--no-install-recommends" not in args:
                    add("DL3015", line, "Avoid additional packages by specifying --no-install-recommends")
    return issues


def lint(content: str | None = None, path: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Lint Dockerfile text (``content`` or file ``path``)."""
    if content is None:
        if path is None:
            raise ValueError("Provide Dockerfile 'content' or a 'path'")
        content = Path(path).read_text(encoding="utf-8")
        fname = str(path)
    else:
        fname = str(path or "<dockerfile>")
    if shutil.which("hadolint") is not None:
        proc = subprocess.run(["hadolint", "--format", "json", fname],
                              capture_output=True, text=True, timeout=120,
                              input=content if path is None else None)
        import json

        data = json.loads(proc.stdout or "[]")
        issues = [{"file": i.get("file", fname), "line": i.get("line", 0),
                   "rule": i.get("code", ""), "message": i.get("message", "")}
                  for i in data]
        engine = "hadolint"
    else:
        issues = _fallback_lint(content, fname)
        engine = "pure-python"
    return {"status": "ok", "engine": engine, "n_issues": len(issues), "issues": issues}


def score(content: str | None = None, path: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Dockerfile quality score: 100 minus penalties per rule hit."""
    res = lint(content, path)
    weights = {"DL3002": 25, "DL3007": 15, "DL3009": 10, "DL3015": 5,
               "DL3020": 10, "DL4001": 25}
    penalty = sum(weights.get(i["rule"], 10) for i in res["issues"])
    return {"status": "ok", "score": max(0, 100 - penalty),
            "n_issues": res["n_issues"]}


run = skill_run({"lint": lint, "score": score})
register_skill("hadolint", run)
