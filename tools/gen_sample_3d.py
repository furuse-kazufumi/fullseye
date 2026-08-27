"""Generate the shipped 3-D sample datasets for the examples3d gallery (dev tool).

These are **real-world** 3-D samples so the toolkit's examples run on genuine data,
not just synthetic spheres:

  * ``itokawa_points.npy`` — a decimated surface point cloud of near-Earth asteroid
    25143 Itokawa, from the Gaskell shape model (Hayabusa mission). Public-domain
    scientific data (co-archived at NASA PDS Small Bodies Node); see ATTRIBUTION.md.
  * ``skeleton_ct.npy`` — a synthetic X-ray-CT density volume of a hand skeleton,
    voxelised from the MS-Human-700 anatomical bone meshes (a *dummy* tomographic
    phantom built from real bone geometry — for demonstrating volumetric CT ops).

This is a **development tool**, not shipped in the wheel (like ``gen_sample_thumbs.py``).
Re-run it to regenerate the small ``.npy`` samples that DO ship in ``studio_assets/sample_3d``.

    py -3.11 tools/gen_sample_3d.py itokawa
    py -3.11 tools/gen_sample_3d.py skeleton_ct
    py -3.11 tools/gen_sample_3d.py all
"""
from __future__ import annotations

import os
import sys
import gzip
import urllib.request

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
_OUT = os.path.join(_ROOT, "studio_assets", "sample_3d")
_CACHE = os.path.join(_ROOT, "data", "sample_3d_cache")   # gitignored dev cache

_ITOKAWA_URL = "https://data.darts.isas.jaxa.jp/pub/hayabusa/shape/gaskell/itokawa_f0049152.stl.gz"
_MS700_GEO = "C:/dev/projects/ms_human_700_jaw/assets/geometry"


def _ensure_dirs():
    os.makedirs(_OUT, exist_ok=True)
    os.makedirs(_CACHE, exist_ok=True)


def gen_itokawa(n_points: int = 3000, seed: int = 0):
    """Download (if absent) the Gaskell Itokawa STL, sample a small surface cloud, ship it."""
    import mesh
    _ensure_dirs()
    stl = os.path.join(_CACHE, "itokawa_f0049152.stl")
    if not os.path.exists(stl):
        gz = stl + ".gz"
        print(f"downloading Itokawa shape model from JAXA DARTS ...\n  {_ITOKAWA_URL}")
        urllib.request.urlretrieve(_ITOKAWA_URL, gz)
        with gzip.open(gz, "rb") as f, open(stl, "wb") as o:
            o.write(f.read())
    V, F = mesh.read_mesh(stl)
    pts = mesh.sample_surface(V, F, n_points, seed=seed).astype(np.float32)
    # centre and scale to metres (shape model is in km) for intuitive units.
    pts = (pts - pts.mean(0)) * 1000.0
    out = os.path.join(_OUT, "itokawa_points.npy")
    np.save(out, pts)
    span = pts.max(0) - pts.min(0)
    print(f"itokawa_points.npy: {pts.shape} float32, extent {span.round(1)} m, "
          f"{os.path.getsize(out)} bytes")


def gen_skeleton_ct(res: int = 96, seed: int = 0):
    """Voxelise real MS-Human-700 hand bones into a synthetic X-ray-CT density volume.

    The individual bone meshes are modelled about the origin, so we lay them out in a
    simple anatomical hand pose (metacarpals fanned, phalanges distal) — a *dummy*
    phantom of real bone geometry. Density = bone interior (1) blurred to mimic the
    CT point-spread function, plus a faint soft-tissue envelope and mild noise.
    """
    import mesh
    import render3d
    from scipy import ndimage
    _ensure_dirs()
    # hand bones (metacarpals + proximal/middle/distal phalanges of fingers 2-5) with a
    # crude anatomical layout: (finger index, chain offset along -y, lateral x slot).
    layout = [
        ("1mc", 0.030, -0.010), ("2mc", 0.000, -0.004), ("3mc", 0.000, 0.004),
        ("4mc", 0.002, 0.012), ("5mc", 0.006, 0.020),
        ("2proxph", -0.028, -0.004), ("3proxph", -0.030, 0.004),
        ("4proxph", -0.028, 0.012), ("5proxph", -0.024, 0.020),
        ("2midph", -0.050, -0.004), ("3midph", -0.054, 0.004),
        ("2distph", -0.064, -0.004), ("3distph", -0.068, 0.004),
    ]
    # common world grid covering the assembled hand.
    placed = []
    for name, dy, dx in layout:
        p = os.path.join(_MS700_GEO, name + ".stl")
        if not os.path.exists(p):
            continue
        V, F = mesh.read_mesh(p)
        V = V - V.mean(0)                       # centre each bone
        V = V + np.array([dx, dy, 0.0])         # place in the hand
        placed.append((V, F))
    allV = np.vstack([v for v, _ in placed])
    lo, hi = allV.min(0), allV.max(0)
    pitch = float((hi - lo).max()) / res
    vol = None
    for V, F in placed:
        occ, origin = render3d.voxelize_solid(V, F, pitch=pitch)
        # paste each bone's occupancy into the shared grid by integer offset.
        off = np.round((origin - lo) / pitch).astype(int)
        if vol is None:
            dims = np.ceil((hi - lo) / pitch).astype(int)[::-1] + occ.shape  # generous
            vol = np.zeros(np.ceil((hi - lo) / pitch).astype(int)[::-1] + 4, dtype=bool)
        oz, oy, ox = off[2], off[1], off[0]
        dz, dy2, dx2 = occ.shape
        vol[oz:oz + dz, oy:oy + dy2, ox:ox + dx2] |= occ
    dens = vol.astype(np.float32)
    dens = ndimage.gaussian_filter(dens, 0.7)          # CT point-spread blur
    soft = ndimage.gaussian_filter(vol.astype(np.float32), 3.0)
    dens = dens + 0.15 * (soft > 0.02)                 # faint soft-tissue envelope
    rng = np.random.default_rng(seed)
    dens = dens + rng.normal(0, 0.02, dens.shape).astype(np.float32)   # mild noise
    dens = np.clip(dens, 0.0, None).astype(np.float32)
    out = os.path.join(_OUT, "skeleton_ct.npy")
    np.save(out, dens)
    print(f"skeleton_ct.npy: {dens.shape} float32 (z,y,x), bones={len(placed)}, "
          f"{os.path.getsize(out)} bytes")


def write_attribution():
    _ensure_dirs()
    txt = """# 3-D sample data — sources & attribution

## itokawa_points.npy
Decimated surface point cloud of near-Earth asteroid **25143 Itokawa**, derived from
the **Gaskell shape model** produced from JAXA *Hayabusa* mission imagery.

- Source: JAXA DARTS archive — https://data.darts.isas.jaxa.jp/pub/hayabusa/shape/gaskell/
  (file `itokawa_f0049152.stl`, "generated from tri2stl by Naru Hirata").
- The Gaskell Itokawa shape model is co-archived at the **NASA PDS Small Bodies Node**
  (public-domain scientific data).
- Please cite: Gaskell, R. W., et al. (2008), *Characterizing and navigating small bodies
  with imaging data*, Meteoritics & Planetary Science 43(6), 1049-1061; and the Hayabusa/AMICA
  shape dataset. Shipped here as a small derived point cloud for demonstration.

## skeleton_ct.npy
Synthetic X-ray-CT density volume built by voxelising anatomical hand-bone meshes from the
**MS-Human-700** musculoskeletal model (bone geometry), arranged in a dummy hand pose. Used
only to demonstrate Fullseye's volumetric / tomography operators on realistic bone shapes.
"""
    with open(os.path.join(_OUT, "ATTRIBUTION.md"), "w", encoding="utf-8") as f:
        f.write(txt)
    print("ATTRIBUTION.md written")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("itokawa", "all"):
        gen_itokawa()
    if which in ("skeleton_ct", "all"):
        gen_skeleton_ct()
    write_attribution()
