# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""3D グレースケール morphology の経路パリティ(torch↔scipy)と GT。"""
from __future__ import annotations

import numpy as np
import pytest

import match3d as m


def _rand_vol():
    return np.random.default_rng(0).random((14, 16, 18)).astype(np.float32)


@pytest.mark.skipif(not m._HAS_TORCH, reason="torch 無し環境では scipy 経路のみ")
def test_cube_parity_torch_vs_scipy():
    """cube SE の torch 経路と scipy 経路がビット単位で一致(境界規約含む)。"""
    v = _rand_vol()
    d_t = m.morph_dilate3d(v, 2)
    e_t = m.morph_erode3d(v, 2)
    m._HAS_TORCH = False
    try:
        d_s = m.morph_dilate3d(v, 2)
        e_s = m.morph_erode3d(v, 2)
    finally:
        m._HAS_TORCH = True
    assert np.array_equal(d_t, d_s), "dilation: torch と scipy が不一致"
    assert np.array_equal(e_t, e_s), "erosion: torch と scipy が不一致"


def test_open_removes_spike_close_fills_cavity():
    sol = np.zeros((24, 24, 24), np.float32)
    sol[6:18, 6:18, 6:18] = 1.0
    spike = sol.copy()
    spike[12, 12, 18:22] = 1.0                     # SE より細い棘
    cav = sol.copy()
    cav[11:13, 11:13, 11:13] = 0.0                 # SE より小さい空洞
    op = m.morph_open3d(spike, 2) > 0.5
    cl = m.morph_close3d(cav, 2) > 0.5
    assert not op[12, 12, 19], "opening が棘を残した"
    assert op[12, 12, 12], "opening が本体を消した"
    assert cl[12, 12, 12], "closing が空洞を埋めていない"


def test_ball_se_isotropic_vs_cube():
    """ball SE は cube SE の部分集合(対角方向に控えめ)= 等方性の検証。"""
    v = np.zeros((15, 15, 15), np.float32)
    v[7, 7, 7] = 1.0
    ball = m.morph_dilate3d(v, 3, se="ball") > 0.5
    cube = m.morph_dilate3d(v, 3, se="cube") > 0.5
    assert ball[7, 7, 4] and ball[4, 7, 7], "ball が軸方向 r まで届いていない"
    assert not ball[4, 4, 4], "ball が対角の角まで届いている(cube 化している)"
    assert cube[4, 4, 4], "cube は対角の角まで届くはず"
    assert (ball <= cube).all(), "ball は cube の部分集合のはず"


def test_gradient_tophat_blackhat_composition():
    v = _rand_vol()
    g = m.morph_gradient3d(v, 1)
    assert np.allclose(g, m.morph_dilate3d(v, 1) - m.morph_erode3d(v, 1))
    th = m.morph_tophat3d(v, 1)
    assert np.allclose(th, v - m.morph_open3d(v, 1), atol=1e-6)
    bh = m.morph_blackhat3d(v, 1)
    assert np.allclose(bh, m.morph_close3d(v, 1) - v, atol=1e-6)
    assert (th >= -1e-6).all() and (bh >= -1e-6).all(), "top/black-hat は非負のはず"
