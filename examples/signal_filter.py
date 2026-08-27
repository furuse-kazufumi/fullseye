# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""signal_filter — 計測点列を多項式近似・周波数分析・ローパス/ハイパスで処理する。

    py -3.11 examples/signal_filter.py

【用途(分かりやすく)】
センサやプロファイルの1D計測列を手軽に扱う。トレンドを多項式で抜き出し、含まれる
周期成分をフーリエで数え、ローパスでノイズを落とし、ハイパスで細部・変動だけ残す。

【グラウンドトゥルース(beat-the-null)】
1. 既知の多項式+ノイズを poly_fit で復元 → 真の多項式に近く、定数当てはめを大きく下回る。
2. 2本の正弦波を混ぜた信号の fft_spectrum が、ちょうどその2周波数にピークを出す。
3. トレンド+高周波ノイズを lowpass するとトレンドに近づき(生信号より誤差が小さい)、
   highpass はノイズ側だけを残す(トレンドとは無相関)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import signal1d as S  # noqa: E402


def main():
    rng = np.random.default_rng(0)

    # 1) 多項式近似(トレンド抽出)
    x = np.linspace(-3, 3, 160)
    true_poly = 2 - 1.5 * x + 0.4 * x ** 2 - 0.1 * x ** 3
    y = true_poly + rng.normal(0, 0.3, x.size)
    fit = S.poly_eval(S.poly_fit(x, y, 3), x)
    rmse = float(np.sqrt(np.mean((fit - true_poly) ** 2)))
    const = float(np.sqrt(np.mean((y.mean() - true_poly) ** 2)))
    print(f"多項式近似: 復元rmse={rmse:.3f}(ノイズ0.3)、定数当てはめrmse={const:.3f}")
    assert rmse < 0.15 and rmse < 0.1 * const

    # 2) フーリエで周期成分を数える
    n = 512
    t = np.arange(n)
    f1, f2 = 0.05, 0.18
    tones = np.sin(2 * np.pi * f1 * t) + 0.7 * np.sin(2 * np.pi * f2 * t)
    fr, mag = S.fft_spectrum(tones)
    peaks = sorted(fr[np.argsort(mag)[-2:]])
    print(f"フーリエ: 検出ピーク周波数={[round(p, 3) for p in peaks]}(真値 {f1}, {f2})")
    assert abs(peaks[0] - f1) < 0.01 and abs(peaks[1] - f2) < 0.01

    # 3) ローパス/ハイパスで遅い成分と速い成分を分ける
    trend = np.sin(2 * np.pi * 0.01 * np.arange(400))
    noise = rng.normal(0, 0.5, 400)
    noisy = trend + noise
    lp = S.lowpass(noisy, cutoff=0.05)
    hp = S.highpass(noisy, cutoff=0.05)
    print(f"ローパス: トレンド誤差 {np.std(lp - trend):.3f}(生信号 {np.std(noisy - trend):.3f})")
    print(f"ハイパス: ノイズとの相関 {abs(np.corrcoef(hp, noise)[0, 1]):.2f} / "
          f"トレンドとの相関 {abs(np.corrcoef(hp, trend)[0, 1]):.2f}")
    assert np.std(lp - trend) < 0.4 * np.std(noisy - trend)
    assert abs(np.corrcoef(hp, noise)[0, 1]) > 0.9 and abs(np.corrcoef(hp, trend)[0, 1]) < 0.3

    print("\nPASS: 点列を多項式で近似し(定数を大きく上回る)、フーリエで周期成分を正しく数え、"
          "ローパスでノイズを落とし・ハイパスで細部だけを残せた。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
