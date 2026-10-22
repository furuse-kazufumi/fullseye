# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""temsim の門: 波長の公表値、CTF の零点の閉形式、Scherzer、Raman–Nath、焦点外れの回収と拒否、台帳への登録。"""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import special

import temsim as T


def test_wavelength_published_values():
    for kv, pm in ((100.0, 3.7014), (200.0, 2.5079), (300.0, 1.9687)):
        assert abs(T.tem_wavelength(kv)["wavelength_pm"] - pm) < 6e-5
    r = T.tem_wavelength(300.0)
    assert r["wavelength_nonrel_pm"] / r["wavelength_pm"] > 1.1           # relativity is not optional
    assert abs(T.POTENTIAL_CONST - 47.8776) < 1e-3 and abs(T.MOTT_BETHE_K - 0.023934) < 1e-6


def test_ctf_zeros_match_closed_form_and_scherzer():
    p = T.tem_ctf_profile(0.4, 200001, 300.0, 2.7, 15000.0, 0.07)
    s = np.sign(p["ctf"])
    idx = np.where(s[1:] * s[:-1] < 0)[0]
    num = p["k"][idx] - p["ctf"][idx] * (p["k"][idx + 1] - p["k"][idx]) / (p["ctf"][idx + 1] - p["ctf"][idx])
    assert len(num) == len(p["zeros_A_inv"]) > 10
    assert np.max(np.abs(num - np.array(p["zeros_A_inv"]))) < 1e-6
    sch = T.tem_scherzer(300.0, 2.7)
    first = 1.0 / T.tem_ctf_profile(1.0, 10, 300.0, 2.7, sch["defocus_A"], 0.0)["zeros_A_inv"][0]
    assert abs(first - sch["point_resolution_A"]) < 1e-9
    assert abs(first / sch["point_resolution_formula_A"] - 1) < 0.005
    c2 = T.tem_ctf(64, 1.0, 300.0, 2.7, 15000.0)
    assert c2.shape == (64, 64) and abs(c2[32, 32] + 0.07) < 1e-12        # DC = −w


def test_scatterer_integral_and_mip():
    v = T.tem_projected_potential([[10.2, 7.9]], "C", 64, 0.5)
    want = T.POTENTIAL_CONST * float(T._electron_form_factor("C", 0.0))
    assert abs(v.sum() * 0.25 / want - 1) < 1e-9
    mip = T.POTENTIAL_CONST * 8 * float(T._electron_form_factor("Si", 0.0)) / 5.4311 ** 3
    assert abs(mip / 13.71 - 1) < 0.02                                    # neutral-atom value
    with pytest.raises(ValueError):
        T.tem_projected_potential([[0.0, 0.0]], "Xx", 32, 0.5)


def test_multislice_raman_nath_and_linear_limit():
    n, px, phi0 = 64, 0.5, 1.1
    sig = T.tem_wavelength(300.0)["sigma_rad_per_VA"]
    x = np.arange(n) * px
    v = np.tile((phi0 / sig) * np.cos(2 * np.pi * 4 * x / (n * px))[None, :], (n, 1))
    F = np.fft.fft2(T.tem_multislice(v, px, 300.0, 0.0, 1.0)["exit_wave"]) / (n * n)
    for o in range(4):
        assert abs(abs(F[0, 4 * o]) ** 2 - special.jv(o, phi0) ** 2) < 1e-12
    film = T.tem_amorphous_film(64, 1.0, 20.0, seed=3)
    f0 = (film - film.mean()) * 0.05
    a = T.tem_image_weak_phase(f0, 1.0, 300.0, 2.7, 8000.0, mode="linear")
    b = T.tem_image_weak_phase(f0, 1.0, 300.0, 2.7, 8000.0, mode="coherent")
    assert np.std(a - b) / np.std(a - 1) < 0.02


def test_estimate_recovers_defocus_and_refuses_noise():
    film = T.tem_amorphous_film(512, 1.0, 50.0, seed=1)
    I = T.tem_image_weak_phase(film, 1.0, 300.0, 2.7, 12000.0, 800.0, 30.0, 0.07, alpha_mrad=0.01,
                               focal_spread_A=40.0, dose_e_per_A2=40.0, seed=21)
    r = T.tem_ctf_estimate(I, 1.0, 300.0, 2.7, 0.07)
    assert r["accepted"] and abs(r["defocus_A"] - 12000.0) < 60.0
    assert abs((r["defocus_u_A"] - r["defocus_v_A"]) - 800.0) < 80.0
    assert abs((r["astig_angle_deg"] - 30.0 + 90) % 180 - 90) < 5.0
    assert 0 < r["defocus_sigma_A"] < 100.0
    noise = np.random.default_rng(0).poisson(40.0, (512, 512)).astype(float)
    with pytest.raises(ValueError, match="refused"):
        T.tem_ctf_estimate(noise, 1.0, 300.0, 2.7, 0.07)
    assert not T.tem_ctf_estimate(noise, 1.0, 300.0, 2.7, 0.07, on_fail="report")["accepted"]


def test_correction_improves_and_fail_closed():
    film = T.tem_amorphous_film(128, 0.5, 30.0, seed=5)
    I = T.tem_image_weak_phase(film, 0.5, 300.0, 2.7, 6000.0)
    k = np.hypot(*np.meshgrid(np.fft.fftfreq(128, 0.5), np.fft.fftfreq(128, 0.5)))
    vl = np.fft.ifft2(np.fft.fft2(film) * (k <= 1 / 3.0)).real
    c = lambda a: float(np.corrcoef(np.fft.ifft2(np.fft.fft2(a) * (k <= 1 / 3.0)).real.ravel(), vl.ravel())[0, 1])  # noqa: E731
    assert c(T.tem_ctf_correct(I, 0.5, 300.0, 2.7, 6000.0)) > c(-(I - I.mean())) + 0.3
    with pytest.raises(ValueError):
        T.tem_ctf_correct(I, 0.5, method="nope")
    with pytest.raises(ValueError):
        T.tem_image_weak_phase(np.full((16, 16), np.nan))
    with pytest.raises(ValueError):
        T.tem_ctf(8, amplitude_contrast=1.0)
    with pytest.raises(ValueError):
        T.tem_wavelength(-1.0)
    assert math.isfinite(T.tem_power_spectrum(I).sum())


def test_ledger_registration():
    import opsoptics
    assert opsoptics.list_ops("tem") == sorted(opsoptics.list_ops("tem"), key=T.__all__.index)
    assert set(opsoptics.list_ops("tem")) == set(T.__all__)
    assert opsoptics.missing() == []
    import fullseye as fs
    assert callable(fs.ledger.tem_ctf_estimate)


def test_refusal_thresholds_flip_the_verdict_at_the_boundary():
    """判定のしきい値 2 つが、境界に置いた入力で 2 点とも効く(探針の種と同じ写真)。

    Δf 6000 Å・帯域 k ≤ 0.2 Å⁻¹ で零点は 4 本、相関の山は 100 e/Å² で 11.8 MAD。線量 30 / 60 e/Å² の組は
    山の z が既定の 8 のすぐ下と上に来る。返り値の ``n_rings`` と ``peak_z`` が「測れる限界」。
    """
    film = T.tem_amorphous_film(256, 1.0, 30.0, seed=2)
    kw = dict(defocus_min_A=2000.0, k_max=0.2, on_fail="report")
    I = T.tem_image_weak_phase(film, 1.0, 300.0, 2.7, 6000.0, dose_e_per_A2=100.0, seed=1)
    base = T.tem_ctf_estimate(I, 1.0, **kw)
    assert base["accepted"] and base["n_rings"] == 4 and 8.0 < base["peak_z"] < 16.0
    assert T.tem_ctf_estimate(I, 1.0, min_rings=4, **kw)["accepted"]
    assert not T.tem_ctf_estimate(I, 1.0, min_rings=5, **kw)["accepted"]
    assert T.tem_ctf_estimate(I, 1.0, min_peak_z=4.0, **kw)["accepted"]
    assert not T.tem_ctf_estimate(I, 1.0, min_peak_z=16.0, **kw)["accepted"]
    lo = T.tem_ctf_estimate(T.tem_image_weak_phase(film, 1.0, 300.0, 2.7, 6000.0, dose_e_per_A2=30.0, seed=1), 1.0, **kw)
    hi = T.tem_ctf_estimate(T.tem_image_weak_phase(film, 1.0, 300.0, 2.7, 6000.0, dose_e_per_A2=60.0, seed=1), 1.0, **kw)
    assert 6.0 < lo["peak_z"] < 8.0 and not lo["accepted"]
    assert 8.0 < hi["peak_z"] < 11.0 and hi["accepted"]
