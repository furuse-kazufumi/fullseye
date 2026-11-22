"""Terrain / traversability building blocks (numpy + scipy only).

Turns a 3-D point cloud (e.g. from :mod:`stereo`) into a robot-centric 2.5-D
elevation map — the "mountain-map"/heightmap used for locomotion — and derives a
traversability mask (step + slope) for foothold selection and obstacle
avoidance.

Frame convention: input points are in a **world/ground frame** where ``x`` and
``y`` span the ground plane and ``z`` is height (up). The caller is responsible
for the camera->world transform (robot-specific extrinsics); this module owns the
binning and the terrain analysis, not the robot's pose.

The reverse direction (2026-11-15): :func:`heightmap_depth_camera` renders a height
map / DEM directly with a pinhole depth camera (OpenCV axes, world->camera pose as in
:mod:`camera`), so ``depth -> camera.depth_to_points -> elevation_map`` can be closed on
synthetic data with a known surface.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = ["elevation_map", "fill_gaps", "traversability", "foothold_score",
           "ground_surface", "ground_plane", "detect_obstacles",
           "fuse_elevation", "slope_map", "roughness_map", "surface_normals",
           "step_edges", "foothold_candidates",
           # 台帳の入口(2026-11-06): op 名は全体で 1 つ・1 語の名前は避ける、の規則に合わせた名前
           "elevation_traversability", "elevation_normals", "elevation_step_edges",
           # 高さ図を深度カメラで撮る(2026-11-15)
           "heightmap_depth_camera"]

HEIGHTMAP_DEPTH_BOTTOM_ROW_ATOL = 1e-9   # 無次元 / dimensionless: 4x4 同次変換の最終行の許容幅 / bottom-row tolerance
HEIGHTMAP_DEPTH_ROTATION_ATOL = 1e-6     # 無次元 / dimensionless: 回転行列の直交性の許容幅 / orthogonality tolerance
HEIGHTMAP_DEPTH_IMAGE_SIZE_ATOL = 1e-9   # [px] 主点から整数画素数を復元する丸め許容幅 / image-size rounding allowance
HEIGHTMAP_DEPTH_MAX_PIXELS = 4_000_000   # [px] 過大な深度画像の確保を拒否 / reject excessive image allocation
HEIGHTMAP_DEPTH_RAY_PARALLEL_TOL = 1e-15 # 無次元 / dimensionless: 足場の軸と平行な光線の判定幅 / parallel-ray threshold
HEIGHTMAP_DEPTH_STEP_BATCH = 64          # [step] 一回の march 作業配列の上限 / bound each marching work array
HEIGHTMAP_DEPTH_RAY_BATCH = 16_384       # [ray] 一回の光線束の上限 / bound each ray bundle


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
def _crossing_fraction(a0, a1):
    """上 a0 > 0 から下 a1 ≤ 0 へ入る刻みの中の交点の割合 a0/(a0 − a1)(光線 − 面が一次と見て)。"""
    den = a0 - a1
    return np.where(den > 0.0, a0 / np.where(den > 0.0, den, 1.0), 0.0)


def _pose_world_to_camera(pose, op):
    """``(R, t)``(X_cam = R·X_world + t、OpenCV の軸)か 4×4 の world→camera を (R, t) にする。

    4×4 は ndarray でも入れ子の list(JSON / MCP から来る形)でも、先に行列として読む(list の 4×4 を
    (R, t) の組と取り違えない)。4×4 の最後の行は (0, 0, 0, 1) でなければ断る。"""
    M = None
    try:
        arr = np.asarray(pose, np.float64)
    except (ValueError, TypeError):                       # (R, t) の組は形がそろわない
        arr = None
    if arr is not None and arr.shape == (4, 4):
        M = arr
    if M is not None:
        if not np.allclose(M[3], (0.0, 0.0, 0.0, 1.0), atol=HEIGHTMAP_DEPTH_BOTTOM_ROW_ATOL):
            raise ValueError("%s: a 4x4 pose must have the bottom row (0, 0, 0, 1), got %r" % (op, M[3].tolist()))
        R, t = M[:3, :3], M[:3, 3]
    elif isinstance(pose, (tuple, list)) and len(pose) >= 2:
        R = np.asarray(pose[0], np.float64)
        t = np.asarray(pose[1], np.float64).ravel()
    else:
        shape = None if arr is None else arr.shape
        raise ValueError("%s: pose must be (R, t) or a 4x4 world->camera matrix, got shape %r" % (op, shape))
    if R.shape != (3, 3) or t.size != 3 or not (np.all(np.isfinite(R)) and np.all(np.isfinite(t))):
        raise ValueError("%s: pose must be a finite (R 3x3, t 3)" % op)
    if not np.allclose(R @ R.T, np.eye(3), atol=HEIGHTMAP_DEPTH_ROTATION_ATOL) or np.linalg.det(R) <= 0.0:
        raise ValueError("%s: pose R must be a rotation (orthonormal, det +1)" % op)
    return R, t


def heightmap_depth_camera(heights, pose, K, cell: float = 0.05, origin=(0.0, 0.0), *, width=None, height=None,
                           step=None, near: float = 0.1, max_range: float = 10.0, disparity_sigma: float = 0.0,
                           baseline: float = 0.05, seed: int = 0):
    """高さ図(標高図・DEM)を、ピンホールの深度カメラで直接撮る(光線を一定の刻みで高さの上に進める)。

    画素ごとに光線を ``step`` 刻みで進め、光線が高さの面の下へ入った刻みで、前の刻みとの間を一次で補間して
    交点を取り、**光軸方向の深度 z**(:func:`camera.depth_to_points` が受ける量)を返す。高さはセルの中心の値の
    双一次補間(:func:`terrain.elevation_map` と同じ並び: ``heights[i, j]`` はセルの中心
    (``origin[0]`` + (j + ½)·cell, ``origin[1]`` + (i + ½)·cell))。セルの中心が張る範囲の外と、``nan`` の
    セル(観測していない)に触れる所には面が無い。

    * **カメラの向きの決まりは 1 つ**: :mod:`camera` と同じ OpenCV の軸(x 右・y 下・z 前)。``pose`` は
      world→camera の ``(R, t)``(X_cam = R·X_world + t、:func:`camera.project_points` と同じ)か 4×4。画素の
      中心は整数の座標(``u = c``, ``v = r``)。返した深度を :func:`camera.depth_to_points` に渡し、
      ``Rᵀ (X_cam − t)`` で世界へ戻せば元の面の上に乗る(往復)。render3d / world_camera の OpenGL の軸
      (y 上・−z 前)とは ``(x, y, z)_here = (x, −y, −z)_render3d``。
    * **刻み**: ``step`` は既定 cell/2、cell より大きい値は断る。刻みより短い弦で光線が横切る細い突起
      (1 セル幅の壁を浅い角度でかすめる所など)は飛び越しうる。交点の補間の誤差は刻みの 2 乗で縮む(平面では 0)。
    * **雑音**: ステレオ・構造化光の誤差の伝播と同じ形 ``σ_z = z²·σ_d / (f·b)``(``acceptance_scan`` の
      ``triangulation`` と同じ則。f = K[0, 0] [px]、``baseline`` b [m]、``disparity_sigma`` σ_d [px])。
      既定 σ_d = 0(雑音なし = 厳密)。``seed`` で決定的。
    * 当たらない画素・面の下から始まる光線・深度が [``near``, ``max_range``] の外の画素は ``nan``(範囲は雑音を
      足す前の深度で判定する)。
      面の下から始まる光線(カメラが地面の中)と、地図の外から面の高さより下で入ってくる光線(地図の側面)も
      ``nan``(側面は面ではない)。

    Parameters
    ----------
    heights : (ny, nx) array
        高さ図 [m](``nan`` = 観測していない)。
    pose : (R, t) or (4, 4)
        world→camera。4×4 は ndarray でも入れ子の list でもよい(最後の行は (0, 0, 0, 1))。
    K : (3, 3)
        内部行列(``camera.intrinsic_matrix``)。
    cell, origin
        セルの大きさと、格子の左下の角 (xmin, ymin)(``elevation_map`` の extent の (xmin, ymin))。
    width, height : int or None
        画像の大きさ(整数の画素。10.7 のような値は断る)。None なら主点から (2·cx + 1, 2·cy + 1)(整数でなければ断る)。

    Returns
    -------
    depth : (height, width) float64
        光軸方向の深度 [m]、当たらない所は ``nan``。

    **Raises** ``ValueError``: 形・値の誤り(pose が回転でない、K が 3×3 でない、step > cell、near ≥ max_range、
    画像が 4e6 画素を超える 等)。

    空の入力(``heights`` が 0 要素)は ValueError で拒否する。

    English: renders a height map / DEM directly with a pinhole depth camera by marching each pixel ray at a
    fixed step over the bilinear height surface and refining the crossing linearly; returns depth along the
    optical axis (OpenCV axes, world->camera pose as in camera.project_points), NaN where nothing is hit.
    Optional stereo noise sigma_z = z^2 sigma_d / (f b). The inverse of depth_to_points -> elevation_map.

    呼び出し例::

        import numpy as np
        import terrain
        R = np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]])   # 真下を向く(z 前 = 世界の −z)
        C = np.array([1.0, 1.0, 2.0])                                         # 高さ 2 m のカメラ
        K = np.array([[100.0, 0.0, 31.5], [0.0, 100.0, 23.5], [0.0, 0.0, 1.0]])
        d = terrain.heightmap_depth_camera(np.zeros((40, 40)), (R, -R @ C), K)  # 2 m 四方の平らな床
        assert d.shape == (48, 64) and np.allclose(d, 2.0)
    """
    op = "heightmap_depth_camera"
    Hm = np.asarray(heights, np.float64)
    if Hm.size == 0:
        raise ValueError("%s: heights is empty — pass a (ny, nx) height map" % op)
    if Hm.ndim != 2 or min(Hm.shape) < 2:
        raise ValueError("%s: heights must be a 2-D map of at least 2 x 2 cells, got shape %r" % (op, Hm.shape))
    if not np.any(np.isfinite(Hm)):
        raise ValueError("%s: heights has no finite cell" % op)
    c = float(cell)
    if not (np.isfinite(c) and c > 0.0):
        raise ValueError("%s: cell must be a positive finite length" % op)
    o = np.asarray(origin, np.float64).ravel()
    if o.size != 2 or not np.all(np.isfinite(o)):
        raise ValueError("%s: origin must be a finite (xmin, ymin)" % op)
    R, t = _pose_world_to_camera(pose, op)
    Km = np.asarray(K, np.float64)
    if Km.shape != (3, 3) or not np.all(np.isfinite(Km)) or Km[0, 0] <= 0 or Km[1, 1] <= 0:
        raise ValueError("%s: K must be a finite 3x3 intrinsic matrix with fx, fy > 0" % op)
    for name, v in (("width", width), ("height", height)):
        if v is not None and (isinstance(v, (bool, np.bool_)) or not np.isfinite(float(v)) or float(v) != int(float(v))):
            raise ValueError("%s: %s must be a whole number of pixels, got %r" % (op, name, v))
    W = int(round(2.0 * Km[0, 2] + 1.0)) if width is None else int(float(width))
    Hh = int(round(2.0 * Km[1, 2] + 1.0)) if height is None else int(float(height))
    if (width is None and abs(2.0 * Km[0, 2] + 1.0 - W) > HEIGHTMAP_DEPTH_IMAGE_SIZE_ATOL
            or height is None and abs(2.0 * Km[1, 2] + 1.0 - Hh) > HEIGHTMAP_DEPTH_IMAGE_SIZE_ATOL):
        raise ValueError("%s: the image size cannot be read from K (cx, cy are not (W-1)/2, (H-1)/2); pass width "
                         "and height" % op)
    if W < 1 or Hh < 1 or W * Hh > HEIGHTMAP_DEPTH_MAX_PIXELS:
        raise ValueError("%s: image must have 1..%g pixels, got %d x %d"
                         % (op, HEIGHTMAP_DEPTH_MAX_PIXELS, Hh, W))
    st = 0.5 * c if step is None else float(step)
    if not (np.isfinite(st) and 0.0 < st <= c):
        raise ValueError("%s: step must be in (0, cell] (a coarser step jumps over thin ridges), got %r" % (op, step))
    nr, mr = float(near), float(max_range)
    if not (np.isfinite(nr) and np.isfinite(mr) and 0.0 < nr < mr):
        raise ValueError("%s: need 0 < near < max_range" % op)
    sd, bl = float(disparity_sigma), float(baseline)
    if not (np.isfinite(sd) and sd >= 0.0 and np.isfinite(bl) and bl > 0.0):
        raise ValueError("%s: disparity_sigma must be >= 0 and baseline > 0" % op)
    ny, nx = Hm.shape
    # 画素の光線(カメラの座標、z 成分 1)→ 世界の単位方向
    v, u = np.mgrid[0:Hh, 0:W].astype(np.float64)
    yk = (v - Km[1, 2]) / Km[1, 1]
    xk = (u - Km[0, 2] - Km[0, 1] * yk) / Km[0, 0]
    dc = np.stack([xk, yk, np.ones_like(xk)], -1).reshape(-1, 3)
    norm = np.linalg.norm(dc, axis=1)
    dw = (dc / norm[:, None]) @ R                          # Rᵀ·d(行ベクトルで)
    Cw = -R.T @ t                                          # カメラの中心(世界)
    zmax_map = float(np.nanmax(Hm))
    x_lo, x_hi = o[0] + 0.5 * c, o[0] + (nx - 0.5) * c
    y_lo, y_hi = o[1] + 0.5 * c, o[1] + (ny - 0.5) * c
    t_far = mr * float(norm.max())                         # 深度 max_range の光線の長さの最大
    t0 = nr

    def surface(px, py, clamp=False):
        """双一次の高さ。足場(セルの中心が張る矩形)の外は nan(``clamp`` なら縁へ寄せて読む)。"""
        fx = (px - o[0]) / c - 0.5
        fy = (py - o[1]) / c - 0.5
        ok = (fx >= 0.0) & (fx <= nx - 1) & (fy >= 0.0) & (fy <= ny - 1)
        if clamp:
            fx, fy = np.clip(fx, 0.0, nx - 1), np.clip(fy, 0.0, ny - 1)
        j0 = np.clip(np.floor(fx).astype(np.int64), 0, nx - 2)
        i0 = np.clip(np.floor(fy).astype(np.int64), 0, ny - 2)
        wx, wy = fx - j0, fy - i0
        h = ((1 - wy) * ((1 - wx) * Hm[i0, j0] + wx * Hm[i0, j0 + 1])
             + wy * ((1 - wx) * Hm[i0 + 1, j0] + wx * Hm[i0 + 1, j0 + 1]))
        return h if clamp else np.where(ok, h, np.nan)

    def footprint_span(dwc):
        """光線が足場の矩形に入る長さ t_in と出る長さ t_out(入らなければ t_in > t_out)。"""
        t_in = np.full(len(dwc), -np.inf)
        t_out = np.full(len(dwc), np.inf)
        for ax, lo_, hi_ in ((0, x_lo, x_hi), (1, y_lo, y_hi)):
            d_ = dwc[:, ax]
            par = np.abs(d_) < HEIGHTMAP_DEPTH_RAY_PARALLEL_TOL
            with np.errstate(divide="ignore", invalid="ignore"):
                a_ = (lo_ - Cw[ax]) / d_
                b_ = (hi_ - Cw[ax]) / d_
            t_in = np.maximum(t_in, np.where(par, np.where((Cw[ax] >= lo_) & (Cw[ax] <= hi_), -np.inf, np.inf),
                                              np.minimum(a_, b_)))
            t_out = np.minimum(t_out, np.where(par, np.where((Cw[ax] >= lo_) & (Cw[ax] <= hi_), np.inf, -np.inf),
                                                np.maximum(a_, b_)))
        return t_in, t_out

    def above_at(dwc, tv):
        """長さ tv の点の「光線 − 面」(足場の縁の上で読むので縁へ寄せる)。"""
        tv = np.where(np.isfinite(tv), tv, 0.0)
        Pq = Cw[None, :] + tv[:, None] * dwc
        return Pq[:, 2] - surface(Pq[:, 0], Pq[:, 1], clamp=True)

    def march(dwc):
        """光線の束 dwc (m, 3) の、最初に面の上から下へ入る点までの長さ(当たらなければ nan)。

        刻みの間で足場の矩形に入る・出る光線は、縁の点の高さで判定する(縁の 1 刻みの内側の当たりを
        落とさない)。足場の外か穴(nan)から面の下へ入る光線は側面に当たったとして nan。"""
        m = dwc.shape[0]
        out = np.full(m, np.nan)
        t_in_all, t_out_all = footprint_span(dwc)
        a_in_all = above_at(dwc, t_in_all)
        a_out_all = above_at(dwc, t_out_all)
        active = np.arange(m)
        prev_above = np.full(m, np.nan)               # 前の刻みの「光線 − 面」(nan = 面が無い)
        prev_t = np.full(m, -np.inf)
        k = 0
        while active.size and k < n_steps:
            ks = np.arange(k, min(k + HEIGHTMAP_DEPTH_STEP_BATCH, n_steps))
            ts = t0 + ks * st
            da = dwc[active]
            na = len(active)
            P = Cw[None, None, :] + ts[None, :, None] * da[:, None, :]
            above = P[..., 2] - surface(P[..., 0], P[..., 1])     # > 0 上、<= 0 下、nan 面なし
            a_prev = np.concatenate([prev_above[active][:, None], above[:, :-1]], 1)
            t_prev = np.concatenate([prev_t[active][:, None], np.broadcast_to(ts[:-1], (na, len(ts) - 1))], 1)
            tb = np.broadcast_to(ts, (na, len(ts)))
            t_in = t_in_all[active][:, None]
            t_out = t_out_all[active][:, None]
            a_in = np.broadcast_to(a_in_all[active][:, None], above.shape)
            a_out = np.broadcast_to(a_out_all[active][:, None], above.shape)
            span = t_in <= t_out
            down = (a_prev > 0.0) & (above <= 0.0)                         # 上から下へ = 当たり
            entered = span & (t_prev < t_in) & (t_in <= tb)                # この刻みの間で足場に入った
            enter_hit = entered & np.isnan(a_prev) & (above <= 0.0) & (a_in > 0.0)
            blocked = np.isnan(a_prev) & (above <= 0.0) & ~enter_hit      # 外・穴・始点から面の下へ = 側面
            exit_hit = (span & (t_prev < t_out) & (t_out <= tb) & (a_prev > 0.0) & np.isnan(above)
                        & (a_out <= 0.0))                                  # 出る前に縁の内側で当たった
            event = down | enter_hit | blocked | exit_hit
            hit = event.any(1)
            jj = np.argmax(event, 1)
            rows = np.arange(na)
            ta, aa = t_prev[rows, jj].copy(), a_prev[rows, jj].copy()
            tb_, ab = tb[rows, jj].copy(), above[rows, jj].copy()
            e_in, e_out = enter_hit[rows, jj], exit_hit[rows, jj]
            ta[e_in], aa[e_in] = t_in[e_in, 0], a_in[e_in, 0]
            tb_[e_out], ab[e_out] = t_out[e_out, 0], a_out[e_out, 0]
            ok = hit & (down[rows, jj] | e_in | e_out)
            ta = np.where(ok, ta, tb_)                      # 当たらない行は使わない(−inf を掛けない)
            tt = ta + _crossing_fraction(np.where(ok, aa, 1.0), np.where(ok, ab, 0.0)) * (tb_ - ta)
            out[active[ok]] = tt[ok]
            # 進めない光線を止める: 当たった・塞がれた・面の最高点より上で上を向く・足場から離れていく
            last = P[:, -1, :]
            gone = (last[:, 2] > zmax_map) & (da[:, 2] >= 0.0)
            gone |= ts[-1] > t_out[:, 0]
            prev_above[active] = above[:, -1]
            prev_t[active] = ts[-1]
            active = active[~hit & ~gone]
            k += len(ks)
        return out

    n_steps = int(np.ceil((t_far - t0) / st)) + 1
    dist = np.concatenate([march(dw[a:a + HEIGHTMAP_DEPTH_RAY_BATCH])
                           for a in range(0, dw.shape[0], HEIGHTMAP_DEPTH_RAY_BATCH)])
    z = (dist / norm).reshape(Hh, W)                       # 光線の長さ → 光軸方向の深度
    z[~((z >= nr) & (z <= mr))] = np.nan
    if sd > 0.0:
        rng = np.random.default_rng(seed)
        noise = rng.standard_normal(z.shape)                # 全画素ぶん引く(当たる画素が変わっても列が揃う)
        fin = np.isfinite(z)
        z[fin] = z[fin] + noise[fin] * (z[fin] ** 2 * sd / (Km[0, 0] * bl))
    return z
