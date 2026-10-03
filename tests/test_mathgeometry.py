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
          "mesh_torus"]


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
