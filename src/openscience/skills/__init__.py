"""Skill registry for openScience.

Skills are deterministic, callable tool implementations that agents invoke
through the orchestrator's ``execute_skill`` entry point. A skill is any
callable with the signature ``skill(operation: str, **kwargs)``.

This module provides a simple in-process registry so that real skill
implementations (template engines, HTTP API clients, etc.) can be bound
without requiring an LLM API key.
"""

from typing import Any, Callable

SkillFn = Callable[..., Any]

_REGISTRY: dict[str, SkillFn] = {}


def register_skill(name: str, fn: SkillFn) -> None:
    """Register a skill implementation under ``name``."""
    _REGISTRY[name] = fn


def get_skill(name: str) -> SkillFn | None:
    """Return the skill callable registered under ``name``, if any."""
    return _REGISTRY.get(name)


def list_skills() -> list[str]:
    """Return sorted names of all registered skills."""
    return sorted(_REGISTRY)


def execute_skill(name: str, operation: str, **kwargs) -> Any:
    """Execute a registered skill. Raises ``KeyError`` if unknown."""
    fn = _REGISTRY.get(name)
    if fn is None:
        raise KeyError(f"No skill registered under name {name!r}")
    return fn(operation=operation, **kwargs)


def load_default_skills() -> None:
    """Import every built-in skill module so they self-register.

    Auto-discovers ``*.py`` modules under each skill category package and
    imports them. Modules that fail to import (e.g. missing optional
    third-party dependency) are skipped silently — the pattern each module
    follows is to register a graceful-fallback skill even when the heavy
    dependency is absent.
    """
    import importlib
    import pkgutil

    from openscience import skills as _pkg

    for _importer, category_name, is_pkg in pkgutil.iter_modules(_pkg.__path__):
        if not is_pkg or category_name.startswith("_"):
            continue
        category = importlib.import_module(f"openscience.skills.{category_name}")
        for _imp, mod_name, _is_pkg in pkgutil.iter_modules(category.__path__):
            if mod_name.startswith("_"):
                continue
            full = f"openscience.skills.{category_name}.{mod_name}"
            try:
                module = importlib.import_module(full)
            except Exception:  # noqa: BLE001 - optional deps may be absent
                continue
            # Modules exposing a bare ``run`` dispatcher but that never call
            # register_skill get bound under their module's short name.
            short = mod_name
            if short.endswith("_skill"):
                short = short[: -len("_skill")]
            if short not in _REGISTRY and callable(getattr(module, "run", None)):
                _REGISTRY[short] = module.run
