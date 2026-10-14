# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""filmoptics の門: 転送行列は Airy の式(別実装)と多層膜の閉形式に、膜厚の逆問題は既知の膜厚と閉形式の偏りに一致する。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import filmoptics as F
import matappear as M
import materials as MT


def _n(material, lam):
    return MT._nk(MT._record(material, "t"), np.asarray(lam, float) / 1000.0, "t")[0]


def test_single_layer_matches_airy_independent_implementation():
    lam = np.linspace(400.0, 800.0, 81)
    worst = 0.0
    for d in (0.0, 120.0, 900.0):
        for cos_t, pol in ((1.0, "unpolarized"), (0.6, "s"), (0.6, "p")):
            a = F.multilayer_reflectance([("SIO2", d)], "SI", wavelengths_nm=lam,
                                         angle_deg=math.degrees(math.acos(cos_t)), polarization=pol)[:, 1]
            b = M.thin_film_reflectance(lam, d, "SIO2", "SI", cos_theta=cos_t, polarization=pol)
            worst = max(worst, float(np.max(np.abs(a - b))))
    assert worst < 1e-12


def test_multilayer_closed_forms_and_energy():
    nH, nL, ns, lam0 = 2.3, 1.38, 1.52, 550.0
    for N in (1, 3, 6):
        stack = [(nH, lam0 / 4 / nH), (nL, lam0 / 4 / nL)] * N
        R = float(F.multilayer_reflectance(stack, ns, wavelengths_nm=[lam0])[0, 1])
        q = ns * (nH / nL) ** (2 * N)
        assert abs(R - ((1 - q) / (1 + q)) ** 2) < 1e-12
    ar = F.multilayer_reflectance([(math.sqrt(ns), lam0 / 4 / math.sqrt(ns))], ns, wavelengths_nm=[lam0])[0, 1]
    assert ar < 1e-15
    lam = np.linspace(400.0, 800.0, 41)
    st = [(nH, 80.0), (nL, 120.0), ("SIO2", 200.0)]
    R = F.multilayer_reflectance(st, "N-BK7", wavelengths_nm=lam, angle_deg=35.0)[:, 1]
    T = F.multilayer_reflectance(st, "N-BK7", wavelengths_nm=lam, angle_deg=35.0, quantity="transmittance")[:, 1]
    assert np.max(np.abs(R + T - 1.0)) < 1e-12
    A = F.multilayer_reflectance([("TI", 5.0), ("SIO2", 80.0)], "N-BK7", wavelengths_nm=lam, quantity="absorptance")[:, 1]
    assert np.all(A > 0.05) and np.all(A < 1.0)            # an absorbing metal layer absorbs


def test_roughness_is_debye_waller_and_na_cone_has_closed_form_shift():
    lam = np.linspace(400.0, 800.0, 41)
    r0 = F.multilayer_reflectance([], "SI", wavelengths_nm=lam)[:, 1]
    rr = F.multilayer_reflectance([], "SI", wavelengths_nm=lam, roughness_nm=4.0)[:, 1]
    assert np.max(np.abs(rr - r0 * np.exp(-(4 * np.pi * 4.0 / lam) ** 2))) < 1e-14
    sp = F.multilayer_reflectance([("SIO2", 1000.0)], "SI", 400.0, 800.0, 201, na=0.3)
    nbar = float(np.mean(_n("SIO2", sp[:, 0])))
    t = F.film_thickness_fit(sp, "SIO2", "SI", 0.0, 3000.0)["thickness_nm"]
    assert abs(t / (1000.0 * (1 - 0.09 / (4 * nbar ** 2))) - 1) < 0.003


def test_fft_and_fit_recover_thickness_and_fft_limit_is_closed_form():
    sp = F.multilayer_reflectance([("SIO2", 1500.0)], "SI", 400.0, 800.0, 401)
    f = F.film_thickness_fft(sp, "SIO2")
    x = 2 * _n("SIO2", sp[:, 0]) / sp[:, 0]
    assert abs(f["min_thickness_nm"] - 2.0 / (x.max() - x.min())) < 1e-9
    assert f["reliable"] and abs(f["thickness_nm"] - 1500.0) < 5.0
    assert abs(f["n_fringes"] - f["thickness_nm"] * (x.max() - x.min())) < 1e-9
    thin = F.multilayer_reflectance([("SIO2", 80.0)], "SI", 400.0, 800.0, 401)
    assert not F.film_thickness_fft(thin, "SIO2")["reliable"]
    fit = F.film_thickness_fit(thin, "SIO2", "SI", 0.0, 2000.0)
    assert abs(fit["thickness_nm"] - 80.0) < 0.05 and fit["rmse"] < 1e-6
    assert [c[0] for c in fit["candidates"]][0] == fit["thickness_nm"]


def test_wrong_material_bias_follows_optical_thickness_and_shows_in_residual():
    sp = F.multilayer_reflectance([("SIO2", 1000.0)], "SI", 400.0, 800.0, 201)
    w = F.film_thickness_fit(sp, "SI3N4", "SI", 0.0, 3000.0)
    lam = sp[:, 0]
    closed = 1000.0 * np.mean(_n("SIO2", lam)) / np.mean(_n("SI3N4", lam))
    assert abs(w["thickness_nm"] / closed - 1) < 0.03
    assert w["rmse"] > 0.02


def test_film_color_bare_silicon_and_white_point():
    c = F.film_color("SIO2", "SI", 0.0, 600.0, 7)
    assert c["srgb"].shape == (7, 3) and np.all((c["srgb"] >= 0) & (c["srgb"] <= 1))
    assert 240.0 <= c["hue_deg"][0] <= 300.0 and c["chroma"][0] < 10.0      # bare Si: bluish grey
    lam = c["wavelength_nm"]
    assert abs(float(M.spectrum_to_srgb(lam, np.ones_like(lam))[1]) - 1.0) < 1e-3   # sRGB matrix is the 4-digit IEC one
    tri = np.column_stack([np.arange(370.0, 791.0), np.ones(421)])
    c2 = F.film_color("SIO2", "SI", 0.0, 600.0, 7, illuminant=tri)       # flat light also works
    assert c2["lab"].shape == (7, 3)


def test_thickness_map_spectral_unique_and_rgb_window():
    rng = np.random.default_rng(0)
    d = 300.0 + 400.0 * rng.random((6, 7))
    lam = np.arange(400.0, 701.0, 20.0)
    lut = F._model_lut(lam, "SIO2", "SI", (), d.ravel(), 0.0, 0.0, 1.0, 0.0, "t")
    cube = lut.T.reshape(lam.size, 6, 7)
    m = F.film_thickness_map(cube, lam, "SIO2", "SI", 0.0, 1500.0, step_nm=0.5)
    assert np.max(np.abs(m["thickness"] - d)) < 0.05 and np.all(m["n_candidates"] == 1)
    mn = F.film_thickness_map(cube * 0.9, lam, "SIO2", "SI", 0.0, 1500.0, step_nm=0.5, normalize=True)
    assert np.max(np.abs(mn["thickness"] - d)) < 0.05               # brightness does not matter when normalised
    col = F.film_color("SIO2", "SI", 0.0, 1500.0, 3001)
    rgb = np.array([np.interp(d, col["thickness_nm"], col["linear_srgb"][:, k]) for k in range(3)])
    w = F.film_thickness_map(rgb, None, "SIO2", "SI", 450.0, 650.0, mode="srgb", step_nm=0.5)
    inside = (d > 455) & (d < 645)
    assert inside.sum() >= 5 and np.max(np.abs(w["thickness"] - d)[inside]) < 0.5


def test_fail_closed():
    with pytest.raises(ValueError, match="unknown material"):
        F.multilayer_reflectance([("UNOBTAINIUM", 10.0)], "SI")
    with pytest.raises(ValueError, match=">= 0"):
        F.multilayer_reflectance([("SIO2", -1.0)], "SI")
    with pytest.raises(ValueError):
        F.multilayer_reflectance([("PMMA", 100.0)], "SI", 400.0, 800.0)      # PMMA table starts at 437 nm
    with pytest.raises(ValueError, match="not both"):
        F.multilayer_reflectance([("SIO2", 100.0)], "SI", na=0.2, angle_deg=5.0)
    with pytest.raises(ValueError, match="opaque"):
        F.multilayer_reflectance([("TI", 50000.0)], "SI")
    with pytest.raises(ValueError, match="roughness"):
        F.multilayer_reflectance([("SIO2", 100.0)], "SI", roughness_nm=2.0, quantity="transmittance")
    sp = F.multilayer_reflectance([("SIO2", 500.0)], "SI", 400.0, 800.0, 41)
    with pytest.raises(ValueError, match="strictly increasing"):
        F.film_thickness_fft(sp[::-1])
    with pytest.raises(ValueError):
        F.film_thickness_fit(sp, "SIO2", "SI", 100.0, 50.0)
    with pytest.raises(ValueError, match="band images"):
        F.film_thickness_map(np.zeros((4, 3, 3)), (450.0, 500.0, 550.0, 600.0, 650.0, 700.0))
    with pytest.raises(ValueError, match="exactly 3"):
        F.film_thickness_map(np.zeros((4, 3, 3)), None, mode="srgb")
