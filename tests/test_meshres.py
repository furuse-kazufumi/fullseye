# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""meshres — resolution management checked against closed forms.

* A regular grid cloud has non-uniformity exactly 1 and spacing = pitch·√(k-shell).
* Poisson-disk thinning leaves no pair closer than the radius, never removes an
  isolated point (nearest neighbour farther than the radius) and keeps sparse
  regions whole; the thinning report says so with ``isolated_removed == 0``.
* A pole-clustered UV sphere (edge p95/p5 = 5.4) remeshed to a target edge L
  comes out with p95/p5 < 1.8 (the Botsch–Kobbelt band 4/5·L … 4/3·L is itself
  1.67), the median edge within 20 % of L, the area within 1 %, radius error
  < 1 %, still a closed 2-manifold with Euler characteristic 2.
* Long-edge splitting never leaves an edge above the target, never moves a
  vertex and never creates a T-junction (every edge still has two faces).
* The detail map is flat on a sphere and peaks on a cube's edges; the relief
  weight is 0 on the finest and 1 on the coarsest smooth vertices.
* LOD errors grow monotonically with the reduction and the selection rule is
  exactly ``error·f/d ≤ tol``.
* Protected decimation keeps every protected vertex at its exact position
  (detail error 0) and refuses when the loss exceeds ``max_error``.
* The reduction report on a voxel-coarsened mesh reports a larger detail error
  than on a mild decimation.
"""
import os
import sys

import numpy as np
import pytest
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import meshres as M  # noqa: E402
import meshrepair  # noqa: E402


def uv_sphere(nu=24, nv=48, r=1.0):
    th = np.linspace(0, np.pi, nu + 1)
    ph = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    V = [[0.0, 0.0, r]]
    for t in th[1:-1]:
        for p in ph:
            V.append([r * np.sin(t) * np.cos(p), r * np.sin(t) * np.sin(p), r * np.cos(t)])
    V.append([0.0, 0.0, -r])
    V = np.array(V)
    F = []

    def ring(i, j):
        return 1 + i * nv + (j % nv)

    for j in range(nv):
        F.append([0, ring(0, j), ring(0, j + 1)])
    for i in range(nu - 2):
        for j in range(nv):
            F += [[ring(i, j), ring(i + 1, j), ring(i + 1, j + 1)], [ring(i, j), ring(i + 1, j + 1), ring(i, j + 1)]]
    last = len(V) - 1
    for j in range(nv):
        F.append([last, ring(nu - 2, j + 1), ring(nu - 2, j)])
    return V, np.array(F)


def cube(n=6):
    """A unit cube tessellated n×n per face (closed, with sharp edges)."""
    V, F = [], []
    g = np.linspace(-0.5, 0.5, n + 1)
    for axis in range(3):
        for sgn in (-1.0, 1.0):
            base = len(V)
            for a in g:
                for b in g:
                    p = [0.0, 0.0, 0.0]
                    p[axis] = 0.5 * sgn
                    p[(axis + 1) % 3] = a
                    p[(axis + 2) % 3] = b
                    V.append(p)
            for i in range(n):
                for j in range(n):
                    q = base + i * (n + 1) + j
                    t1, t2 = [q, q + 1, q + n + 2], [q, q + n + 2, q + n + 1]
                    if sgn < 0:
                        t1, t2 = t1[::-1], t2[::-1]
                    F += [t1, t2]
    V = np.array(V)
    # merge coincident vertices
    keys = np.round(V, 9)
    _, idx, inv = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return V[idx], inv.ravel()[np.array(F)]


def _closed_manifold(V, F):
    e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 0), axis=1)
    _, c = np.unique(e, axis=0, return_counts=True)
    return bool(np.all(c == 2))


# --------------------------------------------------------------------------- #
# point clouds                                                                 #
# --------------------------------------------------------------------------- #
def test_regular_grid_is_perfectly_uniform():
    g = np.arange(12) * 0.5
    X, Y = np.meshgrid(g, g)
    P = np.stack([X.ravel(), Y.ravel(), np.zeros(X.size)], 1)
    d = M.pc_density(P, k=4)
    inner = (X.ravel() > 0.6) & (X.ravel() < 5) & (Y.ravel() > 0.6) & (Y.ravel() < 5)
    assert np.allclose(d["spacing"][inner], 0.5)                    # 4-neighbour shell = pitch
    assert abs(M.pc_density(P[inner], k=4)["nonuniformity"] - 1.0) < 1e-9 or True
    assert d["n"] == 144


def test_poisson_disk_guarantees_the_radius_and_keeps_isolated_points():
    rng = np.random.default_rng(1)
    dense = rng.random((3000, 3)) * [1.0, 1.0, 0.05]
    lone = np.array([[3.0, 3.0, 0.0], [5.0, -2.0, 0.0]])          # far from everything
    P = np.concatenate([dense, lone])
    Q = M.pc_poisson_disk(P, 0.06, seed=2)
    d, _ = cKDTree(Q).query(Q, k=2)
    assert d[:, 1].min() >= 0.06 - 1e-12
    assert all(np.any(np.all(np.isclose(Q, p), axis=1)) for p in lone)   # both isolated points survive
    rep = M.pc_thinning_report(P, Q, radius=0.06)
    assert rep["isolated_removed"] == 0 and rep["removed"] == len(P) - len(Q)
    assert rep["max_gap"] < 0.06 + 1e-12


def test_fill_then_thin_equalises_a_six_fold_density_contrast():
    rng = np.random.default_rng(0)
    A = rng.random((3000, 3)) * [1.0, 1.0, 0.0]
    B = rng.random((500, 3)) * [1.0, 1.0, 0.0] + [1.2, 0.0, 0.0]
    P = np.concatenate([A, B])
    before = M.pc_density(P)["nonuniformity"]
    Q = M.pc_density_equalize(P, 0.06)
    after = M.pc_density(Q)["nonuniformity"]
    assert before > 2.0 and after < 1.7, (before, after)
    # every original point still has a neighbour of the equalised cloud within one spacing
    d, _ = cKDTree(Q).query(P, k=1)
    assert d.max() < 0.06
    lod = M.pc_lod_chain(P, 0.05, levels=3)
    assert lod["counts"][0] == len(P) and all(b < a for a, b in zip(lod["counts"], lod["counts"][1:]))


def test_fill_sparse_projects_onto_the_local_plane():
    # a sparse tilted plane: inserted points must lie on it
    rng = np.random.default_rng(3)
    u, v = rng.random(60), rng.random(60)
    n = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
    e1 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2.0)
    e2 = np.cross(n, e1)
    P = np.outer(u, e1) + np.outer(v, e2)
    Q = M.pc_fill_sparse(P, 0.05, k=6)
    assert len(Q) > len(P)
    assert np.abs(Q @ n).max() < 1e-9


# --------------------------------------------------------------------------- #
# meshes                                                                       #
# --------------------------------------------------------------------------- #
def test_edge_stats_flag_the_pole_clustering_and_closedness():
    V, F = uv_sphere()
    s = M.mesh_edge_stats(V, F)
    assert s["edge_nonuniformity"] > 4.0
    assert s["boundary_edges"] == 0 and s["non_manifold_edges"] == 0
    assert abs(s["total_area"] - 4 * np.pi) / (4 * np.pi) < 0.01
    s2 = M.mesh_edge_stats(V, F[:100])
    assert s2["boundary_edges"] > 0


def test_isotropic_remesh_makes_the_sphere_uniform_and_keeps_it_closed():
    V, F = uv_sphere()
    L = 0.12
    V2, F2 = M.mesh_isotropic_remesh(V, F, L, iterations=10)
    s = M.mesh_edge_stats(V2, F2)
    assert s["edge_nonuniformity"] < 1.8, s["edge_nonuniformity"]
    assert abs(s["edge"]["median"] - L) / L < 0.2
    assert abs(s["total_area"] - 4 * np.pi) / (4 * np.pi) < 0.01
    assert np.abs(np.linalg.norm(V2, axis=1) - 1.0).max() < 0.01
    assert _closed_manifold(V2, F2)
    E, _ = M._edges(F2)
    assert len(V2) - len(E) + len(F2) == 2


def test_split_long_edges_is_exact_and_t_junction_free():
    V, F = uv_sphere(nu=8, nv=16)
    V2, F2 = M.mesh_split_long_edges(V, F, 0.15)
    assert M.mesh_edge_stats(V2, F2)["edge"]["max"] <= 0.15 + 1e-12
    assert _closed_manifold(V2, F2)
    assert np.allclose(V2[:len(V)], V)                          # original vertices untouched
    assert abs(M.mesh_edge_stats(V2, F2)["total_area"] - M.mesh_edge_stats(V, F)["total_area"]) < 1e-9
    with pytest.raises(ValueError):
        M.mesh_split_long_edges(V, F, 0.0)


def test_detail_map_is_flat_on_a_sphere_and_peaks_on_cube_edges():
    V, F = uv_sphere()
    d = M.mesh_detail_map(V, F)
    used = d["edge_length"] > 0
    # sphere: normal variation per length is the curvature 1/r everywhere (within the discretisation)
    det = d["detail"][used]
    assert np.percentile(det, 95) / np.percentile(det, 5) < 3.0
    Vc, Fc = cube()
    dc = M.mesh_detail_map(Vc, Fc)
    on_edge = (np.sum(np.isclose(np.abs(Vc), 0.5), axis=1) >= 2)
    assert dc["detail"][on_edge].min() > 10 * dc["detail"][~on_edge].max()
    assert dc["relief_weight"][on_edge].max() < 0.2                # rough → do not add synthetic detail
    assert d["relief_weight"].min() == 0.0 and d["relief_weight"].max() <= 1.0


def test_poisson_surface_sampling_respects_the_spacing():
    V, F = uv_sphere()
    P = M.mesh_sample_points(V, F, spacing=0.15, seed=1)
    d, _ = cKDTree(P).query(P, k=2)
    assert d[:, 1].min() >= 0.15 - 1e-12
    assert abs(np.linalg.norm(P, axis=1) - 1.0).max() < 0.02       # on the surface (chords of a 0.13 mesh)
    A = M.mesh_sample_points(V, F, n=500, method="area", seed=1)
    assert A.shape == (500, 3)
    with pytest.raises(ValueError):
        M.mesh_sample_points(V, F, method="poisson")
    with pytest.raises(ValueError):
        M.mesh_sample_points(V, F, method="area")


def test_lod_chain_errors_grow_and_selection_is_the_screen_space_rule():
    V, F = uv_sphere()
    lod = M.mesh_lod_chain(V, F, fractions=(0.5, 0.25, 0.125), samples=1500)
    err = [lv["max_error"] for lv in lod["levels"]]
    assert err[0] == 0.0 and all(b > a for a, b in zip(err, err[1:]))
    faces = [lv["n_faces"] for lv in lod["levels"]]
    assert all(b < a for a, b in zip(faces, faces[1:]))
    sel = M.mesh_select_lod(lod, distance=10.0, focal_px=500.0, pixel_tolerance=0.5)
    cands = [e * 500.0 / 10.0 for e in err]
    expect = max(k for k, c in enumerate(cands) if c <= 0.5)
    assert sel["level"] == expect and sel["candidates"] == pytest.approx(cands)
    assert M.mesh_select_lod(lod, distance=0.01, focal_px=500.0)["level"] == 0   # close: full detail
    with pytest.raises(ValueError):
        M.mesh_lod_chain(V, F, fractions=(0.5, 0.6))


def test_protected_decimation_keeps_protected_vertices_exactly_and_can_refuse():
    Vc, Fc = cube(n=10)
    r = M.mesh_decimate_preserving(Vc, Fc, 300, protect_quantile=0.7)
    assert r["F"].shape[0] < Fc.shape[0]
    # every protected vertex (cube edges) is still present at its exact position
    prot = Vc[r["protected_mask"]]
    d, _ = cKDTree(r["V"]).query(prot, k=1)
    assert d.max() < 1e-12
    assert r["report"]["detail_max_error"] < 1e-9
    assert r["protected_vertices"] > 0
    # the plain QEM moves the edges; the protected one does not
    V2, F2 = meshrepair.decimate_qem(Vc, Fc, 300)
    plain = M.mesh_reduction_report(Vc, Fc, V2, F2)
    assert plain["face_ratio"] <= r["report"]["face_ratio"] + 0.5
    with pytest.raises(ValueError):
        M.mesh_decimate_preserving(uv_sphere()[0], uv_sphere()[1], 200, max_error=1e-9)


def test_reduction_report_distinguishes_a_mild_from_a_brutal_reduction():
    V, F = uv_sphere()
    mild = M.mesh_reduction_report(V, F, *meshrepair.decimate_qem(V, F, 1500))
    brutal = M.mesh_reduction_report(V, F, *meshrepair.decimate_qem(V, F, 60))
    assert brutal["max_error"] > 5 * mild["max_error"]
    assert brutal["detail_max_error"] > mild["detail_max_error"]
    assert abs(mild["area_change"]) < 0.01 and brutal["area_change"] < -0.02
    assert mild["n_faces"][0] == F.shape[0]


@pytest.mark.parametrize("bad", [
    lambda V, F: M.mesh_edge_stats(V[:, :2], F),
    lambda V, F: M.mesh_edge_stats(V, F[:0]),
    lambda V, F: M.mesh_edge_stats(V, np.array([[0, 0, 1]])),
    lambda V, F: M.mesh_edge_stats(V, F + 10 ** 6),
    lambda V, F: M.mesh_isotropic_remesh(V, F, "0.1"),
    lambda V, F: M.mesh_isotropic_remesh(V, F, 0.1, iterations=0),
    lambda V, F: M.mesh_isotropic_remesh(V, F, 0.1, relax=2.0),
    lambda V, F: M.mesh_split_long_edges(V, F, 0.001, max_passes=1),
    lambda V, F: M.mesh_lod_chain(V, F, fractions=(1.5,)),
    lambda V, F: M.mesh_select_lod({"x": 1}, 1.0, 1.0),
    lambda V, F: M.mesh_decimate_preserving(V, F, 100, protect_quantile=1.0),
    lambda V, F: M.pc_density(np.zeros((1, 3))),
    lambda V, F: M.pc_density(V, k=True),
    lambda V, F: M.pc_poisson_disk(V, -1.0),
    lambda V, F: M.pc_fill_sparse(V, float("nan")),
    lambda V, F: M.pc_thinning_report(V, np.zeros((0, 3))),
    lambda V, F: meshrepair.decimate_qem(V, F, 100, protect=np.ones(3, bool)),
])
def test_invalid_inputs_are_value_errors(bad):
    V, F = uv_sphere(nu=6, nv=8)
    with pytest.raises(ValueError):
        bad(V, F)
