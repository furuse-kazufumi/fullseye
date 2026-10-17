# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gratingspec(回折格子と分光器)の門: 閉形式・第 2 実装・公表の分光器・壊して確かめる探針・fail-closed。"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import gratingspec as GS  # noqa: E402
import mathops  # noqa: E402

# 公表の分光器 1: Feng ほか, Sensors 21(2):323 (2021), CC BY 4.0(表 1 と本文)
FENG = dict(groove_density_per_mm=900.0, wavelength_min_nm=670.0, wavelength_max_nm=1130.0, incidence_deg=45.0,
            collimator_f_mm=40.0, detector_length_mm=28.67, collimator_offaxis_deg=14.5, camera_f_mm=68.0)
# 公表の分光器 2: "Three Criteria of M-Type Spectrometers for Engineering", Sensors 25(8):2439 (2025), CC BY 4.0(表 1・3・7)
MTYPE = dict(groove_density_per_mm=1200.0, wavelength_min_nm=500.0, wavelength_max_nm=750.0, incidence_deg=9.0,
             collimator_f_mm=104.1667 / 2.0, detector_length_mm=28.672, collimator_offaxis_deg=6.5,
             camera_f_mm=148.3872 / 2.0)


# --------------------------------------------------------------------------- #
# 格子の式                                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("G,lam,a,m", [(1200, 550, 10, 1), (600, 900, 20, 2), (300, 400, 30, -1), (1800, 250, 5, 1)])
def test_grating_equation_and_dispersion_closed_forms(G, lam, a, m):
    g = GS.grating_dispersion(G, lam, a, m, focal_length_mm=150.0, illuminated_width_mm=40.0)
    d = 1e6 / G
    b = math.radians(g["beta_deg"])
    assert abs(m * lam - d * (math.sin(math.radians(a)) + math.sin(b))) < 1e-9
    # Palmer (2-13) と (2-14) は同じ量の 2 つの書き方
    assert abs(g["angular_dispersion_rad_per_nm"] - (math.sin(math.radians(a)) + math.sin(b)) / (lam * math.cos(b))) < 1e-15
    assert abs(g["reciprocal_linear_dispersion_nm_per_mm"] - d * math.cos(b) / (abs(m) * 150.0)) < 1e-12
    assert abs(g["resolving_power"] - abs(m) * 40.0e6 / d) < 1e-6
    assert g["resolving_power"] <= g["resolving_power_max"] + 1e-6                        # Palmer (2-23)
    assert abs(g["free_spectral_range_nm"] - lam / abs(m)) < 1e-12


def test_littrow_dispersion_is_two_tan_beta_over_lambda():
    G, lam = 1200.0, 600.0
    lit = math.degrees(math.asin(lam * G * 1e-6 / 2.0))
    g = GS.grating_dispersion(G, lam, lit, 1)
    assert abs(g["beta_deg"] - lit) < 1e-9 and abs(g["littrow_deg"] - lit) < 1e-9
    assert abs(g["angular_dispersion_rad_per_nm"] - 2.0 * math.tan(math.radians(lit)) / lam) < 1e-15
    assert abs(g["anamorphic_magnification"] - 1.0) < 1e-12                                 # Littrow で 1


def test_second_implementation_mathops_agrees_under_sign_mapping():
    """mathops.wave_grating_orders は d(sin_out − sin_in) = mλ。Palmer の α は sin_in = −sin α に写る。"""
    for G, lam, a in ((1200, 550, 10.0), (600, 700, -12.0), (900, 820, 45.0)):
        g = GS.grating_dispersion(G, lam, a, 1)
        r = mathops.wave_grating_orders(1000.0 / G, lam, -math.sin(math.radians(a)), orders=(1,))
        assert abs(float(r["angle_deg"][0]) - g["beta_deg"]) < 1e-9


def test_overlapping_orders_share_the_direction():
    g = GS.grating_dispersion(600, 800, 10, 1)
    assert (2, 400.0) in g["overlaps"]
    g2 = GS.grating_dispersion(600, 400, 10, 2)
    assert abs(g2["beta_deg"] - g["beta_deg"]) < 1e-9                                   # 2 次の 400 = 1 次の 800


def test_orders_list_holds_every_propagating_order():
    g = GS.grating_dispersion(300, 500, 0.0, 1)
    ms = [m for m, _ in g["orders"]]
    assert ms == list(range(-6, 7))                                                     # |m| < 2d/λ ⇒ 6.67、α = 0 なら |m| ≤ 6


# --------------------------------------------------------------------------- #
# Czerny–Turner と公表の分光器                                                   #
# --------------------------------------------------------------------------- #
def test_feng2021_shafer_angle_and_camera_focal_length():
    D = GS.czerny_turner_design(**FENG)
    assert abs(D["beta_center_deg"] - 5.906) < 1e-3                                    # 表 1: θ = 5.906°
    assert abs(D["shafer_offaxis_deg"] - 14.968) < 1e-3                                # 表 1: I4 = 14.968°
    assert abs(D["camera_f_linear_mm"] - 68.0) / 68.0 < 0.015                          # 式 (16) → r4 = 136 mm
    lo, hi = D["detector_coverage_mm"]
    assert hi - lo == pytest.approx(28.67, rel=0.03)


def test_mtype2025_slit_image_and_resolution():
    D = GS.czerny_turner_design(**MTYPE)
    B = GS.spectrometer_bandpass(D, 25.0, 14.0, 0.11, [500.0, 625.0, 750.0])
    pub_img = np.array([40.0, 43.0, 50.0])                                             # 表 7 の像の FWHM [µm]
    assert np.all(np.abs(B["slit_image_um"] - pub_img) / pub_img < 0.06)
    pub_res = np.array([0.391, 0.386, 0.385])                                          # 表 7 の分解能 [nm]
    assert len(B["regime"]) == 3
    assert np.all(np.abs(B["fwhm_nm"] - pub_res) / pub_res < 0.035)
    assert all(r == "slit" for r in B["regime"])


def test_slit_limited_bandpass_is_independent_of_wavelength():
    D = GS.czerny_turner_design(**MTYPE)
    B = GS.spectrometer_bandpass(D, 50.0, 0.0, 0.2, np.linspace(500, 750, 7))
    c = 50e-3 * D["groove_spacing_nm"] * math.cos(math.radians(9.0)) / (1 * D["collimator_f_mm"])
    assert np.allclose(B["slit_limited_nm"], c, rtol=0, atol=1e-12)
    # 像の幅 × 逆線分散 = 一定(焦点面でも平らな検出器でも)
    assert np.allclose(B["slit_image_um"] * B["reciprocal_dispersion_nm_per_mm"] * 1e-3, c, rtol=1e-12)
    assert np.allclose(B["slit_image_flat_um"] * B["reciprocal_dispersion_flat_nm_per_mm"] * 1e-3, c, rtol=1e-12)
    assert np.all(np.abs(B["fwhm_nm"] - c) / c < 0.02)                                # 回折は小さい(NA 0.2)


def test_rectangular_pupil_reaches_mN_as_slit_and_pixel_vanish():
    D = GS.czerny_turner_design(**MTYPE)
    B = GS.spectrometer_bandpass(D, 0.0, 0.0, 0.05, [625.0], pupil="rectangular")
    ref = GS.SINC2_FWHM * 625.0 / B["grating_resolving_power"]
    assert abs(B["fwhm_nm"][0] - ref) / ref < 5e-4
    assert abs(B["rayleigh_limit_nm"][0] - 625.0 / B["grating_resolving_power"]) < 1e-12
    assert B["regime"] == ["diffraction"]


def test_two_rectangles_give_the_larger_width_palmer_8_12():
    D = GS.czerny_turner_design(**MTYPE)
    for w, p in ((40.0, 10.0), (8.0, 30.0)):
        B = GS.spectrometer_bandpass(D, w, p, 0.4, [625.0])
        assert abs(B["fwhm_nm"][0] - B["palmer_bandpass_nm"][0]) / B["palmer_bandpass_nm"][0] < 0.02


def test_resolution_versus_throughput_trade():
    """スリットを広げると エタンデュ ∝ w だが、帯域の幅は回折の床より下がらない(Jacquinot の取引)。"""
    D = GS.czerny_turner_design(**MTYPE)
    ws = [2.0, 5.0, 10.0, 25.0, 50.0, 100.0]
    fw = [GS.spectrometer_bandpass(D, w, 0.0, 0.05, [625.0])["fwhm_nm"][0] for w in ws]
    et = [GS.spectrometer_bandpass(D, w, 0.0, 0.05, [625.0])["etendue_mm2sr"] for w in ws]
    assert np.all(np.diff(fw) > 0) and np.all(np.diff(et) > 0)
    assert et[-1] / et[0] == pytest.approx(50.0)
    floor = GS.spectrometer_bandpass(D, 0.0, 0.0, 0.05, [625.0])["fwhm_nm"][0]
    assert fw[0] > floor and fw[0] < 1.3 * floor                                        # 細いスリットは回折の床へ


# --------------------------------------------------------------------------- #
# smile と keystone                                                             #
# --------------------------------------------------------------------------- #
def test_smile_matches_the_conical_closed_form_and_bends_to_longer_wavelengths():
    D = GS.czerny_turner_design(**MTYPE)
    S = GS.spectrometer_slit_image(D, 2.0)
    assert np.all(S["smile_um"] > 0)                                                   # 長い波長の側へ(Palmer 7.2)
    assert np.all(np.abs(S["smile_um"] - S["smile_closed_um"]) / S["smile_closed_um"] < 2e-3)


def test_littrow_curvature_radius_is_f_over_two_tan_beta():
    lit = math.degrees(math.asin(625e-6 * 1200 / 2.0))
    D = GS.czerny_turner_design(1200.0, 600.0, 650.0, lit, 100.0, 10.0, 5.0, camera_f_mm=100.0)
    S = GS.spectrometer_slit_image(D, 1.0, [625.0])
    assert abs(S["curvature_radius_mm"][0] - 100.0 / (2.0 * math.tan(math.radians(lit)))) < 1e-9


def test_scalar_rule_probe_misses_the_smile():
    """壊した模型(面内の式を高さに関係なく使う)は smile を 0 にし、閉形式の門に落ちる。"""
    D = GS.czerny_turner_design(**MTYPE)
    S = GS.spectrometer_slit_image(D, 2.0, rule="scalar")
    assert np.max(np.abs(S["smile_um"])) < 1e-6
    assert not np.all(np.abs(S["smile_um"] - S["smile_closed_um"]) / S["smile_closed_um"] < 2e-3)


def test_keystone_closed_form_and_zero_at_centre():
    D = GS.czerny_turner_design(**MTYPE)
    S = GS.spectrometer_slit_image(D, 2.0, [500.0, 562.5, 625.0, 687.5, 750.0])
    assert abs(S["keystone_um"][2]) < 1e-9
    big = S["keystone_closed_um"] > 1.0
    assert np.count_nonzero(big) >= 2
    assert np.all(np.abs(S["keystone_um"][big] - S["keystone_closed_um"][big]) / S["keystone_closed_um"][big] < 0.03)


def test_anamorphic_trace_equals_closed_form():
    D = GS.czerny_turner_design(**MTYPE)
    S = GS.spectrometer_slit_image(D, 1.0)
    assert np.allclose(S["anamorphic_trace"], S["anamorphic_closed"], rtol=1e-6)


# --------------------------------------------------------------------------- #
# 検出器の読み                                                                  #
# --------------------------------------------------------------------------- #
def _lines(lines, lo=250.0, hi=800.0, step=0.01, width=0.004, base=0.0):
    lam = np.arange(lo, hi, step)
    y = np.full(lam.size, base)
    for l0, a in lines:
        y = y + a * np.exp(-0.5 * ((lam - l0) / width) ** 2)
    return np.column_stack([lam, y])


def _resolved(r, l1, l2):
    i1 = int(np.argmin(np.abs(r[:, 0] - l1)))
    i2 = int(np.argmin(np.abs(r[:, 0] - l2)))
    seg = r[min(i1, i2):max(i1, i2) + 1, 1]
    return float(seg.min()) < 0.8 * min(float(r[i1 - 2:i1 + 3, 1].max()), float(r[i2 - 2:i2 + 3, 1].max()))


def test_mercury_yellow_doublet_resolves_with_a_narrow_slit_only():
    D = GS.czerny_turner_design(**MTYPE)
    sp = _lines([(576.96, 1.0), (579.07, 1.0)], 560.0, 600.0)
    narrow = GS.spectrometer_spectrum(D, sp, 25.0, 14.0, 0.11, max_order_multiple=1)
    wide = GS.spectrometer_spectrum(D, sp, 400.0, 14.0, 0.11, max_order_multiple=1)
    assert _resolved(narrow, 576.96, 579.07)
    assert not _resolved(wide, 576.96, 579.07)
    pk = narrow[int(np.argmax(narrow[:, 1])), 0]
    px_nm = D["reciprocal_dispersion_nm_per_mm"][1] * 14e-3
    assert min(abs(pk - 576.96), abs(pk - 579.07)) < 1.5 * px_nm


def test_second_order_ghost_and_longpass_filter():
    D = GS.czerny_turner_design(**MTYPE)
    sp = _lines([(312.6, 1.0)], 250.0, 760.0, step=0.02, width=0.01)
    no_hi = GS.spectrometer_spectrum(D, sp, 25.0, 14.0, 0.11, max_order_multiple=1)
    ghost = GS.spectrometer_spectrum(D, sp, 25.0, 14.0, 0.11, max_order_multiple=3, higher_order_efficiency=0.3)
    filt = GS.spectrometer_spectrum(D, sp, 25.0, 14.0, 0.11, max_order_multiple=3, longpass_nm=400.0)
    assert np.max(no_hi[:, 1]) == 0.0
    pk = ghost[int(np.argmax(ghost[:, 1])), 0]
    assert abs(pk - 2 * 312.6) < 0.3                                                   # 2 次は 625.2 nm の画素へ
    assert np.max(filt[:, 1]) == 0.0


def test_continuum_flux_is_conserved_in_first_order():
    D = GS.czerny_turner_design(**MTYPE)
    sp = _lines([], 480.0, 770.0, step=0.02, base=1.0)
    r = GS.spectrometer_spectrum(D, sp, 25.0, 14.0, 0.11, max_order_multiple=1)
    mid = r[200:-200]
    px_nm = np.abs(np.gradient(r[:, 0]))[200:-200]
    assert np.allclose(mid[:, 1], px_nm, rtol=0.01)                                    # 連続光 1 → 画素の Δλ


# --------------------------------------------------------------------------- #
# fail-closed                                                                  #
# --------------------------------------------------------------------------- #
def test_fail_closed():
    with pytest.raises(ValueError, match="order 0"):
        GS.grating_dispersion(order=0)
    with pytest.raises(ValueError, match="does not propagate"):
        GS.grating_dispersion(2400, 900, 10, 1)
    for bad in ("1200", True, float("nan"), -5.0):
        with pytest.raises(ValueError):
            GS.grating_dispersion(bad)
    with pytest.raises(ValueError, match="must exceed"):
        GS.czerny_turner_design(wavelength_min_nm=700, wavelength_max_nm=600)
    with pytest.raises(ValueError):
        GS.spectrometer_bandpass({"kind": "other"})
    D = GS.czerny_turner_design(**MTYPE)
    with pytest.raises(ValueError, match="inside the design band"):
        GS.spectrometer_bandpass(D, wavelengths_nm=[450.0])
    with pytest.raises(ValueError, match="coarser"):
        GS.spectrometer_spectrum(D, _lines([], 480.0, 770.0, step=1.0, base=1.0))
    with pytest.raises(ValueError, match="negative"):
        GS.spectrometer_spectrum(D, np.column_stack([np.arange(480, 770, 0.02), -np.ones(14500)]))
    with pytest.raises(ValueError, match="rule"):
        GS.spectrometer_slit_image(D, rule="paraxial")
    with pytest.raises(ValueError, match="pupil"):
        GS.spectrometer_bandpass(D, pupil="square")
