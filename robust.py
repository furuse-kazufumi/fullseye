"""Robust multi-seed champion selection — honest handling of evolution variance.

Single-seed evolution is high variance (a seed can collapse below trivial). The
standard, honest fix is to run N independent seeds and keep the best — but
selection MUST stay on TRAIN so the holdout never leaks into model choice. This
runs N seeds, picks the champion with the best TRAIN score, reports its holdout,
and DISCLOSES the full per-seed spread (min/max/mean holdout, collapses, and how
many beat the hand-built baseline). Best-of-N with the variance shown — not a
cherry-picked single seed.

Two holdouts are reported, and they are NOT interchangeable. The OBSERVED holdout
(seed+10000) is the split evolve.run scores every generation: never selected on,
but not untouched either. The LOCKED holdout (seed+20000) is scored exactly once
per seed on the final champion — that is the genuinely untouched number. Every
`holdout_*`/`n_*` field below is the observed split; its `*_locked` twin is the
locked one. If a champion carries no locked score, the locked fields stay null
rather than quietly reusing the observed value.

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
    # The locked tally MUST use a locked-split baseline, not the observed one, or a
    # number labelled "locked" is compared against an observed-split threshold. These
    # are null for a baseline file written before locked-split scoring existed.
    hand_lk = base.get("hand", {}).get("locked_holdout")
    trivial_lk = base.get("trivial", {}).get("locked_holdout")
    unit = None

    champs = []
    for s in range(a.seeds):
        c = evolve.run(a.problem, a.workdir, a.gens, a.pop, s, verbose=False)
        unit = c["unit"]
        champs.append(c)
        print("  seed %d: train %.3f holdout %.3f" % (s, c["train"], c["holdout"]))

    # SELECT on TRAIN only (holdout stays pure); report the selected champ's holdout.
    best = max(champs, key=lambda c: c["train"])
    # Persist the TRAIN-selected champion: evolve.run overwrote champion_<problem>.json
    # with EACH seed, so without this the file holds the last seed, not the best-of-N.
    (wd / f"champion_{a.problem}.json").write_text(json.dumps(best, indent=2), encoding="utf-8")
    hold = np.array([c["holdout"] for c in champs], float)
    n_beat = int(np.sum(hold > hand)) if hand is not None else None
    n_collapse = int(np.sum(hold < trivial)) if trivial is not None else None

    # The tally above is on the OBSERVED holdout (seed+10000) — the split evolve.run
    # scores EVERY generation. Tally the LOCKED holdout (seed+20000, scored once per
    # seed) too instead of letting the observed number stand in for the untouched one.
    # Fail-closed twice: a champion without a locked score leaves `locked` null, AND
    # the locked beat/collapse tally uses the LOCKED-split baseline (hand_lk/trivial_lk)
    # — never the observed-split threshold — so it is null unless that baseline exists.
    lk = [c.get("locked_holdout") for c in champs]
    locked = np.array(lk, float) if lk and all(v is not None for v in lk) else None
    n_beat_lk = int(np.sum(locked > hand_lk)) if (locked is not None and hand_lk is not None) else None
    n_collapse_lk = int(np.sum(locked < trivial_lk)) if (locked is not None and trivial_lk is not None) else None

    def _spread(x):
        return None if x is None else {"min": float(x.min()), "max": float(x.max()),
                                       "mean": round(float(x.mean()), 4), "std": round(float(x.std()), 4)}

    out = {
        "problem": a.problem, "unit": unit, "seeds": a.seeds, "gens": a.gens,
        "baseline_hand": hand, "baseline_trivial": trivial,
        "split_note": ("holdout_*/n_beat_hand/n_collapse_below_trivial = OBSERVED split "
                       "(seed+10000, scored every generation, never selected on); "
                       "*_locked = LOCKED split (seed+20000, scored once per seed)"),
        "selected_by_train": {"seed": best["seed"], "train": best["train"],
                              "holdout": best["holdout"],
                              "locked_holdout": best.get("locked_holdout"),
                              "pipeline": best["pipeline"]},
        "holdout_spread": _spread(hold),
        "n_beat_hand": n_beat, "n_collapse_below_trivial": n_collapse,
        "locked_holdout_spread": _spread(locked),
        "n_beat_hand_locked": n_beat_lk, "n_collapse_below_trivial_locked": n_collapse_lk,
    }
    (wd / f"robust_{a.problem}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("\n[robust:%s] %d seeds, hand baseline=%s %s" % (a.problem, a.seeds, hand, unit))
    print("  selected-by-train champion: train %.3f observed-holdout %.3f locked-holdout %s (seed %d)"
          % (best["train"], best["holdout"],
             "n/a" if best.get("locked_holdout") is None else "%.3f" % best["locked_holdout"],
             best["seed"]))
    print("  observed-holdout spread (seed+10000, seen every gen): min %.3f / mean %.3f / max %.3f (std %.3f)"
          % (hold.min(), hold.mean(), hold.max(), hold.std()))
    if hand is not None:
        print("    seeds beating hand baseline: %d/%d   |   collapses (< trivial %.3f): %d/%d"
              % (n_beat, a.seeds, trivial, n_collapse, a.seeds))
    if locked is not None:
        print("  LOCKED-holdout spread (seed+20000, scored once): min %.3f / mean %.3f / max %.3f (std %.3f)"
              % (locked.min(), locked.mean(), locked.max(), locked.std()))
        if hand is not None:
            print("    seeds beating hand baseline: %d/%d   |   collapses (< trivial %.3f): %d/%d"
                  % (n_beat_lk, a.seeds, trivial, n_collapse_lk, a.seeds))
    else:
        print("  LOCKED-holdout: not available (champions carry no 'locked_holdout') — not substituted")
    print("  -> honest: best-of-N (train-selected) = %.3f observed / %s locked; variance disclosed above."
          % (best["holdout"], "n/a" if best.get("locked_holdout") is None else "%.3f" % best["locked_holdout"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
