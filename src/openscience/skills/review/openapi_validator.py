"""openapi_spec_validator skill: structural OpenAPI checks (pure python).

Validates, for an OpenAPI 3.x / Swagger 2.x document given as YAML/JSON
text or a parsed dict: presence of the ``openapi``/``swagger`` field,
non-empty ``paths``, and that every operation has ``responses``.

Operations: ``validate``, ``errors_list``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import skill_run

_HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def _load(spec: Any = None, path: str | None = None,
          content: str | None = None) -> dict[str, Any]:
    if isinstance(spec, dict):
        return spec
    if content is None:
        if path is None:
            raise ValueError("Provide 'spec' (dict), 'content' (yaml/json), or 'path'")
        content = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    try:
        import yaml

        data = yaml.safe_load(content)
    except ImportError as exc:
        raise RuntimeError("install with: pip install pyyaml  # to parse YAML specs") from exc
    if not isinstance(data, dict):
        raise ValueError("Spec did not parse to a mapping")
    return data


def _errors(doc: dict[str, Any]) -> list[dict[str, str]]:
    errors = []
    version = doc.get("openapi") or doc.get("swagger")
    if not version:
        errors.append({"location": "$", "message": "missing 'openapi' (or 'swagger') version field"})
    info = doc.get("info")
    if not isinstance(info, dict) or not info.get("title"):
        errors.append({"location": "$.info", "message": "missing info.title"})
    paths = doc.get("paths")
    if not isinstance(paths, dict) or not paths:
        errors.append({"location": "$.paths", "message": "'paths' must be a non-empty mapping"})
        return errors
    for route, item in paths.items():
        if not isinstance(item, dict):
            errors.append({"location": f"$.paths.{route}",
                           "message": "path item must be a mapping"})
            continue
        ops = [(m, op) for m, op in item.items()
               if isinstance(m, str) and m.lower() in _HTTP_METHODS]
        if not ops:
            errors.append({"location": f"$.paths.{route}",
                           "message": "path item declares no HTTP operations"})
        for method, op in ops:
            loc = f"$.paths.{route}.{method.lower()}"
            if not isinstance(op, dict):
                errors.append({"location": loc, "message": "operation must be a mapping"})
                continue
            responses = op.get("responses")
            if not isinstance(responses, dict) or not responses:
                errors.append({"location": f"{loc}.responses",
                               "message": "operation must declare at least one response"})
    return errors


def validate(spec: Any = None, path: str | None = None, content: str | None = None,
             **kwargs: Any) -> dict[str, Any]:
    """Validate an OpenAPI document structure."""
    doc = _load(spec, path, content)
    errors = _errors(doc)
    return {"status": "ok", "valid": not errors, "n_errors": len(errors),
            "errors": errors}


def errors_list(spec: Any = None, path: str | None = None, content: str | None = None,
                **kwargs: Any) -> dict[str, Any]:
    """Just the error list for a spec."""
    res = validate(spec, path, content)
    return {"status": "ok", "valid": res["valid"], "errors": res["errors"]}


run = skill_run({"validate": validate, "errors_list": errors_list})
register_skill("openapi_spec_validator", run)
