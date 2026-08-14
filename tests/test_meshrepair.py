"""Ground-truth tests for meshrepair.py (simulation-ready body conditioning).

The correctness anchor is a known solid: the unit cube [0,1]^3 (8 vertices, 12
triangles), for which the exact mass properties are textbook — a uniform solid
cube of side s, density 1, has volume s^3, centre (s/2, s/2, s/2) and inertia
diag(m s^2 / 6) about its centre. inertia_tensor must reproduce that to ~1e-6.
Every other operator is checked against a property it must preserve (watertight-
ness, bounding box, volume, component count) rather than an exact byte pattern.
"""
import numpy as np
import pytest

import mesh
import meshrepair as mr

# --------------------------------------------------------------------------- #
# reference solid: the unit cube [0,1]^3 (outward winding, matches test_mesh)  #
# --------------------------------------------------------------------------- #
CUBE_V = np.array([
    [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
])
CUBE_F = np.array([
    [0, 2, 1], [0, 3, 2],        # z = 0
    [4, 5, 6], [4, 6, 7],        # z = 1
    [0, 1, 5], [0, 5, 4],        # y = 0
    [1, 2, 6], [1, 6, 5],        # x = 1
    [2, 3, 7], [2, 7, 6],        # y = 1
    [3, 0, 4], [3, 4, 7],        # x = 0
])
# open cube = cube minus the z = 1 face (drop the two top triangles, rows 2, 3)
OPEN_F = np.delete(CUBE_F, [2, 3], axis=0)


def tri_set(V, F):
    """Triangles as an order/winding-independent set of coordinate triples."""
    return {tuple(sorted(tuple(np.round(V[i], 9) + 0.0) for i in f)) for f in F}


def subdivided_cube(n):
    """A watertight unit cube with an n x n grid on each of the 6 faces, returned
    as a triangle soup (welding restores the shared vertices)."""
    verts, faces = [], []

    def add_face(origin, du, dv):
        base = len(verts)
        origin, du, dv = map(np.asarray, (origin, du, dv))
        for a in range(n + 1):
            for b in range(n + 1):
                verts.append(origin + (a / n) * du + (b / n) * dv)

        def vid(a, b):
            return base + a * (n + 1) + b

        for a in range(n):
            for b in range(n):
                faces.append((vid(a, b), vid(a + 1, b), vid(a + 1, b + 1)))
                faces.append((vid(a, b), vid(a + 1, b + 1), vid(a, b + 1)))

    add_face([0, 0, 0], [1, 0, 0], [0, 1, 0])   # z = 0
    add_face([0, 0, 1], [1, 0, 0], [0, 1, 0])   # z = 1
    add_face([0, 0, 0], [1, 0, 0], [0, 0, 1])   # y = 0
    add_face([0, 1, 0], [1, 0, 0], [0, 0, 1])   # y = 1
    add_face([0, 0, 0], [0, 1, 0], [0, 0, 1])   # x = 0
    add_face([1, 0, 0], [0, 1, 0], [0, 0, 1])   # x = 1
    return np.asarray(verts, np.float64), np.asarray(faces, np.int64)


def clean_subdivided_cube(n):
    """Welded + outward-oriented subdivided cube (watertight)."""
    V, F = mr.weld_vertices(*subdivided_cube(n), tol=1e-9)
    F, _ = mr.orient_consistent(V, F)
    assert mr.is_watertight(V, F)
    return V, F


# --------------------------------------------------------------------------- #
# watertight / boundary_edges / edge-manifold                                  #
# --------------------------------------------------------------------------- #
def test_is_watertight_closed_vs_open_cube():
    assert mr.is_watertight(CUBE_V, CUBE_F) is True
    assert mr.is_edge_manifold(CUBE_V, CUBE_F) is True
    assert mr.is_watertight(CUBE_V, OPEN_F) is False
    assert mr.is_edge_manifold(CUBE_V, OPEN_F) is True     # still manifold, just open


def test_boundary_edges_are_the_missing_face_rim():
    be = mr.boundary_edges(CUBE_V, OPEN_F)
    got = {tuple(e) for e in be.tolist()}
    assert got == {(4, 5), (5, 6), (6, 7), (4, 7)}
    assert mr.boundary_edges(CUBE_V, CUBE_F).shape == (0, 2)   # closed -> none


# --------------------------------------------------------------------------- #
# inertia_tensor — the load-bearing correctness anchor                         #
# --------------------------------------------------------------------------- #
def test_inertia_unit_cube():
    p = mr.inertia_tensor(CUBE_V, CUBE_F, density=1.0)
    assert abs(p["mass"] - 1.0) < 1e-6
    assert abs(p["volume"] - 1.0) < 1e-6
    assert np.allclose(p["com"], [0.5, 0.5, 0.5], atol=1e-6)
    assert np.allclose(p["inertia"], np.eye(3) / 6.0, atol=1e-6)


def test_inertia_scales_with_size_and_density():
    # side-2 cube [0,2]^3: volume 8, inertia diag(m s^2 / 6) = diag(8 * 4 / 6)
    p = mr.inertia_tensor(CUBE_V * 2.0, CUBE_F, density=1.0)
    assert abs(p["volume"] - 8.0) < 1e-6
    assert abs(p["mass"] - 8.0) < 1e-6
    assert np.allclose(p["com"], [1.0, 1.0, 1.0], atol=1e-6)
    assert np.allclose(p["inertia"], np.eye(3) * (8.0 * 4.0 / 6.0), atol=1e-6)
    # mass and inertia are linear in density
    p3 = mr.inertia_tensor(CUBE_V, CUBE_F, density=3.0)
    assert abs(p3["mass"] - 3.0) < 1e-6
    assert np.allclose(p3["inertia"], np.eye(3) * 3.0 / 6.0, atol=1e-6)


def test_inertia_requires_watertight():
    with pytest.raises(ValueError, match="watertight"):
        mr.inertia_tensor(CUBE_V, OPEN_F)


def test_inertia_handles_inward_winding():
    """A consistently-inward mesh still yields positive mass/volume."""
    inward = CUBE_F[:, [0, 2, 1]]
    p = mr.inertia_tensor(CUBE_V, inward)
    assert abs(p["volume"] - 1.0) < 1e-6
    assert np.allclose(p["inertia"], np.eye(3) / 6.0, atol=1e-6)


# --------------------------------------------------------------------------- #
# convex_hull                                                                   #
# --------------------------------------------------------------------------- #
def test_convex_hull_of_cube_corners_plus_noise():
    rng = np.random.default_rng(0)
    interior = 0.25 + 0.5 * rng.random((40, 3))       # strictly inside [0,1]^3
    pts = np.vstack([CUBE_V, interior])
    Vh, Fh = mr.convex_hull(pts)
    assert Vh.shape[0] == 8                            # interior points dropped
    assert mr.is_watertight(Vh, Fh)
    p = mr.inertia_tensor(Vh, Fh)
    assert abs(p["volume"] - 1.0) < 1e-9
    assert np.allclose(p["com"], [0.5, 0.5, 0.5], atol=1e-9)
    assert np.allclose(p["inertia"], np.eye(3) / 6.0, atol=1e-9)


def test_convex_hull_needs_enough_points():
    with pytest.raises(ValueError):
        mr.convex_hull(np.zeros((3, 3)))


# --------------------------------------------------------------------------- #
# weld_vertices / remove_degenerate_faces                                      #
# --------------------------------------------------------------------------- #
def test_weld_split_corner_cube_back_to_eight_vertices():
    soup_V = CUBE_V[CUBE_F].reshape(-1, 3)            # 36 unshared corners
    soup_F = np.arange(36, dtype=np.int64).reshape(12, 3)
    assert not mr.is_watertight(soup_V, soup_F)       # nothing is shared yet
    V, F = mr.weld_vertices(soup_V, soup_F)
    assert V.shape[0] == 8
    assert F.shape[0] == 12
    assert mr.is_watertight(V, F)
    assert tri_set(V, F) == tri_set(CUBE_V, CUBE_F)


def test_remove_degenerate_faces_drops_repeated_and_collinear():
    V = np.vstack([CUBE_V, [0.5, 0.0, 0.0]])          # new collinear midpoint (idx 8)
    F = np.vstack([CUBE_F,
                   [0, 0, 1],                          # repeated-index face
                   [0, 8, 1]])                         # collinear (zero-area) face
    Vc, Fc = mr.remove_degenerate_faces(V, F)
    assert Fc.shape[0] == 12
    assert tri_set(Vc, Fc) == tri_set(CUBE_V, CUBE_F)


# --------------------------------------------------------------------------- #
# fill_holes                                                                    #
# --------------------------------------------------------------------------- #
def test_fill_holes_closes_the_open_cube():
    assert not mr.is_watertight(CUBE_V, OPEN_F)
    V, F = mr.fill_holes(CUBE_V, OPEN_F)
    assert mr.is_watertight(V, F)
    # the fan lies in the z=1 plane, so the closed solid is exactly the unit cube
    F2, _ = mr.orient_consistent(V, F)
    p = mr.inertia_tensor(V, F2)
    assert abs(p["volume"] - 1.0) < 1e-9
    assert np.allclose(p["inertia"], np.eye(3) / 6.0, atol=1e-9)


def test_fill_holes_respects_max_boundary_len():
    V, F = mr.fill_holes(CUBE_V, OPEN_F, max_boundary_len=3)   # loop has 4 edges
    assert not mr.is_watertight(V, F)                          # too long -> left open


# --------------------------------------------------------------------------- #
# smooth_taubin                                                                 #
# --------------------------------------------------------------------------- #
def test_smooth_taubin_reduces_noise_without_collapsing_volume():
    V, F = clean_subdivided_cube(8)
    rng = np.random.default_rng(1)
    noise = 0.02 * rng.standard_normal(V.shape)
    Vn = V + noise
    before = np.linalg.norm(Vn - V, axis=1).mean()
    Vs = mr.smooth_taubin(Vn, F, iterations=15)
    after = np.linalg.norm(Vs - V, axis=1).mean()
    assert after < before                                     # noise attenuated
    vol0 = mr.inertia_tensor(V, F)["volume"]
    vol_s = mr.inertia_tensor(Vs, F)["volume"]
    assert vol_s > 0.85 * vol0                                # shrink-free: not collapsed
    assert vol_s < 1.10 * vol0


# --------------------------------------------------------------------------- #
# decimate_qem                                                                  #
# --------------------------------------------------------------------------- #
def test_decimate_qem_reduces_faces_and_keeps_bbox():
    V, F = clean_subdivided_cube(8)
    n0 = F.shape[0]
    assert n0 == 768
    Vd, Fd = mr.decimate_qem(V, F, target_faces=200)
    assert Fd.shape[0] < n0
    assert Fd.shape[0] <= 260                                 # collapsed toward target
    assert np.allclose(V.min(0), Vd.min(0), atol=1e-6)        # cube corners preserved
    assert np.allclose(V.max(0), Vd.max(0), atol=1e-6)


def test_decimate_rejects_bad_target():
    with pytest.raises(ValueError):
        mr.decimate_qem(CUBE_V, CUBE_F, 0)


# --------------------------------------------------------------------------- #
# orient_consistent / components                                               #
# --------------------------------------------------------------------------- #
def test_orient_consistent_fixes_one_flipped_face():
    F_bad = CUBE_F.copy()
    F_bad[5] = F_bad[5][::-1]                                  # reverse one winding
    assert _has_inconsistent_winding(CUBE_V, F_bad)
    F_fixed, flipped = mr.orient_consistent(CUBE_V, F_bad)
    assert flipped == 1
    assert not _has_inconsistent_winding(CUBE_V, F_fixed)
    assert mr._signed_volume(CUBE_V, F_fixed) > 0             # outward
    p = mr.inertia_tensor(CUBE_V, F_fixed)                    # now a valid solid
    assert np.allclose(p["inertia"], np.eye(3) / 6.0, atol=1e-6)


def test_components_splits_two_disjoint_cubes():
    V = np.vstack([CUBE_V, CUBE_V + [5.0, 0.0, 0.0]])
    F = np.vstack([CUBE_F, CUBE_F + 8])
    comps = mr.components(V, F)
    assert len(comps) == 2
    for Vc, Fc in comps:
        assert Vc.shape == (8, 3) and Fc.shape == (12, 3)
        assert mr.is_watertight(Vc, Fc)


def _has_inconsistent_winding(V, F):
    """A closed edge-manifold mesh is inconsistently wound iff some shared edge is
    traversed the same direction by both its faces."""
    from collections import defaultdict
    seen = defaultdict(list)
    for a, b, c in F:
        for u, v in ((int(a), int(b)), (int(b), int(c)), (int(c), int(a))):
            seen[(u, v) if u < v else (v, u)].append((u, v))
    for key, dirs in seen.items():
        if len(dirs) == 2 and dirs[0] == dirs[1]:
            return True
    return False


# --------------------------------------------------------------------------- #
# fail-closed on malformed input                                               #
# --------------------------------------------------------------------------- #
def test_fail_closed_bad_index_and_nonfinite():
    bad_idx = np.array([[0, 1, 99]])                          # out of range
    for fn in (mr.is_watertight, mr.weld_vertices):
        with pytest.raises(ValueError, match="out of range"):
            fn(CUBE_V, bad_idx)
    nan_V = CUBE_V.copy()
    nan_V[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        mr.is_watertight(nan_V, CUBE_F)
    with pytest.raises(ValueError):
        mr.inertia_tensor(nan_V, CUBE_F)
    with pytest.raises(ValueError):                           # wrong shape
        mr.smooth_taubin(np.zeros((4, 2)), CUBE_F)


# --------------------------------------------------------------------------- #
# integration through mesh.py (import side -> conditioning side)               #
# --------------------------------------------------------------------------- #
def test_roundtrips_through_mesh_reader(tmp_path):
    """A cube written and re-read by mesh.py conditions to the same solid."""
    p = str(tmp_path / "cube.obj")
    mesh.write_mesh(p, CUBE_V, CUBE_F)
    V, F = mesh.read_mesh(p)
    assert mr.is_watertight(V, F)
    props = mr.inertia_tensor(V, F)
    assert abs(props["volume"] - 1.0) < 1e-6
    assert np.allclose(props["inertia"], np.eye(3) / 6.0, atol=1e-6)
