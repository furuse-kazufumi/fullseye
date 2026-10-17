# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""仮想 SEM(電子と固体の相互作用のモンテカルロ)の門 —— 外部の実測値で採点する。

採点の相手は、どれもこの repo の外で決まった数:

  * 反射電子係数 η(Z, E): Joy の電子-固体相互作用データベース(rev. 04-02、2004)に
    収録された実測(Hunger & Küchler 1979 / Bishop 1963 / Heinrich 1966 / Reimer & Tollkamp
    1980 / Neubert)。値は事実として引用する(データベースの文書そのものは同梱しない)。
  * 傾けた試料の η(θ): Arnal ほか 1969 の (1 + cos θ)^(−9/√Z)。
  * 電子の到達深さ: Kanaya-Okayama 1972 の R = 0.0276 A E^1.67 / (Z^0.889 ρ) µm。
  * 二次電子の収率の形: Lin & Joy 2005 の普遍曲線(式 12)と、同じ論文の Table 1 の Emax。

どれも 1 本ずつ「壊して確かめる探針」を添える(断面積を遮蔽ラザフォードに戻す /
阻止能を半分にする / 脱出深さを 10 倍にする —— 門がそれを落とすこと)。
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import materials as MT                                            # noqa: E402
import semsim as SM                                               # noqa: E402

#: Joy のデータベース(rev. 04-02)に収録された η の実測。(材料, keV) → 値の列。
ETA_MEASURED = {
    ("C", 5): (0.082, 0.085), ("C", 20): (0.049, 0.061, 0.060),
    ("AL", 5): (0.153, 0.186), ("AL", 20): (0.148,),
    ("SI", 5): (0.188, 0.206), ("SI", 20): (0.159, 0.194, 0.164),
    ("CU", 5): (0.323,), ("CU", 20): (0.306, 0.309),
    ("AG", 5): (0.393, 0.418), ("AG", 20): (0.398, 0.408),
    ("W", 5): (0.449, 0.472), ("W", 20): (0.469, 0.494),
    ("AU", 5): (0.469, 0.489), ("AU", 20): (0.485, 0.506, 0.516),
}
#: 実測の幅の外側に許す余裕(実測どうしの散らばりと同じ桁、MC の 95 % 区間 ≈ 0.02 を含む)。
ETA_MARGIN = 0.04


def _eta(material, e_kev, model="browning", n=2500, tilt=0.0):
    m = SM._electron_material(material, "test", model)
    geom = SM._ProfileGeom([0.0, 1.0], [0.0, 0.0], coll_window=1.0)
    r = SM._transport([m, m], geom, np.zeros(n), np.zeros(n), e_kev, np.random.default_rng(7), tilt_deg=tilt)
    return float(r["bse"].mean())


def _eta_misses(model):
    out = []
    for (mat, e), vals in ETA_MEASURED.items():
        eta = _eta(mat, float(e), model)
        lo, hi = min(vals) - ETA_MARGIN, max(vals) + ETA_MARGIN
        if not (lo <= eta <= hi):
            out.append((mat, e, round(eta, 3), (round(lo, 3), round(hi, 3))))
    return out


# --------------------------------------------------------------------------- #
# 1. 材料表(Z・A・密度は materials に寄せる)                                     #
# --------------------------------------------------------------------------- #
def test_the_material_table_gives_mass_fractions_that_sum_to_one():
    for name in MT.ELECTRON_SOLID:
        r = MT.material_electron_properties(name)
        assert sum(c[2] for c in r["composition"]) == pytest.approx(1.0, abs=1e-12), name
        assert r["density_g_cm3"] > 0 and r["se_escape_nm"] > 0 and r["se_energy_ev"] > 0
    # SiO2 の Si の質量分率 = 28.085 / 60.083(原子量から)。
    r = MT.material_electron_properties("FUSED_SILICA")
    w_si = [c[2] for c in r["composition"] if c[0] == 14][0]
    assert w_si == pytest.approx(28.085 / (28.085 + 2 * 15.999), abs=1e-9)
    assert r["insulator"] and r["name"] == "SILICA"
    assert MT.material_electron_properties("carbon")["name"] == "C"
    with pytest.raises(ValueError):
        MT.material_electron_properties("UNOBTAINIUM")


def test_the_lin_joy_constants_are_the_published_table():
    """7 元素の λ・ε・δmax・Emax は Lin & Joy 2005 Table 1 のまま(写し間違いの門)。"""
    want = {"C": (2.5, 80, 1.06, 0.40), "AL": (1.7, 32, 2.00, 0.40), "SI": (2.7, 90, 0.89, 0.45),
            "CU": (0.6, 35, 1.53, 0.40), "AG": (1.0, 50, 1.43, 0.60), "W": (0.2, 20, 1.06, 0.25),
            "AU": (0.5, 35, 1.28, 0.50)}
    for k, (lam, eps, dm, em) in want.items():
        r = MT.material_electron_properties(k)
        assert (r["se_escape_nm"], r["se_energy_ev"]) == (lam, eps), k
        assert r["se_ref"] == (dm, em), k


# --------------------------------------------------------------------------- #
# 2. 外部真値: η(Z, E)・η(θ)・到達深さ・二次電子の普遍曲線                         #
# --------------------------------------------------------------------------- #
def test_backscatter_coefficient_matches_measurements_across_z_and_energy():
    """7 元素 × 5 / 20 keV の η が、実測の幅 ± 0.04 に入る(Browning の断面積)。"""
    misses = _eta_misses("browning")
    assert misses == [], "実測の幅から外れた η: %r" % misses


def test_probe_screened_rutherford_overshoots_heavy_elements():
    """★探針: 断面積を遮蔽ラザフォードに戻すと、重元素の η が実測の幅から外れる(門に歯がある)。"""
    misses = _eta_misses("rutherford")
    heavy = [m for m in misses if m[0] in ("AG", "W", "AU")]
    assert heavy, "遮蔽ラザフォードでも全部通った —— 門が断面積の違いを見分けていない"
    assert all(m[2] > m[3][1] for m in heavy), "外れ方が過大でない: %r" % heavy


def test_tilted_backscatter_follows_arnal():
    """傾けた試料の η(θ) は (1 + cos θ)^(−9/√Z) に 0.05 以内で沿う(Si と Cu、10 keV)。"""
    for mat, z in (("SI", 14), ("CU", 29)):
        for th in (0.0, 45.0, 75.0):
            eta = _eta(mat, 10.0, n=2500, tilt=th)
            ref = (1.0 + np.cos(np.radians(th))) ** (-9.0 / np.sqrt(z))
            assert abs(eta - ref) <= 0.05, "%s θ=%g: η %.3f vs Arnal %.3f" % (mat, th, eta, ref)


def test_penetration_depth_scales_like_kanaya_okayama():
    """最大の到達深さは R_KO の 0.75〜1.05 倍、p95 の深さは E^1.67 に沿う(指数 1.45〜1.85)。"""
    for mat in ("SI", "AU"):
        p95 = []
        for e in (5.0, 10.0, 20.0):
            r = SM.sem_electron_mc(mat, e, tol=0.02, batch=1000, max_electrons=2000, seed=3)
            ratio = r["depth_max_nm"] / r["range_ko_nm"]
            assert 0.75 <= ratio <= 1.05, "%s %g keV: 最大深さ/R_KO = %.3f" % (mat, e, ratio)
            p95.append(r["depth_p95_nm"])
        slope = np.polyfit(np.log([5.0, 10.0, 20.0]), np.log(p95), 1)[0]
        assert 1.45 <= slope <= 1.85, "%s: 深さの電圧の指数 %.3f" % (mat, slope)


def test_probe_halved_stopping_power_overshoots_the_range(monkeypatch):
    """★探針: 阻止能を半分にすると電子が R_KO を大きく越え、深さの門が落とす。"""
    monkeypatch.setattr(SM, "_BETHE_PREF", SM._BETHE_PREF * 0.5)
    r = SM.sem_electron_mc("SI", 10.0, tol=0.05, batch=600, max_electrons=600, seed=3)
    assert r["depth_max_nm"] / r["range_ko_nm"] > 1.05


_SE_ENERGIES = np.geomspace(0.1, 12.0, 12)


def _shape(material, n=900):
    return SM.sem_yield_curve(material, _SE_ENERGIES, n_electrons=n, seed=5)


def test_se_yield_has_the_universal_shape_and_the_published_emax():
    """C / Al / Si / Cu / Ag: δ(E)/δmax が普遍曲線に RMS 0.08 以内、Emax は Table 1 の ±20 %。

    ★λ・ε は Table 1 のまま入れたが、δ の山の位置も形も合わせていない(予測)。
    W・Au は形が広がる(SE2 が主になるため)ので、この門の外にして別の門で数える。
    """
    for mat in ("C", "AL", "SI", "CU", "AG"):
        r = _shape(mat)
        em_ref = MT.material_electron_properties(mat)["se_ref"][1]
        assert r["shape_rms"] <= 0.08, "%s: 形の RMS %.3f" % (mat, r["shape_rms"])
        assert abs(r["emax_kev"] / em_ref - 1.0) <= 0.20, "%s: Emax %.3f vs %.2f" % (mat, r["emax_kev"], em_ref)


def test_heavy_elements_have_a_broader_se_curve_than_the_universal_one():
    """W・Au は普遍曲線より裾が厚い(既知の未解決: SE2 が主になる)—— 黙って直さず数で固定する。"""
    for mat in ("W", "AU"):
        r = _shape(mat)
        hi = r["energies_kev"] / r["emax_kev"] > 3.0
        assert np.all(r["se_yield"][hi] >= r["universal"][hi]), mat


def test_probe_ten_times_escape_depth_moves_emax(monkeypatch):
    """★探針: Si の脱出深さを 10 倍にすると Emax が Table 1 から 20 % 以上ずれ、門が落とす。"""
    real = MT.material_electron_properties

    def fake(name):
        r = real(name)
        r["se_escape_nm"] *= 10.0
        return r
    monkeypatch.setattr(MT, "material_electron_properties", fake)
    r = _shape("SI")
    assert abs(r["emax_kev"] / 0.45 - 1.0) > 0.20, "Emax %.3f が動かない" % r["emax_kev"]


def test_universal_curve_closed_form():
    x = np.array([0.5, 1.0, 2.0])
    want = 1.28 * x ** -0.67 * (1 - np.exp(-1.614 * x ** 1.67))
    assert np.allclose(SM.sem_se_universal_curve(x), want, rtol=0, atol=0)
    with pytest.raises(ValueError):
        SM.sem_se_universal_curve([0.0])


def test_tilted_si_se_yield_is_close_to_sec_theta():
    """Si(SE1 が主)の δ(θ)/δ(0) は sec θ の ±15 %(既存の sem_render の sec θ と同じ物理)。"""
    r0 = SM.sem_electron_mc("SI", 5.0, tol=0.01, batch=2000, max_electrons=4000, seed=1)
    for th in (45.0, 60.0):
        r = SM.sem_electron_mc("SI", 5.0, tol=0.01, batch=2000, max_electrons=4000, seed=1, tilt_deg=th)
        ratio = r["se_yield"] / r0["se_yield"]
        sec = 1.0 / np.cos(np.radians(th))
        assert abs(ratio / sec - 1.0) <= 0.15, "θ=%g: δ比 %.3f vs sec %.3f" % (th, ratio, sec)


# --------------------------------------------------------------------------- #
# 3. 幾何(断面と高さ場)の整合と、像・線プロファイルの構造                       #
# --------------------------------------------------------------------------- #
def test_flat_geometries_agree_with_the_bulk_mc():
    """平らな高さ場の像・平らな断面の線プロファイルは、平らな試料の MC と同じ η・δ を出す。"""
    bulk = SM.sem_electron_mc("SI", 3.0, tol=0.01, batch=2000, max_electrons=6000, seed=2)
    sig = SM.sem_image(np.zeros((6, 6)), energy_kev=3.0, electrons_per_pixel=60, beam_sigma_nm=0.0,
                       return_signals=True, seed=4)
    assert abs(float(sig["eta"].mean()) - bulk["eta"]) <= 0.03
    assert abs(float(sig["se_total"].mean()) / bulk["se_yield"] - 1.0) <= 0.08
    lp = SM.sem_line_profile("SI", "SI", 3.0, width_nm=20, height_nm=0.0, x_half_range_nm=10,
                             x_step_nm=10, electrons_per_point=700, beam_sigma_nm=0.0, seed=4)
    assert abs(float(lp["eta"].mean()) - bulk["eta"]) <= 0.03
    assert abs(float(lp["se_total"].mean()) / bulk["se_yield"] - 1.0) <= 0.08


def test_line_profile_has_bright_edges_and_a_detector_facing_asymmetry():
    """5 keV の PMMA の線: 縁は上面と基板より明るい。側方の検出器(+x)を向く右の縁が左より明るい。"""
    r = SM.sem_line_profile("PMMA", "SI", 5.0, width_nm=40, height_nm=40, sidewall_deg=88,
                            x_half_range_nm=40, x_step_nm=2, electrons_per_point=400, seed=1)
    x, il = r["x_nm"], r["inlens"]
    edge = il[(np.abs(np.abs(x) - 18) <= 2)].mean()
    top = il[np.abs(x) <= 6].mean()
    sub = il[np.abs(x) >= 32].mean()
    assert edge > 1.3 * top and edge > 1.3 * sub, (edge, top, sub)
    et = r["everhart"]
    right = et[(x >= 16) & (x <= 20)].mean()
    left = et[(x >= -20) & (x <= -16)].mean()
    assert right > 1.15 * left, (right, left)


def test_backscatter_shows_z_contrast_that_se_hides():
    """表面に埋めた W(CMP 後の W プラグ相当、段差なし)を 1 keV で: 反射電子は +50 % 超、二次電子は ±15 % 以内。

    もう 1 つ: 深さ 150 nm に埋もれた W は 1 keV では反射電子でも見えず、20 keV で浮かぶ(情報深さ)。
    """
    def contrast(e, top, key):
        r = SM.sem_line_profile("SI", "SI", e, width_nm=60, height_nm=0.0, x_half_range_nm=400,
                                x_step_nm=400, electrons_per_point=2500, beam_sigma_nm=0.0,
                                buried=[("W", -50.0, 50.0, top, top + 60.0)], seed=2)
        v = r[key]
        return v[1] / (0.5 * (v[0] + v[2])) - 1.0
    assert contrast(1.0, 0.0, "bse") > 0.5
    assert abs(contrast(1.0, 0.0, "inlens")) < 0.15
    assert abs(contrast(1.0, 150.0, "bse")) < 0.1
    assert contrast(20.0, 150.0, "bse") > 0.4


def test_cd_measure_on_closed_form_peaks():
    """2 つのガウスの山: 50 % しきい値は中心 ± σ√(2 ln 2)、最大傾斜は中心 ± σ。"""
    x = np.arange(-60.0, 60.5, 0.5)
    sig = 3.0
    y = 0.1 + np.exp(-0.5 * ((x + 20) / sig) ** 2) + np.exp(-0.5 * ((x - 20) / sig) ** 2)
    prof = np.stack([x, y], axis=1)
    th = SM.sem_cd_measure(prof, method="threshold", threshold=0.5)
    assert th["width_nm"] == pytest.approx(2 * (20 + sig * np.sqrt(2 * np.log(2))), abs=0.1)
    ms = SM.sem_cd_measure(prof, method="max_slope")
    assert ms["width_nm"] == pytest.approx(2 * (20 + sig), abs=0.1)
    with pytest.raises(ValueError):
        SM.sem_cd_measure(prof, method="nope")
    with pytest.raises(ValueError):
        SM.sem_cd_measure(np.stack([x, np.full_like(x, 0.3)], axis=1))   # 山が無い


def test_same_seed_same_result_and_fail_closed():
    a = SM.sem_image(np.zeros((4, 4)), energy_kev=1.0, electrons_per_pixel=5, seed=9)
    b = SM.sem_image(np.zeros((4, 4)), energy_kev=1.0, electrons_per_pixel=5, seed=9)
    assert np.array_equal(a, b)
    with pytest.raises(ValueError):
        SM.sem_electron_mc("SI", 0.01)                       # 電圧の範囲外
    with pytest.raises(ValueError):
        SM.sem_electron_mc("UNOBTAINIUM", 5.0)
    with pytest.raises(ValueError):
        SM.sem_image(np.zeros((4, 4)), detector="eye")
    with pytest.raises(ValueError):
        SM.sem_image(np.zeros((4, 4)), material_map=np.full((4, 4), 3), materials=("SI",))
    with pytest.raises(ValueError):
        SM.sem_line_profile(width_nm=10, height_nm=40, sidewall_deg=60)     # 上辺が負


# --------------------------------------------------------------------------- #
# 4. 帯電(コマごとの時間発展)                                                   #
# --------------------------------------------------------------------------- #
def test_escape_fraction_closed_form():
    """F(V) = φ²(3u − 2φ)/u³: F(0) = 1、F(φ) = 1/2、単調に減る。数値積分とも一致。"""
    phi = 2.0
    assert float(SM.sem_se_escape_fraction(0.0, phi_ev=phi)) == 1.0
    assert float(SM.sem_se_escape_fraction(phi, phi_ev=phi)) == pytest.approx(0.5, abs=1e-12)
    e = np.linspace(0.0, 4000.0, 2_000_001)
    f = e / (e + phi) ** 4
    trap = getattr(np, "trapezoid", None) or np.trapz          # numpy 1.x には trapezoid が無い
    for v in (0.5, 3.0, 10.0):
        num = trap(f[e >= v], e[e >= v]) / trap(f, e)
        assert float(SM.sem_se_escape_fraction(v, phi_ev=phi)) == pytest.approx(num, abs=1e-5)


def test_positive_charging_self_regulates_to_the_balance_potential():
    """η + δ > 1 の画素は、電位が η + δ·F(V*) = 1 の V*(別に二分法で解く)に止まる。"""
    h = np.zeros((6, 6))
    kw = dict(materials=("PMMA",), substrate="PMMA", energy_kev=0.5, electrons_per_pixel=40, seed=3)
    r = SM.sem_charging_series(h, frames=60, spread_px=0.0, return_potential=True, **kw)
    sig = SM.sem_image(h, return_signals=True, **kw)
    eta, dl = sig["eta"], sig["se_total"]
    pos = eta + dl > 1.05
    assert pos.sum() >= 30
    for (i, j) in zip(*np.nonzero(pos)):
        lo, hi = 0.0, 1e4
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if eta[i, j] + dl[i, j] * float(SM.sem_se_escape_fraction(mid)) > 1.0:
                lo = mid
            else:
                hi = mid
        assert r["potential_v"][-1, i, j] == pytest.approx(lo, abs=1e-3)
    # 像は 1 コマ目より暗くなって止まる。
    vid = r["video"]
    assert vid[-10:].mean() < 0.8 * vid[0].mean()


def test_negative_charging_brightens_and_grounded_conductors_stay_put():
    """20 keV の PMMA は負に溜まって明るくなる。同じ像の中の Si(導体)は電位 0 のまま。"""
    h = np.zeros((6, 8))
    mm = np.zeros((6, 8), dtype=int)
    mm[:, 4:] = 1
    r = SM.sem_charging_series(h, mm, materials=("PMMA", "SI"), substrate="SI", energy_kev=20.0,
                               layer_bottom_nm=50.0, electrons_per_pixel=30, frames=20,
                               return_potential=True, spread_px=0.0, seed=2)
    pv = r["potential_v"]
    assert np.all(pv[-1][:, :4] < -5.0) and np.all(pv[:, :, 4:] == 0.0)
    v = r["video"]
    assert v[-5:, :, :4].mean() > 1.2 * v[0, :, :4].mean()


def test_a_vanishing_cap_layer_does_not_change_backscatter():
    """★回帰(2026-10-15): W の上の Si のキャップを 0 → 0.01 nm にしても η は連続(差 0.03 以内)。

    自由行程を出発点の材料で引いたまま材料の境界を素通りしていたとき、0.01 nm のキャップで
    η が 0.425 → 0.329 に跳んだ(Si の長い自由行程で W に深く入ってから最初の散乱が起きる)。
    境界で歩を切って新しい材料で引き直すのが正しい(指数分布は無記憶)。断面と高さ場の両方で見る。
    """
    si, w = SM._electron_material("SI", "t"), SM._electron_material("W", "t")
    etas = []
    for cap in (0.0, 0.01):
        g = SM._ProfileGeom([0.0, 1.0], [0.0, 0.0], buried=[(2, -1e6, 1e6, cap, 1e6)], coll_window=1.0)
        r = SM._transport([si, si, w], g, np.zeros(4000), np.zeros(4000), 1.0, np.random.default_rng(1))
        etas.append(float(r["bse"].mean()))
    assert abs(etas[0] - etas[1]) <= 0.03, etas
    mask = np.ones((4, 4), dtype=bool)
    img = []
    for cap in (0.0, 0.01):
        s = SM.sem_image(np.zeros((4, 4)), energy_kev=1.0, electrons_per_pixel=250, beam_sigma_nm=0.0,
                         buried=[("W", mask, cap, 1e4)], return_signals=True, seed=1)
        img.append(float(s["eta"].mean()))
    assert abs(img[0] - img[1]) <= 0.03 and abs(img[0] - etas[0]) <= 0.03, (img, etas)
