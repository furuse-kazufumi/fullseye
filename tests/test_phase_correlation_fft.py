# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""filters_freq.phase_correlation_fft の回帰の門(2026-10-06)。

0.4.0 までの既定(窓なし + 全白色化)は、帯域の限られた像の **周期的でない切り出し** で正しいずれを返さなかった
(真 (−2, −5) に (1, 0))。np.roll の周期的なずれでは厳密なので、それだけの門では見えなかった。原因は白色化:
信号の無い周波数のビン(切り出しの縁の漏れと丸め)が信号のあるビンと同じ重みになる。窓だけでは直らない。
既定を Hann 窓 + 半分の白色化に直し、旧の挙動は ``window=None, whitening=1.0`` で残した。
ここでは場面ごとにずれを 12 通り振り、既定が全部当たること・旧の挙動が罠を再現すること(否定の門は両側)を固定する。
"""
from __future__ import annotations

import numpy as np
import pytest

import filters_freq as FF


def _bandlimited(n, off_r, off_c, seed):
    """帯域制限した正弦波 120 本の和を (off_r, off_c) だけずらして標本化(補間なしの厳密な並進、周期的でない)。"""
    rng = np.random.default_rng(seed)
    f = rng.uniform(-0.2, 0.2, (120, 2))
    ph = rng.uniform(0, 2 * np.pi, 120)
    a = rng.uniform(0.3, 1.0, 120) / (1 + 20 * np.hypot(f[:, 0], f[:, 1]))
    i, j = np.mgrid[0:n, 0:n].astype(float)
    arg = 2 * np.pi * (f[:, 0, None, None] * (i + off_r) + f[:, 1, None, None] * (j + off_c)) + ph[:, None, None]
    return np.sum(a[:, None, None] * np.cos(arg), axis=0)


def _lowpass_scene(n, seed):
    big = np.random.default_rng(seed).normal(0, 1, (n + 40, n + 40))
    F = np.fft.fft2(big)
    fy, fx = np.meshgrid(np.fft.fftfreq(n + 40), np.fft.fftfreq(n + 40), indexing="ij")
    F[np.hypot(fy, fx) > 0.15] = 0
    return np.fft.ifft2(F).real


def _shifts():
    rng = np.random.default_rng(5)
    out = []
    while len(out) < 12:
        d = (int(rng.integers(-8, 9)), int(rng.integers(-8, 9)))
        if d != (0, 0):
            out.append(d)
    assert len(out) == 12
    return out


def _hit(r, d):
    # 返りは image1 の image2 に対するずれ: image2 = image1 を d だけ動かしたもの → (−d)
    return (r["row_shift"], r["col_shift"]) == (float(-d[0]), float(-d[1]))


def test_default_recovers_shift_on_non_periodic_bandlimited_crops_and_old_default_does_not():
    n = 64
    new_hits = old_hits = 0
    for k, d in enumerate(_shifts()):
        a = _bandlimited(n, 0.0, 0.0, 10 + k)
        b = _bandlimited(n, -d[0], -d[1], 10 + k)
        new_hits += _hit(FF.phase_correlation_fft(a, b), d)
        old_hits += _hit(FF.phase_correlation_fft(a, b, window=None, whitening=1.0), d)
    assert new_hits == 12, new_hits
    assert old_hits <= 2, old_hits                          # 0.4.0 の挙動は罠のまま(試作の実測 0 / 60)


def test_default_recovers_shift_on_lowpass_crops_and_old_default_does_not():
    n = 64
    new_hits = old_hits = 0
    for k, d in enumerate(_shifts()):
        L = _lowpass_scene(n, 40 + k)
        a = L[20:20 + n, 20:20 + n]
        b = L[20 - d[0]:20 - d[0] + n, 20 - d[1]:20 - d[1] + n]
        new_hits += _hit(FF.phase_correlation_fft(a, b), d)
        old_hits += _hit(FF.phase_correlation_fft(a, b, window=None, whitening=1.0), d)
    assert new_hits == 12, new_hits
    assert old_hits <= 2, old_hits


def test_periodic_roll_and_broadband_crop_stay_exact():
    n = 64
    a = _bandlimited(n, 0.0, 0.0, 3)
    big = np.random.default_rng(1).normal(0, 1, (n + 40, n + 40))
    for d in _shifts():
        b = np.roll(a, d, axis=(0, 1))
        assert _hit(FF.phase_correlation_fft(a, b), d)
        assert _hit(FF.phase_correlation_fft(a, b, window=None, whitening=1.0), d)
        A = big[20:20 + n, 20:20 + n]
        B = big[20 - d[0]:20 - d[0] + n, 20 - d[1]:20 - d[1] + n]
        assert _hit(FF.phase_correlation_fft(A, B), d)
    r = FF.phase_correlation_fft(a, a)
    assert (r["row_shift"], r["col_shift"]) == (0.0, 0.0) and r["window"] == "hann" and r["whitening"] == 0.5
    assert np.isfinite(r["correlation"]).all() and r["correlation"].shape == (n, n)


def test_bad_inputs_raise():
    a = np.zeros((16, 16))
    for kw in ({"window": "hamming"}, {"whitening": 1.5}, {"whitening": -0.1}, {"whitening": True}):
        with pytest.raises(ValueError):
            FF.phase_correlation_fft(a, a, **kw)
    with pytest.raises(ValueError):
        FF.phase_correlation_fft(a, np.zeros((16, 8)))
    with pytest.raises(ValueError):
        FF.phase_correlation_fft(np.zeros(16), np.zeros(16))
