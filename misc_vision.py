"""残 genuine の寄せ集め: Image 生成・Regions・Segmentation(HALCON 複数 chapter genuine, numpy).

image = 2D float64、region = bool 2D、contour = dict {shape, cs:[Nx2]}。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


# ── Image 生成 ───────────────────────────────────────────────────────────────── #
def gen_image1(array):
    """1 チャネル配列から画像を作る(gen_image1)。"""
    return _img(array)


def gen_image1_extern(array, width=None, height=None):
    """外部メモリ(1D/2D)から 1 チャネル画像を構成(gen_image1_extern)。"""
    a = _img(array)
    if width and height:
        return a.reshape(int(height), int(width))
    return a


def gen_image3(ch1, ch2, ch3):
    """3 チャネル配列から (H,W,3) 画像を作る(gen_image3)。"""
    return np.stack([_img(ch1), _img(ch2), _img(ch3)], axis=-1)


def gen_image3_extern(data, width, height):
    """外部メモリ(interleaved)から 3 チャネル画像を構成(gen_image3_extern)。"""
    return _img(data).reshape(int(height), int(width), 3)


def paint_xld(image, contour, value=1.0):
    """XLD 輪郭を画像へ描画(paint_xld)。"""
    out = _img(image).copy(); H, W = out.shape
    for a in contour["cs"]:
        rr = np.clip(a[:, 0].round().astype(int), 0, H - 1)
        cc = np.clip(a[:, 1].round().astype(int), 0, W - 1)
        out[rr, cc] = value
    return out


def shape_histo_all(image, region=None, bins=32):
    """しきい値を掃引して各レベルの領域面積を集めた形状ヒストグラム(shape_histo_all)。"""
    im = _img(image); m = np.ones(im.shape, bool) if region is None else np.asarray(region, bool)
    levels = np.linspace(0, 1, int(bins))
    areas = np.array([((im >= t) & m).sum() for t in levels])
    return {"levels": levels, "area": areas}


def shape_histo_point(image, row, col, bins=32):
    """指定点を含む連結領域の面積をしきい値ごとに集める(shape_histo_point)。"""
    from scipy import ndimage
    im = _img(image); levels = np.linspace(0, 1, int(bins))
    r, c = int(row), int(col); areas = []
    for t in levels:
        lab, _ = ndimage.label(im >= t)
        lv = lab[r, c]
        areas.append(int((lab == lv).sum()) if lv > 0 else 0)
    return {"levels": levels, "area": np.asarray(areas)}


# ── Regions ─────────────────────────────────────────────────────────────────── #
def gen_random_region(shape, area=100, seed=0):
    """ランダムな連結領域を生成(ランダムウォーク膨張)(gen_random_region)。"""
    from scipy.ndimage import binary_dilation
    rng = np.random.default_rng(seed)
    H, W = shape; m = np.zeros(shape, bool)
    m[rng.integers(0, H), rng.integers(0, W)] = True
    while m.sum() < area:
        m = binary_dilation(m)
        if m.sum() >= area:
            ys, xs = np.where(m)
            drop = rng.choice(len(ys), m.sum() - area, replace=False)
            m[ys[drop], xs[drop]] = False
            break
    return m


def gen_random_regions(shape, count=3, area=100, seed=0):
    """複数のランダム領域を生成(gen_random_regions)。"""
    return [gen_random_region(shape, area, seed + k) for k in range(int(count))]


def merge_regions_line_scan(runs_list, shape):
    """ラインスキャンのラン集合を連結して領域へ統合(merge_regions_line_scan)。
    runs_list: [(row, col_start, col_end), ...]。"""
    m = np.zeros(shape, bool)
    for row, c0, c1 in runs_list:
        m[int(row), int(c0):int(c1) + 1] = True
    from scipy import ndimage
    lab, n = ndimage.label(m)
    return {"region": m, "labels": lab, "num": n}


def select_shape_proto(regions, prototype, feature="area", max_diff=0.2):
    """プロトタイプ領域に形状特徴が近い領域を選ぶ(select_shape_proto)。"""
    def area(r): return np.asarray(r, bool).sum()

    def compactness(r):
        from scipy.ndimage import binary_erosion
        rb = np.asarray(r, bool); per = (rb & ~binary_erosion(rb)).sum()
        return per ** 2 / (4 * np.pi * rb.sum() + 1e-9)
    fn = {"area": area, "compactness": compactness}[feature]
    ref = fn(prototype)
    out = []
    for reg in regions:
        if abs(fn(reg) - ref) / (ref + 1e-9) <= max_diff:
            out.append(reg)
    return out


def expand_gray_ref(image, seed_region, ref_image, tol=0.05):
    """参照画像のグレー類似で seed を膨張(expand_gray_ref)。"""
    from scipy.ndimage import binary_dilation
    im = _img(image); ref = _img(ref_image)
    reg = np.asarray(seed_region, bool).copy()
    for _ in range(1000):
        cand = binary_dilation(reg) & ~reg & (np.abs(im - ref) < tol)
        if not cand.any():
            break
        reg |= cand
    return reg


def classify_image_class_knn(feature_images, train_features, train_labels, k=3):
    """k-NN で多チャネル特徴画像を画素分類(classify_image_class_knn)。"""
    from scipy.spatial import cKDTree
    F = feature_images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = _img(F); H, W, D = F.shape
    tree = cKDTree(np.asarray(train_features, float).reshape(-1, D))
    lab = np.asarray(train_labels).ravel()
    _, idx = tree.query(F.reshape(-1, D), k=int(k))
    if k == 1:
        pred = lab[idx]
    else:
        pred = np.array([np.bincount(lab[row]).argmax() for row in idx])
    return pred.reshape(H, W)
