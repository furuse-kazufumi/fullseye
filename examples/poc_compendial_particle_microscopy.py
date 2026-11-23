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
    pairs = _match(features)
    if len(pairs) != len(TRUTH) or max(pair[2] for pair in pairs) > 12.0:
        raise RuntimeError("segmentation did not produce one feature near every truth particle")
    order = sorted(pairs, key=lambda pair: pair[1])
    fi = np.array([pair[0] for pair in order], int)
    table = {
        "object_id": [TRUTH[j]["id"] for _, j, _ in order],
        "diameter_px": features["equiv_diameter"][fi],
        "area_px2": features["area"][fi],
        "touches_border": features["touches_border"][fi].astype(bool),
        "split_status": [TRUTH[j]["overlap"] for _, j, _ in order],
        "major_axis_px": features["major"][fi],
        "minor_axis_px": features["minor"][fi],
    }
    measured_mm_per_px = fs.ledger.mm_per_px_from_reference(MICROMETER_LENGTH_PX, MICROMETER_KNOWN_MM)
    calibration = {"scale_per_px": measured_mm_per_px * 1000.0, "unit": "um/px",
                   "uncertainty_per_px": SCALE_UNCERTAINTY_UM_PER_PX,
                   "calibrator_id": CALIBRATOR_ID, "calibrated_at": CALIBRATED_AT,
                   "valid_until": VALID_UNTIL}
    report = fs.ledger.particle_size_distribution(
        table, calibration, border_policy="exclude", measurement_date=MEASUREMENT_DATE,
        bootstrap_samples=400 if os.environ.get("CI") == "1" else 1000, seed=SEED)
    return {"region": region, "labels": labels, "distance": distance, "seeds": seeds,
            "split": split, "features": features, "pairs": order, "table": table,
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
        xlabel="diameter [um]", ylabel="fraction", title="Number basis != volume basis",
        size=(480, 320), ylim=(0.0, 1.0), colors=["reference", "emphasis"], scale=1)
    overlap = np.array([row["overlap"] for row in sweep])
    components = np.array([row["components"] for row in sweep], float)
    lo = np.array([row["lo"] for row in sweep], float)
    hi = np.array([3.0 if row["hi"] is None else row["hi"] for row in sweep], float)
    failure = figs.render_plot(
        [("connected components", overlap, components), ("interval lower", overlap, lo),
         ("interval upper (? shown as 3)", overlap, hi)],
        xlabel="overlap fraction", ylabel="reported count", title="Failure side: overlap hides count",
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
         ["D50 number / volume", "%.3f / %.3f um" %
          (report["quantiles"]["number"]["D50"]["value"], report["quantiles"]["volume"]["D50"]["value"])],
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

    truth_d = np.array([_equivalent_diameter(row) for row in TRUTH])
    estimated_d = np.asarray(result["table"]["diameter_px"])
    simple = np.array([i for i, row in enumerate(TRUTH) if row["overlap"] == "isolated" and row["inside"]])
    error_px = estimated_d - truth_d
    max_simple_error = float(np.max(np.abs(error_px[simple])))
    report = result["report"]
    q_number = report["quantiles"]["number"]["D50"]["value"]
    q_volume = report["quantiles"]["volume"]["D50"]["value"]
    gates = [
        GateResult("circle-and-ellipse-pixelisation", max_simple_error < DIAMETER_ERROR_LIMIT_PX,
                   max_simple_error, DIAMETER_ERROR_LIMIT_PX, 0.0, "<", "isolated circle/ellipse/low contrast"),
        GateResult("three-weight-bases-differ", q_volume > q_number, q_volume - q_number, 0.0, 0.0, ">", "um"),
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
        metrics={"max_simple_diameter_error_px": max_simple_error, "number_D50_um": q_number,
                 "volume_D50_um": q_volume, "calibration_sha256": report["calibration_provenance"]["sha256"]},
        arrays={"raw": image, "segmentation": result["split"], "truth_diameter_px": truth_d,
                "estimated_diameter_px": estimated_d, "main_figure": figure_a},
        truth=truth, gates=gates, figures=figs.manifest(), videos={}, seed=SEED)
    manifest_repeat = build_manifest(
        "poc_compendial_particle_microscopy",
        metrics={"max_simple_diameter_error_px": max_simple_error, "number_D50_um": q_number,
                 "volume_D50_um": q_volume, "calibration_sha256": repeat["report"]["calibration_provenance"]["sha256"]},
        arrays={"raw": image.copy(), "segmentation": repeat["split"], "truth_diameter_px": truth_d.copy(),
                "estimated_diameter_px": np.asarray(repeat["table"]["diameter_px"]), "main_figure": figure_b},
        truth=truth, gates=gates, figures=figs.manifest(), videos={}, seed=SEED)
    differences = compare_manifests(manifest, manifest_repeat)
    gates.append(GateResult("same-environment-manifest", differences == [], len(differences), 0, 0, "==", "exact JSON"))
    manifest["gates"] = [gate.as_dict() for gate in gates]
    if figs.target_dir() is not None:
        write_manifest(figs.target_dir() / "evaluation.json", manifest)

    elapsed = time.perf_counter() - started
    print("== particle microscopy PSD")
    print("scale %.6f um/px (u=%.6f), calibration %s" %
          (SCALE_UM_PER_PX, SCALE_UNCERTAINTY_UM_PER_PX, report["calibration_provenance"]["sha256"]))
    print("isolated circle/ellipse max |diameter error| %.3f px" % max_simple_error)
    print("D50 number %.3f um / volume %.3f um (not laser-diffraction equivalence)" % (q_number, q_volume))
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
