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


def _reviewer_scene(seed=0, n_cam=4, n_pt=60):
    """4 台 / 60 点(2026-09-02 レビューの再現条件)。→ (cams, pts, oc, op, ouv, K)。"""
    from scipy.spatial.transform import Rotation as Rot
    rng = np.random.default_rng(seed)
    K = np.array([[500.0, 0, 320], [0, 500.0, 240], [0, 0, 1.0]])
    pts = rng.uniform([-1, -1, 4], [1, 1, 8], (n_pt, 3))
    cams = []
    for i in range(n_cam):
        Ri = Rot.from_euler("xyz", [3 * i, -5 * i, 2 * i], degrees=True).as_matrix()
        cams.append(np.concatenate([Rot.from_matrix(Ri).as_rotvec(),
                                    [0.4 * i, 0.05 * i, -0.1 * i]]))
    cams = np.array(cams)
    oc, op, ouv = [], [], []
    for c in range(n_cam):
        proj = B.project(pts, cams[c, :3], cams[c, 3:], K)
        oc += [c] * n_pt; op += list(range(n_pt)); ouv += list(proj)
    return cams, pts, np.array(oc), np.array(op), np.array(ouv), K


def _perturbed(cams, pts, seed=1, sr=0.02, st=0.05, sp=0.05):
    r = np.random.default_rng(seed)
    cams0 = cams + np.concatenate([r.normal(0, sr, (len(cams), 3)),
                                   r.normal(0, st, (len(cams), 3))], 1)
    cams0[0] = cams[0]
    return cams0, pts + r.normal(0, sp, pts.shape)


def test_scale_gauge_is_fixed_exact_observations():
    """Regression (2026-09-02): 再投影誤差は相似変換に不変なので、scale を拘束しない
    LM は rmse≈0 のまま scale を ×0.7..×213 に滑らせていた(cam1 t が真値 0.4 に対し
    -34 など)。構造 RMS 距離を初期値に保つ拘束で、cam1 の並進が真値に戻ること。"""
    cams, pts, oc, op, ouv, K = _reviewer_scene()
    cams0, pts0 = _perturbed(cams, pts)
    out = B.bundle_adjust(cams0, pts0, oc, op, ouv, K)
    assert out["rmse"] < 1e-8, out["rmse"]
    assert np.linalg.norm(out["cameras"][1, 3:] - cams[1, 3:]) < 1e-3, out["cameras"][1, 3:]
    ratio = np.linalg.norm(out["points"], axis=1) / np.linalg.norm(pts, axis=1)
    assert abs(ratio.mean() - 1.0) < 3e-3 and ratio.ptp() < 1e-6      # rigid, not similarity
    assert out["scale_anchor"] is not None
    # the anchor is honoured exactly: RMS point distance from cam-0 centre == initial
    rms_out = np.sqrt(np.mean(np.sum(out["points"] ** 2, axis=1)))
    assert abs(rms_out / out["scale_anchor"] - 1.0) < 1e-9


def test_scale_gauge_is_fixed_under_pixel_noise():
    """0.5 px 観測ノイズでも scale が漂わない: 構造の RMS 距離は真値の 1% 以内、
    かつ拘束(初期 RMS)に厳密に一致する。※ 1 台の短基線(cam1: 基線 0.41 @ 深度 6)の
    並進長は雑音由来の固有不確かさを持つ(実測 2-10%)ので、そこでは判定しない。"""
    cams, pts, oc, op, ouv, K = _reviewer_scene()
    cams0, pts0 = _perturbed(cams, pts)
    ouv_n = ouv + np.random.default_rng(2).normal(0, 0.5, ouv.shape)
    out = B.bundle_adjust(cams0, pts0, oc, op, ouv_n, K)
    assert out["rmse"] < 1.0
    rms_out = np.sqrt(np.mean(np.sum(out["points"] ** 2, axis=1)))
    rms_true = np.sqrt(np.mean(np.sum(pts ** 2, axis=1)))
    assert abs(rms_out / rms_true - 1.0) < 1e-2, rms_out / rms_true
    assert abs(rms_out / out["scale_anchor"] - 1.0) < 1e-6
    # all cameras carry one consistent scale (a similarity of the truth, ~1)
    sc = [np.linalg.norm(out["cameras"][c, 3:]) / np.linalg.norm(cams[c, 3:]) for c in (2, 3)]
    assert all(abs(s - 1.0) < 0.05 for s in sc), sc


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
