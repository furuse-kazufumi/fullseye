"""pose_graph の GT 検証: ループ状の合成姿勢 + オドメトリ/ループ閉じ → ドリフト初期から真姿勢へ回復。"""
import numpy as np
import pytest

import pose_graph as pg


def _rot_angle_deg(rva, rvb):
    R = pg.rvec_to_R(rva).T @ pg.rvec_to_R(rvb)
    c = np.clip((np.trace(R) - 1) / 2, -1, 1)
    return np.rad2deg(np.arccos(c))


def _loop_scene(n=8, R=3.0, seed=0):
    """円状に n ノードを配置し各々中心を向く真姿勢 + 連続オドメトリ + ループ閉じエッジ。"""
    rng = np.random.default_rng(seed)
    poses = []
    for i in range(n):
        ang = 2 * np.pi * i / n
        pos = np.array([R * np.cos(ang), R * np.sin(ang), 0.0])
        # 中心を向く向き(z 軸まわり)+ 小さな傾き
        yaw = ang + np.pi
        rvec = np.array([0.05 * np.sin(ang), 0.05 * np.cos(ang), yaw])
        poses.append(np.concatenate([rvec, pos]))
    poses = np.array(poses)
    edges = []
    for i in range(n):
        j = (i + 1) % n                                  # 連続 + 最後→0=ループ閉じ
        rvec_ij, t_ij = pg.relative_pose(poses[i], poses[j])
        edges.append((i, j, rvec_ij, t_ij, 1.0, 1.0))
    return poses, edges


def test_residual_zero_at_truth():
    poses, edges = _loop_scene()
    assert pg.mean_edge_error(poses, edges) < 1e-9


def test_optimize_recovers_from_drift():
    poses, edges = _loop_scene(n=8, seed=1)
    # ドリフト初期: 各ノードに累積誤差を模した摂動(先頭は真値固定)
    rng = np.random.default_rng(5)
    init = poses.copy()
    drift = np.zeros(3)
    for i in range(1, len(poses)):
        drift = drift + rng.normal(0, 0.1, 3)            # 累積並進ドリフト
        init[i, 3:] += drift
        init[i, :3] += rng.normal(0, 0.03, 3)            # 回転摂動
    rmse_init = pg.mean_edge_error(init, edges)
    out = pg.optimize_pose_graph(init, edges, fix_first=True)
    # 残差 ~0 に収束(ループ閉じがドリフトを補正)
    assert out["rmse"] < 1e-3, (out["rmse"], rmse_init)
    assert out["rmse"] < rmse_init
    # 各ノード姿勢が真値へ回復(先頭固定で gauge 除去)
    for i in range(len(poses)):
        assert _rot_angle_deg(out["poses"][i, :3], poses[i, :3]) < 1.0
        assert np.linalg.norm(out["poses"][i, 3:] - poses[i, 3:]) < 0.05


def test_first_node_fixed():
    poses, edges = _loop_scene(seed=2)
    init = poses.copy()
    init[1:, 3:] += np.random.default_rng(3).normal(0, 0.05, init[1:, 3:].shape)
    out = pg.optimize_pose_graph(init, edges, fix_first=True)
    assert np.allclose(out["poses"][0], poses[0])


def test_loop_closure_beats_open_chain():
    # ループ閉じ有り vs 無し: 有りの方が終端ノードの誤差が小さい(ドリフト補正)
    poses, edges = _loop_scene(n=8, seed=4)
    open_edges = [e for e in edges if not (e[0] == 7 and e[1] == 0)]  # ループ閉じを除く
    init = poses.copy()
    rng = np.random.default_rng(6)
    drift = np.zeros(3)
    for i in range(1, len(poses)):
        drift = drift + rng.normal(0, 0.12, 3)
        init[i, 3:] += drift
    closed = pg.optimize_pose_graph(init, edges, fix_first=True)
    opened = pg.optimize_pose_graph(init, open_edges, fix_first=True)
    err_closed = np.linalg.norm(closed["poses"][4, 3:] - poses[4, 3:])
    err_open = np.linalg.norm(opened["poses"][4, 3:] - poses[4, 3:])
    assert err_closed < err_open                          # ループ閉じが誤差を減らす


def test_guards():
    poses, edges = _loop_scene()
    with pytest.raises(ValueError):
        pg.optimize_pose_graph(poses[:1], edges)          # <2 ノード
    with pytest.raises(ValueError):
        pg.optimize_pose_graph(poses, [])                 # エッジ空
