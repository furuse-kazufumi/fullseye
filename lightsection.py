# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Light-section (laser triangulation) metrology — line centres, light-plane calibration,
triangulation and scanning, and the speckle floor of the height (numpy + scipy).

光切断(シート光・レーザー三角測量)の族。**土台は標準の手順**、その上に Fullseye だけの層
(スペックルが決める高さの不確かさの床を、閉形式とコヒーレント結像のシミュの両方で出す)を載せる。

土台(並びは測定の順)/ The base layer:

  * :func:`laser_line_center_centroid` / :func:`laser_line_center_gauss` /
    :func:`laser_line_center_steger` — 光条の中心を列ごとにサブピクセルで取る 3 つの変種
    (輝度の重心 / 対数放物線 = ガウスの当てはめ / Steger 1998 の Hessian による線の中心)。
    返りは ``kind="laser_line_centers"`` の表(``col`` / ``row`` / ``valid`` / ``peak``)。
  * :func:`light_section_rig` — 既知の幾何の装置(ピンホールカメラ ``K``・姿勢 ``R, t``・
    光面)。世界座標は X = 光条に沿う向き、Y = 走査の向き、Z = 上。光面は世界の ``Y = 0``。
  * :func:`light_section_targets` — 既知の高さの水平面(基準面・段差・ゲージブロック)を
    カメラ座標の平面の式に直した表(校正の入力)。
  * :func:`light_section_render` — 断面 ``(x, h)`` を光面とカメラで撮った光条の画像
    (真値つきの合成。順方向は :func:`camera.project_points`)。
  * :func:`light_plane_calibrate` — 既知の平面に当たった光条の中心から光面の式
    ``n · X = d``(カメラ座標)を全最小二乗(SVD)で当てる。
  * :func:`light_section_profile` — 中心 → 視線と光面の交点 → 3-D 点(``points``)。
  * :func:`light_section_scan` / :func:`light_section_height_map` — 走査(1 枚ごとに
    部品が ``step_mm`` だけ動く)で点群 / 高さ地図(``depth``、測れない所は NaN)。

Fullseye だけの層 / The layer only Fullseye has:

  * :func:`light_section_speckle_floor` — :mod:`coherent` の ``laser_line_coherent`` で
    粗面のスペックル込みの光条を描き、上の中心抽出で高さを測って標準偏差を取る(シミュ)。
    並べて閉形式 ``δz = C λ / (2π sin u_obs sin θ)``(Dorsch, Häusler & Herrmann 1994)を返す。
  * :func:`light_section_uncertainty_budget` — 不確かさの成分(スペックル・読み出し雑音と
    量子化・校正)を GUM の表(``source`` / ``u`` / ``sensitivity`` / ``dof``)で返す。
    そのまま :func:`spc.gum_propagate` / :func:`spc.gum_expanded` に流せる。
  * :func:`light_section_floor_sweep` — 1 つの量(波長・開口・三角測量角・独立パターン数・
    雑音)を掃引し、閉形式とシミュの δz と、どの成分が支配的かを返す。

真値(``tests/test_lightsection.py`` の門)/ Ground truth:
  * ガウスの対数は 2 次式(定理): 点標本のガウス光条で :func:`laser_line_center_gauss` は
    サブピクセルの中心を 1e-9 画素で返す。
  * Steger の 1 ステップ(Newton 法)の偏り: ガウスの断面に対し、画素中心からのずれ δ で
    誤差 ``−δ³ / (σ² − δ²)``(σ² = 光条の σ² + 平滑化の σ²)。閉形式と比べる。
  * 順方向(:func:`camera.project_points` で描く)と逆方向(視線と光面の交点)は別の経路。
    描いた断面を中心 → 三角測量で戻し、真の高さと比べる。
  * 光面の校正: 1 つの高さだけでは点が 1 直線に並び面が決まらない(fail-closed で拒む)。
    2 つ以上の高さで真の面の法線と 1e-9 で一致(雑音なし)。
  * スペックルの床: 閉形式とシミュの比、λ・sin u・sin θ の log-log の傾き(+1・−1・−1)。
  * 読み出し雑音の項: スペックルの無い滑らかな面(``roughness_rad=0``)に雑音だけを
    足したシミュの標準偏差と、線形化した重心の分散の閉形式。

★正直に書いておくこと / Honest limits:
  * Dorsch らの原論文(Appl. Opt. 33(7):1306, 1994)は本文を読めていない(抄録のみ)。
    式 ``δz = (C/2π) · λ / (sin u_obs · sin θ)`` は同じ研究室の公開論文(Ettl, Arold, Yang &
    Häusler, "Hand-guided 3D surface acquisition by combining simple light sectioning with
    real-time algorithms", arXiv:1401.1946, 2014)が Dorsch ら 1994 を引いて書いている形。
  * 光条の長さ ``L`` に沿って中心を平均すると誤差は約 ``√(w/L)`` で下がる(:mod:`coherent`
    の実測。Dorsch の「スポットの大きさによらない」は L ≈ w の場合)。予算の op はこの
    スケーリングを**実測の規則**として使い、閉形式とは書かない。
  * :func:`light_section_render` は光条の太さを画像上で一定(``line_sigma_px``)にする。
    前縮み・デフォーカス・自己遮蔽(段差の影)・多重反射は入れていない。
    断面の像が列について単調でない(折り返す)ときは拒む。
  * :func:`light_section_height_map` の格子は **(フレーム, 画像の列)** で、世界の X に
    等間隔ではない(高さで X と列の対応が少し動く)。等間隔の格子が要るなら
    :func:`light_section_scan` の点群を既存の点群の op で格子に落とす。

出典 / References: C. Steger, "An unbiased detector of curvilinear structures", IEEE TPAMI
20(2):113–125, 1998 / R. G. Dorsch, G. Häusler, J. M. Herrmann, "Laser triangulation:
fundamental uncertainty in distance measurement", Appl. Opt. 33(7):1306–1314, 1994 /
S. Ettl, O. Arold, Z. Yang, G. Häusler, arXiv:1401.1946, 2014 / H. Guo, "A simple algorithm
for fitting a Gaussian function", IEEE Signal Process. Mag. 28(5):134–137, 2011 /
R. Hartley, A. Zisserman, *Multiple View Geometry*, 2nd ed., 2004(視線と平面の交点)/
JCGM 100:2008 (GUM)。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

import camera as _camera
import coherent as _coherent

__all__ = [
    "laser_line_center_centroid",
    "laser_line_center_gauss",
    "laser_line_center_steger",
    "light_section_rig",
    "light_section_targets",
    "light_section_render",
    "light_plane_calibrate",
    "light_section_profile",
    "light_section_scan",
    "light_section_height_map",
    "light_section_speckle_floor",
    "light_section_uncertainty_budget",
    "light_section_floor_sweep",
]

#: 画像 1 枚の画素数の上限(作業領域を確保する前に拒む)。
MAX_PIXELS = 1 << 25
#: 走査の枚数の上限。
MAX_FRAMES = 1 << 14
#: 掃引できる量。
SWEEP_PARAMETERS = ("wavelength_um", "sin_u_obs", "sin_theta", "n_patterns", "noise_rel")

_CENTERS = "laser_line_centers"
_RIG = "light_section_rig"
_TARGETS = "light_section_targets"


# --------------------------------------------------------------------------- #
# 入力の検証(fail-closed)
# --------------------------------------------------------------------------- #
def _num(v, name, op, lo=None, hi=None, lo_open=True, hi_open=False):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    v = float(v)
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and (v < lo or (lo_open and v == lo)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and (v > hi or (hi_open and v == hi)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, "<" if hi_open else "<=", hi, v))
    return v


def _int(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if not lo <= v <= hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


def _image(a, op, name="image"):
    if a is None:
        raise ValueError("%s: %s is None" % (op, name))
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked entries" % (op, name))
    arr = np.asarray(a)
    if arr.dtype.kind not in "iuf":
        raise ValueError("%s: %s has dtype %r — expected real numbers" % (op, name, str(arr.dtype)))
    if arr.ndim != 2:
        raise ValueError("%s: %s must be 2-D (rows, cols), got shape %s" % (op, name, arr.shape))
    if min(arr.shape) < 3:
        raise ValueError("%s: %s must be at least 3x3, got %s" % (op, name, arr.shape))
    if arr.size > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels, over the %d cap" % (op, name, arr.size, MAX_PIXELS))
    arr = arr.astype(np.float64)
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has non-finite values (nan/inf)" % (op, name))
    return arr


def _matrix_k(K, op):
    Km = np.asarray(K, dtype=np.float64)
    if Km.shape != (3, 3) or not np.isfinite(Km).all():
        raise ValueError("%s: the camera matrix K must be a finite 3x3 array, got %s" % (op, Km.shape))
    if abs(Km[2, 0]) > 0 or abs(Km[2, 1]) > 0 or Km[2, 2] != 1.0 or Km[0, 0] <= 0 or Km[1, 1] <= 0:
        raise ValueError("%s: K must be [[fx, s, cx], [0, fy, cy], [0, 0, 1]] with fx, fy > 0" % op)
    return Km


def _vec3(v, name, op, unit=False):
    a = np.asarray(v, dtype=np.float64).reshape(-1)
    if a.size != 3 or not np.isfinite(a).all():
        raise ValueError("%s: %s must be 3 finite numbers, got %r" % (op, name, v))
    if unit:
        n = float(np.linalg.norm(a))
        if n < 1e-12:
            raise ValueError("%s: %s is the zero vector" % (op, name))
        a = a / n
    return a


def _rig(rig, op):
    if not isinstance(rig, dict) or rig.get("kind") != _RIG:
        raise ValueError("%s: expected a light-section rig table (kind=%r) from light_section_rig or "
                         "light_plane_calibrate, got %r" % (op, _RIG, type(rig).__name__ if not isinstance(rig, dict)
                                                            else rig.get("kind")))
    out = {"K": _matrix_k(rig.get("K"), op), "normal": _vec3(rig.get("plane_normal"), "plane_normal", op, unit=True)}
    d = rig.get("plane_d")
    out["d"] = _num(d, "plane_d", op) / float(np.linalg.norm(np.asarray(rig["plane_normal"], float)))
    R, t = rig.get("R"), rig.get("t")
    if (R is None) != (t is None):
        raise ValueError("%s: the rig has R without t (or t without R)" % op)
    if R is not None:
        Rm = np.asarray(R, dtype=np.float64)
        if Rm.shape != (3, 3) or not np.isfinite(Rm).all() or not np.allclose(Rm @ Rm.T, np.eye(3), atol=1e-9) \
                or np.linalg.det(Rm) < 0:
            raise ValueError("%s: the rig's R must be a proper 3x3 rotation" % op)
        out["R"], out["t"] = Rm, _vec3(t, "t", op)
    else:
        out["R"] = out["t"] = None
    return out


def _centers(c, op):
    if not isinstance(c, dict) or c.get("kind") != _CENTERS:
        raise ValueError("%s: expected a line-centre table (kind=%r) from laser_line_center_*, got %r"
                         % (op, _CENTERS, type(c).__name__ if not isinstance(c, dict) else c.get("kind")))
    col = np.asarray(c.get("col"), dtype=np.float64).reshape(-1)
    row = np.asarray(c.get("row"), dtype=np.float64).reshape(-1)
    val = np.asarray(c.get("valid"), dtype=bool).reshape(-1)
    if not (col.size == row.size == val.size) or col.size == 0:
        raise ValueError("%s: the line-centre table's col/row/valid must have the same non-zero length" % op)
    if not (np.isfinite(col[val]).all() and np.isfinite(row[val]).all()):
        raise ValueError("%s: a valid line centre is not finite" % op)
    return col, row, val


# --------------------------------------------------------------------------- #
# 1. 線の中心(列ごと)
# --------------------------------------------------------------------------- #
def _peak_rows(img, min_peak_rel):
    peak_row = np.argmax(img, axis=0)
    cols = np.arange(img.shape[1])
    peak = img[peak_row, cols]
    gmax = float(img.max())
    if gmax <= 0:
        raise ValueError("laser_line_center: the image has no positive intensity — no line to find")
    valid = peak > min_peak_rel * gmax
    return peak_row, peak, valid


def _pack(op, col, row, valid, peak, extra=None):
    row = np.where(valid, row, np.nan)
    col = np.where(valid, col, np.nan) if col.dtype.kind == "f" else col.astype(np.float64)
    out = {"kind": _CENTERS, "method": op.replace("laser_line_center_", ""),
           "col": np.asarray(col, np.float64), "row": np.asarray(row, np.float64),
           "valid": np.asarray(valid, bool), "peak": np.asarray(peak, np.float64),
           "n_valid": int(np.count_nonzero(valid))}
    if extra:
        out.update(extra)
    return out


def laser_line_center_centroid(image, min_peak_rel=0.1, half_window=None, background=0.0, clip_negative=True):
    """Sub-pixel centre of a bright laser line in every column by the intensity centroid (``table``).

    列ごとに最大の行 ``p`` を探し、``[p − half_window, p + half_window]``(``None`` = 列全体)の
    輝度から ``background`` を引いて負を 0 にした重みの重心を返す。最大値が画像全体の最大の
    ``min_peak_rel`` 倍以下の列は ``valid=False``(``row`` は NaN)。

    For each column the peak row ``p`` is found, and the centroid of
    ``max(I − background, 0)`` over ``[p − half_window, p + half_window]`` (``None`` = the whole
    column) is returned. Columns whose peak is at most ``min_peak_rel`` × the image maximum are
    marked ``valid=False`` (``row`` NaN). ``clip_negative=False`` keeps negative weights (zero-mean
    noise stays zero-mean: the estimator is then linear in the noise, which is what
    :func:`light_section_uncertainty_budget`'s read-noise term assumes). Pixel-centre convention of :mod:`camera`: row ``r``
    is the coordinate ``v = r`` exactly.

    Returns ``{"kind": "laser_line_centers", "method": "centroid", "col", "row", "valid",
    "peak", "n_valid"}``. Ground truth: a symmetric line profile has its centroid at the true
    centre; the centroid of a column-binned image equals that of the unbinned one
    (``tests/test_lightsection.py``). ★Limits: the centroid is biased toward the window's
    centre when the window cuts an off-centre profile, and a background left in the weights
    pulls it toward the column's middle.
    """
    op = "laser_line_center_centroid"
    img = _image(image, op)
    mp = _num(min_peak_rel, "min_peak_rel", op, lo=0.0, hi=1.0, lo_open=False, hi_open=True)
    bg = _num(background, "background", op)
    ny, nx = img.shape
    peak_row, peak, valid = _peak_rows(img, mp)
    w = img - bg
    if clip_negative:
        w = np.clip(w, 0.0, None)
    y = np.arange(ny, dtype=np.float64)[:, None]
    if half_window is not None:
        h = _int(half_window, "half_window", op, 1, ny)
        m = np.abs(y - peak_row[None, :]) <= h
        w = w * m
    s = w.sum(axis=0)
    ok = valid & (s > 0) & (s > 1e-12 * np.abs(w).sum(axis=0))
    row = (w * y).sum(axis=0) / np.where(s > 0, s, 1.0)
    return _pack(op, np.arange(nx, dtype=np.float64), row, ok, peak)


def laser_line_center_gauss(image, min_peak_rel=0.1, half_window=2):
    """Sub-pixel line centre per column by a Gaussian fit = weighted parabola on ``ln I`` (``table``).

    列ごとに最大の行 ``p`` のまわり ``2·half_window + 1`` 点で ``ln I = a + b y + c y²`` を
    重み ``I²`` の最小二乗で当て(Guo 2011)、中心 ``p − b / (2c)`` を返す。``half_window=1`` は
    古典の 3 点の対数放物線。正でない画素は外し、3 点未満・``c ≥ 0``(上に凸でない)・
    中心が窓の外に出た列は ``valid=False``。

    Fits ``ln I = a + b y + c y²`` with weights ``I²`` (Guo 2011) on ``2·half_window + 1`` rows
    around the column's peak; the centre is ``p − b / (2c)``. ``half_window=1`` is the classic
    three-point log-parabola. Non-positive samples are dropped; columns with fewer than three
    samples, ``c ≥ 0`` or a centre outside the window are ``valid=False``.

    Ground truth (theorem): the log of a Gaussian is a quadratic, so a point-sampled Gaussian
    line comes back at its sub-pixel centre to 1e-9 px. ★Pixel-integrated (box-filtered)
    profiles are not exactly Gaussian; the bias is then measured, not zero. Also returns
    ``sigma_px`` (the fitted Gaussian's σ = sqrt(−1/(2c))).
    """
    op = "laser_line_center_gauss"
    img = _image(image, op)
    mp = _num(min_peak_rel, "min_peak_rel", op, lo=0.0, hi=1.0, lo_open=False, hi_open=True)
    ny, nx = img.shape
    h = _int(half_window, "half_window", op, 1, max(1, (ny - 1) // 2))
    peak_row, peak, valid = _peak_rows(img, mp)
    offs = np.arange(-h, h + 1)
    rows = peak_row[None, :] + offs[:, None]                     # (2h+1, nx)
    inside = (rows >= 0) & (rows < ny)
    vals = img[np.clip(rows, 0, ny - 1), np.arange(nx)[None, :]]
    pos = inside & (vals > 0)
    lv = np.log(np.where(pos, vals, 1.0))
    wgt = np.where(pos, vals * vals, 0.0)
    yv = offs[:, None].astype(np.float64) * np.ones((1, nx))
    # 重みつき正規方程式(3x3)を列ごとに
    S = [np.sum(wgt * yv ** k, axis=0) for k in range(5)]
    T = [np.sum(wgt * lv * yv ** k, axis=0) for k in range(3)]
    A = np.stack([np.stack([S[0], S[1], S[2]], -1), np.stack([S[1], S[2], S[3]], -1),
                  np.stack([S[2], S[3], S[4]], -1)], -2)          # (nx, 3, 3)
    bvec = np.stack(T, -1)                                        # (nx, 3)
    npos = pos.sum(axis=0)
    det = np.linalg.det(A)
    good = valid & (npos >= 3) & (np.abs(det) > 1e-300)
    coef = np.zeros((nx, 3))
    if np.any(good):
        coef[good] = np.linalg.solve(A[good], bvec[good][..., None])[..., 0]
    b, c = coef[:, 1], coef[:, 2]
    good &= c < 0
    off = np.where(good, -b / np.where(good, 2.0 * c, 1.0), 0.0)
    good &= np.abs(off) <= h
    sig = np.where(good, np.sqrt(-1.0 / np.where(good, 2.0 * c, -1.0)), np.nan)
    return _pack(op, np.arange(nx, dtype=np.float64), peak_row + off, good, peak,
                 {"sigma_px": sig})


def laser_line_center_steger(image, sigma=1.5, min_peak_rel=0.1, max_iter=3):
    """Sub-pixel line centre by Steger's Hessian method (``table``).

    ガウスの微分(``scipy.ndimage.gaussian_filter``、σ = ``sigma``)で 1 次・2 次の微分を取り、
    Hessian の絶対値最大の固有値(明るい線では負)の固有ベクトル ``n`` を線の法線とし、
    2 次の Taylor 展開の極値 ``t = −(r_x n_x + r_y n_y) / (r_xx n_x² + 2 r_xy n_x n_y + r_yy n_y²)``
    を線の中心とする(Steger 1998)。列ごとに平滑化した画像の最大の行から始め、``t n`` が
    画素の外(|·| > 0.5)なら隣の画素へ移って ``max_iter`` 回まで繰り返し、``|t n|∞`` が最小の
    画素の値を採る(中心がちょうど画素の境にあると Newton の 1 歩の行き過ぎで 2 画素の間を往復する
    ので、0.5 の厳密な判定だけでは拾えない —— 実測)。最小でも ``|t n|∞ > 1``(隣の画素より遠い)・
    固有値が負でない列は ``valid=False``。中心は 2-D の点(``col`` も実数)。

    Steger (1998): with Gaussian-derivative filters of scale ``sigma`` the line normal ``n`` is
    the eigenvector of the Hessian's largest-magnitude eigenvalue (negative for a bright line),
    and the centre is the extremum of the second-order Taylor polynomial along ``n``. The
    point is 2-D (``col`` is sub-pixel too). Also returns ``strength`` (−eigenvalue) and the
    normal ``nx``, ``ny``.

    Ground truth (closed form of one Newton step on a Gaussian): for a Gaussian profile of
    total variance ``σ² = σ_line² + sigma²`` and a start pixel at offset ``δ`` from the centre,
    the error is ``−δ³ / (σ² − δ²)`` (≤ 0.125/σ² px for |δ| ≤ 0.5). Steger's condition
    ``sigma ≥ w/√3`` (w = the line's half-width) keeps the profile's second derivative single-signed.
    """
    op = "laser_line_center_steger"
    img = _image(image, op)
    s = _num(sigma, "sigma", op, lo=0.3, hi=64.0, lo_open=False)
    mp = _num(min_peak_rel, "min_peak_rel", op, lo=0.0, hi=1.0, lo_open=False, hi_open=True)
    it = _int(max_iter, "max_iter", op, 1, 16)
    ny, nx = img.shape
    g = ndimage.gaussian_filter(img, s, mode="nearest")
    ry = ndimage.gaussian_filter(img, s, order=(1, 0), mode="nearest")
    rx = ndimage.gaussian_filter(img, s, order=(0, 1), mode="nearest")
    ryy = ndimage.gaussian_filter(img, s, order=(2, 0), mode="nearest")
    rxx = ndimage.gaussian_filter(img, s, order=(0, 2), mode="nearest")
    rxy = ndimage.gaussian_filter(img, s, order=(1, 1), mode="nearest")
    cols = np.arange(nx)
    r = np.argmax(g, axis=0)
    peak = img[np.argmax(img, axis=0), cols]
    gmax = float(img.max())
    if gmax <= 0:
        raise ValueError("%s: the image has no positive intensity — no line to find" % op)
    valid = peak > mp * gmax
    c = cols.copy()
    best = np.full(nx, np.inf)                       # これまでで最小の |t n|∞(負の固有値のときだけ)
    py = np.full(nx, np.nan)
    px = np.full(nx, np.nan)
    lam_out = np.full(nx, np.nan)
    nxo = np.full(nx, np.nan)
    nyo = np.full(nx, np.nan)
    for _ in range(it):
        a, b2, d2 = rxx[r, c], rxy[r, c], ryy[r, c]
        # 2x2 対称行列の固有値・固有ベクトル(閉形式)
        tr2 = 0.5 * (a + d2)
        disc = np.sqrt(0.25 * (a - d2) ** 2 + b2 * b2)
        l1, l2 = tr2 + disc, tr2 - disc
        lam = np.where(np.abs(l1) >= np.abs(l2), l1, l2)
        vx = np.where(np.abs(b2) > 1e-300, lam - d2, np.where(np.abs(a) >= np.abs(d2), 1.0, 0.0))
        vy = np.where(np.abs(b2) > 1e-300, b2, np.where(np.abs(a) >= np.abs(d2), 0.0, 1.0))
        nn = np.hypot(vx, vy)
        vx, vy = vx / nn, vy / nn
        den = a * vx * vx + 2.0 * b2 * vx * vy + d2 * vy * vy
        num = rx[r, c] * vx + ry[r, c] * vy
        t = np.where(np.abs(den) > 1e-300, -num / np.where(np.abs(den) > 1e-300, den, 1.0), np.inf)
        with np.errstate(invalid="ignore"):
            dx, dy = t * vx, t * vy
            dist = np.maximum(np.abs(dx), np.abs(dy))
        dist = np.where(np.isfinite(dist) & (lam < 0), dist, np.inf)
        newly = dist < best
        best = np.where(newly, dist, best)
        py[newly] = r[newly] + dy[newly]
        px[newly] = c[newly] + dx[newly]
        lam_out[newly] = lam[newly]
        nxo[newly], nyo[newly] = vx[newly], vy[newly]
        done = best <= 0.5
        if done.all():
            break
        # 画素の外へ出た列は、その向きの隣の画素へ
        step_y = np.where(np.isfinite(dy), np.sign(np.round(dy)), 0).astype(int)
        step_x = np.where(np.isfinite(dx), np.sign(np.round(dx)), 0).astype(int)
        move = ~done
        r = np.where(move, np.clip(r + step_y, 0, ny - 1), r)
        c = np.where(move, np.clip(c + step_x, 0, nx - 1), c)
    ok = valid & (best <= 1.0)
    return _pack(op, px, py, ok, peak,
                 {"strength": np.where(ok, -lam_out, np.nan), "nx": nxo, "ny": nyo, "sigma": s})


# --------------------------------------------------------------------------- #
# 2. 装置の幾何・校正の的・合成
# --------------------------------------------------------------------------- #
def light_section_rig(theta_deg=30.0, standoff_mm=200.0, focal_px=2000.0, image_shape=(480, 640)):
    """A light-section rig with known geometry (``table``): pinhole camera + laser plane.

    世界座標: X = 光条に沿う向き、Y = 走査(搬送)の向き、Z = 上。レーザーは真上から
    ``Y = 0`` の面に光を立てる。カメラは Y–Z 面の中で光面から ``theta_deg`` 傾いた向きから、
    距離 ``standoff_mm`` で原点を見る(画像の u = 世界の X、高さが増えると光条は画像の上へ)。
    ``K`` は主点が画像の中心(:mod:`camera` の画素中心の約束)。

    World frame: X along the line, Y the scan direction, Z up; the laser plane is ``Y = 0``.
    The camera looks at the origin from ``standoff_mm`` away, tilted ``theta_deg`` from the
    laser plane in the Y–Z plane (camera x = world X). Returns ``{"kind": "light_section_rig",
    "K", "R", "t" (world → camera, X_c = R X_w + t), "plane_normal", "plane_d" (laser plane in
    camera coordinates, n·X_c = d), "theta_deg", "standoff_mm", "image_shape",
    "plane_normal_world", "plane_d_world"}``.

    Ground truth: the camera centre ``−Rᵀ t`` is at distance ``standoff_mm`` from the origin and
    the plane's camera-frame equation maps world points with ``Y = 0`` to residual 0 (1e-12).
    """
    op = "light_section_rig"
    th = _num(theta_deg, "theta_deg", op, lo=0.0, hi=89.0)
    so = _num(standoff_mm, "standoff_mm", op, lo=0.0, hi=1e6)
    f = _num(focal_px, "focal_px", op, lo=0.0, hi=1e7)
    try:
        ny, nx = image_shape
    except (TypeError, ValueError):
        raise ValueError("%s: image_shape must be (rows, cols), got %r" % (op, image_shape)) from None
    ny = _int(ny, "image_shape[0]", op, 8, 1 << 14)
    nx = _int(nx, "image_shape[1]", op, 8, 1 << 14)
    t_ = math.radians(th)
    C = np.array([0.0, -so * math.sin(t_), so * math.cos(t_)])
    zc = -C / so
    xc = np.array([1.0, 0.0, 0.0])
    yc = np.cross(zc, xc)
    R = np.stack([xc, yc, zc])
    t = -R @ C
    K = np.array([[f, 0.0, (nx - 1) / 2.0], [0.0, f, (ny - 1) / 2.0], [0.0, 0.0, 1.0]])
    n_w = np.array([0.0, 1.0, 0.0])
    n_c = R @ n_w
    d_c = float(n_c @ t)                       # n_w·X_w = 0 → (R n_w)·X_c = (R n_w)·t
    return {"kind": _RIG, "K": K, "R": R, "t": t, "plane_normal": n_c, "plane_d": d_c,
            "plane_normal_world": n_w, "plane_d_world": 0.0,
            "theta_deg": th, "standoff_mm": so, "image_shape": (ny, nx)}


def light_section_targets(rig, heights_mm, col_ranges=None):
    """Known horizontal planes ``Z = h`` (gauge blocks, a step, the base) as camera-frame planes (``table``).

    校正の的: 世界の水平面 ``Z = h_k`` を、装置の姿勢 ``R, t`` でカメラ座標の平面の式
    ``n_k · X_c = d_k`` に直す。1 枚の画像に複数の高さ(段差の的)が写るときは
    ``col_ranges`` に ``(col_lo, col_hi)``(両端を含む)を高さごとに与える。

    World planes ``Z = h_k`` mapped by the rig's pose to ``n_k · X_c = d_k``. Use ``col_ranges``
    ``[(lo, hi), ...]`` (inclusive) when one image shows several heights (a step target).
    Returns ``{"kind": "light_section_targets", "normal" (M, 3), "d" (M,), "height_mm" (M,),
    "col_lo" (M,), "col_hi" (M,)}``. The rig must carry ``R, t``.
    """
    op = "light_section_targets"
    g = _rig(rig, op)
    if g["R"] is None:
        raise ValueError("%s: the rig has no pose (R, t) — the targets' planes cannot be placed" % op)
    h = np.asarray(heights_mm, dtype=np.float64).reshape(-1)
    if h.size == 0 or not np.isfinite(h).all():
        raise ValueError("%s: heights_mm must be one or more finite numbers" % op)
    R, t = g["R"], g["t"]
    n_c = R @ np.array([0.0, 0.0, 1.0])
    d = h + float(n_c @ t)                      # Z_w = h → (R e_z)·X_c = h + (R e_z)·t
    lo = np.full(h.size, -1.0)                 # 既定 = 全部の列(有限の印。−1 と 2³¹ は画像の外)
    hi = np.full(h.size, float(1 << 31))
    if col_ranges is not None:
        cr = np.asarray(col_ranges, dtype=np.float64)
        if cr.shape != (h.size, 2) or not np.all(cr[:, 0] <= cr[:, 1]):
            raise ValueError("%s: col_ranges must be (M, 2) with lo <= hi, one per height" % op)
        lo, hi = cr[:, 0].copy(), cr[:, 1].copy()
    return {"kind": _TARGETS, "normal": np.tile(n_c, (h.size, 1)), "d": d, "height_mm": h,
            "col_lo": lo, "col_hi": hi}


def light_section_render(rig, profile, line_sigma_px=1.5, peak=1.0, background=0.0, noise=0.0,
                         seed=0, sampling="point"):
    """Image of the laser line on a surface profile seen by the rig's camera (``image2d``).

    ``profile`` は光面(世界 ``Y = 0``)上の断面 ``(x_mm, h_mm)`` の (K, 2) の並び(x は単調増加)。
    各点を :func:`camera.project_points` で写し、画像の列ごとに断面の像の行 ``v(u)`` を線形補間し、
    行の向きに σ = ``line_sigma_px`` のガウスの光条を描く(``sampling="point"`` = 画素中心の点標本、
    ``"pixel"`` = 画素の面積で積分した誤差関数の差)。断面の外の列は背景だけ。
    ``noise`` は加法ガウス雑音の標準偏差(``seed``)。

    ``profile`` is the (K, 2) cross-section ``(x_mm, h_mm)`` on the laser plane (x increasing).
    The points are projected with :func:`camera.project_points`, the image row of the profile
    ``v(u)`` is linearly interpolated per column, and a Gaussian line of σ = ``line_sigma_px``
    is drawn along the rows (``"point"`` = point samples at pixel centres, ``"pixel"`` = the
    pixel-area integral). ★Limits: constant line width, no foreshortening, no defocus, no
    self-occlusion (a step's shadow) and no inter-reflection; a profile whose image folds over
    (``u`` not monotonic) is refused. The rig must carry ``R, t`` (made by
    :func:`light_section_rig`).
    """
    op = "light_section_render"
    g = _rig(rig, op)
    if g["R"] is None:
        raise ValueError("%s: the rig has no pose (R, t)" % op)
    P = np.asarray(profile, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 2 or P.shape[0] < 2 or not np.isfinite(P).all():
        raise ValueError("%s: profile must be a finite (K >= 2, 2) array of (x_mm, h_mm)" % op)
    if not np.all(np.diff(P[:, 0]) > 0):
        raise ValueError("%s: profile x_mm must be strictly increasing" % op)
    sig = _num(line_sigma_px, "line_sigma_px", op, lo=0.05, hi=1e3)
    pk = _num(peak, "peak", op, lo=0.0, hi=1e9)
    bg = _num(background, "background", op)
    nz = _num(noise, "noise", op, lo=0.0, hi=1e9, lo_open=False)
    if sampling not in ("point", "pixel"):
        raise ValueError("%s: sampling must be 'point' or 'pixel'" % op)
    ny, nx = rig.get("image_shape", (None, None))
    ny = _int(ny, "rig image_shape[0]", op, 8, 1 << 14)
    nx = _int(nx, "rig image_shape[1]", op, 8, 1 << 14)
    Xw = np.column_stack([P[:, 0], np.zeros(P.shape[0]), P[:, 1]])
    res = (g["R"] @ Xw.T).T + g["t"]
    if np.max(np.abs(res @ g["normal"] - g["d"])) > 1e-6 * max(1.0, abs(g["d"])):
        raise ValueError("%s: the rig's laser plane is not the world plane Y = 0 — render supports "
                         "rigs from light_section_rig only" % op)
    uv, z = _camera.project_points(Xw, g["K"], g["R"], g["t"])
    if np.any(z <= 0):
        raise ValueError("%s: part of the profile is behind the camera" % op)
    u, v = uv[:, 0], uv[:, 1]
    du = np.diff(u)
    if not (np.all(du > 0) or np.all(du < 0)):
        raise ValueError("%s: the profile's image folds over (u is not monotonic) — not supported" % op)
    if du[0] < 0:
        u, v = u[::-1], v[::-1]
    cols = np.arange(nx, dtype=np.float64)
    inside = (cols >= u[0]) & (cols <= u[-1])
    vc = np.interp(cols, u, v)
    rows = np.arange(ny, dtype=np.float64)[:, None]
    if sampling == "point":
        band = np.exp(-0.5 * ((rows - vc[None, :]) / sig) ** 2)
    else:
        from scipy.special import erf  # noqa: PLC0415
        s2 = sig * math.sqrt(2.0)
        # 画素(幅 1)の面積で積分した exp(−(y − v)²/(2σ²))。幅 1 の画素では中心の値とほぼ同じ高さ。
        band = (math.sqrt(math.pi / 2.0) * sig) * (erf((rows + 0.5 - vc) / s2) - erf((rows - 0.5 - vc) / s2))
    img = bg + pk * band * inside[None, :]
    if nz > 0:
        img = img + np.random.default_rng(_int(seed, "seed", op, 0, (1 << 63) - 1)).normal(0.0, nz, img.shape)
    return img


# --------------------------------------------------------------------------- #
# 3. 光面の校正・三角測量・走査
# --------------------------------------------------------------------------- #
def _rays(col, row, K):
    uv1 = np.column_stack([col, row, np.ones(col.size)])
    return uv1 @ np.linalg.inv(K).T                     # z 成分 = 1 の視線


def _intersect(rays, normal, d, op):
    den = rays @ normal
    if np.any(np.abs(den) < 1e-12):
        raise ValueError("%s: a viewing ray is parallel to the plane (no intersection)" % op)
    s = d / den
    if np.any(s <= 0):
        raise ValueError("%s: a plane intersection is behind the camera" % op)
    return rays * s[:, None]


def light_plane_calibrate(centers_list, targets, K, R=None, t=None):
    """Fit the laser plane ``n · X = d`` (camera frame) from lines on known planes (``table``).

    ``centers_list[k]``(``laser_line_center_*`` の表)は、既知の平面
    ``targets["normal"][k] · X = targets["d"][k]`` に当たった光条。列の範囲
    ``col_lo..col_hi`` の中の有効な中心を視線と的の平面の交点に上げ、全部の点に平面を全最小
    二乗(重心を引いた SVD)で当てる。点が 1 直線に並ぶ(的の高さが 1 つ)と面が決まらないので
    拒む(2 番目と 3 番目の特異値の比で判定)。

    Each centre table is lifted to 3-D by intersecting its viewing rays with the matching known
    plane, and one plane is fitted to all points by total least squares (SVD of the centred
    points). Points on a single line (one target height) leave the plane undetermined and are
    refused: all points from one target plane (its intersection with the laser plane is one
    line, whatever the noise), or ``s2 < 10 s3`` (the spread across the line is not above the
    noise). Returns a rig table ``{"kind": "light_section_rig", "K",
    "plane_normal", "plane_d", "rms_mm", "max_abs_mm", "n_points", "conditioning" (s2/s1),
    "R", "t"}`` (``R, t`` only if given — the world pose of the camera, for world-frame output).
    The normal is oriented so that ``d > 0`` (the camera at the origin is on the negative side).
    """
    op = "light_plane_calibrate"
    Km = _matrix_k(K, op)
    if isinstance(centers_list, dict):
        centers_list = [centers_list]
    if not isinstance(centers_list, (list, tuple)) or len(centers_list) == 0:
        raise ValueError("%s: centers_list must be a non-empty list of line-centre tables" % op)
    if not isinstance(targets, dict) or targets.get("kind") != _TARGETS:
        raise ValueError("%s: targets must be a table from light_section_targets (kind=%r)" % (op, _TARGETS))
    tn = np.asarray(targets["normal"], dtype=np.float64)
    td = np.asarray(targets["d"], dtype=np.float64).reshape(-1)
    lo = np.asarray(targets.get("col_lo", np.full(td.size, -np.inf)), dtype=np.float64).reshape(-1)
    hi = np.asarray(targets.get("col_hi", np.full(td.size, np.inf)), dtype=np.float64).reshape(-1)
    if tn.shape != (len(centers_list), 3) or td.size != len(centers_list) or lo.size != td.size or hi.size != td.size:
        raise ValueError("%s: targets must have one plane per centre table (%d), got %d"
                         % (op, len(centers_list), td.size))
    pts = []
    used = []
    for k, c in enumerate(centers_list):
        col, row, val = _centers(c, op)
        m = val & (col >= lo[k]) & (col <= hi[k])
        if not np.any(m):
            continue
        nrm = tn[k] / np.linalg.norm(tn[k])
        dk = td[k] / np.linalg.norm(tn[k])
        pts.append(_intersect(_rays(col[m], row[m], Km), nrm, dk, op))
        used.append(np.r_[nrm, dk])
    # 1 つの的の平面と光面の交わりは 1 本の直線: 平面が 1 枚(同じ平面の繰り返しを含む)なら、
    # 雑音でどれだけ点が散っても光面は決まらない(雑音つきの点は特異値の判定をすり抜ける —— PoC で実測)。
    U_ = np.unique(np.round(np.asarray(used), 9), axis=0) if used else np.zeros((0, 4))
    if U_.shape[0] < 2:
        raise ValueError("%s: all calibration points lie on one target plane, so on one line — use "
                         "targets at two or more heights" % op)
    if not pts:
        raise ValueError("%s: no valid line centre fell on any target" % op)
    X = np.concatenate(pts)
    if X.shape[0] < 3:
        raise ValueError("%s: need at least 3 points, got %d" % (op, X.shape[0]))
    cen = X.mean(axis=0)
    _, sv, vt = np.linalg.svd(X - cen, full_matrices=False)
    if sv[1] <= 1e-9 * max(sv[0], 1e-300) or sv[1] < 1e-6 or sv[1] < 10.0 * sv[2]:
        raise ValueError("%s: the calibration points lie on one line (singular values %s) — use "
                         "targets at two or more heights" % (op, sv))
    n = vt[2]
    d = float(n @ cen)
    if d < 0:
        n, d = -n, -d
    r = X @ n - d
    out = {"kind": _RIG, "K": Km, "plane_normal": n, "plane_d": d,
           "rms_mm": float(np.sqrt(np.mean(r * r))), "max_abs_mm": float(np.max(np.abs(r))),
           "n_points": int(X.shape[0]), "conditioning": float(sv[1] / sv[0]),
           "singular_values": sv}
    if (R is None) != (t is None):
        raise ValueError("%s: pass both R and t, or neither" % op)
    if R is not None:
        out["R"] = np.asarray(R, dtype=np.float64)
        out["t"] = _vec3(t, "t", op)
        _rig(out, op)                                  # 姿勢の検査
    return out


def _to_world(Xc, g):
    if g["R"] is None:
        return Xc
    return (Xc - g["t"]) @ g["R"]                      # X_w = Rᵀ (X_c − t)


def light_section_profile(centers, rig):
    """Triangulate line centres into 3-D points: viewing ray ∩ laser plane (``points``).

    有効な中心ごとに視線 ``K⁻¹ (u, v, 1)`` と光面 ``n · X = d`` の交点を返す (N, 3)。
    装置の表が姿勢 ``R, t`` を持つなら世界座標(Z = 高さ)、無ければカメラ座標。

    Returns (N, 3) points for the valid centres: in world coordinates (Z = height) when the
    rig carries ``R, t``, otherwise in camera coordinates. Ground truth: a profile rendered by
    :func:`light_section_render` (forward projection) comes back at its true heights.
    """
    op = "light_section_profile"
    g = _rig(rig, op)
    col, row, val = _centers(centers, op)
    if not np.any(val):
        raise ValueError("%s: no valid line centre to triangulate" % op)
    Xc = _intersect(_rays(col[val], row[val], g["K"]), g["normal"], g["d"], op)
    return _to_world(Xc, g)


_METHODS = {"centroid": laser_line_center_centroid, "gauss": laser_line_center_gauss,
            "steger": laser_line_center_steger}


def _scan_frames(images, op):
    if isinstance(images, np.ndarray) and images.ndim == 3:
        images = list(images)
    if not isinstance(images, (list, tuple)) or len(images) == 0:
        raise ValueError("%s: images must be a non-empty list of 2-D images" % op)
    if len(images) > MAX_FRAMES:
        raise ValueError("%s: %d frames is over the %d cap" % (op, len(images), MAX_FRAMES))
    return images


def light_section_scan(images, rig, step_mm=(0.0, 0.1, 0.0), method="gauss", center_kw=None):
    """Scan: frame ``k`` sees the part moved by ``k · step_mm`` → one point cloud in the part's frame (``points``).

    1 枚ごとに中心(``method`` = centroid / gauss / steger)→ 三角測量 → 部品の座標へ戻す
    (``X − k · step``)。``step_mm`` は装置が姿勢を持てば世界座標、無ければカメラ座標の 3 成分。
    Each frame: centres (``method``) → triangulation → back to the part's frame
    (``X − k · step_mm``). ``step_mm`` is in world coordinates when the rig has a pose, else in
    camera coordinates. ``center_kw`` is passed to the centre op.
    """
    op = "light_section_scan"
    frames = _scan_frames(images, op)
    g = _rig(rig, op)
    st = _vec3(step_mm, "step_mm", op)
    if method not in _METHODS:
        raise ValueError("%s: method must be one of %s" % (op, sorted(_METHODS)))
    kw = dict(center_kw or {})
    out = []
    for k, im in enumerate(frames):
        c = _METHODS[method](im, **kw)
        if not np.any(c["valid"]):
            continue
        out.append(light_section_profile(c, rig) - k * st)
    if not out:
        raise ValueError("%s: no frame had a valid line centre" % op)
    del g
    return np.concatenate(out)


def light_section_height_map(images, rig, reference_plane=None, method="gauss", center_kw=None):
    """Height map over (frame, image column) from a scan (``depth``; NaN = not measured).

    各フレームの各列の中心を三角測量し、高さ = 基準面からの符号つき距離を (フレーム数, 列数) の
    格子に置く。基準面は ``reference_plane = (normal (3,), d)``(装置と同じ座標)で、``None`` なら
    装置が姿勢を持つとき世界の ``Z = 0``(高さ = Z)。中心が取れない列は NaN(= 測れない)。

    Heights are the signed distance to ``reference_plane`` = ``(normal, d)`` in the rig's frame
    (``None`` = world ``Z = 0`` for a posed rig). Columns without a valid centre are NaN.
    ★The grid is (frame, image column), not uniform in world X; resample the points of
    :func:`light_section_scan` when a metric grid is needed.
    """
    op = "light_section_height_map"
    frames = _scan_frames(images, op)
    g = _rig(rig, op)
    if method not in _METHODS:
        raise ValueError("%s: method must be one of %s" % (op, sorted(_METHODS)))
    if reference_plane is None:
        if g["R"] is None:
            raise ValueError("%s: a rig without a pose needs reference_plane=(normal, d)" % op)
        rn, rd = np.array([0.0, 0.0, 1.0]), 0.0
    else:
        try:
            rn_raw, rd = reference_plane
        except (TypeError, ValueError):
            raise ValueError("%s: reference_plane must be (normal (3,), d)" % op) from None
        rn_raw = _vec3(rn_raw, "reference_plane normal", op)
        nn = float(np.linalg.norm(rn_raw))
        if nn < 1e-12:
            raise ValueError("%s: reference_plane normal is zero" % op)
        rn, rd = rn_raw / nn, _num(rd, "reference_plane d", op) / nn
    kw = dict(center_kw or {})
    nx = np.asarray(frames[0]).shape[1]
    H = np.full((len(frames), nx), np.nan)
    for k, im in enumerate(frames):
        if np.asarray(im).shape[1] != nx:
            raise ValueError("%s: frame %d has %d columns, frame 0 has %d" % (op, k, np.asarray(im).shape[1], nx))
        c = _METHODS[method](im, **kw)
        col, row, val = _centers(c, op)
        if not np.any(val):
            continue
        X = light_section_profile(c, rig)
        ci = np.clip(np.rint(col[val]).astype(int), 0, nx - 1)
        H[k, ci] = X @ rn - rd
    return H


# --------------------------------------------------------------------------- #
# 4. Fullseye だけの層: スペックルの床と不確かさの予算
# --------------------------------------------------------------------------- #
def _chi2_ci(sd, dof):
    from scipy import stats as _st  # noqa: PLC0415
    lo = sd * math.sqrt(dof / _st.chi2.ppf(0.975, dof))
    hi = sd * math.sqrt(dof / _st.chi2.ppf(0.025, dof))
    return lo, hi


def light_section_speckle_floor(wavelength_um=0.65, sin_u_obs=0.1, sin_theta=0.5, line_width_um=40.0,
                                pixel_um=1.0, length_um=None, method="centroid", n_trials=12,
                                n_columns=1024, n_rows=160, n_patterns=1, polarizations=1,
                                noise_rel=0.0, pixel_oversample=2, seed=0, center_kw=None,
                                smooth_surface=False):
    """Speckle floor of a light-section height, simulated and in closed form side by side (``table``).

    シミュ: :func:`coherent.laser_line_coherent` で粗面のスペックル込みの光条を ``n_trials`` 枚
    (高さは乱数、部品ごとに別の位相スクリーン)描き、``method`` の中心抽出で列ごとの中心を取り、
    長さ ``length_um``(既定 = 光条の幅)ごとに平均して高さに直す(``z = Δrow · pixel / sin θ``、
    coherent の三角測量の約束)。真の高さとの差の標準偏差が ``sim_delta_z_um``(95 % の χ² 区間つき)。
    閉形式: ``δz = C λ / (2π sin u_obs sin θ) · √(w/L)``、C = 1/√(n_patterns · polarizations)
    (:func:`coherent.speckle_reduction`)。読み出し雑音 ``noise_rel``(光条の頂の平均に対する比)は
    シミュに入り、閉形式の側は :func:`light_section_uncertainty_budget` の雑音の項と合わせて
    ``closed_form_total_um`` に入る。

    Simulates ``n_trials`` speckled lines with :func:`coherent.laser_line_coherent`, extracts the
    centre per column with ``method``, averages over ``length_um`` (default = the line width) and
    converts to height (``z = Δrow · pixel / sin θ``). Returns the simulated standard deviation
    (with its χ² 95 % interval), the Dorsch closed form, their ratio, and the additive-noise
    term. ``smooth_surface=True`` renders a mirror-smooth part (phase 0: no speckle, contrast 0)
    so that only ``noise_rel`` is left — the gate for the budget's read-noise term. ``center_kw`` overrides the estimator's settings (defaults: centroid over the whole
    column without clipping; gauss with ``half_window`` = the line's 1/e² half-width in pixels;
    steger with ``sigma = w/(pixel·√3)``). ★Columns within one block share speckle; blocks are treated as independent samples
    (the χ² interval assumes that). ★The 2π constant is from the open-access Ettl et al. 2014,
    which cites Dorsch et al. 1994; the primary text was not read.
    """
    op = "light_section_speckle_floor"
    lam = _num(wavelength_um, "wavelength_um", op, lo=0.0, hi=100.0)
    su = _num(sin_u_obs, "sin_u_obs", op, lo=0.0, hi=1.0)
    st = _num(sin_theta, "sin_theta", op, lo=0.0, hi=1.0)
    w = _num(line_width_um, "line_width_um", op, lo=0.0, hi=1e5)
    pix = _num(pixel_um, "pixel_um", op, lo=0.0, hi=1e4)
    L = w if length_um is None else _num(length_um, "length_um", op, lo=0.0, hi=1e7)
    if method not in _METHODS:
        raise ValueError("%s: method must be one of %s" % (op, sorted(_METHODS)))
    nt = _int(n_trials, "n_trials", op, 2, 4096)
    nc = _int(n_columns, "n_columns", op, 8, 1 << 14)
    nr = _int(n_rows, "n_rows", op, 16, 1 << 12)
    npat = _int(n_patterns, "n_patterns", op, 1, _coherent.MAX_PATTERNS)
    pol = _int(polarizations, "polarizations", op, 1, 2)
    nz = _num(noise_rel, "noise_rel", op, lo=0.0, hi=10.0, lo_open=False)
    s = _int(pixel_oversample, "pixel_oversample", op, 1, 16)
    sd0 = _int(seed, "seed", op, 0, (1 << 62))
    if not isinstance(smooth_surface, (bool, np.bool_)):
        raise ValueError("%s: smooth_surface must be True or False" % op)
    smooth = bool(smooth_surface)
    block = max(1, int(round(L / pix)))
    nb = nc // block
    if nb < 1:
        raise ValueError("%s: length_um (%g) is longer than the simulated line (%g um)" % (op, L, nc * pix))
    ckw_all = {"min_peak_rel": 0.0}                            # スペックルの暗い列も数える(落とすと床が下がって見える)
    rng = np.random.default_rng(sd0)
    # 高さは ±1 行ぶんの乱数(サブピクセルの位置を振る)。大きく振ると光条の裾が窓の端で切れ、
    # 重心が窓の中心へ寄る系統誤差が床に混ざる(滑らかな面・雑音 0 で 0.11 µm、実測)。
    span = 1.0 * pix / st
    if method == "centroid":
        ckw = dict(ckw_all, clip_negative=False)
    elif method == "gauss":                                      # 窓 = 光条の 1/e² 半幅(5 点では粒の頂を当てる)
        ckw = dict(ckw_all, half_window=max(1, min(int(round(w / pix)), (nr - 1) // 2)))
    else:                                                        # Steger の条件 σ ≥ w/√3(w = 半幅)
        ckw = dict(ckw_all, sigma=max(0.5, (w / pix) / math.sqrt(3.0)))
    ckw.update(center_kw or {})
    errs = []
    for k in range(nt):
        h = float(rng.uniform(-span, span))
        img = _coherent.laser_line_coherent(shape=(nr, nc), wavelength_um=lam, sin_u_obs=su,
                                            pixel_um=pix, line_width_um=w, height_um=h, sin_theta=st,
                                            polarizations=pol, n_patterns=npat, pixel_oversample=s,
                                            noise=nz, seed=sd0 * 7919 + k, noise_seed=sd0 * 104729 + k,
                                            roughness_rad=0.0 if smooth else None)
        c = _METHODS[method](img, **ckw)
        row = c["row"]
        if not np.all(c["valid"]):
            # 取れない列がある設定(雑音が大きすぎる)は数えずに拒む —— 黙って詰めると床が下がって見える
            raise ValueError("%s: %d of %d columns had no valid centre — the setting is outside the "
                             "estimator's range" % (op, int(np.count_nonzero(~c["valid"])), nc, ))
        rb = row[: nb * block].reshape(nb, block).mean(axis=1)
        z = (rb - (nr - 1) / 2.0) * pix / st
        errs.append(z - h)
    e = np.concatenate(errs)
    sd = float(e.std(ddof=1))
    dof = e.size - 1
    lo, hi = _chi2_ci(sd, dof)
    red = _coherent.speckle_reduction(n_patterns=npat, polarizations=pol)
    C_sp = 0.0 if smooth else red["contrast_diversity"]
    lim = _coherent.triangulation_speckle_limit(lam, su, st, contrast=C_sp)
    cf = lim["delta_z_um"] * math.sqrt(w / L)
    bud = light_section_uncertainty_budget(lam, su, st, line_width_um=w, pixel_um=pix, length_um=L,
                                           n_patterns=npat, polarizations=pol, noise_rel=nz,
                                           window_rows=nr, speckle_contrast=C_sp)
    return {
        "sim_delta_z_um": sd, "sim_ci95_um": (lo, hi), "sim_bias_um": float(e.mean()),
        "n_samples": int(e.size), "block_columns": block,
        "closed_form_delta_z_um": cf, "ratio_sim_to_closed_form": sd / cf if cf > 0 else float("nan"),
        "closed_form_total_um": bud["combined_u_z_um"],
        "ratio_sim_to_closed_form_total": (sd / bud["combined_u_z_um"] if bud["combined_u_z_um"] > 0
                                           else float("nan")),
        "noise_term_um": float(bud["delta_z_um"][1]),
        "speckle_fwhm_um": lim["speckle_fwhm_um"], "contrast": C_sp, "smooth_surface": smooth,
        "method": method, "wavelength_um": lam, "sin_u_obs": su, "sin_theta": st,
        "line_width_um": w, "length_um": L, "pixel_um": pix, "noise_rel": nz,
        "formula": "delta_z = C*lambda/(2*pi*sin_u*sin_theta) * sqrt(w/L)",
        "source": lim["source"] + "; open-access form: Ettl et al., arXiv:1401.1946 (2014)",
    }


def _centroid_noise_var_rows(w_px, window_rows):
    """光条 exp(−2 y²/w²)(頂 1)の列全体の重心に、標準偏差 1 の白色雑音が入れる分散 [行²]。

    線形化: δŷ = Σ (y − y0) n_y / Σ I_y、var = Σ (y − y0)² / (Σ I)²(列の全 ``window_rows`` 行)。
    """
    y = np.arange(window_rows, dtype=np.float64) - (window_rows - 1) / 2.0
    I = np.exp(-2.0 * y * y / (w_px * w_px))
    return float(np.sum(y * y) / np.sum(I) ** 2)


def light_section_uncertainty_budget(wavelength_um=0.65, sin_u_obs=0.1, sin_theta=0.5, line_width_um=40.0,
                                     pixel_um=1.0, length_um=None, n_patterns=1, polarizations=1,
                                     noise_rel=0.0, peak_dn=None, window_rows=160, calib_rms_um=0.0,
                                     calib_dof=np.inf, speckle_contrast=None):
    """Uncertainty budget of a light-section height as a GUM table (``table``).

    成分(行)/ components:
      * ``speckle``: ``u = C λ / (2π sin u_obs) · √(w/L)`` [µm、観察面の横ずれ]、感度 ``1/sin θ``。
      * ``read_noise``: 列全体の重心に加法の白色雑音(頂に対する比 ``noise_rel``、``peak_dn`` を
        与えれば量子化 1/12 LSB² も)が入れる分散を線形化した閉形式
        ``Σ (y − y0)² / (Σ I)² · σ²``、``L / pixel`` 列の平均で割る。単位は µm、感度 ``1/sin θ``。
      * ``calibration``: 光面の校正の残差 ``calib_rms_um``、感度 1、自由度 ``calib_dof``。
    列は ``source`` / ``u`` / ``sensitivity`` / ``dof`` / ``delta_z_um``(= |c|·u)で、
    :func:`spc.gum_propagate` / :func:`spc.gum_expanded` にそのまま渡せる(相関なしを仮定)。
    ``combined_u_z_um``(二乗和の平方根)と ``dominant``(最大の成分)も返す。

    ★The read-noise term is the linearised variance of the whole-column centroid (the estimator
    of :func:`laser_line_center_centroid` with ``half_window=None`` over ``window_rows`` rows);
    other estimators have other noise gains. ``speckle_contrast`` overrides the contrast
    (default ``1/√(n_patterns · polarizations)``, fully developed speckle; 0 = a smooth surface). The √(w/L) speckle averaging is a measured rule
    (see :mod:`coherent`), not part of Dorsch's closed form.
    """
    op = "light_section_uncertainty_budget"
    lam = _num(wavelength_um, "wavelength_um", op, lo=0.0, hi=100.0)
    su = _num(sin_u_obs, "sin_u_obs", op, lo=0.0, hi=1.0)
    st = _num(sin_theta, "sin_theta", op, lo=0.0, hi=1.0)
    w = _num(line_width_um, "line_width_um", op, lo=0.0, hi=1e5)
    pix = _num(pixel_um, "pixel_um", op, lo=0.0, hi=1e4)
    L = w if length_um is None else _num(length_um, "length_um", op, lo=0.0, hi=1e7)
    npat = _int(n_patterns, "n_patterns", op, 1, 1 << 30)
    pol = _int(polarizations, "polarizations", op, 1, 2)
    nz = _num(noise_rel, "noise_rel", op, lo=0.0, hi=10.0, lo_open=False)
    wr = _int(window_rows, "window_rows", op, 3, 1 << 14)
    cal = _num(calib_rms_um, "calib_rms_um", op, lo=0.0, lo_open=False)
    cdof = float(calib_dof)
    if not cdof > 0:
        raise ValueError("%s: calib_dof must be > 0 (numpy.inf for a known constant)" % op)
    q2 = 0.0
    if peak_dn is not None:
        pdn = _num(peak_dn, "peak_dn", op, lo=0.0, hi=1e9)
        q2 = (1.0 / pdn) ** 2 / 12.0
    red = _coherent.speckle_reduction(n_patterns=npat, polarizations=pol)
    C_sp = red["contrast_diversity"] if speckle_contrast is None else _num(
        speckle_contrast, "speckle_contrast", op, lo=0.0, hi=1.0, lo_open=False)
    u_sp = C_sp * lam / (2.0 * math.pi * su) * math.sqrt(w / L)
    ncol = max(1.0, L / pix)
    var_rows = _centroid_noise_var_rows(w / pix, wr) * (nz * nz + q2) / ncol
    u_nz = math.sqrt(var_rows) * pix
    src = np.array(["speckle", "read_noise", "calibration"], dtype=object)
    u = np.array([u_sp, u_nz, cal])
    c = np.array([1.0 / st, 1.0 / st, 1.0])
    dof = np.array([np.inf, np.inf, cdof])
    dz = np.abs(c) * u
    return {"source": src, "u": u, "sensitivity": c, "dof": dof, "delta_z_um": dz,
            "combined_u_z_um": float(np.sqrt(np.sum(dz * dz))),
            "dominant": str(src[int(np.argmax(dz))]),
            "unit": "um", "contrast": C_sp}


def light_section_floor_sweep(parameter, values, n_trials=6, method="centroid", seed=0, **base):
    """Sweep one quantity and return simulated vs closed-form height uncertainty (``table``).

    ``parameter`` は ``wavelength_um`` / ``sin_u_obs`` / ``sin_theta`` / ``n_patterns`` /
    ``noise_rel`` のどれか。値ごとに :func:`light_section_speckle_floor` を回し、シミュの δz、
    閉形式(スペックル + 雑音の二乗和)、比、支配的な成分を並べる。2 点以上で正の値なら
    log-log の傾き(``slope_sim`` / ``slope_closed_form``)も返す(λ: +1、sin u・sin θ: −1 が理論)。

    Runs :func:`light_section_speckle_floor` per value of ``parameter`` and tabulates the simulated
    δz, the closed form (speckle ⊕ noise), their ratio and the dominant term; with two or more
    positive values also the log-log slopes. ``base`` holds the other keyword arguments.
    """
    op = "light_section_floor_sweep"
    if parameter not in SWEEP_PARAMETERS:
        raise ValueError("%s: parameter must be one of %s" % (op, SWEEP_PARAMETERS))
    if parameter in base:
        raise ValueError("%s: %s is both swept and fixed" % (op, parameter))
    vals = list(values) if not isinstance(values, np.ndarray) else values.tolist()
    if not vals:
        raise ValueError("%s: values is empty" % op)
    sim, cf, ratio, dom = [], [], [], []
    for v in vals:
        kw = dict(base)
        kw[parameter] = v
        r = light_section_speckle_floor(method=method, n_trials=n_trials, seed=seed, **kw)
        b = light_section_uncertainty_budget(
            **{k: kw[k] for k in ("wavelength_um", "sin_u_obs", "sin_theta", "line_width_um", "pixel_um",
                                  "length_um", "n_patterns", "polarizations", "noise_rel") if k in kw},
            window_rows=kw.get("n_rows", 160))
        sim.append(r["sim_delta_z_um"])
        cf.append(b["combined_u_z_um"])
        ratio.append(r["sim_delta_z_um"] / b["combined_u_z_um"])
        dom.append(b["dominant"])
    x = np.asarray(vals, dtype=np.float64)
    out = {"parameter": parameter, "values": x, "sim_delta_z_um": np.array(sim),
           "closed_form_delta_z_um": np.array(cf), "ratio": np.array(ratio),
           "dominant": np.array(dom, dtype=object), "method": method}
    if x.size >= 2 and np.all(x > 0) and np.ptp(x) > 0:
        out["slope_sim"] = float(np.polyfit(np.log(x), np.log(out["sim_delta_z_um"]), 1)[0])
        out["slope_closed_form"] = float(np.polyfit(np.log(x), np.log(out["closed_form_delta_z_um"]), 1)[0])
    return out
