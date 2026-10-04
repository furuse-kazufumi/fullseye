# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tacslip — 視触覚センサ(弾性膜 + カメラ)のマーカー配列から、せん断場・固着/滑り・接線力を読む(2026-10-04)。

物理シミュ × Fullseye 系列の第 2 弾の第 2 本(第 1 本 = :mod:`tacsim`、法線荷重の押し込みから力)。外から来る真値は 2 系統:
  * **閉形式**(K. L. Johnson, *Contact Mechanics*, CUP 1985, DOI 10.1017/CBO9781139171731):
      - Cattaneo (1938) / Mindlin (1949) の部分滑り(§7.2): 球を法線 P で押したまま接線 Q < μP を掛けると、固着円 c/a = (1 − Q/μP)^{1/3}、
        接線トラクション q = q′ − q″(q′ = μp0√(1−r²/a²)、q″ = μp0(c/a)√(1−r²/c²))、剛体球の接線変位 δx = 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}]、
        初期接線剛性 kt = 8Ga/(2−ν)。固着円内の表面接線変位は一様 = δx(2 つの Hertz 形トラクションの x², y² 項が打ち消す)。
      - Hertz 形の接線トラクション 1 個が円内に作る表面変位(式 3.91): ūx = (πq0/32Ga)[4(2−ν)a² − (4−3ν)x² − (4−ν)y²]、ūy = (πq0/32Ga)·2νxy。
      - 法線荷重の半径方向表面変位(式 3.41b): ūr = −(1−2ν)p0a²/(6Gr)[1 − (1−r²/a²)^{3/2}] (r ≤ a)、外側 −(1−2ν)p0a²/(6Gr)。
      - 接線点荷重の半空間表面解 = Cerruti(§3.6 式 3.22、Landau & Lifshitz 弾性理論 §8): ūx = (Qx/4πG)[2(1−ν)/r + 2νx²/r³]、
        ūy = (Qx/4πG)·2νxy/r³、ūz = −(Qx/4πG)(1−2ν)x/r²。
  * **有限要素の節点変位**(Robo-Touch/Taxim リポジトリ同梱、MIT ライセンス): 有限厚のドーム状ゲルの法線・斜め押し込み。半空間解が
    どこで外れるかを数にする第 2 真値(荷重の大きさは不明なので形だけ)。
  公表の定性値(W. Yuan, S. Dong, E. H. Adelson, *Sensors* 17(12):2762, 2017, DOI 10.3390/s17122762): 滑りは接触の周縁から始まり、
  マーカー変位の大きさのヒストグラムのエントロピーは部分滑りで増える。

自分で作った部分(正直に): 接触円の**外側**と滑り環の接線変位には閉形式が無いので Cerruti 核を画素平均で離散化して FFT で畳む
(:func:`cerruti_kernel` / :func:`cerruti_surface_displacement`、円内の閉形式 (3.91) と 0.02 %)。逆算は**相似則** —— Hertz 形トラクション
(半径 R、頂点 q0)の表面変位は q0·R·ĝ(x/R) なので、任意の固着半径 c の場は g(x) − (c/a)²g(x·a/c)(畳み込み 1 回、:func:`mindlin_model` /
:func:`mindlin_fit`)。マーカー像は「変位で中心を移してから描く」(補間で歪めない、:func:`membrane_render_markers`)。

被験者 = Fullseye の既存 op: :func:`blob2d.blob_label` / :func:`blob2d.blob_features`(重心)、:func:`pivops.piv_cross_correlate`(窓相関、
第 2 実装)、:mod:`backends_subpix` の副画素極値、:func:`backends_tactile.tac_shear_field`(構造テンソルのコヒーレンス、別被験者)、
:func:`measure.fit_circle`。Hertz の表(a・p0・P)は :func:`tacsim.hertz_sphere`。

試作で測って決めたこと(PoC の門に固定): (1) **規則格子に相関を当てると格子周期でエイリアスする** —— 8 px 格子を 5 px ずらすと PIV は
−3 px(= 5 − 8)、ジッタ格子なら 5 px。最近傍の対応も同じで、核の変位 6.4 px は隣の基準位置から 1.6 px なので偽の種になる → 対応は
**視野の縁(遠方場 = 小変位)から連続性で内側へ伸ばす**(:func:`marker_match_grow`)。(2) **小さい円盤の重心の pixel-locking** —— 半径 2 px で
±0.030 px、2.5 px で ±0.018 px の系統バイアスが副画素位相で符号を変え、基準像は格子全体が同じ位相なので場全体の共通モードになり c/a を
0.02 ずらした。反復ガウス重みの重心(σ = 半径)で 3 分の 1(:func:`marker_detect`)。剛体シフトを模型に足すのは 1/r の尾と縮退して逆効果。
(3) ūr の最大は r = a でなく r = 0.93a(ūr(a) の 1.022 倍)。(4) 滑り環で隣接マーカーの間隔が縮み、低しきい値の縞が繋がる → 成分は
高しきい値で切り、縞は距離変換で最近傍の本体へ。

規約: 長さ m、力 N、角 rad。画素座標は (x, y) = (列, 行)、マーカー中心の配列は (N, 2) の float。変位場の格子 (n, n) は :func:`tacsim._grid`
と同じ画素中心(中心 = ((n−1)/2, (n−1)/2))。G はせん断弾性率 E/(2(1+ν))。μ と Q は G・ν・a が既知なら別々に決まる(c は Q/μP だけで、
固着円の一様変位 δx が μP を与える)が、μ の誤差は c/a の誤差の 2c/(1−c²) 倍に増幅されるので低 Q ほど決まりにくい。
"""
from __future__ import annotations

import math
import os

import numpy as np
from scipy import ndimage

import blob2d as _blob

__all__ = [
    "mindlin_partial_slip", "mindlin_traction", "hertz_surface_ur", "hertzian_tangential_inner",
    "cerruti_kernel", "cerruti_surface_displacement", "membrane_shear_field",
    "membrane_markers", "displace_markers", "membrane_render_markers",
    "marker_image", "marker_detect", "marker_match_grow", "marker_track",
    "mindlin_model", "mindlin_fit", "stick_radius_modelfree", "slip_entropy",
    "fem_nodes_load", "fem_vs_halfspace",
]


# ----------------------------------------------------------------------------------------------------------------------
# 1. 閉形式(外部真値)
def mindlin_partial_slip(Q: float, hz: dict, mu: float, G: float, nu: float) -> dict:
    """Cattaneo–Mindlin の部分滑り(Johnson 1985 §7.2): 球を法線 P で押したまま接線 Q を掛ける。

    ``hz`` は :func:`tacsim.hertz_sphere` の表(a・F・p0)。返り: ``c``(固着半径 = a(1 − Q/μP)^{1/3})、``c_over_a``、``q_ratio`` = Q/μP、
    ``delta_x``(剛体球の接線変位 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}])、``k_t``(初期接線剛性 8Ga/(2−ν))、``slipping``(Q ≥ μP で True =
    全滑り。例外にせず印で返す: 滑りは物理的に起きる状態で入力の誤りではない)、入力の写し(``Q``・``muP``・``a``・``P``・``mu``・``G``・``nu``・``p0``)。
    **Raises** ValueError: Q < 0、μ ≤ 0、G ≤ 0、ν が [0, 0.5] の外、hz に a/F/p0 が無い。"""
    Q, mu, G, nu = float(Q), float(mu), float(G), float(nu)
    if not (Q >= 0.0) or not (mu > 0.0) or not (G > 0.0) or not (0.0 <= nu <= 0.5):
        raise ValueError("mindlin_partial_slip: need Q >= 0, mu > 0, G > 0, 0 <= nu <= 0.5")
    if not isinstance(hz, dict) or not all(k in hz for k in ("a", "F", "p0")):
        raise ValueError("mindlin_partial_slip: hz must be the dict from tacsim.hertz_sphere()")
    a, P = float(hz["a"]), float(hz["F"])
    muP = mu * P
    ratio = Q / muP
    s = max(0.0, 1.0 - ratio)
    c_over_a = s ** (1.0 / 3.0)
    return {"c": c_over_a * a, "c_over_a": c_over_a, "q_ratio": ratio, "delta_x": 3.0 * muP * (2.0 - nu) / (16.0 * G * a) * (1.0 - s ** (2.0 / 3.0)),
            "k_t": 8.0 * G * a / (2.0 - nu), "slipping": bool(ratio >= 1.0), "Q": Q, "muP": muP, "a": a, "P": P, "mu": mu, "G": G, "nu": nu,
            "p0": float(hz["p0"])}


def mindlin_traction(r, mp: dict) -> np.ndarray:
    """接線トラクション q(r) = q′ − q″ [Pa]: q′ = μp0√(1−r²/a²)(r < a)、q″ = μp0(c/a)√(1−r²/c²)(r < c)。滑り環 c ≤ r < a では q = μp(r)
    (Coulomb の限界に張り付く)、固着円では q < μp。``mp`` は :func:`mindlin_partial_slip` の表。r と同じ形。**Raises** ValueError: mp に a/c/mu/p0 が無い。"""
    if not isinstance(mp, dict) or not all(k in mp for k in ("a", "c", "mu", "p0")):
        raise ValueError("mindlin_traction: mp must be the dict from mindlin_partial_slip()")
    r = np.abs(np.asarray(r, np.float64))
    a, c, mu, p0 = float(mp["a"]), float(mp["c"]), float(mp["mu"]), float(mp["p0"])
    q1 = np.where(r < a, mu * p0 * np.sqrt(np.maximum(0.0, 1.0 - (r / a) ** 2)), 0.0)
    if c <= 0.0:
        return q1
    q2 = np.where(r < c, mu * p0 * (c / a) * np.sqrt(np.maximum(0.0, 1.0 - (r / c) ** 2)), 0.0)
    return q1 - q2


def hertz_surface_ur(r, a: float, p0: float, G: float, nu: float) -> np.ndarray:
    """法線荷重(Hertz 圧 p0√(1−r²/a²))が作る半空間表面の**半径方向**変位 ūr [m] (Johnson 1985 式 3.41b を E = 2G(1+ν) で書き直し)。
    負 = 中心向き。内側 −(1−2ν)p0a²/(6Gr)[1 − (1−r²/a²)^{3/2}]、外側 −(1−2ν)p0a²/(6Gr)(= 点荷重 −(1−2ν)P/(4πGr))、r → 0 で 0。
    最大は縁でなく r ≈ 0.93a(ūr(a) の 1.022 倍)。ūr(a)/δ = 2(1−2ν)/(3π(1−ν))(ν 0.48 で 1.6 %、ν 0.3 で 12 %)—— ほぼ非圧縮のゲルでは
    法線荷重でマーカーはほとんど動かない。**Raises** ValueError: a, p0, G ≤ 0。"""
    a, p0, G, nu = float(a), float(p0), float(G), float(nu)
    if not (a > 0.0 and p0 > 0.0 and G > 0.0):
        raise ValueError("hertz_surface_ur: a, p0, G must be > 0")
    r = np.abs(np.asarray(r, np.float64))
    pref = -(1.0 - 2.0 * nu) * p0 * a * a / (6.0 * G)
    rr = np.maximum(r, 1e-300)
    inner = np.where(r > 1e-15, pref / rr * (1.0 - np.maximum(0.0, 1.0 - (r / a) ** 2) ** 1.5), 0.0)
    return np.where(r <= a, inner, pref / rr)


def hertzian_tangential_inner(x, y, q0: float, a: float, G: float, nu: float) -> dict:
    """Hertz 形の接線トラクション q0√(1−r²/a²) が円内 r ≤ a に作る表面変位の閉形式(Johnson 1985 式 3.91)。
    ``ux`` = (πq0/32Ga)[4(2−ν)a² − (4−3ν)x² − (4−ν)y²]、``uy`` = (πq0/32Ga)·2νxy [m]。円の外では成り立たない(そこは畳み込みで)。
    **Raises** ValueError: a, G ≤ 0、x と y の形が違う。"""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    if x.shape != y.shape:
        raise ValueError("hertzian_tangential_inner: x and y must have the same shape")
    if not (float(a) > 0.0 and float(G) > 0.0):
        raise ValueError("hertzian_tangential_inner: a and G must be > 0")
    k = math.pi * float(q0) / (32.0 * float(G) * float(a))
    return {"ux": k * (4.0 * (2.0 - nu) * a * a - (4.0 - 3.0 * nu) * x * x - (4.0 - nu) * y * y), "uy": k * 2.0 * nu * x * y}


# ----------------------------------------------------------------------------------------------------------------------
# 2. Cerruti 核の FFT 畳み込み(接触円の外側に閉形式が無いので数値で)
def cerruti_kernel(n: int, pitch: float, G: float, nu: float, sub: int = 4, with_uz: bool = False) -> dict:
    """x 向き接線トラクション(1 画素 = pitch² に一様 1 Pa)が作る表面変位の離散核を 2n 格子(零詰めの線形畳み込み用)で作り、rfft2 済みで返す。

    核は画素ごとに**画素平均**で持つ(sub×sub の副標本の平均)。中心画素は 1/r が可積分なので解析値 —— ∫□ 1/r dA = 4h ln(1+√2)、
    ∫□ x²/r³ dA = 2h ln(1+√2)(対称性から ∫x²/r³ = ∫y²/r³ = ½∫1/r)、∫□ xy/r³ = ∫□ x/r² = 0。返り: ``Kxx``・``Kyx``(接線 → 接線)、
    ``with_uz=True`` なら ``Kzx``(接線 → 法線、係数 (1−2ν) で ν 0.48 では 0.04 倍)、``n``・``pitch``・``G``・``nu``。
    閉形式 (3.91) との一致は ūx 0.017 %・ūy 0.03 %(256 px、PoC の門)。**Raises** ValueError: n < 8、pitch, G ≤ 0、sub < 1。"""
    n, sub = int(n), int(sub)
    pitch, G, nu = float(pitch), float(G), float(nu)
    if n < 8 or not (pitch > 0.0 and G > 0.0) or sub < 1:
        raise ValueError("cerruti_kernel: need n >= 8, pitch > 0, G > 0, sub >= 1")
    m = 2 * n
    idx = np.arange(m)
    off = np.where(idx < n, idx, idx - m).astype(np.float64)
    OX, OY = np.meshgrid(off, off)
    s = (np.arange(sub) + 0.5) / sub - 0.5
    kxx = np.zeros((m, m)); kyx = np.zeros((m, m)); kzx = np.zeros((m, m)) if with_uz else None
    for sy in s:
        for sx in s:
            X = (OX + sx) * pitch
            Y = (OY + sy) * pitch
            r = np.hypot(X, Y)
            with np.errstate(divide="ignore", invalid="ignore"):
                inv_r3 = 1.0 / r ** 3
                kxx += 2.0 * (1.0 - nu) / r + 2.0 * nu * X * X * inv_r3
                kyx += 2.0 * nu * X * Y * inv_r3
                if with_uz:
                    kzx += -(1.0 - 2.0 * nu) * X / (r * r)
    kxx /= sub * sub; kyx /= sub * sub
    L = math.log(1.0 + math.sqrt(2.0))
    kxx[0, 0] = (2.0 * (1.0 - nu) * 4.0 * L + 2.0 * nu * 2.0 * L) / pitch      # 中心画素: 解析平均(÷ h² 済み → /h)
    kyx[0, 0] = 0.0
    scale = pitch * pitch / (4.0 * math.pi * G)                                # 面積 × 1/(4πG)
    out = {"Kxx": np.fft.rfft2(kxx * scale), "Kyx": np.fft.rfft2(kyx * scale), "n": n, "pitch": pitch, "G": G, "nu": nu}
    if with_uz:
        kzx /= sub * sub; kzx[0, 0] = 0.0
        out["Kzx"] = np.fft.rfft2(kzx * scale)
    return out


def cerruti_surface_displacement(qx, kern: dict) -> dict:
    """接線トラクション分布 qx (n, n) [Pa] → 表面変位 ``ux``・``uy``(核に ``Kzx`` があれば ``uz``)(n, n) [m]。零詰め 2n の線形畳み込み
    (巻き込みなし)。**Raises** ValueError: qx が (n, n) でない、kern が :func:`cerruti_kernel` の表でない。"""
    if not isinstance(kern, dict) or not all(k in kern for k in ("Kxx", "Kyx", "n")):
        raise ValueError("cerruti_surface_displacement: kern must be the dict from cerruti_kernel()")
    q = np.asarray(qx, np.float64)
    n = int(kern["n"])
    if q.shape != (n, n):
        raise ValueError("cerruti_surface_displacement: qx must be (%d, %d), got %r" % (n, n, q.shape))
    pad = np.zeros((2 * n, 2 * n)); pad[:n, :n] = q
    Fq = np.fft.rfft2(pad)
    out = {}
    for key, name in (("Kxx", "ux"), ("Kyx", "uy"), ("Kzx", "uz")):
        if key in kern:
            out[name] = np.fft.irfft2(Fq * kern[key], s=(2 * n, 2 * n))[:n, :n]
    return out


def membrane_shear_field(hz: dict, mp: dict, X, Y, kern: dict) -> dict:
    """膜表面の変位場: Mindlin のトラクション q(r) を Cerruti 核で畳んだ接線変位 ``ux``・``uy`` と、法線荷重の半径変位 ``urx``・``ury``
    (:func:`hertz_surface_ur` を x, y に分けたもの)[m]、``q``、固着/滑りのマスク ``mask_stick``(r ≤ c)・``mask_slip``(c < r ≤ a)、``r``。
    X, Y は格子の座標 [m] (中心が原点)。**Raises** ValueError: X と Y の形が違う、kern の n と合わない。"""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    if X.shape != Y.shape or X.ndim != 2 or X.shape != (int(kern["n"]), int(kern["n"])):
        raise ValueError("membrane_shear_field: X, Y must be (n, n) with the kernel's n")
    r = np.hypot(X, Y)
    q = mindlin_traction(r, mp)
    u = cerruti_surface_displacement(q, kern)
    ur = hertz_surface_ur(r, hz["a"], hz["p0"], mp["G"], mp["nu"])
    rr = np.maximum(r, 1e-300)
    cx = np.where(r > 1e-15, X / rr, 0.0)
    cy = np.where(r > 1e-15, Y / rr, 0.0)
    return {"ux": u["ux"], "uy": u["uy"], "uz": u.get("uz"), "urx": ur * cx, "ury": ur * cy, "q": q,
            "mask_stick": r <= mp["c"], "mask_slip": (r > mp["c"]) & (r <= hz["a"]), "r": r}


# ----------------------------------------------------------------------------------------------------------------------
# 3. マーカー配列の合成(変位で中心を移してから描く)
def membrane_markers(n: int, pitch_px: float, ox: float = 0.3, oy: float = 0.6) -> np.ndarray:
    """n×n 画素の視野に撒くマーカー中心 (N, 2) = (x, y) [px] の規則格子(ピッチ pitch_px、副画素位相 (ox, oy))。視野の外にも 1 周だけ撒く
    (変位で入ってくるぶん)。**Raises** ValueError: n < 8、pitch_px < 2。"""
    n = int(n); pitch_px = float(pitch_px)
    if n < 8 or pitch_px < 2.0:
        raise ValueError("membrane_markers: need n >= 8 and pitch_px >= 2")
    k = np.arange(-1, int(math.ceil(n / pitch_px)) + 1)
    base = (n - 1) / 2.0 - pitch_px * (len(k) // 2 - 1)
    XX, YY = np.meshgrid(k * pitch_px + float(ox) + base, k * pitch_px + float(oy) + base)
    return np.column_stack([XX.ravel(), YY.ravel()])


def _sample(field, xy_px):
    """格子場 (n, n) を画素座標 (x, y) で双線形標本化(外は縁)。"""
    return ndimage.map_coordinates(np.asarray(field, np.float64), [xy_px[:, 1], xy_px[:, 0]], order=1, mode="nearest")


def displace_markers(pts, fx, fy, pitch: float) -> np.ndarray:
    """変位場 fx, fy (n, n) [m] でマーカー中心 (N, 2) [px] を移す(場は中心位置で双線形標本化、画素に換算して足す)。
    **Raises** ValueError: pts が (N, 2) でない、fx と fy の形が違う、pitch ≤ 0。"""
    p = np.asarray(pts, np.float64)
    fx = np.asarray(fx, np.float64); fy = np.asarray(fy, np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or fx.shape != fy.shape or fx.ndim != 2 or not (float(pitch) > 0.0):
        raise ValueError("displace_markers: pts must be (N, 2), fx/fy the same (n, n), pitch > 0")
    return p + np.column_stack([_sample(fx, p), _sample(fy, p)]) / float(pitch)


def membrane_render_markers(rgb, pts, r_px: float, dark: float, sub: int = 8) -> np.ndarray:
    """RGB (H, W, 3) に黒い円盤のマーカー(中心 pts (N, 2) [px]、半径 r_px)を描く: 画素の被覆率で rgb *= 1 − dark·coverage。
    被覆率は円盤の縁の画素だけ sub² の副標本(内側 1・外側 0)。像を補間して歪めないので真値が厳密。
    **Raises** ValueError: rgb が (H, W, 3) でない、pts が (N, 2) でない、r_px ≤ 0、dark が [0, 1] の外。"""
    out = np.asarray(rgb, np.float64).copy()
    pts = np.asarray(pts, np.float64)
    if out.ndim != 3 or out.shape[2] != 3 or pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("membrane_render_markers: rgb must be (H, W, 3) and pts (N, 2)")
    r_px, dark, sub = float(r_px), float(dark), int(sub)
    if not (r_px > 0.0) or not (0.0 <= dark <= 1.0) or sub < 1:
        raise ValueError("membrane_render_markers: need r_px > 0, 0 <= dark <= 1, sub >= 1")
    H, W = out.shape[:2]
    if len(pts) == 0:
        return out
    s = (np.arange(sub) + 0.5) / sub - 0.5
    SX, SY = np.meshgrid(s, s)
    win = int(math.ceil(r_px + 1.0))
    oy, ox = np.mgrid[-win:win + 1, -win:win + 1].astype(np.float64)
    fx, fy = np.floor(pts[:, 0]), np.floor(pts[:, 1])
    frx, fry = pts[:, 0] - fx, pts[:, 1] - fy
    d0 = np.hypot(ox[None] - frx[:, None, None], oy[None] - fry[:, None, None])
    cov = np.where(d0 <= r_px - 0.75, 1.0, 0.0)
    edge = np.abs(d0 - r_px) < 0.75
    ex = (ox[None] - frx[:, None, None])[edge]; ey = (oy[None] - fry[:, None, None])[edge]
    dxe = ex[:, None, None] + SX[None]; dye = ey[:, None, None] + SY[None]
    cov[edge] = (dxe * dxe + dye * dye <= r_px * r_px).mean(axis=(-1, -2))
    rows = (fy[:, None, None] + oy[None]).astype(int)
    cols = (fx[:, None, None] + ox[None]).astype(int)
    valid = (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W) & (cov > 0)
    att = np.ones((H, W))
    np.multiply.at(att, (rows[valid], cols[valid]), 1.0 - dark * cov[valid])
    return out * att[..., None]


# ----------------------------------------------------------------------------------------------------------------------
# 4. 被験者(既存 op)で読む: マーカー像・検出・対応
def marker_image(rgb, bg) -> np.ndarray:
    """マーカーだけの像 m = 1 − gray/gray_bg ∈ [0, 1] (H, W)。bg = マーカーの無い同じ照明の像 = 実機の参照フレーム較正に当たる。
    **Raises** ValueError: 2 枚の形が違う、(H, W, 3) でない。"""
    g = np.asarray(rgb, np.float64); b = np.asarray(bg, np.float64)
    if g.shape != b.shape or g.ndim != 3 or g.shape[2] != 3:
        raise ValueError("marker_image: rgb and bg must be the same (H, W, 3)")
    return np.clip(1.0 - g.mean(-1) / np.maximum(b.mean(-1), 1e-6), 0.0, 1.0)


def _refine_centroids(m, c0, sigma: float, iters: int = 3, win: int = 4) -> np.ndarray:
    """重心の精密化: 推定中心を中心にしたガウス窓(σ)で m を重み付けし直して重心を取り直す(粒子追跡の定石)。

    理由(実測、2 次元の副画素位相走査 5×5): 素の重み重心は半径 2.5 px の円盤で最悪 0.018 px の系統バイアス(境界画素内の被覆部分の重心が
    画素中心とずれ、位相で打ち消し合わない = pixel-locking)。σ = 半径で 0.006 px(σ = 1.5 だと 0.012、σ = 4 だと 0.008)。
    窓が画像の外に出る点はそのまま返す。"""
    H, W = m.shape
    c = np.array(c0, np.float64).copy()
    if c.size == 0:
        return c
    oy, ox = np.mgrid[-win:win + 1, -win:win + 1]
    for _ in range(int(iters)):
        i0 = np.rint(c[:, 1]).astype(int); j0 = np.rint(c[:, 0]).astype(int)
        ok = (i0 - win >= 0) & (j0 - win >= 0) & (i0 + win < H) & (j0 + win < W)
        if not ok.any():
            break
        rows = i0[ok, None, None] + oy[None]; cols = j0[ok, None, None] + ox[None]
        sub = m[rows, cols]
        xx = cols.astype(np.float64); yy = rows.astype(np.float64)
        g = np.exp(-((xx - c[ok, 0, None, None]) ** 2 + (yy - c[ok, 1, None, None]) ** 2) / (2.0 * sigma * sigma))
        w = sub * g
        sw = w.sum(axis=(1, 2))
        good = sw > 1e-12
        idx = np.flatnonzero(ok)[good]
        c[idx, 0] = (w * xx).sum(axis=(1, 2))[good] / sw[good]
        c[idx, 1] = (w * yy).sum(axis=(1, 2))[good] / sw[good]
    return c


def marker_detect(m, dark: float, r_px: float, binary: bool = False) -> dict:
    """マーカー像 m(:func:`marker_image`)→ マーカー中心。``weighted``(主、(N, 2) の (x, y) [px]): 高しきい値 0.5·dark の連結成分
    (:func:`blob2d.blob_label`)を本体とし、低しきい値 0.08·dark の画素(縞)を距離変換で最近傍の本体へ割り当て、m を重みにした重心を
    反復ガウス重み(σ = r_px)で精密化。``weighted_plain`` = 精密化前。``binary=True`` なら ``binary`` = :func:`blob2d.blob_features` の
    row/col(二値重心、周長・凸包まで計算するので 1,000 個で 0.4 s)。縁に触る成分は捨てる。``n`` = 本体の数。
    縞を本体から切るのは、滑り環で隣接間隔が 8 → 6 px に縮むと低しきい値の縞が繋がって 1 成分に併合するから(実測)。
    **Raises** ValueError: m が 2 次元でない、dark が (0, 1] の外、r_px ≤ 0。"""
    m = np.asarray(m, np.float64)
    dark, r_px = float(dark), float(r_px)
    if m.ndim != 2 or not (0.0 < dark <= 1.0) or not (r_px > 0.0):
        raise ValueError("marker_detect: m must be 2-D, 0 < dark <= 1, r_px > 0")
    out = {}
    if binary:
        f = _blob.blob_features(_blob.blob_label(m > 0.5 * dark, 8))
        keep = ~np.asarray(f["touches_border"], bool)
        out["binary"] = np.column_stack([np.asarray(f["col"])[keep], np.asarray(f["row"])[keep]])
    lab_hi = _blob.blob_label(m > 0.5 * dark, 8)
    n_hi = int(lab_hi.max())
    if n_hi == 0:
        empty = np.zeros((0, 2))
        out.update({"weighted": empty, "weighted_plain": empty.copy(), "n": 0})
        return out
    _, (iy, ix) = ndimage.distance_transform_edt(lab_hi == 0, return_indices=True)
    lab_lo = np.where(m > 0.08 * dark, lab_hi[iy, ix], 0)
    w = np.where(lab_lo > 0, m, 0.0)
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    sw = np.bincount(lab_lo.ravel(), weights=w.ravel(), minlength=n_hi + 1)
    sx = np.bincount(lab_lo.ravel(), weights=(w * xx).ravel(), minlength=n_hi + 1)
    sy = np.bincount(lab_lo.ravel(), weights=(w * yy).ravel(), minlength=n_hi + 1)
    good = sw[1:] > 1e-9
    wc = np.column_stack([sx[1:][good] / sw[1:][good], sy[1:][good] / sw[1:][good]])
    obj = ndimage.find_objects(lab_lo)
    tb = np.array([(sl is not None) and (sl[0].start == 0 or sl[1].start == 0 or sl[0].stop == m.shape[0] or sl[1].stop == m.shape[1])
                   for sl in obj], bool)
    wc = wc[~tb[good]]
    out["weighted_plain"] = wc
    out["weighted"] = _refine_centroids(m, wc, sigma=r_px)
    out["n"] = n_hi
    return out


def marker_match_grow(p0, p1, pitch_px: float, seed_tol: float = 0.25, tols=(0.2, 0.3, 0.45), nb_r: float = 1.6,
                      border: float = 2.0, max_iter: int = 80) -> dict:
    """基準マーカー p0 と荷重後 p1(各 (N, 2) [px])の対応を**連続性で伸ばして**取る。返り ``i0``・``i1``(対応の index 配列)、``matched``。

    規則格子では |u| がピッチ/2 を超えると最近傍も相関も隣のマーカーに飛ぶ(実測: 8 px 格子で 5 px のずれを PIV は −3 px と読む)。
    種 = p0 の外接矩形の**縁(border·ピッチ以内)**にあるマーカーで、予測なしの最近傍が seed_tol·ピッチ以内かつ 2 番目が 0.75 ピッチより
    遠いもの(「接触は視野の内側にあり縁は遠方場 = 小変位」という物理の前提。どこでも種にすると、核の変位 6.4 px が隣の基準位置から
    1.6 px なのでピッチ 1 つ飛んだ偽の種が 27 個できた)。以後、未対応のマーカーは nb_r·ピッチ以内の既対応 2 点以上の変位の平均を予測にして
    tol·ピッチ以内の最近傍を取り、tol は小さい値から段階的に緩める。1 つの p1 は 1 回しか使わない。
    **Raises** ValueError: p0/p1 が (N, 2) でない、pitch_px ≤ 0。"""
    from scipy.spatial import cKDTree
    p0 = np.asarray(p0, np.float64); p1 = np.asarray(p1, np.float64)
    if p0.ndim != 2 or p0.shape[1] != 2 or p1.ndim != 2 or p1.shape[1] != 2 or not (float(pitch_px) > 0.0):
        raise ValueError("marker_match_grow: p0, p1 must be (N, 2) and pitch_px > 0")
    n0 = len(p0)
    match = -np.ones(n0, int)
    if n0 == 0 or len(p1) < 2:
        return {"i0": np.zeros(0, int), "i1": np.zeros(0, int), "matched": 0}
    t1 = cKDTree(p1); t0 = cKDTree(p0)
    used = np.zeros(len(p1), bool)
    d2, i2 = t1.query(p0, k=2)
    bd = float(border) * float(pitch_px)
    lo, hi = p0.min(axis=0), p0.max(axis=0)
    on_border = (p0[:, 0] < lo[0] + bd) | (p0[:, 1] < lo[1] + bd) | (p0[:, 0] > hi[0] - bd) | (p0[:, 1] > hi[1] - bd)
    seed = on_border & (d2[:, 0] < seed_tol * pitch_px) & (d2[:, 1] > 0.75 * pitch_px)
    for k in np.flatnonzero(seed):
        if not used[i2[k, 0]]:
            match[k] = i2[k, 0]; used[i2[k, 0]] = True
    for tol in tols:
        for _ in range(int(max_iter)):
            todo = np.flatnonzero(match < 0)
            if todo.size == 0:
                break
            progressed = False
            nbrs = t0.query_ball_point(p0[todo], nb_r * pitch_px)
            for k, nb in zip(todo, nbrs):
                nb = [j for j in nb if match[j] >= 0]
                if len(nb) < 2:
                    continue
                u_pred = (p1[match[nb]] - p0[nb]).mean(axis=0)
                d, i = t1.query(p0[k] + u_pred, distance_upper_bound=tol * pitch_px)
                if np.isfinite(d) and not used[i]:
                    match[k] = i; used[i] = True; progressed = True
            if not progressed:
                break
    ok = match >= 0
    return {"i0": np.flatnonzero(ok), "i1": match[ok], "matched": int(ok.sum())}


def _piv_field(m_ref, m_cur, window: int = 32, overlap: float = 0.5, search_limit: float = 0.12):
    """:func:`pivops.piv_cross_correlate`(単段の窓相関、第 2 実装)の場と、任意の点で標本化する関数。

    多段(64 → 32)は使わない: 64 px 窓は探索 ±16 px に格子周期 8 px の倍数の偽ピークを持ち、第 1 段が −15/+9 px に飛んで第 2 段を道連れにした
    (実測)。単段 32 px 窓でも探索 ±8 px(1/4 則)だと核の 1 窓が 1.5 → −6.5 px に飛ぶので、探索をピッチ/2 未満(0.12 × 32 = ±3.8 px)に絞る
    —— その代わり |u| ≥ 3.8 px は測れない(格子に相関を当てる方法の原理的な上限)。"""
    from scipy.interpolate import RegularGridInterpolator

    import pivops
    flow, info = pivops.piv_cross_correlate(m_ref, m_cur, window=window, overlap=overlap, search_limit=search_limit)
    flow = np.nan_to_num(np.asarray(flow), nan=0.0)
    ys, xs = np.asarray(info["rows"], float), np.asarray(info["cols"], float)
    fy = RegularGridInterpolator((ys, xs), flow[0], bounds_error=False, fill_value=None)
    fx = RegularGridInterpolator((ys, xs), flow[1], bounds_error=False, fill_value=None)

    def at(pts):
        p = np.column_stack([pts[:, 1], pts[:, 0]])
        return np.column_stack([fx(p), fy(p)])
    return at, flow, info


def marker_track(m_ref, m_cur, dark: float, pitch_px: float, r_px: float, piv: bool = False) -> dict:
    """基準・荷重後のマーカー像(:func:`marker_image`)から変位ベクトル場: 検出(:func:`marker_detect`、2 枚)→ 連続性で対応
    (:func:`marker_match_grow`)→ ``u`` = p1 − p0 [px]。返り ``p0``・``p1``・``u``(各 (M, 2))、``matched``、``n0``・``n1``。
    ``piv=True`` なら :func:`pivops.piv_cross_correlate` の場(第 2 実装、探索 ±0.12 窓)を ``piv_flow``・``piv_info``・``piv_at``(点列で標本化する
    関数)として付ける。**Raises** ValueError: 2 枚の形が違う。"""
    m_ref = np.asarray(m_ref, np.float64); m_cur = np.asarray(m_cur, np.float64)
    if m_ref.shape != m_cur.shape or m_ref.ndim != 2:
        raise ValueError("marker_track: m_ref and m_cur must be the same (H, W)")
    d0, d1 = marker_detect(m_ref, dark, r_px), marker_detect(m_cur, dark, r_px)
    p0, p1 = d0["weighted"], d1["weighted"]
    mt = marker_match_grow(p0, p1, pitch_px)
    i0, i1 = mt["i0"], mt["i1"]
    out = {"p0": p0[i0], "p1": p1[i1], "u": p1[i1] - p0[i0], "matched": int(len(i0)), "n0": int(len(p0)), "n1": int(len(p1))}
    if piv:
        at, flow, info = _piv_field(m_ref, m_cur)
        out.update({"piv_flow": flow, "piv_info": info, "piv_at": at})
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 5. 逆算: 固着円と Q/μP、μP を変位場から(相似則)
def mindlin_model(hz: dict, X, Y, kern: dict, G: float, nu: float) -> dict:
    """任意の c/a の Mindlin 変位場を**相似則**で出す逆算模型(畳み込みは 1 回だけ)。

    Hertz 形の接線トラクション(半径 R、頂点 q0)の表面変位は u = q0·R·ĝ(x/R)(線形弾性 + 無次元化)。q′(半径 a、頂点 μp0)と
    q″(半径 c、頂点 μp0·c/a)の差だから、g(x) = 頂点 1 Pa・半径 a の場として u(x; c) = μp0·[g(x) − (c/a)²·g(x·a/c)]。
    g は Cerruti 核で格子上に作り、x·a/c が格子の外に出る点は点荷重の漸近形(総力 (2/3)πa²·1 Pa)で補う。順方向の畳み込みとの差は
    核で 0.05 %、環で 0.13 %。返り ``gx``・``gy``(n, n)、``Qunit``、``n``・``pitch``・``c0``(格子中心 [px])、``hz``・``G``・``nu``。
    c/a の格子を線形補間する模型は場が c に非線形なので c/a を 0.01 ずらした(捨てた)。**Raises** ValueError: 形の不一致、G ≤ 0。"""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    n = int(kern["n"])
    if X.shape != (n, n) or Y.shape != (n, n) or not (float(G) > 0.0):
        raise ValueError("mindlin_model: X, Y must be (n, n) with the kernel's n and G > 0")
    a = float(hz["a"])
    r = np.hypot(X, Y)
    u = cerruti_surface_displacement(np.where(r < a, np.sqrt(np.maximum(0.0, 1.0 - (r / a) ** 2)), 0.0), kern)
    return {"gx": u["ux"], "gy": u["uy"], "Qunit": (2.0 / 3.0) * math.pi * a * a, "n": n, "pitch": float(kern["pitch"]),
            "c0": (n - 1) / 2.0, "hz": dict(hz), "G": float(G), "nu": float(nu)}


def _model_g_at(model: dict, pts_px):
    """g(x) を画素座標で標本化。格子の外は Cerruti 点荷重の漸近形。"""
    c0, pitch, G, nu = model["c0"], model["pitch"], model["G"], model["nu"]
    xy = (pts_px - c0) * pitch
    inside = (np.abs(pts_px[:, 0] - c0) < c0 - 1.0) & (np.abs(pts_px[:, 1] - c0) < c0 - 1.0)
    gx = np.empty(len(pts_px)); gy = np.empty(len(pts_px))
    if inside.any():
        gx[inside] = _sample(model["gx"], pts_px[inside]); gy[inside] = _sample(model["gy"], pts_px[inside])
    if (~inside).any():
        x, y = xy[~inside, 0], xy[~inside, 1]
        r = np.maximum(np.hypot(x, y), 1e-300)
        k = model["Qunit"] / (4.0 * math.pi * G)
        gx[~inside] = k * (2.0 * (1.0 - nu) / r + 2.0 * nu * x * x / r ** 3)
        gy[~inside] = k * 2.0 * nu * x * y / r ** 3
    return gx, gy


def _model_unit_field(model: dict, pts_px, c_over_a: float):
    """μP = 1 N あたりの (ux, uy) [m/N] を点列で。"""
    p0_per_P = model["hz"]["p0"] / model["hz"]["F"]
    g1x, g1y = _model_g_at(model, pts_px)
    if c_over_a <= 1e-9:
        return p0_per_P * g1x, p0_per_P * g1y
    sc = (pts_px - model["c0"]) / c_over_a + model["c0"]
    g2x, g2y = _model_g_at(model, sc)
    return p0_per_P * (g1x - c_over_a ** 2 * g2x), p0_per_P * (g1y - c_over_a ** 2 * g2y)


def mindlin_fit(model: dict, pts_px, u_m, n_coarse: int = 101, n_fine: int = 41, rigid: bool = False) -> dict:
    """マーカー位置 pts_px (M, 2) [px] と変位 u_m (M, 2) [m] に (c/a, μP) を当てる: c/a を粗く走査 → 最良の周りを細かく、μP は各 c で
    線形最小二乗。返り ``c_over_a``・``q_ratio`` = 1 − (c/a)³・``muP``・``Q``・``mu``(= μP/P)・``rms_m``・``shift_m``。
    ``rigid=True`` は剛体シフト (tx, ty) も自由にする —— 試作では**逆効果**だった(外側 900 点の 1/r の尾と縮退して c/a が 0.028 ずれる)ので
    既定は切る。実機のドリフトは接触の外の遠方マーカーで別途引くのが筋。真の変位で当てると c/a の誤差 0.001、画像からの追跡では 0.011
    (重心の pixel-locking が共通モードで乗る)。**Raises** ValueError: 形の不一致、点が 3 個未満。"""
    pts_px = np.asarray(pts_px, np.float64); u_m = np.asarray(u_m, np.float64)
    if pts_px.ndim != 2 or pts_px.shape[1] != 2 or u_m.shape != pts_px.shape or len(pts_px) < 3:
        raise ValueError("mindlin_fit: pts_px and u_m must be (M, 2) with M >= 3")
    n = len(pts_px)
    obs = np.concatenate([u_m[:, 0], u_m[:, 1]])
    ones_x = np.concatenate([np.ones(n), np.zeros(n)]); ones_y = np.concatenate([np.zeros(n), np.ones(n)])

    def cost(ca):
        fx, fy = _model_unit_field(model, pts_px, ca)
        f = np.concatenate([fx, fy])
        A = np.column_stack([f, ones_x, ones_y]) if rigid else f[:, None]
        sol, *_ = np.linalg.lstsq(A, obs, rcond=None)
        return float(np.sqrt(np.mean((obs - A @ sol) ** 2))), sol
    grid = np.linspace(0.0, 1.0, int(n_coarse))
    costs = [cost(ca) for ca in grid]
    k = int(np.argmin([c_[0] for c_ in costs]))
    fine = np.linspace(grid[max(k - 1, 0)], grid[min(k + 1, len(grid) - 1)], int(n_fine))
    cf = [cost(ca) for ca in fine]
    j = int(np.argmin([c_[0] for c_ in cf]))
    res, sol = cf[j]
    ca = float(fine[j]); muP = float(sol[0])
    return {"c_over_a": ca, "q_ratio": 1.0 - ca ** 3, "muP": muP, "Q": muP * (1.0 - ca ** 3), "mu": muP / float(model["hz"]["F"]),
            "rms_m": res, "shift_m": (float(sol[1]), float(sol[2])) if rigid else (0.0, 0.0)}


def stick_radius_modelfree(pts_c, u_px, rel: float = 0.08, abs_px: float = 0.05) -> dict:
    """模型なしの固着半径: 中心からの距離順に、内側 6 点の中央値 δ̂ から |ux − δ̂| が rel·|δ̂| + abs_px を超える最初の点と、その手前の点の中点の
    半径 ``c_px``(分解能 = マーカー間隔)。``core_px`` = δ̂。pts_c は中心相対 (M, 2) [px]、u_px は (M, 2) [px]。**Raises** ValueError: 点が 6 個未満。"""
    pts_c = np.asarray(pts_c, np.float64); u_px = np.asarray(u_px, np.float64)
    if pts_c.ndim != 2 or pts_c.shape[1] != 2 or u_px.shape != pts_c.shape or len(pts_c) < 6:
        raise ValueError("stick_radius_modelfree: need (M, 2) with M >= 6 for both arrays")
    r = np.hypot(pts_c[:, 0], pts_c[:, 1])
    o = np.argsort(r)
    core = float(np.median(u_px[o[:6], 0]))
    dev = np.abs(u_px[o, 0] - core) > rel * abs(core) + abs_px
    k = int(np.argmax(dev)) if dev.any() else len(o)
    if k == 0:
        return {"c_px": 0.0, "core_px": core}
    r_in = r[o[k - 1]]
    r_out = r[o[k]] if k < len(o) else r_in
    return {"c_px": float(0.5 * (r_in + r_out)), "core_px": core}


def slip_entropy(mag, bins: int = 16, vmax=None) -> float:
    """変位の大きさ |u| の列のヒストグラム(bins 本、範囲 [0, vmax] —— 省略時は最大値)の Shannon エントロピーを ln(bins) で正規化(0..1)。
    Yuan 2017 の滑りの指標: 固着核が縮んで滑り環の勾配に乗るマーカーが増えると上がる。**Raises** ValueError: 点が無い、bins < 2。"""
    mag = np.asarray(mag, np.float64).ravel()
    if mag.size == 0 or int(bins) < 2:
        raise ValueError("slip_entropy: need >= 1 value and bins >= 2")
    hi = float(vmax) if vmax is not None else float(mag.max()) * (1.0 + 1e-9)
    if not (hi > 0.0):
        return 0.0
    h, _ = np.histogram(np.clip(mag, 0.0, hi), bins=int(bins), range=(0.0, hi))
    p = h[h > 0] / h.sum()
    return float(-(p * np.log(p)).sum() / math.log(int(bins)))


# ----------------------------------------------------------------------------------------------------------------------
# 6. 有限要素の節点変位(第 2 真値)
def fem_nodes_load(dirpath: str, name: str) -> dict:
    """有限要素の表面節点テキスト(Robo-Touch/Taxim リポジトリ同梱、MIT ライセンス)を 3 本読む: ``<dirpath>/<name>_{x,y,z}.txt``、
    タブ区切り・1 行ヘッダ ``Node Number / X Location (m) / Y Location (m) / Z Location (m) / Directional Deformation (m)``、単位 m。
    3 本は同じ節点集合で最終列だけがその方向の変位。返り ``id``・``X``・``Y``・``Z``・``dx``・``dy``・``dz``(各 (N,))、``n``、``name``。
    **Raises** FileNotFoundError: ファイルが無い。ValueError: ヘッダが違う、列が 5 本でない、3 本の節点座標が一致しない(fail-closed)。"""
    arrs = []
    for comp in "xyz":
        p = os.path.join(str(dirpath), "%s_%s.txt" % (name, comp))
        if not os.path.isfile(p):
            raise FileNotFoundError(p)
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.readline()
        if "Directional Deformation (m)" not in head or "X Location (m)" not in head:
            raise ValueError("fem_nodes_load: unexpected header in %s: %r" % (os.path.basename(p), head[:80]))
        a = np.loadtxt(p, delimiter="\t", skiprows=1, ndmin=2)
        if a.ndim != 2 or a.shape[1] != 5 or a.shape[0] < 3:
            raise ValueError("fem_nodes_load: expected >= 3 rows x 5 columns in %s, got %r" % (os.path.basename(p), a.shape))
        arrs.append(a)
    for a in arrs[1:]:
        if a.shape != arrs[0].shape or not np.allclose(a[:, :4], arrs[0][:, :4]):
            raise ValueError("fem_nodes_load: node coordinates differ between the x/y/z files")
    a0 = arrs[0]
    return {"id": a0[:, 0].astype(int), "X": a0[:, 1], "Y": a0[:, 2], "Z": a0[:, 3],
            "dx": arrs[0][:, 4], "dy": arrs[1][:, 4], "dz": arrs[2][:, 4], "n": int(a0.shape[0]), "name": str(name)}


def _annulus_mean(r, v, edges):
    idx = np.digitize(r, edges)
    mids, vals, cnt = [], [], []
    for k in range(1, len(edges)):
        m = idx == k
        if m.sum() >= 3:
            mids.append(0.5 * (edges[k - 1] + edges[k])); vals.append(float(v[m].mean())); cnt.append(int(m.sum()))
    return np.array(mids), np.array(vals), np.array(cnt)


def _fit_angular(th, v, basis):
    """v ≈ A + B·basis(θ) の最小二乗(A, B, R²)。点が 3 個未満なら nan。"""
    if len(th) < 3:
        return float("nan"), float("nan"), float("nan")
    Am = np.column_stack([np.ones(len(th)), basis])
    (a_, b_), *_ = np.linalg.lstsq(Am, v, rcond=None)
    ss = float(np.sum((v - (a_ + b_ * basis)) ** 2)); st = float(np.sum((v - v.mean()) ** 2))
    return float(a_), float(b_), (1.0 - ss / st if st > 0 else float("nan"))


def fem_vs_halfspace(fz: dict, fxz: dict) -> dict:
    """同じ節点集合の法線押し込み ``fz`` と斜め押し込み ``fxz``(:func:`fem_nodes_load`)を半空間解と**形だけ**比べる(荷重の大きさは不明)。
    (1) r·dz を 0.5〜0.8 mm で 1 に正規化(``mids``・``rdz_n``): 半空間 Boussinesq は r ≫ 接触で一定、有限厚は落ちる。1/r から 2 倍外れる
    半径 ``r_half``(無ければ None)。(2) 斜め押し込みの dx(θ) を r = 1/1.5/2/3 mm の環で A + B cos²θ に当てる(``ang``: Cerruti なら
    B/A = ν/(1−ν) → ``nu``、``ratio`` = (A+B)/A、``R2``)、dy を A + B sin2θ に(``dy_fit``)。``R_dome``(表面の r–z を球冠に当てた半径)、
    ``dy_over_dz0``(法線だけでも出ている接線成分 = 非対称の量)、``rdx_n``、``dz0``、``dx_min_spacing``、``r``・``th``(中心相対)も返す。
    **Raises** ValueError: 2 つの表の節点数が違う、節点が 10 個未満。"""
    if int(fz["n"]) != int(fxz["n"]) or int(fz["n"]) < 10:
        raise ValueError("fem_vs_halfspace: both tables must have the same >= 10 nodes")
    i0 = int(np.argmax(fz["dz"]))
    cx, cy = float(fz["X"][i0]), float(fz["Y"][i0])
    r = np.hypot(fz["X"] - cx, fz["Y"] - cy)
    th = np.arctan2(fz["Y"] - cy, fz["X"] - cx)
    sel = r < 10e-3
    R_dome = float("nan")
    if sel.sum() >= 3:
        co = np.linalg.lstsq(np.column_stack([r[sel] ** 2, np.ones(sel.sum())]), fz["Z"][sel], rcond=None)[0]
        R_dome = 1.0 / (2.0 * co[0]) if abs(co[0]) > 1e-30 else float("inf")
    edges = np.array([0.4, 0.55, 0.7, 0.85, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]) * 1e-3

    def normalised(v):
        mids, vm, cnt = _annulus_mean(r, v, edges)
        if mids.size == 0:
            return mids, np.zeros(0), cnt
        rv = mids * vm
        band = (mids >= 0.5e-3) & (mids <= 0.8e-3)
        ref = float(np.mean(rv[band])) if band.any() else float(rv[0])
        return mids, rv / ref if ref != 0.0 else rv, cnt
    mids, rdz_n, cnt = normalised(fz["dz"])
    r_half = None
    for k in range(1, len(mids)):
        if rdz_n[k - 1] >= 0.5 > rdz_n[k]:
            t = (rdz_n[k - 1] - 0.5) / (rdz_n[k - 1] - rdz_n[k])
            r_half = float(mids[k - 1] + t * (mids[k] - mids[k - 1]))
            break
    ang = []
    for r0, w in ((1.0e-3, 0.25e-3), (1.5e-3, 0.25e-3), (2.0e-3, 0.3e-3), (3.0e-3, 0.4e-3)):
        m = np.abs(r - r0) < w
        a_, b_, r2 = _fit_angular(th[m], fxz["dx"][m], np.cos(th[m]) ** 2)
        nu_impl = (b_ / a_) / (1.0 + b_ / a_) if (np.isfinite(a_) and a_ > 0) else float("nan")
        ang.append({"r": r0, "n": int(m.sum()), "A": a_, "B": b_, "ratio": (a_ + b_) / a_ if (np.isfinite(a_) and a_ != 0) else float("nan"),
                    "nu": float(nu_impl), "R2": r2})
    m = np.abs(r - 2.0e-3) < 0.3e-3
    a2, b2, r2 = _fit_angular(th[m], fxz["dy"][m], np.sin(2.0 * th[m]))
    mids2, rdx_n, _ = normalised(fxz["dx"])
    dz0 = float(fz["dz"][i0])
    return {"centre": (cx, cy), "R_dome": R_dome, "mids": mids, "rdz_n": rdz_n, "cnt": cnt, "r_half": r_half,
            "dy_over_dz0": float(fz["dy"][i0] / dz0) if dz0 != 0.0 else float("nan"), "ang": ang,
            "dy_fit": {"A": a2, "B": b2, "R2": r2, "n": int(m.sum())}, "mids_dx": mids2, "rdx_n": rdx_n, "dz0": dz0,
            "dx0_xz": float(fxz["dx"][i0]), "dz0_xz": float(fxz["dz"][i0]), "r": r, "th": th,
            "dx_min_spacing": float(np.sort(r)[1]) if len(r) > 1 else float("nan")}
