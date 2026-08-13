"""Curated sample pipelines — the "example programs" a workbench ships with.

Each recipe is a named, ready-to-run operator chain (in fullseye/Python form) that
can be selected and loaded in the Studio or called programmatically:

    import fullseye
    fullseye.run_pipeline(frame, fullseye.recipe("Edge — Sobel + Otsu")["stages"])

`stages` is a list of `(op, a, b)` tuples. All ops are verified to exist and the
chains are sort-coherent (checked by `validate()` and the test suite).
"""
from __future__ import annotations

RECIPES = [
    {"name": "Denoise — bilateral + unsharp", "task": "denoise",
     "stages": [("bilateral", 0.5, 0.5), ("unsharp", 0.3, 0.5)],
     "note": "edge-preserving smooth, then a light sharpen"},
    {"name": "Denoise — total variation", "task": "denoise",
     "stages": [("sk_tv", 0.5, 0.5)], "note": "ROF TV denoising"},
    {"name": "Denoise — median", "task": "denoise",
     "stages": [("median", 0.4, 0.5)], "note": "impulse-noise friendly"},
    {"name": "Edge — Sobel + Otsu", "task": "edge",
     "stages": [("gaussian", 0.4, 0.5), ("sobel_amp", 0.5, 0.5), ("otsu", 0.4, 0.5)],
     "note": "gradient magnitude thresholded to a binary edge map"},
    {"name": "Edge — Canny", "task": "edge",
     "stages": [("gaussian", 0.4, 0.5), ("canny", 0.4, 0.5)],
     "note": "smoothed then Canny edges (image -> region)"},
    {"name": "Segment — blob / coin", "task": "segment",
     "stages": [("gaussian", 0.45, 0.5), ("otsu", 0.4, 0.5), ("fill_up", 0.5, 0.5),
                ("remove_small", 0.3, 0.5)],
     "note": "smooth, threshold, fill holes, drop specks"},
    {"name": "Count — blobs", "task": "measure",
     "stages": [("gaussian", 0.45, 0.5), ("otsu", 0.4, 0.5), ("fill_up", 0.5, 0.5),
                ("count_obj", 0.5, 0.5)],
     "note": "ends in a feature — the object count"},
    {"name": "Binarize — document (adaptive)", "task": "ocr",
     "stages": [("adaptive_gauss_thresh", 0.5, 0.5)],
     "note": "local adaptive threshold for uneven lighting"},
    {"name": "Enhance — CLAHE contrast", "task": "enhance",
     "stages": [("clahe", 0.5, 0.5)], "note": "local histogram equalization"},
    {"name": "Enhance — histogram equalize", "task": "enhance",
     "stages": [("equalize", 0.5, 0.5)], "note": "global equalization"},
    {"name": "Enhance — gamma", "task": "enhance",
     "stages": [("gamma", 0.4, 0.5)], "note": "gamma tone curve"},
    {"name": "Sharpen — unsharp mask", "task": "enhance",
     "stages": [("unsharp", 0.6, 0.5)], "note": "unsharp masking"},
    {"name": "Sharpen — highpass", "task": "enhance",
     "stages": [("highpass", 0.4, 0.5)], "note": "frequency-domain high-pass"},
    {"name": "Texture — Gabor", "task": "texture",
     "stages": [("gabor", 0.3, 0.4)], "note": "oriented band-pass texture response"},
    {"name": "Texture — local std", "task": "texture",
     "stages": [("std_filter", 0.5, 0.5)], "note": "local standard deviation"},
    {"name": "Keypoints — Harris corners", "task": "features",
     "stages": [("sk_corner_harris", 0.5, 0.5)], "note": "corner response map"},
    {"name": "Blobs — Difference of Gaussians", "task": "features",
     "stages": [("sk_dog", 0.3, 0.6)], "note": "DoG blob response"},
    {"name": "Morphology — gradient", "task": "morphology",
     "stages": [("morph_grad", 0.5, 0.5)], "note": "dilation minus erosion"},
    {"name": "Shape — distance transform", "task": "shape",
     "stages": [("gaussian", 0.4, 0.5), ("otsu", 0.4, 0.5), ("distance_transform", 0.5, 0.5)],
     "note": "distance to background inside each region"},
    {"name": "Spots — local maxima", "task": "features",
     "stages": [("gaussian", 0.4, 0.5), ("local_max", 0.5, 0.5)],
     "note": "bright-spot detection"},
]


def names():
    return [r["name"] for r in RECIPES]


def get(name):
    return next((r for r in RECIPES if r["name"] == name), None)


def stages(name):
    r = get(name)
    return [tuple(s) for s in r["stages"]] if r else None


def validate():
    """Return a list of problems (empty if all recipes resolve and are
    sort-coherent). Used by the test suite."""
    import api
    problems = []
    for r in RECIPES:
        sort = "image"
        for (op, a, b) in r["stages"]:
            o = api.find_op(op)
            if o is None:
                problems.append(f"{r['name']}: unknown op {op!r}")
                break
            if o.in_sort not in (sort, "any"):
                problems.append(f"{r['name']}: {op} expects {o.in_sort}, got {sort}")
                break
            sort = o.out_sort
    return problems
