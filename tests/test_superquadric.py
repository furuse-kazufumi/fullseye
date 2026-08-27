"""superquadric.py の ground-truth テスト(既知の楕円体/箱を生成して閉形式で検証)。

スーパー2次曲面は表面点が厳密に内外関数 F=1 を満たす(cos^2+sin^2 が指数を
打ち消す)ので、まず F の閉形式値を機械精度で検証する。続いて既知パラメータの
表面をサンプル→fit_superquadric で半径 a・形状指数 eps・姿勢 (R,t) を復元し、
相対誤差で数値照合する。回転は主軸の符号任意性があるため a は主軸ソートで比較。
tolerance の根拠は各テストの docstring に明記(ノイズ無し=機械精度近く、
ノイズ有り=実測誤差から honest に設定)。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")

import superquadric as sq
from scipy.spatial.transform import Rotation


def _sorted_axes(a):
    """半径を降順ソート(主軸ラベルの任意性を吸収して順不同比較する)。"""
    return np.sort(np.asarray(a, float))[::-1]


# ═══════════════════════════════════════════════════════════════════════════
# 内外関数 F
# ═══════════════════════════════════════════════════════════════════════════
def test_inside_outside_surface_center_far():
    """F: 表面点で 1(<1e-6)、中心で <1、遠方で >1。閉形式との一致を機械精度で。"""
    a = (2.0, 1.0, 0.5)
    eps = (1.0, 1.0)
    surf = sq.sample_surface(a, eps, 40, 40)
    F_surf = sq.inside_outside(surf, a, eps)
    assert np.max(np.abs(F_surf - 1.0)) < 1e-6      # 表面は厳密に F=1

    F_center = float(sq.inside_outside(np.zeros((1, 3)), a, eps)[0])
    assert F_center < 1.0
    assert F_center == pytest.approx(0.0, abs=1e-12)  # 中心は F=0

    # 遠方点: 楕円体なので (x/a1)^2+(y/a2)^2+(z/a3)^2、eps=1 は真の楕円体二次形式。
    far = np.array([[10.0, 10.0, 10.0]])
    F_far = float(sq.inside_outside(far, a, eps)[0])
    assert F_far > 1.0
    assert F_far == pytest.approx((10 / 2) ** 2 + (10 / 1) ** 2 + (10 / 0.5) ** 2, rel=1e-12)


def test_inside_outside_pose_roundtrip():
    """F は姿勢不変: 表面点を (R,t) で動かし同 (R,t) を渡せば F=1 を保つ。"""
    a = (1.5, 0.8, 0.6)
    eps = (0.7, 1.2)
    R = Rotation.from_rotvec([0.3, -0.6, 0.9]).as_matrix()
    t = np.array([2.0, -1.0, 0.5])
    surf = sq.sample_surface(a, eps, 40, 40, R=R, t=t)
    F = sq.inside_outside(surf, a, eps, R=R, t=t)
    assert np.max(np.abs(F - 1.0)) < 1e-6


# ═══════════════════════════════════════════════════════════════════════════
# フィット
# ═══════════════════════════════════════════════════════════════════════════
def test_fit_ellipsoid_recovers_axes_and_eps():
    """楕円体 eps=(1,1),a=(2,1,0.5): a を相対誤差<10%、eps≈1(±0.3)で復元。

    ノイズ無し表面サンプルで初期姿勢(主軸)がほぼ厳密解のため機械精度近くまで
    収束する(実測 max_rel_err≈0)。tolerance はマージンを取り 10% / 0.3。
    """
    a_true = np.array([2.0, 1.0, 0.5])
    eps_true = np.array([1.0, 1.0])
    P = sq.sample_surface(a_true, eps_true, 50, 50)
    res = sq.fit_superquadric(P)

    a_fit = _sorted_axes(res["a"])
    rel = np.abs(a_fit - a_true) / a_true
    assert np.max(rel) < 0.10, f"a rel err too big: {rel}"
    assert res["eps"] == pytest.approx(1.0, abs=0.3)
    assert res["residual"] < 1e-4


def test_fit_box_recovers_small_eps():
    """箱状 eps=(0.2,0.2): fit 後の eps が明確に小さく回復(< 0.6)。

    初期 eps=1(楕円体)から角ばりを表す小 eps へ降下できることを確認。
    実測では 0.2 付近まで戻る(閾値 0.6 は十分な安全マージン)。
    """
    a_true = np.array([1.0, 1.0, 1.0])
    eps_true = np.array([0.2, 0.2])
    P = sq.sample_surface(a_true, eps_true, 50, 50)
    res = sq.fit_superquadric(P)

    assert res["eps"][0] < 0.6, f"eps1 not small: {res['eps']}"
    assert res["eps"][1] < 0.6, f"eps2 not small: {res['eps']}"
    # 半径も回復(a=1 の立方体、相対誤差<10%)
    a_fit = _sorted_axes(res["a"])
    assert np.max(np.abs(a_fit - a_true) / a_true) < 0.10


def test_fit_under_rotation_translation():
    """ランダム回転+並進下でも residual が小さく a が回復(主軸ソート比較)。"""
    a_true = np.array([2.0, 1.0, 0.5])
    eps_true = np.array([1.0, 1.0])
    R = Rotation.random(random_state=11).as_matrix()
    t = np.array([3.0, -2.0, 1.5])
    P = sq.sample_surface(a_true, eps_true, 50, 50, R=R, t=t)
    res = sq.fit_superquadric(P)

    a_fit = _sorted_axes(res["a"])
    assert np.max(np.abs(a_fit - a_true) / a_true) < 0.10
    assert res["residual"] < 1e-4
    # 中心(並進)も回復
    assert np.allclose(res["t"], t, atol=0.05)


def test_fit_robust_to_noise():
    """ガウスノイズ(sigma=0.02)下でも a 相対誤差<10%・eps≈1(±0.3)を保つ。

    tolerance は実測(sigma=0.03 で max_rel_err≈0.025)からマージンを取って設定。
    """
    rng = np.random.default_rng(0)
    a_true = np.array([2.0, 1.0, 0.5])
    eps_true = np.array([1.0, 1.0])
    P = sq.sample_surface(a_true, eps_true, 50, 50)
    P = P + rng.normal(0.0, 0.02, P.shape)
    res = sq.fit_superquadric(P)

    a_fit = _sorted_axes(res["a"])
    assert np.max(np.abs(a_fit - a_true) / a_true) < 0.10
    assert res["eps"] == pytest.approx(1.0, abs=0.3)


def test_residual_zero_on_exact_surface():
    """superquadric_residual: 真パラメータ+厳密表面点で ~0(機械精度)。"""
    a = np.array([1.5, 1.0, 0.7])
    eps = np.array([0.8, 1.3])
    R = Rotation.from_rotvec([0.2, 0.5, -0.3]).as_matrix()
    t = np.array([-1.0, 2.0, 0.0])
    P = sq.sample_surface(a, eps, 40, 40, R=R, t=t)
    r = sq.superquadric_residual(P, a, eps, R, t)
    assert r < 1e-12


def test_sample_surface_shape():
    """sample_surface は (n_u*n_v, 3) を返す。"""
    P = sq.sample_surface((1, 1, 1), (1, 1), n_u=30, n_v=20)
    assert P.shape == (30 * 20, 3)
