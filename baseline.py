"""S0 — the honest floor (per problem).

Measures three references on a train/holdout split so S1's evolution has an honest
yardstick (nothing here is 'the answer'; it is what evolution must beat):

  - trivial : do-nothing pipeline (identity).
  - hand    : the problem's hand-built expert pipeline.
  - random  : best of N random pipelines *selected on train*, reported on holdout
              (same protocol as evolution, so a win over `random` isolates search).

Writes baseline_<problem>.json into the shared workdir. Deterministic (seeded).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import ops
import problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problem", default="denoise", choices=list(problems.PROBLEMS))
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--out", default=None)
    ap.add_argument("--n-train", type=int, default=14)
    ap.add_argument("--n-holdout", type=int, default=8)
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--random-samples", type=int, default=300)
    a = ap.parse_args()

    prob = problems.PROBLEMS[a.problem]
    wd = Path(a.workdir); wd.mkdir(parents=True, exist_ok=True)
    tr = prob.make(a.n_train, a.size, a.seed)
    ho = prob.make(a.n_holdout, a.size, a.seed + 10_000)

    def ho_score(g):
        return prob.score(g, ho)

    trivial = problems.trivial_genome()
    hand = prob.hand()
    rng = np.random.default_rng(a.seed + 777)
    best_g, best_tr = None, -1e18
    for _ in range(a.random_samples):
        g = rng.random(ops.GENOME_LEN)
        s = prob.score(g, tr)
        if s > best_tr:
            best_tr, best_g = s, g

    result = {
        "problem": a.problem, "unit": prob.unit,
        "config": {"n_train": a.n_train, "n_holdout": a.n_holdout, "size": a.size,
                   "seed": a.seed, "random_samples": a.random_samples},
        "trivial": {"holdout": round(ho_score(trivial), 4), "pipeline": ops.pipeline_str(trivial)},
        "hand": {"train": round(prob.score(hand, tr), 4), "holdout": round(ho_score(hand), 4),
                 "pipeline": ops.pipeline_str(hand)},
        "random": {"train": round(best_tr, 4), "holdout": round(ho_score(best_g), 4),
                   "pipeline": ops.pipeline_str(best_g), "genome": best_g.tolist()},
    }
    (wd / f"baseline_{a.problem}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if a.out:
        p = a.out if a.out.endswith(".json") else a.out + ".json"
        Path(p).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[baseline:{a.problem}] trivial {result['trivial']['holdout']:.3f} | "
          f"hand {result['hand']['holdout']:.3f} | random {result['random']['holdout']:.3f} ({prob.unit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
