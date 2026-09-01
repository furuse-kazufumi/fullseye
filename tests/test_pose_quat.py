# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pose_quat(四元数・双対四元数による剛体変換代数)の契約テスト。

このモジュールは 2026-09-01 まで **どちらの facade からも 1 つも引けない**
状態だった(module-only)。公開面に出すにあたって敵対監査をかけたところ、
正規化が `norm + 1e-12` で割っていたために **2 通りの無言の誤り**が同居して
いた ―― どちらも例外も NaN も出ない:

  1. **零ベクトルが通る。** ``quat_normalize([0,0,0,0])`` が ``[0,0,0,0]`` を
     返し、それを回転行列にすると **単位行列**になる。「回転が定義できない」
     が「回転しない」に化ける ―― 姿勢推定で最悪の化け方である。
  2. **正しい入力まで系統的に縮む。** 商のノルムが 1 をわずかに下回るので、
     そこから作った回転行列が直交から外れる(実測 |RᵀR − I| = 4.0e-12)。
     丸め誤差ではなく一方向の縮みなので、合成を重ねるほど溜まる。

以下はその回帰である。
"""
import numpy as np
import pytest

import pose_quat as pq


# --------------------------------------------------------------------------- #
# 1. 零長は「回転しない」ではなく「定義できない」                                #
# --------------------------------------------------------------------------- #
def test_degenerate_input_is_refused_rather_than_silently_becoming_identity():
    with pytest.raises(ValueError, match="zero length"):
        pq.quat_normalize([0.0, 0.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="zero length"):
        pq.axis_angle_to_quat(0.0, 0.0, 0.0, 1.0)      # 軸の無い回転要求
    with pytest.raises(ValueError, match="zero length"):
        pq.dual_quat_normalize(np.zeros(8))
    with pytest.raises(ValueError, match="zero length"):
        pq.screw_to_dual_quat(0.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def test_non_finite_input_is_refused():
    for bad in ([np.nan, 0.0, 0.0, 1.0], [np.inf, 0.0, 0.0, 1.0]):
        with pytest.raises(ValueError):
            pq.quat_normalize(bad)


# --------------------------------------------------------------------------- #
# 2. 正しい入力は厳密に単位化される(系統的な縮みを許さない)                     #
# --------------------------------------------------------------------------- #
def test_a_rotor_is_exactly_unit_and_its_matrix_is_orthogonal():
    """εを分母に足すと直交性が 4e-12 ずれていた。丸め誤差の桁まで戻すこと。"""
    rng = np.random.default_rng(0)
    worst_norm, worst_orth = 0.0, 0.0
    for _ in range(64):
        axis = rng.standard_normal(3)
        ang = float(rng.uniform(-np.pi, np.pi))
        q = pq.axis_angle_to_quat(*axis, ang)
        worst_norm = max(worst_norm, abs(float(np.linalg.norm(q)) - 1.0))
        R = np.asarray(pq.quat_to_hom_mat3d(q))[:3, :3]
        worst_orth = max(worst_orth, float(np.abs(R.T @ R - np.eye(3)).max()))
    assert worst_norm < 1e-15, "ロータが単位長でない(縮みが残っている)"
    assert worst_orth < 1e-14, (
        "回転行列が直交していない: %.3g — 分母に ε を足していないか" % worst_orth)


def test_the_shrink_would_have_been_visible_at_this_tolerance():
    """この検査が実際に旧実装を落とすことの確認(空振りしていないこと)。

    旧実装は ``q / (norm + 1e-12)`` だった。同じ式を再現して、上の許容差を
    確かに超えることを示す ―― 超えないなら検査に意味が無い。
    """
    q = pq.axis_angle_to_quat(0.0, 0.0, 1.0, np.pi / 2)
    old = q / (float(np.linalg.norm(q)) + 1e-12)       # 旧実装の再現
    R = np.asarray(pq.quat_to_hom_mat3d(old))[:3, :3]
    assert float(np.abs(R.T @ R - np.eye(3)).max()) > 1e-13


# --------------------------------------------------------------------------- #
# 3. 代数として正しいこと(独立な経路で確かめる)                                 #
# --------------------------------------------------------------------------- #
def test_rotation_agrees_with_the_matrix_route():
    """四元数のサンドイッチ積と回転行列の積が一致すること。"""
    rng = np.random.default_rng(1)
    for _ in range(32):
        q = pq.axis_angle_to_quat(*rng.standard_normal(3),
                                  float(rng.uniform(-np.pi, np.pi)))
        p = rng.standard_normal(3)
        by_quat = np.asarray(pq.quat_rotate_point_3d(q, *p))
        by_mat = np.asarray(pq.quat_to_hom_mat3d(q))[:3, :3] @ p
        assert np.allclose(by_quat, by_mat, atol=1e-13)


def test_composition_stays_on_the_unit_sphere():
    """合成を重ねても単位長から外れないこと(縮みの累積を検出する)。"""
    rng = np.random.default_rng(2)
    q = pq.axis_angle_to_quat(0.0, 0.0, 1.0, 0.01)
    for _ in range(2000):
        q = pq.quat_normalize(pq.quat_compose(
            q, pq.axis_angle_to_quat(*rng.standard_normal(3), 0.01)))
    assert abs(float(np.linalg.norm(q)) - 1.0) < 1e-12


def test_conjugate_inverts_a_rotation():
    q = pq.axis_angle_to_quat(0.3, -0.7, 0.2, 1.1)
    p = np.array([0.4, -1.2, 2.0])
    back = pq.quat_rotate_point_3d(pq.quat_conjugate(q),
                                   *pq.quat_rotate_point_3d(q, *p))
    assert np.allclose(np.asarray(back), p, atol=1e-13)
