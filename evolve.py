"""S1 — the evolution core (memetic).

Evolves a population of typed-pipeline genomes with a (mu+lambda) ES plus a light
memetic local refinement on the elite. Fitness is TRAIN PSNR only; holdout PSNR is
tracked every generation but NEVER used for selection — that separation is the
honest guard against the 'pseudo-equation trap' (fitting the eval set).

Deterministic given --seed (mirrors r2's bit-identical discipline). Regenerates the
exact train/holdout split from baseline.json's config so numbers are comparable.

Writes pareto.json (per-gen history) and champion.json (the designed algorithm).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import ops


def _refine(genome, fit_fn, rng, steps=12, sigma=0.05):
    """Memetic local search: keep per-coordinate perturbations that improve train fit."""
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
    ap.add_argument("--workdir", default="out/worklog/imgevolve")
    ap.add_argument("--baseline", default=None, help="baseline.json (for config + warm-start)")
    ap.add_argument("--gens", type=int, default=60)
    ap.add_argument("--pop", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None, help="also copy pareto.json here (<OUT>.json)")
    a = ap.parse_args()

    wd = Path(a.workdir); wd.mkdir(parents=True, exist_ok=True)
    bpath = Path(a.baseline) if a.baseline else wd / "baseline.json"
    cfg = json.loads(bpath.read_text(encoding="utf-8"))["config"] if bpath.exists() else {
        "n_train": 12, "n_holdout": 6, "size": 64, "noise": 0.12, "seed": 0}

    c_tr, n_tr = ops.make_dataset(cfg["n_train"], cfg["size"], cfg["noise"], seed=cfg["seed"])
    c_ho, n_ho = ops.make_dataset(cfg["n_holdout"], cfg["size"], cfg["noise"], seed=cfg["seed"] + 10_000)

    def train_fit(g):
        return ops.mean_psnr_over(g, c_tr, n_tr)

    def holdout_fit(g):
        return ops.mean_psnr_over(g, c_ho, n_ho)

    rng = np.random.default_rng(a.seed)
    mu = max(2, a.pop // 4)
    # warm-start: include the baseline's random champion if present
    pop = rng.random((a.pop, ops.GENOME_LEN))
    if bpath.exists():
        rg = json.loads(bpath.read_text(encoding="utf-8")).get("random", {}).get("genome")
        if rg and len(rg) == ops.GENOME_LEN:
            pop[0] = np.asarray(rg, np.float64)

    history = []
    champ, champ_tr = pop[0].copy(), train_fit(pop[0])
    for gen in range(a.gens):
        fits = np.array([train_fit(g) for g in pop])
        order = np.argsort(-fits)
        elite = pop[order[:mu]]
        # memetic refine on the current best elite
        best_g, best_s = _refine(elite[0].copy(), train_fit, rng)
        if best_s > champ_tr:
            champ, champ_tr = best_g.copy(), best_s
        elite[0] = best_g
        # reproduce: gaussian mutation of elites -> next generation
        children = []
        while len(children) < a.pop - mu:
            parent = elite[int(rng.integers(0, mu))]
            child = np.clip(parent + rng.normal(0, 0.12, ops.GENOME_LEN), 0.0, 1.0)
            children.append(child)
        pop = np.vstack([elite, np.array(children)])
        history.append({"gen": gen, "best_train": round(champ_tr, 4),
                        "best_holdout": round(holdout_fit(champ), 4)})
        if gen % 10 == 0 or gen == a.gens - 1:
            print(f"  gen {gen:3d} train {champ_tr:.3f} holdout {holdout_fit(champ):.3f}", flush=True)

    champion = {
        "genome": champ.tolist(),
        "pipeline": ops.pipeline_str(champ),
        "train_psnr": round(champ_tr, 4),
        "holdout_psnr": round(holdout_fit(champ), 4),
        "config": cfg, "seed": a.seed, "gens": a.gens, "pop": a.pop,
    }
    pareto = {"config": cfg, "seed": a.seed, "history": history, "champion": champion}
    (wd / "champion.json").write_text(json.dumps(champion, indent=2), encoding="utf-8")
    (wd / "pareto.json").write_text(json.dumps(pareto, indent=2), encoding="utf-8")
    if a.out:
        Path(a.out if a.out.endswith(".json") else a.out + ".json").write_text(
            json.dumps(pareto, indent=2), encoding="utf-8")
    print(f"[evolve] champion: {champion['pipeline']} | train {champ_tr:.2f} "
          f"holdout {champion['holdout_psnr']:.2f} -> {wd/'champion.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
