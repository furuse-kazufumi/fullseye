"""X-ray CT / laminography inspection: a reconstructed volume -> per-slice denoise
-> segment the material -> find internal voids (defects) -> measure them.

Industrial NDT: a CT or laminography scan yields a 3-D volume; the job is to find
voids/cracks/inclusions inside a part. This runs the fullseye operator stack
slice-by-slice on a *synthetic* volume (a cylinder with two internal voids), so it
is self-contained. Laminography (limited-angle) is modelled by blurring the volume
anisotropically along z — the characteristic axial smear — and the pipeline still
recovers the voids.

    py -3.11 examples/ct_inspection.py [--save out_dir] [--laminography]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


def synthetic_ct(n=64, nz=48, laminography=False, seed=0):
    """A cylindrical part (bright material) with two internal spherical voids
    (dark), plus scan noise. *laminography* adds the limited-angle axial smear."""
    rng = np.random.default_rng(seed)
    zz, yy, xx = np.mgrid[0:nz, 0:n, 0:n].astype(np.float64)
    cy, cx = n / 2, n / 2
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    vol = np.where(r < n * 0.4, 0.8, 0.05)                 # solid cylinder
    for (vz, vy, vx, vr) in [(nz * 0.4, n * 0.45, n * 0.5, 5.0),
                             (nz * 0.6, n * 0.55, n * 0.42, 4.0)]:
        d = np.sqrt((zz - vz) ** 2 + (yy - vy) ** 2 + (xx - vx) ** 2)
        vol[d < vr] = 0.05                                 # internal voids (defects)
    vol = ndimage.gaussian_filter(vol, 0.8)
    if laminography:
        vol = ndimage.gaussian_filter(vol, (3.0, 0.4, 0.4))  # anisotropic axial smear
    vol = np.clip(vol + 0.04 * rng.standard_normal(vol.shape), 0, 1)
    return vol


def run(save_dir=None, laminography=False):
    vol = synthetic_ct(laminography=laminography)
    nz = vol.shape[0]
    material = np.zeros_like(vol, bool)
    for z in range(nz):
        # denoise the slice, segment the material (Otsu) — the fullseye op stack
        seg = fs.run_pipeline(vol[z], [("gaussian", 0.4, 0.5), ("otsu", 0.5, 0.5)])
        material[z] = seg > 0.5

    # voids = inside the part's bounding solid but not material. Fill each slice's
    # material to get the "should be solid" mask, then a hole is a void.
    solid = ndimage.binary_fill_holes(material)
    voids = solid & ~material
    lbl, n_void = ndimage.label(voids)
    sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, n_void + 1)) if n_void else np.array([])
    # keep only sizeable 3-D voids (drop speckle)
    keep = [i + 1 for i, s in enumerate(sizes) if s >= 20]
    defect_voxels = int(sum(sizes[i - 1] for i in keep))

    result = {
        "laminography": laminography,
        "material_voxels": int(material.sum()),
        "n_defects": len(keep),
        "defect_voxels": defect_voxels,
        "defect_fraction": round(defect_voxels / max(1, int(solid.sum())), 5),
    }
    print("[ct] " + "  ".join(f"{k}={v}" for k, v in result.items()))

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        mid = nz // 2
        fs.save(os.path.join(save_dir, "slice.png"), vol[mid])
        fs.save(os.path.join(save_dir, "material.png"), material[mid].astype(float))
        fs.save(os.path.join(save_dir, "voids.png"), voids[mid].astype(float))
        print(f"[ct] wrote mid-slice / material / voids PNGs -> {save_dir}")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--save", default=None)
    ap.add_argument("--laminography", action="store_true", help="model limited-angle axial smear")
    a = ap.parse_args()
    run(save_dir=a.save, laminography=a.laminography)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
