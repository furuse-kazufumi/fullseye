# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 背景の縞の歪みからガラス瓶を逆に測る ―― 外半径・壁厚・屈折率・液面を、シミュレーションの真値で採点し、分けられない量は分けられないと出す。

【問い】透明な瓶は、後ろに置いた縞模様を歪めて見せる。その歪み(画素ごとに「背景のどこを見ているか」u)から、瓶の外半径・壁の厚み・ガラスと液体の屈折率・液面を
逆に当てはめられるか。当てはまるとして、どの量が本当に分かり、どの量は他の量と取り替えがきくか(分けられないか)。

新 op 2 本(`watervision`、`opsoptics` の `watervision`):
  * `bottle_background_map` ―― `bottle_image` と同じ瓶・同じカメラで、明るさでなく「各画素の光線が背景の板に当たる座標 u」を返す(ベクトルのスネルの式で追跡)。
  * `bottle_fit_from_pattern` ―― u の地図から (外半径, 壁厚, n_glass, n_liquid, 液面) を最小二乗で当てはめ、標準偏差・相関行列・条件数・弱い方向を返す。

【inverse crime を避ける】観測を作る描画(`bottle_background_map`: 円と直線の交点を順に追うベクトルのスネルの式)と、逆当てはめの順モデル(同心円の閉形式: 光線を
「向きの角と軸からの距離」で持ち、界面ごとに asin(b/r) で曲げる)は**別の導出**で、同じコードを共有しない。さらに第 3 の導出(近軸の 2 × 2 光線行列)で中心の傾きを検算し、
別系統の液面(`bottle_image` の背面光の明暗 → `fill_level_from_image`)と突き合わせる。

【真値の開示(「異常に良い結果は内訳を疑う」)】真値は**自分で作ったシミュレーションの入力**(R = 30 mm・壁 1.5 mm・n_glass 1.52・水 1.333 / 油 1.47・充填 5 通り)であって、
実物の瓶の測定ではない。観測も当てはめも、理想の針穴カメラ・完全な円筒・分散なし・既知のカメラ距離と背景距離・点の標本化(画素の開口で縞が平均化されない)を仮定する。
雑音なしで 1e-6 以下に戻るのは、2 つの独立な導出が同じ幾何光学の式に同じ入力を渡した結果であり、「実物でそうなる」ことの証拠ではない。
**精度と正確さは別**: 雑音だけが誤差なら標準偏差は 1e-4 mm 台になるが、カメラ距離・背景距離・画素位置の較正の誤差はそれより桁違いに大きく、ガラスの屈折率を動かす(下の章 5)。
縦の屈折(肩・底)と縦に傾いた光線は `bottle_image` と同じく扱わない。

  1. **順問題の検算**: 2 つの導出(追跡と閉形式)が全画素で一致、近軸の行列が中心の傾きに一致、真っ直ぐな背景の外側は直線。
  2. **雑音なしの回収**: 水・油 × 充填 5 通りで R・壁・n_glass・n_liquid・液面を 1e-6 / 1 画素で回収。空の瓶は液面「無し」、満の瓶も液面「無し」(屈折率は戻る)。
  3. **縞を撮って u を戻す**: 周期 256・32・4 mm の 4 ステップ位相シフトを 8 bit・雑音つきで撮り、階層的にほどいて u を作る。雑音 300 回で R 1 %・液面 1 画素・n_liquid 2 % 以内。
  4. **別系統の液面**: u の行間の不連続(この PoC)と、背面光の明暗(`fill_level_from_image`)が 1 画素以内で一致。
  5. **分けられない量**: 壁厚と n_glass の相関、使える窓を狭めたときの標準偏差、薄い壁、背景距離と n_liquid の縮退、較正の誤差が引き起こす偏り。
  6. **壊して確かめる**: n_glass を 1.4 に固定する / スネルの式の向きを逆にする → 残差が雑音床を越えて門が赤になる。

★正直な限界: 上の「真値の開示」のとおり。さらに、縞を標本化する画素の開口を無視している(縁では 1 画素が縞の数周期に広がる; その画素は隣の列との差で除く)、
使える画素は全反射で落ちる所と縁の 3 画素を除いた内側、雑音は加算ガウスと 8 bit 量子化だけ(固定パターン・光量の揺らぎ・背景の印刷誤差なし)。
【学習】0。【較正】0(カメラと背景の距離は既知として渡す)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import watermedia as WM  # noqa: E402
import watervision as WV  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}

R_B, T_B, N_G, H_B = 30.0, 1.5, 1.52, 80.0
DC, DB = 500.0, 150.0
PITCH_UM = 50.0
PITCH = PITCH_UM / 1000.0
LIQUIDS = (("水", 1.333), ("油", 1.47))
FILLS = (0.1, 0.3, 0.5, 0.7, 0.9)
PERIODS = (256.0, 32.0, 4.0)       # 背景の縞の周期 [mm]: 粗 → 細。粗い縞が u の全域(±128 mm)を一意にし、細い縞が精度を出す
SIGMA_DN = 1.5                     # 縞の画像に足す雑音(8 bit の階調で)
STEP_LIMIT_MM = 1.0                # 隣の列で u が 1 mm(細い縞の 1/4)以上動く画素は、画素の開口で縞が平均されるので使わない
BAND_ROWS = 40                     # 雑音の試行は液面を挟む 40 行の帯で回す(行は互いに独立なので、全高と同じデータの行を減らしたもの)
N_TRIALS = 40 if REDUCED else 300       # 各区間 1 行で使う雑音の試行数(水・油)
N_TRIALS_ALL = 10 if REDUCED else 60    # 各区間の全行(約 18 行)で使う試行数
N_SWEEP = 8 if REDUCED else 20          # 壁厚の掃引の 1 点あたりの試行数


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


def full_map(fill, nl, t=T_B, ng=N_G, R=R_B, db=DB, dc=DC):
    return WV.bottle_background_map(R, t, H_B, fill, ng, nl, db, dc, PITCH_UM)


def band_map(fill_in_band, nl, t=T_B, ng=N_G, R=R_B, db=DB, dc=DC):
    """液面を挟む BAND_ROWS 行だけの地図(高さ BAND_ROWS × 画素, 液面は帯の中の fill_in_band)。"""
    return WV.bottle_background_map(R, t, BAND_ROWS * PITCH, fill_in_band, ng, nl, db, dc, PITCH_UM, size=(BAND_ROWS, 1380))


def observe(m, rng, sigma_dn=SIGMA_DN, periods=PERIODS):
    """縞を 4 ステップ位相シフトで撮り(8 bit・雑音つき)、階層的にほどいて u を戻す。使えない画素は NaN。

    撮る画像 = 255 (0.5 + 0.5 w cos(2π u / P + kπ/2))、w は光線のフレネル透過率の積(縁では縞のコントラストが落ちる)。
    u の戻し方は画素ごとに独立: 粗い縞の位相 → 中くらい → 細い縞(前の段の u から整数周期を決める)。"""
    u, w = m["u_mm"], m["weight"]
    phases = []
    for P in periods:
        imgs = []
        for k in range(4):
            val = 255.0 * (0.5 + 0.5 * w * np.cos(2.0 * np.pi * u / P + k * np.pi / 2.0))
            if sigma_dn > 0.0:
                val = val + rng.normal(0.0, sigma_dn, val.shape)
            imgs.append(np.round(np.clip(val, 0.0, 255.0)))
        phases.append(np.arctan2(imgs[3] - imgs[1], imgs[0] - imgs[2]))
    out = phases[0] / (2.0 * np.pi) * periods[0]
    for P, ph in zip(periods[1:], phases[1:]):
        frac = ph / (2.0 * np.pi) * P
        out = frac + P * np.round((out - frac) / P)
    out = np.where(m["valid"], out, np.nan)
    big = np.abs(np.diff(out, axis=1)) > STEP_LIMIT_MM
    bad = np.zeros(out.shape, dtype=bool)
    bad[:, :-1] |= big
    bad[:, 1:] |= big
    return np.where(bad, np.nan, out)


def fit(u, x, **kw):
    return WV.bottle_fit_from_pattern(u, x, PITCH_UM, DC, DB, **kw)


def rel(a, b):
    return abs(a - b) / abs(b)


# --------------------------------------------------------------------------- #
# 1. 順問題の検算(第 3 の導出: 近軸の行列)                                        #
# --------------------------------------------------------------------------- #
def paraxial_slope(nl, t=T_B, ng=N_G, R=R_B, dc=DC, db=DB):
    """針穴から出た近軸光線が背景に着く u / x の傾きを、2 × 2 の光線行列(y, n·傾き)で。追跡とも閉形式とも別の導出。"""
    Ri = R - t

    def T(d, n):
        return np.array([[1.0, d / n], [0.0, 1.0]])

    def S(n1, n2, r):
        return np.array([[1.0, 0.0], [-(n2 - n1) / r, 1.0]])
    M = (T(db - R, 1.0) @ S(ng, 1.0, -R) @ T(t, ng) @ S(nl, ng, -Ri) @ T(2.0 * Ri, nl) @ S(ng, nl, Ri) @ T(t, ng)
         @ S(1.0, ng, R) @ T(dc - R, 1.0))
    return float(M[0, 1] / dc)


def chapter_forward(maps):
    print("\n1. 順問題: 観測を作る描画と、当てはめの順モデルと、近軸の行列")
    out = {}
    worst_para = 0.0
    for name, nl in LIQUIDS:
        m = maps[(name, 0.5)]
        x = m["x_mm"]
        u = m["u_mm"]
        c = np.abs(x) < 0.2
        # 上の行(空)と下の行(液)の中心の傾き
        for label, row, core in (("空", 0, 1.0), ("液", -1, nl)):
            slope = np.polyfit(x[c], u[row][c], 1)[0]
            pred = paraxial_slope(core, t=T_B)
            worst_para = max(worst_para, rel(slope, pred))
        out[name] = m
    print("   中心の傾き u/x: 追跡と近軸の行列の相対差 最大 %.2e" % worst_para)
    gate("中心の傾きが近軸の 2×2 行列(第 3 の導出)に 1e-4(追跡の刻み 1e-6 mm と有限の画素による)", worst_para < 1e-4, "%.2e" % worst_para)
    m = out["水"]
    xs = m["x_mm"]
    outside = np.abs(xs) > R_B * 1.05
    straight = float(np.abs(m["u_mm"][0][outside] - m["u_straight_mm"][outside]).max())
    gate("瓶の外の画素は真っ直ぐな背景の写像 x (dc + db) / dc に厳密(2e-12 mm 以下)", straight < 2e-12, "%.1e mm" % straight)
    gate("同じ種類の行は bit 一致(液面の上 / 下、NaN の位置も)", bool(np.array_equal(m["u_mm"][0], m["u_mm"][10], equal_nan=True) and np.array_equal(m["u_mm"][-1], m["u_mm"][-10], equal_nan=True)))
    gate("空の断面は縁の全反射で画素を落とし(数える)、液の断面は落とさない", m["tir_rays"] > 0 and bool(m["valid"][-1].all()),
         "全反射の光線 %d 本(%d 画素 × 行)" % (m["tir_rays"], int((~m["valid"][0]).sum())))
    NUMBERS["para"] = worst_para
    return out


# --------------------------------------------------------------------------- #
# 2. 雑音なしの回収                                                              #
# --------------------------------------------------------------------------- #
def chapter_noise_free(maps):
    print("\n2. 雑音なし: u の地図から直接当てはめる(第 2 の導出で当てる ← 追跡で作った地図)")
    rows = []
    worst = 0.0
    worst_level = 0.0
    rms_max = 0.0
    results = {}
    t0 = time.time()
    for name, nl in LIQUIDS:
        for fill in FILLS:
            m = maps[(name, fill)] if (name, fill) in maps else full_map(fill, nl)
            maps[(name, fill)] = m
            r = fit(m["u_mm"], m["x_mm"])
            results[(name, fill)] = r
            errs = (rel(r["radius_mm"], R_B), rel(r["wall_mm"], T_B), rel(r["n_glass"], N_G), rel(r["n_liquid"], nl))
            worst = max(worst, max(errs))
            lv = abs(r["level_mm"] - m["fill_z_mm"])
            worst_level = max(worst_level, lv)
            rms_max = max(rms_max, r["residual_rms_mm"])
            rows.append((name, fill, r, errs, lv))
            print("   %s 充填 %.1f: R %.7f  壁 %.7f  n_g %.7f  n_l %.7f  液面 %.3f mm(真値 %.3f)  残差 %.1e mm  cond %.1f" % (
                name, fill, r["radius_mm"], r["wall_mm"], r["n_glass"], r["n_liquid"], r["level_mm"], m["fill_z_mm"], r["residual_rms_mm"], r["cond"]))
    gate("水・油 × 充填 5 通りで R・壁・n_glass・n_liquid の相対誤差が 1e-6 以下", worst < 1e-6, "最大 %.1e" % worst)
    gate("液面が真値に画素の 1 つ以内(実際は行境界で 0)", worst_level <= PITCH + 1e-9, "最大 %.1e mm" % worst_level)
    gate("残差の RMS が 1e-8 mm 以下(追跡と閉形式が全画素で一致 ← 2 つの導出の検算)", rms_max < 1e-8, "%.1e mm" % rms_max)
    NUMBERS["noisefree_worst"] = worst
    NUMBERS["noisefree_rms"] = rms_max
    # 空・満
    me = full_map(0.0, 1.333)
    re = fit(me["u_mm"], me["x_mm"])
    gate("空の瓶: 液面は「無し」(行の間に不連続が無い)、芯の屈折率は 1.0(空気)に戻り、R・壁・n_glass は 1e-6", (not re["level_found"]) and abs(re["n_liquid"] - 1.0) < 1e-6
         and rel(re["radius_mm"], R_B) < 1e-6 and rel(re["wall_mm"], T_B) < 1e-6 and rel(re["n_glass"], N_G) < 1e-6,
         "level_found=%s、n = %.8f、状態 %s" % (re["level_found"], re["n_liquid"], re["fill_state"]))
    for name, nl in LIQUIDS:
        mf = full_map(1.0, nl)
        rf = fit(mf["u_mm"], mf["x_mm"])
        gate("満の瓶(%s): 液面は「無し」、屈折率は 1e-6 で戻る(行の違いが無いので液面は測れない)" % name, (not rf["level_found"]) and rel(rf["n_liquid"], nl) < 1e-6,
             "level_found=%s、n = %.8f、cond %.0f" % (rf["level_found"], rf["n_liquid"], rf["cond"]))
    gate("瓶の写っていない地図(定数 / 真っ直ぐな背景だけ)は拒否", refused(lambda: fit(np.full((20, 1380), 3.0), me["x_mm"]))
         and refused(lambda: fit(np.tile(me["u_straight_mm"], (20, 1)), me["x_mm"])))
    return results, rows


# --------------------------------------------------------------------------- #
# 3. 縞を撮って u を戻す                                                          #
# --------------------------------------------------------------------------- #
def chapter_fringes(maps):
    print("\n3. 縞を撮る(4 ステップ × 周期 %s mm、8 bit、雑音 %.1f 階調)→ u → 当てはめ" % ("/".join("%g" % p for p in PERIODS), SIGMA_DN))
    rng = np.random.default_rng(20261111)
    rows = []
    worst = {"R": 0.0, "nl": 0.0, "lv": 0.0, "ng": 0.0, "wall": 0.0}
    keep = {}
    t0 = time.time()
    for name, nl in LIQUIDS:
        for fill in FILLS:
            m = maps[(name, fill)]
            um = observe(m, rng)
            ok = m["valid"] & np.isfinite(um)
            err = (um - m["u_mm"])[ok]
            r = fit(um, m["x_mm"])
            keep[(name, fill)] = (um, r, float(err.std()), float(ok.mean() / m["valid"].mean()))
            e = (rel(r["radius_mm"], R_B), rel(r["wall_mm"], T_B), rel(r["n_glass"], N_G), rel(r["n_liquid"], nl), abs(r["level_mm"] - m["fill_z_mm"]))
            worst["R"], worst["wall"], worst["ng"], worst["nl"], worst["lv"] = (max(worst["R"], e[0]), max(worst["wall"], e[1]), max(worst["ng"], e[2]),
                                                                              max(worst["nl"], e[3]), max(worst["lv"], e[4]))
            rows.append((name, fill, r, e))
            print("   %s 充填 %.1f: u の誤差 %.1f µm(使える画素 %.0f %%)  R %.4f  壁 %.4f  n_g %.4f  n_l %.4f  液面 %.2f mm  残差 %.4f mm" % (
                name, fill, 1e3 * err.std(), 100 * ok.mean() / m["valid"].mean(), r["radius_mm"], r["wall_mm"], r["n_glass"], r["n_liquid"], r["level_mm"], r["residual_rms_mm"]))
    sd = float(np.mean([v[2] for v in keep.values()]))
    NUMBERS["u_noise_um"] = 1e3 * sd
    print("   u の雑音 平均 %.1f µm = %.2f 画素(背景面の mm を軸の面の画素 %.0f µm に換算して)、%.1f 秒" % (1e3 * sd, sd / (PITCH * (DC + DB) / DC), PITCH_UM, time.time() - t0))
    gate("全 10 構成(縞の画像 → u → 当てはめ): R が 1 % 以内", worst["R"] < 0.01, "最大 %.2e" % worst["R"])
    gate("全 10 構成: 液面が 1 画素以内", worst["lv"] <= PITCH + 1e-9, "最大 %.3f mm" % worst["lv"])
    gate("全 10 構成: n_liquid が 2 % 以内", worst["nl"] < 0.02, "最大 %.2e" % worst["nl"])
    print("   参考(門にしない): n_glass 最大 %.2e、壁厚 最大 %.2e" % (worst["ng"], worst["wall"]))
    NUMBERS["fringe_worst_R"], NUMBERS["fringe_worst_nl"], NUMBERS["fringe_worst_ng"], NUMBERS["fringe_worst_wall"] = worst["R"], worst["nl"], worst["ng"], worst["wall"]
    return keep, rows


def trial_stats(fill, nl, n, rows_per_section, seed, t=T_B, ng=N_G, restarts=1, window=None):
    """帯の地図に雑音を n 回かけ、その都度、縞 → u → 当てはめ。推定値・予測 σ・収束・「分けられた」の旗を返す。"""
    rng = np.random.default_rng(seed)
    m = band_map(fill, nl, t=t, ng=ng)
    x = m["x_mm"]
    est, sig, conv, sep, poor = [], [], [], [], []
    for _ in range(n):
        um = observe(m, rng)
        if window is not None:
            um = np.where(np.abs(x)[None, :] <= window * R_B, um, np.nan)
        try:
            r = fit(um, x, rows_per_section=rows_per_section, restarts=restarts)
        except ValueError:
            continue
        est.append([r["radius_mm"], r["wall_mm"], r["n_glass"], r["n_liquid"]])
        sig.append([r["sigma"][k] for k in ("radius_mm", "wall_mm", "n_glass", "n_liquid")])
        conv.append(bool(r["converged"]))
        sep.append(bool(r["separated"]))
        poor.append(list(r["poorly_determined"]))
    return {"est": np.array(est), "sig": np.array(sig), "conv": np.array(conv, dtype=bool), "sep": np.array(sep, dtype=bool), "poor": poor, "map": m}


def chapter_trials():
    print("\n3b. 雑音(水 50 %%・油 50 %%、液面を挟む %d 行の帯): 各区間 1 行は %d 回、各区間の全行は %d 回" % (BAND_ROWS, N_TRIALS, N_TRIALS_ALL))
    truth = np.array([R_B, T_B, N_G, 1.333])
    summary = {}
    t0 = time.time()
    for name, nl in LIQUIDS:
        truth[3] = nl
        for rps, label, n in ((1, "各区間 1 行", N_TRIALS), (None, "各区間の全行", N_TRIALS_ALL)):
            tr = trial_stats(0.5, nl, n, rps, seed=7 + (rps or 0), restarts=1)
            est, sig = tr["est"], tr["sig"]
            relerr = (est - truth) / truth
            p95 = np.percentile(np.abs(relerr), 95, axis=0)
            emp = est.std(axis=0)
            pred = np.median(sig, axis=0)
            summary[(name, label)] = (relerr, p95, emp, pred, int(tr["conv"].sum()), len(est))
            print("   %s・%s: 試行 %d、収束 %d | 相対誤差 p95: R %.2e 壁 %.2e n_g %.2e n_l %.2e | 経験 σ %s | 予測 σ %s" % (
                name, label, len(est), int(tr["conv"].sum()), p95[0], p95[1], p95[2], p95[3], np.array2string(emp, precision=5), np.array2string(pred, precision=5)))
    worstR = max(float(np.abs(v[0][:, 0]).max()) for v in summary.values())
    worstL = max(float(np.abs(v[0][:, 3]).max()) for v in summary.values())
    allconv = all(v[4] == v[5] for v in summary.values())
    gate("雑音の全試行(水・油 × {1 行・全行})で R が 1 % 以内", worstR < 0.01, "最大 %.2e" % worstR)
    gate("同: n_liquid が 2 % 以内", worstL < 0.02, "最大 %.2e" % worstL)
    gate("同: 全試行で当てはめが収束", allconv, "収束 %s" % ", ".join("%d/%d" % (v[4], v[5]) for v in summary.values()))
    ratios = []
    for v in summary.values():
        ratios.extend((v[3] / np.maximum(v[2], 1e-12)).tolist())
    r_min, r_max = min(ratios), max(ratios)
    print("   予測 σ / 経験 σ: %.2f 〜 %.2f(1 に近いほど共分散が信用できる)、%.1f 秒" % (r_min, r_max, time.time() - t0))
    gate("共分散から予測した σ が経験の σ の 0.5〜2 倍(共分散を信用してよい範囲)", 0.5 < r_min and r_max < 2.0, "%.2f〜%.2f" % (r_min, r_max))
    NUMBERS["pred_over_emp_min"], NUMBERS["pred_over_emp_max"] = r_min, r_max
    NUMBERS["trial_worst_R"], NUMBERS["trial_worst_nl"] = worstR, worstL
    return summary


# --------------------------------------------------------------------------- #
# 4. 別系統の液面                                                                #
# --------------------------------------------------------------------------- #
def chapter_level(keep):
    print("\n4. 液面を 2 通りで: u の行間の不連続(縞)と、背面光の明暗(`fill_level_from_image`)")
    rows = []
    worst = 0.0
    worst_truth = 0.0
    for name, nl in LIQUIDS:
        for fill in FILLS:
            um, r, _, _ = keep[(name, fill)]
            im = WV.bottle_image(R_B, T_B, H_B, fill, N_G, nl, pixel_pitch_um=PITCH_UM)
            lv = WV.fill_level_from_image(im["image"], PITCH_UM, "edge")["level_mm"]
            lp = r["level_mm"]
            d = abs(lp - lv)
            worst = max(worst, d)
            worst_truth = max(worst_truth, abs(lp - fill * H_B))
            rows.append((name, fill, fill * H_B, lp, lv, d))
            print("   %s 充填 %.1f: 真値 %.2f mm | 縞の不連続 %.2f mm | 明暗 %.2f mm | 差 %.3f mm" % (name, fill, fill * H_B, lp, lv, d))
    gate("縞の不連続と明暗の 2 系統の液面が 1 画素以内で一致(10 構成)", worst <= PITCH + 1e-9, "最大 %.3f mm(画素 %.3f mm)" % (worst, PITCH))
    gate("縞による液面が真値に 1 画素以内(10 構成)", worst_truth <= PITCH + 1e-9, "最大 %.3f mm" % worst_truth)
    NUMBERS["level_pair_worst_mm"] = worst
    return rows


# --------------------------------------------------------------------------- #
# 5. 分けられない量                                                              #
# --------------------------------------------------------------------------- #
def chapter_identifiability(keep):
    print("\n5. 何が分かり、何が分けられないか")
    res = {}
    # (a) 相関行列と条件数(水 50 %、全窓)
    um, r, _, _ = keep[("水", 0.5)]
    names = r["corr_names"]
    corr = np.array(r["corr"])
    i_w, i_g = names.index("wall_mm"), names.index("n_glass")
    print("   (a) 水 50 %%・全窓: 壁厚と n_glass の相関 %.3f、cond %.1f、最も弱い方向 %s(相対 1σ %.1e)" % (
        corr[i_w, i_g], r["cond"], {k: round(v, 2) for k, v in r["weak_direction"].items()}, r["weak_rel_sigma"]))
    res["corr"] = (names, corr, r["cond"])
    gate("壁厚と n_glass は強い負の相関(|相関| > 0.8)= 取り替えがきく方向が存在する", abs(corr[i_w, i_g]) > 0.8, "%.3f" % corr[i_w, i_g])
    # (b) 使える窓を狭める
    m = band_map(0.5, 1.333)
    x = m["x_mm"]
    rng = np.random.default_rng(11)
    uo = observe(m, rng)
    wins = (1.0, 0.8, 0.6, 0.4, 0.25, 0.15)
    wrows = []
    for f in wins:
        uw = np.where(np.abs(x)[None, :] <= f * R_B, uo, np.nan)
        try:
            rr = fit(uw, x, restarts=3)
        except ValueError:
            wrows.append((f, None))
            continue
        wrows.append((f, rr))
    print("   (b) 使える窓(中心から R の何割まで)を狭める: 1σ の相対値 [%]")
    for f, rr in wrows:
        if rr is None:
            print("      窓 %.2f: 拒否(使える画素が足りない)" % f)
            continue
        s = rr["sigma"]
        print("      窓 %.2f: R %.4f  壁 %.3f  n_g %.4f  n_l %.4f  | cond %.0f  | 収束 %s  推定 壁 %.3f / n_g %.4f" % (
            f, 100 * s["radius_mm"] / rr["radius_mm"], 100 * s["wall_mm"] / rr["wall_mm"], 100 * s["n_glass"] / rr["n_glass"], 100 * s["n_liquid"] / rr["n_liquid"],
            rr["cond"], rr["converged"], rr["wall_mm"], rr["n_glass"]))
    res["windows"] = wrows
    s_full = wrows[0][1]["sigma"]["wall_mm"] / T_B
    s_q = [rr for f, rr in wrows if f == 0.25][0]
    s_q_wall = s_q["sigma"]["wall_mm"] / s_q["wall_mm"]
    gate("使える窓を R の 25 % に狭めると、壁厚の相対 σ が全窓の 30 倍以上に増える(縁の画素が壁と n_glass を分けている)", s_q_wall > 30 * s_full,
         "全窓 %.2e → 25 %% %.2e(%.0f 倍)" % (s_full, s_q_wall, s_q_wall / s_full))
    NUMBERS["wall_sigma_full"], NUMBERS["wall_sigma_q"] = s_full, s_q_wall
    # (c) 薄い壁 × 使える窓(全窓 / 中心 25 %)
    ts = (0.1, 0.2, 0.4, 0.8, 1.5)
    trows = []
    print("   (c) 壁厚を薄くする(雑音 %d 回、各区間 1 行)。窓 = 使える範囲(中心から R の何割まで)。壁厚が 25 %% 以内に戻った割合 / 外れたのに「分けられた」と言った割合" % N_SWEEP)
    wrong_total = 0
    wrong_silent = 0
    for win in (1.0, 0.25):
        for t in ts:
            tr = trial_stats(0.5, 1.333, N_SWEEP, 1, seed=int(1000 * t) + int(100 * win) + 5, t=t, restarts=1, window=win)
            est, sig = tr["est"], tr["sig"]
            if len(est) == 0:
                trows.append((win, t, float("nan"), 0.0, 0.0, float("nan"), 0.0, 0.0))
                continue
            e = np.abs(est[:, 1] - t) / t
            eg = np.abs(est[:, 2] - N_G) / N_G
            wrong = ~((e < 0.25) & tr["conv"])
            silent = wrong & tr["sep"]
            wrong_total += int(wrong.sum())
            wrong_silent += int(silent.sum())
            trows.append((win, t, float(np.median(e)), float((~wrong).mean()), float(silent.sum() / max(wrong.sum(), 1)), float(np.median(sig[:, 1]) / t),
                          float(tr["sep"].mean()), float(np.median(eg))))
            print("      窓 %.2f・壁 %.1f mm: 壁の誤差の中央値 %.3f、25 %% 以内 %.2f、外れ %d 回のうち「分けられた」と言った %d 回、予測 σ/壁 %.3f、n_g の誤差の中央値 %.3f、分けられたと言った割合 %.2f" % (
                win, t, trows[-1][2], trows[-1][3], int(wrong.sum()), int(silent.sum()), trows[-1][5], trows[-1][7], trows[-1][6]))
    res["walls"] = trows
    by = {(r_[0], r_[1]): r_ for r_ in trows}
    gate("全窓では 0.1 mm の壁も 25 % 以内で戻る(0.9 以上): 縁の画素が壁と n_glass を分けている", by[(1.0, 0.1)][3] >= 0.9, "%.2f" % by[(1.0, 0.1)][3])
    gate("窓が中心 25 % なら、壁 0.1 mm は 25 % 以内に戻らず(0.5 未満)、壁 1.5 mm は戻る(0.9 以上)", by[(0.25, 0.1)][3] < 0.5 and by[(0.25, 1.5)][3] >= 0.9,
         "壁 0.1: %.2f / 壁 1.5: %.2f" % (by[(0.25, 0.1)][3], by[(0.25, 1.5)][3]))
    sil = wrong_silent / max(wrong_total, 1)
    print("      外れた %d 回のうち「分けられた」と言ったもの %d 回(%.1f %%)" % (wrong_total, wrong_silent, 100 * sil))
    gate("壁厚が外れた試行のうち、当てはめが「分けられた」と言い張ったのは 20 % 以下(分けられない量を分けられたと書かない)", wrong_total > 0 and sil <= 0.2, "%d / %d" % (wrong_silent, wrong_total))
    NUMBERS["silent_wrong_fraction"] = sil
    # (d) 背景距離を未知にすると n_liquid と縮退
    rd = fit(uo, x, free_background=True, restarts=3)
    nd = rd["corr_names"]
    cd = np.array(rd["corr"])
    c_nl_db = cd[nd.index("n_liquid"), nd.index("background_distance_mm")]
    print("   (d) 背景距離も未知: n_liquid と背景距離の相関 %.4f、n_glass と n_liquid の相関 %.3f、cond %.0f(既知なら %.0f)" % (
        c_nl_db, cd[nd.index("n_glass"), nd.index("n_liquid")], rd["cond"], r["cond"]))
    gate("背景距離を未知にすると n_liquid と背景距離はほぼ完全に縮退する(|相関| > 0.99)、cond は 5 倍以上に悪化", abs(c_nl_db) > 0.99 and rd["cond"] > 5 * r["cond"],
         "相関 %.4f、cond %.0f → %.0f" % (c_nl_db, r["cond"], rd["cond"]))
    res["bg"] = (rd, r)
    # (e) 較正の誤差が起こす偏り
    base = fit(uo, x, restarts=3)
    sys_rows = []

    def refit(label, u_, x_, dc=DC, db=DB):
        rr = WV.bottle_fit_from_pattern(u_, x_, PITCH_UM, dc, db, restarts=3)
        sys_rows.append((label, rr["radius_mm"] - base["radius_mm"], rr["wall_mm"] - base["wall_mm"], rr["n_glass"] - base["n_glass"], rr["n_liquid"] - base["n_liquid"], rr["residual_rms_mm"]))
    refit("背景距離を +1 mm 誤る", uo, x, db=DB + 1.0)
    refit("カメラ距離を +1 mm 誤る", uo, x, dc=DC + 1.0)
    refit("画素の位置が +0.1 画素ずれる", uo, x + 0.1 * PITCH)
    print("   (e) 較正の誤差が起こす推定値の動き(真値でなく、較正が正しい推定からの差): 雑音だけの 1σ は R %.1e 壁 %.1e n_g %.1e n_l %.1e mm" % (
        base["sigma"]["radius_mm"], base["sigma"]["wall_mm"], base["sigma"]["n_glass"], base["sigma"]["n_liquid"]))
    for lab, dR, dW, dG, dL, rms in sys_rows:
        print("      %s: ΔR %+.4f mm  Δ壁 %+.4f mm  Δn_g %+.5f  Δn_l %+.5f  残差 %.4f mm" % (lab, dR, dW, dG, dL, rms))
    res["sys"] = (base, sys_rows)
    sig_ng = base["sigma"]["n_glass"]
    max_dng = max(abs(r_[3]) for r_ in sys_rows)
    gate("較正の誤差(背景 1 mm・カメラ 1 mm・画素 0.1)が n_glass を動かす量は、雑音の 1σ の 20 倍以上(精度 ≠ 正確さ)", max_dng > 20 * sig_ng,
         "最大 Δn_g %.1e、雑音の σ %.1e(%.0f 倍)" % (max_dng, sig_ng, max_dng / sig_ng))
    NUMBERS["sys_over_noise_ng"] = max_dng / sig_ng
    # (f) 壁厚と n_glass の等高線(窓 40 %・各区間 1 行)
    uw = np.where(np.abs(x)[None, :] <= 0.4 * R_B, uo, np.nan)
    ts_ = np.linspace(1.5 - 0.6, 1.5 + 0.6, 13)
    gs_ = np.linspace(N_G - 0.06, N_G + 0.06, 13)
    sig_noise = None
    grid = np.zeros((gs_.size, ts_.size))
    for i, g in enumerate(gs_):
        for j, t in enumerate(ts_):
            rr = WV.bottle_fit_from_pattern(uw, x, PITCH_UM, DC, DB, known={"wall_mm": float(t), "n_glass": float(g)}, restarts=1, rows_per_section=1)
            grid[i, j] = rr["residual_rms_mm"]
    best = fit(uw, x, restarts=3, rows_per_section=1)
    floor = best["residual_rms_mm"]
    res["grid"] = (ts_, gs_, grid, floor)
    inside = grid < 1.5 * floor
    valley = float(inside.mean())
    ii, jj = np.nonzero(inside)
    corr_v = float(np.corrcoef(ts_[jj], gs_[ii])[0, 1]) if ii.size >= 4 else float("nan")
    print("   (f) 窓 40 %% の (壁厚 × n_glass) 面の残差 RMS: 最小 %.4f mm(雑音の床 %.4f mm)、床の 1.5 倍以内の格子 %d 個(%.0f %%)、その点の (壁厚, n_glass) の相関 %.3f" % (
        float(grid.min()), floor, int(ii.size), 100 * valley, corr_v))
    NUMBERS["valley_fraction"], NUMBERS["valley_corr"] = valley, corr_v
    gate("(壁厚, n_glass) 面に、雑音の床の 1.5 倍以内に収まる細長い谷がある(格子の 4 点以上・半分未満で、壁厚と n_glass の相関 −0.9 より強い)", ii.size >= 4 and valley < 0.5 and corr_v < -0.9,
         "%d 点、%.0f %%、相関 %.3f" % (ii.size, 100 * valley, corr_v))
    return res


# --------------------------------------------------------------------------- #
# 6. 壊して確かめる                                                              #
# --------------------------------------------------------------------------- #
def chapter_probes(keep):
    print("\n6. 壊して確かめる(門が赤になるか)")
    um, r0, sd, _ = keep[("水", 0.5)]
    m = full_map(0.5, 1.333)
    floor = r0["residual_rms_mm"]
    rb = fit(um, m["x_mm"], known={"n_glass": 1.4})
    print("   n_glass を 1.4 に固定: 残差 RMS %.4f mm(正しい当てはめ %.4f mm、%.1f 倍)" % (rb["residual_rms_mm"], floor, rb["residual_rms_mm"] / floor))
    gate("n_glass = 1.4 に固定すると、残差が雑音床の 1.5 倍を越える(門が赤)", rb["residual_rms_mm"] > 1.5 * floor, "%.1f 倍" % (rb["residual_rms_mm"] / floor))
    old = WV._SNELL_ROTATION
    try:
        WV._SNELL_ROTATION = -1.0
        rs = fit(um, m["x_mm"])
    finally:
        WV._SNELL_ROTATION = old
    print("   スネルの式の向きを逆にした順モデル: 残差 RMS %.4f mm(%.1f 倍)" % (rs["residual_rms_mm"], rs["residual_rms_mm"] / floor))
    gate("スネルの式の向きを逆にした順モデルは、残差が雑音床の 5 倍を越える(門が赤)", rs["residual_rms_mm"] > 5 * floor, "%.1f 倍" % (rs["residual_rms_mm"] / floor))
    rw = fit(um, m["x_mm"], known={"radius_mm": 28.0})
    gate("外半径を 28 mm に固定すると残差が雑音床の 1.5 倍を越える", rw["residual_rms_mm"] > 1.5 * floor, "%.1f 倍" % (rw["residual_rms_mm"] / floor))
    gate("拒否: 外半径が壁より小さい・背景が瓶の前・屈折率 1 以下・カメラが近すぎる", all(refused(f_) for f_ in (
        lambda: WV.bottle_background_map(30, 31, 80, 0.5, 1.52, 1.333), lambda: WV.bottle_background_map(30, 1.5, 80, 0.5, 1.52, 1.333, background_distance_mm=20.0),
        lambda: WV.bottle_background_map(30, 1.5, 80, 0.5, 1.0, 1.333), lambda: WV.bottle_background_map(30, 1.5, 80, 0.5, 1.52, 1.333, camera_distance_mm=50.0),
        lambda: fit(um, m["x_mm"], known={"bogus": 1.0}), lambda: fit(np.full((20, 1380), np.nan), m["x_mm"]))))
    NUMBERS["probe_n14"] = rb["residual_rms_mm"] / floor
    NUMBERS["probe_snell"] = rs["residual_rms_mm"] / floor


# --------------------------------------------------------------------------- #
# 図                                                                             #
# --------------------------------------------------------------------------- #
def checker_panel(m, size=8.0):
    """背景の市松(8 mm)を瓶越しに見た絵: 画素 (行 z, 列 u) → 市松。縮小は 4 × 4 の平均。"""
    u = np.where(m["valid"], m["u_mm"], 0.0)
    z = m["z_mm"][:, None]
    ch = ((np.floor(u / size) + np.floor(z / size)) % 2) * 0.8 + 0.1
    ch = 0.5 + (ch - 0.5) * m["weight"]
    ch = np.where(m["valid"], ch, 0.0)
    h, w = ch.shape
    return ch[:h // 4 * 4, :w // 4 * 4].reshape(h // 4, 4, w // 4, 4).mean(axis=(1, 3))


def make_figures(maps, keep, trials, ident, lrows):
    # 1 瓶越しの市松(水 6 枚)
    panels, caps = [], []
    for fill in (0.0, 0.1, 0.3, 0.5, 0.7, 0.9):
        m = maps.get(("水", fill)) or full_map(fill, 1.333)
        panels.append(checker_panel(m))
        caps.append("充填 %d %%" % round(100 * fill))
    figs.save_grid("checker_through_bottle", panels, gray=True, ncols=3, vrange=(0.0, 1.0), captions=caps,
                   title="瓶越しに見た背景の市松(1 マス 8 mm): 液のある所だけ左右が反転し、空の所は縁で全反射して欠ける",
                   caption="R 30 mm・壁 1.5 mm・n 1.52 の瓶、水 1.333。各画素の光線を追跡して背景のどこを見ているか(u)を求め、そこの市松を描いた。逆から見ると、この歪みが瓶を測る手がかり。")
    # 2 u(x) の断面と当てはめ
    um, r, sd, frac = keep[("水", 0.5)]
    m = maps[("水", 0.5)]
    x = m["x_mm"]
    top = np.nanmedian(um[:600], axis=0)
    bot = np.nanmedian(um[900:], axis=0)
    st = m["u_straight_mm"]
    Ri = r["radius_mm"] - r["wall_mm"]
    ux, okx = WV._section_u(x, r["radius_mm"], Ri, r["n_glass"], r["n_liquid"], DC, DB)
    uy, oky = WV._section_u(x, r["radius_mm"], Ri, r["n_glass"], 1.0, DC, DB)
    def fin(label, yv):
        k = np.isfinite(yv) & (np.abs(x) <= 29.0)
        return (label, x[k], yv[k])
    series = [fin("液のある行(観測)", bot - st), fin("空の行(観測)", top - st), fin("当てはめ(液)", np.where(okx, ux - st, np.nan)), fin("当てはめ(空)", np.where(oky, uy - st, np.nan))]
    figs.save_plot("profile_fit", series, xlabel="画像の横位置 x [mm]", ylabel="背景の座標のずれ u − 直線 [mm]", colors=["emphasis", "reference", "right", "right"],
                   styles=[None, None, "dashed", "dashed"], size=(760, 400), xlim=(-29.0, 29.0), ylim=(-420.0, 200.0),
                   title="縞から戻した u の断面(水 50 %%)と、閉形式の当てはめ: 残差 %.4f mm" % r["residual_rms_mm"],
                   caption="縞の位相を 8 bit・雑音つきで撮ってほどいた u から直線(瓶なし)を引いた量。破線が閉形式の当てはめで、観測に重なる。")
    # 3 回収の表
    header = ["液体", "充填", "R [mm]", "壁 [mm]", "n_glass", "n_liquid", "液面 [mm]", "cond"]
    trs = []
    for name, nl in LIQUIDS:
        for fill in FILLS:
            _, rr, _, _ = keep[(name, fill)]
            trs.append([name, "%.1f" % fill, "%.4f" % rr["radius_mm"], "%.4f" % rr["wall_mm"], "%.4f" % rr["n_glass"], "%.4f" % rr["n_liquid"], "%.2f" % rr["level_mm"], "%.0f" % rr["cond"]])
    figs.save_table("recovery_table", header, trs, title="縞から戻した値(真値 R 30・壁 1.5・n_g 1.52)",
                    caption="8 bit・雑音 %.1f 階調。真値は自分で作ったシミュレーションの入力で、実物の測定ではない。" % SIGMA_DN)
    # 4 雑音試行の表
    header = ["液体 / 使う行", "試行", "R の p95 誤差", "壁の p95 誤差", "n_g の p95 誤差", "n_l の p95 誤差", "予測 σ / 経験 σ (R, 壁, n_g, n_l)"]
    trs = []
    for (name, label), (relerr, p95, emp, pred, conv, n) in trials.items():
        trs.append(["%s・%s" % (name, label), "%d" % n, "%.1e" % p95[0], "%.1e" % p95[1], "%.1e" % p95[2], "%.1e" % p95[3], " / ".join("%.2f" % v for v in (pred / np.maximum(emp, 1e-12)))])
    figs.save_table("noise_trials", header, trs, title="雑音 %d / %d 回の相対誤差(95 %% 点)と予測 σ の当たり具合" % (N_TRIALS, N_TRIALS_ALL),
                    caption="雑音だけが誤差なら、1 行ずつの最悪の場合でも R・n_liquid は 1e-4 以下で、予測 σ は経験の σ に 0.67〜1.00 倍で合う。ただし較正の誤りは別(下の表)。")
    # 5 窓
    wrows = ident["windows"]
    fx = np.array([f for f, rr in wrows if rr is not None])

    def col(k):
        return np.array([100.0 * rr["sigma"][k] / rr[k] for f, rr in wrows if rr is not None])
    figs.save_plot("window_sigma", [("壁厚", fx, col("wall_mm")), ("n_glass", fx, col("n_glass")), ("外半径 R", fx, col("radius_mm")), ("n_liquid", fx, col("n_liquid"))],
                   xlabel="使える窓(中心から R の何割まで)", ylabel="相対 1σ [%]", colors=["wrong", "emphasis", "reference", "right"], size=(720, 400),
                   title="縁の画素を失うと、壁厚と n_glass から先に分けられなくなる(窓 0.15 で壁 %.0f %%)" % col("wall_mm")[-1],
                   caption="共分散から予測した 1σ(窓 1.0 は全幅)。縁近くの光線ほど壁と屈折率に敏感なので、窓が狭いと壁厚と n_glass は互いに取り替えがきく。R と n_liquid は最後まで残る。")
    # 6 薄い壁
    trows = ident["walls"]
    full_w = [t for t in trows if t[0] == 1.0]
    mid_w = [t for t in trows if t[0] == 0.25]
    figs.save_plot("thin_wall", [("全窓: 壁が 25 % 以内に戻った割合", np.array([t[1] for t in full_w]), np.array([t[3] for t in full_w])),
                                 ("中心 25 % だけ: 25 % 以内に戻った割合", np.array([t[1] for t in mid_w]), np.array([t[3] for t in mid_w])),
                                 ("中心 25 % だけ: 予測 σ / 壁", np.array([t[1] for t in mid_w]), np.clip(np.array([t[5] for t in mid_w]), 0.0, 1.0))],
                   xlabel="壁厚の真値 [mm]", ylabel="割合 / 相対 σ(1 で頭打ち)", colors=["right", "wrong", "emphasis"], styles=[None, None, "dashed"], size=(760, 400),
                   title="壁が薄いほど、縁を失うと壁厚が n_glass と分かれない(壁 0.1 mm で戻る割合 %.2f)" % mid_w[0][3],
                   caption="雑音 %d 回、各区間 1 行。縁まで使えれば 0.1 mm の壁も戻る(%.2f)が、中心 25 %% だけだと戻らず、当てはめ自身も「分けられていない」と申告する(予測 σ が壁の %.0f %%)。" % (
                       N_SWEEP, full_w[0][3], 100 * min(mid_w[0][5], 9.99)))
    # 7 等高線
    ts_, gs_, grid, floor = ident["grid"]
    vr = (0.0, 6.0)
    z = np.clip(grid / floor, vr[0], vr[1])
    panel = figs._render_heatmap(z, ts_, 1000.0 * (gs_ - N_G), xlabel="横: 壁厚 [mm]", ylabel="縦: n_glass − 1.52 [×1e-3]", vrange=vr, boundary=z < 1.5, size=(640, 480), colorbar_unit="倍")
    figs.save_grid("wall_glass_valley", [panel], ncols=1, captions=["横: 壁厚、縦: n_glass"], title="(壁厚, n_glass) の面の残差: 白線の内側が雑音床の 1.5 倍以内(使える窓 40 %・1 行)",
                   caption="色は残差 / 雑音の床(倍)。他の 2 量(R・n_liquid)は各点で当て直した。壁を厚く・n_glass を下げる(または逆)の対角に細長い谷があり、谷の上の点は雑音の中では見分けがつかない(谷の点の相関 %.2f)。" % NUMBERS["valley_corr"])
    # 8 較正の偏り
    base, srows = ident["sys"]
    header = ["誤差", "ΔR [mm]", "Δ壁 [mm]", "Δn_glass", "Δn_liquid", "残差 [mm]"]
    trs = [["雑音だけの 1σ(推定の標準偏差)", "%.1e" % base["sigma"]["radius_mm"], "%.1e" % base["sigma"]["wall_mm"], "%.1e" % base["sigma"]["n_glass"], "%.1e" % base["sigma"]["n_liquid"], "%.4f(雑音の床)" % base["residual_rms_mm"]]]
    for lab, dR, dW, dG, dL, rms in srows:
        trs.append([lab, "%+.4f" % dR, "%+.4f" % dW, "%+.5f" % dG, "%+.5f" % dL, "%.4f" % rms])
    figs.save_table("calibration_bias", header, trs, title="精度と正確さ: 較正の誤りは雑音より桁違いに効く",
                    caption="カメラ距離・背景距離・画素位置は「既知」として渡す前提。背景距離 1 mm の誤りは n_glass を %.3f(雑音の σ の %.0f 倍)動かし、残差は雑音の床より約 %.0f 倍に増えるだけなので、残差だけでは較正の誤りか屈折率の違いか区別しにくい。" % (
                        abs(srows[0][3]), NUMBERS["sys_over_noise_ng"], srows[0][5] / base["residual_rms_mm"]))
    # 9 液面の 2 系統
    header = ["液体", "充填", "真値 [mm]", "縞の不連続 [mm]", "背面光の明暗 [mm]", "差 [mm]"]
    trs = [[n, "%.1f" % f, "%.2f" % t_, "%.2f" % a_, "%.2f" % b_, "%.3f" % d_] for n, f, t_, a_, b_, d_ in lrows]
    figs.save_table("level_two_ways", header, trs, title="液面を別系統の 2 通りで(縞 / 背面光の明暗)",
                    caption="2 系統は互いに 1 画素(0.05 mm)以内で一致し、どちらも真値(充填 × 80 mm)に 1 画素以内。空の瓶・満の瓶は液面「無し」と返す。")


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("PoC 背景の縞の歪みからガラス瓶を逆に測る(予算 %s)" % ("reduced" if REDUCED else "full"))
    maps = {}
    for name, nl in LIQUIDS:
        for fill in FILLS:
            maps[(name, fill)] = full_map(fill, nl)
    chapter_forward(maps)
    results, rows = chapter_noise_free(maps)
    keep, frows = chapter_fringes(maps)
    trials = chapter_trials()
    lrows = chapter_level(keep)
    ident = chapter_identifiability(keep)
    chapter_probes(keep)
    if figs.target_dir() is not None:
        make_figures(maps, keep, trials, ident, lrows)
    cpu = time.process_time() - c0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
