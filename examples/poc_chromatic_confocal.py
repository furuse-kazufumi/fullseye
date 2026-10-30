# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: クロマティック共焦点(白色共焦点)変位センサ —— 硝材の分散で「虹のものさし」を作り、色で高さを読む。

【問い】白色光を軸上色収差の大きいレンズで集光すると、波長ごとに焦点の高さが変わる。面で反射して
ピンホールを通って分光器に戻るのは、面にピントの合った色だけ —— だから**戻ってきた光の色が高さ**になる。
透明体の表裏・フィルム厚・鏡面・段差を、走査せずに 1 本のスペクトルで非接触に測る定番の方式。
そのセンサを、**対物レンズの処方と硝材の分散(材料表)から**組み立て、どこまで正しく、どこで壊れるかを
閉形式と外の真値で採点する。光学系(高分散の重フリント、n_d 1.923・V_d 20.9 の対物レンズ)と観察対象(ホウケイ酸クラウン n_d 1.517・V_d 64.2 の板・金・アルミ・Si)は
**同じ材料表**(`materials`)を引く。

新 op 6 本(`chromconf`、`opsoptics` の `confocal`): `chromatic_confocal_probe`(処方 → 較正表)、
`confocal_axial_response`(共焦点の軸応答、sinc² と収差つき)、`chromatic_confocal_spectrum`(面と層 →
戻りスペクトル)、`chromatic_confocal_peaks`(ピーク波長、4 つの推定法)、`chromatic_confocal_readout`
(高さと厚さ)、`chromatic_confocal_limits`(範囲・分解能・傾き・最小膜厚)。5 章:

  1. **虹のものさし**: 重フリントの非球面単レンズ(f ≈ 16 mm、ビーム半径 2.5 mm)で 450〜700 nm の焦点が
     光軸上に並ぶ。焦点の位置は厚肉レンズの閉形式 f(λ) = f₀(n₀ − 1)/(n(λ) − 1)(材料表の n(λ))と一致、
     軸方向の応答の幅は鏡面の閉形式 0.443 λ/(1 − cos α) と一致(∝ λ/NA²)。★非球面は 575 nm でしか
     球面収差を消さない(色球面収差): 450 nm では縁の光線の焦点が 40 µm 手前にずれ、応答のピークは
     約その半分ずれて高さも 3/4 に落ちる。較正(鏡を置いてピークを読む)がこれを吸収する。同じ f の
     球面の単レンズは縦収差が大きすぎて幅が何倍にも崩れ、ハイパークロマート(重フリントの正 + フッ素クラウンの負、
     色消しの逆)は同じ焦点距離で範囲が広がる。
  2. **実測の流れ**: 面の高さ → 戻りスペクトル → ピーク → 高さ。推定法 4 つの偏り(雑音なし)を
     測り、★「設計値の較正表」では残る推定法の偏りを、実機と同じ「鏡を動かして読む較正」で消す。
     段差と傾いた面の断面、雑音つきの再現性。
  3. **透明な板**: ホウケイ酸クラウン 500 µm の表裏 2 ピーク → 見かけの厚さ × n(λ₂)。★近軸の補正だけでは
     平板の球面収差の分だけ薄く出る。空気側の焦点位置で ray parameter を保つ Snell 光線式を
     独立な真値にして NA 補正を検証する。座標は空気側から見た見かけの深さで、厚さは実空間へ戻す。
     カタログの n_d を使うと、下の面の色の n との差だけずれる。
  4. **失敗条件**: (a) 鏡面の傾きが NA を超えると戻らない(瞳の重なり、閉形式とモンテカルロ)、
     (b) 粗い面は鏡面成分が短波長ほど減って(TIS)ピークを赤へ引く、(c) 色のついた対象(金の反射率は
     500〜600 nm で急に立ち上がる)がピークを引っ張る偏りは、反射率の傾き / 応答の曲率の閉形式で
     予言できる、(d) 薄すぎる膜は 2 ピークが 1 つに潰れる(Sparrow の閉形式、readout は拒否)、
     (e) 光源(白色 LED = 青 + 蛍光体)のむらは白色参照で割って補正する。
  5. **図**: 虹のものさし(光線図)、較正表、高さで動くスペクトルの GIF、段差・板・金の読み、限界。

EXTEND: 実機の分光器のデータを読むなら、`chromatic_confocal_peaks` に (λ, counts) の pairs と白色参照を
渡すだけでよい。ただし較正表は**レンズの設計値でなく、鏡を既知の位置に動かして測ったもの**に差し替える
(この PoC の 2 章の手順そのもの)。層のあいだの干渉(数 µm の薄膜で出るチャネルドスペクトル)、傾いた面の
応答の非対称、スペックルはここでは入れていない —— 実機の数字をこの PoC の数字と比べてはいけない。

【外部真値】厚肉レンズの近軸の式(材料表の n(λ) で計算、raytrace と独立)、鏡面の共焦点の軸応答
sinc²(u/2)(Corle–Chou–Kino 1986)、瞳の重なりのモンテカルロ、平行平板の焦点ずれの閉形式
(`materials.plate_focus_shift`)、Sparrow の基準、TIS の式。
【文献との照合】範囲の式(Hillenbrand 2012 式 (2))、軸応答の半値 kz(1 − cos α) = 1.39(Corle 1986)、
傾きの上限 = 半頂角(Hillenbrand 2012)、推定法の系統誤差が面の高さで変わること(Chen 2018 / 2019)、
透明板に n と NA の両方が要ること(Choi 2020)は一次文献で確かめた。NA の補正式・金や粗さの偏りの大きさ・
白色 LED の分光分布・薄膜の限界は**模型**(値の対応表は `chromconf` の docstring)。
【実画像】6 章: 公開論文(Qin M. ほか, Sensors 24(20):6649, 2024, DOI 10.3390/s24206649, CC BY 4.0)の
図 3(a)(ライン共焦点の生の分光画像)と図 6(b)(標準溝の高さの断面)を読み、基準深さ 66.14 µm と突き合わせる。
生データは公開されていないので、**図の画素から読む記録値**(環境変数がある時だけ実行。縮小・JPEG・印の大きさが誤差になり、1 画素 ≈ 0.33 µm)。
図 3(a) からは溝の段差を「図の画素」でしか読めない(分光器の画素との比も波長の較正も書かれていない)ので、µm の
突き合わせは図 6(b) の目盛で行う —— つまりこれは**論文の測定結果を図から読み直す**検査で、この PoC の
センサの模型を実機で検証するものではない。図は repo に同梱せず、`FULLSEYE_CCF_REAL_DIR` に置いたときだけ走る。
【学習した数】0。【較正】2 章の「鏡を動かして読む」1 回だけ(合成のデータで)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import chromconf as CC  # noqa: E402
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import materials as MT  # noqa: E402
import raytrace as RT  # noqa: E402
import spectralrad as SR  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
INF = float("inf")
F0 = 16.0                     # 575 nm の焦点距離 [mm]
BEAM = 2.5                    # ビーム半径 [mm]
LAM0 = 0.575                  # 非球面で球面収差を消す波長 [µm]


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _n(material, wl_nm):
    return float(MT.material_optical_constants(material, float(wl_nm))["n"])


def singlet(aspheric=True, glass=CC.GLASS_DENSE_FLINT):
    """平凸単レンズ(平面を光源側)。aspheric なら出射面を双曲面 k = −n²(575 nm で無収差)。"""
    n = RT.refractive_index(glass, LAM0)
    last = {"R": -(n - 1.0) * F0, "t": None, "n": 1.0}
    if aspheric:
        last["k"] = -n * n
    return [{"R": INF, "t": 4.0, "n": glass, "ap": BEAM}, last]


def hyperchromat():
    """ハイパークロマート: 負のフッ素クラウン(V 91)+ 正の重フリント(V 21)の貼り合わせ(色消しの逆)。

    薄肉の近似で φ_FK58 = −φ、φ_SF66 = +2φ(色の和 φ₁/V₁ + φ₂/V₂ が単レンズの約 1.8 倍)。最終面の
    4 次の非球面係数を、575 nm の縁の光線の縦収差が 0 になるよう二分法で決める。
    """
    from scipy.optimize import brentq

    def mk(a4):
        return [{"R": INF, "t": 1.5, "n": CC.GLASS_FLUOR_CROWN, "ap": BEAM}, {"R": 7.3, "t": 4.5, "n": CC.GLASS_DENSE_FLINT},
                {"R": -600.0, "t": None, "n": 1.0, "asph": (a4,)}]

    def lsa(a4):
        s = RT.lens_system(mk(a4), stop=0, wavelength_um=LAM0)
        p = RT.paraxial_trace(s)
        return CC._marginal_focus(RT, s, BEAM) - p["bfl"]

    return mk(brentq(lsa, 1e-5, 1e-3, xtol=1e-15))


# --------------------------------------------------------------------------- #
# 1. 虹のものさし                                                                #
# --------------------------------------------------------------------------- #
def chapter_ruler():
    print("\n1. 虹のものさし: 重フリントの非球面単レンズで 450〜700 nm の焦点が光軸上に並ぶ")
    npts = 26                                                                              # 10 nm 刻み(スプラインの門の前提)
    P = CC.chromatic_confocal_probe(singlet(True), 0, 450.0, 700.0, npts)
    wl = np.array(P["wavelength_nm"])
    # 外部真値: 平面が前の平凸レンズは後側主点が曲面の頂点にあり BFL = f = R/(1 − n) —— raytrace と独立に材料表から
    n0 = RT.refractive_index(CC.GLASS_DENSE_FLINT, LAM0)
    f_closed = np.array([(n0 - 1.0) * F0 / (_n(CC.GLASS_DENSE_FLINT, w) - 1.0) for w in wl])          # mm
    par = np.array(P["paraxial_um"]) * 1e-3 + P["origin_mm"]
    err = float(np.max(np.abs(par - f_closed))) * 1e3
    NUMBERS["focus_closed_err_um"] = err
    gate("近軸焦点 = 厚肉レンズの閉形式 f₀(n₀ − 1)/(n(λ) − 1)(材料表の n(λ)、全波長 1e-6 µm)", err < 1e-6, "最大 %.1e µm" % err)
    rng_closed = (f_closed[-1] - f_closed[0]) * 1e3
    NUMBERS.update({"range_um": P["range_um"], "range_paraxial_um": P["range_paraxial_um"], "range_closed_um": rng_closed})
    gate("測定範囲(450→700 nm の焦点ずれ)= %.0f µm、閉形式 %.0f µm との差 %.1e µm(近軸)"
         % (P["range_um"], rng_closed, abs(P["range_paraxial_um"] - rng_closed)),
         abs(P["range_paraxial_um"] - rng_closed) < 1e-6)
    vd = MT.abbe_number(CC.GLASS_DENSE_FLINT)["vd"]
    thin_fc = F0 / vd                                                                       # F−C の焦点差 ≈ f/V
    fc = (n0 - 1.0) * F0 * (1.0 / (_n(CC.GLASS_DENSE_FLINT, 656.27) - 1.0) - 1.0 / (_n(CC.GLASS_DENSE_FLINT, 486.13) - 1.0)) * 1e3
    NUMBERS.update({"fc_shift_um": fc, "f_over_v_um": thin_fc * 1e3})
    gate("F 線〜C 線の焦点差 %.0f µm ≈ f/V_d = %.0f µm(V_d = %.1f、5 %% 以内 —— 分散の大きい硝子ほど目盛が長い)"
         % (fc, thin_fc * 1e3, vd), abs(fc / (thin_fc * 1e3) - 1.0) < 0.05)
    # 応答の幅: 閉形式と数値積分
    i0 = int(np.argmin(np.abs(wl - 575.0)))
    na0 = P["na"][i0]
    z = np.linspace(-60.0, 60.0, 2401)
    closed = CC.confocal_axial_response(-60.0, 60.0, 2401, 575.0, na0)
    quad = CC.confocal_axial_response(-60.0, 60.0, 2401, 575.0, na0, longitudinal_sa_um=1e-9)
    e = float(np.max(np.abs(closed[:, 1] - quad[:, 1])))
    gate("軸応答: 瞳の数値積分(収差 1e-9 µm)= 閉形式 sinc²(u/2)(1e-9)", e < 1e-9, "最大 %.1e" % e)
    half = closed[closed[:, 1] >= 0.5, 0]
    fwhm_meas = float(half.max() - half.min())
    fwhm_cl = 0.4430 * 0.575 / (1.0 - math.sqrt(1.0 - na0 * na0))
    gate("鏡面の FWHM = 0.443 λ/(1 − cos α) = %.2f µm(数値 %.2f、格子 0.05 µm 以内)" % (fwhm_cl, fwhm_meas),
         abs(fwhm_meas - fwhm_cl) < 0.1)
    scal = []
    for na in (0.1, 0.2, 0.3):
        for lam in (450.0, 700.0):
            scal.append(CC._fwhm_closed(lam * 1e-3, na) / (lam * 1e-3 / na ** 2))
    NUMBERS["fwhm_per_lambda_na2"] = float(np.mean(scal))
    gate("分解能 ∝ λ/NA²: FWHM/(λ/NA²) は NA 0.1〜0.3・450/700 nm で %.3f〜%.3f(近軸 0.886 から 3 %% 以内)"
         % (min(scal), max(scal)), max(abs(s / 0.886 - 1) for s in scal) < 0.03)
    # スプライン(較正表の補間)の誤差: 節の間の波長を処方から直接
    mids = 0.5 * (wl[1:] + wl[:-1])[::3]
    direct = []
    for w in mids:
        s = RT.with_wavelength(RT.lens_system(singlet(True), stop=0), w * 1e-3)
        direct.append(RT.paraxial_trace(s)["bfl"] * 1e3 - P["origin_mm"] * 1e3)
    interp = CC._probe_at(P, mids, "poc")["paraxial_um"]
    ie = float(np.max(np.abs(interp - np.array(direct))))
    NUMBERS["spline_err_um"] = ie
    gate("較正表の 3 次スプライン(%d 点)は節の間でも処方の直接計算と 0.01 µm 以内" % npts, ie < 0.01, "最大 %.1e µm" % ie)
    # 色球面収差
    lsa = np.array(P["lsa_um"])
    off = np.array(P["calibration_um"]) - np.array(P["paraxial_um"])
    NUMBERS.update({"lsa450": lsa[0], "lsa700": lsa[-1], "peak450": P["peak_response"][0],
                    "cal_off450": off[0], "fwhm450": P["fwhm_um"][0], "fwhm450_closed": P["fwhm_closed_um"][0]})
    lsa575 = float(CC._probe_at(P, [575.0], "poc")["lsa_um"][0])
    gate("★色球面収差: 575 nm で縦収差 %.3f µm、450 nm で %.1f µm・700 nm で %+.1f µm(非球面は 1 色でしか直らない)"
         % (lsa575, lsa[0], lsa[-1]), abs(lsa575) < 0.1 and lsa[0] < -20.0)
    gate("★450 nm の較正ピークは近軸焦点から %.1f µm(≈ 縦収差の半分 %.1f)、高さは無収差の %.2f、幅は %.1f → %.1f µm"
         % (off[0], lsa[0] / 2, P["peak_response"][0], P["fwhm_closed_um"][0], P["fwhm_um"][0]),
         abs(off[0] / (lsa[0] / 2) - 1.0) < 0.15 and P["peak_response"][0] < 0.9)
    Ps = CC.chromatic_confocal_probe(singlet(False), 0, 450.0, 700.0, npts)
    blow = Ps["fwhm_um"][i0] / P["fwhm_um"][i0]
    NUMBERS.update({"sphere_lsa575": Ps["lsa_um"][i0], "sphere_fwhm_ratio": blow})
    gate("球面の単レンズ(同じ f)は 575 nm の縦収差 %.0f µm、応答の幅が非球面の %.1f 倍(目盛が太る)"
         % (Ps["lsa_um"][i0], blow), blow > 3.0)
    H = CC.chromatic_confocal_probe(hyperchromat(), 0, 450.0, 700.0, npts)
    ef_s, ef_h = P["efl_mm"][i0], H["efl_mm"][i0]
    gain = (H["range_um"] / ef_h) / (P["range_um"] / ef_s)
    NUMBERS.update({"hyper_range_um": H["range_um"], "hyper_efl": ef_h, "hyper_gain": gain})
    gate("ハイパークロマート(フッ素クラウン負 + 重フリント正)は焦点距離あたりの範囲が単レンズの %.2f 倍(%.0f µm、f %.1f mm)"
         % (gain, H["range_um"], ef_h), gain > 1.5)
    return P, Ps, H


# --------------------------------------------------------------------------- #
# 2. 実測の流れ                                                                  #
# --------------------------------------------------------------------------- #
def _read(P, spec, mode="gaussian", **kw):
    pk = CC.chromatic_confocal_peaks(spec, mode=mode, max_peaks=1, **kw)
    return CC.chromatic_confocal_readout(pk, P)["heights_um"][0]


def recalibrate(P, mode="gaussian", step_um=10.0):
    """実機と同じ較正: 鏡を既知の位置へ動かしてピーク波長を読み、波長 → 位置の表を作り直す。"""
    zs = np.arange(15.0, P["range_um"] - 15.0, step_um)
    lam = []
    for z in zs:
        pk = CC.chromatic_confocal_peaks(CC.chromatic_confocal_spectrum(P, float(z)), mode=mode, max_peaks=1)
        lam.append(pk[0]["wavelength_nm"])
    lam = np.array(lam)
    w = np.array(P["wavelength_nm"])
    inside = (w >= lam[0]) & (w <= lam[-1])
    Q = dict(P)
    sp = CC._spline(lam, zs)
    cal = np.array(P["calibration_um"], dtype=np.float64)
    cal[inside] = sp(w[inside])
    Q["calibration_um"] = cal.tolist()
    Q["recalibrated_band_nm"] = [float(lam[0]), float(lam[-1])]
    return Q


def chapter_flow(P):
    print("\n2. 実測の流れ: 面の位置 → 戻りスペクトル → ピーク → 高さ")
    zs = np.linspace(40.0, P["range_um"] - 40.0, 9 if REDUCED else 31)
    bias = {}
    for mode in ("gaussian", "parabolic", "centroid", "peak"):
        bias[mode] = np.array([_read(P, CC.chromatic_confocal_spectrum(P, float(z)), mode) - z for z in zs])
    for m, b in bias.items():
        NUMBERS["bias_%s" % m] = float(np.max(np.abs(b)))
    gate("推定法の偏り(雑音なし、設計値の較正表): 放物線 %.3f / ガウス %.3f / 重心 %.3f / 最大ビン %.3f µm"
         % tuple(NUMBERS["bias_" + m] for m in ("parabolic", "gaussian", "centroid", "peak")),
         NUMBERS["bias_parabolic"] < 0.2 and NUMBERS["bias_peak"] > NUMBERS["bias_parabolic"])
    step = 40.0 if REDUCED else 10.0
    Q = recalibrate(P, "gaussian", step)
    Qp = recalibrate(P, "parabolic", step)
    zt = zs[(zs > 60.0) & (zs < P["range_um"] - 60.0)] + 3.7                         # 較正の格子と重ならない位置
    rb = np.array([_read(Q, CC.chromatic_confocal_spectrum(P, float(z))) - z for z in zt])
    rp = np.array([_read(Qp, CC.chromatic_confocal_spectrum(P, float(z)), "parabolic") - z for z in zt])
    NUMBERS["bias_recal"] = float(np.max(np.abs(rb)))
    NUMBERS["bias_recal_parabolic"] = float(np.max(np.abs(rp)))
    gate("★鏡を動かして読む較正(実機の手順)で、ガウスの偏りは %.3f → %.4f µm に消える(偏りが滑らか = 較正表が吸収できる)"
         % (NUMBERS["bias_gaussian"], NUMBERS["bias_recal"]), NUMBERS["bias_recal"] < 0.3 * NUMBERS["bias_gaussian"])
    gate("★放物線は較正し直しても %.3f µm 残る(ビンの刻み 0.5 nm ごとに振れる偏りは、滑らかな較正表では消せない)"
         % NUMBERS["bias_recal_parabolic"], NUMBERS["bias_recal_parabolic"] > 2.0 * NUMBERS["bias_recal"])
    reps = 60 if REDUCED else 200
    Qc = recalibrate(P, "centroid", step)
    sd = {}
    for mode, QQ in (("centroid", Qc), ("gaussian", Q)):
        for ph in (4000.0, 16000.0):
            rd = np.array([_read(QQ, CC.chromatic_confocal_spectrum(P, 600.0, photons_per_peak=ph, seed=s), mode) for s in range(reps)])
            sd[mode, ph] = (float(rd.std()), float(rd.mean() - 600.0))
    ratio = sd["centroid", 4000.0][0] / sd["centroid", 16000.0][0]
    fw_mid = P["fwhm_um"][len(P["fwhm_um"]) // 2]
    worse = sd["gaussian", 16000.0][0] / sd["centroid", 16000.0][0]
    NUMBERS.update({"repeat_centroid_4000": sd["centroid", 4000.0][0], "repeat_centroid_16000": sd["centroid", 16000.0][0],
                    "repeat_gaussian_16000": sd["gaussian", 16000.0][0], "repeat_ratio": ratio, "gauss_over_centroid": worse})
    gate("ショット雑音の再現性(重心): ピーク 4000 光子で σ %.3f µm、16000 光子で %.3f µm(比 %.2f ≈ √4 = 2、FWHM %.1f µm の 1/%.0f)"
         % (sd["centroid", 4000.0][0], sd["centroid", 16000.0][0], ratio, fw_mid, fw_mid / sd["centroid", 16000.0][0]),
         abs(ratio / 2.0 - 1.0) < 0.2)
    gate("★雑音があると 3 点のガウスは重心の %.1f 倍ばらつく(雑音なしの偏りと順位が入れ替わる —— 白色干渉の module と同じ形)" % worse,
         worse > 2.0)
    gate("雑音で平均はずれない(重心・16000 光子、平均の誤差 %.3f µm < 4σ/√n)" % sd["centroid", 16000.0][1],
         abs(sd["centroid", 16000.0][1]) < 4.0 * sd["centroid", 16000.0][0] / math.sqrt(reps) + 0.01)
    # 段差と傾いた面の断面
    x = np.linspace(0.0, 2.0, 21 if REDUCED else 61)                                  # mm
    step = np.where(x < 1.0, 400.0, 450.0)
    tilt = 300.0 + 1000.0 * x * math.tan(math.radians(2.0))
    r_step = np.array([_read(Q, CC.chromatic_confocal_spectrum(P, float(z), photons_per_peak=4000.0, read_noise=5.0, seed=i)) for i, z in enumerate(step)])
    r_tilt = np.array([_read(Q, CC.chromatic_confocal_spectrum(P, float(z), tilt_deg=2.0, photons_per_peak=4000.0, read_noise=5.0, seed=100 + i))
                       for i, z in enumerate(tilt)])
    e_step = float(np.sqrt(np.mean((r_step - step) ** 2)))
    e_tilt = float(np.sqrt(np.mean((r_tilt - tilt) ** 2)))
    hstep = float(np.mean(r_step[x >= 1.0]) - np.mean(r_step[x < 1.0]))
    NUMBERS.update({"step_rms": e_step, "tilt_rms": e_tilt, "step_height": hstep})
    gate("50 µm の段差は %.3f µm と読める、断面の RMS 誤差 %.3f µm(雑音つき)" % (hstep, e_step), abs(hstep - 50.0) < 0.2 and e_step < 0.5)
    ftilt = float(CC._tilt_return(2.0, np.array([P["na"][len(P["na"]) // 2]]))[0])
    gate("2° 傾いた面: 戻る光は %.0f %% に減るが、RMS 誤差 %.3f µm(傾き 2° は NA の内側)" % (100 * ftilt, e_tilt), e_tilt < 0.6)
    return Q, bias, zs, (x, step, r_step, tilt, r_tilt)


# --------------------------------------------------------------------------- #
# 3. 透明な板                                                                    #
# --------------------------------------------------------------------------- #
def chapter_plate(P, Q):
    print("\n3. 透明な板: ホウケイ酸クラウンの表裏の 2 ピーク → 見かけの厚さ × n(λ)")
    rows = []
    for mat, t, label in ((CC.GLASS_CROWN, 500.0, "クラウン"), (CC.GLASS_CROWN, 200.0, "クラウン"),
                          ("SAPPHIRE", 300.0, "サファイア"), ("PMMA", 400.0, "PMMA")):
        spec = CC.chromatic_confocal_spectrum(P, 250.0, stack=((mat, t),), substrate=1.0)
        pk = CC.chromatic_confocal_peaks(spec, mode="parabolic")
        r = CC.chromatic_confocal_readout(pk, Q, mat)
        nd = MT.abbe_number(mat)["nd"]
        rows.append((mat, t, r, nd * r["apparent_thickness_um"]))
        print("   %-9s %5.0f µm: 見かけ %.2f、n(λ₂ %.1f nm) %.4f、近軸 %.3f、NA 補正 %.3f、n_d 使用 %.3f µm"
              % (label, t, r["apparent_thickness_um"], r["wavelengths_nm"][1], r["n_layer"], r["thickness_paraxial_um"], r["thickness_um"], nd * r["apparent_thickness_um"]))
    bk = rows[0]
    NUMBERS.update({"plate_paraxial_err": bk[2]["thickness_paraxial_um"] - 500.0, "plate_na_err": bk[2]["thickness_um"] - 500.0,
                    "plate_nd_err": bk[3] - 500.0})
    gate("★ホウケイ酸クラウン 500 µm: 近軸の補正 n·t' は %.2f µm ずれ(平板の球面収差)、NA の補正で %.3f µm" % (bk[2]["thickness_paraxial_um"] - 500.0, bk[2]["thickness_um"] - 500.0),
         abs(bk[2]["thickness_um"] - 500.0) < 0.25 * abs(bk[2]["thickness_paraxial_um"] - 500.0) and abs(bk[2]["thickness_um"] - 500.0) < 0.3)
    worst = max(abs(r["thickness_um"] - t) / t for _, t, r, _ in rows)
    gate("4 枚(ホウケイ酸クラウン 500/200・サファイア 300・PMMA 400 µm)の NA 補正の厚さは真値と 0.1 %% 以内(材料表の n(λ₂))", worst < 1e-3, "最大 %.2e" % worst)
    gate("カタログの n_d を使うとホウケイ酸クラウン 500 µm で %.2f µm ずれる(下の面の色 %.0f nm の n と n_d の差)"
         % (bk[3] - 500.0, bk[2]["wavelengths_nm"][1]), abs(bk[3] - 500.0) > 0.3)
    pf = MT.plate_focus_shift(CC.GLASS_CROWN, 0.5, bk[2]["wavelengths_nm"][1], bk[2]["na"])
    g = CC._plate_g(bk[2]["n_layer"], bk[2]["na"])
    gate("平板の縦球面収差 / 厚さ(chromconf)= materials.plate_focus_shift の式(1e-12)",
         abs(g * 0.5 - pf["spherical_aberration_mm"]) < 1e-12, "%.3e mm" % pf["spherical_aberration_mm"])
    return rows


# --------------------------------------------------------------------------- #
# 4. 失敗条件                                                                    #
# --------------------------------------------------------------------------- #
def chapter_failures(P, Q):
    print("\n4. 失敗条件: 傾き・粗さ・色のついた対象・薄すぎる膜・光源のむら")
    L = CC.chromatic_confocal_limits(Q, CC.GLASS_CROWN, 15.0, 61)
    na_mid = P["na"][len(P["na"]) // 2]
    rng = np.random.default_rng(20261015)
    nmc = 40000 if REDUCED else 400000
    r = na_mid * np.sqrt(rng.random(nmc))
    t = 2 * np.pi * rng.random(nmc)
    px, py = r * np.cos(t), r * np.sin(t)
    worst = 0.0
    for th in (1.0, 3.0, 5.0, 7.0, 8.5):
        d = math.sin(2 * math.radians(th))
        mc = float(np.mean((px + d) ** 2 + py ** 2 <= na_mid ** 2))
        worst = max(worst, abs(mc - float(CC._tilt_return(th, np.array([na_mid]))[0])))
    gate("(a) 傾き: 戻る光の割合(2 円の重なり)= 瞳の光線のモンテカルロ(%d 本、0.01 以内)" % nmc, worst < 0.01, "最大差 %.4f" % worst)
    NUMBERS["max_tilt_deg"] = L["max_tilt_deg"]
    na_red = P["na"][-1]
    lit = math.degrees(math.asin(na_red))
    gate("傾きの上限 %.2f°(瞳の重なり、赤 NA %.3f)は文献の「半頂角 = 傾き」asin NA = %.2f° と 2 %% 以内(Hillenbrand 2012)"
         % (L["max_tilt_deg"], na_red, lit), abs(L["max_tilt_deg"] / lit - 1.0) < 0.02)
    t_all = float(np.degrees(0.5 * np.arcsin(2.0 * max(P["na"]))))                     # 最も NA の大きい色(青)も戻らない傾き
    NUMBERS["max_tilt_deg_blue"] = t_all
    try:
        CC.chromatic_confocal_spectrum(P, 500.0, tilt_deg=t_all + 0.2)
        refused = False
    except ValueError:
        refused = True
    gate("鏡面が %.1f°(赤)〜%.1f°(青)を超えて傾くと何も戻らず、スペクトルの合成が「戻らない」と拒否する(黙って 0 を読まない)"
         % (L["max_tilt_deg"], t_all), refused)
    # (b) 粗さ
    sig = [0.0, 10.0, 20.0, 30.0, 40.0] if REDUCED else [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0, 60.0]
    z_r = 300.0
    rough = np.array([_read(Q, CC.chromatic_confocal_spectrum(P, z_r, roughness_nm=s)) - z_r for s in sig])
    rough = rough - rough[0]                                                              # 滑らかな面との差
    NUMBERS["rough_bias_max"] = float(rough.max())
    NUMBERS["rough_sigma_at_max"] = float(sig[int(np.argmax(rough))])
    smooth = CC.chromatic_confocal_spectrum(P, z_r)
    p0 = CC.chromatic_confocal_peaks(smooth, max_peaks=1)[0]["wavelength_nm"]
    p1 = CC.chromatic_confocal_peaks(CC.chromatic_confocal_spectrum(P, z_r, roughness_nm=30.0), max_peaks=1)[0]["wavelength_nm"]
    k = int(np.argmax(smooth[:, 1]))
    lnI = np.log(smooth[k - 1:k + 2, 1])
    curv = (lnI[2] - 2 * lnI[1] + lnI[0]) / (smooth[1, 0] - smooth[0, 0]) ** 2
    dlnT = 2.0 * (4.0 * math.pi * 30.0) ** 2 / p0 ** 3                                      # d ln TIS / dλ
    pred = -dlnT / curv
    NUMBERS.update({"rough_shift_nm": p1 - p0, "rough_shift_pred_nm": pred})
    gate("(b) 粗い面: 鏡面成分 exp(−(4πσ/λ)²) は短波長ほど減り、ピークを赤へ引く。σ 30 nm で %.4f nm、閉形式 −(d ln TIS/dλ)/(d² ln I/dλ²) = %.4f nm(30 %% 以内)"
         % (p1 - p0, pred), p1 > p0 and abs((p1 - p0) / pred - 1.0) < 0.3)
    gate("ただし応答が鋭い(FWHM 数 nm)ので偏りは小さい: σ 0〜%.0f nm で最大 %.3f µm(戻る光は σ 40 nm の青で 3 割に減る)"
         % (sig[-1], rough.max()), 0.0 < rough.max() < 0.5)
    # (c) 金とアルミ: 反射率の傾きがピークを引く。閉形式 δλ ≈ −(R'/R)/(d² ln I/dλ²)
    rows = []
    zs = np.linspace(80.0, 700.0, 4 if REDUCED else 9)
    for z in zs:
        flat = CC.chromatic_confocal_spectrum(P, float(z), substrate="AL")
        gold = CC.chromatic_confocal_spectrum(P, float(z), substrate="AU")
        pa = CC.chromatic_confocal_peaks(flat, mode="parabolic", max_peaks=1)[0]
        pg = CC.chromatic_confocal_peaks(gold, mode="parabolic", max_peaks=1)[0]
        lam = flat[:, 0]
        lnI = np.log(np.maximum(flat[:, 1], 1e-300))
        k = int(np.argmax(flat[:, 1]))
        h = lam[1] - lam[0]
        curv = (lnI[k + 1] - 2 * lnI[k] + lnI[k - 1]) / h ** 2
        Ra = MT.material_reflectance("AL", lam[k] - 2.0, lam[k] + 2.0, 3)
        Rg = MT.material_reflectance("AU", lam[k] - 2.0, lam[k] + 2.0, 3)
        slope = (math.log(Rg[2, 1]) - math.log(Rg[0, 1])) / 4.0 - (math.log(Ra[2, 1]) - math.log(Ra[0, 1])) / 4.0
        pred = -slope / curv
        rows.append((float(z), pa["wavelength_nm"], pg["wavelength_nm"] - pa["wavelength_nm"], pred,
                     CC.chromatic_confocal_readout([pg["wavelength_nm"]], Q)["heights_um"][0] - CC.chromatic_confocal_readout([pa["wavelength_nm"]], Q)["heights_um"][0]))
    shifts = np.array([r_[2] for r_ in rows])
    preds = np.array([r_[3] for r_ in rows])
    dz = np.array([r_[4] for r_ in rows])
    NUMBERS.update({"gold_dz_max": float(dz.max()), "gold_dz_at": float(rows[int(np.argmax(dz))][1])})
    rel = float(np.max(np.abs(shifts - preds) / np.maximum(np.abs(preds), 1e-6)))
    gate("(c) 金の面は読みが遠い側へ最大 %.2f µm(%.0f nm 付近、反射率が急に立ち上がる色)、アルミとの差 = 傾き/曲率の閉形式(相対 25 %% 以内)"
         % (dz.max(), NUMBERS["gold_dz_at"]), dz.max() > 0.1 and rel < 0.25, "最大の相対差 %.2f" % rel)
    gr = MT.material_reflectance("AU", 450.0, 700.0, 501)
    z_g = rows[int(np.argmax(dz))][0]
    raw = CC.chromatic_confocal_spectrum(P, z_g, substrate="AU")
    corr = _read(Q, raw, reference=gr) - z_g
    NUMBERS["gold_corrected"] = corr
    gate("金だと分かっていれば、材料表の金の反射率で割ると偏りが %.3f µm に戻る" % corr, abs(corr) < 0.25 * dz.max())
    # (d) 薄すぎる膜
    ts = np.arange(10.0, 61.0, 5.0 if REDUCED else 1.0)
    two = []
    for t_ in ts:
        pk = CC.chromatic_confocal_peaks(CC.chromatic_confocal_spectrum(Q, 500.0, stack=((CC.GLASS_CROWN, float(t_)),), substrate=1.0), mode="parabolic")
        two.append(len(pk) == 2)
    two = np.array(two)
    t_min = float(ts[np.argmax(two)]) if two.any() else float("nan")
    NUMBERS.update({"film_min_measured": t_min, "film_min_sparrow": L["min_thickness_um"]})
    gate("(d) 薄い膜: 2 ピークに分かれる最小の厚さ %.0f µm、Sparrow の閉形式 %.1f µm(1.0〜1.5 倍 —— 谷の深さの基準の分だけ厚い)"
         % (t_min, L["min_thickness_um"]), two.any() and 1.0 <= t_min / L["min_thickness_um"] <= 1.5 and bool(np.all(two[ts >= t_min])))
    thin = CC.chromatic_confocal_peaks(CC.chromatic_confocal_spectrum(Q, 500.0, stack=((CC.GLASS_CROWN, 0.6 * L["min_thickness_um"]),), substrate=1.0))
    try:
        CC.chromatic_confocal_readout(thin, Q, CC.GLASS_CROWN)
        refused = False
    except ValueError:
        refused = True
    gate("それより薄い膜(%.0f µm)は 1 ピークに潰れ、readout は厚さを当て推量せず拒否する" % (0.6 * L["min_thickness_um"]), refused and len(thin) == 1)
    # (e) 光源のむら: 白色 LED = 青い LED + 蛍光体
    lo, hi = 440.0, 710.0
    blue = SR.led_spectrum(450.0, 20.0, lo, hi, 541)
    phos = SR.led_spectrum(560.0, 110.0, lo, hi, 541)
    white = blue.copy()
    white[:, 1] = blue[:, 1] / blue[:, 1].max() + 0.6 * phos[:, 1] / phos[:, 1].max()
    zw = [float(z) for z in np.linspace(60.0, 1100.0, 4 if REDUCED else 12)]
    raw_e = np.array([_read(Q, CC.chromatic_confocal_spectrum(P, z, source=white)) - z for z in zw])
    cor_e = np.array([_read(Q, CC.chromatic_confocal_spectrum(P, z, source=white), reference=white) - z for z in zw])
    NUMBERS.update({"led_raw_max": float(np.max(np.abs(raw_e))), "led_cor_max": float(np.max(np.abs(cor_e)))})
    gate("(e) 白色 LED のむらは読みを最大 %.2f µm 引き、白色参照で割ると %.3f µm(10 倍以上の改善)"
         % (NUMBERS["led_raw_max"], NUMBERS["led_cor_max"]), NUMBERS["led_cor_max"] * 10 < NUMBERS["led_raw_max"])
    return L, (sig, rough), rows, (ts, two), (white, zw, raw_e, cor_e)


# --------------------------------------------------------------------------- #
# 6. 実画像: 公開論文の図(CC BY 4.0)から標準溝の深さを読む                        #
# --------------------------------------------------------------------------- #
#: 実画像の出典(CC BY 4.0)。図はダウンロードして ``FULLSEYE_CCF_REAL_DIR`` に置く(repo には同梱しない)。
REAL_SOURCE = ("Qin M. ほか, \"A Kernel-Based Calibration Algorithm for Chromatic Confocal Line Sensors\", "
               "Sensors 24(20):6649, 2024, DOI 10.3390/s24206649, CC BY 4.0")
REAL_FILES = {"spectral_image": "sensors-24-06649-g003a.jpg", "groove_fit": "sensors-24-06649-g006b.jpg"}
REAL_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC11510888/"
GROOVE_REF_UM = 66.14            # 論文の標準溝の基準深さ(真値)
GROOVE_PAPER_UM = 66.244         # 論文の図 6(b) の凡例に書かれた、論文自身の当てはめの深さ


def _real_dir():
    d = os.environ.get("FULLSEYE_CCF_REAL_DIR", "").strip()
    if not d:
        return None
    if not all(os.path.isfile(os.path.join(d, f)) for f in REAL_FILES.values()):
        print("   FULLSEYE_CCF_REAL_DIR=%s に図が揃っていない(%s)" % (d, ", ".join(REAL_FILES.values())))
        return None
    return d


def _read_gray(path):
    from PIL import Image
    with Image.open(path) as im:                       # 外から来た画像: 復号するだけで、中身は数として扱う
        return np.asarray(im.convert("L"), dtype=np.float64), np.asarray(im.convert("RGB"), dtype=np.float64)


def chapter_real():
    print("\n6. 実画像: 公開論文の図(CC BY 4.0)から標準溝の深さを読み、基準値 %.2f µm と突き合わせる" % GROOVE_REF_UM)
    d = _real_dir()
    if d is None:
        print("   (飛ばした)実画像の段は FULLSEYE_CCF_REAL_DIR に %s の図 3(a)・図 6(b) を置いたときだけ走る。"
              "入手先 %s(図だけが CC BY で公開、生データは非公開)。" % (REAL_SOURCE, REAL_URL))
        return None
    print("   出典: " + REAL_SOURCE)
    # (A) 図 3(a): ライン共焦点の生の分光画像。縦が分光器の画素(色)、横が線上の位置。各列を 1 本の
    #     スペクトルとみなして chromatic_confocal_peaks でピークの行を読む。
    a, _ = _read_gray(os.path.join(d, REAL_FILES["spectral_image"]))
    r0, r1 = 200, 300                                    # 輝線のある帯(下の淡い迷光の帯 ≈ 300 行目は外す)
    rows = np.arange(r0, r1, dtype=np.float64)
    cols = np.arange(10, a.shape[1] - 10)
    peak = {}
    for mode in ("centroid", "gaussian", "peak"):
        v = []
        for c in cols:
            sp = np.column_stack([rows, a[r0:r1, c]])
            v.append(CC.chromatic_confocal_peaks(sp, mode=mode, max_peaks=1, min_prominence=0.3)[0]["wavelength_nm"])
        peak[mode] = np.array(v)
    pc = peak["centroid"]
    low = pc > 0.5 * (pc.min() + pc.max())
    gcols = cols[low]
    frac3 = float((gcols.max() - gcols.min()) / (cols.max() - cols.min()))
    step = {m: float(np.median(v[low]) - np.median(v[~low])) for m, v in peak.items()}
    sig_top = float(np.std(pc[~low]))
    NUMBERS.update({"real_step_px": step["centroid"], "real_step_px_gauss": step["gaussian"], "real_top_sigma_px": sig_top,
                    "real_groove_frac_fig3": frac3})
    gate("(A) 図 3(a) の分光画像を列ごとのスペクトルとして読むと、溝の底の輝線は上面より %.1f 画素(重心)/ %.1f 画素(ガウス)ずれる"
         "(図の画素。分光器の画素との比が書かれていないので µm にはできない)" % (step["centroid"], step["gaussian"]),
         3.0 < step["centroid"] < 6.0 and abs(step["gaussian"] - step["centroid"]) < 1.0,
         "上面の読みのばらつき %.2f 画素 —— 図は縮小・JPEG で、輝線の幅が 1〜2 画素しかない" % sig_top)
    # (B) 図 6(b): 論文の高さの断面(縦軸 z [µm])。目盛の画素から z の換算を当て、上面(青の三角)と
    #     溝の底(赤の三角)の印の中心を fs.fit_line で直線に当てて、深さを読む。
    g, rgb = _read_gray(os.path.join(d, REAL_FILES["groove_fit"]))
    prof = 255.0 - g[20:260, 60:65].mean(axis=1)        # 縦軸の左の目盛線(-490 〜 -550 µm、10 µm 刻み)
    idx = np.where(prof > 40.0)[0]
    groups = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)
    tick = np.array([20.0 + float((c * prof[c]).sum() / prof[c].sum()) for c in groups])
    val = -490.0 - 10.0 * np.arange(tick.size)
    A = np.column_stack([np.ones_like(tick), tick])
    coef = np.linalg.lstsq(A, val, rcond=None)[0]
    tick_res = float(np.max(np.abs(val - A @ coef)))
    um_per_px = float(-coef[1])
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    area = np.zeros(g.shape, bool)
    area[26:249, 68:703] = True                          # 上の段のグラフの枠の内側
    area[95:170, 68:330] = False                         # 凡例の箱(印の見本)を除く
    blue = (B > 150) & (R < 110) & (G < 110) & area
    red = (R > 150) & (G < 110) & (B < 110) & area

    def centres(m):                                      # 列ごとに印の上端と下端の中点(三角の印は外接枠の中心がデータ点)
        out = []
        for c in np.where(m.any(axis=0))[0]:
            rr = np.where(m[:, c])[0]
            out.append((0.5 * (rr.min() + rr.max()), float(c)))
        return np.array(out)

    U, Lw = centres(blue), centres(red)
    fu, fl = fs.fit_line(U), fs.fit_line(Lw)
    upper_at = lambda c: fu["cy"] + (c - fu["cx"]) * fu["dy"] / fu["dx"]      # noqa: E731
    depth_px = float(np.mean(Lw[:, 0] - upper_at(Lw[:, 1])))
    depth = depth_px * um_per_px
    frac6 = float((Lw[:, 1].max() - Lw[:, 1].min()) / (U[:, 1].max() - U[:, 1].min()))
    read_err = 0.5 * um_per_px                           # 印の中心の読みの目安(半画素)
    NUMBERS.update({"real_depth_um": depth, "real_um_per_px": um_per_px, "real_tick_res_um": tick_res,
                    "real_depth_vs_ref": depth - GROOVE_REF_UM, "real_depth_vs_paper": depth - GROOVE_PAPER_UM,
                    "real_groove_frac_fig6": frac6})
    gate("(B) 図 6(b) の目盛 7 本から 1 画素 = %.4f µm(当てはめの残差 最大 %.3f µm)" % (um_per_px, tick_res), tick_res < 0.15)
    gate("★図 6(b) の印から読んだ溝の深さ %.3f µm、論文の当てはめ %.3f µm と %+.3f µm(図の読みの目安 ±%.2f µm 以内)"
         % (depth, GROOVE_PAPER_UM, depth - GROOVE_PAPER_UM, 2 * read_err), abs(depth - GROOVE_PAPER_UM) < 2 * read_err)
    gate("★基準深さ %.2f µm との差 %+.3f µm(論文の表 1 の誤差の幅 −0.80〜+0.49 µm の内側)"
         % (GROOVE_REF_UM, depth - GROOVE_REF_UM), -0.80 <= depth - GROOVE_REF_UM <= 0.49)
    gate("上面と溝の底の直線の傾きの差 %.3f°(平行な溝として読めている)" % abs(fu["angle_deg"] - fl["angle_deg"]),
         abs(fu["angle_deg"] - fl["angle_deg"]) < 0.5)
    gate("溝の幅 / 走査の幅: 図 3(a) %.3f と図 6(b) %.3f が 0.01 以内(同じ走査の 2 つの図として整合)" % (frac3, frac6),
         abs(frac3 - frac6) < 0.01)
    return {"a": a, "rows": (r0, r1), "cols": cols, "peak": pc, "low": low, "rgb": rgb, "U": U, "L": Lw,
            "fu": fu, "depth": depth}


# --------------------------------------------------------------------------- #
# 図                                                                             #
# --------------------------------------------------------------------------- #
def wl_rgb(nm):
    """波長 → 表示用の sRGB(CIE 1931 等色関数 → 線形 sRGB → 最大成分で正規化 → ガンマ)。"""
    import matappear
    xyz = np.atleast_2d(matappear.cie_xyz_from_wavelength(np.atleast_1d(np.asarray(nm, float))))
    M = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
    rgb = np.clip(xyz @ M.T, 0.0, None)
    rgb = rgb / np.maximum(rgb.max(axis=1, keepdims=True), 1e-12)
    return np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)


def _line(img, p0, p1, rgb, width=1.6):
    """反エイリアスの線分(線分上を細かく刻み、幅つきで画素に塗り重ねる)。"""
    h, w, _ = img.shape
    L = max(2, int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * 3))
    t = np.linspace(0.0, 1.0, L)
    xs = p0[0] + (p1[0] - p0[0]) * t
    ys = p0[1] + (p1[1] - p0[1]) * t
    cov = np.zeros((h, w))
    r = int(math.ceil(width))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            xi = np.round(xs).astype(int) + dx
            yi = np.round(ys).astype(int) + dy
            d = np.hypot(xi - xs, yi - ys)
            wgt = np.clip(width / 2 + 0.5 - d, 0.0, 1.0)
            ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
            np.maximum.at(cov, (yi[ok], xi[ok]), wgt[ok])
    img[:] = img * (1.0 - cov[..., None]) + np.asarray(rgb)[None, None, :] * cov[..., None]


def ray_figure(surfaces, P, zoom, size=(900, 420), title=""):
    """光線図: 6 色 × 縁と中間の光線。zoom=None は全体、(z0, z1, ymax) は焦点付近の拡大 [mm]。"""
    W, Hh = size
    img = np.ones((Hh, W, 3))
    base = RT.lens_system(surfaces, stop=0)
    zl = sum(s["t"] for s in base["surfaces"][:-1])
    wls = np.linspace(450.0, 700.0, 11 if zoom else 6)
    z0, z1, ym = zoom if zoom else (-3.0, P["origin_mm"] + zl + P["range_um"] * 1e-3 + 1.0, BEAM * 1.25)
    sx = (W - 40) / (z1 - z0)
    sy = (Hh / 2 - 30) / ym
    X = lambda z: 20 + (z - z0) * sx        # noqa: E731
    Y = lambda y: Hh / 2 - y * sy           # noqa: E731
    _line(img, (X(z0), Y(0)), (X(z1), Y(0)), (0.6, 0.6, 0.6), 1.0)
    if not zoom:                             # レンズの輪郭
        n = RT.refractive_index(surfaces[0]["n"], LAM0)
        k = surfaces[-1].get("k", 0.0)
        R = surfaces[-1]["R"]
        ys = np.linspace(-BEAM * 1.1, BEAM * 1.1, 60)
        c = 1.0 / R
        sag = c * ys ** 2 / (1 + np.sqrt(1 - (1 + k) * c * c * ys ** 2))
        pts = [(X(4.0 + s), Y(y)) for s, y in zip(sag, ys)]
        for a, b in zip(pts, pts[1:]):
            _line(img, a, b, (0.2, 0.2, 0.3), 1.6)
        _line(img, (X(0), Y(-BEAM * 1.1)), (X(0), Y(BEAM * 1.1)), (0.2, 0.2, 0.3), 1.6)
        _line(img, pts[0], (X(0), Y(-BEAM * 1.1)), (0.2, 0.2, 0.3), 1.6)
        _line(img, pts[-1], (X(0), Y(BEAM * 1.1)), (0.2, 0.2, 0.3), 1.6)
        del n
    cols = wl_rgb(wls)
    for wl, col in zip(wls, cols):
        sw = RT.with_wavelength(base, wl * 1e-3)
        for hfrac in (-1.0, -0.6, 0.6, 1.0):
            r = RT.trace_rays(sw, [[0.0, BEAM * hfrac, -3.0]], [[0.0, 0.0, 1.0]], image_mm=50.0)
            pts = r["points"][0]
            D = r["dirs"][0, -1]
            seq = [(p[2], p[1]) for p in pts[:-1]]
            Pz, Py = pts[-2][2], pts[-2][1]
            tz = (z1 - Pz) / D[2]
            seq.append((z1, Py + D[1] * tz))
            for (a, b), (c_, d) in zip(seq, seq[1:]):
                _line(img, (X(a), Y(b)), (X(c_), Y(d)), col * 0.92, 1.4 if zoom else 1.1)
    img = np.clip(img, 0.0, 1.0)
    if title:
        img = np.asarray(fs.text_box(img, title, (8, 6), anchor="lt", font_size=13))
    return img, X, Y


def real_figure(real):
    """実画像の段の図: 図 3(a) の輝線に読んだピークの行を、図 6(b) に読んだ印の中心と当てた直線を重ねる。"""
    a = real["a"]
    r0, r1 = real["rows"]
    crop = np.repeat(a[r0:r1] / 255.0, 3, axis=0)       # 縦を 3 倍(行の差を見えるように)
    img = np.repeat(np.clip(crop, 0, 1)[..., None], 3, axis=2)
    for c, pr in zip(real["cols"], real["peak"]):
        y = int(round((pr - r0) * 3 + 1))
        if 0 <= y < img.shape[0]:
            img[y, int(c)] = (1.0, 0.25, 0.1) if pr > 0.5 * (real["peak"].min() + real["peak"].max()) else (0.2, 0.7, 1.0)
    img = np.asarray(fs.text_box(img, "図 3(a) の分光画像(縦 3 倍)に、列ごとに読んだピークの行", (6, 6), anchor="lt", font_size=12))
    rgb = real["rgb"] / 255.0
    out = rgb.copy()
    fu = real["fu"]
    for c in range(68, 703):
        y = fu["cy"] + (c - fu["cx"]) * fu["dy"] / fu["dx"]
        out[int(round(y)), c] = (0.0, 0.6, 0.0)
        y2 = y + (real["L"][:, 0].mean() - (fu["cy"] + (real["L"][:, 1].mean() - fu["cx"]) * fu["dy"] / fu["dx"]))
        out[int(round(y2)), c] = (0.0, 0.6, 0.0)
    for (yy, xx) in np.vstack([real["U"], real["L"]]):
        out[int(round(yy)), int(xx)] = (1.0, 0.85, 0.0)
    out = np.asarray(fs.text_box(out, "図 6(b) に読んだ印の中心(黄)と直線(緑): 深さ %.3f µm" % real["depth"], (80, 300), anchor="lt", font_size=12))
    w = max(img.shape[1], out.shape[1])
    pad = lambda m: np.pad(m, ((0, 0), (0, w - m.shape[1]), (0, 0)), constant_values=1.0)      # noqa: E731
    figs.save("real_groove_from_paper_figures", np.concatenate([pad(img), pad(out)], axis=0),
              caption="出典: %s。図 3(a)・図 6(b) に読み取りの点と直線を重ねた(改変)。上: 生の分光画像を列ごとのスペクトルとして読み、溝の底の輝線が %.1f 画素ずれることを読む(図の画素で、µm への換算は書かれていない)。下: 高さの断面の印から深さ %.3f µm を読み、論文の当てはめ %.3f µm・基準 %.2f µm と比べた。図の画素から読む限界(1 画素 = %.2f µm、縮小と JPEG)を含む。" % (REAL_SOURCE, NUMBERS["real_step_px"], real["depth"], GROOVE_PAPER_UM, GROOVE_REF_UM, NUMBERS["real_um_per_px"]))


def make_figures(P, Ps, H, flow, plate, fails, real=None):
    Q, bias, zs, prof = flow
    L, rough, gold, film, led = fails
    base = RT.lens_system(singlet(True), stop=0)
    zl = sum(s["t"] for s in base["surfaces"][:-1])
    zf0 = P["origin_mm"] + zl                         # 450 nm の較正ピーク(第 1 面から)[mm]
    zoom_win = (zf0 - 0.15, zf0 + P["range_um"] * 1e-3 + 0.15, 0.06)
    full, _, _ = ray_figure(singlet(True), P, None, title="重フリントの非球面単レンズ: 白色光の焦点が色ごとに並ぶ")
    zoom, X, Y = ray_figure(singlet(True), P, zoom_win,
                            title="焦点付近を拡大(縦 ±60 µm、横 %.2f mm)= 虹のものさし" % (P["range_um"] * 1e-3 + 0.3))
    for wl, zc in zip(P["wavelength_nm"][::5], P["calibration_um"][::5]):
        x = X(zf0 + zc * 1e-3)
        zoom = np.asarray(fs.text_box(zoom, "%.0f nm\n%.0f µm" % (wl, zc), (int(x), 400), anchor="cb", font_size=10))
    figs.save("rainbow_ruler", np.concatenate([full, zoom], axis=0),
              caption="上: f = 16 mm の重フリント非球面単レンズに平行な白色光(半径 2.5 mm)を入れ、11 色の光線を実光線追跡した。下: 焦点付近の拡大(縦 ±60 µm を横の %.0f 倍に引き伸ばしてある)。450 nm から 700 nm の焦点が光軸上に %.0f µm にわたって並ぶ —— これが目盛。目盛の数字は較正(鏡を置いて応答のピークを読む)の位置。青の光線が 1 点に集まらないのは色球面収差(非球面は 575 nm でしか球面収差を消さない)。" % (((420 / 2 - 30) / zoom_win[2]) / ((900 - 40) / (zoom_win[1] - zoom_win[0])), P["range_um"]))
    wl = np.array(P["wavelength_nm"])
    n0 = RT.refractive_index(CC.GLASS_DENSE_FLINT, LAM0)
    closed = np.array([((n0 - 1.0) * F0 / (_n(CC.GLASS_DENSE_FLINT, w) - 1.0) - P["origin_mm"]) * 1e3 for w in wl])
    left = figs.render_plot([("較正(鏡のピーク)", wl, np.array(P["calibration_um"])),
                             ("閉形式 f₀(n₀−1)/(n(λ)−1)", wl, closed),
                             ("ハイパークロマート(較正)", np.array(H["wavelength_nm"]), np.array(H["calibration_um"]))],
                            xlabel="波長 [nm]", ylabel="焦点の位置 [µm]", colors=["emphasis", "reference", "right"],
                            kinds=["line", "scatter", "line"], title="波長 → 焦点の位置(目盛)", size=(520, 360))
    right = figs.render_plot([("較正 − 近軸焦点", wl, np.array(P["calibration_um"]) - np.array(P["paraxial_um"])),
                              ("縦球面収差の半分", wl, 0.5 * np.array(P["lsa_um"]))],
                             xlabel="波長 [nm]", ylabel="[µm]", colors=["emphasis", "reference"], styles=[None, "dashed"],
                             title="色球面収差が目盛をずらす", size=(520, 360))
    figs.save("calibration_curve", np.concatenate([left, right], axis=1),
              caption="左: 単レンズの範囲 %.0f µm、ハイパークロマート %.0f µm(焦点距離あたり %.2f 倍)。近軸焦点は閉形式と %.0e µm で一致(点)。右: 鏡で較正したピークは近軸焦点から縦球面収差のほぼ半分だけずれる —— 450 nm で %.1f µm。575 nm では 0(非球面で消した色)。" % (P["range_um"], H["range_um"], NUMBERS["hyper_gain"], NUMBERS["focus_closed_err_um"], NUMBERS["cal_off450"]))
    figs.save_plot("axial_response",
                   [("非球面 575 nm(閉形式)", *CC.confocal_axial_response(-80, 80, 801, 575.0, P["na"][len(wl) // 2]).T),
                    ("非球面 450 nm(色球面収差 %.0f µm)" % P["lsa_um"][0], *CC.confocal_axial_response(-80, 80, 801, 450.0, P["na"][0], longitudinal_sa_um=P["lsa_um"][0]).T),
                    ("球面の単レンズ 575 nm", *CC.confocal_axial_response(-80, 80, 801, 575.0, Ps["na"][len(wl) // 2], longitudinal_sa_um=Ps["lsa_um"][len(wl) // 2]).T)],
                   xlabel="鏡の位置 − 近軸焦点 [µm]", ylabel="ピンホールを通る光(無収差のピーク = 1)",
                   colors=["emphasis", "wrong", "neutral"], title="共焦点の軸応答 = 目盛 1 本の太さ",
                   caption="鏡面の応答は sinc²(u/2)、FWHM = 0.443 λ/(1 − cos α)(∝ λ/NA²)。450 nm は縦収差で低く広く、ピークは手前へ縦収差の約半分ずれる(較正が吸収する)。同じ焦点距離の球面の単レンズは縦収差 %.0f µm で応答が崩れ(幅 %.0f 倍)、目盛として使えない。" % (Ps["lsa_um"][len(wl) // 2], NUMBERS["sphere_fwhm_ratio"]))
    # GIF: 面(灰色の縦線)を遠ざけると、ピントの合う色が変わり、戻るスペクトルが動く
    top0, Xs, _ = ray_figure(singlet(True), P, zoom_win, size=(560, 220), title="")
    frames = []
    nfr = 30
    W, Hs = 560, 230
    for i, z in enumerate(np.linspace(20.0, P["range_um"] - 20.0, nfr)):
        sp = CC.chromatic_confocal_spectrum(P, float(z), photons_per_peak=3000.0, read_noise=4.0, seed=i)
        lam_axis = sp[:, 0]
        top = top0.copy()
        xz = int(round(Xs(zf0 + z * 1e-3)))
        top[:, max(0, xz - 2):xz + 2] = 0.35
        top = np.asarray(fs.text_box(top, "面(灰色の線)の位置 %.1f µm" % z, (8, 6), anchor="lt", font_size=13))
        img = np.ones((Hs, W, 3)) * 0.08
        cols = wl_rgb(lam_axis)
        xs = (np.arange(lam_axis.size) / (lam_axis.size - 1) * (W - 40) + 20).astype(int)
        hh = np.clip(sp[:, 1] / 3600.0, 0.0, 1.0)
        for x_, h_, c in zip(xs, hh, cols):
            t_ = int(Hs - 34 - h_ * (Hs - 80))
            img[t_:Hs - 34, x_:x_ + 2] = c
        pk = CC.chromatic_confocal_peaks(sp, mode="centroid", max_peaks=1)
        zr = CC.chromatic_confocal_readout(pk, flow[0])["heights_um"][0]
        img = np.asarray(fs.text_box(img, "戻りスペクトル: ピーク %.2f nm → 読み %.2f µm(真値 %.2f)" % (pk[0]["wavelength_nm"], zr, z), (8, 6), anchor="lt", font_size=13))
        for t_ in (450, 500, 550, 600, 650, 700):
            x_ = int(20 + (t_ - lam_axis[0]) / (lam_axis[-1] - lam_axis[0]) * (W - 40))
            img = np.asarray(fs.text_box(img, "%d nm" % t_ if t_ == 700 else "%d" % t_, (min(x_, W - 4), Hs - 4), anchor="cb" if t_ < 700 else "rb", font_size=11))
        frames.append(np.clip(np.concatenate([top, img], axis=0), 0, 1))
    figs.save_gif("spectrum_vs_height", frames, fps=5.0,
                  caption="上: 虹のものさし(焦点付近の光線)と面(灰色の縦線)。下: ピンホールへ戻るスペクトル(棒の色はその波長の色、ピーク 3000 光子 + 読出し雑音)。面を遠ざけると、ピントの合う色が青から赤へ移り、戻る色が変わる。ピーク波長を較正表で引くと高さになる。")
    x, step, r_step, tilt, r_tilt = prof
    figs.save_plot("step_and_tilt",
                   [("段差の真値", x, step), ("段差の読み", x, r_step), ("2° 傾いた面の真値", x, tilt), ("傾いた面の読み", x, r_tilt)],
                   xlabel="横の位置 [mm]", ylabel="面の位置 [µm]", styles=["dashed", None, "dashed", None],
                   colors=["reference", "emphasis", "reference", "right"], kinds=["line", "scatter", "line", "scatter"],
                   title="段差 50 µm と 2° の傾き(雑音つき)",
                   caption="段差は %.3f µm と読める(RMS 誤差 %.3f µm)。2° 傾くと戻る光は約 7 割に減るが読みは保たれる(RMS %.3f µm)。" % (NUMBERS["step_height"], NUMBERS["step_rms"], NUMBERS["tilt_rms"]))
    sp = CC.chromatic_confocal_spectrum(P, 250.0, stack=((CC.GLASS_CROWN, 500.0),), substrate=1.0)
    bk = plate[0][2]
    pl = figs.render_plot([("ホウケイ酸クラウン 500 µm の板", sp[:, 0], sp[:, 1])], xlabel="波長 [nm]", ylabel="戻りスペクトル(最大 = 1)",
                          colors=["emphasis"], title="板: 表 %.1f nm・裏 %.1f nm の 2 本" % tuple(bk["wavelengths_nm"]), size=(520, 360))
    pl = np.asarray(fs.text_box(pl, "見かけ %.2f µm × n %.4f\n近軸 %.2f / NA 補正 %.2f µm(真値 500)"
                                % (bk["apparent_thickness_um"], bk["n_layer"], bk["thickness_paraxial_um"], bk["thickness_um"]), (505, 60), anchor="rt", font_size=12))
    cal = CC._spline(np.array(Q["wavelength_nm"]), Q["calibration_um"]).derivative()
    gz = np.array([g_[0] for g_ in gold])
    gm = np.array([g_[4] for g_ in gold])
    gp = np.array([g_[3] * float(cal(g_[1])) for g_ in gold])
    gl = np.array([g_[1] for g_ in gold])
    gd = figs.render_plot([("金 − アルミ(測った)", gl, gm), ("閉形式 −(R'/R)/(d²lnI/dλ²)", gl, gp)],
                          xlabel="ピークの波長 [nm]", ylabel="読みの偏り [µm]", colors=["wrong", "reference"],
                          kinds=["line", "scatter"], title="金: 反射率の立ち上がる色で読みが遠くなる", size=(520, 360))
    del gz
    figs.save("plate_and_gold", np.concatenate([pl, gd], axis=1),
              caption="左: 透明な板は表と裏の 2 ピーク。見かけの厚さ × n(λ₂)、NA の補正で誤差 %.3f µm(近軸のみ %.2f µm、カタログの n_d を使うと %.2f µm)。右: 金の反射率は 500〜550 nm で急に立ち上がり、ピークを赤へ引く。偏りは最大 %.2f µm で、反射率の傾き / 応答の曲率の閉形式(点)が予言する。材料表の金の反射率で割れば %.3f µm に戻る。" % (NUMBERS["plate_na_err"], NUMBERS["plate_paraxial_err"], NUMBERS["plate_nd_err"], NUMBERS["gold_dz_max"], NUMBERS["gold_corrected"]))
    tr = L["tilt_return"]
    sig, rb = rough
    ts, two = film
    white, zw, raw_e, cor_e = led
    panels = [
        figs.render_plot([("戻る光の割合", tr[:, 0], tr[:, 1])], xlabel="面の傾き [°]", ylabel="瞳へ戻る割合",
                         title="(a) 傾き: %.1f° で 0" % L["max_tilt_deg"], colors=["emphasis"], size=(460, 300)),
        figs.render_plot([("読みの偏り", np.array(sig), rb)], xlabel="粗さ σ [nm]", ylabel="偏り [µm]",
                         title="(b) 粗さ: 赤へ引かれる(小さい)", colors=["wrong"], kinds=["line"], size=(460, 300)),
        figs.render_plot([("2 ピークに分かれる", ts, two.astype(float)), ("Sparrow の閉形式", np.array([L["min_thickness_um"]] * 2), np.array([0.0, 1.0]))],
                         xlabel="ホウケイ酸クラウンの膜厚 [µm]", ylabel="1 = 分かれる", styles=[None, "dashed"], colors=["emphasis", "reference"],
                         title="(d) 薄い膜の限界", size=(460, 300)),
        figs.render_plot([("白色 LED のまま", np.array(zw), raw_e), ("白色参照で割る", np.array(zw), cor_e)],
                         xlabel="面の位置 [µm]", ylabel="読みの誤差 [µm]", colors=["wrong", "right"],
                         title="(e) 光源のむらと補正", size=(460, 300)),
    ]
    top = np.concatenate(panels[:2], axis=1)
    bot = np.concatenate(panels[2:], axis=1)
    figs.save("failure_modes", np.concatenate([top, bot], axis=0),
              caption="(a) 鏡面の傾きが %.1f°(sin 2θ = 2NA)を超えると何も戻らない(瞳の光線のモンテカルロと一致)。(b) 粗さは鏡面成分を短波長ほど減らし読みを遠くするが、応答が鋭いので σ 60 nm でも %.2f µm。(d) %.0f µm より薄いホウケイ酸クラウンの膜は 2 ピークに分かれない(Sparrow の閉形式 %.1f µm、干渉は入れていない)。(e) 白色 LED(青 + 蛍光体)のむらは最大 %.2f µm の偏り、白色参照で割ると %.3f µm。" % (L["max_tilt_deg"], NUMBERS["rough_bias_max"], NUMBERS["film_min_measured"], L["min_thickness_um"], NUMBERS["led_raw_max"], NUMBERS["led_cor_max"]))


def main():
    t0 = time.time()
    print("PoC クロマティック共焦点変位センサ(予算 %s)" % ("reduced" if REDUCED else "full"))
    P, Ps, H = chapter_ruler()
    flow = chapter_flow(P)
    plate = chapter_plate(P, flow[0])
    fails = chapter_failures(P, flow[0])
    real = chapter_real()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(P, Ps, H, flow, plate, fails)
        if real is not None:
            real_figure(real)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    for k, v in NUMBERS.items():
        print("   %s = %.6g" % (k, v))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
