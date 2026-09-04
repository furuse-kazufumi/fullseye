# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1 枚目 hero の差別化パネル(2026-09-04、ユーザー「この絵は DirectX で大昔からできる。差別化が見えないとダメ」)。
同じシーンについて、絵(beauty)の隣に **物理量チャンネル**(depth/法線/AO/影/シルエット)を numpy 配列として
並べ、それを食った fullseye の視覚 op(エッジ)と真値照合の数字を出す。= レンダラは「絵を出す装置」でなく
「真値つき合成データを返す計測器」— これが GPU パイプラインとの違い。Run: py -3.11 tools/gen_hero_channels.py"""
from __future__ import annotations
import importlib.util, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import render3d, render_ao, render_shadow, render_beauty as rb, api  # noqa: E402
OUT = ROOT / "docs" / "articles" / "assets" / "hero_channels.png"

def _ex():
    spec = importlib.util.spec_from_file_location("ex_rb", ROOT / "examples_3d" / "render_beauty.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def _gray(a, lo=None, hi=None):
    a = np.asarray(a, np.float64); m = np.isfinite(a)
    lo = np.nanmin(a[m]) if lo is None else lo; hi = np.nanmax(a[m]) if hi is None else hi
    g = np.zeros_like(a); g[m] = np.clip((a[m] - lo) / max(hi - lo, 1e-12), 0, 1)
    return np.repeat(g[..., None], 3, -1)

def main() -> int:
    ex = _ex(); S = 640
    V, F, N, A = ex.still_life(res_scale=0.7)
    lo, hi = V.min(0), V.max(0); cen = 0.5 * (lo + hi); rad = float(np.linalg.norm(hi - lo)) * 0.5
    eye = cen + np.array([2.2, -2.8, 1.6]) * rad * 0.85
    pose = render3d.look_at(eye, [cen[0], cen[1], cen[2] * 0.8], up=(0, 0, 1))
    K = render3d.intrinsics_from_fov(36.0, S, S); light = (0.45, 0.55, 0.75)
    t0 = time.time()
    beauty = rb.render_beauty(V, F, pose=pose, intrinsics=K, size=S, ss=1, material="metal", albedo=(0.85,) * 3,
                              vertex_albedo=A, light=light, ambient=0.16, ao=True, ground_shadow=False, tonemap="aces",
                              exposure=1.5, background=(0.07, 0.08, 0.10), ao_samples=16, smooth_normals=True, vertex_normals=N)
    view = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=S, height=S)
    depth, normals, sil = view["depth"], view["normals"], view["silhouette"]
    ao = render_ao.ambient_occlusion(V, F, pose=pose, intrinsics=K, width=S, height=S)
    ao = ao["ao"] if isinstance(ao, dict) else ao
    sh = render_shadow.shadow_raycast(V, F, light, pose=pose, intrinsics=K, width=S, height=S)
    sh = sh["shadow"] if isinstance(sh, dict) else sh
    # 視覚 op を食わせる: 深度の不連続=物体輪郭(sobel_mag)と、レンダラのシルエット境界を照合
    d_in = np.where(np.isfinite(depth), depth, np.nanmax(depth[np.isfinite(depth)]))
    d01 = (d_in - d_in.min()) / max(np.ptp(d_in), 1e-12)
    edges = api.apply(d01, "sobel_mag", 0.5, 0.5)
    sil_edge = api.apply(sil.astype(np.float64), "sobel_mag", 0.5, 0.5) > 0.05
    e_on = float(edges[sil_edge].mean()); e_off = float(edges[~sil_edge & (sil > 0)].mean())
    ao_contact = float(np.nanmin(ao[sil > 0])); ao_top = float(np.nanmax(ao[sil > 0]))
    print(f"[gt] edge energy on silhouette boundary {e_on:.3f} vs interior {e_off:.3f} (ratio {e_on / max(e_off, 1e-9):.1f}x)")
    print(f"[gt] AO range on object {ao_contact:.2f}..{ao_top:.2f}; shadowed frac {float((sh < 0.5).mean()):.3f}; {time.time() - t0:.0f}s")
    assert e_on > 3 * e_off and ao_contact < 0.5 < ao_top
    panels = [(beauty, "beauty(絵)"), (_gray(depth), "depth [m] 数値配列"), (0.5 * (normals + 1) * (sil > 0)[..., None], "法線 (H,W,3)"),
              (_gray(ao, 0, 1), f"AO 配列 min {ao_contact:.2f}"), (_gray(sh, 0, 1), "影マスク(レイキャスト)"),
              (_gray(np.clip(edges * 4, 0, 1)), f"sobel_mag(depth) 境界/内部 {e_on / max(e_off, 1e-9):.0f}x")]
    font = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 22); T, pad, cap = 420, 12, 40
    W = pad + 3 * (T + pad); H = pad + 2 * (T + cap + pad)
    cv = Image.new("RGB", (W, H), (18, 20, 24)); dr = ImageDraw.Draw(cv)
    for i, (img, c) in enumerate(panels):
        im = Image.fromarray((np.clip(np.asarray(img, np.float64), 0, 1) * 255 + 0.5).astype(np.uint8)).resize((T, T), Image.LANCZOS)
        x = pad + (i % 3) * (T + pad); y = pad + (i // 3) * (T + cap + pad)
        cv.paste(im, (x, y)); dr.text((x, y + T + 6), c, font=font, fill=(235, 235, 235))
    cv.save(OUT, optimize=True); print(f"[channels] {OUT} {cv.size}"); return 0
if __name__ == "__main__":
    sys.exit(main())
