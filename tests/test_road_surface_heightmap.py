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
9. 独立レビューの指摘で足した門: 任意の列(heading・curvature・grade・s)の単位・符号の誤りと、% のつもりの
   crossfall・rate を断る(正しい線形は通す)。既定の extent の車道の外(側溝・路側の段)と線形の端の外を閉形式で、
   折線の射影へ退避するセルを含む全セルで真値の grade を高さ図の勾配(δ = 1e-6 m の中心差分)で突き合わせる。
   距離標の起点(s が 1000 から)で面が変わらない。
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
# ---- 独立レビューの指摘で足した門(2026-11-15) -------------------------------------------------------
def _straight(n=81, step=0.5, g=0.06):
    s = np.arange(n) * step
    return {"x": s, "y": np.zeros_like(s), "z": g * s, "s": s}


def _arc_cols(R=30.0, L=50.0, step=1.0):
    ss = np.arange(0.0, L + 1e-9, step)
    cp = DL.clothoid_points(L, ss, kappa0=1.0 / R, kappa1=1.0 / R)
    return {"x": cp["points"][:, 0], "y": cp["points"][:, 1], "z": 0.05 * ss, "s": ss, "heading": cp["heading"],
            "curvature": cp["curvature"], "grade": np.full_like(ss, 0.05)}


@pytest.mark.parametrize("name,make,col", [
    ("heading in degrees (360 for 0 rad)", lambda: dict(_straight(), heading=np.full(81, 360.0)), "heading"),
    ("heading reversed (the xy go +x)", lambda: dict(_straight(), heading=np.full(81, math.pi)), "heading"),
    ("heading in degrees on an arc", lambda: dict(_arc_cols(), heading=np.degrees(_arc_cols()["heading"])), "heading"),
    ("curvature with the wrong sign", lambda: dict(_arc_cols(), curvature=-_arc_cols()["curvature"]), "curvature"),
    ("curvature in 1/km", lambda: dict(_arc_cols(), curvature=1000.0 * _arc_cols()["curvature"]), "curvature"),
    ("grade in percent", lambda: dict(_arc_cols(), grade=np.full(51, 5.0)), "grade"),
    ("grade with the wrong sign", lambda: dict(_arc_cols(), grade=np.full(51, -0.05)), "grade"),
    ("s in km", lambda: dict(_straight(), s=_straight()["s"] / 1000.0), "s"),
])
def test_optional_columns_that_disagree_with_the_polyline_are_refused(name, make, col):
    """指摘 1: 任意の列(heading / curvature / grade / s)は xy・z の折線と突き合わせ、単位・符号の誤りは断る。

    直す前は黙って通り、高さ図と真値が揃って cm ずれた(heading 360 で z が 3.3 cm、曲率の符号で 4.0 cm)。"""
    with pytest.raises(ValueError, match="alignment %s" % col):
        DL.road_surface_heightmap(make(), 0.1, extent=(-2.0, 40.0, -3.0, 30.0))


def test_consistent_columns_still_pass():
    """断る門が正しい線形を断らない: 2π ずれの向き、直線 → 円弧の継ぎ目(曲率が標本で跳ぶ)、クロソイド、距離標の起点。"""
    s = _straight()
    DL.road_surface_heightmap(dict(s, heading=np.full(81, 2.0 * math.pi)), 0.1, extent=(5.0, 35.0, -3.0, 3.0))
    DL.road_surface_heightmap(_arc_cols(), 0.1, extent=(-2.0, 30.0, -2.0, 30.0))
    a = DL.clothoid_points(20.0, np.arange(0.0, 20.01, 0.5))
    b = DL.clothoid_points(20.0, np.arange(0.5, 20.01, 0.5), kappa0=0.04, kappa1=0.04, start=(20.0, 0.0))
    ss = np.r_[np.arange(0.0, 20.01, 0.5), 20.0 + np.arange(0.5, 20.01, 0.5)]
    joint = {"x": np.r_[a["points"][:, 0], b["points"][:, 0]], "y": np.r_[a["points"][:, 1], b["points"][:, 1]],
             "z": 0.05 * ss, "s": ss + 1000.0, "heading": np.r_[a["heading"], b["heading"]],
             "curvature": np.r_[a["curvature"], b["curvature"]], "grade": np.full_like(ss, 0.05)}
    DL.road_surface_heightmap(joint, 0.25)
    sc = np.arange(0.0, 60.01, 1.0)
    cl = DL.clothoid_points(60.0, sc, kappa0=0.0, kappa1=1.0 / 25.0)          # 緩和曲線(曲率が一次で増える)
    DL.road_surface_heightmap({"x": cl["points"][:, 0], "y": cl["points"][:, 1], "z": 0.0 * sc, "s": sc,
                               "heading": cl["heading"], "curvature": cl["curvature"]}, 0.25)


@pytest.mark.parametrize("kw", [{"crossfall": 2.0}, {"crossfall": -0.25}, {"rate": 6.0}, {"rate": -0.3}])
def test_cross_slopes_are_in_m_per_m_and_bounded(kw):
    """指摘 1: crossfall・rate は m/m。% のつもりの 2 を通すと勾配 2 m/m の面が返っていた。|値| > 0.2 は断る。"""
    road = _straight()
    if "rate" in kw:
        road = dict(road, beta=np.ones(81), rate=np.full(81, kw["rate"]))
        kw = {}
    with pytest.raises(ValueError, match="crossfall|rate"):
        DL.road_surface_heightmap(road, 0.1, extent=(5.0, 35.0, -3.0, 3.0), **kw)
    DL.road_surface_heightmap(_straight(), 0.1, extent=(5.0, 35.0, -3.0, 3.0), crossfall=0.2)   # 上限ちょうどは通す


@pytest.mark.parametrize("curvature", [0.05, 1000.0])
def test_two_sample_curvature_must_agree_with_the_heading_integral(curvature):
    """1 区間でも heading 差 = ∫κ ds。直線の両端 heading と非零曲率を黙って面に使わない。"""
    road = {"x": [0.0, 10.0], "y": [0.0, 0.0], "z": [0.0, 1.0], "s": [0.0, 10.0],
            "heading": [0.0, 0.0], "curvature": [curvature, curvature], "grade": [0.1, 0.1]}
    with pytest.raises(ValueError, match="curvature.*heading"):
        DL.road_surface_heightmap(road, 1.0)


def test_two_sample_nonzero_curvature_without_heading_is_refused():
    """2 標本だけでは曲率を折線から照合できないため、非零曲率を heading なしでは受け取らない。"""
    road = {"x": [0.0, 10.0], "y": [0.0, 0.0], "z": [0.0, 1.0], "s": [0.0, 10.0],
            "curvature": [0.05, 0.05], "grade": [0.1, 0.1]}
    with pytest.raises(ValueError, match="curvature.*heading"):
        DL.road_surface_heightmap(road, 1.0)


def test_two_sample_circular_arc_curvature_agrees_with_heading_integral():
    """1 区間でも、解析的な円弧の端点・heading・曲率が一致する入力は拒否しない。"""
    curvature, length = 0.05, 10.0
    angle = curvature * length
    road = {"x": [0.0, np.sin(angle) / curvature], "y": [0.0, (1.0 - np.cos(angle)) / curvature],
            "z": [0.0, 1.0], "s": [0.0, length], "heading": [0.0, angle],
            "curvature": [curvature, curvature], "grade": [0.1, 0.1]}
    H = DL.road_surface_heightmap(road, 1.0)
    assert H.size > 0 and np.all(np.isfinite(H))


def _section(y, cs, beta=0.0, rate=0.0):
    """横断の閉形式 p(y)・∂p/∂y(直線の道で e = y)。車道の外は縁の高さから側溝の半正弦、その外は路側の段。"""
    edge = cs["half_width"] + cs["shoulder"]
    yc = np.clip(y, -edge, edge)
    p = (1 - beta) * (-cs["crossfall"] * np.abs(yc)) + beta * (-rate * yc)
    dp = np.where(np.abs(y) <= edge, (1 - beta) * (-cs["crossfall"] * np.sign(y)) - beta * rate, 0.0)
    u = (np.abs(y) - edge) / cs["gutter_width"]
    gut = (u > 0) & (u <= 1)
    p = p - np.where(gut, cs["gutter_depth"] * np.sin(np.pi * np.clip(u, 0, 1)), 0.0) - np.where(u > 1, cs["verge_drop"], 0.0)
    dp = np.where(gut, -cs["gutter_depth"] * np.pi / cs["gutter_width"] * np.cos(np.pi * u) * np.sign(y), dp)
    return p, dp


@pytest.mark.parametrize("beta,rate", [(0.0, 0.0), (1.0, 0.05)])
def test_default_grid_outside_the_carriageway_and_beyond_the_ends_matches_the_closed_form(beta, rate):
    """指摘 2: 既定の extent(端の外 margin 10 m・側溝・路側を含む)の全セルを閉形式で突き合わせる。

    縦断は放物線の縦断曲線(g1 → g2)で、端の外は端の高さと勾配の直線(z = z_end + g_end·u)。横断は車道の外で
    縁の高さのまま、側溝 −gutter_depth·sin(π·u)、その外 −verge_drop。真値の grade は端の外で g1 / g2。
    側溝の符号・路側の段・端の外の縦断と勾配を壊した写しは、直す前の 13 本を全部すり抜けていた。"""
    g1, g2, L = 0.02, 0.08, 40.0
    s = np.arange(0.0, L + 1e-9, 2.0)
    road = {"x": s, "y": np.zeros_like(s), "z": g1 * s + (g2 - g1) * s ** 2 / (2 * L), "s": s,
            "beta": np.full_like(s, beta), "rate": np.full_like(s, rate)}
    H, T = DL.road_surface_heightmap(road, 0.1, return_truth=True)
    X, Y = _centres(H, T)
    assert X.min() < -9.0 and X.max() > L + 9.0 and np.abs(Y).max() > 9.0      # 既定の extent = 端の外と路側まで
    zc = np.where(X < 0, g1 * X, np.where(X > L, g1 * L + (g2 - g1) * L / 2 + g2 * (X - L),
                                          g1 * X + (g2 - g1) * X ** 2 / (2 * L)))
    gc = np.where(X < 0, g1, np.where(X > L, g2, g1 + (g2 - g1) * X / L))
    p, dp = _section(Y, T["cross_section"], beta, rate)
    assert np.abs(H - (zc + p)).max() < 1e-12
    assert np.abs(T["grade"] - gc).max() < 1e-12
    edge = T["cross_section"]["half_width"] + T["cross_section"]["shoulder"]
    smooth = np.abs(np.abs(Y) - edge - T["cross_section"]["gutter_width"]) > 0.06   # 側溝の外縁の段の上は除く
    assert np.abs(T["cross"] - dp)[smooth & (np.abs(Y) > 0.06)].max() < 1e-12
    gut = (np.abs(Y) > edge) & (np.abs(Y) < edge + T["cross_section"]["gutter_width"])
    verge = np.abs(Y) > edge + T["cross_section"]["gutter_width"]
    assert gut.sum() > 1000 and verge.sum() > 10000 and ((X < 0) | (X > L)).sum() > 20000
    assert not T["carriageway"][(X < 0) | (X > L) | (np.abs(Y) > edge)].any()


def _hairpin(R, exact):
    L = math.pi * R
    ss = np.arange(0.0, L + 1e-9, 1.0)
    cp = DL.clothoid_points(L, ss, kappa0=1.0 / R, kappa1=1.0 / R)
    road = {"x": cp["points"][:, 0], "y": cp["points"][:, 1], "z": 0.06 * ss, "s": ss}
    if exact:
        road.update(heading=cp["heading"], curvature=cp["curvature"])
    return road


def _spiral_hairpin(R=10.0, Ls=12.0, step=1.0):
    """緩和曲線(曲率 0 → 1/R、長さ Ls)・円弧・緩和曲線(1/R → 0)で向きが π 回るヘアピン。heading / curvature は
    clothoid_points の解析の値(厳密な列)。曲率が変わる所では隣り合う局所の円弧の法線の間に楔が残る。"""
    La = (math.pi - Ls / R) * R
    total = 2 * Ls + La
    s_all = np.r_[np.arange(0.0, total - 1e-9, step), total]
    P, th, kap = np.empty((len(s_all), 2)), np.empty(len(s_all)), np.empty(len(s_all))
    a, p0, h0 = 0.0, np.zeros(2), 0.0
    for L, k0, k1 in ((Ls, 0.0, 1.0 / R), (La, 1.0 / R, 1.0 / R), (Ls, 1.0 / R, 0.0)):
        m = (s_all >= a - 1e-9) & (s_all <= a + L + 1e-9)
        cp = DL.clothoid_points(L, np.clip(s_all[m] - a, 0.0, L), kappa0=k0, kappa1=k1, start=p0, heading0=h0)
        P[m], th[m], kap[m] = cp["points"], cp["heading"], cp["curvature"]
        end = DL.clothoid_points(L, [L], kappa0=k0, kappa1=k1, start=p0, heading0=h0)
        p0, h0, a = end["points"][0], float(end["heading"][0]), a + L
    return {"x": P[:, 0], "y": P[:, 1], "z": 0.06 * s_all, "s": s_all, "heading": th, "curvature": kap}


def _tiny_step_grade(road, cell=0.1, delta=1e-6):
    """高さ図そのものの勾配を、δ = 1e-6 m だけずらした格子 4 枚の中心差分で取り、真値の向きへ射影する。"""
    H, T = DL.road_surface_heightmap(road, cell, return_truth=True)
    e, (ny, nx) = T["extent"], H.shape
    z = {k: DL.road_surface_heightmap(road, cell, extent=(e[0] + dx, e[0] + dx + (nx - 0.5) * cell,
                                                          e[2] + dy, e[2] + dy + (ny - 0.5) * cell))
         for k, (dx, dy) in {"xp": (delta, 0), "xm": (-delta, 0), "yp": (0, delta), "ym": (0, -delta)}.items()}
    gx, gy = (z["xp"] - z["xm"]) / (2 * delta), (z["yp"] - z["ym"]) / (2 * delta)
    return H, T, gx * np.cos(T["heading"]) + gy * np.sin(T["heading"])


@pytest.mark.parametrize("layout", ["spiral hairpin (exact columns)", "hairpin R 6 m (estimated columns)"])
def test_truth_grade_is_the_derivative_of_the_heights_on_the_whole_default_grid(layout):
    """指摘 2: 局所の円弧が区間に収まらず折線の射影へ退避するセル(far)を含め、既定の格子の全セルで真値の grade が
    高さ図の勾配(δ = 1e-6 m の中心差分)に一致する。

    緩和曲線のヘアピンでは、曲率が変わる所の曲がりの外側に、どの局所の円弧にも足が落ちない楔が残り、そこが退避に
    入る(曲率 0 を「使った曲率」として返す)。直す前は退避したセルの s が区間の端に張り付き(勾配 0)、真値の grade
    (g)と食い違った(この配置で 89 セル)。"""
    road = _spiral_hairpin() if layout.startswith("spiral") else _hairpin(6.0, False)
    H, T, num = _tiny_step_grade(road)
    ok = np.isfinite(T["grade"])
    rel = np.abs(num - T["grade"]) / np.maximum(1.0, np.abs(T["grade"]))
    near_axis = np.abs(1.0 - T["curvature"] * T["e"]) < 0.05                # 曲率の中心のごく近く(勾配が発散)
    assert ok.sum() > 50000
    if layout.startswith("spiral"):
        inner = (T["s"] > road["s"][1]) & (T["s"] < road["s"][-2])
        assert int((inner & (T["curvature"] == 0.0)).sum()) > 100            # 退避に入るセルがある(曲率 0 の直線扱い)
    assert int((ok & ~near_axis & (rel > 1e-5)).sum()) == 0, float(np.max(rel[ok & ~near_axis]))


def test_chainage_offset_does_not_change_the_surface():
    """距離標の起点(s が 0 から始まらない)で高さ図と真値は変わらない(s が 1000 ずれるだけ)。

    直す前は折線の射影へ退避するセルが lateral_offset の s(0 から数えた弦の長さ)と線形の s を混ぜ、起点 1000 の
    ヘアピンで車道のセルを含む 110 セルの s が最大 1 m・高さが最大 6 cm ずれた。"""
    road = _hairpin(12.0, False)
    H0, T0 = DL.road_surface_heightmap(road, 0.1, return_truth=True)
    H1, T1 = DL.road_surface_heightmap(dict(road, s=road["s"] + 1000.0), 0.1, return_truth=True)
    assert np.abs(H1 - H0).max() < 1e-9
    assert np.abs((T1["s"] - 1000.0) - T0["s"]).max() < 1e-9
    assert np.array_equal(T1["carriageway"], T0["carriageway"])
