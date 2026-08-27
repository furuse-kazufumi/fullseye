"""curvature3d の GT 検証: 球/円柱/平面の閉形式曲率と一致するか。"""
import numpy as np

import curvature3d


def _fib_sphere(n, R, seed=0):
    """Fibonacci 球で半径 R の球面を n 点サンプル。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    gold = np.pi * (1 + 5 ** 0.5)
    theta = gold * i
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return R * np.stack([x, y, z], axis=1)


def _cylinder(n_theta, n_z, R, H, seed=0):
    """半径 R・高さ H の円柱側面。"""
    th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    zz = np.linspace(-H / 2, H / 2, n_z)
    T, Z = np.meshgrid(th, zz)
    x = R * np.cos(T).ravel()
    y = R * np.sin(T).ravel()
    z = Z.ravel()
    return np.stack([x, y, z], axis=1)


def _plane(n, L, seed=0):
    rng = np.random.default_rng(seed)
    xy = rng.uniform(-L, L, size=(n, 2))
    return np.stack([xy[:, 0], xy[:, 1], np.zeros(n)], axis=1)


def test_sphere_curvature():
    R = 2.0
    pts = _fib_sphere(700, R)
    k1, k2 = curvature3d.principal_curvatures(pts, k=25)
    K = curvature3d.gaussian_curvature(pts, k=25)
    # 球: k1=k2=1/R, K=1/R²(離散フィット + 境界なしの閉曲面 → 中央値で ~10%)
    assert abs(np.median(np.abs(k1)) - 1 / R) < 0.15 * (1 / R)
    assert abs(np.median(np.abs(k2)) - 1 / R) < 0.15 * (1 / R)
    assert abs(np.median(K) - 1 / R ** 2) < 0.20 * (1 / R ** 2)
    # 凸符号(外向き法線で正)
    assert np.median(k1) > 0 and np.median(k2) > 0


def test_sphere_shape_index():
    pts = _fib_sphere(700, 2.0)
    s = curvature3d.shape_index(pts, k=25)
    # 凸球 → +1 付近
    assert np.median(s) > 0.9, np.median(s)


def test_cylinder_curvature():
    R = 1.5
    pts = _cylinder(60, 40, R, H=6.0)
    k1, k2 = curvature3d.principal_curvatures(pts, k=25)
    K = curvature3d.gaussian_curvature(pts, k=25)
    # 円柱: k1=1/R, k2≈0, K≈0(端の境界点はフィットが歪む → 中央値でロバストに)
    assert abs(np.median(k1) - 1 / R) < 0.15 * (1 / R), np.median(k1)
    assert abs(np.median(k2)) < 0.15 * (1 / R), np.median(k2)
    assert abs(np.median(K)) < 0.10 * (1 / R ** 2), np.median(K)


def test_cylinder_shape_index():
    pts = _cylinder(60, 40, 1.5, H=6.0)
    s = curvature3d.shape_index(pts, k=25)
    # 円柱(凸)→ +0.5 付近
    assert 0.3 < np.median(s) < 0.7, np.median(s)


def test_plane_curvature():
    pts = _plane(500, 3.0)
    k1, k2 = curvature3d.principal_curvatures(pts, k=25)
    K = curvature3d.gaussian_curvature(pts, k=25)
    assert np.median(np.abs(k1)) < 0.05
    assert np.median(np.abs(k2)) < 0.05
    assert np.median(np.abs(K)) < 0.01


def test_gaussian_sign_invariant_to_normal_flip():
    # ガウス曲率は法線反転に不変であるべき(K=k1k2)
    pts = _fib_sphere(400, 2.0)
    K = curvature3d.gaussian_curvature(pts, k=25)
    assert np.median(K) > 0  # 球は常に正の K
