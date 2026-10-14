# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""moirealign の門: 拡大率の閉形式、雑音の下限、差動で消える共通の誤差、折り返し、Talbot 長、fail-closed。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import moirealign as MA

PM, PW, PX = 2.0, 2.04, 0.5
P_PX = PM * PW / (PW - PM) / PX


def _read(img, ref, layout="single", **kw):
    return MA.moire_mark_read(img, ref, PX, PM, PW, layout, **kw)


def test_magnification_closed_form_and_moving_grating():
    w = MA.moire_magnification(PM, PW, "wafer")
    m = MA.moire_magnification(PM, PW, "mask")
    assert abs(w["moire_period_um"] - 102.0) < 1e-9
    assert abs(w["magnification"] - 50.0) < 1e-9 and abs(m["magnification"] - 51.0) < 1e-9
    assert abs(w["capture_range_differential_um"] - PM * PW / (PM + PW)) < 1e-12
    for mv, M in (("wafer", 50.0), ("mask", 51.0)):
        a = MA.moire_phase(MA.moire_overlay_image(moving=mv), P_PX)
        b = MA.moire_phase(MA.moire_overlay_image(shift_nm=100.0, moving=mv), P_PX)
        s = MA.moire_phase_to_shift(b["phase_rad"], a["phase_rad"], PM, PW, mv)
        assert abs(s["shift_nm"] - 100.0) < 0.01
        assert abs(abs(s["fringe_shift_um"]) / 0.1 - M) < 0.01
    tw = MA.moire_magnification(PM, PW, twist_mrad=5.0)
    assert tw["moire_period_um"] < w["moire_period_um"] and abs(tw["fringe_angle_deg"]) > 10.0


def test_noise_free_reads_and_fft_method_agree():
    ref = MA.moire_overlay_image()
    img = MA.moire_overlay_image(shift_nm=37.0)
    assert abs(_read(img, ref)["shift_x_nm"] - 37.0) < 0.01
    lk = MA.moire_phase(img, P_PX)
    ft = MA.moire_phase(img, P_PX, method="fft")
    assert abs(math.remainder(lk["phase_rad"] - ft["phase_rad"], 2 * math.pi)) < 1e-3
    assert abs(ft["period_fit_px"] / P_PX - 1) < 1e-3
    est = MA.moire_phase(img)
    assert est["period_estimated"] and abs(est["period_px"] / P_PX - 1) < 1e-3


def test_monte_carlo_matches_crlb():
    errs = []
    for k in range(24):
        ref = MA.moire_overlay_image(noise_sigma=0.01, seed=k)
        img = MA.moire_overlay_image(shift_nm=5.0, noise_sigma=0.01, seed=100 + k)
        errs.append(_read(img, ref)["shift_x_nm"] - 5.0)
    amp = MA.moire_phase(MA.moire_overlay_image(), P_PX)["amplitude"]
    lb = MA.moire_phase_crlb(0.01, amp, 256, 1024, PM, PW)
    ratio = float(np.std(errs, ddof=1)) / lb["shift_std_nm"]
    assert 0.6 < ratio < 1.5
    assert abs(lb["window_factor"] - 1.5) < 0.01
    assert MA.moire_phase_crlb(0.01, amp, 256, 1024, PM, PW, window="none")["window_factor"] == 1.0


def test_differential_cancels_common_drift_and_quad_reads_xy():
    ref = MA.moire_overlay_image(layout="differential")
    r = _read(MA.moire_overlay_image(layout="differential", shift_nm=25.0, drift_nm=300.0), ref, "differential")
    assert abs(r["single_x_nm"] - 25.0 + 6.0) < 0.1               # 単一の対は 300/M = 6 nm 狂う
    assert abs(r["shift_x_nm"] - 25.0) < 0.01 and abs(r["drift_x_nm"] - 300.0) < 0.5
    d = MA.moire_differential_shift(0.3, -0.3, 0.0, 0.0, PM, PW)
    assert abs(d["ambiguity_nm"] - PM * PW / (PM + PW) * 1e3) < 1e-9
    q0 = MA.moire_overlay_image((1024, 1024), layout="quad")
    q1 = MA.moire_overlay_image((1024, 1024), layout="quad", shift_nm=(12.0, -25.0), drift_nm=(200.0, -100.0))
    q = _read(q1, q0, "quad")
    assert abs(q["shift_x_nm"] - 12.0) < 0.01 and abs(q["shift_y_nm"] + 25.0) < 0.01


def test_wrap_ambiguity_and_absolute_order():
    ref = MA.moire_overlay_image()
    a = _read(MA.moire_overlay_image(shift_nm=300.0), ref)["shift_x_nm"]
    b = _read(MA.moire_overlay_image(shift_nm=300.0 + PW * 1e3), ref)["shift_x_nm"]
    assert abs(a - b) < 1e-3
    pa = MA.moire_phase(ref, P_PX)["phase_rad"]
    pb = MA.moire_phase(MA.moire_overlay_image(shift_nm=2340.0), P_PX)["phase_rad"]
    s = MA.moire_phase_to_shift(pb, pa, PM, PW, coarse_shift_nm=2300.0)
    assert s["order"] == 1 and abs(s["shift_nm"] - 2340.0) < 0.01


def test_talbot_gap_returns_and_flips():
    zt = 2 * PM ** 2 / 0.55
    assert abs(MA.moire_talbot_gap(PM, 0.55, zt)["contrast_ratio"] - 1.0) < 0.01
    half = MA.moire_talbot_gap(PM, 0.55, zt / 2)
    assert half["contrast_ratio"] < -0.99 and abs(half["phase_rad"] - math.pi) < 1e-9
    assert MA.moire_talbot_gap(PM, 0.55, 0.0)["contrast_ratio"] == 1.0
    amp0 = MA.moire_phase(MA.moire_overlay_image(), P_PX)["amplitude"]
    ampg = MA.moire_phase(MA.moire_overlay_image(gap_um=4.0, wavelength_um=0.55), P_PX)["amplitude"]
    assert abs(ampg / amp0 / abs(MA.moire_talbot_gap(PM, 0.55, 4.0)["contrast_ratio"]) - 1) < 0.02


def test_direct_image_of_unresolved_grating_is_flat():
    img = MA.moire_overlay_image(with_mask=False)
    assert img.std() < 1e-4 and abs(img.mean() - 0.5) < 1e-6


def test_fail_closed():
    with pytest.raises(ValueError, match="no beat"):
        MA.moire_magnification(2.0, 2.0)
    with pytest.raises(ValueError, match="Nyquist"):
        MA.moire_overlay_image(pixel_um=5.0, p_mask_um=2.0, p_wafer_um=3.0, blur_sigma_um=3.0)
    with pytest.raises(ValueError, match="less than one moiré period"):
        MA.moire_overlay_image(shape=(64, 64))
    with pytest.raises(ValueError, match="alias"):
        MA.moire_overlay_image(pixel_um=1.5, blur_sigma_um=0.2)
    with pytest.raises(ValueError, match="Nyquist"):
        MA.moire_phase(np.zeros((8, 64)), 1.5)
    with pytest.raises(ValueError, match="fringe periods"):
        MA.moire_phase(MA.moire_overlay_image(), 5000.0)
    with pytest.raises(ValueError, match="NaN"):
        MA.moire_phase(np.full((8, 64), np.nan), 8.0)
    with pytest.raises(ValueError, match="moving"):
        MA.moire_phase_to_shift(0.0, 0.0, moving="stage")
    with pytest.raises(ValueError, match="square"):
        MA.moire_overlay_image(profile="sine", gap_um=5.0, wavelength_um=0.55)
    with pytest.raises(ValueError, match="wavelength_um"):
        MA.moire_overlay_image(gap_um=5.0)
    with pytest.raises(ValueError, match="not str"):
        MA.moire_magnification("2.0", 2.04)
    with pytest.raises(ValueError, match="not bool"):
        MA.moire_phase_crlb(True)
    with pytest.raises(ValueError, match="wavelength"):
        MA.moire_talbot_gap(0.4, 0.55, 1.0)
    with pytest.raises(ValueError, match="same shape"):
        MA.moire_mark_read(np.zeros((8, 8)), np.zeros((8, 9)))
    with pytest.raises(ValueError):
        MA.moire_phase_crlb(-1.0)
