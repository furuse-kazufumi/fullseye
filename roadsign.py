# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Classical Japanese road-sign shape and colour rules / 日本の道路標識を読む古典規則。

No learned weights, OCR model, map, semantic image, or truth label is used.  The two ops
separate geometric evidence from the supported colour layouts so ambiguous or damaged signs
can be rejected instead of being assigned a confident class.

学習済み重み、OCRモデル、地図、semantic画像、真値ラベルは使わない。形の証拠と対象と
する配色を分離し、曖昧・欠損した標識を無理に既知クラスへ入れず ``unknown`` にする。

Normative source / 規格の出典 (verified 2026-11-25): e-Gov, *Order on Road Signs,
Road Markings, and Road Surface Markings*, Appended Table 2, Law ID 335M50004002003,
revision 335M50004002003_20260901_508M60000802003.
https://laws.e-gov.go.jp/law/335M50004002003/20260901_508M60000802003

The figures show an 80 cm inverted triangle for stop (330-A), and 60 cm circles for
maximum speed (323) and no entry (303).  Note 1(iii) specifies: stop has white text/edge
on red; maximum speed has blue text/symbol, red border, and white edge/ground; no entry
has a white bar/edge on red.  Note 1(ii)(9) permits regulatory/sign signs to be scaled
from one half to twice the illustrated dimensions when road conditions require it.

図示寸法は一時停止(330-A)が一辺80 cmの逆三角形、最高速度(323)と車両進入禁止
(303)が直径60 cmの円。備考一（三）は、一時停止を赤地・赤縁に白文字・白縁線、
最高速度を白地・白縁に赤枠・青文字/記号、車両進入禁止を赤地に白帯・白縁とする。
備考一（二）9は道路条件により図示寸法の二分の一から二倍までを認める。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

import backends_color

__all__ = ["regular_shape_classify", "road_sign_rule_classify"]


EGOV_LAW_ID = "335M50004002003"
EGOV_REVISION_ID = "335M50004002003_20260901_508M60000802003"
EGOV_SOURCE_URL = ("https://laws.e-gov.go.jp/law/335M50004002003/"
                   "20260901_508M60000802003")

# e-Gov別表第二の図示寸法[m] / illustrated dimensions in Appended Table 2.
STOP_SIDE_M = 0.80
CIRCULAR_SIGN_DIAMETER_M = 0.60
LEGAL_DIMENSION_MIN_SCALE = 0.50
LEGAL_DIMENSION_MAX_SCALE = 2.00

# 輪郭規則 / contour rules.
MIN_CONTOUR_POINTS = 8
DEFAULT_SIMPLIFY_TOLERANCE = 0.012
MIN_CONTOUR_AREA_PX2 = 16.0
TRIANGLE_CIRCULARITY_MIN = 0.42
TRIANGLE_CIRCULARITY_MAX = 0.78
OCTAGON_VERTEX_MIN = 7
OCTAGON_VERTEX_MAX = 9
OCTAGON_CIRCULARITY_MIN = 0.82
OCTAGON_CIRCULARITY_MAX = 0.975
CIRCLE_CIRCULARITY_MIN = 0.955
CIRCLE_MIN_VERTICES = 10
STOP_MIN_APEX_DROP_FRACTION = 0.30
STOP_MAX_TOP_EDGE_TILT_FRACTION = 0.35
STOP_MAX_APEX_CENTRE_OFFSET_FRACTION = 0.30

# HSVと配色規則 / HSV and layout rules.
RED_HUE_HALF_WIDTH = 18.0 / 255.0
HSV_HUE_PERIOD = 180.0 / 255.0
RED_MIN_SATURATION = 0.32
RED_MIN_VALUE = 0.20
WHITE_MAX_SATURATION = 0.24
WHITE_MIN_VALUE = 0.48
BLUE_HUE_MIN = 90.0 / 255.0
BLUE_HUE_MAX = 145.0 / 255.0
BLUE_MIN_SATURATION = 0.28
BLUE_MIN_VALUE = 0.18
BORDER_FRACTION = 0.12
STOP_MIN_RED_FRACTION = 0.45
STOP_MIN_WHITE_FRACTION = 0.015
NO_ENTRY_MIN_RED_FRACTION = 0.45
NO_ENTRY_MIN_WHITE_FRACTION = 0.055
NO_ENTRY_MAX_WHITE_FRACTION = 0.38
NO_ENTRY_BAR_MIN_ASPECT = 2.0
NO_ENTRY_BAR_MAX_CENTRE_OFFSET = 0.24
SPEED_MIN_BORDER_RED_FRACTION = 0.38
SPEED_MIN_INTERIOR_WHITE_FRACTION = 0.42
SPEED_MIN_INK_FRACTION = 0.006


def _contour_points(contour, op):
    """Return one finite closed XLD loop and image shape / 有限な閉XLDを1本返す。"""
    if not isinstance(contour, dict) or "shape" not in contour or "cs" not in contour:
        raise ValueError("%s: contour must be {'shape': (H, W), 'cs': [Nx2 loop]}" % op)
    try:
        shape = tuple(int(v) for v in contour["shape"][:2])
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: contour shape must contain two positive integers" % op) from None
    if len(shape) != 2 or min(shape) < 1:
        raise ValueError("%s: contour shape must contain two positive integers" % op)
    cs = contour["cs"]
    if not isinstance(cs, (list, tuple)) or len(cs) != 1:
        raise ValueError("%s: exactly one contour loop is required" % op)
    points = np.asarray(cs[0], np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < MIN_CONTOUR_POINTS:
        raise ValueError("%s: contour loop must be an (N >= %d, 2) array" % (op, MIN_CONTOUR_POINTS))
    if not np.all(np.isfinite(points)):
        raise ValueError("%s: contour coordinates must be finite" % op)
    if np.linalg.norm(points[0] - points[-1]) <= 1e-9:
        points = points[:-1]
    keep = np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-9]
    points = points[keep]
    if len(points) < 3:
        raise ValueError("%s: contour collapses after duplicate points are removed" % op)
    return points, shape


def _polygon_metrics(points):
    """Shoelace area and closed perimeter / 靴紐面積と閉周長。"""
    nxt = np.roll(points, -1, axis=0)
    area = 0.5 * abs(float(np.sum(points[:, 1] * nxt[:, 0] - nxt[:, 1] * points[:, 0])))
    perimeter = float(np.sum(np.linalg.norm(nxt - points, axis=1)))
    if area < MIN_CONTOUR_AREA_PX2 or perimeter <= 0.0:
        raise ValueError("regular_shape_classify: contour area or perimeter is too small")
    return area, perimeter


def _cross2d(a, b):
    """Scalar 2-D cross product / 2次元外積のz成分。"""
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _rdp(points, epsilon):
    """Open-chain Ramer-Douglas-Peucker vertices / 開曲線RDPの頂点。"""
    if len(points) <= 2:
        return points[[0, -1]]
    chord = points[-1] - points[0]
    length = float(np.linalg.norm(chord))
    if length <= 1e-12:
        distance = np.linalg.norm(points - points[0], axis=1)
    else:
        distance = np.abs(_cross2d(np.broadcast_to(chord, points.shape), points - points[0])) / length
    split = int(np.argmax(distance))
    if float(distance[split]) <= epsilon:
        return points[[0, -1]]
    left = _rdp(points[:split + 1], epsilon)
    right = _rdp(points[split:], epsilon)
    return np.vstack([left[:-1], right])


def _closed_rdp(points, epsilon):
    """Simplify a closed loop without a privileged seam / 閉曲線を継ぎ目に依存せず簡略化。"""
    first = 0
    opposite = int(np.argmax(np.linalg.norm(points - points[first], axis=1)))
    if opposite in (0, len(points) - 1):
        opposite = len(points) // 2
    chain_a = points[:opposite + 1]
    chain_b = np.vstack([points[opposite:], points[:1]])
    a = _rdp(chain_a, epsilon)
    b = _rdp(chain_b, epsilon)
    vertices = np.vstack([a[:-1], b[:-1]])
    # A nearly collinear seam point may survive both chains. Remove it by the same
    # distance-to-neighbour chord test / 継ぎ目のほぼ直線な余分な点を同じ距離門で落とす。
    changed = True
    while changed and len(vertices) > 3:
        changed = False
        for index in range(len(vertices)):
            prev = vertices[index - 1]
            cur = vertices[index]
            nxt = vertices[(index + 1) % len(vertices)]
            chord = nxt - prev
            length = float(np.linalg.norm(chord))
            distance = (float(np.linalg.norm(cur - prev)) if length <= 1e-12
                        else abs(float(_cross2d(chord, cur - prev))) / length)
            if distance <= epsilon:
                vertices = np.delete(vertices, index, axis=0)
                changed = True
                break
    return vertices


def _inverted_triangle_features(vertices):
    """Measure an upright 330-A silhouette / 正立した330-A逆三角形の向きを測る。"""
    if len(vertices) != 3:
        return {"inverted": False, "apex_drop_fraction": 0.0,
                "top_edge_tilt_fraction": math.inf,
                "apex_centre_offset_fraction": math.inf}
    rows = vertices[:, 0]
    cols = vertices[:, 1]
    height = max(float(np.ptp(rows)), np.finfo(float).eps)
    width = max(float(np.ptp(cols)), np.finfo(float).eps)
    apex_index = int(np.argmax(rows))
    top = np.delete(vertices, apex_index, axis=0)
    apex = vertices[apex_index]
    drop = float((apex[0] - float(np.max(top[:, 0]))) / height)
    tilt = float(abs(top[0, 0] - top[1, 0]) / height)
    offset = float(abs(apex[1] - float(np.mean(top[:, 1]))) / width)
    inverted = (drop >= STOP_MIN_APEX_DROP_FRACTION
                and tilt <= STOP_MAX_TOP_EDGE_TILT_FRACTION
                and offset <= STOP_MAX_APEX_CENTRE_OFFSET_FRACTION)
    return {"inverted": bool(inverted), "apex_drop_fraction": drop,
            "top_edge_tilt_fraction": tilt, "apex_centre_offset_fraction": offset}


def regular_shape_classify(contour, *, simplify_tolerance=DEFAULT_SIMPLIFY_TOLERANCE):
    """輪郭を頂点数と等周円形度で三角・八角・円・不明に分類する。

    Parameters
    ----------
    contour : contour
        ``{"shape": (H,W), "cs": [Nx2]}``。行・列順の閉じた輪郭を1本だけ受ける。
    simplify_tolerance : float
        輪郭bbox対角に対するRDP許容距離の比。既定0.012。

    Returns
    -------
    table
        ``label``、RDPの``vertex_count``/``vertices``、``circularity=4πA/P²``、
        面積、周長、確信度。欠け・凹み・閾値境界は ``unknown``。

    English: simplify one ordered closed contour with scale-relative RDP, then combine
    vertex count with isoperimetric circularity.  It recognises triangle, octagon, and
    circle only; partial, concave, or threshold-boundary contours are rejected as unknown.
    Rotation and uniform scale do not affect the features.

    呼び出し例::

        import numpy as np
        import roadsign
        t = np.linspace(0., 2*np.pi, 65)
        c = np.c_[32 + 20*np.sin(t), 32 + 20*np.cos(t)]
        out = roadsign.regular_shape_classify({"shape":(65,65), "cs":[c]})
        assert out["label"] == "circle" and out["circularity"] > .99
    """
    points, shape = _contour_points(contour, "regular_shape_classify")
    tolerance = float(simplify_tolerance)
    if not (np.isfinite(tolerance) and 0.002 <= tolerance <= 0.10):
        raise ValueError("regular_shape_classify: simplify_tolerance must be in [0.002, 0.10]")
    area, perimeter = _polygon_metrics(points)
    extent = np.ptp(points, axis=0)
    diagonal = float(np.linalg.norm(extent))
    if diagonal <= 0.0:
        raise ValueError("regular_shape_classify: contour extent must be positive")
    vertices = _closed_rdp(points, tolerance * diagonal)
    vertex_count = int(len(vertices))
    circularity = float(np.clip(4.0 * math.pi * area / (perimeter * perimeter), 0.0, 1.0))
    edge_a = np.roll(vertices, -1, axis=0) - vertices
    edge_b = np.roll(edge_a, -1, axis=0)
    turns = _cross2d(edge_a, edge_b)
    convex = bool(np.all(turns >= -1e-9) or np.all(turns <= 1e-9))
    label = "unknown"
    reason = "no supported vertex/circularity rule matched"
    confidence = 0.0
    if convex and vertex_count == 3 and TRIANGLE_CIRCULARITY_MIN <= circularity <= TRIANGLE_CIRCULARITY_MAX:
        label = "triangle"
        reason = "three convex vertices with triangular circularity"
        confidence = 1.0 - min(1.0, abs(circularity - math.pi * math.sqrt(3.0) / 9.0) / 0.20)
    elif (convex and OCTAGON_VERTEX_MIN <= vertex_count <= OCTAGON_VERTEX_MAX
          and OCTAGON_CIRCULARITY_MIN <= circularity <= OCTAGON_CIRCULARITY_MAX):
        label = "octagon"
        reason = "seven to nine convex vertices with regular-octagon circularity"
        confidence = min(1.0, (circularity - OCTAGON_CIRCULARITY_MIN)
                         / (OCTAGON_CIRCULARITY_MAX - OCTAGON_CIRCULARITY_MIN))
        confidence *= max(0.0, 1.0 - abs(vertex_count - 8) / 2.0)
    elif convex and vertex_count >= CIRCLE_MIN_VERTICES and circularity >= CIRCLE_CIRCULARITY_MIN:
        label = "circle"
        reason = "many convex vertices with near-unit circularity"
        confidence = min(1.0, (circularity - CIRCLE_CIRCULARITY_MIN)
                         / (1.0 - CIRCLE_CIRCULARITY_MIN))
    return {"valid": True, "label": label, "vertex_count": vertex_count,
            "vertices": vertices, "circularity": circularity, "area": area,
            "perimeter": perimeter, "convex": convex,
            "confidence": float(np.clip(confidence, 0.0, 1.0)), "reason": reason,
            "image_shape": shape, "points": points}


def _polygon_mask(shape, points):
    """Rasterise a polygon with an even-odd rule / 偶奇則で多角形を塗る。"""
    height, width = shape
    rows, cols = np.mgrid[0:height, 0:width].astype(np.float64)
    rows += 0.5
    cols += 0.5
    inside = np.zeros(shape, bool)
    previous = points[-1]
    for current in points:
        r0, c0 = previous
        r1, c1 = current
        crosses = ((r0 > rows) != (r1 > rows))
        at_col = (c1 - c0) * (rows - r0) / (r1 - r0 + np.finfo(float).eps) + c0
        inside ^= crosses & (cols < at_col)
        previous = current
    return inside


def _colour_config(rules):
    """Resolve named colour/layout thresholds / 名前付き配色閾値を解決。"""
    config = {
        "red_hue_half_width": RED_HUE_HALF_WIDTH,
        "red_min_saturation": RED_MIN_SATURATION,
        "red_min_value": RED_MIN_VALUE,
        "white_max_saturation": WHITE_MAX_SATURATION,
        "white_min_value": WHITE_MIN_VALUE,
        "blue_hue_min": BLUE_HUE_MIN,
        "blue_hue_max": BLUE_HUE_MAX,
        "blue_min_saturation": BLUE_MIN_SATURATION,
        "blue_min_value": BLUE_MIN_VALUE,
    }
    if rules is None:
        return config
    if not isinstance(rules, dict):
        raise ValueError("road_sign_rule_classify: rules must be a dict or None")
    unknown = sorted(set(rules) - set(config))
    if unknown:
        raise ValueError("road_sign_rule_classify: unknown rule parameter(s): %s" % ", ".join(unknown))
    for name, value in rules.items():
        value = float(value)
        if not np.isfinite(value):
            raise ValueError("road_sign_rule_classify: rule %s must be finite" % name)
        config[name] = value
    if not (0.0 < config["red_hue_half_width"] < 0.25
            and 0.0 < config["red_min_saturation"] < 1.0
            and 0.0 <= config["red_min_value"] < 1.0
            and 0.0 < config["white_max_saturation"] < 1.0
            and 0.0 <= config["white_min_value"] < 1.0
            and 0.0 <= config["blue_hue_min"] < config["blue_hue_max"] <= 1.0
            and 0.0 < config["blue_min_saturation"] < 1.0
            and 0.0 <= config["blue_min_value"] < 1.0):
        raise ValueError("road_sign_rule_classify: rule thresholds are outside their documented ranges")
    return config


def _largest_white_bar(white, mask):
    """Return size/aspect/centering of the largest white component / 最大白成分の棒らしさ。"""
    labels, count = ndimage.label(white & mask)
    if count == 0:
        return {"fraction": 0.0, "aspect": 0.0, "centre_offset": math.inf}
    sizes = ndimage.sum(np.ones(mask.shape), labels, index=np.arange(1, count + 1))
    component = labels == int(np.argmax(sizes) + 1)
    points = np.column_stack(np.nonzero(component)).astype(np.float64)
    fraction = float(len(points) / max(1, int(mask.sum())))
    centre = points.mean(axis=0)
    centred = points - centre
    covariance = centred.T @ centred / max(1, len(points))
    eigenvalues = np.linalg.eigvalsh(covariance)
    aspect = math.sqrt(float(eigenvalues[-1] / max(eigenvalues[0], 1e-12)))
    target = np.column_stack(np.nonzero(mask)).mean(axis=0)
    scale = max(float(np.linalg.norm(np.ptp(np.column_stack(np.nonzero(mask)), axis=0))), 1.0)
    offset = float(np.linalg.norm(centre - target) / scale)
    return {"fraction": fraction, "aspect": aspect, "centre_offset": offset}


def road_sign_rule_classify(image, contour, rules=None):
    """RGBと輪郭の形から日本式一時停止・最高速度候補・車両進入禁止を規則分類する。

    Parameters
    ----------
    image : (H, W, 3) rgbimage
        0..1の標識crop。輪郭と同じ画素座標。
    contour : contour
        :func:`regular_shape_classify` と同じXLD輪郭。
    rules : table or None
        HSVしきい値の名前付き上書き。既定値はモジュール定数として公開する。

    Returns
    -------
    table
        ``label`` は ``stop_jp``、``speed_limit_candidate``、``no_entry``、``unknown``。
        形、赤/白/青の面積率、外周/内側配色、白帯の形、確信度、棄却理由も返す。

    出典: e-Gov「道路標識、区画線及び道路標示に関する命令」別表第二、Law ID
    ``335M50004002003``、Revision ``335M50004002003_20260901_508M60000802003``
    (2026-11-25確認)。一時停止(330-A)は赤い逆三角形、最高速度(323)は赤枠・白地・
    青文字の円、車両進入禁止(303)は赤地・白横帯の円。図示寸法は順に一辺0.80 m、
    直径0.60 m、直径0.60 m。

    ``speed_limit_candidate`` は速度標識らしい外形までで、数字も規制内容も確定しない。
    数字認識には別の検証済みOCR/テンプレート照合が必要である。赤い八角形は日本の
    一時停止ではないため ``unknown`` に棄却する。

    English: combine the contour op with explicit HSV/layout rules for the three supported
    Japanese appearances.  A circular red border is only a ``speed_limit_candidate``;
    no numeric limit is inferred without a separate validated digit recogniser.  A red
    octagon is deliberately rejected because Japanese stop sign 330-A is an inverted triangle.
    The normative dimensions and colours above come from e-Gov Appended Table 2.

    呼び出し例::

        import numpy as np
        import roadsign
        t = np.linspace(0., 2*np.pi, 65)
        c = np.c_[32 + 24*np.sin(t), 32 + 24*np.cos(t)]
        rgb = np.zeros((65,65,3)); rgb[...,0] = .8
        rgb[28:37, 14:51] = 1.
        out = roadsign.road_sign_rule_classify(rgb, {"shape":(65,65), "cs":[c]}, {})
        assert out["label"] == "no_entry"
    """
    rgb = np.asarray(image, np.float64)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) < 1:
        raise ValueError("road_sign_rule_classify: image must be a non-empty (H, W, 3) RGB array")
    if not np.all(np.isfinite(rgb)) or np.any((rgb < 0.0) | (rgb > 1.0)):
        raise ValueError("road_sign_rule_classify: RGB values must be finite and in [0, 1]")
    points, shape = _contour_points(contour, "road_sign_rule_classify")
    if tuple(rgb.shape[:2]) != shape:
        raise ValueError("road_sign_rule_classify: image and contour shapes must match")
    geometry = regular_shape_classify(contour)
    triangle_orientation = _inverted_triangle_features(geometry["vertices"])
    mask = _polygon_mask(shape, points)
    area = int(mask.sum())
    if area < int(MIN_CONTOUR_AREA_PX2):
        raise ValueError("road_sign_rule_classify: contour encloses too few pixels")
    config = _colour_config(rules)
    hsv = backends_color._trans_from_rgb(rgb, 0.0, 0.0)
    hue, saturation, value = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    # OpenCV stores 8-bit HSV hue on [0, 179], while the shared converter divides
    # every channel by 255 / OpenCVの色相周期は255でなく180段階。
    red_delta = np.minimum(np.abs(hue), np.abs(HSV_HUE_PERIOD - hue))
    red = ((red_delta <= config["red_hue_half_width"])
           & (saturation >= config["red_min_saturation"])
           & (value >= config["red_min_value"]))
    white = ((saturation <= config["white_max_saturation"])
             & (value >= config["white_min_value"]))
    blue = ((hue >= config["blue_hue_min"]) & (hue <= config["blue_hue_max"])
            & (saturation >= config["blue_min_saturation"])
            & (value >= config["blue_min_value"]))
    extent = np.ptp(points, axis=0)
    iterations = max(1, int(round(BORDER_FRACTION * float(np.min(extent)))))
    interior = ndimage.binary_erosion(mask, iterations=iterations)
    if not interior.any():
        interior = ndimage.binary_erosion(mask, iterations=1)
    border = mask & ~interior
    fraction = lambda colour, region: float(np.mean(colour[region])) if region.any() else 0.0
    features = {
        "red_fraction": fraction(red, mask),
        "white_fraction": fraction(white, mask),
        "blue_fraction": fraction(blue, mask),
        "border_red_fraction": fraction(red, border),
        "interior_red_fraction": fraction(red, interior),
        "interior_white_fraction": fraction(white, interior),
        "interior_blue_fraction": fraction(blue, interior),
    }
    bar = _largest_white_bar(white, mask)
    label = "unknown"
    reason = "unsupported or ambiguous colour/shape combination"
    nominal_size = None
    confidence = 0.0
    if (geometry["label"] == "triangle" and triangle_orientation["inverted"]
            and features["red_fraction"] >= STOP_MIN_RED_FRACTION
            and features["white_fraction"] >= STOP_MIN_WHITE_FRACTION):
        label = "stop_jp"
        reason = "red inverted-triangle appearance with white inscription/edge"
        nominal_size = {"kind": "side", "metres": STOP_SIDE_M}
        confidence = min(geometry["confidence"], features["red_fraction"])
    elif geometry["label"] == "circle":
        no_entry = (features["red_fraction"] >= NO_ENTRY_MIN_RED_FRACTION
                    and NO_ENTRY_MIN_WHITE_FRACTION <= features["white_fraction"] <= NO_ENTRY_MAX_WHITE_FRACTION
                    and bar["aspect"] >= NO_ENTRY_BAR_MIN_ASPECT
                    and bar["centre_offset"] <= NO_ENTRY_BAR_MAX_CENTRE_OFFSET)
        speed = (features["border_red_fraction"] >= SPEED_MIN_BORDER_RED_FRACTION
                 and features["interior_white_fraction"] >= SPEED_MIN_INTERIOR_WHITE_FRACTION
                 and features["interior_blue_fraction"] >= SPEED_MIN_INK_FRACTION)
        if no_entry and not speed:
            label = "no_entry"
            reason = "red circle with a centred elongated white bar"
            nominal_size = {"kind": "diameter", "metres": CIRCULAR_SIGN_DIAMETER_M}
            confidence = min(geometry["confidence"], features["red_fraction"],
                             min(1.0, bar["aspect"] / NO_ENTRY_BAR_MIN_ASPECT - 0.5))
        elif speed and not no_entry:
            label = "speed_limit_candidate"
            reason = "red circular border, white interior, and blue ink; digits are not recognised"
            nominal_size = {"kind": "diameter", "metres": CIRCULAR_SIGN_DIAMETER_M}
            confidence = min(geometry["confidence"], features["border_red_fraction"],
                             features["interior_white_fraction"])
        elif no_entry and speed:
            reason = "both no-entry and speed-candidate rules matched"
    elif (geometry["label"] == "triangle" and not triangle_orientation["inverted"]
          and features["red_fraction"] >= STOP_MIN_RED_FRACTION):
        reason = "red triangle is upright rather than inverted stop sign 330-A"
    elif geometry["label"] == "octagon" and features["red_fraction"] >= STOP_MIN_RED_FRACTION:
        reason = "red octagon is not Japanese stop sign 330-A"
    return {"valid": True, "label": label, "confidence": float(np.clip(confidence, 0.0, 1.0)),
            "reason": reason, "shape": geometry, "features": features, "white_bar": bar,
            "nominal_size": nominal_size, "legal_dimension_scale":
            (LEGAL_DIMENSION_MIN_SCALE, LEGAL_DIMENSION_MAX_SCALE),
            "triangle_orientation": triangle_orientation,
            "source": {"law_id": EGOV_LAW_ID, "revision_id": EGOV_REVISION_ID,
                       "url": EGOV_SOURCE_URL, "checked": "2026-11-25"},
            "rules": config}
