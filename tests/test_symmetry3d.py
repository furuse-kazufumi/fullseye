"""symmetry3d の GT 検証: 楕円体=反射対称・非対称形状=スコア大・円柱=回転対称。"""
import numpy as np

import symmetry3d as S


def _fib_sphere(n, seed=0):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th), np.cos(phi)], 1)


def _ellipsoid(n, abc=(2.0, 1.0, 0.5)):
    return _fib_sphere(n) * np.asarray(abc)


def _cylinder(n_th, n_z, R=1.0, H=4.0):
    th = np.linspace(0, 2 * np.pi, n_th, endpoint=False)
    zz = np.linspace(-H / 2, H / 2, n_z)
    T, Z = np.meshgrid(th, zz)
    return np.stack([R * np.cos(T).ravel(), R * np.sin(T).ravel(), Z.ravel()], 1)


def test_ellipsoid_is_reflection_symmetric():
    pts = _ellipsoid(1000)
    out = S.detect_reflection_symmetry(pts)
    # 楕円体は主軸平面で対称 → スコア小(点間隔/半径オーダー)
    assert out["score"] < 0.6, out["score"]
    # 3 主軸すべて対称面(全スコアが小=点間隔オーダー)
    assert max(out["all_scores"]) < 0.7, out["all_scores"]


def test_asymmetric_shape_scores_worse():
    pts = _ellipsoid(1000)
    sym_score = S.detect_reflection_symmetry(pts)["score"]
    # 片側(+x)に鏡映相手のいない突起を付ける → 対称性が崩れる
    rng = np.random.default_rng(0)
    bump = np.array([2.6, 0.9, 0.4]) + rng.normal(0, 0.08, (250, 3))  # 軸外=全主軸平面の対称を破る
    asym = np.vstack([pts, bump])
    asym_score = S.detect_reflection_symmetry(asym)["score"]
    assert asym_score > 1.5 * sym_score, (asym_score, sym_score)


def test_cylinder_is_rotationally_symmetric_about_axis():
    pts = _cylinder(60, 30, R=1.0, H=4.0)
    out = S.detect_rotational_symmetry(pts, orders=(2, 4, 8))
    # 円柱は軸(z)まわり回転対称 → スコア小、軸が z に整列
    assert out["score"] < 0.1, out["score"]
    assert abs(abs(out["axis_dir"][2]) - 1.0) < 0.05, out["axis_dir"]


def test_reflect_is_involution():
    # 2 回鏡映すると元に戻る(反射は対合)
    pts = _ellipsoid(200)
    n = np.array([1.0, 2.0, 0.5])
    r2 = S.reflect_points(S.reflect_points(pts, [0, 0, 0], n), [0, 0, 0], n)
    assert np.max(np.linalg.norm(r2 - pts, axis=1)) < 1e-9


def test_scale_invariance_of_score():
    pts = _ellipsoid(800)
    s1 = S.detect_reflection_symmetry(pts)["score"]
    s2 = S.detect_reflection_symmetry(pts * 1000.0)["score"]   # 座標 1000 倍 → 正規化で不変
    assert abs(s1 - s2) < 1e-6, (s1, s2)
