# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 水と透明媒質 ―― 海の波・水面の屈折・水中の色・瓶の焦線を、閉形式と公表値と第 2 実装で採点する。

【問い】水は、上から見れば動くレンズ、下から見れば距離で濃くなる色フィルタ。プールの底の模様はなぜ揺れ、水中の赤はなぜ先に消え、
水の入った瓶はなぜ一本の明るい線を作るのか。新 op 10 本(`watermedia`、`opsoptics` の `watermedia`)に切り出し、4 つの場面を同じ関数で示す。

  1. **海**: 風速 8 m/s の Pierson–Moskowitz(1964)の海を Tessendorf(2001)の FFT で作る。門: 有義波高が 0.21 U²/g に 2 % 以内、
     ピーク角周波数が 0.877 g/U に 1e-3 以内、JONSWAP(γ = 1)が PM に 1e-9 で一致、実数、空間の分散がスペクトルの積分に 3 % 以内(8 種)、
     単一モードの周期が 2π/ω、傾きの分散は Cox & Munk(1954)の 0.003 + 0.00512 U と比べる(PM は毛管波を持たないので届かない ――
     届く範囲と届かない範囲を数字で示す)。
  2. **プールの底**: 2 m の底の市松模様を平らな水面と波のある水面越しに見る。門: 真上からの見かけの深さが d/n に 1e-9、見つけた経路が
     スネルの式を 1e-9 で満たす、鏡像対称、水上の点は不変、平面は 4 次方程式(第 2 実装)と光路長の直接最小化(第 3 実装)に一致、
     波面ではベクトルのスネルの式と、カメラからの逆向きの光線追跡(画素を作る経路)が同じ底の点に戻る。水中から見上げるとスネルの窓は 48.6°。
  3. **瓶**: 水を入れた円柱(n ≈ 1.52 のガラス、n_fill = 1.333)は近軸焦点を持ち、実光線は球面収差で手前に焦線を作る。空の瓶は光を曲げない
     ので、液面の高さで明るい線が現れる。門: 近軸焦点が閉形式 n R / (2 (n − 1)) と 1e-9、実光線の焦点が弦の三角関数(第 2 実装)と 1e-9、
     周縁光線の焦点が近軸より短い、空の瓶の屈折力が水入りの 1/10 未満。
  4. **潜水夫の見る色**: 同じ色票を深さ 1・5・15 m で、ジャーロフの I 型(外洋)と 3C 型(沿岸)で。門: Pope & Fry(1997)の吸収の最小 417.5 nm で
     0.00442 /m、700 nm で 0.624 /m、Beer–Lambert が glassmirror と 1e-12、光子の数え上げ(モンテカルロ)が指数則に統計誤差の内、距離 0 で入力に戻る、
     I 型で赤の減衰が青の約 12 倍。
  5. **限界(モデルが外れる所)**: 平らな界面の見かけの深さ d/n は斜めに見るほど外れる(60° で 52 %)。PM の波は毛管波を持たず、飽和域を毛管波数まで延ばしても 10 m/s の傾きは
     Cox & Munk の 6 割しか出ない。Kd を視線に沿った減衰として使うのは近似。
  6. **壊して確かめる**: 屈折率を 1.4 に、PM の α を 10 % 変える、スネルの式の向きを逆にする → 門が赤になる。

【外部真値】Brewster 角・臨界角・R(0) = ((n−1)/(n+1))²・視深度 d/n・円柱の焦点距離 n R / (2 (n−1)) の閉形式、PM の有義波高の閉形式、
Pope & Fry(1997)/ Smith & Baker(1981)/ Solonenko & Mobley(2015)/ Petzold(1972)の公表値、Cox & Munk(1954)の実測式、
フェルマーの原理を直接最小化した第 2 実装、光子のモンテカルロ。手法: Tessendorf, Simulating Ocean Water(2001)/ Akkaynak & Treibitz, CVPR 2018。【学習】0。【較正】0。

★正直な限界: PM の波は毛管波を持たないので、格子で解ける波の傾きは Cox & Munk の 1 割ほど(波数 370 /m まで飽和域を延ばせば 5 m/s では合うが
10 m/s では 4 割届かない)。見かけの深さの d/n は真上の近傍だけ。Kd を視線の減衰に使うのは近似で、実際は距離と深さで変わる(Akkaynak & Treibitz 2018)。
水の吸収は 380〜727.5 nm、ジャーロフの表は 400〜700 nm(3C は 650 nm、5C は 575 nm まで)で、外は拒否する。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import glassmirror as GM  # noqa: E402
import watermedia as WM  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
G = WM.G


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# 1. 海                                                                         #
# --------------------------------------------------------------------------- #
def chapter_ocean():
    print("\n1. 海(Pierson–Moskowitz と Tessendorf の FFT)")
    U = 8.0
    sp = WM.ocean_spectrum(U)
    rule = 0.21 * U * U / G
    wp_rule = 0.877 * G / U
    print("   U = 8 m/s: Hs = %.4f m(0.21 U²/g = %.4f)、Tp = %.2f s、ω_p = %.4f rad/s(0.877 g/U = %.4f)" % (
        sp["hs_m"], rule, sp["tp_s"], sp["omega_peak"], wp_rule))
    gate("有義波高は 0.21 U²/g に 2 % 以内、ピークは 0.877 g/U に 1e-3 以内",
         abs(sp["hs_m"] / rule - 1) < 0.02 and abs(sp["omega_peak"] / wp_rule - 1) < 1e-3,
         "%.2f %% / %.1e" % (100 * abs(sp["hs_m"] / rule - 1), abs(sp["omega_peak"] / wp_rule - 1)))
    jn = WM.ocean_spectrum(U, kind="jonswap", gamma=1.0)
    d_pm = float(np.abs(jn["S"] - sp["S"]).max() / sp["S"].max())
    gate("JONSWAP(γ = 1)は PM と 1e-9 で一致", d_pm < 1e-9, "%.1e" % d_pm)
    j33 = WM.ocean_spectrum(U, kind="jonswap")
    print("   JONSWAP(γ = 3.3): ピークの S は PM の %.2f 倍、Hs = %.3f m" % (j33["S"].max() / sp["S"].max(), j33["hs_m"]))
    NUMBERS.update({"hs_8": sp["hs_m"], "tp_8": sp["tp_s"]})
    n, L = 256, 300.0
    seeds = range(8)
    fields = [WM.ocean_height_field(n, L, U, 0.0, seed=s) for s in seeds]
    f0 = fields[0]
    var_meas = float(np.mean([f["height"].var() for f in fields]))
    gate("高さは実数(虚部 1e-12 以内)", max(f["imag_residual"] for f in fields) <= 1e-12,
         "%.1e" % max(f["imag_residual"] for f in fields))
    gate("空間の分散がスペクトルの積分に 3 % 以内(8 種の平均)", len(fields) == 8 and abs(var_meas / f0["variance_expected_m2"] - 1) < 0.03,
         "実測 %.4f m²、積分 %.4f m²(%.2f %%)" % (var_meas, f0["variance_expected_m2"], 100 * abs(var_meas / f0["variance_expected_m2"] - 1)))
    sl_meas = float(np.mean([(f["slope_x"] ** 2 + f["slope_y"] ** 2).mean() for f in fields]))
    cm = f0["cox_munk_slope_variance"]
    print("   傾きの分散(U = 8): 格子で解ける波 %.4f、スペクトルの積分 %.4f、毛管波数 370 /m まで飽和域を延ばすと %.4f、Cox & Munk %.4f" % (
        sl_meas, f0["slope_variance_expected"], f0["slope_variance_with_tail"], cm))
    gate("場の傾きの分散がスペクトルの積分に 3 % 以内", abs(sl_meas / f0["slope_variance_expected"] - 1) < 0.03,
         "%.2f %%" % (100 * abs(sl_meas / f0["slope_variance_expected"] - 1)))
    res = {}
    for uu in (5.0, 10.0):
        ff = WM.ocean_height_field(n, 1000.0, uu, 0.0, seed=0)
        res[uu] = (ff["slope_variance_expected"], ff["slope_variance_with_tail"], ff["cox_munk_slope_variance"])
        print("   U = %4.1f: 解ける波 %.4f(Cox & Munk の %.0f %%)、飽和域を延ばして %.4f(%.0f %%)、Cox & Munk %.4f" % (
            uu, res[uu][0], 100 * res[uu][0] / res[uu][2], res[uu][1], 100 * res[uu][1] / res[uu][2], res[uu][2]))
    gate("U = 5 m/s: 飽和域を毛管波数まで延ばすと Cox & Munk に 25 % 以内", abs(res[5.0][1] / res[5.0][2] - 1) < 0.25,
         "%.1f %%" % (100 * (res[5.0][1] / res[5.0][2] - 1)))
    gate("U = 10 m/s: 同じやり方は 4 割ほど届かない(PM の α は風速で増えない ―― 限界として記録)", 0.45 < res[10.0][1] / res[10.0][2] < 0.8,
         "%.1f %%" % (100 * (res[10.0][1] / res[10.0][2] - 1)))
    gate("格子で解ける波だけの傾きは Cox & Munk の 2 割未満(毛管波が無いため)", res[5.0][0] / res[5.0][2] < 0.2 and res[10.0][0] / res[10.0][2] < 0.2)
    NUMBERS.update({"cm_5_tail": res[5.0][1] / res[5.0][2], "cm_10_tail": res[10.0][1] / res[10.0][2],
                    "cm_5_resolved": res[5.0][0] / res[5.0][2], "cm_10_resolved": res[10.0][0] / res[10.0][2]})
    # 単一モードの周期
    A = 0.3
    m0 = WM.ocean_height_field(32, 100.0, U, 0.0, single_mode=(2, 1, A))
    T = 2 * math.pi / m0["omega_mode"]
    mT = WM.ocean_height_field(32, 100.0, U, 0.0, t=T, single_mode=(2, 1, A))
    e_T = float(np.abs(mT["height"] - m0["height"]).max() / A)
    gate("単一モードの周期は 2π/ω(1e-6 以内)", e_T < 1e-6, "T = %.4f s、残差 %.1e" % (T, e_T))
    a1 = WM.ocean_height_field(64, 200.0, U, 30.0, t=1.5, seed=3)
    a2 = WM.ocean_height_field(64, 200.0, U, 30.0, t=1.5, seed=3)
    gate("同じ種・同じ時刻は同一、荒れ 0 は変位が厳密に 0",
         np.array_equal(a1["height"], a2["height"]) and not a1["displacement_x"].any() and not a1["displacement_y"].any())
    return f0, fields, res


# --------------------------------------------------------------------------- #
# 2. プールの底                                                                  #
# --------------------------------------------------------------------------- #
POOL_DEPTH = 2.0
POOL_SEA_N = 32                      # 6 m の窓に 19 cm の格子: 波長 40 cm より長い波だけ(板の上の穏やかなさざ波)
N_W = 4.0 / 3.0


def checker(x, y, cell=0.10):
    """市松模様(赤みと青みを少し付けて、色の分離も見える)。"""
    ix = np.floor(x / cell).astype(int)
    iy = np.floor(y / cell).astype(int)
    on = ((ix + iy) % 2) == 0
    base = np.where(on, 0.88, 0.16)
    tint = np.where((np.floor(x / (4 * cell)).astype(int) + np.floor(y / (4 * cell)).astype(int)) % 2 == 0, 1.0, 0.0)
    return np.stack([base * (0.80 + 0.20 * tint), base * 0.90, base * (1.0 - 0.20 * tint)], axis=-1)


class SeaLookup:
    """海の高さと勾配を連続座標で引く(周期タイル。3 次補間)。"""

    def __init__(self, f):
        from scipy.ndimage import map_coordinates
        self._mc = map_coordinates
        self.h, self.sx, self.sy = f["height"], f["slope_x"], f["slope_y"]
        self.n, self.L = self.h.shape[0], f["extent_m"]

    def _c(self, a, x, y):
        u, v = np.mod(x, self.L) / self.L * self.n, np.mod(y, self.L) / self.L * self.n
        return self._mc(a, [v.ravel(), u.ravel()], order=3, mode="grid-wrap").reshape(x.shape)

    def height(self, x, y):
        return self._c(self.h, x, y)

    def slopes(self, x, y, eps=1e-4):
        """勾配は高さの 3 次補間の中心差分(op の使う高さの双 3 次スプラインの微分とは別の経路)。"""
        return ((self.height(x + eps, y) - self.height(x - eps, y)) / (2 * eps),
                (self.height(x, y + eps) - self.height(x, y - eps)) / (2 * eps))


def _box(a, ss):
    """ss x ss の箱で平均して縮める(エイリアシングを抑える超サンプリング)。"""
    if ss == 1:
        return a
    h, w = a.shape[0] // ss, a.shape[1] // ss
    return a[:h * ss, :w * ss].reshape(h, ss, w, ss, *a.shape[2:]).mean(axis=(1, 3))


def render_down(cam_h, fov_deg, npx, sea=None, ss=1):
    """真上のカメラから見たプールの底(平らな水 / 波のある水)。カメラからの逆向きの光線追跡で画素を作る。"""
    if ss > 1:
        img, p, q, nrm = render_down(cam_h, fov_deg, npx * ss, sea, 1)
        return _box(img, ss), _box(p, ss), _box(q, ss), _box(nrm, ss)
    half = math.tan(math.radians(fov_deg / 2))
    u = (np.arange(npx) + 0.5) / npx * 2 - 1
    X, Y = np.meshgrid(u * half, u * half)
    d = np.stack([X, Y, -np.ones_like(X)], axis=-1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    o = np.array([3.0, 3.0, cam_h])
    t = (0.0 - o[2]) / d[..., 2]
    p = o + t[..., None] * d
    nrm = np.zeros_like(d)
    nrm[..., 2] = 1.0
    if sea is not None:
        for _ in range(8):
            z = sea.height(p[..., 0], p[..., 1])
            t = (z - o[2]) / d[..., 2]
            p = o + t[..., None] * d
        sx, sy = sea.slopes(p[..., 0], p[..., 1])
        nrm = np.stack([-sx, -sy, np.ones_like(sx)], axis=-1)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    r, tir = GM.refract_rays(d, nrm, 1.0, N_W)
    tb = (-POOL_DEPTH - p[..., 2]) / r[..., 2]
    q = p + tb[..., None] * r
    return checker(q[..., 0], q[..., 1]), p, q, nrm


def render_up(npx, depth_cam=1.0, ss=1):
    """水中から見上げる魚眼(等距離射影、天頂 = 中心、端 = 水平)。窓の外は全反射で底が鏡に映る。"""
    if ss > 1:
        img, tir, rad, th = render_up(npx * ss, depth_cam, 1)
        # 全反射の旗は超サンプルの解像度のまま縮める(過半数)
        return _box(img, ss), _box(tir.astype(float), ss) > 0.5, _box(rad, ss), _box(th, ss)
    u = (np.arange(npx) + 0.5) / npx * 2 - 1
    X, Y = np.meshgrid(u, u)
    rad = np.hypot(X, Y)
    th = rad * (math.pi / 2)                          # 天頂角
    ph = np.arctan2(Y, X)
    inside = rad <= 1.0
    st, ct = np.sin(th), np.cos(th)
    ct_safe = np.where(ct > 1e-6, ct, 1e-6)
    deg = np.degrees(th)
    fr = WM.fresnel_water_air(np.clip(deg, 0, 90), 0.55, "unpolarized", "water_to_air", n_water=N_W)
    tir = fr["tir"]
    x0 = depth_cam * np.tan(th) * np.cos(ph)
    y0 = depth_cam * np.tan(th) * np.sin(ph)
    tt = (POOL_DEPTH - 0.0) / ct_safe                 # 反射後に底へ(水面から底まで POOL_DEPTH)
    bot = checker(x0 + tt * st * np.cos(ph), y0 + tt * st * np.sin(ph))
    out_ang = np.arcsin(np.clip(N_W * st, 0, 1))
    sky = np.stack([0.30 + 0.35 * np.cos(out_ang), 0.52 + 0.33 * np.cos(out_ang), 0.95 + 0.0 * out_ang], axis=-1)
    R = fr["R"][..., None]
    img = (1 - R) * sky + R * bot * np.array([0.55, 0.75, 0.9])
    img = np.where(inside[..., None], img, 0.0)
    return img, tir & inside, rad, th


def chapter_pool():
    print("\n2. プールの底の市松模様(平らな水 / 波のある水)と水中からのスネルの窓")
    npx = 120 if REDUCED else 480
    ss = 1 if REDUCED else 3
    flat, p_f, q_f, _ = render_down(4.0, 50.0, npx, None, ss)
    sea = WM.ocean_height_field(POOL_SEA_N, 6.0, 8.0, 0.0, seed=5)
    wavy, p_w, q_w, nrm_w = render_down(4.0, 50.0, npx, SeaLookup(sea), ss)
    print("   水面の傾き(6 m の窓): 標準偏差 %.3f 、画像の最大のずれ %.3f" % (
        float(np.std(sea["slope_x"])), float(np.abs(wavy - flat).max())))
    # --- refracted_view の門
    n = N_W
    P = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, -2.5], [0.0, 0.0, -0.1]])
    r0 = WM.refracted_view(P, np.array([0.0, 0.0, 4.0]), n_water=n)
    e_dn = float(np.abs(r0["apparent_depth_m"] - np.array([1.0, 2.5, 0.1]) / n).max())
    gate("真上から見た見かけの深さは d / n に 1e-9 以内", e_dn < 1e-9, "%.1e" % e_dn)
    rng = np.random.default_rng(5)
    Q = np.column_stack([rng.uniform(-2, 2, 60), rng.uniform(-2, 2, 60), -rng.uniform(0.2, 3.0, 60)])
    E = np.array([0.7, -0.4, 4.0])
    rv = WM.refracted_view(Q, E, n_water=n)
    R = rv["refraction_point"]
    dw, da = R - Q, E[None, :] - R
    sw = np.hypot(dw[:, 0], dw[:, 1]) / np.linalg.norm(dw, axis=1)
    sa = np.hypot(da[:, 0], da[:, 1]) / np.linalg.norm(da, axis=1)
    e_sn = float(np.abs(n * sw - sa).max())
    gate("見つけた経路がスネルの式(sin の比)を 1e-9 以内で満たす(幾何から再計算)", rv["converged"].all() and e_sn < 1e-9, "%.1e" % e_sn)
    Pm = np.array([[1.2, 0.5, -1.5], [-1.2, 0.5, -1.5]])
    am = WM.refracted_view(Pm, np.array([0.0, 0.0, 3.0]), n_water=n)["apparent"]
    e_mir = float(np.abs(am[0] * np.array([-1, 1, 1]) - am[1]).max())
    gate("鏡に映した配置は見かけの位置も鏡像(1e-9 以内)", e_mir < 1e-9, "%.1e" % e_mir)
    Pa = np.array([[1.0, 2.0, 0.0], [0.0, 0.0, 5.0]])
    gate("水上の点はそのまま返る", np.array_equal(WM.refracted_view(Pa, E, n_water=n)["apparent"], Pa))
    # 第 2 実装: 4 次方程式 / 第 3 実装: 光路長の直接最小化
    from scipy.optimize import minimize_scalar
    worst_q, worst_m = 0.0, 0.0
    for i in range(0, 60, 6):
        s = math.hypot(E[0] - Q[i, 0], E[1] - Q[i, 1])
        d_, h_ = -Q[i, 2], E[2]
        pol = (np.polynomial.Polynomial([0, 0, 1]) * np.polynomial.Polynomial([s, -1]) ** 2 * (n * n - 1)
               + np.polynomial.Polynomial([0, 0, n * n * h_ * h_]) + np.polynomial.Polynomial([s, -1]) ** 2 * (-d_ * d_))
        xs = [z.real for z in pol.roots() if abs(z.imag) < 1e-9 and 0 < z.real < s]
        x_op = math.hypot(R[i, 0] - Q[i, 0], R[i, 1] - Q[i, 1])
        worst_q = max(worst_q, abs(xs[0] - x_op))
        res = minimize_scalar(lambda x: n * math.hypot(x, d_) + math.hypot(s - x, h_), bounds=(0, s), method="bounded", options={"xatol": 1e-13})
        worst_m = max(worst_m, abs(res.x - x_op))
    gate("平面の屈折点は 4 次方程式(第 2 実装)に 1e-9、光路長の直接最小化(第 3 実装)に 1e-6 以内", worst_q < 1e-9 and worst_m < 1e-6,
         "%.1e / %.1e" % (worst_q, worst_m))
    # 波面: ベクトルのスネルの式と、カメラからの逆向きの光線追跡が同じ底の点に戻る
    lk = SeaLookup(sea)
    P2 = np.column_stack([rng.uniform(2.4, 3.6, 12), rng.uniform(2.4, 3.6, 12), -POOL_DEPTH * np.ones(12)])
    cam = np.array([3.0, 3.0, 4.0])
    rw = WM.refracted_view(P2, cam, surface=sea, n_water=n)
    ok_w = rw["converged"].all()
    back = []
    for i in range(12):
        Rp = rw["refraction_point"][i]
        dcam = (Rp - cam) / np.linalg.norm(Rp - cam)
        sx_, sy_ = lk.slopes(np.array([Rp[0]]), np.array([Rp[1]]))
        N_ = np.array([-sx_[0], -sy_[0], 1.0])
        N_ /= np.linalg.norm(N_)
        rr, _ = GM.refract_rays(dcam[None, :], N_[None, :], 1.0, n)
        tt = (-POOL_DEPTH - Rp[2]) / rr[0, 2]
        back.append(np.linalg.norm(Rp + tt * rr[0] - P2[i]))
    e_back = float(max(back))
    print("   波面: 12 点の屈折点を求め、カメラから屈折点を通る光線を追って底へ戻すと、元の点との距離の最大 %.1e m" % e_back)
    gate("波面の経路は、カメラから逆向きに追う光線(画像を作る経路)で同じ底の点に戻る(5e-6 m 以内)", ok_w and e_back < 5e-6, "%.1e m" % e_back)
    gate("波面の屈折は平面と違う(見かけの位置が 1 mm 以上ずれる)",
         float(np.abs(rw["apparent"] - WM.refracted_view(P2, cam, n_water=n)["apparent"]).max()) > 1e-3)
    # --- スネルの窓
    npx_up = 120 if REDUCED else 480
    up, tir, rad, th = render_up(npx_up, 1.0, 1 if REDUCED else 2)
    row = tir[npx_up // 2, npx_up // 2:]
    first = int(np.argmax(row))
    th_b = math.degrees(th[npx_up // 2, npx_up // 2 + first])
    swin = WM.snell_window(1.0, n_water=n)
    tol = 90.0 / (npx_up / 2) + 1e-9                  # 画素 1 つぶんの角度
    print("   見上げた魚眼で全反射が始まる角 %.2f°(閉形式 %.2f°)、窓の半径(深さ 1 m)%.3f m" % (th_b, swin["critical_deg"], swin["window_radius_m"][()] if hasattr(swin["window_radius_m"], "shape") else swin["window_radius_m"]))
    gate("水中から見上げて全反射が始まる角は臨界角 48.6° の直後 1 画素(%.2f°)以内" % tol, 0.0 <= th_b - swin["critical_deg"] < tol, "%.2f°" % th_b)
    gate("窓の半径 = 深さ × tan(臨界角)(1e-12)", abs(float(np.squeeze(swin["window_radius_m"])) - 1.0 * math.tan(math.asin(1 / n))) < 1e-12)
    NUMBERS.update({"snell_deg": swin["critical_deg"], "apparent_depth_err": e_dn, "back_trace_err": e_back})
    return flat, wavy, up, swin, sea, q_f, q_w


# --------------------------------------------------------------------------- #
# 3. 瓶                                                                         #
# --------------------------------------------------------------------------- #
def chapter_bottle():
    print("\n3. 水の入った瓶(円柱レンズ)と、空の瓶")
    R, ng, nf, t = 30.0, 1.52, 1.333, 1.5
    sol = WM.cylinder_lens_caustic(20.0, 1.5)
    f_cf = 1.5 * 20.0 / (2 * 0.5)
    gate("棒の近軸焦点は n R / (2 (n − 1)) に 1e-9", abs(sol["efl_mm"] - f_cf) < 1e-9 * f_cf and abs(sol["paraxial_focus_mm"] - f_cf) < 1e-9 * f_cf,
         "%.1e" % abs(sol["efl_mm"] - f_cf))
    y = sol["heights_mm"]
    i = np.arcsin(y / 20.0)
    rr = np.arcsin(np.sin(i) / 1.5)
    e1 = np.stack([-20.0 * np.cos(i), y], 1)
    e2 = e1 + (2 * 20.0 * np.cos(rr))[:, None] * np.stack([np.cos(i - rr), -np.sin(i - rr)], 1)
    zf = e2[:, 0] + e2[:, 1] / np.tan(2 * (i - rr))
    ok = np.isfinite(sol["focus_z_mm"])
    e_tr = float(np.abs(zf[ok] - sol["focus_z_mm"][ok]).max())
    gate("実光線の焦点は弦の三角関数(第 2 実装)と 1e-9", e_tr < 1e-9, "%.1e" % e_tr)
    full = WM.cylinder_lens_caustic(R, ng, nf, t)
    empty = WM.cylinder_lens_caustic(R, ng, 1.0, t)
    f_thin = nf * R / (2 * (nf - 1))
    print("   水入り(R = 30 mm、ガラス n = 1.52、壁 1.5 mm、水 1.333): 近軸焦点(軸から)%.2f mm、周縁光線 %.2f mm(球面収差 %.2f mm)、薄肉の閉形式 %.2f mm" % (
        full["paraxial_focus_mm"], full["marginal_focus_mm"], full["longitudinal_aberration_mm"], f_thin))
    print("   屈折力: 水入り %.5f /mm、空 %.5f /mm(比 %.1f)" % (full["power_per_mm"], empty["power_per_mm"], abs(full["power_per_mm"] / empty["power_per_mm"])))
    gate("周縁光線の焦点は近軸より短い(正の球面収差)", full["marginal_focus_mm"] < full["paraxial_focus_mm"],
         "%.2f mm < %.2f mm" % (full["marginal_focus_mm"], full["paraxial_focus_mm"]))
    gate("空の瓶の屈折力は水入りの 1/10 未満(比 > 10)", abs(full["power_per_mm"] / empty["power_per_mm"]) > 10.0)
    thin = WM.cylinder_lens_caustic(R, ng, nf, 1e-6)
    gate("壁を薄くすると 2 界面の閉形式 n_fill R / (2 (n_fill − 1)) に収束(1e-6)", abs(thin["efl_mm"] / f_thin - 1) < 1e-6,
         "%.1e" % abs(thin["efl_mm"] / f_thin - 1))
    # --- 液面の検査: 背後の面での強度
    D = 50.0
    nray = 1500 if REDUCED else 2001
    prof = {}
    for label, b in (("filled", WM.cylinder_lens_caustic(R, ng, nf, t, n_rays=nray)), ("empty", WM.cylinder_lens_caustic(R, ng, 1.0, t, n_rays=nray))):
        yy = b["heights_mm"]
        pz, py, dz, dy = b["paths_z_mm"][:, -1], b["paths_y_mm"][:, -1], b["exit_dir_z"], b["exit_dir_y"]
        ys = py + (D - pz) * dy / dz
        prof[label] = (yy, ys)
    edges = np.linspace(-45.0, 45.0, 181)
    dy_step = prof["filled"][0][1] - prof["filled"][0][0]
    irr = {}
    for label, (yy, ys) in prof.items():
        h_ = np.histogram(np.concatenate([ys, -ys]), bins=edges, weights=np.full(2 * ys.size, dy_step))[0] / (edges[1] - edges[0])
        # 開口の外(壁だけを通る光)はまっすぐ進むと見なして足す
        a = prof[label][0][-1] / 0.95
        out_y = np.concatenate([np.linspace(0.95 * a, R, 40), -np.linspace(0.95 * a, R, 40)])
        h_ += np.histogram(out_y, bins=edges, weights=np.full(out_y.size, (R - 0.95 * a) / 40))[0] / (edges[1] - edges[0])
        irr[label] = h_
    inc = 1.0
    peak_f, peak_e = float(irr["filled"].max() / inc), float(irr["empty"].max() / inc)
    cen = slice(80, 101)
    print("   背後 %.0f mm の面の強度(入射 = 1): 水入りの最大 %.2f(中心 %.2f)、空の最大 %.2f" % (D, peak_f, float(irr["filled"][cen].mean()), peak_e))
    cen_f, cen_e = float(irr["filled"][cen].mean()), float(irr["empty"][cen].mean())
    gate("水のある部分の中心は入射の 3 倍以上の明るい線、空の部分の中心は入射以下(発散して暗い)で、比は 5 倍以上",
         cen_f > 3.0 and cen_e < 1.0 and cen_f / cen_e > 5.0, "%.2f / %.2f(比 %.1f)" % (cen_f, cen_e, cen_f / cen_e))
    NUMBERS.update({"bottle_para": full["paraxial_focus_mm"], "bottle_marg": full["marginal_focus_mm"], "bottle_ratio": abs(full["power_per_mm"] / empty["power_per_mm"]),
                    "rod_marg": sol["marginal_focus_mm"], "peak_f": peak_f})
    return full, empty, irr, edges, D


# --------------------------------------------------------------------------- #
# 4. 潜水夫の見る色                                                               #
# --------------------------------------------------------------------------- #
CHART_NAMES = ["白", "灰", "黒", "赤", "橙", "黄", "黄緑", "緑", "青緑", "水色", "青", "紫"]
CHART = np.array([[0.90, 0.90, 0.90], [0.50, 0.50, 0.50], [0.10, 0.10, 0.10], [0.80, 0.08, 0.06], [0.85, 0.40, 0.06], [0.88, 0.80, 0.08],
                  [0.55, 0.78, 0.10], [0.10, 0.60, 0.12], [0.08, 0.62, 0.55], [0.20, 0.65, 0.88], [0.08, 0.15, 0.80], [0.50, 0.12, 0.60]])


def chart_image(px=40):
    img = np.full((3 * px, 4 * px, 3), 0.35)
    for k in range(12):
        r, c = divmod(k, 4)
        img[r * px + 3:(r + 1) * px - 3, c * px + 3:(c + 1) * px - 3] = CHART[k]
    return img


def chapter_diver():
    print("\n4. 潜水夫の見る色(深さ 1・5・15 m、ジャーロフ I 型と 3C 型)")
    # 公表値
    wl = np.array([x for x, _ in WM._wd.POPE_FRY_1997]) / 1000.0
    pf = WM.water_attenuation(wl, "pure")
    i = int(np.argmin(pf["a"]))
    a700 = float(WM.water_attenuation(0.7, "pure")["a"][0])
    print("   Pope & Fry(1997): 吸収の最小 %.1f nm で %.5f /m、700 nm で %.3f /m" % (wl[i] * 1000, pf["a"][i], a700))
    gate("Pope & Fry の最小は 417.5 nm で 0.00442 /m(表の値)、700 nm で 0.624 /m", abs(wl[i] - 0.4175) < 1e-12 and abs(pf["a"][i] - 0.00442) < 1e-12 and abs(a700 - 0.624) < 1e-12)
    z = np.array([1.0, 5.0, 15.0])
    wls = np.array([0.45, 0.55, 0.65])
    worst = 0.0
    for wt in ("pure", "jerlov_I", "jerlov_3C"):
        r = WM.water_attenuation(wls, wt, depth_m=z)
        for k, zk in enumerate(z):
            ref = GM.beer_lambert_transmittance(zk * 1000.0, r["kd"] / 1000.0)
            worst = max(worst, float(np.abs(r["transmittance"][k] - ref).max()))
    gate("透過率は glassmirror の Beer–Lambert と 1e-12 以内", worst < 1e-12, "%.1e" % worst)
    rng = np.random.default_rng(3)
    a = float(WM.water_attenuation(0.65, "pure")["a"][0])
    nph = 200000 if REDUCED else 1000000
    surv = float(np.mean(-np.log(1.0 - rng.random(nph)) / a > 6.0))
    ex = math.exp(-6.0 * a)
    sig = math.sqrt(ex * (1 - ex) / nph)
    print("   光子 %d 個(吸収のみ、0.65 µm、6 m): 残る割合 %.5f、exp(−a z) = %.5f、統計誤差 %.5f" % (nph, surv, ex, sig))
    gate("光子の数え上げ(モンテカルロ)が指数則に 4σ 以内", abs(surv - ex) < 4 * sig, "%.1f σ" % (abs(surv - ex) / sig))
    kd500 = {t: WM.water_attenuation(0.5, "jerlov_" + t)["kd"][0] for t in ("I", "II", "III", "1C")}
    gate("Kd(500 nm) は I < II < III < 1C", kd500["I"] < kd500["II"] < kd500["III"] < kd500["1C"], " < ".join("%s %.3f" % kv for kv in kd500.items()))
    chart = chart_image()
    out = {}
    for wt in ("jerlov_I", "jerlov_3C"):
        for zz in (1.0, 5.0, 15.0):
            o = WM.underwater_image(chart, zz, 2.0, wt, apply_ambient=True)
            out[(wt, zz)] = o
    o0 = WM.underwater_image(chart, 5.0, 0.0, "jerlov_I")
    gate("距離 0 は入力に戻る(1e-12)", float(np.abs(o0["image"] - chart).max()) < 1e-12)
    nb = WM.underwater_image(chart, 5.0, 7.0, "jerlov_III", backscatter=False)
    kd3 = WM.water_attenuation(list(WM.RGB_WAVELENGTHS_UM), "jerlov_III")["kd"]
    gate("後方散乱を切ると Beer–Lambert だけ(water_attenuation と 1e-12)",
         float(np.abs(nb["image"] - chart * np.exp(-7.0 * kd3)[None, None, :]).max()) < 1e-12)
    ratio = out[("jerlov_I", 1.0)]["red_to_blue_kd_ratio"]
    t10 = WM.underwater_image(chart, 0.0, 10.0, "jerlov_I", backscatter=False)["transmission"][0, 0]
    print("   Jerlov I: 赤 / 青の Kd の比 %.1f、10 m の透過率 赤 %.3f 緑 %.3f 青 %.3f" % (ratio, t10[0], t10[1], t10[2]))
    gate("I 型で赤の減衰は青の 8 倍以上(比 %.1f)" % ratio, ratio > 8.0 and t10[0] < t10[1] < t10[2])
    prev = chart
    mono = True
    for rdist in (1.0, 3.0, 8.0):
        cur = WM.underwater_image(chart, 0.0, rdist, "jerlov_I")["image"]
        mono &= bool((cur < prev).all())
        prev = cur
    gate("距離とともに単調に暗くなる", mono)
    print("   記録された色(赤の票 [0.80 0.08 0.06] と白の票、距離 2 m、深さごと):")
    for wt in ("jerlov_I", "jerlov_3C"):
        for zz in (1.0, 5.0, 15.0):
            im = out[(wt, zz)]["image"]
            # 票 3 = 赤(行 0・列 3)、票 0 = 白(行 0・列 0)
            red = im[20, 3 * 40 + 20]
            wh = im[20, 20]
            print("     %-9s %4.0f m: 赤の票 → (%.3f, %.3f, %.3f)  白の票 → (%.3f, %.3f, %.3f)" % (wt, zz, *red, *wh))
    red15 = out[("jerlov_I", 15.0)]["image"][20, 3 * 40 + 20]
    gate("I 型 15 m では赤の票の R が 3 % 未満に落ち、白の票は青みを帯びる(B が R の 10 倍以上)",
         red15[0] < 0.03 and out[("jerlov_I", 15.0)]["image"][20, 20][2] > 10 * out[("jerlov_I", 15.0)]["image"][20, 20][0])
    NUMBERS.update({"kd_ratio_I": ratio, "red15_R": float(red15[0])})
    return out, chart, pf


# --------------------------------------------------------------------------- #
# 5. 限界                                                                        #
# --------------------------------------------------------------------------- #
def chapter_limits():
    print("\n5. 限界(モデルが外れる所)")
    ang = np.array([0.0, 10, 20, 30, 40, 50, 60, 70, 80, 85])
    sw = WM.snell_window(1.0, n_water=N_W, view_angle_deg=ang)
    err = sw["paraxial_error"]
    print("   見かけの深さの d/n の誤差(角度:誤差): " + "、".join("%d°:%+.1f%%" % (a, 100 * e) for a, e in zip(ang, err)))
    gate("d/n は真上で厳密、30° で 5 % 超、60° で 50 % 超の過大評価(限界)", abs(err[0]) < 1e-12 and err[3] > 0.05 and err[6] > 0.50,
         "30°: %.1f %%、60°: %.1f %%" % (100 * err[3], 100 * err[6]))
    # 平らな界面の見かけの深さを光線の構成で独立に確かめる
    tw = np.arcsin(np.sin(np.radians(ang[1:])) / N_W)
    ref = np.tan(tw) / np.tan(np.radians(ang[1:]))
    gate("角度ごとの見かけの深さは光線の構成(第 2 実装)と 1e-12", float(np.abs(sw["apparent_depth_factor"][1:] - ref).max()) < 1e-12)
    # スペクトルの被覆
    gate("ジャーロフの表の外は拒否(3C の 700 nm、5C の 600 nm、波長 0.3 µm)", all(_refused(lambda a=a, b=b: WM.water_attenuation(a, b))
                                                                             for a, b in ((0.70, "jerlov_3C"), (0.60, "jerlov_5C"), (0.30, "jerlov_II"))))
    pet = {k: WM.scattering_phase_petzold([1.0, 90.0], k) for k in WM.PETZOLD_KINDS}
    ratios = {k: v["phase_per_sr"][0] / v["phase_per_sr"][1] for k, v in pet.items()}
    print("   Petzold の位相関数 p(1°)/p(90°): " + "、".join("%s %.0f" % kv for kv in ratios.items()))
    gate("Petzold: 前方の鋭いピーク(clear で p(1°)/p(90°) > 1e3)", ratios["clear"] > 1e3)
    x, wt = np.polynomial.legendre.leggauss(2000)
    worst = 0.0
    for gg in (-0.9, 0.0, 0.5, 0.9):
        p = WM.phase_function_hg(x, gg)["phase_per_sr"]
        worst = max(worst, abs(2 * np.pi * np.sum(wt * p) - 1), abs(2 * np.pi * np.sum(wt * p * x) - gg))
    gate("Henyey–Greenstein は 4π で 1 に積分され、平均余弦が g(1e-6 以内)", worst < 1e-6, "%.1e" % worst)
    NUMBERS.update({"err30": float(err[3]), "err60": float(err[6]), "pet_clear": float(ratios["clear"])})
    return ang, err


def _refused(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


# --------------------------------------------------------------------------- #
# 6. 壊して確かめる                                                              #
# --------------------------------------------------------------------------- #
def chapter_probes():
    print("\n6. 壊して確かめる(門が赤になる/拒否される)")
    gate("屈折率 1.4 では Brewster 角が 53.12° から外れる(門は赤)", abs(math.degrees(math.atan(1.4)) - 53.12) > 0.5)
    r = WM.ocean_spectrum(10.0)
    bad_hs = 4 * math.sqrt(0.0081 * 1.1 / (4 * 0.74)) * 100 / G
    gate("PM の α を 10 % 変えると有義波高の 2 % の門は赤", abs(bad_hs / r["hs_m"] - 1) > 0.02)
    # スネルの式の向きを逆(n sin = sin を sin = n sin に)にした経路は、見つけた点で式が合わない
    n = N_W
    P = np.array([[0.4, 0.0, -1.0]])
    E = np.array([0.0, 0.0, 3.0])
    R = WM.refracted_view(P, E, n_water=n)["refraction_point"][0]
    dw, da = R - P[0], E - R
    sw = math.hypot(dw[0], dw[1]) / np.linalg.norm(dw)
    sa = math.hypot(da[0], da[1]) / np.linalg.norm(da)
    gate("向きを逆にしたスネルの式 sin_w = n sin_a は同じ点で外れる(門は赤)", abs(sw - n * sa) > 0.05 and abs(n * sw - sa) < 1e-9)
    gate("拒否: 風速 −1・fetch 0・|g| = 1・n ≤ 1・未知の水の種類・負の距離",
         all(_refused(f) for f in (lambda: WM.ocean_spectrum(-1.0), lambda: WM.ocean_spectrum(10.0, 0.0, "jonswap"), lambda: WM.phase_function_hg(0.0, 1.0),
                                   lambda: WM.cylinder_lens_caustic(10.0, 1.0), lambda: WM.water_attenuation(0.5, "jerlov_Z"),
                                   lambda: WM.underwater_image(np.ones((2, 2, 3)), 1.0, -1.0, "jerlov_I"))))


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(ocean, pool, bottle, diver, limits):
    f0, fields, ocres = ocean
    flat, wavy, up, swin, sea, q_f, q_w = pool
    full, empty, irr, edges, D = bottle
    out, chart, pf = diver
    ang, err = limits
    hh = f0["height"]
    nz = f0["normal"]
    light = np.array([0.35, 0.25, 0.90])
    light /= np.linalg.norm(light)
    shade = np.clip(nz @ light, 0.0, 1.0)
    sp8 = WM.ocean_spectrum(8.0)
    figs.save_grid("ocean_field", [hh, shade], captions=["高さ [m]", "同じ海を斜めの光で陰影づけ(法線 · 光の向き)"], ncols=2, signed=[True, False],
                   gray=[False, True], title="風速 8 m/s の海(Pierson–Moskowitz + cos² の方向分布、300 m 四方)",
                   caption="Tessendorf の FFT。有義波高 %.2f m、周期 %.1f s。波は +x(右)へ進む。" % (sp8["hs_m"], sp8["tp_s"]))
    jn8 = WM.ocean_spectrum(8.0, kind="jonswap")
    wm_ = sp8["omega"]
    sel = (wm_ >= 0.4) & (wm_ <= 4.0)
    figs.save_plot("ocean_spectrum", [("Pierson–Moskowitz(完全に発達)", wm_[sel], sp8["S"][sel]), ("JONSWAP γ = 3.3", wm_[sel], jn8["S"][sel])],
                   xlabel="角周波数 ω [rad/s]", ylabel="S(ω) [m² s]", colors=["emphasis", "right"],
                   title="波のスペクトル(8 m/s): ピーク ω_p = %.3f rad/s = 0.877 g/U、Hs = %.2f m" % (sp8["omega_peak"], sp8["hs_m"]),
                   caption="JONSWAP はピークを γ 倍に尖らせる。γ = 1 なら PM と 1e-9 で一致する。")
    # 風下方向の傾きの分布(成分ごとに分散が違うので、方向を分けて比べる)
    sx = np.concatenate([f["slope_x"].ravel() for f in fields])
    edges_s = np.linspace(-0.45, 0.45, 91)
    cnt = np.histogram(sx, bins=edges_s, density=True)[0]
    mid = 0.5 * (edges_s[1:] + edges_s[:-1])
    var_cm_u = 0.00316 * 8.0
    var_r = float(np.mean([f["slope_x"].var() for f in fields]))
    gauss = lambda v: np.exp(-mid ** 2 / (2 * v)) / math.sqrt(2 * math.pi * v)      # noqa: E731
    figs.save_plot("slope_histogram", [("格子で解ける波(8 種、分散 %.4f)" % var_r, mid, cnt), ("同じ分散のガウス分布", mid, gauss(var_r)),
                                       ("Cox & Munk の風下方向(分散 %.4f)" % var_cm_u, mid, gauss(var_cm_u))],
                   xlabel="風下方向の傾き dh/dx", ylabel="確率密度", kinds=["scatter", "line", "line"], styles=[None, "dashed", None],
                   colors=["emphasis", "reference", "wrong"], size=(640, 380),
                   title="海の傾きの分布 ―― 解ける波だけでは Cox & Munk の分散に届かない",
                   caption="PM の波は毛管波を持たず、風下方向の傾きの分散は Cox & Munk(0.00316 U)の %.0f %%。全方向では %.0f %%(飽和域を毛管波数まで延ばすと %.0f %%)。" % (
                       100 * var_r / var_cm_u, 100 * f0["slope_variance_expected"] / f0["cox_munk_slope_variance"],
                       100 * f0["slope_variance_with_tail"] / f0["cox_munk_slope_variance"]))
    shift_cm = 100.0 * np.hypot(q_w[..., 0] - q_f[..., 0], q_w[..., 1] - q_f[..., 1])
    ring = up.copy()
    thc = math.radians(swin["critical_deg"]) / (math.pi / 2)
    yy_, xx_ = np.mgrid[0:up.shape[0], 0:up.shape[1]]
    rr_ = np.hypot((xx_ + 0.5) / up.shape[1] * 2 - 1, (yy_ + 0.5) / up.shape[0] * 2 - 1)
    ring[np.abs(rr_ - thc) < 1.2 / (up.shape[0] / 2)] = [1.0, 0.85, 0.1]
    figs.save_grid("pool_views", [flat, wavy, shift_cm, ring],
                   captions=["平らな水越しの底(10 cm 角)", "波のある水越しの底", "波による底の見える位置のずれ [cm]", "水中(深さ 1 m)から見上げた魚眼"], ncols=2,
                   gray=[False, False, False, False], signed=[False, False, False, False],
                   title="2 m のプールの底の市松模様と、水中から見たスネルの窓",
                   caption="見上げた魚眼の中央が空(窓)、外側は全反射で底が鏡に映る。黄の輪が臨界角 %.1f°(窓の半径は深さ 1 m で %.2f m)。(c) の最大のずれは %.1f cm。" % (
                       swin["critical_deg"], float(np.squeeze(swin["window_radius_m"])), float(shift_cm.max())))
    # 瓶: 断面と光線
    series = []
    th = np.linspace(0, 2 * np.pi, 361)
    R = 30.0
    series.append(("ガラスの外周", R * np.cos(th), R * np.sin(th)))
    series.append(("水の外周", (R - 1.5) * np.cos(th), (R - 1.5) * np.sin(th)))
    zmax = 75.0
    for k in range(0, full["heights_mm"].size, 3):
        pz, py = full["paths_z_mm"][k], full["paths_y_mm"][k]
        fz = full["focus_z_mm"][k]
        if not np.isfinite(fz):
            continue
        zs = np.concatenate([pz, [min(fz, zmax)]])
        yy = np.concatenate([py, [0.0]])
        series.append(("", zs, yy))
        series.append(("", zs, -yy))
    cz, cy = full["caustic_z_mm"], full["caustic_y_mm"]
    okc = np.isfinite(cz) & (cz < zmax)
    series.append(("焦線(隣り合う光線の交点)", cz[okc], cy[okc]))
    series.append(("近軸焦点", np.array([full["paraxial_focus_mm"]]), np.array([0.0])))
    kinds = ["line"] * (len(series) - 2) + ["scatter", "scatter"]
    colors = ["neutral", "reference"] + ["emphasis"] * (len(series) - 4) + ["wrong", "right"]
    figs.save_plot("bottle_caustic", series, xlabel="光軸方向 z [mm](瓶の中心が 0)", ylabel="y [mm]", kinds=kinds, colors=colors, aspect="equal",
                   size=(720, 420), xlim=(-60, zmax), ylim=(-33, 33),
                   title="水を入れた瓶: 平行光が球面収差で手前に焦線を作る(近軸焦点 %.1f mm、周縁 %.1f mm)" % (full["paraxial_focus_mm"], full["marginal_focus_mm"]),
                   caption="空の瓶はほとんど曲げない(屈折力は水入りの 1/%.0f)。" % abs(full["power_per_mm"] / empty["power_per_mm"]))
    # 液面の検査
    top = np.repeat(np.repeat(irr["empty"][None, :], 240, axis=0), 4, axis=1)
    bot = np.repeat(np.repeat(irr["filled"][None, :], 240, axis=0), 4, axis=1)
    figs.save_grid("fill_level", [top, bot], captions=["液面の上(空の瓶)", "液面の下(水入りの瓶)"], ncols=2, gray=True, vrange=(0.0, 6.0),
                   title="瓶の背後 %.0f mm の面の強度(入射 = 1、白 = 6 以上)" % D,
                   caption="水のある所だけ中央に明るい線(最大 %.1f 倍)、空の所は発散して中央が暗い(%.2f 倍)。" % (
                       float(irr["filled"].max()), float(irr["empty"][80:101].mean())))
    # 色票
    panels, caps = [], []
    for wt in ("jerlov_I", "jerlov_3C"):
        for zz in (1.0, 5.0, 15.0):
            panels.append(np.clip(out[(wt, zz)]["image"], 0, 1))
            caps.append("%s 深さ %g m" % ("I 型" if wt.endswith("I") else "3C 型", zz))
    figs.save_grid("diver_chart", panels, captions=caps, ncols=3, title="同じ色票(カメラから 2 m)を深さ 1・5・15 m で記録すると",
                   caption="上: 外洋(ジャーロフ I)、下: 沿岸(3C)。赤が先に消え、沿岸では青も落ちて緑に寄る。露出は固定。")
    peaks = {k: float(v["image"].max()) for k, v in out.items()}
    panels2 = [np.clip(out[k]["image"] / peaks[k], 0, 1) for k in out]
    caps2 = ["%s %g m(最大 %.3f を 1 に)" % ("I 型" if k[0].endswith("I") else "3C 型", k[1], peaks[k]) for k in out]
    figs.save_grid("diver_chart_exposed", panels2, captions=caps2, ncols=3, title="露出を合わせて(白の票の最大を 1 に)色の偏りだけを見る",
                   caption="I 型は 15 m で青一色、3C 型は 5 m から緑が主になる。")
    wl = np.array([x for x, _ in WM._wd.POPE_FRY_1997]) / 1000.0
    ser = [("純水の吸収 a(Pope & Fry 1997)", wl * 1000, np.log10(pf["a"]))]
    w2 = np.linspace(0.4, 0.7, 61)
    for wt, lab in (("jerlov_I", "Kd 外洋 I"), ("jerlov_III", "Kd III"), ("jerlov_3C", "Kd 沿岸 3C")):
        w3 = w2 if wt != "jerlov_3C" else w2[w2 <= 0.65]
        ser.append((lab, w3 * 1000, np.log10(WM.water_attenuation(w3, wt)["kd"])))
    figs.save_plot("water_spectra", ser, xlabel="波長 [nm]", ylabel="log10 [1/m]", colors=["reference", "emphasis", "right", "wrong"], ylim=(-3.4, 1.2),
                   title="水の吸収と拡散減衰 ―― 赤は数 m で消え、青〜青緑(420〜480 nm)が最も通る",
                   caption="純水の吸収の最小は 417.5 nm の 0.00442 /m、700 nm で 0.624 /m。")
    figs.save_plot("limits_apparent_depth", [("厳密な見かけの深さ / 深さ", ang, 1.0 / N_W / (1 + err)), ("d / n(近軸)", ang, np.full_like(ang, 1.0 / N_W))],
                   xlabel="水面の法線からの見る角 [度]", ylabel="見かけの深さ / 本当の深さ", styles=[None, "dashed"], colors=["wrong", "reference"],
                   title="限界: 平らな水の見かけの深さ d/n は真上だけ ―― 60° で %.0f %% の過大評価" % (100 * err[6]),
                   caption="斜めに見るほど底は浅く見える。")


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 水と透明媒質(予算 %s)" % ("reduced" if REDUCED else "full"))
    ocean = chapter_ocean()
    pool = chapter_pool()
    bottle = chapter_bottle()
    diver = chapter_diver()
    limits = chapter_limits()
    chapter_probes()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(ocean, pool, bottle, diver, limits)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
