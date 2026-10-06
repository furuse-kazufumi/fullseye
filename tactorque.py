# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tactorque — 視触覚センサ(弾性膜 + カメラ)のマーカー変位場から「触覚双極子モーメント」で把持内の傾き・ねじりトルクを読む(2026-10-04)。

物理シミュ × Fullseye 系列の第 2 弾の第 3 本(第 1 本 = :mod:`tacsim` 法線荷重、第 2 本 = :mod:`tacslip` 接線荷重と固着/滑り)。
再実装した方法: Y. Fuchioka, M. Hamaya, "An Electromagnetism-Inspired Method for Estimating In-Grasp Torque from Visuotactile Sensors",
ICRA 2024, arXiv 2404.15626 —— 学習なし・光学模型なし。マーカー変位場 v の**発散** ∇·v を電荷密度(法線力の分布、Gauss の法則の類推)と見て
双極子モーメント p = (1/N) Σ r_i (∇·v)_i(式 4–5)を取り、r_i の原点は正・負の発散の重心の中点(式 6–8)、傾きトルクは双極子に直交
τ = [c_x p_y, −c_y p_x] (式 9、較正係数 c は力覚センサで線形に当てる)。基線(式 10–11、Yamaguchi & Atkeson 流)は |v_i| を法線力の代わりにし
原点を画像中心に置く。手順の要は**把持後に零点を取る**こと(零点を取らないと法線力の成分が支配する)。論文の主張は「直線性は保たれるが較正
係数は物体ごとに違う」(形状不変は主張していない)。著者のリポジトリは無ライセンスなのでコードは読まず、本文の式だけから再実装した。
センサは retrographic sensing(M. K. Johnson, E. H. Adelson, CVPR 2009)系。

外から来る真値 = 閉形式(K. L. Johnson, *Contact Mechanics*, CUP 1985, DOI 10.1017/CBO9781139171731):
  * 平頭円形押し込み子(半径 a)に法線力 P と傾きモーメント M を掛けた圧力 p = P/(2πa√(a²−r²)) + 3(M_x x + M_y y)/(2πa³√(a²−r²))。
    第 1 項は式 3.34。第 2 項(反対称項)は ∫ (x, y) p dA = M を満たす(∫₀^a r³/√(a²−r²) dr = 2a³/3、本モジュールの導出、門で数値確認)。
    接触が離れない条件 p ≥ 0 ⇔ |M| ≤ Pa/3。
  * 法線点荷重の半空間表面の変位(Boussinesq、§3.2): 接線 ū_r = −(1−2ν)P/(4πGr)、法線 ū_z = (1−ν)P/(2πGr)。これを核にして圧力分布を FFT で畳む
    (:func:`boussinesq_kernel` / :func:`boussinesq_surface_displacement`)。門 = Hertz 圧で畳んだ結果 vs 式 3.41b(:func:`tacslip.hertz_surface_ur`)と
    式 3.42a(:func:`tacsim.hertz_surface_uz`)。
  * **Gauss の法則は半空間で厳密に成り立つ**(本モジュールの導出): 2 次元で ∇·(r̂/r) = 2πδ²(r) なので、表面接線変位の発散は
    ∇·ū = −(1−2ν) p(x, y)/(2G)。「発散 ∝ 局所の法線圧」は類推でなく恒等式で、面積重みの双極子 Σ r_i (∇·u)_i h² は −(1−2ν)/(2G) × (圧力の
    1 次モーメント)。1 次モーメントは押し込み子の形に依らずモーメント M そのものなので、**半空間では係数 −(1−2ν)/(2G) が形状不変**。
    ただし実機のゲルは有限厚で剛体裏打ち(非圧縮に近い)、半空間の (1−2ν) 結合は ν 0.48 で 0.04 倍に消え、実機の信号は有限厚の膨らみから来る
    (有限要素で符号が逆、下記)。半空間は対称性・直線性・形状不変・分解の門であって、大きさの門ではない(正直に)。
  * ねじり(法線まわり): 剛体円形領域の無滑りねじり(Reissner–Sagoci、Johnson §3.9 相当)q_θ = 3M_z r/(4πa³√(a²−r²))、ねじれ角
    β = 3M_z/(16Ga³)、円内の表面変位 u_θ = βr(剛体回転)。β の式は Cerruti 核の畳み込み(:mod:`tacslip`、独立実装)で円内の u_θ/r が一様に β と
    一致することで数値検証する。Lubkin (1951) の部分滑りねじり(固着半径 c と M_z、楕円積分)の閉形式は一次資料で式を確かめられなかったので
    実装しない。**どちらの接触かで無滑りが成り立つ範囲が違う**(本モジュールの導出): 平頭押し込み子の圧 p = P/(2πa√(a²−r²)) なら
    q_θ/(μp) = 3M_z r/(2μPa²) は縁で有限(最大 3M_z/(2μPa))で、全滑りのトルク πμPa/4 の 8/(3π) ≈ 0.85 倍までは無滑りが厳密。
    Hertz 接触(球、p = p₀√(1 − r²/a²))では q_θ/(μp) が r → a で発散するので、どんな小さな M_z でも縁から滑る(Johnson の定性的注意)。
    ★部分滑りでは同じ M_z でもねじれ角が無滑りより大きいので、無滑りの関係 M_z = (16Ga³/3)ω で読むと過大になる(全滑りまでの比 0.5 で
    +33 %、0.8 で +85 %)。2026-10-06 から :func:`torque_decompose` の既定(``torsion_model="partial_slip"``)は Hertz 接触の部分滑りの
    数値解(:func:`cuttouch.torsion_partial_slip`、Cerruti 核の影響行列、両端は Reissner–Sagoci と全滑りのトルク (3π/16)μPa)で直す。
    平頭押し込み子(上の範囲)や接着した円盤は ``torsion_model="no_slip"``(0.4.0 までの値)。
  * 接線荷重 Q(Cattaneo–Mindlin、:mod:`tacslip`)の表面変位の発散(本モジュールの導出): Cerruti 点荷重の場の発散は −(1−ν)Qx/(2πGr³)、
    固着円内は変位が一様なので発散 0。**半空間では純せん断も窓全体に発散双極子を作る**(半径 R の円窓で −(1−ν)QR/(2G)、傾きモーメント
    M_eq = (1−ν)/(1−2ν)·Q·R に相当、ν 0.48 で 13·Q·R)。双極子を傾きだけに効かせるには窓を固着円に限る —— :func:`torque_decompose` の窓の根拠。

有限要素の第 2 真値(有限厚ドーム状ゲルの節点変位、Robo-Touch/Taxim リポジトリ同梱、MIT ライセンス、環境変数 FULLSEYE_TAXIM_DATA の下の
``calibs/``、:func:`tacslip.fem_nodes_load`): 法線押し込み(dz)と斜め押し込み(dx+dz)。有限厚ゲルは押し込み子の下で**膨らむ**(発散 +、
周りに負の環)—— 半空間の (1−2ν) 結合と符号が逆。斜め荷重で増える双極子は Cerruti のせん断漏れの符号(せん断 +x → 双極子 −x)で、
傾きトルクの検証にはならない(荷重の大きさも不明、形と符号だけ)。

試作で測って決めたこと(PoC の門に固定): (1) 平頭押し込み子の縁 1/√(a²−r²) は格子で 4×4 の副標本平均をしても ∫ x p dA が M から 1 % 弱外れる
(可積分だが収束は O(√h))→ 双極子の門は格子で積分した M1 と比べ、名目 M との差は別に報告。(2) 発散は散在点の局所最小二乗(1 + x + y の
平面当て、近傍半径 1.5 ピッチ)で取る —— 規則格子で半径 1.01 ピッチなら 5 点の中心差分と同値(:func:`sceneflow.flow_divergence` が第 2 実装)、
3×3 の 9 点は行平均の差分で縁で 11 % 違う。FEM の散在節点にも同じ op が効く。(3) 窓の矛盾: 傾きは縁の 1/√ 特異点に電荷が集中するので
窓 ≥ a + 1.5 ピッチが要る(a ちょうどで 69 %、1.25a で 99.8 %)、せん断を切るには窓 ≤ c − 1.5 ピッチ。両立しないので小さい窓では傾きが
真値の固定比(0.9a で 0.47)になり較正で吸収する(論文の「係数は較正」と整合)。(4) 基線形式(|u|)は零点後の対称な傾きに対して符号を
知らない(|u| は M の偶関数)。(5) ねじりは剛体回転の最小二乗で取る(平均 curl/2 は縁で 11 % 低い)。(6) 雑音 0.03 px → 半空間 ν 0.48 では
σ_M = 0.11 N·mm(窓 1.5a、252 個)、窓を広げると雑音だけ増える。

規約: 長さ m、力 N、モーメント N·m、角 rad。画素座標 (x, y) = (列, 行)、マーカー中心 (N, 2) float、変位 (N, 2) [m]。圧力の 1 次モーメント
M1 = ∫ (x, y) p dA [N·m]。物体がゲルを押す力は −ẑ p(z はゲルから物体へ)なのでトルク τ = (−M1_y, +M1_x)(式 9 と同じ「直交」)。
双極子 D は「電荷 ρ の 1 次モーメント」の枡で返す(ρ = 発散 / |u| / 放射成分)。``weight="area"`` は Σ ρ_i r_i h²(単位 m³、閉形式の係数と
比べられる)、``weight="mean"`` は論文の (1/N) Σ。G はせん断弾性率 E/(2(1+ν))。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

import tacslip as _S

__all__ = [
    "punch_pressure", "punch_surface_uz", "hertz_pressure_shifted", "ellipse_pressure_shifted", "pressure_first_moment",
    "boussinesq_kernel", "boussinesq_surface_displacement", "surface_divergence_closed_form", "tilt_shear_field",
    "torsion_stick_field", "marker_divergence", "rigid_rotation_fit", "tactile_dipole_moment", "dipole_to_torque_fit",
    "torque_decompose", "dipole_torque_resolution", "grasp_torque_frame",
]

#: 双極子の電荷の取り方(綴り違いは fail-closed)。
DIPOLE_FORMS = ("divergence", "norm_cross", "radial")


# ----------------------------------------------------------------------------------------------------------------------
# 1. 閉形式の圧力分布(外部真値)
def _subgrid(sub: int):
    s = (np.arange(int(sub)) + 0.5) / int(sub) - 0.5
    SX, SY = np.meshgrid(s, s)
    return SX.ravel(), SY.ravel()


def punch_pressure(X, Y, a: float, P: float = 0.0, M1=(0.0, 0.0), pitch: float | None = None, sub: int = 4) -> np.ndarray:
    """平頭円形押し込み子(半径 a [m])の圧力 [Pa]: p = P/(2πa√(a²−r²)) + 3(M1_x x + M1_y y)/(2πa³√(a²−r²))(r < a、外は 0)。
    第 1 項 = Johnson 1985 式 3.34、第 2 項 = ∫ (x, y) p dA = M1 を満たす反対称項(導出はモジュール docstring、門で数値確認)。
    ``pitch`` を渡すと画素を sub×sub の副標本で平均する(縁の 1/√ 特異点の格子誤差を減らす。4×4 で Σ p h² が P と 0.6 %、実測)。
    **Raises** ValueError: a ≤ 0、P < 0、X と Y の形が違う、|M1| > Pa/3(接触が離れる: 線形の式が成り立たない、fail-closed)。"""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    a, P = float(a), float(P)
    mx, my = float(M1[0]), float(M1[1])
    if X.shape != Y.shape or not (a > 0.0) or P < 0.0:
        raise ValueError("punch_pressure: X, Y same shape, a > 0, P >= 0")
    if math.hypot(mx, my) > P * a / 3.0 + 1e-15:
        raise ValueError("punch_pressure: |M1| = %.3e exceeds P a / 3 = %.3e (contact would lift off)" % (math.hypot(mx, my), P * a / 3.0))

    def _p(x, y):
        r2 = x * x + y * y
        inside = r2 < a * a
        root = np.sqrt(np.maximum(a * a - r2, 1e-300))
        val = (P / (2.0 * math.pi * a) + 3.0 * (mx * x + my * y) / (2.0 * math.pi * a ** 3)) / root
        return np.where(inside, val, 0.0)

    if pitch is None or int(sub) <= 1:
        return _p(X, Y)
    sx, sy = _subgrid(sub)
    out = np.zeros_like(X)
    for dx, dy in zip(sx, sy):
        out += _p(X + dx * float(pitch), Y + dy * float(pitch))
    return out / len(sx)


def punch_surface_uz(r, a: float, P: float, G: float, nu: float) -> np.ndarray:
    """平頭円形押し込み子(法線力 P)の半空間表面の法線変位 [m] (沈む向き正): 円内は一様 δ = P(1−ν)/(4Ga)、外側は (2δ/π) arcsin(a/r)
    (Johnson 1985 §3.4 の平頭押し込み子。式番号は本文で確認できず **unverified** —— Boussinesq 核 ``Kz`` の畳み込みと 0.35 % で一致することで
    数値検証した)。**Raises** ValueError: a, P, G ≤ 0。"""
    a, P, G, nu = float(a), float(P), float(G), float(nu)
    if not (a > 0.0 and P > 0.0 and G > 0.0):
        raise ValueError("punch_surface_uz: a, P, G must be > 0")
    r = np.abs(np.asarray(r, np.float64))
    delta = P * (1.0 - nu) / (4.0 * G * a)
    with np.errstate(invalid="ignore", divide="ignore"):
        outer = 2.0 * delta / math.pi * np.arcsin(np.minimum(1.0, a / np.maximum(r, 1e-300)))
    return np.where(r <= a, delta, outer)


def hertz_pressure_shifted(X, Y, hz: dict, d=(0.0, 0.0)) -> np.ndarray:
    """中心を d = (dx, dy) [m] にずらした Hertz 圧 p0 √(1 − r′²/a²) [Pa] (``hz`` = :func:`tacsim.hertz_sphere` の表)。
    小さな傾きトルク τ を受けた把持球は圧の中心が d = τ/P だけ寄る(準静的なモーメント釣合い)ので、ずらした Hertz 圧の元の中心まわりの
    1 次モーメントは P·d = τ(厳密に線形)。**Raises** ValueError: hz に a/p0 が無い、X と Y の形が違う。"""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    if X.shape != Y.shape or not isinstance(hz, dict) or not all(k in hz for k in ("a", "p0")):
        raise ValueError("hertz_pressure_shifted: X, Y same shape and hz from tacsim.hertz_sphere()")
    a, p0 = float(hz["a"]), float(hz["p0"])
    r2 = (X - float(d[0])) ** 2 + (Y - float(d[1])) ** 2
    return p0 * np.sqrt(np.maximum(0.0, 1.0 - r2 / (a * a)))


def ellipse_pressure_shifted(X, Y, a: float, b: float, P: float, d=(0.0, 0.0)) -> np.ndarray:
    """半軸 a(x)・b(y)[m] の楕円 Hertz 圧 p0 √(1 − x′²/a² − y′²/b²) [Pa]、P = 2πab p0/3(Johnson 1985 式 4.24)、中心を d にずらす。
    b ≫ a で円筒(稜・くさび状)の押し込みに近い形 —— 形状不変の門の 3 つ目。**Raises** ValueError: a, b, P ≤ 0、X と Y の形が違う。"""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    a, b, P = float(a), float(b), float(P)
    if X.shape != Y.shape or not (a > 0.0 and b > 0.0 and P > 0.0):
        raise ValueError("ellipse_pressure_shifted: X, Y same shape and a, b, P > 0")
    p0 = 3.0 * P / (2.0 * math.pi * a * b)
    s = ((X - float(d[0])) / a) ** 2 + ((Y - float(d[1])) / b) ** 2
    return p0 * np.sqrt(np.maximum(0.0, 1.0 - s))


def pressure_first_moment(p, X, Y, pitch: float) -> dict:
    """格子上の圧力 p (n, n) [Pa] の 0 次・1 次モーメント: ``P`` = Σ p h² [N]、``M1`` = Σ (x, y) p h² [N·m]、``tau`` = (−M1_y, M1_x)
    (z はゲルから物体へ、物体がゲルを押す力 −ẑ p のモーメント)。**Raises** ValueError: 形が違う、pitch ≤ 0。"""
    p = np.asarray(p, np.float64); X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    if p.shape != X.shape or X.shape != Y.shape or not (float(pitch) > 0.0):
        raise ValueError("pressure_first_moment: p, X, Y same shape and pitch > 0")
    h2 = float(pitch) ** 2
    m1 = np.array([float((X * p).sum() * h2), float((Y * p).sum() * h2)])
    return {"P": float(p.sum() * h2), "M1": m1, "tau": np.array([-m1[1], m1[0]])}


# ----------------------------------------------------------------------------------------------------------------------
# 2. Boussinesq 核(法線圧 → 表面変位)の FFT 畳み込み
def boussinesq_kernel(n: int, pitch: float, G: float, nu: float, sub: int = 4, with_uz: bool = True) -> dict:
    """法線圧(1 画素 = pitch² に一様 1 Pa)が作る表面変位の離散核(2n 格子、rfft2 済み): ``Kx`` = ū_x、``Ky`` = ū_y(接線、
    −(1−2ν)/(4πG) · x/r² と y/r²、Johnson 1985 §3.2 の点荷重解)、``with_uz`` なら ``Kz`` = ū_z((1−ν)/(2πGr))。
    画素平均(sub² の副標本)。中心画素: ∫□ x/r² dA = 0(奇関数)、∫□ 1/r dA = 4h ln(1+√2)(解析値)。
    :func:`tacslip.cerruti_kernel`(接線 → 接線)と同じ作りの法線版。**Raises** ValueError: n < 8、pitch, G ≤ 0、ν が [0, 0.5] の外。"""
    n, sub = int(n), int(sub)
    pitch, G, nu = float(pitch), float(G), float(nu)
    if n < 8 or not (pitch > 0.0 and G > 0.0) or sub < 1 or not (0.0 <= nu <= 0.5):
        raise ValueError("boussinesq_kernel: need n >= 8, pitch > 0, G > 0, sub >= 1, 0 <= nu <= 0.5")
    m = 2 * n
    idx = np.arange(m)
    off = np.where(idx < n, idx, idx - m).astype(np.float64)
    OX, OY = np.meshgrid(off, off)
    sx, sy = _subgrid(sub)
    kx = np.zeros((m, m)); ky = np.zeros((m, m)); kz = np.zeros((m, m)) if with_uz else None
    for dx, dy in zip(sx, sy):
        Xp = (OX + dx) * pitch; Yp = (OY + dy) * pitch
        r2 = Xp * Xp + Yp * Yp
        with np.errstate(divide="ignore", invalid="ignore"):
            kx += Xp / r2; ky += Yp / r2
            if with_uz:
                kz += 1.0 / np.sqrt(r2)
    kx /= len(sx); ky /= len(sx)
    kx[0, 0] = 0.0; ky[0, 0] = 0.0
    ct = -(1.0 - 2.0 * nu) * pitch * pitch / (4.0 * math.pi * G)
    out = {"Kx": np.fft.rfft2(kx * ct), "Ky": np.fft.rfft2(ky * ct), "n": n, "pitch": pitch, "G": G, "nu": nu}
    if with_uz:
        kz /= len(sx)
        kz[0, 0] = 4.0 * math.log(1.0 + math.sqrt(2.0)) / pitch
        out["Kz"] = np.fft.rfft2(kz * (1.0 - nu) * pitch * pitch / (2.0 * math.pi * G))
    return out


def boussinesq_surface_displacement(p, kern: dict) -> dict:
    """法線圧 p (n, n) [Pa] → 表面変位 ``ux``・``uy``(核に ``Kz`` があれば ``uz``、沈む向きが正)(n, n) [m]。零詰め 2n の線形畳み込み。
    **Raises** ValueError: p が (n, n) でない、kern が :func:`boussinesq_kernel` の表でない。"""
    if not isinstance(kern, dict) or not all(k in kern for k in ("Kx", "Ky", "n")):
        raise ValueError("boussinesq_surface_displacement: kern must be the dict from boussinesq_kernel()")
    q = np.asarray(p, np.float64)
    n = int(kern["n"])
    if q.shape != (n, n):
        raise ValueError("boussinesq_surface_displacement: p must be (%d, %d), got %r" % (n, n, q.shape))
    pad = np.zeros((2 * n, 2 * n)); pad[:n, :n] = q
    Fq = np.fft.rfft2(pad)
    out = {}
    for key, name in (("Kx", "ux"), ("Ky", "uy"), ("Kz", "uz")):
        if key in kern:
            out[name] = np.fft.irfft2(Fq * kern[key], s=(2 * n, 2 * n))[:n, :n]
    return out


def surface_divergence_closed_form(p, G: float, nu: float) -> np.ndarray:
    """半空間の表面接線変位の発散の閉形式 ∇·ū = −(1−2ν) p/(2G)(本モジュールの導出: Boussinesq 点荷重 ū_r = −(1−2ν)P/(4πGr) と
    2 次元の ∇·(r̂/r) = 2πδ²)。畳み込みの数値発散と比べる門(r < 0.8a で 0.2 %、実測)。**Raises** ValueError: G ≤ 0。"""
    if not (float(G) > 0.0):
        raise ValueError("surface_divergence_closed_form: G must be > 0")
    return -(1.0 - 2.0 * float(nu)) * np.asarray(p, np.float64) / (2.0 * float(G))


def tilt_shear_field(p_before, p_after, kern: dict) -> dict:
    """「把持後に零点を取る」論文の手順そのまま: 把持直後の圧 p_before とトルク後の圧 p_after の差 Δp を Boussinesq 核で畳み、
    零点後のマーカー変位 ``ux``・``uy``(・``uz``)と ``dp`` を返す。Δp の 0 次モーメントが 0(法線力不変)なら双極子は原点に依らない。
    **Raises** ValueError: 2 枚の形が違う。"""
    pb = np.asarray(p_before, np.float64); pa = np.asarray(p_after, np.float64)
    if pb.shape != pa.shape:
        raise ValueError("tilt_shear_field: p_before and p_after must have the same shape")
    out = boussinesq_surface_displacement(pa - pb, kern)
    out["dp"] = pa - pb
    return out


# ----------------------------------------------------------------------------------------------------------------------
# 3. ねじり(法線まわり)—— 無滑りの剛体円形領域
def _torsion_stick_traction(X, Y, a: float, Mz: float, pitch: float | None = None, sub: int = 4) -> dict:
    """無滑りねじり(Reissner–Sagoci)の接線トラクション q_θ = 3M_z r/(4πa³√(a²−r²)) [Pa] (r < a)を成分 qx = −q_θ y/r、qy = q_θ x/r で返す
    (反時計回り正)。∫ r q_θ dA = M_z(門)。"""
    X = np.asarray(X, np.float64); Y = np.asarray(Y, np.float64)
    a, Mz = float(a), float(Mz)
    if X.shape != Y.shape or not (a > 0.0):
        raise ValueError("torsion_stick_field: X, Y same shape and a > 0")

    def _q(x, y):
        r2 = x * x + y * y
        inside = r2 < a * a
        root = np.sqrt(np.maximum(a * a - r2, 1e-300))
        qth_over_r = 3.0 * Mz / (4.0 * math.pi * a ** 3) / root            # q_θ / r
        return np.where(inside, -qth_over_r * y, 0.0), np.where(inside, qth_over_r * x, 0.0)

    if pitch is None or int(sub) <= 1:
        qx, qy = _q(X, Y)
    else:
        sx, sy = _subgrid(sub)
        qx = np.zeros_like(X); qy = np.zeros_like(X)
        for dx, dy in zip(sx, sy):
            a1, a2 = _q(X + dx * float(pitch), Y + dy * float(pitch))
            qx += a1; qy += a2
        qx /= len(sx); qy /= len(sx)
    return {"qx": qx, "qy": qy, "beta_times_G": 3.0 * Mz / (16.0 * a ** 3), "Mz": Mz, "a": a}


def _tangential_displacement(qx, qy, kern: dict) -> dict:
    """接線トラクション 2 成分 (qx, qy) [Pa] → 表面接線変位 ux・uy [m]。:func:`tacslip.cerruti_kernel` は x 向き荷重の核(Kxx, Kyx)しか
    持たないので、y 向き荷重は転置で使う(正方・等ピッチの格子でだけ正しい: Kxx(x, y) の y 荷重版 = Kxx(y, x))。"""
    ux = _S.cerruti_surface_displacement(qx, kern)
    uy_t = _S.cerruti_surface_displacement(np.asarray(qy, np.float64).T, kern)
    return {"ux": ux["ux"] + uy_t["uy"].T, "uy": ux["uy"] + uy_t["ux"].T}


def torsion_stick_field(X, Y, a: float, Mz: float, kern: dict, G: float) -> dict:
    """無滑りねじり(Reissner–Sagoci、Johnson 1985 §3.9 相当、式番号は未確認 → 畳み込みで数値検証)の表面変位場: トラクション
    q_θ = 3M_z r/(4πa³√(a²−r²)) を :func:`tacslip.cerruti_kernel` の核で畳んだ ``ux``・``uy`` [m] と、閉形式 ``beta`` = 3M_z/(16Ga³)、
    円内の剛体回転 ``ux_cf`` = −βy・``uy_cf`` = βx(r < a)、トラクション ``qx``・``qy``。畳み込みが円内で一様な u_θ/r = β を返すことで β の式を
    独立実装で検証する(−0.5 %、一様性 0.14 %、実測)。これは無滑りの場: 平頭押し込み子なら全滑りの 8/(3π) 倍まで厳密だが、Hertz 接触では
    縁から必ず滑る —— Hertz 接触の部分滑りの場は :func:`cuttouch.torsion_partial_slip` の ``field=True``(モジュール docstring 参照)。
    **Raises** ValueError: G ≤ 0、a ≤ 0、X と Y の形が違う、核の格子が合わない。"""
    if not (float(G) > 0.0):
        raise ValueError("torsion_stick_field: G must be > 0")
    if not isinstance(kern, dict) or "pitch" not in kern:
        raise ValueError("torsion_stick_field: kern must be the dict from tacslip.cerruti_kernel()")
    tr = _torsion_stick_traction(X, Y, a, Mz, pitch=float(kern["pitch"]))
    u = _tangential_displacement(tr["qx"], tr["qy"], kern)
    beta = tr["beta_times_G"] / float(G)
    r = np.hypot(X, Y)
    u.update({"beta": beta, "ux_cf": np.where(r < a, -beta * Y, 0.0), "uy_cf": np.where(r < a, beta * X, 0.0), "qx": tr["qx"], "qy": tr["qy"]})
    return u


# ----------------------------------------------------------------------------------------------------------------------
# 4. マーカー場の微分と双極子(論文の式の再実装)
def marker_divergence(pts, u, radius: float, min_neighbors: int = 4, k_max: int = 24) -> dict:
    """散在マーカー pts (N, 2) と変位 u (N, 2) から各点の発散 ``div`` = ∂ux/∂x + ∂uy/∂y と回転 ``curl`` = ∂uy/∂x − ∂ux/∂y
    (単位は u の単位 ÷ pts の単位)。近傍半径 ``radius`` 内(最大 ``k_max`` 個)の点に平面 c0 + c1 x + c2 y を最小二乗で当てる
    (規則格子 + 半径 1.01 ピッチなら 5 点の中心差分と同値で :func:`sceneflow.flow_divergence` と 1e-15、半径 1.5 ピッチの 9 点は行平均の差分で
    縁で 11 % 違う、実測)。正規方程式を点ごとに一括で解く。近傍が ``min_neighbors`` 未満、または正規方程式が特異(共線)な点は
    ``valid`` = False、div/curl = nan(fail-closed: 黙って 0 にしない)。FEM の散在節点にも同じ op。
    **Raises** ValueError: pts/u が (N, 2) でない、形が違う、radius ≤ 0、N < min_neighbors。"""
    pts = np.asarray(pts, np.float64); u = np.asarray(u, np.float64)
    radius = float(radius)
    if pts.ndim != 2 or pts.shape[1] != 2 or u.shape != pts.shape or not (radius > 0.0) or len(pts) < int(min_neighbors):
        raise ValueError("marker_divergence: pts and u must be (N, 2) with N >= min_neighbors, radius > 0")
    n = len(pts)
    k = int(min(k_max, n))
    tree = cKDTree(pts)
    dist, idx = tree.query(pts, k=k)
    w = (dist <= radius).astype(np.float64)                                   # (N, k) 0/1 重み
    cnt = w.sum(1)
    dx = (pts[idx, 0] - pts[:, None, 0]) / radius; dy = (pts[idx, 1] - pts[:, None, 1]) / radius   # 半径で無次元化(条件数を揃える)
    one = np.ones_like(dx)
    B = np.stack([one, dx, dy], -1) * w[..., None]                            # (N, k, 3)
    AtA = np.einsum("nki,nkj->nij", B, B)
    rhs = np.einsum("nki,nkc->nic", B, u[idx] * w[..., None])                 # (N, 3, 2)
    det = np.linalg.det(AtA)
    valid = (cnt >= int(min_neighbors)) & (np.abs(det) > 1e-9 * np.maximum(cnt, 1.0) ** 3)
    coef = np.full((n, 3, 2), np.nan)
    if valid.any():
        coef[valid] = np.linalg.solve(AtA[valid], rhs[valid])
    div = (coef[:, 1, 0] + coef[:, 2, 1]) / radius
    curl = (coef[:, 1, 1] - coef[:, 2, 0]) / radius
    div[~valid] = np.nan; curl[~valid] = np.nan
    return {"div": div, "curl": curl, "valid": valid, "n_valid": int(valid.sum())}


def rigid_rotation_fit(pts, u, window=None) -> dict:
    """窓内のマーカー場に剛体変位 u ≈ t + ω ẑ×r を最小二乗で当てる: ``t`` = 平均変位、``omega`` = Σ (x′u′_y − y′u′_x)/Σ r′²
    (′ は窓内平均を引いたもの)、``resid_rms`` = 残差 RMS、``n``。無滑りねじりでは円内が剛体回転(u_θ = βr)なので ω = β が真値
    (平均 curl/2 は円の縁で当てはめが外に漏れて低くなる —— 実測 11 %)。``window`` = (cx, cy, R)。**Raises** ValueError: 点が 3 未満。"""
    pts = np.asarray(pts, np.float64); u = np.asarray(u, np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2 or u.shape != pts.shape:
        raise ValueError("rigid_rotation_fit: pts and u must be (N, 2) of the same length")
    keep = np.ones(len(pts), bool)
    if window is not None:
        cx, cy, R = (float(v) for v in window)
        keep &= np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) <= R
    if keep.sum() < 3:
        raise ValueError("rigid_rotation_fit: fewer than 3 markers in the window")
    p = pts[keep] - pts[keep].mean(0); t = u[keep].mean(0); v = u[keep] - t
    omega = float((p[:, 0] * v[:, 1] - p[:, 1] * v[:, 0]).sum() / (p * p).sum())
    res = v - omega * np.column_stack([-p[:, 1], p[:, 0]])
    return {"t": t, "omega": omega, "resid_rms": float(np.sqrt((res ** 2).sum(1).mean())), "n": int(keep.sum())}


def _divergence_centroid_midpoint(pts, rho) -> dict:
    """論文の式 6–7: 正の電荷(ρ > 0)の重心 C⁺ と負の電荷(ρ < 0)の重心 C⁻ の中点 m を原点にする。どちらかが無いときはある方だけ
    (両方無ければ全点の平均、degenerate = True)。"""
    pts = np.asarray(pts, np.float64); rho = np.asarray(rho, np.float64)
    pos = np.where(rho > 0, rho, 0.0); neg = np.where(rho < 0, -rho, 0.0)
    cp = (pos[:, None] * pts).sum(0) / pos.sum() if pos.sum() > 0 else None
    cn = (neg[:, None] * pts).sum(0) / neg.sum() if neg.sum() > 0 else None
    if cp is not None and cn is not None:
        return {"m": 0.5 * (cp + cn), "c_plus": cp, "c_minus": cn, "degenerate": False}
    c = cp if cp is not None else cn
    if c is None:
        return {"m": pts.mean(0), "c_plus": None, "c_minus": None, "degenerate": True}
    return {"m": c, "c_plus": cp, "c_minus": cn, "degenerate": True}


def tactile_dipole_moment(pts, u, form: str = "divergence", origin="midpoint", weight: str = "area", area: float | None = None,
                          window=None, rho=None, radius: float | None = None) -> dict:
    """触覚双極子モーメント D = Σ_i w ρ_i r_i(2 成分)。``form``:
      * ``"divergence"`` —— 論文(arXiv 2404.15626)式 4–8: ρ_i = (∇·u)_i(``rho`` を渡すか、``radius`` で :func:`marker_divergence`)。
      * ``"norm_cross"`` —— 論文の基線(式 10–11、Yamaguchi & Atkeson 流): ρ_i = |u_i|(ベクトルのノルムを法線力の代わりに)。
        l_i × f_i の傾き成分は (l_y|u|, −l_x|u|) で D を 90° 回したものなので、同じ「1 次モーメント」の枡で返す。零点後の対称な傾きでは
        |u| が M の偶関数なので恒等的に 0(符号を知らない、門)。
      * ``"radial"`` —— 本モジュールの変種: ρ_i = u_i · r̂_i(放射成分)。
    ``origin``: ``"midpoint"``(式 6–7、正負の重心の中点)/ ``"centre"``(pts の平均、基線の作法)/ (x0, y0)。
    ``weight``: ``"area"`` = 1 点あたり面積 ``area`` [m²] を掛ける(閉形式の係数 −(1−2ν)/(2G) と比べられる、単位 m³)/ ``"mean"`` = 1/N(論文)。
    ``window`` = (cx, cy, R) なら半径 R 内の点だけ使う(せん断の漏れを切る窓、根拠はモジュール docstring)。valid でない点(nan)は除く。
    返り ``D`` (2,)、``tau_dir`` = (−D_y, D_x)(式 9 の向き、係数なし)、``origin``、``n``、``rho``、``form``、``keep``。
    **Raises** ValueError: form/origin/weight が未知(綴り違いは fail-closed)、pts/u の形、area 無しの "area"、使える点が 3 未満。"""
    if form not in DIPOLE_FORMS:
        raise ValueError("tactile_dipole_moment: unknown form %r (use one of %s)" % (form, DIPOLE_FORMS))
    if weight not in ("area", "mean"):
        raise ValueError("tactile_dipole_moment: weight must be 'area' or 'mean', got %r" % (weight,))
    pts = np.asarray(pts, np.float64); u = np.asarray(u, np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2 or u.shape != pts.shape:
        raise ValueError("tactile_dipole_moment: pts and u must be (N, 2) of the same length")
    if weight == "area" and (area is None or not (float(area) > 0.0)):
        raise ValueError("tactile_dipole_moment: weight='area' needs area > 0 (m² per marker)")
    keep = np.ones(len(pts), bool)
    if window is not None:
        cx, cy, R = (float(v) for v in window)
        keep &= np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) <= R
    if form == "divergence":
        if rho is None:
            if radius is None:
                raise ValueError("tactile_dipole_moment: form='divergence' needs rho (per-marker divergence) or radius")
            rho = marker_divergence(pts, u, float(radius))["div"]
        rho = np.asarray(rho, np.float64)
        if rho.shape != (len(pts),):
            raise ValueError("tactile_dipole_moment: rho must be (N,)")
        keep &= np.isfinite(rho)
    elif form == "norm_cross":
        rho = np.hypot(u[:, 0], u[:, 1])
    else:
        c0 = pts[keep].mean(0)
        rr = pts - c0
        nr = np.maximum(np.hypot(rr[:, 0], rr[:, 1]), 1e-300)
        rho = (u[:, 0] * rr[:, 0] + u[:, 1] * rr[:, 1]) / nr
    P, R_ = pts[keep], rho[keep]
    if len(P) < 3:
        raise ValueError("tactile_dipole_moment: fewer than 3 usable markers")
    if isinstance(origin, str):
        if origin == "midpoint":
            o = _divergence_centroid_midpoint(P, R_)["m"]
        elif origin == "centre":
            o = P.mean(0)
        else:
            raise ValueError("tactile_dipole_moment: unknown origin %r (use 'midpoint', 'centre' or (x0, y0))" % (origin,))
    else:
        o = np.asarray(origin, np.float64).reshape(2)
    w = float(area) if weight == "area" else 1.0 / len(P)
    D = w * ((P - o) * R_[:, None]).sum(0)
    return {"D": D, "tau_dir": np.array([-D[1], D[0]]), "origin": o, "n": int(len(P)), "rho": rho, "form": form, "keep": keep}


def dipole_to_torque_fit(D, M) -> dict:
    """双極子の 1 成分列 D (K,) と既知のモーメント M (K,) [N·m] の線形較正 D ≈ k M(原点通過)と D ≈ k₁ M + b(切片あり)。
    返り ``k``・``R2``(原点通過の決定係数 = 1 − SS_res/SS_tot)・``k1``・``b``・``R2_affine``・``rmse_M``(M に換算した残差 RMS)。
    論文の較正係数 c = 1/k に当たる。**Raises** ValueError: K < 2、形が違う、M がすべて同じ。"""
    D = np.asarray(D, np.float64).ravel(); M = np.asarray(M, np.float64).ravel()
    if D.shape != M.shape or len(D) < 2 or np.ptp(M) <= 0.0:
        raise ValueError("dipole_to_torque_fit: need >= 2 samples with varying M and matching shapes")
    k = float((D * M).sum() / (M * M).sum())
    res = D - k * M
    st = float(((D - D.mean()) ** 2).sum())
    R2 = 1.0 - float((res ** 2).sum()) / st if st > 0 else float("nan")
    A = np.column_stack([M, np.ones_like(M)])
    (k1, b), *_ = np.linalg.lstsq(A, D, rcond=None)
    res1 = D - (k1 * M + b)
    R2a = 1.0 - float((res1 ** 2).sum()) / st if st > 0 else float("nan")
    return {"k": k, "R2": R2, "k1": float(k1), "b": float(b), "R2_affine": R2a,
            "rmse_M": float(np.sqrt((res ** 2).mean())) / abs(k) if k != 0 else float("inf")}


#: ねじりの換算の模型(:func:`torque_decompose`、綴り違いは fail-closed)。
TORSION_MODELS = ("partial_slip", "no_slip")


def torque_decompose(pts, u, area: float, G: float, nu: float, a: float | None = None, window=None, radius: float | None = None,
                     coef: float | None = None, P: float | None = None, mu: float | None = None,
                     torsion_model: str = "partial_slip") -> dict:
    """マーカー場を 3 つの力学量に分ける: ``translation`` = 窓内の平均変位(せん断 Q、単向成分)、``omega`` = 剛体回転角
    (:func:`rigid_rotation_fit`)→ ねじり ``Mz``(a が要る; ``omega_curl`` = 平均 curl/2 は参考)、
    ``D`` = 発散双極子(面積重み)→ 傾き ``M1`` = D / coef(coef 既定 = 半空間の閉形式 −(1−2ν)/(2G)、実機は較正値を渡す)、``tau`` = (−M1_y, M1_x)。
    発散・curl は平均変位を引いても変わらない(定数の微分は 0)ので順序に依らない。窓 (cx, cy, R) は接触円に限る(半空間では純せん断が
    窓全体に発散双極子を作るため、モジュール docstring 参照)。``radius`` = 発散の近傍半径(必須)。

    ねじり: 無滑りの関係(Reissner–Sagoci)M = (16Ga³/3)ω を ``Mz_no_slip`` に残す。★``torsion_model="partial_slip"``(既定、2026-10-06 から)
    では、Hertz 接触(法線力 ``P``、摩擦 ``mu``、接触半径 ``a``)の部分滑りの数値解(:func:`cuttouch.torsion_partial_slip` の
    ``contact`` と ``from_no_slip_read``)で直した値を ``Mz`` に返す —— Hertz 接触のねじりは縁から必ず滑るので、無滑りの関係のままだと
    M を過大に読む(全滑りまでの比 0.5 で +33 %、0.8 で +85 %)。``Mz_ratio``(全滑りまでの比)、``Mz_c_over_a``(固着円の半径 / a)、
    ``Mz_readable``(全滑りでなく、固着円が当てはめの窓の半径を含む —— 偽なら数は返すが当てにならない。窓が無ければ偽)も返す。
    a を渡して P か mu が無いと補正できないので ValueError(黙って無滑りの値を返さない)。``"no_slip"`` は 0.4.0 までの値
    (``Mz`` = ``Mz_no_slip``)—— 平頭押し込み子(全滑りの 8/(3π) 倍まで無滑りが厳密)や接着した円盤の場合。
    **Raises** ValueError: area, G ≤ 0、ν が [0, 0.5] の外、点の形、radius 無し、窓内の点が 3 未満、torsion_model の綴り違い、
    partial_slip で a があるのに P・mu が正の有限でない。"""
    if not (float(area) > 0.0 and float(G) > 0.0) or not (0.0 <= float(nu) <= 0.5):
        raise ValueError("torque_decompose: need area > 0, G > 0, 0 <= nu <= 0.5")
    if radius is None:
        raise ValueError("torque_decompose: radius (neighbourhood for the divergence/curl fit) is required")
    if torsion_model not in TORSION_MODELS:
        raise ValueError("torque_decompose: torsion_model must be 'partial_slip' or 'no_slip', got %r" % (torsion_model,))
    if torsion_model == "partial_slip" and a is not None and float(a) > 0.0:
        for nm, v in (("P", P), ("mu", mu)):
            if v is None or isinstance(v, bool) or not (math.isfinite(float(v)) and float(v) > 0.0):
                raise ValueError("torque_decompose: torsion_model='partial_slip' needs the normal force P and friction mu of the Hertz "
                                 "contact to correct Mz (got %s=%r); pass torsion_model='no_slip' for a flat punch or a bonded disc" % (nm, v))
    pts = np.asarray(pts, np.float64); u = np.asarray(u, np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2 or u.shape != pts.shape:
        raise ValueError("torque_decompose: pts and u must be (N, 2)")
    dc = marker_divergence(pts, u, float(radius))
    keep = dc["valid"].copy()
    if window is not None:
        cx, cy, R = (float(v) for v in window)
        keep &= np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) <= R
    if keep.sum() < 3:
        raise ValueError("torque_decompose: fewer than 3 usable markers in the window")
    rf = rigid_rotation_fit(pts[keep], u[keep])
    t = rf["t"]
    omega = rf["omega"]
    omega_curl = 0.5 * float(np.nanmean(dc["curl"][keep]))
    dp = tactile_dipole_moment(pts, u, "divergence", origin="midpoint", weight="area", area=float(area), window=window, rho=dc["div"])
    c = float(coef) if coef is not None else -(1.0 - 2.0 * float(nu)) / (2.0 * float(G))
    M1 = dp["D"] / c
    out = {"translation": t, "omega": omega, "omega_curl": omega_curl, "D": dp["D"], "M1": M1, "tau": np.array([-M1[1], M1[0]]), "coef": c,
           "n": int(keep.sum()), "div": dc["div"], "curl": dc["curl"], "origin": dp["origin"], "rot_resid_rms": rf["resid_rms"]}
    if a is not None and float(a) > 0.0:
        mz_ns = 16.0 * float(G) * float(a) ** 3 / 3.0 * omega
        out.update({"Mz": mz_ns, "Mz_no_slip": mz_ns, "torsion_model": torsion_model})
        if torsion_model == "partial_slip":
            import cuttouch as _CT                              # 遅延 import(cuttouch → pegtactile → tactorque の循環を避ける)
            info = _CT.torsion_partial_slip(mz_ns, float(P), contact={"a": float(a), "mu": float(mu), "G": float(G)}, from_no_slip_read=True)
            r_core = float(window[2]) if window is not None else float("inf")
            out.update({"Mz": float(info["M"]), "Mz_ratio": float(info["ratio"]), "Mz_c_over_a": float(info["c_over_a"]),
                        "Mz_readable": bool(not info["slipping"] and info["c_over_a"] * float(a) >= r_core)})
    return out


def dipole_torque_resolution(pts, u, sigma_px: float, pitch: float, coef: float, area: float, radius: float, trials: int = 100,
                             window=None, seed: int = 0, form: str = "divergence") -> dict:
    """マーカー重心の雑音 σ [px] を変位に足して双極子を ``trials`` 回取り直し、トルク分解能 σ_M = σ_D/|coef| [N·m] を測る。
    返り ``sigma_D`` (2,)、``sigma_M`` (2,)、``D0``(雑音なし)、``snr`` = |D0|/σ_D、``trials``。σ_M ∝ σ(実測)。
    **Raises** ValueError: σ < 0、trials < 2、coef = 0。"""
    if not (float(sigma_px) >= 0.0) or int(trials) < 2 or not (float(coef) != 0.0):
        raise ValueError("dipole_torque_resolution: need sigma_px >= 0, trials >= 2, coef != 0")
    rng = np.random.default_rng(int(seed))
    pts = np.asarray(pts, np.float64); u = np.asarray(u, np.float64)
    base = tactile_dipole_moment(pts, u, form, origin="centre", weight="area", area=area, window=window, radius=radius)["D"]
    Ds = []
    for _ in range(int(trials)):
        un = u + rng.normal(0.0, float(sigma_px) * float(pitch), size=u.shape)
        Ds.append(tactile_dipole_moment(pts, un, form, origin="centre", weight="area", area=area, window=window, radius=radius)["D"])
    Ds = np.array(Ds)
    sD = Ds.std(0, ddof=1)
    return {"sigma_D": sD, "sigma_M": sD / abs(float(coef)), "D0": base, "snr": np.abs(base) / np.maximum(sD, 1e-300), "trials": int(trials)}


def grasp_torque_frame(m_ref, m_cur, dark: float, pitch_px: float, r_px: float, pitch: float, G: float, nu: float, a: float | None = None,
                       window=None, coef: float | None = None, P: float | None = None, mu: float | None = None,
                       torsion_model: str = "partial_slip") -> dict:
    """像から 1 回で: 基準・現在のマーカー像(:func:`tacslip.marker_image`)→ :func:`tacslip.marker_track` → m 単位の場 → :func:`torque_decompose`。
    ``pitch_px``・``r_px`` = マーカー格子と半径 [px]、``pitch`` = m/px、``window`` は [px] の (cx, cy, R)。マーカー 1 個あたりの面積 = (pitch_px·pitch)²、
    発散の近傍半径 = 1.5 ピッチ。``P``・``mu``・``torsion_model`` はねじりの換算(:func:`torque_decompose`、既定は Hertz 接触の部分滑りで
    P と mu が要る、平頭押し込み子は ``"no_slip"``)。返り = torque_decompose の表 + ``track``(matched・n0・n1・p0・u [px])。
    **Raises** ValueError: 追跡の対応が 9 個未満(双極子に足りない)、pitch ≤ 0、torque_decompose の ValueError。"""
    if not (float(pitch) > 0.0):
        raise ValueError("grasp_torque_frame: pitch (m per px) must be > 0")
    tr = _S.marker_track(m_ref, m_cur, dark, pitch_px, r_px)
    if tr["matched"] < 9:
        raise ValueError("grasp_torque_frame: only %d matched markers (need >= 9)" % tr["matched"])
    pts_m = tr["p0"] * float(pitch)
    u_m = tr["u"] * float(pitch)
    area = (float(pitch_px) * float(pitch)) ** 2
    win = None
    if window is not None:
        win = (float(window[0]) * pitch, float(window[1]) * pitch, float(window[2]) * pitch)
    out = torque_decompose(pts_m, u_m, area, G, nu, a=a, window=win, radius=1.5 * float(pitch_px) * float(pitch), coef=coef,
                           P=P, mu=mu, torsion_model=torsion_model)
    out["track"] = {"matched": tr["matched"], "n0": tr["n0"], "n1": tr["n1"], "p0": tr["p0"], "u": tr["u"]}
    return out


def _grid_to_markers(X, Y, fields, pts_px, pitch: float):
    """格子場 (n, n) [m] をマーカー中心 pts_px (N, 2) [px] で双線形標本化して (N, 2) の変位 [m] に。``fields`` = (ux, uy)。"""
    p = np.asarray(pts_px, np.float64)
    out = [ndimage.map_coordinates(np.asarray(f, np.float64), [p[:, 1], p[:, 0]], order=1, mode="nearest") for f in fields]
    return np.column_stack(out)
