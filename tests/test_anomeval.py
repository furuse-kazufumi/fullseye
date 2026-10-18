# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""異常検知の評価指標(anomeval、4 op)の門。

★真値は op の外から取る:

1. **閉形式**: 正規 2 群 N(0,1) と N(d,1) の AUROC は Φ(d/√2)。大標本の推定がその値を
   Hanley–McNeil の標準誤差の 4 倍以内に含む。
2. **定義そのもの(総当たり)**: 欠陥と良品の全組を数え、同点を 1/2 とした比率と 1e-12 で一致。
3. **第 2 実装**: ``sklearn.metrics.roc_auc_score``(入っていなければ飛ばす。テスト専用の任意依存)。
4. **手計算**: PRO の曲線と AUPRO を、紙の上で数えた小さな例と厳密に照合。
5. **別経路の PRO**: すべての異なる閾値で、領域ごとの重なりを ``scipy.ndimage.label`` と
   Python のループで数え直した曲線と一致(op の累積和の経路とは独立)。

壊す探針: 欠陥マスクを 1 画素ずらすと PRO の手計算の値から外れること、スコアの単調変換で
AUROC が変わらないこと(順位だけで決まる)、定義できない入力(欠陥なし・良品なし・2 値でない
マスク・非有限)は ``ValueError``。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest
from scipy import ndimage as ndi
from scipy import stats

import anomeval as AE
import opsspc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------- #
# 1. AUROC                                                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("d", [0.0, 0.5, 1.5])
def test_image_auroc_matches_the_binormal_closed_form(d):
    rng = np.random.default_rng([2026, 10, 18, int(d * 10)])
    n = 20_000
    s = np.r_[rng.standard_normal(n), d + rng.standard_normal(n)]
    y = np.r_[np.zeros(n), np.ones(n)]
    r = AE.anomaly_image_auroc(s, y)
    a = stats.norm.cdf(d / math.sqrt(2.0))
    q1 = a / (2 - a)
    q2 = 2 * a * a / (1 + a)
    se = math.sqrt((a * (1 - a) + (n - 1) * (q1 - a * a) + (n - 1) * (q2 - a * a)) / (n * n))
    assert abs(r["auroc"] - a) < 4 * se, (r["auroc"], a, se)
    assert (r["n_pos"], r["n_neg"]) == (n, n)


def _brute_auroc(pos, neg):
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return (gt + 0.5 * eq) / (pos.size * neg.size)


def test_pixel_auroc_equals_the_pairwise_definition_with_ties():
    rng = np.random.default_rng(7)
    s = np.round(rng.random((3, 12, 9)), 1)                    # 同点だらけ
    m = np.zeros(s.shape, dtype=bool)
    m[0, 2:5, 1:4] = True
    m[2, 8, 8] = True
    r = AE.anomaly_pixel_auroc(s, m)
    assert abs(r["auroc"] - _brute_auroc(s[m], s[~m])) < 1e-12
    # 画像 AUROC と同じ統計量(平らに並べた画素を 1 列として)
    assert abs(AE.anomaly_image_auroc(s.ravel(), m.ravel())["auroc"] - r["auroc"]) < 1e-15


def test_auroc_agrees_with_sklearn_when_available():
    skm = pytest.importorskip("sklearn.metrics")
    rng = np.random.default_rng(11)
    s = np.round(rng.standard_normal(500), 2)
    y = rng.random(500) < 0.3
    assert abs(AE.anomaly_image_auroc(s, y)["auroc"] - skm.roc_auc_score(y, s)) < 1e-12


def test_auroc_depends_only_on_the_order_of_the_scores():
    rng = np.random.default_rng(3)
    s = rng.random((2, 16, 16))
    m = rng.random((2, 16, 16)) < 0.1
    a = AE.anomaly_pixel_auroc(s, m)["auroc"]
    assert AE.anomaly_pixel_auroc(np.exp(5 * s) - 3.0, m)["auroc"] == a
    assert abs(AE.anomaly_pixel_auroc(-s, m)["auroc"] - (1.0 - a)) < 1e-12


# --------------------------------------------------------------------------- #
# 2. PRO                                                                       #
# --------------------------------------------------------------------------- #
#: 手計算の例。領域 A = 画素 0,1(スコア 0.9, 0.2)、領域 B = 画素 5(0.8)、良品 7 画素
#: (0.1, 0.5, 0.0 ×5)。閾値を下げると (FPR, PRO) は
#:   (0,0) → 0.9: (0, 1/4) → 0.8: (0, 3/4) → 0.5: (1/7, 3/4) → 0.2: (1/7, 1) → 0.1: (2/7, 1) → 0.0: (1, 1)
_HAND_S = np.array([[0.9, 0.2, 0.1, 0.5, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0]])
_HAND_M = np.array([[1, 1, 0, 0, 0, 1, 0, 0, 0, 0]], dtype=bool)


def test_pro_curve_matches_the_hand_count():
    r = AE.anomaly_pro(_HAND_S, _HAND_M, fpr_max=1.0)
    want_f = [0, 0, 0, 1 / 7, 1 / 7, 2 / 7, 1]
    want_p = [0, 0.25, 0.75, 0.75, 1, 1, 1]
    assert np.allclose(r["fpr"], want_f, atol=1e-15) and np.allclose(r["pro"], want_p, atol=1e-15)
    assert abs(r["aupro"] - (0.75 / 7 + 6 / 7)) < 1e-15
    r3 = AE.anomaly_pro(_HAND_S, _HAND_M)                      # 慣習の上限 0.3
    assert r3["fpr_max"] == 0.3
    assert abs(r3["aupro"] - (0.75 / 7 + (0.3 - 1 / 7)) / 0.3) < 1e-14
    assert r3["n_regions"] == 2


def test_pro_hand_count_breaks_when_the_mask_is_shifted():
    """探針: マスクを 1 画素ずらしただけで手計算の値から外れる(門が素通りしない)。"""
    good = AE.anomaly_pro(_HAND_S, _HAND_M)["aupro"]
    bad = AE.anomaly_pro(_HAND_S, np.roll(_HAND_M, 1, axis=1))["aupro"]
    assert abs(good - bad) > 0.05, (good, bad)


def test_pro_weighs_a_small_region_like_a_large_one():
    s = np.zeros((1, 20, 20))
    m = np.zeros((1, 20, 20), dtype=bool)
    m[0, 1:11, 1:11] = True            # 100 画素
    m[0, 15, 15] = True                # 1 画素
    s[0, 15, 15] = 1.0                 # 小さい方だけ当てる
    r = AE.anomaly_pro(s, m, fpr_max=0.3)
    # 閾値 1 で PRO = (0 + 1)/2 (FPR 0)。次の閾値 0 で全部が立つ (FPR 1, PRO 1)。台形則は
    # その間を直線でつなぐ慣習なので FPR 0.3 での PRO は 0.65、面積 (0.5+0.65)/2*0.3 → 0.575。
    assert abs(r["pro"][1] - 0.5) < 1e-15
    assert abs(r["pro"][-1] - 0.65) < 1e-12
    assert abs(r["aupro"] - 0.575) < 1e-12


def _brute_pro_curve(s, m):
    """別経路: 異なる閾値ごとに領域を数え直す(Python のループ)。"""
    regs = []
    for i in range(s.shape[0]):
        lab, n = ndi.label(m[i], structure=np.ones((3, 3), dtype=int))
        for k in range(1, n + 1):
            regs.append((i, lab == k))
    neg = ~m
    pts = [(0.0, 0.0)]
    for t in np.unique(s)[::-1]:
        hit = s >= t
        pro = np.mean([hit[i][rm].mean() for i, rm in regs])
        pts.append(((hit & neg).sum() / neg.sum(), pro))
    return np.array(pts)


def test_pro_curve_agrees_with_an_independent_region_loop():
    rng = np.random.default_rng(5)
    s = np.round(rng.random((3, 14, 14)), 2)
    m = np.zeros(s.shape, dtype=bool)
    m[0, 2:6, 3:9] = True
    m[0, 10, 10:13] = True
    m[1, 7:12, 1:3] = True
    s = s + 0.5 * m
    r = AE.anomaly_pro(s, m, fpr_max=1.0)
    ref = _brute_pro_curve(s, m)
    assert np.allclose(r["fpr"], ref[:, 0], atol=1e-12)
    assert np.allclose(r["pro"], ref[:, 1], atol=1e-12)
    # 1 点ずつは region_overlap(bincount の経路)とも一致
    t = np.unique(s)[len(np.unique(s)) // 2]
    ro = AE.anomaly_region_overlap(s >= t, m)
    j = int(np.nonzero(np.isclose(np.unique(s)[::-1], t))[0][0]) + 1
    assert abs(ro["pro"] - ref[j, 1]) < 1e-12 and abs(ro["fpr"] - ref[j, 0]) < 1e-12


def test_region_overlap_hand_example():
    m = np.zeros((1, 10, 10), dtype=bool)
    m[0, 0:2, 0:4] = True              # 8 画素
    m[0, 6:8, 6:8] = True              # 4 画素
    p = np.zeros_like(m)
    p[0, 0:2, 0:2] = True              # 4/8
    p[0, 6, 6] = True                  # 1/4
    p[0, 9, 0] = True                  # 誤検出 1 / 良品 88
    r = AE.anomaly_region_overlap(p, m, min_overlap=0.5)
    assert np.allclose(r["overlap"], [0.5, 0.25])
    assert r["pro"] == 0.375 and r["detected_fraction"] == 0.5 and r["hit_any"] == 1.0
    assert abs(r["fpr"] - 1 / 88) < 1e-15


# --------------------------------------------------------------------------- #
# 3. 拒否                                                                      #
# --------------------------------------------------------------------------- #
def test_undefined_or_malformed_inputs_are_refused():
    s = np.random.default_rng(0).random((2, 8, 8))
    m = np.zeros((2, 8, 8), dtype=bool)
    with pytest.raises(ValueError):
        AE.anomaly_pixel_auroc(s, m)                            # 欠陥なし
    with pytest.raises(ValueError):
        AE.anomaly_pixel_auroc(s, np.ones_like(m))              # 良品なし
    with pytest.raises(ValueError):
        AE.anomaly_pro(s, m)
    m[0, 1, 1] = True
    with pytest.raises(ValueError):
        AE.anomaly_pixel_auroc(s, m.astype(int) * 255)          # 2 値でない
    bad = s.copy()
    bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        AE.anomaly_pro(bad, m)
    with pytest.raises(ValueError):
        AE.anomaly_pro(s, m, fpr_max=0.0)
    with pytest.raises(ValueError):
        AE.anomaly_pixel_auroc(s, m[:1])                        # 形違い
    with pytest.raises(ValueError):
        AE.anomaly_image_auroc(np.array([]), np.array([]))      # 空
    with pytest.raises(ValueError):
        AE.anomaly_image_auroc([0.1, 0.2], [1, 1])              # 片側だけ
    with pytest.raises(ValueError):
        AE.anomaly_region_overlap(np.zeros((0, 4, 4)), np.zeros((0, 4, 4)))
    with pytest.raises(ValueError):
        AE.anomaly_region_overlap(m, m, min_overlap=1.5)


# --------------------------------------------------------------------------- #
# 4. 台帳と公開経路                                                             #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    listed = set(opsspc.list_ops("anomaly_eval"))
    assert listed == set(AE.__all__), (listed, AE.__all__)
    assert not opsspc.missing()
    for name in listed:
        assert opsspc.info(name)["module"] == "anomeval"
        assert opsspc.info(name)["out"] == "table"
        assert len(opsspc.info(name)["doc"]) >= 20


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs

    for name in AE.__all__:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = {r[0]: r for r in tc.catalog() if r[0].startswith("anomaly_")}
    assert set(rows) == set(AE.__all__)
    assert rows["anomaly_image_auroc"][2] == ["signal", "signal"]
    assert rows["anomaly_pro"][2] == ["video", "video"]


def test_the_fuzzer_builds_arguments_that_actually_compute():
    """★宣言型 video は広い —— 任意の動画はマスクとして 2 値でなく拒否される。ビルダが本物を組むこと。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    for name in AE.__all__:
        assert name in cf.OP_ARG_BUILDERS, name
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        out = getattr(AE, name)(*args, **kw)
        assert cf.TYPE_CHECKS["table"](out)
    a, k = cf.OP_ARG_BUILDERS["anomaly_region_overlap"](None, np.random.default_rng(0))
    r = AE.anomaly_region_overlap(*a, **k)
    assert 0.0 < r["detected_fraction"] < 1.0, "min_overlap の探針が効かない種"
