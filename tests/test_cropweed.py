# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cropweed(作物と雑草の 5 op)の門: 閉形式・第 2 の計算・不変性・壊す探針・fail-closed。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import cropweed as cw


# --------------------------------------------------------------------------- #
# plant_color_index                                                            #
# --------------------------------------------------------------------------- #
def test_closed_form_values():
    px = np.array([[[0.0, 1.0, 0.0], [0.5, 0.5, 0.5], [0.2, 0.3, 0.5]]])
    exg = cw.plant_color_index(px, index="exg")["index"][0]
    assert exg[0] == 2.0 and exg[1] == 0.0
    # 第 2 の計算: 色度座標を手で作る
    r, g, b = 0.2, 0.3, 0.5
    assert math.isclose(exg[2], 2 * g - r - b, abs_tol=1e-15)
    cive = cw.plant_color_index(px, index="cive")["index"][0]
    assert math.isclose(cive[1], 0.441 / 3 - 0.811 / 3 + 0.385 / 3 + 18.78745, abs_tol=1e-12)
    ng = cw.plant_color_index(px, index="ngrdi")["index"][0]
    assert math.isclose(ng[2], (0.3 - 0.2) / (0.3 + 0.2), abs_tol=1e-15)
    veg = cw.plant_color_index(px, index="veg")["index"][0]
    assert math.isclose(veg[2], g / (r ** 0.667 * b ** 0.333), rel_tol=1e-12)
    assert np.isnan(veg[0])           # r = 0 で VEG は定義されない(NaN と valid=False)


def test_exgr_identity_and_scale_invariance():
    g = np.random.default_rng(5)
    img = g.uniform(0.05, 1.0, (8, 9, 3))
    exg = cw.plant_color_index(img, index="exg")["index"]
    exr = cw.plant_color_index(img, index="exr")["index"]
    exgr = cw.plant_color_index(img, index="exgr")["index"]
    assert np.allclose(exgr, exg - exr, atol=1e-14, rtol=0)
    # 色度座標の指標は明るさの一様な倍率に不変
    half = cw.plant_color_index(img * 0.5, index="exgr")["index"]
    assert np.allclose(half, exgr, atol=1e-13, rtol=0)


def test_uint8_matches_float():
    g = np.random.default_rng(6)
    u8 = g.integers(10, 255, (5, 5, 3)).astype(np.uint8)
    a = cw.plant_color_index(u8, index="exg")["index"]
    b = cw.plant_color_index(u8.astype(np.float64) / 255.0, index="exg")["index"]
    assert np.allclose(a, b, atol=1e-15, rtol=0)


def test_channel_swap_probe_flips_sign():
    """壊す探針: R と G を入れ替えると、植物の色(G 優位)の ExGR は正から負へ。"""
    leaf = np.full((4, 4, 3), (0.2, 0.5, 0.15))
    assert (cw.plant_color_index(leaf, index="exgr")["index"] > 0).all()
    assert (cw.plant_color_index(leaf[..., [1, 0, 2]], index="exgr")["index"] < 0).all()


def test_dark_pixels_are_undefined_not_zero():
    img = np.full((3, 3, 3), 0.4)
    img[0, 0] = 0.005
    out = cw.plant_color_index(img, index="exg", dark_floor=0.02)
    assert np.isnan(out["index"][0, 0]) and not out["valid"][0, 0] and out["n_invalid"] == 1


@pytest.mark.parametrize("bad", [np.zeros((0, 0, 3)), np.zeros((4, 4)), np.full((2, 2, 3), 1.5),
                                 np.full((2, 2, 3), np.nan), np.zeros((3, 3, 3))])
def test_plant_color_index_refuses(bad):
    with pytest.raises(ValueError):
        cw.plant_color_index(bad)


def test_unknown_index_refused():
    with pytest.raises(ValueError):
        cw.plant_color_index(np.full((2, 2, 3), 0.5), index="ndvi")


# --------------------------------------------------------------------------- #
# superpixel_color_texture_features                                            #
# --------------------------------------------------------------------------- #
def test_region_means_match_direct_computation():
    g = np.random.default_rng(7)
    img = g.uniform(0.1, 0.9, (12, 12, 3))
    lab = np.ones((12, 12), np.int64)
    lab[:, 6:] = 2
    f = cw.superpixel_color_texture_features(img, lab)
    exg = cw.plant_color_index(img, index="exg")["index"]
    assert np.allclose(f["X"][:, 0], [exg[:, :6].mean(), exg[:, 6:].mean()], atol=1e-14, rtol=0)
    br = img.mean(2)
    assert np.allclose(f["X"][:, 5], [br[:, :6].mean(), br[:, 6:].mean()], atol=1e-14, rtol=0)
    assert np.allclose(f["X"][:, 6], [br[:, :6].std(), br[:, 6:].std()], atol=1e-12, rtol=0)
    assert f["names"][8] == "orientation_coherence"


def test_coherence_stripes_vs_isotropic():
    """向きの揃い: 一方向の縞は 1 に近く、同心円(全方向)は 0 に近い。"""
    yy, xx = np.mgrid[0:64, 0:64].astype(float)
    stripes = 0.5 + 0.3 * np.sin(0.6 * xx)
    rings = 0.5 + 0.3 * np.sin(0.6 * np.hypot(yy - 31.5, xx - 31.5))
    lab = np.ones((64, 64), np.int64)
    c_s = cw.superpixel_color_texture_features(np.repeat(stripes[..., None], 3, 2), lab)["X"][0, 8]
    c_r = cw.superpixel_color_texture_features(np.repeat(rings[..., None], 3, 2), lab)["X"][0, 8]
    assert c_s > 0.99 and c_r < 0.05


def test_small_and_dark_regions_are_dropped_with_reason():
    img = np.full((10, 10, 3), 0.5)
    lab = np.ones((10, 10), np.int64)
    lab[0, :2] = 2                    # 2 画素
    lab[5:, 5:] = 3
    img[5:, 5:] = 0.001               # 暗い
    f = cw.superpixel_color_texture_features(img, lab, min_size=4)
    assert f["ids"].tolist() == [1]
    reasons = dict(f["dropped_ids"])
    assert "min_size" in reasons[2] and "bright" in reasons[3]


def test_features_refuse():
    img = np.full((4, 4, 3), 0.5)
    with pytest.raises(ValueError):
        cw.superpixel_color_texture_features(img, np.ones((3, 4), np.int64))
    with pytest.raises(ValueError):
        cw.superpixel_color_texture_features(img, -np.ones((4, 4), np.int64))
    with pytest.raises(ValueError):
        cw.superpixel_color_texture_features(img, np.zeros((4, 4), np.int64))   # 領域が 0


# --------------------------------------------------------------------------- #
# fisher_lda_fit / fisher_lda_score                                             #
# --------------------------------------------------------------------------- #
def test_lda_1d_equal_variance_boundary_is_midpoint():
    """閉形式: 1 次元・等分散・等しい事前確率なら境界は 2 つの平均の中点。"""
    x0 = np.array([-1.0, 0.0, 1.0, 2.0])
    x1 = x0 + 6.0
    X = np.r_[x0, x1][:, None]
    y = np.r_[np.zeros(4), np.ones(4)]
    m = cw.fisher_lda_fit(X, y, ridge=0.0)
    mid = (x0.mean() + x1.mean()) / 2
    s = cw.fisher_lda_score(m, np.array([[mid - 1e-9], [mid + 1e-9]]))
    assert s["label"].tolist() == [0, 1]
    assert abs(cw.fisher_lda_score(m, np.array([[mid]]))["score"][0]) < 1e-12


def test_lda_exact_zero_score_is_class_0():
    """宣言した規則: score がちょうど 0 はクラス 0(対称な 2 クラスの中点で score は厳密に 0)。"""
    X = np.array([[-1.0], [1.0], [3.0], [5.0]])
    m = cw.fisher_lda_fit(X, np.array([0, 0, 1, 1]), ridge=0.0)
    s = cw.fisher_lda_score(m, np.array([[2.0]]))
    assert s["score"][0] == 0.0 and s["label"][0] == 0


def test_lda_class_swap_flips_sign_and_affine_invariance():
    g = np.random.default_rng(8)
    X = np.r_[g.normal(0, 1, (30, 3)), g.normal(0, 1, (30, 3)) + [2.0, -1.0, 0.5]]
    y = np.r_[np.zeros(30), np.ones(30)]
    m = cw.fisher_lda_fit(X, y, ridge=0.0)
    ms = cw.fisher_lda_fit(X, 1 - y, ridge=0.0)
    s, ss = cw.fisher_lda_score(m, X)["score"], cw.fisher_lda_score(ms, X)["score"]
    assert np.allclose(s, -ss, atol=1e-10, rtol=0)
    A = np.array([[2.0, 0.3, 0.0], [0.0, 0.5, 0.1], [0.4, 0.0, 3.0]])
    Xa = X @ A.T + [5.0, -2.0, 7.0]
    ma = cw.fisher_lda_fit(Xa, y, ridge=0.0)
    assert np.allclose(cw.fisher_lda_score(ma, Xa)["score"], s, atol=1e-8, rtol=0)


def test_lda_refuses_degenerate():
    X = np.r_[np.zeros((5, 2)), np.zeros((5, 2))]
    y = np.r_[np.zeros(5), np.ones(5)]
    with pytest.raises(ValueError):
        cw.fisher_lda_fit(X + np.random.default_rng(0).normal(0, 1, X.shape) * [1, 0], y, ridge=0.0)
    g = np.random.default_rng(1)
    Z = g.normal(0, 1, (10, 2))
    with pytest.raises(ValueError):                       # 平均が同じ(鏡像の 2 クラス)
        cw.fisher_lda_fit(np.r_[Z, Z], np.r_[np.zeros(10), np.ones(10)])
    with pytest.raises(ValueError):
        cw.fisher_lda_fit(np.ones((4, 2)), np.array([0, 0, 0, 1]))
    with pytest.raises(ValueError):
        cw.fisher_lda_fit(np.ones((4, 2)), np.array([0, 2, 0, 1]))
    m = cw.fisher_lda_fit(np.r_[Z, Z + 3], np.r_[np.zeros(10), np.ones(10)])
    with pytest.raises(ValueError):
        cw.fisher_lda_score(m, np.ones((3, 5)))
    with pytest.raises(ValueError):
        cw.fisher_lda_score({"w": 1}, Z)


# --------------------------------------------------------------------------- #
# cover_ratio_grade                                                            #
# --------------------------------------------------------------------------- #
def test_grade_edges_inclusive_upper_and_margin():
    out = cw.cover_ratio_grade([0.0, 0.0499, 0.05, 0.2499, 0.25, 0.5, 1.0])
    assert out["grade"].tolist() == [0, 0, 1, 1, 2, 3, 3]
    assert out["n_grades"] == 4 and out["counts"].tolist() == [2, 2, 1, 2]
    assert math.isclose(out["margin"][1], 0.0001, abs_tol=1e-12)


@pytest.mark.parametrize("frac,edges", [([], (0.1,)), ([1.2], (0.1,)), ([np.nan], (0.1,)),
                                        ([0.3], (0.5, 0.2)), ([0.3], (0.0, 0.5)), ([0.3], ())])
def test_grade_refuses(frac, edges):
    with pytest.raises(ValueError):
        cw.cover_ratio_grade(frac, edges=edges)


def test_registered_in_ledger():
    import opssegmentation as reg
    for n in ("plant_color_index", "superpixel_color_texture_features", "cover_ratio_grade"):
        assert reg.info(n)["category"] == "plant"
    for n in ("fisher_lda_fit", "fisher_lda_score"):
        assert reg.info(n)["category"] == "classify"
    assert not reg.missing()
