"""bundle3d の GT 検証: 合成 N 視点で摂動 → BA が再投影 RMSE~0・姿勢を回復。"""
import numpy as np
import pytest

import bundle3d as B


def _rot_angle_deg(Ra, Rb):
    R = Ra.T @ Rb
    c = np.clip((np.trace(R) - 1) / 2, -1, 1)
    return np.rad2deg(np.arccos(c))


def _scene(n_cam=4, n_pt=40, seed=0):
    """合成 N カメラ + 点群 + 全観測。→ (cameras_true(nc,6), points_true(m,3), obs...)。"""
    rng = np.random.default_rng(seed)
    K = np.array([[600.0, 0, 320], [0, 600.0, 240], [0, 0, 1.0]])
    pts = rng.uniform(-1.5, 1.5, size=(n_pt, 3)) + np.array([0, 0, 6.0])
    cams = [np.zeros(6)]                                  # cam0 = [I|0]
    for i in range(1, n_cam):
        rvec = rng.uniform(-0.25, 0.25, 3)
        t = np.array([rng.uniform(-1, 1), rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)])
        cams.append(np.concatenate([rvec, t]))
    cams = np.array(cams)
    oc, op, ouv = [], [], []
    for c in range(n_cam):
        proj = B.project(pts, cams[c, :3], cams[c, 3:], K)
        for j in range(n_pt):
            oc.append(c); op.append(j); ouv.append(proj[j])
    return cams, pts, np.array(oc), np.array(op), np.array(ouv), K


def test_reprojection_zero_at_truth():
    cams, pts, oc, op, ouv, K = _scene()
    rmse = B.mean_reprojection_error(cams, pts, oc, op, ouv, K)
    assert rmse < 1e-9, rmse


def test_bundle_adjust_recovers_from_perturbation():
    cams, pts, oc, op, ouv, K = _scene(seed=1)
    rng = np.random.default_rng(9)
    cams0 = cams.copy()
    cams0[1:, :3] += rng.normal(0, 0.02, cams0[1:, :3].shape)   # 姿勢摂動
    cams0[1:, 3:] += rng.normal(0, 0.05, cams0[1:, 3:].shape)
    pts0 = pts + rng.normal(0, 0.05, pts.shape)                 # 構造摂動
    rmse_init = B.mean_reprojection_error(cams0, pts, oc, op, ouv, K)
    out = B.bundle_adjust(cams0, pts0, oc, op, ouv, K, fix_first=True)
    # 再投影が ~0 に収束(摂動で大きかったものが)
    assert out["rmse"] < 1e-3, (out["rmse"], rmse_init)
    assert out["rmse"] < rmse_init
    # 各カメラの回転が真値に回復(cam0 固定で gauge 除去、scale は回転に無関係)
    for c in range(1, len(cams)):
        ang = _rot_angle_deg(B.rvec_to_R(out["cameras"][c, :3]), B.rvec_to_R(cams[c, :3]))
        assert ang < 0.5, (c, ang)


def test_first_camera_fixed():
    cams, pts, oc, op, ouv, K = _scene(seed=2)
    pts0 = pts + np.random.default_rng(3).normal(0, 0.03, pts.shape)
    out = B.bundle_adjust(cams, pts0, oc, op, ouv, K, fix_first=True)
    # 先頭カメラは初期値のまま固定
    assert np.allclose(out["cameras"][0], cams[0])


def test_guards():
    cams, pts, oc, op, ouv, K = _scene()
    with pytest.raises(ValueError):
        B.bundle_adjust(cams[:1], pts, oc, op, ouv, K)            # <2 カメラ
    with pytest.raises(ValueError):
        B.bundle_adjust(cams, pts, [], [], np.zeros((0, 2)), K)   # 観測空
