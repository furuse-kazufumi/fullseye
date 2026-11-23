# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Learning-free lane and stop-line perception operators / 学習なしの車線・停止線知覚。

RGB → colour rules → colour-preserving top view → robust lane boundaries → lane centre
→ stop line is one typed recipe. The implementation intentionally uses classical image
processing only; no learned weights, semantic image, map or ground-truth pose enters it.

RGB → 色規則 → RGB 保持の俯瞰 → 頑健な車線境界 → 車線中央 → 停止線、を型付きで
つなぐ。学習済み重み、semantic 画像、地図、正解姿勢は使わない。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

import backends_color
import calib
import ransac_fit

__all__ = ["color_rule_mask", "plane_topview_color", "lane_boundary_fit",
           "lane_center_path", "stop_line_detect"]


# 色規則 / colour rules (OpenCV HSV returned by trans_from_rgb, all scaled by 255).
WHITE_MAX_SATURATION = 0.22
WHITE_MIN_VALUE = 0.28
WHITE_MIN_LOCAL_CONTRAST = 0.025
WHITE_LOCAL_WINDOW_PIXELS = 15
YELLOW_HUE_CENTER = 30.0 / 255.0
YELLOW_HUE_HALF_WIDTH = 10.0 / 255.0
YELLOW_MIN_SATURATION = 0.30
YELLOW_MIN_VALUE = 0.28
MIN_CLASS_CONFIDENCE = 0.05
AMBIGUITY_MARGIN = 0.06
UNKNOWN_LABEL = 0
WHITE_LABEL = 1
YELLOW_LABEL = 2

# 境界当てはめ / boundary fitting.
MIN_BOUNDARY_POINTS = 6
DEFAULT_RANSAC_THRESHOLD_M = 0.18
DEFAULT_RANSAC_ITERATIONS = 300
HUBER_SCALE_MULTIPLIER = 1.5
IRLS_ITERATIONS = 12
IRLS_COEFFICIENT_TOLERANCE = 1e-12
# RANSAC は初期直線の外れ値を完全には捨てない。0.25 は、初期inlierを4倍優先して
# 曲線へ収束させつつ、直線RANSACが取りこぼした曲線上の点もIRLSへ残す折衷である。
# Keep RANSAC outliers at one quarter weight: initial inliers dominate 4:1 while curved
# inliers missed by the initial line can still enter the IRLS fit.
INITIAL_RANSAC_OUTLIER_WEIGHT = 0.25
MIN_FORWARD_DIRECTION = 0.20
MIN_OBSERVED_RANGE_M = 5.0
MIN_DISTINCT_BOUNDARY_Y = 3
MAX_QUADRATIC_DESIGN_CONDITION = 1.0e7
MAX_LEGACY_COEFFICIENT_WORLD_Y_M = 1.0e6

# 中央と走行帯 / centre and drivable band.
DEFAULT_LANE_WIDTH_M = 3.50
MIN_LANE_WIDTH_M = 1.50
MAX_LANE_WIDTH_M = 6.00
DEFAULT_PATH_SAMPLES = 51
DEFAULT_BAND_INSET_M = 0.20
SINGLE_BOUNDARY_CONFIDENCE_SCALE = 0.60

# 停止線 / stop line.
MIN_COMPONENT_PIXELS = 4
MIN_FRAGMENT_WIDTH_M = 0.25
MIN_TRANSVERSE_BAND_WIDTH_M = 1.00
MIN_STOP_WIDTH_M = 2.20
MAX_STOP_THICKNESS_M = 0.90
MAX_PERPENDICULAR_ERROR_DEG = 18.0
MERGE_LONGITUDINAL_M = 0.38
LANE_INTERIOR_FRACTION = 0.48
JAPAN_CROSSWALK_MIN_STRIPE_LENGTH_M = 1.00
JAPAN_CROSSWALK_MAX_STRIPE_WIDTH_M = 0.90
JAPAN_CROSSWALK_MAX_PARALLEL_ERROR_DEG = 18.0
# National Police Agency, 2024-07-26 notification: the clear interval between
# Japanese crosswalk (201) white stripes is 0.45--0.90 m.  One BEV pixel is
# allowed at either end because the raster measures both stripe edges only to
# that resolution.
JAPAN_CROSSWALK_MIN_STRIPE_GAP_M = 0.45
JAPAN_CROSSWALK_MAX_STRIPE_GAP_M = 0.90
CROSSWALK_GAP_TOLERANCE_PIXELS = 1.0
MIN_CROSSWALK_STRIPES = 2
MAPPING_ABSOLUTE_TOLERANCE = 1e-12
HOMOGRAPHY_SINGULAR_VALUE_FLOOR = 1e-12
BEV_HOMOGENEOUS_ROW_TOLERANCE = 1e-12
PATH_SEGMENT_LENGTH_FLOOR_M = 1e-9


def _invalid_boundary(reason, *, side, points, ransac_line=None, ransac_inliers=None):
    """Return an explicit unusable boundary / 二次同定不能の境界を明示する。"""
    return {"valid": False, "reason": reason, "side": side,
            "points": points.copy(), "ransac_line": ransac_line,
            "ransac_inlier_mask": ransac_inliers}


def _quadratic_design_is_identifiable(y):
    """Normalise y before testing the final quadratic design / 中心化・正規化した二次設計行列の同定性。"""
    unique_y = np.unique(np.asarray(y, np.float64))
    y0 = float(np.mean(y))
    scale = float(np.max(np.abs(y - y0)))
    if not np.isfinite(scale) or scale <= np.finfo(float).eps:
        return False, 0, len(unique_y), float("inf"), y0, scale
    u = (y - y0) / scale
    design = np.column_stack([np.ones(len(y)), u, u * u])
    rank = int(np.linalg.matrix_rank(design))
    condition = float(np.linalg.cond(design))
    ok = (rank == 3 and len(unique_y) >= MIN_DISTINCT_BOUNDARY_Y
          and np.isfinite(condition) and condition <= MAX_QUADRATIC_DESIGN_CONDITION)
    return ok, rank, len(unique_y), condition, y0, scale


def _quadratic_original_coefficients(coefficients, y_centre, y_scale):
    """Convert x=b0+b1*u+b2*u^2 back to x=c0+c1*y+c2*y^2 / 正規化係数を世界座標へ戻す。"""
    b0, b1, b2 = np.asarray(coefficients, np.float64)
    return np.array([b0 - b1 * y_centre / y_scale + b2 * y_centre ** 2 / y_scale ** 2,
                     b1 / y_scale - 2.0 * b2 * y_centre / y_scale ** 2,
                     b2 / y_scale ** 2])


def _evaluate_boundary(boundary, y):
    """Evaluate the canonical normalised fit when it is available / 正規化fitを正準として評価する。"""
    yy = np.asarray(y, np.float64)
    if all(key in boundary for key in ("normalised_coefficients", "y_centre", "y_scale")):
        coefficient = np.asarray(boundary["normalised_coefficients"], np.float64)
        centre, scale = float(boundary["y_centre"]), float(boundary["y_scale"])
        if coefficient.shape != (3,) or not np.all(np.isfinite(coefficient)) or not np.isfinite(centre) or scale <= 0.0:
            raise ValueError("lane_center_path: boundary has invalid normalised coefficients")
        u = (yy - centre) / scale
        return coefficient[0] + coefficient[1] * u + coefficient[2] * u * u
    coefficient = np.asarray(boundary["coefficients"], np.float64)
    return coefficient[0] + coefficient[1] * yy + coefficient[2] * yy * yy


def _boundary_slope(boundary, y):
    """Evaluate dx/dy without expanding a large-origin polynomial / 大原点へ展開せず接線を評価する。"""
    yy = np.asarray(y, np.float64)
    if all(key in boundary for key in ("normalised_coefficients", "y_centre", "y_scale")):
        coefficient = np.asarray(boundary["normalised_coefficients"], np.float64)
        centre, scale = float(boundary["y_centre"]), float(boundary["y_scale"])
        u = (yy - centre) / scale
        return (coefficient[1] + 2.0 * coefficient[2] * u) / scale
    coefficient = np.asarray(boundary["coefficients"], np.float64)
    return coefficient[1] + 2.0 * coefficient[2] * yy


def _minimum_boundary_radius(boundary, y0, y1):
    """Return the minimum radius using canonical coefficients / 正規化係数で最小曲率半径を求める。"""
    if all(key in boundary for key in ("normalised_coefficients", "y_centre", "y_scale")):
        coefficient = np.asarray(boundary["normalised_coefficients"], np.float64)
        centre, scale = float(boundary["y_centre"]), float(boundary["y_scale"])
        if abs(coefficient[2]) <= np.finfo(float).eps:
            return float("inf")
        critical_u = np.clip(-coefficient[1] / (2.0 * coefficient[2]),
                             (y0 - centre) / scale, (y1 - centre) / scale)
        slopes = (coefficient[1] + 2.0 * coefficient[2] * np.array([
            (y0 - centre) / scale, (y1 - centre) / scale, critical_u])) / scale
        return float(np.min((1.0 + slopes * slopes) ** 1.5 * scale * scale / abs(2.0 * coefficient[2])))
    return _minimum_quadratic_radius(boundary["coefficients"], y0, y1)


def _minimum_quadratic_radius(coefficients, y0, y1):
    """Return the smallest radius of curvature on y0..y1 / 二次境界の最小曲率半径。"""
    c1, c2 = float(coefficients[1]), float(coefficients[2])
    if abs(c2) <= np.finfo(float).eps:
        return float("inf")
    critical = np.clip(-c1 / (2.0 * c2), y0, y1)
    slopes = c1 + 2.0 * c2 * np.array([y0, y1, critical])
    return float(np.min((1.0 + slopes * slopes) ** 1.5 / abs(2.0 * c2)))


def _polyline_self_intersects(points):
    """Detect proper or touching non-adjacent segment intersections / 非隣接線分の自己交差を検出。"""
    p = np.asarray(points, np.float64)
    def cross2(a, b):
        return float(a[0] * b[1] - a[1] * b[0])
    for i in range(len(p) - 1):
        a, b = p[i], p[i + 1]
        for j in range(i + 2, len(p) - 1):
            c, d = p[j], p[j + 1]
            ab_c = cross2(b - a, c - a)
            ab_d = cross2(b - a, d - a)
            cd_a = cross2(d - c, a - c)
            cd_b = cross2(d - c, b - c)
            if ab_c * ab_d <= 0.0 and cd_a * cd_b <= 0.0:
                return True
    return False


def _finite_unit_path(path, op):
    """Validate every path segment before a tangent is formed / 接線の前に各経路区間を検査。"""
    if path.ndim != 2 or path.shape[1] != 2 or len(path) < 2 or not np.all(np.isfinite(path)):
        raise ValueError("%s: lane_model.path must be finite (N >= 2, 2) world points" % op)
    segments = np.diff(path, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    if not np.all(np.isfinite(lengths)) or np.any(lengths <= PATH_SEGMENT_LENGTH_FLOOR_M):
        raise ValueError("%s: every lane_model.path segment must have positive finite length" % op)
    local = np.empty_like(path)
    local[0], local[-1] = segments[0], segments[-1]
    if len(path) > 2:
        local[1:-1] = path[2:] - path[:-2]
    if np.any(np.linalg.norm(local, axis=1) <= PATH_SEGMENT_LENGTH_FLOOR_M):
        raise ValueError("%s: every lane_model.path point must have a nonzero local tangent" % op)
    return lengths


def _bev_pixel_to_world(pixel_to_world, op):
    """Validate the affine BEV raster mapping / BEV の正則なアフィン対応だけを受ける。"""
    H = np.asarray(pixel_to_world, np.float64)
    if H.shape != (3, 3) or not np.all(np.isfinite(H)):
        raise ValueError("%s: lane_model.pixel_to_world must be a finite 3x3 matrix" % op)
    if not np.allclose(H[2], [0.0, 0.0, 1.0], rtol=0.0,
                       atol=BEV_HOMOGENEOUS_ROW_TOLERANCE):
        raise ValueError("%s: pixel_to_world must be an affine BEV mapping with final row [0, 0, 1]" % op)
    linear = H[:2, :2]
    if np.linalg.matrix_rank(linear) != 2 or np.linalg.svd(linear, compute_uv=False)[-1] <= HOMOGRAPHY_SINGULAR_VALUE_FLOOR:
        raise ValueError("%s: pixel_to_world 2x2 linear part must be nonsingular" % op)
    if np.linalg.matrix_rank(H) != 3:
        raise ValueError("%s: pixel_to_world must be nonsingular" % op)
    return H


def _finite_rgb(image, op):
    """Return finite HxWx3 RGB in [0,1] / 有限な RGB を返す。"""
    rgb = np.asarray(image, np.float64)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) < 1:
        raise ValueError("%s: image must be a non-empty (H, W, 3) RGB array" % op)
    if not np.all(np.isfinite(rgb)) or np.any((rgb < 0.0) | (rgb > 1.0)):
        raise ValueError("%s: RGB values must be finite and in [0, 1]" % op)
    return rgb


def _rule_values(rules):
    """Resolve named overrides; sequence order never changes precedence / 規則順に依存させない。"""
    values = {
        "white_max_saturation": WHITE_MAX_SATURATION,
        "white_min_value": WHITE_MIN_VALUE,
        "white_min_local_contrast": WHITE_MIN_LOCAL_CONTRAST,
        "white_local_window_pixels": WHITE_LOCAL_WINDOW_PIXELS,
        "yellow_hue_center": YELLOW_HUE_CENTER,
        "yellow_hue_half_width": YELLOW_HUE_HALF_WIDTH,
        "yellow_min_saturation": YELLOW_MIN_SATURATION,
        "yellow_min_value": YELLOW_MIN_VALUE,
        "min_class_confidence": MIN_CLASS_CONFIDENCE,
        "ambiguity_margin": AMBIGUITY_MARGIN,
    }
    if rules is None:
        return values
    if isinstance(rules, dict):
        items = [rules]
    elif isinstance(rules, (list, tuple)):
        items = list(rules)
    else:
        raise ValueError("color_rule_mask: rules must be a dict, a sequence of dicts, or None")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("color_rule_mask: every rule override must be a dict")
        name = item.get("name")
        if name in ("white", "yellow"):
            prefix = name + "_"
            for key, value in item.items():
                if key != "name":
                    values[prefix + key] = value
        else:
            for key, value in item.items():
                if key != "name":
                    values[key] = value
    unknown = sorted(set(values) - {
        "white_max_saturation", "white_min_value", "white_min_local_contrast",
        "white_local_window_pixels", "yellow_hue_center",
        "yellow_hue_half_width", "yellow_min_saturation", "yellow_min_value",
        "min_class_confidence", "ambiguity_margin"})
    if unknown:
        raise ValueError("color_rule_mask: unknown rule parameter(s): %s" % ", ".join(unknown))
    for key, value in list(values.items()):
        try:
            values[key] = float(value)
        except (TypeError, ValueError):
            raise ValueError("color_rule_mask: rule %s must be numeric" % key) from None
        if not np.isfinite(values[key]):
            raise ValueError("color_rule_mask: rule %s must be finite" % key)
    if not (0.0 < values["white_max_saturation"] < 1.0
            and 0.0 <= values["white_min_value"] < 1.0
            and 0.0 < values["white_min_local_contrast"] < 1.0
            and values["white_local_window_pixels"] >= 3.0
            and values["white_local_window_pixels"].is_integer()
            and int(values["white_local_window_pixels"]) % 2 == 1
            and 0.0 < values["yellow_hue_half_width"] < 0.5
            and 0.0 < values["yellow_min_saturation"] < 1.0
            and 0.0 <= values["yellow_min_value"] < 1.0
            and 0.0 <= values["min_class_confidence"] < 1.0
            and 0.0 <= values["ambiguity_margin"] < 1.0):
        raise ValueError("color_rule_mask: rule thresholds are outside their documented ranges")
    return values


def color_rule_mask(image, rules=None):
    """RGBを明示的なHSV規則で白線・黄線・不明に分け、maskと確信度を返す。

    :func:`trans_from_rgb` の既存実装でRGB→HSVに変換する。白と黄のscoreを独立に
    計算して最大scoreを採るため、``rules``をlistで渡した順序には依存しない。scoreが
    ``min_class_confidence``未満、または上位2色の差が``ambiguity_margin``以下なら
    ``unknown``に棄却する。影・逆光・濡れ路面に合わせた自動較正はしない。

    Parameters
    ----------
    image : (H, W, 3) rgbimage
        0..1の有限なRGB画像。
    rules : table or None
        名前付きしきい値の上書き。``[{"name":"white", "min_value":...}, ...]``も可。

    Returns
    -------
    table
        ``labels``(0 unknown, 1 white, 2 yellow)、各mask、``confidence``、色ごとのscore、HSV、使った規則。

    English: classify finite RGB pixels as white, yellow or unknown with explicit HSV
    thresholds after the existing ``trans_from_rgb`` conversion. Ambiguous pixels are
    rejected. White additionally requires local value contrast, so a uniformly bright road
    is not a white line; this is a fixed classical rule, not an illumination estimator.

    呼び出し例::

        import numpy as np
        import laneops
        rgb = np.array([[[0.9, 0.9, 0.9], [0.9, 0.75, 0.05], [0.3, 0.3, 0.3]]])
        out = laneops.color_rule_mask(rgb, {})
        assert out["labels"].tolist() == [[1, 2, 0]]
    """
    rgb = _finite_rgb(image, "color_rule_mask")
    cfg = _rule_values(rules)
    # 既存 op の実装そのものを再利用する / reuse the registered op implementation.
    hsv = backends_color._trans_from_rgb(rgb, 0.0, 0.0)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    white_sat = (cfg["white_max_saturation"] - sat) / cfg["white_max_saturation"]
    white_val = (val - cfg["white_min_value"]) / (1.0 - cfg["white_min_value"])
    local_floor = ndimage.grey_opening(
        val, size=int(cfg["white_local_window_pixels"]), mode="nearest")
    white_contrast = (val - local_floor - cfg["white_min_local_contrast"]) / (
        1.0 - cfg["white_min_local_contrast"])
    white_score = np.clip(np.minimum.reduce([white_sat, white_val, white_contrast]), 0.0, 1.0)
    hue_delta = np.abs(hue - cfg["yellow_hue_center"])
    hue_delta = np.minimum(hue_delta, 1.0 - hue_delta)
    yellow_hue = (cfg["yellow_hue_half_width"] - hue_delta) / cfg["yellow_hue_half_width"]
    yellow_sat = (sat - cfg["yellow_min_saturation"]) / (1.0 - cfg["yellow_min_saturation"])
    yellow_val = (val - cfg["yellow_min_value"]) / (1.0 - cfg["yellow_min_value"])
    yellow_score = np.clip(np.minimum.reduce([yellow_hue, yellow_sat, yellow_val]), 0.0, 1.0)
    scores = np.stack([white_score, yellow_score], -1)
    best = np.max(scores, -1)
    gap = np.abs(white_score - yellow_score)
    second = np.minimum(white_score, yellow_score)
    # 競合色が0なら小さいscoreでも曖昧ではない。両色が候補のときだけ差で棄却する。
    # A sole weak candidate is not an ambiguity; apply the margin only when both compete.
    known = (best >= cfg["min_class_confidence"]) & ((second <= 0.0) | (gap > cfg["ambiguity_margin"]))
    labels = np.where(known, np.argmax(scores, -1) + 1, UNKNOWN_LABEL).astype(np.int16)
    confidence = np.where(known, best, 1.0 - best)
    return {"labels": labels, "white_mask": labels == WHITE_LABEL,
            "yellow_mask": labels == YELLOW_LABEL, "unknown_mask": labels == UNKNOWN_LABEL,
            "confidence": confidence, "white_score": white_score,
            "yellow_score": yellow_score, "hsv": hsv, "rules": cfg}


def plane_topview_color(image, K, R, t, *, z=0.0, centre=(0.0, 0.0),
                        extent=30.0, res=0.05, fill=(0.0, 0.0, 0.0)):
    """地面平面をRGBのまま俯瞰へ写し、有効maskと画素↔世界座標を返す。

    投影格子は既存 :func:`plane_topview` と共通の ``calib`` 核を使う。列=世界+x、
    行=世界−y、画素中心は整数。レンズ歪みは補正済みを前提とし、地面を単一平面
    z=``z``とみなすため、坂・縁石・車体は正しい位置にならない。``K``の正則性と
    焦点距離、``R``の直交性・行列式を入口で検査し、満たさなければ拒否する。

    Parameters
    ----------
    image : (H, W, 3) rgbimage
        0..1 RGB。色を輝度へ落とさない。
    K, R, t : matrix, matrix, signal
        ``X_camera = R @ X_world + t``の内部/外部パラメータ。
    z, centre, extent, res
        平面の高さ、出力中心(x,y)、一辺[m]、1画素[m]。

    Returns
    -------
    table
        ``rgb``, ``valid``, ``world_x/y``, ``image_row/col``, ``pixel_to_world`` と逆行列。

    English: bilinearly rectify RGB onto a world z-plane while retaining a validity
    mask and both pixel/world correspondences. It assumes an already-undistorted image
    and a single plane; non-planar road objects are not metrically valid. It validates
    nonsingular positive-focal K and a proper orthogonal R before any sampling.

    呼び出し例::

        import numpy as np
        import laneops
        rgb = np.zeros((8, 8, 3)); rgb[..., 1] = 1.0
        K = np.array([[4., 0., 3.5], [0., 4., 3.5], [0., 0., 1.]])
        R = np.diag([1., -1., -1.]); C = np.array([0., 0., 4.])
        out = laneops.plane_topview_color(rgb, K, R, -R @ C, extent=4., res=.5)
        assert out["rgb"].shape == (8, 8, 3) and np.all(out["rgb"][out["valid"], 1] == 1.0)
    """
    rgb = _finite_rgb(image, "plane_topview_color")
    maps = calib._plane_topview_projection(
        rgb.shape[:2], K, R, t, z=z, centre=centre, extent=extent, res=res,
        op="plane_topview_color")
    rows, cols, valid = maps["image_row"], maps["image_col"], maps["valid"]
    fill_rgb = np.asarray(fill, np.float64).reshape(-1)
    if fill_rgb.shape != (3,) or not np.all(np.isfinite(fill_rgb)):
        raise ValueError("plane_topview_color: fill must be three finite RGB values")
    out = np.empty(rows.shape + (3,), np.float64)
    out[...] = fill_rgb
    r0 = np.clip(np.floor(rows[valid]).astype(int), 0, rgb.shape[0] - 2)
    c0 = np.clip(np.floor(cols[valid]).astype(int), 0, rgb.shape[1] - 2)
    fr, fc = rows[valid] - r0, cols[valid] - c0
    out[valid] = ((1 - fc)[:, None] * (1 - fr)[:, None] * rgb[r0, c0]
                  + fc[:, None] * (1 - fr)[:, None] * rgb[r0, c0 + 1]
                  + (1 - fc)[:, None] * fr[:, None] * rgb[r0 + 1, c0]
                  + fc[:, None] * fr[:, None] * rgb[r0 + 1, c0 + 1])
    return {"rgb": out, "valid": valid, "world_x": maps["world_x"],
            "world_y": maps["world_y"], "image_row": rows, "image_col": cols,
            "pixel_to_world": maps["pixel_to_world"],
            "world_to_pixel": maps["world_to_pixel"], "resolution": float(res),
            "z": float(z), "centre": np.asarray(centre, np.float64), "extent": float(extent)}


def lane_boundary_fit(points, *, side="unknown", ransac_threshold=DEFAULT_RANSAC_THRESHOLD_M,
                      ransac_iterations=DEFAULT_RANSAC_ITERATIONS,
                      initial_outlier_weight=INITIAL_RANSAC_OUTLIER_WEIGHT, seed=0):
    """俯瞰の(x横,y前方)点から ``x=c0+c1*y+c2*y²`` の車線境界を頑健に当てはめる。

    既存 :func:`ransac_line` を外れ値に強い初期直線として使い、その後Huber IRLSの
    二次曲線へ拡張する。強いS字、yが折り返す境界、地面平面でない点には使えない。

    Parameters
    ----------
    points : (N, 2) keypoints
        世界座標 ``(x lateral, y forward)`` [m]。順序は問わない。
    side : {"left", "right", "unknown"}
        後段が片側だけを車線中央へずらすための名前。
    ransac_threshold, ransac_iterations, initial_outlier_weight, seed
        直線/最終inlierの距離[m]、反復数、初期RANSAC外れ値のIRLS重み、固定乱数seed。
        ``initial_outlier_weight=0.25``は初期inlierを4倍優先しつつ、曲線上で初期直線から
        外れた点を残すための固定値である。

    Returns
    -------
    table
        正準の``normalised_coefficients``(b0,b1,b2), ``y_centre``, ``y_scale``、
        ``observed_y``、``inlier_mask``、残差、RMS、確信度。互換用の
        ``coefficients``(c0,c1,c2)は ``abs(y) <= 1e6 m`` の範囲だけ数値精度を契約する。

    English: initialise with the existing 3-D ``ransac_line`` (z=0), then fit the
    boundary x(y) with a Huber robust quadratic. Point order does not matter. It centres
    and normalises y for rank, condition-number, least-squares work, and evaluation.
    ``normalised_coefficients``, ``y_centre``, and ``y_scale`` are the canonical output.
    The legacy expanded world coefficients are numerically guaranteed only while
    ``abs(y) <= 1e6 m``. The final inlier design must have
    rank 3, at least three distinct y values, and bounded condition number; otherwise it
    returns ``valid=False`` instead of silently using a line. Hairpins where y is not
    single-valued are outside the contract and fail closed.

    呼び出し例::

        import numpy as np
        import laneops
        y = np.linspace(0., 20., 41); x = -1.75 + 0.002 * y*y
        fit = laneops.lane_boundary_fit(np.c_[x, y], side="left", seed=7)
        assert np.allclose(fit["coefficients"], [-1.75, 0., 0.002], atol=1e-10)
    """
    op = "lane_boundary_fit"
    p = np.asarray(points, np.float64)
    if (p.ndim != 2 or p.shape[1] != 2 or len(p) < MIN_BOUNDARY_POINTS
            or not np.all(np.isfinite(p))):
        raise ValueError("%s: points must be a finite (N >= %d, 2) array" % (op, MIN_BOUNDARY_POINTS))
    if side not in ("left", "right", "unknown"):
        raise ValueError("%s: side must be 'left', 'right', or 'unknown'" % op)
    threshold = float(ransac_threshold)
    iterations = int(ransac_iterations)
    outlier_weight = float(initial_outlier_weight)
    if not (np.isfinite(threshold) and threshold > 0.0 and iterations >= 1):
        raise ValueError("%s: ransac_threshold must be > 0 and ransac_iterations >= 1" % op)
    if not (np.isfinite(outlier_weight) and 0.0 <= outlier_weight <= 1.0):
        raise ValueError("%s: initial_outlier_weight must be finite and in [0, 1]" % op)
    p3 = np.column_stack([p, np.zeros(len(p))])
    line, line_inliers, line_info = ransac_fit.ransac_line(p3, threshold, iters=iterations, seed=int(seed))
    point, direction = line["point"], line["direction"]
    if abs(direction[1]) < MIN_FORWARD_DIRECTION:
        raise ValueError("%s: boundary is not single-valued in forward y (RANSAC direction y=%g)"
                         % (op, direction[1]))
    y = p[:, 1]
    y_centre = float(np.mean(y))
    y_scale = float(np.max(np.abs(y - y_centre)))
    if not np.isfinite(y_scale) or y_scale <= np.finfo(float).eps:
        return _invalid_boundary("quadratic design has no finite y scale", side=side, points=p,
                                 ransac_line=line, ransac_inliers=line_inliers)
    u = (y - y_centre) / y_scale
    design = np.column_stack([np.ones(len(p)), u, u * u])
    line_slope = direction[0] / direction[1]
    coef = np.array([point[0] + line_slope * y_centre, line_slope * y_scale, 0.0])
    delta = HUBER_SCALE_MULTIPLIER * threshold
    weights = np.where(line_inliers, 1.0, outlier_weight)
    for _ in range(IRLS_ITERATIONS):
        root_w = np.sqrt(weights)
        new_coef, *_ = np.linalg.lstsq(design * root_w[:, None], p[:, 0] * root_w, rcond=None)
        residual = p[:, 0] - design @ new_coef
        abs_residual = np.abs(residual)
        weights = np.where(abs_residual <= delta, 1.0, delta / np.maximum(abs_residual, np.finfo(float).eps))
        if np.max(np.abs(new_coef - coef)) < IRLS_COEFFICIENT_TOLERANCE:
            coef = new_coef
            break
        coef = new_coef
    residual = p[:, 0] - design @ coef
    inliers = np.abs(residual) <= threshold
    if int(inliers.sum()) < MIN_BOUNDARY_POINTS:
        raise ValueError("%s: fewer than %d inliers remain after robust fitting" % (op, MIN_BOUNDARY_POINTS))
    identifiable, rank, unique_count, condition, _, _ = _quadratic_design_is_identifiable(y[inliers])
    # このopは次数を黙って一次へ落とさない。必要な二次情報が無い出力は明示的に無効にする。
    # Do not silently fall back to a line: a quadratic boundary needs all three columns.
    if not identifiable:
        return _invalid_boundary("quadratic design is not identifiable (rank=%d, distinct_y=%d, condition=%g)"
                                 % (rank, unique_count, condition), side=side, points=p,
                                 ransac_line=line, ransac_inliers=line_inliers)
    coef, *_ = np.linalg.lstsq(design[inliers], p[inliers, 0], rcond=None)
    residual = p[:, 0] - design @ coef
    inliers = np.abs(residual) <= threshold
    identifiable, rank, unique_count, condition, _, _ = _quadratic_design_is_identifiable(y[inliers])
    if not identifiable:
        return _invalid_boundary("final quadratic design is not identifiable (rank=%d, distinct_y=%d, condition=%g)"
                                 % (rank, unique_count, condition), side=side, points=p,
                                 ransac_line=line, ransac_inliers=line_inliers)
    yrange = np.array([float(np.min(y[inliers])), float(np.max(y[inliers]))])
    span = float(yrange[1] - yrange[0])
    rms = float(np.sqrt(np.mean(residual[inliers] ** 2)))
    confidence = float((inliers.mean()) * min(1.0, span / MIN_OBSERVED_RANGE_M)
                       * math.exp(-rms / threshold))
    original = _quadratic_original_coefficients(coef, y_centre, y_scale)
    return {"valid": True, "model": "x=b0+b1*u+b2*u^2; u=(y-y_centre)/y_scale", "side": side,
            "normalised_coefficients": coef.copy(), "y_centre": y_centre, "y_scale": y_scale,
            "coefficients": original,
            "legacy_coefficients_valid": bool(np.max(np.abs(y[inliers])) <= MAX_LEGACY_COEFFICIENT_WORLD_Y_M),
            "observed_y": yrange, "inlier_mask": inliers,
            "residuals": residual, "rms": rms, "confidence": confidence,
            "ransac_line": line, "ransac_inlier_mask": line_inliers,
            "ransac_info": line_info, "points": p.copy()}


def _boundary(boundary, name):
    """Validate a boundary table or a documented absent value / 境界表を検査。"""
    if boundary is None or (isinstance(boundary, dict) and not boundary.get("valid", True)):
        return None
    if not isinstance(boundary, dict):
        raise ValueError("lane_center_path: %s must be a boundary table or None" % name)
    coef = np.asarray(boundary.get("coefficients"), np.float64).reshape(-1)
    yrange = np.asarray(boundary.get("observed_y"), np.float64).reshape(-1)
    confidence = boundary.get("confidence", np.nan)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = float("nan")
    has_normalised = all(key in boundary for key in ("normalised_coefficients", "y_centre", "y_scale"))
    normalised = np.asarray(boundary.get("normalised_coefficients", []), np.float64).reshape(-1)
    normal_centre, normal_scale = boundary.get("y_centre", np.nan), boundary.get("y_scale", np.nan)
    normal_ok = (normalised.shape == (3,) and np.all(np.isfinite(normalised))
                 and np.isfinite(normal_centre) and np.isfinite(normal_scale) and normal_scale > 0.0)
    if ((not has_normalised and (coef.shape != (3,) or not np.all(np.isfinite(coef))))
            or (has_normalised and not normal_ok) or yrange.shape != (2,) or not np.all(np.isfinite(yrange))
            or yrange[1] <= yrange[0] or not np.isfinite(confidence)
            or not 0.0 <= confidence <= 1.0):
        raise ValueError("lane_center_path: %s has invalid coefficients or observed_y" % name)
    return boundary


def lane_center_path(left, right, *, lane_width=DEFAULT_LANE_WIDTH_M,
                     samples=DEFAULT_PATH_SAMPLES, band_inset=DEFAULT_BAND_INSET_M):
    """左右境界から車線中央の経路と走行可能帯を返す。

    両側があれば共通観測範囲で中点を取る。片側だけなら既知の``lane_width``の半分
    だけ内側へずらし、確信度を``SINGLE_BOUNDARY_CONFIDENCE_SCALE``倍に下げる。

    Parameters
    ----------
    left, right : table or None
        :func:`lane_boundary_fit`の結果。欠測側はNoneか``{"valid":False}``。
    lane_width, samples, band_inset
        既知の車線幅[m]、標本数、境界から走行帯を内側へ引く量[m]。

    Returns
    -------
    table
        ``path``(x,y)、``band_left/right``、閉じた``corridor_polygon``、幅、確信度、使用した側。

    English: average two fitted boundaries, or offset a single observed boundary by
    half the known lane width with reduced confidence. Before a one-sided offset, it
    rejects a curvature radius no larger than any constructed offset, and rejects a
    cusp, tangent reversal, or self-intersection with ``valid=False``. It returns the
    centre path and an inset drivable corridor; it does not check vehicle footprint or
    obstacles.

    呼び出し例::

        import numpy as np
        import laneops
        left = {"coefficients":np.array([-1.75,0.,0.]), "observed_y":np.array([0.,20.]), "confidence":1.}
        right = {"coefficients":np.array([1.75,0.,0.]), "observed_y":np.array([0.,20.]), "confidence":1.}
        out = laneops.lane_center_path(left, right)
        assert np.allclose(out["path"][:, 0], 0.) and np.allclose(out["lane_width_samples"], 3.5)
    """
    lft, rgt = _boundary(left, "left"), _boundary(right, "right")
    if lft is None and rgt is None:
        raise ValueError("lane_center_path: at least one boundary is required")
    width, inset = float(lane_width), float(band_inset)
    count = int(samples)
    if not (MIN_LANE_WIDTH_M <= width <= MAX_LANE_WIDTH_M and 0.0 <= inset < width / 2.0 and count >= 2):
        raise ValueError("lane_center_path: lane_width, band_inset, or samples is outside the documented range")
    if lft is not None and rgt is not None:
        y0 = max(float(lft["observed_y"][0]), float(rgt["observed_y"][0]))
        y1 = min(float(lft["observed_y"][1]), float(rgt["observed_y"][1]))
        if y1 <= y0:
            raise ValueError("lane_center_path: left and right observed ranges do not overlap")
        y = np.linspace(y0, y1, count)
        lx = _evaluate_boundary(lft, y)
        rx = _evaluate_boundary(rgt, y)
        widths = rx - lx
        if np.any((widths < MIN_LANE_WIDTH_M) | (widths > MAX_LANE_WIDTH_M)):
            raise ValueError("lane_center_path: boundaries cross or give an implausible lane width")
        cx = 0.5 * (lx + rx)
        confidence = math.sqrt(float(lft.get("confidence", 0.0)) * float(rgt.get("confidence", 0.0)))
        confidence *= math.exp(-float(np.std(widths)) / width)
        source = "both"
    else:
        one, source = (lft, "left") if lft is not None else (rgt, "right")
        y = np.linspace(float(one["observed_y"][0]), float(one["observed_y"][1]), count)
        curvature_radius = _minimum_boundary_radius(one, y[0], y[-1])
        # 片側の中心だけでなく推定した反対側境界まで作るので、最大offset=lane_widthを守る。
        # The inferred outer boundary is offset by a full lane width, not only the centre.
        if curvature_radius <= width:
            return {"valid": False, "reason": "one-sided offset reaches curvature radius (radius=%g m, offset=%g m)"
                    % (curvature_radius, width), "source": source, "left": lft, "right": rgt}
        bx = _evaluate_boundary(one, y)
        slope = _boundary_slope(one, y)
        # (x(y), y) の右向き法線。曲線の平行曲線なので x だけをずらさない。
        normal = np.column_stack([np.ones(count), -slope])
        normal /= np.linalg.norm(normal, axis=1, keepdims=True)
        boundary_points = np.column_stack([bx, y])
        if source == "left":
            left_points = boundary_points
            right_points = boundary_points + width * normal
            centre_points = boundary_points + 0.5 * width * normal
        else:
            right_points = boundary_points
            left_points = boundary_points - width * normal
            centre_points = boundary_points - 0.5 * width * normal
        widths = np.full(count, width)
        confidence = float(one.get("confidence", 0.0)) * SINGLE_BOUNDARY_CONFIDENCE_SCALE
    if lft is not None and rgt is not None:
        left_points = np.column_stack([lx, y])
        right_points = np.column_stack([rx, y])
        centre_points = np.column_stack([cx, y])
    # 片側は法線方向、両側は既知の左右境界方向で走行帯を内側へ縮める。
    inward = right_points - left_points
    inward /= np.linalg.norm(inward, axis=1, keepdims=True)
    band_left = left_points + inset * inward
    band_right = right_points - inset * inward
    path = centre_points
    if source != "both":
        tangents = np.diff(path, axis=0)
        tangent_lengths = np.linalg.norm(tangents, axis=1)
        if (np.any(tangent_lengths <= PATH_SEGMENT_LENGTH_FLOOR_M)
                or np.any(np.sum(tangents[:-1] * tangents[1:], axis=1) <= 0.0)
                or _polyline_self_intersects(path)
                or _polyline_self_intersects(left_points)
                or _polyline_self_intersects(right_points)):
            return {"valid": False, "reason": "one-sided offset has a cusp, reversal, or self-intersection",
                    "source": source, "left": lft, "right": rgt}
    polygon = np.vstack([band_left, band_right[::-1], band_left[:1]])
    out = {"valid": True, "path": path, "band_left": band_left,
            "band_right": band_right, "corridor_polygon": polygon,
            "lane_width_samples": widths, "lane_width": float(np.median(widths)),
            "observed_y": np.array([y[0], y[-1]]), "confidence": float(np.clip(confidence, 0.0, 1.0)),
            "source": source, "left": lft, "right": rgt}
    # ラスタ対応を境界表に添えた呼び手は、そのまま停止線へ型付きでつなげる。
    # Preserve an explicitly supplied raster mapping for the downstream stop-line op.
    mappings = [b.get("pixel_to_world") for b in (lft, rgt) if b is not None and "pixel_to_world" in b]
    if mappings:
        first = np.asarray(mappings[0], np.float64)
        if any(not np.allclose(first, np.asarray(m, np.float64), rtol=0.0,
                               atol=MAPPING_ABSOLUTE_TOLERANCE) for m in mappings[1:]):
            raise ValueError("lane_center_path: left and right pixel_to_world mappings disagree")
        out["pixel_to_world"] = first
    return out


def _pixel_world(pixel_to_world, rows, cols, op):
    """Raster coordinates to world xy / ラスタ座標を世界xyへ。"""
    H = _bev_pixel_to_world(pixel_to_world, op)
    q = np.column_stack([cols, rows, np.ones(len(rows))]) @ H.T
    if np.any(np.abs(q[:, 2]) < np.finfo(float).eps):
        raise ValueError("%s: pixel_to_world maps a white pixel to the horizon" % op)
    return q[:, :2] / q[:, 2:3]


def _empty_crosswalk():
    """Return the fail-soft typed crosswalk table / 横断歩道なしの型付き表。"""
    return {"crosswalk_found": False, "near_distance": float("nan"), "far_distance": float("nan"),
            "width": 0.0, "stripe_count": 0, "stripe_width": 0.0,
            "stripe_spacing": float("nan"), "stripe_spacings": [], "confidence": 0.0,
            "candidates": []}


def _crosswalk_from_lane_coordinates(arc, lateral, resolution):
    """Group long lane-parallel stripes and measure their clear gaps / 縦縞群と白線間隔を測る。"""
    empty = _empty_crosswalk()
    if len(arc) == 0:
        return empty
    # Remove transverse bands before measuring a stripe.  In a touching comb the
    # first stripe shares one raster row with the stop line; retaining that row would
    # incorrectly pull the stripe's near edge back to the stop-line near edge.
    # A diagonal raster line jitters its projected arc coordinate by roughly a pixel;
    # use a two-pixel longitudinal band so that it is still removed as one transverse line.
    forward_bins = np.rint(arc / (2.0 * resolution)).astype(np.int64)
    keep = np.ones(len(arc), bool)
    for bin_id in np.unique(forward_bins):
        selected = forward_bins == bin_id
        lateral_bins = np.unique(np.rint(lateral[selected] / resolution).astype(np.int64))
        breaks = np.flatnonzero(np.diff(lateral_bins) > 1)
        starts = np.r_[0, breaks + 1]
        ends = np.r_[breaks, len(lateral_bins) - 1]
        widest_run = max((lateral_bins[end] - lateral_bins[start] + 1) * resolution
                         for start, end in zip(starts, ends))
        if widest_run >= MIN_TRANSVERSE_BAND_WIDTH_M:
            keep[selected] = False
    arc, lateral = arc[keep], lateral[keep]
    if len(arc) == 0:
        return empty
    # A transverse stop line contributes only a short arc span to each lateral bin;
    # a zebra stripe must stay long in the forward direction.
    bins = np.rint(lateral / resolution).astype(np.int64)
    stripes = []
    for bin_id in np.unique(bins):
        selected = bins == bin_id
        if selected.sum() < MIN_COMPONENT_PIXELS:
            continue
        length = float(np.ptp(arc[selected]) + resolution)
        if length < JAPAN_CROSSWALK_MIN_STRIPE_LENGTH_M:
            continue
        stripes.append({"bin": int(bin_id), "near_distance": float(np.min(arc[selected])),
                        "far_distance": float(np.max(arc[selected])),
                        "left": float(np.min(lateral[selected])), "right": float(np.max(lateral[selected])),
                        "width": float(np.ptp(lateral[selected]) + resolution), "length": length})
    if not stripes:
        return empty
    # Join adjacent long bins into one painted white stripe.
    stripes.sort(key=lambda stripe: stripe["bin"])
    merged = []
    for stripe in stripes:
        if not merged or stripe["bin"] > merged[-1][-1]["bin"] + 1:
            merged.append([stripe])
        else:
            merged[-1].append(stripe)
    measured = []
    for group in merged:
        measured.append({"near_distance": min(s["near_distance"] for s in group),
                         "far_distance": max(s["far_distance"] for s in group),
                         "left": min(s["left"] for s in group), "right": max(s["right"] for s in group),
                         "width": max(s["right"] for s in group) - min(s["left"] for s in group) + resolution,
                         "length": max(s["far_distance"] for s in group) - min(s["near_distance"] for s in group) + resolution})
    tolerance = CROSSWALK_GAP_TOLERANCE_PIXELS * resolution
    groups = []
    for stripe in measured:
        if not groups or stripe["left"] - groups[-1][-1]["right"] > JAPAN_CROSSWALK_MAX_STRIPE_GAP_M + tolerance:
            groups.append([stripe])
        else:
            groups[-1].append(stripe)
    candidates = []
    for group in groups:
        gaps = [float(group[i + 1]["left"] - group[i]["right"])
                for i in range(len(group) - 1)]
        valid_widths = all(s["width"] <= JAPAN_CROSSWALK_MAX_STRIPE_WIDTH_M + tolerance for s in group)
        valid_gaps = (len(group) >= MIN_CROSSWALK_STRIPES and all(
            JAPAN_CROSSWALK_MIN_STRIPE_GAP_M - tolerance <= gap <= JAPAN_CROSSWALK_MAX_STRIPE_GAP_M + tolerance
            for gap in gaps))
        confidence = min(1.0, len(group) / 4.0) * (1.0 if valid_gaps and valid_widths else 0.25)
        candidates.append({"kind": "japan_crosswalk_201", "crosswalk_found": bool(valid_gaps and valid_widths),
                           "near_distance": min(s["near_distance"] for s in group),
                           "far_distance": max(s["far_distance"] for s in group),
                           "width": max(s["right"] for s in group) - min(s["left"] for s in group) + resolution,
                           "stripe_count": len(group), "stripe_width": float(np.median([s["width"] for s in group])),
                           "stripe_spacing": float(np.median(gaps)) if gaps else float("nan"),
                           "stripe_spacings": gaps, "spacing_tolerance": tolerance,
                           "spacing_valid": bool(valid_gaps), "confidence": float(confidence)})
    candidates.sort(key=lambda candidate: (candidate["crosswalk_found"], candidate["stripe_count"], candidate["confidence"]), reverse=True)
    primary = candidates[0]
    return {**primary, "observed_stripe_count": len(measured), "candidates": candidates}


def stop_line_detect(labels, lane_model):
    """停止線と日本式横断歩道を別々の型付き出力として検出する。

    白画素を車線内へ切り、連結片を世界座標へ写す。同じ前方距離の遮蔽片を結合し、
    車線接線への直交角、幅、厚さで停止線を判定する。日本式の横断歩道は、車の進行方向と
    平行な細長い白線を道路幅方向に並べる様式なので、長手が接線方向・幅が道路幅方向に細い
    片を横断歩道縞として数える。同一の8近傍成分に停止線と縦縞が接しても、まず各前方位置の
    横方向の帯を取り出して停止線候補を残す。縞は別に横方向へ束ね、停止線とは別の横断歩道
    表として手前/奥の弧長、幅、縞数、縞幅、白線間隔、確信度を返す。縞の間隔が法令の範囲外
    なら横断歩道と断定しない。別様式の横断歩道はこのopの入力契約外である。

    様式の一次情報: 道路標識、区画線及び道路標示に関する命令（昭和三十五年総理府・建設省令
    第三号）別表第6の横断歩道(201)および停止線(203)、e-Gov法令検索
    https://laws.e-gov.go.jp/law/335M50004002003 。
    白線間隔は警察庁交通規制課長通達「白線の設置間隔を拡大した横断歩道等を設ける場合の
    留意事項について」（令和6年7月26日、警規発第96号）で45--90 cm。
    https://www.npa.go.jp/laws/notification/koutuu/kisei/kisei20240726_4.pdf 。BEVでは各端
    を1画素までしか測れないため、判定域を ``[0.45-res, 0.90+res] m`` とする。

    Parameters
    ----------
    labels : (H, W) labels
        :func:`color_rule_mask`のlabelを俯瞰へ写したもの。1だけを白として使う。
    lane_model : table
        ``path``(世界xy), ``lane_width`` と ``pixel_to_world``(俯瞰画素col,row→世界xy)。

    Returns
    -------
    table
        停止線の``found``、``ambiguous``、経路始点からの``distance``[m]、``width``[m]、
        ``confidence``、候補に加え、別の型付き ``crosswalk`` 表と同じ値の
        ``crosswalk_found``、``crosswalk_near_distance``、``crosswalk_far_distance``、
        ``crosswalk_width``、``crosswalk_stripe_count``、``crosswalk_stripe_width``、
        ``crosswalk_stripe_spacing``、``crosswalk_confidence``を返す。

    English: find wide white components nearly perpendicular to the lane tangent and
    merge fragments split by occlusion. It returns a separate typed crosswalk table.
    The supported Japanese crosswalk style is a set of long lane-parallel, laterally narrow stripes, per Road Sign, Road Marking
    and Road Surface Marking Order, Appended Table 6, crosswalk (201) and stop line
    (203), e-Gov https://laws.e-gov.go.jp/law/335M50004002003 . Its clear stripe gaps
    must be 0.45--0.90 m per National Police Agency notification No. 96 (2024-07-26),
    https://www.npa.go.jp/laws/notification/koutuu/kisei/kisei20240726_4.pdf , with one
    BEV pixel tolerance at each bound. Other national styles are outside this op's contract. It
    validates every path segment and an affine nonsingular BEV mapping first. Distance
    is arc length from path[0].

    呼び出し例::

        import numpy as np
        import laneops
        labels = np.zeros((201, 81), np.int16); labels[100:104, 8:73] = 1
        H = np.array([[.05,0.,-2.],[0.,-.05,10.],[0.,0.,1.]])
        lane = {"path":np.c_[np.zeros(101), np.linspace(0.,10.,101)], "lane_width":3.5, "pixel_to_world":H}
        out = laneops.stop_line_detect(labels, lane)
        assert out["found"] and abs(out["distance"] - 5.0) < 0.11
    """
    op = "stop_line_detect"
    lab = np.asarray(labels)
    if lab.ndim != 2 or lab.size == 0 or not np.issubdtype(lab.dtype, np.integer):
        raise ValueError("%s: labels must be a non-empty 2-D integer label image" % op)
    if not isinstance(lane_model, dict):
        raise ValueError("%s: lane_model must be a table" % op)
    path = np.asarray(lane_model.get("path"), np.float64)
    segment_lengths = _finite_unit_path(path, op)
    lane_width = float(lane_model.get("lane_width", np.nan))
    if not (MIN_LANE_WIDTH_M <= lane_width <= MAX_LANE_WIDTH_M):
        raise ValueError("%s: lane_model.lane_width is missing or implausible" % op)
    H = _bev_pixel_to_world(lane_model.get("pixel_to_world"), op)
    white_rows, white_cols = np.nonzero(lab == WHITE_LABEL)
    def result(stop, crosswalk):
        return {**stop, "crosswalk": crosswalk,
                "crosswalk_found": crosswalk["crosswalk_found"],
                "crosswalk_near_distance": crosswalk["near_distance"],
                "crosswalk_far_distance": crosswalk["far_distance"],
                "crosswalk_width": crosswalk["width"],
                "crosswalk_stripe_count": crosswalk["stripe_count"],
                "crosswalk_stripe_width": crosswalk["stripe_width"],
                "crosswalk_stripe_spacing": crosswalk["stripe_spacing"],
                "crosswalk_confidence": crosswalk["confidence"],
                "rejected_crosswalk": crosswalk.get("observed_stripe_count", crosswalk["stripe_count"])}
    empty = {"found": False, "distance": float("nan"), "width": 0.0,
             "confidence": 0.0, "ambiguous": False, "candidates": []}
    if len(white_rows) == 0:
        return result(empty, _empty_crosswalk())
    world = _pixel_world(lane_model.get("pixel_to_world"), white_rows, white_cols, op)
    # 最近の中心点と接線 / nearest centre point and local tangent.
    from scipy.spatial import cKDTree
    nearest = cKDTree(path).query(world)[1]
    prev = np.maximum(nearest - 1, 0)
    nxt = np.minimum(nearest + 1, len(path) - 1)
    tangent = path[nxt] - path[prev]
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    lateral = np.sum((world - path[nearest]) * normal, axis=1)
    keep = np.abs(lateral) <= LANE_INTERIOR_FRACTION * lane_width
    interior = np.zeros(lab.shape, bool)
    interior[white_rows[keep], white_cols[keep]] = True
    components, ncomp = ndimage.label(interior, structure=np.ones((3, 3), int))
    cumulative = np.r_[0.0, np.cumsum(segment_lengths)]
    kept_world, kept_nearest = world[keep], nearest[keep]
    kept_tangent, kept_normal = tangent[keep], normal[keep]
    crosswalk_arc = cumulative[kept_nearest] + np.sum((kept_world - path[kept_nearest]) * kept_tangent, axis=1)
    crosswalk_lateral = np.sum((kept_world - path[kept_nearest]) * kept_normal, axis=1)
    fragments = []
    resolution = math.sqrt(abs(float(np.linalg.det(H[:2, :2]))))
    for component_id in range(1, ncomp + 1):
        rows, cols = np.nonzero(components == component_id)
        if len(rows) < MIN_COMPONENT_PIXELS:
            continue
        pts = _pixel_world(lane_model["pixel_to_world"], rows, cols, op)
        idx = int(cKDTree(path).query(pts.mean(0))[1])
        i0, i1 = max(idx - 1, 0), min(idx + 1, len(path) - 1)
        tv = path[i1] - path[i0]
        tv /= np.linalg.norm(tv)
        nv = np.array([-tv[1], tv[0]])
        rel = pts - path[idx]
        along, across = rel @ tv, rel @ nv
        # Extract transverse bands before rejecting long vertical stripes.  This is what
        # keeps a stop line when its end touches a zebra stripe in an 8-neighbour image.
        along_bins = np.rint(along / resolution).astype(np.int64)
        broad = []
        for bin_id in np.unique(along_bins):
            selected = along_bins == bin_id
            # Four separated zebra stripes have a large outer span but no wide
            # continuous transverse run.  Test the largest continuous run instead.
            lateral_bins = np.unique(np.rint(across[selected] / resolution).astype(np.int64))
            breaks = np.flatnonzero(np.diff(lateral_bins) > 1)
            starts = np.r_[0, breaks + 1]
            ends = np.r_[breaks, len(lateral_bins) - 1]
            widest_run = max((lateral_bins[end] - lateral_bins[start] + 1) * resolution
                             for start, end in zip(starts, ends))
            if widest_run >= MIN_TRANSVERSE_BAND_WIDTH_M:
                broad.append(int(bin_id))
        runs = []
        for bin_id in broad:
            if not runs or bin_id > runs[-1][-1] + 1:
                runs.append([bin_id])
            else:
                runs[-1].append(bin_id)
        for run in runs:
            selected = np.isin(along_bins, run)
            band = pts[selected]
            band_along, band_across = along[selected], across[selected]
            thickness = float(np.ptp(band_along) + resolution)
            width = float(np.ptp(band_across) + resolution)
            if thickness > MAX_STOP_THICKNESS_M:
                continue
            cov = np.cov(band - band.mean(0), rowvar=False)
            major = np.linalg.eigh(cov)[1][:, -1]
            angle_error = math.degrees(math.asin(np.clip(abs(float(major @ tv)), 0.0, 1.0)))
            if width >= MIN_FRAGMENT_WIDTH_M and angle_error <= MAX_PERPENDICULAR_ERROR_DEG:
                fragments.append({"points": band, "distance": float(cumulative[idx] + np.mean(band_along)),
                                  "width": width, "thickness": thickness, "angle_error_deg": angle_error})
    crosswalk = _crosswalk_from_lane_coordinates(crosswalk_arc, crosswalk_lateral, resolution)
    if not fragments:
        return result(empty, crosswalk)
    fragments.sort(key=lambda f: f["distance"])
    groups = []
    for fragment in fragments:
        if not groups or fragment["distance"] - groups[-1][-1]["distance"] > MERGE_LONGITUDINAL_M:
            groups.append([fragment])
        else:
            groups[-1].append(fragment)
    candidates = []
    for group in groups:
        pts = np.vstack([f["points"] for f in group])
        centre = pts.mean(0)
        idx = int(cKDTree(path).query(centre)[1])
        i0, i1 = max(idx - 1, 0), min(idx + 1, len(path) - 1)
        tv = path[i1] - path[i0]
        tv /= np.linalg.norm(tv)
        nv = np.array([-tv[1], tv[0]])
        rel = pts - path[idx]
        along, across = rel @ tv, rel @ nv
        cov = np.cov(pts - centre, rowvar=False)
        major = np.linalg.eigh(cov)[1][:, -1]
        angle_error = math.degrees(math.asin(np.clip(abs(float(major @ tv)), 0.0, 1.0)))
        width = float(np.ptp(across) + resolution)
        thickness = float(np.ptp(along) + resolution)
        if width >= MIN_STOP_WIDTH_M and thickness <= MAX_STOP_THICKNESS_M and angle_error <= MAX_PERPENDICULAR_ERROR_DEG:
            distance = float(cumulative[idx] + np.mean(along))
            confidence = min(1.0, width / lane_width) * max(0.0, 1.0 - angle_error / MAX_PERPENDICULAR_ERROR_DEG)
            candidates.append({"distance": distance, "width": width, "thickness": thickness,
                               "angle_error_deg": angle_error, "confidence": confidence,
                               "fragment_count": len(group), "crosswalk": False,
                               "ambiguous": False})
    if not candidates:
        return result(empty, crosswalk)
    candidates.sort(key=lambda c: c["distance"])
    accepted = [c for c in candidates if c["distance"] >= 0.0]
    if not accepted:
        return result({**empty, "candidates": candidates}, crosswalk)
    best = min(accepted, key=lambda c: c["distance"])
    confidence = best["confidence"]
    return result({"found": True, "distance": best["distance"], "width": best["width"],
            "confidence": confidence, "ambiguous": best["ambiguous"], "thickness": best["thickness"],
            "angle_error_deg": best["angle_error_deg"], "candidates": candidates,
            }, crosswalk)
