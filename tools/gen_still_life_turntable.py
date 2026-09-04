# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""静物 hero(examples_3d/render_beauty.still_life)のターンテーブル GIF/MP4。
「立体なら回転させておいてほしい」(2026-09-04)。カメラが z 軸まわりを一周、光は固定。
Run: py -3.11 tools/gen_still_life_turntable.py [--frames 24 --size 480]
"""
from __future__ import annotations
import argparse, importlib.util, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import render3d, render_beauty as rb, video  # noqa: E402

def _ex():
    spec = importlib.util.spec_from_file_location("ex_rb", ROOT / "examples_3d" / "render_beauty.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--size", type=int, default=480); ap.add_argument("--fps", type=int, default=12)
    a = ap.parse_args()
    ex = _ex()
    V, F, N, A = ex.still_life(res_scale=0.7)
    lo, hi = V.min(0), V.max(0); cen = 0.5 * (lo + hi); rad = float(np.linalg.norm(hi - lo)) * 0.5
    K = render3d.intrinsics_from_fov(36.0, a.size, a.size)
    frames = []
    t0 = time.time()
    for i in range(a.frames):
        th = 2 * np.pi * i / a.frames
        off = np.array([2.2 * np.cos(th) + 2.8 * np.sin(th), 2.2 * np.sin(th) - 2.8 * np.cos(th), 1.6]) * rad * 0.85
        pose = render3d.look_at(cen + off, [cen[0], cen[1], cen[2] * 0.8], up=(0, 0, 1))
        img = rb.render_beauty(V, F, pose=pose, intrinsics=K, size=a.size, ss=1, material="metal",
                               albedo=(0.85, 0.85, 0.85), vertex_albedo=A, light=(0.45, 0.55, 0.75), ambient=0.16,
                               ao=True, ground_shadow=True, tonemap="aces", exposure=1.5,
                               background=(0.07, 0.08, 0.10), ao_samples=12, shadow_res=512,
                               penumbra=12.0, shadow_samples=4, shadow_pcf=1, smooth_normals=True, vertex_normals=N)
        frames.append((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))
        print(f"[frame] {i + 1}/{a.frames} {time.time() - t0:.0f}s", flush=True)
    out = ROOT / "examples_3d" / "_gallery" / "still_life_turntable.gif"
    video.write_video(str(out), frames, fps=a.fps)
    video.write_video(str(out.with_suffix(".mp4")), frames, fps=a.fps)
    print(f"[done] {out} {out.stat().st_size / 1e6:.2f} MB, {len(frames)} frames")
    return 0

if __name__ == "__main__":
    sys.exit(main())
