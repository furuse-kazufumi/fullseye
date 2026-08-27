"""twoview の GT 検証: 合成 2 カメラで投影 → F 拘束・相対姿勢・三角測量を閉形式で確認。"""
import numpy as np
import pytest

import twoview


def _rot(axis, deg):
    """軸(単位)まわり deg 度の回転行列(Rodrigues)。"""
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    th = np.deg2rad(deg)
    K = np.array([[0, -axis[2], axis[1]],
                  [axis[2], 0, -axis[0]],
                  [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def _rot_angle_deg(Ra, Rb):
    """2 回転行列間の角度差(度)。"""
    R = Ra.T @ Rb
    c = np.clip((np.trace(R) - 1) / 2, -1, 1)
    return np.rad2deg(np.arccos(c))


def _scene(n=30, seed=0):
    """合成 2 カメラ + 前方 3D 点。→ (X, pts1, pts2, K, R_true, t_true)。"""
    rng = np.random.default_rng(seed)
    K = np.array([[800.0, 0, 320], [0, 800.0, 240], [0, 0, 1.0]])
    R_true = _rot([0.2, 1.0, 0.1], 18.0)
    t_true = np.array([1.0, 0.15, 0.1])          # baseline(スケールは任意)
    # 両カメラ前方の点だけ集める
    X = []
    while len(X) < n:
        p = np.array([rng.uniform(-2, 2), rng.uniform(-2, 2), rng.uniform(4, 9)])
        z2 = (R_true @ p + t_true)[2]
        if p[2] > 0.5 and z2 > 0.5:
            X.append(p)
    X = np.array(X)
    P1, P2 = twoview._projection_matrices(R_true, t_true, K, K)
    h1 = (P1 @ np.hstack([X, np.ones((len(X), 1))]).T).T
    h2 = (P2 @ np.hstack([X, np.ones((len(X), 1))]).T).T
    pts1 = h1[:, :2] / h1[:, 2:3]
    pts2 = h2[:, :2] / h2[:, 2:3]
    return X, pts1, pts2, K, R_true, t_true


def test_fundamental_epipolar_constraint():
    _, pts1, pts2, _, _, _ = _scene(n=30)
    F = twoview.fundamental_8point(pts1, pts2)
    # ノイズ無しなら Sampson 距離 ~0
    d = twoview.sampson_distance(F, pts1, pts2)
    assert np.max(d) < 1e-6, f"sampson max={np.max(d)}"


def test_triangulate_exact_with_true_pose():
    X, pts1, pts2, K, R, t = _scene(n=20)
    P1, P2 = twoview._projection_matrices(R, t, K, K)
    Xr = twoview.triangulate(pts1, pts2, P1, P2)
    assert np.max(np.linalg.norm(Xr - X, axis=1)) < 1e-6


def test_recover_pose_rotation_and_translation_direction():
    X, pts1, pts2, K, R_true, t_true = _scene(n=40)
    R_est, t_est, Xr = twoview.recover_pose(pts1, pts2, K)
    # 回転は絶対的に一致(<1°)
    assert _rot_angle_deg(R_est, R_true) < 1.0, _rot_angle_deg(R_est, R_true)
    # 並進はスケール不定 → 方向のみ(cheirality で符号も確定するはず)
    u_est = t_est / np.linalg.norm(t_est)
    u_true = t_true / np.linalg.norm(t_true)
    assert np.dot(u_est, u_true) > 0.999, np.dot(u_est, u_true)
    # 復元 3D は両カメラ前方
    z2 = ((R_est @ Xr.T).T + t_est)[:, 2]
    assert np.all(Xr[:, 2] > 0) and np.all(z2 > 0)


def test_recovered_structure_reprojects():
    _, pts1, pts2, K, _, _ = _scene(n=40)
    R_est, t_est, Xr = twoview.recover_pose(pts1, pts2, K)
    P1, P2 = twoview._projection_matrices(R_est, t_est, K, K)
    h1 = (P1 @ np.hstack([Xr, np.ones((len(Xr), 1))]).T).T
    h2 = (P2 @ np.hstack([Xr, np.ones((len(Xr), 1))]).T).T
    r1 = h1[:, :2] / h1[:, 2:3]
    r2 = h2[:, :2] / h2[:, 2:3]
    # スケール不定でも同じ姿勢が説明する → 再投影は元画素と一致
    assert np.max(np.linalg.norm(r1 - pts1, axis=1)) < 1e-3
    assert np.max(np.linalg.norm(r2 - pts2, axis=1)) < 1e-3


def test_min_points_guard():
    with pytest.raises(ValueError):
        twoview.fundamental_8point(np.zeros((5, 2)), np.zeros((5, 2)))
