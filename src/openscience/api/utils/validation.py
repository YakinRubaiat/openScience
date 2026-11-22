"""Validation helpers and constrained types for request schemas."""

import re
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, Field

_SAFE_NAME_RE = re.compile(r"^[\w\-. ]+$")
_AGENT_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


def _validate_safe_path(value: str) -> str:
    """Reject path traversal and absolute-path escape attempts."""
    if not value or "\x00" in value:
        raise ValueError("Invalid path")
    normalized = Path(value)
    # Reject obvious traversal segments.
    if ".." in normalized.parts:
        raise ValueError("Path traversal is not allowed")
    if len(value) > 1024:
        raise ValueError("Path too long")
    return value


def _validate_safe_name(value: str) -> str:
    if not _SAFE_NAME_RE.match(value) or len(value) > 255:
        raise ValueError("Invalid name; only letters, digits, space, '_', '-', '.' allowed")
    return value


def _validate_agent_name(value: str) -> str:
    if not _AGENT_NAME_RE.match(value) or len(value) > 128:
        raise ValueError("Invalid agent name")
    return value


SafeFilePath = Annotated[str, AfterValidator(_validate_safe_path)]
SafeAgentName = Annotated[str, AfterValidator(_validate_agent_name)]
SessionName = Annotated[str, AfterValidator(_validate_safe_name), Field(min_length=1)]
Username = Annotated[str, Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.\-]+$")]
