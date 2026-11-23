# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""薬学向け顕微鏡粒径 —— 校正・端・重なりを記録し、個数基準と体積基準を分けて真値と比べる。

    PYTHONPATH=. py -3.11 examples/poc_compendial_particle_microscopy.py
    $env:CI='1'; $env:PYTHONPATH='.'; py -3.11 examples/poc_compendial_particle_microscopy.py

1 枚の合成試料に、ステージミクロメータ、孤立した円と楕円、2 個の重なった円、
画面端で切れた円、低コントラスト円を置く。真値は中心、面積相当径、長軸・短軸、
重なり状態、画面内外を、描画とは別の数表で保持する。画像から
``blob_label`` → ``blob_features``、重なりには ``blob_distance`` → ``blob_seeds`` →
``blob_split`` を使い、ステージミクロメータは ``mm_per_px_from_reference`` で校正する。
最後に ``particle_size_distribution`` が端・重なりの採否、尺度不確かさ、個数・面積・
体積基準のビンと D10/D50/D90、校正来歴を 1 つの表へまとめる。

個数基準の画像解析と体積基準のレーザー回折は同じ量ではない。体積基準は球相当の
``d^3`` 重みを用いた比較表示に過ぎず、USP <776>・<788>・<429>への適合を示さない。
ここで示すのは、これらの規格が問う量を合成の真値と比べた結果である。

主図は原画像 → 分割 → 真値と推定 → 径分布 → 失敗側を 1 画面に置く。別図は
重なり率を増やし、連結成分が 1 個へ潰れる一方、``blob_count_interval`` が曖昧な
場合に単一個数を返さない系列である。動画は作らない。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import blob2d  # noqa: E402
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import pharmaparticle as pharma  # noqa: E402
from fullseye.evaluation.manifest import build_manifest, compare_manifests, write_manifest  # noqa: E402
from fullseye.evaluation.result import GateResult  # noqa: E402
from fullseye.evaluation.truth import TruthBundle  # noqa: E402


SEED = 776
IMAGE_SHAPE = (320, 480)
BACKGROUND_LEVEL = 0.82
PARTICLE_LEVEL = 0.20
LOW_CONTRAST_LEVEL = 0.60
SEGMENT_THRESHOLD = 0.68
MICROMETER_KNOWN_MM = 0.100
MICROMETER_LENGTH_PX = 200.0
SCALE_UM_PER_PX = 1000.0 * MICROMETER_KNOWN_MM / MICROMETER_LENGTH_PX
SCALE_UNCERTAINTY_UM_PER_PX = 0.0025
MEASUREMENT_DATE = "2026-11-23"
CALIBRATED_AT = "2026-10-01"
VALID_UNTIL = "2027-09-30"
CALIBRATOR_ID = "STAGE-MICROMETER-SM-2026-017"
MIN_SEED_PROMINENCE_PX = 4.0
OVERLAP_RATES = np.array([0.05, 0.25, 0.45, 0.60, 0.75])
DIAMETER_ERROR_LIMIT_PX = 1.5


TRUTH = (
    {"id": "circle", "center": (105.0, 80.0), "major": 36.0, "minor": 36.0,
     "overlap": "isolated", "inside": True, "level": PARTICLE_LEVEL},
    {"id": "ellipse", "center": (118.0, 185.0), "major": 54.0, "minor": 26.0,
     "overlap": "isolated", "inside": True, "level": PARTICLE_LEVEL},
    {"id": "overlap-a", "center": (205.0, 270.0), "major": 40.0, "minor": 40.0,
     "overlap": "split", "inside": True, "level": PARTICLE_LEVEL},
    {"id": "overlap-b", "center": (205.0, 300.0), "major": 40.0, "minor": 40.0,
     "overlap": "split", "inside": True, "level": PARTICLE_LEVEL},
    {"id": "low-contrast", "center": (255.0, 105.0), "major": 34.0, "minor": 34.0,
     "overlap": "isolated", "inside": True, "level": LOW_CONTRAST_LEVEL},
    {"id": "border", "center": (282.0, 474.0), "major": 48.0, "minor": 48.0,
     "overlap": "isolated", "inside": False, "level": PARTICLE_LEVEL},
)


def _equivalent_diameter(row):
    """Area-equivalent ellipse diameter / 楕円の面積相当径。"""
    return float(np.sqrt(row["major"] * row["minor"]))


def synthesize():
    """Render the calibrated synthetic specimen / 校正標本と粒子を描く。"""
    rng = np.random.default_rng(SEED)
    h, w = IMAGE_SHAPE
    yy, xx = np.mgrid[0:h, 0:w]
    image = np.full((h, w), BACKGROUND_LEVEL, np.float64)
    masks = []
    for row in TRUTH:
        cy, cx = row["center"]
        mask = ((yy - cy) / (row["minor"] / 2.0)) ** 2 + ((xx - cx) / (row["major"] / 2.0)) ** 2 <= 1.0
        image[mask] = np.minimum(image[mask], row["level"])
        masks.append(mask)
    # The stage micrometer occupies a separate calibration band and is excluded from segmentation.
    image[24:28, 35:35 + int(MICROMETER_LENGTH_PX)] = 0.05
    for tick in range(35, 236, 40):
        image[18:34, tick:tick + 2] = 0.05
    image += rng.normal(0.0, 0.006, image.shape)
    return np.clip(image, 0.0, 1.0), masks


def _match(features):
    """Nearest-centre assignment, independently checked one-to-one / 重心を真値へ一対一対応。"""
    estimated = np.c_[features["row"], features["col"]]
    truth = np.array([row["center"] for row in TRUTH], np.float64)
    pairs, used = [], set()
    for i, point in enumerate(estimated):
        distances = np.linalg.norm(truth - point, axis=1)
        for j in np.argsort(distances):
            if int(j) not in used:
                used.add(int(j))
                pairs.append((i, int(j), float(distances[j])))
                break
    return pairs


def analyse(image):
    """Run the existing blob chain and the reporting op / 既存 op の鎖と新 op を実行。"""
    region = (image < SEGMENT_THRESHOLD)
    region[:48] = False
    labels = blob2d.blob_label(region)
    distance = blob2d.blob_distance(region)
    seeds = blob2d.blob_seeds(distance, MIN_SEED_PROMINENCE_PX)
    split = blob2d.blob_split(labels, seeds, distance)
    features = blob2d.blob_features(split)
    count_record = blob2d.blob_count_interval(region, round_tol=0.12)
    pairs = _match(features)
    if len(pairs) != len(TRUTH) or max(pair[2] for pair in pairs) > 12.0:
        raise RuntimeError("segmentation did not produce one feature near every truth particle")
    order = sorted(pairs, key=lambda pair: pair[1])
    fi = np.array([pair[0] for pair in order], int)
    components = count_record["components"]
    component_records = {
        int(components["label"][i]): {
            "lo": int(components["lo"][i]),
            "hi": None if int(components["hi"][i]) < 0 else int(components["hi"][i]),
            "status": components["status"][i],
            "determined": components["status"][i] == "determined",
            "count": int(components["lo"][i]) if components["status"][i] == "determined" else None,
        }
        for i in range(len(components["label"]))}
    component_ids = labels[features["row"][fi].round().astype(int), features["col"][fi].round().astype(int)]
    upstream = [component_records[int(label)] for label in component_ids]
    # This table is derived solely from blob_split labels and blob_count_interval;
    # TRUTH is used only below for a separate post-hoc comparison.
    statuses = ["ambiguous" if not row["determined"] else ("split" if row["count"] > 1 else "isolated")
                for row in upstream]
    table = {
        "object_id": [TRUTH[j]["id"] for _, j, _ in order],
        "diameter_px": features["equiv_diameter"][fi],
        "area_px2": features["area"][fi],
        "diameter_unit": "px", "area_unit": "px2",
        "touches_border": features["touches_border"][fi].astype(bool),
        "split_status": statuses,
        "component_id": ["component-%d" % int(label) for label in component_ids],
        "split_evidence": ["blob_split + blob_count_interval:%s" % row["status"] for row in upstream],
        "count_interval_lo": [int(row["lo"]) for row in upstream],
        "count_interval_hi": [None if row["hi"] is None else int(row["hi"]) for row in upstream],
        "count_determined": [bool(row["determined"]) for row in upstream],
        "major_axis_px": features["major"][fi],
        "minor_axis_px": features["minor"][fi],
    }
    measured_mm_per_px = fs.ledger.mm_per_px_from_reference(MICROMETER_LENGTH_PX, MICROMETER_KNOWN_MM)
    calibration = {"scale": {"value": measured_mm_per_px, "unit": "mm/px",
                               "standard_uncertainty": SCALE_UNCERTAINTY_UM_PER_PX / 1000.0},
                   "calibrator_id": CALIBRATOR_ID, "calibrated_at": CALIBRATED_AT,
                   "valid_until": VALID_UNTIL}
    report = fs.ledger.particle_size_distribution(
        table, calibration, border_policy="exclude", measurement_date=MEASUREMENT_DATE,
        bootstrap_samples=400 if os.environ.get("CI") == "1" else 1000, seed=SEED)
    return {"region": region, "labels": labels, "distance": distance, "seeds": seeds,
            "split": split, "features": features, "pairs": order, "table": table, "count_record": count_record,
            "calibration": calibration, "report": report}


def overlap_sweep():
    """Increase overlap and record component count versus interval verdict / 重なり系列。"""
    size, radius = 96, 18.0
    yy, xx = np.mgrid[0:size, 0:size]
    rows, panels, captions = [], [], []
    for overlap in OVERLAP_RATES:
        separation = 2.0 * radius * (1.0 - overlap)
        a = (yy - 48.0) ** 2 + (xx - (48.0 - separation / 2.0)) ** 2 <= radius ** 2
        b = (yy - 48.0) ** 2 + (xx - (48.0 + separation / 2.0)) ** 2 <= radius ** 2
        region = a | b
        labels = blob2d.blob_label(region)
        interval = blob2d.blob_count_interval(region, round_tol=0.12)
        rows.append({"overlap": float(overlap), "components": int(labels.max()),
                     "lo": int(interval["lo"]), "hi": interval["hi"],
                     "determined": bool(interval["determined"])})
        panels.append(region.astype(float))
        verdict = str(interval["count"]) if interval["determined"] else "%s..%s" % (
            interval["lo"], "?" if interval["hi"] is None else interval["hi"])
        captions.append("overlap %.2f | components %d | interval %s" % (overlap, labels.max(), verdict))
    return rows, panels, captions


def _midpoint_truth(diameter, weight, q):
    """Independent truth calculator for the documented midpoint convention / 真値用の別実装。"""
    order = np.argsort(diameter)
    x, w = np.asarray(diameter)[order], np.asarray(weight)[order]
    unique = np.unique(x)
    mass = np.array([w[x == value].sum() for value in unique])
    position = (np.cumsum(mass) - mass / 2.0) / mass.sum()
    return float(np.interp(q / 100.0, position, unique, left=unique[0], right=unique[-1]))


def large_sample_validation():
    """Separate 324-particle rendered specimen and image-only analysis / 数百粒子の独立検証。"""
    rng = np.random.default_rng(SEED + 31)
    h = w = 560
    yy, xx = np.mgrid[0:h, 0:w]
    image = np.full((h, w), BACKGROUND_LEVEL, float)
    truth = []
    for r in range(18):
        for c in range(18):
            cy, cx = 18 + 29 * r + rng.uniform(-.35, .35), 18 + 29 * c + rng.uniform(-.35, .35)
            diameter = float(rng.uniform(9.0, 17.0))
            low = (r * 18 + c) % 17 == 0
            truth.append({"center": (cy, cx), "diameter": diameter, "low": low, "border": False})
    # The final eight are deliberately clipped, and a separate set of pairs is overlapped.
    for i in range(8):
        truth[i]["center"] = (0.5 + i * 65.0, 1.0)
        truth[i]["border"] = True
    for i in range(30, 42, 2):
        cy, cx = truth[i]["center"]
        truth[i + 1]["center"] = (cy, cx + truth[i]["diameter"] * .42)
    for row in truth:
        cy, cx = row["center"]
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= (row["diameter"] / 2.0) ** 2
        image[mask] = np.minimum(image[mask], LOW_CONTRAST_LEVEL if row["low"] else PARTICLE_LEVEL)
    image = np.clip(image + rng.normal(0.0, .008, image.shape), 0.0, 1.0)
    region = image < SEGMENT_THRESHOLD
    labels = blob2d.blob_label(region)
    distance = blob2d.blob_distance(region)
    split = blob2d.blob_split(labels, blob2d.blob_seeds(distance, MIN_SEED_PROMINENCE_PX), distance)
    feature = blob2d.blob_features(split)
    interval = blob2d.blob_count_interval(region, round_tol=.12)["components"]
    records = {int(interval["label"][i]): {"lo": int(interval["lo"][i]),
               "hi": None if int(interval["hi"][i]) < 0 else int(interval["hi"][i]),
               "determined": interval["status"][i] == "determined", "status": interval["status"][i]}
               for i in range(len(interval["label"]))}
    comp = labels[feature["row"].round().astype(int), feature["col"].round().astype(int)]
    upstream = [records[int(label)] for label in comp]
    table = {"object_id": ["detected-%03d" % i for i in range(feature["n"])],
             "diameter_px": feature["equiv_diameter"], "area_px2": feature["area"],
             "diameter_unit": "px", "area_unit": "px2", "touches_border": feature["touches_border"].astype(bool),
             "split_status": ["ambiguous" if not x["determined"] else ("split" if x["lo"] > 1 else "isolated") for x in upstream],
             "component_id": ["component-%d" % int(x) for x in comp],
             "split_evidence": ["blob_split + blob_count_interval:%s" % x["status"] for x in upstream],
             "count_interval_lo": [x["lo"] for x in upstream], "count_interval_hi": [x["hi"] for x in upstream],
             "count_determined": [x["determined"] for x in upstream]}
    calibration = {"scale": {"value": MICROMETER_KNOWN_MM / MICROMETER_LENGTH_PX, "unit": "mm/px",
                               "standard_uncertainty": SCALE_UNCERTAINTY_UM_PER_PX / 1000.0},
                   "calibrator_id": CALIBRATOR_ID, "calibrated_at": CALIBRATED_AT, "valid_until": VALID_UNTIL}
    report = fs.ledger.particle_size_distribution(table, calibration, border_policy="exclude",
        measurement_date=MEASUREMENT_DATE, bootstrap_samples=400 if os.environ.get("CI") == "1" else 1000, seed=SEED + 31)
    # Truth selection is intentionally separate from the measured upstream records.
    td = np.array([row["diameter"] for row in truth]) * calibration["scale"]["value"]
    valid = np.array([not row["border"] for row in truth])
    edges = report["bins"]["edges"]
    curves, values = [], {}
    for basis, weight in (("number", np.ones_like(td)), ("area", td ** 2), ("volume", td ** 3)):
        hist = np.histogram(td[valid], edges, weights=weight[valid])[0]
        curves.extend([("estimated " + basis, np.sqrt(edges[:-1] * edges[1:]), report["bins"][basis]),
                       ("truth " + basis, np.sqrt(edges[:-1] * edges[1:]), hist / hist.sum())])
        values[basis] = [_midpoint_truth(td[valid], weight[valid], q) for q in (10, 50, 90)]
    distribution = figs.render_plot(curves, xlabel="diameter [mm]", ylabel="fraction",
        title="324-particle specimen: estimated and synthetic truth", size=(640, 360), ylim=(0.0, 1.0), scale=1)
    rows = []
    for basis in ("number", "area", "volume"):
        for name, truth_value in zip(("D10", "D50", "D90"), values[basis]):
            q = report["quantiles"][basis][name]
            rows.append([basis + " " + name, "%.5f" % truth_value, "%.5f [%.5f, %.5f]" %
                         (q["value"], q["ci_lower"], q["ci_upper"])])
    summary = figs._render_table(["basis / Dx", "truth mm", "estimate / 95% CI mm"], rows,
                                 title="Midpoint convention; conditional bootstrap interval", scale=1)
    figure = fs.annotate_figure_grid([_rgb_gray(image), _label_rgb(split), distribution, summary],
        captions=["Input: low contrast, overlap and clipped particles", "blob_split + blob_count_interval evidence",
                  "Three bases: estimate versus truth", "D10/D50/D90 and interval versus truth"], ncols=2,
        title="Large-sample PSD validation / 数百粒子の分布検証")
    return report, values, figure, image, split


def accuracy_sweep():
    """Independent render/measure sweep over declared imaging conditions / 条件域の精度掃引。"""
    rows = []
    yy, xx = np.mgrid[0:96, 0:96]
    for diameter in (12.0, 20.0):
        for ratio in (1.0, 1.8):
            for phase in (.15, .65):
                for noise in (.01, .04):  # SNR range follows particle contrast / sigma.
                    for psf in (.4, 1.0):
                        for threshold in (.55, .68):
                            for background_gradient in (0.0, .12):
                                major, minor = diameter * np.sqrt(ratio), diameter / np.sqrt(ratio)
                                cy, cx = 48.0 + phase, 48.0 + (1.0 - phase)
                                truth_mask = ((yy - cy) / (minor / 2.0)) ** 2 + ((xx - cx) / (major / 2.0)) ** 2 <= 1.0
                                field = BACKGROUND_LEVEL + background_gradient * (xx / 95.0 - .5)
                                image = np.where(truth_mask, PARTICLE_LEVEL, field)
                                image = ndimage.gaussian_filter(image, psf, mode="nearest")
                                seed = int(diameter * 100 + ratio * 10 + phase * 1000 + noise * 10000 + psf * 100 + threshold * 1000 + background_gradient * 100)
                                image = image + np.random.default_rng(seed).normal(0.0, noise, image.shape)
                                f = blob2d.blob_features(blob2d.blob_label(image < threshold))
                                if f["n"] != 1 or bool(f["touches_border"][0]):
                                    rows.append({"error_px": np.nan, "rejected": True})
                                else:
                                    rows.append({"error_px": float(f["equiv_diameter"][0] - diameter), "rejected": False})
    error = np.abs(np.array([row["error_px"] for row in rows], float))
    accepted = error[np.isfinite(error)]
    stats = {"conditions": len(rows), "median_abs_error_px": float(np.median(accepted)),
             "p90_abs_error_px": float(np.quantile(accepted, .90)), "worst_abs_error_px": float(np.max(accepted)),
             "rejection_rate": float(np.mean(~np.isfinite(error)))}
    panel = figs._render_table(["swept condition", "range / result"],
        [["diameter px", "12, 20"], ["axis ratio", "1.0, 1.8"], ["subpixel phase px", "0.15, 0.65"],
         ["noise sigma (SNR proxy)", "0.01, 0.04"], ["PSF sigma px", "0.4, 1.0"],
         ["threshold", "0.55, 0.68"], ["background gradient", "0.00, 0.12"],
         ["median / p90 / worst |error| px", "%.3f / %.3f / %.3f" % (stats["median_abs_error_px"], stats["p90_abs_error_px"], stats["worst_abs_error_px"])],
         ["rejection rate", "%.1f%%" % (100 * stats["rejection_rate"]) ]],
        title="Accuracy claim limited to the swept synthetic range", scale=1)
    return stats, panel


def _rgb_gray(image):
    return np.repeat(np.asarray(image)[..., None], 3, axis=2)


def _label_rgb(labels):
    colors = np.array([[0.92, 0.92, 0.92], [0.00, 0.45, 0.70], [0.90, 0.62, 0.00],
                       [0.00, 0.62, 0.45], [0.80, 0.30, 0.35], [0.35, 0.35, 0.75],
                       [0.55, 0.35, 0.10]])
    return colors[np.asarray(labels, int) % len(colors)]


def _cross(image, row, col, color, radius=6):
    """Draw a fixed-size centre cross / 中心の十字を描く。"""
    out = image
    r, c = int(round(row)), int(round(col))
    out[max(0, r - radius):min(out.shape[0], r + radius + 1), max(0, c - 1):min(out.shape[1], c + 2)] = color
    out[max(0, r - 1):min(out.shape[0], r + 2), max(0, c - radius):min(out.shape[1], c + radius + 1)] = color


def make_panels(image, result, sweep):
    """Input/output/truth/distributions/failure/metrics at one size / 主図の 6 面。"""
    raw = _rgb_gray(image)
    segmented = _label_rgb(result["split"])
    overlay = 0.55 * raw + 0.45 * segmented
    for row in TRUTH:
        _cross(overlay, *row["center"], np.array([0.0, 0.75, 0.2]), radius=7)
    for i in range(result["features"]["n"]):
        _cross(overlay, result["features"]["row"][i], result["features"]["col"][i],
               np.array([0.9, 0.1, 0.1]), radius=4)
    bins = result["report"]["bins"]
    centres = np.sqrt(bins["edges"][:-1] * bins["edges"][1:])
    distribution = figs.render_plot(
        [("number basis", centres, bins["number"]), ("volume basis (d^3)", centres, bins["volume"])],
        xlabel="diameter [mm]", ylabel="fraction", title="Number basis != volume basis",
        size=(480, 320), ylim=(0.0, 1.0), colors=["reference", "emphasis"], scale=1)
    overlap = np.array([row["overlap"] for row in sweep])
    components = np.array([row["components"] for row in sweep], float)
    lo = np.array([row["lo"] for row in sweep], float)
    hi = np.array([np.nan if row["hi"] is None else row["hi"] for row in sweep], float)
    known_hi = np.isfinite(hi)
    failure = figs.render_plot(
        [("connected components", overlap, components), ("interval lower", overlap, lo),
         ("interval upper (unknown omitted)", overlap[known_hi], hi[known_hi])],
        xlabel="overlap fraction", ylabel="reported count", title="Failure side: overlap hides count (unknown upper omitted)",
        size=(480, 320), ylim=(0.0, 3.2), colors=["wrong", "reference", "emphasis"], scale=1)
    simple = np.array([i for i, row in enumerate(TRUTH) if row["overlap"] == "isolated" and row["inside"]])
    measured = np.asarray(result["table"]["diameter_px"])
    truth = np.array([_equivalent_diameter(row) for row in TRUTH])
    max_error = float(np.max(np.abs(measured[simple] - truth[simple])))
    report = result["report"]
    summary = figs._render_table(  # examplefig's measured text layout; panel only, no extra artifact
        ["measured quantity", "same-run value"],
        [["stage micrometer scale", "%.6f +/- %.6f um/px" % (SCALE_UM_PER_PX, SCALE_UNCERTAINTY_UM_PER_PX)],
         ["isolated max |diameter error|", "%.3f px" % max_error],
         ["accepted / input", "%d / %d" % (report["counts"]["accepted_observed"], report["counts"]["input"])],
         ["border excluded / split overlap", "%d / %d" % (report["counts"]["border_excluded"], report["counts"]["overlap_split_accepted"])],
         ["D10/D50/D90", "not reported: n_eff < %d" % report["policy"]["minimum_effective_particles"]],
         ["quantile convention", "weighted empirical midpoint"],
         ["laser diffraction equivalence", "NO"]],
        title="Measured in this run / この実行の値", scale=1)
    canvas = np.ones((320, 480, 3), float)
    sh, sw = summary.shape[:2]
    if sh > canvas.shape[0] or sw > canvas.shape[1]:
        from PIL import Image
        factor = min(canvas.shape[0] / sh, canvas.shape[1] / sw)
        summary = np.asarray(Image.fromarray(np.uint8(np.clip(summary, 0, 1) * 255)).resize(
            (max(1, int(sw * factor)), max(1, int(sh * factor))), Image.Resampling.LANCZOS)) / 255.0
        sh, sw = summary.shape[:2]
    canvas[(320 - sh) // 2:(320 - sh) // 2 + sh, (480 - sw) // 2:(480 - sw) // 2 + sw] = summary
    return [raw, segmented, overlay, distribution, failure, canvas]


def _array_hash(value):
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(arr.dtype.str.encode("ascii"))
    h.update(json.dumps(list(arr.shape), separators=(",", ":")).encode("ascii"))
    h.update(arr.tobytes())
    return h.hexdigest()


def main():
    started = time.perf_counter()
    image, truth_masks = synthesize()
    result = analyse(image)
    repeat = analyse(image.copy())
    sweep, sweep_panels, sweep_captions = overlap_sweep()
    large_report, large_truth, large_figure, large_raw, large_split = large_sample_validation()
    sweep_stats, sweep_figure = accuracy_sweep()

    truth_d = np.array([_equivalent_diameter(row) for row in TRUTH])
    estimated_d = np.asarray(result["table"]["diameter_px"])
    simple = np.array([i for i, row in enumerate(TRUTH) if row["overlap"] == "isolated" and row["inside"]])
    error_px = estimated_d - truth_d
    max_simple_error = float(np.max(np.abs(error_px[simple])))
    report = result["report"]
    gates = [
        GateResult("circle-and-ellipse-pixelisation", max_simple_error < DIAMETER_ERROR_LIMIT_PX,
                   max_simple_error, DIAMETER_ERROR_LIMIT_PX, 0.0, "<", "isolated circle/ellipse/low contrast"),
        GateResult("small-sample-quantiles-suppressed",
                   all(report["quantiles"][basis][name]["status"] == "insufficient_sample"
                       for basis in ("number", "area", "volume") for name in ("D10", "D50", "D90")),
                   report["quantiles"]["number"]["D50"]["effective_particles"], pharma.MIN_EFFECTIVE_PARTICLES, 0, "<", "n_eff"),
        GateResult("border-excluded", report["counts"]["border_excluded"] == 1,
                   report["counts"]["border_excluded"], 1, 0, "==", "one clipped particle"),
        GateResult("overlap-split-recorded", report["counts"]["overlap_split_accepted"] == 2,
                   report["counts"]["overlap_split_accepted"], 2, 0, "==", "two split rows"),
        GateResult("scale-uncertainty-propagated",
                   all(row["diameter_uncertainty"] > 0.0 for row in report["particle_rows"]),
                   min(row["diameter_uncertainty"] for row in report["particle_rows"]), 0.0, 0.0, ">", "um"),
        GateResult("same-seed-array-hash", _array_hash(result["split"]) == _array_hash(repeat["split"]),
                   _array_hash(result["split"]), _array_hash(repeat["split"]), 0, "==", "exact SHA-256"),
        GateResult("deep-overlap-not-silently-one", any(not row["determined"] for row in sweep[2:]),
                   sum(not row["determined"] for row in sweep[2:]), 1, 0, ">=", "ambiguous sweep cases"),
        GateResult("large-sample-truth-inside-number-D50-interval",
                   large_report["quantiles"]["number"]["D50"]["ci_lower"] <= large_truth["number"][1] <= large_report["quantiles"]["number"]["D50"]["ci_upper"],
                   large_truth["number"][1], large_report["quantiles"]["number"]["D50"]["ci_lower"], large_report["quantiles"]["number"]["D50"]["ci_upper"], "within", "mm"),
        GateResult("accuracy-sweep-is-labelled-with-its-range", sweep_stats["conditions"] == 128,
                   sweep_stats["conditions"], 128, 0, "==", "factorial conditions"),
    ]

    panels = make_panels(image, result, sweep)
    captions = ["1 Input: stage micrometer + particles", "2 Output: blob_split labels",
                "3 Truth green / estimate red", "4 PSD: number and volume basis",
                "5 Failure: overlap and count interval", "6 Same-run measured values"]
    # Two columns retain all input→output→truth→failure panels on one screen while
    # giving the bilingual labels their documented inspection size.
    figure_a = fs.annotate_figure_grid(panels, captions=captions, ncols=2,
                                       title="Compendial microscopy quantities vs synthetic truth / 規格が問う量を真値と比べる")
    figure_b = fs.annotate_figure_grid(make_panels(image, repeat, sweep), captions=captions, ncols=2,
                                       title="Compendial microscopy quantities vs synthetic truth / 規格が問う量を真値と比べる")
    gates.append(GateResult("deterministic-main-figure", _array_hash(figure_a) == _array_hash(figure_b),
                            _array_hash(figure_a), _array_hash(figure_b), 0, "==", "exact SHA-256"))
    figs.save("compendial_particle_microscopy_main", figure_a,
              "原画像→分割→真値と推定→個数/体積基準の径分布→失敗側。体積基準はレーザー回折との同一性を意味しない。")
    figs.save_grid("particle_overlap_rate_series", sweep_panels, captions=sweep_captions, ncols=5,
                   gray=True, vrange=(0.0, 1.0),
                   caption="重なり率を増やす系列。連結成分数だけでは 2 粒を 1 粒として数える。")
    figs.save("compendial_particle_microscopy_large_validation", large_figure,
              "324粒子の別試料。低コントラスト、重なり、端粒子を含み、3基準の分布と真値・区間を併記する。")
    figs.save("compendial_particle_microscopy_accuracy_sweep", sweep_figure,
              "径、軸比、副画素位置、SNR、PSF、閾値、背景むらを掃引した範囲内だけの精度要約。")

    truth = TruthBundle(
        fields={"centres": np.array([row["center"] for row in TRUTH]),
                "diameter_px": truth_d,
                "major_minor_px": np.array([[row["major"], row["minor"]] for row in TRUTH]),
                "inside": np.array([row["inside"] for row in TRUTH], bool),
                "overlap_status": np.array([{"isolated": 0, "split": 1}[row["overlap"]] for row in TRUTH])},
        units={"centres": "px", "diameter_px": "px", "major_minor_px": "px",
               "inside": "bool", "overlap_status": "code"},
        frames={"centres": "image-row-col-raw", "diameter_px": "index", "major_minor_px": "index",
                "inside": "index", "overlap_status": "index"},
        masks={}, provenance={"processing_stage": "raw-pre-isp", "generator": "analytic ellipses"}, seed=SEED)
    manifest = build_manifest(
        "poc_compendial_particle_microscopy",
        metrics={"max_simple_diameter_error_px": max_simple_error,
                 "calibration_sha256": report["calibration_provenance"]["sha256"]},
        arrays={"raw": image, "segmentation": result["split"], "truth_diameter_px": truth_d,
                "estimated_diameter_px": estimated_d, "main_figure": figure_a, "large_raw": large_raw,
                "large_segmentation": large_split, "large_figure": large_figure, "accuracy_sweep": sweep_figure},
        truth=truth, gates=gates, figures=figs.manifest(), videos={}, seed=SEED)
    manifest_repeat = build_manifest(
        "poc_compendial_particle_microscopy",
        metrics={"max_simple_diameter_error_px": max_simple_error,
                 "calibration_sha256": repeat["report"]["calibration_provenance"]["sha256"]},
        arrays={"raw": image.copy(), "segmentation": repeat["split"], "truth_diameter_px": truth_d.copy(),
                "estimated_diameter_px": np.asarray(repeat["table"]["diameter_px"]), "main_figure": figure_b,
                "large_raw": large_raw.copy(), "large_segmentation": large_split.copy(), "large_figure": large_figure.copy(),
                "accuracy_sweep": sweep_figure.copy()},
        truth=truth, gates=gates, figures=figs.manifest(), videos={}, seed=SEED)
    differences = compare_manifests(manifest, manifest_repeat)
    gates.append(GateResult("same-environment-manifest", differences == [], len(differences), 0, 0, "==", "exact JSON"))
    manifest["gates"] = [gate.as_dict() for gate in gates]
    if figs.target_dir() is not None:
        write_manifest(figs.target_dir() / "evaluation.json", manifest)

    elapsed = time.perf_counter() - started
    print("== particle microscopy PSD")
    print("scale %.9f mm/px (u=%.9f), calibration %s" %
          (SCALE_UM_PER_PX / 1000.0, SCALE_UNCERTAINTY_UM_PER_PX / 1000.0, report["calibration_provenance"]["sha256"]))
    print("isolated circle/ellipse max |diameter error| %.3f px" % max_simple_error)
    print("six-particle main figure: decision-path explanation; quantiles suppressed below n_eff=%d" % pharma.MIN_EFFECTIVE_PARTICLES)
    for basis in ("number", "area", "volume"):
        print("large %s truth/estimate D10,D50,D90: %s / %s" % (basis,
              ", ".join("%.5f" % x for x in large_truth[basis]),
              ", ".join("%.5f" % large_report["quantiles"][basis][name]["value"] for name in ("D10", "D50", "D90"))))
    print("accuracy sweep n=%d: median %.3f px, p90 %.3f px, worst %.3f px, rejected %.1f%%" %
          (sweep_stats["conditions"], sweep_stats["median_abs_error_px"], sweep_stats["p90_abs_error_px"],
           sweep_stats["worst_abs_error_px"], 100 * sweep_stats["rejection_rate"]))
    print("accepted %d, border excluded %d, split overlap accepted %d" %
          (report["counts"]["accepted_observed"], report["counts"]["border_excluded"],
           report["counts"]["overlap_split_accepted"]))
    for gate in gates:
        print("  [%s] %s: %s" % ("PASS" if gate.passed else "FAIL", gate.name, gate.measured))
    print("figures %s" % (figs.target_dir() or "disabled"))
    print("elapsed %.3f s, main figure %s" % (elapsed, tuple(figure_a.shape)))
    if figs.errors():
        print("figure errors: %s" % figs.errors())
    if not gates or not all(gate.passed for gate in gates) or figs.errors():
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
