"""離散幾何と位相の古典の門(2026-10-03、陣 4)。定理で立てる: Euler の公式・Descartes(離散 Gauss–Bonnet)・
Delaunay の三角形の数 2n−h−2 と空円性・熱法の測地距離が大円距離へ収束(辺の Dijkstra は収束しない)。"""
import math
import warnings

import numpy as np
import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import fullseye as fs
    import geodesic3d
    import mathgeometry as G
    import opsmath

LEDGER = ["mesh_euler_characteristic", "angle_defect", "delaunay_triangulate", "geodesic_heat", "geodesic_heat_grid",
          "mesh_torus", "nurbs_curve", "nurbs_circle", "nurbs_surface", "nurbs_revolve"]


def test_public_and_ledger():
    assert opsmath.missing() == []
    assert sorted(opsmath.list_ops("geometry")) == sorted(LEDGER)
    assert sorted(G.__all__) == sorted(LEDGER)
    for n in LEDGER:
        assert callable(getattr(fs, n)) and n in fs.__all__ and callable(getattr(fs.ledger, n)), n


@pytest.mark.parametrize("freq", [1, 2, 5])
def test_sphere_has_chi_two_and_total_angle_defect_four_pi(freq):
    V, F = fs.ledger.geodesic_dome(freq)
    e = G.mesh_euler_characteristic(V, F)
    assert e["chi"] == 2 and e["genus"] == 0 and e["closed"]
    assert abs(G.angle_defect(V, F)["total"] - 4 * math.pi) < 1e-10


def test_torus_has_genus_one_and_zero_total_curvature_even_when_jittered():
    V, F = G.mesh_torus(2.0, 0.7, 24, 12)
    e = G.mesh_euler_characteristic(V, F)
    assert e["chi"] == 0 and e["genus"] == 1
    for jitter in (0.0, 0.05):
        Vj = V + jitter * np.random.default_rng(0).normal(size=V.shape)
        d = G.angle_defect(Vj, F)
        assert abs(d["total"]) < 1e-10
    d = G.angle_defect(V, F)["defect"].reshape(24, 12)
    assert d[:, 0].min() > 0 and d[:, 6].max() < 0                 # 外側(v=0)は凸で正、内側(v=π)は鞍で負


def test_disc_with_boundary_obeys_gauss_bonnet_with_the_boundary_term():
    V, F = fs.ledger.geodesic_dome(4, hemisphere=True) if "hemisphere" in fs.ledger.geodesic_dome.__code__.co_varnames \
        else fs.ledger.geodesic_dome(4)
    e = G.mesh_euler_characteristic(V, F)
    d = G.angle_defect(V, F)
    assert abs(d["total"] - 2 * math.pi * e["chi"]) < 1e-10


def test_delaunay_count_and_empty_circles():
    rng = np.random.default_rng(1)
    for n in (10, 60, 300):
        P = rng.random((n, 2))
        d = G.delaunay_triangulate(P)
        assert d["n_triangles"] == 2 * n - len(d["hull"]) - 2
        assert len(d["circumcenters"]) == d["n_triangles"] > 0          # 空の列で下の表明が空振りしない
        for c, r in zip(d["circumcenters"], d["circumradii"]):
            assert np.sum(np.linalg.norm(P - c, axis=1) < r - 1e-9) == 0
    with pytest.raises(ValueError):
        G.delaunay_triangulate(np.c_[np.arange(5.0), np.arange(5.0)])         # 一直線
    with pytest.raises(ValueError):
        G.delaunay_triangulate([[0, 0], [1, 0], [0, 1], [0, 0]])


def test_heat_method_converges_to_great_circle_distance_while_edge_dijkstra_does_not():
    errs_h, errs_d = [], []
    for freq in (4, 8, 16):
        V, F = fs.ledger.geodesic_dome(freq)
        V = V / np.linalg.norm(V, axis=1, keepdims=True)
        true = np.arccos(np.clip(V @ V[0], -1, 1))
        errs_h.append(np.abs(G.geodesic_heat(V, F, 0)["distance"] - true).mean())
        errs_d.append(np.abs(geodesic3d.geodesic_mesh(V, F, 0) - true).mean())
    assert errs_h[0] > errs_h[1] > errs_h[2] and errs_h[2] < 0.02
    assert errs_d[2] > 0.5 * errs_d[0] and errs_d[2] > 3 * errs_h[2]          # Dijkstra は辺の向きの誤差が残る


def test_euler_rejects_bad_meshes():
    with pytest.raises(ValueError):
        G.mesh_euler_characteristic(np.zeros((4, 3)), [[0, 1, 9]])
    with pytest.raises(ValueError):
        G.mesh_torus(1.0, 2.0)


def test_delaunay_3d_has_empty_circumspheres_and_euler_one():
    import itertools
    P = np.random.default_rng(2).random((150, 3))
    d = G.delaunay_triangulate(P)
    assert d["dim"] == 3
    assert len(d["circumcenters"]) == len(d["simplices"]) > 0
    for c, r in zip(d["circumcenters"], d["circumradii"]):
        assert np.sum(np.linalg.norm(P - c, axis=1) < r - 1e-9) == 0
    E, Fc = set(), set()
    for t in d["simplices"]:
        E.update(itertools.combinations(sorted(t), 2))
        Fc.update(itertools.combinations(sorted(t), 3))
    assert len(P) - len(E) + len(Fc) - d["n_simplices"] == 1          # 凸な塊は球と同じ位相


def _dijkstra8(M, src, sp):
    from scipy.sparse import coo_matrix, csgraph
    n0, n1 = M.shape
    idx = -np.ones(M.shape, int)
    idx[M] = np.arange(M.sum())
    R, C, W = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        y0, y1 = 0, n0 - dy
        x0, x1 = max(0, -dx), n1 - max(0, dx)
        a = idx[y0:y1, x0:x1]
        b = idx[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        ok = (a >= 0) & (b >= 0)
        R.append(a[ok])
        C.append(b[ok])
        W.append(np.full(ok.sum(), math.hypot(dy, dx) * sp))
    A = coo_matrix((np.concatenate(W), (np.concatenate(R), np.concatenate(C))), shape=(M.sum(),) * 2)
    out = np.full(M.shape, np.inf)
    out[M] = csgraph.dijkstra(A, directed=False, indices=idx[src])
    return out


def test_grid_heat_converges_to_euclidean_while_grid_dijkstra_keeps_its_direction_error():
    eh, ed = [], []
    for n in (41, 81, 161):
        M = np.ones((n, n), bool)
        c = (n // 2, n // 2)
        sp = 2.0 / (n - 1)
        yy, xx = np.indices(M.shape)
        true = np.hypot(yy - c[0], xx - c[1]) * sp
        eh.append(np.abs(G.geodesic_heat_grid(M, c, spacing=sp)["distance"] - true).max())
        ed.append(np.abs(_dijkstra8(M, c, sp) - true).max())
    assert eh[0] > eh[1] > eh[2] and eh[2] < 0.01 and 1.7 < eh[0] / eh[1] < 2.3
    assert ed[2] > 0.9 * ed[0] and ed[2] > 5 * eh[2]                 # 8 近傍は 22.5° 方向で 8% の誤差が消えない


def test_grid_heat_goes_around_an_obstacle():
    n = 121
    sp = 1.0 / (n - 1)
    M = np.ones((n, n), bool)
    M[60, :] = False
    M[60, 90:96] = True                                             # 壁にすき間
    src = (20, 30)
    D = G.geodesic_heat_grid(M, src, spacing=sp)["distance"]

    def exact(p):
        best = min(math.hypot(60 - src[0], gx - src[1]) + math.hypot(p[0] - 60, p[1] - gx) for gx in np.linspace(90, 95, 51))
        return best * sp
    for p in ((100, 10), (100, 60), (110, 100), (119, 119)):
        assert abs(D[p] - exact(p)) < 0.015 * exact(p), p
    assert np.isinf(D[60, 0])                                       # 壁の中は inf


def test_grid_heat_in_a_3d_volume():
    n = 33
    M = np.ones((n, n, n), bool)
    c = (16, 16, 16)
    sp = 2.0 / (n - 1)
    D = G.geodesic_heat_grid(M, c, spacing=sp)["distance"]
    zz, yy, xx = np.indices(M.shape)
    true = np.sqrt((zz - c[0]) ** 2 + (yy - c[1]) ** 2 + (xx - c[2]) ** 2) * sp
    assert np.abs(D - true).max() < 0.06
    with pytest.raises(ValueError):
        G.geodesic_heat_grid(M, (0, 0))


# ── NURBS: 重みつきで制御点を通らない本物(旧 gen_contour_nurbs_xld は補間 B スプラインだった) ─────── #
def test_nurbs_unit_weights_equal_scipy_bspline():
    """重みが全部 1 なら NURBS は普通の B スプライン —— scipy の独立実装と丸め誤差で一致し、基底の和は 1。"""
    from scipy.interpolate import BSpline
    P = np.random.default_rng(0).random((7, 2))
    r = G.nurbs_curve(P, degree=3, n=101)
    ref = BSpline(r["knots"], P, 3)(r["u"])
    assert np.abs(r["points"] - ref).max() < 1e-12
    assert np.abs(r["basis"].sum(axis=1) - 1).max() < 1e-12
    assert np.allclose(r["points"][[0, -1]], P[[0, -1]])          # clamped: 端点だけは通る


def test_nurbs_circle_is_exact_and_misses_corner_points():
    """9 点の 2 次 NURBS は円そのもの(多項式では不可能)。隅の制御点は円の外 (√2−1)R にあって曲線は通らない。"""
    from scipy.spatial import cKDTree
    c = G.nurbs_circle(2.0, (1.0, -1.0))
    q = G.nurbs_curve(c["control_points"], c["weights"], degree=2, knots=c["knots"], n=2001)
    d = np.linalg.norm(q["points"] - [1.0, -1.0], axis=1)
    assert np.abs(d - 2.0).max() < 1e-13
    gap = cKDTree(q["points"]).query(c["control_points"][1])[0]
    assert abs(gap - (math.sqrt(2) - 1) * 2.0) < 1e-6
    # 重みを 1 にすると円でなくなる(重みが要る理由)
    q1 = G.nurbs_curve(c["control_points"], None, degree=2, knots=c["knots"], n=2001)
    assert np.abs(np.linalg.norm(q1["points"] - [1.0, -1.0], axis=1) - 2.0).max() > 0.05


def test_nurbs_commutes_with_projective_maps():
    """NURBS は射影変換と可換: 同次座標の制御点を変換してから描く = 描いてから変換する(B スプラインは不可)。"""
    c = G.nurbs_circle(1.0)
    H = np.array([[1.1, 0.2, 0.3], [-0.1, 0.9, 0.5], [0.05, -0.08, 1.0]])
    q = G.nurbs_curve(c["control_points"], c["weights"], degree=2, knots=c["knots"], n=501)
    Pw = np.column_stack([c["control_points"] * c["weights"][:, None], c["weights"]]) @ H.T
    q2 = G.nurbs_curve(Pw[:, :2] / Pw[:, 2:], Pw[:, 2], degree=2, knots=c["knots"], n=501)
    h = np.column_stack([q["points"], np.ones(501)]) @ H.T
    assert np.abs(q2["points"] - h[:, :2] / h[:, 2:]).max() < 1e-12


def test_nurbs_weight_pulls_curve_toward_its_point():
    """重みを上げるほど曲線はその制御点に寄る(単調)。∞ の極限で点を通る。"""
    P = np.array([[0, 0], [1, 2], [2, -1], [3, 3], [4, 0], [5, 1]], float)
    gaps = []
    for wt in (0.25, 1.0, 4.0, 64.0):
        w = np.ones(6)
        w[3] = wt
        pts = G.nurbs_curve(P, w, degree=3, n=4001)["points"]
        gaps.append(np.linalg.norm(pts - P[3], axis=1).min())
    assert all(a > b for a, b in zip(gaps, gaps[1:])), gaps
    assert gaps[-1] < 0.05 * gaps[1]


def test_nurbs_revolve_gives_exact_sphere_and_torus():
    """断面が厳密な円弧なら回転面も厳密: 球の半径・トーラスの管の半径が丸め誤差で一定。メッシュは閉じた曲面の位相。"""
    h = 1 / math.sqrt(2)
    prof = np.array([[0, -1], [1, -1], [1, 0], [1, 1], [0, 1]], float) * 3.0
    s = G.nurbs_revolve(prof, [1, h, 1, h, 1], degree=2, knots=[0, 0, 0, .5, .5, 1, 1, 1], n=(40, 30))
    assert np.abs(np.linalg.norm(s["points"], axis=2) - 3.0).max() < 1e-12
    cc = G.nurbs_circle(0.7, (2.0, 0.0))
    t = G.nurbs_revolve(cc["control_points"], cc["weights"], degree=2, knots=cc["knots"], n=(40, 30))
    X = t["points"]
    assert np.abs(np.hypot(np.hypot(X[..., 0], X[..., 1]) - 2.0, X[..., 2]) - 0.7).max() < 1e-12
    V, F = t["mesh"]
    assert V.shape == (40 * 30, 3) and F.shape == (2 * 39 * 29, 3)


def test_nurbs_rejects_bad_input():
    with pytest.raises(ValueError):
        G.nurbs_curve(np.zeros((3, 2)), degree=3)                 # 次数が高すぎ
    with pytest.raises(ValueError):
        G.nurbs_curve(np.random.rand(5, 2), [1, 1, -1, 1, 1])     # 負の重み
    with pytest.raises(ValueError):
        G.nurbs_curve(np.random.rand(5, 2), knots=[0, 0, 0, 1, 1])  # 節点の数
    with pytest.raises(ValueError):
        G.nurbs_revolve(np.array([[-1.0, 0], [1, 1]]), degree=1)   # 軸の反対側


def test_old_nurbs_names_warn_they_are_interpolating_bsplines():
    """旧 2 本は非推奨: 呼ぶと警告し、docstring が「本当は補間 B スプライン」と言う。"""
    import contours_xld2
    for f in (contours_xld2.gen_contour_nurbs_xld, contours_xld2.gen_nurbs_interp):
        assert "補間 B スプライン" in f.__doc__ and "nurbs_curve" in f.__doc__
        with pytest.warns(DeprecationWarning):
            f(np.array([[10, 10], [40, 80], [90, 30], [120, 100]], float), 3, 20)
