"""gicp.py の ground-truth テスト。

方針(note_15 の 3 失敗モードを踏まない):
- (A) 閾値はスケール相対に。剛体回復は scale=1 と scale=1000 の 2 スケールで検証。
- (B) 縮退(単一平面)入力は NaN/発散させず、観測可能量(接平面整合)で honest に判定。
      単一平面は面内 2 並進 + 法線回り回転が原理的に不可観測なので、完全な R,t 復元は
      主張せず「変換後 source が target 平面に乗る(点-面距離が小)」ことのみ検証する。
- (C) GT は独立生成(既知の軸角回転+並進を閉形式で構成)。判別は GT との照合で行い、
      実装の再導出をテストにしない。共分散の固有値 {ε,1,1} も閉形式で検証。

ICP はローカル最適化なので **近い初期化前提**。したがって中程度(~8°)の回転で検証する。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")

import gicp


# ─────────────────────────────────────────────────────────────────────────
# GT ヘルパ(実装から独立した閉形式)
# ─────────────────────────────────────────────────────────────────────────
def _axis_angle_R(axis, deg):
    """軸(3,)と角(度)から回転行列 (Rodrigues 閉形式・実装から独立)。"""
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]], float)
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)


def _rot_angle_deg(Ra, Rb):
    """2 回転行列間の測地角(度)。"""
    Rrel = Ra.T @ Rb
    c = (np.trace(Rrel) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def _wavy_surface(seed=0, nx=45, ny=45, extent=1.0):
    """原点中心の波打つ曲面(法線が多方向 → full 6-DOF 可観測)。返り (M,3)。"""
    rng = np.random.default_rng(seed)
    xs = np.linspace(-extent, extent, nx)
    ys = np.linspace(-extent, extent, ny)
    X, Y = np.meshgrid(xs, ys)
    Z = 0.25 * extent * (np.sin(3.0 * X / extent) + np.cos(3.0 * Y / extent))
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    P += rng.normal(0, 1e-9, P.shape)   # 対称性を割る極小ジッタ(GT はほぼクリーン)
    return P - P.mean(axis=0)           # 原点中心化


# ═══════════════════════════════════════════════════════════════════════════
# estimate_covariances: 固有値 {ε,1,1} と法線方向の GT 検証
# ═══════════════════════════════════════════════════════════════════════════
def test_covariance_eigenvalues_are_epsilon_one_one():
    """plane-to-plane 共分散の固有値が厳密に {ε,1,1} になる(閉形式 GT)。"""
    P = _wavy_surface(1)
    eps = 1e-3
    cov = gicp.estimate_covariances(P, k=20, epsilon=eps)
    assert cov.shape == (P.shape[0], 3, 3)
    # 各共分散の固有値(昇順)が [ε,1,1] に一致
    w = np.linalg.eigvalsh(cov)                     # (N,3) 昇順
    assert np.allclose(w[:, 0], eps, atol=1e-12)
    assert np.allclose(w[:, 1], 1.0, atol=1e-12)
    assert np.allclose(w[:, 2], 1.0, atol=1e-12)
    # 対称性
    assert np.allclose(cov, np.transpose(cov, (0, 2, 1)), atol=1e-12)


def test_covariance_epsilon_direction_is_plane_normal():
    """平面上では ε に対応する固有ベクトルが平面法線に一致する(GT 法線と照合)。"""
    rng = np.random.default_rng(2)
    normal = np.array([0.3, -0.5, 1.0]); normal /= np.linalg.norm(normal)
    e1 = np.cross(normal, [1.0, 0, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(normal, e1)
    uv = rng.uniform(-1, 1, (400, 2))
    P = uv[:, :1] * e1 + uv[:, 1:] * e2 + rng.normal(0, 1e-4, (400, 3))
    cov = gicp.estimate_covariances(P, k=20, epsilon=1e-3)
    # ε は最小固有値 → 対応固有ベクトルは eigh の第0列
    w, V = np.linalg.eigh(cov)
    n_est = V[:, :, 0]                               # (N,3)
    cosang = np.abs(n_est @ normal)                 # 符号不定を吸収
    assert np.median(cosang) > 0.99


def test_covariance_fail_closed_on_degenerate():
    """縮退入力(点数不足 / 不正 epsilon / 形状不正)は fail-closed(ValueError)。"""
    with pytest.raises(ValueError):
        gicp.estimate_covariances(np.zeros((2, 3)), k=20)          # N<3
    with pytest.raises(ValueError):
        gicp.estimate_covariances(_wavy_surface(0), epsilon=0.0)   # ε 範囲外
    with pytest.raises(ValueError):
        gicp.estimate_covariances(np.zeros((10, 2)))               # 形状不正


# ═══════════════════════════════════════════════════════════════════════════
# gicp: 既知剛体変換の高精度回復(2 スケールでスケール相対を検証)
# ═══════════════════════════════════════════════════════════════════════════
def _recover_at_scale(scale, deg=8.0, seed=0):
    """scale 倍した曲面に既知 (R_gt,t_gt) を掛けた対で GICP を走らせ結果を返す。"""
    Q = _wavy_surface(seed) * scale                 # target(参照)
    R_gt = _axis_angle_R([0.2, 0.9, -0.3], deg)     # 中程度回転(近い初期化前提)
    t_gt = np.array([0.05, -0.04, 0.03]) * scale    # 並進もスケールに比例
    # target ≈ R_gt·source + t_gt となる source を構成(GT は独立閉形式)
    source = (Q - t_gt) @ R_gt                      # = R_gtᵀ·(Q - t_gt) を各行に
    out = gicp.gicp(source, Q, max_iter=40, k=20, epsilon=1e-3, init=None)
    return out, R_gt, t_gt, scale


def test_recover_rigid_transform_unit_scale():
    """単位スケール: rot 誤差<0.5°、t 誤差 小、rmse 小(GT 照合)。"""
    out, R_gt, t_gt, scale = _recover_at_scale(1.0)
    ang = _rot_angle_deg(out["R"], R_gt)
    t_err = np.linalg.norm(out["t"] - t_gt)
    assert ang < 0.5, f"rotation error {ang} deg"
    assert t_err < 1e-3 * scale, f"translation error {t_err}"
    assert out["rmse"] < 1e-3 * scale, f"rmse {out['rmse']}"


def test_recover_rigid_transform_large_scale():
    """1000 倍スケール: 同じ相対閾値で成立(絶対 epsilon なら破綻する = mode A 検証)。"""
    out, R_gt, t_gt, scale = _recover_at_scale(1000.0)
    ang = _rot_angle_deg(out["R"], R_gt)
    t_err = np.linalg.norm(out["t"] - t_gt)
    assert ang < 0.5, f"rotation error {ang} deg"
    assert t_err < 1e-3 * scale, f"translation error {t_err}"
    assert out["rmse"] < 1e-3 * scale, f"rmse {out['rmse']}"


def test_recover_under_noise():
    """ノイズ付き曲面でも rot 誤差<0.5°(honest tolerance、rmse はノイズ相当)。"""
    rng = np.random.default_rng(7)
    scale = 1.0
    noise = 3e-3 * scale
    Q = _wavy_surface(3) * scale + rng.normal(0, noise, (2025, 3))
    R_gt = _axis_angle_R([0.1, -0.8, 0.5], 7.0)
    t_gt = np.array([0.03, 0.02, -0.05]) * scale
    source = (Q - t_gt) @ R_gt + rng.normal(0, noise, Q.shape)
    out = gicp.gicp(source, Q, max_iter=40, k=25, epsilon=1e-3)
    ang = _rot_angle_deg(out["R"], R_gt)
    assert ang < 0.5, f"rotation error {ang} deg"
    # rmse は概ねノイズ規模(±2σ 目安)。詐称的な 0 は出ない。
    assert out["rmse"] < 6.0 * noise, f"rmse {out['rmse']}"
    assert out["rmse"] > 0.1 * noise, f"rmse suspiciously small {out['rmse']}"


def test_init_close_pose_refines():
    """粗初期化(init に近い R0,t0)を渡すと高精度に締め上げる。"""
    Q = _wavy_surface(5)
    R_gt = _axis_angle_R([0.0, 0.0, 1.0], 6.0)
    t_gt = np.array([0.02, 0.01, -0.02])
    source = (Q - t_gt) @ R_gt
    R0 = _axis_angle_R([0.0, 0.0, 1.0], 4.0)        # GT より 2° 手前
    out = gicp.gicp(source, Q, init=(R0, np.zeros(3)))
    assert _rot_angle_deg(out["R"], R_gt) < 0.5


# ═══════════════════════════════════════════════════════════════════════════
# 縮退(単一平面): NaN/発散しない + 接平面整合(honest な可観測量で判定)
# ═══════════════════════════════════════════════════════════════════════════
def test_planar_cloud_converges_without_nan():
    """単一平面(+ノイズ)は完全な R,t 復元は不可観測 → 接平面整合のみ honest に検証。

    面内 2 並進 + 法線回り回転は原理的に不可観測。よって GICP には「平面を傾ける
    (面内軸回り)回転 + 法線方向並進」= 可観測な変換のみを与える。判定は
    「変換後 source が target 平面に乗る(点-面距離が小)」+ 非 NaN・非発散。
    """
    rng = np.random.default_rng(11)
    normal = np.array([0.2, 0.1, 1.0]); normal /= np.linalg.norm(normal)
    e1 = np.cross(normal, [1.0, 0, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(normal, e1)
    uv = rng.uniform(-1, 1, (1600, 2))
    noise = 2e-3
    Q = uv[:, :1] * e1 + uv[:, 1:] * e2 + rng.normal(0, noise, (1600, 3))

    # 可観測な変換のみ: 面内軸(e1)回り 5° 傾け + 法線方向 0.05 並進
    R_gt = _axis_angle_R(e1, 5.0)
    t_gt = 0.05 * normal
    source = (Q - t_gt) @ R_gt

    out = gicp.gicp(source, Q, max_iter=50, k=25, epsilon=1e-3)

    assert np.all(np.isfinite(out["R"])) and np.all(np.isfinite(out["t"]))
    assert np.isfinite(out["rmse"])
    # 収束後 target 平面法線を推定し、変換後 source の点-面距離を測る。
    p = source @ out["R"].T + out["t"]
    n_hat = normal                                   # GT 平面法線(独立)
    offset = float(np.median(Q @ n_hat))            # 平面オフセット(GT 平面)
    plane_resid = np.abs(p @ n_hat - offset)
    # 接平面整合: RMS 点-面距離がノイズ規模に収まる(初期の傾き 5° より大幅改善)
    init_resid = np.abs(source @ n_hat - offset)
    assert np.sqrt(np.mean(plane_resid ** 2)) < 3.0 * noise
    assert np.sqrt(np.mean(plane_resid ** 2)) < 0.2 * np.sqrt(np.mean(init_resid ** 2))


def test_gicp_fail_closed_on_bad_shape():
    """入力形状不正・点数不足は fail-closed(ValueError)。"""
    with pytest.raises(ValueError):
        gicp.gicp(np.zeros((10, 2)), np.zeros((10, 3)))
    with pytest.raises(ValueError):
        gicp.gicp(np.zeros((2, 3)), np.zeros((10, 3)))
