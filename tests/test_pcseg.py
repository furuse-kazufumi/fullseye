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


def _blob(seed, n=300, scale=0.5):
    """A gaussian blob + random normals: no sphere and no cylinder in it."""
    rng = np.random.default_rng(seed)
    P = rng.normal(0, scale, (n, 3))
    N = rng.normal(size=(n, 3))
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    return P, N


def test_ransac_rejects_self_supporting_hypotheses():
    # the 4 (sphere) / 2 (cylinder) samples always fit the model they generated, so
    # without a consensus gate every cloud yields a confident-looking fit backed by
    # nothing but its own samples. No model => None, not a meaningless one.
    for seed in range(4):
        P, N = _blob(seed, n=20, scale=1.0)
        assert pcseg.fit_sphere_ransac(P, thresh=1e-6, iters=200, seed=seed) is None
        assert pcseg.fit_cylinder_ransac(P, N, thresh=1e-6, iters=200, seed=seed) is None


def test_ransac_consensus_gate_rejects_blob_keeps_real_shapes():
    # a blob has no primitive in it: demanding that the model explain half the cloud
    # must come back empty-handed ...
    P, N = _blob(0)
    assert pcseg.fit_cylinder_ransac(P, N, thresh=0.01, iters=300,
                                     min_inlier_frac=0.5) is None
    assert pcseg.fit_sphere_ransac(P, thresh=0.01, iters=300,
                                   min_inlier_frac=0.5) is None
    assert pcseg.fit_cylinder_ransac(P, N, thresh=0.01, iters=300,
                                     min_inliers=150) is None

    # ... while the same gate leaves a genuine cylinder / sphere untouched.
    rng = np.random.default_rng(11)
    w0 = np.array([0.0, 0.0, 1.0])
    e1, e2 = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
    th = rng.uniform(0, 2 * np.pi, 500)
    radial = np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2
    Pc = np.array([1.0, 1.0, 0.0]) + 1.5 * radial + rng.uniform(-2, 2, 500)[:, None] * w0
    ax_pt, ax_dir, r, inl = pcseg.fit_cylinder_ransac(Pc, radial, thresh=0.02,
                                                      iters=400, min_inlier_frac=0.5)
    assert abs(r - 1.5) < 0.05 and inl.mean() > 0.9

    dirs = rng.normal(size=(400, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    Ps = np.array([1.0, -2.0, 3.0]) + 2.5 * dirs + rng.normal(0, 0.003, (400, 3))
    c, sr, sinl = pcseg.fit_sphere_ransac(Ps, thresh=0.03, iters=300,
                                          min_inlier_frac=0.5)
    assert abs(sr - 2.5) < 0.05 and sinl.mean() > 0.9


def test_default_consensus_gate_rejects_a_WELL_SCALED_blob():
    # Regression (R1) — HONEST scope: the DEFAULT gate rejects a non-primitive blob
    # only when the cloud is LARGE relative to thresh (extent >> thresh). _blob's
    # default scale=0.5 (~50x thresh) is that regime, and it is correctly rejected.
    for seed in range(4):
        P, N = _blob(seed)                          # 300-pt gaussian blob, extent ~50x thresh
        assert pcseg.fit_sphere_ransac(P, thresh=0.01, iters=300, seed=seed) is None
        assert pcseg.fit_cylinder_ransac(P, N, thresh=0.01, iters=300, seed=seed) is None
    # a genuine sphere still fits with NO opt-in (consensus far above the 10% floor).
    rng = np.random.default_rng(7)
    dirs = rng.normal(size=(400, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    Ps = np.array([0.5, 1.0, -1.0]) + 2.0 * dirs + rng.normal(0, 0.003, (400, 3))
    fit = pcseg.fit_sphere_ransac(Ps, thresh=0.03, iters=300)
    assert fit is not None and abs(fit[1] - 2.0) < 0.05


def test_default_gate_is_weak_on_a_COMPACT_blob_but_opt_in_rejects_it():
    # HONEST disclosure (adversarial review): the 10% default is a scale-dependent
    # heuristic — a COMPACT non-primitive blob (extent ~10x thresh) can still clear it
    # with a plausible small radius. The default therefore does NOT guarantee blob
    # rejection; the escape hatch is a stricter min_inlier_frac. This test pins the
    # ESCAPE HATCH (deterministic), and documents the limitation the default has.
    P, N = _blob(0, scale=0.10)                     # ~10x thresh: the weak regime
    # a stricter demand (30% consensus) rejects it regardless of scale
    assert pcseg.fit_sphere_ransac(P, thresh=0.01, iters=400, min_inlier_frac=0.3) is None
    assert pcseg.fit_cylinder_ransac(P, N, thresh=0.01, iters=400, min_inlier_frac=0.3) is None


def test_consensus_floor_coerces_clamps_and_rejects_non_finite():
    # R5: a float min_inliers is ceiled (not truncated); min_inlier_frac is clamped to
    # [0,1]; and (adversarial review) a non-finite override is rejected fail-closed
    # rather than crashing deep in the fitter with a bare ValueError/OverflowError.
    assert pcseg._consensus_floor(100, 4, 10.9, None) == 11       # ceil, not 10
    assert pcseg._consensus_floor(100, 4, None, 1.5) == 100       # clamped to 1.0 -> all points
    assert pcseg._consensus_floor(100, 4, None, -0.5) == 10       # negative ignored -> default 10%
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            pcseg._consensus_floor(100, 4, bad, None)
        with pytest.raises(ValueError):
            pcseg._consensus_floor(100, 4, None, bad)
    # reachable through the public fitter, and now a clean ValueError:
    rng = np.random.default_rng(1)
    Ps = rng.normal(0, 1.0, (50, 3))
    with pytest.raises(ValueError):
        pcseg.fit_sphere_ransac(Ps, thresh=0.03, iters=20, min_inlier_frac=float("nan"))


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
    assert fps_cov <= 99.0 / (k - 1)                # FPS 2-approximation of optimal spacing


def test_farthest_point_sampling_no_duplicates_with_repeats():
    # a cloud with many duplicate points must still return k DISTINCT indices.
    base = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], float)
    P = np.repeat(base, 10, axis=0)                     # 30 points, only 3 distinct
    idx = pcseg.farthest_point_sampling(P, 5, seed=0)
    assert len(np.unique(idx)) == 5                     # no index picked twice


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
