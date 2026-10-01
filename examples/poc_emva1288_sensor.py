# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: カメラを買わずにカメラを測る —— EMVA 1288(ISO 24942)の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す。

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

正直に書くこと: 合成センサ(実機の画像ではない)。高域フィルタ(8.1 節、照明のむら除去)はかけていない —— 照明は一様に作った。
直線性の B-スプライン検査(式 51)は入れていない。公表値の台帳は整数に丸めた値で、K が公表されないので DR の検算は量子化雑音を 0 とみなす。

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
    rows, bad_dr = [], []
    for model, v in optscene._SENSOR_CATALOG.items():
        qe_, sd_, sat, dr_db, snr_db = v[6] / 100.0, v[7], v[8] * 1e3, v[9], v[10]
        snr_calc = 20.0 * math.log10(math.sqrt(sat))
        t_ = SC.emva_sensitivity_threshold(qe_, sd_, 1.0, sigma_q2=0.0)
        dr_calc = SC.emva_dynamic_range(sat / qe_, t_["mu_p_min"])["dB"]
        rows.append((model, snr_db, snr_calc, dr_db, dr_calc))
        if abs(dr_calc - dr_db) > 3.0:
            bad_dr.append(model)
    d_snr = [abs(r[2] - r[1]) for r in rows]
    d_dr = [r[4] - r[3] for r in rows]
    print("  最大 SNR: 全 %d 型番で公表値との差 最大 %.2f dB(丸めの幅 0.5 dB 以内)" % (len(rows), max(d_snr)))
    print("  DR: 差 %.1f〜%+.1f dB(中央値 %+.2f)、3 dB を越えるのは %s" % (min(d_dr), max(d_dr), float(np.median(d_dr)), bad_dr))
    for r in rows:
        if r[0] in bad_dr:
            print("    %s: 飽和 %.1f ke⁻・暗雑音 %d e⁻ からは DR %.1f dB、台帳は %d dB —— 暗雑音か DR の欄が別条件の値と見られる(未確認、台帳は直さない)" % (
                r[0], optscene._SENSOR_CATALOG[r[0]][8], optscene._SENSOR_CATALOG[r[0]][7], r[4], r[3]))
    gate("公表値: 最大 SNR は全型番 0.5 dB 以内、DR は 1 型番(IMX287)を除き 3 dB 以内", max(d_snr) <= 0.5 and bad_dr == ["IMX287"])

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

    if figs.enabled():
        print("== 8. 図と動画")
        t_f = time.time()
        _figures(pairs, mp, mu, var, ptc, mu_sat, th, bnd, Ks, rows, bad_dr)
        print("  図と動画(%.1f s)" % (time.time() - t_f))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("所要 %.1f s" % (time.time() - T0))
    print("SUMMARY: %d / %d gates PASS" % (sum(OK), len(OK)))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


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


if __name__ == "__main__":
    sys.exit(main())
