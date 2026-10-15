# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""間接 ToF(連続波・位相方式)—— 4 位相の生信号から距離を出し、折り返し・多重反射・縁の混合・高調波で壊れるところまで。

光源を周波数 f で強度変調し、戻ってきた光と参照の相関を、参照の位相を K 段(ふつう 4 段 = 0°・90°・180°・270°)
ずらして積分する。画素 1 つが K 個の値(バケット)を出し、そこから位相 φ・振幅 A・オフセット B が決まる:

    m_k = B + A·cos(φ − θ_k)、θ_k = 2πk/K      (4 段なら φ = atan2(m1 − m3, m0 − m2)、A = ½√((m0−m2)² + (m1−m3)²))
    距離 d = c·φ / (4π f)、非曖昧距離(折り返しの周期)= c / (2f)

距離は**周期 c/(2f) の剰余**でしか分からない。高い f ほど 1 周期が短く位相雑音あたりの距離誤差が小さい
(σ_d = c/(4π f)·σ_φ)が、すぐ折り返す。周波数を 2〜3 個使い、剰余を中国剰余定理(CRT)で組み合わせて
c/(2·gcd f) までを一意にする(多周波アンラップ)。位相雑音が大きいと**次数(何周目か)を丸ごと誤り**、
距離が周期の単位で飛ぶ。

壊れ方は 4 つで、どれも op で作って測れる:

* **マルチパス**(多重反射): 画素に 2 本以上の経路の光が入ると、位相はフェーザ和の位相になる
  (部屋の隅・凹んだ部品・半透明板・散乱)。経路の位相は周波数に比例して回るので、等間隔の多周波で測れば
  分けられる(スパースな逆問題 / Prony・行列ペンシル)。
* **フライングピクセル**: 画素の視野に前景と背景が同時に入ると、2 つの位相が混ざって**その間の宙に浮いた距離**になる。
* **高調波の周期誤差(wiggling)**: 変調・復調が矩形波だと相関は三角波になり、K 段の推定に奇数次の高調波が
  折り返す(4 段なら 3 次と 5 次)。誤差は位相の周期 2π/K で波打つ。
* **背景光**: 太陽光などは B を増やすだけで A を増やさない。ショット雑音 √B が増え、σ_φ ≈ √B/(√2 A)(4 段)が悪化する。

op(どれも fail-closed、黙って推定・補間しない):

* :func:`itof_capture` —— 距離の図(と反射率・余分な経路・背景光)→ 周波数ごと K 段の生信号(ショット雑音・読み出し雑音つき)。
  細かく描いた距離を画素の開口で平均すれば、縁の混合(フライングピクセル)がそのまま生まれる。
* :func:`itof_phase_amplitude` —— K 段の生信号 → 位相・振幅・オフセット・折り返した距離・画素ごとの距離の雑音の見積もり。
  段の位相が等間隔でなくても(既知なら)最小二乗で解く。
* :func:`itof_noise_budget` —— 信号・背景光・読み出し雑音・復調コントラスト → σ_φ・σ_d・非曖昧距離の閉形式。
* :func:`itof_unwrap_multifreq` —— 複数周波数の位相 → 距離。次数の仮説を全部試す最尤の復号、重みつき頑健 CRT
  (``residue.residue_crt``)、または 2 周波のうなり。
* :func:`itof_unwrap_error_rate` —— 周波数の組と位相雑音 → 最尤の復号が次数を誤る確率の上界(和集合の上界)と Wang–Xia の保証域。
* :func:`itof_multipath_separate` —— 等間隔の多周波のフェーザ → 経路ごとの距離と強さ(行列ペンシル)。
* :func:`itof_flying_pixel_mask` —— 距離の図 → 前景と背景の間に浮いた画素の印。
* :func:`itof_wiggling_correct` —— 高調波による周期誤差を、波形の模型(LUT の逆引き)か較正の組(2π/K 周期の調和の当てはめ)で補正する。

既存の op との棲み分け(再実装しない):

* 剰余の組み合わせは ``residue.residue_crt``(重みつき・頑健な実数 CRT)をそのまま呼ぶ。
* 凹んだ形の相互反射の多経路(輸送行列・形態係数)は ``lighttransport``(``tof_multipath_phase`` /
  ``tof_transport_depth``)。この族の :func:`itof_capture` は経路の距離と強さを受け取るだけなので、輸送行列から
  1 回反射の経路を並べて渡せば同じ数字になる(PoC で突き合わせる)。
* 直接 ToF(光子の到達時刻のヒストグラム)は ``photoncount``(``dtof_cube_simulate`` / ``dtof_cube_depth``)。

出典(式は本文で確かめたもの):

* R. Lange, P. Seitz, "Solid-state time-of-flight range camera", IEEE J. Quantum Electronics 37(3), 390–397 (2001),
  DOI 10.1109/3.910448 —— 4 段の位相・振幅・オフセットと、距離の分解能(ショット雑音律速)。
* M. Hansard, S. Lee, O. Choi, R. Horaud, *Time-of-Flight Cameras: Principles, Methods and Applications*,
  Springer (2013), DOI 10.1007/978-1-4471-4658-2 —— 位相と距離、非曖昧距離、フライングピクセル、多周波。
* X.-G. Xia, G. Wang, "Phase unwrapping and a robust Chinese remainder theorem", IEEE Signal Processing Letters
  14(4), 247–250 (2007), DOI 10.1109/LSP.2006.884898 —— 剰余の誤差が Γ/4 未満なら次数を誤らない。
* A. Bhandari et al., "Resolving multipath interference in time-of-flight imaging via modulation frequency diversity
  and sparse regularization", Optics Letters 39(6), 1705–1708 (2014), DOI 10.1364/OL.39.001705 —— 経路の位相が
  周波数に比例して回ることを使い、多周波の測定から経路を分ける。
* S. Fuchs, "Multipath interference compensation in time-of-flight camera images", ICPR 2010,
  DOI 10.1109/ICPR.2010.874 —— 凹んだ場面で距離が伸びる。
* M. Lindner, I. Schiller, A. Kolb, R. Koch, "Time-of-flight sensor calibration for accurate range sensing",
  Computer Vision and Image Understanding 114(12), 1318–1328 (2010), DOI 10.1016/j.cviu.2009.11.002 ——
  距離に周期的な系統誤差(wiggling)があり、較正で補正する。
* Y. Hua, T. K. Sarkar, "Matrix pencil method for estimating parameters of exponentially damped/undamped sinusoids
  in noise", IEEE Trans. ASSP 38(5), 814–824 (1990), DOI 10.1109/29.56027 —— 行列ペンシル。
"""
from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

import residue

__all__ = [
    "itof_capture",
    "itof_phase_amplitude",
    "itof_noise_budget",
    "itof_unwrap_multifreq",
    "itof_unwrap_error_rate",
    "itof_multipath_separate",
    "itof_flying_pixel_mask",
    "itof_wiggling_correct",
]

#: 真空中の光速 [m/s]。
C_LIGHT = 299_792_458.0
#: 生信号であることを示す印(:func:`itof_phase_amplitude` が確かめる)。
RAW_KIND = "itof_raw"
#: 位相の表であることを示す印。
PHASE_KIND = "itof_phase"
#: 周波数の上限 [Hz](連続波の iToF は数 MHz〜数百 MHz)。
MAX_FREQ_HZ = 2e9
#: 周波数の個数の上限。
MAX_FREQS = 32
#: 段の数(K)の範囲。
MIN_STEPS, MAX_STEPS = 3, 32
#: 細かく描いた距離の画素数の上限。
MAX_PIXELS = 1 << 22
#: 余分な経路の本数の上限。
MAX_PATHS = 4096
#: 経路 × 画素 × 周波数の上限(計算量の歯止め)。
MAX_WORK = 400_000_000
WAVEFORMS = ("sine", "square")


# ───────────────────────────── 検査 ─────────────────────────────
def _num(v, name, fn, lo=None, hi=None, lo_open=False):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a number (got %r)" % (fn, name, v))
    x = float(v)
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite (got %r)" % (fn, name, v))
    if lo is not None and (x <= lo if lo_open else x < lo):
        raise ValueError("%s: %s must be %s %g (got %r)" % (fn, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and x > hi:
        raise ValueError("%s: %s must be <= %g (got %r)" % (fn, name, hi, v))
    return x


def _int(v, name, fn, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or not (lo <= int(v) <= hi):
        raise ValueError("%s: %s must be an integer in [%d, %d] (got %r)" % (fn, name, lo, hi, v))
    return int(v)


def _real_array(a, name, fn):
    if isinstance(a, (str, bytes, dict)) or a is None:
        raise ValueError("%s: %s must be a numeric array (got %s)" % (fn, name, type(a).__name__))
    try:
        arr = np.asarray(a)
    except Exception:                                    # noqa: BLE001
        raise ValueError("%s: %s is not array-like" % (fn, name)) from None
    if arr.dtype == object or arr.dtype.kind not in "biuf":
        raise ValueError("%s: %s must be real numbers (dtype %s)" % (fn, name, arr.dtype))
    arr = arr.astype(np.float64)
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s contains NaN or inf" % (fn, name))
    return arr


def _complex_array(a, name, fn):
    if isinstance(a, (str, bytes, dict)) or a is None:
        raise ValueError("%s: %s must be a numeric array (got %s)" % (fn, name, type(a).__name__))
    arr = np.asarray(a)
    if arr.dtype == object or arr.dtype.kind not in "biufc":
        raise ValueError("%s: %s must be numbers (dtype %s)" % (fn, name, arr.dtype))
    arr = arr.astype(np.complex128)
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s contains NaN or inf" % (fn, name))
    return arr


def _freqs(frequencies_hz, fn):
    f = _real_array(np.atleast_1d(frequencies_hz) if not isinstance(frequencies_hz, (str, bytes, dict))
                    else frequencies_hz, "frequencies_hz", fn)
    if f.ndim != 1 or not (1 <= f.size <= MAX_FREQS):
        raise ValueError("%s: frequencies_hz must be 1..%d numbers (got shape %s)" % (fn, MAX_FREQS, f.shape))
    if (f <= 0).any() or (f > MAX_FREQ_HZ).any():
        raise ValueError("%s: every frequency must be in (0, %g] Hz (got %s)" % (fn, MAX_FREQ_HZ, f.tolist()))
    if np.unique(f).size != f.size:
        raise ValueError("%s: frequencies_hz contains duplicates (%s)" % (fn, f.tolist()))
    return f


def _steps(n_phases, phase_offsets_rad, fn):
    """段の位相 θ_k(既定は 2πk/K の等間隔)。"""
    if phase_offsets_rad is None:
        k = _int(n_phases, "n_phases", fn, MIN_STEPS, MAX_STEPS)
        return 2.0 * np.pi * np.arange(k) / k
    th = _real_array(phase_offsets_rad, "phase_offsets_rad", fn)
    if th.ndim != 1 or not (MIN_STEPS <= th.size <= MAX_STEPS):
        raise ValueError("%s: phase_offsets_rad must be %d..%d angles (got shape %s)"
                         % (fn, MIN_STEPS, MAX_STEPS, th.shape))
    M = np.stack([np.ones_like(th), np.cos(th), np.sin(th)], axis=1)
    if np.linalg.matrix_rank(M, tol=1e-6) < 3:
        raise ValueError("%s: phase_offsets_rad %s cannot separate offset, cos and sin "
                         "(need three distinct angles not a multiple of π apart)" % (fn, th.tolist()))
    return th


def _waveform(waveform, fn):
    """相関の波形。``"sine"`` / ``"square"``(三角波の相関)/ 余弦の係数 c_1..c_N の配列。"""
    if isinstance(waveform, str):
        if waveform not in WAVEFORMS:
            raise ValueError("%s: waveform must be one of %s or an array of cosine harmonics (got %r)"
                             % (fn, WAVEFORMS, waveform))
        return waveform
    c = _real_array(waveform, "waveform", fn)
    if c.ndim != 1 or not (1 <= c.size <= 64):
        raise ValueError("%s: waveform harmonics must be 1..64 numbers c_1..c_N (got shape %s)" % (fn, c.shape))
    if c[0] <= 0 or np.abs(c[1:]).sum() >= c[0]:
        raise ValueError("%s: waveform harmonics need c_1 > 0 and sum |c_n| (n >= 2) < c_1 "
                         "(the fundamental must dominate), got %s" % (fn, c.tolist()))
    return c


def _corr(x, wf):
    """正規化した相関 corr(x)(x = 0 で 1)。"""
    if isinstance(wf, str):
        if wf == "sine":
            return np.cos(x)
        w = np.abs(np.mod(x + np.pi, 2.0 * np.pi) - np.pi)          # [0, π]
        return 1.0 - 2.0 * w / np.pi                                 # 矩形 × 矩形 = 三角波
    n = np.arange(1, wf.size + 1)
    xs = np.asarray(x)[..., None]
    return (wf * np.cos(n * xs)).sum(-1) / wf.sum()


def _wrap(x):
    return np.mod(x + np.pi, 2.0 * np.pi) - np.pi


def _block_mean(a, s):
    if s == 1:
        return a
    h, w = a.shape[-2] // s, a.shape[-1] // s
    return a.reshape(a.shape[:-2] + (h, s, w, s)).mean(axis=(-3, -1))


# ───────────────────────────── 撮る ─────────────────────────────
def itof_capture(depth, reflectivity=None, frequencies_hz=(20e6,), n_phases=4, signal_electrons=2000.0,
                 demod_contrast=0.5, ambient_electrons=0.0, read_noise_e=0.0, waveform="sine",
                 paths_depth=None, paths_amplitude=None, supersample=1, falloff_m=None, noise=True, seed=0):
    """距離の図 → 間接 ToF の生信号(周波数ごとに K 段のバケット、電子数)。``table``(``dict``)を返す。

    画素(細かく描いた標本)ごとに、直接の経路(距離 *depth*、強さ ``signal_electrons · reflectivity``)と、
    任意で余分な経路(*paths_depth* = 往復の経路長の半分 [m]、*paths_amplitude* = ``signal_electrons`` に掛ける強さ)が
    入る。経路 p の位相は ``φ_p = 4π f d_p / c``。段 k(参照の位相 ``θ_k = 2πk/K``)のバケットの期待値は

        m_k = (Σ_p a_p + ambient) / K + demod_contrast · Σ_p a_p · corr(φ_p − θ_k) / K

    (corr は *waveform*: ``"sine"`` なら cos、``"square"`` なら矩形どうしの相関 = 三角波、配列なら余弦の係数 c_1..c_N)。
    つまり 1 回の測定(K 段の合計)に信号 ``a_p`` 電子と背景光 ``ambient_electrons`` 電子が入る。*noise* が真なら
    各バケットに Poisson のショット雑音と、標準偏差 *read_noise_e* の正規の読み出し雑音を足す。

    *supersample* = s > 1 なら *depth* などは**センサの s 倍の細かさ**で描いたものとみなし、s × s の標本の
    バケットを平均して 1 画素にする(バケットは経路の光の線形和なので、これは画素の開口で光を足すのと同じ)。
    前景と背景をまたぐ画素では 2 つの位相が混ざり、フライングピクセルが生まれる。
    *falloff_m* を与えると直接の経路の強さに ``(falloff_m / depth)²``(逆二乗)を掛ける。

    返す ``dict``: ``kind``(``"itof_raw"``)、``samples`` ``(F, K, H, W)``、``mean_samples``(雑音なしの期待値)、
    ``frequencies_hz``、``phase_offsets_rad``、``true_depth``(画素内の直接経路の距離の平均)、``mixed``(画素内の
    距離の幅 [m])、``waveform``、``demod_contrast``、``read_noise_e``、``ambiguity_range`` ``(F,)``。

    **Raises** ``ValueError``: depth が 2 次元でない・正でない・非有限 / reflectivity・経路の形が合わない・負 /
    周波数が (0, 2 GHz] でない・重複 / n_phases が 3〜32 でない / demod_contrast が (0, 1] でない / 電子数が負 /
    形が supersample で割り切れない / 画素数・経路数・計算量が上限を超える / waveform が不正。
    """
    fn = "itof_capture"
    d = _real_array(depth, "depth", fn)
    if d.ndim != 2 or min(d.shape) < 1:
        raise ValueError("%s: depth must be a 2-D map (got shape %s)" % (fn, d.shape))
    if (d <= 0).any():
        raise ValueError("%s: depth must be > 0 everywhere (min %g)" % (fn, d.min()))
    if d.size > MAX_PIXELS:
        raise ValueError("%s: depth has %d samples (> %d)" % (fn, d.size, MAX_PIXELS))
    rho = np.ones_like(d) if reflectivity is None else _real_array(reflectivity, "reflectivity", fn)
    if rho.shape != d.shape:
        raise ValueError("%s: reflectivity shape %s != depth shape %s" % (fn, rho.shape, d.shape))
    if (rho < 0).any():
        raise ValueError("%s: reflectivity must be >= 0" % fn)
    f = _freqs(frequencies_hz, fn)
    th = _steps(n_phases, None, fn)
    K = th.size
    S = _num(signal_electrons, "signal_electrons", fn, lo=0.0, hi=1e12)
    cd = _num(demod_contrast, "demod_contrast", fn, lo=0.0, hi=1.0, lo_open=True)
    amb = _num(ambient_electrons, "ambient_electrons", fn, lo=0.0, hi=1e12)
    rn = _num(read_noise_e, "read_noise_e", fn, lo=0.0, hi=1e6)
    wf = _waveform(waveform, fn)
    s = _int(supersample, "supersample", fn, 1, 64)
    if d.shape[0] % s or d.shape[1] % s:
        raise ValueError("%s: depth shape %s is not divisible by supersample %d" % (fn, d.shape, s))
    a0 = S * rho
    if falloff_m is not None:
        r0 = _num(falloff_m, "falloff_m", fn, lo=0.0, lo_open=True)
        a0 = a0 * (r0 / d) ** 2
    pd = [d]
    pa = [a0]
    if (paths_depth is None) != (paths_amplitude is None):
        raise ValueError("%s: give both paths_depth and paths_amplitude, or neither" % fn)
    if paths_depth is not None:
        xd = _real_array(paths_depth, "paths_depth", fn)
        xa = _real_array(paths_amplitude, "paths_amplitude", fn)
        if xd.ndim == 2:
            xd, xa = xd[None], (xa[None] if xa.ndim == 2 else xa)
        if xd.ndim != 3 or xd.shape[1:] != d.shape or xa.shape != xd.shape:
            raise ValueError("%s: paths_depth / paths_amplitude must both be (P, %d, %d) (got %s and %s)"
                             % (fn, d.shape[0], d.shape[1], xd.shape, xa.shape))
        if xd.shape[0] > MAX_PATHS:
            raise ValueError("%s: %d extra paths (> %d)" % (fn, xd.shape[0], MAX_PATHS))
        if (xd <= 0).any() or (xa < 0).any():
            raise ValueError("%s: path depths must be > 0 and path amplitudes >= 0" % fn)
        pd += list(xd)
        pa += list(S * xa)
    if len(pd) * d.size * f.size * K > MAX_WORK:
        raise ValueError("%s: %d paths x %d samples x %d frequencies x %d steps exceeds %d"
                         % (fn, len(pd), d.size, f.size, K, MAX_WORK))
    asum = np.sum(pa, axis=0)
    mean = np.empty((f.size, K) + d.shape)
    for i, fi in enumerate(f):
        k_ = 4.0 * np.pi * fi / C_LIGHT
        acc = np.zeros((K,) + d.shape)
        for dp, ap in zip(pd, pa):
            ph = k_ * dp
            for k in range(K):
                acc[k] += ap * _corr(ph - th[k], wf)
        mean[i] = (asum + amb)[None] / K + cd * acc / K
    mean = _block_mean(mean, s)
    if noise:
        rng = np.random.default_rng(seed)
        smp = rng.poisson(np.maximum(mean, 0.0)).astype(np.float64)
        if rn > 0:
            smp = smp + rng.normal(0.0, rn, smp.shape)
    else:
        smp = mean.copy()
    if s > 1:
        dd = d.reshape(d.shape[0] // s, s, d.shape[1] // s, s)
        mixed = dd.max(axis=(1, 3)) - dd.min(axis=(1, 3))
    else:
        mixed = np.zeros_like(d)
    return {"kind": RAW_KIND, "samples": smp, "mean_samples": mean, "frequencies_hz": f.copy(),
            "phase_offsets_rad": th, "true_depth": _block_mean(d, s), "mixed": mixed,
            "waveform": wf if isinstance(wf, str) else wf.tolist(), "demod_contrast": cd,
            "read_noise_e": rn, "ambiguity_range": C_LIGHT / (2.0 * f)}


# ───────────────────────────── 位相・振幅 ─────────────────────────────
def itof_phase_amplitude(samples, frequencies_hz=None, phase_offsets_rad=None, read_noise_e=None):
    """K 段の生信号 → 位相・振幅・オフセット・折り返した距離・画素ごとの距離の雑音の見積もり(``table``)。

    *samples* は :func:`itof_capture` の ``dict``、または ``(F, K, ...)`` の配列(周波数 F、段 K が先頭。1 周波なら
    ``samples[None]``)。段 k のバケットを ``m_k = B + A·cos(φ − θ_k)`` とみなし、``[1, cos θ_k, sin θ_k]`` の
    最小二乗で B・A cos φ・A sin φ を解く(θ_k が等間隔 2πk/K なら DFT と同じ。4 段なら
    ``φ = atan2(m1 − m3, m0 − m2)``、``A = ½√((m0 − m2)² + (m1 − m3)²)``、``B = Σm_k / 4``)。
    θ_k は *phase_offsets_rad*(既定は等間隔、``dict`` ならその値)。

    距離の雑音の見積もり: 各バケットの分散を ``B + read_noise²``(ショット雑音は平均に等しい)とみなすと、最小二乗の
    共分散から位相の標準偏差 σ_φ が出る(4 段・等間隔なら ``σ_φ = √((B + σ_r²)/2) / A``)。``σ_d = c σ_φ / (4π f)``。
    ★小さい雑音の近似で、A ≈ √B 程度まで SNR が落ちると実際の散らばりはこれより大きい。

    返す ``dict``: ``kind``(``"itof_phase"``)、``phase`` ``(F, ...)`` [0, 2π)、``amplitude``、``offset``、``phasor``
    (``A·e^{iφ}``、複素)、``frequencies_hz``(分かれば)、``wrapped_depth`` と ``ambiguity_range``(周波数が分かれば)、
    ``phase_sigma``、``depth_sigma``(周波数が分かれば)。

    **Raises** ``ValueError``: 配列が 2 次元未満・非有限 / 段の数が 3〜32 でない / 段の位相が退化 /
    周波数の数が F と合わない・範囲外 / dict が生信号でない。
    """
    fn = "itof_phase_amplitude"
    rn = None
    if isinstance(samples, dict):
        if samples.get("kind") != RAW_KIND or "samples" not in samples:
            raise ValueError("%s: dict input must come from itof_capture (kind %r)" % (fn, RAW_KIND))
        if frequencies_hz is None:
            frequencies_hz = samples.get("frequencies_hz")
        if phase_offsets_rad is None:
            phase_offsets_rad = samples.get("phase_offsets_rad")
        rn = samples.get("read_noise_e")
        samples = samples["samples"]
    m = _real_array(samples, "samples", fn)
    if m.ndim < 2:
        raise ValueError("%s: samples must be (F, K, ...) (got shape %s)" % (fn, m.shape))
    F, K = m.shape[0], m.shape[1]
    th = _steps(K, phase_offsets_rad, fn)
    if th.size != K:
        raise ValueError("%s: %d phase offsets for %d steps" % (fn, th.size, K))
    if read_noise_e is not None:
        rn = _num(read_noise_e, "read_noise_e", fn, lo=0.0, hi=1e6)
    rn = 0.0 if rn is None else float(rn)
    M = np.stack([np.ones_like(th), np.cos(th), np.sin(th)], axis=1)          # (K, 3)
    P = np.linalg.pinv(M)                                                       # (3, K)
    coef = np.tensordot(P, m, axes=([1], [1]))                                  # (3, F, ...)
    B, X, Y = coef[0], coef[1], coef[2]
    A = np.hypot(X, Y)
    ph = np.mod(np.arctan2(Y, X), 2.0 * np.pi)
    C = np.linalg.inv(M.T @ M)[1:, 1:]                                          # 分散 1 あたりの (X, Y) の共分散
    var = np.maximum(B, 0.0) + rn ** 2
    s_, c_ = np.sin(ph), np.cos(ph)
    perp = s_ ** 2 * C[0, 0] + c_ ** 2 * C[1, 1] - 2.0 * s_ * c_ * C[0, 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        sig = np.where(A > 0, np.sqrt(var * perp) / np.where(A > 0, A, 1.0), np.inf)
    out = {"kind": PHASE_KIND, "phase": ph, "amplitude": A, "offset": B, "phasor": A * np.exp(1j * ph),
           "phase_sigma": sig, "phase_offsets_rad": th}
    if frequencies_hz is not None:
        f = _freqs(frequencies_hz, fn)
        if f.size != F:
            raise ValueError("%s: %d frequencies for %d frequency planes" % (fn, f.size, F))
        sc = (C_LIGHT / (4.0 * np.pi * f)).reshape((F,) + (1,) * (m.ndim - 2))
        out.update(frequencies_hz=f, wrapped_depth=ph * sc, ambiguity_range=C_LIGHT / (2.0 * f),
                   depth_sigma=sig * sc)
    return out


def itof_noise_budget(frequency_hz=20e6, signal_electrons=2000.0, demod_contrast=0.5, ambient_electrons=0.0,
                      read_noise_e=0.0, n_phases=4):
    """間接 ToF の距離の雑音の閉形式(1 画素・1 周波数・等間隔 K 段)。``table`` を返す。

    1 回の測定(K 段の合計)に信号 S 電子・背景光 S_bg 電子が入るとき、段ごとに
    ``A = c_d · S / K``(振幅)、``B = (S + S_bg) / K``(オフセット)。各バケットの分散を ``B + σ_r²`` とすると、
    等間隔 K 段の位相の推定の標準偏差は

        σ_φ = √(2 (B + σ_r²) / K) / A           (4 段なら √((B + σ_r²)/2) / A)
        σ_d = c / (4π f) · σ_φ

    (小さい雑音の近似)。背景光は B だけを増やすので σ_d は √(S + S_bg) に比例して悪くなり、信号を k 倍にすると
    (背景光なしで)σ_d は 1/√k。周波数を k 倍にすると σ_d は 1/k、非曖昧距離 ``c/(2f)`` も 1/k。

    返す ``dict``: ``amplitude``、``offset``、``snr``(``A / √(B + σ_r²)``)、``phase_sigma``、``depth_sigma``、
    ``ambiguity_range``、``frequency_hz``、``n_phases``。

    **Raises** ``ValueError``: 周波数が (0, 2 GHz] でない / 電子数が負・信号が 0 / demod_contrast が (0, 1] でない /
    n_phases が 3〜32 でない。
    """
    fn = "itof_noise_budget"
    f = _num(frequency_hz, "frequency_hz", fn, lo=0.0, hi=MAX_FREQ_HZ, lo_open=True)
    S = _num(signal_electrons, "signal_electrons", fn, lo=0.0, hi=1e12, lo_open=True)
    cd = _num(demod_contrast, "demod_contrast", fn, lo=0.0, hi=1.0, lo_open=True)
    amb = _num(ambient_electrons, "ambient_electrons", fn, lo=0.0, hi=1e12)
    rn = _num(read_noise_e, "read_noise_e", fn, lo=0.0, hi=1e6)
    K = _int(n_phases, "n_phases", fn, MIN_STEPS, MAX_STEPS)
    A = cd * S / K
    B = (S + amb) / K
    sig_phi = math.sqrt(2.0 * (B + rn ** 2) / K) / A
    return {"amplitude": A, "offset": B, "snr": A / math.sqrt(B + rn ** 2), "phase_sigma": sig_phi,
            "depth_sigma": C_LIGHT / (4.0 * math.pi * f) * sig_phi, "ambiguity_range": C_LIGHT / (2.0 * f),
            "frequency_hz": f, "n_phases": K}


# ───────────────────────────── 多周波アンラップ ─────────────────────────────
def _phase_input(phase, frequencies_hz, weights, fn):
    if isinstance(phase, dict):
        if phase.get("kind") != PHASE_KIND:
            raise ValueError("%s: dict input must come from itof_phase_amplitude (kind %r)" % (fn, PHASE_KIND))
        if frequencies_hz is None:
            frequencies_hz = phase.get("frequencies_hz")
        if weights is None and "amplitude" in phase and "offset" in phase:
            A = np.asarray(phase["amplitude"], dtype=np.float64)
            B = np.asarray(phase["offset"], dtype=np.float64)
            with np.errstate(divide="ignore", invalid="ignore"):
                weights = np.where(B > 0, A ** 2 / np.where(B > 0, B, 1.0), 0.0)   # ∝ 1/σ_φ²(最尤の重み)
        phase = phase["phase"]
    if frequencies_hz is None:
        raise ValueError("%s: frequencies_hz is required (the phase table carries none)" % fn)
    ph = _real_array(phase, "phase", fn)
    f = _freqs(frequencies_hz, fn)
    if ph.ndim == 0 or ph.shape[0] != f.size:
        raise ValueError("%s: phase must be (F, ...) with F = %d frequencies (got shape %s)" % (fn, f.size, ph.shape))
    return ph, f, weights


def _ml_core(r, p, w, hi):
    """最も細かい周期(距離の誤差が最も小さい周波数)の剰余を錨に、次数の仮説を全部採点する。"""
    F = p.size
    shp = r.shape[1:]
    pb = p.reshape((F,) + (1,) * len(shp))
    ref = int(np.argmin(p))
    K = int(math.ceil(hi / p[ref])) + 1
    best = np.full(shp, np.nan)
    s1 = np.full(shp, -np.inf)
    s2 = np.full(shp, -np.inf)
    for k in range(K):
        cand = r[ref] + k * p[ref]
        sc = (w * np.cos(2.0 * np.pi * (cand[None] - r) / pb)).sum(0)
        sc = np.where(cand < hi, sc, -np.inf)
        upd = sc > s1
        s2 = np.where(upd, s1, np.maximum(s2, sc))
        best = np.where(upd, cand, best)
        s1 = np.where(upd, sc, s1)
    e = residue._wrap_signed(r - best[None], pb)
    iv = w / pb ** 2
    ivs = iv.sum(0)
    val = best + np.where(ivs > 0, (iv * e).sum(0) / np.where(ivs > 0, ivs, 1.0), 0.0)
    val = np.mod(val, hi)
    ws = w.sum(0)
    wsum = np.where(ws > 0, ws, 1.0)
    margin = np.where(np.isfinite(s2), (s1 - s2) / wsum, 2.0)
    margin = np.where(ws > 0, margin, 0.0)
    return val, s1 / wsum, margin, residue._wrap_signed(r - val[None], pb)


def itof_unwrap_multifreq(phase, frequencies_hz=None, weights=None, max_range_m=None, method="ml"):
    """複数の周波数の位相 → 距離(多周波アンラップ)。``table`` を返す。

    周波数 f_i の位相 φ_i は距離を周期 ``p_i = c/(2 f_i)`` の剰余 ``r_i = φ_i p_i / (2π)`` で教える。周期の最小公倍数
    ``U = c / (2·gcd f)`` までが一意(非曖昧距離)。

    * ``method="ml"``(既定)—— **最も高い周波数**(距離の誤差が最も小さい帯)の剰余を錨にして、その次数の仮説
      ``v = r_hi + k p_hi``(k = 0 … U/p_hi)を全部、フェーザの一致 ``Σ w_i cos(2π(v − r_i)/p_i)`` で採点し、最良の仮説を
      逆分散の重み平均で精密化する(仮説を全部試す最尤の復号。位相雑音が帯ごとに同じなら、錨の誤差が最も小さい)。
    * ``method="crt"`` —— ``residue.residue_crt``(重みつきの頑健な中国剰余定理)にそのまま渡す。★``residue_crt`` は
      **最も長い周期**(= 最も低い周波数)を錨にするので、位相雑音が帯ごとに同じだと錨の距離の誤差が最も大きい。
      低い周波数の位相の誤差が Wang–Xia の保証(:func:`itof_unwrap_error_rate` の ``guaranteed_phase_rad``)を越えると
      ``"ml"`` より大きく崩れる(比較のために残してある)。
    * ``method="beat"`` —— 2 周波だけ。うなりの位相 ``φ_1 − φ_2`` で粗い距離(周期 ``c/(2|f_1 − f_2|)``)を出し、
      各周波数の次数をそれに最も近く丸めて重み平均する(教科書の古典的な方法)。

    *weights* の既定は、:func:`itof_phase_amplitude` の表なら ``A²/B``(∝ 1/σ_φ²)、配列なら全帯 1。
    *max_range_m* で探す範囲 ``[0, max_range_m)`` を狭められる(非曖昧距離より広くは拒否)。

    返す ``dict``: ``depth``、``order`` ``(F, ...)``(各周波数で何周目か)、``margin``(最良と次点の採点の差。小さい =
    次数が際どい)、``score``、``residual`` ``(F, ...)`` [m]、``unambiguous_range``、``periods``、``method``。

    **Raises** ``ValueError``: 周波数・位相の形が合わない / 周期が通約できない(非曖昧距離が有限でない)/
    max_range_m が非曖昧距離より広い / beat で 2 周波でない / method が不正 / 仮説 × 画素が上限を超える。
    """
    fn = "itof_unwrap_multifreq"
    ph, f, w = _phase_input(phase, frequencies_hz, weights, fn)
    if method not in ("ml", "crt", "beat"):
        raise ValueError("%s: method must be 'ml', 'crt' or 'beat' (got %r)" % (fn, method))
    if f.size < 2:
        raise ValueError("%s: need at least 2 frequencies (got %d)" % (fn, f.size))
    p = C_LIGHT / (2.0 * f)
    shp = (f.size,) + (1,) * (ph.ndim - 1)
    r = np.mod(ph, 2.0 * np.pi) / (2.0 * np.pi) * p.reshape(shp)
    hi = None
    if max_range_m is not None:
        hi = _num(max_range_m, "max_range_m", fn, lo=0.0, lo_open=True)
    if w is not None:
        w = _real_array(w, "weights", fn)
        if (w < 0).any():
            raise ValueError("%s: weights must be >= 0" % fn)
        if w.ndim == 1 and w.size == f.size:
            w = w.reshape(shp)
        try:
            w = np.broadcast_to(w, ph.shape).astype(np.float64)
        except ValueError:
            raise ValueError("%s: weights shape %s does not broadcast to phase %s" % (fn, w.shape, ph.shape)) from None
    if method in ("ml", "crt"):
        # 周期は c/(2f) で、比は周波数の比の逆数。光速の値で分母が崩れないよう、周期を最長の周期で割った単位で
        # 通約を確かめる(c を掛けたままだと 1e-9 の相対誤差の判定が浮動小数で落ちる)。
        unit = p.max()
        if method == "crt":
            res = residue.residue_crt(r / unit, p / unit, weights=w, lo=0.0,
                                      hi=None if hi is None else hi / unit)
            out = {"depth": res["value"] * unit, "margin": res["margin"], "score": res["score"],
                   "residual": res["residual"] * unit, "unambiguous_range": res["unambiguous_range"] * unit}
        else:
            _, fg = _frequency_integers(f, fn)
            U = C_LIGHT / (2.0 * fg)
            if hi is not None and hi > U * (1 + 1e-12):
                raise ValueError("%s: max_range_m %.6g is wider than the unambiguous range %.6g "
                                 "(c / (2 gcd f)) — two distances would share every phase" % (fn, hi, U))
            top = U if hi is None else hi
            n_hyp = int(math.ceil(top / p.min())) + 1
            if n_hyp * max(r[0].size, 1) * f.size > residue.MAX_SEARCH_ELEMENTS:
                raise ValueError("%s: %d hypotheses x %d samples x %d frequencies exceeds %d"
                                 % (fn, n_hyp, r[0].size, f.size, residue.MAX_SEARCH_ELEMENTS))
            ww = np.ones(ph.shape) if w is None else w
            val, score, margin, resid = _ml_core(r, p, ww, top)
            out = {"depth": val, "margin": margin, "score": score, "residual": resid, "unambiguous_range": U}
    else:
        if f.size != 2:
            raise ValueError("%s: method 'beat' needs exactly 2 frequencies (got %d)" % (fn, f.size))
        pb = C_LIGHT / (2.0 * abs(f[0] - f[1]))
        if hi is not None and hi > pb * (1 + 1e-12):
            raise ValueError("%s: max_range_m %.6g is wider than the beat period %.6g" % (fn, hi, pb))
        lo_i, hi_i = (0, 1) if f[0] > f[1] else (1, 0)
        coarse = np.mod(ph[lo_i] - ph[hi_i], 2.0 * np.pi) / (2.0 * np.pi) * pb
        ests = []
        for i in range(2):
            nn = np.round((coarse - r[i]) / p[i])
            ests.append(r[i] + nn * p[i])
        ww = np.ones(ph.shape) if w is None else w
        iv = ww / (p.reshape(shp) ** 2)
        den = iv.sum(0)
        depth = np.where(den > 0, (iv * np.stack(ests)).sum(0) / np.where(den > 0, den, 1.0), coarse)
        resid = residue._wrap_signed(r - depth[None], p.reshape(shp))
        ep = np.abs(ests[0] - ests[1])
        out = {"depth": depth, "margin": 1.0 - np.minimum(ep / p.min(), 1.0),
               "score": np.cos(2 * np.pi * resid / p.reshape(shp)).mean(0), "residual": resid,
               "unambiguous_range": pb}
    order = np.floor(out["depth"][None] / p.reshape(shp) + 1e-9)
    out.update(order=order, periods=p, method=method)
    return out


def _frequency_integers(f, fn):
    """周波数を共通の基本周波数 f_g の整数倍 n_i に書く(分母 ≤ 1000 の有理比)。"""
    base = f.min()
    fr = [Fraction(float(x / base)).limit_denominator(1000) for x in f]
    for x, q in zip(f, fr):
        if abs(float(q) * base - x) > 1e-9 * x:
            raise ValueError("%s: frequencies %s are not commensurate (ratios must be rational with "
                             "denominators <= 1000)" % (fn, f.tolist()))
    den = 1
    for q in fr:
        den = den * q.denominator // math.gcd(den, q.denominator)
    n = [int(q * den) for q in fr]
    g = 0
    for x in n:
        g = math.gcd(g, x)
    n = [x // g for x in n]
    return np.array(n, dtype=np.int64), base * g / den


def _qfunc(x):
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def itof_unwrap_error_rate(frequencies_hz=(80e6, 100e6, 120e6), phase_sigma_rad=0.05, max_range_m=None):
    """多周波アンラップ(最尤の復号)で次数(何周目か)を誤る確率の見積もり。``table`` を返す。

    周波数を共通の基本周波数の整数倍 ``f_i = n_i f_g`` と書くと、非曖昧距離は ``U = c / (2 f_g)``、周期は ``p_i = U / n_i``。
    折り返さない位相を並べたベクトルは距離 v に比例する直線 ``v·g``(``g_i = 2π/p_i``)の上にあり、折り返しは
    これを ``2π m``(m は整数のベクトル)だけずらした平行な直線の族を作る。最尤の復号(:func:`itof_unwrap_multifreq` の
    ``"ml"``)が誤るのは、測った位相が別の直線 ``v·g + 2πm`` の方に近いとき。位相雑音 σ_i で割った空間での 2 本の
    直線の距離を ``D_m`` とすると、その 2 仮説の誤りは ``Q(D_m / 2)``(ガウス)。

    * ``union_bound`` = ``Σ_m Q(D_m/2)``(範囲内で出会う m すべての和。上界)、``nearest_term`` = ``max_m Q(D_m/2)``。
    * Wang–Xia(2007)の保証: 周期を ``p_i = Γ M_i`` と書く(``Γ = U / lcm(n_i)``)。全周波数の剰余の誤差が ``Γ/4`` 未満なら
      次数は決して誤らない(最も長い周期を錨にする ``residue_crt`` の保証)。``guaranteed_phase_rad`` = 各周波数で
      その境界に当たる位相の誤差 ``2π (Γ/4) / p_i`` —— 低い周波数ほど小さい。

    *phase_sigma_rad* はスカラ(全周波数で同じ)か周波数ごと。*max_range_m* は探す範囲(既定 U)。

    返す ``dict``: ``unambiguous_range``、``periods``、``integers``(n_i)、``gamma``、``guaranteed_phase_rad``、
    ``union_bound``、``nearest_term``、``min_distance``(最小の D_m)、``offsets``(m の配列、``(M, F)``)、``distances``。

    **Raises** ``ValueError``: 周波数が 2 個未満・通約できない・比が細かすぎる / σ が正でない・形が合わない /
    max_range_m が U より広い。
    """
    fn = "itof_unwrap_error_rate"
    f = _freqs(frequencies_hz, fn)
    if f.size < 2:
        raise ValueError("%s: need at least 2 frequencies (got %d)" % (fn, f.size))
    sg = _real_array(np.atleast_1d(phase_sigma_rad) if not isinstance(phase_sigma_rad, (str, bytes, dict))
                     else phase_sigma_rad, "phase_sigma_rad", fn)
    if sg.size == 1:
        sg = np.full(f.size, float(sg.ravel()[0]))
    if sg.shape != f.shape or (sg <= 0).any():
        raise ValueError("%s: phase_sigma_rad must be > 0, a scalar or one per frequency" % fn)
    n, fg = _frequency_integers(f, fn)
    U = C_LIGHT / (2.0 * fg)
    rng_ = U
    if max_range_m is not None:
        rng_ = _num(max_range_m, "max_range_m", fn, lo=0.0, lo_open=True)
        if rng_ > U * (1 + 1e-9):
            raise ValueError("%s: max_range_m %.6g is wider than the unambiguous range %.6g" % (fn, rng_, U))
    if int(np.max(n)) > 4096:
        raise ValueError("%s: frequency ratios too fine (max n_i = %d > 4096)" % (fn, int(np.max(n))))
    p = U / n
    L = 1
    for x in n:
        L = L * int(x) // math.gcd(L, int(x))
    gamma = U / L
    # 範囲内のずれ δ ∈ (−rng, rng) で出会う整数のずれ m_i = round(δ / p_i) を全部集める(δ を p_min/16 刻みで掃く)
    step = p.min() / 16.0
    deltas = np.arange(-rng_ + step / 2, rng_, step)
    ms = np.unique(np.round(deltas[:, None] / p[None, :]).astype(np.int64), axis=0)
    gs = (2.0 * np.pi / p) / sg                                  # σ で割った空間の直線の向き
    u = gs / np.linalg.norm(gs)
    pts = 2.0 * np.pi * ms / sg[None, :]
    perp = pts - (pts @ u)[:, None] * u[None, :]
    D = np.linalg.norm(perp, axis=1)
    keep = D > 1e-9 * (2.0 * np.pi / sg.min())                   # 直線そのもの(m = 0 と U の倍数のずれ)を除く
    ms, D = ms[keep], D[keep]
    terms = np.array([_qfunc(x / 2.0) for x in D]) if D.size else np.zeros(0)
    return {"unambiguous_range": U, "periods": p, "integers": n, "gamma": gamma,
            "guaranteed_phase_rad": 2 * np.pi * (gamma / 4) / p,
            "union_bound": float(min(1.0, terms.sum())) if terms.size else 0.0,
            "nearest_term": float(terms.max()) if terms.size else 0.0,
            "min_distance": float(D.min()) if D.size else float("inf"), "offsets": ms, "distances": D}


# ───────────────────────────── マルチパスの分離 ─────────────────────────────
def itof_multipath_separate(phasors, frequencies_hz=None, n_paths=2, pencil=None):
    """等間隔の多周波で測ったフェーザ → 経路ごとの距離と強さ(行列ペンシル)。``table`` を返す。

    画素に経路 p(距離 d_p、強さ a_p)の光が入ると、周波数 f のフェーザは
    ``m(f) = Σ_p a_p e^{i 4π f d_p / c}``。周波数が等間隔 ``f_k = f_0 + kΔf`` なら
    ``m_k = Σ_p α_p z_p^k``(``z_p = e^{i 4π Δf d_p / c}``、``α_p = a_p e^{i 4π f_0 d_p / c}``)という減衰しない
    指数の和になり、行列ペンシル(Hua & Sarkar 1990)で z_p が閉形式に出る:

    1. 粗い距離 ``d_p = arg(z_p) · c / (4π Δf)``(周期 ``c/(2Δf)`` の剰余)。
    2. Vandermonde の最小二乗で α_p。``|α_p|`` が強さ。
    3. 細かい距離: 中央の周波数 ``f_c`` を原点にした ``arg(α_p)`` は周期 ``c/(2f_c)`` の剰余を教えるので、粗い距離に
       最も近い次数を選んで精密化する(粗い距離の誤差が ``c/(4 f_c)`` を越えると次数を誤る —— 雑音が大きいときは
       ``depth_coarse`` も見ること)。

    経路は距離の近い順に並べる。経路が 1 本しか無い画素では、2 本目の強さが 0 近くに出る。
    ★分けられるのは、2 つの経路の距離の差がおおよそ帯域の分解能 ``c / (2 F Δf)`` より大きいときだけ
    (等間隔 F 周波数の幅が帯域)。それより近い経路は雑音があると 1 本に潰れる。

    *phasors* は :func:`itof_phase_amplitude` の表(``phasor`` と周波数を使う)か、複素の ``(F, ...)`` 配列。
    *pencil* はペンシルの幅 L(既定 F // 2、``n_paths <= L <= F − n_paths``)。

    返す ``dict``: ``depth`` ``(P, ...)``、``depth_coarse``、``amplitude`` ``(P, ...)``、``residual``(当てはめの相対残差)、
    ``ambiguity_coarse``(``c/(2Δf)``)、``resolution``(``c/(2FΔf)``)。

    **Raises** ``ValueError``: 周波数が等間隔でない・2·n_paths 個未満 / 形が合わない / n_paths が 1〜8 でない /
    pencil が範囲外 / 画素数が上限を超える。
    """
    fn = "itof_multipath_separate"
    if isinstance(phasors, dict):
        if phasors.get("kind") != PHASE_KIND or "phasor" not in phasors:
            raise ValueError("%s: dict input must come from itof_phase_amplitude (kind %r)" % (fn, PHASE_KIND))
        if frequencies_hz is None:
            frequencies_hz = phasors.get("frequencies_hz")
        phasors = phasors["phasor"]
    if frequencies_hz is None:
        raise ValueError("%s: frequencies_hz is required" % fn)
    m = _complex_array(phasors, "phasors", fn)
    f = _freqs(frequencies_hz, fn)
    P = _int(n_paths, "n_paths", fn, 1, 8)
    F = f.size
    if m.ndim == 0 or m.shape[0] != F:
        raise ValueError("%s: phasors must be (F, ...) with F = %d (got shape %s)" % (fn, F, m.shape))
    if F < 2 * P:
        raise ValueError("%s: %d paths need at least %d frequencies (got %d)" % (fn, P, 2 * P, F))
    order = np.argsort(f)
    f = f[order]
    m = m[order]
    df = np.diff(f)
    if np.abs(df - df.mean()).max() > 1e-6 * df.mean():
        raise ValueError("%s: frequencies must be equally spaced (got steps %s)" % (fn, df.tolist()))
    dF = float(df.mean())
    Lp = F // 2 if pencil is None else _int(pencil, "pencil", fn, P, F - P)
    if not (P <= Lp <= F - P):
        raise ValueError("%s: pencil %d must be in [%d, %d]" % (fn, Lp, P, F - P))
    shp = m.shape[1:]
    X = m.reshape(F, -1).T                                                    # (N, F)
    N = X.shape[0]
    if N > MAX_PIXELS:
        raise ValueError("%s: %d pixels (> %d)" % (fn, N, MAX_PIXELS))
    idx = np.arange(F - Lp)[:, None] + np.arange(Lp + 1)[None, :]
    Y = X[:, idx]                                                             # (N, F-L, L+1)
    _, _, Vh = np.linalg.svd(Y, full_matrices=False)
    V = np.swapaxes(Vh[:, :P, :], 1, 2)                                       # (N, L+1, P): 行空間 = Vandermonde の列
    V1, V2 = V[:, :-1, :], V[:, 1:, :]
    Z = np.linalg.eigvals(np.linalg.pinv(V1) @ V2)                            # (N, P)
    kc = 4.0 * np.pi * dF / C_LIGHT
    dc = np.mod(np.angle(Z), 2.0 * np.pi) / kc
    kk = np.arange(F) - 0.5 * (F - 1)                                          # 中央の周波数を原点に(α の位相 = 4π f_c d / c)
    fc = float(f.mean())
    k0 = 4.0 * np.pi * fc / C_LIGHT
    # 振幅: Vandermonde の最小二乗(z を単位円に載せる = 減衰なしの模型)
    zu = np.exp(1j * kc * dc)
    Vd = zu[:, None, :] ** kk[None, :, None]                                 # (N, F, P)
    alpha = np.linalg.lstsq(Vd[0], X[0], rcond=None)[0][None] if N == 1 else None
    if alpha is None:
        VhV = np.conj(np.swapaxes(Vd, 1, 2)) @ Vd
        rhs = (np.conj(np.swapaxes(Vd, 1, 2)) @ X[:, :, None])[..., 0]
        alpha = np.linalg.solve(VhV + 1e-12 * np.eye(P)[None] * np.abs(VhV).max(), rhs[..., None])[..., 0]
    fit = (Vd @ alpha[:, :, None])[..., 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        resid = np.linalg.norm(X - fit, axis=1) / np.maximum(np.linalg.norm(X, axis=1), 1e-300)
    pf = C_LIGHT / (2.0 * fc)
    fine0 = np.mod(np.angle(alpha), 2.0 * np.pi) / k0
    nn = np.round((dc - fine0) / pf)
    dfine = fine0 + nn * pf
    srt = np.argsort(dfine, axis=1)
    dfine = np.take_along_axis(dfine, srt, 1)
    dc = np.take_along_axis(dc, srt, 1)
    amp = np.take_along_axis(np.abs(alpha), srt, 1)
    return {"depth": dfine.T.reshape((P,) + shp), "depth_coarse": dc.T.reshape((P,) + shp),
            "amplitude": amp.T.reshape((P,) + shp), "residual": resid.reshape(shp),
            "ambiguity_coarse": C_LIGHT / (2.0 * dF), "resolution": C_LIGHT / (2.0 * F * dF),
            "frequencies_hz": f}


# ───────────────────────────── フライングピクセル ─────────────────────────────
def itof_flying_pixel_mask(depth, threshold_m=0.04, rel_threshold=0.0, radius=1, plateau_ratio=0.5,
                           depth_sigma=None, n_sigma=3.0):
    """距離の図 → フライングピクセル(前景と背景の**間に浮いた**画素)の印 ``(H, W)``(1.0 = 浮いている)。

    画素の視野が段差をまたぐと、iToF は 2 つの位相のフェーザ和を返し、距離は前景と背景の**間**に出る
    (段差の縁に沿って宙に浮いた点の列ができる)。ある方向(横・縦・2 つの斜め)の両側 ±r 画素の距離
    ``a``・``b`` に対して、次の 3 つがそろったとき印をつける:

    1. ``d`` が**両者の間**にある(``(d − a)(d − b) < 0``)。
    2. 両側との差がどちらも閾値 ``τ = max(threshold_m, rel_threshold · d, n_sigma · σ_d)`` を越える。*depth_sigma*
       (画素ごとの距離の雑音、:func:`itof_phase_amplitude` の ``depth_sigma`` から作る)を渡すと、信号の弱い所
       (遠い床・暗い印刷)で雑音を段差と取り違えない。
    3. **両側が平らな台地**: その先の ±2r 画素との差 ``|a − a₂|``・``|b − b₂|`` が、それぞれ ``|d − a|``・``|d − b|`` の
       *plateau_ratio* 倍以下。★斜面(床を浅い角度で見る・傾いた面)は 1・2 を満たしてしまうが、斜面なら
       ``|a − a₂| ≈ |d − a|``(同じ傾きが続く)なので 3 で落ちる。段差の縁の混合は、両側が前景と背景の平らな面なので残る。

    r = 1〜*radius* を全部見る(縁の混合が 2 画素に広がる場合)。段差の上の正しい画素(前景か背景のどちらかに等しい)は、
    片側との差が 0 なので印がつかない。★幅 1〜2 画素の細い物(線・棒)は両側が背景で「間」にならないので、この判定では
    拾えない。

    **Raises** ``ValueError``: depth が 2 次元でない・非有限 / 閾値が負・両方 0 / radius が 1〜4 でない /
    plateau_ratio が (0, 1] でない / depth_sigma の形が合わない・負 / n_sigma が負。
    """
    fn = "itof_flying_pixel_mask"
    d = _real_array(depth, "depth", fn)
    if d.ndim != 2:
        raise ValueError("%s: depth must be 2-D (got shape %s)" % (fn, d.shape))
    t_abs = _num(threshold_m, "threshold_m", fn, lo=0.0)
    t_rel = _num(rel_threshold, "rel_threshold", fn, lo=0.0, hi=10.0)
    if t_abs == 0.0 and t_rel == 0.0:
        raise ValueError("%s: threshold_m and rel_threshold cannot both be 0" % fn)
    R = _int(radius, "radius", fn, 1, 4)
    q = _num(plateau_ratio, "plateau_ratio", fn, lo=0.0, hi=1.0, lo_open=True)
    tau = np.maximum(t_abs, t_rel * np.abs(d))
    if depth_sigma is not None:
        ns = _num(n_sigma, "n_sigma", fn, lo=0.0, hi=100.0)
        sg = _real_array(depth_sigma, "depth_sigma", fn)
        if sg.ndim not in (0, 2) or (sg.ndim == 2 and sg.shape != d.shape) or (sg < 0).any():
            raise ValueError("%s: depth_sigma must be >= 0, a scalar or the shape of depth %s (got %s)"
                             % (fn, d.shape, sg.shape))
        tau = np.maximum(tau, ns * sg)
    mask = np.zeros(d.shape, dtype=bool)
    pad = np.pad(d, 2 * R, mode="edge")
    H, W = d.shape
    o = 2 * R

    def at(sy, sx):
        return pad[o + sy:o + sy + H, o + sx:o + sx + W]

    for r in range(1, R + 1):
        for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
            a, b = at(-r * dy, -r * dx), at(r * dy, r * dx)
            a2, b2 = at(-2 * r * dy, -2 * r * dx), at(2 * r * dy, 2 * r * dx)
            da, db = np.abs(d - a), np.abs(d - b)
            between = (d - a) * (d - b) < 0
            flat = (np.abs(a - a2) <= q * da) & (np.abs(b - b2) <= q * db)
            mask |= between & (da > tau) & (db > tau) & flat
    return mask.astype(np.float64)


# ───────────────────────────── 高調波の周期誤差 ─────────────────────────────
def _model_lut(wf, th, n=8192):
    """真の位相 → K 段の推定の位相(波形 wf の相関)。単調でなければ ValueError。"""
    phi = 2.0 * np.pi * np.arange(n) / n
    Mx = np.stack([np.ones_like(th), np.cos(th), np.sin(th)], 1)
    Pm = np.linalg.pinv(Mx)
    vals = _corr(phi[:, None] - th[None, :], wf)                            # (n, K)
    co = vals @ Pm.T                                                         # (n, 3)
    est = np.unwrap(np.arctan2(co[:, 2], co[:, 1]))
    est = est - 2.0 * np.pi * np.floor(est[0] / (2.0 * np.pi) + 0.5)
    return phi, est


def itof_wiggling_correct(phase, frequencies_hz=None, waveform="square", n_phases=4, calibration=None,
                          n_harmonics=2):
    """高調波による周期誤差(wiggling)を補正した位相と距離。``table`` を返す。

    変調と復調が矩形波だと、相関は三角波(``waveform="square"``)になり、K 段の推定は奇数次の高調波を基本波に
    折り返す。4 段なら真の位相 φ が第 1 象限にあるとき ``u = 2φ/π`` として推定は ``atan(u / (1 − u))`` になり、
    誤差は周期 π/2 で波打つ(最大 ±0.071 rad 程度、20 MHz で ±8.5 cm)。

    * 模型(*calibration* なし): *waveform* の相関で「真の位相 → 推定の位相」の表を作り(単調でなければ拒否)、逆に引く。
    * 較正(*calibration* = ``(measured_phase, true_phase)``、同じ周波数の 1-D の組): 誤差 ``e(φ_m)`` を
      ``c_0 + Σ_{j=1..J} (a_j cos(jKφ_m) + b_j sin(jKφ_m))``(周期 2π/K の調和、J = *n_harmonics*)で最小二乗に当て、
      ``φ_m − e(φ_m)`` を返す(c_0 は距離のオフセット = 系の遅延)。

    *phase* は :func:`itof_phase_amplitude` の表か、``(F, ...)`` の位相の配列(周波数ごとに同じ補正)。

    返す ``dict``: ``phase``(補正後、[0, 2π))、``depth``(周波数が分かれば、折り返したまま)、``correction``(足した量)、
    ``model``(``"lut"`` か ``"fit"``)、``coefficients``(較正のとき)、``fit_rms``(較正の残差 [rad])。

    **Raises** ``ValueError``: 位相が非有限 / waveform が不正・推定が単調でない / 較正の組の形が合わない・
    未知数より少ない / n_harmonics が 1〜8 でない。
    """
    fn = "itof_wiggling_correct"
    if isinstance(phase, dict):
        if phase.get("kind") != PHASE_KIND:
            raise ValueError("%s: dict input must come from itof_phase_amplitude (kind %r)" % (fn, PHASE_KIND))
        if frequencies_hz is None:
            frequencies_hz = phase.get("frequencies_hz")
        th = np.asarray(phase.get("phase_offsets_rad"), dtype=np.float64)
        phase = phase["phase"]
    else:
        th = _steps(n_phases, None, fn)
    ph = _real_array(phase, "phase", fn)
    K = th.size
    ph = np.mod(ph, 2.0 * np.pi)
    if calibration is None:
        wf = _waveform(waveform, fn)
        tphi, est = _model_lut(wf, th)
        if not (np.diff(est) > 0).all():
            raise ValueError("%s: the %s waveform gives a non-monotonic phase estimate with %d steps — "
                             "cannot invert" % (fn, waveform if isinstance(waveform, str) else "given", K))
        e_ext = np.concatenate([est - 2 * np.pi, est, est + 2 * np.pi])
        t_ext = np.concatenate([tphi - 2 * np.pi, tphi, tphi + 2 * np.pi])
        corr = np.mod(np.interp(ph, e_ext, t_ext), 2.0 * np.pi)
        out = {"phase": corr, "correction": _wrap(corr - ph), "model": "lut", "coefficients": None,
               "fit_rms": None}
    else:
        J = _int(n_harmonics, "n_harmonics", fn, 1, 8)
        if not isinstance(calibration, (tuple, list)) or len(calibration) != 2:
            raise ValueError("%s: calibration must be (measured_phase, true_phase)" % fn)
        pm = np.mod(_real_array(calibration[0], "calibration[0]", fn).ravel(), 2.0 * np.pi)
        pt = _real_array(calibration[1], "calibration[1]", fn).ravel()
        if pm.size != pt.size or pm.size < 2 * J + 2:
            raise ValueError("%s: calibration needs matching pairs, at least %d (got %d and %d)"
                             % (fn, 2 * J + 2, pm.size, pt.size))
        e = _wrap(pm - pt)

        def design(x):
            cols = [np.ones_like(x)]
            for j in range(1, J + 1):
                cols += [np.cos(j * K * x), np.sin(j * K * x)]
            return np.stack(cols, axis=-1)

        coef, *_ = np.linalg.lstsq(design(pm), e, rcond=None)
        rms = float(np.sqrt(np.mean((design(pm) @ coef - e) ** 2)))
        corr_amt = design(ph) @ coef
        corr = np.mod(ph - corr_amt, 2.0 * np.pi)
        out = {"phase": corr, "correction": -corr_amt, "model": "fit", "coefficients": coef, "fit_rms": rms}
    if frequencies_hz is not None:
        f = _freqs(frequencies_hz, fn)
        if ph.ndim == 0 or ph.shape[0] != f.size:
            raise ValueError("%s: phase must be (F, ...) with F = %d (got shape %s)" % (fn, f.size, ph.shape))
        sc = (C_LIGHT / (4.0 * np.pi * f)).reshape((f.size,) + (1,) * (ph.ndim - 1))
        out["depth"] = out["phase"] * sc
        out["frequencies_hz"] = f
    return out
