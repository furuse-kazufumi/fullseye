# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""itof(間接 ToF、連続波・位相方式)の門: 閉形式・既存 op(lighttransport / residue)との一致・fail-closed。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import residue  # noqa: E402
import itof as T
import lighttransport as LT
import opsoptics

C = T.C_LIGHT


def _wrap(x):
    return np.mod(x + np.pi, 2 * np.pi) - np.pi


def test_noise_free_phase_amplitude_offset_are_exact():
    d = np.linspace(0.3, 7.0, 64).reshape(8, 8)
    raw = T.itof_capture(d, frequencies_hz=(20e6,), signal_electrons=2000.0, demod_contrast=0.5, noise=False)
    pa = T.itof_phase_amplitude(raw)
    U = C / (2 * 20e6)
    assert np.abs(_wrap((pa["wrapped_depth"][0] - np.mod(d, U)) / U * 2 * np.pi)).max() < 1e-12
    assert np.allclose(pa["amplitude"], 0.5 * 2000 / 4) and np.allclose(pa["offset"], 2000 / 4)
    assert np.allclose(pa["ambiguity_range"], U)


def test_four_step_closed_form_atan2():
    # 4 段: φ = atan2(m1 − m3, m0 − m2)、A = ½√(...)、B = Σ/4(θ_k = +kπ/2 の約束)
    m = np.array([7.0, 9.0, 3.0, 1.0])
    pa = T.itof_phase_amplitude(m.reshape(1, 4, 1))
    assert math.isclose(pa["phase"][0, 0], math.atan2(9 - 1, 7 - 3), abs_tol=1e-12)
    assert math.isclose(pa["amplitude"][0, 0], 0.5 * math.hypot(8, 4), abs_tol=1e-12)
    assert math.isclose(pa["offset"][0, 0], 5.0, abs_tol=1e-12)


def test_arbitrary_known_steps_are_solved_by_least_squares():
    th = np.array([0.0, -2.094395, -4.18879])            # e^{−iθ} の約束の 3 段
    phi = 1.1
    m = 50.0 + 20.0 * np.cos(phi - th)
    pa = T.itof_phase_amplitude(m.reshape(1, 3, 1), phase_offsets_rad=th)
    assert abs(pa["phase"][0, 0] - phi) < 1e-9 and abs(pa["amplitude"][0, 0] - 20.0) < 1e-9


def test_noise_matches_closed_form_and_lange():
    wall = np.full((160, 160), 2.0)
    raw = T.itof_capture(wall, frequencies_hz=(20e6,), signal_electrons=8000.0, demod_contrast=0.5, read_noise_e=10.0, seed=1)
    meas = np.std(T.itof_phase_amplitude(raw)["wrapped_depth"])
    nb = T.itof_noise_budget(20e6, 8000.0, 0.5, 0.0, 10.0)
    assert abs(meas / nb["depth_sigma"] - 1) < 0.04
    # Lange & Seitz: ΔL = (L/√8)·√B/(2 A_L)、A_L = 積分前の振幅 = π/2 × 標本の振幅
    nb0 = T.itof_noise_budget(20e6, 8000.0, 0.5, 0.0, 0.0)
    L = C / (2 * 20e6)
    lange = L / math.sqrt(8) * math.sqrt(nb0["offset"]) / (2 * (math.pi / 2) * nb0["amplitude"])
    assert math.isclose(lange, nb0["depth_sigma"], rel_tol=1e-12)


def test_ambient_only_raises_offset():
    a = T.itof_noise_budget(20e6, 4000.0, 0.5, 0.0)
    b = T.itof_noise_budget(20e6, 4000.0, 0.5, 16000.0)
    assert a["amplitude"] == b["amplitude"] and math.isclose(b["depth_sigma"] / a["depth_sigma"], math.sqrt(5), rel_tol=1e-12)


def test_multifreq_unwrap_exact_and_unambiguous_range():
    d = np.random.default_rng(0).uniform(0.2, 18.5, (40, 40))
    f = (16e6, 80e6, 120e6)
    pa = T.itof_phase_amplitude(T.itof_capture(d, frequencies_hz=f, noise=False))
    for meth in ("ml", "crt"):
        un = T.itof_unwrap_multifreq(pa, method=meth)
        assert np.abs(un["depth"] - d).max() < 1e-9
        assert math.isclose(un["unambiguous_range"], C / (2 * 8e6), rel_tol=1e-12)
    two = T.itof_phase_amplitude(T.itof_capture(np.clip(d, 0.2, 7.3), frequencies_hz=(80e6, 100e6), noise=False))
    assert np.abs(T.itof_unwrap_multifreq(two, method="beat")["depth"] - np.clip(d, 0.2, 7.3)).max() < 1e-9


def test_beyond_unambiguous_range_folds():
    d = np.full((4, 4), 9.0)                               # 80/100/120 MHz の非曖昧距離は 7.495 m
    pa = T.itof_phase_amplitude(T.itof_capture(d, frequencies_hz=(80e6, 100e6, 120e6), noise=False))
    un = T.itof_unwrap_multifreq(pa)
    assert np.allclose(un["depth"], 9.0 - C / (2 * 20e6))


def test_residue_crt_matches_ml_with_the_wang_xia_anchor():
    """2026-10-18 統合: residue_crt が錨を Wang–Xia(分散が最小の帯、同分散なら式 (58))で選ぶようになり、
    位相雑音が帯ごとに同じ iToF でも最尤と同等になった(以前は最も長い周期を錨にして 2 倍以上誤った)。
    保証の外の画素では黙らずに ResidueBoundWarning を出す。"""
    rng = np.random.default_rng(1)
    d = rng.uniform(0.3, 18.4, (150, 150))
    f = (16e6, 80e6, 120e6)
    pa = T.itof_phase_amplitude(T.itof_capture(d, frequencies_hz=f, signal_electrons=300.0, read_noise_e=10.0, seed=2))
    jml = np.mean(np.abs(T.itof_unwrap_multifreq(pa, method="ml")["depth"] - d) > 0.3)
    with pytest.warns(residue.ResidueBoundWarning):
        jcrt = np.mean(np.abs(T.itof_unwrap_multifreq(pa, method="crt")["depth"] - d) > 0.3)
    sig = float(np.median(pa["phase_sigma"]))
    er = T.itof_unwrap_error_rate(f, sig)
    assert abs(jcrt - jml) <= 0.1 * jml + 5.0 / d.size, (jcrt, jml)
    assert 0.5 * er["nearest_term"] <= jml <= 1.3 * er["union_bound"]


def test_error_rate_closed_quantities():
    er = T.itof_unwrap_error_rate((80e6, 100e6, 120e6), 0.05)
    assert er["integers"].tolist() == [4, 5, 6]
    assert math.isclose(er["unambiguous_range"], C / (2 * 20e6), rel_tol=1e-12)
    assert math.isclose(er["gamma"], er["unambiguous_range"] / 60, rel_tol=1e-12)
    small = T.itof_unwrap_error_rate((80e6, 100e6, 120e6), 0.5)
    assert small["union_bound"] > er["union_bound"]


def test_two_path_single_frequency_matches_lighttransport():
    one = np.ones((1, 1))
    raw = T.itof_capture(one * 1.3, one * 0.35, frequencies_hz=(20e6,), paths_depth=(one * 0.95)[None],
                         paths_amplitude=(one * 0.10)[None], noise=False)
    got = T.itof_phase_amplitude(raw)["wrapped_depth"][0, 0, 0]
    ref = LT.tof_multipath_phase(np.array([0.35, 0.10]), np.array([2.6, 1.9]), 20e6)["depth"]
    assert abs(got - ref) < 1e-12


def test_corner_paths_match_transport_one_bounce():
    prof = LT.groove_profile("vgroove", n_patches=60, width=2.0)
    Tm = LT.transport_matrix_radiosity(prof, albedo=0.6)
    c = prof["centers"]
    to = np.array([0.0, 1.5])[None] - c
    r = np.hypot(to[:, 0], to[:, 1])
    cosi = (prof["normals"] * to).sum(1) / r
    F = LT.form_factors_2d(prof)
    R = np.hypot(c[:, None, 0] - c[None, :, 0], c[:, None, 1] - c[None, :, 1])
    a_path = 0.6 * F * (0.6 * cosi / r)[None, :]
    L = r[None, :] + R + r[:, None]
    raw = T.itof_capture(r[None, :], (0.6 * cosi / r)[None, :], frequencies_hz=(20e6,),
                         paths_depth=(0.5 * L.T)[:, None, :], paths_amplitude=a_path.T[:, None, :], noise=False)
    mine = T.itof_phase_amplitude(raw)["wrapped_depth"][0, 0]
    sc = C / (4 * np.pi * 20e6)
    bias = _wrap((mine - r) / sc) * sc
    ref = LT.tof_transport_depth(Tm, camera_xz=(0.0, 1.5), modulation_hz=20e6, n_bounces=1)["bias"]
    assert np.abs(bias - ref).max() < 1e-12


def test_matrix_pencil_separates_two_paths():
    fs = np.arange(1, 9) * 20e6
    one = np.ones((2, 2))
    raw = T.itof_capture(one * 1.3, one * 0.35, frequencies_hz=fs, paths_depth=(one * 0.8)[None],
                         paths_amplitude=(one * 0.1)[None], noise=False)
    ms = T.itof_multipath_separate(T.itof_phase_amplitude(raw))
    assert np.abs(ms["depth"][0] - 0.8).max() < 1e-8 and np.abs(ms["depth"][1] - 1.3).max() < 1e-8
    assert np.allclose(ms["amplitude"][0] / ms["amplitude"][1], 0.1 / 0.35)
    assert ms["residual"].max() < 1e-9


def test_square_wave_wiggling_closed_form_and_correction():
    f = 20e6
    phi = np.linspace(0.02, 2 * np.pi - 0.02, 300)
    d = phi * C / (4 * np.pi * f)
    pa = T.itof_phase_amplitude(T.itof_capture(d[None, :], frequencies_hz=(f,), waveform="square", noise=False))
    q = np.floor(phi / (np.pi / 2))
    u = (phi - q * np.pi / 2) / (np.pi / 2)
    closed = q * np.pi / 2 + np.arctan2(u, 1 - u)
    assert np.abs(_wrap(pa["phase"][0, 0] - closed)).max() < 1e-12
    assert abs(np.abs(_wrap(closed - phi)).max() - 0.0711) < 5e-4
    lut = T.itof_wiggling_correct(pa)
    assert np.abs(_wrap(lut["phase"][0, 0] - phi)).max() < 1e-5
    idx = np.linspace(0, 299, 24).astype(int)
    fit = T.itof_wiggling_correct(pa, calibration=(pa["phase"][0, 0, idx], phi[idx]), n_harmonics=3)
    assert np.abs(_wrap(fit["phase"][0, 0] - phi)).max() < 0.2 * np.abs(_wrap(closed - phi)).max()


def test_flying_pixels_are_flagged_and_ramps_are_not():
    fine = np.full((96, 96), 1.2)
    fine[30:66, 25:70] = 0.8
    raw = T.itof_capture(fine, frequencies_hz=(16e6, 80e6, 120e6), supersample=3, noise=False)
    d = T.itof_unwrap_multifreq(T.itof_phase_amplitude(raw))["depth"]
    blk = fine.reshape(32, 3, 32, 3)
    floating = np.abs(blk - d[:, None, :, None]).min(axis=(1, 3)) > 0.04
    m = T.itof_flying_pixel_mask(d, threshold_m=0.04) > 0
    assert floating.sum() > 10 and (m & floating).sum() >= 0.9 * floating.sum() and (m & ~floating).sum() == 0
    ramp = 1.0 + 0.06 * np.arange(32)[None, :] * np.ones((32, 1))       # 1 画素 6 cm の斜面
    assert T.itof_flying_pixel_mask(ramp, threshold_m=0.04).sum() == 0


def test_fail_closed():
    with pytest.raises(ValueError):
        T.itof_capture(np.zeros((4, 4)))
    with pytest.raises(ValueError):
        T.itof_capture(np.ones((4, 4)), frequencies_hz=(20e6, 20e6))
    with pytest.raises(ValueError):
        T.itof_capture(np.ones((4, 4)), supersample=3)
    with pytest.raises(ValueError):
        T.itof_capture(np.ones((4, 4)), paths_depth=np.ones((1, 4, 4)))
    with pytest.raises(ValueError):
        T.itof_phase_amplitude(np.ones((1, 2, 4)))                        # 2 段では解けない
    with pytest.raises(ValueError):
        T.itof_phase_amplitude({"kind": "other"})
    with pytest.raises(ValueError):
        T.itof_unwrap_multifreq(np.zeros((2, 3)), (80e6, 81.234567e6))     # 通約できない
    pa = T.itof_phase_amplitude(T.itof_capture(np.ones((2, 2)), frequencies_hz=(80e6, 100e6, 120e6), noise=False))
    with pytest.raises(ValueError):
        T.itof_unwrap_multifreq(pa, max_range_m=20.0)                      # 非曖昧距離 7.49 m より広い
    with pytest.raises(ValueError):
        T.itof_unwrap_multifreq(pa, method="beat")                         # 2 周波でない
    with pytest.raises(ValueError):
        T.itof_multipath_separate(pa)                                      # 4 周波未満・等間隔でない
    with pytest.raises(ValueError):
        T.itof_flying_pixel_mask(np.ones((4, 4)), threshold_m=0.0, rel_threshold=0.0)
    with pytest.raises(ValueError):
        T.itof_wiggling_correct(pa, waveform=[1.0, 1.2])                   # 高調波が基本波を上回る


def test_registered_in_the_optics_ledger():
    assert opsoptics.list_ops("itof") == list(T.__all__)
    for name in opsoptics.list_ops("itof"):
        assert opsoptics.get(name) is getattr(T, name)
    import fullseye as fs
    assert fs.ledger.itof_capture is not None
