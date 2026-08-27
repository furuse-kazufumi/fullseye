"""scene_flow3d の ground-truth テスト(点群シーンフロー / 剛体・非剛体分解)。

GT は実装から独立に構成する: 剛体運動は Rodrigues 公式で自前生成(実装の Kabsch を
再導出しない)、一様並進 / 線形変位場は閉形式の期待値を持つ。全ケースを座標スケール
1 倍と 1000 倍で回し、tolerance はスケール相対(絶対 epsilon を使わない)。縮退入力は
fail-closed(ValueError)を確認する。"""
import numpy as np
import pytest

import scene_flow3d as sf

SCALES = [1.0, 1000.0]


# ----------------------------------------------------------------------------
# 独立 GT ヘルパ(実装非依存)
# ----------------------------------------------------------------------------
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


def grid(n=6, spacing=1.0):
    """中心対称な規則格子 (n^3, 3) と各軸座標を返す。"""
    c = (np.arange(n, dtype=float) - (n - 1) / 2.0) * spacing
    gx, gy, gz = np.meshgrid(c, c, c, indexing="ij")
    P = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)
    return P, gx.ravel(), gy.ravel(), gz.ravel()


# ----------------------------------------------------------------------------
# 1. 一様並進場 -> nearest_neighbor_flow がその並進を回復
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_nearest_neighbor_flow_recovers_uniform_translation(scale):
    P0, *_ = grid(n=5, spacing=1.0)
    P0 = P0 * scale
    # 並進は格子間隔(=scale)の半分未満 -> 最近傍対応が真の対応と一致する
    T = np.array([0.13, -0.08, 0.05]) * scale
    P1 = P0 + T
    flow = sf.nearest_neighbor_flow(P0, P1)
    assert flow.shape == P0.shape
    # 全点が同一の並進 T(閉形式 GT)
    assert np.allclose(flow, T, atol=1e-6 * scale)


# ----------------------------------------------------------------------------
# 2. 既知剛体運動 -> rigid_flow が R,t 回復 / residual_flow ~ 0
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_rigid_flow_recovers_known_motion_and_zero_residual(scale):
    rng = np.random.default_rng(7)
    P0 = rng.uniform(-0.5, 0.5, size=(400, 3)) * scale
    R_true = rodrigues([1.0, 2.0, -1.0], 6.0)          # 6 deg, 独立 GT
    t_true = np.array([0.05, -0.03, 0.04]) * scale
    P1 = P0 @ R_true.T + t_true

    res = sf.rigid_flow(P0, P1)
    R, t, rmse = res["R"], res["t"], res["rmse"]

    # 回転回復: << 0.5 deg
    assert rot_angle_deg(R, R_true) < 0.5
    # 並進回復(スケール相対)
    assert np.allclose(t, t_true, atol=1e-6 * scale)
    # 整合 rmse は実測でほぼ 0(スケール相対)
    assert rmse < 1e-6 * scale
    # 有効な回転(det=+1, 直交)
    assert np.isclose(np.linalg.det(R), 1.0, atol=1e-9)
    assert np.allclose(R.T @ R, np.eye(3), atol=1e-9)

    # 剛体を引いた残差はゼロに潰れる
    residual = sf.residual_flow(P0, P1, R, t)
    assert residual.shape == P0.shape
    assert np.max(np.linalg.norm(residual, axis=1)) < 1e-6 * scale


# ----------------------------------------------------------------------------
# 3. 既知の滑らかな(線形)変位場 + ノイズ -> smooth_flow が平滑近似(ノイズ低減)
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_smooth_flow_reduces_noise_vs_known_field(scale):
    P0, gx, gy, gz = grid(n=6, spacing=1.0)
    P0 = P0 * scale
    # 線形変位場 D(p) = A p(原点通過, 対称近傍で不偏平均)。|D| は間隔の 1/10 程度。
    A = np.array([[0.00, 0.05, 0.00],
                  [-0.05, 0.00, 0.03],
                  [0.02, 0.00, 0.00]])
    D = P0 @ A.T                                       # (N,3) 真の滑らか場
    rng = np.random.default_rng(11)
    noise = rng.normal(0.0, 0.06 * scale, size=P0.shape)   # ゼロ平均ノイズ
    P1 = P0 + D + noise                                # |D+noise| < 0.5*scale で対応保持

    raw = sf.nearest_neighbor_flow(P0, P1)             # 対応正 -> raw = D + noise
    smooth = sf.smooth_flow(P0, P1, k=7, n_iter=6)     # 自身 + 6 面近傍 = 対称

    # 対応が正しいことを確認(raw が D+noise に一致 = GT の前提保証)
    assert np.allclose(raw, D + noise, atol=1e-6 * scale)

    # 格子内部(全 6 面近傍が存在)でのみ評価
    interior = (np.abs(gx) < (P0[:, 0].max() / scale)) \
        & (np.abs(gy) < (P0[:, 1].max() / scale)) \
        & (np.abs(gz) < (P0[:, 2].max() / scale))
    err_raw = np.sqrt(np.mean(np.sum((raw[interior] - D[interior]) ** 2, axis=1)))
    err_smooth = np.sqrt(np.mean(np.sum((smooth[interior] - D[interior]) ** 2, axis=1)))

    # 平滑化がノイズを明確に低減(スケール不変な比で判定)
    assert err_smooth < 0.7 * err_raw
    # 平滑化は実際にフローを変える(恒等でない = 判別的)
    assert not np.allclose(smooth, raw)

    # ラフネス(近傍との差)も低下する
    def roughness(F):
        from scipy.spatial import cKDTree
        _, idx = cKDTree(P0).query(P0, k=7)
        nbr_mean = F[idx].mean(axis=1)
        return np.mean(np.sum((F - nbr_mean) ** 2, axis=1))
    assert roughness(smooth) < roughness(raw)


# ----------------------------------------------------------------------------
# 4. 判別: 剛体 + 局所非剛体変形 -> residual が変形領域に局在する
#    (「常に 0」や「= 全フロー」な壊れた実装を弾く)
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("scale", SCALES)
def test_residual_flow_localizes_nonrigid_deformation(scale):
    rng = np.random.default_rng(3)
    P0 = rng.uniform(-0.5, 0.5, size=(160, 3)) * scale
    R_true = rodrigues([0.3, -1.0, 0.5], 5.0)
    t_true = np.array([0.04, 0.02, -0.03]) * scale
    base = P0 @ R_true.T + t_true

    # 少数派(x>0.3)にだけ一定の変位(間隔より小さく最近傍対応を保つ)
    mask = P0[:, 0] > 0.3 * scale
    bump = np.array([0.0, 0.0, 0.12]) * scale
    P1 = base.copy()
    P1[mask] += bump

    res = sf.rigid_flow(P0, P1)
    residual = sf.residual_flow(P0, P1, res["R"], res["t"])
    rn = np.linalg.norm(residual, axis=1)

    # 変形領域の残差が非変形領域より明確に大きい
    assert rn[mask].mean() > 3.0 * rn[~mask].mean()
    # 変形量そのもののオーダーを回復している(スケール相対の下限)
    assert rn[mask].mean() > 0.5 * np.linalg.norm(bump)


# ----------------------------------------------------------------------------
# 5. 縮退 / 不正入力は fail-closed(ValueError)
# ----------------------------------------------------------------------------
def test_fail_closed_on_degenerate_inputs():
    P = np.random.default_rng(0).uniform(size=(10, 3))

    # 回転を一意化できない < 3 点
    with pytest.raises(ValueError):
        sf.rigid_flow(P[:2], P)

    # 形状不正 (N,2)
    with pytest.raises(ValueError):
        sf.nearest_neighbor_flow(P[:, :2], P)

    # 最近傍が存在しない(pts1 空)
    with pytest.raises(ValueError):
        sf.nearest_neighbor_flow(P, np.empty((0, 3)))
    with pytest.raises(ValueError):
        sf.rigid_flow(P, np.empty((0, 3)))

    # 非有限値
    bad = P.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        sf.nearest_neighbor_flow(bad, P)

    # residual_flow の R,t 形状不正
    with pytest.raises(ValueError):
        sf.residual_flow(P, P, np.eye(2), np.zeros(3))


def test_empty_source_returns_empty_not_error():
    """空 pts0 は縮退ではなく有効入力 -> 空 (0,3) を返す(詐称せず)。"""
    empty = np.empty((0, 3))
    P1 = np.random.default_rng(1).uniform(size=(5, 3))
    assert sf.nearest_neighbor_flow(empty, P1).shape == (0, 3)
    assert sf.smooth_flow(empty, P1).shape == (0, 3)
    assert sf.residual_flow(empty, P1, np.eye(3), np.zeros(3)).shape == (0, 3)
