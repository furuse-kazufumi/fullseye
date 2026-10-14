# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 材料の光学物性ライブラリ —— 硝材・結晶・半導体・金属・液体・プラスチック 83 種を 1 つの表にし、
カタログ公表値と第二実装で採点する。

【問い】観察用の光学系(レンズ・窓・鏡・膜)と観察対象(ウェハ・モールド・はんだ)は、どちらも材料の
光学特性で見え方が決まる。両方が**同じ材料表**を引けるか —— 硝材カタログの分散式、半導体の n,k の表、
金属の複素屈折率、液体とプラスチックを 1 つのレコード型に載せ、波長曲線をすべて同じ形(λ [nm], 値)で
返す。新 op 16 本(`materials`)。5 章:

  1. **硝材 46 種の Abbe 図**(4 社のカタログ、CC0 の refractiveindex.info database から): 分散式から計算した
     n_d / V_d が**カタログの公表値と 1e-4 / 0.3 以内**(46 種全部)。プラスチック・結晶・液体を同じ図に。
     **第二実装** optiland 0.6.3(同じ一次文献を別のコードで評価)の n(λ) と 23 点で 1e-6。
  2. **Si の NIR 窓**(Green 2008): 公表の点 k(1.0 µm) = 5.09e-4、k(1.2 µm) = 2.1e-7 を再現、吸収端を跨ぐ
     3 桁の落差、平行平板の透過率は閉形式(1−R)²e^{−αt}/(1−R²e^{−2αt})と 1e-9、自由キャリア吸収は
     Schroder 1978 の λ² 則、平行平板の焦点ずれ t(1 − 1/n) と縦球面収差(NA²)は閉形式。
  3. **鏡の材料**(Johnson & Christy / Rakić / Weaver / Werner): 10 金属の反射率。門: 銀は 500 nm で ≥ 0.97、
     アルミの谷は 750〜900 nm(≈ 0.87)、金は 500 nm で < 0.6・700 nm で > 0.95。色は CIE 等色関数から
     (金は R > G > B、銀はほぼ中性)。
  4. **硝子とプラスチック**: 分散曲線と dn/dT(カタログの式 A)。門: 基準温度で Δn = 0、dn/dT は Δn の
     有限差分と 1e-3、プラスチックの V_d は硝子の同じ n_d より小さい。
  5. **取り込み口**: .agf(硝材カタログ)の雛形を読んで同梱レコードと 1e-12、環境変数 ``FULLSEYE_GLASS_DIR``
     にユーザーのカタログがあれば同名の硝材を照合(無ければ「未配置」と明示)。

【外部真値】refractiveindex.info database(CC0 1.0、Polyanskiy, Sci. Data 11, 94 (2024))の一次文献と
カタログ公表値、Green, Sol. Energy Mater. Sol. Cells 92, 1305 (2008)、Johnson & Christy, Phys. Rev. B 6,
4370 (1972)、Schroder, Thomas & Swartz, IEEE TED 25, 254 (1978)、optiland 0.6.3(OSS、第二実装)。
【学習した数】0。【較正】0。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import materials as MT  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
GLASS_DIR = os.environ.get("FULLSEYE_GLASS_DIR", "").strip()

#: 第二実装 optiland 0.6.3(同じ refractiveindex.info の一次文献を別のコードで評価、2026-10-14 実行)。
#: (材料, λ nm) → (n, k)。Si は Green 2008 と Salzberg、水は Daimon(20 ℃)と Hale の区間。
OPTILAND = {
    ("N-BK7", 400): (1.530848538, 1.0227e-08), ("N-BK7", 1550): (1.500652043, 1.4361e-07),
    ("N-SF11", 500): (1.802555175, 7.6618e-08), ("S-BSL7", 600): (1.515825156, 1.4345e-08),
    ("H-K9L", 700): (1.513071801, 1.6736e-08), ("FD60", 900): (1.779252370, 1.4338e-08),
    ("H-ZF52A", 800): (1.823406896, 1.2745e-08), ("SI", 1000): (3.572000000, 5.0930e-04),
    ("SI", 3000): (3.432322072, 0.0), ("AG", 500): (0.050000000, 3.1309e+00),
    ("AU", 600): (0.248731988, 3.0740e+00), ("SILICA", 1064): (1.449630990, 0.0),
    ("CAF2", 1500): (1.426257966, 0.0), ("GE", 1550): (4.216243957, 2.7000e-04),
    ("ZNSE", 1200): (2.471354515, 0.0), ("ZNS", 800): (2.313185509, 0.0),
    ("TIO2", 633): (2.583580138, 0.0), ("HFO2", 550): (1.902098695, 0.0),
    ("GAN", 450): (2.486916613, 0.0), ("PMMA", 800): (1.484307203, 0.0),
    ("WATER", 500): (1.336795977, 0.0), ("WATER", 1500): (1.319000000, 1.1175e-04),
    ("SAPPHIRE", 800): (1.760132585, 0.0),
}

#: Green 2008 の表の公表点(λ µm, n, k)。
GREEN_2008 = {1.0: (3.572, 5.093e-4), 1.2: (3.520, 2.1008e-7), 0.5: (4.294, 4.4165e-2)}

METALS = ["AG", "AL", "AU", "CU", "RH", "CR", "NI", "W", "TI", "PT"]

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _at(curve, x):
    return float(curve[int(np.argmin(np.abs(curve[:, 0] - x))), 1])


# --------------------------------------------------------------------------- #
# 1. 硝材の Abbe 図と第二実装                                                    #
# --------------------------------------------------------------------------- #
def chapter_glass():
    print("\n1. 硝材 46 種の Abbe 図(カタログ公表値)と第二実装 optiland")
    cat = MT.material_table()
    print("   同梱 %d 材料: %s" % (len(cat), ", ".join("%s %d" % (c, sum(r["class"] == c for r in cat))
                                                   for c in MT.CLASSES[:-1])))
    gate("同梱の材料は 83 種(硝材 46・結晶 12・半導体 6・膜 4・金属 10・液体 1・高分子 4)", len(cat) == 83
         and sum(r["class"] == "glass" for r in cat) == 46)
    rec = MT.material_record("SI")
    print("   例: Si のレコード = %s、区間 %s" % (rec["class"], ", ".join("%s %s %.3g-%.3g µm (%s)" % (
        d["type"], d.get("formula", ""), d["range_um"][0], d["range_um"][1], d["page"].split("/")[-1]) for d in rec["datasets"])))
    gate("レコードは区間ごとに一次文献のページを持つ(Si は Green 2008 と Salzberg)",
         all(d["page"].endswith(".yml") for d in rec["datasets"]) and len(rec["datasets"]) == 2)
    worst_n, worst_v = 0.0, 0.0
    rows = []
    for r in MT.material_table("glass"):
        a = MT.abbe_number(r["name"])
        dn, dv = abs(a["nd"] - a["nd_catalog"]), abs(a["vd"] - a["vd_catalog"])
        worst_n, worst_v = max(worst_n, dn), max(worst_v, dv)
        rows.append((r["name"], a["nd"], a["nd_catalog"], a["vd"], a["vd_catalog"], a["PgF"] if a["PgF"] is not None else float("nan"), r["density_kg_m3"]))
    NUMBERS["glass_worst_dn"], NUMBERS["glass_worst_dv"] = worst_n, worst_v
    gate("46 種すべてで分散式の n_d がカタログ公表値と 1e-4 以内、V_d が 0.3 以内",
         worst_n <= 1e-4 and worst_v <= 0.3, "最大 |Δn_d| %.1e、|ΔV_d| %.3f" % (worst_n, worst_v))
    gm = MT.glass_map()
    cls = {c: [g for g in gm if g["class"] == c] for c in ("glass", "polymer", "crystal", "liquid", "film", "semiconductor")}
    print("   Abbe 図に載る材料 %d(硝材 %d・高分子 %d・結晶 %d・液体 %d・膜 %d・半導体 %d)"
          % (len(gm), *[len(cls[c]) for c in ("glass", "polymer", "crystal", "liquid", "film", "semiconductor")]))
    gate("可視で吸収する金属は Abbe 図に載らず、硝材 46 種は全部載る",
         not any(g["class"] == "metal" for g in gm) and len(cls["glass"]) == 46)
    pm = {g["name"]: g for g in gm}
    gate("プラスチック 4 種はどれも V_d < 60(硝子なら同じ n_d のクラウンが 60 前後)",
         all(pm[p]["vd"] < 60 for p in ("PMMA", "POLYCARBONATE", "POLYSTYRENE", "ZEONEX_E48R")),
         "PMMA %.1f / PC %.1f / PS %.1f / COP %.1f" % tuple(pm[p]["vd"] for p in ("PMMA", "POLYCARBONATE", "POLYSTYRENE", "ZEONEX_E48R")))
    worst = 0.0
    for (name, wl), (n2, k2) in OPTILAND.items():
        a = MT.material_optical_constants(name, wl)
        worst = max(worst, abs(a["n"] - n2))
        if k2 > 0:
            worst = max(worst, abs(a["k"] / k2 - 1.0) * 1e-6)
    NUMBERS["optiland_worst"] = worst
    gate("第二実装 optiland の n(λ) と %d 点で 1e-6 以内(k は相対 1)" % len(OPTILAND), worst <= 1e-6, "最大 %.1e" % worst)
    return rows, gm


# --------------------------------------------------------------------------- #
# 2. Si の NIR 窓                                                               #
# --------------------------------------------------------------------------- #
def chapter_silicon():
    print("\n2. Si の NIR 窓(Green 2008)、平行平板の透過率と焦点ずれ、自由キャリア吸収")
    for wl, (n_pub, k_pub) in sorted(GREEN_2008.items()):
        a = MT.material_optical_constants("SI", wl * 1e3)
        gate("Si %.1f µm: n = %.3f, k = %.4g(Green 2008 の表の点)" % (wl, n_pub, k_pub),
             abs(a["n"] - n_pub) < 5e-4 and abs(a["k"] / k_pub - 1.0) < 1e-3, "n %.4f k %.4g" % (a["n"], a["k"]))
    al = MT.material_absorption("SI", 900, 1400, 101)
    a10, a12 = _at(al, 1000), _at(al, 1200)
    NUMBERS["si_alpha_1000"], NUMBERS["si_alpha_1200"] = a10, a12
    gate("吸収係数は 1.0 → 1.2 µm で 3 桁落ちる(吸収端 ≈ 1.1 µm)", a10 / a12 > 1e3, "%.1f → %.4f /cm" % (a10, a12))
    t_mm = 0.775
    T = MT.material_transmittance("SI", t_mm, 900, 1400, 101)
    c12 = MT.material_optical_constants("SI", 1200.0)
    R = c12["reflectance_normal"]
    inner = np.exp(-c12["alpha_per_cm"] * t_mm * 0.1)
    closed = (1 - R) ** 2 * inner / (1 - R * R * inner * inner)
    NUMBERS["si_T_1200"], NUMBERS["si_T_1000"] = _at(T, 1200), _at(T, 1000)
    gate("775 µm のウェハ: T(1.2 µm) = (1−R)²e^{−αt}/(1−R²e^{−2αt}) と 1e-9", abs(_at(T, 1200) - closed) < 1e-9,
         "%.4f(R = %.3f なので多重反射込みで半分強)" % (_at(T, 1200), R))
    gate("775 µm のウェハ: T(1.0 µm) < 1 %(吸収端の上は透過しない)", _at(T, 1000) < 0.01, "%.2e" % _at(T, 1000))
    Ti = MT.material_transmittance("SI", t_mm, 900, 1400, 101, include_fresnel=False)
    gate("内部透過率は Fresnel 込みより大きく、1.3 µm で 0.99 以上", np.all(Ti[:, 1] >= T[:, 1] - 1e-12) and _at(Ti, 1300) > 0.99,
         "内部 %.4f / 全体 %.4f" % (_at(Ti, 1300), _at(T, 1300)))
    fc = MT.silicon_free_carrier_absorption(1e19, "n", 1000, 2000, 101)
    fcp = MT.silicon_free_carrier_absorption(1e19, "p", 1000, 2000, 101)
    gate("自由キャリア吸収は λ²(1.0 → 2.0 µm で 4 倍)、p 型は n 型の 2.7 倍(Schroder 1978)",
         abs(_at(fc, 2000) / _at(fc, 1000) - 4.0) < 1e-9 and abs(_at(fcp, 1300) / _at(fc, 1300) - 2.7) < 1e-9,
         "n 型 1e19 cm⁻³ の 1.3 µm で %.1f /cm" % _at(fc, 1300))
    NUMBERS["fc_1e19_1300"] = _at(fc, 1300)
    T_doped = np.exp(-_at(fc, 1300) * t_mm * 0.1)
    print("   高濃度基板(1e19 cm⁻³、775 µm)は 1.3 µm で自由キャリアだけで ×%.2f に暗くなる" % T_doped)
    NUMBERS["fc_T_1e19"] = T_doped
    p = MT.plate_focus_shift("SI", t_mm, 1100.0, 0.1)
    gate("平行平板の近軸焦点ずれ = t(1 − 1/n)、縦球面収差 = Δ(θ) − Δ₀ > 0",
         abs(p["paraxial_shift_mm"] - t_mm * (1 - 1 / p["n"])) < 1e-12 and p["spherical_aberration_mm"] > 0,
         "Δ₀ %.3f mm、NA 0.1 で収差 %.1f µm" % (p["paraxial_shift_mm"], p["spherical_aberration_mm"] * 1e3))
    NUMBERS["plate_shift"], NUMBERS["plate_sa"] = p["paraxial_shift_mm"], p["spherical_aberration_mm"]
    p3 = MT.plate_focus_shift("SI", t_mm, 1100.0, 0.3)
    gate("縦球面収差は NA の 2 乗(NA 0.1 → 0.3 で 8.5〜9.5 倍、波面収差なら 4 乗)",
         8.5 < p3["spherical_aberration_mm"] / p["spherical_aberration_mm"] < 9.5,
         "%.2f 倍、NA 0.3 で %.1f µm" % (p3["spherical_aberration_mm"] / p["spherical_aberration_mm"], p3["spherical_aberration_mm"] * 1e3))
    return T, Ti, fc


# --------------------------------------------------------------------------- #
# 3. 鏡の材料                                                                   #
# --------------------------------------------------------------------------- #
def chapter_mirror():
    print("\n3. 鏡の材料 10 種の反射率と色")
    R = {m: MT.material_reflectance(m, 300, 1900, 161) for m in METALS}
    gate("銀は 500 nm で R ≥ 0.97(Johnson & Christy)", _at(R["AG"], 500) >= 0.97, "%.4f" % _at(R["AG"], 500))
    ral = R["AL"]
    sel = (ral[:, 0] >= 400) & (ral[:, 0] <= 1500)
    imin = int(np.argmin(np.where(sel, ral[:, 1], 9.0)))
    NUMBERS["al_dip_nm"], NUMBERS["al_dip_R"] = ral[imin, 0], ral[imin, 1]
    gate("アルミの反射率の谷は 750〜900 nm(バンド間遷移)", 750 <= ral[imin, 0] <= 900, "最小 %.3f at %.0f nm" % (ral[imin, 1], ral[imin, 0]))
    gate("金は 500 nm で R < 0.6、700 nm で R > 0.95(黄色い理由)", _at(R["AU"], 500) < 0.6 and _at(R["AU"], 700) > 0.95,
         "%.3f / %.3f" % (_at(R["AU"], 500), _at(R["AU"], 700)))
    gate("銅も 500 nm では金と同じ側(R < 0.65)で 700 nm で > 0.95", _at(R["CU"], 500) < 0.65 and _at(R["CU"], 700) > 0.95)
    def _vis(m):
        r = R[m][(R[m][:, 0] >= 400) & (R[m][:, 0] <= 700), 1]
        return float(np.ptp(r)), float(r.mean())
    grey = {m: _vis(m) for m in ("RH", "CR", "NI", "W", "PT", "TI")}
    gate("灰色の鏡(Rh・Cr・Ni・W・Pt・Ti)は可視の変化が金(%.2f)の半分以下で、平均は銀(%.3f)より暗い"
         % (_vis("AU")[0], _vis("AG")[1]),
         all(v[0] < 0.5 * _vis("AU")[0] and v[1] < _vis("AG")[1] for v in grey.values()),
         " / ".join("%s 変化 %.2f 平均 %.2f" % (m, v[0], v[1]) for m, v in grey.items()))
    import matappear
    grid = np.linspace(380.0, 780.0, 81)
    rgb = {}
    for m in METALS:
        Rv = MT.material_reflectance(m, 380, 780, 81)[:, 1]
        rgb[m] = np.asarray(matappear.spectrum_to_srgb(grid, Rv), dtype=np.float64).ravel()
    gate("色は塗っていない: 金と銅は R > G > B、銀は 3 成分が 10 % 以内で中性",
         rgb["AU"][0] > rgb["AU"][1] > rgb["AU"][2] and rgb["CU"][0] > rgb["CU"][1] > rgb["CU"][2]
         and np.ptp(rgb["AG"]) / rgb["AG"].max() < 0.10,
         "Au %s Ag %s" % (np.round(rgb["AU"], 3), np.round(rgb["AG"], 3)))
    Rs = MT.material_reflectance("AL", 633, 634, 2, angle_deg=60.0, polarization="s")[0, 1]
    Rp = MT.material_reflectance("AL", 633, 634, 2, angle_deg=60.0, polarization="p")[0, 1]
    Ru = MT.material_reflectance("AL", 633, 634, 2, angle_deg=60.0)[0, 1]
    gate("斜入射(60°)で s > p、無偏光は平均", Rs > Rp and abs(Ru - 0.5 * (Rs + Rp)) < 1e-12, "s %.3f p %.3f" % (Rs, Rp))
    return R, rgb


# --------------------------------------------------------------------------- #
# 4. 硝子とプラスチック                                                          #
# --------------------------------------------------------------------------- #
def chapter_plastic():
    print("\n4. 硝子とプラスチックの分散と dn/dT")
    names = ["N-BK7", "N-SF11", "SILICA", "CAF2", "PMMA", "POLYCARBONATE", "ZEONEX_E48R"]
    disp = {n: MT.material_dispersion(n, 440, 1000, 57) for n in names}
    def slope(n):
        d = disp[n]
        return (d[0, 1] - d[-1, 1]) / d[0, 1]
    gate("ポリカーボネートの分散(440 → 1000 nm の n の落ち)は N-BK7 の 2 倍以上、CaF2 は N-BK7 より小さい",
         slope("POLYCARBONATE") > 2 * slope("N-BK7") and slope("CAF2") < slope("N-BK7"),
         "PC %.4f / N-BK7 %.4f / CaF2 %.4f" % (slope("POLYCARBONATE"), slope("N-BK7"), slope("CAF2")))
    th_names = ["N-BK7", "N-SF11", "S-BSL7", "FD60", "H-ZF52A"]
    temps = np.linspace(-20.0, 80.0, 41)
    th = {}
    worst = 0.0
    for n in th_names:
        tref = MT.thermo_optic_coefficient(n, 546.07, 20.0)["reference_temperature_c"]
        a = MT.thermo_optic_coefficient(n, 546.07, tref)
        gate("%s: 基準温度 %.0f ℃ で Δn = 0" % (n, tref), abs(a["delta_n"]) < 1e-15)
        dn = np.array([MT.thermo_optic_coefficient(n, 546.07, t)["delta_n"] for t in temps])
        th[n] = dn
        # dn/dT = dΔn/dT を 40 ℃ の有限差分で確かめる(式 A の D₁・D₂・E₁ の項まで)
        h = 0.01
        fd = (MT.thermo_optic_coefficient(n, 546.07, 40.0 + h)["delta_n"] - MT.thermo_optic_coefficient(n, 546.07, 40.0 - h)["delta_n"]) / (2 * h)
        an = MT.thermo_optic_coefficient(n, 546.07, 40.0)["dn_dt_per_k"]
        worst = max(worst, abs(fd / an - 1.0))
    gate("dn/dT は Δn の有限差分と 1e-3 以内(5 種、40 ℃)", worst < 1e-3, "最大 %.1e" % worst)
    bk = MT.thermo_optic_coefficient("N-BK7", 546.07, 30.0)["dn_dt_per_k"]
    NUMBERS["bk7_dndt"] = bk
    gate("N-BK7 の dn/dT(e 線、20〜40 ℃)は 1.4〜1.8e-6 /K", 1.4e-6 < bk < 1.8e-6, "%.2e /K" % bk)
    for n in ("PMMA", "WATER"):
        try:
            MT.thermo_optic_coefficient(n)
            gate("%s に dn/dT の係数は無い → ValueError" % n, False)
        except ValueError:
            gate("%s に dn/dT の係数は無い → ValueError(黙って 0 にしない)" % n, True)
    return disp, temps, th


# --------------------------------------------------------------------------- #
# 5. 取り込み口                                                                 #
# --------------------------------------------------------------------------- #
def chapter_import():
    print("\n5. 硝材カタログ(.agf)の取り込みと自前の材料")
    recs = MT.read_glass_catalog_agf(None)
    worst = 0.0
    for r in recs:
        for wl in (400.0, 587.56, 800.0, 1000.0):
            worst = max(worst, abs(MT.material_optical_constants(r, wl)["n"] - MT.material_optical_constants(r["name"], wl)["n"]))
    gate("雛形 .agf の %s を読むと同梱レコードと 1e-12 以内(Sellmeier 1 と Schott 多項式の両方)" % " / ".join(r["name"] for r in recs),
         worst < 1e-12 and [r["name"] for r in recs] == ["N-BK7", "BSC7"], "最大 %.1e" % worst)
    k = MT.material_optical_constants(recs[0], 400.0)["k"]
    gate("IT 行(内部透過率)から k を復元する(N-BK7 の 400 nm で 1e-9〜1e-7)", 1e-9 < k < 1e-7, "%.2e" % k)
    custom = MT.material_from_sellmeier("my_glass", reference="worked example")
    gate("自前の Sellmeier 係数(既定は N-BK7)からレコードを作り、他の op に渡せる",
         abs(MT.abbe_number(custom)["nd"] - 1.5168) < 1e-4)
    cur = MT.material_from_curves(MT.material_dispersion("N-SF11", 400, 1000, 61), MT.material_extinction("N-SF11", 400, 1000, 61), "measured")
    gate("測った曲線(pairs)から作ったレコードは節で元と一致し、区間外は外挿しない",
         abs(MT.material_optical_constants(cur, 600.0)["n"] - MT.material_optical_constants("N-SF11", 600.0)["n"]) < 1e-12)
    try:
        MT.material_optical_constants(cur, 1200.0)
        gate("区間外は ValueError", False)
    except ValueError:
        gate("区間外は ValueError", True)
    if GLASS_DIR and os.path.isdir(GLASS_DIR):
        user = MT.read_glass_catalog_agf(GLASS_DIR)
        hit = [r for r in user if r["name"] in MT.MATERIALS]
        worst = 0.0
        for r in hit:
            lo, hi = r["datasets"][0]["range_um"]
            for wl in np.linspace(max(lo, 0.4), min(hi, 1.0), 4):
                worst = max(worst, abs(MT.material_optical_constants(r, wl * 1e3)["n"] - MT.material_optical_constants(r["name"], wl * 1e3)["n"]))
        print("   ユーザーのカタログ: %d 硝材、同梱と同名 %d、n の最大差 %.1e" % (len(user), len(hit), worst))
        NUMBERS["user_glass_count"] = len(user)
        gate("ユーザーのカタログの同名硝材は同梱レコードと 1e-4 以内", worst < 1e-4, "%.1e" % worst)
    else:
        print("   ユーザーの硝材カタログ(FULLSEYE_GLASS_DIR)は未配置 —— 雛形だけで採点")
    return recs


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(glass, si, mirror, plastic, agf):
    import matappear  # noqa: F401
    rows, gm = glass
    T, Ti, fc = si
    R, rgb = mirror
    disp, temps, th = plastic
    series, kinds, colors = [], [], []
    for cls, label, col in (("glass", "硝材 46 種(4 社)", "neutral"), ("polymer", "プラスチック 4 種", "emphasis"),
                            ("crystal", "結晶・IR 材", "right"), ("liquid", "水", "reference"), ("film", "膜", "wrong"),
                            ("semiconductor", "半導体(GaN・SiC)", "wrong")):
        pts = [g for g in gm if g["class"] == cls]
        if pts:
            series.append((label, np.array([g["vd"] for g in pts]), np.array([g["nd"] for g in pts])))
            kinds.append("scatter")
            colors.append(col)
    figs.save_plot("abbe_diagram", series, xlabel="Abbe 数 V_d(慣例と逆向きに右へ増える)", ylabel="n_d",
                   title="Abbe 図: 同梱 %d 材料(硝材はカタログ公表値と |Δn_d| ≤ %.0e、|ΔV_d| ≤ %.3f)"
                         % (len(gm), NUMBERS["glass_worst_dn"], NUMBERS["glass_worst_dv"]),
                   kinds=kinds, colors=colors,
                   caption="分散式(refractiveindex.info の一次文献、CC0)から計算した n_d と V_d。プラスチックは同じ n_d の硝子より左(分散が大きい)、CaF2 と石英は右端。")
    figs.save_table("glass_catalogue", ["硝材", "n_d 計算", "n_d 公表", "V_d 計算", "V_d 公表", "P_g,F", "密度 kg/m³"],
                    [[r[0], "%.5f" % r[1], "%.5f" % r[2], "%.2f" % r[3], "%.2f" % r[4], "%.4f" % r[5], "%.0f" % r[6]] for r in rows[:46]],
                    title="硝材 46 種: 分散式の n_d / V_d とカタログ公表値", caption="4 社のカタログの Sellmeier / Schott 多項式を同じレコード型で評価した。")
    figs.save_table("second_implementation", ["材料", "λ nm", "n (optiland 0.6.3)", "n (fullseye)", "k (optiland)", "k (fullseye)"],
                    [[nm, "%g" % wl, "%.9f" % n2, "%.9f" % MT.material_optical_constants(nm, wl)["n"], "%.4e" % k2,
                      "%.4e" % MT.material_optical_constants(nm, wl)["k"]] for (nm, wl), (n2, k2) in OPTILAND.items()],
                    title="第二実装との突き合わせ(最大差 %.1e)" % NUMBERS["optiland_worst"],
                    caption="同じ一次文献を optiland(MIT)が別のコードで評価した値。式 1〜5 と数表の補間が同じ答えを返す。")
    # 2. Si
    wl = np.linspace(250.0, 1450.0, 241)
    n_si = MT.material_dispersion("SI", 250, 1450, 241)
    k_si = MT.material_extinction("SI", 250, 1450, 241)
    pub = np.array(sorted(GREEN_2008))
    figs.save_plot("silicon_index", [("n(λ)", n_si[:, 0], n_si[:, 1]), ("Green 2008 の表の点", pub * 1e3, np.array([GREEN_2008[w][0] for w in pub]))],
                   xlabel="波長 [nm]", ylabel="n", title="Si の屈折率(Green 2008、300 K)", kinds=["line", "scatter"], colors=["emphasis", "reference"],
                   caption="紫外の 370 nm 付近で n ≈ 6.9 の峰(直接遷移)、NIR で 3.5。")
    keep = k_si[:, 1] > 0
    figs.save_plot("silicon_extinction", [("log10 k(λ)", k_si[keep, 0], np.log10(k_si[keep, 1])),
                                          ("Green 2008 の表の点", pub * 1e3, np.log10([GREEN_2008[w][1] for w in pub]))],
                   xlabel="波長 [nm]", ylabel="log10 k", title="Si の消衰係数: 吸収端 ≈ 1.1 µm で 3 桁落ちる",
                   kinds=["line", "scatter"], colors=["emphasis", "reference"],
                   caption="k(1.0 µm) = 5.1e-4 → k(1.2 µm) = 2.1e-7。NIR 透過検査が 1.1 µm より長い波長を使う理由。")
    ths = [0.1, 0.3, 0.775, 2.0]
    figs.save_plot("silicon_transmittance", [("%g mm" % t, *(MT.material_transmittance("SI", t, 900, 1400, 101).T)) for t in ths],
                   xlabel="波長 [nm]", ylabel="透過率(多重反射込み)", title="Si 平板の透過率(厚さ別)", ylim=(0.0, 0.6),
                   caption="吸収端の上は厚さに関わらず 0、下は (1−R)²/(1−R²) ≈ 0.53 に漸近(n ≈ 3.5 の Fresnel 損失)。")
    frames = []
    for t in np.geomspace(0.05, 3.0, 20):
        Tt = MT.material_transmittance("SI", float(t), 900, 1400, 101)
        img = figs.render_plot([("厚さ %.2f mm" % t, Tt[:, 0], Tt[:, 1])], xlabel="波長 [nm]", ylabel="透過率",
                               title="Si 平板 %.2f mm: T(1.1 µm) %.3f、T(1.2 µm) %.3f、T(1.3 µm) %.3f" % (t, _at(Tt, 1100), _at(Tt, 1200), _at(Tt, 1300)),
                               colors=["emphasis"], ylim=(0.0, 0.6), xlim=(900.0, 1400.0))
        frames.append(np.asarray(img))
    figs.save_gif("silicon_window_thickness", frames, fps=4.0,
                  caption="厚さ 0.05 → 3 mm: 吸収端が長波長側へ押され、1.1 µm の肩が消えていく。薄いダイなら 1.0 µm 台でも透け、厚いウェハは 1.2 µm 以上。")
    dops = np.logspace(14, 20, 61)
    curves = []
    for wl_nm in (1200.0, 1300.0, 1550.0):
        a = np.array([_at(MT.silicon_free_carrier_absorption(N, "n", wl_nm, wl_nm + 1, 2), wl_nm) for N in dops])
        curves.append(("n 型 %.0f nm" % wl_nm, np.log10(dops), np.exp(-a * 0.775 * 0.1)))
    figs.save_plot("silicon_free_carrier", curves, xlabel="log10 キャリア密度 [cm⁻³]", ylabel="自由キャリア吸収だけの透過率(775 µm)",
                   title="自由キャリア吸収(Schroder 1978、α = 1e-18 N λ²)", ylim=(0.0, 1.05),
                   caption="1e18 cm⁻³ を超える基板は吸収端の下でも暗くなり、長波長ほど(λ²)早く落ちる。")
    nas = np.linspace(0.02, 0.5, 49)
    sa = np.array([MT.plate_focus_shift("SI", 0.775, 1100.0, float(na))["spherical_aberration_mm"] for na in nas]) * 1e3
    sh = np.array([MT.plate_focus_shift("SI", 0.775, 1100.0, float(na))["marginal_shift_mm"] for na in nas]) * 1e3
    figs.save_plot("plate_focus_shift", [("縁の光線の焦点ずれ [µm]", nas, sh), ("縦球面収差 [µm]", nas, sa),
                                         ("近軸 Δ₀ = t(1−1/n)", nas, np.full_like(nas, NUMBERS["plate_shift"] * 1e3))],
                   xlabel="NA", ylabel="µm", title="Si ウェハ 775 µm 越しの焦点(1.1 µm): 近軸で %.0f µm、縦球面収差は NA²" % (NUMBERS["plate_shift"] * 1e3),
                   styles=[None, None, "dashed"], colors=["emphasis", "right", "reference"],
                   caption="平行平板は像を t(1−1/n) 奥へ動かし、NA の 2 乗で縦球面収差(波面では 4 乗)を足す。ウェハ越しの結像で NA を抑える理由。")
    # 3. 鏡
    figs.save_plot("mirror_reflectance", [(m, R[m][:, 0], R[m][:, 1]) for m in METALS], xlabel="波長 [nm]", ylabel="垂直入射の反射率",
                   title="鏡の材料 10 種(Johnson & Christy / Rakić / Weaver / Werner)", ylim=(0.0, 1.0),
                   caption="銀は可視〜NIR で最も明るく 400 nm 以下で落ちる。アルミは 815 nm に谷。金・銅は 500 nm 以下で暗い(黄・赤)。")
    sw = np.ones((180, 100 * len(METALS), 3))
    for i, m in enumerate(METALS):
        c = np.clip(rgb[m], 0.0, 1.0) ** (1 / 2.2)
        sw[20:120, i * 100 + 5:i * 100 + 95] = c
        sw = np.asarray(fs.text_box(sw, m, (i * 100 + 50, 130), anchor="ct", font_size=12))
    figs.save("mirror_colours", sw, caption="n,k → 分光反射率 → CIE 等色関数 → sRGB。色は塗っていない: 金と銅が暖色で銀が中性なのは表の n,k から出る。")
    # 4. 分散と dn/dT
    figs.save_plot("dispersion_glass_vs_plastic", [(n, disp[n][:, 0], disp[n][:, 1]) for n in disp], xlabel="波長 [nm]", ylabel="n",
                   title="硝子・結晶・プラスチックの分散(440〜1000 nm)",
                   caption="ポリカーボネートは N-BK7 の 2 倍以上の落ち(V_d ≈ 30)。CaF2 と石英はほぼ平ら。")
    figs.save_plot("thermo_optic", [(n, temps, th[n] * 1e6) for n in th], xlabel="温度 [℃]", ylabel="Δn × 1e6(e 線、真空中)",
                   title="硝材の温度による屈折率変化(カタログの式 A)",
                   caption="FD60 のような重フリントは低温側で負の dn/dT を持つ。基準温度(20 ℃ / 25 ℃)で 0 を通る。")


def main():
    t0 = time.time()
    print("PoC 材料の光学物性ライブラリ(予算 %s、ユーザーの硝材カタログ %s)" % ("reduced" if REDUCED else "full", "あり" if GLASS_DIR else "未配置"))
    glass = chapter_glass()
    si = chapter_silicon()
    mirror = chapter_mirror()
    plastic = chapter_plastic()
    agf = chapter_import()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(glass, si, mirror, plastic, agf)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
