# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ginza v2 stage 2 — gentle-lane curvature, speed limit, and Japanese sign shapes.

The truth is analytic geometry created before the operators run.  Tuning and holdout use
disjoint scene families, not merely different seeds: curve/cubic ranges, occluder
shape/count/position, illumination families, and sign ordering do not overlap.  Blur,
perspective residual, sensor noise/JPEG, flare, road wear, and sign weathering are swept
independently to expose breakdown.  No learned model, semantic image, map, or truth value
is passed to an operator.

真値はop実行前に作る解析形状で、調整用とholdoutはseedだけでなく、曲率・三次項の範囲、
隠れの形・数・位置、照明の族、標識順を分ける。ぼけ、透視残差、センサ雑音/JPEG、
フレア、路面劣化、標識の汚れを一軸ずつ強め、壊れる位置も公表する。学習モデル、
semantic画像、地図、真値ラベルをopへ渡さない。

Run / 実行::

    py -3.11 examples/poc_ginza_stage2_ops.py
    $env:CI = "1"; py -3.11 examples/poc_ginza_stage2_ops.py
    py -3.11 examples/poc_ginza_stage2_ops.py --metrics metrics.json

Set ``FULLSEYE_FIGURE_DIR`` to write first/middle/last inspection frames and a contact
sheet.  Every tuning/holdout scenario is printed and is also stored by ``--metrics``.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import fullseye as fs  # noqa: E402
import roadsign  # noqa: E402


LG = fs.ledger
TUNING_SEED = 20261124
HOLDOUT_SEED = 20261217
LANE_SHAPE = (320, 200)
LANE_RESOLUTION_M = 0.10
LANE_WIDTH_M = 3.50
CAMERA_HEIGHT_M = 1.60
LATERAL_ACCEL_LIMIT_MPS2 = 2.50
SIGN_SHAPE = (129, 129)
SIGN_PIXELS_PER_METRE = 80.0
SIGN_LABELS = ("stop_jp", "speed_limit_candidate", "no_entry", "unknown")
ACCEPT_CENTRE_P95_M = 0.30
ACCEPT_SIGN_MACRO_F1 = 0.90

# 2026-11-25に、このレビュー修正を入れる直前のcheckoutでfullを実行した値。
# Values measured by a full run of this checkout immediately before this review fix.
PRE_REVIEW_HOLDOUT = {
    "centre_error_p95_m": 0.0030961832666781338,
    "curvature_error_p95_per_m": 3.748526505883763e-05,
    "sign_macro_f1": 1.0,
    "lane_cases": 20,
    "sign_cases": 40,
}

# 公開データはカメラの光子数や読み出し雑音を公開していない。以下は公開画像に見える
# clean～破綻側を画像空間で囲むpractitioner envelopeで、センサ較正値ではない。
# Public sets do not publish photon/read-noise calibration. These are practitioner image-
# space envelopes bracketing their visible clean-to-failure side, not camera calibration.
DEGRADATION_RANGES = {
    "focus_blur": {"sigma_px": [0.0, 2.8]},
    "motion_blur": {"length_px": [1, 15]},
    "perspective": {"corner_displacement_px": [0.0, 14.0]},
    "shot_read_noise": {"photons_per_white_pixel": [1600.0, 40.0],
                         "read_noise_01": [0.0, 0.030]},
    "jpeg": {"quality": [96, 30]},
    "flare": {"veiling_luminance_01": [0.0, 0.70]},
    "road_dirt": {"covered_fraction": [0.0, 0.30]},
    "line_fade": {"contrast_loss_fraction": [0.0, 0.85]},
    "line_missing": {"missing_length_fraction": [0.0, 0.65]},
    "sign_dirt": {"covered_fraction": [0.0, 0.35]},
    "sign_occlusion": {"occluded_bbox_fraction": [0.0, 0.45]},
    "sign_fade": {"saturation_loss_fraction": [0.0, 0.85]},
}
PERTURBATION_SOURCES = [
    {
        "name": "CULane",
        "source_type": "public labelled lane-image benchmark / 公開の車線画像ベンチマーク",
        "evidence_level": "verified category frequencies; practitioner image-space strengths",
        "range_basis": ("133235 frames; test categories include no-line 11.7%, shadow 2.7%, "
                        "dazzle-light 1.4%, and curve 1.2%"),
        "url": "https://openaccess.thecvf.com/content_ICCV_2019/papers/Hou_Learning_Lightweight_Lane_Detection_CNNs_by_Self_Attention_Distillation_ICCV_2019_paper.pdf",
    },
    {
        "name": "BDD100K",
        "source_type": "public crowd-sourced dashcam video/keyframes / 公開の車載動画・代表画像",
        "evidence_level": "verified acquisition/domain range; practitioner image-space strengths",
        "range_basis": "100000 videos across weather, time-of-day, and scene types",
        "url": "https://openaccess.thecvf.com/content_CVPR_2020/papers/Yu_BDD100K_A_Diverse_Driving_Dataset_for_Heterogeneous_Multitask_Learning_CVPR_2020_paper.pdf",
    },
    {
        "name": "Mapillary Traffic Sign Dataset",
        "source_type": "public street-level traffic-sign image benchmark / 公開の道路標識画像ベンチマーク",
        "evidence_level": "verified acquisition/domain range; practitioner image-space strengths",
        "range_basis": "105000 images with varying weather and lighting across global scenes",
        "url": "https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123680069.pdf",
    },
]

LANE_AXES = ("focus_blur", "motion_blur", "perspective", "shot_read_noise", "jpeg",
             "flare", "road_dirt", "line_fade", "line_missing")
SIGN_AXES = ("focus_blur", "motion_blur", "perspective", "shot_read_noise", "jpeg",
             "flare", "sign_dirt", "sign_occlusion", "sign_fade")


def _lane_mapping():
    """BEV raster (row, col) to metric (x, y) / BEV画素からメートル座標。"""
    height, width = LANE_SHAPE
    return np.array([[LANE_RESOLUTION_M, 0.0, -0.5 * width * LANE_RESOLUTION_M],
                     [0.0, -LANE_RESOLUTION_M, (height - 1) * LANE_RESOLUTION_M],
                     [0.0, 0.0, 1.0]])


def _lane_scenarios(split, count, seed):
    """Draw from deliberately disjoint tuning/holdout scene families / 非重複の場面族。"""
    rng = np.random.default_rng(seed)
    scenarios = []
    for index in range(count):
        direction = -1.0 if index % 2 else 1.0
        if split == "tuning":
            quadratic = direction * float(rng.uniform(0.0007, 0.0022))
            cubic = 0.0
            occluder_family = "near_rectangles"
            occluder_count = int(index % 2)
            illumination_family = "horizontal_shadow"
            severity = float(rng.uniform(0.005, 0.025))
        elif split == "holdout":
            quadratic = direction * float(rng.uniform(0.0028, 0.0045))
            cubic = -direction * float(rng.uniform(1.0e-6, 4.0e-6))
            occluder_family = "far_ellipses"
            occluder_count = 1 + int(index % 3)
            illumination_family = "radial_backlight" if index % 2 else "diagonal_shadow"
            severity = float(rng.uniform(0.03, 0.065))
        else:
            raise ValueError("_lane_scenarios: split must be tuning or holdout")
        degradation = {axis: severity * float(rng.uniform(0.72, 1.0)) for axis in LANE_AXES}
        scenarios.append({
            "id": "%s-lane-%02d" % (split, index),
            "seed": int(seed + index),
            "offset_m": float(rng.uniform(-0.25, 0.25)),
            "slope": float(rng.uniform(-0.045, 0.045)),
            "quadratic": quadratic,
            "cubic": cubic,
            "gamma": float(rng.uniform(0.76, 1.28)),
            "exposure": float(rng.uniform(0.78, 1.08)),
            "shadow": float(rng.uniform(0.62, 0.88)),
            "occluder_family": occluder_family,
            "occluder_count": occluder_count,
            "illumination_family": illumination_family,
            "degradation": degradation,
        })
    return scenarios


def _centre_x(y, scenario):
    return (scenario["offset_m"] + scenario["slope"] * y
            + scenario["quadratic"] * y * y + scenario.get("cubic", 0.0) * y ** 3)


def _truth_curvature(y, scenario):
    """Signed curvature of the analytic quadratic/cubic truth / 解析真値の符号つき曲率。"""
    cubic = float(scenario.get("cubic", 0.0))
    first = scenario["slope"] + 2.0 * scenario["quadratic"] * y + 3.0 * cubic * y * y
    second = 2.0 * scenario["quadratic"] + 6.0 * cubic * y
    return second / np.power(1.0 + first * first, 1.5)


def _metric_grid():
    rows, cols = np.mgrid[0:LANE_SHAPE[0], 0:LANE_SHAPE[1]]
    mapping = _lane_mapping()
    q = np.stack([cols, rows, np.ones_like(rows)], -1) @ mapping.T
    return rows, cols, q[..., 0], q[..., 1]


def _median_label_points(labels, wanted, mapping):
    """One BEV point per observed raster row / 観測行ごとにBEV点を1点返す。"""
    points = []
    for row in range(labels.shape[0]):
        columns = np.flatnonzero(labels[row] == wanted)
        if len(columns):
            pixel = np.array([float(np.median(columns)), float(row), 1.0])
            world = mapping @ pixel
            points.append(world[:2] / world[2])
    return np.asarray(points, np.float64)


def _homography(source, target):
    """Four point projective map, row/column coordinates / 4点の行列・列射影。"""
    src = np.asarray(source, np.float64)
    dst = np.asarray(target, np.float64)
    system, values = [], []
    for (row, col), (out_row, out_col) in zip(src, dst):
        system.append([row, col, 1.0, 0.0, 0.0, 0.0, -out_row * row, -out_row * col])
        values.append(out_row)
        system.append([0.0, 0.0, 0.0, row, col, 1.0, -out_col * row, -out_col * col])
        values.append(out_col)
    h = np.r_[np.linalg.solve(np.asarray(system), np.asarray(values)), 1.0]
    return h.reshape(3, 3)


def _perspective_matrix(shape, severity, family):
    height, width = shape
    displacement = DEGRADATION_RANGES["perspective"]["corner_displacement_px"][1] * severity
    source = np.array([[0.0, 0.0], [0.0, width - 1.0],
                       [height - 1.0, width - 1.0], [height - 1.0, 0.0]])
    if family in ("horizontal_shadow", "tuning"):
        target = source + displacement * np.array([[0.0, 0.20], [0.0, -0.20],
                                                    [0.10, 0.45], [-0.10, -0.45]])
    else:
        target = source + displacement * np.array([[0.15, 0.65], [-0.15, -0.45],
                                                    [-0.35, 0.25], [0.30, -0.55]])
    return _homography(source, target)


def _transform_points(points, matrix):
    homogeneous = np.c_[points, np.ones(len(points))] @ np.asarray(matrix).T
    return homogeneous[:, :2] / homogeneous[:, 2:3]


def _warp_rgb(rgb, matrix):
    """Inverse-map RGB without resizing / RGBを逆写像し、寸法は変えない。"""
    height, width = rgb.shape[:2]
    rows, cols = np.mgrid[0:height, 0:width]
    output = np.stack([rows, cols, np.ones_like(rows)], -1).reshape(-1, 3)
    source = output @ np.linalg.inv(matrix).T
    source = source[:, :2] / source[:, 2:3]
    warped = np.empty_like(rgb)
    for channel in range(3):
        warped[..., channel] = ndimage.map_coordinates(
            rgb[..., channel], [source[:, 0], source[:, 1]], order=1,
            mode="nearest").reshape(height, width)
    return warped


def _motion_blur(rgb, severity):
    length = 1 + 2 * int(round(0.5 * (DEGRADATION_RANGES["motion_blur"]["length_px"][1] - 1) * severity))
    if length <= 1:
        return rgb
    kernel = np.zeros((length, length), np.float64)
    kernel[np.arange(length), np.arange(length)] = 1.0 / length
    return np.stack([ndimage.convolve(rgb[..., channel], kernel, mode="reflect")
                     for channel in range(3)], axis=-1)


def _sensor_noise(rgb, rng, severity):
    photons = 1600.0 / (1.0 + 39.0 * severity)
    read_sigma = DEGRADATION_RANGES["shot_read_noise"]["read_noise_01"][1] * severity
    noisy = rng.poisson(np.clip(rgb, 0.0, 1.0) * photons) / photons
    return np.clip(noisy + rng.normal(0.0, read_sigma, rgb.shape), 0.0, 1.0)


def _jpeg(rgb, severity):
    quality = int(round(96.0 - 66.0 * severity))
    buffer = io.BytesIO()
    Image.fromarray(np.rint(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)).save(
        buffer, format="JPEG", quality=quality, subsampling=2, optimize=False)
    buffer.seek(0)
    return np.asarray(Image.open(buffer).convert("RGB"), np.float64) / 255.0


def _flare(rgb, severity, *, centre_fraction):
    if severity <= 0.0:
        return rgb
    height, width = rgb.shape[:2]
    rows, cols = np.mgrid[0:height, 0:width]
    centre = np.array([centre_fraction[0] * height, centre_fraction[1] * width])
    radius = max(height, width) * (0.10 + 0.30 * severity)
    bloom = np.exp(-((rows - centre[0]) ** 2 + (cols - centre[1]) ** 2) / (2.0 * radius ** 2))
    streak = np.exp(-((rows - centre[0] - 0.18 * (cols - centre[1])) / (2.0 + 5.0 * severity)) ** 2)
    veil = np.clip(0.7 * bloom + 0.3 * streak, 0.0, 1.0)[..., None]
    strength = DEGRADATION_RANGES["flare"]["veiling_luminance_01"][1] * severity
    return np.clip(rgb * (1.0 - 0.45 * strength * veil) + strength * veil, 0.0, 1.0)


def _random_blob_mask(shape, rng, fraction, *, count):
    rows, cols = np.mgrid[0:shape[0], 0:shape[1]]
    mask = np.zeros(shape, bool)
    target = fraction * shape[0] * shape[1]
    for _ in range(max(1, count)):
        centre = (rng.uniform(0, shape[0]), rng.uniform(0, shape[1]))
        area = target / max(1, count)
        ry = max(1.0, math.sqrt(area / math.pi) * rng.uniform(0.55, 1.15))
        rx = max(1.0, area / (math.pi * ry))
        mask |= ((rows - centre[0]) / ry) ** 2 + ((cols - centre[1]) / rx) ** 2 <= 1.0
    return mask


def _lane_occlusion_mask(world_x, world_y, scenario, rng):
    mask = np.zeros(LANE_SHAPE, bool)
    count = int(scenario["occluder_count"])
    if scenario["occluder_family"] == "near_rectangles":
        for index in range(count):
            y0 = 7.0 + 3.0 * index
            mask |= (world_y >= y0) & (world_y <= y0 + 2.0) & (np.abs(world_x) <= 4.5)
    else:
        for index in range(count):
            cy = 18.0 + 4.2 * index + rng.uniform(-0.5, 0.5)
            cx = rng.uniform(-2.0, 2.0)
            mask |= ((world_y - cy) / rng.uniform(1.0, 1.8)) ** 2 + (
                (world_x - cx) / rng.uniform(1.2, 2.4)) ** 2 <= 1.0
    return mask


def _apply_lane_degradation(rgb, line_mask, scenario, rng):
    degradation = scenario["degradation"]
    dirt = _random_blob_mask(LANE_SHAPE, rng, 0.30 * degradation["road_dirt"],
                             count=2 + int(round(5 * degradation["road_dirt"])))
    dirt_colour = np.array([0.16, 0.13, 0.09])
    rgb[dirt] = 0.55 * rgb[dirt] + 0.45 * dirt_colour
    fade = 0.85 * degradation["line_fade"]
    rgb[line_mask] = (1.0 - fade) * rgb[line_mask] + fade * np.array([0.24, 0.24, 0.22])
    missing = _random_blob_mask(LANE_SHAPE, rng, 0.65 * degradation["line_missing"] * 0.08,
                                count=2 + int(round(8 * degradation["line_missing"])))
    rgb[line_mask & missing] = np.array([0.19, 0.18, 0.16])
    sigma = DEGRADATION_RANGES["focus_blur"]["sigma_px"][1] * degradation["focus_blur"]
    if sigma > 0.0:
        rgb = ndimage.gaussian_filter(rgb, sigma=(sigma, sigma, 0.0), mode="reflect")
    rgb = _motion_blur(rgb, degradation["motion_blur"])
    matrix = _perspective_matrix(LANE_SHAPE, degradation["perspective"],
                                 scenario["illumination_family"])
    rgb = _warp_rgb(rgb, matrix)
    rgb = _sensor_noise(rgb, rng, degradation["shot_read_noise"])
    rgb = _jpeg(rgb, degradation["jpeg"])
    rgb = _flare(rgb, degradation["flare"], centre_fraction=(0.16, 0.78))
    return np.clip(rgb, 0.0, 1.0), matrix


def _run_lane_case(scenario):
    rng = np.random.default_rng(scenario["seed"])
    rows, _cols, world_x, world_y = _metric_grid()
    texture = rng.normal(0.0, 0.008, (*LANE_SHAPE, 1))
    rgb = np.clip(0.18 + texture, 0.0, 1.0) * np.ones((1, 1, 3))
    centre = _centre_x(world_y, scenario)
    left = np.abs(world_x - (centre - 0.5 * LANE_WIDTH_M)) <= 0.075
    right = np.abs(world_x - (centre + 0.5 * LANE_WIDTH_M)) <= 0.075
    occluded = _lane_occlusion_mask(world_x, world_y, scenario, rng)
    left &= ~occluded
    right &= ~occluded
    rgb[left] = (0.93, 0.93, 0.93)
    rgb[right] = (0.94, 0.76, 0.05)
    if scenario["illumination_family"] == "horizontal_shadow":
        illumination = scenario["exposure"] * np.where(
            rows[..., None] < 0.55 * LANE_SHAPE[0], 1.0, scenario["shadow"])
    elif scenario["illumination_family"] == "diagonal_shadow":
        cols = np.arange(LANE_SHAPE[1])[None, :]
        diagonal = rows > 0.30 * LANE_SHAPE[0] + 0.55 * cols
        illumination = scenario["exposure"] * np.where(diagonal[..., None], scenario["shadow"], 1.0)
    else:
        radius = ((rows - 0.10 * LANE_SHAPE[0]) / LANE_SHAPE[0]) ** 2
        illumination = scenario["exposure"] * (0.72 + 0.55 * np.exp(-radius))[..., None]
    rgb = np.clip(rgb * illumination, 0.0, 1.0) ** scenario["gamma"]
    rgb, perspective = _apply_lane_degradation(rgb, left | right, scenario, rng)
    colour = LG.color_rule_mask(rgb, {})
    mapping = _lane_mapping()
    left_points = _median_label_points(colour["labels"], 1, mapping)
    right_points = _median_label_points(colour["labels"], 2, mapping)
    try:
        left_fit = LG.lane_boundary_fit(left_points, side="left", seed=scenario["seed"])
        right_fit = LG.lane_boundary_fit(right_points, side="right", seed=scenario["seed"])
        curve = LG.lane_curve_estimate(
            left_fit, right_fit, lane_width=LANE_WIDTH_M, samples=81,
            pixel_to_world=mapping, camera_height=CAMERA_HEIGHT_M, seed=scenario["seed"])
        if not curve.get("valid", False):
            raise ValueError(str(curve.get("reason", "invalid curve")))
    except (ValueError, np.linalg.LinAlgError) as exc:
        reason = ("lane pipeline rejected the degraded image: %s / 劣化画像を拒否しました: %s; "
                  "lane evidence is insufficient, so a metric answer would be unsafe / 車線根拠が不足し、"
                  "数値回答は危険です; reduce the named severity or provide a calibrated BEV crop / "
                  "該当劣化を弱めるか、較正済みBEV cropを入力してください" % (exc, exc))
        row = {**scenario, "valid": False, "reason": reason,
               "white_points": int(len(left_points)), "yellow_points": int(len(right_points))}
        artifact = {"rgb": rgb, "labels": colour["labels"], "row": row,
                    "perspective_matrix": perspective}
        return row, artifact
    y = curve["path"][:, 1]
    truth_x = _centre_x(y, scenario)
    truth_kappa = _truth_curvature(y, scenario)
    centre_error = np.abs(curve["path"][:, 0] - truth_x)
    curvature_error = np.abs(curve["curvature"] - truth_kappa)
    speed = LG.curvature_speed_plan(
        curve["arc_length"], curve["curvature"], v_max=22.0,
        a_lat_max=LATERAL_ACCEL_LIMIT_MPS2, a_accel=1.8, a_decel=2.5)
    lateral_accel = speed["v_limit"] ** 2 * np.abs(curve["curvature"])
    row = {**scenario, "valid": True,
           "centre_error_p95_m": float(np.percentile(centre_error, 95)),
           "centre_error_max_m": float(np.max(centre_error)),
           "curvature_error_p95_per_m": float(np.percentile(curvature_error, 95)),
           "curvature_error_max_per_m": float(np.max(curvature_error)),
           "estimated_curvature_min_per_m": float(np.min(curve["curvature"])),
           "estimated_curvature_max_per_m": float(np.max(curve["curvature"])),
           "speed_limit_min_mps": float(np.min(speed["v_limit"])),
           "lateral_accel_max_mps2": float(np.max(lateral_accel)),
           "white_points": int(len(left_points)), "yellow_points": int(len(right_points))}
    artifact = {"rgb": rgb, "labels": colour["labels"], "curve": curve,
                 "truth_path": np.c_[truth_x, y], "truth_kappa": truth_kappa,
                 "speed": speed, "row": row,
                 "centre_error": centre_error, "curvature_error": curvature_error,
                 "perspective_matrix": perspective}
    return row, artifact


def _regular_vertices(count, radius, angle, centre=(64.0, 64.0)):
    theta = angle + 2.0 * math.pi * np.arange(count) / count
    return np.c_[centre[0] + radius * np.cos(theta),
                 centre[1] + radius * np.sin(theta)]


def _dense_polygon(vertices, samples_per_edge=18):
    pieces = []
    for start, end in zip(vertices, np.roll(vertices, -1, axis=0)):
        t = np.arange(samples_per_edge, dtype=np.float64) / samples_per_edge
        pieces.append(start[None] * (1.0 - t[:, None]) + end[None] * t[:, None])
    return np.vstack(pieces)


def _polygon_mask(points):
    rows, cols = np.mgrid[0:SIGN_SHAPE[0], 0:SIGN_SHAPE[1]].astype(np.float64)
    rows += 0.5
    cols += 0.5
    inside = np.zeros(SIGN_SHAPE, bool)
    previous = points[-1]
    for current in points:
        r0, c0 = previous
        r1, c1 = current
        crosses = (r0 > rows) != (r1 > rows)
        at_col = (c1 - c0) * (rows - r0) / (r1 - r0 + np.finfo(float).eps) + c0
        inside ^= crosses & (cols < at_col)
        previous = current
    return inside


def _sign_scenarios(split, count, seed):
    rng = np.random.default_rng(seed)
    tuning_order = ("stop_jp", "speed_limit_candidate", "no_entry", "octagon",
                    "upright_triangle", "damaged", "low_saturation", "blank_red_circle")
    holdout_order = ("damaged", "no_entry", "upright_triangle", "stop_jp",
                     "blank_red_circle", "speed_limit_candidate", "low_saturation", "octagon")
    scenarios = []
    for index in range(count):
        if split == "tuning":
            kind = tuning_order[index % len(tuning_order)]
            illumination_family = "column_gradient"
            severity = float(rng.uniform(0.01, 0.04))
        elif split == "holdout":
            block, within = divmod(index, len(holdout_order))
            kind = holdout_order[(within + 3 * block) % len(holdout_order)]
            illumination_family = "radial_tint" if index % 2 else "diagonal_shadow"
            severity = float(rng.uniform(0.05, 0.10))
        else:
            raise ValueError("_sign_scenarios: split must be tuning or holdout")
        truth = kind if kind in SIGN_LABELS[:-1] else "unknown"
        degradation = {axis: severity * float(rng.uniform(0.72, 1.0)) for axis in SIGN_AXES}
        scenarios.append({
            "id": "%s-sign-%02d" % (split, index), "seed": int(seed + 100 + index),
            "kind": kind, "truth": truth,
            "angle_rad": float(rng.uniform(-0.18, 0.18)),
            "size_scale": float(rng.uniform(0.72, 1.28)),
            "brightness": float(rng.uniform(0.65, 1.08)),
            "gamma": float(rng.uniform(0.84, 1.18)),
            "illumination_family": illumination_family,
            "degradation": degradation,
        })
    return scenarios


def _apply_sign_degradation(rgb, points, outer, scenario):
    rng = np.random.default_rng(scenario["seed"])
    degradation = scenario["degradation"]
    fade = 0.85 * degradation["sign_fade"]
    grey = np.mean(rgb, axis=2, keepdims=True)
    rgb[outer] = (1.0 - fade) * rgb[outer] + fade * grey[outer]
    dirt = _random_blob_mask(SIGN_SHAPE, rng, 0.35 * degradation["sign_dirt"] * 0.30,
                             count=3 + int(round(10 * degradation["sign_dirt"]))) & outer
    rgb[dirt] = 0.35 * rgb[dirt] + 0.65 * np.array([0.24, 0.19, 0.11])
    occlusion = 0.45 * degradation["sign_occlusion"]
    if occlusion > 0.0:
        row_min, col_min = np.min(points, axis=0)
        row_max, col_max = np.max(points, axis=0)
        width = (col_max - col_min) * occlusion
        rr, cc = np.mgrid[0:SIGN_SHAPE[0], 0:SIGN_SHAPE[1]]
        if scenario["seed"] % 2:
            hidden = outer & (cc >= col_max - width) & (rr <= row_min + 0.72 * (row_max - row_min))
        else:
            hidden = outer & (cc <= col_min + width) & (rr >= row_min + 0.25 * (row_max - row_min))
        rgb[hidden] = np.array([0.12, 0.12, 0.12])
    sigma = DEGRADATION_RANGES["focus_blur"]["sigma_px"][1] * degradation["focus_blur"]
    if sigma > 0.0:
        rgb = ndimage.gaussian_filter(rgb, sigma=(sigma, sigma, 0.0), mode="reflect")
    rgb = _motion_blur(rgb, degradation["motion_blur"])
    matrix = _perspective_matrix(SIGN_SHAPE, degradation["perspective"],
                                 "tuning" if scenario["illumination_family"] == "column_gradient" else "holdout")
    rgb = _warp_rgb(rgb, matrix)
    points = _transform_points(points, matrix)
    rgb = _sensor_noise(rgb, rng, degradation["shot_read_noise"])
    rgb = _jpeg(rgb, degradation["jpeg"])
    rgb = _flare(rgb, degradation["flare"], centre_fraction=(0.20, 0.78))
    return np.clip(rgb, 0.0, 1.0), points, matrix


def _make_sign(scenario):
    kind = scenario["kind"]
    centre = np.array([64.0, 64.0])
    if kind in ("stop_jp", "upright_triangle"):
        radius = (roadsign.STOP_SIDE_M * SIGN_PIXELS_PER_METRE
                  / math.sqrt(3.0) * scenario["size_scale"])
        angle = scenario["angle_rad"] + (math.pi if kind == "upright_triangle" else 0.0)
        vertices = _regular_vertices(3, radius, angle)
        points = _dense_polygon(vertices)
        measured = np.linalg.norm(vertices[1] - vertices[0]) / SIGN_PIXELS_PER_METRE
        assert abs(measured - roadsign.STOP_SIDE_M * scenario["size_scale"]) < 1e-12
    elif kind in ("octagon", "damaged"):
        radius = (0.5 * roadsign.CIRCULAR_SIGN_DIAMETER_M * SIGN_PIXELS_PER_METRE
                  * scenario["size_scale"])
        vertices = _regular_vertices(8, radius, scenario["angle_rad"])
        if kind == "damaged":
            vertices[1] = centre + 0.35 * (vertices[1] - centre)
        points = _dense_polygon(vertices)
    else:
        radius = (0.5 * roadsign.CIRCULAR_SIGN_DIAMETER_M * SIGN_PIXELS_PER_METRE
                  * scenario["size_scale"])
        theta = np.linspace(0.0, 2.0 * math.pi, 129, endpoint=False)
        points = np.c_[centre[0] + radius * np.cos(theta),
                       centre[1] + radius * np.sin(theta)]
        measured = 2.0 * radius / SIGN_PIXELS_PER_METRE
        assert abs(measured - roadsign.CIRCULAR_SIGN_DIAMETER_M * scenario["size_scale"]) < 1e-12
    contour = {"shape": SIGN_SHAPE, "cs": [points]}
    outer = _polygon_mask(points)
    rgb = np.full((*SIGN_SHAPE, 3), 0.12, np.float64)
    red = np.array([0.90, 0.04, 0.04])
    white = np.array([0.94, 0.94, 0.94])
    blue = np.array([0.04, 0.12, 0.82])
    rgb[outer] = red
    rr, cc = np.mgrid[0:SIGN_SHAPE[0], 0:SIGN_SHAPE[1]]
    if kind in ("stop_jp", "upright_triangle"):
        rgb[_polygon_mask(centre + 0.84 * (points - centre))] = white
        rgb[_polygon_mask(centre + 0.72 * (points - centre))] = red
        inscription = (outer & (np.abs(rr - centre[0]) <= 2.0)
                       & (np.abs(cc - centre[1]) <= 0.42 * radius))
        rgb[inscription] = white
    elif kind == "speed_limit_candidate":
        inner = (rr - centre[0]) ** 2 + (cc - centre[1]) ** 2 <= (0.74 * radius) ** 2
        rgb[inner] = white
        ink = inner & (((np.abs(cc - (centre[1] - 0.20 * radius)) <= 0.07 * radius)
                        & (np.abs(rr - centre[0]) <= 0.42 * radius))
                       | ((np.abs(cc - (centre[1] + 0.20 * radius)) <= 0.07 * radius)
                          & (np.abs(rr - centre[0]) <= 0.42 * radius)))
        rgb[ink] = blue
    elif kind == "no_entry":
        bar = outer & (np.abs(rr - centre[0]) <= 0.13 * radius) & (np.abs(cc - centre[1]) <= 0.72 * radius)
        rgb[bar] = white
    elif kind == "low_saturation":
        rgb[outer] = (0.58, 0.46, 0.46)
    brightness = scenario["brightness"]
    if scenario["illumination_family"] == "column_gradient":
        light = np.linspace(0.92, 1.03, SIGN_SHAPE[1])[None, :, None]
    elif scenario["illumination_family"] == "diagonal_shadow":
        light = np.where(rr + 0.65 * cc < 0.88 * SIGN_SHAPE[0], 0.72, 1.04)[..., None]
    else:
        radial = ((rr - 26.0) ** 2 + (cc - 98.0) ** 2) / (SIGN_SHAPE[0] ** 2)
        light = (0.76 + 0.42 * np.exp(-radial / 0.16))[..., None] * np.array([1.05, 1.00, 0.92])
    rgb = np.clip(rgb * brightness * light, 0.0, 1.0) ** scenario["gamma"]
    rgb, points, perspective = _apply_sign_degradation(rgb, points, outer, scenario)
    contour = {"shape": SIGN_SHAPE, "cs": [points]}
    return rgb, contour, perspective


def _run_sign_case(scenario):
    rgb, contour, perspective = _make_sign(scenario)
    shape = LG.regular_shape_classify(contour)
    result = LG.road_sign_rule_classify(rgb, contour, {})
    row = {**scenario, "predicted": result["label"],
           "correct": bool(result["label"] == scenario["truth"]),
           "shape_label": shape["label"], "vertices": int(shape["vertex_count"]),
           "circularity": float(shape["circularity"]),
           "confidence": float(result["confidence"]), "reason": result["reason"]}
    return row, {"rgb": rgb, "contour": contour, "shape": shape,
                  "result": result, "row": row, "perspective_matrix": perspective}


def _macro_f1(rows):
    per_class = {}
    for label in SIGN_LABELS:
        tp = sum(row["truth"] == label and row["predicted"] == label for row in rows)
        fp = sum(row["truth"] != label and row["predicted"] == label for row in rows)
        fn = sum(row["truth"] == label and row["predicted"] != label for row in rows)
        denominator = 2 * tp + fp + fn
        per_class[label] = float(2 * tp / denominator) if denominator else 0.0
    return float(np.mean(list(per_class.values()))), per_class


def _split_metrics(lane_rows, lane_artifacts, sign_rows):
    valid_pairs = [(row, artifact) for row, artifact in zip(lane_rows, lane_artifacts)
                   if row.get("valid", False)]
    if not valid_pairs:
        raise AssertionError("all lane cases were rejected; no honest aggregate can be reported")
    valid_rows = [pair[0] for pair in valid_pairs]
    valid_artifacts = [pair[1] for pair in valid_pairs]
    centre_errors = np.concatenate([artifact["centre_error"] for artifact in valid_artifacts])
    curvature_errors = np.concatenate([artifact["curvature_error"] for artifact in valid_artifacts])
    macro_f1, class_f1 = _macro_f1(sign_rows)
    return {
        "lane_cases": len(lane_rows), "lane_samples": int(len(centre_errors)),
        "lane_valid": len(valid_rows), "lane_valid_fraction": float(len(valid_rows) / len(lane_rows)),
        "centre_error_p95_m": float(np.percentile(centre_errors, 95)),
        "centre_error_max_m": float(np.max(centre_errors)),
        "curvature_error_p95_per_m": float(np.percentile(curvature_errors, 95)),
        "curvature_error_max_per_m": float(np.max(curvature_errors)),
        "lateral_accel_max_mps2": float(max(row["lateral_accel_max_mps2"] for row in valid_rows)),
        "sign_cases": len(sign_rows), "sign_correct": int(sum(row["correct"] for row in sign_rows)),
        "sign_macro_f1": macro_f1, "sign_f1_by_class": class_f1,
    }


def _axis_scenario(base, axes, axis, severity, suffix):
    scenario = dict(base)
    scenario["id"] = base["id"] + "-" + suffix
    scenario["degradation"] = {name: (float(severity) if name == axis else 0.0)
                               for name in axes}
    return scenario


def _breakdown_curves(*, ci):
    """Sweep each corruption independently and retain failures / 各劣化を単独で強める。"""
    levels = [0.0, 0.5, 1.0] if ci else [0.0, 0.25, 0.50, 0.75, 1.0]
    lane_base = _lane_scenarios("holdout", 2 if ci else 6, HOLDOUT_SEED + 2000)
    sign_base = _sign_scenarios("holdout", 8 if ci else 40, HOLDOUT_SEED + 3000)
    lane_curves, sign_curves = {}, {}
    for axis in LANE_AXES:
        curve = []
        for level in levels:
            rows, artifacts = [], []
            for index, base in enumerate(lane_base):
                row, artifact = _run_lane_case(_axis_scenario(
                    base, LANE_AXES, axis, level, "%s-%.2f-%02d" % (axis, level, index)))
                rows.append(row)
                artifacts.append(artifact)
            valid = [(row, artifact) for row, artifact in zip(rows, artifacts)
                     if row.get("valid", False)]
            if valid:
                centre = np.concatenate([artifact["centre_error"] for _, artifact in valid])
                curvature = np.concatenate([artifact["curvature_error"] for _, artifact in valid])
                centre_p95 = float(np.percentile(centre, 95))
                curvature_p95 = float(np.percentile(curvature, 95))
                lateral = float(max(row["lateral_accel_max_mps2"] for row, _ in valid))
            else:
                centre_p95 = None
                curvature_p95 = None
                lateral = None
            valid_fraction = float(len(valid) / len(rows))
            curve.append({
                "severity": float(level), "lane_valid_fraction": valid_fraction,
                "centre_error_p95_m": centre_p95,
                "curvature_error_p95_per_m": curvature_p95,
                "lateral_accel_max_mps2": lateral,
                "gate_pass": bool(valid_fraction == 1.0 and centre_p95 is not None
                                  and centre_p95 <= ACCEPT_CENTRE_P95_M
                                  and lateral <= LATERAL_ACCEL_LIMIT_MPS2 + 1e-12),
                "rejections": [row.get("reason") for row in rows if not row.get("valid", False)],
            })
        lane_curves[axis] = curve
    for axis in SIGN_AXES:
        curve = []
        for level in levels:
            rows = []
            for index, base in enumerate(sign_base):
                row, _ = _run_sign_case(_axis_scenario(
                    base, SIGN_AXES, axis, level, "%s-%.2f-%02d" % (axis, level, index)))
                rows.append(row)
            macro_f1, class_f1 = _macro_f1(rows)
            curve.append({"severity": float(level), "macro_f1": macro_f1,
                          "f1_by_class": class_f1,
                          "correct": int(sum(row["correct"] for row in rows)),
                          "cases": len(rows), "gate_pass": bool(macro_f1 >= ACCEPT_SIGN_MACRO_F1)})
        sign_curves[axis] = curve
    first_failure = {
        "lanes": {axis: next((point["severity"] for point in curve if not point["gate_pass"]), None)
                  for axis, curve in lane_curves.items()},
        "signs": {axis: next((point["severity"] for point in curve if not point["gate_pass"]), None)
                  for axis, curve in sign_curves.items()},
    }
    return {"severity_levels": levels, "lanes": lane_curves, "signs": sign_curves,
            "first_gate_failure_severity": first_failure}


def run_suite(*, ci=False):
    lane_counts = {"tuning": 3 if ci else 12, "holdout": 4 if ci else 20}
    sign_counts = {"tuning": 8 if ci else 32, "holdout": 16 if ci else 40}
    rows = {"tuning": {"lanes": [], "signs": []},
            "holdout": {"lanes": [], "signs": []}}
    artifacts = {"tuning": {"lanes": [], "signs": []},
                 "holdout": {"lanes": [], "signs": []}}
    for split, seed in (("tuning", TUNING_SEED), ("holdout", HOLDOUT_SEED)):
        for scenario in _lane_scenarios(split, lane_counts[split], seed):
            row, artifact = _run_lane_case(scenario)
            rows[split]["lanes"].append(row)
            artifacts[split]["lanes"].append(artifact)
        for scenario in _sign_scenarios(split, sign_counts[split], seed):
            row, artifact = _run_sign_case(scenario)
            rows[split]["signs"].append(row)
            artifacts[split]["signs"].append(artifact)
    metrics = {split: _split_metrics(rows[split]["lanes"], artifacts[split]["lanes"],
                                     rows[split]["signs"])
               for split in ("tuning", "holdout")}
    breakdown = _breakdown_curves(ci=ci)
    assert metrics["holdout"]["lane_valid_fraction"] == 1.0
    assert metrics["holdout"]["centre_error_p95_m"] <= ACCEPT_CENTRE_P95_M
    assert metrics["holdout"]["sign_macro_f1"] >= ACCEPT_SIGN_MACRO_F1
    assert metrics["tuning"]["lateral_accel_max_mps2"] <= LATERAL_ACCEL_LIMIT_MPS2 + 1e-12
    assert metrics["holdout"]["lateral_accel_max_mps2"] <= LATERAL_ACCEL_LIMIT_MPS2 + 1e-12
    payload = {
        "mode": "ci" if ci else "full", "seeds": {"tuning": TUNING_SEED, "holdout": HOLDOUT_SEED},
        "scene_family_separation": {
            "lane_curve": {"tuning": "quadratic |q| in [0.0007,0.0022], cubic=0",
                           "holdout": "|q| in [0.0028,0.0045], opposing cubic |c| in [1e-6,4e-6]"},
            "lane_occlusion": {"tuning": "0 or 1 near rectangle at y=7..12 m",
                               "holdout": "1..3 far ellipses at y=18..28 m"},
            "illumination": {"tuning": ["horizontal_shadow"],
                             "holdout": ["diagonal_shadow", "radial_backlight/radial_tint"]},
            "sign_order": {"tuning": list(("stop_jp", "speed_limit_candidate", "no_entry", "octagon",
                                             "upright_triangle", "damaged", "low_saturation", "blank_red_circle")),
                           "holdout": "different permutation, rotated by three each eight-case block"},
            "degradation_severity": {
                "lane_tuning": [0.005, 0.025], "lane_holdout": [0.03, 0.065],
                "sign_tuning": [0.01, 0.04], "sign_holdout": [0.05, 0.10]},
        },
        "perturbation_sources": PERTURBATION_SOURCES,
        "degradation_ranges": DEGRADATION_RANGES,
        "acceptance": {"centre_error_p95_m_max": ACCEPT_CENTRE_P95_M,
                       "holdout_sign_macro_f1_min": ACCEPT_SIGN_MACRO_F1,
                       "lateral_accel_mps2_max": LATERAL_ACCEL_LIMIT_MPS2},
        "calibration": {"camera_height_m": CAMERA_HEIGHT_M,
                        "bev_pixel_to_world": _lane_mapping().tolist()},
        "normative_source": {"law_id": roadsign.EGOV_LAW_ID,
                             "revision_id": roadsign.EGOV_REVISION_ID,
                             "url": roadsign.EGOV_SOURCE_URL,
                             "checked": "2026-11-25",
                             "stop_side_m": roadsign.STOP_SIDE_M,
                             "circular_sign_diameter_m": roadsign.CIRCULAR_SIGN_DIAMETER_M,
                             "legal_scale": [roadsign.LEGAL_DIMENSION_MIN_SCALE,
                                             roadsign.LEGAL_DIMENSION_MAX_SCALE]},
        "metrics": metrics,
        "comparison": {"before_review_measured": PRE_REVIEW_HOLDOUT,
                       "after_review_measured": metrics["holdout"]},
        "breakdown": breakdown, "rows": rows,
    }
    return payload, artifacts


def _draw_path(image, points, colour, radius=1):
    from scipy import ndimage

    out = np.asarray(image, np.float64).copy()
    mapping = _lane_mapping()
    inverse = np.linalg.inv(mapping)
    homogeneous = np.c_[points, np.ones(len(points))] @ inverse.T
    cols = np.rint(homogeneous[:, 0] / homogeneous[:, 2]).astype(int)
    rows = np.rint(homogeneous[:, 1] / homogeneous[:, 2]).astype(int)
    valid = ((rows >= 0) & (rows < out.shape[0]) & (cols >= 0) & (cols < out.shape[1]))
    mask = np.zeros(out.shape[:2], bool)
    mask[rows[valid], cols[valid]] = True
    if radius:
        mask = ndimage.binary_dilation(mask, iterations=radius)
    out[mask] = colour
    return out


def _label_image(labels):
    out = np.full((*labels.shape, 3), 0.08, np.float64)
    out[labels == 1] = (0.96, 0.96, 0.96)
    out[labels == 2] = (0.95, 0.72, 0.05)
    return out


def _pad_panel(panel, shape=(360, 600)):
    """Centre data without resampling / データを補間せず余白の中央へ置く。"""
    image = np.asarray(panel, np.float64)
    height, width = image.shape[:2]
    if height > shape[0] or width > shape[1]:
        raise ValueError("panel %r is larger than the fixed figure cell %r" % ((height, width), shape))
    out = np.ones((*shape, 3), np.float64)
    row = (shape[0] - height) // 2
    col = (shape[1] - width) // 2
    out[row:row + height, col:col + width] = image[..., :3]
    return out


def _sign_strip(sign_artifacts, supported):
    selected = []
    wanted = SIGN_LABELS[:-1] if supported else ("octagon", "upright_triangle", "damaged")
    for wanted_label in wanted:
        for artifact in sign_artifacts:
            key = artifact["row"]["truth"] if supported else artifact["row"]["kind"]
            if key == wanted_label:
                selected.append(artifact["rgb"])
                break
    separator = np.ones((SIGN_SHAPE[0], 4, 3), np.float64)
    pieces = []
    for index, panel in enumerate(selected):
        if index:
            pieces.append(separator)
        pieces.append(panel)
    return np.concatenate(pieces, axis=1)


def _speed_card(lane_artifact):
    """Large-text same-run speed result / 同じ実行の速度結果を大字で示す。"""
    speed = lane_artifact["speed"]
    curvature = lane_artifact["curve"]["curvature"]
    maximum = float(np.max(speed["v_limit"] ** 2 * np.abs(curvature)))
    minimum_speed = float(np.min(speed["v_limit"]))
    card = np.ones((360, 600, 3), np.float64)
    lines = (
        ("Curve speed / カーブ速度", 34),
        ("min limit  %.2f m/s" % minimum_speed, 30),
        ("max v²|kappa|  %.3f" % maximum, 30),
        ("truth bound  <= %.3f m/s²" % LATERAL_ACCEL_LIMIT_MPS2, 30),
    )
    for index, (label, font_size) in enumerate(lines):
        card = np.asarray(fs.text_box(
            card, label, (28, 28 + 78 * index), anchor="lt", font_size=font_size))
    return card


def _status_card(title, lines):
    """Readable result card kept off the data / データに重ねない結果札。"""
    card = np.ones((360, 600, 3), np.float64)
    card = np.asarray(fs.text_box(card, title, (24, 24), anchor="lt", font_size=32))
    for index, line in enumerate(lines):
        card = np.asarray(fs.text_box(card, line, (24, 96 + 58 * index),
                                     anchor="lt", font_size=25))
    return card


def _frame_panels(figs, lane_artifact, sign_artifacts, metrics):
    curve = lane_artifact["curve"]
    overlay = _draw_path(lane_artifact["rgb"], lane_artifact["truth_path"], (0.10, 0.35, 0.95), 2)
    overlay = _draw_path(overlay, curve["path"], (0.10, 0.78, 0.30), 1)
    speed_plot = _speed_card(lane_artifact)
    title_metrics = ("centre p95 %.3f m / sign macro F1 %.3f"
                     % (metrics["centre_error_p95_m"], metrics["sign_macro_f1"]))
    panels = [_pad_panel(panel) for panel in
              (lane_artifact["rgb"], _label_image(lane_artifact["labels"]), overlay,
               speed_plot, _sign_strip(sign_artifacts, True), _sign_strip(sign_artifacts, False))]
    captions = ["input RGB / 入力", "colour masks / 白・黄",
                "truth=blue, fit=green", "v²|kappa| <= 2.50",
                "JP 330-A / 323 / 303", "reject: octagon / upright / damage"]
    return panels, captions, title_metrics


def render_figures(payload, artifacts):
    if not os.environ.get("FULLSEYE_FIGURE_DIR", "").strip():
        return []
    import examplefig as figs

    written = []
    frames = [
        ("first", artifacts["tuning"]["lanes"][0], artifacts["tuning"]["signs"],
         payload["metrics"]["tuning"]),
        ("middle", artifacts["holdout"]["lanes"][len(artifacts["holdout"]["lanes"]) // 2],
         artifacts["holdout"]["signs"], payload["metrics"]["holdout"]),
        ("last", artifacts["holdout"]["lanes"][-1], artifacts["holdout"]["signs"],
         payload["metrics"]["holdout"]),
    ]
    contact_panels = []
    contact_captions = []
    for name, lane_artifact, sign_artifacts, metrics in frames:
        panels, captions, title_metrics = _frame_panels(figs, lane_artifact, sign_artifacts, metrics)
        path = figs.save_grid(
            name, panels, captions=captions, ncols=3,
            title="Ginza v2 stage 2 — %s — %s" % (name, title_metrics),
            caption=("Same-run input -> output -> analytic truth. Japanese sign dimensions/colours: "
                     "e-Gov Appended Table 2, revision %s." % roadsign.EGOV_REVISION_ID),
            font_size=32, min_font_size=30, caption_h=76)
        if path is not None:
            written.append(str(path))
        contact_panels.extend([panels[2], panels[4], panels[5]])
        contact_captions.extend([name + " lane", name + " supported", name + " failures"])
    path = figs.save_grid(
        "contact_sheet", contact_panels, captions=contact_captions, ncols=3,
        title=("Contact sheet / 検分一覧 — holdout centre p95 %.3f m, sign macro F1 %.3f"
               % (payload["metrics"]["holdout"]["centre_error_p95_m"],
                  payload["metrics"]["holdout"]["sign_macro_f1"])),
        caption="First / middle / last: input-output-truth plus the supported and rejected sign sides.",
        font_size=32, min_font_size=30, caption_h=76)
    if path is not None:
        written.append(str(path))
    levels = np.asarray(payload["breakdown"]["severity_levels"], np.float64)
    lane_series = []
    for axis in LANE_AXES:
        values = [point["centre_error_p95_m"] if point["centre_error_p95_m"] is not None
                  else np.nan for point in payload["breakdown"]["lanes"][axis]]
        lane_series.append((axis, levels, np.asarray(values, np.float64)))
    lane_series.append(("gate 0.30 m", levels, np.full(len(levels), ACCEPT_CENTRE_P95_M)))
    path = figs.save_plot(
        "breakdown_lane_error", lane_series, xlabel="severity / 劣化強さ",
        ylabel="centre p95 [m]", title="Lane breakdown / 車線の崩れ方",
        caption=("Each perturbation is swept alone on the disjoint holdout family. Missing points are "
                 "explicit rejections; see breakdown_lane_valid. / 各劣化を単独で強め、欠点は拒否。"),
        size=(1000, 540), xlim=(0.0, 1.0), ylim=(0.0, 0.45), scale=2,
        styles=[None] * len(LANE_AXES) + ["dashed"],
        colors=[None] * len(LANE_AXES) + ["reference"],
        source="CULane/BDD100K category-bracketed practitioner image-space envelope")
    if path is not None:
        written.append(str(path))
    lane_valid_series = [
        (axis, levels, np.asarray([point["lane_valid_fraction"]
                                  for point in payload["breakdown"]["lanes"][axis]]))
        for axis in LANE_AXES]
    path = figs.save_plot(
        "breakdown_lane_valid", lane_valid_series, xlabel="severity / 劣化強さ",
        ylabel="valid fraction / 有効率", title="Lane fail-closed curve / 車線の拒否率",
        caption="A rejected case is not hidden from the centre-error curve. / 拒否例を誤差集計から隠さない。",
        size=(1000, 540), xlim=(0.0, 1.0), ylim=(0.0, 1.05), scale=2,
        source="CULane/BDD100K category-bracketed practitioner image-space envelope")
    if path is not None:
        written.append(str(path))
    sign_series = [
        (axis, levels, np.asarray([point["macro_f1"]
                                  for point in payload["breakdown"]["signs"][axis]]))
        for axis in SIGN_AXES]
    sign_series.append(("gate 0.90", levels, np.full(len(levels), ACCEPT_SIGN_MACRO_F1)))
    path = figs.save_plot(
        "breakdown_sign_f1", sign_series, xlabel="severity / 劣化強さ",
        ylabel="macro F1", title="Sign breakdown / 標識の崩れ方",
        caption="Each perturbation is swept alone; every prediction, including unknown, is scored.",
        size=(1000, 540), xlim=(0.0, 1.0), ylim=(0.0, 1.05), scale=2,
        styles=[None] * len(SIGN_AXES) + ["dashed"],
        colors=[None] * len(SIGN_AXES) + ["reference"],
        source="Mapillary Traffic Sign Dataset category-bracketed practitioner image-space envelope")
    if path is not None:
        written.append(str(path))

    lane_row = None
    lane_failure = None
    for base in _lane_scenarios("holdout", 6, HOLDOUT_SEED + 2000):
        row, artifact = _run_lane_case(_axis_scenario(
            base, LANE_AXES, "perspective", 1.0, "figure-failure"))
        if (lane_row is None or not row.get("valid", False)
                or (row.get("centre_error_p95_m", -1.0)
                    > lane_row.get("centre_error_p95_m", -1.0))):
            lane_row, lane_failure = row, artifact
        if not row.get("valid", False):
            break
    sign_failure = None
    sign_row = None
    for base in _sign_scenarios("holdout", 40, HOLDOUT_SEED + 3000):
        row, artifact = _run_sign_case(_axis_scenario(
            base, SIGN_AXES, "motion_blur", 0.75, "figure-failure"))
        if not row["correct"]:
            sign_row, sign_failure = row, artifact
            break
    if sign_failure is None:
        raise RuntimeError("no sign failure was found for the declared motion-blur breakdown frame")
    lane_lines = (["valid: no / 拒否", "severity 1.00 perspective"] if not lane_row["valid"]
                  else ["centre p95 %.3f m" % lane_row["centre_error_p95_m"],
                        "gate <= %.2f m: %s" % (ACCEPT_CENTRE_P95_M,
                                                "PASS" if lane_row["centre_error_p95_m"] <= ACCEPT_CENTRE_P95_M else "FAIL")])
    failure_panels = [
        _pad_panel(lane_failure["rgb"]), _pad_panel(_label_image(lane_failure["labels"])),
        _status_card("Perspective residual / 透視残差", lane_lines),
        _pad_panel(sign_failure["rgb"]),
        _status_card("Motion blur / 動きぼけ", ["truth: " + sign_row["truth"],
                                                   "output: " + sign_row["predicted"],
                                                   "severity 0.75: FAIL"]),
        _status_card("Honest limit / 限界", ["no learning / 学習なし",
                                               "unknown is scored",
                                               "failures stay in JSON"]),
    ]
    path = figs.save_grid(
        "breakdown_failure", failure_panels,
        captions=["lane input", "lane output mask", "lane vs truth",
                  "sign input", "sign output vs truth", "reported limit"], ncols=3,
        title="Failure side / 壊れる側 — same-run input -> output -> truth",
        caption="Holdout-only scene family; the displayed values are recomputed in this figure run.",
        font_size=32, min_font_size=30, caption_h=76)
    if path is not None:
        written.append(str(path))
    if figs.errors():
        raise RuntimeError("figure generation failed: %s" % "; ".join(figs.errors()))
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--metrics", type=Path, help="write the printed metrics and all rows as UTF-8 JSON")
    args = parser.parse_args(argv)
    start = time.perf_counter()
    ci = os.environ.get("CI", "") == "1"
    payload, artifacts = run_suite(ci=ci)
    # 公開する結果ファイルに手元の絶対パスを残さない: 図の場所は FULLSEYE_FIGURE_DIR からの名前だけを記録する。
    payload["figures"] = [os.path.basename(path) for path in render_figures(payload, artifacts)]
    payload["runtime_seconds"] = float(time.perf_counter() - start)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    print(text)
    if args.metrics is not None:
        args.metrics.parent.mkdir(parents=True, exist_ok=True)
        args.metrics.write_text(text + "\n", encoding="utf-8")
    print("PASS: Ginza v2 stage-2 operators meet the synthetic tuning/holdout gates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
