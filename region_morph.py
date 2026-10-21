"""region 形態(HALCON "Morphology" chapter の genuine 追加, scipy)。"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _disc(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return xx * xx + yy * yy <= r * r


# On a 1024x1024 mixed mask, the structuring-element/EDT opening times crossed
# at radius 9 (78.1/62.5 ms, process_time median of 3, 2026-10-21).
_EDT_DISC_RADIUS = 9


def _disc_erosion(region, radius):
    if radius < _EDT_DISC_RADIUS:
        return ndimage.binary_erosion(region, structure=_disc(radius))
    padded = np.pad(region, radius, constant_values=False)
    distance = ndimage.distance_transform_edt(padded)
    return distance[radius:-radius, radius:-radius] > radius


def _disc_dilation(region, radius):
    if radius < _EDT_DISC_RADIUS:
        return ndimage.binary_dilation(region, structure=_disc(radius))
    if not region.any():
        return np.zeros_like(region, dtype=bool)
    padded = np.pad(region, radius, constant_values=False)
    distance = ndimage.distance_transform_edt(~padded)
    return distance[radius:-radius, radius:-radius] <= radius


def _disc_opening(region, radius):
    return _disc_dilation(_disc_erosion(region, radius), radius)


def _disc_closing(region, radius):
    return _disc_erosion(_disc_dilation(region, radius), radius)


def top_hat(region, size: int = 3):
    """region - opening(region): 小さな明構造を抽出(top_hat)。"""
    reg = np.asarray(region) > 0.5
    op = _disc_opening(reg, 1 + int(size))
    return (reg & ~op).astype(np.float64)


def bottom_hat(region, size: int = 3):
    """closing(region) - region: 小さな暗構造(隙間)を抽出(bottom_hat)。"""
    reg = np.asarray(region) > 0.5
    cl = _disc_closing(reg, 1 + int(size))
    return (cl & ~reg).astype(np.float64)


def hit_or_miss(region, size: int = 1):
    """hit-or-miss 変換: 前景を disc で erode ∧ 背景を disc で erode(hit_or_miss)。角/孤立点検出。"""
    reg = np.asarray(region) > 0.5
    fg = _disc_erosion(reg, int(size))
    bg = _disc_erosion(~reg, int(size) + 1)
    return (fg & bg).astype(np.float64)
