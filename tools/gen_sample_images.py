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
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)                 # so `import imgio` (repo root) works from tools/
OUT = os.path.join(_ROOT, "studio_assets", "sample_images")


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


OWNER = "gen_sample_images"


class ManifestError(RuntimeError):
    """The existing manifest is unreadable / malformed — refuse to overwrite it (fail-closed)."""


def load_manifest(mpath: str) -> dict:
    """Read ``manifest.json`` (``{"images": [...]}``); a missing file is an empty manifest.

    A file that exists but is not valid JSON of that shape raises :class:`ManifestError`
    instead of being silently replaced — provenance records must never be clobbered.
    """
    if not os.path.exists(mpath):
        return {"images": []}
    try:
        with open(mpath, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise ManifestError(f"{mpath}: cannot parse existing manifest ({e}); fix or delete it") from e
    imgs = data.get("images") if isinstance(data, dict) else None
    if not isinstance(imgs, list) or not all(isinstance(e, dict) and "name" in e for e in imgs):
        raise ManifestError(f"{mpath}: expected {{'images': [{{'name': ...}}, ...]}}")
    return data


def merge_manifest(mpath: str, entries: list, owner: str) -> dict:
    """Read-modify-write ``manifest.json`` so generators can run in ANY order.

    Each entry is stamped ``owner``. Merge rules (per name, order-stable, idempotent):

    * an existing entry with the same ``name`` is replaced in place by the new one
      (legacy entries without an ``owner`` are claimed the same way);
    * an existing entry owned by *this* ``owner`` whose name is no longer generated
      is dropped (the generator is the truth for what it owns);
    * entries owned by *other* generators are kept untouched, in their position;
    * new names are appended.

    Before this, ``gen_sample_images`` rewrote the whole file and silently dropped the
    three ``gen_synth_samples`` entries whenever it ran second.
    """
    manifest = load_manifest(mpath)
    new = {e["name"]: dict(e, owner=owner) for e in entries}
    merged, seen = [], set()
    for old in manifest["images"]:
        n = old["name"]
        if n in new:
            merged.append(new[n]); seen.add(n)
        elif old.get("owner") == owner:
            continue                                   # stale entry of ours: dropped
        else:
            merged.append(old)                         # someone else's: preserved
    merged += [new[n] for n in new if n not in seen]
    manifest["images"] = merged
    os.makedirs(os.path.dirname(os.path.abspath(mpath)), exist_ok=True)
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    import imgio  # local: license-clean save

    entries = []
    for name, arr in _synthetic().items():
        p = os.path.join(OUT, name + ".png")
        imgio.save(p, np.asarray(arr, float))
        entries.append({"name": name, "file": name + ".png",
                        "source": "synthetic (Fullseye)", "licence": "own work"})
    for name, arr in _skimage().items():
        p = os.path.join(OUT, name + ".png")
        imgio.save(p, np.asarray(arr, float))
        entries.append({"name": name, "file": name + ".png",
                        "source": "skimage.data", "licence": "BSD / public domain (see scikit-image)"})

    manifest = merge_manifest(os.path.join(OUT, "manifest.json"), entries, OWNER)
    print("[sample_images] wrote %d images (manifest now %d entries) -> %s"
          % (len(entries), len(manifest["images"]), OUT))
    for it in manifest["images"]:
        print("  %-14s %s" % (it["name"], it["source"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
