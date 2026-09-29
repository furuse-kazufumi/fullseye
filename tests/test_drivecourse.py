"""drivecourse(規格寸法の教習所コース)の門。

固定する性質:
- 靴紐面積が閉形式に一致(クランク = w·L + 2r²(1 − π/4)、S 字 = 2πf(R_o² − R_i²) + 2Ew、方向変換・交差点も
  すみ切りは「凹頂点を削るので面積が増える」側)、arc_pts を増やすと誤差が単調に減る
- 規格の値が params["regulation"] にそのまま入る(別表第三の記号 A〜E)
- entry から exit までの centerline が polygon の内側(端点を除く)
- 幅の門: 幅 3.5 の道で中心線から法線 ±1.8 は外、±1.7 は内(クランクは角のすみ切り圏を除く)
- 第 2 実装: 偶奇規則と回転数が凸でない多角形で乱数 5,000 点すべて一致
- 占有格子の True 率が 1 − 面積/格子面積 に cell → 0 で収束(誤差は周長 × cell で抑えられる)、row 0 = ymin
- 配置は剛体(面積・周長が不変、姿勢は yaw が回る、坂道の profile は動かない)
- fail-closed: 幅 ≤ 0、弧の比 ∉ (0, 1)、cell ≤ 0、形の悪い配置は ValueError
"""
import math

import numpy as np
import pytest

import drivecourse as D

ALL_ELEMENTS = (D.course_crank, D.course_s_curve, D.course_turnaround, D.course_slope, D.course_intersection,
                D.course_parallel_parking, D.course_crossing)
CURVED = (D.course_crank, D.course_s_curve, D.course_turnaround, D.course_intersection)


def _perimeter(P):
    return float(np.sum(np.hypot(*(np.roll(P, -1, axis=0) - P).T)))


def _segment_midpoints_and_normals(pts):
    """折線の各区間の中点と左法線。"""
    P = np.asarray(pts, float)
    d = P[1:] - P[:-1]
    L = np.hypot(d[:, 0], d[:, 1])
    keep = L > 1e-12
    d, P0, P1 = d[keep], P[:-1][keep], P[1:][keep]
    t = d / L[keep][:, None]
    return 0.5 * (P0 + P1), np.stack([-t[:, 1], t[:, 0]], axis=1)


def _six_layout():
    els = [D.course_crank(), D.course_s_curve(), D.course_turnaround(), D.course_slope(), D.course_intersection(),
           D.course_crossing()]
    plc = [(0.0, 0.0, 0.0), (30.0, 0.0, 0.3), (60.0, 10.0, 1.2), (0.0, 40.0, -0.4), (50.0, 50.0, 0.7),
           (90.0, 30.0, 2.0)]
    return D.course_layout(els, plc)


# ---- 面積: 閉形式と収束 -------------------------------------------------------------------------------
@pytest.mark.parametrize("make", ALL_ELEMENTS)
def test_area_matches_closed_form(make):
    e = make()
    a = D.polygon_area(e["polygon"])
    assert a > 0                                    # 反時計回り
    # 既定の arc_pts での折線誤差: 弦 1 本あたり (R²/2)(α − sin α) ≈ R²α³/12。S 字(α = 135°/48)で
    # (R_o² − R_i²)·48·α³/12 ≈ 0.038 m²(相対 3e-4)、クランク(α = 90°/16)で 2·r²·16·α³/12 ≈ 2.5e-3 m²
    assert abs(a - e["area_closed_form"]) <= 5e-4 * e["area_closed_form"]
    if make in CURVED:
        fine = make(arc_pts=1024)
        assert abs(D.polygon_area(fine["polygon"]) - fine["area_closed_form"]) <= 1e-6 * fine["area_closed_form"]
    else:
        assert abs(a - e["area_closed_form"]) <= 1e-9 * e["area_closed_form"]


def test_closed_forms_are_the_derived_expressions():
    w, B, C, r = 3.5, 12.0, 4.0, 1.0
    # 図の測り方: C は帯の壁から出入口まで → 中心線の直線部は C + w/2、L = 2C + w + B
    assert D.course_crank()["area_closed_form"] == pytest.approx(w * (2 * C + w + B) + 2 * r * r * (1 - math.pi / 4))
    assert D.course_crank()["centerline_length"] == pytest.approx(2 * C + w + B)
    Ro, Ri, E = 7.5, 4.0, 4.0
    assert D.course_s_curve()["area_closed_form"] == pytest.approx(2 * (3 / 8) * math.pi * (Ro ** 2 - Ri ** 2) + 2 * E * w)
    assert D.course_turnaround()["area_closed_form"] == pytest.approx((2 * 5.0 + 3.5) * 3.5 + 5.0 * 3.5 + 2 * (1 - math.pi / 4))
    assert D.course_slope()["area_closed_form"] == pytest.approx(7.0 * (1.5 / 0.08 + 4.0 + 1.5 / 0.11))
    assert D.course_intersection()["area_closed_form"] == pytest.approx(2 * (40 + 7) * 7 - 49 + 4 * 9 * (1 - math.pi / 4))
    assert D.course_parallel_parking()["area_closed_form"] == pytest.approx((10 + 7.5) * 7.0 + 7.5 * 1.8)
    assert D.course_crossing()["area_closed_form"] == pytest.approx(7.0 * (2 * (0.75 + 0.55) + 12.0))


@pytest.mark.parametrize("make", CURVED)
def test_area_error_decreases_monotonically_with_arc_pts(make):
    errs = []
    for n in (2, 4, 8, 16, 32, 64, 128):
        e = make(arc_pts=n)
        errs.append(abs(D.polygon_area(e["polygon"]) - e["area_closed_form"]))
    assert all(b < a for a, b in zip(errs, errs[1:])), errs
    assert errs[-1] < 1e-3 * make()["area_closed_form"]
    # 符号の向き: すみ切り(円に内接する折線)は面積が閉形式より大きく、環状扇形は小さい側から収束
    e = make(arc_pts=8)
    sign = D.polygon_area(e["polygon"]) - e["area_closed_form"]
    assert (sign < 0) if make is D.course_s_curve else (sign > 0)


# ---- 規格の値 ------------------------------------------------------------------------------------------
def test_regulation_values_are_in_params():
    assert D.course_crank()["params"]["regulation"] == {"A": 3.5, "B": 12.0, "C": 4.0, "D": 1.0}
    assert D.course_s_curve()["params"]["regulation"] == {"A": 3.5, "B": 7.5, "C": 3 / 8}
    assert D.course_s_curve()["params"]["radius_inner"] == pytest.approx(4.0)
    assert D.course_s_curve()["params"]["arc_angle"] == pytest.approx(math.radians(135))
    assert D.course_turnaround()["params"]["regulation"] == {"A": 3.5, "B": 3.5, "C": 5.0, "D": 5.0, "E": 1.0}
    s = D.course_slope()["params"]
    assert s["regulation"]["width_min"] == 7.0 and s["regulation"]["height_min"] == 1.5
    assert s["regulation"]["gentle_range"] == (0.065, 0.09) and s["regulation"]["steep_range"] == (0.10, 0.125)
    assert s["regulation"]["top_min"] == 4.0
    assert s["regulation"]["gentle_range"][0] <= s["grade_gentle"] <= s["regulation"]["gentle_range"][1]
    assert s["regulation"]["steep_range"][0] <= s["grade_steep"] <= s["regulation"]["steep_range"][1]
    assert D.course_intersection()["params"]["regulation"] == {"width_min": 7.0, "corner_radius_min": 3.0, "stop_setback_std": 2.0, "crosswalk_min": 4.0}
    assert D.course_crossing()["params"]["regulation"] == {"gauge": 1.1, "rail_outer": 0.75}
    pp = D.course_parallel_parking()["params"]
    assert pp["bay_length"] == 7.5 and "法令に数値なし" in pp["regulation"]["note"]
    for make in ALL_ELEMENTS:
        e = make()
        assert e["width"] == e["params"]["width"] if "width" in e["params"] else e["params"]["road_width"]


# ---- 中心線と幅の門 ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("make", ALL_ELEMENTS)
def test_centerline_is_inside_polygon(make):
    e = make()
    pts = D._resample_polyline(e["centerline"], 0.1)[1:-1]
    assert len(pts) > 10
    assert np.all(D.course_contains(e, pts))
    assert np.allclose(e["centerline"][0], e["entry"][:2]) or e["kind"] == "turnaround"
    # entry / exit の位置は多角形の境界上(わずかに内側へ寄せると内、外へ寄せると外)
    for pose in (e["entry"], e["exit"]):
        c, s = math.cos(pose[2]), math.sin(pose[2])
        fwd = np.array([pose[0] + 0.05 * c, pose[1] + 0.05 * s])
        back = np.array([pose[0] - 0.05 * c, pose[1] - 0.05 * s])
        assert D.course_contains(e, fwd) != D.course_contains(e, back)


def test_width_gate_3p5_road_rejects_3p6_body():
    half_out, half_in = 1.8, 1.7
    # クランク: 角のすみ切り圏(w/2 + r)の外では法線 ±1.8 は外、±1.7 は内
    e = D.course_crank()
    mid, nrm = _segment_midpoints_and_normals(D._resample_polyline(e["centerline"], 0.05))
    corners = e["corners"]
    assert np.allclose(corners, [[5.75, 0.0], [5.75, 12.0]])
    far = np.min(np.hypot(*(mid[:, None, :] - corners[None]).transpose(2, 0, 1)), axis=1) > 1.75 + 1.0 + 0.05
    assert far.sum() > 100
    for sgn in (+1, -1):
        assert not np.any(D.course_contains(e, mid[far] + sgn * half_out * nrm[far]))
        assert np.all(D.course_contains(e, mid[far] + sgn * half_in * nrm[far]))
    # 角の圏内には 3.6 幅が入る場所がある(L 字の角は広い)—— 門を角で緩めた理由の記録
    assert np.any(D.course_contains(e, mid[~far] + half_out * nrm[~far]))
    # S 字: 全区間(弧の弦の中点は R_c(1 − cos(α/2)) ≈ 2 mm 内側に寄るが門の余裕 5 cm に収まる)
    e = D.course_s_curve()
    mid, nrm = _segment_midpoints_and_normals(e["centerline"])
    for sgn in (+1, -1):
        assert not np.any(D.course_contains(e, mid + sgn * half_out * nrm))
        assert np.all(D.course_contains(e, mid + sgn * half_in * nrm))
    # 方向変換: 道路の軸、右側(車庫の無い側)は全区間、左側は車庫口の圏外
    e = D.course_turnaround()
    xb0, xb1 = e["bay"][0], e["bay"][1]
    road = D._resample_polyline(e["centerline"][:2], 0.05)
    mid, nrm = _segment_midpoints_and_normals(road)
    assert not np.any(D.course_contains(e, mid - half_out * nrm))
    assert np.all(D.course_contains(e, mid - half_in * nrm))
    away = (mid[:, 0] < xb0 - 1.0 - 0.05) | (mid[:, 0] > xb1 + 1.0 + 0.05)
    assert away.sum() > 50
    assert not np.any(D.course_contains(e, mid[away] + half_out * nrm[away]))
    assert np.all(D.course_contains(e, mid[away] + half_in * nrm[away]))


# ---- 第 2 実装: 偶奇 vs 回転数 ----------------------------------------------------------------------------
@pytest.mark.parametrize("make", (D.course_crank, D.course_s_curve, D.course_intersection, D.course_turnaround))
def test_even_odd_agrees_with_winding_number(make):
    e = make()
    rng = np.random.default_rng(14)
    x0, x1, y0, y1 = e["bounds"]
    pts = np.column_stack([rng.uniform(x0 - 1, x1 + 1, 5000), rng.uniform(y0 - 1, y1 + 1, 5000)])
    eo = D._contains_even_odd(e["polygon"], pts)
    wn = D._contains_winding(e["polygon"], pts)
    assert eo.shape == (5000,) and np.array_equal(eo, wn)
    assert 0.05 < eo.mean() < 0.95                 # 内も外も両方踏んでいる
    frac = eo.mean() * (x1 - x0 + 2) * (y1 - y0 + 2)
    assert abs(frac - e["area_closed_form"]) < 0.1 * e["area_closed_form"]   # Monte Carlo の粗い一致
    assert np.array_equal(D.course_contains(e, pts), eo)


def test_even_odd_agrees_with_winding_on_rotated_layout():
    lay = _six_layout()
    rng = np.random.default_rng(7)
    x0, x1, y0, y1 = lay["bounds"]
    pts = np.column_stack([rng.uniform(x0, x1, 5000), rng.uniform(y0, y1, 5000)])
    ref = np.zeros(5000, bool)
    for el in lay["elements"]:
        ref |= D._contains_winding(el["polygon"], pts)
    assert np.array_equal(D.course_contains(lay, pts), ref)


# ---- 占有格子 ----------------------------------------------------------------------------------------------
def test_occupancy_row0_is_ymin_and_outside_is_true():
    e = D.course_crank()
    occ, (xmin, xmax, ymin, ymax) = D.course_occupancy(e, cell=0.25, margin=2.0)
    assert occ.dtype == bool and occ.ndim == 2
    assert xmin == pytest.approx(-2.0) and ymin == pytest.approx(-1.75 - 2.0)
    assert xmax == pytest.approx(xmin + occ.shape[1] * 0.25) and ymax == pytest.approx(ymin + occ.shape[0] * 0.25)

    def cell_of(x, y):
        return int((y - ymin) / 0.25), int((x - xmin) / 0.25)

    assert not occ[cell_of(1.0, 0.0)]              # 進入路の中は走れる
    assert occ[cell_of(1.0, 5.0)]                   # 進入路の脇のブロック
    assert occ[0, 0] and occ[-1, -1]                # margin の縁は障害物
    assert not occ[cell_of(5.75, 6.0)]              # 曲角間の帯(x ∈ [4, 7.5])
    assert occ[cell_of(3.0, 6.0)] and occ[cell_of(8.5, 6.0)]
    assert not occ[cell_of(10.0, 12.0)]             # 退出路(x ∈ [7.5, 11.5])
    assert occ[cell_of(3.0, 12.0)]                  # 退出路の裏側は走れない(Z の外)


def test_occupancy_fraction_converges_to_one_minus_area_ratio():
    lay = _six_layout()
    area = lay["area_closed_form_sum"]
    perim = sum(_perimeter(el["polygon"]) for el in lay["elements"])
    errs, bounds = [], []
    for cell in (0.5, 0.25, 0.125):
        occ, (x0, x1, y0, y1) = D.course_occupancy(lay, cell=cell, margin=2.0)
        grid_area = (x1 - x0) * (y1 - y0)
        assert grid_area == pytest.approx(occ.size * cell * cell)
        errs.append(abs(occ.mean() - (1 - area / grid_area)))
        bounds.append(perim * cell / grid_area)     # 境界帯(周長 × cell)より誤差は小さい
    assert all(e < b for e, b in zip(errs, bounds)), (errs, bounds)
    assert errs[-1] < errs[0] and errs[1] < errs[0]
    # 要素が重ならない配置なので面積の和が真値: 最細の格子で相対 1e-3 以内
    assert errs[-1] < 1e-3


def test_occupancy_of_single_element_equals_layout_of_one():
    e = D.course_s_curve()
    lay = D.course_layout([e], [(0.0, 0.0, 0.0)])
    o1, x1 = D.course_occupancy(e, cell=0.25)
    o2, x2 = D.course_occupancy(lay, cell=0.25)
    assert np.array_equal(o1, o2) and x1 == pytest.approx(x2)


# ---- 配置(剛体) ------------------------------------------------------------------------------------------
def test_layout_is_rigid_and_transforms_poses():
    els = [D.course_intersection(), D.course_slope(), D.course_crossing()]
    plc = [(10.0, -5.0, 0.9), (-20.0, 3.0, -2.5), (0.0, 30.0, 3.0)]
    lay = D.course_layout(els, plc)
    assert lay["kind"] == "layout" and lay["polygon"] is None and len(lay["elements"]) == 3
    for e, t, (x, y, yaw) in zip(els, lay["elements"], plc):
        assert D.polygon_area(t["polygon"]) == pytest.approx(D.polygon_area(e["polygon"]))
        assert _perimeter(t["polygon"]) == pytest.approx(_perimeter(e["polygon"]))
        assert t["placement"] == (x, y, yaw)
        c, s = math.cos(yaw), math.sin(yaw)
        ex, ey, eyaw = e["entry"]
        assert t["entry"][0] == pytest.approx(c * ex - s * ey + x)
        assert t["entry"][1] == pytest.approx(s * ex + c * ey + y)
        assert math.cos(t["entry"][2] - (eyaw + yaw)) == pytest.approx(1.0)
        assert -math.pi < t["entry"][2] <= math.pi
        assert np.all(D.course_contains(t, D._resample_polyline(t["centerline"], 0.1)[1:-1]))
        assert t["bounds"][0] == pytest.approx(t["polygon"][:, 0].min())
    it = lay["elements"][0]
    assert it["signal_poses"].shape == (4, 3) and it["stop_lines"].shape == (4, 2, 2)
    for k in range(4):
        assert math.cos(it["signal_poses"][k, 2] - (els[0]["signal_poses"][k, 2] + plc[0][2])) == pytest.approx(1.0)
    sl = lay["elements"][1]
    assert np.array_equal(sl["profile"], els[1]["profile"])          # (s, z) は動かない
    cr = lay["elements"][2]
    assert cr["rails"].shape == (2, 2, 2)
    assert np.hypot(*(cr["rails"][0, 1] - cr["rails"][0, 0])) == pytest.approx(7.0)
    bx = lay["bounds"]
    assert bx[0] == pytest.approx(min(t["bounds"][0] for t in lay["elements"]))
    assert bx[3] == pytest.approx(max(t["bounds"][3] for t in lay["elements"]))
    # 変換前の要素は触られていない
    assert els[0]["entry"] == (-23.5, 0.0, 0.0)


def test_layout_contains_is_union():
    a, b = D.course_crank(), D.course_crossing()
    lay = D.course_layout([a, b], [(0.0, 0.0, 0.0), (40.0, 0.0, 0.0)])
    pts = np.array([[1.0, 0.0], [45.0, 0.0], [25.0, 0.0], [1.0, 5.0]])
    assert np.array_equal(D.course_contains(lay, pts), [True, True, False, False])
    assert D.course_contains(lay, [1.0, 0.0]) and not D.course_contains(lay, [25.0, 0.0])


# ---- 個別要素のメタデータ --------------------------------------------------------------------------------
def test_intersection_signals_and_stop_lines():
    e = D.course_intersection()
    sig, stop = e["signal_poses"], e["stop_lines"]
    assert sig.shape == (4, 3) and stop.shape == (4, 2, 2)
    assert not np.any(D.course_contains(e, sig[:, :2]))          # 信号柱は路外
    assert np.all(D.course_contains(e, stop.mean(axis=1)))        # 停止線は路上
    # 東行(yaw 0)流入路: 横断歩道はすみ切りの終わり(6.5)から幅 4、停止線はその 2 m 手前 x = −12.5 で左半分 y ∈ [0, 3.5]、
    # 信号は交差点の向こう側(出口側の横断歩道の外 x = +11.0)の左の角で西向き(対面)
    assert e["crosswalks"].shape == (4, 2, 2) and e["crosswalk_width"] == 4.0
    assert np.allclose(e["crosswalks"][0], [[-8.5, -3.5], [-8.5, 3.5]])
    assert np.allclose(stop[0], [[-12.5, 0.0], [-12.5, 3.5]])
    assert np.allclose(sig[0], [11.0, 4.0, math.pi])
    assert np.all(D.course_contains(e, e["crosswalks"].mean(axis=1)))     # 横断歩道は路上
    for k in range(4):
        assert math.cos(sig[k, 2] - (k * math.pi / 2 + math.pi)) == pytest.approx(1.0)
    # 4 方向対称: 停止線の中点は原点から等距離
    d = np.hypot(*stop.mean(axis=1).T)
    assert np.allclose(d, d[0])


def test_crossing_rails_and_zone():
    e = D.course_crossing()
    r, (z0, z1) = e["rails"], e["crossing_zone"]
    assert r.shape == (2, 2, 2)
    assert r[1, 0, 0] - r[0, 0, 0] == pytest.approx(1.1)          # 軌間
    assert z1 - z0 == pytest.approx(1.1 + 2 * 0.75)               # 踏切面
    assert z0 < r[0, 0, 0] < r[1, 0, 0] < z1
    assert np.all(D.course_contains(e, r.mean(axis=1)))
    assert e["params"]["length"] == pytest.approx(14.6)
    assert e["stop_lines"][0, 0, 0] == pytest.approx(z0 - 0.5)       # 踏切の手前の側端から 0.5 m 手前(運転免許技能試験実施基準)


def test_slope_profile_and_height():
    e = D.course_slope()
    pr = e["profile"]
    assert pr.shape == (4, 2) and pr[0, 1] == 0 and pr[-1, 1] == 0 and pr[1, 1] == pr[2, 1] == 1.5
    assert (pr[1, 1] - pr[0, 1]) / (pr[1, 0] - pr[0, 0]) == pytest.approx(0.08)
    assert (pr[2, 1] - pr[3, 1]) / (pr[3, 0] - pr[2, 0]) == pytest.approx(0.11)
    assert pr[2, 0] - pr[1, 0] == pytest.approx(4.0)
    assert e["params"]["length"] == pytest.approx(pr[-1, 0]) == pytest.approx(e["exit"][0])
    assert D.slope_height(e, [0.0, pr[1, 0] / 2, pr[1, 0], pr[2, 0], pr[-1, 0]]).tolist() == pytest.approx(
        [0.0, 0.75, 1.5, 1.5, 0.0])
    with pytest.raises(ValueError):
        D.slope_height(D.course_crank(), 1.0)
    with pytest.raises(ValueError):
        D.course_slope(grade_steep=1.5)


def test_parallel_parking_bay_side():
    left = D.course_parallel_parking()
    right = D.course_parallel_parking(side="right")
    x0, x1, y0, y1 = left["bay"]
    assert x1 - x0 == pytest.approx(7.5) and y0 == pytest.approx(3.5) and y1 == pytest.approx(5.3)
    assert D.course_contains(left, [0.5 * (x0 + x1), 4.4]) and not D.course_contains(right, [0.5 * (x0 + x1), 4.4])
    assert D.course_contains(right, [0.5 * (x0 + x1), -4.4])
    assert D.polygon_area(right["polygon"]) == pytest.approx(D.polygon_area(left["polygon"]))
    with pytest.raises(ValueError):
        D.course_parallel_parking(side="up")


def test_turnaround_bay_geometry():
    e = D.course_turnaround()
    x0, x1, y0, y1 = e["bay"]
    assert x1 - x0 == pytest.approx(3.5) and y1 - y0 == pytest.approx(5.0) and x0 == pytest.approx(5.0)
    assert D.course_contains(e, [0.5 * (x0 + x1), y1 - 0.1]) and not D.course_contains(e, [x0 - 0.1, y0 + 2.0])
    assert e["exit"] == (0.0, 0.0, math.pi)
    # すみ切り: 車庫口の角の外側の点(頂点から (−0.1, +0.1))はすみ切りで走れる、r = 0 なら走れない
    assert D.course_contains(e, [x0 - 0.1, y0 + 0.1])
    assert not D.course_contains(D.course_turnaround(corner_radius=0.0), [x0 - 0.1, y0 + 0.1])
    # 鏡映(図の向き = 道路の右側に車庫): 面積は同じ、車庫は −y
    rt = D.course_turnaround(side="right")
    assert D.polygon_area(rt["polygon"]) == pytest.approx(D.polygon_area(e["polygon"]))
    assert D.course_contains(rt, [0.5 * (x0 + x1), -(y1 - 0.1)]) and not D.course_contains(rt, [0.5 * (x0 + x1), y1 - 0.1])
    assert np.all(D.course_contains(rt, D._resample_polyline(rt["centerline"], 0.1)[1:-1]))
    with pytest.raises(ValueError):
        D.course_turnaround(side="both")


def test_deterministic_and_ccw():
    for make in ALL_ELEMENTS:
        a, b = make(), make()
        assert np.array_equal(a["polygon"], b["polygon"]) and np.array_equal(a["centerline"], b["centerline"])
        assert D.polygon_area(a["polygon"]) > 0
        assert a["polygon"].dtype == np.float64 and a["polygon"].shape[1] == 2
        assert not np.any(np.all(np.abs(np.diff(a["polygon"], axis=0)) < 1e-12, axis=1))   # 重複点なし


# ---- fail-closed ----------------------------------------------------------------------------------------------
def test_bad_arguments_raise():
    for make in ALL_ELEMENTS:
        with pytest.raises(ValueError):
            make(width=0.0) if make is not D.course_parallel_parking else make(road_width=0.0)
        with pytest.raises(ValueError):
            make(width=-3.5) if make is not D.course_parallel_parking else make(car_width=-1.0)
    for f in (0.0, 1.0, -0.2, 1.5, float("nan")):
        with pytest.raises(ValueError):
            D.course_s_curve(arc_fraction=f)
    with pytest.raises(ValueError):
        D.course_s_curve(radius_outer=3.0)                  # 内径 ≤ 0
    with pytest.raises(ValueError):
        D.course_crank(entry=0.5)                           # すみ切り(r = 1)が出入口にはみ出る
    with pytest.raises(ValueError):
        D.course_crank(between=4.0)                         # 2 つの角が重なる(B < w + r)
    with pytest.raises(ValueError):
        D.course_crank(arc_pts=0)
    with pytest.raises(ValueError):
        D.course_crank(arc_pts=2.5)
    with pytest.raises(ValueError):
        D.course_intersection(arm=1.0)
    e = D.course_crank()
    for cell in (0.0, -0.25, float("inf")):
        with pytest.raises(ValueError):
            D.course_occupancy(e, cell=cell)
    with pytest.raises(ValueError):
        D.course_occupancy(e, cell=0.25, margin=-1.0)
    with pytest.raises(ValueError):
        D.course_contains(e, [[0.0, 0.0, 0.0]])
    with pytest.raises(ValueError):
        D.course_contains(e, [[float("nan"), 0.0]])
    with pytest.raises(ValueError):
        D.course_contains({"kind": "crank"}, [[0.0, 0.0]])
    with pytest.raises(ValueError):
        D.polygon_area([[0.0, 0.0], [1.0, 0.0]])
    with pytest.raises(ValueError):
        D.course_layout([], [])
    with pytest.raises(ValueError):
        D.course_layout([e], [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)])
    with pytest.raises(ValueError):
        D.course_layout([e], [(0.0, float("nan"), 0.0)])
    with pytest.raises(ValueError):
        D.course_layout([e], [(0.0, 0.0)])
    lay = D.course_layout([e], [(0.0, 0.0, 0.0)])
    with pytest.raises(ValueError):
        D.course_layout([lay], [(0.0, 0.0, 0.0)])          # 入れ子の配置は非対応(黙って空にしない)
    with pytest.raises(ValueError):
        D.polygon_area(lay["polygon"])


# ---- 周回コースと連絡路(2026-09-29 追加) -------------------------------------------------------------
def test_loop_bend_area_converges_to_pi_R_w():
    errs = []
    for n in (8, 32, 128, 512):
        e = D.course_loop_bend(radius=30.0, width=8.0, arc_pts=n)
        errs.append(abs(D.polygon_area(e["polygon"]) - e["area_closed_form"]) / e["area_closed_form"])
    assert all(d < 0 for d in np.diff(errs)) and errs[-1] < 1e-5, errs
    assert abs(e["area_closed_form"] - math.pi * 30.0 * 8.0) < 1e-9
    assert np.allclose(e["exit"], (0.0, 60.0, math.pi))
    with pytest.raises(ValueError):
        D.course_loop_bend(radius=3.0, width=8.0)


def test_loop_is_a_closed_ring_and_the_road_is_exact():
    loop = D.course_loop(straight=80.0, radius=30.0, width=8.0)
    L = D.course_layout(loop["elements"], loop["placements"])
    assert len(L["elements"]) == 4
    assert D.course_contains(L, np.column_stack([np.linspace(-40, 40, 20), np.full(20, 30.0)])).all()
    assert D.course_contains(L, np.column_stack([np.linspace(-40, 40, 20), np.full(20, -30.0)])).all()
    th = np.linspace(-0.5 * math.pi, 0.5 * math.pi, 15)
    assert D.course_contains(L, np.column_stack([40.0 + 30.0 * np.cos(th), 30.0 * np.sin(th)])).all()
    assert not D.course_contains(L, np.array([[0.0, 0.0], [0.0, 20.0], [90.0, 0.0], [0.0, 40.0]])).any()
    for k in range(4):                                    # 出口が次の入口(反時計回りに閉じる; 直線は 0.05 m 食い込む)
        a = L["elements"][k]["exit"]
        b = L["elements"][(k + 1) % 4]["entry"]
        assert np.allclose(a[:2], b[:2], atol=0.05 + 1e-9) and abs(math.remainder(a[2] - b[2], 2 * math.pi)) < 1e-9
    loop0 = D.course_loop(straight=80.0, radius=30.0, width=8.0, overlap=0.0)
    L0 = D.course_layout(loop0["elements"], loop0["placements"])
    for k in range(4):                                    # 重なり 0 なら厳密に閉じる
        a = L0["elements"][k]["exit"]
        b = L0["elements"][(k + 1) % 4]["entry"]
        assert np.allclose(a[:2], b[:2], atol=1e-9)
    r = D.course_road(length=20.0, width=7.0)
    assert abs(D.polygon_area(r["polygon"]) - 140.0) < 1e-12 and r["area_closed_form"] == 140.0
    with pytest.raises(ValueError):
        D.course_road(length=0.0)
