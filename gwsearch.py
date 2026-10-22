# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gwsearch —— 色つき雑音に埋もれた既知波形を「雑音の PSD で割って」見つける(整合フィルタ)。

重力波望遠鏡の信号処理は、1-D の古典信号処理そのものである: 雑音の PSD を Welch 法で測り、
PSD の平方根で割って白色化し(``whiten_by_psd``)、既知波形(チャープ)との相関を PSD で
重み付けして SNR の時系列にする(``matched_filter_snr``)。GW150914 はこの手順で
SNR 24 の山として現れた(Abbott ら 2016 *Phys. Rev. Lett.* 116, 061102)。
fullseye の ``dsp`` には帯域通過・スペクトル・ピークはあったが、**PSD での白色化と整合フィルタ**
は無かった(2026-10-14 時点で repo 全層 0 件 —— ``flyvision.fly_matched_filter`` は画像の
方向場の整合であって時系列ではない)。振動計・AE・超音波の「色つき雑音の中の既知の波形」
にそのまま使える。

収めた式(``tests/test_gwsearch.py`` が確かめる):

  1. **Welch の PSD**(``psd_welch``): 片側 PSD [1/Hz]。白色ガウス雑音(分散 σ²、標本化 fs)で
     ``S = 2σ²/fs``(**門**、平均 2 % 以内)。
  2. **白色化**(``whiten_by_psd``): ``x_w = irfft(rfft(x)·√(2Δt/S(f)))``。色つきガウス雑音を
     白色化すると**分散 1・スペクトル平ら**(門)。
  3. **ニュートン近似のチャープ**(``chirp_newtonian``): チャープ質量 ``M_c = (m₁m₂)^{3/5}/(m₁+m₂)^{1/5}``、
     周波数 ``f(τ) = (1/π)(5/256τ)^{3/8}(GM_c/c³)^{−5/8}``(τ = 合体までの時間)、振幅
     ``A = (4/d)(GM_c/c²)^{5/3}(πf/c)^{2/3}``、位相 ``Φ = −2(5GM_c/c³)^{−5/8}τ^{5/8}``、
     最終安定円軌道 ``f_ISCO = c³/(6^{3/2}πGM)`` で止める。**門**: 零交差から測った瞬時周波数の
     ``df/dt = (96/5)π^{8/3}(GM_c/c³)^{5/3}f^{11/3}``(PRL 116, 061102 式 1)。
  4. **周波数の軌跡からチャープ質量**(``chirp_mass_from_track``): ``f^{−8/3}`` は t の 1 次
     (``f^{−8/3} = (8/3)·(96/5)π^{8/3}(GM_c/c³)^{5/3}·(t_c − t)``)なので最小二乗で傾きを取り
     ``M_c`` と ``t_c`` を返す(門: 合成の軌跡で 1e-6)。
  5. **整合フィルタ**(``matched_filter_snr`` / ``optimal_snr``): 内積 ``⟨a|b⟩ = 4Re∫ÃB̃*/S df``、
     ``σ² = ⟨h|h⟩``(最適 SNR)、``ρ(t) = ⟨d|h_t⟩/σ`` を位相で最大化(解析信号の絶対値)。
     **門**: 白色雑音に σ = 30 で埋めたテンプレートは、埋めた時刻に 30 ± 4(統計 1σ = 1)の
     山、時刻のずれ 0 標本。
  6. **2 検出器の到達時間差**(``coincidence_delay``): 片方の山の ±max_delay 以内で他方の山を
     探し、放物線で副標本の時刻差。GW150914 の H1→L1 は公表 6.9 (+0.5/−0.4) ms、
     光の走行時間 10 ms が上限。

型語彙(**新語はゼロ**): ``signal``(1-D 実配列)、``pairs``((N, 2) の曲線 = PSD や
周波数の軌跡)、``table``、``measurement``。
"""
from __future__ import annotations

import numpy as np

__all__ = ["psd_welch", "whiten_by_psd", "chirp_newtonian", "chirp_mass_from_track",
           "matched_filter_snr", "optimal_snr", "coincidence_delay"]

#: 万有引力定数 [m³ kg⁻¹ s⁻²] (CODATA 2018)
G_NEWTON = 6.67430e-11
#: 光速 [m/s]
C_LIGHT = 299792458.0
#: 太陽質量 [kg] (IAU 2015 名目値 GM☉ / G)
M_SUN = 1.98847e30
#: メガパーセク [m]
MPC = 3.0856775814913673e22

_MAX_SAMPLES = 1 << 26


# --------------------------------------------------------------------------- #
# 入口の検査(fail-closed)                                                     #
# --------------------------------------------------------------------------- #
def _positive(v, name: str, op: str) -> float:
    f = float(v)
    if not np.isfinite(f) or f <= 0.0:
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return f


def _as_signal(x, name: str, op: str, min_len: int = 2) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64).reshape(-1) if np.ndim(x) <= 1 else np.asarray(x, dtype=np.float64)
    if a.ndim != 1:
        raise ValueError("%s: %s must be 1-D, got shape %r" % (op, name, a.shape))
    if a.size < min_len or a.size > _MAX_SAMPLES:
        raise ValueError("%s: %s must have %d..%d samples, got %d" % (op, name, min_len, _MAX_SAMPLES, a.size))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has non-finite values (NaN/Inf)" % (op, name))
    return a


def _as_pairs(p, name: str, op: str, *, positive_y: bool = False, min_rows: int = 2) -> np.ndarray:
    a = np.asarray(p, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError("%s: %s must be (N, 2) pairs, got shape %r" % (op, name, a.shape))
    if a.shape[0] < min_rows:
        raise ValueError("%s: %s needs at least %d rows, got %d" % (op, name, min_rows, a.shape[0]))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has non-finite values" % (op, name))
    if positive_y and (a[:, 1] <= 0.0).any():
        raise ValueError("%s: %s column 1 must be positive" % (op, name))
    return a


def _psd_on_rfft_grid(psd_pairs: np.ndarray, freqs: np.ndarray, op: str) -> np.ndarray:
    f, s = psd_pairs[:, 0], psd_pairs[:, 1]
    if (np.diff(f) <= 0.0).any():
        raise ValueError("%s: psd frequencies must be strictly increasing" % op)
    if (f < 0.0).any():
        raise ValueError("%s: psd frequencies must be non-negative" % op)
    # log 補間(PSD は桁で変わる)。範囲外は端の値で延長する。
    return np.exp(np.interp(freqs, f, np.log(s)))


def _band_mask(freqs: np.ndarray, f_low, f_high, op: str) -> np.ndarray:
    m = np.ones(freqs.shape, dtype=bool)
    if f_low is not None:
        lo = _positive(f_low, "f_low_hz", op)
        m &= freqs >= lo
    if f_high is not None:
        hi = _positive(f_high, "f_high_hz", op)
        if f_low is not None and hi <= float(f_low):
            raise ValueError("%s: f_high_hz must exceed f_low_hz" % op)
        m &= freqs <= hi
    if m.sum() < 2:
        raise ValueError("%s: the band [f_low_hz, f_high_hz] keeps fewer than 2 frequency bins" % op)
    return m


# --------------------------------------------------------------------------- #
# 1. Welch の PSD                                                              #
# --------------------------------------------------------------------------- #
def psd_welch(x, rate: float = 4096.0, segment_s: float | None = None, *, overlap: float = 0.5,
              window: str = "hann", average: str = "mean") -> np.ndarray:
    """Welch 法の片側 PSD を ``pairs``(周波数 [Hz], S [1/Hz])で返す。

    Parameters
    ----------
    x : array_like
        時系列(1-D)。
    rate : float
        標本化周波数 fs [Hz]。
    segment_s : float or None
        1 区間の長さ [s] (周波数分解能 = 1/segment_s)。``None`` なら **4 s と信号長の 1/8 の短い方**
        (重力波の慣例 4 s、短い信号でも 8 区間は取る)。信号より長ければ信号全長に切り詰める。
    overlap : float
        区間の重なり(0 ≤ overlap < 1)。
    window : str
        窓("hann" / "hamming" / "blackman" / "boxcar"、scipy の名前)。
    average : str
        区間の平均 "mean" か "median"(グリッチに強い。scipy は median の偏り補正つき)。

    Returns
    -------
    numpy.ndarray
        ``(n_freq, 2)``。白色ガウス雑音(分散 σ²)で ``S = 2σ²/fs``(片側)。

    Notes
    -----
    重力波の標準手順(GWOSC の例題)と同じ ``scaling="density"``。分解能 1/segment_s より
    細い線(60 Hz の電源線など)は幅がこの分解能に広がる。
    """
    from scipy import signal as _sig

    op = "psd_welch"
    a = _as_signal(x, "x", op, min_len=8)
    fs = _positive(rate, "rate", op)
    seg = (min(4.0, a.size / (8.0 * fs)) if segment_s is None else _positive(segment_s, "segment_s", op))
    ov = float(overlap)
    if not np.isfinite(ov) or ov < 0.0 or ov >= 1.0:
        raise ValueError("%s: overlap must be in [0, 1), got %r" % (op, overlap))
    if average not in ("mean", "median"):
        raise ValueError("%s: average must be 'mean' or 'median', got %r" % (op, average))
    nper = int(min(round(seg * fs), a.size))
    if nper < 8:
        raise ValueError("%s: segment_s*rate must be at least 8 samples, got %d" % (op, nper))
    try:
        f, s = _sig.welch(a, fs=fs, window=window, nperseg=nper, noverlap=int(ov * nper),
                          scaling="density", average=average)
    except ValueError as e:
        raise ValueError("%s: %s" % (op, e))
    return np.stack([f, s], axis=1)


# --------------------------------------------------------------------------- #
# 2. 白色化                                                                    #
# --------------------------------------------------------------------------- #
def whiten_by_psd(x, psd, rate: float = 4096.0) -> np.ndarray:
    """雑音の PSD で割って白色化する(``x_w = irfft(rfft(x)·√(2Δt/S(f)))``)。

    Parameters
    ----------
    x : array_like
        時系列(1-D)。
    psd : array_like
        片側 PSD の ``pairs``(``psd_welch`` の返り)。rfft の格子へ log 補間する。
    rate : float
        標本化周波数 [Hz]。

    Returns
    -------
    numpy.ndarray
        白色化した時系列(x と同じ長さ)。雑音がこの PSD に従うガウス過程なら**分散 1**。

    Notes
    -----
    端の数区間は FFT の循環のため乱れる(重力波の実データでは Tukey 窓で落とすのが慣例)。
    """
    op = "whiten_by_psd"
    a = _as_signal(x, "x", op, min_len=8)
    p = _as_pairs(psd, "psd", op, positive_y=True)
    fs = _positive(rate, "rate", op)
    dt = 1.0 / fs
    freqs = np.fft.rfftfreq(a.size, d=dt)
    s = _psd_on_rfft_grid(p, freqs, op)
    xw = np.fft.irfft(np.fft.rfft(a) * np.sqrt(2.0 * dt / s), n=a.size)
    return xw


# --------------------------------------------------------------------------- #
# 3. ニュートン近似のチャープ                                                  #
# --------------------------------------------------------------------------- #
def _chirp_mass(mass1_msun: float, mass2_msun: float) -> float:
    """チャープ質量 ``(m₁m₂)^{3/5}/(m₁+m₂)^{1/5}``(内部用、単位は太陽質量)。"""
    m1, m2 = float(mass1_msun), float(mass2_msun)
    return (m1 * m2) ** 0.6 / (m1 + m2) ** 0.2


def chirp_newtonian(mass1_msun: float = 36.0, mass2_msun: float = 29.0, rate: float = 4096.0,
                    duration_s: float = 1.0, *, f_low_hz: float = 20.0,
                    distance_mpc: float = 410.0, phase_rad: float = 0.0) -> np.ndarray:
    """ニュートン近似(0PN)のインスパイラル波形 h₊(t) を ``signal`` で返す(合体が配列の末尾)。

    Parameters
    ----------
    mass1_msun, mass2_msun : float
        成分質量 [M☉] (検出器系)。
    rate : float
        標本化周波数 [Hz]。
    duration_s : float
        配列の長さ [s]。f_low からの時間がこれより長ければ ``f_low`` を押し上げる。
    f_low_hz : float
        波形を始める重力波周波数 [Hz] (軌道周波数の 2 倍)。
    distance_mpc : float
        光度距離 [Mpc] (振幅だけに効く)。
    phase_rad : float
        合体時の位相。

    Returns
    -------
    numpy.ndarray
        ``round(duration_s·rate)`` 点。``f_ISCO = c³/(6^{3/2}πG(m₁+m₂))`` で止め、以降は 0。
        合体時刻は最後の標本(``index n−1``)。

    Notes
    -----
    ``f(τ) = (1/π)(5/256τ)^{3/8}(GM_c/c³)^{−5/8}``、``A = (4/d)(GM_c/c²)^{5/3}(πf/c)^{2/3}``、
    ``Φ(τ) = −2(5GM_c/c³)^{−5/8}τ^{5/8} + φ₀``。合体・リングダウンは含まない(これが
    GW150914 の SNR を数値相対論の波形より小さく見積もる理由 —— PoC が数で示す)。
    """
    op = "chirp_newtonian"
    m1 = _positive(mass1_msun, "mass1_msun", op)
    m2 = _positive(mass2_msun, "mass2_msun", op)
    fs = _positive(rate, "rate", op)
    dur = _positive(duration_s, "duration_s", op)
    f_low = _positive(f_low_hz, "f_low_hz", op)
    d = _positive(distance_mpc, "distance_mpc", op) * MPC
    phi0 = float(phase_rad)
    if not np.isfinite(phi0):
        raise ValueError("%s: phase_rad must be finite" % op)
    n = int(round(dur * fs))
    if n < 16 or n > _MAX_SAMPLES:
        raise ValueError("%s: duration_s*rate must give 16..%d samples, got %d" % (op, _MAX_SAMPLES, n))
    mc = _chirp_mass(m1, m2) * M_SUN
    mt = (m1 + m2) * M_SUN
    tc_mc = G_NEWTON * mc / C_LIGHT ** 3            # チャープ質量の時間 [s]
    f_isco = C_LIGHT ** 3 / (6.0 ** 1.5 * np.pi * G_NEWTON * mt)
    if f_isco <= f_low:
        raise ValueError("%s: f_low_hz=%g is above f_ISCO=%.1f Hz for this total mass" % (op, f_low, f_isco))
    if f_isco > 0.5 * fs:
        raise ValueError("%s: f_ISCO=%.1f Hz exceeds Nyquist %.1f Hz" % (op, f_isco, 0.5 * fs))
    tau = (np.arange(n)[::-1]) / fs                 # 合体までの時間(末尾で 0)
    tau_low = (5.0 / 256.0) * tc_mc ** (-5.0 / 3.0) * (np.pi * f_low) ** (-8.0 / 3.0)
    tau_isco = (5.0 / 256.0) * tc_mc ** (-5.0 / 3.0) * (np.pi * f_isco) ** (-8.0 / 3.0)
    live = (tau <= tau_low) & (tau >= tau_isco)
    h = np.zeros(n)
    t = tau[live]
    f = (1.0 / np.pi) * (5.0 / (256.0 * t)) ** (3.0 / 8.0) * tc_mc ** (-5.0 / 8.0)
    amp = (4.0 / d) * (G_NEWTON * mc / C_LIGHT ** 2) ** (5.0 / 3.0) * (np.pi * f / C_LIGHT) ** (2.0 / 3.0)
    phase = -2.0 * (5.0 * tc_mc) ** (-5.0 / 8.0) * t ** (5.0 / 8.0) + phi0
    h[live] = amp * np.cos(phase)
    return h


# --------------------------------------------------------------------------- #
# 4. 周波数の軌跡 → チャープ質量                                                #
# --------------------------------------------------------------------------- #
def chirp_mass_from_track(track) -> dict:
    """重力波周波数の軌跡 (t, f) からチャープ質量と合体時刻を最小二乗で返す。

    Parameters
    ----------
    track : array_like
        ``(N, 2)`` の ``pairs``: 列 0 = 時刻 [s]、列 1 = 重力波周波数 [Hz] (正)。N ≥ 3。

    Returns
    -------
    dict
        ``chirp_mass_msun``、``coalescence_time_s``(t_c = a/b)、``slope``(b)、
        ``residual_rms``(``f^{−8/3}`` の当てはめ残差)、``n_points``、``rising``(周波数が
        時間とともに上がる軌跡か)。**上がらない軌跡はインスパイラルではない**ので
        ``rising = False`` とし、``chirp_mass_msun`` と ``coalescence_time_s`` は ``None``
        (例外にはしない —— 「鳴いていない」は正しい答え)。

    Notes
    -----
    ``f^{−8/3} = a − b·t``、``b = (8/3)(96/5)π^{8/3}(GM_c/c³)^{5/3}``。PRL 116, 061102 の
    式 (1) の積分形。
    """
    op = "chirp_mass_from_track"
    p = _as_pairs(track, "track", op, positive_y=True, min_rows=3)
    t, f = p[:, 0], p[:, 1]
    y = f ** (-8.0 / 3.0)
    A = np.stack([np.ones_like(t), -t], axis=1)
    coef, _res, rank, _sv = np.linalg.lstsq(A, y, rcond=None)
    if rank < 2:
        raise ValueError("%s: the track is degenerate (all times equal?)" % op)
    a, b = float(coef[0]), float(coef[1])
    resid = y - (a - b * t)
    out = {"chirp_mass_msun": None, "coalescence_time_s": None, "slope": b,
           "residual_rms": float(np.sqrt(np.mean(resid ** 2))), "n_points": int(t.size),
           "rising": bool(np.isfinite(b) and b > 0.0)}
    if out["rising"]:
        k = (8.0 / 3.0) * (96.0 / 5.0) * np.pi ** (8.0 / 3.0)
        tc_mc = (b / k) ** 0.6
        out["chirp_mass_msun"] = float(tc_mc * C_LIGHT ** 3 / G_NEWTON / M_SUN)
        out["coalescence_time_s"] = float(a / b)
    return out


# --------------------------------------------------------------------------- #
# 5. 整合フィルタ                                                              #
# --------------------------------------------------------------------------- #
def _taper(d: np.ndarray, taper_s, fs: float, op: str) -> np.ndarray:
    """両端を余弦で 0 へ落とす(Tukey 窓の端)。FFT の循環で端の不連続が全体へ漏れるのを抑える。"""
    ts = float(taper_s)
    if not np.isfinite(ts) or ts < 0.0:
        raise ValueError("%s: taper_s must be a non-negative finite number, got %r" % (op, taper_s))
    m = int(round(ts * fs))
    if m == 0:
        return d
    if 2 * m >= d.size:
        raise ValueError("%s: taper_s*rate*2 (%d) must be shorter than the data (%d)" % (op, 2 * m, d.size))
    w = np.ones(d.size)
    ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(m) / m))
    w[:m] = ramp
    w[-m:] = ramp[::-1]
    return d * w


def _inner_setup(data, template, psd, rate, f_low, f_high, op, taper_s=0.0):
    d = _as_signal(data, "data", op, min_len=16)
    fs0 = _positive(rate, "rate", op)
    d = _taper(d, taper_s, fs0, op)
    h = _as_signal(template, "template", op, min_len=2)
    if h.size > d.size:
        raise ValueError("%s: template (%d) is longer than data (%d)" % (op, h.size, d.size))
    if not (h != 0.0).any():
        raise ValueError("%s: template is identically zero" % op)
    p = _as_pairs(psd, "psd", op, positive_y=True)
    fs = _positive(rate, "rate", op)
    dt = 1.0 / fs
    n = d.size
    freqs = np.fft.rfftfreq(n, d=dt)
    s = _psd_on_rfft_grid(p, freqs, op)
    mask = _band_mask(freqs, f_low, f_high, op)
    hpad = np.zeros(n)
    hpad[:h.size] = h
    D = np.fft.rfft(d) * dt
    H = np.fft.rfft(hpad) * dt
    df = fs / n
    w = np.where(mask, 1.0 / s, 0.0)
    sigma2 = 4.0 * df * float(np.sum(np.abs(H) ** 2 * w))
    if not np.isfinite(sigma2) or sigma2 <= 0.0:
        raise ValueError("%s: the template has no power inside the band" % op)
    return D, H, w, np.sqrt(sigma2), n, dt


def optimal_snr(template, psd, rate: float = 4096.0, *, f_low_hz: float | None = 20.0,
                f_high_hz: float | None = None) -> float:
    """テンプレートの最適 SNR ``σ = √(4∫|h̃|²/S df)``(``measurement``)。

    Parameters
    ----------
    template : array_like
        波形(1-D)。
    psd : array_like
        片側 PSD の ``pairs``。
    rate : float
        標本化周波数 [Hz]。
    f_low_hz, f_high_hz : float or None
        内積を取る帯域(None は端まで)。

    Returns
    -------
    float
        この PSD の雑音に対し、位相・時刻が既知のときに期待される SNR。
    """
    op = "optimal_snr"
    h = _as_signal(template, "template", op, min_len=16)
    _D, _H, _w, sigma, _n, _dt = _inner_setup(h, h, psd, rate, f_low_hz, f_high_hz, op)
    return float(sigma)


def matched_filter_snr(data, template, psd, rate: float = 4096.0, *, f_low_hz: float | None = 20.0,
                       f_high_hz: float | None = None, template_ref_index: int | None = None,
                       taper_s: float = 0.0) -> np.ndarray:
    """整合フィルタの SNR 時系列 |ρ(t)|(位相で最大化)を ``signal`` で返す。

    Parameters
    ----------
    data : array_like
        観測時系列(1-D)。
    template : array_like
        テンプレート(data 以下の長さ。末尾を 0 で埋めて同じ長さにする)。
    psd : array_like
        雑音の片側 PSD の ``pairs``(``psd_welch``)。
    rate : float
        標本化周波数 [Hz]。
    f_low_hz, f_high_hz : float or None
        内積の帯域。
    template_ref_index : int or None
        テンプレート内の「事象の時刻」の標本番号(None なら ``argmax |h|``)。返り値はこの分だけ
        回してあり、**|ρ| の山の標本番号 = data 内の事象の時刻**になる。
    taper_s : float
        data の両端を余弦で 0 へ落とす長さ [s] (Tukey 窓の端)。実データの端の不連続が
        FFT の循環で全体に漏れるのを抑える(GWOSC の例題は 32 s に対し 2 s)。

    Returns
    -------
    numpy.ndarray
        data と同じ長さの非負配列。``ρ(t) = ⟨d|h_t⟩/σ``、``⟨a|b⟩ = 4Re∫ÃB̃*/S df``、
        ``σ = optimal_snr``。位相は解析信号で最大化する(``|z|``)。テンプレートが data の外へ
        はみ出す時刻(先頭の ``ref`` 標本と末尾の ``len(template) − ref − 1`` 標本)は循環の折り返し
        なので **0** にしてある(山の探索に混じらない)。

    Notes
    -----
    白色ガウス雑音だけなら |ρ| の典型値は ~1.25(レイリー)、閾値 8 が重力波探索の慣例。
    """
    op = "matched_filter_snr"
    D, H, w, sigma, n, dt = _inner_setup(data, template, psd, rate, f_low_hz, f_high_hz, op, taper_s)
    h = np.asarray(template, dtype=np.float64).reshape(-1)
    if template_ref_index is None:
        ref = int(np.argmax(np.abs(h)))
    else:
        ref = int(template_ref_index)
        if ref != float(template_ref_index) or ref < 0 or ref >= h.size:
            raise ValueError("%s: template_ref_index must be in [0, %d), got %r" % (op, h.size, template_ref_index))
    Y = D * np.conj(H) * w
    full = np.zeros(n, dtype=complex)
    full[:Y.size] = Y
    z = np.fft.ifft(full) * (4.0 / dt) / sigma      # 解析信号(片側スペクトルの逆 FFT)
    snr = np.roll(np.abs(z), ref)
    m = h.size
    snr[:ref] = 0.0
    tail = m - ref - 1
    if tail > 0:
        snr[n - tail:] = 0.0
    return snr


# --------------------------------------------------------------------------- #
# 6. 2 検出器の到達時間差                                                      #
# --------------------------------------------------------------------------- #
def coincidence_delay(snr_a, snr_b, rate: float = 4096.0, *, max_delay_s: float = 0.010) -> dict:
    """2 本の SNR 時系列の山の時刻差(b − a)を副標本精度で返す。

    Parameters
    ----------
    snr_a, snr_b : array_like
        ``matched_filter_snr`` の返り(同じ長さ・同じ標本化)。
    rate : float
        標本化周波数 [Hz]。
    max_delay_s : float
        a の山から b の山を探す窓(±)[s]。LIGO H1–L1 は光の走行時間 10 ms。

    Returns
    -------
    dict
        ``delay_s``(副標本、放物線)、``delay_samples``(整数)、``peak_a`` / ``peak_b``(山の高さ)、
        ``index_a`` / ``index_b``、``network_snr`` = √(peak_a² + peak_b²)、``window_samples``
        (探した窓の片側の標本数 = round(max_delay_s·rate))。
    """
    op = "coincidence_delay"
    a = _as_signal(snr_a, "snr_a", op, min_len=3)
    b = _as_signal(snr_b, "snr_b", op, min_len=3)
    if a.size != b.size:
        raise ValueError("%s: snr_a and snr_b must have the same length (%d vs %d)" % (op, a.size, b.size))
    fs = _positive(rate, "rate", op)
    md = _positive(max_delay_s, "max_delay_s", op)
    win = int(round(md * fs))
    if win < 1:
        raise ValueError("%s: max_delay_s*rate must be at least 1 sample" % op)
    ia = int(np.argmax(a))
    lo, hi = max(0, ia - win), min(b.size, ia + win + 1)
    ib = lo + int(np.argmax(b[lo:hi]))

    def _sub(x, i):
        if 0 < i < x.size - 1:
            y0, y1, y2 = x[i - 1], x[i], x[i + 1]
            den = y0 - 2.0 * y1 + y2
            if den < 0.0:
                return i + 0.5 * (y0 - y2) / den
        return float(i)

    sa, sb = _sub(a, ia), _sub(b, ib)
    return {"delay_s": float((sb - sa) / fs), "delay_samples": int(ib - ia),
            "peak_a": float(a[ia]), "peak_b": float(b[ib]), "index_a": ia, "index_b": ib,
            "network_snr": float(np.hypot(a[ia], b[ib])), "window_samples": int(win)}
