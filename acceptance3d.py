# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""acceptance3d —— 光学式 3D センサの仮想受入試験(VDI/VDE 2634 Part 2/3・ISO 10360-13 の考え方に沿った評価量)。

Virtual acceptance test of optical 3-D sensors, following the *ideas* of VDI/VDE 2634 Part 2/3 and
ISO 10360-13. **Not a conformance implementation**: the normative texts are paid documents and are not
copied here. The quantity definitions below are the ones described in the open literature that applies
the guideline (cited per function), and the placement rule is a Fullseye convention modelled on it.

## 何ができるか / What it does

1. 試験体(球・球間距離のバー = ダンベル・平面)を測定体積の中に置く規則(:func:`acceptance_layout`)。
2. 点群から評価量を計算する(実機の点群でもシミュレーションの点群でも同じ op):
   探針の誤差の形状 PF と寸法 PS(:func:`sphere_probing_error`)、球間距離の誤差 SD
   (:func:`sphere_spacing_error`)、平面度の誤差 F(:func:`plane_flatness_error`)。
3. MPE(最大許容誤差)に対する合否(:func:`acceptance_verdict`)。
4. **Fullseye だけの層**: シミュレーションのセンサ(理想 / 三角測量の雑音則 / 既存 :mod:`itof` の物理モデル)
   で試験体を「測って」受入試験を回す(:func:`acceptance_scan`、:func:`virtual_acceptance_test`)。
   誤差の要因(雑音・校正誤差・多重反射・反射率)を 1 つずつ入れて、**どれが合否を決めるか**を返す
   (:func:`acceptance_error_budget`)。真値は場面の側(解析的な光線と球・平面の交点)にある。

## 評価量の定義(公開文献から)/ Definitions (from the open literature)

* **PF(探針の誤差・形状)**: 球の点群にガウスの最小二乗で球(半径は自由)を当て、点の半径方向の距離の
  範囲 ``R_max − R_min``。最大偏差の点を最大 0.3 % まで除いてよい
  (Carfagni et al., *Sensors* 19(3):489, 2019, doi:10.3390/s19030489; Carfagni et al.,
  *IEEE Sensors J.* 17(14), 2017, doi:10.1109/JSEN.2017.2703829)。
* **PS(探針の誤差・寸法)**: 当てた球の直径 − 校正済みの直径(符号つき)。同上。
* **SD(球間距離の誤差)**: 2 つの球の中心間距離(各球は半径自由の最小二乗)− 校正済みの距離(符号つき)。
  ダンベルを測定体積の中の 7 姿勢に置く(同上; Eiríksson et al., ISPRS Archives XL-5/W8, 2016,
  doi:10.5194/isprs-archives-XL-5-W8-7-2016)。
* **F(平面度の誤差)**: 平面の点群に最小二乗の平面を当て、符号つき距離の範囲 ``max − min``(除外 0.3 % まで)。
  Ramm et al. 2025(*IEEE Sensors Letters*, doi:10.1109/LSENS.2025.3647147)は同じ評価を単眼深度 AI に当てた。

★7 姿勢の具体的な向き(空間対角線 4 本 + 面の対角線 3 本)は **Fullseye の約束**であり、規格の図の写しではない。
規格どおりかを言えるのは本文を持つ人だけなので、この族は「準拠」と名乗らない。

## 数値の門(tests/test_acceptance3d.py)

* 完全な球・平面の点群 → PF = PS = F = 0(1e-9 以内)、ダンベル → SD = 0。
* 尺度の誤差 s(全点を原点まわりに s 倍)→ SD = (s−1)·L、PS = (s−1)·D が**厳密に**出る(閉形式)。
* 半径方向に b だけ外へ押した球 → PS = 2b、PF = 0。
* 純ガウス雑音 σ・N 点の PF の期待値 = σ·E[正規標本 N 個の範囲](Tippett 1925 の積分。d2(25) = 3.931 の公表値で
  積分そのものを検算する)。
* 理想センサの仮想受入試験 → 全評価量 ≈ 0(場面の解析解と逆投影の往復だけ)。

依存は numpy(+ itof センサを使うときの :mod:`itof`、それ自体 numpy のみ)。
"""
from __future__ import annotations

import math

import numpy as np

#: 除外してよい点の割合の上限(公開文献の記述: 最大 0.3 %)。
#: Upper bound on the excluded fraction (0.3 % in the literature cited above).
DEFAULT_EXCLUDE = 0.003

#: 点群の上限(大きすぎる入力で固まらないための線)。Upper bound on points per call.
MAX_POINTS = 5_000_000

_SENSOR_KINDS = ("ideal", "triangulation", "itof")


# =========================================================================== #
# 入力の検査 / input validation (fail-closed)
# =========================================================================== #
def _points(p, name, op, min_rows):
    if isinstance(p, (str, bytes, dict)) or p is None:
        raise ValueError("%s: %s must be an (N, 3) numeric array (got %s)" % (op, name, type(p).__name__))
    a = np.asarray(p)
    if a.dtype == object or a.dtype.kind not in "biuf":
        raise ValueError("%s: %s must be real numbers (dtype %s)" % (op, name, a.dtype))
    a = a.astype(np.float64)
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError("%s: %s must have shape (N, 3) (got %s)" % (op, name, a.shape))
    if a.shape[0] < min_rows:
        raise ValueError("%s: %s needs >= %d points (got %d)" % (op, name, min_rows, a.shape[0]))
    if a.shape[0] > MAX_POINTS:
        raise ValueError("%s: %s has %d points (> %d)" % (op, name, a.shape[0], MAX_POINTS))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s contains NaN or inf" % (op, name))
    return a


def _num(v, name, op, lo=None, hi=None, lo_open=False):
    if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a real number (got %r)" % (op, name, v))
    x = float(v)
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite (got %r)" % (op, name, v))
    if lo is not None and (x < lo or (lo_open and x == lo)):
        raise ValueError("%s: %s must be %s %g (got %g)" % (op, name, ">" if lo_open else ">=", lo, x))
    if hi is not None and x > hi:
        raise ValueError("%s: %s must be <= %g (got %g)" % (op, name, hi, x))
    return x


def _vec3(v, name, op):
    a = np.asarray(v, dtype=float).reshape(-1)
    if a.size != 3 or not np.isfinite(a).all():
        raise ValueError("%s: %s must be 3 finite numbers (got %r)" % (op, name, v))
    return a


def _exclude(v, op):
    return _num(v, "exclude_fraction", op, lo=0.0, hi=0.05)


# =========================================================================== #
# 当てはめ(ガウスの最小二乗)/ Gaussian least-squares fits
# =========================================================================== #
def _sphere_kasa(P):
    """代数(Kåsa)の初期値。重心へ寄せて解く(桁落ち防止)。Algebraic initial guess."""
    p0 = P.mean(0)
    Q = P - p0
    sv = np.linalg.svd(Q, compute_uv=False)
    if sv[-1] <= 1e-9 * sv[0]:
        raise ValueError("points are coplanar or degenerate; no finite sphere fits")
    A = np.hstack([2.0 * Q, np.ones((len(Q), 1))])
    b = (Q ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    r2 = sol[3] + c @ c
    if not np.isfinite(r2) or r2 <= 0:
        raise ValueError("algebraic sphere fit failed (r^2 = %r)" % r2)
    return c + p0, math.sqrt(r2)


def _sphere_geometric(P, fixed_radius=None, iters=100):
    """幾何(直交距離)の最小二乗球。Gauss-Newton、初期値は Kåsa。

    Geometric least-squares sphere: minimises sum (|p_i - c| - R)^2 (Gauss-Newton from the
    algebraic start). With ``fixed_radius`` only the centre is free."""
    c, R = _sphere_kasa(P)
    if fixed_radius is not None:
        R = float(fixed_radius)
    scale = max(R, 1e-300)
    for _ in range(iters):
        d = P - c
        rho = np.linalg.norm(d, axis=1)
        if np.any(rho <= 0):
            raise ValueError("a point coincides with the sphere centre; geometric fit undefined")
        u = d / rho[:, None]
        r = rho - R
        if fixed_radius is None:
            J = np.hstack([-u, -np.ones((len(P), 1))])
        else:
            J = -u
        step, *_ = np.linalg.lstsq(J, -r, rcond=None)
        c = c + step[:3]
        if fixed_radius is None:
            R = R + step[3]
        if np.max(np.abs(step)) <= 1e-14 * scale:
            break
    rho = np.linalg.norm(P - c, axis=1)
    return c, float(R), rho - R


def _plane_lsq(P):
    """直交回帰の平面(SVD)。Orthogonal-regression plane through the centroid (SVD)."""
    c = P.mean(0)
    _, s, vt = np.linalg.svd(P - c, full_matrices=False)
    if s[1] <= 1e-9 * s[0]:
        raise ValueError("points are collinear; no plane normal is defined")
    n = vt[-1] / np.linalg.norm(vt[-1])
    return c, n, (P - c) @ n


def _with_exclusion(P, fit, frac):
    """最大偏差の点を ``floor(frac·N)`` 個除いて当て直す。Drop the floor(frac*N) largest |residuals|, refit once."""
    res = fit(P)
    k = int(math.floor(frac * len(P)))
    if k <= 0:
        return P, res, 0
    keep = np.argsort(np.abs(res[-1]), kind="stable")[: len(P) - k]
    Pk = P[np.sort(keep)]
    return Pk, fit(Pk), k


# =========================================================================== #
# 評価量 / evaluation quantities (same op for measured and simulated clouds)
# =========================================================================== #
def sphere_probing_error(points, calibrated_diameter, exclude_fraction=DEFAULT_EXCLUDE):
    """球の点群から探針の誤差の形状 PF と寸法 PS を計算する(``table``)。

    Probing error of form (PF) and of size (PS) from the point cloud of one calibrated sphere.

    ガウスの最小二乗で半径自由の球を当て(代数解を初期値に Gauss-Newton)、半径方向の偏差が最大の点を
    ``floor(exclude_fraction · N)`` 個まで除いて当て直す。``pf = R_max − R_min``(除外後の点の、当てた中心から
    の距離の範囲)、``ps = 2R − calibrated_diameter``(符号つき: 大きく測れば正)。
    A free-radius least-squares sphere is fitted, at most ``floor(exclude_fraction*N)`` points with the
    largest radial deviation are dropped and the sphere refitted; ``pf`` is the range of radial distances,
    ``ps`` the signed diameter error. Definitions as described in Carfagni et al. 2019 (doi:10.3390/s19030489)
    for VDI/VDE 2634 Part 2 — the normative text is not reproduced; this is not a conformance claim.

    返す ``dict``: ``pf``、``ps``、``diameter``、``radius``、``center`` (3,)、``residual_rms``、``n_points``、
    ``n_used``、``n_excluded``、``exclude_fraction``、``calibrated_diameter``。単位は入力の点の単位のまま。
    限界: 球冠しか見えない点群(片側から撮った球)では半径と中心が相関し、PS は雑音に敏感になる
    (見えている角度が小さいほど)。``residual_rms`` が雑音の目安。

    **Raises** ``ValueError``: 点が (N, 3) でない・10 点未満・非有限、同一平面上(球が定まらない)、
    ``calibrated_diameter`` が正でない、``exclude_fraction`` が [0, 0.05] の外。
    """
    op = "sphere_probing_error"
    P = _points(points, "points", op, 10)
    D = _num(calibrated_diameter, "calibrated_diameter", op, lo=0.0, lo_open=True)
    frac = _exclude(exclude_fraction, op)
    try:
        Pk, (c, R, res), k = _with_exclusion(P, _sphere_geometric, frac)
    except ValueError as e:
        raise ValueError("%s: %s" % (op, e)) from None
    rho = res + R
    return {"pf": float(rho.max() - rho.min()), "ps": float(2.0 * R - D), "diameter": 2.0 * R,
            "radius": R, "center": c, "residual_rms": float(np.sqrt(np.mean(res ** 2))),
            "n_points": int(len(P)), "n_used": int(len(Pk)), "n_excluded": int(k),
            "exclude_fraction": frac, "calibrated_diameter": D}


def sphere_spacing_error(points_a, points_b, calibrated_distance, exclude_fraction=DEFAULT_EXCLUDE,
                         fixed_diameter=None):
    """ダンベル(2 球)の点群から球間距離の誤差 SD を計算する(``table``)。

    Sphere-spacing error SD of a ball bar: distance of the two fitted sphere centres minus the
    calibrated distance (signed: positive when measured too long).

    各球は :func:`sphere_probing_error` と同じ当てはめ(半径自由、最大偏差の点を除いて当て直し)。
    ``fixed_diameter`` を与えると半径をその値に固定して中心だけを当てる(文献によっては固定半径で評価する;
    既定は自由)。定義は Carfagni et al. 2019 / Eiríksson et al. 2016 の記述による。規格本文の写しではない。
    Each sphere is fitted as in :func:`sphere_probing_error`; ``fixed_diameter`` fixes the radius.

    返す ``dict``: ``sd``、``distance``、``calibrated_distance``、``center_a``、``center_b``、
    ``diameter_a``、``diameter_b``、``pf_a``、``pf_b``、``n_used_a``、``n_used_b``。
    限界: 尺度の誤差は SD に ``(s−1)·L`` で出る(L が長いほど見える)ので、L は測定体積の対角に近いほどよい。

    **Raises** ``ValueError``: どちらかの点群が不正(:func:`sphere_probing_error` と同じ条件)、
    ``calibrated_distance`` が正でない、``fixed_diameter`` が正でない、2 つの中心が重なる。
    """
    op = "sphere_spacing_error"
    A = _points(points_a, "points_a", op, 10)
    B = _points(points_b, "points_b", op, 10)
    L = _num(calibrated_distance, "calibrated_distance", op, lo=0.0, lo_open=True)
    frac = _exclude(exclude_fraction, op)
    fr = None
    if fixed_diameter is not None:
        fr = 0.5 * _num(fixed_diameter, "fixed_diameter", op, lo=0.0, lo_open=True)

    def fit(P):
        return _sphere_geometric(P, fixed_radius=fr)

    try:
        Ak, (ca, Ra, resa), _ = _with_exclusion(A, fit, frac)
        Bk, (cb, Rb, resb), _ = _with_exclusion(B, fit, frac)
    except ValueError as e:
        raise ValueError("%s: %s" % (op, e)) from None
    dist = float(np.linalg.norm(ca - cb))
    if dist <= 0:
        raise ValueError("%s: the two fitted centres coincide" % op)
    return {"sd": dist - L, "distance": dist, "calibrated_distance": L, "center_a": ca, "center_b": cb,
            "diameter_a": 2.0 * Ra, "diameter_b": 2.0 * Rb,
            "pf_a": float(np.ptp(resa)), "pf_b": float(np.ptp(resb)),
            "n_used_a": int(len(Ak)), "n_used_b": int(len(Bk)), "fixed_diameter": fixed_diameter}


def plane_flatness_error(points, exclude_fraction=DEFAULT_EXCLUDE):
    """平面の点群から平面度の誤差 F(最小二乗平面からの符号つき距離の範囲)を計算する(``table``)。

    Flatness measurement error F: range of signed distances from the least-squares (orthogonal-
    regression) plane, after dropping at most ``floor(exclude_fraction*N)`` largest deviations and
    refitting once. Definition as described in Carfagni et al. 2019 for VDI/VDE 2634 Part 2.

    ★最小二乗の平面(Gauss)であり、最小領域(Chebyshev)の平面ではない。最小領域の F は最小二乗の F 以下になる
    (定義から)。正弦のうねり(振幅 A、周期の整数倍)を持つ平面では最小二乗の平面が公称の平面と一致し、F = 2A。

    返す ``dict``: ``f``、``normal`` (3,)、``center`` (3,)、``residual_rms``、``n_points``、``n_used``、``n_excluded``。

    **Raises** ``ValueError``: 点が (N, 3) でない・10 点未満・非有限、共線(法線が定まらない)、
    ``exclude_fraction`` が [0, 0.05] の外。
    """
    op = "plane_flatness_error"
    P = _points(points, "points", op, 10)
    frac = _exclude(exclude_fraction, op)
    try:
        Pk, (c, n, d), k = _with_exclusion(P, _plane_lsq, frac)
    except ValueError as e:
        raise ValueError("%s: %s" % (op, e)) from None
    return {"f": float(d.max() - d.min()), "normal": n, "center": c,
            "residual_rms": float(np.sqrt(np.mean(d ** 2))), "n_points": int(len(P)),
            "n_used": int(len(Pk)), "n_excluded": int(k)}


def _expected_range_of_normal(n):
    """正規標本 n 個の範囲の期待値 d2(n)(Tippett 1925 の積分を数値で)。

    Expected range of n i.i.d. standard normals, d2(n) = ∫ [1 − Φ(x)^n − (1 − Φ(x))^n] dx,
    evaluated by the trapezoid rule on [-12, 12] (error < 1e-9 for n <= 1e6). Used as the
    closed-form expectation of PF / F under pure Gaussian noise. Not an op (helper)."""
    n = int(n)
    if n < 2:
        raise ValueError("_expected_range_of_normal: n must be >= 2 (got %d)" % n)
    x = np.linspace(-12.0, 12.0, 240001)
    Phi = 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))
    f = 1.0 - Phi ** n - (1.0 - Phi) ** n
    return float(np.trapezoid(f, x) if hasattr(np, "trapezoid") else np.trapz(f, x))


# =========================================================================== #
# 試験体の配置 / artefact layout in the measuring volume
# =========================================================================== #
def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _rot_axis(axis, ang):
    a = _unit(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def acceptance_layout(volume_mm=(400.0, 300.0, 300.0), center_mm=(0.0, 0.0, 800.0), sphere_diameter_mm=25.0,
                      bar_length_mm=None, plane_size_mm=(300.0, 150.0), plane_tilt_deg=25.0):
    """測定体積の中に試験体(探針の球 1・ダンベル 7 姿勢・平面 7 姿勢)を置く配置を作る(``table``)。

    Place the artefacts in the measuring volume: one probing sphere at the centre, a ball bar in 7
    orientations and a flat in 7 orientations. Coordinates are the sensor frame (x right, y down,
    z along the optical axis, mm), the volume a box of ``volume_mm`` centred on ``center_mm``.

    ダンベルの 7 姿勢 = 空間対角線 4 本 + 面の対角線 3 本(xy・xz・yz)、どれも体積の中心を通る。光軸(z)に
    平行な姿勢は手前の球が奥の球を隠すので取らない。平面の 7 姿勢 = 正対 1 + x 軸・y 軸まわりに ±``plane_tilt_deg``
    の 4 + 対角の軸まわり ±tilt の 2。★これは **Fullseye の約束** で、VDI/VDE 2634 の図の写しではない
    (考え方 = 体積を対角に貫く長さで尺度の誤差を見る、に沿っただけ)。
    This 7+7 convention is Fullseye's own, modelled on the guideline's idea (span the volume
    diagonally so a scale error shows up); it is not a copy of the normative figure.

    ``bar_length_mm`` の既定 = 7 方向のうち最も短い「体積を貫く長さ」の 0.8 倍から球の直径を引いた値。

    返す ``dict``: ``kind`` = ``"acceptance_layout"``、``volume_mm``、``center_mm``、``sphere_diameter_mm``、
    ``bar_length_mm``、``probe``(``[{"center", "diameter"}]``)、``bars``(7 個の
    ``{"name", "center_a", "center_b", "length", "diameter", "direction"}``)、
    ``planes``(7 個の ``{"name", "center", "normal", "u", "v", "size"}``)。

    **Raises** ``ValueError``: 寸法が正でない・非有限、``center_mm`` の z が体積の半分以下(センサの後ろに入る)、
    球やダンベルや平面が体積からはみ出す、平面の傾きが [0, 60] 度の外。
    """
    op = "acceptance_layout"
    vol = _vec3(volume_mm, "volume_mm", op)
    if np.any(vol <= 0):
        raise ValueError("%s: volume_mm must be positive (got %s)" % (op, vol))
    c0 = _vec3(center_mm, "center_mm", op)
    if c0[2] - vol[2] / 2.0 <= 0:
        raise ValueError("%s: the volume reaches behind the sensor (center z %g <= half depth %g)"
                         % (op, c0[2], vol[2] / 2.0))
    D = _num(sphere_diameter_mm, "sphere_diameter_mm", op, lo=0.0, lo_open=True)
    if D >= 0.5 * vol.min():
        raise ValueError("%s: sphere diameter %g does not fit the volume %s" % (op, D, vol))
    tilt = math.radians(_num(plane_tilt_deg, "plane_tilt_deg", op, lo=0.0, hi=60.0))
    ps = np.asarray(plane_size_mm, float).reshape(-1)
    if ps.size != 2 or not np.isfinite(ps).all() or np.any(ps <= 0):
        raise ValueError("%s: plane_size_mm must be 2 positive numbers (got %r)" % (op, plane_size_mm))
    h = vol / 2.0
    dirs = [("space_diag_1", (h[0], h[1], h[2])), ("space_diag_2", (-h[0], h[1], h[2])),
            ("space_diag_3", (h[0], -h[1], h[2])), ("space_diag_4", (-h[0], -h[1], h[2])),
            ("face_diag_xy", (h[0], h[1], 0.0)), ("face_diag_xz", (h[0], 0.0, h[2])),
            ("face_diag_yz", (0.0, h[1], h[2]))]
    # 方向 d に沿って中心から体積の面までの半分の長さ / half extent of the box along d
    spans = []
    for _, d in dirs:
        u = _unit(d)
        with np.errstate(divide="ignore"):
            t = np.min(np.where(np.abs(u) > 1e-12, h / np.abs(u), np.inf))
        spans.append(2.0 * t)
    if bar_length_mm is None:
        L = 0.8 * min(spans) - D
    else:
        L = _num(bar_length_mm, "bar_length_mm", op, lo=0.0, lo_open=True)
    bars = []
    for (name, d), span in zip(dirs, spans):
        u = _unit(d)
        if L + D > span + 1e-9:
            raise ValueError("%s: ball bar %g + sphere %g does not fit along %s (span %.1f)"
                             % (op, L, D, name, span))
        bars.append({"name": name, "center_a": c0 - 0.5 * L * u, "center_b": c0 + 0.5 * L * u,
                     "length": float(L), "diameter": D, "direction": u})
    planes = []
    axes = [None, (1, 0, 0), (1, 0, 0), (0, 1, 0), (0, 1, 0), (1, 1, 0), (1, -1, 0)]
    signs = [0, 1, -1, 1, -1, 1, 1]
    names = ["frontal", "tilt_x_pos", "tilt_x_neg", "tilt_y_pos", "tilt_y_neg", "tilt_diag_1", "tilt_diag_2"]
    for name, ax, sg in zip(names, axes, signs):
        Rm = np.eye(3) if ax is None else _rot_axis(ax, sg * tilt)
        u, v, n = Rm[:, 0], Rm[:, 1], -Rm[:, 2]            # 法線はセンサの側を向く / normal faces the sensor
        corners = [c0 + a * ps[0] / 2 * u + b * ps[1] / 2 * v for a in (-1, 1) for b in (-1, 1)]
        if any(np.any(np.abs(p - c0) > h + 1e-9) for p in corners):
            raise ValueError("%s: plane %s (%gx%g, tilt %.1f deg) leaves the volume"
                             % (op, name, ps[0], ps[1], math.degrees(tilt)))
        planes.append({"name": name, "center": c0.copy(), "normal": n, "u": u, "v": v,
                       "size": (float(ps[0]), float(ps[1]))})
    return {"kind": "acceptance_layout", "volume_mm": vol, "center_mm": c0, "sphere_diameter_mm": D,
            "bar_length_mm": float(L), "probe": [{"center": c0.copy(), "diameter": D}],
            "bars": bars, "planes": planes}


# =========================================================================== #
# シミュレーションのセンサ / simulated sensors
# =========================================================================== #
def _sensor(s, op):
    """センサの表を既定値で埋めて検査する。Fill defaults and validate a sensor table."""
    if not isinstance(s, dict):
        raise ValueError("%s: sensor must be a dict (got %s)" % (op, type(s).__name__))
    if "kind" not in s:
        # 空の表を「全部既定」と黙って読まない —— どのセンサかは呼び手が言う(fail-closed)
        raise ValueError("%s: sensor must name its kind (one of %s)" % (op, _SENSOR_KINDS))
    out = {"kind": "ideal", "shape": (480, 640), "fx": 900.0, "fy": 900.0, "cx": None, "cy": None,
           "fx_rel_error": 0.0, "fy_rel_error": 0.0, "cx_error_px": 0.0, "cy_error_px": 0.0,
           "range_scale": 1.0, "range_offset_mm": 0.0,
           # triangulation
           "baseline_mm": 100.0, "disparity_sigma_px": 0.05,
           # itof
           "frequency_hz": 50e6, "signal_electrons": 1e7, "ambient_electrons": 0.0, "read_noise_e": 0.0,
           "demod_contrast": 0.5, "supersample": 1, "sphere_reflectivity": 1.0, "plane_reflectivity": 1.0,
           "background_mm": 1500.0, "background_reflectivity": 0.5,
           "multipath_amplitude": 0.0, "multipath_extra_mm": 50.0, "flying_pixel_filter": True,
           "noise": True}
    unknown = set(s) - set(out) - {"name"}
    if unknown:
        raise ValueError("%s: unknown sensor keys %s" % (op, sorted(unknown)))
    out.update(s)
    if out["kind"] not in _SENSOR_KINDS:
        raise ValueError("%s: sensor kind must be one of %s (got %r)" % (op, _SENSOR_KINDS, out["kind"]))
    sh = tuple(int(x) for x in out["shape"])
    if len(sh) != 2 or min(sh) < 8 or sh[0] * sh[1] > 4_000_000:
        raise ValueError("%s: shape must be (H, W) with 8 <= H, W and H*W <= 4e6 (got %r)" % (op, out["shape"]))
    out["shape"] = sh
    for k in ("fx", "fy"):
        out[k] = _num(out[k], k, op, lo=0.0, lo_open=True)
    out["cx"] = (sh[1] - 1) / 2.0 if out["cx"] is None else _num(out["cx"], "cx", op)
    out["cy"] = (sh[0] - 1) / 2.0 if out["cy"] is None else _num(out["cy"], "cy", op)
    for k in ("fx_rel_error", "fy_rel_error"):
        out[k] = _num(out[k], k, op, lo=-0.5, hi=0.5)
    for k in ("cx_error_px", "cy_error_px", "range_offset_mm"):
        out[k] = _num(out[k], k, op)
    out["range_scale"] = _num(out["range_scale"], "range_scale", op, lo=0.0, lo_open=True)
    out["baseline_mm"] = _num(out["baseline_mm"], "baseline_mm", op, lo=0.0, lo_open=True)
    out["disparity_sigma_px"] = _num(out["disparity_sigma_px"], "disparity_sigma_px", op, lo=0.0)
    for k in ("sphere_reflectivity", "plane_reflectivity", "background_reflectivity", "multipath_amplitude",
              "ambient_electrons", "read_noise_e", "signal_electrons"):
        out[k] = _num(out[k], k, op, lo=0.0)
    out["background_mm"] = _num(out["background_mm"], "background_mm", op, lo=0.0, lo_open=True)
    out["multipath_extra_mm"] = _num(out["multipath_extra_mm"], "multipath_extra_mm", op, lo=0.0, lo_open=True)
    out["frequency_hz"] = _num(out["frequency_hz"], "frequency_hz", op, lo=0.0, hi=2e9, lo_open=True)
    out["demod_contrast"] = _num(out["demod_contrast"], "demod_contrast", op, lo=0.0, hi=1.0, lo_open=True)
    ss = out["supersample"]
    if isinstance(ss, bool) or not isinstance(ss, (int, np.integer)) or not 1 <= int(ss) <= 8:
        raise ValueError("%s: supersample must be an integer in [1, 8] (got %r)" % (op, ss))
    out["supersample"] = int(ss)
    for k in ("noise", "flying_pixel_filter"):
        if not isinstance(out[k], (bool, np.bool_)):
            raise ValueError("%s: %s must be a bool (got %r)" % (op, k, out[k]))
    if out["kind"] == "itof":
        amb = 299_792_458.0 / (2.0 * out["frequency_hz"]) * 1e3
        if out["background_mm"] + out["multipath_extra_mm"] >= amb:
            raise ValueError("%s: background %g mm + multipath %g mm reaches the iToF ambiguity range %.0f mm "
                             "(lower frequency_hz)" % (op, out["background_mm"], out["multipath_extra_mm"], amb))
    return out


def _artifact(a, op):
    """1 つの試験体を (kind, 形状) に直す。Normalize one artefact to a list of primitives."""
    if not isinstance(a, dict):
        raise ValueError("%s: artifact must be a dict from acceptance_layout (got %s)" % (op, type(a).__name__))
    if "center_a" in a:                                   # ball bar
        r = 0.5 * _num(a["diameter"], "diameter", op, lo=0.0, lo_open=True)
        return [("sphere", _vec3(a["center_a"], "center_a", op), r),
                ("sphere", _vec3(a["center_b"], "center_b", op), r)]
    if "normal" in a:                                     # plane
        size = np.asarray(a["size"], float).reshape(-1)
        if size.size != 2 or np.any(size <= 0):
            raise ValueError("%s: plane size must be 2 positive numbers" % op)
        return [("plane", _vec3(a["center"], "center", op), _unit(_vec3(a["normal"], "normal", op)),
                 _unit(_vec3(a["u"], "u", op)), _unit(_vec3(a["v"], "v", op)), size)]
    if "diameter" in a and "center" in a:                 # probing sphere
        return [("sphere", _vec3(a["center"], "center", op),
                 0.5 * _num(a["diameter"], "diameter", op, lo=0.0, lo_open=True))]
    raise ValueError("%s: artifact must be a probe sphere, a ball bar or a plane from acceptance_layout" % op)


def _rays(S, s):
    """真の K による画素(細かい標本)の視線。Unit rays through (sub)pixel centres with the TRUE K."""
    H, W = S["shape"]
    rr = (np.arange(H * s) + 0.5) / s - 0.5
    cc = (np.arange(W * s) + 0.5) / s - 0.5
    C, R = np.meshgrid(cc, rr)
    d = np.stack([(C - S["cx"]) / S["fx"], (R - S["cy"]) / S["fy"], np.ones_like(C)], axis=-1)
    return d / np.linalg.norm(d, axis=-1, keepdims=True), R, C


def _cast(prims, d):
    """光線と試験体の解析的な交点(最も近い当たり)。Analytic nearest hit: range and primitive label (-1 = miss)."""
    t = np.full(d.shape[:2], np.inf)
    lab = np.full(d.shape[:2], -1, dtype=int)
    for i, p in enumerate(prims):
        if p[0] == "sphere":
            c, r = p[1], p[2]
            b = d @ c
            disc = b * b - (c @ c - r * r)
            ok = disc >= 0
            ti = np.where(ok, b - np.sqrt(np.where(ok, disc, 0.0)), np.inf)
            ti = np.where(ti > 0, ti, np.inf)
        else:
            c, n, u, v, size = p[1], p[2], p[3], p[4], p[5]
            den = d @ n
            with np.errstate(divide="ignore", invalid="ignore"):
                ti = np.where(np.abs(den) > 1e-12, (c @ n) / den, np.inf)
            X = d * ti[..., None] - c
            inside = (np.abs(X @ u) <= size[0] / 2) & (np.abs(X @ v) <= size[1] / 2) & (ti > 0)
            ti = np.where(inside, ti, np.inf)
        closer = ti < t
        t = np.where(closer, ti, t)
        lab = np.where(closer, i, lab)
    return t, lab


def _block(a, s):
    if s == 1:
        return a
    H, W = a.shape[0] // s, a.shape[1] // s
    return a.reshape(H, s, W, s).mean(axis=(1, 3))


def _scan(S, prims, seed):
    """センサで試験体を撮り、画素ごとの点 (H, W, 3) と試験体の番号を返す。Scan -> organized points + labels."""
    s = S["supersample"] if S["kind"] == "itof" else 1
    d, _, _ = _rays(S, s)
    t, lab = _cast(prims, d)
    H, W = S["shape"]
    if s > 1:                                             # 画素の多数決の番号 / majority label per pixel
        L = lab.reshape(H, s, W, s).transpose(0, 2, 1, 3).reshape(H, W, s * s)
        votes = np.stack([(L == i).sum(-1) for i in range(-1, len(prims))], axis=-1)
        plab = votes.argmax(-1) - 1
    else:
        plab = lab
    rng = np.random.default_rng(seed)
    if S["kind"] == "itof":
        import itof as _itof
        rho_obj = np.array([S["sphere_reflectivity"] if p[0] == "sphere" else S["plane_reflectivity"]
                            for p in prims] + [S["background_reflectivity"]])
        rng_m = np.where(np.isfinite(t), t, S["background_mm"])
        rho = rho_obj[np.where(lab >= 0, lab, len(prims))]
        kw = {}
        if S["multipath_amplitude"] > 0:
            hit = np.isfinite(t)
            kw = {"paths_depth": ((rng_m + S["multipath_extra_mm"]) * 1e-3)[None],
                  "paths_amplitude": (np.where(hit, S["multipath_amplitude"] * rho, 0.0))[None]}
        raw = _itof.itof_capture(rng_m * 1e-3, rho, frequencies_hz=(S["frequency_hz"],),
                                 signal_electrons=S["signal_electrons"], demod_contrast=S["demod_contrast"],
                                 ambient_electrons=S["ambient_electrons"], read_noise_e=S["read_noise_e"],
                                 supersample=s, noise=bool(S["noise"]),
                                 seed=int(rng.integers(0, 2 ** 31 - 1)), **kw)
        ph = _itof.itof_phase_amplitude(raw)
        meas = ph["wrapped_depth"][0] * 1e3               # 視線方向の距離 [mm] / measured range
        valid = (plab >= 0) & (ph["amplitude"][0] > 0)
        if S["flying_pixel_filter"] and s > 1:
            # 既存の itof_flying_pixel_mask で縁の混合を落とす(実機の前処理にあたる)/ drop mixed edge pixels
            fly = _itof.itof_flying_pixel_mask(ph["wrapped_depth"][0], threshold_m=0.01, radius=2,
                                               depth_sigma=ph["depth_sigma"][0])
            valid = valid & (fly < 0.5)
        rad = True
    else:
        dz = d[..., 2]
        z = np.where(np.isfinite(t), t * dz, np.nan)      # 光軸方向の奥行き / depth along z
        if S["kind"] == "triangulation" and S["noise"]:
            sig = z ** 2 * S["disparity_sigma_px"] / (S["fx"] * S["baseline_mm"])
            z = z + rng.standard_normal(z.shape) * np.nan_to_num(sig)
        meas = z
        valid = plab >= 0
        rad = False
    meas = S["range_scale"] * meas + S["range_offset_mm"]
    # センサが「信じている」K で逆投影する(校正の誤差はここに入る)/ back-project with the sensor's believed K
    fx = S["fx"] * (1 + S["fx_rel_error"])
    fy = S["fy"] * (1 + S["fy_rel_error"])
    cx = S["cx"] + S["cx_error_px"]
    cy = S["cy"] + S["cy_error_px"]
    C, R = np.meshgrid(np.arange(W, dtype=float), np.arange(H, dtype=float))
    ray = np.stack([(C - cx) / fx, (R - cy) / fy, np.ones_like(C)], axis=-1)
    if rad:
        ray = ray / np.linalg.norm(ray, axis=-1, keepdims=True)
    pts = ray * np.where(valid, meas, np.nan)[..., None]
    valid = valid & np.isfinite(pts).all(-1)
    return pts, np.where(valid, plab, -1)


def acceptance_scan(sensor, artifact, seed=0):
    """シミュレーションのセンサで 1 つの試験体を撮り、その点群 ``(N, 3)`` を返す(``points``)。

    Scan one artefact (probe sphere, ball bar or plane from :func:`acceptance_layout`) with a simulated
    sensor and return its points (N, 3) in the sensor frame, mm. For a ball bar the points of both
    spheres are concatenated in the order a, b (use :func:`virtual_acceptance_test` for the split).

    センサ(``sensor`` の ``kind``):
      * ``"ideal"`` —— 真の視線距離をそのまま返す(雑音なし)。往復の検算用。
      * ``"triangulation"`` —— 奥行き z に正規雑音 ``σ_z = z²·σ_d / (f·b)``(``z = f·b/d`` の誤差伝播、
        ``disparity_sigma_px`` = σ_d、``baseline_mm`` = b)。構造化光・ステレオの雑音則の代表で、縞を描いて
        復号するわけではない(限界)。
      * ``"itof"`` —— 既存の :func:`itof.itof_capture` → :func:`itof.itof_phase_amplitude` で 4 位相の生信号から
        距離を出す(ショット雑音・反射率・背景光・``supersample`` による縁の混合 = フライングピクセル・
        ``multipath_amplitude`` の 2 経路の多重反射)。多重反射は「全画素に一様な第 2 経路
        (余分な経路長 ``multipath_extra_mm``)」の最も粗いモデル。
    校正の誤差は逆投影に入る: ``fx_rel_error``・``fy_rel_error``(相対)、``cx_error_px``・``cy_error_px``、
    距離の尺度 ``range_scale`` とオフセット ``range_offset_mm``。真値は場面の解析解(光線と球・平面の交点)。

    **Raises** ``ValueError``: センサの表に ``kind`` が無い(空の表は既定値で黙って走らせない)・鍵が未知・値が範囲外、試験体が配置の形でない、点が 10 点未満しか写らない。
    """
    op = "acceptance_scan"
    S = _sensor(sensor, op)
    prims = _artifact(artifact, op)
    pts, lab = _scan(S, prims, seed)
    P = pts[lab >= 0]
    if len(P) < 10:
        raise ValueError("%s: only %d points of the artefact are visible (move it into the field of view)"
                         % (op, len(P)))
    order = np.argsort(lab[lab >= 0], kind="stable")
    return P[order]


# =========================================================================== #
# 仮想受入試験 / virtual acceptance test
# =========================================================================== #
_MPE_KEYS = ("pf", "ps", "sd", "f")


def acceptance_verdict(results, mpe):
    """評価量の表を MPE(最大許容誤差)と比べて合否を出す(``table``)。

    Compare acceptance results with maximum permissible errors. ``results`` holds lists (one value per
    position) under any of ``pf``, ``ps``, ``sd``, ``f`` (the shape :func:`virtual_acceptance_test`
    returns; measured values may be assembled by hand). ``mpe`` gives a positive limit per quantity.
    A quantity passes when ``max |value| <= mpe`` (PF and F are non-negative by definition).

    返す ``dict``: ``passed``(全体)、``by_quantity``(量ごとに ``worst``・``worst_index``・``mpe``・``ratio``・
    ``passed``)、``decided_by``(``ratio`` が最大の量 = 合否を決めた量)、``max_ratio``。
    ★MPE の値は規格ではなく**メーカーの仕様**が決める(この op は数字を持たない)。

    **Raises** ``ValueError``: ``results``・``mpe`` が dict でない、共通の量が 1 つも無い、値が空・非有限、
    MPE が正でない、未知の量の名前。
    """
    op = "acceptance_verdict"
    if not isinstance(results, dict) or not isinstance(mpe, dict):
        raise ValueError("%s: results and mpe must be dicts" % op)
    bad = set(mpe) - set(_MPE_KEYS)
    if bad:
        raise ValueError("%s: unknown MPE quantities %s (use %s)" % (op, sorted(bad), _MPE_KEYS))
    keys = [k for k in _MPE_KEYS if k in mpe and k in results]
    if not keys:
        raise ValueError("%s: no quantity is present in both results and mpe" % op)
    by = {}
    for k in keys:
        v = np.asarray(results[k], float).reshape(-1)
        if v.size == 0 or not np.isfinite(v).all():
            raise ValueError("%s: results[%r] must be a non-empty list of finite numbers" % (op, k))
        m = _num(mpe[k], "mpe[%r]" % k, op, lo=0.0, lo_open=True)
        i = int(np.argmax(np.abs(v)))
        w = float(v[i])
        by[k] = {"worst": w, "worst_index": i, "mpe": m, "ratio": abs(w) / m, "passed": bool(abs(w) <= m)}
    dec = max(keys, key=lambda k: by[k]["ratio"])
    return {"passed": all(b["passed"] for b in by.values()), "by_quantity": by, "decided_by": dec,
            "max_ratio": by[dec]["ratio"]}


def virtual_acceptance_test(sensor, layout=None, mpe=None, exclude_fraction=DEFAULT_EXCLUDE, seed=0):
    """シミュレーションのセンサで試験体の全配置を撮り、PF・PS・SD・F と合否を返す(``table``)。

    Run the whole virtual acceptance test: scan the probing sphere, the ball bar in its 7 positions and the
    flat in its 7 positions with the simulated ``sensor`` (see :func:`acceptance_scan`), evaluate them with
    the same ops a real point cloud would go through, and (if ``mpe`` is given) the verdict.

    返す ``dict``: ``pf``・``ps``(探針の球の位置ごと)、``sd``(ダンベル 7 姿勢)、``f``(平面 7 姿勢)、
    ``probe``・``bars``・``planes``(各評価 op の返り)、``verdict``(``mpe`` があれば :func:`acceptance_verdict`)、
    ``layout``、``sensor``(既定値で埋めた写し)。ダンベルの 2 球は場面の番号で分ける(実機では作業者が
    範囲を切る作業にあたる)。

    **Raises** ``ValueError``: センサや配置が不正、どれかの試験体が 10 点未満しか写らない。
    """
    op = "virtual_acceptance_test"
    S = _sensor(sensor, op)
    lay = acceptance_layout() if layout is None else layout
    if not isinstance(lay, dict) or lay.get("kind") != "acceptance_layout":
        raise ValueError("%s: layout must come from acceptance_layout" % op)
    k = 0
    probe, bars, planes = [], [], []
    for a in lay["probe"]:
        P = acceptance_scan(S, a, seed=seed + k)
        k += 1
        probe.append(sphere_probing_error(P, a["diameter"], exclude_fraction))
    for a in lay["bars"]:
        pts, lab = _scan(S, _artifact(a, op), seed + k)
        k += 1
        Pa, Pb = pts[lab == 0], pts[lab == 1]
        if len(Pa) < 10 or len(Pb) < 10:
            raise ValueError("%s: ball bar %s is not visible (%d / %d points)" % (op, a["name"], len(Pa), len(Pb)))
        r = sphere_spacing_error(Pa, Pb, a["length"], exclude_fraction)
        r["name"] = a["name"]
        bars.append(r)
    for a in lay["planes"]:
        P = acceptance_scan(S, a, seed=seed + k)
        k += 1
        r = plane_flatness_error(P, exclude_fraction)
        r["name"] = a["name"]
        planes.append(r)
    out = {"pf": [p["pf"] for p in probe], "ps": [p["ps"] for p in probe], "sd": [b["sd"] for b in bars],
           "f": [p["f"] for p in planes], "probe": probe, "bars": bars, "planes": planes,
           "layout": lay, "sensor": {kk: v for kk, v in S.items()}}
    if mpe is not None:
        out["verdict"] = acceptance_verdict(out, mpe)
    return out


#: 誤差の要因を「入れない」ときの値(理想の基準)。The value of each factor when it is switched off.
_IDEAL = {"noise": False, "fx_rel_error": 0.0, "fy_rel_error": 0.0, "cx_error_px": 0.0, "cy_error_px": 0.0,
          "range_scale": 1.0, "range_offset_mm": 0.0, "multipath_amplitude": 0.0, "supersample": 1}


def acceptance_error_budget(sensor, factors, mpe, layout=None, exclude_fraction=DEFAULT_EXCLUDE, n_repeat=1, seed=0):
    """誤差の要因を 1 つずつ入れて仮想受入試験を回し、どの要因が合否を決めるかを返す(``table``)。

    One-factor-at-a-time error budget of the virtual acceptance test. The baseline is ``sensor`` with every
    error source switched off (noise off, calibration errors 0, range scale 1, multipath 0, supersample 1).
    ``factors`` maps a name to the sensor keys that switch that factor on, e.g.
    ``{"noise": {"noise": True}, "fx 0.2 %": {"fx_rel_error": 0.002}, "multipath": {"multipath_amplitude": 0.05}}``.
    Each factor is run alone on the baseline, then all together ("all"). With noise, ``n_repeat`` seeds are
    run and the worst of the per-run maxima is kept (the verdict must hold for every run).

    返す ``dict``: ``baseline``・``all``・``factors``(名前ごとに ``pf``・``ps``・``sd``・``f`` の最悪値と
    ``verdict``)、``decisive``(単独で MPE を超えた要因の名前、比の大きい順)、``ranking``(全要因の比の大きい順と
    その量)、``interaction``(「all」の比 − 単独の比の最大。正なら要因が重なって初めて落ちる)。
    基準(全部切った)の評価量は解析解の往復だけなので ≈ 0 になる(門で確かめる)。

    **Raises** ``ValueError``: ``factors`` が空・dict でない、未知のセンサの鍵、``n_repeat`` が 1〜50 の外、
    ``mpe`` が不正(:func:`acceptance_verdict`)。
    """
    op = "acceptance_error_budget"
    S = _sensor(sensor, op)
    if not isinstance(factors, dict) or not factors:
        raise ValueError("%s: factors must be a non-empty dict name -> sensor overrides" % op)
    if isinstance(n_repeat, bool) or not isinstance(n_repeat, (int, np.integer)) or not 1 <= int(n_repeat) <= 50:
        raise ValueError("%s: n_repeat must be an integer in [1, 50] (got %r)" % (op, n_repeat))
    base = dict(S)
    base.update(_IDEAL)
    for name, ov in factors.items():
        if not isinstance(ov, dict) or not ov:
            raise ValueError("%s: factor %r must be a non-empty dict of sensor keys" % (op, name))
        _sensor({**{k: v for k, v in base.items()}, **ov}, op)          # 鍵と値の検査 / validate keys

    def run(over):
        s_ = dict(base)
        s_.update(over)
        reps = int(n_repeat) if s_.get("noise") else 1
        worst = {q: 0.0 for q in _MPE_KEYS}
        for r in range(reps):
            res = virtual_acceptance_test(s_, layout, None, exclude_fraction, seed=seed + 1000 * r)
            for q in _MPE_KEYS:
                v = np.asarray(res[q], float)
                i = int(np.argmax(np.abs(v)))
                if abs(v[i]) > abs(worst[q]):
                    worst[q] = float(v[i])
        row = dict(worst)
        row["verdict"] = acceptance_verdict({q: [worst[q]] for q in _MPE_KEYS}, mpe)
        return row

    out_f = {name: run(ov) for name, ov in factors.items()}
    allov = {}
    for ov in factors.values():
        allov.update(ov)
    base_row = run({})
    all_row = run(allov)
    rank = sorted(((name, r["verdict"]["max_ratio"], r["verdict"]["decided_by"]) for name, r in out_f.items()),
                  key=lambda x: -x[1])
    decisive = [n for n, ratio, _ in rank if ratio > 1.0]
    inter = all_row["verdict"]["max_ratio"] - (rank[0][1] if rank else 0.0)
    return {"baseline": base_row, "all": all_row, "factors": out_f, "decisive": decisive,
            "ranking": [{"factor": n, "max_ratio": r, "quantity": q} for n, r, q in rank],
            "interaction": float(inter), "n_repeat": int(n_repeat)}
