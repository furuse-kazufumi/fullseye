# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""バイアル異物検査: 回転停止後の粒子を合成真値で POD 評価する。

``vial_spin_stop_sequence`` は、止めた後に指数減衰する旋回流へ Stokes の
沈降・浮上を重ね、粒子・気泡・静止傷の画を先に真値から描く。
``track_moving_particles`` は時間中央値との差で動体を拾い、上向き軌跡を気泡、
静止成分を傷として分離する。この PoC は粒径 x コントラスト x 照明で、調整用
trial と独立 holdout を分け、holdout の hit/miss だけで POD と誤検出率を出す。

これは USP <1790> 等の正式な適格性基準ではなく、実機データによる検証もして
いない。低 Re・孤立球の Stokes 抗力、幾何学的な壁反射、簡略化した屈折という
モデルの範囲での、合成真値付きの第 1 段評価である。

Run:
    PYTHONPATH=. py -3.11 examples/poc_vial_particle_pod.py
    FULLSEYE_POC_BUDGET=reduced PYTHONPATH=. py -3.11 examples/poc_vial_particle_pod.py
    FULLSEYE_FIGURE_DIR=C:/tmp/vial_figs PYTHONPATH=. py -3.11 examples/poc_vial_particle_pod.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import examplefig as figs  # noqa: E402
from pod import pod_hitmiss_fit, proportion_interval  # noqa: E402
from vialops import track_moving_particles, vial_spin_stop_sequence  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
DIAMETERS = np.array([45.0, 65.0, 90.0, 120.0])
CONTRASTS = np.array([0.035, 0.065, 0.12])
ILLUMINATIONS = ("back", "side")
REPS = 2 if REDUCED else 8
CHECKS = []


def check(condition, name, detail):
    CHECKS.append(bool(condition))
    print("  [%s] %s — %s" % ("PASS" if condition else "FAIL", name, detail))


def _truth_particle(truth):
    m = truth["object_type"] == "particle"
    return truth["frame"][m].astype(int), truth["row_px"][m].astype(float), truth["col_px"][m].astype(float)


def score_sequence(frames, truth, threshold):
    """粒子真値を各フレームの移動検出へ照合。近傍3コマ以上を hit とする。"""
    tracks = track_moving_particles(frames, threshold=threshold, max_displacement_px=12.0)
    moving = tracks["object_class"] != "scratch"
    fr, rr, cc = _truth_particle(truth)
    matched = 0
    for frame, row, col in zip(fr, rr, cc):
        q = moving & (tracks["frame"].astype(int) == frame)
        if np.any(q) and float(np.min(np.hypot(tracks["row_px"][q].astype(float) - row,
                                                tracks["col_px"][q].astype(float) - col))) <= 3.5:
            matched += 1
    hit = matched >= 3
    return bool(hit), int(matched), tracks


def run_one(diameter, contrast, illumination, seed, threshold, with_particle=True):
    frames, truth = vial_spin_stop_sequence(n_frames=14, particle_diameter_um=float(diameter),
                                             particle_contrast=float(contrast), illumination=illumination,
                                             n_particles=1 if with_particle else 0, n_bubbles=1 if with_particle else 0,
                                             n_scratches=1, noise_sigma=0.012, seed=int(seed))
    if with_particle:
        hit, matched, tracks = score_sequence(frames, truth, threshold)
    else:
        tracks = track_moving_particles(frames, threshold=threshold, max_displacement_px=12.0)
        # A one-frame noise island is not an inspection call.  The same persistence
        # rule is applied to every clean holdout sequence before counting an FPR.
        ids = tracks["track_id"].astype(int)
        hit = any(cls == "particle" and int(np.sum(ids == tid)) >= 3
                  for tid, cls in zip(np.unique(ids),
                                      [tracks["object_class"][np.flatnonzero(ids == z)[0]] for z in np.unique(ids)]))
        matched = 0
    return {"hit": hit, "matched": matched, "frames": frames, "truth": truth, "tracks": tracks}


def choose_threshold():
    """調整 set のみで閾値を選ぶ。holdout の結果はここへ流さない。"""
    candidates = (0.009, 0.010, 0.011, 0.012, 0.014, 0.016)
    records = []
    for threshold in candidates:
        hits, false = [], []
        for k, diameter in enumerate((65.0, 90.0)):
            for illumination in ILLUMINATIONS:
                result = run_one(diameter, 0.065, illumination, 1000 + 41 * k + len(hits), threshold)
                hits.append(result["hit"])
                clean = run_one(diameter, 0.065, illumination, 2000 + 41 * k + len(false), threshold, with_particle=False)
                false.append(clean["hit"])
        # FPR is deliberately penalised harder than a miss for the tuning choice.
        records.append((threshold, float(np.mean(hits)), float(np.mean(false))))
    selected = max(records, key=lambda x: x[1] - 1.5 * x[2])
    return selected[0], records


def evaluate(threshold):
    rows, misses, exemplar = [], [], None
    for phase, seed_base in (("calibration", 3000), ("holdout", 9000)):
        for d_i, diameter in enumerate(DIAMETERS):
            for c_i, contrast in enumerate(CONTRASTS):
                for l_i, illumination in enumerate(ILLUMINATIONS):
                    for rep in range(REPS):
                        seed = seed_base + 1000 * d_i + 100 * c_i + 10 * l_i + rep
                        got = run_one(diameter, contrast, illumination, seed, threshold)
                        row = {"phase": phase, "diameter_um": float(diameter), "contrast": float(contrast),
                               "illumination": illumination, "hit": int(got["hit"]), "matched_frames": got["matched"],
                               "seed": seed}
                        rows.append(row)
                        if phase == "holdout" and not got["hit"]:
                            misses.append((row, got))
                            if exemplar is None:
                                exemplar = (row, got)
    # Clean, independent holdout trials for false positive interval.
    clean = []
    for illumination in ILLUMINATIONS:
        for rep in range(REPS * 6):
            clean.append(run_one(90.0, 0.065, illumination, 16000 + 100 * len(clean) + rep,
                                 threshold, with_particle=False)["hit"])
    return rows, np.asarray(clean, dtype=bool), misses, exemplar


def _line(img, p0, p1, colour):
    """Draw a simple antialiased-free diagnostic path; it is annotation, not data interpolation."""
    n = max(2, int(np.ceil(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))) + 1)
    for r, c in np.linspace(p0, p1, n):
        rr, cc = int(round(r)), int(round(c))
        if 0 <= rr < img.shape[0] and 0 <= cc < img.shape[1]:
            img[max(0, rr - 1):rr + 2, max(0, cc - 1):cc + 2] = colour


def overlay(frames, truth, tracks, frame):
    """True paths (cyan/amber/magenta) overlay the source image; detections are white crosses."""
    out = np.repeat(frames[frame, ..., None], 3, axis=2) * 0.78
    colours = {"particle": np.array([0.15, 0.80, 1.0]), "bubble": np.array([1.0, 0.68, 0.05]),
               "scratch": np.array([0.95, 0.20, 0.75])}
    for oid in np.unique(truth["object_id"]):
        q = (truth["object_id"] == oid) & (truth["frame"] <= frame)
        typ = str(truth["object_type"][q][0])
        r, c = truth["row_px"][q], truth["col_px"][q]
        for i in range(len(r) - 1):
            _line(out, (r[i], c[i]), (r[i + 1], c[i + 1]), colours[typ])
    q = (tracks["frame"].astype(int) == frame) & (tracks["object_class"] != "scratch")
    for r, c in zip(tracks["row_px"][q].astype(float), tracks["col_px"][q].astype(float)):
        rr, cc = int(round(r)), int(round(c))
        out[max(0, rr - 2):rr + 3, cc] = 1.0
        out[rr, max(0, cc - 2):cc + 3] = 1.0
    return np.clip(out, 0.0, 1.0)


def make_figures(threshold, rows, misses, exemplar):
    if not figs.enabled():
        return
    representative = run_one(90.0, 0.065, "back", 4242, threshold)
    points = (0, 2, 13)
    figs.save_grid("spin_stop_tracks", [overlay(representative["frames"], representative["truth"], representative["tracks"], i)
                                         for i in points],
                   ["回転中相当 t=0", "停止直後 t=0.08 s", "終端 t=0.52 s"], ncols=3,
                   title="真値軌跡: 粒子=水色、気泡=橙、傷=紫; 白十字=追跡検出",
                   caption="同じ run(seed=4242)の入力画像へ、粒子・気泡・静止傷の真値軌跡を色分けして重ねた。")
    holdout = [r for r in rows if r["phase"] == "holdout"]
    series, colours = [], []
    for illumination, colour in (("back", "emphasis"), ("side", "right")):
        for contrast, style in zip(CONTRASTS, (None, "dashed", "dotted")):
            rate = [np.mean([r["hit"] for r in holdout if r["illumination"] == illumination and
                            r["contrast"] == contrast and r["diameter_um"] == d]) for d in DIAMETERS]
            series.append(("%s C=%.3f" % ("背面" if illumination == "back" else "側面", contrast), DIAMETERS, rate))
            colours.append(colour)
    figs.save_plot("pod_by_diameter_contrast", series, xlabel="粒径 [µm]", ylabel="holdout POD",
                   title="粒径 × コントラスト × 照明の POD(点は独立 holdout)", colors=colours,
                   styles=[None, "dashed", "dotted"] * 2, ylim=(0.0, 1.0), size=(760, 460),
                   caption="調整 trial は曲線選択だけに使い、この図と数値は独立 holdout の hit/miss から集計した。")
    if exemplar is None:
        exemplar = (None, run_one(45.0, 0.035, "side", 5555, threshold))
    row, got = exemplar
    i = 7
    figs.save_grid("miss_representative", [overlay(got["frames"], got["truth"], got["tracks"], i),
                                            np.repeat(got["frames"][i, ..., None], 3, axis=2)],
                   ["真値と追跡を重ねた見逃し", "入力だけ(同じコマ)"], ncols=2,
                   title="見逃し側の代表コマ", caption="水色の粒子真値が追跡の白十字にならない例。"
                   + (" 条件: %g µm, C=%g, %s。" % (row["diameter_um"], row["contrast"], row["illumination"]) if row else ""))


def save_inspection_frames(threshold):
    """Repo 外の確認先へ first/middle/last/contact sheet を書く。"""
    target = os.environ.get("FULLSEYE_INSPECTION_DIR")
    if not target:
        return
    from imageio.v3 import imwrite
    out = Path(target)
    out.mkdir(parents=True, exist_ok=True)
    got = run_one(90.0, 0.065, "back", 4242, threshold)
    panels = [overlay(got["frames"], got["truth"], got["tracks"], i) for i in (0, 7, 13)]
    for name, panel in zip(("first", "middle", "last"), panels):
        imwrite(out / (name + ".png"), np.round(panel * 255).astype(np.uint8))
    imwrite(out / "contact_sheet.png", np.round(np.concatenate(panels, axis=1) * 255).astype(np.uint8))


def main():
    t0, cpu0 = time.time(), time.process_time()
    print("poc_vial_particle_pod — 回転停止後のバイアル異物、POD は独立 holdout で評価")
    threshold, tuning = choose_threshold()
    print("調整 trial: " + "; ".join("閾値 %.3f: hit %.3f / false %.3f" % r for r in tuning))
    print("選択閾値 %.3f (調整 set のみ)" % threshold)
    rows, clean, misses, exemplar = evaluate(threshold)
    holdout = [r for r in rows if r["phase"] == "holdout"]
    # POD GLM is deliberately fit to all holdout contrasts/illumination: contrast is reported as stratified curves above.
    tab = {"a": np.array([r["diameter_um"] for r in holdout]), "hit": np.array([r["hit"] for r in holdout])}
    fit = pod_hitmiss_fit(tab, log_size=True, link="logit")
    fpr = proportion_interval(int(clean.sum()), int(clean.size), confidence=0.95, sides="upper")
    by_condition = {}
    for illumination in ILLUMINATIONS:
        for contrast in CONTRASTS:
            group = [r["hit"] for r in holdout if r["illumination"] == illumination and r["contrast"] == contrast]
            by_condition[(illumination, contrast)] = float(np.mean(group))
    print("holdout %d trial: hit %d, miss %d; a90=%.2f µm, a90/95=%.2f µm" %
          (len(holdout), sum(r["hit"] for r in holdout), len(misses), fit["a90"], fit["a90_95"]))
    print("clean holdout false particle %d/%d: FPR=%.4f, 95%% upper=%.4f" %
          (int(clean.sum()), int(clean.size), fpr["estimate"], fpr["upper"]))
    for (illumination, contrast), rate in by_condition.items():
        print("  %s contrast %.3f: POD=%.3f" % (illumination, contrast, rate))
    check(0 < sum(r["hit"] for r in holdout) < len(holdout), "POD fit is non-vacuous", "hit/miss %d/%d" % (sum(r["hit"] for r in holdout), len(holdout)))
    check(np.all(np.diff(vial_spin_stop_sequence(seed=17)[1]["omega_rad_s"]) < 0), "post-stop swirl decays", "omega is strictly decreasing")
    check(time.process_time() - cpu0 < (25 if REDUCED else 120), "runtime budget", "CPU %.1f s" % (time.process_time() - cpu0))
    make_figures(threshold, rows, misses, exemplar)
    save_inspection_frames(threshold)
    assert not figs.errors(), figs.errors()
    if not all(CHECKS):
        raise SystemExit(1)
    print("PASS (wall %.1f s, CPU %.1f s, mode=%s)" %
          (time.time() - t0, time.process_time() - cpu0, "reduced" if REDUCED else "full"))


if __name__ == "__main__":
    main()
