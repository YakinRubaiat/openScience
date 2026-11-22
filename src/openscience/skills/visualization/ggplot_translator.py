"""ggplot-syntax translator skill (``ggplot_syntax``).

Parses simple R-style ggplot2 strings such as
``ggplot(df) + geom_point(aes(x, y)) + geom_line()`` into equivalent
matplotlib code and optionally executes it to a file. Deliberately a
*small* subset — points, lines, bars and histograms with ``aes(x, y)``.
"""

from __future__ import annotations

import os
import re
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run

_GEOM_METHOD = {
    "geom_point": "scatter",
    "geom_line": "plot",
    "geom_bar": "bar",
    "geom_col": "bar",
    "geom_histogram": "hist",
    "geom_boxplot": "boxplot",
}


def _parse_aes(aes: str) -> dict[str, str]:
    out: dict[str, str] = {}
    body = aes.strip()
    m = re.match(r"^aes\((.*)\)$", body)
    if m:
        body = m.group(1)
    for i, part in enumerate(p for p in body.split(",") if p.strip()):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
        elif i == 0:
            out["x"] = part.strip()
        elif i == 1:
            out["y"] = part.strip()
    return out


def translate(**kwargs) -> dict:
    """Translate a ggplot string to matplotlib source; optionally execute.

    Parameters:
        code / ggplot : the ggplot string, e.g.
            ``"ggplot(df) + geom_point(aes(x, y))"``.
        data : DataFrame bound as ``df`` when executing.
        output_path : when given, the generated code is executed with an
            Agg backend and the figure is saved to this path.
    Returns the generated matplotlib source (always) plus ``saved_to``.
    """
    code = kwargs.get("code") or kwargs.get("ggplot")
    if not code:
        raise ValueError("translate requires code=\"ggplot(df)+geom_point(...)\"")

    m = re.search(r"ggplot\(\s*(\w+)", code)
    data_var = m.group(1) if m else "df"

    geoms = re.findall(r"(geom_\w+)\s*\(((?:[^()]|\([^()]*\))*)\)", code)
    if not geoms:
        raise ValueError(
            f"No geom_* calls found in {code!r}. "
            f"Supported: {sorted(_GEOM_METHOD)}")

    lines = [
        "import matplotlib",
        "matplotlib.use('Agg')",
        "import matplotlib.pyplot as plt",
        "fig, ax = plt.subplots(figsize=(4, 3))",
    ]
    unsupported: list[str] = []
    for geom, args in geoms:
        method = _GEOM_METHOD.get(geom)
        if method is None:
            unsupported.append(geom)
            continue
        aes = _parse_aes(args) if args.strip() else {}
        x, y = aes.get("x"), aes.get("y")
        color = aes.get("color") or aes.get("colour")
        if method == "hist":
            lines.append(f"ax.hist({data_var}[{x!r}].dropna(), bins=30)")
        elif method == "boxplot":
            cols = f"[{y!r}]" if y else f"list({data_var}.columns)"
            lines.append(
                f"ax.boxplot([{data_var}[c].dropna() for c in {cols}], "
                f"labels={cols})")
        elif method == "bar":
            lines.append(f"ax.bar({data_var}[{x!r}], {data_var}[{y!r}])")
        elif method == "scatter":
            style = "s=8, alpha=0.7, linewidths=0"
            if color:
                lines.append(
                    f"_groups = {data_var}.groupby({color!r})")
                lines.append(
                    f"for _g, _sub in _groups: "
                    f"ax.scatter(_sub[{x!r}], _sub[{y!r}], {style}, label=str(_g))")
                lines.append("ax.legend(fontsize=6, frameon=False)")
            else:
                lines.append(
                    f"ax.scatter({data_var}[{x!r}], {data_var}[{y!r}], {style})")
        else:  # plot
            order = (f"{data_var}[{x!r}].argsort()" if x else "None")
            lines.append(
                f"ax.plot({data_var}[{x!r}][{order}], "
                f"{data_var}[{y!r}][{order}], lw=1.2)")

    if x:
        lines.append(f"ax.set_xlabel({x!r})")
    if y:
        lines.append(f"ax.set_ylabel({y!r})")
    tm = re.search(r"ggtitle\(\s*['\"]([^'\"]+)['\"]\s*\)", code)
    if tm:
        lines.append(f"ax.set_title({tm.group(1)!r})")
    lines.append("fig.tight_layout()")
    src = "\n".join(lines)

    out = result(code=src, n_geoms=len(geoms), unsupported=unsupported)

    output_path = kwargs.get("output_path") or kwargs.get("save_path")
    if output_path:
        namespace: dict[str, Any] = {}
        data = kwargs.get("data")
        if data is None:
            import numpy as np
            import pandas as pd

            rng = np.random.default_rng(0)
            data = pd.DataFrame({"x": rng.normal(size=50),
                                 "y": rng.normal(size=50)})
        namespace[data_var] = data
        exec(compile(src, "<ggplot_translation>", "exec"), namespace)
        fig = namespace.get("fig")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        fig.savefig(output_path)
        import matplotlib.pyplot as plt

        plt.close(fig)
        out["saved_to"] = output_path
    return out


def help(**_) -> dict:
    return result(
        syntax="ggplot(df) + geom_point(aes(x, y)) [+ geom_line()] "
               "[+ ggtitle('title')]",
        supported_geoms=sorted(_GEOM_METHOD),
        example="ggplot(df) + geom_point(aes(x, y, color=group))",
        note="Small subset of ggplot2; unsupported geoms are reported in "
             "'unsupported' and skipped.",
    )


_OPS = {"translate": translate, "help": help}

run = skill_run(_OPS)
register_skill("ggplot_syntax", run)
