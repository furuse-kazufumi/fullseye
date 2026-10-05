# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""研削・研磨・拭き取りを画像で測る —— 削れた深さ・拭けた帯の幅・拭けた面積を、Preston の式と接触圧の閉形式と MuJoCo で確かめる(2026-10-05)。

物理シミュ × Fullseye 系列(柔らかい手首のペグ挿入、失敗の分類、膜、対称性)の続き。研究所の研削の模倣学習(DIPCOM、arXiv:2410.19235)と
可変コンプライアンスの拭き(Comp-ACT、arXiv:2406.14990)は、接触を保つ剛性を学習で決める。ここでは学習を使わず、仕事の結果(削れた量・
拭けた範囲)を画像で読んで、外から来る式と比べる。
外から来るもの:
  * **Preston の式** dh/dt = k_p p v(Preston 1927 は未読。式の形と k_p の桁 = Shen ほか 2018、J. Am. Ceram. Soc.、LLNL-JRNL-748089 の式 (1)
    と本文: セリアでガラスを磨くと 2×10⁻¹³〜2×10⁻¹² m²/N)。
  * **接触圧の閉形式**: 平らな工具は一様、球面の工具は Hertz の p(r)(Johnson 1985、tacsim の hertz_sphere)。
  * **導出した閉形式**: 直線の一筆の断面(平板 2k_p p √(a² − y²)、Hertz k_p (E*/R)(a² − y²)、回る平板の asinh の式)、拭けた帯の幅と
    最小の力、平行な一筆の面積(端の円の和集合)、弾性床のパッドで粗さが exp(−k_p k_w v t) で減ること。
  * **物理エンジン(--full)**: MuJoCo で円柱の工具を手首のばねで板に押し付けて動かした時の接触力・摩擦・軌跡(柔らかい手首 300 N/m と
    硬い手首 10 kN/m、板の高さの誤差 ±1 mm)。

門(既定 10 本は numpy、--full でさらに MuJoCo の 5 本):
  1 除去の地図の 2 つの実装(直接の積分 / 軌跡の線密度と圧力の窓の FFT 畳み込み)/ 2 一筆の断面 = 閉形式(平板・Hertz・回る平板)と
  体積 = k_p F / 3 力と速さの法則(平板は力に比例、Hertz は放物線の曲率が力に依らない、回ると 1/v)/ 4 画像から読んだ帯の幅 = 閉形式
  (Otsu のしきい値が意味する残膜を戻す)と罠 / 5 拭ける最小の力: 「きれいになった」画素は F_min の下で 0 / 6 平行な一筆の面積 /
  7 前後の高さ図から削れた深さと Preston 係数(と参照の枠の罠)/ 8 弾性床のパッドで粗さが減る(roughness の Sq で)と部分接触で外れる /
  9 膜の画像の往復 / 10 綴り壊し;
  --full: 11 押し付けの静的な力・摩擦・横の遅れ / 12 一筆の間の力 = ばねの閉形式(柔らかい手首)と離れる位置(硬い手首)/
  13 MuJoCo の力で作った拭き跡の画像の帯の幅 = 力が変わる一筆の閉形式 / 14 柔らかい手首は帯がそろい、硬い手首はばらつき途中で切れる /
  15 1 列ごとの除去体積 = k F(MuJoCo の力)。
図(FULLSEYE_FIGURE_DIR があるとき、等倍): 既定 6 枚 = 平行に拭く動く図(残った膜と工具の輪)、一筆の断面(地図の点と閉形式の破線)、
帯の幅 vs 力(画像の読みと閉形式)、前後の高さ図と読んだ深さ、粗さの減り方(exp の破線と部分接触)、面積 vs 間隔;
--full でさらに 2 枚 = 一筆の間の力(柔らかい / 硬い手首、ばねの閉形式の破線)、MuJoCo の力で拭いた跡の画像(2 段)。
正直に: Preston の原文(1927)は読めていない。拭き取りの係数(膜の除去係数)は実測値の無い仮の値で、帯の幅の門は「同じ係数で閉形式と
画像が合うか」を見るもの。弾性床は仮定(パッドの曲げ・粘弾性・砥粒の大きさは入れない)。高さ図は前後で横にずれない前提。
Run: py -3.11 examples/poc_polish_wipe_measure.py [--full]        (--full は mujoco)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import polish as S  # noqa: E402

FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []
# 拭き取り(汚れの膜): 平らなパッド a = 8 mm、球のパッド R = 50 mm・E* = 2 MPa、膜 1 µm、除去係数は仮の値(拭ける最小の力が 2 N になる値)
A_PAD, R_BALL, E_BALL = 8.0e-3, 0.05, 2.0e6
H0 = 1.0e-6
K_SOIL = math.pi * A_PAD * H0 / (2.0 * 2.0)
# 研磨(ガラス): k_p = 1e-12 m²/N(Shen ほか 2018 のセリアの範囲)、10 N、600 rpm、送り 1 mm/s
K_GLASS, F_POL, OMEGA, V_POL = 1.0e-12, 10.0, 2.0 * math.pi * 10.0, 1.0e-3
BARE, TAU = 0.85, math.log(4.0)


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail), flush=True)


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _stroke_map(F, kind, shape=(201, 121), res=1.0e-4, k=K_SOIL, **kw):
    R = A_PAD if kind == "flat" else R_BALL
    es = None if kind == "flat" else E_BALL
    return S.preston_removal_map(np.array([[-0.03, 0.0], [0.03, 0.0]]), F, R, k, shape=shape, res=res, kind=kind, speed=5e-3,
                                 estar=es, **kw)


def _read_band(img, res, coat=H0, threshold=None):
    """画像 → (しきい値、残膜、帯の幅の中央値)。threshold が無ければ Otsu(wipe_coverage = detect.segment_objects)。"""
    if threshold is None:
        cov = S.wipe_coverage(img, res, coat=coat, optical_depth=TAU, bare=BARE)
        thr, resid = cov["threshold"], cov["residual_at_threshold"]
    else:
        thr = threshold
        resid = coat * math.log(BARE / thr) / TAU
    prof = S.band_width_profile(img, thr, res)
    return thr, resid, prof


def numpy_part() -> dict:
    out = {}
    # ---- 門 1 二つの実装
    t0 = time.time()
    rows = []
    ell = np.array([[0.012 * math.cos(t), 0.006 * math.sin(t)] for t in np.linspace(0.0, 5.0, 60)])
    straight = np.array([[-0.03, 0.0], [0.03, 0.0]])
    for pname, path in (("straight", straight), ("arc", ell)):
        for kind, R, es in (("flat", A_PAD, None), ("hertz", R_BALL, E_BALL)):
            md = S.preston_removal_map(path, 10.0, R, K_SOIL, shape=(181, 401), res=1e-4, kind=kind, speed=5e-3, estar=es)
            mf = S.preston_removal_map(path, 10.0, R, K_SOIL, shape=(181, 401), res=1e-4, kind=kind, speed=5e-3, estar=es, method="fft")
            rows.append((pname, kind, float(np.sqrt(np.mean((md - mf) ** 2)) / md.max()), float(md.sum() / mf.sum())))
    worst_rms = max(r[2] for r in rows)
    worst_vol = max(abs(r[3] - 1) for r in rows)
    gate("門 1 除去の地図の 2 つの実装(小区間ごとに窓の画素で足す直接の積分 / 軌跡の線密度と正規化した圧力の窓の FFT 畳み込み)が、直線と楕円の弧 × "
         "平板と Hertz の 4 組で rms < 1 % of peak、体積の比 < 1e-3", worst_rms < 0.01 and worst_vol < 1e-3,
         "(rms 最大 %.4f、体積 最大 %.1e、%.2f s)" % (worst_rms, worst_vol, time.time() - t0))
    out["impl"] = rows
    # ---- 門 2 断面の閉形式
    t0 = time.time()
    H, W, res = 241, 121, 1e-4
    y = ((H - 1) / 2.0 - np.arange(H)) * res
    prof = {}
    errs, vols = {}, {}
    for name, kind, kw in (("flat", "flat", {}), ("hertz", "hertz", {}), ("flat spinning", "flat", {"spin": OMEGA})):
        R = A_PAD if kind == "flat" else R_BALL
        es = None if kind == "flat" else E_BALL
        k = K_GLASS
        v = V_POL
        m = S.preston_removal_map(np.array([[-0.03, 0.0], [0.03, 0.0]]), F_POL, R, k, shape=(H, W), res=res, kind=kind, speed=v,
                                  estar=es, **kw)
        th = S.preston_track_profile(y, F_POL, R, k, kind=kind, speed=v, estar=es, **kw)
        col = m[:, W // 2]
        errs[name] = float(np.max(np.abs(col - th)) / th.max())
        vols[name] = float(col.sum() * res / (k * F_POL))
        prof[name] = (y, col, th)
    gate("門 2 長い直線の一筆の断面: 地図の中央の列 = 閉形式(平板 2k_p p √(a² − y²)、Hertz k_p (E*/R)(a² − y²)、600 rpm で回る平板の asinh の式)が "
         "最大誤差 < 0.5 %% of peak、体積 / 長さ = k_p F(平板・Hertz、< 1e-3)。回ると体積は k_p F の %.0f 倍" % vols["flat spinning"],
         max(errs.values()) < 0.005 and abs(vols["flat"] - 1) < 1e-3 and abs(vols["hertz"] - 1) < 1e-3,
         "(誤差 %s、体積比 平板 %.5f Hertz %.5f、%.2f s)" % ({k_: round(v_, 5) for k_, v_ in errs.items()}, vols["flat"], vols["hertz"], time.time() - t0))
    out["profiles"] = prof
    # ---- 門 3 法則
    t0 = time.time()
    curv, cdepth = [], []
    for F in (2.0, 5.0, 10.0):
        m = S.preston_removal_map(np.array([[-0.03, 0.0], [0.03, 0.0]]), F, R_BALL, K_GLASS, shape=(H, W), res=res, kind="hertz",
                                  speed=V_POL, estar=E_BALL)
        col = m[:, W // 2]
        a = S.wipe_band_width(F, R_BALL, K_GLASS, 1e-30, kind="hertz", estar=E_BALL)["a"]
        sel = np.abs(y) < 0.7 * a
        c2 = np.polyfit(y[sel], col[sel], 2)[0]
        curv.append(-c2 / (K_GLASS * E_BALL / R_BALL))
        mf = S.preston_removal_map(np.array([[-0.03, 0.0], [0.03, 0.0]]), F, A_PAD, K_GLASS, shape=(H, W), res=res, speed=V_POL)
        cdepth.append(float(mf[H // 2, W // 2]) / F)
    sp = [float(S.preston_removal_map(np.array([[-0.03, 0.0], [0.03, 0.0]]), F_POL, A_PAD, K_GLASS, shape=(H, W), res=res, speed=v,
                                      spin=OMEGA)[H // 2, W // 2]) * v for v in (1e-3, 2e-3, 4e-3)]
    v4 = [float(S.preston_removal_map(np.array([[-0.03, 0.0], [0.03, 0.0]]), F_POL, A_PAD, K_GLASS, shape=(H, W), res=res,
                                      speed=v)[H // 2, W // 2]) for v in (1e-3, 4e-3)]
    ok3 = (max(abs(c - 1) for c in curv) < 0.01 and np.ptp(cdepth) / np.mean(cdepth) < 1e-9
           and np.ptp(sp) / np.mean(sp) < 0.01 and abs(v4[1] / v4[0] - 1) < 1e-12)
    gate("門 3 法則: Hertz の工具の跡の放物線の曲率 = k_p E*/R で力 2 / 5 / 10 N に依らない(< 1 %)、平板の中心の深さ / F が一定、回らなければ"
         "速さに依らない、回る平板は深さ × v が一定(相対速度の大半は ω r なので 1 % 以内)", ok3,
         "(曲率 / 閉形式 %s、深さ×v の ptp %.4f、%.2f s)" % ([round(c, 4) for c in curv], np.ptp(sp) / np.mean(sp), time.time() - t0))
    # ---- 門 4 帯の幅
    t0 = time.time()
    band = []
    trap = []
    for kind, R, es, Fs in (("flat", A_PAD, None, (2.5, 4.0, 8.0, 16.0)), ("hertz", R_BALL, E_BALL, (0.6, 1.5, 4.0, 10.0))):
        for F in Fs:
            m = _stroke_map(F, kind)
            img = S.coat_image(m, H0, optical_depth=TAU, bare=BARE, noise=0.01, seed=int(F * 10))
            thr, resid, pr = _read_band(img, 1e-4)
            th = S.wipe_band_width(F, R, K_SOIL, H0 - resid, kind=kind, estar=es)["width"]
            naive = S.wipe_band_width(F, R, K_SOIL, H0, kind=kind, estar=es)["width"]
            band.append((kind, F, pr["median"], th, naive, resid / H0))
            trap.append(abs(naive / pr["median"] - 1))
    berr = max(abs(b[2] / b[3] - 1) for b in band)
    gate("門 4 膜の画像(Beer–Lambert、雑音 1 %%)から帯の幅: Otsu(detect.segment_objects)のしきい値の明るさを残膜の厚さに戻し(しきい値は"
         "「除去 ≥ h0 − 残膜」の所)、副画素で読んだ幅の中央値 = 閉形式が平板 4 力・Hertz 4 力で < 1 %%; 罠: しきい値の意味を忘れて h0 のまま"
         "閉形式に入れると最大 %.0f %% 外れる" % (100 * max(trap)), berr < 0.01 and max(trap) > 0.05,
         "(最大誤差 %.4f、しきい値の残膜 / h0 = %s、%.2f s)" % (berr, sorted(set(round(b[5], 2) for b in band)), time.time() - t0))
    out["band"] = band
    # ---- 門 5 拭ける最小の力
    t0 = time.time()
    thr_clean = BARE * math.exp(-TAU * 0.05)               # 残膜 ≤ 5 % を「きれい」とする明るさ
    fmin = S.wipe_band_width(1.0, A_PAD, K_SOIL, 0.95 * H0)["force_min"]
    sweep = []
    for F in fmin * np.array([0.9, 0.97, 1.03, 1.2, 2.0]):
        m = _stroke_map(float(F), "flat")
        img = S.coat_image(m, H0, optical_depth=TAU, bare=BARE)
        n_clean = int(np.sum(img >= thr_clean))
        pr = S.band_width_profile(img, thr_clean, 1e-4)
        th = S.wipe_band_width(float(F), A_PAD, K_SOIL, 0.95 * H0)["width"]
        sweep.append((float(F), n_clean, pr["median"] if n_clean else 0.0, th))
    ok5 = (sweep[0][1] == 0 and sweep[1][1] == 0 and all(s_[1] > 0 for s_ in sweep[2:])
           and all(abs(s_[2] / s_[3] - 1) < 0.02 for s_ in sweep[3:]))
    gate("門 5 拭ける最小の力 F_min = π a h0'/(2k)(h0' = 0.95 h0、残膜 ≤ 5 % を「きれい」とする): 0.90 / 0.97 F_min で「きれい」な画素 0、"
         "1.03 F_min から帯が現れ、1.2 / 2.0 F_min の幅が閉形式に 2 % 以内", ok5,
         "(F_min %.3f N、%s、%.2f s)" % (fmin, [(round(a_, 2), b_, round(c_ * 1e3, 3), round(d_ * 1e3, 3)) for a_, b_, c_, d_ in sweep], time.time() - t0))
    out["fmin"] = (fmin, sweep)
    # ---- 門 6 平行な一筆の面積
    t0 = time.time()
    a6, L6, N6, res6 = 5.0e-3, 0.03, 4, 2.0e-4
    F6 = 10.0
    h6 = 2 * a6 * K_SOIL * F6 / (math.pi * a6 * a6) / 1000.0     # 中心の深さの 1/1000 の薄い膜(縁の取り残しを無視できる)
    areas = []
    for so in (0.5, 1.0, 1.6, 2.4):
        ra = S.raster_wipe_area(a6, L6, so * a6, N6, centre=(0.31 * res6, 0.27 * res6))   # 軸に平行な縁を画素の中心に載せない
        Hh = int(((N6 - 1) * so * a6 + 2 * a6) / res6) + 30
        Ww = int((L6 + 2 * a6) / res6) + 30
        m = S.preston_removal_map(ra["path"], F6, a6, K_SOIL, shape=(Hh, Ww), res=res6, speed=0.02)
        img = S.coat_image(m, h6, optical_depth=TAU, bare=BARE, noise=0.01, seed=1)
        cov = S.wipe_coverage(img, res6)
        areas.append((so, cov["area"], ra["area"], cov["n_regions"], ra["overlap_saving"] / (N6 * (2 * a6 * L6 + math.pi * a6 * a6))))
    aerr = max(abs(a_[1] / a_[2] - 1) for a_ in areas)
    gate("門 6 平行な 4 本の一筆(持ち上げて戻る)で拭けた面積: 画像(Otsu)= 閉形式 (2a + (N−1)min(s, 2a))L + Nπa² − (N−1)lens(s) が間隔 "
         "0.5a / 1.0a / 1.6a / 2.4a で < 1 %、2.4a(> 2a)では領域が 4 つに分かれる", aerr < 0.01 and areas[-1][3] == N6 and areas[0][3] == 1,
         "(最大誤差 %.4f、重なりで減った割合 %s、%.2f s。型を画素の中心から 0.3 画素ずらして置く —— 軸に平行な縁が画素の中心に載ると 1 列まるごと落ちて最大 −1.7 %%)"
         % (aerr, [round(a_[4], 3) for a_ in areas], time.time() - t0))
    out["areas"] = areas
    # ---- 門 7 高さ図
    t0 = time.time()
    import roughness as RG
    H7, W7, res7 = 241, 161, 1e-4
    x7 = (np.arange(W7) - (W7 - 1) / 2.0) * res7
    y7 = ((H7 - 1) / 2.0 - np.arange(H7)) * res7
    X7, Y7 = np.meshgrid(x7, y7)
    true = np.repeat(S.preston_track_profile(y7, F_POL, A_PAD, K_GLASS, spin=OMEGA, speed=V_POL)[:, None], W7, axis=1)
    zb, _ = RG.surface_synth_psd((H7, W7), res7, 0.8, 4e-4, 5e-3, 20e-9, seed=3)
    rng = np.random.default_rng(5)
    z_before = zb + 3e-6 * X7 / 0.01 + rng.normal(0, 1e-9, zb.shape)
    z_after = zb - true + 50e-9 - 2e-6 * Y7 / 0.01 + 1e-6 * X7 / 0.01 + rng.normal(0, 1e-9, zb.shape)    # 載せ直しで傾きと高さが変わる
    ref = np.abs(Y7) > A_PAD + 1e-3
    d = S.removal_depth_from_heights(z_before, z_after, ref_mask=ref)
    derr = float(np.sqrt(np.mean((d - true) ** 2)))
    dwell = S.preston_removal_map(np.array([[-0.05, 0.0], [0.05, 0.0]]), F_POL, A_PAD, 1.0, shape=(H7, W7), res=res7, speed=V_POL, spin=OMEGA)
    fit = S.preston_coefficient_fit(d, dwell)
    d_bad = S.removal_depth_from_heights(z_before, z_after)
    fit_bad = S.preston_coefficient_fit(d_bad, dwell)
    ok7 = derr < 2.0e-9 and abs(fit["k_p"] / K_GLASS - 1) < 0.01 and abs(fit_bad["k_p"] / K_GLASS - 1) > 0.1
    gate("門 7 前後の高さ図(粗さ Sq 20 nm = roughness.surface_synth_psd、測定の雑音 1 nm、載せ直しの傾き)から削れた深さ: 閉形式の断面で作った後の図"
         "(地図の積分を使わない)を、触れていない帯で平面を引いて読むと rms 誤差 < 2 nm(深さ %.0f nm)、直接の積分の滞在の地図で当てた Preston 係数が"
         " 1 %% 以内; 罠: 既定の外周の枠を参照にすると(軌跡が左右の縁を横切る)係数が 10 %% 以上外れる" % (true.max() * 1e9), ok7,
         "(rms %.2f nm、k_p 比 %.4f(切片つき %.4f、R² %.4f)、罠 %.3f、%.2f s)" % (derr * 1e9, fit["k_p"] / K_GLASS, fit["k_p_affine"] / K_GLASS,
                                                                      fit["r2"], fit_bad["k_p"] / K_GLASS, time.time() - t0))
    out["heights"] = (z_before, z_after, d, true)
    # ---- 門 8 弾性床
    t0 = time.time()
    p_bar, k_w, v8, T8 = 3.0e4, 1.0e10, 1.0, 200.0
    runs = {}
    for name, sq0 in (("full", 0.3e-6), ("partial", 3.0e-6)):
        z0, _ = RG.surface_synth_psd((96, 96), 20e-6, 0.8, 6e-5, 4e-4, sq0, seed=7)
        r = S.winkler_polish_run(z0, p_bar, k_w, K_GLASS, v8, T8)
        c = K_GLASS * k_w * v8                                  # 閉形式の速さ(この関数の戻り値を使わない)
        pred = r["rms"][0] * np.exp(-c * r["t"])
        res0, _ = RG.surface_form_remove(z0, 20e-6, order=1)
        res1, _ = RG.surface_form_remove(r["z"], 20e-6, order=1)
        sq_ratio = RG.surface_params(res1, 20e-6)["Sq"] / RG.surface_params(res0, 20e-6)["Sq"]
        runs[name] = {"r": r, "pred": pred, "dev": float(np.max(np.abs(r["rms"] / pred - 1))), "sq_ratio": sq_ratio,
                      "closed": math.exp(-c * T8), "mean": float((r["mean"][0] - r["mean"][-1]) / (K_GLASS * p_bar * v8 * T8)),
                      "contact": float(r["contact"].min())}
    f_, p_ = runs["full"], runs["partial"]
    ok8 = (f_["contact"] == 1.0 and f_["dev"] < 0.005 and abs(f_["sq_ratio"] / f_["closed"] - 1) < 0.01 and abs(f_["mean"] - 1) < 1e-9
           and p_["contact"] < 1.0 and p_["dev"] > 0.05 and abs(p_["mean"] - 1) < 1e-9)
    gate("門 8 弾性床のパッド(k_w = 10¹⁰ Pa/m、平均圧 30 kPa、相対速度 1 m/s、200 s): 全面が当たる粗さ 0.3 µm では平均からのずれの rms が "
         "exp(−k_p k_w v t) に 0.5 %% 以内・roughness の Sq(面の傾きを除き surface_params)の比も 1 %% 以内、平均の下がりは k_p p̄ v t(1e-9); "
         "山だけが当たる 3 µm では式から 5 %% 以上外れる(当たる割合の最小 %.2f)" % p_["contact"], ok8,
         "(全面: 最大のずれ %.4f、Sq 比 %.4f vs %.4f。部分: ずれ %.3f、%.2f s)" % (f_["dev"], f_["sq_ratio"], f_["closed"], p_["dev"], time.time() - t0))
    out["winkler"] = runs
    # ---- 門 9 往復
    m = _stroke_map(5.0, "flat")
    t_true = np.clip(H0 - m, 0.0, H0)
    t_back = S.coat_thickness_from_image(S.coat_image(m, H0, optical_depth=TAU, bare=BARE), H0, optical_depth=TAU, bare=BARE)
    e9 = float(np.max(np.abs(t_back - t_true)))
    gate("門 9 膜の画像の往復: coat_thickness_from_image(coat_image(深さ)) = clip(h0 − 深さ, 0, h0)(雑音なし、< 1e-15 m)", e9 < 1e-15, "(最大 %.1e m)" % e9)
    # ---- 門 10 綴り壊し
    P2 = np.array([[0.0, 0.0], [0.01, 0.0]])
    bad_calls = [
        lambda: S.preston_pressure_kernel(0.0, A_PAD, 1e-4), lambda: S.preston_pressure_kernel(1.0, A_PAD, 1e-4, kind="cone"),
        lambda: S.preston_pressure_kernel(1.0, R_BALL, 1e-4, kind="hertz"), lambda: S.preston_pressure_kernel(1.0, A_PAD, 0.02),
        lambda: S.preston_removal_map(P2, 1.0, A_PAD, K_SOIL), lambda: S.preston_removal_map(np.array([[0.0, 0.0]]), 1.0, A_PAD, K_SOIL, speed=1.0),
        lambda: S.preston_removal_map(np.array([[0.0, 0.0], [np.nan, np.nan], [1.0, 1.0]]), 1.0, A_PAD, K_SOIL, speed=1.0),
        lambda: S.preston_removal_map(P2, 1.0, A_PAD, K_SOIL, speed=1.0, spin=3.0, method="fft"),
        lambda: S.preston_removal_map(P2, np.array([1.0, 2.0]), A_PAD, K_SOIL, speed=1.0, method="fft"),
        lambda: S.preston_removal_map(P2, 1.0, A_PAD, K_SOIL, times=np.array([1.0, 1.0])),
        lambda: S.preston_removal_map(P2, 1.0, A_PAD, K_SOIL, speed=1.0, method="euler"),
        lambda: S.preston_track_profile(np.zeros(3), 1.0, A_PAD, K_SOIL, spin=2.0),
        lambda: S.preston_track_profile(np.zeros(3), 1.0, R_BALL, K_SOIL, kind="hertz", estar=E_BALL, spin=2.0, speed=1.0),
        lambda: S.wipe_band_width(1.0, A_PAD, K_SOIL, 0.0), lambda: S.raster_wipe_area(A_PAD, 0.03, 0.01, 0),
        lambda: S.raster_wipe_area(A_PAD, 0.03, 0.01, 2.5), lambda: S.coat_image(np.zeros((4, 4)), H0, bare=1.5),
        lambda: S.coat_image(np.full((4, 4), np.nan), H0), lambda: S.wipe_coverage(np.full((8, 8), 0.5), 1e-4),
        lambda: S.band_width_profile(np.zeros((8, 8)), 0.5, 1e-4, along="z"),
        lambda: S.removal_depth_from_heights(np.zeros((8, 8)), np.zeros((8, 9))),
        lambda: S.removal_depth_from_heights(np.zeros((8, 8)), np.zeros((8, 8)), ref_mask=np.zeros((8, 8), bool)),
        lambda: S.preston_coefficient_fit(np.ones((8, 8)), np.zeros((8, 8))),
        lambda: S.winkler_polish_run(np.zeros((8, 8)), 3e4, 1e10, 1e-12, 1.0, 10.0, dt=10.0),
        lambda: S.polish_scene_mjcf(k_z=-1.0),
    ]
    nbad = sum(_raises(f) for f in bad_calls)
    xml = S.polish_scene_mjcf()
    ok10 = nbad == len(bad_calls) and xml.count("<joint") == 3 and xml.count("<position") == 3 and 'type="cylinder"' in xml
    gate("門 10 綴り壊し %d 本は全部 ValueError(fail-closed)、MJCF は直動の関節 3 本・位置サーボ 3 本・円柱の工具" % len(bad_calls), ok10,
         "(%d / %d)" % (nbad, len(bad_calls)))
    return out


# ======================================================================================================================
def _band_varying_force(xs_eval, s_rec, F_rec, a, k, coat, n_y=400):
    """力が変わる直線の一筆(平板)の帯の半幅: h(x, y) = (k/(πa²)) ∫_{x−c}^{x+c} F(s) ds、c = √(a² − y²) を y の二分法で h = coat に。
    MuJoCo の力の記録を s(進んだ道のり)で 1 次元に積分するだけで、2-D の地図の積分を使わない(第 2 の経路)。"""
    order = np.argsort(s_rec)
    s_sorted, F_sorted = s_rec[order], F_rec[order]
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (F_sorted[1:] + F_sorted[:-1]) * np.diff(s_sorted))])

    def integ(lo, hi):
        return float(np.interp(hi, s_sorted, cum) - np.interp(lo, s_sorted, cum))

    out = np.zeros(len(xs_eval))
    for i, x in enumerate(xs_eval):
        def h(yv):
            c = math.sqrt(max(0.0, a * a - yv * yv))
            return k / (math.pi * a * a) * integ(x - c, x + c)
        if h(0.0) < coat:
            continue
        lo, hi = 0.0, a
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if h(mid) >= coat:
                lo = mid
            else:
                hi = mid
        out[i] = 2.0 * lo
    return out


def full_part(out) -> dict:
    import mujoco  # noqa: F401
    t0 = time.time()
    mass, mu, kxy = 0.2, 0.3, 2.0e4
    g = 9.81
    # ---- 門 11 静的な押し付け
    st = []
    for kz, depths in ((300.0, (0.01, 0.03)), (1.0e4, (2e-4, 1e-3))):
        sc = S.polish_scene_build(k_z=kz, mass=mass, friction=mu, k_xy=kxy)
        for dd in depths:
            r = S.polish_stroke_run(sc, np.array([[0.0, 0.0], [0.002, 0.0]]), np.array([-dd, -dd]), speed=0.01, settle=0.5)
            N = float(np.mean(r["normal"][-20:]))
            ft = float(np.mean(np.hypot(*r["tangent"][-20:].T)))
            lag = float(np.mean(r["cmd_xy"][-20:, 0] - r["xy"][-20:, 0]))
            lag_th = (mu * N + 2.0 * math.sqrt(kxy * mass) * 0.01) / kxy
            st.append((kz, dd, N / (mass * g + kz * dd), ft / N, lag / lag_th, float(r["z"][-1])))
        S.polish_scene_close(sc)
    soft = [s_ for s_ in st if s_[0] == 300.0]
    stiff = [s_ for s_ in st if s_[0] != 300.0]
    ok11 = (all(abs(s_[2] - 1) < 0.005 for s_ in soft) and all(abs(s_[3] / mu - 1) < 0.01 for s_ in st)
            and all(abs(s_[4] - 1) < 0.06 for s_ in st))
    gate("門 11 MuJoCo の押し付け: 柔らかい手首(300 N/m、押し込み 10 / 30 mm)の接触の法線力 = m g + k Δ(< 0.5 %)、滑っている間の接線力 / 法線力 = μ"
         "(< 1 %)、横の遅れ = (μN + c v)/k_xy(< 6 %)。硬い手首(10 kN/m)は接触のめり込みが ばねと直列に効いて閉形式より小さい(内訳に出す)", ok11,
         "(柔らかい %s、硬い %s、%.2f s)" % ([(round(s_[2], 4), round(s_[3], 4), round(s_[4], 3)) for s_ in soft],
                                       [(round(s_[2], 3), round(s_[5] * 1e6, 1)) for s_ in stiff], time.time() - t0))
    # ---- 門 12〜15 一筆
    t0 = time.time()
    grade = 0.025                                  # 板の高さの誤差: 80 mm で 2 mm
    xs = np.linspace(-0.04, 0.04, 81)
    path = np.stack([xs, np.zeros_like(xs)], axis=1)
    strokes = {}
    for name, kz, d0 in (("compliant", 300.0, 0.03), ("stiff", 1.0e4, 0.3e-3)):
        sc = S.polish_scene_build(k_z=kz, mass=mass, friction=mu, k_xy=kxy)
        r = S.polish_stroke_run(sc, path, -d0 + grade * xs, speed=0.02, settle=0.5)
        S.polish_scene_close(sc)
        pred = np.maximum(0.0, mass * g + kz * (-r["z_cmd"]))
        strokes[name] = {"r": r, "pred": pred, "kz": kz, "d0": d0}
    c_ = strokes["compliant"]
    e_c = np.abs(c_["r"]["normal"] / c_["pred"] - 1)
    s_ = strokes["stiff"]
    x_off_th = (s_["d0"] + mass * g / s_["kz"]) / grade
    xm = s_["r"]["cmd_xy"][:, 0]
    off_meas = float(xm[np.argmax(s_["r"]["normal"] < 0.01)]) if np.any(s_["r"]["normal"] < 0.01) else float("nan")
    gate("門 12 一筆の間の法線力: 柔らかい手首は ばねの閉形式 m g + k (Δ0 − g_x x)(板の高さの誤差 2 mm / 80 mm)に 99 %% 点で < 1 %%; 硬い手首は"
         "閉形式の離れる位置 x* = (Δ0 + m g/k)/g_x = %.1f mm で工具が浮く(MuJoCo の最初の 0 が 1 mm 以内)" % (x_off_th * 1e3),
         np.percentile(e_c, 99) < 0.01 and abs(off_meas - x_off_th) < 1e-3,
         "(柔らかい 99 %% 点 %.4f 最大 %.4f、硬い 浮く位置 %.2f mm、%.2f s)" % (np.percentile(e_c, 99), e_c.max(), off_meas * 1e3, time.time() - t0))
    # 拭き跡の画像: MuJoCo の実測の軌跡と力で地図 → 膜の画像 → しきい値 → 列ごとの帯の幅
    t0 = time.time()
    res, H, W = 2.0e-4, 121, 521
    h0 = 1.0e-6
    k_w = K_SOIL
    cols_x = (np.arange(W) - (W - 1) / 2.0) * res
    for name, st_ in strokes.items():
        r = st_["r"]
        m = S.preston_removal_map(r["xy"], r["normal"], A_PAD, k_w, shape=(H, W), res=res, times=r["t"])
        img = S.coat_image(m, h0, optical_depth=TAU, bare=BARE, noise=0.01, seed=3)
        thr_clean = BARE * math.exp(-TAU * 0.3)
        pr = S.band_width_profile(img, thr_clean, res)
        s_rec = r["xy"][:, 0]
        th = _band_varying_force(cols_x, s_rec, r["normal"], A_PAD, k_w, 0.7 * h0)
        vol = m.sum(axis=0) * res                           # 列ごとの除去体積 / 列幅 = k ∫F ds の窓…の代わりに全体で比べる
        st_.update({"map": m, "img": img, "widths": np.where(pr["valid"], pr["widths"], 0.0), "th_widths": th,
                    "vol_ratio": float(m.sum() * res * res / (k_w * np.trapezoid(r["normal"], s_rec))) if hasattr(np, "trapezoid")
                    else float(m.sum() * res * res / (k_w * np.trapz(r["normal"], s_rec))), "vol_cols": vol})
    inner = np.abs(cols_x) < 0.04 - A_PAD - 1e-3              # 端の円の影響を外す
    e13 = {}
    for name, st_ in strokes.items():
        w_img, w_th = st_["widths"][inner], st_["th_widths"][inner]
        both = (w_th > 0) & (w_img > 0)
        e13[name] = (float(np.median(np.abs(w_img[both] / w_th[both] - 1))), float(np.percentile(np.abs(w_img[both] / w_th[both] - 1), 95)),
                     int(np.sum((w_th > 0) != (w_img > 0))))
    gate("門 13 MuJoCo の実測の軌跡と力(柔らかい / 硬い手首)で拭いた跡の画像から列ごとの帯の幅(残膜 ≤ 30 % を「きれい」)= 力が変わる一筆の閉形式"
         "(MuJoCo の力を道のりで 1 次元に積分、2-D の地図を使わない)が中央値 < 1 %、95 % 点 < 3 %、帯の有無の食い違い ≤ 2 列",
         all(v_[0] < 0.01 and v_[1] < 0.03 and v_[2] <= 2 for v_ in e13.values()),
         "(%s、%.2f s)" % ({k_: (round(v_[0], 4), round(v_[1], 4), v_[2]) for k_, v_ in e13.items()}, time.time() - t0))
    wc = strokes["compliant"]["widths"][inner]
    ws = strokes["stiff"]["widths"][inner]
    cv_c = float(np.std(wc) / np.mean(wc))
    gap_cols = int(np.sum(ws == 0))
    cv_s = float(np.std(ws[ws > 0]) / np.mean(ws[ws > 0])) if np.any(ws > 0) else float("nan")
    gate("門 14 柔らかい手首は板の高さの誤差 2 mm でも帯の幅がそろい(変動係数 < 2 %)、硬い手首は幅がばらつき(> 10 %)途中で拭けない列が出る"
         "—— 可変コンプライアンスで拭く理由を、学習なしで帯の幅の画像から", cv_c < 0.02 and cv_s > 0.10 and gap_cols > 10,
         "(柔らかい %.4f、硬い %.3f、拭けない列 %d / %d)" % (cv_c, cv_s, gap_cols, int(inner.sum())))
    v15 = {k_: round(v_["vol_ratio"], 5) for k_, v_ in strokes.items()}
    gate("門 15 Preston の保存: MuJoCo の力で積分した地図の全除去体積 = k ∫ F ds(実測の力と道のり、柔らかい / 硬い手首)が 0.5 % 以内"
         "(地図の外にこぼれる端の円を含めるため地図は一筆より 2 a 以上広い)", all(abs(v_ - 1) < 0.005 for v_ in v15.values()), "(%s)" % v15)
    out["strokes"] = strokes
    return out


# ======================================================================================================================
def _ring(rgb, cx, cy, rad, col):
    t = np.linspace(0, 2 * math.pi, 360)
    xx = np.round(cx + rad * np.cos(t)).astype(int)
    yy = np.round(cy + rad * np.sin(t)).astype(int)
    ok = (xx >= 0) & (xx < rgb.shape[1]) & (yy >= 0) & (yy < rgb.shape[0])
    rgb[yy[ok], xx[ok]] = col


def figures(out):
    t0 = time.time()
    # 1. 平行に拭く動く図
    a, L, N, res = 5.0e-3, 0.03, 4, 1.0e-4
    so = 1.2
    ra = S.raster_wipe_area(a, L, so * a, N)
    Hh = int(((N - 1) * so * a + 2 * a) / res) + 40
    Ww = int((L + 2 * a) / res) + 40
    F = 10.0
    h_f = 2 * a * K_SOIL * F / (math.pi * a * a) / 3.0
    Cc, DS, V, D, FF, LAB = S._segment_samples(ra["path"], F, None, 0.02, res / 4.0, "fig")
    frames_at = np.linspace(0, len(Cc) - 1, 36).astype(int)
    _, snaps = S._removal_direct((Hh, Ww), res, Cc, DS, V, D, FF, a, "flat", None, K_SOIL, 0.0, frames=frames_at)
    frames = []
    for i, sn in zip(frames_at, snaps):
        img = S.coat_image(sn, h_f, optical_depth=TAU, bare=BARE)
        rgb = np.stack([img * 0.95, img * 0.9, img * 0.75], axis=2) * 255.0
        cx = Cc[i, 0] / res + (Ww - 1) / 2.0
        cy = (Hh - 1) / 2.0 - Cc[i, 1] / res
        _ring(rgb, cx, cy, a / res, (40, 110, 220))
        _ring(rgb, cx, cy, a / res - 1, (40, 110, 220))
        frames.append(np.clip(rgb, 0, 255).astype(np.uint8))
    final_area = S.wipe_coverage(S.coat_image(snaps[-1], h_f, optical_depth=TAU, bare=BARE), res)["area"]
    figs.save_gif("polish_raster_wipe_coat", frames, fps=6.0,
                  caption="半径 5 mm の平らなパッドで、長さ 30 mm の一筆を間隔 1.2a で 4 本(持ち上げて戻る)。暗い所 = 残った膜(Beer–Lambert)、青い輪 = "
                          "工具。最後の画像で拭けた面積 %.1f mm²、閉形式 (2a + (N−1)min(s, 2a))L + Nπa² − (N−1)lens(s) = %.1f mm²。縁は膜が薄くなるだけで"
                          "消えきらない所があり(パッドの縁は通過の弦が短い)、Otsu のしきい値がその途中に入る。" % (final_area * 1e6, ra["area"] * 1e6))
    # 2. 断面
    series, kinds, styles = [], [], []
    for name, (y, col, th) in out["profiles"].items():
        pk = float(th.max())
        series.append(("%s: map (peak %.3g nm)" % (name, pk * 1e9), y[::4] * 1e3, col[::4] / pk))
        kinds.append("scatter")
        styles.append(None)
        series.append(("%s: closed form" % name, y * 1e3, th / pk))
        kinds.append("line")
        styles.append("dashed")
    figs.save_plot("polish_track_profiles_vs_closed_form", series, xlabel="lateral offset y [mm] (left of travel = +)", ylabel="removed depth / closed-form peak",
                   title="One straight stroke: removal map vs closed form", kinds=kinds, styles=styles, size=(640, 400),
                   caption="10 N、k_p = 10⁻¹² m²/N(セリアでガラスを磨く桁)、送り 1 mm/s。平板(半径 8 mm)= 半楕円、球(R = 50 mm、E* = 2 MPa)= Hertz で"
                           "放物線、600 rpm で回る平板 = 進む側(+y で相対速度が小さい)と戻る側で非対称。点 = 地図の中央の列、破線 = 閉形式。回らない時の"
                           "深さは送りの速さに依らない(dx だけで決まる)。縦軸は閉形式の最大で割った(回ると深さが 300 倍以上になるので)。")
    # 3. 帯の幅 vs 力
    series, kinds, styles, colors = [], [], [], []
    for kind, R, es in (("flat", A_PAD, None), ("hertz", R_BALL, E_BALL)):
        pts = [b for b in out["band"] if b[0] == kind]
        resid = float(np.mean([b[5] for b in pts])) * H0
        Fs = np.geomspace(0.3, 20.0, 160)
        ws = [S.wipe_band_width(float(f), R, K_SOIL, H0 - resid, kind=kind, estar=es)["width"] * 1e3 for f in Fs]
        series.append(("%s: closed form (coat h0 - residual at threshold)" % kind, Fs, np.array(ws)))
        kinds.append("line")
        styles.append("dashed")
        colors.append("reference" if kind == "flat" else "neutral")
        series.append(("%s: read from the image" % kind, np.array([b[1] for b in pts]), np.array([b[2] * 1e3 for b in pts])))
        kinds.append("scatter")
        styles.append(None)
        colors.append("emphasis" if kind == "flat" else "right")
    figs.save_plot("polish_band_width_vs_force", series, xlabel="pressing force F [N]", ylabel="cleaned band width [mm]",
                   title="Wiped band width: image read vs closed form", kinds=kinds, styles=styles, colors=colors, size=(640, 400),
                   caption="膜 1 µm、除去係数は仮の値(平板で拭ける最小の力が 2 N になる値)。平板の幅は 2a√(1 − (h0/D)²) で半径 8 mm の 2 倍に近づき、"
                           "球の幅は Hertz の接触半径とともに F^{1/3} で伸び続ける。画像の読みは Otsu のしきい値が意味する残膜(h0 の約 1/3)を戻して閉形式に入れた。")
    # 4. 高さ図
    import roughness as RG
    zb, za, d, true = out["heights"]
    zb_f = RG.surface_form_remove(zb, 1e-4, order=1)[0]
    za_f = RG.surface_form_remove(za, 1e-4, order=1)[0]
    figs.save_grid("polish_height_maps_depth_read", [zb_f * 1e9, za_f * 1e9, d * 1e9, (d - true) * 1e9],
                   captions=["before, plane removed [nm]", "after, plane removed [nm]", "depth read [nm]", "read - closed form [nm]"], ncols=4,
                   signed=[False, False, False, True], gray=False,
                   caption="16 × 24 mm、画素 0.1 mm。磨く前と後の高さ図(粗さ Sq 20 nm、雑音 1 nm、後は載せ直しで傾きと高さが変わる。見せるために全体の平面を引いた)。軌跡から 1 mm 以上離れた帯で"
                           "平面を引くと、削れた深さ(最大 240 nm)が雑音の桁(rms 1.4 nm)で読める。右端 = 読みと閉形式の差。")
    # 5. 粗さの減り方
    w = out["winkler"]
    series = []
    for name, r_ in w.items():
        r = r_["r"]
        series.append(("%s contact: simulation" % name, r["t"], r["rms"] / r["rms"][0]))
    r = w["full"]["r"]
    series.append(("closed form exp(-k_p k_w v t)", r["t"], w["full"]["pred"] / r["rms"][0]))
    figs.save_plot("polish_roughness_decay_winkler", series, xlabel="time [s]", ylabel="rms height / initial", title="Roughness decay under an elastic pad",
                   kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"], colors=["emphasis", "wrong", "reference"],
                   caption="弾性床のパッド(k_w = 10¹⁰ Pa/m、平均圧 30 kPa、相対速度 1 m/s)。全面が当たる(粗さ 0.3 µm)間は rms が exp(−k_p k_w v t) に乗る。"
                           "粗さ 3 µm では山だけが当たり(当たる割合の最小 %.2f)、谷は削られないので減り方が式より遅い。" % w["partial"]["contact"])
    # 6. 面積 vs 間隔
    ar = out["areas"]
    so_ = np.linspace(0.2, 3.0, 120)
    th = [S.raster_wipe_area(5e-3, 0.03, float(s) * 5e-3, 4)["area"] * 1e6 for s in so_]
    figs.save_plot("polish_raster_area_vs_pitch", [("closed form", so_, np.array(th)), ("image (Otsu)", np.array([a_[0] for a_ in ar]),
                                                                                         np.array([a_[1] * 1e6 for a_ in ar]))],
                   xlabel="pitch s / pad radius a", ylabel="wiped area [mm2]", title="Raster wiping: area vs pitch",
                   kinds=["line", "scatter"], styles=["dashed", None], colors=["reference", "emphasis"],
                   caption="4 本の一筆(長さ 30 mm、パッド半径 5 mm)。s ≥ 2a で帯が離れ、面積は 4 本の和で一定になる(破線の平らな部分)。点 = 膜の画像を Otsu で"
                           "2 値化して数えた面積。")
    if FULL and "strokes" in out:
        _figures_full(out)
    print("  図: %s(%.1f s)" % (figs.errors() or "ok", time.time() - t0))


def _figures_full(out):
    st = out["strokes"]
    series, kinds, styles, colors = [], [], [], []
    for name, s_ in st.items():
        r = s_["r"]
        x = r["cmd_xy"][:, 0] * 1e3
        series += [("%s: MuJoCo contact force" % name, x[::10], r["normal"][::10]), ("%s: spring closed form" % name, x, s_["pred"])]
        kinds += ["scatter", "line"]
        styles += [None, "dashed"]
        colors += ["emphasis" if name == "compliant" else "neutral", "reference"]
    figs.save_plot("polish_mujoco_force_along_stroke", series, xlabel="tool x [mm]", ylabel="normal force [N]",
                   title="Pressing force along one stroke: compliant vs stiff wrist", kinds=kinds, styles=styles, colors=colors, size=(640, 400),
                   caption="板の高さの誤差 2 mm(80 mm で)。柔らかい手首(300 N/m、30 mm 押し込む)は力がほぼ一定で ばねの閉形式どおり。硬い手首(10 kN/m、0.3 mm)"
                           "は力が 15 N から 0 まで変わり、x* = (Δ0 + mg/k)/g で浮く。硬い手首の点のばらつきは接触の細かな跳ね。")
    imgs = [st["compliant"]["img"], st["stiff"]["img"]]
    figs.save_grid("polish_mujoco_wiped_bands", imgs, captions=["compliant wrist 300 N/m", "stiff wrist 10 kN/m"], ncols=1, gray=True,
                   caption="MuJoCo の実測の軌跡と力で拭いた跡(膜 1 µm、画素 0.2 mm、104 × 24 mm)。柔らかい手首は帯がそろい、硬い手首は押しすぎる所で太く、"
                           "浮く所で途切れる。")


def main() -> int:
    t_all = time.time()
    c_all = time.process_time()
    out = numpy_part()
    if FULL:
        out = full_part(out)
    else:
        skip("門 11〜15(MuJoCo)", "--full のときだけ")
    if figs.enabled():
        figures(out)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s、この過程の CPU %.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all, time.process_time() - c_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
