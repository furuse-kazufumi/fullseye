"""Accuracy benchmark — does evolution beat the null, across every problem?

For each problem it builds a fixed train/holdout split, measures the honest floor
(trivial = do nothing, hand = the hand-built pipeline, random = best-of-N random
selected on train), evolves a champion (selection on TRAIN only), and reports every
score on the SAME held-out set plus the generalization gap. Emits a standing table
so "the champion beats the null on holdout" is evidence, not a claim.

    py -3.11 accuracy_bench.py                     # short-budget sweep -> docs/ACCURACY_BENCH.md
    py -3.11 accuracy_bench.py --gens 40 --pop 24  # heavier run

Higher is better for every unit (dB PSNR, F1, accuracy, ...); the gap = train - holdout.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np

import evolve
import ops
import problems


def bench_problem(name, workdir, gens, pop, seed, n_train, n_holdout, size, random_samples):
    prob = problems.PROBLEMS[name]
    tr = prob.make(n_train, size, seed)
    ho = prob.make(n_holdout, size, seed + 10_000)

    trivial = float(prob.score_stages(problems.trivial_stages(), ho))
    hand = float(prob.score_stages(prob.hand_stages(), ho))

    rng = np.random.default_rng(seed + 777)
    best_g, best_tr = None, -1e18
    for _ in range(random_samples):
        g = rng.random(ops.GENOME_LEN)
        s = prob.score(g, tr)
        if s > best_tr:
            best_tr, best_g = s, g
    random_ho = float(prob.score(best_g, ho))

    # evolve.run reads this for the config + a warm-start random genome
    (Path(workdir) / f"baseline_{name}.json").write_text(json.dumps({
        "config": {"n_train": n_train, "n_holdout": n_holdout, "size": size,
                   "seed": seed, "random_samples": random_samples},
        "random": {"genome": best_g.tolist()},
    }), encoding="utf-8")
    champ = evolve.run(name, workdir=workdir, gens=gens, pop=pop, seed=seed, verbose=False)

    null = max(trivial, hand, random_ho)
    return {
        "problem": name, "unit": prob.unit,
        "trivial": round(trivial, 4), "hand": round(hand, 4), "random": round(random_ho, 4),
        "champion_train": champ["train"], "champion_holdout": champ["holdout"],
        "gap": round(champ["train"] - champ["holdout"], 4),
        "beats_null": bool(champ["holdout"] > null + 1e-9),
        "best_baseline": round(null, 4),
        "pipeline": champ["pipeline"],
    }


def run(workdir="out/accuracy_bench", gens=8, pop=10, seed=0, n_train=6, n_holdout=4,
        size=32, random_samples=80, problem_names=None):
    os.makedirs(workdir, exist_ok=True)
    names = problem_names or list(problems.PROBLEMS)
    rows = []
    for name in names:
        try:
            rows.append(bench_problem(name, workdir, gens, pop, seed, n_train, n_holdout,
                                      size, random_samples))
        except Exception as e:  # keep going; record the failure honestly
            rows.append({"problem": name, "error": f"{type(e).__name__}: {e}"})
    return {"config": {"gens": gens, "pop": pop, "seed": seed, "n_train": n_train,
                       "n_holdout": n_holdout, "size": size, "random_samples": random_samples},
            "rows": rows}


def to_markdown(result) -> str:
    cfg = result["config"]
    out = ["# Accuracy benchmark — champion vs null (holdout)", "",
           f"> Short-budget sweep: gens={cfg['gens']}, pop={cfg['pop']}, "
           f"n_train={cfg['n_train']}, n_holdout={cfg['n_holdout']}, size={cfg['size']}, "
           f"seed={cfg['seed']}. Selection is on TRAIN only; all scores below are on the "
           f"HELD-OUT set. Higher is better. Not the headline long-budget numbers — this is "
           f"the standing 'does evolution beat the null' table.", "",
           "| problem | unit | trivial | hand | random | **champion** | best null | beats null? | gap |",
           "|---|---|--:|--:|--:|--:|--:|:--:|--:|"]
    n_beat = 0
    for r in result["rows"]:
        if "error" in r:
            out.append(f"| {r['problem']} | — | — | — | — | ERROR | — | — | {r['error']} |")
            continue
        mark = "yes" if r["beats_null"] else "no"
        n_beat += int(r["beats_null"])
        out.append(f"| {r['problem']} | {r['unit']} | {r['trivial']} | {r['hand']} | "
                   f"{r['random']} | **{r['champion_holdout']}** | {r['best_baseline']} | "
                   f"{mark} | {r['gap']} |")
    total = sum(1 for r in result["rows"] if "error" not in r)
    out += ["", f"**Champion beats the best null on holdout in {n_beat}/{total} problems.** "
            "A negative gap means holdout ≥ train (no overfit); a large positive gap flags overfitting."]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", default="out/accuracy_bench")
    ap.add_argument("--gens", type=int, default=8)
    ap.add_argument("--pop", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-train", type=int, default=6)
    ap.add_argument("--n-holdout", type=int, default=4)
    ap.add_argument("--size", type=int, default=32)
    ap.add_argument("--random-samples", type=int, default=80)
    ap.add_argument("--problems", default=None, help="comma-separated subset")
    ap.add_argument("--md", default="docs/ACCURACY_BENCH.md")
    a = ap.parse_args()
    names = [s.strip() for s in a.problems.split(",")] if a.problems else None
    result = run(a.workdir, a.gens, a.pop, a.seed, a.n_train, a.n_holdout, a.size,
                 a.random_samples, names)
    Path(a.workdir, "accuracy_bench.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    os.makedirs(os.path.dirname(a.md) or ".", exist_ok=True)
    Path(a.md).write_text(to_markdown(result), encoding="utf-8")
    ok = sum(1 for r in result["rows"] if r.get("beats_null"))
    tot = sum(1 for r in result["rows"] if "error" not in r)
    print(f"[accuracy_bench] champion beats null on holdout: {ok}/{tot} -> {a.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
