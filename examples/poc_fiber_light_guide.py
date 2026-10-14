# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 光ファイバとライトガイド —— 材料表の溶融石英から、モード・分散・モード径・照明の効率まで閉形式と特性方程式で。

【問い】検査の照明はライトガイド(ファイバの束)で運び、計測の光(干渉・分光・OCT)は単一モードファイバで運ぶ。
どちらもガラスの分散(材料表 ``materials``)と導波の式(Bessel 関数の特性方程式)で決まる。新 op 7 本(`fiberoptics`)
を、外の真値で採点する。5 章:

  1. **ガラスの分散**: 溶融石英(Malitson 1965、材料表)の群屈折率 1.55 µm で 1.4626、材料分散の零点 1.27 µm、
     D(1.55 µm) ≈ 22 ps/(nm·km)。門: どれも公表値の幅に入る。
  2. **LP モード**: 特性方程式 u J_{l−1}(u)/J_l(u) = −w K_{l−1}(w)/K_l(w) を区間ごとに解く。門: 遮断が Bessel の零点
     (LP11 = 2.4048、LP21 / LP02 = 3.8317)で ±0.001 の上下でモード数が変わる(★LP0m は遮断の直上で束縛が
     指数関数的に弱く —— V − u が e^{−数百} —— 浮動小数で解けるのは遮断の 0.05 上から)、V = 30 でモード数 → V²/2 が 2 % 以内、
     LP01 の b(V) が Rudolph–Neumann の近似と 1.5 < V < 2.5 で 0.5 % 以内。
  3. **モード径**: LP01 の厳密な場に重なり最大のガウスを当てた MFD は Marcuse 1977 の近似式と 1.2 < V < 2.4 で 1 % 以内。
     ★所見: 定義を 2 次モーメント(Petermann I)に変えると V = 1.2 で 11 % 大きい —— 「MFD」は定義を書かないと比べられない。
  4. **標準の単一モードファイバ**(ITU-T G.652 の数値の範囲を外の真値に): コア半径 4.1 µm・NA 0.12 で遮断 1.29 µm、
     1310 nm の MFD が規格の 8.6〜9.5 µm に入る。
  5. **ライトガイドの効率**: Lambert の LED を NA の違う束に入れる割合 = (NA_束 / NA_光源)² の閉形式、充填率・端面の Fresnel・
     減衰を掛けた全体の効率と、Si ウェハ越しの NIR 照明(`spectralrad`)の鎖へ繋ぐ。

【外部真値】Bessel 関数の零点、Malitson 1965 の溶融石英(材料表、refractiveindex.info、CC0)の分散の公表値、Marcuse 1977、
Rudolph & Neumann 1976 の b(V) 近似、ITU-T G.652(標準の単一モードファイバの MFD の範囲)。【学習】0。【較正】0。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np
from scipy import special

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fiberoptics as FO  # noqa: E402
import materials as MT  # noqa: E402
import spectralrad as SR  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

#: 溶融石英の公表値(Malitson 1965 の分散式から広く引かれる値の幅)。
SILICA_NG_1550 = (1.4615, 1.4635)          # 群屈折率
SILICA_ZDW_NM = (1265.0, 1280.0)           # 材料分散の零点
SILICA_D_1550 = (21.0, 23.0)               # ps/(nm·km)
G652_MFD_1310_UM = (8.6, 9.5)              # ITU-T G.652 の 1310 nm の MFD の範囲

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def chapter_dispersion():
    print("\n1. ガラスの分散(材料表の溶融石英)")
    ng = float(FO.material_group_index("SILICA", 1549.0, 1551.0, 3)[1, 1])
    D = FO.material_gvd("SILICA", 1200.0, 1350.0, 301)
    i = int(np.argmin(np.abs(D[:, 1])))
    zdw = float(D[i, 0] - D[i, 1] * (D[i + 1, 0] - D[i, 0]) / (D[i + 1, 1] - D[i, 1]))
    d1550 = float(FO.material_gvd("SILICA", 1549.0, 1551.0, 3)[1, 1])
    NUMBERS.update({"ng1550": ng, "zdw": zdw, "d1550": d1550})
    gate("群屈折率 1.55 µm = %.4f(公表 1.462 前後)" % ng, SILICA_NG_1550[0] <= ng <= SILICA_NG_1550[1])
    gate("材料分散の零点 = %.1f nm(公表 1.27 µm)" % zdw, SILICA_ZDW_NM[0] <= zdw <= SILICA_ZDW_NM[1])
    gate("D(1.55 µm) = %.2f ps/(nm·km)(公表 ≈ 22)" % d1550, SILICA_D_1550[0] <= d1550 <= SILICA_D_1550[1])
    n = MT.material_dispersion("SILICA", 1000.0, 1700.0, 71)
    g = FO.material_group_index("SILICA", 1000.0, 1700.0, 71)
    gate("群屈折率は屈折率より大きい(正常分散の領域、1.0〜1.7 µm 全点)", bool(np.all(g[:, 1] > n[:, 1])))
    return n, g, FO.material_gvd("SILICA", 1000.0, 1700.0, 71)


def chapter_modes():
    print("\n2. LP モード(特性方程式)")
    j01, j11 = float(special.jn_zeros(0, 1)[0]), float(special.jn_zeros(1, 1)[0])
    below = FO.fiber_lp_modes(j01 - 1e-3)["n_modes"]
    above = FO.fiber_lp_modes(j01 + 1e-3)["n_modes"]
    below2 = FO.fiber_lp_modes(j11 - 1e-3)["n_modes"]
    above2 = FO.fiber_lp_modes(j11 + 1e-3)["n_modes"]
    later2 = FO.fiber_lp_modes(j11 + 5e-2)["n_modes"]
    gate("単一モードの遮断 V = %.4f(J0 の零点): 0.001 下で 2、上で 6(LP11 の 4 が加わる)" % j01, below == 2 and above == 6,
         "%d → %d" % (below, above))
    gate("次の遮断 V = %.4f(J1 の零点): LP21(4)は 0.001 上で加わり、★LP02(2)は束縛が指数関数的に弱く 0.05 上で解ける" % j11,
         below2 == 6 and above2 == 10 and later2 == 12, "%d → %d → %d" % (below2, above2, later2))
    big = FO.fiber_lp_modes(30.0)
    ratio = big["n_modes"] / big["count_approx"]
    NUMBERS["count_ratio_30"] = ratio
    gate("V = 30 でモード数 %d ≈ V²/2 = %.0f(2 %% 以内)" % (big["n_modes"], big["count_approx"]), abs(ratio - 1) < 0.02)
    worst = 0.0
    for V in np.linspace(1.6, 2.4, 9):
        b = FO.fiber_lp_modes(float(V))["modes"][0]["b"]
        rn = (1.1428 - 0.996 / V) ** 2
        worst = max(worst, abs(b / rn - 1))
    NUMBERS["b_rn_worst"] = worst
    gate("LP01 の b(V) は Rudolph–Neumann の近似 (1.1428 − 0.996/V)² と 1.6 ≤ V ≤ 2.4 で 0.5 % 以内", worst < 0.005, "最大 %.2e" % worst)
    return big


def chapter_mfd():
    print("\n3. モード径(LP01 の厳密な場とガウス)")
    rows = []
    worst = 0.0
    for V in (1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4):
        m = FO.fiber_mode_field_diameter(4.1, V)
        rows.append((V, m))
        worst = max(worst, abs(m["relative_difference"]))
    NUMBERS["marcuse_worst"] = worst
    gate("Marcuse 1977 の近似式は重なり最大のガウスの MFD と 1.2 ≤ V ≤ 2.4 で 1 % 以内", worst < 0.01, "最大 %.2e" % worst)
    p_vs_g = rows[0][1]["mfd_petermann1_um"] / rows[0][1]["mfd_um"] - 1
    NUMBERS["petermann_vs_gauss_12"] = p_vs_g
    gate("★定義が違うと MFD は違う: V = 1.2 で 2 次モーメントの定義は %.0f %% 大きい(> 5 %%)" % (100 * p_vs_g), p_vs_g > 0.05)
    gate("ガウスとの重なりは V = 2.4 で 0.99 以上(単一モードファイバをガウスで扱ってよい理由)", rows[-1][1]["overlap"] > 0.99,
         "%.4f" % rows[-1][1]["overlap"])
    return rows


def chapter_smf():
    print("\n4. 標準の単一モードファイバ(ITU-T G.652 の範囲)")
    a = 4.1
    nap = FO.fiber_numerical_aperture(1.4504 + 0.0050, 1.4504)        # 溶融石英(1310 nm)のクラッドに Δn = 0.005 のコア
    na = round(nap["na"], 2)
    gate("コアとクラッドの屈折率差 0.005 で NA = %.4f(√(n₁² − n₂²) の閉形式、Δ = %.4f)" % (nap["na"], nap["delta"]),
         abs(nap["na"] / math.sqrt((1.4504 + 0.0050) ** 2 - 1.4504 ** 2) - 1.0) < 1e-12 and na == 0.12)
    v1310 = FO.fiber_v_number(a, na, 1310.0)
    v1550 = FO.fiber_v_number(a, na, 1550.0)
    m1310 = FO.fiber_mode_field_diameter(a, v1310["v"])
    m1550 = FO.fiber_mode_field_diameter(a, v1550["v"])
    NUMBERS.update({"cutoff": v1310["cutoff_wavelength_nm"], "mfd1310": m1310["mfd_um"], "mfd1550": m1550["mfd_um"]})
    gate("コア半径 4.1 µm・NA 0.12 の遮断 %.0f nm(1310 nm で単一モード)" % v1310["cutoff_wavelength_nm"],
         v1310["single_mode"] and v1550["single_mode"] and v1310["cutoff_wavelength_nm"] < 1310.0)
    gate("1310 nm の MFD %.2f µm は G.652 の 8.6〜9.5 µm に入る(1550 nm は %.2f µm、長い波長ほど広がる)"
         % (m1310["mfd_um"], m1550["mfd_um"]),
         G652_MFD_1310_UM[0] <= m1310["mfd_um"] <= G652_MFD_1310_UM[1] and m1550["mfd_um"] > m1310["mfd_um"])
    return a, na


def chapter_guide():
    print("\n5. ライトガイドの効率と NIR 照明の鎖")
    sna = 0.5
    fn = np.linspace(0.1, 0.7, 25)
    acc = np.array([FO.fiber_bundle_coupling(sna, float(f), 1.0, 1.0, 0.0, 0.0)["acceptance"] for f in fn])
    closed = np.minimum(1.0, (fn / sna) ** 2)
    worst = float(np.max(np.abs(acc - closed)))
    gate("Lambert 光源の受け入れ = (NA_束 / NA_光源)²(1 で頭打ち)を 25 点で 1e-15", worst < 1e-15, "最大 %.1e" % worst)
    b = FO.fiber_bundle_coupling(0.5, 0.55, 0.8, 1.62, 2.0, 0.3)
    prod = b["packing"] * b["fresnel"] * b["acceptance"] * b["attenuation"]
    gate("全体の効率 = 充填率 × Fresnel × 受け入れ × 減衰(%.3f)" % b["transmission"], abs(prod - b["transmission"]) < 1e-15)
    lo, hi, n = 900.0, 1300.0, 401
    led = SR.energy_to_photons(SR.led_spectrum(1065.0, 50.0, lo, hi, n))
    led[:, 1] /= SR.spectral_integral(led)
    T = MT.material_transmittance("SI", 0.775, lo, hi, n)
    qe = SR.silicon_photodiode_qe(3.0, 0.0, None, lo, hi, n)
    y = SR.spectral_integral(SR.spectral_product(SR.spectral_product(led, T), qe))
    chain = b["transmission"] * y
    NUMBERS.update({"guide": b["transmission"], "chain_yield": chain})
    gate("LED → ライトガイド(2 m)→ Si ウェハ 775 µm → Si センサ: 光子 1 個あたり %.2e 電子(ガイドの %.2f 倍が失われずに残る)"
         % (chain, b["transmission"]), 0 < chain < y)
    return fn, acc, closed, b


def make_figures(disp, big, mfd_rows, guide):
    n, g, D = disp
    figs.save_plot("silica_dispersion", [("屈折率 n", n[:, 0], n[:, 1]), ("群屈折率 n_g", g[:, 0], g[:, 1])],
                   xlabel="波長 [nm]", ylabel="屈折率", title="溶融石英: 群屈折率は 1.55 µm で %.4f" % NUMBERS["ng1550"],
                   caption="パルスの包絡は c/n_g で進む。材料表の溶融石英(Malitson 1965)から差分で求めた。")
    figs.save_plot("silica_gvd", [("D(λ)", D[:, 0], D[:, 1]), ("0", D[:, 0], 0 * D[:, 1])], xlabel="波長 [nm]",
                   ylabel="ps/(nm·km)", styles=[None, "dashed"], colors=["emphasis", "reference"],
                   title="材料分散の零点 %.0f nm、1.55 µm で %.1f ps/(nm·km)" % (NUMBERS["zdw"], NUMBERS["d1550"]),
                   caption="零点より短い波長は正常分散(青が遅い)、長い波長は異常分散。単一モードファイバの零分散 1.3 µm の大半はこの材料分散。")
    Vs = np.linspace(0.5, 8.0, 151)
    curves = {}
    for V in Vs:
        for m in FO.fiber_lp_modes(float(V))["modes"]:
            curves.setdefault((m["l"], m["m"]), []).append((V, m["b"]))
    order = sorted((k for k, v in curves.items() if len(v) > 2), key=lambda k: curves[k][0][0])[:10]   # 現れる順
    series = [("LP%d%d" % k, np.array([p[0] for p in curves[k]]), np.array([p[1] for p in curves[k]])) for k in order]
    figs.save_plot("lp_b_v_diagram", series, xlabel="規格化周波数 V", ylabel="規格化伝搬定数 b", ylim=(0.0, 1.0),
                   styles=[None] * 5 + ["dashed"] * 5,
                   title="LP モードの b–V 図(特性方程式の数値解)",
                   caption="各モードは Bessel の零点(LP11 = 2.405、LP21 と LP02 = 3.832 …)で b = 0 から立ち上がる。V < 2.405 なら LP01 だけ —— 単一モード。")
    V = np.array([r[0] for r in mfd_rows])
    figs.save_plot("mode_field_diameter", [("重なり最大のガウス", V, np.array([r[1]["mfd_um"] for r in mfd_rows])),
                                           ("Marcuse 1977", V, np.array([r[1]["mfd_marcuse_um"] for r in mfd_rows])),
                                           ("2 次モーメント(Petermann I)", V, np.array([r[1]["mfd_petermann1_um"] for r in mfd_rows]))],
                   xlabel="V", ylabel="MFD [µm](コア半径 4.1 µm)", styles=[None, "dashed", None],
                   colors=["emphasis", "reference", "wrong"], title="モード径: 近似式は 1 % 以内、定義を変えると 11 % 違う",
                   caption="V が小さいほど場がクラッドへ染み出し、指数関数の裾が 2 次モーメントを押し上げる。")
    m = FO.fiber_mode_field_diameter(4.1, 2.0)
    r = np.linspace(0.0, 3.0, 301)
    e = np.where(r <= 1.0, special.jv(0, m["u"] * r) / special.jv(0, m["u"]), special.kv(0, m["w"] * np.maximum(r, 1e-9)) / special.kv(0, m["w"]))
    w0 = m["mfd_um"] / 2 / 4.1
    figs.save_plot("lp01_field", [("LP01 の厳密な場", r, e), ("重なり最大のガウス", r, np.exp(-(r / w0) ** 2))],
                   xlabel="r / a", ylabel="場(中心で 1)", styles=[None, "dashed"], colors=["emphasis", "reference"],
                   title="V = 2.0 の LP01: 重なり %.4f" % m["overlap"],
                   caption="コアの中は J0、外は K0。ガウスとの差は主に裾(r/a > 1.5)。")
    fn, acc, closed, b = guide
    figs.save_plot("light_guide_acceptance", [("op", fn, acc), ("(NA_束/NA_光源)²", fn, closed)], xlabel="束の NA(光源 NA 0.5)",
                   ylabel="入る割合", kinds=["scatter", "line"], colors=["emphasis", "reference"], ylim=(0.0, 1.05),
                   title="Lambert の LED を束に入れる割合",
                   caption="光源より NA の小さい束は、立体角の比 (NA_束/NA_光源)² しか受け取らない。全体の効率 = 充填率 × 端面 × 受け入れ × 減衰。")


def main():
    t0 = time.time()
    print("PoC 光ファイバとライトガイド(予算 %s)" % ("reduced" if REDUCED else "full"))
    disp = chapter_dispersion()
    big = chapter_modes()
    mfd_rows = chapter_mfd()
    chapter_smf()
    guide = chapter_guide()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(disp, big, mfd_rows, guide)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
