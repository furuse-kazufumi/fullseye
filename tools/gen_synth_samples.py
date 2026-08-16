#!/usr/bin/env python3
"""Generate own-work sample images by LEARNING a texture and synthesising a new one.

Dogfoods the foundation end-to-end — a procedural exemplar (my own work) → learn
its statistics → ``synth.synthesize_like`` → ``imgio.save`` — and produces
license-clean sample images that need no external dataset (unlike the skimage.data
classics). Each is verified honestly: ``feature_distance`` shows it matched the
exemplar's learned features, ``patch_novelty`` shows it is a genuinely NEW image,
not a crop. Deterministic (fixed seeds); re-runs are idempotent.

    py -3.11 tools/gen_synth_samples.py            # write PNGs + merge manifest
    py -3.11 tools/gen_synth_samples.py --verify   # print verification, write nothing
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import imgio
import synth

OUT = os.path.join(_ROOT, "studio_assets", "sample_images")
_N = 256


def _norm01(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float64)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)


def _exemplar_grain(seed: int = 0) -> np.ndarray:
    """Film-grain / sand: isotropic 1/f (pink) noise — a stochastic texture."""
    rng = np.random.default_rng(seed)
    F = np.fft.fftshift(np.fft.fft2(rng.standard_normal((_N, _N))))
    cy, cx = _N // 2, _N // 2
    y, x = np.ogrid[:_N, :_N]
    r = np.hypot(y - cy, x - cx)
    r[cy, cx] = 1.0
    return _norm01(np.real(np.fft.ifft2(np.fft.ifftshift(F / r))))


def _exemplar_weave(seed: int = 0) -> np.ndarray:
    """Fabric weave: two crossed oriented band-pass fields (anisotropic texture)."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:_N, 0:_N]
    warp = np.sin(2 * np.pi * x / 9.0) * np.sin(2 * np.pi * y / 22.0)
    weft = np.sin(2 * np.pi * y / 9.0) * np.sin(2 * np.pi * x / 22.0)
    return _norm01(warp + weft + 0.25 * rng.standard_normal((_N, _N)))


def _exemplar_brick(seed: int = 0) -> np.ndarray:
    """Brick wall: a STRUCTURED texture with per-brick jitter (for quilting).

    Slight width/offset/shade jitter + grain makes it non-periodic, so quilting
    produces a genuinely new arrangement (measurable novelty) rather than a
    verbatim re-tiling of a perfectly regular grid.
    """
    rng = np.random.default_rng(seed)
    img = np.full((_N, _N), 0.32)
    bh, mortar = 24, 4
    for i, ry in enumerate(range(0, _N, bh)):
        off = (28 if (i % 2) else 0) + int(rng.integers(-6, 7))
        rx = -off
        while rx < _N:
            bw = 56 + int(rng.integers(-10, 11))
            shade = 0.70 + 0.10 * rng.standard_normal()
            img[ry + mortar:ry + bh, rx + mortar:rx + bw] = shade
            rx += bw
    img = img + 0.03 * rng.standard_normal((_N, _N))
    return np.clip(img, 0, 1)


# name -> (exemplar, method, kwargs, description)
_SAMPLES = {
    "grain_synth": (_exemplar_grain(0), "spectral", {"seed": 11}, "1/f grain (spectral synthesis)"),
    "weave_synth": (_exemplar_weave(0), "spectral", {"seed": 12}, "fabric weave (spectral synthesis)"),
    "brick_quilt": (_exemplar_brick(0), "patch",
                    {"seed": 13, "block": 40, "overlap": 12, "size": (320, 320)},
                    "brick wall, enlarged (image quilting)"),
}


def _generate() -> dict:
    results = {}
    for name, (ex, method, kw, desc) in _SAMPLES.items():
        out = synth.synthesize_like(ex, seed=kw.pop("seed"), method=method, **kw)
        fd = synth.feature_distance(ex, out)
        nov = synth.patch_novelty(out, ex, seed=1)
        results[name] = {"image": out, "desc": desc, "method": method,
                         "feature_distance": fd, "novelty": nov}
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true", help="print verification only; write nothing")
    a = ap.parse_args()

    results = _generate()
    for name, r in results.items():
        fd = r["feature_distance"]
        print(f"[{name}] {r['desc']}: spectrum_l2={fd['spectrum_l2']:.4f} "
              f"hist_chi2={fd['hist_chi2']:.4f} novelty={r['novelty']:.5f}")
    if a.verify:
        return 0

    os.makedirs(OUT, exist_ok=True)
    for name, r in results.items():
        path = os.path.join(OUT, f"{name}.png")
        imgio.save(path, r["image"])                 # dogfoods imgio.save (raises on failure)
        back = imgio.load(path)                       # round-trip check
        assert back.shape == r["image"].shape, f"{name}: save/load shape mismatch"

    # merge manifest (own-work provenance), keep existing entries, no duplicates
    mpath = os.path.join(OUT, "manifest.json")
    manifest = {"images": []}
    if os.path.exists(mpath):
        with open(mpath, encoding="utf-8") as f:
            manifest = json.load(f)
    have = {e["name"] for e in manifest["images"]}
    for name, r in results.items():
        if name in have:
            continue
        manifest["images"].append({
            "name": name, "file": f"{name}.png",
            "source": f"synthesized (Fullseye synth.synthesize_like, {r['desc']})",
            "licence": "own work",
        })
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"wrote {len(results)} synthesized samples -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
