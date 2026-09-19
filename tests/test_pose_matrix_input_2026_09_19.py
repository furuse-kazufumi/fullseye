# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pose ヘルパは自分の出力(4×4 同次行列)を受けられる(GenSpark 第 14 報 D-1、2026-09-19)。

``pose_to_hom_mat3d_local(pose)`` の 4×4 を ``pose_to_quat`` に戻すと ``_pose_to_R`` の ``pose[4]`` で
IndexError(4×4 の 5 行目を引く)。直し = ``_as_pose`` が 6/7 ベクトル・3×3・4×4 を受け、他は何が要るかを言う。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fullseye as fs  # noqa: E402

POSE = np.array([0.1, 0.2, 0.3, 0.4, -0.2, 0.9])


def test_pose_helpers_accept_their_own_homogeneous_matrix():
    H = fs.pose_to_hom_mat3d_local(POSE)
    assert H.shape == (4, 4)
    assert np.allclose(fs.pose_to_quat(H), fs.pose_to_quat(POSE))
    assert np.allclose(fs.pose_to_dual_quat(H), fs.pose_to_dual_quat(POSE))
    assert np.allclose(fs.pose_to_hom_mat3d_local(H), H)            # 行列 → 行列は恒等


def test_pose_helpers_accept_a_rotation_matrix_with_zero_translation():
    H = fs.pose_to_hom_mat3d_local(POSE)
    q_from_R = fs.pose_to_quat(H[:3, :3])
    assert np.allclose(q_from_R, fs.pose_to_quat(POSE))
    dq = fs.pose_to_dual_quat(H[:3, :3])
    assert np.allclose(dq[4:], 0.0)                                  # 並進 0 → 双対部 0


def test_seven_element_pose_with_type_field_still_works():
    p7 = np.concatenate([POSE, [0.0]])
    assert np.allclose(fs.pose_to_quat(p7), fs.pose_to_quat(POSE))


@pytest.mark.parametrize("bad", [np.zeros(5), np.zeros((2, 2)), np.zeros((4, 4, 1)), {"tx": 0.1}, 0.5])
def test_other_shapes_say_what_a_pose_is(bad):
    with pytest.raises((ValueError, TypeError), match="pose must be"):
        fs.pose_to_quat(bad)
