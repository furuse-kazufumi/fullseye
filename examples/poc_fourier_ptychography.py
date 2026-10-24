# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: フーリエ・タイコグラフィ —— 4 倍の対物の広い視野のまま、20 倍相当の分解能と位相を、反復の位相回復で得る。

    py -3.11 examples/poc_fourier_ptychography.py

【問い】低倍率の対物(4 倍、NA 0.1)は視野が広いが分解能が低い。LED アレイで照明の角度を変えて 169 枚撮り、
周波数空間でつなぐと、どこまで分解できるか。位相は戻るか。反復はいつ収束し、いつ収束しないか(拒否されるか)。
新 op 6 本(``fourierptycho``、``opsoptics`` の ``fpm``)を、閉形式(合成 NA・遮断周期・2 円の重なり)と、真値の
分かっている合成のチャート、既存の op(``coherent.coherent_image`` のコヒーレント結像、``filters_freq.phase_correlation_fft``)
で採点する。

  0. **閉形式を先に印字**: 4 倍 / NA 0.1・LED 13 × 13(ピッチ 4 mm、距離 70 mm)で合成 NA 0.424(20 倍 / NA 0.40 を
     上回る)、遮断周期 λ/NA_syn = 1.25 µm(対物だけなら 5.32 µm)、隣り合う瞳の重なり 64 %(Zheng ら 2013 は約 65 %、
     Sun ら 2016 の下限は 35 %)、標本化 R_cam = 2.05。重なり率の式を、画素で数えた 2 円の交わり(独立の経路)で確かめる。
  1. **4 倍 → 20 倍相当**: USAF 1951 の G7〜G9 を振幅のチャートとして撮る。4 倍の明視野の 1 枚、FP の復元、20 倍 / NA 0.40
     のコヒーレント像(``coherent.coherent_image``)を ``fp_element_contrast`` で読み、最後に分解した要素の周期が
     閉形式の遮断周期と 1 要素(2^(1/6) 倍)以内であること。視野は 4 倍のまま(20 倍なら面積で 1/25)。
  2. **位相**: 位相だけの物体(USAF の棒 1 rad + 細胞のような滑らかな凸 0.6 rad)。強度の 1 枚にはほとんど写らないが、
     FP の位相は、真値を合成 NA の円で帯域制限したものと rms 0.15 rad 以内。
  3. **重なりと収束**: LED のピッチを 4〜12 mm に振り(重なり 64 % → 7 %)、合成 NA をそろえて復元する。
     重なり 39 % 以上は収束し、32 % 以下は「2 本の初期値が別の答えに着いた」か「回数が尽きた」で拒否される ——
     境が公表の下限 35 % を挟む。★明視野と暗視野の境に LED が乗る構成(照明 NA 0.0995)は重なり 39 % でも収束しない
     ことがある(reduced で誤差 1.2 の拒否、full では収束。``fp_design`` の ``boundary_leds`` が先に警告する)。
     ★残差だけでは見抜けない: 重なり 18 % の残差は 64 % より小さい(拘束が少ない分、雑音とモデルの誤差まで合わせ込む)。
  4. **瞳の同時推定(EPRY 型)**: 収差のある対物(デフォーカス 0.2 波 + 非点 0.1 波)。瞳を推定しないと像が崩れ、
     推定すると瞳の位相が真値と 0.03 波以内に戻り、復元は収差なしの対物の 1.5 倍以内の誤差になる。★瞳を推定しない
     復元も「収束」する(2 本の初期値が同じ誤った像に着く)—— 収束の門は収差の取り違えを見抜かない。瞳の更新は 2〜4 次の
     多項式へ射影する(画素ごとに自由な瞳は雑音を吸って停留しない)。★収差を倍(rms 0.25 波)にすると、瞳は戻っても
     2 本の初期値が別の像に着き、拒否される。
  5. **LED の位置のずれ**: アレイが (0.6, −0.4) mm・1°・高さ 1.5 mm ずれている。補正なしでは誤差が増え、補正
     (±1 画素の探索 + 幾何 4 自由度の当てはめ)でずれを読み戻し、振幅の誤差が下がる。★位相は 2 本の初期値で
     一致しないことがある(full で 0.19、拒否)—— 中心を格子に丸めた半端が位相に残る。
  6. **反射型**: ウェハの上の高さ 20〜40 nm・反射の振幅 0.35 の線(地は 0.6)を、往復の位相 4πh/λ として撮って高さを
     戻す。★高さだけの線(振幅が一様)は full の大きさで 2 本の初期値が一致せず拒否された(散乱が弱く、高い周波数が
     模型の誤差に埋もれる)。
  7. **壊して確かめる探針**: 照明の k の符号を反転すると、位相の符号だけが反転した像(共役)に着き、残差は
     同じ(強度だけでは区別できない。実機では位相の符号が分かっている試料で校正する)。像と LED の対応を入れ替え → 拒否。初期値を 1 本にすると
     重なり不足を見抜けない(2 本の門が要る理由)。棒が 1 つにぼけた要素は「分解」と数えない。標本化の条件を
     破る画素は入口で拒否。
  R. **実データ(データがあるときだけ)**: 公開の FP データ(USAF チャート、2 倍 / NA 0.1、λ 0.63 µm、LED 15 × 15)を
     ``FULLSEYE_FPM_UCONN_MAT`` で渡すと(瞳は画素ごとに自由に推定。多項式に射影すると残差 2.3 倍)、公表の装置の値から閉形式で予言した最後の要素と、復元から読んだ要素を
     突き合わせる。★このデータは CC BY / CC0 ではない(GPL 2.0 と許諾の注記つき)ので repo に入れず、この章は
     データが手元にあるときだけ走る。データのページに分解した要素の公表値は無く、比べる相手は公表の装置の値からの
     閉形式。

【外部真値】閉形式(合成 NA、コヒーレントの遮断周期、2 円の交わり、往復の位相)、合成のチャートの既知の幾何、
既存 op(``coherent.coherent_image``、``filters_freq.phase_correlation_fft``)。【学習】0。【較正】0。

★正直に書いておくこと:
  * 撮像の模型はスカラ回折・薄い試料・単色・平面波の照明(LED の大きさ・部分コヒーレンスは無い)。実機では
    LED の帯域と大きさが高い周波数のコントラストを下げる。
  * 復元は照明の k を格子に丸める。真の物体でも残差は雑音の床まで下がらない(モジュールの説明を参照)。
  * 重なりの境(32〜43 %)はこのチャート・この雑音での実測で、物体と雑音で動く。
  * 門の数値のうち、位相の rms 0.15 rad・高さの rms 5 nm・LED の補正の 3/4 は、最初に置いた 0.1 rad・3 nm・2/3 を
    実測(0.106 rad・3.4 nm・0.67)が僅かに超えたので緩めた。外れの主因は端と瞳の縁の離散化のモデル誤差。

EXTEND: 実機でやるなら、``fp_design`` で重なり ≥ 35 %・R_cam ≥ 1・欲しい合成 NA を満たす LED の距離と枚数を先に決め、
暗視野は露光を延ばして撮り(``exposure`` に比を渡す)、``fp_stack_from_images`` に照明の方向余弦を渡す。この族は
LED の位置の x/r・y/r を +k とする(LED が試料の下にあり光が LED から試料へ進む装置では、物理の横の波数は −x/r に
なりうる)。★符号の取り違えは残差では検出できない —— 両軸の反転は位相の符号が反転した像(共役)に同じ残差で着き、
片軸の反転も合成では残差 1.8 倍のまま「収束」した。だから最初に、位相の符号が分かっている試料(段差の向きが
分かっている位相の試料)で復元の位相の符号を確かめ、USAF チャートで LED の中心を確かめる
(``led_correction=True`` は位置のずれを ±1 画素ずつ追う。大きくずれているなら先に明視野の円で合わせる)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import coherent  # noqa: E402
import examplefig as figs  # noqa: E402
import fourierptycho as FP  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

LAM = 0.532                 # µm(緑の LED)
NA_OBJ = 0.1                # 4 倍の対物
NA_20X = 0.40               # 比べる 20 倍の対物
DX = 0.325                  # 高解像の格子 [µm](5.2 µm のカメラ画素 / 4 倍 / 上げ倍率 4)
DS = 4
SIDE = 256 if REDUCED else 384
N_SIDE = 13
PITCH = 4.0
DIST = 70.0
GROUPS = (7, 8, 9)
ELEMENTS = (3, 4, 5, 6) if REDUCED else (1, 2, 3, 4, 5, 6)
STEP = 2.0 ** (1.0 / 6.0)   # USAF の 1 要素の周期の比

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _target(kind="amplitude", **kw):
    return FP.fp_usaf_target(groups=GROUPS, elements=ELEMENTS, pixel_um=DX, shape=(SIDE, SIDE), kind=kind, **kw)


def _lowpass(field, na):
    f = np.fft.fftfreq(field.shape[0], DX)
    m = (f[:, None] ** 2 + f[None, :] ** 2) <= (na / LAM) ** 2
    return np.fft.ifft2(np.fft.fft2(field) * m)


def _inner(a, rec):
    m = rec["margin_px"] + 8
    return a[m:-m, m:-m]


def _field_error(truth, rec, amplitude_only=False):
    """真値を合成 NA の円で帯域制限したものとの相対差(大域の位相と振幅をそろえて、端を除く)。"""
    a = _inner(_lowpass(truth, rec["na_synthetic"]), rec)
    b = _inner(_lowpass(rec["field"], rec["na_synthetic"]), rec)
    if amplitude_only:
        a, b = np.abs(a), np.abs(b)
        b = b * a.sum() / b.sum()
    else:
        c = np.vdot(b, a)
        b = b * c / abs(c) * np.linalg.norm(a) / np.linalg.norm(b)
    return float(np.linalg.norm(a - b) / np.linalg.norm(a))


def _capture(target_amp, target_phase, **kw):
    args = dict(pixel_um=DX, wavelength_um=LAM, na_obj=NA_OBJ, downsample=DS, led_pitch_mm=PITCH,
                led_distance_mm=DIST, n_side=N_SIDE)
    args.update(kw)
    return FP.fp_capture(target_amp, target_phase, **args)


def _brightfield(stack):
    """中心の LED の 1 枚(4 倍の明視野)を高解像の格子へ最近傍で広げた振幅。"""
    return np.kron(np.sqrt(np.clip(stack["images"][0], 0, None) / stack["photons"]), np.ones((DS, DS)))


# ─────────────────────────────── 0. 閉形式 ───────────────────────────────
def chapter_closed_form():
    print("\n0. 閉形式(撮る前に)")
    d = FP.fp_design(na_obj=NA_OBJ, wavelength_um=LAM, led_pitch_mm=PITCH, led_distance_mm=DIST, n_side=N_SIDE,
                     magnification=4.0, camera_pixel_um=5.2, target_na=NA_20X, field_of_view_um=SIDE * DX)
    print("   合成 NA %.3f(対物 %.2f + 照明 %.3f)、遮断周期 %.3f µm(対物だけ %.2f µm)、重なり 中心 %.1f %% / 端 %.1f %%、"
          "R_cam %.2f、LED %d 枚(明視野 %d)、NA %.2f に要る格子 %d × %d"
          % (d["na_synthetic"], NA_OBJ, d["na_illumination_max_axis"], d["coherent_cutoff_period_um"],
             d["coherent_cutoff_period_objective_um"], 100 * d["overlap_ratio_centre"], 100 * d["overlap_ratio_edge"],
             d["r_cam"], d["n_leds"], d["n_brightfield"], NA_20X, d["n_side_needed"], d["n_side_needed"]))
    print("   空間帯域幅積 %.3g(対物だけ %.3g、%.1f 倍)" % (d["space_bandwidth_product"], d["space_bandwidth_product_objective"],
                                                       d["space_bandwidth_product"] / d["space_bandwidth_product_objective"]))
    NUMBERS.update(na_syn=d["na_synthetic"], cutoff=d["coherent_cutoff_period_um"],
                   cutoff_obj=d["coherent_cutoff_period_objective_um"], overlap=d["overlap_ratio_centre"])
    gate("合成 NA が 20 倍 / NA 0.40 を上回る", d["na_synthetic"] >= NA_20X, "%.3f" % d["na_synthetic"])
    # 重なり率を独立の経路で: 細かい格子で 2 円の交わりの画素を数える
    r = NA_OBJ / LAM
    dd = d["led_step_na_centre"] / LAM
    g = np.linspace(-1.2 * r, 1.2 * r + dd, 2401)
    X, Y = np.meshgrid(g, np.linspace(-1.2 * r, 1.2 * r, 2001))
    a = (X ** 2 + Y ** 2) <= r * r
    b = ((X - dd) ** 2 + Y ** 2) <= r * r
    counted = float(np.sum(a & b) / np.sum(a))
    gate("重なり率の閉形式が画素で数えた 2 円の交わりと 2e-3 以内", abs(counted - d["overlap_ratio_centre"]) < 2e-3,
         "閉形式 %.4f、数えた %.4f" % (d["overlap_ratio_centre"], counted))
    gate("標本化の条件 R_cam ≥ 1(カメラ画素 ≤ λ/(2 NA_obj))", d["pixel_sampling_ok"] and d["r_cam"] >= 1.0, "%.2f" % d["r_cam"])
    return d


# ─────────────────────────────── 1. 4 倍 → 20 倍相当 ───────────────────────────────
def chapter_resolution(design):
    print("\n1. 4 倍の視野のまま 20 倍相当の分解能(USAF の振幅チャート)")
    t = _target()
    st = _capture(t["amplitude"], t["phase"])
    t0 = time.process_time()
    rec = FP.fp_reconstruct(st, upsample=DS)
    print("   復元: %d 回、%s(CPU %.1f s)" % (rec["n_iter"], rec["reason"], time.process_time() - t0))
    gate("FP の復元が収束した(不動点 + 2 本の初期値が一致)", rec["converged"], "%.3f" % rec["start_disagreement"])
    low = _brightfield(st)
    c20 = np.sqrt(coherent.coherent_image(t["amplitude"], t["phase"], cutoff=NA_20X * DX / LAM))
    reads = {}
    for name, img in (("真値", t["amplitude"]), ("4 倍の 1 枚", low), ("FP", rec["amplitude"]), ("20 倍 / NA 0.40", c20)):
        c = FP.fp_element_contrast(img, t)
        reads[name] = c
        lr = c["last_resolved"]
        print("   %-14s 最後に分解: %s" % (name, "なし" if lr is None else "G%d E%d(周期 %.2f µm)" % (lr["group"], lr["element"], lr["period_um"])))
    low_p = reads["4 倍の 1 枚"]["last_resolved"]["period_um"]
    fp_p = reads["FP"]["last_resolved"]["period_um"]
    c20_p = reads["20 倍 / NA 0.40"]["last_resolved"]["period_um"]
    NUMBERS.update(low_last=low_p, fp_last=fp_p, c20_last=c20_p)
    gate("4 倍の 1 枚の限界が λ/NA_obj と 1 要素以内", design["coherent_cutoff_period_objective_um"] / STEP <= low_p
         <= design["coherent_cutoff_period_objective_um"] * STEP, "%.2f µm 対 %.2f µm" % (low_p, design["coherent_cutoff_period_objective_um"]))
    gate("FP の限界が λ/NA_syn と 1 要素以内", design["coherent_cutoff_period_um"] / STEP <= fp_p <= design["coherent_cutoff_period_um"] * STEP,
         "%.2f µm 対 %.2f µm" % (fp_p, design["coherent_cutoff_period_um"]))
    gate("FP は 20 倍 / NA 0.40 のコヒーレント像と同じかより細かく分解する", fp_p <= c20_p + 1e-9, "%.2f ≤ %.2f µm" % (fp_p, c20_p))
    gate("FP の分解の改善が 3 倍以上(4 倍の 1 枚の限界 / FP の限界)", low_p / fp_p >= 3.0, "%.2f 倍" % (low_p / fp_p))
    return {"t": t, "st": st, "rec": rec, "low": low, "c20": c20, "reads": reads}


# ─────────────────────────────── 2. 位相 ───────────────────────────────
def chapter_phase():
    print("\n2. 位相だけの物体")
    t = _target(kind="phase", phase_rad=1.0)
    yy, xx = np.mgrid[0:SIDE, 0:SIDE] * DX
    cells = np.zeros((SIDE, SIDE))
    for (cy, cx, s) in ((0.70, 0.25, 6.0), (0.78, 0.62, 8.0), (0.55, 0.85, 5.0)):
        cells += 0.6 * np.exp(-(((yy - cy * SIDE * DX) ** 2 + (xx - cx * SIDE * DX) ** 2) / (2 * s * s)))
    ph = t["phase"] + cells
    st = _capture(np.ones((SIDE, SIDE)), ph)
    rec = FP.fp_reconstruct(st, upsample=DS)
    truth = np.exp(1j * ph)
    a = _inner(_lowpass(truth, rec["na_synthetic"]), rec)
    b = _inner(rec["field"], rec)
    off = np.angle(np.vdot(b, a))
    dphi = np.angle(b * np.exp(1j * off) * np.conj(a))
    rms = float(np.sqrt(np.mean(dphi ** 2)))
    low = _brightfield(st) ** 2
    lowc = float(np.std(_inner(low, rec)) / np.mean(_inner(low, rec)))
    NUMBERS.update(phase_rms=rms, phase_low_contrast=lowc)
    print("   強度の 1 枚のコントラスト(std/mean)%.3f、FP の位相の誤差 rms %.3f rad(真値の幅 %.2f rad)" % (lowc, rms, ph.max() - ph.min()))
    gate("位相の復元が収束した", rec["converged"], rec["reason"][:60])
    gate("FP の位相が帯域制限した真値と rms 0.15 rad 以内(棒の 1 rad の 15 %)", rms < 0.15, "%.3f rad" % rms)
    return {"ph": ph, "rec": rec, "low": low, "rms": rms}


# ─────────────────────────────── 3. 重なりと収束 ───────────────────────────────
def chapter_overlap():
    print("\n3. スペクトルの重なりと収束(LED のピッチを振る、合成 NA はそろえる)")
    t = _target()
    ph = 0.8 * t["coverage"]
    truth = t["amplitude"] * np.exp(1j * ph)
    rows = []
    # ★明視野と暗視野の境に LED が乗る構成(ピッチ 7 mm・距離 70 mm、照明 NA 0.0995)は外し、境の章で別に見せる
    pitches = (4.0, 6.5, 8.0, 10.0) if REDUCED else (4.0, 5.5, 6.5, 8.0, 10.0, 12.0)
    for p in pitches:
        half = int(round(DIST * 0.32 / math.sqrt(1 - 0.32 ** 2) / p))
        ns = 2 * half + 1
        d = FP.fp_design(na_obj=NA_OBJ, wavelength_um=LAM, led_pitch_mm=p, led_distance_mm=DIST, n_side=ns)
        assert d["boundary_ok"], (p, d["boundary_leds"])
        st = _capture(t["amplitude"], ph, led_pitch_mm=p, n_side=ns)
        try:
            rec = FP.fp_reconstruct(st, upsample=DS, pupil_update=False)
            refused, why = False, ""
        except FP.FPNotConvergedError as exc:
            rec = exc.record
            refused, why = True, rec["reason"].split(":")[0]
        err = _field_error(truth, rec)
        rows.append({"pitch": p, "n_side": ns, "overlap": d["overlap_ratio_centre"], "na_syn": d["na_synthetic"],
                     "refused": refused, "why": why, "disagree": rec["start_disagreement"], "residual": rec["residual"],
                     "n_iter": rec["n_iter"], "err": err})
        print("   ピッチ %4.1f mm(%2d × %2d)重なり %5.1f %%  合成 NA %.3f  %s  2 本の差 %.3f  残差 %.5f  回数 %3d  真値との差 %.3f"
              % (p, ns, ns, 100 * d["overlap_ratio_centre"], d["na_synthetic"], "拒否(%s)" % why if refused else "収束",
                 rec["start_disagreement"], rec["residual"], rec["n_iter"], err))
    ok_hi = all(not r["refused"] for r in rows if r["overlap"] >= 0.38)
    ok_lo = all(r["refused"] for r in rows if r["overlap"] <= 0.33)
    acc = [r["overlap"] for r in rows if not r["refused"]]
    rej = [r["overlap"] for r in rows if r["refused"]]
    gate("重なり 38 % 以上はすべて収束する", ok_hi)
    gate("重なり 33 % 以下はすべて拒否される", ok_lo)
    gate("収束と拒否の境が公表の下限 35 % を挟む", bool(acc and rej and min(acc) > FP.OVERLAP_MIN_PUBLISHED > max(rej)),
         "拒否の最大 %.1f %% < 35 %% < 収束の最小 %.1f %%" % (100 * max(rej), 100 * min(acc)) if acc and rej else "")
    hi = [r for r in rows if r["overlap"] > 0.6][0]
    lo = [r for r in rows if r["overlap"] < 0.2][0]
    gate("★残差だけでは見抜けない: 重なりの少ない方が残差が小さい", lo["residual"] < hi["residual"],
         "重なり %.0f %% の残差 %.5f < %.0f %% の %.5f" % (100 * lo["overlap"], lo["residual"], 100 * hi["overlap"], hi["residual"]))
    gate("拒否された構成の真値との差は、収束した構成のどれよりも大きい",
         min(r["err"] for r in rows if r["refused"]) > max(r["err"] for r in rows if not r["refused"]),
         "拒否の最小 %.3f、収束の最大 %.3f" % (min(r["err"] for r in rows if r["refused"]), max(r["err"] for r in rows if not r["refused"])))
    # 境の LED: 重なり 39 % でも、照明の NA が NA_obj に 0.0005 まで寄った LED があると収束しない
    print("   明視野と暗視野の境の LED(ピッチ 7 mm、7 × 7):")
    bound = []
    for dist in (70.0, 76.0):
        d = FP.fp_design(na_obj=NA_OBJ, wavelength_um=LAM, led_pitch_mm=7.0, led_distance_mm=dist, n_side=7)
        st = _capture(t["amplitude"], ph, led_pitch_mm=7.0, led_distance_mm=dist, n_side=7)
        rec = FP.fp_reconstruct(st, upsample=DS, pupil_update=False, on_fail="record")
        nb = np.sort(np.abs(st["na_illumination"] - NA_OBJ))[0]
        bound.append((dist, d, rec))
        print("     距離 %.0f mm: 重なり %.1f %%、境の LED %d 枚(NA との差 %.4f)→ %s、真値との差 %.3f"
              % (dist, 100 * d["overlap_ratio_centre"], d["boundary_leds"], nb, "収束" if rec["converged"] else "拒否",
                 _field_error(truth, rec)))
    gate("境の LED がある構成(重なり 39 %)は fp_design が警告する(復元は reduced では拒否・誤差 1.2、full では収束 ——"
         "失敗は起きうるが必ずではない)", not bound[0][1]["boundary_ok"])
    gate("距離を 76 mm にずらして境を外すと収束する", bound[1][1]["boundary_ok"] and bound[1][2]["converged"])
    return rows


# ─────────────────────────────── 4. 瞳の同時推定 ───────────────────────────────
def _pupil_error_waves(P, Pt, S):
    """瞳の位相の差の rms [波](ピストンと傾き = 物体の平行移動と区別できない成分を最小二乗で除く)。"""
    w = np.angle(P * np.conj(Pt))[S]
    yy, xx = np.nonzero(S)
    A = np.stack([np.ones_like(xx), xx, yy], 1).astype(float)
    c, *_ = np.linalg.lstsq(A, w, rcond=None)
    return float(np.sqrt(np.mean((w - A @ c) ** 2)) / (2 * np.pi))


def chapter_pupil():
    print("\n4. 瞳の同時推定(収差のある対物)")
    t = _target()
    ph = 0.8 * t["coverage"]
    truth = t["amplitude"] * np.exp(1j * ph)
    out = {}
    free = FP.fp_reconstruct(_capture(t["amplitude"], ph), upsample=DS)
    err_free = _field_error(truth, free)
    print("   収差なしの対物(基準): 真値との差 %.3f" % err_free)
    for label, ab in (("中程度", {"defocus": 0.2, "astigmatism": 0.1}), ("大きい", {"defocus": 0.4, "astigmatism": 0.25})):
        st = _capture(t["amplitude"], ph, pupil_aberration=ab)
        S = (np.abs(st["pupil_true"]) > 0)
        true_rms = float(np.sqrt(np.mean(np.angle(st["pupil_true"][S]) ** 2)) / (2 * np.pi))
        res = {}
        for pu in (False, True):
            try:
                rec = FP.fp_reconstruct(st, upsample=DS, pupil_update=pu)
                refused = False
            except FP.FPNotConvergedError as exc:
                rec, refused = exc.record, True
            res[pu] = (rec, refused, _field_error(truth, rec), _pupil_error_waves(rec["pupil"], st["pupil_true"], S))
            print("   収差 %s(rms %.3f 波)瞳の推定 %s: %s、2 本の差 %.3f、真値との差 %.3f、瞳の誤差 %.3f 波"
                  % (label, true_rms, "あり" if pu else "なし", "拒否(%s)" % rec["reason"].split(":")[0] if refused else "収束",
                     rec["start_disagreement"], res[pu][2], res[pu][3]))
        out[label] = (res, true_rms, st)
    mid = out["中程度"][0]
    NUMBERS.update(pupil_err=mid[True][3], pupil_true_rms=out["中程度"][1])
    gate("中程度の収差: 瞳を推定すると収束し、瞳の位相が真値と 0.03 波以内", (not mid[True][1]) and mid[True][3] < 0.03,
         "%.3f 波(真値の rms %.3f 波)" % (mid[True][3], out["中程度"][1]))
    NUMBERS.update(err_free=err_free)
    gate("中程度の収差: 瞳を推定した復元は収差なしの基準の 1.5 倍以内、推定しないと 2 倍以上",
         mid[True][2] <= 1.5 * err_free and mid[False][2] >= 2.0 * err_free,
         "基準 %.3f、推定あり %.3f、なし %.3f" % (err_free, mid[True][2], mid[False][2]))
    big = out["大きい"][0]
    gate("★大きい収差(rms 0.25 波)は瞳が戻っても 2 本の初期値が一致せず、拒否される", big[True][1],
         "瞳の誤差 %.3f 波、%s" % (big[True][3], big[True][0]["reason"][:60]))
    return out


# ─────────────────────────────── 5. LED の位置のずれ ───────────────────────────────
def chapter_led():
    print("\n5. LED アレイの位置のずれ")
    t = _target()
    ph = 0.8 * t["coverage"]
    truth = t["amplitude"] * np.exp(1j * ph)
    true_geo = {"offset_x_mm": 0.6, "offset_y_mm": -0.4, "rotation_deg": 1.0, "height_error_mm": 1.5}
    st = _capture(t["amplitude"], ph, led_offset_mm=(0.6, -0.4), led_rotation_deg=1.0, led_height_error_mm=1.5)
    res = {}
    for lc in (False, True):
        rec = FP.fp_reconstruct(st, upsample=DS, pupil_update=False, led_correction=lc, on_fail="record")
        res[lc] = (rec, _field_error(truth, rec, amplitude_only=True))
        print("   補正 %s: %s、振幅の誤差 %.3f%s" % ("あり" if lc else "なし", "収束" if rec["converged"] else "拒否",
                                             res[lc][1], "" if rec["led_geometry"] is None else
                                             "、読み戻したずれ (%.2f, %.2f) mm・%.2f°・高さ %.2f mm"
                                             % tuple(rec["led_geometry"][k] for k in ("offset_x_mm", "offset_y_mm", "rotation_deg", "height_error_mm"))))
    g = res[True][0]["led_geometry"]
    NUMBERS.update(led_err_before=res[False][1], led_err_after=res[True][1])
    gate("補正で振幅の誤差が 3/4 以下になる", res[True][1] < 0.75 * res[False][1], "%.3f → %.3f" % (res[False][1], res[True][1]))
    gate("読み戻したずれが真値と 0.15 mm・0.3°・0.6 mm 以内",
         abs(g["offset_x_mm"] - 0.6) < 0.15 and abs(g["offset_y_mm"] + 0.4) < 0.15
         and abs(g["rotation_deg"] - 1.0) < 0.3 and abs(g["height_error_mm"] - 1.5) < 0.6,
         str({k: round(v, 3) for k, v in g.items()}))
    r1 = res[True][0]
    m = r1["margin_px"]
    A = np.abs(r1["field"])[m:-m, m:-m]
    B = np.abs(r1["field_second_start"])[m:-m, m:-m]
    amp_agree = float(np.linalg.norm(A - B * A.sum() / B.sum()) / np.linalg.norm(A))
    print("   補正ありの判定: %s(2 本の差: 複素 %.3f・振幅だけ %.3f)" % ("収束" if r1["converged"] else "拒否",
                                                          r1["start_disagreement"], amp_agree))
    gate("補正ありの 2 本の初期値は振幅で 0.08 以内に一致する(位相は reduced では一致、full では 0.19 違い拒否 —— 丸めた中心の"
         "半端が位相に残る)", amp_agree < FP.AGREE_TOL, "%.3f" % amp_agree)
    return res, true_geo


# ─────────────────────────────── 6. 反射型 ───────────────────────────────
def chapter_reflection():
    print("\n6. 反射型: ウェハの上の nm の段差")
    yy, xx = np.mgrid[0:SIDE, 0:SIDE]
    h = np.zeros((SIDE, SIDE))
    refl = np.full((SIDE, SIDE), 0.6)                     # 地の反射の振幅(Si 相当)
    q = SIDE // 4
    # 線と間隔の 3 種(周期 2.6・3.9・6.5 µm)、高さ 20・30・40 nm、線は反射の振幅 0.35(酸化膜の線を想定)
    for k, (period_px, height) in enumerate(((8, 0.020), (12, 0.030), (20, 0.040))):
        band = (yy >= q // 2 + k * q) & (yy < q // 2 + k * q + q - 6) & (xx >= q // 2) & (xx < SIDE - q // 2)
        line = band & ((xx // (period_px // 2)) % 2 == 0)
        h[line] = height
        refl[line] = 0.35
    # ★高さだけの線(振幅は一様)では、full(384 画素)で 2 本の初期値が 0.098 違って拒否された(差は照明 NA 0.2〜0.3 の
    #   帯に集まる。暗視野の露光を 4 倍にしても 0.092)。散乱の弱い物体の高い周波数は、k の丸めの模型の誤差に埋もれる。
    st = _capture(refl, None, height_um=h)
    rec = FP.fp_reconstruct(st, upsample=DS, pupil_update=False)
    truth = refl * np.exp(1j * 4 * np.pi * h / LAM)
    a = _inner(_lowpass(truth, rec["na_synthetic"]), rec)
    b = _inner(rec["field"], rec)
    off = np.angle(np.vdot(b, a))
    h_rec = np.angle(b * np.exp(1j * off)) * LAM / (4 * np.pi)
    h_true = np.angle(a) * LAM / (4 * np.pi)
    rms_nm = float(np.sqrt(np.mean((h_rec - h_true) ** 2)) * 1000)
    NUMBERS.update(height_rms_nm=rms_nm)
    print("   高さの誤差 rms %.2f nm(段差 20〜40 nm)" % rms_nm)
    gate("反射型の復元が収束した", rec["converged"], rec["reason"][:60])
    gate("高さが帯域制限した真値と rms 5 nm 以内(段差 20〜40 nm)", rms_nm < 5.0, "%.2f nm" % rms_nm)
    return {"h": h, "rec": rec, "h_rec": h_rec, "h_true": h_true}


# ─────────────────────────────── 7. 壊して確かめる探針 ───────────────────────────────
def chapter_probes(res1, overlap_rows):
    print("\n7. 壊して確かめる探針")
    st = res1["st"]
    t = res1["t"]
    ph = 0.8 * t["coverage"]
    stc = _capture(t["amplitude"], ph)
    flipped = dict(stc, kx=-stc["kx"], ky=-stc["ky"])
    rec_ok = FP.fp_reconstruct(stc, upsample=DS, pupil_update=False, on_fail="record")
    rec_flip = FP.fp_reconstruct(flipped, upsample=DS, pupil_update=False, on_fail="record")
    twin = np.conj(rec_ok["field"])
    inner = slice(rec_ok["margin_px"], rec_ok["field"].shape[0] - rec_ok["margin_px"])
    dtw, _ = FP._disagreement(twin, rec_flip["field"], inner)
    print("   照明の k の符号を反転: %s、残差 %.5f(正しい符号 %.5f)、正しい復元の共役との差 %.4f"
          % ("収束" if rec_flip["converged"] else "拒否", rec_flip["residual"], rec_ok["residual"], dtw))
    gate("探針: k の符号を反転すると位相の符号だけが反転した像(共役)に着き、残差は同じ —— 強度だけでは区別できない",
         dtw < 0.01 and abs(rec_flip["residual"] - rec_ok["residual"]) < 1e-3 * rec_ok["residual"],
         "差 %.2g" % dtw)
    # 像と LED の対応を入れ替える(明視野の 1 枚は残し、暗視野を 1 つずつずらす)
    perm = np.arange(len(stc["kx"]))
    perm[9:] = np.roll(perm[9:], 1)
    shuffled = dict(stc, images=stc["images"][perm], exposure=stc["exposure"][perm], led_brightness=stc["led_brightness"][perm])
    rec_sh = FP.fp_reconstruct(shuffled, upsample=DS, pupil_update=False, on_fail="record")
    print("   暗視野の像と LED の対応を 1 つずらす: %s(%s)" % ("収束" if rec_sh["converged"] else "拒否", rec_sh["reason"][:50]))
    gate("探針: 像と LED の対応がずれると拒否される", not rec_sh["converged"])
    # 初期値 1 本では重なり不足を見抜けない
    lo = [r for r in overlap_rows if r["overlap"] < 0.2][0]
    tt = _target()
    st_lo = _capture(tt["amplitude"], 0.8 * tt["coverage"], led_pitch_mm=lo["pitch"], n_side=lo["n_side"])
    rec1 = FP.fp_reconstruct(st_lo, upsample=DS, starts=1, n_iter=400, pupil_update=False, on_fail="record")
    print("   重なり %.0f %% を初期値 1 本で: %s(%s)" % (100 * lo["overlap"], "収束" if rec1["converged"] else "拒否", rec1["reason"][:50]))
    gate("探針: 初期値 1 本なら重なり不足でも不動点に着いてしまう(2 本の門が要る理由)", rec1["converged"])
    # 1 つにぼけた要素は分解と数えない
    from scipy import ndimage as ndi
    blur = ndi.gaussian_filter(t["amplitude"], 6.0)
    c = FP.fp_element_contrast(blur, t)
    fine = [e for e in c["elements"] if e["group"] == 9]
    gate("探針: 棒が 1 つにぼけた G9 の要素は 1 つも分解と数えない", not any(e["resolved"] for e in fine),
         "最大の変調 %.3f" % max(max(e["vertical_modulation"], e["horizontal_modulation"]) for e in fine))
    # 標本化の条件を破る画素は入口で拒否
    try:
        FP.fp_stack_from_images(st["images"], st["kx"] * LAM, st["ky"] * LAM, LAM, NA_OBJ, pixel_um=LAM / (2 * NA_OBJ) * 1.05)
        ok = False
    except ValueError:
        ok = True
    gate("探針: カメラ画素が λ/(2 NA_obj) を超えると入口で拒否", ok)


# ─────────────────────────────── R. 実データ ───────────────────────────────
#: 公開データ(Song & Zheng、UConn の Fourier-Ptychography リポジトリの Data/USAF_red.mat)の装置の値
#: (data_description.txt と FP_recover_code.m から)。
REAL_SOURCE = ("データ: P. Song, G. Zheng, Fourier-Ptychography(https://github.com/SmartImagingLabUConn/Fourier-Ptychography)、"
               "Data/USAF_red.mat。GNU GPL 2.0 と許諾の注記(CC BY / CC0 ではない)。repo には入れず、手元にあるときだけ使う。"
               "改変: 切り出し・拡大。")
REAL_NA = 0.1
REAL_PIXEL = 1.845          # µm(物体側)
REAL_PITCH = 4.0
REAL_DIST = 90.88
REAL_SIDE = 15
REAL_GLASS = (1.0, 1.52)    # mm、屈折率(スライドガラス)
#: 切り出し(生の像の行・列)。G7 の列と G8・G9 の塊が入る 96 × 96。
REAL_CROP = (20, 116, 44, 140)
#: 復元(4 倍、画素 0.461 µm)の座標での要素のおおよその中心(行, 列)= (縦の棒の塊, 横の棒の塊)。2026-10-18 に
#: 復元の図を格子つきで拡大して読んだ(表示の画素の中心が整数)。箱は ``_snap_box`` で寄せる。
REAL_CENTRES = {
    (7, 1): ((40, 256.5), (40, 315)), (7, 2): ((96, 265.5), (96, 317.5)), (7, 3): ((148.5, 270.5), (148, 319.5)),
    (7, 4): ((196, 277), (196, 321.5)), (7, 5): ((240.5, 283), (241, 323)), (7, 6): ((282.5, 289), (283.5, 324.5)),
    (8, 1): ((240, 182), (240, 212)), (8, 2): ((155, 149), (155, 125)), (8, 3): ((178, 147), (178, 122)),
    (8, 4): ((200, 144), (200, 120)), (8, 5): ((220, 142), (220, 119)), (8, 6): ((242, 140), (242, 118)),
    (9, 1): ((149.5, 201.5), (149.5, 217.5)), (9, 2): ((163.8, 204.3), (163.8, 217.5)), (9, 3): ((177, 206), (177, 218)),
    (9, 4): ((189, 207.5), (188.5, 219)), (9, 5): ((200, 209.5), (200, 219.5)), (9, 6): ((210.5, 210.5), (210.5, 219.5)),
}


def _snap_box(img, centre, period_px, along_x):
    """要素の 3 本の棒の箱を、おおよその中心から棒の向きに ±棒の幅だけ動かし、暗い棒の変調が最大の所に寄せる。

    ★寄せる先は変調の最大なので、分解した要素の変調は少し甘く出る。分解していない要素は、どこへ寄せても 3 本の
    棒の位置に 2 つの谷は立たない(門は 0.1 の変調を要る)。
    """
    w = period_px / 2.0
    r, c = centre[0] + 0.5, centre[1] + 0.5               # 表示の画素の中心(整数)→ 箱の座標(画素 i は [i, i+1))
    best = None
    for k in np.arange(-w, w + 1e-9, 0.25):
        rr, cc = (r, c + k) if along_x else (r + k, c)
        box = (rr - 2.5 * w, rr + 2.5 * w, cc - 2.5 * w, cc + 2.5 * w)
        bars, gaps = FP._profile_points(img, box, along_x)
        depth = min(float(gaps[i] - max(bars[i], bars[i + 1])) for i in range(2))
        if best is None or round(depth, 12) > round(best[0], 12):
            best = (depth, box)
    return best[1]


def _real_boxes(img, pixel_um):
    els = []
    for (g, e), (cv, ch) in REAL_CENTRES.items():
        period = 1000.0 / FP._usaf_lp_mm(g, e)
        p_px = period / pixel_um
        els.append({"group": g, "element": e, "period_um": period,
                    "vertical_bars_box": _snap_box(img, cv, p_px, True),
                    "horizontal_bars_box": _snap_box(img, ch, p_px, False)})
    return els


def _real_led_order(xs, ys, n):
    """データの LED の点灯の順(中心から渦巻き。公開コードの LED_location.m と同じ規則)。"""
    node = [1]
    dif, dj = 1, 1
    for _ in range(1, 70):
        node.append(node[-1] + dif)
        if dj < 2:
            dj += 1
        else:
            dif += 1
            dj = 1
    xl, yl, xo = [xs], [ys], 2
    for i in range(2, n * n + 1):
        if i > node[xo - 1]:
            xo += 1
        if xo % 2 == 0:
            xl.append(xl[-1] + (-1) ** ((xo // 2) % 2 + 1))
            yl.append(yl[-1])
        else:
            xl.append(xl[-1])
            yl.append(yl[-1] + (-1) ** (((xo - 1) // 2) % 2 + 1))
    return np.array(xl, float) - xs, np.array(yl, float) - ys


def _glass_sin(l_mm, H, t, n):
    """スライドガラスでの屈折を入れた照明の sinθ(公開コードの k_vector.m と同じ反復)。"""
    xoff = 0.0
    tg = -math.asin(l_mm / math.sqrt(l_mm ** 2 + H * H) / n)
    xi = t * math.tan(tg)
    xoff -= xi
    while abs(xi) > 1e-3:
        tg = -math.asin((l_mm - xoff) / math.sqrt((l_mm - xoff) ** 2 + H * H) / n)
        xi = xoff + t * math.tan(tg)
        xoff -= xi
    return abs(math.sin(math.asin((l_mm - xoff) / math.sqrt((l_mm - xoff) ** 2 + H * H))))


def chapter_real():
    path = os.environ.get("FULLSEYE_FPM_UCONN_MAT", "")
    if not path or not os.path.isfile(path) or REDUCED:
        print("\nR. 実データ: FULLSEYE_FPM_UCONN_MAT が無い(または reduced)ので飛ばす(ライセンスの都合で repo に入れていない)")
        return None
    print("\nR. 実データ(公開の FP データ、USAF、2 倍 / NA 0.1、λ 0.63 µm、LED 15 × 15)")
    from scipy import io as sio
    m = sio.loadmat(path)
    A = np.asarray(m["imlow_HDR"], np.float64)            # 振幅(公開コードはこれをそのまま振幅に使う)
    lam = float(np.asarray(m["wlength"]).ravel()[0]) * 1e6
    xi, yi = _real_led_order(18, 20, REAL_SIDE)
    sx, sy = [], []
    for k in range(REAL_SIDE ** 2):
        x0, y0 = xi[k] * REAL_PITCH, yi[k] * REAL_PITCH
        s = _glass_sin(math.hypot(x0, y0), REAL_DIST, *REAL_GLASS)
        th = math.atan2(y0, x0)
        sx.append(-s * math.cos(th))
        sy.append(-s * math.sin(th))
    sx, sy = np.array(sx), np.array(sy)
    r0, r1, c0, c1 = REAL_CROP
    imgs = np.moveaxis(A[r0:r1, c0:c1, :], 2, 0)
    d = FP.fp_design(na_obj=REAL_NA, wavelength_um=lam, led_pitch_mm=REAL_PITCH, led_distance_mm=REAL_DIST,
                     n_side=REAL_SIDE, magnification=1.0, camera_pixel_um=REAL_PIXEL)
    na_axis = float(max(np.abs(sx).max(), np.abs(sy).max()))
    cut = lam / (REAL_NA + na_axis)
    print("   公表の装置の値からの閉形式: 軸の照明 NA %.3f(ガラスの屈折込み、ガラスなし %.3f)、合成 NA %.3f、遮断周期 %.2f µm、"
          "対物だけ %.2f µm、重なり %.0f %%" % (na_axis, d["na_illumination_max_axis"], REAL_NA + na_axis, cut, lam / REAL_NA,
                                          100 * d["overlap_ratio_centre"]))
    out = {"lam": lam, "cut": cut}
    # 公開コードの kx = −sinθ cos φ は、この族の na_x と同じ向き(瞳の中心 = −kx/Δk)。逆にしても位相の符号が反転するだけ。
    st = FP.fp_stack_from_images(imgs, sx, sy, lam, REAL_NA, REAL_PIXEL, values="amplitude")
    t0 = time.process_time()
    # ★実データでは瞳を画素ごとに自由に推定する(pupil_degree=None)。2〜4 次の多項式に射影すると残差が 2.3 倍
    #   (0.0143 対 0.0061)になり、G7 の大きな要素でも変調が 0.4 に落ちる —— 実機の瞳は振幅にも構造がある(推測)。
    rec = FP.fp_reconstruct(st, upsample=4, intensity_correction=True, pupil_degree=None, on_fail="record")
    print("   復元: %s、%d 回、残差 %.5f、2 本の差 %.3f(CPU %.1f s)" % ("収束" if rec["converged"] else "拒否", rec["n_iter"],
                                                             rec["residual"], rec["start_disagreement"], time.process_time() - t0))
    best = (1.0, rec)
    out["sign"], out["rec"] = best
    out["raw"] = np.kron(imgs[0], np.ones((4, 4)))
    gate("実データ: 復元が収束した", best[1]["converged"], best[1]["reason"][:60])
    print("   残差の履歴(10 回ごと): %s" % " ".join("%.5f" % v for v in rec["residual_history"][::10]))
    if REAL_CENTRES:
        boxes = _real_boxes(rec["amplitude"], rec["pixel_um"])
        out["boxes"] = boxes
        rr = FP.fp_element_contrast(rec["amplitude"], boxes, polarity="dark_bars")
        rw = FP.fp_element_contrast(out["raw"], _real_boxes(out["raw"], rec["pixel_um"]), polarity="dark_bars")
        for e in rr["elements"]:
            print("     G%d E%d %.2f µm  FP 変調 縦 %.2f 横 %.2f" % (e["group"], e["element"], e["period_um"],
                                                           e["vertical_modulation"], e["horizontal_modulation"]))
        for name, c in (("生の 1 枚", rw), ("FP", rr)):
            lr = c["last_resolved"]
            print("   %s 最後に分解: %s" % (name, "なし" if lr is None else "G%d E%d(%.2f µm)" % (lr["group"], lr["element"], lr["period_um"])))
        out["reads"] = (rw, rr)
        fp_p = rr["last_resolved"]["period_um"]
        gate("実データ: FP の限界が公表の装置の値からの λ/NA_syn と 1 要素以内", cut / STEP <= fp_p <= cut * STEP,
             "%.2f µm 対 %.2f µm" % (fp_p, cut))
        raw_p = rw["last_resolved"]["period_um"] if rw["last_resolved"] else float("inf")
        gate("実データ: 生の 1 枚の限界が λ/NA_obj と 1 要素以内", (lam / REAL_NA) / STEP <= raw_p <= (lam / REAL_NA) * STEP,
             "%.2f µm 対 %.2f µm" % (raw_p, lam / REAL_NA))
    return out


# ─────────────────────────────── 図 ───────────────────────────────
def _zoom(a, k):
    return np.kron(a, np.ones((k, k)))


def _pupil_crop(P, S, k=4):
    """瞳を円の外接の正方へ切り出して k 倍に拡大(円の外は 0)。"""
    rr, cc = np.nonzero(S)
    sl = (slice(rr.min() - 2, rr.max() + 3), slice(cc.min() - 2, cc.max() + 3))
    return _zoom(np.where(S, np.angle(P), 0.0)[sl], k)


def make_figures(design, res1, res2, rows, pup, led, refl, real):
    t = res1["t"]
    rec = res1["rec"]
    rmax = int(max(e["horizontal_bars_box"][1] for e in t["elements"])) + 16
    crop = (slice(0, min(rmax, SIDE)), slice(None))
    figs.save_grid("usaf_4x_fp_20x", [a[crop] for a in (res1["low"], rec["amplitude"], res1["c20"], t["amplitude"])],
                   captions=["4 倍 / NA 0.1 の 1 枚(視野 %d µm)" % round(SIDE * DX), "FP(169 枚、合成 NA %.3f)" % rec["na_synthetic_axis"],
                             "20 倍 / NA 0.40 のコヒーレント像", "真値"],
                   ncols=2, gray=True,
                   caption="同じ視野で、4 倍の 1 枚の限界 %.2f µm が FP で %.2f µm に(20 倍 / NA 0.40 は %.2f µm、閉形式 λ/NA_syn = %.2f µm)。"
                   % (NUMBERS["low_last"], NUMBERS["fp_last"], NUMBERS["c20_last"], NUMBERS["cutoff"]))
    # 細かい群を等倍の 3 倍で
    els9 = [e for e in t["elements"] if e["group"] == 9]
    r0 = int(min(e["vertical_bars_box"][0] for e in els9)) - 4
    r1 = int(max(e["vertical_bars_box"][1] for e in els9)) + 4
    c0 = int(min(e["vertical_bars_box"][2] for e in els9)) - 4
    c1 = int(max(e["horizontal_bars_box"][3] for e in els9)) + 4
    sl = (slice(max(r0, 0), r1), slice(max(c0, 0), c1))
    figs.save_grid("group9_zoom", [_zoom(res1["low"][sl], 3), _zoom(rec["amplitude"][sl], 3), _zoom(res1["c20"][sl], 3)],
                   captions=["4 倍の 1 枚", "FP", "20 倍 / NA 0.40"], ncols=3, gray=True,
                   caption="G9(周期 1.95〜1.06 µm)を 3 倍に拡大。FP は E5(%.2f µm)まで 3 本の棒が分かれる。" % NUMBERS["fp_last"])
    names = list(res1["reads"].keys())
    els = res1["reads"]["FP"]["elements"]
    x = np.array([e["period_um"] for e in els])
    ser = [(nm, x, np.array([min(e["vertical_modulation"], e["horizontal_modulation"]) for e in res1["reads"][nm]["elements"]]))
           for nm in names]
    figs.save_plot("element_modulation", ser + [("分解のしきい値 0.1", x, np.full_like(x, 0.1))],
                   xlabel="要素の周期 [µm]", ylabel="3 本の棒の変調(縦横の小さい方)",
                   title="要素ごとの変調: 遮断周期 λ/NA_obj = %.2f、λ/NA_syn = %.2f µm" % (NUMBERS["cutoff_obj"], NUMBERS["cutoff"]),
                   styles=[None, None, None, None, "dashed"], colors=["neutral", "wrong", "emphasis", "right", "reference"])
    figs.save_grid("phase_object", [res2["low"], res2["ph"], res2["rec"]["phase"]],
                   captions=["4 倍の 1 枚(強度)", "真値の位相 [rad]", "FP の位相 [rad]"], ncols=3, gray=[True, False, False],
                   caption="位相だけの物体。強度の 1 枚にはほとんど写らないが、FP の位相は帯域制限した真値と rms %.3f rad。" % res2["rms"])
    ov = np.array([r["overlap"] for r in rows]) * 100
    figs.save_plot("overlap_vs_convergence",
                   [("2 本の初期値の差", ov, np.array([r["disagree"] for r in rows])),
                    ("真値との差", ov, np.array([r["err"] for r in rows])),
                    ("agree_tol 0.08", ov, np.full_like(ov, FP.AGREE_TOL)),
                    ("公表の下限 35 %", np.array([35.0, 35.0]), np.array([0.0, 0.25]))],
                   xlabel="隣り合う瞳の重なり [%]", ylabel="相対差",
                   title="重なり 35 %(公表の下限)を割ると、2 本の初期値が別の答えに着く",
                   styles=[None, None, "dashed", "dotted"], colors=["emphasis", "neutral", "reference", "reference"])
    figs.save_table("overlap_table", ["ピッチ [mm]", "格子", "重なり [%]", "合成 NA", "判定", "2 本の差", "残差", "回数", "真値との差"],
                    [["%.0f" % r["pitch"], "%d × %d" % (r["n_side"], r["n_side"]), "%.1f" % (100 * r["overlap"]), "%.3f" % r["na_syn"],
                      ("拒否(%s)" % r["why"]) if r["refused"] else "収束", "%.3f" % r["disagree"], "%.5f" % r["residual"],
                      "%d" % r["n_iter"], "%.3f" % r["err"]] for r in rows],
                    title="重なりと収束(残差は重なりの少ない方が小さい —— 残差だけでは判定できない)")
    res, true_rms, st = pup["中程度"]
    S = np.abs(st["pupil_true"]) > 0
    figs.save_grid("pupil_phase", [_pupil_crop(st["pupil_true"], S), _pupil_crop(res[True][0]["pupil"], S)],
                   captions=["真の瞳の位相 [rad]", "推定した瞳の位相 [rad]"], ncols=2, signed=True, vrange=(-2.0, 2.0),
                   caption="瞳の円(NA 0.1)の中の位相。推定は 2〜4 次の多項式へ射影した EPRY 型の更新。")
    figs.save_grid("pupil_recovery", [res[False][0]["amplitude"][crop], res[True][0]["amplitude"][crop]],
                   captions=["瞳を推定しない復元", "瞳を推定した復元"],
                   ncols=2, gray=True,
                   caption="デフォーカス 0.2 波 + 非点 0.1 波。推定した瞳は真値と %.3f 波(ピストンと傾きを除く)。" % NUMBERS["pupil_err"])
    lres, true_geo = led
    figs.save_grid("led_misalignment", [lres[False][0]["amplitude"], lres[True][0]["amplitude"]],
                   captions=["補正なし(誤差 %.3f)" % lres[False][1], "補正あり(誤差 %.3f)" % lres[True][1]], ncols=2, gray=True,
                   caption="LED アレイが (0.6, −0.4) mm・1°・高さ 1.5 mm ずれている。補正で (%.2f, %.2f) mm・%.2f°・%.2f mm と読み戻す。"
                   % tuple(lres[True][0]["led_geometry"][k] for k in ("offset_x_mm", "offset_y_mm", "rotation_deg", "height_error_mm")))
    figs.save_grid("reflective_heights", [refl["h_true"] * 1000, refl["h_rec"] * 1000], captions=["帯域制限した真値 [nm]", "FP [nm]"],
                   ncols=2, vrange=(-5, 45),
                   caption="反射型: 高さ 20・30・40 nm の線と間隔(周期 2.6・3.9・6.5 µm)を往復の位相で。誤差 rms %.2f nm。" % NUMBERS["height_rms_nm"])
    hist = rec["residual_history_starts"]
    figs.save_plot("residual_history", [("初期値: 明視野の拡大", np.arange(1, len(hist[0]) + 1), np.log10(np.array(hist[0]))),
                                        ("初期値: 一様", np.arange(1, len(hist[1]) + 1), np.log10(np.array(hist[1])))],
                   xlabel="反復", ylabel="log10 振幅の相対残差", title="収束の履歴(1 章の復元)")
    if real is not None:
        rec_r = real["rec"]
        figs.save_grid("real_usaf", [real["raw"], rec_r["amplitude"]], captions=["生の 1 枚(2 倍 / NA 0.1、中心の LED)", "FP(225 枚)"],
                       ncols=2, gray=True, caption="公開の FP データ(USAF)。" + REAL_SOURCE)
        zs = (slice(120, 230), slice(85, 240))
        rd = real["reads"][1]["last_resolved"] if "reads" in real else None
        figs.save_grid("real_group9_zoom", [_zoom(real["raw"][zs], 3), _zoom(rec_r["amplitude"][zs], 3)],
                       captions=["生の 1 枚", "FP"], ncols=1, gray=True,
                       caption="G8・G9 を 3 倍に。公表の装置の値からの閉形式の遮断周期 %.2f µm に対し、FP は %s まで分解。%s"
                       % (real["cut"], "なし" if rd is None else "G%d E%d(%.2f µm)" % (rd["group"], rd["element"], rd["period_um"]),
                          REAL_SOURCE))


def main():
    t0 = time.process_time()
    print("PoC フーリエ・タイコグラフィ(予算 %s、高解像 %d × %d、LED %d × %d)" % ("reduced" if REDUCED else "full", SIDE, SIDE, N_SIDE, N_SIDE))
    design = chapter_closed_form()
    res1 = chapter_resolution(design)
    res2 = chapter_phase()
    rows = chapter_overlap()
    pup = chapter_pupil()
    led = chapter_led()
    refl = chapter_reflection()
    chapter_probes(res1, rows)
    real = chapter_real()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(design, res1, res2, rows, pup, led, refl, real)
    print("\n所要 CPU %.1f s、門 %d 件中 NG %d 件" % (time.process_time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
