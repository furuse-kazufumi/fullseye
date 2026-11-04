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


# --------------------------------------------------------------------------- #
# O6 fringe.modulation: 変調度の床は相対量(全体の尺度で答えが変わらない)
# --------------------------------------------------------------------------- #
SCALES = (1.0, 1e-6, 1e-13, 1e-18)


def test_o6_modulation_is_scale_invariant():
    import fringe as F
    imgs = F.synthesize_fringes(np.zeros((32, 32)), n_steps=4, freq=3)
    ref = F.modulation(imgs)
    assert ref.mean() > 0.9                              # 真値: bias 0.5・振幅 0.5 で γ = 1
    assert len(SCALES) == 4
    for s in SCALES:
        assert np.abs(F.modulation(imgs * s) - ref).max() < 1e-9, s   # 以前は 1e-13 で 0
    assert np.all(F.modulation(np.zeros((4, 8, 8))) == 0.0)          # 平均 0 の画素は γ = 0


def test_o6_decode_fringe_and_grating_retrieval_survive_a_tiny_scale():
    pytest.importorskip("skimage")
    import fringe as F
    import gratinginterf as G
    imgs = F.synthesize_fringes(np.zeros((32, 32)), n_steps=4, freq=3)
    out = F.decode_fringe(imgs * 1e-13, min_modulation=0.5)          # 以前は「有効画素なし」
    assert np.isfinite(out).all()
    yy, xx = np.mgrid[0:64, 0:64]
    T = 0.6 + 0.2 * np.exp(-((xx - 32) ** 2 + (yy - 32) ** 2) / 200.0)
    P = 0.8 * np.sin(xx / 10.0)
    D = 0.7 + 0.2 * (yy / 63.0)
    sc = 1e-13
    s = G.grating_stepping_simulate(transmission=T * sc, dpc_rad=P, darkfield=D, n_steps=8)
    r = G.grating_stepping_simulate(n_steps=8, shape=(64, 64)) * sc
    res = G.grating_three_image_retrieve(s, r)                       # P = N の経路(以前は拒否)
    assert np.abs(res["transmission"] - T).max() < 1e-9
    assert np.abs(res["darkfield"] - D).max() < 1e-9
    assert np.abs(res["dpc_rad"] - P).max() < 1e-9


def test_o6_sibling_ftp_constant_check_is_relative():
    import fringe as F
    yy, xx = np.mgrid[0:64, 0:64]
    img = 0.5 + 0.4 * np.cos(2 * np.pi * xx / 8.0)
    h1 = F.fringe_ftp_phase(img, carrier_period=8.0)
    for s in (1e-15, 1e-18):                            # 以前は max(|im|, 1.0) の床で「一定」と拒否
        assert np.abs(F.fringe_ftp_phase(img * s, carrier_period=8.0) - h1).max() < 1e-9
    with pytest.raises(ValueError, match="constant"):
        F.fringe_ftp_phase(np.zeros((64, 64)))


# --------------------------------------------------------------------------- #
# O7 wrapped_phase: 値域は文書どおり (-π, π](−π は +π へ)と兄弟
# --------------------------------------------------------------------------- #
def test_o7_wrapped_phase_never_returns_minus_pi():
    import fringe as F
    stacks = {"general": F.synthesize_fringes(np.zeros((4, 64)), n_steps=3, freq=4),
              "four_step": F.synthesize_fringes(np.zeros((4, 64)), n_steps=4, freq=4)}
    assert len(stacks) == 2
    for method, st in stacks.items():
        w = F.wrapped_phase(st, method=method)
        assert w.min() > -np.pi and w.max() <= np.pi, method      # 以前は −π ちょうどが出た
        # 真値: 搬送波 4 周期の総位相 φ = 2π·4·x/64 を (-π, π] に折ったもの
        x = np.arange(64) / 64.0
        true = np.angle(np.exp(1j * 2 * np.pi * 4 * x))
        true = np.where(true <= -np.pi, np.pi, true)
        d = np.angle(np.exp(1j * (w[0] - true)))
        assert np.abs(d).max() < 1e-9, method


def test_o7_siblings_lockin_and_multipath_phase_range():
    import lighttransport as LT
    import lockin as L
    n = 16
    k = np.arange(n)
    v = np.zeros((n, 4, 4))
    v[:] = -np.cos(2 * np.pi * k / n)[:, None, None]            # 位相 π ちょうど
    ph = L.lockin_demodulate(v, 1.0, 16.0)["phase"]
    assert ph.min() > -np.pi and np.allclose(ph, np.pi)          # 以前は −π
    r = LT.fringe_multipath_phase_error(1.0, -np.pi, 0.0, 0.0)
    assert -np.pi < float(r["phase"]) <= np.pi and abs(float(r["phase"]) - np.pi) < 1e-12
    assert -np.pi < float(r["bias"]) <= np.pi


# --------------------------------------------------------------------------- #
# O5 decode_fringe(ref_phase=...): 参照を引いた高さに k·2πm の大域オフセットが残らない
# --------------------------------------------------------------------------- #
def test_o5_reference_subtraction_has_no_global_2pi_offset():
    pytest.importorskip("skimage")
    import fringe as F
    yy, xx = np.mgrid[0:64, 0:64]
    cases = [(amp, freq, n) for amp in (1.0, 2.0, 3.0, 4.0) for freq in (2, 3, 4, 5, 6)
             for n in (3, 4, 5)]
    assert len(cases) == 60
    worst = 0.0
    for amp, freq, n in cases:
        h = amp * np.exp(-((xx - 32) ** 2 + (yy - 32) ** 2) / 150.0)     # 真値の高さ
        kw = dict(n_steps=n, freq=freq, phase_gain=2.0, bias=0.5, amplitude=0.4)
        ref = F.decode_fringe(F.synthesize_fringes(np.zeros_like(h), **kw))
        out = F.decode_fringe(F.synthesize_fringes(h, **kw), ref_phase=ref, k=0.5)
        worst = max(worst, float(np.abs(out - h).max()))
    assert worst < 1e-6                                   # 以前は 60 条件中 24 で π / 2π ずれた


def test_o5_any_2pi_offset_in_the_reference_cancels():
    """参照の位相に 2πm を足しても(展開の分岐の違い)高さは同じ —— 差を先に取るので。"""
    pytest.importorskip("skimage")
    import fringe as F
    yy, xx = np.mgrid[0:48, 0:48]
    h = 1.5 * np.exp(-((xx - 24) ** 2 + (yy - 24) ** 2) / 80.0)
    kw = dict(n_steps=4, freq=3, phase_gain=1.0)
    _, total_ref = F.synthesize_fringes(np.zeros_like(h), return_phase=True, **kw)
    obj = F.synthesize_fringes(h, **kw)
    outs = [F.decode_fringe(obj, ref_phase=total_ref + 2 * np.pi * m, k=1.0) for m in (-3, 0, 1, 7)]
    assert len(outs) == 4
    for o in outs:
        assert np.abs(o - h).max() < 1e-9


# --------------------------------------------------------------------------- #
# O4 fringe_ftp_phase: 推定した搬送波を DFT の整数ビンに丸めない
# --------------------------------------------------------------------------- #
def _ftp_bump(period, noise=0.0):
    yy, xx = np.mgrid[0:128, 0:128]
    true = 1.5 * np.exp(-((xx - 64) ** 2 + (yy - 64) ** 2) / (2 * 15 ** 2))   # 傾きを持たない対象
    img = 0.5 + 0.4 * np.cos(2 * np.pi * xx / period + true)
    if noise:
        img = img + np.random.default_rng(5).normal(0.0, noise, img.shape)
    return img, true - true.mean()


def test_o4_off_bin_carrier_is_estimated_below_one_bin():
    import fringe as F
    periods = (7.3, 6.55, 9.17, 11.9)
    assert len(periods) == 4
    for period in periods:
        img, ref = _ftp_bump(period)
        _, est = F.fringe_ftp_phase(img, return_info=True)
        _, known = F.fringe_ftp_phase(img, carrier_period=period, return_info=True)
        e_est = (est["phase"] - ref)[16:-16, 16:-16]
        e_known = (known["phase"] - ref)[16:-16, 16:-16]
        rms_est = float(np.sqrt((e_est ** 2).mean()))
        rms_known = float(np.sqrt((e_known ** 2).mean()))
        # 独立の基準: 搬送波を真値で渡した同じ op の誤差(端の効果だけを持つ)
        assert rms_est < max(2.0 * rms_known, 0.03), (period, rms_est, rms_known)  # 以前は 0.63 rad
        assert abs(est["carrier_period"] / period - 1.0) < 2e-3, period


def test_o4_frame_periodic_image_keeps_the_exact_integer_bin():
    import fringe as F
    img, ref = _ftp_bump(8.0)                            # 128 / 8 = 16 周期(整数ビン)
    _, info = F.fringe_ftp_phase(img, return_info=True)
    assert info["carrier_period"] == 8.0


def test_o4_noisy_integer_carrier_still_estimated_closely():
    import fringe as F
    img, ref = _ftp_bump(8.0, noise=0.02)                # 雑音で漏れがある -> サブビン推定の経路
    _, info = F.fringe_ftp_phase(img, return_info=True)
    assert abs(info["carrier_period"] / 8.0 - 1.0) < 2e-3


# --------------------------------------------------------------------------- #
# O8 台帳の docstring の「N op / M カテゴリ」が実数と合う(opsinterferometry と兄弟)
# --------------------------------------------------------------------------- #
def _docstring_count_claims():
    """ops*.py の docstring にある「<mod>.py(、)N op / M カテゴリ」を全部拾う。"""
    import ast
    import pathlib
    import re
    pat = re.compile(r"`{0,2}(\w+)\.py`{0,2}\s*[、(]\s*(?:[^、()]*、\s*)?(\d+) op / (\d+) カテゴリ")
    root = pathlib.Path(__file__).resolve().parents[1]
    out = []
    for f in sorted(root.glob("ops*.py")):
        doc = ast.get_docstring(ast.parse(f.read_text(encoding="utf-8"))) or ""
        for m in pat.finditer(doc):
            out.append((f.stem, m.group(1), int(m.group(2)), int(m.group(3))))
    return out


def test_o8_registry_docstring_counts_match_the_registry():
    import collections
    import importlib
    claims = _docstring_count_claims()
    assert len(claims) >= 12                              # 拾えているか(空集合への表明の防止)
    assert ("opsinterferometry", "interferometry", 9, 6) in claims   # 以前は 5 カテゴリ
    bad = []
    for reg, mod, n_op, n_cat in claims:
        m = importlib.import_module(reg)
        cats = collections.defaultdict(list)
        for name in m.list_ops():
            info = m.info(name)
            cats[info.get("module")].append(info["category"])
        got = (len(cats[mod]), len(set(cats[mod])))
        if got != (n_op, n_cat):
            bad.append((reg, mod, (n_op, n_cat), got))
    assert not bad, bad
