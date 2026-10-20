# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 水が検査画像にどう写るか ―― プールの底のコースティクス・瓶の側面像・濡れた板・船体の水中画像を、閉形式と第 2 の方法で採点する。

【問い】水は検査カメラの映像を 4 通りに変える。(1) 波のある水面は、底の模様の上に明るい網(コースティクス)を載せ、ひび割れの検出器はそれをひびと取り違える。
(2) 液体の入った瓶は円柱レンズで、背面光の下では中央の帯だけが明るくなる。気泡は暗い輪になり、液面の高さは明暗の段になる。(3) 濡れた面は暗く、てかる。
(4) 濁った水の中で、カメラの横のランプは正面の水を照らして霧のベールを作り、距離とともに信号対雑音比が落ちる。
新 op 7 本(`watervision`、`opsoptics` の `watervision`)に切り出し、4 つの場面を同じ関数で示す。

  1. **プールの底**: 12a の海の場(風速 3 と 6 m/s の JONSWAP)を、手で傾きに合わせて(PM は毛管波を持たないので傾きの絶対値は手で決める)水面にして、
     深さ 1 m の底の照度を光子(規則格子の光線をスネルの式で曲げ、双線形に撒く)とヤコビアン(1/|det J|、折り目は inf)の 2 つの方法で作る。門: 平らな水面は
     一様に cos θ T、光子の総量が入射 × 平均透過率に 1e-6(周期境界)、2 方法が滑らかな面で 2 % 以内(実測 0.3 %)、折り目でだけ食い違い波面法は inf と旗を出す、
     光線密度を 2 倍にして 1 % 未満。ひび割れ検出器(レジストリの `canny`)は、コースティクスの縁を拾って適合率が落ちる。コースティクスの分割で縁を除くと適合率が戻る
     (再現率は下がる)。強い波(6 m/s)では検出器の相対しきい値がコースティクスの勾配に負けてひびが消え、分割で除いても戻らない ―― 照度で割る(平坦化)と戻る。
  2. **瓶**: 円柱の断面を行ごとに追跡する。門: 液面の上下の行は空・満の断面と bit 一致、中央の明るさの比が 4 界面のフレネル透過率の積の比に 1e-9、
     明るい帯の半幅が近軸焦点からの予測に 15 % 以内、液面の行が round(充填率 × 高さ / 画素) ± 1、5 つの充填 × 2 つの照明で測った液面が 1 画素以内、
     気泡の輪の外径が 2 r × 倍率(近軸の 2 × 2 行列)に ± 1 画素、どの画素も背面板の放射輝度(1)を超えない。
  3. **濡れた面**: Lekner & Dorf(1988)。門: 膜 0 で反照率が変わらない(1e-12)、朗伯面の濡れた反照率が閉形式に、独立の数値積分で 1e-6、どの反照率でも濡れは暗い
     (a = 0.5 で比 0.673)。同じ板を乾湿で描き、欠陥のコントラストが予測の向きに動く。照明角を変えるとてかりの出る画素が入れ替わる。
  4. **船体と水中のランプ**: 1・3・6 m、ジャーロフ I 型と 3C 型。門: SNR が距離で単調に落ちる、純水で距離 → 0 は澄んだ水に 1e-9、中央のベールが最大。
  5. **限界(モデルが外れる所)**: 瓶は断面ごとに追跡するので、カメラから縦に離れた行は光線が面から傾く。垂直な円柱ではこれは実効屈折率
     `sqrt(n² − sin²α)` に置き換えることで厳密に扱え(縦成分は保存される)、明るい帯の半幅がどれだけ動くかを示す。肩(半径の変わる所)ではその置き換えも使えない。
  6. **壊して確かめる**: 屈折率を変える、倍率 1 を仮定する、内部反射率 r = 0 とする → 門が赤になる。

【外部真値】Fresnel の式を別に書いたもの、光子の数え上げとヤコビアンの 2 方法、近軸の 2 × 2 行列、Lekner & Dorf の閉形式と別の数値積分(`scipy.integrate.quad`)、
スペクトルのピークの周期。手法: Tessendorf(2001)/ Lekner & Dorf, Applied Optics 27, 1278(1988)/ Twomey et al., Applied Optics 25, 631(1986)/ Akkaynak & Treibitz, CVPR 2018。
【学習】0。【較正】0。

★正直な限界: 瓶は水平の断面で追跡し(縦の屈折は実効屈折率で近似できるが肩は扱えない)、壁の内部反射は追わない。濡れた面の膜は波長より十分厚いとして干渉を無視し、
被覆率の法則(膜厚 2 µm で 63 %)は仮定。ランプのベールは 1 回散乱でビームの形は仮定。海の傾きの絶対値は手で合わせた(12a の限界)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import defectgen  # noqa: E402
import examplefig as figs  # noqa: E402
import ops  # noqa: E402
import watermedia as WM  # noqa: E402
import watervision as WV  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}
N_W = float(WM.fresnel_water_air(0.0)["n_water"])
CANNY = {o.name: o for o in ops.REGISTRY}["canny"].fn


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def refused(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def fresnel_t(theta, n1, n2):
    """Fresnel の透過率(無偏光)。op とは別に書いたもの。"""
    ci = np.cos(theta)
    ct = np.sqrt(1.0 - (n1 / n2 * np.sin(theta)) ** 2)
    rs = (n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)
    rp = (n2 * ci - n1 * ct) / (n2 * ci + n1 * ct)
    return 1.0 - 0.5 * (rs * rs + rp * rp)


# --------------------------------------------------------------------------- #
# 1. プールの底                                                                  #
# --------------------------------------------------------------------------- #
POOL_L = 6.0
POOL_DEPTH = 1.0


def make_sea(wind, slope_rms, n=256, seed=4):
    """12a の JONSWAP の場を、波長 0.3 m 以上の重力波だけにして、傾きの RMS を手で合わせる。"""
    f = WM.ocean_height_field(n, POOL_L, wind, 0.0, kind="jonswap", fetch_m=200.0, seed=seed)
    h = f["height"]
    k = 2 * math.pi * np.fft.fftfreq(n, POOL_L / n)
    kk = np.hypot(k[:, None], k[None, :])
    h = np.fft.ifft2(np.fft.fft2(h) * (kk < 2 * math.pi / 0.30)).real
    spec = np.fft.fft2(h)
    hx = np.fft.ifft2(spec * 1j * k[None, :]).real
    hy = np.fft.ifft2(spec * 1j * k[:, None]).real
    return h * slope_rms / math.sqrt(float(np.mean(hx * hx + hy * hy)))


def pr(det, truth, tol=3):
    near = ndimage.binary_dilation(truth, iterations=tol)
    prec = float((det & near).sum() / max(det.sum(), 1))
    rec = float((truth & ndimage.binary_dilation(det, iterations=tol)).sum() / truth.sum())
    return prec, rec


def chapter_pool():
    print("\n1. プールの底のコースティクスと、ひび割れ検出器")
    # (a) 平らな面と光子の総量
    flat = WV.caustic_irradiance(np.zeros((32, 32)), POOL_L, POOL_DEPTH, (35.0, 20.0))
    th = math.radians(35.0)
    expect = math.cos(th) * fresnel_t(th, 1.0, N_W)
    gate("平らな水面は一様に cos θ · T(1e-9、ばらつき 1e-9 以下)",
         abs(flat["irradiance"].mean() / expect - 1) < 1e-9 and np.ptp(flat["irradiance"]) < 1e-9,
         "%.6f(閉形式 %.6f)、ptp %.1e" % (flat["irradiance"].mean(), expect, np.ptp(flat["irradiance"])))
    seas = {3.0: make_sea(3.0, 0.06), 6.0: make_sea(6.0, 0.10)}
    res = {w: WV.caustic_irradiance(h, POOL_L, POOL_DEPTH, (0.0, 0.0)) for w, h in seas.items()}
    r3 = res[3.0]
    cell = (POOL_L / 256) ** 2
    gate("光子の総量 = 入射 × 平均透過率(周期境界、1e-6)",
         abs(r3["floor_flux"] / (r3["incident_flux_analytic"] * r3["mean_transmittance"]) - 1) < 1e-6
         and abs(r3["irradiance"].sum() * cell / r3["floor_flux"] - 1) < 1e-9,
         "床の総量 %.6f、入射 × T = %.6f、T̄ = %.5f" % (r3["floor_flux"], r3["incident_flux_analytic"] * r3["mean_transmittance"], r3["mean_transmittance"]))
    for w, r in res.items():
        e = r["irradiance"]
        print("   風速 %g m/s: 照度の最大 %.2f、最小 %.2f(平らなら %.3f)" % (w, e.max(), e.min(), r["flat_irradiance"]))
    gate("強い波ほどコースティクスの濃淡が大きい(6 m/s の最大 > 3 m/s)", res[6.0]["irradiance"].max() > res[3.0]["irradiance"].max())
    # (b) 2 つの方法
    n_s = 64
    xs = np.arange(n_s) * 4.0 / n_s
    X, Y = np.meshgrid(xs, xs)

    def surf(a):
        return a * (np.sin(2 * np.pi * 2 * X / 4.0) + 0.6 * np.cos(2 * np.pi * (X + 2 * Y) / 4.0 + 0.7) + 0.4 * np.sin(2 * np.pi * 3 * Y / 4.0 + 1.1))

    hs = surf(0.008)
    ph = WV.caustic_irradiance(hs, 4.0, 1.0, (0.0, 0.0), ray_density=2)
    wf = WV.caustic_irradiance(hs, 4.0, 1.0, (0.0, 0.0), method="wavefront", ray_density=1)
    rel = float(np.sqrt(np.mean((ph["irradiance"] - wf["irradiance"]) ** 2)) / ph["irradiance"].mean())
    gate("光子とヤコビアンは滑らかな面で 2 % 以内、折り目なし", rel < 0.02 and not wf["fold_mask"].any(), "相対 RMS %.2f %%" % (100 * rel))
    NUMBERS["rel_methods"] = rel
    hf = surf(0.2)
    pf = WV.caustic_irradiance(hf, 4.0, 1.0, (0.0, 0.0), ray_density=4)
    wff = WV.caustic_irradiance(hf, 4.0, 1.0, (0.0, 0.0), method="wavefront", ray_density=2)
    fold = wff["fold_mask"]
    near = fold.copy()
    for _ in range(3):
        near = near | np.roll(near, 1, 0) | np.roll(near, -1, 0) | np.roll(near, 1, 1) | np.roll(near, -1, 1)
    far = ~near
    rel_far = float(np.sqrt(np.mean((pf["irradiance"][far] - wff["irradiance"][far]) ** 2)) / pf["irradiance"][far].mean())
    gate("折り目(振幅 0.2 m): 波面法は inf と旗を出し、光子は有限の大きな値を数える",
         fold.sum() > 20 and bool(np.isinf(wff["irradiance"][fold]).all()) and bool(np.isfinite(pf["irradiance"]).all()),
         "折り目 %d 画素(%.1f %%)、光子の折り目の平均 %.1f(全体平均の %.1f 倍)" % (
             fold.sum(), 100 * fold.mean(), pf["irradiance"][fold].mean(), pf["irradiance"][fold].mean() / pf["irradiance"].mean()))
    gate("折り目から 3 画素以上離れた所では 2 方法がなお合う(15 % 以内)", rel_far < 0.15, "相対 RMS %.1f %%" % (100 * rel_far))
    h5 = surf(0.05)
    d4 = WV.caustic_irradiance(h5, 4.0, 1.0, (20.0, 0.0), ray_density=4)["irradiance"]
    d8 = WV.caustic_irradiance(h5, 4.0, 1.0, (20.0, 0.0), ray_density=8)["irradiance"]
    dd = float(np.sqrt(np.mean((d4 - d8) ** 2)) / d8.mean())
    gate("光線密度を 2 倍(4 → 8)にして光子の結果が 1 % 未満しか動かない", dd < 0.01, "相対 RMS %.2f %%" % (100 * dd))
    NUMBERS["density_doubling"] = dd
    # (c) コースティクス分割
    seg = {w: WV.caustic_floor_segmentation(r["irradiance"], "otsu") for w, r in res.items()}
    for w, s in seg.items():
        print("   風速 %g m/s: 分割(Otsu)で床の %.0f %% が明るい線・網" % (w, 100 * s["fraction"]))
    wave = WV.caustic_irradiance(0.01 * np.sin(2 * np.pi * 5 * np.tile(np.arange(64) * 4.0 / 64, (64, 1)) / 4.0), 4.0, 1.0, (0.0, 0.0))["irradiance"]
    sw = {m: WV.caustic_floor_segmentation(wave, m) for m in ("otsu", "fold")}
    gate("1 本の正弦波の光子結果: 分割した線の周期が波の周期(64 / 5 画素)に 2 % 以内(otsu・fold)",
         all(abs(s["period_px_x"] / (64 / 5) - 1) < 0.02 for s in sw.values()) and len(sw) == 2,
         "otsu %.3f、fold %.3f 画素(真値 %.3f)" % (sw["otsu"]["period_px_x"], sw["fold"]["period_px_x"], 64 / 5))
    # (d) ひび割れ
    n = 256
    _, crack = defectgen.defect_crack(shape=(n, n), length_px=150, width_px=3.0, angle_deg=70, seed=3)
    crack = crack.astype(bool)
    alb = 0.55 * (1 + 0.03 * np.random.default_rng(1).standard_normal((n, n)))
    alb = np.where(crack, alb * 0.4, alb)
    rows = {}
    for w in (3.0, 6.0):
        e = res[w]["irradiance"]
        floor = alb * e
        det_flat = CANNY(alb, 0.4, 0.3) > 0.5
        det = CANNY(floor, 0.4, 0.3) > 0.5
        masked = det & ~ndimage.binary_dilation(seg[w]["mask"], iterations=3)
        flatfield = CANNY(floor / e, 0.4, 0.3) > 0.5
        rows[w] = {"floor": floor, "det": det, "masked": masked, "flatfield": flatfield, "flat": det_flat,
                   "p_flat": pr(det_flat, crack), "p_det": pr(det, crack), "p_masked": pr(masked, crack), "p_ff": pr(flatfield, crack)}
        print("   風速 %g m/s: 適合率 / 再現率  コースティクス無し %.2f / %.2f、有り %.2f / %.2f、分割で除く %.2f / %.2f、照度で割る %.2f / %.2f(検出 %d → %d 画素)" % (
            w, *rows[w]["p_flat"], *rows[w]["p_det"], *rows[w]["p_masked"], *rows[w]["p_ff"], det.sum(), masked.sum()))
    r3_ = rows[3.0]
    gate("3 m/s: 検出器は影の無い板では適合率 1.00・再現率 1.00",
         r3_["p_flat"][0] > 0.99 and r3_["p_flat"][1] > 0.99, "%.2f / %.2f" % r3_["p_flat"])
    gate("3 m/s: コースティクスの縁で適合率が 0.2 未満に落ちる(再現率は 1.0)",
         r3_["p_det"][0] < 0.2 and r3_["p_det"][1] > 0.95, "適合率 %.3f、再現率 %.2f" % r3_["p_det"])
    gate("3 m/s: コースティクスの分割で縁を除くと適合率が 0.9 を超える(再現率は下がる)",
         r3_["p_masked"][0] > 0.9 and r3_["p_masked"][1] < r3_["p_det"][1], "適合率 %.2f → %.2f、再現率 %.2f → %.2f" % (
             r3_["p_det"][0], r3_["p_masked"][0], r3_["p_det"][1], r3_["p_masked"][1]))
    r6 = rows[6.0]
    gate("6 m/s: 相対しきい値の検出器はコースティクスの勾配に負けてひびを見失い、分割で除いても戻らない",
         r6["p_det"][1] < 0.3 and r6["p_masked"][1] < 0.3, "再現率 %.2f → %.2f" % (r6["p_det"][1], r6["p_masked"][1]))
    gate("6 m/s: 照度で割る(平坦化)とひびが戻る(適合率・再現率とも 0.95 以上)", r6["p_ff"][0] > 0.95 and r6["p_ff"][1] > 0.95,
         "%.2f / %.2f" % r6["p_ff"])
    NUMBERS.update({"prec_before": r3_["p_det"][0], "prec_after": r3_["p_masked"][0], "rec_before": r3_["p_det"][1], "rec_after": r3_["p_masked"][1]})
    return {"res": res, "seg": seg, "rows": rows, "crack": crack, "photon": ph, "wavefront": wf, "pf": pf, "wff": wff, "wave": wave}


# --------------------------------------------------------------------------- #
# 2. 瓶                                                                         #
# --------------------------------------------------------------------------- #
PITCH = 100.0           # um
R_B, T_B, H_B, N_G, N_L = 30.0, 2.5, 150.0, 1.52, 1.333


def bottle(fill, light="backlight", pitch=PITCH, size=None, **kw):
    return WV.bottle_image(R_B, T_B, H_B, fill, N_G, N_L, pixel_pitch_um=pitch, light=light, size=size, **kw)


def band_half_width(img, c=None):
    row = img["image"][100]
    c = row.size // 2 if c is None else c
    x = img["x_mm"]
    return float(x[np.nonzero(row[c:] < 0.5 * row[c])[0][0] + c])


def paraxial_magnification(r_b, dc=500.0, na=1.0):
    """気泡の中心から前面の 2 つの面を通って針穴のカメラまでの近軸 2 × 2 行列で、気泡の輪郭の倍率を出す。"""
    Ri = R_B - T_B
    m = (np.array([[1, 0], [-(N_G - na) / R_B, 1]]) @ np.array([[1, T_B / N_G], [0, 1]])
         @ np.array([[1, 0], [-(N_L - N_G) / Ri, 1]]) @ np.array([[1, Ri / N_L], [0, 1]]))
    a, b, c, d = m[0, 0], m[0, 1], m[1, 0], m[1, 1]
    ll = dc - R_B
    p0 = -r_b * (a + ll * c / na) / (b + ll * d / na)
    return abs(a * r_b + b * p0) * dc / (dc - R_B) / r_b


def chapter_bottle():
    print("\n2. 水の入った瓶(円柱の断面を行ごとに追跡)")
    out = {}
    for light in ("backlight", "frontlight"):
        half, empty, full = bottle(0.5, light), bottle(0.0, light), bottle(1.0, light)
        k = half["fill_row_from_top"]
        gate("%s: 液面の上の行は空の断面、下の行は満の断面と bit 一致" % ("背面光" if light == "backlight" else "前面光"),
             k == 750 and np.array_equal(half["image"][:k], empty["image"][:k]) and np.array_equal(half["image"][k:], full["image"][k:]),
             "液面の行 %d(round(0.5 × %.0f / %.2f) = %d)" % (k, H_B, PITCH / 1000, round(0.5 * H_B / (PITCH / 1000))))
        out[light] = (half, empty, full)
    e = bottle(0.0, size=(1500, 301))
    f = bottle(1.0, size=(1500, 301))
    ratio = float(f["image"][100, 150] / e["image"][100, 150])
    ta = 1 - ((1 - N_G) / (1 + N_G)) ** 2
    tl = 1 - ((N_G - N_L) / (N_G + N_L)) ** 2
    gate("中央の明るさの比(満 / 空)が 4 界面のフレネル透過率の積の比に 1e-9", abs(ratio / (tl ** 2 / ta ** 2) - 1) < 1e-9,
         "測定 %.6f、閉形式 %.6f(空 %.4f、満 %.4f)" % (ratio, tl ** 2 / ta ** 2, e["image"][100, 150], f["image"][100, 150]))
    hw, pred = band_half_width(f), f["band_half_width_mm_paraxial"]
    gate("満の断面の明るい帯の半幅が、近軸焦点(%.2f mm)からの予測 α / (1/f − 1/d) に 15 %% 以内" % f["paraxial_efl_mm"], abs(hw / pred - 1) < 0.15,
         "測定 %.2f mm、予測 %.2f mm(%.1f %%、球面収差で帯は予測より狭い)" % (hw, pred, 100 * (hw / pred - 1)))
    lit_e = int((e["image"][100] > 0.5 * e["image"][100, 150]).sum())
    lit_f = int((f["image"][100] > 0.5 * f["image"][100, 150]).sum())
    gate("空の断面は縁近くまで明るく、満の断面は中央の帯だけ(明るい画素数 空 %d、満 %d)" % (lit_e, lit_f), lit_e > 1.5 * lit_f)
    NUMBERS.update({"band_measured": hw, "band_pred": pred, "ratio": ratio})
    # 液面
    errs, rows_ok = [], []
    fills = (0.15, 0.33, 0.5, 0.72, 0.9)
    for light in ("backlight", "frontlight"):
        for fl in fills:
            im = bottle(fl, light)
            lv = WV.fill_level_from_image(im["image"], PITCH, "edge")
            lv2 = WV.fill_level_from_image(im["image"], PITCH, "brightness")
            errs.append(max(abs(lv["row"] - im["fill_row_from_top"]), abs(lv2["row"] - im["fill_row_from_top"])))
            rows_ok.append(abs(im["liquid_rows"] - round(fl * H_B / (PITCH / 1000))))
    gate("液面の行が round(充填率 × 高さ / 画素) ± 1、5 つの充填 × 2 つの照明で測った液面(edge・brightness)が 1 画素以内",
         len(errs) == 10 and max(errs) <= 1 and max(rows_ok) <= 1, "最大の差 %d 画素 / 行数の差 %d" % (max(errs), max(rows_ok)))
    refuse_const = refused(lambda: WV.fill_level_from_image(np.full((50, 20), 0.5), PITCH))
    refuse_full = refused(lambda: WV.fill_level_from_image(bottle(1.0)["image"], PITCH))
    gate("定数の画像と、液面の無い画像(満・空)は拒否", refuse_const and refuse_full)
    # 気泡
    pitch = 50.0
    rb, zb = 1.0, 60.0
    bi = bottle(0.5, pitch=pitch, bubbles=[(0.0, zb, rb)])
    j = int(round((H_B - zb) / (pitch / 1000) - 0.5))
    row = bi["image"][j]
    x = bi["x_mm"]
    plate = float(np.median(row[np.abs(x) < 6.0]))
    dark = np.nonzero((row < 0.5 * plate) & (np.abs(x) < 4.0))[0]
    d_px = int(dark.max() - dark.min() + 1)
    mag = paraxial_magnification(rb)
    expect = 2 * rb * mag / (pitch / 1000)
    gate("気泡(半径 %.1f mm)の暗い輪の外径が 2 r × 倍率(近軸の行列 %.4f)に ± 1 画素" % (rb, mag), abs(d_px - expect) <= 1.0,
         "測定 %d 画素、予測 %.1f 画素(倍率 1 なら %.0f 画素 ―― 水入りの円柱は軸上の物を約 n 倍に見せる)" % (d_px, expect, 2 * rb / (pitch / 1000)))
    mx = max(float(WV.bottle_image(R_B, T_B, H_B, fl, N_G, N_L, meniscus_mm=m_, pixel_pitch_um=250.0, bubbles=bb)["image"].max())
             for fl, m_, bb in ((0.0, 0.0, None), (0.6, 4.0, [(0.0, 50.0, 2.0)]), (1.0, 0.0, None)))
    gate("どの画素も背面板の放射輝度 1 を超えない(気泡・メニスカスつきでも)", mx <= 1 + 1e-9, "最大 %.9f" % mx)
    gate("拒否: n ≤ 1・充填率 1.1・壁が半径以上・液面の上の気泡",
         all(refused(f_) for f_ in (lambda: WV.bottle_image(30, 2.5, 150, 0.5, 1.0, 1.333), lambda: WV.bottle_image(30, 2.5, 150, 0.5, 1.52, 0.9),
                                    lambda: WV.bottle_image(30, 2.5, 150, 1.1, 1.52, 1.333), lambda: WV.bottle_image(30, 30, 150, 0.5, 1.52, 1.333),
                                    lambda: WV.bottle_image(30, 2.5, 150, 0.5, 1.52, 1.333, bubbles=[(0, 120, 1.0)]))))
    out["bubble_row"] = (bi, j, dark, d_px, expect)
    out["empty_full"] = (e, f)
    return out


def tilt_limit():
    """限界: カメラから縦に離れた行の光線は断面から傾く。垂直な円柱では実効屈折率に置き換えて厳密に扱える。"""
    print("\n5. 限界: 断面ごとの追跡は縦の傾きを無視する")
    alphas = np.array([0.0, 4.0, 8.5, 15.0, 25.0, 40.0])
    bands = []
    for a in alphas:
        s = math.sin(math.radians(a))
        c = math.cos(math.radians(a))
        ng = math.sqrt(N_G ** 2 - s * s) / c
        nl = math.sqrt(N_L ** 2 - s * s) / c
        im = WV.bottle_image(R_B, T_B, H_B, 1.0, ng, nl, pixel_pitch_um=200.0, size=(8, 601))
        row = im["image"][4]
        x = im["x_mm"]
        c0 = row.size // 2
        bands.append(float(x[np.nonzero(row[c0:] < 0.5 * row[c0])[0][0] + c0]))
    bands = np.array(bands)
    a_max = math.degrees(math.atan(0.5 * H_B / 500.0))
    dev = bands / bands[0] - 1
    print("   縦の傾き α = %s 度の明るい帯の半幅 %s mm(0 度との差 %s %%)" % (
        ", ".join("%g" % a for a in alphas), ", ".join("%.2f" % b for b in bands), ", ".join("%+.1f" % (100 * d) for d in dev)))
    print("   本設定(カメラ 500 mm、高さ 150 mm)の最大の傾きは %.1f 度: 帯の半幅は %.1f %% 動く。肩(半径の変わる所)ではこの置き換えも使えず、3 次元の追跡が要る" % (
        a_max, 100 * abs(float(np.interp(a_max, alphas, dev)))))
    gate("傾きが大きいほど帯が狭まる(単調: 実効屈折率が上がり焦点が近づく)、傾き 40 度では 0 度より 10 % 以上動く ―― 2 次元の追跡の限界を数で示す",
         bool(np.all(np.diff(bands) <= 0)) and dev[-1] < -0.10, "40 度で %+.1f %%" % (100 * dev[-1]))
    return alphas, bands


# --------------------------------------------------------------------------- #
# 3. 濡れた面                                                                    #
# --------------------------------------------------------------------------- #
def r_internal_quad(n):
    from scipy.integrate import quad
    thc = math.asin(1.0 / n)
    inner, _ = quad(lambda t: 2.0 * (1.0 - fresnel_t(t, n, 1.0)) * math.sin(t) * math.cos(t), 0.0, thc, epsabs=1e-13, epsrel=1e-13)
    return inner + (1.0 - 1.0 / (n * n))


def make_plate(n=160):
    rng = np.random.default_rng(7)
    streak = ndimage.gaussian_filter(rng.standard_normal((n, n)), (0.6, 6.0))
    tex = np.clip(0.60 + 0.5 * streak / streak.std() * 0.03, 0, 1)
    _, scr = defectgen.defect_scratch(shape=(n, n), length_px=110, width_px=4.0, angle_deg=20, seed=2)
    scr = scr.astype(bool)
    tex = np.where(scr, 0.25, tex)
    return tex, scr


def chapter_wet():
    print("\n3. 濡れた面(Lekner & Dorf 1988)")
    a0 = np.array([0.0, 0.1, 0.5, 0.9, 1.0])
    z = WV.wet_surface_appearance(a0, 0.3, 0.0, 30.0, 40.0)
    gate("膜 0 では反照率が変わらない(1e-12)", float(np.abs(z["wet_albedo"] - a0).max()) <= 1e-12, "最大の差 %.1e" % np.abs(z["wet_albedo"] - a0).max())
    ld = 35.0
    errs = []
    for a in (0.05, 0.2, 0.5, 0.8, 0.95):
        r = WV.wet_surface_appearance(a, 0.2, 100.0, 20.0, ld)
        rbar = r_internal_quad(N_W)
        rs = 1 - fresnel_t(math.radians(ld), 1.0, N_W)
        errs.append(abs(float(r["wet_albedo"]) - a * (1 - rs) * (1 - rbar) / (1 - a * rbar)))
    gate("朗伯面の濡れた反照率が a (1 − R_s)(1 − r) / (1 − a r) に、独立の数値積分(quad)の r で 1e-6", len(errs) == 5 and max(errs) < 1e-6,
         "最大の差 %.1e(r = %.6f、操作側 %.6f)" % (max(errs), r_internal_quad(N_W), WV.wet_surface_appearance(0.5, 0.2, 100.0, 20.0, ld)["internal_reflectance_mean"]))
    a = np.linspace(0.01, 0.99, 99)
    wet = WV.wet_surface_appearance(a, 0.2, 50.0, 20.0, 30.0)
    half = float(WV.wet_surface_appearance(0.5, 0.2, 50.0, 20.0, 30.0)["ratio"])
    gate("どの反照率でも濡れは乾より暗く(99 点)、暗い面ほど相対的に大きく暗くなる", a.size == 99 and bool((wet["wet_albedo"] < a).all()) and bool((np.diff(wet["ratio"]) > 0).all()),
         "a = 0.5 で濡れ / 乾 = %.3f(約 3 分の 1 の損)、a = 0.1 で %.3f、a = 0.9 で %.3f" % (
             half, float(WV.wet_surface_appearance(0.1, 0.2, 50.0, 20.0, 30.0)["ratio"]), float(WV.wet_surface_appearance(0.9, 0.2, 50.0, 20.0, 30.0)["ratio"])))
    NUMBERS["ratio_half"] = half
    tex, scr = make_plate()
    pair = WV.wet_dry_inspection_pair(tex, scr, 0.3, 20.0, 40.0, 40.0)
    print("   欠陥のコントラスト(Michelson): 拡散のみ 乾 %.4f → 濡れ %.4f(予測 %.4f)、全体 乾 %.4f → 濡れ %.4f、てかり画素 %d → %d" % (
        pair["contrast_diffuse_dry"], pair["contrast_diffuse_wet"], pair["predicted_diffuse_contrast_wet"], pair["contrast_dry"], pair["contrast_wet"],
        pair["glint_pixels_dry"], pair["glint_pixels_wet"]))
    gate("欠陥のコントラストが予測の向きに動く(暗い傷は濡れると拡散のコントラストが増す、予測値に 1 % 以内、全体も同じ向き)",
         pair["contrast_diffuse_wet"] > pair["contrast_diffuse_dry"] and abs(pair["contrast_diffuse_wet"] / pair["predicted_diffuse_contrast_wet"] - 1) < 0.01
         and pair["contrast_wet"] > pair["contrast_dry"],
         "拡散 %.4f → %.4f、全体 %.4f → %.4f" % (pair["contrast_diffuse_dry"], pair["contrast_diffuse_wet"], pair["contrast_dry"], pair["contrast_wet"]))
    zero = WV.wet_dry_inspection_pair(tex, scr, 0.3, 0.0, 40.0, 40.0)
    gate("膜 0 では乾と濡れの画像が同一", np.array_equal(zero["dry"], zero["wet"]))
    lights = (20.0, 40.0, 60.0)
    pairs = {la: WV.wet_dry_inspection_pair(tex, scr, 0.25, 20.0, la, 40.0, normal_sigma_px=10.0) for la in lights}
    g = {la: p["specular_wet"] > 0.5 for la, p in pairs.items()}
    ov = (g[20.0] & g[60.0]).sum() / max(min(g[20.0].sum(), g[60.0].sum()), 1)
    gate("照明角を 20° → 60° に動かすと、てかりの出る画素が入れ替わる(重なり 50 % 未満)", g[20.0].sum() > 0 and g[60.0].sum() > 0 and ov < 0.5,
         "てかり画素 %d・%d・%d、重なり %.0f %%" % (g[20.0].sum(), g[40.0].sum(), g[60.0].sum(), 100 * ov))
    return {"pair": pair, "pairs": pairs, "tex": tex, "scr": scr, "a": a, "wet": wet}


# --------------------------------------------------------------------------- #
# 4. 船体と水中のランプ                                                          #
# --------------------------------------------------------------------------- #
def make_hull(h=96, w=144):
    yy, xx = np.mgrid[0:h, 0:w]
    base = 0.55 + 0.04 * np.sin(xx / 5.0) * np.cos(yy / 7.0)
    weld = ((yy % 32) < 2) | ((xx % 48) < 2)
    rust = (np.hypot(xx - 100, yy - 30) < 14)
    albedo = np.where(weld, 0.2, base)
    albedo = np.where(rust, 0.32, albedo)
    letters = ((xx > 20) & (xx < 26) & (yy > 52) & (yy < 80)) | ((xx > 26) & (xx < 40) & (yy > 52) & (yy < 58)) | ((xx > 34) & (xx < 40) & (yy > 52) & (yy < 80)) | ((xx > 26) & (xx < 40) & (yy > 64) & (yy < 70))
    albedo = np.where(letters, 0.9, albedo)
    return albedo


def chapter_hull():
    print("\n4. 船体の検査(ランプはカメラの横)")
    alb = make_hull()
    h, w = alb.shape
    u = np.linspace(-1, 1, w)[None, :] + np.zeros((h, 1))
    out = {}
    for water in ("jerlov_I", "jerlov_3C"):
        for d0 in (1.0, 3.0, 6.0):
            dist = d0 * (1.0 + 0.15 * u)
            out[(water, d0)] = WV.underwater_inspection_image(alb, dist, water)
    for water in ("jerlov_I", "jerlov_3C"):
        snr_c = [float(out[(water, d)]["snr_mean"][h // 2, w // 2]) for d in (1.0, 3.0, 6.0)]
        print("   %s: 中央の SNR  1 m %.1f、3 m %.1f、6 m %.2f   中央 / 隅のベール %.2f 倍" % (
            water, *snr_c, float(out[(water, 3.0)]["backscatter"][h // 2, w // 2, 1] / out[(water, 3.0)]["backscatter"][0, 0, 1])))
    gate("SNR は距離で単調に落ちる(0.5〜6 m の 8 点、純水・I・3C)",
         all(bool(np.all(np.diff([float(WV.underwater_inspection_image(np.full((9, 9), 0.6), np.full((9, 9), x), wt)["snr"][4, 4, 1])
                                  for x in (0.5, 1, 1.5, 2, 3, 4, 5, 6)]) < 0)) for wt in ("pure", "jerlov_I", "jerlov_3C")))
    r0 = WV.underwater_inspection_image(np.random.default_rng(1).random((6, 6)), np.full((6, 6), 1e-10), "pure")
    gate("純水で距離 → 0 は澄んだ水の場合に 1e-9", float(np.abs(r0["snr"] / r0["snr_clear"] - 1).max()) < 1e-9, "最大 %.1e" % np.abs(r0["snr"] / r0["snr_clear"] - 1).max())
    a3, d3 = np.random.default_rng(2).random((20, 30, 3)), 1.5 + 3 * np.random.default_rng(3).random((20, 30))
    r = WV.underwater_inspection_image(a3, d3, "jerlov_II")
    att = WM.water_attenuation(np.array(WM.RGB_WAVELENGTHS_UM), "jerlov_II")
    cf = a3 * np.exp(-d3[..., None] * att["c"]) / d3[..., None] ** 2 * np.exp(-d3[..., None] * att["kd"])
    gate("直接光が閉形式 albedo · exp(−c r) / r² · exp(−Kd r) に一致(1e-12)", float(np.abs(r["direct"] - cf).max() / cf.max()) < 1e-12)
    s3 = out[("jerlov_3C", 3.0)]
    gate("中央のベールが隅より強く、3C の 3 m の SNR は中央 < 隅", s3["backscatter"][h // 2, w // 2, 1] > 1.5 * s3["backscatter"][0, 0, 1]
         and s3["snr"][h // 2, w // 2, 1] < s3["snr"][0, 0, 1],
         "ベール 中央 %.4f、隅 %.4f" % (s3["backscatter"][h // 2, w // 2, 1], s3["backscatter"][0, 0, 1]))
    gate("同じ距離で濁った水(3C)の SNR は外洋(I)より低い(1・3・6 m)",
         all(float(out[("jerlov_3C", d)]["snr_mean"].mean()) < float(out[("jerlov_I", d)]["snr_mean"].mean()) for d in (1.0, 3.0, 6.0)))
    return out, alb


# --------------------------------------------------------------------------- #
# 壊して確かめる                                                                  #
# --------------------------------------------------------------------------- #
def chapter_probes():
    print("\n6. 壊して確かめる(門が赤になる/拒否される)")
    seas = make_sea(3.0, 0.06, n=64)
    a = WV.caustic_irradiance(seas, POOL_L, POOL_DEPTH, (0.0, 0.0))["irradiance"]
    b = WV.caustic_irradiance(seas, POOL_L, POOL_DEPTH, (0.0, 0.0), n_water=1.45)["irradiance"]
    gate("屈折率 1.45 の水では照度が 1 % 以上動く(密度の門・平面の門が赤)", float(np.sqrt(np.mean((a - b) ** 2)) / a.mean()) > 0.01)
    gate("気泡の倍率を 1 と仮定すると外径が ± 1 画素から外れる(門は赤)", abs(2 * 1.0 / 0.05 - 2 * 1.0 * paraxial_magnification(1.0) / 0.05) > 5)
    r = WV.wet_surface_appearance(0.5, 0.2, 100.0, 30.0, 30.0)
    gate("内部反射 r = 0 とすると a = 0.5 の比が 0.67 から外れる(門は赤)", abs(float(r["ratio"]) - (1.0 - r["fresnel_light"])) > 0.2)
    gate("拒否: 非有限の高さ・波頭より浅い底・albedo 1.5・距離 0・定数の照度",
         all(refused(f_) for f_ in (lambda: WV.caustic_irradiance(np.full((8, 8), np.nan), 1.0, 1.0, (0.0, 0.0)),
                                    lambda: WV.caustic_irradiance(np.full((8, 8), 2.0), 1.0, 1.0, (0.0, 0.0)),
                                    lambda: WV.wet_surface_appearance(1.5, 0.2, 10.0, 30.0, 30.0),
                                    lambda: WV.underwater_inspection_image(np.full((4, 4), 0.5), np.zeros((4, 4)), "pure"),
                                    lambda: WV.caustic_floor_segmentation(np.ones((16, 16))))))


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(pool, bot, wet, hull, tilt, bottle_small):
    res, seg, rows = pool["res"], pool["seg"], pool["rows"]
    e3, e6 = res[3.0]["irradiance"], res[6.0]["irradiance"]
    figs.save_grid("pool_caustics", [e3, seg[3.0]["mask"].astype(float), e6, seg[6.0]["mask"].astype(float)], gray=True, ncols=2,
                   vrange=[(0.0, 3.0), (0, 1), (0.0, 3.0), (0, 1)],
                   captions=["風速 3 m/s の底の照度(白 = 3 倍)", "分割(Otsu)の明るい線", "風速 6 m/s の底の照度", "分割(Otsu)"],
                   title="深さ 1 m のプールの底: 波が作る明るい網(6 m 四方、真上からの光)",
                   caption="照度の最大 %.1f 倍(3 m/s)・%.1f 倍(6 m/s)。分割は床の %.0f %%・%.0f %%。傾きの RMS は手で 0.06・0.10 に合わせた。" % (
                       e3.max(), e6.max(), 100 * seg[3.0]["fraction"], 100 * seg[6.0]["fraction"]))
    r3, r6 = rows[3.0], rows[6.0]
    figs.save_grid("crack_detector", [r3["floor"], r3["det"].astype(float), r3["masked"].astype(float), r6["floor"], r6["det"].astype(float), r6["flatfield"].astype(float)],
                   gray=True, ncols=3,
                   captions=["3 m/s の底(板 × 照度、ひび 1 本)", "検出器 canny(適合率 %.2f)" % r3["p_det"][0], "分割で縁を除く(適合率 %.2f、再現率 %.2f)" % r3["p_masked"],
                             "6 m/s の底", "検出器(再現率 %.2f: ひびを見失う)" % r6["p_det"][1], "照度で割ってから(%.2f / %.2f)" % r6["p_ff"]],
                   title="ひび割れ検出器はコースティクスの縁をひびと取り違える", caption="上: 3 m/s は分割で縁を除くと適合率が戻る。下: 6 m/s は縁の勾配がひびに勝ち、除いても戻らない ―― 照度で割ると戻る。")
    ph, wf, pf, wff = pool["photon"], pool["wavefront"], pool["pf"], pool["wff"]
    clip = np.where(np.isfinite(wff["irradiance"]), wff["irradiance"], 6.0)
    figs.save_grid("two_methods", [pf["irradiance"], clip, wff["fold_mask"].astype(float)], gray=True, ncols=3, vrange=[(0, 6.0), (0, 6.0), (0, 1)],
                   captions=["光子(波高 0.2 m の面)", "ヤコビアン(inf は白)", "折り目(波面法が旗を出す所)"],
                   title="2 つの方法は折り目でだけ食い違う", caption="光子は折り目で有限の大きな値を数え、波面法は幾何学的な利得が無限になる所を inf にして旗で知らせる。")
    # 瓶
    sm = bottle_small
    panels, caps = [], []
    for light, nm in (("backlight", "背面光"), ("frontlight", "前面光")):
        for key, lab in (("empty", "空"), ("half", "半分"), ("full", "満"), ("bub", "気泡 3 つ")):
            panels.append(sm[(light, key)]["image"])
            caps.append("%s・%s" % (nm, lab))
    figs.save_grid("bottles", panels, gray=True, ncols=4, vrange=(0.0, 1.0), captions=caps,
                   title="円柱の断面を追跡した瓶の側面像(半径 30 mm、n = 1.52、水 1.333)",
                   caption="背面光: 満の部分は中央の帯だけが明るく、空の部分は縁近くまで明るい。気泡は暗い輪(中央は細く明るい)。前面光は壁の映り込み(右の縦の筋)が出る。")
    e, f = bot["empty_full"]
    x = f["x_mm"]
    series = [("空の断面", x, e["image"][100]), ("満の断面", x, f["image"][100])]
    pred = f["band_half_width_mm_paraxial"]
    series.append(("近軸焦点からの帯の予測 ±%.1f mm" % pred, np.array([-pred, -pred]), np.array([0.0, 1.0])))
    series.append(("", np.array([pred, pred]), np.array([0.0, 1.0])))
    figs.save_plot("focal_band", series, xlabel="画像の横位置 x [mm]", ylabel="背面光の明るさ", colors=["reference", "emphasis", "right", "right"], styles=[None, None, "dashed", "dashed"],
                   size=(700, 380), title="満の瓶では中央の帯だけが明るい(測定 ±%.1f mm、予測 ±%.1f mm)" % (NUMBERS["band_measured"], NUMBERS["band_pred"]),
                   caption="空の瓶は縁近くまで明るい。液体のある所だけ円柱レンズになり、光が光軸の方へ曲がって背面板の外れる光線が縁に出る。")
    bi, j, dark, d_px, expect = bot["bubble_row"]
    xb = bi["x_mm"]
    sel = np.abs(xb) < 3.0
    series = [("気泡のある行", xb[sel], bi["image"][j][sel]),
              ("輪の外径(測定 %d 画素)" % d_px, np.array([xb[dark.min()], xb[dark.min()]]), np.array([0.0, 1.0])),
              ("", np.array([xb[dark.max()], xb[dark.max()]]), np.array([0.0, 1.0]))]
    figs.save_plot("bubble_ring", series, xlabel="画像の横位置 x [mm]", ylabel="背面光の明るさ", colors=["emphasis", "right", "right"], styles=[None, "dashed", "dashed"], size=(640, 360),
                   title="気泡の輪: 外径は 2 r × 近軸の倍率(予測 %.1f 画素)" % expect,
                   caption="半径 1 mm の気泡。水入りの円柱は軸上の物を約 1.33 倍に見せるので、輪は 2 mm でなく 2.67 mm 幅。")
    alphas, bands = tilt
    figs.save_plot("limit_tilt", [("明るい帯の半幅(実効屈折率で厳密)", alphas, bands), ("傾き 0 度(本設定の追跡)", alphas, np.full_like(alphas, bands[0]))],
                   xlabel="光線の縦の傾き α [度]", ylabel="帯の半幅 [mm]", colors=["wrong", "reference"], styles=[None, "dashed"], size=(640, 360),
                   title="限界: 断面だけの追跡は縦に傾いた光線を無視する(本設定の最大 %.1f 度、肩では 40 度以上)" % math.degrees(math.atan(75.0 / 500.0)),
                   caption="垂直な円柱の傾きは n → sqrt(n² − sin²α) で厳密に扱える。肩の曲面ではこれも使えない。")
    # 濡れた板
    pair, pairs, tex, scr = wet["pair"], wet["pairs"], wet["tex"], wet["scr"]
    figs.save_grid("wet_dry_plate", [pair["dry"], pair["wet"], pair["diffuse_dry"], pair["diffuse_wet"]], gray=True, ncols=2, vrange=(0.0, 1.2),
                   captions=["乾いた板(拡散 + てかり)", "濡れた板(膜 20 µm)", "乾・拡散のみ(傷のコントラスト %.3f)" % pair["contrast_diffuse_dry"], "濡れ・拡散のみ(%.3f)" % pair["contrast_diffuse_wet"]],
                   title="同じ板を乾湿で描く: 濡れると暗くなり、暗い傷はむしろ目立つ",
                   caption="全体のコントラスト %.3f → %.3f。濡れ膜は粗さを埋めててかりの画素を減らし(%d → %d)、傷の拡散コントラストを %.3f → %.3f に上げる。" % (
                       pair["contrast_dry"], pair["contrast_wet"], pair["glint_pixels_dry"], pair["glint_pixels_wet"], pair["contrast_diffuse_dry"], pair["contrast_diffuse_wet"]))
    figs.save_grid("highlight_moves", [pairs[la]["specular_wet"] for la in (20.0, 40.0, 60.0)], gray=True, ncols=3, vrange=(0.0, 2.0),
                   captions=["照明 20°(視線 40°)", "照明 40°(鏡面)", "照明 60°"], title="濡れた板のてかり(鏡面成分): 照明角を変えると光る小面が入れ替わる",
                   caption="粗さ 0.25・なだらかな法線(10 画素)の板。局所の法線が照明と視線の二等分線に合った小面だけが光り、照明角とともに光る場所が移る(光る画素 %d・%d・%d)。" % tuple(int((pairs[la]["specular_wet"] > 0.5).sum()) for la in (20.0, 40.0, 60.0)))
    a, wetr = wet["a"], wet["wet"]
    figs.save_plot("wet_ratio", [("濡れ / 乾(Lekner & Dorf)", a, wetr["ratio"]), ("膜なし = 1", a, np.ones_like(a))], xlabel="乾いた反照率 a", ylabel="濡れた反照率 / 乾いた反照率",
                   colors=["emphasis", "reference"], styles=[None, "dashed"], size=(640, 360), title="濡れるとなぜ暗いか: 暗い面ほど大きく暗くなる(a = 0.5 で %.2f)" % NUMBERS["ratio_half"],
                   caption="内部反射 r = %.3f の水–空気界面が光を膜に閉じ込め、基板に吸わせる。" % WV.wet_surface_appearance(0.5, 0.2, 50.0, 20.0, 30.0)["internal_reflectance_mean"])
    # 船体
    out, alb = hull
    keys = [(w, d) for w in ("jerlov_I", "jerlov_3C") for d in (1.0, 3.0, 6.0)]
    imgs, caps_i = [], []
    for k in keys:
        im = out[k]["image"]
        imgs.append(np.clip(im / max(float(im.max()), 1e-12), 0, 1) ** 0.6)
        caps_i.append("%s・%g m(最大 %.3g)" % ("I 型" if k[0].endswith("I") else "3C 型", k[1], float(im.max())))
    figs.save_grid("hull_images", imgs, ncols=3, captions=caps_i, title="船体の溶接線・錆・番号を、カメラの横のランプで 1・3・6 m から見る",
                   caption="各コマは最大を 1 にして見やすくした(露出は固定でなく、絶対の明るさは題に)。外洋は青に寄り、沿岸(3C)は黄緑に寄って、距離とともに霧のベールが乗る(6 m の沿岸はほぼベールだけ)。")
    snrs = [np.log10(np.clip(out[k]["snr_mean"], 1e-3, None)) for k in keys]
    figs.save_grid("hull_snr", snrs, gray=True, ncols=3, vrange=(-1.0, 2.5), captions=["SNR %s・%g m(中央 %.1f)" % ("I" if k[0].endswith("I") else "3C", k[1], float(out[k]["snr_mean"][48, 72])) for k in keys],  # gray-ok: 距離別の光学像だが画素値は SNR であり距離場ではない
                   title="画素ごとの SNR(log10、白 = 316): 距離で落ち、中央のベールで中央が最も悪い",
                   caption="SNR = √N · 直接光 / √(直接光 + ベール + 1e-12)。ランプの後方散乱の体積はカメラの視野の中央で最も重なる。")


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 水が検査画像にどう写るか(予算 %s)" % ("reduced" if REDUCED else "full"))
    pool = chapter_pool()
    bot = chapter_bottle()
    wet = chapter_wet()
    hull = chapter_hull()
    tilt = tilt_limit()
    chapter_probes()
    if not REDUCED and figs.target_dir() is not None:
        small = {}
        for light in ("backlight", "frontlight"):
            small[(light, "empty")] = bottle(0.0, light, pitch=250.0, size=(600, 276))
            small[(light, "half")] = bottle(0.5, light, pitch=250.0, size=(600, 276))
            small[(light, "full")] = bottle(1.0, light, pitch=250.0, size=(600, 276))
            small[(light, "bub")] = bottle(0.5, light, pitch=250.0, size=(600, 276), bubbles=[(0.0, 60.0, 1.5), (8.0, 40.0, 2.0), (-8.0, 50.0, 2.5)])
        make_figures(pool, bot, wet, hull, tilt, small)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    print("数字: 適合率 %.3f → %.3f(再現率 %.2f → %.2f)、帯 %.2f / %.2f mm、比 %.4f、a = 0.5 の濡れ / 乾 %.3f、方法の差 %.2f %%、密度 2 倍 %.2f %%" % (
        NUMBERS["prec_before"], NUMBERS["prec_after"], NUMBERS["rec_before"], NUMBERS["rec_after"], NUMBERS["band_measured"], NUMBERS["band_pred"], NUMBERS["ratio"],
        NUMBERS["ratio_half"], 100 * NUMBERS["rel_methods"], 100 * NUMBERS["density_doubling"]))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
