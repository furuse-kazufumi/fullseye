"""motion_seg3d(剛体運動セグメンテーション)テスト — 全て ground-truth 数値検証。

GT 方針(note_15 の 3 失敗モードを踏まない):
- (A) スケール相対: 全ケースを座標スケール 1x と 1000x で回し、thresh / 運動量を
      スケールに比例させる(絶対 epsilon をテストにも実装にも置かない)。
- (B) 縮退 / 不正入力(空 pts1, 非有限, 形状不正, thresh<=0, N<3)は fail-closed
      (ValueError)。outlier / 未対応点は詐称せず label = -1 になることを検証。
- (C) GT は実装から独立に構成: 回転は Rodrigues 公式で自前生成(Kabsch を再導出しない)、
      物体は空間的に分離した格子(間隔 >> 運動量 = 最近傍対応が真の対応と一致)で作る。
      判別ケース(単一剛体 -> 1 個 / 2 剛体 -> 2 個 / outlier -> -1)で「常に 1 個」や
      「全部 -1」な壊れた実装を弾く。各 label の点数を既知の格子点数と厳密照合する。
"""
import numpy as np
import pytest

import motion_seg3d as ms

SCALES = [1.0, 1000.0]


# ---------------------------------------------------------------------------
# 独立 GT ヘルパ(実装非依存)
# ---------------------------------------------------------------------------
def rodrigues(axis, deg: float) -> np.ndarray:
    """軸-角から回転行列(Rodrigues)。実装の Kabsch とは独立の GT 生成器。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def rot_angle_deg(Ra, Rb) -> float:
    """2 回転間の測地角(度)。"""
    c = (np.trace(np.asarray(Ra).T @ np.asarray(Rb)) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def grid(n, spacing, center):
    """中心 center の規則格子 (n^3, 3)。間隔 spacing。"""
    c = (np.arange(n, dtype=float) - (n - 1) / 2.0) * spacing
    gx, gy, gz = np.meshgrid(c, c, c, indexing="ij")
    P = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)
    return P + np.asarray(center, float)


# ---------------------------------------------------------------------------
# 1. estimate_flow: 一様並進を閉形式で回復(格子間隔 >> 並進 -> 最近傍が真対応)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_estimate_flow_recovers_uniform_translation(scale):
    P0 = grid(4, 1.0, (0, 0, 0)) * scale
    T = np.array([0.2, -0.1, 0.05]) * scale       # |T| < 0.5*spacing -> 最近傍=真対応
    P1 = P0 + T
    flow = ms.estimate_flow(P0, P1)
    assert flow.shape == P0.shape
    assert np.allclose(flow, T, atol=1e-6 * scale)   # 閉形式 GT


# ---------------------------------------------------------------------------
# 2. fit_rigid: 既知の剛体運動を回復(独立 Rodrigues GT, 有効な回転)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_fit_rigid_recovers_known_motion(scale):
    rng = np.random.default_rng(7)
    P = rng.uniform(-0.5, 0.5, size=(50, 3)) * scale
    R_true = rodrigues([1.0, 2.0, -1.0], 12.0)
    t_true = np.array([0.05, -0.03, 0.04]) * scale
    Q = P @ R_true.T + t_true

    R, t = ms.fit_rigid(P, Q)
    assert rot_angle_deg(R, R_true) < 1e-4
    assert np.allclose(t, t_true, atol=1e-6 * scale)
    # 有効な回転(det=+1, 直交)
    assert np.isclose(np.linalg.det(R), 1.0, atol=1e-9)
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-9)


# ---------------------------------------------------------------------------
# 3. 2 剛体(左半分=並進 / 右半分=回転)を 2 個に分割し各運動を回復
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_segments_two_rigid_bodies(scale):
    n = 4
    spacing = 1.0
    # 空間的に分離した 2 格子(x 方向にギャップ 6 >> 運動量 -> クロス最近傍なし)
    cL = np.array([-3.0, 0.0, 0.0])
    cR = np.array([+3.0, 0.0, 0.0])
    L0 = grid(n, spacing, cL) * scale
    R0 = grid(n, spacing, cR) * scale
    npts = n ** 3                                  # 各物体の既知点数

    # 左物体: 一様並進(|T| < 0.5*spacing*scale)
    T = np.array([0.2, 0.1, -0.05]) * scale
    L1 = L0 + T
    R_left_true = np.eye(3)
    t_left_true = T

    # 右物体: 中心 cR まわりの小回転(最大変位 < 0.5*spacing*scale で最近傍対応を保つ)
    R_rot = rodrigues([0.2, 1.0, -0.3], 6.0)
    cRs = cR * scale
    R1 = (R0 - cRs) @ R_rot.T + cRs
    R_right_true = R_rot
    t_right_true = cRs - R_rot @ cRs               # p1 = R p0 + (c - R c)

    P0 = np.vstack([L0, R0])
    P1 = np.vstack([L1, R1])
    gt_is_left = np.concatenate([np.ones(npts, bool), np.zeros(npts, bool)])

    out = ms.segment_rigid_motions(P0, P1, thresh=0.05 * scale, max_bodies=5)
    labels = out["labels"]
    motions = out["motions"]

    # ちょうど 2 剛体
    assert len(motions) == 2
    assert set(np.unique(labels)) == {0, 1}        # outlier なし(完全対応)

    # 各 label が 1 つの GT 物体に純粋対応し、点数が既知格子点数と一致
    for lab in (0, 1):
        member = labels == lab
        assert member.sum() == npts                # 厳密な点数一致(見た目でない)
        # 純度 100%: すべて同じ GT 物体
        assert gt_is_left[member].all() or (~gt_is_left[member]).all()

    # label -> どちらの物体か(並進物体は R≈I)を判定して各運動を GT 照合
    for lab in (0, 1):
        member = labels == lab
        is_left_body = gt_is_left[member][0]
        R, t = motions[lab]
        # 有効な回転
        assert np.isclose(np.linalg.det(R), 1.0, atol=1e-9)
        assert np.allclose(R.T @ R, np.eye(3), atol=1e-9)
        if is_left_body:
            assert rot_angle_deg(R, R_left_true) < 1e-3
            assert np.allclose(t, t_left_true, atol=1e-5 * scale)
        else:
            assert rot_angle_deg(R, R_right_true) < 1e-3
            assert np.allclose(t, t_right_true, atol=1e-5 * scale)


# ---------------------------------------------------------------------------
# 4. 判別: 単一剛体 -> ちょうど 1 個(「常に複数へ割る」壊れた実装を弾く)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_single_rigid_body_is_one_segment(scale):
    n = 4
    P0 = grid(n, 1.0, (0, 0, 0)) * scale
    R_true = rodrigues([0.3, -1.0, 0.5], 5.0)
    t_true = np.array([0.1, 0.05, -0.08]) * scale   # |disp| < 0.5*spacing
    P1 = P0 @ R_true.T + t_true

    out = ms.segment_rigid_motions(P0, P1, thresh=0.05 * scale, max_bodies=5)
    labels, motions = out["labels"], out["motions"]

    assert len(motions) == 1
    assert np.all(labels == 0)                      # 全点が唯一の剛体
    R, t = motions[0]
    assert rot_angle_deg(R, R_true) < 1e-3
    assert np.allclose(t, t_true, atol=1e-5 * scale)


# ---------------------------------------------------------------------------
# 5. 判別(honest): outlier / 未対応点は label = -1(詐称して剛体化しない)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_outliers_are_labeled_minus_one(scale):
    n = 4
    body0 = grid(n, 1.0, (0, 0, 0)) * scale
    npts = n ** 3
    T = np.array([0.15, -0.1, 0.05]) * scale
    body1 = body0 + T

    # 遠方の少数 outlier(剛体運動に整合しないランダム変位)。数 << min_inliers。
    rng = np.random.default_rng(5)
    k = 5
    far = np.array([12.0, 12.0, 12.0]) * scale
    out0 = far + rng.uniform(-0.4, 0.4, size=(k, 3)) * scale
    out1 = far + rng.uniform(-0.4, 0.4, size=(k, 3)) * scale   # 独立 -> ランダム変位

    P0 = np.vstack([body0, out0])
    P1 = np.vstack([body1, out1])

    out = ms.segment_rigid_motions(P0, P1, thresh=0.02 * scale, max_bodies=5)
    labels, motions = out["labels"], out["motions"]

    # 剛体は 1 個、本体点は同一 label、outlier は -1
    assert len(motions) == 1
    body_labels = labels[:npts]
    outlier_labels = labels[npts:]
    assert np.all(body_labels == 0)                 # 本体は 1 剛体に集約
    assert np.all(outlier_labels == -1)             # 5 個の outlier は未割当(honest)

    R, t = motions[0]
    assert rot_angle_deg(R, np.eye(3)) < 1e-3
    assert np.allclose(t, T, atol=1e-5 * scale)


# ---------------------------------------------------------------------------
# 6. 縮退 / 不正入力は fail-closed(ValueError)
# ---------------------------------------------------------------------------
def test_fail_closed_on_degenerate_inputs():
    P = np.random.default_rng(0).uniform(size=(10, 3))

    # 形状不正 (N, 2)
    with pytest.raises(ValueError):
        ms.estimate_flow(P[:, :2], P)
    with pytest.raises(ValueError):
        ms.segment_rigid_motions(P[:, :2], P, thresh=0.1)

    # 最近傍が存在しない(pts1 空)
    with pytest.raises(ValueError):
        ms.estimate_flow(P, np.empty((0, 3)))
    with pytest.raises(ValueError):
        ms.segment_rigid_motions(P, np.empty((0, 3)), thresh=0.1)

    # 非有限
    bad = P.copy()
    bad[0, 0] = np.inf
    with pytest.raises(ValueError):
        ms.estimate_flow(bad, P)
    with pytest.raises(ValueError):
        ms.segment_rigid_motions(bad, P, thresh=0.1)

    # thresh <= 0 / 非有限
    with pytest.raises(ValueError):
        ms.segment_rigid_motions(P, P, thresh=0.0)
    with pytest.raises(ValueError):
        ms.segment_rigid_motions(P, P, thresh=-1.0)
    with pytest.raises(ValueError):
        ms.segment_rigid_motions(P, P, thresh=np.nan)

    # max_bodies < 1 / k_sample < 3
    with pytest.raises(ValueError):
        ms.segment_rigid_motions(P, P, thresh=0.1, max_bodies=0)
    with pytest.raises(ValueError):
        ms.segment_rigid_motions(P, P, thresh=0.1, k_sample=2)

    # fit_rigid: 対応不一致 / N < 3
    with pytest.raises(ValueError):
        ms.fit_rigid(P[:5], P[:4])
    with pytest.raises(ValueError):
        ms.fit_rigid(P[:2], P[:2])


def test_empty_source_returns_empty_not_error():
    """空 pts0 は縮退ではなく有効入力 -> 空 flow / labels を返す(詐称せず)。"""
    empty = np.empty((0, 3))
    P1 = np.random.default_rng(1).uniform(size=(5, 3))
    assert ms.estimate_flow(empty, P1).shape == (0, 3)
    out = ms.segment_rigid_motions(empty, P1, thresh=0.1)
    assert out["labels"].shape == (0,)
    assert out["motions"] == []
