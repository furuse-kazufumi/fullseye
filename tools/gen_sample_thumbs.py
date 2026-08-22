#!/usr/bin/env python3
"""Render a result thumbnail (input -> output, side by side) for every sample recipe.

For each recipe in ``recipes.RECIPES`` this picks a fitting sample image
(``studio_assets/sample_images/``), runs the pipeline headlessly with
``ops.run_stages``, and writes an ~800 px wide before/after PNG to
``studio_assets/sample_thumbs/<slug>.png`` — the naming the Studio's
"Samples & code" gallery resolves via ``studio.sample_thumb_path``.

Feature-valued endpoints (e.g. ``count_obj``) show the last image/region-valued
intermediate with the measured value stamped on the output panel. A thumbnail is
only written when the output is non-degenerate (not flat black/white), and a
``manifest.json`` records input image, output kind and any skips — auditable, like
``gen_sample_images.py``.

    py -3.11 tools/gen_sample_thumbs.py
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)                 # so repo-root imports work from tools/

import imgio          # noqa: E402
import ops            # noqa: E402
import recipes        # noqa: E402
import sample_images  # noqa: E402

OUT = os.path.join(_ROOT, "studio_assets", "sample_thumbs")

#: recipe task -> best-fitting sample image (falls back to "camera").
TASK_IMAGE = {
    "denoise": "checker_noisy",
    "edge": "coins",
    "segment": "coins",
    "measure": "coins",
    "ocr": "page",
    "enhance": "camera",
    "texture": "brick_quilt",
    "features": "blobs",
    "morphology": "coins",
    "shape": "coins",
}

#: per-recipe overrides where the task default is not the most telling scene.
NAME_IMAGE = {
    "Keypoints — Harris corners": "checker_noisy",
    "Spots — local maxima": "cell",
    "Denoise — median": "grain_synth",
}

PANEL_H = 300          # panel height; two panels + gap come out ~800 px wide
GAP = 4                # white separator between the input and output panels


def slug(name):
    """Recipe name -> thumbnail file stem (must match ``studio.sample_thumb_path``)."""
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def _panel(arr):
    """Any 2-D result -> displayable float [0,1] array (colourise if out of range)."""
    a = np.asarray(arr, np.float64)
    if a.ndim == 2 and (a.min() < -1e-9 or a.max() > 1 + 1e-9 or not np.isfinite(a).all()):
        a = imgio.apply_cmap(a)
    return a


def _resize_h(a, h):
    import cv2
    w = max(1, int(round(a.shape[1] * h / a.shape[0])))
    return cv2.resize(a.astype(np.float32), (w, h),
                      interpolation=cv2.INTER_AREA).astype(np.float64)


def render(recipe):
    """Run one recipe headlessly. Returns ``(png_float_array, meta)`` or ``(None, meta)``."""
    name = recipe["name"]
    img_name = NAME_IMAGE.get(name) or TASK_IMAGE.get(recipe.get("task"), "camera")
    if sample_images.path(img_name) is None:
        img_name = "camera"
    img = sample_images.load(img_name)

    # run stage by stage so a feature endpoint still leaves us a picture to show
    val, last_2d, label = img, img, None
    for (op, a, b) in recipe["stages"]:
        val = ops.run_stages([ops.stage(op, a, b)], val)
        if isinstance(val, np.ndarray) and val.ndim == 2:
            last_2d = val
        elif isinstance(val, (int, float, np.floating, np.integer)):
            label = "%s = %.4g" % (op, float(val))
        elif isinstance(val, dict):                      # contour set
            label = "%s: %d contours" % (op, len(val.get("cs", [])))

    out = _panel(last_2d)
    flat = float(np.nanmax(out) - np.nanmin(out)) < 1e-6  # black/blank guard
    meta = {"name": name, "input": img_name, "slug": slug(name),
            "kind": "feature" if label else ("region" if set(np.unique(last_2d)) <= {0.0, 1.0}
                                             else "image"),
            "label": label}
    if flat:
        meta["skip"] = "degenerate output (flat panel)"
        return None, meta

    left = _resize_h(np.dstack([img] * 3), PANEL_H)
    right = out if out.ndim == 3 else np.dstack([out] * 3)
    right = _resize_h(right, PANEL_H)
    if label:                                            # stamp the measured value
        import cv2
        r8 = (np.clip(right, 0, 1) * 255).astype(np.uint8)
        cv2.rectangle(r8, (0, 0), (r8.shape[1], 30), (24, 24, 24), -1)
        cv2.putText(r8, label, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (90, 200, 255), 1, cv2.LINE_AA)
        right = r8 / 255.0
    canvas = np.ones((PANEL_H, left.shape[1] + GAP + right.shape[1], 3)) * 1.0
    canvas[:, :left.shape[1]] = left
    canvas[:, left.shape[1] + GAP:] = right
    return canvas, meta


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest, made, skipped = [], 0, 0
    for r in recipes.RECIPES:
        try:
            canvas, meta = render(r)
        except Exception as e:                            # honest disclosure per recipe
            meta = {"name": r["name"], "slug": slug(r["name"]),
                    "skip": "error: %s" % e}
            canvas = None
        if canvas is not None:
            p = os.path.join(OUT, meta["slug"] + ".png")
            imgio.save(p, canvas)
            meta["file"] = os.path.basename(p)
            made += 1
            print("ok   %-38s -> %s" % (r["name"], meta["file"]))
        else:
            skipped += 1
            print("SKIP %-38s (%s)" % (r["name"], meta.get("skip")))
        manifest.append(meta)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"thumbs": manifest}, f, indent=2, ensure_ascii=False)
    print("done: %d thumbnails, %d skipped -> %s" % (made, skipped, OUT))
    return 0 if made else 1


if __name__ == "__main__":
    sys.exit(main())
