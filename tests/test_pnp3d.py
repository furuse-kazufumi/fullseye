"""pnp3d — PnP/DLT 姿勢推定の ground-truth 検証(既知姿勢で投影→復元)。"""
import numpy as np
import pytest
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


def test_dlt_coplanar_is_solved_by_planar_pnp():
    """[3] 共平面な 3D 点(z=0)は一般 DLT が縮退する — 旧挙動は reproj≈4e4px のゴミ、
    その後 fail-closed で拒否。現在は平面 PnP(ホモモグラフィ分解)へ振り分けて
    正しく解く(チェッカーボードは PnP の主用途なので、拒否より解くのが正しい)。"""
    X = _coplanar_scene(0)
    Rg = _rot([0.2, 1, 0.3], 25.0); tg = np.array([0.5, -0.3, 12.0])
    x = P._project(X, _K, Rg, tg)
    R, t = P.dlt_pose(X, x, _K)
    assert _rerr(R, Rg) < 0.1, _rerr(R, Rg)
    assert np.linalg.norm(t - tg) < 1e-2
    assert P.reprojection_error(X, x, _K, R, t) < 1e-3


def test_coplanarity_ratio_separates_planar_from_volumetric():
    """共平面判定量: 平面≈0、立体シーンは有意に大きい(閾値の妥当性を符号化)。"""
    X_plane = _coplanar_scene(1)
    X_vol = _scene(1, n=40)
    assert P.coplanarity_ratio(X_plane) < P._COPLANAR_TOL
    assert P.coplanarity_ratio(X_vol) > P._COPLANAR_TOL


def test_pnp_ransac_coplanar_recovers_pose():
    """[4] 共平面入力の pnp_ransac: 旧挙動は 47° ずれの姿勢を「100% コンセンサス」と
    詐称、その後 ValueError。平面 PnP 経路で実際に姿勢を復元し、info.rms も実測値。"""
    X = _coplanar_scene(2)
    Rg = _rot([0.3, 0.5, 1.0], 30.0); tg = np.array([1.0, 0.5, 14.0])
    x = P._project(X, _K, Rg, tg)
    R, t, mask, info = P.pnp_ransac(X, x, _K, thresh=2.0, iters=200)
    assert _rerr(R, Rg) < 0.1
    assert mask.all()
    assert abs(info["rms"] - P.reprojection_error(X[mask], x[mask], _K, R, t)) < 1e-9


def test_collinear_points_fail_closed():
    """全点一直線は平面 PnP でも姿勢が定まらない → ValueError。"""
    import pytest
    X = np.outer(np.linspace(-2, 2, 12), [1.0, 0.5, 0.2])
    x = P._project(X, _K, np.eye(3), np.array([0, 0, 10.0]))
    with pytest.raises(ValueError):
        P.dlt_pose(X, x, _K)


# ── 2026-09-02 レビュー再現(正規化 / 準共平面 / 精密化)────────────────────── #
def _board_scene(thickness, seed=3, n=40):
    """2x2 の板を z=6 に置き、厚み ``thickness`` の法線方向ばらつきを持つ準共平面点群。"""
    r = np.random.default_rng(seed)
    X = r.uniform([-1, -1, 0], [1, 1, 0], (n, 3)) + np.array([0, 0, 6.0])
    X[:, 2] += r.normal(0, thickness, n)
    return X


_K500 = np.array([[500.0, 0, 320.0], [0, 500.0, 240.0], [0, 0, 1.0]])
_RG = _rot([0.1, -0.2, 0.06], 11.6)               # ~ euler xyz (5,-10,3) deg
_TG = np.array([0.5, 0.1, -0.2])


@pytest.mark.parametrize("thickness", [1e-3, 1e-2, 3e-2])
def test_near_planar_board_with_pixel_noise(thickness):
    """Regression: 厚み比 1e-2..5e-2 の準共平面板は旧 DLT(正規化なし・ガード 1e-6)で
    0.3 px ノイズでも回転 170° 級に破綻した。正規化 + 平面 PnP 候補 + LM 精密化で
    < 3° (実測 ~0.4°)。"""
    X = _board_scene(thickness)
    x = P._project(X, _K500, _RG, _TG)
    errs = []
    for trial in range(5):
        xn = x + np.random.default_rng(10 + trial).normal(0, 0.3, x.shape)
        R, t = P.dlt_pose(X, xn, _K500)
        errs.append(_rerr(R, _RG))
    assert max(errs) < 3.0, errs


def test_world_offset_does_not_degrade_pose():
    """Regression: 世界原点を (100,200,0) ずらすだけで旧 DLT は再投影 4.5 → 106 px に
    劣化した(素の座標で DLT を組んだ条件数悪化 + 原点回りの回転/並進の結合)。
    正規化 + 重心回りの精密化で原点位置に依らない。"""
    X = _scene(0, n=60) + np.array([0, 0, 12.0])
    x = P._project(X, _K500, _RG, _TG)
    base = None
    for off in (np.zeros(3), np.array([100.0, 200.0, 0.0]), np.array([1000.0, 0.0, 0.0])):
        Xo = X + off
        to = _TG - _RG @ off
        xo = P._project(Xo, _K500, _RG, to)
        assert np.allclose(xo, x, atol=1e-8)          # same image, shifted world origin
        xn = xo + np.random.default_rng(20).normal(0, 0.5, xo.shape)
        R, t, rms = P.pnp_pose(Xo, xn, _K500)
        if base is None:
            base = (_rerr(R, _RG), rms)
        assert abs(_rerr(R, _RG) - base[0]) < 1e-3, (off, _rerr(R, _RG), base)
        assert abs(rms - base[1]) < 1e-3
        assert rms < 1.0


def test_noisy_pose_matches_camera_solve_pnp():
    """0.5 px ノイズで camera.solve_pnp(射影の正典)と同等の姿勢精度・再投影 RMS。"""
    import camera
    X = _scene(5, n=60) + np.array([0, 0, 12.0])
    x = P._project(X, _K500, _RG, _TG)
    for trial in range(3):
        xn = x + np.random.default_rng(trial).normal(0, 0.5, x.shape)
        R, t, rms = P.pnp_pose(X, xn, _K500)
        Rc, tc, rmsc = camera.solve_pnp(X, xn, _K500)
        assert abs(rms - rmsc) < 1e-3 * max(1.0, rmsc), (rms, rmsc)
        assert _rerr(R, Rc) < 1e-2
        assert abs(rms - P.reprojection_error(X, xn, _K500, R, t)) < 1e-9


def test_pnp_pose_refine_false_is_the_initialiser():
    X = _scene(6, n=40) + np.array([0, 0, 12.0])
    x = P._project(X, _K500, _RG, _TG)
    R0, t0, rms0 = P.pnp_pose(X, x, _K500, refine=False)
    R1, t1, rms1 = P.pnp_pose(X, x, _K500)
    assert rms0 < 1e-6 and rms1 <= rms0 + 1e-12


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
