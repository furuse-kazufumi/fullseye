# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""feat_shot.iss_keypoints — 特徴の無い平面からはどの向きでもキーポイントを出さない。

2026-10-11 まで、平面上の点の λ3(丸め屑)を saliency > 0 で通していたので、
軸に沿った平面では 0 個なのに、傾けた同じ平面では 203 個のキーポイントが出ていた。
角度を複数振って固定する(回転不変の主張は角度 1 つでは確かめられない)。
"""
import numpy as np
import pytest

import feat_shot


def _rot(ax, th):
    c, s = np.cos(th), np.sin(th)
    if ax == 0:
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


@pytest.mark.parametrize("ax,th", [(0, 0.0), (0, 0.7), (1, 0.3), (0, 1.9), (1, 2.6)])
def test_plane_has_no_keypoints_at_any_tilt(ax, th):
    rng = np.random.default_rng(0)
    p = np.c_[rng.random(1500), rng.random(1500), np.zeros(1500)]
    assert len(feat_shot.iss_keypoints(p @ _rot(ax, th).T, 0.08)) == 0


def test_curved_surface_still_yields_keypoints_rotation_stable():
    rng = np.random.default_rng(1)
    x, y = rng.random(1500), rng.random(1500)
    p = np.c_[x, y, 0.3 * np.sin(6 * x) * np.cos(5 * y)]
    n0 = len(feat_shot.iss_keypoints(p, 0.12))
    n1 = len(feat_shot.iss_keypoints(p @ _rot(0, 0.7).T, 0.12))
    assert n0 > 0 and n1 > 0
    assert abs(n0 - n1) <= max(2, 0.2 * n0)
