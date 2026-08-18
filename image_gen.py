"""画像生成/ドメイン操作(HALCON "Image" chapter の genuine 実装, numpy).

定数画像・傾斜画像・多項式サーフェス画像の生成と、domain(ROI)操作。
image = 2D float64、region/domain = bool 2D。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def gen_image_const(width=64, height=64, value=0.0) -> np.ndarray:
    """定数値で満たした画像(gen_image_const)。"""
    return np.full((int(height), int(width)), float(value), dtype=np.float64)


def gen_image_gray_ramp(width=64, height=64, alpha=0.01, beta=0.01, mean=0.5) -> np.ndarray:
    """線形傾斜画像 g = alpha*(c-cx)+beta*(r-cy)+mean(gen_image_gray_ramp)。"""
    H, W = int(height), int(width)
    rr, cc = np.mgrid[0:H, 0:W]
    return alpha * (cc - W / 2) + beta * (rr - H / 2) + mean


def gen_image_surface_first_order(width, height, alpha, beta, gamma, row0=0, col0=0) -> np.ndarray:
    """1 次サーフェス画像 g = alpha*(c-col0)+beta*(r-row0)+gamma(gen_image_surface_first_order)。"""
    H, W = int(height), int(width)
    rr, cc = np.mgrid[0:H, 0:W]
    return alpha * (cc - col0) + beta * (rr - row0) + gamma


def gen_image_surface_second_order(width, height, params, row0=0, col0=0) -> np.ndarray:
    """2 次サーフェス画像 g = a*x^2+b*x*y+c*y^2+d*x+e*y+f(gen_image_surface_second_order)。"""
    a, b, c, d, e, f = params
    H, W = int(height), int(width)
    rr, cc = np.mgrid[0:H, 0:W]
    x = cc - col0; y = rr - row0
    return a * x * x + b * x * y + c * y * y + d * x + e * y + f


def gen_image1_rect(image, row, col, width, height) -> np.ndarray:
    """画像から矩形領域を切り出す(gen_image1_rect)。"""
    im = _img(image)
    r, c = int(row), int(col)
    return im[r:r + int(height), c:c + int(width)].copy()


def change_domain(image, region):
    """画像の domain(ROI)を region に変更(領域外を 0 マスク)(change_domain)。"""
    im = _img(image); m = np.asarray(region, bool)
    return {"image": np.where(m, im, 0.0), "domain": m}


def reduce_domain(image, region):
    """domain を region へ縮小(reduce_domain)。change_domain と同義の facade。"""
    return change_domain(image, region)


def get_domain(image):
    """画像の domain(非ゼロ/全域)を bool mask で返す(get_domain)。"""
    im = _img(image)
    return np.ones(im.shape, bool)


def crop_domain(image, region):
    """domain の外接矩形で画像を切り出す(crop_domain)。"""
    im = _img(image); m = np.asarray(region, bool)
    if not m.any():
        return im[:0, :0].copy()
    rs, cs = np.where(m)
    return im[rs.min():rs.max() + 1, cs.min():cs.max() + 1].copy()


def crop_domain_rel(image, region, top=0, left=0, bottom=0, right=0):
    """domain 外接矩形を相対マージン付きで切り出す(crop_domain_rel)。"""
    im = _img(image); m = np.asarray(region, bool)
    if not m.any():
        return im[:0, :0].copy()
    rs, cs = np.where(m)
    r0 = max(0, rs.min() + int(top)); r1 = min(im.shape[0], rs.max() + 1 - int(bottom))
    c0 = max(0, cs.min() + int(left)); c1 = min(im.shape[1], cs.max() + 1 - int(right))
    return im[r0:r1, c0:c1].copy()


def crop_rectangle2(image, row, col, phi, length1, length2) -> np.ndarray:
    """回転矩形 (row,col,phi,l1,l2) を切り出し軸並行化(crop_rectangle2)。"""
    from scipy.ndimage import rotate, map_coordinates
    im = _img(image)
    l1, l2 = float(length1), float(length2)
    h = int(2 * l2 + 1); w = int(2 * l1 + 1)
    jj, ii = np.meshgrid(np.arange(w) - l1, np.arange(h) - l2)
    ca, sa = np.cos(phi), np.sin(phi)
    src_c = col + jj * ca - ii * sa
    src_r = row + jj * sa + ii * ca
    return map_coordinates(im, [src_r.ravel(), src_c.ravel()], order=1).reshape(h, w)
