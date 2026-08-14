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

import os

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
    (gaussian, mean/median, morphology, rank). NOT for global ops (otsu/FFT); check
    scale_class first.

    Caveat: ops that end in a GLOBAL normalization (`_norm`/`signed01`, e.g.
    `sobel_mag`, `laplace`) tile *spatially* correctly, but the [0,1] scale is a
    whole-image reduction — each tile would normalize by its own max. For those,
    tile the raw filter and normalize once at the end.
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


# --- multithreaded + out-of-core tiling (HALCON-XL scale) ------------------- #
def _tile_specs(H, W, tile, halo):
    """Geometry of every haloed tile: (core y0,y1,x0,x1 ; extended ey0,ey1,ex0,ex1)."""
    t, h = int(tile), int(halo)
    specs = []
    for y0 in range(0, H, t):
        for x0 in range(0, W, t):
            y1, x1 = min(y0 + t, H), min(x0 + t, W)
            ey0, ex0 = max(0, y0 - h), max(0, x0 - h)
            ey1, ex1 = min(H, y1 + h), min(W, x1 + h)
            specs.append((y0, y1, x0, x1, ey0, ey1, ex0, ex1))
    return specs


def _run_tile(fn, src, dst, spec, a, b):
    """Process one haloed tile from ``src`` and write its core into ``dst``.

    Threads own disjoint core regions of ``dst`` and only read ``src``, so this is
    safe to run concurrently."""
    y0, y1, x0, x1, ey0, ey1, ex0, ex1 = spec
    patch = np.asarray(src[ey0:ey1, ex0:ex1], np.float64)
    res = np.asarray(fn(patch, a, b), np.float64)
    dst[y0:y1, x0:x1] = res[y0 - ey0:y0 - ey0 + (y1 - y0),
                            x0 - ex0:x0 - ex0 + (x1 - x0)]


def process_tiled_mt(fn, img, a=0.5, b=0.5, tile=1024, halo=16, workers=None):
    """Multithreaded :func:`process_tiled` — identical result, tiles in parallel.

    Each haloed tile is an independent unit writing a disjoint core region, so they
    run on a :class:`ThreadPoolExecutor`. numpy/scipy release the GIL inside their C
    kernels (filters, morphology, FFT), so this gives a real wall-clock speed-up for
    compute-bound tile-safe ops at XL sizes — with a bit-identical result to the
    serial version. ``workers`` defaults to the CPU count. Use for tile-safe ops
    (check :func:`scale_class`); NOT for global ops."""
    src = np.asarray(img, np.float64)
    H, W = src.shape[:2]
    out = np.empty((H, W), np.float64)
    specs = _tile_specs(H, W, tile, halo)
    n = len(specs) if workers is None else int(workers)
    n = max(1, min(n, len(specs), (os.cpu_count() or 1)))
    if n <= 1:
        for s in specs:
            _run_tile(fn, src, out, s, a, b)
    else:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=n) as ex:
            list(ex.map(lambda s: _run_tile(fn, src, out, s, a, b), specs))
    return out


def open_memmap(path, shape=None, dtype=np.float64, mode="r+"):
    """Open (or create) an on-disk ``.npy`` array as a memory-map — the array is
    read/written in pages from disk, never fully resident in RAM.

    ``mode='w+'`` creates a new file (give ``shape`` + ``dtype``); ``'r'``/``'r+'``
    open an existing one (the ``.npy`` header supplies shape/dtype). The storage
    backing :func:`process_tiled_memmap` for images larger than memory."""
    from numpy.lib.format import open_memmap as _om
    if mode == "w+":
        if shape is None:
            raise ValueError("mode 'w+' needs a shape")
        return _om(path, mode="w+", dtype=np.dtype(dtype), shape=tuple(shape))
    return _om(path, mode=mode)


def process_tiled_memmap(fn, src, dst, a=0.5, b=0.5, tile=1024, halo=16, workers=1):
    """Out-of-core :func:`process_tiled`: process an on-disk image tile-by-tile into
    an on-disk output, at bounded RAM for **any** image size.

    ``src``/``dst`` are memmap arrays or paths to ``.npy`` files; only one extended
    tile and its result are ever resident, so a 100k x 100k image processes in a few
    MB of RAM. ``dst`` (path) is created to match ``src``'s 2-D shape. ``workers>1``
    processes tiles concurrently (each reads/writes disjoint disk regions). Result
    matches whole-image processing wherever the op's receptive field <= halo.
    Returns the ``dst`` memmap (flushed)."""
    S = open_memmap(src, mode="r") if isinstance(src, str) else src
    H, W = S.shape[:2]
    if isinstance(dst, str):
        D = open_memmap(dst, shape=(H, W), dtype=np.float64, mode="w+")
    else:
        D = dst
    specs = _tile_specs(H, W, tile, halo)
    if workers and int(workers) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=int(workers)) as ex:
            list(ex.map(lambda s: _run_tile(fn, S, D, s, a, b), specs))
    else:
        for s in specs:
            _run_tile(fn, S, D, s, a, b)
    if hasattr(D, "flush"):
        D.flush()
    return D
