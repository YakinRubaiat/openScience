"""Serialization helpers for framework objects."""

from pathlib import Path
from typing import Any


def to_jsonable(value: Any) -> Any:
    """Convert an arbitrary value into a JSON-serializable structure."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    # Fall back to repr for anything else (figures, arrays, dataframes...).
    return repr(value)


def serialize_result(result: Any) -> Any:
    """Serialize a core ``Result`` (or raw value) for JSON responses."""
    from openscience.core.orchestrator import Result

    if isinstance(result, Result):
        return {
            "data": to_jsonable(result.data),
            "metadata": to_jsonable(result.metadata),
            "artifacts": to_jsonable(result.artifacts),
        }
    return to_jsonable(result)
