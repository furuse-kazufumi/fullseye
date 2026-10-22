"""画像生成/ドメイン操作(HALCON "Image" chapter の genuine 実装, numpy).

定数画像・傾斜画像・多項式サーフェス画像の生成と、domain(ROI)操作。
image = 2D float64、region/domain = bool 2D。
"""
from __future__ import annotations

import numpy as np

from fslib import FsTypeError, FsValueError


def _img(a, operator="image operator"):
    try:
        value = np.asarray(a)
    except (TypeError, ValueError) as exc:
        raise FsTypeError("%s: image input must be a numeric 2-D array: %s" %
                          (operator, exc)) from exc
    if value.ndim != 2 or value.dtype.kind not in "biuf":
        raise FsTypeError("%s: image input must be a numeric 2-D array, got shape %r and dtype %s"
                          % (operator, value.shape, value.dtype))
    image = value.astype(np.float64, copy=False)
    if not np.isfinite(image).all():
        raise FsValueError("%s: image input contains NaN or infinity" % operator)
    return image


def _region(value, shape, operator):
    """Validate a domain mask: bool, or a numeric 0/1 mask (the documented list form).

    A numeric array with values other than 0 and 1 is not a mask (it is most
    likely an image passed in the region's place) and is rejected instead of
    being silently thresholded.
    """
    try:
        mask = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise FsTypeError("%s: region input must be a bool 2-D array: %s" %
                          (operator, exc)) from exc
    if mask.ndim != 2 or mask.dtype.kind not in "biu" and mask.dtype.kind != "f":
        raise FsTypeError("%s: region input must be a bool 2-D array, got shape %r and dtype %s"
                          % (operator, mask.shape, mask.dtype))
    if mask.dtype != np.bool_:
        if mask.size and not np.isin(mask, (0, 1)).all():
            raise FsTypeError("%s: region input must be a bool or 0/1 mask, got values outside {0, 1} (dtype %s)"
                              % (operator, mask.dtype))
        mask = mask.astype(bool)
    if mask.shape != shape:
        raise FsValueError("%s: image shape %r does not match region shape %r" %
                           (operator, shape, mask.shape))
    return mask


def _as_image_domain(value, operator="image operator"):
    """Return an image and its explicit domain, accepting either public form."""
    if isinstance(value, dict):
        if "image" not in value or "domain" not in value:
            raise FsTypeError("%s: domain image requires image and domain keys" % operator)
        im = _img(value["image"], operator)
        domain = _region(value["domain"], im.shape, operator)
        if domain.shape != im.shape:
            raise ValueError("image and domain must have the same shape")
        return im, domain
    im = _img(value, operator)
    return im, np.ones(im.shape, dtype=bool)


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


def change_domain(image, region, *, keep_pixels: bool = False):
    """Replace the domain with ``region``.

    An empty region is valid and returns a dictionary whose ``image`` is a
    float64 array and whose ``domain`` is an all-false bool array of the input
    shape. The default zeroes outside pixels for compatibility. ``keep_pixels=True``
    retains the untouched matrix, which is the HALCON reference policy.
    Example: ``change_domain(np.ones((2, 2)), [[1, 0], [0, 0]], keep_pixels=True)``.
    """
    im, _ = _as_image_domain(image, "change_domain")
    m = _region(region, im.shape, "change_domain")
    if not isinstance(keep_pixels, (bool, np.bool_)):
        raise FsTypeError("change_domain: keep_pixels must be a bool")
    return {"image": im.copy() if keep_pixels else np.where(m, im, 0.0), "domain": m}


def reduce_domain(image, region, *, keep_pixels: bool = False):
    """Intersect the existing domain with ``region``.

    An empty region is valid and returns a dictionary whose ``image`` is a
    float64 array and whose ``domain`` is an all-false bool array of the input
    shape. The default zeroes outside pixels for compatibility. ``keep_pixels=True``
    retains the untouched matrix, which is the HALCON reference policy. Plain
    arrays start with a full domain. Array-only consumers ignore explicit
    domains; the functions in this module which accept dictionaries preserve
    them. Example: ``reduce_domain(np.ones((2, 2)), [[1, 0], [0, 0]], keep_pixels=True)``.
    """
    if not isinstance(keep_pixels, (bool, np.bool_)):
        raise FsTypeError("reduce_domain: keep_pixels must be a bool")
    im, domain = _as_image_domain(image, "reduce_domain")
    m = domain & _region(region, im.shape, "reduce_domain")
    return {"image": im.copy() if keep_pixels else np.where(m, im, 0.0), "domain": m}


def get_domain(image):
    """画像の domain を bool mask で返す(get_domain)。素の配列には domain の概念が無いので**常に全面 True**。

    (2026-10-02 訂正: 以前は「非ゼロ/全域」と書いていたが、実装は値によらず全面を返す。公開済みの
    ``hx_get_domain`` と同じ答え。非ゼロの画素が欲しいなら ``image != 0``。)
    """
    _, domain = _as_image_domain(image)
    return domain.copy()


def crop_domain(image, region, *, keep_pixels: bool = False):
    """domain の外接矩形で画像を切り出す(crop_domain)。"""
    if not isinstance(keep_pixels, (bool, np.bool_)):
        raise ValueError("keep_pixels must be a bool")
    is_domain_image = isinstance(image, dict)
    im, domain = _as_image_domain(image); m = np.asarray(region, bool)
    if not m.any():
        cropped = im[:0, :0].copy()
        return {"image": cropped, "domain": domain[:0, :0].copy()} if is_domain_image else cropped
    rs, cs = np.where(m)
    sl = (slice(rs.min(), rs.max() + 1), slice(cs.min(), cs.max() + 1))
    cropped = im[sl].copy()
    return {"image": cropped, "domain": domain[sl].copy()} if is_domain_image else cropped


def crop_domain_rel(image, region, top=0, left=0, bottom=0, right=0, *, keep_pixels: bool = False):
    """domain 外接矩形を相対マージン付きで切り出す(crop_domain_rel)。"""
    if not isinstance(keep_pixels, (bool, np.bool_)):
        raise ValueError("keep_pixels must be a bool")
    is_domain_image = isinstance(image, dict)
    im, domain = _as_image_domain(image); m = np.asarray(region, bool)
    if not m.any():
        cropped = im[:0, :0].copy()
        return {"image": cropped, "domain": domain[:0, :0].copy()} if is_domain_image else cropped
    rs, cs = np.where(m)
    r0 = max(0, rs.min() + int(top)); r1 = min(im.shape[0], rs.max() + 1 - int(bottom))
    c0 = max(0, cs.min() + int(left)); c1 = min(im.shape[1], cs.max() + 1 - int(right))
    sl = (slice(r0, r1), slice(c0, c1))
    cropped = im[sl].copy()
    return {"image": cropped, "domain": domain[sl].copy()} if is_domain_image else cropped


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
