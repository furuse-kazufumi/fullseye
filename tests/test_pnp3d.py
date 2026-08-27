"""pnp3d — PnP/DLT 姿勢推定の ground-truth 検証(既知姿勢で投影→復元)。"""
import numpy as np
import pnp3d as P


def _rot(ax, deg):
    a = np.asarray(ax, float); a /= np.linalg.norm(a); th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


_K = np.array([[800.0, 0, 320.0], [0, 800.0, 240.0], [0, 0, 1.0]])


def _scene(seed=0, n=40):
    rng = np.random.default_rng(seed)
    return rng.uniform([-3, -3, -3], [3, 3, 3], (n, 3))


def _rerr(Re, Rg):
    return np.degrees(np.arccos(np.clip((np.trace(Re.T @ Rg) - 1) / 2, -1, 1)))


def test_dlt_recovers_known_pose():
    """既知 R,t で投影 → dlt_pose が姿勢を復元(再投影 ~0)。"""
    X = _scene(0)
    Rg = _rot([0.2, 1, 0.3], 25.0); tg = np.array([0.5, -0.3, 12.0])
    x = P._project(X, _K, Rg, tg)
    R, t = P.dlt_pose(X, x, _K)
    assert _rerr(R, Rg) < 0.1, f"rot err {_rerr(R, Rg):.4f}"
    assert np.linalg.norm(t - tg) < 1e-2, f"t err {np.linalg.norm(t - tg):.5f}"
    assert P.reprojection_error(X, x, _K, R, t) < 1e-3


def test_reprojection_zero_for_true_pose():
    """真の姿勢での再投影誤差はゼロ。"""
    X = _scene(1)
    Rg = _rot([1, 0, 0], 10.0); tg = np.array([0, 0, 10.0])
    x = P._project(X, _K, Rg, tg)
    assert P.reprojection_error(X, x, _K, Rg, tg) < 1e-9


def test_pnp_ransac_with_outliers():
    """2D 対応の 25% を外れ値にしても RANSAC が姿勢を復元。"""
    X = _scene(2, n=60)
    Rg = _rot([0.3, 0.5, 1.0], 30.0); tg = np.array([1.0, 0.5, 14.0])
    x = P._project(X, _K, Rg, tg)
    rng = np.random.default_rng(3)
    n_out = 15
    x_noisy = x.copy()
    x_noisy[:n_out] += rng.uniform(-80, 80, (n_out, 2))  # 外れ値
    R, t, inliers, info = P.pnp_ransac(X, x_noisy, _K, thresh=2.0, iters=400)
    assert _rerr(R, Rg) < 1.0, f"rot err {_rerr(R, Rg):.3f}"
    assert np.linalg.norm(t - tg) < 0.2
    # 外れ値の大半が除外される
    assert inliers[:n_out].sum() <= 2 and inliers[n_out:].sum() >= 40


def test_depth_positive_convention():
    """復元姿勢で全点がカメラ前方(depth>0)。"""
    X = _scene(4)
    Rg = _rot([0, 1, 0], 15.0); tg = np.array([0.2, 0.1, 11.0])
    x = P._project(X, _K, Rg, tg)
    R, t = P.dlt_pose(X, x, _K)
    depth = (R @ X.T).T[:, 2] + t[2]
    assert np.all(depth > 0)


def test_insufficient_points_raises():
    import pytest
    with pytest.raises(ValueError):
        P.dlt_pose(np.zeros((5, 3)), np.zeros((5, 2)), _K)
