"""Ground-truth tests for SDF CSG composition (sdf_ops.py).

Every check uses a closed-form signed distance (|p-c|-R for spheres, the exact
box distance, the min/max CSG algebra) evaluated at hand-computed points, so the
expected values are independent of the implementation. Boolean ops are exact
algebra -> tight tolerances; the smooth-min has a closed-form dip of k/4 at a==b.
Scale consistency is checked at two magnitudes (unit and x1000) so no absolute
epsilon hides a scale bug."""
import numpy as np
import pytest

import sdf_ops


# --------------------------------------------------------------------------- #
# Primitives: closed-form distances at known points, at two scales.           #
# --------------------------------------------------------------------------- #
def test_sphere_sdf_closed_form_two_scales():
    for s in (1.0, 1000.0):                      # failure mode A: >=2 scales
        c = np.array([1.0, 2.0, -1.0]) * s
        R = 2.0 * s
        pts = np.array([
            c,                                   # center -> -R
            c + np.array([R, 0, 0]),             # on surface -> 0
            c + np.array([2 * R, 0, 0]),         # one radius outside -> +R
            c + np.array([0, 0, -3 * R]),        # 2R outside -> +2R
        ])
        got = sdf_ops.sphere_sdf(pts, c, R)
        expect = np.array([-R, 0.0, R, 2 * R])
        assert np.allclose(got, expect, rtol=1e-12, atol=1e-9 * s)


def test_box_sdf_exact_face_edge_corner_interior():
    # cube [-1,1]^3, half-extents (1,1,1). GT distances are hand-computed geometry.
    c = np.zeros(3)
    he = np.ones(3)
    pts = np.array([
        [2.0, 0.0, 0.0],     # off a face -> perpendicular distance 1
        [2.0, 2.0, 0.0],     # off an edge -> sqrt(1^2+1^2)
        [2.0, 2.0, 2.0],     # off a corner -> sqrt(3)
        [0.0, 0.0, 0.0],     # center -> nearest face at 1 -> -1
        [0.5, 0.0, 0.0],     # inside -> nearest face x=1 at 0.5 -> -0.5
    ])
    got = sdf_ops.box_sdf(pts, c, he)
    expect = np.array([1.0, np.sqrt(2.0), np.sqrt(3.0), -1.0, -0.5])
    assert np.allclose(got, expect, rtol=1e-12, atol=1e-12)


def test_box_sdf_scale_homogeneous():
    # box SDF is degree-1 homogeneous: scaling geometry scales the distance.
    rng = np.random.default_rng(0)
    g = rng.uniform(-3, 3, (50, 3))
    c = np.array([0.2, -0.4, 0.1])
    he = np.array([1.0, 0.7, 1.3])
    s = 1000.0
    base = sdf_ops.box_sdf(g, c, he)
    scaled = sdf_ops.box_sdf(g * s, c * s, he * s)
    assert np.allclose(scaled, s * base, rtol=1e-12, atol=1e-9 * s)


# --------------------------------------------------------------------------- #
# Boolean CSG: min / max / max(a,-b) with discriminating geometry.            #
# --------------------------------------------------------------------------- #
def _two_spheres(g):
    """SDFs of A=center(0) R=2 and B=center(2,0,0) R=1 on coords g."""
    a = sdf_ops.sphere_sdf(g, [0, 0, 0], 2.0)
    b = sdf_ops.sphere_sdf(g, [2, 0, 0], 1.0)
    return a, b


def test_union_zero_levelset_and_exterior_distance():
    # exterior point far along -x: nearest surface is A's exposed left pole.
    p_out = np.array([[-5.0, 0.0, 0.0]])
    a, b = _two_spheres(p_out)
    u = sdf_ops.sdf_union(a, b)
    assert np.isclose(u[0], 3.0, atol=1e-12)          # true distance to union boundary
    # a point on A's surface, away from B -> on the union boundary (sdf==0).
    p_bnd = np.array([[-2.0, 0.0, 0.0]])
    au, bu = _two_spheres(p_bnd)
    assert np.isclose(sdf_ops.sdf_union(au, bu)[0], 0.0, atol=1e-12)
    # a point inside B only -> inside the union (sdf<0).
    p_inB = np.array([[2.0, 0.0, 0.0]])
    ai, bi = _two_spheres(p_inB)
    assert sdf_ops.sdf_union(ai, bi)[0] < 0.0


def test_intersect_is_max_and_semantics():
    # P inside A but outside B -> NOT in the intersection (sdf>0).
    p = np.array([[0.0, 0.0, 0.0]])              # a=-2 (inside A), b=1 (outside B)
    a, b = _two_spheres(p)
    inter = sdf_ops.sdf_intersect(a, b)
    assert np.isclose(inter[0], np.maximum(a, b)[0], atol=1e-12)
    assert inter[0] > 0.0                        # outside the intersection
    # P inside both -> inside the intersection (sdf<0).
    p2 = np.array([[1.5, 0.0, 0.0]])             # a=-0.5, b=-0.5
    a2, b2 = _two_spheres(p2)
    assert sdf_ops.sdf_intersect(a2, b2)[0] < 0.0


def test_subtract_is_max_a_neg_b_and_semantics():
    # A minus B. Point inside A and inside B -> removed (sdf>0).
    p_rm = np.array([[2.0, 0.0, 0.0]])           # a=0 (on A), b=-1 (inside B)
    a, b = _two_spheres(p_rm)
    sub = sdf_ops.sdf_subtract(a, b)
    assert np.isclose(sub[0], np.maximum(a, -b)[0], atol=1e-12)
    assert sub[0] > 0.0                          # carved away because it lies in B
    # Point inside A and outside B -> kept (sdf<0).
    p_keep = np.array([[-1.0, 0.0, 0.0]])        # a=-1 (inside A), b=2 (outside B)
    a2, b2 = _two_spheres(p_keep)
    assert sdf_ops.sdf_subtract(a2, b2)[0] < 0.0
    # non-commutative: A\B != B\A in general
    assert not np.isclose(sdf_ops.sdf_subtract(a, b)[0],
                          sdf_ops.sdf_subtract(b, a)[0])


def test_union_volume_inclusion_exclusion_on_grid():
    # set-algebra GT on a dense lattice: max(|A|,|B|) <= |A∪B| <= |A|+|B|.
    coords, _ = sdf_ops.grid_coords([[-3, 3], [-3, 3], [-3, 3]], 40)
    a, b = _two_spheres(coords)
    va = int((a < 0).sum())
    vb = int((b < 0).sum())
    vu = int((sdf_ops.sdf_union(a, b) < 0).sum())
    assert max(va, vb) <= vu <= va + vb
    assert vu < va + vb                          # the spheres genuinely overlap


# --------------------------------------------------------------------------- #
# Smooth union: closed-form dip k/4, convergence to min, symmetry, scale.     #
# --------------------------------------------------------------------------- #
def test_smooth_union_closed_form_dip_and_min_limit():
    # regime 1: a == b -> smin = a - k/4 exactly (max dip of the quadratic smin).
    for s in (1.0, 1000.0):                      # scale consistency
        a = np.array([0.3 * s])
        k = 0.4 * s
        smin = sdf_ops.sdf_smooth_union(a, a, k)
        assert np.isclose(smin[0], 0.3 * s - k / 4.0, rtol=1e-12, atol=1e-9 * s)
    # regime 2: well-separated (|a-b| >> k) -> smin == min exactly.
    a = np.array([-5.0, 2.0, 0.0])
    b = np.array([1.0, -3.0, 4.0])
    smin = sdf_ops.sdf_smooth_union(a, b, 1e-9)
    assert np.allclose(smin, np.minimum(a, b), rtol=0, atol=1e-8)


def test_smooth_union_converges_and_stays_below_min():
    rng = np.random.default_rng(1)
    a = rng.uniform(-2, 2, 200)
    b = rng.uniform(-2, 2, 200)
    hard = np.minimum(a, b)
    prev = np.inf
    for k in (1.0, 0.25, 0.0625):
        smin = sdf_ops.sdf_smooth_union(a, b, k)
        assert np.all(smin <= hard + 1e-12)      # smin never exceeds the hard min
        dev = float(np.max(hard - smin))         # max downward dip
        assert dev <= k / 4.0 + 1e-12            # bounded by the closed-form k/4
        assert dev < prev                        # monotonically approaches min
        prev = dev


def test_smooth_union_symmetric():
    rng = np.random.default_rng(2)
    a = rng.uniform(-2, 2, 100)
    b = rng.uniform(-2, 2, 100)
    assert np.allclose(sdf_ops.sdf_smooth_union(a, b, 0.7),
                       sdf_ops.sdf_smooth_union(b, a, 0.7), rtol=1e-12, atol=1e-12)


def test_smooth_union_homogeneous():
    rng = np.random.default_rng(3)
    a = rng.uniform(-2, 2, 100)
    b = rng.uniform(-2, 2, 100)
    k, s = 0.5, 1000.0
    base = sdf_ops.sdf_smooth_union(a, b, k)
    scaled = sdf_ops.sdf_smooth_union(a * s, b * s, k * s)
    assert np.allclose(scaled, s * base, rtol=1e-12, atol=1e-9 * s)


def test_smooth_union_rejects_nonpositive_k():
    a = np.zeros(3)
    for bad in (0.0, -1.0):                      # failure mode B: fail-closed
        with pytest.raises(ValueError):
            sdf_ops.sdf_smooth_union(a, a, bad)


# --------------------------------------------------------------------------- #
# Offset: uniform distance shift, equals a grown/shrunk primitive.            #
# --------------------------------------------------------------------------- #
def test_offset_shifts_distance_uniformly():
    rng = np.random.default_rng(4)
    sdf = rng.uniform(-3, 3, (20, 20))
    for r in (0.5, -0.7, 1000.0):
        assert np.allclose(sdf_ops.sdf_offset(sdf, r), sdf - r, rtol=1e-12, atol=1e-12)


def test_offset_of_sphere_equals_larger_sphere():
    # offsetting a sphere SDF by r is exactly a sphere of radius R+r, at two scales.
    for s in (1.0, 1000.0):
        g = np.array([[0.0, 0.0, 0.0], [s, 0, 0], [0, 2 * s, 0]])
        c = np.array([0.1, -0.2, 0.3]) * s
        R, r = 2.0 * s, 0.5 * s
        off = sdf_ops.sdf_offset(sdf_ops.sphere_sdf(g, c, R), r)
        grown = sdf_ops.sphere_sdf(g, c, R + r)
        assert np.allclose(off, grown, rtol=1e-12, atol=1e-9 * s)


# --------------------------------------------------------------------------- #
# grid_coords: voxel-center alignment matches occupancy convention.           #
# --------------------------------------------------------------------------- #
def test_grid_coords_center_alignment_and_extent():
    coords, extent = sdf_ops.grid_coords([[0, 2], [0, 4], [-1, 1]], 2)
    assert coords.shape == (2, 2, 2, 3)
    assert extent == (0.0, 2.0, 0.0, 4.0, -1.0, 1.0)
    # voxel i center = lo + (i+0.5)/res*span. For x: span 2, res 2 -> 0.5, 1.5.
    assert np.allclose(coords[:, 0, 0, 0], [0.5, 1.5])
    assert np.allclose(coords[0, :, 0, 1], [1.0, 3.0])      # y: span 4 -> 1.0, 3.0
    assert np.allclose(coords[0, 0, :, 2], [-0.5, 0.5])     # z: span 2 shifted -1


def test_grid_coords_anisotropic_res():
    coords, _ = sdf_ops.grid_coords([[0, 1], [0, 1], [0, 1]], [2, 3, 4])
    assert coords.shape == (2, 3, 4, 3)


def test_grid_sphere_zero_crossing_radius():
    # SDF sign flips across the true surface: cells inside R are negative.
    coords, _ = sdf_ops.grid_coords([[-2, 2], [-2, 2], [-2, 2]], 64)
    sdf = sdf_ops.sphere_sdf(coords, [0, 0, 0], 1.0)
    centers = np.linalg.norm(coords, axis=-1)
    assert np.all(sdf[centers < 0.95] < 0)                  # comfortably inside
    assert np.all(sdf[centers > 1.05] > 0)                  # comfortably outside


# --------------------------------------------------------------------------- #
# Fail-closed on malformed / degenerate inputs.                               #
# --------------------------------------------------------------------------- #
def test_sphere_sdf_rejects_negative_radius():
    with pytest.raises(ValueError):
        sdf_ops.sphere_sdf(np.zeros((1, 3)), [0, 0, 0], -1.0)


def test_box_sdf_rejects_negative_half_extents():
    with pytest.raises(ValueError):
        sdf_ops.box_sdf(np.zeros((1, 3)), [0, 0, 0], [1.0, -0.1, 1.0])


def test_primitives_reject_bad_grid_shape():
    with pytest.raises(ValueError):
        sdf_ops.sphere_sdf(np.zeros((4, 2)), [0, 0, 0], 1.0)     # last axis != 3
    with pytest.raises(ValueError):
        sdf_ops.box_sdf(np.zeros((4, 4)), [0, 0, 0], [1, 1, 1])


def test_grid_coords_rejects_degenerate():
    with pytest.raises(ValueError):
        sdf_ops.grid_coords([[0, 0], [0, 1], [0, 1]], 8)        # zero-span axis
    with pytest.raises(ValueError):
        sdf_ops.grid_coords([[0, 1], [0, 1], [0, 1]], 0)        # res<=0
