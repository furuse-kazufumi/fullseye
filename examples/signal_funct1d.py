# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""signal_funct1d — 減衰振動のセンサー信号を HALCON funct_1d ファミリで解析する。

    py -3.11 examples/signal_funct1d.py

【用途(分かりやすく)】
打撃試験・振動計のような「減衰しながら振動する」1D センサー信号を、funct1d の
HALCON 対応 op だけで料理する: 平滑化 → 極値で周期推定 → ゼロ交差で半周期 →
微分/積分の往復 → ピーク包絡線から減衰時定数 → 相互相関で遅延推定。

【グラウンドトゥルース(beat-the-null)】
信号は y(t) = exp(-t/τ)·sin(2πft) + ノイズ を自分で合成するので、周期 1/f、
半周期 1/(2f)、時定数 τ、遅延サンプル数がすべて解析的に分かっている。
各推定値がその真値に一致することを assert する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import funct1d as F  # noqa: E402


def main():
    rng = np.random.default_rng(0)

    # ---- 合成センサー信号(真値が既知) ---------------------------------- #
    dt, f0, tau = 0.002, 5.0, 0.4          # 2ms sampling, 5 Hz, τ=0.4s
    t = np.arange(0.0, 1.2, dt)            # 600 サンプル
    clean = np.exp(-t / tau) * np.sin(2 * np.pi * f0 * t)
    noisy = F.create_funct_1d_array(clean + rng.normal(0, 0.02, t.size))
    n = F.num_points_funct_1d(noisy)
    print(f"信号: {n} サンプル, x範囲={F.x_range_funct_1d(noisy)}, "
          f"y範囲=({F.y_range_funct_1d(noisy)[0]:.3f}, {F.y_range_funct_1d(noisy)[1]:.3f})")

    # ---- 1) 平滑化はノイズを実測で減らす(gauss と mean の両方) ---------- #
    sm = F.smooth_funct_1d_gauss(noisy, sigma=3.0)
    sm_mean = F.smooth_funct_1d_mean(noisy, size=7, iterations=2)
    err_raw = F.distance_funct_1d(noisy, clean, mode="mean")
    err_sm = F.distance_funct_1d(sm, clean, mode="mean")
    err_mn = F.distance_funct_1d(sm_mean, clean, mode="mean")
    print(f"平滑化: 平均誤差 生={err_raw:.4f} → gauss={err_sm:.4f} / mean={err_mn:.4f}")
    assert err_sm < 0.5 * err_raw and err_mn < 0.7 * err_raw

    # 減衰末尾(t>0.9s は振幅 ~0.1 未満)はノイズが極値を偽造するので、
    # SNR が十分な最初の 0.9 秒だけを周期・包絡線解析に使う(honest な窓選択)。
    win = int(0.9 / dt)
    sm_w, t_w = sm[:win], t[:win]

    # ---- 2) 極値の間隔 → 周期(真値 1/f0 = 0.2 s) ----------------------- #
    ext = F.local_min_max_funct_1d(sm_w)
    peaks = ext["max"]
    period = float(np.mean(np.diff(peaks))) * dt
    print(f"周期推定: 極大 {len(peaks)} 個, 間隔平均 {period:.4f} s(真値 {1 / f0:.4f} s)")
    assert abs(period - 1 / f0) < 0.05 / f0            # 5% 以内

    # ---- 3) ゼロ交差の間隔 → 半周期(真値 1/(2f0) = 0.1 s) -------------- #
    zc = F.zero_crossings_funct_1d(sm_w)
    half = float(np.mean(np.diff(zc))) * dt
    print(f"半周期推定: ゼロ交差 {len(zc)} 個, 間隔平均 {half:.4f} s(真値 {1 / (2 * f0):.4f} s)")
    assert abs(half - 1 / (2 * f0)) < 0.05 / (2 * f0)

    # ---- 4) 微分と積分は往復で恒等(∫f' = f - f(0)) --------------------- #
    dsm = F.derivate_funct_1d(sm_w)
    back = F.integrate_funct_1d(dsm)
    round_err = F.distance_funct_1d(back, sm_w - sm_w[0], mode="max")
    print(f"微分→積分の往復: 最大誤差 {round_err:.2e}(信号振幅 ~1)")
    assert round_err < 5e-3
    # 極大点では微分 ≈ 0(1次条件)
    assert float(np.max(np.abs(dsm[peaks]))) < 0.02 * float(np.max(np.abs(dsm)))

    # ---- 5) ピーク包絡線 → 減衰時定数 τ(真値 0.4 s) -------------------- #
    env = F.abs_funct_1d(sm_w)
    peak_amp = np.array([F.get_pair_funct_1d(env, int(i))[1] for i in peaks])
    slope = np.polyfit(t_w[peaks], np.log(peak_amp), 1)[0]  # log 包絡は直線, 傾き -1/τ
    tau_est = -1.0 / slope
    print(f"減衰時定数: τ推定 {tau_est:.3f} s(真値 {tau} s)")
    assert abs(tau_est - tau) < 0.2 * tau              # 20% 以内

    # ---- 6) 相互相関で既知の遅延を復元(真値 25 サンプル) ---------------- #
    y1 = sm[:400]
    y2 = sm[25:425]                                    # y2[i] = y1[i+25] → shift=+25
    m = F.match_funct_1d_trans(y1, y2)
    print(f"遅延推定: shift={m['shift']} サンプル(真値 25), score={m['score']:.3f}")
    assert m["shift"] == 25
    assert F.distance_funct_1d(y1, y1) == 0.0          # 距離の恒等
    assert F.distance_funct_1d(y1, y2) == F.distance_funct_1d(y2, y1)  # 対称性

    # ---- 7) 再標本化・単位変換・補間読み出し ------------------------------ #
    half_rate = F.sample_funct_1d(sm, step=2)          # 4ms レートへ間引き
    mv = F.scale_y_funct_1d(sm, mult=1000.0)           # V → mV
    at_peak = F.get_y_value_funct_1d(sm, float(peaks[0]))
    pairs = F.funct_1d_to_pairs(half_rate)
    print(f"再標本化: {F.num_points_funct_1d(half_rate)} サンプル(1/2), "
          f"最初のピーク値 {at_peak:.3f} V = {F.get_y_value_funct_1d(mv, float(peaks[0])):.1f} mV, "
          f"pairs 形状 {pairs.shape}")
    assert F.num_points_funct_1d(half_rate) == (n + 1) // 2
    assert abs(F.get_y_value_funct_1d(mv, float(peaks[0])) - 1000.0 * at_peak) < 1e-9
    assert pairs.shape == (half_rate.size, 2)

    print("\nPASS: 合成した減衰振動から、平滑化でノイズを実測で減らし、極値で周期・"
          "ゼロ交差で半周期・包絡線で時定数・相互相関で遅延を、すべて既知の真値どおりに復元した。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
