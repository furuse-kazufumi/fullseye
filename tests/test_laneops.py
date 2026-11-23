"""Known-truth gates for the five classical lane/stop-line operators.

5本のopを、位置・距離が既知の合成道路、係数が既知の点列、投影の閉形式で検査する。
正常系だけでなく、線なし・片側・遮蔽・回転・点順変更も固定seedで通す。
"""
from __future__ import annotations

import textwrap

import numpy as np
import pytest

import laneops as LO
import pegsym


def _road_rgb(gamma=1.0, shadow=False):
    """白・黄の縦線、白い停止線/横断歩道、灰色路面の既知色画像。"""
    h, w = 240, 160
    rgb = np.full((h, w, 3), 0.20, np.float64)
    rgb[:, 35:40] = (0.92, 0.92, 0.92)       # white lane boundary
    rgb[:, 120:125] = (0.92, 0.76, 0.06)     # yellow lane boundary
    rgb[88:94, 42:118] = (0.90, 0.90, 0.90)  # stop line
    for row in (140, 152, 164, 176):          # crosswalk stripes
        rgb[row:row + 6, 42:118] = (0.90, 0.90, 0.90)
    if shadow:
        rgb[:, :80] *= 0.55
    return np.clip(rgb, 0.0, 1.0) ** float(gamma)


@pytest.mark.parametrize("gamma", [0.70, 1.0, 1.45])
@pytest.mark.parametrize("shadow", [False, True])
def test_color_rule_mask_known_colours_brightness_gamma_and_shadow(gamma, shadow):
    rgb = _road_rgb(gamma=gamma, shadow=shadow)
    got = LO.color_rule_mask(rgb, {})
    # 真値の中心画素を直接読む。背景を線として数えないことも絶対値で見る。
    assert got["labels"][30, 37] == LO.WHITE_LABEL
    assert got["labels"][30, 122] == LO.YELLOW_LABEL
    assert got["labels"][90, 80] == LO.WHITE_LABEL
    assert got["labels"][10, 80] == LO.UNKNOWN_LABEL
    assert got["confidence"][30, 37] > 0.08
    assert got["confidence"][30, 122] > 0.1


def test_color_rule_order_is_invariant_and_ambiguous_is_unknown():
    rgb = _road_rgb(shadow=True)
    a = LO.color_rule_mask(rgb, [{"name": "white", "min_value": 0.40},
                                 {"name": "yellow", "min_saturation": 0.28}])
    b = LO.color_rule_mask(rgb, [{"name": "yellow", "min_saturation": 0.28},
                                 {"name": "white", "min_value": 0.40}])
    assert np.array_equal(a["labels"], b["labels"])
    ambiguous = np.array([[[0.46, 0.45, 0.35]]])
    assert LO.color_rule_mask(ambiguous, {})["labels"][0, 0] == LO.UNKNOWN_LABEL


def test_color_rule_mask_rejects_invalid_inputs_and_unknown_rule():
    with pytest.raises(ValueError, match="RGB values"):
        LO.color_rule_mask(np.full((3, 3, 3), np.nan), {})
    with pytest.raises(ValueError, match="unknown rule"):
        LO.color_rule_mask(np.zeros((3, 3, 3)), {"magic": 0.4})


def _top_camera():
    K = np.array([[100.0, 0.0, 50.0], [0.0, 100.0, 50.0], [0.0, 0.0, 1.0]])
    R = np.diag([1.0, -1.0, -1.0])
    C = np.array([0.0, 0.0, 10.0])
    return K, R, -R @ C


def test_plane_topview_color_closed_form_grid_roundtrip_scale_and_rgb():
    K, R, t = _top_camera()
    rows, cols = np.mgrid[0:101, 0:101]
    rgb = np.stack([cols / 100.0, rows / 100.0, np.full(rows.shape, 0.25)], -1)
    got = LO.plane_topview_color(rgb, K, R, t, extent=10.0, res=0.1)
    assert got["valid"].all()
    # RGBの双線形補間は入力座標そのものの線形関数なので閉形式と丸め誤差で一致する。
    expected = np.stack([got["image_col"] / 100.0,
                         got["image_row"] / 100.0,
                         np.full(got["image_row"].shape, 0.25)], -1)
    assert np.max(np.abs(got["rgb"] - expected)) < 2e-16
    rr, cc = np.mgrid[0:100, 0:100]
    q = np.stack([cc, rr, np.ones_like(rr)], -1) @ got["pixel_to_world"].T
    assert np.max(np.abs(q[..., 0] - got["world_x"])) < 1e-14
    assert np.max(np.abs(q[..., 1] - got["world_y"])) < 1e-14
    assert np.allclose(np.diff(got["world_x"], axis=1), 0.1)
    assert np.allclose(np.diff(got["world_y"], axis=0), -0.1)


def test_plane_topview_color_restores_world_orientation_under_left_right_flip():
    K, R, t = _top_camera()
    rgb = np.zeros((101, 101, 3), float)
    rgb[..., 0] = np.arange(101)[None, :] / 100.0
    normal = LO.plane_topview_color(rgb, K, R, t, extent=8.0, res=0.1)
    # 世界xを画像の左へ写す別カメラ。入力像も同じ世界色になるよう左右反転する。
    Rflip = np.diag([-1.0, 1.0, -1.0])
    tflip = -Rflip @ np.array([0.0, 0.0, 10.0])
    flipped = LO.plane_topview_color(rgb[:, ::-1], K, Rflip, tflip, extent=8.0, res=0.1)
    assert np.max(np.abs(normal["rgb"] - flipped["rgb"])) < 3e-16
    assert np.array_equal(normal["world_x"], flipped["world_x"])


def test_plane_topview_color_and_existing_gray_op_share_projection():
    K, R, t = _top_camera()
    g = np.linspace(0.0, 1.0, 101 * 101).reshape(101, 101)
    rgb = np.repeat(g[..., None], 3, axis=2)
    colour = LO.plane_topview_color(rgb, K, R, t, extent=8.0, res=0.1)
    gray = pegsym.plane_topview(g, K, R, t, extent=8.0, res=0.1)
    assert np.max(np.abs(colour["rgb"][..., 0] - gray)) < 1e-15


@pytest.mark.parametrize("bad_K,bad_R", [(np.zeros((3, 3)), np.eye(3)),
                                          (np.eye(3), np.zeros((3, 3))),
                                          (np.eye(3), np.diag([1.0, 1.0, -1.0]))])
def test_plane_topview_color_rejects_degenerate_camera_before_sampling(bad_K, bad_R):
    # 白画素も無い入力で先に校正を拒否する。もっともらしい空BEVを返さない。
    with pytest.raises(ValueError, match="K must|R must"):
        LO.plane_topview_color(np.zeros((8, 8, 3)), bad_K, bad_R, (0.0, 0.0, 1.0),
                               extent=4.0, res=0.5)


def _boundary_points(seed=20261123, shuffle=False, occluded=False):
    rng = np.random.default_rng(seed)
    y = np.linspace(0.0, 25.0, 126)
    if occluded:
        y = y[(y < 8.0) | (y > 14.0)]
    truth = np.array([-1.75, 0.035, 0.0015])
    x = truth[0] + truth[1] * y + truth[2] * y * y + rng.normal(0.0, 0.018, len(y))
    good = np.c_[x, y]
    outliers = np.c_[rng.uniform(-5.0, 5.0, 24), rng.uniform(0.0, 25.0, 24)]
    points = np.vstack([good, outliers])
    if shuffle:
        points = points[rng.permutation(len(points))]
    return points, truth


@pytest.mark.parametrize("occluded", [False, True])
def test_lane_boundary_fit_curve_outliers_occlusion_and_signed_coefficients(occluded):
    points, truth = _boundary_points(occluded=occluded)
    got = LO.lane_boundary_fit(points, side="left", seed=17)
    err = got["coefficients"] - truth
    assert abs(err[0]) < 0.015
    assert abs(err[1]) < 0.003
    assert abs(err[2]) < 0.00012
    assert got["inlier_mask"].sum() >= 95
    assert got["rms"] < 0.03
    assert got["observed_y"][0] < 0.3 and got["observed_y"][1] > 24.7


def test_lane_boundary_fit_is_point_order_invariant_with_fixed_seed():
    a, truth = _boundary_points(shuffle=False)
    b, _ = _boundary_points(shuffle=True)
    fa = LO.lane_boundary_fit(a, seed=3)
    fb = LO.lane_boundary_fit(b, seed=3)
    assert np.max(np.abs(fa["coefficients"] - truth)) < 0.005
    assert np.max(np.abs(fb["coefficients"] - truth)) < 0.005
    assert np.max(np.abs(fa["coefficients"] - fb["coefficients"])) < 5e-4


def test_lane_boundary_fit_rotated_straight_line_and_no_line_failure():
    y = np.linspace(0.0, 20.0, 50)
    slope = np.tan(np.radians(12.0))
    got = LO.lane_boundary_fit(np.c_[-1.8 + slope * y, y], seed=0)
    assert np.allclose(got["coefficients"], [-1.8, slope, 0.0], atol=2e-12)
    with pytest.raises(ValueError, match="points must"):
        LO.lane_boundary_fit(np.empty((0, 2)))
    horizontal = np.c_[np.linspace(-5.0, 5.0, 20), np.zeros(20)]
    with pytest.raises(ValueError, match="single-valued"):
        LO.lane_boundary_fit(horizontal)


def test_lane_boundary_fit_refuses_unidentifiable_quadratic_without_linear_fallback():
    points = np.repeat(np.array([[0.0, 0.0], [1.0, 25.0]]), 3, axis=0)
    got = LO.lane_boundary_fit(points, seed=3)
    assert not got["valid"] and "rank=2" in got["reason"]


def test_lane_boundary_fit_is_translation_invariant_for_large_world_y_origin():
    local_y = np.linspace(0.0, 25.0, 41)
    local_x = -1.75 + 0.035 * local_y + 0.0015 * local_y * local_y
    translated_y = 1_000_000.0 + local_y
    local = LO.lane_boundary_fit(np.c_[local_x, local_y], side="left", seed=7)
    translated = LO.lane_boundary_fit(np.c_[local_x, translated_y], side="left", seed=7)
    assert local["valid"] and translated["valid"]
    probe = np.linspace(0.0, 25.0, 31)
    local_prediction = np.polynomial.polynomial.polyval(probe, local["coefficients"])
    translated_prediction = np.polynomial.polynomial.polyval(
        probe + 1_000_000.0, translated["coefficients"])
    assert np.max(np.abs(local_prediction - (-1.75 + 0.035 * probe + 0.0015 * probe * probe))) < 1e-9
    assert np.max(np.abs(translated_prediction - local_prediction)) < 2e-4


@pytest.mark.parametrize("curvature,outlier_fraction", [(0.0, 0.0), (0.0015, 0.15), (0.003, 0.30)])
@pytest.mark.parametrize("initial_outlier_weight", [0.10, LO.INITIAL_RANSAC_OUTLIER_WEIGHT, 0.50])
def test_lane_boundary_fit_initial_outlier_weight_sensitivity(curvature, outlier_fraction, initial_outlier_weight):
    rng = np.random.default_rng(20261124)
    y = np.linspace(0.0, 25.0, 101)
    truth = np.array([-1.75, 0.02, curvature])
    good = np.c_[np.polynomial.polynomial.polyval(y, truth) + rng.normal(0.0, 0.012, len(y)), y]
    nbad = int(round(len(good) * outlier_fraction))
    bad = np.c_[rng.uniform(-5.0, 5.0, nbad), rng.uniform(0.0, 25.0, nbad)]
    got = LO.lane_boundary_fit(np.vstack([good, bad]), seed=19,
                               initial_outlier_weight=initial_outlier_weight)
    assert got["valid"] and np.max(np.abs(got["coefficients"] - truth)) < 0.02


def _boundary(c0, confidence=0.9, yrange=(0.0, 20.0)):
    return {"valid": True, "coefficients": np.array([c0, 0.02, 0.001]),
            "observed_y": np.array(yrange), "confidence": confidence}


def test_lane_center_path_two_sides_truth_and_corridor_containment():
    got = LO.lane_center_path(_boundary(-1.75), _boundary(1.75))
    y = got["path"][:, 1]
    truth_x = 0.02 * y + 0.001 * y * y
    assert np.max(np.abs(got["path"][:, 0] - truth_x)) < 1e-14
    assert np.allclose(got["lane_width_samples"], 3.5)
    assert np.all(got["band_left"][:, 0] < got["path"][:, 0])
    assert np.all(got["path"][:, 0] < got["band_right"][:, 0])
    assert got["corridor_polygon"].shape == (103, 2)


@pytest.mark.parametrize("missing", ["left", "right"])
def test_lane_center_path_one_side_offsets_and_lowers_confidence(missing):
    left, right = _boundary(-1.75), _boundary(1.75)
    both = LO.lane_center_path(left, right)
    one = LO.lane_center_path(None if missing == "left" else left,
                              None if missing == "right" else right)
    # 曲線ではx方向だけでなく法線方向へずらす。両側の単純中点とは座標が一致しない。
    coef = left["coefficients"] if missing == "right" else right["coefficients"]
    sign = 1.0 if missing == "right" else -1.0
    y = np.linspace(0.0, 20.0, 51)
    bx = coef[0] + coef[1] * y + coef[2] * y * y
    slope = coef[1] + 2.0 * coef[2] * y
    normal = np.c_[np.ones_like(y), -slope]
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    expected = np.c_[bx, y] + sign * 1.75 * normal
    assert np.max(np.abs(one["path"] - expected)) < 1e-14
    assert np.max(np.abs(one["path"] - both["path"])) > 0.01
    assert one["confidence"] < both["confidence"]
    assert one["source"] == ("right" if missing == "left" else "left")


def test_lane_center_path_fail_closed_without_boundaries_or_with_crossing():
    with pytest.raises(ValueError, match="at least one"):
        LO.lane_center_path(None, None)
    with pytest.raises(ValueError, match="cross"):
        LO.lane_center_path(_boundary(1.0), _boundary(-1.0))
    with pytest.raises(ValueError, match="invalid coefficients"):
        LO.lane_center_path({**_boundary(-1.75), "confidence": np.nan}, None)


def test_lane_center_path_rejects_one_sided_offset_cusp_and_foldover():
    # x=0.5y^2 は y=0 の曲率半径が1 mで、3.5 m の片側offsetは尖点・折返しを作る。
    tight = {"valid": True, "coefficients": np.array([0.0, 0.0, 0.5]),
             "observed_y": np.array([0.0, 2.0]), "confidence": 1.0}
    got = LO.lane_center_path(tight, None)
    assert not got["valid"] and "curvature radius" in got["reason"]


def _bev_geometry(theta_deg=0.0):
    h, w, res = 401, 161, 0.05
    pixel_to_world = np.array([[res, 0.0, -4.0], [0.0, -res, 20.0], [0.0, 0.0, 1.0]])
    theta = np.radians(theta_deg)
    tangent = np.array([np.sin(theta), np.cos(theta)])
    normal = np.array([-tangent[1], tangent[0]])
    s = np.linspace(0.0, 20.0, 201)
    path = s[:, None] * tangent
    lane = {"path": path, "lane_width": 3.5, "pixel_to_world": pixel_to_world}
    rows, cols = np.mgrid[0:h, 0:w]
    q = np.stack([cols, rows, np.ones_like(rows)], -1) @ pixel_to_world.T
    world = q[..., :2] / q[..., 2:3]
    along = world @ tangent
    across = world @ normal
    return np.zeros((h, w), np.int16), lane, along, across


def _paint_japan_crosswalk(labels, along, across, *, start=8.7, end=11.5, stripes=(-1.2, -0.4, 0.4, 1.2)):
    """Paint lane-parallel, laterally spaced Japanese zebra stripes / 日本式ゼブラを描く。"""
    for lateral in stripes:
        labels[(np.abs(across - lateral) <= 0.15) & (along >= start) & (along <= end)] = LO.WHITE_LABEL


def test_stop_line_detect_distance_width_partial_occlusion_and_crosswalk_rejection():
    labels, lane, along, across = _bev_geometry()
    stop = (np.abs(along - 8.0) <= 0.15) & (np.abs(across) <= 1.60)
    stop &= ~((across > -0.25) & (across < 0.35))  # 中央の遮蔽で2片に割る
    labels[stop] = LO.WHITE_LABEL
    _paint_japan_crosswalk(labels, along, across, start=12.0, end=15.0)
    # 車線境界は停止線へ接続しても、車線内へ切る段で除かれる。
    labels[np.abs(across + 1.75) <= 0.03] = LO.WHITE_LABEL
    labels[np.abs(across - 1.75) <= 0.03] = LO.WHITE_LABEL
    got = LO.stop_line_detect(labels, lane)
    assert got["found"]
    assert abs(got["distance"] - 8.0) <= 0.06
    assert abs(got["width"] - 3.25) <= 0.11
    assert got["rejected_crosswalk"] == 4
    assert got["confidence"] > 0.8
    assert got["candidates"][0]["fragment_count"] == 2


@pytest.mark.parametrize("theta_deg", [-14.0, 11.0])
def test_stop_line_detect_rotated_lane(theta_deg):
    labels, lane, along, across = _bev_geometry(theta_deg)
    labels[(np.abs(along - 9.0) <= 0.14) & (np.abs(across) <= 1.55)] = LO.WHITE_LABEL
    got = LO.stop_line_detect(labels, lane)
    assert got["found"] and abs(got["distance"] - 9.0) < 0.10
    assert got["angle_error_deg"] < 2.0


def test_stop_line_detect_crosswalk_only_and_no_lines_fail_soft():
    labels, lane, along, across = _bev_geometry()
    empty = LO.stop_line_detect(labels, lane)
    assert not empty["found"] and np.isnan(empty["distance"]) and empty["confidence"] == 0.0
    _paint_japan_crosswalk(labels, along, across, start=7.0, end=10.0)
    crossing = LO.stop_line_detect(labels, lane)
    assert not crossing["found"] and not crossing["ambiguous"]
    assert crossing["confidence"] == 0.0 and crossing["rejected_crosswalk"] == 4


def test_stop_line_detect_keeps_adjacent_stop_before_japan_crosswalk_definitive():
    labels, lane, along, across = _bev_geometry()
    labels[(np.abs(along - 8.0) <= 0.15) & (np.abs(across) <= 1.55)] = LO.WHITE_LABEL
    _paint_japan_crosswalk(labels, along, across, start=8.7, end=11.5)
    got = LO.stop_line_detect(labels, lane)
    assert got["found"] and not got["ambiguous"]
    assert abs(got["distance"] - 8.0) <= 0.06
    assert got["confidence"] > 0.8 and got["rejected_crosswalk"] == 4


@pytest.mark.parametrize("visibility,stripes", [("occlusion", (-0.4,)),
                                                    ("image_edge_crop", (-1.2, 1.2)),
                                                    ("shadow", (0.4,))])
def test_stop_line_detect_rejects_one_or_two_visible_japan_crosswalk_stripes(visibility, stripes):
    labels, lane, along, across = _bev_geometry()
    # 各破壊要因の後に縦縞が1〜2本だけ残る観測を表す。停止線と形が違うので返さない。
    _paint_japan_crosswalk(labels, along, across, start=7.0, end=10.0, stripes=stripes)
    got = LO.stop_line_detect(labels, lane)
    assert not got["found"] and not got["ambiguous"]
    assert got["confidence"] == 0.0 and got["rejected_crosswalk"] == len(stripes)


@pytest.mark.parametrize("mapping", [np.array([[.05, 0., -4.], [0., 0., 20.], [0., 0., 1.]]),
                                       np.array([[.05, 0., -4.], [0., -.05, 20.], [.01, 0., 1.]])])
def test_stop_line_detect_rejects_bad_bev_mapping_even_without_white_pixels(mapping):
    labels, lane, _, _ = _bev_geometry()
    lane["pixel_to_world"] = mapping
    with pytest.raises(ValueError, match="nonsingular|affine"):
        LO.stop_line_detect(labels, lane)


def test_stop_line_detect_rejects_zero_length_path_before_detection():
    labels, lane, _, _ = _bev_geometry()
    lane["path"] = np.array([[0.0, 0.0], [0.0, 0.0]])
    with pytest.raises(ValueError, match="segment"):
        LO.stop_line_detect(labels, lane)
    lane["path"] = np.array([[0.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
    with pytest.raises(ValueError, match="local tangent"):
        LO.stop_line_detect(labels, lane)


def test_stop_line_detect_rejects_non_label_input():
    labels, lane, _, _ = _bev_geometry()
    with pytest.raises(ValueError, match="integer"):
        LO.stop_line_detect(labels.astype(float), lane)


@pytest.mark.parametrize("name", LO.__all__)
def test_worked_examples_execute(name):
    doc = getattr(LO, name).__doc__
    code = doc.split("呼び出し例::", 1)[1]
    exec(compile(textwrap.dedent(code), "<%s example>" % name, "exec"), {})
