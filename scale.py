"""Large-image (HALCON-XL-style) execution helpers.

Some operators need an *algorithm change* at XL scale (measured in
docs/AUDIT_2026_08_12.md): cv2 warps fail past ~32767 px, FFT ops are O(N^2)
memory, and iterative filters are compute-bound. But **local** operators
(pointwise + separable filters + morphology) give bit-interior-identical results
when run on **haloed tiles** — that is the algorithm change for those: bounded
memory at any image size.

    import scale, ops
    big = ...                                   # e.g. 20000 x 20000 gray [0,1]
    out = scale.process_tiled(ops.RT["gaussian"], big, a=0.6)   # any size, bounded RAM

`scale_class(op)` tells you whether an operator is tile-safe, and if not, why.
"""
from __future__ import annotations

import numpy as np

# --- scale classification --------------------------------------------------- #
# Local (receptive field <= halo): correct under haloed tiling.
_TILE_SAFE_CATS = {"smoothing", "rank", "morphology", "edges", "gray", "texture", "region"}
# Need GLOBAL statistics (histogram / whole-image threshold) -> not tileable as-is.
_GLOBAL_CATS = {"segmentation", "features", "classification", "barcode", "matching"}
_COMPUTE_BOUND = {"bilateral", "sk_tv", "median", "xsp_wiener"}      # slow at XL
_MEMORY_BOUND_CATS = {"frequency"}                                   # FFT: O(N^2) memory
_CV2_LIMITED_HINTS = ("polar", "warp", "logpolar")                   # cv2 SHRT_MAX (~32767)


def scale_class(op) -> dict:
    """Classify an Op (or a name+category) for large-image behaviour.

    Returns {class, tile_safe, reason}. class in
    {tile_safe, global, compute_bound, memory_bound, cv2_limited}.
    """
    name = getattr(op, "name", op if isinstance(op, str) else "")
    cat = getattr(op, "category", "")
    if any(h in name for h in _CV2_LIMITED_HINTS) or "geometry" in cat:
        return {"class": "cv2_limited", "tile_safe": False,
                "reason": "cv2 warp/geometry: coordinate limit ~32767 px; downscale or use skimage"}
    if cat in _MEMORY_BOUND_CATS:
        return {"class": "memory_bound", "tile_safe": False,
                "reason": "FFT-based: O(N^2) complex memory; use overlap-add or downscale"}
    if name in _COMPUTE_BOUND:
        return {"class": "compute_bound", "tile_safe": True,
                "reason": "local but slow; tiling bounds memory, use cv2/GPU for speed"}
    if cat in _GLOBAL_CATS:
        return {"class": "global", "tile_safe": False,
                "reason": "needs global statistics (histogram/threshold); compute stats globally, then apply"}
    if cat in _TILE_SAFE_CATS:
        return {"class": "tile_safe", "tile_safe": True, "reason": "local filter/morphology"}
    return {"class": "global", "tile_safe": False, "reason": "unclassified; treat as non-tileable"}


# --- haloed tiling ---------------------------------------------------------- #
def process_tiled(fn, img, a=0.5, b=0.5, tile=1024, halo=16):
    """Apply a LOCAL image->image op over haloed tiles; bounded memory at any size.

    Each tile is extended by `halo` px on every side, the op runs on the extended
    patch, and only the core is written back — so the result matches whole-image
    processing wherever the op's receptive field <= halo. Use for tile-safe ops
    (gaussian, sobel, morphology, rank). NOT for global ops (otsu/FFT); check
    scale_class first.
    """
    src = np.asarray(img, np.float64)
    H, W = src.shape[:2]
    out = np.empty((H, W), np.float64)
    for y0 in range(0, H, tile):
        for x0 in range(0, W, tile):
            y1, x1 = min(y0 + tile, H), min(x0 + tile, W)
            ey0, ex0 = max(0, y0 - halo), max(0, x0 - halo)
            ey1, ex1 = min(H, y1 + halo), min(W, x1 + halo)
            res = np.asarray(fn(src[ey0:ey1, ex0:ex1], a, b), np.float64)
            out[y0:y1, x0:x1] = res[y0 - ey0:y0 - ey0 + (y1 - y0),
                                    x0 - ex0:x0 - ex0 + (x1 - x0)]
    return out


def tiling_error(fn, img, a=0.5, b=0.5, tile=64, halo=16):
    """Max abs diff between whole-image and tiled results (0 for local ops)."""
    whole = np.asarray(fn(np.asarray(img, np.float64), a, b), np.float64)
    tiled = process_tiled(fn, img, a, b, tile=tile, halo=halo)
    return float(np.max(np.abs(whole - tiled)))
