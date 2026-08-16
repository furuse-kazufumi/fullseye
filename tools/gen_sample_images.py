#!/usr/bin/env python3
"""Collect a small set of license-clean sample images for Fullseye Studio.

Two provenance-clean sources only (no external download, no scraping):
  * synthetic   — generated here, deterministic (my own work).
  * skimage.data — ships with scikit-image (BSD / public-domain classics:
                   coins, camera, page, cell). Skipped cleanly if unavailable.

Writes 8-bit PNGs to ``studio_assets/sample_images/`` + a ``manifest.json`` that
records each image's source and licence, so the provenance is auditable. Re-runs
are idempotent (same bytes for the synthetic ones).

    py -3.11 tools/gen_sample_images.py
"""
from __future__ import annotations

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "studio_assets", "sample_images")


def _synthetic():
    """Deterministic synthetic scenes (grayscale float [0,1])."""
    out = {}
    yy, xx = np.mgrid[0:256, 0:256] / 255.0

    # a smooth gradient
    out["gradient"] = xx.copy()

    # separated bright blobs on a dark ground (blob counting / segmentation)
    blobs = np.zeros((256, 256), float)
    rng = np.random.default_rng(0)
    for _ in range(9):
        cy, cx = rng.integers(30, 226, 2)
        r = rng.integers(12, 26)
        blobs[(yy * 255 - cy) ** 2 + (xx * 255 - cx) ** 2 <= r * r] = 1.0
    out["blobs"] = blobs

    # a bright ring + disc (edges / region shapes)
    r2 = (yy * 255 - 128) ** 2 + (xx * 255 - 128) ** 2
    ring = ((r2 <= 90 ** 2) & (r2 >= 62 ** 2)).astype(float)
    ring[r2 <= 34 ** 2] = 1.0
    out["shapes"] = ring

    # a checker + gaussian noise (denoise demos)
    checker = (((yy * 255).astype(int) // 32 + (xx * 255).astype(int) // 32) % 2).astype(float)
    noisy = np.clip(checker * 0.7 + 0.15 + rng.normal(0, 0.09, checker.shape), 0, 1)
    out["checker_noisy"] = noisy
    return out


def _skimage():
    """Classic BSD / public-domain images that ship with scikit-image."""
    out = {}
    try:
        from skimage import data
    except Exception:
        return out
    for name, fn in (("coins", "coins"), ("camera", "camera"),
                     ("page", "page"), ("cell", "cell")):
        try:
            arr = np.asarray(getattr(data, fn)(), float)
            if arr.ndim == 3:
                arr = arr.mean(2)
            arr = arr / (arr.max() or 1.0)
            out[name] = arr
        except Exception:
            pass
    return out


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    import imgio  # local: license-clean save

    manifest = {"images": []}
    for name, arr in _synthetic().items():
        p = os.path.join(OUT, name + ".png")
        imgio.save(p, np.asarray(arr, float))
        manifest["images"].append({"name": name, "file": name + ".png",
                                    "source": "synthetic (Fullseye)", "licence": "own work"})
    for name, arr in _skimage().items():
        p = os.path.join(OUT, name + ".png")
        imgio.save(p, np.asarray(arr, float))
        manifest["images"].append({"name": name, "file": name + ".png",
                                    "source": "skimage.data", "licence": "BSD / public domain (see scikit-image)"})

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("[sample_images] wrote %d images -> %s" % (len(manifest["images"]), OUT))
    for it in manifest["images"]:
        print("  %-14s %s" % (it["name"], it["source"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
