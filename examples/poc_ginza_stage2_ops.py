# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ginza v2 stage 2 — gentle-lane curvature, speed limit, and Japanese sign shapes.

The truth is analytic geometry created before the operators run.  Tuning and holdout use
different scenario seeds.  No learned model, semantic image, map, or truth value is passed
to an operator.

真値はop実行前に作る解析形状で、調整用とholdoutはシナリオseedを分ける。学習モデル、
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
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

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


def _lane_mapping():
    """BEV raster (row, col) to metric (x, y) / BEV画素からメートル座標。"""
    height, width = LANE_SHAPE
    return np.array([[LANE_RESOLUTION_M, 0.0, -0.5 * width * LANE_RESOLUTION_M],
                     [0.0, -LANE_RESOLUTION_M, (height - 1) * LANE_RESOLUTION_M],
                     [0.0, 0.0, 1.0]])


def _lane_scenarios(split, count, seed):
    rng = np.random.default_rng(seed)
    scenarios = []
    for index in range(count):
        quadratic = float(rng.uniform(-0.0038, 0.0038))
        if abs(quadratic) < 0.0007:
            quadratic = math.copysign(0.0007, quadratic if quadratic else 1.0)
        scenarios.append({
            "id": "%s-lane-%02d" % (split, index),
            "seed": int(seed + index),
            "offset_m": float(rng.uniform(-0.25, 0.25)),
            "slope": float(rng.uniform(-0.045, 0.045)),
            "quadratic": quadratic,
            "gamma": float(rng.uniform(0.76, 1.28)),
            "exposure": float(rng.uniform(0.78, 1.08)),
            "shadow": float(rng.uniform(0.62, 0.88)),
            "occluded": bool(index % 3 == 1),
        })
    return scenarios


def _centre_x(y, scenario):
    return (scenario["offset_m"] + scenario["slope"] * y
            + scenario["quadratic"] * y * y)


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


def _run_lane_case(scenario):
    rng = np.random.default_rng(scenario["seed"])
    rows, _cols, world_x, world_y = _metric_grid()
    texture = rng.normal(0.0, 0.008, (*LANE_SHAPE, 1))
    rgb = np.clip(0.18 + texture, 0.0, 1.0) * np.ones((1, 1, 3))
    centre = _centre_x(world_y, scenario)
    left = np.abs(world_x - (centre - 0.5 * LANE_WIDTH_M)) <= 0.075
    right = np.abs(world_x - (centre + 0.5 * LANE_WIDTH_M)) <= 0.075
    if scenario["occluded"]:
        gap = (world_y >= 12.0) & (world_y <= 16.0)
        left &= ~gap
        right &= ~gap
    rgb[left] = (0.93, 0.93, 0.93)
    rgb[right] = (0.94, 0.76, 0.05)
    illumination = scenario["exposure"] * np.where(
        rows[..., None] < 0.55 * LANE_SHAPE[0], 1.0, scenario["shadow"])
    rgb = np.clip(rgb * illumination, 0.0, 1.0) ** scenario["gamma"]
    colour = LG.color_rule_mask(rgb, {})
    mapping = _lane_mapping()
    left_points = _median_label_points(colour["labels"], 1, mapping)
    right_points = _median_label_points(colour["labels"], 2, mapping)
    left_fit = LG.lane_boundary_fit(left_points, side="left", seed=scenario["seed"])
    right_fit = LG.lane_boundary_fit(right_points, side="right", seed=scenario["seed"])
    curve = LG.lane_curve_estimate(
        left_fit, right_fit, lane_width=LANE_WIDTH_M, samples=81,
        pixel_to_world=mapping, camera_height=CAMERA_HEIGHT_M, seed=scenario["seed"])
    y = curve["path"][:, 1]
    truth_x = _centre_x(y, scenario)
    truth_kappa = (2.0 * scenario["quadratic"]
                   / np.power(1.0 + (scenario["slope"]
                                     + 2.0 * scenario["quadratic"] * y) ** 2, 1.5))
    centre_error = np.abs(curve["path"][:, 0] - truth_x)
    curvature_error = np.abs(curve["curvature"] - truth_kappa)
    speed = LG.curvature_speed_plan(
        curve["arc_length"], curve["curvature"], v_max=22.0,
        a_lat_max=LATERAL_ACCEL_LIMIT_MPS2, a_accel=1.8, a_decel=2.5)
    lateral_accel = speed["v_limit"] ** 2 * np.abs(curve["curvature"])
    row = {**scenario,
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
                "centre_error": centre_error, "curvature_error": curvature_error}
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
    kinds = ("stop_jp", "speed_limit_candidate", "no_entry", "octagon",
             "upright_triangle", "damaged", "low_saturation", "blank_red_circle")
    scenarios = []
    for index in range(count):
        kind = kinds[index % len(kinds)]
        truth = kind if kind in SIGN_LABELS[:-1] else "unknown"
        scenarios.append({
            "id": "%s-sign-%02d" % (split, index), "seed": int(seed + 100 + index),
            "kind": kind, "truth": truth,
            "angle_rad": float(rng.uniform(-0.18, 0.18)),
            "size_scale": float(rng.uniform(0.72, 1.28)),
            "brightness": float(rng.uniform(0.65, 1.08)),
            "gamma": float(rng.uniform(0.84, 1.18)),
        })
    return scenarios


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
    column_light = np.linspace(0.92, 1.03, SIGN_SHAPE[1])[None, :, None]
    rgb = np.clip(rgb * brightness * column_light, 0.0, 1.0) ** scenario["gamma"]
    return rgb, contour


def _run_sign_case(scenario):
    rgb, contour = _make_sign(scenario)
    shape = LG.regular_shape_classify(contour)
    result = LG.road_sign_rule_classify(rgb, contour, {})
    row = {**scenario, "predicted": result["label"],
           "correct": bool(result["label"] == scenario["truth"]),
           "shape_label": shape["label"], "vertices": int(shape["vertex_count"]),
           "circularity": float(shape["circularity"]),
           "confidence": float(result["confidence"]), "reason": result["reason"]}
    return row, {"rgb": rgb, "contour": contour, "shape": shape,
                 "result": result, "row": row}


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
    centre_errors = np.concatenate([artifact["centre_error"] for artifact in lane_artifacts])
    curvature_errors = np.concatenate([artifact["curvature_error"] for artifact in lane_artifacts])
    macro_f1, class_f1 = _macro_f1(sign_rows)
    return {
        "lane_cases": len(lane_rows), "lane_samples": int(len(centre_errors)),
        "centre_error_p95_m": float(np.percentile(centre_errors, 95)),
        "centre_error_max_m": float(np.max(centre_errors)),
        "curvature_error_p95_per_m": float(np.percentile(curvature_errors, 95)),
        "curvature_error_max_per_m": float(np.max(curvature_errors)),
        "lateral_accel_max_mps2": float(max(row["lateral_accel_max_mps2"] for row in lane_rows)),
        "sign_cases": len(sign_rows), "sign_correct": int(sum(row["correct"] for row in sign_rows)),
        "sign_macro_f1": macro_f1, "sign_f1_by_class": class_f1,
    }


def run_suite(*, ci=False):
    lane_counts = {"tuning": 3 if ci else 12, "holdout": 4 if ci else 20}
    sign_counts = {"tuning": 8 if ci else 32, "holdout": 8 if ci else 40}
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
    assert metrics["holdout"]["centre_error_p95_m"] <= ACCEPT_CENTRE_P95_M
    assert metrics["holdout"]["sign_macro_f1"] >= ACCEPT_SIGN_MACRO_F1
    assert metrics["tuning"]["lateral_accel_max_mps2"] <= LATERAL_ACCEL_LIMIT_MPS2 + 1e-12
    assert metrics["holdout"]["lateral_accel_max_mps2"] <= LATERAL_ACCEL_LIMIT_MPS2 + 1e-12
    payload = {
        "mode": "ci" if ci else "full", "seeds": {"tuning": TUNING_SEED, "holdout": HOLDOUT_SEED},
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
        "metrics": metrics, "rows": rows,
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
    payload["figures"] = render_figures(payload, artifacts)
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
