# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pixelshift(ピクセルシフト撮像)の門: 開口の積分の厳密さ・格子の合成・fail-closed・閉形式。"""
from __future__ import annotations

import math

import numpy as np
import pytest

import opsoptics
import pixelshift as PS

F = 8


def _block_scene(h, w, seed=0, rgb=True):
    """センサ画素ごとに一定のシーン(升の境界に乗る開口の積分は、その画素の値そのもの)。"""
    rng = np.random.default_rng(seed)
    blk = rng.random((h, w, 3) if rgb else (h, w))
    return blk, np.repeat(np.repeat(blk, F, 0), F, 1)


def test_capture_integrates_the_aperture_exactly():
    blk, sc = _block_scene(20, 24)
    out = PS.pixel_shift_capture(sc, F, [[0.0, 0.0]], None, margin=2)
    assert out.shape == (1, 16, 20, 3)
    assert np.abs(out[0] - blk[2:-2, 2:-2]).max() < 1e-12
    # 半画素ずらすと、隣り合う 4 画素の平均(箱の面積の重み)
    half = PS.pixel_shift_capture(sc[..., 0], F, [[0.5, 0.5]], None, margin=2)[0]
    b = blk[..., 0]
    want = 0.25 * (b[2:-2, 2:-2] + b[3:-1, 2:-2] + b[2:-2, 3:-1] + b[3:-1, 3:-1])
    assert np.abs(half - want).max() < 1e-12


def test_fill_factor_samples_the_centre():
    # 開口率 0.25 の画素は中央の 1/4 × 1/4 だけを見る: 画素の中で左右に分かれたシーンでも、中央の升の値になる
    sc = np.zeros((16 * F, 16 * F))
    sc[:, :] = np.tile(np.repeat([0.0, 1.0], F // 2), 16 * 2)[None, :16 * F]
    full = PS.pixel_shift_capture(sc, F, [[0.0, 0.0]], None, fill_factor=1.0)[0]
    quarter = PS.pixel_shift_capture(sc, F, [[0.0, 0.0]], None, fill_factor=0.25)[0]
    assert np.allclose(full, 0.5)
    assert np.allclose(quarter, 0.5)                     # 中央 2 標本 = 0 と 1 が 1 つずつ


def test_four_shot_gives_every_colour_at_every_pixel_and_no_false_colour():
    blk, sc = _block_scene(24, 24, seed=1)
    nom = PS.pixel_shift_pattern("4shot")
    raw = PS.pixel_shift_capture(sc, F, nom, "RGGB", margin=2)
    merged = PS.pixel_shift_merge(raw, nom, "RGGB")
    truth = blk[2:-2, 2:-2]
    assert np.abs(merged - truth)[1:, 1:].max() < 1e-12   # 端の 1 行 1 列は (0,0) の 1 枚で埋めた所
    gray = np.repeat(truth.mean(-1, keepdims=True), 3, -1)
    fc = PS.false_color_metric(gray)
    assert fc["max"] < 1e-12 and fc["n_pixels"] == gray.shape[0] * gray.shape[1]


def test_sixteen_shot_matches_the_half_pixel_ideal_sensor():
    _blk, sc = _block_scene(20, 20, seed=2)
    nom = PS.pixel_shift_pattern("16shot")
    assert nom.shape == (16, 2)
    m = PS.pixel_shift_merge(PS.pixel_shift_capture(sc, F, nom, "RGGB", margin=2), nom, "RGGB", scale=2)
    want = np.zeros_like(m)
    for a in (0, 1):
        for b in (0, 1):
            want[a::2, b::2] = PS.pixel_shift_capture(sc, F, [[a / 2, b / 2]], None, margin=2)[0]
    assert np.abs(m - want)[2:-2, 2:-2].max() < 1e-12


def test_half_pixel_shift_resolves_what_one_frame_aliases():
    hs = 72 * F
    f0 = 0.7
    xc = (np.arange(hs) + 0.5) / F
    row = 0.5 + 0.4 * np.cos(2 * np.pi * f0 * xc) * np.sinc(f0 / F)
    sc = np.repeat(row[None, :], hs, 0)
    nom = PS.pixel_shift_pattern("half4")
    one = PS.pixel_shift_capture(sc, F, [[0.0, 0.0]], None, margin=2)[0]
    hr = PS.pixel_shift_merge(PS.pixel_shift_capture(sc, F, nom, None, margin=2), nom, None, scale=2)

    def peak(img, scale):
        r = img.mean(0) - img.mean()
        sp = np.abs(np.fft.rfft(r * np.hanning(r.size)))
        return np.fft.rfftfreq(r.size, 1.0 / scale)[int(np.argmax(sp[2:])) + 2]

    assert abs(peak(one, 1) - (1 - f0)) < 0.02             # 折り返し
    assert abs(peak(hr, 2) - f0) < 0.02                    # 正しい周波数


def test_merge_is_fail_closed():
    _blk, sc = _block_scene(16, 16)
    nom = PS.pixel_shift_pattern("4shot")
    raw = PS.pixel_shift_capture(sc, F, nom, "RGGB")
    with pytest.raises(ValueError, match="cover only"):
        PS.pixel_shift_merge(raw, nom, "RGGB", scale=2)       # 1 画素シフトでは半画素の格子を埋められない
    with pytest.raises(ValueError, match="not on the 1/1-pixel grid"):
        PS.pixel_shift_merge(raw, nom + 0.4, "RGGB")          # 誤差込みのシフトを渡した
    with pytest.raises(ValueError, match="cover only"):
        PS.pixel_shift_merge(raw[:2], nom[:2], "RGGB")        # 2 枚の Bayer は色を埋めない
    with pytest.raises(ValueError, match="shifts for"):
        PS.pixel_shift_merge(raw, nom[:3], "RGGB")
    with pytest.raises(ValueError, match="NaN"):
        PS.pixel_shift_merge(np.where(raw > 0.5, np.nan, raw), nom, "RGGB")
    with pytest.raises(ValueError, match="pattern"):
        PS.pixel_shift_merge(raw, nom, "RGBX")


def test_capture_is_fail_closed():
    _blk, sc = _block_scene(16, 16)
    with pytest.raises(ValueError, match="RGB scene"):
        PS.pixel_shift_capture(sc[..., 0], F, [[0, 0]], "RGGB")
    with pytest.raises(ValueError, match="multiple of factor"):
        PS.pixel_shift_capture(sc[:-3], F, [[0, 0]], None)
    with pytest.raises(ValueError, match="registration"):
        PS.pixel_shift_capture(sc, F, [[0, 5.0]], None)
    with pytest.raises(ValueError, match="margin"):
        PS.pixel_shift_capture(sc, F, [[0, 1.0]], None, margin=0)
    with pytest.raises(ValueError, match="fill_factor"):
        PS.pixel_shift_capture(sc, F, [[0, 0]], None, fill_factor=0.0)
    with pytest.raises(ValueError, match="frames"):
        PS.pixel_shift_capture(np.stack([sc, sc]), F, [[0, 0]], None, per_frame=True)
    with pytest.raises(ValueError, match="error_px"):
        PS.pixel_shift_pattern("4shot", error_px=0.6)
    with pytest.raises(ValueError, match="mode"):
        PS.pixel_shift_pattern("8shot")


def test_shift_error_and_cycles():
    e = PS.pixel_shift_pattern("4shot", error_px=0.1, seed=3) - PS.pixel_shift_pattern("4shot")
    assert 0 < np.abs(e).max() < 0.5
    assert np.array_equal(PS.pixel_shift_pattern("4shot", error_px=0.1, seed=3),
                          PS.pixel_shift_pattern("4shot", error_px=0.1, seed=3))
    assert PS.pixel_shift_pattern("4shot", cycles=3).shape == (12, 2)


def test_noise_falls_with_samples_per_point():
    rng = np.random.default_rng(0)
    flat = np.full((44 * F, 44 * F, 3), 0.5)
    nom = PS.pixel_shift_pattern("4shot", cycles=4)
    raw = PS.pixel_shift_capture(flat, F, nom, "RGGB") + rng.normal(0, 0.02, (16, 42, 42))
    m = PS.pixel_shift_merge(raw, nom, "RGGB")[2:-2, 2:-2]
    assert abs(m[..., 0].std() / (0.02 / 2) - 1) < 0.1          # R: 4 標本
    assert abs(m[..., 1].std() / (0.02 / math.sqrt(8)) - 1) < 0.1   # G: 8 標本


def test_motion_mask_finds_a_moving_patch_and_merge_falls_back():
    rng = np.random.default_rng(1)
    _blk, base = _block_scene(40, 40, seed=4)
    nom = PS.pixel_shift_pattern("4shot")
    scenes = []
    for i in range(4):
        s = base.copy()
        s[12 * F:24 * F, (10 + 2 * i) * F:(18 + 2 * i) * F] = 0.95     # 白い部品が 2 px/枚 で右へ
        scenes.append(s)
    raw = PS.pixel_shift_capture(np.stack(scenes), F, nom, "RGGB", per_frame=True) + rng.normal(0, 0.003, (4, 38, 38))
    mask = PS.pixel_shift_motion_mask(raw, nom, "RGGB", threshold=4.0)
    assert mask.shape == (38, 38) and set(np.unique(mask)) <= {0.0, 1.0}
    assert mask[11:22, 9:24].mean() > 0.3 and mask[28:, :].mean() < 0.02
    fixed = PS.pixel_shift_merge(raw, nom, "RGGB", motion_threshold=4.0)
    naive = PS.pixel_shift_merge(raw, nom, "RGGB")
    assert fixed.shape == naive.shape == (38, 38, 3)
    assert not np.array_equal(fixed, naive)
    assert np.array_equal(fixed[30:, 30:], naive[30:, 30:])        # 止まっている所は 4 枚のまま


def test_resolution_budget_closed_forms():
    b = PS.pixel_shift_resolution_budget(3.45, 2.8)
    assert math.isclose(b["Q"], 0.55 * 2.8 / 3.45)
    assert math.isclose(b["mtf_at_nyquist_single"]["aperture"], 2 / math.pi, rel_tol=1e-12)
    assert b["regime"] == "pixel_limited" and b["gain"] > 1.5
    lens = PS.pixel_shift_resolution_budget(3.45, 16.0)
    assert lens["regime"] == "lens_limited" and lens["gain"] == 1.0
    no_lens = PS.pixel_shift_resolution_budget(3.45, 1e-6)
    assert abs(no_lens["mtf50_cyc_px"] - 0.60335) < 1e-4            # sinc(f) = 0.5
    half_fill = PS.pixel_shift_resolution_budget(3.45, 1e-6, fill_factor=0.5)
    assert half_fill["aperture_zero_cyc_px"] == 2.0
    with pytest.raises(ValueError, match="step_px"):
        PS.pixel_shift_resolution_budget(3.45, 2.8, step_px=0.3)
    with pytest.raises(ValueError, match="pitch_um"):
        PS.pixel_shift_resolution_budget(0.0, 2.8)


def test_false_color_metric_with_reference_and_border():
    rgb = np.zeros((10, 10, 3))
    rgb[..., 0] = 1.0                                              # 真っ赤
    assert PS.false_color_metric(rgb)["mean"] > 0.5
    assert PS.false_color_metric(rgb, reference=rgb)["max"] == 0.0
    assert PS.false_color_metric(rgb, border=2)["n_pixels"] == 36
    with pytest.raises(ValueError, match="border"):
        PS.false_color_metric(rgb, border=5)
    with pytest.raises(ValueError, match="reference"):
        PS.false_color_metric(rgb, reference=rgb[:5])


def test_registered_in_the_optics_ledger():
    assert opsoptics.list_ops("pixelshift") == [
        "pixel_shift_pattern", "pixel_shift_capture", "pixel_shift_merge", "pixel_shift_motion_mask",
        "false_color_metric", "pixel_shift_resolution_budget"]
    for name in opsoptics.list_ops("pixelshift"):
        assert opsoptics.get(name) is getattr(PS, name)
