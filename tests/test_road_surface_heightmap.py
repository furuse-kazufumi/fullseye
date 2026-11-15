# -*- coding: utf-8 -*-
"""road_surface_heightmap(drivelateral、2026-11-15)の真値の門。

作り方そのものが真値なので、op の式だけで閉じる門は検算にならない。ここでは op の外の真値で突き合わせる:

1. 直線・勾配 g・拝み勾配 c: 世界の座標の閉形式 z = g·x − c·|y|(射影を通らない式)。片勾配 1 では z = g·x − rate·y。
2. 左の円弧(半径 R、clothoid_points の線形): 円の中心からの極座標の閉形式 z = g·R·φ − c·|R − r|、
   s = R·φ、e = R − r。真値の勾配は内側ほど急 g·R/(R − e)。折線の射影だけの写しは mm で外れる(直す前に落ちる)。
3. 放物線の縦断曲線: z_c(s) = g1·s + (g2 − g1)·s²/(2L) が標本の間でも厳密(3 次 Hermite)。
4. 既存の op で読み戻す: 回した直線の道の車線の窓を crop_rectangle2 → surface_form_remove にかけると、
   係数が (g, −c) に戻る。dem_slope(Horn)の中央値が atan(√(g² + c²))。
5. 推定した曲率(heading / curvature の列なし)を curvature_torsion(既存の op)の 1/R と照合する。
6. 片勾配のすりつけを道路構造令の表(drivelateral の TRANSITION_LENGTH・MAX_SUPERELEVATION)の長さと値で作ると、
   車線の中央の横勾配がすりつけの区間で一次に動き、終わりで −rate になる。右の車線は途中で 0(平ら)を通る。
7. 真値の勾配と、高さ図の数値微分(中心差分)が一致する(面と真値が同じものを指している)。
8. 地形へのなじませ: 車道は地形に依らずビット一致、外側は地形へ寄る。混ぜたセルの真値は nan(言わない)。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import drivelateral as DL


def _centres(H, T):
    ext, c = T["extent"], T["cell"]
    xc = ext[0] + (np.arange(H.shape[1]) + 0.5) * c
    yc = ext[2] + (np.arange(H.shape[0]) + 0.5) * c
    return np.meshgrid(xc, yc)


def _arc(R=35.0, g=0.06, step=1.0, exact=True):
    L = math.pi * R
    ss = np.arange(0.0, L + 1e-9, step)
    cp = DL.clothoid_points(L, ss, kappa0=1.0 / R, kappa1=1.0 / R)
    road = {"x": cp["points"][:, 0], "y": cp["points"][:, 1], "z": g * ss, "s": ss}
    if exact:
        road.update(heading=cp["heading"], curvature=cp["curvature"])
    return road


def _polar(X, Y, R):
    r = np.hypot(X, Y - R)
    phi = np.arctan2(X, R - Y)                          # 始点 (0, 0)・中心 (0, R)・左回り
    return r, phi


@pytest.mark.parametrize("g,c", [(0.06, 0.02), (-0.09, 0.015)])
def test_straight_crowned_road_matches_the_world_closed_form(g, c):
    s = np.arange(0.0, 40.01, 0.5)
    road = {"x": s, "y": np.zeros_like(s), "z": g * s, "s": s}
    H, T = DL.road_surface_heightmap(road, 0.1, extent=(5.0, 35.0, -3.4, 3.4), crossfall=c, return_truth=True)
    X, Y = _centres(H, T)
    assert np.abs(H - (g * X - c * np.abs(Y))).max() < 1e-12
    assert np.abs(T["grade"] - g).max() < 1e-12
    assert np.allclose(T["cross"][Y > 0], -c) and np.allclose(T["cross"][Y < 0], c)
    assert np.allclose(T["s"], X) and np.allclose(T["e"], Y)
    assert T["carriageway"].all()


def test_superelevated_section_is_a_plane():
    s = np.arange(0.0, 40.01, 0.5)
    road = {"x": s, "y": np.zeros_like(s), "z": 0.06 * s, "s": s,
            "beta": np.ones_like(s), "rate": np.full_like(s, 0.05)}
    H, T = DL.road_surface_heightmap(road, 0.1, extent=(5.0, 35.0, -3.4, 3.4), return_truth=True)
    X, Y = _centres(H, T)
    assert np.abs(H - (0.06 * X - 0.05 * Y)).max() < 1e-12
    assert np.abs(T["cross"] + 0.05).max() < 1e-12


def test_circular_arc_matches_the_polar_closed_form_and_the_inner_lane_is_steeper():
    R, g = 35.0, 0.06
    H, T = DL.road_surface_heightmap(_arc(R, g), 0.05, extent=(-5.0, 40.0, -5.0, 75.0), return_truth=True)
    X, Y = _centres(H, T)
    r, phi = _polar(X, Y, R)
    e = R - r
    on = (phi > 0.05) & (phi < math.pi - 0.05) & (np.abs(e) < 3.4)
    assert on.sum() > 50000
    assert np.abs(H - (g * R * phi - 0.02 * np.abs(e)))[on].max() < 1e-9
    assert np.abs(T["s"] - R * phi)[on].max() < 1e-9 and np.abs(T["e"] - e)[on].max() < 1e-9
    assert np.abs(T["grade"] - g * R / (R - e))[on].max() < 1e-9      # 内側(e > 0)ほど急
    inner = on & (np.abs(e - 1.5) < 0.05)
    outer = on & (np.abs(e + 1.5) < 0.05)
    assert T["grade"][inner].min() > g > T["grade"][outer].max()


def test_polyline_only_projection_misses_the_closed_form_by_millimetres(monkeypatch):
    """直す前で落ちる: 局所の円弧で射影し直さない写し(折線の射影だけ、製作の Centerline と同じ)。"""
    R, g = 35.0, 0.06
    orig = DL._foot_on_local_arc
    monkeypatch.setattr(DL, "_foot_on_local_arc", lambda P, C, th, k: orig(P, C, th, np.zeros_like(k)))
    H, T = DL.road_surface_heightmap(_arc(R, g, step=1.0), 0.05, extent=(-5.0, 40.0, -5.0, 75.0), return_truth=True)
    X, Y = _centres(H, T)
    r, phi = _polar(X, Y, R)
    on = (phi > 0.05) & (phi < math.pi - 0.05) & (np.abs(R - r) < 3.4)
    err = np.abs(H - (g * R * phi - 0.02 * np.abs(R - r)))[on].max()
    assert err > 1e-3                                                 # 頂点の折れ目 = mm の段


def test_parabolic_vertical_curve_is_exact_between_samples():
    g1, g2, Lv = 0.02, 0.09, 30.0
    s = np.arange(0.0, Lv + 1e-9, 2.0)                               # 標本は 2 m おき
    road = {"x": s, "y": np.zeros_like(s), "z": g1 * s + (g2 - g1) * s ** 2 / (2 * Lv), "s": s}
    H, T = DL.road_surface_heightmap(road, 0.1, extent=(0.0, 30.0, -0.05, 0.05), return_truth=True)
    x = (np.arange(H.shape[1]) + 0.5) * 0.1
    assert np.abs(H[0] - (g1 * x + (g2 - g1) * x ** 2 / (2 * Lv))).max() < 1e-12
    assert np.abs(T["grade"][0] - (g1 + (g2 - g1) * x / Lv)).max() < 1e-12


def test_lane_window_read_back_by_crop_rectangle2_and_surface_form_remove():
    """既存の op の合成で (縦断勾配, 横勾配) を読み戻す: 回した直線の道の左の車線。"""
    import image_gen
    import roughness
    psi, g, c, cell = 0.7, 0.07, 0.02, 0.05
    s = np.arange(-5.0, 45.01, 0.5)
    road = {"x": s * math.cos(psi), "y": s * math.sin(psi), "z": g * s, "s": s, "heading": np.full_like(s, psi),
            "curvature": np.zeros_like(s)}
    H, T = DL.road_surface_heightmap(road, cell, extent=(-2.0, 36.0, -4.0, 30.0), return_truth=True)
    s0, e0 = 20.0, 1.5                                                # 左の車線の中央
    xw, yw = s0 * math.cos(psi) - e0 * math.sin(psi), s0 * math.sin(psi) + e0 * math.cos(psi)
    col = (xw - T["extent"][0]) / cell - 0.5
    row = (yw - T["extent"][2]) / cell - 0.5
    win = image_gen.crop_rectangle2(H, row, col, psi, 20.0, 18.0)     # 長さ 2 m・幅 1.8 m(車線の中)
    _res, coef = roughness.surface_form_remove(win, cell, order=1)
    assert abs(coef[1] - g) < 1e-9 and abs(coef[2] + c) < 1e-9
    import demops
    lane = DL.road_surface_heightmap(dict(road, heading=np.zeros_like(s), x=s, y=np.zeros_like(s)), 0.1,
                                     extent=(5.0, 35.0, 0.3, 2.7))
    slope = demops.dem_slope(lane, 0.1)
    assert abs(np.median(slope) - math.degrees(math.atan(math.hypot(g, c)))) < 1e-9


def test_estimated_curvature_agrees_with_curvature_torsion():
    """heading / curvature の列を渡さないときに標本から作る曲率を、既存の curvature_torsion と照合する。"""
    import curve3d
    R = 35.0
    road = _arc(R, 0.06, step=0.5, exact=False)
    H, T = DL.road_surface_heightmap(road, 0.25, extent=(-5.0, 40.0, -5.0, 75.0), return_truth=True)
    kappa_ct = np.asarray(curve3d.curvature_torsion(np.c_[road["x"], road["y"], road["z"]])[0])
    X, Y = _centres(H, T)
    r, phi = _polar(X, Y, R)
    on = (phi > 0.2) & (phi < math.pi - 0.2) & (np.abs(R - r) < 3.4)
    # 3-D の曲率は勾配の分だけ小さい(弧長が √(1 + g²) 倍): κ_3d = κ_plan / (1 + g²)
    assert abs(np.median(kappa_ct[5:-5]) * (1 + 0.06 ** 2) - 1.0 / R) < 5e-6   # 差分の O(h²)
    assert np.abs(T["curvature"][on] - 1.0 / R).max() < 1e-6
    r2, phi2 = _polar(X, Y, R)
    assert np.abs(H - (0.06 * R * phi2 - 0.02 * np.abs(R - r2)))[on].max() < 2e-3   # 推定でも mm 以内


def test_superelevation_runoff_with_the_road_structure_tables():
    """すりつけの長さ = 道路構造令 第 18 条の表(設計速度 30 km/h → 25 m)、片勾配 ≤ 第 16 条の表の値。"""
    L_run = float(DL.TRANSITION_LENGTH[30])
    rate = 0.06
    assert rate <= DL.MAX_SUPERELEVATION["other"]
    s = np.arange(0.0, 60.01, 0.5)
    beta = np.clip((s - 10.0) / L_run, 0.0, 1.0)
    road = {"x": s, "y": np.zeros_like(s), "z": 0.04 * s, "s": s, "beta": beta, "rate": np.full_like(s, rate)}
    H, T = DL.road_surface_heightmap(road, 0.1, extent=(0.0, 60.0, -3.4, 3.4), return_truth=True)
    X, Y = _centres(H, T)
    i_l = int(np.argmin(np.abs(Y[:, 0] - 1.55)))                      # 左の車線の中央の行
    i_r = int(np.argmin(np.abs(Y[:, 0] + 1.55)))
    cl, cr = T["cross"][i_l], T["cross"][i_r]
    b = np.clip((X[0] - 10.0) / L_run, 0.0, 1.0)
    assert np.abs(cl - (-(1 - b) * 0.02 - b * rate)).max() < 1e-12   # 一次で −c から −rate へ
    assert np.abs(cr - ((1 - b) * 0.02 - b * rate)).max() < 1e-12
    assert cr[X[0] < 10].min() > 0 and cr[X[0] > 10 + L_run].max() < 0   # 右の車線は途中で平ら(0)を通る
    # すりつけ中の縁の勾配は中心線と違う(相対勾配): ∂z/∂s = g + ∂p/∂β · β'
    run = (X[0] > 11.0) & (X[0] < 10.0 + L_run - 1.0)
    e = Y[i_l, 0]
    assert np.abs(T["grade"][i_l][run] - (0.04 + (0.02 * abs(e) - rate * e) / L_run)).max() < 1e-12


def test_truth_grade_matches_the_numerical_derivative_of_the_heights():
    R, g = 35.0, 0.06
    H, T = DL.road_surface_heightmap(_arc(R, g), 0.05, extent=(-5.0, 40.0, -5.0, 75.0), return_truth=True)
    X, Y = _centres(H, T)
    gy, gx = np.gradient(H, 0.05)
    hd = T["heading"]
    num_grade = gx * np.cos(hd) + gy * np.sin(hd)
    num_cross = -gx * np.sin(hd) + gy * np.cos(hd)
    r, phi = _polar(X, Y, R)
    e = R - r
    lane = (phi > 0.1) & (phi < math.pi - 0.1) & (np.abs(np.abs(e) - 1.6) < 1.2)   # 頂と縁から離れた車線
    assert np.abs(num_grade - T["grade"])[lane].max() < 1e-5
    assert np.abs(num_cross - T["cross"])[lane].max() < 1e-5


def test_blending_into_terrain_keeps_the_carriageway_and_hides_the_blended_truth():
    s = np.arange(0.0, 40.01, 0.5)
    road = {"x": s, "y": np.zeros_like(s), "z": 0.05 * s, "s": s}
    H0, T0 = DL.road_surface_heightmap(road, 0.1, return_truth=True)
    X, Y = _centres(H0, T0)
    terr = 0.3 * Y + 0.01 * X
    H1, T1 = DL.road_surface_heightmap(road, 0.1, terrain=terr, return_truth=True)
    car = T0["carriageway"]
    assert car.sum() > 1000 and np.array_equal(H1[car], H0[car])        # 車道はビット一致
    far = np.abs(Y) > 9.5 + 0.05
    assert np.abs(H1[far & (X > 0) & (X < 40)] - terr[far & (X > 0) & (X < 40)]).max() < 1e-12
    blended = (np.abs(T1["e"]) > 5.0) | (T1["s"] < 0.0) | (T1["s"] > 40.0)
    assert np.isnan(T1["grade"][blended]).all() and np.isfinite(T1["grade"][~blended]).all()
    with pytest.raises(ValueError, match="terrain"):
        DL.road_surface_heightmap(road, 0.1, terrain=terr[:-1])


def test_refusals():
    s = np.arange(0.0, 10.01, 0.5)
    road = {"x": s, "y": np.zeros_like(s), "z": 0.05 * s}
    with pytest.raises(ValueError, match="empty"):
        DL.road_surface_heightmap({})
    with pytest.raises(ValueError, match="column"):
        DL.road_surface_heightmap({"x": s, "y": s})
    with pytest.raises(ValueError, match="unknown"):
        DL.road_surface_heightmap(dict(road, banking=s))
    with pytest.raises(ValueError, match="beta"):
        DL.road_surface_heightmap(dict(road, beta=np.full_like(s, 1.5)))
    with pytest.raises(ValueError, match="repeated"):
        DL.road_surface_heightmap({"x": np.zeros(3), "y": np.zeros(3), "z": np.zeros(3)})
    with pytest.raises(ValueError, match="cell"):
        DL.road_surface_heightmap(road, 0.0)
    with pytest.raises(ValueError, match="cells"):
        DL.road_surface_heightmap(road, 1e-3, margin=100.0)


def test_docstring_call_example_runs():
    import textwrap
    code = DL.road_surface_heightmap.__doc__.split("呼び出し例::")[1]
    exec(compile(textwrap.dedent(code), "<road_surface_heightmap example>", "exec"), {})
