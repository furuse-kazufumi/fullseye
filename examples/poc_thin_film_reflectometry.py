# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 分光反射率で薄膜の膜厚を測る —— 公開の実測データで採点し、縞・干渉色・FFT とあてはめ・膜厚むらの画像へ。

【問い】Si 上の SiO₂ の膜厚は、反射スペクトルの干渉縞から非接触で測る(分光干渉式の膜厚計)。カメラで見れば
膜厚むらは干渉色(ウェハの色むら)になる。新 op 5 本(`filmoptics`)と材料表(`materials`、膜も基板も同じ表)を、
**まず他人が測った実物のデータで**採点し(主役)、そのあと閉形式と合成の模型で限界を測る:

  ★ **実測で採点**(公開データ、どちらも CC BY 4.0。抜き出した小さな表と縮小写真を ``data/thin_film_real/`` に同梱、
     出典と改変は同じ場所の README.md):
     * Schwarz ら, Adv. Opt. Mater. (2024), doi:10.1002/adom.202402502、データ Zenodo 10.5281/zenodo.13753754:
       Si 上の SiO₂ の顕微分光の実測反射率(440〜950 nm、測定点の被覆率 0〜100 % の 11 本)とカラー顕微鏡写真。
       基準の膜厚 98.5 nm(論文のモデル値 98.8 nm と比 1.003046 から逆算。基準の測り方は本文を読めておらず未確認)。
     * Sánchez-Arriaga ら, Sensors 23, 5326 (2023), doi:10.3390/s23115326、データ 10.15131/shef.data.23285603:
       市販の SiO₂/Si 膜厚標準(公称 476.3 nm・198.7 nm)を安価な分光器 2 種 × 光源 3 種で測った反射率。
     裸の Si の実測と材料表の Si、膜厚(顕微分光・標準試料)、被覆率の読み返し、実物の写真からの画素ごとの膜厚。
  1. **転送行列の検算**: 1 層は Airy の式(この PoC に独立に書いた閉じた式)と、(HL)^N の鏡・λ/4 の AR 膜・
     吸収の無い積層の R + T = 1 は閉形式と、膜厚 0 は裸の Si の Fresnel と一致する。fail-closed。
  2. **縞の本数**: 帯域 λ₁〜λ₂ の縞の本数は閉形式 N = d·Δx、x = 2 n(λ)/λ。
  3. **ウェハの色見本**: 計算した干渉色を、公表の SiO₂ on Si の色表(Pliskin & Conrad 1964 の表の写し、TU Delft
     Kavli Nanolab)の色名と色相で比べる(色名から色相への対応は CSS の名前つき色、弱い門)。
  4. **膜厚の推定**: FFT 法とモデルあてはめ。FFT 法が破綻する薄さの閉形式(窓の主ローブの半幅 2/Δx)を先に印字して
     突合。材料の取り違え・入射角・集光 NA・共形な粗さの偏りを閉形式と比べる。
  5. **画像(模型)**: スピンコートのむらを持つ合成のウェハを RGB カメラと分光カメラで撮り、膜厚マップを真値と比べる。
     RGB では色が周期的に似るので膜厚が一意に決まらない画素が残る。顕微鏡の拡大(繊維の彗星・焼き付いた薄片)も模型。

【スピンコート欠陥の文献表(模型の量の根拠、確度つき)】
  * 彗星の成因と定義: 粒子や繊維が塗布中に落ちてレジストに包まれ、「粒子の中心からウェハの縁まで続く小さな膜厚差」
    (Knápek ら, Jordan J. Phys. 13(2), 93–100 (2020), doi:10.47011/13.2.1 —— 本文の記述だけを引用、図は使わない)。
    大きめの粒子が半径方向の流れを妨げる(Birnie の研究ページ「Coating Defects」、U. Arizona、Wayback で確認)。
  * 符号: 原典どうしで食い違う —— レジスト販売元の応用ノート「Spin Coating of Photoresists」は thinning(図は頭の縁に bead、下流に
    thinned area)、MIT FAB.nano の手引きは too thick。模型はその応用ノートの図に従った。大きさは原典に数値が無く、
    Knápek の図 3 の縞の次数から 10〜25 % と推定(推定)。
  * 尾の形: 流れは半径方向でなめらか(Birnie)、Coriolis による曲がりは実用上無視できる(Shepherd, Boujo & Sellier,
    J. Fluid Mech. 998, A32 (2024))→ 尾は半径方向にまっすぐ。下流へ扇形に開く(Birnie の写真、推定)。
  * 焼き付いた薄片: 乾いたレジストの薄片がベークで固着し、周りに円形の暈が 1 周(Knápek の図 3 右、Δd は推定)。
  * 放射状の筋: 間隔 50〜200 µm(Birnie)、振幅は実測が見つからず模型(Birnie & Haas, ISCST 2006 の模型 A/Hf ≈ 0.1〜0.15)。
  * 縁の盛り上がり: 高さは膜厚と同程度まで(DTU Nanolab の手引き)、幅 1〜3 mm(US7335319B2)。
  * ウェハ全体の干渉の輪: 芯ずれ・水平の狂い・回転条件の不良で出て、顕微鏡では見えず肉眼で見える(Knápek 2020)。
    大きさは原典に無く模型。

【外部真値】公開の実測データ 2 件(上)、Airy の式(別実装)、多層膜の閉形式(Macleod)、公表の色表(色名)、
材料表(Malitson 1965 の溶融石英・Green 2008 の Si・Luke 2015 の Si₃N₄、refractiveindex.info、CC0)。【学習】0。【較正】0
(実物の写真だけは、裸の Si の領域で色を材料表の Si に合わせる 1 回の白合わせをする —— カメラの分光感度が不明なため)。
★合成の章のモデルあてはめは、データの作り方とあてはめのモデルが同じなので白色雑音だけなら 0.1 nm 未満に出る
(逆犯罪の良さ)。実測の章では直入射のモデルで −5.7 %、標準試料の 198.7 nm で +5〜8 % —— こちらが実機の姿。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import filmoptics as FO  # noqa: E402
import materials as MT  # noqa: E402
import matappear as MA  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

LO, HI, K = 400.0, 800.0, 401          # 分光膜厚計の帯域(可視)と標本数
NOISE = 0.003                          # 反射率の白色雑音(絶対値)

#: 公表の色表(Pliskin & Conrad, IBM J. Res. Dev. 8(1), 43 (1964) の表の写し。TU Delft Kavli Nanolab の
#: 「Silicon Oxide Colours」の SiO₂ 列 [µm] と色名をそのまま。写しによって 0.465 の名が violet-red / red-violet と
#: 割れ、1.46 / 1.54 の行は別の写しで 1.45 / 1.51 になっている —— 一次の原本の表は確認していない)。
CHART = (
    (0.050, "tan"), (0.075, "brown"), (0.100, "dark violet to red-violet"), (0.125, "royal blue"),
    (0.150, "light blue to metallic blue"), (0.175, "metallic to very light yellow-green"),
    (0.200, "light gold to yellow slightly metallic"), (0.225, "gold with slight yellow-orange"),
    (0.250, "orange to melon"), (0.275, "red-violet"), (0.300, "blue to violet-blue"), (0.310, "blue"),
    (0.325, "blue to blue-green"), (0.345, "light green"), (0.350, "green to yellow-green"), (0.365, "yellow-green"),
    (0.375, "green-yellow"), (0.390, "yellow"), (0.412, "light orange"), (0.426, "carnation pink"),
    (0.443, "violet-red"), (0.465, "violet-red"), (0.476, "violet"), (0.480, "blue-violet"), (0.493, "blue"),
    (0.502, "blue-green"), (0.520, "green"), (0.540, "yellow-green"), (0.560, "green-yellow"),
    (0.574, "yellow to yellowish"), (0.585, "light orange to pink borderline"), (0.600, "carnation pink"),
    (0.630, "violet-red"), (0.680, "bluish"), (0.720, "blue-green to green"), (0.770, "yellowish"), (0.800, "orange"),
    (0.820, "salmon"), (0.850, "dull light red-violet"), (0.860, "violet"), (0.870, "blue-violet"), (0.890, "blue"),
    (0.920, "blue-green"), (0.950, "dull yellow-green"), (0.970, "yellow to yellowish"), (0.990, "orange"),
    (1.000, "carnation pink"), (1.020, "violet-red"), (1.050, "red-violet"), (1.060, "violet"), (1.070, "blue-violet"),
    (1.100, "green"), (1.110, "yellow-green"), (1.120, "green"), (1.180, "violet"), (1.190, "red-violet"),
    (1.210, "violet-red"), (1.240, "carnation pink to salmon"), (1.250, "orange"), (1.280, "yellowish"),
    (1.320, "sky-blue to green-blue"), (1.400, "orange"), (1.450, "violet"), (1.460, "blue-violet"), (1.500, "blue"),
    (1.540, "dull yellow-green"),
)

#: 色名 → CSS の名前つき色(W3C CSS Color Module Level 4 の sRGB 値)。複合語は長い順に照合する。
#: ★色名から色相への対応は私の選択(CSS の色は表の色より彩度が高い)—— 色相だけを比べる。
CSS = {"tan": (210, 180, 140), "brown": (165, 42, 42), "darkviolet": (148, 0, 211), "mediumvioletred": (199, 21, 133),
       "royalblue": (65, 105, 225), "blue": (0, 0, 255), "lightblue": (173, 216, 230), "steelblue": (70, 130, 180),
       "yellowgreen": (154, 205, 50), "greenyellow": (173, 255, 47), "gold": (255, 215, 0), "yellow": (255, 255, 0),
       "orange": (255, 165, 0), "salmon": (250, 128, 114), "blueviolet": (138, 43, 226), "violet": (238, 130, 238),
       "teal": (0, 128, 128), "lightgreen": (144, 238, 144), "green": (0, 128, 0), "pink": (255, 192, 203),
       "hotpink": (255, 105, 180), "skyblue": (135, 206, 235)}
TERMS = (("very light yellow-green", ("yellowgreen",)), ("red-violet", ("mediumvioletred",)),
         ("violet-red", ("mediumvioletred",)), ("violet-blue", ("blueviolet",)), ("blue-violet", ("blueviolet",)),
         ("blue-green", ("teal",)), ("green-blue", ("teal",)), ("yellow-green", ("yellowgreen",)),
         ("green-yellow", ("greenyellow",)), ("yellow-orange", ("gold", "orange")), ("carnation pink", ("pink", "hotpink")),
         ("royal blue", ("royalblue",)), ("light blue", ("lightblue",)), ("metallic blue", ("steelblue",)),
         ("sky-blue", ("skyblue",)), ("dark violet", ("darkviolet",)), ("light green", ("lightgreen",)),
         ("light gold", ("gold",)), ("light orange", ("orange",)), ("tan", ("tan",)), ("brown", ("brown",)),
         ("gold", ("gold",)), ("yellowish", ("yellow",)), ("yellow", ("yellow",)), ("orange", ("orange",)),
         ("melon", ("salmon",)), ("salmon", ("salmon",)), ("bluish", ("blue",)), ("blue", ("blue",)),
         ("violet", ("violet", "darkviolet")), ("green", ("green",)), ("pink", ("pink", "hotpink")))

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def n_of(material, lam):
    return MT._nk(MT._record(material, "poc"), np.asarray(lam, float) / 1000.0, "poc")[0]


def airy(lam, d, n1, n2, cos0, pol):
    """1 層の Airy の式(N = n + ik、位相 e^{2iβ}、減衰の枝 Im(N cosθ) ≥ 0)。filmoptics と別に書いた検算用。

    以前は matappear.thin_film_reflectance を別実装として使っていたが、2026-10-15 に両 op の計算を filmoptics の
    特性行列 1 か所に寄せたので、ここに式を持つ(同じコードを両辺に入れた門は何も確かめない)。
    """
    s0 = math.sqrt(1.0 - cos0 * cos0)

    def cs(n):
        c = np.sqrt(1.0 - (s0 / n) ** 2 + 0j)
        return np.where((n * c).imag < 0, -c, c)

    c1, c2 = cs(n1), cs(n2)
    if pol == "s":
        r1, r2 = (cos0 - n1 * c1) / (cos0 + n1 * c1), (n1 * c1 - n2 * c2) / (n1 * c1 + n2 * c2)
    else:
        r1, r2 = (n1 * cos0 - c1) / (n1 * cos0 + c1), (n2 * c1 - n1 * c2) / (n2 * c1 + n1 * c2)
    ph = np.exp(4j * np.pi * n1 * d * c1 / lam)
    return np.abs((r1 + r2 * ph) / (1 + r1 * r2 * ph)) ** 2


def nk_of(material, lam):
    n, k = MT._nk(MT._record(material, "poc"), np.asarray(lam, float) / 1000.0, "poc")[:2]
    return n + 1j * k


def spectrum(d, **kw):
    return FO.multilayer_reflectance([("SIO2", float(d))], "SI", LO, HI, K, **kw)


# --------------------------------------------------------------------------- #
# 1. 転送行列の検算                                                             #
# --------------------------------------------------------------------------- #
def chapter_truth():
    print("\n1. 転送行列の検算(別実装と閉形式)")
    lam = np.linspace(LO, HI, 201)
    worst = 0.0
    for d in (0.0, 100.0, 500.0, 1500.0):
        for cos_t, pol in ((1.0, "unpolarized"), (0.7, "s"), (0.5, "p")):
            a = FO.multilayer_reflectance([("SIO2", d)], "SI", wavelengths_nm=lam,
                                          angle_deg=math.degrees(math.acos(cos_t)), polarization=pol)[:, 1]
            pols = ("s", "p") if pol == "unpolarized" else (pol,)
            b = sum(airy(lam, d, nk_of("SIO2", lam), nk_of("SI", lam), cos_t, p) for p in pols) / len(pols)
            worst = max(worst, float(np.max(np.abs(a - b))))
        a = FO.multilayer_reflectance([("SIO2", d)], "TI", wavelengths_nm=lam, angle_deg=40.0)[:, 1]
        c40 = math.cos(math.radians(40.0))
        b = 0.5 * (airy(lam, d, nk_of("SIO2", lam), nk_of("TI", lam), c40, "s")
                   + airy(lam, d, nk_of("SIO2", lam), nk_of("TI", lam), c40, "p"))
        worst = max(worst, float(np.max(np.abs(a - b))))
    NUMBERS["airy_worst"] = worst
    gate("1 層は Airy の式(この PoC に独立に書いた式)と一致: Si・Ti の基板、s/p/無偏光、斜入射", worst < 1e-12,
         "最大差 %.1e" % worst)
    nH, nL, ns, N, lam0 = 2.3, 1.38, 1.52, 5, 550.0
    stack = [(nH, lam0 / 4 / nH), (nL, lam0 / 4 / nL)] * N
    R = float(FO.multilayer_reflectance(stack, ns, wavelengths_nm=[lam0])[0, 1])
    q = ns * (nH / nL) ** (2 * N)
    gate("(HL)^5 の鏡: R = ((1 − q)/(1 + q))²、q = n_s (n_H/n_L)^10(閉形式)", abs(R - ((1 - q) / (1 + q)) ** 2) < 1e-12,
         "R = %.6f" % R)
    ar = float(FO.multilayer_reflectance([(math.sqrt(ns), lam0 / 4 / math.sqrt(ns))], ns, wavelengths_nm=[lam0])[0, 1])
    gate("λ/4 の AR 膜(n = √n_s)は設計波長で R = 0", ar < 1e-15, "%.1e" % ar)
    Rp = FO.multilayer_reflectance(stack, ns, wavelengths_nm=lam, angle_deg=30.0)[:, 1]
    Tp = FO.multilayer_reflectance(stack, ns, wavelengths_nm=lam, angle_deg=30.0, quantity="transmittance")[:, 1]
    gate("吸収の無い積層は R + T = 1(斜入射 30°、201 波長)", float(np.max(np.abs(Rp + Tp - 1))) < 1e-12)
    n0 = n_of("SI", lam) + 1j * MT._nk(MT._record("SI", "poc"), lam / 1000.0, "poc")[1]
    bare = np.abs((1 - n0) / (1 + n0)) ** 2
    r0 = FO.multilayer_reflectance([("SIO2", 0.0)], "SI", wavelengths_nm=lam)[:, 1]
    rr = FO.multilayer_reflectance([("SIO2", 0.0)], "SI", wavelengths_nm=lam, roughness_nm=5.0)[:, 1]
    dw = bare * np.exp(-(4 * np.pi * 5.0 / lam) ** 2)
    gate("膜厚 0 は裸の Si の Fresnel、粗さ 5 nm は Debye–Waller の因子 exp(−(4πσ/λ)²)",
         float(np.max(np.abs(r0 - bare))) < 1e-12 and float(np.max(np.abs(rr - dw))) < 1e-12)
    refused = 0
    for bad in (lambda: FO.multilayer_reflectance([("UNOBTAINIUM", 100.0)], "SI"),
                lambda: FO.multilayer_reflectance([("SIO2", -5.0)], "SI"),
                lambda: FO.multilayer_reflectance([("PMMA", 500.0)], "SI", 400.0, 800.0),
                lambda: FO.multilayer_reflectance([("SIO2", 100.0)], "SI", na=0.3, angle_deg=10.0)):
        try:
            bad()
        except ValueError:
            refused += 1
    gate("fail-closed: 知らない材料・負の膜厚・材料表の範囲外(PMMA は 437 nm から)・NA と斜入射の同時指定を拒否",
         refused == 4, "%d / 4" % refused)


# --------------------------------------------------------------------------- #
# ★ 実測で採点(公開データ、CC BY 4.0)—— この PoC の主役                       #
# --------------------------------------------------------------------------- #
REAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "thin_film_real")
#: Schwarz ら 2024 の基準の膜厚(Figure_S4a のモデル値 98.8 nm と Figure 4 の比 1.003046 から逆算、data/thin_film_real/README.md)。
SCHWARZ_REF_NM = 98.8 / 1.003046
#: Sánchez-Arriaga ら 2023 の市販の膜厚標準(公称値)。
SHEFFIELD_NOMINAL = {1: 476.3, 2: 198.7}


def _csv(name):
    import csv
    with open(os.path.join(REAL, name), encoding="utf-8") as f:
        return list(csv.reader(f))


def chapter_real():
    print("\n★ 実測で採点(公開データ CC BY 4.0: Schwarz ら 2024 の顕微分光と写真、Sánchez-Arriaga ら 2023 の標準試料)")
    rows = _csv("schwarz2024_sio2_si_reflectance.csv")
    cov = [float(h.replace("R_cov", "")) for h in rows[0][1:]]
    a = np.array([[float(v) for v in r] for r in rows[1:]])
    lam = a[:, 0]
    full, bare = np.column_stack([lam, a[:, 1]]), np.column_stack([lam, a[:, -1]])
    out = {"lam": lam, "full": full, "bare": bare, "cov": cov, "a": a}
    # (1) 裸の Si: 材料表の Si(Green 2008)の Fresnel と、実測の反射率の比
    r_si = FO.multilayer_reflectance([], "SI", wavelengths_nm=lam)[:, 1]
    ratio = a[:, -1] / r_si
    NUMBERS["real_bare_ratio_median"] = float(np.median(ratio))
    NUMBERS["real_bare_ratio_spread"] = float(np.percentile(ratio, 95) - np.percentile(ratio, 5))
    gate("実測の裸の Si の反射率は材料表の Si の Fresnel と中央値で %.1f %% 差(440〜950 nm、5〜95 %% の幅 %.3f)"
         % (100 * (NUMBERS["real_bare_ratio_median"] - 1), NUMBERS["real_bare_ratio_spread"]),
         abs(NUMBERS["real_bare_ratio_median"] - 1) < 0.03)
    # (2) SiO₂ 100 %: 直入射のモデル・NA を残差で選んだモデル・FFT
    fit0 = FO.film_thickness_fit(full, "SIO2", "SI", 0.0, 400.0)
    scan = [(na, FO.film_thickness_fit(full, "SIO2", "SI", 0.0, 400.0, na=na)) for na in np.arange(0.0, 0.91, 0.1)]
    na_b, fit_b = min(scan, key=lambda t: t[1]["rmse"])
    fft = FO.film_thickness_fft(full, "SIO2")
    ref = SCHWARZ_REF_NM
    NUMBERS.update({"real_fit0": fit0["thickness_nm"], "real_fit_na": fit_b["thickness_nm"], "real_na": na_b,
                    "real_fft": fft["thickness_nm"], "real_ref": ref})
    out.update({"fit0": fit0, "fit_na": (na_b, fit_b), "scan": scan})
    print("      SiO₂ 100 %%(基準 %.1f nm): 直入射のモデル %.1f nm(%+.1f %%、RMS %.4f)/ 残差が最小の NA %.1f で %.1f nm"
          "(%+.1f %%、RMS %.4f)/ FFT %.1f nm(測れる下限 %.0f nm、reliable=%s)"
          % (ref, fit0["thickness_nm"], 100 * (fit0["thickness_nm"] / ref - 1), fit0["rmse"], na_b, fit_b["thickness_nm"],
             100 * (fit_b["thickness_nm"] / ref - 1), fit_b["rmse"], fft["thickness_nm"], fft["min_thickness_nm"], fft["reliable"]))
    gate("実測の顕微分光の膜厚は基準 %.1f nm と直入射のモデルで %.1f %%(< 7 %%)"
         % (ref, 100 * (fit0["thickness_nm"] / ref - 1)), abs(fit0["thickness_nm"] / ref - 1) < 0.07)
    gate("★直入射のモデルは薄く読む(章 4 の閉形式 d(1 − NA²/4n²) と同じ向き)—— NA を残差で選ぶと基準に近づく"
         "(%.1f → %.1f nm、NA %.1f)。顕微鏡の NA は論文を読めておらず未確認" % (fit0["thickness_nm"], fit_b["thickness_nm"], na_b),
         fit0["thickness_nm"] < ref and abs(fit_b["thickness_nm"] - ref) < abs(fit0["thickness_nm"] - ref))
    gate("FFT は 98 nm の膜で「信頼できない」と自分で言う(下限の閉形式 %.0f nm より薄い)" % fft["min_thickness_nm"],
         not fft["reliable"])
    # (3) 被覆率: 測定点の中の SiO₂ の割合 f を R = f R_膜 + (1 − f) R_Si の最小二乗で(膜厚は 100 % のあてはめ)
    rf = FO.multilayer_reflectance([("SIO2", fit_b["thickness_nm"])], "SI", wavelengths_nm=lam, na=na_b)[:, 1]
    rb = FO.multilayer_reflectance([], "SI", wavelengths_nm=lam, na=na_b)[:, 1]
    est = []
    for k in range(len(cov)):
        y = a[:, 1 + k] - rb
        est.append(float(np.clip(np.sum(y * (rf - rb)) / np.sum((rf - rb) ** 2), 0.0, 1.0)) * 100.0)
    err = np.array(est) - np.array(cov)
    NUMBERS["real_cov_mae"] = float(np.mean(np.abs(err)))
    out["cov_est"] = est
    gate("測定点の SiO₂ の被覆率(論文の値 0〜100 %%、11 点)を線形の混合で %.1f 点の平均誤差で読み返す" % NUMBERS["real_cov_mae"],
         NUMBERS["real_cov_mae"] < 5.0)
    # (4) 標準試料(安価な分光器、反射率は任意単位 → 倍率もあてはめる)
    rs = _csv("sanchez_arriaga2023_sio2_standards.csv")
    groups = {}
    for r in rs[1:]:
        groups.setdefault((r[0], r[1], int(r[2])), []).append((float(r[3]), float(r[4])))
    res = []
    for (fn, sh, smp), pts in sorted(groups.items()):
        sp = np.array(sorted(pts))
        sp = sp[(sp[:, 0] >= 450.0) & (sp[:, 0] <= 800.0)]
        f = FO.film_thickness_fit(sp, "SIO2", "SI", 0.0, 1500.0, fit_scale=True)
        nominal = SHEFFIELD_NOMINAL[smp]
        near = min(f["candidates"], key=lambda c: abs(c[0] - nominal))
        rank = [c[0] for c in f["candidates"]].index(near[0]) + 1
        res.append((fn, sh, smp, nominal, f["thickness_nm"], f["rmse"], rank, near[0]))
        print("      %-26s %-20s 公称 %5.1f nm → %6.1f nm(%+5.1f %%、RMS %.3f)%s"
              % (fn, sh, nominal, f["thickness_nm"], 100 * (f["thickness_nm"] / nominal - 1), f["rmse"],
                 "" if rank == 1 else "  ★最良は外れ、%d 番目の候補 %.1f nm" % (rank, near[0])))
    out["sheffield"] = res
    e1 = [abs(r[4] / r[3] - 1) for r in res if r[2] == 1]
    e2 = [abs(r[4] / r[3] - 1) for r in res if r[2] == 2 and r[6] == 1]
    miss = [r for r in res if r[6] != 1]
    NUMBERS.update({"real_s1_worst": max(e1), "real_s2_median": float(np.median(e2)), "real_s_miss": len(miss)})
    gate("標準 476.3 nm は %d 本すべて 2 %% 以内(最大 %.1f %%、安価な分光器・任意単位)" % (len(e1), 100 * max(e1)), max(e1) < 0.02)
    gate("標準 198.7 nm は %d 本中 %d 本で最良の候補が合い中央値 %.1f %%(★厚めに読む、%d 本は最良が外れ、"
         "正しい膜厚は %d 番目の候補に残る)" % (len([r for r in res if r[2] == 2]), len(e2), 100 * NUMBERS["real_s2_median"],
                                              len(miss), max([r[6] for r in miss], default=1)),
         NUMBERS["real_s2_median"] < 0.10 and all(r[6] <= 3 for r in miss))
    # (5) 実物の顕微鏡写真(カメラは不明)→ 裸の Si の領域で色を合わせて、画素ごとの膜厚
    from PIL import Image
    im = np.asarray(Image.open(os.path.join(REAL, "schwarz2024_micrograph_sio2_edge_640.jpg")).convert("RGB"), float) / 255.0
    lin = np.where(im <= 0.04045, im / 12.92, ((im + 0.055) / 1.055) ** 2.4)
    h, w = lin.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    si = (xx >= 20) & (xx < w // 2 - 40) & (yy >= 20) & (yy < h - 20)          # 裸の Si(左)
    fi = (xx >= w // 2 + 50) & (xx < w - 20) & (yy >= 20) & (yy < h - 20)       # SiO₂(右)
    # ★フラット補正(2026-10-15、図を見たユーザーの指摘「Si 側が 2 段に分かれて見える」から): 写真は視野の中心が明るい
    #   周辺減光を持つ(裸の Si は左端 0.238 → 中央寄り 0.263、SiO₂ は中央寄り 0.103 → 右端 0.095)。補正しないと、Si の
    #   暗い側が「薄い膜」と読まれ(0 nm 付近は R が膜厚の 2 乗でしか下がらないので、数 % の明るさの差が 10〜17 nm に化ける)、
    #   明るい側は 0 nm に張り付いて、2 段に見えた。減光を半径の 2 乗 V = c₀ + c₁ r² として**裸の Si の側だけ**で当てはめ、
    #   視野全体を割る。SiO₂ の側は当てはめに使っていないので、その明るさの傾きが消えるかが独立の検算になる。
    r2 = ((xx - w / 2) ** 2 + (yy - h / 2) ** 2) / (w / 2) ** 2
    lum = lin.mean(2)
    c0, c1 = np.linalg.lstsq(np.column_stack([np.ones(int(si.sum())), r2[si]]), lum[si], rcond=None)[0]
    flat = lin / (1.0 + (c1 / c0) * r2)[..., None]

    def _tilt(img, m_):
        return float(np.polyfit(xx[m_], img.mean(2)[m_], 1)[0] * (w / 2) / img.mean(2)[m_].mean())

    bare_rgb = flat[si].mean(0)
    col0 = FO.film_color("SIO2", "SI", 0.0, 1.0, 2)["linear_srgb"][0]
    balanced = flat / bare_rgb * col0                          # 裸の Si が材料表の Si の色になるよう、チャンネルごとに合わせる
    m = FO.film_thickness_map(np.moveaxis(balanced, -1, 0), None, "SIO2", "SI", 0.0, 400.0, mode="srgb", step_nm=0.5,
                              ambiguity_rms=0.01)
    film_px, bare_px = m["thickness"][fi], m["thickness"][si]
    NUMBERS.update({"real_rgb_film": float(np.median(film_px)), "real_rgb_bare": float(np.median(bare_px)),
                    "real_rgb_bare_p95": float(np.percentile(bare_px, 95)),
                    "real_rgb_film_p5": float(np.percentile(film_px, 5)), "real_rgb_film_p95": float(np.percentile(film_px, 95)),
                    "real_vignette": float(c1 / c0), "real_tilt_before": _tilt(lin, fi), "real_tilt_after": _tilt(flat, fi),
                    "real_rgb_cands": float(np.median(m["n_candidates"][fi]))})
    print("      周辺減光(裸の Si だけで当てはめ)%.1f %%(視野の端)、SiO₂ 側の明るさの傾き %+.1f %% → %+.1f %%(当てはめに未使用 = 独立の検算)"
          % (100 * NUMBERS["real_vignette"], 100 * NUMBERS["real_tilt_before"], 100 * NUMBERS["real_tilt_after"]))
    print("      Si 側の膜厚 中央値 %.1f nm・95 パーセンタイル %.1f nm(0 nm 付近は R が膜厚の 2 乗でしか動かず、雑音が数 nm に化ける)、"
          "SiO₂ 側 5〜95 パーセンタイル %.1f〜%.1f nm" % (NUMBERS["real_rgb_bare"], NUMBERS["real_rgb_bare_p95"],
                                                   NUMBERS["real_rgb_film_p5"], NUMBERS["real_rgb_film_p95"]))
    gate("フラット補正: 裸の Si で当てはめた周辺減光で割ると、SiO₂ 側の明るさの傾きが 1/5 以下に(%+.1f %% → %+.1f %%)"
         % (100 * NUMBERS["real_tilt_before"], 100 * NUMBERS["real_tilt_after"]),
         abs(NUMBERS["real_tilt_after"]) < 0.2 * abs(NUMBERS["real_tilt_before"]))
    out["photo"] = (im, m)
    gate("★実物の写真(カメラ不明・JPEG)から: SiO₂ 側の膜厚の中央値 %.1f nm(基準 %.1f nm と %+.0f %%)、裸の Si 側 %.1f nm、"
         "0〜400 nm で候補 %.0f 個 —— 次数は合うが、分光より %.0f 倍粗い"
         % (NUMBERS["real_rgb_film"], ref, 100 * (NUMBERS["real_rgb_film"] / ref - 1), NUMBERS["real_rgb_bare"],
            NUMBERS["real_rgb_cands"], abs(NUMBERS["real_rgb_film"] - ref) / max(abs(fit_b["thickness_nm"] - ref), 1e-9)),
         abs(NUMBERS["real_rgb_film"] / ref - 1) < 0.25 and NUMBERS["real_rgb_bare"] < 25.0)
    return out


# --------------------------------------------------------------------------- #
# 2. 縞の本数                                                                   #
# --------------------------------------------------------------------------- #
def chapter_fringes():
    print("\n2. 縞の本数(閉形式 N = d·Δx、x = 2 n(λ)/λ)")
    lam = np.linspace(LO, HI, 2001)
    n = n_of("SIO2", lam)
    span = float((2 * n / lam).max() - (2 * n / lam).min())
    NUMBERS["span_x"] = span
    worst = 0
    rows = []
    for d in (200.0, 500.0, 1000.0, 1500.0, 2000.0):
        R = FO.multilayer_reflectance([("SIO2", d)], "SI", wavelengths_nm=lam)[:, 1]
        peaks = int(np.sum((R[1:-1] > R[:-2]) & (R[1:-1] > R[2:])))
        rows.append((d, peaks, d * span))
        worst = max(worst, abs(peaks - d * span))
    for d, p, nf in rows:
        print("      d = %4.0f nm: 極大 %d 本、閉形式 %.2f 本" % (d, p, nf))
    gate("縞の極大の本数は閉形式 d·Δx と ±1 本以内(0.2〜2 µm、Δx = %.5f /nm)" % span, worst <= 1.0, "最大のずれ %.2f" % worst)
    return lam, span


# --------------------------------------------------------------------------- #
# 3. ウェハの色見本                                                             #
# --------------------------------------------------------------------------- #
def _hue_of_srgb8(rgb):
    x = np.asarray(rgb, float) / 255.0
    lin = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    lab = FO._lab(lin @ np.linalg.inv(MA._XYZ_TO_SRGB).T)
    return float(np.degrees(np.arctan2(lab[2], lab[1])) % 360.0)


CSS_HUE = {k: _hue_of_srgb8(v) for k, v in CSS.items()}


def chart_css(name):
    t, out = name, []
    for term, css in TERMS:
        if term in t:
            out += list(css)
            t = t.replace(term, " ")
    return out


def tri_band(lam):
    """三波長形の蛍光灯の模型(Hg 435.8 nm・Tb 545.4 nm・Eu 611.3 nm の輝線 + 弱い連続)。CIE F11 の表ではない。"""
    s = 0.08 * np.ones_like(lam)
    for c, h in ((435.8, 0.6), (545.4, 1.0), (611.3, 0.8), (487.0, 0.15), (587.0, 0.1)):
        s = s + h * np.exp(-0.5 * ((lam - c) / 1.7) ** 2)
    return np.column_stack([lam, s])


def chapter_chart():
    print("\n3. ウェハの色見本(公表の色表と色相で)")
    nd = 3201 if not REDUCED else 1601
    step = 1600.0 / (nd - 1)
    out = {}
    for label, ill in (("D65", None), ("三波長", tri_band(np.arange(370.0, 791.0, 0.5)))):
        c = FO.film_color("SIO2", "SI", 0.0, 1600.0, nd, illuminant=ill)
        res = []
        for t_um, name in CHART:
            i = int(round(t_um * 1000.0 / step))
            h, ch = float(c["hue_deg"][i]), float(c["chroma"][i])
            dh = min(abs((CSS_HUE[k] - h + 180.0) % 360.0 - 180.0) for k in chart_css(name))
            res.append((t_um * 1000.0, name, h, ch, dh))
        out[label] = (c, res)
    for label, (c, res) in out.items():
        t = np.array([r[0] for r in res])
        dh = np.array([r[4] for r in res])
        ch = np.array([r[3] for r in res])
        m1 = t <= 560.0
        NUMBERS["chart_%s_hit_I_III" % label] = float(np.mean(dh[m1] <= 36.0))
        NUMBERS["chart_%s_median_dh_I_III" % label] = float(np.median(dh[m1]))
        NUMBERS["chart_%s_chroma_thick" % label] = float(np.median(ch[t >= 1000.0]))
        print("      %s: 1〜3 次(≤ 560 nm、%d 行)で色相が CSS の色名の ±36° に入る割合 %.0f %%(中央値 %.0f°)、"
              "全 %d 行 %.0f %%、1 µm 以上の彩度の中央値 C* %.1f"
              % (label, int(m1.sum()), 100 * np.mean(dh[m1] <= 36), np.median(dh[m1]), len(dh), 100 * np.mean(dh <= 36),
                 np.median(ch[t >= 1000.0])))
    _, res = out["D65"]
    print("      膜厚 色表の色名 → 計算(D65)の色相 h° / 彩度 C* / 最も近い名との差")
    for r in res[:29:2]:
        print("      %5.0f nm  %-38s h %3.0f°  C* %4.1f  Δh %3.0f°" % r)
    gate("1〜3 次の色(≤ 560 nm)は色表の色名と色相で過半が一致(±36° = Munsell の 1 色相ほど、D65)",
         NUMBERS["chart_D65_hit_I_III"] >= 0.5, "%.0f %%" % (100 * NUMBERS["chart_D65_hit_I_III"]))
    gate("★1 µm より厚い膜は連続光(D65)では灰色に寄り、輝線の照明(三波長の模型)では色が残る(C* が 1.3 倍以上)",
         NUMBERS["chart_三波長_chroma_thick"] > 1.3 * NUMBERS["chart_D65_chroma_thick"],
         "C* %.1f → %.1f" % (NUMBERS["chart_D65_chroma_thick"], NUMBERS["chart_三波長_chroma_thick"]))
    c0 = out["D65"][0]
    # ★予言が外れた: 「裸の Si は無彩色(C* < 3)」と置いたら C* 6.6 だった。Si の反射率は 400 nm 0.49 → 800 nm 0.33 と
    #   短波長ほど高いので、裸のウェハは**青みの灰色**に見える(実物のとおり)。門を所見の側に書き直した。
    h0, c0c = float(c0["hue_deg"][0]), float(c0["chroma"][0])
    gate("裸の Si(膜厚 0)は青みの灰色: 色相 %.0f°(青 240〜300°)、C* %.1f(< 10)。Si の R は 400 nm %.2f → 800 nm %.2f"
         % (h0, c0c, float(spectrum(0.0)[0, 1]), float(spectrum(0.0)[-1, 1])), 240.0 <= h0 <= 300.0 and c0c < 10.0)
    return out


# --------------------------------------------------------------------------- #
# 4. 膜厚の推定                                                                 #
# --------------------------------------------------------------------------- #
def chapter_estimate():
    print("\n4. 膜厚の推定: FFT 法とモデルあてはめ")
    rng = np.random.default_rng(1)
    lam = np.linspace(LO, HI, K)
    n_bar = float(np.mean(n_of("SIO2", lam)))
    span = NUMBERS["span_x"]
    lim_hann, lim_rect = 2.0 / span, 1.0 / span
    print("      ★先に閉形式: Δx = 2 n(λ)/λ の帯域幅 %.5f /nm、FFT の窓の主ローブの半幅 = 測れる下限 hann 2/Δx = %.0f nm、"
          "rect 1/Δx = %.0f nm(縞 2 本・1 本)。λ/(4 n̄) = %.0f nm(550 nm で最初の極値)"
          % (span, lim_hann, lim_rect, 550.0 / (4 * n_bar)))
    ds = np.arange(50.0, 2001.0, 25.0 if not REDUCED else 50.0)
    err_h, err_r, err_f = [], [], []
    for d in ds:
        sp = spectrum(d)
        sp[:, 1] += NOISE * rng.standard_normal(K)
        err_h.append(FO.film_thickness_fft(sp, "SIO2")["thickness_nm"] - d)
        err_r.append(FO.film_thickness_fft(sp, "SIO2", window="rect")["thickness_nm"] - d)
        err_f.append(FO.film_thickness_fit(sp, "SIO2", "SI", 0.0, 3000.0)["thickness_nm"] - d)
    err_h, err_r, err_f = map(np.asarray, (err_h, err_r, err_f))
    rel = np.abs(err_h) / ds
    bad = ds[rel > 0.05]
    onset = float(bad.max()) + (ds[1] - ds[0]) if bad.size else float(ds[0])
    NUMBERS.update({"fft_limit_closed": lim_hann, "fft_limit_measured": onset,
                    "fit_worst_nm": float(np.max(np.abs(err_f))), "fft_worst_above": float(np.max(np.abs(err_h[ds >= onset]))),
                    "fft_worst_thick": float(np.max(np.abs(err_h[ds >= 2 * lim_hann]) / ds[ds >= 2 * lim_hann]))})
    gate("FFT(hann)が 5 %% 以内に収まる薄さの境 %.0f nm は閉形式 2/Δx = %.0f nm と ±25 %% で一致" % (onset, lim_hann),
         abs(onset / lim_hann - 1.0) <= 0.25)
    # ★境の直上でも FFT は最大 %.0f nm 外す(窓の DC の裾とフレネルの位相の分)—— 2 倍の厚さで 1 % 以内に入る。
    gate("下限の 2 倍(%.0f nm)より厚ければ FFT の誤差は %.2f %% 以内(境の直上は最大 %.0f nm)"
         % (2 * lim_hann, 100 * NUMBERS["fft_worst_thick"], NUMBERS["fft_worst_above"]), NUMBERS["fft_worst_thick"] < 0.01)
    gate("モデルあてはめは縞が 1 本未満の 50 nm でも決まる(全域で最大 %.2f nm)★逆犯罪の良さ: 雑音のほかに食い違いが無い"
         % NUMBERS["fit_worst_nm"], NUMBERS["fit_worst_nm"] < 1.0)

    print("   材料の取り違え(真値 SiO₂ 1000 nm を Si₃N₄ の n で読む)")
    sp = spectrum(1000.0)
    nS, nN = float(np.mean(n_of("SIO2", lam))), float(np.mean(n_of("SI3N4", lam)))
    closed = 1000.0 * nS / nN
    wrong = FO.film_thickness_fit(sp, "SI3N4", "SI", 0.0, 3000.0)
    right = FO.film_thickness_fit(sp, "SIO2", "SI", 0.0, 3000.0)
    fwrong = FO.film_thickness_fft(sp, "SI3N4")
    NUMBERS.update({"wrong_fit": wrong["thickness_nm"], "wrong_fft": fwrong["thickness_nm"], "wrong_closed": closed,
                    "wrong_rmse": wrong["rmse"], "right_rmse": right["rmse"]})
    gate("あてはめは光学的厚さ n d を保って d = 1000·n̄_SiO₂/n̄_Si₃N₄ = %.0f nm へ偏る(実測 %.0f nm、3 %% 以内)" % (closed, wrong["thickness_nm"]),
         abs(wrong["thickness_nm"] / closed - 1) < 0.03)
    gate("★あてはめは残差で取り違えに気づける(RMS %.3f、正しい材料 %.0e)、FFT は %.0f nm と出して何も言わない"
         % (wrong["rmse"], right["rmse"], fwrong["thickness_nm"]), wrong["rmse"] > 10 * NOISE and abs(fwrong["thickness_nm"] / closed - 1) < 0.06)

    print("   入射角(直入射のモデルで読む)")
    worst = 0.0
    for ang in (30.0, 60.0):
        t = FO.film_thickness_fit(spectrum(1000.0, angle_deg=ang), "SIO2", "SI", 0.0, 3000.0)["thickness_nm"]
        cl = 1000.0 * math.sqrt(1.0 - math.sin(math.radians(ang)) ** 2 / n_bar ** 2)
        worst = max(worst, abs(t / cl - 1))
        print("      %2.0f°: 見かけ %.1f nm、閉形式 d cos θ_膜 = %.1f nm" % (ang, t, cl))
    gate("斜入射を直入射で読むと d cos θ_膜 に縮む(30°・60°、0.2 % 以内)", worst < 0.002, "%.1e" % worst)

    print("   集光の NA(瞳を一様に満たす照明、直入射のモデルで読む)")
    na_rows = []
    worst = 0.0
    for na in (0.1, 0.3, 0.5, 0.7):
        t = FO.film_thickness_fit(spectrum(1000.0, na=na), "SIO2", "SI", 0.0, 3000.0)["thickness_nm"]
        cl = 1000.0 * (1.0 - na ** 2 / (4.0 * n_bar ** 2))
        na_rows.append((na, t, cl))
        worst = max(worst, abs(t / cl - 1))
        print("      NA %.1f: 見かけ %.1f nm、閉形式 d (1 − NA²/(4n²)) = %.1f nm" % (na, t, cl))
    gate("NA の角度平均は膜を d (1 − NA²/(4 n²)) に見せる(NA 0.1〜0.7、0.3 % 以内)", worst < 0.003, "%.1e" % worst)
    d_wash = n_bar * LO / 0.5 ** 2
    thick = spectrum(3000.0, na=0.5)
    blind = FO.film_thickness_fit(thick, "SIO2", "SI", 0.0, 4000.0)
    aware = FO.film_thickness_fit(thick, "SIO2", "SI", 0.0, 4000.0, na=0.5)
    NUMBERS.update({"wash_closed": d_wash, "na_blind": blind["thickness_nm"], "na_aware": aware["thickness_nm"]})
    gate("★縞が消える膜厚の閉形式 n λ/NA² = %.0f nm(NA 0.5、λ = 400 nm)を超える 3 µm は、直入射のモデルでは %.0f nm と"
         "破綻、NA を入れたモデルなら %.1f nm" % (d_wash, blind["thickness_nm"], aware["thickness_nm"]),
         abs(blind["thickness_nm"] - 3000.0) > 300.0 and abs(aware["thickness_nm"] - 3000.0) < 1.0)

    print("   共形な粗さ(R の Debye–Waller、モデルは粗さ無し)")
    rough = []
    for s in (2.0, 5.0, 10.0):
        t = FO.film_thickness_fit(spectrum(1000.0, roughness_nm=s), "SIO2", "SI", 0.0, 3000.0, fit_scale=True)
        rough.append((s, t["thickness_nm"] - 1000.0, t["scale"]))
        print("      σ = %4.1f nm: 膜厚の偏り %+.2f nm、反射率の倍率 %.3f" % rough[-1])
    gate("★共形な粗さは縞の位置をほとんど動かさない(σ = 10 nm で偏り 1 nm 未満)—— 効くのは反射率の大きさ",
         abs(rough[-1][1]) < 1.0 and rough[-1][2] < 0.95)
    return ds, err_h, err_r, err_f, na_rows


# --------------------------------------------------------------------------- #
# 5. 画像: 膜厚むらのあるウェハ                                                  #
# --------------------------------------------------------------------------- #
WAFER_R = 100.0     # mm(200 mm ウェハ)
D0 = 470.0          # 公称膜厚 nm(2 次の紫 → 縁で青へ。色が濃い帯)
COMET_DD = 80.0     # 彗星の尾の膜厚の減り [nm] (wafer_truth の注、文献の表の (a))


def wafer_truth(n_px):
    """スピンコートの形の膜厚分布(既知)と、ウェハのマスク。"""
    half = 108.0
    y, x = np.mgrid[0:n_px, 0:n_px]
    X = (x + 0.5) / n_px * 2 * half - half
    Y = (y + 0.5) / n_px * 2 * half - half
    r = np.hypot(X, Y)
    th = np.arctan2(Y, X)
    notch = np.hypot(X, Y - WAFER_R) < 3.0                       # 下端のノッチ
    mask = (r <= WAFER_R) & ~notch
    # 文献の表(PoC の docstring「スピンコート欠陥の文献表」)に結びつけた模型。量に出典が無いものは「模型」と書く。
    # (f) 大域のむら: Knápek 2020 は芯ずれ・水平の狂い・回転条件の不良でウェハ全体に「干渉の輪」が出る(顕微鏡の視野では
    #     見えず肉眼で見える)と書く。大きさの数値は原典に無い → 中心を 8 mm ずらした反り +4 % は**模型**。
    rho = np.hypot(X - 8.0, Y + 5.0) / WAFER_R
    d = D0 * (1.0 + 0.04 * rho ** 2)
    # (d) 放射状の筋(striation): 間隔 50〜200 µm(Birnie の研究ページ)で、この絵の 1 画素(0.45 mm)より細かい
    #     → ウェハ全体の絵では解像できない(画素の中で平均される)ので入れない。顕微鏡の図に入れる。
    # (a)(b) 彗星: 粒子の中心からウェハの縁まで続く小さな膜厚差(Knápek 2020)、流れは半径方向でなめらか
    #     (Birnie)、Coriolis による曲がりは実用上無視できる(Shepherd, Boujo & Sellier 2024)→ 尾は**半径方向に
    #     まっすぐ**、下流へ扇形に開く(Birnie の写真)。尾を薄く(レジスト販売元の応用ノートの「thinning」)、−80 nm(膜厚の
    #     17 %、Knápek の写真の縞の次数からの推定 10〜25 % の中)。開き方(半角 0.8 mm + 0.06·距離)は模型。
    r0c, phi0 = 38.0, 1.1
    along = r - r0c
    across = r * np.angle(np.exp(1j * (th - phi0)))                 # 中心線からの弧長(mm)
    comet = np.where(along > 0, np.exp(-(across / (0.8 + 0.06 * along)) ** 4), 0.0)
    d -= COMET_DD * comet
    # (e) 縁の盛り上がり(edge bead): 高さは膜厚と同程度まで(DTU: comparable to the resist thickness)、幅 1〜3 mm
    #     (US7335319B2)→ +55 %(+260 nm)・幅 2.5 mm。
    d += 260.0 * np.exp(-((WAFER_R - r) / 2.5) ** 2)
    return np.where(mask, d, np.nan), mask, r
    return np.where(mask, d, np.nan), mask, r


def chapter_identifiability():
    print("\n5a. 色だけで膜厚が決まるか(0〜1.5 µm を 2 nm 刻みで、RGB 3 色)")
    rng = np.random.default_rng(5)
    grid = np.arange(0.0, 1500.25, 0.25)
    lin = FO.film_color("SIO2", "SI", 0.0, 1500.0, grid.size)["linear_srgb"]
    d = np.arange(20.0, 1480.0, 2.0 if not REDUCED else 8.0)
    rgb = np.array([np.interp(d, grid, lin[:, c]) for c in range(3)])
    bands = ((0, 300), (300, 600), (600, 900), (900, 1200), (1200, 1500))
    out = {}
    for norm in (False, True):
        meas = rgb + NOISE * rng.standard_normal(rgb.shape)
        m = FO.film_thickness_map(meas[:, None, :], None, "SIO2", "SI", 0.0, 1500.0, mode="srgb",
                                  ambiguity_rms=2 * NOISE, normalize=norm)
        e, nc = m["thickness"][0] - d, m["n_candidates"][0]
        out[norm] = [(float(np.mean(nc[(d >= lo) & (d < hi)] >= 2)), float(np.mean(np.abs(e[(d >= lo) & (d < hi)]) > 30.0)))
                     for lo, hi in bands]
        print("      %s: " % ("明るさが分からない(色の向きだけ)" if norm else "明るさも校正済み")
              + "  ".join("%d〜%d nm 候補複数 %.0f %% / 30 nm 超 %.0f %%" % (lo, hi, 100 * a_, 100 * b_)
                          for (lo, hi), (a_, b_) in zip(bands, out[norm])))
    NUMBERS.update({"amb_thin_cal": out[False][1][0], "amb_thick_cal": out[False][4][0],
                    "wrong_thick_cal": out[False][4][1], "amb_thin_norm": out[True][1][0]})
    gate("★校正済みの理想の RGB でも 1.2〜1.5 µm は候補が複数(%.0f %%)、%.0f %% の点で 30 nm 以上外す(色が淡く周期的)"
         % (100 * out[False][4][0], 100 * out[False][4][1]), out[False][4][0] > 0.8 and out[False][4][1] > 0.2)
    gate("薄い側(300〜600 nm)は色が濃く、校正済みなら候補は 1 つ(複数 %.0f %%)" % (100 * out[False][1][0]), out[False][1][0] < 0.1)
    # 1.2 µm 超はどちらも 100 % 近くで飽和するので、比べるのは 0〜900 nm の帯と全体の平均。
    gate("明るさが分からない(色の向きだけで照合)と、0〜900 nm のどの帯でも候補が複数の点が増える(平均 %.0f %% → %.0f %%)"
         % (100 * np.mean([c_[0] for c_ in out[False]]), 100 * np.mean([n_[0] for n_ in out[True]])),
         all(n_[0] > c_[0] for n_, c_ in zip(out[True][:3], out[False][:3]))
         and np.mean([n_[0] for n_ in out[True]]) > np.mean([c_[0] for c_ in out[False]]))
    return d, bands, out


def chapter_images():
    print("\n5b. 画像: 膜厚むらのウェハを RGB カメラと分光カメラで(照明のむら ±6 % = 明るさは未校正)")
    n_px = 96 if REDUCED else 480
    d_true, mask, r = wafer_truth(n_px)
    rng = np.random.default_rng(3)
    dvals = d_true[mask]
    # 撮像(順モデル): 0.25 nm 刻みの早見表を補間 —— 反射率の補間誤差は 1e-5 未満
    grid = np.arange(0.0, 1500.0 + 0.25, 0.25)
    bands = np.arange(400.0, 701.0, 10.0)
    lutS = FO._model_lut(bands, "SIO2", "SI", (), grid, 0.0, 0.0, 1.0, 0.0, "poc")       # (N, 31)
    col = FO.film_color("SIO2", "SI", 0.0, 1500.0, grid.size)
    lin = col["linear_srgb"]
    light = illumination(n_px)[mask]
    cube = np.zeros((bands.size, n_px, n_px))
    rgb = np.zeros((3, n_px, n_px))
    for b in range(bands.size):
        cube[b][mask] = np.interp(dvals, grid, lutS[:, b]) * light
    for c in range(3):
        rgb[c][mask] = np.interp(dvals, grid, lin[:, c]) * light
    cube += NOISE * rng.standard_normal(cube.shape)
    rgb_meas = rgb + NOISE * rng.standard_normal(rgb.shape)
    t0 = time.time()
    spec = FO.film_thickness_map(cube, bands, "SIO2", "SI", 0.0, 1500.0, mode="spectral", step_nm=1.0,
                                 ambiguity_rms=2 * NOISE, normalize=True)
    t_spec = time.time() - t0
    full = FO.film_thickness_map(rgb_meas, None, "SIO2", "SI", 0.0, 1500.0, mode="srgb", step_nm=1.0,
                                 ambiguity_rms=2 * NOISE, normalize=True)
    win = FO.film_thickness_map(rgb_meas, None, "SIO2", "SI", D0 - 90.0, D0 + 90.0, mode="srgb", step_nm=1.0,
                                ambiguity_rms=2 * NOISE, normalize=True)
    e_spec = (spec["thickness"] - d_true)[mask]
    e_rgb = (full["thickness"] - d_true)[mask]
    e_win = (win["thickness"] - d_true)[mask]
    bead = (r >= WAFER_R - 8.0)[mask]
    inwin = (np.abs(dvals - D0) < 85.0)
    amb = full["n_candidates"][mask]
    NUMBERS.update({"map_rms": float(np.sqrt(np.mean(e_spec ** 2))), "map_unique": float(np.mean(spec["n_candidates"][mask] == 1)),
                    "rgb_wrong": float(np.mean(np.abs(e_rgb) > 30.0)), "rgb_ambig": float(np.mean(amb >= 2)),
                    "rgb_wrong_bead": float(np.mean(np.abs(e_rgb[bead]) > 30.0)),
                    "win_rms": float(np.sqrt(np.mean(e_win[inwin] ** 2))), "win_wrong_bead": float(np.mean(np.abs(e_win[bead]) > 30.0)),
                    "period": 550.0 / (2 * 1.46), "t_spec": t_spec})
    gate("分光カメラ(31 帯域、雑音 %.3f、明るさ未校正 = 形だけで照合)の膜厚マップは真値と RMS %.2f nm(%d 画素、%.1f 秒)"
         % (NOISE, NUMBERS["map_rms"], int(mask.sum()), t_spec), NUMBERS["map_rms"] < 2.0)
    gate("分光では候補が 1 つに決まる画素が %.1f %%" % (100 * NUMBERS["map_unique"]), NUMBERS["map_unique"] > 0.99)
    gate("★RGB では候補が 2 つ以上残る画素 %.0f %%、30 nm 以上外す画素 %.0f %%(端の盛り上がりでは %.0f %%)"
         "—— 色の周期 ≈ λ/(2n) = %.0f nm ごとに似た色に戻る"
         % (100 * NUMBERS["rgb_ambig"], 100 * NUMBERS["rgb_wrong"], 100 * NUMBERS["rgb_wrong_bead"], NUMBERS["period"]),
         NUMBERS["rgb_ambig"] > 0.1 and NUMBERS["rgb_wrong"] > 0.02)
    gate("工程の知識(公称 %.0f ± 90 nm、周期の半分以下)を足すと RGB でも決まる: 窓の中の RMS %.1f nm、"
         "★窓の外の端の盛り上がりは %.0f %% の画素で 30 nm 以上外す" % (D0, NUMBERS["win_rms"], 100 * NUMBERS["win_wrong_bead"]),
         NUMBERS["win_rms"] < 15.0 and NUMBERS["win_wrong_bead"] > 0.3)
    return d_true, mask, spec, full, win, rgb, col


def illumination(n):
    """斜めの照明のむら(左上が明るい、±6 %)。撮像と絵で同じものを使う。"""
    y, x = np.mgrid[0:n, 0:n]
    cx = (x + 0.5) / n * 2 - 1
    cy = (y + 0.5) / n * 2 - 1
    return 1.0 + 0.06 * (-cx * 0.6 - cy * 0.8)


# --------------------------------------------------------------------------- #
# 5c. 顕微鏡で見た彗星(comet)と暈(halo)                                       #
# --------------------------------------------------------------------------- #
#: 顕微鏡の照明(ハロゲン ≈ 3200 K の黒体)。film_color が同じ照明の白で正規化する(白色順応)。
HALOGEN_K = 3200.0
#: 顕微鏡の模型の量(文献の表に結びつけた。出典の無い量は「模型」)。
#:   繊維: 長さ 250 µm・太さ 12 µm(Knápek 2020 図 3 の繊維の長さ ≈ 0.25 mm、写真からの推定。太さは模型)。
#:   頭の際の盛り上がり: +HEAD_DD nm(Knápek 図 3 の頭の近くの干渉色の次数 2〜3 → 縞 1 本 ≈ 190 nm で 400〜600 nm、推定)、
#:     際から HEAD_W µm で減る(模型)。符号は その応用ノートの図の「bead」(頭の縁が厚い)。
#:   尾: 薄く TAIL_DD nm(その応用ノートの「thinned area」、大きさは Knápek の写真からの推定 10〜25 %)、下流へ扇形に開き
#:     0.3 mm で頭の幅の約 1.75 倍(Birnie の写真の 1.5〜2 倍、推定)。減衰の長さ TAIL_L は模型(論文は縁まで続くと書く)。
#:   放射状の筋: 間隔 STRI_UM µm(Birnie の 50〜200 µm の中)、振幅 STRI_REL × 膜厚(Birnie & Haas の模型 A/Hf ≈ 0.10〜0.15
#:     の下限の 1/5 —— 実測の振幅は見つかっていないので控えめに、模型)。
#:   焼き付いた薄片(Knápek 2020: 乾いたレジストの薄片がベークで固着): 不規則な薄片の周りに円形の暈が 1 周
#:     (図 3 右は 10〜15 µm の薄片に直径 ≈ 30 µm の 1 次の暈、Δd ≲ 0.2 µm、推定)。視野 25 µm の写真に合わせて縮めた模型。
HEAD_DD, HEAD_W = 450.0, 22.0
TAIL_DD, TAIL_L, TAIL_HALF_DEG = -80.0, 900.0, 4.3
STRI_UM, STRI_REL = 100.0, 0.02
HALO_DD, HALO_R, HALO_W = 55.0, 6.5, 2.2


def comet_micro(n_px, field_um, kind, d0=D0):
    """顕微鏡の視野(一辺 field_um µm)の膜厚 [nm] と異物のマスク。

    kind="comet": 繊維が作る彗星(Knápek 2020 図 3 左の形): 細長い不透明な繊維 + 頭の際の盛り上がり(縞が密)+ 下流
                  (半径の外向き)へ扇形に開いて色が段階的に変わる尾 + 流れに平行な放射状の筋。
    kind="flake": ベークで焼き付いたレジストの薄片(同 図 3 右の形): 小さな不規則な薄片 + 円形の暈が 1 周、尾は無い。

    ★根拠と限界: 形は Knápek 2020 の記述・Birnie の写真・ユーザーが見せた顕微鏡写真(出所・権利不明なので repo に
    入れない)に合わせ、量は上の定数の注に書いた文献表の値か推定に結びつけた。原典に数値の無い量(減衰の長さ・
    繊維の太さ・筋の振幅)は**模型**。膜厚の符号は原典どうしで食い違う(レジスト販売元の応用ノートは thinning、MIT FAB.nano は
    too thick)—— ここではその応用ノートの図(頭の縁に bead、下流に thinned area)に従った。
    """
    y, x = np.mgrid[0:n_px, 0:n_px]
    um = field_um / n_px
    X = (x + 0.5) * um - field_um / 2
    Y = (y + 0.5) * um - field_um / 2
    d = np.full((n_px, n_px), float(d0))
    if kind == "flake":
        rho = np.hypot(X, Y)
        ang = np.arctan2(Y, X)
        rim = 2.2 * (1.0 + 0.22 * np.sin(3 * ang + 0.4) + 0.12 * np.sin(5 * ang + 1.3))   # 不規則な薄片の輪郭
        particle = rho < rim
        d += HALO_DD * np.exp(-((rho - HALO_R) / HALO_W) ** 2)
        return d, particle, rho
    # 流れ(半径の外向き)は画像の右下へ。繊維は流れに対して 35° 傾いて落ちている。
    hx, hy = -0.17 * field_um, -0.17 * field_um
    fa = math.atan2(0.62, 1.0)
    ca, sa = math.cos(fa), math.sin(fa)
    u = (X - hx) * ca + (Y - hy) * sa                                   # 下流方向
    v = -(X - hx) * sa + (Y - hy) * ca
    ga = fa + math.radians(35.0)
    cg, sg = math.cos(ga), math.sin(ga)
    a_ = (X - hx) * cg + (Y - hy) * sg                                  # 繊維の軸
    b_ = -(X - hx) * sg + (Y - hy) * cg
    dist = np.hypot(np.maximum(np.abs(a_) - 125.0, 0.0), b_)            # 繊維(カプセル形)の軸からの距離
    particle = dist < 6.0
    d += HEAD_DD * np.exp(-np.maximum(dist - 6.0, 0.0) / HEAD_W)
    # 尾: 繊維の下流の端から、流れの向きに扇形に開く
    u_end = 125.0 * abs(math.cos(math.radians(35.0))) + 6.0
    half0 = 125.0 * abs(math.sin(math.radians(35.0))) + 6.0            # 流れに直交する繊維の幅(頭の幅)の半分
    uu = np.maximum(u - u_end, 0.0)
    half = half0 + uu * math.tan(math.radians(TAIL_HALF_DEG))
    prof = np.exp(-(v / half) ** 4)
    ramp = np.clip(uu / 120.0, 0.0, 1.0)
    tail = prof * np.exp(-uu / TAIL_L) * ramp * ramp * (3.0 - 2.0 * ramp)
    d += TAIL_DD * tail
    d += STRI_REL * d0 * np.sin(2 * np.pi * v / STRI_UM + 0.7) * np.clip((u + 300.0) / 300.0, 0.0, 1.0) * 0.5 \
        * (1.0 + np.sin(2 * np.pi * v / (2.7 * STRI_UM)))              # 流れに平行な筋(間隔 100 µm 前後、模型の振幅)
    return d, particle, u


def micro_render(d, particle, seed=0, sigma_px=1.2):
    """顕微鏡のカラー写真らしく: ハロゲン照明の干渉色、粒子の頭は暗く、光学のぼけ・周辺減光・センサ雑音。"""
    from scipy import ndimage
    import spectralrad as SR
    ill = SR.blackbody_spectrum(HALOGEN_K, 370.0, 790.0, 421)
    lo, hi = float(d.min()) - 5.0, float(d.max()) + 5.0
    col = FO.film_color("SIO2", "SI", max(lo, 0.0), hi, 801, illuminant=ill)
    lin = np.stack([np.interp(d, col["thickness_nm"], col["linear_srgb"][:, k]) for k in range(3)], -1)
    n = d.shape[0]
    y, x = np.mgrid[0:n, 0:n]
    rr = np.hypot(x - n / 2, y - n / 2) / (n / 2)
    shade = np.clip(np.hypot(*np.gradient(ndimage.gaussian_filter(particle.astype(float), 2.0))), 0, 1)
    head = np.stack([0.035 + 0.05 * shade] * 3, -1) * np.array([1.0, 0.95, 0.85])   # 不透明な粒子(縁だけ鈍く光る)
    lin = np.where(particle[..., None], head, lin)
    lin = np.stack([ndimage.gaussian_filter(lin[..., k], sigma_px) for k in range(3)], -1)
    lin *= (1.0 - 0.18 * rr ** 2)[..., None] * 1.25                    # 周辺減光と露出
    rng = np.random.default_rng(seed)
    lin = lin + rng.normal(0.0, 0.004, lin.shape) + 0.006 * rng.standard_normal(lin.shape) * np.sqrt(np.clip(lin, 0, None))
    return FO._srgb_gamma(lin)


def chapter_microscope():
    print("\n5c. 顕微鏡で見た繊維の彗星と焼き付いた薄片(模型 —— 形は Knápek 2020 などの記述、量は文献表の値か推定)")
    n = 120 if REDUCED else 480
    d, part, u = comet_micro(n, 500.0, "comet")
    lam = 2.0 / np.mean(1.0 / np.linspace(400.0, 700.0, 31))               # 可視の調和平均
    n_bar = float(np.mean(n_of("SIO2", np.linspace(400.0, 700.0, 31))))
    # 繊維の真ん中から繊維に直交して上流側(尾の無い側)へ引いた 1 本の線で、反射率(550 nm)の極大の数を数える
    fa = math.atan2(0.62, 1.0) + math.radians(35.0)
    t = np.linspace(6.5, 200.0, 800)
    px = (-0.17 * 500.0 + t * math.sin(fa) + 250.0) / 500.0 * n - 0.5
    py = (-0.17 * 500.0 - t * math.cos(fa) + 250.0) / 500.0 * n - 0.5
    from scipy import ndimage
    line = ndimage.map_coordinates(d, [py, px], order=1)
    R = FO._model_lut(np.array([550.0]), "SIO2", "SI", (), line, 0.0, 0.0, 1.0, 0.0, "poc")[:, 0]
    peaks = int(np.sum((R[1:-1] > R[:-2]) & (R[1:-1] > R[2:])))
    closed550 = float(line.max() - line.min()) * 2.0 * float(n_of("SIO2", [550.0])[0]) / 550.0   # 線の上の膜厚差から
    NUMBERS.update({"head_fringes": peaks, "head_fringes_closed": closed550})
    gate("頭の際の縞の本数(550 nm の反射の極大)%d 本 ≈ 閉形式 Δd·2n/λ = %.1f 本(±1)" % (peaks, closed550),
         abs(peaks - closed550) <= 1.0)
    dh, ph, rho = comet_micro(n, 25.0, "flake")
    ring = dh[~ph]
    gate("焼き付いた薄片の暈は 1 周だけ: 膜厚の山は半径 %.1f µm の 1 つ(+%.0f nm、縞 %.2f 本 < 1)"
         % (HALO_R, HALO_DD, HALO_DD * 2 * n_bar / lam), HALO_DD * 2 * n_bar / lam < 1.0 and float(ring.max() - D0) > 0.9 * HALO_DD)
    return (d, part), (dh, ph)


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def _lab_text(img, text, xy, size=13, anchor="lt"):
    import fullseye as fs
    return np.asarray(fs.text_box(img, text, xy, anchor=anchor, font_size=size))


def wafer_photo(d_true, mask, rgb_lin, exposure=1.3):
    """RGB カメラの絵(ウェハの質感: チャックの暗い台・ベベルの縁・照明のむら・ノッチ)。"""
    n = mask.shape[0]
    y, x = np.mgrid[0:n, 0:n]
    cx = (x + 0.5) / n * 2 - 1
    cy = (y + 0.5) / n * 2 - 1
    rr = np.hypot(cx, cy) * 108.0
    img = np.zeros((n, n, 3))
    base = np.moveaxis(rgb_lin, 0, -1) * exposure                # rgb_lin は照明のむらを含む(撮像と同じ)
    img[mask] = base[mask]
    bevel = mask & (rr > WAFER_R - 1.2)
    img[bevel] *= 0.55                                           # ベベル(面取り)は斜めで暗い
    bg = (~mask)
    chuck = 0.035 + 0.02 * np.exp(-((rr - 104.0) / 3.0) ** 2) * (rr > WAFER_R)
    img[bg] = np.stack([chuck, chuck, chuck * 1.08], -1)[bg]
    return FO._srgb_gamma(img)


def make_figures(lam, chart, est, imgs, ident, micro, real):
    # 0. 実測(公開データ)—— 主役の図を先頭に
    im, m = real["photo"]
    h, w = im.shape[:2]
    tm = _cmap(m["thickness"], (0.0, 140.0))
    import fullseye as fs
    ramp = np.asarray(_cmap(np.linspace(0.0, 1.0, 256)[None, :], (0.0, 1.0)))[0]
    pane = np.ones((h, w + 110, 3))
    pane[:, :w] = tm
    field = np.zeros((h, w + 110))
    field[:, :w] = m["thickness"]
    mk = np.zeros((h, w + 110), bool)
    mk[:, :w] = True
    pane = np.asarray(fs.annotate_colorbar(pane, field, (w + 16, 20, 18, h - 40), lut=ramp, vmin=0.0, vmax=140.0,
                                           alpha=0.0, mask=mk, unit="nm", label_fmt="{:.0f}", font_size=12))[..., :3]
    gap = np.ones((h, 10, 3))
    canvas = np.ones((h + 40, 2 * w + 120, 3))
    canvas[34:34 + h] = np.concatenate([im, gap, pane], axis=1)
    canvas = _lab_text(canvas, "実物の顕微鏡写真(左 Si、右 SiO₂)", (4, 4), 13)
    canvas = _lab_text(canvas, "film_thickness_map の膜厚 0〜140 nm", (w + 14, 4), 13)
    canvas = _lab_text(canvas, "SiO₂ 側の中央値 %.1f nm(基準 %.1f nm)" % (NUMBERS["real_rgb_film"], NUMBERS["real_ref"]),
                       (w + 14 + w // 2, 34 + h // 2), 13, anchor="lm")
    figs.save("real_micrograph_thickness", canvas,
              "実物の顕微鏡のカラー写真(左が裸の Si、右が Si 上の SiO₂)から、裸の Si の領域で色を材料表の Si に合わせ、"
              "film_thickness_map(RGB)で画素ごとの膜厚を出した。SiO₂ 側の中央値 %.1f nm、基準 %.1f nm(%+.0f %%)。カメラの"
              "分光感度は不明で、CIE の等色関数で代用している。視野の周辺減光(%.0f %%)は裸の Si の側だけで当てはめて割った"
              "(SiO₂ 側の明るさの傾き %+.0f %% → %+.0f %%)。Si 側は中央値 %.1f nm だが 95 パーセンタイル %.0f nm —— 0 nm 付近では"
              "反射率が膜厚の 2 乗でしか変わらないので、写真の明るさの揺れが数 nm に化ける(補正前は減光で Si 側が 2 段に分かれていた)。"
              % (NUMBERS["real_rgb_film"], NUMBERS["real_ref"], 100 * (NUMBERS["real_rgb_film"] / NUMBERS["real_ref"] - 1),
                 100 * NUMBERS["real_vignette"], 100 * NUMBERS["real_tilt_before"], 100 * NUMBERS["real_tilt_after"],
                 NUMBERS["real_rgb_bare"], NUMBERS["real_rgb_bare_p95"])
              + "出典: Schwarz ら, Adv. Opt. Mater. (2024) doi:10.1002/adom.202402502、データ Zenodo 10.5281/zenodo.13753754(CC BY 4.0)。改変: 1920×1080 → 640×360 に縮小し JPEG で保存、右に計算した膜厚の図を並べた。")
    lamr = real["lam"]
    na_b, fit_b = real["fit_na"]
    m0 = FO.multilayer_reflectance([("SIO2", real["fit0"]["thickness_nm"])], "SI", wavelengths_nm=lamr)[:, 1]
    mn = FO.multilayer_reflectance([("SIO2", fit_b["thickness_nm"])], "SI", wavelengths_nm=lamr, na=na_b)[:, 1]
    figs.save_plot("real_spectra",
                   [("実測 SiO₂ 100 %", lamr, real["full"][:, 1]), ("実測 裸の Si", lamr, real["bare"][:, 1]),
                    ("あてはめ 直入射 %.1f nm" % real["fit0"]["thickness_nm"], lamr, m0),
                    ("あてはめ NA %.1f %.1f nm" % (na_b, fit_b["thickness_nm"]), lamr, mn)],
                   xlabel="波長 [nm]", ylabel="反射率", styles=[None, None, "dashed", "dotted"],
                   colors=["emphasis", "neutral", "reference", "right"],
                   title="実測の顕微分光(基準 %.1f nm)に転送行列をあてはめる" % NUMBERS["real_ref"],
                   caption="実測の反射スペクトルに film_thickness_fit を当てた。直入射のモデルは %.1f nm、残差が最小の NA %.1f で"
                           " %.1f nm。裸の Si は材料表の Si と中央値 %.1f %% 差。" % (real["fit0"]["thickness_nm"], na_b,
                                                                       fit_b["thickness_nm"],
                                                                       100 * (NUMBERS["real_bare_ratio_median"] - 1))
                           + "出典: Schwarz ら, Adv. Opt. Mater. (2024) doi:10.1002/adom.202402502、データ Zenodo 10.5281/zenodo.13753754(CC BY 4.0)。改変: 表から 2 本を選び、モデルの曲線を重ねた。")
    sh = real["sheffield"]
    regular = [r for r in sh if r[4] >= 100.0]
    outlier = [r for r in sh if r[4] < 100.0]
    figs.save_plot("real_standards",
                   [("推定(最良の候補)", [r[3] for r in regular], [r[4] for r in regular]),
                    ("外れ: 公称 198.7 → 最良 51 nm(正解は 2 番目)",
                     [r[3] for r in outlier], [r[4] for r in outlier]),
                    ("公称 = 推定", [150.0, 520.0], [150.0, 520.0])],
                   xlabel="標準試料の公称の膜厚 [nm]", ylabel="スペクトルから推定 [nm]",
                   kinds=["scatter", "scatter", "line"],
                   styles=[None, None, "dashed"], colors=["emphasis", "wrong", "reference"],
                   xlim=(150, 520), ylim=(0, 520),
                   title="安価な分光器で測った SiO₂/Si 標準(10 本)",
                   caption="476.3 nm は最大 %.1f %%、198.7 nm は中央値 %.1f %% 厚めに読み、1 本は最良の候補が 51 nm に外れた"
                           "(正しい膜厚は 2 番目の候補)。" % (100 * NUMBERS["real_s1_worst"], 100 * NUMBERS["real_s2_median"])
                           + "出典: Sánchez-Arriaga ら, Sensors 23, 5326 (2023) doi:10.3390/s23115326、データ 10.15131/shef.data.23285603(CC BY 4.0)。改変: 繰り返しの平均を取りあてはめた結果だけを描いた。")
    # 1. 膜厚 × 波長の反射率と色の帯(縞が増えていく)
    nd = 401
    dd = np.linspace(0.0, 2000.0, nd)
    Rm = FO._model_lut(np.linspace(LO, HI, 401), "SIO2", "SI", (), dd, 0.0, 0.0, 1.0, 0.0, "poc")
    col = FO.film_color("SIO2", "SI", 0.0, 2000.0, nd, exposure=1.6)["srgb"]
    Rimg = np.repeat(np.clip(Rm / Rm.max(), 0, 1)[..., None], 3, -1)
    strip = np.repeat(col[:, None, :], 60, axis=1)
    gap = np.ones((nd, 8, 3))
    pane = np.concatenate([Rimg, gap, strip], axis=1)
    canvas = np.ones((nd + 100, pane.shape[1] + 90, 3))
    canvas[40:40 + nd, 80:80 + pane.shape[1]] = pane
    canvas = _lab_text(canvas, "Si 上の SiO₂: 反射率(白 = 高い)と見える色", (80, 8), 14)
    canvas = _lab_text(canvas, "400 nm", (80, nd + 46), 11)
    canvas = _lab_text(canvas, "800 nm", (80 + 401, nd + 46), 11, anchor="rt")
    canvas = _lab_text(canvas, "色(D65)", (80 + 409, nd + 46), 11)
    for t in (0, 500, 1000, 1500, 2000):
        canvas = _lab_text(canvas, "%d nm" % t, (74, 40 + int(t / 2000 * (nd - 1))), 11, anchor="rm" if 0 < t < 2000 else ("rt" if t == 0 else "rb"))
    figs.save("fringes_vs_thickness", canvas,
              "縦が膜厚 0〜2 µm、横が波長 400〜800 nm の反射率(転送行列、材料表の SiO₂ と Si)。膜が厚いほど縞の本数が "
              "d·Δx で増え、右の帯(D65 で見た色)は 1 µm を過ぎると縞が帯域内で平均されて淡くなる。")
    # 2. スペクトル
    series = []
    for d in (100.0, 500.0, 1000.0, 2000.0):
        p = spectrum(d)
        series.append(("%d nm" % d, p[:, 0], p[:, 1]))
    figs.save_plot("spectra", series, xlabel="波長 [nm]", ylabel="反射率", ylim=(0.0, 0.6),
                   title="Si 上の SiO₂ の反射スペクトル(縞の本数 = d·Δx)",
                   caption="100 nm は縞が 1 本未満、2 µm は 7 本余り。FFT 法は縞の周期を読み、モデルあてはめは形そのものを読む。")
    # 3. 色見本と色表
    (cD, resD), (cT, resT) = chart["D65"], chart["三波長"]
    w = 1200
    tt = np.linspace(0.0, 1600.0, w)
    rowD = np.array([np.interp(tt, cD["thickness_nm"], cD["srgb"][:, k]) for k in range(3)]).T
    linT = cT["linear_srgb"]
    rowT = FO._srgb_gamma(np.array([np.interp(tt, cT["thickness_nm"], linT[:, k]) for k in range(3)]).T * 1.3)
    rowD = FO._srgb_gamma(np.array([np.interp(tt, cD["thickness_nm"], cD["linear_srgb"][:, k]) for k in range(3)]).T * 1.6)
    chartrow = np.ones((w, 3))
    for i, (t_um, name) in enumerate(CHART):
        t0 = t_um * 1000.0
        t1 = CHART[i + 1][0] * 1000.0 if i + 1 < len(CHART) else 1600.0
        c = np.array(CSS[chart_css(name)[0]]) / 255.0
        chartrow[(tt >= t0) & (tt < t1)] = c
    H = 70
    canvas = np.ones((3 * H + 140, w + 20, 3))
    for k, row in enumerate((rowD, rowT, chartrow)):
        canvas[40 + k * (H + 25):40 + k * (H + 25) + H, 10:10 + w] = row[None, :, :]
    canvas = _lab_text(canvas, "計算(D65、連続光)", (14, 44), 12)
    canvas = _lab_text(canvas, "計算(三波長の蛍光灯の模型、輝線)", (14, 44 + H + 25), 12)
    canvas = _lab_text(canvas, "公表の色表(Pliskin & Conrad 1964 の写し)の色名を CSS の色で塗った帯", (14, 44 + 2 * (H + 25)), 12)
    for t in range(0, 1601, 200):
        canvas = _lab_text(canvas, "%d" % t, (10 + int(t / 1600 * (w - 1)), 40 + 3 * (H + 25) - 18), 11,
                           anchor="lt" if t == 0 else ("rt" if t == 1600 else "ct"))
    canvas = _lab_text(canvas, "SiO₂ の膜厚 [nm] (Si 上、垂直に見る)", (10, 8), 14)
    figs.save("wafer_color_chart", canvas,
              "上: 材料表の n,k と転送行列から計算した干渉色(D65)。中: 同じ膜を輝線の照明で(厚い膜の色が残る)。"
              "下: 公表の色表の色名(CSS の名前つき色で塗った目安。色名の彩度は実物より高い)。"
              "1〜3 次の色相は %.0f %% の行で ±36° 以内。" % (100 * NUMBERS["chart_D65_hit_I_III"]))
    # 4. FFT とあてはめの誤差
    ds, eh, er, ef, na_rows = est
    lim = NUMBERS["fft_limit_closed"]
    figs.save_plot("fft_vs_fit_error",
                   [("FFT(hann)", ds, np.clip(eh, -150, 150)), ("FFT(rect)", ds, np.clip(er, -150, 150)),
                    ("モデルあてはめ", ds, ef), ("閉形式の下限 2/Δx", [lim, lim], [-150, 150])],
                   xlabel="真の膜厚 [nm]", ylabel="推定 − 真値 [nm] (±150 で切る)", ylim=(-150, 150),
                   styles=[None, None, None, "dashed"], colors=["emphasis", "neutral", "right", "reference"],
                   title="FFT 法は縞が 2 本未満(< %.0f nm)で崩れる、あてはめは崩れない" % lim,
                   caption="雑音 %.3f。FFT の窓の主ローブ(DC の山)にピークが埋もれる薄さは閉形式 2/Δx で先に分かる。"
                           "あてはめの誤差の小ささは逆犯罪(モデルが同じ)の分を含む。" % NOISE)
    na = np.array([r[0] for r in na_rows])
    figs.save_plot("na_apparent_thickness",
                   [("あてはめ(直入射のモデル)", na, np.array([r[1] for r in na_rows])),
                    ("閉形式 d(1 − NA²/(4n²))", na, np.array([r[2] for r in na_rows]))],
                   xlabel="対物の NA", ylabel="見かけの膜厚 [nm] (真値 1000)", kinds=["scatter", "line"],
                   styles=[None, "dashed"], colors=["emphasis", "reference"],
                   title="集光の角度平均で膜は薄く見える",
                   caption="顕微分光の対物は斜めの光も入れる。膜の中の光路は cos θ_膜 で縮むので、直入射のモデルで読むと薄く出る。")
    # 5. ウェハ
    d_true, mask, spec, full, win, rgb, colr = imgs
    photo = wafer_photo(d_true, mask, rgb)
    figs.save("wafer_rgb_camera", photo,
              "RGB カメラ(CIE 1931 の等色関数、D65)で撮った SiO₂ 膜(公称 %.0f nm)のウェハ。"
              "芯ずれの干渉の輪(+4 %%、模型)・粒子の彗星(縁まで半径方向、−80 nm)・端の盛り上がり(+260 nm、幅 2.5 mm)の色むら。量は PoC の docstring の文献表に結びつけた(出典の無い量は模型)。" % D0)
    err = np.where(mask, spec["thickness"] - d_true, 0.0)
    erg = np.where(mask, full["thickness"] - d_true, 0.0)
    ncand = np.where(mask, full["n_candidates"], 0).astype(float)
    figs.save_grid("thickness_maps",
                   [np.where(mask, d_true, np.nanmin(d_true)), np.where(mask, spec["thickness"], np.nanmin(d_true)),
                    np.clip(err, -1, 1), np.clip(erg, -200, 200), ncand],
                   captions=["真の膜厚 [nm]", "分光 31 帯域の推定", "分光 − 真値(±1 nm)", "RGB − 真値(±200 nm)",
                             "RGB の候補の数"],
                   signed=[False, False, True, True, False], ncols=3,
                   vrange=[(float(np.nanpercentile(d_true, 0.5)), float(np.nanpercentile(d_true, 90.0)))] * 2
                   + [(-1, 1), (-200, 200), (0, 4)],
                   caption="分光カメラは全画素で真値と RMS %.2f nm。RGB 3 色は候補が 2 つ以上の画素が %.0f %% で、"
                           "周期 ≈ λ/(2n) ごとに似た色に戻るので次数を取り違える。" % (NUMBERS["map_rms"], 100 * NUMBERS["rgb_ambig"]))
    d_id, bands_id, out_id = ident
    mids = np.array([(lo + hi) / 2 for lo, hi in bands_id])
    figs.save_plot("rgb_identifiability",
                   [("明るさ校正済み: 候補が複数", mids, 100 * np.array([a for a, _ in out_id[False]])),
                    ("明るさ未校正: 候補が複数", mids, 100 * np.array([a for a, _ in out_id[True]])),
                    ("明るさ校正済み: 30 nm 超を外す", mids, 100 * np.array([b for _, b in out_id[False]])),
                    ("明るさ未校正: 30 nm 超を外す", mids, 100 * np.array([b for _, b in out_id[True]]))],
                   xlabel="真の膜厚 [nm] (300 nm ごとの帯の中央)", ylabel="点の割合 [%]", ylim=(0, 100),
                   styles=[None, None, "dashed", "dashed"], colors=["emphasis", "wrong", "emphasis", "wrong"],
                   title="RGB 3 色で膜厚が決まるか(理想の測色カメラ、雑音 %.3f)" % NOISE,
                   caption="厚い膜ほど色が淡く周期的に似るので、色だけでは次数を取り違える。明るさが分からない(照明のむら)と"
                           "色の向きだけで照合するので、薄い側でも候補が増える。")
    # 6. 膜厚を振る GIF(スペクトル + 色)
    frames = []
    figure_scale = figs.figure_scale()
    for d in np.linspace(0.0, 1500.0, 46):
        p = spectrum(d)
        plot = figs.render_plot([("R(λ)", p[:, 0], p[:, 1])], xlabel="波長 [nm]", ylabel="反射率",
                                title="SiO₂ %4.0f nm on Si" % d, size=(420, 280), ylim=(0.0, 0.6))
        sw = FO.film_color("SIO2", "SI", d, d + 1e-6, 2, exposure=1.6)["srgb"][0]
        yy, xx = np.mgrid[0:280 * figure_scale, 0:140 * figure_scale]
        disk = np.hypot(xx - 70 * figure_scale, yy - 140 * figure_scale) < 62 * figure_scale
        pane = np.full((280 * figure_scale, 140 * figure_scale, 3), 0.16)
        pane[disk] = sw                                           # その膜厚のウェハ(D65 で見た色)
        frame = np.concatenate([np.asarray(plot)[..., :3],
                                np.ones((280 * figure_scale, 6 * figure_scale, 3)), pane], axis=1)
        frames.append((np.clip(frame, 0, 1) * 255).astype(np.uint8))
    figs.save_gif("thickness_sweep", frames, "膜厚を 0 → 1.5 µm に振ると縞が増え、色が周期的に巡りながら淡くなる。", fps=8)
    # 7. 顕微鏡で見た彗星と暈(写真らしい絵 + 同じ模型の膜厚マップ)
    (dc, pc), (dh, ph) = micro
    a = micro_render(dc, pc, seed=1)
    b = micro_render(dh, ph, seed=2, sigma_px=2.5)
    vc = (float(np.percentile(dc[~pc], 1)), float(np.percentile(dc[~pc], 99.5)))
    tm = np.asarray(_cmap(np.where(pc, vc[0], dc), vc))
    th = np.asarray(_cmap(np.where(ph, D0, dh), (D0 - 5, D0 + HALO_DD + 5)))
    n = dc.shape[0]
    a = _scalebar(a, 100.0 / 500.0 * n, "100 µm")
    b = _scalebar(b, 5.0 / 25.0 * n, "5 µm")
    tm = _scalebar(tm, 100.0 / 500.0 * n, "100 µm")
    th = _scalebar(th, 5.0 / 25.0 * n, "5 µm")
    gap = np.ones((n, 10, 3))
    top = np.concatenate([a, gap, tm], axis=1)
    bot = np.concatenate([b, gap, th], axis=1)
    canvas = np.ones((2 * n + 90, top.shape[1], 3))
    canvas[30:30 + n] = top
    canvas[60 + n:60 + 2 * n] = bot
    canvas = _lab_text(canvas, "顕微鏡 0.5 mm 角: 繊維が作る彗星(ハロゲン照明)", (4, 6), 13)
    canvas = _lab_text(canvas, "同じ模型の膜厚 %.0f〜%.0f nm" % vc, (n + 14, 6), 13)
    canvas = _lab_text(canvas, "顕微鏡 25 µm 角: 焼き付いたレジストの薄片", (4, 36 + n), 13)
    canvas = _lab_text(canvas, "膜厚 %.0f〜%.0f nm" % (D0, D0 + HALO_DD), (n + 14, 36 + n), 13)
    figs.save("comet_microscope", canvas,
              "Si 上の SiO₂ %.0f nm に粒子が乗ったときの模型を、ハロゲン(3200 K)照明の顕微鏡で見た色(左)と膜厚(右)。"
              "上: 細長い不透明な粒子の頭、頭の際の急な盛り上がり(+%.0f nm、縞 %d 本)、下流へ扇形に開く尾"
              "(%.0f nm、%.0f µm で減衰)。下: 焼き付いたレジストの薄片の円形の暈(+%.0f nm、縞 1 周)。形は Knápek 2020 の記述と写真に合わせた模型で、"
              "★模型: 膜厚変化の大きさは原典に数値が無く、写真の縞の次数からの推定(PoC の docstring の文献表)。" % (D0, HEAD_DD, NUMBERS["head_fringes"], TAIL_DD, TAIL_L, HALO_DD))


def _cmap(v, vr):
    import fullseye as fs
    return np.clip(np.asarray(fs.colorize_depth(v, vmin=vr[0], vmax=vr[1]), np.float64)[..., :3], 0, 1)


def _scalebar(img, length_px, text):
    out = np.array(img, dtype=np.float64, copy=True)
    n = out.shape[0]
    x1 = n - 16
    x0 = int(x1 - length_px)
    out[n - 22:n - 17, x0:x1] = 1.0
    return _lab_text(out, text, ((x0 + x1) // 2, n - 26), 11, anchor="cb")


def main():
    t0 = time.time()
    print("PoC 分光反射率による薄膜の膜厚測定(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_truth()
    real = chapter_real()
    lam, _span = chapter_fringes()
    chart = chapter_chart()
    est = chapter_estimate()
    ident = chapter_identifiability()
    imgs = chapter_images()
    micro = chapter_microscope()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(lam, chart, est, imgs, ident, micro, real)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
