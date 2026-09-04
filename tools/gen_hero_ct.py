# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""記事図: 記事の静物を「X 線 CT にかける」(2026-09-04)。

やること: hero の静物(ジャイロイド格子球 / 三葉結び目 / 歯車)を SDF から **中身の詰まった
減衰係数ボリューム**として作り(材質ごとに μ を変える)、スライスごとに
`radon_transform` で平行ビーム投影 → 光子数のポアソンノイズを載せる →
`filtered_backprojection` で再構成 → **真値ボリュームと Dice / μ 誤差で採点**する。

構造化光が「表面を測る」側なら、CT は「中を見る」側。どちらも同じライブラリの中に
真値があるので、閉ループで採点できる。

零点(beat-the-null): (a) ランプフィルタ無しの単純逆投影(`backproject_sinogram`)は
1/r のボケが残る。(b) 視野角を 1/8 に間引いた 24 ビュー FBP はストリークが出る。
実手法(180 ビュー FBP)が両方を Dice で判別的に上回ることを assert する。

Run: py -3.11 tools/gen_hero_ct.py
出力: docs/articles/assets/hero_ct.png
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

import tomography  # noqa: E402

OUT = ROOT / "docs" / "articles" / "assets" / "hero_ct.png"
N = 144                     # xy 格子(スライス 1 枚の一辺)
VIEWS = 180                 # 実手法のビュー数
VIEWS_FEW = 24              # 零点(b)のビュー数
I0 = 3.0e4                  # 入射光子数(ポアソンノイズの強さ)
PART_MM = 30.0              # 被写体の横幅(mm)。μ を cm^-1 で書くための較正の宣言
#: 材質の線減衰係数 [cm^-1](100 keV 付近の公開値の桁: PMMA 0.17 / Al 0.46 / Ti 1.2)。
#: ★ここは「ただの定数」ではない: 線積分 p = Σ μ·Δx が 10 を超えると exp(-p) が
#: 光子数 1 を割り、対数が飽和して **p が頭打ち**になる(photon starvation)。
#: 最初の版は μ を 0.55–1.0「/画素」で置いてしまい、p が 30 に達して復元 μ が
#: 50–84% 低く出た。零点(単純逆投影)の方が Dice で勝ってしまい、そこで気づいた。
MU_CM = {"pmma": 0.17, "al": 0.46, "ti": 1.20}

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


def build_phantom(ex):
    """still_life と同じ配置で、中身の詰まった μ ボリュームと材質ラベルを作る。

    still_life は SDF → メッシュ → (scale, xy 平行移動, 接地)の順に変換する。ここでは
    その **逆写像**でワールド格子を各部品のローカル座標へ戻し、SDF を直接評価するので、
    メッシュ化の解像度に依存しない「本当の中身」が得られる(= 再構成の真値)。
    """
    # (sdf, bounds, mesh_res, scale, xy, μ [cm^-1 相当], 名前)
    parts = [
        (ex.gyroid_sphere_sdf, ((-1.1, 1.1),) * 3, 110, 0.9, (-0.9, 0.9), MU_CM["al"], "格子球(Al)"),
        (ex.knot_sdf, ((-1.4, 1.4), (-1.4, 1.4), (-0.6, 0.6)), 96, 0.75, (0.9, -0.3), MU_CM["ti"], "結び目(Ti)"),
        (ex.gear_sdf, ((-0.6, 0.6), (-0.6, 0.6), (-0.12, 0.12)), 100, 1.6, (-0.8, -1.0), MU_CM["pmma"], "歯車(PMMA)"),
    ]
    placed = []
    for fn, bounds, res, scale, xy, mu, name in parts:
        V, _F, _Nn = ex._sdf_mesh(fn, bounds, res)
        Vw = V * scale
        Vw[:, :2] += np.asarray(xy, float)
        dz = -Vw[:, 2].min()
        Vw[:, 2] += dz
        placed.append((fn, scale, np.array([xy[0], xy[1], dz]), mu, name,
                       Vw.min(0), Vw.max(0)))

    lo = np.min([p[5] for p in placed], axis=0) - 0.06
    hi = np.max([p[6] for p in placed], axis=0) + 0.06
    step = float(max(hi[0] - lo[0], hi[1] - lo[1])) / (N - 1)
    nz = int(np.ceil((hi[2] - lo[2]) / step)) + 1
    xs = lo[0] + step * np.arange(N)
    ys = lo[1] + step * np.arange(N)
    zs = lo[2] + step * np.arange(nz)

    mu_vol = np.zeros((nz, N, N))
    lab = np.zeros((nz, N, N), np.int8)
    for idx, (fn, scale, off, mu, name, plo, phi) in enumerate(placed, start=1):
        i0 = np.searchsorted(zs, plo[2] - step, "left"), np.searchsorted(zs, phi[2] + step, "right")
        j0 = np.searchsorted(ys, plo[1] - step, "left"), np.searchsorted(ys, phi[1] + step, "right")
        k0 = np.searchsorted(xs, plo[0] - step, "left"), np.searchsorted(xs, phi[0] + step, "right")
        Z, Y, X = np.meshgrid(zs[i0[0]:i0[1]], ys[j0[0]:j0[1]], xs[k0[0]:k0[1]], indexing="ij")
        world = np.stack([X, Y, Z], axis=-1)
        local = (world - off) / scale                    # ★ still_life の変換の逆写像
        inside = fn(local) < 0.0
        sub = (slice(*i0), slice(*j0), slice(*k0))
        mu_vol[sub] = np.where(inside, mu, mu_vol[sub])
        lab[sub] = np.where(inside, idx, lab[sub])
        print(f"  {name}: μ={mu} 体素 {int(inside.sum())}", flush=True)
    return mu_vol, lab, [p[4] for p in placed], [p[3] for p in placed], step


def scan_slice(sl, angles, rng):
    """1 スライスを撮影する: 線積分 → 光子数 → ポアソン → 対数で線積分へ戻す。"""
    sino = tomography.radon_transform(sl, angles_deg=angles)
    counts = rng.poisson(np.maximum(I0 * np.exp(-sino), 1e-9))
    return -np.log(np.maximum(counts, 1.0) / I0)


def dice(a, b):
    inter = float(np.logical_and(a, b).sum())
    return 2.0 * inter / max(float(a.sum() + b.sum()), 1e-9)


def main() -> int:
    t0 = time.time()
    ex = _ex()
    mu_cm, lab, names, mus_cm, step = build_phantom(ex)
    nz, ny, nx = mu_cm.shape
    gt = lab > 0
    # 世界単位 → mm → cm。投影は「画素あたりの減衰」で積分されるので、μ[cm^-1] に
    # 画素の物理サイズ [cm] を掛けたものが p の単位になる。復元値は逆に割って戻す。
    world_w = step * (N - 1)
    px_cm = 0.1 * PART_MM * (step / world_w)
    mu_vol = mu_cm * px_cm                       # 画素あたりの減衰
    mus = [m * px_cm for m in mus_cm]
    print(f"[phantom] {mu_vol.shape} voxel={10 * px_cm:.3f} mm / 材質 {len(names)} 種 "
          f"/ 占有 {100 * gt.mean():.2f}% / 最大線積分 p={float((mu_vol.sum(axis=2)).max()):.2f} "
          f"({time.time() - t0:.0f}s)", flush=True)

    ang = np.linspace(0.0, 180.0, VIEWS, endpoint=False)
    ang_few = np.linspace(0.0, 180.0, VIEWS_FEW, endpoint=False)
    rng = np.random.default_rng(5)

    rec = np.zeros_like(mu_vol)
    rec_bp = np.zeros_like(mu_vol)
    rec_few = np.zeros_like(mu_vol)
    for k in range(nz):
        sino = scan_slice(mu_vol[k], ang, rng)
        rec[k] = tomography.filtered_backprojection(sino, angles_deg=ang, size=nx)
        rec_bp[k] = tomography.backproject_sinogram(sino, angles_deg=ang, size=nx)
        sino_few = scan_slice(mu_vol[k], ang_few, rng)
        rec_few[k] = tomography.filtered_backprojection(sino_few, angles_deg=ang_few, size=nx)
        if k % 20 == 0:
            print(f"  slice {k}/{nz} ({time.time() - t0:.0f}s)", flush=True)
    print(f"[scan] {nz} スライス × ({VIEWS} + {VIEWS_FEW}) ビュー ({time.time() - t0:.0f}s)", flush=True)

    thr = 0.5 * min(mus)                                  # 最も薄い材質の半分で二値化
    d_real = dice(rec > thr, gt)
    # 単純逆投影は絶対値が別スケールなので、**その手法に最も有利なしきい値**で採点する
    # (自分の零点を不利な設定で殴らない)
    cand = np.linspace(rec_bp[gt].min(), rec_bp.max(), 60)
    d_bp = max(dice(rec_bp > c, gt) for c in cand)
    d_few = dice(rec_few > thr, gt)
    err_mu = [float(np.mean(rec[lab == i + 1]) - m) for i, m in enumerate(mus)]
    # ★材質ごとの数字は **再現率(recall)**。「その材質のラベル内で拾えた割合」であって
    # Dice ではない(ラベルの外に出た偽陽性を数えないので、Dice と名乗ると必ず 1.0 に
    # 近づく)。全体の取りこぼし/拾いすぎは下の precision / recall で別に出す。
    rec_bin = rec > thr
    d_mat = [float((rec_bin & (lab == i + 1)).sum()) / max(float((lab == i + 1).sum()), 1e-9)
             for i in range(len(mus))]
    tp = float((rec_bin & gt).sum())
    prec = tp / max(float(rec_bin.sum()), 1e-9)
    recall = tp / max(float(gt.sum()), 1e-9)
    # 各材質の「最も薄いところ」が体素いくつぶんか(分解能の限界を数字で出す)。
    # 薄い板は部分体積効果で μ が薄まる ―― バグではなく物理なので、隠さず並べる。
    from scipy import ndimage as _ndi
    thin = []
    for i in range(len(mus)):
        m = lab == i + 1
        edt = _ndi.distance_transform_edt(m)       # 材質内の「表面までの距離」
        thin.append(2.0 * float(np.median(edt[m])))   # ×2 ≒ 局所の肉厚(体素)
    print(f"[score] Dice 実手法 {d_real:.4f}(precision {prec:.4f} / recall {recall:.4f})"
          f" / 単純逆投影 {d_bp:.4f}(最良しきい値)/ {VIEWS_FEW} ビュー {d_few:.4f}", flush=True)
    for nm, m, e, dm, th in zip(names, mus, err_mu, d_mat, thin):
        print(f"  {nm}: μ 真値 {m / px_cm:.3f} cm^-1 → 誤差 {e / px_cm:+.4f} "
              f"({100 * abs(e) / m:.1f}%) / 再現率 {dm:.3f} / 局所肉厚 {th:.1f} 体素", flush=True)
    # 実手法が両方の零点を **明確に**(1.5 倍以上)上回ること。
    assert d_real > 1.5 * max(d_bp, d_few), (d_real, d_bp, d_few)
    assert d_real > 0.85, d_real
    # 厚い部材(Ti の管・PMMA の板)は μ が 10% 以内で戻る。薄い殻(Al)は部分体積効果で
    # 薄まるので 20% 以内。ここを一律 10% にすると「薄い物を測れない」事実が消える。
    assert abs(err_mu[1]) / mus[1] < 0.10 and abs(err_mu[2]) / mus[2] < 0.10, err_mu
    assert abs(err_mu[0]) / mus[0] < 0.20, err_mu

    # ---- 図 ----
    ks = int(np.argmax([(lab[k] > 0).sum() for k in range(nz)]))   # 最も情報の多いスライス
    sino_show = scan_slice(mu_vol[ks], ang, np.random.default_rng(5))
    vmax = max(mus) * 1.15
    err = np.abs(rec[ks] - mu_vol[ks])
    mip_gt = mu_vol.max(axis=0)
    mip_rec = rec.max(axis=0)
    panels = [
        (cmap(mu_vol[ks] / vmax), f"真値スライス z={ks}"),
        (cmap((sino_show - sino_show.min()) / max(float(np.ptp(sino_show)), 1e-9)),
         f"サイノグラム({VIEWS} ビュー × {sino_show.shape[1]} 検出器)"),
        (cmap(rec[ks] / vmax), f"FBP 再構成(Dice {d_real:.3f})"),
        (cmap(rec_bp[ks] / max(rec_bp[ks].max(), 1e-9)),
         f"零点(a) ランプ無しの逆投影(Dice {d_bp:.3f})"),
        (cmap(rec_few[ks] / vmax), f"零点(b) {VIEWS_FEW} ビュー FBP(Dice {d_few:.3f})"),
        (cmap(err / (0.25 * vmax)), f"|Δμ| 誤差マップ  適合率 {prec:.2f} / 再現率 {recall:.2f}"),
    ]
    extra = [(cmap(mip_gt / vmax), "真値の最大値投影(上から)"),
             (cmap(mip_rec / vmax), "再構成の最大値投影(上から)")]

    font = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/YuGothB.ttc", 17)
    T, pad, cap, head = 380, 12, 34, 70
    cols = 4
    rows = 2
    cv = Image.new("RGB", (pad + cols * (T + pad), head + pad + rows * (T + cap + pad)), (18, 20, 24))
    dr = ImageDraw.Draw(cv)
    dr.text((pad, 8), f"同じ静物を X 線 CT にかける — 横幅 {PART_MM:.0f} mm / 体素 {10 * px_cm:.3f} mm / "
                      f"{nz} スライス × {VIEWS} ビュー / 光子 {I0:.0e} のポアソンノイズ",
            font=font, fill=(240, 240, 240))
    dr.text((pad, 36), f"μ[1/cm] = Al {mus_cm[0]} / Ti {mus_cm[1]} / PMMA {mus_cm[2]}  ―― "
                       f"真値は SDF そのもの(メッシュ化を経ない中身)",
            font=small, fill=(198, 200, 206))
    for i, (img, c) in enumerate(panels[:3] + extra[:1] + panels[3:] + extra[1:]):
        im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((T, T), Image.LANCZOS)
        x = pad + (i % cols) * (T + pad)
        y = head + pad + (i // cols) * (T + cap + pad)
        cv.paste(im, (x, y))
        dr.text((x, y + T + 5), c, font=small, fill=(235, 235, 235))
    cv.save(OUT, optimize=True)
    print(f"[fig] {OUT} {cv.size} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
