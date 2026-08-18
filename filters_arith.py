"""画素算術/ビット/N 画像統計フィルタ(HALCON "Filters" chapter の genuine 実装, numpy).

2 画像間演算と、画像スタックにわたる統計。image = 2D float64 [0,1]。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def _stack(images):
    return np.stack([_img(i) for i in images], axis=0)


def add_image(image1, image2, mult=1.0, add=0.0):
    """(image1+image2)*mult+add(add_image)。"""
    return (_img(image1) + _img(image2)) * mult + add


def sub_image(image1, image2, mult=1.0, add=0.0):
    """(image1-image2)*mult+add(sub_image)。"""
    return (_img(image1) - _img(image2)) * mult + add


def mult_image(image1, image2, mult=1.0, add=0.0):
    """image1*image2*mult+add(mult_image)。"""
    return _img(image1) * _img(image2) * mult + add


def div_image(image1, image2, mult=1.0, add=0.0):
    """image1/image2*mult+add(div_image)。0 除算は保護。"""
    b = _img(image2)
    return _img(image1) / np.where(np.abs(b) < 1e-12, np.nan, b) * mult + add


def abs_diff_image(image1, image2, mult=1.0):
    """|image1-image2|*mult(abs_diff_image)。"""
    return np.abs(_img(image1) - _img(image2)) * mult


def max_image(image1, image2):
    """画素ごとの最大(max_image)。"""
    return np.maximum(_img(image1), _img(image2))


def min_image(image1, image2):
    """画素ごとの最小(min_image)。"""
    return np.minimum(_img(image1), _img(image2))


def atan2_image(image1, image2):
    """atan2(image1, image2)(vector field の角度、atan2_image)。"""
    return np.arctan2(_img(image1), _img(image2))


def _to_int(a, bits=8):
    return np.clip((_img(a) * ((1 << bits) - 1)).round().astype(np.int64), 0, (1 << bits) - 1)


def bit_and(image1, image2, bits=8):
    """整数化した画素のビット AND(bit_and)。"""
    return (_to_int(image1, bits) & _to_int(image2, bits)) / ((1 << bits) - 1)


def bit_or(image1, image2, bits=8):
    """ビット OR(bit_or)。"""
    return (_to_int(image1, bits) | _to_int(image2, bits)) / ((1 << bits) - 1)


def bit_xor(image1, image2, bits=8):
    """ビット XOR(bit_xor)。"""
    return (_to_int(image1, bits) ^ _to_int(image2, bits)) / ((1 << bits) - 1)


def bit_not(image, bits=8):
    """ビット反転(bit_not)。"""
    return ((~_to_int(image, bits)) & ((1 << bits) - 1)) / ((1 << bits) - 1)


def mean_n(images):
    """画像スタックの画素平均(mean_n)。"""
    return _stack(images).mean(axis=0)


def deviation_n(images):
    """画像スタックの画素標準偏差(deviation_n)。"""
    return _stack(images).std(axis=0)


def min_max_gray_n(images):
    """スタックの画素最小/最大(min_image/max_image の N 版)。"""
    s = _stack(images)
    return {"min": s.min(axis=0), "max": s.max(axis=0)}


def midrange_image(image, mask_size=3):
    """局所 (min+max)/2 の midrange フィルタ(midrange_image)。"""
    from scipy.ndimage import minimum_filter, maximum_filter
    im = _img(image); k = int(mask_size)
    return (minimum_filter(im, k) + maximum_filter(im, k)) / 2.0


def rank_n(images, rank=None):
    """画像スタックの画素 rank 値(順位統計、rank_n)。既定は中央値。"""
    s = _stack(images)
    n = s.shape[0]
    r = n // 2 if rank is None else int(np.clip(rank, 0, n - 1))
    return np.sort(s, axis=0)[r]


def rank_image(image, mask_size=3, rank=None):
    """局所ウィンドウの順位統計フィルタ(rank_image)。既定は中央値。"""
    from scipy.ndimage import rank_filter, median_filter
    im = _img(image); k = int(mask_size)
    if rank is None:
        return median_filter(im, size=k)
    return rank_filter(im, rank=int(rank), size=k)


def scale_image(image, mult=1.0, add=0.0):
    """線形スケーリング image*mult+add(scale_image)。"""
    return _img(image) * mult + add


def invert_image(image):
    """グレー反転 1-image(invert_image)。"""
    return 1.0 - _img(image)
