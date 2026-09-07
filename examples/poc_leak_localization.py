# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""(暫定 docstring —— 実行後に実測値で書き換える)"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元(すべて既知 = 真値) ---------------------------------------- #
FS_HZ = 8192.0            # 標本化周波数 [Hz]
T_SEC = 2.0               # 記録長 [s]
N = int(FS_HZ * T_SEC)    # 標本数
L_M = 120.0               # センサ 1 とセンサ 2 の管路長 [m]
X_LEAK = 78.0             # 漏水源の位置(センサ 1 から) [m]
C_TRUE = 1250.0           # 管の音速 [m/s](延性鋳鉄 φ150 相当)
C_PVC = 500.0             # 途中で切り替わる樹脂管の音速 [m/s]
BAND = (100.0, 800.0)     # 漏水音の帯域 [Hz]
ALPHA_DB_1KHZ = 0.20      # 減衰 [dB/m @ 1 kHz]。周波数に比例させる
ECHO_M = (1.4, 2.2)       # センサの先の継手までの**往復**距離 [m](反射の元)
SEED = 20260908

_LAB = fs.ledger
FREQS = np.fft.rfftfreq(N, 1.0 / FS_HZ)
LAGS = np.arange(N)
LAGS[LAGS > N // 2] -= N
#: 物理的にあり得る遅れだけを探す(相関器の探索窓)。
LAG_MAX = int(np.ceil(L_M / min(C_TRUE, C_PVC) * FS_HZ)) + 4
#: 相関の主ローブの幅 c/(2B) [m]。これを超えた誤差は「別のピークを掴んだ」。
GROSS_M = C_TRUE / (2.0 * (BAND[1] - BAND[0]))
#: 整数ピークの位置量子 c/(2 fs) [m]。
QUANT_M = C_TRUE / (2.0 * FS_HZ)

PIPE_UNIFORM = ((L_M, C_TRUE),)
PIPE_MIXED = ((60.0, C_TRUE), (60.0, C_PVC))


# --------------------------------------------------------------------------- #
# 場面を作る —— 源・音速・減衰・センサ位置をすべて既知にする                     #
# --------------------------------------------------------------------------- #
def travel_time(pipe, a: float, b: float) -> float:
    """管路の ``a`` [m] から ``b`` [m] までの伝搬時間 [s](区間ごとの音速で積分)。"""
    a, b = sorted((float(a), float(b)))
    t, pos = 0.0, 0.0
    for length, c in pipe:
        lo, hi = pos, pos + length
        overlap = max(0.0, min(b, hi) - max(a, lo))
        t += overlap / c
        pos = hi
    return t


#: 片側スペクトルの重み(Parseval で時間領域の平均二乗に戻すため)。
_ONESIDE = np.full(FREQS.size, 2.0)
_ONESIDE[0] = _ONESIDE[-1] = 1.0
_INBAND = (FREQS >= BAND[0]) & (FREQS <= BAND[1])


def make_records(snr_db: float, seed: int, x_leak: float = X_LEAK,
                 pipe=PIPE_UNIFORM, echo: float = 0.0,
                 alpha: float = ALPHA_DB_1KHZ) -> dict:
    """2 点の記録を合成する。**遅れも減衰も反射も雑音の密度も既知**。

    源は「帯域内で振幅が平坦・位相が一様乱数」の広帯域雑音(漏水の噴流音)。
    **時間領域で白色雑音を濾すのではなく周波数領域で組む** —— そうすると
    信号のビンごとのパワーが乱数でなく**閉形式**になり、あとで CRLB を
    推定でなく計算で出せる(1 回目は濾した版で書いて、実測 RMS が CRLB を
    下回るという有り得ない結果になった。原因は周期グラム比の推定誤差)。

    センサ i には ``exp(-2πi f t_i)`` の**厳密な小数標本遅れ**と、距離に
    比例し周波数に比例する減衰を掛けて届ける。反射はセンサの先の継手で
    折り返した往復路(振幅 ``echo``)。雑音は**広帯域**(交通・ポンプ)で、
    帯域内 SNR が ``snr_db`` になるように振幅を決める —— 帯域内だけの
    雑音にすると「帯域制限」という前処理が無条件に無力になり比較が嘘になる。
    """
    rng = np.random.default_rng(seed)
    spec = np.where(_INBAND, np.exp(2j * np.pi * rng.random(FREQS.size)), 0.0)
    d1, d2 = float(x_leak), float(L_M - x_leak)
    t1 = travel_time(pipe, 0.0, x_leak)
    t2 = travel_time(pipe, x_leak, L_M)

    def leg(delay_s: float, dist_m: float, amp: float = 1.0) -> np.ndarray:
        att = 10.0 ** (-(alpha * (FREQS / 1000.0) * dist_m) / 20.0)
        return spec * amp * att * np.exp(-2j * np.pi * FREQS * delay_s)

    ys = [leg(t1, d1), leg(t2, d2)]
    if echo > 0.0:
        c_end = (pipe[0][1], pipe[-1][1])
        for k, (tt, dd, extra) in enumerate(((t1, d1, ECHO_M[0]),
                                             (t2, d2, ECHO_M[1]))):
            ys[k] = ys[k] + leg(tt + extra / c_end[k], dd + extra, echo)

    snr = 10.0 ** (snr_db / 10.0)
    clean, noise, recs, rho = [], [], [], []
    for spec_i in ys:
        # 帯域内の信号パワー(Parseval)/ 白色雑音のビンあたり期待パワー N
        p_sig = float(np.sum(_ONESIDE[_INBAND]
                             * np.abs(spec_i[_INBAND]) ** 2)) / N ** 2
        g2 = p_sig * N / (snr * float(np.sum(_ONESIDE[_INBAND])))
        g = float(np.sqrt(g2))
        y = np.fft.irfft(spec_i, N)
        w = g * rng.standard_normal(N)
        clean.append(y)
        noise.append(w)
        recs.append(y + w)
        rho.append(np.abs(spec_i) ** 2 / (g2 * N))     # ビンごとの SNR(閉形式)
    return {"y1": recs[0], "y2": recs[1], "clean1": clean[0], "clean2": clean[1],
            "n1": noise[0], "n2": noise[1], "rho1": rho[0], "rho2": rho[1],
            "t1": t1, "t2": t2, "tau_true": t1 - t2, "x_leak": float(x_leak),
            "pipe": pipe}


# --------------------------------------------------------------------------- #
# 推定器 —— どれも「遅延 τ [s]」を返す。位置は最後に 1 か所で作る               #
# --------------------------------------------------------------------------- #
def position(tau, c_assumed: float):
    """遅延から掘る場所 [m] を出す。``x = (L + c·τ)/2`` —— この 1 行が全部。"""
    return 0.5 * (L_M + c_assumed * np.asarray(tau, np.float64))


def _score_1d(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """fullseye の :func:`correlation_score`(3-D 用)を 1-D 信号に使う。

    ``score[s] = Σ a[x] b[x+s]`` の正規化版で、``b`` が ``a`` を ``s0``
    ずらしたものならピークは厳密に ``s0``(閉形式の真値つき op)。
    """
    s = np.asarray(_LAB.correlation_score(a[None, None, :].astype(np.float64),
                                          b[None, None, :].astype(np.float64)))
    return s[0, 0]


def _peak_lag(corr: np.ndarray, subsample: bool = True) -> float:
    """探索窓のなかの最大ピーク位置 [標本](放物線サブサンプルつき)。"""
    idx = np.nonzero(np.abs(LAGS) <= LAG_MAX)[0]
    k = int(idx[int(np.argmax(corr[idx]))])
    delta = 0.0
    if subsample:
        ym, y0, yp = (float(corr[(k - 1) % N]), float(corr[k]),
                      float(corr[(k + 1) % N]))
        den = ym - 2.0 * y0 + yp
        if den < -1e-30:
            delta = float(np.clip(0.5 * (ym - yp) / den, -1.0, 1.0))
    return float(LAGS[k]) + delta


def tau_raw(rec: dict, subsample: bool = False) -> float:
    """ゼロ点 —— 生の相互相関のピークをそのまま読む。"""
    return -_peak_lag(_score_1d(rec["y1"], rec["y2"]), subsample) / FS_HZ


def tau_bandlimited(rec: dict) -> float:
    """帯域制限してから相関(前処理その 1、fullseye の ``bandpass``)。"""
    a = fs.bandpass(rec["y1"], FS_HZ, BAND[0], BAND[1], order=4)
    b = fs.bandpass(rec["y2"], FS_HZ, BAND[0], BAND[1], order=4)
    return -_peak_lag(_score_1d(a, b), True) / FS_HZ


def _gcc(y1: np.ndarray, y2: np.ndarray, phat: bool, band=None) -> np.ndarray:
    """一般化相互相関。``phat`` で振幅を白色化する(Knapp-Carter 1976)。"""
    cross = np.conj(np.fft.rfft(y1)) * np.fft.rfft(y2)
    if phat:
        mag = np.abs(cross)
        cross = np.where(mag > 1e-18, cross / np.maximum(mag, 1e-18), 0.0)
    if band is not None:
        cross = np.where((FREQS >= band[0]) & (FREQS <= band[1]), cross, 0.0)
    return np.fft.irfft(cross, N)


def tau_phat(rec: dict) -> float:
    """GCC-PHAT(全帯域、教科書どおり)。"""
    return -_peak_lag(_gcc(rec["y1"], rec["y2"], True), True) / FS_HZ


def tau_phat_band(rec: dict) -> float:
    """GCC-PHAT を漏水音の帯域内だけで(白色化 + 帯域制限)。"""
    return -_peak_lag(_gcc(rec["y1"], rec["y2"], True, BAND), True) / FS_HZ


def tau_phase_slope(rec: dict) -> float:
    """位相勾配 —— ``transfer_function`` の位相の傾きから群遅延を出す。

    ``y2(t) = y1(t + τ)`` なので ``H(f) = exp(+2πi f τ)``。コヒーレンスで
    重みを付けた最小二乗で傾きを取る(fullseye の acoustics 族 2 op)。
    """
    tf = _LAB.transfer_function(rec["y1"], rec["y2"], FS_HZ, win=4096)
    f = np.asarray(tf["freqs"], np.float64)
    m = (f >= BAND[0]) & (f <= BAND[1])
    ph = np.unwrap(np.asarray(tf["phase_rad"], np.float64)[m])
    w = np.asarray(tf["coherence"], np.float64)[m] ** 2
    ff = f[m]
    a = np.vstack([ff, np.ones_like(ff)]).T
    sol, *_ = np.linalg.lstsq(a * w[:, None], ph * w, rcond=None)
    return float(sol[0]) / (2.0 * np.pi)


METHODS = (("生の相関(整数ピーク)", lambda r: tau_raw(r, False)),
           ("生の相関 + サブサンプル", lambda r: tau_raw(r, True)),
           ("帯域制限 + サブサンプル", tau_bandlimited),
           ("GCC-PHAT(全帯域)", tau_phat),
           ("GCC-PHAT(帯域内)", tau_phat_band))


# --------------------------------------------------------------------------- #
# 崖を先に予測する —— Cramér-Rao 下界(Knapp-Carter 1976)                      #
# --------------------------------------------------------------------------- #
def crlb_sigma_x(rec: dict) -> float:
    """この場面の CRLB(位置の標準偏差 [m])を**閉形式のビンごと SNR から**出す。

    ``var(τ) = [2 Σ_k (2π f_k)² ρ1 ρ2 / (1 + ρ1 + ρ2)]⁻¹``
    (Knapp-Carter 1976 の一般形。``γ²/(1-γ²) = ρ1ρ2/(1+ρ1+ρ2)``)。
    ρ_i は**ビンごとの** SNR なので、減衰で高域が痩せていることも
    帯域外に信号が無いことも自動的に入る(平坦帯域の閉形式より正直)。
    """
    r1, r2 = rec["rho1"], rec["rho2"]
    fisher = 2.0 * np.sum((2.0 * np.pi * FREQS) ** 2 * r1 * r2 / (1.0 + r1 + r2))
    return 0.5 * C_TRUE * float(np.sqrt(1.0 / fisher))


def crlb_flat(snr_db: float) -> float:
    """平坦帯域・両端等 SNR の閉形式(比較用)。σ_x = (c/2)·σ_τ。"""
    rho = 10.0 ** (snr_db / 10.0)
    f1, f2 = BAND
    var = 3.0 * (1.0 + 2.0 * rho) / (8.0 * np.pi ** 2 * T_SEC
                                     * (f2 ** 3 - f1 ** 3) * rho ** 2)
    return 0.5 * C_TRUE * float(np.sqrt(var))


def threshold_prediction() -> float:
    """崖の予測 [dB] —— CRLB の σ_τ が相関主ローブの半幅 1/(2 f_hi) に届く点。"""
    half = 1.0 / (2.0 * BAND[1])
    for snr_db in np.arange(10.0, -50.0, -0.1):
        if crlb_flat(snr_db) / (0.5 * C_TRUE) >= half:
            return float(snr_db)
    return float("nan")


# --------------------------------------------------------------------------- #
# 1) 場面とゼロ点                                                              #
# --------------------------------------------------------------------------- #
def _scene_figure(rec: dict) -> None:
    if not figs.enabled():
        return
    w, h = 820, 330
    img = np.full((h, w, 3), 0.97)
    x0, x1, ypipe = 70.0, float(w - 70), 225.0

    def px(m: float) -> float:
        return x0 + (x1 - x0) * (m / L_M)

    img = np.asarray(fs.draw_line(img, (0.0, 92.0), (float(w), 92.0),
                                  color="neutral", width=2))
    img = np.asarray(fs.text_box(img, "地表(舗装)", (10.0, 78.0), anchor="lb",
                                 font_size=11))
    img = np.asarray(fs.draw_line(img, (x0, ypipe), (x1, ypipe),
                                  color="reference", width=10))
    for m, name in ((0.0, "センサ 1"), (L_M, "センサ 2")):
        img = np.asarray(fs.draw_line(img, (px(m), 100.0), (px(m), ypipe - 6.0),
                                      color="neutral", width=2))
        img = np.asarray(fs.draw_circle(img, (px(m), 108.0), 9.0,
                                        color="neutral", width=2, fill=True))
        img = np.asarray(fs.text_box(img, name, (px(m), 74.0), anchor="ct",
                                     font_size=12))
    img = np.asarray(fs.draw_circle(img, (px(X_LEAK), ypipe), 11.0,
                                    color="wrong", width=3, fill=False))
    img = np.asarray(fs.arrow(img, (px(X_LEAK), ypipe - 8.0),
                              (px(X_LEAK), ypipe - 52.0), color="wrong", width=2))
    img = np.asarray(fs.text_box(img, "漏水 x = %.0f m" % X_LEAK,
                                 (px(X_LEAK), ypipe - 58.0), anchor="cb",
                                 color="wrong", font_size=12))
    img = np.asarray(fs.arrow(img, (px(X_LEAK) - 14.0, ypipe + 30.0),
                              (px(0.0) + 6.0, ypipe + 30.0), color="emphasis",
                              width=2))
    img = np.asarray(fs.arrow(img, (px(X_LEAK) + 14.0, ypipe + 30.0),
                              (px(L_M) - 6.0, ypipe + 30.0), color="emphasis",
                              width=2))
    img = np.asarray(fs.text_box(
        img, "d1 = %.0f m  /  %.1f ms" % (X_LEAK, 1e3 * rec["t1"]),
        (px(X_LEAK * 0.5), ypipe + 46.0), anchor="ct", font_size=11))
    img = np.asarray(fs.text_box(
        img, "d2 = %.0f m  /  %.1f ms" % (L_M - X_LEAK, 1e3 * rec["t2"]),
        (px((X_LEAK + L_M) * 0.5), ypipe + 46.0), anchor="ct", font_size=11))
    img = np.asarray(fs.text_box(
        img, "管路 L = %.0f m / 音速 c = %.0f m/s / 帯域 %.0f-%.0f Hz"
        % (L_M, C_TRUE, BAND[0], BAND[1]), (10.0, 16.0), anchor="lt", font_size=13))
    img = np.asarray(fs.text_box(
        img, "掘る場所 x = (L + c·τ) / 2   —— τ = d1/c - d2/c = %.2f ms"
        % (1e3 * rec["tau_true"]), (10.0, float(h - 12)), anchor="lb",
        color="emphasis", font_size=12))
    figs.save("scene", img,
              "埋設管の 2 点に相関式漏水探知機を当てる。位置は到達時間差 τ と "
              "音速 c だけで決まる。")


def section_scene_zero() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面とゼロ点 —— 生の相互相関のピークをそのまま読む")
    print("=" * 78)

    rec = make_records(0.0, SEED)
    print("  管路 %.0f m / 漏水 %.0f m / 音速 %.0f m/s / 帯域 %.0f-%.0f Hz / "
          "記録 %.0f s @ %.0f Hz" % (L_M, X_LEAK, C_TRUE, BAND[0], BAND[1],
                                     T_SEC, FS_HZ))
    print("  真値: d1 = %.1f ms, d2 = %.1f ms, τ = %.3f ms (= %.1f 標本)"
          % (1e3 * rec["t1"], 1e3 * rec["t2"], 1e3 * rec["tau_true"],
             rec["tau_true"] * FS_HZ))
    print("  位置の量子(整数ピーク) c/(2fs) = %.3f m / 主ローブ幅 c/(2B) = %.3f m"
          % (QUANT_M, GROSS_M))

    # 符号の自己検査 —— 雑音を切って、閉形式の τ が戻ることを確かめる
    noiseless = make_records(60.0, SEED)
    tau_chk = tau_raw(noiseless, True)
    assert abs(tau_chk - noiseless["tau_true"]) < 3.0 / FS_HZ, (tau_chk,
                                                                noiseless["tau_true"])

    rows = []
    print("\n  手法                      τ の誤差 [µs]   掘る場所 [m]   ずれ [m]")
    for name, fn in METHODS:
        tau = fn(rec)
        x_hat = position(tau, C_TRUE)
        rows.append([name, "%+.1f" % (1e6 * (tau - rec["tau_true"])),
                     "%.3f" % x_hat, "%+.3f" % (x_hat - X_LEAK)])
        print("   %-24s %+8.1f      %8.3f    %+7.3f"
              % (name, 1e6 * (tau - rec["tau_true"]), x_hat, x_hat - X_LEAK))
    worst = max(abs(float(r[3])) for r in rows)
    ps = []
    for snr in (20.0, 0.0):
        tau_ps = tau_phase_slope(make_records(snr, SEED))
        x_ps = position(tau_ps, C_TRUE)
        ps.append(float(x_ps) - X_LEAK)
        print("   %-20s(SNR %+.0f dB) %+8.1f      %8.3f    %+7.3f"
              % ("位相勾配", snr, 1e6 * (tau_ps - rec["tau_true"]), x_ps,
                 x_ps - X_LEAK))
    rows.append(["位相勾配(transfer_function)", "-", "%.3f" % position(
        tau_phase_slope(rec), C_TRUE), "%+.3f" % ps[1]])
    print("\n  ★SNR 0 dB・音速が真値なら、相関系の 5 手法はどれも %.3f m 以内"
          "(主ローブ幅 %.2f m の 1/10 以下)。" % (worst, GROSS_M))
    print("     ★位相勾配だけは別で、+20 dB なら %+.3f m だが 0 dB では "
          "%+.3f m —— 位相の unwrap が\n     帯域のどこかで 1 周滑ると、"
          "傾き = 遅延がそのぶん丸ごとずれる(壊れ方が連続でない)。"
          % (ps[0], ps[1]))

    _scene_figure(rec)

    t = np.arange(N) / FS_HZ
    sl = slice(int(0.500 * FS_HZ), int(0.560 * FS_HZ))
    figs.save_plot("waveforms",
                   [("センサ 1(遠い %.0f m)" % X_LEAK, 1e3 * t[sl], rec["y1"][sl]),
                    ("センサ 2(近い %.0f m)" % (L_M - X_LEAK), 1e3 * t[sl],
                     rec["y2"][sl])],
                   xlabel="時刻 [ms]", ylabel="振幅 [任意単位]",
                   title="2 点の記録(SNR 0 dB)—— 目では遅れは読めない",
                   caption="同じ漏水源に既知の遅れ %.2f ms・距離に応じた減衰・"
                           "独立な広帯域雑音を乗せた。" % (1e3 * rec["tau_true"]))

    xs = position(-LAGS / FS_HZ, C_TRUE)
    keep = np.abs(LAGS) <= LAG_MAX
    order = np.argsort(xs[keep])
    series = []
    for name, corr in (("生の相関", _score_1d(rec["y1"], rec["y2"])),
                       ("GCC-PHAT(帯域内)", _gcc(rec["y1"], rec["y2"], True, BAND))):
        v = corr[keep][order]
        series.append((name, xs[keep][order], v / np.max(np.abs(v))))
    series.append(("真の漏水位置", [X_LEAK, X_LEAK], [-0.4, 1.0]))
    figs.save_plot("correlation_curves", series, xlabel="相関が指す位置 [m]",
                   ylabel="正規化した相関",
                   title="相関関数を「掘る場所」の軸で見る(SNR 0 dB)",
                   caption="PHAT は白色化でピークが尖る。ただし尖ることと"
                           "当たることは別。")
    return {"rec": rec, "rows": rows}


# --------------------------------------------------------------------------- #
# 2) 崖 —— SNR を掃く。予測(CRLB)と突き合わせる                               #
# --------------------------------------------------------------------------- #
def section_snr_cliff() -> dict:
    print("\n" + "=" * 78)
    print("2) 崖 —— SNR を掃く。★予測を先に置く")
    print("=" * 78)
    thr = threshold_prediction()
    print("  予測 A: 位置の散らばりは CRLB(Knapp-Carter 1976)に従う。")
    print("          σ_x = (c/2)·√{3(1+2ρ) / (8π² T (f2³-f1³) ρ²)}")
    print("          0 dB で %.4f m、-20 dB で %.3f m。"
          % (crlb_flat(0.0), crlb_flat(-20.0)))
    print("  予測 B: 崖は CRLB の σ_τ が相関主ローブの半幅 1/(2 f_hi) = %.0f µs "
          "に届く\n          **SNR %.1f dB** 付近。そこから下はピークの取り違えで、"
          "誤差は\n          探索窓いっぱい(一様なら RMS %.1f m)に飛ぶ。"
          % (1e6 / (2.0 * BAND[1]), thr,
             float(np.sqrt(L_M ** 2 / 12.0 + (X_LEAK - L_M / 2.0) ** 2))))
    print("  予測 C: 整数ピークは c/(2fs) = %.3f m に量子化され、RMS は"
          " %.4f m を下回れない。" % (QUANT_M, QUANT_M / np.sqrt(12.0)))

    # 数値の CRLB が閉形式と一致することを、減衰を切った場面で確かめておく
    flat_chk = crlb_sigma_x(make_records(0.0, SEED, alpha=0.0))
    print("  検算: 減衰を切った場面のビンごと CRLB %.5f m と平坦帯域の閉形式"
          " %.5f m は %.2f %% 差。\n        減衰を入れると %.5f m へ悪化する"
          "(高域が先に痩せ、Fisher 情報は f² で効くため)。"
          % (flat_chk, crlb_flat(0.0), 100 * abs(flat_chk / crlb_flat(0.0) - 1),
             crlb_sigma_x(make_records(0.0, SEED))))
    assert abs(flat_chk / crlb_flat(0.0) - 1.0) < 0.02, (flat_chk, crlb_flat(0.0))

    snrs = (10.0, 5.0, 0.0, -5.0, -10.0, -15.0, -20.0, -25.0, -30.0)
    seeds = [SEED + 7 * k for k in range(24)]
    names = [n for n, _ in METHODS]
    fine = {n: [] for n in names}
    gross = {n: [] for n in names}
    crlb, crlb_num = [], []

    for snr in snrs:
        errs = {n: [] for n in names}
        num = []
        for k, sd in enumerate(seeds):
            rec = make_records(snr, sd)
            if k == 0:
                num.append(crlb_sigma_x(rec))
            for name, fn in METHODS:
                errs[name].append(position(fn(rec), C_TRUE) - X_LEAK)
        crlb.append(crlb_flat(snr))
        crlb_num.append(float(np.mean(num)))
        for name in names:
            e = np.asarray(errs[name])
            ok = np.abs(e) <= GROSS_M
            gross[name].append(100.0 * float(np.mean(~ok)))
            fine[name].append(float(np.sqrt(np.mean(e[ok] ** 2))) if ok.any()
                              else float("nan"))

    print("\n  SNR [dB]   CRLB(平坦) CRLB(実測ｽﾍﾟｸﾄﾙ)  "
          + "  ".join("%-12s" % n[:12] for n in names))
    for i, snr in enumerate(snrs):
        cells = []
        for name in names:
            cells.append("%6.3f/%3.0f%%" % (fine[name][i], gross[name][i]))
        print("   %+6.1f     %8.4f      %8.4f        %s"
              % (snr, crlb[i], crlb_num[i], "  ".join("%-12s" % c for c in cells)))
    print("  (値は「ピークを取り違えなかった試行の RMS [m] / 取り違えた割合」)")

    ref = "帯域制限 + サブサンプル"
    first = next((snrs[i] for i in range(len(snrs)) if gross[ref][i] > 5.0), None)
    print("\n  ★実測の崖(%s が 5 %% 以上取り違える最初の点): %s dB。予測は %.1f dB。"
          % (ref, "%+.0f" % first if first is not None else "掃引内に無し", thr))
    idx0 = snrs.index(0.0)
    print("  ★0 dB での実測 RMS: 整数 %.4f m / サブサンプル %.4f m / "
          "帯域制限 %.4f m\n     —— CRLB は %.4f m(実測スペクトル %.4f m)。"
          "**どれも下界には遠い**。"
          % (fine[names[0]][idx0], fine[names[1]][idx0], fine[ref][idx0],
             crlb[idx0], crlb_num[idx0]))
    print("     整数ピークの量子化の寄与 %.4f m を二乗で引くと %.4f m —— "
          "サブサンプルの実測 %.4f m とほぼ同じで、\n     **整数版の誤差は"
          "ほぼ量子化だけで説明できる**。"
          % (QUANT_M / np.sqrt(12.0),
             float(np.sqrt(max(fine[names[0]][idx0] ** 2
                               - QUANT_M ** 2 / 12.0, 0.0))),
             fine[names[1]][idx0]))

    figs.save_plot("snr_sweep",
                   [(n, list(snrs), fine[n]) for n in names]
                   + [("CRLB(実測スペクトル)", list(snrs), crlb_num)],
                   xlabel="帯域内 SNR [dB]", ylabel="位置誤差の RMS [m](対数)",
                   title="崖 —— どこから掘る場所が飛ぶか",
                   caption="取り違えを除いた試行だけの RMS。下界に触れる手法は"
                           "無い。")
    figs.save_plot("gross_rate", [(n, list(snrs), gross[n]) for n in names],
                   xlabel="帯域内 SNR [dB]", ylabel="ピークの取り違え [%]",
                   title="崖の正体はピークの取り違え(%.2f m 超を数えた)" % GROSS_M)
    return {"snrs": snrs, "fine": fine, "gross": gross, "crlb": crlb,
            "crlb_num": crlb_num, "thr": thr, "first": first, "names": names}


# --------------------------------------------------------------------------- #
# 3) 反射 —— PHAT は勝つか                                                     #
# --------------------------------------------------------------------------- #
def section_reflection() -> dict:
    print("\n" + "=" * 78)
    print("3) 反射を入れる —— ★予想: PHAT が勝つ(白色化で直達ピークが立つ)")
    print("=" * 78)
    print("  予想: 継手からの反射は相関に第 2 のピークを作り、生の相関の重心を")
    print("        引っぱる。PHAT は振幅を白色化するので直達波のピークが")
    print("        相対的に立ち、反射に強いはず。ただし低 SNR では雑音しか")
    print("        無いビンも等しく持ち上げるので負けるはず。")

    amps = (0.0, 0.2, 0.4, 0.6, 0.8)
    seeds = [SEED + 13 * k for k in range(16)]
    pick = ("生の相関 + サブサンプル", "帯域制限 + サブサンプル",
            "GCC-PHAT(帯域内)")
    out = {snr: {n: [] for n in pick} for snr in (10.0, -10.0)}
    for snr in (10.0, -10.0):
        for amp in amps:
            acc = {n: [] for n in pick}
            for sd in seeds:
                rec = make_records(snr, sd, echo=amp)
                for name, fn in METHODS:
                    if name in pick:
                        acc[name].append(position(fn(rec), C_TRUE) - X_LEAK)
            for name in pick:
                out[snr][name].append(float(np.sqrt(np.mean(
                    np.asarray(acc[name]) ** 2))))

    rows = []
    for snr in (10.0, -10.0):
        print("\n  SNR %+.0f dB   反射振幅 " % snr
              + "  ".join("%6.1f" % a for a in amps) + "   [位置誤差の RMS, m]")
        for name in pick:
            print("     %-24s " % name
                  + "  ".join("%6.3f" % v for v in out[snr][name]))
            rows.append(["%+.0f dB" % snr, name]
                        + ["%.3f" % v for v in out[snr][name]])

    hi_raw = out[10.0]["生の相関 + サブサンプル"][-1]
    hi_phat = out[10.0]["GCC-PHAT(帯域内)"][-1]
    lo_raw = out[-10.0]["生の相関 + サブサンプル"][-1]
    lo_phat = out[-10.0]["GCC-PHAT(帯域内)"][-1]
    print("\n  ★実測: 反射 0.8・SNR +10 dB では PHAT %.3f m vs 生 %.3f m "
          "(%.2f 倍)。" % (hi_phat, hi_raw, hi_phat / hi_raw))
    print("     反射 0.8・SNR -10 dB では PHAT %.3f m vs 生 %.3f m (%.2f 倍)。"
          % (lo_phat, lo_raw, lo_phat / lo_raw))

    figs.save_plot("reflection_sweep",
                   [("%s / %+.0f dB" % (n.replace("+ サブサンプル", ""), snr),
                     list(amps), out[snr][n])
                    for snr in (10.0, -10.0) for n in pick],
                   xlabel="反射の振幅(直達波を 1 として)",
                   ylabel="位置誤差の RMS [m]",
                   title="反射があるとき PHAT は勝つか")
    figs.save_table("reflection_table",
                    ["SNR", "手法"] + ["反射 %.1f" % a for a in amps], rows,
                    title="反射の掃引(位置誤差の RMS [m])")
    return {"amps": amps, "out": out}


# --------------------------------------------------------------------------- #
# 4) 音速 —— 相関はきれいなのに掘る場所が外れる                                 #
# --------------------------------------------------------------------------- #
def section_sound_speed() -> dict:
    print("\n" + "=" * 78)
    print("4) 対照群 —— (a) 音速が真値 (b) 10 %% 間違える (c) 管種が変わる")
    print("=" * 78)
    print("  ★予測: 音速の誤差は位置に**線形**に効く。"
          "Δx = (Δc/c)·(x - L/2)\n          —— 中点では 0、端に行くほど大きい。"
          "相関の形は 1 ミリも変わらない。")

    rec = make_records(10.0, SEED)
    tau_hat = tau_bandlimited(rec)
    cases = []
    for label, c_as in (("(a) 音速が真値 %.0f m/s" % C_TRUE, C_TRUE),
                        ("(b) 音速を +10 %% 誤る", 1.10 * C_TRUE),
                        ("(c) 音速を -10 %% 誤る", 0.90 * C_TRUE)):
        x_hat = position(tau_hat, c_as)
        cases.append((label, c_as, x_hat, x_hat - X_LEAK))
        print("   %-26s c = %7.1f m/s -> x = %7.3f m (%+7.3f m)"
              % (label, c_as, x_hat, x_hat - X_LEAK))
    pred = 0.10 * (X_LEAK - L_M / 2.0)
    print("   予測(+10 %%): %+0.3f m / 実測 %+0.3f m —— 差 %.4f m"
          % (pred, cases[1][3], abs(pred - cases[1][3])))

    # 音速の誤差を掃く / 漏水位置を振る
    fracs = np.linspace(-0.15, 0.15, 13)
    meas_far, meas_mid, pred_far = [], [], []
    rec_mid = make_records(10.0, SEED, x_leak=L_M / 2.0)
    tau_mid = tau_bandlimited(rec_mid)
    for fr in fracs:
        meas_far.append(position(tau_hat, C_TRUE * (1 + fr)) - X_LEAK)
        meas_mid.append(position(tau_mid, C_TRUE * (1 + fr)) - L_M / 2.0)
        pred_far.append(fr * (X_LEAK - L_M / 2.0))
    print("\n   ★中点の漏水(x = %.0f m)は音速を ±15 %% 間違えても "
          "誤差 %.4f m 以内。\n     同じ誤りが x = %.0f m では %.3f m。"
          "**音速の誤りは中点からの距離に比例する**。"
          % (L_M / 2.0, float(np.max(np.abs(meas_mid))), X_LEAK,
             float(np.max(np.abs(meas_far)))))

    # (c) 管種が途中で変わる
    print("\n   (c) 管種が %.0f m で変わる場合(鋳鉄 %.0f m/s -> 樹脂 %.0f m/s)"
          % (PIPE_MIXED[0][0], C_TRUE, C_PVC))
    rec_mx = make_records(10.0, SEED, pipe=PIPE_MIXED)
    tau_mx = tau_bandlimited(rec_mx)
    print("      真の τ = %.4f ms / 推定 τ = %.4f ms(**相関はきれいに立っている**)"
          % (1e3 * rec_mx["tau_true"], 1e3 * tau_mx))
    for c_as, tag in ((C_TRUE, "鋳鉄の音速を仮定"), (C_PVC, "樹脂の音速を仮定"),
                      (0.5 * (C_TRUE + C_PVC), "2 つの平均を仮定")):
        x_hat = position(tau_mx, c_as)
        print("      %-18s c = %6.1f -> x = %7.3f m (%+7.3f m)"
              % (tag, c_as, x_hat, x_hat - X_LEAK))
    print("      ★**どの音速を入れても %.0f m 付近**。τ ≈ 0 なので "
          "x = (L + c·0)/2 = L/2。\n         音速は掛け算の相手なので、"
          "**τ が 0 のときは何を掛けても直らない**。\n         これは"
          "パラメータの誤りではなく**モデルの誤り**(区間で音速が違う)。"
          % position(tau_mx, C_TRUE))

    # 漏水位置を管路全体に振って、3 つの条件を比べる
    xs = np.arange(6.0, L_M - 5.0, 4.0)
    ideal, wrong_c, mixed = [], [], []
    for x in xs:
        r = make_records(10.0, SEED, x_leak=float(x))
        t = tau_bandlimited(r)
        ideal.append(position(t, C_TRUE))
        wrong_c.append(position(t, 1.10 * C_TRUE))
        rm = make_records(10.0, SEED, x_leak=float(x), pipe=PIPE_MIXED)
        mixed.append(position(tau_bandlimited(rm), C_TRUE))
    err_ideal = float(np.max(np.abs(np.asarray(ideal) - xs)))
    err_wrong = float(np.max(np.abs(np.asarray(wrong_c) - xs)))
    err_mixed = float(np.max(np.abs(np.asarray(mixed) - xs)))
    print("\n   管路全体に漏水を振ったときの最大の外し [m]: "
          "(a) %.3f / (b) %.3f / (c) %.3f" % (err_ideal, err_wrong, err_mixed))

    figs.save_plot("sound_speed_error",
                   [("x = %.0f m(端寄り)実測" % X_LEAK, 100 * fracs, meas_far),
                    ("予測 (Δc/c)(x-L/2)", 100 * fracs, pred_far),
                    ("x = %.0f m(中点)実測" % (L_M / 2), 100 * fracs, meas_mid)],
                   xlabel="音速の誤り [%]", ylabel="掘る場所のずれ [m]",
                   title="音速の誤りは位置に線形に効く(中点では効かない)",
                   caption="相関の形も相関係数も一切変わらない。変わるのは"
                           "掘る場所だけ。")
    figs.save_plot("position_scan",
                   [("(a) 音速が真値", xs, ideal),
                    ("(b) 音速 +10 %", xs, wrong_c),
                    ("(c) 管種が %.0f m で変わる" % PIPE_MIXED[0][0], xs, mixed),
                    ("真値(対角線)", xs, xs)],
                   xlabel="真の漏水位置 [m]", ylabel="推定した掘る場所 [m]",
                   title="対照群 —— 3 つの条件で管路全体を走査",
                   caption="(c) は相関がきれいでも折れ曲がる。単一の音速では"
                           "どうやっても直せない。")
    return {"cases": cases, "pred": pred, "mixed_tau": tau_mx,
            "mixed_x": position(tau_mx, C_TRUE), "err": (err_ideal, err_wrong,
                                                         err_mixed),
            "mid_max": float(np.max(np.abs(meas_mid))),
            "far_max": float(np.max(np.abs(meas_far)))}


# --------------------------------------------------------------------------- #
# 5) 誤差の内訳 —— 1 つの数字に畳まない                                        #
# --------------------------------------------------------------------------- #
def section_budget(sw: dict, ss: dict) -> None:
    print("\n" + "=" * 78)
    print("5) 誤差を種類ごとに分ける(全部 [m]。足し合わせない)")
    print("=" * 78)
    ref = "帯域制限 + サブサンプル"
    i0 = sw["snrs"].index(0.0)
    rows = [
        ["量子化(整数ピーク)", "%.4f" % (QUANT_M / np.sqrt(12.0)),
         "c/(2 fs)/√12。標本化周期で決まる。サブサンプル補間で消える"],
        ["サブサンプル誤差", "%.4f" % sw["fine"][ref][i0],
         "SNR 0 dB の実測 RMS。CRLB %.4f m には %.0f 倍届かない"
         % (sw["crlb_num"][i0], sw["fine"][ref][i0] / sw["crlb_num"][i0])],
        ["ピークの取り違え", "%.1f" % (0.01 * sw["gross"][ref][-1]
                                      * float(np.sqrt(L_M ** 2 / 12.0))),
         "SNR %.0f dB で %.0f %% 起きる。起きると誤差は探索窓いっぱい"
         % (sw["snrs"][-1], sw["gross"][ref][-1])],
        ["音速の偏り(+10 %)", "%.3f" % abs(ss["cases"][1][3]),
         "(Δc/c)(x - L/2)。系統誤差なので平均しても消えない"],
        ["管種の変化(モデル誤り)", "%.3f" % abs(ss["mixed_x"] - X_LEAK),
         "どの単一音速を入れても直らない"],
    ]
    print("   %-24s %10s   %s" % ("誤差の種類", "大きさ [m]", "性質"))
    for r in rows:
        print("   %-24s %10s   %s" % (r[0], r[1], r[2]))
    print("\n  ★大きさの桁が違う: 量子化 %.0f mm、サブサンプル %.0f mm、"
          "音速 10 %% で %.1f m、管種の取り違えで %.0f m。"
          % (1e3 * QUANT_M / np.sqrt(12.0), 1e3 * sw["fine"][ref][i0],
             abs(ss["cases"][1][3]), abs(ss["mixed_x"] - X_LEAK)))
    print("     **相関を良くする努力は左の 2 つにしか効かない。**")
    figs.save_table("error_budget", ["誤差の種類", "大きさ [m]", "性質"], rows,
                    title="掘る場所の誤差の内訳(種類ごとに分けて数える)")


# --------------------------------------------------------------------------- #
# 6) 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("6) 道具の穴(この PoC を書いていて公開経路に無かったもの)")
    print("=" * 78)
    for name in ("gcc_phat", "time_delay_estimate", "cross_correlate_1d",
                 "group_delay", "tdoa_localize"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    print("  (a) 1-D の相互相関 / GCC(PHAT・ROTH・SCOT の重み)が無い。"
          "この PoC は 3-D 用の\n      correlation_score を (1,1,N) に潰して"
          "使い、PHAT だけ numpy で書いた。")
    print("  (b) 遅延推定そのもの(time_delay_estimate)と、TDOA から位置を"
          "出す口が無い。")
    print("  (c) 群遅延 op が無い。transfer_function の位相を自分で unwrap して"
          "最小二乗で\n      傾きを取った —— 位相の傾きは遅延そのものなので、"
          "族に入れる価値がある。")
    assert not hasattr(fs.ledger, "correlation_score_1d")
    print("  (d) correlation_score は 3-D 専用で、1-D 信号は (1,1,N) に"
          "整形して渡すしかない。\n      サブサンプルの相棒 refine_peak_newton"
          "も 27 近傍を要求するので 1-D では使えない。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("埋設管の漏水を音で位置決めする —— 伝わる速さを間違えると、掘る場所がずれる")
    print("=" * 78)

    z = section_scene_zero()
    sw = section_snr_cliff()
    section_reflection()
    ss = section_sound_speed()
    section_budget(sw, ss)
    section_tool_gaps()

    ref = "帯域制限 + サブサンプル"
    i0 = sw["snrs"].index(0.0)
    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 音速が真値なら SNR 0 dB で %.3f m まで当たる(CRLB %.4f m)。"
          % (sw["fine"][ref][i0], sw["crlb_num"][i0]))
    print("  * 崖は %s dB(予測 %.1f dB)。落ちるとピークの取り違えで"
          " %.0f m 級に飛ぶ。"
          % ("%+.0f" % sw["first"] if sw["first"] is not None else "?",
             sw["thr"], L_M / 4.0))
    print("  * 音速を 10 %% 間違えると %+.2f m。管種が途中で変わると %+.1f m で、"
          "\n    **どの単一音速でも直らない**。" % (ss["cases"][1][3],
                                                   ss["mixed_x"] - X_LEAK))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    assert sw["fine"][ref][i0] < 0.2, sw["fine"][ref][i0]
    assert sw["gross"][ref][0] == 0.0, sw["gross"][ref][0]
    assert abs(abs(ss["cases"][1][3]) - abs(ss["pred"])) < 0.05
    assert abs(ss["mixed_x"] - L_M / 2.0) < 1.0, ss["mixed_x"]
    assert ss["mid_max"] < 0.05 and ss["far_max"] > 2.0
    assert len(z["rows"]) == 6

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
