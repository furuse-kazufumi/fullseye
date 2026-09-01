"""S0 — the honest floor (per problem, multi-sort aware).

  trivial : empty pipeline (do nothing).
  hand    : the problem's hand-built typed pipeline (may span image->region->feature).
  random  : best of N random genomes selected on train, reported on holdout.

Writes baseline_<problem>.json. Deterministic.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import ops
import problems


#: evolve.run's fallback split config, duplicated here ON PURPOSE. evolve.run reads
#: ``baseline_<problem>.json`` for its ``config`` and falls back to exactly these
#: numbers when the file is absent. robust.py must score the hand/trivial floors on
#: the SAME split the champion was scored on, so it needs the same resolution rule
#: without importing evolve (which would drag the whole ES in). Keep in sync with
#: evolve.run: a drift here would silently compare two different extractions —
#: the exact trap docs/EVOLUTION_ENVIRONMENT.md records ("+38%" that was really +2%).
DEFAULT_CFG = {"n_train": 14, "n_holdout": 8, "size": 64, "seed": 0}

#: split name -> seed offset. train = cfg seed; observed holdout = +10000 (scored
#: every generation, never selected on); locked holdout = +20000 (scored once).
SPLIT_OFFSET = {"train": 0, "holdout": 10_000, "locked": 20_000}


def _stages_str(stages) -> str:
    parts = [f"{s.op}(a={s.a:.2f},b={s.b:.2f})" for s in stages if s.op != "identity"]
    return " -> ".join(parts) if parts else "identity"


def resolve_cfg(workdir, problem) -> dict:
    """The split config ``evolve.run`` will use for *problem* in *workdir*.

    Mirrors ``evolve.run``: the ``config`` block of ``baseline_<problem>.json`` when
    that file exists, else :data:`DEFAULT_CFG`. Callers that measure a baseline for a
    champion MUST resolve the config this way — scoring the floor on a different
    extraction than the champion is how a 2% gain got written up as 38%.
    """
    p = Path(workdir) / f"baseline_{problem}.json"
    if p.exists():
        try:
            cfg = json.loads(p.read_text(encoding="utf-8")).get("config")
        except (OSError, ValueError):
            cfg = None
        if isinstance(cfg, dict) and all(k in cfg for k in DEFAULT_CFG):
            return dict(cfg)
    return dict(DEFAULT_CFG)


def split_data(prob, cfg, split):
    """The *split* extraction for *prob* under *cfg* (``train``/``holdout``/``locked``)."""
    n = cfg["n_train"] if split == "train" else cfg.get("n_locked", cfg["n_holdout"]) \
        if split == "locked" else cfg["n_holdout"]
    return prob.make(n, cfg["size"], cfg["seed"] + SPLIT_OFFSET[split])


def measure_baselines(prob, cfg, splits=("train", "holdout", "locked")) -> dict:
    """Score the trivial (identity) and hand pipelines on each split.

    Returns ``{"trivial": {...}, "hand": {...}}`` with one rounded score per split
    plus the pipeline string. Cheap (two pipelines over ``n_holdout`` items) and
    deterministic — there is no reason for a run to report ``null`` floors.
    """
    hand = prob.hand_stages()
    triv = problems.trivial_stages()
    out = {"trivial": {"pipeline": "identity"}, "hand": {"pipeline": _stages_str(hand)}}
    for split in splits:
        data = split_data(prob, cfg, split)
        out["trivial"][split] = round(prob.score_stages(triv, data), 4)
        out["hand"][split] = round(prob.score_stages(hand, data), 4)
    return out


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
    cfg = {"n_train": a.n_train, "n_holdout": a.n_holdout, "size": a.size, "seed": a.seed}
    tr = split_data(prob, cfg, "train")
    ho = split_data(prob, cfg, "holdout")
    # LOCKED split (robust.py's *_locked tally) is scored inside measure_baselines.
    floors = measure_baselines(prob, cfg)

    hand = prob.hand_stages()
    rng = np.random.default_rng(a.seed + 777)
    best_g, best_tr = None, -1e18
    for _ in range(a.random_samples):
        g = rng.random(ops.GENOME_LEN)
        s = prob.score(g, tr)
        if s > best_tr:
            best_tr, best_g = s, g

    result = {
        "problem": a.problem, "unit": prob.unit,
        "config": dict(cfg, random_samples=a.random_samples),
        "trivial": {"train": floors["trivial"]["train"],
                    "holdout": floors["trivial"]["holdout"],
                    "locked_holdout": floors["trivial"]["locked"],
                    "pipeline": "identity"},
        "hand": {"train": floors["hand"]["train"],
                 "holdout": floors["hand"]["holdout"],
                 "locked_holdout": floors["hand"]["locked"],
                 "pipeline": _stages_str(hand)},
        "random": {"train": round(best_tr, 4), "holdout": round(prob.score(best_g, ho), 4),
                   "pipeline": ops.pipeline_str(best_g, prob.in_sort), "genome": best_g.tolist()},
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
