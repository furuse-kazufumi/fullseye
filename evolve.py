"""S1 — the evolution core (memetic, per problem).

Evolves typed-pipeline genomes with a (mu+lambda) ES plus a light memetic local
refinement on the elite. Fitness is the TRAIN score only; the HOLDOUT score is
tracked every generation but NEVER used for selection — the honest guard against
the 'pseudo-equation trap'. Deterministic given --seed.

Writes pareto_<problem>.json and champion_<problem>.json into the shared workdir.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import ops
import problems


def _refine(genome, fit_fn, rng, steps=15, sigma=0.05):
    g = genome.copy()
    best = fit_fn(g)
    for _ in range(steps):
        j = int(rng.integers(0, ops.GENOME_LEN))
        cand = g.copy()
        cand[j] = float(np.clip(cand[j] + rng.normal(0, sigma), 0.0, 1.0))
        s = fit_fn(cand)
        if s > best:
            g, best = cand, s
    return g, best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problem", default="denoise", choices=list(problems.PROBLEMS))
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--gens", type=int, default=50)
    ap.add_argument("--pop", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    prob = problems.PROBLEMS[a.problem]
    wd = Path(a.workdir); wd.mkdir(parents=True, exist_ok=True)
    bpath = wd / f"baseline_{a.problem}.json"
    base = json.loads(bpath.read_text(encoding="utf-8")) if bpath.exists() else {}
    cfg = base.get("config", {"n_train": 14, "n_holdout": 8, "size": 64, "seed": 0})

    tr = prob.make(cfg["n_train"], cfg["size"], cfg["seed"])
    ho = prob.make(cfg["n_holdout"], cfg["size"], cfg["seed"] + 10_000)
    train_fit = lambda g: prob.score(g, tr)  # noqa: E731
    holdout_fit = lambda g: prob.score(g, ho)  # noqa: E731

    rng = np.random.default_rng(a.seed)
    mu = max(2, a.pop // 4)
    pop = rng.random((a.pop, ops.GENOME_LEN))
    # warm-start slot 0 with the baseline's random champion if available (hand is a
    # typed stage-list, not a genome, so it is not injected into the population)
    rg = base.get("random", {}).get("genome")
    if rg and len(rg) == ops.GENOME_LEN:
        pop[0] = np.asarray(rg, np.float64)

    champ, champ_tr = pop[0].copy(), train_fit(pop[0])
    history = []
    for gen in range(a.gens):
        fits = np.array([train_fit(g) for g in pop])
        elite = pop[np.argsort(-fits)[:mu]].copy()
        best_g, best_s = _refine(elite[0].copy(), train_fit, rng)
        if best_s > champ_tr:
            champ, champ_tr = best_g.copy(), best_s
        elite[0] = best_g
        children = []
        while len(children) < a.pop - mu:
            parent = elite[int(rng.integers(0, mu))]
            children.append(np.clip(parent + rng.normal(0, 0.12, ops.GENOME_LEN), 0.0, 1.0))
        pop = np.vstack([elite, np.array(children)])
        history.append({"gen": gen, "best_train": round(champ_tr, 4),
                        "best_holdout": round(holdout_fit(champ), 4)})
        if gen % 10 == 0 or gen == a.gens - 1:
            print(f"  [{a.problem}] gen {gen:3d} train {champ_tr:.3f} holdout {holdout_fit(champ):.3f}", flush=True)

    champion = {
        "problem": a.problem, "unit": prob.unit,
        "genome": champ.tolist(), "pipeline": ops.pipeline_str(champ),
        "train": round(champ_tr, 4), "holdout": round(holdout_fit(champ), 4),
        "config": cfg, "seed": a.seed, "gens": a.gens, "pop": a.pop,
    }
    (wd / f"champion_{a.problem}.json").write_text(json.dumps(champion, indent=2), encoding="utf-8")
    pareto = {"problem": a.problem, "config": cfg, "seed": a.seed, "history": history, "champion": champion}
    (wd / f"pareto_{a.problem}.json").write_text(json.dumps(pareto, indent=2), encoding="utf-8")
    if a.out:
        p = a.out if a.out.endswith(".json") else a.out + ".json"
        Path(p).write_text(json.dumps(pareto, indent=2), encoding="utf-8")
    print(f"[evolve:{a.problem}] champion: {champion['pipeline']} | train {champ_tr:.3f} "
          f"holdout {champion['holdout']:.3f} ({prob.unit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
