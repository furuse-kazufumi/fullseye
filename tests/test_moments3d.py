"""moments3d — 3D モーメント不変量の ground-truth 検証。

不変性(並進・回転・スケール)と識別性(細長い vs 球状)を数値で確認する。
- 楕円体の内部を一様充填した点群を生成し、同一点群に既知の剛体変換 R,t と
  一様スケール s を掛けた版と特徴が一致することを検証する(変換は厳密なので
  誤差は float64 の丸め ~1e-12 に収まり、仕様の相対誤差 < 1e-3 を大きく下回る)。
- 慣性テンソル固有値も回転で不変(< 1e-9)。
- 中心モーメント・慣性テンソルの閉形式(既知値)との一致も確認する。

すべて決定論的な rng で生成し再現可能。
"""
import numpy as np
import pytest

pytest.importorskip("numpy")

import moments3d as M  # noqa: E402


# --------------------------------------------------------------------------- #
# ジェネレータ / ユーティリティ                                               #
# --------------------------------------------------------------------------- #
def _solid_ellipsoid(n=6000, axes=(3.0, 1.5, 0.8), seed=1):
    """半軸 axes=(a,b,c) の楕円体内部を一様充填した点群 (n,3)。

    単位球を一様サンプルして軸倍する。中心 2 次モーメントは閉形式で
    diag(a²/5, b²/5, c²/5)(一様充填 solid ellipsoid の慣性から)。
    """
    a, b, c = axes
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < n:
        u = rng.uniform(-1.0, 1.0, size=(n, 3))
        u = u[np.einsum("ij,ij->i", u, u) <= 1.0]
        pts.extend(u.tolist())
    u = np.asarray(pts[:n], dtype=np.float64)
    return u * np.asarray(axes, dtype=np.float64)


def _rod(n=6000, length=6.0, thick=0.15, seed=3):
    """x 方向に細長い直方体を一様充填した点群 (n,3)。"""
    rng = np.random.default_rng(seed)
    x = rng.uniform(-length, length, size=n)
    y = rng.uniform(-thick, thick, size=n)
    z = rng.uniform(-thick, thick, size=n)
    return np.stack([x, y, z], axis=1)


def _solid_sphere(n=6000, r=1.0, seed=5):
    """半径 r の球内部を一様充填した点群 (n,3)。"""
    return _solid_ellipsoid(n=n, axes=(r, r, r), seed=seed)


def _rot_matrix(seed=7):
    """QR 分解で作る決定論的な回転行列(det=+1 に補正)。"""
    rng = np.random.default_rng(seed)
    q, r = np.linalg.qr(rng.standard_normal((3, 3)))
    q *= np.sign(np.diag(r))          # QR の符号任意性を除去
    if np.linalg.det(q) < 0:
        q[:, 0] = -q[:, 0]            # 反射を回転へ
    return q


def _rel_err(a, b):
    """要素ごとの相対誤差の最大値(分母は |b| と 1 の大きい方でゼロ割回避)。"""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denom = np.maximum(np.abs(b), 1.0)
    return float(np.max(np.abs(a - b) / denom))


# --------------------------------------------------------------------------- #
# 1. moment_invariants: 並進+回転+スケール不変                                #
# --------------------------------------------------------------------------- #
def test_invariants_under_rigid_transform_and_scale():
    """同一楕円体点群に R,t,s を掛けても moment_invariants が一致(rel < 1e-3)。

    変換は厳密なので実際の相対誤差は float64 丸め(~1e-12)。仕様の 1e-3 を
    大きく下回るため、より正直に 1e-9 を上限に設定する(系統誤差は無い)。
    """
    pts = _solid_ellipsoid(n=6000, axes=(3.0, 1.5, 0.8), seed=11)
    R = _rot_matrix(seed=7)
    t = np.array([12.3, -4.5, 100.0])
    s = 3.7

    base = M.moment_invariants(pts)
    transformed = M.moment_invariants(s * (pts @ R.T) + t)

    err = _rel_err(transformed, base)
    assert err < 1e-9, f"不変量が剛体変換+スケールで動いた: rel_err={err:.2e}"
    # 仕様が要求する 1e-3 も当然満たす。
    assert err < 1e-3


def test_invariants_separate_translation_rotation_scale():
    """並進・回転・スケールを個別に掛けても各々不変(それぞれ rel < 1e-9)。"""
    pts = _solid_ellipsoid(n=5000, axes=(2.5, 2.0, 1.0), seed=13)
    base = M.moment_invariants(pts)

    # 並進のみ
    only_t = M.moment_invariants(pts + np.array([-7.0, 3.0, 42.0]))
    assert _rel_err(only_t, base) < 1e-9

    # 回転のみ
    R = _rot_matrix(seed=21)
    only_r = M.moment_invariants(pts @ R.T)
    assert _rel_err(only_r, base) < 1e-9

    # スケールのみ
    only_s = M.moment_invariants(0.017 * pts)
    assert _rel_err(only_s, base) < 1e-9


def test_invariants_sum_to_one():
    """正規化固有値 λ̂1+λ̂2+λ̂3 は構成上 1(スケール正規化の健全性)。"""
    pts = _solid_ellipsoid(n=4000, axes=(3.0, 1.0, 0.5), seed=17)
    inv = M.moment_invariants(pts)
    assert abs(inv[0] + inv[1] + inv[2] - 1.0) < 1e-12
    assert inv[0] >= inv[1] >= inv[2] >= 0.0   # 降順・非負


# --------------------------------------------------------------------------- #
# 2. principal_moments: 回転不変                                               #
# --------------------------------------------------------------------------- #
def test_principal_moments_rotation_invariant():
    """慣性テンソル固有値は回転で不変(ソート後 < 1e-9)。"""
    pts = _solid_ellipsoid(n=6000, axes=(3.0, 1.5, 0.8), seed=23)
    R = _rot_matrix(seed=31)

    pm = M.principal_moments(pts)
    pm_rot = M.principal_moments(pts @ R.T)

    assert np.allclose(pm, pm_rot, atol=1e-9, rtol=0.0), (
        f"主慣性モーメントが回転で動いた: {pm} vs {pm_rot}"
    )


def test_principal_moments_translation_invariant():
    """慣性テンソル固有値は並進で厳密不変。"""
    pts = _solid_ellipsoid(n=4000, axes=(2.0, 1.2, 0.6), seed=29)
    pm = M.principal_moments(pts)
    pm_t = M.principal_moments(pts + np.array([100.0, -50.0, 7.0]))
    assert np.allclose(pm, pm_t, atol=1e-9, rtol=0.0)


# --------------------------------------------------------------------------- #
# 3. 閉形式(既知値)との一致                                                  #
# --------------------------------------------------------------------------- #
def test_second_moments_match_closed_form_ellipsoid():
    """一様 solid 楕円体の中心 2 次モーメントは diag(a²/5, b²/5, c²/5)。

    軸に沿って生成しているので慣性テンソル対角 = mean(b²+c², a²+c², a²+b²)/... の
    閉形式と一致するはず。サンプリング誤差 O(1/sqrt(N)) を見込み rel < 3e-2。
    """
    a, b, c = 3.0, 1.5, 0.8
    pts = _solid_ellipsoid(n=40000, axes=(a, b, c), seed=101)

    cm = M.central_moments(pts, max_order=2)
    # μ_{200}=a²/5, μ_{020}=b²/5, μ_{002}=c²/5(交差項は対称性から ~0)
    assert cm[(2, 0, 0)] == pytest.approx(a * a / 5.0, rel=3e-2)
    assert cm[(0, 2, 0)] == pytest.approx(b * b / 5.0, rel=3e-2)
    assert cm[(0, 0, 2)] == pytest.approx(c * c / 5.0, rel=3e-2)
    # 交差モーメントは 0 近傍(絶対誤差で判定、スケールは a*b/5 程度)
    assert abs(cm[(1, 1, 0)]) < 3e-2 * (a * b / 5.0) + 1e-3
    assert abs(cm[(1, 0, 1)]) < 3e-2 * (a * c / 5.0) + 1e-3
    assert abs(cm[(0, 1, 1)]) < 3e-2 * (b * c / 5.0) + 1e-3

    # μ_{000}=1、1 次モーメントは中心化で厳密 0。
    assert cm[(0, 0, 0)] == pytest.approx(1.0, abs=1e-12)
    assert abs(cm[(1, 0, 0)]) < 1e-12
    assert abs(cm[(0, 1, 0)]) < 1e-12
    assert abs(cm[(0, 0, 1)]) < 1e-12


def test_inertia_tensor_matches_covariance_identity():
    """inertia_tensor == tr(C)·E − C を満たす(共分散との代数恒等式)。"""
    pts = _solid_ellipsoid(n=5000, axes=(2.0, 1.7, 0.9), seed=131)
    centered = pts - pts.mean(axis=0, keepdims=True)
    cov = (centered.T @ centered) / centered.shape[0]
    expected = np.trace(cov) * np.eye(3) - cov

    it = M.inertia_tensor(pts)
    assert np.allclose(it, expected, atol=1e-12)
    assert np.allclose(it, it.T, atol=1e-12)   # 対称


def test_inertia_tensor_diagonal_for_axis_aligned():
    """軸に沿った楕円体では慣性テンソルが概ね対角(交差項 ≈ 0)。"""
    pts = _solid_ellipsoid(n=40000, axes=(3.0, 1.5, 0.8), seed=137)
    it = M.inertia_tensor(pts)
    off = np.abs(it - np.diag(np.diag(it)))
    assert off.max() < 2e-2, f"非対角が大きい:\n{it}"


# --------------------------------------------------------------------------- #
# 4. shape_distance: 識別性                                                    #
# --------------------------------------------------------------------------- #
def test_shape_distance_discriminates_rod_vs_sphere():
    """細長い棒 vs 球で shape_distance が明確に大きく、同形状では ~0。"""
    sphere = M.moment_invariants(_solid_sphere(n=6000, r=1.0, seed=201))
    sphere2 = M.moment_invariants(_solid_sphere(n=6000, r=5.0, seed=202))  # 別サンプル+別スケール
    rod = M.moment_invariants(_rod(n=6000, length=6.0, thick=0.15, seed=203))

    d_same = M.shape_distance(sphere, sphere2)
    d_diff = M.shape_distance(sphere, rod)

    # 同形状(球どうし、スケール違い)は不変性によりほぼ 0。
    assert d_same < 0.02, f"同形状の距離が大きすぎる: {d_same:.4f}"
    # 異形状(棒 vs 球)は明確に大きい。
    assert d_diff > 0.5, f"異形状の距離が小さすぎる: {d_diff:.4f}"
    # 少なくとも一桁以上の分離。
    assert d_diff > 20.0 * d_same


def test_shape_distance_zero_for_identical_transformed():
    """同一形状を剛体変換+スケールしても距離 ~0(不変性の直接確認)。"""
    pts = _solid_ellipsoid(n=5000, axes=(2.2, 1.1, 0.9), seed=211)
    R = _rot_matrix(seed=41)
    a = M.moment_invariants(pts)
    b = M.moment_invariants(9.9 * (pts @ R.T) + np.array([1.0, 2.0, 3.0]))
    assert M.shape_distance(a, b) < 1e-8


# --------------------------------------------------------------------------- #
# 5. 入力検証(fail-closed)                                                   #
# --------------------------------------------------------------------------- #
def test_input_validation():
    """不正入力を明示的な ValueError で弾く。"""
    with pytest.raises(ValueError):
        M.moment_invariants(np.zeros((5, 2)))          # (N,2) 次元違い
    with pytest.raises(ValueError):
        M.moment_invariants(np.array([[1.0, 2.0, np.nan]] * 3))  # NaN
    with pytest.raises(ValueError):
        M.moment_invariants(np.zeros((10, 3)))         # 全点一致 → RMS=0 で縮退
    with pytest.raises(ValueError):
        M.shape_distance(np.zeros(5), np.zeros(4))     # 長さ不一致
