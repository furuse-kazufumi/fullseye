# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Gates for hdrfusion.py — camera response, HDR merge, exposure fusion, dynamic range.

真値: 既知の放射輝度の場面を EMVA 1288 の線形モデル(+ 既知の γ の応答)で撮った露出の列。
推定した応答・放射輝度は真値と比べ、ダイナミックレンジは EMVA の閉形式
(sensorchar.emva_sensitivity_threshold / emva_dynamic_range、別の module)と比べる。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import hdrfusion as H  # noqa: E402
import sensorchar as SC  # noqa: E402

TS = [0.01, 0.04, 0.16, 0.64, 2.56]
ETA, K, OFF = 0.6, 0.1, 4.0
Z = np.arange(256)


def _scene():
    yy, xx = np.mgrid[0:128, 0:160]
    return 10.0 ** (math.log10(50.0) + 4.0 * xx / 159.0) * (1.0 + 0.2 * np.sin(yy / 5.0))


def _true_inverse(gamma):
    return (255.0 * (Z / 255.0) ** gamma - OFF) / (K * ETA)


def _g_residual(resp, gamma):
    Xt = _true_inverse(gamma)
    ok = (Xt > 50.0) & (Z <= 240)
    d = resp["g"][ok] - np.log(Xt[ok])
    return d - np.median(d)


# --------------------------------------------------------------------------- #
# 1. 応答関数
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("gamma", [1.0, 2.2])
@pytest.mark.parametrize("fn", [H.camera_response_debevec, H.camera_response_robertson])
def test_response_matches_the_true_inverse(fn, gamma):
    imgs = H.hdr_exposure_series_simulate(_scene(), TS, gamma=gamma, seed=3)
    d = _g_residual(fn(imgs, TS), gamma)
    # 実測(ln の残差の rms / 最大): Debevec γ=1 0.045 / 0.10、γ=2.2 0.090 / 0.15(滑らかさ λ=10 =
    # OpenCV の既定。λ=30 で 0.053 —— 暗い側の急な曲がりと雑音の兼ね合い)、Robertson γ=1 0.021 / 0.10、
    # γ=2.2 0.057 / 0.16(30 反復 = OpenCV の既定)。
    assert np.sqrt(np.mean(d * d)) < 0.10, np.sqrt(np.mean(d * d))
    assert np.max(np.abs(d)) < 0.20
    # 門に力があること: γ を取り違えた真値とは桁で外れる
    wrong = _g_residual(fn(imgs, TS), 1.0 if gamma != 1.0 else 2.2)
    assert np.sqrt(np.mean(wrong * wrong)) > 0.3


def test_noise_free_series_gives_a_tighter_response():
    rad = _scene()
    ex = [np.clip(np.rint(OFF + K * ETA * rad * t), 0, 255).astype(np.int64) for t in TS]
    for fn in (H.camera_response_debevec, H.camera_response_robertson):
        d = _g_residual(fn(ex, TS), 1.0)
        assert np.sqrt(np.mean(d * d)) < 0.02


def test_robertson_end_weights_are_zero():
    """飽和の段に重みが残ると w·t² で長い露出が支配し応答が ±0.7 波打つ(実測)。端は 0 で、雑音なしで 0.02 以内。"""
    rng = np.random.default_rng(0)
    rad = 10 ** rng.uniform(math.log10(50), math.log10(5e5), (128, 160))
    ex = [np.clip(np.rint(OFF + K * ETA * rad * t), 0, 255).astype(np.int64) for t in TS]
    d = _g_residual(H.camera_response_robertson(ex, TS), 1.0)
    assert np.max(np.abs(d)) < 0.05


# --------------------------------------------------------------------------- #
# 2. 合成
# --------------------------------------------------------------------------- #
def _mask(rad):
    dr = H.hdr_dynamic_range(TS, n_frames=200)
    return (rad > 10 * dr["L_min"]) & (rad < 0.5 * dr["L_sat"])


def test_linear_merge_is_unbiased_and_shot_noise_limited():
    rad = _scene()
    imgs = H.hdr_exposure_series_simulate(rad, TS, seed=5)
    E = H.hdr_merge(imgs, TS, response=H.camera_response_linear(256, OFF, K * ETA), weight="linear")
    m = _mask(rad)
    er = H.hdr_radiance_error(E, rad, mask=m, fit_scale=False)
    assert abs(float(np.median(E[m] / rad[m])) - 1.0) < 0.005
    assert er["rms_rel"] < 0.06
    # 予測: 光子数の和の相対標準偏差(飽和しない露出だけ)の二乗平均と 15 % 以内
    tt = np.asarray(TS)[:, None, None]
    unsat = (OFF + K * ETA * rad[None] * tt) < 250.0
    Tsum = np.sum(np.where(unsat, tt, 0.0), axis=0)
    n = unsat.sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):          # 全露出で飽和する画素は m の外
        sig = np.sqrt(ETA * rad * Tsum + n * (8.0 ** 2 + SC.SIGMA_Q2 / K ** 2)) / (ETA * rad * Tsum)
    pred = float(np.sqrt(np.mean(sig[m] ** 2)))
    assert er["rms_rel"] == pytest.approx(pred, rel=0.15)


def test_debevec_pipeline_radiance_error():
    rad = _scene()
    imgs = H.hdr_exposure_series_simulate(rad, TS, gamma=2.2, seed=3)
    resp = H.camera_response_debevec(imgs, TS)
    er = H.hdr_radiance_error(H.hdr_merge(imgs, TS, response=resp), rad, mask=_mask(rad))
    assert er["rms_rel"] < 0.2 and er["median_rel"] < 0.1


def test_merge_fills_pixels_saturated_everywhere_with_a_lower_bound():
    rad = np.full((8, 8), 1e9)
    imgs = H.hdr_exposure_series_simulate(rad, TS, seed=1)
    E = H.hdr_merge(imgs, TS, response=H.camera_response_linear(256, OFF, K * ETA), weight="linear")
    assert np.isfinite(E).all()
    assert np.all(E < rad)                                    # 下限であって真値ではない


# --------------------------------------------------------------------------- #
# 3. 露出融合
# --------------------------------------------------------------------------- #
def test_exposure_fusion_identities():
    rng = np.random.default_rng(1)
    a, b = rng.random((37, 53)), rng.random((37, 53))
    assert np.max(np.abs(H.exposure_fusion_mertens([a]) - a)) < 1e-12
    assert np.max(np.abs(H.exposure_fusion_mertens([a, a, a]) - a)) < 1e-12
    assert np.max(np.abs(H.exposure_fusion_mertens([a, b], 0, 0, 0) - 0.5 * (a + b))) < 1e-12
    c = rng.random((37, 53, 3))
    assert np.max(np.abs(H.exposure_fusion_mertens([c, c]) - c)) < 1e-12


def test_pyramid_expand_has_unit_gain_at_the_borders():
    """回帰(2026-11-03、図で発見): 拡大の補間が端でも重みの和 1(定数は定数のまま)。

    "reflect" の境界では 0 を挟んだ格子の偶奇がずれ、端の画素が 11/8 倍になっていた。
    """
    for shape in ((16, 16), (17, 23), (9, 4)):
        small = np.full(((shape[0] + 1) // 2, (shape[1] + 1) // 2), 0.7)
        up = H._expand(small, shape)
        assert np.max(np.abs(up - 0.7)) < 1e-12, shape


def test_exposure_fusion_prefers_well_exposed_pixels():
    rad = _scene()
    imgs = H.hdr_exposure_series_simulate(rad, TS, seed=2)
    f = H.exposure_fusion_mertens(imgs)
    # 融合はどの 1 枚より 0.5 に近い画素が多い(露出の良さの重みの効き目)
    dev = np.abs(f - 0.5).mean()
    assert len(imgs) == len(TS)
    assert all(dev < np.abs(np.asarray(im) - 0.5).mean() for im in imgs)


# --------------------------------------------------------------------------- #
# 4. Fullseye だけの層: シミュとダイナミックレンジ
# --------------------------------------------------------------------------- #
def test_simulated_sensor_has_the_emva_photon_transfer_slope():
    mu, va = [], []
    for v in (100.0, 500.0, 2000.0, 8000.0, 20000.0, 30000.0):
        a, b = H.hdr_exposure_series_simulate(np.full((64, 64), v), [0.1, 0.1], seed=int(v), as_float=False)
        a, b = a.astype(float), b.astype(float)
        mu.append(0.5 * (a.mean() + b.mean()))
        va.append(np.var(a - b) / 2.0)
    d0, d1 = H.hdr_exposure_series_simulate(np.zeros((64, 64)), [0.1, 0.1], seed=1, as_float=False)
    ptc = SC.emva_photon_transfer(np.array(mu), np.array(va), 0.5 * (d0.mean() + d1.mean()),
                                  np.var(d0.astype(float) - d1) / 2.0, 250.0)
    assert ptc["K"] == pytest.approx(K, rel=0.03)


def test_single_exposure_dynamic_range_is_the_emva_closed_form():
    d = H.hdr_dynamic_range([1.0], n_frames=2000)
    thr = SC.emva_sensitivity_threshold(ETA, 8.0, K)
    assert d["L_min_closed_form"] == pytest.approx(thr["mu_p_min"], rel=1e-12)
    clip = SC.emva_dynamic_range(d["L_clip_closed_form"], thr["mu_p_min"])
    assert 20 * math.log10(d["L_clip_closed_form"] / d["L_min_closed_form"]) == pytest.approx(clip["dB"], rel=1e-12)
    assert d["ratio_measured_to_closed_form"] == pytest.approx(1.0, abs=0.04)
    assert d["L_min"] == pytest.approx(d["L_min_closed_form"], rel=0.03)
    assert d["L_sat"] == pytest.approx(d["L_sat_closed_form"], rel=0.02)
    # 分散の最大は平均の打ち切り点より低い(EMVA の飽和の定義)
    assert d["L_sat"] < d["L_clip_closed_form"]


def test_multi_exposure_dynamic_range_measured_vs_closed_form():
    d1 = H.hdr_dynamic_range([1.0], n_frames=1000)
    d3 = H.hdr_dynamic_range([1.0, 4.0, 16.0], n_frames=1000)
    assert d3["ratio_measured_to_closed_form"] == pytest.approx(1.0, abs=0.03)
    # 上は最短の露出で決まり(同じ)、下は露出の和 21 倍 —— 暗雑音が √3 倍になる分だけ 21 倍に届かない
    assert d3["L_sat"] == pytest.approx(d1["L_sat"], rel=0.02)
    gain = d3["dr"] / d1["dr"]
    # 2 つの実測の比(どちらも閉形式と 4 % 以内)の比なので、許容はその合成
    assert gain == pytest.approx(d3["dr_closed_form"] / d1["dr_closed_form"], rel=0.08)
    assert gain < 21.0


# --------------------------------------------------------------------------- #
# 5. fail-closed
# --------------------------------------------------------------------------- #
def test_fail_closed():
    a = np.random.default_rng(0).random((8, 8))
    with pytest.raises(ValueError):
        H.camera_response_debevec([a, a], [1.0])
    with pytest.raises(ValueError):
        H.camera_response_debevec([a * 2, a], [1.0, 2.0])
    with pytest.raises(ValueError):
        H.hdr_merge([a, a], [1.0, 2.0], response={"kind": "other"})
    with pytest.raises(ValueError):
        H.exposure_fusion_mertens([a, np.ones((9, 9))])
    with pytest.raises(ValueError):
        H.hdr_exposure_series_simulate(-a, [1.0])
    with pytest.raises(ValueError):
        H.hdr_radiance_error(np.zeros((4, 4)), np.ones((4, 4)))
