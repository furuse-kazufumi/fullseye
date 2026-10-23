# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""シンチレータ・蛍光体の発光の列(materials)と、シンチレータ積層のセンサ(dualxray.scintillator_sensor_qe)。

真値の門:
  * 吸収効率は閉形式 1 − exp(−ρ (μ/ρ) t)(μ/ρ は NIST SRD 126 の列)、厚さ → ∞ で 1、厚さに単調。
  * 発光スペクトルは ∫ S dλ = 1 に正規化される(倍率に依らない)。細いガウスの極限は「極大の 1 本の線」に戻る。
  * 既存の ``dual_kvp_channels`` の既定(CsI 0.6 mm)は 2026-10-23 の前(master 125dc785c8 で採った値)と一致し、
    同じプロセスの中では既定・明示の ``CSI``・シンチレータの ``CSI:TL`` が 1 ビットも違わない。
  * 材料表の発光の極大での屈折率(PDG 2024 表 35.4)を、独立な一次文献の分散式(RII の CsI / NaI / BGO)で検算する。
"""
from __future__ import annotations

import math
import re

import numpy as np
import pytest

import dualxray as D
import materials as M
import materials_xray_data as MX
import spectralrad as SR

SCINT = ("BI4GE3O12", "CDWO4", "CSI:TL", "GD2O2S:TB", "LU1.8Y0.2SIO5:CE", "LU2SIO5:CE", "NAI:TL")
FIELDS = ("density_g_cm3", "light_yield_photons_per_mev", "decay_time_ns", "emission_peak_nm",
          "emission_fwhm_nm", "refractive_index_at_peak", "xray_material")


def _sc(name):
    return M._RECORDS[name]["properties"]["scintillator"]


# --------------------------------------------------------------------------- #
# 材料表のレコード                                                              #
# --------------------------------------------------------------------------- #
def test_seven_scintillator_records_named_by_formula():
    names = tuple(sorted(n for n, r in M._RECORDS.items() if "scintillator" in r["properties"]))
    assert names == SCINT
    for n in names:
        # 化学式(元素記号・数・小数点)+ 付活剤(:記号)だけ —— 商品名を名前にしない
        assert re.fullmatch(r"([A-Z][A-Z]?[0-9.]*)+(:[A-Z][A-Z]?)?", n), n
        assert M._RECORDS[n]["class"] == "crystal"


def test_every_value_has_a_source_and_missing_values_are_declared():
    for n in SCINT:
        sc = _sc(n)
        for f in FIELDS:
            if sc[f] is None:
                assert f in sc["unverified"], (n, f)
            else:
                assert f not in sc["unverified"], (n, f)
                assert sc["sources"].get(f), (n, f)
        assert M._RECORDS[n]["properties"]["density_kg_m3"] == pytest.approx(sc["density_g_cm3"] * 1000.0)
    # 一次情報で確かめられなかったもの(推測で埋めない): GOS の光収率、全材料の発光の幅
    assert _sc("GD2O2S:TB")["light_yield_photons_per_mev"] is None
    assert all(_sc(n)["emission_fwhm_nm"] is None for n in SCINT)


def test_published_values_as_copied():
    """写した公表値の回帰(PDG 2024 表 35.4 / LBNL の行 / Tang 2023)。値を変えるなら出典も読み直すこと。"""
    want = {  # (密度, 光収率, 減衰 ns, 極大 nm)
        "CSI:TL": (4.51, 56000.0, 1220.0, 550.0), "NAI:TL": (3.67, 45000.0, 245.0, 410.0),
        "BI4GE3O12": (7.13, 8500.0, 300.0, 480.0), "LU2SIO5:CE": (7.40, 27000.0, 40.0, 402.0),
        "LU1.8Y0.2SIO5:CE": (7.1, 34000.0, 41.0, 397.0), "CDWO4": (7.9, 27000.0, 12000.0, 495.0),
        "GD2O2S:TB": (7.44, None, 638000.0, 545.0)}
    for n, (rho, ly, tau, peak) in want.items():
        sc = _sc(n)
        assert (sc["density_g_cm3"], sc["light_yield_photons_per_mev"], sc["decay_time_ns"],
                sc["emission_peak_nm"]) == (rho, ly, tau, peak), n


@pytest.mark.parametrize("name,tol", [("CSI:TL", 0.01), ("BI4GE3O12", 0.01), ("NAI:TL", 0.03)])
def test_refractive_index_at_the_peak_agrees_with_an_independent_dispersion(name, tol):
    """PDG の「発光の極大での n」と、RII の一次文献の分散式(CsI / NaI: Li 1976、BGO: Williams 1996)。

    NaI だけ 0.03: Li 1976 の NaI の Sellmeier は「1 点の測定と誘電率から作った」と RII 自身が注記していて、
    410 nm で 1.824(PDG 1.85 より 0.026 低い)。測った Jellison 2012(436〜633 nm)は 436 nm で 1.839 で、
    範囲が発光の極大に届かず、Li(436 nm で 1.812)と継ぐと 0.027 の段差になるので表には入れていない。
    """
    sc = _sc(name)
    n = M.material_optical_constants(name, sc["emission_peak_nm"])["n"]
    assert abs(n - sc["refractive_index_at_peak"]) < tol, (name, n)


def test_material_table_rows_carry_a_reference():
    rows = {r["name"]: r for r in M.material_table()}
    for n in SCINT:
        assert rows[n]["reference"], n


def test_aliases_resolve_to_the_records():
    for alias, name in (("BGO", "BI4GE3O12"), ("LSO", "LU2SIO5:CE"), ("LYSO", "LU1.8Y0.2SIO5:CE"),
                        ("GOS:Tb", "GD2O2S:TB"), ("CsI(Tl)", "CSI:TL"), ("NaI:Tl", "NAI:TL")):
        assert M._scintillator(alias, "t")[0] == name
    # X 線の列の名前(NIST の化合物の表)はシンチレータに読み替えない
    assert M._scintillator("CSI", "t") is None and M._scintillator("GOS", "t") is None
    assert M._scintillator("N-BK7", "t") is None and M._scintillator(3.0, "t") is None


# --------------------------------------------------------------------------- #
# X 線の列                                                                      #
# --------------------------------------------------------------------------- #
def test_lu_and_bi_tables_were_added_from_nist():
    el = {e["Z"]: e for e in MX.XRAY_ELEMENTS}
    assert len(el) == 51
    lu, bi = el[71], el[83]
    assert (lu["symbol"], bi["symbol"]) == ("Lu", "Bi")
    k_lu = [r for r in lu["rows"] if r[3] == "K"]
    k_bi = [r for r in bi["rows"] if r[3] == "K"]
    assert k_lu[0][0] == 63.3138 and k_bi[0][0] == 90.5259      # K 端 [keV](NIST ElemTab z71 / z83)
    assert M.material_xray_constants("LU", 60.0)["mu_rho_cm2_g"] == 3.297
    assert M.material_xray_constants("BI", 60.0)["mu_rho_cm2_g"] == 5.233


def test_csi_tl_x_ray_column_is_bit_identical_to_the_nist_csi_table():
    a = M.material_xray_attenuation("CSI", 10.0, 150.0, 141, "mu")
    b = M.material_xray_attenuation("CsI:Tl", 10.0, 150.0, 141, "mu")
    assert np.array_equal(a, b)


@pytest.mark.parametrize("name,formula", [("LSO", "Lu2SiO5"), ("BGO", "Bi4Ge3O12"), ("LYSO", "Lu1.8Y0.2SiO5"),
                                          ("CDWO4", "CdWO4"), ("NAI:TL", "NaI")])
def test_formula_records_use_the_mixture_rule_and_the_record_density(name, formula):
    rec = M._xray_source(name, "t")
    assert rec["kind"] == "mixture"
    assert rec["density_g_cm3"] == _sc(M._scintillator(name, "t")[0])["density_g_cm3"]
    # 質量分率の閉形式: w_i = n_i A_i / Σ n_j A_j
    toks = re.findall(r"([A-Z][a-z]?)([0-9.]*)", formula)
    z_of = {e["symbol"]: e["Z"] for e in MX.XRAY_ELEMENTS}
    mass = {z_of[s]: (float(c) if c else 1.0) * M._atomic_mass(z_of[s]) for s, c in toks}
    tot = sum(mass.values())
    got = dict(rec["composition"])
    for z, m in mass.items():
        assert got[z] == pytest.approx(m / tot, rel=1e-12)


# --------------------------------------------------------------------------- #
# dual_kvp_channels: 既定は変わらない、シンチレータの名前で選べる                   #
# --------------------------------------------------------------------------- #
def _spectra():
    return D.xray_tube_spectrum(70.0), D.xray_tube_spectrum(140.0, filtration=(("AL", 2.5), ("CU", 0.5)))


def test_dual_kvp_default_is_unchanged_from_master():
    """master 125dc785c8(2026-10-23、この変更の前)で採った値。1e-13 は CPU・numpy の版による exp の丸めの余地。"""
    ch = D.dual_kvp_channels(*_spectra())
    assert ch["response"] == {"detector": "CSI", "detector_mm": 0.6}
    E, W = ch["energy_kev"], ch["weights"]
    assert E.size == 270
    idx = [10, 40, 100, 200, 269]
    assert E[idx].tolist() == [10.25, 25.25, 55.25, 105.25, 139.75]
    np.testing.assert_allclose(W[0, idx], [1.9911892742684628e-09, 0.011646264399637613, 0.0063521841448293415,
                                           0.0, 0.0], rtol=1e-13, atol=0)
    np.testing.assert_allclose(W[1, idx], [4.577041691055595e-49, 3.6103002492024675e-06, 0.006339784652712866,
                                           0.0013171936467242268, 4.401693626799084e-06], rtol=1e-13, atol=0)
    np.testing.assert_allclose(W.sum(axis=1), [0.9616497673471098, 0.7087583712744476], rtol=1e-13, atol=0)


def test_dual_kvp_default_explicit_and_csi_tl_are_bit_identical():
    lo, hi = _spectra()
    a = D.dual_kvp_channels(lo, hi)
    b = D.dual_kvp_channels(lo, hi, detector="CSI", detector_mm=0.6)
    c = D.dual_kvp_channels(lo, hi, detector="CSI:TL", detector_mm=0.6)
    for k in ("energy_kev", "weights", "gain"):
        assert np.array_equal(a[k], b[k]) and np.array_equal(a[k], c[k]), k
    assert a["response"] == b["response"] == {"detector": "CSI", "detector_mm": 0.6}
    s = c["response"]["scintillator"]
    assert s["name"] == "CSI:TL" and s["light_yield_photons_per_mev"] == 56000.0
    assert s["light_photons_per_kev"] == 56.0 and s["emission_peak_nm"] == 550.0


def test_dual_kvp_selects_other_scintillators_by_name():
    lo, hi = _spectra()
    csi = D.dual_kvp_channels(lo, hi, detector="CSI:TL", detector_mm=0.2)
    bgo = D.dual_kvp_channels(lo, hi, detector="BGO", detector_mm=0.2)
    assert bgo["response"]["scintillator"]["name"] == "BI4GE3O12"
    # 同じ厚さなら BGO(ρ 7.13、Bi)は CsI(ρ 4.51)より高いエネルギーをよく止める
    assert bgo["weights"][1].sum() > csi["weights"][1].sum()
    gos = D.dual_kvp_channels(lo, hi, detector="GOS:TB", detector_mm=0.2)
    assert gos["response"]["scintillator"]["light_yield_photons_per_mev"] is None
    assert gos["response"]["scintillator"]["unverified"]


# --------------------------------------------------------------------------- #
# scintillator_sensor_qe                                                        #
# --------------------------------------------------------------------------- #
def test_absorption_efficiency_closed_form():
    r = D.scintillator_sensor_qe("CSI:TL", 0.6, 10.0, 150.0, 141)
    E = r["energy_kev"]
    mu_rho = np.array([M.material_xray_constants("CSI", float(e))["mu_rho_cm2_g"] for e in E])
    want = 1.0 - np.exp(-4.51 * mu_rho * 0.06)
    np.testing.assert_allclose(r["absorption_efficiency"], want, rtol=1e-12, atol=1e-15)
    # dual_kvp_channels と同じ関数(同じ値)
    assert np.array_equal(r["absorption_efficiency"], D._absorption_efficiency("CSI", 0.6, E, "t"))


def test_thick_scintillator_absorbs_everything_and_thicker_absorbs_more():
    thick = D.scintillator_sensor_qe("CSI:TL", 100.0, 10.0, 60.0, 51)
    assert np.all(thick["absorption_efficiency"] > 1.0 - 1e-12)
    a = [D.scintillator_sensor_qe("LSO", t, 20.0, 150.0, 21)["absorption_efficiency"] for t in (0.1, 0.5, 2.0, 10.0)]
    for x, y in zip(a, a[1:]):
        assert np.all(y >= x)                                   # 低いエネルギーは薄くても 1 に飽和する
        open_ = x < 1.0 - 1e-9
        assert open_.sum() >= 5 and np.all(y[open_] > x[open_])


def test_electrons_are_absorption_times_yield_times_energy_times_overlap():
    r = D.scintillator_sensor_qe("NAI:TL", 1.0, 20.0, 100.0, 9, light_collection=0.5)
    np.testing.assert_allclose(r["light_photons"], r["absorption_efficiency"] * 45000.0 * r["energy_kev"] / 1000 * 0.5,
                               rtol=1e-15)
    np.testing.assert_allclose(r["electrons"], r["light_photons"] * r["overlap"], rtol=1e-15)
    # 表から作る発光は極大の 1 本の線: 重なり = QE(λ_peak)
    qe = SR.silicon_photodiode_qe()
    assert r["overlap"] == pytest.approx(float(np.interp(410.0, qe[:, 0], qe[:, 1])), rel=1e-15)
    assert r["emission"] is None and "line" in r["emission_model"]
    assert r["sources"]["light_yield_photons_per_mev"].startswith("Berkeley Lab")


def test_emission_spectrum_is_normalised_whatever_its_scale():
    lam = np.linspace(400.0, 700.0, 601)
    g = np.exp(-0.5 * ((lam - 550.0) / 25.0) ** 2)
    a = D.scintillator_sensor_qe("CSI:TL", emission_spectrum=np.column_stack([lam, g]))
    b = D.scintillator_sensor_qe("CSI:TL", emission_spectrum=np.column_stack([lam, 37.0 * g]))
    assert a["overlap"] == pytest.approx(b["overlap"], rel=1e-14)
    em = a["emission"]
    area = float(np.sum(0.5 * (em[1:, 1] + em[:-1, 1]) * np.diff(em[:, 0])))
    assert area == pytest.approx(1.0, rel=1e-14)
    assert "given" in a["emission_model"]
    # 一定の QE なら重なりは QE そのもの(正規化の閉形式)
    flat = np.array([[300.0, 0.7], [900.0, 0.7]])
    assert D.scintillator_sensor_qe("CSI:TL", emission_spectrum=np.column_stack([lam, g]),
                                    photodetector_qe=flat)["overlap"] == pytest.approx(0.7, rel=1e-12)


def test_narrow_band_tends_to_the_line_model():
    lam = np.linspace(540.0, 560.0, 4001)
    narrow = np.exp(-0.5 * ((lam - 550.0) / 0.05) ** 2)
    line = D.scintillator_sensor_qe("CSI:TL")["overlap"]
    band = D.scintillator_sensor_qe("CSI:TL", emission_spectrum=np.column_stack([lam, narrow]))["overlap"]
    assert band == pytest.approx(line, rel=1e-5)


def test_a_table_width_turns_into_a_gaussian(monkeypatch):
    sc = dict(_sc("CSI:TL"))
    sc["emission_fwhm_nm"] = 80.0
    monkeypatch.setattr(M, "_scintillator", lambda m, op: ("CSI:TL", sc) if m == "CSI:TL" else None)
    r = D.scintillator_sensor_qe("CSI:TL")
    assert "gaussian" in r["emission_model"]
    em = r["emission"]
    half = em[em[:, 1] >= 0.5 * em[:, 1].max(), 0]
    assert half[-1] - half[0] == pytest.approx(80.0, abs=0.5)        # 格子 2001 点の刻み 0.24 nm
    area = float(np.sum(0.5 * (em[1:, 1] + em[:-1, 1]) * np.diff(em[:, 0])))
    assert area == pytest.approx(1.0, rel=1e-12)


def test_light_yield_override_for_the_material_without_one():
    with pytest.raises(ValueError, match="no verified light yield"):
        D.scintillator_sensor_qe("GD2O2S:TB")
    r = D.scintillator_sensor_qe("GD2O2S:TB", 0.2, light_yield_per_mev=1000.0)
    assert r["light_yield_photons_per_mev"] == 1000.0 and r["sources"]["light_yield_photons_per_mev"].startswith("given")


@pytest.mark.parametrize("kw", [
    {"scintillator": "N-BK7"}, {"scintillator": "CSI"}, {"scintillator": "nothing"}, {"scintillator": 3},
    {"thickness_mm": 0.0}, {"thickness_mm": -1.0}, {"thickness_mm": float("nan")}, {"thickness_mm": float("inf")},
    {"thickness_mm": 101.0}, {"e_min_kev": 0.5}, {"e_min_kev": 50.0, "e_max_kev": 50.0},
    {"e_max_kev": 2000.0}, {"n_points": 1}, {"n_points": 2.5}, {"n_points": "x"},
    {"light_collection": 0.0}, {"light_collection": 1.5}, {"light_yield_per_mev": 0.0},
    {"light_yield_per_mev": float("nan")},
    {"emission_spectrum": [[500.0, 1.0], [400.0, 1.0]]}, {"emission_spectrum": [[400.0, -1.0], [500.0, 1.0]]},
    {"emission_spectrum": [[400.0, 0.0], [500.0, 0.0]]}, {"emission_spectrum": [[100.0, 1.0], [500.0, 1.0]]},
    {"emission_spectrum": [[400.0, float("nan")], [500.0, 1.0]]}, {"emission_spectrum": [[400.0, 1.0]]},
    {"photodetector_qe": [[300.0, 1.2], [900.0, 0.5]]}, {"photodetector_qe": [[600.0, 0.5], [900.0, 0.5]]},
])
def test_fail_closed(kw):
    with pytest.raises(ValueError):
        D.scintillator_sensor_qe(**kw)


def test_emission_only_records_are_not_lens_media():
    """回帰(2026-10-23): n のデータが無いシンチレータが透過材の一覧に載り、glass_catalog が min() の空列で落ちた。"""
    import raytrace as RT
    names = RT.glass_catalog()
    assert {"BI4GE3O12", "CSI:TL", "NAI:TL"} <= set(names)
    for n in ("LU2SIO5:CE", "LU1.8Y0.2SIO5:CE", "CDWO4", "GD2O2S:TB"):
        assert n not in names
        with pytest.raises(ValueError, match="no refractive-index data"):
            RT.glass_catalog(n)
    for n in names:                                         # 一覧のどれも引ける(落ちない)
        RT.glass_catalog(n)


def test_registered_in_the_spectral_xray_ledger():
    import opstomography as T
    m = T.OPSTOMOGRAPHY["scintillator_sensor_qe"]
    assert m["category"] == "spectral_xray" and m["out"] == "table"
    assert "scintillator_sensor_qe" in D.__all__
    r = T.call("scintillator_sensor_qe")
    assert isinstance(r, dict) and math.isfinite(r["overlap"])
