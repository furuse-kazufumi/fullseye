"""Ground-truth tests for grasp synthesis from geometry (grasp.py).

The reference object is a **thin box** built from mesh.py primitives: a slab
0.30 x 0.30 x 0.04 (recentred on the origin). A parallel-jaw gripper whose
opening is capped below the box's 0.30 side but above its 0.04 thickness can only
grasp it one way — closing across the two large parallel faces — so we have a
known-correct answer to check the sampler against:

  * the closing ``axis`` must be the face normal (the thin +-z direction);
  * the jaw ``width`` must be the box thickness (~0.04);
  * every proposed grasp must be antipodal / force-closure with positive quality.

The force-closure and Ferrari-Canny unit tests use hand-built contact pairs with
known geometry (opposing normals colinear with the contact line = a clean grasp;
same-side or off-cone pairs = not a grasp).
"""
import numpy as np
import pytest

import grasp
import mesh
import pointcloud


# --------------------------------------------------------------------------- #
# reference object: a thin box, recentred on the origin                       #
# --------------------------------------------------------------------------- #
def make_box(sx, sy, sz):
    """Axis-aligned box of the given side lengths, centred on the origin."""
    V = np.array([
        [0, 0, 0], [sx, 0, 0], [sx, sy, 0], [0, sy, 0],
        [0, 0, sz], [sx, 0, sz], [sx, sy, sz], [0, sy, sz],
    ], np.float64)
    V = V - V.mean(axis=0)
    F = np.array([
        [0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
        [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
    ], np.int64)
    return V, F


THIN_BOX = make_box(0.30, 0.30, 0.04)          # graspable only across the +-z faces
MU = 0.5


def _box_cloud(n=2000, seed=0):
    V, F = THIN_BOX
    pts = mesh.sample_surface(V, F, n, seed=seed)
    nrm = pointcloud.estimate_normals(pts, k=16)
    return pts, nrm


# --------------------------------------------------------------------------- #
# sampling on the thin box                                                    #
# --------------------------------------------------------------------------- #
def test_sample_antipodal_grasps_finds_cross_face_grasps():
    pts, nrm = _box_cloud()
    grasps = grasp.sample_antipodal_grasps(pts, normals=nrm, mu=MU,
                                           width_max=0.08, seed=0)
    assert len(grasps) > 0, "no grasps found on a graspable thin box"

    # inspect the best handful: they must close across the thin (z) faces
    from scipy.spatial import cKDTree
    tree = cKDTree(pts)
    for g in grasps[:20]:
        assert g.contacts.shape == (2, 3)
        assert g.center.shape == (3,) and g.axis.shape == (3,) and g.approach.shape == (3,)
        assert abs(np.linalg.norm(g.axis) - 1.0) < 1e-9         # unit closing axis
        assert abs(g.width - 0.04) < 6e-3                       # ~ box thickness
        assert abs(abs(g.axis[2]) - 1.0) < 0.15                 # axis ~ +-z face normal
        assert g.quality > 0.0                                  # scored, force-closure
        # force-closure holds under the sampler's own (unoriented) normals
        _, idx = tree.query(g.contacts)
        assert grasp.force_closure(g.contacts, nrm[idx], MU) is True


def test_grasps_from_mesh_convenience():
    V, F = THIN_BOX
    grasps = grasp.grasps_from_mesh(V, F, n_surface=1500, mu=MU, width_max=0.08, seed=1)
    assert len(grasps) > 0
    assert all(g.quality > 0 for g in grasps[:10])
    assert abs(grasps[0].width - 0.04) < 6e-3


def test_width_max_gates_the_opening():
    """A jaw that cannot open to the box thickness finds nothing."""
    pts, nrm = _box_cloud()
    none = grasp.sample_antipodal_grasps(pts, normals=nrm, mu=MU, width_max=0.02, seed=0)
    assert none == []                          # 0.02 < 0.04 thickness -> ungraspable


def test_normals_estimated_when_omitted():
    pts, _ = _box_cloud()
    grasps = grasp.sample_antipodal_grasps(pts, normals=None, mu=MU, width_max=0.08, seed=0)
    assert len(grasps) > 0                      # normals computed internally


# --------------------------------------------------------------------------- #
# force closure (Nguyen 1988)                                                 #
# --------------------------------------------------------------------------- #
def test_force_closure_true_for_clean_antipodal_pair():
    contacts = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    normals = np.array([[0, 0, -1.0], [0, 0, 1.0]])          # opposing, along the line
    assert grasp.force_closure(contacts, normals, MU) is True
    # sign of the normals must not matter (unsigned line test)
    assert grasp.force_closure(contacts, -normals, MU) is True
    assert grasp.force_closure(contacts, np.array([[0, 0, 1.0], [0, 0, 1.0]]), MU) is True


def test_force_closure_false_for_single_contact():
    assert grasp.force_closure(np.array([[0, 0, 0.0]]),
                               np.array([[0, 0, 1.0]]), MU) is False


def test_force_closure_false_for_same_side_pair():
    # two contacts on the same face: line lies in the face plane, perpendicular
    # to the (shared) normal -> outside both cones.
    contacts = np.array([[0, 0, 0.0], [0.05, 0, 0.0]], float)
    normals = np.array([[0, 0, 1.0], [0, 0, 1.0]])
    assert grasp.force_closure(contacts, normals, MU) is False


def test_force_closure_false_outside_friction_cone():
    # the contact line is 45 deg off the normals; mu=0.2 -> cone half-angle ~11 deg.
    contacts = np.array([[0, 0, 0.0], [0.03, 0, 0.03]], float)
    normals = np.array([[0, 0, -1.0], [0, 0, 1.0]])
    assert grasp.force_closure(contacts, normals, 0.2) is False
    # widen the cone enough (mu=1.2 -> ~50 deg) and the same pair is now closure
    assert grasp.force_closure(contacts, normals, 1.2) is True


# --------------------------------------------------------------------------- #
# Ferrari-Canny epsilon quality (Ferrari & Canny 1992)                        #
# --------------------------------------------------------------------------- #
def test_ferrari_canny_positive_for_closure_zero_otherwise():
    contacts = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    good = np.array([[0, 0, -1.0], [0, 0, 1.0]])
    bad = np.array([[0, 0, 1.0], [0, 0, 1.0]])              # same-side, not closure
    assert grasp.ferrari_canny_quality(contacts, good, MU) > 0.0
    assert grasp.ferrari_canny_quality(np.array([[0, 0, 0.0], [0.05, 0, 0.0]]),
                                       bad, MU) == 0.0
    # a single contact cannot be scored
    assert grasp.ferrari_canny_quality(contacts[:1], good[:1], MU) == 0.0


def test_ferrari_canny_centered_beats_skewed():
    contacts = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    centered = np.array([[0, 0, -1.0], [0, 0, 1.0]])            # normals along the line
    ang = np.radians(20)
    skewed = np.array([[np.sin(ang), 0, -np.cos(ang)],
                       [np.sin(ang), 0, np.cos(ang)]])          # tilted within the cone
    q_centered = grasp.ferrari_canny_quality(contacts, centered, MU)
    q_skewed = grasp.ferrari_canny_quality(contacts, skewed, MU)
    assert q_centered > q_skewed > 0.0


def test_ferrari_canny_is_finite_and_deterministic():
    contacts = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    normals = np.array([[0, 0, -1.0], [0, 0, 1.0]])
    a = grasp.ferrari_canny_quality(contacts, normals, MU, n_cone=8)
    b = grasp.ferrari_canny_quality(contacts, normals, MU, n_cone=8)
    assert a == b and np.isfinite(a)


# --------------------------------------------------------------------------- #
# frame / approach / ranking                                                  #
# --------------------------------------------------------------------------- #
def test_approach_is_unit_and_perpendicular_to_axis():
    contacts = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    normals = np.array([[0, 0, -1.0], [0, 0, 1.0]])
    a = grasp.approach_vector_from_normals(contacts, normals)
    axis = (contacts[1] - contacts[0]) / np.linalg.norm(contacts[1] - contacts[0])
    assert abs(np.linalg.norm(a) - 1.0) < 1e-9
    assert abs(float(a @ axis)) < 1e-9                          # perpendicular


def test_grasp_pose_is_a_rigid_frame():
    contacts = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    normals = np.array([[0, 0, -1.0], [0, 0, 1.0]])
    g = grasp._make_grasp(contacts[0], contacts[1], normals[0], normals[1],
                          MU, grasp.CONE_EDGES_DEFAULT)
    T = g.pose
    assert T.shape == (4, 4)
    R = T[:3, :3]
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-9)           # orthonormal
    assert abs(np.linalg.det(R) - 1.0) < 1e-9                   # proper rotation
    assert np.allclose(T[3], [0, 0, 0, 1])
    assert np.allclose(T[:3, 3], g.center)                      # origin at the centre
    assert np.allclose(R[:, 0], g.approach)                     # x column = approach
    assert np.allclose(R[:, 1], g.axis)                         # y column = axis


def test_rank_grasps_orders_by_quality_descending():
    def dummy(q):
        return grasp.Grasp(center=np.zeros(3), axis=np.array([0, 0, 1.0]),
                           approach=np.array([1.0, 0, 0]), width=0.04, quality=q,
                           contacts=np.array([[0, 0, -0.02], [0, 0, 0.02]]))
    grasps = [dummy(0.1), dummy(0.9), dummy(0.5)]
    ranked = grasp.rank_grasps(grasps)
    assert [g.quality for g in ranked] == [0.9, 0.5, 0.1]


def test_sampler_output_is_sorted_and_deterministic():
    pts, nrm = _box_cloud()
    a = grasp.sample_antipodal_grasps(pts, normals=nrm, mu=MU, width_max=0.08, seed=0)
    b = grasp.sample_antipodal_grasps(pts, normals=nrm, mu=MU, width_max=0.08, seed=0)
    assert len(a) == len(b) and len(a) > 0
    assert np.array_equal(a[0].contacts, b[0].contacts)
    qs = [g.quality for g in a]
    assert qs == sorted(qs, reverse=True)                       # best first
    # a different seed explores a different subset -> not identical
    c = grasp.sample_antipodal_grasps(pts, normals=nrm, mu=MU, width_max=0.08,
                                      n_samples=50, seed=1)
    d = grasp.sample_antipodal_grasps(pts, normals=nrm, mu=MU, width_max=0.08,
                                      n_samples=50, seed=2)
    assert not (len(c) == len(d) and all(np.array_equal(x.contacts, y.contacts)
                                         for x, y in zip(c, d)))


# --------------------------------------------------------------------------- #
# optional collision check                                                    #
# --------------------------------------------------------------------------- #
def test_collision_free_flags_a_protruding_point():
    contacts = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    normals = np.array([[0, 0, -1.0], [0, 0, 1.0]])
    g = grasp._make_grasp(contacts[0], contacts[1], normals[0], normals[1],
                          MU, grasp.CONE_EDGES_DEFAULT)
    # a lone point on the closing axis, wider than the grasp but inside the jaw
    # envelope -> a finger would strike it first.
    blocked = np.array([[0, 0, 0.05]])
    assert grasp.collision_free(g, blocked, gripper_width=0.12, finger_len=0.05) is False
    # empty / clear surroundings -> free
    assert grasp.collision_free(g, np.zeros((0, 3)), gripper_width=0.12, finger_len=0.05)
    assert grasp.collision_free(g, np.array([[0.5, 0.5, 0.5]]),
                                gripper_width=0.12, finger_len=0.05) is True


# --------------------------------------------------------------------------- #
# fail-closed on malformed / degenerate input                                 #
# --------------------------------------------------------------------------- #
def test_empty_or_single_point_cloud_returns_no_grasps():
    assert grasp.sample_antipodal_grasps(np.zeros((0, 3)), mu=MU) == []
    assert grasp.sample_antipodal_grasps(np.zeros((1, 3)), mu=MU) == []
    # all points coincident -> degenerate (zero-extent) cloud -> no grasps
    assert grasp.sample_antipodal_grasps(np.ones((50, 3)), mu=MU) == []


def test_non_positive_mu_raises():
    contacts = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    normals = np.array([[0, 0, -1.0], [0, 0, 1.0]])
    for bad in (0.0, -0.5):
        with pytest.raises(ValueError):
            grasp.force_closure(contacts, normals, bad)
        with pytest.raises(ValueError):
            grasp.ferrari_canny_quality(contacts, normals, bad)
        with pytest.raises(ValueError):
            grasp.sample_antipodal_grasps(np.zeros((4, 3)), mu=bad)


def test_non_finite_input_raises():
    good = np.array([[0, 0, -0.02], [0, 0, 0.02]], float)
    normals = np.array([[0, 0, -1.0], [0, 0, 1.0]])
    bad = good.copy(); bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        grasp.force_closure(bad, normals, MU)
    with pytest.raises(ValueError, match="non-finite"):
        grasp.ferrari_canny_quality(bad, normals, MU)
    with pytest.raises(ValueError, match="non-finite"):
        grasp.sample_antipodal_grasps(np.array([[0.0, 0, 0], [np.inf, 0, 0]]), mu=MU)


def test_bad_sampling_arguments_raise():
    pts = np.zeros((10, 3))
    pts[:, 0] = np.arange(10) * 0.1
    with pytest.raises(ValueError):
        grasp.sample_antipodal_grasps(pts, mu=MU, n_samples=0)
    with pytest.raises(ValueError):
        grasp.sample_antipodal_grasps(pts, mu=MU, width_max=-1.0)
    with pytest.raises(ValueError):
        grasp.sample_antipodal_grasps(pts, mu=MU, n_samples=-5)


def test_module_exports_match_all():
    for name in grasp.__all__:
        assert hasattr(grasp, name), name
