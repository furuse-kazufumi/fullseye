# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""segcompare — 分割の比較量の定理(距離の公理・付け替え不変)・閉形式・第 2 実装。

真値は 3 種類: (1) 定理 —— VOI は距離(対称・三角不等式・自分とは 0)、ラベル番号の付け替えで
何も変わらない、(2) 閉形式 —— 正解の 1 領域 m 画素を半分に割ると split がちょうど m/N ビット
増え merge は 0、(3) 第 2 実装 —— 画素対の総当たり、scikit-image / scikit-learn(在れば)。
乱数のラベルだけでは対称性の破れが隠れるので、構造を作ったラベルでも確かめる。
"""
from __future__ import annotations

import itertools

import numpy as np
import pytest

import segcompare as S


def _blocks(h=40, w=60):
    """縦 2 × 横 3 の 6 ブロック(大きさが違う)。"""
    a = np.zeros((h, w), int)
    a[:, :15] = 1
    a[:, 15:35] = 2
    a[:, 35:] = 3
    a[h // 2:] += 3
    return a


def _random_labels(shape=(30, 30), k=5, seed=0):
    return np.random.default_rng(seed).integers(0, k, shape)


def test_identity_gives_zero_voi_and_unit_ari():
    a = _blocks()
    v = S.seg_variation_of_information(a, a)
    r = S.seg_rand(a, a)
    assert v["voi"] == 0.0 and v["split"] == 0.0 and v["merge"] == 0.0
    assert r["adjusted_rand_index"] == 1.0 and r["rand_index"] == 1.0 and r["adapted_rand_error"] == 0.0


def test_relabelling_by_any_permutation_changes_nothing():
    a, b = _blocks(), _random_labels((40, 60), 7, 1)
    base_v, base_r = S.seg_variation_of_information(a, b), S.seg_rand(a, b)
    perm = np.random.default_rng(2).permutation(100) + 1000
    v = S.seg_variation_of_information(perm[a], perm[b])
    r = S.seg_rand(perm[a], perm[b])
    for k in ("voi", "split", "merge"):
        assert v[k] == pytest.approx(base_v[k], abs=1e-12)
    for k in ("rand_index", "adjusted_rand_index", "adapted_rand_error"):
        assert r[k] == pytest.approx(base_r[k], abs=1e-12)


def test_halving_one_true_region_adds_exactly_m_over_n_bits_of_split():
    a = _blocks()
    b = a.copy()
    region = a == 2                      # 20 列 x 20 行 = 400 画素
    rows = np.nonzero(region)[0]
    b[region & (np.arange(a.shape[0])[:, None] < rows.min() + (rows.max() - rows.min() + 1) // 2)] = 99
    m, n = int(region.sum()), a.size
    v = S.seg_variation_of_information(a, b)
    assert v["merge"] == pytest.approx(0.0, abs=1e-12)
    assert v["split"] == pytest.approx(m / n, abs=1e-12)


def test_gluing_two_true_regions_is_merge_not_split():
    a = _blocks()
    b = a.copy()
    b[b == 2] = 1
    v = S.seg_variation_of_information(a, b)
    assert v["split"] == pytest.approx(0.0, abs=1e-12) and v["merge"] > 0


def test_voi_is_a_metric():
    labs = [_random_labels((20, 20), k, s) for k, s in ((3, 0), (4, 1), (6, 2), (2, 3), (5, 4))]
    for x, y in itertools.permutations(labs, 2):
        assert S.seg_variation_of_information(x, y)["voi"] == pytest.approx(
            S.seg_variation_of_information(y, x)["voi"], abs=1e-12)
    for x, y, z in itertools.permutations(labs, 3):
        d = lambda p, q: S.seg_variation_of_information(p, q)["voi"]  # noqa: E731
        assert d(x, z) <= d(x, y) + d(y, z) + 1e-12


def test_rand_index_matches_brute_force_pair_counting():
    a, b = _random_labels((6, 7), 3, 5), _random_labels((6, 7), 4, 6)
    fa, fb = a.ravel(), b.ravel()
    agree = sum((fa[i] == fa[j]) == (fb[i] == fb[j]) for i, j in itertools.combinations(range(fa.size), 2))
    total = fa.size * (fa.size - 1) // 2
    assert S.seg_rand(a, b)["rand_index"] == pytest.approx(agree / total, abs=1e-15)


def test_contingency_sums_are_exact():
    a, b = _blocks(), _random_labels((40, 60), 5, 7)
    t = S.seg_contingency(a, b)
    assert t["counts"].sum() == t["n"] == a.size
    assert t["row_sums"].sum() == t["col_sums"].sum() == a.size
    assert t["row_sums"].tolist() == [int((a == l).sum()) for l in t["labels_a"]]


def test_ignore_label_drops_truth_pixels_only():
    a = _blocks()
    a[:5] = 0
    b = a.copy()
    b[:5] = 7                            # 無視した画素で候補が何をしていても関係ない
    b[:5, :10] = 8                       # (1 ラベルだけだと正解の 0 と 1 対 1 で、無視しなくても VOI 0 になる)
    assert S.seg_variation_of_information(a, b, ignore_label=0)["voi"] == 0.0
    assert S.seg_variation_of_information(a, b)["voi"] > 0.0


def test_three_dimensional_volumes_are_accepted():
    a = np.stack([_blocks()] * 4)
    assert S.seg_rand(a, a)["adjusted_rand_index"] == 1.0


def test_second_implementation_scikit_image_voi_and_adapted_rand():
    skm = pytest.importorskip("skimage.metrics")
    for seed in range(4):
        a, b = _random_labels((25, 30), 4 + seed, seed), _random_labels((25, 30), 3 + seed, 10 + seed)
        v = S.seg_variation_of_information(a, b)
        # scikit-image の返りは (H(image1|image0), H(image0|image1)) = (split, merge) の順。
        # ★最初は逆に読んで赤になった —— 名前は閉形式の門(半分に割ると split が m/N)で固定してある
        h10, h01 = skm.variation_of_information(a, b)
        assert v["split"] == pytest.approx(h10, abs=1e-9) and v["merge"] == pytest.approx(h01, abs=1e-9)
        are, sk_prec, sk_rec = skm.adapted_rand_error(a, b, ignore_labels=())
        r = S.seg_rand(a, b)
        assert r["adapted_rand_error"] == pytest.approx(are, abs=1e-12)
        # ★scikit-image の precision は正解側の対で割っている(コードは truth x test の表の行和)=
        #   こちらの recall。docstring は「test の対で割る」と書くので、名前が入れ替わっている。
        #   F 値は対称なので誤差そのものは一致する。
        assert r["recall"] == pytest.approx(sk_prec, abs=1e-12) and r["precision"] == pytest.approx(sk_rec, abs=1e-12)


def test_second_implementation_scikit_learn_adjusted_rand():
    metrics = pytest.importorskip("sklearn.metrics")
    for seed in range(4):
        a, b = _random_labels((25, 30), 5, seed), _random_labels((25, 30), 6, 20 + seed)
        assert S.seg_rand(a, b)["adjusted_rand_index"] == pytest.approx(
            metrics.adjusted_rand_score(a.ravel(), b.ravel()), abs=1e-12)


@pytest.mark.parametrize("a, b", [
    (np.zeros((4, 4)), np.zeros((4, 5), int)),            # 形違い
    (np.full((4, 4), 0.5), np.zeros((4, 4), int)),        # 非整数
    (np.array([[np.nan, 1], [1, 1]]), np.ones((2, 2), int)),
    (np.zeros(5, int), np.zeros(5, int)),                 # 1-D
    ("abc", np.zeros((2, 2), int)),
    (np.zeros((0, 3), int), np.zeros((0, 3), int)),       # 空
])
def test_refuses(a, b):
    with pytest.raises(ValueError):
        S.seg_variation_of_information(a, b)


def test_everything_ignored_is_refused():
    with pytest.raises(ValueError):
        S.seg_rand(np.zeros((3, 3), int), np.ones((3, 3), int), ignore_label=0)


# ---------------------------------------------------------------- 配線(シナプスの所属)
def _wiring_case():
    """3 本の神経(左・中・右の帯)と、その間のシナプス。1→2 に 4 個、2→3 に 2 個、3→1 に 2 個。"""
    a = np.zeros((40, 30), int)
    a[:, :10], a[:, 10:20], a[:, 20:] = 1, 2, 3
    pre = [(2, 5), (6, 5), (22, 5), (30, 5), (4, 15), (8, 15), (12, 25), (16, 25)]
    post = [(2, 15), (6, 15), (22, 15), (30, 15), (4, 25), (8, 25), (12, 5), (16, 5)]
    return a, np.array(pre, float), np.array(post, float)


def _h2(p):
    return 0.0 if p in (0.0, 1.0) else -(p * np.log2(p) + (1 - p) * np.log2(1 - p))


def test_synapse_partners_reads_the_wiring_diagram():
    a, pre, post = _wiring_case()
    r = S.seg_synapse_partners(a, {"pre": pre, "post": post})
    assert r["edges"].tolist() == [[1, 2], [2, 3], [3, 1]]
    assert r["synapses_per_edge"].tolist() == [4, 2, 2]
    assert r["n_background"] == 0 and r["n_autapse"] == 0 and r["n"] == 8


def test_wiring_identity_and_relabelling_give_zero():
    a, pre, post = _wiring_case()
    same = S.seg_wiring_variation(a, a, {"pre": pre, "post": post})
    assert same["voi"] == 0.0 and same["connection_split"] == 0.0 and same["connection_merge"] == 0.0
    v = S.seg_wiring_variation(a, np.array([0, 70, 50, 60])[a], {"pre": pre, "post": post})
    assert v["voi"] == 0.0 and v["split_connections"] == 0 and v["merged_connections"] == 0


def test_cutting_a_neuron_splits_its_connection_by_the_closed_form():
    a, pre, post = _wiring_case()
    b = a.copy()
    b[20:, :10] = 9                       # 神経 1 の下半分を別物に: 1→2 の 4 個のうち 2 個が 9→2 へ
    v = S.seg_wiring_variation(a, b, {"pre": pre, "post": post})
    n, s, s1 = 8, 4, 2                    # 接続の水準: 1→2 の 4 個が 2 + 2 に散る
    assert v["connection_split"] == pytest.approx(s / n * _h2(s1 / s), abs=1e-12)
    assert v["connection_merge"] == pytest.approx(0.0, abs=1e-12)
    ends, e, e1 = 16, 6, 2                # 端の水準: 神経 1 の端 6 個(1→2 の前 4 + 3→1 の後 2)のうち 2 個が 9 へ
    assert v["split"] == pytest.approx(e / ends * _h2(e1 / e), abs=1e-12)
    assert v["merge"] == pytest.approx(0.0, abs=1e-12)
    assert v["split_connections"] == 1 and v["merged_connections"] == 0


def test_gluing_neurons_without_a_shared_partner_fuses_no_connection():
    a, pre, post = _wiring_case()
    b = np.where(a == 3, 2, a)            # 神経 3 を 2 へ: 1→2 はそのまま、2→3 は 2→2(自己結合)、3→1 は 2→1
    v = S.seg_wiring_variation(a, b, {"pre": pre, "post": post})
    assert v["connection_split"] == pytest.approx(0.0, abs=1e-12)
    assert v["connection_merge"] == pytest.approx(0.0, abs=1e-12)    # 3 本の接続は名前が変わっただけ
    assert v["merged_connections"] == 0
    # 端の水準では融合が見える: 神経 2 の端 6 個と神経 3 の端 4 個が 1 つの物体に
    assert v["merge"] == pytest.approx(10 / 16 * _h2(6 / 10), abs=1e-12)
    assert v["split"] == pytest.approx(0.0, abs=1e-12)
    assert S.seg_synapse_partners(b, {"pre": pre, "post": post})["n_autapse"] == 2


def test_a_merge_that_fuses_two_connections_is_counted_as_merge_by_the_closed_form():
    a, pre, post = _wiring_case()
    pre2 = np.vstack([pre, [(35, 25)]])   # 3→2 のシナプスを 1 個足す
    post2 = np.vstack([post, [(35, 15)]])
    b = np.where(a == 3, 1, a)            # 3 を 1 へ貼ると、1→2 (4 個) と 3→2 (1 個) が 1 本の接続に融合する
    v = S.seg_wiring_variation(a, b, {"pre": pre2, "post": post2})
    n, m, m1 = 9, 5, 4
    assert v["connection_merge"] == pytest.approx(m / n * _h2(m1 / m), abs=1e-12)
    assert v["connection_split"] == pytest.approx(0.0, abs=1e-12)
    assert v["merged_connections"] == 1 and v["split_connections"] == 0
    # 端: 神経 1 の端 6 個と神経 3 の端 5 個(2→3 の後 2・3→1 の前 2・3→2 の前 1)が融合、端は全部で 18 個
    assert v["merge"] == pytest.approx(11 / 18 * _h2(6 / 11), abs=1e-12)
    assert v["split"] == pytest.approx(0.0, abs=1e-12)


def test_lost_synapses_are_singletons_not_one_giant_background_connection():
    a, pre, post = _wiring_case()
    b = a.copy()
    b[:, 10:20] = 0                       # 神経 2 を背景に: 2 に触れる 6 個が行方不明
    v = S.seg_wiring_variation(a, b, {"pre": pre, "post": post})
    assert v["n_lost"] == 6
    assert v["merge"] == pytest.approx(0.0, abs=1e-12)   # 背景を 1 つの物体とみなすと merge が出てしまう
    assert v["connection_merge"] == pytest.approx(0.0, abs=1e-12)
    assert v["split"] > 0 and v["connection_split"] > 0


def test_wiring_voi_equals_label_voi_over_the_connection_codes():
    rng = np.random.default_rng(3)
    a = np.repeat(np.repeat(rng.integers(1, 6, (6, 6)), 5, 0), 5, 1)
    b = np.repeat(np.repeat(rng.integers(1, 4, (6, 6)), 5, 0), 5, 1)
    pre, post = rng.uniform(0, 30, (60, 2)), rng.uniform(0, 30, (60, 2))
    v = S.seg_wiring_variation(a, b, {"pre": pre, "post": post})
    ca = S.seg_synapse_partners(a, {"pre": pre, "post": post})["connection"]
    cb = S.seg_synapse_partners(b, {"pre": pre, "post": post})["connection"]
    w = S.seg_variation_of_information(ca.reshape(1, -1), cb.reshape(1, -1))
    assert v["connection_split"] == pytest.approx(w["split"], abs=1e-12)
    assert v["connection_merge"] == pytest.approx(w["merge"], abs=1e-12)
    # 端の水準 = 端の位置だけで取った分割の VOI(画素の VOI を端に制限したもの)
    ends = np.vstack([pre, post]).astype(int)
    la, lb = a[ends[:, 0], ends[:, 1]], b[ends[:, 0], ends[:, 1]]
    x = S.seg_variation_of_information(la.reshape(1, -1), lb.reshape(1, -1))
    assert v["split"] == pytest.approx(x["split"], abs=1e-12)
    assert v["merge"] == pytest.approx(x["merge"], abs=1e-12)


def test_wiring_in_physical_units_on_an_anisotropic_volume():
    a = np.zeros((5, 20, 20), int)
    a[..., :10], a[..., 10:] = 1, 2
    pre = np.array([[40 * 2 + 1, 4 * 3, 4 * 2]])   # z=2, y=3, x=2 (間隔 40/4/4 nm)
    post = np.array([[40 * 2 + 1, 4 * 3, 4 * 15]])
    r = S.seg_synapse_partners(a, {"pre": pre, "post": post}, spacing=(40, 4, 4))
    assert r["edges"].tolist() == [[1, 2]]


@pytest.mark.parametrize("kw", [
    {"pre": [[50.0, 5.0]]},                       # 外
    {"pre": [[1.0, 1.0], [2.0, 2.0]]},            # 個数違い
    {"pre": [[np.nan, 1.0]]},                     # 非有限
    {"pre": [[1.0, 1.0, 1.0]]},                   # 次元違い
    {"spacing": (1.0, 0.0)},
    {"spacing": (1.0,)},
])
def test_wiring_refuses(kw):
    a = np.ones((10, 10), int)
    args = {"pre": [[1.0, 1.0]], "post": [[2.0, 2.0]], "spacing": None}
    args.update(kw)
    with pytest.raises(ValueError):
        S.seg_synapse_partners(a, {"pre": args["pre"], "post": args["post"]}, spacing=args["spacing"])


def test_a_relabelling_is_exactly_zero_not_rounding_dust():
    """H(a,b) - H(a) の差で出すと、付け替えだけの比較に 8.9e-16 の屑が残った(下の入力で旧実装が実際に出した)。"""
    rng = np.random.default_rng(0)
    a = rng.integers(1, 41, (200,)).reshape(1, -1)
    perm = rng.permutation(60) + 5
    v = S.seg_variation_of_information(a, perm[a])
    assert v["voi"] == 0.0 and v["split"] == 0.0 and v["merge"] == 0.0
    cols = rng.uniform(0, 200, (2, 150))
    syn = {"pre": np.stack([np.full(150, 0.5), cols[0]], 1), "post": np.stack([np.full(150, 0.5), cols[1]], 1)}
    w = S.seg_wiring_variation(a, perm[a], syn)
    assert w["voi"] == 0.0 and w["connection_split"] == 0.0 and w["connection_merge"] == 0.0


def test_synapses_as_an_n_by_2_by_d_array_and_bad_tables():
    a, pre, post = _wiring_case()
    r = S.seg_synapse_partners(a, np.stack([pre, post], axis=1))
    assert r["edges"].tolist() == [[1, 2], [2, 3], [3, 1]]
    for bad in ({"pre": pre}, "pre,post", np.zeros((3, 3, 2))):
        with pytest.raises(ValueError):
            S.seg_synapse_partners(a, bad)


def test_wiring_refuses_shape_mismatch_and_all_background():
    a = np.ones((10, 10), int)
    with pytest.raises(ValueError):
        S.seg_wiring_variation(a, np.ones((10, 11), int), {"pre": [[1.0, 1.0]], "post": [[2.0, 2.0]]})
    with pytest.raises(ValueError):
        S.seg_wiring_variation(np.zeros((10, 10), int), a, {"pre": [[1.0, 1.0]], "post": [[2.0, 2.0]]})



# ---------------------------------------------------------------- NRI(端の対の F 値)
def test_nri_is_one_on_the_truth_and_counts_pairs_by_hand():
    a, pre, post = _wiring_case()
    syn = {"pre": pre, "post": post}
    r = S.seg_synapse_nri(a, a, syn)
    assert r["nri"] == 1.0 and r["fp"] == 0 and r["fn"] == 0
    # 端 16 個: 神経 1 に 6、神経 2 に 6、神経 3 に 4 → 対は C(6,2)+C(6,2)+C(4,2) = 36
    assert r["tp"] == 36 and r["n_ends"] == 16


def test_nri_split_makes_false_negatives_only():
    a, pre, post = _wiring_case()
    b = a.copy()
    b[20:, :10] = 9                       # 神経 1 の端 6 個が 4 + 2 に分かれる: 失う対 = 4·2 = 8
    r = S.seg_synapse_nri(a, b, {"pre": pre, "post": post})
    assert r["fn"] == 8 and r["fp"] == 0 and r["tp"] == 28
    assert r["recall"] == pytest.approx(28 / 36) and r["precision"] == 1.0
    assert r["nri"] == pytest.approx(2 * 28 / (2 * 28 + 8))


def test_nri_merge_makes_false_positives_only():
    a, pre, post = _wiring_case()
    b = np.where(a == 3, 2, a)            # 神経 2(端 6)と 3(端 4)を融合: 偽の対 = 6·4 = 24
    r = S.seg_synapse_nri(a, b, {"pre": pre, "post": post})
    assert r["fp"] == 24 and r["fn"] == 0
    assert r["precision"] == pytest.approx(36 / 60) and r["recall"] == 1.0


def test_nri_equals_one_minus_adapted_rand_over_the_ends_on_random_data():
    rng = np.random.default_rng(5)
    a = np.repeat(np.repeat(rng.integers(1, 6, (6, 6)), 5, 0), 5, 1)
    b = np.repeat(np.repeat(rng.integers(1, 4, (6, 6)), 5, 0), 5, 1)
    syn = {"pre": rng.uniform(0, 30, (60, 2)), "post": rng.uniform(0, 30, (60, 2))}
    r = S.seg_synapse_nri(a, b, syn)
    ends = np.vstack([syn["pre"], syn["post"]]).astype(int)
    la, lb = a[ends[:, 0], ends[:, 1]], b[ends[:, 0], ends[:, 1]]
    other = S.seg_rand(la.reshape(1, -1), lb.reshape(1, -1))
    assert r["nri"] == pytest.approx(1.0 - other["adapted_rand_error"], abs=1e-12)
    assert r["precision"] == pytest.approx(other["precision"], abs=1e-12)
    assert r["recall"] == pytest.approx(other["recall"], abs=1e-12)


def test_nri_lost_ends_are_singletons_and_refusals():
    a, pre, post = _wiring_case()
    b = a.copy()
    b[:, 10:20] = 0
    r = S.seg_synapse_nri(a, b, {"pre": pre, "post": post})
    assert r["n_lost"] == 6 and r["fp"] == 0           # 背景を 1 つの物体とみなすと偽の対が出てしまう
    with pytest.raises(ValueError):
        S.seg_synapse_nri(np.zeros((40, 30), int), a, {"pre": pre, "post": post})
    with pytest.raises(ValueError):
        S.seg_synapse_nri(a, a[:, :20], {"pre": pre, "post": post})



# ---------------------------------------------------------------- 配線の露出(端の個数だけから)
def test_exposure_bounds_sum_to_one_bit_and_density_follows_the_shares():
    a, pre, post = _wiring_case()
    r = S.seg_wiring_exposure(a, {"pre": pre, "post": post})
    assert r["labels"].tolist() == [1, 2, 3] and r["ends"].tolist() == [6, 6, 4]
    assert r["bound"].tolist() == pytest.approx([6 / 16, 6 / 16, 4 / 16], abs=1e-15)
    assert r["total_bound"] == pytest.approx(1.0, abs=1e-15) and r["n_background"] == 0
    # 3 本とも体積 400 / 1200 なので、密度 = 端の取り分 ÷ 1/3
    assert r["density"].tolist() == pytest.approx([1.125, 1.125, 0.75], abs=1e-15)
    # worst: 端 6 個は 3+3 で H2 = 1(bound と一致)、4 個も 2+2
    assert r["worst"].tolist() == pytest.approx(r["bound"].tolist(), abs=1e-15)


def test_expected_h2_binomial_by_hand_and_against_scipy():
    from scipy.stats import binom
    assert S._expected_h2_binomial(1, 0.5) == 0.0
    assert S._expected_h2_binomial(2, 0.5) == pytest.approx(0.5, abs=1e-15)            # 1+1 の確率 1/2 で H2 = 1
    assert S._expected_h2_binomial(3, 0.5) == pytest.approx(0.75 * _h2(1 / 3), abs=1e-15)
    for s, p in ((7, 0.5), (12, 0.2), (40, 0.5), (301, 0.7)):
        k = np.arange(s + 1)
        q = k / s
        h = np.array([_h2(float(x)) for x in q])
        assert S._expected_h2_binomial(s, p) == pytest.approx(float((binom.pmf(k, s, p) * h).sum()), abs=1e-12)
    e = [S._expected_h2_binomial(s, 0.5) for s in range(1, 60)]
    assert all(x < y for x, y in zip(e, e[1:])) and e[-1] < 1.0                     # 単調に 1 へ
    assert S._expected_h2_binomial(4000, 0.5) > 0.999
    assert S._expected_h2_binomial(4, 0.1) < S._expected_h2_binomial(4, 0.5)


def test_exposure_expected_matches_shuffling_the_ends_over_the_object():
    rng = np.random.default_rng(3)
    a = np.zeros((40, 30), int)
    a[:, :10], a[:, 10:20], a[:, 20:] = 1, 2, 3
    s = 5
    pts = np.c_[rng.uniform(0, 40, (2 * s, 1)), rng.uniform(0, 10, (2 * s, 1))]     # 端 2s 個すべて神経 1
    r = S.seg_wiring_exposure(a, {"pre": pts[:s], "post": pts[s:]})
    assert r["labels"].tolist() == [1] and r["ends"].tolist() == [2 * s]
    # 神経 1 の体素に端を 2s 個ばら撒き、体素の中央で切る(p = 1/2)—— 混ぜ直しの H2 の平均が 2 項分布の期待値
    vox = np.flatnonzero(a == 1)
    side = (np.arange(a.size).reshape(a.shape)[a == 1] // 30) >= 20
    h = [_h2(side[rng.choice(len(vox), 2 * s, replace=False)].mean()) for _ in range(6000)]
    assert abs(np.mean(h) - S._expected_h2_binomial(2 * s, 0.5)) < 0.015
    assert r["expected"][0] == pytest.approx(r["bound"][0] * S._expected_h2_binomial(2 * s, 0.5), abs=1e-15)


def test_exposure_drops_background_ends_and_refuses_bad_p():
    a, pre, post = _wiring_case()
    b = a.copy()
    b[:, 10:20] = 0                                             # 神経 2 を背景に: その端 6 個は落ちる
    r = S.seg_wiring_exposure(b, {"pre": pre, "post": post})
    assert r["labels"].tolist() == [1, 3] and r["n_background"] == 6 and r["n_ends"] == 10
    assert r["total_bound"] == pytest.approx(10 / 16, abs=1e-15)
    for bad in (0.0, 1.0, -0.2, float("nan")):
        with pytest.raises(ValueError):
            S.seg_wiring_exposure(a, {"pre": pre, "post": post}, p=bad)
    with pytest.raises(ValueError):
        S.seg_wiring_exposure(np.zeros((40, 30), int), {"pre": pre, "post": post})


def test_exposure_predicts_the_closed_form_cost_of_an_actual_cut():
    a, pre, post = _wiring_case()
    b = a.copy()
    b[20:, :10] = 9                                             # 神経 1 の端 6 個が 4 + 2 に
    v = S.seg_wiring_variation(a, b, {"pre": pre, "post": post})
    r = S.seg_wiring_exposure(a, {"pre": pre, "post": post})
    i = r["labels"].tolist().index(1)
    assert v["split"] == pytest.approx(r["bound"][i] * _h2(2 / 6), abs=1e-12)
    assert v["split"] <= r["worst"][i] + 1e-12 <= r["bound"][i] + 1e-12
