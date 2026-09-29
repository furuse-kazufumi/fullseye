"""drivettc(τ 理論の衝突までの時間、世界の真値で採点)の門。

固定する性質:
- 逆投影 → 投影は恒等(render3d の規約: −Z が前、画素中心は整数座標)、driveworld.world_project_points と一致
- 恒等式: 純並進の真の流れを time_to_contact に入れると τ₀ = ttc_truth と 1e-9 で一致(1 コマの補正込み)
- 等速なら dτ/dt = −1(次のコマの τ はちょうど Δt 小さい)
- 大きさから: w ∝ 1/Z なら閉形式が厳密 / 距離から: d / v
- FoE: 前進なら主点、横滑りは nan、回転は ValueError
- 描画器との整合: 世界を描いて 1 コマ動かし、真の流れで写した先の深度が描き直した深度と一致(車の画素)
- fail-closed: 形の悪い K / T / dt ≤ 0 / 幅 ≤ 0
"""
import math

import numpy as np
import pytest

import drivettc as TT


def _K(fx=300.0, w=64, h=40):
    return np.array([[fx, 0, (w - 1) / 2], [0, fx, (h - 1) / 2], [0, 0, 1.0]])


def _translation(t):
    T = np.eye(4)
    T[:3, 3] = t
    return T


def test_backproject_then_project_is_identity():
    rng = np.random.default_rng(0)
    K = _K()
    Z = rng.uniform(2.0, 40.0, (40, 64))
    Z[3, 5] = np.nan
    Z[7, 9] = 0.0
    P = TT.camera_backproject(Z, K)
    col, row, d = TT.camera_project(P, K)
    rr, cc = np.mgrid[0:40, 0:64]
    ok = np.isfinite(Z) & (Z > 0)
    assert np.allclose(col[ok], cc[ok], atol=1e-9)
    assert np.allclose(row[ok], rr[ok], atol=1e-9)
    assert np.allclose(d[ok], Z[ok])
    assert np.isnan(P[3, 5]).all() and np.isnan(P[7, 9]).all()
    assert np.all(P[ok][:, 2] < 0)                       # 前は −Z


def test_matches_driveworld_projection_through_a_pose():
    import driveworld as DW
    rng = np.random.default_rng(1)
    K = _K()
    pose = DW.camera_pose((1.0, -2.0, 1.4), (20.0, 3.0, 0.5))
    Z = rng.uniform(3.0, 30.0, (40, 64))
    Pc = TT.camera_backproject(Z, K).reshape(-1, 3)
    Pw = (Pc - pose[:3, 3]) @ pose[:3, :3]              # camera → world(R は直交)
    col, row, d = DW.world_project_points(Pw, pose, K)
    rr, cc = np.mgrid[0:40, 0:64]
    assert np.allclose(col, cc.ravel(), atol=1e-8)
    assert np.allclose(row, rr.ravel(), atol=1e-8)
    assert np.allclose(d, Z.ravel())


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_tau_from_true_flow_equals_truth_to_1e_9(seed):
    """純並進では r² / (Δr · r) = Z₁/(Z₀ − Z₁) コマ → 1 コマ足すと Z₀/(Z₀ − Z₁) = 真の τ₀。"""
    rng = np.random.default_rng(seed)
    K = _K()
    Z = rng.uniform(5.0, 40.0, (40, 64))
    dt = 0.1
    v = np.array([rng.uniform(-2, 2), rng.uniform(-1, 1), rng.uniform(4, 12)])   # camera 系の相対速度(+z = 近づく)
    T = _translation(v * dt)
    f = TT.flow_from_depth_motion(Z, K, T)
    truth = TT.ttc_truth(Z, K, T, dt)
    foe = TT.foe_from_motion(K, T)
    est = TT.ttc_from_flow(f["u"], f["v"], dt, foe=foe)
    ok = f["valid"] & np.isfinite(truth["tau"])
    assert ok.mean() > 0.95
    assert np.max(np.abs(est["tau_map"][ok] - truth["tau"][ok]) / truth["tau"][ok]) < 1e-9
    assert np.allclose(truth["closing_speed"][ok], v[2])
    # 2 コマ目の τ はちょうど Δt 小さい(等速: dτ/dt = −1)
    est1 = TT.ttc_from_flow(f["u"], f["v"], dt, foe=foe, at_first_frame=False)
    assert np.allclose(truth["tau"][ok] - est1["tau_map"][ok], dt, atol=1e-9)


def test_next_frame_tau_is_dt_smaller_with_the_next_depth():
    rng = np.random.default_rng(5)
    K = _K()
    Z = rng.uniform(5.0, 40.0, (40, 64))
    dt, v = 0.05, 8.0
    T = _translation([0, 0, v * dt])
    t0 = TT.ttc_truth(Z, K, T, dt)
    t1 = TT.ttc_truth(t0["depth1"], K, T, dt)
    ok = t0["valid"] & t1["valid"]
    assert np.allclose(t0["tau"][ok] - t1["tau"][ok], dt, atol=1e-9)
    assert np.allclose(t0["tau"][ok], Z[ok] / v)


def test_estimated_foe_from_true_flow_matches_the_projected_heading():
    import sceneflow
    rng = np.random.default_rng(3)
    K = _K(fx=200.0, w=96, h=64)
    Z = rng.uniform(5.0, 40.0, (64, 96))
    T = _translation([0.3, -0.1, 0.8])
    f = TT.flow_from_depth_motion(Z, K, T)
    foe = TT.foe_from_motion(K, T)
    est = sceneflow.focus_of_expansion(np.nan_to_num(f["u"]), np.nan_to_num(f["v"]))
    assert np.hypot(est[0] - foe[0], est[1] - foe[1]) < 1e-6


def test_foe_special_cases():
    K = _K()
    foe = TT.foe_from_motion(K, _translation([0, 0, 1.0]))
    assert np.allclose(foe, [K[0, 2], K[1, 2]])            # 真っ直ぐ前 = 主点
    assert np.isnan(TT.foe_from_motion(K, _translation([1.0, 0, 0]))).all()
    R = np.eye(4)
    c, s = math.cos(0.01), math.sin(0.01)
    R[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    with pytest.raises(ValueError):
        TT.foe_from_motion(K, R)


def test_scale_and_range_closed_forms():
    Z0, Z1, dt = 20.0, 18.0, 0.1
    w0, w1 = 100.0 / Z0, 100.0 / Z1                       # w ∝ 1/Z
    assert abs(TT.ttc_from_scale(w0, w1, dt) - Z0 * dt / (Z0 - Z1)) < 1e-12
    assert TT.ttc_from_scale(5.0, 5.0, dt) == float("inf")
    assert TT.ttc_from_range(20.0, 16.0) == 1.25
    assert TT.ttc_from_range(20.0, 0.0) == float("inf")
    with pytest.raises(ValueError):
        TT.ttc_from_scale(0.0, 1.0, dt)
    with pytest.raises(ValueError):
        TT.ttc_from_range(-1.0, 1.0)


def test_label_extent():
    L = np.zeros((10, 12), int)
    L[2:5, 3:9] = 2
    e = TT.label_extent(L, 2)
    assert (e["col0"], e["col1"], e["row0"], e["row1"], e["width"], e["height"], e["n"]) == (3, 8, 2, 4, 6, 3, 18)
    assert TT.label_extent(L, 7)["n"] == 0


def test_flow_from_depth_motion_marks_points_that_leave_the_view():
    K = _K()
    Z = np.full((40, 64), 3.0)
    f = TT.flow_from_depth_motion(Z, K, _translation([0, 0, 3.5]))     # 全部カメラの背後へ
    assert not f["valid"].any() and np.isnan(f["u"]).all()
    f = TT.flow_from_depth_motion(Z, K, _translation([0, 0, 1.0]))
    assert f["valid"].all()
    rr, cc = np.mgrid[0:40, 0:64]
    # 前進なら流れは主点から外向き
    assert np.all(f["u"] * (cc - K[0, 2]) >= -1e-12) and np.all(f["v"] * (rr - K[1, 2]) >= -1e-12)


def test_ttc_from_flow_mask_and_median():
    K = _K()
    Z = np.full((40, 64), 10.0)
    dt = 0.1
    T = _translation([0, 0, 1.0])
    f = TT.flow_from_depth_motion(Z, K, T)
    m = np.zeros((40, 64), bool)
    m[10:20, 10:30] = True
    est = TT.ttc_from_flow(f["u"], f["v"], dt, foe=TT.foe_from_motion(K, T), mask=m)
    assert abs(est["tau"] - 1.0) < 1e-9 and est["n"] == 200
    with pytest.raises(ValueError):
        TT.ttc_from_flow(f["u"], f["v"], dt, mask=np.zeros((3, 3), bool))
    with pytest.raises(ValueError):
        TT.ttc_from_flow(f["u"], f["v"], 0.0)


def test_rendered_world_moved_one_frame_agrees_with_the_true_flow():
    """世界を描き、カメラを 1 コマ進めて描き直す: 真の流れで写した先の深度 = 描き直した深度(車の画素)。"""
    import drivecourse as DC
    import driveworld as DW
    W = DW.world_build(DC.course_road(40.0, 7.0), props=[("sedan", 14.0, 1.75, math.pi)])
    K = DW.camera_intrinsics(60.0, 160, 100)
    dt, v = 0.1, 8.0
    p0 = DW.camera_pose((2.0, 1.75, 1.35), (22.0, 1.75, 0.9))
    p1 = DW.camera_pose((2.0 + v * dt, 1.75, 1.35), (22.0 + v * dt, 1.75, 0.9))
    c0 = DW.world_camera(W, p0, K, 160, 100)
    c1 = DW.world_camera(W, p1, K, 160, 100)
    T = TT.relative_motion(p0, p1)
    assert np.allclose(T[:3, :3], np.eye(3), atol=1e-12)          # 直進はカメラ系でも純並進
    f = TT.flow_from_depth_motion(c0["depth"], K, T)
    car = (c0["label"] == 2) & f["valid"]
    assert car.sum() > 50
    rr, cc = np.mgrid[0:100, 0:160]
    r1 = np.clip(np.rint(rr[car] + f["v"][car]).astype(int), 0, 99)
    c1_ = np.clip(np.rint(cc[car] + f["u"][car]).astype(int), 0, 159)
    d_pred = f["depth1"][car]
    d_seen = c1["depth"][r1, c1_]
    rel = np.abs(d_pred - d_seen) / d_pred
    assert np.median(rel) < 0.01
    assert np.mean(c1["label"][r1, c1_] == 2) > 0.9
    truth = TT.ttc_truth(c0["depth"], K, T, dt)
    # 静止した車: 奥行きは光軸に沿って測るので、閉じる速さは v · (光軸の前向き · 進行方向)(カメラは少し下を向く)
    fwd = -p0[2, :3]                                                # カメラ系 −Z の世界での向き
    v_axis = v * float(fwd @ [1.0, 0.0, 0.0])
    assert 0.99 < v_axis / v < 1.0
    assert np.allclose(truth["closing_speed"][car], v_axis, atol=1e-9)
    assert np.allclose(truth["tau"][car], c0["depth"][car] / v_axis, atol=1e-9)


@pytest.mark.parametrize("bad", [np.eye(2), np.zeros((3, 3))])
def test_bad_intrinsics(bad):
    with pytest.raises(ValueError):
        TT.camera_backproject(np.ones((4, 4)), bad)


def test_bad_transform():
    T = np.eye(4)
    T[3, 0] = 1.0
    with pytest.raises(ValueError):
        TT.flow_from_depth_motion(np.ones((4, 4)), _K(), T)
    with pytest.raises(ValueError):
        TT.ttc_truth(np.ones((4, 4)), _K(), np.eye(4), 0.0)
