# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""spectral_tour — FFT では足りないスペクトル推定を、FFT 的なやり方と並べて見る(MUSIC / ESPRIT / Lomb–Scargle)。

    py -3.11 examples/spectral_tour.py

【この例が示すこと】
1. **到来方向の超分解能** —— 8 素子のアンテナ列に、6° しか離れていない 2 つの電波が来る。普通のビームフォーマ
   (遅延和 = 空間の FFT)の分解能はアンテナの長さで決まり(ビーム幅 ≈ 12.7°)、2 つは 1 つの山に融ける。
   MUSIC は「雑音だけの方向」を共分散から割り出し、その直交方向として 2 本の鋭い峰を立てる。ESPRIT は格子を使わずに
   角度を直接解く。ただし前提が崩れる(2 つが同じ信号の反射 = 相関している)と MUSIC も割れない —— それも並べる。
2. **時刻がばらばらな観測の周期** —— 観測の時刻が格子に乗っていない(天体の光度曲線、イベント駆動のセンサー)と、
   FFT は「等間隔」を前提にしているので使えない。ありがちな間違いは**時刻を無視して並び順のまま FFT する**こと ——
   周波数の目盛りが平均間隔で決まるので、峰が真の周波数からずれる。Lomb–Scargle は観測した時刻のまま周期を探す。
   等間隔なら FFT の周期図と一致する(恒等式)。
   (★最初は「格子の上の欠測を 0 で埋めた FFT」を失敗例にしたが、図を見るとそれも正しい周波数に峰を立てていた
   —— 格子が残っていれば周期は残る。失敗例として嘘だったので差し替えた、2026-10-03。)

【グラウンドトゥルース】電波の到来角(10°, 16°)と時系列の周波数(0.137)は自分で決めた真値。
Lomb–Scargle = 周期図(等間隔)は Scargle 1982 の恒等式。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.<名前>)から呼ぶ


def _bartlett_db(X, grid):
    """遅延和(Bartlett)ビームフォーマの空間スペクトル a(θ)ᴴ R a(θ) を dB で(比較用の素朴な方法)。"""
    M = X.shape[0]
    R = X @ X.conj().T / X.shape[1]
    A = np.exp(-2j * math.pi * 0.5 * np.arange(M)[:, None] * np.sin(np.radians(grid))[None, :])
    P = np.real(np.sum(A.conj() * (R @ A), axis=0))
    return 10 * np.log10(P / P.max())


def _peaks(y, x, lo, hi):
    pk = np.flatnonzero((y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:])) + 1
    return x[pk][(x[pk] > lo) & (x[pk] < hi)]


def run() -> dict:
    t0 = time.perf_counter()
    out = {}
    truth = (10.0, 16.0)

    # ---- 1. 到来方向 ------------------------------------------------------------------ #
    X = fs.ula_snapshots(truth, 8, 400, snr_db=15, seed=0)
    mus = fs.music_doa(X)                                       # 波源の数は MDL で推定させる
    esp = fs.esprit_doa(X)
    grid = mus["grid_deg"]
    bart = _bartlett_db(X, grid)
    b_pk = _peaks(bart, grid, 0, 26)
    m_pk = _peaks(mus["pseudo_spectrum_db"], grid, 0, 26)
    print("1) 到来方向(真値 %s°、8 素子、ビーム幅 ≈ 12.7°): 遅延和の峰 %s / MUSIC %s(波源 %d 個と推定)/ ESPRIT %s"
          % (truth, np.round(b_pk, 2), np.round(m_pk, 2), mus["n_sources"], np.round(esp["doa_deg"], 2)))
    assert len(b_pk) == 1 and len(m_pk) == 2 and mus["n_sources"] == 2
    assert np.allclose(esp["doa_deg"], truth, atol=0.5) and np.allclose(m_pk, truth, atol=0.5)
    # 前提が崩れる例: 同じ信号の反射(相関した 2 波)
    s = (np.random.default_rng(3).normal(size=400) + 1j * np.random.default_rng(4).normal(size=400)) / math.sqrt(2)
    A = np.exp(-2j * math.pi * 0.5 * np.arange(8)[:, None] * np.sin(np.radians(truth))[None, :])
    Xc = A @ np.vstack([s, 0.8 * s]) + 0.03 * (np.random.default_rng(5).normal(size=(8, 400))
                                               + 1j * np.random.default_rng(6).normal(size=(8, 400)))
    coh = fs.music_doa(Xc, 2)
    c_pk = _peaks(coh["pseudo_spectrum_db"], grid, 0, 26)
    print("   相関した 2 波(反射)では MUSIC の峰が %d 本 —— 部分空間の前提が崩れる" % len(c_pk))
    assert len(c_pk) < 2
    out.update(bartlett_peaks=len(b_pk), music_peaks=len(m_pk), esprit=list(np.round(esp["doa_deg"], 4)))

    # ---- 2. 不等間隔の周期 --------------------------------------------------------------- #
    rng = np.random.default_rng(1)
    f_true = 0.137
    # 時刻は格子に乗らない: 観測の間隔が 0.2〜2.6 のばらばら、途中に長い空白(30〜55)
    gaps = rng.uniform(0.2, 2.6, 120)
    t = np.cumsum(gaps)
    t = t[(t < 30) | (t > 55)]
    y = np.sin(2 * math.pi * f_true * t) + 0.4 * rng.normal(size=t.size)
    f = np.linspace(0.005, 0.8, 4000)
    ls = fs.lomb_scargle(t, y, f)
    mean_dt = float((t[-1] - t[0]) / (t.size - 1))
    F = np.abs(np.fft.rfft(y - y.mean())) ** 2                    # 時刻を無視して並び順のまま FFT(ありがちな間違い)
    ff = np.fft.rfftfreq(t.size, mean_dt)
    naive_peak = float(ff[1:][np.argmax(F[1:])])
    print("2) 時刻がばらばら(%d 点、平均間隔 %.2f、空白あり、真の周波数 %.3f): Lomb–Scargle の峰 %.4f / "
          "並び順のまま FFT の峰 %.4f" % (t.size, mean_dt, f_true, ls["peak_freq"], naive_peak))
    e_ls, e_naive = abs(ls["peak_freq"] - f_true), abs(naive_peak - f_true)
    assert e_ls < 1e-3 and e_naive > 10 * e_ls                  # 実測: 0.0002 と 0.008(40 倍)
    # 等間隔なら周期図と一致(恒等式)
    k = np.arange(1, 32)
    tt = np.arange(64) * 0.5
    yy = np.sin(2 * math.pi * 0.37 * tt) + 0.3 * rng.normal(size=64)
    eq = float(np.abs(fs.lomb_scargle(tt, yy, k / 32.0)["power"]
                      - np.abs(np.fft.fft(yy - yy.mean()))[1:32] ** 2 / 64).max())
    assert eq < 1e-10
    out.update(ls_peak=ls["peak_freq"], ls_equals_periodogram=eq)

    # ---- 図 ---------------------------------------------------------------------------- #
    if figs.enabled():
        sel = (grid > -20) & (grid < 45)
        figs.save_plot("doa",
                       [("遅延和(空間の FFT)", grid[sel], bart[sel]),
                        ("MUSIC", grid[sel], np.maximum(mus["pseudo_spectrum_db"][sel], -40)),
                        ("真の向き 10°", [truth[0]] * 2, [-40, 0]), ("真の向き 16°", [truth[1]] * 2, [-40, 0])],
                       styles=[None, None, "dashed", "dashed"], ylim=(-42, 2),
                       xlabel="到来角 θ [度]", ylabel="強さ [dB]",
                       title="6° 離れた 2 つの電波 —— 遅延和は 1 つに融け、MUSIC は 2 本に割れる",
                       caption="8 素子のアンテナ列のビーム幅は約 12.7°。それより近い 2 波は遅延和では 1 つの山(13°)になる。"
                               "MUSIC は真の向き(破線)に 2 本の鋭い峰を立てる。ESPRIT は格子なしで %.2f° と %.2f°。"
                               % tuple(esp["doa_deg"]))
        figs.save_plot("doa_coherent",
                       [("MUSIC(無相関の 2 波)", grid[sel], np.maximum(mus["pseudo_spectrum_db"][sel], -40)),
                        ("MUSIC(同じ信号の反射 = 相関した 2 波)", grid[sel], np.maximum(coh["pseudo_spectrum_db"][sel], -40))],
                       ylim=(-42, 2), xlabel="到来角 θ [度]", ylabel="強さ [dB]",
                       title="前提が崩れると —— 反射(相関した波)では MUSIC も割れない",
                       caption="MUSIC は「波どうしが無相関」を前提に共分散を部分空間に分ける。同じ信号が 2 方向から来る"
                               "(壁の反射)と共分散の階数が 1 に潰れ、峰が 2 本に割れない。")
        figs.save_plot("lomb_scargle",
                       [("Lomb–Scargle(不等間隔のまま)", f, ls["power"] / ls["power"].max()),
                        ("時刻を無視して並び順のまま FFT", ff[ff <= 0.8], (F / F.max())[ff <= 0.8]),
                        ("真の周波数 %.3f" % f_true, [f_true] * 2, [0, 1])],
                       styles=[None, None, "dashed"], xlim=(0, 0.8),
                       xlabel="周波数", ylabel="強さ(最大で正規化)",
                       title="時刻がばらばらな観測の周期 —— 並び順のまま FFT すると峰がずれる",
                       caption="FFT は等間隔を前提にしている。時刻を無視して並び順のまま FFT すると、周波数の目盛りが"
                               "平均間隔(%.2f)で決まり、峰が %.3f にずれる。Lomb–Scargle は観測した時刻のまま当てはめるので、"
                               "真の周波数(破線)に峰が立つ。" % (mean_dt, naive_peak))
        tl = np.linspace(t[0], t[-1], 2000)
        figs.save_plot("samples",
                       [("観測した点", t, y), ("真の信号", tl, np.sin(2 * math.pi * f_true * tl))],
                       kinds=["scatter", "line"], styles=[None, "dashed"],
                       xlabel="時刻", ylabel="値", title="観測の時刻がばらばら —— 間隔は 0.2〜2.6、30〜55 は空白",
                       caption="この点だけから周期 1/%.3f ≈ %.1f を当てる。" % (f_true, 1 / f_true))
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  spectral_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
