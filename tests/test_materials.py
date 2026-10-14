# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""materials(材料の物性ライブラリ)の門。

真値は外から: 4 社の硝材カタログの公表値 n_d / V_d(refractiveindex.info の PROPERTIES、CC0)、
Green 2008 の Si の表の点、Johnson & Christy 1972 の Ag の点、Malitson 1965 の石英、閉形式
(Fresnel・平行平板・Sellmeier の逆算)。生成物 ``materials_data.py`` は tools/gen_material_tables.py
が RII から作るので、ここでは**その中身が一次文献の数字どおりか**を要所で押さえる。
"""
import os

import numpy as np
import pytest

import materials as M
import materials_data as MD


# --------------------------------------------------------------------------- #
# 表そのもの                                                                     #
# --------------------------------------------------------------------------- #
def test_table_has_83_materials_in_seven_classes():
    cat = M.material_table()
    assert len(cat) == 83 == len(M.MATERIALS)
    counts = {c: sum(r["class"] == c for r in cat) for c in M.CLASSES[:-1]}
    assert counts == {"glass": 46, "crystal": 12, "semiconductor": 6, "film": 4, "metal": 10, "liquid": 1, "polymer": 4}
    for r in cat:
        assert r["reference"], r["name"]                     # 出典の無い行は無い
        assert r["range_um"][0] < r["range_um"][1]
        assert r["intervals_um"][0][0] == r["range_um"][0]


def test_every_generated_record_cites_a_cc0_page():
    for rec in MD.MATERIAL_RECORDS:
        assert rec["name"] == M._key(rec["name"])
        assert rec["class"] in M.CLASSES
        for ds in rec["datasets"]:
            assert ds["page"].endswith(".yml"), (rec["name"], ds["page"])
            assert ds["reference"]
            assert ds["type"] in ("formula", "nk", "n", "k")
            lo, hi = ds["range_um"]
            assert 0 < lo < hi


def test_catalogue_nd_vd_match_the_dispersion_formula_for_all_46_glasses():
    """4 社・2 種類の式(Sellmeier 2・Schott 多項式)が公表値を 1e-4 / 0.3 で返す。"""
    for r in M.material_table("glass"):
        a = M.abbe_number(r["name"])
        assert abs(a["nd"] - a["nd_catalog"]) < 1e-4, (r["name"], a["nd"], a["nd_catalog"])
        assert abs(a["vd"] - a["vd_catalog"]) < 0.3, (r["name"], a["vd"], a["vd_catalog"])


def test_every_material_evaluates_over_every_covered_interval():
    for r in M.material_table():
        for lo, hi in r["intervals_um"]:
            d = M.material_dispersion(r["name"], lo * 1e3 * 1.0001, hi * 1e3 * 0.9999, 50)
            k = M.material_extinction(r["name"], lo * 1e3 * 1.0001, hi * 1e3 * 0.9999, 50)
            assert np.all(np.isfinite(d)) and np.all(d[:, 1] > 0), r["name"]
            assert np.all(k[:, 1] >= 0), r["name"]


def test_gaas_has_a_hole_between_its_two_sources_and_says_so():
    r = [x for x in M.material_table() if x["name"] == "GAAS"][0]
    assert len(r["intervals_um"]) == 2
    with pytest.raises(ValueError, match="no refractive-index data"):
        M.material_optical_constants("GAAS", 900.0)


# --------------------------------------------------------------------------- #
# 公表値                                                                        #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("wl_um, n_pub, k_pub", [(1.0, 3.572, 5.093e-4), (1.2, 3.520, 2.1008e-7), (0.5, 4.294, 4.4165e-2)])
def test_silicon_green_2008_table_points(wl_um, n_pub, k_pub):
    a = M.material_optical_constants("SI", wl_um * 1e3)
    assert abs(a["n"] - n_pub) < 5e-4 and abs(a["k"] / k_pub - 1) < 1e-3
    assert a["n_source"].endswith("Green-2008.yml") and a["k_source"].endswith("Green-2008.yml")


def test_silicon_beyond_green_uses_salzberg_and_reports_no_k():
    a = M.material_optical_constants("SI", 3000.0)
    assert a["n_source"].endswith("Salzberg.yml") and a["k_source"] is None and a["k"] == 0.0


def test_silver_johnson_christy_at_500nm():
    a = M.material_optical_constants("AG", 500.0)
    assert abs(a["n"] - 0.05) < 0.01 and abs(a["k"] - 3.13) < 0.05
    assert a["reflectance_normal"] > 0.97


def test_fused_silica_malitson_d_line():
    assert abs(M.material_optical_constants("SILICA", 587.56)["n"] - 1.4585) < 1e-4


def test_water_daimon_20c_and_hale_ir():
    assert abs(M.material_optical_constants("WATER", 589.0)["n"] - 1.3330) < 5e-4
    a = M.material_optical_constants("WATER", 1500.0)
    assert a["n_source"].endswith("Hale.yml") and 1e-5 < a["k"] < 1e-3
    assert a["k_source"].endswith("Segelstein.yml")                # k だけ細かい表(2026-10-15)


def test_water_nir_bands_are_resolved():
    """2026-10-15: RII の Hale & Querry の表は NIR を 0.2 µm おきにしか持たず、1.45 / 1.94 µm の帯を
    線形補間で 1/3 に潰していた。k だけ Segelstein 1981 の表にして α(1450) ≈ 31 /cm、α(1940) ≈ 124 /cm
    (Kou ら 1993 の実測 32.8 / 135 /cm と 10 % 以内)。"""
    for wl, kou_per_cm in ((1453.0, 32.8), (1930.0, 136.7)):
        k = M.material_optical_constants("WATER", wl)["k"]
        alpha_per_cm = 4.0 * np.pi * k / (wl * 1e-7)
        assert abs(alpha_per_cm / kou_per_cm - 1.0) < 0.10, (wl, alpha_per_cm)


def test_aliases_and_record_summary():
    assert M.material_record("bk7")["name"] == "N-BK7"
    assert M.material_record("silicon")["name"] == "SI"
    rec = M.material_record("N-BK7")
    assert rec["properties"]["nd"] == 1.5168 and rec["properties"]["density_kg_m3"] == 2510.0
    tabulated = [ds for ds in rec["datasets"] if "rows" in ds]
    assert len(tabulated) == 1                                   # N-BK7 の k の表
    assert all(isinstance(ds["rows"], int) for ds in tabulated)


def test_unknown_material_and_bad_inputs_are_refused():
    with pytest.raises(ValueError, match="unknown material"):
        M.material_dispersion("unobtainium")
    with pytest.raises(ValueError, match="wl_min_nm"):
        M.material_dispersion("N-BK7", 800, 400)
    with pytest.raises(ValueError, match="not extrapolated"):
        M.material_dispersion("N-BK7", 100, 200)
    with pytest.raises(ValueError, match="n_points"):
        M.material_extinction("SI", 400, 800, 1)
    with pytest.raises(ValueError, match="angle_deg"):
        M.material_reflectance("AG", angle_deg=90)
    with pytest.raises(ValueError, match="polarization"):
        M.material_reflectance("AG", polarization="circular")
    with pytest.raises(ValueError, match="material_class"):
        M.material_table("unobtainium")
    with pytest.raises(ValueError, match="record"):
        M.material_optical_constants({"name": "x"})


# --------------------------------------------------------------------------- #
# 閉形式                                                                        #
# --------------------------------------------------------------------------- #
def test_all_nine_rii_formulas_evaluate_and_formula_1_equals_formula_2_with_squared_c():
    lam = np.array([0.5, 0.8, 1.2])
    c1 = (0.0, 0.6961663, 0.0684043, 0.4079426, 0.1162414, 0.8974794, 9.896161)
    c2 = (0.0, 0.6961663, 0.0684043 ** 2, 0.4079426, 0.1162414 ** 2, 0.8974794, 9.896161 ** 2)
    assert np.allclose(M._formula(1, c1, lam), M._formula(2, c2, lam), rtol=0, atol=1e-15)
    assert np.allclose(M._formula(3, (2.25, 0.0, 2.0), lam), 1.5)            # n² = 2.25
    assert np.allclose(M._formula(4, (2.25,), lam), 1.5)
    assert np.allclose(M._formula(5, (1.5, 0.0, -2.0), lam), 1.5)
    assert np.allclose(M._formula(6, (0.5,), lam), 1.5)
    assert np.allclose(M._formula(7, (1.5,), lam), 1.5)
    a = (1.5 ** 2 - 1) / (1.5 ** 2 + 2)
    assert np.allclose(M._formula(8, (a,), lam), 1.5)
    assert np.allclose(M._formula(9, (2.25,), lam), 1.5)
    with pytest.raises(ValueError, match="formula"):
        M._formula(10, (1.0,), lam)


def test_transmittance_is_the_incoherent_slab_formula():
    T = M.material_transmittance("SI", 0.7, 1200, 1201, 2)
    a = M.material_optical_constants("SI", 1200.0)
    R = a["reflectance_normal"]
    e = np.exp(-a["alpha_per_cm"] * 0.07)
    assert abs(T[0, 1] - (1 - R) ** 2 * e / (1 - R * R * e * e)) < 1e-12
    Ti = M.material_transmittance("SI", 0.7, 1200, 1201, 2, include_fresnel=False)
    assert abs(Ti[0, 1] - e) < 1e-12
    assert M.material_transmittance("SI", 0.0, 1200, 1201, 2, include_fresnel=False)[0, 1] == 1.0
    assert M.material_transmittance("SI", 0.7, 1000, 1001, 2)[0, 1] < 0.02            # 吸収端の上
    with pytest.raises(ValueError, match="thickness_mm"):
        M.material_transmittance("SI", -1.0)


def test_reflectance_matches_glassmirror_fresnel_conductor():
    import glassmirror
    R = M.material_reflectance("AU", 500, 700, 3, angle_deg=45.0, polarization="p")
    assert len(R) == 3
    assert R.shape[1] == 2
    for wl, r in R:
        a = M.material_optical_constants("AU", wl)
        ref = glassmirror.fresnel_conductor(np.cos(np.radians(45.0)), a["n"], a["k"], "p")
        assert abs(r - float(ref)) < 1e-12
    Rs = M.material_reflectance("N-BK7", 587, 588, 2, angle_deg=0.0)[0, 1]
    n = M.material_optical_constants("N-BK7", 587.0)["n"]
    assert abs(Rs - ((n - 1) / (n + 1)) ** 2) < 1e-9                 # 誘電体は k ≈ 0 で普通の Fresnel


def test_mirror_material_ordering_from_the_tables():
    R = {m: M.material_reflectance(m, 400, 1000, 61) for m in ("AG", "AU", "AL", "CU")}
    at = lambda m, wl: float(R[m][np.argmin(np.abs(R[m][:, 0] - wl)), 1])  # noqa: E731
    assert at("AG", 500) >= 0.97 and at("AU", 500) < 0.6 and at("AU", 700) > 0.95
    al = R["AL"]
    i = int(np.argmin(al[:, 1]))
    assert 750 <= al[i, 0] <= 900


def test_plate_focus_shift_closed_form():
    p = M.plate_focus_shift("N-BK7", 3.0, 587.56, 0.2)
    n = p["n"]
    assert abs(p["paraxial_shift_mm"] - 3.0 * (1 - 1 / n)) < 1e-12
    th = np.arcsin(0.2)
    assert abs(p["marginal_shift_mm"] - 3.0 * (1 - np.cos(th) / np.sqrt(n * n - np.sin(th) ** 2))) < 1e-12
    assert p["spherical_aberration_mm"] > 0 and abs(p["optical_thickness_mm"] - 3.0 * n) < 1e-12
    with pytest.raises(ValueError, match="numerical_aperture"):
        M.plate_focus_shift("N-BK7", 3.0, 587.56, 1.0)


def test_free_carrier_absorption_schroder_1978():
    a = M.silicon_free_carrier_absorption(1e18, "n", 1000, 2000, 3)
    assert abs(a[0, 1] - 1.0) < 1e-12 and abs(a[2, 1] - 4.0) < 1e-12        # 1e-18 × 1e18 × λ²
    p = M.silicon_free_carrier_absorption(1e18, "p", 1000, 1001, 2)
    assert abs(p[0, 1] - 2.7) < 1e-12
    with pytest.raises(ValueError, match="carrier"):
        M.silicon_free_carrier_absorption(1e18, "i")


def test_thermo_optic_reference_temperature_and_derivative():
    a = M.thermo_optic_coefficient("N-BK7", 546.07, 20.0)
    assert a["reference_temperature_c"] == 20.0 and a["delta_n"] == 0.0
    b = M.thermo_optic_coefficient("S-BSL7", 546.07, 25.0)
    assert b["reference_temperature_c"] == 25.0 and b["delta_n"] == 0.0
    h = 1e-3
    fd = (M.thermo_optic_coefficient("N-BK7", 546.07, 40 + h)["delta_n"] - M.thermo_optic_coefficient("N-BK7", 546.07, 40 - h)["delta_n"]) / (2 * h)
    assert abs(fd / M.thermo_optic_coefficient("N-BK7", 546.07, 40.0)["dn_dt_per_k"] - 1) < 1e-6
    assert 1.4e-6 < M.thermo_optic_coefficient("N-BK7", 546.07, 30.0)["dn_dt_per_k"] < 1.8e-6
    with pytest.raises(ValueError, match="thermal-dispersion"):
        M.thermo_optic_coefficient("PMMA")


def test_glass_map_excludes_metals_and_abbe_refuses_them():
    gm = M.glass_map()
    assert len(gm) >= 60
    assert not any(g["class"] == "metal" for g in gm)
    assert sum(g["class"] == "glass" for g in gm) == 46
    with pytest.raises(ValueError, match="Abbe number is meaningless"):
        M.abbe_number("AG")
    pm = {g["name"]: g for g in gm}
    assert pm["PMMA"]["vd"] < 60 and pm["POLYCARBONATE"]["vd"] < 35


# --------------------------------------------------------------------------- #
# 取り込み口                                                                     #
# --------------------------------------------------------------------------- #
def test_agf_example_reproduces_the_bundled_records_exactly():
    recs = M.read_glass_catalog_agf(None)
    assert [r["name"] for r in recs] == ["N-BK7", "BSC7"]
    for r in recs:
        for wl in (400.0, 587.56, 1000.0):
            assert abs(M.material_optical_constants(r, wl)["n"] - M.material_optical_constants(r["name"], wl)["n"]) < 1e-12
    bk = recs[0]
    assert bk["properties"]["nd"] == 1.5168 and bk["properties"]["density_kg_m3"] == 2510.0
    assert bk["properties"]["reference_temperature_c"] == 20.0
    assert 1e-9 < M.material_optical_constants(bk, 400.0)["k"] < 1e-7        # IT 行から k
    assert M.thermo_optic_coefficient(bk, 546.07, 30.0)["dn_dt_per_k"] == pytest.approx(
        M.thermo_optic_coefficient("N-BK7", 546.07, 30.0)["dn_dt_per_k"], rel=1e-12)


def test_agf_reader_covers_every_zemax_formula_and_refuses_unknown(tmp_path):
    lines = ["NM G%d %d 0 1.5 60 0 1 0\nCD %s\nLD 0.4 1.0\n" % (code, code, cd) for code, cd in (
        (1, "2.25 0 0 0 0 0"), (2, "1.25 0 0 0 0 0"), (3, "1.5 0 0 0 0 0"), (4, "1.25 0 0 0 0"), (5, "1.5 0 0"),
        (6, "1.25 0 0 0 0 0 0 0"), (7, "2.25 0 0 0"), (8, "2.25 0 0 0"), (9, "2.25 0 0 0 0"), (10, "2.25 0 0 0 0 0 0 0"),
        (11, "1.25 0 0 0 0 0 0 0 0 0"), (12, "2.25 0 0 0 0 0 0 0"), (13, "2.25 0 0 0 0 0 0 0 0"))]
    p = tmp_path / "all_formulas.agf"
    p.write_text("".join(lines), encoding="utf-8")
    recs = M.read_glass_catalog_agf(str(p))
    assert len(recs) == 13
    for r in recs:
        assert abs(M.material_optical_constants(r, 600.0)["n"] - 1.5) < 1e-12, r["name"]
    bad = tmp_path / "bad.agf"
    bad.write_text("NM X 14 0 1.5 60 0 1 0\nCD 1 2 3\nLD 0.4 1.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="formula 14"):
        M.read_glass_catalog_agf(str(bad))
    nold = tmp_path / "nold.agf"
    nold.write_text("NM X 2 0 1.5 60 0 1 0\nCD 1.0 0.01 0 0 0 0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="LD"):
        M.read_glass_catalog_agf(str(nold))
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="no .agf"):
        M.read_glass_catalog_agf(str(tmp_path / "empty"))
    with pytest.raises(ValueError, match="source must be"):
        M.read_glass_catalog_agf(str(tmp_path / "dir_that_does_not_exist"))


def test_agf_reader_reads_a_directory_and_utf16(tmp_path):
    d = tmp_path / "cat"
    d.mkdir()
    (d / "a.agf").write_text(M.AGF_EXAMPLE, encoding="utf-8")
    (d / "b.AGF").write_bytes(M.AGF_EXAMPLE.encode("utf-16"))
    recs = M.read_glass_catalog_agf(str(d))
    assert [r["name"] for r in recs] == ["N-BK7", "BSC7", "N-BK7", "BSC7"]


@pytest.mark.skipif(not os.environ.get("FULLSEYE_GLASS_DIR"), reason="user glass catalogue not placed")
def test_user_glass_catalogue_agrees_with_the_bundled_cc0_records():
    recs = M.read_glass_catalog_agf(os.environ["FULLSEYE_GLASS_DIR"])
    hit = [r for r in recs if r["name"] in M.MATERIALS]
    assert hit, "no glass in the user catalogue shares a name with the bundled table"
    for r in hit:
        lo, hi = r["datasets"][0]["range_um"]
        for wl in np.linspace(max(lo, 0.4), min(hi, 1.0), 4):
            assert abs(M.material_optical_constants(r, wl * 1e3)["n"] - M.material_optical_constants(r["name"], wl * 1e3)["n"]) < 1e-4, r["name"]


def test_custom_records_round_trip_and_refuse_empty():
    custom = M.material_from_sellmeier("MY GLASS", reference="worked example")
    assert custom["name"] == "MY_GLASS" and abs(M.abbe_number(custom)["nd"] - 1.5168) < 1e-4
    with pytest.raises(ValueError, match="equal-length"):
        M.material_from_sellmeier(b=(1.0, 2.0), c=(1.0,))
    with pytest.raises(ValueError, match="range_um"):
        M.material_from_sellmeier(range_um=(2.0, 1.0))
    n = M.material_dispersion("N-SF11", 400, 1000, 31)
    k = M.material_extinction("N-SF11", 400, 1000, 31)
    cur = M.material_from_curves(n, k, "measured")
    assert abs(M.material_optical_constants(cur, 600.0)["n"] - M.material_optical_constants("N-SF11", 600.0)["n"]) < 1e-12
    assert abs(M.material_optical_constants(cur, 600.0)["k"] - M.material_optical_constants("N-SF11", 600.0)["k"]) < 1e-15
    with pytest.raises(ValueError, match="empty"):
        M.material_from_curves(np.zeros((0, 2)))
    with pytest.raises(ValueError, match="duplicate"):
        M.material_from_curves([(500, 1.5), (500, 1.6)])
    with pytest.raises(ValueError, match="k_curve"):
        M.material_from_curves(n, [(500, -1.0), (600, 0.0)])
    with pytest.raises(ValueError, match="not extrapolated"):
        M.material_optical_constants(cur, 1200.0)


# --------------------------------------------------------------------------- #
# 台帳                                                                          #
# --------------------------------------------------------------------------- #
def test_ledger_registration():
    import opsoptics
    names = [r[0] for r in opsoptics._CATALOG["matprop"]]
    assert sorted(names) == sorted(n for n in M.__all__ if n not in ("MATERIALS", "CLASSES", "AGF_EXAMPLE", "NIR_BAND_MODELS"))
    assert len(names) == 19                                   # + 近赤外の吸収帯 3 op(2026-10-15)
    for n in names:
        assert opsoptics.get(n) is getattr(M, n)
    import fullseye as fs
    assert fs.ledger.material_optical_constants("SI", 1000.0)["k"] == pytest.approx(5.093e-4, rel=1e-3)


#: 550 nm の垂直反射率の、**別の一次文献**の値(refractiveindex.info database の別ページを
#: 2026-10-14 に読んだもの)。材料表に選んだ表がこの幅から外れたら、選定を疑う。
#: 初版は W / Pt に Werner 2009 の REELS 逆算を選んでいて 0.84 / 0.93 —— この門で落ちる。
INDEPENDENT_R550 = {
    "W": (0.496, 0.537),    # Rakić 1998 LD / Werner 2009 DFT
    "PT": (0.641, 0.734),   # Rakić 1998 LD / Werner 2009 DFT(選んだ表 = Tselin 2024)
    "AG": (0.96, 0.99),
    "AL": (0.90, 0.93),
}


def test_metal_reflectance_agrees_with_an_independent_dataset():
    assert len(INDEPENDENT_R550) == 4
    for name, (lo, hi) in INDEPENDENT_R550.items():
        c = M.material_optical_constants(name, 550.0)
        r = c["reflectance_normal"]
        assert lo - 0.03 <= r <= hi + 0.03, (name, r, lo, hi)


#: 屈折率の、**材料表に選ばなかった**別の一次文献の値(refractiveindex.info database、2026-10-14 に読んだもの)。
#: 初版の Ge(膜に近い Amotchkina)は 10 µm で 3.96、SiC(スパッタ膜の Larruquert を継いだ)は 1.55 µm で 3.18 —— この門で落ちる。
INDEPENDENT_N = {
    ("GE", 10.0): 4.0025,     # Li 293 K(Burnett 4.0040、Icenogle 4.0043)
    ("GE", 1.0): 4.4259,      # Nunley(選んだ表そのもの —— 結晶の値が入っていること)
    ("SIC", 0.633): 2.6342,   # Singh の 6H 常光線(4H と 6H の常光線は 0.002 以内)
    ("SIC", 1.55): 2.5651,    # Wang の 6H 常光線
    ("SI", 1.4): 3.4896,      # Li 293 K
}


def test_semiconductor_index_agrees_with_an_independent_bulk_dataset():
    assert len(INDEPENDENT_N) == 5
    for (name, lam_um), ref in INDEPENDENT_N.items():
        n = M.material_optical_constants(name, lam_um * 1000.0)["n"]
        assert abs(n - ref) < 0.005, (name, lam_um, n, ref)


def test_two_index_sources_meet_without_a_step():
    """2 つの n の出典の継ぎ目: 生の差は 0.01 以内(別の物質をつないでいない)、混ぜた後は 1 nm 刻みの段差が隣の 3 倍以内。"""
    multi = []
    for name in M.MATERIALS:
        rec = M._record(name, "t")                           # 生のレコード(material_record は行数だけの要約)
        srcs = [d for d in rec["datasets"] if d["type"] in ("formula", "nk", "n")]
        for a, b in zip(srcs, srcs[1:]):
            end = a["range_um"][1]
            if b["range_um"][0] < end <= b["range_um"][1]:
                multi.append((name, a, b, end))
    assert len(multi) >= 3                                    # SI / GE / WATER(2026-10-14)
    for name, a, b, end in multi:
        raw = abs(float(M._n_of(a, np.array([end]))[0]) - float(M._n_of(b, np.array([end]))[0]))
        assert raw < 0.01, (name, end, raw)
        lam = np.linspace(end * 0.9, min(end * 1.05, b["range_um"][1]), 2001)
        n = M._nk(M._record(name, "t"), lam, "t")[0]
        d = np.abs(np.diff(n))
        assert d.max() < 3.0 * np.median(d) + 1e-12, (name, d.max(), np.median(d))


def test_transmittance_takes_extra_absorption_such_as_free_carriers():
    """2026-10-14: ドープの吸収を足す口。内部透過率は e^{-(α_k + α_fc) t} の閉形式、範囲の足りない曲線は拒否。"""
    clean = M.material_transmittance("SI", 0.775, 1100.0, 1500.0, 41, include_fresnel=False)
    fc = M.silicon_free_carrier_absorption(1e19, "n", 1100.0, 1500.0, 41)
    doped = M.material_transmittance("SI", 0.775, 1100.0, 1500.0, 41, include_fresnel=False, extra_absorption=fc)
    assert doped.shape == (41, 2)
    assert np.allclose(doped[:, 1], clean[:, 1] * np.exp(-fc[:, 1] * 0.0775), rtol=1e-12)
    T13 = float(np.interp(1300.0, doped[:, 0], doped[:, 1]) / np.interp(1300.0, clean[:, 0], clean[:, 1]))
    assert abs(T13 - np.exp(-1e-18 * 1e19 * 1.3 ** 2 * 0.0775)) < 1e-12        # ×0.27 at 1.3 µm
    with pytest.raises(ValueError, match="not extrapolated"):
        M.material_transmittance("SI", 0.775, 1000.0, 1500.0, 41, extra_absorption=fc)
    with pytest.raises(ValueError, match=">= 0"):
        M.material_transmittance("SI", 0.775, 1100.0, 1500.0, 41, extra_absorption=fc * np.array([1.0, -1.0]))
