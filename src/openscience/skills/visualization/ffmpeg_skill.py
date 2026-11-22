"""Video-encoding skill (``ffmpeg``).

Thin subprocess wrapper around the system ``ffmpeg``/``ffprobe`` binaries.
When the binary is absent operations return a clear ``unavailable`` result
instead of raising.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from openscience.skills import register_skill
from openscience.skills._common import result, skill_run


def _unavailable(binary: str) -> dict:
    return result(
        "unavailable",
        reason=f"'{binary}' not found on PATH. Install ffmpeg "
               f"(e.g. brew install ffmpeg / apt install ffmpeg).",
        binary=binary,
    )


def encode(**kwargs) -> dict:
    """Encode an input (frames glob or video) into an mp4/gif via ffmpeg.

    Parameters: ``input`` (path or glob pattern like ``frames/f_%03d.png``),
    ``output_path``, ``fps`` (default 15), ``crf`` (default 23).
    """
    if not shutil.which("ffmpeg"):
        return _unavailable("ffmpeg")
    input_spec = kwargs.get("input") or kwargs.get("frames")
    output_path = kwargs.get("output_path") or kwargs.get("output")
    if not input_spec or not output_path:
        raise ValueError("encode requires input and output_path")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(int(kwargs.get("fps", 15))),
        "-i", str(input_spec),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", str(int(kwargs.get("crf", 23))),
        output_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return result("error", error=proc.stderr.strip()[-500:],
                      saved_to=None)
    return result(saved_to=output_path, format=os.path.splitext(output_path)[1].lstrip("."))


def frames_to_video(**kwargs) -> dict:
    """Alias of ``encode`` with a sensible frames-glob default."""
    frames_dir = kwargs.get("frames_dir") or kwargs.get("output_dir")
    pattern = kwargs.get("input")
    if pattern is None:
        if not frames_dir:
            raise ValueError("frames_to_video requires frames_dir or input")
        pattern = os.path.join(str(frames_dir), kwargs.get("pattern", "frame_%03d.png"))
    merged = dict(kwargs)
    merged["input"] = pattern
    return encode(**merged)


def probe(**kwargs) -> dict:
    """Return ffprobe JSON metadata for a media file."""
    if not shutil.which("ffprobe"):
        return _unavailable("ffprobe")
    path = kwargs.get("path") or kwargs.get("input")
    if not path:
        raise ValueError("probe requires path")
    proc = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return result("error", error=proc.stderr.strip()[-500:])
    try:
        info: Any = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        info = {"raw": proc.stdout}
    return result(path=str(path), info=info)


_OPS = {"encode": encode, "frames_to_video": frames_to_video, "probe": probe}

run = skill_run(_OPS)
register_skill("ffmpeg", run)
