# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""featmatch —— スケール・回転に強い 2-D 特徴点と照合、頑健推定、条件ごとの精度の表 / scale-invariant features.

なぜ足したか(2026-11-03)/ Why
--------------------------------
Fullseye には特徴点の **数を数える** op(``xcv_orb_count`` など)と、スケール不変ではない
パッチ記述子(:mod:`features`、Harris / FAST + 正規化パッチ + 比の検定)はあったが、
**スケールと回転に不変な記述子と照合**(OpenCV features2d・scikit-image・kornia のどれにもある)が
無かった。部品の位置決め・貼り合わせ・視点の大きく違う 2 枚の対応づけは、ここが土台になる。

Fullseye has had feature *counts* and a non-scale-invariant patch descriptor; the
scale/rotation-invariant detector + descriptor + matcher that every OSS vision library ships
was missing. This module fills it, then adds the layer only a simulator-backed library can:
**accuracy tables against known transforms** (:func:`features_accuracy_table`).

中身 / Contents
---------------
* :func:`features_sift` —— DoG のスケール空間の極値 + 128 次元の勾配方向ヒストグラム(Lowe 2004)。
  特許は 2020-03 に失効(US 6,711,293)。
* :func:`features_orb` —— FAST-9(:func:`features.fast_corners` を再利用)+ Harris で順位 +
  輝度重心の向き + 向きに合わせた BRIEF 256 bit(Rublee et al. 2011)。★学習した rBRIEF の
  対の表は使わない(乱数で固定した対)。
* :func:`features_match` —— 最近傍 + Lowe の比の検定 + 相互最近傍。L2(実数記述子)と Hamming
  (2 値記述子)。実数の照合は :func:`features.match_descriptors` と同じ規則(テストで一致を固定)。
* :func:`ransac_homography` / :func:`ransac_fundamental` —— MSAC(打ち切り二乗の損失)+ 必要回数の
  適応 + 内れ値での局所最適化(LO-RANSAC)。行列の当てはめは既存の正規化 DLT
  (``twoview._homography_dlt``)と正規化 8 点法(:func:`twoview.fundamental_8point`)を再利用する。
* :func:`features_accuracy_table` —— 既知のホモグラフィ・回転・拡大・照明・ぼけ・雑音で合成した
  組で、再現率・照合精度・推定誤差を**条件ごとの表**で返す(どの条件で何が壊れるか)。

型 / Types
----------
新しい型の語は作らない。特徴の集合・照合・推定は ``table``(``kind`` の印つき dict)で、
``kind`` の違う表を渡すと ``ValueError``(取り違えを黙って通さない):

* ``kind="features"`` —— ``xy`` (N,2) の **(x, y)** 画素座標、``scale``(σ、原画像の画素)、
  ``angle``(度、画像座標 = y 下向きで ``atan2(gy, gx)``)、``response``、``descriptors``、
  ``descriptor_kind``(``"float"`` / ``"binary"``)、``detector``、``image_shape``。
* ``kind="feature_matches"`` —— ``idx`` (M,2)、``pts1`` / ``pts2`` (M,2) の (x, y)、``distance``。
* ``kind="homography"`` / ``kind="fundamental"`` —— 行列 + ``inliers`` + 内訳。

GPU / 経路
----------
重い部分(ガウスのスケール空間、極値の 3×3×3 最大値フィルタ、距離行列、RANSAC の一括残差)は
numpy + ``scipy.ndimage`` だけで書いてあり、cv2・skimage を呼ばない。``gpu_shadow``(CuPy の
機械的な GPU 化)が同じソースを動かせる形。キーポイントごとの記述子の組み立ては Python の
ループなので、GPU で速くなるのはスケール空間と照合の側だけ(実測はしていない)。

呼び出し例 / Example::

    >>> import numpy as np, featmatch
    >>> img = featmatch.synthetic_scene((128, 128), seed=3)
    >>> a = featmatch.features_sift(img)
    >>> b = featmatch.features_sift(np.rot90(img).copy())
    >>> m = featmatch.features_match(a, b)
    >>> h = featmatch.ransac_homography(m)
    >>> bool(h["n_inliers"] >= 20)
    True

参照 / References (public literature, reimplemented):
- D. G. Lowe, "Distinctive image features from scale-invariant keypoints", IJCV 60(2), 2004.
- E. Rublee, V. Rabaud, K. Konolige, G. Bradski, "ORB: an efficient alternative to SIFT or SURF", ICCV 2011.
- M. Calonder et al., "BRIEF: Binary Robust Independent Elementary Features", ECCV 2010.
- P. L. Rosin, "Measuring corner properties", CVIU 73(2), 1999 (intensity centroid).
- M. A. Fischler, R. C. Bolles, "Random sample consensus", CACM 24(6), 1981.
- P. H. S. Torr, A. Zisserman, "MLESAC", CVIU 78(1), 2000 (MSAC loss).
- O. Chum, J. Matas, J. Kittler, "Locally optimized RANSAC", DAGM 2003.
- K. Mikolajczyk, C. Schmid, "A performance evaluation of local descriptors", TPAMI 27(10), 2005.
- V. Balntas et al., "HPatches", CVPR 2017 (mean corner error of the homography).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

import features as _features
import twoview as _twoview

__all__ = [
    "features_sift", "features_orb", "features_match",
    "ransac_homography", "ransac_fundamental", "features_accuracy_table",
    "synthetic_scene", "warp_homography", "corner_error", "condition_homography",
    "DEFAULT_CONDITIONS", "HOMOGRAPHY_MODELS",
]

# ---------------------------------------------------------------------------
# 入口の検証 / input validation (fail-closed, English messages)
# ---------------------------------------------------------------------------


def _image(img, name, op, min_side=16):
    """2-D の有限な画像を float64 で返す。定数画像は拒む(特徴が無い)。"""
    a = np.asarray(img)
    if a.dtype == object:
        raise ValueError("%s: %s must be a numeric 2-D array" % (op, name))
    a = a.astype(np.float64)
    if a.ndim != 2:
        raise ValueError("%s: %s must be a 2-D gray image, got shape %r" % (op, name, a.shape))
    if min(a.shape) < min_side:
        raise ValueError("%s: %s must be at least %d px on each side, got %r"
                         % (op, name, min_side, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has non-finite values (NaN/Inf)" % (op, name))
    if float(np.ptp(a)) == 0.0:
        raise ValueError("%s: %s is constant — a flat image has no features" % (op, name))
    return a


def _pos(x, name, op, integer=False, allow_zero=False):
    """正の有限な数(``integer`` なら整数)。bool は拒む。"""
    if isinstance(x, bool) or not isinstance(x, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, x))
    v = float(x)
    if not math.isfinite(v) or v < 0 or (v == 0 and not allow_zero):
        raise ValueError("%s: %s must be a %s finite number, got %r"
                         % (op, name, "non-negative" if allow_zero else "positive", x))
    if integer:
        if v != int(v):
            raise ValueError("%s: %s must be an integer, got %r" % (op, name, x))
        return int(v)
    return v


def _table(t, kind, op, name="table"):
    """``kind`` の印つきの表(dict)であることを確かめる。"""
    if not isinstance(t, dict) or t.get("kind") != kind:
        got = t.get("kind") if isinstance(t, dict) else type(t).__name__
        raise ValueError("%s: %s must be a table with kind=%r, got %r" % (op, name, kind, got))
    return t


# ---------------------------------------------------------------------------
# 合成の道具 / synthesis helpers (used by the accuracy table, the tests and the PoCs)
# ---------------------------------------------------------------------------


def synthetic_scene(shape=(256, 256), seed=0, n_blobs=40, n_rects=25):
    """特徴点の試験に使う、角と斑点と勾配を含む合成の濃淡画像。→ (H, W) float64 in [0, 1]。

    乱数だけの画像は特徴点の位置が雑音で決まり、スケール不変かどうかを試せないので、
    大きさの違う円・回転した矩形・ゆるい勾配を重ねる(大きさの幅 = スケール空間の試験)。
    ``seed`` で決まる(同じ seed なら同じ画像)。
    """
    h, w = int(shape[0]), int(shape[1])
    if h < 16 or w < 16:
        raise ValueError("synthetic_scene: shape must be at least 16x16, got %r" % (shape,))
    rng = np.random.default_rng(int(seed))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    img = 0.35 + 0.15 * (xx / w) + 0.1 * (yy / h)
    s = min(h, w)
    for _ in range(int(n_rects)):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        a, b = rng.uniform(0.03, 0.14) * s, rng.uniform(0.02, 0.09) * s
        th = rng.uniform(0, np.pi)
        u = (xx - cx) * np.cos(th) + (yy - cy) * np.sin(th)
        v = -(xx - cx) * np.sin(th) + (yy - cy) * np.cos(th)
        img = np.where((np.abs(u) < a) & (np.abs(v) < b), rng.uniform(0.0, 1.0), img)
    for _ in range(int(n_blobs)):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(0.01, 0.06) * s
        img = img + rng.uniform(-0.35, 0.35) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))
    img = ndimage.gaussian_filter(img, 0.7)
    lo, hi = img.min(), img.max()
    return (img - lo) / (hi - lo)


def _apply_h(H, xy):
    """(N,2) の (x, y) に 3x3 の射影変換を掛ける。"""
    p = np.asarray(xy, np.float64).reshape(-1, 2)
    q = np.column_stack([p, np.ones(len(p))]) @ np.asarray(H, np.float64).T
    with np.errstate(divide="ignore", invalid="ignore"):
        return q[:, :2] / q[:, 2:3]


def warp_homography(img, H, out_shape=None, order=3, cval=0.0):
    """``out(p) = img(H^-1 p)`` で画像を射影変換する(``H`` は (x, y) の同次座標で img → out)。

    → ``(warped, valid)``。``valid`` は元画像の内側から標本した画素(bool)。``order=3`` は
    3 次スプライン(照合側の双線形と違う補間にして、補間の型が一致する甘さを避ける)。
    """
    a = np.asarray(img, np.float64)
    Hm = np.asarray(H, np.float64)
    if Hm.shape != (3, 3) or not np.isfinite(Hm).all():
        raise ValueError("warp_homography: H must be a finite 3x3 matrix")
    oh, ow = a.shape if out_shape is None else (int(out_shape[0]), int(out_shape[1]))
    yy, xx = np.mgrid[0:oh, 0:ow].astype(np.float64)
    src = _apply_h(np.linalg.inv(Hm), np.column_stack([xx.ravel(), yy.ravel()]))
    sx, sy = src[:, 0].reshape(oh, ow), src[:, 1].reshape(oh, ow)
    out = ndimage.map_coordinates(a, [sy, sx], order=int(order), mode="constant", cval=cval)
    valid = (sx >= 0) & (sx <= a.shape[1] - 1) & (sy >= 0) & (sy <= a.shape[0] - 1)
    return out, valid


def corner_error(H_est, H_true, shape):
    """画像の 4 隅を 2 つのホモグラフィで写したときの距離の平均 [px](HPatches の指標)。"""
    h, w = int(shape[0]), int(shape[1])
    c = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float64)
    d = np.linalg.norm(_apply_h(H_est, c) - _apply_h(H_true, c), axis=1)
    return float(d.mean())


# ---------------------------------------------------------------------------
# SIFT
# ---------------------------------------------------------------------------

_SIFT_BORDER = 5
_SIFT_MAX_INTERP = 5
_SIFT_ORI_BINS = 36
_SIFT_ORI_PEAK = 0.8
_SIFT_D = 4
_SIFT_N = 8
_SIFT_MAG_CLIP = 0.2


def _upsample2(a):
    """2 倍に拡大(双線形、標本点 = i/2 なので拡大後の座標は原画像の 2 倍ちょうど)。"""
    h, w = a.shape
    yy, xx = np.mgrid[0:2 * h - 1, 0:2 * w - 1].astype(np.float64) / 2.0
    return ndimage.map_coordinates(a, [yy, xx], order=1, mode="nearest")


def _gaussian_octaves(base, n_oct, s, sigma0):
    """オクターブごとのガウス像 ``s+3`` 枚と DoG ``s+2`` 枚。"""
    sig = [sigma0]
    k = 2.0 ** (1.0 / s)
    for i in range(1, s + 3):
        prev = sigma0 * k ** (i - 1)
        sig.append(math.sqrt((prev * k) ** 2 - prev ** 2))
    gauss, dogs = [], []
    img = base
    for o in range(n_oct):
        g = [img if o > 0 else img]
        for i in range(1, s + 3):
            g.append(ndimage.gaussian_filter(g[-1], sig[i], mode="nearest"))
        gauss.append(np.stack(g))
        dogs.append(np.stack(g[1:]) - np.stack(g[:-1]))
        img = g[s][::2, ::2]                      # 2σ0 のぼけ = 次のオクターブの土台
        if min(img.shape) < 2 * _SIFT_BORDER + 3:
            break
    return gauss, dogs


def _refine_extrema(D, cand, s, contrast, edge):
    """極値の候補 (layer, y, x) を 2 次の当てはめで副画素へ詰め、低コントラストと稜線を捨てる(一括)。"""
    L, H, W = D.shape
    lay, yy, xx = (c.astype(np.int64) for c in cand)
    n = lay.size
    active = np.ones(n, bool)
    converged = np.zeros(n, bool)
    off = np.zeros((n, 3))
    for _ in range(_SIFT_MAX_INTERP):
        i = np.flatnonzero(active)
        if i.size == 0:
            break
        l, y, x = lay[i], yy[i], xx[i]
        c = D[l, y, x]
        dx = (D[l, y, x + 1] - D[l, y, x - 1]) * 0.5
        dy = (D[l, y + 1, x] - D[l, y - 1, x]) * 0.5
        ds = (D[l + 1, y, x] - D[l - 1, y, x]) * 0.5
        dxx = D[l, y, x + 1] + D[l, y, x - 1] - 2 * c
        dyy = D[l, y + 1, x] + D[l, y - 1, x] - 2 * c
        dss = D[l + 1, y, x] + D[l - 1, y, x] - 2 * c
        dxy = (D[l, y + 1, x + 1] - D[l, y + 1, x - 1] - D[l, y - 1, x + 1] + D[l, y - 1, x - 1]) * 0.25
        dxs = (D[l + 1, y, x + 1] - D[l + 1, y, x - 1] - D[l - 1, y, x + 1] + D[l - 1, y, x - 1]) * 0.25
        dys = (D[l + 1, y + 1, x] - D[l + 1, y - 1, x] - D[l - 1, y + 1, x] + D[l - 1, y - 1, x]) * 0.25
        Hs = np.stack([np.stack([dxx, dxy, dxs], -1), np.stack([dxy, dyy, dys], -1),
                       np.stack([dxs, dys, dss], -1)], -2)
        g = np.stack([dx, dy, ds], -1)
        ok = np.abs(np.linalg.det(Hs)) > 1e-18
        o = np.full_like(g, np.inf)
        if ok.any():
            o[ok] = -np.linalg.solve(Hs[ok], g[ok][..., None])[..., 0]
        bad = ~np.isfinite(o).all(1) | (np.abs(o) > 1e3).any(1)
        active[i[bad]] = False
        good = ~bad
        i, o = i[good], o[good]
        done = (np.abs(o) < 0.5).all(1)
        converged[i[done]] = True
        off[i[done]] = o[done]
        active[i[done]] = False
        im, om = i[~done], o[~done]
        lay[im] += np.round(om[:, 2]).astype(np.int64)
        yy[im] += np.round(om[:, 1]).astype(np.int64)
        xx[im] += np.round(om[:, 0]).astype(np.int64)
        out = (lay[im] < 1) | (lay[im] > s) | (yy[im] < _SIFT_BORDER) | (yy[im] >= H - _SIFT_BORDER) \
            | (xx[im] < _SIFT_BORDER) | (xx[im] >= W - _SIFT_BORDER)
        active[im[out]] = False
    sel = np.flatnonzero(converged)
    if sel.size == 0:
        return np.empty((0, 4)), np.empty(0)
    l, y, x = lay[sel], yy[sel], xx[sel]
    o = off[sel]
    c = D[l, y, x]
    dx = (D[l, y, x + 1] - D[l, y, x - 1]) * 0.5
    dy = (D[l, y + 1, x] - D[l, y - 1, x]) * 0.5
    ds = (D[l + 1, y, x] - D[l - 1, y, x]) * 0.5
    val = c + 0.5 * (dx * o[:, 0] + dy * o[:, 1] + ds * o[:, 2])
    dxx = D[l, y, x + 1] + D[l, y, x - 1] - 2 * c
    dyy = D[l, y + 1, x] + D[l, y - 1, x] - 2 * c
    dxy = (D[l, y + 1, x + 1] - D[l, y + 1, x - 1] - D[l, y - 1, x + 1] + D[l, y - 1, x - 1]) * 0.25
    tr, det = dxx + dyy, dxx * dyy - dxy * dxy
    keep = (np.abs(val) * s >= contrast) & (det > 0) & (tr * tr * edge < (edge + 1) ** 2 * det)
    pts = np.column_stack([l + o[:, 2], y + o[:, 1], x + o[:, 0], l])[keep]
    return pts, np.abs(val[keep])


def _orientations(gimg, y, x, sigma_oct):
    """輝度勾配の向きの 36 ビンのヒストグラムの山(最大の 0.8 倍以上)→ 角度 [rad] のリスト。"""
    H, W = gimg.shape
    rad = int(round(3 * 1.5 * sigma_oct))
    y0, y1 = max(1, y - rad), min(H - 2, y + rad)
    x0, x1 = max(1, x - rad), min(W - 2, x + rad)
    if y1 <= y0 or x1 <= x0:
        return []
    p = gimg[y0 - 1:y1 + 2, x0 - 1:x1 + 2]
    gx = p[1:-1, 2:] - p[1:-1, :-2]
    gy = p[2:, 1:-1] - p[:-2, 1:-1]
    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    wgt = np.exp(-((yy - y) ** 2 + (xx - x) ** 2) / (2 * (1.5 * sigma_oct) ** 2))
    inside = (yy - y) ** 2 + (xx - x) ** 2 <= rad * rad
    mag = np.hypot(gx, gy) * wgt * inside
    ang = np.arctan2(gy, gx) % (2 * np.pi)
    b = np.floor(ang / (2 * np.pi) * _SIFT_ORI_BINS).astype(int) % _SIFT_ORI_BINS
    hist = np.bincount(b.ravel(), mag.ravel(), _SIFT_ORI_BINS)
    hist = (np.roll(hist, 2) + np.roll(hist, -2)) / 16 + (np.roll(hist, 1) + np.roll(hist, -1)) * 4 / 16 \
        + hist * 6 / 16
    mx = hist.max()
    if mx <= 0:
        return []
    out = []
    for k in range(_SIFT_ORI_BINS):
        l, r = hist[k - 1], hist[(k + 1) % _SIFT_ORI_BINS]
        if hist[k] > l and hist[k] > r and hist[k] >= _SIFT_ORI_PEAK * mx:
            d = 0.5 * (l - r) / (l - 2 * hist[k] + r)
            out.append(((k + 0.5 + d) / _SIFT_ORI_BINS * 2 * np.pi) % (2 * np.pi))
    return out


def _sift_descriptor(gimg, y, x, angle, sigma_oct):
    """4x4x8 = 128 次元の SIFT 記述子(三線形の振り分け、0.2 で切って正規化)。"""
    H, W = gimg.shape
    d, n = _SIFT_D, _SIFT_N
    hw = 3.0 * sigma_oct
    rad = int(round(hw * math.sqrt(2) * (d + 1) * 0.5))
    rad = min(rad, int(math.hypot(H, W)))
    cos_t, sin_t = math.cos(angle) / hw, math.sin(angle) / hw
    yi, xi = np.mgrid[-rad:rad + 1, -rad:rad + 1]
    py, px = y + yi, x + xi
    ok = (py > 0) & (py < H - 1) & (px > 0) & (px < W - 1)
    yi, xi, py, px = yi[ok], xi[ok], py[ok], px[ok]
    # 回転した座標(画像座標で y 下向き、角度は atan2(gy, gx))
    c_rot = xi * cos_t + yi * sin_t
    r_rot = -xi * sin_t + yi * cos_t
    rbin = r_rot + d / 2 - 0.5
    cbin = c_rot + d / 2 - 0.5
    inb = (rbin > -1) & (rbin < d) & (cbin > -1) & (cbin < d)
    py, px, rbin, cbin, r_rot, c_rot = py[inb], px[inb], rbin[inb], cbin[inb], r_rot[inb], c_rot[inb]
    gx = gimg[py, px + 1] - gimg[py, px - 1]
    gy = gimg[py + 1, px] - gimg[py - 1, px]
    wgt = np.exp(-(c_rot ** 2 + r_rot ** 2) / (0.5 * d * d))
    mag = np.hypot(gx, gy) * wgt
    ori = (np.arctan2(gy, gx) - angle) % (2 * np.pi)
    obin = ori / (2 * np.pi) * n
    r0, c0, o0 = np.floor(rbin).astype(int), np.floor(cbin).astype(int), np.floor(obin).astype(int)
    dr, dc, do = rbin - r0, cbin - c0, obin - o0
    hist = np.zeros((d + 2, d + 2, n + 2))
    for ir in (0, 1):
        wr = mag * (dr if ir else 1 - dr)
        for ic in (0, 1):
            wc = wr * (dc if ic else 1 - dc)
            for io in (0, 1):
                wo = wc * (do if io else 1 - do)
                np.add.at(hist, (r0 + 1 + ir, c0 + 1 + ic, (o0 + io) % n), wo)
    v = hist[1:d + 1, 1:d + 1, :n].ravel()
    nrm = np.linalg.norm(v)
    if nrm <= 0:
        return None
    v = np.minimum(v, _SIFT_MAG_CLIP * nrm)
    nrm = np.linalg.norm(v)
    return (v / max(nrm, 1e-12)).astype(np.float32)


def features_sift(image, n_octaves=None, n_scales=3, sigma=1.6, contrast_threshold=0.04,
                  edge_threshold=10.0, max_features=2000, double_image=True):
    """SIFT の特徴点と 128 次元の記述子(DoG の極値、Lowe 2004)。→ table(``kind="features"``)。

    DoG(ガウスの差)のスケール空間で 3×3×3 の極値を探し、2 次の当てはめで副画素・副スケールへ
    詰め、低コントラスト(``|D| * n_scales < contrast_threshold``、画像は [0, 1] の尺度)と稜線
    (ヘッセ行列の固有値比が ``edge_threshold`` 超)を捨てる。向きは勾配の 36 ビンの山(最大の
    0.8 倍以上の山ごとに 1 点、同じ位置に複数の向きが出る)、記述子は 4×4 のマス × 8 方向。

    座標の約束: ``xy`` は原画像の **(x, y)** 画素(画素の中心が整数)。``double_image=True`` の
    拡大は標本点 ``i/2`` の双線形なので、拡大後の座標の半分がちょうど原画像の座標になる
    (OpenCV の拡大は画素中心の扱いが違い、点が約 0.25 px ずれる —— 位置を直接比べるときの注意)。

    実測(256×256 の :func:`synthetic_scene`、``tests/test_featmatch.py`` が固定): 90 度回転の対で
    ホモグラフィの 4 隅誤差 < 0.5 px、0.5 倍の縮小で < 1.5 px、OpenCV の SIFT(5.0)と同じ対で
    4 隅誤差が同じ桁。

    限界: 記述子の組み立てはキーポイントごとの Python ループ(2000 点で数秒)。アフィン不変では
    ない(強い遠近では壊れる。:func:`features_accuracy_table` で条件ごとに測れる)。

    Args:
        image: 2-D の濃淡画像(値の尺度は [0, 1] を想定。コントラストのしきい値がこの尺度)。
        n_octaves: オクターブ数。``None`` なら ``log2(min(H, W)) - 3``(最低 1)。
        n_scales: 1 オクターブあたりの尺度の数(Lowe の s、既定 3)。
        sigma: 土台の σ(既定 1.6)。原画像は σ=0.5 のぼけを持つと仮定する。
        contrast_threshold: 低コントラストを捨てるしきい値(既定 0.04)。
        edge_threshold: 稜線を捨てる固有値比 r(既定 10)。
        max_features: 応答の強い順に残す上限。
        double_image: 最初に 2 倍へ拡大するか(既定 True、小さな特徴が拾える)。

    Returns:
        dict(``kind="features"``, ``detector="sift"``)。``xy`` (N,2) / ``scale`` (N,) [px] /
        ``angle`` (N,) [度] / ``response`` (N,) / ``octave`` (N,) / ``descriptors`` (N,128) float32 /
        ``descriptor_kind="float"`` / ``image_shape``。

    Raises:
        ValueError: 2-D でない / 16 px 未満 / 非有限 / 定数画像 / 引数が値域外。
    """
    op = "features_sift"
    img = _image(image, "image", op)
    s = _pos(n_scales, "n_scales", op, integer=True)
    sigma0 = _pos(sigma, "sigma", op)
    contrast = _pos(contrast_threshold, "contrast_threshold", op)
    edge = _pos(edge_threshold, "edge_threshold", op)
    nmax = _pos(max_features, "max_features", op, integer=True)
    if not isinstance(double_image, (bool, np.bool_)):
        raise ValueError("%s: double_image must be a bool, got %r" % (op, double_image))
    if sigma0 <= 2 * 0.5:
        raise ValueError("%s: sigma must exceed 1.0 (twice the assumed camera blur 0.5)" % op)
    base = _upsample2(img) if double_image else img
    blur0 = 1.0 if double_image else 0.5
    base = ndimage.gaussian_filter(base, math.sqrt(sigma0 ** 2 - blur0 ** 2), mode="nearest")
    if n_octaves is None:
        n_oct = max(1, int(round(math.log2(min(base.shape)))) - 3)
    else:
        n_oct = _pos(n_octaves, "n_octaves", op, integer=True)
    gauss, dogs = _gaussian_octaves(base, n_oct, s, sigma0)
    up = 2.0 if double_image else 1.0
    thr = 0.5 * contrast / s
    kp_rows = []
    for o, (G, D) in enumerate(zip(gauss, dogs)):
        mx = ndimage.maximum_filter(D, size=3, mode="nearest")
        mn = ndimage.minimum_filter(D, size=3, mode="nearest")
        ext = ((D == mx) | (D == mn)) & (np.abs(D) > thr)
        ext[0] = ext[-1] = False
        ext[:, :_SIFT_BORDER] = ext[:, -_SIFT_BORDER:] = False
        ext[:, :, :_SIFT_BORDER] = ext[:, :, -_SIFT_BORDER:] = False
        cand = np.nonzero(ext)
        if cand[0].size == 0:
            continue
        pts, resp = _refine_extrema(D, cand, s, contrast, edge)
        for (lay_f, yf, xf, lay_i), r in zip(pts, resp):
            sig_oct = sigma0 * 2.0 ** (lay_f / s)
            gimg = G[int(lay_i)]
            yi, xi = int(round(yf)), int(round(xf))
            for ang in _orientations(gimg, yi, xi, sig_oct):
                kp_rows.append((o, xf, yf, sig_oct, ang, float(r), int(lay_i)))
    if not kp_rows:
        return _empty_features("sift", img.shape, 128, "float")
    kp_rows.sort(key=lambda t: -t[5])
    descs, rows = [], []
    for o, xf, yf, sig_oct, ang, r, li in kp_rows:
        if len(rows) >= nmax:
            break
        G = gauss[o][li]
        dsc = _sift_descriptor(G, int(round(yf)), int(round(xf)), ang, sig_oct)
        if dsc is None:
            continue
        f = 2.0 ** o / up
        rows.append((xf * f, yf * f, sig_oct * f, math.degrees(ang) % 360.0, r, o))
        descs.append(dsc)
    R = np.asarray(rows, np.float64).reshape(-1, 6)
    return {
        "kind": "features", "detector": "sift",
        "xy": R[:, :2].copy(), "scale": R[:, 2].copy(), "angle": R[:, 3].copy(),
        "response": R[:, 4].copy(), "octave": R[:, 5].astype(int),
        "descriptors": np.asarray(descs, np.float32).reshape(-1, 128),
        "descriptor_kind": "float", "image_shape": tuple(img.shape),
    }


def _empty_features(det, shape, dim, dkind):
    dt = np.float32 if dkind == "float" else np.uint8
    return {"kind": "features", "detector": det, "xy": np.empty((0, 2)), "scale": np.empty(0),
            "angle": np.empty(0), "response": np.empty(0), "octave": np.empty(0, int),
            "descriptors": np.empty((0, dim), dt), "descriptor_kind": dkind, "image_shape": tuple(shape)}


# ---------------------------------------------------------------------------
# ORB
# ---------------------------------------------------------------------------

_ORB_PATCH = 31
_ORB_HALF = 15
_ORB_BITS = 256


def _orb_pattern(seed=20111106):
    """BRIEF の比較の対 256 組(等方ガウス σ = 31/5、半径 13 の円に収める)。乱数の種で固定。

    ★Rublee et al. 2011 の **学習した** 対の表(rBRIEF)ではない。向きに合わせて回す steered BRIEF に
    当たり、論文の比較では rBRIEF より分散が小さい(照合の識別力がやや落ちる)。
    """
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < _ORB_BITS:
        p = rng.normal(0.0, _ORB_PATCH / 5.0, size=4)
        if np.hypot(p[0], p[1]) <= 13 and np.hypot(p[2], p[3]) <= 13:
            pts.append(p)
    return np.asarray(pts)


_ORB_PAIRS = _orb_pattern()


def _resize_level(img, scale):
    """1/scale に縮小(前に σ = 0.5·sqrt(scale²-1) のガウスで折り返しを抑える)。"""
    if scale == 1.0:
        return img
    sm = ndimage.gaussian_filter(img, 0.5 * math.sqrt(scale * scale - 1.0), mode="nearest")
    h = max(1, int(round(img.shape[0] / scale)))
    w = max(1, int(round(img.shape[1] / scale)))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    return ndimage.map_coordinates(sm, [yy * scale, xx * scale], order=1, mode="nearest")


def features_orb(image, n_features=1000, n_levels=8, scale_factor=1.2, fast_threshold=0.08,
                 harris_k=0.04):
    """ORB の特徴点と 256 bit の 2 値記述子(Rublee et al. 2011)。→ table(``kind="features"``)。

    縮小の段(``scale_factor`` ずつ ``n_levels`` 段)ごとに FAST-9 の角(:func:`features.fast_corners`
    を再利用)を拾い、Harris の応答で順位をつけて段ごとの割り当て数だけ残す。向きは半径 15 の円の
    輝度重心(Rosin 1999)、記述子はガウス(σ=2)でならした像の上で、向きに合わせて回した 256 組の
    明暗比較。

    ★学習した rBRIEF の対の表は使わない(乱数で固定した対 = steered BRIEF)。OpenCV の ORB の
    記述子とは**ビット単位で一致しない**。比べられるのは「照合して推定したホモグラフィの誤差」まで。

    座標は原画像の **(x, y)**(段の座標 × 段の倍率)。``scale`` は段の倍率 × 31(パッチの一辺)。

    Args:
        image: 2-D の濃淡画像([0, 1] の尺度。``fast_threshold`` がこの尺度)。
        n_features: 全段の合計の上限(段ごとの割り当ては面積に比例する等比数列)。
        n_levels: 段の数。
        scale_factor: 段の縮小率(> 1)。
        fast_threshold: FAST の明暗差のしきい値(既定 0.08 ≈ 20/255)。
        harris_k: Harris の k。

    Returns:
        dict(``kind="features"``, ``detector="orb"``)。``descriptors`` は (N,32) uint8
        (256 bit を詰めたもの)、``descriptor_kind="binary"``。他の鍵は :func:`features_sift` と同じ。

    Raises:
        ValueError: 2-D でない / 16 px 未満 / 非有限 / 定数画像 / 引数が値域外(``scale_factor <= 1`` など)。
    """
    op = "features_orb"
    img = _image(image, "image", op)
    nfeat = _pos(n_features, "n_features", op, integer=True)
    nlev = _pos(n_levels, "n_levels", op, integer=True)
    sf = _pos(scale_factor, "scale_factor", op)
    if sf <= 1.0:
        raise ValueError("%s: scale_factor must be > 1, got %r" % (op, scale_factor))
    fth = _pos(fast_threshold, "fast_threshold", op)
    hk = _pos(harris_k, "harris_k", op)
    # 段ごとの割り当て(面積に比例: n_l ∝ sf^-2l)
    w = sf ** (-2.0 * np.arange(nlev))
    alloc = np.maximum(0, np.round(nfeat * w / w.sum())).astype(int)
    yy, xx = np.mgrid[-_ORB_HALF:_ORB_HALF + 1, -_ORB_HALF:_ORB_HALF + 1]
    circ = (yy * yy + xx * xx) <= _ORB_HALF * _ORB_HALF
    rows, descs = [], []
    for lev in range(nlev):
        scl = sf ** lev
        L = _resize_level(img, scl)
        if min(L.shape) < 2 * _ORB_HALF + 3 or alloc[lev] == 0:
            continue
        kp = _features.fast_corners(L, thresh=fth, min_distance=2, max_n=None, n_contig=9)
        if kp.shape[0] == 0:
            continue
        H, W = L.shape
        b = _ORB_HALF + 3
        kp = kp[(kp[:, 0] >= b) & (kp[:, 0] < H - b) & (kp[:, 1] >= b) & (kp[:, 1] < W - b)]
        if kp.shape[0] == 0:
            continue
        gy, gx = np.gradient(L)
        Ixx = ndimage.gaussian_filter(gx * gx, 1.0)
        Iyy = ndimage.gaussian_filter(gy * gy, 1.0)
        Ixy = ndimage.gaussian_filter(gx * gy, 1.0)
        R = Ixx * Iyy - Ixy * Ixy - hk * (Ixx + Iyy) ** 2
        score = R[kp[:, 0], kp[:, 1]]
        order = np.argsort(-score, kind="stable")[:alloc[lev]]
        kp, score = kp[order], score[order]
        S = ndimage.gaussian_filter(L, 2.0, mode="nearest")
        for (y, x), sc in zip(kp, score):
            patch = L[y - _ORB_HALF:y + _ORB_HALF + 1, x - _ORB_HALF:x + _ORB_HALF + 1]
            m01 = float((patch * yy * circ).sum())
            m10 = float((patch * xx * circ).sum())
            ang = math.atan2(m01, m10)
            c, s_ = math.cos(ang), math.sin(ang)
            P = _ORB_PAIRS
            # (dx, dy) を角度 ang だけ回す(画像座標、y 下向き)
            ax = np.rint(c * P[:, 0] - s_ * P[:, 1]).astype(int)
            ay = np.rint(s_ * P[:, 0] + c * P[:, 1]).astype(int)
            bx = np.rint(c * P[:, 2] - s_ * P[:, 3]).astype(int)
            by = np.rint(s_ * P[:, 2] + c * P[:, 3]).astype(int)
            bits = S[y + ay, x + ax] < S[y + by, x + bx]
            descs.append(np.packbits(bits))
            rows.append((x * scl, y * scl, _ORB_PATCH * scl, math.degrees(ang) % 360.0, float(sc), lev))
    if not rows:
        return _empty_features("orb", img.shape, 32, "binary")
    Rr = np.asarray(rows, np.float64)
    D = np.asarray(descs, np.uint8)
    order = np.argsort(-Rr[:, 4], kind="stable")[:nfeat]
    Rr, D = Rr[order], D[order]
    return {
        "kind": "features", "detector": "orb",
        "xy": Rr[:, :2].copy(), "scale": Rr[:, 2].copy(), "angle": Rr[:, 3].copy(),
        "response": Rr[:, 4].copy(), "octave": Rr[:, 5].astype(int),
        "descriptors": D, "descriptor_kind": "binary", "image_shape": tuple(img.shape),
    }


# ---------------------------------------------------------------------------
# 照合 / matching
# ---------------------------------------------------------------------------

_POPCOUNT = np.array([bin(i).count("1") for i in range(256)], np.uint8)


def _distances(A, B, kind):
    """記述子の距離行列(L2 の 2 乗、または Hamming)。"""
    if kind == "binary":
        out = np.empty((A.shape[0], B.shape[0]), np.float64)
        for i0 in range(0, A.shape[0], 256):
            x = np.bitwise_xor(A[i0:i0 + 256, None, :], B[None, :, :])
            out[i0:i0 + 256] = _POPCOUNT[x].sum(-1)
        return out
    A = A.astype(np.float64)
    B = B.astype(np.float64)
    d = (A ** 2).sum(1)[:, None] + (B ** 2).sum(1)[None, :] - 2.0 * A @ B.T
    return np.maximum(d, 0.0)


def features_match(features1, features2, ratio=0.8, mutual=True, max_distance=None):
    """2 つの特徴の表を最近傍 + 比の検定(+ 相互最近傍)で照合する。→ table(``kind="feature_matches"``)。

    記述子が実数(SIFT)なら L2、2 値(ORB)なら Hamming。1 番目に近い相手が 2 番目より明らかに近い
    (L2 は ``d1 < ratio · d2``、2 乗距離では ``ratio²`` で比べる。Hamming は ``d1 < ratio · d2``)
    ときだけ残し、``mutual=True`` なら相手の側から見ても最近傍であることを求める。

    実数の記述子での規則は :func:`features.match_descriptors` と同じ(同じ入力で同じ組が返ることを
    ``tests/test_featmatch.py`` が固定している)。違いは距離行列を一括で作ること(GPU の影の経路に
    乗る形)と、2 値の記述子を受けること。

    Args:
        features1, features2: :func:`features_sift` / :func:`features_orb` の表。記述子の種類が同じであること。
        ratio: 比の検定のしきい値(0 < ratio <= 1、既定 0.8)。
        mutual: 相互最近傍を求めるか。
        max_distance: 距離の上限(L2 は距離そのもの、Hamming はビット数)。``None`` なら無し。

    Returns:
        dict(``kind="feature_matches"``)。``idx`` (M,2) / ``pts1`` / ``pts2`` (M,2) の (x, y) /
        ``distance`` (M,)(L2 は距離、Hamming はビット数)/ ``ratio_value`` (M,)(d1/d2)/ ``metric`` /
        ``n1`` / ``n2`` / ``image_shape1`` / ``image_shape2``。

    Raises:
        ValueError: 表の種類が違う / 記述子の種類か次元が違う / 引数が値域外。
    """
    op = "features_match"
    f1 = _table(features1, "features", op, "features1")
    f2 = _table(features2, "features", op, "features2")
    if f1["descriptor_kind"] != f2["descriptor_kind"]:
        raise ValueError("%s: descriptor kinds differ (%s vs %s)" % (op, f1["descriptor_kind"],
                                                                     f2["descriptor_kind"]))
    A, B = np.asarray(f1["descriptors"]), np.asarray(f2["descriptors"])
    if A.ndim != 2 or B.ndim != 2 or A.shape[1] != B.shape[1]:
        raise ValueError("%s: descriptor dimensions differ (%r vs %r)" % (op, A.shape, B.shape))
    r = _pos(ratio, "ratio", op)
    if r > 1.0:
        raise ValueError("%s: ratio must be <= 1, got %r" % (op, ratio))
    if not isinstance(mutual, (bool, np.bool_)):
        raise ValueError("%s: mutual must be a bool" % op)
    kind = f1["descriptor_kind"]
    metric = "hamming" if kind == "binary" else "l2"
    empty = {"kind": "feature_matches", "idx": np.empty((0, 2), int), "pts1": np.empty((0, 2)),
             "pts2": np.empty((0, 2)), "distance": np.empty(0), "ratio_value": np.empty(0),
             "metric": metric, "n1": int(A.shape[0]), "n2": int(B.shape[0]),
             "image_shape1": tuple(f1["image_shape"]), "image_shape2": tuple(f2["image_shape"])}
    if A.shape[0] == 0 or B.shape[0] == 0:
        return empty
    d = _distances(A, B, kind)
    if B.shape[0] >= 2:
        nn = np.argpartition(d, 1, axis=1)[:, :2]
        d0, d1_ = d[np.arange(len(d)), nn[:, 0]], d[np.arange(len(d)), nn[:, 1]]
        swap = d1_ < d0
        best = np.where(swap, nn[:, 1], nn[:, 0])
        dbest, dsecond = np.minimum(d0, d1_), np.maximum(d0, d1_)
    else:
        best = np.zeros(A.shape[0], int)
        dbest, dsecond = d[:, 0], np.full(A.shape[0], np.inf)
    # 同じ距離の候補が並ぶときは match_descriptors と同じく argsort の先頭(番号の小さい方)を取る
    tie = dbest == d.min(axis=1)
    first = np.argmin(d, axis=1)
    best = np.where(tie, first, best)
    if metric == "l2":
        passes = np.where(np.isfinite(dsecond), dbest < r * r * dsecond, True)
    else:
        passes = np.where(np.isfinite(dsecond), dbest < r * dsecond, True)
    if mutual:
        back = np.argmin(d, axis=0)
        passes &= back[best] == np.arange(A.shape[0])
    if max_distance is not None:
        md = _pos(max_distance, "max_distance", op, allow_zero=True)
        dist_cmp = np.sqrt(dbest) if metric == "l2" else dbest
        passes &= dist_cmp <= md
    i = np.flatnonzero(passes)
    if i.size == 0:
        return empty
    j = best[i]
    dist = np.sqrt(dbest[i]) if metric == "l2" else dbest[i]
    with np.errstate(divide="ignore", invalid="ignore"):
        rv = np.where(np.isfinite(dsecond[i]) & (dsecond[i] > 0),
                      (np.sqrt(dbest[i] / dsecond[i]) if metric == "l2" else dbest[i] / dsecond[i]), 0.0)
    out = dict(empty)
    out.update(idx=np.column_stack([i, j]).astype(int), pts1=np.asarray(f1["xy"])[i].astype(np.float64),
               pts2=np.asarray(f2["xy"])[j].astype(np.float64), distance=dist.astype(np.float64),
               ratio_value=rv.astype(np.float64))
    return out


# ---------------------------------------------------------------------------
# 頑健推定 / robust estimation (MSAC + adaptive iterations + local optimisation)
# ---------------------------------------------------------------------------


def _homog_fit(p1, p2):
    return _twoview._homography_dlt(p1, p2)


def _translation_fit(p1, p2):
    H = np.eye(3)
    H[:2, 2] = (p2 - p1).mean(0)
    return H


def _similarity_fit(p1, p2):
    """2-D の相似(回転 + 一様な倍率 + 並進)の最小二乗(Umeyama 1991)。"""
    m1, m2 = p1.mean(0), p2.mean(0)
    # ★2026-11-04(外部監査 v0.9.0 F3): 床 ``va <= 1e-12`` [座標²] は座標の単位に依存した(座標 1e-6 の 2 点は常に「退化」)。
    #   退化 = 標本の点が座標の丸めの範囲で重なること(相対量)。広がり ref で割ってから倍率を取る。
    ref = float(np.abs(p1 - m1).max())
    if not ref > 1e-12 * float(np.abs(p1).max()):
        raise ValueError("degenerate sample")
    a, b = (p1 - m1) / ref, (p2 - m2) / ref
    va = (a * a).sum()
    U, S, Vt = np.linalg.svd(b.T @ a)
    D = np.diag([1.0, np.sign(np.linalg.det(U @ Vt))])
    R = U @ D @ Vt
    sc = (S * np.diag(D)).sum() / va
    H = np.eye(3)
    H[:2, :2] = sc * R
    H[:2, 2] = m2 - sc * R @ m1
    return H


def _affine_fit(p1, p2):
    A = np.column_stack([p1, np.ones(len(p1))])
    X, *_ = np.linalg.lstsq(A, p2, rcond=None)
    H = np.eye(3)
    H[:2, :] = X.T
    return H


def _degenerate_affine(p1, p2):
    for P in (p1, p2):
        u, v = P[1] - P[0], P[2] - P[0]
        # ★2026-11-04(外部監査 v0.9.0 F3): 以前は ``< 1e-6 * (1.0 + |u|² + |v|²)`` で、定数 1.0 [px²] が座標の単位に依存した
        #   (座標 1e-6 の三角形は常に「一直線」)。外積と |u|²+|v|² は同じ単位なので比だけで判定する。
        if abs(u[0] * v[1] - u[1] * v[0]) <= 1e-6 * (np.dot(u, u) + np.dot(v, v)):
            return True
    return False


def _degenerate_pair(p1, p2):
    # ★2026-11-04(外部監査 v0.9.0 F3): 以前は絶対の 1e-6 [px]。2 点の重なりは座標の大きさに対する相対量で判定する。
    return bool(any(np.linalg.norm(P[1] - P[0]) <= 1e-9 * float(np.abs(P).max()) for P in (p1, p2)))


def _homog_resid2(H, p1, p2):
    q = _apply_h(H, p1)
    r = ((q - p2) ** 2).sum(1)
    return np.where(np.isfinite(r), r, np.inf)


def _degenerate_h(p1, p2):
    """4 点のうち 3 点が一直線(どちらかの画像で)なら退化。"""
    for P in (p1, p2):
        for a, b, c in ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)):
            u, v = P[b] - P[a], P[c] - P[a]
            if abs(u[0] * v[1] - u[1] * v[0]) <= 1e-6 * (np.dot(u, u) + np.dot(v, v)):   # F3: 相対量(_degenerate_affine)
                return True
    return False


#: 平面の変換の模型 → (最小標本の数, 当てはめ, 退化の判定)
HOMOGRAPHY_MODELS = {
    "translation": (1, _translation_fit, None),
    "similarity": (2, _similarity_fit, _degenerate_pair),
    "affine": (3, _affine_fit, _degenerate_affine),
    "projective": (4, _homog_fit, _degenerate_h),
}


def _fund_fit(p1, p2):
    return _twoview.fundamental_8point(p1, p2)


def _sampson2(F, p1, p2):
    """Sampson 距離の 2 乗 [px²](1 次近似の幾何誤差)。"""
    h1 = np.column_stack([p1, np.ones(len(p1))])
    h2 = np.column_stack([p2, np.ones(len(p2))])
    Fx1 = h1 @ F.T
    Ftx2 = h2 @ F
    num = np.sum(h2 * Fx1, axis=1) ** 2
    den = Fx1[:, 0] ** 2 + Fx1[:, 1] ** 2 + Ftx2[:, 0] ** 2 + Ftx2[:, 1] ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        r = num / den
    return np.where(np.isfinite(r), r, np.inf)


def _ransac(p1, p2, s, fit, resid2, thresh, confidence, max_iters, score, lo, seed, degenerate=None):
    """汎用の RANSAC / MSAC。→ (model, inliers, iterations, cost)。"""
    n = len(p1)
    rng = np.random.default_rng(seed)
    th2 = thresh * thresh
    best_m, best_in, best_cost = None, None, np.inf
    need = max_iters
    it = 0

    def cost_of(r2):
        if score == "msac":
            return float(np.minimum(r2, th2).sum())
        return float(-(r2 < th2).sum())

    while it < min(need, max_iters):
        it += 1
        idx = rng.choice(n, s, replace=False)
        a, b = p1[idx], p2[idx]
        if degenerate is not None and degenerate(a, b):
            continue
        try:
            M = fit(a, b)
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            continue
        if M is None or not np.isfinite(M).all():
            continue
        r2 = resid2(M, p1, p2)
        c = cost_of(r2)
        if c < best_cost:
            inl = r2 < th2
            if lo and inl.sum() > s:
                # 局所最適化: 内れ値で当てはめ直し、良くなる限り繰り返す(Chum 2003)
                for _ in range(4):
                    try:
                        M2 = fit(p1[inl], p2[inl])
                    except (np.linalg.LinAlgError, ValueError, FloatingPointError):
                        break
                    if not np.isfinite(M2).all():
                        break
                    r2b = resid2(M2, p1, p2)
                    c2 = cost_of(r2b)
                    if c2 >= c:
                        break
                    M, r2, c, inl = M2, r2b, c2, r2b < th2
            best_m, best_in, best_cost = M, inl, c
            w = inl.mean()
            if w >= 1.0:
                need = it
            elif w > 0:
                need = int(math.ceil(math.log(1 - confidence) / math.log(1 - w ** s)))
    return best_m, best_in, it, best_cost


def _refit_keeping_consensus(model, inl, fit, resid2, th2, need, p1, p2):
    """全内れ値での当てはめ直しを、合意(内れ値 ``need`` 個以上)を保つときだけ採る。→ (model, r2, inliers)。

    ★2026-11-04(外部監査 v0.9.0 F6): 以前は当てはめ直した模型で内れ値を数え直すだけで、その数を
    ``min_inliers`` と比べ直していなかった(``min_inliers=7`` で 6 個の模型が成功として返った)。
    当てはめ直しで合意が痩せたら、合意を満たしていた RANSAC の模型をそのまま返す
    (``pcseg.fit_sphere_ransac`` と同じ規則)。返す ``inliers`` は常に返す模型の内れ値。
    """
    try:
        M2 = fit(p1[inl], p2[inl])
    except (np.linalg.LinAlgError, ValueError, FloatingPointError):
        M2 = None
    if M2 is not None and np.isfinite(M2).all():
        r2 = resid2(M2, p1, p2)
        inl2 = r2 < th2
        if int(inl2.sum()) >= need:
            return M2, r2, inl2
    r2 = resid2(model, p1, p2)
    return model, r2, r2 < th2


def _ransac_common(matches, op, thresh, confidence, max_iters, score, local_optimization, seed, s):
    m = _table(matches, "feature_matches", op, "matches")
    p1 = np.asarray(m["pts1"], np.float64).reshape(-1, 2)
    p2 = np.asarray(m["pts2"], np.float64).reshape(-1, 2)
    if len(p1) != len(p2):
        raise ValueError("%s: pts1 and pts2 have different lengths" % op)
    if not (np.isfinite(p1).all() and np.isfinite(p2).all()):
        raise ValueError("%s: matches contain non-finite points" % op)
    if len(p1) < s:
        raise ValueError("%s: need at least %d matches, got %d" % (op, s, len(p1)))
    th = _pos(thresh, "thresh", op)
    conf = _pos(confidence, "confidence", op)
    if conf >= 1.0:
        raise ValueError("%s: confidence must be < 1, got %r" % (op, confidence))
    mi = _pos(max_iters, "max_iters", op, integer=True)
    if score not in ("msac", "ransac"):
        raise ValueError("%s: score must be 'msac' or 'ransac', got %r" % (op, score))
    if not isinstance(local_optimization, (bool, np.bool_)):
        raise ValueError("%s: local_optimization must be a bool" % op)
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError("%s: seed must be an int" % op)
    return p1, p2, th, conf, mi


def ransac_homography(matches, thresh=2.0, confidence=0.999, max_iters=5000, score="msac",
                      local_optimization=True, min_inliers=8, seed=0, model="projective"):
    """照合の組から頑健にホモグラフィ(pts1 → pts2、(x, y) の同次座標)を推定する。→ table(``kind="homography"``)。

    4 点の最小標本を引き、前向きの転送誤差 ``|H p1 - p2|`` で採点する。既定の採点は MSAC
    (打ち切り二乗 ``min(r², thresh²)`` の和、Torr & Zisserman 2000)で、内れ値の数だけ数える
    素の RANSAC(``score="ransac"``)より閾値の近くの点の扱いが滑らか。必要な試行回数は
    内れ値の割合から都度見積もり(``confidence``)、良い仮説が出るたびに内れ値で当てはめ直す
    (``local_optimization``、LO-RANSAC)。行列の当てはめは正規化 DLT(``twoview._homography_dlt``、
    Hartley の正規化)を再利用し、退化した標本(3 点が一直線)は捨てる。

    ★既存の ``mosaic.proj_match_points_ransac`` は (row, col) の点・正規化なしの DLT・固定回数で、
    これは (x, y)・正規化 DLT・適応回数・MSAC・LO。座標の順が逆なので混ぜないこと。

    ★**自由度の少ない模型**(``model="translation"`` 1 点 / ``"similarity"`` 2 点 / ``"affine"`` 3 点)を
    選べる。返りはどれも 3×3。正しい組が狭い帯にしか無い(貼り合わせの重なりが細い)とき、8 自由度の
    射影はその帯の組には合うのに帯の外へ大きく外挿を外す(``examples/poc_part_locate_features.py`` の
    5 節: 重なり 80 px・正しい組 9 で、射影は原点の並進を 15 px 外し、相似は 0.1 px 以内)。

    Args:
        matches: :func:`features_match` の表。
        thresh: 内れ値の転送誤差の上限 [px]。
        confidence: 外れ値を含まない標本を少なくとも 1 回引く確率(< 1)。
        max_iters: 試行回数の上限。
        score: ``"msac"`` / ``"ransac"``。
        local_optimization: 内れ値で当てはめ直すか。
        min_inliers: これ未満の内れ値しか集まらなければ失敗(``ValueError``)。
        seed: 標本の乱数の種(同じ種で同じ結果)。
        model: ``"projective"``(既定、8 自由度)/ ``"affine"`` / ``"similarity"`` / ``"translation"``。

    Returns:
        dict(``kind="homography"``)。``H`` (3,3)(``H[2,2] = 1``)/ ``model`` / ``inliers`` (M,) bool /
        ``n_inliers`` / ``inlier_ratio`` / ``rms_px``(内れ値の転送誤差の rms)/ ``iterations`` /
        ``score`` / ``thresh`` / ``image_shape1`` / ``image_shape2``。

    Raises:
        ValueError: 表の種類が違う / 模型の最小標本より少ない / 非有限 / 引数が値域外 / 内れ値が ``min_inliers`` 未満
            (「いちばんましな H」を成功として返さない)。
    """
    op = "ransac_homography"
    if model not in HOMOGRAPHY_MODELS:
        raise ValueError("%s: model must be one of %s, got %r" % (op, tuple(HOMOGRAPHY_MODELS), model))
    ns, fit, degen = HOMOGRAPHY_MODELS[model]
    p1, p2, th, conf, mi = _ransac_common(matches, op, thresh, confidence, max_iters, score,
                                          local_optimization, seed, ns)
    mn = _pos(min_inliers, "min_inliers", op, integer=True)
    H, inl, it, _ = _ransac(p1, p2, ns, fit, _homog_resid2, th, conf, mi, score,
                            local_optimization, int(seed), degen)
    if H is None or int(inl.sum()) < max(ns, mn):
        raise ValueError("%s: no consensus — %d inliers (< %d) within %.3g px after %d iterations"
                         % (op, 0 if inl is None else int(inl.sum()), max(ns, mn), th, it))
    H, r2, inl = _refit_keeping_consensus(H, inl, fit, _homog_resid2, th * th, max(ns, mn), p1, p2)
    H = H / H[2, 2]
    return {"kind": "homography", "H": H, "model": model, "inliers": inl, "n_inliers": int(inl.sum()),
            "inlier_ratio": float(inl.mean()), "rms_px": float(np.sqrt(r2[inl].mean())) if inl.any() else 0.0,
            "iterations": int(it), "score": score, "thresh": th,
            "image_shape1": tuple(matches["image_shape1"]), "image_shape2": tuple(matches["image_shape2"])}


def ransac_fundamental(matches, thresh=1.0, confidence=0.999, max_iters=5000, score="msac",
                       local_optimization=True, min_inliers=15, seed=0):
    """照合の組から頑健に基礎行列 F(``x2ᵀ F x1 = 0``)を推定する。→ table(``kind="fundamental"``)。

    8 点の最小標本を正規化 8 点法(:func:`twoview.fundamental_8point`、rank 2 を強制)で当てはめ、
    Sampson 距離(エピポーラ線までの幾何距離の 1 次近似)で採点する。採点・適応回数・局所最適化は
    :func:`ransac_homography` と同じ。

    限界: 平面の場面や純回転では F は一意に決まらない(ホモグラフィ 1 つで説明できる退化)。
    その判定はしない —— 姿勢まで欲しいなら :func:`twoview.recover_pose`(平面を拒む)へ。
    7 点法は使わない(最小標本は 8)。

    Args:
        matches: :func:`features_match` の表。
        thresh: 内れ値の Sampson 距離の上限 [px]。
        confidence, max_iters, score, local_optimization, seed: :func:`ransac_homography` と同じ。
        min_inliers: これ未満なら失敗(``ValueError``)。

    Returns:
        dict(``kind="fundamental"``)。``F`` (3,3)(フロベニウスノルム 1、符号は ``F[2,2] >= 0``)/
        ``inliers`` / ``n_inliers`` / ``inlier_ratio`` / ``rms_px``(内れ値の Sampson 距離の rms)/
        ``iterations`` / ``score`` / ``thresh``。

    Raises:
        ValueError: 表の種類が違う / 8 組未満 / 非有限 / 引数が値域外 / 内れ値が ``min_inliers`` 未満。
    """
    op = "ransac_fundamental"
    p1, p2, th, conf, mi = _ransac_common(matches, op, thresh, confidence, max_iters, score,
                                          local_optimization, seed, 8)
    mn = _pos(min_inliers, "min_inliers", op, integer=True)
    F, inl, it, _ = _ransac(p1, p2, 8, _fund_fit, _sampson2, th, conf, mi, score,
                            local_optimization, int(seed))
    if F is None or int(inl.sum()) < max(8, mn):
        raise ValueError("%s: no consensus — %d inliers (< %d) within %.3g px after %d iterations"
                         % (op, 0 if inl is None else int(inl.sum()), max(8, mn), th, it))
    F, r2, inl = _refit_keeping_consensus(F, inl, _fund_fit, _sampson2, th * th, max(8, mn), p1, p2)
    F = F / np.linalg.norm(F)
    if F[2, 2] < 0:
        F = -F
    return {"kind": "fundamental", "F": F, "inliers": inl, "n_inliers": int(inl.sum()),
            "inlier_ratio": float(inl.mean()), "rms_px": float(np.sqrt(r2[inl].mean())) if inl.any() else 0.0,
            "iterations": int(it), "score": score, "thresh": th}


# ---------------------------------------------------------------------------
# 精度の表 / accuracy table against known transforms (the Fullseye-only layer)
# ---------------------------------------------------------------------------

#: 既定の条件(名前 → 合成の引数)。順番はそのまま表の行の順。
DEFAULT_CONDITIONS = (
    ("identity", {}),
    ("rotate_15", {"rotate_deg": 15.0}),
    ("rotate_45", {"rotate_deg": 45.0}),
    ("rotate_90", {"rotate_deg": 90.0}),
    ("scale_0.5", {"scale": 0.5}),
    ("scale_0.7", {"scale": 0.7}),
    ("scale_1.4", {"scale": 1.4}),
    ("scale_2.0", {"scale": 2.0}),
    ("perspective_low", {"perspective": 0.0006}),
    ("perspective_high", {"perspective": 0.0018}),
    ("gain_0.5", {"gain": 0.5}),
    ("gamma_2.2", {"gamma": 2.2}),
    ("blur_1", {"blur_sigma": 1.0}),
    ("blur_2", {"blur_sigma": 2.0}),
    ("blur_4", {"blur_sigma": 4.0}),
    ("noise_0.02", {"noise_sigma": 0.02}),
    ("noise_0.05", {"noise_sigma": 0.05}),
    ("noise_0.10", {"noise_sigma": 0.10}),
)

_COND_KEYS = ("rotate_deg", "scale", "perspective", "gain", "gamma", "blur_sigma", "noise_sigma")


def condition_homography(shape, rotate_deg=0.0, scale=1.0, perspective=0.0):
    """画像の中心まわりの回転・拡大・遠近のホモグラフィ(img1 → img2、(x, y))。"""
    h, w = shape
    c = np.array([(w - 1) / 2.0, (h - 1) / 2.0])
    T = np.array([[1, 0, -c[0]], [0, 1, -c[1]], [0, 0, 1.0]])
    Ti = np.array([[1, 0, c[0]], [0, 1, c[1]], [0, 0, 1.0]])
    t = math.radians(rotate_deg)
    R = np.array([[scale * math.cos(t), -scale * math.sin(t), 0],
                  [scale * math.sin(t), scale * math.cos(t), 0], [0, 0, 1.0]])
    P = np.array([[1, 0, 0], [0, 1, 0], [perspective, 0.5 * perspective, 1.0]])
    return Ti @ P @ R @ T


def _synth_pair(img, cond, seed):
    H = condition_homography(img.shape, cond.get("rotate_deg", 0.0), cond.get("scale", 1.0),
                             cond.get("perspective", 0.0))
    out, valid = warp_homography(img, H, order=3)
    out = np.clip(out, 0.0, 1.0)
    out = cond.get("gain", 1.0) * out
    if cond.get("gamma", 1.0) != 1.0:
        out = np.clip(out, 0, 1) ** cond["gamma"]
    if cond.get("blur_sigma", 0.0) > 0:
        out = ndimage.gaussian_filter(out, cond["blur_sigma"], mode="nearest")
    if cond.get("noise_sigma", 0.0) > 0:
        out = out + np.random.default_rng(seed).normal(0.0, cond["noise_sigma"], out.shape)
    out = np.clip(out, 0.0, 1.0) * valid
    return out, H


def features_accuracy_table(image, detector="sift", conditions=None, tol_px=2.0, ransac_thresh=2.0,
                            seed=0, detector_kwargs=None):
    """既知の変換で合成した組で、特徴点の再現率・照合精度・ホモグラフィの誤差を条件ごとに表で返す。→ table。

    ``image`` を条件ごとの既知のホモグラフィ ``H_true``(中心まわりの回転・拡大・遠近)で写し
    (3 次スプライン補間 —— 照合側と違う補間で、補間の型が一致する甘さを避ける)、照明(利得・
    ガンマ)・ぼけ・雑音を足した 2 枚目を作る。2 枚とも検出 → 記述 → :func:`features_match` →
    :func:`ransac_homography` を走らせ、**合成に使った真の H** で答え合わせする:

    * ``repeatability`` —— 2 枚の共通の領域にある 1 枚目の点のうち、``H_true`` で写した位置から
      ``tol_px`` 以内に 2 枚目の点があるものの割合(Mikolajczyk & Schmid 2005 の考え方を点の距離で。
      領域の重なりではない)。
    * ``precision`` —— 照合の組のうち ``|H_true p1 - p2| < tol_px`` のものの割合。
    * ``matching_score`` —— 正しい照合の数 / 共通の領域にある 1 枚目の点の数。
    * ``corner_error_px`` —— 推定した H と真の H で 4 隅を写したときの距離の平均(HPatches)。
      RANSAC が合意に届かなければ ``homography_ok=False`` で ``corner_error_px=None``。

    答えの真値は合成のパラメータそのもので、推定側はそれを知らない(使った式で答え合わせする門
    ではない)。限界: 平面の射影変換だけ(視差・遮蔽・鏡面反射は入らない)。照明はこの画像全体に
    一様(局所の影は入らない)。

    Args:
        image: 2-D の濃淡画像 [0, 1]。模様の乏しい画像では行がほとんど 0 になる(それも結果)。
        detector: ``"sift"`` / ``"orb"``。
        conditions: ``None`` なら :data:`DEFAULT_CONDITIONS`。条件名の並び(既定の名前から選ぶ)か、
            ``(名前, {rotate_deg, scale, perspective, gain, gamma, blur_sigma, noise_sigma})`` の並び。
        tol_px: 正しい対応とみなす距離 [px]。
        ransac_thresh: :func:`ransac_homography` の ``thresh``。
        seed: 雑音と RANSAC の乱数の種。
        detector_kwargs: 検出器へ渡す追加の引数(dict)。

    Returns:
        dict(``kind="feature_accuracy"``)。``rows``(条件ごとの dict の list)/ ``columns`` /
        ``detector`` / ``tol_px`` / ``image_shape`` / ``n_conditions`` /
        ``worst``(``corner_error_px`` が最大か失敗した条件の名前)。

    Raises:
        ValueError: 画像が不正 / 検出器の名前が違う / 条件の名前・鍵・値が不正。
    """
    op = "features_accuracy_table"
    img = _image(image, "image", op, min_side=32)
    if detector not in ("sift", "orb"):
        raise ValueError("%s: detector must be 'sift' or 'orb', got %r" % (op, detector))
    tol = _pos(tol_px, "tol_px", op)
    rth = _pos(ransac_thresh, "ransac_thresh", op)
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise ValueError("%s: seed must be an int" % op)
    dk = {} if detector_kwargs is None else dict(detector_kwargs)
    det = features_sift if detector == "sift" else features_orb
    defaults = dict(DEFAULT_CONDITIONS)
    if conditions is None:
        conds = list(DEFAULT_CONDITIONS)
    else:
        conds = []
        for c in conditions:
            if isinstance(c, str):
                if c not in defaults:
                    raise ValueError("%s: unknown condition %r (known: %s)" % (op, c, ", ".join(defaults)))
                conds.append((c, defaults[c]))
            else:
                name, spec = c
                bad = set(spec) - set(_COND_KEYS)
                if bad:
                    raise ValueError("%s: unknown condition keys %s" % (op, sorted(bad)))
                for k, v in spec.items():
                    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                        raise ValueError("%s: condition %r: %s must be a finite number" % (op, name, k))
                if spec.get("scale", 1.0) <= 0 or spec.get("gain", 1.0) <= 0 or spec.get("gamma", 1.0) <= 0:
                    raise ValueError("%s: condition %r: scale, gain and gamma must be > 0" % (op, name))
                conds.append((str(name), dict(spec)))
    if not conds:
        raise ValueError("%s: conditions is empty" % op)
    f1 = det(img, **dk)
    h, w = img.shape
    m = max(4.0, tol)
    rows = []
    for k, (name, spec) in enumerate(conds):
        img2, Ht = _synth_pair(img, spec, seed + k)
        row = {"condition": name, "n_kp1": int(len(f1["xy"]))}
        row.update({key: float(spec.get(key, 0.0 if key in ("rotate_deg", "perspective", "blur_sigma",
                                                              "noise_sigma") else 1.0)) for key in _COND_KEYS})
        try:
            f2 = det(img2, **dk)
        except ValueError:
            f2 = _empty_features(detector, img.shape, f1["descriptors"].shape[1], f1["descriptor_kind"])
        row["n_kp2"] = int(len(f2["xy"]))
        # 共通の領域: 1 枚目の点を H で写して 2 枚目の内側(縁から m px)に来るもの
        p1 = np.asarray(f1["xy"])
        q1 = _apply_h(Ht, p1) if len(p1) else np.empty((0, 2))
        inside = (q1[:, 0] >= m) & (q1[:, 0] <= w - 1 - m) & (q1[:, 1] >= m) & (q1[:, 1] <= h - 1 - m) \
            if len(q1) else np.zeros(0, bool)
        n_common = int(inside.sum())
        p2 = np.asarray(f2["xy"])
        if n_common and len(p2):
            dmin = np.sqrt(((q1[inside][:, None, :] - p2[None, :, :]) ** 2).sum(-1)).min(1)
            rep = float((dmin < tol).mean())
        else:
            rep = 0.0
        row.update(n_common=n_common, repeatability=rep)
        mt = features_match(f1, f2)
        nm = int(len(mt["idx"]))
        if nm:
            err = np.linalg.norm(_apply_h(Ht, mt["pts1"]) - mt["pts2"], axis=1)
            ncor = int((err < tol).sum())
            # matching_score の分子は分母(共通の領域の点)と同じ集合で数える(縁の外の点を数えると 1 を超える)
            ncor_common = int(((err < tol) & inside[mt["idx"][:, 0]]).sum())
        else:
            ncor = ncor_common = 0
        row.update(n_matches=nm, n_correct=ncor, precision=(ncor / nm) if nm else 0.0,
                   matching_score=(ncor_common / n_common) if n_common else 0.0)
        try:
            hr = ransac_homography(mt, thresh=rth, seed=seed)
            row.update(homography_ok=True, n_inliers=hr["n_inliers"],
                       corner_error_px=corner_error(hr["H"], Ht, img.shape))
        except ValueError:
            row.update(homography_ok=False, n_inliers=0, corner_error_px=None)
        rows.append(row)
    worst = max(rows, key=lambda r: np.inf if r["corner_error_px"] is None else r["corner_error_px"])
    cols = ["condition", *_COND_KEYS, "n_kp1", "n_kp2", "n_common", "repeatability", "n_matches",
            "n_correct", "precision", "matching_score", "homography_ok", "n_inliers", "corner_error_px"]
    return {"kind": "feature_accuracy", "detector": detector, "rows": rows, "columns": cols,
            "tol_px": tol, "image_shape": tuple(img.shape), "n_conditions": len(rows),
            "worst": worst["condition"]}
