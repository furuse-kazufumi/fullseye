# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""「写真から形を取り出して光を動かす」GIF(2026-09-04)。6 灯撮影 → photometric_stereo_robust で
法線+アルベド復元 → render_lambertian で光を一周(復元だけで再照明)。参考として真値法線の再照明を
並べ、角度誤差も焼き込む。積分した高さ場(integrate_normals)も 1 枚出す。すべて fullseye の op。
Run: py -3.11 tools/gen_hero_relight.py [--frames 24 --size 384]"""
from __future__ import annotations
import argparse, importlib.util, sys, time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import render3d, render_beauty as rb, photometric, specularity, video  # noqa: E402

def _ex():
    s = importlib.util.spec_from_file_location("ex", ROOT / "examples_3d" / "render_beauty.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--size", type=int, default=384); ap.add_argument("--fps", type=int, default=12)
    a = ap.parse_args(); ex = _ex(); S = a.size
    V, F, N, _A = ex.still_life(res_scale=0.7)
    lo, hi = V.min(0), V.max(0); cen = 0.5 * (lo + hi); rad = float(np.linalg.norm(hi - lo)) * 0.5
    pose = render3d.look_at(cen + np.array([2.2, -2.8, 1.6]) * rad * 0.85,
                            [cen[0], cen[1], cen[2] * 0.8], up=(0, 0, 1))
    K = render3d.intrinsics_from_fov(36.0, S, S); R = pose[:3, :3]
    view = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=S, height=S, attributes=True)
    sil = view["silhouette"] > 0; ys, xs = np.nonzero(sil)
    Nc = N @ R.T; g = np.einsum("ij,ijk->ik", view["bary"][ys, xs], Nc[F[view["face"][ys, xs]]])
    gt = np.zeros((S, S, 3)); gt[ys, xs] = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-15)
    Lw = [l / np.linalg.norm(l) for l in
          (np.array([np.cos(t) * 0.7, np.sin(t) * 0.7, 0.9]) for t in np.linspace(0, 2 * np.pi, 6, endpoint=False))]
    t0 = time.time()
    shots = [rb.render_beauty(V, F, pose=pose, intrinsics=K, size=S, ss=1, material="plastic", albedo=(0.8,) * 3,
                              brdf="lambert", brdf_params={"w": 0.8}, tonemap="linear", exposure=1.0, ambient=0.0,
                              light=tuple(l), ao=False, ground_shadow=False, background=(0, 0, 0),
                              smooth_normals=True, vertex_normals=N).mean(-1) for l in Lw]
    print(f"[capture] 6 lights {time.time() - t0:.0f}s", flush=True)
    Lc = np.array([R @ l for l in Lw])
    n_rec, alb, _ = specularity.photometric_stereo_robust(shots, Lc, method="ransac", threshold=0.05)
    # RANSAC は inlier が足りない画素を未定(非有限)で返す。誤差は有限画素だけで測り、
    # 再照明/積分には (0,0,1) を詰めて渡す(嘘の形を作らないための明示的な既定値)。
    bad = ~np.isfinite(n_rec).all(-1)
    n_rec = np.where(bad[..., None], np.array([0.0, 0.0, 1.0]), n_rec)
    e = photometric.angular_error_deg(n_rec, gt); ok = sil & np.isfinite(e) & ~bad
    err = float(np.median(e[ok])); print(f"[recover] undefined pixels {int((bad & sil).sum())}/{int(sil.sum())}", flush=True)
    print(f"[recover] median angular error {err:.3f} deg", flush=True)
    alb = np.where(sil, alb, 0.0)
    frames = []
    for i in range(a.frames):                       # 光を一周(復元法線だけで再照明)
        th = 2 * np.pi * i / a.frames
        l = np.array([np.cos(th) * 0.75, np.sin(th) * 0.75, 0.6]); l /= np.linalg.norm(l)
        rec = photometric.render_lambertian(n_rec, alb, l, ambient=0.05) * sil
        ref = photometric.render_lambertian(gt, alb, l, ambient=0.05) * sil
        pair = np.concatenate([rec, ref], axis=1)   # 左=復元のみ / 右=真値法線
        frames.append((np.clip(pair, 0, 1) * 255 + 0.5).astype(np.uint8))
    out = ROOT / "docs" / "articles" / "assets" / "media" / "relight_from_normals.gif"
    out.parent.mkdir(parents=True, exist_ok=True)
    video.write_video(str(out), frames, fps=a.fps); video.write_video(str(out.with_suffix(".mp4")), frames, fps=a.fps)
    z = photometric.integrate_normals(n_rec, mask=sil)
    zi = np.where(sil & np.isfinite(z), z, np.nan); rngz = float(np.nanmax(zi) - np.nanmin(zi))
    print(f"[relight] {out} {out.stat().st_size / 1e6:.2f} MB, {len(frames)} frames; height range {rngz:.2f} px")
    assert err < 1.0 and rngz > 0
    return 0

if __name__ == "__main__":
    sys.exit(main())
