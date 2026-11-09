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
     透ける 1200 nm は Si センサでは最良の 1/28 —— ただしこの 28 は LED の分光の形の仮定(Ohno 形・半値全幅
     50 nm)で桁が動く: 1200 nm の LED の電子は分光の短波長の裾から来るので、半値全幅 30〜100 nm で 1/75〜1/7、
     Gauss 形 50 nm で 1/58(この章で印字)。集める深さを 3 → 50 µm にすると電子は 16 倍だが、最良の
     ピークは動かない(最適はウェハが決める)。
  4. **像**: 775 µm ウェハの裏の配線パターンを、最良の LED と 1050 / 1200 nm で撮る(光子のショット雑音 +
     読出し雑音)。最良の LED で CNR 20 にするには開口 1 画素に約 1.2e6 光子が要る(Si センサの歩留まりは
     光子 1 万個で電子 3〜4 個)。門: 雑音前の電子数 = 波長積分(1e-12)、分散 = 平均 + 読出し²、
     像から測った CNR = 閉形式 e/√(e + 読出し²)(10 % 以内。この章の像は PSF を掛けないので閉形式がそのまま効く)。
  5. **焦点**: ウェハの厚さ分だけ機械的に下げると、像は t(1 − 1/n) = 556 µm ずれて回折限界の像が崩れる
     (`pupil_blur`、波面の defocus に換算)。補正した焦点で縁幅が戻る。
  6. **3-D のシーンで撮る**(2026-10-15、`optscene` の波長積分): 第 4 章は配線の絵を手で描いて電子数を掛けた。
     ここでは同じウェハ(材料表の Si、k から吸収)・裏の配線・バックライト・テレセンのレンズ・Si センサを 3-D に置き、
     `layout_capture(mode="spectral")` で LED のスペクトルを数本の波長に割って光線で撮る。門: 開口の画素の
     電子/光子が、この章で独立に書いた波長積分 ∫LED·λ·(1 − R)²e^{−αt}·QE / ∫LED と 4 % 以内(光線追跡と
     曲線の積は別の実装)、850 nm ではウェハが不透明(1e-10 未満)、配線の影は幾何の真値の画素と 1 画素も違わない、
     像から測った CNR = 理論。★レンダラは板の中の多重反射を追わないので、第 3 章の積分(多重反射込み)より
     少し暗い —— その差も数として出す。
  7. **実物のダイの配線で撮る**(2026-11-08): 公開のダイ写真(CC BY 3.0)からアルミ配線の形を取り、それを
     ウェハの裏の配線の真値にして、同じ LED・同じ光子数・回折の PSF で撮る。門: 像の CNR = 雑音の無い像 + Poisson と
     読出しの式(PSF の裾の漏れと開口の波打ちを雑音の無い像から入れた形。Poisson の分散 = 平均の確かめで、閉形式
     e/√(e + 読出し²) とは別の量 —— 閉形式との差 = PSF の裾の分は別の数として印字)、最良の LED で配線の形が
     IoU > 0.85(どの像も σ 1 のぼかしの後で比べる)、1200 nm は「形が取れない」のではなく同じ形に要る光が 4 倍以上、
     850 nm はウェハが不透明で信号が無い、50 µm のダイでは定番の 1050 nm の CNR が式どおり落ちる、機械的な焦点では
     形が崩れる。「電子の比だけ光を足すと最良と同じ像」は門にしない(開口の電子数を最良と同じにした構成上の恒等で、
     違いは PSF の λ だけ —— 注記として印字)。50 µm のダイの LED の差は、最良の LED が IoU 0.9 に届く最小の光で
     2 枚を撮って見せる。★配線の真値は写真の明るさのしきい値で取った形(写真の粒 = 辺 8 µm 未満の穴と島は消す)で、
     それを透過率にして撮り直し同じ形と比べる往復 —— IoU が測るのは撮像系の劣化で、写真の配線を当てた
     ことではない。写真は repo に入れず ``tools/fetch_die_photo.py`` で取得し SHA-256 で固定する。写真があれば実測を
     記録値(``RECORDED_CH7``)と照合し、無い環境(CI)では記録値を表示して第 4 章の線と十字を代役に同じ門を回す。

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
from scipy import ndimage

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
def _electrons(peak_nm, thickness_um, collection_um=COLLECTION_UM, fwhm_nm=LED_FWHM_NM, model="ohno"):
    """LED(ピーク peak_nm、分光の形 model)→ Si ウェハ(厚さ、多重反射込み)→ Si センサ の相対電子数。"""
    lo, hi, n = GRID
    led = SR.energy_to_photons(SR.led_spectrum(peak_nm, fwhm_nm, lo, hi, n, model=model))
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
    gate("775 µm: ウェハが最もよく透ける 1200 nm の LED は最良の 1/%.0f(Ohno 形・半値全幅 50 nm の LED、Si センサには見えない)"
         % NUMBERS["gain_vs_1200"], NUMBERS["gain_vs_1200"] > 20.0)
    # 1/28 は LED の分光の形の仮定で桁が動く(1200 nm の LED の電子は分光の短波長の裾から来る)。形と幅を振って印字する
    shapes = {}
    for model, fw in (("ohno", 30.0), ("ohno", 50.0), ("ohno", 80.0), ("ohno", 100.0), ("gaussian", 50.0)):
        e_ = np.array([_electrons(p_, 775.0, fwhm_nm=fw, model=model) for p_ in PEAKS_NM])
        shapes[(model, fw)] = float(e_.max() / _electrons(1200.0, 775.0, fwhm_nm=fw, model=model))
    NUMBERS.update({"gain_vs_1200_%s_%g" % k: v for k, v in shapes.items()})
    print("   775 µm・最良 / 1200 nm の電子の比は LED の形で動く: " + "、".join(
        "%s 形 半値全幅 %g nm → %.1f 倍" % ("Ohno" if m == "ohno" else "Gauss", fw, v) for (m, fw), v in shapes.items()))
    gate("LED の形(Ohno / Gauss)と半値全幅(30〜100 nm)を振っても 1200 nm は最良の 1/5 未満(28 倍の桁は仮定で動くが順位は動かない)",
         min(shapes.values()) > 5.0, "%.1f〜%.1f 倍" % (min(shapes.values()), max(shapes.values())))
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
    integral_table = SR.spectral_integral_table(led)
    tail = 1.0 - integral_table["integrate"](best[775.0] - 1.5 * LED_FWHM_NM,
                                               best[775.0] + 1.5 * LED_FWHM_NM) / integral_table["integrate"]()
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
# 7. 実物のダイの配線をウェハ越しに撮る(2026-11-08)                                #
# --------------------------------------------------------------------------- #
#: 第 4・6 章の配線は手で描いた線と十字だった。ここでは**実物の IC のダイ写真**(公開・CC BY 3.0)から
#: アルミ配線の形を取り、それを「ウェハの裏の配線」の真値として、同じ LED・同じ光子数・回折の PSF で
#: 775 µm の Si 越しに撮る。配線の形は写真の明るさのしきい値で取った近似(アルミは白く、酸化膜は
#: 干渉色で色が付く)で、写真に写らない下の層(拡散層・ポリ)は入っていない。
#: 出典表示: ZeptoBars (Mikhail Svarichevsky), die shot "RCA-CA3033-HD.jpg", CC BY 3.0, https://commons.wikimedia.org/wiki/File:RCA-CA3033-HD.jpg
DIE_PHOTO_URL = "https://upload.wikimedia.org/wikipedia/commons/d/da/RCA-CA3033-HD.jpg"
DIE_PHOTO_FILE = "die_photo.jpg"
DIE_PHOTO_BYTES = 8_096_761
DIE_PHOTO_SHA256 = "00408e9081f94a0100a12b3bc37c03eba5a01c01f431837f599168647d4c0f47"
DIE_PHOTO_CREDIT = ("ダイ写真: ZeptoBars (Mikhail Svarichevsky), Wikimedia Commons, CC BY 3.0 "
                    "(https://creativecommons.org/licenses/by/3.0)。配線の形を明るさのしきい値で取り出す改変あり")
DIE_UM = 1513.0                    # 配布元の説明文のダイの幅 [µm](写真の幅 3792 画素)
DIE_PX = 3792
DIE_CROP = (640, 800, 2304)        # 配線の中央部(ボンディングワイヤを避ける): 上端 y、左端 x、辺 [写真の画素]
OBJ_PITCH_UM = 2.0                 # 物体側の画素 [µm](NA 0.1 の回折限界 λ/2NA ≈ 5 µm を 2.5 画素で)
#: 写真がある手元の実行(2026-11-08 夜、seed 20261108)の数。写真があるときは実測とこの値を全部照合し(門、相対 1e-3)、
#: 無い CI ではこの値から作った文(recorded_ch7_text)を表示したうえで、第 4 章の線と十字を代役にして同じ門を回す。
#: 真値の mask から写真の粒(辺 8 µm 未満の穴と島)を消す前の記録は IoU 0.925 / 1200 nm 0.868 / 焦点 0.153、
#: 50 µm の CNR 61.0 / 38.9(消した後は 0.943 / 0.889 / 0.172、60.6 / 38.9)。
RECORDED_CH7 = {"die_metal_frac": 0.34101, "b775": 1065.0, "b50": 935.0, "die_cnr_best": 18.34515,
                "die_cnr_closed_best": 20.0, "die_iou_best": 0.94304, "die_cnr_1050": 17.93611, "die_iou_1050": 0.94334,
                "die_cnr_1200": 2.20917, "die_iou_1200": 0.88897, "die_need_1200": 2.0, "die_need_best": 0.0625,
                "die_iou_mech": 0.17155, "die_cnr_thin_best": 60.6084, "die_cnr_thin_1050": 38.94886, "die_thin_ratio": 3.40849,
                "die_need_thin_best": 0.00390625, "die_iou_thin_low_best": 0.92858, "die_iou_thin_low_1050": 0.83946}


def _mult_s(m):
    """光子数の倍率の表示(2 の冪の格子): 1 未満は 1/n で。"""
    return ("1/%d" % round(1.0 / m)) if m < 1.0 else ("%g" % m)


def recorded_ch7_text(v):
    """記録値の表示の文(値から作る。CI が表示する文と写真の実行の数が食い違わないように)。"""
    return {
        "配線の占める割合": "%.1f %%(物体側 2 µm の画素 460 x 460、視野 920 µm)" % (100 * v["die_metal_frac"]),
        "775 µm・%.0f nm(最良)" % v["b775"]: "CNR %.1f(閉形式 %.1f)、形 IoU %.3f" % (v["die_cnr_best"], v["die_cnr_closed_best"], v["die_iou_best"]),
        "775 µm・1050 nm": "CNR %.1f、形 IoU %.3f" % (v["die_cnr_1050"], v["die_iou_1050"]),
        "775 µm・1200 nm": "CNR %.1f、形 IoU %.3f、IoU 0.9 に要る光子 %s 倍(最良の %g 倍、2 倍刻みの格子)"
                         % (v["die_cnr_1200"], v["die_iou_1200"], _mult_s(v["die_need_1200"]), v["die_need_1200"] / v["die_need_best"]),
        "775 µm・850 nm": "ウェハが不透明、形は測れない",
        "%.0f nm・焦点を補正しない" % v["b775"]: "形 IoU %.3f" % v["die_iou_mech"],
        "50 µm・%.0f nm(最良)/ 1050 nm" % v["b50"]: "CNR %.1f / %.1f(同じ光子数。1050 nm の電子は最良の 1/%.1f)"
                                         % (v["die_cnr_thin_best"], v["die_cnr_thin_1050"], v["die_thin_ratio"]),
        "50 µm・光子 %s 倍(最良が IoU 0.9 に届く最小の光)" % _mult_s(v["die_need_thin_best"]):
            "形 IoU 最良 %.3f / 1050 nm %.3f" % (v["die_iou_thin_low_best"], v["die_iou_thin_low_1050"]),
    }


def die_photo_dir():
    """ダイ写真の置き場(repo の外)。``FULLSEYE_DIE_PHOTO_DATA`` があればそこ、開発の作業木
    (``<root>/projects/<checkout>``)なら ``<root>/data/fullseye_poc_real/die_photo_bipolar_opamp``、
    それ以外はユーザーのキャッシュ。手元の絶対パスをソースに書かないための分岐。"""
    from pathlib import Path
    configured = os.environ.get("FULLSEYE_DIE_PHOTO_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parents[1]
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real" / "die_photo_bipolar_opamp"
    return Path.home() / ".cache" / "fullseye" / "die_photo_bipolar_opamp"


def load_die_photo():
    """取得済みのダイ写真を SHA-256 を照合して読む。無ければ None(ネットへは出ない)、
    中身が違えば例外(fail-closed: 別の画像で数を出さない)。"""
    import hashlib
    from PIL import Image
    path = die_photo_dir() / DIE_PHOTO_FILE
    if not path.is_file():
        return None
    blob = path.read_bytes()
    got = hashlib.sha256(blob).hexdigest()
    if len(blob) != DIE_PHOTO_BYTES or got != DIE_PHOTO_SHA256:
        raise RuntimeError("ダイ写真の中身が固定した値と違う: %s(%d byte、sha256 %s)" % (path, len(blob), got))
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0


def die_wiring(photo):
    """写真の配線の中央部から、物体側 2 µm の画素の (透過率, 配線の真値の mask, 表示用の写真) を作る。

    アルミ = 明るく(最大値 > 0.55)色の薄い(彩度 < 0.30)画素。アルミの上の黒い点(表面の汚れ・
    ヒロック)は透過では関係ないので、ぼかしと閉じで埋め、残った辺 8 µm 未満の穴と島(写真の粒)も消す。2 µm の画素へは面積平均(画素の中の
    アルミの割合 = 遮る割合)で落とす。
    """
    from PIL import Image
    y0, x0, s = DIE_CROP
    c = photo[y0:y0 + s, x0:x0 + s]
    mx, mn = c.max(axis=-1), c.min(axis=-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    metal = (mx > 0.55) & (sat < 0.30)
    metal = ndimage.gaussian_filter(metal.astype(float), 4.0) > 0.4
    metal = ndimage.binary_closing(metal, iterations=4)
    metal = ndimage.binary_opening(metal, iterations=3)
    um_per_px = DIE_UM / DIE_PX
    # 写真の粒(アルミの上の色の付いた点・酸化膜の上の明るい点)を真値に残さない: 辺 8 µm 未満の穴と島を消す
    min_px = int(round((8.0 / um_per_px) ** 2))
    for want in (False, True):                       # False = アルミの中の穴を埋める、True = 小さなアルミの島を消す
        lab, nl = ndimage.label(metal == want)
        if nl:
            sizes = np.bincount(lab.ravel())
            small = (sizes < min_px)
            small[0] = False
            metal = np.where(small[lab], not want, metal)
    n = int(round(s * um_per_px / OBJ_PITCH_UM))
    frac = np.asarray(Image.fromarray(metal.astype(np.float32)).resize((n, n), Image.Resampling.BOX), dtype=np.float64)
    shown = np.asarray(Image.fromarray(np.rint(c * 255).astype(np.uint8)).resize((n, n), Image.Resampling.LANCZOS))
    return 1.0 - np.clip(frac, 0.0, 1.0), frac > 0.5, shown, um_per_px


def stand_in_wiring(n=460):
    """写真が無いときの代役: 第 4 章の線と十字(1 画素 = 4 画素に拡大)。数は写真の実行と違う。"""
    pat = np.kron(_pattern(n // 4), np.ones((4, 4)))
    metal = pat < 0.5
    shown = np.repeat(np.rint(255 * pat).astype(np.uint8)[..., None], 3, axis=2)
    return pat.astype(np.float64), metal, shown, OBJ_PITCH_UM


#: 形の一致(IoU)を数える前に、どの像にも同じ後処理をかける: ガウス σ 1 画素(PSF の芯 ≈ 2.5 画素より狭い)。
#: 2026-11-08 のレビューで、画素ごとのしきい値だと 1200 nm が雑音で負けるだけで、σ 1 のぼかしで 0.60 → 0.87
#: に戻ることが分かった。「波長で形が取れなくなる」ではなく「同じ像質に要る光の量が違う」が正しい主張なので、
#: 比較は (1) 同じ後処理の IoU と (2) 同じ CNR に要る光子数の比 で行う。
IOU_SIGMA = 1.0
IOU_TARGET = 0.9
EXPOSURES = tuple(2.0 ** k for k in range(-8, 8))     # 光子数の倍率 1/256 〜 128


def chapter_die(best, w20_mech):
    print("\n7. 実物のダイの配線を Si 越しに撮る(公開のダイ写真から取った配線、回折の PSF、ショット雑音)")
    photo = load_die_photo()
    real = photo is not None
    if real:
        trans, metal, shown, um_px = die_wiring(photo)
        print("   写真 %.3f µm/画素 → 物体側 %.1f µm の画素 %d x %d(視野 %.0f µm)、配線の占める割合 %.1f %%"
              % (um_px, OBJ_PITCH_UM, *trans.shape, trans.shape[0] * OBJ_PITCH_UM, 100 * metal.mean()))
    else:
        print("   ダイ写真が無い(tools/fetch_die_photo.py で取得)。写真の手元の実行の数:")
        for k, v in recorded_ch7_text(RECORDED_CH7).items():
            print("     %s = %s" % (k, v))
        print("   ↓ 代役(第 4 章の線と十字)で同じ門を回す。数は写真の実行と違う")
        trans, metal, shown, um_px = stand_in_wiring()
    fno = 5.0
    pupil = (np.hypot(*np.mgrid[-1:1:64j, -1:1:64j]) <= 1.0).astype(float)
    read_e = 5.0
    ppp = NUMBERS["photons_per_px"]
    open_ = ndimage.binary_erosion(~metal, iterations=5)
    dark = ndimage.binary_erosion(metal, iterations=5)
    rng = np.random.default_rng(20261108)
    clean_cache = {}

    def clean(peak, w20):
        key = (peak, w20)
        if key not in clean_cache:
            clean_cache[key] = np.clip(np.asarray(fs.pupil_blur(trans, pupil, w20, peak / 1000.0, fno, OBJ_PITCH_UM),
                                                  dtype=np.float64), 0.0, None)
        return clean_cache[key]

    def shoot(peak, thick, w20=0.0, mult=1.0):
        img = clean(peak, w20)
        e_open = ppp * mult * _electrons(peak, thick)
        nz = rng.poisson(img * e_open).astype(np.float64) + rng.normal(0.0, read_e, img.shape)
        return img, e_open, nz

    def iou(nz, e_open):
        est = ndimage.gaussian_filter(nz, IOU_SIGMA) < 0.5 * e_open      # しきい値 = 理論の開口の半分
        return float(np.logical_and(est, metal).sum() / max(np.logical_or(est, metal).sum(), 1))

    def cnr(nz):
        return float((nz[open_].mean() - nz[dark].mean()) / nz[open_].std())

    def cnr_noiseless(img, e):
        # 雑音の無い像 + Poisson・読出しの式: 回折の PSF の裾が配線の内側へ漏れ(暗部の平均 > 0)、開口の中にも
        # 波打ちが残る —— その分を雑音の無い像から測って入れた形。測った CNR と合うのは Poisson の分散 = 平均の
        # 確かめで、閉形式 e/√(e + 読出し²)(PSF なし)とは別の量
        c = (img[open_].mean() - img[dark].mean()) * e
        return float(c / math.sqrt(img[open_].mean() * e + read_e ** 2 + (e * img[open_].std()) ** 2))

    b775 = best[775.0]
    b50 = best[50.0]
    runs = {"850 nm": (850.0, 775.0, 0.0), "%.0f nm(最良)" % b775: (b775, 775.0, 0.0), "1050 nm": (1050.0, 775.0, 0.0),
            "1200 nm": (1200.0, 775.0, 0.0), "%.0f nm・焦点を補正しない" % b775: (b775, 775.0, w20_mech),
            "50 µm・%.0f nm(最良)" % b50: (b50, 50.0, 0.0), "50 µm・1050 nm": (1050.0, 50.0, 0.0)}
    res = {}
    for label, (peak, thick, w20) in runs.items():
        img, e_open, nz = shoot(peak, thick, w20)
        res[label] = {"e_open": e_open, "nz": nz, "cnr": cnr(nz), "cnr_th": cnr_noiseless(img, e_open),
                      "iou": iou(nz, e_open) if e_open > 1.0 else float("nan")}
    # 同じ形(IoU ≥ 0.9)に要る光子数の倍率
    need = {}
    for label in ("%.0f nm(最良)" % b775, "1050 nm", "1200 nm", "50 µm・%.0f nm(最良)" % b50, "50 µm・1050 nm"):
        peak, thick, w20 = runs[label]
        need[label] = next((m_ for m_ in EXPOSURES if iou(shoot(peak, thick, w20, m_)[2], ppp * m_ * _electrons(peak, thick)) >= IOU_TARGET),
                           float("inf"))
    lb, l12 = "%.0f nm(最良)" % b775, "1200 nm"
    for k, v in res.items():
        v["cnr_closed"] = v["e_open"] / math.sqrt(v["e_open"] + read_e ** 2)
        print("   %-24s 開口 %9.2f 電子  CNR 測 %6.2f / 雑音の無い像+Poisson %6.2f / 閉形式 %6.2f  形 IoU(σ1)%s  IoU %.2f に要る光子 %s 倍"
              % (k, v["e_open"], v["cnr"], v["cnr_th"], v["cnr_closed"], "測れない" if not np.isfinite(v["iou"]) else "%.3f" % v["iou"],
                 IOU_TARGET, ("%g" % need[k]) if k in need else "—"))
    y_ratio = _electrons(b775, 775.0) / _electrons(1200.0, 775.0)
    img12, e12, nz12 = shoot(1200.0, 775.0, 0.0, y_ratio)                 # 1200 nm に電子の比だけ光を足す
    res["1200 nm・光子 %.0f 倍" % y_ratio] = {"e_open": e12, "nz": nz12, "cnr": cnr(nz12), "cnr_th": cnr_noiseless(img12, e12),
                                            "iou": iou(nz12, e12)}
    thin_ratio = _electrons(b50, 50.0) / _electrons(1050.0, 50.0)
    lt_ = "50 µm・%.0f nm(最良)" % b50
    m_thin = need[lt_]
    for label, peak in (("50 µm・%.0f nm・光子 %g 倍" % (b50, m_thin), b50), ("50 µm・1050 nm・光子 %g 倍" % m_thin, 1050.0)):
        img_, e_, nz_ = shoot(peak, 50.0, 0.0, m_thin)
        res[label] = {"e_open": e_, "nz": nz_, "cnr": cnr(nz_), "cnr_th": cnr_noiseless(img_, e_), "iou": iou(nz_, e_)}
    low_b, low_1050 = res["50 µm・%.0f nm・光子 %g 倍" % (b50, m_thin)], res["50 µm・1050 nm・光子 %g 倍" % m_thin]
    print("   50 µm・最良の LED が IoU %.1f に届く最小の光(光子 %s 倍)で撮ると: %.0f nm IoU %.3f(CNR %.1f)/ 1050 nm IoU %.3f(CNR %.1f)"
          % (IOU_TARGET, _mult_s(m_thin), b50, low_b["iou"], low_b["cnr"], low_1050["iou"], low_1050["cnr"]))
    NUMBERS.update({"die_metal_frac": float(metal.mean()), "die_iou_best": res[lb]["iou"], "die_iou_1200": res[l12]["iou"],
                    "die_iou_mech": res["%.0f nm・焦点を補正しない" % b775]["iou"], "die_need_1200": need[l12], "die_need_best": need[lb],
                    "die_cnr_best": res[lb]["cnr"], "die_cnr_1200": res[l12]["cnr"], "die_yield_ratio_1200": y_ratio,
                    "die_thin_ratio": thin_ratio, "die_cnr_1050": res["1050 nm"]["cnr"], "die_iou_1050": res["1050 nm"]["iou"],
                    "die_cnr_closed_best": res[lb]["e_open"] / math.sqrt(res[lb]["e_open"] + read_e ** 2),
                    "die_cnr_thin_best": res[lt_]["cnr"], "die_cnr_thin_1050": res["50 µm・1050 nm"]["cnr"],
                    "die_need_thin_best": m_thin, "die_iou_thin_low_best": low_b["iou"],
                    "die_iou_thin_low_1050": low_1050["iou"], "b775": b775, "b50": b50})
    checked = [k for k in res if res[k]["e_open"] > 1.0]
    worst = max(abs(res[k]["cnr"] / res[k]["cnr_th"] - 1) for k in checked)
    gate("像の CNR = 雑音の無い像 + Poisson・読出しの式(PSF の裾と開口の波打ちを雑音の無い像から入れた形)、850 nm 以外の全条件で 10 % 以内",
         worst < 0.10, "最大のずれ %.1f %%" % (100 * worst))
    psf_loss = {k: 1.0 - res[k]["cnr_th"] * math.sqrt(res[k]["e_open"] + read_e ** 2) / res[k]["e_open"]
                for k in checked if "焦点を補正しない" not in k}
    print("   閉形式 e/√(e + 読出し²)(PSF なし)との差 = 回折の PSF の裾の分(焦点を合わせた条件): 雑音の無い像の CNR は閉形式より %.0f〜%.0f %% 低い"
          % (100 * min(psf_loss.values()), 100 * max(psf_loss.values())))
    gate("850 nm ではウェハが不透明: 開口の信号が読出し雑音の 1/100 未満(像に配線の情報が無い、IoU は定義しない)",
         res["850 nm"]["e_open"] < 0.01 * read_e, "開口 %.1e 電子" % res["850 nm"]["e_open"])
    gate("最良の LED の像(σ 1 のぼかしの後)から配線の形が取れる(IoU > 0.85)", res[lb]["iou"] > 0.85, "IoU %.3f" % res[lb]["iou"])
    r12 = res["1200 nm・光子 %.0f 倍" % y_ratio]
    # 門にしない(構成上の恒等): 電子の比だけ光子を足すと開口の電子数が最良と同じになり、違いは PSF の λ だけ
    print("   注: 1200 nm に電子の比(%.0f 倍)だけ光子を足すと開口の電子数は最良と同じ(構成上の恒等、違いは PSF の λ だけ):"
          " CNR %.1f vs %.1f、IoU %.3f vs %.3f" % (y_ratio, r12["cnr"], res[lb]["cnr"], r12["iou"], res[lb]["iou"]))
    gate("同じ形(IoU ≥ %.1f)に要る光子は 1200 nm が最良の LED の 4 倍以上(%g 倍 vs %g 倍)" % (IOU_TARGET, need[l12], need[lb]),
         need[l12] >= 4.0 * need[lb])
    lt = "50 µm・%.0f nm(最良)" % b50
    gate("50 µm のダイでは定番の 1050 nm が最良(%.0f nm)の 1/%.1f しか電子が出ず、同じ光子数で CNR が式(雑音の無い像 + Poisson)どおり下がる(10 %% 以内)"
         % (b50, thin_ratio),
         thin_ratio > 2.0 and abs((res[lt]["cnr"] / res["50 µm・1050 nm"]["cnr"])
                                  / (res[lt]["cnr_th"] / res["50 µm・1050 nm"]["cnr_th"]) - 1) < 0.10,
         "CNR %.1f vs %.1f(式 %.1f vs %.1f)" % (res[lt]["cnr"], res["50 µm・1050 nm"]["cnr"], res[lt]["cnr_th"],
                                                  res["50 µm・1050 nm"]["cnr_th"]))
    gate("焦点をウェハの厚さだけ機械的に下げると(W20 = %.1f 波長)形が崩れる(IoU が補正後より 0.1 以上低い)" % w20_mech,
         res["%.0f nm・焦点を補正しない" % b775]["iou"] < res[lb]["iou"] - 0.1,
         "%.3f vs %.3f" % (res["%.0f nm・焦点を補正しない" % b775]["iou"], res[lb]["iou"]))
    if real and RECORDED_CH7:
        now = {k: NUMBERS[k] for k in RECORDED_CH7}
        bad = {k: (now[k], RECORDED_CH7[k]) for k in now if abs(now[k] - RECORDED_CH7[k]) > 1e-3 * max(1.0, abs(RECORDED_CH7[k]))}
        print("   記録値の文(CI はこの文を表示する): " + " / ".join("%s = %s" % kv for kv in recorded_ch7_text(now).items()))
        gate("写真の実行の数 = 記録した数(CI が表示する値が今の実装の値であること、1e-3)", not bad, str(bad) if bad else "")
    return {"res": res, "need": need, "metal": metal, "shown": shown, "real": real, "lb": lb, "b775": b775, "b50": b50,
            "y_ratio": y_ratio, "thin_ratio": thin_ratio, "m_thin": m_thin}


def fig_die(die, best):
    """代表の図: 表から撮ったダイの写真・配線の真値と、Si 越しに裏から撮った近赤外の像(各 360 画素を等倍で切り出し)。"""
    from PIL import Image, ImageDraw
    import annotate as AN
    res, b775, b50 = die["res"], die["b775"], die["b50"]
    c = 360
    n = die["shown"].shape[0]
    o = (n - c) // 2
    cut = lambda a: np.ascontiguousarray(a[o:o + c, o:o + c])

    def gray(nz, e_open):
        q = np.clip(nz / (1.15 * e_open), 0.0, 1.0)
        return np.repeat(np.rint(q * 255).astype(np.uint8)[..., None], 3, axis=2)
    ref = res[die["lb"]]["e_open"]
    mask_img = np.repeat(np.where(die["metal"], 235, 30).astype(np.uint8)[..., None], 3, axis=2)

    def note(k):
        r = res[k]
        iou_s = "測れない" if not np.isfinite(r["iou"]) else "%.2f" % r["iou"]
        return "CNR %.1f / 形 IoU %s" % (r["cnr"], iou_s)
    y12 = "1200 nm・光子 %.0f 倍" % die["y_ratio"]
    k50b = "50 µm・%.0f nm・光子 %g 倍" % (b50, die["m_thin"])
    k50n = "50 µm・1050 nm・光子 %g 倍" % die["m_thin"]
    panels = [("表から撮った写真(可視光)", cut(die["shown"]), "出典は下"),
              ("配線の真値(写真から)", cut(mask_img), "白 = アルミ"),
              ("775 µm・850 nm", cut(gray(res["850 nm"]["nz"], ref)), "ウェハが不透明"),
              ("775 µm・%.0f nm(最良)" % b775, cut(gray(res[die["lb"]]["nz"], res[die["lb"]]["e_open"])), note(die["lb"])),
              ("775 µm・1050 nm", cut(gray(res["1050 nm"]["nz"], res["1050 nm"]["e_open"])), note("1050 nm")),
              ("775 µm・1200 nm", cut(gray(res["1200 nm"]["nz"], res["1200 nm"]["e_open"])), note("1200 nm")),
              (y12, cut(gray(res[y12]["nz"], res[y12]["e_open"])), note(y12)),
              ("775 µm・焦点を補正しない", cut(gray(res["%.0f nm・焦点を補正しない" % b775]["nz"], ref)),
               note("%.0f nm・焦点を補正しない" % b775)),
              ("50 µm・%.0f nm(最良)・光 %s 倍" % (b50, _mult_s(die["m_thin"])), cut(gray(res[k50b]["nz"], res[k50b]["e_open"])), note(k50b)),
              ("50 µm・1050 nm・光 %s 倍" % _mult_s(die["m_thin"]), cut(gray(res[k50n]["nz"], res[k50n]["e_open"])), note(k50n))]
    cols, gap, cap_h, head, foot = 5, 8, 54, 56, 124
    W_ = cols * c + (cols + 1) * gap
    H_ = head + 2 * (c + cap_h) + gap + foot
    im = Image.new("RGB", (W_, H_), (24, 26, 30))
    d = ImageDraw.Draw(im)

    def text(s, xy, size=22, fill=(240, 240, 240)):
        m_ = AN.measure_text(s, font_size=size, min_font_size=size, wrap=False)
        if xy[0] + m_["width"] > W_ - 2 or xy[1] + m_["height"] > H_:
            raise ValueError("図の文字がはみ出す: %r" % s)
        for i, line in enumerate(m_["lines"]):
            d.text((xy[0], xy[1] + i * m_["line_height"]), line, font=m_["font"], fill=fill)
    text("Si 越しに裏の配線を見る LED の波長: 775 µm のウェハは %.0f nm(1050 nm とほぼ同じ)、50 µm のダイは %.0f nm"
         % (b775, b50), (gap, 14), size=24)
    for i, (title, img, sub) in enumerate(panels):
        r_, c_ = divmod(i, cols)
        x = gap + c_ * (c + gap)
        y = head + r_ * (c + cap_h + gap)
        text(title, (x + 3, y + 2), size=18, fill=(255, 210, 120) if "最良" in title else (235, 235, 235))
        text(sub, (x + 3, y + 27), size=16, fill=(160, 210, 255))
        im.paste(Image.fromarray(img), (x, y + cap_h))
    fy = H_ - foot + 6
    text("同じ光子数(第 4 章、開口 1 画素に %.1e)、NA 0.1、Si センサ、読出し雑音 5 電子。形 IoU は σ 1 画素のぼかしの後に理論の開口の半分で"
         % NUMBERS["photons_per_px"], (gap, fy), size=16, fill=(210, 210, 210))
    text("しきい値処理して真値と比べた。1200 nm は光を %.0f 倍(Ohno 形・半値全幅 50 nm の LED の電子の比)足すと開口の電子が最良と同じ(下段 2 枚目)。"
         % die["y_ratio"], (gap, fy + 24), size=16, fill=(210, 210, 210))
    text("下段右 2 枚 = 50 µm のダイを、最良の LED が IoU 0.9 に届く最小の光(第 4 章の %s 倍)で。視野 %.0f µm の中央 %.0f µm を等倍、向きは表の写真に。"
         % (_mult_s(die["m_thin"]), n * OBJ_PITCH_UM, c * OBJ_PITCH_UM), (gap, fy + 48), size=16, fill=(210, 210, 210))
    text(("ダイ写真: ZeptoBars (Mikhail Svarichevsky)、Wikimedia Commons、CC BY 3.0(配線を明るさで取り出す改変)"
          if die["real"] else "代役: 第 4 章の線と十字(ダイ写真が無い実行)"), (gap, fy + 74), size=16, fill=(170, 170, 170))
    figs.save("die_through_wafer", np.asarray(im), source=DIE_PHOTO_CREDIT if die["real"] else "",
              caption="公開のダイ写真から取った実物のアルミ配線を Si の裏に置き、同じ光子数で近赤外の LED を替えて撮った。775 µm の"
                      "ウェハでは %.0f nm(最良)と 1050 nm がほぼ同じで形 IoU %.2f、1200 nm は %.2f —— 波長の差は「同じ像質に要る光の量」"
                      "(電子の比 %.0f 倍は Ohno 形・半値全幅 50 nm の LED の場合)。850 nm はウェハが不透明。50 µm のダイでは "
                      "1050 nm の電子は最良(%.0f nm)の 1/%.1f で、最良が IoU 0.9 に届く最小の光では %.2f 対 %.2f。"
                      "焦点をウェハの厚さだけ機械的に下げると IoU %.2f に崩れる。"
                      % (b775, res[die["lb"]]["iou"], res["1200 nm"]["iou"], die["y_ratio"], b50, die["thin_ratio"],
                         res[k50b]["iou"], res[k50n]["iou"], res["%.0f nm・焦点を補正しない" % b775]["iou"]))


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(A, qs, contra, img, focus, scene=None, die=None):
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
    if die is not None:
        fig_die(die, best)


def main():
    t0 = time.time()
    print("PoC Si ウェハ越しの近赤外透過検査(予算 %s)" % ("reduced" if REDUCED else "full"))
    A = chapter_sources()
    qs = chapter_sensor()
    contra = chapter_contradiction()
    img = chapter_image(contra[1])
    focus = chapter_focus(img[0], contra[1])
    scene = chapter_scene(contra[1], NUMBERS["photons_per_px"])
    die = chapter_die(contra[1], focus[2])
    if not REDUCED and figs.target_dir() is not None:
        make_figures(A, qs, contra, img, focus, scene, die)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
