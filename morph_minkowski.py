"""Minkowski 形態学(HALCON "Morphology" chapter genuine, numpy/scipy).

Minkowski 和/差 と erosion2/dilation2(参照点つき構造要素)を本物の形態学で実装。
region = bool 2D、構造要素 se = bool 2D。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _r(x):
    return np.asarray(x, dtype=bool)


def minkowski_add1(region, se):
    """Minkowski 和(構造要素で膨張)(minkowski_add1)。"""
    return ndimage.binary_dilation(_r(region), structure=_r(se))


def minkowski_add2(region, se, iterations=1):
    """反復 Minkowski 和(minkowski_add2)。"""
    return ndimage.binary_dilation(_r(region), structure=_r(se), iterations=int(iterations))


def minkowski_sub1(region, se):
    """Minkowski 差(構造要素で収縮)(minkowski_sub1)。"""
    return ndimage.binary_erosion(_r(region), structure=_r(se))


def minkowski_sub2(region, se, iterations=1):
    """反復 Minkowski 差(minkowski_sub2)。"""
    return ndimage.binary_erosion(_r(region), structure=_r(se), iterations=int(iterations))


def erosion2(region, se, row=None, col=None):
    """参照点 (row,col) つき構造要素での収縮(erosion2)。"""
    se = _r(se)
    origin = (0, 0)
    if row is not None and col is not None:
        origin = (int(row - se.shape[0] // 2), int(col - se.shape[1] // 2))
    return ndimage.binary_erosion(_r(region), structure=se, origin=origin)


def dilation2(region, se, row=None, col=None):
    """参照点 (row,col) つき構造要素での膨張(dilation2)。"""
    se = _r(se)
    origin = (0, 0)
    if row is not None and col is not None:
        origin = (int(row - se.shape[0] // 2), int(col - se.shape[1] // 2))
    return ndimage.binary_dilation(_r(region), structure=se, origin=origin)
