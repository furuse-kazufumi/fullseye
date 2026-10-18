# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 格子干渉計 —— 吸収では見えない粉・割れ・繊維の向きを、縞の振幅(暗視野)で見る。

【問い】X 線の透過像は「どれだけ吸われたか」しか写さない。樹脂の板の中の繊維の向き、幅 2 µm の割れ、気孔の群は、
吸収がまわりとほとんど同じなので透過像では消える。格子を 2 枚(線源が大きいなら 3 枚)入れて片方を 1 周期ずらし
ながら数枚撮ると、各画素で縞の正弦が取れ、その平均・位相・振幅から **透過・微分位相・暗視野** の 3 枚が同時に出る。
暗視野は「縞の振幅がどれだけ落ちたか」で、画素より小さい構造の小角散乱を測る。この PoC は、その一連を Fullseye の
op(`gratinginterf`、`opsoptics` の `grating_interf`、8 本)だけで組み、閉形式・第 2 実装・公開の実データで採点する。

  1. **タルボ絨毯**: 位相 π の格子の後ろの強度 I(x, z) を回折次数の和で出す(``talbot_carpet``、厳密な角スペクトル)。
     縞の可視度の極大が分数タルボ距離 (m − 1/2)·p²/(4λ)(Weitkamp ら 2005)に立ち、高さは方形波の基本波 4/π。
     第 2 実装 = 1 周期を標本化した場の FFT 伝搬(``optics.angular_spectrum_propagate``)。
  2. **線源の大きさと Lau の条件**: 線源が大きいと点ごとの縞がずれて重なり、可視度は |sinc(π w d/(L p2))| に落ちる。
     焦点 2 mm では 0.001。線源格子の周期を p0 = p2·L/d にすると開口ごとの縞が 1 周期ずつずれて重なり、2/π まで戻る。
     周期を 1/開口数 だけずらすと再び消える(``talbot_source_visibility``、第 2 実装 = 線源の点の非干渉な和)。
  3. **見せ場: 短繊維強化樹脂の板**(穴の周りを流れた跡に繊維が並び、穴の後ろの合流線で向きが 90° 変わる)に、
     幅 2 µm の割れと気孔の群を入れる。吸収ではほぼ見えないものが暗視野で浮かぶ。格子を 4 方位に回して撮り、
     暗視野の cos 2ω(Jensen ら 2010)から繊維の向きを画素ごとに戻す。★探針: 0/90° の 2 方位では斜めの繊維が決まらない。
  4. **微分位相の積分と折り返し**: 丸棒の微分位相を ``dpc_integrate`` で積分して投影の厚さに戻す。距離を延ばして
     縞の位相が π を超えると、op は「隣と 2π 近く跳ぶ」画素を見つけて拒否する。★正直な限界: 平らな背景の隣の
     1 画素だけが π を超える場合(段差の縁)は、折り返した図からは見分けられず、黙って間違う —— これも門で固定する。
  5. **1 周期のステップ数の推定**: 「1 周期を走査」とだけ書かれたデータは、1 周期のステップ数 P が枚数 N と一致しない
     ことがある。P = N と仮定すると微分位相が縞状に狂う。``grating_step_period_estimate`` が残差の最小で P を戻す。
     ★あてた平均で残差を割ると、雑音の項が P の一次で傾いて最小が偏る(1 枚 6000 光子で +0.03 段、3000 光子で
     +0.06 段。op は P に依らない素の平均で割る)。
  6. **実データ**(CC BY 4.0、Sanchez-Lara & Garcia-Pinto 2025「Talbot Lau Phase Contrast Images」、
     Zenodo, DOI 10.5281/zenodo.16944391): 基準 22 段・試料 24 段。P を推定してから 3 像を分ける。真値は無いので、
     物理の向き(吸収の強い球は散乱が弱く、繊維の束は吸収が弱く散乱が強い、球の左右の縁で微分位相の符号が逆)を門にする。
     データは同梱しない。``FULLSEYE_TALBOT_DATA`` に Reference.tif と Object.tif の置き場を指すと走り、無ければ・CI では
     記録値を印字して飛ばす。

【外部真値】分数タルボ距離と縞の周期(Weitkamp, Diaz, David et al., Opt. Express 13, 6296 (2005))、Lau の条件
(Pfeiffer, Weitkamp, Bunk & David, Nature Physics 2, 258 (2006))、暗視野 = 可視度の比(Pfeiffer et al., Nature
Materials 7, 134 (2008))、ガウス散乱の D = exp(−2π²σ²d²/p2²)(Bech et al., Phys. Med. Biol. 55, 5529 (2010))、
方向つき暗視野の cos 2ω(Jensen et al., Phys. Med. Biol. 55, 3317 (2010))、方形波の基本波 4/π、一様な線源の sinc。
第 2 実装 2 本(FFT の角スペクトル伝搬、線源の点の和)。公開の実データ 1 組。【学習】0。【較正】0。

★正直な限界: 位相ステップは単色・理想の正弦(格子の高次の調和・ステップの位置の誤差・検出器の点広がりは入れない)。
繊維・割れの散乱は「向きのあるガウス散乱」と置いた模型で、σ の大きさは選んだ値(実際は構造の大きさと自己相関長
ξ = λd/p2 の比で決まる)。線源格子は開口率 1/2 の理想。多色の線源で吸収が平均のエネルギーを上げ、散乱しない物体でも
可視度が落ちる効果(実データの球の中央で −ln D ≈ 0.17)は単色の順モデルに無い。

EXTEND: 装置の実データなら、まず空気(または基準)の区画で ``grating_step_period_estimate`` を回して P を決め、
基準と試料の露光が違えば ``grating_three_image_retrieve(reference_exposure=…)`` を渡す。暗視野を散乱角の広がりへ直すには
``darkfield_scatter_relation``、格子の配置の設計には ``talbot_grating_design`` と ``talbot_source_visibility``。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import gratinginterf as GI  # noqa: E402
import optics  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
DATA = os.environ.get("FULLSEYE_TALBOT_DATA", "").strip()

# 装置(実験室の X 線管を想定した値。特定の装置の値ではない)
E_KEV = 28.0
P1_UM = 4.36          # 第 1 格子(位相 π)
L_MM = 1200.0         # 線源(線源格子)から第 1 格子まで
V0 = 0.25             # 基準の縞の可視度
FLUX = 6000.0         # 1 枚あたりの光子数(透過 1 の画素)
N_STEPS = 8
PIX_UM = 40.0

FAILS: list[str] = []
GATES: list[str] = []
R: dict = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _hsv(h, s, v):
    """HSV(各 [0, 1])→ RGB。向きの図の色相用。"""
    h6 = (np.asarray(h) % 1.0) * 6.0
    i = np.floor(h6).astype(int) % 6
    f = h6 - np.floor(h6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


# --------------------------------------------------------------------------- #
def chapter_carpet():
    print("\n1. タルボ絨毯(位相 π の格子、平面波、厳密な角スペクトル)")
    lam_nm = GI.HC_KEV_NM / E_KEV
    zt = 2 * P1_UM ** 2 / (lam_nm * 1e-3) * 1e-3
    c = GI.talbot_carpet(P1_UM, energy_kev=E_KEV, grating="pi", z_max_mm=zt / 2, n_z=241 if REDUCED else 481,
                         n_x=128, n_periods=2, n_harmonics=63 if REDUCED else 255)
    zs, v = c["z_mm"], np.round(c["visibility"], 9)
    peaks = [zs[i] for i in range(1, zs.size - 1) if v[i] >= v[i - 1] and v[i] > v[i + 1] and v[i] > 1.0]
    dz = zs[1] - zs[0]
    d = c["self_image_mm"]
    err = max(min(abs(p - q) for p in peaks) for q in d) if peaks else float("inf")
    gate("縞の可視度の極大 %d 本 = 分数タルボ距離 (m − 1/2)p²/(4λ)(格子 %.2f mm 以内)" % (len(d), dz),
         len(peaks) == len(d) and err <= dz,
         "閉形式 %s mm / 極大 %s mm" % (", ".join("%.1f" % q for q in d), ", ".join("%.1f" % p for p in peaks)))
    vmax = float(np.max(c["visibility"]))
    gate("極大の可視度 %.4f = 方形波の基本波 4/π = %.4f" % (vmax, 4 / math.pi), abs(vmax - 4 / math.pi) < 1e-3)
    # 第 2 実装: 1 周期を 256 点で標本化した場を FFT で伝搬
    spp = 256
    x = (np.arange(spp) + 0.5) / spp
    t = np.where(x < 0.5, -1.0 + 0j, 1.0 + 0j)
    worst = 0.0
    for z in np.linspace(zt / 40, zt / 2, 9):
        u = optics.angular_spectrum_propagate(np.vstack([t, t]), wavelength_um=lam_nm * 1e-3, distance_um=z * 1e3,
                                              pixel_pitch_um=P1_UM / spp)
        inten = np.abs(u[0]) ** 2
        spec = np.fft.fft(inten) / spp
        v2 = 2 * abs(spec[2]) / spec[0].real
        vc = GI.talbot_carpet(P1_UM, energy_kev=E_KEV, grating="pi", z_max_mm=z, n_z=2, n_x=8)["visibility"][-1]
        worst = max(worst, abs(v2 - vc))
    gate("第 2 実装(標本化した場の FFT 伝搬)と可視度が 9 距離で 2e-3 以内", worst < 2e-3, "最大差 %.1e" % worst)
    R["carpet"] = c


def chapter_source():
    print("\n2. 線源の大きさと Lau の条件")
    g = GI.talbot_grating_design(P1_UM, energy_kev=E_KEV, source_distance_mm=L_MM)
    d, p2, p0 = g["distance_mm"], g["analyzer_period_um"], g["source_grating_period_um"]

    def point_sum(pts):
        ph = 2 * math.pi * (-np.asarray(pts) * d / L_MM) / p2
        return float(abs(np.mean(np.exp(1j * ph))))

    sizes = np.linspace(1.0, 400.0, 100 if REDUCED else 200)
    num = np.array([point_sum(-s / 2 + (np.arange(4000) + 0.5) * s / 4000) for s in sizes])
    cf = np.array([GI.talbot_source_visibility(s, L_MM, d, p2)["visibility_factor"] for s in sizes])
    gate("一様な線源: 閉形式 |sinc(π w d/(L p2))| = 線源の点の非干渉な和", float(np.max(np.abs(num - cf))) < 1e-4,
         "最大差 %.1e" % float(np.max(np.abs(num - cf))))
    spot = 2000.0
    v_spot = GI.talbot_source_visibility(spot, L_MM, d, p2)["visibility_factor"]
    n_slit = 2 * int(spot / (2 * p0)) + 1
    ratios = np.round(np.linspace(0.96, 1.04, 161 if REDUCED else 321), 9)
    v_g0 = np.array([GI.talbot_source_visibility(n_slit * p0 * r, L_MM, d, p2, source_grating_period_um=p0 * r,
                                                 n_slits=n_slit)["visibility_factor"] for r in ratios])
    k = np.arange(n_slit) - n_slit // 2
    num_g0 = []
    for r in ratios[:: 8]:
        pp = p0 * r
        pts = (k[:, None] * pp + (np.arange(64)[None, :] + 0.5) / 64 * pp / 2 - pp / 4).ravel()
        num_g0.append(point_sum(pts))
    diff_g0 = float(np.max(np.abs(np.array(num_g0) - v_g0[:: 8])))
    best = float(ratios[int(np.argmax(np.round(v_g0, 9)))])
    gate("焦点 2 mm で縞が消える(×%.3f)/ 線源格子の最良の周期 = Lau の条件(%.4f × p0、p0 = %.1f µm、開口 %d 本)"
         % (v_spot, best, p0, n_slit), v_spot < 0.01 and abs(best - 1) <= ratios[1] - ratios[0])
    gate("線源格子の可視度 %.4f = 開口 1/2 の |sinc(π/2)| = 2/π、点の和と %.1e 以内" % (v_g0.max(), diff_g0),
         abs(v_g0.max() - 2 / math.pi) < 1e-4 and diff_g0 < 1e-4)
    off = GI.talbot_source_visibility(n_slit * p0, L_MM, d, p2, source_grating_period_um=p0 * (1 + 1 / n_slit),
                                      n_slits=n_slit)["visibility_factor"]
    gate("探針: 周期を 1/開口数(%.1f %%)ずらすと開口ごとの縞が 1 周して消える(×%.4f)" % (100 / n_slit, off), off < 0.01)
    R["source"] = dict(sizes=sizes, num=num, cf=cf, ratios=ratios, v_g0=v_g0, v_spot=v_spot, g=g, n_slit=n_slit)
    return g


# --------------------------------------------------------------------------- #
def coupon(h=200, w=300):
    """繊維の向き θ(rad、x 軸から)、繊維の有無、等方の散乱、割れ、厚さ、穴、合流線。"""
    yy, xx = np.mgrid[:h, :w].astype(float)
    cx, cy, a = 110.0, 100.0, 34.0
    X, Y = (xx - cx) / a, (yy - cy) / a
    r2 = X * X + Y * Y
    hole = r2 < 1.0
    with np.errstate(divide="ignore", invalid="ignore"):          # 円柱を過ぎるポテンシャル流(繊維は流れに沿う)
        u = 1 - (X * X - Y * Y) / (r2 * r2)
        v = -2 * X * Y / (r2 * r2)
    theta = np.arctan2(v, u)
    weld = (xx > cx + a) & (np.abs(yy - cy) < 6)                    # 穴の後ろの合流線: 流れに直交して並ぶ
    theta = np.where(weld, np.pi / 2, theta)
    theta = np.mod(np.where(hole, 0.0, theta), np.pi)
    fiber = np.where(hole, 0.0, 1.0)
    rng = np.random.default_rng(20261015)                           # この PoC 専用の種(共有の乱数列を引かない)
    iso = np.zeros((h, w))
    for _ in range(60):                                             # 気孔の群(等方の散乱)
        px, py = rng.uniform(220, 280), rng.uniform(140, 185)
        iso += np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / (2 * 1.6 ** 2))
    iso = np.clip(iso, 0, 1.0) * (~hole)
    ang = math.radians(-25.0)                                       # 幅 2 µm・長さ 4.8 mm の割れ(画素 40 µm の 1/20)
    s = (xx - 200.0) * math.cos(ang) + (yy - 60.0) * math.sin(ang)
    n = -(xx - 200.0) * math.sin(ang) + (yy - 60.0) * math.cos(ang)
    crack = (np.abs(n) < 0.8) & (s > 0) & (s < 120)
    thick_mm = np.where(hole, 0.0, 3.0 + 0.2 * xx / w)
    return dict(theta=theta, fiber=fiber, iso=iso, crack=crack, crack_normal=ang + math.pi / 2,
                thick_mm=thick_mm, hole=hole, weld=weld)


def coupon_maps(c, omega, g):
    """格子の感度の向き ω での透過・微分位相・暗視野(真値)。"""
    k = 2 * math.pi ** 2 * (g["distance_mm"] * 1e3 / g["analyzer_period_um"]) ** 2
    mu = 0.06                                                       # 1/mm(樹脂 + 繊維、28 keV 付近の目安)
    trans = np.exp(-mu * c["thick_mm"])
    trans = np.where(c["crack"], trans * np.exp(mu * c["thick_mm"] * 2.0 / PIX_UM), trans)   # 割れの空隙 2/40
    sig_f, sig_iso, sig_crack = 6.0e-6, 6.0e-6, 9.0e-6              # rad(板 1 枚分)
    var = (c["fiber"] * sig_f ** 2 * np.sin(omega - c["theta"]) ** 2 * (c["thick_mm"] / 3.0)
           + c["iso"] * sig_iso ** 2 + c["crack"] * sig_crack ** 2 * np.cos(omega - c["crack_normal"]) ** 2)
    dfm = np.exp(-k * var)
    gy, gx = np.gradient(c["thick_mm"] * 1e3 / PIX_UM)
    alpha = -4.0e-7 * (gx * math.cos(omega) + gy * math.sin(omega))
    return trans, 2 * math.pi * g["distance_mm"] * 1e3 * alpha / g["analyzer_period_um"], dfm


def chapter_coupon(g):
    print("\n3. 見せ場: 短繊維強化樹脂の板(吸収ではほぼ見えない繊維の向き・割れ・気孔)")
    c = coupon()
    omegas = np.deg2rad([0.0, 45.0, 90.0, 135.0])
    rec = []
    for i, om in enumerate(omegas):
        t, phi, dfm = coupon_maps(c, om, g)
        s = GI.grating_stepping_simulate(t, phi, dfm, n_steps=N_STEPS, ref_visibility=V0, flux=FLUX, seed=10 + i)
        r = GI.grating_stepping_simulate(None, n_steps=N_STEPS, ref_visibility=V0, flux=FLUX, seed=50 + i,
                                         shape=t.shape)
        rec.append(GI.grating_three_image_retrieve(s, r, distance_mm=g["distance_mm"],
                                                   analyzer_period_um=g["analyzer_period_um"]))
    t0, _phi0, d0 = coupon_maps(c, 0.0, g)
    mat = ~c["hole"]
    e_t = float(np.sqrt(np.mean((rec[0]["transmission"][mat] - t0[mat]) ** 2)))
    e_d = float(np.sqrt(np.mean((rec[0]["darkfield"][mat] - d0[mat]) ** 2)))
    pred_d = math.sqrt(2.0 / (N_STEPS * FLUX)) / V0 * math.sqrt(2.0)            # 振幅の比の雑音の目安
    gate("3 像の回収: 透過 RMS %.4f、暗視野 RMS %.4f(Poisson の目安 %.3f)" % (e_t, e_d, pred_d),
         e_t < 0.02 and e_d < 2 * pred_d)
    sides = np.zeros_like(c["crack"])
    for sh in (3, 4, 5):
        sides |= np.roll(c["crack"], sh, axis=0) | np.roll(c["crack"], -sh, axis=0)
    sides &= ~c["crack"] & mat

    def cnr(img):
        a, b = img[c["crack"]], img[sides]
        return float(abs(np.mean(a) - np.mean(b)) / np.std(b))

    best = int(np.argmax([round(cnr(-np.log(np.clip(o["darkfield"], 1e-3, None))), 6) for o in rec]))
    cnr_t, cnr_d = cnr(rec[0]["transmission"]), cnr(rec[best]["darkfield"])
    gate("幅 2 µm の割れ: 暗視野の CNR %.1f(格子 %.0f°)が吸収の %.2f の 5 倍以上"
         % (cnr_d, np.rad2deg(omegas[best]), cnr_t), cnr_d > 5 * cnr_t)
    # −ln D(ω) = a + b sin²(ω − θ) = (a + b/2) − (b/2) cos 2(ω − θ)
    y = np.stack([-np.log(np.clip(o["darkfield"], 1e-3, None)) for o in rec])
    cc = np.tensordot(np.exp(-2j * omegas), y, axes=(0, 0))
    theta_hat = np.mod(-np.angle(-cc) / 2.0, np.pi)
    aniso = np.abs(cc) / len(omegas) * 2.0
    sel = mat & ~c["crack"] & (c["iso"] < 0.05)
    dth = np.angle(np.exp(2j * (theta_hat - c["theta"]))) / 2.0
    med = float(np.rad2deg(np.median(np.abs(dth[sel]))))
    p90 = float(np.rad2deg(np.percentile(np.abs(dth[sel]), 90)))
    gate("4 方位の暗視野から戻した繊維の向き: 誤差の中央値 %.1f°・90 %% 点 %.1f°" % (med, p90), med < 4.0 and p90 < 12.0)
    weld_th = float(np.rad2deg(np.median(theta_hat[c["weld"] & sel])))
    gate("合流線で向きが流れに直交(%.1f°、真値 90°)" % weld_th, abs(weld_th - 90.0) < 10.0)
    cc2 = np.tensordot(np.exp(-2j * omegas[[0, 2]]), y[[0, 2]], axes=(0, 0))
    th2 = np.mod(-np.angle(-cc2) / 2.0, np.pi)
    d2 = np.angle(np.exp(2j * (th2 - c["theta"]))) / 2.0
    diag = sel & (np.abs(np.mod(c["theta"], np.pi / 2) - np.pi / 4) < np.pi / 8)
    med2, med4 = (float(np.rad2deg(np.median(np.abs(x_[diag])))) for x_ in (d2, dth))
    gate("探針: 0/90° の 2 方位だけでは斜めの繊維が決まらない(誤差の中央値 %.1f° 対 4 方位 %.1f°)" % (med2, med4),
         med2 > 3 * med4)
    pore = c["iso"] > 0.5
    mean_sc = np.mean(y, axis=0)
    r_pore = float(np.median(aniso[pore] / mean_sc[pore]))
    r_fib = float(np.median(aniso[sel] / mean_sc[sel]))
    gate("気孔は等方の散乱(異方性 / 平均 %.2f、繊維 %.2f)" % (r_pore, r_fib), r_pore < 0.5 * r_fib)
    R["coupon"] = dict(c=c, rec=rec, omegas=omegas, theta_hat=theta_hat, aniso=aniso, mean_sc=mean_sc, best=best,
                       cnr=(cnr_t, cnr_d))


# --------------------------------------------------------------------------- #
def _rod_dpc(g, h=40, w=200, r_px=60.0, delta=4.0e-7):
    xb = np.arange(w + 1, dtype=float) - 0.5
    tb = 2 * np.sqrt(np.clip(r_px ** 2 - (xb - w / 2) ** 2, 0, None)) * PIX_UM
    alpha = np.tile(-delta * np.diff(tb) / PIX_UM, (h, 1))
    return 2 * math.pi * g["distance_mm"] * 1e3 * alpha / g["analyzer_period_um"], 0.5 * (tb[1:] + tb[:-1])


def chapter_integrate(g):
    print("\n4. 微分位相の積分と折り返し")
    delta = 4.0e-7
    phi, t_c = _rod_dpc(g)
    s = GI.grating_stepping_simulate(np.exp(-0.06e-3 * np.tile(t_c, (phi.shape[0], 1))), phi, None,
                                     n_steps=N_STEPS, ref_visibility=V0, flux=FLUX, seed=7)
    r = GI.grating_stepping_simulate(None, n_steps=N_STEPS, ref_visibility=V0, flux=FLUX, seed=8, shape=phi.shape)
    o = GI.grating_three_image_retrieve(s, r)
    th = GI.dpc_integrate(o["dpc_rad"], PIX_UM, g["distance_mm"], g["analyzer_period_um"],
                          wavelength_nm=g["wavelength_nm"], delta=delta, baseline="both")["thickness_um"]
    prof = th.mean(axis=0)
    err = float(np.max(np.abs(prof - t_c)) / t_c.max())
    gate("丸棒(直径 4.8 mm)の厚さを微分位相の積分で %.2f %% 以内に(縞の位相の最大 %.2f rad)"
         % (err * 100, float(np.max(np.abs(phi)))), err < 0.03)
    # 距離(角度感度)を延ばしていくと、どこで折り返すか
    scales = np.round(np.arange(1.0, 12.01, 0.5), 6)
    verdict = []
    for k in scales:
        try:
            GI.dpc_integrate(GI._wrap(phi * k), PIX_UM, g["distance_mm"] * k, g["analyzer_period_um"],
                             wavelength_nm=g["wavelength_nm"], delta=delta)
            verdict.append(True)
        except ValueError:
            verdict.append(False)
    first_ref = float(scales[verdict.index(False)]) if False in verdict else None
    true_max = float(np.max(np.abs(phi)))
    gate("感度を上げて本当の |φ| が π を超えたら拒否(%.1f 倍から拒否、そのとき |φ| = %.2f rad)"
         % (first_ref or float("nan"), (first_ref or 0) * true_max),
         first_ref is not None and first_ref * true_max > math.pi and all(verdict[: verdict.index(False)])
         and all((sc * true_max <= math.pi) == ok_ for sc, ok_ in zip(scales, verdict) if sc * true_max <= math.pi))
    # ★正直な限界: 段差の縁の 1 画素だけが π を超える板(平らな背景の隣)は、折り返しが見えずに通る
    w = 120
    xb = np.arange(w + 1, dtype=float) - 0.5
    tb = np.where((xb > 40) & (xb < 80), 2000.0, 0.0)              # 厚さ 2 mm の板(縁が鋭い)
    alpha = -delta * np.diff(tb) / PIX_UM
    k_need = 1.4 * math.pi / float(np.max(np.abs(2 * math.pi * g["distance_mm"] * 1e3 * alpha / g["analyzer_period_um"])))
    phi_slab = np.tile(2 * math.pi * g["distance_mm"] * k_need * 1e3 * alpha / g["analyzer_period_um"], (4, 1))
    o_s = GI.dpc_integrate(GI._wrap(phi_slab), PIX_UM, g["distance_mm"] * k_need, g["analyzer_period_um"],
                           wavelength_nm=g["wavelength_nm"], delta=delta)
    slab_mid = float(o_s["thickness_um"][0, 60])
    gate("正直な限界: 鋭い縁の 1 画素だけが π を超える板は折り返しが見えず通る(中央の厚さ %.0f µm、真値 2000)"
         % slab_mid, abs(slab_mid - 2000.0) > 500.0)
    R["integrate"] = dict(t_c=t_c, prof=prof, scales=scales, verdict=verdict, true_max=true_max,
                          slab=(o_s["thickness_um"][0], 0.5 * (tb[1:] + tb[:-1])))


def chapter_period(g):
    print("\n5. 1 周期のステップ数の推定(P ≠ N)")
    n, p_true = 22, 20.85
    yy, xx = np.mgrid[:128, :192].astype(float)
    phi = 0.6 * np.exp(-((xx - 120) ** 2 + (yy - 64) ** 2) / (2 * 28.0 ** 2)) * (xx - 120) / 28.0
    s = GI.grating_stepping_simulate(None, phi, None, n_steps=24, steps_per_period=22.3, ref_visibility=V0,
                                     flux=FLUX, seed=21)
    r = GI.grating_stepping_simulate(None, n_steps=n, steps_per_period=p_true, ref_visibility=V0, flux=FLUX,
                                     seed=22, shape=phi.shape)
    region = (0, 128, 0, 40)                                         # 試料の無い左の帯
    er = GI.grating_step_period_estimate(r, p_step=0.01, region=region)
    es = GI.grating_step_period_estimate(s, p_step=0.01, region=region)
    gate("推定した P: 基準 %.2f(真値 %.2f)・試料 %.2f(真値 22.30)" % (er["steps_per_period"], p_true,
                                                              es["steps_per_period"]),
         abs(er["steps_per_period"] - p_true) <= 0.05 and abs(es["steps_per_period"] - 22.3) <= 0.05)
    naive = GI.grating_three_image_retrieve(s, r)
    good = GI.grating_three_image_retrieve(s, r, steps_per_period_sample=es["steps_per_period"],
                                           steps_per_period_reference=er["steps_per_period"])
    e_n = float(np.sqrt(np.mean((naive["dpc_rad"] - phi) ** 2)))
    e_g = float(np.sqrt(np.mean((good["dpc_rad"] - phi) ** 2)))
    gate("微分位相の誤差 RMS: P = N と仮定 %.3f rad → 推定した P %.3f rad" % (e_n, e_g), e_g < 0.5 * e_n)
    grid = np.round(np.arange(20.5, 21.2001, 0.01), 9)
    biased = [round(float(np.sqrt(np.mean(GI._sine_fit(r[:, :, :40], float(p), "x", "s")[3] ** 2))), 9) for p in grid]
    p_b = float(grid[int(np.argmin(biased))])
    gate("探針: あてた平均で残差を割ると最小が偏る(%.2f、op は %.2f、真値 %.2f)" % (p_b, er["steps_per_period"], p_true),
         p_b - p_true > 0.02 and abs(er["steps_per_period"] - p_true) < p_b - p_true)
    R["period"] = dict(er=er, es=es, naive=naive, good=good, phi=phi)


# --------------------------------------------------------------------------- #
RECORDED_REAL = {"note": "2026-10-18 の実行で記録(データが無い・CI では読み込まずにこれを印字する)",
                 "P_ref": 20.80, "N_ref": 22, "P_obj": 22.30, "N_obj": 24,
                 "residual_ref": "0.0073 -> 0.0044", "residual_obj": "0.0065 -> 0.0040",
                 "transmission_sphere_stick": (0.778, 0.919), "minus_ln_D_sphere_stick": (0.1738, 0.5487),
                 "dpc_edge_left_right_rad": (0.12, -0.17), "visibility_reference_median": 0.1281}


def _bin2(a):
    n, h, w = a.shape
    return a[:, : h // 2 * 2, : w // 2 * 2].reshape(n, h // 2, 2, w // 2, 2).mean(axis=(2, 4))


def chapter_real():
    print("\n6. 実データ(CC BY 4.0、Zenodo 16944391、Sanchez-Lara & Garcia-Pinto 2025)")
    ref_p = os.path.join(DATA, "Reference.tif") if DATA else ""
    obj_p = os.path.join(DATA, "Object.tif") if DATA else ""
    if REDUCED or not (ref_p and os.path.exists(ref_p) and os.path.exists(obj_p)):
        print("   データが無い(FULLSEYE_TALBOT_DATA)/ CI のため飛ばす。記録値: %s" % RECORDED_REAL)
        return
    try:
        import tifffile
    except ImportError:
        print("   tifffile が無いので飛ばす(pip install tifffile)。記録値: %s" % RECORDED_REAL)
        return
    ref = _bin2(tifffile.imread(ref_p).astype(np.float64))
    obj = _bin2(tifffile.imread(obj_p).astype(np.float64))
    print("   基準 %s、試料 %s(2×2 で束ねた)" % (ref.shape, obj.shape))
    region = (80, 180, 60, 160)                                      # 容器の中・球と棒の外
    er = GI.grating_step_period_estimate(ref, region=region)
    es = GI.grating_step_period_estimate(obj, region=region)
    gate("1 周期のステップ数: 基準 P = %.2f(N = %d)・試料 P = %.2f(N = %d)、残差 %.4f→%.4f / %.4f→%.4f"
         % (er["steps_per_period"], er["n_steps"], es["steps_per_period"], es["n_steps"], er["residual_at_n"],
            er["residual_min"], es["residual_at_n"], es["residual_min"]),
         er["residual_min"] < er["residual_at_n"] and es["residual_min"] < es["residual_at_n"])
    o = GI.grating_three_image_retrieve(obj, ref, steps_per_period_sample=es["steps_per_period"],
                                        steps_per_period_reference=er["steps_per_period"])
    T, Dm, P = o["transmission"], o["darkfield"], o["dpc_rad"]
    bg, sph, stick = (slice(420, 640), slice(420, 470)), (slice(170, 220), slice(320, 380)), \
        (slice(420, 640), slice(300, 355))

    def t_rel(rr):
        return float(np.nanmedian(T[rr]) / np.nanmedian(T[bg]))

    def s_rel(rr):
        return float(-np.log(np.nanmedian(Dm[rr]) / np.nanmedian(Dm[bg])))

    gate("球は吸収が強く散乱が弱い / 棒は吸収が弱く散乱が強い(透過 %.2f / %.2f、−ln D %.3f / %.3f)"
         % (t_rel(sph), t_rel(stick), s_rel(sph), s_rel(stick)),
         t_rel(sph) < t_rel(stick) and s_rel(stick) > 2 * max(s_rel(sph), 0.02))
    left = float(np.nanmedian(P[170:220, 285:300]) - np.nanmedian(P[170:220, 255:270]))
    right = float(np.nanmedian(P[170:220, 405:420]) - np.nanmedian(P[170:220, 435:450]))
    gate("球の左右の縁で微分位相の符号が逆(%+.2f / %+.2f rad)" % (left, right),
         left * right < 0 and min(abs(left), abs(right)) > 0.1)
    R["real"] = dict(o=o, er=er, es=es)
    print("   記録: P_ref %.2f、P_obj %.2f、透過 %.3f / %.3f、−ln D %.4f / %.4f、基準の可視度の中央値 %.4f"
          % (er["steps_per_period"], es["steps_per_period"], t_rel(sph), t_rel(stick), s_rel(sph), s_rel(stick),
             float(np.nanmedian(o["visibility_reference"]))))


# --------------------------------------------------------------------------- #
SRC_REAL = ("Sanchez-Lara, V. & Garcia-Pinto, D. (2025) Talbot Lau Phase Contrast Images. Zenodo. "
            "https://doi.org/10.5281/zenodo.16944391 (CC BY 4.0). 改変: 2×2 の画素を束ね、Fullseye の op で 3 像に分けた")


def make_figures():
    c = R["carpet"]
    img = c["intensity"].T[::-1]                                     # 縦 = x(2 周期)、横 = z
    figs.save("talbot_carpet", np.repeat(img, 2, axis=0), "位相 π の格子(%.0f keV、p1 = %.2f µm)の後ろの強度 I(x, z)。"
              "横 = 第 1 格子からの距離 0〜z_T/2(%.0f mm)、縦 = 2 周期。周期 p1/2 の縞が結ぶ距離が分数タルボ距離 "
              "(m − 1/2)p1²/(4λ) = %s mm。z = 0 は純粋な位相格子なので強度は一様(縞が無い)。"
              % (E_KEV, P1_UM, c["z_mm"][-1], ", ".join("%.0f" % z for z in c["self_image_mm"])))
    vis = c["visibility"]
    ser = [("縞の可視度(回折次数の和)", c["z_mm"], vis), ("4/π", c["z_mm"], np.full_like(vis, 4 / math.pi))]
    for z in c["self_image_mm"]:
        ser.append(("", np.array([z, z]), np.array([0.0, 4 / math.pi])))
    figs.save_plot("carpet_visibility", ser, xlabel="z [mm]", ylabel="周期 p1/2 の縞の可視度",
                   styles=[None, "dashed"] + ["dotted"] * len(c["self_image_mm"]),
                   colors=["emphasis", "reference"] + ["neutral"] * len(c["self_image_mm"]),
                   title="極大は分数タルボ距離(点線)に立ち、高さは方形波の基本波 4/π",
                   caption="点線 = 閉形式の距離。極大の位置は第 2 実装(標本化した場の FFT 伝搬)とも 2e-3 で一致。")
    s = R["source"]
    figs.save_plot("source_size", [("線源の点の非干渉な和", s["sizes"], s["num"]),
                                   ("|sinc(π w d/(L p2))|", s["sizes"], s["cf"])],
                   xlabel="線源の幅 w [µm]", ylabel="縞の可視度(相対)", styles=[None, "dashed"],
                   colors=["neutral", "reference"], kinds=["scatter", "line"],
                   title="線源が大きいと点ごとの縞がずれて重なり、消える",
                   caption="L = %.0f mm、d = %.1f mm、p2 = %.3f µm。焦点 2 mm では ×%.3f。"
                           % (L_MM, s["g"]["distance_mm"], s["g"]["analyzer_period_um"], s["v_spot"]))
    figs.save_plot("lau_condition", [("線源格子あり(開口 %d 本)" % s["n_slit"], s["ratios"], s["v_g0"]),
                                     ("線源格子なし(焦点 2 mm)", s["ratios"], np.full_like(s["ratios"], s["v_spot"])),
                                     ("2/π", s["ratios"], np.full_like(s["ratios"], 2 / math.pi))],
                   xlabel="線源格子の周期 / Lau の条件 p2·L/d", ylabel="縞の可視度(相対)",
                   styles=[None, "dotted", "dashed"], colors=["emphasis", "wrong", "reference"],
                   title="Lau の条件 p0 = %.1f µm で 2/π まで戻り、1/開口数 ずらすと消える"
                         % s["g"]["source_grating_period_um"],
                   caption="開口 1/2 の線源格子。開口 1 本の縞は |sinc(π/2)| = 2/π、開口の並びの因子 |sin Nβ/(N sin β)| は "
                           "β = π(Lau の条件)で 1。")
    k = R["coupon"]
    cp, rec = k["c"], k["rec"]
    tr0 = rec[0]["transmission"]
    t_lo, t_hi = (float(np.percentile(tr0[~cp["hole"]], q)) for q in (0.5, 99.5))
    figs.save_grid("three_images", [tr0, rec[0]["dpc_rad"], rec[3]["darkfield"],
                                    rec[0]["darkfield"], rec[1]["darkfield"], rec[2]["darkfield"]],
                   captions=["透過(吸収)", "微分位相 0°", "暗視野 135°", "暗視野 0°", "暗視野 45°", "暗視野 90°"],
                   ncols=3, gray=[True, False, True, True, True, True], signed=[False, True, False, False, False, False],
                   vrange=[(t_lo, t_hi), (-0.6, 0.6), (0.3, 1.05), (0.3, 1.05), (0.3, 1.05), (0.3, 1.05)],
                   title="短繊維強化樹脂の板: 吸収では消えるものが暗視野に出る",
                   caption="同じ 8 段の位相ステップから 3 像。透過(板の値の範囲 %.3f〜%.3f に伸ばして表示)では繊維の向き・"
                           "幅 2 µm の割れ(右上の斜めの線)・気孔の群"
                           "(右下)はほぼ見えない(割れの CNR %.2f)。暗視野では割れが CNR %.1f で浮かび、格子を回すと"
                           "繊維の向きに応じて明暗が入れ替わる。画素 40 µm、1 枚 6000 光子、V0 = 0.25。" % ((t_lo, t_hi) + k["cnr"]))
    hole = cp["hole"]
    sat = np.clip(k["aniso"] / np.nanpercentile(k["aniso"][~hole], 95), 0, 1)
    rgb = _hsv(k["theta_hat"] / np.pi, np.ones_like(sat), sat)
    rgb[hole] = 0
    truth = _hsv(cp["theta"] / np.pi, np.ones_like(sat), (~hole).astype(float))
    msc = k["mean_sc"] / np.nanpercentile(k["mean_sc"][~hole], 99.5)
    figs.save_grid("fiber_orientation", [truth, rgb, np.clip(msc, 0, 1)],
                   captions=["真値の向き(色相 0〜180°)", "暗視野 4 方位から戻した向き", "平均の散乱 −ln D"],
                   ncols=3, title="暗視野の cos 2ω から繊維の向きを画素ごとに",
                   caption="中央: 色相 = 向き、明るさ = 異方性の強さ。穴の周りを回り込む流れと、穴の後ろの合流線(90°、"
                           "水平な帯)で向きが変わる様子が戻る。右: 等方の気孔の群と割れは平均の散乱に出る。")
    frames = []
    for om in np.deg2rad(np.arange(0, 180, 7.5)):
        yv = k["mean_sc"] - k["aniso"] * np.cos(2 * (om - k["theta_hat"]))
        im = np.where(hole, 1.0, np.exp(-np.clip(yv, 0, None)))
        g8 = np.clip((im - 0.3) / 0.75, 0, 1).repeat(2, axis=0).repeat(2, axis=1)     # 2 倍(最近傍)・灰色
        frames.append(np.stack([g8, g8, g8], axis=-1))
    figs.save_gif("rotating_grating", frames, "格子の向きを 0〜180° に回したときの暗視野(4 方位から戻した a、b、θ で描く)。"
                  "繊維が格子の感度の向きに直交すると暗くなり、明暗の帯が向きの場に沿って流れる。", fps=8.0)
    it = R["integrate"]
    xs = np.arange(it["t_c"].size, dtype=float)
    figs.save_plot("dpc_integration", [("真値の投影の厚さ", xs, it["t_c"] / 1e3), ("微分位相を積分", xs, it["prof"] / 1e3)],
                   xlabel="画素(40 µm)", ylabel="厚さ [mm]", styles=["dashed", None], colors=["reference", "emphasis"],
                   title="丸棒の微分位相を積分して厚さに戻す(baseline = 両端)",
                   caption="行の平均。縞の位相の最大 %.2f rad(π より十分小さい)。" % it["true_max"])
    ver = np.array(it["verdict"], float)
    figs.save_plot("wrap_refusal", [("受理 = 1 / 拒否 = 0", it["scales"] * it["true_max"], ver),
                                    ("π", np.array([math.pi, math.pi]), np.array([0.0, 1.0]))],
                   xlabel="本当の縞の位相の最大 |φ| [rad](距離を延ばして感度を上げる)", ylabel="dpc_integrate の判定",
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   title="本当の |φ| が π を超えると折り返しを見つけて拒否する",
                   caption="正直な限界: 鋭い縁の 1 画素だけが π を超える板は、折り返した値が背景と π 以内に収まるので見えずに通る"
                           "(中央の厚さ %.0f µm、真値 2000 µm)。" % float(it["slab"][0][60]))
    p = R["period"]
    figs.save_plot("step_period", [("基準(N = 22)", p["er"]["p_grid"], p["er"]["residual"]),
                                   ("試料(N = 24)", p["es"]["p_grid"], p["es"]["residual"])],
                   xlabel="1 周期のステップ数 P", ylabel="正弦をあてた残差(RMS / 平均)", colors=["emphasis", "neutral"],
                   title="残差の最小が 1 周期のステップ数(基準 %.2f・試料 %.2f)"
                         % (p["er"]["steps_per_period"], p["es"]["steps_per_period"]),
                   caption="真値は基準 20.85・試料 22.30。P = N と仮定すると微分位相に縞状の誤差が出る(次の図)。")
    e_n = p["naive"]["dpc_rad"] - p["phi"]
    e_g = p["good"]["dpc_rad"] - p["phi"]
    figs.save_grid("step_period_dpc", [p["phi"], e_n, e_g],
                   captions=["真値の微分位相(±0.6 rad)", "誤差: P = N と仮定(±0.15)", "誤差: 推定した P(±0.15)"],
                   ncols=3, signed=True, vrange=[(-0.6, 0.6), (-0.15, 0.15), (-0.15, 0.15)],
                   title="1 周期のステップ数を間違えると微分位相が狂う",
                   caption="誤差 RMS %.3f → %.3f rad。P = N と仮定した誤差は位相の場そのものに沿って出る(縞の位相ごとに"
                           "ずれ方が違う)ので、平均を引いても消えない。推定した P では雑音だけが残る。"
                           % (float(np.sqrt(np.mean(e_n ** 2))), float(np.sqrt(np.mean(e_g ** 2)))))
    if "real" in R:
        o = R["real"]["o"]
        tr, df = o["transmission"], o["darkfield"]
        figs.save_grid("real_three_images", [tr, o["dpc_rad"], df], captions=["透過", "微分位相 [rad]", "暗視野"],
                       ncols=3, gray=[True, False, True], signed=[False, True, False],
                       vrange=[(float(np.nanpercentile(tr, 1)), float(np.nanpercentile(tr, 99))), (-0.35, 0.35),
                               (float(np.nanpercentile(df, 1)), float(np.nanpercentile(df, 99)))],
                       title="公開の実データを 3 像に(1 周期のステップ数は推定: 基準 %.2f・試料 %.2f)"
                             % (R["real"]["er"]["steps_per_period"], R["real"]["es"]["steps_per_period"]),
                       caption="球(吸収が強い)は透過で暗く暗視野ではほぼ消え、繊維の束の棒(吸収が弱い)は暗視野で暗い。"
                               "微分位相の左右の色の違いは背景の位相の傾き(基準と試料の撮影の間の格子のずれか円錐の効果。"
                               "dpc_integrate の baseline='both' で消す種類のずれ)。")
        # save_grid は source を取らないので、台帳の項目に出典を足す
        if figs._manifest and figs._manifest[-1]["name"] == "real_three_images":
            figs._manifest[-1]["source"] = SRC_REAL
            d = figs.target_dir()
            if d is not None:
                import json
                (d / "figures.json").write_text(json.dumps(figs._manifest, ensure_ascii=False, indent=1),
                                                encoding="utf-8")


def main():
    t0, c0 = time.time(), time.process_time()
    print("PoC 格子干渉計(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_carpet()
    g = chapter_source()
    chapter_coupon(g)
    chapter_integrate(g)
    chapter_period(g)
    chapter_real()
    if not REDUCED and figs.target_dir() is not None:
        make_figures()
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件"
          % (time.process_time() - c0, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
