# -*- coding: utf-8 -*-
"""linescan(TDI ラインスキャンとラインスキャン用レンズ、2026-10-15)の門。

閉形式に対して: EMVA 1288 の式 21 を段数倍した SNR(デジタル加算は厳密に √N)、一様な掃引の |sinc| MTF、
瞳収差の無い系の cos⁴ 則、照度の 3 因子分解(cos⁴ × 瞳 × 歪曲)が恒等式であること。
撮像に対して: 完全同期なら 1 標本で厳密、ε の掃引が閉形式に合う、エンコーダで速度誤差が消える、fail-closed。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import linescan as LS  # noqa: E402
import raytrace as RT  # noqa: E402
import sensorchar as SC  # noqa: E402


# --------------------------------------------------------------------------- #
# tdi_snr                                                                      #
# --------------------------------------------------------------------------- #
def test_tdi_snr_digital_is_exactly_sqrt_n():
    r = LS.tdi_snr(20.0, [1, 4, 16, 64], 0.6, 12.0, 0.25, architecture="digital")
    np.testing.assert_allclose(r["gain"], np.sqrt([1, 4, 16, 64]), rtol=1e-12)


def test_tdi_snr_charge_equals_emva_eq21_with_n_times_exposure():
    r = LS.tdi_snr(20.0, [1, 8, 64], 0.6, 12.0, 0.25)
    ref = [SC.emva_snr_curve([n * 20.0], 0.6, 12.0, 0.25)[0, 1] for n in (1, 8, 64)]
    np.testing.assert_allclose(r["snr"], ref, rtol=1e-12)
    assert r["gain"][-1] > 8.0                           # 暗いと電荷加算は √N を超える
    # 明るいと √N に近づく(ショット雑音律)
    b = LS.tdi_snr(1e6, [1, 64], 0.6, 12.0, 0.25)
    assert abs(b["gain"][1] / 8.0 - 1.0) < 1e-3


@pytest.mark.parametrize("kw", [dict(stages=0), dict(stages=2.5), dict(eta=1.5), dict(K=0.0),
                                dict(architecture="ccd"), dict(photons_per_stage=-1.0)])
def test_tdi_snr_refuses(kw):
    with pytest.raises(ValueError):
        LS.tdi_snr(**kw)


# --------------------------------------------------------------------------- #
# tdi_sync_mtf                                                                 #
# --------------------------------------------------------------------------- #
def test_sync_mtf_closed_form_and_zero():
    m = LS.tdi_sync_mtf([0.0, 0.25, 1.0 / 1.28], 64, 0.02)
    assert m["smear_scan_px"] == pytest.approx(1.28)
    assert m["mtf_scan"][0] == 1.0
    assert m["mtf_scan"][1] == pytest.approx(abs(math.sin(math.pi * 0.32) / (math.pi * 0.32)))
    assert m["mtf_scan"][2] < 1e-12                      # 最初の零 = 1/L
    assert np.all(m["mtf_cross"] == 1.0)


def test_sync_mtf_yaw_cross_blur_is_n_sin_theta():
    m = LS.tdi_sync_mtf([0.2], 64, 0.0, yaw_deg=2.0)
    assert m["smear_cross_px"] == pytest.approx(64 * math.sin(math.radians(2.0)))
    assert m["slip_scan"] == pytest.approx(1.0 - math.cos(math.radians(2.0)))


@pytest.mark.parametrize("kw", [dict(sync_error=0.9), dict(yaw_deg=45.0), dict(frequency_cyc_px=[-0.1]),
                                dict(frequency_cyc_px=[np.nan]), dict(stages=0)])
def test_sync_mtf_refuses(kw):
    with pytest.raises(ValueError):
        LS.tdi_sync_mtf(**kw)


# --------------------------------------------------------------------------- #
# linescan_acquire                                                             #
# --------------------------------------------------------------------------- #
def _sine_web(f, os_=5, h=420, w=24):
    y = np.arange(h * os_, dtype=np.float64)[:, None]
    return np.repeat(0.5 + 0.3 * np.cos(2 * np.pi * f / os_ * y), w * os_, axis=1)


def _amp(img, pos, f):
    A = np.stack([np.cos(2 * np.pi * f * pos), np.sin(2 * np.pi * f * pos), np.ones_like(pos)], 1)
    coef, *_ = np.linalg.lstsq(A, img, rcond=None)
    return float(np.mean(np.hypot(coef[0], coef[1]) / coef[2]))


def test_perfect_sync_is_one_sample_and_exact():
    web = np.random.default_rng(0).uniform(0.2, 0.8, (120, 40))
    r = LS.linescan_acquire(web, stages=16, photons_per_stage=100.0, noise=False, lines=60, width=30)
    assert r["samples"] == 1
    rows = np.round(r["line_rows"]).astype(int)
    cols = int(round(r["col0"])) + np.arange(30)
    np.testing.assert_allclose(r["mean_e"], 16 * 0.6 * 100.0 * web[np.ix_(rows, cols)], rtol=1e-10)


@pytest.mark.parametrize("eps,f", [(0.02, 0.25), (0.04, 0.2), (0.01, 0.4)])
def test_sync_error_matches_sinc(eps, f):
    web = _sine_web(f)
    kw = dict(stages=64, noise=False, lines=200, samples_per_px=8.0, oversample=5)
    r0 = LS.linescan_acquire(web, **kw)
    r1 = LS.linescan_acquire(web, sync_error=eps, **kw)
    m = _amp(r1["mean_e"], r1["line_rows"], f / 5) / _amp(r0["mean_e"], r0["line_rows"], f / 5)
    assert m == pytest.approx(float(LS.tdi_sync_mtf([f], 64, eps)["mtf_scan"][0]), abs=0.006)


def test_encoder_removes_speed_error_but_not_yaw():
    web = _sine_web(0.25)
    ripple = 0.03 * np.sin(np.arange(400) / 20.0)
    kw = dict(stages=32, noise=False, lines=200, samples_per_px=8.0, oversample=5)
    en = LS.linescan_acquire(web, encoder=True, sync_error=ripple, **kw)
    assert np.std(np.diff(en["line_rows"])) < 1e-9
    assert en["smear_scan_px"] == 0.0
    yw = LS.linescan_acquire(web, encoder=True, yaw_deg=1.0, **kw)
    assert yw["smear_cross_px"] == pytest.approx(32 * math.sin(math.radians(1.0)))


def test_noise_matches_eq21_charge_and_digital():
    flat = np.full((200, 120), 0.5)
    for arch in ("charge", "digital"):
        kw = dict(stages=16, photons_per_stage=40.0, eta=0.6, sigma_d=12.0, K=0.25, architecture=arch, lines=100)
        a = LS.linescan_acquire(flat, seed=1, **kw)["image"]
        b = LS.linescan_acquire(flat, seed=2, **kw)["image"]
        st = SC.emva_pair_statistics(a, b)
        snr = st["mu"] / math.sqrt(st["var_temporal"])
        ref = LS.tdi_snr(20.0, [16], 0.6, 12.0, 0.25, architecture=arch)["snr"][0]
        assert snr == pytest.approx(ref, rel=0.04)


@pytest.mark.parametrize("kw", [dict(web=np.full((40, 40), 1.5)), dict(web=np.full((40, 40), np.nan)),
                                dict(web=np.zeros(40)), dict(stages=0), dict(sync_error=0.7),
                                dict(order=2), dict(oversample=2), dict(architecture="x"),
                                dict(sync_error=np.zeros(5)), dict(lines=10_000)])
def test_acquire_refuses(kw):
    args = dict(web=np.full((160, 60), 0.5))
    args.update(kw)
    with pytest.raises(ValueError):
        LS.linescan_acquire(**args)


def test_acquire_refuses_leaving_the_web():
    with pytest.raises(ValueError, match="leaves the web"):
        LS.linescan_acquire(np.full((160, 60), 0.5), yaw_deg=25.0, stages=64, lines=40)


# --------------------------------------------------------------------------- #
# lens_field_profile / columns / example                                       #
# --------------------------------------------------------------------------- #
def test_flux_follows_cos4_without_pupil_aberration():
    pin = RT.lens_system([{"R": float("inf"), "t": 0.5, "n": 1.0, "ap": 1.0},
                          {"R": 51.68, "t": 5.0, "n": "N-BK7"}, {"R": float("inf"), "t": None, "n": 1.0}],
                         stop=0, object_mm=300.0)
    p = LS.lens_field_profile(pin, [0.0, 10.0, 20.0, 30.0])
    np.testing.assert_allclose(p["flux_ratio"], p["cos4"], atol=0.01)
    assert p["cos4"][-1] < 0.95                          # 探針が素通しでない(角が付いている)


def test_illumination_factorisation_is_exact():
    p = LS.lens_field_profile()
    ok = p["covered"]
    np.testing.assert_allclose(p["relative_illumination"][ok],
                               (p["cos4"] * p["pupil_factor"] * p["area_gain"])[ok], rtol=1e-12)
    assert p["relative_illumination"][-1] > 0.9


def test_cmount_model_goes_dark_at_the_end_of_a_long_sensor():
    p = LS.lens_field_profile(LS.linescan_lens_example("cmount"), [0.0, 5.5, 28.672])
    assert p["covered"][1] and not p["covered"][2]
    assert p["relative_illumination"][2] == 0.0
    c = LS.linescan_lens_columns(p, 8192, 7.0)
    # 表は 3 点だけなので端の列(像高 28.6685 mm)は 5.5 → 28.672 mm の線形補間で 0 に近い値
    assert c["relative_illumination"][0] < 0.01 and c["relative_illumination"][4096] == pytest.approx(1.0, abs=1e-3)


def test_lens_profile_refuses():
    with pytest.raises(ValueError):
        LS.lens_field_profile(RT.example_system("doublet"))          # 無限遠の物体
    with pytest.raises(ValueError):
        LS.lens_field_profile(image_heights_mm=[-1.0])
    with pytest.raises(ValueError):
        LS.linescan_lens_example("fisheye")
    p = LS.lens_field_profile(None, [0.0, 10.0])
    with pytest.raises(ValueError):
        LS.linescan_lens_columns(p, 8192, 7.0)                      # センサが表の外まで届く
    with pytest.raises(ValueError):
        LS.linescan_acquire(np.full((160, 60), 0.5), lens={"relative_illumination": np.ones(3),
                                                           "blur_sigma_px": np.zeros((3, 2))})
