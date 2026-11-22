"""FlowCore-style FCS file skill.

- ``load_fcs``      — load an FCS file via the optional ``flowio`` (or
  ``fcsparser``) package; clear error when neither is installed
- ``get_events``    — return event statistics / a sample of events
- ``channel_names`` — list channel names from the file's metadata
"""

from __future__ import annotations

from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, unwrap


def _load(path, context=None):
    if context is not None and isinstance(context, dict) and "fcs" in context:
        return context["fcs"]
    if has_module("flowio"):
        flowio = optional_import("flowio")
        f = flowio.FlowData(str(path))
        events = np.asarray(f.events, dtype=float).reshape(f.channel_count, -1).T
        channels = [f.channels[str(i + 1)].get("PnN", f"ch{i + 1}") for i in range(f.channel_count)]
        return {"events": events, "channels": channels, "n_events": int(events.shape[0])}
    if has_module("fcsparser"):
        fcsparser = optional_import("fcsparser")
        _meta, df = fcsparser.parse(str(path))
        return {"events": df.to_numpy(dtype=float), "channels": [str(c) for c in df.columns], "n_events": int(df.shape[0])}
    raise RuntimeError(
        "Reading FCS files requires the 'flowio' or 'fcsparser' package. "
        "Install one with: pip install flowio  (or: pip install fcsparser)"
    )


def load_fcs(fcs_path=None, context=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = fcs_path or kw.get("fcs_path") or kw.get("path")
    if p is None:
        raise ValueError("load_fcs requires 'fcs_path'")
    data = _load(p, kw.get("context", context))
    if isinstance(kw.get("context", context), dict):
        kw.get("context", context).setdefault("fcs", data)
    return {
        "path": str(p),
        "n_events": data["n_events"],
        "n_channels": len(data["channels"]),
        "channels": data["channels"],
    }


def get_events(fcs_path=None, max_events=None, context=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = fcs_path or kw.get("fcs_path") or kw.get("path")
    data = _load(p, kw.get("context", context)) if p or not (isinstance(kw.get("context", context), dict) and "fcs" in kw.get("context", context)) else kw.get("context", context)["fcs"]
    events = data["events"]
    max_events = int(kw.get("max_events", max_events or 5))
    means = events.mean(axis=0) if events.size else np.zeros(len(data["channels"]))
    return {
        "n_events": int(events.shape[0]),
        "channels": data["channels"],
        "channel_means": {c: float(m) for c, m in zip(data["channels"], means)},
        "events_preview": [
            {c: float(v) for c, v in zip(data["channels"], row)}
            for row in events[:max_events]
        ],
    }


def channel_names(fcs_path=None, context=None, **kwargs: Any):
    kw = unwrap(kwargs)
    p = fcs_path or kw.get("fcs_path") or kw.get("path")
    ctx = kw.get("context", context)
    if p is None and isinstance(ctx, dict) and "fcs" in ctx:
        data = ctx["fcs"]
    else:
        if p is None:
            raise ValueError("channel_names requires 'fcs_path' (or a loaded FCS in context)")
        data = _load(p, ctx)
    return {"channels": data["channels"], "n_channels": len(data["channels"])}


def run(operation: str, **kwargs: Any):
    ops = {"load_fcs": load_fcs, "get_events": get_events, "channel_names": channel_names}
    fn = ops.get(operation)
    if fn is None:
        raise ValueError(f"flowcore: unknown operation {operation!r}. Available: {sorted(ops)}")
    return fn(**kwargs)


register_skill("flowcore", run)
