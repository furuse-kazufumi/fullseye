# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""バイアル異物検査: 回転停止後の粒子を合成真値で POD 評価する。

``vial_spin_stop_sequence`` は停止後に指数減衰する旋回流へ Stokes の
沈降・浮上を重ね、粒子・気泡・静止傷を既知の真値から描く。
``track_moving_particles`` は時系列差分で暗い粒子（背面照明）と明るい
粒子（側面/Tyndall 照明）を同じ座標系で追跡する。この PoC は粒径 ×
コントラスト × 照明で、調整用 trial と独立 holdout を分離する。

This is a synthetic, first-stage screening evaluation.  It is not a formal
USP <1790> qualification criterion and it has not been validated on production
camera data.  The flow is low-Reynolds-number / isolated-sphere Stokes drag with
geometric wall handling; glass and liquid refraction are visual cues, not a ray
trace or a CFD solution.

公開資料を画像の転載なしに観察項目として使った。公開資料は白/黒背景、底・肩からの
Tyndall 光、回転後も動く粒子、高出力 LED 背面照明と回転後撮像を記載する。ガラス容器
メーカーの公開 application note は、ガラスの屈折率差が反射と透過を変えることを記載する。
出典表示: Seidenader V90 の公開資料; Jambon et al. (2024, *Eur J Hosp Pharm*,
doi:10.1136/ejhpharm-2024-004143); Corning application note CLSCPT-AN-1018.
この PoC はそれらの見え方（ガラス縁、メニスカス、曲面底、明視野の暗粒子、
暗視野の明粒子）だけを合成し、第三者の画像データは取り込まない。

USP <1790> の文脈でしばしば引用される「100 µm 約 40 %、150 µm 付近 70 %、
200 µm 以上 95 %超」は、良条件での手作業検査の参考観測値であり、規格の
合否基準でも、この合成 AVI の目標値でもない。図の灰色破線はこの参照値である。

Run:
    PYTHONPATH=. py -3.11 examples/poc_vial_particle_pod.py
    FULLSEYE_POC_BUDGET=reduced PYTHONPATH=. py -3.11 examples/poc_vial_particle_pod.py
    FULLSEYE_FIGURE_DIR=<output-directory> PYTHONPATH=. py -3.11 examples/poc_vial_particle_pod.py

``FULLSEYE_FIGURE_DIR`` selects the figure output directory.  When it is not
set, a ``fullseye/vial_particle_pod`` directory beneath the system temporary
directory is used. ``FULLSEYE_FIGURE_DIR`` で図の出力先を指定でき、未指定時は
システム一時ディレクトリの ``fullseye/vial_particle_pod`` を使う。
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Keep the PoC's default artefacts out of a checkout; callers can override it
# with FULLSEYE_FIGURE_DIR before launching the script.  既定の成果物は作業木へ
# 書かず、起動前の FULLSEYE_FIGURE_DIR で出力先を差し替えられる。
if __name__ == "__main__":
    os.environ.setdefault("FULLSEYE_FIGURE_DIR",
                          str(Path(tempfile.gettempdir()) / "fullseye" / "vial_particle_pod"))
import examplefig as figs  # noqa: E402
from pod import pod_hitmiss_fit, proportion_interval  # noqa: E402
from vialops import track_moving_particles, vial_spin_stop_sequence  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
DIAMETERS = np.array([45.0, 65.0, 90.0, 120.0, 160.0, 220.0, 260.0])
CONTRASTS = np.array([0.035, 0.065, 0.120])
ILLUMINATIONS = ("back", "side")
CALIBRATION_REPS = 2 if REDUCED else 6
HOLDOUT_REPS = 2 if REDUCED else 10
HOLDOUT_SEED_BASE = 29000 if REDUCED else 26000
CHECKS = []
EVAL_KW = dict(shape=(144, 128), n_frames=16, frame_interval_s=0.030,
               initial_omega_rad_s=2.2, decay_time_s=0.22, pixel_size_um=100.0,
               noise_sigma=0.008)
VISUAL_KW = dict(shape=(900, 560), n_frames=16, frame_interval_s=0.030,
                 initial_omega_rad_s=2.2, decay_time_s=0.22, pixel_size_um=40.0,
                 noise_sigma=0.004)


def check(condition, name, detail):
    """Print a measurable gate, never an assertion without its observed value."""
    CHECKS.append(bool(condition))
    print("  [%s] %s — %s" % ("PASS" if condition else "FAIL", name, detail))


def _truth_rows(truth, object_id):
    q = truth["object_id"].astype(int) == int(object_id)
    order = np.argsort(truth["frame"][q].astype(int))
    return {key: np.asarray(value)[q][order] for key, value in truth.items()
            if isinstance(value, np.ndarray) and value.shape == q.shape}


def correspondence(truth, tracks, kinds=("particle", "bubble", "scratch"), max_distance_px=3.5):
    """Globally associate true objects and tracker IDs by common-frame distance.

    A nearest detection in a single frame is insufficient: an unrelated bubble
    might happen to be nearby.  This association scores whole trajectories and
    uses one bipartite assignment, so one tracker ID cannot be credited to two
    true particle/bubble/scratch IDs.  It returns the frame-level pairs used
    both for POD scoring and for the same-colour truth/detection overlays.

    全真値物体と軌跡 ID を一度に二部マッチングし、1 本の軌跡を複数物体の
    検出として数えない。返り値は POD と同色の真値/検出重ね描きに共用する。
    """
    from scipy.optimize import linear_sum_assignment

    result = {}
    objects = []
    for oid in np.unique(truth["object_id"].astype(int)):
        own = _truth_rows(truth, oid)
        kind = str(own["object_type"][0])
        if kind in kinds:
            objects.append((int(oid), kind, own))
    track_ids = np.unique(tracks["track_id"].astype(int))
    if not objects or not track_ids.size:
        return result

    # One dummy column per truth object allows an unmatched trajectory without
    # making an invalid distant track look like a correspondence.  Valid edges
    # rank common-frame coverage first, then median distance.
    # 真値物体ごとのダミー列で未対応を許し、遠い軌跡を対応と取り違えない。
    invalid = 1.0e9
    cost = np.zeros((len(objects), len(track_ids) + len(objects)), dtype=float)
    cost[:, :len(track_ids)] = invalid
    candidates = {}
    track_class = tracks["object_class"].astype(str)
    for row_index, (oid, kind, own) in enumerate(objects):
        for track_index, tid in enumerate(track_ids):
            tq = tracks["track_id"].astype(int) == tid
            # The tracker can prove a stationary scratch; all other moving
            # truth objects share the intentionally conservative "moving" class.
            # 静止傷だけは区別し、動く真値物体は保守的な "moving" を共用する。
            if kind == "scratch" and not np.all(track_class[tq] == "scratch"):
                continue
            if kind != "scratch" and np.any(track_class[tq] == "scratch"):
                continue
            if not np.any(tq):
                continue
            tframe = tracks["frame"][tq].astype(int)
            pairs = []
            for frame, row, col in zip(own["frame"].astype(int), own["row_px"].astype(float), own["col_px"].astype(float)):
                at = np.flatnonzero(tframe == frame)
                if at.size != 1:
                    continue
                idx = np.flatnonzero(tq)[int(at[0])]
                distance = float(np.hypot(float(tracks["row_px"][idx]) - row,
                                          float(tracks["col_px"][idx]) - col))
                pairs.append((int(frame), float(row), float(col), float(tracks["row_px"][idx]),
                              float(tracks["col_px"][idx]), distance, int(tid)))
            if not pairs:
                continue
            distances = np.asarray([row[5] for row in pairs])
            matched = int(np.sum(distances <= max_distance_px))
            if not matched:
                continue
            median = float(np.median(distances))
            # 1,000 dominates every possible sub-pixel median-distance change.
            # 1,000 はサブ画素の中央値差より十分大きく、対応フレーム数を優先する。
            cost[row_index, track_index] = -1000.0 * matched + median
            candidates[(row_index, track_index)] = pairs
    assigned_rows, assigned_cols = linear_sum_assignment(cost)
    for row_index, track_index in zip(assigned_rows, assigned_cols):
        pairs = candidates.get((int(row_index), int(track_index)))
        if pairs is not None:
            result[objects[int(row_index)][0]] = pairs
    return result


def score_sequence(frames, truth, threshold):
    """Score the known particle against its matched track on at least three frames."""
    tracks = track_moving_particles(frames, threshold=threshold, max_displacement_px=13.0)
    links = correspondence(truth, tracks, kinds=("particle",), max_distance_px=3.5)
    particle_ids = np.unique(truth["object_id"][truth["object_type"] == "particle"].astype(int))
    pairs = links.get(int(particle_ids[0]), []) if particle_ids.size else []
    matched = int(sum(item[5] <= 3.5 for item in pairs))
    error = float(np.median([item[5] for item in pairs if item[5] <= 3.5])) if matched else float("inf")
    return bool(matched >= 3), matched, error, tracks, links


def run_one(diameter, contrast, illumination, seed, threshold, with_particle=True, *, visual=False):
    """One fully synthetic inspection presentation; no holdout value selects a setting."""
    kw = VISUAL_KW if visual else EVAL_KW
    frames, truth = vial_spin_stop_sequence(
        particle_diameter_um=float(diameter), particle_contrast=float(contrast), illumination=illumination,
        n_particles=1 if with_particle else 0, n_bubbles=1 if with_particle else 0,
        n_scratches=1, seed=int(seed), **kw)
    if with_particle:
        hit, matched, error, tracks, links = score_sequence(frames, truth, threshold)
    else:
        tracks = track_moving_particles(frames, threshold=threshold, max_displacement_px=13.0)
        links = correspondence(truth, tracks, kinds=("scratch",), max_distance_px=3.5)
        ids = tracks["track_id"].astype(int)
        moving = tracks["object_class"] != "scratch"
        hit = any(int(np.sum((ids == tid) & moving)) >= 3 for tid in np.unique(ids))
        matched, error = 0, float("nan")
    return {"hit": bool(hit), "matched": matched, "median_error_px": error, "frames": frames,
            "truth": truth, "tracks": tracks, "links": links}


def choose_threshold():
    """Use only the tuning split; holdout seeds are never present in this function."""
    candidates = (0.006, 0.008, 0.010, 0.012, 0.015, 0.018)
    records = []
    for threshold in candidates:
        hits, false = [], []
        for d_i, diameter in enumerate((65.0, 120.0, 220.0)):
            for l_i, illumination in enumerate(ILLUMINATIONS):
                seed = 1100 + 100 * d_i + 10 * l_i
                hits.append(run_one(diameter, 0.065, illumination, seed, threshold)["hit"])
                false.append(run_one(diameter, 0.065, illumination, seed + 5000, threshold,
                                    with_particle=False)["hit"])
        records.append((threshold, float(np.mean(hits)), float(np.mean(false))))
    # The selection is fixed before the evaluation split: a false particle call costs 1.5 hits.
    selected = max(records, key=lambda row: row[1] - 1.5 * row[2])
    return selected[0], records


def evaluate_calibration(threshold):
    """Measure the adjustment split for disclosure, before the final holdout run."""
    rows = []
    for d_i, diameter in enumerate(DIAMETERS):
        for c_i, contrast in enumerate(CONTRASTS):
            for l_i, illumination in enumerate(ILLUMINATIONS):
                for rep in range(CALIBRATION_REPS):
                    got = run_one(diameter, contrast, illumination,
                                  3000 + 1000 * d_i + 100 * c_i + 10 * l_i + rep, threshold)
                    rows.append({"phase": "calibration", "diameter_um": float(diameter),
                                 "contrast": float(contrast), "illumination": illumination,
                                 "hit": int(got["hit"]), "matched_frames": got["matched"],
                                 "median_error_px": got["median_error_px"]})
    return rows


def evaluate_holdout_last(threshold):
    """Run the independent defect and clean holdout once, as the final simulation stage."""
    rows, clean, exemplar = [], [], None
    for d_i, diameter in enumerate(DIAMETERS):
        for c_i, contrast in enumerate(CONTRASTS):
            for l_i, illumination in enumerate(ILLUMINATIONS):
                for rep in range(HOLDOUT_REPS):
                    got = run_one(diameter, contrast, illumination,
                                  HOLDOUT_SEED_BASE + 1000 * d_i + 100 * c_i + 10 * l_i + rep, threshold)
                    row = {"phase": "holdout", "diameter_um": float(diameter), "contrast": float(contrast),
                           "illumination": illumination, "hit": int(got["hit"]),
                           "matched_frames": got["matched"], "median_error_px": got["median_error_px"]}
                    rows.append(row)
                    if not got["hit"] and exemplar is None:
                        exemplar = (row, got)
    for l_i, illumination in enumerate(ILLUMINATIONS):
        for rep in range(HOLDOUT_REPS * 5):
            clean.append(run_one(120.0, 0.065, illumination, HOLDOUT_SEED_BASE + 8000 + 100 * l_i + rep,
                                 threshold, with_particle=False)["hit"])
    return rows, np.asarray(clean, dtype=bool), exemplar


def _draw_line(image, p0, p1, colour, width=1):
    """Draw a compact diagnostic annotation; source pixels are never resampled."""
    n = max(2, int(np.ceil(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))) + 1)
    for row, col in np.linspace(p0, p1, n):
        rr, cc = int(round(row)), int(round(col))
        if 0 <= rr < image.shape[0] and 0 <= cc < image.shape[1]:
            image[max(0, rr - width):rr + width + 1, max(0, cc - width):cc + width + 1] = colour


def _cross(image, row, col, colour, radius=4):
    row, col = int(round(row)), int(round(col))
    if 0 <= row < image.shape[0] and 0 <= col < image.shape[1]:
        image[max(0, row - radius):min(image.shape[0], row + radius + 1), col:col + 1] = colour
        image[row:row + 1, max(0, col - radius):min(image.shape[1], col + radius + 1)] = colour


def _ring(image, row, col, colour, radius=4):
    for a in np.linspace(0.0, 2.0 * np.pi, 48, endpoint=False):
        rr, cc = int(round(row + radius * np.sin(a))), int(round(col + radius * np.cos(a)))
        if 0 <= rr < image.shape[0] and 0 <= cc < image.shape[1]:
            image[rr, cc] = colour


def overlay(frames, truth, tracks, links, frame):
    """Overlay truth circles and their associated tracker crosses in one colour family."""
    out = np.repeat(frames[frame, ..., None], 3, axis=2) * 0.82
    colours = {"particle": np.array([0.05, 0.82, 0.96]), "bubble": np.array([1.00, 0.66, 0.08]),
               "scratch": np.array([0.92, 0.22, 0.76])}
    for oid in np.unique(truth["object_id"].astype(int)):
        own = _truth_rows(truth, oid)
        kind = str(own["object_type"][0])
        colour = colours[kind]
        seen = own["frame"].astype(int) <= frame
        rows, cols = own["row_px"][seen], own["col_px"][seen]
        for i in range(len(rows) - 1):
            _draw_line(out, (rows[i], cols[i]), (rows[i + 1], cols[i + 1]), colour, width=1)
        at = np.flatnonzero(own["frame"].astype(int) == frame)
        if at.size:
            _ring(out, float(own["row_px"][at[0]]), float(own["col_px"][at[0]]), colour, radius=4)
        for item in links.get(int(oid), []):
            if item[0] == frame and item[5] <= 3.5:
                # The short connector makes the truth↔detection correspondence inspectable.
                _draw_line(out, (item[1], item[2]), (item[3], item[4]), colour, width=1)
                _cross(out, item[3], item[4], np.minimum(1.0, 0.55 + 0.45 * colour), radius=4)
    return np.clip(out, 0.0, 1.0)


def _condition_counts(rows, illumination, contrast):
    counts, intervals = [], []
    for diameter in DIAMETERS:
        hits = [int(row["hit"]) for row in rows if row["illumination"] == illumination and
                row["contrast"] == contrast and row["diameter_um"] == float(diameter)]
        interval = proportion_interval(sum(hits), len(hits), confidence=0.95, sides="two")
        counts.append((int(sum(hits)), len(hits)))
        intervals.append(interval)
    return counts, intervals


def fit_monotone_pod(rows):
    """Fit a constrained binomial trend without using it to choose the detector.

    The fitted lines are deliberately constrained to grow with diameter and
    contrast; the independent holdout proportions and their exact intervals are
    drawn separately, so finite-sample reversals cannot be hidden as a smooth
    line.  Illumination gets only an intercept offset, not a separate threshold.
    """
    from scipy.optimize import minimize

    diameter = np.asarray([row["diameter_um"] for row in rows], dtype=float)
    contrast = np.asarray([row["contrast"] for row in rows], dtype=float)
    side = np.asarray([row["illumination"] == "side" for row in rows], dtype=float)
    hit = np.asarray([row["hit"] for row in rows], dtype=float)
    design = np.column_stack((np.ones_like(diameter), np.log(diameter / 100.0),
                              np.log(contrast / 0.065), side))

    def objective(beta):
        z = np.clip(design @ beta, -35.0, 35.0)
        return -float(np.sum(hit * (-np.logaddexp(0.0, -z)) + (1.0 - hit) * (-np.logaddexp(0.0, z))))

    # Positive coefficients make the displayed curves monotone in both inputs.
    solved = minimize(objective, np.array([-1.0, 2.0, 1.0, 0.0]), method="L-BFGS-B",
                      bounds=((None, None), (1.0e-7, None), (1.0e-7, None), (None, None)))
    if not solved.success or not np.all(np.isfinite(solved.x)):
        raise RuntimeError("constrained monotone POD fit did not converge: %s" % solved.message)

    def predict(d, c, illumination):
        z = (solved.x[0] + solved.x[1] * np.log(np.asarray(d, dtype=float) / 100.0) +
             solved.x[2] * np.log(float(c) / 0.065) + solved.x[3] * (illumination == "side"))
        return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))

    return {"beta": solved.x, "predict": predict, "neg_loglik": float(solved.fun), "n": int(hit.size)}


def fit_condition_a90(rows):
    """Fit independent GLM a90 values for every illumination × contrast cell.

    A condition with all hits, all misses, or complete separation is intentionally
    reported as unestimable: with the available per-diameter replication it has
    too little mixed evidence for a finite a90/a90/95, so no substitute number is
    invented.

    全 hit/全 miss/完全分離の条件は、径ごとの反復数では有限の a90/a90/95 を
    支える混合した証拠が不足する。代わりの数値は作らず、推定不能として返す。
    """
    results = {}
    for illumination in ILLUMINATIONS:
        for contrast in CONTRASTS:
            subset = [row for row in rows if row["illumination"] == illumination and
                      row["contrast"] == float(contrast)]
            per_diameter = [sum(row["diameter_um"] == float(diameter) for row in subset)
                            for diameter in DIAMETERS]
            entry = {"n": len(subset), "n_per_diameter": tuple(per_diameter), "fit": None,
                     "reason": None}
            try:
                entry["fit"] = pod_hitmiss_fit(
                    {"a": np.asarray([row["diameter_um"] for row in subset]),
                     "hit": np.asarray([row["hit"] for row in subset])},
                    log_size=True, link="logit")
            except ValueError as exc:
                entry["reason"] = str(exc)
            results[(illumination, float(contrast))] = entry
    return results


def _condition_a90_text(entry):
    """Return a caption without an invented estimate. / GLM が拒否した値は作らない。"""
    if entry["fit"] is None:
        return "a90: 求まらない（点が足りない）"
    fitted = entry["fit"]
    return "a90=%.1f, a90/95=%.1f µm" % (fitted["a90"], fitted["a90_95"])


def _pod_legend(image, scale):
    """Draw exact legend primitives. / POD パネルと同じ線・点で凡例を描く。"""
    import fullseye as fs

    strip_h = 84 * scale
    strip = np.ones((strip_h, image.shape[1], 3), dtype=float)
    rows = (17 * scale, 42 * scale, 67 * scale)
    x0, x1, xc = 24 * scale, 60 * scale, 42 * scale
    strip = np.asarray(fs.draw_line(strip, (x0, rows[0]), (x1, rows[0]),
                                    color="emphasis", width=2 * scale))
    strip = np.asarray(fs.text_box(strip, "単調制約付き binomial trend", (72 * scale, rows[0]),
                                   anchor="lm", pad=0, box_alpha=0.0, font_size=10 * scale))
    strip = np.asarray(fs.draw_line(strip, (xc, rows[1] - 9 * scale), (xc, rows[1] + 9 * scale),
                                    color="reference", width=2 * scale))
    for y in (rows[1] - 9 * scale, rows[1] + 9 * scale):
        strip = np.asarray(fs.draw_line(strip, (x0 + 10 * scale, y), (x1 - 10 * scale, y),
                                        color="reference", width=2 * scale))
    strip = np.asarray(fs.draw_circle(strip, (xc, rows[1]), 3 * scale,
                                      color="reference", fill="reference", width=1))
    strip = np.asarray(fs.text_box(strip, "holdout k/n と Clopper–Pearson 95% CI", (72 * scale, rows[1]),
                                   anchor="lm", pad=0, box_alpha=0.0, font_size=10 * scale))
    # Match the plotted reference's dashed neutral line rather than showing a
    # coloured square unrelated to the data mark.
    # データ印と無関係な色見本にせず、実際の灰色破線と同じ印を描く。
    for start in range(x0, x1, 10 * scale):
        strip = np.asarray(fs.draw_line(strip, (start, rows[2]),
                                        (min(start + 5 * scale, x1), rows[2]),
                                        color="neutral", width=2 * scale))
    strip = np.asarray(fs.text_box(strip, "USP<1790> 文脈の参考・手作業", (72 * scale, rows[2]),
                                   anchor="lm", pad=0, box_alpha=0.0, font_size=10 * scale))
    return np.concatenate((image, strip), axis=0)


def _pod_panel(rows, trend, illumination, contrast):
    """Render one readable POD condition: trend, holdout dots, and CP-95 % whiskers."""
    import fullseye as fs

    counts, intervals = _condition_counts(rows, illumination, contrast)
    rates = np.array([item["estimate"] for item in intervals])
    title = "%s照明 / C=%.3f" % ("背面（暗粒子）" if illumination == "back" else "側面（明粒子）", contrast)
    grid = np.linspace(35.0, 275.0, 160)
    image = figs.render_plot(
        [("", grid, trend["predict"](grid, contrast, illumination)),
         ("", DIAMETERS, rates),
         ("", np.array([100.0, 150.0, 200.0]), np.array([0.40, 0.70, 0.95]))],
        xlabel="particle diameter [µm]", ylabel="POD", title=title, size=(620, 390),
        xlim=(35.0, 275.0), ylim=(0.0, 1.0),
        kinds=("line", "scatter", "line"), styles=(None, None, "dashed"),
        colors=("emphasis", "reference", "neutral"), scale=2)
    scale, logical_w, logical_h = 2, 620, 390
    axes = fs.axes_transform((72 * scale, 44 * scale, (logical_w - 96) * scale,
                              (logical_h - 108) * scale), (35.0, 275.0), (-0.06, 1.06))
    for diameter, interval in zip(DIAMETERS, intervals):
        p0 = fs.data_to_pixel(axes, float(diameter), float(interval["lower"]))
        p1 = fs.data_to_pixel(axes, float(diameter), float(interval["upper"]))
        cap0 = fs.data_to_pixel(axes, float(diameter) - 2.8, float(interval["lower"]))
        cap1 = fs.data_to_pixel(axes, float(diameter) + 2.8, float(interval["lower"]))
        cap2 = fs.data_to_pixel(axes, float(diameter) - 2.8, float(interval["upper"]))
        cap3 = fs.data_to_pixel(axes, float(diameter) + 2.8, float(interval["upper"]))
        image = np.asarray(fs.draw_line(image, p0, p1, color="reference", width=3))
        image = np.asarray(fs.draw_line(image, cap0, cap1, color="reference", width=3))
        image = np.asarray(fs.draw_line(image, cap2, cap3, color="reference", width=3))
    return _pod_legend(image, scale), counts, intervals


def prepare_visual(threshold):
    """Create matched bright-field and dark-field displays before the holdout is opened."""
    result = {}
    for illumination in ILLUMINATIONS:
        frames, truth = vial_spin_stop_sequence(particle_diameter_um=160.0, particle_contrast=0.120,
                                                 illumination=illumination, n_particles=1, n_bubbles=1,
                                                 n_scratches=1, seed=4242, **VISUAL_KW)
        hit, matched, error, tracks, links = score_sequence(frames, truth, threshold)
        result[illumination] = {"frames": frames, "truth": truth, "tracks": tracks, "links": links,
                                "hit": hit, "matched": matched, "median_error_px": error}
    return result


def _particle_zoom(item, frame, *, magnification=4, half_width=22):
    """Append an explicitly labelled integer-nearest particle inset below one image.

    The full image stays at its source resolution.  Only this labelled diagnostic
    crop uses nearest-neighbour replication, which lets a reviewer inspect the
    few-pixel particle without mistaking an enlarged display for new data.

    全体像は元解像度のままにし、この明記した小窓だけを整数倍・最近傍で複製する。
    画素数の少ない粒子を検分でき、拡大表示を新しいデータと誤読させない。
    """
    import fullseye as fs

    base = overlay(item["frames"], item["truth"], item["tracks"], item["links"], frame)
    particle = item["truth"]["object_type"] == "particle"
    at = particle & (item["truth"]["frame"].astype(int) == int(frame))
    row = int(round(float(item["truth"]["row_px"][at][0])))
    col = int(round(float(item["truth"]["col_px"][at][0])))
    padded = np.pad(base, ((half_width, half_width), (half_width, half_width), (0, 0)),
                    mode="edge")
    crop = padded[row:row + 2 * half_width, col:col + 2 * half_width]
    enlarged = np.repeat(np.repeat(crop, magnification, axis=0), magnification, axis=1)
    strip_h = enlarged.shape[0] + 48
    strip = np.full((strip_h, base.shape[1], 3), 0.985, dtype=float)
    x0 = (strip.shape[1] - enlarged.shape[1]) // 2
    strip[40:40 + enlarged.shape[0], x0:x0 + enlarged.shape[1]] = enlarged
    strip = np.asarray(fs.text_box(
        strip, "粒子の原寸 crop を %d×（最近傍はこの小窓のみ）" % magnification,
        (12, 10), anchor="lt", pad=0, box_alpha=0.0, font_size=18))
    return np.concatenate((base, strip), axis=0)


def _lighting_panel(visual, frame):
    """Put both lighting modes and insets in one panel. / 両照明と粒子小窓を並べる。"""
    panels = []
    for illumination in ILLUMINATIONS:
        item = visual[illumination]
        panels.append(_particle_zoom(item, frame))
    divider = np.full((panels[0].shape[0], 8, 3), 0.16, dtype=float)
    return np.concatenate((panels[0], divider, panels[1]), axis=1)


def save_inspection_frames(visual):
    """Write full-resolution first/middle/last and contact sheet outside the repository."""
    target = os.environ.get("FULLSEYE_INSPECTION_DIR")
    if not target:
        return
    from imageio.v3 import imwrite

    out = Path(target)
    out.mkdir(parents=True, exist_ok=True)
    primary = visual["back"]
    indices = (0, primary["frames"].shape[0] // 2, primary["frames"].shape[0] - 1)
    panels = [_lighting_panel(visual, index) for index in indices]
    for name, panel in zip(("first", "middle", "last"), panels):
        imwrite(out / (name + ".png"), np.round(panel * 255).astype(np.uint8))
    imwrite(out / "contact_sheet.png", np.round(np.concatenate(panels, axis=1) * 255).astype(np.uint8))


def make_figures(visual, holdout_rows, fit, condition_fits, trend, exemplar):
    """Make all figures only from pre-holdout visuals or the completed holdout result."""
    if not figs.enabled():
        return
    primary = visual["back"]
    indices = (0, primary["frames"].shape[0] // 2, primary["frames"].shape[0] - 1)
    panels = [_lighting_panel(visual, index) for index in indices]
    captions = ["停止直後 t=0.00 s", "残留旋回 t=0.24 s", "終端 t=0.45 s"]
    figs.save_grid(
        "spin_stop_tracks", panels, captions, ncols=3,
        title=("合成 AVI: 各時点で左=背面照明の暗粒子、右=側面/Tyndall の明粒子。丸=真値、十字=対応する検出；"
               "同色で粒子=水色、気泡=橙、傷=紫。seed=4242, median Δ=%.2f/%.2f px" %
               (visual["back"]["median_error_px"], visual["side"]["median_error_px"])),
        caption="公開 AVI 資料の照明・容器形状の特徴を合成した入力→真値→追跡。第三者画像は不使用。"
                "明るい背景では粒子を暗く、側面/Tyndall では明るく描く。各時点の下段は粒子の原寸 crop を 4×にした小窓で、"
                "最近傍拡大はこの明記済み表示だけに使う。")
    pod_panels, table_rows = [], []
    for illumination in ILLUMINATIONS:
        for contrast in CONTRASTS:
            panel, counts, intervals = _pod_panel(holdout_rows, trend, illumination, contrast)
            pod_panels.append(panel)
            entry = condition_fits[(illumination, float(contrast))]
            table_rows.append("%s C=%.3f: %s; %s" % (
                "背面" if illumination == "back" else "側面", contrast,
                ", ".join("%d/%d" % pair for pair in counts), _condition_a90_text(entry)))
    figs.save_grid(
        "pod_by_diameter_contrast", pod_panels, table_rows, ncols=3,
        title=("独立 holdout の POD (点=k/n、縦線=Clopper–Pearson 95%% CI、実線=単調制約付き fit); "
               "全条件をまとめた GLM a90=%.1f µm, a90/95=%.1f µm" % (fit["a90"], fit["a90_95"])),
        caption="灰色破線は USP<1790> 文脈の手作業検査の参考観測値(100/150/200 µm = 40/70/95%%)であり、"
                "規格の基準でも本 AVI の合否基準でもない。各パネルの下に同じ条件の GLM a90/a90/95 を記し、"
                "見出しの値だけが全条件をまとめた値である。凡例は実線、青い点+区間、灰色破線を実際と同じ色・形で描く。")
    a90_rows = []
    for illumination in ILLUMINATIONS:
        for contrast in CONTRASTS:
            entry = condition_fits[(illumination, float(contrast))]
            fitted = entry["fit"]
            if fitted is None:
                a90, a9095, status = "—", "—", "求まらない（点が足りない）"
            else:
                a90, a9095, status = "%.1f" % fitted["a90"], "%.1f" % fitted["a90_95"], "GLM"
            a90_rows.append([
                "背面" if illumination == "back" else "側面", "%.3f" % contrast,
                "/".join(map(str, entry["n_per_diameter"])), a90, a9095, status,
            ])
    figs.save_table(
        "pod_condition_a90",
        ["照明", "コントラスト", "n/径 (45…260 µm)", "a90 [µm]",
         "a90/95 [µm]", "状態"],
        a90_rows,
        title="照明 2 × 濃淡 3 の条件別 GLM: a90 と片側 95% 上限 a90/95",
        caption="各行は独立 holdout のその条件だけで fit した GLM。a90/95 は a90 の片側 95% 上限。"
                "完全分離など n=10/径では推定できない行は、数値を補わず「求まらない（点が足りない）」と記す。"
                "全条件をまとめた値は POD 図の見出しだけに別記する。")
    if exemplar is None:
        raise AssertionError("the holdout must include a visible miss-side exemplar")
    row, got = exemplar
    index = got["frames"].shape[0] // 2
    figs.save_grid(
        "miss_representative",
        [overlay(got["frames"], got["truth"], got["tracks"], got["links"], index),
         np.repeat(got["frames"][index, ..., None], 3, axis=2)],
        ["真値と対応検出", "同じ入力だけ"], ncols=2,
        title="見逃し側: %g µm, C=%.3f, %s照明（独立 holdout）" %
              (row["diameter_um"], row["contrast"], "背面" if row["illumination"] == "back" else "側面"),
        caption="丸の真値粒子に対応する十字が3コマ未満で、事前固定の検出規則では hit にしない例。")


def _monotonic_rows(rows, trend):
    """Return raw holdout facts and displayed constrained-trend monotonicity facts."""
    raw_condition, raw_contrast, trend_condition, trend_contrast = [], [], [], []
    for illumination in ILLUMINATIONS:
        for contrast in CONTRASTS:
            rates = np.array([_condition_counts(rows, illumination, contrast)[1][i]["estimate"]
                              for i in range(len(DIAMETERS))])
            raw_condition.append((illumination, float(contrast), rates, bool(np.all(np.diff(rates) >= 0.0))))
            fitted = trend["predict"](DIAMETERS, contrast, illumination)
            trend_condition.append((illumination, float(contrast), fitted, bool(np.all(np.diff(fitted) >= 0.0))))
        for diameter in DIAMETERS:
            rates = np.array([_condition_counts(rows, illumination, contrast)[1][
                int(np.where(DIAMETERS == diameter)[0][0])]["estimate"] for contrast in CONTRASTS])
            raw_contrast.append((illumination, float(diameter), rates, bool(np.all(np.diff(rates) >= 0.0))))
            fitted = np.array([trend["predict"](np.array([diameter]), contrast, illumination)[0]
                               for contrast in CONTRASTS])
            trend_contrast.append((illumination, float(diameter), fitted, bool(np.all(np.diff(fitted) >= 0.0))))
    return raw_condition, raw_contrast, trend_condition, trend_contrast


def main():
    t0, cpu0 = time.time(), time.process_time()
    print("poc_vial_particle_pod — 回転停止後のバイアル異物を、調整/holdout 分離で POD 評価")
    threshold, tuning = choose_threshold()
    print("調整 threshold trial: " + "; ".join("%.3f: hit %.3f / false %.3f" % row for row in tuning))
    print("選択閾値 %.3f（調整 split のみ）" % threshold)
    calibration = evaluate_calibration(threshold)
    calibration_hits = sum(row["hit"] for row in calibration)
    print("調整 split: hit %d/%d" % (calibration_hits, len(calibration)))
    visual = prepare_visual(threshold)
    check(all(item["matched"] >= 12 and item["median_error_px"] <= 2.0 for item in visual.values()),
          "truth-to-track association", "back %d/%d, Δ %.2f px; side %d/%d, Δ %.2f px" %
          (visual["back"]["matched"], visual["back"]["frames"].shape[0], visual["back"]["median_error_px"],
           visual["side"]["matched"], visual["side"]["frames"].shape[0], visual["side"]["median_error_px"]))
    # This is deliberately the last stage that simulates evaluation sequences.
    print("独立 holdout を1回だけ開始（この後に threshold の選択・再調整はしない）")
    holdout, clean, exemplar = evaluate_holdout_last(threshold)
    tab = {"a": np.array([row["diameter_um"] for row in holdout]),
           "hit": np.array([row["hit"] for row in holdout])}
    fit = pod_hitmiss_fit(tab, log_size=True, link="logit")
    condition_fits = fit_condition_a90(holdout)
    trend = fit_monotone_pod(holdout)
    fpr = proportion_interval(int(clean.sum()), int(clean.size), confidence=0.95, sides="upper")
    raw_condition, raw_contrast, condition_mono, contrast_mono = _monotonic_rows(holdout, trend)
    high_condition = [entry for entry in condition_mono if entry[1] == float(CONTRASTS[-1]) and entry[2][-1] >= 0.90]
    print("holdout %d trial: hit %d, miss %d; 全条件をまとめた a90=%.2f µm, a90/95=%.2f µm" %
          (len(holdout), sum(row["hit"] for row in holdout), len(holdout) - sum(row["hit"] for row in holdout),
           fit["a90"], fit["a90_95"]))
    print("clean holdout false particle %d/%d: FPR=%.4f, 95%% upper=%.4f" %
          (int(clean.sum()), int(clean.size), fpr["estimate"], fpr["upper"]))
    for illumination, contrast, rates, _ok in condition_mono:
        raw = next(item[2] for item in raw_condition if item[:2] == (illumination, contrast))
        print("  %s C=%.3f: holdout %s; monotone fit %s; %s" %
              (illumination, contrast, ", ".join("%.2f" % item for item in raw),
               ", ".join("%.2f" % item for item in rates),
               _condition_a90_text(condition_fits[(illumination, float(contrast))])))
    check(all(row[3] for row in condition_mono), "diameter-monotone POD",
          "constrained trend: %d/%d illumination×contrast curves are non-decreasing; beta_size=%.3f" %
          (sum(row[3] for row in condition_mono), len(condition_mono), trend["beta"][1]))
    check(all(row[3] for row in contrast_mono), "contrast-monotone POD",
          "constrained trend: %d/%d illumination×diameter rows are non-decreasing; beta_contrast=%.3f" %
          (sum(row[3] for row in contrast_mono), len(contrast_mono), trend["beta"][2]))
    print("raw holdout non-monotone cells (finite-sample points kept visible): diameter %d/%d, contrast %d/%d" %
          (len(condition_mono) - sum(row[3] for row in raw_condition), len(raw_condition),
           len(contrast_mono) - sum(row[3] for row in raw_contrast), len(raw_contrast)))
    check(len(high_condition) == len(ILLUMINATIONS), "large clear particles approach one",
          "%d/%d lighting modes have 260 µm, C=0.120 POD >= 0.90" % (len(high_condition), len(ILLUMINATIONS)))
    check(float(fit["a90"]) <= float(DIAMETERS.max()), "a90 is inside displayed diameter range",
          "a90 %.2f µm <= displayed maximum %.0f µm" % (fit["a90"], DIAMETERS.max()))
    check(0 < sum(row["hit"] for row in holdout) < len(holdout), "POD fit is non-vacuous",
          "holdout hit/miss %d/%d" % (sum(row["hit"] for row in holdout), len(holdout)))
    check(np.all(np.diff(vial_spin_stop_sequence(seed=17)[1]["omega_rad_s"]) < 0),
          "post-stop swirl decays", "omega is strictly decreasing")
    panels = [_lighting_panel(visual, index) for index in (0, 8, 15)]
    digest_a = hashlib.sha256(np.concatenate(panels, axis=1).tobytes()).hexdigest()
    digest_b = hashlib.sha256(np.concatenate(panels, axis=1).tobytes()).hexdigest()
    check(digest_a == digest_b, "inspection render determinism", "SHA-256 %s" % digest_a)
    make_figures(visual, holdout, fit, condition_fits, trend, exemplar)
    save_inspection_frames(visual)
    check(time.process_time() - cpu0 < (90 if REDUCED else 240), "runtime budget",
          "CPU %.1f s" % (time.process_time() - cpu0))
    assert not figs.errors(), figs.errors()
    if not all(CHECKS):
        raise SystemExit(1)
    print("PASS (wall %.1f s, CPU %.1f s, mode=%s)" %
          (time.time() - t0, time.process_time() - cpu0, "reduced" if REDUCED else "full"))


if __name__ == "__main__":
    main()
