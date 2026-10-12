# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: レーザー光切断の誤差の床はスペックルが決める —— 平均しても消えない、推定器の順位も入れ替わる

    py -3.11 examples/poc_laser_line_speckle_floor.py

``poc_weld_bead_scan_angle.py`` の続編です。あちらは光条を**なめらかなガウスの帯 + 加法雑音**
で描き、中心を取る推定器を比べました(3 点の対数放物線が、輝度最大の画素より 7.5 倍良い)。
けれど実物のレーザー光条は**粒々**です。レーザー光はコヒーレントなので、波長より粗い面で
反射した光は画素ごとにでたらめな位相で干渉し、スペックルになる。この PoC は同じ光切断を
**コヒーレント結像**(``fs.ledger.laser_line_coherent``: 粗面の位相 → 観察開口の瞳 →
``|E|²`` → 画素の積分)で描き直して、次の 4 つを実測します。

1. **加法雑音の世界の勝者が負ける**。輝度最大の画素・3 点の対数放物線・重心 2 種を、
   前作と同じ細い光条(1σ = 1.4 画素)+ 雑音 1.5 % と、スペックルの光条 + 同じ雑音で比べる。
   加法雑音では対数放物線が輝度最大より約 9 倍、重心より約 1.6 倍良い。スペックルでは
   **順位が入れ替わり**、山の 3 点しか見ない推定器は「いちばん明るい粒」を追って、輝度最大の
   画素と同じ誤差(差 3 % 程度)まで落ちる —— 9 倍の差が消える。重心は光条全体を平均するので
   いちばん良く、列ごとの値は Dorsch の床と同じ桁に着く。
2. **フレームを平均しても下がらない**。部品が止まっていればスペックルは毎フレーム同じ
   なので、100 枚平均しても誤差はそのまま(読み出し雑音だけが消える)。部品を動かして
   **毎フレーム別のスペックル**にすると 1/√N で下がる。なめらかな光条 + 雑音の世界では
   静止のまま 1/√N で下がる —— 加法雑音のモデルでは「平均すれば良くなる」と誤って言う。
3. **開口と三角測量角が床を決める**。観察開口 sin u と三角測量角 θ を振った誤差が、
   Dorsch–Häusler–Herrmann(1994)の ``δz = C·λ/(2π sin u sin θ)`` の線に、傾き −1 で乗る。
   比例定数(実測 / 式)は表に出す(門にはしない)。
4. **画素を大きくしても重心の誤差は変わらない**。画素が粒より大きくなると、見た目の
   コントラストは下がる(Goodman の積分スペックル)。けれど箱で積分した強度の重心は
   元の強度の重心と**厳密に同じ**なので、重心の誤差は 1e-9 µm の桁まで動かない。

真値: 光条の中心は描画に入れた ``row0 + h·sin θ / 画素``(``h`` は乱数で与えた高さ)。
スペックルの統計(指数分布・粒径)は ``tests/test_coherent.py`` が Goodman の定理と
Airy の閉形式で確かめてあり、ここでは要点だけ再掲します。

★正直に書いておくこと(合成であること):
  * スカラ回折・近軸・倍率 1(物体側の座標で描く)・焦点の合った平面の粗面。高さの変化は
    光条をずらすだけで、前縮み(斜めから見ると光条の見かけの幅が cos θ 倍)・Scheimpflug・
    デフォーカス・体積散乱は入っていない。粗面は完全発達(位相が一様乱数)。
  * Dorsch らの式は原論文の本文を読めていない(抄録のみ)。2π の係数は二次文献の引用の形。
    だから**傾き**を判定し、**比例定数は開示**する。
  * 重心の誤差は光条の幅 w と平均する長さ L に √(w/L) で依存する(``tests`` で実測)。
    「スポットの大きさによらない」という Dorsch の言い方は L ≈ w の場合に当たる。この PoC の
    3 章は L = w(光条の幅と同じ長さの束)で測る。
  * 物体側の細格子が粗い(1 粒に 2 点)と傾きが 1.13 まで反る(実測)。ここでは 1 粒に 4 点以上。

走らせ方: ``py -3.11 examples/poc_laser_line_speckle_floor.py``
(図は ``FULLSEYE_FIGURE_DIR`` を指定したときだけ書く)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402  (台帳の公開経路 fs.ledger を使う)

CHECKS = []

# ---- 光切断センサ(物体側の寸法) ------------------------------------------ #
WAVE_UM = 0.65            # 赤色の半導体レーザー
PIX_UM = 5.0              # 物体側の画素
OVERSAMPLE = 4            # 物体側の細格子 = 1.25 µm(1 粒に 9 点)
LINE_W_UM = 14.0          # 光条の 1/e² 半幅 = 前作の 1σ 1.4 画素(カメラから見た幅)
SIN_U = 0.03              # 観察開口(被写界深度のために絞った値)
THETA_DEG = 30.0          # 三角測量角
NOISE = 0.015             # 読み出し雑音(光条の山の平均に対する比)
NY = 49                   # 行(光条を横切る向き)。中心が画素の中央に来る奇数


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


def sin_t(deg=THETA_DEG):
    return math.sin(math.radians(deg))


def laser(ncol, seed, height, sin_u=SIN_U, deg=THETA_DEG, noise=NOISE, noise_seed=None,
          ny=NY, pix=PIX_UM, oversample=OVERSAMPLE, width=LINE_W_UM, **kw):
    """台帳の公開経路(``fs.ledger``)からスペックルの光条を描く。"""
    return fs.ledger.laser_line_coherent(
        shape=(ny, ncol), wavelength_um=WAVE_UM, sin_u_obs=sin_u, pixel_um=pix,
        line_width_um=width, height_um=height, sin_theta=sin_t(deg), pixel_oversample=oversample,
        noise=noise, seed=seed, noise_seed=noise_seed, **kw)


def smooth(ncol, height, noise=NOISE, noise_seed=0, ny=NY, deg=THETA_DEG):
    """前作と同じ世界: なめらかなガウスの帯(画素で積分)+ 加法雑音。山の平均は 1。"""
    r0 = (ny - 1) / 2.0 + height * sin_t(deg) / PIX_UM
    s = OVERSAMPLE
    yy = (np.arange(ny * s) + 0.5) / s - 0.5
    prof = np.exp(-2.0 * ((yy - r0) * PIX_UM) ** 2 / LINE_W_UM ** 2)
    prof = prof.reshape(ny, s).mean(axis=1)
    img = np.repeat(prof[:, None], ncol, axis=1)
    return img + np.random.default_rng(noise_seed + 77).normal(0.0, noise, img.shape)


def truth_row(height, ny=NY, deg=THETA_DEG, pix=PIX_UM):
    return (ny - 1) / 2.0 + height * sin_t(deg) / pix


# ---- 光条の中心を取る推定器(列ごと) --------------------------------------- #
def est_argmax(img):
    """輝度最大の画素(整数)。"""
    return img.argmax(axis=0).astype(float)


def est_log_parabola(img):
    """山の 3 点の対数に放物線(ガウス当てはめ)。前作で最良だった推定器。"""
    ny, nx = img.shape
    k = np.clip(img.argmax(axis=0), 1, ny - 2)
    ix = np.arange(nx)
    lg = [np.log(np.clip(img[k + d, ix], 1e-6, None)) for d in (-1, 0, 1)]
    den = lg[0] - 2.0 * lg[1] + lg[2]
    dd = np.where(np.abs(den) > 1e-12, 0.5 * (lg[0] - lg[2]) / np.where(den == 0, 1, den), 0.0)
    return k + np.clip(dd, -1.0, 1.0)


def est_centroid_fixed(img, half=6):
    """重心・固定窓(公称の中心 ±half 行、負の値も重みに入れる = 整流しない)。"""
    ny = img.shape[0]
    c = int(round((ny - 1) / 2.0))
    r = np.arange(max(0, c - half), min(ny, c + half + 1))
    w = img[r]
    return (w * r[:, None]).sum(axis=0) / w.sum(axis=0)


def est_centroid_adaptive(img, frac=0.25, half=10):
    """重心・追従窓(列ごとの山の frac 以上の画素だけ、山の ±half 行)。"""
    ny, nx = img.shape
    k = img.argmax(axis=0)
    pk = img.max(axis=0)
    r = np.arange(ny)[:, None]
    m = (np.abs(r - k[None, :]) <= half) & (img >= frac * pk[None, :])
    w = np.where(m, img, 0.0)
    return (w * r).sum(axis=0) / w.sum(axis=0)


ESTIMATORS = (("輝度最大の画素", est_argmax), ("3 点の対数放物線", est_log_parabola),
              ("重心・固定窓", est_centroid_fixed), ("重心・追従窓", est_centroid_adaptive))


def block_centroid(img, block):
    ny, nx = img.shape
    nb = nx // block
    b = img[:, : nb * block].reshape(ny, nb, block).sum(axis=2)
    r = np.arange(ny, dtype=float)[:, None]
    return (b * r).sum(axis=0) / b.sum(axis=0)


def rms_um(rows, truth, deg=THETA_DEG, pix=PIX_UM):
    """行の誤差 → 高さの誤差 [µm](三角測量: Δz = Δ行 · 画素 / sin θ)の RMS。"""
    e = (np.asarray(rows) - truth) * pix / sin_t(deg)
    return float(np.sqrt(np.mean(e * e)))


def contrast(img, row):
    """光条の芯(真の中心に最も近い 1 行)に沿ったコントラスト σ/⟨I⟩。"""
    core = img[int(round(row))]
    return float(core.std() / core.mean())


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    lim = fs.ledger.triangulation_speckle_limit(WAVE_UM, SIN_U, sin_t(), 1.0)
    print("=" * 76)
    print("PoC: レーザー光切断の誤差の床はスペックルが決める")
    print("=" * 76)
    print("λ = %.2f µm、観察開口 sin u = %.3f、三角測量角 θ = %.0f°、物体側の画素 %.0f µm、"
          "光条の半幅 %.0f µm" % (WAVE_UM, SIN_U, THETA_DEG, PIX_UM, LINE_W_UM))
    print("スペックルの粒(自己相関の半値全幅) %.1f µm、Dorsch の床 δz = %.2f µm"
          % (lim["speckle_fwhm_um"], lim["delta_z_um"]))

    # ---- 1. スペックルは本物か ---------------------------------------------- #
    print("\n[1] スペックルの統計(Goodman の定理と円形瞳の Airy)")
    cut = SIN_U / WAVE_UM * PIX_UM / 2.0          # 半分の画素で見た遮断周波数(粒を 2 倍細かく見る)
    st = fs.ledger.speckle_statistics(fs.ledger.speckle_field((384, 384), cutoff=cut, seed=1))
    fw_um = st["speckle_fwhm_px"] * PIX_UM / 2.0
    check(abs(st["contrast"] - 1) < 0.05 and st["ks_p_exponential"] > 1e-3,
          "完全発達の強度は指数分布(C = 1)",
          "C = %.3f、KS p = %.2f" % (st["contrast"], st["ks_p_exponential"]))
    check(abs(fw_um / lim["speckle_fwhm_um"] - 1) < 0.05, "粒径 = 0.5145 λ / sin u",
          "%.2f µm(式 %.2f µm)" % (fw_um, lim["speckle_fwhm_um"]))
    st2 = fs.ledger.speckle_statistics(fs.ledger.speckle_field((384, 384), cutoff=cut,
                                                                polarizations=2, n_patterns=2, seed=2))
    red = fs.ledger.speckle_reduction(n_patterns=2, polarizations=2)
    check(abs(st2["contrast"] / red["contrast"] - 1) < 0.05,
          "偏光 2 本 × 独立 2 枚の和は C = 1/√4",
          "C = %.3f(式 %.3f)" % (st2["contrast"], red["contrast"]))

    # コヒーレント結像は「振幅で」線形: 位相だけの格子は、±1 次が瞳の外なら一様な J0(a)² に
    a, per = 1.3, 16
    ph = a * np.sin(2 * np.pi * np.arange(128) / per)[None, :] * np.ones((128, 1))
    I0 = fs.ledger.coherent_image(np.ones((128, 128)), ph, cutoff=0.5 / per)
    from scipy.special import j0
    check(float(np.max(np.abs(I0 - j0(a) ** 2))) < 1e-12,
          "位相だけの格子を 0 次だけ通すと一様な J0(a)²(インコヒーレントなら 1 のまま)",
          "%.6f(J0² = %.6f)" % (float(I0.mean()), j0(a) ** 2))

    # ---- 2. 推定器の順位 ------------------------------------------------------ #
    print("\n[2] 同じ光条・同じ雑音 %.1f %%。違うのは光がコヒーレントかどうかだけ(列ごと、高さの RMS [µm])"
          % (100 * NOISE))
    NCOL, NIMG = 1024, 3
    rng = np.random.default_rng(5)
    heights = rng.uniform(-10, 10, NIMG)
    imgs_s = [smooth(NCOL, h, noise_seed=k) for k, h in enumerate(heights)]
    imgs_c = [laser(NCOL, 10 + k, h, noise_seed=k) for k, h in enumerate(heights)]
    res = {}
    for name, fn in ESTIMATORS:
        es = rms_um(np.concatenate([fn(im) - truth_row(h) for im, h in zip(imgs_s, heights)]), 0.0)
        ec = rms_um(np.concatenate([fn(im) - truth_row(h) for im, h in zip(imgs_c, heights)]), 0.0)
        res[name] = (es, ec)
        print("  %-14s 加法雑音 %7.3f µm   スペックル %7.3f µm   (%5.1f 倍に悪化)" % (name, es, ec, ec / es))
    add = {k: v[0] for k, v in res.items()}
    spk = {k: v[1] for k, v in res.items()}
    best_add = min(add, key=add.get)
    check(best_add == "3 点の対数放物線" and add["重心・固定窓"] / add[best_add] > 1.4
          and add["輝度最大の画素"] / add[best_add] > 5,
          "加法雑音の世界では 3 点の対数放物線が勝つ",
          "重心・固定窓の %.1f 分の 1、輝度最大の %.0f 分の 1"
          % (add["重心・固定窓"] / add[best_add], add["輝度最大の画素"] / add[best_add]))
    check(spk["3 点の対数放物線"] > 1.5 * spk["重心・固定窓"],
          "スペックルの世界では順位が入れ替わる(山の 3 点 = いちばん明るい粒を追う)",
          "対数放物線 %.2f µm / 重心 %.2f µm = %.1f 倍"
          % (spk["3 点の対数放物線"], spk["重心・固定窓"], spk["3 点の対数放物線"] / spk["重心・固定窓"]))
    r_pk = spk["3 点の対数放物線"] / spk["輝度最大の画素"]
    check(abs(r_pk - 1) < 0.2 and add["輝度最大の画素"] / add["3 点の対数放物線"] > 5,
          "山を見る 2 つ(輝度最大と 3 点当てはめ)の差は消える",
          "加法雑音 %.1f 倍 → スペックル %.2f 倍" % (add["輝度最大の画素"] / add["3 点の対数放物線"], 1 / r_pk))
    r_add = add["重心・固定窓"] / add["重心・追従窓"]
    r_spk = spk["重心・固定窓"] / spk["重心・追従窓"]
    check(abs(math.log(r_spk)) < abs(math.log(r_add)) and abs(r_spk - 1) < 0.25,
          "重心 2 種は加法雑音では差があり、スペックルでは同じ床に寄る",
          "固定窓 / 追従窓 = %.2f → %.2f" % (r_add, r_spk))
    floor = spk["重心・固定窓"]
    print("  (Dorsch の床 C·λ/(2π sin u sin θ) = %.2f µm、列ごとの重心は %.2f 倍)"
          % (lim["delta_z_um"], floor / lim["delta_z_um"]))
    check(floor > 5 * add[best_add], "スペックルの床は加法雑音の最良より桁で高い",
          "%.2f µm vs %.3f µm" % (floor, add[best_add]))

    # ---- 3. フレームの平均 ---------------------------------------------------- #
    print("\n[3] フレームを N 枚平均する(重心・固定窓、高さの RMS [µm])")
    NC3, NS = 256, (1, 4, 16, 64, 100)
    frames_static = [laser(NC3, 7, 0.0, noise_seed=k) for k in range(max(NS))]
    frames_moving = [laser(NC3, 1000 + k, 0.0, noise_seed=k) for k in range(max(NS))]
    frames_smooth = [smooth(NC3, 0.0, noise_seed=k) for k in range(max(NS))]
    curves = {"静止した部品(同じスペックル)": [], "部品を動かす(毎フレーム別のスペックル)": [],
              "なめらかな光条 + 雑音(前作の世界)": []}
    tr = truth_row(0.0)
    for n in NS:
        curves["静止した部品(同じスペックル)"].append(
            rms_um(est_centroid_fixed(np.mean(frames_static[:n], axis=0)), tr))
        curves["部品を動かす(毎フレーム別のスペックル)"].append(
            rms_um(est_centroid_fixed(np.mean(frames_moving[:n], axis=0)), tr))
        curves["なめらかな光条 + 雑音(前作の世界)"].append(
            rms_um(est_centroid_fixed(np.mean(frames_smooth[:n], axis=0)), tr))
    for k, v in curves.items():
        print("  %-34s " % k + "  ".join("N=%-3d %6.3f" % (n, e) for n, e in zip(NS, v)))
    cs, cm, cn = (curves[k] for k in curves)
    check(cs[-1] / cs[0] > 0.85, "静止した部品は 100 枚平均しても下がらない",
          "%.3f → %.3f µm(%.2f 倍)" % (cs[0], cs[-1], cs[-1] / cs[0]))
    check(abs(cm[-1] / cm[0] * 10 - 1) < 0.35, "部品を動かすと 1/√N(100 枚で 1/10)",
          "%.3f → %.3f µm(%.3f 倍)" % (cm[0], cm[-1], cm[-1] / cm[0]))
    check(abs(cn[-1] / cn[0] * 10 - 1) < 0.35, "加法雑音の世界では静止のまま 1/√N で下がる(誤った安心)",
          "%.3f → %.3f µm" % (cn[0], cn[-1]))

    # ---- 4. 開口と角度 ------------------------------------------------------- #
    print("\n[4] 開口 sin u と三角測量角 θ を振る(光条の幅と同じ長さの束で重心 = スポット相当)")
    P4, S4, NC4, NI4 = 3.0, 4, 1536, 10         # 細格子 0.75 µm(最小の粒 3.3 µm に 4 点以上)
    W4 = 48.0
    block = int(W4 / P4)                         # 12 列 = 48 µm
    ny4 = 64

    def floor_err(sin_u, deg, nimg=NI4):
        e = []
        for k in range(nimg):
            h = float(np.random.default_rng(300 + k).uniform(-15, 15))
            img = laser(NC4, 500 + k, h, sin_u=sin_u, deg=deg, noise=0.0, ny=ny4, pix=P4,
                        oversample=S4, width=W4)
            e.append((block_centroid(img, block) - truth_row(h, ny4, deg, P4)) * P4 / sin_t(deg))
        e = np.concatenate(e)
        return float(np.sqrt(np.mean(e * e)))

    us = np.array([0.035, 0.05, 0.07, 0.1])
    eu = np.array([floor_err(u, THETA_DEG) for u in us])
    du = np.array([fs.ledger.triangulation_speckle_limit(WAVE_UM, u, sin_t(), 1.0)["delta_z_um"] for u in us])
    degs = np.array([15.0, 22.5, 30.0, 45.0, 60.0])
    et = np.array([floor_err(0.05, d, nimg=4) for d in degs])
    dt = np.array([fs.ledger.triangulation_speckle_limit(WAVE_UM, 0.05, sin_t(d), 1.0)["delta_z_um"]
                   for d in degs])
    su_slope = float(np.polyfit(np.log(us), np.log(eu), 1)[0])
    th_slope = float(np.polyfit(np.log(np.sin(np.radians(degs))), np.log(et), 1)[0])
    kappa = np.r_[eu / du, et / dt]
    for u, e, d in zip(us, eu, du):
        print("  sin u = %.3f: 実測 %6.2f µm   式 %6.2f µm   比 %.2f" % (u, e, d, e / d))
    for g, e, d in zip(degs, et, dt):
        print("  θ = %4.1f°:     実測 %6.2f µm   式 %6.2f µm   比 %.2f" % (g, e, d, e / d))
    check(abs(su_slope + 1) < 0.1, "誤差 ∝ 1/sin u(log-log の傾き −1)", "傾き %.3f" % su_slope)
    check(abs(th_slope + 1) < 0.1, "誤差 ∝ 1/sin θ(log-log の傾き −1)", "傾き %.3f" % th_slope)
    check(0.6 < kappa.min() and kappa.max() < 1.4, "桁は Dorsch の式どおり(比例定数は開示のみ)",
          "実測 / 式 = %.2f〜%.2f" % (kappa.min(), kappa.max()))

    # ---- 5. 画素の大きさ ------------------------------------------------------ #
    print("\n[5] 画素を 2 倍・4 倍にする(同じ細格子・同じスペックル)")
    kw = dict(seed=42, noise=0.0, width=LINE_W_UM)
    ref = None
    for f in (1, 2, 4):
        ny5 = 96 // f                            # 96 / 48 / 24 行 = 同じ 240 µm
        img = laser(1024 // f, height=6.0, ny=ny5, pix=2.5 * f, oversample=4 * f, **kw)
        tr5 = truth_row(6.0, ny5, THETA_DEG, 2.5 * f)
        yc = (block_centroid(img, 16 // f) - tr5) * 2.5 * f
        cvis = contrast(img, tr5)
        if ref is None:
            ref = yc
        diff = float(np.max(np.abs(yc - ref)))
        print("  画素 %4.1f µm: 光条の芯の見た目のコントラスト %.3f、重心のずれ RMS(観察面)%.4f µm、"
              "画素 2.5 µm との差 %.1e µm" % (2.5 * f, cvis, float(np.sqrt(np.mean(yc ** 2))), diff))
        if f == 4:
            check(diff < 1e-9 and cvis < 0.9,
                  "画素を 4 倍にすると見た目の粒は鈍るが、重心は 1e-9 µm も動かない",
                  "コントラスト %.2f、差 %.1e µm" % (cvis, diff))

    elapsed = time.time() - t0
    check(elapsed < 60.0, "所要時間(CI の上限に余裕を残す)", "%.1f 秒" % elapsed)

    if figs.enabled():
        _figures(imgs_s, imgs_c, res, NS, curves, us, eu, du, degs, et, dt, su_slope, th_slope)
    assert not figs.errors(), figs.errors()

    bad = [c for c in CHECKS if not c[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(CHECKS), len(CHECKS) - len(bad), elapsed))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


def _figures(imgs_s, imgs_c, res, NS, curves, us, eu, du, degs, et, dt, su_slope, th_slope):
    def zoom(img, k=5):
        """中央 ±10 行 × 120 列(物体側 105 µm × 600 µm)を k 倍に(最近傍 = 画素がそのまま見える)。"""
        c = (NY - 1) // 2
        return np.kron(img[c - 10: c + 11, :120], np.ones((k, k)))

    sharp = laser(120, 10, 0.0, sin_u=0.07, noise=0.0)
    calm = laser(120, 10, 0.0, n_patterns=8, polarizations=2, noise=0.0)
    panels = [zoom(imgs_s[0]), zoom(imgs_c[0]), zoom(sharp), zoom(calm)]
    caps = ["なめらかな光条 + 雑音(前作の世界)", "レーザー(sin u = %.2f): 粒 %.0f µm" % (SIN_U, 0.5145 * WAVE_UM / SIN_U),
            "開口を開ける(sin u = 0.07): 粒 %.0f µm" % (0.5145 * WAVE_UM / 0.07),
            "偏光 2 × 独立 8 枚の和(C = 1/4)"]
    figs.save_grid("line", panels, caps, title="同じ光条、光がコヒーレントになるだけで粒々になる",
                   ncols=1, gray=True, vrange=(0.0, 1.6),
                   caption="1 画素 = 物体側 %.0f µm、横 120 列 = 0.6 mm を 5 倍に拡大。粒の大きさは "
                           "0.51 λ/sin u で決まり、開口を開けると細かく、独立なパターンを足すと滑らかになる。"
                           "部品が止まっている限り、この粒は毎フレーム同じ場所にある。" % PIX_UM)
    names = [n for n, _ in ESTIMATORS]
    rows = [[n, "%.3f" % res[n][0], "%.2f" % res[n][1], "%.0f 倍" % (res[n][1] / res[n][0])] for n in names]
    figs.save_table("estimators", ["推定器", "加法雑音 [µm]", "スペックル [µm]", "悪化"], rows,
                    title="光条の中心の推定器: 順位が入れ替わる",
                    caption="列ごとの高さの RMS 誤差。加法雑音で最良の 3 点当てはめは、スペックルでは"
                            "いちばん明るい粒を追う。光条全体を平均する重心だけが床に着く。")
    ser, cols, sty = [], [], []
    for (k, v), col in zip(curves.items(), ("wrong", "emphasis", "neutral")):
        ser.append((k, np.log10(NS), np.log10(v)))
        cols.append(col)
        sty.append(None)
    v0 = list(curves.values())[1][0]
    ser.append(("1/√N", np.log10(NS), np.log10(v0 / np.sqrt(NS))))
    cols.append("reference")
    sty.append("dashed")
    figs.save_plot("frames", ser, xlabel="log10 平均したフレーム数 N", ylabel="log10 高さの RMS [µm]",
                   title="静止したスペックルは平均で消えない", colors=cols, styles=sty, size=(720, 440),
                   caption="部品が止まっていれば 100 枚平均しても誤差はそのまま。部品を動かすと 1/√N。"
                           "加法雑音のモデルは静止のまま下がると言ってしまう。")
    ser = [("実測(θ = 30°、sin u を振る)", np.log10(us), np.log10(eu)),
           ("Dorsch の式 C·λ/(2π sin u sin θ)", np.log10(us), np.log10(du))]
    figs.save_plot("aperture", ser, xlabel="log10 観察開口 sin u", ylabel="log10 高さの誤差 [µm]",
                   title="開口を開けるほど床は下がる(傾き %.2f)" % su_slope, kinds=["scatter", "line"],
                   colors=["emphasis", "reference"], styles=[None, "dashed"], size=(640, 420),
                   caption="光条の幅と同じ長さ(48 µm)の束ごとの重心。実測 / 式 = %.2f〜%.2f。"
                           % ((eu / du).min(), (eu / du).max()))
    st = np.sin(np.radians(degs))
    ser = [("実測(sin u = 0.05、θ を振る)", np.log10(st), np.log10(et)),
           ("Dorsch の式", np.log10(st), np.log10(dt))]
    figs.save_plot("angle", ser, xlabel="log10 sin θ", ylabel="log10 高さの誤差 [µm]",
                   title="三角測量角を開けるほど床は下がる(傾き %.2f)" % th_slope, kinds=["scatter", "line"],
                   colors=["emphasis", "reference"], styles=[None, "dashed"], size=(640, 420),
                   caption="θ = 15°〜60°。前縮み(光条の見かけの幅が cos θ 倍)はこの描画に入っていない。")


if __name__ == "__main__":
    main()
