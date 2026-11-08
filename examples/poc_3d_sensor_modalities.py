# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC 2026.309: 同じ部品を 3-D センサの 5 方式で「測り」、どの方式がどこで壊れるかを数字で並べる。

    py -3.11 examples/poc_3d_sensor_modalities.py

展示会のブースは、自社の 1 方式を最良の部品で見せる。ここでは**同じ部品・同じ材質**を、
ステレオ・縞投影(位相シフト格子投影)・間接 ToF・光切断・照度差ステレオの 5 方式で撮り、
真値(部品の寸法表)と比べる。材質は 4 つ(つや消し・金属光沢・半透明の樹脂・黒)。

部品(寸法表 :data:`PART`)は段差・止まり穴・斜面・V 溝・薄いリブを持つ機械部品で、
撮像は物理で描く: 面の傾きと材質の反射(Lambert + Beckmann の鏡面の山)、光源と視点の影、
加工の筋と粒(テクスチャ)、半透明の樹脂の内部散乱(入った光が中でにじんで出る)、
画素の開口(細かく描いて画素で足す = 縁の混合)、センサの雑音(ショット・読み出し・12 bit・飽和)、
光切断のスペックル、金属の鏡面の 1 回反射(V 溝の中の 2 回反射 = 偽の光)、V 溝の中の拡散の相互反射
(``lighttransport.form_factors_2d``)。どれも「その方式の装置ならこう写る」の生の画像まで描いてから、
Fullseye の op で高さに戻す:

* ステレオ(受動、ドーム + 斜めの 1 灯、2 台を ±15° に傾けた正射影)→ ``fs.ledger.binocular_disparity_ms``
* 縞投影(投影 30°、周期 16 / 4 / 1 mm の 4 段位相シフト × 3)→ ``fringe.wrapped_phase`` /
  ``fringe.modulation`` / ``fringe.absolute_phase`` / ``fringe.phase_to_height``
* 間接 ToF(100 MHz、4 段、画素 0.4 mm)→ ``itof.itof_capture`` / ``itof.itof_phase_amplitude`` /
  ``itof.itof_flying_pixel_mask``
* 光切断(シート光は鉛直、カメラ 30°、0.05 mm 送り)→ ``lightsection.laser_line_center_centroid``
* 照度差ステレオ(仰角 45° の 8 灯)→ ``fs.photometric_stereo_robust`` / ``photometric.integrate_normals``

採点は 1 つの数字にしない: 平らな所の雑音、偏り(平らな所の差の中央値)、欠測、形の外れ(偏りを引いた差が
**全方式に共通の** 0.1 mm / 1 mm を超えた有効画素)、それに機械の人が実際に見る寸法 —— 段差の高さ・穴の深さ・
斜面の角度・V 溝の深さ・打痕 —— を真値と比べる。

条件は揃えられる所は揃えた: 三角測量の角(ステレオ ±15°・縞投影・光切断とも 30°)、露光(どの方式も
つや消しの 8 倍まで上げる自動露光。ToF は積分時間)。揃えないもの(画素: ToF 0.4 mm、ほか 0.05 mm。撮像の
枚数: 2 / 12 / 4 段 / 8 / 1 列 1 コマ)は現場の典型として書き、条件を振ると順位が動くことを 4 章の表で示す。
材質の値(反射率・粗さ・内部散乱の広がり 0.25 mm)は著者が置いた値で、出典があるのは鏡面の反射率だけ。

既存の方式別の深掘りとの関係: 受入試験は ``poc_virtual_acceptance_3d``(3 つの設計案を VDI/VDE 2634 Part 2 の
考え方で。この PoC の 5 章は同じ評価 op を使う)、ToF は ``poc_tof_camera`` / ``poc_itof_multifreq`` /
``poc_dtof_ranging``、縞の相互反射は ``poc_interreflection_fringe_error``、光切断の床は
``poc_laser_line_speckle_floor`` / ``poc_light_section_step_weld_floor``、実写ステレオは ``poc_real_stereo_depth`` /
``poc_real_stereo_multiscanline``、照度差ステレオは ``examples/specular_photometric.py``。どれも 1 方式を深く掘る。
この PoC の新しさは、**同じ部品・同じ材質を 5 方式とも生の画像から描いて復号し、方式をまたいで同じ物差しで
並べた**こと。★既存との数字の突き合わせ: 光切断のスペックルの雑音は、同じ条件の op の独立な 2-D コヒーレント結像の
シミュ(既存の 2 本と同じく Dorsch × √(w/L) の約 0.87 倍)と比べる。誤りが 3 つあって直した —— 式に光条の幅を全幅で
渡していた、参照の op を粗い細かさ・少ない試行で呼んでいた、瞳の遮断を像の座標でなく u' で掛けていた。残る差(画素
0.05 mm で op より低い)は 1 章に数字で出し、未解決とする。

何が外からの真値で何が検算か(2026-11-08 の敵対的レビューで分けた):
外からの真値 = 部品の寸法表と、光切断のスペックルの床(``lightsection.light_section_speckle_floor`` = Dorsch の式と、
その op の独立なコヒーレント結像のシミュ)。縞投影の ``σ_φ = √(2/N)·σ_I / b`` と ToF の ``itof_noise_budget`` は
同じ雑音モデルの解析式なので**実装の検算**。実データ(Middlebury 2014 の実写ステレオ = scikit-image 同梱の
1/4 縮小、T-LESS の同じ場面を構造化光と ToF の 2 種の深度センサで撮った深度と CAD の真値 = CC BY 4.0)が
支えるのは**段差の縁の外側が太るか浮くかの向きだけ**で、材質の主張はシミュだけ。

所要時間(この機械、2026-11-08 実測): 図つきの full 実行 約 12〜23 分(T-LESS あり、697〜1386 秒。同じ機械でも負荷で変わる)、CI の縮小版(画素 0.1 mm・図なし)約 2.5 分(136 秒)。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import fringe  # noqa: E402
import itof  # noqa: E402
import lighttransport  # noqa: E402
import lightsection  # noqa: E402
import photometric  # noqa: E402

#: CI(図を出さない実行)では部品を半分の細かさで描く。図つきの full 実行は手元で。
REDUCED = not figs.enabled()

# --------------------------------------------------------------------------- #
# 部品(寸法表)と格子
# --------------------------------------------------------------------------- #
#: カメラ 1 画素が部品の上で占める幅 [mm](ToF 以外)。CI では 2 倍粗い。
PITCH = 0.10 if REDUCED else 0.05
#: 1 画素を何×何の標本で描くか(画素の開口で光を足す = 縁の混合)
SS = 2
FINE = PITCH / SS
W_MM, H_MM = 40.0, 24.0
#: 部品の寸法表 [mm]。x = 縞・光切断・ステレオの三角測量の向き。z = 高さ(台の面 = 0)。
PART = {
    "block": (2.0, 14.0, 6.0),          # 上段のブロック x0, x1, 高さ
    "plateau": (14.0, 20.0, 3.0),       # 段差 3 mm の下の段
    "ramp": (20.0, 25.0, 3.0, 0.5),     # 斜面 x0, x1, 上端の高さ, 下端の高さ(26.57°)
    "floor": 0.5,                       # 斜面より先の床
    "groove": (32.0, 1.0, 1.0),         # 90° の V 溝: 中心 x, 半幅, 深さ
    "rib": (36.0, 38.0, 4.0),           # 薄いリブ x0, x1, 高さ
    "hole": (8.0, 12.0, 2.0, 3.0),      # 止まり穴: 中心 x, y, 半径, 深さ
    "hole_small": (8.0, 4.5, 1.0, 2.0),  # 小さい穴
    # 浅い打痕(球の一部)x, y, 半径, 深さ。下の段の上に 50 µm と 15 µm
    "dents": ((17.0, 8.0, 0.8, 0.050), (17.0, 16.0, 0.8, 0.015)),
}
#: 寸法の真値(採点に使う)
TRUE_STEP = PART["block"][2] - PART["plateau"][2]
TRUE_HOLE = PART["hole"][3]
TRUE_SLOPE_DEG = float(np.degrees(np.arctan((PART["ramp"][2] - PART["ramp"][3])
                                            / (PART["ramp"][1] - PART["ramp"][0]))))
TRUE_GROOVE = PART["groove"][2]
TRUE_RIB = PART["rib"][2] - PART["floor"]


#: 部品を画素の格子からずらして置く [mm]。★ずらさないと壁が ToF の画素(0.4 mm)の境目にちょうど乗り、
#: 縁の混合画素が 1 つも出ない(2026-11-08 に実測: ToF の縁の外側が全部「正しい」)。実物の壁は画素の境目を選ばない
X_SHIFT, Y_SHIFT = 0.175, 0.125


def grid(pitch):
    """画素の中心の部品座標 (X, Y) [mm]。"""
    nx, ny = int(round(W_MM / pitch)), int(round(H_MM / pitch))
    x = (np.arange(nx) + 0.5) * pitch - X_SHIFT
    y = (np.arange(ny) + 0.5) * pitch - Y_SHIFT
    return np.meshgrid(x, y)


def part_height(pitch):
    """寸法表 → 高さの図 [mm](格子 ``pitch``)。"""
    X, Y = grid(pitch)
    z = np.zeros_like(X)
    b0, b1, bh = PART["block"]
    p0, p1, ph = PART["plateau"]
    r0, r1, rt, rb = PART["ramp"]
    z[(X >= b0) & (X < b1)] = bh
    z[(X >= p0) & (X < p1)] = ph
    m = (X >= r0) & (X < r1)
    z[m] = rt + (rb - rt) * (X[m] - r0) / (r1 - r0)
    z[X >= r1] = PART["floor"]
    gc, gw, gd = PART["groove"]
    m = np.abs(X - gc) < gw
    z[m] = PART["floor"] - gd * (1.0 - np.abs(X[m] - gc) / gw)
    q0, q1, qh = PART["rib"]
    z[(X >= q0) & (X < q1)] = qh
    for key in ("hole", "hole_small"):
        hx, hy, hr, hd = PART[key]
        z[(X - hx) ** 2 + (Y - hy) ** 2 < hr ** 2] = bh - hd
    for dx, dy, dr, dd in PART["dents"]:
        # 半径 dr・深さ dd の球冠: 球の半径 R = (dr² + dd²) / (2 dd)
        R = (dr ** 2 + dd ** 2) / (2 * dd)
        r2 = (X - dx) ** 2 + (Y - dy) ** 2
        m = r2 < dr ** 2
        z[m] -= np.sqrt(R ** 2 - r2[m]) - (R - dd)
    return z


def regions(pitch):
    """採点の領域(画素の格子 ``pitch``)。縁の帯は段差の両側 0.3 mm。"""
    X, Y = grid(pitch)
    z = part_height(pitch)
    band = 0.3
    walls = [PART["block"][0], PART["block"][1], PART["rib"][0], PART["rib"][1]]
    edge = np.zeros(X.shape, bool)
    for w in walls:
        edge |= np.abs(X - w) < band
    for key in ("hole", "hole_small"):
        hx, hy, hr, _ = PART[key]
        rr = np.hypot(X - hx, Y - hy)
        edge |= np.abs(rr - hr) < band
    hole = np.zeros(X.shape, bool)
    for key in ("hole", "hole_small"):
        hx, hy, hr, _ = PART[key]
        hole |= np.hypot(X - hx, Y - hy) < hr - band
    r0, r1 = PART["ramp"][:2]
    slope = (X > r0 + band) & (X < r1 - band)
    gc, gw, _ = PART["groove"]
    groove = np.abs(X - gc) < gw
    rib = (X > PART["rib"][0] + band) & (X < PART["rib"][1] - band)
    flat = ~(edge | hole | slope | groove | rib) & (X > PART["block"][0] + band)
    flat &= ~((X > r0 - band) & (X < r1 + band)) & ~(np.abs(X - gc) < gw + band)
    return {"flat": flat, "edge": edge, "hole": hole, "slope": slope, "groove": groove,
            "rib": rib, "z": z}


# --------------------------------------------------------------------------- #
# 材質
# --------------------------------------------------------------------------- #
#: rho = 拡散の反射率、ks = 鏡面の反射率(Fresnel の F0)、m = Beckmann の粗さ、tex = 模様のコントラスト、
#: aniso = 筋(加工の送り)の向きの伸び、sss = 内部散乱の広がり [mm](0 = 無し)、mic = 細かい傾きの揺らぎ [rad]
MATERIALS = {
    "matte": {"ja": "つや消し", "rho": 0.70, "ks": 0.02, "m": 0.35, "tex": 0.10, "aniso": 1.0,
              "sss": 0.0, "mic": 0.0},
    "metal": {"ja": "金属光沢", "rho": 0.06, "ks": 0.90, "m": 0.12, "tex": 0.15, "aniso": 20.0,
              "sss": 0.0, "mic": 0.03},
    "resin": {"ja": "半透明の樹脂", "rho": 0.80, "ks": 0.04, "m": 0.05, "tex": 0.05, "aniso": 1.0,
              "sss": 0.25, "mic": 0.0},
    "black": {"ja": "黒", "rho": 0.04, "ks": 0.04, "m": 0.15, "tex": 0.10, "aniso": 1.0,
              "sss": 0.0, "mic": 0.0},
}
MAT_ORDER = ("matte", "metal", "resin", "black")


#: 受入試験の試験体(VDI/VDE 2634 Part 2 の考え方の球・ダンベル・平面を、この視野に入る大きさで):
#: 平らな板(高さ 0)の上に直径 8 mm の球を 2 つ、中心の間隔 20 mm(中心は板の面の高さ = 上半分が見える)
ART_SPHERE_D = 8.0
ART_CENTERS = ((10.0, 6.0), (30.0, 6.0))
#: 試験体の視野の縦 [mm](球が入る幅だけにして計算を半分にする)
ART_H_MM = 12.0


def artifact_height(pitch):
    """受入試験の試験体の高さの図 [mm]。"""
    X, Y = grid(pitch)
    z = np.zeros_like(X)
    r = ART_SPHERE_D / 2
    for cx, cy in ART_CENTERS:
        d2 = (X - cx) ** 2 + (Y - cy) ** 2
        m = d2 < r ** 2
        z[m] = np.maximum(z[m], np.sqrt(r ** 2 - d2[m]))
    return z


class Scene:
    """部品 1 つ × 材質 1 つを細かい格子で持つ(高さ・法線・模様)。``kind="artifact"`` は受入試験の試験体。"""

    def __init__(self, mat_key, seed=0, kind="part"):
        self.key = mat_key
        self.mat = MATERIALS[mat_key]
        self.kind = kind
        self.truth = part_height if kind == "part" else artifact_height
        self.has_groove = kind == "part"
        self.h = self.truth(FINE)
        rng = np.random.default_rng(1000 + seed)
        ny, nx = self.h.shape
        # 模様: 帯域を絞った乱数(筋は y に伸ばす = 送りの向き)。細かい格子 2〜3 標本の粒。
        s = 1.2 / (FINE / 0.025)
        t = ndi.gaussian_filter(rng.normal(size=(ny, nx)), (s * self.mat["aniso"], s))
        t /= t.std() + 1e-12
        self.albedo = self.mat["rho"] * np.clip(1.0 + self.mat["tex"] * t, 0.05, None)
        hx = np.gradient(self.h, FINE, axis=1)
        hy = np.gradient(self.h, FINE, axis=0)
        if self.mat["mic"] > 0:
            u = ndi.gaussian_filter(rng.normal(size=(ny, nx)), (s * self.mat["aniso"], s))
            hx = hx + self.mat["mic"] * u / (u.std() + 1e-12)
        n = np.stack([-hx, -hy, np.ones_like(hx)], axis=-1)
        self.n = n / np.linalg.norm(n, axis=-1, keepdims=True)


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def brdf_cos(scene, light, view, irr=1.0):
    """入射の向き ``light``(面から光源へ)・視線 ``view``(面からカメラへ)の放射輝度(余弦を掛けた BRDF)。

    Lambert(拡散)+ Beckmann の微小面(鏡面)。Fresnel は Schlick、遮蔽は Cook–Torrance の G。
    戻りは (拡散, 鏡面) の 2 枚(どちらも照度 ``irr`` を掛けた値)。
    """
    n = scene.n
    L, V = unit(light), unit(view)
    H = unit(L + V)
    ci = np.clip(n @ L, 0.0, None)
    co = np.clip(n @ V, 1e-4, None)
    ch = np.clip(n @ H, 1e-4, 1.0)
    m = scene.mat["m"]
    tan2 = (1.0 - ch ** 2) / ch ** 2
    D = np.exp(-tan2 / m ** 2) / (np.pi * m ** 2 * ch ** 4)
    vh = max(float(V @ H), 1e-4)
    F0 = scene.mat["ks"]
    F = F0 + (1.0 - F0) * (1.0 - float(L @ H)) ** 5
    G = np.minimum(1.0, np.minimum(2 * ch * co / vh, 2 * ch * ci / vh))
    spec = F * D * G / (4.0 * co) * (ci > 0)
    diff = scene.albedo / np.pi * ci
    return irr * diff, irr * spec


def sss_blur(img, scene, shift_xy=(0.0, 0.0)):
    """半透明の樹脂: 入った光が中でにじんで出る(指数の核、広がり ``sss``)。拡散の成分だけに掛ける。

    ★核の中心を光の入る向きに少しずらす(斜めに入った光は奥へ進んでから広がる)。
    """
    ell = scene.mat["sss"]
    if ell <= 0:
        return img
    r = int(np.ceil(5 * ell / FINE))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1] * FINE
    k = np.exp(-np.hypot(xx - shift_xy[0], yy - shift_xy[1]) / ell)
    k /= k.sum()
    from scipy.signal import fftconvolve
    return fftconvolve(np.pad(img, r, mode="edge"), k, mode="same")[r:-r, r:-r]


def visible_xz(h, angle_deg):
    """x-z 面内の向きから見えるか(光が届くか)。``angle_deg`` > 0 = +x の側に傾いた視点(光源)。

    行ごとに ``g(x) = h(x)·tan a − x`` の右側の累積最大と比べる(格子の上で厳密な地平線の判定)。
    """
    a = np.radians(abs(angle_deg))
    if a < 1e-9:
        return np.ones(h.shape, bool)
    xs = (np.arange(h.shape[1]) + 0.5) * FINE
    hh = h if angle_deg > 0 else h[:, ::-1]
    g = hh * np.tan(a) - xs[None, :]
    rmax = np.maximum.accumulate(g[:, ::-1], axis=1)[:, ::-1]
    nxt = np.concatenate([rmax[:, 1:], np.full((h.shape[0], 1), -np.inf)], axis=1)
    vis = g >= nxt - 1e-9
    return vis if angle_deg > 0 else vis[:, ::-1]


def oblique_resample(h, value, angle_deg, shift_mm=0.0):
    """x-z 面内で ``angle_deg`` 傾いた正射影カメラの像(細かい格子のまま)。

    像の座標 ``u' = x − z·tan a + shift``(z = 0 の面は真上のカメラと同じ所に写る)。見える標本だけを
    ``u'`` の順に並べて線形に補間する(壁は上端と下端の間を埋める)。
    """
    vis = visible_xz(h, angle_deg)
    t = np.tan(np.radians(angle_deg))
    xs = (np.arange(h.shape[1]) + 0.5) * FINE
    out = np.zeros_like(value)
    for r in range(h.shape[0]):
        v = vis[r]
        u = xs[v] - h[r, v] * t + shift_mm
        out[r] = np.interp(xs, u, value[r, v], left=0.0, right=0.0)
    return out


def box(img, s=SS):
    """細かい標本を s×s で足して 1 画素にする(画素の開口)。"""
    ny, nx = img.shape[0] // s, img.shape[1] // s
    return img[:ny * s, :nx * s].reshape(ny, s, nx, s, *img.shape[2:]).mean(axis=(1, 3))


#: カメラ: 満杯 10,000 電子、読み出し 6 電子、12 bit。露光は「上位 0.5 % が満杯の 9 割」まで上げる
#: 自動露光、ただし同じ方式のつや消しの露光の 8 倍まで(タクトの上限)。
FULL_WELL = 10000.0
READ_E = 6.0
BITS = 12
EXPOSURE_CAP = 8.0


def expose(radiance_stack, ref_gain=None):
    """放射輝度 → 電子数の倍率(自動露光)。``ref_gain`` = つや消しの倍率(上限の基準)。"""
    p = float(np.percentile(np.asarray(radiance_stack), 99.5))
    g = 0.9 * FULL_WELL / max(p, 1e-12)
    if ref_gain is not None:
        g = min(g, EXPOSURE_CAP * ref_gain)
    return g


#: レンズ: 点像のぼけ σ [画素](回折と収差をまとめたガウス)と、像の隅の周辺減光(cos⁴ 則の近似で隅が 0.8)
LENS_PSF_PX = 0.6
VIGNETTE_CORNER = 0.8


def lens(radiance):
    """レンズを通した像: 点像のぼけと周辺減光(像の中心からの距離の 2 乗で落ちる)。"""
    a = ndi.gaussian_filter(np.asarray(radiance, float), LENS_PSF_PX, mode="nearest")
    ny, nx = a.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    r2 = ((xx - (nx - 1) / 2) / (nx / 2)) ** 2 + ((yy - (ny - 1) / 2) / (ny / 2)) ** 2
    return a * (1.0 - (1.0 - VIGNETTE_CORNER) * r2 / 2.0)


def sensor(radiance, gain, rng, optics=True):
    """レンズ(ぼけ・周辺減光)を通し、電子数にしてショット・読み出し雑音を足し、12 bit に量子化する。

    戻りは [0, 1](1 = 飽和)。"""
    e = np.clip((lens(radiance) if optics else radiance) * gain, 0.0, None)
    e = rng.poisson(np.minimum(e, 4 * FULL_WELL)).astype(np.float64) + rng.normal(0.0, READ_E, e.shape)
    dn = np.clip(np.round(e / FULL_WELL * (2 ** BITS - 1)), 0, 2 ** BITS - 1)
    return dn / (2 ** BITS - 1)


def brdf_pairs(scene, idx, light_dirs, view):
    """標本 ``idx``(平らな添字)ごとに別の入射の向き ``light_dirs`` (n, 3) の放射輝度の係数(拡散 + 鏡面)。"""
    n = scene.n.reshape(-1, 3)[idx]
    alb = scene.albedo.reshape(-1)[idx]
    L = light_dirs / np.linalg.norm(light_dirs, axis=1, keepdims=True)
    V = unit(view)
    H = L + V
    H /= np.linalg.norm(H, axis=1, keepdims=True)
    ci = np.clip((n * L).sum(1), 0.0, None)
    co = np.clip(n @ V, 1e-4, None)
    ch = np.clip((n * H).sum(1), 1e-4, 1.0)
    m = scene.mat["m"]
    D = np.exp(-((1 - ch ** 2) / ch ** 2) / m ** 2) / (np.pi * m ** 2 * ch ** 4)
    vh = np.clip(H @ V, 1e-4, None)
    F0 = scene.mat["ks"]
    F = F0 + (1 - F0) * (1 - np.clip((L * H).sum(1), 0, 1)) ** 5
    G = np.minimum(1.0, np.minimum(2 * ch * co / vh, 2 * ch * ci / vh))
    return alb / np.pi * ci + F * D * G / (4 * co) * (ci > 0)


def specular_bounce(scene, travel_xz, lit, view, step=None, max_mm=12.0):
    """金属の鏡面の 1 回反射(x-z 面内、行ごと)。光の進む向き ``travel_xz`` で ``lit`` の標本に当たった光が
    鏡の向きへ跳ね、同じ行の別の標本 j に当たって、そこから ``view`` の向きへ出る分。

    戻り: ``(src, dst, coef, path_mm)`` —— 平らな添字の対と、j の放射輝度への係数(入射の照度 1 あたり)、
    i → j の距離 [mm]。★粗さの山の広がりは 3 本の光線(鏡の向きと ±m)で近似する。穴の壁のように
    法線が y を向く面の反射は行の外へ出るので扱わない(近似)。
    """
    h = scene.h
    ny, nx = h.shape
    step = step or max(FINE, 0.05)        # 0.05 mm 刻みで辿る(当たりの位置の誤差は刻み以下)
    d = np.array([travel_xz[0], travel_xz[1]], float)
    d /= np.linalg.norm(d)
    nxz = scene.n[..., [0, 2]]
    nxz = nxz / np.linalg.norm(nxz, axis=-1, keepdims=True)
    F0 = scene.mat["ks"]
    m = scene.mat["m"]
    xs = (np.arange(nx) + 0.5) * FINE
    hmax = float(h.max()) + 0.01
    out = ([], [], [], [])
    for dth, wgt in ((-m, 0.25), (0.0, 0.5), (m, 0.25)):
        dn = (nxz * d).sum(-1)
        r = d[None, None, :] - 2 * dn[..., None] * nxz
        c, s = np.cos(dth), np.sin(dth)
        r = np.stack([c * r[..., 0] - s * r[..., 1], s * r[..., 0] + c * r[..., 1]], -1)
        # ★真上へ跳ねる光は高さの図(張り出しが無い)には二度と当たらないので辿らない(時間の大半がここだった)
        ok = lit & (r[..., 1] > 0.02) & (dn < 0) & (np.abs(r[..., 0]) > 0.02)
        rr, cc = np.nonzero(ok)
        if rr.size == 0:
            continue
        rx, rz = r[rr, cc, 0], r[rr, cc, 1]
        x0, z0 = xs[cc], h[rr, cc]
        hit = np.full(rr.size, -1)
        tl = np.zeros(rr.size)
        alive = np.ones(rr.size, bool)
        nsteps = int(max_mm / step)
        for k in range(2, nsteps):
            a = np.nonzero(alive)[0]
            if a.size == 0:
                break
            t = k * step
            xk = x0[a] + t * rx[a]
            zk = z0[a] + t * rz[a]
            ci = np.floor(xk / FINE).astype(int)
            inside = (ci >= 0) & (ci < nx) & (zk < hmax)
            alive[a[~inside]] = False
            a, ci, zk = a[inside], ci[inside], zk[inside]
            got = h[rr[a], ci] >= zk
            if got.any():
                g = a[got]
                hit[g] = ci[got]
                tl[g] = t
                alive[g] = False
        ok2 = hit >= 0
        if not ok2.any():
            continue
        src = rr[ok2] * nx + cc[ok2]
        dst = rr[ok2] * nx + hit[ok2]
        cos_i = -(nxz[rr[ok2], cc[ok2]] * d).sum(-1)
        Fi = F0 + (1 - F0) * (1 - np.clip(cos_i, 0, 1)) ** 5
        ldir = np.stack([-rx[ok2], np.zeros(int(ok2.sum())), -rz[ok2]], 1)
        coef = wgt * Fi * brdf_pairs(scene, dst, ldir, view)
        out[0].append(src)
        out[1].append(dst)
        out[2].append(coef)
        out[3].append(tl[ok2])
    if not out[0]:
        return (np.zeros(0, int),) * 2 + (np.zeros(0),) * 2
    return tuple(np.concatenate(o) for o in out)


_GROOVE_F = {}


def groove_form_factors(n):
    """V 溝(90°、押し出し)の形態係数 ``F[i, j]``(``lighttransport.form_factors_2d``)。"""
    if n not in _GROOVE_F:
        gw = PART["groove"][1]
        prof = lighttransport.groove_profile("vgroove", n_patches=int(n), width=2 * gw, angle_deg=90.0)
        F = lighttransport.form_factors_2d(prof)
        _GROOVE_F[n] = (np.asarray(F["F"] if isinstance(F, dict) else F, float), prof)
    return _GROOVE_F[n]


def groove_cols():
    gc, gw, _ = PART["groove"]
    xs = grid(FINE)[0][0]
    return np.nonzero(np.abs(xs - gc) < gw)[0]


def groove_interreflection(scene, irradiance):
    """V 溝の中の拡散の 1 回反射。``irradiance`` は細かい格子の照度(光源から直接)。

    戻りは溝の中で増える放射輝度(細かい格子)。溝は y に押し出した形なので全行で同じ形態係数。
    """
    if not scene.has_groove:
        return np.zeros_like(irradiance)
    cols = groove_cols()
    F, _ = groove_form_factors(cols.size)
    alb = scene.mat["rho"]
    B = alb * irradiance[:, cols]                          # 拡散の放射発散度 ρE
    add = np.zeros_like(irradiance)
    add[:, cols] = alb / np.pi * (B @ F.T)
    return add


# --------------------------------------------------------------------------- #
# 方式 1: 縞投影(位相シフト格子投影)
# --------------------------------------------------------------------------- #
FR_THETA = 30.0                 #: 投影の傾き [°](プロジェクタは -x の側、カメラは真上)
FR_PERIODS = (16.0, 4.0, 1.0)   #: 縞の周期(光線に直角に測った長さ)[mm]、粗 → 細
FR_STEPS = 4
FR_BLUR = 0.05                  #: 投影のぼけ σ [mm](縞の振幅を exp(−2π²σ²/P²) に落とす)
FR_BLACK = 0.02                 #: プロジェクタの黒(コントラスト 50:1)
FR_GAMMA_MIN = 0.10             #: これより変調度の低い画素は捨てる


def measure_fringe(scene, rng, gain_ref=None, keep_images=False):
    """縞投影で測る。戻り: ``{"z", "valid", "gain", ...}``(カメラの格子)。"""
    h = scene.h
    th = np.radians(FR_THETA)
    L = np.array([-np.sin(th), 0.0, np.cos(th)])
    vis = visible_xz(h, -FR_THETA)
    diff, spec = brdf_cos(scene, L, (0, 0, 1))
    cos_i = np.clip(scene.n @ L, 0, None)
    X = grid(FINE)[0]
    s = X * np.cos(th) + h * np.sin(th)
    shift = 0.5 * scene.mat["sss"] * np.sin(np.arcsin(np.sin(th) / 1.5))
    if scene.mat["ks"] >= 0.5:
        src, dst, coef, _ = specular_bounce(scene, (np.sin(th), -np.cos(th)), vis, (0, 0, 1))
    else:
        src = dst = np.zeros(0, int)
        coef = np.zeros(0)
    radiance = []
    for P in FR_PERIODS:
        for n in range(FR_STEPS):
            amp = 0.5 * np.exp(-2 * np.pi ** 2 * FR_BLUR ** 2 / P ** 2)
            patt = FR_BLACK + (1 - FR_BLACK) * (0.5 + amp * np.cos(2 * np.pi * s / P - 2 * np.pi * n / FR_STEPS))
            E = patt * vis
            if scene.mat["sss"] > 0:
                d_part = scene.albedo / np.pi * sss_blur(E * cos_i, scene, (shift, 0.0))
            else:
                d_part = diff * E
            img = d_part + spec * E + groove_interreflection(scene, E * cos_i)
            if src.size:
                img = img + np.bincount(dst, coef * patt.reshape(-1)[src],
                                        minlength=h.size).reshape(h.shape)
            radiance.append(box(img))
    radiance = np.stack(radiance)
    gain = expose(radiance, gain_ref)
    imgs = np.stack([sensor(r, gain, rng) for r in radiance])
    Xc = grid(PITCH)[0]
    k = FR_STEPS
    dphi = []
    for i, P in enumerate(FR_PERIODS):
        ph = fringe.wrapped_phase(imgs[i * k:(i + 1) * k])
        ref = 2 * np.pi * Xc * np.cos(th) / P
        dphi.append(np.angle(np.exp(1j * (ph - ref))))
    st = imgs[-k:]
    gam = fringe.modulation(st)
    a = dphi[0]
    for i in range(1, len(FR_PERIODS)):
        a = fringe.absolute_phase(dphi[i], a * FR_PERIODS[i - 1] / FR_PERIODS[i])
    kk = FR_PERIODS[-1] / (2 * np.pi * np.sin(th))
    z = fringe.phase_to_height(a, 0.0, kk)
    sat = (imgs >= 1.0).any(axis=0)
    mean = st.mean(0)
    valid = (gam >= FR_GAMMA_MIN) & ~sat & (mean > 0.005) & np.isfinite(z)
    # 閉形式の位相雑音(平らな所の検算用): σ_φ = √(2/N)·σ_I / b。σ_I は電子のショット + 読み出し + 量子化
    b = 2.0 / k * np.abs((st * np.exp(-2j * np.pi * np.arange(k) / k)[:, None, None]).sum(0))
    sig_I = np.sqrt(np.clip(mean, 0, None) * (2 ** BITS - 1) / (2 ** BITS - 1) * FULL_WELL + READ_E ** 2) / FULL_WELL
    sig_I = np.sqrt(sig_I ** 2 + (1 / (2 ** BITS - 1)) ** 2 / 12)
    return {"z": np.where(valid, z, np.nan), "valid": valid, "gain": gain, "sat": sat,
            "modulation": gam, "mean": mean, "images": imgs,
            "sigma_z_pred": kk * np.sqrt(2.0 / k) * sig_I / np.maximum(b, 1e-9)}


# --------------------------------------------------------------------------- #
# 方式 2: 間接 ToF
# --------------------------------------------------------------------------- #
TOF_PITCH = 0.4          #: ToF の画素が部品の上で占める幅 [mm](VGA 級の ToF を近くに置いた想定)
TOF_F = 100e6            #: 変調周波数
TOF_STANDOFF = 400.0     #: カメラから台の面まで [mm]
TOF_SIGNAL = 4.0e5       #: 白い Lambert 面(反射率 1)1 画素の 1 測定の信号電子(4 段の合計)
TOF_AMBIENT = 0.5e5      #: 背景光の電子(1 測定)
TOF_READ = 20.0
#: ToF も露光(積分時間)をカメラと同じ規則で決める: 雑音なしの上位 0.5 % のバケットが満杯の 9 割になる倍率、
#: ただしつや消しの倍率の EXPOSURE_CAP 倍まで。満杯はつや消しが倍率 1 で 9 割になる所に置く
#: (★前の版は ToF だけ露光が固定で「露光を上げられない」と書いていた —— 条件の差で勝ち負けを作っていた)
TOF_N_REF = 1.5          #: 樹脂の屈折率(内部散乱の遅れ = 屈折率 × 広がり)


def measure_tof(scene, rng, sat_ref=None):
    """間接 ToF(光源とカメラは同じ所、真上)。戻り: ``{"z", "valid", ...}``(ToF の格子)。

    ``sat_ref`` = つや消しで決めた満杯の電子数(None ならこの材質で決める = つや消しの実行)。"""
    h = scene.h
    up = np.array([0.0, 0.0, 1.0])
    diff, spec = brdf_cos(scene, up, up)
    ss = int(round(TOF_PITCH / FINE))
    depth = (TOF_STANDOFF - h) / 1000.0
    paths_d, paths_a = [], []
    if scene.mat["sss"] > 0:
        # 中で散った光は遅れて出る: 拡散の分を「奥にずれた経路」として足し、直接の経路は表面の鏡面だけ
        d_part = sss_blur(diff, scene)
        refl = np.pi * spec
        paths_d.append(depth + TOF_N_REF * scene.mat["sss"] / 1000.0)
        paths_a.append(np.pi * d_part)
    else:
        refl = np.pi * (diff + spec)
    # V 溝の中の拡散の 1 回反射: 画素ごとにフェーザを足して 1 本の等価な経路にする(溝の無い試験体では 0)
    cols = groove_cols() if scene.has_groove else np.zeros(0, int)
    k4 = 4 * np.pi * TOF_F / 299_792_458.0
    gd = depth.copy()
    ga = np.zeros_like(h)
    if cols.size:
        F, _ = groove_form_factors(cols.size)
        cz = h[:, cols]
        Eg = np.clip(scene.n[:, cols] @ up, 0, None)
        alb = scene.mat["rho"]
        # 光源 → j(下りの長さ)、j → i、i → カメラ。距離の半分を経路にする(行ごとに同じ形)
        cx = (cols + 0.5) * FINE
        zc = cz[0]
        dij = np.hypot(cx[:, None] - cx[None, :], zc[:, None] - zc[None, :])
        half = ((TOF_STANDOFF - zc)[None, :] + dij + (TOF_STANDOFF - zc)[:, None]) / 2.0 / 1000.0
        amp_ij = alb * F * (alb * Eg[0])[None, :]               # i が受けて出す分(反射率の係数)
        ph = (amp_ij * np.exp(1j * k4 * half)).sum(1)
        gd[:, cols] = (np.angle(ph) % (2 * np.pi)) / k4
        ga[:, cols] = np.abs(ph)
    paths_d.append(gd)
    paths_a.append(ga)
    if scene.mat["ks"] >= 0.5:
        vis = np.ones(h.shape, bool)
        src, dst, coef, tl = specular_bounce(scene, (0.0, -1.0), vis, up)
        sd = np.zeros(h.size)
        sa = np.zeros(h.size)
        if src.size:
            hs = h.reshape(-1)
            plen = ((TOF_STANDOFF - hs[src]) + tl + (TOF_STANDOFF - hs[dst])) / 2.0 / 1000.0
            pz = np.bincount(dst, np.pi * coef * np.exp(1j * k4 * plen).real, minlength=h.size) \
                + 1j * np.bincount(dst, np.pi * coef * np.exp(1j * k4 * plen).imag, minlength=h.size)
            sa = np.abs(pz)
            sd = np.where(sa > 0, (np.angle(pz) % (2 * np.pi)) / k4, depth.reshape(-1))
        paths_d.append(sd.reshape(h.shape))
        paths_a.append(sa.reshape(h.shape))
    kw = dict(reflectivity=refl, frequencies_hz=(TOF_F,), n_phases=4, demod_contrast=0.5, read_noise_e=TOF_READ,
              paths_depth=np.stack(paths_d), paths_amplitude=np.stack(paths_a), supersample=ss)
    probe = itof.itof_capture(depth, signal_electrons=TOF_SIGNAL, ambient_electrons=TOF_AMBIENT, noise=False, **kw)
    p995 = float(np.percentile(probe["mean_samples"].max(axis=(0, 1)), 99.5))
    if sat_ref is None:
        sat_ref = p995 / 0.9
        gain = 1.0
    else:
        gain = min(0.9 * sat_ref / max(p995, 1e-12), EXPOSURE_CAP)
    cap = itof.itof_capture(depth, signal_electrons=TOF_SIGNAL * gain, ambient_electrons=TOF_AMBIENT * gain,
                            noise=True, seed=int(rng.integers(1 << 30)), **kw)
    smp = cap["samples"]
    sat = (cap["mean_samples"] >= sat_ref).any(axis=(0, 1))
    smp = np.minimum(smp, sat_ref)
    pa = itof.itof_phase_amplitude(smp, (TOF_F,))
    d = np.asarray(pa["wrapped_depth"])[0]
    A = np.asarray(pa["amplitude"])[0]
    dsig = np.asarray(pa["depth_sigma"])[0] if np.ndim(pa["depth_sigma"]) else np.full(d.shape, float(pa["depth_sigma"]))
    z = TOF_STANDOFF - 1000.0 * d
    fly = np.asarray(itof.itof_flying_pixel_mask(d, threshold_m=0.0005, radius=1)) > 0.5
    valid = ~sat & (A > 6 * np.sqrt(gain * TOF_AMBIENT / 4 + TOF_READ ** 2)) & np.isfinite(z)
    return {"z_raw": np.where(valid, z, np.nan), "z": np.where(valid & ~fly, z, np.nan),
            "valid": valid & ~fly, "valid_raw": valid, "fly": fly & valid, "sat": sat, "amp": A,
            "sat_ref": sat_ref, "gain": gain, "depth_sigma_mm": 1000.0 * dsig, "true_mixed": cap.get("mixed"),
            "refl_flat": refl}


# --------------------------------------------------------------------------- #
# 方式 3: 光切断(レーザーのシート光)
# --------------------------------------------------------------------------- #
LS_CAM = 30.0            #: カメラの傾き [°](+x の側)。シート光は鉛直に下ろす
LS_SIGMA = 0.10          #: シート光の太さ σ [mm](1/e² の半幅 0.2 mm)。★0.05 mm(カメラの 0.5〜1 画素)では
#: 重心が画素の格子へ引き寄せられ、平らな面で ±0.03 mm の偏りが出た(画素の固着)。光条を 2 画素以上に写すのが定石
LS_LAMBDA_UM = 0.65
LS_SIN_U = 0.02          #: 観察側の開口 sin u
LS_PEAK_MIN = 0.02       #: 列の最大がこれ(満杯の比)未満なら光条なしとする
LS_AMBIENT = 0.02        #: 部屋の明かり(光条の頂の照度に対する比)


LS_DX_UM = 4.0           #: スペックルを描く細かさ [µm](強度の帯域 2·sin u/λ = 0.062 /µm のナイキスト 8.1 µm の半分。7.5 µm では床の比が 0.39〜0.46 に動いた)


def speckle_grain_mm():
    """スペックルの粒の大きさ λ/(2 sin u) [mm](観察側の開口で決まる)。"""
    return LS_LAMBDA_UM / (2 * LS_SIN_U) / 1000.0


def coherent_speckle(ideal, rng):
    """光条の像(``(u', 行)``、画素ごとの強度)にコヒーレント結像のスペックルを載せる。

    ★2026-11-08 の敵対的レビューの指摘で作り直した。前の版は画素ごとに独立なガンマ乱数(粒の数 M)で、
    画素を大きくすると雑音が 1/√M で消え、Dorsch の床より下(比 0.52)まで下がった —— 物理では
    スペックルの重心のゆらぎは観察側の開口で決まり、画素で平均しても消えない。

    手順(列 = 1 行の光条、像の縦 u' に沿って 1 次元): 画素の強度を ``LS_DX_UM`` の細かさへ線形に
    補い、振幅に一様乱数の位相を掛け(粗い面)、瞳(遮断の空間周波数 sin u/λ)で帯域を切ってから
    ``|E|²`` を画素へ戻す。行の高さ(画素の幅)の中にある粒の数だけ独立な場を描いて平均する
    (光条に沿う向きの積分)。光の無い所は描かない(光がある u' の範囲だけを切り出す)。
    """
    nu, nr = ideal.shape
    lit = ideal.max(axis=1) > 1e-6 * max(float(ideal.max()), 1e-30)
    if not lit.any():
        return ideal
    idx = np.nonzero(lit)[0]
    a, b = max(0, idx[0] - 6), min(nu, idx[-1] + 7)
    part = ideal[a:b]
    os_ = max(2, int(np.ceil(1000.0 * PITCH / LS_DX_UM)))
    dx_um = 1000.0 * PITCH / os_
    n = part.shape[0] * os_
    uf = (np.arange(n) + 0.5) / os_ - 0.5
    # 画素の中心のあいだを線形に補う(列ごとの np.interp と同じ値を、添字の算術でまとめて)
    ufc = np.clip(uf, 0.0, part.shape[0] - 1.0)
    i0 = np.minimum(np.floor(ufc).astype(int), part.shape[0] - 2) if part.shape[0] > 1 else np.zeros(n, int)
    wgt = (ufc - i0)[:, None]
    fine = part[i0] * (1.0 - wgt) + part[np.minimum(i0 + 1, part.shape[0] - 1)] * wgt
    from scipy import fft as sfft
    amp = np.sqrt(np.clip(fine, 0, None)).astype(np.float32)
    freq = np.fft.fftfreq(n, d=dx_um)
    # ★u' は像の座標を cos a で割った座標(u' = x − z·tan a)。瞳の遮断の空間周波数 sin u/λ は像の座標での値なので、
    #   u' では cos a 倍にする(掛けないと粒が cos 30° = 0.87 倍細かくなり、雑音が低く出る。2026-11-08 の再レビュー)
    keep = np.abs(freq) <= np.cos(np.radians(LS_CAM)) * LS_SIN_U / LS_LAMBDA_UM
    ky = max(1, int(round(PITCH / speckle_grain_mm())))
    out = np.zeros(fine.shape)
    for _ in range(ky):
        # 単精度で描く(倍精度の 3 倍速い。強度の相対誤差 1e-6 程度で、雑音の床の比には効かない)
        E = amp * np.exp(np.float32(2 * np.pi) * 1j * rng.random(amp.shape, dtype=np.float32))
        Ef = sfft.fft(E, axis=0, workers=-1)
        Ef[~keep] = 0
        out += np.abs(sfft.ifft(Ef, axis=0, workers=-1)) ** 2
    out /= ky * (keep.sum() / n)                     # 瞳が通した分のエネルギーで割り、平均の明るさを保つ
    res = ideal.copy()
    res[a:b] = out.reshape(part.shape[0], os_, nr).mean(axis=1)
    return res


def measure_laser(scene, rng, gain_ref=None, frames=None, keep_frames=()):
    """光切断で測る。シート光を x に 1 画素ずつ送り、各コマの列ごとの光条の中心から高さを出す。

    戻り: ``{"z", "valid", ...}``(カメラの格子、x = シート光の位置)。``keep_frames`` のコマの像も返す(float32)。
    """
    h = scene.h
    ny, nx = h.shape
    t = np.tan(np.radians(LS_CAM))
    up = np.array([0.0, 0.0, 1.0])
    V = np.array([np.sin(np.radians(LS_CAM)), 0.0, np.cos(np.radians(LS_CAM))])
    vis_cam = visible_xz(h, LS_CAM)
    diff, spec = brdf_cos(scene, up, V)
    diff_amb = scene.albedo / np.pi
    cos_i = np.clip(scene.n @ up, 0, None)
    xs = (np.arange(nx) + 0.5) * FINE
    nyc = ny // SS
    # 像の縦(u')の範囲: 部品全体。カメラの格子は PITCH
    u0 = -float(h.max()) * t - 1.0
    nu = int(np.ceil((W_MM - u0 + 1.0) / PITCH))
    if scene.mat["ks"] >= 0.5:
        src, dst, coef, _ = specular_bounce(scene, (0.0, -1.0), np.ones(h.shape, bool), V)
        keep = vis_cam.reshape(-1)[dst]
        src, dst, coef = src[keep], dst[keep], coef[keep]
    else:
        src = dst = np.zeros(0, int)
        coef = np.zeros(0)
    srcx = src % nx if src.size else src
    ncols = int(round(W_MM / PITCH))
    xk_all = (np.arange(ncols) + 0.5) * PITCH
    if frames is None:
        frames = np.arange(ncols)
    ell = scene.mat["sss"]
    half = int(np.ceil(max(4 * LS_SIGMA, 5 * ell) / FINE)) + 2
    ucoord = xs[None, :] - h * t                       # 各標本が写る u'
    upos = (ucoord - u0) / PITCH                       # 像の縦の位置 [画素]
    rowc = (np.arange(ny) // SS)[:, None] * np.ones((1, nx), int)
    wfp = FINE / PITCH                                 # 標本 1 つの足跡の幅 [画素]

    def splat(rc, p, val):
        # ★標本の足跡(幅 FINE)を、重なる 2 つの画素へ重なりの比で分ける。点で 1 画素へ落とすと、
        #   細い光条の中心が画素の格子へ引き寄せられる(シミュの都合で出る偽の偏り、最大 0.04 mm を実測)。
        lo = p - 0.5 * wfp
        b = np.floor(lo).astype(int)
        fl = np.clip((b + 1 - lo) / wfp, 0.0, 1.0)
        ok0 = (b >= 0) & (b < nu)
        ok1 = (b + 1 >= 0) & (b + 1 < nu)
        out = np.bincount(rc[ok0] * nu + b[ok0], val[ok0] * fl[ok0], minlength=nyc * nu)
        out += np.bincount(rc[ok1] * nu + b[ok1] + 1, val[ok1] * (1 - fl[ok1]), minlength=nyc * nu)
        return out

    def sheet(xc, xk):
        # 標本の足跡の上で平均したシート光の強さ(ガウスの積分)
        from scipy.special import ndtr
        a = (xc - 0.5 * FINE - xk) / LS_SIGMA
        b = (xc + 0.5 * FINE - xk) / LS_SIGMA
        return (ndtr(b) - ndtr(a)) * LS_SIGMA * np.sqrt(2 * np.pi) / FINE

    def frame_image(xk):
        c0 = max(0, int(xk / FINE) - half)
        c1 = min(nx, int(xk / FINE) + half + 1)
        G = sheet(xs[c0:c1], xk)[None, :] * np.ones((ny, 1))
        E = G * cos_i[:, c0:c1]
        if ell > 0:
            k = np.exp(-np.abs(np.arange(-half, half + 1) * FINE) / ell)
            k /= k.sum()
            Ed = ndi.convolve1d(np.pad(E, ((0, 0), (half, half))), k, axis=1, mode="constant")
            lo, hi = c0 - half, c1 + half
            a0, a1 = max(0, lo), min(nx, hi)
            Ed = Ed[:, a0 - lo:Ed.shape[1] - (hi - a1)]
            rad = scene.albedo[:, a0:a1] / np.pi * Ed
            sl = slice(a0, a1)
            rad = rad + np.pad(spec[:, c0:c1] * G, ((0, 0), (c0 - a0, a1 - c1)))
        else:
            sl = slice(c0, c1)
            rad = (diff[:, c0:c1] + spec[:, c0:c1]) * G
        v = vis_cam[:, sl]
        img = splat(rowc[:, sl][v], upos[:, sl][v], rad[v])
        if src.size:
            sel = np.abs(srcx * FINE + 0.5 * FINE - xk) < 4 * LS_SIGMA
            if sel.any():
                s_, d_ = src[sel], dst[sel]
                gs = sheet(xs[s_ % nx], xk)
                img = img + splat(d_ // nx // SS, upos.reshape(-1)[d_], coef[sel] * gs)
        return img.reshape(nyc, nu).T / (SS * SS)        # (u', 行)

    # 自動露光: 部品の数か所のコマで決める(雑音なしの像の上位 0.5 %)
    probe = [frame_image(x) for x in xk_all[:: max(1, ncols // 24)]]
    gain = expose(np.stack(probe), gain_ref)
    # 部屋の明かり(光条の頂の LS_AMBIENT 倍の照度で一様に照らす)。見える面がうっすら写る
    v_all = vis_cam
    ambient = splat(rowc[v_all], upos[v_all], (LS_AMBIENT * diff_amb)[v_all]).reshape(nyc, nu).T / (SS * SS)
    z = np.full((nyc, ncols), np.nan)
    amb_img = sensor(ambient, gain, rng, optics=False)
    kept, kept_ids = [], []
    keep_set = set(int(k) for k in keep_frames)
    for f in frames:
        xk = xk_all[f]
        ideal = frame_image(xk)
        # ★レンズのぼけは光切断ではコヒーレントな瞳(coherent_speckle の中)で入れてあるので、二重に掛けない
        img = sensor(coherent_speckle(ideal, rng) + ambient, gain, rng, optics=False)
        if int(f) in keep_set:
            kept.append(img.astype(np.float32))
            kept_ids.append(int(f))
        # 部屋の明かりの分は、レーザーを消して撮った 1 枚(amb_img)を引く(光切断の装置の定石)
        sub = np.clip(img - amb_img, 0.0, None)
        if not (sub.max() > 0):            # 光条がどこにも写らないコマ(全部が影)
            continue
        # 重心の窓は光条の ±3σ(画素の数で固定すると、細かい画素で光条の裾を切って画素の格子へ引き寄せる:
        #   0.05 mm・±3 画素で平らな板が 41 µm ずれた)
        tab = lightsection.laser_line_center_centroid(sub, min_peak_rel=0.0,
                                                       half_window=int(np.ceil(3 * LS_SIGMA / PITCH)))
        row = np.asarray(tab["row"], float)
        ok = np.asarray(tab["valid"], bool) & (np.asarray(tab["peak"], float) >= LS_PEAK_MIN)
        uc = u0 + (row + 0.5) * PITCH
        z[:, f] = np.where(ok, (xk - uc) / t, np.nan)
    valid = np.isfinite(z)
    return {"z": z, "valid": valid, "gain": gain, "frames": kept, "kept_ids": kept_ids, "u0": u0}


# --------------------------------------------------------------------------- #
# 方式 4: 照度差ステレオ
# --------------------------------------------------------------------------- #
PS_EL = 45.0          #: 照明の仰角 [°]
PS_N = 8              #: 照明の数(方位 45° おき)


def ps_lights():
    az = np.radians(np.arange(PS_N) * 360.0 / PS_N)
    el = np.radians(PS_EL)
    return np.stack([np.cos(az) * np.cos(el), np.sin(az) * np.cos(el), np.full(PS_N, np.sin(el))], 1)


def cast_shadow(h, light, step):
    """光源の向き ``light`` へ高さの図を辿り、遮られる標本を印す(細かい格子)。"""
    lx, ly, lz = light
    horiz = np.hypot(lx, ly)
    tan_e = lz / horiz
    ny, nx = h.shape
    lit = np.ones(h.shape, bool)
    hmax = float(h.max())
    nsteps = int(np.ceil((hmax - h.min()) / tan_e / step)) + 1
    for k in range(1, nsteps + 1):
        dx = int(round(k * step * lx / horiz / FINE))
        dy = int(round(k * step * ly / horiz / FINE))
        rise = k * step * tan_e
        sh = np.zeros_like(h)
        ys = slice(max(0, -dy), min(ny, ny - dy))
        xsl = slice(max(0, -dx), min(nx, nx - dx))
        yd = slice(max(0, dy), min(ny, ny + dy))
        xd = slice(max(0, dx), min(nx, nx + dx))
        sh[ys, xsl] = h[yd, xd]
        lit &= ~(sh > h + rise + 1e-9)
    return lit


def measure_ps(scene, rng, gain_ref=None):
    """照度差ステレオ(8 灯、真上のカメラ)。法線 → Frankot–Chellappa の積分で高さ(定数は真値に合わせる)。"""
    h = scene.h
    lights = ps_lights()
    rad = []
    for Ld in lights:
        lit = cast_shadow(h, Ld, FINE * 2)
        diff, spec = brdf_cos(scene, Ld, (0, 0, 1))
        if scene.mat["sss"] > 0:
            cos_i = np.clip(scene.n @ Ld, 0, None)
            shift = -0.5 * scene.mat["sss"] * np.sin(np.arcsin(np.cos(np.radians(PS_EL)) / 1.5))
            d_part = scene.albedo / np.pi * sss_blur(cos_i * lit, scene, (shift * Ld[0] / np.hypot(Ld[0], Ld[1]),
                                                                        shift * Ld[1] / np.hypot(Ld[0], Ld[1])))
        else:
            d_part = diff * lit
        rad.append(box(d_part + spec * lit))
    rad = np.stack(rad)
    gain = expose(rad, gain_ref)
    imgs = np.stack([sensor(r, gain, rng) for r in rad])
    normals, albedo, inl = fs.photometric_stereo_robust(imgs, lights, method="ransac", threshold=0.05, seed=0)
    normals = np.asarray(normals, float)
    albedo = np.asarray(albedo, float)
    # 解けなかった画素(NaN = 3 灯の部分集合が合意しない)は欠測。積分には真上の法線で埋めて渡す
    valid = np.isfinite(albedo) & np.isfinite(normals).all(-1) & (np.nan_to_num(albedo) > 1e-3)
    filled = np.where(valid[..., None], np.nan_to_num(normals), np.array([0.0, 0.0, 1.0]))
    zrel = np.asarray(photometric.integrate_normals(filled)) * PITCH
    return {"z_rel": zrel, "valid": valid, "gain": gain, "images": imgs, "normals": normals}


# --------------------------------------------------------------------------- #
# 方式 5: ステレオ(受動、ドーム照明)
# --------------------------------------------------------------------------- #
#: 2 台のカメラの傾き ±[°]。★±15°(輻輳 30°)にして、縞投影・光切断の三角測量の角 30° と揃える
#: (前の版は ±5° で、ステレオだけ三角測量の角が 3 分の 1 だった。条件の差で負けを作らない)
ST_ANGLE = 15.0
ST_ZOFF = 1.0         #: 視差を正にするための高さのずらし [mm]


def measure_stereo(scene, rng, gain_ref=None):
    """2 台の正射影カメラ(±``ST_ANGLE``° = ±15°)で撮り ``binocular_disparity_ms`` で視差 → 高さ。x の格子へ並べ直す。"""
    h = scene.h
    t = np.tan(np.radians(ST_ANGLE))
    # 照明: ドーム(一様な天空、7 割)+ 斜め上の 1 灯(3 割)。ドームの分は拡散 = ρ、鏡面は一様な天空を映すだけ
    # なので F(=ks)の一定値。1 灯の分は面の傾きで陰影がつき、金属では見る向きで変わる光り(2 台で違う)が出る
    base = scene.albedo.copy()
    if scene.mat["sss"] > 0:
        base = sss_blur(base, scene)
    dome = 0.7 * (base / np.pi + scene.mat["ks"] / np.pi)
    Lk = unit((-0.40, -0.30, 0.87))
    views = []
    for ang in (-ST_ANGLE, ST_ANGLE):
        V = (np.sin(np.radians(ang)), 0.0, np.cos(np.radians(ang)))
        dk, sk = brdf_cos(scene, Lk, V)
        if scene.mat["sss"] > 0:
            # 顔料も中の散乱でにじむ: 模様ごと散乱の核で均す(模様を均さないと、無いはずの模様で対応が取れる)
            dk = sss_blur(scene.albedo * np.clip(scene.n @ Lk, 0, None), scene) / np.pi
        views.append(dome + 0.3 * np.pi * (dk + sk))
    left = box(oblique_resample(h, views[0], -ST_ANGLE))
    right = box(oblique_resample(h, views[1], ST_ANGLE, shift_mm=-2 * ST_ZOFF * t))
    gain = expose(np.stack([left, right]), gain_ref)
    L = sensor(left, gain, rng)
    R = sensor(right, gain, rng)
    md = int(np.ceil(2 * (float(h.max()) + ST_ZOFF) * t / PITCH)) + 4
    res = fs.ledger.binocular_disparity_ms(L, R, max_disp=md, window=7, paths=4)
    d = np.asarray(res["disparity"], float)
    zL = d * PITCH / (2 * t) - ST_ZOFF
    Xc = grid(PITCH)[0]
    xpos = Xc - zL * t            # 左の像の u' = x + z·t
    z = np.full(zL.shape, np.nan)
    xg = Xc[0]
    for r in range(zL.shape[0]):
        ok = np.isfinite(zL[r])
        if ok.sum() < 2:
            continue
        xo, zo = xpos[r, ok], zL[r, ok]
        o = np.argsort(xo)
        xo, zo = xo[o], zo[o]
        # ★いちばん近い測定を採る(線形に補間すると、壁をまたぐ所に「間の高さ」を作ってしまう ——
        #   縁の外側の判定で、方式ではなく並べ直しが浮いた画素を作る)
        j = np.clip(np.searchsorted(xo, xg), 1, xo.size - 1)
        left_near = np.abs(xg - xo[j - 1]) <= np.abs(xo[j] - xg)
        k = np.where(left_near, j - 1, j)
        zi = zo[k]
        zi[np.abs(xo[k] - xg) > 0.75 * PITCH] = np.nan
        z[r] = zi
    return {"z": z, "valid": np.isfinite(z), "gain": gain, "left": L, "right": R, "disp": d}


# --------------------------------------------------------------------------- #
# 採点
# --------------------------------------------------------------------------- #
METHODS = ("stereo", "fringe", "tof", "laser", "ps")
METHOD_JA = {"stereo": "ステレオ", "fringe": "縞投影", "tof": "間接 ToF", "laser": "光切断",
             "ps": "照度差ステレオ"}
#: 形の外れを数える許容差 [mm] —— **全方式に共通の物差し**。精密な用途(図面の公差 ±0.1 mm 級)と
#: 粗い用途(ピッキング・有無の検査 ±1 mm 級)の 2 段。
#: ★2026-11-08 の敵対的レビューの指摘で変えた: 前の版は方式ごとに「つや消しの雑音の 5 倍」を閾値にしていて、
#: ToF 6.7 mm・照度差ステレオ 10 mm と雑音の大きい方式ほど甘く、トゲだらけの ToF が「偽 0 %」になっていた。
TOL_FINE = 0.1
TOL_COARSE = 1.0


def robust_sigma(v):
    v = v[np.isfinite(v)]
    if v.size < 10:
        return float("nan")
    return float(1.4826 * np.median(np.abs(v - np.median(v))))


def feature_values(z, pitch):
    """寸法: 段差・穴の深さ・斜面の角度・V 溝の深さ・リブの高さ(測れなければ NaN)。"""
    X, Y = grid(pitch)
    ok = np.isfinite(z)

    def med(mask):
        m = mask & ok
        return float(np.median(z[m])) if m.sum() >= max(10, 0.3 * mask.sum()) else float("nan")

    blk = (X > 3.0) & (X < 13.0) & (np.hypot(X - 8, Y - 12) > 3.0) & (np.hypot(X - 8, Y - 4.5) > 2.0)
    plat = (X > 15.0) & (X < 19.0)
    step = med(blk) - med(plat)
    ring = (np.hypot(X - 8, Y - 12) > 2.6) & (np.hypot(X - 8, Y - 12) < 3.6)
    bottom = np.hypot(X - 8, Y - 12) < 1.0
    hole = med(ring) - med(bottom)
    sl = (X > 20.5) & (X < 24.5) & ok
    if sl.sum() >= 0.3 * ((X > 20.5) & (X < 24.5)).sum():
        A = np.stack([X[sl], np.ones(int(sl.sum()))], 1)
        coef = np.linalg.lstsq(A, z[sl], rcond=None)[0]
        slope = float(np.degrees(np.arctan(-coef[0])))
    else:
        slope = float("nan")
    gc, gw, _ = PART["groove"]
    fl = ((np.abs(X - gc) > gw + 0.4) & (np.abs(X - gc) < gw + 1.5))
    bot = np.abs(X - gc) < 0.15
    groove = med(fl) - med(bot)
    ribm = (X > 36.4) & (X < 37.6)
    flr = ((X > 34.0) & (X < 35.6)) | ((X > 38.4) & (X < 39.6))
    rib = med(ribm) - med(flr)
    dents = []
    for dx, dy, dr, dd in PART["dents"]:
        # 周りの輪に平面を当てて引いてから、中心の深さを読む(周りの傾きを打痕と取り違えない)
        rr = np.hypot(X - dx, Y - dy)
        ctr = (rr < 0.2) & ok
        ann = (rr > dr + 0.2) & (rr < dr + 0.8)
        a_ok = ann & ok
        if a_ok.sum() < max(10, 0.3 * ann.sum()) or ctr.sum() < 3:      # 中心に 3 画素も無ければ測れない
            dents.append(float("nan"))
            continue
        A = np.stack([X[a_ok] - dx, Y[a_ok] - dy, np.ones(int(a_ok.sum()))], 1)
        c = np.linalg.lstsq(A, z[a_ok], rcond=None)[0]
        plane_c = c[0] * (X[ctr] - dx) + c[1] * (Y[ctr] - dy) + c[2]
        dents.append(float(np.median(plane_c - z[ctr])))
    return {"step": step, "hole": hole, "slope": slope, "groove": groove, "rib": rib,
            "dent50": dents[0], "dent15": dents[1]}


FEATURE_JA = {"step": "段差 3 mm", "hole": "穴の深さ 3 mm", "slope": "斜面 26.6°", "groove": "V 溝 1 mm",
              "rib": "リブ 3.5 mm", "dent50": "打痕 50 µm", "dent15": "打痕 15 µm"}


def true_features(pitch):
    """寸法の真値: 同じ格子・同じ測り方で真の高さの図から測った値(画素の中心の取り方の差を消す)。"""
    return feature_values(part_height(pitch), pitch)


def score(z, pitch):
    """真値との差を領域ごとに数える。偏り(平らな所の差の中央値)と形の外れを分けて数える。

    形の外れ = 偏りを引いた差が共通の許容差(``TOL_FINE`` / ``TOL_COARSE``)を超えた有効画素。偏りは
    基準面で校正すれば消せる一様なずれなので、形の外れには入れず別の列に出す(材質で変わる偏りは
    校正で消えないことがあるので、偏りの値そのものも出す)。
    """
    reg = regions(pitch)
    err = z - reg["z"]
    ok = np.isfinite(z)
    noise = robust_sigma(err[reg["flat"]])
    bias = float(np.nanmedian(err[reg["flat"]])) if (ok & reg["flat"]).any() else 0.0
    dev = np.abs(err - bias)
    false = ok & (dev > TOL_FINE)
    coarse = ok & (dev > TOL_COARSE)
    per = {}
    for name in ("flat", "edge", "hole", "slope", "groove", "rib"):
        m = reg[name]
        per[name] = {"missing": float(1 - ok[m].mean()), "false": float(false[m].sum() / max(1, ok[m].sum())),
                     "coarse": float(coarse[m].sum() / max(1, ok[m].sum()))}
    feats = feature_values(z, pitch)
    return {"noise": noise, "bias": bias, "missing": float(1 - ok.mean()),
            "false": float(false.sum() / max(1, ok.sum())), "coarse": float(coarse.sum() / max(1, ok.sum())),
            "per": per, "features": feats, "err": err, "falsemask": false}


# --------------------------------------------------------------------------- #
# 実データ 1: T-LESS(同じ場面を構造化光のセンサと ToF のセンサで撮った深度、CAD の真値)
# --------------------------------------------------------------------------- #
#: 置き場所(repo の外)。``tools/fetch_tless_v2_sensors.py`` が取ってきて展開する。
TLESS_ENV = "FULLSEYE_TLESS_V2_DATA"
TLESS_SCENE = 2
#: 採点に使う画像の番号(504 枚から等間隔に 12 枚。決定的)
TLESS_IMAGES = tuple(range(0, 504, 42))
#: センサの種類(製品名はソースに書かない: 展開した置き場の ``sensors.json`` が種類 → フォルダを引く。
#: 書くのは取得の道具 ``tools/fetch_tless_v2_sensors.py``)
TLESS_SENSORS = {"sl": "構造化光(点の模様の投影 + 相関)", "tof": "ToF(連続波)"}
#: 縁の帯の幅 [px](物体の輪郭の内側)
TLESS_EDGE_PX = 3
#: 「外れ」とみなす深度の差 [mm]
TLESS_OUTLIER_MM = 10.0


def _tless_dir():
    d = os.environ.get(TLESS_ENV, "").strip()
    if d and os.path.isfile(os.path.join(d, "sensors.json")):
        return d
    return None


def _tless_folders(root):
    """``sensors.json``(種類 → 場面のフォルダ)を読み、ありえない値は拒む(信頼しない入力)。"""
    import json
    with open(os.path.join(root, "sensors.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    out = {}
    for key in TLESS_SENSORS:
        name = m.get(key)
        if not isinstance(name, str) or "/" in name or "\\" in name or name.startswith("."):
            raise ValueError("sensors.json: bad folder for %r: %r" % (key, name))
        path = os.path.join(root, name, "%02d" % TLESS_SCENE)
        if not os.path.isfile(os.path.join(path, "gt.yml")):
            raise ValueError("sensors.json: %r has no scene %02d" % (name, TLESS_SCENE))
        out[key] = path
    models = m.get("models")
    if not isinstance(models, str) or not os.path.isdir(os.path.join(root, models)):
        raise ValueError("sensors.json: bad models folder: %r" % (models,))
    return out, os.path.join(root, models)


def _read_yml_blocks(path):
    """T-LESS v2 の info.yml / gt.yml を読む(この 2 種の形だけを相手にする小さな読み手。値は信頼しない入力)。"""
    out, cur, item = {}, None, None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if not line.startswith(" ") and not line.startswith("-") and line.endswith(":"):
                cur = int(line[:-1])
                out[cur] = []
                item = None
                continue
            s = line.strip()
            if s.startswith("- "):
                item = {}
                out[cur].append(item)
                s = s[2:]
            elif item is None:
                item = {}
                out[cur].append(item)
            k, v = s.split(":", 1)
            v = v.strip()
            if v.startswith("["):
                item[k.strip()] = [float(t) for t in v.strip("[]").split(",")]
            else:
                try:
                    item[k.strip()] = float(v)
                except ValueError:
                    item[k.strip()] = v
    return out


_MODEL_CACHE = {}


def _ply_mesh(path):
    """ASCII の PLY(頂点 x y z ... と面)を読む。"""
    if path in _MODEL_CACHE:
        return _MODEL_CACHE[path]
    with open(path, encoding="ascii") as fh:
        nv = nf = 0
        while True:
            line = fh.readline()
            if not line:
                raise ValueError("PLY header not terminated: %s" % path)
            if line.startswith("element vertex"):
                nv = int(line.split()[2])
            elif line.startswith("element face"):
                nf = int(line.split()[2])
            elif line.strip() == "end_header":
                break
        if not (0 < nv < 5_000_000 and 0 < nf < 10_000_000):
            raise ValueError("PLY size out of range: %d vertices, %d faces" % (nv, nf))
        V = np.loadtxt(fh, max_rows=nv, usecols=(0, 1, 2))
        Fc = np.loadtxt(fh, max_rows=nf, dtype=np.int64)
    if Fc.ndim != 2 or (Fc[:, 0] != 3).any():
        raise ValueError("only triangle faces are supported: %s" % path)
    F = Fc[:, 1:4]
    if F.min() < 0 or F.max() >= nv:
        raise ValueError("face index out of range: %s" % path)
    _MODEL_CACHE[path] = (V, F)
    return V, F


def _surface_points(V, F, spacing=0.35, seed=0):
    """三角形の面を ``spacing`` [mm] ほどの間隔で埋める点(面積に比例した数、決定的)。"""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    n = np.maximum(1, np.ceil(area / spacing ** 2).astype(int))
    rng = np.random.default_rng(seed)
    idx = np.repeat(np.arange(F.shape[0]), n)
    r1 = np.sqrt(rng.random(idx.size))
    r2 = rng.random(idx.size)
    return (1 - r1)[:, None] * a[idx] + (r1 * (1 - r2))[:, None] * b[idx] + (r1 * r2)[:, None] * c[idx]


def _render_gt_depth(objs, K, shape, models_dir):
    """真値の深度: CAD を真値の姿勢で置き、点で埋めて z バッファ(各画素でいちばん手前)。"""
    H, W = shape
    zbuf = np.full(H * W, np.inf)
    for o in objs:
        V, F = _ply_mesh(os.path.join(models_dir, "obj_%02d.ply" % int(o["obj_id"])))
        key = ("pts", int(o["obj_id"]))
        if key not in _MODEL_CACHE:
            _MODEL_CACHE[key] = _surface_points(V, F)
        P = _MODEL_CACHE[key]
        R = np.asarray(o["cam_R_m2c"]).reshape(3, 3)
        t = np.asarray(o["cam_t_m2c"])
        C = P @ R.T + t
        u = np.round(K[0, 0] * C[:, 0] / C[:, 2] + K[0, 2]).astype(int)
        v = np.round(K[1, 1] * C[:, 1] / C[:, 2] + K[1, 2]).astype(int)
        ok = (u >= 0) & (u < W) & (v >= 0) & (v < H) & (C[:, 2] > 0)
        np.minimum.at(zbuf, v[ok] * W + u[ok], C[ok, 2])
    z = zbuf.reshape(H, W)
    filled = np.isfinite(z)
    # 点の隙間(1 画素)だけを近傍の最小で埋める。輪郭は広げない
    zf = ndi.minimum_filter(np.where(filled, z, np.inf), size=3)
    inner = ndi.binary_closing(filled, iterations=1) & ~filled
    z = np.where(inner & np.isfinite(zf), zf, z)
    return np.where(np.isfinite(z), z, np.nan)


#: 深度の元の格子の焦点距離 [px] の目安(公表の画素数と水平の視野角から: 構造化光 640 px・58°、ToF 512 px・70.6°)。
#: T-LESS の深度はカラーの格子(焦点距離 約 1076 px)へ移してあるので、元の 1 画素はカラーの約 1.9 / 3.0 画素。
TLESS_NATIVE_FX = {"sl": 320.0 / np.tan(np.radians(29.0)), "tof": 256.0 / np.tan(np.radians(35.3))}


def tless_chapter(n_images=None, native=False):
    """T-LESS の 2 つのセンサの深度を CAD の真値と比べる。データが無ければ None。

    ``native=True`` は縁の帯の幅を**深度の元の画素**で 3 画素にとる(カラーの格子へ移したときの補間で
    「浮く」が増えていないかの確かめ。ToF は約 3 倍に引き伸ばされている)。"""
    root = _tless_dir()
    if root is None:
        return None
    from PIL import Image
    import realdata
    ids = TLESS_IMAGES if n_images is None else TLESS_IMAGES[:n_images]
    folders, models = _tless_folders(root)
    res = {}
    keep = {}
    for sensor_key in TLESS_SENSORS:
        base = folders[sensor_key]
        info = _read_yml_blocks(os.path.join(base, "info.yml"))
        gt = _read_yml_blocks(os.path.join(base, "gt.yml"))
        acc = {"interior_err": [], "edge_err": [], "interior_n": 0, "edge_n": 0, "interior_miss": 0,
               "edge_miss": 0, "outside_fly": 0, "outside_fat": 0, "outside_n": 0}
        for i in ids:
            K = np.asarray(info[i][0]["cam_K"]).reshape(3, 3)
            f_up = K[0, 0] / TLESS_NATIVE_FX[sensor_key] if native else 1.0
            ep = int(round(TLESS_EDGE_PX * f_up))
            e4, e7 = ep + int(round(4 * f_up)), ep + int(round(7 * f_up))
            scale = float(info[i][0]["depth_scale"])
            D = np.asarray(Image.open(os.path.join(base, "depth", "%04d.png" % i)), dtype=np.float64) * scale
            G = _render_gt_depth(gt[i], K, D.shape, models)
            obj = np.isfinite(G)
            inner = ndi.binary_erosion(obj, iterations=ep)
            edge = obj & ~inner
            meas = D > 0
            e = D - np.nan_to_num(G)
            acc["interior_err"].append(e[inner & meas])
            acc["edge_err"].append(e[edge & meas])
            acc["interior_n"] += int(inner.sum())
            acc["edge_n"] += int(edge.sum())
            acc["interior_miss"] += int((inner & ~meas).sum())
            acc["edge_miss"] += int((edge & ~meas).sum())
            # 輪郭の外 1〜3 画素を 3 つに分ける: 物体の深度のまま(縁が太る)/ 物体と背景の間に浮く(混合)/
            # 背景(正しい)。物体の深度 = いちばん近い物体の画素の真値、背景 = 外側 7〜10 画素の測定の平均
            ring = ndi.binary_dilation(obj, iterations=ep) & ~obj
            far = (ndi.binary_dilation(obj, iterations=e7) & ~ndi.binary_dilation(obj, iterations=e4) & meas)
            _, (iy, ix) = ndi.distance_transform_edt(~obj, return_indices=True)
            gnear = np.nan_to_num(G)[iy, ix]
            wsum = ndi.uniform_filter(far.astype(float), size=21)
            bg = np.where(wsum > 0, ndi.uniform_filter(np.where(far, D, 0.0), size=21) / np.maximum(wsum, 1e-12), 0.0)
            judge = ring & meas & (bg > gnear + 3 * TLESS_OUTLIER_MM)
            fat = judge & (np.abs(D - gnear) <= TLESS_OUTLIER_MM)
            fly = judge & (D > gnear + TLESS_OUTLIER_MM) & (D < bg - TLESS_OUTLIER_MM)
            acc["outside_fat"] += int(fat.sum())
            acc["outside_fly"] += int(fly.sum())
            acc["outside_n"] += int(judge.sum())
            if i == ids[0]:
                keep[sensor_key] = {"D": D, "G": G, "edge": edge, "inner": inner, "fly": fly, "fat": fat,
                                    "rgb": os.path.join(base, "rgb", "%04d.png" % i)}
        ie = np.concatenate(acc["interior_err"])
        ee = np.concatenate(acc["edge_err"])
        off = float(np.median(ie))
        res[sensor_key] = {
            "offset_mm": off,
            "interior_sigma_mm": robust_sigma(ie),
            "interior_miss": acc["interior_miss"] / max(1, acc["interior_n"]),
            "edge_miss": acc["edge_miss"] / max(1, acc["edge_n"]),
            "interior_out": float((np.abs(ie - off) > TLESS_OUTLIER_MM).mean()),
            "edge_out": float((np.abs(ee - off) > TLESS_OUTLIER_MM).mean()),
            "outside_fly": acc["outside_fly"] / max(1, acc["outside_n"]),
            "outside_fat": acc["outside_fat"] / max(1, acc["outside_n"]),
            "outside_n": acc["outside_n"],
            "n_images": len(ids), "ring_px": ep,
        }
    realdata.mark_read("tless_v2_sensors")
    res["keep"] = keep
    return res


# --------------------------------------------------------------------------- #
# 実データ 2: Middlebury 2014(実写ステレオ、真値視差)で「縁の外側」を同じ物差しで数える
# --------------------------------------------------------------------------- #
MB_MAX_DISP = 64
MB_WINDOW = 5
MB_JUMP = 5.0          #: 前景の縁とみなす視差の段 [px]
MB_TOL = 1.0           #: 「同じ」とみなす視差の差 [px]


def classify_outside(meas, near_fg, near_bg, tol):
    """縁の外側の 1 画素を 4 つに分ける: 欠測 / 太る(前景の値のまま)/ 浮く(間)/ 正しい(背景の値)。"""
    out = np.full(np.shape(meas), "other", dtype=object)
    lo, hi = np.minimum(near_fg, near_bg), np.maximum(near_fg, near_bg)
    out[~np.isfinite(meas)] = "missing"
    f = np.isfinite(meas)
    out[f & (np.abs(meas - near_fg) <= tol)] = "fat"
    out[f & (np.abs(meas - near_bg) <= tol)] = "ok"
    out[f & (meas > lo + tol) & (meas < hi - tol)] = "fly"
    return out


def middlebury_chapter():
    """実写ステレオ(scikit-image 同梱の Middlebury 2014 motorcycle)を同じ op で通し、縁の外側を数える。"""
    import realdata
    L, R, G = realdata.sample_stereo_pair()
    G = np.where(np.isfinite(G), G, np.nan)
    res = fs.ledger.binocular_disparity_ms(L, R, max_disp=MB_MAX_DISP, window=MB_WINDOW, paths=4)
    D = np.asarray(res["disparity"], float)
    ok = np.isfinite(G)
    fg = ndi.grey_dilation(np.nan_to_num(G, nan=-1e9), size=(1, 7))        # 横 ±3 画素の最大の視差 = 前景
    nb = ok & (fg - np.nan_to_num(G) > MB_JUMP)                               # 前景の縁のすぐ外の背景
    cls = classify_outside(D[nb], fg[nb], G[nb], MB_TOL)
    frac = {k: float((cls == k).mean()) for k in ("missing", "fat", "fly", "ok", "other")}
    bad = np.abs(D - G) > 2.0
    edge_band = ndi.binary_dilation(nb, iterations=2)
    rest = ok & ~edge_band & np.isfinite(D)
    eb = ok & edge_band & np.isfinite(D)
    return {"n": int(nb.sum()), "frac": frac, "bad2_edge": float(bad[eb].mean()), "bad2_rest": float(bad[rest].mean()),
            "L": L, "D": D, "G": G, "nb": nb}


# --------------------------------------------------------------------------- #
# シミュの本体: 5 方式 × 4 材質
# --------------------------------------------------------------------------- #
#: 段差の壁: (x, 高い側, 高い面, 低い面)
WALLS = ((2.0, "right", 6.0, 0.0), (14.0, "left", 6.0, 3.0), (36.0, "right", 4.0, 0.5), (38.0, "left", 4.0, 0.5))


def outside_profile(z, pitch):
    """壁の低い側 1〜3 画素の列を、行の中央値の断面で 4 つに分ける(太る / 浮く / 正しい / 欠測)。"""
    X = grid(pitch)[0]
    xc = X[0]
    labels = []
    for xw, high, zh, zl in WALLS:
        for k in (1, 2, 3):
            xx = xw + (k - 0.5) * pitch if high == "left" else xw - (k - 0.5) * pitch
            j = int(np.argmin(np.abs(xc - xx)))
            col = z[:, j]
            if np.isfinite(col).mean() < 0.5:
                labels.append("missing")
                continue
            m = float(np.nanmedian(col))
            tol = 0.2 * (zh - zl)
            labels.append(str(classify_outside(np.array([m]), np.array([zh]), np.array([zl]), tol)[0]))
    return {k: labels.count(k) / len(labels) for k in ("missing", "fat", "fly", "ok", "other")}


def measure(method, scene, rng, ref):
    """1 方式・1 材質を測り、``(z, pitch, raw)`` を返す。``ref`` はつや消しの露光(上限の基準)を持つ辞書。"""
    if method == "fringe":
        r = measure_fringe(scene, rng, ref.get("fringe"))
        ref.setdefault("fringe", r["gain"])
        return r["z"], PITCH, r
    if method == "tof":
        r = measure_tof(scene, rng, ref.get("tof"))
        ref.setdefault("tof", r["sat_ref"])
        return r["z"], TOF_PITCH, r
    if method == "laser":
        ncols = int(round(W_MM / PITCH))
        # 図の 1 コマは穴を横切る位置(x = 8.3 mm)。動画は部品を端から端まで 24 コマ
        mid = int(round((8.3 + X_SHIFT) / PITCH))
        keep = (sorted(set(np.linspace(0, ncols - 1, 24).round().astype(int)) | {mid}) if scene.key == "matte"
                else [mid])
        r = measure_laser(scene, rng, ref.get("laser"), keep_frames=keep)
        ref.setdefault("laser", r["gain"])
        return r["z"], PITCH, r
    if method == "ps":
        r = measure_ps(scene, rng, ref.get("ps"))
        ref.setdefault("ps", r["gain"])
        zt = scene.truth(PITCH)
        zr = np.where(r["valid"], r["z_rel"], np.nan)
        # 照度差ステレオは高さの定数を持たない: 有効画素の真値との差の中央値だけ合わせる(真値を使う。
        # 形の外れは偏りを引いてから数えるので、この合わせ方は偏りの列にしか効かない —— 図と表に明記する)
        return zr + np.nanmedian(zt - zr), PITCH, r
    r = measure_stereo(scene, rng, ref.get("stereo"))
    ref.setdefault("stereo", r["gain"])
    return r["z"], PITCH, r


def run_matrix(seed=7):
    """5 方式 × 4 材質を測って採点する(形の外れは全方式に共通の許容差 0.1 mm / 1 mm で数える)。"""
    out = {}
    for method in METHODS:
        ref = {}
        out[method] = {}
        for mk in MAT_ORDER:
            scene = Scene(mk, seed=0)
            rng = np.random.default_rng(seed + 31 * METHODS.index(method) + MAT_ORDER.index(mk))
            t = time.perf_counter()
            z, pitch, raw = measure(method, scene, rng, ref)
            sc = score(z, pitch)
            if method == "ps":
                # 照度差ステレオが直接測るのは傾き: 斜面の角度は積分した高さでなく法線から読む(方式の本来の量)
                X = grid(pitch)[0]
                n = raw["normals"]
                sl = (X > 20.5) & (X < 24.5) & raw["valid"]
                g = -n[..., 0][sl] / np.clip(n[..., 2][sl], 1e-6, None)
                sc["features"]["slope"] = (float(np.degrees(np.arctan(-np.median(g))))
                                           if sl.sum() >= 0.3 * ((X > 20.5) & (X < 24.5)).sum() else float("nan"))
                nt = np.stack([-np.gradient(part_height(pitch), pitch, axis=1),
                               -np.gradient(part_height(pitch), pitch, axis=0),
                               np.ones(X.shape)], -1)
                nt /= np.linalg.norm(nt, axis=-1, keepdims=True)
                fl = regions(pitch)["flat"] & raw["valid"]
                cosang = np.clip((n[fl] * nt[fl]).sum(-1), -1, 1)
                sc["normal_err_deg"] = float(np.degrees(np.median(np.arccos(cosang))))
            sc["outside"] = outside_profile(z, pitch)
            if method == "tof":
                # 浮いた画素の印(itof_flying_pixel_mask)で落とす前の生の深度でも数える(実データの比べ先)
                sc["outside_raw"] = outside_profile(raw["z_raw"], pitch)
            sc["seconds"] = time.perf_counter() - t
            sc["pitch"] = pitch
            out[method][mk] = {"z": z, "pitch": pitch, "raw": raw, "score": sc}
    return out


def print_matrix(M):
    print("\n2. 5 方式 × 4 材質(数字は真値との差。形の外れ = 偏りを引いた差が全方式共通の %.1f mm / %.0f mm を"
          "超えた有効画素の割合)" % (TOL_FINE, TOL_COARSE))
    print("   %-10s %-10s %8s %8s %7s %8s %8s | %6s %6s %6s %6s %6s %7s %7s" % (
        "方式", "材質", "雑音mm", "偏りµm", "欠測%", "外0.1%", "外1mm%", "段差", "穴", "斜面°", "V溝", "リブ",
        "打痕50", "打痕15"))
    for method in METHODS:
        tf = true_features(M[method]["matte"]["pitch"])
        for mk in MAT_ORDER:
            s = M[method][mk]["score"]
            f = s["features"]

            def d(k, scale=1.0, fmt="%+6.2f"):
                v = f[k]
                return "  測れず" if not np.isfinite(v) else fmt % (scale * (v - tf[k]))
            print("   %-10s %-10s %8.4f %+8.0f %7.1f %8.1f %8.1f | %s %s %s %s %s %s %s" % (
                METHOD_JA[method], MATERIALS[mk]["ja"], s["noise"], 1e3 * s["bias"], 100 * s["missing"],
                100 * s["false"], 100 * s["coarse"], d("step"), d("hole"), d("slope", fmt="%+6.1f"), d("groove"),
                d("rib"), d("dent50", 1000, "%+6.0f"), d("dent15", 1000, "%+6.0f")))
    print("   (寸法の列は 測った値 − 真値。段差・穴・V 溝・リブは mm、斜面は度、打痕は µm)")


# --------------------------------------------------------------------------- #
# 図と動画
# --------------------------------------------------------------------------- #
BG = (14, 18, 24)
PANEL = (24, 30, 39)
INK = (232, 236, 241)
SUB = (170, 180, 192)


def _font(size, bold=False):
    from PIL import ImageFont
    return ImageFont.truetype(str(figs._japanese_font_path(bold=bold)), size)


def _text(draw, xy, text, box, size=22, fill=INK, bold=False, anchor=None):
    """描く前に文字の外接箱を測り、許した箱から 1 px でもはみ出せば止める(文字をデータに重ねない)。"""
    f = _font(size, bold)
    bb = draw.multiline_textbbox(xy, text, font=f, spacing=4, anchor=anchor)
    x0, y0, x1, y1 = box
    if not (bb[0] >= x0 and bb[1] >= y0 and bb[2] <= x1 and bb[3] <= y1):
        raise AssertionError("text overflows its box: %r %r %r" % (text, bb, box))
    draw.multiline_text(xy, text, font=f, fill=fill, spacing=4, anchor=anchor)


def _on_grid(z, pitch, out_pitch):
    """別の格子の高さの図を表示の格子へ(双一次。欠測は最近傍の印で保つ)。"""
    if abs(pitch - out_pitch) < 1e-12:
        return z
    f = pitch / out_pitch
    ok = np.isfinite(z)
    zf = ndi.zoom(np.where(ok, z, np.nanmedian(z) if ok.any() else 0.0), f, order=1)
    okf = ndi.zoom(ok.astype(float), f, order=0) > 0.5
    return np.where(okf, zf, np.nan)


def relief(z, pitch, tilt_deg=48.0, light=(-0.45, 0.55, 0.70), false_mask=None, tint=None, zlim=(-1.0, 7.5)):
    """高さの図を斜め前から見た陰影つきの立体に描く(RGB、0..1)。欠測 = 暗い灰、偽の形 = 橙。

    ★描き方は撮像のシミュと同じ地平線の判定(手前の高い所が奥を隠す)。色は材質の地色に Lambert の陰影。
    """
    # ★表示の高さは部品の範囲に切る(照度差ステレオの積分の飛び値 1 本で、立体全体が潰れて見えた)
    z = np.where(np.isfinite(z), np.clip(z, *zlim), np.nan)
    ok = np.isfinite(z)
    zf = z.copy()
    if not ok.all():
        idx = ndi.distance_transform_edt(~ok, return_distances=False, return_indices=True)
        zf = z[tuple(idx)] if ok.any() else np.zeros_like(z)
    gy, gx = np.gradient(zf, pitch)
    n = np.stack([-gx, -gy, np.ones_like(zf)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Ld = unit(light)
    shade = 0.25 + 0.75 * np.clip(n @ Ld, 0, 1)
    base = np.array(tint if tint is not None else (0.78, 0.80, 0.83))
    rgb = shade[..., None] * base[None, None, :]
    if false_mask is not None:
        fm = false_mask & ok
        rgb[fm] = shade[fm][:, None] * np.array([0.95, 0.50, 0.10])[None, :]
    rgb[~ok] = np.array([0.20, 0.21, 0.24])
    # 列ごと(y 方向)に傾けて見る: 転置して x-z の斜め射影と同じ手順
    t = np.tan(np.radians(tilt_deg))
    zt = zf.T
    ys = (np.arange(zt.shape[1]) + 0.5) * pitch
    a = np.radians(tilt_deg)
    g = zt * np.tan(a) - ys[None, :]
    rmax = np.maximum.accumulate(g[:, ::-1], axis=1)[:, ::-1]
    nxt = np.concatenate([rmax[:, 1:], np.full((zt.shape[0], 1), -np.inf)], axis=1)
    vis = g >= nxt - 1e-9
    zmax = float(np.nanmax(zf)) + 1.0
    out_y = np.arange(-int(np.ceil(zmax * t / pitch)), zt.shape[1]) * pitch + 0.5 * pitch
    img = np.zeros((zt.shape[0], out_y.size, 3)) + np.array(BG) / 255.0
    for r in range(zt.shape[0]):
        v = vis[r]
        u = ys[v] - zt[r, v] * t
        for c in range(3):
            img[r, :, c] = np.interp(out_y, u, rgb[:, r, c][v], left=BG[c] / 255.0, right=BG[c] / 255.0)
    return np.transpose(img, (1, 0, 2))


def _to8(a):
    return np.rint(255 * np.clip(a, 0, 1)).astype(np.uint8)


def _fit(img8, w, h):
    from PIL import Image
    im = Image.fromarray(img8)
    return im.resize((w, h), Image.Resampling.LANCZOS)


#: 判定の数の基準(この順に当てはめる): 欠測 50 % 超 → ほぼ測れない / 段差か穴の深さが 0.5 mm 超ずれる → 寸法が崩れる /
#: 1 mm 超が 10 % 超 → 1 mm でも外れる / 0.1 mm 超が 20 % 超 → 0.1 mm では外れる / 0.1 mm 超が 5 % 超か 1 mm 超が 1 % 超 →
#: 0.1 mm で所々外れる / 欠測 20 % 超 → 欠けが多い / それ以外(0.1 mm 超 ≤ 5 %・1 mm 超 ≤ 1 %)→ 0.1 mm で測れる
VERDICT_RULES = "0.1 mm で測れる = 0.1 mm 超 5 % 以下・1 mm 超 1 % 以下・欠測 20 % 以下"


def _verdict(s, method):
    """1 マスの判定の言葉(全方式に共通の物差しの数字から。基準は上の表)。"""
    if s["missing"] > 0.5:
        return "ほぼ測れない"
    tf = true_features(s["pitch"])
    if any(not np.isfinite(s["features"][k]) or abs(s["features"][k] - tf[k]) > 0.5 for k in ("step", "hole")):
        return "寸法が崩れる"
    if s["coarse"] > 0.1:
        return "1 mm でも外れる"
    if s["false"] > 0.2:
        return "0.1 mm では外れる"
    if s["false"] > 0.05 or s["coarse"] > 0.01:
        return "0.1 mm で所々外れる"
    if s["missing"] > 0.2:
        return "欠けが多い"
    return "0.1 mm で測れる"


def _text_fit(draw, xy, text, box, sizes=(17, 16, 15, 14), **kw):
    """収まる最大の字の大きさで描く(14 px でも収まらなければ止める)。"""
    for k, sz in enumerate(sizes):
        try:
            return _text(draw, xy, text, box, size=sz, **kw)
        except AssertionError:
            if k == len(sizes) - 1:
                raise


def _cell_note(s, m):
    note = "欠測 %.0f%%・外れ %.0f/%.0f%%  %s" % (100 * s["missing"], 100 * s["false"], 100 * s["coarse"], _verdict(s, m))
    return note


def fig_map(M):
    """図 1: 5 方式 × 4 材質の測った形(斜めから見た立体、欠測 = 灰、偽の形 = 橙)と真値。"""
    from PIL import Image, ImageDraw
    cw, ch = 300, 205
    lx, top = 185, 120
    W = lx + 4 * cw + 5 * 8 + 10
    H = top + 6 * (ch + 30) + 40
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    _text(d, (16, 12), "同じ部品・同じ材質を 5 つの方式で測った形(斜め前から見た立体。灰 = 欠測、橙 = 0.1 mm を超える外れ)",
          (0, 0, W, 50), size=24, bold=True)
    _text(d, (16, 52), "部品: 40×24 mm、段差 3 mm・止まり穴 φ4 深さ 3・斜面 26.6°・V 溝 1 mm・リブ 3.5 mm・打痕 50 / 15 µm",
          (0, 48, W, 88), size=18, fill=SUB)
    tint = {"matte": (0.80, 0.80, 0.79), "metal": (0.74, 0.77, 0.82), "resin": (0.86, 0.84, 0.74),
            "black": (0.55, 0.56, 0.60)}
    zt = part_height(PITCH)
    rows = [("truth", "真値(寸法表)")] + [(m, METHOD_JA[m] + ("\n(高さの定数は\n真値に合わせた)" if m == "ps" else ""))
                                       for m in METHODS]
    for ci, mk in enumerate(MAT_ORDER):
        x = lx + 8 + ci * (cw + 8)
        _text(d, (x + cw // 2, top - 6), MATERIALS[mk]["ja"], (x, top - 36, x + cw, top), size=22, bold=True,
              anchor="ms")
    for ri, (m, label) in enumerate(rows):
        y = top + ri * (ch + 30)
        _text(d, (12, y + ch // 2), label, (0, y, lx, y + ch), size=21, bold=True, anchor="lm")
        for ci, mk in enumerate(MAT_ORDER):
            x = lx + 8 + ci * (cw + 8)
            if m == "truth":
                rgb = relief(zt, PITCH, tint=tint[mk])
                note = "真値"
            else:
                cell = M[m][mk]
                z = _on_grid(cell["z"], cell["pitch"], PITCH)
                fm = _on_grid(np.where(cell["score"]["falsemask"], 1.0, 0.0), cell["pitch"], PITCH) > 0.5
                rgb = relief(z, PITCH, false_mask=fm, tint=tint[mk])
                s = cell["score"]
                note = _cell_note(s, m)
            im.paste(_fit(_to8(rgb), cw, ch), (x, y))
            _text_fit(d, (x + 4, y + ch + 3), note, (x, y + ch, x + cw, y + ch + 28), fill=SUB)
    _text_fit(d, (16, H - 34), "外れ = 偏りを引いた差が共通の 0.1 / 1 mm を超えた画素の %%。%s。三角測量 30°、画素 ToF 0.4 mm・"
              "ほか %.2f mm。" % (VERDICT_RULES, PITCH), (0, H - 38, W, H), sizes=(16, 15, 14, 13), fill=SUB)
    return np.asarray(im)


def fig_raw(raws):
    """図 2: 5 方式の装置が撮る生の画像(つや消しと金属光沢)。"""
    from PIL import Image, ImageDraw
    cw, ch = 260, 168
    lx, top = 118, 60
    W = lx + 5 * (cw + 8) + 8
    H = top + 2 * (ch + 36) + 10
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    _text(d, (16, 12), "装置が撮る生の画像(同じ部品。上 = つや消し、下 = 金属光沢)", (0, 0, W, 50), size=24, bold=True)
    names = ("ステレオ(左)", "縞投影(周期 1 mm)", "ToF の振幅", "光切断の 1 コマ", "照度差(1 灯目)")
    for ri, mk in enumerate(("matte", "metal")):
        y = top + ri * (ch + 36)
        _text(d, (10, y + ch // 2), MATERIALS[mk]["ja"], (0, y, lx, y + ch), size=21, bold=True, anchor="lm")
        for ci, key in enumerate(("stereo", "fringe", "tof", "laser", "ps")):
            x = lx + 8 + ci * (cw + 8)
            a = raws[mk][key]
            g = _to8(np.clip(a, 0, 1))
            pane = _fit(np.stack([g] * 3, -1), cw, ch)
            im.paste(pane, (x, y + 30))
            if ri == 0:
                _text(d, (x + 2, y + 2), names[ci], (x, y, x + cw, y + 30), size=18, fill=SUB)
            else:
                _text(d, (x + 2, y + 2), names[ci], (x, y, x + cw, y + 30), size=18, fill=SUB)
    return np.asarray(im)


def fig_real(tl, mb):
    """図 4: 実データ。T-LESS の同じ場面を構造化光と ToF で撮った深度と、縁の外側の判定。"""
    from PIL import Image, ImageDraw
    keep = tl["keep"]
    D0 = keep["sl"]["G"]
    obj = np.isfinite(D0)
    ys, xs = np.nonzero(obj)
    y0, y1 = max(0, ys.min() - 20), min(D0.shape[0], ys.max() + 20)
    x0, x1 = max(0, xs.min() - 20), min(D0.shape[1], xs.max() + 20)
    cw = 380
    ch = int(round(cw * (y1 - y0) / (x1 - x0)))
    W = 16 + 3 * (cw + 12) + 4
    H = 70 + ch + 160
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    _text(d, (16, 12), "実データ: 同じ場面を 2 種類の深度センサで(T-LESS、CAD の真値つき)", (0, 0, W, 50), size=24, bold=True)
    rgb = np.asarray(Image.open(keep["sl"]["rgb"]).convert("RGB"))[y0:y1, x0:x1]
    im.paste(_fit(rgb, cw, ch), (16, 64))
    _text(d, (16, 64 + ch + 4), "カラー画像(構造化光の側)", (16, 64 + ch, 16 + cw, 64 + ch + 30), size=18, fill=SUB)
    lo = float(np.nanpercentile(D0, 1)) - 10
    hi = float(np.nanpercentile(D0, 99)) + 45
    for k, key in enumerate(("sl", "tof")):
        D = keep[key]["D"][y0:y1, x0:x1]
        g = np.clip((D - lo) / (hi - lo), 0, 1)
        g = np.where(D > 0, 1.0 - 0.85 * g, 0.0)
        a = np.stack([g] * 3, -1)
        fat = keep[key]["fat"][y0:y1, x0:x1]
        fly = keep[key]["fly"][y0:y1, x0:x1]
        a[fat] = np.array([0.90, 0.62, 0.0])
        a[fly] = np.array([0.34, 0.71, 0.91])
        x = 16 + (k + 1) * (cw + 12)
        im.paste(_fit(_to8(a), cw, ch), (x, 64))
        r = tl[key]
        _text(d, (x, 64 + ch + 4), "%s の深度" % TLESS_SENSORS[key], (x, 64 + ch, x + cw, 64 + ch + 30), size=18,
              fill=SUB)
        _text(d, (x, 64 + ch + 34), "縁の外 1〜3 画素: 太る %.0f %% / 浮く %.0f %%"
              % (100 * r["outside_fat"], 100 * r["outside_fly"]), (x, 64 + ch + 30, x + cw, 64 + ch + 62),
              size=18, bold=True)
        _text(d, (x, 64 + ch + 64), "内側の雑音 %.1f mm、欠測 %.1f %%(%d 枚)"
              % (r["interior_sigma_mm"], 100 * r["interior_miss"], r["n_images"]),
              (x, 64 + ch + 60, x + cw, 64 + ch + 92), size=18, fill=SUB)
    _text(d, (16, H - 62), "橙 = 太る(物体の深度のまま背景へはみ出す)  青 = 浮く(物体と背景の間の深度)。"
          "実写ステレオ(Middlebury)では 太る %.0f %% / 浮く %.0f %% / 欠測 %.0f %%。"
          % (100 * mb["frac"]["fat"], 100 * mb["frac"]["fly"], 100 * mb["frac"]["missing"]),
          (0, H - 66, W, H - 34), size=17, fill=SUB)
    _text(d, (16, H - 32), "出典表示: Hodaň et al., T-LESS, WACV 2017, CC BY 4.0(深度とカラー画像を切り出して表示)",
          (0, H - 34, W, H), size=16, fill=SUB)
    return np.asarray(im)


VIDEO_W, VIDEO_H, VIDEO_FPS = 960, 540, 10


def _card(title, lines, n):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (VIDEO_W, VIDEO_H), BG)
    d = ImageDraw.Draw(im)
    _text(d, (60, 150), title, (0, 100, VIDEO_W, 230), size=36, bold=True)
    y = 250
    for ln in lines:
        _text(d, (50, y), ln, (0, y - 4, VIDEO_W, y + 40), size=22, fill=SUB)
        y += 44
    a = np.asarray(im)
    return [a] * n


def _frame_with(img8, title, caption):
    """1 コマ: 上に見出し、中に絵(縦横比を保って収める)、下に字幕の帯。"""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (VIDEO_W, VIDEO_H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, VIDEO_W, 44), fill=PANEL)
    _text(d, (14, 8), title, (0, 0, VIDEO_W, 44), size=22, bold=True)
    d.rectangle((0, VIDEO_H - 40, VIDEO_W, VIDEO_H), fill=PANEL)
    _text(d, (14, VIDEO_H - 34), caption, (0, VIDEO_H - 40, VIDEO_W, VIDEO_H), size=20)
    src = Image.fromarray(img8)
    aw, ah = VIDEO_W - 20, VIDEO_H - 96
    s = min(aw / src.width, ah / src.height)
    src = src.resize((max(1, int(src.width * s)), max(1, int(src.height * s))), Image.Resampling.LANCZOS)
    im.paste(src, ((VIDEO_W - src.width) // 2, 50 + (ah - src.height) // 2))
    return np.asarray(im)


def _raw_panel(stereo_pair, fringe_img, tof_amp, laser_img, ps_img, k):
    """生の画像 5 枚を 1 枚に(3 + 2 の割り付け)。"""
    from PIL import Image, ImageDraw
    W, H = 900, 400
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    cw, ch = 290, 170
    items = [("ステレオ(左 / 右を交互)", stereo_pair[k % 2]), ("縞投影(12 枚を順に)", fringe_img),
             ("ToF の振幅(画素 0.4 mm)", tof_amp), ("光切断(シート光を送る)", laser_img),
             ("照度差ステレオ(8 灯を順に)", ps_img)]
    for i, (name, a) in enumerate(items):
        x = 5 + (i % 3) * (cw + 8)
        y = 4 + (i // 3) * (ch + 30)
        g = _to8(np.clip(a, 0, 1))
        im.paste(_fit(np.stack([g] * 3, -1), cw, ch), (x, y + 26))
        _text(d, (x, y + 2), name, (x, y, x + cw, y + 26), size=17, fill=SUB)
    return np.asarray(im)


def make_video(M, tl, mb, extra):
    """約 50 秒の説明動画: 何を入れ → 何を比べ → 何が分かったか。"""
    fps = VIDEO_FPS
    frames = []
    frames += _card("同じ部品を、5 つの 3-D センサで測る",
                    ["ブースは自社の 1 方式を、いちばん良い部品で見せる。",
                     "ここでは同じ部品・同じ材質を 5 方式で撮り、",
                     "真値(寸法表)と比べて、どこで壊れるかを数える。"], int(3.0 * fps))
    zt = part_height(PITCH)
    tr = _to8(relief(zt, PITCH))
    frames += [_frame_with(tr, "部品(真値): 段差・止まり穴・斜面・V 溝・リブ・浅い打痕",
                           "40×24 mm。段差 3 mm、穴 φ4 深さ 3 mm、斜面 26.6°、V 溝 1 mm、リブ 3.5 mm、打痕 50 / 15 µm")] * int(3.5 * fps)
    raw = extra["raw_matte"]
    n_raw = int(10 * fps)
    for k in range(n_raw):
        fi = raw["fringe_all"][k % len(raw["fringe_all"])]
        li = raw["laser_all"][k % len(raw["laser_all"])]
        pi = raw["ps_all"][k % len(raw["ps_all"])]
        p = _raw_panel((raw["stereo_l"], raw["stereo_r"]), fi, raw["tof"], li, pi, k // 3)
        frames.append(_frame_with(p, "装置が撮る生の画像(つや消し)",
                                  "物理で描いた生の画像(影・反射・模様・画素・雑音)を、Fullseye の op で高さに戻す"))
    frames += _card("材質を変える", ["つや消し → 金属光沢 → 半透明の樹脂 → 黒。",
                                   "灰 = 欠測、橙 = 全方式共通の 0.1 mm を超えて外れた画素。"], int(2.5 * fps))
    tint = {"matte": (0.80, 0.80, 0.79), "metal": (0.74, 0.77, 0.82), "resin": (0.86, 0.84, 0.74),
            "black": (0.55, 0.56, 0.60)}
    from PIL import Image, ImageDraw
    for mk in MAT_ORDER:
        im = Image.new("RGB", (900, 420), BG)
        d = ImageDraw.Draw(im)
        cw, ch = 290, 180
        for i, m in enumerate(METHODS):
            cell = M[m][mk]
            z = _on_grid(cell["z"], cell["pitch"], PITCH)
            fm = _on_grid(np.where(cell["score"]["falsemask"], 1.0, 0.0), cell["pitch"], PITCH) > 0.5
            x = 5 + (i % 3) * (cw + 8)
            y = 4 + (i // 3) * (ch + 34)
            im.paste(_fit(_to8(relief(z, PITCH, false_mask=fm, tint=tint[mk])), cw, ch), (x, y + 26))
            s = cell["score"]
            _text_fit(d, (x, y + 2), "%s  欠測 %.0f%% / 外れ %.0f%%" % (METHOD_JA[m], 100 * s["missing"],
                                                                     100 * s["false"]),
                      (x, y, x + cw, y + 26), sizes=(16, 15, 14), fill=SUB)
        x = 5 + 2 * (cw + 8)
        y = 4 + (ch + 34)
        im.paste(_fit(_to8(relief(zt, PITCH, tint=tint[mk])), cw, ch), (x, y + 26))
        _text(d, (x, y + 2), "真値", (x, y, x + cw, y + 26), size=16, fill=SUB)
        msg = extra["material_lines"][mk]
        frames += [_frame_with(np.asarray(im), "材質: %s" % MATERIALS[mk]["ja"], msg)] * int(4.0 * fps)
    frames += [_frame_with(extra["map_table"], "どの方式がどこで壊れるか(数字は同じ実行の値)",
                           "青の字 = 0.1 mm で測れる、橙の字 = 欠ける・外れる(共通の物差し 0.1 mm / 1 mm)")] * int(6.0 * fps)
    if extra.get("real") is not None:
        frames += [_frame_with(extra["real"], "実データで裏を取る: 同じ場面を構造化光と ToF で",
                               "縁の外側が 構造化光では「太る」、ToF では「浮く」。実データが支えるのはこの向きだけ")] * int(5.0 * fps)
    frames += _card("分かったこと", extra["conclusion"], int(5.0 * fps))
    return frames


def map_table_image(M):
    """どの方式がどこで壊れるかの表(5 方式 × 4 材質、各マスに 欠測・偽の形・判定)。"""
    from PIL import Image, ImageDraw
    cw, ch = 205, 74
    lx, top = 150, 50
    W, H = lx + 4 * cw + 10, top + 5 * ch + 10
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    good = tuple(int(255 * c) for c in fs.semantic_palette()["right"])
    bad = tuple(int(255 * c) for c in fs.semantic_palette()["emphasis"])
    for ci, mk in enumerate(MAT_ORDER):
        x = lx + ci * cw
        _text(d, (x + cw // 2, top - 10), MATERIALS[mk]["ja"], (x, 0, x + cw, top), size=20, bold=True, anchor="ms")
    for ri, m in enumerate(METHODS):
        y = top + ri * ch
        _text(d, (8, y + ch // 2), METHOD_JA[m], (0, y, lx, y + ch), size=20, bold=True, anchor="lm")
        for ci, mk in enumerate(MAT_ORDER):
            x = lx + ci * cw
            s = M[m][mk]["score"]
            v = _verdict(s, m)
            d.rectangle((x + 2, y + 2, x + cw - 4, y + ch - 4), fill=PANEL, outline=(60, 70, 84))
            _text(d, (x + 10, y + 8), v, (x, y, x + cw, y + ch), size=19, bold=True,
                  fill=good if v == "0.1 mm で測れる" else bad)
            _text_fit(d, (x + 10, y + 40), "欠測 %.0f%%・外れ %.0f/%.0f%%" % (100 * s["missing"], 100 * s["false"],
                                                                       100 * s["coarse"]),
                      (x, y, x + cw, y + ch), sizes=(16, 15, 14), fill=SUB)
    return np.asarray(im)


def claims_chapter(M, mb, tl, tl_native, dents, cond, seeds, acc):
    """8. 主張(どれも上で印字した数字から。数字が動いたら文のほうを直す)。

    ★2026-11-08 の敵対的レビューで外した主張と理由(消さずに残す):
    「雑音の床の順」(画素の大きさ・ステレオの角で入れ替わる —— 4 章の表で条件ごとに出す)、
    「シミュでは縁の外側がステレオで太り ToF で浮く」(壁 4 枚 × 3 列 = 12 標本で、部品を画素の格子から
    ずらすと入れ替わる —— 縁の外側の向きは実データ 2 つだけで主張する)、
    「黒の ToF の斜面の偽の形」(誤差の符号が乱数の種で入れ替わる = 系統でなく雑音)、
    「打痕 15 µm は縞投影だけが読む」(画素・レンズのぼけで動く —— 表に数字だけ出す)。
    """
    print("\n8. 主張の検査(形の外れは全方式共通の 0.1 mm / 1 mm で数える)")
    S = {m: {mk: M[m][mk]["score"] for mk in MAT_ORDER} for m in METHODS}
    gate("ToF(画素 0.4 mm)はつや消しでも 0.1 mm の用途には届かない(0.1 mm を超える外れが 8 割以上)",
         S["tof"]["matte"]["false"] >= 0.8, "外れ %.0f %%(1 mm を超える外れ %.0f %%)"
         % (100 * S["tof"]["matte"]["false"], 100 * S["tof"]["matte"]["coarse"]))
    fm = S["fringe"]["metal"]["per"]
    gate("金属光沢の縞投影: V 溝は鏡面の 2 回反射で半分以上が 0.1 mm を超えて外れる(つや消しの 2 倍以上)",
         fm["groove"]["false"] >= 0.5 and fm["groove"]["false"] > 2 * S["fringe"]["matte"]["per"]["groove"]["false"],
         "V 溝の外れ 金属 %.0f %% / つや消し %.0f %%" % (100 * fm["groove"]["false"],
                                                100 * S["fringe"]["matte"]["per"]["groove"]["false"]))
    tm = S["tof"]["metal"]
    gate("金属光沢の ToF: 露光が鏡面の返りに合わさり、ほかの面が暗くなって 1 mm を超える外れが半分以上",
         tm["coarse"] >= 0.5, "1 mm を超える外れ %.0f %%、露光の倍率 %.4f(つや消し = 1)"
         % (100 * tm["coarse"], M["tof"]["metal"]["raw"]["gain"]))
    sr = S["stereo"]["resin"]
    gate("半透明の樹脂のステレオ: 模様が内部散乱でにじみ、3 割以上欠け、残りの半分以上が 0.1 mm を超えて外れる",
         sr["missing"] >= 0.3 and sr["false"] >= 0.5, "欠測 %.0f %%、外れ %.0f %%" % (100 * sr["missing"],
                                                                               100 * sr["false"]))
    fr = S["fringe"]["resin"]
    gate("半透明の樹脂の縞投影: 一様な偏り(40 µm 以上沈む)であって、平らな所の形の外れは 2 割未満",
         fr["bias"] <= -0.04 and fr["per"]["flat"]["false"] < 0.2,
         "偏り %+.0f µm、平らな所の外れ %.0f %%" % (1e3 * fr["bias"], 100 * fr["per"]["flat"]["false"]))
    # 黒のステレオは門にしない(0.1 mm 超が 6 % 対 1 % の小さい数どうしの比で、仕組み「光沢の写り方が 2 台で違う」を
    # 別に確かめていない。2026-11-08 の再レビュー)
    print("   (参考)黒のステレオの 0.1 mm 超: %.1f %%(つや消し %.1f %%)"
          % (100 * S["stereo"]["black"]["false"], 100 * S["stereo"]["matte"]["false"]))
    ps = seeds["ps_step"]
    gate("照度差ステレオ: 段差はどの種でも 1 mm 以上外れる(壁の法線が撮れず、積分で段が消える)",
         min(abs(v) for v in ps) >= 1.0, "種 %d 通りで %s mm" % (len(ps), " / ".join("%+.2f" % v for v in ps)))
    d50 = {m: dents[m][0][0] for m in METHODS}
    # 「読めない」= 値が出ないか、誤差が打痕の深さ 50 µm を超える(前の版は「値が出ない」だけで判定していて、ToF の
    # 画素を 0.2 mm にすると +1023 µm の雑音の値が出て NG になった —— 門の判定の仕方の誤り。2026-11-08 の再レビュー)
    tof_cant = (not np.isfinite(d50["tof"])) or abs(d50["tof"]) > 50
    gate("打痕 50 µm: つや消しで縞投影・光切断・照度差ステレオは ±20 µm 以内に読み、ToF(画素 %.1f mm)は読めない"
         "(値が出ないか誤差 50 µm 超)" % TOF_PITCH,
         all(np.isfinite(d50[m]) and abs(d50[m]) <= 20 for m in ("fringe", "laser", "ps")) and tof_cant,
         "縞 %+.0f / 光切断 %+.0f / 照度差 %+.0f / ステレオ %+.0f µm / ToF %s" % (
             d50["fringe"], d50["laser"], d50["ps"], d50["stereo"],
             "%+.0f µm" % d50["tof"] if np.isfinite(d50["tof"]) else "値が出ない"))
    a = acc
    # ★門の経緯(2026-11-08、消さずに残す):
    #   (1) 最初の門は「全部の点の PF が縞投影・光切断は 0.1 mm 以下、ToF は 1 mm 超」。画素 0.1 mm(CI)で通り、
    #       画素 0.05 mm(full)で光切断が 0.110 mm になって NG。PF は範囲(最大 − 最小)なので点が多いほど大きい。
    #   (2) 光切断を外した比の門に書き直したのは、結果を見て門を動かした形だったので戻した。
    #   (3) 点を 200 にそろえた PF で同じ主張を確かめたが、種 77 の 1 回の抽選(下側 5 %)に頼っていた。
    #   (4) 200 回の抽選の中央値・外れ点の除外なし(全部の点の列とそろえる)にすると、full で光切断が 0.104 mm
    #       (5〜95 % 0.077〜0.129)となり、**光切断の PF ≤ 0.1 mm は成り立たない**。CI(画素 0.1 mm)では 0.071 で通る
    #       —— 画素で合否が変わる主張は立てない。光切断は「約 0.1 mm」として表と印字に出し(限界)、門に残すのは
    #       画素に依らず成り立つ「縞投影 ≤ 0.1 mm、ToF > 1 mm」だけ(再レビューの提案の書き方)
    lm = a[("laser", "matte")]
    print("   (限界)光切断のつや消しの PF: 200 点の中央 %.3f mm(5〜95 %% %.3f〜%.3f)、全部の点 %.3f mm —— 約 0.1 mm で、"
          "0.1 mm 以下とは言えない(画素 0.1 mm では 0.07 mm 前後)" % (lm["pf_eq"], lm["pf_eq_lo"], lm["pf_eq_hi"], lm["pf"]))
    gate("受入試験の物差し(つや消し、点を %d にそろえた %d 回の抽選の中央値): 探針の誤差 PF は縞投影が 0.1 mm 以下、"
         "ToF(画素 0.4 mm)は 1 mm 超" % (ACC_N_EQ, ACC_N_DRAW),
         a[("fringe", "matte")]["pf_eq"] <= 0.1 and a[("tof", "matte")]["pf_eq"] > 1.0,
         "PF(%d 点の中央)縞 %.3f / ToF %.3f mm(光切断 %.3f mm は門に入れない)" % (
             ACC_N_EQ, a[("fringe", "matte")]["pf_eq"], a[("tof", "matte")]["pf_eq"], lm["pf_eq"]))
    gate("受入試験の物差し(点を %d にそろえる): 金属光沢にすると縞投影の PF がつや消しの 5 倍以上に悪くなる" % ACC_N_EQ,
         a[("fringe", "metal")]["pf_eq"] >= 5 * a[("fringe", "matte")]["pf_eq"],
         "%.3f → %.3f mm" % (a[("fringe", "matte")]["pf_eq"], a[("fringe", "metal")]["pf_eq"]))
    lf = cond["laser_flat"]
    ratios = [r["sim_um"] / r["dorsch_um"] for r in lf]
    print("   (参考)光切断の雑音と Dorsch × √(w/L) の比: %s(門にしない —— 粒の大きさを誤っても比は画素で動かないので、"
          "物理の検査にならない)" % " / ".join("%.2f" % v for v in ratios))
    f = mb["frac"]
    gate("実写ステレオ: 縁の外側は太る > 浮く、bad-2 は縁でそれ以外の 5 倍以上",
         f["fat"] > f["fly"] and mb["bad2_edge"] >= 5 * mb["bad2_rest"],
         "太る %.1f / 浮く %.1f %%、bad-2 %.1f / %.1f %%" % (100 * f["fat"], 100 * f["fly"], 100 * mb["bad2_edge"],
                                                         100 * mb["bad2_rest"]))
    if tl is not None:
        for name, t in (("カラーの格子で 3 画素", tl), ("深度の元の格子で 3 画素", tl_native)):
            gate("T-LESS(%s): ToF は縁の外側が浮き(構造化光の 3 倍以上)、構造化光は太る(ToF より多い)" % name,
                 t["tof"]["outside_fly"] >= 3 * t["sl"]["outside_fly"]
                 and t["sl"]["outside_fat"] > t["tof"]["outside_fat"],
                 "浮く ToF %.1f / 構造化光 %.1f %%、太る 構造化光 %.1f / ToF %.1f %%" % (
                     100 * t["tof"]["outside_fly"], 100 * t["sl"]["outside_fly"], 100 * t["sl"]["outside_fat"],
                     100 * t["tof"]["outside_fat"]))
    # 空の表明の門: どのマスも数字が有限で、0.1 mm の外れが方式・材質で大きく散らばること
    allv = np.array([[S[m][mk]["false"] for mk in MAT_ORDER] for m in METHODS])
    gate("地図が空でも一様でもない(0.1 mm を超える外れが 5 % 未満〜80 % 超まで散らばる)",
         np.isfinite(allv).all() and allv.min() < 0.05 and allv.max() > 0.8,
         "外れ %.1f〜%.1f %%" % (100 * allv.min(), 100 * allv.max()))


def _material_lines(M):
    """動画の字幕(材質ごと)。どれも同じ実行の数字から組む。"""
    S = {m: {mk: M[m][mk]["score"] for mk in MAT_ORDER} for m in METHODS}
    best = {}
    for mk in MAT_ORDER:
        best[mk] = min(METHODS, key=lambda m: S[m][mk]["false"] + S[m][mk]["missing"])
    return {
        "matte": "つや消し: 0.1 mm の外れ 縞 %.0f%%・ステレオ %.0f%%・光切断 %.0f%%・ToF %.0f%%。照度差は段差を失う"
                 % tuple(100 * S[m]["matte"]["false"] for m in ("fringe", "stereo", "laser", "tof")),
        "metal": "金属光沢: 縞投影の V 溝は %.0f%% が 2 回反射で外れ、ToF は露光が鏡面に合わさり %.0f%% が 1 mm 超外れ"
                 % (100 * S["fringe"]["metal"]["per"]["groove"]["false"], 100 * S["tof"]["metal"]["coarse"]),
        "resin": "半透明の樹脂: ステレオは模様がにじんで %.0f%% 欠測、縞投影は一様に %+.0f µm 沈む(形は崩れない)"
                 % (100 * S["stereo"]["resin"]["missing"], 1e3 * S["fringe"]["resin"]["bias"]),
        # ★ステレオの黒の外れは画素で大きく変わる(0.1 mm で 37 %、0.05 mm で 6 %)ので、画素を値と並べる
        "black": "黒: 縞・光切断は露光で補える。ステレオは画素 %.2f mm で %.0f%% 外れる(光沢の違いと見られる)"
                 % (PITCH, 100 * S["stereo"]["black"]["false"]),
    }


def make_figures(M, mb, tl, cond, seeds, acc):
    """図 1〜5 と動画 1 本を書く(図を出す実行だけ)。"""
    figs.save("map", fig_map(M),
              caption="同じ部品(段差・止まり穴・斜面・V 溝・リブ・浅い打痕)を 4 つの材質で、ステレオ・縞投影・間接 ToF・"
                      "光切断・照度差ステレオの 5 方式で測った形。灰 = 欠測、橙 = 全方式共通の 0.1 mm を超える外れ。"
                      "三角測量の角はステレオ・縞投影・光切断とも 30°。撮像は物理で描き、高さへの戻しは Fullseye の op。"
                      "照度差ステレオの高さの定数は真値に合わせた(形の外れは偏りを引いて数えるので、合わせ方に依らない)。")
    raws = {}
    for mk in ("matte", "metal"):
        r = {m: M[m][mk]["raw"] for m in METHODS}
        tof_amp = r["tof"]["amp"] / max(float(np.percentile(r["tof"]["amp"], 99)), 1e-12)
        mid = int(round((8.3 + X_SHIFT) / PITCH))
        ks = M["laser"][mk]["raw"]["kept_ids"]
        lf = r["laser"]["frames"][ks.index(mid)].T
        raws[mk] = {"stereo": r["stereo"]["left"], "fringe": r["fringe"]["images"][-FR_STEPS],
                    "tof": np.clip(tof_amp, 0, 1), "laser": np.clip(lf, 0, 1),
                    "ps": r["ps"]["images"][0]}
    figs.save("raw", fig_raw(raws),
              caption="装置が撮る生の画像(上 = つや消し、下 = 金属光沢)。ステレオの左、縞投影の 1 枚(周期 1 mm)、"
                      "ToF の振幅(画素 0.4 mm)、光切断の 1 コマ(部屋の明かりつき)、照度差ステレオの 1 灯目。"
                      "カメラの像はレンズのぼけと周辺減光を通してある。")
    hdr = ["方式", "材質", "雑音 mm", "偏り µm", "欠測 %", "外れ0.1 %", "外れ1 %", "段差 Δmm", "穴 Δmm", "斜面 Δ°",
           "V溝 Δmm", "リブ Δmm", "打痕50 Δµm", "打痕15 Δµm"]
    rows = []
    for m in METHODS:
        tf = true_features(M[m]["matte"]["pitch"])
        for mk in MAT_ORDER:
            s = M[m][mk]["score"]
            f = s["features"]

            def dd(k, sc=1.0, fmt="%+.2f"):
                return "測れず" if not np.isfinite(f[k]) else fmt % (sc * (f[k] - tf[k]))
            rows.append([METHOD_JA[m], MATERIALS[mk]["ja"], "%.4f" % s["noise"] if np.isfinite(s["noise"]) else "―",
                         "%+.0f" % (1e3 * s["bias"]), "%.1f" % (100 * s["missing"]), "%.1f" % (100 * s["false"]),
                         "%.1f" % (100 * s["coarse"]), dd("step"), dd("hole"), dd("slope", fmt="%+.1f"), dd("groove"),
                         dd("rib"), dd("dent50", 1e3, "%+.0f"), dd("dent15", 1e3, "%+.0f")])
    figs.save_table("numbers", hdr, rows, title="5 方式 × 4 材質の数字(寸法は 測った − 真値)",
                    caption="雑音 = 平らな所の真値との差の頑健な標準偏差。偏り = 平らな所の差の中央値。外れ = 偏りを引いた差が"
                            "全方式共通の 0.1 mm / 1 mm を超えた有効画素の割合。照度差ステレオの偏りは真値に合わせた後の値。")
    figs.save_table("conditions", ["方式", "条件", "雑音 µm", "0.1 mm の外れ %", "備考"], cond["rows"],
                    title="条件を振ると順位が動く(つや消し)",
                    caption="ステレオの輻輳角・カメラの画素・ToF の画素を振った雑音。光切断は模様の無い平らな板で、"
                            "Dorsch の式とその op の独立なコヒーレント結像のシミュと並べた。")
    arow = []
    for (m, mk), r in acc.items():
        eq = ("―" if not np.isfinite(r["pf_eq"]) else
              "%.3f(%.3f〜%.3f)" % (r["pf_eq"], r["pf_eq_lo"], r["pf_eq_hi"]))
        arow.append([METHOD_JA[m], MATERIALS[mk]["ja"],
                     "―" if not np.isfinite(r["pf"]) else "%.3f" % r["pf"], eq,
                     "―" if not np.isfinite(r["sphere_resid"]) else "%.4f" % r["sphere_resid"]]
                    + ["―" if not np.isfinite(r[k]) else ("%.3f" if k == "f" else "%+.3f") % r[k]
                       for k in ("ps", "sd", "f")] + [str(r["n"])])
    figs.save_table("acceptance", ["方式", "材質", "PF 全点 mm", "PF %d 点 中央(5〜95 %%)" % ACC_N_EQ, "残差 RMS mm",
                                   "PS mm", "SD mm", "F mm", "球の点"], arow,
                    title="受入試験の物差しで 5 方式を並べる(球 2 つ・平らな板)",
                    caption="VDI/VDE 2634 Part 2 の考え方の評価量(準拠ではない)。評価 op は poc_virtual_acceptance_3d と同じ "
                            "sphere_probing_error / sphere_spacing_error / plane_flatness_error。直径 8 mm の球 2 つ(間隔 20 mm)と"
                            "平らな板を、同じ撮像と復号で測った点群に当てた。")
    real = None
    if tl is not None:
        real = fig_real(tl, mb)
        figs.save("real", real, source="Hodaň et al., T-LESS: An RGB-D Dataset for 6D Pose Estimation of "
                  "Texture-less Objects, WACV 2017, https://doi.org/10.1109/WACV.2017.8, CC BY 4.0(切り出して表示)",
                  caption="実データ: 同じ場面を構造化光と ToF の深度センサで撮った深度(T-LESS)。縁の外 1〜3 画素で、"
                          "構造化光は物体の深度のまま太り(橙)、ToF は物体と背景の間に浮く(青)。実データが支えるのは"
                          "この縁の外側の向きだけで、材質の主張はシミュだけ。")
    lines = _material_lines(M)
    conc = cond["video_lines"] + [
        "金属は鏡面で、樹脂は内部散乱で、方式ごとに別の壊れ方をする(シミュ)。",
        "照度差ステレオは段差を失うが、浅い打痕は読める。",
        "縁の外側: 構造化光とステレオは太り、ToF は浮く(実データ 2 つ)。"]
    frames = make_video(M, tl, mb, {"raw_matte": _video_raw(M), "material_lines": lines,
                                     "map_table": map_table_image(M), "real": real, "conclusion": conc})
    figs.save_video("explained", frames, fps=VIDEO_FPS, gif_every=5, gif_fps=2.0, gif_width=480,
                    caption="何を入れ(同じ部品・4 材質)→ 何を比べ(5 方式の生の画像と測った形)→ 何が分かったか"
                            "(どこで壊れるか)を約 %d 秒で。" % int(round(len(frames) / VIDEO_FPS)))
    _audit(frames)


def _video_raw(M):
    r = {m: M[m]["matte"]["raw"] for m in METHODS}
    tof_amp = r["tof"]["amp"] / max(float(np.percentile(r["tof"]["amp"], 99)), 1e-12)
    return {"stereo_l": r["stereo"]["left"], "stereo_r": r["stereo"]["right"],
            "fringe_all": list(r["fringe"]["images"]), "tof": np.clip(tof_amp, 0, 1),
            "laser_all": [np.clip(f.T, 0, 1) for f in r["laser"]["frames"]], "ps_all": list(r["ps"]["images"])}


def _audit(frames):
    """依頼時だけ、先頭・中間・末尾と 12 コマの接触印画を repo の外へ書く(``FULLSEYE_AUDIT_DIR``)。"""
    root = os.environ.get("FULLSEYE_AUDIT_DIR", "").strip()
    if not root:
        return
    from PIL import Image
    out = Path(root) / "poc_3d_sensor_modalities"
    out.mkdir(parents=True, exist_ok=True)
    for fn, i in (("f000.png", 0), ("f_mid.png", len(frames) // 2), ("f_end.png", len(frames) - 1)):
        Image.fromarray(frames[i]).save(out / fn)
    ids = np.linspace(0, len(frames) - 1, 12).round().astype(int)
    sheet = Image.new("RGB", (1280, 540), BG)
    for k, i in enumerate(ids):
        sheet.paste(Image.fromarray(frames[i]).resize((320, 180), Image.Resampling.LANCZOS), ((k % 4) * 320, (k // 4) * 180))
    sheet.save(out / "contact.png")


# --------------------------------------------------------------------------- #
# 本体
# --------------------------------------------------------------------------- #
#: T-LESS を手元で測った値(データが無い実行 = CI で印字だけする。門にはしない —— 定数どうしを比べても空の門)
RECORDED_TLESS = {
    "sl": {"interior_sigma_mm": 4.0383, "interior_miss": 0.0156, "interior_out": 0.0899, "outside_fly": 0.0544,
           "outside_fat": 0.3354, "outside_n": 23131, "n_images": 12},
    "tof": {"interior_sigma_mm": 4.3547, "interior_miss": 0.0030, "interior_out": 0.1113, "outside_fly": 0.4835,
            "outside_fat": 0.1799, "outside_n": 20145, "n_images": 12},
}
RECORDED_TLESS_NATIVE = {
    "sl": {"outside_fly": 0.1137, "outside_fat": 0.1894, "outside_n": 38690, "ring_px": 6},
    "tof": {"outside_fly": 0.5180, "outside_fat": 0.0445, "outside_n": 18579, "ring_px": 9},
}

_FAILS = []


def gate(name, ok, detail):
    print("   [%s] %s —— %s" % ("OK" if ok else "NG", name, detail))
    if not ok:
        _FAILS.append(name)


class _Conditions:
    """格子の細かさ・ステレオの角・ToF の画素を一時的に変える(抜けると元に戻す)。"""

    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        g = globals()
        self.old = {k: g[k] for k in ("PITCH", "FINE", "ST_ANGLE", "TOF_PITCH", "H_MM")}
        for k, v in self.kw.items():
            g[k] = v
        if "PITCH" in self.kw:
            g["FINE"] = self.kw["PITCH"] / SS
        _GROOVE_F.clear()
        return self

    def __exit__(self, *exc):
        globals().update(self.old)
        _GROOVE_F.clear()
        return False


def laser_flat_noise(pitch, n_frames=40, seed=1):
    """模様の無い平らな板(高さ 3 mm、つや消し)を光切断で測った雑音と、op の独立なシミュ・Dorsch の式。

    ``dorsch_pure_um`` = Dorsch の式そのもの C·λ/(2π sin u sin θ)(w = L として √(w/L) = 1 にした値)。
    ``dorsch_um`` = op の閉形式 = Dorsch × √(w/L)(√(w/L) は op が「実測の規則で、Dorsch の式の一部ではない」と書く)。"""
    with _Conditions(PITCH=pitch):
        sc = Scene("matte")
        sc.h = np.full_like(sc.h, 3.0)
        sc.albedo[:] = MATERIALS["matte"]["rho"]
        sc.n[...] = np.array([0.0, 0.0, 1.0])
        ncols = int(round(W_MM / pitch))
        fr = np.linspace(10, ncols - 10, n_frames).astype(int)
        r = measure_laser(sc, np.random.default_rng(seed), frames=fr)
        e = r["z"][:, fr] - 3.0
        sim = robust_sigma(e.ravel())
        cf = lightsection.light_section_speckle_floor(
            wavelength_um=LS_LAMBDA_UM, sin_u_obs=LS_SIN_U, sin_theta=np.sin(np.radians(LS_CAM)),
            # ★line_width_um は op の約束で「カメラから見た」光条の 1/e² の半幅 w(強度 exp(−2y²/w²))。光条は 2σ、
            #   カメラ(30°)からは cos 30° 倍に縮んで見える。参照の細かさは 1 標本 ≤ 6.25 µm(16 倍、強度のナイキスト
            #   8.1 µm より細かい)、試行 16 回(χ² の 95 % 区間 約 ±5 %)。前の版(8 倍・4 回)は参照が粗く、
            #   「1 画素で平均すると op も式を下回る」と誤って読んだ(2026-11-08 の再レビュー)
            line_width_um=2000.0 * LS_SIGMA * np.cos(np.radians(LS_CAM)), pixel_um=1000.0 * pitch,
            length_um=1000.0 * pitch, n_trials=16, n_columns=64, n_rows=96, pixel_oversample=16)
        pure = float(lightsection.light_section_speckle_floor(
            wavelength_um=LS_LAMBDA_UM, sin_u_obs=LS_SIN_U, sin_theta=np.sin(np.radians(LS_CAM)),
            line_width_um=1000.0 * pitch, pixel_um=1000.0 * pitch, length_um=1000.0 * pitch, n_trials=2,
            n_columns=16, n_rows=32, pixel_oversample=16)["closed_form_delta_z_um"])
    return {"pitch": pitch, "sim_um": 1e3 * sim, "dorsch_um": float(cf["closed_form_delta_z_um"]),
            "dorsch_pure_um": pure, "op_ci": tuple(float(v) for v in cf["sim_ci95_um"]),
            "op_sim_um": float(cf["sim_delta_z_um"]), "bias_um": 1e3 * float(np.nanmedian(e))}


def closed_form_chapter(M):
    """1. 雑音の床を式と突き合わせる(つや消しの平らな所)。どれが独立な検証で、どれが実装の検算かを分けて書く。"""
    print("\n1. 雑音の床を式と突き合わせる(つや消し、平らな所の真値との差の頑健な標準偏差)")
    reg = regions(PITCH)
    fr = M["fringe"]["matte"]
    pred = float(np.nanmedian(fr["raw"]["sigma_z_pred"][reg["flat"] & fr["raw"]["valid"]]))
    meas = fr["score"]["noise"]
    print("   縞投影(実装の検算): 同じ像から読んだ σ_I と振幅 b を σ_z = k·√(2/N)·σ_I/b に入れた値 %.2f µm、実測 %.2f µm"
          "(比 %.2f)。像の雑音が位相の復号を通って式どおりに高さへ伝わるかの検算で、外からの真値ではない"
          % (1e3 * pred, 1e3 * meas, meas / pred))
    tf = M["tof"]["matte"]
    regt = regions(TOF_PITCH)
    refl = box(tf["raw"]["refl_flat"], int(round(TOF_PITCH / FINE)))
    rho = float(np.median(refl[regt["flat"]]))
    g = tf["raw"]["gain"]
    nb = itof.itof_noise_budget(TOF_F, TOF_SIGNAL * g * rho, 0.5, TOF_AMBIENT * g, TOF_READ, 4)
    pred_t = 1e3 * float(nb["depth_sigma"])
    meas_t = tf["score"]["noise"]
    print("   間接 ToF(実装の検算): itof_noise_budget に装置の値だけ(信号 %.0f 電子 × 反射率 %.2f、背景光、読み出し)を"
          "入れた %.3f mm、実測 %.3f mm(比 %.2f)。同じショット雑音のモデルの解析式なので、独立な検証ではない"
          % (TOF_SIGNAL * g, rho, pred_t, meas_t, meas_t / pred_t))
    # 画素は光条(σ 0.1 mm)が 1 画素以上にかかる範囲で振る(0.2 mm だと光条が 0.5 画素で、スペックルでなく
    # 画素の固着で 45 µm になる = 装置の設計の外)
    lf = [laser_flat_noise(p) for p in sorted({PITCH, 0.08, 0.10})]
    for r in lf:
        print("   光切断(模様の無い平らな板、画素 %.2f mm): 実測 %.1f µm | op の独立な 2-D コヒーレント結像のシミュ %.1f µm"
              "(95 %% 区間 %.1f〜%.1f、比 %.2f)| Dorsch × √(w/L)(op の経験則つき)%.1f µm(比 %.2f)| Dorsch の式そのもの"
              " %.2f µm(比 %.2f)| 偏り %+.1f µm"
              % (r["pitch"], r["sim_um"], r["op_sim_um"], r["op_ci"][0], r["op_ci"][1], r["sim_um"] / r["op_sim_um"],
                 r["dorsch_um"], r["sim_um"] / r["dorsch_um"], r["dorsch_pure_um"], r["sim_um"] / r["dorsch_pure_um"],
                 r["bias_um"]))
    ro = [r["op_sim_um"] / r["dorsch_um"] for r in lf]
    print("   ★op のシミュ自身は Dorsch × √(w/L) の %.2f〜%.2f 倍(既存の 2 本の 0.87〜0.93 と同じ)。この PoC のスペックルは"
          "1 次元の場を光条に沿う向きに独立に平均する近似で、画素 0.05 mm だけ op より低い分は**未解決**"
          "(候補: 光条に沿う独立な場の数の丸め、光条が 2 画素にしか乗らないこと)" % (min(ro), max(ro)))
    gate("縞投影: 実装の検算(比 0.8〜1.3)", 0.8 <= meas / pred <= 1.3, "%.2f" % (meas / pred))
    gate("ToF: 実装の検算(比 0.8〜1.25)", 0.8 <= meas_t / pred_t <= 1.25, "%.2f" % (meas_t / pred_t))
    # 帯は走らせる前に決めた物理の帯: 参照(op、試行 16 回)の 95 % 区間 ±5 % と、この PoC の 1 次元の近似の
    # 許し ±15 % を足した 0.8〜1.2。どれか 1 つの画素でも外れれば門が NG になる(PoC が落ちる)。帯の中でも
    # 画素 0.05 mm の 13 % の差は原因が分からないので「未解決」と印字する
    LS_BAND = (0.8, 1.2)
    ok_l = [LS_BAND[0] <= r["sim_um"] / r["op_sim_um"] <= LS_BAND[1] for r in lf]
    gate("光切断: スペックルの雑音は同じ条件の op の独立なコヒーレント結像のシミュと一致する(比 0.8〜1.2、全部の画素で)",
         all(ok_l), " / ".join("%.2f" % (r["sim_um"] / r["op_sim_um"]) for r in lf))
    return {"fringe": (pred, meas), "tof": (pred_t, meas_t), "laser_flat": lf}


def conditions_chapter(M, cf):
    """4. 条件を振ると順位が動く(つや消しの雑音と 0.1 mm の外れ)。勝ち負けを条件で決めない。"""
    print("\n4. 条件を振る(つや消し): ステレオの輻輳角・カメラの画素・ToF の画素")
    rows = []

    def one(method, label, **kw):
        with _Conditions(**kw):
            sc = Scene("matte")
            z, pitch, raw = measure(method, sc, np.random.default_rng(11), {})
            s = score(z, pitch)
        rows.append([METHOD_JA[method], label, "%.1f" % (1e3 * s["noise"]), "%.1f" % (100 * s["false"]), ""])
        print("   %-8s %-28s 雑音 %8.1f µm  0.1 mm の外れ %5.1f %%" % (METHOD_JA[method], label, 1e3 * s["noise"],
                                                                 100 * s["false"]))
        return s

    base = {m: M[m]["matte"]["score"] for m in METHODS}
    for m, lab in (("stereo", "±%.0f°・画素 %.2f mm(本表)" % (ST_ANGLE, PITCH)),
                   ("fringe", "30°・画素 %.2f mm(本表)" % PITCH), ("tof", "画素 %.1f mm(本表)" % TOF_PITCH)):
        rows.append([METHOD_JA[m], lab, "%.1f" % (1e3 * base[m]["noise"]), "%.1f" % (100 * base[m]["false"]), "本表"])
        print("   %-8s %-28s 雑音 %8.1f µm  0.1 mm の外れ %5.1f %%" % (METHOD_JA[m], lab, 1e3 * base[m]["noise"],
                                                                 100 * base[m]["false"]))
    s5 = one("stereo", "±5°・画素 %.2f mm" % PITCH, ST_ANGLE=5.0)
    one("stereo", "±15°・画素 %.2f mm" % (2 * PITCH), PITCH=2 * PITCH)
    one("fringe", "30°・画素 %.2f mm" % (2 * PITCH), PITCH=2 * PITCH)
    # 画素を半分にしたとき: 同じ光学なら 1 画素に入る光は 1/4。電子数を据え置いた行(感度の高いセンサか近い距離)と、
    # 1/4 にした行(同じ装置で画素だけ細かい)の両方を出す
    t2 = one("tof", "画素 %.1f mm・電子数は画素あたり据え置き" % (TOF_PITCH / 2), TOF_PITCH=TOF_PITCH / 2)
    global TOF_SIGNAL, TOF_AMBIENT
    keep_sig = (TOF_SIGNAL, TOF_AMBIENT)
    TOF_SIGNAL, TOF_AMBIENT = keep_sig[0] / 4, keep_sig[1] / 4
    try:
        t4 = one("tof", "画素 %.1f mm・電子数 1/4(同じ光学)" % (TOF_PITCH / 2), TOF_PITCH=TOF_PITCH / 2)
    finally:
        TOF_SIGNAL, TOF_AMBIENT = keep_sig
    for r in cf["laser_flat"]:
        rows.append([METHOD_JA["laser"], "30°・画素 %.2f mm(平らな板)" % r["pitch"], "%.1f" % r["sim_um"], "",
                     "op のシミュ %.1f / Dorsch×√(w/L) %.1f / Dorsch %.1f µm" % (r["op_sim_um"], r["dorsch_um"],
                                                                          r["dorsch_pure_um"])])
    lp = [r for r in cf["laser_flat"] if abs(r["pitch"] - PITCH) < 1e-9][0]
    order = sorted([(base["fringe"]["noise"], "縞"), (base["stereo"]["noise"], "ステレオ"),
                    (lp["sim_um"] / 1e3, "光切断(平らな板)"), (base["tof"]["noise"], "ToF")])
    lines = ["雑音の順は条件で動く。画素 %.2f mm・三角測量 30° では" % PITCH,
             " " + " < ".join("%s %s" % (n, ("%.0f µm" % (1e3 * v)) if v < 0.5 else ("%.1f mm" % v)) for v, n in order),
             "±5° のステレオ %.0f µm。ToF 画素半分: 据え置き %.1f mm / 同じ光学 %.1f mm"
             % (1e3 * s5["noise"], t2["noise"], t4["noise"])]
    print("   → 雑音の順(本表の条件): " + " < ".join("%s %.4f" % (n, v) for v, n in order))
    return {"rows": rows, "video_lines": lines, "laser_flat": cf["laser_flat"]}


ACC_MATERIALS = ("matte", "metal")
#: 球の当てはめに使う点: 真上から見て中心から半径の 0.9 倍まで(赤道の近くの急な面は、どの方式でも欠けるか外れる)
ACC_CAP = 0.9
#: PF をそろえた点の数で比べる(PF は範囲 = 最大 − 最小なので点が多いほど大きく出る。ToF の画素 0.4 mm で球に
#: 約 240 点しか乗らないので、その下の 200 点にそろえる)
ACC_N_EQ = 200
ACC_N_DRAW = 200
#: 外れ点の除外は 0 にそろえる(全部の点も 200 点も同じ規則。VDI/VDE 2634 の考え方の最大 0.3 % の除外は使わない)


def acceptance_chapter():
    """5. 受入試験の物差し(``poc_virtual_acceptance_3d`` と同じ評価 op)で 5 方式を並べる。

    VDI/VDE 2634 Part 2 の考え方の評価量 —— 探針の誤差 PF(形)・PS(寸法)、球間距離の誤差 SD、平面度 F ——
    を、試験体(直径 8 mm の球 2 つ・間隔 20 mm、平らな板)を 5 方式で撮った点群に ``fs.ledger`` の
    ``sphere_probing_error`` / ``sphere_spacing_error`` / ``plane_flatness_error`` で当てる。どの方式にも同じ評価量・
    同じ試験体なので、方式ごとに物差しが違うことは起きない。★準拠ではなく考え方に沿った評価(規格の値は使わない)。
    ★試験体は片側からしか見えない球冠で、赤道の近くは使わない(``ACC_CAP``)。
    """
    print("\n5. 受入試験の物差し(探針の誤差 PF・PS、球間距離の誤差 SD、平面度 F。評価 op は acceptance3d と同じ)")
    print("   試験体: 平らな板の上に直径 %.0f mm の球 2 つ(中心の間隔 %.0f mm)。球は真上から半径の %.1f 倍まで使う"
          % (ART_SPHERE_D, ART_CENTERS[1][0] - ART_CENTERS[0][0], ACC_CAP))
    print("   %-10s %-10s %8s %24s %8s %8s %8s %8s %7s" % (
        "方式", "材質", "PF 全点", "PF %d 点の中央(5〜95 %%)" % ACC_N_EQ, "残差RMS", "PS mm", "SD mm", "F mm", "点の数"))
    out = {}
    L = float(np.hypot(ART_CENTERS[1][0] - ART_CENTERS[0][0], ART_CENTERS[1][1] - ART_CENTERS[0][1]))
    r = ART_SPHERE_D / 2
    with _Conditions(H_MM=ART_H_MM):
        _acceptance_rows(out, L, r)
    print("   ★PF・F は範囲(最大 − 最小)なので、同じ雑音でも点が多いほど大きく出る(正規の雑音で 200 点 約 5.5σ、"
          "16,000 点 約 8.3σ)。点の数に依らない比べ方は残差 RMS。点が 50 未満か直径の誤差が直径を超える当てはめは"
          "「球が定まらない」とした")
    return out


def _acceptance_rows(out, L, r):
    for m in METHODS:
        ref = {}
        for mk in ACC_MATERIALS:
            if mk != "matte" and not ref:
                measure(m, Scene("matte", kind="artifact"), np.random.default_rng(400), ref)
            sc = Scene(mk, kind="artifact")
            z, pitch, raw = measure(m, sc, np.random.default_rng(500 + METHODS.index(m)), ref)
            X, Y = grid(pitch)
            ok = np.isfinite(z)
            res = {"pf": np.nan, "ps": np.nan, "sd": np.nan, "f": np.nan, "n": 0, "pf_eq": np.nan,
                   "pf_eq_lo": np.nan, "pf_eq_hi": np.nan, "sphere_resid": np.nan}
            # ★キーを op と同じ名前(残差の二乗平均の 3 文字)にすると、op の例の索引(引用符つきの op 名を拾う)がこの PoC を op の例に数える
            pts = []
            for cx, cy in ART_CENTERS:
                sel = ok & (np.hypot(X - cx, Y - cy) < ACC_CAP * r)
                pts.append(np.stack([X[sel], Y[sel], z[sel]], 1))
            plane = ok & np.all([np.hypot(X - cx, Y - cy) > r + 1.5 for cx, cy in ART_CENTERS], axis=0) & (X > 1.0)
            try:
                a = fs.ledger.sphere_probing_error(pts[0], ART_SPHERE_D, exclude_fraction=0.0)
                b = fs.ledger.sphere_spacing_error(pts[0], pts[1], L, exclude_fraction=0.0)
                if len(pts[0]) >= ACC_N_EQ:
                    # 点の数をそろえた PF: ACC_N_EQ 点を ACC_N_DRAW 回選び直した中央値と 5〜95 %。PF は範囲なので 1 回の
                    # 抽選はくじ引き(前の版は種 77 の 1 回で、光切断は下側 5 % の値だった)。外れ点の除外は全部の点の側と
                    # そろえて 0(sphere_probing_error の既定 0.3 % は 200 点では 0 点、15,000 点では 44 点除く —— 列で規則が違った)
                    rg = np.random.default_rng(77)
                    v = [float(fs.ledger.sphere_probing_error(pts[0][rg.choice(len(pts[0]), ACC_N_EQ, replace=False)],
                                                             ART_SPHERE_D, exclude_fraction=0.0)["pf"])
                         for _ in range(ACC_N_DRAW)]
                    res["pf_eq"] = float(np.median(v))
                    res["pf_eq_lo"], res["pf_eq_hi"] = (float(x) for x in np.percentile(v, [5, 95]))
                if a["n_points"] < 50 or abs(a["ps"]) > ART_SPHERE_D:
                    res.update(n=int(a["n_points"]), why="球が定まらない(点 %d、直径 %.1f mm)"
                               % (a["n_points"], a["diameter"]), pf_eq=np.nan, pf_eq_lo=np.nan, pf_eq_hi=np.nan)
                else:
                    res.update(pf=float(a["pf"]), ps=float(a["ps"]), sd=float(b["sd"]), n=int(a["n_points"]),
                               sphere_resid=float(a["residual_rms"]))
            except ValueError as exc:
                res["why"] = str(exc)[:60]
            if plane.sum() >= 10:
                res["f"] = float(fs.ledger.plane_flatness_error(np.stack([X[plane], Y[plane], z[plane]], 1))["f"])
            out[(m, mk)] = res
            print("   %-10s %-10s %8.3f %8.3f(%.3f〜%.3f) %8.4f %+8.3f %+8.3f %8.3f %7d%s" % (
                METHOD_JA[m], MATERIALS[mk]["ja"], res["pf"], res["pf_eq"], res["pf_eq_lo"], res["pf_eq_hi"],
                res["sphere_resid"], res["ps"], res["sd"], res["f"], res["n"],
                ("  (" + res["why"] + ")") if "why" in res else ""))


def seeds_chapter():
    """6. 乱数の種を変える: 照度差ステレオの段差の誤差、黒の ToF の斜面の角度(幅で出す)。"""
    print("\n6. 乱数の種を変える(1 つの種の値を主張にしない)")
    tf = true_features(PITCH)
    ps, tb = [], []
    for k in range(3):
        sc = Scene("matte", seed=k)
        z, pitch, raw = measure("ps", sc, np.random.default_rng(100 + k), {})
        ps.append(feature_values(z, pitch)["step"] - tf["step"])
        ref = {}
        measure("tof", Scene("matte", seed=k), np.random.default_rng(200 + k), ref)
        zb, pb, _ = measure("tof", Scene("black", seed=k), np.random.default_rng(300 + k), ref)
        tb.append(feature_values(zb, pb)["slope"] - true_features(pb)["slope"])
    print("   照度差ステレオ(つや消し)の段差の誤差: %s mm" % " / ".join("%+.2f" % v for v in ps))
    print("   黒の ToF の斜面の角度の誤差: %s °(種で %.0f° も動く = 低い信号の雑音。系統の主張にしない)"
          % (" / ".join("%+.1f" % v for v in tb), max(tb) - min(tb)))
    return {"ps_step": ps, "tof_black_slope": tb}


def outside_chapter(M, mb, tl, tl_native):
    """3. 段差の縁の外側: 太る(上の面の高さのまま)/ 浮く(間)/ 欠ける。主張は実データ 2 つだけで立てる。"""
    print("\n3. 段差の縁のすぐ外側(低い側 1〜3 画素)は何になるか —— 太る / 浮く / 欠ける / 正しい")
    print("   シミュ(参考。壁 4 枚 × 3 列 = 12 標本で、部品を画素の格子からずらすと入れ替わるので主張にしない):")
    for m in METHODS:
        o = M[m]["matte"]["score"]["outside"]
        print("     %-8s 太る %3.0f %%  浮く %3.0f %%  欠ける %3.0f %%  正しい %3.0f %%"
              % (METHOD_JA[m], 100 * o["fat"], 100 * o["fly"], 100 * o["missing"], 100 * o["ok"]))
    f = mb["frac"]
    print("   実写ステレオ(Middlebury 2014 motorcycle、binocular_disparity_ms、前景の縁の外 %d 画素):" % mb["n"])
    print("     太る %.1f %%  浮く %.1f %%  欠ける %.1f %%  正しい %.1f %%   bad-2: 縁 %.1f %% / それ以外 %.1f %%"
          % (100 * f["fat"], 100 * f["fly"], 100 * f["missing"], 100 * f["ok"], 100 * mb["bad2_edge"],
             100 * mb["bad2_rest"]))
    if tl is None:
        print("   T-LESS: データが無いので記録値を印字するだけ(2026-11-08 に手元で測った値、門にはしない。置き場は環境変数 %s、"
              "取得は tools/fetch_tless_v2_sensors.py)" % TLESS_ENV)
        show = ((RECORDED_TLESS, "カラーの格子で 3 画素"), (RECORDED_TLESS_NATIVE, "深度の元の格子で 3 画素"))
    else:
        print("   T-LESS(同じ場面 %d 枚を 2 種類の深度センサで、CAD を真値の姿勢で置いた深度と比べる):"
              % tl["sl"]["n_images"])
        diff = max(max(abs(tl[k][f] - RECORDED_TLESS[k][f]) for f in ("interior_sigma_mm", "outside_fly",
                                                                       "outside_fat"))
                   for k in TLESS_SENSORS)
        diff = max(diff, max(abs(tl_native[k][f] - RECORDED_TLESS_NATIVE[k][f]) for k in TLESS_SENSORS
                             for f in ("outside_fly", "outside_fat")))
        gate("T-LESS の測り直しが記録値と一致(差 0.001 以内)", diff <= 1e-3, "最大の差 %.2g" % diff)
        show = ((tl, "カラーの格子で 3 画素"), (tl_native, "深度の元の格子で 3 画素"))
    for t, name in show:
        for k in TLESS_SENSORS:
            r = t[k]
            print("     %-26s %s: 太る %.1f %%  浮く %.1f %%(%d 画素)"
                  % (TLESS_SENSORS[k], name, 100 * r["outside_fat"], 100 * r["outside_fly"], r["outside_n"]))
    print("   ★T-LESS の深度はカラーの格子へ移してある(ToF は元の約 3 倍、構造化光は約 1.9 倍に引き伸ばし)。"
          "帯を元の画素で 3 画素にとっても向きは同じ —— 補間が「浮く」を作っているのではない")
    return tl


def dent_chapter(M):
    """7. 浅い打痕(50 µm・15 µm)はどの方式で見えるか。"""
    print("\n7. 浅い打痕(下の段の上、半径 0.8 mm)の深さ —— 測った − 真値(µm)。真値は同じ格子で測った値")
    out = {}
    for m in METHODS:
        row = []
        for mk in MAT_ORDER:
            f = M[m][mk]["score"]["features"]
            tf = true_features(M[m][mk]["pitch"])
            row.append(tuple(1e3 * (f[k] - tf[k]) if np.isfinite(f[k]) else float("nan") for k in ("dent50", "dent15")))
        out[m] = row
        print("   %-8s " % METHOD_JA[m] + "  ".join("%s %s/%s" % (MATERIALS[mk]["ja"][:2],
              "%+5.0f" % a if np.isfinite(a) else "  ―", "%+5.0f" % b if np.isfinite(b) else "  ―")
              for mk, (a, b) in zip(MAT_ORDER, row)))
    print("   (各マス = 打痕 50 µm / 15 µm。― = 測れない。15 µm は画素・レンズのぼけで動くので主張にしない)")
    return out


def main():
    t0 = time.perf_counter()
    print("PoC 2026.309: 同じ部品を 3-D センサの 5 方式で測り、どこで壊れるかを数える(%s)"
          % ("縮小版: 画素 %.2f mm、図なし" % PITCH if REDUCED else "画素 %.2f mm" % PITCH))
    print("\n0. 部品の寸法(真値): 段差 %.1f mm、穴 φ%.0f 深さ %.1f mm、斜面 %.2f°、V 溝 %.1f mm、リブ %.1f mm、"
          "打痕 %.0f / %.0f µm" % (TRUE_STEP, 2 * PART["hole"][2], TRUE_HOLE, TRUE_SLOPE_DEG, TRUE_GROOVE, TRUE_RIB,
                                  1e3 * PART["dents"][0][3], 1e3 * PART["dents"][1][3]))
    print("   撮像の条件: 三角測量の角 30°(ステレオ ±15°・縞投影・光切断)、画素 %.2f mm(ToF %.1f mm)、"
          "1 測定の撮像 ステレオ 2 枚 / 縞投影 12 枚 / ToF 4 段 / 照度差 8 枚 / 光切断 1 列に 1 コマ(%d コマ)、"
          "露光はどの方式もつや消しの 8 倍まで上げる自動露光" % (PITCH, TOF_PITCH, int(round(W_MM / PITCH))))
    print("   材質の値(反射率・粗さ・内部散乱の広がり)は著者が置いた値。出典があるのは鏡面の反射率だけ"
          "(アルミの垂直入射 約 0.9、屈折率 1.5 の Fresnel 0.04)")
    M = run_matrix()
    cf = closed_form_chapter(M)
    print_matrix(M)
    mb = middlebury_chapter()
    tl = tless_chapter()
    tl_native = tless_chapter(native=True) if tl is not None else None
    outside_chapter(M, mb, tl, tl_native)
    cond = conditions_chapter(M, cf)
    acc = acceptance_chapter()
    seeds = seeds_chapter()
    dents = dent_chapter(M)
    claims_chapter(M, mb, tl, tl_native, dents, cond, seeds, acc)
    if figs.enabled():
        make_figures(M, mb, tl, cond, seeds, acc)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
        _FAILS.append("figures")
    if _FAILS:
        print("\nFAIL: %d 件 —— %s" % (len(_FAILS), " / ".join(_FAILS)))
        raise SystemExit(1)
    print("\nPASS: 5 方式 × 4 材質を共通の物差し(0.1 mm / 1 mm)で数え、条件と乱数の種を振り、縁の外側の向きを"
          "実データ 2 つ(実写ステレオ・同じ場面の構造化光と ToF)で確かめた。実行 %.1f 秒" % (time.perf_counter() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
