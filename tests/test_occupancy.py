"""Ground-truth tests for 2-D occupancy / free-space mapping (occupancy.py).

Grids are built from known geometry (a cloud cluster at a known place, a single
obstacle cell, a wall between two points), so occupancy, inflation, clearance,
line-of-sight and frontiers are checked against exact expected values."""
import numpy as np

import occupancy


def test_occupancy_grid_marks_cluster():
    rng = np.random.default_rng(0)
    obj = rng.uniform([1.0, 1.0, 0.2], [1.2, 1.2, 0.4], (200, 3))   # a blob at (1.1,1.1)
    occ, extent = occupancy.occupancy_grid_2d(obj, cell=0.05,
                                              bounds=(0, 2, 0, 2), z_range=(0.1, 0.5))
    assert occ.shape == (40, 40)
    # the occupied cells sit around (x,y)=(1.1,1.1) -> col/row ~ 22
    ys, xs = np.where(occ)
    assert 18 <= xs.mean() <= 26 and 18 <= ys.mean() <= 26
    assert occ.sum() < 40                       # a compact blob, not the whole grid


def test_occupancy_z_slab_filters_floor():
    # floor points at z~0 and body points at z~0.3; a body-height slab keeps only body
    floor = np.column_stack([np.linspace(0, 2, 300), np.full(300, 1.0), np.zeros(300)])
    body = np.column_stack([np.full(50, 0.5), np.full(50, 0.5),
                            np.linspace(0.2, 0.4, 50)])
    P = np.vstack([floor, body])
    occ, _ = occupancy.occupancy_grid_2d(P, cell=0.1, bounds=(0, 2, 0, 2),
                                         z_range=(0.15, 0.5))
    assert occ.sum() <= 2                        # only the single body column, not the floor line


def test_inflate_obstacles_disk():
    occ = np.zeros((21, 21), bool)
    occ[10, 10] = True
    inf = occupancy.inflate_obstacles(occ, radius_cells=3.0)
    assert inf[10, 10] and inf[10, 13] and inf[7, 10]      # within radius 3
    assert not inf[10, 14] and not inf[6, 10]              # beyond radius 3
    assert inf.sum() < np.pi * 4 ** 2                       # roughly a disk of r=3


def test_clearance_map_distance():
    occ = np.zeros((10, 10), bool)
    occ[:, 0] = True                                        # a wall down column 0
    clr = occupancy.clearance_map(occ, cell=0.1)
    assert np.isclose(clr[5, 0], 0.0)                       # on the wall
    assert np.isclose(clr[5, 3], 0.3)                       # 3 cells * 0.1 m
    assert np.isclose(clr[5, 9], 0.9)


def test_line_of_sight_clear_and_blocked():
    occ = np.zeros((20, 20), bool)
    assert occupancy.line_of_sight(occ, (2, 2), (2, 17))    # empty grid -> clear
    occ[:, 10] = True                                       # a wall at column 10
    occ[2, 2] = False; occ[2, 17] = False                   # keep endpoints free
    assert not occupancy.line_of_sight(occ, (2, 2), (2, 17))   # blocked by the wall
    assert occupancy.line_of_sight(occ, (2, 2), (2, 8))     # stops before the wall
    assert not occupancy.line_of_sight(occ, (2, 2), (2, 25))  # off-grid endpoint


def test_occupancy_drops_out_of_bounds_points():
    # points outside the given bounds must be dropped, not clamped onto edge cells
    pts = np.array([[0.5, 0.5, 0.3], [5.0, 5.0, 0.3], [-3.0, 0.5, 0.3]])   # 2 outside
    occ, _ = occupancy.occupancy_grid_2d(pts, cell=0.1, bounds=(0, 1, 0, 1))
    assert occ.sum() == 1                              # only the in-bounds point
    assert not occ[:, -1].any() and not occ[:, 0].any() and not occ[-1, :].any()


def test_clearance_and_inflate_no_obstacles():
    free = np.zeros((8, 8), bool)
    clr = occupancy.clearance_map(free, cell=0.1)
    assert np.isinf(clr).all()                         # nothing to avoid -> infinite clearance
    inf = occupancy.inflate_obstacles(free, radius_cells=3.0)
    assert not inf.any()                               # no phantom C-space obstacles


def test_line_of_sight_no_corner_cutting():
    # two obstacles touching only at a diagonal must block the diagonal line between
    # the cells they flank (standard Bresenham would tunnel through).
    occ = np.zeros((7, 7), bool)
    occ[3, 4] = True
    occ[4, 3] = True
    assert not occupancy.line_of_sight(occ, (3, 3), (4, 4))   # corner is sealed
    # but a genuinely open diagonal is still visible
    assert occupancy.line_of_sight(np.zeros((7, 7), bool), (1, 1), (5, 5))


def test_line_of_sight_is_symmetric():
    # line_of_sight must be undirected for a planner's visibility graph:
    # los(a, b) == los(b, a) for every pair of free cells. Direction-dependent
    # Bresenham stepping + corner-cut used to disagree on a grazing tie.
    repro = np.zeros((3, 3), bool)
    repro[0, 1] = True                                     # the confirmed regression case
    assert occupancy.line_of_sight(repro, (0, 0), (1, 2)) == \
        occupancy.line_of_sight(repro, (1, 2), (0, 0))
    assert not occupancy.line_of_sight(repro, (0, 0), (1, 2))   # grazing -> blocked (fail-closed)

    rng = np.random.default_rng(0)
    for _ in range(20):                                    # many random obstacle fields
        occ = rng.random((7, 7)) < 0.2
        free = np.argwhere(~occ)
        for a in free:                                     # every ordered pair of free cells
            for b in free:
                assert occupancy.line_of_sight(occ, tuple(a), tuple(b)) == \
                    occupancy.line_of_sight(occ, tuple(b), tuple(a))


def test_frontier_between_free_and_unknown():
    free = np.zeros((10, 10), bool)
    unknown = np.zeros((10, 10), bool)
    free[:, :5] = True                                      # left half mapped free
    unknown[:, 5:] = True                                   # right half unseen
    fr, clusters = occupancy.frontier_cells(free, unknown)
    assert fr[:, 4].all()                                   # the free column touching unknown
    assert not fr[:, :4].any()                              # interior free is not a frontier
    assert len(clusters) == 1 and clusters[0].shape[0] == 10


# ═══════════════════════════════════════════════════════════════════════════
# 3-D voxel occupancy + ESDF (robot planning) — ground-truth tests
# ─────────────────────────────────────────────────────────────────────────
# GT はすべて解析値: 球の符号付き距離は r-R(外+/内-/面0)、膨張は単調、スケールは
# voxel_size に比例。実装の再導出ではなく独立に計算した r-R / 解析距離で照合する。
# 許容は honest な系統誤差: ESDF はボクセル中心で測るためゼロ交差が中心の中間に落ち、
# 面セルの |ESDF| は最大 √2·vs、中盤の離散化誤差は約 1 ボクセル。
# ═══════════════════════════════════════════════════════════════════════════
import pytest

BOUNDS = ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))
RES = 40
VS = 2.0 / RES                                   # 物理ボクセル辺長 = span/res = 0.05
R_BALL = 0.5


def _voxel_center_radius(res, bounds, center=(0.0, 0.0, 0.0)):
    """各ボクセル中心の center からの距離 (res,res,res)(独立 GT 用)。"""
    lo = np.array([b[0] for b in bounds], float)
    hi = np.array([b[1] for b in bounds], float)
    span = hi - lo
    ii, jj, kk = np.mgrid[0:res, 0:res, 0:res]
    cx = lo[0] + (ii + 0.5) / res * span[0] - center[0]
    cy = lo[1] + (jj + 0.5) / res * span[1] - center[1]
    cz = lo[2] + (kk + 0.5) / res * span[2] - center[2]
    return np.sqrt(cx * cx + cy * cy + cz * cz)


def _solid_ball(res, bounds, R, center=(0.0, 0.0, 0.0)):
    """半径 R の中実球の占有格子 + 各ボクセル中心半径(解析 SDF = r-R の GT)。"""
    r = _voxel_center_radius(res, bounds, center)
    return r <= R, r


def _sphere_surface_points(n, R, center=(0.0, 0.0, 0.0), seed=0):
    v = np.random.default_rng(seed).standard_normal((n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v * R + np.asarray(center, float)


def test_occupancy_grid_marks_sphere_shell():
    """球面点群 → occupancy_grid が球殻ボクセルだけを占有(中は空)。"""
    pts = _sphere_surface_points(6000, R_BALL, seed=0)
    occ = occupancy.occupancy_grid(pts, BOUNDS, RES)
    assert occ.shape == (RES, RES, RES) and occ.dtype == bool
    assert occ.any()
    r = _voxel_center_radius(RES, BOUNDS)
    ro = r[occ]
    # 占有ボクセル中心は半径 R の薄い殻に乗る(量子化ぶん ±2·vs 以内)
    assert ro.min() > R_BALL - 2 * VS and ro.max() < R_BALL + 2 * VS
    # 殻の内側(中心)と外側(角)は自由
    c = RES // 2
    assert not occ[c, c, c]
    assert not occ[0, 0, 0]


def test_occupancy_grid_drops_out_of_bounds():
    """bounds 外の点は落とす(端セルへ clamp して幻の障害物を作らない)。"""
    pts = np.array([[0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [-9.0, 0.0, 0.0]])   # 2 個は外
    occ = occupancy.occupancy_grid(pts, BOUNDS, RES)
    assert occ.sum() == 1
    c = RES // 2
    assert occ[c, c, c]                          # 原点の 1 点だけ


def test_esdf_sign_and_surface():
    """ESDF: 面近傍≈0、外は正、内は負、解析 r-R に一致(離散化 ~1 voxel)。"""
    occ, r = _solid_ball(RES, BOUNDS, R_BALL)
    E = occupancy.esdf(occ, voxel_size=VS)
    analytic = r - R_BALL
    # 面バンド |r-R|<vs: |ESDF| は最大 √2·vs(中心の中間にゼロ交差) → << R で「≈0」
    band = np.abs(analytic) < VS
    assert np.abs(E[band]).max() <= 1.6 * VS
    # 明確に内/外のセルは符号が確定
    assert E[r < R_BALL - 3 * VS].max() < 0.0
    assert E[r > R_BALL + 3 * VS].min() > 0.0
    # 中盤(グリッド端の切詰めを避ける)で解析距離に一致
    mid = np.abs(analytic) < 0.35
    assert np.abs(E[mid] - analytic[mid]).max() <= 1.5 * VS


def test_esdf_monotonic_increasing_outward():
    """中心から外向きの ray で ESDF は単調増加しゼロを跨ぐ(内負→外正)。"""
    occ, _ = _solid_ball(RES, BOUNDS, R_BALL)
    E = occupancy.esdf(occ, voxel_size=VS)
    c = RES // 2
    ray = E[c:c + 18, c, c]
    assert np.all(np.diff(ray) > 0)              # 厳密単調増加
    assert ray[0] < 0 < ray[-1]                  # 内(負)から外(正)へ


def test_esdf_empty_and_full_are_honest():
    """全自由=+inf(最近占有なし)、全占有=-inf(最近自由なし)— 詐称せず honest。"""
    free = np.zeros((8, 8, 8), bool)
    full = np.ones((8, 8, 8), bool)
    assert np.isposinf(occupancy.esdf(free)).all()
    assert np.isneginf(occupancy.esdf(full)).all()


def test_esdf_scales_exactly_with_voxel_size():
    """voxel_size を 2 倍 → ESDF はちょうど 2 倍(絶対 epsilon なし=スケール整合)。"""
    occ = occupancy.occupancy_grid(
        np.random.default_rng(1).standard_normal((3000, 3)) * 0.3, BOUNDS, RES)
    E1 = occupancy.esdf(occ, voxel_size=1.0)
    E2 = occupancy.esdf(occ, voxel_size=2.0)
    fin = np.isfinite(E1) & np.isfinite(E2)
    assert np.abs(E2[fin] - 2.0 * E1[fin]).max() < 1e-9


def test_inflate_monotonic_and_nested():
    """inflate: radius 増で占有数が単調増、各半径は入れ子集合、r=0 は恒等。"""
    occ = np.zeros((21, 21, 21), bool)
    occ[10, 10, 10] = True
    grids = {r: occupancy.inflate(occ, r, voxel_size=1.0) for r in (0, 1, 2, 3, 4)}
    counts = [int(grids[r].sum()) for r in (0, 1, 2, 3, 4)]
    assert counts == sorted(counts) and counts[0] == 1 and counts[-1] > counts[0]
    for a, b in ((1, 2), (2, 3), (3, 4)):
        assert np.all(grids[b] >= grids[a])      # 大半径は小半径の上位集合
    assert np.array_equal(grids[0], occ)         # 膨張なし
    # radius が ESDF<=radius を捕らえる: 中心から距離2の軸セルは r>=2 で占有
    assert grids[2][10, 12, 10] and not grids[1][10, 12, 10]


def test_inflate_respects_voxel_size():
    """同じ world radius でも voxel_size が小さいほど voxel 数で厚く膨張(スケール整合)。"""
    occ = np.zeros((21, 21, 21), bool)
    occ[10, 10, 10] = True
    fine = occupancy.inflate(occ, radius=2.0, voxel_size=1.0)    # 2 voxel 膨張
    coarse = occupancy.inflate(occ, radius=2.0, voxel_size=2.0)  # 1 voxel 膨張
    assert int(fine.sum()) > int(coarse.sum())


def test_query_distance_matches_analytic():
    """既知座標での query_distance が解析距離 r-R に一致(三線形補間, ~1 voxel)。"""
    occ, _ = _solid_ball(RES, BOUNDS, R_BALL)
    E = occupancy.esdf(occ, voxel_size=VS)
    q = np.array([[0.9, 0.0, 0.0], [0.7, 0.0, 0.0],
                  [0.1, 0.0, 0.0], [0.0, 0.0, 0.0]])
    expect = np.linalg.norm(q, axis=1) - R_BALL   # 解析 SDF
    got = occupancy.query_distance(E, BOUNDS, RES, q)
    assert np.abs(got - expect).max() <= 1.5 * VS
    # 外の点は正、内の点は負(符号一致)
    assert got[0] > 0 and got[1] > 0 and got[2] < 0 and got[3] < 0


def test_query_distance_nearest_matches_grid():
    """mode='nearest' はそのボクセルの ESDF 値を返す(補間なし)。"""
    occ, _ = _solid_ball(RES, BOUNDS, R_BALL)
    E = occupancy.esdf(occ, voxel_size=VS)
    lo = np.array([-1.0, -1.0, -1.0])
    span = np.array([2.0, 2.0, 2.0])
    idx = np.array([[12, 25, 30], [20, 20, 20], [5, 33, 18]])
    centers = lo + (idx + 0.5) / RES * span       # ボクセル中心の world 座標
    got = occupancy.query_distance(E, BOUNDS, RES, centers, mode="nearest")
    exp = E[idx[:, 0], idx[:, 1], idx[:, 2]]
    assert np.allclose(got, exp)


def test_query_distance_scale_consistency():
    """幾何をスケールしても ESDF/クエリは voxel_size 比で整合(2 スケール検証)。"""
    # スケール1: 半径0.5 @ bounds(-1,1)  / スケール2: 半径1.0 @ bounds(-2,2)(全2倍)
    b1 = ((-1.0, 1.0),) * 3
    b2 = ((-2.0, 2.0),) * 3
    occ1, _ = _solid_ball(RES, b1, 0.5)
    occ2, _ = _solid_ball(RES, b2, 1.0)
    E1 = occupancy.esdf(occ1, voxel_size=2.0 / RES)
    E2 = occupancy.esdf(occ2, voxel_size=4.0 / RES)
    d1 = occupancy.query_distance(E1, b1, RES, np.array([[0.9, 0.0, 0.0]]))[0]
    d2 = occupancy.query_distance(E2, b2, RES, np.array([[1.8, 0.0, 0.0]]))[0]
    assert abs(d2 - 2.0 * d1) <= 2.0 * (2.0 / RES)   # スケール2倍 ⇒ 距離2倍


def test_3d_fail_closed_on_degenerate_input():
    """退化入力は fail-closed(ValueError): res<=0 / 退化bounds / vs<=0 / radius<0 / 形状不正。"""
    pts = np.zeros((3, 3))
    with pytest.raises(ValueError):
        occupancy.occupancy_grid(pts, BOUNDS, 0)                       # res<=0
    with pytest.raises(ValueError):
        occupancy.occupancy_grid(pts, ((0, 0), (0, 1), (0, 1)), RES)   # 退化 bounds
    with pytest.raises(ValueError):
        occupancy.occupancy_grid(np.zeros((4, 2)), BOUNDS, RES)        # (N,3) でない
    with pytest.raises(ValueError):
        occupancy.esdf(np.zeros((4, 4, 4), bool), voxel_size=0.0)      # vs<=0
    with pytest.raises(ValueError):
        occupancy.inflate(np.zeros((4, 4, 4), bool), radius=-1.0)      # radius<0
    E = np.zeros((RES, RES, RES))
    with pytest.raises(ValueError):
        occupancy.query_distance(E, BOUNDS, RES, np.zeros((2, 2)))     # query 形状不正
    with pytest.raises(ValueError):
        occupancy.query_distance(E, BOUNDS, RES, np.zeros((1, 3)), mode="foo")  # 不明 mode


def test_occupancy_grid_2d_rejects_degenerate_bounds():
    """2-D occupancy_grid_2d: 明示された退化/反転 bounds は fail-closed(3-D と一貫)。"""
    pt = [[0.5, 0.5, 0.3]]
    with pytest.raises(ValueError):
        occupancy.occupancy_grid_2d(pt, cell=0.1, bounds=(1.0, 0.0, 0.0, 1.0))  # xmax<xmin
    with pytest.raises(ValueError):
        occupancy.occupancy_grid_2d(pt, cell=0.1, bounds=(0.0, 1.0, 1.0, 0.0))  # ymax<ymin
    with pytest.raises(ValueError):
        occupancy.occupancy_grid_2d(pt, cell=0.1, bounds=(0.0, 0.0, 0.0, 1.0))  # xmax==xmin
    # 正常な bounds は不変(単一 in-bounds 点が占有)
    occ, extent = occupancy.occupancy_grid_2d(pt, cell=0.1, bounds=(0, 1, 0, 1))
    assert occ.sum() == 1 and extent == (0, 1, 0, 1)


def test_inflate_validates_voxel_size_before_shortcut():
    """inflate: radius==0 / 空占有の短絡パスでも voxel_size<=0 は ValueError(短絡前に検証)。"""
    full = np.ones((3, 3, 3), bool)
    empty = np.zeros((3, 3, 3), bool)
    with pytest.raises(ValueError):
        occupancy.inflate(full, radius=0, voxel_size=0)          # radius==0 短絡でも検証
    with pytest.raises(ValueError):
        occupancy.inflate(empty, radius=5, voxel_size=-3)        # 空占有短絡でも検証
    with pytest.raises(ValueError):
        occupancy.inflate(full, radius=0, voxel_size=(1.0, -1.0, 1.0))  # 異方の負成分も
    # 正常な短絡は恒等のまま(回帰なし)
    assert np.array_equal(occupancy.inflate(full, radius=0, voxel_size=1.0), full)
    assert np.array_equal(occupancy.inflate(empty, radius=5, voxel_size=1.0), empty)
