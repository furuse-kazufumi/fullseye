# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""シンチレータ・蛍光体の発光の列(materials)と、シンチレータ積層のセンサ(dualxray.scintillator_sensor_qe)。

真値の門:
  * 吸収効率は閉形式 1 − exp(−ρ (μ/ρ) t)(μ/ρ は NIST SRD 126 の列)、厚さ → ∞ で 1、厚さに単調。
  * 発光スペクトルは ∫ S dλ = 1 に正規化される(倍率に依らない)。細いガウスの極限は「極大の 1 本の線」に戻る。
  * 発光の成分(2026-10-24): エネルギー軸のガウスは波長軸でも面積 1(ヤコビアン hc/λ²)、重なりはどちらの軸で
    積分しても同じ、線の束は Σ wᵢ·QE(λᵢ)(重みの和が 1 でない合成も、解析式の QE で独立に数えた値と一致)、
    QE の山頂(480 nm)では線が帯より大きく出る(向きだけが真値の門。大きさ BGO +6.6 % / CdWO4 +4.6 % は
    回帰の定数)。
  * エネルギー保存: 発光の光子のエネルギーの和は吸収したエネルギーを超えない(Y·⟨E_ph⟩ ≤ 10⁶ eV/MeV)。
    超える光収率は拒否し、材料表の全材料が下回る。
  * 光収率の幅の両端の電子の数は、値に比例する。
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
FIELDS = ("density_g_cm3", "light_yield_photons_per_mev", "light_yield_range_photons_per_mev", "decay_time_ns",
          "emission_peak_nm", "emission_components", "refractive_index_at_peak", "xray_material")


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
    # 一次情報で確かめられなかったもの(推測で埋めない): GOS の光収率、CsI:Tl と NaI:Tl の発光の形
    assert _sc("GD2O2S:TB")["light_yield_photons_per_mev"] is None
    assert [n for n in SCINT if _sc(n)["emission_components"] is None] == ["CSI:TL", "NAI:TL"]


def test_published_values_as_copied():
    """写した公表値の回帰(PDG 2024 表 35.4 / LBNL の行 / Tang 2023 / de Haas 2008 / Bardelli 2006)。

    値を変えるなら出典も読み直すこと。2026-10-24: LYSO の光収率 34,000(LBNL の Pidol2004 の行)→ 27,000
    (de Haas & Dorenbos 2008 Table II、APD 26,000 / PD 27,000)、CdWO4 の発光の極大 495 → 480 nm
    (Bardelli 2006 Table 1。495 は Moszynski2005 の行だけ)。
    """
    want = {  # (密度, 光収率, 減衰 ns, 極大 nm)
        "CSI:TL": (4.51, 56000.0, 1220.0, 550.0), "NAI:TL": (3.67, 45000.0, 245.0, 410.0),
        "BI4GE3O12": (7.13, 8500.0, 300.0, 480.0), "LU2SIO5:CE": (7.40, 27000.0, 40.0, 402.0),
        "LU1.8Y0.2SIO5:CE": (7.1, 27000.0, 41.0, 397.0), "CDWO4": (7.9, 27000.0, 12000.0, 480.0),
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
    {"emission_geometry": "surface"},
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


# --------------------------------------------------------------------------- #
# 光収率の幅と発光の成分(2026-10-24)                                            #
# --------------------------------------------------------------------------- #
QE = SR.silicon_photodiode_qe()
LQ, Q = QE[:, 0], QE[:, 1]


def _qe(lam):
    return float(np.interp(lam, LQ, Q))


def test_light_yield_ranges_only_where_the_spread_was_read():
    """幅は文献のばらつきの理由を読んだ材料だけ(CdWO4: 絶対値の Holl 1988〜Dorenbos 1995、LYSO: de Haas 2008 の APD/PD)。"""
    want = {"CDWO4": (20000.0, 28000.0), "LU1.8Y0.2SIO5:CE": (26000.0, 27000.0)}
    for n in SCINT:
        sc = _sc(n)
        rng = sc["light_yield_range_photons_per_mev"]
        assert rng == want.get(n), n
        if rng is not None:
            assert rng[0] <= sc["light_yield_photons_per_mev"] <= rng[1]
            assert sc["sources"]["light_yield_range_photons_per_mev"]
    # CdWO4 の出典は条件の分かる書き方(光電子数 → 光子数の換算と、低い値の理由)
    src = _sc("CDWO4")["sources"]["light_yield_photons_per_mev"]
    for frag in ("6,500 +- 200 phe/MeV", "27,400 ph/MeV", "arXiv:1001.5461", "Holl", "20,000", "Dorenbos", "28,000",
                 "shaping"):
        assert frag in src, frag
    assert "de Haas" in _sc("LU1.8Y0.2SIO5:CE")["sources"]["light_yield_photons_per_mev"]
    assert "not stated" in _sc("LU1.8Y0.2SIO5:CE")["sources"]["light_yield_photons_per_mev"]


def test_emission_components_are_well_formed():
    geos = {"surface", "thick_crystal_transmission"}
    for n in SCINT:
        comps = _sc(n)["emission_components"]
        if n in ("CSI:TL", "NAI:TL"):
            assert comps is None and "emission_components" in _sc(n)["unverified"]
            assert _sc(n)["emission_default_geometry"] is None
            continue
        sums = {}
        for c in comps:
            assert c["geometry"] in geos and c["excitation"] in ("xray", "gamma", "uv")
            assert c["digitized_from_figure"] is True and c["source"]
            sums[c["geometry"]] = sums.get(c["geometry"], 0.0) + c["weight"]
        assert all(abs(v - 1.0) < 1e-12 for v in sums.values()), (n, sums)
        assert _sc(n)["emission_default_geometry"] == ("surface" if "surface" in sums else next(iter(sums)))
    assert {c["geometry"] for c in _sc("LU2SIO5:CE")["emission_components"]} == geos
    assert [c["center_nm"] for c in _sc("GD2O2S:TB")["emission_components"]] == [411.0, 490.0, 545.0, 587.0, 620.0,
                                                                                  667.0]
    assert all(c["fwhm_ev"] is None for c in _sc("GD2O2S:TB")["emission_components"])
    assert [(c["center_nm"], c["fwhm_ev"]) for c in _sc("BI4GE3O12")["emission_components"]] == [(480.0, 0.70)]
    assert [(c["center_nm"], c["fwhm_ev"]) for c in _sc("CDWO4")["emission_components"]] == [(480.0, 0.58)]


@pytest.mark.parametrize("center_nm,fwhm_ev", [(480.0, 0.70), (402.0, 0.50), (550.0, 0.05), (900.0, 0.4)])
def test_component_gaussian_has_unit_area_in_wavelength(center_nm, fwhm_ev):
    """エネルギー軸で面積 1 のガウスは、ヤコビアン hc/λ² を掛けた波長の密度でも面積 1。"""
    ce = D.HC_EV_NM / center_nm
    lam = D._component_grid(ce, fwhm_ev, "t")
    area = float(np.trapezoid(D._gauss_ev_per_nm(lam, ce, fwhm_ev), lam))
    assert area == pytest.approx(1.0, abs=1e-6)
    # ヤコビアンを落とすと面積は 1 にならない(壊して赤になることの確認)
    sig = fwhm_ev / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    no_jac = np.exp(-0.5 * ((D.HC_EV_NM / lam - ce) / sig) ** 2) / (sig * math.sqrt(2.0 * math.pi))
    assert abs(float(np.trapezoid(no_jac, lam)) - 1.0) > 0.1
    # 帯の裾が光子のエネルギー 0 に届く(幅が広すぎる)成分は拒否する
    with pytest.raises(ValueError, match="zero photon energy"):
        D._component_grid(D.HC_EV_NM / 900.0, 0.9, "t")


@pytest.mark.parametrize("center_nm,fwhm_ev", [(480.0, 0.70), (402.0, 0.50), (453.0, 0.63)])
def test_overlap_is_the_same_on_the_energy_and_the_wavelength_axis(center_nm, fwhm_ev):
    """∫ g_λ(λ) QE(λ) dλ = ∫ g_E(E) QE(hc/E) dE(ヤコビアンの確認)。"""
    ce = D.HC_EV_NM / center_nm
    comps = [{"center_nm": center_nm, "fwhm_ev": fwhm_ev, "weight": 1.0, "digitized_from_figure": True,
              "source": "t"}]
    _, ov_lam, _ = D._emission_components_overlap(comps, LQ, Q, "t")
    sig = fwhm_ev / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    E = np.linspace(ce - 6 * sig, ce + 6 * sig, 200001)
    gE = np.exp(-0.5 * ((E - ce) / sig) ** 2) / (sig * math.sqrt(2.0 * math.pi))
    ov_E = float(np.trapezoid(gE * np.interp(D.HC_EV_NM / E, LQ, Q), E) / np.trapezoid(gE, E))
    assert ov_lam == pytest.approx(ov_E, rel=2e-5)


def test_single_gaussian_tends_to_the_line_as_the_width_goes_to_zero():
    errs = []
    for fw in (0.3, 0.03, 0.003, 0.0003):
        comps = [{"center_nm": 480.0, "fwhm_ev": fw, "weight": 1.0, "digitized_from_figure": False, "source": "t"}]
        errs.append(abs(D._emission_components_overlap(comps, LQ, Q, "t")[1] - _qe(480.0)))
    assert errs[-1] < 1e-5 * _qe(480.0)
    assert errs == sorted(errs, reverse=True)


def test_line_bundle_overlap_is_the_weighted_sum_of_qe():
    """GOS:Tb の線の束: Q̄ = Σ wᵢ·QE(λᵢ)(J. Inorg. Mater. 2023 の図から読んだ割合)。"""
    r = D.scintillator_sensor_qe("GD2O2S:TB", 0.2, light_yield_per_mev=1.0)
    comps = _sc("GD2O2S:TB")["emission_components"]
    want = sum(c["weight"] * _qe(c["center_nm"]) for c in comps)
    assert r["overlap"] == pytest.approx(want, rel=1e-14)
    assert r["emission"] is None and "line bundle" in r["emission_model"]
    assert [round(x["weight"], 12) for x in r["emission_components"]] == [0.10, 0.12, 0.53, 0.13, 0.08, 0.04]
    # 545 nm の 1 本の線で近似すると Si の QE の山の上で大きく出る
    assert _qe(545.0) > r["overlap"]


@pytest.mark.parametrize("name,band_over_line", [("BI4GE3O12", 0.066), ("CDWO4", 0.046)])
def test_the_line_model_overestimates_on_the_top_of_the_qe_hill(name, band_over_line):
    """QE が上に凸の山頂付近(480 nm)では、極大の線は帯の重なりより大きい。

    向き(線 > 帯)は QE が上に凸であることから出る真値の門。大きさ(BGO +6.6 %、CdWO4 +4.6 %)は調査のときに
    同じ模型で計算した値で、独立の真値ではなく**回帰の定数**(模型・QE の曲線を変えたら読み直す)。
    """
    r = D.scintillator_sensor_qe(name)
    line = _qe(r["emission_peak_nm"])
    assert "Gaussian in energy" in r["emission_model"]
    assert line > r["overlap"]
    assert line / r["overlap"] - 1.0 == pytest.approx(band_over_line, abs=0.002)


def test_electrons_at_the_ends_of_the_light_yield_range_are_proportional():
    r = D.scintillator_sensor_qe("CDWO4", 0.5, 20.0, 150.0, 15)
    lo, hi = r["electrons_light_yield_range"]
    assert r["light_yield_range_photons_per_mev"] == (20000.0, 28000.0)
    np.testing.assert_allclose(lo, r["electrons"] * 20000.0 / 27000.0, rtol=1e-14)
    np.testing.assert_allclose(hi, r["electrons"] * 28000.0 / 27000.0, rtol=1e-14)
    np.testing.assert_allclose(lo, r["absorption_efficiency"] * 20000.0 * r["energy_kev"] / 1000 * r["overlap"],
                               rtol=1e-13)
    assert r["sources"]["light_yield_range_photons_per_mev"].startswith("absolute")
    # 幅の無い材料と、光収率を上書きしたときは None
    assert D.scintillator_sensor_qe("CSI:TL")["electrons_light_yield_range"] is None
    assert D.scintillator_sensor_qe("CDWO4", light_yield_per_mev=1e4)["electrons_light_yield_range"] is None


def test_lso_geometry_is_chosen_by_argument_and_defaults_to_the_surface():
    surf = D.scintillator_sensor_qe("LSO")
    thick = D.scintillator_sensor_qe("LSO", emission_geometry="thick_crystal_transmission")
    assert surf["emission_geometry"] == "surface" and thick["emission_geometry"] == "thick_crystal_transmission"
    assert surf["overlap"] == D.scintillator_sensor_qe("LSO", emission_geometry="surface")["overlap"]
    # 厚い結晶では自己吸収で極大が 453 nm へ動き、Si の QE が高い側へ寄る
    assert thick["overlap"] > surf["overlap"]
    assert thick["emission_components"][0]["center_nm"] == 453.0
    assert "gamma" in thick["emission_model"] and "uv" in surf["emission_model"]
    # CdWO4 は厚い結晶の測定しか無いので、既定はそれ
    assert D.scintillator_sensor_qe("CDWO4")["emission_geometry"] == "thick_crystal_transmission"
    lyso = D.scintillator_sensor_qe("LYSO")
    assert "assumed" in lyso["emission_model"] and all(c["weight_assumed"] for c in lyso["emission_components"])


@pytest.mark.parametrize("kw", [
    {"scintillator": "CDWO4", "emission_geometry": "surface"},
    {"scintillator": "CSI:TL", "emission_geometry": "surface"},
    {"scintillator": "LSO", "emission_geometry": "bulk"},
    {"scintillator": "LSO", "emission_geometry": 3},
    {"scintillator": "LSO", "emission_geometry": "surface",
     "emission_spectrum": [[380.0, 0.0], [400.0, 1.0], [420.0, 0.0]]},
])
def test_emission_geometry_fails_closed(kw):
    with pytest.raises(ValueError):
        D.scintillator_sensor_qe(**kw)


def test_band_outside_the_qe_range_is_refused():
    narrow = np.array([[470.0, 0.5], [490.0, 0.5]])
    with pytest.raises(ValueError, match="outside the photodetector QE range"):
        D.scintillator_sensor_qe("BGO", photodetector_qe=narrow)
    with pytest.raises(ValueError, match="outside the photodetector QE range"):
        D.scintillator_sensor_qe("GOS:TB", light_yield_per_mev=1.0, photodetector_qe=narrow)


# --------------------------------------------------------------------------- #
# 重みの和が 1 でない合成を、独立に数えた値と比べる(2026-10-24)                    #
# --------------------------------------------------------------------------- #
def _analytic_qe(lam):
    """解析式の QE(λ)(実装の np.interp を通さずに真値を出すため)。300〜1000 nm で 0.2〜0.8。"""
    return 0.5 + 0.3 * np.sin(np.pi * (np.asarray(lam, dtype=np.float64) - 300.0) / 700.0)


#: 解析式の QE を 0.05 nm 刻みで標本化した曲線(区分線形の補間誤差は 1e-8 未満)
QE_AN = np.column_stack([np.linspace(300.0, 1000.0, 14001), _analytic_qe(np.linspace(300.0, 1000.0, 14001))])


def test_unnormalised_mixed_components_match_an_independent_sum():
    """重み 2 : 3 : 1(和 6)の 線・エネルギー軸のガウス・線 —— 期待値は解析式の QE とエネルギー軸の求積で独立に。"""
    comps = [{"center_nm": 545.0, "fwhm_ev": None, "weight": 2.0, "digitized_from_figure": False, "source": "t"},
             {"center_nm": 450.0, "fwhm_ev": 0.5, "weight": 3.0, "digitized_from_figure": False, "source": "t"},
             {"center_nm": 600.0, "fwhm_ev": None, "weight": 1.0, "digitized_from_figure": False, "source": "t"}]
    pairs, ov, rows = D._emission_components_overlap(comps, QE_AN[:, 0], QE_AN[:, 1], "t")
    # 帯の部分: エネルギー軸で ±6σ を 20 万点の台形(実装は波長軸の格子)
    ce = D.HC_EV_NM / 450.0
    sig = 0.5 / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    E = np.linspace(ce - 6 * sig, ce + 6 * sig, 200001)
    gE = np.exp(-0.5 * ((E - ce) / sig) ** 2)
    q_band = float(np.trapezoid(gE * _analytic_qe(D.HC_EV_NM / E), E) / np.trapezoid(gE, E))
    want = (2.0 * float(_analytic_qe(545.0)) + 3.0 * q_band + 1.0 * float(_analytic_qe(600.0))) / 6.0
    assert ov == pytest.approx(want, rel=1e-7)
    # 正規化を忘れた和(Σ wᵢ Q̄ᵢ をそのまま)とは 6 倍違う —— 壊したら赤になる
    assert abs(ov * 6.0 - want) > 1.0
    assert [r["weight"] for r in rows] == pytest.approx([2 / 6, 3 / 6, 1 / 6], rel=1e-15)
    # 返す pairs は帯の部分だけで、面積は帯の重みの割合 3/6
    assert float(np.trapezoid(pairs[:, 1], pairs[:, 0])) == pytest.approx(0.5, abs=1e-6)


def test_line_bundle_through_the_op_matches_the_analytic_qe():
    """GOS:Tb の線の束を公開の op に解析式の QE で通す: Q̄ = Σ wᵢ·f(λᵢ)(f は解析式、補間を通さない)。"""
    r = D.scintillator_sensor_qe("GD2O2S:TB", 0.2, light_yield_per_mev=1.0, photodetector_qe=QE_AN)
    table = [(411.0, 0.10), (490.0, 0.12), (545.0, 0.53), (587.0, 0.13), (620.0, 0.08), (667.0, 0.04)]
    want = sum(w * float(_analytic_qe(c)) for c, w in table) / sum(w for _, w in table)
    assert r["overlap"] == pytest.approx(want, rel=1e-8)


# --------------------------------------------------------------------------- #
# エネルギー保存: 光収率の物理上限(2026-10-24)                                   #
# --------------------------------------------------------------------------- #
def _mean_photon_ev(r):
    """返り値から発光の光子のエネルギーの平均 [eV] を独立に数える(波長軸の pairs を ∫ S·hc/λ dλ で)。"""
    comps = r["emission_components"]
    if comps is None:
        if r["emission"] is not None:
            lam, S = r["emission"][:, 0], r["emission"][:, 1]
            return float(np.trapezoid(S * D.HC_EV_NM / lam, lam) / np.trapezoid(S, lam))
        return D.HC_EV_NM / r["emission_peak_nm"]
    band = [c for c in comps if c["kind"] != "line"]
    e = sum(c["weight"] * D.HC_EV_NM / c["center_nm"] for c in comps if c["kind"] == "line")
    if band:
        lam, S = r["emission"][:, 0], r["emission"][:, 1]
        e += float(np.trapezoid(S * D.HC_EV_NM / lam, lam))      # 帯の部分の面積は帯の重みの和
    return e


def test_material_table_light_yields_obey_energy_conservation():
    """材料表の全材料で Y·⟨E_ph⟩ < 10⁶ eV/MeV(光のエネルギーが吸収したエネルギーを超えない)。

    材料表に禁制帯幅は無いので、Y ≤ 10⁶/(β·E_g) の門は置けない(エネルギー保存だけ)。
    """
    seen = 0
    for n in SCINT:
        y = _sc(n)["light_yield_photons_per_mev"]
        if y is None:
            continue
        r = D.scintillator_sensor_qe(n)
        eff = y * _mean_photon_ev(r) / 1e6          # 固有の変換効率(吸収したエネルギーのうち光になる割合)
        assert 0.0 < eff < 1.0, (n, eff)
        seen += 1
    assert seen == 6


@pytest.mark.parametrize("name", ["BI4GE3O12", "CSI:TL", "LU2SIO5:CE", "LU1.8Y0.2SIO5:CE", "GD2O2S:TB"])
def test_light_yield_above_energy_conservation_is_refused(name):
    """上書きの光収率が 10⁶/⟨E_ph⟩ を超えたら ValueError(fail-closed)。境界の直下は通る。"""
    r = D.scintillator_sensor_qe(name, light_yield_per_mev=1000.0)
    y_max = 1e6 / _mean_photon_ev(r)
    ok = D.scintillator_sensor_qe(name, light_yield_per_mev=0.999 * y_max)
    assert ok["light_yield_photons_per_mev"] == pytest.approx(0.999 * y_max)
    with pytest.raises(ValueError, match="energy conservation"):
        D.scintillator_sensor_qe(name, light_yield_per_mev=1.001 * y_max)
    with pytest.raises(ValueError, match="energy conservation"):
        D.scintillator_sensor_qe(name, light_yield_per_mev=9e5)


def test_energy_conservation_uses_the_given_emission_spectrum():
    """``emission_spectrum`` を渡したときは、その平均の光子のエネルギーで上限を決める。"""
    lam = np.linspace(380.0, 420.0, 401)
    spec = np.column_stack([lam, np.exp(-0.5 * ((lam - 400.0) / 5.0) ** 2)])
    e_mean = float(np.trapezoid(spec[:, 1] * D.HC_EV_NM / lam, lam) / np.trapezoid(spec[:, 1], lam))
    y_max = 1e6 / e_mean                          # ≈ 3.23e5(400 nm の光子は 3.10 eV)
    D.scintillator_sensor_qe("BGO", light_yield_per_mev=0.999 * y_max, emission_spectrum=spec)
    with pytest.raises(ValueError, match="energy conservation"):
        D.scintillator_sensor_qe("BGO", light_yield_per_mev=1.001 * y_max, emission_spectrum=spec)


# --------------------------------------------------------------------------- #
# 材料表の注記(2026-10-24)                                                     #
# --------------------------------------------------------------------------- #
def test_notes_say_where_a_value_needs_care_and_reach_the_op():
    for n in SCINT:
        for note in _sc(n)["notes"]:
            assert note.split(":", 1)[0] in FIELDS, (n, note)
    gos = " ".join(_sc("GD2O2S:TB")["notes"])
    # 密度は塊の値(粉末・セラミックでは充填率で下がる)
    assert "bulk" in gos and "packing fraction" in gos and "7.44" in gos
    # 線の位置: 図から読んだ 490/587/620 と、Tang 2023 の 494/589/623 は別の測定
    assert all(x in gos for x in ("490", "587", "620", "494", "589", "623", "different measurement"))
    assert "approximation" in " ".join(_sc("LU2SIO5:CE")["notes"])
    assert _sc("CSI:TL")["notes"] == ()
    r = D.scintillator_sensor_qe("GD2O2S:TB", 0.2, light_yield_per_mev=1000.0)
    assert r["notes"] == _sc("GD2O2S:TB")["notes"]
    lo, hi = _spectra()
    ch = D.dual_kvp_channels(lo, hi, detector="GD2O2S:TB", detector_mm=0.2)
    assert ch["response"]["scintillator"]["notes"] == _sc("GD2O2S:TB")["notes"]
