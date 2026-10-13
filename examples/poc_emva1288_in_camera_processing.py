# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: カメラの中の前処理は、データシートの数をもっともらしく嘘にする —— どの数がどれだけ動き、何がそれを見破るか。

    py -3.11 examples/poc_emva1288_in_camera_processing.py

カメラのデータシートの量子効率 η・システムゲイン K・暗雑音・飽和容量・最大 SNR・ダイナミックレンジ・DSNU・PRNU は
EMVA 1288 Release 4.0 Linear の手順で測った数です。その手順は「出力が光子数に比例し、時間雑音が画素どうし・画像どうしで
独立」というカメラを前提にしています(Linear 1.2 節。本文は「前処理がこの条件を壊すなら Release 4 Linear は使えない。
典型は debayer・雑音除去・輪郭強調」と書く)。カメラの中で雑音除去や圧伸をかけると、手順そのものは何事もなく走り、
**それらしい数**が出ます。

この PoC は、値を仕込んだ**同じ合成センサ**(η 0.45・K 0.25 DN/e⁻・暗雑音 6 e⁻・12 bit、列と画素の DSNU・PRNU、
熱画素 30 個)に、カメラの中の前処理を 1 つずつかけて規格の手順で測り直し、**仕込んだ真値に対して**数がどれだけ動くかを
出します。前処理は 6 つ:

1. デジタルゲイン ×2(ADC の後で 2 倍)
2. 雑音除去(3 × 3 の平均を 3 割混ぜる)
3. 輪郭強調(アンシャープマスク、強さ 0.5)
4. 時間方向の雑音除去(1 次の再帰 y_t = 0.8 x_t + 0.2 y_{t−1})
5. 欠陥画素の補正(工場の地図にある熱画素を 8 近傍の中央値で置き換える)
6. 対数の圧伸(12 bit を 10 bit の対数に詰める)

線形な 1〜4 は閉形式で予測でき(``emva_filter_distortion``: 平均は Σw 倍、白い時間雑音は Σw² 倍、2 枚の差は再帰で
α²/(2 − α) 倍)、予測と実測を突き合わせます。見破る側は 3 つ: 規格の式 51(photon transfer の直線性、B-スプラインの局所の
傾き)、「η ≤ 1」という物理、そして前提 3 を直接確かめる検査(``emva_noise_whiteness``: 2 枚の差の隣の画素との相関・
1 枚おきの画像との相関)—— ★最後のものは**規格が定義した数ではありません**(規格は前提を書くが確かめ方を決めていない)。
最後に General の手順(特性曲線の傾きで入力へ戻す)で同じカメラを測り、圧伸の嘘が消えることと、**空間・時間の雑音除去の
嘘は General でも消えない**ことを見ます。

★正直に書いておくこと:
  * 合成センサです(実機の画像ではない)。前処理はどれも単純化した代表(実機の中身は分からない)。空間フィルタは周期の境界
    (端の画素の扱いを考えない)で、照明は一様に作ったので DSNU・PRNU は高域フィルタ(8.1 節)無しで測った。
  * 「前提 3 の検査」の z の閾値 5 はこの PoC の選択。白い雑音で 150 回試した z の標準偏差は約 1(``tests/test_sensorchar_r4.py``)。
  * 式 51 は画素数が要る(2 枚の差の分散の揺れ √(2/NM) が局所の傾きの揺れになる)。乱数 12 通りの実測で、線形なセンサが
    3 % を越えて落ちたのは 256 × 320 で 1 回、512 × 640 で 0 回。この PoC は 512 × 640 で撮る(最初に 256 × 320 で書いたとき、
    前処理なしのカメラが 3.6 % で落ちた —— 乱数を選び直すのでなく画素数を増やした)。
  * 8.8 節の欠陥画素は高域フィルタ(8.1 節)をかけた画像で数える。この実装は平滑化が定義されない端 9 画素を捨てるので
    (4.0 の本文は端の扱いを書いていない)、端にある熱画素は数えられない —— 真値もフィルタの内側の数で比べる。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import sensorchar as SC  # noqa: E402
import sensorgeneral as SG  # noqa: E402

ETA, K, SD, OFF, BITS = 0.45, 0.25, 6.0, 64.0, 12
MAXDN = (1 << BITS) - 1
H, W = 512, 640             # 式 51 は画素数が要る(下の「正直に」)
L = 16                       # 不均一の積み重ね(付録 C.3 の 4: インライン検査なら 16 枚でよい)
N_HOT, HOT_DN = 30, 60.0
DEFECT_THR = 20.0            # 欠陥画素の「止め帯」[出力の DN](8.8 節: 用途が決める値)
C_LOG = 1000.0
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print("  [%s] %s %s" % ("OK" if cond else "NG", label, detail))


# ─────────────────────────────── センサ(真値)と前処理 ─────────────────────────────
def make_sensor():
    rng = np.random.default_rng(1288)
    col = 0.6 * rng.standard_normal(W)[None, :]
    pix = 1.0 * rng.standard_normal((H, W))
    hot = rng.choice(H * W, size=N_HOT, replace=False)
    pix_hot = pix.copy()
    pix_hot.flat[hot] += HOT_DN
    prnu_pix = 0.008 * rng.standard_normal((H, W))
    prnu_col = 0.003 * rng.standard_normal(W)[None, :]
    return {"col": col, "pix": pix_hot, "dsnu": col + pix_hot, "hot": hot,
            "prnu": 1.0 + prnu_pix + prnu_col, "prnu_pix": prnu_pix, "prnu_col": prnu_col}


def box3_wrap(y):
    """周期の境界で 3 × 3 の箱(分けて 2 回の 1-D の和)。"""
    r = y + np.roll(y, 1, 0) + np.roll(y, -1, 0)
    return (r + np.roll(r, 1, 1) + np.roll(r, -1, 1)) / 9.0


def blend_with_box(a, b):
    """y' = a·y + b·(3 × 3 の箱)。カーネルは a·δ + b·(1/9)。雑音除去(a = 0.7, b = 0.3)と輪郭強調(1.5, −0.5)。"""
    return lambda y: np.clip(np.round(a * y + b * box3_wrap(y)), 0, MAXDN)


W_GAIN = np.array([[2.0]])
W_DENOISE = np.full((3, 3), 0.3 / 9.0)
W_DENOISE[1, 1] += 0.7
W_SHARPEN = -0.5 * np.full((3, 3), 1.0 / 9.0)
W_SHARPEN[1, 1] += 1.5
ALPHA = 0.8


def log_comp(y):
    return np.round(1023.0 * np.log1p(y / C_LOG) / np.log1p(MAXDN / C_LOG))


def log_slope(y):
    return 1023.0 / np.log1p(MAXDN / C_LOG) / (C_LOG + y)


class Camera:
    """センサ + 前処理。``frames(mu_p, n)`` は**続けて撮った** n 枚(時間フィルタはその間で状態を持つ)。"""

    def __init__(self, name, label, sensor, rng, proc=None, temporal=None, out_max=MAXDN, kernel=None):
        self.name, self.label, self.s, self.rng = name, label, sensor, rng
        self.proc, self.temporal, self.out_max, self.kernel = proc, temporal, out_max, kernel

    def raw(self, mu_p):
        e = self.rng.poisson(ETA * mu_p * self.s["prnu"])
        return np.clip(np.round(K * (e + self.rng.normal(0.0, SD, (H, W))) + OFF + self.s["dsnu"]), 0, MAXDN)

    def frames(self, mu_p, n, burn=4):
        if self.temporal is not None:
            st = self.raw(mu_p)
            for _ in range(burn):           # 立ち上がりを捨てる: 初めの画像の分散の重みは (1 − α)^(2·burn) = 2.6e-6
                st = self.temporal * self.raw(mu_p) + (1 - self.temporal) * st
            out = []
            for _ in range(n):
                st = self.temporal * self.raw(mu_p) + (1 - self.temporal) * st
                out.append(np.clip(np.round(st), 0, MAXDN))
            return out
        return [self.raw(mu_p) if self.proc is None else self.proc(self.raw(mu_p)) for _ in range(n)]


def dpc(sensor):
    hot = sensor["hot"]
    rr, cc = np.unravel_index(hot, (H, W))
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def f(y):
        z = y.copy()
        vals = np.stack([y[(rr + a) % H, (cc + b) % W] for a, b in nb])
        z[rr, cc] = np.round(np.median(vals, axis=0))
        return z
    return f


def find_saturation(cam):
    """6.6 節: 0.1〜0.2 % の画素が最大値になる露光(ここでは 0.15 % に二分法で合わせる)。"""
    lo, hi = 1000.0, 80000.0
    for _ in range(14):                                                 # 幅 79000/2^14 ≈ 5 光子まで
        m = 0.5 * (lo + hi)
        frac = float(np.mean([(f >= cam.out_max).mean() for f in cam.frames(m, 1, burn=2)]))
        if frac > 0.0015:
            hi = m
        else:
            lo = m
    return 0.5 * (lo + hi)


# ─────────────────────────────── 規格の手順で測る ─────────────────────────────
def measure(cam):
    psat = find_saturation(cam)
    mp = np.unique(np.concatenate([np.linspace(0.0, psat, 50), np.geomspace(3.0, 400.0, 14)]))
    st = []
    pairs_mid = None
    for m in mp:
        f = cam.frames(m, 3 if abs(m - 0.3 * psat) == min(abs(mp - 0.3 * psat)) else 2)
        if len(f) == 3:
            pairs_mid = f
        st.append(SC.emva_pair_statistics(f[0], f[1]))                # 式 16・18
    mu = np.array([s["mu"] for s in st])
    var = np.array([s["var_temporal"] for s in st])
    i_sat = int(np.argmin(np.abs(mp - psat)))
    mu_sat = float(mu[i_sat])
    out = {"psat": psat, "mp": mp, "mu": mu, "var": var, "mu_sat": mu_sat}
    ptc = SC.emva_photon_transfer(mu[1:], var[1:], mu[0], var[0], mu_sat)     # 式 50・53
    qe = SC.emva_quantum_efficiency(mp[1:], mu[1:], mu[0], mu_sat, ptc["K"])   # 式 49・52
    lc = SC.emva_ptc_linearity_check(mu[1:], var[1:], mu[0], var[0], mu_sat)  # 式 51
    le = SC.emva_linearity_error(mp, mu, mu[0], mu_sat)                       # 式 58〜63
    out.update(K=ptc["K"], eta=qe["eta"], sigma_d=ptc["sigma_d"], eq51=lc["mean_rel_dev"], eq51_ok=lc["linear_model_ok"],
               LE=le["LE_percent"], ptc=ptc)
    out["mu_e_sat"] = out["eta"] * psat                                 # 式 24
    out["snr_max_dB"] = 20.0 * math.log10(math.sqrt(out["mu_e_sat"]))  # 式 55
    try:
        th = SC.emva_sensitivity_threshold(out["eta"], out["sigma_d"], out["K"])   # 式 26(η ≤ 1 でなければ拒む)
        out["mu_p_min"] = th["mu_p_min"]
        out["DR_dB"] = SC.emva_dynamic_range(psat, th["mu_p_min"])["dB"]   # 式 28
        out["refused"] = None
    except ValueError as e:
        out["mu_p_min"] = out["DR_dB"] = None
        out["refused"] = str(e).split(":")[0] + ": " + ("η > 1" if "eta" in str(e) else str(e)[:60])
    dark = np.stack(cam.frames(0.0, L))
    bright = np.stack(cam.frames(0.5 * psat, L))
    sn = SC.emva_spatial_nonuniformity(dark, bright, out["K"])          # 式 66・67(照明は一様 —— 高域フィルタなし)
    out.update(DSNU=sn["DSNU1288_e"], PRNU=sn["PRNU1288"], dark_avg=dark.mean(axis=0))
    hp = SC.emva_highpass(dark.mean(axis=0))                            # 8.8 節は高域フィルタをかけた平均画像で
    out["defects"] = SC.emva_defect_pixels(hp["image"], L, DEFECT_THR)["n_above"]
    out["hp_border"] = hp["border"]
    out["white"] = SC.emva_noise_whiteness(*pairs_mid)                  # 前提 3(この族の検査)
    out["mid_frames"] = pairs_mid
    try:
        out["general"] = SG.emva_general_sensitivity(mp[1:], mu[1:], var[1:], mu[0], var[0], psat)
    except ValueError as e:
        out["general"] = None
        out["general_err"] = str(e)
    return out


def truth(sensor, raw_psat):
    th = SC.emva_sensitivity_threshold(ETA, SD, K)
    return {"eta": ETA, "K": K, "sigma_d": SD, "mu_e_sat": ETA * raw_psat,
            "snr_max_dB": 20 * math.log10(math.sqrt(ETA * raw_psat)), "mu_p_min": th["mu_p_min"],
            "DR_dB": 20 * math.log10(raw_psat / th["mu_p_min"]), "DSNU": float(sensor["dsnu"].std()) / K,
            "PRNU": float(sensor["prnu"].std() / sensor["prnu"].mean()), "defects": hot_inside(sensor, 9)}


def hot_inside(sensor, border):
    """高域フィルタ(8.1 節)の内側に入る熱画素の数(端 *border* 画素は平滑化が定義されないので捨てる)。"""
    rr, cc = np.unravel_index(sensor["hot"], (H, W))
    return int(((rr >= border) & (rr < H - border) & (cc >= border) & (cc < W - border)).sum())


def predict_linear(sensor, w, alpha, psat, requant=True):
    """閉形式の予測(``emva_filter_distortion``)。σ_d は量子化を含めた厳密な式(生の 1/12 もフィルタを通る)。"""
    fd = SC.emva_filter_distortion(w, temporal_alpha=alpha)
    G, W2, St = fd["G"], fd["sum_w2"], fd["S_temporal"]
    Kp, etap = K * fd["K_factor"], ETA * fd["eta_factor"]
    q_re = SC.SIGMA_Q2 if requant else 0.0
    sdp = math.sqrt(W2 * St * (K ** 2 * SD ** 2 + SC.SIGMA_Q2) + q_re - SC.SIGMA_Q2) / Kp
    pg = fd["pattern_gain"]
    v_pix, v_col = float(sensor["pix"].var()), float(sensor["col"].var())
    dsnu_dn = G * math.sqrt(pg["pixel"] * v_pix + pg["col"] * v_col)
    prnu = math.sqrt(pg["pixel"] * float(sensor["prnu_pix"].var()) + pg["col"] * float(sensor["prnu_col"].var())) / float(sensor["prnu"].mean())
    th = SC.emva_sensitivity_threshold(min(etap, 1.0), sdp, Kp)
    return {"fd": fd, "K": Kp, "eta": etap, "sigma_d": sdp, "DSNU": dsnu_dn / Kp, "PRNU": prnu,
            "snr_max_dB": 20 * math.log10(math.sqrt(etap * psat)), "mu_p_min": th["mu_p_min"],
            "DR_dB": 20 * math.log10(psat / th["mu_p_min"])}


def rel(a, b):
    return a / b - 1.0


def main():
    t0 = time.time()
    c0 = time.process_time()
    sensor = make_sensor()
    rng = np.random.default_rng(2026)
    cams = [
        Camera("raw", "前処理なし", sensor, rng),
        Camera("gain2", "デジタルゲイン ×2", sensor, rng, proc=lambda y: np.clip(2.0 * y, 0, MAXDN), kernel=W_GAIN),
        Camera("denoise", "雑音除去(3×3 を 3 割)", sensor, rng, proc=blend_with_box(0.7, 0.3), kernel=W_DENOISE),
        Camera("sharpen", "輪郭強調(強さ 0.5)", sensor, rng, proc=blend_with_box(1.5, -0.5), kernel=W_SHARPEN),
        Camera("tnr", "時間の雑音除去 α = 0.8", sensor, rng, temporal=ALPHA, kernel=np.array([[1.0]])),
        Camera("dpc", "欠陥画素の補正(地図)", sensor, rng, proc=dpc(sensor)),
        Camera("log", "対数の圧伸 → 10 bit", sensor, rng, proc=lambda y: log_comp(y), out_max=1023),
    ]
    print("仕込んだセンサ: η %.2f・K %.2f DN/e⁻・σ_d %.1f e⁻・%d bit・%d × %d 画素、DSNU(列 + 画素 + 熱画素 %d 個 +%.0f DN)・PRNU(列 + 画素)"
          % (ETA, K, SD, BITS, W, H, N_HOT, HOT_DN))
    R = {}
    for cam in cams:
        t_c = time.time()
        R[cam.name] = measure(cam)
        print("  測った: %-22s (%.1f s)" % (cam.label, time.time() - t_c))
    T = truth(sensor, R["raw"]["psat"])

    # ── 表: どの数がどれだけ動くか(真値に対して) ──
    keys = [("eta", "η", "%.3f"), ("K", "K", "%.4f"), ("sigma_d", "σ_d e⁻", "%.2f"), ("mu_e_sat", "μ_e.sat", "%.0f"),
            ("snr_max_dB", "SNRmax dB", "%.1f"), ("DR_dB", "DR dB", "%.1f"), ("DSNU", "DSNU e⁻", "%.2f"),
            ("PRNU", "PRNU", "%.4f"), ("defects", "欠陥", "%d")]
    print("\n== データシートの数(規格 Linear の手順のまま)と、仕込んだ真値に対するずれ")
    print("  %-22s " % "前処理" + " ".join("%14s" % h for _, h, _ in keys))
    print("  %-22s " % "真値" + " ".join("%14s" % (f % T[k]) for k, _, f in keys))
    rows = []
    for cam in cams:
        r = R[cam.name]
        cells = []
        for k, _, f in keys:
            v = r.get(k)
            if v is None:
                cells.append("拒否")
            elif k in ("snr_max_dB", "DR_dB"):
                cells.append((f % v) + "(%+.1f)" % (v - T[k]))
            elif k == "defects":
                cells.append("%d" % v)
            else:
                cells.append((f % v) + "(%+.0f%%)" % (100 * rel(v, T[k])))
        rows.append([cam.label] + cells)
        print("  %-22s " % cam.label + " ".join("%14s" % c for c in cells))
    print("\n== 見破る側: 式 51(photon transfer の直線性)・η ≤ 1・前提 3 の検査(画素間の相関 ρ_h・1 枚おきの相関 ρ_t)・LE")
    for cam in cams:
        r = R[cam.name]
        wv = r["white"]
        print("  %-22s 式51 %6.3f(%s) η %s  ρ_h %+.3f(z %+6.1f) ρ_t %+.3f(z %+6.1f) → %s  LE %.3f %%" % (
            cam.label, r["eq51"], "通る" if r["eq51_ok"] else "落ちる", "≤ 1" if r["eta"] <= 1 else "> 1 !",
            wv["rho_h"], wv["z_h"], wv["rho_t"], wv["z_t"], "白い" if wv["white"] else "白くない", r["LE"]))

    # ─────────────────────────────── 門 ─────────────────────────────
    print("\n== 1. 前処理なし: 規格の手順で仕込んだ値に戻る")
    r = R["raw"]
    check(abs(rel(r["eta"], ETA)) < 0.03 and abs(rel(r["K"], K)) < 0.02 and abs(rel(r["sigma_d"], SD)) < 0.03,
          "η・K・σ_d が 3 %・2 %・3 % 以内", "(%+.2f / %+.2f / %+.2f %%)" % (100 * rel(r["eta"], ETA), 100 * rel(r["K"], K), 100 * rel(r["sigma_d"], SD)))
    check(abs(rel(r["DSNU"], T["DSNU"])) < 0.05 and abs(rel(r["PRNU"], T["PRNU"])) < 0.05 and r["defects"] == T["defects"],
          "DSNU・PRNU が 5 %% 以内、欠陥画素を数え直す(熱画素 %d 個のうち高域フィルタの内側の %d 個)" % (N_HOT, T["defects"]),
          "(%+.1f / %+.1f %%、%d 個)" % (100 * rel(r["DSNU"], T["DSNU"]), 100 * rel(r["PRNU"], T["PRNU"]), r["defects"]))
    check(r["eq51_ok"] and r["white"]["white"], "式 51 を通り、前提 3 の検査も白い", "(式 51 = %.3f)" % r["eq51"])
    check(abs(rel(r["mu_p_min"], T["mu_p_min"])) < 0.03 and abs(r["DR_dB"] - T["DR_dB"]) < 0.3,
          "絶対感度しきい値(式 26)3 %・DR(式 28)0.3 dB 以内", "(μ_p.min %.2f、真 %.2f)" % (r["mu_p_min"], T["mu_p_min"]))
    check(T["defects"] < N_HOT, "★高域フィルタ(8.1 節)が捨てる端 %d 画素に熱画素が %d 個あり、8.8 節の数え方では見えない" % (
        R["raw"]["hp_border"], N_HOT - T["defects"]))

    print("== 2. 線形な前処理(ゲイン・雑音除去・輪郭強調・時間の雑音除去)は閉形式どおりに数を動かす")
    pred = {}
    for nm, w, a, rq in (("gain2", W_GAIN, 1.0, False), ("denoise", W_DENOISE, 1.0, True),
                         ("sharpen", W_SHARPEN, 1.0, True), ("tnr", np.array([[1.0]]), ALPHA, True)):
        pred[nm] = predict_linear(sensor, w, a, R[nm]["psat"], requant=rq)
        p, m = pred[nm], R[nm]
        errs = {k: rel(m[k], p[k]) for k in ("K", "eta", "sigma_d")}
        print("  %-8s S = %.4f: K %.4f(予測 %.4f)η %.3f(予測 %.3f)σ_d %.2f(予測 %.2f)DSNU %.2f(予測 %.2f)PRNU %.4f(予測 %.4f)"
              % (nm, p["fd"]["S"], m["K"], p["K"], m["eta"], p["eta"], m["sigma_d"], p["sigma_d"], m["DSNU"], p["DSNU"], m["PRNU"], p["PRNU"]))
        check(max(abs(v) for v in errs.values()) < 0.03, "%s: K・η・σ_d が閉形式の予測と 3 %% 以内" % nm,
              "(%s)" % " / ".join("%s %+.2f %%" % (k, 100 * v) for k, v in errs.items()))
        if nm != "tnr":
            check(abs(rel(m["DSNU"], p["DSNU"])) < 0.04 and abs(rel(m["PRNU"], p["PRNU"])) < 0.04,
                  "%s: DSNU・PRNU が成分ごとの利得(画素・列)の予測と 4 %% 以内" % nm,
                  "(%+.1f / %+.1f %%)" % (100 * rel(m["DSNU"], p["DSNU"]), 100 * rel(m["PRNU"], p["PRNU"])))
    sat_ratio = R["gain2"]["psat"] / R["raw"]["psat"]
    sat_pred = (MAXDN / 2.0 - OFF) / (MAXDN - OFF)
    check(abs(R["gain2"]["eta"] / ETA - 1) < 0.02 and abs(sat_ratio / sat_pred - 1) < 0.02,
          "ゲイン ×2: η は動かず、飽和の露光が (2^k/2 − 暗)/(2^k − 暗) 倍になる", "(%.3f、予測 %.3f)" % (sat_ratio, sat_pred))
    dn = R["denoise"]
    check(dn["eta"] > 1.5 * ETA and dn["eta"] <= 1.0 and dn["eq51_ok"],
          "雑音除去: η が %.0f %% 増えてもまだ 1 以下(もっともらしい)、式 51 も通る —— 規格の検査は見逃す" % (100 * rel(dn["eta"], ETA)),
          "(η %.3f、式 51 %.3f)" % (dn["eta"], dn["eq51"]))
    check(not dn["white"]["white"] and not R["sharpen"]["white"]["white"] and dn["white"]["rho_h"] > 0 > R["sharpen"]["white"]["rho_h"],
          "前提 3 の検査は雑音除去(ρ_h > 0)と輪郭強調(ρ_h < 0)を見破る",
          "(ρ_h %+.3f 予測 %+.3f / %+.3f 予測 %+.3f)" % (dn["white"]["rho_h"], pred["denoise"]["fd"]["rho_h"],
                                                   R["sharpen"]["white"]["rho_h"], pred["sharpen"]["fd"]["rho_h"]))
    tn = R["tnr"]
    check(abs(tn["white"]["rho_h"]) < 0.03 and abs(tn["white"]["rho_t"] - (1 - ALPHA)) < 0.04 and not tn["white"]["white"],
          "時間の雑音除去: 画素どうしは白い(空間の検査は通る)が、1 枚おきの相関 ρ_t = 1 − α で見破る",
          "(ρ_h %+.3f、ρ_t %.3f、予測 %.2f)" % (tn["white"]["rho_h"], tn["white"]["rho_t"], 1 - ALPHA))

    print("== 3. 欠陥画素の補正: どの検査にも掛からない")
    dp = R["dpc"]
    pat = sensor["dsnu"].copy()
    rr, cc = np.unravel_index(sensor["hot"], (H, W))
    nb = np.stack([sensor["dsnu"][(rr + a) % H, (cc + b) % W] for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)])
    pat[rr, cc] = np.median(nb, axis=0)
    dsnu_pred = float(pat.std()) / K
    check(dp["defects"] == 0 and abs(rel(dp["DSNU"], dsnu_pred)) < 0.04,
          "熱画素 %d 個 → 0 個、DSNU は熱画素を中央値で埋めた模様の値(予測 %.2f e⁻)に下がる" % (T["defects"], dsnu_pred),
          "(%.2f e⁻、真値 %.2f の %+.0f %%)" % (dp["DSNU"], T["DSNU"], 100 * rel(dp["DSNU"], T["DSNU"])))
    check(abs(rel(dp["K"], K)) < 0.02 and abs(rel(dp["eta"], ETA)) < 0.03 and dp["eq51_ok"] and dp["white"]["white"],
          "K・η は動かず、式 51 も前提 3 の検査も通る —— 欠陥の数の嘘は手順の中からは見えない")

    print("== 4. 対数の圧伸: Linear の数は崩れ、式 51 が見破り、General が圧伸の前のセンサを取り戻す")
    lg = R["log"]
    check(not lg["eq51_ok"] and lg["eq51"] > 0.5, "式 51 が落ちる(局所の傾きの相対偏差の平均 %.0f %% ≫ 3 %%)" % (100 * lg["eq51"]))
    check(abs(rel(lg["eta"], ETA)) > 0.5, "Linear で読んだ η は %+.0f %%(%.3f)" % (100 * rel(lg["eta"], ETA), lg["eta"]),
          "%s" % ("—— η > 1 を emva_sensitivity_threshold が拒む" if lg["refused"] else ""))
    g = lg["general"]
    gr = R["raw"]["general"]
    pu = lg["mp"][1:][g["used"]]
    yr = OFF + K * ETA * pu
    tru = pu / np.sqrt((K ** 2 * (SD ** 2 + ETA * pu) + SC.SIGMA_Q2 + SC.SIGMA_Q2 / log_slope(yr) ** 2) / (K * ETA) ** 2)
    pp = np.geomspace(1, 300, 20000)
    ypp = OFF + K * ETA * pp
    tmin = pp[np.argmin(np.abs(pp / np.sqrt((K ** 2 * (SD ** 2 + ETA * pp) + SC.SIGMA_Q2 + SC.SIGMA_Q2 / log_slope(ypp) ** 2) / (K * ETA) ** 2) - 1))]
    m3 = tru > 3
    e_snr = float(np.abs(g["snr_p"][m3] / tru[m3] - 1).max())
    check(e_snr < 0.05 and abs(rel(g["snr_max"], tru.max())) < 0.02 and abs(rel(g["mu_p_min_local"], tmin)) < 0.04,
          "General: 入力 SNR が真値と 5 % 以内、SNRmax 2 %、μ_p.min(局所の補間)4 %",
          "(SNR 最大のずれ %.1f %%、SNRmax %.1f(真 %.1f)、μ_p.min %.2f(真 %.2f)、規格の逆回帰 %.2f)" % (
              100 * e_snr, g["snr_max"], tru.max(), g["mu_p_min_local"], tmin, g["mu_p_min"]))
    # General の不均一(式 55〜59): 傾きは General の特性曲線の B-スプラインから
    sp = SC.emva_bspline_regression(lg["mp"][1:], lg["mu"][1:] - lg["mu"][0], n_intervals=8, x_max=lg["psat"],
                                    x_eval=[0.0, 0.5 * lg["psat"]])
    cl = Camera("log2", "", sensor, np.random.default_rng(77), proc=lambda y: log_comp(y), out_max=1023)
    gn = SG.emva_general_nonuniformity(np.stack(cl.frames(0.0, L)), np.stack(cl.frames(0.5 * lg["psat"], L)),
                                       float(sp["slope_eval"][1]), 0.5 * lg["psat"], float(sp["slope_eval"][0]), highpass=None)
    check(abs(rel(gn["PRNU1288"], R["raw"]["PRNU"])) < 0.05 and abs(rel(lg["PRNU"], R["raw"]["PRNU"])) > 0.2,
          "General の PRNU(入力へ戻す、式 59)は圧伸しないセンサの値と 5 % 以内、Linear の式 67 は外れる",
          "(General %.4f / Linear %.4f / 圧伸なし %.4f)" % (gn["PRNU1288"], lg["PRNU"], R["raw"]["PRNU"]))

    # 相対量子効率(General 9.4 節、式 73・74): 圧伸したカメラで波長を振る(η は仕込み、光子数は波長ごとに揃えない)
    etas = np.array([ETA, 0.30, 0.20, 0.38])
    mps = np.array([8000.0, 15000.0, 21000.0, 5000.0])
    cq = Camera("logqe", "", sensor, np.random.default_rng(78), proc=lambda y: log_comp(y), out_max=1023)
    ys = []
    for p_, e_ in zip(mps, etas):
        fr = []
        for _ in range(2):                                              # 波長 λ では η(λ) で電子になる
            e = cq.rng.poisson(e_ * p_ * sensor["prnu"])
            fr.append(log_comp(np.clip(np.round(K * (e + cq.rng.normal(0.0, SD, (H, W))) + OFF + sensor["dsnu"]), 0, MAXDN)))
        ys.append(0.5 * (fr[0].mean() + fr[1].mean()))
    rq = SG.emva_general_relative_qe(lg["mp"][1:], lg["mu"][1:], lg["mu"][0], np.array(ys), mps, 0)
    e_rel = float(np.abs(rq["eta_rel"] / (etas / ETA) - 1).max())
    e_pr = float(np.abs(rq["eq74_as_printed"] / (etas / ETA) - 1).max())
    naive = (np.array(ys) - lg["mu"][0]) / mps / ((ys[0] - lg["mu"][0]) / mps[0])
    check(e_rel < 0.02 and e_pr > 0.5, "General の相対量子効率(逆の特性曲線で線形化、式 73・74)が仕込みの比を 2 % 以内で取り戻す",
          "(最大のずれ %.2f %%。印刷どおりの式 74 は %.0f %%、線形化しない比は %.0f %% 外れる)"
          % (100 * e_rel, 100 * e_pr, 100 * float(np.abs(naive / (etas / ETA) - 1).max())))

    print("== 5. General は空間・時間の雑音除去の嘘を消さない(η・K を出さないだけ)")
    for nm in ("denoise", "tnr"):
        gm = R[nm]["general"]
        S = pred[nm]["fd"]["S"]
        pm = R[nm]["mp"][1:][gm["used"]]
        band = (pm > 0.05 * R[nm]["psat"]) & (pm < 0.9 * R[nm]["psat"])
        ratio = float(np.median(gm["snr_p"][band] / SC.emva_snr_curve(pm[band], ETA, SD, K)[:, 1]))
        check(abs(ratio * math.sqrt(S) - 1) < 0.02, "%s: General の入力 SNR は真値の 1/√S = %.3f 倍に膨らむ(飽和の 5〜90 %% の中央値)"
              % (nm, 1 / math.sqrt(S)), "(%.3f 倍、μ_p.min %.1f → %.1f 光子)" % (ratio, gr["mu_p_min_local"], gm["mu_p_min_local"]))
    snr_sat = R["denoise"]["general"]["snr_max"]
    print("  ★雑音除去のカメラの SNRmax(General、測った SNR_p の最大)は %.0f(真の入力 SNR の飽和の露光での値 %.0f の %.2f 倍)。"
          "飽和は前処理の後の値で決まるが、生の画素はそれより先に 4095 で切れて分散が潰れる —— 最大はその潰れた点に出る。"
          % (snr_sat, SC.emva_snr_curve([R["denoise"]["psat"]], ETA, SD, K)[0, 1],
             snr_sat / SC.emva_snr_curve([R["denoise"]["psat"]], ETA, SD, K)[0, 1]))

    print("== 6. 閉形式の第 2 の実装: S = Σw²/(Σw)² を周波数領域(Parseval: |Ŵ(f)|² の平均)で")
    worst = 0.0
    for w in (W_DENOISE, W_SHARPEN, W_GAIN):
        Wf = np.fft.fft2(w, s=(32, 32))
        s_fft = float(np.mean(np.abs(Wf) ** 2)) / float(np.abs(Wf[0, 0]) ** 2)
        worst = max(worst, abs(s_fft / SC.emva_filter_distortion(w)["S_spatial"] - 1))
    check(worst < 1e-12, "Σw²/(Σw)² = 周波数領域の値", "(最大のずれ %.1e)" % worst)

    elapsed = time.time() - t0
    cpu = time.process_time() - c0
    # ★壁時計でなく CPU 時間で掛ける: スイートが PoC を 6 本並べて走らせると、単独 31 秒が壁時計 115 秒になった(2026-10-13 の全量)。
    #   この PoC が自分で使う計算量を見るのが目的なので、他のプロセスの混み具合で揺れない量にする。
    check(cpu < 60.0, "所要 CPU 時間(CI の上限に余裕を残す)", "%.1f 秒(壁時計 %.1f 秒)" % (cpu, elapsed))
    if figs.enabled():
        t_f = time.time()
        _figures(cams, R, T, rows, keys, pred, tru, pu, g)
        print("  図(%.1f s)" % (time.time() - t_f))
    assert not figs.errors(), figs.errors()
    bad = [c for c in CHECKS if not c[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(CHECKS), len(CHECKS) - len(bad), elapsed))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


# ─────────────────────────────── 図 ─────────────────────────────
def _figures(cams, R, T, rows, keys, pred, tru, pu, g):
    names = [c.name for c in cams]
    labels = {c.name: c.label for c in cams}
    # (1) 嘘の大きさ: 数ごとに、真値に対する比(log2)を前処理ごとに並べる
    series = []
    x = np.arange(len(names), dtype=float)
    for si, (k, h, _) in enumerate(keys[:3] + keys[6:8]):               # 5 系列まで(色と印が重ならない)
        ys = []
        for nm in names:
            v = R[nm].get(k)
            if v is None:
                ys.append(np.nan)
            elif k == "snr_max_dB":
                ys.append((v - T[k]) / (20 * math.log10(2)))          # dB の差 → 2 倍の数
            else:
                ys.append(math.log2(v / T[k]))
        series.append((h, x + 0.1 * (si - 2.0), np.array(ys)))               # 重ならないよう数ごとに横へずらす
    series.append(("", [-0.4, 6.4], [0.0, 0.0]))                               # 真値(比 1)
    figs.save_plot("datasheet_lies", series, kinds=["scatter"] * (len(series) - 1) + ["line"],
                   styles=[None] * (len(series) - 1) + ["dashed"], colors=[None] * (len(series) - 1) + ["reference"], size=(720, 380),
                   xlabel="前処理(0 なし / 1 ゲイン×2 / 2 雑音除去 / 3 輪郭強調 / 4 時間 / 5 欠陥補正 / 6 対数)",
                   ylabel="log2(測った値 / 真値)", title="データシートの数はどれだけ動くか",
                   caption="同じセンサに前処理を 1 つずつかけ、規格 Linear の手順で測った数を真値で割る(0 = 正しい、1 = 2 倍)。"
                           "雑音除去は η を %+.0f %%、時間の雑音除去は %+.0f %% 膨らませる。どちらも η はまだ 1 以下でもっともらしい。" % (
                               100 * (R["denoise"]["eta"] / ETA - 1), 100 * (R["tnr"]["eta"] / ETA - 1)))
    # (2) 表(CSV/TSV も)
    figs.save_table("datasheet_numbers", ["前処理"] + [h for _, h, _ in keys],
                    [["真値"] + [(f % T[k]) for k, _, f in keys]] + rows,
                    title="規格 Linear の手順で測った数(括弧は真値に対するずれ)",
                    caption="拒否 = η > 1 で絶対感度しきい値(式 26)の op が拒んだ。DSNU・PRNU は照明が一様なので高域フィルタなし。")
    # (3) 雑音の指紋: 2 枚の差の拡大(前処理ごと)
    panels, caps = [], []
    for nm in ("raw", "denoise", "sharpen", "tnr"):
        f = R[nm]["mid_frames"]
        d = (f[0] - f[1])[96:160, 128:192]
        panels.append(d / max(1e-9, float(np.abs(d).max())))
        wv = R[nm]["white"]
        caps.append("%s ρ_h %+.2f ρ_t %+.2f" % (labels[nm], wv["rho_h"], wv["rho_t"]))
    figs.save_grid("noise_fingerprint", panels, captions=caps, title="同じ露光の 2 枚の差(時間雑音だけが残る)", ncols=4,
                   caption="前処理なしの差は白い砂嵐。雑音除去はまだら(隣と似る、ρ_h > 0)、輪郭強調は細かいざらつき(隣と逆、ρ_h < 0)。"
                           "時間の雑音除去は画素どうしは白いままで、1 枚おきの画像との相関 ρ_t = 1 − α = %.1f だけが残る。" % (1 - ALPHA))
    # (4) photon transfer: 傾きが K。雑音除去は直線のまま傾きだけが寝る(式 51 は見逃す)、圧伸は曲がる(式 51 が見破る)
    ser = []
    for nm in ("raw", "denoise", "sharpen", "log"):
        r = R[nm]
        ok = r["mu"] - r["mu"][0] <= 0.7 * (r["mu_sat"] - r["mu"][0])
        ser.append((labels[nm], (r["mu"] - r["mu"][0])[ok], (r["var"] - r["var"][0])[ok]))
    figs.save_plot("photon_transfer", ser, kinds=["scatter"] * 4, xlabel="平均 − 暗の平均 [DN]", ylabel="分散 − 暗の分散 [DN²]",
                   title="photon transfer(0〜70 %)",
                   caption="傾きがシステムゲイン K。雑音除去は直線のまま傾きが %.2f 倍に寝る —— 式 51(直線性)は通り、η = R/K が膨らむ。"
                           "対数の圧伸は曲がるので式 51 が落ちる。" % (R["denoise"]["K"] / R["raw"]["K"]))
    # (5) General: 圧伸したカメラの入力 SNR
    figs.save_plot("general_input_snr", [("General で測った入力 SNR_p(対数の圧伸)", np.log10(pu[pu > 0]), np.log10(g["snr_p"][pu > 0])),
                                         ("真値(圧伸の前のセンサ + 量子化)", np.log10(pu[pu > 0]), np.log10(tru[pu > 0])),
                                         ("Linear で読んだ η・σ_d からの式 21", np.log10(pu[pu > 0]),
                                          np.log10(SC.emva_snr_curve(pu[pu > 0], min(R["log"]["eta"], 1.0), R["log"]["sigma_d"] or 1.0,
                                                                     R["log"]["K"])[:, 1]))],
                   kinds=["scatter", "line", "line"], styles=[None, "dashed", None], xlabel="log10 μ_p [光子/画素]", ylabel="log10 SNR",
                   title="圧伸したカメラ: General は入力の SNR を取り戻す",
                   caption="General は出力の雑音を特性曲線の傾きで入力へ戻す(式 9・10)。圧伸したカメラでも圧伸の前のセンサの SNR に重なる。"
                           "Linear の数(η %.2f)から引いた式 21 の曲線は別物。" % R["log"]["eta"])


if __name__ == "__main__":
    main()
