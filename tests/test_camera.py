"""Ground-truth tests for pinhole camera geometry (camera.py).

Every scene is synthetic with a *known* camera pose and 3-D structure, so the
recovered geometry is checked against the exact answer rather than for mere
plausibility."""
import numpy as np
import pytest

import camera


# --- synthetic calibrated two-view scene ------------------------------------ #
def _scene(seed=0, n=60):
    rng = np.random.default_rng(seed)
    Xw = rng.uniform(-1.0, 1.0, (n, 3))
    Xw[:, 2] += 6.0                                   # push in front of both cameras
    K = camera.intrinsic_matrix(600.0, 600.0, 320.0, 240.0)
    R = camera.rodrigues(np.array([0.04, -0.09, 0.02]))
    t = np.array([-1.2, 0.15, 0.25])
    uv1, z1 = camera.project_points(Xw, K)            # camera 1 = identity pose
    uv2, z2 = camera.project_points(Xw, K, R, t)      # camera 2 = (R, t)
    return {"Xw": Xw, "K": K, "R": R, "t": t,
            "uv1": uv1, "uv2": uv2, "z1": z1, "z2": z2}


def test_intrinsic_roundtrip():
    K = camera.intrinsic_matrix(500.0, 450.0, 320.0, 240.0, skew=0.3)
    d = camera.decompose_intrinsics(K)
    assert d == {"fx": 500.0, "fy": 450.0, "cx": 320.0, "cy": 240.0, "skew": 0.3}


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_rodrigues_log_roundtrip(seed):
    rng = np.random.default_rng(seed)
    rvec = rng.uniform(-np.pi, np.pi, 3)
    R = camera.rodrigues(rvec)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-9)      # orthonormal
    assert np.isclose(np.linalg.det(R), 1.0)               # proper rotation
    R2 = camera.rodrigues(camera.rotation_log(R))
    assert np.allclose(R, R2, atol=1e-9)                   # log is the inverse


def test_rodrigues_log_near_180():
    R = camera.rodrigues(np.array([np.pi, 0.0, 0.0]))
    back = camera.rotation_log(R)
    assert np.allclose(camera.rodrigues(back), R, atol=1e-6)


def test_project_backproject_roundtrip():
    s = _scene()
    uv, z = camera.project_points(s["Xw"], s["K"], s["R"], s["t"])
    Xc = s["Xw"] @ s["R"].T + s["t"]
    rec = camera.backproject(uv, z, s["K"])
    assert np.allclose(rec, Xc, atol=1e-8)


def test_depth_to_points_recovers_plane():
    K = camera.intrinsic_matrix(400.0, 400.0, 160.0, 120.0)
    H, W = 60, 80
    Z = np.full((H, W), 5.0)
    Z[0, 0] = -1.0                                         # invalid -> dropped
    Z[1, 1] = np.inf
    pts = camera.depth_to_points(Z, K)
    assert pts.shape == (H * W - 2, 3)
    assert np.allclose(pts[:, 2], 5.0)
    org = camera.depth_to_points(Z, K, organized=True)
    assert org.shape == (H, W, 3)
    assert np.isnan(org[0, 0]).all() and np.isnan(org[1, 1]).all()


def test_normals_from_depth_frontoparallel():
    K = camera.intrinsic_matrix(400.0, 400.0, 160.0, 120.0)
    Z = np.full((40, 50), 4.0)
    n = camera.normals_from_depth(Z, K)
    core = n[2:-2, 2:-2]
    assert np.allclose(core, np.array([0.0, 0.0, -1.0]), atol=1e-6)


def test_normals_from_depth_tilted_plane_exact():
    # a tilted plane n.X = d in the camera frame; central differences of on-plane
    # points are in-plane, so their cross product is the exact plane normal.
    K = camera.intrinsic_matrix(400.0, 400.0, 160.0, 120.0)
    H, W = 60, 80
    nrm = np.array([0.25, -0.15, -1.0]); nrm /= np.linalg.norm(nrm)
    d = 5.0 * nrm[2]                                       # depth 5 at principal point
    v, u = np.mgrid[0:H, 0:W].astype(float)
    x = (u - 160.0) / 400.0
    y = (v - 120.0) / 400.0
    denom = nrm[0] * x + nrm[1] * y + nrm[2]
    Z = d / denom
    got = camera.normals_from_depth(Z, K)
    core = got[3:-3, 3:-3].reshape(-1, 3)
    assert np.allclose(core, nrm, atol=1e-6)


def test_triangulate_recovers_structure():
    s = _scene()
    P1 = camera.projection_matrix(s["K"])
    P2 = camera.projection_matrix(s["K"], s["R"], s["t"])
    X = camera.triangulate(s["uv1"], s["uv2"], P1, P2)
    assert np.allclose(X, s["Xw"], atol=1e-6)


def test_solve_pnp_recovers_pose_clean():
    s = _scene()
    R, t, rms = camera.solve_pnp(s["Xw"], s["uv2"], s["K"])
    assert rms < 1e-3
    assert np.allclose(R, s["R"], atol=1e-4)
    assert np.allclose(t, s["t"], atol=1e-4)


def test_solve_pnp_planar_target():
    # a coplanar (checkerboard-style) target: general DLT resection is degenerate
    # here, so the planar homography init must carry it. 5x5 grid on z=0.
    K = camera.intrinsic_matrix(600.0, 600.0, 320.0, 240.0)
    gx, gy = np.meshgrid(np.linspace(-0.1, 0.1, 5), np.linspace(-0.1, 0.1, 5))
    X = np.column_stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)])
    fails = 0
    for seed in range(20):
        rng = np.random.default_rng(seed)
        R_true = camera.rodrigues(rng.uniform(-0.6, 0.6, 3))
        t_true = np.array([rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 1.5])
        uv, z = camera.project_points(X, K, R_true, t_true)
        if (z <= 0).any():
            continue
        R, t, rms = camera.solve_pnp(X, uv, K)
        ang = np.degrees(np.linalg.norm(camera.rotation_log(R @ R_true.T)))
        if ang > 1.0 or rms > 1e-2:
            fails += 1
    assert fails == 0, f"{fails}/20 planar-target PnP recoveries failed"


def test_solve_pnp_robust_to_noise():
    s = _scene(seed=5)
    rng = np.random.default_rng(9)
    noisy = s["uv2"] + rng.normal(0.0, 0.3, s["uv2"].shape)
    R, t, rms = camera.solve_pnp(s["Xw"], noisy, s["K"])
    # sub-pixel noise -> pose within a fraction of a degree / cm, small residual
    assert rms < 1.0
    ang = np.degrees(np.linalg.norm(camera.rotation_log(R @ s["R"].T)))
    assert ang < 1.5
    assert np.linalg.norm(t - s["t"]) < 0.1


def test_fundamental_satisfies_epipolar_constraint():
    s = _scene()
    F = camera.fundamental_matrix(s["uv1"], s["uv2"])
    x1 = np.hstack([s["uv1"], np.ones((s["uv1"].shape[0], 1))])
    x2 = np.hstack([s["uv2"], np.ones((s["uv2"].shape[0], 1))])
    err = np.abs(np.einsum("ni,ij,nj->n", x2, F, x1))
    assert err.max() < 1e-6


def test_epipolar_lines_pass_through_matches():
    s = _scene()
    F = camera.fundamental_matrix(s["uv1"], s["uv2"])
    l2 = camera.epipolar_lines(F, s["uv1"], which=2)
    x2 = np.hstack([s["uv2"], np.ones((s["uv2"].shape[0], 1))])
    assert np.abs((x2 * l2).sum(1)).max() < 1e-6         # points lie on their lines
    assert np.allclose(np.hypot(l2[:, 0], l2[:, 1]), 1.0)  # normalized


def test_recover_pose_from_essential():
    s = _scene()
    E = camera.essential_matrix(s["uv1"], s["uv2"], s["K"])
    R, t, mask = camera.recover_pose(E, s["uv1"], s["uv2"], s["K"])
    assert mask.mean() > 0.9                              # most points in front
    assert np.allclose(R, s["R"], atol=1e-3)
    # t is recovered up to positive scale -> compare unit directions
    assert np.allclose(t, s["t"] / np.linalg.norm(s["t"]), atol=1e-3)


def test_essential_from_fundamental_matches_direct():
    s = _scene()
    F = camera.fundamental_matrix(s["uv1"], s["uv2"])
    E1 = camera.essential_from_fundamental(F, s["K"])
    E2 = camera.essential_matrix(s["uv1"], s["uv2"], s["K"])
    # equal up to scale and sign -> normalize by Frobenius norm and align sign
    E1 = E1 / np.linalg.norm(E1)
    E2 = E2 / np.linalg.norm(E2)
    diff = min(np.linalg.norm(E1 - E2), np.linalg.norm(E1 + E2))
    assert diff < 1e-3


@pytest.mark.parametrize("dist", [
    [0.1, -0.05, 0.0, 0.0],
    [-0.2, 0.1, 0.001, -0.002],
    [0.15, -0.03, 0.0005, 0.0008, 0.01],
])
def test_distort_undistort_roundtrip(dist):
    K = camera.intrinsic_matrix(500.0, 500.0, 320.0, 240.0)
    rng = np.random.default_rng(3)
    uv = rng.uniform([40, 40], [600, 440], (200, 2))
    dd = camera.distort_points(uv, K, dist)
    back = camera.undistort_points(dd, K, dist, iters=20)
    assert np.allclose(back, uv, atol=1e-3)


def test_stereo_rectify_identity_for_rectified_pair():
    K = camera.intrinsic_matrix(600.0, 600.0, 320.0, 240.0)
    R = np.eye(3)
    t = np.array([-1.0, 0.0, 0.0])                       # pure horizontal baseline
    R1, R2, Knew = camera.stereo_rectify(K, K, R, t)
    assert np.allclose(R1, np.eye(3), atol=1e-9)
    assert np.allclose(R2, np.eye(3), atol=1e-9)
    assert np.allclose(Knew, K)


def test_stereo_rectify_row_aligns_general_pair():
    s = _scene(seed=2)
    K = s["K"]
    R1, R2, Knew = camera.stereo_rectify(K, K, s["R"], s["t"])
    H1 = Knew @ R1 @ np.linalg.inv(K)
    H2 = Knew @ R2 @ np.linalg.inv(K)

    def warp(uv, H):
        x = np.hstack([uv, np.ones((uv.shape[0], 1))]) @ H.T
        return x[:, :2] / x[:, 2:3]

    r1 = warp(s["uv1"], H1)
    r2 = warp(s["uv2"], H2)
    # corresponding points share the same rectified row (horizontal epipolar lines)
    assert np.abs(r1[:, 1] - r2[:, 1]).max() < 1e-6
