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


def execute_skill(name: str, operation: str, **kwargs) -> Any:
    """Execute a registered skill. Raises ``KeyError`` if unknown."""
    fn = _REGISTRY.get(name)
    if fn is None:
        raise KeyError(f"No skill registered under name {name!r}")
    return fn(operation=operation, **kwargs)


def load_default_skills() -> None:
    """Import built-in skill modules so they self-register."""
    from openscience.skills.writing import (
        citation,  # noqa: F401
        pubmed,  # noqa: F401
        scientific_writing,  # noqa: F401
    )
