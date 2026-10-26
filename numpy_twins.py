# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""scikit-image の数本を numpy / scipy だけで**同じ答え**に写した双子(twins)。

scikit-image が無い環境(numpy + scipy だけの min 構成、ブラウザの Pyodide など)で、登録 op が
**別の答えを黙って返さない**ための代替経路。2026-10-25 の探針では、full では走る 488 op のうち 89 op が
min 構成で例外なく走って別の値を返していた(領域特徴 23 本が全部「面積率」、circle の構造要素が矩形、
skeleton が恒等写像、…)。ここにあるのは、そのうち **安く bit 一致で書けるもの** だけ。書けないもの
(find_contours / watershed / canny / frangi / convex_hull_image / rank.entropy / cv2 の幾何変換 …)は
:class:`backend_safe.MissingDependencyError` で fail-closed にする(``backends_auto`` 側)。

**正本は scikit-image**(BSD-3-Clause、(c) the scikit-image team)。各関数は同名の scikit-image 0.26 の
実装と同じ式・同じ演算順・同じ表(``G123_LUT`` / Euler 係数 / 周囲長の重み)で書いてあり、
``tests/test_numpy_twins_2026_10_25.py`` が実物と bit 一致(浮動小数は 4 ULP かつ 1e-12 以内)を乱数の
入力で確かめ、``tests/test_fallback_parity_2026_10_25.py`` が登録 op 単位で min / full の一致を確かめる。
**差が出たら twin が間違い**であって scikit-image が正。scikit-image が入っている環境では呼ばれない
(``backends_auto`` が import の成否で振り分ける)。

浮動小数の型は scikit-image と同じ規則(``_supported_float_type``: uint8 / int16 / float16 → float32、
それ以外 → float64)に従う —— ``regionprops`` は領域を uint8 に落としてから積率を取るので **float32** で
計算しており、ここで float64 にすると最下位の桁が合わない。
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy import ndimage as ndi

__all__ = [
    "disk", "threshold_otsu", "apply_hysteresis_threshold", "skeletonize", "thin",
    "remove_small_holes", "perimeter", "euler_number", "moments", "moments_central",
    "moments_normalized", "moments_hu", "inertia_tensor", "inertia_tensor_eigvals",
    "RegionTwin", "graycomatrix", "graycoprops", "structure_tensor", "corner_harris",
    "corner_foerstner", "supported_float_type",
]


# --------------------------------------------------------------------------- #
# dtype 規則                                                                   #
# --------------------------------------------------------------------------- #
_NEW_FLOAT_TYPE = {
    np.dtype(np.float32).char: np.float32, np.dtype(np.float64).char: np.float64,
    np.dtype(np.complex64).char: np.complex64, np.dtype(np.complex128).char: np.complex128,
    np.dtype(np.int8).char: np.float32, np.dtype(np.uint8).char: np.float32,
    np.dtype(np.int16).char: np.float32, np.dtype(np.uint16).char: np.float32,
    np.dtype(np.float16).char: np.float32,
}


def supported_float_type(dtype):
    """``skimage._shared.utils._supported_float_type``: 小さい整数・半精度は float32、それ以外は float64。"""
    dtype = np.dtype(dtype)
    if dtype.kind == "c":
        raise ValueError("complex valued input is not supported")
    return _NEW_FLOAT_TYPE.get(dtype.char, np.float64)


# --------------------------------------------------------------------------- #
# 構造要素                                                                     #
# --------------------------------------------------------------------------- #
def disk(radius, dtype=np.uint8):
    """``skimage.morphology.disk(radius)``(``strict_radius=True``、分解なし): ``X²+Y² <= r²`` の離散円。"""
    L = np.arange(-radius, radius + 1)
    X, Y = np.meshgrid(L, L)
    return np.array((X ** 2 + Y ** 2) <= radius ** 2, dtype=dtype)


# --------------------------------------------------------------------------- #
# しきい値                                                                     #
# --------------------------------------------------------------------------- #
def threshold_otsu(image, nbins=256):
    """``skimage.filters.threshold_otsu``(hist=None)。

    ヒストグラムは ``np.histogram(image.ravel(), nbins)``(範囲は画像の min..max)、ビン中心は辺の平均、
    度数は **float32** に落としてから累積する(``_validate_image_histogram`` と同じ)。
    """
    image = np.asarray(image)
    first_pixel = image.reshape(-1)[0]
    if np.all(image == first_pixel):
        return first_pixel
    flat = image.reshape(-1)
    if np.issubdtype(flat.dtype, np.integer):
        raise NotImplementedError("numpy_twins.threshold_otsu: integer images are not needed here (ops pass float)")
    counts, bin_edges = np.histogram(flat.flatten(), bins=nbins, range=None)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    counts = counts.astype("float32", copy=False)
    weight1 = np.cumsum(counts)
    weight2 = np.cumsum(counts[::-1])[::-1]
    mean1 = np.cumsum(counts * bin_centers) / weight1
    mean2 = (np.cumsum((counts * bin_centers)[::-1]) / weight2[::-1])[::-1]
    variance12 = weight1[:-1] * weight2[1:] * (mean1[:-1] - mean2[1:]) ** 2
    idx = np.argmax(variance12)
    return bin_centers[idx]


def apply_hysteresis_threshold(image, low, high):
    """``skimage.filters.apply_hysteresis_threshold``: ``> low`` の連結成分のうち ``> high`` を含むもの。"""
    image = np.asarray(image)
    low = np.clip(low, a_min=None, a_max=high)
    mask_low = image > low
    mask_high = image > high
    labels_low, num_labels = ndi.label(mask_low)
    sums = ndi.sum(mask_high, labels_low, np.arange(num_labels + 1))
    connected_to_high = sums > 0
    return connected_to_high[labels_low]


# --------------------------------------------------------------------------- #
# 骨格化・細線化                                                               #
# --------------------------------------------------------------------------- #
#: Zhang–Suen 細線化の判定表(scikit-image ``_skeletonize_various_cy.pyx`` の ``_fast_skeletonize`` の ``lut`` と
#: 同一。BSD-3-Clause、(c) the scikit-image team)。値 1 = 副反復 1 で削る、2 = 副反復 2 で削る、3 = 両方で削る。
#: インデックス = NW + 2·N + 4·NE + 8·E + 16·SE + 32·S + 64·SW + 128·W。
_ZHANG_LUT = np.array([
    0, 0, 0, 1, 0, 0, 1, 3, 0, 0, 3, 1, 1, 0, 1, 3, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 2, 0, 3, 0, 3, 3,
    0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 2, 2,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    2, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 3, 0, 2, 0,
    0, 0, 3, 1, 0, 0, 1, 3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1,
    3, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    2, 3, 1, 3, 0, 0, 1, 3, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    2, 3, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 0, 1, 0, 0, 0, 0, 2, 2, 0, 0, 2, 0, 0, 0,
], dtype=np.uint8)
assert _ZHANG_LUT.size == 256


def skeletonize(image):
    """``skimage.morphology.skeletonize``(2 次元、``method="zhang"``)—— Zhang–Suen の並列細線化。

    scikit-image の Cython ループ(``_fast_skeletonize``)をそのまま写した: 1 画素の零パディング、各副反復は
    **その副反復の開始時の画像**で 8 近傍の番号を作り、表 ``_ZHANG_LUT`` の値が 3、または副反復 1 で 1、副反復 2 で 2
    の画素を一斉に消す。消える画素が 1 つも無くなるまで繰り返す。
    """
    sk = np.pad(np.asarray(image).astype(bool), 1).astype(np.uint8)
    removed = True
    while removed:
        removed = False
        for first in (True, False):
            idx = (sk[:-2, :-2].astype(np.int32) + 2 * sk[:-2, 1:-1] + 4 * sk[:-2, 2:] + 8 * sk[1:-1, 2:]
                   + 16 * sk[2:, 2:] + 32 * sk[2:, 1:-1] + 64 * sk[2:, :-2] + 128 * sk[1:-1, :-2])
            v = _ZHANG_LUT[idx]
            kill = (sk[1:-1, 1:-1] == 1) & ((v == 3) | (v == (1 if first else 2)))
            if kill.any():
                removed = True
                sk[1:-1, 1:-1][kill] = 0
    return sk[1:-1, 1:-1].astype(bool)


#: Guo–Hall 細線化の削除表(scikit-image ``skimage/morphology/_skeletonize.py`` の ``G123_LUT`` /
#: ``G123P_LUT`` と同一。BSD-3-Clause、(c) the scikit-image team)。インデックスは近傍マスク
#: ``[[8, 4, 2], [16, 0, 1], [32, 64, 128]]`` との相関。
_G123_LUT = np.array([
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0,
    1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0,
], dtype=bool)
assert _G123_LUT.size == 256, _G123_LUT.size

_G123P_LUT = np.array([
    0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
], dtype=bool)
assert _G123P_LUT.size == 256, _G123P_LUT.size


def thin(image, max_num_iter=None):
    """``skimage.morphology.thin`` —— Guo–Hall の 2 副反復細線化(表引き)。純 numpy の実装をそのまま写した。"""
    skel = np.asanyarray(image, dtype=bool).copy().view(np.uint8)
    if skel.ndim != 2:
        raise ValueError("thin: 2-D image required")
    mask = np.array([[8, 4, 2], [16, 0, 1], [32, 64, 128]], dtype=np.uint8)
    max_num_iter = max_num_iter or np.inf
    num_iter = 0
    n_pts_old, n_pts_new = np.inf, np.sum(skel)
    while n_pts_old != n_pts_new and num_iter < max_num_iter:
        n_pts_old = n_pts_new
        for lut in (_G123_LUT, _G123P_LUT):
            N = ndi.correlate(skel, mask, mode="constant")
            D = np.take(lut, N)
            skel[D] = 0
        n_pts_new = np.sum(skel)
        num_iter += 1
    return skel.astype(bool)


# --------------------------------------------------------------------------- #
# 領域の後処理・計測                                                           #
# --------------------------------------------------------------------------- #
def remove_small_holes(ar, area_threshold, connectivity=1):
    """``skimage.morphology.remove_small_holes(ar, area_threshold=N)`` —— 補集合の成分のうち面積 ``<= N`` のものを埋める。

    ★scikit-image 0.26 では ``area_threshold`` は非推奨名で、デコレータが ``max_size``(**以下**、inclusive)に写す。
    したがって ``area_threshold=100`` で面積ちょうど 100 の穴も埋まる(乱数の塊で実測して合わせた。0.25 以前の
    ``min_size``(未満)とは 1 だけ違う)。登録 op ``fill_up_shape`` は ``area_threshold=`` で呼んでいるので、
    この双子もその呼び方に合わせる。
    """
    ar = np.asarray(ar, bool)
    out = np.logical_not(ar)
    footprint = ndi.generate_binary_structure(ar.ndim, connectivity)
    ccs = np.zeros_like(ar, dtype=np.int32)
    ndi.label(out, footprint, output=ccs)
    component_sizes = np.bincount(ccs.ravel())
    too_small = component_sizes <= area_threshold          # 0.26: max_size (inclusive)
    out[too_small[ccs]] = 0
    return np.logical_not(out)


_STREL_4 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
_STREL_8 = np.ones((3, 3), dtype=np.uint8)


def perimeter(image, neighborhood=4):
    """``skimage.measure.perimeter``(Benkrid / Crookes の重み付き境界画素数)。"""
    image = np.asarray(image)
    if image.ndim != 2:
        raise NotImplementedError("`perimeter` supports 2D images only")
    strel = _STREL_4 if neighborhood == 4 else _STREL_8
    image = image.astype(np.uint8)
    eroded_image = ndi.binary_erosion(image, strel, border_value=0)
    border_image = image - eroded_image
    perimeter_weights = np.zeros(50, dtype=np.float64)
    perimeter_weights[[5, 7, 15, 17, 25, 27]] = 1
    perimeter_weights[[21, 33]] = math.sqrt(2)
    perimeter_weights[[13, 23]] = (1 + math.sqrt(2)) / 2
    perimeter_image = ndi.convolve(border_image, np.array([[10, 2, 10], [2, 1, 2], [10, 2, 10]]),
                                   mode="constant", cval=0)
    perimeter_histogram = np.bincount(perimeter_image.ravel(), minlength=50)
    return perimeter_histogram @ perimeter_weights


#: ``skimage.measure._regionprops_utils.EULER_COEFS2D_{4,8}``(BSD-3-Clause、(c) the scikit-image team)。
_EULER_COEFS2D_8 = np.array([0, 0, 0, 0, 0, 0, -1, 0, 1, 0, 0, 0, 0, 0, -1, 0])
_EULER_COEFS2D_4 = np.array([0, 1, 0, 0, 0, 0, 0, -1, 0, 1, 0, 0, 0, 0, 0, 0])


def euler_number(image, connectivity=None):
    """``skimage.measure.euler_number``(2 次元。既定は 8 連結 = ``connectivity=2``)。"""
    image = (np.asarray(image) > 0).astype(int)
    if image.ndim != 2:
        raise NotImplementedError("numpy_twins.euler_number: 2-D only")
    image = np.pad(image, pad_width=1, mode="constant")
    if connectivity is None:
        connectivity = image.ndim
    config = np.array([[0, 0, 0], [0, 1, 4], [0, 2, 8]])
    coefs = _EULER_COEFS2D_4 if connectivity == 1 else _EULER_COEFS2D_8
    XF = ndi.convolve(image, config, mode="constant", cval=0)
    h = np.bincount(XF.ravel(), minlength=16)
    return coefs @ h


# --------------------------------------------------------------------------- #
# 積率(moments)                                                               #
# --------------------------------------------------------------------------- #
def _moments_central_einsum(image, center, order, spacing=None):
    float_dtype = supported_float_type(image.dtype)
    if spacing is None:
        spacing = np.ones(image.ndim, dtype=float_dtype)
    calc = image.astype(float_dtype, copy=False)
    L = list(range(image.ndim))
    sum_label = image.ndim
    order_label = sum_label + 1
    orders = np.arange(order + 1, dtype=float_dtype)
    for dim, dim_length in enumerate(image.shape):
        delta = np.arange(dim_length, dtype=float_dtype) * spacing[dim] - center[dim]
        powers_of_delta = delta[:, np.newaxis] ** orders
        calc = np.einsum(calc, L[:dim] + [sum_label] + L[dim + 1:], powers_of_delta,
                         [sum_label, order_label], L[:dim] + [order_label] + L[dim + 1:],
                         optimize="greedy")
    return calc


def moments(image, order=3, spacing=None):
    """``skimage.measure.moments``: 原点まわりの生の積率(einsum、dtype は入力の規則に従う)。

    ``spacing`` を float64 で渡すと ``delta`` が float64 に昇格して計算全体が float64 になる —— ``regionprops`` は
    ``spacing=np.full(ndim, 1.0)`` を渡すので、uint8 の領域でも積率は float64 で出る(渡さなければ float32)。
    """
    image = np.asarray(image)
    return _moments_central_einsum(image, (0,) * image.ndim, order, spacing)


def _moments_raw_to_central_fast(m_raw):
    """``skimage.measure._moments_analytical._moments_raw_to_central_fast``(2 次元、order < 4)。"""
    float_dtype = m_raw.dtype
    m = m_raw.astype(np.float64, copy=False)
    order = m.shape[0] - 1
    mc = np.zeros_like(m)
    cx = m[1, 0] / m[0, 0]
    cy = m[0, 1] / m[0, 0]
    mc[0, 0] = m[0, 0]
    if order > 1:
        mc[1, 1] = m[1, 1] - cx * m[0, 1]
        mc[2, 0] = m[2, 0] - cx * m[1, 0]
        mc[0, 2] = m[0, 2] - cy * m[0, 1]
    if order > 2:
        mc[2, 1] = (m[2, 1] - 2 * cx * m[1, 1] - cy * m[2, 0] + cx ** 2 * m[0, 1] + cy * cx * m[1, 0])
        mc[1, 2] = (m[1, 2] - 2 * cy * m[1, 1] - cx * m[0, 2] + 2 * cy * cx * m[0, 1])
        mc[3, 0] = m[3, 0] - 3 * cx * m[2, 0] + 2 * cx ** 2 * m[1, 0]
        mc[0, 3] = m[0, 3] - 3 * cy * m[0, 2] + 2 * cy ** 2 * m[0, 1]
    return mc.astype(float_dtype, copy=False)


def moments_central(image, center=None, order=3, spacing=None):
    """``skimage.measure.moments_central``: ``center=None`` なら生の積率から解析式で(fast path)、与えれば einsum で。"""
    image = np.asarray(image)
    if image.ndim != 2 or order > 3:
        raise NotImplementedError("numpy_twins.moments_central: 2-D, order <= 3 only")
    if center is None:
        return _moments_raw_to_central_fast(moments(image, order=order, spacing=spacing))
    return _moments_central_einsum(image, center, order, spacing)


def moments_normalized(mu, order=3):
    """``skimage.measure.moments_normalized``(spacing なし)。次数 2 未満は NaN。"""
    mu = np.asarray(mu)
    if np.any(np.array(mu.shape) <= order):
        raise ValueError("Shape of image moments must be >= `order`")
    nu = np.zeros_like(mu)
    mu0 = mu.ravel()[0]
    scale = 1.0
    for powers in itertools.product(range(order + 1), repeat=mu.ndim):
        if sum(powers) < 2:
            nu[powers] = np.nan
        else:
            nu[powers] = (mu[powers] / scale ** sum(powers)) / (mu0 ** (sum(powers) / nu.ndim + 1))
    return nu


def moments_hu(nu):
    """``skimage.measure.moments_hu``(Cython ``_moments_cy.moments_hu`` と同じ演算順、7 値)。"""
    nu = np.asarray(nu)
    dtype = np.float32 if nu.dtype == np.float32 else np.float64
    nu = nu.astype(dtype, copy=False)
    hu = np.zeros(7, dtype=dtype)
    t0 = nu[3, 0] + nu[1, 2]
    t1 = nu[2, 1] + nu[0, 3]
    q0 = t0 * t0
    q1 = t1 * t1
    n4 = 4 * nu[1, 1]
    s = nu[2, 0] + nu[0, 2]
    d = nu[2, 0] - nu[0, 2]
    hu[0] = s
    hu[1] = d * d + n4 * nu[1, 1]
    hu[3] = q0 + q1
    hu[5] = d * (q0 - q1) + n4 * t0 * t1
    t0 *= q0 - 3 * q1
    t1 *= 3 * q0 - q1
    q0 = nu[3, 0] - 3 * nu[1, 2]
    q1 = 3 * nu[2, 1] - nu[0, 3]
    hu[2] = q0 * q0 + q1 * q1
    hu[4] = q0 * t0 + q1 * t1
    hu[6] = q1 * t0 - q0 * t1
    return hu


def inertia_tensor(mu):
    """``skimage.measure.inertia_tensor(image, mu)``(2 次元、spacing なし)。"""
    mu = np.asarray(mu)
    ndim = mu.ndim
    mu0 = mu[(0,) * ndim]
    result = np.zeros((ndim, ndim), dtype=mu.dtype)
    corners2 = tuple(2 * np.eye(ndim, dtype=int))
    d = np.diag(result)
    d.flags.writeable = True
    d[:] = (np.sum(mu[corners2]) - mu[corners2]) / mu0
    for dims in itertools.combinations(range(ndim), 2):
        mu_index = np.zeros(ndim, dtype=int)
        mu_index[list(dims)] = 1
        result[dims] = -mu[tuple(mu_index)] / mu0
        result.T[dims] = -mu[tuple(mu_index)] / mu0
    return result


def inertia_tensor_eigvals(T):
    """``skimage.measure.inertia_tensor_eigvals(T=T)``: 固有値を 0 で下から切り、降順に。"""
    eigvals = np.linalg.eigvalsh(T)
    eigvals = np.clip(eigvals, 0, None, out=eigvals)
    return sorted(eigvals, reverse=True)


class RegionTwin:
    """``skimage.measure.regionprops(mask.astype(int))[0]`` のうち、fullseye の領域特徴 op が読む属性だけの双子。

    ``image`` は外接矩形で切った bool、積率は uint8 に落としてから(= float32 で)取る —— regionprops と同じ。
    ``area_convex`` は双子を持たない(``convex_hull_image`` の格子点判定は Cython で、bit 一致の numpy 版が無い)
    ので :class:`backend_safe.MissingDependencyError` を投げる。
    """

    def __init__(self, mask):
        m = np.asarray(mask, bool)
        if m.ndim != 2:
            raise ValueError("RegionTwin: 2-D mask required")
        ys, xs = np.nonzero(m)
        if ys.size == 0:
            raise ValueError("RegionTwin: empty region")
        self.slice = (slice(int(ys.min()), int(ys.max()) + 1), slice(int(xs.min()), int(xs.max()) + 1))
        self.image = m[self.slice]
        self._ndim = 2
        self._spacing = np.full(self._ndim, 1.0)      # regionprops と同じ: float64 の 1.0(積率を float64 に昇格させる)

    @property
    def area(self):
        return np.sum(self.image) * 1.0

    @property
    def bbox(self):
        return (self.slice[0].start, self.slice[1].start, self.slice[0].stop, self.slice[1].stop)

    @property
    def image_filled(self):
        return ndi.binary_fill_holes(self.image, np.ones((3,) * self._ndim))

    @property
    def area_filled(self):
        return np.sum(self.image_filled) * 1.0

    @property
    def perimeter(self):
        return perimeter(self.image, 4) * 1.0

    @property
    def moments(self):
        return moments(self.image.astype(np.uint8), 3, spacing=self._spacing)

    @property
    def centroid_local(self):
        M = self.moments
        M0 = M[(0,) * self._ndim]
        return np.asarray(tuple(M[(0,) * ax + (1,) + (0,) * (self._ndim - 1 - ax)] / M0 for ax in range(self._ndim)))

    @property
    def moments_central(self):
        return moments_central(self.image.astype(np.uint8), self.centroid_local, order=3, spacing=self._spacing)

    @property
    def inertia_tensor(self):
        return inertia_tensor(self.moments_central)

    @property
    def inertia_tensor_eigvals(self):
        return inertia_tensor_eigvals(self.inertia_tensor)

    @property
    def orientation(self):
        a, b, b, c = self.inertia_tensor.flat
        if a - c == 0:
            return math.pi / 4.0 if b < 0 else -math.pi / 4.0
        return 0.5 * math.atan2(-2 * b, c - a)

    @property
    def axis_major_length(self):
        return 4 * math.sqrt(self.inertia_tensor_eigvals[0])

    @property
    def axis_minor_length(self):
        return 4 * math.sqrt(self.inertia_tensor_eigvals[-1])

    @property
    def area_convex(self):
        from backend_safe import missing_dependency
        raise missing_dependency("skimage", "convex-hull area (skimage.morphology.convex_hull_image) has no "
                                            "bit-exact numpy twin")

    @property
    def solidity(self):
        return self.area / self.area_convex


# --------------------------------------------------------------------------- #
# テクスチャ(GLCM)                                                            #
# --------------------------------------------------------------------------- #
def graycomatrix(image, distances, angles, levels=None, symmetric=False, normed=False):
    """``skimage.feature.graycomatrix``。共起の数え方(オフセット = ``round(sin·d), round(cos·d)``)は ``_glcm_loop`` と同じ。"""
    image = np.ascontiguousarray(image)
    if image.ndim != 2:
        raise ValueError("graycomatrix: 2-D image required")
    if np.issubdtype(image.dtype, np.floating):
        raise ValueError("Float images are not supported by graycomatrix. Convert the image to an unsigned integer type.")
    if levels is None:
        levels = 256
    if image.max() >= levels:
        raise ValueError("The maximum grayscale value in the image should be smaller than the number of levels.")
    distances = np.ascontiguousarray(distances, dtype=np.float64)
    angles = np.ascontiguousarray(angles, dtype=np.float64)
    P = np.zeros((levels, levels, len(distances), len(angles)), dtype=np.uint32, order="C")
    rows, cols = image.shape
    img = image.astype(np.int64)
    for d_idx, dist in enumerate(distances):
        for a_idx, ang in enumerate(angles):
            orow = int(round(math.sin(ang) * dist))
            ocol = int(round(math.cos(ang) * dist))
            r0, r1 = max(0, -orow), min(rows, rows - orow)
            c0, c1 = max(0, -ocol), min(cols, cols - ocol)
            if r1 <= r0 or c1 <= c0:
                continue
            i = img[r0:r1, c0:c1].ravel()
            j = img[r0 + orow:r1 + orow, c0 + ocol:c1 + ocol].ravel()
            ok = (i >= 0) & (i < levels) & (j >= 0) & (j < levels)
            cnt = np.bincount((i[ok] * levels + j[ok]), minlength=levels * levels)
            P[:, :, d_idx, a_idx] = cnt.reshape(levels, levels).astype(np.uint32)
    if symmetric:
        Pt = np.transpose(P, (1, 0, 2, 3))
        P = P + Pt
    if normed:
        P = P.astype(np.float64)
        glcm_sums = np.sum(P, axis=(0, 1), keepdims=True)
        glcm_sums[glcm_sums == 0] = 1
        P /= glcm_sums
    return P


def graycoprops(P, prop="contrast"):
    """``skimage.feature.graycoprops``(全 prop、同じ式・同じ演算順)。"""
    P = np.asarray(P)
    if P.ndim != 4:
        raise ValueError("graycoprops: P must be 4-D")
    (num_level, num_level2, num_dist, num_angle) = P.shape
    if num_level != num_level2:
        raise ValueError("num_level and num_level2 must be equal.")
    P = P.astype(np.float64)
    glcm_sums = np.sum(P, axis=(0, 1), keepdims=True)
    glcm_sums[glcm_sums == 0] = 1
    P /= glcm_sums
    I, J = np.ogrid[0:num_level, 0:num_level]

    def glcm_mean():
        Ii = np.arange(num_level).reshape((num_level, 1, 1, 1))
        return Ii, np.sum(Ii * P, axis=(0, 1))

    if prop == "contrast":
        weights = (I - J) ** 2
    elif prop == "dissimilarity":
        weights = np.abs(I - J)
    elif prop == "homogeneity":
        weights = 1.0 / (1.0 + (I - J) ** 2)
    elif prop in ("ASM", "energy", "correlation", "entropy", "variance", "mean", "std"):
        weights = None
    else:
        raise ValueError(f"{prop} is an invalid property")
    if prop == "energy":
        return np.sqrt(np.sum(P ** 2, axis=(0, 1)))
    if prop == "ASM":
        return np.sum(P ** 2, axis=(0, 1))
    if prop == "mean":
        return glcm_mean()[1]
    if prop == "variance":
        Ii, mean = glcm_mean()
        return np.sum(P * ((Ii - mean) ** 2), axis=(0, 1))
    if prop == "std":
        Ii, mean = glcm_mean()
        return np.sqrt(np.sum(P * ((Ii - mean) ** 2), axis=(0, 1)))
    if prop == "entropy":
        ln = -np.log(P, where=(P != 0), out=np.zeros_like(P))
        return np.sum(P * ln, axis=(0, 1))
    if prop == "correlation":
        results = np.zeros((num_dist, num_angle), dtype=np.float64)
        Ii = np.array(range(num_level)).reshape((num_level, 1, 1, 1))
        Jj = np.array(range(num_level)).reshape((1, num_level, 1, 1))
        diff_i = Ii - np.sum(Ii * P, axis=(0, 1))
        diff_j = Jj - np.sum(Jj * P, axis=(0, 1))
        std_i = np.sqrt(np.sum(P * (diff_i) ** 2, axis=(0, 1)))
        std_j = np.sqrt(np.sum(P * (diff_j) ** 2, axis=(0, 1)))
        cov = np.sum(P * (diff_i * diff_j), axis=(0, 1))
        mask_0 = std_i < 1e-15
        mask_0[std_j < 1e-15] = True
        results[mask_0] = 1
        mask_1 = ~mask_0
        results[mask_1] = cov[mask_1] / (std_i[mask_1] * std_j[mask_1])
        return results
    weights = weights.reshape((num_level, num_level, 1, 1))
    return np.sum(P * weights, axis=(0, 1))


# --------------------------------------------------------------------------- #
# コーナー(構造テンソル)                                                     #
# --------------------------------------------------------------------------- #
def structure_tensor(image, sigma=1, mode="constant", cval=0):
    """``skimage.feature.structure_tensor(image, sigma, order="rc")``(float 入力): Sobel 微分の積をガウスで平滑化。"""
    image = np.asarray(image)
    if image.dtype.kind != "f":
        raise NotImplementedError("numpy_twins.structure_tensor: float images only (ops pass float64)")
    derivatives = [ndi.sobel(image, axis=i, mode=mode, cval=cval) for i in range(image.ndim)]
    out = []
    for der0, der1 in itertools.combinations_with_replacement(derivatives, 2):
        prod = der0 * der1
        buf = np.empty_like(prod)
        ndi.gaussian_filter(prod, sigma, output=buf, mode=mode, cval=cval, truncate=4.0)
        out.append(buf)
    return out


def corner_harris(image, method="k", k=0.05, eps=1e-6, sigma=1):
    """``skimage.feature.corner_harris``。"""
    Arr, Arc, Acc = structure_tensor(image, sigma)
    detA = Arr * Acc - Arc ** 2
    traceA = Arr + Acc
    if method == "k":
        return detA - k * traceA ** 2
    return 2 * detA / (traceA + eps)


def corner_foerstner(image, sigma=1):
    """``skimage.feature.corner_foerstner``: ``(w, q)``。"""
    Arr, Arc, Acc = structure_tensor(image, sigma)
    detA = Arr * Acc - Arc ** 2
    traceA = Arr + Acc
    w = np.zeros_like(image, dtype=detA.dtype)
    q = np.zeros_like(w)
    mask = traceA != 0
    w[mask] = detA[mask] / traceA[mask]
    q[mask] = 4 * detA[mask] / traceA[mask] ** 2
    return w, q
