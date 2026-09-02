"""calib.camera_calibration: (row, col) image-point convention, exact recovery on
synthetic views, and fail-closed behaviour on degenerate input.

Regression for the 2026-09-02 finding: image points were treated as (x, y) while
every sibling API is (row, col), silently swapping fx<->fy and cx<->cy.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import calib  # noqa: E402

K_TRUE = {"fx": 800.0, "fy": 600.0, "cx": 320.0, "cy": 240.0}


def _rotm(rx, ry, rz):
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _pose(rx, ry, rz, t):
    T = np.eye(4)
    T[:3, :3] = _rotm(rx, ry, rz)
    T[:3, 3] = t
    return T


def _target():
    r, c = np.mgrid[0:7, 0:7]
    xy = np.column_stack([c.ravel() * 10.0, r.ravel() * 10.0])     # (x, y) mm
    xy -= xy.mean(0)
    return xy


POSES = [_pose(0.3, -0.2, 0.1, [5, -3, 400]), _pose(-0.25, 0.35, -0.4, [-10, 8, 450]),
         _pose(0.15, 0.15, 0.9, [0, 0, 380]), _pose(-0.4, -0.1, 0.3, [12, -4, 420])]


def _views(poses, K=K_TRUE):
    xy = _target()
    world = np.column_stack([xy, np.zeros(len(xy))])
    return xy, [calib.project_3d_point(world, K, P) for P in poses]      # (row, col)


def test_row_col_image_points_recover_asymmetric_intrinsics_exactly():
    xy, views = _views(POSES)
    K = calib.camera_calibration(xy, views)
    for k in ("fx", "fy", "cx", "cy"):
        assert abs(K[k] - K_TRUE[k]) < 1e-3, (k, K[k])
    assert abs(K["skew"]) < 1e-3
    assert max(K["reproj_rms"]) < 1e-6


def test_xy_image_points_would_swap_axes():
    """Documented consequence: feeding (x, y) instead of (row, col) swaps fx/fy, cx/cy."""
    xy, views = _views(POSES)
    K = calib.camera_calibration(xy, [v[:, ::-1] for v in views])
    assert abs(K["fx"] - 600) < 1e-3 and abs(K["fy"] - 800) < 1e-3
    assert abs(K["cx"] - 240) < 1e-3 and abs(K["cy"] - 320) < 1e-3


def test_noisy_views_stay_close():
    rng = np.random.default_rng(0)
    xy, views = _views(POSES)
    K = calib.camera_calibration(xy, [v + rng.normal(0, 0.2, v.shape) for v in views])
    assert abs(K["fx"] - 800) < 8 and abs(K["fy"] - 600) < 8
    assert abs(K["cx"] - 320) < 8 and abs(K["cy"] - 240) < 8
    assert 0.05 < max(K["reproj_rms"]) < 1.0


def test_fewer_than_three_views_raises():
    xy, views = _views(POSES)
    with pytest.raises(ValueError, match="3 views"):
        calib.camera_calibration(xy, views[:2])


def test_fronto_parallel_views_raise_instead_of_nan():
    fp = [_pose(0, 0, 0, [0, 0, 400]), _pose(0, 0, 0, [10, 5, 450]), _pose(0, 0, 0.3, [0, 0, 500])]
    xy, views = _views(fp)
    with pytest.raises(ValueError, match="degenerate"):
        calib.camera_calibration(xy, views)


def test_mismatched_point_counts_raise():
    xy, views = _views(POSES)
    with pytest.raises(ValueError):
        calib.camera_calibration(xy, [views[0][:-1], views[1], views[2]])


def test_project_point_hom_mat3d_matches_project_3d_point_row_col():
    xy = _target()
    world = np.column_stack([xy, np.zeros(len(xy))])
    P = POSES[0]
    Kmat = calib._K(K_TRUE)
    proj = Kmat @ P[:3]
    a = calib.project_3d_point(world, K_TRUE, P)
    b = calib.project_point_hom_mat3d(world, proj)
    c = calib.project_hom_point_hom_mat3d(np.column_stack([world, np.ones(len(world))]), proj)
    assert np.allclose(a, b) and np.allclose(a, c)
