"""Shared helpers for skill implementations.

Every skill follows one of two patterns:

1. A module-level ``run(operation: str, **kwargs)`` dispatcher (older style), or
2. Self-registration via ``register_skill(name, fn)`` at import time (preferred).

Both patterns are executed through ``openscience.skills.execute_skill`` /
``AgentOrchestrator.execute_skill``. This module provides shared utilities:

- ``optional_import``: import a heavy dependency lazily, raising a clear error
- ``unwrap``: agents often nest parameters one level deep
- ``result``: build a consistent result dict
- ``skill_run``: helper to build a ``run`` dispatcher from an operation table
"""

from __future__ import annotations

import importlib
from typing import Any, Callable

# Keys that never belong to a skill operation's signature.
_RESERVED_KEYS = ("operation", "parameters", "context")


def unwrap(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Agents pass parameters={"parameters": {...}}; unwrap one level.

    Returns the inner dict when present, else the kwargs themselves with the
    reserved keys ("operation", "parameters", "context") removed.
    """
    p = kwargs.get("parameters")
    if isinstance(p, dict):
        merged = {k: v for k, v in kwargs.items() if k not in _RESERVED_KEYS}
        merged.update(p)
        return merged
    return {k: v for k, v in kwargs.items() if k not in ("operation", "context")}


def result(status: str = "ok", **payload: Any) -> dict[str, Any]:
    """Build a consistent skill result dict."""
    out = {"status": status}
    out.update(payload)
    return out


def optional_import(module_name: str, package: str | None = None):
    """Import ``module_name``, raising a clear, actionable error if missing.

    Use for heavy scientific dependencies (torch, qiime2, gatk, etc.) so a
    skill degrades with a helpful message instead of an ``ImportError``.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:  # pragma: no cover - thin wrapper
        pip_name = package or module_name.split(".")[0]
        raise RuntimeError(
            f"Skill dependency '{module_name}' is not installed. "
            f"Install it with: pip install {pip_name}"
        ) from exc


def has_module(module_name: str) -> bool:
    """Return True if ``module_name`` can be imported (no side effects)."""
    import importlib.util

    return importlib.util.find_spec(module_name) is not None


def skill_run(operations: dict[str, Callable[..., Any]]) -> Callable[..., Any]:
    """Build a ``run(operation, **kwargs)`` dispatcher from a table.

    Any operation name not in the table raises ``ValueError``. The special
    operation ``"run"`` maps to the first entry in the table, which supports
    agents that call ``skill.run("run", ...)`` generically.
    """

    default_op = next(iter(operations))

    def run(operation: str = "run", **kwargs: Any) -> Any:
        op = operations.get(operation) or operations.get(default_op)
        if operation not in operations and operation != "run":
            raise ValueError(
                f"Unknown operation {operation!r}. "
                f"Available: {sorted(operations)}"
            )
        return op(**unwrap(kwargs))

    return run
