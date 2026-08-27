"""2-D occupancy / free-space mapping for navigation (numpy + scipy).

The planning-grid layer above :mod:`terrain`: collapse a 3-D cloud (from
:mod:`camera`/:mod:`stereo`) into a top-down occupancy grid, grow obstacles by the
robot's radius (configuration space), turn that into a clearance / distance-to-
obstacle cost field, test line-of-sight between cells, and find exploration
frontiers. These are the classic 2-D navigation primitives a path planner consumes
— the "where can I walk / drive and how do I get there" companion to terrain's
"is this cell steppable".

Frame convention: a **world/ground frame** where x, y span the ground and z is up
(same as :mod:`terrain`). Grids are indexed ``[row=y, col=x]`` with a returned
``extent = (xmin, xmax, ymin, ymax)``.

References (public literature — reimplemented, not derived from any product):
- Elfes, "Using occupancy grids for mobile robot perception and navigation",
  Computer 1989 (occupancy grids).
- Lozano-Pérez & Wesley, "An algorithm for planning collision-free paths...",
  CACM 1979 (configuration-space obstacle growing).
- Yamauchi, "A frontier-based approach for autonomous exploration", CIRA 1997.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["occupancy_grid_2d", "inflate_obstacles", "clearance_map",
           "line_of_sight", "frontier_cells",
           # 3-D voxel occupancy + ESDF (robot motion planning; see section below)
           "occupancy_grid", "esdf", "inflate", "query_distance"]


def occupancy_grid_2d(points, cell: float = 0.05, z_range=None, bounds=None,
                      min_points: int = 1):
    """Collapse a 3-D cloud into a top-down 2-D occupancy grid.

    Points are binned by their (x, y); a cell is occupied when at least
    *min_points* fall in it. ``z_range=(zmin, zmax)`` keeps only points in a height
    slab first (e.g. the robot's body height, so the floor and high canopy don't
    count as obstacles). ``bounds=(xmin, xmax, ymin, ymax)`` fixes the extent
    (defaults to the data range). Returns ``(occ boolean grid, extent)``."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    if z_range is not None:
        zlo, zhi = z_range
        P = P[(P[:, 2] >= zlo) & (P[:, 2] <= zhi)]
    x, y = P[:, 0], P[:, 1]
    if bounds is None:
        if P.shape[0] == 0:
            raise ValueError("empty cloud and no bounds given")
        xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
    else:
        xmin, xmax, ymin, ymax = bounds
        if not (xmax > xmin and ymax > ymin):   # degenerate/inverted bounds -> fail-closed
            # silently accepting these drops every point (in-bounds mask is empty)
            # and returns a phantom all-free grid with an inverted extent; the 3-D
            # occupancy_grid rejects the same condition, so match it here.
            raise ValueError(
                "degenerate 2-D bounds: require xmax > xmin and ymax > ymin")
    nx = max(1, int(np.ceil((xmax - xmin) / cell)))
    ny = max(1, int(np.ceil((ymax - ymin) / cell)))
    counts = np.zeros((ny, nx), np.int64)
    if P.shape[0]:
        # DROP out-of-bounds points; clamping them onto the edge cells would pile up
        # phantom obstacles along the grid border.
        inb = (x >= xmin) & (x <= xmax) & (y >= ymin) & (y <= ymax)
        jx = np.clip(((x[inb] - xmin) / cell).astype(int), 0, nx - 1)
        iy = np.clip(((y[inb] - ymin) / cell).astype(int), 0, ny - 1)
        np.add.at(counts, (iy, jx), 1)
    return counts >= int(min_points), (xmin, xmax, ymin, ymax)


def inflate_obstacles(occ, radius_cells: float):
    """Grow occupied cells by *radius_cells* (configuration-space obstacles).

    A point robot planning on the inflated grid keeps a real robot of that radius
    clear of obstacles (Lozano-Pérez 1979). Uses a Euclidean disk, so corners are
    rounded correctly (not a square dilation). Returns a boolean grid."""
    occ = np.asarray(occ, bool)
    r = float(radius_cells)
    if r <= 0 or not occ.any():
        return occ.copy()                           # no obstacles -> nothing to inflate
    # distance from every free cell to the nearest obstacle; inflate where <= r
    dist = ndimage.distance_transform_edt(~occ)
    return dist <= r


def clearance_map(occ, cell: float = 0.05):
    """Distance from each cell to the nearest obstacle, in world units.

    The Euclidean distance transform of the free space — a smooth cost field a
    planner uses to prefer routes with margin (larger = safer). Occupied cells are
    0. With no obstacles the clearance is infinite everywhere (nothing to avoid) —
    not the corner-biased distance-to-border a raw EDT of an all-free grid invents.
    Returns a float grid in the same units as *cell*."""
    occ = np.asarray(occ, bool)
    if not occ.any():
        return np.full(occ.shape, np.inf)
    return ndimage.distance_transform_edt(~occ) * float(cell)


def line_of_sight(occ, start, end) -> bool:
    """True if the straight segment between two cells crosses no obstacle.

    Bresenham traversal of the occupancy grid between ``start`` and ``end`` (each
    ``(row, col)``) with **corner-cutting rejected**: a diagonal step is blocked if
    both cells flanking the corner are occupied, so the line cannot tunnel between two
    diagonally-touching obstacles. The collision test a planner runs to add an edge or
    shortcut a path. Endpoints outside the grid, or either endpoint occupied, return
    False.

    **Undirected (symmetric):** Bresenham's error stepping and the corner-cut test
    both depend on the traversal direction, so a single scan can disagree with itself
    when the two argument orders quantise the same segment onto different cells (a
    grazing tie). To keep ``line_of_sight(a, b) == line_of_sight(b, a)`` for a
    planner's visibility graph — and to stay fail-closed — the segment is scanned in
    **both** directions and reported clear only when both agree; a segment that grazes
    an obstacle from either end is blocked."""
    occ = np.asarray(occ, bool)
    H, W = occ.shape
    r0, c0 = int(start[0]), int(start[1])
    r1, c1 = int(end[0]), int(end[1])
    if not (0 <= r0 < H and 0 <= c0 < W and 0 <= r1 < H and 0 <= c1 < W):
        return False
    if occ[r0, c0] or occ[r1, c1]:
        return False

    def _scan(ra, ca, rb, cb):
        """Directed Bresenham scan ra→rb with corner-cut rejection (True = clear)."""
        dr = abs(rb - ra)
        dc = abs(cb - ca)
        sr = 1 if rb > ra else -1
        sc = 1 if cb > ca else -1
        r, c = ra, ca
        err = dr - dc
        while True:
            if occ[r, c]:
                return False
            if r == rb and c == cb:
                return True
            e2 = 2 * err
            moved_r = moved_c = False
            if e2 > -dc:
                err -= dc
                r += sr
                moved_r = True
            if e2 < dr:
                err += dr
                c += sc
                moved_c = True
            if moved_r and moved_c and occ[r - sr, c] and occ[r, c - sc]:
                return False                        # diagonal step would cut a corner

    # scan both directions and require both clear -> symmetric and fail-closed
    return _scan(r0, c0, r1, c1) and _scan(r1, c1, r0, c0)


def frontier_cells(free, unknown, min_cluster: int = 1):
    """Frontier cells for exploration: free cells adjacent to unknown space.

    A frontier is the boundary between what the robot has mapped as free and what it
    has not seen (Yamauchi 1997) — the places worth driving toward to grow the map.
    ``free`` and ``unknown`` are boolean grids (a cell is typically free, occupied or
    unknown). Returns ``(frontier_mask, clusters)`` where *clusters* is a list of
    (row, col) arrays (connected frontier segments >= *min_cluster*, largest first),
    each a candidate exploration target."""
    free = np.asarray(free, bool)
    unknown = np.asarray(unknown, bool)
    if free.shape != unknown.shape:
        raise ValueError("free and unknown grids must have the same shape")
    # a free cell touching unknown in its 4-neighbourhood is a frontier
    near_unknown = ndimage.binary_dilation(unknown, iterations=1) & free
    lbl, n = ndimage.label(near_unknown)
    clusters = []
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        if ys.size >= int(min_cluster):
            clusters.append(np.stack([ys, xs], 1))
    clusters.sort(key=lambda a: -a.shape[0])
    return near_unknown, clusters


# ═══════════════════════════════════════════════════════════════════════════
# 3-D voxel occupancy + Euclidean Signed Distance Field (ESDF) — robot planning
# ═══════════════════════════════════════════════════════════════════════════
# 差別化 (固有価値, honest):
#   - match3d.points_to_voxel は点を splat した **密度 voxel**(float カウント)で
#     マッチング用。ここは planning 用の **占有 (bool) → ESDF → 膨張 → 距離クエリ**。
#   - 上の occupancy_grid_2d / inflate_obstacles / clearance_map は **2-D 俯瞰**格子
#     (航法)。ここは **3-D 体積**格子(6-DoF アーム/飛行体の C-space)で、外正・内負の
#     **符号付き** 距離場と任意座標での連続クエリ(三線形補間)を持つのが固有。
#   - terrain.* は高さ場、volops.vol_distance_transform は符号無し EDT のみ。
# ESDF>0=外(自由)で最近占有までの距離、ESDF<0=内(占有)で最近自由までの距離。
# planner は margin(ESDF>=r_robot)と勾配(∇ESDF=退避方向)にこれを使う。


def _parse_bounds(bounds):
    """bounds=((xmin,xmax),(ymin,ymax),(zmin,zmax)) を (lo(3,), span(3,)) に。退化は ValueError。"""
    b = np.asarray(bounds, np.float64)
    if b.shape != (3, 2):
        raise ValueError("bounds must be ((xmin,xmax),(ymin,ymax),(zmin,zmax))")
    lo, hi = b[:, 0], b[:, 1]
    span = hi - lo
    if not np.all(span > 0):                    # 退化 (max<=min) は fail-closed
        raise ValueError("degenerate bounds: max must exceed min on every axis")
    return lo, span


def occupancy_grid(points, bounds, res):
    """点群 (N,3) → 3-D 占有ボクセル格子 (res,res,res) bool(点の落ちた voxel を占有)。

    ``bounds=((xmin,xmax),(ymin,ymax),(zmin,zmax))`` が格子の張る体積、``res`` は各軸の
    ボクセル数(立方 res³)。ボクセルは半開区間 [lo+i/res*span, lo+(i+1)/res*span) で、
    上端 (frac==1) の点は最終ボクセルに含める。**bounds 外の点は落とす**(端セルへ
    clamp すると境界に幻の障害物が積もるため)。match3d.points_to_voxel が密度(float)
    を作るのに対し、これは planning 用の占有(bool)を作る点が固有。

    Raises ValueError for res<=0, non-(N,3) points, or degenerate bounds."""
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    res = int(res)
    if res <= 0:                                # fail-closed
        raise ValueError("res must be a positive integer")
    lo, span = _parse_bounds(bounds)
    grid = np.zeros((res, res, res), bool)
    if P.shape[0] == 0:
        return grid                             # 空雲 → 何も占有しない(honest: 幻を足さない)
    frac = (P - lo) / span                      # in-bounds なら [0,1]
    inb = np.all((frac >= 0.0) & (frac <= 1.0), axis=1)
    if not np.any(inb):
        return grid
    fi = frac[inb]
    # floor(frac*res); frac==1 は res になるので最終ボクセル res-1 にクランプ
    idx = np.minimum((fi * res).astype(np.int64), res - 1)
    grid[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return grid


def _sampling(voxel_size):
    """voxel_size(スカラ=等方 / 長さ3=異方)→ scipy EDT の sampling。<=0 は ValueError。"""
    vs = np.atleast_1d(np.asarray(voxel_size, np.float64))
    if vs.size == 1:
        s = float(vs[0])
        if s <= 0:
            raise ValueError("voxel_size must be positive")
        return s
    if vs.size == 3:
        if not np.all(vs > 0):
            raise ValueError("voxel_size components must be positive")
        return tuple(float(v) for v in vs)
    raise ValueError("voxel_size must be a scalar or length-3 sequence")


def esdf(occupancy, voxel_size=1.0):
    """占有格子 → Euclidean 符号付き距離場 (ESDF)(外=+ 最近占有まで, 内=- 最近自由まで)。

    ``scipy.ndimage.distance_transform_edt`` を自由側(外)と占有側(内)に別々にかけ、
    ``d_out - d_in`` で符号を付ける。``voxel_size`` はボクセル辺長(等方スカラ or 異方
    長さ3。EDT の ``sampling`` に渡す)で、返る距離は world 単位。全自由なら +inf、全占有
    なら -inf(honest: 最近対辺が存在しない)。ゼロ交差は占有/自由ボクセル**中心の中間**に
    落ちるため、境界セル中心の |ESDF| は約 1 ボクセル(下流テストの許容根拠)。

    Raises ValueError for voxel_size<=0."""
    occ = np.asarray(occupancy, bool)
    samp = _sampling(voxel_size)
    if not occ.any():                           # 障害物なし → 最近占有は無限遠
        return np.full(occ.shape, np.inf, np.float64)
    if occ.all():                               # 全占有 → 最近自由は無限遠(内側なので負)
        return np.full(occ.shape, -np.inf, np.float64)
    d_out = ndimage.distance_transform_edt(~occ, sampling=samp)   # 自由セル: 最近占有まで(>0)
    d_in = ndimage.distance_transform_edt(occ, sampling=samp)     # 占有セル: 最近自由まで(>0)
    return d_out - d_in                         # 外 +, 内 -


def inflate(occupancy, radius, voxel_size=1.0):
    """障害物を ``radius``(world 単位)膨張した占有格子 bool(= ESDF<=radius を占有)。

    planner の安全マージン: 点ロボットが膨張格子上で衝突回避すれば、半径 radius の実
    ロボットが障害物から離隔を保つ(configuration-space obstacle)。ESDF は外で正の
    最近占有距離なので、``ESDF<=radius`` は「占有(負)∪ 障害物から radius 以内の自由」を
    捕らえる。radius を増やすと単調に占有が増える(下流テストの GT)。

    Raises ValueError for radius<0 (voxel_size<=0 は esdf 経由で ValueError)."""
    occ = np.asarray(occupancy, bool)
    r = float(radius)
    if r < 0:                                   # fail-closed
        raise ValueError("radius must be non-negative")
    if r == 0.0 or not occ.any():
        return occ.copy()                       # 膨張なし / 障害物なし
    return esdf(occ, voxel_size) <= r


def query_distance(esdf_grid, bounds, res, query_points, mode="trilinear"):
    """任意 world 座標 (M,3) での ESDF 値 (M,) を返す(``mode``='trilinear' 補間 or 'nearest')。

    ``bounds``/``res`` は ESDF を作った格子と同じもの。world→連続ボクセル座標は
    ``c=(q-lo)/span*res-0.5``(voxel i の中心が c=i)。三線形補間はボクセル中心 8 近傍を
    重み付け(格子外はエッジにクランプ=最近端の値で外挿)。planner がノード/経路上の任意点で
    離隔を問い合わせる用途。返り値は ESDF と同じ world 単位。

    Raises ValueError for res<=0, degenerate bounds, non-(M,3) query, or unknown mode."""
    E = np.asarray(esdf_grid, np.float64)
    res = int(res)
    if res <= 0:
        raise ValueError("res must be a positive integer")
    if E.shape != (res, res, res):
        raise ValueError("esdf_grid shape must be (res, res, res)")
    lo, span = _parse_bounds(bounds)
    Q = np.asarray(query_points, np.float64)
    if Q.ndim != 2 or Q.shape[1] != 3:
        raise ValueError("query_points must be (M, 3)")
    c = (Q - lo) / span * res - 0.5             # voxel-center-aligned 連続座標
    if mode == "nearest":
        idx = np.clip(np.round(c).astype(np.int64), 0, res - 1)
        return E[idx[:, 0], idx[:, 1], idx[:, 2]]
    if mode != "trilinear":
        raise ValueError("mode must be 'trilinear' or 'nearest'")
    c0 = np.floor(c).astype(np.int64)
    t = c - c0                                  # 各軸の小数部 [0,1)
    out = np.zeros(len(Q), np.float64)
    for dx in (0, 1):
        wx = t[:, 0] if dx else (1.0 - t[:, 0])
        i = np.clip(c0[:, 0] + dx, 0, res - 1)
        for dy in (0, 1):
            wy = t[:, 1] if dy else (1.0 - t[:, 1])
            j = np.clip(c0[:, 1] + dy, 0, res - 1)
            for dz in (0, 1):
                wz = t[:, 2] if dz else (1.0 - t[:, 2])
                k = np.clip(c0[:, 2] + dz, 0, res - 1)
                out += (wx * wy * wz) * E[i, j, k]
    return out
