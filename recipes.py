"""Curated sample pipelines — the "example programs" a workbench ships with.

Each recipe is a named, ready-to-run operator chain (in fullseye/Python form) that
can be selected and loaded in the Studio or called programmatically:

    import fullseye
    fullseye.run_pipeline(frame, fullseye.recipe("Edge — Sobel + Otsu")["stages"])

`stages` is a list of `(op, a, b)` tuples. A recipe may also name the bundled sample
image it was tuned on (`"image"`, a `sample_images` name — the FA inspection set does);
`fullseye.recipe(name)["image"]` then `sample_images.load(...)` shows it on that scene.
All ops are verified to exist and the chains are sort-coherent (checked by `validate()`
and the test suite).
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
    # --- factory inspection (FA) -------------------------------------------------- #
    # Each one is tuned on, and pinned by tests/test_fa_samples.py against, a bundled
    # physics-made sample image ("image") whose defect mask is known pixel for pixel
    # (studio_assets/sample_images/<image>.truth.png, written by tools/gen_fa_samples.py).
    {"name": "FA — scratch on hairline metal", "task": "inspect",
     "image": "metal_hairline_scratch",
     "stages": [("gaussian", 0.1, 0.5), ("sk_rolling_ball", 0.2, 0.5), ("threshold", 0.12, 0.5),
                ("select_shape", 0.0, 0.5)],
     "note": "dark-field ring light makes the torn scratch floor bright; a rolling ball "
             "(radius 9) removes the hairline glints' slow background, a fixed threshold "
             "keeps what is 0.12 above it, specks under 16 px are dropped"},
    {"name": "FA — dent and foreign fibre on resin", "task": "inspect",
     "image": "resin_dent_fibre",
     "stages": [("gaussian", 1.0, 0.5), ("hx_plane_deviation", 0.5, 0.5), ("threshold", 0.05, 0.5),
                ("select_shape", 0.2, 0.5)],
     "note": "smooth away the mould texture, subtract the best-fit plane (the bar light's "
             "fall-off) and keep |deviation| > 0.05 in blobs of 56 px or more; a dent shows as "
             "its shading pair (dark and bright half), a dark fibre as one line"},
    {"name": "FA — engraved lot code (binarize for OCR)", "task": "inspect",
     "image": "engraved_lot_code",
     "stages": [("gaussian", 0.4, 0.5), ("otsu", 0.5, 0.5), ("select_shape", 0.2, 0.5)],
     "note": "dark-field ring: the laser-melted engraving is bright on blasted aluminium; "
             "smooth the blast glints, Otsu, drop specks -> one region per glyph"},
    {"name": "FA — count holes in a back-lit plate", "task": "measure",
     "image": "machined_plate_holes",
     "stages": [("otsu", 0.5, 0.5), ("sk_clear_border", 0.5, 0.5), ("count_obj", 0.5, 0.5)],
     "note": "back light: light passes through the holes and around the part; Otsu keeps the "
             "light, clearing what touches the border leaves only the through-holes, then count"},
    {"name": "FA — weld porosity (X-ray)", "task": "inspect",
     "image": "weld_xray_porosity",
     "stages": [("gaussian", 0.4, 0.5), ("local_threshold", 1.0, 0.66), ("select_shape", 0.0, 0.5)],
     "note": "pores are thinner steel, so brighter; keep pixels 0.048 above a sigma-4 local "
             "background (follows the weld cap), drop specks under 16 px"},
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
