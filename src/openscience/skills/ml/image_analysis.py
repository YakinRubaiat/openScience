"""Image analysis skill: TIFF loading, Otsu thresholding, object counting,
and intensity summaries.

Operations
----------
- ``load_tiff``         — load a TIFF (tifffile if available, PIL fallback)
- ``threshold_otsu``    — Otsu threshold (scikit-image if available, else a
  pure-numpy implementation)
- ``count_objects``     — connected-component labelling on a binary image
- ``intensity_summary`` — per-region intensity statistics (mean/median/min/max)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from openscience.skills import register_skill
from openscience.skills._common import has_module, skill_run, unwrap


def load_tiff(**kwargs: Any) -> dict[str, Any]:
    """Load a TIFF image as a numpy array.

    Uses ``tifffile`` when installed, falling back to PIL (Pillow).
    """
    kw = unwrap(kwargs)
    path = Path(kw.get("path") or kw.get("image_path") or "")
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    if has_module("tifffile"):
        from openscience.skills._common import optional_import

        tifffile = optional_import("tifffile")
        arr = tifffile.imread(str(path))
    else:
        pil = optional_import("PIL.Image", package="Pillow")
        img = pil.open(str(path))
        arr = np.asarray(img)

    arr = np.asarray(arr)
    return {
        "path": str(path),
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "_array": arr,  # internal: may be consumed by other ops/tests
    }


def _otsu_numpy(image: np.ndarray, nbins: int = 256) -> float:
    """Pure-numpy Otsu threshold (maximises between-class variance)."""
    data = image.astype(float).ravel()
    lo, hi = float(data.min()), float(data.max())
    if hi <= lo:
        return lo
    hist, bin_edges = np.histogram(data, bins=nbins, range=(lo, hi))
    centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    hist = hist.astype(float)
    total = hist.sum()
    if total == 0:
        return lo
    weight_bg = np.cumsum(hist)
    weight_fg = total - weight_bg
    sum_bg = np.cumsum(hist * centers)
    sum_total = sum_bg[-1]
    mean_bg = np.divide(sum_bg, weight_bg, out=np.zeros_like(sum_bg), where=weight_bg > 0)
    mean_fg = np.divide(
        sum_total - sum_bg, weight_fg, out=np.zeros_like(sum_bg), where=weight_fg > 0
    )
    between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
    return float(centers[int(np.argmax(between))])


def threshold_otsu(**kwargs: Any) -> dict[str, Any]:
    """Compute an Otsu threshold and return the binarized mask.

    Accepts either ``array`` (nested list / numpy array) or ``path`` to a TIFF.
    Uses scikit-image when available, otherwise a pure-numpy implementation.
    """
    kw = unwrap(kwargs)
    arr = kw.get("array")
    if arr is None:
        arr = load_tiff(path=kw.get("path"))["_array"]
    arr = np.asarray(arr, dtype=float)

    if has_module("skimage"):
        from openscience.skills._common import optional_import

        filters = optional_import("skimage.filters", package="scikit-image")
        thresh = float(filters.threshold_otsu(arr))
    else:
        thresh = _otsu_numpy(arr)

    mask = arr > thresh
    return {
        "threshold": thresh,
        "foreground_fraction": float(mask.mean()),
        "mask": mask,
    }


def count_objects(**kwargs: Any) -> dict[str, Any]:
    """Count connected components in a binary (or binarizable) image.

    Parameters: ``mask`` (bool array) or ``array`` plus ``threshold``. When no
    ``threshold`` is given for a grayscale ``array``, Otsu is used.
    Connected-component labelling uses ``scipy.ndimage.label``.
    """
    kw = unwrap(kwargs)
    ndimage = optional_ndimage()

    mask = kw.get("mask")
    if mask is None:
        arr = np.asarray(kw["array"], dtype=float)
        thr = kw.get("threshold")
        if thr is None:
            thr = threshold_otsu(array=arr)["threshold"]
        mask = arr > float(thr)
    mask = np.asarray(mask).astype(bool)

    min_size = int(kw.get("min_size", 1))
    labels, n = ndimage.label(mask)
    if min_size > 1:
        sizes = ndimage.sum_labels(np.ones_like(labels), labels, index=np.arange(1, n + 1))
        keep = np.asarray(sizes) >= min_size
        n = int(keep.sum())
    return {"n_objects": int(n), "labels": labels}


def optional_ndimage():
    from openscience.skills._common import optional_import

    return optional_import("scipy.ndimage", package="scipy")


def intensity_summary(**kwargs: Any) -> dict[str, Any]:
    """Per-region intensity statistics from an image + label image.

    Parameters: ``array`` (intensity image) and ``labels`` (label image, e.g.
    from ``count_objects``). Returns mean/median/min/max/area per label id.
    """
    kw = unwrap(kwargs)
    ndimage = optional_ndimage()

    arr = np.asarray(kw["array"], dtype=float)
    labels = np.asarray(kw["labels"])
    ids = [int(i) for i in np.unique(labels) if i != 0]

    regions: dict[str, Any] = {}
    for i in ids:
        vals = arr[labels == i]
        if vals.size == 0:
            continue
        regions[str(i)] = {
            "area": int(vals.size),
            "mean": float(np.mean(vals)),
            "median": float(np.median(vals)),
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
            "sum": float(np.sum(vals)),
        }
    return {"n_regions": len(regions), "regions": regions}


run = skill_run(
    {
        "load_tiff": load_tiff,
        "threshold_otsu": threshold_otsu,
        "count_objects": count_objects,
        "intensity_summary": intensity_summary,
    }
)

register_skill("image_analysis", run)
