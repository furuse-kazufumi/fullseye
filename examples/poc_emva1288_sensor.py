# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: カメラを買わずにカメラを測る —— EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す。

カメラのデータシートに並ぶ「量子効率 η・システムゲイン K・暗雑音 σ_d・飽和容量・SNR・ダイナミックレンジ・DSNU・PRNU」は、
EMVA 1288 Release 4.0 Linear の手順で出した数である。この PoC は**物理モデルでセンサを合成**し(光子のポアソン → 電子 → 暗雑音・
暗電流 → K 倍 → 量子化・飽和、画素ごとの DSNU・PRNU の模様つき)、**規格の推定手順**(式 16・18・50・52・53・42・66・67)で
その値を取り戻せるかを見る。合成と推定は別の式 —— 同じ式を往復させていない。

門(真値の出どころ):
  1. **復元**: K・σ_d・η・暗電流・列/行/画素の空間分散・DSNU・PRNU を、仕込んだ値に戻す(許容は各門に記す)。
  2. **恒等式**: SNR(μ_p.min) = 1(式 26 と式 21 は独立に書かれている)/ 理想センサの SNR = √μ_p(式 23)/ 傾き 1 → 1/2(式 22)。
  3. **規格が書いた適用範囲**: σ²_y.dark < 0.24 DN² では σ_d を推定しない(式 53・54)。平らなセンサではそこが本当に推定の壊れる境界。
     ★DSNU の模様があると量子化のディザになり、境界の外でも当たる —— 規格の境界は保守側(種 6 通りで確かめてから書いた)。
  4. **公表値**: メーカーが公表した EMVA 1288 データ(optscene の台帳、38 型番)で、最大 SNR = √μ_e.sat(式 55)と DR(式 28)を検算。
  5. **直線性**: 直線性の誤差(式 58〜63)の閉形式が numpy の重みつき最小二乗(第 2 実装)と一致し、線形に合成したセンサで 1 % 未満。
  6. **欠陥画素**: 仕込んだ熱画素の数を、平均からの偏差のしきい値で数え直す(8.8 節の積算ヒストグラム)。
  7. **規格の模擬カメラ**(Linear 5 節の最後の段落: 640 × 480、DSNU に正弦 2 本、照明が端へ 3 % 落ちる): 8.1 節の高域フィルタで
     照明のむらが PRNU から消え、DSNU は伝達関数どおりに減る。8.6 節のスペクトログラム(式 70〜72)で正弦の振幅を取り戻す。
     付録 C.5 の式 86 の 0.92 は実測の 0.96(Parseval)と合わない。
  8. **式 51**(photon transfer の直線性、General の B-スプラインの局所の傾き): 512 × 640 の線形なセンサは通るが、128 × 160 では
     線形でも落ちることがある —— 2 枚の差の分散の揺れが局所の傾きの揺れになる(画素数が要る)。
  9. **式 3・4・25・69**: 光子数の定数 50.34、SNR の逆関数の SNR = 1 が式 26、総合 SNR の頭打ちが 1/PRNU。

正直に書くこと: 合成センサ(実機の画像ではない)。1〜7 節の照明は一様に作った(高域フィルタは 7 節の模擬カメラで見る)。
公表値の台帳は整数に丸めた値で、K が公表されないので DR の検算は量子化雑音を 0 とみなす。前処理(雑音除去・圧伸など)が数を
どう動かすかと、Release 4.0 General の手順は続編 ``poc_emva1288_in_camera_processing.py``。

Run: py -3.11 examples/poc_emva1288_sensor.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。MP4 は extras [video] があるときだけ)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import sensorchar as SC  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
OK = []

# 仕込む値(真値)
ETA, K, SD, OFFSET, BITS = 0.62, 0.21, 3.4, 40.0, 12
DARK_E_PER_S = 150.0
H, W = 96, 128
MAXDN = (1 << BITS) - 1


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def patterns(rng):
    """DSNU(列・行・画素の加算の模様、DN)と PRNU(乗算の模様)。"""
    col = 1.2 * rng.standard_normal(W)[None, :]
    row = 0.7 * rng.standard_normal(H)[:, None]
    pix = 0.9 * rng.standard_normal((H, W))
    prnu = 1.0 + 0.015 * rng.standard_normal((H, W)) + 0.01 * np.sin(np.linspace(0, 6, W))[None, :]
    return {"col": col, "row": row, "pix": pix, "dsnu": col + row + pix, "prnu": prnu}


def shot(rng, mu_p, pat, *, k=K, sd=SD, dark_e=0.0):
    """物理モデル: 光子 → 電子(ポアソン)+ 暗電流(ポアソン)→ 暗雑音(電子)→ K 倍 + オフセット + DSNU → 量子化・飽和。"""
    e = rng.poisson(ETA * mu_p * pat["prnu"])
    if dark_e > 0:
        e = e + rng.poisson(dark_e, (H, W))
    y = k * (e + rng.normal(0.0, sd, (H, W))) + OFFSET + pat["dsnu"]
    return np.clip(np.round(y), 0, MAXDN)


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    rng = np.random.default_rng(1288)
    pat = patterns(rng)
    print("仕込んだ値: η = %.2f、K = %.2f DN/e⁻、σ_d = %.1f e⁻、暗電流 %.0f e⁻/s、画像 %d × %d、%d bit" % (ETA, K, SD, DARK_E_PER_S, W, H, BITS))

    # ─────────────────────────────── 1. photon transfer ─────────────────────────────
    print("== 1. 露光を振って 2 枚ずつ撮る → 平均と時間分散(式 16・18)→ photon transfer(式 50)と応答(式 49・52)")
    n_lv = 16 if REDUCED else 32
    mu_p_sat = (MAXDN - OFFSET) / (K * ETA)
    mp = np.linspace(0.0, 1.02 * mu_p_sat, n_lv)
    pairs = [(shot(rng, m, pat), shot(rng, m, pat)) for m in mp]
    st = [SC.emva_pair_statistics(a, b) for a, b in pairs]
    mu = np.array([s["mu"] for s in st])
    var = np.array([s["var_temporal"] for s in st])
    sat_frac = np.array([float((a == MAXDN).mean()) for a, _ in pairs])
    i_sat = int(np.argmax(var))                      # 分散が最大の露光 = 飽和の手前(その先は飽和で分散が潰れる)
    mu_sat = float(mu[i_sat])
    ptc = SC.emva_photon_transfer(mu[1:], var[1:], mu[0], var[0], mu_sat)
    qe = SC.emva_quantum_efficiency(mp[1:], mu[1:], mu[0], mu_sat, ptc["K"])
    eK, eS, eE = ptc["K"] / K - 1, ptc["sigma_d"] / SD - 1, qe["eta"] / ETA - 1
    print("  %d 段、飽和 μ_y.sat = %.0f DN(飽和画素 %.1f %%)、当てはめ %d 点(0〜70 %%)" % (n_lv, mu_sat, 100 * sat_frac[i_sat], ptc["n_points"]))
    print("  K   仕込み %.4f → 推定 %.4f(%+.2f %%)" % (K, ptc["K"], 100 * eK))
    print("  σ_d 仕込み %.3f → 推定 %.3f e⁻(%+.2f %%、式 53 = 暗画像から直接)" % (SD, ptc["sigma_d"], 100 * eS))
    print("  η   仕込み %.3f → 推定 %.3f(%+.2f %%)" % (ETA, qe["eta"], 100 * eE))
    sd_icpt = math.sqrt(max(var[0] + ptc["offset"] - SC.SIGMA_Q2, 0.0)) / ptc["K"]
    print("  (比べ)σ_d を photon transfer の切片から出すと %.3f e⁻(%+.1f %%)—— 切片は K のためのもの" % (sd_icpt, 100 * (sd_icpt / SD - 1)))
    gate("復元: K・σ_d・η が仕込んだ値に 3 %・5 %・4 % 以内", abs(eK) < 0.03 and abs(eS) < 0.05 and abs(eE) < 0.04)
    # 直線性の誤差 LE(式 58〜63): 相対偏差の重み 1/y² の当てはめ。第 2 実装 = numpy の重みつき最小二乗(np.polyfit の w = 1/y)
    le = SC.emva_linearity_error(mp, mu, mu[0], mu_sat)
    u = le["used"]
    a1_np, a0_np = np.polyfit(mp[u], (mu - mu[0])[u], 1, w=1.0 / (mu - mu[0])[u])
    le_diff = max(abs(le["a0"] - a0_np) / max(1.0, abs(a0_np)), abs(le["a1"] / a1_np - 1))
    print("  直線性の誤差 LE = %.3f %%(飽和の 5〜95 %% の %d 点)、式 59〜61 と numpy の重みつき最小二乗の差 %.1e" % (le["LE_percent"], int(u.sum()), le_diff))
    gate("直線性: 式 59〜61 の閉形式が独立の重みつき最小二乗と 1e-9、合成(線形)センサの LE < 1 %", le_diff < 1e-9 and le["LE_percent"] < 1.0)

    # ─────────────────────────────── 2. 恒等式 ─────────────────────────────
    print("== 2. 恒等式: SNR(μ_p.min) = 1(式 26 と 21)、理想 SNR = √μ_p(式 23)、傾き 1 → 1/2(式 22)")
    th = SC.emva_sensitivity_threshold(ETA, SD, K)
    s1 = abs(SC.emva_snr_curve([th["mu_p_min"]], ETA, SD, K)[0, 1] - 1.0)
    grid = np.logspace(-1, 5, 200)
    s2 = float(np.abs(SC.emva_snr_curve(grid, 1.0, 0.0, 1.0, sigma_q2=0.0)[:, 1] - np.sqrt(grid)).max())
    c = SC.emva_snr_curve(np.logspace(-3, 7, 400), ETA, SD, K)
    sl = np.diff(np.log(c[:, 1])) / np.diff(np.log(c[:, 0]))
    dr = SC.emva_dynamic_range(mu_p_sat, th["mu_p_min"])
    print("  μ_p.min = %.2f 光子(μ_e.min = %.2f e⁻ > σ_d = %.1f —— 量子化雑音の分)、SNR(μ_p.min) − 1 = %.1e" % (th["mu_p_min"], th["mu_e_min"], SD, s1))
    print("  理想 SNR と √μ_p の差 %.1e(200 点)、傾き 低露光 %.4f → 高露光 %.4f" % (s2, sl[0], sl[-1]))
    print("  DR = %.0f 倍 = %.1f dB = %.2f bit、最大 SNR = √μ_e.sat = %.1f dB(式 55)" % (dr["ratio"], dr["dB"], dr["bits"], 10 * math.log10(ETA * mu_p_sat)))
    gate("恒等式: SNR(μ_p.min) = 1(1e-12)・理想 = √μ_p(1e-9)・傾き 1 → 1/2(1e-2)", s1 < 1e-12 and s2 < 1e-9 and abs(sl[0] - 1) < 1e-2 and abs(sl[-1] - 0.5) < 1e-2)

    # ─────────────────────────────── 3. 暗電流 ─────────────────────────────
    print("== 3. 暗電流(7.1 節): 暗画像の平均と分散を露光時間に当てる(6 点以上)")
    t = np.linspace(0.0, 1.0, 8)
    ds = [SC.emva_pair_statistics(shot(rng, 0.0, pat, dark_e=DARK_E_PER_S * tt), shot(rng, 0.0, pat, dark_e=DARK_E_PER_S * tt)) for tt in t]
    dc = SC.emva_dark_current(t, [d["mu"] for d in ds], ptc["K"], var_y_dark=[d["var_temporal"] for d in ds])
    print("  平均の傾きから %.1f e⁻/s(%+.1f %%)、分散の傾きから %.1f e⁻/s(%+.1f %%)—— 規格が平均を推すのは精度の差" % (
        dc["mu_I_e"], 100 * (dc["mu_I_e"] / DARK_E_PER_S - 1), dc["mu_I_e_from_var"], 100 * (dc["mu_I_e_from_var"] / DARK_E_PER_S - 1)))
    gate("復元: 暗電流が平均から 3 % 以内", abs(dc["mu_I_e"] / DARK_E_PER_S - 1) < 0.03)

    # ─────────────────────────────── 4. 空間の不均一 ─────────────────────────────
    L = 16 if REDUCED else 50
    print("== 4. 空間の不均一: %d 枚平均 → 時間雑音の残り σ²/L を引き(式 36)、列・行・画素に分ける(式 42)" % L)
    dark = np.stack([shot(rng, 0.0, pat) for _ in range(L)])
    mp50 = 0.5 * mu_p_sat
    bright = np.stack([shot(rng, mp50, pat) for _ in range(L)])
    sn = SC.emva_spatial_nonuniformity(dark, bright, ptc["K"])
    d = sn["dark"]
    tru = {"s2_col": float(pat["col"].var()), "s2_row": float(pat["row"].var()), "s2_pixel": float(pat["pix"].var())}
    errs = {k: d[k] / tru[k] - 1 for k in tru}
    dsnu_true = float(pat["dsnu"].std()) / K
    prnu_true = float(pat["prnu"].std() / pat["prnu"].mean())
    raw = float(dark.mean(axis=0).var())
    print("  暗画像の空間分散: 列 %.3f(真 %.3f)行 %.3f(真 %.3f)画素 %.3f(真 %.3f)DN²" % (
        d["s2_col"], tru["s2_col"], d["s2_row"], tru["s2_row"], d["s2_pixel"], tru["s2_pixel"]))
    print("  時間雑音の残りを引かないと %.3f DN² —— 式 36 の補正 %.3f" % (raw, raw - d["s2"]))
    print("  DSNU1288 = %.2f e⁻(真 %.2f、%+.1f %%)、PRNU1288 = %.2f %%(真 %.2f %%、%+.1f %%)" % (
        sn["DSNU1288_e"], dsnu_true, 100 * (sn["DSNU1288_e"] / dsnu_true - 1), 100 * sn["PRNU1288"], 100 * prnu_true,
        100 * (sn["PRNU1288"] / prnu_true - 1)))
    gate("復元: 列・行・画素の空間分散 15 %、DSNU 5 %、PRNU 10 % 以内",
         max(abs(v) for v in errs.values()) < 0.15 and abs(sn["DSNU1288_e"] / dsnu_true - 1) < 0.05 and abs(sn["PRNU1288"] / prnu_true - 1) < 0.10,
         "(列 %+.1f / 行 %+.1f / 画素 %+.1f %%)" % tuple(100 * errs[k] for k in ("s2_col", "s2_row", "s2_pixel")))

    # ─────────────────────────────── 5. 適用範囲の境界 ─────────────────────────────
    print("== 5. 規格の適用範囲: σ²_y.dark < 0.24 DN² では σ_d を推定しない(式 53・54)—— 本当に境界か")
    flat = {"dsnu": np.zeros((H, W)), "prnu": np.ones((H, W))}
    Ks = np.array([0.03, 0.05, 0.07, 0.10, 0.14, 0.21, 0.35, 0.5, 1.0, 2.0])
    n_rep = 2 if REDUCED else 6
    bnd = {"flat": [], "pattern": []}
    for kx in Ks:
        for nm, pp in (("flat", flat), ("pattern", pat)):
            ev, vv = [], []
            for _ in range(n_rep):
                v = SC.emva_pair_statistics(shot(rng, 0.0, pp, k=kx), shot(rng, 0.0, pp, k=kx))["var_temporal"]
                vv.append(v)
                ev.append(abs(math.sqrt(max(v - SC.SIGMA_Q2, 0.0)) / kx / SD - 1))
            bnd[nm].append((float(np.mean(vv)), float(np.median(ev)), float(np.max(ev))))
    ok_flat = all((e_max < 0.05) if v >= 0.24 else (e_med > 0.05) for v, e_med, e_max in bnd["flat"])
    for kx, (vf, ef, _), (vp, ep, _) in zip(Ks, bnd["flat"], bnd["pattern"]):
        print("  K = %.2f: σ²_y.dark %.3f DN²(%s)σ_d の誤差 平ら %5.1f %% / 模様あり %5.1f %%" % (
            kx, vf, "有効" if vf >= 0.24 else "無効", 100 * ef, 100 * ep))
    i10 = int(np.argmin(np.abs(Ks - 0.10)))
    gate("境界: 平らなセンサでは「有効」側 5 %% 以内・「無効」側は外れる(乱数 %d 通り)" % n_rep, ok_flat)
    print("  ★模様あり(DSNU)では K = 0.10 の無効側でも %.1f %%(平ら %.1f %%)—— 画素ごとの暗レベルのずれが量子化のディザになる。"
          "規格の境界は保守側。" % (100 * bnd["pattern"][i10][1], 100 * bnd["flat"][i10][1]))

    # ─────────────────────────────── 6. 公表値 ─────────────────────────────
    print("== 6. 公表値: メーカーが公表した EMVA 1288 データ(台帳 38 型番、整数に丸めた値)で式 (55)(28) を検算")
    import optscene
    # 型番(社名が分かる)は図・ログに出さず、台帳の並び順の番号で書く(公開 PoC に社名を書かない規則)
    rows, bad_dr = [], []
    for idx, (model, v) in enumerate(optscene._SENSOR_CATALOG.items()):
        qe_, sd_, sat, dr_db, snr_db = v[6] / 100.0, v[7], v[8] * 1e3, v[9], v[10]
        snr_calc = 20.0 * math.log10(math.sqrt(sat))
        t_ = SC.emva_sensitivity_threshold(qe_, sd_, 1.0, sigma_q2=0.0)
        dr_calc = SC.emva_dynamic_range(sat / qe_, t_["mu_p_min"])["dB"]
        rows.append(("台帳の %d 番目" % (idx + 1), snr_db, snr_calc, dr_db, dr_calc, model))
        if abs(dr_calc - dr_db) > 3.0:
            bad_dr.append(rows[-1][0])
    d_snr = [abs(r[2] - r[1]) for r in rows]
    d_dr = [r[4] - r[3] for r in rows]
    print("  最大 SNR: 全 %d 型番で公表値との差 最大 %.2f dB(丸めの幅 0.5 dB 以内)" % (len(rows), max(d_snr)))
    print("  DR: 差 %.1f〜%+.1f dB(中央値 %+.2f)、3 dB を越えるのは %s" % (min(d_dr), max(d_dr), float(np.median(d_dr)), bad_dr))
    for r in rows:
        if r[0] in bad_dr:
            print("    %s: 飽和 %.1f ke⁻・暗雑音 %d e⁻ からは DR %.1f dB、台帳は %d dB —— 暗雑音か DR の欄が別条件の値と見られる(未確認、台帳は直さない)" % (
                r[0], optscene._SENSOR_CATALOG[r[5]][8], optscene._SENSOR_CATALOG[r[5]][7], r[4], r[3]))
    odd = [r[5] for r in rows if r[0] in bad_dr]
    gate("公表値: 最大 SNR は全型番 0.5 dB 以内、DR は 1 型番(飽和 21.0 ke⁻・暗雑音 7 e⁻ の行)を除き 3 dB 以内",
         max(d_snr) <= 0.5 and len(odd) == 1 and optscene._SENSOR_CATALOG[odd[0]][7:9] == (7, 21.0))

    # ─────────────────────────────── 7. 欠陥画素 ─────────────────────────────
    print("== 7. 欠陥画素(8.8 節): 熱画素を仕込み、平均画像の偏差のしきい値で数え直す")
    hot = rng.choice(H * W, size=9, replace=False)
    avg = dark.mean(axis=0)
    avg_h = avg.copy()
    avg_h.flat[hot] += 40.0
    dp = SC.emva_defect_pixels(avg_h, L, threshold=15.0)
    dp0 = SC.emva_defect_pixels(avg, L, threshold=15.0)
    print("  仕込み 9 個 → しきい値 15 DN を越える画素 %d 個(仕込む前 %d 個)、ヒストグラム %d 本の升" % (dp["n_above"], dp0["n_above"], len(dp["hist_counts"])))
    gate("欠陥画素: 仕込んだ数を数え直す(仕込む前は 0)", dp["n_above"] == 9 and dp0["n_above"] == 0)

    # ─────────────────────────────── 8. 規格の残りの式 ─────────────────────────────
    print("== 8. 規格 5 節の模擬カメラ(640 × 480、η 0.5、K 0.1、σ_d 30 e⁻、DSNU 白 1.5 DN + 振幅 1.5 DN の正弦 2 本、PRNU 白 0.5 %、"
          "照明が端へ 3 % 落ちる)で 8.1 節の高域フィルタと 8.6 節のスペクトログラム")
    ex = _standard_example_camera(np.random.default_rng(530))
    L8 = 16
    ex_dark = np.stack([ex(0.0) for _ in range(L8)])
    ex_bright = np.stack([ex(0.5 * (MAXDN - 29.4) / (0.1 * 0.5)) for _ in range(L8)])
    nu = {hp: SC.emva_spatial_nonuniformity(ex_dark, ex_bright, 0.1, highpass=hp) for hp in (None, "r4", "r3.1")}
    g2 = nu["r4"]["highpass"]["white_variance_gain"]
    hp_ref = SC.emva_highpass(np.zeros((40, 40)))
    Tk = lambda k: float(np.interp(k, hp_ref["transfer_k"], hp_ref["transfer"]))    # noqa: E731
    print("  PRNU: 高域フィルタなし %.3f %% / 8.1 節 %.3f %% / 付録 C.5(旧版) %.3f %%  —— 仕込み 0.5 %%(8.1 節の白い利得 %.4f をかけると %.3f %%)" % (
        100 * nu[None]["PRNU1288"], 100 * nu["r4"]["PRNU1288"], 100 * nu["r3.1"]["PRNU1288"], g2, 100 * 0.005 * math.sqrt(g2)))
    gate("8.1 節: 照明のむらは PRNU を +%.0f %% 膨らませ、高域フィルタで仕込み × √(白い利得) に 3 %% 以内で戻る" % (
        100 * (nu[None]["PRNU1288"] / 0.005 - 1)),
         nu[None]["PRNU1288"] > 1.4 * 0.005 and abs(nu["r4"]["PRNU1288"] / (0.005 * math.sqrt(g2)) - 1) < 0.03)
    dsnu_pred = math.sqrt(g2 * 1.5 ** 2 + 1.5 ** 2 / 2 * Tk(0.08) ** 2 + 1.5 ** 2 / 2 * Tk(0.4) ** 2) / 0.1
    print("  DSNU: フィルタなし %.2f e⁻(仕込み %.2f)/ 8.1 節 %.2f e⁻ —— 伝達関数からの予測 %.2f(波長 25 画素の正弦は %.0f %% に減る)" % (
        nu[None]["DSNU1288_e"], math.sqrt(1.5 ** 2 * 2) / 0.1, nu["r4"]["DSNU1288_e"], dsnu_pred, 100 * Tk(0.08)))
    gate("8.1 節: 高域フィルタの DSNU = 白い利得と伝達関数からの予測(2 %)", abs(nu["r4"]["DSNU1288_e"] / dsnu_pred - 1) < 0.02)
    avg_d = ex_dark.mean(axis=0)
    hp_d = SC.emva_highpass(avg_d)["image"]
    sh = SC.emva_spectrogram(avg_d, band=(0.035, 0.045))
    sv = SC.emva_spectrogram(avg_d, axis="vertical", band=(0.195, 0.205))
    shh = SC.emva_spectrogram(hp_d, band=(0.035, 0.045))
    svh = SC.emva_spectrogram(hp_d, axis="vertical", band=(0.195, 0.205))
    print("  式 72 の振幅(白い床を引く): 横 0.04 c/px %.3f DN・縦 0.2 c/px %.3f DN(仕込み 1.5)。8.6 節どおり高域フィルタの後では %.3f / %.3f"
          "(伝達関数の予測 %.3f / %.3f)" % (sh["amplitude_above_floor"], sv["amplitude_above_floor"], shh["amplitude_above_floor"],
                                           svh["amplitude_above_floor"], 1.5 * Tk(0.08), 1.5 * Tk(0.4)))
    print("  (式 72 そのまま = 帯の中の白い雑音も足した値: %.3f / %.3f)" % (sh["amplitude"], sv["amplitude"]))
    gate("8.6 節: 周期模様の振幅を式 72 で 5 % 以内に取り戻す(高域フィルタの後は伝達関数どおり 10 %)",
         abs(sh["amplitude_above_floor"] / 1.5 - 1) < 0.05 and abs(sv["amplitude_above_floor"] / 1.5 - 1) < 0.05
         and abs(shh["amplitude_above_floor"] / (1.5 * Tk(0.08)) - 1) < 0.10 and abs(svh["amplitude_above_floor"] / (1.5 * Tk(0.4)) - 1) < 0.10)
    old = SC.emva_highpass(np.random.default_rng(3).standard_normal((400, 400)), method="r3.1")
    v_old = float(old["image"].var())
    print("  付録 C.5(旧版の 5 × 5 の箱): 白い雑音の分散は %.4f 倍(Parseval 1 − 1/25 = 0.96)。本文の式 86 は (1 − 1/P²)² = 0.92 と書く" % v_old)
    gate("付録 C.5 の式 86 の 0.92 は実測と合わない(0.96 ± 0.01)", abs(v_old - 0.96) < 0.01 and abs(v_old - 0.92) > 0.03)

    print("== 9. 式 51(photon transfer の直線性、局所の傾きの相対偏差の平均 < 3 %)は画素数が要る —— 線形なセンサで測る")
    res = {}
    for (hh, ww), seeds in (((128, 160), range(6)), ((512, 640), range(2))):
        vals = []
        for sd_ in seeds:
            vals.append(_eq51_linear(hh, ww, 9000 + sd_))
        res[(hh, ww)] = vals
        print("  %d × %d: 式 51 = %s(3 %% 以上で「線形でない」と判定 %d / %d)" % (
            ww, hh, " / ".join("%.3f" % v for v in vals), sum(v >= 0.03 for v in vals), len(vals)))
    small, big = res[(128, 160)], res[(512, 640)]
    gate("式 51: 512 × 640 の線形なセンサは通り、128 × 160 では線形でも落ちることがある(2 枚の差の分散の揺れ √(2/NM))",
         all(v < 0.03 for v in big) and any(v >= 0.03 for v in small) and np.median(small) > 2 * np.median(big))
    # 区間の数は 0〜70 % に入った点の数から(式 47 は Q > P + 3 点を要る)。CI の reduced 予算は露光 16 段で
    # 0〜70 % に 9 点しか入らず、既定の 6 区間(係数 9)では当てはめが立たない(2026-10-13 に CI だけ赤)。
    n_used = int(ptc["used"].sum())
    n_int = max(1, min(6, n_used - 4))
    ok51 = SC.emva_ptc_linearity_check(mu[1:], var[1:], mu[0], var[0], mu_sat, n_intervals=n_int)
    print("  (1 節のセンサ 128 × 96 では式 51 = %.3f(%d 点・%d 区間)—— 同じ理由で数字は読まない)" % (
        ok51["mean_rel_dev"], ok51["n_points"], n_int))

    print("== 10. 式 3・4(光子数)・式 25(SNR の逆)・式 69(総合 SNR)")
    c0 = SC.emva_photon_exposure(1.0, 1.0, 1.0, 1.0)[0]
    inv1 = SC.emva_exposure_for_snr(1.0, ETA, SD, K)[0]
    tot = SC.emva_total_snr([1e9], ETA, SD, K, sn["DSNU1288_e"], sn["PRNU1288"])[0, 2]
    print("  式 4 の定数 %.4f(本文 50.34)、μ_p(SNR = 1) = %.4f = 式 26 の %.4f、総合 SNR の頭打ち %.1f = 1/PRNU %.1f" % (
        c0, inv1, th["mu_p_min"], tot, 1.0 / sn["PRNU1288"]))
    gate("式 4 の 50.34・式 25 の SNR = 1 が式 26・式 69 の頭打ち = 1/PRNU",
         round(c0, 2) == 50.34 and abs(inv1 / th["mu_p_min"] - 1) < 1e-12 and abs(tot * sn["PRNU1288"] - 1) < 1e-3)

    if figs.enabled():
        print("== 11. 図と動画")
        t_f = time.time()
        _figures(pairs, mp, mu, var, ptc, mu_sat, th, bnd, Ks, rows, bad_dr)
        _figures_r4(ex_bright, ex_dark, nu, sh, sv, shh, svh, hp_ref, res)
        print("  図と動画(%.1f s)" % (time.time() - t_f))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("所要 %.1f s" % (time.time() - T0))
    print("SUMMARY: %d / %d gates PASS" % (sum(OK), len(OK)))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


def _standard_example_camera(rng, H8=480, W8=640):
    """Linear 5 節の最後の段落に書かれた模擬カメラ(本文の図 5〜16 はこの模擬データ)。

    12 bit・640 × 480・η 0.5・暗の値 29.4 DN・K 0.1・σ_d 30 e⁻・DSNU は白 1.5 DN + 振幅 1.5 DN の正弦(横 0.04・縦 0.2 c/px)・
    PRNU 白 0.5 %・照明は端へ向かって約 3 % の 2 次の落ち。「わずかに線形でない特性」は本文に量が無いので入れない。
    """
    n, m = np.arange(W8), np.arange(H8)
    dsnu = 1.5 * rng.standard_normal((H8, W8)) + 1.5 * np.sin(2 * np.pi * 0.04 * n + 0.7)[None, :] \
        + 1.5 * np.sin(2 * np.pi * 0.2 * m + 0.2)[:, None]
    prnu = 1.0 + 0.005 * rng.standard_normal((H8, W8))
    yy, xx = np.mgrid[0:H8, 0:W8]
    r2 = ((xx - (W8 - 1) / 2) ** 2 + (yy - (H8 - 1) / 2) ** 2) / (((W8 - 1) / 2) ** 2 + ((H8 - 1) / 2) ** 2)
    illum = 1.0 - 0.03 * r2

    def shot8(mp):
        e = rng.poisson(0.5 * mp * prnu * illum)
        return np.clip(np.round(0.1 * (e + rng.normal(0.0, 30.0, (H8, W8))) + 29.4 + dsnu), 0, MAXDN)
    return shot8


def _eq51_linear(hh, ww, seed):
    """線形なセンサ(η 0.45・K 0.25・σ_d 6 e⁻)を 50 段で撮り、式 51 の値を返す。"""
    rng = np.random.default_rng(seed)
    prnu = 1.0 + 0.008 * rng.standard_normal((hh, ww))
    dsnu = 1.0 * rng.standard_normal((hh, ww))

    def s(mp):
        return np.clip(np.round(0.25 * (rng.poisson(0.45 * mp * prnu) + rng.normal(0.0, 6.0, (hh, ww))) + 64.0 + dsnu), 0, MAXDN)
    mp_ = np.linspace(0.0, (MAXDN - 64.0) / (0.25 * 0.45), 50)
    st = [SC.emva_pair_statistics(s(m), s(m)) for m in mp_]
    mu_ = np.array([x["mu"] for x in st])
    var_ = np.array([x["var_temporal"] for x in st])
    return SC.emva_ptc_linearity_check(mu_[1:], var_[1:], mu_[0], var_[0], float(mu_[int(np.argmax(var_))]))["mean_rel_dev"]


# ─────────────────────────────── 図 ─────────────────────────────
def _canvas(w, h, bg=(1.0, 1.0, 1.0)):
    img = np.empty((h, w, 3))
    img[:] = bg
    return img


def _dot(img, x, y, r, color):
    h, w = img.shape[:2]
    y0, y1, x0, x1 = max(0, int(y - r - 1)), min(h, int(y + r + 2)), max(0, int(x - r - 1)), min(w, int(x + r + 2))
    if y0 >= y1 or x0 >= x1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = (xx - x) ** 2 + (yy - y) ** 2 <= r * r
    img[yy[m], xx[m]] = color


def _hline(img, y, x0, x1, color, width=1):
    h, w = img.shape[:2]
    a, b = int(np.clip(min(x0, x1), 0, w)), int(np.clip(max(x0, x1), 0, w))
    c = int(np.clip(y, 0, h - 1))
    img[c:min(h, c + width), a:b] = color


def _vline(img, x, y0, y1, color, width=1):
    h, w = img.shape[:2]
    a, b = int(np.clip(min(y0, y1), 0, h)), int(np.clip(max(y0, y1), 0, h))
    c = int(np.clip(x, 0, w - 1))
    img[a:b, c:min(w, c + width)] = color


def _ptc_panel(w, h, mu, var, k_show, ptc, mu_dark, var_dark, mu_sat, xmax, ymax):
    """photon transfer の枠: x = μ_y − μ_y.dark、y = σ²_y − σ²_y.dark。点は k_show 個まで。"""
    img = _canvas(w, h)
    L_, R_, T_, B_ = 58, w - 24, 40, h - 64

    def px(x, y):
        return L_ + (R_ - L_) * x / xmax, B_ - (B_ - T_) * y / ymax

    _hline(img, B_, L_, R_, (0.2, 0.2, 0.2), 2)
    _vline(img, L_, T_, B_, (0.2, 0.2, 0.2), 2)
    x70, _ = px(0.7 * (mu_sat - mu_dark), 0)
    img[T_:B_, L_ + 2:int(x70)] = np.array([0.93, 0.97, 0.93])              # 当てはめに使う 0〜70 %
    for kk in range(k_show):
        x, y = px(mu[kk] - mu_dark, var[kk] - var_dark)
        used = 0 <= mu[kk] - mu_dark <= 0.7 * (mu_sat - mu_dark)
        _dot(img, x, y, 4, (0.1, 0.45, 0.2) if used else (0.75, 0.3, 0.2))
    if k_show >= len(mu):
        xs = np.linspace(0, 0.95 * xmax, 200)
        for x_ in xs:
            a, b = px(x_, ptc["offset"] + ptc["K"] * x_)
            _dot(img, a, b, 1.2, (0.15, 0.35, 0.9))
    for fx in (0.0, 0.5, 1.0):                                          # 目盛り(x = 平均の差 [DN]、y = 分散の差 [DN²])
        x_, _ = px(fx * xmax, 0)
        _vline(img, x_, B_, B_ + 5, (0.2, 0.2, 0.2), 2)
        img = np.asarray(AN.text_box(img, "%.0f" % (fx * xmax), (int(min(x_ - 10, w - 60)), B_ + 6), font_size=11), dtype=np.float64)
    for fy in (0.5, 1.0):
        _, y_ = px(0, fy * ymax)
        _hline(img, y_, L_ - 5, L_, (0.2, 0.2, 0.2), 2)
        img = np.asarray(AN.text_box(img, "%.0f" % (fy * ymax), (2, int(y_) - 10), font_size=11), dtype=np.float64)
    img = np.asarray(AN.text_box(img, "photon transfer: 分散 − 暗の分散 [DN²] vs 平均 − 暗の平均 [DN]", (6, 6), font_size=13), dtype=np.float64)
    img = np.asarray(AN.text_box(img, "緑 = 当てはめに使う 0〜70 %  赤 = 飽和の近く(分散が潰れる)", (6, h - 36), font_size=12), dtype=np.float64)
    if k_show >= len(mu):
        img = np.asarray(AN.text_box(img, "傾き K = %.4f DN/e⁻(仕込み %.2f)" % (ptc["K"], K), (L_ + 10, T_ + 6), font_size=14), dtype=np.float64)
    return img


def _figures(pairs, mp, mu, var, ptc, mu_sat, th, bnd, Ks, rows, bad_dr):
    # (1) 動画: 露光を上げながら撮った画像(左)と、photon transfer の点が 1 つずつ増えていく図(右)
    xmax = 1.05 * float(mu.max() - mu[0])
    ymax = 1.10 * float((var - var[0]).max())
    frames = []
    n = len(mu)
    for kk in range(1, n + 1):
        a = pairs[kk - 1][0]
        left = np.repeat((a / MAXDN)[:, :, None], 3, axis=2)
        left = np.kron(left, np.ones((3, 3, 1)))[:, :, :3]                    # 128×96 → 384×288
        crop = a[40:56, 56:72]
        cz = (crop - crop.min()) / max(1.0, float(np.ptp(crop)))
        cz = np.kron(np.repeat(cz[:, :, None], 3, axis=2), np.ones((6, 6, 1)))  # 16×16 → 96×96(明るさを伸ばして粒を見せる)
        panel = _canvas(400, 440)
        panel[40:40 + left.shape[0], 8:8 + left.shape[1]] = left
        panel[340:436, 8:104] = cz
        panel = np.asarray(AN.text_box(panel, "露光 μ_p = %.0f 光子/画素  平均 %.0f DN" % (mp[kk - 1], mu[kk - 1]), (6, 6), font_size=13), dtype=np.float64)
        panel = np.asarray(AN.text_box(panel, "← 16×16 を拡大(粒 = 光子雑音と暗雑音)", (110, 370), font_size=12), dtype=np.float64)
        right = _ptc_panel(560, 440, mu, var, kk, ptc, mu[0], var[0], mu_sat, xmax, ymax)
        f = np.concatenate([panel, right], axis=1)
        frames.append((np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8))
    frames += [frames[-1]] * 12
    figs.save_video("photon_transfer", frames, fps=6.0, gif_every=1, gif_width=None,
                    caption="露光を上げながら同じ露光で 2 枚ずつ撮り、平均と時間分散(2 枚の差から、式 18)を 1 点ずつ置く。直線の傾きがシステムゲイン "
                            "K = %.4f DN/e⁻(仕込み %.2f)。飽和の近くでは分散が潰れるので、規格は 0〜70 %% の点だけで当てる。" % (ptc["K"], K))
    # (2) SNR 曲線(log10 の軸)
    grid = np.logspace(-0.5, math.log10(1.2 * mp[-1]), 200)
    c = SC.emva_snr_curve(grid, ETA, SD, K)
    snr_meas = (mu[1:] - mu[0]) / np.sqrt(var[1:])
    keep = snr_meas > 0
    figs.save_plot("snr_curve", [("式 21(仕込んだ η・σ_d・K)", np.log10(c[:, 0]), np.log10(c[:, 1])),
                                 ("理想センサ √μ_p(式 23)", np.log10(c[:, 0]), np.log10(c[:, 2])),
                                 ("合成画像から測った SNR", np.log10(mp[1:][keep]), np.log10(snr_meas[keep]))],
                   kinds=["line", "line", "scatter"], xlabel="log10 μ_p [光子/画素]", ylabel="log10 SNR", title="SNR 曲線",
                   caption="SNR は暗い側で傾き 1(暗雑音が支配)、明るい側で傾き 1/2(光子雑音が支配)。SNR = 1 になる露光が絶対感度しきい値 "
                           "μ_p.min = %.1f 光子。量子化雑音の分だけ μ_e.min = %.2f e⁻ は暗雑音 %.1f e⁻ より大きい。" % (th["mu_p_min"], th["mu_e_min"], SD))
    # (3) 規格の適用範囲
    vf = np.array([b[0] for b in bnd["flat"]])
    vp = np.array([b[0] for b in bnd["pattern"]])
    ef = 100 * np.array([b[1] for b in bnd["flat"]])
    ep = 100 * np.array([b[1] for b in bnd["pattern"]])
    mf, mpat = vf > 0, vp > 0                        # 分散がちょうど 0(K が小さすぎて全画素が同じ値)の点は対数の軸に載らない
    figs.save_plot("validity_boundary", [("平らなセンサ", np.log10(vf[mf]), ef[mf]),
                                         ("DSNU の模様あり", np.log10(vp[mpat]), ep[mpat]),
                                         ("規格の下限 0.24 DN²", [math.log10(0.24)] * 2, [0.0, 100.0])],
                   kinds=["line", "line", "line"], xlabel="log10 σ²_y.dark [DN²]", ylabel="σ_d の推定誤差 [%]", title="測れなくなる境界",
                   caption="暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。平らなセンサではそこから下で推定が崩れる。"
                           "DSNU の模様があると画素ごとのずれが量子化のディザになり、境界の外でも当たる —— 規格の境界は保守側。"
                           "(分散がちょうど 0 になった K = %s は対数の軸に載らないので省いた)" % ", ".join("%.2f" % k for k in Ks[~(mf & mpat)]))
    # (4) 公表値: DR の検算
    pub = np.array([r[3] for r in rows], float)
    calc = np.array([r[4] for r in rows], float)
    ok = np.array([r[0] not in bad_dr for r in rows])
    figs.save_plot("datasheet_dynamic_range", [("台帳の型番", pub[ok], calc[ok]), ("食い違う型番(%s)" % ", ".join(bad_dr), pub[~ok], calc[~ok]),
                                               ("一致の線", [float(min(pub.min(), calc.min())) - 2, float(max(pub.max(), calc.max())) + 2],
                                                [float(min(pub.min(), calc.min())) - 2, float(max(pub.max(), calc.max())) + 2])],
                   kinds=["scatter", "scatter", "line"], xlabel="公表の DR [dB]", ylabel="式 28 で検算した DR [dB]", title="データシートを検算する",
                   caption="メーカーが公表した EMVA 1288 データ %d 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。%d 型番は 3 dB 以内"
                           "(暗雑音が整数に丸めてあるぶん)、%s だけが外れる —— 暗雑音か DR の欄のどちらかが別条件の値と見られる。" % (
                               len(rows), int(ok.sum()), ", ".join(bad_dr)))



def _figures_r4(ex_bright, ex_dark, nu, sh, sv, shh, svh, hp_ref, res):
    avg_b = ex_bright.mean(axis=0) - ex_dark.mean(axis=0)
    hp_b = SC.emva_highpass(avg_b)["image"]
    figs.save_grid("highpass_prnu", [avg_b, hp_b], captions=["PRNU 画像 = 明るい平均画像 − 暗い平均画像(照明が端へ 3 % 落ちる)",
                                                            "8.1 節の高域フィルタの後(端 9 画素を落とす)"],
                   title="照明のむらを除く(8.1 節)", ncols=2,
                   caption="規格の模擬カメラ。高域フィルタなしの PRNU は %.3f %%(仕込み 0.5 %%)、フィルタの後は %.3f %%。" % (
                       100 * nu[None]["PRNU1288"], 100 * nu["r4"]["PRNU1288"]))
    figs.save_plot("spectrogram", [("暗画像 横(式 71)", sh["freq"][1:], np.sqrt(sh["power"][1:])),
                                   ("暗画像 縦", sv["freq"][1:], np.sqrt(sv["power"][1:])),
                                   ("高域フィルタの後 横", shh["freq"][1:], np.sqrt(shh["power"][1:]))],
                   kinds=["line", "line", "line"], styles=[None, None, "dashed"], xlabel="空間周波数 [cycles/pixel]",
                   ylabel="√P [DN]", title="スペクトログラム(8.6 節)",
                   caption="白い DSNU は平らな床(高さ = 標準偏差 1.5 DN)、正弦は鋭い山(横 0.04・縦 0.2 c/px)。式 72 で山の帯を足すと"
                           "振幅 %.2f / %.2f DN(仕込み 1.5)。高域フィルタの後は波長 25 画素の山が伝達関数どおりに低くなる。"
                           "周波数 0 の升(行・列の平均 = もう一方の向きの模様が入る)は描いていない。" % (
                               sh["amplitude_above_floor"], sv["amplitude_above_floor"]))
    figs.save_plot("highpass_transfer", [("8.1 節(Release 4.0)", hp_ref["transfer_k"], hp_ref["transfer"]),
                                         ("付録 C.5(Release 3.1、5 × 5 の箱)", SC.emva_highpass(np.zeros((40, 40)), method="r3.1")["transfer_k"],
                                          SC.emva_highpass(np.zeros((40, 40)), method="r3.1")["transfer"])],
                   kinds=["line", "line"], xlabel="波数(ナイキストで 1)", ylabel="伝達関数", title="高域フィルタの伝達関数",
                   caption="Release 4.0 のフィルタは高域でほぼ 1(付録 E.3)。旧版の 5 × 5 の箱は 0.80〜1.25 で揺れる。")
    s128, s512 = res[(128, 160)], res[(512, 640)]
    figs.save_plot("eq51_pixels", [("128 × 160", [128 * 160] * len(s128), [100 * v for v in s128]),
                                   ("512 × 640", [512 * 640] * len(s512), [100 * v for v in s512]),
                                   ("規格の上限 3 %", [1e4, 4e5], [3.0, 3.0])],
                   kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"], xlabel="画素数", ylabel="式 51 [%]",
                   title="式 51 は画素数が要る",
                   caption="線形なセンサを乱数を変えて撮り、式 51(局所の傾きの相対偏差の平均)を出す。小さい画像では 2 枚の差の分散の揺れが"
                           "局所の傾きを揺らし、線形なのに 3 % を越えることがある。")

if __name__ == "__main__":
    sys.exit(main())
