# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: Si ウェハ越しの近赤外透過検査 —— 光源 × ウェハ × センサの波長積分で、何 nm の LED を選ぶかを決める。

【問い】Si のダイやウェハの裏側(配線・アライメントマーク・ボンディングの欠陥)は、Si が透ける近赤外の光で
見る。ところが **Si のウェハが透ける波長(> 1.1 µm)は、Si のセンサが感じない波長**でもある ——
同じ材料の吸収端が、観察対象では窓に、センサでは壁になる(矛盾)。安い Si センサで見るなら、どの LED が
最も明るく・最もノイズの少ない像になるか。ウェハの厚さでその答えは動くか。

材料表(`materials`、第 1〜2 段)の Si の n,k(Green 2008)を、**観察対象(ウェハの透過率)とセンサ
(フォトダイオードの QE)の両方**に使う。新 op 9 本(`spectralrad`): 光源の分光分布(Planck・CIE A・LED)、
帯域通過フィルタ、Si フォトダイオードの QE、エネルギー → 光子数、曲線の積と積分。6 章:

  1. **光源**: CIE A の表(300 / 560 / 780 nm)を定義式で再現、黒体は Wien と Stefan–Boltzmann、LED と
     フィルタの FWHM は指定どおり。
  2. **センサ**: QE = (1 − R)[1 − e^{−αW}] は閉形式、W → ∞ で 1 − R、集める深さが深いほど NIR が伸びる。
     ★エネルギーと光子数を混ぜると 1100 nm で 2 倍(λ 比)の誤り。
  3. **波長の矛盾**: LED のピーク(FWHM 50 nm、光子数をそろえる)を 850〜1200 nm で振り、ウェハ厚ごとに
     電子数が最大になるピークを探す。門: 狭い線の極限で積分 = T(λ)·QE(λ)、最良のピークは厚いほど長波長へ
     単調に動き、どれも走査の内側(50 µm → 935 nm、775 µm → 1065 nm)。★所見: 定番の 1050 nm の LED は
     厚いウェハでは最良と 5 % 差だが、**薄いダイ(50 µm)では最良の 1/3.4** しか電子が出ない。ウェハが最も
     透ける 1200 nm は Si センサでは最良の 1/28。集める深さを 3 → 50 µm にすると電子は 16 倍だが、最良の
     ピークは動かない(最適はウェハが決める)。
  4. **像**: 775 µm ウェハの裏の配線パターンを、最良の LED と 1050 / 1200 nm で撮る(光子のショット雑音 +
     読出し雑音)。最良の LED で CNR 20 にするには開口 1 画素に約 1.2e6 光子が要る(Si センサの歩留まりは
     光子 1 万個で電子 3〜4 個)。門: 雑音前の電子数 = 波長積分(1e-12)、分散 = 平均 + 読出し²、
     像から測った CNR = 理論 e/√(e + 読出し²)(10 % 以内)。
  5. **焦点**: ウェハの厚さ分だけ機械的に下げると、像は t(1 − 1/n) = 556 µm ずれて回折限界の像が崩れる
     (`pupil_blur`、波面の defocus に換算)。補正した焦点で縁幅が戻る。
  6. **3-D のシーンで撮る**(2026-10-15、`optscene` の波長積分): 第 4 章は配線の絵を手で描いて電子数を掛けた。
     ここでは同じウェハ(材料表の Si、k から吸収)・裏の配線・バックライト・テレセンのレンズ・Si センサを 3-D に置き、
     `layout_capture(mode="spectral")` で LED のスペクトルを数本の波長に割って光線で撮る。門: 開口の画素の
     電子/光子が、この章で独立に書いた波長積分 ∫LED·λ·(1 − R)²e^{−αt}·QE / ∫LED と 4 % 以内(光線追跡と
     曲線の積は別の実装)、850 nm ではウェハが不透明(1e-10 未満)、配線の影は幾何の真値の画素と 1 画素も違わない、
     像から測った CNR = 理論。★レンダラは板の中の多重反射を追わないので、第 3 章の積分(多重反射込み)より
     少し暗い —— その差も数として出す。

【外部真値】CIE 15:2004 の標準イルミナント A(式と表)、Planck・Wien・Stefan–Boltzmann(SI 2019 の定数)、
Green 2008 の Si の n,k(refractiveindex.info database、CC0)、Poisson 雑音の分散 = 平均。
【学習した数】0。【較正】0。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import materials as MT  # noqa: E402
import optics  # noqa: E402
import optscene as OS  # noqa: E402
import spectralrad as SR  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

#: CIE 15:2004 の標準イルミナント A の表の値。
CIE_A_TABLE = {300.0: 0.930483, 560.0: 100.0, 780.0: 241.675}
WIEN_B_UM_K = 2897.771955          # µm·K(CODATA)
SIGMA_SB = 5.670374419e-8          # W m⁻² K⁻⁴(CODATA)

THICKNESS_UM = [50.0, 150.0, 300.0, 775.0]
PEAKS_NM = np.arange(850.0, 1201.0, 5.0)
LED_FWHM_NM = 50.0
COLLECTION_UM = 3.0                # 裏面照射 CMOS の目安
GRID = (700.0, 1350.0, 651)        # 光源・ウェハ・センサを同じ波長格子で掛ける(1 nm 刻み)

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _at(curve, x):
    return float(np.interp(x, curve[:, 0], curve[:, 1]))


# --------------------------------------------------------------------------- #
# 1. 光源                                                                       #
# --------------------------------------------------------------------------- #
def chapter_sources():
    print("\n1. 光源の分光分布(Planck・CIE A・LED・フィルタ)")
    A = SR.cie_illuminant_a(300.0, 830.0, 107)
    worst = max(abs(_at(A, w) - v) / v for w, v in CIE_A_TABLE.items())
    gate("CIE 標準イルミナント A の表(300 / 560 / 780 nm)を定義式で再現(相対 5e-6)", worst < 5e-6, "最大 %.1e" % worst)
    wien, sb = 0.0, 0.0
    for T in (2856.0, 5772.0):
        st = SR.spectral_stats(SR.blackbody_spectrum(T, 100.0, 100000.0, 200000 if not REDUCED else 100000))
        wien = max(wien, abs(st["peak_nm"] - WIEN_B_UM_K * 1e3 / T))
        sb = max(sb, abs(st["integral"] * math.pi / (SIGMA_SB * T ** 4) - 1.0))
    gate("黒体のピークは Wien の変位則(2856 K → 1015 nm、5772 K → 502 nm、格子 1 nm 以内)", wien < 1.0, "最大 %.2f nm" % wien)
    gate("全放射 πL を積分すると Stefan–Boltzmann の σT⁴(相対 1e-4)", sb < 1e-4, "最大 %.1e" % sb)
    w_led = [SR.spectral_stats(SR.led_spectrum(1050.0, LED_FWHM_NM, 800.0, 1300.0, 5001, model=m))["fwhm_nm"] for m in ("ohno", "gaussian")]
    w_bp = SR.spectral_stats(SR.bandpass_spectrum(1100.0, 40.0, 0.9, 4, 0.0, 800.0, 1400.0, 6001))["fwhm_nm"]
    gate("LED(Ohno 2005・Gauss)とフィルタの半値全幅は指定どおり(1e-3 nm)",
         max(abs(w - LED_FWHM_NM) for w in w_led) < 1e-3 and abs(w_bp - 40.0) < 1e-3,
         "LED %.4f / %.4f nm、フィルタ %.4f nm" % (w_led[0], w_led[1], w_bp))
    return A


# --------------------------------------------------------------------------- #
# 2. センサ                                                                     #
# --------------------------------------------------------------------------- #
def chapter_sensor():
    print("\n2. Si フォトダイオードの量子効率(材料表の Si の n,k から)")
    qs = {W: SR.silicon_photodiode_qe(W, 0.0, None, 400.0, 1200.0, 801) for W in (1.0, 3.0, 10.0, 50.0)}
    lam = qs[3.0][:, 0]
    c = MT.material_optical_constants("SI", 1000.0)
    rec = [MT.material_optical_constants("SI", float(w)) for w in (600.0, 900.0, 1050.0)]
    worst = max(abs(_at(qs[3.0], r["wavelength_nm"]) - (1 - r["reflectance_normal"]) * (1 - math.exp(-r["alpha_per_cm"] * 3e-4)))
                for r in rec)
    gate("QE = (1 − R)[1 − e^{−αW}] を材料表の R と α から閉形式で(600 / 900 / 1050 nm、1e-12)", worst < 1e-12, "最大 %.1e" % worst)
    thick = SR.silicon_photodiode_qe(1e5, 0.0, None, 400.0, 700.0, 31)
    one_minus_r = np.array([1 - MT.material_optical_constants("SI", float(w))["reflectance_normal"] for w in thick[:, 0]])
    gate("集める深さ → ∞ で QE = 1 − R(全光子が吸収される、400〜700 nm)", float(np.max(np.abs(thick[:, 1] - one_minus_r))) < 1e-9)
    r1050 = {W: _at(q, 1050.0) for W, q in qs.items()}
    NUMBERS.update({"qe1050_w%g" % W: v for W, v in r1050.items()})
    gate("1050 nm の QE は集める深さで単調に伸びる(1 → 50 µm)", r1050[1.0] < r1050[3.0] < r1050[10.0] < r1050[50.0],
         " / ".join("W %g µm %.3f" % kv for kv in r1050.items()))
    e = SR.blackbody_spectrum(3000.0, 500.0, 1200.0, 701)
    ph = SR.energy_to_photons(e)
    ratio = (_at(ph, 1100.0) / _at(e, 1100.0)) / (_at(ph, 550.0) / _at(e, 550.0))
    NUMBERS["photon_ratio"] = ratio
    gate("★エネルギーと光子数: QE を掛ける前に λ/hc を掛ける(1100 nm と 550 nm で重みが 2 倍違う)", abs(ratio - 2.0) < 1e-12, "%.6f" % ratio)
    _ = c, lam
    return qs


# --------------------------------------------------------------------------- #
# 3. 波長の矛盾                                                                  #
# --------------------------------------------------------------------------- #
def _electrons(peak_nm, thickness_um, collection_um=COLLECTION_UM, fwhm_nm=LED_FWHM_NM):
    """LED(ピーク peak_nm)→ Si ウェハ(厚さ、多重反射込み)→ Si センサ の相対電子数。"""
    lo, hi, n = GRID
    led = SR.energy_to_photons(SR.led_spectrum(peak_nm, fwhm_nm, lo, hi, n))
    led[:, 1] /= SR.spectral_integral(led)                          # 光子数 1 に規格化(同じ電力ではなく同じ光子数)
    T = MT.material_transmittance("SI", thickness_um / 1000.0, lo, hi, n)
    qe = SR.silicon_photodiode_qe(collection_um, 0.0, None, lo, hi, n)
    return SR.spectral_integral(SR.spectral_product(SR.spectral_product(led, T), qe))


def chapter_contradiction():
    print("\n3. 波長の矛盾: ウェハは長波長で透け、センサは長波長で感じない")
    lo, hi, n = GRID
    narrow = SR.led_spectrum(1100.0, 0.5, 1090.0, 1110.0, 2001)
    T = MT.material_transmittance("SI", 0.775, lo, hi, n)
    qe = SR.silicon_photodiode_qe(COLLECTION_UM, 0.0, None, lo, hi, n)
    lim = SR.spectral_integral(SR.spectral_product(SR.spectral_product(narrow, T), qe)) / SR.spectral_integral(narrow)
    exact = _at(T, 1100.0) * _at(qe, 1100.0)
    gate("狭い線(FWHM 0.5 nm)の極限で ∫LED·T·QE / ∫LED = T(1100)·QE(1100)(相対 1e-3)", abs(lim / exact - 1) < 1e-3,
         "%.4e vs %.4e" % (lim, exact))
    sig = {t: np.array([_electrons(p, t) for p in PEAKS_NM]) for t in THICKNESS_UM}
    best = {t: float(PEAKS_NM[int(np.argmax(s))]) for t, s in sig.items()}
    NUMBERS.update({"best_%g" % t: b for t, b in best.items()})
    NUMBERS.update({"yield_%g" % t: float(s.max()) for t, s in sig.items()})
    order = [best[t] for t in THICKNESS_UM]
    interior = all(PEAKS_NM[0] < b < PEAKS_NM[-1] for b in order)
    gate("最良の LED のピークは厚いほど長波長へ動き(50 → 775 µm で単調)、どれも走査の端でない(内側の最適)",
         interior and all(a < b for a, b in zip(order, order[1:])),
         " / ".join("%g µm → %.0f nm" % (t, b) for t, b in best.items()))
    i1050 = int(np.argmin(np.abs(PEAKS_NM - 1050.0)))
    thin = float(sig[50.0].max() / sig[50.0][i1050])
    thick = float(sig[775.0].max() / sig[775.0][i1050])
    NUMBERS.update({"thin_vs_1050": thin, "thick_vs_1050": thick})
    gate("★定番の 1050 nm の LED は、厚いウェハ(775 µm)では最良と 10 %% 以内だが、薄いダイ(50 µm)では最良の 1/%.1f しか電子が出ない" % thin,
         thick < 1.10 and thin > 2.0, "775 µm: 最良/1050 = %.3f、50 µm: %.2f" % (thick, thin))
    s775 = sig[775.0]
    i1200 = int(np.argmin(np.abs(PEAKS_NM - 1200.0)))
    NUMBERS["gain_vs_1200"] = float(s775.max() / s775[i1200])
    gate("775 µm: ウェハが最もよく透ける 1200 nm の LED は最良の 1/%.0f(Si センサには見えない)" % NUMBERS["gain_vs_1200"],
         NUMBERS["gain_vs_1200"] > 20.0)
    deep = np.array([_electrons(p, 775.0, collection_um=50.0) for p in PEAKS_NM])
    NUMBERS["best_775_deep"] = float(PEAKS_NM[int(np.argmax(deep))])
    NUMBERS["deep_gain"] = float(deep.max() / s775.max())
    gate("集める深さ 3 → 50 µm(NIR 強化のセンサ)で電子は %.0f 倍、最良のピークは %.0f → %.0f nm(最適はウェハが決める)"
         % (NUMBERS["deep_gain"], best[775.0], NUMBERS["best_775_deep"]),
         NUMBERS["deep_gain"] > 10.0 and abs(NUMBERS["best_775_deep"] - best[775.0]) <= 10.0)
    return sig, best, deep


# --------------------------------------------------------------------------- #
# 4. 像                                                                         #
# --------------------------------------------------------------------------- #
def _pattern(size):
    """ウェハ裏の配線パターン(1 = 開口、0 = 金属で遮光): 線と間隔の 3 組 + 十字のアライメントマーク。"""
    img = np.ones((size, size))
    y, x = np.mgrid[0:size, 0:size]
    for k, (w, x0) in enumerate(((2, 8), (4, 48), (8, 88))):
        band = (y > 10) & (y < size // 2 - 6) & (x >= x0) & (x < x0 + 36)
        img[band & (((x - x0) // w) % 2 == 0)] = 0.0
    c = (size // 2 + 30, size // 2)
    img[(np.abs(y - c[0]) < 3) & (np.abs(x - c[1]) < 30)] = 0.0
    img[(np.abs(x - c[1]) < 3) & (np.abs(y - c[0]) < 30)] = 0.0
    return img


def chapter_image(best):
    print("\n4. 像: 775 µm のウェハ越しに裏の配線を撮る(ショット雑音 + 読出し雑音)")
    size = 96 if REDUCED else 160
    pat = _pattern(size)
    read_e = 5.0
    y_best = _electrons(best[775.0], 775.0)
    target = 20.0                                                  # 最良の LED で CNR 20 になる露光を選ぶ
    e_need = 0.5 * (target ** 2 + math.sqrt(target ** 4 + 4 * target ** 2 * read_e ** 2))
    photons_per_px = e_need / y_best                               # 開口部に届く光子(LED の出力 × 露光)
    NUMBERS["photons_per_px"] = photons_per_px
    gate("775 µm 越しに CNR 20 を得るには、開口 1 画素に %.2e 光子(Si センサの歩留まり %.1e 電子/光子)" % (photons_per_px, y_best),
         abs(photons_per_px * y_best - e_need) < 1e-9 * e_need)
    rng = np.random.default_rng(20261014)
    shots = {}
    for label, peak in (("1050 nm", 1050.0), ("最良 %.0f nm" % best[775.0], best[775.0]), ("1200 nm", 1200.0)):
        e_open = photons_per_px * _electrons(peak, 775.0)
        clean = pat * e_open
        noisy = rng.poisson(clean).astype(np.float64) + rng.normal(0.0, read_e, clean.shape)
        shots[label] = (e_open, clean, noisy)
    lab_best = [k for k in shots if k.startswith("最良")][0]
    e_open, clean, noisy = shots[lab_best]
    gate("開口部の雑音前の電子数 = 光子数 × ∫LED·T·QE(1e-12)",
         abs(float(clean[pat == 1].mean()) - photons_per_px * _electrons(best[775.0], 775.0)) < 1e-12 * e_open)
    flat = rng.poisson(np.full((256, 256), e_open)).astype(np.float64) + rng.normal(0.0, read_e, (256, 256))
    var_ratio = float(flat.var() / (e_open + read_e ** 2))
    gate("一様な開口の分散 = 平均 + 読出し²(Poisson + Gauss、3 % 以内)", abs(var_ratio - 1) < 0.03, "%.4f" % var_ratio)
    cnr, cnr_th = {}, {}
    for k, (eo, cl, nz) in shots.items():
        cnr[k] = float((nz[pat == 1].mean() - nz[pat == 0].mean()) / nz[pat == 1].std())
        cnr_th[k] = eo / math.sqrt(eo + read_e ** 2)
    NUMBERS.update({"cnr_" + k.split()[0]: v for k, v in cnr.items()})
    worst = max(abs(cnr[k] / cnr_th[k] - 1) for k in cnr)
    gate("像から測った CNR = 理論 e/√(e + 読出し²)(3 つの LED、10 % 以内)", worst < 0.10,
         " / ".join("%s 測 %.1f 理 %.1f" % (k, cnr[k], cnr_th[k]) for k in cnr))
    gate("理論 CNR の順: 最良 ≥ 1050 nm ≫ 1200 nm(1200 nm の像は配線が雑音に沈む)",
         cnr_th[lab_best] >= cnr_th["1050 nm"] > 3.0 * cnr_th["1200 nm"])
    return pat, shots, cnr


# --------------------------------------------------------------------------- #
# 5. 焦点                                                                       #
# --------------------------------------------------------------------------- #
def _edge_width(img, row):
    """行 row の暗 → 明の縁の 10–90 % 幅 [px](十字の左腕の端、線形補間)。"""
    p = img[row].astype(np.float64)
    p = (p - p.min()) / max(np.ptp(p), 1e-12)
    centre = len(p) // 2
    seg = p[centre + 20:centre + 45]
    i10 = np.argmax(seg >= 0.1)
    i90 = np.argmax(seg >= 0.9)
    return float(i90 - i10)


def chapter_focus(pat, best):
    print("\n5. 焦点: ウェハの厚さだけ機械的に下げると、像は t(1 − 1/n) ずれる")
    wl = best[775.0]
    pf = MT.plate_focus_shift("SI", 0.775, wl, 0.1)
    shift_um = pf["paraxial_shift_mm"] * 1e3
    n = MT.material_optical_constants("SI", wl)["n"]
    gate("焦点ずれ = t(1 − 1/n)(%.0f nm で n = %.3f → %.0f µm)、球面収差は焦点ずれの 1 %% 未満" % (wl, n, shift_um),
         abs(shift_um - 775.0 * (1 - 1 / n)) < 1e-9 and pf["spherical_aberration_mm"] * 1e3 < 0.01 * shift_um)
    fno = 5.0                                                      # NA 0.1
    pitch = 5.0
    pupil = (np.hypot(*np.mgrid[-1:1:64j, -1:1:64j]) <= 1.0).astype(float)
    w20 = optics.defocus_from_shift(shift_um, wl / 1000.0, fno)
    w20 = float(w20["defocus_waves"] if isinstance(w20, dict) else w20)
    sharp = np.asarray(fs.pupil_blur(pat, pupil, 0.0, wl / 1000.0, fno, pitch), dtype=np.float64)
    blurred = np.asarray(fs.pupil_blur(pat, pupil, w20, wl / 1000.0, fno, pitch), dtype=np.float64)
    row = pat.shape[0] // 2 + 30
    e_sharp, e_blur = _edge_width(sharp, row), _edge_width(blurred, row)
    NUMBERS.update({"w20": w20, "edge_sharp": e_sharp, "edge_blur": e_blur, "shift_um": shift_um})
    gate("補正しない焦点(W20 = %.1f 波長)は縁の 10–90 %% 幅が補正後の 3 倍以上(%.0f px vs %.0f px)" % (w20, e_blur, e_sharp),
         e_blur >= 3.0 * max(e_sharp, 1.0))
    return sharp, blurred, w20, shift_um


# --------------------------------------------------------------------------- #
# 6. 3-D のシーンで撮る(optscene の波長積分)                                     #
# --------------------------------------------------------------------------- #
#: 裏の配線(中心 x, y と半幅 hx, hy [mm])。線と間隔の 3 組(0.2 / 0.4 / 0.8 mm = 2 / 4 / 8 画素)と十字。
WIRES = [(x0 + w / 2 + 2 * k * w, -2.0, w / 2, 1.6) for w, x0 in ((0.2, -4.0), (0.4, -1.4), (0.8, 1.2)) for k in range(3)]
WIRES += [(0.0, 2.4, 2.0, 0.15), (0.0, 2.4, 0.15, 1.5)]


def _wafer_scene(t_um):
    """Si ウェハ(材料表の n と k の吸収)の裏に、光を通さない配線を貼った 3-D のシーン。"""
    si = OS.scene_material("dielectric", glass="SI", absorption_from_k=True)
    t = t_um / 1000.0
    objs = [OS.scene_box((0.0, 0.0, 1.0 + t / 2), (12.0, 12.0, t / 2), si)]
    dark = OS.scene_material("lambert", albedo=0.0)
    objs += [OS.scene_box((cx, cy, 0.975), (hx, hy, 0.025), dark) for cx, cy, hx, hy in WIRES]
    return objs


def _backlight(peak_nm):
    return OS.light_spec("backlight", source="led", wavelength_nm=peak_nm, bandwidth_nm=LED_FWHM_NM,
                         radius_mm=40.0, height_mm=60.0, n=8, size_mm=60.0)


def _single_pass_integral(peak_nm, t_um):
    """独立の経路: ∫ S(λ)·(λ/550)·(1 − R)²·e^{−αt}·QE(λ) dλ / ∫ S(λ) dλ(1 nm より細かい格子の台形則)。

    S は Ohno の LED(峰 ± 1.5 半値全幅)、R・α は材料表の Si の n,k(垂直入射)、QE は第 2 章の Si フォトダイオード。
    レンダラと同じく板の中の多重反射は入れない(入れた値との差は別に数える)。
    """
    lo, hi = peak_nm - 1.5 * LED_FWHM_NM, peak_nm + 1.5 * LED_FWHM_NM
    led = SR.led_spectrum(peak_nm, LED_FWHM_NM, lo, hi, 1501)
    lam = led[:, 0]
    qe = SR.silicon_photodiode_qe(COLLECTION_UM, 0.0, None, lo, hi, 1501)[:, 1]
    c = [MT.material_optical_constants("SI", float(v)) for v in lam]
    t1 = np.array([(1 - r["reflectance_normal"]) ** 2 * math.exp(-r["alpha_per_cm"] * t_um * 1e-4) for r in c])
    y = led[:, 1] * (lam / 550.0) * t1 * qe
    return float(np.trapezoid(y, lam) / np.trapezoid(led[:, 1], lam))


def chapter_scene(best, photons_per_px):
    print("\n6. 3-D のシーンで撮る: ウェハ・裏の配線・バックライト・テレセンのレンズ・Si センサ(optscene の波長積分)")
    res, K = (48, 9) if REDUCED else (96, 15)
    qe = SR.silicon_photodiode_qe(COLLECTION_UM, 0.0, None, 700.0, 1350.0, 651)
    sensor = OS.sensor_spec(pixel_um=20.0 * 96 / res, resolution=(res, res), qe_curve=qe)   # 視野 9.6 mm(物体側の画素 0.1 mm × 96)
    lens = OS.lens_spec(focal_mm=25.0, f_number=4.0, working_distance_mm=150.0, telecentric=True)
    scene = _wafer_scene(775.0)
    cam = OS.vision_layout(sensor, lens, [_backlight(1050.0)], scene=scene)["camera"]
    # 平らな視野(ウェハなしでバックライトを直接)で割る = フラットフィールド補正。発光点の粗さの模様が消え、
    # 画素の値がそのまま「光源のエネルギー 1 あたりの T·QE·λ/550」になる
    nothing = [OS.scene_box((1000.0, 0.0, 0.0), (0.1, 0.1, 0.1))]
    flat = OS.render_optscene(nothing, cam, [_backlight(1050.0)])[..., 0]
    o, _d = OS.camera_rays(cam)                                    # テレセン: 光線の原点の xy = 物体の xy
    x, y = o[:, 0].reshape(res, res), o[:, 1].reshape(res, res)
    pad = 0.75 * cam["object_pixel_mm"]
    inside = np.zeros((res, res), bool)
    near = np.zeros((res, res), bool)
    for cx, cy, hx, hy in WIRES:
        inside |= (np.abs(x - cx) < hx - pad) & (np.abs(y - cy) < hy - pad)
        near |= (np.abs(x - cx) < hx + pad) & (np.abs(y - cy) < hy + pad)
    open_ = ~near
    leds = {"850 nm": 850.0, "最良 %.0f nm" % best[775.0]: best[775.0], "1050 nm": 1050.0, "1200 nm": 1200.0}
    shots, rel, ratio_img = {}, {}, {}
    cpu0 = time.process_time()
    for label, peak in leds.items():
        lay = OS.vision_layout(sensor, lens, [_backlight(peak)], scene=scene)
        cap = OS.layout_capture(lay, supersample=1, raw=True, mode="spectral", spectral_samples=K,
                                apply_diffraction=False)
        per_energy = cap["radiance"][..., 0] / (flat * lens["transmission"])
        photon_norm = sum(t["weight"] * t["photon_ratio"] for t in cap["spectral_terms"])
        ratio_img[label] = per_energy
        e_per_photon = per_energy / photon_norm                    # 電子 / 光子(第 3 章と同じ規格化)
        shots[label] = e_per_photon
        rel[label] = float(per_energy[open_].mean()) / _single_pass_integral(peak, 775.0) - 1.0
    NUMBERS["scene_cpu_s"] = time.process_time() - cpu0
    lab_best = [k for k in leds if k.startswith("最良")][0]
    worst = max(abs(rel[k]) for k in leds if k != "850 nm")
    NUMBERS["scene_vs_integral"] = worst
    gate("光線で撮った開口の画素 = 独立に書いた波長積分 ∫LED·λ·(1 − R)²e^{−αt}·QE / ∫LED(%d 本の波長、4 %% 以内)" % K,
         worst < 0.04, " / ".join("%s %+.2f %%" % (k, 100 * rel[k]) for k in leds if k != "850 nm"))
    spread = max(float(ratio_img[k][open_].std() / ratio_img[k][open_].mean()) for k in leds if k != "850 nm")
    gate("開口の画素はどれも同じ値(フラットフィールド補正の後、相対 1e-9)", spread < 1e-9, "最大 %.1e" % spread)
    opaque = float(ratio_img["850 nm"][open_].mean() / ratio_img[lab_best][open_].mean())
    want = _single_pass_integral(850.0, 775.0) / _single_pass_integral(best[775.0], 775.0)
    NUMBERS["opaque_850"] = opaque
    gate("850 nm ではウェハが不透明: 開口でも最良の LED の 1e-7 未満(積分は %.1e、裾の 925 nm 側だけが漏れる)" % want,
         opaque < 1e-7 and want < 1e-7, "%.1e" % opaque)
    dark = max(float(ratio_img[k][inside].max() / ratio_img[k][open_].mean()) for k in leds if k != "850 nm")
    gate("配線の影は幾何の真値どおり(配線の内側の画素は 0、開口の画素は全部明るい)",
         dark == 0.0 and all(float(ratio_img[k][open_].min()) > 0.0 for k in leds if k != "850 nm"))
    ch3 = _electrons(best[775.0], 775.0)
    NUMBERS["scene_vs_ch3"] = float(shots[lab_best][open_].mean() / ch3)
    c = MT.material_optical_constants("SI", best[775.0])
    mr = 1.0 / (1.0 - c["reflectance_normal"] ** 2 * math.exp(-2.0 * c["alpha_per_cm"] * 775e-4))
    led = SR.energy_to_photons(SR.led_spectrum(best[775.0], LED_FWHM_NM, *GRID))
    tail = 1.0 - SR.spectral_integral(led, best[775.0] - 1.5 * LED_FWHM_NM, best[775.0] + 1.5 * LED_FWHM_NM) / SR.spectral_integral(led)
    NUMBERS.update({"multi_reflection": mr, "led_tail": tail})
    gate("第 3 章(多重反射込み・LED の全幅で光子数を規格化)と 4 %% 以内: レンダラ / 第 3 章 = %.3f。内訳 —— 板の中の往復(第 3 章だけ)"
         "×%.3f、LED の ±1.5 半値全幅の外の光子 %.1f %%(第 3 章だけが数える)、波長 %d 本の誤差 %+.1f %%"
         % (NUMBERS["scene_vs_ch3"], mr, 100 * tail, K, 100 * rel[lab_best]),
         abs(NUMBERS["scene_vs_ch3"] - 1.0) < 0.04)
    rng = np.random.default_rng(20261015)
    read_e = 5.0
    noisy, cnr, cnr_th = {}, {}, {}
    for k, e in shots.items():
        clean = photons_per_px * e
        nz = rng.poisson(clean).astype(np.float64) + rng.normal(0.0, read_e, clean.shape)
        noisy[k] = (clean, nz)
        eo = float(clean[open_].mean())
        cnr_th[k] = eo / math.sqrt(eo + read_e ** 2)
        cnr[k] = float((nz[open_].mean() - nz[inside].mean()) / nz[open_].std())
    worst_cnr = max(abs(cnr[k] / cnr_th[k] - 1) for k in leds if k not in ("850 nm",))
    gate("撮った像の CNR = 理論 e/√(e + 読出し²)(第 4 章と同じ光子数、10 % 以内)", worst_cnr < 0.10,
         " / ".join("%s 測 %.1f 理 %.1f" % (k, cnr[k], cnr_th[k]) for k in leds))
    print("   (光線で撮った 4 枚の CPU 時間 %.1f s)" % NUMBERS["scene_cpu_s"])
    return noisy, cnr, open_


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(A, qs, contra, img, focus, scene=None):
    sig, best, deep = contra
    pat, shots, cnr = img
    sharp, blurred, w20, shift_um = focus
    lo, hi, n = GRID
    T775 = MT.material_transmittance("SI", 0.775, lo, hi, n)
    q3 = SR.silicon_photodiode_qe(3.0, 0.0, None, lo, hi, n)
    q50 = SR.silicon_photodiode_qe(50.0, 0.0, None, lo, hi, n)
    floor = 1e-7                                                   # 表示の床(これより小さい値は床に置く、図の注に明記)
    lg = lambda v: np.log10(np.maximum(v, floor))
    prod = T775[:, 1] * q3[:, 1]
    figs.save_plot("wavelength_contradiction",
                   [("Si ウェハ 775 µm の透過率", T775[:, 0], lg(T775[:, 1])),
                    ("Si センサの QE(集める深さ 3 µm)", q3[:, 0], lg(q3[:, 1])),
                    ("Si センサの QE(50 µm)", q50[:, 0], lg(q50[:, 1])),
                    ("積 T·QE(3 µm)", T775[:, 0], lg(prod))],
                   xlabel="波長 [nm]", ylabel="log10(透過率 / 量子効率)", ylim=(-7.2, 0.2),
                   colors=["reference", "emphasis", "right", "wrong"], styles=[None, None, "dashed", None],
                   title="同じ Si の吸収端が、ウェハでは窓・センサでは壁になる",
                   caption="ウェハは 1.1 µm より長波長で透け、Si センサは同じ波長で感じなくなる。積は 1065 nm 付近で最大 %.1e —— 光子 1 万個で電子 3〜4 個。1e-7 未満は図の床に置いた。" % prod.max())
    figs.save_plot("best_led_vs_thickness", [("%g µm" % t, PEAKS_NM, s / s.max()) for t, s in sig.items()],
                   xlabel="LED のピーク波長 [nm](FWHM 50 nm、光子数をそろえる)", ylabel="電子数(厚さごとに最大で規格化)",
                   title="最良の LED のピークはウェハの厚さで動く",
                   caption="最良のピーク: " + "、".join("%g µm → %.0f nm" % (t, b) for t, b in best.items()) + "。薄いダイは吸収端の手前の 1.0 µm 台でも透け、センサが感じる短い側が勝つ。厚いウェハは吸収端の肩まで押し出される。")
    def _tile(v, label):
        g = np.kron(np.clip(v, 0.0, 1.0), np.ones((2, 2)))           # 2 倍に最近傍で拡大(画素をそのまま見せる)
        rgb = np.ones((g.shape[0] + 30, g.shape[1], 3))
        rgb[30:] = g[..., None]
        return np.asarray(fs.text_box(rgb, label, (6, 4), anchor="lt", font_size=12))
    tiles = [_tile(nz / (1.2 * eo), "%s  CNR %.1f" % (k, cnr[k])) for k, (eo, cl, nz) in shots.items()]
    figs.save("three_leds_through_wafer", np.concatenate(tiles, axis=1),
              caption="775 µm の Si ウェハの裏の配線を、同じ光子数(開口 1 画素に %.1e)の 3 つの LED で撮った。表示は各像の開口の平均で正規化 —— 明るさでなく雑音の粒で差が見える。1200 nm は配線が雑音に沈む。" % NUMBERS["photons_per_px"])
    figs.save("focus_through_wafer", np.concatenate([_tile(blurred, "機械的に %.0f µm 下げた焦点" % 775.0),
                                                      _tile(sharp, "t(1 − 1/n) を補正")], axis=1),
              caption="左: ウェハの厚さだけ機械的に下げた焦点(像は %.0f µm ずれ、W20 = %.1f 波長、回折の PSF で計算)。右: t(1 − 1/n) を補正した焦点。NA 0.1、画素 5 µm。" % (shift_um, w20))
    frames = []
    for i, t in enumerate(np.geomspace(30.0, 1500.0, 16 if not REDUCED else 4)):
        s = np.array([_electrons(p, float(t)) for p in PEAKS_NM])
        b = float(PEAKS_NM[int(np.argmax(s))])
        frames.append(np.asarray(figs.render_plot([("厚さ %.0f µm" % t, PEAKS_NM, s / s.max())], xlabel="LED のピーク [nm]",
                                                  ylabel="電子数(最大で規格化)", title="ウェハ %.0f µm: 最良 %.0f nm" % (t, b),
                                                  colors=["emphasis"], ylim=(0.0, 1.05), xlim=(850.0, 1200.0))))
    figs.save_gif("best_led_sweep", frames, fps=3.0, caption="ウェハを 30 µm から 1.5 mm まで厚くすると、最良の LED が長波長へ滑っていく。")
    if scene is not None:
        noisy3d, cnr3d, open3d = scene
        ref = max(float(c[open3d].mean()) for c, _n in noisy3d.values())
        tiles3d = [_tile(np.kron(nz, np.ones((1, 1))) / (1.2 * max(float(cl[open3d].mean()), 1e-30)) if not k.startswith("850")
                         else nz / (1.2 * ref), "%s  CNR %.1f" % (k, cnr3d[k])) for k, (cl, nz) in noisy3d.items()]
        figs.save("scene_through_wafer", np.concatenate(tiles3d, axis=1),
                  caption="同じ 775 µm のウェハと裏の配線を 3-D のシーンに置き、光線で撮った(optscene の波長積分、テレセンのレンズ、"
                          "Si センサ、第 4 章と同じ光子数)。850 nm は表示を最良の LED の開口で正規化 —— ウェハが不透明で読出し雑音だけが写る。"
                          "他の 3 枚は各像の開口の平均で正規化。配線の影は幾何の真値の画素とずれない。")


def main():
    t0 = time.time()
    print("PoC Si ウェハ越しの近赤外透過検査(予算 %s)" % ("reduced" if REDUCED else "full"))
    A = chapter_sources()
    qs = chapter_sensor()
    contra = chapter_contradiction()
    img = chapter_image(contra[1])
    focus = chapter_focus(img[0], contra[1])
    scene = chapter_scene(contra[1], NUMBERS["photons_per_px"])
    if not REDUCED and figs.target_dir() is not None:
        make_figures(A, qs, contra, img, focus, scene)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
