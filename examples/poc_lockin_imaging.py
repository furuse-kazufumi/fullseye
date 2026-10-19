# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 画素ごとの直交復調(ロックイン)―― 変調した光や熱に追従する成分だけを、振幅・位相・直流の 3 枚に取り出す。

【問い】時間相関イメージセンサ(画素ごとに、変調した照明と同期した参照信号との相関を取るセンサ)は、普通のカメラが
苦手なことを 3 つしてきた: (a) 光の向きを変調した輪の照明で面の傾き(法線)と凹凸を、反射率の模様に邪魔されずに読む、
(b) 符号で断続する照明だけを昼間の光から取り出す、(c) 周期加熱の熱波の遅れから内部の欠陥の深さを読む。
どれも「画像列に対する画素ごとの直交復調」で、新 op 9 本(`lockin`、`opsoptics` の `lockin`)に切り出して 3 つを同じ関数の
変種として示す。対象は ViEW2010『多重極変調リング照明と時間相関イメージセンサを用いた表面欠陥検査』、
ViEW2010『時間相関イメージセンサによる三次元計測』、ViEW2014『時間相関技術の塗装検査への応用』、
ViEW2016『符号化間歇照明に基づく照明識別と昼間化画像処理』が扱う題材で、式は自前で書いた(本文・図・表は写していない)。

  1. **閉形式**: 正弦の振幅・位相・直流が 1e-12 以内、参照の周波数をずらすと振幅は sinc で落ちる(0.5 が Δf·T = 0.60)。
     周期が整数でない長さは矩形窓では拒否し、窓の宣言(hann)なら漏れの大きさを表で返す。
  2. **雑音**: 白色雑音の下での位相の標準偏差が、SN 比から決まる閉形式(Rice の位相分布)と合う。
  3. **(a) 多重極変調リング**: 8 灯の輪の光の位相を方位角と一緒に 1 周させる(双極子)と、基本波の応答が
     (n_x − j n_y)·反射率·sinζ/2、直流が反射率·cosζ·n_z。比を取ると反射率が消えて法線が出る。門: 既知の法線(2 次曲面の解析的な勾配)
     に対する角度誤差、反射率の違う 3 つの条件で同じ。四重極は平坦でない朗伯面でも 0 になる(物体の向きに依らない成分の検査)。
  4. **(b) 符号化間歇照明**: 3 つの灯を Walsh 符号で断続し、昼間の光(直流・ゆっくりした増加・商用周波数のちらつき)の下で
     1 灯ずつの像に分ける。ちらつきは残差の画像に出る。
  5. **(c) ロックイン・サーモグラフィ**: 周期加熱した板の表面温度の厳密解 coth(σL)/σ(1 次元の熱伝導を別実装の有限体積で確認)から
     欠陥の深さを位相で読む。加熱ムラは振幅を壊すが位相には入らない。
  6. **壊して確かめる**: 参照を 10 % ずらす・天頂角を間違える・窓を宣言しない・符号が従属 → それぞれ門が赤になる/拒否される。

【外部真値】正弦の複素応答の閉形式(Dirichlet 核)、Rice の位相分布、2 次曲面の解析的な法線、熱波の厳密解(Carslaw & Jaeger)と
別実装の有限体積。手法: Breitenstein, Langenkamp 'Lock-in Thermography'(2003)/ Rice, Bell Syst. Tech. J. 24 (1945)。【学習】0。【較正】0。

★正直な限界: 法線の復元は朗伯面で影の無い画素(傾きが 90° − 天頂角 未満)だけ有効で、光沢や相互反射では式が崩れる。サーモグラフィは
定常状態の 1 次元モデルで、横拡散と立ち上がりの過渡は入れていない(実機では最初の数周期を捨てる)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import lockin as LK  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _cube(v):
    return np.tile(np.asarray(v, np.float64)[:, None, None], (1, 4, 4))


# --------------------------------------------------------------------------- #
# 1. 閉形式                                                                     #
# --------------------------------------------------------------------------- #
def chapter_closed_form():
    print("\n1. 閉形式(正弦・参照のずれ・窓)")
    n, fps = 1024, 1024.0
    k = np.arange(n)
    amp, ph, dc, p = 2.5, 0.7, 1.5, 64
    r = LK.lockin_demodulate(_cube(dc + amp * np.cos(2 * np.pi * p * k / n + ph)), p * fps / n, fps)
    e_a, e_p, e_d = abs(r["amplitude"][0, 0] - amp), abs(r["phase"][0, 0] - ph), abs(r["dc"][0, 0] - dc)
    print("   A = 2.5, φ = 0.7 rad, DC = 1.5 → 誤差 %.1e / %.1e / %.1e" % (e_a, e_p, e_d))
    gate("振幅・位相・直流は閉形式と 1e-12 以内", max(e_a, e_p, e_d) < 1e-12, "最大 %.1e" % max(e_a, e_p, e_d))
    same = (np.array_equal(LK.lockin_amplitude(_cube(dc + amp * np.cos(2 * np.pi * p * k / n + ph)), p * fps / n, fps), r["amplitude"]) and
            np.array_equal(LK.lockin_phase(_cube(dc + amp * np.cos(2 * np.pi * p * k / n + ph)), p * fps / n, fps), r["phase"]))
    gate("lockin_amplitude / lockin_phase は表の amplitude / phase と同じ画像", same)
    NUMBERS["closed_err"] = max(e_a, e_p, e_d)
    gains = {}
    for off in (0.2, 0.6033, 1.0, 1.5):
        x = np.cos(2 * np.pi * (p + off) * k / n)                       # 参照からの周波数のずれ = off / T
        gains[off] = LK.lockin_demodulate(_cube(x), p * fps / n, fps)["amplitude"][0, 0]
    sinc = {o: abs(math.sin(math.pi * o) / (math.pi * o)) for o in gains}
    worst = max(abs(gains[o] - sinc[o]) for o in gains)
    print("   Δf·T = 0.2 / 0.6033 / 1.0 / 1.5 の振幅: %s(sinc: %s)" % (
        ["%.4f" % gains[o] for o in gains], ["%.4f" % sinc[o] for o in gains]))
    gate("参照のずれに対する振幅は |sinc(Δf·T)| に 4e-3 以内(残りは共役側の像)", len(gains) == 4 and worst < 4e-3, "最大 %.1e" % worst)
    gate("Δf·T = 0.6033 で半分、1.0 で 0", abs(gains[0.6033] - 0.5) < 5e-3 and gains[1.0] < 3e-3)
    NUMBERS.update({"sinc_worst": worst, "gain_half": gains[0.6033]})
    # 窓の宣言
    short = _cube(dc + amp * np.cos(2 * np.pi * 4 * np.arange(60) / 64 + ph))          # 3.75 周期
    try:
        LK.lockin_demodulate(short, 4.0, 64.0)
        refused = False
    except ValueError as e:
        refused = "3.75" in str(e)
    rh = LK.lockin_demodulate(short, 4.0, 64.0, "hann")
    err = abs(rh["amplitude"][0, 0] - amp)
    bound = amp * rh["leak_image"] + 2 * dc * rh["leak_dc"]
    print("   3.75 周期: 矩形窓は拒否(%s)、hann は振幅誤差 %.4f(宣言した漏れの上限 %.4f)" % (refused, err, bound))
    gate("周期が整数でない長さは矩形窓で拒否、hann は漏れを表で宣言してその内に収まる", refused and 1e-4 < err <= bound + 1e-15,
         "誤差 %.4f ≤ 上限 %.4f" % (err, bound))
    NUMBERS.update({"hann_err": err, "hann_bound": bound})


# --------------------------------------------------------------------------- #
# 2. 雑音                                                                       #
# --------------------------------------------------------------------------- #
def chapter_noise():
    print("\n2. 雑音下の位相の標準偏差(SN 比から決まる閉形式)")
    n, fps, sigma = 64, 64.0, 1.0
    k = np.arange(n)[:, None, None]
    rows = []
    for amp, seed in ((8.0, 1), (2.0, 2), (0.3, 3)):
        rng = np.random.default_rng(seed)
        vid = amp * np.cos(2 * np.pi * 4 * k / n + 0.4) + rng.normal(0.0, sigma, (n, 160, 160))
        r = LK.lockin_demodulate(vid, 4.0, fps)
        sd = float(np.std(np.angle(np.exp(1j * (r["phase"] - 0.4)))))
        cf = LK.lockin_noise_floor(n, sigma, amp)
        rows.append((amp, cf["snr_component"], sd, cf["phase_std_exact"], cf["phase_std_small_noise"]))
        print("   A = %.1f(成分の SN 比 %5.2f): 実測 %.4f rad、閉形式(Rice)%.4f、小雑音近似 %.4f" % (
            amp, cf["snr_component"], sd, cf["phase_std_exact"], cf["phase_std_small_noise"]))
    gate("3 つの SN 比で位相の標準偏差が閉形式と 3 % 以内", len(rows) == 3 and all(abs(r[2] / r[3] - 1) < 0.03 for r in rows),
         "最大 %.2f %%" % (100 * max(abs(r[2] / r[3] - 1) for r in rows)))
    gate("小雑音近似は低 SN 比で外れ(%.0f %%)、Rice の式は外れない" % (100 * abs(rows[2][4] / rows[2][3] - 1)),
         abs(rows[2][4] / rows[2][3] - 1) > 0.1 and abs(rows[0][4] / rows[0][3] - 1) < 0.01)
    NUMBERS.update({"phase_sd_hi": rows[0][2], "phase_sd_lo": rows[2][2], "noise_rel_worst": max(abs(r[2] / r[3] - 1) for r in rows)})


# --------------------------------------------------------------------------- #
# 3. (a) 多重極変調リング                                                          #
# --------------------------------------------------------------------------- #
def make_relief(n=96):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    h = 0.15 * np.sin(2 * np.pi * xx / 17.0) * np.cos(2 * np.pi * yy / 23.0)           # 緩い波(ゆず肌)
    h += -3.0 * np.exp(-((yy - 30) ** 2 + (xx - 30) ** 2) / (2 * 5.0 ** 2))              # へこみ
    h += 2.5 * np.exp(-((yy - 62) ** 2 + (xx - 66) ** 2) / (2 * 4.0 ** 2))                # こぶ
    d = np.abs((xx - 15) - 0.6 * (yy - 55))                                              # 引っかき傷(斜めの溝)
    h += -1.0 * np.exp(-d ** 2 / (2 * 1.2 ** 2)) * ((yy > 50) & (yy < 90))
    stripes = 0.35 + 0.55 * (np.floor(xx / 6.0) % 2) + 0.05 * (yy / n)                    # 印刷の縞(反射率)
    return h, np.clip(stripes, 0.05, 1.0)


def chapter_ring():
    print("\n3. (a) 多重極変調リング: 法線と凹凸")
    h, alb = make_relief()
    zen, s, fpp, npd = 25.0, 8, 16, 4
    vid = LK.lockin_ring_synthesize(h, zen, s, 1, fpp, npd, albedo=alb)
    d = LK.lockin_demodulate(vid, 1.0, float(fpp))
    nrm = LK.lockin_ring_normals(d, zen)
    gy, gx = np.gradient(h)
    inner = (slice(1, -1), slice(1, -1))
    tilt_true = np.degrees(np.arctan(np.hypot(gx, gy)))
    valid_frac = float(nrm["valid"].mean())
    n1 = np.stack([-nrm["height_gradient_x"], -nrm["height_gradient_y"], np.ones_like(gx)], -1)
    n2 = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    ang = np.degrees(np.arctan2(np.linalg.norm(np.cross(n1, n2), axis=-1), np.sum(n1 * n2, -1)))[inner]
    print("   面: 傾き最大 %.1f°(影の限界 %.0f°)、有効画素 %.1f %%、法線の角度誤差 最大 %.1e°" % (
        tilt_true.max(), 90 - zen, 100 * valid_frac, np.nanmax(ang)))
    gate("全画素が有効(影が出ない傾き)で、法線の角度誤差は 1e-9° 以内(反射率の縞があっても)",
         valid_frac == 1.0 and np.nanmax(ang) < 1e-9, "最大 %.1e°" % np.nanmax(ang))
    NUMBERS.update({"ring_tilt_max": float(tilt_true.max()), "ring_ang_err": float(np.nanmax(ang))})
    # 反射率 3 条件で同じか(縞 / 一様 / 反転)
    errs = []
    for a in (alb, np.full_like(alb, 0.6), 1.05 - alb):
        dd = LK.lockin_demodulate(LK.lockin_ring_synthesize(h, zen, s, 1, fpp, npd, albedo=a), 1.0, float(fpp))
        e = LK.lockin_ring_normals(dd, zen)
        errs.append(float(np.nanmax(np.abs(e["height_gradient_x"] - gx)[inner])))
    gate("反射率を 3 通りにしても勾配は同じ(差 1e-12 以内)", len(errs) == 3 and max(errs) < 1e-12, "%.1e" % max(errs))
    # 普通の 1 灯の像 / 平均の像は反射率の縞に埋もれる。復調の傾きは凹凸と相関する
    plain = d["dc"]
    r_plain = float(np.corrcoef(plain.ravel(), tilt_true.ravel())[0, 1])
    r_ring = float(np.corrcoef(nrm["tilt_deg"].ravel(), tilt_true.ravel())[0, 1])
    print("   真の傾きとの相関: 平均の像 %.3f、リングの法線 %.6f" % (r_plain, r_ring))
    gate("傾きの相関: 平均の像は 0.5 未満、リングの法線は 0.999999 以上", abs(r_plain) < 0.5 and r_ring > 0.999999)
    NUMBERS.update({"corr_plain": r_plain, "corr_ring": r_ring})
    # 四重極 / 単極
    d2 = LK.lockin_demodulate(LK.lockin_ring_synthesize(h, zen, s, 2, fpp, npd, albedo=alb), 1.0, float(fpp))
    d0 = LK.lockin_demodulate(LK.lockin_ring_synthesize(h, zen, s, 0, fpp, npd, albedo=alb), 1.0, float(fpp))
    q = float(d2["amplitude"][inner].max())
    mo = float(np.abs(d0["amplitude"] - d0["dc"])[inner].max())
    print("   四重極の振幅 最大 %.1e、単極の |振幅 − 直流| 最大 %.1e" % (q, mo))
    gate("四重極は朗伯面で 0(1e-14 以内)、単極は振幅 = 直流(向きを持たない)", q < 1e-14 and mo < 1e-14)
    # 雑音を入れた法線: 予測と比べる
    sig = 0.004
    vn = LK.lockin_ring_synthesize(h, zen, s, 1, fpp, npd, albedo=alb, noise_sigma=sig, seed=7)
    dn = LK.lockin_demodulate(vn, 1.0, float(fpp))
    nn = LK.lockin_ring_normals(dn, zen)
    comp = LK.lockin_noise_floor(fpp * npd, sig, 1.0)["component_std"]
    pred = float(np.sqrt(np.mean((2 * comp / (d["dc"] * math.tan(math.radians(zen)))) ** 2)))
    meas = float(np.sqrt(np.nanmean(np.r_[(nn["height_gradient_x"] - gx).ravel(), (nn["height_gradient_y"] - gy).ravel()] ** 2)))
    ang_n = np.degrees(np.arctan2(np.hypot(nn["height_gradient_x"] - gx, nn["height_gradient_y"] - gy), 1.0))
    print("   雑音 σ = %.3f(64 枚): 勾配の RMS 誤差 実測 %.4f、予測 %.4f(2σ_c / (DC tanζ))、法線の角度誤差 RMS %.2f°" % (
        sig, meas, pred, math.sqrt(np.nanmean(ang_n ** 2))))
    gate("雑音下の勾配の誤差が予測と 15 % 以内", abs(meas / pred - 1.0) < 0.15, "%.1f %%" % (100 * abs(meas / pred - 1)))
    NUMBERS.update({"ring_noise_meas": meas, "ring_noise_pred": pred, "ring_noise_ang_rms": float(math.sqrt(np.nanmean(ang_n ** 2)))})
    # 壊して確かめる: 天頂角を間違える
    bad = LK.lockin_ring_normals(d, zen * 1.3)
    e_bad = float(np.nanmax(np.abs(bad["height_gradient_x"] - gx)[inner]))
    gate("天頂角を 30 % 間違えると勾配が 1e-2 以上狂う(門は赤になる)", e_bad > 1e-2, "誤差 %.2f" % e_bad)
    # 影: 急な傾きは有効にしない
    steep = np.mgrid[0:48, 0:48][1] * 1.2                    # 50° の斜面
    ds = LK.lockin_demodulate(LK.lockin_ring_synthesize(steep, 45.0, s, 1, fpp, 2), 1.0, float(fpp))
    ns = LK.lockin_ring_normals(ds, 45.0)
    gate("影の限界(90° − 天頂角 = 45°)を超える 50° の斜面は有効画素 0(法線を作らない)", int(ns["valid"][4:-4, 4:-4].sum()) == 0)
    return h, alb, d, nrm, tilt_true


# --------------------------------------------------------------------------- #
# 4. (b) 符号化間歇照明                                                           #
# --------------------------------------------------------------------------- #
def chapter_daylight():
    print("\n4. (b) 符号化間歇照明: 昼間の光の下で灯を分ける")
    n = 32
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float64)
    texture = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(xx / 5.0) * np.cos(yy / 7.0))
    lamps = [texture * (0.5 + 0.5 * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / 600.0))
             for cy, cx in ((16, 16), (16, 48), (48, 32))]
    ambient = 4.0 * (0.6 + 0.4 * xx / 64.0)                           # 昼間の光: 灯の 3〜4 倍
    codes = LK.lockin_walsh_codes(n, 3)
    t = np.arange(n)[:, None, None]
    gate_on = (1.0 + codes) / 2.0
    clean = ambient[None] + sum(lamps[i][None] * gate_on[i][:, None, None] for i in range(3))
    # 比べ手: 灯 1 の点いたコマ - 消えたコマ(2 枚の差)。32 コマ x 32 コマの全部の対から**最良**を選ぶ(Walsh 符号では
    # 灯 1 だけが変わる対は無い。他の灯が少なくとも 1 つ一緒に変わる)
    k_on = int(np.argmax(gate_on[0] * (1 - gate_on[1]) * (1 - gate_on[2])))
    best = (np.inf, 0, 0)
    for ka in np.flatnonzero(gate_on[0] == 1):
        for kb in np.flatnonzero(gate_on[0] == 0):
            e = float(np.max(np.abs(clean[ka] - clean[kb] - lamps[0])))
            if e < best[0]:
                best = (e, int(ka), int(kb))
    naive = clean[best[1]] - clean[best[2]]
    r = LK.lockin_separate(clean, codes)
    e_sep = max(float(np.max(np.abs(r["on_image"][i] - lamps[i]))) for i in range(3))
    e_naive = best[0]
    print("   昼間の光/灯 = %.1f〜%.1f。理想: 3 灯とも分離、最大誤差 %.1e(灯の像の最大 %.2f)" % (
        ambient.min() / lamps[0].max(), ambient.max() / lamps[0].max(), e_sep, lamps[0].max()))
    gate("昼間の光が一定なら 3 つの灯を 1e-12 以内で分離(直流 = 昼間 + 灯の半分)",
         r["coefficients"].shape == (3, 64, 64) and e_sep < 1e-12 and
         float(np.max(np.abs(r["dc"] - (ambient + sum(lamps) / 2.0)))) < 1e-12, "最大 %.1e" % e_sep)
    # ちらつきとゆっくりした増加
    flick = 0.6 * np.cos(2 * np.pi * 5 * t / n) * (0.5 + 0.5 * xx / 64.0)[None]
    drift = 0.8 * (t / (n - 1.0)) * np.ones((1, 64, 64))
    dirty = clean + flick + drift + np.random.default_rng(3).normal(0.0, 0.02, clean.shape)
    r2 = LK.lockin_separate(dirty, codes)
    e_dirty = float(np.max(np.abs(r2["on_image"][0] - lamps[0])))
    ramp = np.linspace(-1.0, 1.0, n)
    r3 = LK.lockin_separate(dirty, np.vstack([codes, ramp]))
    e_ramp = float(np.max(np.abs(r3["on_image"][0] - lamps[0])))
    print("   昼間の光にちらつき + 増加 + 雑音: 灯 1 の最大誤差 %.3f(増加の列を足すと %.3f)、残差 RMS 平均 %.3f → %.3f" % (
        e_dirty, e_ramp, float(r2["residual_rms"].mean()), float(r3["residual_rms"].mean())))
    gate("増加を表す列を足すと灯 1 の誤差が下がり、ちらつき(5 周期)が残差に出る",
         e_ramp < e_dirty and float(r3["residual_rms"].mean()) > 0.1)
    print("   比べ手(灯 1 の点いたコマ − 消えたコマ、256 通りの対から最良)の最大誤差 %.2f(灯 1 の像の最大 %.2f)" % (e_naive, lamps[0].max()))
    gate("2 枚の差は最良の対でも他の灯が混ざって誤差 %.2f(符号の分離 1.9e-15 の 14 桁上)" % e_naive, e_naive > 0.1 and e_sep < 1e-12)
    try:
        LK.lockin_separate(clean, np.stack([codes[0], codes[1], codes[0] + codes[1]]))
        ref = False
    except ValueError as e:
        ref = "dependent" in str(e)
    gate("従属な符号は拒否", ref)
    NUMBERS.update({"sep_err": e_sep, "naive_err": e_naive, "dirty_err": e_dirty, "ramp_err": e_ramp,
                    "amb_ratio_lo": float(ambient.min() / lamps[0].max())})
    return clean, lamps, r, k_on, naive, dirty, r3


# --------------------------------------------------------------------------- #
# 5. (c) ロックイン・サーモグラフィ                                                  #
# --------------------------------------------------------------------------- #
ALPHA = 4.2e-7          # CFRP の板厚方向の熱拡散率 [m^2/s]
F_HEAT = 0.2            # 加熱の周波数 [Hz]
L_PLATE = 3.0e-3        # 板厚 [m]


def _phase_of_depth(x):
    """板厚 x·μ の層の位相 [rad] = -45° + arg coth((1+j)x)。"""
    return -0.25 * np.pi + np.angle(1.0 / np.tanh((1.0 + 1.0j) * np.asarray(x, np.float64)))


def chapter_thermo():
    print("\n5. (c) ロックイン・サーモグラフィ")
    mu = math.sqrt(ALPHA / (math.pi * F_HEAT))
    print("   CFRP α = %.1e m²/s、加熱 %.2f Hz → 熱拡散長 μ = %.3f mm、板厚 %.1f mm = %.1f μ" % (ALPHA, F_HEAT, mu * 1e3, L_PLATE * 1e3, L_PLATE / mu))
    n = 96
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    depth = np.full((n, n), L_PLATE)
    voids = [(24, 24, 9, 0.3), (24, 72, 9, 0.6), (72, 24, 9, 1.0), (72, 72, 9, 1.5)]          # (行, 列, 半径 px, 深さ mm)
    for cy, cx, rad, dmm in voids:
        depth[(yy - cy) ** 2 + (xx - cx) ** 2 <= rad * rad] = dmm * 1e-3
    uneven = (0.6 + 0.8 * xx / n) * (1.0 - 0.3 * np.exp(-((yy - 48) ** 2 + (xx - 48) ** 2) / 200.0))   # 加熱・放射率のムラ
    fpp, npd = 20, 4
    clean = LK.lockin_thermal_wave(depth, ALPHA, F_HEAT, fpp, npd, nonuniformity=uneven)
    even = LK.lockin_thermal_wave(depth, ALPHA, F_HEAT, fpp, npd)
    d = LK.lockin_demodulate(clean, 1.0, float(fpp))
    d_even = LK.lockin_demodulate(even, 1.0, float(fpp))
    sound = depth == L_PLATE
    ph_sd = float(np.std(d["phase"][sound]))
    amp_cv = float(np.std(d["amplitude"][sound]) / np.mean(d["amplitude"][sound]))
    dev = float(np.max(np.abs(d["phase"] - d_even["phase"])))
    print("   加熱ムラ入り: 健全部の振幅の変動 %.0f %%、位相の標準偏差 %.1e rad、ムラの有無での位相の差 最大 %.1e" % (100 * amp_cv, ph_sd, dev))
    gate("加熱ムラは健全部の振幅を 20 % 以上ばらつかせるが位相には入らない(位相の差 1e-12 以内)", amp_cv > 0.2 and dev < 1e-12, "%.1e" % dev)
    want = _phase_of_depth(depth / mu)
    e_cf = float(np.max(np.abs(np.angle(np.exp(1j * (d["phase"] - want))))))
    gate("位相は厳密解 −45° + arg coth((1+j)L/μ) と 1e-12 以内", e_cf < 1e-12, "%.1e" % e_cf)
    # 位相から深さへ(単調な枝 L/μ < 1.6)
    xs = np.linspace(0.02, 1.963, 6000)         # 位相が最大になる L/μ = 1.963 まで(それより深いと同じ位相が 2 つの深さに対応する)
    phs = _phase_of_depth(xs)
    mono = bool(np.all(np.diff(phs) > 0))
    # 雑音を入れて深さを読む
    sig = 0.12                                                    # 健全部の振幅(1/√2 ≈ 0.7 を単位として)に対する雑音
    noisy = clean + np.random.default_rng(5).normal(0.0, sig, clean.shape)
    dn = LK.lockin_demodulate(noisy, 1.0, float(fpp))
    cf = LK.lockin_noise_floor(fpp * npd, sig, float(np.median(d["amplitude"][sound])))
    sd_meas = float(np.std(dn["phase"][sound] - d["phase"][sound][0]))
    amp_s = d["amplitude"][sound]
    pred = float(np.sqrt(np.mean((cf["component_std"] / amp_s) ** 2)))
    print("   雑音 σ = %.2f(80 枚): 健全部の位相の標準偏差 実測 %.4f rad、予測 %.4f rad(振幅 %.2f〜%.2f)" % (
        sig, sd_meas, pred, amp_s.min(), amp_s.max()))
    gate("健全部の位相の標準偏差が、振幅ごとの閉形式の予測と 10 % 以内", abs(sd_meas / pred - 1.0) < 0.10, "%.1f %%" % (100 * abs(sd_meas / pred - 1)))
    est = []
    for cy, cx, rad, dmm in voids:
        m = (yy - cy) ** 2 + (xx - cx) ** 2 <= (rad - 2) ** 2
        ph_v = float(np.mean(dn["phase"][m]))
        x_est = float(np.interp(ph_v, phs, xs)) if phs[0] < ph_v < phs[-1] else float("nan")
        est.append((dmm, x_est * mu * 1e3))
        print("   欠陥の深さ %.1f mm(%.2f μ)→ 位相 %.1f° → 推定 %.2f mm" % (dmm, dmm * 1e-3 / mu, math.degrees(ph_v), x_est * mu * 1e3))
    errs = [abs(b - a) / a for a, b in est]
    gate("位相から読んだ欠陥の深さが 4 つとも ±10 % 以内(L/μ = 0.37〜1.85 のうち単調な枝)",
         mono and len(est) == 4 and max(errs) < 0.10, "最大 %.1f %%" % (100 * max(errs)))
    NUMBERS.update({"thermo_amp_cv": amp_cv, "thermo_phase_dev": dev, "thermo_closed_err": e_cf, "thermo_sd_meas": sd_meas,
                    "thermo_sd_pred": pred, "thermo_depth_err_max": float(max(errs)), "mu_mm": mu * 1e3})
    NUMBERS.update({"thermo_est_%d" % i: v[1] for i, v in enumerate(est)})
    return depth, d, dn, est


def chapter_probes():
    print("\n6. 壊して確かめる")
    n, fps = 64, 64.0
    k = np.arange(n)
    ok_ref = 4.0
    x = _cube(np.cos(2 * np.pi * 4 * k / n))
    off = LK.lockin_demodulate(x, ok_ref * 1.10, fps, "hann")["amplitude"][0, 0]
    gate("参照を 10 %% ずらすと振幅は %.2f に落ちる(門 |振幅 − 1| < 1e-12 は赤)" % off, abs(off - 1.0) > 0.05)
    refused = 0
    for bad in (dict(f_ref=fps / 2, fps=fps), dict(f_ref=0.5, fps=fps), dict(f_ref=float("nan"), fps=fps), dict(f_ref=3.7, fps=fps)):
        try:
            LK.lockin_demodulate(x, bad["f_ref"], bad["fps"])
        except ValueError:
            refused += 1
    gate("ナイキスト・1 周期未満・非数・整数でない周期の 4 つはすべて拒否", refused == 4)
    try:
        LK.lockin_ring_synthesize(np.zeros((8, 8)), 20.0, 8, 1, 16, 2, noise_sigma=0.01)
        seedless = False
    except ValueError:
        seedless = True
    gate("雑音の模擬は種を明示しないと拒否(隠れた乱数状態を持たない)", seedless)


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(ring, daylight, thermo):
    h, alb, d, nrm, tilt_true = ring
    clean, lamps, r, k_on, naive, dirty, r3 = daylight
    depth, dt, dtn, est = thermo
    normal_rgb = np.nan_to_num(0.5 + 0.5 * nrm["normal"], nan=0.0)
    ratio = d["amplitude"] / d["dc"]                                                            # 反射率が消える(= tanζ/2 · tan 傾き)
    ph_show = np.where(ratio > 0.01, d["phase"], 0.0)                                           # 傾きの無い所の位相は描かない
    figs.save_grid("ring_amp_phase", [d["dc"], d["amplitude"], ratio, ph_show, normal_rgb, tilt_true],
                   captions=["平均(直流): 反射率の縞が主役", "基本波の振幅 A: 縞が乗る", "A / 直流: 縞が消える",
                             "位相 φ(傾きの向き)", "法線の疑似カラー", "真の傾き [度]"],
                   ncols=3, signed=[False, False, False, True, False, False], gray=[True, False, False, False, False, False],
                   title="多重極変調リング: 縞の反射率に隠れた凹凸が、位相と振幅から法線として出る",
                   caption="8 灯の輪の光の位相を方位角と一緒に 1 周させ(双極子)、画素ごとに復調する。")
    lo_hi = (0.0, float(lamps[0].max()))
    figs.save_grid("daylighting", [clean[k_on], naive - lamps[0], r["on_image"][0], lamps[0]],
                   captions=["昼間の光の下で灯 1 を点けた 1 コマ", "最良の 2 コマの差の誤差(他の灯の混入)", "符号で分離した灯 1(on_image)", "真値の灯 1"],
                   ncols=2, signed=[False, True, False, False], gray=[True, False, True, True],
                   vrange=[(0.0, float(clean[k_on].max())), (-lo_hi[1], lo_hi[1]), lo_hi, lo_hi],
                   title="符号化間歇照明: 昼間の光(灯の 3〜4 倍)の下で、符号の付いた灯だけを取り出す",
                   caption="Walsh 符号 3 本で断続する 3 灯。分離した灯 1 は真値と 1e-12 で一致する。")
    figs.save_grid("thermography", [dt["amplitude"], np.degrees(dt["phase"]), np.degrees(dtn["phase"]), depth * 1e3],
                   captions=["振幅(加熱ムラが乗る)", "位相 [度](ムラが入らない)", "位相 [度](雑音あり)", "真の欠陥の深さ [mm]"],
                   ncols=2, vrange=[None, (-90.0, -43.0), (-90.0, -43.0), (0.0, 3.0)],
                   title="ロックイン・サーモグラフィ: 位相は加熱ムラに影響されず、欠陥の深さを読める",
                   caption="CFRP 板 3 mm、加熱 0.2 Hz(μ = 0.81 mm)。")
    xs = np.linspace(0.05, 3.0, 120)
    figs.save_plot("thermal_phase_vs_depth", [("位相 −45° + arg coth((1+j)L/μ) [度]", xs, np.degrees(_phase_of_depth(xs))),
                                              ("−45°(深い層)", xs, np.full_like(xs, -45.0))],
                   xlabel="層の厚さ L / 熱拡散長 μ", ylabel="位相 [度]", styles=[None, "dashed"], colors=["emphasis", "reference"],
                   title="位相は L/μ = 1.96 まで単調 ―― それより深い欠陥は位相から一意に読めない",
                   caption="周期加熱の熱波が、厚さ L の層の底(断熱面)で反射して表面に戻る遅れ。")


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 画素ごとの直交復調(ロックイン)(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_closed_form()
    chapter_noise()
    ring = chapter_ring()
    daylight = chapter_daylight()
    thermo = chapter_thermo()
    chapter_probes()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(ring, daylight, thermo)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
