"""FlowJo workspace skill.

- ``parse_workspace``— parse a FlowJo .wsp (XML) workspace: sample names,
  gates per sample
- ``export_csv``    — export events/stats (uses flowcore-loaded data or a
  plain table) to CSV
"""

from __future__ import annotations

import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from openscience.skills import register_skill
from openscience.skills._common import unwrap


def parse_workspace(workspace_path=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = workspace_path or kw.get("workspace_path") or kw.get("path")
    if p is None:
        raise ValueError("parse_workspace requires 'workspace_path'")
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(f"Workspace not found: {p}")
    tree = ET.parse(p)
    root = tree.getroot()

    samples = []
    gates: dict[str, list[str]] = {}
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "Sample":
            name = elem.attrib.get("name", "")
            node = elem.find(".//DataSet") or elem.find(".//SampleNode")
            samples.append(name or node.attrib.get("name", f"sample_{len(samples)}") if node is not None else name)
        elif tag == "Gate":
            gate_name = elem.attrib.get("name", "")
            parent = elem.attrib.get("parent", "") or elem.attrib.get("sample", "")
            gates.setdefault(parent or "__workspace__", []).append(gate_name)

    samples = [s for s in samples if s]
    return {
        "path": str(p),
        "n_samples": len(samples),
        "samples": samples[:200],
        "n_gates": sum(len(v) for v in gates.values()),
        "gates_by_sample": {k: v for k, v in list(gates.items())[:50]},
    }


def export_csv(events=None, output_path=None, channels=None, **kwargs: Any):
    """Export an event table (list of dicts or 2-D array) to CSV."""
    kw = unwrap(kwargs)
    events = events if events is not None else kw.get("events")
    if events is None and isinstance(kw.get("context"), dict) and "fcs" in kw["context"]:
        data = kw["context"]["fcs"]
        events = data["events"]
        channels = channels or data["channels"]
    if events is None:
        raise ValueError("export_csv requires 'events' (or context['fcs'])")
    out = output_path or kw.get("output_path")
    if out is None:
        raise ValueError("export_csv requires 'output_path'")

    channels = channels or kw.get("channels")
    if isinstance(events, pd.DataFrame):
        df = events
    elif isinstance(events, (list, tuple)) and events and isinstance(events[0], dict):
        df = pd.DataFrame(events)
    else:
        arr = np.asarray(events, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        cols = channels or [f"ch{i + 1}" for i in range(arr.shape[1])]
        df = pd.DataFrame(arr, columns=cols)

    max_rows = int(kw.get("max_rows", len(df)))
    df = df.head(max_rows)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, quoting=csv.QUOTE_MINIMAL)
    return {
        "output_path": str(out),
        "n_rows_written": int(df.shape[0]),
        "n_columns": int(df.shape[1]),
        "columns": [str(c) for c in df.columns],
    }


def run(operation: str, **kwargs: Any):
    ops = {"parse_workspace": parse_workspace, "export_csv": export_csv}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"flowjo: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("flowjo", run)
