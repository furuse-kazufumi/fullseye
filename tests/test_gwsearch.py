# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gwsearch(PSD・白色化・チャープ・整合フィルタ・到達時間差)の門。

真値は閉形式と統計の期待値: 白色雑音の PSD は 2σ²/fs、白色化した色つき雑音は分散 1 で平ら、
ニュートン近似のチャープの瞬時周波数(零交差から独立に測る)は df/dt = (96/5)π^{8/3}(GM_c/c³)^{5/3}f^{11/3}
(PRL 116, 061102 式 1)に乗り、軌跡からチャープ質量が戻る。整合フィルタは最適 SNR の定義
(白色雑音でテンプレートのエネルギー/雑音分散)と一致し、埋めた時刻に埋めた高さの山を立てる。
実データ(GW150914)の門は examples/poc_gw_detector_pseudo_simulation.py が持つ(データは repo に無い)。
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gwsearch as W                                               # noqa: E402
import ops1d                                                       # noqa: E402

FS = 4096.0


def _white(seconds, seed, sigma=1.0):
    return sigma * np.random.default_rng(seed).standard_normal(int(seconds * FS))


def _flat_psd(sigma=1.0):
    s0 = 2.0 * sigma * sigma / FS
    return np.array([[0.0, s0], [FS / 2, s0]])


# --------------------------------------------------------------------------- #
# 1. Welch                                                                     #
# --------------------------------------------------------------------------- #
def test_white_noise_psd_is_two_sigma_squared_over_fs():
    for sigma in (1.0, 3.0):
        p = W.psd_welch(_white(32.0, 0, sigma), FS, 4.0)
        assert p.shape[1] == 2 and p.shape[0] == int(4.0 * FS) // 2 + 1
        auto = W.psd_welch(_white(32.0, 0, sigma), FS)                 # None → 4 s(32 s の 1/8 = 4 s)
        assert auto.shape == p.shape and np.allclose(auto, p)
        short = W.psd_welch(_white(2.0, 0, sigma), FS)                 # None → 0.25 s(8 区間)
        assert short.shape[0] == int(0.25 * FS) // 2 + 1
        assert np.isfinite(p).all() and (p[:, 1] > 0).all()
        assert p[1, 0] == pytest.approx(0.25, rel=1e-12)      # 分解能 1/segment_s
        assert float(p[5:, 1].mean()) == pytest.approx(2 * sigma * sigma / FS, rel=0.02), sigma


def test_median_averaging_ignores_a_single_glitch_that_the_mean_does_not():
    """中央値は 1 つのグリッチに動じない(区間 63 本で偏り補正込み 5 % 以内)、平均は 1.5 倍以上に跳ねる。"""
    x = _white(128.0, 1)
    x[60000:60200] += 400.0 * np.sin(np.linspace(0, 40 * np.pi, 200))
    pm = W.psd_welch(x, FS, 4.0, average="mean")
    pd = W.psd_welch(x, FS, 4.0, average="median")
    ref = 2.0 / FS
    assert float(pd[5:, 1].mean()) == pytest.approx(ref, rel=0.05)
    assert float(pm[5:, 1].mean()) > 1.5 * ref


@pytest.mark.parametrize("kw", [dict(rate=0.0), dict(segment_s=0.0), dict(overlap=1.0),
                                dict(average="mode"), dict(window="nosuchwindow")])
def test_welch_rejects_bad_knobs(kw):
    with pytest.raises(ValueError):
        W.psd_welch(_white(2.0, 0), **{**dict(rate=FS, segment_s=1.0), **kw})


def test_welch_rejects_non_finite_input():
    x = _white(2.0, 0)
    x[5] = np.nan
    with pytest.raises(ValueError):
        W.psd_welch(x, FS, 1.0)


# --------------------------------------------------------------------------- #
# 2. 白色化                                                                    #
# --------------------------------------------------------------------------- #
def _coloured(seconds, seed):
    """AR(1) で赤く + 1 本の線(60 Hz)。"""
    from scipy import signal as sg

    w = _white(seconds, seed)
    x = sg.lfilter([1.0], [1.0, -0.98], w)
    t = np.arange(x.size) / FS
    return x + 3.0 * np.sin(2 * np.pi * 60.0 * t)


def test_whitening_with_the_measured_psd_gives_unit_variance_and_a_flat_spectrum():
    x = _coloured(64.0, 2)
    p = W.psd_welch(x, FS, 4.0)
    y = _coloured(32.0, 3)                         # 別の実現、同じ過程
    yw = W.whiten_by_psd(y, p, FS)
    assert yw.shape == y.shape and np.isfinite(yw).all()
    core = yw[int(2 * FS):-int(2 * FS)]
    assert float(core.std()) == pytest.approx(1.0, rel=0.05)
    pw = W.psd_welch(core, FS, 2.0)
    f = pw[:, 0]
    lo = float(pw[(f > 30) & (f < 300), 1].mean())
    hi = float(pw[(f > 500) & (f < 1500), 1].mean())
    assert lo / hi == pytest.approx(1.0, rel=0.15)
    # 元の色: 低域は高域の何十倍も強い(白色化が何かをしたことの証拠)
    po = W.psd_welch(y, FS, 2.0)
    assert float(po[(f > 30) & (f < 300), 1].mean()) > 20 * float(po[(f > 500) & (f < 1500), 1].mean())


def test_whitening_rejects_a_psd_with_zero_or_unsorted_frequencies():
    x = _white(2.0, 0)
    with pytest.raises(ValueError):
        W.whiten_by_psd(x, np.array([[0.0, 1.0], [100.0, 0.0]]), FS)
    with pytest.raises(ValueError):
        W.whiten_by_psd(x, np.array([[100.0, 1.0], [10.0, 1.0]]), FS)
    with pytest.raises(ValueError):
        W.whiten_by_psd(x, np.array([1.0, 2.0, 3.0]), FS)


# --------------------------------------------------------------------------- #
# 3. チャープ                                                                  #
# --------------------------------------------------------------------------- #
def _zero_crossing_track(h, rate, t0=0.0):
    """零交差の間隔から瞬時周波数(閉形式を使わない独立経路)。波形が 0 で終わる尾は除く。"""
    live = np.nonzero(h)[0]
    h = h[live[0]:live[-1] + 1]
    tt = np.arange(h.size) / rate + t0 + live[0] / rate
    zc = np.where(np.diff(np.sign(h)) != 0)[0]
    tz = tt[zc] - h[zc] * (tt[zc + 1] - tt[zc]) / (h[zc + 1] - h[zc])
    f = 1.0 / (2.0 * np.diff(tz))
    return np.stack([0.5 * (tz[:-1] + tz[1:]), f], axis=1)


def _hilbert_track(h, rate):
    """解析信号の位相の微分 = 瞬時周波数(チャープが 1 周期の中で加速しても偏らない)。両端 5 % を捨てる。"""
    from scipy.signal import hilbert

    live = np.nonzero(h)[0]
    seg = h[live[0]:live[-1] + 1]
    ph = np.unwrap(np.angle(hilbert(seg)))
    f = np.gradient(ph, 1.0 / rate) / (2 * np.pi)
    t = (np.arange(seg.size) + live[0]) / rate
    k = int(0.05 * seg.size)
    return np.stack([t[k:-k], f[k:-k]], axis=1)


def test_the_chirp_frequency_track_measured_from_the_waveform_returns_the_chirp_mass():
    """波形から瞬時周波数を測り(解析信号の位相微分 = 閉形式を使わない独立経路)、f^{−8/3} の直線から
    チャープ質量を戻す。ゆっくり鳴る系(10+10 M☉ を 30 Hz から、1.4+1.4 M☉ を 200 Hz から)は 0.5 %。
    GW150914 級(36+29 M☉)は 40 Hz で周波数が 1 周期あたり 7 % も上がるので「周期ごとの周波数」自体が
    偏り、3 % まで(PRL 116, 061102 が式 1 から ≈ 30 M☉ と「≈」で書いた理由がこれ)。
    零交差の間隔(粗い経路)でも 3 % 以内。"""
    for m1, m2, tol in ((36.0, 29.0, 0.03), (10.0, 10.0, 0.005), (1.4, 1.4, 0.005)):
        h = W.chirp_newtonian(m1, m2, FS, 2.0, f_low_hz=30.0 if m1 > 5 else 200.0)
        assert h.shape == (int(2.0 * FS),) and np.isfinite(h).all()
        want = W._chirp_mass(m1, m2)
        tr = _hilbert_track(h, FS)
        tr = tr[(tr[:, 1] > 0) & np.isfinite(tr[:, 1])]
        r = W.chirp_mass_from_track(tr)
        assert r["chirp_mass_msun"] == pytest.approx(want, rel=tol), (m1, m2, r)
        assert r["coalescence_time_s"] == pytest.approx((h.size - 1) / FS, abs=0.02)
        zc = _zero_crossing_track(h, FS)
        zc = zc[(zc[:, 1] > 0) & np.isfinite(zc[:, 1])]
        assert W.chirp_mass_from_track(zc)["chirp_mass_msun"] == pytest.approx(want, rel=0.03), (m1, m2)


def test_the_chirp_stops_at_the_isco_and_its_amplitude_scales_with_inverse_distance():
    h1 = W.chirp_newtonian(36.0, 29.0, FS, 1.0, distance_mpc=410.0)
    h2 = W.chirp_newtonian(36.0, 29.0, FS, 1.0, distance_mpc=820.0)
    assert np.allclose(h1, 2.0 * h2, rtol=1e-12)
    f_isco = W.C_LIGHT ** 3 / (6.0 ** 1.5 * np.pi * W.G_NEWTON * 65.0 * W.M_SUN)
    tr = _zero_crossing_track(h1, FS)
    assert float(tr[:, 1].max()) < 1.05 * f_isco
    assert h1[-1] == 0.0 and (h1 != 0).sum() > 0.5 * h1.size


def test_chirp_rejects_a_start_above_isco_or_nyquist_and_absurd_masses():
    with pytest.raises(ValueError):
        W.chirp_newtonian(36.0, 29.0, FS, 1.0, f_low_hz=500.0)
    with pytest.raises(ValueError):
        W.chirp_newtonian(1.4, 1.4, 256.0, 1.0)           # f_ISCO 1570 Hz > Nyquist 128 Hz
    with pytest.raises(ValueError):
        W.chirp_newtonian(0.0, 29.0)
    with pytest.raises(ValueError):
        W.chirp_newtonian(36.0, 29.0, FS, 0.001)


# --------------------------------------------------------------------------- #
# 4. 軌跡 → チャープ質量                                                        #
# --------------------------------------------------------------------------- #
def test_an_exact_newtonian_track_returns_the_chirp_mass_to_machine_precision():
    mc = 30.0
    k = (8.0 / 3.0) * (96.0 / 5.0) * np.pi ** (8.0 / 3.0) * (W.G_NEWTON * mc * W.M_SUN / W.C_LIGHT ** 3) ** (5.0 / 3.0)
    tc = 1.0
    t = np.linspace(0.0, 0.9, 40)
    f = (k * (tc - t)) ** (-3.0 / 8.0)
    r = W.chirp_mass_from_track(np.stack([t, f], axis=1))
    assert r["chirp_mass_msun"] == pytest.approx(mc, rel=1e-9)
    assert r["coalescence_time_s"] == pytest.approx(tc, rel=1e-9)
    assert r["residual_rms"] < 1e-12 and r["n_points"] == 40


def test_a_falling_track_is_not_an_inspiral():
    t = np.linspace(0, 1, 10)
    r = W.chirp_mass_from_track(np.stack([t, 100.0 - 50.0 * t], axis=1))
    assert r["rising"] is False and r["chirp_mass_msun"] is None and r["coalescence_time_s"] is None
    assert np.isfinite(r["slope"]) and r["slope"] < 0
    with pytest.raises(ValueError):
        W.chirp_mass_from_track(np.stack([t[:2], [40.0, 50.0]], axis=1))


# --------------------------------------------------------------------------- #
# 5. 整合フィルタ                                                              #
# --------------------------------------------------------------------------- #
def test_optimal_snr_in_white_noise_is_template_energy_over_noise_variance():
    h = W.chirp_newtonian(36.0, 29.0, FS, 1.0)
    for sigma in (1.0, 2.5):
        got = W.optimal_snr(h, _flat_psd(sigma), FS, f_low_hz=None)
        want = np.sqrt(float(np.sum(h * h)) / (sigma * sigma))
        assert got == pytest.approx(want, rel=0.02), sigma


def test_an_injected_chirp_peaks_at_its_time_with_its_optimal_snr():
    h = W.chirp_newtonian(36.0, 29.0, FS, 1.0)
    p = _flat_psd(1.0)
    x = _white(16.0, 4)
    sig = W.optimal_snr(h, p, FS, f_low_hz=None)
    at = 30000
    x[at:at + h.size] += h * (30.0 / sig)
    snr = W.matched_filter_snr(x, h, p, FS, f_low_hz=None)
    assert snr.shape == x.shape and np.isfinite(snr).all() and (snr >= 0).all()
    ref = int(np.argmax(np.abs(h)))
    i = int(np.argmax(snr))
    assert abs(i - (at + ref)) <= 1
    assert snr[i] == pytest.approx(30.0, abs=4.0)
    # 折り返し領域は 0、他は雑音だけ(レイリーの典型値 ~1.25、最大でも 30 の半分以下)
    assert (snr[:ref] == 0).all()
    rest = np.concatenate([snr[ref:at - 500], snr[at + h.size + 500:x.size - h.size]])
    assert float(rest.max()) < 10.0 and 0.8 < float(rest.mean()) < 1.8


def test_the_edge_taper_is_a_live_knob_and_the_band_is_enforced():
    h = W.chirp_newtonian(36.0, 29.0, FS, 1.0)
    p = _flat_psd(1.0)
    x = _white(8.0, 5)
    a = W.matched_filter_snr(x, h, p, FS, f_low_hz=None)
    b = W.matched_filter_snr(x, h, p, FS, f_low_hz=None, taper_s=0.5)
    assert not np.allclose(a, b)
    with pytest.raises(ValueError):
        W.matched_filter_snr(x, h, p, FS, taper_s=5.0)
    with pytest.raises(ValueError):
        W.matched_filter_snr(x, h, p, FS, f_low_hz=2049.0, f_high_hz=2050.0)     # 帯域がナイキストの外
    with pytest.raises(ValueError):
        W.matched_filter_snr(x, np.zeros(100), p, FS)
    with pytest.raises(ValueError):
        W.matched_filter_snr(h[:100], h, p, FS)
    with pytest.raises(ValueError):
        W.matched_filter_snr(x, h, p, FS, template_ref_index=h.size)


# --------------------------------------------------------------------------- #
# 6. 到達時間差                                                                #
# --------------------------------------------------------------------------- #
def test_a_sub_sample_shift_between_two_peaks_is_recovered():
    n = 4096
    t = np.arange(n)
    for shift in (7.0, -3.3, 2.25):
        a = 1.0 + 20.0 * np.exp(-0.5 * ((t - 2000.0) / 6.0) ** 2)
        b = 1.0 + 15.0 * np.exp(-0.5 * ((t - 2000.0 - shift) / 6.0) ** 2)
        r = W.coincidence_delay(a, b, FS, max_delay_s=0.010)
        assert r["delay_s"] == pytest.approx(shift / FS, abs=0.05 / FS), shift
        assert r["peak_a"] == pytest.approx(21.0, abs=0.1) and r["peak_b"] == pytest.approx(16.0, abs=0.1)
        assert r["network_snr"] == pytest.approx(np.hypot(r["peak_a"], r["peak_b"]), rel=1e-12)
        assert r["window_samples"] == 41


def test_the_search_window_is_honoured():
    n = 4096
    t = np.arange(n)
    a = 1.0 + 20.0 * np.exp(-0.5 * ((t - 2000.0) / 6.0) ** 2)
    b = 1.0 + 15.0 * np.exp(-0.5 * ((t - 2200.0) / 6.0) ** 2)     # 窓(±41 標本)の外
    r = W.coincidence_delay(a, b, FS, max_delay_s=0.010)
    assert abs(r["delay_samples"]) <= 41 and r["peak_b"] < 2.0
    with pytest.raises(ValueError):
        W.coincidence_delay(a, b[:-1], FS)


# --------------------------------------------------------------------------- #
# 7. 台帳                                                                      #
# --------------------------------------------------------------------------- #
class TestLedger:
    def test_every_op_is_registered_and_implemented(self):
        assert ops1d.missing() == []
        assert set(W.__all__) == set(ops1d.list_ops("matched"))
        assert len(W.__all__) == 7

    def test_declared_out_types_are_what_the_ops_return(self):
        x = _white(4.0, 0)
        p = ops1d.call("psd_welch", x, FS, 1.0)
        assert isinstance(p, np.ndarray) and p.ndim == 2 and p.shape[1] == 2
        y = ops1d.call("whiten_by_psd", x, p, FS)
        assert isinstance(y, np.ndarray) and y.ndim == 1
        h = ops1d.call("chirp_newtonian", 36.0, 29.0, FS, 1.0)
        assert isinstance(h, np.ndarray) and h.ndim == 1
        assert isinstance(ops1d.call("optimal_snr", h, _flat_psd(), FS), float)
        s = ops1d.call("matched_filter_snr", x, h, _flat_psd(), FS)
        assert isinstance(s, np.ndarray) and s.ndim == 1
        assert isinstance(ops1d.call("coincidence_delay", s, s, FS), dict)
        tr = _zero_crossing_track(h, FS)
        assert isinstance(ops1d.call("chirp_mass_from_track", tr[tr[:, 1] > 0]), dict)

    def test_reachable_from_the_facade(self):
        import fullseye as fs

        L = fs.ledger
        p = L.psd_welch(_white(8.0, 0), FS, 2.0)
        assert float(p[5:, 1].mean()) == pytest.approx(2.0 / FS, rel=0.05)

    def test_no_op_name_collides_with_a_two_d_registry_op(self):
        import ops

        reg = {o.name for o in ops.REGISTRY}
        assert not (set(W.__all__) & reg)
