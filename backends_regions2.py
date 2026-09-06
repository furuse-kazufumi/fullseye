"""Binary-region geometry operators (registry tier, prefix ``r2_``).

Genuine computational-geometry / connected-component operators over binary region
masks, each implementing the algorithm named by a real, previously-uncovered HALCON
operator.  Every op is a module-level ``fn(v, a, b)`` so tests call it directly; the
tier is assembled by :func:`build`, which the caller wires into the op registry.

Region contract: input/return is a 2-D float64 mask (0/1) in [0,1]; feature ops
return a finite scalar float.  All fns are exception-safe (fail-soft on empty / const
/ tiny / malformed input — never raise) and deterministic (any rng is seeded).

Genuine algorithms
------------------
* ``inner_circle``        - largest inscribed circle via the Euclidean distance
                            transform (center = arg-max distance-to-background,
                            radius = that distance), rasterised as a disk mask.
* ``inner_rectangle1``    - largest axis-aligned all-foreground rectangle via the
                            maximal-rectangle-in-a-binary-matrix stack algorithm.
* ``smallest_rectangle1`` - axis-aligned bounding box of the region.
* ``smallest_circle``     - minimum enclosing circle (Welzl on the convex hull).
* ``smallest_rectangle2`` - minimum-area oriented bounding rectangle (rotating
                            calipers over the convex hull).
* ``sort_region``         - keep the k-th largest connected component (k from ``a``).
* ``union1``              - union of all connected components into one mask.
* ``partition_rectangle`` - split the region bbox into a grid; keep overlapping cells.
* ``runlength_features``  - mean horizontal run length (region -> feature).
* ``split_skeleton_lines``- thin to a skeleton, then break it at junction pixels.

``contlength`` (boundary length) is intentionally NOT implemented here: it is already
covered elsewhere in the registry (``backends_auto``).  See :data:`SKIPPED`.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

try:  # skimage is used only to thin regions for split_skeleton_lines; degrade gracefully
    from skimage.morphology import skeletonize as _sk_skeletonize
except ImportError:  # pragma: no cover - environment without skimage
    _sk_skeletonize = None

# HALCON operators deliberately skipped in this tier (with the honest reason).
SKIPPED = {
    "contlength": "boundary length already covered in backends_auto (region_feat perimeter)",
}


# --------------------------------------------------------------------------- #
# small shared helpers
# --------------------------------------------------------------------------- #
def _as_mask(v) -> np.ndarray:
    """Coerce any region-ish input to a 2-D boolean foreground mask (fail-soft)."""
    a = np.asarray(v, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    elif a.ndim > 2:
        a = a.reshape(a.shape[0], -1)
    return np.isfinite(a) & (a > 0.5)


def _clip01(a: np.ndarray) -> np.ndarray:
    return np.clip(np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)


def _knob(x: float) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not np.isfinite(x):
        return 0.5
    return min(1.0, max(0.0, x))


def _disk(shape, cy: float, cx: float, r: float) -> np.ndarray:
    h, w = shape
    yy, xx = np.ogrid[:h, :w]
    r = max(0.0, float(r))
    return ((yy - cy) ** 2 + (xx - cx) ** 2) <= (r * r)


def _convex_hull_xy(pts_xy: np.ndarray) -> np.ndarray:
    """Andrew's monotone chain. ``pts_xy`` = Nx2 (x, y); returns CCW hull vertices.

    The turn test uses the robust :func:`predicates.orient2d` rather than a raw
    float cross product: near-collinear points make a float determinant pick the
    wrong side ~19% of the time (see predicates.py), which would keep a reflex
    vertex or drop a real one and yield a non-convex "hull".
    """
    import predicates                                     # noqa: PLC0415
    pts = np.unique(pts_xy.astype(np.float64), axis=0)
    if len(pts) <= 2:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def _cross(o, a, b):                                  # >0 left turn, <0 right, 0 collinear
        return predicates.orient2d(o, a, b)

    lower = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in pts[::-1]:
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = np.array(lower[:-1] + upper[:-1], dtype=np.float64)
    return hull if len(hull) >= 1 else pts


# --- minimum enclosing circle (Welzl) --------------------------------------- #
def _circle_2(p, q):
    cx, cy = (p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0
    r = 0.5 * float(np.hypot(p[0] - q[0], p[1] - q[1]))
    return (cx, cy, r)


def _circle_3(p, q, s):
    ax, ay = p
    bx, by = q
    cx_, cy_ = s
    d = 2.0 * (ax * (by - cy_) + bx * (cy_ - ay) + cx_ * (ay - by))
    if abs(d) < 1e-12:  # collinear -> degenerate; caller falls back
        return None
    ux = ((ax * ax + ay * ay) * (by - cy_) + (bx * bx + by * by) * (cy_ - ay)
          + (cx_ * cx_ + cy_ * cy_) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx_ - bx) + (bx * bx + by * by) * (ax - cx_)
          + (cx_ * cx_ + cy_ * cy_) * (bx - ax)) / d
    r = float(np.hypot(ux - ax, uy - ay))
    return (ux, uy, r)


def _in_circle(c, p, eps=1e-7):
    return np.hypot(p[0] - c[0], p[1] - c[1]) <= c[2] + eps


def _trivial(pts):
    if not pts:
        return (0.0, 0.0, 0.0)
    if len(pts) == 1:
        return (pts[0][0], pts[0][1], 0.0)
    if len(pts) == 2:
        return _circle_2(pts[0], pts[1])
    c = _circle_3(pts[0], pts[1], pts[2])
    if c is not None:
        return c
    # collinear triple: enclosing circle = diameter of the farthest pair
    best = _circle_2(pts[0], pts[1])
    for i in range(3):
        for j in range(i + 1, 3):
            cc = _circle_2(pts[i], pts[j])
            if cc[2] > best[2]:
                best = cc
    return best


def _welzl(P, R):
    if not P or len(R) == 3:
        return _trivial(R)
    p = P[-1]
    d = _welzl(P[:-1], R)
    if _in_circle(d, p):
        return d
    return _welzl(P[:-1], R + [p])


def _min_enclosing_circle(points_yx: np.ndarray):
    """Minimum enclosing circle of (row, col) points. Returns (cy, cx, r)."""
    pts = np.asarray(points_yx, dtype=np.float64)
    if len(pts) == 0:
        return (0.0, 0.0, 0.0)
    xy = np.column_stack([pts[:, 1], pts[:, 0]])          # (x, y)
    hull = _convex_hull_xy(xy)
    if len(hull) == 1:
        return (float(hull[0][1]), float(hull[0][0]), 0.0)
    P = [tuple(p) for p in hull]
    rng = np.random.default_rng(0)
    rng.shuffle(P)                                        # deterministic shuffle
    cx, cy, r = _welzl(P, [])
    return (float(cy), float(cx), float(r))               # back to (row, col, r)


# --- minimum-area oriented rectangle (rotating calipers) -------------------- #
def _min_area_rect(points_yx: np.ndarray):
    """Min-area oriented bbox of (row,col) points.

    Returns (cy, cx, long_len, short_len, angle) where ``angle`` (radians) is the
    orientation of the LONG side in image (x=col, y=row) coordinates.
    """
    pts = np.asarray(points_yx, dtype=np.float64)
    if len(pts) == 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    xy = np.column_stack([pts[:, 1], pts[:, 0]])          # (x, y)
    hull = _convex_hull_xy(xy)
    if len(hull) <= 1:
        return (float(pts[0, 0]), float(pts[0, 1]), 0.0, 0.0, 0.0)
    if len(hull) == 2:
        d = hull[1] - hull[0]
        c = hull.mean(0)
        return (float(c[1]), float(c[0]), float(np.hypot(*d)), 0.0,
                float(np.arctan2(d[1], d[0])))

    best = None
    n = len(hull)
    for i in range(n):
        edge = hull[(i + 1) % n] - hull[i]
        L = float(np.hypot(edge[0], edge[1]))
        if L < 1e-12:
            continue
        ux, uy = edge[0] / L, edge[1] / L                 # edge dir
        vx, vy = -uy, ux                                  # perpendicular
        pu = hull[:, 0] * ux + hull[:, 1] * uy
        pv = hull[:, 0] * vx + hull[:, 1] * vy
        umin, umax = pu.min(), pu.max()
        vmin, vmax = pv.min(), pv.max()
        area = (umax - umin) * (vmax - vmin)
        if best is None or area < best[0]:
            cu, cv = (umin + umax) / 2.0, (vmin + vmax) / 2.0
            cx = cu * ux + cv * vx
            cy = cu * uy + cv * vy
            best = (area, cx, cy, umax - umin, vmax - vmin,
                    float(np.arctan2(uy, ux)))
    if best is None:                                      # fully degenerate
        c = hull.mean(0)
        return (float(c[1]), float(c[0]), 0.0, 0.0, 0.0)
    _, cx, cy, ext_u, ext_v, ang_u = best
    if ext_u >= ext_v:
        long_len, short_len, angle = ext_u, ext_v, ang_u
    else:
        long_len, short_len, angle = ext_v, ext_u, ang_u + np.pi / 2.0
    return (float(cy), float(cx), float(long_len), float(short_len), float(angle))


def _oriented_rect_mask(shape, cy, cx, long_len, short_len, angle):
    h, w = shape
    yy, xx = np.ogrid[:h, :w]
    ux, uy = np.cos(angle), np.sin(angle)                 # long axis (x, y)
    dx = xx - cx
    dy = yy - cy
    pu = dx * ux + dy * uy
    pv = -dx * uy + dy * ux
    hu = long_len / 2.0 + 0.5
    hv = short_len / 2.0 + 0.5
    return (np.abs(pu) <= hu) & (np.abs(pv) <= hv)


def _max_all_ones_rect(m: np.ndarray):
    """Largest axis-aligned all-True rectangle. Returns (top, left, bottom, right)."""
    h, w = m.shape
    if not m.any():
        return None
    height = np.zeros(w, dtype=np.int64)
    best = None                                           # (area, top, left, bottom, right)
    for r in range(h):
        height = np.where(m[r], height + 1, 0)
        stack = []                                        # (start_col, bar_height)
        for i in range(w + 1):
            cur = int(height[i]) if i < w else 0
            start = i
            while stack and stack[-1][1] > cur:
                idx, hgt = stack.pop()
                area = hgt * (i - idx)
                if hgt > 0 and (best is None or area > best[0]):
                    best = (area, r - hgt + 1, idx, r, i - 1)
                start = idx
            stack.append((start, cur))
    if best is None:
        return None
    return (best[1], best[2], best[3], best[4])


# --------------------------------------------------------------------------- #
# operators
# --------------------------------------------------------------------------- #
def r2_inner_circle(v, a, b):
    """Largest inscribed circle drawn as a mask (a scales drawn radius; a=0.5=exact).

    領域の最大内接円をマスクとして描く。入力を ``> 0.5`` で前景マスクに直し、
    ``scipy.ndimage.distance_transform_edt`` で各前景画素から最近傍の背景画素
    までの距離を取り、その最大値 ``r0`` を与える画素を中心 ``(cy, cx)`` とする
    (最大値が複数あれば行優先で最初の画素)。描く半径は
    ``r = r0 * (0.6 + 0.8*a)`` で、``a=0`` で 0.6 倍、``a=0.5`` で ``r0`` そのまま、
    ``a=1`` で 1.4 倍(``a`` は [0,1] に clip、非有限なら 0.5)。``b`` は未使用。

    返り値は入力と同形の float64 0/1 マスク(円板 ``(y-cy)^2+(x-cx)^2 <= r^2``)。
    前景が無ければ全零。座標は (row, col)。

    注意: ``r0`` は「背景画素の中心までの距離」なので、``a=0.5`` でも描いた円板は
    領域の縁を 1 画素程度はみ出すことがある(10x20 の矩形で 2 画素、半径 7 の
    円板で 12 画素の外側画素を実測)。厳密に内側へ収めたいなら ``a`` を少し
    下げる。領域が複数の連結成分からなる場合も内接円は 1 つだけ(最も太い成分の
    もの)。3 次元配列 (H,W,C) は (H, W*C) に平坦化されるのでカラー画像は渡さない。
    前段に ``threshold`` や ``select_largest``、対になる外接円は
    ``r2_smallest_circle``(両者の半径比が真円度の粗い指標になる)。
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    dt = ndimage.distance_transform_edt(m)
    cy, cx = np.unravel_index(int(np.argmax(dt)), dt.shape)
    r0 = float(dt[cy, cx])                                # genuine inradius
    r = r0 * (0.6 + 0.8 * _knob(a))                       # a in [0,1] -> [0.6,1.4]*inradius
    out[_disk(m.shape, cy, cx, r)] = 1.0
    return _clip01(out)


def r2_inner_rectangle1(v, a, b):
    """Largest axis-aligned inscribed rectangle (a shrinks the drawn rect; a=0=exact).

    領域に内接する軸並行矩形のうち面積最大のものをマスクとして描く。前景マスク
    (``> 0.5``)に対し、行ごとに各列の連続前景高さを積み、単調スタックで最大
    長方形を求めるヒストグラム法(O(H*W))で厳密解を得る。同面積の候補が複数
    あるときは走査順で最初に見つかったものを採る。

    ``a`` は描く矩形を内側へ縮める割合で、``f = 0.3*a`` として高さを
    ``round(hh*f/2)`` 行ずつ、幅を ``round(ww*f/2)`` 列ずつ両側から削る。``a=0`` で
    厳密な最大内接矩形、``a=1`` で各辺が約 15% ずつ縮む(面積ではおよそ半分)。
    縮めすぎて辺が潰れる場合は中央の 1 行 / 1 列に丸める。``b`` は未使用。

    返り値は入力と同形の float64 0/1 マスク。前景が無ければ全零。矩形は画素境界に
    そろうため ``a=0`` の出力は必ず領域に含まれる(``r2_inner_circle`` と異なり
    はみ出さない)。孔のある領域では孔を避けた矩形になるので、孔を無視したい
    ときは前段に ``fill_up``。回転した矩形は扱えない(軸並行のみ)。外接側の
    軸並行矩形は ``r2_smallest_rectangle1``。
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    rect = _max_all_ones_rect(m)
    if rect is None:
        return out
    top, left, bottom, right = rect
    hh = bottom - top + 1
    ww = right - left + 1
    f = 0.3 * _knob(a)                                    # inward shrink fraction per side
    dt = int(round(hh * f / 2.0))
    dl = int(round(ww * f / 2.0))
    t2, b2 = top + dt, bottom - dt
    l2, r2 = left + dl, right - dl
    if b2 < t2:
        t2 = b2 = (top + bottom) // 2
    if r2 < l2:
        l2 = r2 = (left + right) // 2
    out[t2:b2 + 1, l2:r2 + 1] = 1.0
    return _clip01(out)


def r2_smallest_rectangle1(v, a, b):
    """Axis-aligned bounding box (smallest_rectangle1).

    領域の外接軸並行矩形(bounding box)をマスクとして描く。前景マスク(``> 0.5``)
    の前景画素について行・列の最小/最大 ``ys.min()..ys.max()``、
    ``xs.min()..xs.max()`` を取り、その範囲を 1.0 で塗る。``a``, ``b`` は未使用。

    返り値は入力と同形の float64 0/1 マスク。前景が無ければ全零。出力は必ず入力
    領域を含む。複数の連結成分があれば全成分をまとめて囲む 1 つの矩形になる
    (成分ごとの bbox が欲しければ先に ``r2_sort_region`` や ``select_largest`` で
    1 成分に絞る)。矩形の 4 隅の座標そのものは返さない(マスク表現)。孤立ノイズが
    1 画素あるだけで矩形が大きく広がるので、前段で ``remove_small`` や
    ``opening_circle`` を掛けておく。回転を許した最小面積矩形は
    ``r2_smallest_rectangle2``、内接側は ``r2_inner_rectangle1``。
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    ys, xs = np.where(m)
    if ys.size == 0:
        return out
    out[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = 1.0
    return _clip01(out)


def r2_smallest_circle(v, a, b):
    """Minimum enclosing circle as a mask (Welzl); a inflates radius (>=0).

    領域の全前景画素(画素中心)を含む最小包含円をマスクとして描く。前景座標を
    凸包(Andrew の単調鎖、向き判定は ``predicates.orient2d`` の頑健版)に減らして
    から Welzl の再帰アルゴリズムで厳密な最小円 ``(cy, cx, r)`` を求める。凸包
    頂点の順序は ``numpy.random.default_rng(0)`` で固定シャッフルするので結果は
    決定的。

    描く半径は ``r_draw = (r + 0.75) * (1 + 0.4*a)``。``a=0`` でも 0.75 画素
    余分に膨らませる(画素中心ベースの ``r`` では縁の画素が欠けるため、全前景
    画素を確実に含める設計)。``a=1`` で 1.4 倍。``a`` は [0,1] に clip。``b`` は
    未使用。返り値は入力と同形の float64 0/1 マスク、前景が無ければ全零。

    注意: 出力は常に入力領域を含み、``a`` を上げても縮む方向には動かない。複数の
    連結成分があれば全体を囲む 1 つの円。前景が 1 画素なら ``r=0`` で半径 0.75
    の円板(1 画素)になる。Welzl の再帰は凸包頂点数ぶん深くなる。円の中心や
    半径の数値は返さない。内接円 ``r2_inner_circle`` との半径比が真円度の粗い
    指標になり、向きを持つ外接形は ``r2_smallest_rectangle2``。
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    ys, xs = np.where(m)
    if ys.size == 0:
        return out
    cy, cx, r = _min_enclosing_circle(np.column_stack([ys, xs]))
    r_draw = (r + 0.75) * (1.0 + 0.4 * _knob(a))          # >= r so all pixels enclosed
    out[_disk(m.shape, cy, cx, r_draw)] = 1.0
    return _clip01(out)


def r2_smallest_rectangle2(v, a, b):
    """Minimum-area ORIENTED bounding rectangle as a mask (rotating calipers).

    領域の全前景画素を含む最小面積の回転矩形をマスクとして描く。前景座標の凸包を
    取り、凸包の各辺に平行な向きで外接矩形を作って面積最小のものを選ぶ
    (rotating calipers。最小面積矩形は凸包のいずれかの辺に接するという性質を使う)。
    内部表現は中心 ``(cy, cx)``、長辺 ``long_len``、短辺 ``short_len``、長辺の向き
    ``angle``(画像座標 x=col, y=row で測ったラジアン)。

    ``a`` は長辺だけを ``1 + 0.3*a`` 倍に伸ばす(``a=0`` で最小矩形そのもの、
    ``a=1`` で長辺 1.3 倍。短辺は変えない)。``b`` は未使用。描画は中心からの
    射影 ``|pu| <= long/2 + 0.5``、``|pv| <= short/2 + 0.5`` で、画素の広がりぶん
    0.5 画素の余白を足すため出力は入力領域を必ず含む。

    返り値は入力と同形の float64 0/1 マスク、前景が無ければ全零。角度や辺長の
    数値は返さない。複数の連結成分があれば全体で 1 つの矩形。前景が 1 画素や
    一直線上の場合は退化(点・線分)し、描画は 1 画素幅程度の細い帯になる。
    軸並行でよければ ``r2_smallest_rectangle1`` の方が軽い。細長い部品の向きを
    見る前処理や、``r2_inner_rectangle1`` との面積比で矩形らしさを見る用途に。
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    ys, xs = np.where(m)
    if ys.size == 0:
        return out
    cy, cx, ll, ss, ang = _min_area_rect(np.column_stack([ys, xs]))
    ll = ll * (1.0 + 0.3 * _knob(a))                      # a mildly inflates the long side
    out[_oriented_rect_mask(m.shape, cy, cx, ll, ss, ang)] = 1.0
    return _clip01(out)


def r2_sort_region(v, a, b):
    """Keep the k-th largest connected component; k = round(a*(n-1)).

    前景マスク(``> 0.5``)を ``scipy.ndimage.label``(既定の 4 連結)で連結成分に
    分け、面積(画素数)の降順に並べて ``k`` 番目の成分だけを残す。``k`` は
    ``round(a*(n-1))`` を ``[0, n-1]`` に clip した整数で、``a=0`` で最大成分、
    ``a=1`` で最小成分、``a=0.5`` でおおよそ中央の順位の成分。``n`` は成分数。
    ``b`` は未使用。

    返り値は入力と同形の float64 0/1 マスク。成分が無ければ全零。同面積の成分が
    複数あるときの順位は保証されない(``numpy.argsort`` の順序に依存)。成分数
    ``n`` が変わると同じ ``a`` でも選ばれる順位が変わる(相対指定)ので、
    「最大成分」を確実に取りたいだけなら ``a=0`` か ``select_largest`` を使う。
    斜め接続だけでつながった画素は別成分として数えられる(4 連結)。前段に
    ``opening_circle`` でくびれを切っておくと成分単位の選択が安定する。
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    lab, n = ndimage.label(m)
    if n == 0:
        return out
    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    order = np.argsort(sizes)[::-1]                       # descending by area
    k = int(round(_knob(a) * (n - 1)))
    k = min(n - 1, max(0, k))
    out[lab == (int(order[k]) + 1)] = 1.0
    return _clip01(out)


def r2_union1(v, a, b):
    """Union of all connected components into a single mask (OR of labels).

    前景マスク(``> 0.5``)を ``scipy.ndimage.label`` で連結成分にラベル付けし、
    ``label > 0`` を 1.0 に戻して 1 枚のマスクとして返す。全成分の和集合なので、
    結果は「入力を 0/1 に正規化したもの」と同じになる(値の 2 値化と非有限値の
    除去が実際の効果)。``a``, ``b`` は未使用。

    返り値は入力と同形の float64 0/1 マスク。前景が無ければ全零。0.5 以下の
    グレー値や NaN/Inf はすべて背景になる。複数のラベル値を持つラベル画像を
    受けた場合もラベル番号の区別は消え、単一の前景マスクになる(ラベルごとに
    取り出したいなら ``r3_label_to_region``)。パイプライン上は「領域を 1 個の
    オブジェクトとして扱う」ことを明示する位置づけで、成分単位の選別
    (``select_shape`` / ``r2_sort_region``)はこの op より前に置く。
    """
    m = _as_mask(v)
    lab, _ = ndimage.label(m)
    return _clip01((lab > 0).astype(np.float64))


def r2_partition_rectangle(v, a, b):
    """Split the region bbox into an NxN grid; keep cells overlapping the region.

    領域の外接軸並行矩形を ``N x N`` の格子に等分し、領域と 1 画素でも重なる
    セルを丸ごと 1.0 で塗ったマスクを返す。``N = 2 + int(a*4)`` で ``a=0`` → 2、
    ``a=1`` → 6 分割(``a`` は [0,1] に clip)。セル境界は
    ``numpy.linspace(top, bottom+1, N+1)`` を整数化したもので、bbox がセル数より
    小さいと幅 0 のセルが生じ、そのセルはスキップされる。``b`` は未使用。

    返り値は入力と同形の float64 0/1 マスク。前景が無ければ全零。出力は「領域を
    覆うセルの和」なので入力領域を必ず含み、bbox の外は塗られない。中身が凸で
    bbox いっぱいに詰まった領域では全セルが該当し、``a`` を変えても出力は bbox
    そのものになる。孔や凹みが大きい領域で初めて格子の粗さが見える。用途は
    粗いタイル分割(局所処理の窓決め)や占有パターンの粗視化。隣接セルは
    つながって 1 つの塊になるため、セル単位で分けて扱う用途には向かない。
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    ys, xs = np.where(m)
    if ys.size == 0:
        return out
    top, bottom = int(ys.min()), int(ys.max())
    left, right = int(xs.min()), int(xs.max())
    ncell = 2 + int(_knob(a) * 4)                          # a in [0,1] -> 2..6 divisions
    rb = np.linspace(top, bottom + 1, ncell + 1).astype(int)
    cb = np.linspace(left, right + 1, ncell + 1).astype(int)
    for i in range(ncell):
        for j in range(ncell):
            r0, r1 = rb[i], rb[i + 1]
            c0, c1 = cb[j], cb[j + 1]
            if r1 <= r0 or c1 <= c0:
                continue
            if m[r0:r1, c0:c1].any():
                out[r0:r1, c0:c1] = 1.0
    return _clip01(out)


def r2_runlength_features(v, a, b):
    """Region -> feature: mean length of horizontal foreground runs.

    前景マスク(``> 0.5``)の各行を左から走査し、連続する前景画素の並び(水平ラン)の
    長さをすべて集めて、その平均(画素数)を 1 つのスカラーで返す。行ごとにゼロ
    埋めした行の差分でランの開始/終了を検出する。``a``, ``b`` は未使用。

    返り値は ``numpy.float64``。前景が無ければ 0.0。単位は画素で、画像サイズで
    正規化しない(同じ形状でも解像度が 2 倍なら値も 2 倍になる)。垂直方向のランは
    数えない(縦縞と横縞で値が大きく変わる、向きに依存する特徴量)。細い横線が
    多い領域では値が大きく、点状ノイズが多いと 1 に近づく。ラン長の分散や
    エントロピーは ``r3_runlength_distribution``、短いランの除去は
    ``r3_eliminate_runs``。特徴量なので後段に画像 op は繋げない。
    """
    m = _as_mask(v)
    if not m.any():
        return np.float64(0.0)
    lengths = []
    for row in m:
        if not row.any():
            continue
        # run boundaries via diff on a zero-padded row
        padded = np.concatenate(([0], row.view(np.int8), [0]))
        d = np.diff(padded)
        starts = np.where(d == 1)[0]
        ends = np.where(d == -1)[0]
        lengths.extend((ends - starts).tolist())
    if not lengths:
        return np.float64(0.0)
    return np.float64(float(np.mean(lengths)))


def r2_split_skeleton_lines(v, a, b):
    """Thin the region to a skeleton, then break it at junctions (>=3 neighbours).

    ``a`` drops resulting segments shorter than ``a*8`` pixels (a=0 keeps all).
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    skel = _sk_skeletonize(m) if _sk_skeletonize is not None else m
    skel = np.asarray(skel, dtype=bool)
    if not skel.any():
        return out
    # 8-neighbour foreground count (exclude self)
    kernel = np.ones((3, 3), dtype=np.int64)
    neigh = ndimage.convolve(skel.astype(np.int64), kernel, mode="constant") - skel
    junction = skel & (neigh >= 3)
    segments = skel & ~junction
    min_len = int(_knob(a) * 8)
    if min_len > 0:
        lab, n = ndimage.label(segments)                  # 4-connectivity
        if n > 0:
            sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
            keep = np.zeros_like(segments)
            for i, s in enumerate(sizes, 1):
                if s >= min_len:
                    keep |= (lab == i)
            segments = keep
    out[segments] = 1.0
    return _clip01(out)


_EM_SIMPLE_LUT = None


def _em_simple_lut():
    """(8,4) 単純点判定の 8 近傍 256 パターン LUT(総当たりで構築)。

    P が単純 ⇔ 近傍の前景セルが画素としての 8 隣接でちょうど 1 成分
    ∧ 近傍の背景セルの 4 連結成分のうち P に 4 隣接するものがちょうど 1 個。
    (Couprie ノートの EM93 転記を字義どおり「強連結成分のみ」で実装すると、
    斜め接続だけの近傍画素を数え落とし、並列削除が橋を落とすことを
    反例パターンで実測済み。標準の (8,4) 単純点なら同反例で削除が抑止される)
    """
    global _EM_SIMPLE_LUT
    if _EM_SIMPLE_LUT is not None:
        return _EM_SIMPLE_LUT
    pos = [(-1, 0), (-1, 1), (0, 1), (1, 1),
           (1, 0), (1, -1), (0, -1), (-1, -1)]      # 環順 N,NE,E,SE,S,SW,W,NW

    def n_components(cells, adj):
        comps, seen = 0, set()
        for c in cells:
            if c in seen:
                continue
            comps += 1
            stack = [c]
            while stack:
                u = stack.pop()
                if u in seen:
                    continue
                seen.add(u)
                stack.extend(v for v in cells if v not in seen and adj(u, v))
        return comps

    def adj8(u, v):
        return max(abs(u[0] - v[0]), abs(u[1] - v[1])) == 1

    def adj4(u, v):
        return abs(u[0] - v[0]) + abs(u[1] - v[1]) == 1

    lut = np.zeros(256, dtype=bool)
    for code in range(1, 256):
        fg = [pos[k] for k in range(8) if (code >> k) & 1]
        bg = [pos[k] for k in range(8) if not (code >> k) & 1]
        if n_components(fg, adj8) != 1:
            continue
        bg_touch = [c for c in bg if abs(c[0]) + abs(c[1]) == 1]
        if not bg_touch:
            continue
        comps, seen = 0, set()
        for c in bg:
            if c in seen:
                continue
            stack, comp = [c], set()
            while stack:
                u = stack.pop()
                if u in seen:
                    continue
                seen.add(u)
                comp.add(u)
                stack.extend(v for v in bg if v not in seen and adj4(u, v))
            if any(abs(x[0]) + abs(x[1]) == 1 for x in comp):
                comps += 1
        lut[code] = comps == 1
    _EM_SIMPLE_LUT = lut
    return lut


def em_skeleton(v, a, b):
    """Eckhardt–Maderlechner 型の不変細線化(HALCON `skeleton` と同系統)。

    出典: U. Eckhardt, G. Maderlechner, "Invariant Thinning",
    Int. J. Pattern Recognition and AI 7:1115-1144 (1993)。実装規則は
    M. Couprie "Note on fifteen 2D parallel thinning algorithms" の EM93
    定義に従うクリーンルーム実装。**同ノートが公表する EM93 の参照出力と
    突き合わせ済み**: 形状 1 は骨格の画素集合がビット単位で一致(724/724)、
    形状 2/3 は画素数が公表値と一致(2434 / 3895)。
    tests/test_regions2.py::test_em_skeleton_matches_published_em93_reference。
    (HALCON 実機との直接照合は未実施だが、HALCON が拠る同じ公表アルゴリズムの
    参照出力と一致している):

      interior = 4 近傍がすべて前景の画素
      simple   = (8,4) 単純点(前景 8 連結成分 1 個 ∧ 接する背景 4 連結成分 1 個)
      perfect  = ある 4 方向の隣が interior で、その反対方向が背景
      「simple かつ perfect な画素を全部同時に消す」を不動点まで反復

    注: ノートの転記を字義どおり「強(4)連結成分のみで simple を数える」と
    実装すると並列削除が斜め橋を同時に落とし位相が壊れる(反例で実測)。
    simple を標準の (8,4) 単純点にした本実装が参照出力とビット単位で
    一致したので、これが EM93 の正しい読みだと裏付けられている。

    完全並列・対称(90 度回転/鏡映と可換)・位相保存・冪等。Zhang–Suen 系の
    `sk_skeleton` より枝を多く残す(実測 1.4〜1.5 倍の画素数 = Couprie の
    比較表で EM が対称・枝多である性格と整合)。ヒゲは `pruning` で後処理する
    流儀も HALCON と同じ。つまみ a, b は未使用。
    """
    x = _as_mask(v).astype(bool)
    if not x.any():
        return np.zeros(x.shape, np.float64)
    lut = _em_simple_lut()
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    # 環順 (N,NE,E,SE,S,SW,W,NW) の (dy, dx)
    offs = [(-1, 0), (-1, 1), (0, 1), (1, 1),
            (1, 0), (1, -1), (0, -1), (-1, -1)]

    def shifted(arr, dy, dx):
        """value[P] = arr[P + (dy,dx)](外は背景=False)。"""
        p = np.zeros((arr.shape[0] + 2, arr.shape[1] + 2), dtype=arr.dtype)
        p[1:-1, 1:-1] = arr
        return p[1 + dy:1 + dy + arr.shape[0], 1 + dx:1 + dx + arr.shape[1]]

    while True:
        interior = ndimage.binary_erosion(x, structure=cross, border_value=0)
        code = np.zeros(x.shape, dtype=np.int64)
        for k, (dy, dx) in enumerate(offs):
            code |= shifted(x, dy, dx).astype(np.int64) << k
        simple = lut[code]
        perfect = np.zeros_like(x)
        for k in (0, 2, 4, 6):                       # 強(4)方向のみ
            dy, dx = offs[k]
            oy, ox = offs[(k + 4) % 8]
            perfect |= shifted(interior, dy, dx) & ~shifted(x, oy, ox)
        delete = x & ~interior & simple & perfect
        if not delete.any():
            break
        x = x & ~delete
    return x.astype(np.float64)


def r2_endpoints_skeleton(v, a, b):
    """骨格の端点(8 近傍にちょうど 1 個の骨格画素を持つ点)を抽出する。

    HALCON の `junctions_skeleton` は EndPoints と JuncPoints の両方を返すが、
    fullseye の `junctions_skeleton` は分岐点のみなので、端点側をこの op が担う。
    入力が骨格でない場合は em_skeleton で細線化してから端点を取る。
    孤立 1 画素(近傍 0)も端点に数える。つまみ a, b は未使用。
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
    interior = ndimage.binary_erosion(m, structure=cross, border_value=0)
    sk = m if not interior.any() else (em_skeleton(v, a, b) > 0.5)
    kernel = np.ones((3, 3), dtype=np.int64)
    neigh = ndimage.convolve(sk.astype(np.int64), kernel, mode="constant") - sk
    out[sk & (neigh <= 1)] = 1.0
    return out


# --------------------------------------------------------------------------- #
# registry assembly
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the r2_ binary-region operator tier."""
    cat = "region"
    defs = [
        ("r2_inner_circle", "inner_circle", REGION, REGION, r2_inner_circle),
        ("r2_inner_rectangle1", "inner_rectangle1", REGION, REGION, r2_inner_rectangle1),
        # halcon "" — smallest_rectangle1 is already covered by a core op; this is a
        # genuine alternate impl, not new coverage (no double-claim).
        ("r2_smallest_rectangle1", "", REGION, REGION, r2_smallest_rectangle1),
        ("r2_smallest_circle", "smallest_circle", REGION, REGION, r2_smallest_circle),
        ("r2_smallest_rectangle2", "smallest_rectangle2", REGION, REGION, r2_smallest_rectangle2),
        ("r2_sort_region", "sort_region", REGION, REGION, r2_sort_region),
        ("r2_union1", "union1", REGION, REGION, r2_union1),
        ("r2_partition_rectangle", "partition_rectangle", REGION, REGION, r2_partition_rectangle),
        ("r2_runlength_features", "runlength_features", REGION, FEATURE, r2_runlength_features),
        ("r2_split_skeleton_lines", "split_skeleton_lines", REGION, REGION, r2_split_skeleton_lines),
        # halcon "" — `skeleton` の coverage は core の skeleton op が既に主張
        # している(二重計上しない)。これは同系アルゴリズム(EM93)の別実装。
        ("em_skeleton", "", REGION, REGION, em_skeleton),
        # halcon "" — junctions_skeleton の coverage は既存 op が主張済み。
        # HALCON 版が返す EndPoints 側をこの op が補完する(二重計上しない)。
        ("r2_endpoints_skeleton", "", REGION, REGION, r2_endpoints_skeleton),
    ]
    return [Op(name, cat, halcon, isort, osort, fn)
            for (name, halcon, isort, osort, fn) in defs]
