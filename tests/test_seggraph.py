# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""seggraph の門: graph cut は最大フロー = 最小カットと総当たり、α-expansion は単調性と 2c の上界(総当たり)、SRM は真の領域数、
成分木の開放は skimage と画素一致 + 冪等・反拡大・増加、準平坦領域 = 最小全域木の切断、階層分水嶺は ultrametric・入れ子・
dynamics の閉形式、超画素は 4-連結と skimage との比較、閾値は skimage / SimpleITK / Bayes の閉形式 / 総当たり。"""
from __future__ import annotations

import inspect
import math

import numpy as np
import pytest
from scipy import ndimage as ndi

import seggraph as G
import segworld as SW


# ───────────────────────── 合成の道具(構造のある入力、乱数は seed 固定) ─────────────────────────
def two_discs(noise=0.05, seed=0, h=96, w=96):
    yy, xx = np.mgrid[0:h, 0:w]
    truth = ((yy - 30) ** 2 + (xx - 30) ** 2 < 15 ** 2) * 1 + ((yy - 60) ** 2 + (xx - 65) ** 2 < 20 ** 2) * 2
    im = np.clip(0.2 + 0.3 * truth + noise * np.random.default_rng(seed).standard_normal(truth.shape), 0, 1)
    return im, truth


def basin_terrain(depths=(0.1, 0.25, 0.4, 0.55, 0.7, 0.9)):
    f = np.ones((60, 80))
    pos = [(10, 10), (10, 40), (10, 65), (40, 10), (40, 40), (40, 65)]
    assert len(depths) > 0
    for d, (y, x) in zip(depths, pos):
        f[y:y + 10, x:x + 8] = 1 - d
    return f


def smooth_noise(seed=3, n=80, s=2.0):
    return ndi.gaussian_filter(np.random.default_rng(seed).random((n, n)), s)


def same_partition(a, b):
    """2 つのラベル画像が同じ分割か(番号の付け方は問わない)。"""
    return G._is_nested(a, b) and G._is_nested(b, a)


# ───────────────────────── 1. graph cut ─────────────────────────
@pytest.mark.parametrize("conn", [4, 8])
def test_graph_cut_matches_brute_force_and_maxflow_equals_mincut(conn):
    rng = np.random.default_rng(11)
    n_case = 0
    for _ in range(40):
        im = rng.integers(0, 10, (3, 4)).astype(float)
        lam = float(rng.integers(0, 7))
        r = G.graph_cut_binary(im, lam=lam, mu_bg=2, mu_fg=7, connectivity=conn)
        b = G._brute_force_binary(im, lam=lam, mu_bg=2, mu_fg=7, connectivity=conn)
        if conn == 4:
            assert r["integer_exact"]
            assert r["energy"] == pytest.approx(b["energy"], abs=1e-12)
            assert r["cut_value"] == pytest.approx(r["energy"], abs=1e-12)       # カット + 定数 = エネルギー
        else:                                                                     # 斜めの 1/√2 は整数でない → 丸めの上界
            assert r["energy"] <= b["energy"] + r["quantization_bound"]
        assert r["cut_value_int"] == r["flow_value_int"]                           # 最大フロー = 最小カット(整数で厳密)
        n_case += 1
    assert n_case == 40


def test_graph_cut_contrast_weights_within_quantization_bound():
    rng = np.random.default_rng(5)
    for _ in range(10):
        im = rng.random((3, 4))
        r = G.graph_cut_binary(im, lam=0.7, mu_bg=0.2, mu_fg=0.8, contrast_sigma=0.3)
        b = G._brute_force_binary(im, lam=0.7, mu_bg=0.2, mu_fg=0.8, contrast_sigma=0.3)
        assert not r["integer_exact"] and r["quantization_bound"] < 1e-6
        assert b["energy"] - 1e-12 <= r["energy"] <= b["energy"] + r["quantization_bound"]
        assert abs(r["cut_value"] - r["energy"]) <= r["quantization_bound"]


def test_graph_cut_lambda_zero_is_pixelwise():
    im, _ = two_discs(noise=0.15, seed=2)
    r = G.graph_cut_binary(im, lam=0.0, mu_bg=0.25, mu_fg=0.6)
    np.testing.assert_array_equal(r["mask"], (im - 0.6) ** 2 < (im - 0.25) ** 2)
    assert r["smooth_energy"] == 0.0


def test_graph_cut_is_locally_optimal_and_smooths_noise():
    im, truth = two_discs(noise=0.25, seed=4)
    obj = truth > 0
    r0 = G.graph_cut_binary(im, lam=0.0, mu_bg=0.2, mu_fg=0.6)
    r = G.graph_cut_binary(im, lam=0.08, mu_bg=0.2, mu_fg=0.6)
    assert r["cut_value_int"] == r["flow_value_int"]
    err0 = np.count_nonzero(r0["mask"] != obj)
    err = np.count_nonzero(r["mask"] != obj)
    assert err < 0.2 * err0                     # 平滑項が雑音の点を消す
    # どの 1 画素を反転してもエネルギーは下がらない(大域最小なので当然、局所でも確かめる)
    rng = np.random.default_rng(0)
    a = im.ravel()
    ei, ej, ed = G._grid_edges(*im.shape, 4)
    y = r["mask"].ravel()
    base = G._energy_binary((a - 0.2) ** 2, (a - 0.6) ** 2, ei, ej, np.zeros(ei.size), y) + 0.08 * np.count_nonzero(y[ei] != y[ej])
    assert base == pytest.approx(r["energy"], rel=1e-12)
    idx = rng.choice(a.size, 200, replace=False)
    assert idx.size > 0
    for p in idx.tolist():
        y2 = y.copy()
        y2[p] = ~y2[p]
        e2 = np.where(y2, (a - 0.6) ** 2, (a - 0.2) ** 2).sum() + 0.08 * np.count_nonzero(y2[ei] != y2[ej])
        assert e2 >= r["energy"] - r["quantization_bound"]


def test_graph_cut_seeds_are_hard_constraints():
    im, truth = two_discs(noise=0.05)
    seeds = np.zeros(im.shape, np.int64)
    seeds[30, 30] = 1                          # 物体の中に「背景」の種
    seeds[2, 2] = 2                            # 背景の中に「物体」の種
    r = G.graph_cut_binary(im, lam=0.05, mu_bg=0.2, mu_fg=0.6, seeds=seeds)
    assert not r["mask"][30, 30] and r["mask"][2, 2]
    assert r["n_seeds"] == 2


def test_graph_cut_rejects_bad_input():
    with pytest.raises(ValueError):
        G.graph_cut_binary(np.zeros((4, 4)), lam=-1)
    with pytest.raises(ValueError):
        G.graph_cut_binary(np.full((4, 4), np.nan))
    with pytest.raises(ValueError):
        G.graph_cut_binary(np.zeros((4, 4)), connectivity=6)
    with pytest.raises(ValueError):
        G.graph_cut_binary(np.zeros((4, 4)), seeds=np.full((4, 4), 3))


# ───────────────────────── 2. α-expansion ─────────────────────────
@pytest.mark.parametrize("pairwise", ["potts", "truncated_linear"])
def test_alpha_expansion_monotone_and_within_2c_of_brute_force(pairwise):
    rng = np.random.default_rng(7)
    ratios = []
    for _ in range(25):
        im = rng.integers(0, 9, (2, 4)).astype(float)
        lam = float(rng.integers(1, 10))
        r = G.alpha_expansion(im, [1, 4, 7], lam=lam, pairwise=pairwise, truncation=2)
        b = G._brute_force_multi(im, [1, 4, 7], lam=lam, pairwise=pairwise, truncation=2)
        assert np.all(np.diff(r["energies"]) < 0)                       # 受け入れの列は厳密に減る
        mm = r["move_minima"]
        assert np.all(mm[:, 0] <= mm[:, 1] + 1e-9)                      # 移動の最小 ≤ 今の値(今のラベルも移動の 1 つ)
        assert r["energy"] >= b["energy"] - 1e-9
        assert r["energy"] <= r["bound_factor"] * b["energy"] + 1e-9   # BVZ 2001 Theorem 6.1
        ratios.append(r["energy"] / max(b["energy"], 1e-12))
    assert r["c"] == (1.0 if pairwise == "potts" else 2.0)
    assert max(ratios) <= r["bound_factor"]


def test_alpha_expansion_bound_is_not_vacuous():
    """3×3 の問題では expansion の局所解が大域解より高いことがある(比 > 1)、それでも 2c 以内。"""
    rng = np.random.default_rng(0)
    worst = 0.0
    for _ in range(120):
        im = rng.integers(0, 9, (3, 3)).astype(float)
        lam = float(rng.integers(1, 30))
        r = G.alpha_expansion(im, [1, 4, 7], lam=lam)
        b = G._brute_force_multi(im, [1, 4, 7], lam=lam)
        worst = max(worst, r["energy"] / b["energy"])
        assert r["energy"] <= 2.0 * b["energy"] + 1e-9
    assert 1.0 < worst <= 2.0


def test_alpha_expansion_lambda_zero_is_argmin_and_three_phase_world():
    rng = np.random.default_rng(1)
    yy, xx = np.mgrid[0:64, 0:64]
    truth = 1 + (xx > 21).astype(int) + (xx > 42).astype(int)
    im = (truth - 1) * 0.4 + 0.12 * rng.standard_normal(truth.shape)
    r0 = G.alpha_expansion(im, [0.0, 0.4, 0.8], lam=0.0)
    np.testing.assert_array_equal(r0["labels"], 1 + np.argmin((im[..., None] - np.array([0, 0.4, 0.8])) ** 2, axis=2))
    r = G.alpha_expansion(im, [0.0, 0.4, 0.8], lam=0.05)
    assert np.count_nonzero(r["labels"] != truth) < 0.25 * np.count_nonzero(r0["labels"] != truth)
    assert np.all(np.diff(r["energies"]) < 0)


def test_alpha_expansion_rejects_non_metric_and_bad_means():
    with pytest.raises(ValueError):
        G.alpha_expansion(np.zeros((4, 4)), [0.0])
    with pytest.raises(ValueError):
        G.alpha_expansion(np.zeros((4, 4)), [0.0, 1.0], pairwise="truncated_linear", truncation=0.5)
    with pytest.raises(ValueError):
        G.alpha_expansion(np.zeros((4, 4)), [0.0, 1.0], pairwise="quadratic")


# ───────────────────────── 3. SRM ─────────────────────────
def test_srm_recovers_true_region_count_over_a_range_of_q():
    im, truth = two_discs(noise=0.05)
    counts = []
    qs = [16, 32, 64, 128, 256]
    assert len(qs) > 0
    for q in qs:
        r = G.statistical_region_merging(im, q=q)
        counts.append(r["n_regions"])
        assert same_partition(r["labels"], truth + 1)
    assert counts == [3] * len(qs)


def test_srm_region_count_is_monotone_in_q_on_these_worlds():
    """定理ではなく実測(述語の係数は要確認): 2 値 + 雑音と結晶粒の世界で、q を増やすと領域数は減らない。"""
    im, _ = two_discs(noise=0.08, seed=1)
    g = SW.world_grains_voronoi(16, seed=1, size=(96, 96))["image"]
    assert len([im, g]) > 0
    for img in (im, g):
        n = [G.statistical_region_merging(img, q=q)["n_regions"] for q in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)]
        assert np.all(np.diff(n) >= 0), n
        assert n[0] < n[-1]


def test_srm_constant_and_range_checks():
    r = G.statistical_region_merging(np.full((10, 12), 0.5))
    assert r["n_regions"] == 1
    with pytest.raises(ValueError):
        G.statistical_region_merging(np.full((4, 4), 2.0))
    with pytest.raises(ValueError):
        G.statistical_region_merging(np.zeros((4, 4)), q=0)


# ───────────────────────── 4. 成分木と属性開放 ─────────────────────────
@pytest.mark.parametrize("conn,skc", [(4, 1), (8, 2)])
def test_area_and_diameter_opening_match_skimage(conn, skc):
    morph = pytest.importorskip("skimage.morphology")
    rng = np.random.default_rng(3)
    n = 0
    for t in range(4):
        f = rng.integers(0, 6, (30, 33)).astype(float) if t % 2 == 0 else ndi.gaussian_filter(rng.random((40, 40)), 1.0)
        for A in (1, 3, 7, 25):
            a = G.area_opening_attr(f, A, connectivity=conn)["image"]
            np.testing.assert_array_equal(a, morph.area_opening(f, area_threshold=A, connectivity=skc))
            d = G.area_opening_attr(f, A, attribute="diameter", connectivity=conn)["image"]
            np.testing.assert_array_equal(d, morph.diameter_opening(f, diameter_threshold=A, connectivity=skc))
            n += 1
        par, _ = morph.max_tree(f, connectivity=skc)
        fl = f.ravel()
        can = (fl[par.ravel()] != fl) | (par.ravel() == np.arange(fl.size))
        mt = G.max_tree(f, connectivity=conn)
        assert mt["n_nodes"] == int(can.sum())
        assert mt["area"].ravel()[mt["root"]] == f.size
    assert n == 16


@pytest.mark.parametrize("attribute,thr", [("area", 30), ("diameter", 6)])
def test_attribute_opening_is_idempotent_anti_extensive_increasing(attribute, thr):
    rng = np.random.default_rng(9)
    f = ndi.gaussian_filter(rng.random((64, 64)), 1.5)
    g = f + 0.05 * rng.random(f.shape)                           # f ≤ g
    a = G.area_opening_attr(f, thr, attribute=attribute)
    b = G.area_opening_attr(a["image"], thr, attribute=attribute)
    np.testing.assert_array_equal(a["image"], b["image"])         # 冪等
    assert np.all(a["image"] <= f)                                # 反拡大
    assert np.all(a["image"] <= G.area_opening_attr(g, thr, attribute=attribute)["image"])   # 増加
    assert a["removed"] > 0 and b["removed"] == 0


def test_max_tree_rejects_bad_attribute():
    with pytest.raises(ValueError):
        G.area_opening_attr(np.zeros((4, 4)), 2, attribute="height")


# ───────────────────────── 5. 準平坦領域と α-tree ─────────────────────────
@pytest.mark.parametrize("conn", [4, 8])
def test_quasi_flat_zones_equal_mst_cut(conn):
    rng = np.random.default_rng(4)
    g = np.round(rng.random((40, 44)) * 20) / 20                  # 同じ差が多い(同点の辺が多い)入力
    alphas = [0.0, 0.05, 0.1, 0.15, 0.3, 1.0]
    r = G.alpha_tree(g, alphas, connectivity=conn)
    assert r["nested"]
    assert len(alphas) > 0
    for k, a in enumerate(alphas):
        q = G.quasi_flat_zones(g, a, connectivity=conn)["labels"]
        np.testing.assert_array_equal(q, r["labels"][k])
    assert r["n_zones"][-1] == 1
    assert r["n_mst_edges"] == g.size - 1
    assert np.all(np.diff(r["n_zones"]) <= 0)


def test_quasi_flat_zones_alpha_zero_are_flat_zones():
    rng = np.random.default_rng(8)
    g = rng.integers(0, 3, (30, 30)).astype(float)
    q = G.quasi_flat_zones(g, 0.0)["labels"]
    n = 0
    assert len([0.0, 1.0, 2.0]) > 0
    for v in (0.0, 1.0, 2.0):
        n += ndi.label(g == v)[1]
    assert int(q.max()) == n


# ───────────────────────── 6. 階層分水嶺 ─────────────────────────
def test_hierarchical_watershed_dynamics_closed_form():
    depths = (0.1, 0.25, 0.4, 0.55, 0.7, 0.9)
    f = basin_terrain(depths)
    r = G.hierarchical_watershed(f)
    np.testing.assert_allclose(np.sort(r["dynamics"])[:-1], depths[:-1], atol=1e-12)
    assert np.isinf(np.sort(r["dynamics"])[-1])
    ths = [0.0, 0.05, 0.2, 0.3, 0.5, 0.6, 0.8, 1.0]
    assert len(ths) > 0
    prev = None
    for th in ths:
        h = G.hierarchical_watershed(f, threshold=th)
        assert h["n_regions"] == 1 + sum(1 for d in depths[:-1] if d > th)
        assert h["n_regions"] == h["n_expected"]
        if prev is not None:
            assert G._is_nested(prev, h["labels"])
        prev = h["labels"]


def test_basins_equal_regional_minima():
    morph = pytest.importorskip("skimage.morphology")
    g = smooth_noise()
    r = G.hierarchical_watershed(g)
    n_min = ndi.label(morph.local_minima(g, connectivity=1), structure=[[0, 1, 0], [1, 1, 1], [0, 1, 0]])[1]
    assert r["n_basins"] == n_min


def test_ucm_is_ultrametric_and_its_cuts_are_the_hierarchy():
    g = smooth_noise()
    u = G.ultrametric_contour_map(g, distance_matrix=True)
    D = u["distance"]
    k = D.shape[0]
    assert k > 50
    M = np.maximum(D[:, :, None], D[None, :, :])                  # max(d(x, y), d(y, z)) を [x, y, z] に
    assert np.count_nonzero(D[:, None, :] > M + 1e-12) == 0       # d(x, z) ≤ max(d(x, y), d(y, z))
    np.testing.assert_array_equal(D, D.T)
    h, w = g.shape
    idx = np.arange(h * w).reshape(h, w)
    lv = u["levels"]
    ths = [0.0, float(np.median(lv)), float(lv[-3])]
    assert len(ths) > 0
    for th in ths:
        hw = G.hierarchical_watershed(g, threshold=th)["labels"]
        ki = np.concatenate([idx[:, :-1][u["ucm_h"] <= th], idx[:-1, :][u["ucm_v"] <= th]])
        kj = np.concatenate([idx[:, 1:][u["ucm_h"] <= th], idx[1:, :][u["ucm_v"] <= th]])
        cut = G._components(h * w, ki, kj).reshape(h, w)
        assert same_partition(cut, hw)


def test_hierarchical_watershed_n_regions_and_mask():
    w = SW.world_blobs_touching(2, overlap=0.25, seed=0, size=(64, 96), radius=16.0)
    body = w["labels"] > 0
    relief = -ndi.distance_transform_edt(body)
    r = G.hierarchical_watershed(relief, n_regions=2, mask=body)
    assert r["n_regions"] == 2
    assert np.all(r["labels"][~body] == 0)
    g = smooth_noise()
    assert G.hierarchical_watershed(g, n_regions=5)["n_regions"] == 5


def test_watershed_cut_follows_the_neck_steepest_descent_tie_break():
    """同じ高さの辺を「低い端点が低い順」に処理すると、切れ目が粒のくびれに沿う。辺の番号だけで決めると格子に沿った
    直線と L 字の段になり、境界 F(τ = 2)が 0.93〜0.96 だった(実測、3 seed)。"""
    import segeval as SE
    assert len([0, 1, 2]) > 0
    for s in (0, 1, 2):
        w = SW.world_blobs_touching(10, overlap=0.2, seed=s)
        m = G.threshold_isodata(w["image"])["mask"]
        r = G.hierarchical_watershed(-ndi.distance_transform_edt(m), threshold=2.0, mask=m)
        assert r["n_regions"] == 10
        assert SE.seg_boundary_f(r["labels"], w["labels"], tau=2)["f"] >= 0.975


# ───────────────────────── 7. 超画素 ─────────────────────────
def test_snic_labels_are_connected_and_cover_the_image():
    w = SW.world_grains_voronoi(36, seed=0)
    assert len([50, 200, 400]) > 0
    for K in (50, 200, 400):
        s = G.snic_superpixels(w["image"], n_segments=K, compactness=0.1)
        assert s["all_connected"] and s["n_disconnected"] == 0
        assert np.all(s["labels"] > 0)
        assert abs(s["n_segments"] - K) <= 0.15 * K


def test_snic_and_skimage_slic_boundary_quality_are_close():
    seg = pytest.importorskip("skimage.segmentation")
    w = SW.world_grains_voronoi(36, seed=0)
    s = G.snic_superpixels(w["image"], n_segments=200, compactness=0.1)
    sl = seg.slic(w["image"], n_segments=200, compactness=0.1, channel_axis=None, start_label=1)
    qs = G.superpixel_quality(s["labels"], w["labels"])
    qk = G.superpixel_quality(sl, w["labels"])
    assert qs["boundary_recall"] >= 0.95 and abs(qs["boundary_recall"] - qk["boundary_recall"]) <= 0.05
    assert qs["cuse"] <= qk["cuse"] + 0.03


def test_quickshift_nested_in_tau_and_close_to_skimage():
    seg = pytest.importorskip("skimage.segmentation")
    w = SW.world_grains_voronoi(36, seed=0)
    im = w["image"]
    taus = [2.0, 4.0, 6.0, 9.0]
    labs = [G.quickshift(im, max_dist=t)["labels"] for t in taus]
    assert len(labs) > 1
    for a, b in zip(labs[:-1], labs[1:]):
        assert G._is_nested(a, b)                                  # 同じ木から枝を切るだけ
    assert labs[0].max() >= labs[-1].max()
    mine = G.quickshift(im, kernel_size=3, max_dist=6)
    sk = seg.quickshift(np.dstack([im] * 3), ratio=1.0 / math.sqrt(3.0), kernel_size=3, max_dist=6, convert2lab=False) + 1
    qm = G.superpixel_quality(mine["labels"], w["labels"])
    qk = G.superpixel_quality(sk, w["labels"])
    assert abs(qm["boundary_recall"] - qk["boundary_recall"]) <= 0.02
    assert abs(mine["n_segments"] - int(sk.max())) <= 0.1 * sk.max()


def test_superpixel_quality_identities():
    _, truth = two_discs()
    q = G.superpixel_quality(truth, truth)
    assert q["boundary_recall"] == 1.0 and q["cuse"] == 0.0 and q["ue_np"] == 0.0 and q["asa"] == 1.0
    one = np.ones_like(truth)
    q1 = G.superpixel_quality(one, truth)
    assert q1["cuse"] == pytest.approx(1.0 - np.bincount(truth.ravel()).max() / truth.size)


# ───────────────────────── 8. 閾値 ─────────────────────────
def mixture(P1=0.75, m1=0.3, s1=0.05, m2=0.7, s2=0.08, n=40000, seed=0):
    rng = np.random.default_rng(seed)
    n1 = int(round(P1 * n))
    x = np.concatenate([rng.normal(m1, s1, n1), rng.normal(m2, s2, n - n1)])
    return rng.permutation(x).reshape(200, n // 200)


def bayes_threshold(P1, m1, s1, m2, s2):
    """2 ガウスの Bayes の最小誤差の閾値: P1 N(t; m1, s1) = P2 N(t; m2, s2) の 2 次方程式の、2 つの平均の間の根。"""
    P2 = 1.0 - P1
    a = 1 / (2 * s1 ** 2) - 1 / (2 * s2 ** 2)
    b = -m1 / s1 ** 2 + m2 / s2 ** 2
    c = m1 ** 2 / (2 * s1 ** 2) - m2 ** 2 / (2 * s2 ** 2) - math.log(P1 * s2 / (P2 * s1))
    roots = np.roots([a, b, c]) if abs(a) > 1e-15 else np.array([-c / b])
    r = [float(np.real(x)) for x in roots if abs(np.imag(x)) < 1e-12 and m1 < np.real(x) < m2]
    assert len(r) == 1
    return r[0]


@pytest.mark.parametrize("seed,args", [(0, (0.75, 0.3, 0.05, 0.7, 0.08)), (1, (0.4, 0.2, 0.06, 0.6, 0.06)),
                                       (2, (0.9, 0.35, 0.04, 0.65, 0.05))])
def test_triangle_and_isodata_match_skimage(seed, args):
    filt = pytest.importorskip("skimage.filters")
    x = mixture(*args, seed=seed)
    tri = G.threshold_triangle(x)
    assert tri["threshold"] == filt.threshold_triangle(x)
    iso = G.threshold_isodata(x)
    assert iso["residual"] == 0.0                                  # 画素の上の不動点 t = (μ_low + μ_high)/2
    assert iso["threshold"] == 0.5 * (iso["mu_low"] + iso["mu_high"])
    sk = filt.threshold_isodata(x)
    assert abs(iso["threshold"] - sk) <= iso["bin_width"]
    np.testing.assert_allclose(iso["fixed_points"], filt.threshold_isodata(x, return_all=True))


def test_triangle_left_tail():
    filt = pytest.importorskip("skimage.filters")
    x = 1.0 - mixture(seed=5)
    assert G.threshold_triangle(x)["threshold"] == filt.threshold_triangle(x)


@pytest.mark.parametrize("seed,args", [(0, (0.75, 0.3, 0.05, 0.7, 0.08)), (1, (0.4, 0.2, 0.06, 0.6, 0.06)),
                                       (2, (0.9, 0.35, 0.04, 0.65, 0.05))])
def test_kittler_near_bayes_and_kapur_is_entropy_argmax(seed, args):
    x = mixture(*args, seed=seed, n=80000)
    k = G.threshold_kittler(x)
    bw = (x.max() - x.min()) / 256
    tb = bayes_threshold(*args)
    assert abs(k["threshold"] - tb) <= 2.5 * bw, (k["threshold"], tb, bw)
    kp = G.threshold_kapur(x)
    cnt, _ = np.histogram(x, bins=256, range=(x.min(), x.max()))
    p = cnt / cnt.sum()
    best, arg = -np.inf, -1
    assert p.size > 0
    for t in range(p.size - 1):
        a, b = p[:t + 1], p[t + 1:]
        if a.sum() <= 0 or b.sum() <= 0:
            continue
        qa, qb = a[a > 0] / a.sum(), b[b > 0] / b.sum()
        H = -(qa * np.log(qa)).sum() - (qb * np.log(qb)).sum()
        if H > best:
            best, arg = H, t
    assert kp["bin"] == arg
    assert kp["entropy"][arg] == pytest.approx(best, rel=1e-12)


def test_kittler_kapur_against_simpleitk():
    sitk = pytest.importorskip("SimpleITK")
    x = mixture(seed=0, n=80000)
    img = sitk.GetImageFromArray(x.astype("float32"))
    bw = (x.max() - x.min()) / 256
    got = {}
    assert len(["KittlerIllingworth", "MaximumEntropy"]) > 0
    for nm in ("KittlerIllingworth", "MaximumEntropy"):
        f = getattr(sitk, nm + "ThresholdImageFilter")()
        f.SetNumberOfHistogramBins(256)
        f.SetInsideValue(0)
        f.SetOutsideValue(1)
        f.Execute(img)
        got[nm] = f.GetThreshold()
    assert abs(G.threshold_kapur(x)["threshold"] - got["MaximumEntropy"]) <= 2 * bw
    assert abs(G.threshold_kittler(x)["threshold"] - got["KittlerIllingworth"]) <= 4 * bw


def test_thresholds_reject_flat_image():
    assert len([G.threshold_triangle, G.threshold_isodata, G.threshold_kittler, G.threshold_kapur]) > 0
    for fn in (G.threshold_triangle, G.threshold_isodata, G.threshold_kittler, G.threshold_kapur):
        with pytest.raises(ValueError):
            fn(np.full((8, 8), 0.3))


# ───────────────────────── 規律 ─────────────────────────
def test_module_discipline():
    src = inspect.getsource(G)
    assert "any(" not in src
    names = [n for n in G.__all__ if callable(getattr(G, n))]
    assert len(names) == 16
    for n in names:
        doc = getattr(G, n).__doc__ or ""
        assert doc.strip(), n
        assert "](" not in doc and "{{" not in doc and "{%" not in doc, n
    mod_doc = G.__doc__
    assert "](" not in mod_doc and "{{" not in mod_doc and "{%" not in mod_doc


def test_every_op_returns_dict_on_a_small_image():
    im, truth = two_discs(h=24, w=24)
    outs = [G.graph_cut_binary(im), G.alpha_expansion(im, [0.2, 0.5, 0.8]), G.statistical_region_merging(im),
            G.max_tree(im), G.area_opening_attr(im, 4), G.quasi_flat_zones(im, 0.05), G.alpha_tree(im, [0.05]),
            G.hierarchical_watershed(im), G.ultrametric_contour_map(im), G.snic_superpixels(im, n_segments=9),
            G.quickshift(im), G.superpixel_quality(truth + 1, truth), G.threshold_triangle(im), G.threshold_isodata(im),
            G.threshold_kittler(im), G.threshold_kapur(im)]
    assert len(outs) == 16
    for o in outs:
        assert isinstance(o, dict)
