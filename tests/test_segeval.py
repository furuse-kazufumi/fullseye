# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""segeval の門: 分割表は二重ループ、Dice は恒等式と metrics3d、Rand は画素対の総当たりと ARI の期待値 0、VI は独立で
H(X)+H(Y)、境界 F と Hausdorff は総当たり・metrics3d の点群版、過分割・未分割・個数は仕込んだ誤りの数と一致。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import metrics3d
import segcompare
import segeval as SE
import segworld as SW


# ───────────────────────── 構造のあるラベル(乱数だけでは対称性の破れが隠れる) ─────────────────────────
def squares(h=60, w=80, k=6, side=12, gap=4):
    """背景 0 の上に k 個の正方形(1..k)を格子に並べる。"""
    a = np.zeros((h, w), np.int64)
    per_row = (w - gap) // (side + gap)
    for i in range(k):
        r, c = divmod(i, per_row)
        y, x = gap + r * (side + gap), gap + c * (side + gap)
        a[y:y + side, x:x + side] = i + 1
    assert a.max() == k
    return a


def random_labels(shape=(24, 30), k=4, seed=0):
    return np.random.default_rng(seed).integers(0, k, shape)


# ───────────────────────── 1. 分割表 ─────────────────────────
@pytest.mark.parametrize("pred,true", [(random_labels((24, 30), 4, 1), squares(24, 30, 3, 6, 3)),
                                       (squares(40, 40, 4, 10, 3), random_labels((40, 40), 3, 2)),
                                       (random_labels((20, 20), 5, 3), random_labels((20, 20), 5, 4))])
def test_confusion_table_equals_double_loop(pred, true):
    c = SE.seg_confusion_table(pred, true)
    ua, ub = c["labels_true"], c["labels_pred"]
    assert len(ua) >= 2 and len(ub) >= 2
    for i, la in enumerate(ua):
        for j, lb in enumerate(ub):
            assert c["table"][i, j] == int(np.sum((true == la) & (pred == lb)))
    assert c["n"] == pred.size
    assert np.array_equal(c["row_sums"], [int(np.sum(true == la)) for la in ua])
    assert np.array_equal(c["col_sums"], [int(np.sum(pred == lb)) for lb in ub])
    # 最大重なり = 行ごと・列ごとの argmax を自分で引く(背景の行・列は候補にしない)
    for i, la in enumerate(ua):
        if la == 0:
            continue
        best = max((int(np.sum((true == la) & (pred == lb))), lb) for lb in ub if lb != 0)
        assert c["pred_of_true"][i] == (best[1] if best[0] > 0 else -1)


def test_confusion_matching_is_mutual_and_unique_only_for_a_bijection():
    t = squares()
    same = SE.seg_confusion_table(t, t)
    assert same["unique_matching"] and same["mutual_true"][1:].all() and same["claims"].max() == 1
    # 2 番を縦に半分に割る: 真 2 の相手は大きい半分、小さい半分の相手も真 2 → 相互でない列があり一意でない
    p = t.copy()
    ys, xs = np.nonzero(t == 2)
    p[(t == 2) & (np.arange(t.shape[1])[None, :] < xs.min() + 5)] = 99
    c = SE.seg_confusion_table(p, t)
    i2 = int(np.flatnonzero(c["labels_true"] == 2)[0])
    assert c["pred_of_true"][i2] == 2 and c["mutual_true"][i2]
    j99 = int(np.flatnonzero(c["labels_pred"] == 99)[0])
    assert c["true_of_pred"][j99] == 2 and not c["mutual_pred"][j99]
    assert not c["unique_matching"] and c["n_pred"] == c["n_true"] + 1
    # 番号を付け替えても対応の中身は同じ(行・列の並びは変わるので、表は多重集合で、対応は写した値で照合)
    perm = np.random.default_rng(5).permutation(200) + 300
    cp = SE.seg_confusion_table(perm[p], perm[t], background=int(perm[0]))
    assert sorted(cp["table"].ravel().tolist()) == sorted(c["table"].ravel().tolist())
    assert cp["unique_matching"] == c["unique_matching"] and cp["n_pred"] == c["n_pred"]
    assert len(c["labels_true"]) > 1                       # 背景だけなら下のループは何も確かめない
    for la, pl, mu in zip(c["labels_true"], c["pred_of_true"], c["mutual_true"]):
        if la == 0:
            continue
        k = int(np.flatnonzero(cp["labels_true"] == perm[la])[0])
        assert cp["pred_of_true"][k] == perm[pl] and cp["mutual_true"][k] == mu


# ───────────────────────── 2. Dice・Jaccard ─────────────────────────
def test_dice_is_2j_over_1_plus_j_and_matches_metrics3d():
    rng = np.random.default_rng(0)
    cases = [(rng.random((20, 25)) < p, rng.random((20, 25)) < q) for p, q in ((0.3, 0.3), (0.6, 0.2), (0.05, 0.9))]
    cases.append((squares() > 0, np.roll(squares() > 0, 3, axis=1)))
    cases.append((np.zeros((5, 5), bool), np.zeros((5, 5), bool)))
    assert len(cases) == 5
    for p, t in cases:
        r = SE.seg_dice_jaccard(p, t)
        assert r["dice"] == pytest.approx(2.0 * r["jaccard"] / (1.0 + r["jaccard"]), abs=1e-12)
        assert r["dice"] == pytest.approx(metrics3d.voxel_dice(p.astype(float), t.astype(float)), abs=1e-12)
        assert r["jaccard"] == pytest.approx(metrics3d.voxel_iou(p.astype(float), t.astype(float)), abs=1e-12)
    assert SE.seg_dice_jaccard(cases[-1][0], cases[-1][1])["dice"] == 1.0


def test_per_label_dice_uses_the_max_overlap_partner():
    t = squares()
    p = np.roll(t, 2, axis=1)                                  # 全部 2 画素ずらす: 相手は同じ番号、重なり 10/12
    r = SE.seg_dice_jaccard(p, t, per_label=True)
    assert len(r["labels"]) == 6
    for k in range(6):
        inter = 12 * 10
        assert r["per_jaccard"][k] == pytest.approx(inter / (144 + 144 - inter))
        assert r["per_dice"][k] == pytest.approx(2 * r["per_jaccard"][k] / (1 + r["per_jaccard"][k]))
    p2 = t.copy()
    p2[t == 3] = 0                                             # 3 番を消す: 相手なし → 0
    r2 = SE.seg_dice_jaccard(p2, t, per_label=True)
    assert r2["per_dice"][2] == 0.0 and r2["per_dice"][0] == 1.0 and r2["mean_dice"] == pytest.approx(5 / 6)


# ───────────────────────── 3. Rand・ARI(既存 segcompare.seg_rand を門にかける) ─────────────────────────
def test_rand_index_equals_pixel_pair_brute_force():
    t = squares(12, 16, 2, 5, 2)
    p = random_labels((12, 16), 3, 7)
    n = t.size
    tf, pf = t.ravel(), p.ravel()
    agree = 0
    for i in range(n):
        for j in range(i + 1, n):
            agree += int((tf[i] == tf[j]) == (pf[i] == pf[j]))
    assert n * (n - 1) // 2 > 10000
    r = segcompare.seg_rand(t, p)
    assert r["rand_index"] == pytest.approx(agree / (n * (n - 1) / 2), abs=1e-12)


def test_adjusted_rand_has_zero_expectation_under_random_relabelling():
    """Hubert–Arabie の補正は「周辺を固定して画素をランダムに並べ替えた」ときの期待値を 0 にする(定理)。"""
    t = squares(30, 40, 4, 10, 4)
    p = random_labels((30, 40), 5, 1)
    rng = np.random.default_rng(11)
    vals = np.array([segcompare.seg_rand(t, rng.permutation(p.ravel()).reshape(p.shape))["adjusted_rand_index"] for _ in range(400)])
    assert vals.size == 400
    se = vals.std(ddof=1) / math.sqrt(vals.size)
    assert abs(vals.mean()) < 4 * se + 1e-4
    assert segcompare.seg_rand(t, t)["adjusted_rand_index"] == 1.0


# ───────────────────────── 4. VI(既存 segcompare を門にかける) ─────────────────────────
def test_vi_of_independent_partitions_is_the_sum_of_entropies():
    """行の帯と列の帯は独立(各升の画素数 = 行の大きさ × 列の大きさ / N)→ VI = H(a) + H(b)、MI = 0。"""
    a = np.zeros((60, 60), np.int64)
    a[10:30] = 1
    a[30:] = 2
    b = np.zeros((60, 60), np.int64)
    b[:, 15:30] = 1
    b[:, 30:] = 2
    v = segcompare.seg_variation_of_information(a, b)
    ha = -sum(f * math.log2(f) for f in (10 / 60, 20 / 60, 30 / 60))
    hb = -sum(f * math.log2(f) for f in (15 / 60, 15 / 60, 30 / 60))
    assert v["voi"] == pytest.approx(ha + hb, abs=1e-12) and v["mi"] == pytest.approx(0.0, abs=1e-12)
    assert v["h_a"] == pytest.approx(ha, abs=1e-12) and v["h_b"] == pytest.approx(hb, abs=1e-12)
    assert segcompare.seg_variation_of_information(a, a)["voi"] == 0.0
    labs = [a, b, random_labels((60, 60), 3, 1), squares(60, 60, 4, 12, 4)]
    trip = [(x, y, z) for x in labs for y in labs for z in labs]
    assert len(trip) == 64
    for x, y, z in trip:
        d = lambda u, w: segcompare.seg_variation_of_information(u, w)["voi"]  # noqa: E731
        assert d(x, z) <= d(x, y) + d(y, z) + 1e-12


# ───────────────────────── 5. 境界 F・Hausdorff・平均表面距離 ─────────────────────────
def boundary_pixels(lab):
    b = np.zeros(lab.shape, bool)
    b[:, :-1] |= lab[:, 1:] != lab[:, :-1]
    b[:-1, :] |= lab[1:, :] != lab[:-1, :]
    return np.argwhere(b).astype(float)


def brute_distances(P, Q):
    """P の各点から Q への最小距離(総当たり)。"""
    return np.sqrt(((P[:, None, :] - Q[None, :, :]) ** 2).sum(-1)).min(axis=1)


@pytest.mark.parametrize("tau", [0.0, 1.0, 2.5])
def test_boundary_f_equals_brute_force(tau):
    t = squares(50, 60, 4, 14, 5)
    p = np.roll(t, 1, axis=0)
    p[20:30, 40:55] = 7
    r = SE.seg_boundary_f(p, t, tau=tau)
    BP, BT = boundary_pixels(p), boundary_pixels(t)
    assert len(BP) > 100 and len(BT) > 100
    dpt, dtp = brute_distances(BP, BT), brute_distances(BT, BP)
    assert np.allclose(np.sort(r["dist_pred_to_true"]), np.sort(dpt), atol=1e-9)
    prec, rec = float(np.mean(dpt <= tau + 1e-9)), float(np.mean(dtp <= tau + 1e-9))
    assert r["precision"] == pytest.approx(prec) and r["recall"] == pytest.approx(rec)
    assert r["f"] == pytest.approx(2 * prec * rec / (prec + rec))
    if tau == 0.0:
        setP = {tuple(q) for q in BP.astype(int)}
        setT = {tuple(q) for q in BT.astype(int)}
        assert r["precision"] == pytest.approx(len(setP & setT) / len(setP))
    assert SE.seg_boundary_f(t, t, tau=tau)["f"] == 1.0
    assert SE.seg_boundary_f(np.zeros((5, 5), int), np.zeros((5, 5), int))["f"] == 1.0
    assert SE.seg_boundary_f(np.zeros((5, 5), int), squares(5, 5, 1, 2, 1))["f"] == 0.0


def test_hausdorff_equals_metrics3d_point_cloud_version_and_assd_equals_brute_force():
    t = SW.world_blobs_touching(6, 0.25, 3, size=(90, 90), radius=11.0)["labels"]
    p = SW.world_blobs_touching(6, 0.25, 4, size=(90, 90), radius=12.0)["labels"]
    BP, BT = boundary_pixels(p), boundary_pixels(t)
    assert len(BP) > 50 and len(BT) > 50
    P3, T3 = np.c_[BP, np.zeros(len(BP))], np.c_[BT, np.zeros(len(BT))]
    hd = SE.seg_hausdorff(p, t)
    assert hd["hausdorff"] == pytest.approx(metrics3d.hausdorff_distance(P3, T3), abs=1e-9)
    assert hd["hausdorff"] == max(hd["directed_pred_to_true"], hd["directed_true_to_pred"])
    dpt, dtp = brute_distances(BP, BT), brute_distances(BT, BP)
    assert hd["hausdorff_percentile"] == pytest.approx(max(np.percentile(dpt, 95), np.percentile(dtp, 95)), abs=1e-9)
    sd = SE.seg_mean_surface_distance(p, t)
    assert sd["assd"] == pytest.approx((dpt.sum() + dtp.sum()) / (len(dpt) + len(dtp)), abs=1e-9)
    assert sd["rms"] == pytest.approx(math.sqrt(np.mean(np.r_[dpt, dtp] ** 2)), abs=1e-9)
    assert SE.seg_hausdorff(t, t)["hausdorff"] == 0.0 and SE.seg_mean_surface_distance(t, t)["assd"] == 0.0


# ───────────────────────── 6. 過分割・未分割・個数 ─────────────────────────
def inject(t):
    """真 t に誤りを仕込む: 1 と 2 を割る(2 片ずつ)、3 と 4 を融合、5 を消す、偽の塊を 2 つ足す。"""
    p = t.copy()
    for lab in (1, 2):
        ys, xs = np.nonzero(t == lab)
        p[(t == lab) & (np.arange(t.shape[1])[None, :] >= xs.min() + 6)] = 100 + lab
    p[(t == 3) | (t == 4)] = 3
    y, x = np.nonzero(t == 4)
    p[y.min():y.max() + 1, x.min() - 4:x.min()] = 3                 # 3 と 4 を橋でつなぐ
    p[t == 5] = 0
    p[2:5, 60:70] = 200
    p[50:56, 70:78] = 201
    return p


def test_under_over_segmentation_counts_injected_errors():
    t = squares(60, 80, 6, 12, 4)
    p = inject(t)
    r = SE.seg_under_over_segmentation(p, t)
    assert r["over"] == 2 and set(r["over_segmented_true"].tolist()) == {1, 2}
    assert r["under"] == 1 and r["under_segmented_pred"].tolist() == [3]
    assert r["missed"] == 1 and r["spurious"] == 2
    # 多重度を自分で数える: 各予測の多数決の真 / 各真の多数決の予測
    for lab, k in zip(r["labels_true"], r["pieces_per_true"]):
        own = 0
        for pl in np.unique(p[p > 0]):
            cnt = {tl: int(np.sum((p == pl) & (t == tl))) for tl in np.unique(t)}
            if max(cnt, key=cnt.get) == lab:
                own += 1
        assert own == k
    assert len(r["labels_true"]) == 6
    same = SE.seg_under_over_segmentation(t, t)
    assert same["over"] == same["under"] == same["missed"] == same["spurious"] == 0


def test_object_counts_match_classifies_split_merge_missed_false():
    t = squares(60, 80, 6, 12, 4)
    p = inject(t)
    r = SE.seg_object_counts_match(p, t)
    assert (r["n_true"], r["n_pred"]) == (6, 8)                     # 予測 = 1, 101, 2, 102, 3(融合), 6, 200, 201
    assert r["split"] == 2 and set(r["split_true"].tolist()) == {1, 2}
    assert r["merged"] == 1 and r["merged_pred"].tolist() == [3]
    assert r["missed"] == 1 and r["missed_true"].tolist() == [5]
    assert r["false"] == 2 and set(r["false_pred"].tolist()) == {200, 201}
    assert r["matched"] == 1 and not r["counts_match"]              # 6 番だけがそのまま
    assert len(r["edges"]) == 2 + 2 + 2 + 1                         # 1→2 片、2→2 片、3,4→3、6→6
    same = SE.seg_object_counts_match(t, t)
    assert same["counts_match"] and same["matched"] == 6 and len(same["edges"]) == 6
    # 真値つきの世界でも: 真 vs 真は一致、ラベルを 1 つ消すと欠落 1
    for wld in (SW.world_blobs_touching(8, 0.2, 1), SW.world_thin_structures(2)):
        lab = wld["labels"]
        assert SE.seg_object_counts_match(lab, lab)["counts_match"]
        q = lab.copy()
        q[lab == 2] = 0
        rr = SE.seg_object_counts_match(q, lab)
        assert rr["missed"] == 1 and rr["matched"] == lab.max() - 1


# ───────────────────────── 7. 採点表: 真値どおりの世界で満点 ─────────────────────────
def test_score_card_is_perfect_on_every_world():
    worlds = [SW.world_blobs_touching(), SW.world_grains_voronoi(), SW.world_parts_with_shadow(), SW.world_texture_regions(),
              SW.world_gradient_illumination(), SW.world_thin_structures()]
    assert len(worlds) == 6
    for wld in worlds:
        lab = wld["labels"]
        card = SE.seg_score_card(lab, lab)
        assert card["dice"] == 1.0 and card["jaccard"] == 1.0 and card["voi"] == 0.0 and card["adjusted_rand_index"] == 1.0
        assert card["boundary_f"] == 1.0 and card["hausdorff"] == 0.0 and card["assd"] == 0.0
        assert card["over"] == 0 and card["under"] == 0 and card["counts_match"] and card["n_true"] == lab.max()
        # 全部を 1 つにつぶす(最悪の未分割)は満点でない
        worst = SE.seg_score_card(np.ones_like(lab), lab)
        assert worst["under"] == lab.max() - 1 and worst["merged"] == 1 and worst["counts_match"] is False
        assert math.isnan(worst["hausdorff"]) and worst["boundary_f"] == 0.0


# ───────────────────────── 異常入力 ─────────────────────────
@pytest.mark.parametrize("call", [
    lambda: SE.seg_confusion_table(np.zeros((4, 4), int), np.zeros((4, 5), int)),
    lambda: SE.seg_confusion_table(np.zeros((4, 4, 2), int), np.zeros((4, 4, 2), int)),
    lambda: SE.seg_confusion_table(np.full((4, 4), -1), np.zeros((4, 4), int)),
    lambda: SE.seg_confusion_table(np.full((4, 4), 0.5), np.zeros((4, 4), int)),
    lambda: SE.seg_confusion_table("abc", np.zeros((4, 4), int)),
    lambda: SE.seg_confusion_table(np.zeros((4, 4), int), np.zeros((4, 4), int), background=-1),
    lambda: SE.seg_boundary_f(np.zeros((4, 4), int), np.zeros((4, 4), int), tau=-1.0),
    lambda: SE.seg_boundary_f(np.zeros((4, 4), int), np.zeros((4, 4), int), tau=float("nan")),
    lambda: SE.seg_hausdorff(np.zeros((4, 4), int), np.zeros((4, 4), int)),
    lambda: SE.seg_hausdorff(squares(), squares(), percentile=101.0),
    lambda: SE.seg_mean_surface_distance(np.zeros((4, 4), int), squares(4, 4, 1, 2, 1)),
    lambda: SE.seg_object_counts_match(squares(), squares(), min_overlap=0.0),
    lambda: SE.seg_object_counts_match(squares(), squares(), min_overlap=1.5),
    lambda: SE.seg_dice_jaccard(np.zeros((0, 4), int), np.zeros((0, 4), int)),
])
def test_bad_inputs_raise(call):
    with pytest.raises(ValueError):
        call()
