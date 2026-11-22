"""Matplotlib-animation skill (``matplotlib_animation``).

``frames_only`` writes N PNG frames from a frame-generator callback and
always works. ``line_race`` builds a FuncAnimation bar/line race and saves
it as a GIF via pillow when available; otherwise it writes the individual
PNG frames and reports that GIF encoding needs pillow.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

from openscience.skills import register_skill
from openscience.skills._common import has_module, optional_import, result, skill_run


def _write_frame(fig, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=int(plt.rcParams.get("savefig.dpi", 150)))
    plt.close(fig)


def frames_only(**kwargs) -> dict:
    """Write N PNG frames.

    Parameters:
        frame_fn : callable(i, ax) -> None that draws frame ``i``; when
                   omitted a default sine-wave demo frame is drawn.
        n_frames : number of frames (default 10).
        output_dir / output_path : directory for ``frame_000.png`` …
    """
    frame_fn: Callable[[int, Any], None] | None = kwargs.get("frame_fn")
    n = int(kwargs.get("n_frames", 10))
    outdir = kwargs.get("output_dir") or kwargs.get("output_path") or "frames"
    os.makedirs(outdir, exist_ok=True)

    if frame_fn is None:
        def frame_fn(i, ax):
            t = np.linspace(0, 2 * np.pi, 200)
            ax.plot(t, np.sin(t + i * 0.3), color="#0072B2", lw=1.0)
            ax.set_ylim(-1.2, 1.2)

    paths = []
    for i in range(n):
        fig, ax = plt.subplots(figsize=(4, 3))
        frame_fn(i, ax)
        path = os.path.join(outdir, f"frame_{i:03d}.png")
        _write_frame(fig, path)
        paths.append(path)
    return result(n_frames=n, output_dir=outdir, frames=paths)


def line_race(**kwargs) -> dict:
    """Animated line race: each column of ``data`` grows along the x axis.

    Saves a GIF when pillow is installed; otherwise writes PNG frames and
    reports that GIF encoding requires ``pip install pillow``.
    """
    data = kwargs.get("data")
    n_steps = int(kwargs.get("n_steps", kwargs.get("n_frames", 30)))
    output_path = kwargs.get("output_path") or "line_race.gif"

    if data is not None and hasattr(data, "to_numpy"):
        series = np.asarray(data.to_numpy(dtype=float))
        labels = [str(c) for c in data.columns]
    else:
        rng = np.random.default_rng(0)
        series = np.cumsum(rng.normal(size=(n_steps, 3)), axis=0)
        labels = ["a", "b", "c"]

    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]

    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    lines = [ax.plot([], [], lw=1.5, color=colors[i % len(colors)],
                     label=labels[i])[0] for i in range(series.shape[1])]
    ax.set_xlim(0, series.shape[0] - 1)
    ymin, ymax = float(series.min()), float(series.max())
    pad = 0.1 * (ymax - ymin or 1.0)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.legend(loc="upper left", fontsize=7)
    ax.set_title(kwargs.get("title", ""))

    def _update(frame):
        for i, ln in enumerate(lines):
            ln.set_data(np.arange(frame + 1), series[: frame + 1, i])
        return lines

    frames = np.linspace(0, series.shape[0] - 1, min(n_steps, series.shape[0]))
    frames = np.unique(frames.astype(int))
    anim = FuncAnimation(fig, _update, frames=frames, blit=True)

    if has_module("PIL"):
        optional_import("PIL")  # clear error if import actually fails
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        anim.save(output_path, writer="pillow",
                  fps=int(kwargs.get("fps", 10)))
        plt.close(fig)
        return result(saved_to=output_path, format="gif",
                      n_frames=len(frames))

    outdir = os.path.splitext(output_path)[0] + "_frames"
    paths = []
    for i, f in enumerate(frames):
        _update(int(f))
        path = os.path.join(outdir, f"frame_{i:03d}.png")
        os.makedirs(outdir, exist_ok=True)
        fig.savefig(path, dpi=120)
        paths.append(path)
    plt.close(fig)
    return result(
        "unavailable",
        saved_to=None,
        reason="GIF encoding requires the 'pillow' package. "
               "Install it with: pip install pillow",
        frames=paths,
        n_frames=len(paths),
    )


_OPS = {"line_race": line_race, "frames_only": frames_only}

run = skill_run(_OPS)
register_skill("matplotlib_animation", run)
