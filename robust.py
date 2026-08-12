"""Robust multi-seed champion selection — honest handling of evolution variance.

Single-seed evolution is high variance (a seed can collapse below trivial). The
standard, honest fix is to run N independent seeds and keep the best — but
selection MUST stay on TRAIN so the holdout never leaks into model choice. This
runs N seeds, picks the champion with the best TRAIN score, reports its holdout,
and DISCLOSES the full per-seed spread (min/max/mean holdout, collapses, and how
many beat the hand-built baseline). Best-of-N with the variance shown — not a
cherry-picked single seed.

    py -3.11 robust.py --problem denoise --seeds 5 --gens 20
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import evolve
import problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problem", default="denoise", choices=list(problems.PROBLEMS))
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--gens", type=int, default=20)
    ap.add_argument("--pop", type=int, default=16)
    a = ap.parse_args()

    wd = Path(a.workdir)
    base = json.loads((wd / f"baseline_{a.problem}.json").read_text(encoding="utf-8")) \
        if (wd / f"baseline_{a.problem}.json").exists() else {}
    hand = base.get("hand", {}).get("holdout")       # baseline.py writes 'holdout', not 'score'
    trivial = base.get("trivial", {}).get("holdout")
    unit = None

    champs = []
    for s in range(a.seeds):
        c = evolve.run(a.problem, a.workdir, a.gens, a.pop, s, verbose=False)
        unit = c["unit"]
        champs.append(c)
        print("  seed %d: train %.3f holdout %.3f" % (s, c["train"], c["holdout"]))

    # SELECT on TRAIN only (holdout stays pure); report the selected champ's holdout.
    best = max(champs, key=lambda c: c["train"])
    hold = np.array([c["holdout"] for c in champs], float)
    n_beat = int(np.sum(hold > hand)) if hand is not None else None
    n_collapse = int(np.sum(hold < trivial)) if trivial is not None else None

    out = {
        "problem": a.problem, "unit": unit, "seeds": a.seeds, "gens": a.gens,
        "baseline_hand": hand, "baseline_trivial": trivial,
        "selected_by_train": {"seed": best["seed"], "train": best["train"],
                              "holdout": best["holdout"], "pipeline": best["pipeline"]},
        "holdout_spread": {"min": float(hold.min()), "max": float(hold.max()),
                           "mean": round(float(hold.mean()), 4), "std": round(float(hold.std()), 4)},
        "n_beat_hand": n_beat, "n_collapse_below_trivial": n_collapse,
    }
    (wd / f"robust_{a.problem}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("\n[robust:%s] %d seeds, hand baseline=%s %s" % (a.problem, a.seeds, hand, unit))
    print("  selected-by-train champion: train %.3f holdout %.3f (seed %d)"
          % (best["train"], best["holdout"], best["seed"]))
    print("  holdout spread: min %.3f / mean %.3f / max %.3f (std %.3f)"
          % (hold.min(), hold.mean(), hold.max(), hold.std()))
    if hand is not None:
        print("  seeds beating hand baseline: %d/%d   |   collapses (< trivial %.3f): %d/%d"
              % (n_beat, a.seeds, trivial, n_collapse, a.seeds))
    print("  -> honest: best-of-N (train-selected) = %.3f; variance disclosed above." % best["holdout"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
