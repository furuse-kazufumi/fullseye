# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""spectralrad の門: 光源の式は外部の定義値(CIE 15 の表・Wien・Stefan–Boltzmann)、QE は閉形式。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import spectralrad as S

#: CIE 15:2004 の標準イルミナント A の表の値(定義式の値、5 桁以上で公表)。
CIE_A_TABLE = {300.0: 0.930483, 560.0: 100.0, 780.0: 241.675}


def test_cie_illuminant_a_reproduces_the_published_table():
    A = S.cie_illuminant_a(300.0, 830.0, 107)
    assert A.shape == (107, 2)
    for wl, v in CIE_A_TABLE.items():
        got = float(np.interp(wl, A[:, 0], A[:, 1]))
        assert abs(got - v) / v < 5e-6, (wl, got, v)


def test_blackbody_obeys_wien_and_stefan_boltzmann():
    for T in (2856.0, 5772.0):
        bb = S.blackbody_spectrum(T, 100.0, 100000.0, 200000)
        st = S.spectral_stats(bb)
        assert abs(st["peak_nm"] - 2.897771955e6 / T) < 0.6            # Wien, grid 0.5 nm
        sigma = 5.670374419e-8
        assert abs(st["integral"] * math.pi / (sigma * T ** 4) - 1.0) < 1e-5   # M = π L
    rel = S.blackbody_spectrum(3000.0, 500.0, 1500.0, 11, normalize_nm=1000.0)
    assert float(rel[5, 1]) == pytest.approx(1.0, abs=1e-12)


def test_led_and_bandpass_have_the_requested_width():
    for model in ("ohno", "gaussian"):
        st = S.spectral_stats(S.led_spectrum(1050.0, 50.0, 800.0, 1300.0, 5001, model=model))
        assert abs(st["fwhm_nm"] - 50.0) < 1e-3 and st["peak_nm"] == pytest.approx(1050.0)
    ohno = S.led_spectrum(1050.0, 50.0, 800.0, 1300.0, 5001)
    gauss = S.led_spectrum(1050.0, 50.0, 800.0, 1300.0, 5001, model="gaussian")
    far = ohno[:, 0] > 1110.0
    assert np.all(ohno[far, 1] >= gauss[far, 1])                        # Ohno has heavier tails
    bp = S.bandpass_spectrum(1100.0, 40.0, 0.9, 4, 0.0, 800.0, 1400.0, 6001)
    assert abs(S.spectral_stats(bp)["fwhm_nm"] - 40.0) < 1e-3
    assert float(bp[:, 1].max()) == pytest.approx(0.9)


def test_silicon_qe_is_the_closed_form_and_saturates_to_one_minus_r():
    import materials as M
    q = S.silicon_photodiode_qe(3.0, 0.0, None, 400.0, 1100.0, 71)
    rec = M._record("SI", "t")
    n, k = M._nk(rec, q[:, 0] / 1000.0, "t")[:2]
    R = ((n - 1) ** 2 + k ** 2) / ((n + 1) ** 2 + k ** 2)
    a = 4 * np.pi * k / (q[:, 0] / 1000.0)
    assert np.allclose(q[:, 1], (1 - R) * (1 - np.exp(-a * 3.0)), rtol=0, atol=1e-15)
    thick = S.silicon_photodiode_qe(1e5, 0.0, None, 400.0, 700.0, 31)
    assert np.allclose(thick[:, 1], (1 - R[:31]), atol=1e-9)           # every photon absorbed
    q10 = S.silicon_photodiode_qe(10.0, 0.0, 0.03, 900.0, 1100.0, 21)
    q3 = S.silicon_photodiode_qe(3.0, 0.0, 0.03, 900.0, 1100.0, 21)
    assert np.all(q10[:, 1] > q3[:, 1])                                 # deeper collection helps NIR
    assert float(q3[-1, 1]) < 0.01                                      # 1.1 um: Si barely absorbs


def test_spectral_algebra_and_photon_conversion():
    a = S.led_spectrum(1100.0, 1.0, 1080.0, 1120.0, 4001)
    t = np.array([[1000.0, 0.5], [1200.0, 0.1]])
    prod = S.spectral_product(a, t)
    ratio = S.spectral_integral(prod) / S.spectral_integral(a)
    assert ratio == pytest.approx(0.3, abs=1e-6)                        # narrow line -> T(1100)
    e = np.array([[550.0, 1.0], [1100.0, 1.0]])
    ph = S.energy_to_photons(e)
    assert ph[1, 1] / ph[0, 1] == pytest.approx(2.0)                    # λ/hc
    assert S.spectral_integral(np.array([[0.0 + 1, 1.0], [11.0, 1.0]]), 2.0, 5.0) == pytest.approx(3.0)


def test_fail_closed_inputs():
    with pytest.raises(ValueError, match="not extrapolated"):
        S.spectral_product(np.array([[800.0, 1.0], [1300.0, 1.0]]), np.array([[900.0, 1.0], [1200.0, 1.0]]))
    with pytest.raises(ValueError, match="pairs"):
        S.spectral_integral(np.ones(5))
    with pytest.raises(ValueError, match="increasing"):
        S.spectral_stats(np.array([[2.0, 1.0], [1.0, 1.0]]))
    with pytest.raises(ValueError, match="model"):
        S.led_spectrum(model="laser")
    with pytest.raises(ValueError):
        S.blackbody_spectrum(temperature_k=-1.0)
    with pytest.raises(ValueError):
        S.silicon_photodiode_qe(wl_max_nm=2000.0)                       # outside Green 2008
    with pytest.raises(ValueError, match="outside"):
        S.spectral_integral(np.array([[1.0, 1.0], [2.0, 1.0]]), 0.5, 1.5)
