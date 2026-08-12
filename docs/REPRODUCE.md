# Reproducing the numbers

Everything is seed-driven and deterministic (pinned by
`tests/test_evolution_honesty.py`: same seed → same result, and the held-out split
is recomputable from the champion). Selection is on the **training** split only; the
held-out split is tracked but never selected on.

## Standing "does evolution beat the null" table

```bash
py -3.11 accuracy_bench.py                       # short-budget sweep -> docs/ACCURACY_BENCH.md
py -3.11 accuracy_bench.py --gens 40 --pop 24 --size 64 --n-train 14 --n-holdout 8
```

For each problem this reports, on the same held-out set: `trivial` (do nothing),
`hand` (the hand-built pipeline), `random` (best-of-N random, train-selected), and
the evolved `champion`, plus the generalization gap. The short-budget default is
honest about being short (the hand baselines are strong; few problems are beaten in
8 generations).

## One problem end-to-end

```bash
py -3.11 baseline.py --problem denoise --workdir out/mine --seed 0     # writes baseline_denoise.json
py -3.11 evolve.py   --problem denoise --workdir out/mine --gens 40 --pop 24 --seed 0
py -3.11 robust.py   --problem denoise --workdir out/mine --seeds 5    # best-of-N seeds, train-selected
```

- `baseline.py` builds train (`seed`) and holdout (`seed + 10000`) with
  `n_train`/`n_holdout`/`size` and writes the honest floor.
- `evolve.py` reads that config, evolves on train, writes `champion_denoise.json`
  and `pareto_denoise.json` (per-generation train + holdout history).
- `robust.py` runs N seeds and persists the **train-selected** champion (never the
  best-on-holdout — that would leak the holdout).

## Codegen + differential test (beta)

```bash
py -3.11 codegen.py  --problem denoise --workdir out/mine    # gen_denoise.py (+ .c if C-supported)
py -3.11 difftest.py --problem denoise --workdir out/mine    # generated pipeline == runtime on holdout
```

`difftest` compares the generated pipeline against the runtime (`ops.run_genome`)
on holdout inputs; a feature/contour final is reported as non-comparable rather than
silently passed.

## Determinism notes

`Date.now`/RNG are seeded throughout; the only non-determinism historically came
from operator bugs (unseeded RNG, uninitialized buffers) which are fixed and pinned
by `tests/test_known_bugs.py`.
