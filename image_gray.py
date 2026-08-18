"""グレー値統計/特徴/ヒストグラム(HALCON "Image" chapter の genuine 実装, numpy).

領域(mask, bool 2D)内のグレー値統計を本物のアルゴリズムで実装。
image = 2D float64 [0,1]、region = bool 2D(省略時は全域)。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def _mask(region, shape):
    if region is None:
        return np.ones(shape, bool)
    return np.asarray(region, bool)


def area_center_gray(image, region=None):
    """グレー値を重みとした面積(質量)と重心 (row,col)(area_center_gray)。"""
    im = _img(image); m = _mask(region, im.shape)
    g = np.where(m, im, 0.0)
    total = g.sum()
    rr, cc = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    if total <= 1e-12:
        return {"area": 0.0, "row": 0.0, "column": 0.0}
    return {"area": float(total), "row": float((g * rr).sum() / total),
            "column": float((g * cc).sum() / total)}


def moments_gray_plane(image, region=None):
    """1 次グレーモーメント(平面近似係数 alpha,beta,mean)(moments_gray_plane)。"""
    im = _img(image); m = _mask(region, im.shape)
    rr, cc = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    r = rr[m].astype(float); c = cc[m].astype(float); g = im[m]
    A = np.column_stack([c - c.mean(), r - r.mean(), np.ones_like(c)])
    coef, *_ = np.linalg.lstsq(A, g, rcond=None)
    # Mean = 領域の平均グレー値(重心での値), alpha/beta = 列/行方向の勾配
    return {"alpha": float(coef[0]), "beta": float(coef[1]), "mean": float(g.mean())}


def elliptic_axis_gray(image, region=None):
    """グレー値重み 2 次モーメントの等価楕円 (ra, rb, phi)(elliptic_axis_gray)。"""
    im = _img(image); m = _mask(region, im.shape)
    g = np.where(m, im, 0.0); s = g.sum()
    rr, cc = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    if s <= 1e-12:
        return {"ra": 0.0, "rb": 0.0, "phi": 0.0}
    r0 = (g * rr).sum() / s; c0 = (g * cc).sum() / s
    m20 = (g * (cc - c0) ** 2).sum() / s
    m02 = (g * (rr - r0) ** 2).sum() / s
    m11 = (g * (cc - c0) * (rr - r0)).sum() / s
    cov = np.array([[m20, m11], [m11, m02]])
    w, v = np.linalg.eigh(cov)
    w = np.clip(w, 0, None)
    ra = float(2 * np.sqrt(w[1])); rb = float(2 * np.sqrt(w[0]))
    phi = float(np.arctan2(v[1, 1], v[0, 1]))
    return {"ra": ra, "rb": rb, "phi": phi}


def gray_histo(image, region=None, bins=256):
    """グレーヒストグラム(絶対度数と相対度数)(gray_histo)。"""
    im = _img(image); m = _mask(region, im.shape)
    vals = im[m]
    hist, edges = np.histogram(vals, bins=int(bins), range=(0.0, 1.0))
    rel = hist / max(1, hist.sum())
    return {"absolute": hist, "relative": rel, "edges": edges}


def gray_histo_range(image, region=None, minv=0.0, maxv=1.0, bins=256):
    """指定レンジのグレーヒストグラム(gray_histo_range)。"""
    im = _img(image); m = _mask(region, im.shape)
    hist, edges = np.histogram(im[m], bins=int(bins), range=(float(minv), float(maxv)))
    return {"absolute": hist, "edges": edges, "min": float(minv), "max": float(maxv)}


def gray_features(image, region=None):
    """領域のグレー特徴(mean/deviation/min/max/median/area)(gray_features)。"""
    im = _img(image); m = _mask(region, im.shape)
    v = im[m]
    if v.size == 0:
        return {k: 0.0 for k in ("mean", "deviation", "min", "max", "median", "area")}
    return {"mean": float(v.mean()), "deviation": float(v.std()), "min": float(v.min()),
            "max": float(v.max()), "median": float(np.median(v)), "area": float(v.size)}


def gray_projections(image, region=None):
    """行方向/列方向のグレー投影(gray_projections)。"""
    im = _img(image); m = _mask(region, im.shape)
    g = np.where(m, im, 0.0)
    return {"horizontal": g.sum(axis=1), "vertical": g.sum(axis=0)}


def histo_2dim(image1, image2, region=None, bins=64):
    """2 チャネルの 2 次元ヒストグラム(histo_2dim)。"""
    a = _img(image1); b = _img(image2); m = _mask(region, a.shape)
    H, _, _ = np.histogram2d(a[m], b[m], bins=int(bins), range=[[0, 1], [0, 1]])
    return H


def gen_cooc_matrix(image, region=None, ldgray=8, direction=0):
    """グレー共起行列 (GLCM)(gen_cooc_matrix)。direction=0/45/90/135 度。"""
    im = _img(image); m = _mask(region, im.shape)
    L = int(ldgray)
    q = np.clip((im * (L - 1)).round().astype(int), 0, L - 1)
    dr, dc = {0: (0, 1), 45: (-1, 1), 90: (-1, 0), 135: (-1, -1)}[int(direction)]
    P = np.zeros((L, L))
    H, W = q.shape
    for r in range(H):
        r2 = r + dr
        if not (0 <= r2 < H):
            continue
        for c in range(W):
            c2 = c + dc
            if 0 <= c2 < W and m[r, c] and m[r2, c2]:
                P[q[r, c], q[r2, c2]] += 1
    s = P.sum()
    return P / s if s > 0 else P


def cooc_feature_matrix(cooc):
    """GLCM から Haralick 特徴(energy/contrast/correlation/homogeneity)(cooc_feature_matrix)。"""
    P = np.asarray(cooc, float); L = P.shape[0]
    i, j = np.mgrid[0:L, 0:L]
    mu_i = (i * P).sum(); mu_j = (j * P).sum()
    si = np.sqrt(((i - mu_i) ** 2 * P).sum()); sj = np.sqrt(((j - mu_j) ** 2 * P).sum())
    corr = (((i - mu_i) * (j - mu_j) * P).sum() / (si * sj + 1e-12))
    return {"energy": float((P ** 2).sum()), "contrast": float(((i - j) ** 2 * P).sum()),
            "correlation": float(corr), "homogeneity": float((P / (1 + np.abs(i - j))).sum())}


def fuzzy_entropy(image, region=None, bins=256):
    """領域グレー分布の Shannon エントロピー(fuzzy_entropy)。"""
    h = gray_histo(image, region, bins)["relative"]
    p = h[h > 0]
    return float(-(p * np.log2(p)).sum())


def fuzzy_perimeter(image, region=None):
    """グレー勾配総和による fuzzy 周長(fuzzy_perimeter)。"""
    im = _img(image); m = _mask(region, im.shape)
    gy, gx = np.gradient(np.where(m, im, 0.0))
    return float(np.hypot(gx, gy)[m].sum())


def get_grayval(image, row, col):
    """(row,col) のグレー値を返す(最近傍)(get_grayval)。"""
    im = _img(image)
    r = int(np.clip(round(row), 0, im.shape[0] - 1))
    c = int(np.clip(round(col), 0, im.shape[1] - 1))
    return float(im[r, c])


def get_grayval_interpolated(image, row, col):
    """(row,col) の双一次補間グレー値(get_grayval_interpolated)。"""
    im = _img(image)
    r = np.clip(row, 0, im.shape[0] - 1.0); c = np.clip(col, 0, im.shape[1] - 1.0)
    r0, c0 = int(np.floor(r)), int(np.floor(c))
    r1 = min(r0 + 1, im.shape[0] - 1); c1 = min(c0 + 1, im.shape[1] - 1)
    fr, fc = r - r0, c - c0
    top = im[r0, c0] * (1 - fc) + im[r0, c1] * fc
    bot = im[r1, c0] * (1 - fc) + im[r1, c1] * fc
    return float(top * (1 - fr) + bot * fr)


def select_gray(image, regions, feature="mean", minv=0.0, maxv=1.0):
    """グレー特徴が [minv,maxv] に入る領域だけ選ぶ(select_gray)。regions=bool mask のリスト。"""
    out = []
    for reg in regions:
        f = gray_features(image, reg)[feature]
        if minv <= f <= maxv:
            out.append(reg)
    return out
