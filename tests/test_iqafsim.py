# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""iqafsim の門(FSIM / FSIMc / GMSD / VIF 画素領域版)。

合成(常に): 恒等(FSIM = FSIMc = 1、GMSD = 0、VIF = 1)、雑音 σ で単調、FSIM / GMSD の対称と VIF の非対称、位相一致の利得不変(ε = 1e-12 で
厳密、既定 ε の残差は ε に比例)と値域、偶数核の 'same' の規約(2×2 平均 + 間引き = ブロック平均、scipy の 'same' とは別)、round(1.5) = 2 /
round(2.5) = 3、data_range の尺度、公表表(論文 Table 4/5 の 4 桁と readme の 3 桁が同じ答え)、第 2 実装の照合(backends_transform2 の
モノジェニック位相一致との相関、iqatid.rank_spearman で雑音 σ と指標の順位が −1 / +1)、fail-closed。
実データ(FULLSEYE_TID2013_DATA があるとき): 先頭 120 組(参照 I01 の 24 種 × 5 段)で作者値 FSIMc.txt / FSIM.txt / VIFP.txt と行ごと ≤ 1e-4、
反例(色画像の Y で FSIM を測ると FSIM.txt と合わない)、GMSD は MOS と負の相関。examples/poc_iqa_fsim_gmsd_vif.py の門を単体テストにしたもの。"""
from __future__ import annotations

import numpy as np
import pytest
from scipy.signal import convolve2d

import iqafsim as F
import iqatid as IQ

DATA = IQ.tid2013_root()
needs_data = pytest.mark.skipif(DATA is None, reason="FULLSEYE_TID2013_DATA (extracted TID2013) is not set")


def _synth(h=96, w=128, seed=0):
    """勾配 + 円 + 縞 + 弱い雑音(0–255)。乱数だけの画像は対称性の破れを隠すので構造を入れる。"""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    img = 60.0 + 100.0 * xx / w
    img += 80.0 * (((yy - h / 2) ** 2 + (xx - w / 2) ** 2) < (h / 4) ** 2)
    img += 30.0 * np.sin(2 * np.pi * yy / 12.0) * (xx > w * 0.7)
    img += rng.normal(0, 1.5, (h, w))
    return np.clip(img, 0, 255)


def _rgb(g):
    return np.stack([np.clip(g * 1.1, 0, 255), g, np.clip(g * 0.8 + 20, 0, 255)], axis=-1)


@pytest.fixture(scope="module")
def img():
    return _synth()


# ── 恒等・単調・対称 ──────────────────────────────────────────────────────────
def test_identity_fsim_one_gmsd_zero_vif_one(img):
    rgb = _rgb(img)
    r = F.fsim_pair(rgb, rgb)
    assert r["fsim"] == 1.0 and r["fsimc"] == 1.0 and r["f"] == 1
    assert F.fsim(img, img) == 1.0 and F.fsimc(rgb, rgb) == 1.0
    assert F.gmsd(img, img) == 0.0
    assert np.all(F.gmsd_map(img, img) == 1.0)
    assert abs(F.vifp(img, img) - 1.0) < 1e-9                      # 規約の 1e-10 正則化で 1 − 2e-11


def test_noise_makes_fsim_and_vif_fall_and_gmsd_rise_strictly(img):
    rng = np.random.default_rng(1)
    fs, gs, vs = [], [], []
    for s in (2.0, 5.0, 10.0, 20.0, 40.0):
        d = np.clip(img + rng.normal(0, s, img.shape), 0, 255)
        fs.append(F.fsim(img, d))
        gs.append(F.gmsd(img, d))
        vs.append(F.vifp(img, d))
    assert np.all(np.diff(fs) < 0) and np.all(np.diff(gs) > 0) and np.all(np.diff(vs) < 0)
    assert fs[0] > 0.97 and fs[-1] < 0.6 and gs[-1] > 0.2 and vs[-1] < 0.2
    # 順位相関で言い直す(iqatid の第 2 実装): σ が上がるほど悪い → FSIM / VIF は ρ = −1、GMSD は +1
    sig = [2.0, 5.0, 10.0, 20.0, 40.0]
    assert IQ.rank_spearman(sig, fs) == -1.0 and IQ.rank_spearman(sig, vs) == -1.0 and IQ.rank_spearman(sig, gs) == 1.0


def test_fsim_and_gmsd_are_symmetric_but_vif_is_not(img):
    d = np.clip(img + np.random.default_rng(2).normal(0, 10, img.shape), 0, 255)
    assert F.fsim(img, d) == F.fsim(d, img)
    assert F.gmsd(img, d) == F.gmsd(d, img)
    v_ab, v_ba = F.vifp(img, d), F.vifp(d, img)
    assert abs(v_ab - v_ba) > 0.05, (v_ab, v_ba)                   # 参照の情報量で割るので非対称(雑音の方を参照にすると小さく出る)
    assert v_ba < v_ab


def test_vif_exceeds_one_under_contrast_enhancement_and_gms_map_is_in_unit_interval(img):
    enh = np.clip((img - img.mean()) * 1.4 + img.mean(), 0, 255)
    assert F.vifp(img, enh) > 1.0                                  # 作者値の最大 1.1379(歪み 17 コントラスト変化)と同じ振る舞い
    q = F.gmsd_map(img, np.clip(img + 10 * np.random.default_rng(3).normal(size=img.shape), 0, 255))
    assert q.min() > 0.0 and q.max() <= 1.0 and q.shape == (48, 64)


def test_gray_input_gives_fsimc_equal_to_fsim(img):
    d = np.clip(img + np.random.default_rng(4).normal(0, 6, img.shape), 0, 255)
    r = F.fsim_pair(img, d)
    assert r["fsimc"] == r["fsim"] and 0.5 < r["fsim"] < 1.0
    rc = F.fsim_pair(_rgb(img), _rgb(d))
    assert rc["fsimc"] < rc["fsim"] < 1.0                           # 彩度の項は 1 以下の因子


# ── 位相一致 ────────────────────────────────────────────────────────────────────
def test_phase_congruency_is_gain_invariant_up_to_epsilon_and_in_unit_interval(img):
    pc = F.phase_congruency_pc(img)
    assert pc.shape == img.shape and pc.min() >= 0.0 and pc.max() <= 1.0 and pc.max() > 0.5
    e1, e2 = F.phase_congruency_pc(img, epsilon=1e-12), F.phase_congruency_pc(2.0 * img, epsilon=1e-12)
    assert np.abs(e1 - e2).max() < 1e-10
    d4 = np.abs(pc - F.phase_congruency_pc(2.0 * img)).max()
    d8 = np.abs(F.phase_congruency_pc(img, epsilon=1e-8) - F.phase_congruency_pc(2.0 * img, epsilon=1e-8)).max()
    assert 0.0 < d4 < 1e-4 and d8 < d4 * 1e-3                       # 残差は ε に比例(ε の置き場が原因で、他ではない)
    assert np.all(F.phase_congruency_pc(np.full((32, 32), 7.0)) == 0.0)   # 定数画像は 0(nan にしない)


def test_phase_congruency_agrees_with_the_monogenic_second_implementation():
    import backends_transform2 as BT
    g = _synth(192, 256)                                            # PoC と同じ大きさ(96×128 だと r = 0.59、縞の帯が相対的に太い)
    pc = F.phase_congruency_pc(g)
    mono = np.asarray(BT.tf_phase_congruency(g / 255.0, 0.0, 0.5), dtype=np.float64)
    r = float(np.corrcoef(pc.ravel(), mono.ravel())[0, 1])
    assert 0.6 < r < 0.95, r                                       # 同じ式ではない(方向つき log-Gabor vs Riesz)ので一致でなく相関; 1 に近すぎても怪しい


# ── 規約 ────────────────────────────────────────────────────────────────────────
def test_even_kernel_same_convolution_follows_the_reference_not_scipy():
    a = np.arange(48.0).reshape(6, 8)
    blk = a.reshape(3, 2, 4, 2).mean(axis=(1, 3))
    assert np.array_equal(F._average_downsample(a, 2), blk)
    k = np.full((2, 2), 0.25)
    assert not np.array_equal(F._conv2_same_ref(a, k), convolve2d(a, k, mode="same"))   # scipy は半画素ずれる(反例)
    assert np.array_equal(F._conv2_same_ref(a, np.ones((3, 3)) / 9.0), convolve2d(a, np.ones((3, 3)) / 9.0, mode="same"))   # 奇数核は同じ
    assert F._average_downsample(a, 1) is a


def test_downsample_factor_uses_round_half_away_from_zero():
    assert F._ref_round(384 / 256.0) == 2 and F._ref_round(256 / 256.0) == 1 and F._ref_round(767 / 256.0) == 3
    assert F._ref_round(2.5) == 3 and int(np.round(2.5)) == 2       # numpy の半偶数と違う所
    rgb = _rgb(_synth(300, 400))
    assert F.fsim_pair(rgb, rgb)["f"] == 1 and F.fsim_pair(rgb, rgb, downsample=False)["f"] == 1
    assert F.fsim_pair(_synth(384, 96), _synth(384, 96))["f"] == 1 and F.fsim_pair(_synth(384, 400), _synth(384, 400))["f"] == 2


def test_data_range_rescales_to_the_8_bit_scale(img):
    d = np.clip(img + np.random.default_rng(5).normal(0, 8, img.shape), 0, 255)
    assert F.fsim(img / 255.0, d / 255.0, data_range=1.0) == pytest.approx(F.fsim(img, d), abs=1e-12)
    assert F.gmsd(img / 255.0, d / 255.0, data_range=1.0) == pytest.approx(F.gmsd(img, d), abs=1e-12)
    assert F.vifp(img / 255.0, d / 255.0, data_range=1.0) == pytest.approx(F.vifp(img, d), abs=1e-12)
    assert F.gmsd(img / 255.0, d / 255.0) < F.gmsd(img, d)        # 尺度を宣言しないと c = 170 に対して勾配が小さすぎて別の答え


def test_published_tables_agree_between_paper_and_readme():
    pub = IQ.tid2013_published()
    for key in ("fsim", "fsimc", "vifp", "psnr", "ssim"):
        assert len(F.TID2013_PAPER_SROCC[key]) == 7 and len(F.TID2013_PAPER_KROCC[key]) == 7
        # readme の 3 桁は論文の 4 桁の丸め。PSNR は 0.6395 → readme 0.640 で、Python の round(0.6395, 3) は 2 進表現の都合で 0.639 になる
        # (丸めの境界)ので、本 PoC の 3 本は等号、残りは半桁以内で見る
        assert abs(F.TID2013_PAPER_SROCC[key][-1] - pub[key][0]) <= 0.00051 and abs(F.TID2013_PAPER_KROCC[key][-1] - pub[key][1]) <= 0.00051   # 0.640 − 0.6395 は 2 進で 5.0000000004e-4
    for key in ("fsim", "fsimc", "vifp"):
        assert round(F.TID2013_PAPER_SROCC[key][-1], 3) == pub[key][0]
        assert round(F.TID2013_PAPER_KROCC[key][-1], 3) == pub[key][1]
    assert F.TID2013_PAPER_SROCC["vif"][-1] > F.TID2013_PAPER_SROCC["vifp"][-1]    # steerable 版は別行(未実装)
    s, k, src = F.GMSD_TID2013_SECONDARY
    assert 0.80 < s < 0.81 and 0.63 < k < 0.64 and "arXiv" in src


# ── fail-closed ──────────────────────────────────────────────────────────────────
def test_fail_closed(img):
    with pytest.raises(ValueError):
        F.fsim(img, img[:-1])
    with pytest.raises(ValueError):
        F.gmsd(img, img[:, :-1])
    with pytest.raises(ValueError):
        F.phase_congruency_pc(np.zeros(5))
    with pytest.raises(ValueError):
        F.fsim(np.zeros((8, 8)), np.zeros((8, 8)))                 # 平坦: PC が 0 で 0/0
    with pytest.raises(ValueError):
        F.vifp(np.zeros((40, 40)), np.ones((40, 40)))               # 参照が平坦: 分母 0
    with pytest.raises(ValueError):
        F.vifp(_synth(20, 20), _synth(20, 20))                      # 最小スケールで窓より小さい
    with pytest.raises(ValueError):
        F.gmsd(img, img, c=0.0)
    with pytest.raises(ValueError):
        F.fsim(img, img, data_range=0.0)
    bad = img.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        F.gmsd(img, bad)
    with pytest.raises(ValueError):
        F.phase_congruency_pc(img, nscale=0)


# ── 実データ(TID2013)────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def tid():
    return IQ.tid2013_index(DATA)


@needs_data
def test_real_first_120_pairs_match_author_fsimc_fsim_vifp_to_four_digits(tid):
    n = 120                                                         # 参照 I01 の 24 種 × 5 段(全歪み種を 1 回ずつ踏む; 125 だと I02 の歪み 1 が混ざる)
    both = []
    rc = IQ.tid2013_evaluate(DATA, lambda a, b: both.append(F.fsim_pair(a, b)) or both[-1]["fsimc"], subset=n, luma="rgb", index=tid)
    rf = IQ.tid2013_evaluate(DATA, F.fsim, subset=n, luma="limited_u8", index=tid)
    rv = IQ.tid2013_evaluate(DATA, F.vifp, subset=n, luma="limited_u8", index=tid)
    for key, r in (("fsimc", rc), ("fsim", rf), ("vifp", rv)):
        au = IQ.tid2013_metric_values(DATA, key)[:n]
        c = IQ.tid2013_compare(r["values"], au, r["mos"], published=IQ.tid2013_published()[key])
        assert c["diff_max"] <= 1e-4, (key, c["diff_max"], r["names"][c["argmax"]])      # 作者値 4 桁 → 丸め半分 5e-5 + 余裕
    # 反例: 色画像の full-range Y から出した FSIM は FSIM.txt と合わない(作者の FSIM.txt は Y′ limited の灰色画像)
    fsim_from_rgb = np.array([b["fsim"] for b in both])
    assert np.abs(fsim_from_rgb - IQ.tid2013_metric_values(DATA, "fsim")[:n]).max() > 1e-3


@needs_data
def test_real_gmsd_is_finite_and_anticorrelated_with_mos(tid):
    rg = IQ.tid2013_evaluate(DATA, F.gmsd, subset=120, luma="rgb", index=tid)
    assert np.all(np.isfinite(rg["values"])) and rg["values"].min() >= 0.0 and rg["values"].max() < 0.5
    assert rg["srocc"] < -0.7 and rg["krocc"] < -0.5               # lower is better → MOS との順位相関は負
