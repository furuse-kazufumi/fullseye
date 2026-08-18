"""領域(region)集合演算・述語・空間関係(HALCON "Regions" chapter genuine, numpy).

region = bool 2D mask。集合代数・包含判定・Hamming 距離・空間関係・生成・アクセスを
本物の配列/幾何演算で実装。歩行 Physical AI の踏み場領域処理を支える。
"""
from __future__ import annotations

import numpy as np


def _r(x):
    return np.asarray(x, dtype=bool)


# ── 集合代数 ─────────────────────────────────────────────────────────────────── #
def difference(region, sub):
    """領域差 region \\ sub(difference)。"""
    return _r(region) & ~_r(sub)


def intersection(region1, region2):
    """領域積(intersection)。"""
    return _r(region1) & _r(region2)


def union2(region1, region2):
    """領域和(union2)。"""
    return _r(region1) | _r(region2)


def symm_difference(region1, region2):
    """対称差(symm_difference)。"""
    return _r(region1) ^ _r(region2)


# ── 述語 ─────────────────────────────────────────────────────────────────────── #
def test_equal_region(region1, region2):
    """2 領域が等しいか(test_equal_region)。"""
    return bool(np.array_equal(_r(region1), _r(region2)))


def test_subset_region(region1, region2):
    """region1 ⊆ region2 か(test_subset_region)。"""
    r1 = _r(region1)
    return bool((r1 & ~_r(region2)).sum() == 0)


def hamming_distance(region1, region2):
    """2 領域の Hamming 距離(異なる画素数)(hamming_distance)。"""
    return int((_r(region1) ^ _r(region2)).sum())


def hamming_distance_norm(region1, region2):
    """正規化 Hamming 距離(差分画素 / 和集合画素)(hamming_distance_norm)。"""
    r1 = _r(region1); r2 = _r(region2)
    uni = (r1 | r2).sum()
    return float((r1 ^ r2).sum() / uni) if uni else 0.0


# ── 空間関係 ─────────────────────────────────────────────────────────────────── #
def _bbox(region):
    r = _r(region)
    if not r.any():
        return None
    rs, cs = np.where(r)
    return rs.min(), cs.min(), rs.max(), cs.max()


def find_neighbors(regions, max_distance=1):
    """領域リストの隣接ペア index を返す(膨張して交差判定)(find_neighbors)。"""
    from scipy.ndimage import binary_dilation
    masks = [_r(x) for x in regions]
    dil = [binary_dilation(m, iterations=int(max_distance)) for m in masks]
    out = []
    for i in range(len(masks)):
        for j in range(i + 1, len(masks)):
            if (dil[i] & masks[j]).any():
                out.append((i, j))
    return out


def spatial_relation(region1, region2):
    """2 領域の重心方向に基づく空間関係(above/below/left/right)(spatial_relation)。"""
    b1 = _bbox(region1); b2 = _bbox(region2)
    if b1 is None or b2 is None:
        return None
    r1 = _r(region1); r2 = _r(region2)
    c1r = np.mean(np.where(r1)[0]); c1c = np.mean(np.where(r1)[1])
    c2r = np.mean(np.where(r2)[0]); c2c = np.mean(np.where(r2)[1])
    rels = []
    if c1r < c2r: rels.append("above")
    elif c1r > c2r: rels.append("below")
    if c1c < c2c: rels.append("left")
    elif c1c > c2c: rels.append("right")
    return {"relations": rels, "angle": float(np.arctan2(c2r - c1r, c2c - c1c))}


def select_region_spatial(regions, ref_region, relation="above"):
    """基準領域に対し指定空間関係を満たす領域を選ぶ(select_region_spatial)。"""
    out = []
    for reg in regions:
        sr = spatial_relation(ref_region, reg)
        if sr and relation in sr["relations"]:
            out.append(reg)
    return out


# ── 生成 ─────────────────────────────────────────────────────────────────────── #
def gen_rectangle1(shape, row1, col1, row2, col2):
    """軸並行矩形領域を生成(gen_rectangle1)。"""
    m = np.zeros(shape, bool)
    m[int(row1):int(row2) + 1, int(col1):int(col2) + 1] = True
    return m


def gen_region_hline(shape, rows):
    """水平線分の領域を生成(gen_region_hline)。rows: 行 index の列。"""
    m = np.zeros(shape, bool)
    for r in np.atleast_1d(rows):
        m[int(r), :] = True
    return m


def gen_region_histo(hist, shape=None, scale=1.0):
    """1D ヒストグラムを棒グラフ領域として描く(gen_region_histo)。"""
    h = np.asarray(hist, float)
    N = len(h); H = int(h.max() * scale) + 1 if shape is None else shape[0]
    m = np.zeros((H, N), bool)
    for c, val in enumerate(h):
        bar = int(np.clip(val * scale, 0, H))
        m[H - bar:H, c] = True
    return m


# ── アクセス ─────────────────────────────────────────────────────────────────── #
def get_region_points(region):
    """領域画素の (row, col) 座標配列(get_region_points)。"""
    rs, cs = np.where(_r(region))
    return np.column_stack([rs, cs])


def get_region_runs(region):
    """領域のランレングス表現 [(row, col_start, col_end), ...](get_region_runs)。"""
    r = _r(region); runs = []
    for row in range(r.shape[0]):
        cols = np.where(r[row])[0]
        if cols.size == 0:
            continue
        breaks = np.where(np.diff(cols) > 1)[0]
        start = 0
        for b in list(breaks) + [len(cols) - 1]:
            runs.append((row, int(cols[start]), int(cols[b])))
            start = b + 1
    return runs


def get_region_polygon(region, tolerance=1.5):
    """領域外形の多角形近似頂点を返す(get_region_polygon)。"""
    from scipy.ndimage import binary_erosion
    r = _r(region)
    border = r & ~binary_erosion(r)
    rs, cs = np.where(border)
    if rs.size == 0:
        return np.zeros((0, 2))
    pts = np.column_stack([rs, cs]).astype(float)
    c = pts.mean(0)
    ang = np.arctan2(pts[:, 0] - c[0], pts[:, 1] - c[1])
    return pts[np.argsort(ang)]
