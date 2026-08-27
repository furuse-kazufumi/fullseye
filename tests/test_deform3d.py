"""deform3d(3D 非剛体・変形レジストレーション)テスト。

ground-truth 検証:
    - TPS 厳密内挿: 制御点対応をそのまま与えたら tps_warp が dst_ctrl に一致(λ=0)。
    - 既知変形の回復: クリーン格子に既知の滑らかな sin ベース曲げを掛け、
      register_nonrigid の最終 RMS が初期ズレの 1/10 以下へ縮むこと。
    - 剛体版: 既知の回転+並進を register_cpd_rigid が回復すること。

すべて numpy in / numpy out。scipy が無ければ skip。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")

import deform3d as d3  # noqa: E402


# --------------------------------------------------------------------------- #
# 入力生成ヘルパ                                                              #
# --------------------------------------------------------------------------- #
def _grid(n=6, lo=0.1, hi=0.9):
    """[lo,hi]^3 の n×n×n 構造格子(NN 対応が意味を持つ)。"""
    g = np.linspace(lo, hi, n)
    gx, gy, gz = np.meshgrid(g, g, g, indexing="ij")
    return np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)


def _smooth_bend(P, amp):
    """既知の滑らかな非線形変形(sin ベースの曲げ)。"""
    return P + amp * np.stack(
        [np.sin(np.pi * P[:, 1]),
         0.5 * np.sin(np.pi * P[:, 2]),
         0.3 * np.sin(np.pi * P[:, 0])], axis=1)


def _rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _rot_xyz(ax, ay, az):
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    Rz = _rot_z(az)
    return Rz @ Ry @ Rx


def _rms(a, b):
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


# --------------------------------------------------------------------------- #
# TPS 厳密内挿                                                                #
# --------------------------------------------------------------------------- #
def test_tps_exact_interpolation_at_controls():
    """λ=0 なら制御点上で厳密内挿(warp(src_ctrl) == dst_ctrl)。"""
    rng = np.random.default_rng(20260827)
    src_ctrl = rng.random((25, 3))
    dst_ctrl = src_ctrl + 0.1 * rng.standard_normal((25, 3))

    model = d3.tps_fit(src_ctrl, dst_ctrl, lam=0.0)
    out = d3.tps_warp(model, src_ctrl)

    assert out.shape == dst_ctrl.shape
    resid = np.max(np.abs(out - dst_ctrl))
    assert resid < 1e-8, f"厳密内挿の残差が大きい: {resid:.2e}"


def test_tps_identity_map():
    """恒等対応(dst==src)なら任意点で恒等写像。"""
    rng = np.random.default_rng(1)
    ctrl = rng.random((30, 3))
    model = d3.tps_fit(ctrl, ctrl, lam=0.0)
    q = rng.random((50, 3))
    out = d3.tps_warp(model, q)
    assert _rms(out, q) < 1e-8


def test_tps_reproduces_pure_affine():
    """純アフィン変形(A x + c)は TPS が厳密再現(曲げ項 w≈0)。"""
    rng = np.random.default_rng(7)
    ctrl = rng.random((40, 3))
    A = np.array([[1.2, 0.1, 0.0], [-0.05, 0.9, 0.2], [0.0, 0.1, 1.1]])
    c = np.array([0.3, -0.2, 0.15])
    dst = ctrl @ A.T + c
    model = d3.tps_fit(ctrl, dst, lam=0.0)
    q = rng.random((60, 3))
    out = d3.tps_warp(model, q)
    exact = q @ A.T + c
    assert _rms(out, exact) < 1e-7
    assert np.max(np.abs(model["w"])) < 1e-6  # アフィンは曲げ項ゼロ


def test_tps_warp_single_point_shape():
    """長さ3の1次元入力は (3,) を返す。"""
    rng = np.random.default_rng(2)
    ctrl = rng.random((10, 3))
    model = d3.tps_fit(ctrl, ctrl + 0.05, lam=0.0)
    out = d3.tps_warp(model, np.array([0.5, 0.5, 0.5]))
    assert out.shape == (3,)


def test_tps_regularization_smooths():
    """λ>0 は制御点上で厳密内挿を緩める(残差 > 0)。"""
    rng = np.random.default_rng(3)
    src_ctrl = rng.random((30, 3))
    dst_ctrl = src_ctrl + 0.2 * rng.standard_normal((30, 3))
    m0 = d3.tps_fit(src_ctrl, dst_ctrl, lam=0.0)
    m1 = d3.tps_fit(src_ctrl, dst_ctrl, lam=0.5)
    r0 = _rms(d3.tps_warp(m0, src_ctrl), dst_ctrl)
    r1 = _rms(d3.tps_warp(m1, src_ctrl), dst_ctrl)
    assert r0 < 1e-8 < r1  # λ=0 は厳密、λ>0 は緩む


# --------------------------------------------------------------------------- #
# 非剛体レジストレーション: 既知変形の回復                                    #
# --------------------------------------------------------------------------- #
def test_register_nonrigid_recovers_known_bend():
    """既知の滑らかな曲げを掛けた dst を register_nonrigid が回復(RMS 1/10 以下)。"""
    src = _grid(n=6)                 # 216 点、格子間隔 ~0.16
    amp = 0.08                       # 間隔より小さい変形 → NN 対応が有効
    dst = _smooth_bend(src, amp)     # 既知変形。dst[i] は src[i] の真の像

    init_rms = _rms(src, dst)        # 初期ズレ(恒等)
    warped, model, info = d3.register_nonrigid(src, dst, iters=40, lam=0.02)

    # ground-truth: dst と要素対応が既知なので真の RMS を直接評価
    final_rms = _rms(warped, dst)
    assert final_rms < init_rms / 10.0, (
        f"回復不十分: init={init_rms:.5f} final={final_rms:.5f} "
        f"(ratio={init_rms / max(final_rms, 1e-12):.1f}x)")

    # 返り値の健全性
    assert warped.shape == src.shape
    assert model is not None
    assert info["rms"] <= info["rms_init"] + 1e-12
    # 返した model は原座標系でそのまま warp に使え、warped を再現する
    assert _rms(d3.tps_warp(model, src), warped) < 1e-9


def test_register_nonrigid_scale_invariance():
    """座標を 100 倍しても λ 相対解釈で回復率は不変。"""
    src = _grid(n=5)
    dst = _smooth_bend(src, 0.08)
    _, _, i1 = d3.register_nonrigid(src, dst, iters=40, lam=0.02)
    _, _, i2 = d3.register_nonrigid(src * 100.0, dst * 100.0, iters=40, lam=0.02)
    ratio1 = i1["rms_init"] / max(i1["rms"], 1e-12)
    ratio2 = i2["rms_init"] / max(i2["rms"], 1e-12)
    assert abs(ratio1 - ratio2) / ratio1 < 1e-3


def test_register_nonrigid_k_smooth_runs():
    """k_smooth(近傍平均による軟対応)経路が動作し、健全な出力を返すこと。

    注意: 近傍平均は局所重心へ寄せる幾何バイアスを生むため、構造的/クリーンな
    点群ではハード 1-NN(k_smooth=None)より劣り得る。ここでは経路の健全性
    (有限・正しい形状・model 一致)を検証する(改善は主張しない)。
    """
    src = _grid(n=5)
    dst = _smooth_bend(src, 0.06)
    warped, model, info = d3.register_nonrigid(src, dst, iters=40, lam=0.02, k_smooth=3)
    assert warped.shape == src.shape
    assert np.all(np.isfinite(warped))
    assert model is not None
    assert _rms(d3.tps_warp(model, src), warped) < 1e-9
    assert info["rms"] <= info["rms_init"] + 1e-12  # 発散ガード(対応 RMS)


def test_register_nonrigid_never_worse_than_init():
    """発散ガード: 過大な λ でも初期より悪い結果を返さない。"""
    src = _grid(n=5)
    dst = _smooth_bend(src, 0.1)
    warped, _, info = d3.register_nonrigid(src, dst, iters=30, lam=50.0)
    assert info["rms"] <= info["rms_init"] + 1e-9


# --------------------------------------------------------------------------- #
# 剛体版 CPD: 既知の回転+並進の回復                                           #
# --------------------------------------------------------------------------- #
def test_register_cpd_rigid_recovers_rotation_translation():
    """既知の回転+並進を CPD 剛体版が回復する。"""
    rng = np.random.default_rng(20260827)
    src = rng.random((120, 3))
    R0 = _rot_xyz(0.15, -0.2, 0.3)
    t0 = np.array([0.4, -0.25, 0.1])
    dst = src @ R0.T + t0            # dst ≈ src @ R.T + t

    R, t, info = d3.register_cpd_rigid(src, dst, iters=100)

    # 回転・並進が真値に一致
    assert np.max(np.abs(R - R0)) < 1e-3, f"R 誤差大:\n{R - R0}"
    assert np.max(np.abs(t - t0)) < 1e-3, f"t 誤差大: {t - t0}"
    # 変換後 src が dst に一致
    assert _rms(src @ R.T + t, dst) < 1e-3
    # R は正規直交・行列式 +1
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-6)
    assert abs(np.linalg.det(R) - 1.0) < 1e-6


def test_register_cpd_rigid_improves_from_misalignment():
    """初期ズレが大きい構造点群でも RMSE を大きく縮める。"""
    rng = np.random.default_rng(5)
    src = _grid(n=5)
    R0 = _rot_z(0.4)
    t0 = np.array([0.2, 0.1, -0.15])
    dst = src @ R0.T + t0
    init = _rms(src, dst)
    R, t, info = d3.register_cpd_rigid(src, dst, iters=150)
    assert info["rmse"] < init / 10.0


def test_register_cpd_rigid_outlier_constant_myronenko_scale():
    """外れ値定数が Myronenko&Song 標準形か(w の意味が正しく効くか)。

    root cause 回帰: E ステップ分母の一様(外れ値)項は
        c = (2πσ²)^(D/2) · (w/(1-w)) · (M/N)
    でなければならない。以前の実装は c_const に余分な (2π)^(D/2) を含み、
    D=3 では外れ値オッズ w/(1-w) が (2π)^1.5 ≈ 15.75 倍に化けていた
    (例: w=0.3 → 実効 w≈0.871)。

    その 15.75x 誤スケールを検出する決定的テスト:
    完全対応(厳密一致)のクリーン点群では、σ² が反復で 0 へ縮み真の対応が
    支配的になるため、1 未満の高い w(外れ値割合を高く見積もった事前)でも
    剛体変換は厳密に回復されねばならない。バグ版は外れ値項が 15.75x 過大で
    高 w 域が崩壊(σ² が縮まず恒等変換のまま停滞 → rmse が初期ズレ級に残る)。
    正しい標準形なら w=0.97/0.99 でも rmse≈0 に回復する。
    """
    g = _grid(n=5)                       # 125 点、厳密対応(ノイズ・外れ値なし)
    R0 = _rot_xyz(0.15, -0.2, 0.3)
    t0 = np.array([0.3, -0.2, 0.15])
    dst = g @ R0.T + t0                  # dst[i] は src[i] の厳密な像
    init = _rms(g, dst)

    # w が「外れ値割合」なら、実データが 100% inlier(厳密一致)である限り
    # 1 に近い高 w でも σ² 収縮で真の対応が勝ち、変換を厳密回復できる。
    for w in (0.97, 0.99):
        R, t, info = d3.register_cpd_rigid(g, dst, iters=400, w=w)
        rec = _rms(g @ R.T + t, dst)
        # 旧(バグ)挙動: rec ~ init 級(崩壊)。新(正)挙動: rec ≈ 0。
        assert rec < init / 1e3, (
            f"w={w} で回復失敗 rec={rec:.3e} init={init:.3e} "
            f"(外れ値定数の 15.75x 誤スケール回帰の疑い)")
        assert np.max(np.abs(R - R0)) < 1e-3
        assert np.max(np.abs(t - t0)) < 1e-3

    # w=0(外れ値項ゼロ)は誤スケールの影響を受けない基準として厳密回復する。
    R0i, t0i, _ = d3.register_cpd_rigid(g, dst, iters=400, w=0.0)
    assert _rms(g @ R0i.T + t0i, dst) < init / 1e3


# --------------------------------------------------------------------------- #
# エラー処理                                                                  #
# --------------------------------------------------------------------------- #
def test_tps_fit_shape_errors():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        d3.tps_fit(rng.random((10, 2)), rng.random((10, 2)))   # (N,2) 不正
    with pytest.raises(ValueError):
        d3.tps_fit(rng.random((10, 3)), rng.random((9, 3)))    # 点数不一致
    with pytest.raises(ValueError):
        d3.tps_fit(rng.random((3, 3)), rng.random((3, 3)))     # 制御点不足(<4)
    with pytest.raises(ValueError):
        d3.tps_fit(rng.random((10, 3)), rng.random((10, 3)), lam=-1.0)  # λ<0


def test_tps_fit_rejects_nonfinite():
    rng = np.random.default_rng(0)
    bad = rng.random((10, 3))
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        d3.tps_fit(bad, rng.random((10, 3)))


def test_tps_warp_rejects_bad_model():
    with pytest.raises(ValueError):
        d3.tps_warp({"w": np.zeros((4, 3))}, np.zeros((5, 3)))  # ctrl/a 欠落


def test_register_cpd_rigid_rejects_bad_w():
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        d3.register_cpd_rigid(rng.random((10, 3)), rng.random((10, 3)), w=1.0)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
