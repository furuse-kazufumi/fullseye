# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""フォトメトリックステレオの閉ループ(2026-09-04、ユーザー「PS 再現できる?」「fullseye で作れると見せる」)。
fullseye だけで: render_beauty(brdf=lambert, tonemap=linear)で 6 灯撮影 → photometric_stereo(最小二乗)/
photometric_stereo_robust(RANSAC)で法線復元 → render_mesh の真値法線と角度誤差。影あり(ground_shadow+AO)では
Lambert 仮定が破れて LS が壊れ、robust が救う — その差を数字で出す。Run: py -3.11 tools/gen_hero_photometric_stereo.py"""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import render3d, render_beauty as rb, api  # noqa: E402
import photometric, specularity  # noqa: E402
OUT = ROOT / "docs" / "articles" / "assets" / "hero_photometric_stereo.png"

def _ex():
    spec = importlib.util.spec_from_file_location("ex_rb", ROOT / "examples_3d" / "render_beauty.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def ang_err(n, gt, mask):
    d = np.clip(np.abs(np.einsum("ijk,ijk->ij", n, gt)), 0, 1)     # 符号規約差は abs で吸収
    e = np.degrees(np.arccos(d)); ok = mask & np.isfinite(e); return np.where(ok, e, 0.0), float(np.nanmedian(e[ok]))

def main() -> int:
    ex = _ex(); S = 512
    V, F, N, A = ex.still_life(res_scale=0.7)
    lo, hi = V.min(0), V.max(0); cen = 0.5 * (lo + hi); rad = float(np.linalg.norm(hi - lo)) * 0.5
    eye = cen + np.array([2.2, -2.8, 1.6]) * rad * 0.85
    pose = render3d.look_at(eye, [cen[0], cen[1], cen[2] * 0.8], up=(0, 0, 1))
    K = render3d.intrinsics_from_fov(36.0, S, S)
    view = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=S, height=S, attributes=True)
    sil = view["silhouette"] > 0
    R = pose[:3, :3]
    # 真値法線 = 陰影に使ったのと同じ頂点法線(SDF 勾配)を透視補正重心で補間しカメラ系へ。
    # render_mesh の "normals" は面ごとのフラット法線なので、それと比べると 9° 級の偽誤差が出る
    # (最初にそれで落ちた)。
    ys, xs = np.nonzero(sil); Nc = N @ R.T
    gt = np.zeros((S, S, 3)); g = np.einsum("ij,ijk->ik", view["bary"][ys, xs], Nc[F[view["face"][ys, xs]]])
    gt[ys, xs] = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-15)
    lights_w = [np.array([np.cos(a) * 0.7, np.sin(a) * 0.7, 0.9]) for a in np.linspace(0, 2 * np.pi, 6, endpoint=False)]
    lights_w = [l / np.linalg.norm(l) for l in lights_w]
    lights_c = np.array([R @ l for l in lights_w])                   # 真値法線はカメラ系
    ps_fn = getattr(api, "photometric_stereo", photometric.photometric_stereo)
    def shoot(l, shadows):
        img = rb.render_beauty(V, F, pose=pose, intrinsics=K, size=S, ss=1, material="plastic", albedo=(0.8,) * 3,
                               brdf="lambert", brdf_params={"w": 0.8}, tonemap="linear", exposure=1.0, ambient=0.0,
                               light=tuple(l), ao=shadows, ground_shadow=shadows, background=(0, 0, 0),
                               smooth_normals=True, vertex_normals=N, ao_samples=16, shadow_res=512, shadow_samples=4)
        return img.mean(axis=-1)
    t0 = time.time()
    clean = [shoot(l, False) for l in lights_w]; print(f"[render] 6 clean {time.time() - t0:.0f}s", flush=True)
    shad = [shoot(l, True) for l in lights_w]; print(f"[render] 6 shadowed {time.time() - t0:.0f}s", flush=True)
    n_ls_c, _ = ps_fn(clean, lights_c, mask=sil)
    n_ls_s, _ = ps_fn(shad, lights_c, mask=sil)
    n_rb_c, _, _ = specularity.photometric_stereo_robust(clean, lights_c, method="ransac", threshold=0.05)
    n_rb_s, _, inl = specularity.photometric_stereo_robust(shad, lights_c, method="ransac", threshold=0.05)
    e1, m1 = ang_err(n_ls_c, gt, sil); e2, m2 = ang_err(n_ls_s, gt, sil); e3, m3 = ang_err(n_rb_s, gt, sil); _, m0 = ang_err(n_rb_c, gt, sil)
    # 素朴 LS は付着影(cos_i<0 → 0 の非線形)で偏る(球で 9°、点灯光源だけなら 0.000°)。robust が正解。
    print(f"[gt] median angular error: LS clean {m1:.2f} | RANSAC clean {m0:.3f} | LS shadows {m2:.2f} | RANSAC shadows {m3:.2f} deg")
    assert m0 < 1.0 and m3 < m2 and m3 < m1, (m0, m1, m2, m3)
    def g(a, hi): return np.repeat(np.clip(np.asarray(a) / hi, 0, 1)[..., None], 3, -1)
    def nrm(n): return 0.5 * (n + 1) * sil[..., None]
    panels = [(g(clean[0], clean[0].max()), "撮影 1/6: render_beauty(lambert, linear)"), (g(shad[3], shad[3].max()), "撮影 4/6: 影・AO あり"),
              (nrm(gt), "真値法線: render_mesh"), (nrm(n_ls_c), f"photometric_stereo(最小二乗) {m1:.1f}° ← 付着影で偏る"),
              (nrm(n_ls_s), f"同・影+AO あり {m2:.1f}°"), (nrm(n_rb_s), f"photometric_stereo_robust(RANSAC) {m3:.2f}°(影ありでも)")]
    font = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 20); T, pad, cap = 400, 12, 36
    cv = Image.new("RGB", (pad + 3 * (T + pad), pad + 2 * (T + cap + pad)), (18, 20, 24)); dr = ImageDraw.Draw(cv)
    for i, (img, c) in enumerate(panels):
        im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((T, T), Image.LANCZOS)
        x = pad + (i % 3) * (T + pad); y = pad + (i // 3) * (T + cap + pad); cv.paste(im, (x, y)); dr.text((x, y + T + 5), c, font=font, fill=(235, 235, 235))
    cv.save(OUT, optimize=True); print(f"[ps] {OUT} {cv.size} ({time.time() - t0:.0f}s)"); return 0
if __name__ == "__main__":
    sys.exit(main())
