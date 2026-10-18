# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""kuwahara / xdog の門(外部真値: 第 2 実装・閉形式・独立な FFT 経路)。

* kuwahara: 総当たりの参照実装(窓ごとに ``np.var`` / ``np.mean``)と 1e-12 で一致。
  ランダム入力と構造入力(段差・縞・市松・円・勾配)で、半径を振る。縁を保つ性質は
  閉形式で: 雑音なしの段差は**そっくりそのまま**(窓が自分の側に必ず 1 つある)、
  雑音つきでは平坦部の雑音が ``1/(r+1)`` 程度へ落ち、段差は ``gaussian`` より保たれる。
* xdog: ``tau = 1`` かつ ``phi`` を無限大にすると ``D >= eps`` の二値(DoG の符号)。
  ``D`` は FFT による独立なガウシアン(同じ打ち切りの核)と一致。

壊して確かめる探針: 象限の重なりを外した版は参照と合わない / ``k`` を変えた版は
FFT の参照と合わない。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import fullseye  # noqa: E402
import ops  # noqa: E402


def _kuwahara_bruteforce(x, r):
    """第 2 実装: 画素ごとに 4 つの窓を切り出して ``np.var`` / ``np.mean`` を直接取る。"""
    H, W = x.shape
    xp = np.pad(x, r, mode="edge")
    out = np.empty_like(x)
    for y in range(H):
        for xx in range(W):
            cy, cx = y + r, xx + r
            wins = (xp[cy - r:cy + 1, cx - r:cx + 1], xp[cy - r:cy + 1, cx:cx + r + 1],
                    xp[cy:cy + r + 1, cx - r:cx + 1], xp[cy:cy + r + 1, cx:cx + r + 1])
            vs = [round(float(np.var(w)), ops._KUWAHARA_TIE_DIGITS) for w in wins]
            out[y, xx] = float(np.mean(wins[int(np.argmin(vs))]))
    return out


def _inputs():
    rng = np.random.default_rng(20261018)
    yy, xx = np.mgrid[0:37, 0:41]
    step = np.where(xx < 20, 0.2, 0.8).astype(np.float64)
    stripes = (0.5 + 0.5 * np.sin(xx * 0.9)).astype(np.float64)
    checker = (((yy // 3) + (xx // 3)) % 2).astype(np.float64)
    disc = (((yy - 18) ** 2 + (xx - 20) ** 2) < 90).astype(np.float64) * 0.7 + 0.1
    ramp = ((xx / 40.0 + yy / 72.0) / 1.5).astype(np.float64)
    return {
        "random": rng.random((37, 41)),
        "random_odd": rng.random((23, 17)),
        "step": step, "stripes": stripes, "checker": checker, "disc": disc, "ramp": ramp,
    }


def _a_for_radius(r):
    return (r - 1) / 9.0


@pytest.mark.parametrize("r", [1, 2, 3, 5, 8])
def test_kuwahara_matches_bruteforce(r):
    for name, x in _inputs().items():
        got = fullseye.apply(x, "kuwahara", _a_for_radius(r), 0.0)
        ref = _kuwahara_bruteforce(x, r)
        assert np.abs(got - ref).max() < 1e-12, (name, r, np.abs(got - ref).max())


def test_kuwahara_radius_knob_mapping():
    assert [ops._kuwahara_radius(a) for a in (0.0, 1.0, 0.5)] == [1, 10, 6]
    assert ops._kuwahara_radius(-3) == 1 and ops._kuwahara_radius(7) == 10


def test_kuwahara_noise_free_step_is_exactly_preserved():
    """閉形式: 段差のどちら側の画素にも、自分の側だけの窓(分散 0)が 1 つある。"""
    x = _inputs()["step"]
    for r in (1, 3, 6, 10):
        y = fullseye.apply(x, "kuwahara", _a_for_radius(r), 0.0)
        assert np.abs(y - x).max() < 1e-12, r


def test_kuwahara_smooths_flats_but_keeps_the_step_sharper_than_gaussian():
    from scipy import ndimage
    rng = np.random.default_rng(7)
    x = np.zeros((64, 64))
    x[:, :32] = 0.25
    x[:, 32:] = 0.75
    xn = np.clip(x + 0.03 * rng.standard_normal(x.shape), 0, 1)
    for r in (2, 4, 5):
        y = fullseye.apply(xn, "kuwahara", _a_for_radius(r), 0.0)
        left = (slice(16, 48), slice(2, 24))
        ratio = y[left].std() / xn[left].std()
        assert ratio < 1.5 / (r + 1), (r, ratio)             # 平坦部は 1/(r+1) 程度まで均される
        jump = y[32, 32] - y[32, 31]
        assert jump > 0.9 * 0.5, (r, jump)                   # 真値 0.5 の 9 割以上が隣り合う画素で残る
        g = ndimage.gaussian_filter(xn, r / 2.0, mode="nearest")
        assert g[32, 32] - g[32, 31] < 0.5 * jump            # 同程度に均す gaussian は段差を鈍らせる


def test_kuwahara_break_probe_non_overlapping_quadrants_disagree():
    """壊して確かめる: 象限の重なり(中心の行と列の共有)を外すと参照と合わない。"""
    x = _inputs()["random"]
    r = 3
    H, W = x.shape
    k = r + 1
    mu = float(np.mean(x))
    xp = np.pad(x - mu, r + 1, mode="edge")           # 窓を 1 つぶん外へずらす = 重ならない
    m = ops._box_sums_valid(xp, k) / (k * k)
    q = ops._box_sums_valid(xp * xp, k) / (k * k)
    var = np.maximum(q - m * m, 0.0)
    off = r + 1
    sl = ((slice(0, H), slice(0, W)), (slice(0, H), slice(off, off + W)),
          (slice(off, off + H), slice(0, W)), (slice(off, off + H), slice(off, off + W)))
    means = np.stack([m[s] for s in sl])
    vs = np.round(np.stack([var[s] for s in sl]), ops._KUWAHARA_TIE_DIGITS)
    wrong = np.take_along_axis(means, np.argmin(vs, axis=0)[None], axis=0)[0] + mu
    assert np.abs(wrong - _kuwahara_bruteforce(x, r)).max() > 1e-3


def test_kuwahara_box_sums_equal_direct_sums():
    rng = np.random.default_rng(3)
    x = rng.random((19, 23))
    for k in (1, 2, 5, 9):
        got = ops._box_sums_valid(x, k)
        ref = np.array([[x[i:i + k, j:j + k].sum() for j in range(x.shape[1] - k + 1)]
                        for i in range(x.shape[0] - k + 1)])
        assert np.abs(got - ref).max() < 1e-12


# ---------------------------------------------------------------- XDoG

def _gauss_kernel(sigma):
    """scipy と同じ打ち切り(4 sigma を四捨五入)・正規化の、独立に組んだ 1 次元核。"""
    rad = int(4.0 * sigma + 0.5)
    t = np.arange(-rad, rad + 1, dtype=np.float64)
    w = np.exp(-0.5 * t * t / (sigma * sigma))
    return w / w.sum(), rad


def _fft_gauss(x, sigma):
    """FFT による周期畳み込み(縁の扱いが違うので、縁から核の半径ぶん離れた内側だけ比べる)。"""
    w, rad = _gauss_kernel(sigma)
    out = x
    for ax in (0, 1):
        n = out.shape[ax]
        ker = np.zeros(n)
        ker[:2 * rad + 1] = w
        ker = np.roll(ker, -rad)
        shape = [1, 1]
        shape[ax] = n
        out = np.real(np.fft.ifft(np.fft.fft(out, axis=ax) * np.fft.fft(ker).reshape(shape), axis=ax))
    return out, rad


def _fft_dog(x, sigma, k, tau):
    g1, r1 = _fft_gauss(x, sigma)
    g2, r2 = _fft_gauss(x, k * sigma)
    return g1 - tau * g2, max(r1, r2)


def test_xdog_response_matches_independent_fft_dog():
    rng = np.random.default_rng(11)
    x = rng.random((96, 110))
    for sigma in (0.5, 1.0, 2.0):
        for tau in (1.0, 0.98):
            ref, rad = _fft_dog(x, sigma, 1.6, tau)
            got = ops._xdog_response(x, sigma, 1.6, tau)
            inner = (slice(rad, -rad), slice(rad, -rad))
            assert np.abs(got[inner] - ref[inner]).max() < 1e-12, (sigma, tau)


def test_xdog_public_op_matches_fft_reference_through_the_threshold():
    rng = np.random.default_rng(12)
    x = rng.random((96, 110))
    a, b = 0.2, 0.3                                        # sigma 1.0、eps 0.03
    sigma, eps = 0.5 + 2.5 * a, 0.1 * b
    ref_d, rad = _fft_dog(x, sigma, ops._XDOG_K, ops._XDOG_TAU)
    ref = np.where(ref_d >= eps, 1.0, 1.0 + np.tanh(ops._XDOG_PHI * (ref_d - eps)))
    got = fullseye.apply(x, "xdog", a, b)
    inner = (slice(rad, -rad), slice(rad, -rad))
    assert np.abs(got[inner] - ref[inner]).max() < 1e-11


def test_xdog_break_probe_wrong_k_disagrees_with_fft_reference():
    rng = np.random.default_rng(13)
    x = rng.random((96, 110))
    ref, rad = _fft_dog(x, 1.0, 1.6, 0.98)
    wrong = ops._xdog_response(x, 1.0, 1.5, 0.98)
    inner = (slice(rad, -rad), slice(rad, -rad))
    assert np.abs(wrong[inner] - ref[inner]).max() > 1e-3


def test_xdog_tau_one_phi_infinite_is_the_sign_of_dog():
    """閉形式: tau = 1、phi -> 無限大で T(D) = [D >= eps]。"""
    rng = np.random.default_rng(14)
    x = rng.random((60, 70))
    d = ops._xdog_response(x, 1.2, 1.6, 1.0)
    for eps in (0.0, 0.01):
        t = ops._xdog_threshold(d, eps, 1e15)
        step = (d >= eps).astype(np.float64)
        far = np.abs(d - eps) > 1e-9                        # 閾値ぎりぎりだけは tanh が飽和しない
        assert far.mean() > 0.99
        assert np.array_equal(t[far], step[far])
    # phi が有限なら、閾値の下は 0 と 1 の間で単調
    t = ops._xdog_threshold(np.array([-1.0, -0.01, -0.001, 0.0, 0.5]), 0.0, 50.0)
    assert np.all(np.diff(t) >= 0) and t[-1] == 1.0 and t[0] == 0.0


def test_xdog_step_edge_darkens_only_the_dark_side():
    x = np.zeros((40, 60))
    x[:, 30:] = 1.0
    # tau = 1 の DoG は縁の中心について奇関数(閉形式): D[c-1-j] = -D[c+j]
    d = ops._xdog_response(x, 1.0, 1.6, 1.0)[20]
    assert np.abs(d[29 - np.arange(10)] + d[30 + np.arange(10)]).max() < 1e-12
    y = fullseye.apply(x, "xdog", 0.2, 0.0)[20]
    assert y[:10].min() == 1.0 and y[-10:].min() == 1.0     # 遠い平坦部は紙の白
    assert y.min() < 0.05 and 24 <= int(np.argmin(y)) <= 29  # 線は暗い側にだけ出る
    assert y[30:].min() > 0.99                               # 明るい側には出ない


# ---------------------------------------------------------------- 共通の契約

@pytest.mark.parametrize("name", ["kuwahara", "xdog"])
def test_op_contract_finite_unit_range_deterministic_and_uniform(name):
    rng = np.random.default_rng(5)
    x = rng.random((31, 29))
    for a in (0.0, 0.37, 1.0):
        for b in (0.0, 0.6, 1.0):
            y1 = fullseye.apply(x, name, a, b)
            y2 = fullseye.apply(x, name, a, b)
            assert y1.dtype == np.float64 and y1.shape == x.shape
            assert np.isfinite(y1).all() and y1.min() >= 0.0 and y1.max() <= 1.0
            assert np.array_equal(y1, y2)
    for c in np.linspace(0.0, 1.0, 21):
        flat = np.full((17, 19), c)
        for a in (0.0, 0.5, 1.0):
            y = fullseye.apply(flat, name, a, 0.5)
            assert np.ptp(y) == 0.0, (name, c, a)
