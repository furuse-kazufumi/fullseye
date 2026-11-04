# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""敵対的検証 2026-11-05 第 2 巡(optics)の回帰: O1〜O8 と同型の兄弟。

どれも報告の再現を **真値・不変量・独立実装** と突き合わせる(実装の出力を写した期待値は使わない)。
"""
import numpy as np
import numpy as np
import pytest


# --------------------------------------------------------------------------- #
# O3 ultrasound: ゲートの山はゲート内部の局所極大(表面エコーの裾の端を山と読まない)
# --------------------------------------------------------------------------- #
def _us_independent_peak(a, k):
    """独立の真値: 期待時刻 ±σ_t の中の包絡線の局所極大(解析信号をスペクトルから密に足す)。"""
    ti, sig = a["t_interfaces"][k], a["sigma_t"]
    tt = np.linspace(ti - sig, ti + sig, 4001)
    g = a["weights"] * a["response"]
    env = np.abs(np.exp(2j * np.pi * np.outer(tt, a["freqs"])) @ g)
    j = int(np.argmax(env))
    assert 0 < j < tt.size - 1                          # 窓の内部に山がある(真値の前提)
    return tt[j], env[j]


def test_o3_echo_phase_polarity_reads_the_interface_echo_not_the_front_tail():
    import ultrasound as U
    st = U.acoustic_layer_stack((("silicon", 1e-4), ("sio2", 1e-4)))
    a = U.pulse_echo_ascan(st)                          # 既定 100 MHz
    t_true, e_true = _us_independent_peak(a, 1)
    r = U.echo_phase_polarity(a, interface=1)
    assert r["peak_found"]
    assert abs(r["amplitude"] / e_true - 1.0) < 0.01   # 以前は 0.063(裾)、真値 0.020
    assert abs(r["t_peak"] - t_true) < 0.1 * a["sigma_t"]
    assert r["signed_peak"] == r["polarity"] == -1 and r["signed_peak_agrees"]


def test_o3_sam_cscan_amplitude_and_tof_are_the_interface_echo():
    import ultrasound as U
    st = U.acoustic_layer_stack((("silicon", 1e-4), ("sio2", 1e-4)))
    c = U.sam_cscan(np.zeros((8, 8), int), {0: st}, f0=100e6, water_path=2e-3)
    a = U.pulse_echo_ascan(st, f0=100e6, water_path=2e-3)
    t_true, e_true = _us_independent_peak(a, c["gate_interface"])
    assert c["n_no_peak"] == 0
    # 一様な地図 = 平面の A スキャン: 振幅は期待時刻の値とほぼ同じ(以前は 3.8 倍の裾)
    assert abs(c["amplitude"][4, 4] / c["amplitude_at_t"][4, 4] - 1.0) < 0.03
    assert abs(c["tof"][4, 4] - c["t_expected"]) < 0.25 * a["sigma_t"]
    assert c["tof"][4, 4] > c["gate"][0] + 0.25 * a["sigma_t"]   # ゲートの端ではない
    assert np.isfinite(e_true) and np.isfinite(t_true)


def test_o3_gate_with_no_interior_peak_says_so():
    """ゲートの中が単調な坂(裾だけ)なら、山を作らず NaN と peak_found=False を返す。"""
    import ultrasound as U
    t = np.linspace(0.0, 1e-6, 200)
    a = np.exp(-t / 2e-7).astype(np.complex128)         # 単調に減る包絡線
    tp, ap, amp, found = U._peak_in_gate(t, a, 10e6, 0.0, 1e-6)
    assert not found and np.isnan(tp) and np.isnan(amp)
