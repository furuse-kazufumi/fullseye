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


def run(problem, workdir="out/worklog/imgevolve", gens=50, pop=24, seed=0, out=None, verbose=True):
    """Evolve one problem for one seed; write champion/pareto; return the champion dict.

    Selection is on TRAIN only; HOLDOUT is tracked but never selected on (honest
    guard against the pseudo-equation trap).

    ``problem`` may be a registered problem NAME (str) or a Problem instance
    (e.g. one built by ``Problem.from_pairs`` from real frames) — the latter lets
    real-data problems drive evolution without registering them globally.
    """
    if isinstance(problem, problems.Problem):
        prob = problem
        problem = prob.name
    else:
        prob = problems.PROBLEMS[problem]
    wd = Path(workdir); wd.mkdir(parents=True, exist_ok=True)
    bpath = wd / f"baseline_{problem}.json"
    base = json.loads(bpath.read_text(encoding="utf-8")) if bpath.exists() else {}
    cfg = base.get("config", {"n_train": 14, "n_holdout": 8, "size": 64, "seed": 0})

    tr = prob.make(cfg["n_train"], cfg["size"], cfg["seed"])
    ho = prob.make(cfg["n_holdout"], cfg["size"], cfg["seed"] + 10_000)
    # THIRD split — a LOCKED holdout, distinct from both train (seed) and the
    # per-gen search-validation holdout (seed+10000). It is evaluated EXACTLY ONCE
    # on the final champion (below), never per-gen and never for selection, so it
    # is the strongest honesty guard against the pseudo-equation trap. Selection is
    # unchanged (train-only); adding this split cannot move the champion. Backward
    # compatible: the existing "holdout" key keeps its meaning; "locked_holdout" is
    # additive. Size defaults to n_holdout; override via config "n_locked".
    n_locked = cfg.get("n_locked", cfg["n_holdout"])
    locked = prob.make(n_locked, cfg["size"], cfg["seed"] + 20_000)
    train_fit = lambda g: prob.score(g, tr)  # noqa: E731
    holdout_fit = lambda g: prob.score(g, ho)  # noqa: E731

    rng = np.random.default_rng(seed)
    mu = max(1, min(pop - 1, max(2, pop // 4))) if pop > 1 else 1  # keep >=1 child slot for tiny pops
    popm = rng.random((pop, ops.GENOME_LEN))
    rg = base.get("random", {}).get("genome")
    if rg and len(rg) == ops.GENOME_LEN:
        popm[0] = np.asarray(rg, np.float64)

    champ, champ_tr = popm[0].copy(), train_fit(popm[0])
    history = []
    for gen in range(gens):
        fits = np.array([train_fit(g) for g in popm])
        elite = popm[np.argsort(-fits)[:mu]].copy()
        best_g, best_s = _refine(elite[0].copy(), train_fit, rng)
        if best_s > champ_tr:
            champ, champ_tr = best_g.copy(), best_s
        elite[0] = best_g
        children = []
        while len(children) < pop - mu:
            parent = elite[int(rng.integers(0, mu))]
            children.append(np.clip(parent + rng.normal(0, 0.12, ops.GENOME_LEN), 0.0, 1.0))
        popm = np.vstack([elite, np.array(children)]) if children else elite.copy()
        history.append({"gen": gen, "best_train": round(champ_tr, 4),
                        "best_holdout": round(holdout_fit(champ), 4)})
        if verbose and (gen % 10 == 0 or gen == gens - 1):
            print(f"  [{problem}] gen {gen:3d} train {champ_tr:.3f} holdout {holdout_fit(champ):.3f}", flush=True)

    # Touch the LOCKED holdout exactly once, on the final champion only.
    locked_holdout = round(prob.score(champ, locked), 4)
    champion = {
        "problem": problem, "unit": prob.unit,
        "genome": champ.tolist(), "pipeline": ops.pipeline_str(champ, prob.in_sort),
        # Name-pinned, index-independent champion record (cross-install reload via
        # ops.decode_by_names) — additive; does not affect selection or scoring.
        "pipeline_stages": ops.pipeline_stages(champ, prob.in_sort),
        "train": round(champ_tr, 4), "holdout": round(holdout_fit(champ), 4),
        "locked_holdout": locked_holdout,
        "config": cfg, "seed": seed, "gens": gens, "pop": pop,
    }
    (wd / f"champion_{problem}.json").write_text(json.dumps(champion, indent=2), encoding="utf-8")
    pareto = {"problem": problem, "config": cfg, "seed": seed, "history": history, "champion": champion}
    (wd / f"pareto_{problem}.json").write_text(json.dumps(pareto, indent=2), encoding="utf-8")
    if out:
        p = out if out.endswith(".json") else out + ".json"
        Path(p).write_text(json.dumps(pareto, indent=2), encoding="utf-8")
    if verbose:
        print(f"[evolve:{problem}] champion: {champion['pipeline']} | train {champ_tr:.3f} "
              f"holdout {champion['holdout']:.3f} ({prob.unit})")
    return champion


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--problem", default="denoise", choices=list(problems.PROBLEMS))
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--gens", type=int, default=50)
    ap.add_argument("--pop", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    run(a.problem, a.workdir, a.gens, a.pop, a.seed, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
