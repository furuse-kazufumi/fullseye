"""Ground-truth tests for visual/RGB-D odometry (odometry.py).

Scenes have a known camera motion by construction (a fronto-parallel plane under a
known lateral translation or optical-axis roll, so depth/flow are analytically
consistent), and the trajectory utilities are checked against exact composed poses
and a known similarity transform."""
import numpy as np

import odometry
import camera


def test_rgbd_odometry_lateral_translation():
    # fronto-parallel plane at depth Z; camera translates so points move by -dx in
    # the camera frame -> uniform flow, unchanged depth. Recover t = [-dx, 0, 0].
    K = camera.intrinsic_matrix(400.0, 400.0, 80.0, 60.0)
    H, W = 120, 160
    Z, dx = 4.0, 0.3
    Z0 = np.full((H, W), Z)
    Z1 = np.full((H, W), Z)
    u = np.full((H, W), -400.0 * dx / Z)             # fx*(-dx)/Z, constant
    v = np.zeros((H, W))
    R, t, inl = odometry.rgbd_odometry(Z0, Z1, u, v, K, thresh=0.01, stride=4)
    assert inl > 0.9
    assert np.allclose(R, np.eye(3), atol=1e-6)
    assert np.allclose(t, [-dx, 0.0, 0.0], atol=1e-3)


def test_rgbd_odometry_roll():
    # camera rolls by theta about the optical axis of a fronto-parallel plane:
    # camera-frame points rotate by Rz(-theta), depth (z) is preserved.
    K = camera.intrinsic_matrix(400.0, 400.0, 80.0, 60.0)
    H, W = 120, 160
    Z, theta = 4.0, np.radians(5.0)
    Rpt = camera.rodrigues([0.0, 0.0, -theta])       # scene-point motion in the frame
    v_, u_ = np.mgrid[0:H, 0:W].astype(float)
    p0 = np.stack([u_.ravel(), v_.ravel()], 1)
    X0 = camera.backproject(p0, Z, K)
    X1 = X0 @ Rpt.T
    p1, _ = camera.project_points(X1, K)             # identity pose = same camera
    u = (p1[:, 0] - p0[:, 0]).reshape(H, W)
    v = (p1[:, 1] - p0[:, 1]).reshape(H, W)
    Z0 = np.full((H, W), Z)
    Z1 = np.full((H, W), Z)                           # roll about z keeps the plane at Z
    R, t, inl = odometry.rgbd_odometry(Z0, Z1, u, v, K, thresh=0.01, stride=3)
    ang = np.degrees(np.linalg.norm(camera.rotation_log(R @ Rpt.T)))
    assert inl > 0.8
    assert ang < 1.0
    assert np.linalg.norm(t) < 0.02


def test_umeyama_recovers_similarity():
    rng = np.random.default_rng(0)
    src = rng.normal(size=(50, 3))
    s_true, R_true, t_true = 2.3, camera.rodrigues([0.2, -0.4, 0.1]), np.array([1.0, -2.0, 0.5])
    dst = s_true * (src @ R_true.T) + t_true
    s, R, t = odometry.umeyama_align(src, dst)
    assert abs(s - s_true) < 1e-6
    assert np.allclose(R, R_true, atol=1e-6)
    assert np.allclose(t, t_true, atol=1e-6)


def test_integrate_trajectory_composes():
    R = camera.rodrigues([0.0, 0.0, 0.1])
    t = np.array([0.5, 0.0, 0.0])
    traj = odometry.integrate_trajectory([(R, t)] * 3)
    assert traj.shape == (4, 4, 4)
    assert np.allclose(traj[0], np.eye(4))
    expect = np.linalg.matrix_power(odometry._to_4x4(R, t), 3)
    assert np.allclose(traj[-1], expect, atol=1e-9)


def test_trajectory_error_zero_and_aligned():
    rng = np.random.default_rng(1)
    gt_xyz = np.cumsum(rng.normal(0, 0.1, (30, 3)), axis=0)
    gt = np.stack([odometry._to_4x4(np.eye(3), p) for p in gt_xyz])
    same = odometry.trajectory_error(gt, gt)
    assert same["rmse"] < 1e-9
    # rigidly transform the estimate; ATE after alignment should be ~0
    Rg = camera.rodrigues([0.3, 0.1, -0.2]); tg = np.array([5.0, -1.0, 2.0])
    est_xyz = gt_xyz @ Rg.T + tg
    est = np.stack([odometry._to_4x4(np.eye(3), p) for p in est_xyz])
    err = odometry.trajectory_error(est, gt, align=True)
    assert err["rmse"] < 1e-6


def test_pnp_odometry_wraps_solve_pnp():
    s_rng = np.random.default_rng(2)
    X = s_rng.uniform(-1, 1, (40, 3)); X[:, 2] += 6
    K = camera.intrinsic_matrix(600.0, 600.0, 320.0, 240.0)
    R_true = camera.rodrigues([0.05, -0.1, 0.03]); t_true = np.array([-0.5, 0.1, 0.2])
    uv, _ = camera.project_points(X, K, R_true, t_true)
    R, t, rms = odometry.pnp_odometry(X, uv, K)
    assert rms < 1e-3
    assert np.allclose(R, R_true, atol=1e-4) and np.allclose(t, t_true, atol=1e-4)
