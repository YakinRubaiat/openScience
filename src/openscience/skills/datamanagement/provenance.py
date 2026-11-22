"""provenance_modeling skill: W3C PROV-style provenance graphs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

# In-memory PROV store.
_ENTITIES: dict[str, dict[str, Any]] = {}
_ACTIVITIES: dict[str, dict[str, Any]] = {}
_EDGES: list[dict[str, str]] = []


def w3c_prov_graph(entity: str | None = None,
                   activity: str | None = None,
                   used: list[str] | None = None,
                   agent: str | None = None,
                   attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    """Add a PROV step: an ``activity`` that ``used`` entities and generated
    ``entity``. Nodes are prefixed ``prov:Entity``/``prov:Activity`` style.

    With all arguments omitted, returns the current graph without mutating.
    """
    if entity is None and activity is None:
        return _graph_payload()

    if not activity:
        raise ValueError("w3c_prov_graph requires 'activity' when recording")
    act_id = activity
    _ACTIVITIES[act_id] = {
        "id": act_id, "type": "prov:Activity",
        "startedAtTime": time.time(),
        "agent": agent,
    }
    for src in used or []:
        _ENTITIES.setdefault(src, {"id": src, "type": "prov:Entity",
                                   "attributes": {"role": "source"}})
        _EDGES.append({"from": act_id, "to": src, "relation": "prov:used"})
    if entity:
        _ENTITIES[entity] = {
            "id": entity, "type": "prov:Entity",
            "attributes": dict(attributes or {}),
        }
        _EDGES.append({"from": entity, "to": act_id,
                       "relation": "prov:wasGeneratedBy"})
    return _graph_payload()


def _graph_payload() -> dict[str, Any]:
    nodes = [dict(v) for v in _ENTITIES.values()] + [
        dict(v) for v in _ACTIVITIES.values()
    ]
    return result(
        n_nodes=len(nodes), n_edges=len(_EDGES),
        nodes=nodes, edges=[dict(e) for e in _EDGES],
    )


def export(output_path: str) -> dict[str, Any]:
    """Export the provenance graph as W3C-PROV-flavoured JSON."""
    graph = _graph_payload()
    doc = {
        "prefix": {"prov": "http://www.w3.org/ns/prov#"},
        "entity": {e["id"]: e.get("attributes", {}) for e in graph["nodes"]
                   if e["type"] == "prov:Entity"},
        "activity": {a["id"]: {} for a in graph["nodes"]
                     if a["type"] == "prov:Activity"},
        "used": [
            {"prov:activity": e["from"], "prov:entity": e["to"]}
            for e in graph["edges"] if e["relation"] == "prov:used"
        ],
        "wasGeneratedBy": [
            {"prov:entity": e["from"], "prov:activity": e["to"]}
            for e in graph["edges"] if e["relation"] == "prov:wasGeneratedBy"
        ],
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2))
    return result(output_path=str(path),
                  n_entities=len(doc["entity"]),
                  n_activities=len(doc["activity"]),
                  size_bytes=int(path.stat().st_size))


def clear() -> dict[str, Any]:
    """Reset the in-memory provenance store."""
    n = len(_ENTITIES) + len(_ACTIVITIES)
    _ENTITIES.clear()
    _ACTIVITIES.clear()
    _EDGES.clear()
    return result(cleared=n)


_OPS = {"w3c_prov_graph": w3c_prov_graph, "export": export, "clear": clear}

run = skill_run(_OPS)
register_skill("provenance_modeling", run)
