# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_itokawa_turntable — the article's rotating Itokawa GIF, rebuilt on the physically based pipeline.

    py -3.11 tools/gen_itokawa_turntable.py --frames 0 18      # render frames [0, 18)
    py -3.11 tools/gen_itokawa_turntable.py --frames 18 36
    py -3.11 tools/gen_itokawa_turntable.py --assemble          # PNG frames -> GIF (+ mp4)

Replaces ``showcase_turntable_itokawa.gif`` (2026-08-30: a 2,600-face mesh reconstructed
from the point cloud — decimated — with Lambert + ambient + a pedestal). The new clip uses
the same op chain as the hero still (``examples_3d/itokawa_regolith_hero.py``): the full
49,152-facet shape model, adaptive tessellation to 1.5 m facets with the geometry kept
exact, band-limited relief, angular boulders on the D^-3.1 law, Hapke BRDF, hard
ray-cast shadows with the Sun's 0.53° disc, zero ambient light. **Nothing is decimated.**

The *camera and the Sun* orbit the asteroid (constant phase angle), the mesh stays put, so
the baked relief and the sub-facet bump field are rigidly attached to the surface and the
shading is consistent from frame to frame. One exposure (from frame 0, lit median 0.45) is
used for every frame so the brightness does not pump.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.append(str(_ROOT / "examples_3d"))          # after the repo root: examples_3d/render_beauty.py is an example, not the module

import mesh  # noqa: E402
import itokawa_regolith_hero as H  # noqa: E402

render_beauty = H.render_beauty                       # the real render_beauty module the hero uses

N_FRAMES = 36
SIZE = 480
PHASE_DEG = 45.0
SUN_AZ = 135.0
FRAME_DIR = _ROOT / "out" / "itokawa_turntable"
GIF = _ROOT / "docs" / "articles" / "assets" / "showcase_turntable_itokawa.gif"
MP4 = _ROOT / "docs" / "articles" / "assets" / "media" / "itokawa.mp4"


def _rotz(deg: float) -> np.ndarray:
    c, s = np.cos(np.deg2rad(deg)), np.sin(np.deg2rad(deg))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _lit_median(img: np.ndarray) -> float:
    g = img.mean(axis=2)
    p = float(np.percentile(g, 99.5))
    lit = g[g > 0.04 * p]
    return float(np.median(lit)) if lit.size else 1.0


def render_frames(start: int, stop: int) -> None:
    V, F = mesh.read_mesh(str(H.STL))
    Vr, Fr, info = H.build_relief_mesh(V, F, cache_dir=H.STL.parent)
    nb = len(info["boulders"]["face"]) if "boulders" in info and "face" in info["boulders"] else "?"
    print(f"[mesh] {len(F)} facets -> relief mesh {len(Fr)} faces ({nb} boulders, "
          f"tess {'cached' if info['tess_cached'] else '%.0fs' % info['tess_time']})", flush=True)
    bump = dict(wavelengths=H.WAVELENGTHS, amplitudes=H.AMPLITUDES, seed=H.SEED, complement_edges=True)
    base_dir = np.array([0.15, -1.0, 0.35])
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    exp_file = FRAME_DIR / "exposure.txt"
    kw = dict(size=SIZE, ss=1, sun_angular_diameter_deg=0.53, shadow_samples=2, ao_samples=12,
              self_illumination=1.0, albedo_variation=0.12, tint=(1.0, 0.97, 0.93), bump=bump, **H.HAPKE)
    # one exposure for the whole clip, measured on frame 0 (lit median -> 0.45)
    if exp_file.exists():
        exposure = float(exp_file.read_text())
    else:
        pose, K, sun = H.camera_and_sun(Vr, SIZE, PHASE_DEG, cam_dir=base_dir, sun_azimuth_deg=SUN_AZ)
        probe = render_beauty.render_regolith(Vr, Fr, pose=pose, intrinsics=K, sun=sun, exposure=1.0, **kw)
        exposure = 0.45 / _lit_median(probe)
        exp_file.write_text(repr(exposure))
        print(f"[exposure] frame-0 lit median {_lit_median(probe):.3f} at exposure 1 -> exposure {exposure:.3f}")
    from PIL import Image
    for k in range(start, stop):
        out = FRAME_DIR / f"frame_{k:03d}.png"
        if out.exists():
            continue
        t0 = time.time()
        cd = _rotz(360.0 * k / N_FRAMES) @ base_dir
        pose, K, sun = H.camera_and_sun(Vr, SIZE, PHASE_DEG, cam_dir=cd, sun_azimuth_deg=SUN_AZ)
        img = render_beauty.render_regolith(Vr, Fr, pose=pose, intrinsics=K, sun=sun, exposure=exposure, **kw)
        u8 = np.round(np.clip(img, 0, 1) * 255).astype(np.uint8)
        Image.fromarray(u8).save(out)
        print(f"[frame {k:02d}] lit median {_lit_median(img):.3f}, clipped {(img.max(axis=2) >= 1.0).mean() * 100:.2f} %, "
              f"{time.time() - t0:.1f}s", flush=True)


def assemble(fps: int = 20) -> None:
    from PIL import Image
    import video
    frames = []
    for k in range(N_FRAMES):
        p = FRAME_DIR / f"frame_{k:03d}.png"
        if not p.exists():
            raise SystemExit(f"missing {p}")
        frames.append(np.asarray(Image.open(p).convert("RGB")))
    video.write_video(str(GIF), frames, fps=fps)
    print(f"[gif] {GIF} {GIF.stat().st_size / 1e6:.2f} MB, {len(frames)} frames @ {fps} fps")
    if MP4.parent.exists():
        try:
            video.write_video(str(MP4), frames, fps=fps)
            print(f"[mp4] {MP4} {MP4.stat().st_size / 1e6:.2f} MB")
        except Exception as e:      # noqa: BLE001 - mp4 is a convenience copy
            print(f"[mp4] skipped: {e}")
    # honest check: every frame kept, lit median stable
    im = Image.open(GIF)
    meds = [_lit_median(np.asarray(Image.open(FRAME_DIR / f"frame_{k:03d}.png").convert("RGB")) / 255.0)
            for k in range(N_FRAMES)]
    print(f"[check] gif frames {im.n_frames}/{N_FRAMES}, lit median {min(meds):.3f}..{max(meds):.3f}")
    assert im.n_frames == N_FRAMES


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", nargs=2, type=int, metavar=("START", "STOP"))
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--fps", type=int, default=20)
    a = ap.parse_args()
    if a.frames:
        render_frames(a.frames[0], a.frames[1])
    if a.assemble:
        assemble(a.fps)
    if not a.frames and not a.assemble:
        ap.error("give --frames START STOP and/or --assemble")
    return 0


if __name__ == "__main__":
    sys.exit(main())
