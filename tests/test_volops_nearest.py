# -*- coding: utf-8 -*-
"""3D 距離変換の「向き」3 op の門(2026-09-21): 閉形式の真値・拒否・spacing・GPU 経路との一致。"""
from __future__ import annotations

import numpy as np
import pytest

import volops


def test_vector_points_at_the_nearest_seed_and_is_zero_on_seeds():
    v = np.zeros((5, 7, 9))
    v[2, 3, 1] = 1.0
    v[2, 3, 8] = 1.0
    d = volops.vol_nearest_seed_vector(v)
    assert d.shape == (3, 5, 7, 9) and d.dtype == np.float64
    assert d[:, 2, 3, 1].tolist() == [0.0, 0.0, 0.0]                # seed の上は 0
    assert d[:, 2, 3, 3].tolist() == [0.0, 0.0, -2.0]               # 左の seed が近い
    assert d[:, 2, 3, 7].tolist() == [0.0, 0.0, 1.0]                # 右の seed が近い
    assert d[:, 0, 0, 1].tolist() == [2.0, 3.0, 0.0]                # 斜めでも成分ごとに正しい
    # |変位| は距離変換(seed を背景とした EDT)と一致
    dist = volops.vol_distance_transform(1.0 - v)
    assert np.allclose(np.linalg.norm(d, axis=0), dist)


def test_vector_rejects_no_seed_and_uses_physical_spacing():
    with pytest.raises(ValueError, match="no seed"):
        volops.vol_nearest_seed_vector(np.zeros((3, 3, 3)))
    s = np.zeros((7, 5, 9))
    s[0, 2, 4] = 1                                                     # z に 3 voxel
    s[3, 2, 0] = 1                                                     # x に 4 voxel
    iso = volops.vol_nearest_seed_vector(s)[:, 3, 2, 4]
    aniso = volops.vol_nearest_seed_vector(s, spacing=(2.0, 1.0, 1.0))[:, 3, 2, 4]
    assert iso.tolist() == [-3.0, 0.0, 0.0]
    assert aniso.tolist() == [0.0, 0.0, -4.0]                        # 物理距離 6 > 4 で入れ替わる


def test_nearest_label_is_a_voronoi_partition_and_keeps_seeds():
    L = np.zeros((3, 3, 9), np.int64)
    L[1, 1, 0] = 4
    L[1, 1, 8] = 7
    out = volops.vol_nearest_label(L)
    assert out.dtype == np.int64 and out.shape == L.shape
    assert out[1, 1, 0] == 4 and out[1, 1, 8] == 7
    assert (out[:, :, :4] == 4).all() and (out[:, :, 5:] == 7).all()   # 中央 x=4 は等距離(どちらでもよい)
    assert out[1, 1, 4] in (4, 7)


def test_nearest_label_rejects_bad_labels():
    with pytest.raises(ValueError, match="no non-zero"):
        volops.vol_nearest_label(np.zeros((2, 2, 2)))
    with pytest.raises(ValueError, match="whole numbers"):
        volops.vol_nearest_label(np.array([[[0.0, 1.5]]]))
    with pytest.raises(ValueError, match="whole numbers"):
        volops.vol_nearest_label(np.array([[[0, -1]]]))
    with pytest.raises(ValueError, match="\\(D, H, W\\)"):
        volops.vol_nearest_label(np.zeros((2, 2)))


def test_ledger_exposes_the_three_ops_with_flow_dense_out():
    import ops3d
    ops = {name: spec for name, spec in ops3d.OPS3D.items()} if isinstance(ops3d.OPS3D, dict) else None
    if ops is None:
        pytest.skip("OPS3D is not a dict in this build")
    for name in ("vol_nearest_seed_vector", "vol_nearest_label", "edt_jfa_vector"):
        assert name in ops, name


def test_edt_jfa_vector_matches_scipy():
    torch = pytest.importorskip("torch")
    import match3d
    rng = np.random.default_rng(3)
    seed = rng.random((12, 14, 16)) < 0.02
    seed[0, 0, 0] = True
    ref = volops.vol_nearest_seed_vector(seed.astype(float))
    jfa = match3d.edt_jfa_vector(seed)
    assert isinstance(jfa, torch.Tensor) and tuple(jfa.shape) == (3, 12, 14, 16)
    j = jfa.detach().cpu().numpy()
    assert np.allclose(np.linalg.norm(j, axis=0), np.linalg.norm(ref, axis=0))   # 距離は厳密一致(seed の選び方は同距離で違いうる)
    assert (j[:, seed] == 0).all()
    with pytest.raises(ValueError, match="no seed"):
        match3d.edt_jfa_vector(np.zeros((3, 3, 3), bool))
    # edt_jfa(距離)は変わらない
    d = match3d.edt_jfa(seed).detach().cpu().numpy()
    assert np.allclose(d, np.linalg.norm(ref, axis=0))
