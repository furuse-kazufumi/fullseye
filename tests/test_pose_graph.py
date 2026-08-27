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
    # ノイズ付き相対姿勢制約: open chain はドリフトが積算、ループ閉じが補正する(back-end の存在意義)。
    # 旧テストは exact エッジで open も真値回復し性質を検証していなかった(甘いテスト)。
    poses, _ = _loop_scene(n=8, seed=4)
    n = len(poses)
    rng = np.random.default_rng(11)
    odo = []
    for i in range(n - 1):                            # ノイズ付きオドメトリ(連続エッジ)
        rv, t = pg.relative_pose(poses[i], poses[i + 1])
        odo.append((i, i + 1, rv + rng.normal(0, 0.02, 3), t + rng.normal(0, 0.03, 3), 1.0, 1.0))
    rvc, tc = pg.relative_pose(poses[n - 1], poses[0])   # ループ閉じ(単一ノイズ)
    closure = (n - 1, 0, rvc + rng.normal(0, 0.02, 3), tc + rng.normal(0, 0.03, 3), 1.0, 1.0)
    init = np.zeros_like(poses)                       # 初期: node0=真値、以降はノイズ付きオドメトリ積分=ドリフト積算
    init[0] = poses[0]
    for i in range(n - 1):
        Ri = pg.rvec_to_R(init[i][:3]); ti = init[i][3:]
        Rr = pg.rvec_to_R(odo[i][2]); tr = odo[i][3]
        Rj = Ri @ Rr; tj = Ri @ tr + ti
        init[i + 1] = np.concatenate([pg.R_to_rvec(Rj), tj])
    opened = pg.optimize_pose_graph(init, odo, fix_first=True)
    closed = pg.optimize_pose_graph(init, odo + [closure], fix_first=True)
    err_open = np.linalg.norm(opened["poses"][4, 3:] - poses[4, 3:])
    err_closed = np.linalg.norm(closed["poses"][4, 3:] - poses[4, 3:])
    assert err_closed < err_open, (err_closed, err_open)   # ループ閉じがドリフトを減らす


def test_guards():
    poses, edges = _loop_scene()
    with pytest.raises(ValueError):
        pg.optimize_pose_graph(poses[:1], edges)          # <2 ノード
    with pytest.raises(ValueError):
        pg.optimize_pose_graph(poses, [])                 # エッジ空


def test_edge_index_out_of_range_fails_closed():
    """fail-closed: 範囲外/負のエッジ index は ValueError(負の silent wrap を防ぐ)。"""
    poses, edges = _loop_scene(n=4)
    with pytest.raises(ValueError):
        pg.optimize_pose_graph(poses, [(0, -1, np.zeros(3), np.zeros(3), 1.0, 1.0)])
    with pytest.raises(ValueError):
        pg.optimize_pose_graph(poses, [(0, 9, np.zeros(3), np.zeros(3), 1.0, 1.0)])
