"""region 生成(HALCON "Regions" chapter の genuine 実装, numpy).

座標から二値 region(マスク)を生成する。点/線/多角形(輪郭・塗り)/実行長。
"""
from __future__ import annotations

import numpy as np


def gen_region_points(rows, cols, height=64, width=64):
    """個々の画素を region 化(gen_region_points)。"""
    m = np.zeros((int(height), int(width)), np.float64)
    r = np.clip(np.asarray(rows, int), 0, height - 1)
    c = np.clip(np.asarray(cols, int), 0, width - 1)
    m[r, c] = 1.0
    return m


def gen_region_line(row1, col1, row2, col2, height=64, width=64):
    """線分を region 化(gen_region_line、DDA)。"""
    m = np.zeros((int(height), int(width)), np.float64)
    n = int(max(abs(row2 - row1), abs(col2 - col1))) + 1
    rr = np.linspace(row1, row2, n).round().astype(int)
    cc = np.linspace(col1, col2, n).round().astype(int)
    ok = (rr >= 0) & (rr < height) & (cc >= 0) & (cc < width)
    m[rr[ok], cc[ok]] = 1.0
    return m


def gen_region_polygon(rows, cols, height=64, width=64):
    """多角形の輪郭を region 化(gen_region_polygon)。"""
    rows = np.asarray(rows, float); cols = np.asarray(cols, float)
    m = np.zeros((int(height), int(width)), np.float64)
    n = len(rows)
    for i in range(n):
        seg = gen_region_line(rows[i], cols[i], rows[(i + 1) % n], cols[(i + 1) % n], height, width)
        m = np.maximum(m, seg)
    return m


def gen_region_polygon_filled(rows, cols, height=64, width=64):
    """多角形を塗りつぶして region 化(gen_region_polygon_filled)。"""
    from matplotlib.path import Path
    poly = Path(np.column_stack([np.asarray(cols, float), np.asarray(rows, float)]))
    yy, xx = np.mgrid[0:int(height), 0:int(width)]
    pts = np.column_stack([xx.ravel(), yy.ravel()])
    return poly.contains_points(pts).reshape(int(height), int(width)).astype(np.float64)


def gen_region_runs(runs, height=64, width=64):
    """実行長符号 [(row, col_start, col_end), ...] から region を生成(gen_region_runs)。"""
    m = np.zeros((int(height), int(width)), np.float64)
    for r, c0, c1 in runs:
        m[int(r), int(c0):int(c1) + 1] = 1.0
    return m
