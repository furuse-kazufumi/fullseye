# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: TDI ラインスキャンカメラとラインスキャン用レンズ —— 暗い搬送ラインで段数を積むと欠陥が見え、同期がずれると流れ、
普通の C マウントレンズでは長いセンサの端が消える。

【問い】フィルム・鋼板・ガラス・印刷物・ウェハのように流れてくるものはラインセンサで撮る。暗いラインでは TDI
(時間遅延積分)で N 段ぶん露光を積むが、そのぶん**搬送とラインレートの同期**が画質を決める。8k × 7 µm = 57 mm の
長いセンサは普通の C マウントの像円(2/3 型で 11 mm)に収まらないので、ラインスキャン用のレンズを使う。
新 op 6 本(`linescan`)を、閉形式と仕込んだ欠陥の真値で採点する。4 章:

  1. **段数と SNR**: 冷延鋼板の地合いに薄い傷・ピンホール・異物を仕込み、暗い照明(1 段 40 光子)で N = 1〜64 段。
     平坦な灰色の板の 2 枚撮りから EMVA 1288 の時間雑音(``sensorchar.emva_pair_statistics``)で SNR を測り、
     ``tdi_snr``(式 21 を段数倍)と比べる。電荷で足す方式とデジタルで足す方式の差。欠陥の検出数。
  2. **同期ずれ**: 速度誤差 ε で N 段の間に像が N·ε 画素流れ、流れ方向の MTF が |sinc(f N ε)| に落ちる ——
     閉形式を先に印字してから、正弦波の板で実測する。速度のうねりはエンコーダ同期で消える。
  3. **ヨーと蛇行**: 斜行 θ は幅方向に N·sin θ 画素のぼけを作り、エンコーダでは直らない。蛇行も同じ側。
  4. **ラインスキャン用レンズ**: 同じ形の三枚玉を「57 mm の像円のために」f 90 mm で作ったものと、「2/3 型のために」
     f 35 mm で作ったもの(C マウントの流用)を光線追跡し、像高ごとの照度(cos⁴ × 瞳 × 歪曲の 3 因子に厳密に分解)と
     MTF を出す。8192 画素の全幅を撮り、フラットフィールド補正で照度の落ちは直るが MTF と欠陥の CNR は直らないことを数で。

EXTEND: 実機に差し替えるなら、``linescan_acquire`` の web を実際の反射率の地図(高解像度のエリアカメラで撮った基準や、
CAD の印刷の版)に、``eta`` / ``sigma_d`` / ``K`` を手元のカメラの EMVA 1288 データシートの値に、``lens`` を
``lens_field_profile``(処方があるとき)か、実測した像高ごとの照度と MTF(MTF チャートとフラットの撮像)から作った
``linescan_lens_columns`` 互換の dict にする。★レンズの模型は実在の型番の処方ではない(メーカーの処方は公開されて
いない)ので、本 PoC の像高ごとの数字を特定のレンズの性能として引用してはいけない —— 引用できるのは
「像円が足りないと端が消え、補正で照度は戻るが MTF は戻らない」という**性質**と、その分解の仕方。
同期の模型は一定の ε とうねりまでで、ベルトの滑りの統計や、電荷の送りの離散さ(全条件に共通の 1 画素の掃引)は入れていない。

【外部真値】EMVA 1288 Release 4.0 の式 21 と 6.4 節(TDI は露光に段数を掛ける)、一様な掃引の MTF |sinc|、
cos⁴ 則(``optics.relative_illumination``)、Lepage, Bogaerts & Meynants, IEEE TED 56(11) 2009(電荷とデジタルの加算の
雑音の違い)、Yu ら, Sensors 24(5) 1622, 2024(ウェハの暗視野で TDI の段数が粒子欠陥の SNR を上げる)。
欠陥の位置と形は自分で仕込んだ真値。【学習】0。【較正】0。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import defectgen as DG  # noqa: E402
import examplefig as figs  # noqa: E402
import gfx2d  # noqa: E402
import linescan as LS  # noqa: E402
import optics  # noqa: E402
import sensorchar as SC  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

#: センサの仮定(典型的な桁。特定の型番のデータシートの値ではない)。
SENSOR = {"eta": 0.6, "sigma_d": 12.0, "K": 0.25, "full_well_e": 60000.0}
#: 暗い搬送ライン: 1 段あたりの光子数(反射率 1 のとき)。
PHOTONS_DARK = 40.0
PIXEL_UM = 7.0
SENSOR_PX = 8192

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# 素材: 冷延鋼板の地合い + 薄い欠陥(真値のマスクつき)                           #
# --------------------------------------------------------------------------- #
def steel_web(h, w, seed=0, defects=True, centres=None):
    """冷延鋼板の反射率の地図(圧延方向 = 行 = MD に伸びたヘアライン + 細かい粒 + ゆるいむら)と欠陥のマスク。"""
    rng = np.random.default_rng(seed)
    hair = DG.surface_texture((h, w), kind="brushed", strength=0.02, scale_px=1.6, seed=seed) - 0.5
    grain = DG.surface_texture((h, w), kind="grain", strength=0.008, scale_px=6.0, seed=seed + 1) - 0.5
    mott = ndimage.gaussian_filter(rng.standard_normal((h, w)), 40.0)
    mott = 0.025 * mott / max(float(mott.std()), 1e-12)
    web = 0.55 + hair + grain + mott
    masks = {}
    if defects:
        # 欠陥は「深さ」の層に描いてから縁を σ 0.6 画素でなじませる(画素ちょうどの階段や十字の点にしない)
        cs = centres or [(h * 0.5, w * 0.30), (h * 0.5, w * 0.55), (h * 0.5, w * 0.78)]
        dep = np.zeros((h, w))
        sc_img, sc_m = DG.defect_scratch((h, w), length_px=110.0, width_px=1.3, angle_deg=25.0, wander=0.05,
                                         contrast=-0.12, seed=seed + 2, start=(cs[0][0] - 23, cs[0][1] - 50))
        dep += sc_img - 0.5
        masks["傷(幅 1.3 画素、深さ 12 %)"] = sc_m
        yy, xx = np.mgrid[0:h, 0:w]
        ph = np.zeros((h, w), bool)
        for k in range(4):
            cy, cx = cs[1][0] - 30 + 20 * k, cs[1][1] + (k % 2) * 6
            r2 = (yy - cy) ** 2 + (xx - cx) ** 2
            dep -= 0.16 * np.exp(-r2 / (2.0 * 1.0 ** 2))
            ph |= r2 <= 1.5 ** 2
        masks["ピンホール 4 個(σ 1 画素、深さ 16 %)"] = ph
        bl_img, bl_m = DG.defect_blob((h, w), radius_px=3.5, roughness=0.3, contrast=-0.08, seed=seed + 3,
                                      centre=cs[2])
        dep += bl_img - 0.5
        masks["異物(径 7 画素、深さ 8 %)"] = bl_m
        web = web + ndimage.gaussian_filter(dep, 0.6)
    return np.clip(web, 0.0, 1.0), masks


def detect(img_e, masks_img, k_sigma=4.5, min_px=4):
    """背景(中央値フィルタ)を引いた残差を σ 1 画素のガウスで平滑し、頑健な σ(MAD)で割って k_sigma を超える
    連結成分(min_px 画素以上)を数える。欠陥のマスクに触れた成分 = 検出、どの欠陥にも触れない成分 = 誤検出。"""
    bg = ndimage.median_filter(img_e, size=(15, 15), mode="mirror")
    r = ndimage.gaussian_filter(img_e - bg, 1.0)
    s = 1.4826 * float(np.median(np.abs(r - np.median(r))))
    z = -r / max(s, 1e-12)                                # 欠陥は暗い
    lab, nlab = ndimage.label(z > k_sigma)
    if nlab:
        size = ndimage.sum(np.ones_like(z), lab, index=np.arange(1, nlab + 1))
        lab[np.isin(lab, 1 + np.nonzero(size < min_px)[0])] = 0
    hits = {}
    union = np.zeros_like(img_e, bool)
    for name, m in masks_img.items():
        mm = ndimage.binary_dilation(m, iterations=2)
        union |= mm
        hits[name] = bool(np.any(lab[mm] > 0))
    false_comp = len(set(np.unique(lab[(lab > 0) & ~ndimage.binary_dilation(union, iterations=3)])))
    return hits, false_comp, z


# --------------------------------------------------------------------------- #
# 1. 段数と SNR                                                                  #
# --------------------------------------------------------------------------- #
def chapter_snr():
    print("\n1. TDI の段数と SNR(暗いライン: 1 段 %.0f 光子 × 反射率)" % PHOTONS_DARK)
    stages = [1, 4, 16, 64] if REDUCED else [1, 2, 4, 8, 16, 32, 64]
    flat = np.full((220 if REDUCED else 360, 200), 0.5)
    rows = []
    for arch in ("charge", "digital"):
        cf = LS.tdi_snr(PHOTONS_DARK * 0.5, stages, SENSOR["eta"], SENSOR["sigma_d"], SENSOR["K"], architecture=arch)
        for i, N in enumerate(stages):
            kw = dict(stages=N, photons_per_stage=PHOTONS_DARK, architecture=arch, lines=120,
                      eta=SENSOR["eta"], sigma_d=SENSOR["sigma_d"], K=SENSOR["K"])
            a = LS.linescan_acquire(flat, seed=11, **kw)["image"]
            b = LS.linescan_acquire(flat, seed=12, **kw)["image"]
            st = SC.emva_pair_statistics(a, b)
            snr = st["mu"] / math.sqrt(st["var_temporal"])
            rows.append((arch, N, snr, float(cf["snr"][i])))
    print("   段数 | 電荷加算 実測 / 式 21 | デジタル加算 実測 / 式 21 | √N")
    worst = 0.0
    for N in stages:
        c = [r for r in rows if r[0] == "charge" and r[1] == N][0]
        d = [r for r in rows if r[0] == "digital" and r[1] == N][0]
        worst = max(worst, abs(c[2] / c[3] - 1), abs(d[2] / d[3] - 1))
        print("   %4d | %7.2f / %7.2f | %7.2f / %7.2f | %5.2f" % (N, c[2], c[3], d[2], d[3], math.sqrt(N)))
    gate("像から測った SNR が式 21(段数倍)と一致(全段数・両方式で最悪 %.1f %%)" % (100 * worst), worst < 0.04)
    c1 = [r for r in rows if r[0] == "charge" and r[1] == 1][0][2]
    c64 = [r for r in rows if r[0] == "charge" and r[1] == 64][0][2]
    d1 = [r for r in rows if r[0] == "digital" and r[1] == 1][0][2]
    d64 = [r for r in rows if r[0] == "digital" and r[1] == 64][0][2]
    NUMBERS.update({"snr_c1": c1, "snr_c64": c64, "snr_d64": d64})
    gate("デジタル加算は √N(64 段で ×%.2f、√64 = 8)" % (d64 / d1), abs(d64 / d1 / 8.0 - 1) < 0.05)
    gate("電荷加算は暗いと √N を超える(64 段で ×%.2f > 8 —— 読み出し雑音を 1 回しか払わない)" % (c64 / c1), c64 / c1 > 8.5)
    bright = LS.tdi_snr(4000.0, [1, 64], SENSOR["eta"], SENSOR["sigma_d"], SENSOR["K"])
    g = float(bright["gain"][1])
    gate("明るい(ショット雑音律)と電荷加算もほぼ √N に戻る(1 段 4000 光子で ×%.3f、残りは読み出し雑音の 3 %%)" % g,
         abs(g / 8.0 - 1) < 0.05)

    # 欠陥が見えてくる
    H, W = (260, 320) if REDUCED else (330, 420)
    web, masks = steel_web(H, W, seed=3)
    shots, table = {}, []
    for N in stages:
        r = LS.linescan_acquire(web, stages=N, photons_per_stage=PHOTONS_DARK, lines=H - 2 * N - 12, seed=5,
                                eta=SENSOR["eta"], sigma_d=SENSOR["sigma_d"], K=SENSOR["K"])
        rows_i = np.round(r["line_rows"]).astype(int)
        cols = int(round(r["col0"])) + np.arange(r["width"])
        mi = {k: m[np.ix_(rows_i, cols)] for k, m in masks.items()}
        img_e = r["image"] / SENSOR["K"]
        hits, fa, _z = detect(img_e, mi)
        shots[N] = (img_e, mi)
        table.append((N, sum(hits.values()), fa, hits))
        print("   N = %2d: 欠陥 %d / %d を検出、誤検出 %d 個  %s" % (N, sum(hits.values()), len(hits), fa,
                                                         " ".join("%s=%s" % (k.split("(")[0], "○" if v else "×") for k, v in hits.items())))
    n1, nmax = table[0], table[-1]
    gate("1 段では薄い欠陥が見えない(%d / 3)、64 段で全部見える(%d / 3)" % (n1[1], nmax[1]), n1[1] <= 1 and nmax[1] == 3)
    gate("64 段の誤検出 %d 個(地合いを欠陥と呼ばない)" % nmax[2], nmax[2] <= 2)
    NUMBERS.update({"det1": n1[1], "det64": nmax[1]})
    return rows, shots, stages


# --------------------------------------------------------------------------- #
# 2. 同期ずれ                                                                    #
# --------------------------------------------------------------------------- #
def _amp(img, pos, f):
    """各列の信号を cos/sin/1 で最小二乗し、変調の振幅の列平均を返す(位置 pos = 行の web 座標)。"""
    A = np.stack([np.cos(2 * np.pi * f * pos), np.sin(2 * np.pi * f * pos), np.ones_like(pos)], 1)
    coef, *_ = np.linalg.lstsq(A, img, rcond=None)
    return float(np.mean(np.hypot(coef[0], coef[1]) / coef[2]))


def chapter_sync():
    print("\n2. 同期ずれ(速度誤差 ε、64 段)")
    N = 64
    eps_list = [0.0, 0.005, 0.01, 0.02, 0.04]
    f_list = np.array([0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45]) if not REDUCED else np.array([0.1, 0.25, 0.4])
    print("   閉形式(先に印字): 掃引 L = N·|ε| 画素、MTF = |sinc(f L)|、最初の零 f = 1/L")
    for e in eps_list[1:]:
        cf = LS.tdi_sync_mtf([0.25], N, e)
        print("     ε = %4.1f %%: L = %.2f 画素、MTF(0.25 c/px) = %.3f、零 = %.3f c/px"
              % (100 * e, cf["smear_scan_px"], cf["mtf_scan"][0], cf["first_zero_scan"]))
    OS = 5                                                # 板は 1 画素 5 web 画素で描く(補間の誤差を測りに混ぜない)
    H, W = 420, 24
    meas = {}
    worst = 0.0
    for f in f_list:
        y = np.arange(H * OS, dtype=np.float64)[:, None]
        web = np.repeat(0.5 + 0.3 * np.cos(2 * np.pi * f / OS * y), W * OS, axis=1)
        ref = None
        for e in eps_list:
            r = LS.linescan_acquire(web, stages=N, sync_error=e, noise=False, lines=240, samples_per_px=8.0, oversample=OS)
            a = _amp(r["mean_e"], r["line_rows"], f / OS)
            ref = a if e == 0.0 else ref
            m = a / ref
            c = float(LS.tdi_sync_mtf([f], N, e)["mtf_scan"][0])
            meas[(float(f), e)] = (m, c)
            worst = max(worst, abs(m - c))
    gate("実測の MTF が |sinc(f N ε)| と一致(%d 条件で最大差 %.4f)" % (len(meas), worst), worst < 0.01)
    m, c = meas[(0.25, 0.02)]
    NUMBERS.update({"mtf_sync_meas": m, "mtf_sync_closed": c})
    print("   例: ε = 2 %%、0.25 c/px で実測 %.3f / 閉形式 %.3f" % (m, c))

    # 速度のうねり: エンコーダ同期で消える
    L = 600
    t = np.arange(L + N + 2, dtype=np.float64)
    ripple = 0.03 * np.sin(2 * np.pi * t / 157.0) + 0.01
    f = 0.25
    y = np.arange((L + 2 * N + 60) * OS, dtype=np.float64)[:, None]
    web = np.repeat(0.5 + 0.3 * np.cos(2 * np.pi * f / OS * y), 16 * OS, axis=1)
    kw = dict(stages=N, noise=False, lines=L, samples_per_px=8.0, oversample=OS)
    fr = LS.linescan_acquire(web, sync_error=ripple, **kw)
    en = LS.linescan_acquire(web, encoder=True, sync_error=ripple, **kw)
    m0 = _amp(LS.linescan_acquire(web, **kw)["mean_e"], LS.linescan_acquire(web, **kw)["line_rows"], f / OS)
    win = 40
    mf = [_amp(fr["mean_e"][i:i + win], fr["line_rows"][i:i + win], f / OS) / m0 for i in range(0, L - win, win)]
    me = [_amp(en["mean_e"][i:i + win], en["line_rows"][i:i + win], f / OS) / m0 for i in range(0, L - win, win)]
    sp_f = np.diff(fr["line_rows"]) / OS
    sp_e = np.diff(en["line_rows"]) / OS
    print("   速度のうねり ±3 %% + ずれ 1 %%: ライン間隔 %.3f〜%.3f 行(自走)/ %.3f〜%.3f(エンコーダ)"
          % (sp_f.min(), sp_f.max(), sp_e.min(), sp_e.max()))
    print("   局所 MTF(0.25 c/px)の最低: 自走 %.3f / エンコーダ %.3f" % (min(mf), min(me)))
    gate("エンコーダ同期でライン間隔が一定(ばらつき %.1e 行)" % float(sp_e.std()), float(sp_e.std()) < 1e-9)
    gate("エンコーダ同期で MTF が 1 に戻る(最低 %.4f)、自走は %.3f まで落ちる" % (min(me), min(mf)),
         min(me) > 0.999 and min(mf) < 0.9)
    NUMBERS.update({"ripple_min_free": min(mf), "ripple_min_enc": min(me)})
    return meas, f_list, eps_list, (mf, me)


# --------------------------------------------------------------------------- #
# 3. ヨーと蛇行                                                                  #
# --------------------------------------------------------------------------- #
def chapter_yaw():
    print("\n3. ヨー(斜行)と蛇行 —— エンコーダでは直らない幅方向のぼけ")
    N = 64
    W = 160
    worst = 0.0
    out = {}
    OS = 5
    for th in (0.5, 1.0, 2.0):
        for f in (0.1, 0.2, 0.3):
            x = np.arange(W * OS, dtype=np.float64)[None, :]
            web = np.repeat(0.5 + 0.3 * np.cos(2 * np.pi * f / OS * x), 260 * OS, axis=0)
            kw = dict(stages=N, encoder=True, noise=False, lines=120, width=64, samples_per_px=8.0, oversample=OS)
            r0 = LS.linescan_acquire(web, **kw)
            r1 = LS.linescan_acquire(web, yaw_deg=th, **kw)
            # 幅方向の変調: 各行で列方向に当てはめる(列の web 座標 = 中央 + OS·x cos θ、位相のずれは振幅に効かない)
            xs = np.arange(64, dtype=np.float64) - 31.5
            cxw = (web.shape[1] - 1) / 2.0
            a0 = _amp(r0["mean_e"].T, cxw + OS * xs, f / OS)
            a1 = _amp(r1["mean_e"].T, cxw + OS * xs * math.cos(math.radians(th)), f / OS)
            c = float(LS.tdi_sync_mtf([f], N, 0.0, yaw_deg=th)["mtf_cross"][0])
            out[(th, f)] = (a1 / a0, c)
            worst = max(worst, abs(a1 / a0 - c))
    print("   閉形式: 幅方向の掃引 N·sin θ = %.2f / %.2f / %.2f 画素(0.5° / 1° / 2°)"
          % tuple(N * math.sin(math.radians(t)) for t in (0.5, 1.0, 2.0)))
    m, c = out[(2.0, 0.2)]
    print("   2°・0.2 c/px: 実測 %.3f / 閉形式 |sinc(f N sin θ)| = %.3f" % (m, c))
    gate("ヨーの幅方向 MTF が |sinc(f N sin θ)| と一致(9 条件で最大差 %.4f、エンコーダ同期のまま)" % worst, worst < 0.03)
    NUMBERS.update({"yaw_meas": m, "yaw_closed": c})
    # 蛇行: 傷の幅方向の広がり
    web, masks = steel_web(420, 200, seed=7, centres=[(210, 100), (210, 40), (210, 160)])
    a = LS.linescan_acquire(web, stages=N, encoder=True, noise=False, lines=300, width=180)
    b = LS.linescan_acquire(web, stages=N, encoder=True, weave_px=2.5, weave_period_lines=180.0, noise=False,
                            lines=300, width=180)
    print("   蛇行 振幅 2.5 画素・周期 180 ライン: 1 段の道のりに比例して標本 %d 点(蛇行なし %d 点)" % (b["samples"], a["samples"]))
    return out, (a, b)


# --------------------------------------------------------------------------- #
# 4. ラインスキャン用レンズ                                                      #
# --------------------------------------------------------------------------- #
def chapter_lens():
    print("\n4. ラインスキャン用レンズ vs C マウントの流用(8192 × 7 µm = 57.3 mm、視野 300 mm)")
    import raytrace as RT
    hs = np.linspace(0.0, 28.672, 9 if REDUCED else 17)
    prof = {}
    for kind in ("linescan", "cmount"):
        s = LS.linescan_lens_example(kind)
        p = RT.paraxial_trace(s)
        prof[kind] = LS.lens_field_profile(s, hs, (10.0, 20.0, 35.0))
        pr = prof[kind]
        print("   %-8s f %.1f mm、F %.1f、物体距離 %.0f mm、倍率 %.4f" % (kind, p["efl"], pr["working_fno"],
                                                                     s["object_mm"], p["magnification"]))
        for i in range(0, len(hs), max(1, len(hs) // 4)):
            print("     像高 %5.2f mm: 照度 %.3f = cos⁴ %.3f × 瞳 %.3f × 歪曲 %.3f、MTF20 タン %.2f / サジ %.2f"
                  % (hs[i], pr["relative_illumination"][i], pr["cos4"][i], pr["pupil_factor"][i],
                     np.nan_to_num(pr["area_gain"][i]), np.nan_to_num(pr["mtf_tangential"][i, 1]),
                     np.nan_to_num(pr["mtf_sagittal"][i, 1])))
    ls, cm = prof["linescan"], prof["cmount"]
    cov = ls["covered"] & np.isfinite(ls["area_gain"])
    ident = np.max(np.abs(ls["relative_illumination"][cov] - ls["cos4"][cov] * ls["pupil_factor"][cov] * ls["area_gain"][cov]))
    gate("照度 = cos⁴ × 瞳 × 歪曲 が厳密に成り立つ(最大差 %.1e)" % ident, ident < 1e-12)
    # cos⁴ の閉形式の検算: 絞りが第 1 面の薄い系(瞳収差なし)
    pin = RT.lens_system([{"R": float("inf"), "t": 0.5, "n": 1.0, "ap": 1.0}, {"R": 51.68, "t": 5.0, "n": "N-BK7"},
                          {"R": float("inf"), "t": None, "n": 1.0}], stop=0, object_mm=300.0)
    pp = LS.lens_field_profile(pin, [0.0, 10.0, 20.0, 30.0])
    ri_c = optics.relative_illumination(half_angle_deg=float(np.degrees(np.arctan2(abs(pp["object_height_mm"][-1]),
                                                                                    300.0 + RT.paraxial_trace(pin)["ep_position"]))),
                                        samples=2)[-1, 1]
    dev = float(np.max(np.abs(pp["flux_ratio"] - pp["cos4"])))
    gate("瞳収差の無い系で、光線で数えた光束が cos⁴ 則と一致(最大差 %.4f、optics.relative_illumination の端 %.4f と同じ角)"
         % (dev, ri_c), dev < 0.01 and abs(ri_c - pp["cos4"][-1]) < 1e-12)
    edge_ls, edge_cm = float(ls["relative_illumination"][-1]), float(cm["relative_illumination"][-1])
    cut = float(hs[np.argmax(~cm["covered"])]) if (~cm["covered"]).any() else float("nan")
    print("   センサの端(28.7 mm)の照度: ラインスキャン用 %.3f / C マウント %.3f(cos⁴ だけなら %.3f)"
          % (edge_ls, edge_cm, cm["cos4"][-1]))
    gate("C マウントの流用は端で光が届かない(像高 %.1f mm から 0)、ラインスキャン用は端でも %.2f" % (cut, edge_ls),
         edge_cm == 0.0 and edge_ls > 0.9)
    gate("ラインスキャン用の端の照度は cos⁴(%.3f)より明るい —— 樽型歪曲(%.1f %%)が像を縮めて ×%.3f、瞳が ×%.3f"
         % (ls["cos4"][-1], ls["distortion_percent"][-1], ls["area_gain"][-1], ls["pupil_factor"][-1]),
         edge_ls > ls["cos4"][-1] and ls["area_gain"][-1] > 1.05)
    NUMBERS.update({"ri_edge_ls": edge_ls, "ri_edge_cm": edge_cm, "cos4_edge_ls": float(ls["cos4"][-1]),
                    "cut_cm": cut})

    # 全幅で撮る: 中央と像高 14 mm(C マウントでも光は届く)に同じ欠陥
    lines = 90 if REDUCED else 150
    N = 16
    Hw = lines + 2 * N + 14
    Ww = SENSOR_PX + 16
    x_edge = int(round((SENSOR_PX - 1) / 2 + 14.0 / (PIXEL_UM * 1e-3))) + 8
    x_mid = Ww // 2
    web, masks = steel_web(Hw, Ww, seed=21, centres=[(Hw / 2, x_mid - 40), (Hw / 2, x_mid), (Hw / 2, x_mid + 40)])
    w2, m2 = steel_web(Hw, Ww, seed=22, centres=[(Hw / 2, x_edge - 40), (Hw / 2, x_edge), (Hw / 2, x_edge + 40)])
    yy = np.arange(Ww)
    web = np.where((yy > x_mid + 200)[None, :], w2, web)
    masks.update({k + "@端": v for k, v in m2.items()})
    flat = np.full((Hw, Ww), 0.8)
    res = {}
    kw = dict(stages=N, photons_per_stage=PHOTONS_DARK * 4, lines=lines, width=SENSOR_PX,
              eta=SENSOR["eta"], sigma_d=SENSOR["sigma_d"], K=SENSOR["K"])
    for kind in ("linescan", "cmount"):
        cols = LS.linescan_lens_columns(prof[kind], SENSOR_PX, PIXEL_UM, frequency_index=1)
        img = LS.linescan_acquire(web, lens=cols, seed=31, **kw)
        ff = LS.linescan_acquire(flat, lens=cols, seed=32, **kw)
        dark = np.zeros_like(ff["image"])
        ref = ff["image"].mean(0, keepdims=True)
        scale = 1.0 / (2.0 * float(ref.max()))
        covered = (ref[0] > 0.02 * ref.max())
        try:
            gfx2d.lens_shading_gain(np.repeat(ref * scale, 4, axis=0))
            refused = False
        except ValueError:
            refused = True
        gain = np.ones((1, SENSOR_PX))
        g_cov = gfx2d.lens_shading_gain(np.repeat(ref[:, covered] * scale, 4, axis=0))[0]
        gain[0, covered] = g_cov
        corr = gfx2d.lens_shading_correct(np.clip((img["image"] - dark) * scale, 0, 1), np.repeat(gain, lines, axis=0)) / scale
        flat_c = gfx2d.lens_shading_correct(np.clip(ff["image"] * scale, 0, 1), np.repeat(gain, lines, axis=0)) / scale
        res[kind] = {"cols": cols, "img": img, "corr": corr, "ref": ref[0], "covered": covered, "refused": refused,
                     "flat_c": flat_c}
        cm_ = ff["image"][:, covered].mean(0)
        cc_ = flat_c[:, covered].mean(0)
        print("   %-8s 白板の列平均の幅(最小/最大): 補正前 %.3f → 補正後 %.4f、光の届かない列 %d、補正の拒否(全幅)= %s"
              % (kind, cm_.min() / cm_.max(), cc_.min() / cc_.max(), int((~covered).sum()), refused))
        res[kind]["uni_before"] = float(cm_.min() / cm_.max())
        res[kind]["uni_after"] = float(cc_.min() / cc_.max())
    gate("フラットフィールド補正で照度の落ちは直る(ラインスキャン用 %.3f → %.4f、C マウントも届く列で %.3f → %.4f)"
         % (res["linescan"]["uni_before"], res["linescan"]["uni_after"], res["cmount"]["uni_before"], res["cmount"]["uni_after"]),
         res["linescan"]["uni_after"] > 0.97 and res["cmount"]["uni_after"] > 0.9)
    gate("光の届かない列は補正できない —— lens_shading_gain が全幅の補正を拒否(C マウント %d 列)"
         % int((~res["cmount"]["covered"]).sum()), res["cmount"]["refused"] and not res["linescan"]["refused"])
    # MTF は直らない: 像高 14 mm で幅方向の正弦波の変調を補正前後で
    f = 0.2
    xw = np.arange(Ww, dtype=np.float64)
    chart = np.repeat(0.5 + 0.3 * np.cos(2 * np.pi * f * xw)[None, :], Hw, axis=0)
    mod = {}
    for kind in ("linescan", "cmount"):
        r = LS.linescan_acquire(chart, lens=res[kind]["cols"], noise=False, **kw)
        g = gfx2d.lens_shading_gain(np.repeat(res[kind]["ref"][res[kind]["covered"]][None, :] * 1e-6, 2, axis=0))[0]
        xs = np.arange(SENSOR_PX)
        for where, x0 in (("中央", SENSOR_PX // 2 - 32), ("像高 14 mm", x_edge - 8 - 32)):
            seg = slice(x0, x0 + 64)
            pos = r["col0"] + xs[seg]
            raw = _amp(r["mean_e"][:, seg].T, pos, f)
            gfull = np.ones(SENSOR_PX)
            gfull[res[kind]["covered"]] = g
            cor = _amp((r["mean_e"][:, seg] * gfull[seg][None, :]).T, pos, f)
            mod[(kind, where)] = (raw, cor)
    for k, (raw, cor) in mod.items():
        print("   %-8s %s: 0.2 c/px の変調 %.3f(補正前)→ %.3f(補正後)" % (k[0], k[1], raw, cor))
    dmax = max(abs(c - r_) for r_, c in mod.values())
    gate("補正の前後で変調(MTF)は変わらない(差の最大 %.4f)—— 照度は直せても、ぼけは直せない" % dmax, dmax < 0.005)
    mc, ml = mod[("cmount", "像高 14 mm")][0], mod[("linescan", "像高 14 mm")][0]
    gate("像高 14 mm の変調: C マウント %.3f < ラインスキャン用 %.3f" % (mc, ml), mc < 0.5 * ml)
    NUMBERS.update({"mod14_cm": mc, "mod14_ls": ml})
    # 欠陥の CNR は補正で変わらない
    for kind in ("linescan", "cmount"):
        img = res[kind]["img"]
        rows_i = np.round(img["line_rows"]).astype(int)
        cidx = int(round(img["col0"])) + np.arange(SENSOR_PX)
        for name in [k for k in masks if "異物" in k]:
            mi = masks[name][np.ix_(rows_i, cidx)]
            ring = ndimage.binary_dilation(mi, iterations=8) & ~ndimage.binary_dilation(mi, iterations=3)
            for lab, a in (("前", img["image"]), ("後", res[kind]["corr"])):
                cnr = (a[ring].mean() - a[mi].mean()) / a[ring].std()
                res[kind].setdefault("cnr", {})[(name, lab)] = float(cnr)
    for kind in ("linescan", "cmount"):
        c = res[kind]["cnr"]
        print("   %-8s 異物の CNR: 中央 %.2f → %.2f、端 %.2f → %.2f(補正前 → 後)" % (
            kind, *[c[(n, l)] for n in sorted(k[0] for k in c if k[1] == "前") for l in ("前", "後")]))
    ce = res["cmount"]["cnr"]
    nm = [k[0] for k in ce if "@端" in k[0]][0]
    gate("C マウントの端の異物は補正しても CNR が戻らない(%.2f → %.2f、ラインスキャン用は %.2f)"
         % (ce[(nm, "前")], ce[(nm, "後")], res["linescan"]["cnr"][(nm, "後")]),
         abs(ce[(nm, "後")] - ce[(nm, "前")]) < 0.15 * abs(ce[(nm, "前")]) + 0.1 and res["linescan"]["cnr"][(nm, "後")] > ce[(nm, "後")])
    return prof, res, hs, x_edge


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def _crop(a, r0, c0, h, w):
    return a[r0:r0 + h, c0:c0 + w]


def make_figures(snr, sync, yaw, lens):
    rows, shots, stages = snr
    sel = [n for n in (1, 4, 16, 64) if n in shots]
    panels, caps = [], []
    for N in sel:
        img, _mi = shots[N]
        h, w = img.shape
        crop = _crop(img, h // 2 - 45, int(w * 0.17), 90, int(w * 0.70))
        med = float(np.median(crop))
        sd = 1.4826 * float(np.median(np.abs(crop - med)))
        g = np.clip(0.5 + (crop - med) / (6.0 * sd), 0, 1)           # 中央値 ± 3σ(雑音と地合いの尺度で揃える)
        panels.append(np.repeat(np.repeat(g, 2, axis=0), 2, axis=1))
        caps.append("TDI %d 段" % N)
    figs.save_grid("tdi_stages_defects", panels, captions=caps, ncols=2, gray=True, vrange=(0.0, 1.0),
                   title="暗いラインの冷延鋼板: 段数を積むと薄い欠陥が地合いから浮く",
                   caption="1 段 40 光子 × 反射率、読み出し 12 e⁻。左: 傷(幅 1.3 画素、深さ 12 %)、中: ピンホール 4 個(深さ 16 %)、右: 異物(深さ 8 %)。"
                           "各パネルは自分の中央値 ± 3σ で伸ばし、2 倍に拡大(明るさの差ではなく SNR の差を見る図)。")
    Ns = np.array(stages, float)
    ch = [r for r in rows if r[0] == "charge"]
    dg = [r for r in rows if r[0] == "digital"]
    figs.save_plot("snr_vs_stages", [("電荷加算 実測", Ns, np.array([r[2] for r in ch])),
                                     ("電荷加算 式 21", Ns, np.array([r[3] for r in ch])),
                                     ("デジタル加算 実測", Ns, np.array([r[2] for r in dg])),
                                     ("デジタル加算 式 21", Ns, np.array([r[3] for r in dg])),
                                     ("√N × 1 段", Ns, np.sqrt(Ns) * dg[0][2])],
                   xlabel="TDI の段数 N", ylabel="SNR(灰色 0.5 の板)", kinds=["scatter", "line", "scatter", "line", "line"],
                   styles=[None, "dashed", None, "dashed", "dotted"],
                   colors=["emphasis", "emphasis", "right", "right", "reference"],
                   title="段数と SNR: デジタル加算は厳密に √N、電荷加算は暗いと √N を超える",
                   caption="EMVA 1288 の 2 枚撮り(時間雑音)で測った SNR と、式 21 を段数倍した閉形式。")
    meas, f_list, eps_list, (mf, me) = sync
    ser, kinds, sty, col = [], [], [], []
    for e in eps_list[1:]:
        fs_ = np.array(f_list, float)
        ser.append(("ε = %.1f %% 実測" % (100 * e), fs_, np.array([meas[(float(f), e)][0] for f in f_list])))
        ff = np.linspace(0, 0.5, 101)
        ser.append(("", ff, LS.tdi_sync_mtf(ff, 64, e)["mtf_scan"]))
        kinds += ["scatter", "line"]
        sty += [None, "dashed"]
    figs.save_plot("sync_error_mtf", ser, xlabel="周波数 [cycles/画素](流れ方向)", ylabel="MTF(同期ずれのぶん)",
                   kinds=kinds, styles=sty, ylim=(0, 1.05),
                   title="同期ずれの MTF: 実測(点)と |sinc(f N ε)|(破線)、64 段",
                   caption="ε は搬送速度とラインレートの相対誤差。64 段の間に像が 64·ε 画素流れる。")
    # 同期ずれの絵
    web, masks = steel_web(300, 160, seed=9, centres=[(150, 50), (150, 80), (150, 115)])
    pans, cps = [], []
    for e, lab in ((0.0, "同期 ε = 0"), (0.02, "ε = 2 %"), (0.06, "ε = 6 %"), ("enc", "うねり + エンコーダ")):
        if e == "enc":
            t = np.arange(300)
            r = LS.linescan_acquire(web, stages=64, encoder=True, sync_error=0.03 * np.sin(2 * np.pi * t / 157.0) + 0.01,
                                    photons_per_stage=400, lines=130, seed=4)
        else:
            r = LS.linescan_acquire(web, stages=64, sync_error=e, photons_per_stage=400, lines=130, seed=4)
        a = r["image"][30:100, 20:140]
        a = np.clip((a - np.percentile(a, 0.5)) / (np.percentile(a, 99.5) - np.percentile(a, 0.5)), 0, 1)
        pans.append(np.repeat(np.repeat(a, 3, axis=0), 3, axis=1))
        cps.append(lab)
    figs.save_grid("sync_error_images", pans, captions=cps, ncols=2, gray=True, vrange=(0.0, 1.0),
                   title="同期がずれると欠陥が流れ方向に伸びる(64 段)",
                   caption="ピンホール(σ 1 画素)は ε = 6 % で 3.8 画素ぶん縦に伸びる(3 倍に拡大)。速度がうねってもエンコーダ同期なら崩れない。")
    out, (a, b) = yaw
    th = [0.5, 1.0, 2.0]
    ff = np.linspace(0, 0.5, 101)
    ser = []
    for t in th:
        ser.append(("%.1f° 実測" % t, np.array([0.1, 0.2, 0.3]), np.array([out[(t, f)][0] for f in (0.1, 0.2, 0.3)])))
        ser.append(("", ff, LS.tdi_sync_mtf(ff, 64, 0.0, yaw_deg=t)["mtf_cross"]))
    figs.save_plot("yaw_cross_mtf", ser, xlabel="周波数 [cycles/画素](幅方向)", ylabel="MTF(ヨーのぶん)",
                   kinds=["scatter", "line"] * 3, styles=[None, "dashed"] * 3, ylim=(0, 1.05),
                   title="ヨー(斜行)の幅方向の MTF: |sinc(f N sin θ)|、エンコーダ同期のまま",
                   caption="web が走査軸から θ 傾くと、64 段の間に幅方向へ 64·sin θ 画素ずれる。速度を合わせても消えない。")
    pa = [np.clip((x["mean_e"][40:240] - x["mean_e"].min()) / np.ptp(x["mean_e"]), 0, 1) for x in (a, b)]
    figs.save_grid("weave", pa, captions=["蛇行なし", "蛇行 2.5 画素・周期 180 ライン"], ncols=2, gray=True,
                   title="蛇行: 傷が揺れ、揺れの速い所で幅方向にぼける",
                   caption="エンコーダ同期(速度の誤差なし)のまま。蛇行は幅方向の動きなので速度の同期では直らない。")
    prof, res, hs, x_edge = lens
    ls, cm = prof["linescan"], prof["cmount"]
    hh = np.linspace(0, 28.672, 60)
    figs.save_plot("lens_relative_illumination",
                   [("ラインスキャン用 f 90", hs, ls["relative_illumination"]),
                    ("C マウント流用 f 35", hs, cm["relative_illumination"]),
                    ("cos⁴(f 90 の主光線角)", hs, ls["cos4"]), ("cos⁴(f 35)", hs, cm["cos4"])],
                   xlabel="像高 [mm](センサの端 = 28.7)", ylabel="相対照度", ylim=(0, 1.15),
                   styles=[None, None, "dashed", "dashed"], colors=["right", "wrong", "right", "wrong"],
                   title="像高ごとの照度: C マウントの流用は 2/3 型の像円の外で光が消える",
                   caption="光線追跡(射影立体角の一様格子)で数えた照度。ラインスキャン用は樽型歪曲で cos⁴ より明るい。")
    _ = hh
    figs.save_plot("lens_mtf_field",
                   [("ラインスキャン用 タンジェンシャル", hs, ls["mtf_tangential"][:, 1]),
                    ("ラインスキャン用 サジタル", hs, ls["mtf_sagittal"][:, 1]),
                    ("C マウント タンジェンシャル", hs, np.nan_to_num(cm["mtf_tangential"][:, 1])),
                    ("C マウント サジタル", hs, np.nan_to_num(cm["mtf_sagittal"][:, 1]))],
                   xlabel="像高 [mm]", ylabel="MTF(20 lp/mm)", ylim=(0, 1.05), styles=[None, "dashed", None, "dashed"],
                   colors=["right", "right", "wrong", "wrong"],
                   title="像高ごとの MTF(20 lp/mm): C マウントは 2/3 型の外で崩れる",
                   caption="タンジェンシャル = センサの並び(幅方向)、サジタル = 流れ方向。幾何 MTF × 回折 MTF。")
    pans, cps = [], []
    for kind, lab in (("linescan", "ラインスキャン用"), ("cmount", "C マウント流用")):
        for key, lab2 in (("img", "補正前"), ("corr", "シェーディング補正後")):
            a = res[kind][key]["image"] if key == "img" else res[kind][key]
            a = a[:, :a.shape[1] // 8 * 8].reshape(a.shape[0], -1, 8).mean(2)   # 8 画素ずつ平均して表示
            pans.append(np.clip(a / (1.25 * float(np.median(res["linescan"]["img"]["image"]))), 0, 1))
            cps.append("%s・%s" % (lab, lab2))
    figs.save_grid("full_width_shading", pans, captions=cps, ncols=1, gray=True, vrange=(0.0, 1.0),
                   title="8192 画素の全幅(8 画素ずつ平均して表示): 補正で明るさは揃うが、届かない列は戻らない",
                   caption="同じ明るさの尺度で表示。C マウントの両端は像円の外で光が届かない(補正は拒否される)。")
    pans, cps = [], []
    for kind, lab in (("linescan", "ラインスキャン用"), ("cmount", "C マウント")):
        a = res[kind]["corr"]
        for where, x0 in (("中央", SENSOR_PX // 2 - 100), ("像高 14 mm", x_edge - 8 - 100)):
            c = a[:, x0:x0 + 200]
            pans.append(np.clip((c - np.percentile(c, 0.5)) / (np.percentile(c, 99.5) - np.percentile(c, 0.5) + 1e-9), 0, 1))
            cps.append("%s・%s" % (lab, where))
    figs.save_grid("lens_defects_center_edge", pans, captions=cps, ncols=2, gray=True, vrange=(0.0, 1.0),
                   title="同じ欠陥を中央と像高 14 mm に(シェーディング補正後)",
                   caption="補正で明るさは揃えてあるのに、C マウントの像高 14 mm では傷とピンホールがぼけて地合いに埋もれる。")


def main():
    t0 = time.time()
    print("PoC TDI ラインスキャンとラインスキャン用レンズ(予算 %s)" % ("reduced" if REDUCED else "full"))
    snr = chapter_snr()
    sync = chapter_sync()
    yaw = chapter_yaw()
    lens = chapter_lens()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(snr, sync, yaw, lens)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
