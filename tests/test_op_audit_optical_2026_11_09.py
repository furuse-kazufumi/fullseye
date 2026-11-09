# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Regression gates for the 2026-11-09 op audit (group g3_optical).

各テストは監査の探針(独立担当の再現)を元にしたもので、直す前は落ち、直した後は通る。
真値はどれも op と別の経路から取る(閉形式・定理・合成した既知の面)。
"""
from __future__ import annotations

import math
import os
import sys
import warnings

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import coherent  # noqa: E402
import lightsection as LS  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. light_section_speckle_floor / laser_line_coherent: 強度のナイキスト
# --------------------------------------------------------------------------- #
_SF = dict(wavelength_um=0.65, sin_u_obs=0.02, sin_theta=0.5, line_width_um=173.2, pixel_um=80.0,
           length_um=80.0, n_trials=16, n_columns=64, n_rows=96)


def test_speckle_floor_refuses_a_fine_step_coarser_than_the_intensity_nyquist():
    # dx = 80/8 = 10 µm > λ/(4 sin u) = 8.125 µm: 場のナイキスト(16.25 µm)は通るが強度は折り返す
    with pytest.raises(ValueError, match="pixel_oversample >= 10"):
        LS.light_section_speckle_floor(pixel_oversample=8, **_SF)
    with pytest.raises(ValueError, match="intensity"):
        coherent.laser_line_coherent(shape=(32, 16), wavelength_um=0.65, sin_u_obs=0.02, pixel_um=80.0,
                                     line_width_um=173.2, pixel_oversample=6)


def test_speckle_floor_converged_ratio_and_reported_step():
    r = LS.light_section_speckle_floor(pixel_oversample=16, **_SF)
    assert 0.80 < r["ratio_sim_to_closed_form"] < 0.95, r["ratio_sim_to_closed_form"]
    assert r["fine_step_um"] == pytest.approx(5.0)
    assert r["intensity_nyquist_um"] == pytest.approx(0.65 / 0.08)


def test_speckle_floor_warns_just_inside_the_intensity_nyquist():
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        coherent.laser_line_coherent(shape=(32, 16), wavelength_um=0.65, sin_u_obs=0.02, pixel_um=80.0,
                                     line_width_um=173.2, pixel_oversample=10)   # dx 8.0 ≤ 8.125
    assert any(issubclass(w.category, RuntimeWarning) and "Nyquist" in str(w.message) for w in wl)
    with warnings.catch_warnings(record=True) as wl:
        warnings.simplefilter("always")
        coherent.laser_line_coherent()                                            # 既定 dx 1 µm vs 3.25 µm
    assert not any(issubclass(w.category, RuntimeWarning) for w in wl)


# --------------------------------------------------------------------------- #
# 2. laser_line_center_centroid / _gauss: 飽和した平らな台、縁で切れた裾
# --------------------------------------------------------------------------- #
def _clipped_line(amp, c0=31.3, sig=3.0, ny=64, nx=40):
    y = np.arange(ny, dtype=float)[:, None]
    return np.clip(amp * np.exp(-0.5 * ((y - c0) / sig) ** 2), 0.0, 1.0) * np.ones((1, nx))


def test_centroid_window_is_centred_on_the_saturated_plateau():
    im = _clipped_line(20.0)                       # 台は行 24〜38、argmax は 24(直す前は −5.7 px)
    r = LS.laser_line_center_centroid(im, half_window=4)
    assert np.all(r["valid"]) and np.all(r["saturated"])
    assert abs(r["row"][0] - 31.3) < 0.05, r["row"][0]
    g = LS.laser_line_center_gauss(im, half_window=2)  # 台の標本は外し、裾だけで当てる(ガウスの対数は 2 次式)
    assert np.all(g["valid"]) and np.all(g["saturated"])
    assert abs(g["row"][0] - 31.3) < 1e-9, g["row"][0]
    # 窓に裾の標本が 3 点ない(hw=1 で台の外は 2 点)なら valid=False —— 平らな頂に当てて valid にしない
    assert not np.any(LS.laser_line_center_gauss(_clipped_line(4.0), half_window=1)["valid"])


def test_unsaturated_line_centres_are_bit_identical_and_not_flagged():
    y = np.arange(64, dtype=float)[:, None]
    c0 = np.linspace(20.03, 40.7, 40)
    im = np.exp(-0.5 * ((y - c0) / 2.3) ** 2)
    for hw in (None, 3):
        r = LS.laser_line_center_centroid(im, half_window=hw)
        assert not np.any(r["saturated"])
        w = im * (np.abs(y - np.argmax(im, 0)[None, :]) <= hw) if hw else im
        ref = (w * y).sum(0) / w.sum(0)
        assert np.array_equal(r["row"], ref)
    g = LS.laser_line_center_gauss(im, half_window=2)
    assert not np.any(g["saturated"]) and np.max(np.abs(g["row"] - c0)) < 1e-9


def test_centroid_marks_columns_whose_profile_is_cut_by_the_border():
    y = np.arange(64, dtype=float)[:, None]
    near = LS.laser_line_center_centroid(np.exp(-0.5 * ((y - 0.4) / 2.0) ** 2) * np.ones((1, 8)))
    mid = LS.laser_line_center_centroid(np.exp(-0.5 * ((y - 31.3) / 2.0) ** 2) * np.ones((1, 8)))
    assert np.all(near["truncated"]) and not np.any(mid["truncated"])
    assert np.all(near["valid"])                    # valid は変えない(印だけ)


# --------------------------------------------------------------------------- #
# 3. photometric.integrate_normals: 全体の傾き・非有限・nz ≈ 0
# --------------------------------------------------------------------------- #
import photometric  # noqa: E402


def _tilted_normals(px=0.2, qy=0.0, shape=(96, 96)):
    n = np.zeros(shape + (3,))
    n[..., 0], n[..., 1], n[..., 2] = -px, -qy, 1.0
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def test_integrate_normals_keeps_the_global_tilt():
    z = photometric.integrate_normals(_tilted_normals(0.2))      # 直す前は傾き 0.0000
    slope = np.polyfit(np.arange(96), z[48], 1)[0]
    assert abs(slope - 0.2) < 0.005, slope
    z2 = photometric.integrate_normals(_tilted_normals(0.0, -0.1, (40, 64)))
    yy, xx = np.mgrid[0:40, 0:64]
    truth = -0.1 * (yy - 19.5)
    assert np.max(np.abs(z2 - truth)) < 1e-9
    # 素の周期解(integrate_gradients)は従来どおり直流を落とす —— 約束として固定
    zg = photometric.integrate_gradients(*photometric.normals_to_gradients(_tilted_normals(0.2)))
    assert abs(np.polyfit(np.arange(96), zg[48], 1)[0]) < 1e-9


def test_integrate_normals_refuses_non_finite_and_warns_on_grazing_normals():
    n = _tilted_normals(0.0)
    n[10, 10] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        photometric.integrate_normals(n)
    n = _tilted_normals(0.0)
    n[10, 10] = (1.0, 0.0, 0.0)                                  # nz = 0: 直す前は高さが 2.3e5 px 振れた
    with pytest.warns(RuntimeWarning, match="1 pixel"):
        z = photometric.integrate_normals(n)
    assert np.max(np.abs(z)) < 1e-9


# --------------------------------------------------------------------------- #
# 4. sfp_normals: S0 ≈ 0 の暗い画素
# --------------------------------------------------------------------------- #
import sfpolar  # noqa: E402
import specularity  # noqa: E402

_ANG = (0.0, 45.0, 90.0, 135.0)


def _half_dark_sweep(sig, seed=0, H=32, W=32):
    rng = np.random.default_rng(seed)
    s0 = rng.uniform(0.1, 1, (H, W))
    rho = rng.uniform(0, 1, (H, W))
    psi = rng.uniform(0, math.pi, (H, W))
    s1, s2 = s0 * rho * np.cos(2 * psi), s0 * rho * np.sin(2 * psi)
    fr = np.stack([0.5 * (s0 + s1 * math.cos(2 * math.radians(a)) + s2 * math.sin(2 * math.radians(a)))
                   for a in _ANG])
    dark = np.zeros((4, H, W))
    dark[:, :, : W // 2] = fr[:, :, : W // 2]
    return np.clip(dark + rng.normal(0, sig, dark.shape), 0, None) if sig else dark


def test_sfp_normals_does_not_return_normals_on_dark_noise():
    c = sfpolar.sfp_normals(_half_dark_sweep(0.001), 1.5, "specular")
    assert c["valid"][:, 16:].mean() < 0.01, c["valid"][:, 16:].mean()   # 直す前は 0.28
    assert c["valid"][:, :16].mean() > 0.99
    assert np.all(c["dark"][:, 16:]) and np.all(c["n_distinct"][:, 16:] == 0)
    clean = sfpolar.sfp_normals(_half_dark_sweep(0.0), 1.5, "specular")
    assert np.array_equal(clean["valid"][:, :16], np.ones((32, 16), bool))
    # 雑音基準の床なので、雑音が大きく(σ 0.01 = 上位の 1 %)ても暗い半面は通らない
    c = sfpolar.sfp_normals(_half_dark_sweep(0.01), 1.5, "specular")
    assert c["valid"][:, 16:].mean() < 0.01
    assert not (c["valid"][:, 16:] & ~c["noisy"][:, 16:]).any()


# --------------------------------------------------------------------------- #
# 5a. light_section_speckle_floor: 純 Dorsch の値と √(w/L) を分けて返す
# --------------------------------------------------------------------------- #
def test_speckle_floor_reports_pure_dorsch_separately_from_the_averaging_rule():
    r = LS.light_section_speckle_floor(sin_u_obs=0.02, line_width_um=173.2, pixel_um=50.0, length_um=50.0,
                                       n_trials=2, n_columns=16, n_rows=32, pixel_oversample=16)
    pure = 0.65 / (2 * math.pi * 0.02 * 0.5)                      # 手計算の Dorsch(C = 1)
    assert r["dorsch_delta_z_um"] == pytest.approx(pure, rel=1e-12)
    assert abs(r["dorsch_delta_z_um"] - 10.345) < 1e-3
    assert r["averaging_factor"] == pytest.approx(math.sqrt(173.2 / 50.0), rel=1e-12)
    assert r["closed_form_delta_z_um"] / r["dorsch_delta_z_um"] == pytest.approx(math.sqrt(173.2 / 50.0), rel=1e-12)
    assert r["ratio_sim_to_dorsch"] == pytest.approx(r["sim_delta_z_um"] / pure, rel=1e-12)


# --------------------------------------------------------------------------- #
# 5b. laser_line_center_steger: 縁の 3σ 以内は valid=False
# --------------------------------------------------------------------------- #
def test_steger_invalidates_centres_near_the_border():
    y = np.arange(64, dtype=float)[:, None]
    near = LS.laser_line_center_steger(np.exp(-0.5 * ((y - 2.2) / 2.0) ** 2) * np.ones((1, 40)), sigma=3.0)
    assert not near["valid"][20] and near["near_border"][20]      # 直す前は valid で −1.43 px
    mid = LS.laser_line_center_steger(np.exp(-0.5 * ((y - 31.3) / 2.0) ** 2) * np.ones((1, 40)), sigma=3.0)
    inner = slice(10, 30)                                       # 列の縁 3σ = 9 列も無効(法線に依らない判定)
    assert np.all(mid["valid"][inner]) and not np.any(mid["near_border"][inner])
    assert np.all(mid["near_border"][:9]) and np.all(mid["near_border"][-9:])
    assert np.nanmax(np.abs(mid["row"][inner] - 31.3)) < 0.01


# --------------------------------------------------------------------------- #
# 5c/5d. measuring1d: gen_measure_rectangle2 の約束の固定、measure_pos の入力の門
# --------------------------------------------------------------------------- #
import measuring1d as M1  # noqa: E402


def _step_image(H=41, W=81, x0=40.28):
    xx = np.arange(W, dtype=float)[None, :] * np.ones((H, 1))
    return 0.2 + 0.6 / (1 + np.exp(-(xx - x0) / 0.6))


def test_gen_measure_rectangle2_pins_length2_as_full_width_and_phi_clockwise():
    m = M1.gen_measure_rectangle2(20, 40, 0.0, 30, 2, (41, 81))
    # length2=2 は法線方向 offset ±1 の 2 本(全幅。HALCON の Length2 は半高)
    H, W = 41, 81
    step = _step_image(H, W)[0]                        # 0.2 → 0.8 の段(段差 0.6)
    im = np.zeros((H, W))
    im[21] = step                                      # 中心 +1 行だけの段 → 平均に入る(2 本の 1 本 = 0.3)
    e = M1.measure_pos(im, m, sigma=1.0, threshold=0.1)
    assert len(e) == 1 and abs(e[0]["amplitude"] - 0.3) < 0.02, e
    im2 = np.zeros((H, W))
    im2[22] = step                                     # 中心 +2 行は見ない(HALCON の半高 2 なら入る)
    assert M1.measure_pos(im2, m, sigma=1.0, threshold=0.1) == []
    # φ = +π/2 は行の増える向き(画面の下向き)へ進む
    yy = np.arange(41, dtype=float)[:, None] * np.ones((1, 81))
    down = 0.2 + 0.6 / (1 + np.exp(-(yy - 20.3) / 0.6))
    e = M1.measure_pos(down, M1.gen_measure_rectangle2(20, 40, math.pi / 2, 15, 1, (41, 81)))
    assert e[0]["polarity"] == "positive"
    assert "Half height" in M1.gen_measure_rectangle2.__doc__ and "phi = −Phi" in M1.gen_measure_rectangle2.__doc__


def test_measure_pos_refuses_nan_negative_sigma_and_a_line_outside_the_image():
    im = _step_image()
    m = M1.gen_measure_rectangle2(20, 40, 0.0, 30, 1, im.shape)
    ref = M1.measure_pos(im, m)
    assert len(ref) == 1 and abs(ref[0]["col"] - 40.28) < 0.05
    bad = im.copy()
    bad[20, 41] = np.nan                               # 直す前はエッジが黙って消えた(0 本)
    with pytest.raises(ValueError, match="non-finite"):
        M1.measure_pos(bad, m)
    with pytest.raises(ValueError, match="sigma"):
        M1.measure_pos(im, m, sigma=-1.0)
    with pytest.raises(ValueError, match="outside"):
        M1.measure_pos(im, M1.gen_measure_rectangle2(20, 200, 0.0, 30, 1, im.shape))
    with pytest.warns(RuntimeWarning, match="outside"):
        M1.measure_pos(im, M1.gen_measure_rectangle2(20, 70, 0.0, 30, 1, im.shape))
    assert M1.measure_pos(im, m) == ref                # 正しい入力は不変


# --------------------------------------------------------------------------- #
# 5e. itof_phase_amplitude: 完全飽和・負のオフセット・飽和の印
# --------------------------------------------------------------------------- #
import itof  # noqa: E402


def test_itof_fully_saturated_pixel_has_no_depth():
    pa = itof.itof_phase_amplitude(np.full((1, 4, 1, 1), 6313.0), (20e6,))   # 直す前: 0.59 m, sigma 1e14
    assert pa["amplitude"].ravel()[0] == 0.0 and pa["phase"].ravel()[0] == 0.0
    assert np.isinf(pa["depth_sigma"]).all()
    neg = itof.itof_phase_amplitude(np.array([-5.0, 3.0, -1.0, 0.0]).reshape(1, 4, 1, 1), (20e6,))
    assert np.isinf(neg["depth_sigma"]).all()                                # 直す前は 0(雑音ゼロと主張)


def test_itof_marks_pixels_clipped_at_a_ceiling():
    f = 20e6
    cap = itof.itof_capture(np.array([[1.0, 2.0, 3.0, 4.0, 5.0]]), frequencies_hz=(f,),
                            signal_electrons=20000, ambient_electrons=2000, noise=False)
    smp = cap["samples"]
    fw = np.percentile(smp, 60)
    clipped = itof.itof_phase_amplitude(np.minimum(smp, fw), (f,))
    assert np.all(clipped["saturated"])                                      # 5 画素とも天井に当たる
    clean = itof.itof_phase_amplitude(cap)
    assert not np.any(clean["saturated"])
    assert np.array_equal(clean["wrapped_depth"], itof.itof_phase_amplitude(cap)["wrapped_depth"])


# --------------------------------------------------------------------------- #
# 5f. fringe.absolute_phase: 次数の誤りは残差 coarse − Φ で見張る(docstring の recipe)
# --------------------------------------------------------------------------- #
import fringe  # noqa: E402


def test_absolute_phase_residual_recipe_flags_order_errors():
    rng = np.random.default_rng(1)
    P = (16.0, 4.0, 1.0)
    x = np.linspace(1.0, 15.0, 200000)
    tru = [2 * math.pi * x / p for p in P]
    wr = [np.angle(np.exp(1j * (t + rng.normal(0, 0.3, t.shape)))) for t in tru]
    a = np.mod(wr[0], 2 * math.pi)
    flag = np.zeros(x.size, bool)
    for i in range(1, 3):
        c = a * P[i - 1] / P[i]
        a = fringe.absolute_phase(wr[i][None], c[None])[0]
        flag |= np.abs(c - a) > 0.8 * math.pi                     # docstring の recipe
    wrong = np.abs(np.round((a - tru[2]) / (2 * math.pi))) > 0
    assert 0.01 < wrong.mean() < 0.05                              # 戻り値だけでは 2.6 % が黙って誤る
    assert (flag & wrong).sum() > 0.3 * wrong.sum()                # 残差の印は誤りの 3 割以上を拾う
    assert "resid = c - Phi" in fringe.absolute_phase.__doc__


# --------------------------------------------------------------------------- #
# 5g. polarization_dolp_map / stokes_map: 暗い画素は DoLP 0
# --------------------------------------------------------------------------- #
def test_dolp_map_returns_zero_not_one_on_dark_noise():
    sw = _half_dark_sweep(0.001)
    d = specularity.polarization_dolp_map(sw, _ANG, max_violation_frac=0.6)
    assert np.median(d[:, 16:]) < 0.05, np.median(d[:, 16:])        # 直す前は 1.000
    clean = _half_dark_sweep(0.0)
    ref = specularity.polarization_dolp_map(clean, _ANG)
    assert np.max(np.abs(d[:, :16] - ref[:, :16])) < 0.05             # 明るい半面は雑音の分だけ
    sm = specularity.polarization_stokes_map(sw, _ANG, max_violation_frac=0.6)
    assert not sm["lit"][:, 16:].any() and np.all(sm["dolp"][:, 16:] == 0.0)
    assert sm["lit"][:, :16].all()


# --------------------------------------------------------------------------- #
# 5h. binocular_disparity_ms の遅さ: 集約の一時配列を減らした経路は元の式と bit 一致
# --------------------------------------------------------------------------- #
import stereo  # noqa: E402


def _aggregate_reference(C, S, sy, sx, P1, P2):
    """直す前の集約(_sgm_penalty を 1 歩ごとに呼ぶ版)。"""
    H, W, _ = C.shape
    if sx != 0:
        prev = C[:, 0 if sx > 0 else W - 1, :].copy()
        S[:, 0 if sx > 0 else W - 1, :] += prev
        for x in (range(1, W) if sx > 0 else range(W - 2, -1, -1)):
            cur = C[:, x, :] + stereo._sgm_penalty(prev, P1, P2)
            S[:, x, :] += cur
            prev = cur
    else:
        prev = C[0 if sy > 0 else H - 1, :, :].copy()
        S[0 if sy > 0 else H - 1, :, :] += prev
        for y in (range(1, H) if sy > 0 else range(H - 2, -1, -1)):
            cur = C[y, :, :] + stereo._sgm_penalty(prev, P1, P2)
            S[y, :, :] += cur
            prev = cur


def test_sgm_aggregation_fast_path_is_bit_identical():
    rng = np.random.default_rng(3)
    for D in (1, 2, 17):
        C = np.ascontiguousarray(np.round(rng.random((23, 31, D)) * 24))
        for sy, sx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            a = np.zeros_like(C)
            b = np.zeros_like(C)
            stereo._aggregate_dir_into(C, a, sy, sx, 5.0, 50.0)
            _aggregate_reference(C, b, sy, sx, 5.0, 50.0)
            assert np.array_equal(a, b), (D, sy, sx)


# --------------------------------------------------------------------------- #
# 独立レビュー R1: Steger の縁は推定した法線でなく点の位置で判定(斜めの線)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("deg", [30, 45, 60, 70, 80])
def test_steger_oblique_lines_have_no_valid_point_bent_by_the_border(deg):
    t = math.radians(deg)
    yy, xx = np.mgrid[0:64, 0:64].astype(float)
    d = -(xx - 31.3) * math.sin(t) + (yy - 31.3) * math.cos(t)
    r = LS.laser_line_center_steger(np.exp(-0.5 * (d / 2.0) ** 2), sigma=3.0)
    v = r["valid"]
    assert v.any()
    err = np.abs(-(r["col"][v] - 31.3) * math.sin(t) + (r["row"][v] - 31.3) * math.cos(t))
    assert err.max() < 0.02, err.max()          # 直す前(法線で判定): 30° 0.60 / 60° 0.69 / 70° 0.44 / 80° 0.21 px
    assert np.all((r["row"][v] >= 9) & (r["row"][v] <= 54) & (r["col"][v] >= 9) & (r["col"][v] <= 54))


# --------------------------------------------------------------------------- #
# 独立レビュー R2: 暗い画素の床は雑音基準(固定の相対値は両向きに黙って間違った)
# --------------------------------------------------------------------------- #
def _scene(s0, rho, sig, seed=0):
    rng = np.random.default_rng(seed)
    psi = rng.uniform(0, math.pi, s0.shape)
    s1, s2 = s0 * rho * np.cos(2 * psi), s0 * rho * np.sin(2 * psi)
    sw = np.stack([0.5 * (s0 + s1 * math.cos(2 * math.radians(a)) + s2 * math.sin(2 * math.radians(a)))
                   for a in _ANG])
    return np.clip(sw + rng.normal(0, sig, sw.shape), 0, None) if sig else sw


def test_dark_diffuse_object_next_to_highlights_keeps_its_dolp():
    H = W = 100
    s0 = np.full((H, W), 0.008)                          # 暗い拡散の物体(真の DoLP 0.3、SNR 80)
    s0[:, :5] = 1.0                                       # 鏡面ハイライト 5 %
    rho = np.full((H, W), 0.3)
    sw = _scene(s0, rho, 1e-4)
    d = specularity.polarization_dolp_map(sw, _ANG, max_violation_frac=0.6)
    assert abs(np.median(d[:, 5:]) - 0.3) < 0.02, np.median(d[:, 5:])   # 1 つ前の版(上位 1 % の 1e-2)は 0.000
    c = sfpolar.sfp_normals(sw, 1.5, "diffuse")
    assert c["valid"][:, 5:].mean() > 0.99                                 # 1 つ前の版は 0 %


def test_small_bright_region_still_screens_the_dark_noise():
    H = W = 100
    s0 = np.zeros((H, W))
    s0[:5, :10] = 1.0                                     # 明るい所は画像の 0.5 %
    rho = np.where(s0 > 0, 0.3, 0.0)
    sw = _scene(s0, rho, 1e-3)
    dark = s0 == 0
    d = specularity.polarization_dolp_map(sw, _ANG, max_violation_frac=0.9)
    assert np.median(d[dark]) < 0.05                       # 1 つ前の版は 1.000(99 百分位が暗部に落ちた)
    assert abs(np.median(d[~dark]) - 0.3) < 0.02
    c = sfpolar.sfp_normals(sw, 1.5, "diffuse")
    assert c["valid"][dark].mean() < 0.01 and c["valid"][~dark].mean() > 0.95
    sm = specularity.polarization_stokes_map(sw, _ANG, max_violation_frac=0.9)
    assert sm["lit"][dark].mean() < 0.01 and sm["lit"][~dark].all()


# --------------------------------------------------------------------------- #
# 独立レビュー R3: length2 = 2·L2+1 の offset は整数でない(docstring を実装どおりに)
# --------------------------------------------------------------------------- #
def test_length2_offsets_are_as_documented_not_halcon_integers():
    yy = np.arange(41, dtype=float)[:, None] * np.ones((1, 81))
    img = (yy - 20.0) ** 2                                     # 平均すると mean(offset²) が残る
    prof = M1._profile(img, M1.gen_measure_rectangle2(20, 40, 0.0, 10, 5, img.shape))
    # linspace(-2.5, 2.5, 5) を双線形補間で読むと (6.5·2 + 1.75·2 + 0)/5 = 3.3(HALCON の整数 −2..2 なら 2.0)
    assert np.allclose(prof, 3.3)
    assert "−2.5, −1.25, 0, 1.25, 2.5" in M1.gen_measure_rectangle2.__doc__


# --------------------------------------------------------------------------- #
# 独立レビュー R4: 量子化した飽和していない光条で saturated を立てない
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("amp", [60, 200])
def test_quantised_unsaturated_line_is_not_a_plateau(amp):
    rng = np.random.default_rng(5)
    ny, nx = 64, 400
    y = np.arange(ny, dtype=float)[:, None]
    c0 = rng.uniform(20, 44, nx)
    img = np.round(amp * np.exp(-0.5 * ((y - c0) / 3.0) ** 2)).astype(np.uint8)
    r = LS.laser_line_center_centroid(img, half_window=3)
    assert r["saturated"].mean() < 0.01, r["saturated"].mean()   # 1 つ前の版: 頂 200 で 6.2 %、60 で 15.2 %
    f = img.astype(float)
    w = f * (np.abs(y - np.argmax(f, 0)[None, :]) <= 3)
    ref = (w * y).sum(0) / w.sum(0)                               # master の窓(argmax ± 3)
    ns = ~r["saturated"]
    assert np.array_equal(r["row"][ns], ref[ns])                  # 台でない列は bit 一致
    clipped = np.minimum(np.round(4 * amp * np.exp(-0.5 * ((y - c0) / 3.0) ** 2)), amp).astype(np.uint8)  # 天井 = amp
    assert LS.laser_line_center_centroid(clipped, half_window=3)["saturated"].all()


def test_integrate_normals_documents_its_outlier_weakness():
    doc = photometric.integrate_normals.__doc__
    assert "外れ値に弱い" in doc and "27.9" in doc
