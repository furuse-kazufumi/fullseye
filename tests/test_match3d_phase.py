# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""match3d.match_phase_3d の回帰の門(2026-10-06、filters_freq.phase_correlation_fft と同じ罠)。

0.4.0 までの既定(窓なし + 全白色化)は、帯域の限られた volume の **周期的でない切り出し** で正しいずれを返さなかった
(低域通過した 32³ の切り出しでずれ 10 通りが 0 / 10)。np.roll の周期的なずれでは厳密なので、それだけの門(test_match3d)では
見えなかった。既定を Tukey 窓(α 0.5)+ |R|^0.25 の白色化に直し、旧の挙動は ``window=None, whitening=1.0`` で残した。
ここでは場面ごとにずれを 10 通り振り、既定が当たること・旧の挙動が罠を再現すること(否定の門は両側)を固定する。torch は要らない。
"""
from __future__ import annotations

import numpy as np
import pytest

import match3d as X


def _lowpass(shape, seed, fc=0.15):
    big = np.random.default_rng(seed).normal(0, 1, shape)
    F = np.fft.fftn(big)
    f = np.meshgrid(*[np.fft.fftfreq(s) for s in shape], indexing="ij")
    F[np.sqrt(sum(x * x for x in f)) > fc] = 0
    return np.fft.ifftn(F).real


def _shifts(m, flat=False, k=10, seed=5):
    rng = np.random.default_rng(seed)
    out = []
    while len(out) < k:
        d = tuple(int(x) for x in rng.integers(-m, m + 1, 3))
        if flat:
            d = (0, d[1], d[2])
        if d != (0, 0, 0):
            out.append(d)
    assert len(out) == k
    return out


def _crops(L, o, shape, d):
    """L の o からの切り出し a と、d だけ手前から切った b(b(x) = a(x − d)、周期的でない)。"""
    sl_a = tuple(slice(o[i], o[i] + shape[i]) for i in range(3))
    sl_b = tuple(slice(o[i] - d[i], o[i] - d[i] + shape[i]) for i in range(3))
    return L[sl_a], L[sl_b]


def _old(a, b):
    """0.4.0 の式そのもの(窓なし、R/(|R| + 1e-9))。"""
    A = np.fft.fftn(np.asarray(a, np.float32)); B = np.fft.fftn(np.asarray(b, np.float32))
    R = A * B.conj()
    r = np.fft.ifftn(R / (np.abs(R) + 1e-9)).real
    pk = np.unravel_index(int(np.argmax(r)), r.shape)
    return tuple(int(p - s if p > s // 2 else p) for p, s in zip(pk, r.shape))


def test_default_recovers_shift_on_non_periodic_lowpass_volume_crops_and_old_default_does_not():
    shape, pad = (32, 32, 32), 5
    new = old = 0
    for k, d in enumerate(_shifts(3)):
        L = _lowpass(tuple(s + 2 * pad for s in shape), 40 + k)
        a, b = _crops(L, (pad, pad, pad), shape, d)
        want = tuple(-x for x in d)                             # np.roll(b, want) ≈ a
        new += X.match_phase_3d(a, b) == want
        old += X.match_phase_3d(a, b, window=None, whitening=1.0) == want
    assert new == 10, new
    assert old <= 1, old                                        # 0.4.0 の挙動は罠のまま(実測 0 / 10)


def test_default_recovers_shift_on_2d_crops_passed_as_1_h_w_and_old_default_does_not():
    """(1, H, W) で 2-D の像を通す使い方(poc_change_detection_misreg)。長さ 8 未満の軸には窓を掛けない。"""
    shape, pad = (1, 64, 64), 8
    new = old = 0
    for k, d in enumerate(_shifts(6, flat=True)):
        L = _lowpass((1, 64 + 2 * pad, 64 + 2 * pad), 60 + k)
        a, b = _crops(L, (0, pad, pad), shape, d)
        want = tuple(-x for x in d)
        new += X.match_phase_3d(a, b) == want
        old += X.match_phase_3d(a, b, window=None, whitening=1.0) == want
    assert new == 10, new
    assert old <= 2, old


def test_periodic_roll_and_broadband_crop_stay_exact_and_old_path_is_bit_identical():
    shape, pad = (32, 32, 32), 5
    for k, d in enumerate(_shifts(3)):
        a = _lowpass(shape, 80 + k)
        b = np.roll(a, d, axis=(0, 1, 2))
        want = tuple(-x for x in d)
        assert X.match_phase_3d(a, b) == want                       # 周期的なずれ(辺の 1 割)は既定でも厳密
        assert X.match_phase_3d(a, b, window=None, whitening=1.0) == want
        W = np.random.default_rng(k).normal(0, 1, tuple(s + 2 * pad for s in shape))
        wa, wb = _crops(W, (pad, pad, pad), shape, d)
        assert X.match_phase_3d(wa, wb) == want                     # 広帯域の切り出しは新旧とも当たる
        assert X.match_phase_3d(wa, wb, window=None, whitening=1.0) == want
        L = _lowpass(tuple(s + 2 * pad for s in shape), 40 + k)
        la, lb = _crops(L, (pad, pad, pad), shape, d)
        assert X.match_phase_3d(la, lb, window=None, whitening=1.0) == _old(la, lb)   # 旧の挙動は 0.4.0 の式と同じ答え


def test_large_shift_in_a_small_volume_is_why_the_default_is_tukey_and_quarter_whitening():
    """32³ でずれ ±6(辺の 2 割)は重なりが半分ほどで、窓が 3 軸で重なりを削る。2-D の既定(Hann + 0.5)をそのまま使うと周期的なずれも
    低域の切り出しも 3 / 10、既定(Tukey α 0.5 + 0.25)は 8 / 10・8 / 10(実測)。旧の挙動は周期的なずれだけ 10 / 10、切り出しは 0 / 10。"""
    shape, pad = (32, 32, 32), 6
    hit = {"default": [0, 0], "hann05": [0, 0], "old": [0, 0]}
    cfg = {"default": {}, "hann05": {"window": "hann", "whitening": 0.5}, "old": {"window": None, "whitening": 1.0}}
    for k, d in enumerate(_shifts(6)):
        want = tuple(-x for x in d)
        a = _lowpass(shape, 80 + k)
        la, lb = _crops(_lowpass(tuple(s + 2 * pad for s in shape), 40 + k), (pad, pad, pad), shape, d)
        for nm, kw in cfg.items():
            hit[nm][0] += X.match_phase_3d(a, np.roll(a, d, axis=(0, 1, 2)), **kw) == want
            hit[nm][1] += X.match_phase_3d(la, lb, **kw) == want
    assert hit["default"][0] >= 7 and hit["default"][1] >= 7, hit
    assert hit["hann05"][0] <= 5 and hit["hann05"][1] <= 5, hit
    assert hit["old"][0] == 10 and hit["old"][1] <= 1, hit


def test_hann_and_cross_correlation_options_and_broken_inputs_fail_closed():
    a = _lowpass((24, 24, 24), 3)
    b = np.roll(a, (2, -1, 1), axis=(0, 1, 2))
    assert X.match_phase_3d(a, b, window="hann", whitening=0.0) == (-2, 1, -1)
    for kw in ({"window": "Tukey"}, {"window": "hanning"}, {"whitening": 1.5}, {"whitening": -0.1}, {"whitening": True},
               {"whitening": float("nan")}):
        with pytest.raises(ValueError):
            X.match_phase_3d(a, b, **kw)
    with pytest.raises(ValueError):
        X.match_phase_3d(a, b[:-1])
