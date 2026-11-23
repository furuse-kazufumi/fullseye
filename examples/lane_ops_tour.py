# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lane_ops_tour — 白・黄の車線と停止線を学習なしの5 opで読む数値正解例。

    py -3.11 examples/lane_ops_tour.py
    py -3.11 examples/lane_ops_tour.py --full

縮小/完全の両モードで、照明とgamma、投影格子、曲線+外れ値+遮蔽、片側境界、
停止線の回転+遮蔽、横断歩道の棄却を、合成時に置いた真値と比較する。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import fullseye as fs  # noqa: E402

LG = fs.ledger
SEED = 20261123
HOLDOUT_SEED = 20261125


def colour_gate(full):
    gammas = np.linspace(0.70, 1.45, 9 if full else 3)
    shadow_levels = np.linspace(0.50, 1.0, 7 if full else 2)
    recall, false_positive = [], []
    for gamma in gammas:
        for shadow in shadow_levels:
            rgb = np.full((80, 120, 3), 0.20)
            rgb[:, 20:25] = (0.92, 0.92, 0.92)
            rgb[:, 95:100] = (0.92, 0.76, 0.06)
            rgb[:, :60] *= shadow
            rgb = np.clip(rgb, 0.0, 1.0) ** gamma
            out = LG.color_rule_mask(rgb, {})
            truth = np.zeros((80, 120), np.int16)
            truth[:, 20:25], truth[:, 95:100] = 1, 2
            recall.append(np.mean(out["labels"][truth > 0] == truth[truth > 0]))
            false_positive.append(np.mean(out["labels"][truth == 0] != 0))
    return float(min(recall)), float(max(false_positive)), len(recall)


def projection_gate():
    rows, cols = np.mgrid[0:101, 0:101]
    rgb = np.stack([cols / 100.0, rows / 100.0, np.full(rows.shape, 0.25)], -1)
    K = np.array([[100.0, 0.0, 50.0], [0.0, 100.0, 50.0], [0.0, 0.0, 1.0]])
    R = np.diag([1.0, -1.0, -1.0]); C = np.array([0.0, 0.0, 10.0])
    out = LG.plane_topview_color(rgb, K, R, -R @ C, extent=10.0, res=0.1)
    truth = np.stack([out["image_col"] / 100.0, out["image_row"] / 100.0,
                      np.full(out["image_row"].shape, 0.25)], -1)
    return float(np.max(np.abs(out["rgb"] - truth)))


def boundary_gate(full):
    rng = np.random.default_rng(SEED)
    truth = np.array([-1.75, 0.035, 0.0015])
    errors, shuffled = [], []
    for _ in range(40 if full else 6):
        y = np.linspace(0.0, 25.0, 126)
        keep = (y < 8.0) | (y > 14.0)
        y = y[keep]
        x = truth[0] + truth[1] * y + truth[2] * y*y + rng.normal(0.0, 0.018, len(y))
        pts = np.vstack([np.c_[x, y], np.c_[rng.uniform(-5, 5, 24), rng.uniform(0, 25, 24)]])
        fit = LG.lane_boundary_fit(pts, side="left", seed=17)
        perm = pts[rng.permutation(len(pts))]
        fit2 = LG.lane_boundary_fit(perm, side="left", seed=17)
        yy = np.linspace(0.0, 25.0, 101)
        errors.append(np.max(np.abs(np.polynomial.polynomial.polyval(yy, fit["coefficients"])
                                    - np.polynomial.polynomial.polyval(yy, truth))))
        shuffled.append(np.max(np.abs(fit["coefficients"] - fit2["coefficients"])))
    right = {"valid": True, "coefficients": truth + np.array([3.5, 0.0, 0.0]),
             "observed_y": np.array([0.0, 25.0]), "confidence": 0.95}
    left = {"valid": True, "coefficients": truth, "observed_y": np.array([0.0, 25.0]), "confidence": 0.95}
    both = LG.lane_center_path(left, right)
    one = LG.lane_center_path(left, None)
    centre_delta = float(np.max(np.abs(both["path"] - one["path"])))
    return float(max(errors)), float(max(shuffled)), centre_delta, both["confidence"], one["confidence"]


def stop_gate(full):
    angles = np.linspace(-15.0, 15.0, 31 if full else 5)
    errors, rejected = [], []
    for angle in angles:
        h, w, res = 401, 181, 0.05
        H = np.array([[res, 0.0, -4.5], [0.0, -res, 20.0], [0.0, 0.0, 1.0]])
        rows, cols = np.mgrid[0:h, 0:w]
        q = np.stack([cols, rows, np.ones_like(rows)], -1) @ H.T
        world = q[..., :2]
        theta = np.radians(angle)
        tangent = np.array([np.sin(theta), np.cos(theta)])
        normal = np.array([-tangent[1], tangent[0]])
        along, across = world @ tangent, world @ normal
        labels = np.zeros((h, w), np.int16)
        stop = (np.abs(along - 8.0) <= 0.15) & (np.abs(across) <= 1.60)
        stop &= ~((across > -0.25) & (across < 0.35))
        labels[stop] = 1
        for lateral in (-1.2, -0.4, 0.4, 1.2):
            labels[(np.abs(across - lateral) <= 0.15) & (along >= 12.0) & (along <= 15.0)] = 1
        ss = np.linspace(0.0, 20.0, 201)
        lane = {"path": ss[:, None] * tangent, "lane_width": 3.5, "pixel_to_world": H}
        got = LG.stop_line_detect(labels, lane)
        if not got["found"]:
            raise AssertionError("stop line was missed at angle %.1f deg" % angle)
        errors.append(abs(got["distance"] - 8.0))
        rejected.append(got["rejected_crosswalk"])
    return float(max(errors)), min(rejected), len(angles)


def holdout_stop_gate(full):
    """固定層の独立seed合成holdout。実道路の精度ではなく生成器内の頑健性だけを測る。"""
    rng = np.random.default_rng(HOLDOUT_SEED)
    count = 12 if full else 3
    h, w, res = 401, 161, 0.05
    H_truth = np.array([[res, 0.0, -4.0], [0.0, -res, 20.0], [0.0, 0.0, 1.0]])
    rows, cols = np.mgrid[0:h, 0:w]
    q = np.stack([cols, rows, np.ones_like(rows)], -1) @ H_truth.T
    world = q[..., :2]
    layers = (
        ("clear_stop", True, (-1.2, -0.4, 0.4, 1.2), False, "none"),
        ("stop_plus_japan_crosswalk", True, (-1.2, -0.4, 0.4, 1.2), True, "none"),
        ("crosswalk_all_stripes", False, (-1.2, -0.4, 0.4, 1.2), True, "none"),
        ("crosswalk_one_or_two_stripes", False, None, True, "none"),
        # These change actual observed labels after RGB classification; they are not labels only.
        ("occlusion_mask", True, (-1.2, -0.4, 0.4, 1.2), True, "occlusion_mask"),
        ("image_edge_crop", True, (-1.2, -0.4, 0.4, 1.2), True, "image_edge_crop"),
        ("local_shadow", True, (-1.2, -0.4, 0.4, 1.2), True, "local_shadow"),
    )
    rows_out = []
    for layer, has_stop, stripe_spec, has_crosswalk, degradation in layers:
        found, confidence, ambiguous, crosswalk_found, crosswalk_confidence, stripe_counts, errors = [], [], [], [], [], [], []
        for case in range(count):
            # 格子=画素量子化、ぼけ、露出/色ずれ、白飛び、路面texture、校正誤差を同時に掛ける。
            texture = rng.normal(0.0, 0.025, (h, w, 1)) + 0.018 * np.sin(world[..., 1:2] * 2.3)
            rgb = np.clip(0.22 + texture + rng.uniform(-0.025, 0.025, (1, 1, 3)), 0.0, 1.0)
            if has_stop:
                stop = (np.abs(world[..., 1] - 8.0) <= 0.15) & (np.abs(world[..., 0]) <= 1.55)
                rgb[stop] = 1.05
            if has_crosswalk:
                stripes = stripe_spec if stripe_spec is not None else ((-0.4,) if case % 2 == 0 else (-1.2, 1.2))
                for lateral in stripes:
                    stripe = ((np.abs(world[..., 0] - lateral) <= 0.15)
                              & (world[..., 1] >= 8.7) & (world[..., 1] <= 11.5))
                    rgb[stripe] = 1.05
            rgb = ndimage.gaussian_filter(rgb, sigma=(rng.uniform(0.25, 0.55), rng.uniform(0.25, 0.55), 0.0))
            rgb *= rng.uniform(0.88, 1.16) * rng.uniform(0.97, 1.03, (1, 1, 3))
            rgb[:, :w // 3] *= rng.uniform(0.72, 0.86)  # shadow
            rgb = np.clip(rgb, 0.0, 1.0)  # white clipping
            labels = LG.color_rule_mask(rgb, {})["labels"]
            if degradation == "occlusion_mask":
                labels[(np.abs(world[..., 1] - 8.0) <= 0.15) & (np.abs(world[..., 0]) < 0.28)] = 0
            elif degradation == "image_edge_crop":
                labels[:, :w // 4] = 0
            elif degradation == "local_shadow":
                labels[(world[..., 1] >= 10.0) & (world[..., 1] <= 10.8)
                       & (world[..., 0] >= -0.55) & (world[..., 0] <= -0.25)] = 0
            H_detector = H_truth.copy()
            H_detector[0, 2] += rng.uniform(-0.03, 0.03)
            H_detector[1, 2] += rng.uniform(-0.04, 0.04)
            lane = {"path": np.c_[np.zeros(201), np.linspace(0.0, 20.0, 201)],
                    "lane_width": 3.5, "pixel_to_world": H_detector}
            got = LG.stop_line_detect(labels, lane)
            found.append(bool(got["found"]))
            confidence.append(float(got["confidence"]))
            ambiguous.append(bool(got["ambiguous"]))
            crosswalk_found.append(bool(got["crosswalk_found"]))
            crosswalk_confidence.append(float(got["crosswalk_confidence"]))
            stripe_counts.append(int(got["crosswalk_stripe_count"]))
            if has_stop and got["found"]:
                errors.append(abs(got["distance"] - 8.0))
        rows_out.append({"layer": layer, "cases": count, "has_stop": has_stop,
                         "found": int(sum(found)), "confidence_mean": float(np.mean(confidence)),
                         "confidence_max": float(np.max(confidence)), "ambiguous": int(sum(ambiguous)),
                         "crosswalk_found": int(sum(crosswalk_found)),
                         "crosswalk_confidence_mean": float(np.mean(crosswalk_confidence)),
                         "crosswalk_stripes_min": int(min(stripe_counts)),
                         "max_distance_error": float(max(errors)) if errors else float("nan")})
    stop_layers = [row for row in rows_out if row["has_stop"]]
    no_stop_layers = [row for row in rows_out if not row["has_stop"]]
    crosswalk_layers = [row for row, spec in zip(rows_out, layers) if spec[3]]
    gates = (all(row["found"] == row["cases"] for row in stop_layers),
             all(row["found"] == 0 and row["confidence_max"] < 0.5 for row in no_stop_layers),
             # Even when degraded RGB loses legal spacing confirmation, it must retain a typed
             # crosswalk candidate rather than collapsing the observation to a rejection count.
             all(row["crosswalk_stripes_min"] >= 1 for row in crosswalk_layers))
    return rows_out, gates


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--full", action="store_true", help="run the denser fixed-seed sweep")
    args = ap.parse_args(argv)
    recall, fp, colour_cases = colour_gate(args.full)
    projection_error = projection_gate()
    curve_error, order_error, centre_delta, both_conf, one_conf = boundary_gate(args.full)
    stop_error, rejected, stop_cases = stop_gate(args.full)
    holdout_rows, holdout_gates = holdout_stop_gate(args.full)
    print("mode=%s; colour %d cases: min recall %.3f, max false-positive %.3f"
          % ("full" if args.full else "reduced", colour_cases, recall, fp))
    print("RGB top-view closed-form max error %.3e" % projection_error)
    print("boundary max lateral error %.4f m; point-order coefficient delta %.3e" % (curve_error, order_error))
    print("one-side parallel-curve displacement from two-side midpoint %.4f m; confidence both %.3f > one-side %.3f" % (centre_delta, both_conf, one_conf))
    print("stop distance max error %.4f m over %d rotations; crosswalk stripes rejected >= %d"
          % (stop_error, stop_cases, rejected))
    print("synthetic-generator holdout by fixed layer (not a real-road accuracy claim):")
    for row in holdout_rows:
        print("  %(layer)s: stop %(found)d/%(cases)d; confidence mean %(confidence_mean).3f max %(confidence_max).3f; ambiguous %(ambiguous)d/%(cases)d; crosswalk %(crosswalk_found)d/%(cases)d (mean confidence %(crosswalk_confidence_mean).3f, stripes >= %(crosswalk_stripes_min)d); max stop error %(max_distance_error)s"
              % {**row, "max_distance_error": "n/a" if np.isnan(row["max_distance_error"])
                 else "%.4f m" % row["max_distance_error"]})
    checks = [recall == 1.0, fp == 0.0, projection_error < 1e-14,
              curve_error < 0.06, order_error < 0.002, centre_delta > 0.01,
              one_conf < both_conf, stop_error < 0.10, rejected == 4,
              *holdout_gates]
    ok = all(checks)
    print("PASS" if ok else "FAIL", "(%d / %d)" % (sum(checks), len(checks)))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
