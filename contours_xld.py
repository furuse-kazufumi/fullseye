"""XLD 輪郭の生成・解析・集合演算(HALCON "Contours"/"XLD" chapter genuine, numpy).

contour = dict {shape:(H,W), cs:[Nx2 (row,col) float 配列, ...]}。
輪郭の解析幾何(接線角・多角形近似・モーメント・点内外判定)と、
閉輪郭のブール演算(ラスタライズ経由)を本物で実装。
"""
from __future__ import annotations

import numpy as np


def _contour(shape, arrays):
    return {"shape": tuple(shape), "cs": [np.asarray(a, float).reshape(-1, 2) for a in arrays]}


# ── 生成 ─────────────────────────────────────────────────────────────────────── #
def gen_circle_contour_xld(row, col, radius, n=100, start=0.0, end=2 * np.pi, shape=(256, 256)):
    """円弧輪郭を生成(gen_circle_contour_xld)。"""
    t = np.linspace(start, end, int(n))
    arr = np.column_stack([row + radius * np.sin(t), col + radius * np.cos(t)])
    return _contour(shape, [arr])


def gen_ellipse_contour_xld(row, col, phi, ra, rb, n=100, start=0.0, end=2 * np.pi, shape=(256, 256)):
    """楕円弧輪郭を生成(gen_ellipse_contour_xld)。"""
    t = np.linspace(start, end, int(n))
    x = ra * np.cos(t); y = rb * np.sin(t)
    c = col + x * np.cos(phi) - y * np.sin(phi)
    r = row + x * np.sin(phi) + y * np.cos(phi)
    return _contour(shape, [np.column_stack([r, c])])


def gen_rectangle2_contour_xld(row, col, phi, length1, length2, shape=(256, 256)):
    """回転矩形の輪郭を生成(gen_rectangle2_contour_xld)。"""
    l1, l2 = length1, length2
    corners = np.array([[-l1, -l2], [l1, -l2], [l1, l2], [-l1, l2], [-l1, -l2]], float)
    ca, sa = np.cos(phi), np.sin(phi)
    R = np.array([[ca, -sa], [sa, ca]])
    pc = corners @ R.T
    return _contour(shape, [np.column_stack([row + pc[:, 1], col + pc[:, 0]])])


def gen_contour_polygon_xld(points, shape=(256, 256)):
    """点列から多角形輪郭を生成(gen_contour_polygon_xld)。"""
    return _contour(shape, [np.asarray(points, float).reshape(-1, 2)])


def gen_cross_contour_xld(row, col, size=5.0, angle=0.0, shape=(256, 256)):
    """十字マーカー輪郭を生成(gen_cross_contour_xld)。"""
    ca, sa = np.cos(angle), np.sin(angle)
    h = [np.array([[row - size * sa, col - size * ca], [row + size * sa, col + size * ca]])]
    v = np.array([[row - size * ca, col + size * sa], [row + size * ca, col - size * sa]])
    return _contour(shape, h + [v])


def gen_contour_polygon_rounded_xld(points, radius=2.0, n=8, shape=(256, 256)):
    """角を丸めた多角形輪郭を生成(gen_contour_polygon_rounded_xld)。"""
    p = np.asarray(points, float).reshape(-1, 2)
    out = []
    m = len(p)
    for i in range(m):
        prev = p[(i - 1) % m]; cur = p[i]; nxt = p[(i + 1) % m]
        v1 = prev - cur; v2 = nxt - cur
        v1 = v1 / (np.linalg.norm(v1) + 1e-12); v2 = v2 / (np.linalg.norm(v2) + 1e-12)
        a = cur + v1 * radius; b = cur + v2 * radius
        for t in np.linspace(0, 1, int(n)):
            out.append((1 - t) * a + t * b)
    out.append(out[0])
    return _contour(shape, [np.asarray(out)])


# ── 解析 ─────────────────────────────────────────────────────────────────────── #
def get_contour_angle_xld(contour, k=2):
    """輪郭に沿った接線角(ラジアン)を各点で返す(get_contour_angle_xld)。"""
    out = []
    for a in contour["cs"]:
        d = np.gradient(a, axis=0)
        out.append(np.arctan2(d[:, 0], d[:, 1]))
    return out


def _cross2d(a, b):
    """2D ベクトルの外積(z 成分のスカラー)。numpy>=2.0 で ``np.cross`` の 2 次元
    入力対応が削除される見込みのため、明示式で代替(数式は等価: a×b の z 成分)。"""
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def get_polygon_xld(contour, tolerance=2.0):
    """Douglas-Peucker で輪郭を多角形近似(get_polygon_xld)。頂点列を返す。"""
    def dp(pts, eps):
        if len(pts) < 3:
            return pts
        start, end = pts[0], pts[-1]
        line = end - start; L = np.linalg.norm(line) + 1e-12
        d = np.abs(_cross2d(line, pts - start)) / L
        idx = int(d.argmax())
        if d[idx] > eps:
            left = dp(pts[:idx + 1], eps); right = dp(pts[idx:], eps)
            return np.vstack([left[:-1], right])
        return np.vstack([start, end])

    out = []
    for a in contour["cs"]:
        closed = len(a) > 2 and np.allclose(a[0], a[-1])
        if closed:
            # 閉輪郭は始点から最遠の点で 2 分割してから DP(退化回避)
            far = int(np.hypot(a[:, 0] - a[0, 0], a[:, 1] - a[0, 1]).argmax())
            p1 = dp(a[:far + 1], tolerance); p2 = dp(a[far:], tolerance)
            out.append(np.vstack([p1[:-1], p2]))
        else:
            out.append(dp(a, tolerance))
    return out


def moments_any_points_xld(contour):
    """輪郭点集合の面積・重心・2 次モーメント(moments_any_points_xld)。"""
    pts = np.vstack(contour["cs"])
    c = pts.mean(0)
    d = pts - c
    return {"centroid": c, "m20": float((d[:, 1] ** 2).mean()),
            "m02": float((d[:, 0] ** 2).mean()), "m11": float((d[:, 0] * d[:, 1]).mean()),
            "n": len(pts)}


def get_regress_params_xld(contour):
    """輪郭点への回帰直線パラメータ(法線角 nr,nc と原点距離 dist)(get_regress_params_xld)。"""
    out = []
    for a in contour["cs"]:
        c = a.mean(0); d = a - c
        _, V = np.linalg.eigh(np.cov(d.T))
        direction = V[:, 1]                                 # 最大分散方向
        normal = np.array([-direction[1], direction[0]])
        out.append({"nr": float(normal[0]), "nc": float(normal[1]),
                    "dist": float(normal @ c), "row": float(c[0]), "col": float(c[1])})
    return out


def test_xld_point(contour, row, col):
    """点が閉輪郭の内部にあるか(交差数法)(test_xld_point)。"""
    res = []
    for a in contour["cs"]:
        n = len(a); inside = False; j = n - 1
        for i in range(n):
            ri, ci = a[i]; rj, cj = a[j]
            if ((ci > col) != (cj > col)) and \
               (row < (rj - ri) * (col - ci) / (cj - ci + 1e-12) + ri):
                inside = not inside
            j = i
        res.append(inside)
    return res


def local_max_contours_xld(contour, image):
    """輪郭上でグレー値が局所最大となる点を抽出(local_max_contours_xld)。"""
    im = np.asarray(image, float); out = []
    for a in contour["cs"]:
        rr = np.clip(a[:, 0].round().astype(int), 0, im.shape[0] - 1)
        cc = np.clip(a[:, 1].round().astype(int), 0, im.shape[1] - 1)
        g = im[rr, cc]
        loc = np.nonzero((g[1:-1] > g[:-2]) & (g[1:-1] > g[2:]))[0] + 1
        out.append(a[loc])
    return out


# ── 閉輪郭ブール演算(ラスタライズ経由)──────────────────────────────────────── #
def _rasterize(arr, shape):
    from matplotlib.path import Path
    H, W = shape
    rr, cc = np.mgrid[0:H, 0:W]
    pts = np.column_stack([rr.ravel(), cc.ravel()])
    return Path(arr).contains_points(pts).reshape(H, W)


def _mask_to_contour(mask, shape):
    from scipy.ndimage import binary_erosion
    border = mask & ~binary_erosion(mask)
    rs, cs = np.where(border)
    if rs.size == 0:
        return _contour(shape, [])
    pts = np.column_stack([rs, cs]).astype(float)
    c = pts.mean(0); ang = np.arctan2(pts[:, 0] - c[0], pts[:, 1] - c[1])
    pts = pts[np.argsort(ang)]
    return _contour(shape, [np.vstack([pts, pts[:1]])])


def _binop_closed(c1, c2, op):
    shape = c1.get("shape", (256, 256))
    m1 = np.zeros(shape, bool)
    for a in c1["cs"]:
        m1 |= _rasterize(a, shape)
    m2 = np.zeros(shape, bool)
    for a in c2["cs"]:
        m2 |= _rasterize(a, shape)
    res = op(m1, m2)
    return _mask_to_contour(res, shape)


def union2_closed_contours_xld(contour1, contour2):
    """2 閉輪郭の和(union2_closed_contours_xld)。"""
    return _binop_closed(contour1, contour2, lambda a, b: a | b)


def intersection_closed_contours_xld(contour1, contour2):
    """2 閉輪郭の積(intersection_closed_contours_xld)。"""
    return _binop_closed(contour1, contour2, lambda a, b: a & b)


def difference_closed_contours_xld(contour1, contour2):
    """2 閉輪郭の差(difference_closed_contours_xld)。"""
    return _binop_closed(contour1, contour2, lambda a, b: a & ~b)


def symm_difference_closed_contours_xld(contour1, contour2):
    """2 閉輪郭の対称差(symm_difference_closed_contours_xld)。"""
    return _binop_closed(contour1, contour2, lambda a, b: a ^ b)
