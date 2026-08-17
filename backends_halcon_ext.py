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


# ── 第 2 バッチ ─────────────────────────────────────────────────────────────── #
def _disk(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = (xx * xx + yy * yy <= r * r).astype(np.float64)
    return d / d.sum()


def _mean_image_shape(v, a, b):
    """任意マスク(円 disk)による平均平滑化。半径 r を a で可変(矩形 mean と別 op)。"""
    r = 1 + int(a * 4)
    return ndimage.convolve(v, _disk(r), mode="reflect")


def _close_edges(v, a, b):
    """エッジ振幅画像の隙間を閉じる: しきい値 a で二値化 → morphological closing(半径 b)。"""
    from scipy.ndimage import binary_closing, generate_binary_structure, iterate_structure
    edges = v > a
    it = 1 + int(b * 3)
    st = iterate_structure(generate_binary_structure(2, 2), it)
    return binary_closing(edges, structure=st).astype(np.float64)


def _close_edges_length(v, a, b):
    """close_edges に加え、長さ(画素数)が閾値未満の短いエッジ断片を除去する。"""
    from scipy.ndimage import binary_closing, generate_binary_structure, label
    edges = binary_closing(v > a, structure=generate_binary_structure(2, 2))
    lab, n = label(edges)
    if n == 0:
        return edges.astype(np.float64)
    sizes = np.bincount(lab.ravel())
    min_len = 2 + int(b * 20)
    keep = np.isin(lab, np.nonzero(sizes >= min_len)[0][1:])   # 0=背景を除く
    return keep.astype(np.float64)


def _expand_region(v, a, b):
    """領域間の隙間を埋める(region -> region): 二値領域を dilation で膨張して連結を促す。"""
    from scipy.ndimage import binary_dilation, generate_binary_structure, iterate_structure
    reg = v > 0.5
    it = 1 + int(a * 4)
    st = iterate_structure(generate_binary_structure(2, 1), it)
    return binary_dilation(reg, structure=st).astype(np.float64)


def _region_to_mean(v, a, b):
    """各連結領域をその平均 gray 値で塗る(image -> image)。閾値 a で前景/背景を分け label 化。"""
    from scipy.ndimage import label, mean as ndmean
    fg = v > a
    lab, n = label(fg)
    out = np.full_like(v, float(v[~fg].mean()) if (~fg).any() else 0.0)
    if n > 0:
        means = ndmean(v, labels=lab, index=np.arange(1, n + 1))
        out[fg] = np.asarray(means)[lab[fg] - 1]
    return out


# ── 第 3 バッチ: セグメンテーション/エッジ/周波数フィルタ生成 ─────────────────── #
def _nonmax_suppression_dir(v, a, b):
    """勾配方向に沿った非最大抑制(Canny の NMS 段)。エッジを 1 画素に細線化する。"""
    gx = ndimage.sobel(v, axis=1)
    gy = ndimage.sobel(v, axis=0)
    mag = np.hypot(gx, gy)
    ang = (np.rad2deg(np.arctan2(gy, gx)) % 180.0)
    q = (np.round(ang / 45.0).astype(int)) % 4
    shifts = {0: ((0, -1), (0, 1)), 1: ((-1, 1), (1, -1)),
              2: ((-1, 0), (1, 0)), 3: ((-1, -1), (1, 1))}
    out = np.zeros_like(mag)
    for qi, (s1, s2) in shifts.items():
        n1 = np.roll(np.roll(mag, s1[0], 0), s1[1], 1)
        n2 = np.roll(np.roll(mag, s2[0], 0), s2[1], 1)
        keep = (q == qi) & (mag >= n1) & (mag >= n2)
        out[keep] = mag[keep]
    out = _norm01(out)
    out[out < a * 0.3] = 0.0                              # 弱エッジを a で抑制
    return out


def _char_threshold(v, a, b):
    """暗い文字を明るい背景から抽出(region): thresh = mean - k*std(k は a)で下側を選ぶ。"""
    k = 0.2 + 1.8 * a
    thr = float(v.mean()) - k * float(v.std())
    return (v < thr).astype(np.float64)


def _histo_to_thresh(v, a, b):
    """ヒストグラムの谷から閾値を決めて二値化(Otsu の分散基準でなく谷検出=別 op)。"""
    hist, edges = np.histogram(v.ravel(), bins=64, range=(0.0, 1.0))
    hs = ndimage.gaussian_filter1d(hist.astype(float), 1.5)
    # 2 つの主ピーク間の最小値(谷)を閾値に
    peaks = np.argsort(hs)[::-1]
    p1 = peaks[0]
    p2 = next((p for p in peaks[1:] if abs(p - p1) > 4), p1)
    lo, hi = sorted((p1, p2))
    valley = lo + int(np.argmin(hs[lo:hi + 1])) if hi > lo else 32
    thr = edges[valley]
    return (v > thr).astype(np.float64)


def _freq_radius(shape):
    h, w = shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    return np.fft.fftshift(np.sqrt(fy ** 2 + fx ** 2))   # 中心=DC の正規化周波数半径


def _gen_lowpass(v, a, b):
    """理想ローパスフィルタ画像(周波数領域の中心円板マスク、遮断半径 a)。"""
    r = _freq_radius(v.shape)
    cutoff = 0.05 + 0.45 * a
    return (r <= cutoff).astype(np.float64)


def _gen_highpass(v, a, b):
    r = _freq_radius(v.shape)
    cutoff = 0.05 + 0.45 * a
    return (r > cutoff).astype(np.float64)


def _gen_bandpass(v, a, b):
    """理想バンドパス(周波数領域の円環マスク、内半径 a・帯域幅 b)。"""
    r = _freq_radius(v.shape)
    r_lo = 0.05 + 0.4 * a
    r_hi = r_lo + 0.05 + 0.3 * b
    return ((r >= r_lo) & (r <= r_hi)).astype(np.float64)


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
        # 第 2 バッチ
        ("hx_mean_shape", "mean_image_shape", IMAGE, IMAGE, _mean_image_shape),
        ("hx_close_edges", "close_edges", IMAGE, IMAGE, _close_edges),
        ("hx_close_edges_length", "close_edges_length", IMAGE, IMAGE, _close_edges_length),
        ("hx_expand_region", "expand_region", REGION, REGION, _expand_region),
        ("hx_region_to_mean", "region_to_mean", IMAGE, IMAGE, _region_to_mean),
    ]
    return [Op(name, "halcon_ext", halcon, isort, osort, fn)
            for (name, halcon, isort, osort, fn) in defs]
