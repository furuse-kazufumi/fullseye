# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""敵対的検証 2026-11-05 第 2 巡(optics)の回帰: O1〜O8 と同型の兄弟。

どれも報告の再現を **真値・不変量・独立実装** と突き合わせる(実装の出力を写した期待値は使わない)。
"""
import numpy as np
import numpy as np
import pytest

import optscene as OS


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

def _cam():
    return OS.optical_camera(focal_mm=25.0, pixel_um=3.45, resolution=(64, 64),
                             working_distance_mm=200.0)


# --------------------------------------------------------------------------- #
# O1 defocus_blur: 手前から over 合成(合焦した不透明な手前は奥のぼけに汚されない)
# --------------------------------------------------------------------------- #
def test_o1_in_focus_foreground_is_not_contaminated_by_the_blurred_background():
    cam = _cam()
    img = np.zeros((64, 64))
    img[:, :32] = 1.0                                  # 手前(合焦)が明るく、奥が暗い
    d = np.full((64, 64), 200.0)
    d[:, 32:] = 2000.0
    out = OS.defocus_blur(img, d, cam, f_number=2.0)
    # 不変量: 合焦面(錯乱円 0)の不透明な画素は入力そのもの(以前は境界で 0.666)
    assert np.abs(out[:, :32] - 1.0).max() < 1e-12


def test_o1_blurred_foreground_spills_over_an_in_focus_background():
    """逆向き: ぼけた手前は合焦した奥へ被る(手前の被覆率 α の分だけ奥が隠れる)。"""
    cam = _cam()
    img = np.zeros((64, 64))
    img[:, :32] = 1.0
    d = np.full((64, 64), 200.0)
    d[:, :32] = 195.0                                  # 手前(左)がぼける(錯乱円 13 px)
    out = OS.defocus_blur(img, d, cam, f_number=2.0)
    assert out[32, 33] > 0.05                          # 境界のすぐ奥側に手前の光が被る
    assert np.abs(out[:, 60:] - 0.0).max() < 1e-6      # 遠い奥はそのまま


def test_o1_boundary_depth_belongs_to_exactly_one_layer():
    """層の境界ちょうどの深度は 1 層だけに入る(以前は両端を含む区間で 2 層に重複)。

    境界の深度 300 mm を 1e-7 mm だけ動かして同じ層に入れた結果と一致すること。
    """
    cam = _cam()
    rng = np.random.default_rng(3)
    img = rng.random((64, 64))
    d = np.full((64, 64), 200.0)
    d[:, 20:40] = 300.0                                # edges = [200, 300, 400] のちょうど境界
    d[:, 40:] = 400.0
    a = OS.defocus_blur(img, d, cam, f_number=2.0, layers=2)
    d2 = d.copy()
    d2[:, 20:40] = 300.0 + 1e-7
    b = OS.defocus_blur(img, d2, cam, f_number=2.0, layers=2)
    assert np.abs(a - b).max() < 1e-6


# --------------------------------------------------------------------------- #
# O2 defocus_blur: 深度 +inf は z -> ∞ の錯乱円でぼかす
# --------------------------------------------------------------------------- #
def test_o2_depth_at_infinity_is_blurred_like_a_very_far_plane():
    cam = _cam()
    img = np.zeros((64, 64))
    img[:, ::4] = 1.0                                  # 周期 4 px の縞
    fg = np.full((64, 64), 200.0)
    outs = {}
    for zbg in (1e12, np.inf):
        d = fg.copy()
        d[:, 32:] = zbg
        outs[zbg] = OS.defocus_blur(img, d, cam, f_number=2.0)
    # 閉じた式: z -> ∞ の錯乱円 f²/(N(z_f − f)) = 1.79 mm = 518 px で縞は消える
    c_inf = 25.0 ** 2 / (2.0 * (200.0 - 25.0)) / 3.45e-3
    assert c_inf > 500.0
    assert outs[np.inf][:, 40:60].std() < 1e-3          # 以前は 0.433(くっきり)
    assert np.abs(outs[np.inf] - outs[1e12]).max() < 1e-6
    # 手前の合焦面は入力のまま(縞の σ = 理想)
    assert abs(outs[np.inf][:, 4:24].std() - img[:, 4:24].std()) < 1e-9


def test_o2_nan_depth_is_still_treated_as_in_focus():
    cam = _cam()
    img = np.zeros((64, 64))
    img[:, ::4] = 1.0
    d = np.full((64, 64), np.nan)
    out = OS.defocus_blur(img, d, cam, f_number=2.0)
    assert np.array_equal(out, img)
