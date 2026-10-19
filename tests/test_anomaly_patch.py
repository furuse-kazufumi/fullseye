# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""パッチ特徴の異常検知(anomaly_patch、5 op)と評価の追加分(anomeval の F1 最大・運用点、3 op)の門。

★真値は op の外から取る:

1. **特徴の閉形式**: 傾き a の斜面の勾配の大きさは a(傾きの向き θ なら倍角成分が a·cos2θ, a·sin2θ)、
   波長に合った正弦波の Gabor 応答は ½Σ(包絡)≈πσe²、直交する向きは 0、定数画像の LBP は全画素が一様パターン「8」、
   定数の色は反対色の差そのもの。
2. **第 2 実装**: 縮小推定の強さと共分散は ``sklearn.covariance.LedoitWolf``、F1 最大は
   ``sklearn.metrics.precision_recall_curve``、最近傍は ``scipy.spatial.distance.cdist``、
   Clopper–Pearson は ``scipy.stats.binomtest(...).proportion_ci``。Mahalanobis 距離は
   ``np.cov`` と ``np.linalg.solve`` で数え直した別経路。
3. **分布の校正**: 白色雑音の画像から学んだ位置ごとの正規分布が、新しい白色雑音のパッチに付ける
   距離の超過率が F 分布の分位点(Hotelling の予測区間)と二項の 4σ 以内。
4. **k 中心の保証**: 貪欲被覆の半径は最適な k 中心の半径の 2 倍以下(総当たりで最適を求める)。

壊す探針: 欠陥マスクを 1 画素ずらすと PRO が下がる / 正常画像を欠陥扱いにすると検出器と無作為の差が縮む /
共分散が特異(n <= D)で縮小を宣言しないと拒否 / 欠陥が少なすぎて再現率を保証できないと拒否 /
位置を見ない記憶バンクは「正しい模様が違う場所にある」欠陥を見逃し、位置を見る記憶バンクは見つける。
"""
from __future__ import annotations

import itertools
import math
import os

import numpy as np
import pytest
from scipy import ndimage as ndi
from scipy import stats

import anomaly_patch as AP
import anomeval as AE
import opsspc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --------------------------------------------------------------------------- #
# 材料                                                                         #
# --------------------------------------------------------------------------- #
def _tex(rng, n=64):
    """滑らかな確率的テクスチャ(確率場)。"""
    return ndi.gaussian_filter(rng.standard_normal((n, n)), 2.0) * 4.0 + 0.5 + 0.02 * rng.standard_normal((n, n))


def _spot(img, rng, amp):
    n = img.shape[0]
    r, c = rng.integers(14, n - 14, 2)
    yy, xx = np.mgrid[0:n, 0:n]
    m = (yy - r) ** 2 + (xx - c) ** 2 <= 9
    return img + amp * ndi.gaussian_filter(m.astype(float), 0.5), m


def _scratch(img, rng, amp):
    n = img.shape[0]
    r, c = rng.integers(14, n - 14, 2)
    ang = rng.uniform(0, np.pi)
    t = np.arange(-10, 11)
    m = np.zeros(img.shape, bool)
    m[np.clip(np.round(r + t * np.sin(ang)).astype(int), 0, n - 1),
      np.clip(np.round(c + t * np.cos(ang)).astype(int), 0, n - 1)] = True
    m = ndi.binary_dilation(m, iterations=1)
    return img - amp * ndi.gaussian_filter(m.astype(float), 0.5), m


def _world(n_train, n_test, seed, amp=1.2):
    """良品 n_train 枚と、試験 n_test 枚(半分が不良: 点と細い傷)。真の欠陥マスクつき。"""
    rng = np.random.default_rng([2026, 10, 19, seed])
    train = np.stack([_tex(rng) for _ in range(n_train)]) if n_train else np.zeros((0, 64, 64))
    te, ms, lab = [], [], []
    for i in range(n_test):
        im = _tex(rng)
        m = np.zeros(im.shape, bool)
        if i % 2:
            im, m = (_spot if (i // 2) % 2 else _scratch)(im, rng, amp)
        te.append(im)
        ms.append(m)
        lab.append(bool(i % 2))
    return train, np.stack(te), np.stack(ms), np.array(lab)


def _maps(score, model, tests, **kw):
    return np.stack([score(x, model, **kw)["map"] for x in tests])


# --------------------------------------------------------------------------- #
# 0. 台帳                                                                      #
# --------------------------------------------------------------------------- #
def test_ledger_registers_the_new_ops():
    assert len(opsspc.list_ops("anomaly_patch")) == 5
    assert len(opsspc.list_ops("anomaly_eval")) == 7
    assert sorted(opsspc.list_ops("anomaly_patch")) == [
        "patch_features", "patchbank_fit", "patchbank_score", "patchdist_fit", "patchdist_score"]
    assert opsspc.missing() == []


def test_the_public_path_reaches_every_new_op():
    import fullseye as fs
    names = ["patch_features", "patchdist_fit", "patchdist_score", "patchbank_fit", "patchbank_score",
             "anomaly_pixel_f1_max", "anomaly_image_f1_max", "anomaly_operating_point"]
    assert len(names) == 8
    got = [hasattr(fs.ledger, n) for n in names]
    assert got == [True] * 8


# --------------------------------------------------------------------------- #
# 1. F1 最大                                                                    #
# --------------------------------------------------------------------------- #
def test_f1_max_by_hand():
    s = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4])
    y = np.array([1, 1, 0, 1, 0, 0])
    r = AE.anomaly_image_f1_max(s, y)
    # しきい値ごと: 0.9 -> 1/2, 0.8 -> 4/5, 0.7 -> 2/3, 0.6 -> 6/7, 0.5 -> 3/4, 0.4 -> 2/3
    assert (r["n_pos"], r["n_neg"]) == (3, 3)
    assert r["f1"] == pytest.approx(6.0 / 7.0, abs=1e-15)
    assert r["threshold"] == 0.6
    assert r["precision"] == pytest.approx(0.75, abs=1e-15)
    assert r["recall"] == 1.0


def test_f1_max_groups_equal_scores_as_one_threshold():
    s = np.array([1.0, 1.0, 0.0, 0.0])
    y = np.array([1, 0, 1, 0])
    r = AE.anomaly_image_f1_max(s, y)
    # >= 1: TP1 FP1 FN1 -> 2/4 = 0.5; >= 0: TP2 FP2 FN0 -> 4/6. 1 つの閾値の内側は分けられない。
    assert r["f1"] == pytest.approx(4.0 / 6.0, abs=1e-15)
    assert r["threshold"] == 0.0


def test_f1_max_matches_sklearn_precision_recall_curve():
    sk = pytest.importorskip("sklearn.metrics")
    rng = np.random.default_rng(11)
    s = np.round(rng.standard_normal(4000) + 0.7 * (np.arange(4000) % 5 == 0), 1)    # 同点だらけ
    y = (np.arange(4000) % 5 == 0)
    p, r, _ = sk.precision_recall_curve(y, s)
    f = 2 * p * r / np.maximum(p + r, 1e-300)
    got = AE.anomaly_image_f1_max(s, y)
    assert got["n_pos"] == 800
    assert got["f1"] == pytest.approx(float(f.max()), abs=1e-12)


def test_pixel_f1_equals_the_flattened_image_f1():
    rng = np.random.default_rng(3)
    sc = rng.random((3, 10, 12))
    mk = rng.random((3, 10, 12)) > 0.8
    a = AE.anomaly_pixel_f1_max(sc, mk)
    b = AE.anomaly_image_f1_max(sc.ravel(), mk.ravel())
    assert a["n_pos"] == int(mk.sum())
    assert a == b


def test_f1_refuses_what_is_undefined():
    with pytest.raises(ValueError, match="positives and negatives"):
        AE.anomaly_image_f1_max([0.1, 0.2], [0, 0])
    with pytest.raises(ValueError):
        AE.anomaly_pixel_f1_max(np.zeros((1, 4, 4)), np.zeros((1, 4, 4), bool))
    with pytest.raises(ValueError, match="non-finite"):
        AE.anomaly_image_f1_max([0.1, np.nan], [0, 1])


# --------------------------------------------------------------------------- #
# 2. 運用点                                                                     #
# --------------------------------------------------------------------------- #
def test_operating_point_rule_of_n_required_and_refusal():
    # 全部検出して下限 = (1 - conf)^(1/n) >= recall となる最小の n = ceil(ln(1-conf)/ln(recall))
    y = np.r_[np.zeros(40), np.ones(59)].astype(bool)
    s = np.r_[np.linspace(0.0, 0.4, 40), np.linspace(0.6, 1.0, 59)]
    r = AE.anomaly_operating_point(s, y, recall=0.95, confidence=0.95)
    assert r["n_required"] == 59
    assert r["detected"] == 59 and r["n_pos"] == 59
    assert r["recall_lower"] == pytest.approx(0.05 ** (1.0 / 59.0), abs=1e-12)
    assert r["recall_lower"] >= 0.95
    assert r["threshold"] == pytest.approx(0.6, abs=1e-12)          # 最も低い欠陥のスコア
    assert r["fpr"] == 0.0
    with pytest.raises(ValueError, match="cannot be guaranteed"):
        AE.anomaly_operating_point(s[:-1], y[:-1], recall=0.95, confidence=0.95)    # 欠陥 58 枚


def test_operating_point_lower_limit_matches_scipy_exact_interval_and_is_minimal():
    rng = np.random.default_rng(5)
    y = np.r_[np.zeros(200), np.ones(120)].astype(bool)
    s = np.r_[rng.standard_normal(200), 2.0 + rng.standard_normal(120)]
    r = AE.anomaly_operating_point(s, y, recall=0.9, confidence=0.95)
    n, k = r["n_pos"], r["detected"]
    assert (n, r["n_neg"]) == (120, 200)
    # 第 2 実装: 両側 90 % の正確な区間の下限 = 片側 95 % の下限
    lo = stats.binomtest(k, n).proportion_ci(confidence_level=0.90, method="exact").low
    assert r["recall_lower"] == pytest.approx(lo, abs=1e-9)
    assert lo >= 0.9
    # 最小性: 検出を 1 つ減らすと保証が切れる
    lo1 = stats.binomtest(k - 1, n).proportion_ci(confidence_level=0.90, method="exact").low
    assert lo1 < 0.9
    # 閾値は k 番目に高い欠陥のスコア、誤検出は直接数える
    assert r["threshold"] == np.sort(s[y])[::-1][k - 1]
    assert r["fpr"] == pytest.approx(float((s[~y] >= r["threshold"]).mean()), abs=0.0)
    up = stats.binomtest(int((s[~y] >= r["threshold"]).sum()), 200).proportion_ci(
        confidence_level=0.90, method="exact").high
    assert r["fpr_upper"] == pytest.approx(up, abs=1e-9)


def test_operating_point_stricter_recall_lowers_the_threshold():
    rng = np.random.default_rng(6)
    y = np.r_[np.zeros(100), np.ones(150)].astype(bool)
    s = np.r_[rng.standard_normal(100), 1.5 + rng.standard_normal(150)]
    t = [AE.anomaly_operating_point(s, y, recall=q, confidence=0.9)["threshold"] for q in (0.7, 0.8, 0.9, 0.95)]
    assert len(t) == 4
    assert t == sorted(t, reverse=True)
    assert len(set(t)) == 4
    f = [AE.anomaly_operating_point(s, y, recall=0.9, confidence=c)["threshold"] for c in (0.5, 0.9, 0.99)]
    assert f[0] > f[1] > f[2]


def test_operating_point_refuses_bad_arguments():
    y = np.r_[np.zeros(5), np.ones(80)].astype(bool)
    s = np.arange(85.0)
    with pytest.raises(ValueError, match="recall"):
        AE.anomaly_operating_point(s, y, recall=1.0)
    with pytest.raises(ValueError, match="confidence"):
        AE.anomaly_operating_point(s, y, confidence=0.0)
    with pytest.raises(ValueError, match="both defective and good"):
        AE.anomaly_operating_point(s[5:], y[5:])


# --------------------------------------------------------------------------- #
# 3. 特徴の閉形式                                                               #
# --------------------------------------------------------------------------- #
def _interior(f, lo=4, hi=11):
    return f[lo:hi, lo:hi]


@pytest.mark.parametrize("theta", [0.0, math.pi / 6, math.pi / 2, 1.0])
def test_gradient_channels_of_a_ramp_are_the_closed_form(theta):
    a = 0.02
    yy, xx = np.mgrid[0:64, 0:64].astype(float)
    img = a * (xx * math.cos(theta) + yy * math.sin(theta))
    r = AP.patch_features(img, patch=8, stride=4, scales=(2.0,), groups=("gradient",))
    assert r["names"] == ["grad_mag_s2", "grad_c2_s2", "grad_s2_s2"]
    f = _interior(r["features"])
    assert f.shape == (7, 7, 3)
    assert np.allclose(f[..., 0], a, rtol=1e-3)           # 4σ で打ち切ったガウス核の傾き: 3.5e-4 下
    assert np.allclose(f[..., 1], a * math.cos(2 * theta), atol=2e-5)
    assert np.allclose(f[..., 2], a * math.sin(2 * theta), atol=2e-5)


def test_gabor_matched_sinusoid_and_orthogonal_orientation():
    s = 2.0
    lam = 4.0 * s
    se = 0.56 * lam
    xx = np.arange(96, dtype=float)[None, :] * np.ones((96, 1))
    img = np.cos(2 * np.pi * xx / lam + 0.3)
    r = AP.patch_features(img, patch=8, stride=8, scales=(s,), groups=("gabor",), n_orient=4)
    assert r["names"] == ["gabor0_s2", "gabor1_s2", "gabor2_s2", "gabor3_s2"]
    f = r["features"][3:8, 3:8]
    expected = math.pi * se * se * (1.0 - 2.0 * math.exp(-0.5 * (2 * math.pi * se / lam) ** 2))     # 半分 x 包絡の和、DC 補正つき
    assert np.allclose(f[..., 0], expected, rtol=2e-3)
    assert float(np.abs(f[..., 2]).max()) < 1e-3 * expected                    # 搬送波が y 方向: 直交
    assert float(f[..., 1].mean()) < 0.5 * expected                            # 45 度ずれ: 弱い


def test_lbp_codes_of_a_constant_a_ramp_and_a_spike():
    flat = np.full((16, 16), 0.5)
    code = AP._lbp_riu2(flat, 1)
    assert set(np.unique(code).tolist()) == {8}                                 # 全隣接が >= : 一様で 8 個の 1
    yy, xx = np.mgrid[0:16, 0:16].astype(float)
    ramp = AP._lbp_riu2(xx, 1)[4:12, 4:12]                                      # 右が大きい斜面: 1 1 1 0 0 0 1 1 -> 5
    assert set(np.unique(ramp).tolist()) == {5}
    spike = np.zeros((16, 16))
    spike[8, 8] = 1.0
    assert int(AP._lbp_riu2(spike, 1)[8, 8]) == 0                               # 周りより大きい: 全部 0 のビット
    r = AP.patch_features(flat, patch=4, stride=4, scales=(1.0,), groups=("lbp",))
    assert r["dim"] == 10
    assert np.allclose(r["features"][..., 8], 1.0) and np.allclose(r["features"][..., :8], 0.0)


def test_fourier_bands_put_a_low_frequency_wave_in_the_lowest_band():
    xx = np.arange(64, dtype=float)[None, :] * np.ones((64, 1))
    img = np.cos(2 * np.pi * 0.1 * xx)
    r = AP.patch_features(img, patch=16, stride=16, groups=("fourier",), scales=(1.0,))
    assert r["names"] == ["fourier_b0", "fourier_b1", "fourier_b2"]
    f = r["features"]
    assert float(f[..., 0].min()) > -0.05
    assert float(f[..., 1].max()) < -2.5 and float(f[..., 2].max()) < -2.5


def test_colour_group_is_the_opponent_difference():
    img = np.empty((16, 16, 3))
    img[...] = (0.8, 0.5, 0.2)
    r = AP.patch_features(img, patch=4, stride=4, scales=(1.0,), groups=("color", "intensity"))
    assert r["names"] == ["mean_s1", "opp_rg_s1", "opp_yb_s1"]
    d = dict(zip(r["names"], np.moveaxis(r["features"], -1, 0)))
    assert np.allclose(d["opp_rg_s1"], 0.3)
    assert np.allclose(d["opp_yb_s1"], 0.45)
    assert np.allclose(d["mean_s1"], 0.299 * 0.8 + 0.587 * 0.5 + 0.114 * 0.2)
    with pytest.raises(ValueError, match="color"):
        AP.patch_features(np.zeros((16, 16)), groups=("color",))


def test_feature_dimensions_follow_the_parameters():
    img = _tex(np.random.default_rng(1), 32)
    d = {}
    for g, n in (("intensity", 1), ("gradient", 3), ("gabor", 4), ("lbp", 10)):
        d[g] = AP.patch_features(img, scales=(1.0, 2.0), groups=(g,), n_orient=4)["dim"]
        assert d[g] == 2 * n
    assert d["gabor"] == 8
    assert AP.patch_features(img, scales=(1.0, 2.0), groups=("gabor",), n_orient=6)["dim"] == 12
    r = AP.patch_features(img, patch=8, stride=4)
    assert r["grid"] == (7, 7)
    assert r["dim"] == 51


# --------------------------------------------------------------------------- #
# 4. 位置ごとの正規分布                                                         #
# --------------------------------------------------------------------------- #
def test_shrinkage_intensity_and_covariance_match_ledoit_wolf_of_scikit_learn():
    cov = pytest.importorskip("sklearn.covariance")
    rng = np.random.default_rng(8)
    a = rng.standard_normal((5, 5))
    x = rng.standard_normal((30, 5)) @ a
    lw = cov.LedoitWolf().fit(x)
    xc = x - x.mean(axis=0)
    s = xc.T @ xc / 30
    assert AP._lw_intensity(xc, s) == pytest.approx(float(lw.shrinkage_), abs=1e-12)
    mean, prec, lam = AP._gauss_fit(x[:, None, None, :], "auto", 0.0, "t")
    assert mean.shape == (1, 1, 5)
    assert np.allclose(np.linalg.inv(prec[0, 0]), lw.covariance_, rtol=1e-10, atol=1e-12)
    assert float(lam[0, 0]) == pytest.approx(float(lw.shrinkage_), abs=1e-12)


def test_patchdist_score_equals_an_independent_mahalanobis():
    rng = np.random.default_rng(9)
    stack = np.stack([_tex(rng, 32) for _ in range(12)])
    kw = dict(patch=8, stride=8, scales=(1.0, 2.0), groups=("intensity", "gradient"))
    lam = 0.3
    m = AP.patchdist_fit(stack, shrinkage=lam, ridge=0.0, **kw)
    test = _tex(rng, 32)
    got = AP.patchdist_score(test, m, smooth=0.0)
    f = np.stack([AP.patch_features(x, **kw)["features"] for x in stack])
    ft = AP.patch_features(test, **kw)["features"]
    assert got["grid"].shape == (4, 4)
    assert m["dim"] == 8
    ref = np.empty((4, 4))
    for i in range(4):
        for j in range(4):
            x = f[:, i, j, :]
            s = np.cov(x.T, bias=True)
            sig = (1 - lam) * s + lam * np.trace(s) / 8 * np.eye(8)
            d = ft[i, j] - x.mean(axis=0)
            ref[i, j] = math.sqrt(float(d @ np.linalg.solve(sig, d)))
    assert np.allclose(got["grid"], ref, rtol=1e-8)
    assert got["image_score"] == pytest.approx(float(got["map"].max()), abs=0.0)


@pytest.mark.parametrize("q", [0.90, 0.99])
def test_patchdist_distances_on_white_noise_follow_the_hotelling_distribution(q):
    # 白色雑音の平均強度 3 本(σ = 1, 2, 4): 位置ごとの正規分布が正しいなら d^2 は予測区間の F 分布
    n, d_ = 300, 3
    rng = np.random.default_rng([2026, 10, 19, 77])
    kw = dict(patch=8, stride=8, scales=(1.0, 2.0, 4.0), groups=("intensity",))
    train = rng.standard_normal((n, 64, 64))
    m = AP.patchdist_fit(train, shrinkage="none", **kw)
    assert m["dim"] == d_ and m["grid"] == (8, 8)
    test = rng.standard_normal((120, 64, 64))
    d2 = np.stack([AP.patchdist_score(x, m, smooth=0.0)["grid"] ** 2 for x in test]).ravel()
    assert d2.size == 120 * 64
    # 新しい 1 点の T^2 = (1 + 1/n) (n-1) d / (n-d) F(d, n-d)、最尤の共分散は S_unb (n-1)/n なので d2_mle = T^2 n/(n-1)
    t = (1 + 1.0 / n) * (n - 1) * d_ / (n - d_) * stats.f.ppf(q, d_, n - d_) * n / (n - 1)
    frac = float((d2 > t).mean())
    n_eff = d2.size / 2.0                                    # 隣り合う窓は平滑化の裾でわずかに相関する
    se = math.sqrt((1 - q) * q / n_eff)
    assert abs(frac - (1 - q)) < 4 * se, (frac, 1 - q, se)


def test_singular_covariance_is_declared_or_refused():
    rng = np.random.default_rng(10)
    stack = np.stack([_tex(rng, 32) for _ in range(5)])            # n = 5 << D = 51
    with pytest.raises(ValueError, match="shrinkage"):
        AP.patchdist_fit(stack, shrinkage="none")
    with pytest.raises(ValueError, match="shrinkage"):
        AP.patchdist_fit(stack, shrinkage=0.0)
    m = AP.patchdist_fit(stack)                                      # 既定 = auto: 宣言して返す
    assert m["dim"] == 51 and m["n_train"] == 5
    assert m["shrinkage"] == "auto"
    assert 0.0 < m["shrinkage_mean"] <= 1.0
    assert m["shrinkage_map"].shape == m["grid"]
    m2 = AP.patchdist_fit(stack, shrinkage=0.25)
    assert m2["shrinkage_mean"] == pytest.approx(0.25, abs=1e-15)
    # n - 1 >= D の次元なら "none" は通る(Cholesky が通る = 正定値)
    m3 = AP.patchdist_fit(np.stack([_tex(rng, 32) for _ in range(40)]), groups=("intensity",),
                          scales=(1.0, 2.0), shrinkage="none")
    assert m3["shrinkage_mean"] == 0.0 and m3["dim"] == 2
    with pytest.raises(ValueError, match="no variation"):
        AP.patchdist_fit(np.ones((6, 32, 32)))


def test_global_pool_estimates_one_distribution_from_every_cell():
    rng = np.random.default_rng(12)
    stack = np.stack([_tex(rng, 32) for _ in range(4)])
    m = AP.patchdist_fit(stack, pool="global", groups=("gradient",), scales=(1.0, 2.0))
    assert m["pool"] == "global" and m["dim"] == 6
    assert np.array_equal(m["mean"][0, 0], m["mean"][3, 3])
    p = AP.patchdist_fit(stack, pool="position", groups=("gradient",), scales=(1.0, 2.0))
    assert not np.array_equal(p["mean"][0, 0], p["mean"][3, 3])
    with pytest.raises(ValueError, match="pool"):
        AP.patchdist_fit(stack, pool="everywhere")


# --------------------------------------------------------------------------- #
# 5. 記憶バンク                                                                  #
# --------------------------------------------------------------------------- #
def test_nearest_neighbour_distance_matches_scipy_cdist():
    cd = pytest.importorskip("scipy.spatial.distance").cdist
    rng = np.random.default_rng(13)
    bank = rng.standard_normal((300, 7))
    q = rng.standard_normal((50, 7))
    d = cd(q, bank)
    assert d.shape == (50, 300)
    assert np.allclose(AP._knn_dist(q, bank, 1), d.min(axis=1), atol=1e-9)
    assert np.allclose(AP._knn_dist(q, bank, 3), np.sort(d, axis=1)[:, :3].mean(axis=1), atol=1e-9)


def test_greedy_cover_is_within_twice_the_optimal_radius():
    rng = np.random.default_rng(14)
    x = rng.standard_normal((12, 3))
    d = np.sqrt(((x[:, None] - x[None]) ** 2).sum(-1))
    k = 3
    opt = min(float(d[:, list(c)].min(axis=1).max()) for c in itertools.combinations(range(12), k))
    for seed in (0, 1, 2, 3):
        sel, radius = AP._greedy_kcenter(x, k, seed, None)
        assert len(set(sel.tolist())) == k
        assert radius == pytest.approx(float(d[:, sel].min(axis=1).max()), abs=1e-12)
        assert radius <= 2.0 * opt + 1e-12


def test_coreset_radius_shrinks_with_the_fraction_and_vanishes_at_one():
    train = _world(6, 2, 1)[0]
    kw = dict(patch=8, stride=4, scales=(1.0, 2.0), groups=("gradient", "gabor"))
    ms = [AP.patchbank_fit(train, coreset=c, **kw) for c in (0.02, 0.1, 0.5, 1.0)]
    r = [m["covering_radius"] for m in ms]
    assert [m["n_memory"] for m in ms] == [math.ceil(c * ms[0]["n_total"]) for c in (0.02, 0.1, 0.5, 1.0)]
    assert ms[3]["n_memory"] == ms[3]["n_total"] == 6 * 225
    assert r[0] > r[1] > r[2] > 0.0
    assert r[3] == 0.0


def test_bank_seed_changes_the_cover_but_not_its_size():
    train = _world(4, 2, 2)[0]
    kw = dict(patch=8, stride=4, scales=(1.0, 2.0), groups=("gradient", "gabor"), coreset=0.1)
    a = AP.patchbank_fit(train, seed=0, **kw)
    b = AP.patchbank_fit(train, seed=0, **kw)
    c = AP.patchbank_fit(train, seed=5, **kw)
    assert a["bank"].shape == c["bank"].shape
    assert np.array_equal(a["bank"], b["bank"])
    assert not np.array_equal(a["bank"], c["bank"])


def _bar_world(rng, moved=False):
    yy, xx = np.mgrid[0:64, 0:64].astype(float)
    col = 44 if moved else 20
    img = 0.5 + 0.3 * (np.abs(xx - col) < 3)
    return ndi.gaussian_filter(img, 1.0) + 0.01 * rng.standard_normal(img.shape)


def test_position_aware_bank_sees_a_correct_pattern_in_the_wrong_place():
    rng = np.random.default_rng(15)
    train = np.stack([_bar_world(rng) for _ in range(8)])
    kw = dict(patch=8, stride=4, scales=(1.0, 2.0), groups=("gradient", "intensity"), coreset=1.0)
    free = AP.patchbank_fit(train, position_weight=0.0, **kw)
    aware = AP.patchbank_fit(train, position_weight=4.0, **kw)
    good = _bar_world(rng)
    bad = _bar_world(rng, moved=True)
    sf = [AP.patchbank_score(x, free)["image_score"] for x in (good, bad)]
    sa = [AP.patchbank_score(x, aware)["image_score"] for x in (good, bad)]
    assert sa[1] > 3.0 * sa[0]                       # 位置を見れば、動いた棒は良品の何倍も外れる
    assert sf[1] < 2.0 * sf[0]                       # 位置を見なければ、棒の欠片は記憶に在る


# --------------------------------------------------------------------------- #
# 6. 良品だけで学んだ検出器は無作為より桁で良い、枚数と順位、壊す探針                 #
# --------------------------------------------------------------------------- #
def _scores(train, tests, ms, labs):
    out = {}
    gl = AP.patchdist_fit(train, pool="global")
    ps = AP.patchdist_fit(train, pool="position")
    bk = AP.patchbank_fit(train, coreset=0.1)
    out["dist_global"] = _maps(AP.patchdist_score, gl, tests)
    out["dist_position"] = _maps(AP.patchdist_score, ps, tests)
    out["bank"] = _maps(AP.patchbank_score, bk, tests)
    return out


@pytest.fixture(scope="module")
def world20():
    train, tests, ms, labs = _world(20, 20, 3, amp=2.0)
    return train, tests, ms, labs, _scores(train, tests, ms, labs)


def test_good_only_training_beats_a_random_score_by_an_order_of_magnitude(world20):
    train, tests, ms, labs, maps = world20
    assert int(ms.any(axis=(1, 2)).sum()) == 10 and ms.shape == (20, 64, 64)
    rng = np.random.default_rng(99)
    rnd = [AE.anomaly_pixel_auroc(rng.random(ms.shape), ms)["auroc"] for _ in range(5)]
    gap_random = max(abs(a - 0.5) for a in rnd)
    assert gap_random < 0.02
    for name in ("dist_global", "bank"):
        au = AE.anomaly_pixel_auroc(maps[name], ms)["auroc"]
        assert au - 0.5 > 10.0 * gap_random, (name, au, gap_random)
        assert au > 0.85, (name, au)


def test_shifting_the_defect_mask_by_one_pixel_lowers_pro(world20):
    train, tests, ms, labs, maps = world20
    # ずらした距離が増えるほど PRO は単調に下がる(0, 1, 3, 6 画素)。1 画素の落ちは小さいが、符号は必ず負
    pro = [AE.anomaly_pro(maps["bank"], np.roll(ms, d, axis=2))["aupro"] for d in (0, 1, 3, 6)]
    assert len(pro) == 4
    assert pro[0] > 0.8
    assert pro[0] > pro[1] > pro[2] > pro[3], pro
    assert pro[3] < pro[0] - 0.05, pro


def test_labelling_normal_images_as_defective_breaks_the_ranking(world20):
    train, tests, ms, labs, maps = world20
    sc = maps["bank"].reshape(20, -1).max(axis=1)
    clean = AE.anomaly_image_auroc(sc, labs)["auroc"]
    wrong = labs.copy()
    swapped = np.nonzero(~labs)[0][:5]
    wrong[swapped] = True                                     # 正常 10 枚のうち 5 枚を欠陥扱い
    assert int(wrong.sum()) == 15 and int((~wrong).sum()) == 5
    broken = AE.anomaly_image_auroc(sc, wrong)["auroc"]
    # 組の数え直し: 本物の欠陥 10 と残りの正常 5、誤ラベル 5 と残りの正常 5 の AUROC の重み付き平均に一致する
    rest = np.nonzero(~wrong)[0]
    true_pos = np.nonzero(labs)[0]
    a_true = AE.anomaly_image_auroc(np.r_[sc[true_pos], sc[rest]], np.r_[np.ones(10), np.zeros(5)].astype(bool))["auroc"]
    a_swap = AE.anomaly_image_auroc(np.r_[sc[swapped], sc[rest]], np.r_[np.ones(5), np.zeros(5)].astype(bool))["auroc"]
    assert broken == pytest.approx((10 * a_true + 5 * a_swap) / 15.0, abs=1e-12)
    assert clean > 0.8
    assert broken < clean - 0.05, (clean, broken)


def test_ranking_of_the_scorers_is_stable_over_5_20_and_80_good_images():
    # 確率的なテクスチャでは、位置ごとの正規分布(標本が位置あたり n 個)は、全位置をまとめた正規分布と
    # 記憶バンクのどちらにも負ける。この順位が良品 5・20・80 枚のどれでも変わらない。
    order = {}
    for n in (5, 20, 80):
        train, tests, ms, labs = _world(n, 20, 4)
        m = _scores(train, tests, ms, labs)
        order[n] = {k: AE.anomaly_pro(v, ms)["aupro"] for k, v in m.items()}
    assert sorted(order) == [5, 20, 80]
    for n in (5, 20, 80):
        o = order[n]
        assert o["dist_position"] + 0.05 < o["dist_global"], (n, o)
        assert o["dist_position"] + 0.05 < o["bank"], (n, o)


def test_a_stack_contaminated_by_defects_hurts_the_gaussian_more_than_the_bank():
    rng = np.random.default_rng(21)
    train = np.stack([_tex(rng) for _ in range(20)])
    dirty = train.copy()
    for i in range(0, 20, 2):                                 # 10 枚に傷を混ぜる(良品群の汚れ)
        dirty[i], _ = _scratch(dirty[i], rng, 1.2)
    tests, ms, labs = _world(0, 16, 6)[1:]
    res = {}
    for tag, tr in (("clean", train), ("dirty", dirty)):
        res[tag] = AE.anomaly_pixel_auroc(_maps(AP.patchbank_score, AP.patchbank_fit(tr, coreset=0.1), tests), ms)["auroc"]
    assert res["clean"] > 0.85
    assert res["dirty"] > 0.5
    assert res["dirty"] <= res["clean"] + 0.02


# --------------------------------------------------------------------------- #
# 7. 拒否                                                                       #
# --------------------------------------------------------------------------- #
def test_refusals_are_value_errors_with_a_reason():
    rng = np.random.default_rng(31)
    stack = np.stack([_tex(rng, 32) for _ in range(4)])
    m = AP.patchdist_fit(stack, groups=("gradient",), scales=(1.0,))
    b = AP.patchbank_fit(stack, groups=("gradient",), scales=(1.0,), coreset=0.5)
    with pytest.raises(ValueError, match="does not match"):
        AP.patchdist_score(np.zeros((40, 40)), m)
    with pytest.raises(ValueError, match="does not match"):
        AP.patchbank_score(np.zeros((32, 32, 3)), b)
    with pytest.raises(ValueError, match="returned by patchdist_fit"):
        AP.patchdist_score(stack[0], b)
    with pytest.raises(ValueError, match="returned by patchbank_fit"):
        AP.patchbank_score(stack[0], m)
    with pytest.raises(ValueError, match="at least 2"):
        AP.patchdist_fit(stack[:1])
    with pytest.raises(ValueError, match="groups"):
        AP.patch_features(stack[0], groups=("deep",))
    with pytest.raises(ValueError, match="smaller than patch"):
        AP.patch_features(np.zeros((6, 6)), patch=8)
    with pytest.raises(ValueError, match="non-finite"):
        AP.patch_features(np.full((16, 16), np.nan))
    with pytest.raises(ValueError, match="k must"):
        AP.patchbank_score(stack[0], b, k=10 ** 6)
    with pytest.raises(ValueError, match="coreset"):
        AP.patchbank_fit(stack, coreset=0.0)
    with pytest.raises(ValueError, match="constant"):
        AP.patchbank_fit(np.stack([np.full((16, 16), 0.5)] * 3), groups=("intensity",), scales=(1.0,))
    with pytest.raises(ValueError, match="smooth"):
        AP.patchdist_score(stack[0], m, smooth=-1.0)
