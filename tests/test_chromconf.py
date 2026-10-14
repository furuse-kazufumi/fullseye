# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""chromconf(クロマティック共焦点)の門: 閉形式・外の真値・往復・fail-closed。"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import chromconf as CC  # noqa: E402
import materials as MT  # noqa: E402
import raytrace as RT  # noqa: E402


@pytest.fixture(scope="module")
def probe():
    return CC.chromatic_confocal_probe()


# --------------------------------------------------------------------------- #
# 軸応答                                                                        #
# --------------------------------------------------------------------------- #
def test_axial_response_mirror_is_sinc2_closed_form():
    na, lam = 0.3, 0.55
    r = CC.confocal_axial_response(-20.0, 20.0, 801, lam * 1e3, na)
    s2 = (1.0 - math.sqrt(1.0 - na * na)) / 2.0                      # sin²(α/2)
    u = 8.0 * math.pi * r[:, 0] * s2 / lam
    ref = np.sinc(u / 2.0 / math.pi) ** 2
    assert np.max(np.abs(r[:, 1] - ref)) < 1e-12


def test_axial_response_point_is_sinc4_quarter():
    na, lam = 0.2, 0.6
    r = CC.confocal_axial_response(-30.0, 30.0, 601, lam * 1e3, na, target="point")
    s2 = (1.0 - math.sqrt(1.0 - na * na)) / 2.0
    u = 8.0 * math.pi * r[:, 0] * s2 / lam
    ref = np.sinc(u / 4.0 / math.pi) ** 4
    assert np.max(np.abs(r[:, 1] - ref)) < 1e-12


def test_quadrature_matches_closed_form_at_vanishing_aberration():
    a = CC.confocal_axial_response(-60, 60, 1201, 575.0, 0.16)
    b = CC.confocal_axial_response(-60, 60, 1201, 575.0, 0.16, longitudinal_sa_um=1e-9)
    assert np.max(np.abs(a[:, 1] - b[:, 1])) < 1e-9


def test_vectorised_bins_match_scalar_response():
    lam = np.linspace(450, 700, 9)
    dz = np.linspace(-40, 900, 9)
    na = np.linspace(0.16, 0.15, 9)
    lsa = np.linspace(-40, 20, 9)
    v = CC._response_bins(dz, lam * 1e-3, na, lsa, "mirror")
    s = [CC._response(np.array([d]), w * 1e-3, a, 1.0, q, "mirror")[0] for d, w, a, q in zip(dz, lam, na, lsa)]
    assert np.max(np.abs(v - np.array(s))) < 1e-12


def test_fwhm_closed_form_and_lambda_over_na2():
    for na in (0.1, 0.3):
        r = CC.confocal_axial_response(-100, 100, 40001, 500.0, na)
        half = r[r[:, 1] >= 0.5, 0]
        assert abs((half.max() - half.min()) - CC._fwhm_closed(0.5, na)) < 0.02
    ratio = CC._fwhm_closed(0.5, 0.05) / (0.5 / 0.05 ** 2)
    assert abs(ratio - 4 * CC.FWHM_X_MIRROR / (2 * math.pi)) < 1e-3       # 近軸 0.886 λ/NA²


def test_spherical_aberration_moves_peak_by_half_lsa_and_lowers_it():
    lsa = -30.0
    r = CC.confocal_axial_response(-80, 80, 3201, 550.0, 0.15, longitudinal_sa_um=lsa)
    k = int(np.argmax(r[:, 1]))
    assert abs(r[k, 0] - lsa / 2) < 0.15 * abs(lsa)
    assert r[k, 1] < 0.95


def test_sparrow_fraction_is_where_the_midpoint_flattens():
    d = CC.SPARROW_FRACTION * 2 * CC.FWHM_X_MIRROR
    f = lambda x: np.sinc((x - d / 2) / math.pi) ** 2 + np.sinc((x + d / 2) / math.pi) ** 2  # noqa: E731
    h = 1e-3
    assert abs(f(h) - 2 * f(0) + f(-h)) / h ** 2 < 1e-4
    assert 0.8 < CC.SPARROW_FRACTION < 1.0


# --------------------------------------------------------------------------- #
# 較正表                                                                        #
# --------------------------------------------------------------------------- #
def test_probe_paraxial_focus_matches_thick_lens_closed_form(probe):
    n0 = RT.refractive_index(CC.GLASS_DENSE_FLINT, 0.575)
    for w, z in zip(probe["wavelength_nm"], probe["paraxial_um"]):
        n = MT.material_optical_constants(CC.GLASS_DENSE_FLINT, w)["n"]
        f = (n0 - 1.0) * 16.0 / (n - 1.0)
        assert abs((z * 1e-3 + probe["origin_mm"]) - f) < 1e-9


def test_probe_is_monotonic_and_lsa_vanishes_at_design_wavelength(probe):
    cal = np.array(probe["calibration_um"])
    assert cal[0] == 0.0 and np.all(np.diff(cal) > 0)
    lsa575 = CC._probe_at(probe, [575.0], "t")["lsa_um"][0]
    assert abs(lsa575) < 0.1
    assert probe["lsa_um"][0] < -20.0                                     # 色球面収差


def test_probe_rejects_bad_input():
    with pytest.raises(ValueError):
        CC.chromatic_confocal_probe(wl_min_nm=700.0, wl_max_nm=450.0)
    with pytest.raises(ValueError):
        CC.chromatic_confocal_probe(surfaces=[])
    with pytest.raises(ValueError):
        CC.chromatic_confocal_probe(wl_min_nm="450")
    with pytest.raises(ValueError):
        CC.chromatic_confocal_probe(n_points=True)
    with pytest.raises(ValueError):                                       # 表の外の波長(重フリントは 2.5 µm まで)
        CC.chromatic_confocal_probe(wl_min_nm=2000.0, wl_max_nm=4000.0)


def test_probe_rejects_non_monotonic_calibration():
    # 色消しの貼り合わせ(ホウケイ酸クラウン + フリント n_d 1.620・V_d 36.4、薄肉の条件 φ₁/V₁ + φ₂/V₂ = 0 で f ≈ 95 mm)は焦点が 520 nm 付近で
    # 折り返す(2 次スペクトル)→ 同じ位置に 2 つの色が合い、高さが一意に決まらない
    surf = [{"R": 44.73, "t": 4.0, "n": CC.GLASS_CROWN, "ap": 3.0}, {"R": -44.73, "t": 2.0, "n": CC._glass_near(1.6200, 36.37)},
            {"R": -826.0, "t": None, "n": 1.0}]
    with pytest.raises(ValueError, match="monotonic"):
        CC.chromatic_confocal_probe(surf, 0, 450.0, 700.0, 26)


def test_probe_dict_is_json_serialisable(probe):
    import json
    json.dumps(probe)
    again = CC.chromatic_confocal_probe(surfaces=probe["surfaces"])
    assert abs(again["range_um"] - probe["range_um"]) < 1e-9


# --------------------------------------------------------------------------- #
# 順モデルと読み                                                                 #
# --------------------------------------------------------------------------- #
def test_roundtrip_noiseless_height(probe):
    for z in (80.0, 500.0, 1000.0):
        pk = CC.chromatic_confocal_peaks(CC.chromatic_confocal_spectrum(probe, z), max_peaks=1)
        assert abs(CC.chromatic_confocal_readout(pk, probe)["heights_um"][0] - z) < 0.1


def test_plate_thickness_na_correction(probe):
    s = CC.chromatic_confocal_spectrum(probe, 300.0, stack=((CC.GLASS_CROWN, 500.0),), substrate=1.0)
    r = CC.chromatic_confocal_readout(CC.chromatic_confocal_peaks(s), probe, CC.GLASS_CROWN)
    assert abs(r["thickness_um"] - 500.0) < 0.3
    assert abs(r["thickness_paraxial_um"] - 500.0) > 3 * abs(r["thickness_um"] - 500.0)


def test_plate_sa_matches_materials_plate_focus_shift():
    for mat, wl, na in ((CC.GLASS_CROWN, 530.0, 0.155), ("SAPPHIRE", 500.0, 0.2)):
        n = MT.material_optical_constants(mat, wl)["n"]
        pf = MT.plate_focus_shift(mat, 1.0, wl, na)
        assert abs(float(CC._plate_g(n, na)) - pf["spherical_aberration_mm"]) < 1e-12


def test_tilt_return_closed_form():
    na = np.array([0.15])
    assert CC._tilt_return(0.0, na)[0] == 1.0
    lim = math.degrees(0.5 * math.asin(0.3))
    assert CC._tilt_return(lim + 0.01, na)[0] == 0.0
    assert 0.0 < CC._tilt_return(lim - 0.5, na)[0] < 0.1


def test_spectrum_knobs_and_refusals(probe):
    base = CC.chromatic_confocal_spectrum(probe, 400.0)
    assert base.shape[1] == 2 and abs(base[:, 1].max() - 1.0) < 1e-12
    noisy = CC.chromatic_confocal_spectrum(probe, 400.0, photons_per_peak=1000.0, seed=1)
    assert np.all(noisy[:, 1] == np.round(noisy[:, 1]))                   # Poisson の整数
    assert np.array_equal(noisy, CC.chromatic_confocal_spectrum(probe, 400.0, photons_per_peak=1000.0, seed=1))
    with pytest.raises(ValueError, match="no interface"):
        CC.chromatic_confocal_spectrum(probe, 5000.0)
    with pytest.raises(ValueError, match="nothing returns"):
        CC.chromatic_confocal_spectrum(probe, 400.0, tilt_deg=12.0)
    with pytest.raises(ValueError):
        CC.chromatic_confocal_spectrum({"pre": 1}, 400.0)
    with pytest.raises(ValueError):
        CC.chromatic_confocal_spectrum(probe, 400.0, stack=((CC.GLASS_CROWN, -1.0),))
    with pytest.raises(ValueError):
        CC.chromatic_confocal_spectrum(probe, 400.0, source=np.array([[500.0, 1.0], [600.0, 1.0]]))


def test_peaks_refusals():
    lam = np.linspace(450, 700, 501)
    flat = np.column_stack([lam, np.ones_like(lam)])
    with pytest.raises(ValueError):
        CC.chromatic_confocal_peaks(flat)
    edge = np.column_stack([lam, np.exp(-0.5 * ((lam - 450.0) / 2.0) ** 2)])
    with pytest.raises(ValueError, match="band edge"):
        CC.chromatic_confocal_peaks(edge)
    sat = np.column_stack([lam, np.minimum(np.exp(-0.5 * ((lam - 550.0) / 4.0) ** 2), 0.5)])
    with pytest.raises(ValueError, match="saturated"):
        CC.chromatic_confocal_peaks(sat)
    with pytest.raises(ValueError):
        CC.chromatic_confocal_peaks(np.column_stack([lam, -np.ones_like(lam)]))
    with pytest.raises(ValueError):
        CC.chromatic_confocal_peaks(np.zeros((0, 2)))


def test_readout_refuses_one_peak_for_a_layer_and_empty(probe):
    with pytest.raises(ValueError, match="exactly 2 peaks"):
        CC.chromatic_confocal_readout([520.0], probe, CC.GLASS_CROWN)
    with pytest.raises(ValueError, match="empty"):
        CC.chromatic_confocal_readout([], probe)
    with pytest.raises(ValueError):
        CC.chromatic_confocal_readout([800.0], probe)


def test_limits(probe):
    L = CC.chromatic_confocal_limits(probe)
    assert abs(L["range_um"] - probe["range_um"]) < 1e-12
    assert 5.0 < L["max_tilt_deg"] < 15.0
    assert L["min_thickness_um"] > L["min_apparent_separation_um"]
    assert L["tilt_return"].shape == (61, 2)
