# -*- coding: utf-8 -*-
"""dualxray と materials の X 線の列の門。

外部真値: NIST SRD 126 の公表値(μ/ρ)、NIST の化合物の表(混合則の独立の経路)、IEC 61267 の線質の半価層
(管の模型の合わせには使っていない)、Mayneord の水の Z_eff 7.42、閉形式(Kramers の式・CRLB・Φ(−d′/2))。
第 2 実装: 光子断面積とスペクトルの公開ライブラリ(BSD-3 / MIT)があれば照合する(無ければ飛ばす)。数字は 2026-10-15〜18 の実測。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import dualxray as D
import materials as M
import materials_xray_data as MX

# --------------------------------------------------------------------------- #
# 表(materials の X 線の列)                                                  #
# --------------------------------------------------------------------------- #
#: NIST SRD 126 のページの値(表の点ちょうど)。(材料, keV, μ/ρ cm²/g)
PUBLISHED = [
    ("CU", 8.0, 52.55), ("CU", 8.9789, 278.4), ("CU", 10.0, 215.9), ("WATER", 60.0, 0.2059),
    ("WATER", 100.0, 0.1707), ("AL", 40.0, 0.5685), ("AL", 100.0, 0.1704), ("AL", 60.0, 0.2778),
    ("PMMA", 60.0, 0.1924), ("BONE_CORTICAL_ICRU44", 60.0, 0.3148), ("WATER", 40.0, 0.2683),
]


@pytest.mark.parametrize("mat,e,v", PUBLISHED)
def test_mass_attenuation_matches_nist_published_values(mat, e, v):
    assert M.material_xray_constants(mat, e)["mu_rho_cm2_g"] == pytest.approx(v, rel=1e-12)


def test_copper_k_edge_jumps_from_38_to_278():
    below = M.material_xray_constants("CU", 8.97)["mu_rho_cm2_g"]
    at = M.material_xray_constants("CU", 8.9789)["mu_rho_cm2_g"]
    assert 38.0 < below < 39.0 and at == pytest.approx(278.4)             # 38.29 → 278.4(cm²/g。keV ではない)
    assert ("Cu", "K", 8.9789) in M.material_xray_constants("CU", 9.0)["edges"]


def test_lead_k_edge_is_inside_the_table():
    lo = M.material_xray_constants("PB", 88.0)["mu_rho_cm2_g"]
    hi = M.material_xray_constants("PB", 88.0045)["mu_rho_cm2_g"]
    assert hi / lo > 3.5                                                 # 1.91 → 7.68


@pytest.mark.parametrize("key", ["WATER", "PMMA", "POLYETHYLENE", "MUSCLE_ICRU44", "ADIPOSE_ICRU44",
                                 "BONE_CORTICAL_ICRU44", "PVC", "PTFE", "BOROSILICATE_GLASS", "CSI", "CDTE"])
def test_mixture_rule_over_elements_reproduces_nist_compound_tables(key):
    """独立の経路: NIST の化合物の表(表そのもの)と、元素の表 × ICRU 44 / NIST の組成の混合則を比べる。"""
    rec = MX.XRAY_COMPOUNDS[[c["key"] for c in MX.XRAY_COMPOUNDS].index(key)]
    comp = [(z, w) for z, w in rec["composition"]]
    src = M._xray_source({"composition": comp, "density_g_cm3": 1.0}, "t")
    edges = [r[0] for z, _ in comp for r in M._XE[z]["rows"] if r[3]]
    # 表の点(NIST が同じ規則で計算した点)では丸めの 0.2 % 以内。吸収端の ±15 % は化合物の格子に端の点が無いので外す
    nodes = np.array([r[0] for r in rec["rows"] if not r[3] and 10.0 <= r[0] <= 500.0])
    nodes = nodes[np.all(np.abs(np.log(nodes[:, None] / np.array(edges + [1e9])[None, :])) > 0.15, axis=1)]
    table = np.array([r[1] for r in rec["rows"] if r[0] in set(nodes.tolist()) and not r[3]])
    mix = M._xray_mu_rho(src, nodes, 1)
    assert np.abs(mix / table - 1.0).max() < 2e-3                         # 水 2e-4、骨 1e-3
    # 点の間は「和の補間」と「補間の和」の差で、最大 1 % 未満(水 0.55 %、40 keV 付近)
    E = np.geomspace(10.0, 500.0, 120)
    far = np.all(np.abs(np.log(E[:, None] / np.array(edges + [1e9])[None, :])) > 0.15, axis=1)
    rel = np.abs(M._xray_mu_rho(src, E, 1) / M.material_xray_attenuation(key, 10.0, 500.0, 120)[:, 1] - 1.0)
    assert rel[far].max() < 1e-2


def test_formula_and_mass_fraction_paths_agree():
    a = M.material_xray_constants("Al2O3", 60.0)["mu_rho_cm2_g"]
    b = M.material_xray_constants("SAPPHIRE", 60.0)["mu_rho_cm2_g"]
    al = 2 * M._atomic_mass(13) / (2 * M._atomic_mass(13) + 3 * M._atomic_mass(8))
    c = M.material_xray_constants({"composition": {"Al": al, "O": 1 - al}, "density_g_cm3": 3.98}, 60.0)["mu_rho_cm2_g"]
    assert a == pytest.approx(b) and b == pytest.approx(c, rel=1e-12)


def test_water_effective_z_is_742():
    r = M.material_effective_z("WATER")
    assert r["z_eff"] == pytest.approx(7.42, abs=0.005)                  # 7.4167
    assert r["electron_density_rel_water"] == pytest.approx(1.0)


def test_effective_z_of_an_element_is_its_z():
    for sym, z in (("AL", 13), ("CU", 29), ("C", 6)):
        assert M.material_effective_z(sym)["z_eff"] == pytest.approx(z)


def test_xray_column_shares_names_with_the_optical_table():
    rows = {r["name"]: r for r in M.material_xray_table()}
    for name in ("WATER", "PMMA", "SI", "CU", "SAPPHIRE", "SILICA", "GAAS"):
        assert rows[name]["optical"] is True


def test_xray_solid_agrees_with_the_electron_table_when_both_exist():
    """統合で ELECTRON_SOLID(仮想 SEM)と同じレコードに寄せる。同じ名前の組成・密度が食い違えば赤。"""
    es = getattr(M, "ELECTRON_SOLID", None)
    if not es:
        pytest.skip("ELECTRON_SOLID is not on this branch yet")
    for k, rec in M.XRAY_SOLID.items():
        if k in es and "formula" in rec:
            assert es[k]["formula"] == rec["formula"], k
            assert es[k]["density_g_cm3"] == pytest.approx(rec["density_g_cm3"], rel=0.01), k


@pytest.mark.parametrize("bad", ["N-BK7", "UNOBTAINIUM", "Xx2"])
def test_unknown_or_composition_less_materials_are_refused(bad):
    with pytest.raises(ValueError):
        M.material_xray_constants(bad, 60.0)


@pytest.mark.parametrize("e", [0.5, 2000.0, float("nan")])
def test_energy_outside_the_table_is_refused(e):
    with pytest.raises(ValueError):
        M.material_xray_constants("WATER", e)


def test_xraylib_second_implementation():
    xrl = pytest.importorskip("xraylib")
    for z, sym in ((6, "C"), (13, "AL"), (29, "CU"), (82, "PB")):
        for e in (20.0, 40.0, 60.0, 100.0, 150.0):
            ours = M.material_xray_constants(sym, e)["mu_rho_cm2_g"]
            assert ours == pytest.approx(xrl.CS_Total(z, e), rel=0.03), (sym, e)


# --------------------------------------------------------------------------- #
# 線源                                                                          #
# --------------------------------------------------------------------------- #
def test_spectrum_without_absorption_or_lines_is_kramers():
    s = D.xray_tube_spectrum(100.0, filtration=(), characteristic=False, self_absorption=False)
    E = s[:, 0]
    k = (100.0 - E) / E
    k /= k.sum() * 0.5
    assert np.abs(s[:, 1] - k).max() < 1e-12


def test_spectrum_is_normalised_and_has_tungsten_k_lines():
    s = D.xray_tube_spectrum(100.0, de_kev=0.25)
    assert (s[:, 1].sum() * 0.25) == pytest.approx(1.0)
    peaks = s[np.argsort(s[:, 1])[-2:], 0]
    assert sorted(np.round(peaks).tolist()) == [58.0, 59.0]               # Kα2 57.98 / Kα1 59.32
    assert not np.any(D.xray_tube_spectrum(60.0, de_kev=0.25)[:, 1] > 1.5 * s[:, 1].max())


#: IEC 61267:2005 の線質: (kV, 全ろ過 Al mm, 付加 Al mm, HVL mm Al)。Tanguay & Persson arXiv:2205.03362 表 I、
#: Yoshizumi & Caldas(IPEN 2009)表 2。模型の 4 定数は公開のスペクトル計算の形に合わせたもので、この値は合わせに使っていない。
IEC = [(50, 2.4, 0.0, 1.78), (70, 2.8, 0.0, 2.58), (100, 3.2, 0.0, 3.97), (150, 4.2, 0.0, 6.57),
       (50, 2.4, 10.0, 3.8), (70, 2.8, 21.0, 6.8), (100, 3.2, 34.0, 10.1), (150, 4.2, 45.0, 13.3)]


@pytest.mark.parametrize("kv,tf,add,ref", IEC)
def test_half_value_layer_matches_iec_beam_qualities(kv, tf, add, ref):
    h = D.xray_beam_quality(D.xray_tube_spectrum(kv, filtration=(("AL", tf + add),)))["hvl1_mm"]
    assert h == pytest.approx(ref, rel=0.07)                              # 最大 −5.8 %(RQA3)


def test_monoenergetic_hvl_is_ln2_over_mu():
    E = np.array([59.0, 60.0, 61.0])
    s = np.stack([E, [0.0, 1.0, 0.0]], axis=1)
    q = D.xray_beam_quality(s)
    mu = M.material_xray_constants("AL", 60.0)["mu_per_cm"]
    assert q["hvl1_mm"] == pytest.approx(10 * math.log(2) / mu, rel=1e-6)
    assert q["homogeneity"] == pytest.approx(1.0, rel=1e-6)


def test_spekpy_second_implementation():
    sp = pytest.importorskip("spekpy")
    for kv in (60, 100, 140):
        s = sp.Spek(kvp=kv, th=12, dk=0.5)
        s.filter("Al", 2.5)
        k, f = s.get_spectrum()
        m = D.xray_tube_spectrum(kv, e_min_kev=k[0] - 0.25, de_kev=0.5)
        g = np.interp(m[:, 0], k, f)
        g /= g.sum() * 0.5
        assert 0.5 * np.sum(np.abs(m[:, 1] - g)) * 0.5 < 0.08              # 全変動距離 2〜6 %


def test_opaque_filtration_is_refused_not_normalised():
    # ★探針で見つけた: Pb 50 mm の e^{-130} を正規化して「ふつうのスペクトル」を返していた
    with pytest.raises(ValueError):
        D.xray_tube_spectrum(80.0, filtration=(("PB", 50.0),))


# --------------------------------------------------------------------------- #
# チャネル・投影・分解                                                          #
# --------------------------------------------------------------------------- #
SPEC = D.xray_tube_spectrum(120.0, filtration=(("AL", 2.5), ("CU", 0.2)))
CH = D.photon_counting_channels(SPEC, (20.0, 60.0))


def test_ideal_windows_partition_the_absorbed_photons():
    qe = D._absorption_efficiency("CDTE", 2.0, CH["energy_kev"], "t")
    tot = CH["weights"].sum(axis=0)
    above = CH["energy_kev"] >= 20.0
    np.testing.assert_allclose(tot[above], (SPEC[:, 1] * 0.5 * qe)[above], rtol=1e-12)


def test_charge_sharing_moves_counts_to_the_low_window():
    cs = D.photon_counting_channels(SPEC, (20.0, 60.0), charge_sharing=0.3)
    assert cs["weights"][0].sum() > CH["weights"][0].sum() and cs["weights"][1].sum() < CH["weights"][1].sum()


def test_noise_free_decomposition_recovers_the_thicknesses():
    t = np.zeros((2, 8, 8))
    t[0] = np.linspace(1, 9, 8)[None, :]
    t[1] = np.linspace(0, 0.5, 8)[:, None]
    s = D.xray_channel_projection(t, ["WATER", "AL"], CH, 1e5, noise=False)
    r = D.basis_material_decompose(s, CH, ("WATER", "AL"), 1e5)
    assert r["n_rejected"] == 0 and np.abs(r["thickness"] - t).max() < 1e-9   # 1.3e-14


def test_decomposition_of_a_third_material_is_its_basis_equivalent():
    t = np.full((1, 1, 1), 2.0)
    s = D.xray_channel_projection(t, ["PMMA"], CH, 1e5, noise=False)
    b = D.basis_material_decompose(s, CH, ("WATER", "AL"), 1e5)["thickness"][:, 0, 0]
    mu = D._mu_table(["WATER", "AL"], CH["energy_kev"], "t")
    s2, _ = D._expected(b.reshape(2, 1, 1), mu, CH["energy_kev"], CH["weights"], CH["gain"], 1e5)
    np.testing.assert_allclose(s2, s, rtol=1e-10)
    assert b[1] < 0                                                     # PMMA は水より軽い Z: Al が負


def test_decomposition_noise_reaches_the_crlb():
    n = 4000
    t = np.zeros((2, 1, n))
    t[0], t[1] = 5.0, 0.2
    s = D.xray_channel_projection(t, ["WATER", "AL"], CH, 1e5, seed=3)
    x = D.basis_material_decompose(s, CH, ("WATER", "AL"), 1e5)["thickness"][:, 0, :]
    cr = D.basis_decomposition_crlb((5.0, 0.2), ("WATER", "AL"), CH, 1e5)
    np.testing.assert_allclose(x.std(axis=1), cr["sigma_cm"], rtol=0.05)  # 0.995 / 0.995
    assert abs(np.corrcoef(x)[0, 1] - cr["correlation"][0, 1]) < 0.03


def test_dual_kvp_channels_also_decompose_exactly():
    ch = D.dual_kvp_channels(D.xray_tube_spectrum(70.0), D.xray_tube_spectrum(140.0, filtration=(("AL", 2.5), ("CU", 0.5))))
    t = np.array([4.0, 0.3]).reshape(2, 1, 1)
    s = D.xray_channel_projection(t, ["WATER", "AL"], ch, 1e6, noise=False)
    b = D.basis_material_decompose(s, ch, ("WATER", "AL"), 1e6)["thickness"][:, 0, 0]
    np.testing.assert_allclose(b, [4.0, 0.3], atol=1e-9)


def test_r_value_of_a_thin_monoenergetic_like_slab_is_the_mu_ratio():
    # 細い窓 2 つ(狭い単色に近い)と薄い板: R → μ(E_low)/μ(E_high)
    E = np.arange(20.0, 100.0, 0.5) + 0.25
    phi = np.where((np.abs(E - 30.25) < 0.3) | (np.abs(E - 80.25) < 0.3), 1.0, 0.0)
    ch = D.photon_counting_channels(np.stack([E, phi], axis=1), (25.0, 60.0), detector_mm=50.0)
    s = D.xray_channel_projection(np.full((1, 1, 1), 0.5), ["AL"], ch, 1e6, noise=False)
    R = D.r_value_map(s, ch, 1e6, min_log=1e-3)[0, 0]
    mu = M.material_xray_attenuation("AL", 30.25, 80.25, 2, "mu")[:, 1]
    assert R == pytest.approx(mu[0] / mu[1], rel=1e-9)


def test_effective_z_map_reads_elements_exactly_and_water_near_742():
    for mat, z in (("AL", 13.0), ("SI", 14.0), ("TI", 22.0)):
        s = D.xray_channel_projection(np.full((1, 1, 1), 0.3), [mat], CH, 1e6, noise=False)
        assert D.effective_z_map(s, CH, 1e6)[0, 0] == pytest.approx(z, abs=0.02)
    s = D.xray_channel_projection(np.full((1, 1, 1), 5.0), ["WATER"], CH, 1e6, noise=False)
    assert D.effective_z_map(s, CH, 1e6)[0, 0] == pytest.approx(7.42, abs=0.1)   # 7.45


def test_separability_closed_form_matches_monte_carlo():
    r = D.dual_energy_separability("POLYETHYLENE", 0.05, "AL", None, CH, 1e4)
    assert r["d_prime_single"][-1] < 1e-9 and 0.05 < r["error_rate"] < 0.45
    n = 20000
    flat = 1e4 * CH["weights"].sum(axis=1)
    sa = D.xray_channel_projection(np.full((1, 1, n), 0.05), ["POLYETHYLENE"], CH, 1e4, seed=11)
    sb = D.xray_channel_projection(np.full((1, 1, n), r["thickness_b_cm"]), ["AL"], CH, 1e4, seed=12)
    xa, xb = (-np.log(np.maximum(s[:, 0, :], 0.5) / flat[:, None]) for s in (sa, sb))
    w = np.linalg.solve(r["cov_L"], r["L_b"] - r["L_a"])
    c = w @ (r["L_a"] + r["L_b"]) / 2
    err = 0.5 * (np.mean(w @ xa > c) + np.mean(w @ xb < c))
    assert abs(err - r["error_rate"]) < 3 * math.sqrt(r["error_rate"] * (1 - r["error_rate"]) / n) + 0.005


def test_matched_pair_has_equal_high_window_attenuation():
    # 自己整合の確認のみ(実装は L_a[-1] を目標に b の厚みを二分探索するので、これだけでは表や窓の誤りを見逃す)
    r = D.dual_energy_separability("MUSCLE_ICRU44", 4.0, "BONE_CORTICAL_ICRU44", None, CH, 1e5)
    assert r["L_a"][-1] == pytest.approx(r["L_b"][-1], rel=1e-9)


def test_matched_thickness_equals_hand_computed_beer_lambert():
    """独立の門(単色の 2 チャネル): 窓がそれぞれ 1 本の単色線なら L_c = (μ/ρ)·ρ·t が厳密(Beer–Lambert)。

    水 3 cm と同じ 100 keV の L になるアルミの厚み t_b = (μ/ρ)_水 ρ_水 t_a / ((μ/ρ)_Al ρ_Al) を、NIST SRD 126 の
    公表値(PUBLISHED と同じ 0.1707 / 0.1704 cm²/g)と密度(水 1.000、Al 2.699 g/cm³)から手で計算して比べる。"""
    mono = {"energy_kev": np.array([40.0, 100.0]), "weights": np.eye(2), "gain": np.ones(2), "mode": "photon_counting"}
    r = D.dual_energy_separability("WATER", 3.0, "AL", None, mono, 1e5)
    t_b = 0.1707 * 1.000 * 3.0 / (0.1704 * 2.699)                          # 1.1135 cm
    assert r["thickness_b_cm"] == pytest.approx(t_b, rel=1e-3)             # 密度は 4 桁なので 1e-3
    assert r["L_a"][1] == pytest.approx(0.1707 * 3.0, rel=1e-12)           # 水の 100 keV
    assert r["L_a"][0] == pytest.approx(0.2683 * 3.0, rel=1e-12)           # 水の 40 keV
    assert r["L_b"][1] == pytest.approx(r["L_a"][1], rel=1e-9)
    assert r["L_b"][0] == pytest.approx(0.5685 * 2.699 * r["thickness_b_cm"], rel=1e-3)   # Al の 40 keV


# --------------------------------------------------------------------------- #
# fail-closed(壊して確かめる探針)                                              #
# --------------------------------------------------------------------------- #
def test_zero_count_pixels_are_rejected_not_filled():
    s = D.xray_channel_projection(np.full((2, 2, 2), 0.5), ["WATER", "AL"], CH, 1e4, seed=1)
    s[:, 0, 0] = 0.0
    r = D.basis_material_decompose(s, CH, ("WATER", "AL"), 1e4)
    assert r["n_rejected"] == 1 and np.isnan(r["thickness"][:, 0, 0]).all() and np.isfinite(r["thickness"][:, 1, 1]).all()


def test_runaway_pixels_are_rejected():
    s = D.xray_channel_projection(np.full((2, 1, 1), 0.5), ["WATER", "AL"], CH, 1e4, noise=False)
    s[0] *= 1e-6                                                        # 低い窓だけ 1e-6 倍: 解が飛ぶ
    r = D.basis_material_decompose(s, CH, ("WATER", "AL"), 1e4)
    assert r["n_rejected"] == 1


@pytest.mark.parametrize("call", [
    lambda: D.basis_material_decompose(np.ones((1, 2, 2)), CH, ("WATER", "AL")),          # 窓 1 つで基底 2 つ
    lambda: D.basis_decomposition_crlb((1.0, 1.0), ("WATER", "WATER"), CH),               # 同じ基底 2 回
    lambda: D.photon_counting_channels(SPEC, (20.0, 200.0)),                               # 光子の来ない窓
    lambda: D.photon_counting_channels(SPEC, (60.0, 20.0)),                                # 逆順のしきい値
    lambda: D.xray_tube_spectrum(10.0),                                                    # 範囲外の管電圧
    lambda: D.xray_tube_spectrum(80.0, anode="MO"),                                        # 知らない陽極
    lambda: D.xray_channel_projection(-np.ones((1, 2, 2)), ["WATER"], CH),                 # 負の厚さ
    lambda: D.xray_channel_projection(np.ones((2, 2, 2)), ["WATER"], CH),                  # 材料の数と合わない
    lambda: D.r_value_map(np.ones((2, 2, 2)), CH, low=1, high=1),                          # 同じ窓
    lambda: D.r_value_map(np.ones((2, 2, 2)), CH, low=0.5),                                # 窓の番号が整数でない
    lambda: D.effective_z_map(np.ones((2, 2, 2)), CH, high=5),                             # 窓の外
    lambda: D.xray_channel_projection(np.ones((1, 2, 2)), ["N-BK7"], CH),                  # 組成の無い硝材
])
def test_refusals(call):
    with pytest.raises(ValueError):
        call()


def test_registry_lists_the_new_ops_and_they_exist():
    import opstomography as T
    names = T.list_ops("spectral_xray")
    assert len(names) == 14 and not T.missing()
    out = T.call("basis_material_decompose", np.ones((2, 2, 2)) * 1e4, None, ("WATER", "AL"), 1e5)
    assert isinstance(out, list) and len(out) == 2 and out[0].shape == (2, 2)     # 宣言型 images = 基底の厚みの並び
