"""Extra degenerate/edge-input coverage for the v14 perception stack (tests only —
locks in the graceful-handling contracts across modules)."""
import numpy as np
import pytest

import flow
import stereo
import terrain
import registration as reg
import pointcloud as pc


def test_flow_rejects_color_input():
    color = np.zeros((16, 16, 3))
    with pytest.raises(ValueError):
        flow.optical_flow_lk(color, color)


def test_flow_zero_motion_is_zero():
    img = np.clip(np.random.default_rng(0).random((48, 48)), 0, 1)
    u, v = flow.optical_flow_lk(img, img.copy())
    assert np.abs(u).max() == 0.0 and np.abs(v).max() == 0.0


def test_depth_from_disparity_all_zero_is_inf():
    z = stereo.depth_from_disparity(np.zeros((5, 5)), focal=100.0, baseline=0.1)
    assert np.isinf(z).all()


def test_reproject_drops_all_infinite():
    pts = stereo.reproject_to_points(np.full((4, 4), np.inf))
    assert pts.shape == (0, 3)


def test_disparity_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        stereo.disparity_map(np.zeros((8, 8)), np.zeros((8, 9)))


def test_traversability_all_flat_is_walkable():
    grid = np.zeros((12, 12))
    ok = terrain.traversability(grid, cell=0.05, max_step=0.1, max_slope=0.6)
    assert ok.all()


def test_detect_obstacles_flat_ground_has_none():
    grid = np.zeros((16, 16))
    mask, obs = terrain.detect_obstacles(grid, cell=0.05, clearance=0.12)
    assert not mask.any() and obs == []


def test_icp_identity_is_exact():
    P = np.random.default_rng(1).random((100, 3))
    R, t, aligned, rmse = reg.icp(P, P.copy(), max_iter=5)
    assert rmse < 1e-9
    assert np.allclose(R, np.eye(3), atol=1e-9) and np.allclose(t, 0.0, atol=1e-9)


def test_estimate_normals_minimal_cloud():
    P = np.array([[0., 0, 0], [1., 0, 0], [0., 1, 0], [1., 1, 0]])   # a flat quad
    n = pc.estimate_normals(P, k=4)
    assert n.shape == (4, 3)
    assert np.allclose(np.linalg.norm(n, axis=1), 1.0)
    assert np.abs(n[:, 2]).min() > 0.99                              # normals along z


def test_fpfh_matches_cloud_length():
    P = np.random.default_rng(2).random((40, 3))
    f = pc.fpfh(P, k=8, bins=11)
    assert f.shape == (40, 33) and np.isfinite(f).all()
