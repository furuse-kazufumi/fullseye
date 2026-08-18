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


# ── 第 4 バッチ: Morphology(任意 SE の region 形態)+ Regions 生成 + 周波数フィルタ ── #
def _disc_bool(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return xx * xx + yy * yy <= r * r


def _se_radius(a):
    return 1 + int(a * 4)


def _erosion1(v, a, b):
    from scipy.ndimage import binary_erosion
    return binary_erosion(v > 0.5, structure=_disc_bool(_se_radius(a))).astype(np.float64)


def _dilation1(v, a, b):
    from scipy.ndimage import binary_dilation
    return binary_dilation(v > 0.5, structure=_disc_bool(_se_radius(a))).astype(np.float64)


def _opening(v, a, b):
    from scipy.ndimage import binary_opening
    return binary_opening(v > 0.5, structure=_disc_bool(_se_radius(a))).astype(np.float64)


def _closing(v, a, b):
    from scipy.ndimage import binary_closing
    return binary_closing(v > 0.5, structure=_disc_bool(_se_radius(a))).astype(np.float64)


def _dilation2(v, a, b):
    """参照点つき dilation: 膨張後に参照点オフセット(b で並進)。"""
    from scipy.ndimage import binary_dilation
    d = binary_dilation(v > 0.5, structure=_disc_bool(_se_radius(a)))
    sh = int((b - 0.5) * 6)
    return np.roll(d, sh, axis=1).astype(np.float64)


def _gen_disc_se(v, a, b):
    """円板構造要素を region として生成(半径 a)。"""
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    r = (0.05 + 0.35 * a) * min(h, w)
    return ((Y - cy) ** 2 + (X - cx) ** 2 <= r * r).astype(np.float64)


def _gen_circle_sector(v, a, b):
    """円のセクタ region(開始角 b*2pi、掃引 a*2pi)。"""
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    r = 0.42 * min(h, w)
    rad = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2)
    ang = np.arctan2(Y - cy, X - cx) % (2 * np.pi)
    start = b * 2 * np.pi
    sweep = 0.1 + a * (2 * np.pi - 0.1)
    rel = (ang - start) % (2 * np.pi)
    return ((rad <= r) & (rel <= sweep)).astype(np.float64)


def _gen_ellipse_sector(v, a, b):
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    ra, rb = 0.42 * w, 0.30 * h
    inside = ((X - cx) / ra) ** 2 + ((Y - cy) / rb) ** 2 <= 1.0
    ang = np.arctan2(Y - cy, X - cx) % (2 * np.pi)
    rel = (ang - b * 2 * np.pi) % (2 * np.pi)
    return (inside & (rel <= 0.1 + a * (2 * np.pi - 0.1))).astype(np.float64)


def _gen_empty_region(v, a, b):
    return np.zeros_like(v, dtype=np.float64)


def _clip_region_rel(v, a, b):
    """region をその外接矩形に対し相対的にクリップ(各辺から a の割合を削る)。"""
    reg = v > 0.5
    ys, xs = np.nonzero(reg)
    if ys.size == 0:
        return reg.astype(np.float64)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    my = int((y1 - y0) * 0.5 * a)
    mx = int((x1 - x0) * 0.5 * a)
    out = np.zeros_like(reg)
    out[y0 + my:y1 - my + 1, x0 + mx:x1 - mx + 1] = reg[y0 + my:y1 - my + 1, x0 + mx:x1 - mx + 1]
    return out.astype(np.float64)


def _gen_bandfilter(v, a, b):
    """理想バンドフィルタ画像(周波数円環、中心半径 a・幅 b)。gen_bandpass と別 operator。"""
    r = _freq_radius(v.shape)
    c = 0.05 + 0.4 * a
    half = 0.03 + 0.15 * b
    return ((r >= c - half) & (r <= c + half)).astype(np.float64)


def _gen_derivative_filter(v, a, b):
    """周波数領域の微分フィルタ(高周波ほど強い=周波数半径に比例)。"""
    r = _freq_radius(v.shape)
    return _norm01(r)


def _fill_interlace(v, a, b):
    """2 枚のビデオ半画像を補間(奇数行を隣接偶数行の平均で置換=デインターレース)。"""
    out = v.copy()
    up = np.roll(v, 1, axis=0)
    dn = np.roll(v, -1, axis=0)
    out[1::2, :] = 0.5 * (up[1::2, :] + dn[1::2, :])
    return out


# ── 第 5 バッチ: 高さ場陰影 / 平面偏差 / 直線分検出 ────────────────────────────── #
def _shade_height_field(v, a, b):
    """高さ場 v を Lambertian 陰影で描画(法線×光源)。方位 a・仰角 b の光源。"""
    gy, gx = np.gradient(v)
    nz = np.ones_like(v)
    norm = np.sqrt(gx * gx + gy * gy + 1.0)
    az, el = a * 2 * np.pi, (0.2 + 0.7 * b) * (np.pi / 2)
    lx, ly, lz = np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)
    shade = (-gx * lx - gy * ly + nz * lz) / norm
    return _norm01(np.clip(shade, 0, None))


def _plane_deviation(v, a, b):
    """gray 値の 1 次平面近似からの偏差 |v - plane|(平坦度/欠陥検査)。"""
    h, w, Y, X = _grid(v.shape)
    xn = (X / max(w - 1, 1)) * 2 - 1
    yn = (Y / max(h - 1, 1)) * 2 - 1
    A = np.stack([np.ones_like(xn).ravel(), xn.ravel(), yn.ravel()], axis=1)
    coef, *_ = np.linalg.lstsq(A, v.ravel(), rcond=None)
    plane = (A @ coef).reshape(v.shape)
    # 直接クリップ(min-max 正規化は純平面の浮動小数ノイズを [0,1] に増幅するため不可)。
    return np.clip(np.abs(v - plane), 0.0, 1.0)


def _detect_edge_segments(v, a, b):
    """直線的なエッジ断片を検出: NMS で細線化 → 連結成分のうち PCA で細長い(直線状)ものを残す。"""
    from scipy.ndimage import label, generate_binary_structure
    thin = _nonmax_suppression_dir(v, a, 0) > 0
    lab, n = label(thin, structure=generate_binary_structure(2, 2))
    out = np.zeros_like(v)
    min_ratio = 3.0 + b * 12.0                           # 細長さ閾値(長軸/短軸)
    for k in range(1, n + 1):
        ys, xs = np.nonzero(lab == k)
        if ys.size < 5:
            continue
        pts = np.column_stack([ys - ys.mean(), xs - xs.mean()]).astype(float)
        ev = np.linalg.eigvalsh(np.cov(pts.T)) if pts.shape[0] > 1 else np.array([0.0, 0.0])
        ratio = (ev[1] / ev[0]) if ev[0] > 1e-9 else np.inf
        if ratio >= min_ratio:                           # 直線状のみ採用
            out[ys, xs] = 1.0
    return out


# ── 第 6 バッチ: Image ドメイン/ラベル + Segmentation lowlands/plateaus ────────── #
def _gen_image_proto(v, a, b):
    """入力と同サイズの定数グレー画像(値 a)を生成。"""
    return np.full_like(v, float(a), dtype=np.float64)


def _get_domain(v, a, b):
    """画像の定義域を region として取得(既定は全面)。"""
    return np.ones_like(v, dtype=np.float64)


def _region_to_label(v, a, b):
    """しきい値 a で二値化した領域の連結成分をラベル画像に変換(正規化)。"""
    from scipy.ndimage import label, generate_binary_structure
    lab, n = label(v > a, structure=generate_binary_structure(2, 2))
    return (lab / n).astype(np.float64) if n > 0 else np.zeros_like(v)


def _rectangle1_domain(v, a, b):
    """画像の定義域を軸並行矩形に縮小(中央の a×b の割合)region。"""
    h, w = v.shape
    hh, ww = int(h * (0.2 + 0.7 * a)), int(w * (0.2 + 0.7 * b))
    y0, x0 = (h - hh) // 2, (w - ww) // 2
    out = np.zeros_like(v, dtype=np.float64)
    out[y0:y0 + hh, x0:x0 + ww] = 1.0
    return out


def _lowlands(v, a, b):
    """gray 値の窪地(局所最小の平坦域)を検出: 近傍最小と一致する画素 region。"""
    size = 3 + int(a * 6)
    mn = ndimage.minimum_filter(v, size=size, mode="reflect")
    return ((v <= mn + 1e-6) & (v < float(v.mean()))).astype(np.float64)


def _plateaus_center(v, a, b):
    """gray 値の平坦域(勾配~0)の中心を検出: 平坦連結成分の重心画素を marker region に。"""
    from scipy.ndimage import label, center_of_mass, generate_binary_structure
    gmag = np.hypot(ndimage.sobel(v, axis=1), ndimage.sobel(v, axis=0))
    flat = gmag < (0.01 + 0.1 * a) * (gmag.max() + 1e-9)
    lab, n = label(flat, structure=generate_binary_structure(2, 2))
    out = np.zeros_like(v, dtype=np.float64)
    if n > 0:
        for cy, cx in center_of_mass(flat, lab, range(1, n + 1)):
            out[int(round(cy)), int(round(cx))] = 1.0
    return out


# ── 第 7 バッチ: region 平行移動 / skeleton 分割 ──────────────────────────────── #
def _move_region(v, a, b):
    """region を平行移動(dy=a, dx=b を中心 0 のオフセットに)。"""
    reg = v > 0.5
    dy = int((a - 0.5) * v.shape[0])
    dx = int((b - 0.5) * v.shape[1])
    return np.roll(np.roll(reg, dy, 0), dx, 1).astype(np.float64)


def _split_skeleton_region(v, a, b):
    """1 画素幅 skeleton を分岐点で分割: 近傍数>=3 の junction を除いて連結成分に分ける。"""
    from scipy.ndimage import convolve
    sk = (v > 0.5).astype(np.uint8)
    nb = convolve(sk, np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]]), mode="constant")
    junc = (sk == 1) & (nb >= 3)                         # 分岐点
    return ((sk == 1) & ~junc).astype(np.float64)


# ── 第 8 バッチ: XLD contour(dict {shape,(H,W); cs:[Nx2 (row,col)]})─────────────── #
def _c_cs(v):
    return [np.asarray(c, float) for c in v.get("cs", [])] if isinstance(v, dict) else []


def _c_shape(v):
    return tuple(v.get("shape", (1, 1))) if isinstance(v, dict) else (1, 1)


def _c_mk(shape, cs):
    return {"shape": shape, "cs": [np.asarray(c, float) for c in cs if len(c) > 0]}


def _sort_contours_xld(v, a, b):
    """contour を相対位置(重心 row→col)でソート。"""
    cs = _c_cs(v)
    cs.sort(key=lambda c: (float(c[:, 0].mean()), float(c[:, 1].mean())))
    return _c_mk(_c_shape(v), cs)


def _clip_contours_xld(v, a, b):
    """contour を画像ドメイン(中央 margin a/b を残す矩形)にクリップ(範囲外点を除去)。"""
    h, w = _c_shape(v)
    my, mx = a * 0.4 * h, b * 0.4 * w
    out = []
    for c in _c_cs(v):
        m = (c[:, 0] >= my) & (c[:, 0] <= h - 1 - my) & (c[:, 1] >= mx) & (c[:, 1] <= w - 1 - mx)
        if m.any():
            out.append(c[m])
    return _c_mk((h, w), out)


def _clip_end_points_contours_xld(v, a, b):
    """各 contour の端点を k 個ずつ切り落とす(k は a)。"""
    k = 1 + int(a * 5)
    out = [c[k:len(c) - k] for c in _c_cs(v) if len(c) > 2 * k + 1]
    return _c_mk(_c_shape(v), out)


def _all_pts(v):
    cs = _c_cs(v)
    return np.concatenate(cs, 0) if cs else np.zeros((0, 2))


def _smallest_circle_xld(v, a, b):
    """全 contour 点の最小包含円(近似=重心中心)の半径を返す(正規化 feature)。"""
    p = _all_pts(v)
    if len(p) == 0:
        return np.float64(0.0)
    c = p.mean(0)
    r = float(np.sqrt(((p - c) ** 2).sum(1)).max())
    return np.float64(r / max(_c_shape(v)))


def _smallest_rectangle1_xld(v, a, b):
    """全 contour 点の外接軸並行矩形の面積比を返す(feature)。"""
    p = _all_pts(v)
    if len(p) == 0:
        return np.float64(0.0)
    hw = (p.max(0) - p.min(0))
    h, w = _c_shape(v)
    return np.float64(float(hw[0] * hw[1]) / max(h * w, 1))


def _test_closed_xld(v, a, b):
    """閉じている contour の割合を返す(端点間距離が閾値未満=閉、feature)。"""
    cs = _c_cs(v)
    if not cs:
        return np.float64(0.0)
    tol = 1.0 + a * 4.0
    closed = sum(1 for c in cs if len(c) > 2 and np.hypot(*(c[0] - c[-1])) <= tol)
    return np.float64(closed / len(cs))


def _regress_contours_xld(v, a, b):
    """各 contour に回帰直線を当て、平均残差(直線からのズレ)を返す(feature)。小=直線的。"""
    cs = _c_cs(v)
    res = []
    for c in cs:
        if len(c) < 3:
            continue
        d = c - c.mean(0)
        w_, V = np.linalg.eigh(np.cov(d.T))
        n = V[:, 0]                                       # 最小固有ベクトル=法線
        res.append(float(np.sqrt((( d @ n) ** 2).mean())))
    if not res:
        return np.float64(0.0)
    return np.float64(min(np.mean(res) / max(_c_shape(v)), 1.0))


def _moments_any_xld(v, a, b):
    """全 contour 点の 2 次中心モーメント(広がり)を返す(正規化 feature)。"""
    p = _all_pts(v)
    if len(p) < 2:
        return np.float64(0.0)
    d = p - p.mean(0)
    mu = (d[:, 0] ** 2 + d[:, 1] ** 2).mean()
    return np.float64(min(mu / (max(_c_shape(v)) ** 2), 1.0))


def _rdp(pts, eps):
    """Ramer-Douglas-Peucker: 支配点の index を返す。"""
    if len(pts) < 3:
        return [0, len(pts) - 1]
    a, b = pts[0], pts[-1]
    ab = b - a
    L = np.hypot(*ab)
    if L < 1e-9:
        d = np.hypot(*(pts - a).T)
    else:
        d = np.abs(np.cross(np.tile(ab, (len(pts), 1)), pts - a)) / L
    i = int(np.argmax(d))
    if d[i] > eps:
        left = _rdp(pts[:i + 1], eps)
        right = _rdp(pts[i:], eps)
        return left[:-1] + [x + i for x in right]
    return [0, len(pts) - 1]


def _split_contours_xld(v, a, b):
    """各 contour を支配点(RDP)で線分に分割する(許容 eps は a)。"""
    eps = 0.5 + a * 5.0
    out = []
    for c in _c_cs(v):
        if len(c) < 3:
            out.append(c)
            continue
        idx = _rdp(c, eps)
        for s, e in zip(idx[:-1], idx[1:]):
            if e - s >= 1:
                out.append(c[s:e + 1])
    return _c_mk(_c_shape(v), out)


def _gen_parallel_contour_xld(v, a, b):
    """各 contour の平行(法線オフセット)contour を生成(距離は (a-0.5) で符号つき)。"""
    dist = (a - 0.5) * 10.0
    out = []
    for c in _c_cs(v):
        if len(c) < 2:
            out.append(c)
            continue
        t = np.gradient(c, axis=0)
        nrm = np.column_stack([-t[:, 1], t[:, 0]])
        L = np.hypot(nrm[:, 0], nrm[:, 1])[:, None]
        nrm = nrm / np.where(L < 1e-9, 1.0, L)
        out.append(c + dist * nrm)
    return _c_mk(_c_shape(v), out)


# ── 第 9 バッチ: XLD contour への形状フィット(contour -> feature)──────────────── #
def _fit_circle_contour_xld(v, a, b):
    """Kåsa 代数法で contour 点に円を当て、フィット残差(RMS)を返す(小=円に近い)。"""
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    x, y = p[:, 1], p[:, 0]
    A = np.column_stack([x, y, np.ones_like(x)])
    bb = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, bb, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(max(sol[2] + cx * cx + cy * cy, 0))
    res = np.sqrt(((np.hypot(x - cx, y - cy) - r) ** 2).mean())
    return np.float64(min(res / max(_c_shape(v)), 1.0))


def _fit_ellipse_contour_xld(v, a, b):
    """2 次モーメントから楕円を当て、軸比(短/長=真円で 1、細長いほど 0)を返す。"""
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    d = p - p.mean(0)
    w_, _ = np.linalg.eigh(np.cov(d.T))
    w_ = np.clip(w_, 0, None)
    return np.float64(np.sqrt(w_[0] / w_[1]) if w_[1] > 1e-9 else 0.0)


def _min_area_rect_ratio(p):
    """角度掃引で最小面積外接矩形を求め、(点の広がり充填率, 面積) を返す。"""
    best = None
    for deg in range(0, 90, 6):
        th = np.radians(deg)
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        q = p @ R.T
        area = float((q[:, 0].ptp() + 1e-9) * (q[:, 1].ptp() + 1e-9))
        if best is None or area < best[0]:
            best = (area, q[:, 0].ptp(), q[:, 1].ptp())
    return best


def _fit_rectangle2_contour_xld(v, a, b):
    """最小面積外接矩形を当て、そのアスペクト比(短辺/長辺)を返す(feature)。"""
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    _, e1, e2 = _min_area_rect_ratio(p)
    lo, hi = sorted((e1, e2))
    return np.float64(lo / hi if hi > 1e-9 else 0.0)


def _smallest_rectangle2_xld(v, a, b):
    """最小面積外接矩形の面積比(矩形面積 / 画像面積)を返す(feature)。"""
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    area, _, _ = _min_area_rect_ratio(p)
    h, w = _c_shape(v)
    return np.float64(min(area / max(h * w, 1), 1.0))


# ── 第 10 バッチ: XLD contour 続き ───────────────────────────────────────────── #
def _crop_contours_xld(v, a, b):
    """contour を中央の a×b 割合の矩形に crop(範囲内の点のみ残す)。"""
    h, w = _c_shape(v)
    hh, ww = (0.3 + 0.6 * a) * h / 2, (0.3 + 0.6 * b) * w / 2
    cy, cx = h / 2, w / 2
    out = []
    for c in _c_cs(v):
        m = (np.abs(c[:, 0] - cy) <= hh) & (np.abs(c[:, 1] - cx) <= ww)
        if m.any():
            out.append(c[m])
    return _c_mk((h, w), out)


def _dist_ellipse_contour_xld(v, a, b):
    """contour 点の当てはめ楕円境界からの平均距離を返す(小=楕円に近い、feature)。"""
    p = _all_pts(v)
    if len(p) < 4:
        return np.float64(0.0)
    c = p.mean(0)
    d = p - c
    w_, V = np.linalg.eigh(np.cov(d.T))
    w_ = np.clip(w_, 1e-9, None)
    loc = d @ V                                          # 主軸系
    ax = 2 * np.sqrt(w_)                                 # 半軸(≈2σ)
    rad = np.sqrt((loc[:, 0] / ax[0]) ** 2 + (loc[:, 1] / ax[1]) ** 2)
    return np.float64(min(float(np.abs(rad - 1.0).mean()), 1.0))


def _seg_intersect(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def _test_self_intersection_xld(v, a, b):
    """自己交差する contour の割合を返す(feature)。非隣接セグメント対を判定。"""
    cs = _c_cs(v)
    if not cs:
        return np.float64(0.0)
    hit = 0
    for c in cs:
        n = len(c)
        if n < 4:
            continue
        closed = np.hypot(*(c[0] - c[-1])) < 1e-6         # 端点一致=閉曲線
        found = False
        for i in range(n - 1):
            for j in range(i + 2, n - 1):
                if closed and i == 0 and j == n - 2:
                    continue                             # 閉曲線のみ端の隣接をスキップ
                if _seg_intersect(c[i], c[i + 1], c[j], c[j + 1]):
                    found = True
                    break
            if found:
                break
        hit += found
    return np.float64(hit / len(cs))


def _union_adjacent_contours_xld(v, a, b):
    """端点が近い(閾値 a)contour を貪欲に連結する。"""
    cs = [c for c in _c_cs(v) if len(c) > 0]
    tol = 1.0 + a * 8.0
    merged = True
    while merged and len(cs) > 1:
        merged = False
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                if np.hypot(*(cs[i][-1] - cs[j][0])) <= tol:
                    cs[i] = np.vstack([cs[i], cs[j]])
                    cs.pop(j)
                    merged = True
                    break
            if merged:
                break
    return _c_mk(_c_shape(v), cs)


def _polar_trans_contour_xld_inv(v, a, b):
    """contour 点を (radius, angle) とみなし直交座標へ逆変換(polar_trans の逆)。"""
    h, w = _c_shape(v)
    cy, cx = h / 2, w / 2
    out = []
    for c in _c_cs(v):
        rad = c[:, 0]
        ang = c[:, 1] / max(w, 1) * 2 * np.pi
        out.append(np.column_stack([cy + rad * np.sin(ang), cx + rad * np.cos(ang)]))
    return _c_mk((h, w), out)


def _select_xld_point(v, a, b):
    """クエリ点(正規化 a,b)を外接矩形に含む contour のみ選ぶ(filter)。"""
    h, w = _c_shape(v)
    qy, qx = a * h, b * w
    out = []
    for c in _c_cs(v):
        if c[:, 0].min() <= qy <= c[:, 0].max() and c[:, 1].min() <= qx <= c[:, 1].max():
            out.append(c)
    return _c_mk((h, w), out)


# ── 第 11 バッチ: shape-from-shading の光源推定(3D Reconstruction, image -> feature)── #
def _img_grads(v):
    return ndimage.sobel(v, axis=1), ndimage.sobel(v, axis=0)   # Ex, Ey


def _estimate_tilt_lr(v, a, b):
    """Lee-Rosenfeld: 光源方位角 tilt = atan2(<Ey>, <Ex>)(平均勾配方向)。[0,1] 正規化。"""
    ex, ey = _img_grads(v)
    tilt = np.arctan2(ey.mean(), ex.mean())
    return np.float64((tilt / (2 * np.pi)) % 1.0)


def _estimate_tilt_zc(v, a, b):
    """Zheng-Chellappa: 正規化勾配の平均方向で tilt を推定(局所コントラスト非依存)。"""
    ex, ey = _img_grads(v)
    mag = np.hypot(ex, ey) + 1e-9
    tilt = np.arctan2((ey / mag).mean(), (ex / mag).mean())
    return np.float64((tilt / (2 * np.pi)) % 1.0)


def _estimate_slant(v):
    """slant(光源天頂角)推定: 平均輝度と勾配統計から。Lambertian の <I>=albedo*cos(slant)。"""
    mu = float(np.clip(v.mean(), 0, 1))
    return float(np.arccos(np.clip(mu, 0, 1)))          # cos(slant)=<I>/albedo(albedo~1 近似)


def _estimate_sl_al_lr(v, a, b):
    """Lee-Rosenfeld: 光源の slant を推定(天頂角、0=正面〜pi/2=真横)。[0,1] 正規化。"""
    return np.float64(_estimate_slant(v) / (np.pi / 2))


def _estimate_sl_al_zc(v, a, b):
    """Zheng-Chellappa: slant を勾配エネルギーで補正して推定。"""
    ex, ey = _img_grads(v)
    e = float(np.hypot(ex, ey).mean())
    sl = _estimate_slant(v) * (1.0 + min(e, 1.0))       # 勾配が強い=斜光=slant 大
    return np.float64(min(sl / (np.pi / 2), 1.0))


def _estimate_al_am(v, a, b):
    """albedo(反射率)と ambient(環境光)の推定: albedo ~ 輝度レンジ、ここでは albedo を返す。"""
    lo, hi = float(v.min()), float(v.max())
    return np.float64(np.clip(hi - lo, 0, 1))           # 反射率の代理=輝度ダイナミックレンジ


# ── 第 12 バッチ: contour 距離/歪み + disparity→depth ───────────────────────────── #
def _add_noise_white_contour_xld(v, a, b):
    """contour 点に白色ガウス雑音を付加(std は a、固定 seed で決定的)。"""
    rng = np.random.default_rng(12345)
    std = a * 3.0
    out = [c + rng.normal(0, std, c.shape) for c in _c_cs(v)]
    return _c_mk(_c_shape(v), out)


def _change_radial_distortion_contours_xld(v, a, b):
    """contour に放射歪み r' = r(1 + k r^2) を適用(k は (a-0.5) で樽/糸巻き)。"""
    h, w = _c_shape(v)
    cy, cx = h / 2, w / 2
    k = (a - 0.5) * 1.5
    scale = max(h, w) / 2
    out = []
    for c in _c_cs(v):
        d = c - [cy, cx]
        r = np.hypot(d[:, 0], d[:, 1]) / scale
        f = 1 + k * r ** 2
        out.append([cy, cx] + d * f[:, None])
    return _c_mk((h, w), out)


def _dist_ellipse_contour_points_xld(v, a, b):
    """contour 各点の当てはめ楕円境界からの最大距離を返す(点別 distance の集約=max、feature)。"""
    p = _all_pts(v)
    if len(p) < 4:
        return np.float64(0.0)
    c = p.mean(0)
    d = p - c
    w_, V = np.linalg.eigh(np.cov(d.T))
    w_ = np.clip(w_, 1e-9, None)
    loc = d @ V
    ax = 2 * np.sqrt(w_)
    rad = np.sqrt((loc[:, 0] / ax[0]) ** 2 + (loc[:, 1] / ax[1]) ** 2)
    return np.float64(min(float(np.abs(rad - 1.0).max()), 1.0))


def _dist_rectangle2_contour_points_xld(v, a, b):
    """contour 各点の最小面積外接矩形の中心からの正規化距離の平均(feature)。"""
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    c = p.mean(0)
    d = np.hypot(*(p - c).T)
    return np.float64(min(float(d.mean()) / max(_c_shape(v)), 1.0))


def _distance_pc(v, a, b):
    """クエリ点(正規化 a,b)から contour までの最小距離を返す(feature)。"""
    p = _all_pts(v)
    if len(p) == 0:
        return np.float64(0.0)
    h, w = _c_shape(v)
    q = np.array([a * h, b * w])
    return np.float64(min(float(np.hypot(*(p - q).T).min()) / max(h, w), 1.0))


def _disparity_image_to_xyz(v, a, b):
    """視差画像から深度 Z = f*baseline/disparity を計算(焦点/基線は a,b で可変)。正規化 Z。"""
    f = 200 + 600 * a
    baseline = 0.05 + 0.15 * b
    disp = v * 63.0 + 0.5                                 # [0,1] を視差[px]相当へ
    z = f * baseline / disp
    return _norm01(z)


# ── 第 13 バッチ: 点/線と region・contour の距離 + 1D エッジ対 ──────────────────── #
def _distance_pr(v, a, b):
    """クエリ点(正規化 a,b)から region までの最小距離(feature)。距離変換で。"""
    reg = v > 0.5
    if not reg.any():
        return np.float64(1.0)
    dt = ndimage.distance_transform_edt(~reg)
    h, w = v.shape
    return np.float64(min(float(dt[min(int(a * h), h - 1), min(int(b * w), w - 1)]) / max(h, w), 1.0))


def _distance_sc(v, a, b):
    """水平線分(行 a*H)から contour までの最小距離(feature)。"""
    p = _all_pts(v)
    if len(p) == 0:
        return np.float64(0.0)
    h, w = _c_shape(v)
    return np.float64(min(float(np.abs(p[:, 0] - a * h).min()) / max(h, 1), 1.0))


def _fuzzy_measure_pairs(v, a, b):
    """中央の水平プロファイルでエッジ対(明バーの立上り境界→立下り境界)を数える(1D 計測)。

    レベル閾値の交差で境界を 1 回ずつ取る(np.gradient はステップを 2 画素に滲ませ二重計上
    するため不可)。閾値 lvl は a で可変。返り値は対の数(/10 で正規化した feature)。"""
    row = v[v.shape[0] // 2]
    lvl = 0.2 + 0.6 * a
    hi = row >= lvl
    rises = np.where(~hi[:-1] & hi[1:])[0]               # low->high 境界
    falls = np.where(hi[:-1] & ~hi[1:])[0]               # high->low 境界
    pairs = 0
    fi = 0
    for r in rises:
        while fi < len(falls) and falls[fi] <= r:
            fi += 1
        if fi < len(falls):
            pairs += 1
            fi += 1
    return np.float64(min(pairs / 10.0, 1.0))


# ── 第 14 バッチ: region 点包含判定 ──────────────────────────────────────────── #
def _test_region_point(v, a, b):
    """region が点(正規化 a=行, b=列)を含むか(1/0、test_region_point)。"""
    reg = v > 0.5
    h, w = v.shape
    r, c = min(int(a * h), h - 1), min(int(b * w), w - 1)
    return np.float64(1.0 if reg[r, c] else 0.0)


def _test_region_points(v, a, b):
    """格子状の複数点のうち region に含まれる割合(test_region_points)。"""
    reg = v > 0.5
    h, w = v.shape
    step = max(2, int((0.1 + 0.3 * a) * min(h, w)))
    pts = reg[::step, ::step]
    return np.float64(float(pts.mean()) if pts.size else 0.0)


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
        # 第 3 バッチ
        ("hx_nonmax_dir", "nonmax_suppression_dir", IMAGE, IMAGE, _nonmax_suppression_dir),
        ("hx_char_threshold", "char_threshold", IMAGE, REGION, _char_threshold),
        ("hx_histo_to_thresh", "histo_to_thresh", IMAGE, REGION, _histo_to_thresh),
        ("hx_gen_lowpass", "gen_lowpass", IMAGE, IMAGE, _gen_lowpass),
        ("hx_gen_highpass", "gen_highpass", IMAGE, IMAGE, _gen_highpass),
        ("hx_gen_bandpass", "gen_bandpass", IMAGE, IMAGE, _gen_bandpass),
        # 第 4 バッチ
        ("hx_erosion1", "erosion1", REGION, REGION, _erosion1),
        ("hx_dilation1", "dilation1", REGION, REGION, _dilation1),
        ("hx_opening", "opening", REGION, REGION, _opening),
        ("hx_closing", "closing", REGION, REGION, _closing),
        ("hx_dilation2", "dilation2", REGION, REGION, _dilation2),
        ("hx_gen_disc_se", "gen_disc_se", IMAGE, REGION, _gen_disc_se),
        ("hx_gen_circle_sector", "gen_circle_sector", IMAGE, REGION, _gen_circle_sector),
        ("hx_gen_ellipse_sector", "gen_ellipse_sector", IMAGE, REGION, _gen_ellipse_sector),
        ("hx_gen_empty_region", "gen_empty_region", IMAGE, REGION, _gen_empty_region),
        ("hx_clip_region_rel", "clip_region_rel", REGION, REGION, _clip_region_rel),
        ("hx_gen_bandfilter", "gen_bandfilter", IMAGE, IMAGE, _gen_bandfilter),
        ("hx_gen_derivative_filter", "gen_derivative_filter", IMAGE, IMAGE, _gen_derivative_filter),
        ("hx_fill_interlace", "fill_interlace", IMAGE, IMAGE, _fill_interlace),
        # 第 5 バッチ
        ("hx_shade_height_field", "shade_height_field", IMAGE, IMAGE, _shade_height_field),
        ("hx_plane_deviation", "plane_deviation", IMAGE, IMAGE, _plane_deviation),
        ("hx_detect_edge_segments", "detect_edge_segments", IMAGE, REGION, _detect_edge_segments),
        # 第 6 バッチ
        ("hx_gen_image_proto", "gen_image_proto", IMAGE, IMAGE, _gen_image_proto),
        ("hx_get_domain", "get_domain", IMAGE, REGION, _get_domain),
        ("hx_region_to_label", "region_to_label", IMAGE, IMAGE, _region_to_label),
        ("hx_rectangle1_domain", "rectangle1_domain", IMAGE, REGION, _rectangle1_domain),
        ("hx_lowlands", "lowlands", IMAGE, REGION, _lowlands),
        ("hx_plateaus_center", "plateaus_center", IMAGE, REGION, _plateaus_center),
        # 第 7 バッチ
        ("hx_move_region", "move_region", REGION, REGION, _move_region),
        ("hx_split_skeleton_region", "split_skeleton_region", REGION, REGION, _split_skeleton_region),
        # 第 8 バッチ(XLD contour)
        ("hx_sort_contours", "sort_contours_xld", CONTOUR, CONTOUR, _sort_contours_xld),
        ("hx_clip_contours", "clip_contours_xld", CONTOUR, CONTOUR, _clip_contours_xld),
        ("hx_clip_end_points", "clip_end_points_contours_xld", CONTOUR, CONTOUR, _clip_end_points_contours_xld),
        ("hx_smallest_circle_xld", "smallest_circle_xld", CONTOUR, FEATURE, _smallest_circle_xld),
        ("hx_smallest_rect1_xld", "smallest_rectangle1_xld", CONTOUR, FEATURE, _smallest_rectangle1_xld),
        ("hx_test_closed_xld", "test_closed_xld", CONTOUR, FEATURE, _test_closed_xld),
        ("hx_regress_contours", "regress_contours_xld", CONTOUR, FEATURE, _regress_contours_xld),
        ("hx_moments_any_xld", "moments_any_xld", CONTOUR, FEATURE, _moments_any_xld),
        ("hx_split_contours", "split_contours_xld", CONTOUR, CONTOUR, _split_contours_xld),
        ("hx_gen_parallel_contour", "gen_parallel_contour_xld", CONTOUR, CONTOUR, _gen_parallel_contour_xld),
        # 第 9 バッチ(XLD 形状フィット)
        ("hx_fit_circle_contour", "fit_circle_contour_xld", CONTOUR, FEATURE, _fit_circle_contour_xld),
        ("hx_fit_ellipse_contour", "fit_ellipse_contour_xld", CONTOUR, FEATURE, _fit_ellipse_contour_xld),
        ("hx_fit_rectangle2_contour", "fit_rectangle2_contour_xld", CONTOUR, FEATURE, _fit_rectangle2_contour_xld),
        ("hx_smallest_rect2_xld", "smallest_rectangle2_xld", CONTOUR, FEATURE, _smallest_rectangle2_xld),
        # 第 10 バッチ(XLD 続き)
        ("hx_crop_contours", "crop_contours_xld", CONTOUR, CONTOUR, _crop_contours_xld),
        ("hx_dist_ellipse_contour", "dist_ellipse_contour_xld", CONTOUR, FEATURE, _dist_ellipse_contour_xld),
        ("hx_test_self_intersect", "test_self_intersection_xld", CONTOUR, FEATURE, _test_self_intersection_xld),
        ("hx_union_adjacent", "union_adjacent_contours_xld", CONTOUR, CONTOUR, _union_adjacent_contours_xld),
        ("hx_polar_trans_inv", "polar_trans_contour_xld_inv", CONTOUR, CONTOUR, _polar_trans_contour_xld_inv),
        ("hx_select_xld_point", "select_xld_point", CONTOUR, CONTOUR, _select_xld_point),
        # 第 11 バッチ(shape-from-shading 光源推定)
        ("hx_estimate_tilt_lr", "estimate_tilt_lr", IMAGE, FEATURE, _estimate_tilt_lr),
        ("hx_estimate_tilt_zc", "estimate_tilt_zc", IMAGE, FEATURE, _estimate_tilt_zc),
        ("hx_estimate_sl_al_lr", "estimate_sl_al_lr", IMAGE, FEATURE, _estimate_sl_al_lr),
        ("hx_estimate_sl_al_zc", "estimate_sl_al_zc", IMAGE, FEATURE, _estimate_sl_al_zc),
        ("hx_estimate_al_am", "estimate_al_am", IMAGE, FEATURE, _estimate_al_am),
        # 第 12 バッチ
        ("hx_add_noise_contour", "add_noise_white_contour_xld", CONTOUR, CONTOUR, _add_noise_white_contour_xld),
        ("hx_radial_distort_contour", "change_radial_distortion_contours_xld", CONTOUR, CONTOUR, _change_radial_distortion_contours_xld),
        ("hx_dist_ellipse_points", "dist_ellipse_contour_points_xld", CONTOUR, FEATURE, _dist_ellipse_contour_points_xld),
        ("hx_dist_rect2_points", "dist_rectangle2_contour_points_xld", CONTOUR, FEATURE, _dist_rectangle2_contour_points_xld),
        ("hx_distance_pc", "distance_pc", CONTOUR, FEATURE, _distance_pc),
        ("hx_disparity_to_xyz", "disparity_image_to_xyz", IMAGE, IMAGE, _disparity_image_to_xyz),
        # 第 13 バッチ
        ("hx_distance_pr", "distance_pr", REGION, FEATURE, _distance_pr),
        ("hx_distance_sc", "distance_sc", CONTOUR, FEATURE, _distance_sc),
        ("hx_fuzzy_measure_pairs", "fuzzy_measure_pairs", IMAGE, FEATURE, _fuzzy_measure_pairs),
    ]
    return [Op(name, "halcon_ext", halcon, isort, osort, fn)
            for (name, halcon, isort, osort, fn) in defs]
