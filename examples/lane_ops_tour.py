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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import fullseye as fs  # noqa: E402

LG = fs.ledger
SEED = 20261123


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
        for s in (12.0, 12.7, 13.4, 14.1):
            labels[(np.abs(along - s) <= 0.15) & (np.abs(across) <= 1.60)] = 1
        ss = np.linspace(0.0, 20.0, 201)
        lane = {"path": ss[:, None] * tangent, "lane_width": 3.5, "pixel_to_world": H}
        got = LG.stop_line_detect(labels, lane)
        if not got["found"]:
            raise AssertionError("stop line was missed at angle %.1f deg" % angle)
        errors.append(abs(got["distance"] - 8.0))
        rejected.append(got["rejected_crosswalk"])
    return float(max(errors)), min(rejected), len(angles)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--full", action="store_true", help="run the denser fixed-seed sweep")
    args = ap.parse_args(argv)
    recall, fp, colour_cases = colour_gate(args.full)
    projection_error = projection_gate()
    curve_error, order_error, centre_delta, both_conf, one_conf = boundary_gate(args.full)
    stop_error, rejected, stop_cases = stop_gate(args.full)
    print("mode=%s; colour %d cases: min recall %.3f, max false-positive %.3f"
          % ("full" if args.full else "reduced", colour_cases, recall, fp))
    print("RGB top-view closed-form max error %.3e" % projection_error)
    print("boundary max lateral error %.4f m; point-order coefficient delta %.3e" % (curve_error, order_error))
    print("one-side centre delta %.3e m; confidence both %.3f > one-side %.3f" % (centre_delta, both_conf, one_conf))
    print("stop distance max error %.4f m over %d rotations; crosswalk stripes rejected >= %d"
          % (stop_error, stop_cases, rejected))
    checks = [recall == 1.0, fp == 0.0, projection_error < 1e-14,
              curve_error < 0.06, order_error < 0.002, centre_delta < 1e-12,
              one_conf < both_conf, stop_error < 0.10, rejected == 4]
    ok = all(checks)
    print("PASS" if ok else "FAIL", "(%d / %d)" % (sum(checks), len(checks)))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
