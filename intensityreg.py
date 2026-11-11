# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""intensityreg —— 強度による画像の位置合わせ(ECC・相互情報量・B-spline FFD)と、真値による精度の地図 / intensity-based registration.

なぜ足したか(2026-11-03)/ Why
--------------------------------
Fullseye には並進だけの位置合わせ(:func:`aoi.register_image` の位相相関、Fourier-Mellin の相似)と
密な変形の demons(:func:`deformreg.demons_register`)があり、相互情報量は**指標**
(:func:`imgmetrics.mutual_information`)としてだけあった。**アフィン・射影を強度で合わせる
ECC**、**撮像の違う組(可視と赤外など)をアフィンで合わせる MI**、**B-spline の自由変形(FFD)**
が無かった(OpenCV の ``findTransformECC``、ITK / elastix、kornia の ImageRegistrator にある)。

Intensity-based affine/projective alignment (ECC), mutual-information affine registration for
multi-modal pairs, and B-spline free-form deformation were missing. On top of the standard
algorithms this module adds the layer a simulator-backed library can: **per-pixel error maps
against a known deformation** (:func:`register_accuracy_map`) and **capture ranges**
(:func:`register_capture_range`, how far off the initial guess may be).

符号の約束(:mod:`deformreg` と同じ)/ Convention
------------------------------------------------
結果の変形場 ``flow2d`` は ``(2, H, W)`` の ``(dy, dx)`` で、**動く画像の内容の前向き変位**:
``deformreg.warp_by_field(moving, dx, dy)`` が ``fixed`` に重なる。つまり
``warped(p) = moving(p - flow(p))``。demons の ``(fx, fy)`` と同じ向きなので、
demons と FFD と ECC の結果を画素ごとにそのまま比べられる(:func:`register_accuracy_map` がそうする)。

パラメトリックな変換 ``warp`` は 3×3 で、fixed の (x, y) を moving の (x, y) へ写す:
``moving(W p) ≈ fixed(p)``(OpenCV の ``findTransformECC`` の ``warpMatrix`` と同じ向き。
``cv2.warpAffine(moving, W[:2], flags=WARP_INVERSE_MAP)`` が fixed に重なる)。
``flow(p) = p - W p``。

中身 / Contents
---------------
* :func:`register_ecc` —— 強度相関係数の最大化(Evangelidis & Psarakis 2008、前向き加法)。
  並進 / ユークリッド / アフィン / 射影。粗から細のピラミッド(``levels``)は OpenCV に無い追加。
* :func:`register_mi` —— 正規化相互情報量(Studholme 1999)を目的にした剛体 / 相似 / アフィン。
  同時ヒストグラムは動く側を線形に 2 ビンへ振り分ける(パラメータに対して連続にする)。Powell 法。
* :func:`register_ffd` —— 3 次 B-spline の制御格子による自由変形(Rueckert et al. 1999)、SSD + 曲げの罰。
  変形場は分離可能な行列積 ``By C Bxᵀ``、勾配も ``Byᵀ (r ∇M) Bx`` の行列積で解析的に出す。
  最適化は numpy だけで書いた L-BFGS。
* :func:`registration_to_flow2d` —— 結果の表 → ``flow2d``(``piv_flow_magnitude`` などへ繋ぐ)。
* :func:`register_accuracy_map` —— 既知の変形場で合成した組で、推定した場の誤差を画素ごとに返す。
* :func:`register_capture_range` —— 初期のずれの大きさごとの成功率(どこまで外れて始めても戻るか)。

GPU / 経路
----------
重い部分(画像の標本化 ``map_coordinates``、勾配、同時ヒストグラムの ``bincount``、B-spline の行列積、
L-BFGS)は numpy + ``scipy.ndimage`` だけで書いてあり、cv2・skimage を呼ばない。``gpu_shadow``
(CuPy)が同じソースを動かせる形。★``register_mi`` の Powell 法は ``scipy.optimize`` なので、影の
経路では最適化の外側が CPU に残る(実測はしていない)。

呼び出し例 / Example::

    >>> import numpy as np, intensityreg, featmatch
    >>> big = featmatch.synthetic_scene((128, 128), seed=1)
    >>> fixed, moving = big[16:112, 16:112], big[17:113, 14:110]   # moving(x+2, y-1) = fixed(x, y)
    >>> r = intensityreg.register_ecc(fixed, moving, motion="translation")
    >>> [round(float(v), 3) for v in r["warp"][:2, 2]]
    [2.0, -1.0]

参照 / References (public literature, reimplemented):
- G. D. Evangelidis, E. Z. Psarakis, "Parametric image alignment using enhanced correlation coefficient
  maximization", IEEE TPAMI 30(10), 2008.
- P. Viola, W. M. Wells III, "Alignment by maximization of mutual information", IJCV 24(2), 1997.
- F. Maes et al., "Multimodality image registration by maximization of mutual information", IEEE TMI 16(2), 1997.
- C. Studholme, D. L. G. Hill, D. J. Hawkes, "An overlap invariant entropy measure of 3D medical image
  alignment", Pattern Recognition 32(1), 1999.
- D. Rueckert et al., "Nonrigid registration using free-form deformations: application to breast MR
  images", IEEE TMI 18(8), 1999.
- J. Nocedal, "Updating quasi-Newton matrices with limited storage", Math. Comp. 35, 1980 (L-BFGS).
- M. J. D. Powell, "An efficient method for finding the minimum of a function of several variables
  without calculating derivatives", Comput. J. 7(2), 1964.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from featmatch import _image, _pos, _table

__all__ = [
    "register_ecc", "register_mi", "register_ffd", "registration_to_flow2d",
    "register_accuracy_map", "register_capture_range",
    "warp_parametric", "synthesize_moving", "smooth_test_field",
    "ECC_MOTIONS", "MI_MODELS", "MODALITIES", "ACCURACY_METHODS",
]

ECC_MOTIONS = ("translation", "euclidean", "affine", "homography")
MI_MODELS = ("rigid", "similarity", "affine")
MODALITIES = ("same", "inverted", "gamma", "folded")
ACCURACY_METHODS = ("ecc", "mi", "ffd", "demons", "phase")


# ---------------------------------------------------------------------------
# 標本化と変換 / sampling and parametric warps
# ---------------------------------------------------------------------------


def _grid(shape):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float64)
    return yy, xx


def _map(W, xx, yy):
    """3×3 の W で (x, y) を写す。→ (X, Y)。"""
    X = W[0, 0] * xx + W[0, 1] * yy + W[0, 2]
    Y = W[1, 0] * xx + W[1, 1] * yy + W[1, 2]
    den = W[2, 0] * xx + W[2, 1] * yy + W[2, 2]
    if not (W[2, 0] == 0 and W[2, 1] == 0 and W[2, 2] == 1):
        with np.errstate(divide="ignore", invalid="ignore"):
            X, Y = X / den, Y / den
    return X, Y


def _sample(img, X, Y, order=1, mode="constant"):
    out = ndimage.map_coordinates(img, [Y, X], order=order, mode=mode, cval=0.0)
    return np.where(np.isfinite(out), out, 0.0)


def _inside(shape, X, Y):
    return np.isfinite(X) & np.isfinite(Y) & (X >= 0) & (X <= shape[1] - 1) & (Y >= 0) & (Y <= shape[0] - 1)


def warp_parametric(image, W, out_shape=None, order=3):
    """``out(p) = image(W⁻¹ p)``(W は image の (x, y) → out の (x, y) の 3×3)。→ (H, W) float64。

    合成の道具。``order=3`` の 3 次スプライン(位置合わせ側の双線形と違う補間にして、補間の型の
    一致による甘さを避ける)。外側は 0。向きは ``cv2.warpPerspective``(``WARP_INVERSE_MAP`` なし)と
    同じで、有効域の値は ``order=1`` で cv2 の線形と 1.1e-2(cv2 の 1/32 画素の量子化)、``order=3``
    で cv2 の 3 次と 3.4e-2(補間核の違い)以内。

    - 入口: ``image`` は空でない 2-D の有限な配列、``out_shape`` は正の整数 2 つ、``order`` は 0〜5 の
      整数。外れると ``ValueError``。2026-11-09 より前は検査が無く、NaN が 1 画素あると 3 次スプラインの
      前処理が NaN を全画素へ広げ、そのあと非有限を 0 に置き換えるので**全画素 0**(512² で
      262144/262144)を例外なしで返していた。RGB は scipy の RuntimeError、空は空配列だった。
    - 3 次スプラインは段差で行き過ぎる(0/1 の段差で −0.10〜1.10、自然画で −0.036〜1.06)。
      線積分・濃度・個数のように**負にならない量**を引き直すなら ``order=1``(行き過ぎない)。
    - 速さ: 射影の行が (0, 0, 1) のアフィンは ``scipy.ndimage.affine_transform``(2048² の 3 次で
      0.86 s → 0.33 s)。``map_coordinates`` との**ビット一致は W[2,2] = 1 で渡したときだけ**:
      同じ変換を定数倍した同次表現(例えば W を 2.5 倍)では正規化の順が違い、最大 1e-13 の差が
      出る。射影変換は
      ``map_coordinates``。それでも cv2.warpPerspective の 3 次(2048² で 0.03 s)より 1 桁遅い。
    """
    op = "warp_parametric"
    a = np.asarray(image)
    if a.dtype == object or not (np.issubdtype(a.dtype, np.number) or a.dtype == bool):
        raise ValueError("%s: image must be a numeric 2-D array" % op)
    a = a.astype(np.float64)
    if a.ndim != 2:
        raise ValueError("%s: image must be a 2-D gray image, got shape %r (warp each channel "
                         "separately)" % (op, a.shape))
    if a.size == 0:
        raise ValueError("%s: image is empty, got shape %r" % (op, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: image has %d non-finite pixels (NaN/Inf); the cubic spline would "
                         "spread them over the whole output" % (op, int((~np.isfinite(a)).sum())))
    if isinstance(order, bool) or not isinstance(order, (int, np.integer)) or not 0 <= int(order) <= 5:
        raise ValueError("%s: order must be an integer in 0..5, got %r" % (op, order))
    Wm = _as_warp(W, op)
    if out_shape is None:
        shp = a.shape
    else:
        try:
            shp = tuple(int(v) for v in out_shape)
        except (TypeError, ValueError):
            raise ValueError("%s: out_shape must be two positive integers, got %r" % (op, out_shape)) from None
        if len(shp) != 2 or min(shp) <= 0 or any(float(v) != int(v) for v in out_shape):
            raise ValueError("%s: out_shape must be two positive integers, got %r" % (op, out_shape))
    Wi = np.linalg.inv(Wm)
    if Wi[2, 0] == 0 and Wi[2, 1] == 0 and Wi[2, 2] != 0:
        Wi = Wi / Wi[2, 2]
        # (row, col) 座標の行列: row_in = Wi[1,0] x + Wi[1,1] y + Wi[1,2]、col_in = Wi[0,0] x + ...
        M = np.array([[Wi[1, 1], Wi[1, 0]], [Wi[0, 1], Wi[0, 0]]])
        off = np.array([Wi[1, 2], Wi[0, 2]])
        out = ndimage.affine_transform(a, M, offset=off, output_shape=shp, order=int(order),
                                       mode="constant", cval=0.0)
        return out
    yy, xx = _grid(shp)
    X, Y = _map(Wi, xx, yy)
    return _sample(a, X, Y, order=int(order))


def _as_warp(W, op):
    Wm = np.asarray(W, np.float64)
    if Wm.shape == (2, 3):
        Wm = np.vstack([Wm, [0.0, 0.0, 1.0]])
    if Wm.shape != (3, 3) or not np.isfinite(Wm).all():
        raise ValueError("%s: warp must be a finite 2x3 or 3x3 matrix, got shape %r" % (op, np.shape(W)))
    if abs(np.linalg.det(Wm)) < 1e-12:
        raise ValueError("%s: warp is singular" % op)
    return Wm / Wm[2, 2] if Wm[2, 2] != 0 else Wm


def _auto_levels(levels, shape, op, cap=3):
    """``None`` → 最も粗い段が 16 px 以上になる範囲で最大 ``cap`` 段。数なら検証して返す。"""
    if levels is None:
        return max(1, min(cap, int(math.floor(math.log2(min(shape) / 16.0))) + 1))
    lv = _pos(levels, "levels", op, integer=True)
    if min(shape) / 2 ** (lv - 1) < 16:
        raise ValueError("%s: levels=%d leaves the coarsest level under 16 px" % (op, lv))
    return lv


def _pyr_down(a):
    return ndimage.gaussian_filter(a, 1.0, mode="nearest")[::2, ::2]


def _level_warp(W, s):
    """全解像の W → 1/s の段の W(座標 x_l = x / s)。"""
    S = np.diag([1.0 / s, 1.0 / s, 1.0])
    return S @ W @ np.linalg.inv(S)


def _result(method, model, fixed, moving, W=None, flow=None, metric_name="", metric=0.0,
            iterations=0, converged=False, history=(), extra=None):
    """位置合わせの結果の表(全 method で同じ形)。"""
    yy, xx = _grid(fixed.shape)
    if W is not None:
        X, Y = _map(W, xx, yy)
        flow = np.stack([yy - Y, xx - X])
    else:
        Y, X = yy - flow[0], xx - flow[1]
    valid = _inside(moving.shape, X, Y)
    warped = _sample(moving, X, Y, order=1) * valid
    flow = np.where(np.isfinite(flow), flow, 0.0)
    out = {"kind": "registration", "method": method, "model": model,
           "warp": None if W is None else np.asarray(W, np.float64),
           "flow2d": flow.astype(np.float64), "warped": warped, "valid": valid,
           "valid_fraction": float(valid.mean()), "metric_name": metric_name, "metric": float(metric),
           "iterations": int(iterations), "converged": bool(converged),
           "history": [float(h) for h in history], "image_shape": tuple(fixed.shape)}
    if extra:
        out.update(extra)
    return out


# ---------------------------------------------------------------------------
# ECC
# ---------------------------------------------------------------------------


def _ecc_jacobian(motion, W, xx, yy):
    """∂(x', y')/∂p を (N, 2, P) で。"""
    n = xx.size
    x, y = xx.ravel(), yy.ravel()
    if motion == "translation":
        J = np.zeros((n, 2, 2))
        J[:, 0, 0] = 1.0
        J[:, 1, 1] = 1.0
    elif motion == "euclidean":
        th = math.atan2(W[1, 0], W[0, 0])
        c, s = math.cos(th), math.sin(th)
        J = np.zeros((n, 2, 3))
        J[:, 0, 0] = -s * x - c * y
        J[:, 1, 0] = c * x - s * y
        J[:, 0, 1] = 1.0
        J[:, 1, 2] = 1.0
    elif motion == "affine":
        J = np.zeros((n, 2, 6))
        J[:, 0, 0], J[:, 0, 1], J[:, 0, 2] = x, y, 1.0
        J[:, 1, 3], J[:, 1, 4], J[:, 1, 5] = x, y, 1.0
    else:
        den = W[2, 0] * x + W[2, 1] * y + W[2, 2]
        Xp = (W[0, 0] * x + W[0, 1] * y + W[0, 2]) / den
        Yp = (W[1, 0] * x + W[1, 1] * y + W[1, 2]) / den
        J = np.zeros((n, 2, 8))
        J[:, 0, 0], J[:, 0, 1], J[:, 0, 2] = x / den, y / den, 1.0 / den
        J[:, 1, 3], J[:, 1, 4], J[:, 1, 5] = x / den, y / den, 1.0 / den
        J[:, 0, 6], J[:, 0, 7] = -x * Xp / den, -y * Xp / den
        J[:, 1, 6], J[:, 1, 7] = -x * Yp / den, -y * Yp / den
    return J


def _ecc_update(motion, W, dp):
    W = W.copy()
    if motion == "translation":
        W[0, 2] += dp[0]
        W[1, 2] += dp[1]
    elif motion == "euclidean":
        th = math.atan2(W[1, 0], W[0, 0]) + dp[0]
        c, s = math.cos(th), math.sin(th)
        W[:2, :2] = [[c, -s], [s, c]]
        W[0, 2] += dp[1]
        W[1, 2] += dp[2]
    elif motion == "affine":
        W[:2, :] += dp.reshape(2, 3)
    else:
        W.flat[:8] += dp
    return W


def _ecc_mask(W, xx, yy, bt, I, border, motion, op):
    """今の W で照合に使う画素(縁の帯を除き、写った先が moving の内側)。少なすぎれば ValueError。"""
    X, Y = _map(W, xx, yy)
    m = bt & (X >= border) & (X <= I.shape[1] - 1 - border) & (Y >= border) & (Y <= I.shape[0] - 1 - border)
    P = {"translation": 2, "euclidean": 3, "affine": 6, "homography": 8}[motion]
    if m.sum() < 4 * P + 8:
        raise ValueError("%s: the warp moved the template outside the input image "
                         "(%d valid pixels) — the initial guess is too far off" % (op, int(m.sum())))
    return X, Y, m


def _ecc_level(T, I, W, motion, n_iter, eps, op, border=1, nonpositive="raise"):
    gIy, gIx = np.gradient(I)
    yy, xx = _grid(T.shape)
    # 平滑化の届く縁の帯は、外側を折り返した値が混ざって 2 枚で中身が違う(並進でも偏る)ので照合から外す
    bt = np.zeros(T.shape, bool)
    bt[border:T.shape[0] - border, border:T.shape[1] - border] = True
    rho_prev = -np.inf
    hist = []
    converged = False
    it = 0
    for it in range(1, n_iter + 1):
        X, Y, m = _ecc_mask(W, xx, yy, bt, I, border, motion, op)
        Iw = _sample(I, X, Y)[m]
        gx = _sample(gIx, X, Y)[m]
        gy = _sample(gIy, X, Y)[m]
        J = _ecc_jacobian(motion, W, xx[m], yy[m])
        G = gx[:, None] * J[:, 0, :] + gy[:, None] * J[:, 1, :]
        t = T[m]
        tb = t - t.mean()
        ib = Iw - Iw.mean()
        Gb = G - G.mean(0)
        Hs = Gb.T @ Gb
        try:
            Hinv = np.linalg.inv(Hs)
        except np.linalg.LinAlgError:
            raise ValueError("%s: the ECC Hessian is singular (no texture along some warp direction)" % op)
        nt, ni = np.linalg.norm(tb), np.linalg.norm(ib)
        if nt == 0 or ni == 0:
            raise ValueError("%s: the overlap is constant — ECC is undefined" % op)
        corr = float(tb @ ib)
        rho = corr / (nt * ni)
        hist.append(rho)
        if abs(rho - rho_prev) < eps:
            converged = True
            break
        ip = Gb.T @ ib
        tp = Gb.T @ tb
        lam_n = ni * ni - ip @ Hinv @ ip
        lam_d = corr - tp @ Hinv @ ip
        if lam_d > 0:
            lam = lam_n / lam_d
        elif nonpositive == "raise":
            raise ValueError("%s: ECC would not converge (lambda denominator %.3g <= 0) — the images are "
                             "uncorrelated or anti-correlated under this warp (different modality? use "
                             "register_mi, or nonpositive='step' for a poor initial guess)" % (op, lam_d))
        else:
            # 線形化した相関 f(λ) = (a + λb) / sqrt(c + λ²b)(a = lam_d, b = tᵀPt, c = lam_n)は a <= 0 のとき
            # λ について単調増加で最大が無い。λ = max(sqrt(c/b), -2a/b) を取れば分子 >= -a > 0(相関が正に戻る一歩)。
            # Evangelidis & Psarakis 2008 の「分母が正でないときは λ を選び直す」考え方に従う(定数はここでの選択)。
            b_ = float(tp @ Hinv @ tp)
            if b_ <= 0:
                raise ValueError("%s: ECC step undefined (template has no component in the warp subspace)" % op)
            lam = max(math.sqrt(max(lam_n, 0.0) / b_), -2.0 * lam_d / b_)
        err = lam * tb - ib
        dp = Hinv @ (Gb.T @ err)
        W = _ecc_update(motion, W, dp)
        if not np.isfinite(W).all():
            raise ValueError("%s: the warp diverged (non-finite parameters)" % op)
        rho_prev = rho
    return W, hist, it, converged


def _ecc_rho(T, I, W, motion, op, border=1):
    """W での相関係数(:func:`_ecc_level` の反復と同じ画素・同じ定義)。"""
    yy, xx = _grid(T.shape)
    bt = np.zeros(T.shape, bool)
    bt[border:T.shape[0] - border, border:T.shape[1] - border] = True
    X, Y, m = _ecc_mask(W, xx, yy, bt, I, border, motion, op)
    tb = T[m] - T[m].mean()
    ib = _sample(I, X, Y)[m]
    ib = ib - ib.mean()
    nt, ni = np.linalg.norm(tb), np.linalg.norm(ib)
    if nt == 0 or ni == 0:
        raise ValueError("%s: the overlap is constant — ECC is undefined" % op)
    return float(tb @ ib) / (nt * ni)


def register_ecc(fixed, moving, motion="affine", n_iter=200, eps=1e-6, warp_init=None, levels=1,
                 smooth_sigma=1.1, nonpositive="raise", min_rho=0.0):
    """強度相関係数(ECC)を最大にするパラメトリックな変換で moving を fixed に合わせる。→ table(``kind="registration"``)。

    Evangelidis & Psarakis(2008)の前向き加法の反復: 毎回 moving と勾配を今の変換で標本化し、
    急降下画像 ``G = ∇I · ∂W/∂p``(平均を引く)とゼロ平均の 2 枚から、相関係数の 2 次近似の最大へ
    ``Δp`` を解く。相関係数は明るさの**アフィン**な違い(利得とずれ)に不変 —— 負の利得(白黒の反転)
    や折り返しのある対応には効かない(分母が 0 以下になったら ``ValueError``。それには :func:`register_mi`)。

    ``motion``: ``"translation"``(2)/ ``"euclidean"``(3、回転 + 並進)/ ``"affine"``(6)/
    ``"homography"``(8)。``levels > 1`` で粗から細のピラミッド(OpenCV の ``findTransformECC`` には無い
    追加。初期のずれの許容が広がる —— :func:`register_capture_range` で測れる)。

    実測(96×96 の :func:`featmatch.synthetic_scene`、3 次スプラインで合成、``tests/test_intensityreg.py``
    が固定): 並進 (2.5, -1.5) px の誤差 < 0.05 px、アフィンの 4 隅誤差 < 0.1 px、OpenCV 5.0 の
    ``findTransformECC`` と変換の差 < 0.05 px。

    Args:
        fixed: 基準(テンプレート)の 2-D 画像。
        moving: 合わせる 2-D 画像(大きさは違ってよい)。
        motion: :data:`ECC_MOTIONS`。
        n_iter: 段ごとの反復の上限。
        eps: 相関係数の変化がこれ未満で収束。
        warp_init: 初期の変換(2×3 / 3×3、fixed → moving)。``None`` なら恒等。
        levels: ピラミッドの段数(1 = 原寸だけ、``None`` なら最も粗い段が 16 px 以上で最大 3 段)。
        smooth_sigma: 前処理のガウスの σ [px](OpenCV の ``gaussFiltSize=5`` は σ ≈ 1.1)。0 で無し。
        nonpositive: 相関の 2 次近似の分母が 0 以下になったとき(初期値が遠い・撮像が違う)。``"raise"``
            (既定、OpenCV と同じく ``ValueError``)/ ``"step"``(相関を正へ戻す λ を選んで続ける。初期のずれの
            許容が広がることがある —— :func:`register_capture_range` で測れる)。
        min_rho: 収束した相関係数がこれ未満なら ``ValueError``(``"step"`` で白黒反転の組を「合った」と
            返さないための床)。

    Returns:
        dict(``kind="registration"``, ``method="ecc"``)。``warp`` (3,3) / ``flow2d`` (2,H,W) の
        ``(dy, dx)`` / ``warped``(fixed の格子へ戻した moving、外側は 0)/ ``valid`` / ``valid_fraction`` /
        ``metric_name="ecc_rho"`` / ``metric``(**返す warp での**相関係数)/ ``iterations`` / ``converged`` /
        ``history``(反復ごとの、その反復の**更新前の** warp の相関。反復の上限で止まったときは
        ``history[-1]`` は返す warp の値ではなく ``metric`` と違いうる)/ ``model`` / ``image_shape``。

    Raises:
        ValueError: 画像が不正 / ``motion`` が違う / 引数が値域外 / 初期の変換が特異 / 反復が発散 /
            テンプレートが画像の外へ出た / 相関が負で ECC が定義できない(``nonpositive="raise"``)/
            収束した相関が ``min_rho`` 未満。
    """
    op = "register_ecc"
    T = _image(fixed, "fixed", op)
    I = _image(moving, "moving", op)
    if motion not in ECC_MOTIONS:
        raise ValueError("%s: motion must be one of %s, got %r" % (op, ECC_MOTIONS, motion))
    n = _pos(n_iter, "n_iter", op, integer=True)
    e = _pos(eps, "eps", op)
    lv = _auto_levels(levels, T.shape, op)
    sg = _pos(smooth_sigma, "smooth_sigma", op, allow_zero=True)
    if nonpositive not in ("raise", "step"):
        raise ValueError("%s: nonpositive must be 'raise' or 'step', got %r" % (op, nonpositive))
    if isinstance(min_rho, bool) or not isinstance(min_rho, (int, float)) or not -1.0 <= float(min_rho) < 1.0:
        raise ValueError("%s: min_rho must be a number in [-1, 1), got %r" % (op, min_rho))
    W = np.eye(3) if warp_init is None else _as_warp(warp_init, op)
    if motion != "homography" and (W[2, 0] != 0 or W[2, 1] != 0):
        raise ValueError("%s: warp_init has a projective row but motion=%r" % (op, motion))
    Ts = ndimage.gaussian_filter(T, sg, mode="nearest") if sg > 0 else T
    Is = ndimage.gaussian_filter(I, sg, mode="nearest") if sg > 0 else I
    pyr = [(Ts, Is)]
    for _ in range(lv - 1):
        pyr.append((_pyr_down(pyr[-1][0]), _pyr_down(pyr[-1][1])))
    hist_all, it_all, conv = [], 0, False
    for k in range(lv - 1, -1, -1):
        s = 2.0 ** k
        Wl = _level_warp(W, s)
        # 縁の帯: 前処理の 3σ を段の画素に直したもの + ピラミッドの平滑化(σ=1)の分
        bd = int(math.ceil(3.0 * sg / s)) + (3 if k > 0 else 1)
        Wl, hist, it, conv = _ecc_level(pyr[k][0], pyr[k][1], Wl, motion, n, e, op, border=bd,
                                        nonpositive=nonpositive)
        W = np.linalg.inv(np.diag([1 / s, 1 / s, 1.0])) @ Wl @ np.diag([1 / s, 1 / s, 1.0])
        hist_all += hist
        it_all += it
    # ★2026-11-04(外部監査 v0.9.0 F7): history の各値は**更新前の** W の相関なので、反復の上限で抜けると
    #   history[-1] は返す W の相関ではない(報告 0.8242、返した変換の相関 0.9945 —— min_rho=0.9 で正しい
    #   答えを拒否し、逆向きなら悪い答えを通しうる)。metric と min_rho の判定は返す W(最も細かい段の Wl)で
    #   測り直した相関で行う。収束で抜けたときは W が更新されていないので history[-1] と同じ値。
    #   history は従来どおり反復ごとの値(長さ = iterations)のまま。
    rho = (hist_all[-1] if conv else _ecc_rho(pyr[0][0], pyr[0][1], Wl, motion, op, border=bd)) if hist_all else 0.0
    W = W / W[2, 2]
    if hist_all and rho < min_rho:
        raise ValueError("%s: final correlation %.4f is below min_rho %.4f — not aligned" % (op, rho, min_rho))
    return _result("ecc", motion, T, I, W=W, metric_name="ecc_rho", metric=rho,
                   iterations=it_all, converged=conv, history=hist_all)


# ---------------------------------------------------------------------------
# 相互情報量 / mutual information (rigid / similarity / affine)
# ---------------------------------------------------------------------------


def _mi_warp(model, z, c, r):
    """最適化の変数 z(画素の単位にそろえたもの)→ 3×3 の W(fixed → moving、中心 c まわり)。"""
    if model == "rigid":
        th = z[0] / r
        A = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        t = z[1:3]
    elif model == "similarity":
        th, ls = z[0] / r, z[1] / r
        s = math.exp(ls)
        A = s * np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        t = z[2:4]
    else:
        A = np.eye(2) + np.asarray(z[:4]).reshape(2, 2) / r
        t = z[4:6]
    W = np.eye(3)
    W[:2, :2] = A
    W[:2, 2] = c + np.asarray(t) - A @ c
    return W


def _mi_z_from_warp(model, W, c, r):
    A, t = W[:2, :2], W[:2, 2] - c + W[:2, :2] @ c
    if model == "rigid":
        return np.array([math.atan2(A[1, 0], A[0, 0]) * r, t[0], t[1]])
    if model == "similarity":
        return np.array([math.atan2(A[1, 0], A[0, 0]) * r, math.log(math.sqrt(abs(np.linalg.det(A)))) * r,
                         t[0], t[1]])
    return np.concatenate([((A - np.eye(2)) * r).ravel(), t])


def _soft_joint(bf, mv, valid, bins):
    """fixed は硬いビン、moving は隣り合う 2 ビンへ線形に振り分けた同時ヒストグラム(確率)。"""
    v = np.clip(mv, 0.0, 1.0) * (bins - 1)
    b0 = np.floor(v).astype(np.int64)
    b0 = np.minimum(b0, bins - 2)
    w1 = v - b0
    wv = valid.astype(np.float64)
    idx = bf * bins + b0
    J = np.bincount(idx.ravel(), (wv * (1 - w1)).ravel(), bins * bins) \
        + np.bincount((idx + 1).ravel(), (wv * w1).ravel(), bins * bins)
    tot = J.sum()
    return J.reshape(bins, bins) / tot if tot > 0 else None


def _entropy_bits(p):
    q = p[p > 0]
    return float(-(q * np.log2(q)).sum())


def _mi_terms(P):
    ha, hb, hab = _entropy_bits(P.sum(1)), _entropy_bits(P.sum(0)), _entropy_bits(P)
    return ha + hb - hab, (ha + hb) / hab if hab > 0 else 1.0


def register_mi(fixed, moving, model="affine", bins=32, metric="nmi", levels=None, max_iter=2000,
                warp_init=None, min_overlap=0.25):
    """(正規化)相互情報量を最大にする剛体 / 相似 / アフィンで moving を fixed に合わせる。→ table(``kind="registration"``)。

    撮像の違う組(可視と赤外、CT と MR、照明の向きの違う 2 枚)では明るさの対応が線形でも単調でも
    ないので、相関(:func:`register_ecc`)や SSD は使えない。相互情報量は「fixed の明るさを知ると
    moving の明るさがどれだけ当てられるか」なので、対応が**一対一でなくても**(折り返しがあっても)
    合わせられる(Viola & Wells 1997、Maes et al. 1997)。既定の目的は重なりの大きさに鈍い正規化版
    ``(H(A)+H(B))/H(A,B)``(Studholme 1999、1〜2)。

    同時ヒストグラムは fixed を硬いビン、moving を隣り合う 2 ビンへ線形に振り分け(変換のパラメータに
    対して連続)、moving の外へ出た画素は数えない。最適化は Powell 法(微分を使わない)を粗から細の
    ``levels`` 段で。変数は回転・伸縮を画像の半径倍して画素の単位にそろえてある。

    ★:func:`imgmetrics.mutual_information` は**指標**(硬いビン 2 つ、ビットで返す)で、ここの目的関数は
    振り分けのある別の推定量。合わせ終わった組を ``imgmetrics`` で測ると ``metric`` と少し違う。

    Args:
        fixed: 基準の 2-D 画像。
        moving: 合わせる 2-D 画像(撮像が違ってよい)。
        model: :data:`MI_MODELS`。
        bins: ヒストグラムのビン数(2 以上)。
        metric: ``"nmi"``(既定)/ ``"mi"``(ビット)。
        levels: ピラミッドの段数。``None`` なら最も粗い段が 16 px 以上になる範囲で最大 3 段。
        max_iter: 段ごとの Powell の反復の上限。
        warp_init: 初期の変換(2×3 / 3×3、fixed → moving、射影の行は 0)。
        min_overlap: 重なりの割合がこれ未満の変換は目的関数を最悪にする(外へ逃げる解を防ぐ)。

    Returns:
        dict(``kind="registration"``, ``method="mi"``)。鍵は :func:`register_ecc` と同じ。``metric_name`` は
        ``"nmi"`` / ``"mi_bits"``、加えて ``mi_bits`` / ``nmi``(全解像の最後の値)。

    Raises:
        ValueError: 画像が不正 / ``model`` / ``metric`` が違う / 引数が値域外 / 初期の変換が射影 /
            合わせ終わっても重なりが ``min_overlap`` 未満。
    """
    from scipy.optimize import minimize

    op = "register_mi"
    F = _image(fixed, "fixed", op)
    M = _image(moving, "moving", op)
    if model not in MI_MODELS:
        raise ValueError("%s: model must be one of %s, got %r" % (op, MI_MODELS, model))
    if metric not in ("nmi", "mi"):
        raise ValueError("%s: metric must be 'nmi' or 'mi', got %r" % (op, metric))
    nb = _pos(bins, "bins", op, integer=True)
    if nb < 2:
        raise ValueError("%s: bins must be >= 2" % op)
    lv = _auto_levels(levels, F.shape, op)
    mi_ = _pos(max_iter, "max_iter", op, integer=True)
    mo = _pos(min_overlap, "min_overlap", op)
    if mo >= 1:
        raise ValueError("%s: min_overlap must be < 1" % op)
    W0 = np.eye(3) if warp_init is None else _as_warp(warp_init, op)
    if W0[2, 0] != 0 or W0[2, 1] != 0:
        raise ValueError("%s: warp_init must be affine (no projective row)" % op)
    fn = (F - F.min()) / np.ptp(F)
    mn = (M - M.min()) / np.ptp(M)
    pyr = [(fn, mn)]
    for _ in range(lv - 1):
        pyr.append((_pyr_down(pyr[-1][0]), _pyr_down(pyr[-1][1])))
    W = W0
    hist = []
    nfev = 0
    for k in range(lv - 1, -1, -1):
        s = 2.0 ** k
        Fl, Ml = pyr[k]
        yy, xx = _grid(Fl.shape)
        bf = np.minimum((np.clip(Fl, 0, 1) * nb).astype(np.int64), nb - 1)
        c = np.array([(Fl.shape[1] - 1) / 2.0, (Fl.shape[0] - 1) / 2.0])
        r = 0.5 * min(Fl.shape)
        Wl = _level_warp(W, s)

        def cost(z, Fl=Fl, Ml=Ml, xx=xx, yy=yy, bf=bf, c=c, r=r):
            Wz = _mi_warp(model, z, c, r)
            X, Y = _map(Wz, xx, yy)
            v = _inside(Ml.shape, X, Y)
            if v.mean() < mo:
                return 0.0 if metric == "mi" else -1.0
            P = _soft_joint(bf, _sample(Ml, X, Y), v, nb)
            if P is None:
                return 0.0
            mi_b, nmi = _mi_terms(P)
            return -(nmi if metric == "nmi" else mi_b)

        z0 = _mi_z_from_warp(model, Wl, c, r)
        res = minimize(cost, z0, method="Powell", options={"xtol": 1e-3, "ftol": 1e-7, "maxiter": mi_})
        nfev += int(res.nfev)
        hist.append(-float(res.fun))
        Wl = _mi_warp(model, res.x, c, r)
        W = np.linalg.inv(np.diag([1 / s, 1 / s, 1.0])) @ Wl @ np.diag([1 / s, 1 / s, 1.0])
    yy, xx = _grid(F.shape)
    X, Y = _map(W, xx, yy)
    v = _inside(M.shape, X, Y)
    if v.mean() < mo:
        raise ValueError("%s: the final overlap %.3f is below min_overlap %.3f" % (op, v.mean(), mo))
    bf = np.minimum((fn * nb).astype(np.int64), nb - 1)
    mi_b, nmi = _mi_terms(_soft_joint(bf, _sample(mn, X, Y), v, nb))
    return _result("mi", model, F, M, W=W, metric_name="nmi" if metric == "nmi" else "mi_bits",
                   metric=nmi if metric == "nmi" else mi_b, iterations=nfev, converged=bool(res.success),
                   history=hist, extra={"mi_bits": mi_b, "nmi": nmi, "bins": nb})


# ---------------------------------------------------------------------------
# B-spline FFD
# ---------------------------------------------------------------------------


def _bspline3(t):
    a = np.abs(t)
    return np.where(a < 1, 2.0 / 3.0 - a * a + 0.5 * a ** 3, np.where(a < 2, (2 - a) ** 3 / 6.0, 0.0))


def _basis(n, spacing):
    """画素 n 個 × 制御点の 3 次 B-spline の基底行列(制御点 k は (k-1)·spacing の位置)。"""
    nc = int(math.floor((n - 1) / spacing)) + 4
    i = np.arange(n, dtype=np.float64)[:, None] / spacing
    k = np.arange(nc, dtype=np.float64)[None, :] - 1.0
    return _bspline3(i - k)


def _diff_mat(n, order):
    D = np.eye(n)
    for _ in range(order):
        D = D[1:] - D[:-1]
    return D


def _lbfgs(fg, x0, max_iter, m=8, ftol=1e-7):
    """numpy だけの L-BFGS(2 ループ再帰 + Armijo の後退)。→ (x, f, iterations, converged, history)。"""
    x = x0.copy()
    f, g = fg(x)
    S, Y = [], []
    hist = [f]
    conv = False
    k = 0
    for k in range(1, max_iter + 1):
        q = g.copy()
        al = []
        for s, y in zip(reversed(S), reversed(Y)):
            a = (s @ q) / (y @ s)
            q -= a * y
            al.append(a)
        if S:
            q *= (S[-1] @ Y[-1]) / (Y[-1] @ Y[-1])
        else:
            q *= 0.5 / max(np.abs(q).max(), 1e-12)          # 最初の一歩は最大 0.5 px
        for (s, y), a in zip(zip(S, Y), reversed(al)):
            b = (y @ q) / (y @ s)
            q += s * (a - b)
        d = -q
        gd = g @ d
        if not gd < 0:
            S, Y = [], []
            d = -g * (0.5 / max(np.abs(g).max(), 1e-12))
            gd = g @ d
        t = 1.0
        while True:
            xn = x + t * d
            fn, gn = fg(xn)
            if np.isfinite(fn) and fn <= f + 1e-4 * t * gd:
                break
            t *= 0.5
            if t < 1e-8:
                return x, f, k, True, hist                     # これ以上下がらない = 停留
        s, y = xn - x, gn - g
        if y @ s > 1e-12:
            S.append(s)
            Y.append(y)
            if len(S) > m:
                S.pop(0)
                Y.pop(0)
        done = abs(f - fn) <= ftol * max(1.0, abs(f))
        x, f, g = xn, fn, gn
        hist.append(f)
        if done:
            conv = True
            break
    return x, f, k, conv, hist


def _ffd_objective(F, M, spacing, lam, mem=0.0):
    """FFD の目的関数と解析勾配 ``fg(c) -> (E, dE/dc)`` と基底。``c`` は (2, ny, nx) の係数を平らにしたもの。"""
    H, W = F.shape
    By, Bx = _basis(H, spacing), _basis(W, spacing)
    ny, nx = By.shape[1], Bx.shape[1]
    gMy, gMx = np.gradient(M)
    yy, xx = _grid(F.shape)
    N = F.size
    # 差分を画素の単位の微分に直す(制御点の間隔 spacing で割る)。こうしないと罰の効きが間隔の 2 乗で変わる
    D2y, D2x = _diff_mat(ny, 2) / spacing ** 2, _diff_mat(nx, 2) / spacing ** 2
    D1y, D1x = _diff_mat(ny, 1) / spacing, _diff_mat(nx, 1) / spacing
    nreg = 2.0 * ny * nx

    def fg(c):
        C = c.reshape(2, ny, nx)
        wy = By @ C[0] @ Bx.T
        wx = By @ C[1] @ Bx.T
        Ys, Xs = yy + wy, xx + wx
        Mw = _sample(M, Xs, Ys, mode="nearest")
        r = Mw - F
        e = float((r * r).mean())
        # 画像の外は端の値の延長(mode="nearest")= 一定なので、そこの傾きは 0(目的関数と勾配を一致させる)
        ins = _inside(M.shape, Xs, Ys)
        gy = _sample(gMy, Xs, Ys, mode="nearest") * ins
        gx = _sample(gMx, Xs, Ys, mode="nearest") * ins
        gCy = By.T @ ((2.0 / N) * r * gy) @ Bx
        gCx = By.T @ ((2.0 / N) * r * gx) @ Bx
        grad = np.stack([gCy, gCx])
        if lam > 0:
            reg = 0.0
            rg = np.zeros_like(C)
            for j in range(2):
                a = D2y @ C[j]
                b = C[j] @ D2x.T
                cc = D1y @ C[j] @ D1x.T
                reg += (a * a).sum() + (b * b).sum() + 2 * (cc * cc).sum()
                rg[j] = 2 * (D2y.T @ a + b @ D2x + 2 * D1y.T @ cc @ D1x)
            e += lam * reg / nreg
            grad = grad + lam * rg / nreg
        if mem > 0:
            # 膜のエネルギー(1 階微分の 2 乗)。曲げの罰は一様な傾き(伸び・剪断)を罰しないので、模様の無い所で
            # 場が際限なく伸びる。これがその歯止め。
            reg = 0.0
            rg = np.zeros_like(C)
            for j in range(2):
                a = D1y @ C[j]
                b = C[j] @ D1x.T
                reg += (a * a).sum() + (b * b).sum()
                rg[j] = 2 * (D1y.T @ a + b @ D1x)
            e += mem * reg / nreg
            grad = grad + mem * rg / nreg
        return e, grad.ravel()

    return fg, By, Bx


def _ffd_level(F, M, spacing, w0, max_iter, lam, mem=0.0):
    """1 段の FFD。w0 は (2,H,W) の引き戻しの場 w(warped(p) = M(p + w))の初期値。"""
    fg, By, Bx = _ffd_objective(F, M, spacing, lam, mem)
    ny, nx = By.shape[1], Bx.shape[1]
    Byp, Bxp = np.linalg.pinv(By), np.linalg.pinv(Bx)
    C0 = np.stack([Byp @ w0[0] @ Bxp.T, Byp @ w0[1] @ Bxp.T])
    c, f, it, conv, hist = _lbfgs(fg, C0.ravel(), max_iter)
    C = c.reshape(2, ny, nx)
    w = np.stack([By @ C[0] @ Bx.T, By @ C[1] @ Bx.T])
    return w, f, it, conv, hist, (ny, nx)


def register_ffd(fixed, moving, grid_spacing=8, levels=None, max_iter=150, reg_weight=1.0,
                 normalize=True, init_flow2d=None, membrane_weight=0.0, min_coarse_spacing=2.0):
    """3 次 B-spline の自由変形(FFD)で moving を fixed へ非剛体に合わせる。→ table(``kind="registration"``)。

    変形を ``grid_spacing`` px 間隔の制御格子の係数 ``C`` で表し(Rueckert et al. 1999)、場は分離可能な
    行列積 ``w = By C Bxᵀ``(``By``・``Bx`` は 3 次 B-spline の基底行列)。目的は
    ``mean((M(p + w) - F)²) + reg_weight · 曲げの罰``(制御格子の 2 階差分の 2 乗和、``∂²/∂y²``・
    ``∂²/∂x²``・``2 ∂²/∂x∂y``)、勾配は ``Byᵀ (2 r ∇M / N) Bx`` の解析式。最適化は numpy の L-BFGS を
    粗から細のピラミッドで(段を上がるたびに場を 2 倍して細かい基底へ最小二乗で写す)。

    demons(:func:`deformreg.demons_register`)との違い: demons は画素ごとの場をガウスでならす
    (自由度 2HW)、FFD は制御格子の自由度 ``2 · ny · nx`` しか持たず、格子より細かい変形は表せない
    代わりに、模様の無い所でも場が格子の補間で埋まる。どちらが良いかは被写体次第で、
    :func:`register_accuracy_map` が同じ真値で両方を測れる。

    Args:
        fixed: 基準の 2-D 画像。
        moving: 合わせる 2-D 画像(fixed と同じ形)。
        grid_spacing: 制御点の間隔 [px](全解像で)。
        levels: ピラミッドの段数。``None`` なら最も粗い段が 16 px 以上になる範囲で最大 3 段。
        max_iter: 段ごとの L-BFGS の反復の上限。
        reg_weight: 曲げの罰の重み(0 で無し)。罰は場の 2 階微分 [1/px] の 2 乗の制御点平均なので、
            格子間隔を変えても効きが変わらない。
        normalize: 2 枚とも平均 0・分散 1 にしてから比べる(明るさのアフィンな違いを消す。SSD のまま)。
        init_flow2d: 初期の場(``(2,H,W)``、出力と同じ向き)。``None`` なら 0。
        membrane_weight: 1 階微分の 2 乗(膜のエネルギー)の重み(既定 0 = Rueckert 1999 どおり曲げだけ)。
            ★曲げの罰は一様な傾き(伸び・剪断)を罰しないので、**模様の無い所では場が真の振幅の数倍まで
            暴れうる**(``examples/poc_sheet_deformation_ffd.py`` の 6b 節: 余白で最大 34 px、真値 1.5 px)。
            0.1 でそれが 3.6 px に収まる一方、模様のある所の本物の傾きも罰するので、滑らかな大きな場では
            精度が落ちる(``tests/test_intensityreg.py``)。両立しないので既定は 0 のまま。
        min_coarse_spacing: 粗い段での制御点の間隔の下限 [その段の px]。

    Returns:
        dict(``kind="registration"``, ``method="ffd"``)。``warp=None``、``flow2d`` (2,H,W) の ``(dy, dx)``、
        ``metric_name="rms_residual"``(正規化後の残差の rms、罰を含まない)、``grid_shape``(制御格子)、
        ``grid_spacing``。他の鍵は :func:`register_ecc` と同じ。

    限界: 微分同相(折り返し無し)は保証しない。模様の無い所・1 方向にしか模様の無い所(縦縞では縦の成分)の
    場は罰と補間が決めた値で、データの裏付けは無い —— :func:`register_accuracy_map` の ``by_texture`` で見える。

    Raises:
        ValueError: 画像が不正 / 形が違う / 引数が値域外 / ``init_flow2d`` の形が違うか非有限。
    """
    op = "register_ffd"
    F = _image(fixed, "fixed", op)
    M = _image(moving, "moving", op)
    if F.shape != M.shape:
        raise ValueError("%s: fixed and moving must have the same shape, got %r and %r" % (op, F.shape, M.shape))
    sp = _pos(grid_spacing, "grid_spacing", op)
    if sp < 4:
        raise ValueError("%s: grid_spacing must be >= 4 px, got %r" % (op, grid_spacing))
    lv = _auto_levels(levels, F.shape, op)
    mi_ = _pos(max_iter, "max_iter", op, integer=True)
    lam = _pos(reg_weight, "reg_weight", op, allow_zero=True)
    mem = _pos(membrane_weight, "membrane_weight", op, allow_zero=True)
    mcs = _pos(min_coarse_spacing, "min_coarse_spacing", op)
    if not isinstance(normalize, (bool, np.bool_)):
        raise ValueError("%s: normalize must be a bool" % op)
    if init_flow2d is None:
        w = np.zeros((2,) + F.shape)
    else:
        f0 = np.asarray(init_flow2d, np.float64)
        if f0.shape != (2,) + F.shape or not np.isfinite(f0).all():
            raise ValueError("%s: init_flow2d must be a finite (2, H, W) array matching fixed" % op)
        w = -f0
    Fn = (F - F.mean()) / F.std() if normalize else F
    Mn = (M - M.mean()) / M.std() if normalize else M
    pyr = [(Fn, Mn)]
    for _ in range(lv - 1):
        pyr.append((_pyr_down(pyr[-1][0]), _pyr_down(pyr[-1][1])))
    hist_all, it_all, conv = [], 0, False
    wl = None
    for k in range(lv - 1, -1, -1):
        Fl, Ml = pyr[k]
        s = 2.0 ** k
        if wl is None:
            wl = np.stack([w[0][::int(s), ::int(s)], w[1][::int(s), ::int(s)]]) / s
        else:
            # 1 段細かくする: 場を 2 倍の格子へ(双線形)、変位も 2 倍
            yy, xx = _grid(Fl.shape)
            wl = 2.0 * np.stack([ndimage.map_coordinates(wl[j], [yy / 2.0, xx / 2.0], order=1, mode="nearest")
                                 for j in range(2)])
        wl = wl[:, :Fl.shape[0], :Fl.shape[1]]
        wl, f, it, conv, hist, gshape = _ffd_level(Fl, Ml, max(mcs, sp / s), wl, mi_, lam, mem)
        hist_all += hist
        it_all += it
    yy, xx = _grid(F.shape)
    r = _sample(Mn, xx + wl[1], yy + wl[0], mode="nearest") - Fn
    return _result("ffd", "bspline", F, M, flow=-wl, metric_name="rms_residual",
                   metric=float(np.sqrt((r * r).mean())), iterations=it_all, converged=conv, history=hist_all,
                   extra={"grid_shape": tuple(int(g) for g in gshape), "grid_spacing": float(sp)})


def registration_to_flow2d(result):
    """位置合わせの結果の表から変形場 ``flow2d``((2,H,W) の ``(dy, dx)``)を取り出す。→ flow2d。

    向きは :mod:`deformreg` と同じ(動く画像の内容の前向き変位)。``piv_flow_magnitude`` /
    ``piv_vorticity`` / ``flow_to_rgbimage`` など ``flow2d`` を受ける op へ繋ぐための口。

    Args:
        result: :func:`register_ecc` / :func:`register_mi` / :func:`register_ffd` の表。

    Returns:
        ``(2, H, W)`` float64 の ndarray(写し)。

    Raises:
        ValueError: ``kind="registration"`` の表でない / 場の形が違う。
    """
    op = "registration_to_flow2d"
    t = _table(result, "registration", op, "result")
    f = np.asarray(t.get("flow2d"), np.float64)
    if f.ndim != 3 or f.shape[0] != 2 or not np.isfinite(f).all():
        raise ValueError("%s: result has no finite (2, H, W) flow2d" % op)
    return f.copy()


# ---------------------------------------------------------------------------
# 真値による精度の地図と収束の範囲 / accuracy map and capture range (the Fullseye-only layer)
# ---------------------------------------------------------------------------


def smooth_test_field(shape, amplitude=2.0, wavelength=48.0, seed=0):
    """試験用の滑らかな変形場(正弦の重ね合わせ)。→ (2, H, W) の ``(dy, dx)`` [px]。

    向きと位相の違う 3 つの正弦を重ね、最大の変位がちょうど ``amplitude`` px になるように縮める。
    ``amplitude · 2π / wavelength < 1`` なら逆写像が一意(:func:`synthesize_moving` がそれを確かめる)。
    """
    h, w = int(shape[0]), int(shape[1])
    rng = np.random.default_rng(int(seed))
    yy, xx = _grid((h, w))
    f = np.zeros((2, h, w))
    for _ in range(3):
        th = rng.uniform(0, np.pi)
        ph = rng.uniform(0, 2 * np.pi)
        k = 2 * np.pi / float(wavelength)
        u = np.sin(k * (xx * np.cos(th) + yy * np.sin(th)) + ph)
        d = rng.normal(size=2)
        f += d[:, None, None] * u
    mag = np.hypot(f[0], f[1]).max()
    return f * (float(amplitude) / mag if mag > 0 else 0.0)


def _modality(img, modality):
    if modality == "same":
        return img
    if modality == "inverted":
        return 1.0 - img
    if modality == "gamma":
        return np.clip(img, 0, 1) ** 2.2
    return np.sin(np.pi * np.clip(img, 0, 1))        # folded: 0.3 と 0.7 が同じ明るさになる(単調でない)


def synthesize_moving(fixed, true_flow2d, modality="same", noise_sigma=0.0, seed=0, order=3):
    """``warp_by_field(moving, dx, dy) == fixed`` を満たす moving を、既知の場から合成する。→ (moving, valid)。

    moving の画素 q は fixed の点 p(q) の値で、``p = q + flow(p)`` を不動点の反復で解く(場の勾配が
    1 未満なら収束する。残差が 1e-3 px を超えたら逆写像が一意でないとして ``ValueError``)。
    fixed の標本化は 3 次スプライン(``order``)で、位置合わせ側の双線形と補間の型を変えてある。
    ``modality`` で明るさを写し(``"same"`` / ``"inverted"`` = 1 - x / ``"gamma"`` = x^2.2 /
    ``"folded"`` = sin(πx)、単調でない)、``noise_sigma`` のガウス雑音を足す。
    """
    op = "synthesize_moving"
    F = np.asarray(fixed, np.float64)
    g = np.asarray(true_flow2d, np.float64)
    if g.shape != (2,) + F.shape or not np.isfinite(g).all():
        raise ValueError("%s: true_flow2d must be a finite (2, H, W) array matching fixed, got %r"
                         % (op, g.shape))
    if modality not in MODALITIES:
        raise ValueError("%s: modality must be one of %s, got %r" % (op, MODALITIES, modality))
    yy, xx = _grid(F.shape)
    py, px = yy.copy(), xx.copy()
    for _ in range(60):
        fy = ndimage.map_coordinates(g[0], [py, px], order=1, mode="nearest")
        fx = ndimage.map_coordinates(g[1], [py, px], order=1, mode="nearest")
        ny, nx = yy + fy, xx + fx
        delta = max(np.abs(ny - py).max(), np.abs(nx - px).max())
        py, px = ny, nx
        if delta < 1e-6:
            break
    fy = ndimage.map_coordinates(g[0], [py, px], order=1, mode="nearest")
    fx = ndimage.map_coordinates(g[1], [py, px], order=1, mode="nearest")
    res = max(np.abs(py - (yy + fy)).max(), np.abs(px - (xx + fx)).max())
    if res > 1e-3:
        raise ValueError("%s: the field is not invertible (fixed-point residual %.3g px; keep "
                         "|grad flow| < 1)" % (op, res))
    mv = ndimage.map_coordinates(F, [py, px], order=int(order), mode="nearest")
    valid = (py >= 0) & (py <= F.shape[0] - 1) & (px >= 0) & (px <= F.shape[1] - 1)
    lo, hi = F.min(), F.max()
    mv = (np.clip(mv, lo, hi) - lo) / (hi - lo) if hi > lo else mv
    mv = _modality(mv, modality)
    if noise_sigma > 0:
        mv = mv + np.random.default_rng(int(seed)).normal(0.0, float(noise_sigma), mv.shape)
    return np.clip(mv, 0.0, 1.0), valid


def _run_method(method, F, M, kw):
    """method を走らせて推定の場 (2,H,W) と、場が意味を持つ画素の印を返す。"""
    kw = dict(kw or {})
    if method == "ecc":
        kw.setdefault("motion", "affine")
        r = register_ecc(F, M, **kw)
        return r["flow2d"], r["valid"], r
    if method == "mi":
        r = register_mi(F, M, **kw)
        return r["flow2d"], r["valid"], r
    if method == "ffd":
        r = register_ffd(F, M, **kw)
        return r["flow2d"], r["valid"], r
    if method == "demons":
        import deformreg
        _, fx, fy = deformreg.demons_register(F, M, **kw)
        return np.stack([fy, fx]), np.ones(F.shape, bool), {"method": "demons"}
    import aoi
    r = aoi.register_image(F, M, **kw)
    flow = np.stack([np.full(F.shape, -r["dy"]), np.full(F.shape, -r["dx"])])
    return flow, np.ones(F.shape, bool), r


def register_accuracy_map(fixed, true_flow2d, method="ffd", modality="same", noise_sigma=0.0,
                          margin=4, seed=0, method_kwargs=None):
    """既知の変形場で合成した組で、推定した変形場の誤差を画素ごとに返す(精度の地図)。→ table。

    ``fixed`` と真の場 ``true_flow2d`` から :func:`synthesize_moving` で moving を作り(3 次スプライン、
    明るさの写し、雑音)、``method`` で合わせ、推定の場と真の場の差の長さ(終点誤差 EPE [px])を
    画素ごとに返す。答えの真値は合成に使った場そのもので、推定側はそれを知らない。

    ``method``: ``"ffd"`` / ``"demons"``(:func:`deformreg.demons_register`、場の向きは同じ)/
    ``"ecc"`` / ``"mi"``(パラメトリック。滑らかな場はアフィンでしか近似できない —— その近似の誤差も
    地図に出る)/ ``"phase"``(:func:`aoi.register_image`、並進だけ)。

    地図の内訳(どこで壊れるか)として、fixed の勾配の強さの 4 分位ごと・真の変位の大きさの 4 分位ごとの
    EPE の中央値を ``by_texture`` / ``by_magnitude`` に返す(模様の無い所で場が決まらないことが数で出る)。
    4 群は排他的(``[lo, hi)``、最後の群だけ ``[lo, hi]``)で、``n`` の和は集計した画素の数。同値が境界に
    並ぶと群の大きさは 1/4 ずつにならない(全部同じ値なら最後の群に全部)。

    Args:
        fixed: 基準の 2-D 画像。
        true_flow2d: 真の場 ``(2,H,W)`` の ``(dy, dx)``(結果と同じ向き)。逆写像が一意であること(勾配 < 1)。
        method: :data:`ACCURACY_METHODS`。
        modality: :data:`MODALITIES`(``"folded"`` は単調でない明るさ = ECC が効かない組)。
        noise_sigma: moving に足すガウス雑音の σ([0, 1] の尺度)。
        margin: 縁から除く画素数。
        seed: 雑音の種。
        method_kwargs: method へ渡す引数(dict)。

    Returns:
        dict(``kind="registration_accuracy"``)。``error_map`` (H,W) [px](集計から外した画素は 0)/
        ``mask``(集計した画素)/ ``epe_mean`` / ``epe_median`` / ``epe_p95`` / ``epe_max`` /
        ``true_flow2d`` / ``est_flow2d`` / ``moving`` / ``by_texture`` / ``by_magnitude`` / ``method`` /
        ``modality`` / ``noise_sigma`` / ``method_info``(method の返りの要約)。

    Raises:
        ValueError: 画像・場が不正 / 場の逆写像が一意でない / method・modality が違う / method 自身の拒否。
    """
    op = "register_accuracy_map"
    F = _image(fixed, "fixed", op)
    if method not in ACCURACY_METHODS:
        raise ValueError("%s: method must be one of %s, got %r" % (op, ACCURACY_METHODS, method))
    ns = _pos(noise_sigma, "noise_sigma", op, allow_zero=True)
    mg = _pos(margin, "margin", op, integer=True, allow_zero=True)
    if 2 * mg >= min(F.shape):
        raise ValueError("%s: margin %d leaves no pixels" % (op, mg))
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError("%s: seed must be an int" % op)
    g = np.asarray(true_flow2d, np.float64)
    if g.shape != (2,) + F.shape or not np.isfinite(g).all():
        raise ValueError("%s: true_flow2d must be a finite (2, H, W) array matching fixed" % op)
    M, sv = synthesize_moving(F, g, modality=modality, noise_sigma=ns, seed=seed)
    est, ev, info = _run_method(method, F, M, method_kwargs)
    err = np.hypot(est[0] - g[0], est[1] - g[1])
    mask = sv & ev
    yy, xx = _grid(F.shape)
    # 真の場で moving の外から来る画素(fixed の点 p が moving の外へ写る)も除く
    Yq, Xq = yy - g[0], xx - g[1]
    mask &= _inside(F.shape, Xq, Yq)
    if mg:
        mask[:mg] = mask[-mg:] = False
        mask[:, :mg] = mask[:, -mg:] = False
    if not mask.any():
        raise ValueError("%s: no pixel left to score (the field moves everything outside)" % op)
    e = err[mask]
    gy, gx = np.gradient(F)
    gm = np.hypot(gx, gy)[mask]
    tm = np.hypot(g[0], g[1])[mask]

    def by(q, name):
        # ★2026-11-04(外部監査 v0.9.0 F9): 以前は 4 群とも両端を含む [lo, hi] で、境界の値(同値の多い
        #   場では全部)が隣の群にも数えられた(有効 576 画素で各群 576、合計 2304)。群は排他的に:
        #   [lo, hi) で、最後の群だけ最大値を含む [lo, hi]。全部同じ値なら最後の群に全部が入る。
        edges = np.quantile(q, [0, 0.25, 0.5, 0.75, 1.0])
        grp = np.clip(np.searchsorted(edges, q, side="right") - 1, 0, len(edges) - 2)
        rows = []
        for k, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
            sel = grp == k
            rows.append({name + "_lo": float(a), name + "_hi": float(b), "n": int(sel.sum()),
                         "epe_median": float(np.median(e[sel])) if sel.any() else 0.0})
        return rows

    summary = {k: info[k] for k in ("metric_name", "metric", "iterations", "converged", "model")
               if isinstance(info, dict) and k in info}
    return {"kind": "registration_accuracy", "method": method, "modality": modality, "noise_sigma": ns,
            "error_map": np.where(mask, err, 0.0), "mask": mask,
            "epe_mean": float(e.mean()), "epe_median": float(np.median(e)),
            "epe_p95": float(np.quantile(e, 0.95)), "epe_max": float(e.max()),
            "true_flow2d": g, "est_flow2d": est, "moving": M,
            "by_texture": by(gm, "grad"), "by_magnitude": by(tm, "true_px"), "method_info": summary}


def register_capture_range(fixed, method="ecc", offsets_px=(1, 2, 4, 8, 12, 16, 24, 32), n_directions=8,
                           success_px=0.5, rotation_deg=0.0, modality="same", noise_sigma=0.0, margin=8,
                           seed=0, method_kwargs=None):
    """初期のずれの大きさごとに、恒等から始めた位置合わせが真値へ戻る割合を返す(収束の範囲)。→ table。

    大きさ ``d``(``offsets_px``)の並進を ``n_directions`` 方向(+ 任意の回転 ``rotation_deg``)で
    合成し(:func:`synthesize_moving`)、``method`` を**恒等の初期値から**走らせ、内側の画素の EPE の
    平均が ``success_px`` 未満なら成功。method が例外で止まったら失敗として数える(理由を ``failures``
    に数える)。``capture_range_px`` は、それ以下のすべての大きさで成功率が 0.9 以上になる最大の ``d``
    (最小の大きさで届かなければ 0)。

    ECC のような局所の最適化は、ずれが模様の大きさを超えると別の極値に落ちる。位相相関(``"phase"``)は
    大域の探索なので並進には範囲が広いが、回転が入ると崩れる —— 同じ表で比べられる。

    Args:
        fixed: 基準の 2-D 画像。
        method: :data:`ACCURACY_METHODS`。
        offsets_px: 試す並進の大きさ [px] の並び(正、昇順でなくてよい)。
        n_directions: 方向の数。
        success_px: 成功とみなす EPE の平均の上限 [px]。
        rotation_deg: 並進に加える回転(中心まわり、度)。
        modality / noise_sigma / seed / method_kwargs: :func:`register_accuracy_map` と同じ。
        margin: 縁から除く画素数(大きなずれで moving の外から来る画素も除く)。

    Returns:
        dict(``kind="capture_range"``)。``rows``(大きさごとの ``offset_px`` / ``success_rate`` /
        ``median_epe`` / ``n_trials`` / ``failures``)/ ``capture_range_px`` / ``method`` / ``success_px`` /
        ``rotation_deg`` / ``modality``。

    Raises:
        ValueError: 画像が不正 / method・modality が違う / 引数が値域外。
    """
    op = "register_capture_range"
    F = _image(fixed, "fixed", op)
    if method not in ACCURACY_METHODS:
        raise ValueError("%s: method must be one of %s, got %r" % (op, ACCURACY_METHODS, method))
    offs = [float(_pos(o, "offsets_px", op)) for o in offsets_px]
    if not offs:
        raise ValueError("%s: offsets_px is empty" % op)
    nd = _pos(n_directions, "n_directions", op, integer=True)
    sp = _pos(success_px, "success_px", op)
    rot = rotation_deg
    if isinstance(rot, bool) or not isinstance(rot, (int, float)) or not math.isfinite(rot):
        raise ValueError("%s: rotation_deg must be a finite number" % op)
    ns = _pos(noise_sigma, "noise_sigma", op, allow_zero=True)
    mg = _pos(margin, "margin", op, integer=True, allow_zero=True)
    yy, xx = _grid(F.shape)
    c = np.array([(F.shape[1] - 1) / 2.0, (F.shape[0] - 1) / 2.0])
    rows = []
    for d in sorted(offs):
        epes, fails = [], {}
        for k in range(nd):
            ang = 2 * np.pi * (k + 0.25) / nd
            th = math.radians(rot)
            # moving → fixed の向きの変換(fixed の p は moving の W p): 回転 + 並進
            A = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
            t = d * np.array([math.cos(ang), math.sin(ang)])
            X = A[0, 0] * (xx - c[0]) + A[0, 1] * (yy - c[1]) + c[0] + t[0]
            Y = A[1, 0] * (xx - c[0]) + A[1, 1] * (yy - c[1]) + c[1] + t[1]
            g = np.stack([yy - Y, xx - X])
            try:
                M, sv = synthesize_moving(F, g, modality=modality, noise_sigma=ns, seed=seed + k)
                est, ev, _ = _run_method(method, F, M, method_kwargs)
            except ValueError as ex:
                key = str(ex).split(":")[0] + ": " + str(ex).split(":")[1].split("(")[0].strip() \
                    if ":" in str(ex) else str(ex)
                fails[key[:80]] = fails.get(key[:80], 0) + 1
                epes.append(np.inf)
                continue
            mask = sv & ev & _inside(F.shape, X, Y)
            if mg:
                mask[:mg] = mask[-mg:] = False
                mask[:, :mg] = mask[:, -mg:] = False
            epes.append(float(np.hypot(est[0] - g[0], est[1] - g[1])[mask].mean()) if mask.any() else np.inf)
        ep = np.asarray(epes)
        fin = ep[np.isfinite(ep)]
        rows.append({"offset_px": d, "success_rate": float((ep < sp).mean()),
                     "median_epe": float(np.median(fin)) if fin.size else None,
                     "n_trials": int(nd), "failures": fails})
    cap = 0.0
    for r in rows:
        if r["success_rate"] >= 0.9:
            cap = r["offset_px"]
        else:
            break
    return {"kind": "capture_range", "method": method, "rows": rows, "capture_range_px": cap,
            "success_px": sp, "rotation_deg": float(rot), "modality": modality, "noise_sigma": ns,
            "n_directions": nd}
