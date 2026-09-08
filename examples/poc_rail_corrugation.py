# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""(docstring は実測後に差し替える)"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 軌道と測り方の諸元 ------------------------------------------------------ #
DX = 0.005              # 高分解の標本間隔 [m](5 mm)
LX = 200.0              # 測るレール長 [m]
CHORD_A = 10.0          # 弦 A の長さ [m](10 m 弦正矢法)
CHORD_B = 6.0           # 弦 B の長さ [m]
ASYM_A, ASYM_B = 3.7, 6.3   # 非対称弦の前後の腕 [m](合計 10.0)
CAR_DX = 0.25           # 検測車の標本間隔 [m]
SIGMA = 0.002           # 測定雑音 [mm]
MARGIN = 10.0           # 端から捨てる長さ [m](どの弦でも有効になる内側)
SEED = 11

#: 仕込む凹凸(波長 [m], 振幅 [mm], 位相 [rad], 覚え書き)。**これが真値**。
COMPONENTS = (
    (0.030, 0.050, 0.70, "短波長の波状摩耗"),
    (0.100, 0.080, 1.90, "波状摩耗(中)"),
    (0.315, 0.150, 0.30, "波状摩耗(長)"),
    (1.000, 0.300, 2.40, "★A と B の共通の死角"),
    (1.500, 0.250, 0.95, "B の死角 (6/4)"),
    (2.500, 0.500, 1.10, "A の死角 (10/4)"),
    (3.000, 0.350, 2.00, "B の死角 (6/2)"),
    (5.000, 0.600, 0.50, "A の死角 (10/2)"),
    (10.00, 0.800, 1.40, "A の利得 2 倍 (10/1)"),
    (30.00, 1.200, 0.20, "長波長の通り変位"),
)

X = np.arange(0.0, LX, DX)


# --------------------------------------------------------------------------- #
# 真値 —— レールの縦断形状を式で置く                                            #
# --------------------------------------------------------------------------- #
def profile(scale=None, noise=0.0, seed=SEED):
    """レール縦断形状 y(x) [mm]。``scale`` は成分ごとの倍率(対照群を作る)。"""
    y = np.zeros_like(X)
    for lam, amp, pha, _ in COMPONENTS:
        k = 1.0 if scale is None else float(scale.get(lam, 1.0))
        y += k * amp * np.sin(2.0 * np.pi * X / lam + pha)
    if noise > 0.0:
        y = y + np.random.default_rng(seed).normal(0.0, noise, y.shape)
    return y


# --------------------------------------------------------------------------- #
# 測り方 —— 弦(正矢)                                                          #
# --------------------------------------------------------------------------- #
def chord_versine(y, length, dx=DX):
    """対称弦の正矢 v(x) = y(x) - [y(x-L/2) + y(x+L/2)] / 2。端は NaN。"""
    h = int(round(length / (2.0 * dx)))
    v = np.full(y.shape, np.nan)
    v[h:-h] = y[h:-h] - 0.5 * (y[:-2 * h] + y[2 * h:])
    return v


def chord_asym(y, a=ASYM_A, b=ASYM_B, dx=DX):
    """非対称弦(前 a、後ろ b)の正矢。腕の長さで重みを付けた弦からの距離。"""
    ia, ib = int(round(a / dx)), int(round(b / dx))
    v = np.full(y.shape, np.nan)
    i = np.arange(ia, y.size - ib)
    v[i] = y[i] - (b * y[i - ia] + a * y[i + ib]) / (a + b)
    return v


def h_sym(lam, length):
    """対称弦の伝達関数の大きさ |H(λ)| = |1 - cos(π L / λ)|。**閉形式**。"""
    return np.abs(1.0 - np.cos(np.pi * length / np.asarray(lam, float)))


def h_asym(lam, a=ASYM_A, b=ASYM_B):
    """非対称弦の |H(λ)|。2 本の位相子の重み付き和からの距離。"""
    lam = np.asarray(lam, float)
    z = (b * np.exp(-2j * np.pi * a / lam)
         + a * np.exp(+2j * np.pi * b / lam)) / (a + b)
    return np.abs(1.0 - z)


def amp_at(y, lam, x=X, dx=DX):
    """波長 λ の成分の振幅 [mm](最小二乗で sin/cos に射影。NaN は除く)。"""
    m = np.isfinite(y) & (x >= MARGIN) & (x <= LX - MARGIN)
    xx, yy = x[m], y[m]
    a = np.column_stack([np.cos(2 * np.pi * xx / lam),
                         np.sin(2 * np.pi * xx / lam), np.ones_like(xx)])
    c = np.linalg.lstsq(a, yy, rcond=None)[0]
    return float(np.hypot(c[0], c[1]))


# --------------------------------------------------------------------------- #
# 1. 場面 —— 仕込んだ凹凸と、幾何から先に出す予測                                #
# --------------------------------------------------------------------------- #
def section_scene():
    print("\n[1] 仕込んだ凹凸と、測る前に幾何から出した予測")
    print("    弦の伝達関数は |H(λ)| = |1 - cos(π L / λ)| —— λ = L/(2n) で **厳密に 0**、")
    print("    λ = L/(2n+1) で **2 倍**。10 m 弦の死角 = 5.00 / 2.50 / 1.67 / 1.25 / 1.00 m")
    rows = []
    for lam, amp, _, note in COMPONENTS:
        rows.append([f"{lam:.3f}", f"{amp:.3f}", f"{h_sym(lam, CHORD_A):.4f}",
                     f"{h_sym(lam, CHORD_B):.4f}", f"{h_asym(lam):.4f}", note])
        print("    λ=%7.3f m  A=%.3f mm  |H_A|=%.4f  |H_B|=%.4f  |H_asym|=%.4f  %s"
              % (lam, amp, h_sym(lam, CHORD_A), h_sym(lam, CHORD_B),
                 h_asym(lam), note))
    figs.save_table("planted_components",
                    ["波長 [m]", "振幅 [mm]", "|H| 10m 弦", "|H| 6m 弦",
                     "|H| 非対称", "覚え書き"], rows,
                    title="仕込んだ凹凸と弦の伝達関数(予測)")
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 2. ゼロ点 —— 正矢をそのまま凹凸の高さとして読む                                #
# --------------------------------------------------------------------------- #
def section_zero_point():
    print("\n[2] ゼロ点: 正矢をそのまま凹凸の高さとして読む(10 m 弦)")
    y = profile()
    v = chord_versine(y, CHORD_A)
    out = []
    for lam, amp, _, _ in COMPONENTS:
        meas = amp_at(v, lam)
        pred = amp * h_sym(lam, CHORD_A)
        out.append({"lam": lam, "true": amp, "meas": meas, "pred": pred})
        print("    λ=%7.3f m  真値 %.4f mm → 読み %.4f mm (%+6.1f %%)  予測 %.4f"
              % (lam, amp, meas, 100.0 * (meas - amp) / amp, pred))
    worst_lo = min(out, key=lambda d: d["meas"] / d["true"])
    worst_hi = max(out, key=lambda d: d["meas"] / d["true"])
    print("    → 最小 %.1f %% (λ=%.3f m) / 最大 %.1f %% (λ=%.3f m)"
          % (100 * worst_lo["meas"] / worst_lo["true"], worst_lo["lam"],
             100 * worst_hi["meas"] / worst_hi["true"], worst_hi["lam"]))
    return {"out": out, "lo": worst_lo, "hi": worst_hi}


# --------------------------------------------------------------------------- #
# 3. 予測と実測を突き合わせる                                                   #
# --------------------------------------------------------------------------- #
def section_transfer():
    print("\n[3] 伝達関数: 閉形式の予測 vs 実測(単一成分だけを立てて測る)")
    err = []
    for lam, amp, _, _ in COMPONENTS:
        s = {c[0]: 0.0 for c in COMPONENTS}
        s[lam] = 1.0
        y = profile(scale=s)
        for name, v, pred in (("A", chord_versine(y, CHORD_A), h_sym(lam, CHORD_A)),
                              ("B", chord_versine(y, CHORD_B), h_sym(lam, CHORD_B))):
            meas = amp_at(v, lam) / amp
            err.append(abs(meas - pred))
            if abs(meas - pred) > 0.01 or pred < 0.01:
                print("    λ=%7.3f m 弦%s  予測 |H|=%.5f  実測 %.5f  差 %.5f"
                      % (lam, name, pred, meas, abs(meas - pred)))
    print("    → 予測と実測の差の最大 %.5f(全 %d 通り)" % (max(err), len(err)))
    lam0 = 5.0
    s = {c[0]: 0.0 for c in COMPONENTS}
    s[lam0] = 1.0
    v0 = chord_versine(profile(scale=s), CHORD_A)
    print("    ★ λ=%.2f m の凹凸 0.600 mm を 10 m 弦で測ると、正矢の振幅は "
          "%.5f mm(全域の最大絶対値 %.5f mm)—— **無い**と答える"
          % (lam0, amp_at(v0, lam0), np.nanmax(np.abs(v0))))
    return {"max_err": max(err), "blind_amp": amp_at(v0, lam0),
            "blind_peak": float(np.nanmax(np.abs(v0)))}


# --------------------------------------------------------------------------- #
# 4. ISO 3095 流の 1/3 オクターブ波長帯で見る                                   #
# --------------------------------------------------------------------------- #
def _bands(y, mask):
    """空間周波数 [1/m] の 1/3 オクターブ帯レベル。波長 [m] に直して返す。"""
    r = fs.octave_spectrum(y[mask], 1.0 / DX, fraction=3, f_min=0.05, f_max=20.0)
    lam = 1.0 / np.asarray(r["centers"], float)
    return lam, np.asarray(r["powers"], float), r


def section_bands():
    print("\n[4] 1/3 オクターブ波長帯(ISO 3095 が波状摩耗を並べる形)で見る")
    m = np.isfinite(X) & (X >= MARGIN) & (X <= LX - MARGIN)
    y = profile()
    v = chord_versine(y, CHORD_A)
    mv = np.isfinite(v) & (X >= MARGIN) & (X <= LX - MARGIN)
    lam, pt, rt = _bands(y, m)
    _, pv, _ = _bands(v, mv)
    print("    真値の全帯域の和 %.6f mm^2、正矢の和 %.6f mm^2(Parseval の一致 %.4f)"
          % (rt["total_power"], np.sum(pv), np.sum(pt) / rt["total_power"]))
    ratio = np.sqrt(np.where(pt > 1e-12, pv / np.maximum(pt, 1e-12), np.nan))
    rows = []
    for i in np.argsort(lam)[::-1]:
        if pt[i] < 1e-6:
            continue
        rows.append([f"{lam[i]:.3f}", f"{np.sqrt(2*pt[i]):.4f}",
                     f"{np.sqrt(2*pv[i]):.4f}", f"{ratio[i]:.3f}"])
        print("    帯 λ≈%7.3f m  真値 %.4f mm  正矢 %.4f mm  比 %.3f"
              % (lam[i], np.sqrt(2 * pt[i]), np.sqrt(2 * pv[i]), ratio[i]))
    figs.save_table("octave_bands",
                    ["帯の中心 λ [m]", "真値 [mm]", "10m 弦の正矢 [mm]", "比"],
                    rows, title="1/3 オクターブ波長帯: 真値と 10 m 弦の読み")
    fin = ratio[np.isfinite(ratio)]
    print("    → 帯ごとの比は %.3f 〜 %.3f。**1 つの数字に丸めた「波状摩耗レベル」は、"
          "どの帯が効いたかで %.1f 倍動く**" % (fin.min(), fin.max(), fin.max() / max(fin.min(), 1e-9)))
    return {"lam": lam, "ratio": ratio, "min": float(fin.min()),
            "max": float(fin.max())}


# --------------------------------------------------------------------------- #
# 5. 逆フィルタ —— 割り戻せば直るのか                                           #
# --------------------------------------------------------------------------- #
def section_deconv():
    print("\n[5] 逆フィルタ: 正矢を |H| で割り戻す(雑音 σ=%.3f mm)" % SIGMA)
    y = profile(noise=SIGMA)
    v = chord_versine(y, CHORD_A)
    rows, errs = [], []
    for lam in (10.0, 5.0, 4.5, 4.0, 3.333, 2.500, 1.500, 1.000, 0.315):
        true = next((a for l, a, _, _ in COMPONENTS if abs(l - lam) < 1e-9), 0.0)
        h = float(h_sym(lam, CHORD_A))
        est = amp_at(v, lam) / max(h, 1e-12)
        rows.append([f"{lam:.3f}", f"{h:.5f}", f"{true:.3f}", f"{est:.3f}"])
        errs.append((lam, h, true, est))
        print("    λ=%6.3f m  |H|=%.5f  真値 %.3f mm  逆フィルタ %.3f mm  %s"
              % (lam, h, true, est,
                 "★ 割り戻しが破綻" if h < 0.05 else ""))
    figs.save_table("deconvolution",
                    ["波長 [m]", "|H|", "真値 [mm]", "逆フィルタ [mm]"], rows,
                    title="正矢を |H| で割り戻す —— 死角の近くで壊れる")
    reg = [(lam, 0.0 if h < 0.10 else est) for lam, h, true, est in errs]
    dead = [lam for lam, e in reg if e == 0.0]
    print("    正則化(|H|<0.10 は 0 とみなす)を入れると、%s m は**静かに「凹凸なし」**"
          "になる —— 落ちないので誰も気づかない" % ", ".join("%.3f" % d for d in dead))
    blow = max((e for lam, h, t, e in errs if h < 0.05), default=0.0)
    return {"errs": errs, "dead": dead, "blow": blow}


# --------------------------------------------------------------------------- #
# 6. 弦を 2 本にする —— 互いの死角を埋める、が                                   #
# --------------------------------------------------------------------------- #
def section_dual():
    print("\n[6] 弦を 2 本(10 m と 6 m)にして、|H| の大きい方を採る")
    print("    予測: 共通の死角は λ = L_A/(2n) = L_B/(2m) を満たす所 —— "
          "5/n = 3/m の最小解 n=5, m=3 で **λ = 1.000 m**")
    y = profile(noise=SIGMA)
    va, vb = chord_versine(y, CHORD_A), chord_versine(y, CHORD_B)
    rows, out = [], []
    for lam, amp, _, _ in COMPONENTS:
        ha, hb = float(h_sym(lam, CHORD_A)), float(h_sym(lam, CHORD_B))
        use, h, v = ("A", ha, va) if ha >= hb else ("B", hb, vb)
        est = amp_at(v, lam) / max(h, 1e-12)
        rel = (est - amp) / amp
        out.append({"lam": lam, "true": amp, "est": est, "rel": rel,
                    "h": h, "use": use})
        rows.append([f"{lam:.3f}", use, f"{h:.5f}", f"{amp:.3f}", f"{est:.3f}",
                     f"{100*rel:+.1f}"])
        print("    λ=%7.3f m  採用=弦%s |H|=%.5f  真値 %.3f → %.3f mm (%+6.1f %%)"
              % (lam, use, h, amp, est, 100 * rel))
    figs.save_table("dual_chord",
                    ["波長 [m]", "採用", "|H|", "真値 [mm]", "推定 [mm]", "誤差 %"],
                    rows, title="2 本の弦で互いの死角を埋める")
    ok = [d for d in out if d["h"] > 0.05]
    bad = [d for d in out if d["h"] <= 0.05]
    print("    → %d/%d の波長は誤差 %.1f %% 以内まで戻る。残るのは λ=%s m だけ"
          % (len(ok), len(out), 100 * max(abs(d["rel"]) for d in ok),
             ", ".join("%.3f" % d["lam"] for d in bad)))
    return {"out": out, "ok": ok, "bad": bad}


# --------------------------------------------------------------------------- #
# 7. 検測車の標本間隔 —— 短波長は消えるのではなく、化ける                        #
# --------------------------------------------------------------------------- #
def _alias(lam, dx):
    """標本間隔 dx で折り返した後の見かけの波長 [m](予測の閉形式)。"""
    f, fs_ = 1.0 / lam, 1.0 / dx
    fa = abs(f - round(f / fs_) * fs_)
    return np.inf if fa < 1e-12 else 1.0 / fa


def section_sampling():
    print("\n[7] 検測車の標本間隔 %.2f m(ナイキスト波長 %.2f m)で採り直す"
          % (CAR_DX, 2 * CAR_DX))
    step = int(round(CAR_DX / DX))
    xc, yc = X[::step], profile()[::step]
    rows = []
    for lam, amp, _, _ in COMPONENTS:
        if lam >= 2 * CAR_DX:
            continue
        la = _alias(lam, CAR_DX)
        meas = amp_at(yc, la, x=xc, dx=CAR_DX)
        rows.append([f"{lam:.3f}", f"{amp:.3f}", f"{la:.3f}", f"{meas:.4f}"])
        print("    λ=%.3f m(%.0f mm、振幅 %.3f mm)→ 予測される化けた波長 %.3f m、"
              "そこで実測 %.4f mm" % (lam, 1000 * lam, amp, la, meas))
    figs.save_table("aliasing", ["真の波長 [m]", "振幅 [mm]",
                                 "化けた波長 [m]", "実測 [mm]"], rows,
                    title="0.25 m 標本では短波長が長波長に化ける")
    s = {c[0]: (1.0 if c[0] >= 2 * CAR_DX else 0.0) for c in COMPONENTS}
    yc0 = profile(scale=s)[::step]
    la30 = _alias(0.030, CAR_DX)
    ghost, ctrl = amp_at(yc, la30, x=xc, dx=CAR_DX), amp_at(yc0, la30, x=xc, dx=CAR_DX)
    print("    対照群(短波長を全部止めた同じレール)で λ=%.3f m を測ると %.5f mm。"
          "\n    ★ 幽霊 %.4f mm は対照群の %.0f 倍 —— 0.25 m 標本の記録だけを見て"
          "「%.2f m のうねりがある」と読むと、正体は %.0f mm の波状摩耗"
          % (la30, ctrl, ghost, ghost / max(ctrl, 1e-9), la30, 1000 * 0.030))
    return {"ghost": ghost, "ctrl": ctrl, "alias30": la30}


# --------------------------------------------------------------------------- #
# 8. 非対称弦 —— 死角は消えるのではなく、引っ越す                                #
# --------------------------------------------------------------------------- #
def section_asym():
    print("\n[8] 非対称弦(前 %.1f m / 後ろ %.1f m、合計 %.1f m)"
          % (ASYM_A, ASYM_B, ASYM_A + ASYM_B))
    print("    予測: |H|=0 は 2 本の位相子が同時に 1 になる所 = a/λ も b/λ も整数、")
    print("    つまり **λ = gcd(a, b) / k**。gcd(%.1f, %.1f) = %.2f m なので"
          " 死角の最大波長は %.2f m —— 波状摩耗の帯域そのもの"
          % (ASYM_A, ASYM_B, 0.1, 0.1))
    y = profile()
    v = chord_asym(y)
    rows = []
    for lam, amp, _, _ in COMPONENTS:
        pred = float(h_asym(lam))
        meas = amp_at(v, lam) / amp
        rows.append([f"{lam:.3f}", f"{pred:.5f}", f"{meas:.5f}",
                     f"{h_sym(lam, CHORD_A):.5f}"])
        print("    λ=%7.3f m  予測 |H|=%.5f  実測 %.5f  (対称 10 m 弦なら %.5f)"
              % (lam, pred, meas, h_sym(lam, CHORD_A)))
    figs.save_table("asymmetric_chord",
                    ["波長 [m]", "予測 |H|", "実測 |H|", "対称 10m 弦 |H|"], rows,
                    title="非対称弦: 長波長の死角は消えるが 0.1 m に移る")
    h010 = float(h_asym(0.100))
    hs = [float(h_asym(l)) for l, _, _, _ in COMPONENTS if l >= 1.0]
    print("    → 長波長側の死角(1.0 / 2.5 / 5.0 m)は消えた(|H| の最小 %.4f)が、"
          "\n    ★ λ=0.100 m は |H|=%.6f —— **波状摩耗を測るための弦が、"
          "波状摩耗の帯域に死角を作った**" % (min(hs), h010))
    return {"h010": h010, "hmin_long": min(hs)}


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("レールの波状摩耗を弦で測る —— 伝達関数が 0 になる波長は、"
          "何 mm あっても 0 mm と出る")
    print("レール長 %.0f m / 標本 %.0f mm / 弦 %.0f m と %.0f m / 検測車 %.2f m"
          % (LX, 1000 * DX, CHORD_A, CHORD_B, CAR_DX))
    print("=" * 78)

    sc = section_scene()
    zp = section_zero_point()
    tr = section_transfer()
    bd = section_bands()
    dc = section_deconv()
    du = section_dual()
    sa = section_sampling()
    asy = section_asym()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点(正矢をそのまま高さと読む)は波長で %.1f %% 〜 %.1f %% に化ける。"
          % (100 * zp["lo"]["meas"] / zp["lo"]["true"],
             100 * zp["hi"]["meas"] / zp["hi"]["true"]))
    print("  * 死角は幾何で厳密に予測できる(予測と実測の差は最大 %.5f)。"
          "λ=5.00 m の 0.600 mm は正矢 %.5f mm。" % (tr["max_err"], tr["blind_amp"]))
    print("  * 弦を 2 本にすると %d/%d が戻るが、λ=%.3f m は**両方の死角**なので残る。"
          % (len(du["ok"]), len(du["out"]), du["bad"][0]["lam"]))
    print("  * 0.25 m 標本では 30 mm の波状摩耗が %.2f m のうねりに化ける"
          "(対照群の %.0f 倍)。" % (sa["alias30"], sa["ghost"] / max(sa["ctrl"], 1e-9)))
    print("  * 非対称弦は長波長の死角を消すが、λ=0.100 m に |H|=%.6f の死角を作る。"
          % asy["h010"])
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(壊れたら鳴る)---
    assert tr["max_err"] < 0.01, tr["max_err"]
    assert tr["blind_amp"] < 0.005, tr["blind_amp"]
    assert zp["lo"]["meas"] / zp["lo"]["true"] < 0.02
    assert zp["hi"]["meas"] / zp["hi"]["true"] > 1.8
    assert bd["max"] / bd["min"] > 10.0, (bd["min"], bd["max"])
    assert len(dc["dead"]) >= 2, dc["dead"]
    assert len(du["bad"]) == 1 and abs(du["bad"][0]["lam"] - 1.0) < 1e-9
    assert max(abs(d["rel"]) for d in du["ok"]) < 0.10
    assert abs(sa["alias30"] - 0.75) < 1e-6, sa["alias30"]
    assert sa["ghost"] > 20.0 * sa["ctrl"], (sa["ghost"], sa["ctrl"])
    assert asy["h010"] < 1e-6 < asy["hmin_long"], (asy["h010"], asy["hmin_long"])
    assert len(sc["rows"]) == len(COMPONENTS)

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
