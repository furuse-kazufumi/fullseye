"""Terrain / traversability building blocks (numpy + scipy only).

Turns a 3-D point cloud (e.g. from :mod:`stereo`) into a robot-centric 2.5-D
elevation map — the "mountain-map"/heightmap used for locomotion — and derives a
traversability mask (step + slope) for foothold selection and obstacle
avoidance.

Frame convention: input points are in a **world/ground frame** where ``x`` and
``y`` span the ground plane and ``z`` is height (up). The caller is responsible
for the camera->world transform (robot-specific extrinsics); this module owns the
binning and the terrain analysis, not the robot's pose.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["elevation_map", "fill_gaps", "traversability", "foothold_score",
           "ground_surface", "ground_plane", "detect_obstacles",
           "fuse_elevation", "slope_map", "roughness_map", "surface_normals",
           "step_edges", "foothold_candidates",
           # 台帳の入口(2026-11-06): op 名は全体で 1 つ・1 語の名前は避ける、の規則に合わせた名前
           "elevation_traversability", "elevation_normals", "elevation_step_edges"]


def _grad2(a, cell):
    """(dz/dy, dz/dx) that tolerates a length-1 axis (np.gradient raises there).

    A grid with a size-1 dimension (which elevation_map can produce from a sparse
    cloud) has zero gradient along that axis, not an error."""
    gy = np.gradient(a, cell, axis=0) if a.shape[0] >= 2 else np.zeros_like(a)
    gx = np.gradient(a, cell, axis=1) if a.shape[1] >= 2 else np.zeros_like(a)
    return gy, gx


def elevation_map(points, cell: float = 0.05, agg: str = "max",
                  bounds=None):
    """Bin a point cloud into a 2.5-D elevation grid.

    Parameters
    ----------
    points : (N, 3) array of (x, y, z), z = height.
    cell   : grid resolution in world units.
    agg    : 'max' (canopy / obstacle-safe, default), 'min' (ground), or 'mean'.
    bounds : optional (xmin, xmax, ymin, ymax); defaults to the data extent.

    Returns ``(grid, extent)`` where ``grid[i, j]`` is the aggregated height of
    cell (row i = y, col j = x) and empty cells are ``nan``. ``extent`` is
    ``(xmin, xmax, ymin, ymax)``.

    空の入力(``points`` が 0 要素)は ``bounds`` があれば全セル nan の格子を返す(理由: 観測の無い範囲は nan = 観測していない。``bounds`` が無ければ範囲が決まらないので ValueError)。
    An empty cloud with ``bounds`` gives an all-``nan`` grid; without ``bounds`` it raises
    ``ValueError`` (no extent).
    """
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("points must be (N, 3)")
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    if bounds is None:
        xmin, xmax, ymin, ymax = x.min(), x.max(), y.min(), y.max()
    else:
        xmin, xmax, ymin, ymax = bounds
    nx = max(1, int(np.ceil((xmax - xmin) / cell)))
    ny = max(1, int(np.ceil((ymax - ymin) / cell)))
    jx = np.clip(((x - xmin) / cell).astype(int), 0, nx - 1)
    iy = np.clip(((y - ymin) / cell).astype(int), 0, ny - 1)
    grid = np.full((ny, nx), np.nan)
    flat = iy * nx + jx
    order = np.argsort(flat)
    fs, zs = flat[order], z[order]
    bounds_idx = np.searchsorted(fs, np.arange(nx * ny + 1))
    for c in range(nx * ny):
        lo, hi = bounds_idx[c], bounds_idx[c + 1]
        if hi > lo:
            seg = zs[lo:hi]
            grid.flat[c] = seg.max() if agg == "max" else (
                seg.min() if agg == "min" else seg.mean())
    return grid, (xmin, xmax, ymin, ymax)


def fill_gaps(grid):
    """Fill ``nan`` cells with the nearest finite height (nearest-neighbour).

    空の入力(``grid`` が 0 要素)は形を保った空の配列を返す(理由: 埋める穴が無く、形だけを保つ)。
    An empty grid comes back as an empty grid of the same shape."""
    g = np.asarray(grid, np.float64)
    nan = ~np.isfinite(g)
    if not nan.any():
        return g.copy()
    idx = ndimage.distance_transform_edt(nan, return_distances=False,
                                         return_indices=True)
    return g[tuple(idx)]


def traversability(grid, cell: float = 0.05, max_step: float = 0.1,
                   max_slope: float = 0.6, window: int = 3):
    """Boolean mask (True = traversable) from step and slope limits.

    step  = local (max - min) height over a ``window`` neighbourhood -> a curb /
            ledge / obstacle edge.
    slope = |gradient| of the height per unit distance.
    A cell is non-traversable where either exceeds its limit. ``nan`` cells
    (unobserved) are filled first and marked non-traversable.
    """
    g = np.asarray(grid, np.float64)
    if g.size == 0:                       # 以前は np.gradient の ValueError だった空の格子を、同じ型で名指しして断る
        raise ValueError("grid is empty: no cell to judge")
    unknown = ~np.isfinite(g)
    filled = fill_gaps(g)
    lo = ndimage.minimum_filter(filled, window, mode="nearest")
    hi = ndimage.maximum_filter(filled, window, mode="nearest")
    step = hi - lo
    gy, gx = _grad2(filled, cell)          # 幅 1 の軸でも落ちない(2026-11-08、値は 2 以上の軸で同じ)
    slope = np.hypot(gx, gy)
    ok = (step <= max_step) & (slope <= max_slope) & (~unknown)
    return ok


def ground_surface(grid, cell: float = 0.05, radius: float = 0.4):
    """Smooth walkable-ground envelope by grey-opening (min-filter then max-filter).

    A morphological opening with a structuring element ``radius`` wide follows
    gentle undulation and erases anything narrower that sticks *up*, which makes it
    a good ground model for **rough / curved** terrain. Honest limit: a flat
    structuring element cannot sit under a steep ramp at the grid's up-slope
    border, so on a strong planar slope the envelope lags by ``~radius*slope``
    there and :func:`detect_obstacles` with ``ground='opening'`` can report a
    phantom obstacle in the last ``radius/cell`` cells — use the default
    ``ground='plane'`` for planar/ramp ground. ``nan`` cells are filled first.

    空の入力(``grid`` が 0 要素)は形を保った空の配列を返す(理由: 観測の無い地図には地面の包絡も無く、形だけを保つ)。"""
    filled = fill_gaps(np.asarray(grid, np.float64))
    w = max(3, int(round(2.0 * radius / max(cell, 1e-6))) | 1)   # odd cell window
    return ndimage.maximum_filter(
        ndimage.minimum_filter(filled, w, mode="nearest"), w, mode="nearest")


def ground_plane(grid, trim: float = 0.3, iters: int = 3):
    """Robust least-squares ground plane ``z = a·x + b·y + c`` per cell.

    Fits a plane to the (filled) elevation, then re-fits a few times after
    trimming the highest-residual cells — the ones that rise above the ground and
    are therefore obstacles, not ground. Recovers a flat *or* tilted (ramp) ground
    exactly, with no boundary artefact, which is what obstacle detection wants
    when the walkable surface is planar. *trim* is the top residual fraction
    discarded each iteration.

    空の入力(``grid`` が 0 要素)は形を保った空の配列を返す(理由: 当てはめる高さが無く、形だけを保つ。観測が 3 セル未満の地図は nan の平面)。"""
    filled = fill_gaps(np.asarray(grid, np.float64))
    ny, nx = filled.shape
    yy, xx = np.mgrid[0:ny, 0:nx].astype(np.float64)
    A = np.stack([xx.ravel(), yy.ravel(), np.ones(xx.size)], axis=1)
    z = filled.ravel()
    finite = np.isfinite(z)
    if int(finite.sum()) < 3:           # a fully unobserved map -> NaN plane (visible),
        return np.full((ny, nx), np.nan)  # not a fake z=0 ground that reads as "clear"
    keep = finite.copy()
    coef = np.zeros(3)
    for _ in range(max(1, int(iters))):
        coef, *_ = np.linalg.lstsq(A[keep], z[keep], rcond=None)
        resid = z - A @ coef
        thresh = np.quantile(resid[finite], 1.0 - float(trim))
        keep = finite & (resid <= thresh)   # trim high residuals but never re-admit NaNs
        if int(keep.sum()) < 3:
            break
    return (A @ coef).reshape(ny, nx)


def detect_obstacles(grid, cell: float = 0.05, clearance: float = 0.12,
                     ground: str = "plane", ground_radius: float = 0.4,
                     trim: float = 0.3, min_area: float = 0.01, extent=None):
    """Segment cells rising more than *clearance* above the walkable ground.

    The ground model isolates obstacles from a sloped surface: ``ground='plane'``
    (default) fits a robust :func:`ground_plane` (best when the ground is planar —
    flat or ramp); ``ground='opening'`` uses the morphological
    :func:`ground_surface` envelope (best for rough/curved terrain); or pass a
    precomputed ground height array. So a ramp is not an obstacle but a box, curb,
    or rock on it is. Returns ``(mask, obstacles)``: a boolean obstacle mask and a
    list of per-obstacle dicts sorted largest-first, each with ``area_cells`` /
    ``area`` (m²) / ``height`` (peak rise above ground) / ``centroid_cell``
    (row, col) / ``bbox_cells`` (i0, j0, i1, j1), plus ``centroid_xy`` in world
    units when *extent* (from :func:`elevation_map`) is given. Blobs smaller than
    *min_area* (m²) are dropped as noise.

    ★``ground_radius`` は ``ground='opening'`` のときだけ読まれ、``trim`` は ``'plane'`` のときだけ。
    空の入力(``grid`` が 0 要素)は空の mask と空の listを返す(理由: 観測の無い地図には障害物も無く、形だけを保つ)。"""
    filled = fill_gaps(np.asarray(grid, np.float64))
    if isinstance(ground, np.ndarray):
        gsurf = np.asarray(ground, np.float64)
    elif ground == "plane":
        gsurf = ground_plane(grid, trim=trim)
    elif ground == "opening":
        gsurf = ground_surface(grid, cell, ground_radius)
    else:
        raise ValueError("ground must be 'plane', 'opening', or an array, got %r" % (ground,))
    above = filled - gsurf
    mask = above > float(clearance)
    min_cells = max(1, int(np.ceil(min_area / (cell * cell))))   # drop blobs strictly < min_area
    lbl, n = ndimage.label(mask)
    obstacles = []
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        if xs.size < min_cells:
            mask[ys, xs] = False
            continue
        rec = {
            "area_cells": int(xs.size),
            "area": float(xs.size) * cell * cell,
            "height": float(above[ys, xs].max()),
            "centroid_cell": (float(ys.mean()), float(xs.mean())),
            "bbox_cells": (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())),
        }
        if extent is not None:
            xmin, _xmax, ymin, _ymax = extent
            rec["centroid_xy"] = (xmin + (xs.mean() + 0.5) * cell,
                                  ymin + (ys.mean() + 0.5) * cell)
        obstacles.append(rec)
    obstacles.sort(key=lambda r: r["area_cells"], reverse=True)
    return mask, obstacles


def foothold_score(grid, cell: float = 0.05, window: int = 3):
    """Per-cell flatness score in [0, 1] (1 = flat & level = good foothold).

    Combines local roughness (height std) and slope into a single score; useful
    to rank candidate step locations for a legged robot."""
    g0 = np.asarray(grid, np.float64)
    if g0.size == 0:                      # 以前は np.gradient の ValueError だった空の格子を、同じ型で名指しして断る
        raise ValueError("grid is empty: no cell to score")
    filled = fill_gaps(g0)
    m = ndimage.uniform_filter(filled, window, mode="nearest")
    m2 = ndimage.uniform_filter(filled * filled, window, mode="nearest")
    rough = np.sqrt(np.maximum(m2 - m * m, 0.0))
    gy, gx = _grad2(filled, cell)          # 幅 1 の軸でも落ちない(2026-11-08、値は 2 以上の軸で同じ)
    slope = np.hypot(gx, gy)
    score = np.exp(-(rough / max(cell, 1e-6))) * np.exp(-slope)
    return np.clip(score, 0.0, 1.0)


def fuse_elevation(grids, agg: str = "max"):
    """Fuse several aligned elevation grids into one robot-centric map.

    Multi-frame accumulation: as a robot walks it sees the terrain from several
    depth frames; binning each into an :func:`elevation_map` on a common grid and
    fusing them here fills gaps and firms up heights. ``agg`` = 'max' (obstacle-safe,
    default), 'min' (ground-safe) or 'mean'. ``nan`` (unobserved in a given frame)
    is ignored; a cell unobserved in *every* frame stays ``nan``. Input grids must
    share a shape."""
    stack = np.stack([np.asarray(g, np.float64) for g in grids], 0)
    if stack.ndim != 3:
        raise ValueError("grids must be a sequence of equal-shape 2-D arrays")
    if agg not in ("max", "min", "mean"):
        raise ValueError("agg must be 'max', 'min' or 'mean', got %r" % (agg,))
    allnan = ~np.isfinite(stack).any(0)
    import warnings
    with warnings.catch_warnings():          # all-NaN cells are handled below, not an error
        warnings.simplefilter("ignore", RuntimeWarning)
        fn = {"max": np.nanmax, "min": np.nanmin, "mean": np.nanmean}[agg]
        out = fn(stack, 0)
    out[allnan] = np.nan
    return out


def slope_map(grid, cell: float = 0.05, degrees: bool = True):
    """Per-cell terrain slope = angle of the surface from horizontal.

    ``atan(|grad z|)`` from the (filled) heightmap gradient, in degrees (default)
    or radians. The steepness a leg has to cope with — a walkability primitive
    complementing :func:`traversability`.

    ★台帳(op)には載せず、``dem_slope(grid, cell, method="central")`` に寄せた(2026-11-06)。
    内側のセルは中央差分どうしでビット一致(実測の差 0.0)。違うのは外周 1 セル(こちらは
    ``np.gradient`` の片側差分、``dem_slope`` は端の複製で緩めに出る)と穴(こちらは
    最寄りの値で埋めてから測り、``dem_slope`` は ``nan`` を 3x3 に伝播 = 観測していない所を
    平らと言わない)。同じ量に op 名を 2 つ持たせないため。
    Not a ledger op: the walking chain uses ``dem_slope(method="central")``, which is
    bit-identical in the interior; only the border cells and the hole handling differ."""
    filled = fill_gaps(np.asarray(grid, np.float64))
    gy, gx = _grad2(filled, cell)
    ang = np.arctan(np.hypot(gx, gy))
    return np.degrees(ang) if degrees else ang


def roughness_map(grid, window: int = 3):
    """Per-cell surface roughness = local height standard deviation over a
    ``window`` neighbourhood. High on rubble / vegetation, ~0 on smooth ground.

    ★``dem_roughness``(Riley 1999 の TRI = 8 近傍との差の二乗平均平方根、近傍 1 セル固定)
    とは**別の量**なので別の op として残す: こちらは窓の中の標準偏差(中心を含む、窓の幅が
    つまみ)。傾き a の平面では ``a·cell·√(2/3)`` と TRI の ``a·cell·√(3/4)`` で、乱れた地形
    では TRI の約 0.7 倍(実測の中央値)。:func:`foothold_score` の粗さの項はこの量。
    空の入力(``grid`` が 0 要素)は形を保った空の配列を返す(理由: 観測の無い地図は形を保った空の地図で、どの格子も測っていない)。
    A different quantity from ``dem_roughness`` (TRI): a windowed standard deviation."""
    filled = fill_gaps(np.asarray(grid, np.float64))
    m = ndimage.uniform_filter(filled, window, mode="nearest")
    m2 = ndimage.uniform_filter(filled * filled, window, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def surface_normals(grid, cell: float = 0.05):
    """Per-cell terrain surface normal (H, W, 3), unit, pointing up (+z).

    From the heightmap gradient: ``n = normalize([-dz/dx, -dz/dy, 1])``. A flat
    patch gives ``[0, 0, 1]``; a ramp tilts accordingly. Feeds foot-orientation
    planning and slope-aware foothold scoring."""
    filled = fill_gaps(np.asarray(grid, np.float64))
    gy, gx = _grad2(filled, cell)
    n = np.stack([-gx, -gy, np.ones_like(gx)], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def elevation_traversability(grid, cell: float = 0.05, max_step: float = 0.1,
                             max_slope: float = 0.6, window: int = 3):
    """Traversable cells of an elevation map (True = within the step and slope limits) — ledger door of :func:`traversability`.

    中身は :func:`traversability` と同じ。台帳の名前を変えたのは、1 語の op 名は意味が足りない
    (``<族>_<対象>_<動作>``)という名前の規則のため(素の関数の名前は変えない)。
    step = 窓 ``window`` の中の高さの幅、slope = 勾配の大きさ。どちらかが上限を超えるセルと
    観測していない(``nan``)セルは False。幅 1 の軸の格子も受ける。
    """
    return traversability(grid, cell=cell, max_step=max_step, max_slope=max_slope, window=window)


def elevation_normals(grid, cell: float = 0.05):
    """Unit up-pointing normals (H, W, 3) of an elevation map — ledger door of :func:`surface_normals`.

    地形の高さ図の単位法線(+z 向き)。中身は :func:`surface_normals` と同じ。台帳の名前を
    変えたのは、``surface_normals`` が 3-D の測光(ops3d)の op 名で、``terrain_surface_normals`` は
    facade の正式名(別名の表 opnames)として既に使われているため(op 名は全体で 1 つ)。
    空の入力(``grid`` が 0 要素)は (0, W, 3) の空の配列を返す(理由: 観測の無い地図は法線も無く、形だけを保つ)。
    """
    return surface_normals(grid, cell=cell)


def elevation_step_edges(grid, min_rise: float = 0.05, window: int = 3):
    """Step edges (curbs / stair nosings) of an elevation map -> ``(edge_mask, signed_rise)`` (ledger door).

    中身は :func:`step_edges` と同じで、``cell`` を持たない。``step_edges`` の ``cell`` は勾配の
    **符号**を選ぶのにしか使われず(段差の高さ = 窓の max − min、向き = 勾配の大きいほうの成分の
    符号。どちらも cell で割っても変わらない)効かないノブになるので、台帳の入口から外した
    (素の関数の引数は公開の約束なので外さない)。台帳の宣言 out は mask(``edge_mask``)。
    空の入力(``grid`` が 0 要素)は空の 2 枚の配列を返す(理由: 観測の無い地図には段差も無く、形だけを保つ)。
    """
    return step_edges(grid, min_rise=min_rise, window=window)


def step_edges(grid, cell: float = 0.05, min_rise: float = 0.05, window: int = 3):
    """Detect step edges (curbs / stair nosings) in the heightmap.

    A step is a cell whose neighbourhood height range (max - min over *window*)
    exceeds *min_rise*. Returns ``(edge_mask, signed_rise)`` where ``signed_rise``
    is the along-gradient height change per cell (positive = step **up** in the
    +gradient direction, negative = step down) — the terrain feature a climbing
    gait keys on. The stair/curb detector locomotion asked for."""
    filled = fill_gaps(np.asarray(grid, np.float64))
    lo = ndimage.minimum_filter(filled, window, mode="nearest")
    hi = ndimage.maximum_filter(filled, window, mode="nearest")
    relief = hi - lo
    edge = relief > float(min_rise)
    gy, gx = _grad2(filled, cell)
    # signed_rise = full local relief (the step height), signed by the DOMINANT
    # gradient component. The old |grad|*cell*sign(gx+gy) both under-reported a sharp
    # step ~2x (central diff spreads it over 2 cells) and vanished (sign 0) for any
    # step not aligned to +x/+y (e.g. a diagonal curb where gx = -gy).
    dom = np.where(np.abs(gx) >= np.abs(gy), gx, gy)
    signed = relief * np.sign(dom)
    return edge, np.where(edge, signed, 0.0)


def foothold_candidates(grid, cell: float = 0.05, window: int = 3,
                        min_score: float = 0.6, min_dist: float = 0.15,
                        max_n: int = 50, extent=None):
    """Pick discrete safe stepping targets from the terrain.

    Scores every cell with :func:`foothold_score`, keeps local maxima above
    *min_score*, and greedily suppresses candidates within *min_dist* (world units)
    of a better one — turning the continuous flatness field into a short list of
    "here are places you may put a foot". Returns a list of dicts sorted best-first,
    each with ``cell`` (row, col), ``score``, and ``xy`` (world) when *extent* is
    given. The actionable output a foot-placement planner consumes."""
    g = np.asarray(grid, np.float64)
    observed = np.isfinite(g)                       # never propose a foot where the
    score = foothold_score(g, cell=cell, window=window)   # terrain was not observed
    peak = score >= ndimage.maximum_filter(score, window, mode="nearest") - 1e-12
    ys, xs = np.where(peak & (score >= float(min_score)) & observed)
    if ys.size == 0:
        return []
    vals = score[ys, xs]
    order = np.argsort(-vals)
    ys, xs, vals = ys[order], xs[order], vals[order]
    min_cells = float(min_dist) / max(cell, 1e-9)
    chosen = []
    for y, x, v in zip(ys, xs, vals):
        if any((y - cy) ** 2 + (x - cx) ** 2 < min_cells ** 2 for cy, cx, _ in chosen):
            continue
        chosen.append((y, x, v))
        if len(chosen) >= int(max_n):
            break
    out = []
    for y, x, v in chosen:
        rec = {"cell": (int(y), int(x)), "score": float(v)}
        if extent is not None:
            xmin, _xmax, ymin, _ymax = extent
            rec["xy"] = (xmin + (x + 0.5) * cell, ymin + (y + 0.5) * cell)
        out.append(rec)
    return out
