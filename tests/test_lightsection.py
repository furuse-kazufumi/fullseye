# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Gates for lightsection.py — light-section (laser triangulation) and its speckle floor.

真値はどれも「使った式」と別の経路から取る:
  * ガウスの対数は 2 次式(定理)/ 対称な断面の重心は中心(定理)/ 箱で積分しても重心は動かない
  * Steger の 1 ステップ(Newton 法)の偏り −δ³/(σ² − δ²)(ガウスの断面での閉形式)
  * 順方向 = camera.project_points、逆方向 = 視線と光面の交点(別のコード)
  * スペックルの床 = Dorsch の閉形式 vs coherent のコヒーレント結像のシミュ
  * 読み出し雑音の項 = 線形化した重心の分散 vs 滑らかな面に雑音だけを足したシミュ
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import lightsection as L  # noqa: E402
import spc  # noqa: E402


def _gauss_line(ny=96, nx=200, sigma=1.7, c_lo=40.0, c_hi=41.0):
    c0 = np.linspace(c_lo, c_hi, nx, endpoint=False)
    y = np.arange(ny, dtype=float)[:, None]
    return np.exp(-0.5 * ((y - c0) / sigma) ** 2), c0


def _rig():
    return L.light_section_rig(30.0, 200.0, 2000.0, (480, 640))


def _step_bead(x):
    return np.where(np.abs(x) < 5.0, 2.0, 0.0) + 0.8 * np.exp(-x * x / 2.0)


X = np.linspace(-15.0, 15.0, 601)


# --------------------------------------------------------------------------- #
# 1. 線の中心
# --------------------------------------------------------------------------- #
def test_gauss_fit_is_exact_on_a_point_sampled_gaussian_line():
    img, c0 = _gauss_line()
    for hw in (1, 2, 4):
        r = L.laser_line_center_gauss(img, half_window=hw)
        assert r["n_valid"] == img.shape[1]
        assert np.max(np.abs(r["row"] - c0)) < 1e-9
        assert np.allclose(r["sigma_px"], 1.7, atol=1e-9)


def test_centroid_is_exact_on_a_symmetric_line_and_box_filtering_does_not_move_it():
    img, c0 = _gauss_line(sigma=3.0)
    r = L.laser_line_center_centroid(img)
    assert np.max(np.abs(r["row"] - c0)) < 1e-9
    # 画素の面積で積分した光条(誤差関数の差)でも重心は動かない
    rig = _rig()
    prof = np.column_stack([X, _step_bead(X)])
    for samp in ("point", "pixel"):
        c = L.laser_line_center_centroid(L.light_section_render(rig, prof, sampling=samp))
        P = L.light_section_profile(c, rig)
        assert np.max(np.abs(P[:, 2] - np.interp(P[:, 0], X, prof[:, 1]))) < 1e-9


def test_steger_bias_is_the_closed_form_of_one_newton_step_on_a_gaussian():
    """誤差 = −δ³/(σ_line² + σ² − δ²)(δ = 出発の画素の中心からのずれ)。

    ★門に力があること: 偏りそのもの(0.006〜0.013 px)は残差の許容(2e-5)の 250 倍以上。
    """
    for sl, s in ((1.7, 1.5), (2.5, 2.0)):
        img, c0 = _gauss_line(nx=400, sigma=sl, c_lo=39.5, c_hi=40.5)
        r = L.laser_line_center_steger(img, sigma=s)
        S2 = sl * sl + s * s
        d = np.round(c0) - c0
        pred = c0 - d ** 3 / (S2 - d * d)
        m = np.abs(d) <= 0.4
        assert np.max(np.abs(r["row"][m] - pred[m])) < 2e-5
        assert np.max(np.abs(r["row"][m] - c0[m])) > 250 * 2e-5


def test_steger_follows_a_tilted_line_along_its_normal():
    ny, nx = 120, 160
    yy, xx = np.mgrid[0:ny, 0:nx].astype(float)
    a, b = 0.3, 30.0                                      # 行 = a·列 + b
    dist = (yy - (a * xx + b)) / math.hypot(1.0, a)
    img = np.exp(-0.5 * (dist / 2.0) ** 2)
    r = L.laser_line_center_steger(img, sigma=2.0)
    v = r["valid"]
    assert v[10:-10].all()
    off = (r["row"][v] - (a * r["col"][v] + b)) / math.hypot(1.0, a)
    inner = (r["col"][v] > 10) & (r["col"][v] < nx - 10)
    assert np.max(np.abs(off[inner])) < 0.02             # 1 ステップの偏りの上限 0.125/σ² の桁
    assert abs(float(np.nanmedian(r["ny"][v]))) == pytest.approx(1.0 / math.hypot(1.0, a), abs=1e-3)


def test_dark_columns_are_marked_invalid_not_guessed():
    img, _ = _gauss_line()
    img[:, 50:60] = 0.0
    for fn in (L.laser_line_center_centroid, L.laser_line_center_gauss, L.laser_line_center_steger):
        r = fn(img)
        assert not r["valid"][50:60].any()
        assert np.isnan(r["row"][50:60]).all()


# --------------------------------------------------------------------------- #
# 2. 装置・合成・三角測量・校正・走査
# --------------------------------------------------------------------------- #
def test_rig_geometry():
    rig = _rig()
    C = -rig["R"].T @ rig["t"]
    assert np.linalg.norm(C) == pytest.approx(200.0, rel=1e-12)
    pts = np.column_stack([np.linspace(-5, 5, 7), np.zeros(7), np.linspace(-2, 3, 7)])
    Xc = pts @ rig["R"].T + rig["t"]
    assert np.max(np.abs(Xc @ rig["plane_normal"] - rig["plane_d"])) < 1e-12


@pytest.mark.parametrize("method", ["centroid", "gauss"])
def test_render_then_triangulate_returns_the_true_heights(method):
    rig = _rig()
    c = L._METHODS[method](L.light_section_render(rig, np.column_stack([X, _step_bead(X)])))
    P = L.light_section_profile(c, rig)
    assert P.shape[0] == 300
    assert np.max(np.abs(P[:, 1])) < 1e-9                # 光面 Y = 0 の上
    assert np.max(np.abs(P[:, 2] - np.interp(P[:, 0], X, _step_bead(X)))) < 1e-9


def test_steger_heights_away_from_the_line_ends():
    rig = _rig()
    c = L.laser_line_center_steger(L.light_section_render(rig, np.column_stack([X, _step_bead(X)])))
    P = L.light_section_profile(c, rig)
    e = P[:, 2] - np.interp(P[:, 0], X, _step_bead(X))
    inner = (np.abs(P[:, 0]) < 14.0) & (np.abs(np.abs(P[:, 0]) - 5.0) > 1.0)
    # 平らな所に残る一定の偏り(実測 −0.006 mm)は 1 ステップの Newton の偏り −δ³/(σ² − δ²) が
    # 画像の行のずれ δ ごとに決まったもの(画素の単位で閉形式どおりなのは上の門)。頂の曲率の偏り
    # (実測 0.011 mm)を足しても 0.015 mm を超えない。光条の端(切れ目)は除く。
    assert np.max(np.abs(e[inner])) < 0.015


def test_light_plane_calibration_recovers_the_plane_and_refuses_one_height():
    rig = _rig()
    hs = [0.0, 3.0, 6.0]
    T = L.light_section_targets(rig, hs)
    cl = [L.laser_line_center_gauss(L.light_section_render(rig, np.column_stack([X, np.full_like(X, h)])))
          for h in hs]
    cal = L.light_plane_calibrate(cl, T, rig["K"])
    assert np.allclose(cal["plane_normal"], rig["plane_normal"], atol=1e-9)
    assert cal["plane_d"] == pytest.approx(rig["plane_d"], abs=1e-9)
    assert cal["rms_mm"] < 1e-9
    with pytest.raises(ValueError, match="one line"):
        L.light_plane_calibrate(cl[:1], L.light_section_targets(rig, hs[:1]), rig["K"])
    # 雑音つき(頂に対し 1 %)では法線の角度の誤差 < 0.01°
    cl = [L.laser_line_center_gauss(L.light_section_render(rig, np.column_stack([X, np.full_like(X, h)]),
                                                           noise=0.01, seed=k, sampling="pixel"))
          for k, h in enumerate(hs)]
    cal = L.light_plane_calibrate(cl, T, rig["K"])
    ang = math.degrees(math.acos(min(1.0, abs(float(cal["plane_normal"] @ rig["plane_normal"])))))
    assert ang < 0.01
    assert cal["rms_mm"] < 0.01


def test_one_height_is_refused_even_with_noise():
    """回帰(2026-11-03、PoC で発見): 雑音つきの 1 直線の点は特異値の判定だけでは通ってしまった。"""
    rig = _rig()
    c = L.laser_line_center_gauss(L.light_section_render(rig, np.column_stack([X, np.zeros_like(X)]),
                                                         noise=0.01, seed=3, sampling="pixel"))
    with pytest.raises(ValueError, match="one target plane"):
        L.light_plane_calibrate([c], L.light_section_targets(rig, [0.0]), rig["K"])
    with pytest.raises(ValueError, match="one target plane"):
        L.light_plane_calibrate([c, c], L.light_section_targets(rig, [0.0, 0.0]), rig["K"])


def test_step_target_in_one_image_with_column_ranges():
    rig = _rig()
    prof = np.column_stack([X, np.where(X < 0, 0.0, 4.0)])
    c = L.laser_line_center_gauss(L.light_section_render(rig, prof))
    u_split = rig["K"][0, 2]                               # x = 0 はほぼ主点の列
    T = L.light_section_targets(rig, [0.0, 4.0], col_ranges=[(0, u_split - 8), (u_split + 8, 1e9)])
    cal = L.light_plane_calibrate([c, c], T, rig["K"])
    assert np.allclose(cal["plane_normal"], rig["plane_normal"], atol=1e-9)


def test_scan_and_height_map_of_a_moving_part():
    rig = _rig()
    frames, truth = [], []
    for k in range(6):
        hk = 0.5 * k + _step_bead(X)
        truth.append(hk)
        frames.append(L.light_section_render(rig, np.column_stack([X, hk])))
    H = L.light_section_height_map(frames, rig, method="gauss")
    assert H.shape == (6, 640)
    assert np.isnan(H[:, :150]).all() and np.isnan(H[:, 500:]).all()   # 光条の無い列は NaN
    pts = L.light_section_scan(frames, rig, step_mm=(0.0, 0.25, 0.0), method="gauss")
    for k in range(6):
        sel = np.abs(pts[:, 1] + 0.25 * k) < 1e-9          # Y = −k·step(部品の座標)
        assert sel.sum() >= 300                             # 高いほど光条が少し長く写る
        assert np.max(np.abs(pts[sel, 2] - np.interp(pts[sel, 0], X, truth[k]))) < 1e-9
    good = ~np.isnan(H)
    assert good.sum() == pts.shape[0]


# --------------------------------------------------------------------------- #
# 3. スペックルの床と不確かさの予算(Fullseye だけの層)
# --------------------------------------------------------------------------- #
def test_speckle_floor_simulation_agrees_with_dorsch_closed_form():
    """重心の推定の床: シミュ / 閉形式 = 0.89(実測)。2π の無い形なら 6 倍ずれる。"""
    r = L.light_section_speckle_floor(n_trials=12)
    assert 0.8 < r["ratio_sim_to_closed_form"] < 1.15, r["ratio_sim_to_closed_form"]
    lo, hi = r["sim_ci95_um"]
    assert lo < r["sim_delta_z_um"] < hi
    assert abs(r["sim_bias_um"]) < 3 * r["sim_delta_z_um"] / math.sqrt(r["n_samples"])


def test_speckle_floor_exponents_follow_the_closed_form():
    sw = L.light_section_floor_sweep("wavelength_um", [0.4, 0.55, 0.8], n_trials=10)
    assert abs(sw["slope_sim"] - 1.0) < 0.12, sw["slope_sim"]
    assert sw["slope_closed_form"] == pytest.approx(1.0, abs=1e-12)
    sw = L.light_section_floor_sweep("sin_theta", [0.3, 0.5, 0.8], n_trials=6)
    assert abs(sw["slope_sim"] + 1.0) < 0.02                 # sin θ は高さへの換算にだけ入る
    assert set(sw["dominant"]) == {"speckle"}


def test_diversity_lowers_the_floor_as_one_over_root_n():
    r = L.light_section_speckle_floor(n_patterns=4, n_trials=12)
    assert r["contrast"] == pytest.approx(0.5)
    assert 0.8 < r["ratio_sim_to_closed_form"] < 1.2


def test_read_noise_term_matches_a_speckle_free_simulation():
    for nz in (0.02, 0.1):
        r = L.light_section_speckle_floor(noise_rel=nz, smooth_surface=True, n_trials=12)
        lo, hi = r["sim_ci95_um"]
        assert lo < r["noise_term_um"] < hi, (nz, r["sim_ci95_um"], r["noise_term_um"])
        assert r["ratio_sim_to_closed_form_total"] == pytest.approx(1.0, abs=0.05)


def test_estimator_matters_under_speckle():
    """5 点のガウス当てはめは粒の頂を当ててしまい床の 2.5 倍以上。Steger(σ = w/√3)は床どおり。"""
    g = L.light_section_speckle_floor(method="gauss", center_kw={"half_window": 2}, n_trials=8)
    assert g["ratio_sim_to_closed_form"] > 2.0
    s = L.light_section_speckle_floor(method="steger", n_trials=8)
    assert 0.8 < s["ratio_sim_to_closed_form"] < 1.15


def test_budget_feeds_the_gum_family():
    b = L.light_section_uncertainty_budget(noise_rel=0.05, calib_rms_um=0.8, calib_dof=20)
    g = spc.gum_propagate(b)
    assert float(g["u_combined"][0]) == pytest.approx(b["combined_u_z_um"], rel=1e-12)
    e = spc.gum_expanded(b)
    assert float(e["expanded"][0]) > 1.96 * b["combined_u_z_um"]
    assert b["dominant"] == "speckle"
    assert b["delta_z_um"][0] == pytest.approx(
        L._coherent.triangulation_speckle_limit(0.65, 0.1, 0.5)["delta_z_um"], rel=1e-12)


# --------------------------------------------------------------------------- #
# 4. fail-closed
# --------------------------------------------------------------------------- #
def test_fail_closed():
    rig = _rig()
    with pytest.raises(ValueError):
        L.light_section_profile({"col": [0], "row": [0], "valid": [True]}, rig)
    with pytest.raises(ValueError):
        L.light_section_profile(L.laser_line_center_gauss(_gauss_line()[0]), {"kind": "other"})
    with pytest.raises(ValueError):
        L.laser_line_center_gauss(np.full((10, 10), np.nan))
    with pytest.raises(ValueError):
        L.light_section_render(rig, np.column_stack([X[::-1], _step_bead(X)]))
    with pytest.raises(ValueError):
        L.light_section_floor_sweep("pixel_um", [1, 2])
    with pytest.raises(ValueError, match="no valid centre"):
        L.light_section_speckle_floor(noise_rel=5.0, method="gauss", n_trials=2, n_columns=64)
