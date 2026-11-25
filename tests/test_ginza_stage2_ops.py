"""Known-truth gates for the Ginza v2 stage-2 lane-curve and sign ops.

銀座v2第2段の曲率と日本式標識を、符号つきの閉形式、法令寸法、棄却側まで検査する。
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import drivelateral
import laneops
import roadsign


def _fitted_boundaries(curvature_coefficient, *, mapping=None):
    """Exact quadratic lane boundaries / 厳密な二次車線境界。"""
    y = np.linspace(0.0, 30.0, 121)
    centre = 0.12 + 0.025 * y + curvature_coefficient * y * y
    left = laneops.lane_boundary_fit(np.c_[centre - 1.75, y], side="left", seed=7)
    right = laneops.lane_boundary_fit(np.c_[centre + 1.75, y], side="right", seed=7)
    if mapping is not None:
        left["pixel_to_world"] = mapping
        right["pixel_to_world"] = mapping
    return left, right


@pytest.mark.parametrize("quadratic", [-0.004, 0.0, 0.004])
def test_lane_curve_estimate_signed_closed_form_and_speed_limit(quadratic):
    left, right = _fitted_boundaries(quadratic)
    got = laneops.lane_curve_estimate(left, right, camera_height=1.62, samples=61, seed=11)
    y = got["path"][:, 1]
    truth_x = 0.12 + 0.025 * y + quadratic * y * y
    truth_kappa = (2.0 * quadratic
                   / np.power(1.0 + (0.025 + 2.0 * quadratic * y) ** 2, 1.5))
    assert np.percentile(np.abs(got["path"][:, 0] - truth_x), 95) < 2e-12
    assert np.max(np.abs(got["curvature"] - truth_kappa)) < 2e-12
    if quadratic:
        assert np.all(np.sign(got["curvature"]) == np.sign(quadratic))
    else:
        assert np.all(got["curvature"] == pytest.approx(0.0, abs=2e-16))
        assert np.all(np.isinf(got["radius"]))
    plan = drivelateral.curvature_speed_plan(
        got["arc_length"], got["curvature"], v_max=22.0,
        a_lat_max=2.5, a_accel=1.8, a_decel=2.5)
    assert np.max(plan["v_limit"] ** 2 * np.abs(got["curvature"])) <= 2.5 + 1e-12
    assert got["camera_height"] == 1.62


def test_lane_curve_estimate_preserves_explicit_bev_mapping_and_fails_closed():
    mapping = np.array([[0.05, 0.0, -4.0], [0.0, -0.05, 25.0], [0.0, 0.0, 1.0]])
    left, right = _fitted_boundaries(0.002, mapping=mapping)
    got = laneops.lane_curve_estimate(left, right, pixel_to_world=mapping,
                                       camera_height=1.55, samples=31)
    assert np.array_equal(got["pixel_to_world"], mapping)
    mismatched = mapping.copy()
    mismatched[0, 2] += 0.01
    with pytest.raises(ValueError, match="mappings disagree"):
        laneops.lane_curve_estimate(left, right, pixel_to_world=mismatched)
    with pytest.raises(ValueError, match="camera_height"):
        laneops.lane_curve_estimate(left, right, camera_height=0.0)
    with pytest.raises(ValueError, match="samples"):
        laneops.lane_curve_estimate(left, right, samples=5)


def test_lane_rgb_and_curve_empty_or_constant_inputs_fail_closed_with_kind_guidance():
    """空/一定入力は、誤った曲率でなく理由と直し方を返す / reject without a fake curve."""
    with pytest.raises(ValueError) as empty_rgb:
        laneops.color_rule_mask(np.empty((0, 16, 3)), {})
    message = str(empty_rgb.value)
    assert "(0, 16, 3)" in message and "no lane evidence" in message
    assert "color_rule_mask" in message and "車線根拠" in message and "np.zeros" in message

    constant = laneops.color_rule_mask(np.full((32, 32, 3), 0.6), {})
    assert np.all(constant["labels"] == laneops.UNKNOWN_LABEL)
    assert not constant["white_mask"].any() and not constant["yellow_mask"].any()

    with pytest.raises(ValueError) as no_boundaries:
        laneops.lane_curve_estimate(None, None)
    message = str(no_boundaries.value)
    assert "left=None and right=None" in message and "No centre or curvature" in message
    assert "lane_boundary_fit" in message and "同定できない" in message


def _regular_vertices(count, radius=30.0, angle=0.0, centre=(64.0, 64.0)):
    theta = angle + 2.0 * math.pi * np.arange(count) / count
    return np.c_[centre[0] + radius * np.cos(theta),
                 centre[1] + radius * np.sin(theta)]


def _dense_polygon(vertices, samples_per_edge=16):
    """Ordered edge samples without a duplicate closure / 重複終点なしの辺標本。"""
    pieces = []
    for start, end in zip(vertices, np.roll(vertices, -1, axis=0)):
        t = np.arange(samples_per_edge, dtype=np.float64) / samples_per_edge
        pieces.append(start[None] * (1.0 - t[:, None]) + end[None] * t[:, None])
    return np.vstack(pieces)


def _contour(points, shape=(129, 129)):
    return {"shape": shape, "cs": [np.asarray(points, np.float64)]}


def _mask(shape, points):
    rows, cols = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float64)
    rows += 0.5
    cols += 0.5
    inside = np.zeros(shape, bool)
    previous = points[-1]
    for current in points:
        r0, c0 = previous
        r1, c1 = current
        crosses = (r0 > rows) != (r1 > rows)
        at_col = (c1 - c0) * (rows - r0) / (r1 - r0 + np.finfo(float).eps) + c0
        inside ^= crosses & (cols < at_col)
        previous = current
    return inside


def _sign(kind, *, angle=0.0, scale=1.0, brightness=1.0):
    shape = (129, 129)
    rgb = np.full((*shape, 3), 0.12, np.float64)
    centre = np.array([64.0, 64.0])
    radius = 32.0 * scale
    if kind in ("stop_jp", "upright_triangle"):
        rotation = angle + (math.pi if kind == "upright_triangle" else 0.0)
        vertices = _regular_vertices(3, radius, rotation)
        points = _dense_polygon(vertices)
    elif kind == "octagon":
        points = _dense_polygon(_regular_vertices(8, radius, angle))
    elif kind == "damaged":
        vertices = _regular_vertices(8, radius, angle)
        vertices[1] = centre + 0.35 * (vertices[1] - centre)
        points = _dense_polygon(vertices)
    else:
        theta = np.linspace(0.0, 2.0 * math.pi, 129, endpoint=False)
        points = np.c_[centre[0] + radius * np.cos(theta),
                       centre[1] + radius * np.sin(theta)]
    outer = _mask(shape, points)
    red = np.array([0.90, 0.04, 0.04])
    white = np.array([0.94, 0.94, 0.94])
    blue = np.array([0.04, 0.12, 0.82])
    rgb[outer] = red
    rr, cc = np.mgrid[0:shape[0], 0:shape[1]]
    if kind in ("stop_jp", "upright_triangle"):
        inner_white_points = centre + 0.84 * (points - centre)
        inner_red_points = centre + 0.72 * (points - centre)
        rgb[_mask(shape, inner_white_points)] = white
        rgb[_mask(shape, inner_red_points)] = red
        rgb[outer & (np.abs(rr - 61.0) <= 2.0) & (np.abs(cc - 64.0) <= 16.0)] = white
    elif kind == "speed_limit_candidate":
        inner = (rr - centre[0]) ** 2 + (cc - centre[1]) ** 2 <= (0.76 * radius) ** 2
        rgb[inner] = white
        ink = inner & (((np.abs(cc - 57.0) <= 2.0) & (np.abs(rr - 64.0) <= 13.0))
                       | ((np.abs(cc - 70.0) <= 2.0) & (np.abs(rr - 64.0) <= 13.0)))
        rgb[ink] = blue
    elif kind == "no_entry":
        bar = outer & (np.abs(rr - centre[0]) <= 4.0) & (np.abs(cc - centre[1]) <= 22.0)
        rgb[bar] = white
    elif kind == "low_saturation":
        rgb[outer] = (0.58, 0.46, 0.46)
    return np.clip(rgb * brightness, 0.0, 1.0), _contour(points, shape)


@pytest.mark.parametrize(
    "count,expected",
    [(3, "triangle"), (8, "octagon"), (64, "circle")],
)
@pytest.mark.parametrize("angle", [0.0, 0.23, 1.17])
@pytest.mark.parametrize("scale", [0.65, 1.0, 1.35])
def test_regular_shape_classify_rotation_scale_and_signed_shape(count, expected, angle, scale):
    if count == 64:
        points = _regular_vertices(count, 30.0 * scale, angle)
    else:
        points = _dense_polygon(_regular_vertices(count, 30.0 * scale, angle))
    got = roadsign.regular_shape_classify(_contour(points))
    assert got["label"] == expected
    assert got["convex"]
    assert got["circularity"] > 0.42


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("stop_jp", "stop_jp"),
        ("speed_limit_candidate", "speed_limit_candidate"),
        ("no_entry", "no_entry"),
        ("octagon", "unknown"),
        ("upright_triangle", "unknown"),
        ("damaged", "unknown"),
        ("low_saturation", "unknown"),
    ],
)
@pytest.mark.parametrize("brightness", [0.65, 0.9, 1.1])
def test_road_sign_rule_classify_supported_and_failure_sides(kind, expected, brightness):
    image, contour = _sign(kind, angle=0.12, scale=1.0, brightness=brightness)
    got = roadsign.road_sign_rule_classify(image, contour, {})
    assert got["label"] == expected
    assert got["source"]["law_id"] == "335M50004002003"
    assert got["source"]["revision_id"] == "335M50004002003_20260901_508M60000802003"
    if expected == "stop_jp":
        assert got["triangle_orientation"]["inverted"]
        assert got["nominal_size"] == {"kind": "side", "metres": 0.80}
    elif expected in ("speed_limit_candidate", "no_entry"):
        assert got["nominal_size"] == {"kind": "diameter", "metres": 0.60}
    else:
        assert got["nominal_size"] is None


def test_road_sign_dimensions_and_invalid_inputs_fail_closed():
    assert roadsign.STOP_SIDE_M == 0.80
    assert roadsign.CIRCULAR_SIGN_DIAMETER_M == 0.60
    assert (roadsign.LEGAL_DIMENSION_MIN_SCALE,
            roadsign.LEGAL_DIMENSION_MAX_SCALE) == (0.50, 2.00)
    image, contour = _sign("no_entry")
    with pytest.raises(ValueError, match="RGB values"):
        roadsign.road_sign_rule_classify(image * 2.0, contour)
    with pytest.raises(ValueError, match="shapes must match"):
        roadsign.road_sign_rule_classify(image[:-1], contour)
    with pytest.raises(ValueError, match="exactly one contour"):
        roadsign.regular_shape_classify({"shape": image.shape[:2], "cs": contour["cs"] * 2})


def test_sign_empty_and_constant_inputs_reject_or_return_unknown_with_kind_guidance():
    image, contour = _sign("no_entry")
    with pytest.raises(ValueError) as empty_image:
        roadsign.road_sign_rule_classify(np.empty((0, 32, 3)), contour)
    message = str(empty_image.value)
    assert "(0, 32, 3)" in message and "no colour/layout evidence" in message
    assert "Decode one sign crop" in message and "配色・配置の根拠" in message

    with pytest.raises(ValueError) as empty_contour:
        roadsign.regular_shape_classify({"shape": image.shape[:2], "cs": []})
    message = str(empty_contour.value)
    assert "0 loops" in message and "not identifiable" in message
    assert "Segment one sign crop" in message and "同定できない" in message

    constant = np.full_like(image, 0.5)
    got = roadsign.road_sign_rule_classify(constant, contour, {})
    assert got["label"] == "unknown"
    assert "RGB range is 0" in got["reason"] and "returning unknown" in got["reason"]
    assert "recrop the complete sign" in got["reason"] and "根拠がない" in got["reason"]
