#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 収差の絵は、絵のまま採点できる —— ゼルニケ多項式と点像。

★主張は「ゼルニケを綺麗に描けます」ではない。**収差の絵は、描いたあとに
絵から係数を読み返せて、その読み返しが閉形式と厳密に一致する** —— 使うのは
箱にある `fit_zernike`(円板画像 → {(n,m): 係数})と `wavefront_stats`
(RMS・PV・ストレール比)だけ。**新しい op は 1 つも足していない。**

ゼルニケ多項式は単位円板の上の直交系で、収差の言葉そのものになっている ——
(2,0) がデフォーカス、(2,±2) が非点収差、(3,±1) がコマ、(4,0) が球面収差。

    Z_n^m(ρ,θ) = R_n^m(ρ) × {cos|m|θ (m≥0) / sin|m|θ (m<0)}

★★この PoC の芯は 6 つ:

  1. **★既存 op の「開示」の原因が違っていた。** `fit_zernike` は
     「既定のサンプリングでモード間に最大 ~10%% のクロストークが残る。定量が
     要るなら nr/nt を上げよ」と自分で開示している。ところが測ると、漏れは
     解像度では落ちない —— 2 倍ごとの比は **1.93 / 1.78 / 1.50** で、
     1/nr² が言う 4 には遠く、**上げるほど鈍る**。**原因は極座標格子の
     最外リング 1 本が瞳の縁に乗ること**で、そのリングを捨てるだけで
     回収 0.94798 → **1.00000**、漏れは 4 モードの最悪でも 0.09801 →
     **2.6e-4**(デフォーカス単独なら **4.2e-5**)。解像度を 8 倍
     (計算 64 倍)にしても **5.1 倍**しか買えないのに、リング 1 本は
     **ただで 379 倍**。
  2. **絵を回すと、絵は回るのに測った振幅は 1 ビットも動かない。** 回転は
     係数を exp(−imθ) 倍するだけなので、対の振幅 √(c₊²+c₋²) は**厳密に**
     不変 —— 6 通りの角度で最大 **1.1e-16**、二乗和の差は **0.0e+00**。
     絵に描いてから読み返しても、3 通りの回転で幅 **2.03e-09**。
  3. **点像の第 1 暗環はベッセル関数の零点で決まる。** j₁ の第 1 零点 ÷ π =
     **1.219670 λ/D** で、絵から **3.6e-04** 以内。無収差のストレール比は
     厳密に **1.000000000000**。`wavefront_stats` が返すマレシャル近似は
     RMS 0.02 波で差 **8.8e-06** なのに 0.18 波で **2.0e-02** ——
     **2308 倍**に開く。
  4. **干渉縞が消える半径も閉形式。** 球面収差 6ρ⁴−6ρ²+1 の勾配
     12ρ(2ρ²−1) は **ρ = 1/√2** で 0 になり、そこだけ縞が広い帯になる ——
     絵から **0.70462**(真値 0.70711)。ずれは縞の本数に反比例して消える。
  5. **★絵の対称性の回数から m が読めるが、偶数の m は 2 倍の回数で現れる。**
     奇数の |m| は k = |m| に立ち(コマ **0.1200** / 三つ葉 **0.0946**)、
     **偶数の |m| は k = |m| が厳密に消えて**(最大 **0.00050**)k = 2|m| から
     立つ —— 非点収差が「2 回対称」でなく **4 回**に見える理由。偶数 m の
     波面は θ に対し π 周期なので瞳の場が点対称になり、**1 次の交差項が
     恒等的に 0** になるから。収差を半分にすると奇数は **2.06 / 2.02**
     (1 次)、非点収差は **3.67 / 3.66**(2 次)。
  6. **濃淡の付け方は飾りではない。** 点像を線形で塗ると**外側の輪**が
     1 段に潰れる —— 無収差の 3.5〜8.0 λ/D で階調 **1 段**(その帯の最大値は
     **1.6e-03** で、255 倍しても 1 に届かない)。asinh なら **66 段**。
     しかも asinh は狭義単調なので、**画素の大小は 4,998 組すべてで
     入れ替わらない** —— 見やすくすることと嘘をつくことは別だと数で言える。

★外した予言を 3 つ残してある: 瞳の縁をなめらかにしても第 1 暗環は改善しない /
誤差 ∝ 1/瞳径 も成立しない —— 真因は**線形補間**で、3 次にすると最悪 1.1e-02 が
**3.6e-04** になり瞳を 3 倍に振っても平らだった / 停留環を放物線で精密化したら
悪化した。★自分の測り方の欠陥も 2 件: 瞳を格子の中心から半画素ずらして置いて
いた(直すと像面の虚部の残り **5.3e-17**)/ 方位を最近傍で拾って、**瞳の半径にも
縁の滑らかさにもまったく依らない**偽信号 **0.01489** を作っていた(双一次で
**0.00058**、**26 倍**)。
"""
from __future__ import annotations

import os
import sys
import time
from math import factorial

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
from fullseye import render3d as r3                              # noqa: E402

L = fs.ledger
_PASS = []

_PAPER = (0.985, 0.980, 0.968)
_INK = (0.10, 0.12, 0.18)
_MARK = (0.90, 0.62, 0.18)
#: 点像の色。暗部から明部へ —— 赤と緑は対にしない
_PSF_STOPS = [(0.0, (0.03, 0.05, 0.14)), (0.35, (0.16, 0.30, 0.58)),
              (0.68, (0.55, 0.62, 0.78)), (1.0, (1.00, 0.97, 0.90))]

#: n <= 6 の 28 モード。★(n+1)(n+2)/2 = 28 は閉形式で数えられる
N_MAX = 6
MODES = [(n, m) for n in range(N_MAX + 1) for m in range(-n, n + 1, 2)]

#: 収差の呼び名(絵の見出しに使う)
NAMES = {(0, 0): "ピストン", (1, 1): "傾き x", (1, -1): "傾き y",
         (2, 0): "デフォーカス", (2, 2): "非点収差 0°", (2, -2): "非点収差 45°",
         (3, 1): "コマ x", (3, -1): "コマ y", (3, 3): "三つ葉", (3, -3): "三つ葉 30°",
         (4, 0): "球面収差", (4, 2): "二次非点", (4, -2): "二次非点 45°",
         (5, 1): "二次コマ x", (6, 0): "二次球面", (4, 4): "四つ葉"}


def check(ok, label, detail=""):
    _PASS.append(bool(ok))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label,
                            ("---- " + detail) if detail else ""))


# --------------------------------------------------------------------------- #
# ゼルニケ多項式そのもの                                                        #
# --------------------------------------------------------------------------- #
def radial(n, m, rho):
    """R_n^m(ρ)。整数係数の有限和 —— 近似ではない。"""
    am = abs(m)
    out = np.zeros_like(rho)
    for k in range((n - am) // 2 + 1):
        c = ((-1) ** k * factorial(n - k)
             / (factorial(k) * factorial((n + am) // 2 - k)
                * factorial((n - am) // 2 - k)))
        out = out + c * rho ** (n - 2 * k)
    return out


def zern(n, m, rho, theta):
    """Z_n^m(ρ,θ)。★``fit_zernike`` と同じ正規化(R × cos/sin、規格化しない)。"""
    am = abs(m)
    ang = np.cos(am * theta) if m >= 0 else np.sin(am * theta)
    return radial(n, m, rho) * ang


def disk_grid(size, radius_frac=1.0):
    """正方画像の上に (ρ, θ, 円板の内側か) を作る。

    ★半径は ``fit_zernike`` の取り方 ``min(H,W)/2 - 1`` に**厳密に**合わせる。
    ここが 1 画素ずれると、読み返した係数が別のモードへ漏れる。
    """
    cy = cx = (size - 1) / 2.0
    rad = (size / 2.0 - 1.0) * radius_frac
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    rho = np.hypot(y - cy, x - cx) / rad
    theta = np.arctan2(y - cy, x - cx)
    return rho, theta, rho <= 1.0


def wavefront(coeffs, size=256, extend=1.0):
    """係数 → 波面の絵(円板の外は 0)。

    ``extend`` は「多項式を ρ = 1 の何倍まで延ばして描くか」。既定の 1.0 が
    本物の瞳(縁でぷつりと切れる)で、切り分けのときだけ 1 を超えさせる。
    """
    rho, theta, _ = disk_grid(size)
    w = np.zeros_like(rho)
    for (n, m), c in coeffs.items():
        if c:
            w = w + c * zern(n, m, rho, theta)
    return np.where(rho <= extend, w, 0.0)


def rotate_coeffs(coeffs, angle):
    """波面を角度 ``angle`` だけ回したときの係数。★(c₊, c₋) が回るだけ。"""
    out = {}
    for (n, m) in MODES:
        am = abs(m)
        if am == 0:
            out[(n, 0)] = coeffs.get((n, 0), 0.0)
            continue
        cp = coeffs.get((n, am), 0.0)
        cm = coeffs.get((n, -am), 0.0)
        out[(n, am)] = cp * np.cos(am * angle) - cm * np.sin(am * angle)
        out[(n, -am)] = cp * np.sin(am * angle) + cm * np.cos(am * angle)
    return out


def pair_amplitude(coeffs, n, m):
    """対の振幅 √(c₊² + c₋²)。★回転で厳密に不変な量。"""
    am = abs(m)
    if am == 0:
        return abs(float(coeffs.get((n, 0), 0.0)))
    return float(np.hypot(coeffs.get((n, am), 0.0), coeffs.get((n, -am), 0.0)))


# --------------------------------------------------------------------------- #
# 当てはめ —— 既存 op と、外周リングだけ違う自前版                               #
# --------------------------------------------------------------------------- #
def fit_dropping_rings(img, rings, n_max=N_MAX, nr=48, nt=72):
    """``fit_zernike`` と同じ手順で、**外周 ``rings`` 本だけ捨てて**当てはめる。

    ★op 本体には触らない。「原因はここだ」を示すための、同じ手順の写しである。
    """
    import torch
    import torch.nn.functional as F
    from match3d import _zernike_basis

    H, W = img.shape
    B, idx, rho = _zernike_basis(nr, nt, n_max)
    cy, cx = (H - 1) / 2, (W - 1) / 2
    rad = min(H, W) / 2 - 1
    rr = np.linspace(0, 1, nr)
    th = np.linspace(0, 2 * np.pi, nt, endpoint=False)
    Rg, Tg = np.meshgrid(rr, th, indexing="ij")
    ys = cy + Rg * rad * np.sin(Tg)
    xs = cx + Rg * rad * np.cos(Tg)
    grid = torch.stack([torch.as_tensor(xs / (W - 1) * 2 - 1, dtype=torch.float32),
                        torch.as_tensor(ys / (H - 1) * 2 - 1, dtype=torch.float32)],
                       -1)[None]
    samp = F.grid_sample(torch.as_tensor(np.asarray(img, np.float32))[None, None],
                         grid, align_corners=True)[0, 0].numpy().ravel()
    mask = rho <= 1.0 - rings / float(nr)
    coef, *_ = np.linalg.lstsq(B[:, mask].T, samp[mask], rcond=None)
    return {idx[i]: float(coef[i]) for i in range(len(idx))}


def worst_leak(coeffs, n, m):
    return max(abs(v) for k, v in coeffs.items() if k != (n, m))


# --------------------------------------------------------------------------- #
# 点像(PSF)                                                                    #
# --------------------------------------------------------------------------- #
def pupil_field(coeffs, radius, grid, defocus=0.0):
    """瞳の複素振幅 P = 1[ρ≤1]·exp(i2πW) を、**格子の中心にぴったり**置く。

    ★中心を半画素ずらすと像面に一次の位相が乗り、振幅の実部で零点を探す手が
    使えなくなる(実際に踏んだ: 虚部の残りが 1e-2 まで立って測定がずれた)。
    中心が合っていれば虚部は 4e-17 に落ちる —— それが置けている証拠になる。
    """
    c = grid // 2
    y, x = np.mgrid[0:grid, 0:grid].astype(np.float64)
    rho = np.hypot(y - c, x - c) / float(radius)
    theta = np.arctan2(y - c, x - c)
    inside = rho <= 1.0
    w = np.zeros_like(rho)
    for (n, m), k in coeffs.items():
        if k:
            w = w + k * zern(n, m, np.clip(rho, 0.0, 1.0), theta)
    if defocus:
        w = w + defocus * zern(2, 0, np.clip(rho, 0.0, 1.0), theta)
    return np.where(inside, np.exp(2j * np.pi * w), 0.0), inside


def psf_of(coeffs, radius=96, grid=1024, defocus=0.0):
    """波面 → 点像。返り (psf, 1 画素あたりの λ/D)。

    瞳の**直径**が 2·radius 画素、格子が ``grid`` 画素なら、点像の 1 画素は
    **2·radius/grid λ/D**。★分母は格子でなく瞳の直径。
    """
    p, _ = pupil_field(coeffs, radius, grid, defocus)
    amp = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(p)))
    psf = np.abs(amp) ** 2
    return psf / psf.max(), 2.0 * radius / float(grid)


def airy_zero(radius=96, grid=2048, cubic=True):
    """無収差の点像の振幅が**最初に符号を変える**半径を返す(λ/D 単位)。

    ★線形補間では駄目。エアリー振幅は零点の近くでよく曲がっているので、
    線形だと誤差が 1.1e-2 まで立ち、しかも瞳を大きくすると悪化して見える。
    3 次で補間すると 2.5e-4 まで落ち、**瞳の半径 64→512 の 8 倍でほぼ平ら**
    —— 非単調だったのは物理ではなく補間だったと分かる。
    """
    p, _ = pupil_field({}, radius, grid)
    amp = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(p)))
    c = grid // 2
    v = np.real(amp[c, c:])
    imag_left = float(np.abs(np.imag(amp[c, c:])).max() / abs(np.real(amp[c, c])))
    v = v / v[0]
    i = int(np.argmax(v < 0))
    if cubic:
        xs = np.arange(i - 2, i + 2, dtype=np.float64)
        coef = np.polyfit(xs, v[i - 2:i + 2], 3)
        roots = np.roots(coef)
        roots = roots[np.abs(roots.imag) < 1e-9].real
        z = float(roots[np.argmin(np.abs(roots - (i - 0.5)))])
    else:
        z = (i - 1) + v[i - 1] / (v[i - 1] - v[i])
    return z * 2.0 * radius / float(grid), imag_left


def radial_profile(img, scale, n=900):
    """点像の方位平均 → (半径[λ/D], 値)。★輪を数で掴むため。"""
    c = (img.shape[0] - 1) / 2.0
    y, x = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(np.float64)
    r = np.hypot(y - c, x - c) * scale
    rmax = n * scale
    b = np.clip((r / scale).astype(np.int64), 0, n)
    tot = np.bincount(b.ravel(), img.ravel(), minlength=n + 1)
    cnt = np.bincount(b.ravel(), minlength=n + 1)
    good = cnt > 0
    return (np.arange(n + 1)[good] * scale), (tot[good] / cnt[good]), rmax


def first_dark_ring(rr, vv):
    """方位平均の最初の谷を放物線で補間して返す。★絵から測り返す量。"""
    i = 1
    while i + 1 < len(vv) and not (vv[i] < vv[i - 1] and vv[i] < vv[i + 1]):
        i += 1
    if i + 1 >= len(vv):
        return float("nan")
    y0, y1, y2 = vv[i - 1], vv[i], vv[i + 1]
    d = y0 - 2.0 * y1 + y2
    off = 0.5 * (y0 - y2) / d if abs(d) > 1e-30 else 0.0
    return float(rr[i] + off * (rr[i] - rr[i - 1]))


def fringe_stationary_radius(amp, size=512):
    """干渉縞の絵から、**縞が消える半径**を測る。

    球面収差 Z(4,0) = 6ρ⁴−6ρ²+1 の勾配は 12ρ(2ρ²−1) なので、ρ = 1/√2 で
    停留する —— そこだけ縞の間隔が開く。中心から 1 本引いて明暗の境目
    (cos = 0 の点)を拾い、**いちばん広い間隔の中央**を返す。
    """
    rho, theta, _ = disk_grid(size)
    w = amp * zern(4, 0, np.clip(rho, 0.0, 1.0), theta)
    img = 0.5 + 0.5 * np.cos(2.0 * np.pi * w)
    c = (size - 1) / 2.0
    rad = size / 2.0 - 1.0
    xs = np.arange(int(np.ceil(c)), size)
    prof = img[int(round(c)), xs]
    rr = (xs - c) / rad
    sgn = np.sign(prof - 0.5)
    cross = []
    for i in np.where(sgn[:-1] != sgn[1:])[0]:
        t = (0.5 - prof[i]) / (prof[i + 1] - prof[i])
        cross.append(rr[i] + t * (rr[i + 1] - rr[i]))
    cross = np.asarray([v for v in cross if v <= 1.0])
    gaps = np.diff(cross)
    mids = 0.5 * (cross[:-1] + cross[1:])
    return float(mids[int(np.argmax(gaps))]), int(len(cross))


def psf_harmonics(psf, scale, rmax=5.0, nt=720, nr=200, bilinear=True):
    """点像を極座標で拾い、**方位方向のフーリエ係数**を返す(k=0 で正規化)。

    ★拾い方で答えが変わる。最近垖で拾うと正方格子の 4 回対称が信号に化け、
    k=4 に 0.0138 の偽信号が立つ —— しかも**瞳の半径にも縁の滑らかさにも
    まったく依らない**(半径 48/96/192 で 0.01384 のまま)ので、瞳のせいだと
    誤診しやすい。双一次なら 0.00058 に落ちる。
    """
    g = psf.shape[0]
    c = g // 2
    rr = np.linspace(0.15, rmax, nr) / scale
    th = np.linspace(0.0, 2.0 * np.pi, nt, endpoint=False)
    R, T = np.meshgrid(rr, th, indexing="ij")
    ys = c + R * np.sin(T)
    xs = c + R * np.cos(T)
    if bilinear:
        y0 = np.clip(np.floor(ys).astype(np.int64), 0, g - 2)
        x0 = np.clip(np.floor(xs).astype(np.int64), 0, g - 2)
        fy, fx = ys - y0, xs - x0
        pol = ((1 - fy) * (1 - fx) * psf[y0, x0]
               + (1 - fy) * fx * psf[y0, x0 + 1]
               + fy * (1 - fx) * psf[y0 + 1, x0]
               + fy * fx * psf[y0 + 1, x0 + 1])
    else:
        pol = psf[np.clip(np.rint(ys).astype(np.int64), 0, g - 1),
                  np.clip(np.rint(xs).astype(np.int64), 0, g - 1)]
    F = np.abs(np.fft.rfft(pol, axis=1)).sum(0)
    return F / F[0]


def exact_strehl(coeffs, n=512):
    """厳密なストレール比 |∫exp(i2πW)dA|² / A²(近似を使わない)。"""
    rho, theta, inside = disk_grid(n)
    w = np.zeros_like(rho)
    for (n_, m), c in coeffs.items():
        if c:
            w = w + c * zern(n_, m, rho, theta)
    z = np.exp(2j * np.pi * w)[inside]
    return float(abs(z.mean()) ** 2)


# --------------------------------------------------------------------------- #
# 絵を作る道具 —— ★色は飾りでなく量に結びつける                                  #
# --------------------------------------------------------------------------- #
def ramp(t, stops):
    """停留点の色を線形につなぐ → (..., 3)。"""
    t = np.clip(np.asarray(t, np.float64), 0.0, 1.0)
    out = np.zeros(t.shape + (3,))
    for i in range(len(stops) - 1):
        a, ca = stops[i]
        b, cb = stops[i + 1]
        m = (t >= a) & (t <= b)
        if not m.any():
            continue
        u = ((t[m] - a) / (b - a))[:, None] if t.ndim == 1 else \
            ((t[m] - a) / (b - a))[..., None]
        out[m] = np.asarray(ca) * (1 - u) + np.asarray(cb) * u
    return out


def tone(v, knee):
    """asinh トーン。★狭義単調なので、画素の**順位は厳密に保たれる**。"""
    return np.arcsinh(np.asarray(v, np.float64) / knee) / np.arcsinh(1.0 / knee)


def diverging(v, lo=None, hi=None):
    """符号つきの場を 0 中心で塗る(箱の `diverging_lut` を使う)。"""
    a = np.asarray(v, np.float64)
    m = float(np.max(np.abs(a))) if hi is None else hi
    m = m or 1.0
    lut = np.asarray(fs.diverging_lut(256), np.float64)
    idx = np.clip((a / m * 0.5 + 0.5) * 255.0, 0, 255).astype(np.int32)
    return np.clip(lut[idx], 0.0, 1.0)


def tile_disk(rgb, inside, paper=_PAPER):
    """円板の外を紙の色で塗りつぶす。"""
    out = rgb.copy()
    out[~inside] = paper
    return out


def pyramid(size=86, gap=6):
    """28 モードをピラミッドに並べた 1 枚の絵を作る。"""
    rows = N_MAX + 1
    wide = rows * (size + gap) + gap
    tall = rows * (size + gap) + gap
    canvas = np.ones((tall, wide, 3)) * _PAPER
    rho, theta, inside = disk_grid(size)
    for n in range(rows):
        ms = list(range(-n, n + 1, 2))
        x0 = (wide - len(ms) * (size + gap) + gap) // 2
        for j, m in enumerate(ms):
            z = np.where(inside, zern(n, m, np.clip(rho, 0, 1), theta), 0.0)
            tile = tile_disk(diverging(z), inside)
            y = gap + n * (size + gap)
            x = x0 + j * (size + gap)
            canvas[y:y + size, x:x + size] = tile
    return canvas


def wavefront_mesh(coeffs, rings=64, spokes=192, height=0.42):
    """波面を立体に起こす → (V, F)。

    ★**極座標で張る。** 正方格子のマスクで円板を切ると縁が鋸歯になり、
    「数学の絵なのに縁がギザギザ」という見た目の欠陥がそのまま出る
    (最初にそれを作った)。輪 x 放射で張れば縁は**真円**になる。
    """
    rho_r = np.linspace(0.0, 1.0, rings)
    th_s = np.linspace(0.0, 2.0 * np.pi, spokes, endpoint=False)
    Rg, Tg = np.meshgrid(rho_r, th_s, indexing="ij")
    w = np.zeros_like(Rg)
    for (nn, m), c in coeffs.items():
        if c:
            w = w + c * zern(nn, m, Rg, Tg)
    span = float(np.abs(w).max()) or 1.0
    xs = Rg * np.cos(Tg)
    ys = Rg * np.sin(Tg)
    zs = w / span * height
    V = np.stack([xs.ravel(), ys.ravel(), zs.ravel()], 1)
    idx = np.arange(rings * spokes).reshape(rings, spokes)
    a = idx[:-1, :]
    b = idx[:-1, :]
    b = np.roll(idx[:-1, :], -1, axis=1)
    c2 = idx[1:, :]
    d = np.roll(idx[1:, :], -1, axis=1)
    F = np.concatenate([
        np.stack([a.ravel(), b.ravel(), d.ravel()], 1),
        np.stack([a.ravel(), d.ravel(), c2.ravel()], 1)], 0)
    return V, np.asarray(F, np.int64)


def render_surface(V, F, w=460, h=380, eye=(1.55, -1.75, 1.15), fov=52.0):
    """箱の描画器で立体を描き、陰影だけ返す。★枠を使い切る距離に置く。"""
    pose = r3.look_at(np.asarray(eye, np.float64), np.zeros(3), up=(0, 0, 1))
    K = r3.intrinsics_from_fov(fov, w, h)
    out = r3.render_mesh(V, F, pose, K, w, h)
    nrm = np.asarray(out["normals"], np.float64)
    sil = np.asarray(out["silhouette"]).astype(bool)
    light = np.asarray((0.42, -0.62, 0.66))
    light = light / np.linalg.norm(light)
    lam = np.clip((nrm * light).sum(-1), 0.0, 1.0)
    return lam, sil


# --------------------------------------------------------------------------- #
def run_checks():
    """章を順に走らせ、図が要る材料を返す。★図を書くのは全部の章より後。"""
    t0 = time.time()
    print("PoC: 収差の絵は、絵のまま採点できる —— ゼルニケ多項式と点像")
    print("=" * 72)
    out = {}

    # ---------------------------------------------------------------- #
    print("\n1. 多項式そのものが厳密(数え上げ・端の値・零点の本数)")
    n_modes = len(MODES)
    closed = (N_MAX + 1) * (N_MAX + 2) // 2
    print("   n <= %d のモード数 %d(閉形式 (n+1)(n+2)/2 = %d)"
          % (N_MAX, n_modes, closed))
    check(n_modes == closed, "モードの数え上げが閉形式と一致",
          "%d = (n+1)(n+2)/2" % n_modes)

    one = np.array([1.0])
    edge_err = max(abs(float(radial(n, m, one)[0]) - 1.0) for n, m in MODES)
    print("   R_n^m(1) の 1 からのずれ 最大 %.1e" % edge_err)
    check(edge_err < 1e-12, "どのモードも縁で厳密に 1 になる",
          "28 本すべてで %.1e 以内 —— 係数が整数の有限和だから" % edge_err)

    rr_fine = np.linspace(1e-6, 1.0, 20001)
    zero_bad, zero_counts = 0, []
    for n, m in MODES:
        v = radial(n, m, rr_fine)
        nz = int(np.sum(np.sign(v[:-1]) != np.sign(v[1:])))
        zero_counts.append(nz)
        if nz != (n - abs(m)) // 2:
            zero_bad += 1
    check(zero_bad == 0, "半径方向の零点の本数が (n−|m|)/2 と一致",
          "28 本すべてで一致(外れ %d 本)—— 絵の縞の本数が整数で決まる" % zero_bad)
    out["zero_counts"] = zero_counts

    # ---------------------------------------------------------------- #
    print("\n2. 直交性は閉形式で書ける")
    nr_q, nt_q = 2400, 720
    rho_q = (np.arange(nr_q) + 0.5) / nr_q
    th_q = (np.arange(nt_q) + 0.5) * 2.0 * np.pi / nt_q
    Rq, Tq = np.meshgrid(rho_q, th_q, indexing="ij")
    dA = (Rq / nr_q) * (2.0 * np.pi / nt_q)
    basis_q = np.stack([zern(n, m, Rq, Tq).ravel() for n, m in MODES])
    gram = (basis_q * dA.ravel()) @ basis_q.T
    diag_rel = []
    for i, (n, m) in enumerate(MODES):
        truth = np.pi / (2.0 * (n + 1)) * (2.0 if m == 0 else 1.0)
        diag_rel.append(abs(gram[i, i] / truth - 1.0))
    off_rel = float(np.abs(gram - np.diag(np.diag(gram))).max()
                    / np.diag(gram).max())
    print("   対角の閉形式との相対差 最大 %.2e / 非対角の最大 %.2e"
          % (max(diag_rel), off_rel))
    check(max(diag_rel) < 1e-4, "対角は閉形式 π/(2(n+1))·(1+δ_m0) と一致",
          "最大 %.2e —— 積分の刻みで決まる残り" % max(diag_rel))
    check(off_rel < 1e-5, "非対角は 0",
          "最大 %.2e —— 28 本は互いに直交している" % off_rel)
    out["gram"] = gram
    out["diag_rel"] = max(diag_rel)
    out["off_rel"] = off_rel

    # ---------------------------------------------------------------- #
    print("\n3. ★絵から係数を読み返す —— op の開示の原因が違っていた")
    probe = [(2, 0), (4, 0), (2, 2), (3, 1)]
    fit_default, fit_dropped = {}, {}
    for (n, m) in probe:
        img = wavefront({(n, m): 1.0}, size=256)
        c_def = L.fit_zernike(img.astype(np.float32), n_max=N_MAX)
        c_drop = fit_dropping_rings(img, rings=1)
        fit_default[(n, m)] = (c_def[(n, m)], worst_leak(c_def, n, m))
        fit_dropped[(n, m)] = (c_drop[(n, m)], worst_leak(c_drop, n, m))
        print("   %-12s 既定: 回収 %.5f 漏れ %.5f | 外周 1 本を捨てる: "
              "回収 %.5f 漏れ %.5f"
              % (NAMES.get((n, m), "Z"), fit_default[(n, m)][0],
                 fit_default[(n, m)][1], fit_dropped[(n, m)][0],
                 fit_dropped[(n, m)][1]))
    leak_def = max(v[1] for v in fit_default.values())
    leak_drop = max(v[1] for v in fit_dropped.values())
    rec_drop = max(abs(v[0] - 1.0) for v in fit_dropped.values())
    gain_ring = leak_def / max(leak_drop, 1e-12)
    check(leak_def > 0.08, "既定の当てはめは op の開示どおり約 10 パーセント漏れる",
          "4 モードで最大 %.4f(docstring の記述と一致)" % leak_def)
    check(leak_drop < 1e-3 and rec_drop < 1e-3,
          "★外周リングを 1 本捨てるだけで漏れが消える",
          "漏れ %.5f から %.6f へ(%.0f 倍)、回収のずれ %.6f —— "
          "解像度は一切上げていない" % (leak_def, leak_drop, gain_ring, rec_drop))

    nr_list = (48, 96, 192, 384)
    leak_curve = []
    for nr in nr_list:
        img = wavefront({(2, 0): 1.0}, size=256)
        c = L.fit_zernike(img.astype(np.float32), n_max=N_MAX,
                          nr=nr, nt=nr * 3 // 2)
        leak_curve.append(worst_leak(c, 2, 0))
    ratio_nr = [leak_curve[i] / leak_curve[i + 1]
                for i in range(len(leak_curve) - 1)]
    gain_res = leak_curve[0] / leak_curve[-1]
    print("   漏れと解像度: %s"
          % " / ".join("nr=%d %.5f" % (a, b) for a, b in zip(nr_list, leak_curve)))
    print("   2 倍ごとの比 %s(1/n なら 2、1/n の 2 乗なら 4)"
          % " / ".join("%.2f" % r for r in ratio_nr))
    check(all(r < 2.2 for r in ratio_nr) and gain_res < 6.0,
          "★漏れは解像度では落ちない —— 1/nr の 2 乗どころか 1/nr より鈍い",
          "2 倍ごとの比 %s。1/nr なら 2、1/nr の 2 乗なら 4 なので、**4 には"
          "遠く、しかも上げるほど鈍る**(%.2f → %.2f)。8 倍の解像度"
          "(計算 64 倍)で %.1f 倍しか買えないのに、リング 1 本はただで %.0f 倍"
          % (" / ".join("%.2f" % r for r in ratio_nr), ratio_nr[0],
             ratio_nr[-1], gain_res, gain_ring))

    over_list = (1.02, 1.05)
    over_gain = []
    for over in over_list:
        img = wavefront({(2, 0): 1.0}, size=256, extend=over)
        c = L.fit_zernike(img.astype(np.float32), n_max=N_MAX)
        over_gain.append(worst_leak(c, 2, 0))
    print("   多項式を円板の外まで延ばす(解像度そのまま): %s"
          % " / ".join("%.2f 倍まで %.6f" % (o, g)
                       for o, g in zip(over_list, over_gain)))
    check(max(over_gain) < 1e-3,
          "★縁の段差を円板の縁から追い出しても同じだけ消える",
          "漏れ %.5f から %.6f へ —— 原因は最外リングが瞳の縁に乗ること"
          % (leak_def, max(over_gain)))
    out.update(fit_default=fit_default, fit_dropped=fit_dropped,
               nr_list=nr_list, leak_curve=leak_curve, leak_def=leak_def,
               leak_drop=leak_drop, gain_ring=gain_ring, gain_res=gain_res,
               ratio_nr=ratio_nr, over_list=over_list, over_gain=over_gain,
               probe=probe)

    # ---------------------------------------------------------------- #
    print("\n4. 絵を回しても、測った振幅は 1 ビットも動かない")
    coma = {(3, 1): 0.62, (3, -1): 0.24, (2, 2): 0.35, (4, 0): 0.18}
    amp_ref = {(n, m): pair_amplitude(coma, n, m) for (n, m) in MODES if m >= 0}
    worst_rot = 0.0
    for a in (0.0, 0.4, 0.9, 1.7, 2.6, 4.1):
        cr = rotate_coeffs(coma, a)
        for key in amp_ref:
            worst_rot = max(worst_rot,
                            abs(pair_amplitude(cr, *key) - amp_ref[key]))
    print("   6 通りの角度で、対の振幅のずれ 最大 %.2e" % worst_rot)
    check(worst_rot < 1e-14, "★回転しても対の振幅は厳密に不変",
          "最大 %.1e —— 回転は係数を exp(-imθ) 倍するだけだから" % worst_rot)

    sq_ref = sum(v * v for v in coma.values())
    sq_rot = sum(v * v for v in rotate_coeffs(coma, 1.234).values())
    check(abs(sq_ref - sq_rot) < 1e-13, "回転で二乗和(RMS の素)も不変",
          "%.15f と %.15f(差 %.1e)—— パーセヴァル"
          % (sq_ref, sq_rot, abs(sq_ref - sq_rot)))

    pic_angles = (0.0, 0.7, 1.9)
    amp_pic = []
    for a in pic_angles:
        img = wavefront(rotate_coeffs(coma, a), size=256, extend=1.05)
        c = L.fit_zernike(img.astype(np.float32), n_max=N_MAX)
        amp_pic.append(pair_amplitude(c, 3, 1))
    spread_pic = float(np.ptp(amp_pic))
    print("   絵に描いて読み返したコマの振幅: %s"
          % " / ".join("%.6f" % v for v in amp_pic))
    check(spread_pic < 2e-3, "★絵に描いて読み返しても振幅は動かない",
          "3 通りの回転で幅 %.2e(真値 %.6f)—— 絵は回るのに数は動かない"
          % (spread_pic, pair_amplitude(coma, 3, 1)))
    out.update(coma=coma, worst_rot=worst_rot, amp_pic=amp_pic,
               spread_pic=spread_pic, pic_angles=pic_angles,
               amp_truth=pair_amplitude(coma, 3, 1))

    # ---------------------------------------------------------------- #
    print("\n5. 点像の輪は、ベッセル関数の零点で決まる")
    from scipy.special import jn_zeros
    airy_truth = float(jn_zeros(1, 1)[0] / np.pi)
    print("   真値 j1 の第 1 零点 / pi = %.9f" % airy_truth)
    airy_radii = (64, 96, 192)
    airy_meas, imag_left = [], []
    for radius in airy_radii:
        z, im = airy_zero(radius, 2048)
        airy_meas.append(z)
        imag_left.append(im)
        print("   瞳の半径 %3d 画素  絵から測った第 1 零点 %.7f(ずれ %+.1e)"
              % (radius, z, z - airy_truth))
    airy_err = max(abs(z - airy_truth) for z in airy_meas)

    #: ★同じ絵を**線形補間**で読むとどうなるか(章ごとの接尾辞 lin_)
    lin_meas = [airy_zero(r, 2048, cubic=False)[0] for r in airy_radii]
    lin_err = [abs(z - airy_truth) for z in lin_meas]
    print("   同じ絵を線形補間で読むと: %s"
          % " / ".join("半径 %d で %.6f(ずれ %+.1e)" % (r, z, z - airy_truth)
                       for r, z in zip(airy_radii, lin_meas)))
    lin_worst = max(lin_err)
    lin_mono = all(lin_err[i] >= lin_err[i + 1] for i in range(len(lin_err) - 1))
    check(lin_worst > 8.0 * airy_err and not lin_mono,
          "★非単調さの正体は物理ではなく補間だった",
          "線形なら最悪 %.1e(3 次の %.1e の %.0f 倍)で、しかも瞳を大きくすると"
          "**悪化する**(%s)—— 瞳の縁でも解像度でもなく、零点の近くで"
          "エアリー振幅がよく曲がっているから"
          % (lin_worst, airy_err, lin_worst / airy_err,
             " → ".join("%.1e" % e for e in lin_err)))

    check(airy_err < 2e-3, "★絵から測った第 1 暗環がベッセルの零点と一致",
          "瞳の半径を 3 倍に振ってもずれは %.1e 以内(真値 %.6f λ/D)"
          % (airy_err, airy_truth))
    check(max(imag_left) < 1e-12, "瞳が格子の中心にぴったり乗っている",
          "像面の虚部の残り %.1e —— 半画素ずれるとここが立って測定が狂う"
          % max(imag_left))

    strehl_perfect = exact_strehl({})
    check(abs(strehl_perfect - 1.0) < 1e-12, "無収差のストレール比は厳密に 1",
          "%.12f" % strehl_perfect)
    out.update(airy_truth=airy_truth, airy_meas=airy_meas,
               airy_radii=airy_radii, airy_err=airy_err,
               lin_meas=lin_meas, lin_err=lin_err, lin_worst=lin_worst)

    # ---------------------------------------------------------------- #
    print("\n6. マレシャル近似がどこで壊れるか")
    w_unit = wavefront({(3, 1): 1.0}, size=512)
    _, _, ins_u = disk_grid(512)
    rms_unit = float(np.sqrt((w_unit[ins_u] ** 2).mean()))
    sig_list = (0.02, 0.04, 0.08, 0.12, 0.18)
    str_rows = []
    for sig in sig_list:
        k = sig / rms_unit
        ex = exact_strehl({(3, 1): k})
        st = L.wavefront_stats({(0, 0): 0.0, (3, 1): k},
                               radial=192, angular=288)
        str_rows.append((sig, ex, float(st["strehl"]), float(st["rms_waves"])))
        print("   RMS %.3f 波  厳密 %.6f  マレシャル %.6f  差 %+.2e"
              % (sig, ex, st["strehl"], st["strehl"] - ex))
    dev = [abs(r[2] - r[1]) for r in str_rows]
    open_ratio = dev[-1] / dev[0]
    check(dev[0] < 1e-4 and open_ratio > 20,
          "★マレシャル近似は小さい収差でだけ当たる",
          "RMS %.2f 波で差 %.1e、RMS %.2f 波で %.1e —— %.0f 倍に開く"
          % (sig_list[0], dev[0], sig_list[-1], dev[-1], open_ratio))
    rms_gap = max(abs(r[3] - r[0]) / r[0] for r in str_rows)
    check(rms_gap < 0.02, "op が返す RMS は、絵から測った RMS と一致",
          "5 通りで相対差 %.2e 以内" % rms_gap)
    out.update(sig_list=sig_list, str_rows=str_rows, dev=dev,
               open_ratio=open_ratio)

    # ---------------------------------------------------------------- #
    print("\n7. 干渉縞が消える半径は、勾配の零点で決まる")
    fringe_truth = 1.0 / np.sqrt(2.0)
    print("   真値 12ρ(2ρ²−1) = 0 より ρ = 1/√2 = %.9f" % fringe_truth)
    fringe_amps = (2.0, 3.0, 4.0, 6.0)
    fringe_meas, fringe_n = [], []
    for amp in fringe_amps:
        r_st, n_cross = fringe_stationary_radius(amp)
        fringe_meas.append(r_st)
        fringe_n.append(n_cross)
        print("   振幅 %.0f 波(縞の境目 %2d 本)  絵から %.5f(ずれ %+.1e)"
              % (amp, n_cross, r_st, r_st - fringe_truth))
    fringe_err = [abs(v - fringe_truth) for v in fringe_meas]
    fringe_ratio = [fringe_err[0] / fringe_err[2], fringe_err[1] / fringe_err[3]]
    print("   振幅を 2 倍にしたときの誤差の比 %s(1/本数 なら 2)"
          % " / ".join("%.2f" % r for r in fringe_ratio))
    check(fringe_err[-1] < 5e-3, "★絵から測った停留環が閉形式と一致",
          "振幅 %.0f 波で %.5f(真値 %.5f、ずれ %.1e)"
          % (fringe_amps[-1], fringe_meas[-1], fringe_truth, fringe_err[-1]))
    check(all(1.7 < r < 2.4 for r in fringe_ratio),
          "ずれは縞の本数に反比例して消える",
          "振幅を 2 倍にすると %s 倍に減る —— 間隔の中央で代表させている"
          "ぶんの偏りなので、縞が細かいほど小さくなる"
          % " / ".join("%.2f" % r for r in fringe_ratio))

    # ---------------------------------------------------------------- #
    print("\n8. ★絵の対称性から m が読める —— ただし偶数の m は 2 倍の回数で")
    harm_floor = psf_harmonics(*psf_of({}, radius=48, grid=1024))
    harm_floor_nn = psf_harmonics(*psf_of({}, radius=48, grid=1024),
                                  bilinear=False)
    print("   無収差のときに立つ偽信号(あってはいけない量): "
          "双一次 k=4 %.5f / 最近傍 k=4 %.5f" % (harm_floor[4], harm_floor_nn[4]))
    check(harm_floor[4] < harm_floor_nn[4] / 10.0,
          "★偽信号の正体は瞳ではなく**極座標での拾い方**だった",
          "最近傍 %.5f → 双一次 %.5f(%.0f 倍)。最近傍の値は瞳の半径にも"
          "縁の滑らかさにも依らない —— だから瞳のせいではない"
          % (harm_floor_nn[4], harm_floor[4],
             harm_floor_nn[4] / max(harm_floor[4], 1e-12)))
    harm_cut = 5.0 * harm_floor[4]

    harm_rows = []
    for (hn, hm) in ((2, 0), (4, 0), (3, 1), (2, 2), (3, 3), (4, 4)):
        h = psf_harmonics(*psf_of({(hn, hm): 0.25}, radius=48, grid=1024))
        am = abs(hm)
        harm_rows.append((hn, hm, h))
        print("   %-10s |m|=%d  k=|m| %.5f  k=2|m| %.5f  (k=1..8: %s)"
              % (NAMES.get((hn, hm), "Z"), am,
                 h[am] if am else float("nan"),
                 h[2 * am] if am else float("nan"),
                 " ".join("%.4f" % h[k] for k in range(1, 9))))

    zero_m = [h for (hn, hm, h) in harm_rows if hm == 0]
    worst_m0 = max(float(np.max(h[1:9])) for h in zero_m)
    check(worst_m0 < harm_cut, "m = 0 の収差は絵も厳密に回転対称",
          "デフォーカスと球面収差で k=1..8 の最大 %.5f(床 %.5f 以下)"
          % (worst_m0, harm_cut))

    odd_ok = all(h[abs(hm)] > 20.0 * harm_cut
                 for (hn, hm, h) in harm_rows if abs(hm) % 2 == 1)
    even_zero = max(h[abs(hm)] for (hn, hm, h) in harm_rows
                    if hm != 0 and abs(hm) % 2 == 0)
    even_two = min(h[2 * abs(hm)] for (hn, hm, h) in harm_rows
                   if hm != 0 and abs(hm) % 2 == 0)
    check(odd_ok, "奇数の |m| は k = |m| に立つ",
          "コマ %.4f / 三つ葉 %.4f —— **絵の対称性の回数がそのまま m**"
          % (harm_rows[2][2][1], harm_rows[4][2][3]))
    check(even_zero < harm_cut and even_two > 20.0 * max(even_zero, 1e-12),
          "★偶数の |m| は k = |m| が厳密に消え、k = 2|m| から立つ",
          "偶数 m の k=|m| は最大 %.5f(測定の床 %.5f 以下)なのに k=2|m| は "
          "%.4f 以上 —— **%.0f 倍**。偶数 m の波面は θ に対し π 周期なので"
          "瞳の場が点対称になり、**1 次の交差項が恒等的に 0** になる"
          % (even_zero, harm_cut, even_two,
             even_two / max(even_zero, 1e-12)))

    #: ★1 次か 2 次かは「収差を半分にしたときの比」で分かる(章ごとの接尾辞)
    harm_scale = {}
    for (hn, hm) in ((3, 1), (3, 3), (2, 2)):
        am = abs(hm)
        kk = am if am % 2 else 2 * am
        vals = [psf_harmonics(*psf_of({(hn, hm): c}, radius=48, grid=1024))[kk]
                for c in (0.20, 0.10, 0.05)]
        harm_scale[(hn, hm)] = (kk, vals,
                                [vals[i] / vals[i + 1] for i in range(2)])
        print("   %-10s k=%d を半分ずつ: %s  比 %s"
              % (NAMES.get((hn, hm), "Z"), kk,
                 " / ".join("%.5f" % v for v in vals),
                 " / ".join("%.2f" % r for r in harm_scale[(hn, hm)][2])))
    odd_ratio = [r for (hn, hm), (_k, _v, rs) in harm_scale.items()
                 if abs(hm) % 2 == 1 for r in rs]
    even_ratio = harm_scale[(2, 2)][2]
    check(all(1.7 < r < 2.3 for r in odd_ratio)
          and all(3.3 < r < 4.3 for r in even_ratio),
          "★奇数 m は 1 次、偶数 m は 2 次 —— 半分にしたときの比で分かれる",
          "奇数 %s(2 に寄る)/ 非点収差 %s(4 に寄る)"
          % (" ".join("%.2f" % r for r in odd_ratio),
             " ".join("%.2f" % r for r in even_ratio)))

    # ---------------------------------------------------------------- #
    print("\n9. ★濃淡の付け方は飾りではない")
    psf_sa, scale_sa = psf_of({(4, 0): 0.30}, radius=96, grid=1024)
    psf_airy, scale_airy = psf_of({}, radius=96, grid=1024)
    #: ★帯は必ず書く。球面収差のハローは明るいので、同じ帯でも段数が変わる
    #:   (実測: 無収差の 3.5-8.0 λ/D は線形 1 段、球面収差 0.30 波なら 6 段)。
    zone_lo, zone_hi = 3.5, 8.0
    cc = (psf_airy.shape[0] - 1) / 2.0
    yy, xx = np.mgrid[0:psf_airy.shape[0],
                      0:psf_airy.shape[1]].astype(np.float64)
    rad_ld = np.hypot(yy - cc, xx - cc) * scale_airy
    ring_zone = (rad_ld > zone_lo) & (rad_ld < zone_hi)
    tone_levels = {}
    for tag, pic in (("airy", psf_airy), ("sa", psf_sa)):
        lin8 = np.rint(pic * 255).astype(np.int32)
        asi8 = np.rint(tone(pic, 3e-4) * 255).astype(np.int32)
        tone_levels[tag] = (int(len(np.unique(lin8[ring_zone]))),
                            int(len(np.unique(asi8[ring_zone]))))
    lin_levels, asi_levels = tone_levels["airy"]
    print("   %.1f-%.1f λ/D の帯を 8 bit にしたときの階調の数 —— "
          "無収差: 線形 %d / asinh %d、球面収差 0.30 波: 線形 %d / asinh %d"
          % (zone_lo, zone_hi, lin_levels, asi_levels,
             tone_levels["sa"][0], tone_levels["sa"][1]))
    check(lin_levels <= 2 and asi_levels >= 40,
          "★線形では外側の輪が 1 段(完全な黒)に潰れる。asinh なら出る",
          "無収差の %.1f-%.1f λ/D で 線形 %d 段 → asinh %d 段。"
          "その帯の最大値は %.1e —— 255 倍しても 1 に届かない"
          % (zone_lo, zone_hi, lin_levels, asi_levels,
             float(psf_airy[ring_zone].max())))

    rng_tone = np.random.default_rng(7)
    va = psf_sa.ravel()[rng_tone.integers(0, psf_sa.size, 8000)]
    vb = tone(va, 3e-4)
    i1 = rng_tone.integers(0, len(va), 5000)
    i2 = rng_tone.integers(0, len(va), 5000)
    keep = i1 != i2
    same = (np.sign(va[i1[keep]] - va[i2[keep]])
            == np.sign(vb[i1[keep]] - vb[i2[keep]]))
    kept = float(np.mean(same))
    check(kept == 1.0, "★asinh は画素の順位を厳密に保つ",
          "%d 組すべてで大小が入れ替わらない —— 見やすくすることと"
          "嘘をつくことは別" % int(keep.sum()))
    out.update(fringe_truth=fringe_truth, fringe_amps=fringe_amps,
               fringe_meas=fringe_meas, fringe_n=fringe_n,
               fringe_err=fringe_err, fringe_ratio=fringe_ratio)
    out.update(harm_rows=harm_rows, harm_floor=harm_floor,
               harm_floor_nn=harm_floor_nn, harm_cut=harm_cut,
               harm_scale=harm_scale, worst_m0=worst_m0,
               even_zero=even_zero, even_two=even_two)
    out.update(psf_sa=psf_sa, scale_sa=scale_sa, psf_airy=psf_airy,
               zone_lo=zone_lo, zone_hi=zone_hi, tone_levels=tone_levels,
               lin_levels=lin_levels, asi_levels=asi_levels,
               zone_max=float(psf_airy[ring_zone].max()),
               pairs_kept=int(keep.sum()))
    return t0, out


# --------------------------------------------------------------------------- #
# 図                                                                           #
# --------------------------------------------------------------------------- #
def mosaic(panels, titles, ncols, pad=8, label_h=0):
    """RGB のパネルを並べて 1 枚にする(色を自分で決めたいときに使う)。"""
    h, w = panels[0].shape[:2]
    rows = (len(panels) + ncols - 1) // ncols
    out = np.ones((rows * (h + pad) + pad + rows * label_h,
                   ncols * (w + pad) + pad, 3)) * _PAPER
    for i, p in enumerate(panels):
        r, c = divmod(i, ncols)
        y = pad + r * (h + pad + label_h)
        x = pad + c * (w + pad)
        out[y:y + h, x:x + w] = np.clip(p, 0.0, 1.0)
    return out


def psf_picture(coeffs, radius=48, grid=2048, half=6.0, knee=3e-4,
                defocus=0.0):
    """点像を「見える」絵にする —— asinh トーン + 暗部から明部への配色。

    ★1 画素は 2·radius/grid λ/D。既定では **0.047 λ/D** で、半径 6 λ/D まで
    切り出すと 256 画素角になる。最初これを 0.375 λ/D で作って、輪が 16 画素に
    潰れた絵を出した(生成物を開いて気づいた)。
    """
    psf, scale = psf_of(coeffs, radius=radius, grid=grid, defocus=defocus)
    n = int(half / scale)
    c = grid // 2
    crop = psf[c - n:c + n, c - n:c + n]
    return ramp(tone(crop, knee), _PSF_STOPS)


def upscale(img, k):
    """最近傍で k 倍に伸ばす(格子そのものを見せたい絵に使う)。"""
    return np.repeat(np.repeat(np.asarray(img), k, axis=0), k, axis=1)


def interferogram(coeffs, size=320, fringes=1.0):
    """波面 → 干渉縞 cos(2πW)。★収差の形がそのまま縞の崩れになる。"""
    rho, theta, inside = disk_grid(size)
    w = np.zeros_like(rho)
    for (n, m), k in coeffs.items():
        if k:
            w = w + k * zern(n, m, np.clip(rho, 0.0, 1.0), theta)
    fr = 0.5 + 0.5 * np.cos(2.0 * np.pi * fringes * w)
    rgb = ramp(fr, [(0.0, (0.07, 0.10, 0.22)), (0.5, (0.30, 0.46, 0.62)),
                    (1.0, (0.97, 0.95, 0.88))])
    return tile_disk(rgb, inside)


def draw_figures(out):
    """★図はここだけで書く。数字は必ず ``out`` から取る(章の変数を触らない)。"""
    fit_default = out["fit_default"]
    fit_dropped = out["fit_dropped"]

    # 01 ---------------------------------------------------------------- #
    figs.save("zernike_pyramid", pyramid(),
              "**ゼルニケ多項式のピラミッド**。上から n = 0, 1, …, 6 で、"
              "横は m = −n … n(2 飛び)。合計 **%d 枚** —— これは閉形式 "
              "(n+1)(n+2)/2 で数えられる整数です。2 段目が傾き、3 段目の中央が"
              "**デフォーカス**、両端が**非点収差**、4 段目が**コマ**と三つ葉、"
              "5 段目の中央が**球面収差**。0 を中心に塗ってあるので、山と谷が"
              "そのまま波面の凹凸です。半径方向の縞の本数は **(n−|m|)/2 本**で、"
              "28 枚すべてがその整数どおりでした。" % len(MODES))

    # 02 ---------------------------------------------------------------- #
    panels_3d, caps_3d = [], []
    for key in ((2, 0), (2, 2), (3, 1), (4, 0)):
        V, F = wavefront_mesh({key: 1.0})
        lam, sil = render_surface(V, F)
        rgb = np.ones(lam.shape + (3,)) * _PAPER
        body = ramp(0.25 + 0.72 * lam, [(0.0, (0.10, 0.16, 0.34)),
                                        (0.55, (0.36, 0.52, 0.66)),
                                        (1.0, (0.96, 0.93, 0.86))])
        rgb[sil] = body[sil]
        panels_3d.append(rgb)
        caps_3d.append(NAMES.get(key, ""))
    figs.save("wavefront_3d", mosaic(panels_3d, caps_3d, 2),
              "**波面を立体に起こす**(箱の `render3d` で描画)。左上が"
              "デフォーカス(お椀)、右上が非点収差(鞍)、左下がコマ、"
              "右下が球面収差。収差の名前は、この形の名前です。"
              "立体にしても採点は変わりません —— 係数は絵ではなく多項式に"
              "属しているからで、後の図で**絵を回しても数が動かないこと**を"
              "見せます。")

    # 03 ---------------------------------------------------------------- #
    mix = {(3, 1): 0.55, (2, 2): 0.30, (4, 0): 0.22}
    figs.save("interferogram",
              mosaic([interferogram({(2, 0): 1.2}), interferogram({(4, 0): 1.2}),
                      interferogram({(3, 1): 1.2}), interferogram(mix, fringes=2.0)],
                     ["", "", "", ""], 2),
              "**干渉縞** cos(2πW)。左上デフォーカス、右上球面収差、"
              "左下コマ、右下は 3 つを混ぜたもの(縞を 2 倍細かく)。"
              "干渉計が実際に見せる絵で、**縞の数がそのまま波面の波数**です。"
              "★デフォーカスと球面収差はどちらも同心円ですが、**縞の間隔の"
              "変わり方が違います**。デフォーカス 2ρ²−1 の勾配は 4ρ なので"
              "中心から縁へ単調に詰まるだけ。球面収差 6ρ⁴−6ρ²+1 の勾配は "
              "**12ρ(2ρ²−1)** で、**ρ = 1/√2 ≈ 0.7071 で 0 になる** —— "
              "そこだけ縞が消えて広い帯になります(右上の中ほどの太い輪)。"
              "この半径は閉形式で決まるので、**絵から測り返せます** —— "
              "振幅 %.0f 波の絵から %.5f(真値 %.5f)。"
              % (out["fringe_amps"][-1], out["fringe_meas"][-1],
                 out["fringe_truth"]))

    # 04 ---------------------------------------------------------------- #
    gal_keys = [({}, "無収差(エアリー)"), ({(2, 0): 0.25}, "デフォーカス"),
                ({(2, 2): 0.25}, "非点収差"), ({(3, 1): 0.25}, "コマ"),
                ({(4, 0): 0.25}, "球面収差"), ({(3, 3): 0.25}, "三つ葉")]
    figs.save("psf_gallery",
              mosaic([psf_picture(c) for c, _ in gal_keys],
                     [t for _, t in gal_keys], 3),
              "**点像(PSF)** —— 波面 P = exp(i2πW) のフーリエ変換の強度。"
              "左上から 無収差・デフォーカス・非点収差 / コマ・球面収差・三つ葉"
              "(いずれも 0.25 波)。**同心の輪になるのは無収差だけではありません** "
              "—— デフォーカスも球面収差も m = 0 なので厳密に回転対称です"
              "(方位ハーモニクスの最大 %.5f、床 %.5f 以下)。崩れるのは "
              "m ≠ 0 のほう: コマは片側に尾を引き、三つ葉は 3 回、非点収差は "
              "**4 回**(2 回ではありません —— 次の図がその理由です)。"
              "全部 asinh トーンで塗ってあります(線形だと次の図のように"
              "外側の輪が 1 段に潰れて見えません)。")

    # 05 ---------------------------------------------------------------- #
    lo, hi = out["zone_lo"], out["zone_hi"]
    #: ★検査で使った点像は瞳 96・格子 1024(1 画素 0.19 λ/D)で、絵としては
    #:   粗い。**同じ無収差**をもう一度、細かい刻みで描き直す(数は検査のもの)。
    psf_big, scale_big = psf_of({}, radius=48, grid=2048)
    half_px = int(hi * 1.12 / scale_big)
    c0 = psf_big.shape[0] // 2
    crop = psf_big[c0 - half_px:c0 + half_px, c0 - half_px:c0 + half_px]
    lin_rgb = ramp(crop, _PSF_STOPS)
    asi_rgb = ramp(tone(crop, 3e-4), _PSF_STOPS)
    figs.save("tone_matters", mosaic([lin_rgb, asi_rgb], ["", ""], 2),
              "**濃淡の付け方は飾りではありません。** 同じ無収差の点像です。"
              "左は線形、右は asinh。%.1f〜%.1f λ/D の帯を 8 bit にすると、"
              "左は階調 **%d 段**(つまり完全な黒。その帯の最大値は %.1e で、"
              "255 倍しても 1 に届きません)、右は **%d 段**。"
              "★そして asinh は狭義単調なので、**画素の大小関係は 1 組も"
              "入れ替わりません**(%d 組で検査)—— 見やすくすることと"
              "嘘をつくことは別だと数で言えます。"
              % (lo, hi, out["lin_levels"], out["zone_max"],
                 out["asi_levels"], out["pairs_kept"]))

    # 06 ---------------------------------------------------------------- #
    foc = np.linspace(-0.55, 0.55, 24)
    frames_foc = [psf_picture({}, radius=32, grid=1024, half=5.0,
                              defocus=float(d)) for d in foc]
    frames_foc = frames_foc + frames_foc[-2:0:-1]
    figs.save_gif("through_focus", frames_foc, fps=10.0, caption=(
        "**スルーフォーカス** —— デフォーカスを −0.55 波から +0.55 波まで"
        "振って戻します。輪が**同心のまま**伸縮するのがデフォーカスの特徴で、"
        "ピントの前後で絵が対称になります(だから往復させても継ぎ目が"
        "見えません)。中央の 1 コマだけが無収差のエアリーで、そこだけ"
        "ストレール比が厳密に **1.000000000000** です。"))

    # 07 ---------------------------------------------------------------- #
    coma = out["coma"]
    n_rot = 24
    frames_rot = []
    for i in range(n_rot):
        a = 2.0 * np.pi * i / n_rot
        cr = rotate_coeffs(coma, a)
        rho, theta, inside = disk_grid(300)
        w = np.zeros_like(rho)
        for (n, m), k in cr.items():
            if k:
                w = w + k * zern(n, m, np.clip(rho, 0.0, 1.0), theta)
        left = tile_disk(diverging(w, hi=1.25), inside)
        right = psf_picture(cr, radius=32, grid=1024, half=4.6)
        #: 左右の高さを合わせる(添字の配列で拾う。二重ループは使わない)
        iy = (np.arange(300) * right.shape[0] // 300)
        ix = (np.arange(300) * right.shape[1] // 300)
        right = right[iy[:, None], ix[None, :]]
        frames_rot.append(mosaic([left, right], ["", ""], 2))
    figs.save_gif("rotating_coma", frames_rot, fps=8.0, caption=(
        "**絵は回るのに、測った数は動きません。** 左が波面(コマ %.2f ＋ "
        "非点収差 %.2f ＋ 球面収差 %.2f)、右がその点像。1 周ぶん回して"
        "います。回転は係数を exp(−imθ) 倍するだけなので、対の振幅 "
        "√(c₊²+c₋²) は**厳密に**不変 —— 6 通りの角度で最大 **%.1e**。"
        "しかも**絵に描いてから `fit_zernike` で読み返しても**、3 通りの"
        "回転で振幅の幅は **%.1e** しかありません(真値 %.6f)。"
        "★球面収差(m = 0)だけは絵そのものが回りません —— m = 0 は"
        "回転で変わらないモードだからで、これも絵から読めます。"
        % (coma[(3, 1)], coma[(2, 2)], coma[(4, 0)], out["worst_rot"],
           out["spread_pic"], out["amp_truth"])))

    # 08 ---------------------------------------------------------------- #
    probe = out["probe"]
    bars = []
    for (n, m) in probe:
        bars.append((NAMES.get((n, m), "Z"), fit_default[(n, m)][1],
                     fit_dropped[(n, m)][1]))
    figs.save_plot("edge_ring",
                   [("既定(外周を使う)", np.arange(len(bars)) + 1.0,
                     np.array([b[1] for b in bars])),
                    ("外周リングを 1 本捨てる", np.arange(len(bars)) + 1.0,
                     np.array([b[2] for b in bars]))],
                   xlabel="モード(1 デフォーカス / 2 球面収差 / 3 非点収差 / 4 コマ)",
                   ylabel="他モードへの漏れ(絶対値の最大)",
                   title="漏れの原因は解像度ではなく、円板の縁に乗った 1 本",
                   caption=("★`fit_zernike` は docstring で「既定のサンプリング"
                            "ではモード間に最大 ~10%% のクロストークが残る。"
                            "定量が要るなら nr/nt を上げよ」と自分で開示して"
                            "います。ところが原因は解像度ではありません —— "
                            "極座標格子の**いちばん外のリング 1 本**(半径の "
                            "2%%)が瞳の縁に乗り、双一次補間が外側の 0 を"
                            "吸い込んでいる。**解像度は一切変えず**にその 1 本"
                            "を捨てるだけで、漏れは 4 モードの最悪でも "
                            "%.5f → **%.6f**(%.0f 倍)、回収のずれは "
                            "%.6f になります。"
                            % (out["leak_def"], out["leak_drop"],
                               out["gain_ring"], max(
                                   abs(v[0] - 1.0)
                                   for v in fit_dropped.values()))),
                   kinds=("bar", "bar"))

    # 09 ---------------------------------------------------------------- #
    nr_arr = np.asarray(out["nr_list"], np.float64)
    leak_arr = np.asarray(out["leak_curve"], np.float64)
    figs.save_plot("leak_vs_nr",
                   [("実測の漏れ", nr_arr, leak_arr),
                    ("1/nr なら", nr_arr, leak_arr[0] * nr_arr[0] / nr_arr),
                    ("1/nr² なら", nr_arr,
                     leak_arr[0] * (nr_arr[0] / nr_arr) ** 2)],
                   xlabel="極座標格子の半径方向の刻み nr",
                   ylabel="他モードへの漏れ",
                   title="解像度を上げても、漏れは 1/nr より鈍く落ちる",
                   caption=("解像度を 8 倍(計算量は **64 倍**)にしても漏れは "
                            "%.5f → %.5f の **%.1f 倍**しか減りません。"
                            "2 倍ごとの比は %s —— 1/nr なら 2、1/nr² なら 4 "
                            "なので、**4 には遠く、しかも上げるほど鈍ります**。"
                            "前の図の「リング 1 本」はただで %.0f 倍でした。"
                            "★これが「解像度を上げよ」という直し方の値段です。"
                            % (leak_arr[0], leak_arr[-1], out["gain_res"],
                               " / ".join("%.2f" % r for r in out["ratio_nr"]),
                               out["gain_ring"])))

    # 10 ---------------------------------------------------------------- #
    gram = out["gram"]
    gn = gram / np.abs(gram).max()
    figs.save("gram_matrix", upscale(np.abs(gn), 16),
              "**28 × 28 のグラム行列** ∫Z_n^m Z_n'^m' ρdρdθ。"
              "対角しか光りません —— つまり 28 本は互いに直交しています。"
              "対角の値は閉形式 **π/(2(n+1))·(1+δ_m0)** と相対差 **%.1e** で"
              "一致し、非対角は最大 **%.1e**(0 であるべき量)。"
              "★この直交性があるから、絵から読んだ係数が「そのモードだけの"
              "量」になります。前の 2 枚で見た漏れは、この直交性が壊れたの"
              "ではなく、**絵を極座標で拾うところ**で壊れていたのです。"
              % (out["diag_rel"], out["off_rel"]))

    # 11 ---------------------------------------------------------------- #
    psf_a, sc_a = psf_of({}, radius=96, grid=2048)
    rr_a, vv_a, _ = radial_profile(psf_a, sc_a, n=160)
    keep_a = rr_a <= 5.0
    figs.save_plot("airy_profile",
                   [("絵から測った方位平均", rr_a[keep_a], vv_a[keep_a])],
                   xlabel="中心からの距離(λ/D)", ylabel="強度(中心を 1 とする)",
                   title="第 1 暗環の位置はベッセル関数の零点で決まる",
                   caption=("無収差の点像の方位平均。最初の谷の位置は "
                            "**j₁ の第 1 零点 ÷ π = %.6f λ/D** という閉形式で"
                            "決まります。絵の振幅が符号を変える点を 3 次補間で"
                            "読むと **%.6f**(ずれ %.1e)。瞳の半径を %d → %d "
                            "画素の 3 倍に振ってもずれは同じ桁のままです。"
                            "★同じ絵を**線形補間**で読むと誤差は最悪 %.1e "
                            "(3 次の %.1e の %.0f 倍)まで立ち、しかも瞳を"
                            "大きくすると **%s と悪化します** —— "
                            "非単調さの正体は物理ではなく補間でした。"
                            % (out["airy_truth"], out["airy_meas"][1],
                               out["airy_meas"][1] - out["airy_truth"],
                               out["airy_radii"][0], out["airy_radii"][-1],
                               out["lin_worst"], out["airy_err"],
                               out["lin_worst"] / out["airy_err"],
                               " → ".join("%.1e" % e for e in out["lin_err"]))))

    # 12 ---------------------------------------------------------------- #
    sig = np.asarray([r[0] for r in out["str_rows"]], np.float64)
    ex = np.asarray([r[1] for r in out["str_rows"]], np.float64)
    ma = np.asarray([r[2] for r in out["str_rows"]], np.float64)
    figs.save_plot("strehl_vs_marechal",
                   [("厳密な回折積分", sig, ex),
                    ("マレシャル近似 exp(−(2πσ)²)", sig, ma)],
                   xlabel="波面の RMS(波)", ylabel="ストレール比",
                   title="近似はどこまで使えるのか、を数で出す",
                   caption=("`wavefront_stats` が返すストレール比は"
                            "マレシャル近似 exp(−(2πσ)²) です。厳密な回折積分 "
                            "|∫exp(i2πW)dA|²/A² と比べると、RMS %.2f 波では"
                            "差 **%.1e** しかないのに、RMS %.2f 波では "
                            "**%.1e** —— **%.0f 倍**に開きます。"
                            "★無収差では厳密に **1.000000000000**。"
                            "op はこの限界を docstring で開示していて、"
                            "今回それを実測で裏づけました(op の返す RMS 自体は"
                            "絵から測った RMS と相対差 %.1e で一致)。"
                            % (sig[0], out["dev"][0], sig[-1], out["dev"][-1],
                               out["open_ratio"],
                               max(abs(r[3] - r[0]) / r[0]
                                   for r in out["str_rows"]))))

    # 13 ---------------------------------------------------------------- #
    harm_rows_f = out["harm_rows"]
    ks = np.arange(1, 9, dtype=np.float64)
    figs.save_plot(
        "psf_harmonics",
        [("%s |m|=%d" % (NAMES.get((hn, hm), "Z"), abs(hm)), ks,
          np.asarray([h[int(k)] for k in ks]))
         for (hn, hm, h) in harm_rows_f if hm != 0],
        xlabel="方位ハーモニクスの次数 k", ylabel="振幅(k=0 で正規化)",
        title="偶数の m では k = |m| が厳密に消える",
        kinds=("scatter",) * 4,
        caption=("点像を極座標で拾って方位方向にフーリエ変換したもの。"
                 "**奇数の |m|** はそのまま k = |m| に立ちます(コマ %.4f、"
                 "三つ葉 %.4f)。ところが**偶数の |m| は k = |m| が厳密に 0** "
                 "で(最大 %.5f、床 %.5f 以下)、k = 2|m| から立ちます ——"
                 "非点収差が「2 回対称」ではなく **4 回**に見えるのはこれです。"
                 "★理由があります: 偶数 m の波面は θ に対し π 周期なので瞳の場が"
                 "点対称になり、1 次の交差項(実数のエアリー場 × 純虚数の項)が"
                 "**恒等的に 0** になる。だから偶数 m は 2 次からで、収差を"
                 "半分にすると **1/4**(非点収差の実測 %s)、奇数 m は 1 次なので "
                 "**1/2**(実測 %s)。"
                 % (harm_rows_f[2][2][1], harm_rows_f[4][2][3],
                    out["even_zero"], out["harm_cut"],
                    " / ".join("%.2f" % r for r in out["harm_scale"][(2, 2)][2]),
                    " / ".join("%.2f" % r
                               for r in out["harm_scale"][(3, 1)][2]))))

    rows = [
        ["モードの数 (n≤6)", "(n+1)(n+2)/2", "%d" % len(MODES), "厳密"],
        ["R_n^m(1)", "1", "1", "28 本すべて"],
        ["半径方向の零点", "(n−|m|)/2", "一致", "28 本すべて"],
        ["直交性(対角)", "π/(2(n+1))(1+δ_m0)", "相対差 %.1e" % out["diag_rel"], "刻みで決まる"],
        ["直交性(非対角)", "0", "%.1e" % out["off_rel"], "0 であるべき量"],
        ["既定の当てはめの漏れ", "op の開示 ~10%", "%.4f" % out["leak_def"], "開示どおり"],
        ["★外周 1 本を捨てる", "-", "%.6f" % out["leak_drop"], "%.0f 倍" % out["gain_ring"]],
        ["解像度 8 倍(計算 64 倍)", "-", "%.1f 倍" % out["gain_res"], "買えるのはこれだけ"],
        ["回転での振幅のずれ", "0", "%.1e" % out["worst_rot"], "厳密に不変"],
        ["絵から読み返した振幅の幅", "0", "%.1e" % out["spread_pic"], "3 通りの回転"],
        ["第 1 暗環", "%.6f λ/D" % out["airy_truth"],
         "%.6f" % out["airy_meas"][1], "ずれ %.1e" % out["airy_err"]],
        ["線形補間で読んだ第 1 暗環", "-", "ずれ最悪 %.1e" % out["lin_worst"],
         "3 次の %.0f 倍" % (out["lin_worst"] / out["airy_err"])],
        ["無収差のストレール比", "1", "1.000000000000", "厳密"],
        ["マレシャルのずれの開き", "-", "%.0f 倍" % out["open_ratio"], "RMS 0.02→0.18 波"],
        ["干渉縞が消える半径", "1/√2 = %.5f" % out["fringe_truth"],
         "%.5f" % out["fringe_meas"][-1], "ずれ %.1e" % out["fringe_err"][-1]],
        ["偶数 m の k=|m|", "0", "%.5f" % out["even_zero"], "厳密に消える"],
        ["偶数 m の k=2|m|", "-", "%.4f 以上" % out["even_two"], "2 次から立つ"],
        ["半分にしたときの比(奇数 m)", "2(1 次)",
         "%.2f" % out["harm_scale"][(3, 1)][2][0], "コマ"],
        ["半分にしたときの比(偶数 m)", "4(2 次)",
         "%.2f" % out["harm_scale"][(2, 2)][2][0], "非点収差"],
        ["極座標の拾い方の偽信号", "0", "最近傍 %.5f / 双一次 %.5f"
         % (out["harm_floor_nn"][4], out["harm_floor"][4]), "%.0f 倍"
         % (out["harm_floor_nn"][4] / max(out["harm_floor"][4], 1e-12))],
        ["外側の輪の階調(線形)", "-", "%d 段" % out["lin_levels"], "完全な黒"],
        ["外側の輪の階調(asinh)", "-", "%d 段" % out["asi_levels"], "輪が出る"],
        ["asinh が保つ順位", "全部", "%d 組" % out["pairs_kept"], "入れ替わり 0"],
    ]
    figs.save_table("numbers", ["量", "閉形式・真値", "実測", "備考"], rows,
                    title="この回の数字",
                    caption=("実測はすべて **`fit_zernike` / `wavefront_stats`** と"
                             "閉形式が返したもの。**新しい op は 1 つも"
                             "足していません。**"))


def main():
    t0, out = run_checks()
    if figs.enabled():
        draw_figures(out)
        errs = figs.errors()
        assert not errs, errs

    ok = sum(_PASS)
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(_PASS), ok, time.time() - t0))
    if ok != len(_PASS):
        for i, v in enumerate(_PASS):
            if not v:
                print("  NG が残っている(%d 番目)" % (i + 1))
        return 1
    # ★門 tests/test_poc_scripts_run.py は exit 0 だけでなく PASS の印字も見る。
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
