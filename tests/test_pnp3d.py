"""pnp3d — PnP/DLT 姿勢推定の ground-truth 検証(既知姿勢で投影→復元)。"""
import numpy as np
import pnp3d as P


def _rot(ax, deg):
    a = np.asarray(ax, float); a /= np.linalg.norm(a); th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


_K = np.array([[800.0, 0, 320.0], [0, 800.0, 240.0], [0, 0, 1.0]])


def _scene(seed=0, n=40):
    rng = np.random.default_rng(seed)
    return rng.uniform([-3, -3, -3], [3, 3, 3], (n, 3))


def _rerr(Re, Rg):
    return np.degrees(np.arccos(np.clip((np.trace(Re.T @ Rg) - 1) / 2, -1, 1)))


def test_dlt_recovers_known_pose():
    """既知 R,t で投影 → dlt_pose が姿勢を復元(再投影 ~0)。"""
    X = _scene(0)
    Rg = _rot([0.2, 1, 0.3], 25.0); tg = np.array([0.5, -0.3, 12.0])
    x = P._project(X, _K, Rg, tg)
    R, t = P.dlt_pose(X, x, _K)
    assert _rerr(R, Rg) < 0.1, f"rot err {_rerr(R, Rg):.4f}"
    assert np.linalg.norm(t - tg) < 1e-2, f"t err {np.linalg.norm(t - tg):.5f}"
    assert P.reprojection_error(X, x, _K, R, t) < 1e-3


def test_reprojection_zero_for_true_pose():
    """真の姿勢での再投影誤差はゼロ。"""
    X = _scene(1)
    Rg = _rot([1, 0, 0], 10.0); tg = np.array([0, 0, 10.0])
    x = P._project(X, _K, Rg, tg)
    assert P.reprojection_error(X, x, _K, Rg, tg) < 1e-9


def test_pnp_ransac_with_outliers():
    """2D 対応の 25% を外れ値にしても RANSAC が姿勢を復元。"""
    X = _scene(2, n=60)
    Rg = _rot([0.3, 0.5, 1.0], 30.0); tg = np.array([1.0, 0.5, 14.0])
    x = P._project(X, _K, Rg, tg)
    rng = np.random.default_rng(3)
    n_out = 15
    x_noisy = x.copy()
    x_noisy[:n_out] += rng.uniform(-80, 80, (n_out, 2))  # 外れ値
    R, t, inliers, info = P.pnp_ransac(X, x_noisy, _K, thresh=2.0, iters=400)
    assert _rerr(R, Rg) < 1.0, f"rot err {_rerr(R, Rg):.3f}"
    assert np.linalg.norm(t - tg) < 0.2
    # 外れ値の大半が除外される
    assert inliers[:n_out].sum() <= 2 and inliers[n_out:].sum() >= 40


def test_depth_positive_convention():
    """復元姿勢で全点がカメラ前方(depth>0)。"""
    X = _scene(4)
    Rg = _rot([0, 1, 0], 15.0); tg = np.array([0.2, 0.1, 11.0])
    x = P._project(X, _K, Rg, tg)
    R, t = P.dlt_pose(X, x, _K)
    depth = (R @ X.T).T[:, 2] + t[2]
    assert np.all(depth > 0)


def test_insufficient_points_raises():
    import pytest
    with pytest.raises(ValueError):
        P.dlt_pose(np.zeros((5, 3)), np.zeros((5, 2)), _K)


def _coplanar_scene(seed=0, n=30):
    """全点 z=0 の共平面シーン(チェッカーボード相当)。"""
    rng = np.random.default_rng(seed)
    X = np.zeros((n, 3))
    X[:, :2] = rng.uniform(-3, 3, (n, 2))
    return X


def test_dlt_coplanar_raises():
    """[3] 共平面な 3D 点(z=0)では DLT が縮退するので ValueError で拒否。

    旧挙動: 例外なく reproj≈4e4px のゴミ姿勢を返す → このテストは FAIL。
    新挙動: fail-closed で ValueError を送出 → PASS。
    """
    import pytest
    X = _coplanar_scene(0)
    Rg = _rot([0.2, 1, 0.3], 25.0); tg = np.array([0.5, -0.3, 12.0])
    x = P._project(X, _K, Rg, tg)
    with pytest.raises(ValueError):
        P.dlt_pose(X, x, _K)


def test_coplanarity_ratio_separates_planar_from_volumetric():
    """共平面判定量: 平面≈0、立体シーンは有意に大きい(閾値の妥当性を符号化)。"""
    X_plane = _coplanar_scene(1)
    X_vol = _scene(1, n=40)
    assert P.coplanarity_ratio(X_plane) < P._COPLANAR_TOL
    assert P.coplanarity_ratio(X_vol) > 1e-2


def test_pnp_ransac_coplanar_fails_closed():
    """[4] 共平面入力で pnp_ransac が「100% コンセンサス」を詐称しない。

    旧挙動: info={'n_inliers':n,'inlier_ratio':1.0,'fallback':True}(rms 欠落)を返し
            47°ずれの姿勢を完璧と偽る → FAIL。
    新挙動: DLT 不能を fail-closed で ValueError にする → PASS。
    """
    import pytest
    X = _coplanar_scene(2)
    Rg = _rot([0.3, 0.5, 1.0], 30.0); tg = np.array([1.0, 0.5, 14.0])
    x = P._project(X, _K, Rg, tg)
    with pytest.raises(ValueError):
        P.pnp_ransac(X, x, _K, thresh=2.0, iters=200)


def test_pnp_ransac_fallback_reports_honest_metrics():
    """[4] 非共平面だが合意不十分で fallback した際、info を実測で honest に報告する。

    全 2D 点に大ノイズ → RANSAC は 6 inlier に届かず fallback。
    旧挙動: inlier_ratio=1.0・n_inliers=n・rms 欠落の詐称 → FAIL。
    新挙動: rms を載せ、inlier_ratio は実測 inlier(err<thresh)の割合 → PASS。
    """
    rng = np.random.default_rng(11)
    X = _scene(11, n=20)
    Rg = _rot([0.3, 0.5, 1.0], 30.0); tg = np.array([1.0, 0.5, 14.0])
    x = P._project(X, _K, Rg, tg)
    x_noisy = x + rng.uniform(-200, 200, x.shape)  # 全点を破壊
    R, t, mask, info = P.pnp_ransac(X, x_noisy, _K, thresh=2.0, iters=300)
    assert info.get("fallback") is True
    assert "rms" in info, "fallback でも再投影 RMS を報告すること"
    # 詐称禁止: 全点が inlier のはずがない
    assert info["inlier_ratio"] < 1.0
    # info は実測 mask と整合していること
    assert info["n_inliers"] == int(mask.sum())
    assert abs(info["inlier_ratio"] - mask.mean()) < 1e-12
    # rms は実際の再投影誤差と一致(捏造でない)
    assert abs(info["rms"] - P.reprojection_error(X, x_noisy, _K, R, t)) < 1e-9
