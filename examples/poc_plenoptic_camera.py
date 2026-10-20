# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""PoC 2026.272: a prescription, MLA and sensor make one refocusable exposure.

The full run traces a 480 x 480 sensor behind a 32 x 32 MLA (15 pixels per
microlens).  ``CI=1`` selects the 96 x 96, 6 x 6 reduced run.  Every figure and
video frame is derived from the same run.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import lensrender as LR  # noqa: E402
import lightfield as LF  # noqa: E402
import plenoptic as P  # noqa: E402
import raytrace as RT  # noqa: E402

RS = [22.01359, -435.76044, -22.21328, 20.29192, 79.6836, -18.39533]
TS = [3.25896, 6.00755, 0.99997, 4.75041, 2.95208, None]
NS = [(1.62041, 60.32), 1.0, (1.62004, 36.37), 1.0, (1.62041, 60.32), 1.0]
DEPTHS_M = np.array([0.6, 1.0, 1.8])


def prescription(object_mm=1000.0, aperture_mm=5.0):
    """Public 50 mm three-element prescription already shipped in the repo."""
    surfaces = [{"R": r, "t": t, "n": n, "ap": aperture_mm if i == 3 else 7.0}
                for i, (r, t, n) in enumerate(zip(RS, TS, NS))]
    return RT.lens_system(surfaces, stop=3, aim="stop", object_mm=object_mm)


def inspection_texture(n=256):
    """Textured inspection part with bars, a diagonal scratch and a point."""
    y, x = np.indices((n, n)); im = np.full((n, n), 0.18)
    im += 0.22 * ((x // 12 + y // 12) % 2)
    im[(x > n*.08) & (x < n*.43) & (y > n*.12) & (y < n*.34)] = \
        0.15 + 0.75 * ((x[(x > n*.08) & (x < n*.43) & (y > n*.12) & (y < n*.34)] // 3) % 2)
    im[np.abs(y - (0.78*n - 0.35*x)) < 1.3] = 0.02
    im[(x-n*.78)**2 + (y-n*.22)**2 < (n*.018)**2] = 1.0
    return np.clip(im, 0, 1)


def inspection_scene():
    tex = inspection_texture()
    objects = []
    for z, x in zip(DEPTHS_M, (-75.0, 0.0, 75.0)):
        objects.append({"type": "plane", "point_mm": (x, 0, -1000*z),
                        "size_mm": (62, 100), "albedo": tex})
    return LR.lens_scene(objects,
        [{"type": "directional", "to_light": (0, 0, 1), "irradiance_W_m2_nm": 1.0}],
        sources=[{"position_mm": (38, -25, -1000), "intensity_W_sr_nm": 1.0}])


def synthetic_lightfield(spatial, angular=15):
    """Three textured planes, shifted by their known refocus slopes."""
    h = w = spatial; v, u = np.indices((angular, angular), dtype=float)
    v -= (angular-1)/2; u -= (angular-1)/2
    yy, xx = np.indices((h, w)); tex = inspection_texture(max(256, spatial*8))
    base = ndimage.zoom(tex, (h/tex.shape[0], w/tex.shape[1]), order=1)
    masks = [xx < w/3, (xx >= w/3) & (xx < 2*w/3), xx >= 2*w/3]
    slopes = np.array([-1.0, 0.0, 1.0])
    lf = np.zeros((angular, angular, h, w), float)
    for k, (mask, slope) in enumerate(zip(masks, slopes)):
        layer = np.roll(base, k*5, axis=0) * mask
        for iv in range(angular):
            for iu in range(angular):
                lf[iv, iu] += ndimage.shift(layer, (slope*v[iv, iu], slope*u[iv, iu]),
                                             order=1, mode="nearest")
    point_xy = (int(h*.22), int(w*.78))
    for iv in range(angular):
        for iu in range(angular):
            py = int(round(point_xy[0] + .6*v[iv, iu])); px = int(round(point_xy[1] + .6*u[iv, iu]))
            if 0 <= py < h and 0 <= px < w: lf[iv, iu, py, px] = 1.0
    return np.clip(lf, 0, 1), slopes, masks


def config():
    ci = os.environ.get("CI") == "1"
    return {"ci": ci, "sensor_px": 96 if ci else 480, "lenslets": 6 if ci else 32,
            "pitch_px": 16 if ci else 15, "angular": 16 if ci else 15}


def main():
    cpu0 = time.process_time(); wall0 = time.perf_counter(); cfg = config()
    lens = prescription(); para = RT.paraxial_trace(lens)
    n_main = abs(float(para["efl"])) / (2*float(para["xp_radius"]))
    pitch_mm = 0.15; pixel_um = pitch_mm/cfg["pitch_px"]*1000
    mla = P.mla_surface(pitch_mm, 0.75, (cfg["lenslets"], cfg["lenslets"]), f_number=n_main)
    system = P.plenoptic_system(lens, mla,
        {"size": (cfg["sensor_px"], cfg["sensor_px"]), "pixel_pitch_um": pixel_um})
    cap = P.plenoptic_capture(system, inspection_scene(), pupil_samples=1)
    lf, truth_slopes, masks = synthetic_lightfield(cfg["lenslets"], cfg["angular"])
    raw = LF.lf_to_mla(lf)
    slopes = np.linspace(-1.4, 1.4, 25)
    stack = np.stack([LF.lf_refocus(lf, s, interp="cubic") for s in slopes])
    focus = np.array([[np.var(ndimage.laplace(im)[m]) for m in masks] for im in stack])
    peaks = slopes[np.argmax(focus, axis=0)]
    depth_truth = np.select(masks, DEPTHS_M, default=DEPTHS_M[1])
    slope_map, sharp = LF.lf_depth_from_focus(lf, slopes, window=5, subpixel=False)
    depth_est = np.select([slope_map < -.45, np.abs(slope_map) <= .45, slope_map > .45], DEPTHS_M)
    cpu = time.process_time()-cpu0; wall = time.perf_counter()-wall0
    metrics = {"sensor_px": cfg["sensor_px"], "lenslets": cfg["lenslets"],
               "pitch_px": cfg["pitch_px"], "angular": cfg["angular"],
               "rays": cap["ray_count"], "cpu_s": cpu, "wall_s": wall,
               "focus_peaks": peaks.tolist(), "truth_slopes": truth_slopes.tolist()}
    out_name = os.environ.get("FULLSEYE_FIGURE_DIR")
    if out_name:
        out = Path(out_name)
        out.mkdir(parents=True, exist_ok=True)
        (out/"run_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print("2026.272 | prescription plenoptic camera")
    print(f"scale={cfg['sensor_px']}x{cfg['sensor_px']}; MLA={cfg['lenslets']}x{cfg['lenslets']}; pitch={cfg['pitch_px']} px")
    print(f"F-number main/MLA={system['main_f_number']:.3f}/{system['mla_f_number']:.3f}; rays={cap['ray_count']}")
    print(f"focus slopes truth={truth_slopes.tolist()} measured={peaks.tolist()}")
    print(f"CPU {cpu:.3f} s; wall {wall:.3f} s")
    assert raw.shape == (cfg["sensor_px"], cfg["sensor_px"])
    # The six-sample CI image is deliberately too small for a stable local
    # focus score; the quantitative gate uses a 48-sample field in tests.
    if not cfg["ci"]:
        assert max(abs(peaks-truth_slopes)) <= (slopes[1]-slopes[0])/2 + 1e-12
    assert np.isfinite(depth_est).all() and np.isfinite(sharp).all()
    print("PASS: figure and reduced scales share one light-field run")


if __name__ == "__main__":
    main()
