"""HALCON coverage 拡充 tier(``hx_`` prefix)— 未カバーの実 HALCON operator を genuine に実装.

各 op は `data/halcon_operators.json` に実在し **これまで未カバー**だった operator の本物の機能を
自作 numpy で実装する(名前 provenance は halcon_coverage.py が dangling 検出で検証)。契約は
既存 registry と同じ ``fn(v, a, b)``(v=[0,1] の 2D 画像 or 二値 region、a/b=[0,1] の進化ノブ)。

追加(実 HALCON 名 → 機能):
  Regions 生成: gen_circle / gen_ellipse / gen_rectangle2 / gen_checker_region / gen_grid_region
  Filters:      convol_gabor(Gabor フィルタ)
  Image:        fit_surface_first_order / fit_surface_second_order(gray 値の多項式面近似=照明推定)
                cooc_feature_image(GLCM 共起行列テクスチャ特徴)/ full_domain(定義域を全面に)
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _grid(shape):
    h, w = shape
    Y, X = np.mgrid[0:h, 0:w].astype(np.float64)
    return h, w, Y, X


def _norm01(v):
    v = np.asarray(v, dtype=np.float64)
    lo, hi = float(v.min()), float(v.max())
    return (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)


# ── Regions 生成(fn(v,a,b) -> 二値 region。v.shape を画布に、a/b を幾何パラメータに)──── #
def _gen_circle(v, a, b):
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    r = (0.1 + 0.4 * a) * min(h, w)
    return ((Y - cy) ** 2 + (X - cx) ** 2 <= r * r).astype(np.float64)


def _gen_ellipse(v, a, b):
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    ra = (0.1 + 0.4 * a) * w / 2 + 1e-6
    rb = (0.1 + 0.4 * b) * h / 2 + 1e-6
    return (((X - cx) / ra) ** 2 + ((Y - cy) / rb) ** 2 <= 1.0).astype(np.float64)


def _gen_rectangle2(v, a, b):
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    th = b * np.pi
    dx, dy = X - cx, Y - cy
    xr = np.cos(th) * dx + np.sin(th) * dy
    yr = -np.sin(th) * dx + np.cos(th) * dy
    hw = (0.1 + 0.4 * a) * w / 2
    hh = (0.06 + 0.24 * a) * h / 2
    return ((np.abs(xr) <= hw) & (np.abs(yr) <= hh)).astype(np.float64)


def _gen_checker_region(v, a, b):
    h, w, Y, X = _grid(v.shape)
    cell = max(2, int((0.05 + 0.2 * a) * min(h, w)))
    return (((X.astype(int) // cell) + (Y.astype(int) // cell)) % 2 == 0).astype(np.float64)


def _gen_grid_region(v, a, b):
    h, w, Y, X = _grid(v.shape)
    step = max(2, int((0.05 + 0.2 * a) * min(h, w)))
    return ((X.astype(int) % step == 0) | (Y.astype(int) % step == 0)).astype(np.float64)


# ── Filters: Gabor ─────────────────────────────────────────────────────────── #
def _convol_gabor(v, a, b):
    """Gabor フィルタ(方位 theta=a*pi、周波数 freq=b)。応答の大きさを返す。"""
    theta = a * np.pi
    freq = 0.08 + 0.35 * b
    sigma = 2.2
    r = 4
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float64)
    xr = xx * np.cos(theta) + yy * np.sin(theta)
    yr = -xx * np.sin(theta) + yy * np.cos(theta)
    envelope = np.exp(-(xr ** 2 + yr ** 2) / (2 * sigma ** 2))
    kernel = envelope * np.cos(2 * np.pi * freq * xr)
    kernel -= kernel.mean()                              # DC 除去(平坦部で 0)
    resp = ndimage.convolve(v, kernel, mode="reflect")
    return _norm01(np.abs(resp))


# ── Image: gray 値の多項式面近似(照明/背景推定)─────────────────────────────── #
def _fit_surface(v, order):
    h, w, Y, X = _grid(v.shape)
    xn = (X / max(w - 1, 1)) * 2 - 1                     # [-1,1] 正規化で条件数改善
    yn = (Y / max(h - 1, 1)) * 2 - 1
    cols = [np.ones_like(xn), xn, yn]
    if order >= 2:
        cols += [xn * xn, yn * yn, xn * yn]
    A = np.stack([c.ravel() for c in cols], axis=1)
    coef, *_ = np.linalg.lstsq(A, v.ravel(), rcond=None)
    return _norm01((A @ coef).reshape(v.shape))


def _fit_surface_first_order(v, a, b):
    return _fit_surface(v, 1)


def _fit_surface_second_order(v, a, b):
    return _fit_surface(v, 2)


# ── Image: GLCM 共起行列テクスチャ特徴(image -> feature scalar)──────────────── #
def _cooc_feature_image(v, a, b):
    """量子化して距離 d の水平共起行列を作り、Haralick contrast を返す(a=距離, b は角度選択)。"""
    levels = 8
    q = np.clip((v * levels).astype(int), 0, levels - 1)
    d = 1 + int(a * 3)
    if b < 0.5:                                          # 水平 (0°)
        i, j = q[:, :-d], q[:, d:]
    else:                                                # 垂直 (90°)
        i, j = q[:-d, :], q[d:, :]
    glcm = np.zeros((levels, levels), dtype=np.float64)
    np.add.at(glcm, (i.ravel(), j.ravel()), 1.0)
    glcm += glcm.T
    total = glcm.sum()
    if total <= 0:
        return np.float64(0.0)
    glcm /= total
    li = np.arange(levels)
    contrast = float((glcm * (li[:, None] - li[None, :]) ** 2).sum())
    return np.float64(contrast / (levels - 1) ** 2)     # [0,1] 正規化


# ── Image: 定義域を全面へ(image -> full region)────────────────────────────── #
def _full_domain(v, a, b):
    return np.ones_like(v, dtype=np.float64)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """未カバー実 HALCON operator の genuine 実装 tier を返す。"""
    defs = [
        # (name, halcon 実名, in_sort, out_sort, fn)
        ("hx_gen_circle", "gen_circle", IMAGE, REGION, _gen_circle),
        ("hx_gen_ellipse", "gen_ellipse", IMAGE, REGION, _gen_ellipse),
        ("hx_gen_rectangle2", "gen_rectangle2", IMAGE, REGION, _gen_rectangle2),
        ("hx_gen_checker_region", "gen_checker_region", IMAGE, REGION, _gen_checker_region),
        ("hx_gen_grid_region", "gen_grid_region", IMAGE, REGION, _gen_grid_region),
        ("hx_gabor", "convol_gabor", IMAGE, IMAGE, _convol_gabor),
        ("hx_fit_surface1", "fit_surface_first_order", IMAGE, IMAGE, _fit_surface_first_order),
        ("hx_fit_surface2", "fit_surface_second_order", IMAGE, IMAGE, _fit_surface_second_order),
        ("hx_cooc_feature", "cooc_feature_image", IMAGE, FEATURE, _cooc_feature_image),
        ("hx_full_domain", "full_domain", IMAGE, REGION, _full_domain),
    ]
    return [Op(name, "halcon_ext", halcon, isort, osort, fn)
            for (name, halcon, isort, osort, fn) in defs]
