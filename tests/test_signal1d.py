# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""signal1d のGTテスト: 点列の多項式/FFT/フィルタ/スプライン(開・閉曲線)。"""
import numpy as np
import pytest

import signal1d as S


def test_poly_fit_recovers_and_beats_constant():
    rng = np.random.default_rng(0)
    x = np.linspace(-3, 3, 120)
    true = 2 - 1.5 * x + 0.4 * x ** 2 - 0.1 * x ** 3
    y = true + rng.normal(0, 0.3, x.size)
    fit = S.poly_eval(S.poly_fit(x, y, 3), x)
    rmse = np.sqrt(np.mean((fit - true) ** 2))
    const = np.sqrt(np.mean((y.mean() - true) ** 2))
    assert rmse < 0.15 and rmse < 0.1 * const          # 正しい次数 >> 定数当てはめ


def test_fft_spectrum_finds_the_tones():
    N = 512
    t = np.arange(N)
    f1, f2 = 0.05, 0.18
    sig = np.sin(2 * np.pi * f1 * t) + 0.7 * np.sin(2 * np.pi * f2 * t)
    fr, mag = S.fft_spectrum(sig)
    peaks = sorted(fr[np.argsort(mag)[-2:]])
    assert abs(peaks[0] - f1) < 0.01 and abs(peaks[1] - f2) < 0.01


def test_lowpass_denoises_highpass_extracts():
    rng = np.random.default_rng(1)
    trend = np.sin(2 * np.pi * 0.01 * np.arange(400))
    noise = rng.normal(0, 0.5, 400)
    noisy = trend + noise
    lp = S.lowpass(noisy, cutoff=0.05)
    assert np.std(lp - trend) < 0.4 * np.std(noisy - trend)     # ノイズを落とす
    hp = S.highpass(noisy, cutoff=0.05)
    assert abs(np.corrcoef(hp, noise)[0, 1]) > 0.9              # 細部=ノイズを残す
    assert abs(np.corrcoef(hp, trend)[0, 1]) < 0.3             # トレンドは残さない


def test_bandpass_isolates_middle_tone():
    N = 600
    t = np.arange(N)
    sig = np.sin(2 * np.pi * 0.02 * t) + np.sin(2 * np.pi * 0.2 * t) + np.sin(2 * np.pi * 0.45 * t)
    mid = S.bandpass(sig, low=0.2, high=0.6)                    # ~0.2 cyc/sample = 0.4 of Nyquist
    fr, mag = S.fft_spectrum(mid)
    assert abs(fr[np.argmax(mag)] - 0.2) < 0.02                 # 中央トーンが優勢


def test_smooth_reduces_variance():
    rng = np.random.default_rng(2)
    y = np.zeros(200) + rng.normal(0, 1, 200)
    assert np.std(S.smooth(y, 11)) < np.std(y)


def test_spline_fit_interpolates_exactly():
    rng = np.random.default_rng(3)
    xs = np.sort(rng.uniform(0, 10, 25))
    ys = np.sin(xs)
    spl = S.spline_fit(xs, ys, smooth=0.0)
    assert np.abs(S.spline_eval(spl, xs) - ys).max() < 1e-9     # 全点を通る
    xn, yn = S.spline_resample(xs, ys, 200)
    assert np.abs(yn - np.sin(xn)).max() < 0.02                 # 真の曲線に近い


# --- 開曲線 / 閉曲線 の使い分け ---
def _circle(n=13, R=30, cx=50, cy=50):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([cx + R * np.cos(th), cy + R * np.sin(th)])


def test_closed_curve_wraps_open_curve_does_not():
    pts = _circle()
    rc = S.spline_curve_resample(pts, 120, closed=True)
    ro = S.spline_curve_resample(pts, 120, closed=False)
    seam_closed = np.hypot(*(rc[0] - rc[-1]))
    seam_open = np.hypot(*(ro[0] - ro[-1]))
    assert seam_closed < 3.0 < seam_open                       # 閉は滑らかに閉じ、開は隙間


def test_closed_curve_stays_on_the_circle():
    pts = _circle()
    rc = S.spline_curve_resample(pts, 200, closed=True)
    r = np.hypot(rc[:, 0] - 50, rc[:, 1] - 50)
    assert r.std() < 0.5 and abs(r.mean() - 30) < 0.5          # 円を保持


def test_curve_model_is_polygon_plus_attributes():
    m = S.spline_curve_fit(_circle(), closed=True)
    assert set(m) == {"points", "closed", "tck", "u", "dim"}    # ポリゴン点列 + closed 等の属性
    assert m["closed"] is True and m["dim"] == 2
    # 制御点の parameter u で評価すると制御点に戻る(補間)
    assert np.abs(S.spline_curve_eval(m, m["u"]) - m["points"]).max() < 1e-6


def test_spline_curve_works_in_3d():
    t = np.linspace(0, 4 * np.pi, 40)
    helix = np.column_stack([np.cos(t), np.sin(t), t / 6.0])
    m = S.spline_curve_fit(helix, closed=False)
    assert m["dim"] == 3
    rs = S.spline_curve_resample(helix, 300, closed=False)
    assert rs.shape == (300, 3)
    assert np.hypot(rs[:, 0], rs[:, 1]).std() < 0.05           # ヘリックス上に乗る(半径一定)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        S.poly_fit([1, 2, 3], [1, 2], 1)                       # 長さ不一致
    with pytest.raises(ValueError):
        S.poly_fit(np.arange(3), np.arange(3), 5)              # degree>=点数
    with pytest.raises(ValueError):
        S.bandpass(np.zeros(50), low=0.5, high=0.2)            # low>=high
    with pytest.raises(ValueError):
        S.spline_curve_fit(np.zeros((3, 2)))                   # <4点
