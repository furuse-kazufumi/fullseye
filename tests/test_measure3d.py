"""3-D metrology fits (measure3d) — every result is checked against known ground
truth, and each bound beats an honest null (AABB / PCA box / diagonal sphere), so
a stub returning a plausible-looking dict would fail.

Convention under test: points are (depth, row, col), z-first."""
import numpy as np
import pytest

import measure3d as m3


def _rot(seed):
    rng = np.random.default_rng(seed)
    q, _ = np.linalg.qr(rng.standard_normal((3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]
    return q


def _box_surface(half, R, t, n=9):
    g = np.linspace(-1, 1, n)
    pts = []
    for a in (-1, 1):
        for i in g:
            for j in g:
                pts.append([a, i, j]); pts.append([i, a, j]); pts.append([i, j, a])
    return (np.array(pts) * half) @ R.T + t


# --------------------------------------------------------------------------- #
# fits recover known geometry to ~machine precision                            #
# --------------------------------------------------------------------------- #
def test_fit_line3_recovers_direction_and_is_exact_on_a_line():
    R = _rot(1); d0 = R[:, 0]; c0 = np.array([12., 5., -3.])
    t = np.linspace(-4, 4, 50)[:, None]
    P = c0 + t * d0
    r = m3.fit_line3(P)
    assert abs(abs(r["direction"] @ d0) - 1) < 1e-9      # direction (up to sign)
    assert r["rms"] < 1e-9                                # exact on a line
    assert np.allclose(r["center"], P.mean(0))


def test_fit_line3_beats_a_wrong_direction():
    R = _rot(2); P = np.array([0., 0., 0.]) + np.linspace(-3, 3, 40)[:, None] * R[:, 0]
    diff = P - P.mean(0)
    wrong = R[:, 1]
    null_rms = np.sqrt(np.mean((diff ** 2).sum(1) - (diff @ wrong) ** 2))
    assert m3.fit_line3(P)["rms"] < 1e-6 < null_rms       # fit ~0, wrong axis large


def test_fit_plane3_recovers_normal_and_is_exact():
    R = _rot(3); n0 = R[:, 2]; c0 = np.array([1., 2., 3.])
    g = np.random.default_rng(3).uniform(-5, 5, (80, 2))
    P = c0 + g[:, 0:1] * R[:, 0] + g[:, 1:2] * R[:, 1]
    r = m3.fit_plane3(P)
    assert abs(abs(r["normal"] @ n0) - 1) < 1e-9
    assert r["rms"] < 1e-9


def test_fit_sphere3_recovers_center_and_radius():
    cs = np.array([3., -2., 7.]); R = 4.3
    u = np.random.default_rng(4).standard_normal((200, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    r = m3.fit_sphere3(cs + R * u)
    assert np.allclose(r["center"], cs, atol=1e-6)
    assert abs(r["r"] - R) < 1e-6 and r["rms"] < 1e-6


def test_fit_circle3_recovers_center_radius_normal():
    R = _rot(5); n0 = R[:, 2]; cc0 = np.array([0., 1., -1.]); rc = 2.7
    th = np.linspace(0, 2 * np.pi, 60, endpoint=False)
    P = cc0 + rc * (np.cos(th)[:, None] * R[:, 0] + np.sin(th)[:, None] * R[:, 1])
    r = m3.fit_circle3(P)
    assert np.allclose(r["center"], cc0, atol=1e-6)
    assert abs(r["r"] - rc) < 1e-6
    assert abs(abs(r["normal"] @ n0) - 1) < 1e-6


# --------------------------------------------------------------------------- #
# bounding boxes — the star: minimum-volume OBB beats AABB and a PCA box        #
# --------------------------------------------------------------------------- #
def test_aabb_is_exact_on_axis_aligned_and_loose_on_rotated():
    half = np.array([5., 2., 1.]); I = np.eye(3); t = np.array([1., 1., 1.])
    P = _box_surface(half, I, t)
    aabb = m3.smallest_box3_axis(P)
    assert np.allclose(sorted(aabb["size"]), sorted(2 * half), atol=1e-9)  # exact axis-aligned
    # rotated: AABB volume strictly exceeds the true box volume
    Pr = _box_surface(half, _rot(6), t)
    assert m3.smallest_box3_axis(Pr)["volume"] > float(np.prod(2 * half)) + 1e-3


def test_smallest_box3_recovers_rotated_box_and_beats_aabb():
    half = np.array([5., 2., 1.]); R = _rot(7); t = np.array([10., -4., 6.])
    P = _box_surface(half, R, t)
    obb = m3.smallest_box3(P)
    truevol = float(np.prod(2 * half))
    assert np.allclose(sorted([obb["l1"], obb["l2"], obb["l3"]]), sorted(half), atol=1e-6)
    assert np.allclose(obb["center"], t, atol=1e-6)
    assert abs(obb["volume"] - truevol) < 1e-4
    assert obb["volume"] < m3.smallest_box3_axis(P)["volume"] - 1e-3   # beats AABB
    assert obb["l1"] >= obb["l2"] >= obb["l3"]                          # sorted


def test_smallest_box3_reaches_case_b_minimum_on_a_tetrahedron():
    # regression guard (O'Rourke case b): a regular tetrahedron's minimum box has NO
    # face flush with a hull face, so a hull-face-only search returns ~2.0. The unit
    # cube (volume 1.0) encloses these 4 alternating cube corners, so the true min is
    # 1.0; multi-start refinement must reach it, not the 2.0 hull-face box.
    T = np.array([[0., 0, 0], [1, 1, 0], [1, 0, 1], [0, 1, 1]])
    obb = m3.smallest_box3(T)
    axes, half = obb["axes"], np.array([obb["l1"], obb["l2"], obb["l3"]])
    assert np.all(np.abs((T - obb["center"]) @ axes.T) <= half + 1e-9)   # encloses all 4
    assert obb["volume"] <= 1.05, f"did not reach the case-b optimum: {obb['volume']}"


def test_smallest_box3_never_larger_than_pca_box():
    # a regular tetrahedron: PCA axes are NOT the minimum-volume orientation
    tet = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], float) * 3
    tet = tet @ _rot(8).T + np.array([2., 2., 2.])
    obb, pca = m3.smallest_box3(tet), m3.fit_box3(tet)
    assert obb["volume"] <= pca["volume"] + 1e-9
    assert obb["volume"] < pca["volume"]           # strictly smaller here


def test_box_corners_are_consistent_with_extents():
    P = _box_surface(np.array([3., 2., 1.]), _rot(9), np.array([0., 0., 0.]))
    obb = m3.smallest_box3(P)
    c = obb["corners"]
    assert c.shape == (8, 3)
    # every input point lies inside (or on) the reported box
    axes, half = obb["axes"], np.array([obb["l1"], obb["l2"], obb["l3"]])
    local = np.abs((P - obb["center"]) @ axes.T)
    assert np.all(local <= half + 1e-6)


# --------------------------------------------------------------------------- #
# minimum enclosing sphere (Welzl) — exact on known configurations             #
# --------------------------------------------------------------------------- #
def test_min_sphere_on_a_sphere_equals_that_sphere():
    cs = np.array([1., 2., 3.]); R = 5.0
    u = np.random.default_rng(10).standard_normal((300, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    P = cs + R * u
    s = m3.smallest_sphere3(P)
    assert abs(s["r"] - R) < 1e-6 and np.allclose(s["center"], cs, atol=1e-5)
    assert np.all(np.linalg.norm(P - s["center"], axis=1) <= s["r"] + 1e-7)


def test_min_sphere_cube_is_half_space_diagonal():
    cube = np.array(np.meshgrid([-1, 1], [-1, 1], [-1, 1])).T.reshape(-1, 3) * 2.0
    s = m3.smallest_sphere3(cube)
    assert abs(s["r"] - np.sqrt(3) * 2.0) < 1e-6
    assert np.allclose(s["center"], 0.0, atol=1e-6)


def test_min_sphere_encloses_a_random_cloud_tightly():
    P = np.random.default_rng(11).standard_normal((500, 3)) * [6, 2, 1]
    s = m3.smallest_sphere3(P)
    assert np.all(np.linalg.norm(P - s["center"], axis=1) <= s["r"] + 1e-7)  # encloses all
    # and it is tight: at least two points sit on the boundary
    on = np.abs(np.linalg.norm(P - s["center"], axis=1) - s["r"]) < 1e-6
    assert on.sum() >= 2


# --------------------------------------------------------------------------- #
# fail-closed on malformed / degenerate input                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fn,arg", [
    (m3.fit_plane3, np.zeros((5, 2))),                                # wrong shape
    (m3.fit_sphere3, np.array([[0., 0., np.nan]] * 5)),              # non-finite
    (m3.fit_sphere3, np.zeros((3, 3))),                              # too few points
    (m3.fit_plane3, np.column_stack([np.arange(6.), np.arange(6.) * 2, np.arange(6.) * 3])),  # collinear
    (m3.smallest_box3, np.column_stack([np.random.default_rng(0).uniform(0, 1, 10),
                                        np.random.default_rng(1).uniform(0, 1, 10),
                                        np.zeros(10)])),             # coplanar -> no 3-D box
])
def test_fail_closed(fn, arg):
    with pytest.raises(ValueError):
        fn(arg)
