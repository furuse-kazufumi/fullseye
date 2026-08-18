"""region 形態(HALCON "Morphology" chapter の genuine 追加, scipy)。"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _disc(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return xx * xx + yy * yy <= r * r


def top_hat(region, size: int = 3):
    """region - opening(region): 小さな明構造を抽出(top_hat)。"""
    reg = np.asarray(region) > 0.5
    op = ndimage.binary_opening(reg, structure=_disc(1 + int(size)))
    return (reg & ~op).astype(np.float64)


def bottom_hat(region, size: int = 3):
    """closing(region) - region: 小さな暗構造(隙間)を抽出(bottom_hat)。"""
    reg = np.asarray(region) > 0.5
    cl = ndimage.binary_closing(reg, structure=_disc(1 + int(size)))
    return (cl & ~reg).astype(np.float64)


def hit_or_miss(region, size: int = 1):
    """hit-or-miss 変換: 前景を disc で erode ∧ 背景を disc で erode(hit_or_miss)。角/孤立点検出。"""
    reg = np.asarray(region) > 0.5
    fg = ndimage.binary_erosion(reg, structure=_disc(int(size)))
    bg = ndimage.binary_erosion(~reg, structure=_disc(int(size) + 1))
    return (fg & bg).astype(np.float64)
