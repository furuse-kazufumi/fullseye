"""Ground-truth tests for point-cloud segmentation / fitting (pcseg.py).

Every cloud is generated from a known model (plane / sphere / cylinder / box /
separated blobs), so fits and segmentations are checked against the exact
geometry, not merely for plausibility."""
import numpy as np
import pytest

import pcseg


def _plane_basis(n):
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(n, a); u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return n, u, v


def test_fit_plane_tls_recovers_normal():
    n, u, v = _plane_basis([0.2, 0.3, 1.0])
    rng = np.random.default_rng(0)
    st = rng.uniform(-2, 2, (300, 2))
    P = st[:, :1] * u + st[:, 1:] * v + 5.0 * n
    pl = pcseg.fit_plane(P)
    assert min(np.linalg.norm(pl[:3] - n), np.linalg.norm(pl[:3] + n)) < 1e-8
    assert np.abs(pcseg.plane_distance(P, pl)).max() < 1e-8


def test_fit_plane_ransac_rejects_outliers():
    n, u, v = _plane_basis([0.0, 0.0, 1.0])
    rng = np.random.default_rng(1)
    st = rng.uniform(-2, 2, (400, 2))
    inl = st[:, :1] * u + st[:, 1:] * v + 1.0 * n
    out = rng.uniform(-2, 5, (80, 3)) + np.array([0, 0, 3.0])   # off-plane clutter
    P = np.vstack([inl, out])
    plane, mask = pcseg.fit_plane_ransac(P, thresh=0.05, iters=300)
    # all true plane points recovered, few outliers admitted
    assert mask[:400].mean() > 0.98
    assert mask[400:].mean() < 0.2
    assert min(np.linalg.norm(plane[:3] - n), np.linalg.norm(plane[:3] + n)) < 1e-2


def test_fit_sphere_ransac_recovers_center_radius():
    rng = np.random.default_rng(2)
    c0, r0 = np.array([1.0, -2.0, 3.0]), 2.5
    dirs = rng.normal(size=(400, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    P = c0 + r0 * dirs + rng.normal(0, 0.003, (400, 3))
    c, r, inl = pcseg.fit_sphere_ransac(P, thresh=0.03, iters=300)
    assert np.linalg.norm(c - c0) < 0.05
    assert abs(r - r0) < 0.05
    assert inl.mean() > 0.9


def test_fit_cylinder_ransac_recovers_axis_radius():
    rng = np.random.default_rng(3)
    w0 = np.array([0.0, 0.0, 1.0])
    e1, e2 = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
    a0, r0 = np.array([1.0, 1.0, 0.0]), 1.5
    th = rng.uniform(0, 2 * np.pi, 500)
    h = rng.uniform(-2, 2, 500)
    radial = np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2
    P = a0 + r0 * radial + h[:, None] * w0
    N = radial                                     # outward surface normals (exact)
    ax_pt, ax_dir, r, inl = pcseg.fit_cylinder_ransac(P, N, thresh=0.02, iters=400)
    assert abs(abs(ax_dir @ w0) - 1.0) < 1e-3      # axis parallel to z (either sign)
    assert abs(r - r0) < 0.05
    assert inl.mean() > 0.9


def test_height_above_plane_signed_up():
    P = np.array([[0, 0, 0.0], [0, 0, 1.0], [0, 0, 2.0], [1, 1, 0.5]])
    plane = np.array([0.0, 0.0, 1.0, 0.0])         # z = 0
    h = pcseg.height_above_plane(P, plane)
    assert np.allclose(h, [0.0, 1.0, 2.0, 0.5])


def test_remove_ground_keeps_object_drops_floor():
    rng = np.random.default_rng(4)
    floor = np.column_stack([rng.uniform(-3, 3, 800), rng.uniform(-3, 3, 800),
                             rng.normal(0, 0.005, 800)])
    obj = rng.uniform(-0.3, 0.3, (120, 3)) + np.array([0.0, 0.0, 1.0])
    P = np.vstack([floor, obj])
    nonground, gmask = pcseg.remove_ground(P, thresh=0.03)
    assert gmask[:800].mean() > 0.95               # floor removed
    assert gmask[800:].mean() < 0.05               # object kept
    assert nonground.shape[0] == int((~gmask).sum())


def test_remove_ground_ignores_vertical_wall():
    rng = np.random.default_rng(5)
    wall = np.column_stack([rng.normal(0, 0.005, 800), rng.uniform(-3, 3, 800),
                            rng.uniform(0, 3, 800)])            # x ~ 0 plane (vertical)
    nonground, gmask = pcseg.remove_ground(wall, thresh=0.03, max_slope_deg=40.0)
    assert gmask.sum() == 0                          # too steep to be "ground"


def test_euclidean_clusters_separates_two_blobs():
    rng = np.random.default_rng(6)
    a = rng.normal(0, 0.05, (150, 3))
    b = rng.normal(0, 0.05, (150, 3)) + np.array([2.0, 0.0, 0.0])
    P = np.vstack([a, b])
    clusters = pcseg.euclidean_clusters(P, tol=0.2, min_size=20)
    assert len(clusters) == 2
    assert all(c.size >= 100 for c in clusters)


def test_region_growing_splits_two_faces():
    rng = np.random.default_rng(7)
    # horizontal patch (z=0) and vertical patch (x=0) sharing an edge
    horiz = np.column_stack([rng.uniform(0, 2, 300), rng.uniform(-1, 1, 300),
                             np.zeros(300)])
    vert = np.column_stack([np.zeros(300), rng.uniform(-1, 1, 300),
                            rng.uniform(0, 2, 300)])
    P = np.vstack([horiz, vert])
    Nh = np.tile([0.0, 0.0, 1.0], (300, 1))
    Nv = np.tile([1.0, 0.0, 0.0], (300, 1))
    N = np.vstack([Nh, Nv])
    labels = pcseg.region_growing(P, N, angle_deg=15.0, curv_thresh=0.2)
    lab_h = np.bincount(labels[:300] - labels[:300].min())
    # each face is dominated by a single label, and the two faces differ
    top_h = np.bincount(labels[:300]).argmax()
    top_v = np.bincount(labels[300:]).argmax()
    assert (labels[:300] == top_h).mean() > 0.9
    assert (labels[300:] == top_v).mean() > 0.9
    assert top_h != top_v


def test_aabb_exact():
    P = np.array([[0, 0, 0], [1, 2, 3], [-1, 0.5, 2.0]])
    lo, hi = pcseg.aabb(P)
    assert np.allclose(lo, [-1, 0, 0])
    assert np.allclose(hi, [1, 2, 3])


def test_obb_recovers_rotated_box_extents():
    import camera
    rng = np.random.default_rng(8)
    e = np.array([2.0, 1.0, 0.5])
    local = rng.uniform(-e, e, (3000, 3))
    R = camera.rodrigues([0.3, -0.5, 0.2])
    trans = np.array([4.0, -1.0, 2.0])
    P = local @ R.T + trans
    box = pcseg.obb(P)
    assert np.allclose(np.sort(box["extents"]), np.sort(e), atol=0.1)
    assert np.allclose(box["center"], trans, atol=0.1)
    # all points inside the recovered box (projected onto its axes)
    proj = np.abs((P - box["center"]) @ box["axes"])
    assert np.all(proj <= box["extents"] + 1e-6)


def test_crop_box_and_sphere():
    P = np.array([[0, 0, 0], [1, 1, 1], [5, 5, 5], [0.5, 0.5, 0.5]])
    kept, mask = pcseg.crop_box(P, [-0.1, -0.1, -0.1], [1.1, 1.1, 1.1])
    assert mask.tolist() == [True, True, False, True]
    kept2, mask2 = pcseg.crop_sphere(P, [0, 0, 0], 1.0)
    assert mask2.tolist() == [True, False, False, True]


def test_farthest_point_sampling_covers_evenly():
    # FPS minimises the covering radius (max distance from any point to its nearest
    # sample) -- it spreads out, unlike taking the first k points.
    P = np.column_stack([np.arange(100.0), np.zeros(100), np.zeros(100)])
    k = 5
    idx = pcseg.farthest_point_sampling(P, k, seed=0)
    assert len(np.unique(idx)) == k

    def covering_radius(sel):
        from scipy.spatial import cKDTree
        d, _ = cKDTree(P[sel]).query(P, k=1)
        return float(d.max())

    fps_cov = covering_radius(idx)
    naive_cov = covering_radius(np.arange(k))       # first k points: terrible coverage
    assert fps_cov < naive_cov
    assert fps_cov <= 99.0 / (2 * (k - 1)) + 1.0    # ~even spacing bound on a line


def test_curvature_flat_vs_sphere():
    n, u, v = _plane_basis([0.0, 0.0, 1.0])
    rng = np.random.default_rng(9)
    st = rng.uniform(-1, 1, (500, 2))
    flat = st[:, :1] * u + st[:, 1:] * v
    cflat = pcseg.curvature(flat, k=16)
    assert np.median(cflat) < 1e-3
    dirs = rng.normal(size=(500, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    sph = 0.5 * dirs
    csph = pcseg.curvature(sph, k=16)
    assert np.median(csph) > np.median(cflat)


def test_principal_axes_elongated():
    rng = np.random.default_rng(10)
    P = rng.normal(0, [3.0, 0.3, 0.1], (500, 3))
    w, V = pcseg.principal_axes(P)
    assert w[0] > w[1] > w[2]
    assert abs(abs(V[:, 0] @ np.array([1.0, 0, 0])) - 1.0) < 0.1   # long axis ~ x
