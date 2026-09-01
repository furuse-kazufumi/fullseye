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

**The floors are measured here, not imported.** Earlier runs read hand/trivial out
of ``baseline_<problem>.json`` and, when that file was absent, wrote
``baseline_hand: null`` and carried on — so the published comparison numbers lived
only in whoever's terminal computed them, and the artifact could never be checked
against the claim. The floors are now scored directly (two pipelines over
``n_holdout`` items, well under a second) on the SAME split config evolve.run
resolves, BEFORE any evolution runs in this process. The baseline file, when it
exists, is a cross-check: a disagreement is recorded in ``baseline_file_mismatch``
instead of one of the two numbers silently winning.

    py -3.11 robust.py --problem denoise --seeds 5 --gens 20
    py -3.11 robust.py --problem denoise --seeds 5 --gens 20 --isolate

``--isolate`` runs every seed in a FRESH child process. Measured 2026-09-02: the
chain fuzzer's reachability depends on what ran earlier in the same interpreter
(445/515 from a clean process vs 433/515 after 20 ``evolve.run`` calls, same seed
and args), so any measurement that has to be quotable should not share process
state with a previous one. Isolation costs one interpreter start per seed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

import baseline
import evolve
import problems

HERE = Path(__file__).resolve().parent


def _commit() -> str:
    """Current HEAD, for stamping WHEN a number was measured. Read-only, fail-soft.

    op fixes land continuously and move these scores; a table without a commit is
    a number nobody can ever reproduce.
    """
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(HERE),
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else "unknown"


def _child_env() -> dict:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run_seed_isolated(problem, workdir, gens, pop, seed) -> dict:
    """One evolution seed in a FRESH interpreter; returns its champion dict.

    Each seed gets its own sub-workdir so the per-seed ``champion_*``/``pareto_*``
    writes cannot clobber each other. The baseline file is copied in first because
    ``evolve.run`` resolves its split config (and its seeded random genome) from it
    — without the copy the child would silently evolve on a different extraction.
    """
    wd = Path(workdir)
    seed_dir = wd / f"_seed{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    src = wd / f"baseline_{problem}.json"
    if src.exists():
        shutil.copyfile(src, seed_dir / src.name)
    cmd = [sys.executable, str(HERE / "evolve.py"), "--problem", problem,
           "--workdir", str(seed_dir), "--gens", str(gens), "--pop", str(pop),
           "--seed", str(seed)]
    r = subprocess.run(cmd, cwd=str(HERE), env=_child_env(),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"[abort] isolated seed {seed} failed (rc={r.returncode})\n"
                         f"{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    champ = seed_dir / f"champion_{problem}.json"
    if not champ.exists():
        raise SystemExit(f"[abort] isolated seed {seed} wrote no champion at {champ}")
    return json.loads(champ.read_text(encoding="utf-8"))


def resolve_floors(measured, file_base):
    """Merge the freshly measured floors with the ones on disk.

    Measured always wins as the reported value (it is the one scored on the config
    this run actually used); the file is kept as a cross-check. Returns
    ``(floors, sources, mismatches)`` where *floors* has the four numbers, *sources*
    says where each came from, and *mismatches* lists every field where the file
    disagrees by more than 1e-4 — disclosed, never averaged or silently dropped.
    """
    fields = {                                    # report key -> (measured, file)
        "hand": (("hand", "holdout"), ("hand", "holdout")),
        "trivial": (("trivial", "holdout"), ("trivial", "holdout")),
        "hand_locked": (("hand", "locked"), ("hand", "locked_holdout")),
        "trivial_locked": (("trivial", "locked"), ("trivial", "locked_holdout")),
    }
    floors, sources, mismatches = {}, {}, []
    for key, ((mg, ms), (fg, fs)) in fields.items():
        mine = measured[mg][ms]
        theirs = (file_base.get(fg) or {}).get(fs)
        floors[key] = mine
        sources[key] = "measured" if theirs is None else "measured (file agrees)"
        if theirs is not None and abs(float(theirs) - float(mine)) > 1e-4:
            sources[key] = "measured (file DISAGREES — see baseline_file_mismatch)"
            mismatches.append({"field": key, "measured": mine, "baseline_file": theirs})
    return floors, sources, mismatches


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problem", default="denoise", choices=list(problems.PROBLEMS))
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--gens", type=int, default=20)
    ap.add_argument("--pop", type=int, default=16)
    ap.add_argument("--isolate", action="store_true",
                    help="run each seed in a fresh child process (no shared interpreter state)")
    a = ap.parse_args()
    if a.seeds < 1:
        ap.error("--seeds must be >= 1 (nothing to select from otherwise)")

    wd = Path(a.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    bpath = wd / f"baseline_{a.problem}.json"
    file_base = json.loads(bpath.read_text(encoding="utf-8")) if bpath.exists() else {}

    # ---- floors FIRST, in a still-clean process ---------------------------- #
    # Scored on the config evolve.run will resolve for this workdir, so the floor
    # and the champion are the same extraction. Doing this before any evolve.run
    # also keeps the floors out of reach of the in-process state contamination
    # that --isolate exists to avoid.
    prob = problems.PROBLEMS[a.problem]
    cfg = baseline.resolve_cfg(a.workdir, a.problem)
    measured = baseline.measure_baselines(prob, cfg)
    floors, floor_src, mismatch = resolve_floors(measured, file_base)
    hand, trivial = floors["hand"], floors["trivial"]
    hand_lk, trivial_lk = floors["hand_locked"], floors["trivial_locked"]
    if any(v is None for v in floors.values()):    # fail-closed: never publish a null floor
        raise SystemExit("[abort] a baseline floor came out null — refusing to write "
                         "a result that cannot be compared against anything")
    unit = prob.unit
    t0 = time.perf_counter()

    champs = []
    for s in range(a.seeds):
        c = (run_seed_isolated(a.problem, a.workdir, a.gens, a.pop, s) if a.isolate
             else evolve.run(a.problem, a.workdir, a.gens, a.pop, s, verbose=False))
        unit = c["unit"]
        champs.append(c)
        print("  seed %d: train %.3f holdout %.3f locked %s" %
              (s, c["train"], c["holdout"],
               "n/a" if c.get("locked_holdout") is None else "%.3f" % c["locked_holdout"]))

    # SELECT on TRAIN only (holdout stays pure); report the selected champ's holdout.
    best = max(champs, key=lambda c: c["train"])
    # Persist the TRAIN-selected champion: evolve.run overwrote champion_<problem>.json
    # with EACH seed, so without this the file holds the last seed, not the best-of-N.
    (wd / f"champion_{a.problem}.json").write_text(json.dumps(best, indent=2), encoding="utf-8")
    hold = np.array([c["holdout"] for c in champs], float)
    n_beat = int(np.sum(hold > hand))
    n_collapse = int(np.sum(hold < trivial))

    # The tally above is on the OBSERVED holdout (seed+10000) — the split evolve.run
    # scores EVERY generation. Tally the LOCKED holdout (seed+20000, scored once per
    # seed) too instead of letting the observed number stand in for the untouched one.
    # Fail-closed on the champion side: a champion without a locked score leaves
    # `locked` null. The baseline side can no longer be null — it is measured here.
    lk = [c.get("locked_holdout") for c in champs]
    locked = np.array(lk, float) if lk and all(v is not None for v in lk) else None
    n_beat_lk = int(np.sum(locked > hand_lk)) if locked is not None else None
    n_collapse_lk = int(np.sum(locked < trivial_lk)) if locked is not None else None

    def _spread(x):
        return None if x is None else {"min": round(float(x.min()), 4),
                                       "max": round(float(x.max()), 4),
                                       "mean": round(float(x.mean()), 4),
                                       "std": round(float(x.std(ddof=0)), 4)}

    best_lk = best.get("locked_holdout")
    out = {
        "problem": a.problem, "unit": unit, "seeds": a.seeds, "gens": a.gens,
        "pop": a.pop, "isolated_seeds": bool(a.isolate),
        # WHEN this was measured. op fixes move these scores, so a table without a
        # commit is unreproducible by construction.
        "commit": _commit(),
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": sys.version.split()[0],
        "elapsed_s": round(time.perf_counter() - t0, 1),
        "split_config": cfg,
        "baseline_hand": hand, "baseline_trivial": trivial,
        "baseline_hand_locked": hand_lk, "baseline_trivial_locked": trivial_lk,
        "baseline_hand_train": measured["hand"]["train"],
        "baseline_trivial_train": measured["trivial"]["train"],
        "baseline_pipeline": measured["hand"]["pipeline"],
        "baseline_source": floor_src,
        "baseline_file_mismatch": mismatch,
        "split_note": ("holdout_*/n_beat_hand/n_collapse_below_trivial = OBSERVED split "
                       "(seed+10000, scored every generation, never selected on) vs the "
                       "OBSERVED-split hand/trivial baseline; *_locked = LOCKED split "
                       "(seed+20000, scored once per seed) vs the LOCKED-split baseline "
                       "(baseline_*_locked). Both baselines are measured in this run on "
                       "split_config, never carried over from another extraction."),
        "selected_by_train": {"seed": best["seed"], "train": best["train"],
                              "holdout": best["holdout"],
                              "locked_holdout": best_lk,
                              "pipeline": best["pipeline"]},
        "per_seed": [{"seed": c["seed"], "train": c["train"], "holdout": c["holdout"],
                      "locked_holdout": c.get("locked_holdout"),
                      "pipeline": c["pipeline"]} for c in champs],
        "holdout_spread": _spread(hold),
        "n_beat_hand": n_beat, "n_collapse_below_trivial": n_collapse,
        "locked_holdout_spread": _spread(locked),
        "n_beat_hand_locked": n_beat_lk, "n_collapse_below_trivial_locked": n_collapse_lk,
        # observed - locked, per row. A large gap on the champion with a small gap on
        # the floors is the signature of a champion that fitted the observed split.
        "observed_minus_locked": {
            "trivial": round(trivial - trivial_lk, 4),
            "hand": round(hand - hand_lk, 4),
            "selected_champion": (None if best_lk is None
                                  else round(best["holdout"] - best_lk, 4)),
        },
        # Everything a published table row needs, in one place, so the row is read
        # off the artifact instead of recomputed in a terminal that leaves no trace.
        "table_row": {
            "problem": a.problem, "in_sort": prob.in_sort, "unit": unit,
            "identity_locked": trivial_lk, "hand_locked": hand_lk,
            "evolved_locked": best_lk,
            "identity_observed": trivial, "hand_observed": hand,
            "evolved_observed": best["holdout"],
            "evolved_locked_std": None if locked is None else round(float(locked.std(ddof=0)), 4),
            "evolved_observed_std": round(float(hold.std(ddof=0)), 4),
            "vs_hand_locked_pct": (None if (best_lk is None or abs(hand_lk) < 1e-12)
                                   else round(100.0 * (best_lk - hand_lk) / abs(hand_lk), 1)),
            "vs_hand_locked_abs": None if best_lk is None else round(best_lk - hand_lk, 4),
        },
    }
    (wd / f"robust_{a.problem}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("\n[robust:%s] %d seeds%s, floors measured on %s" %
          (a.problem, a.seeds, " (isolated)" if a.isolate else "", json.dumps(cfg)))
    print("  identity/hand: observed %.4f / %.4f   locked %.4f / %.4f  [%s]"
          % (trivial, hand, trivial_lk, hand_lk, floor_src["hand_locked"]))
    if mismatch:
        print("  !! baseline file disagrees with the measured floor: %s" % json.dumps(mismatch))
    print("  selected-by-train champion: train %.3f observed-holdout %.3f locked-holdout %s (seed %d)"
          % (best["train"], best["holdout"],
             "n/a" if best_lk is None else "%.3f" % best_lk, best["seed"]))
    print("  observed-holdout spread (seed+10000, seen every gen): min %.3f / mean %.3f / max %.3f (std %.3f)"
          % (hold.min(), hold.mean(), hold.max(), hold.std()))
    print("    seeds beating hand baseline: %d/%d   |   collapses (< trivial %.3f): %d/%d"
          % (n_beat, a.seeds, trivial, n_collapse, a.seeds))
    if locked is not None:
        print("  LOCKED-holdout spread (seed+20000, scored once): min %.3f / mean %.3f / max %.3f (std %.3f)"
              % (locked.min(), locked.mean(), locked.max(), locked.std()))
        print("    seeds beating hand baseline (locked): %d/%d   |   collapses (< trivial %.3f): %d/%d"
              % (n_beat_lk, a.seeds, trivial_lk, n_collapse_lk, a.seeds))
    else:
        print("  LOCKED-holdout: not available (champions carry no 'locked_holdout') — not substituted")
    print("  -> honest: best-of-N (train-selected) = %.3f observed / %s locked; variance disclosed above."
          % (best["holdout"], "n/a" if best_lk is None else "%.3f" % best_lk))
    print("  -> commit %s" % out["commit"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
