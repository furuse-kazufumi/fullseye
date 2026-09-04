# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""記事図: 構造化光スキャナを記事の静物へ当てて、真値深度と mm で突き合わせる(2026-09-04)。

やること: 記事 1 枚目の静物(SDF/CSG のトーラス結び目 + ジャイロイド球 + 歯車)に、
投影機から相補 Gray code 18 枚 + 位相シフト 4 枚を投げた「撮影」を合成し、
fullseye の op だけで復号 → 三角測量 → レンダラの真値深度と比較する。
DirectX でも描けるのは「絵」まで。ここでやっているのは **絵から寸法を取り戻す**側で、
しかも答え合わせができる(真値を持っているレンダラが同じライブラリの中にいる)。

Run: py -3.11 tools/gen_hero_structured_light.py
出力: docs/articles/assets/hero_structured_light.png
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import camera  # noqa: E402
import render3d  # noqa: E402
from fringe import (absolute_phase, graycode_decode, triangulate_column,  # noqa: E402
                    wrapped_phase)

OUT = ROOT / "docs" / "articles" / "assets" / "hero_structured_light.png"
S = 560                     # カメラ解像度
PW = PH = 1024              # 投影機解像度(Gray 10 ビット)
BITS = 10
FREQ = 40                   # 投影機幅を横切る縞の本数(1 周期 = 25.6 px)
N_STEPS = 4
NOISE = 0.01
MM = 200.0                  # 静物の対角をこの mm に正規化して報告する(較正の宣言)

_CMAP = np.array([[0.267, 0.005, 0.329], [0.229, 0.322, 0.545], [0.128, 0.567, 0.551],
                  [0.369, 0.789, 0.383], [0.993, 0.906, 0.144]])


def cmap(v01):
    v = np.clip(np.nan_to_num(v01), 0.0, 1.0) * (len(_CMAP) - 1)
    i = np.clip(np.floor(v).astype(int), 0, len(_CMAP) - 2)
    f = (v - i)[..., None]
    return _CMAP[i] * (1.0 - f) + _CMAP[i + 1] * f


def _ex():
    spec = importlib.util.spec_from_file_location("ex_rb", ROOT / "examples_3d" / "render_beauty.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def gray_planes(code, bits):
    g = code ^ (code >> 1)
    return np.stack([(g >> (bits - 1 - i)) & 1 for i in range(bits)]).astype(np.float64)


def main() -> int:
    t0 = time.time()
    ex = _ex()
    V, F, N, _alb = ex.still_life(res_scale=0.8)
    lo, hi = V.min(0), V.max(0)
    scale = MM / float(np.linalg.norm(hi - lo))       # 世界単位 → mm
    V = V * scale
    lo, hi = V.min(0), V.max(0)
    cen = 0.5 * (lo + hi)
    rad = float(np.linalg.norm(hi - lo)) * 0.5

    # カメラと投影機。基線は視距離の ~30%(実機の構造化光ヘッドと同程度の三角形)
    eye = cen + np.array([2.2, -2.8, 1.6]) * rad * 0.85
    peye = cen + np.array([-0.6, -3.4, 1.9]) * rad * 0.85
    pose_c = render3d.look_at(eye, [cen[0], cen[1], cen[2] * 0.8], up=(0, 0, 1))
    pose_p = render3d.look_at(peye, [cen[0], cen[1], cen[2] * 0.8], up=(0, 0, 1))
    K_c = render3d.intrinsics_from_fov(36.0, S, S)
    K_p = render3d.intrinsics_from_fov(30.0, PW, PH)

    # look_at は gluLookAt 規約(-Z 前方)、render_mesh/K は CV 規約(+Z 前方)。
    # 三角測量は CV 側で閉じているので姿勢に FLIP を掛けてから合成する。
    FLIP = np.diag([1.0, -1.0, -1.0])
    Rc, tc = FLIP @ pose_c[:3, :3], FLIP @ pose_c[:3, 3]
    Rp, tp = FLIP @ pose_p[:3, :3], FLIP @ pose_p[:3, 3]
    R = Rp @ Rc.T
    t = tp - R @ tc
    base = float(np.linalg.norm(eye - peye))
    dist = float(np.linalg.norm(eye - cen))

    view = render3d.render_mesh(V, F, pose=pose_c, intrinsics=K_c, width=S, height=S,
                                background=np.nan, attributes=True)
    depth_gt, sil = view["depth"], view["silhouette"] > 0
    pview = render3d.render_mesh(V, F, pose=pose_p, intrinsics=K_p, width=PW, height=PH,
                                 background=np.nan)
    dproj = pview["depth"]
    print(f"[render] camera+projector {time.time() - t0:.0f}s  sil={int(sil.sum())}", flush=True)

    # 各画素の 3D 点 → 投影機コラム u_p(真値)+ 投影機からの可視性(影)
    Xc = camera.depth_to_points(np.where(sil, depth_gt, np.nan), K_c, organized=True)
    Xp = Xc @ R.T + t
    zp = Xp[..., 2]
    with np.errstate(all="ignore"):
        up = K_p[0, 0] * Xp[..., 0] / zp + K_p[0, 2]
        vp = K_p[1, 1] * Xp[..., 1] / zp + K_p[1, 2]
    inside = (zp > 0) & (up >= 0) & (up <= PW - 1) & (vp >= 0) & (vp <= PH - 1)
    ui = np.clip(np.nan_to_num(np.round(up)), 0, PW - 1).astype(np.int64)
    vi = np.clip(np.nan_to_num(np.round(vp)), 0, PH - 1).astype(np.int64)
    seen = np.isfinite(dproj[vi, ui]) & (zp <= dproj[vi, ui] + 0.5 * scale)
    lit = sil & inside & np.nan_to_num(seen, nan=False) & np.isfinite(up)

    # 滑らかな陰影(SDF 勾配の頂点法線を透視補正重心で補間 → CV 規約へ)
    ys, xs = np.nonzero(sil)
    Nc = N @ Rc.T                                    # Rc は FLIP 込み(CV 規約)
    nrm = np.zeros((S, S, 3))
    g = np.einsum("ij,ijk->ik", view["bary"][ys, xs], Nc[F[view["face"][ys, xs]]])
    nrm[ys, xs] = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-15)
    pc_cam = -R.T @ t
    with np.errstate(invalid="ignore"):
        L = pc_cam - Xc
        L = L / np.maximum(np.linalg.norm(L, axis=-1, keepdims=True), 1e-9)
        cos_i = np.nan_to_num(np.einsum("ijk,ijk->ij", nrm, L))
    lit = lit & (cos_i > 0.15)
    shade = np.where(lit, 0.9 * cos_i, 0.0)
    print(f"[geom] lit {int(lit.sum())} / {int(sil.sum())} px ({100 * lit.sum() / sil.sum():.1f}%)",
          flush=True)

    # 撮影の合成: 位相シフト 4 枚 + 相補 Gray 2*BITS 枚
    rng = np.random.default_rng(11)
    phase_true = 2.0 * np.pi * FREQ * np.nan_to_num(up) / PW
    shots = np.stack([np.clip(shade * (0.5 + 0.5 * np.cos(phase_true - 2 * np.pi * n / N_STEPS))
                              + rng.normal(0, NOISE, shade.shape), 0, 1) for n in range(N_STEPS)])
    planes = gray_planes(ui, BITS)

    def shoot(p):
        return np.clip(shade[None] * p + rng.normal(0, NOISE, p.shape), 0, 1)

    hi_b, lo_b = shoot(planes), shoot(1.0 - planes)
    bits_cmp = (hi_b > lo_b).astype(np.float64)

    # 復号 → 三角測量
    wrapped = wrapped_phase(shots)
    col_coarse = graycode_decode(bits_cmp, thresh=0.5).astype(np.float64)
    coarse_phase = 2.0 * np.pi * FREQ * col_coarse / PW
    phi = absolute_phase(wrapped, coarse_phase)
    col = phi * PW / (2.0 * np.pi * FREQ)
    depth = triangulate_column(np.where(lit, col, np.nan), K_c, K_p, R, t)
    depth_gray = triangulate_column(np.where(lit, col_coarse, np.nan), K_c, K_p, R, t)

    ok = lit & np.isfinite(depth) & np.isfinite(depth_gt)
    err = np.abs(depth - depth_gt)
    rmse = float(np.sqrt(np.mean(err[ok] ** 2)))
    med = float(np.median(err[ok]))
    ok_g = lit & np.isfinite(depth_gray)
    rmse_g = float(np.sqrt(np.mean((np.abs(depth_gray - depth_gt)[ok_g]) ** 2)))
    span = float(np.nanmax(depth_gt[sil]) - np.nanmin(depth_gt[sil]))
    n_bad = int((lit & (np.abs(col_coarse - np.nan_to_num(np.round(up))) > 0)).sum())
    print(f"[scan] RMSE {rmse:.4f} mm (median {med:.4f}) / Gray only {rmse_g:.4f} mm / "
          f"span {span:.1f} mm / gray misdecode {n_bad} px", flush=True)
    assert rmse < 0.01 * span and rmse < rmse_g, (rmse, rmse_g, span)

    # ---- 図 ----
    def g3(a):
        return np.repeat(np.clip(np.nan_to_num(a), 0, 1)[..., None], 3, -1)

    d0, d1 = np.nanmin(depth_gt[ok]), np.nanmax(depth_gt[ok])
    emax = 0.1
    panels = [
        (g3(shots[0]), f"撮影 1/{N_STEPS + 2 * BITS}: 位相シフト縞(周期 {PW / FREQ:.1f} px)"),
        # 表示は判定後の二値ではなく **生の撮影**(判定は照らされた画素でしか意味を持たず、
        # 背景の二値は両方ノイズの大小比べ = 砂嵐になる)
        (g3(hi_b[BITS - 3]), f"撮影: 相補 Gray の 1 ビット面(全 {BITS} 面 ×2)"),
        (cmap((wrapped + np.pi) / (2 * np.pi)) * lit[..., None], "巻き込み位相(高精度・2π 不定)"),
        (cmap(col_coarse / PW) * lit[..., None], "Gray 復号のコラム番号(絶対・整数)"),
        (cmap((np.nan_to_num(depth, nan=d1) - d0) / max(d1 - d0, 1e-9)) * ok[..., None],
         f"三角測量した深度(奥行 {span:.0f} mm)"),
        (cmap(np.nan_to_num(err, nan=0.0) / emax) * ok[..., None],
         f"真値との差(0–{emax:.2f} mm)RMSE {rmse:.3f} / 中央値 {med:.3f} mm"),
    ]
    font = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 17)
    T, pad, cap = 400, 12, 36
    head = 44
    cv = Image.new("RGB", (pad + 3 * (T + pad), head + pad + 2 * (T + cap + pad)), (18, 20, 24))
    dr = ImageDraw.Draw(cv)
    dr.text((pad, 12), f"構造化光スキャナを fullseye の op だけで組む — 視距離 {dist:.0f} mm / "
                       f"基線 {base:.0f} mm / 撮影 {N_STEPS + 2 * BITS} 枚 / ノイズ σ={NOISE}",
            font=font, fill=(240, 240, 240))
    for i, (img, c) in enumerate(panels):
        im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((T, T), Image.LANCZOS)
        x = pad + (i % 3) * (T + pad)
        y = head + pad + (i // 3) * (T + cap + pad)
        cv.paste(im, (x, y))
        dr.text((x, y + T + 6), c, font=small, fill=(235, 235, 235))
    cv.save(OUT, optimize=True)
    print(f"[fig] {OUT} {cv.size} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
