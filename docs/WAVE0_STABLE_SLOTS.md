# Wave-0: stable op slots + name-pinned champions

Three additive, backward-compatible changes to the evolution core. Each preserves
the **current** evolutionary behavior exactly (proven by `tests/test_wave0.py`,
which pins the denoise/edge champions and the decode of several fixed genomes
across every start sort to values captured from the pre-change code).

## 1. Stable op slots + name-pinned champion records (`ops.py`)

### The cross-install reproducibility problem

`decode()` picks an op with

```python
cands = _candidates(sort)                       # REGISTRY filtered by in_sort, in registration order
op = cands[min(len(cands) - 1, int(t * len(cands)))]
```

The index a genome resolves to depends on `len(cands)`, which **grows with the
optional backends installed** (scikit-image, OpenCV, kornia, …). The same genome
therefore decodes to different ops on a minimal install versus an all-backends
install. Re-sorting `_candidates` into some globally stable order would fix
cross-install reproducibility **but would change the index every existing genome
maps to today** — i.e. it would silently rewrite every current champion.

### Decision (honest): do NOT change `decode`

Preserving the north-star (current champions unchanged) is worth more than an
elegant decode. `decode()` is left **byte-identical**; `tests/test_wave0.py`
verifies this for the denoise and edge champions and for five fixed genomes across
all seven start sorts.

### What shipped instead — reproduce by NAME, not index

- `ops.SLOTS: dict[str,int]` — each op's registration-order index, frozen when
  `REGISTRY` is fully built (core ops first, then backends in import order).
  Documents that `_candidates(sort)` order is deterministic within an install.
- `ops.pipeline_stages(genome, start)` — records a champion as a list of
  `{op, a, b, sort}` dicts (op **names**, not indices).
- `ops.decode_by_names(stage_specs)` — rebuilds the exact pipeline from those
  names via `_BY_NAME`, independent of the index layout. Fail-closed: raises
  `KeyError` if a named op is absent in the target install.
- `ops.stages_str(stages)` — renders reconstructed stages to the same string form
  as `pipeline_str`.
- `evolve.run` now writes `champion["pipeline_stages"]` alongside the existing
  `champion["pipeline"]` string.

A champion saved by name reloads to the **same** pipeline on any install that has
the named ops — the cross-install-reproducible counterpart to index-based decode.

### Residual caveat (documented honestly)

- Reproducing a champion across installs by name requires the **named ops to be
  present** in the target install. If a backend that provided an op is missing,
  `decode_by_names` fails closed rather than silently substituting.
- A few op **names occur twice** (a backend overrides a core op, e.g. `laplace`,
  `dyn_threshold`, `local_max`, `edges_sub_pix`). Consistent with `RT` and
  `_BY_NAME`, a duplicated name resolves to its **last (canonical)** occurrence —
  which is exactly the function `_apply` executes for that name. Name-pinned
  reload is therefore consistent with execution on both sides.
- `SLOTS` is stable **within** an install, not a global cross-install identity.
  It is documentation/metadata, not a new decode path.

## 2. Three-way honest split (`evolve.py`)

`run` already used train (`n_train`, seed) for selection and a per-generation
holdout (`n_holdout`, seed+10000) tracked but never selected on. Wave-0 adds a
**third, locked holdout** (`n_locked` — defaults to `n_holdout`, seed+20000):

- evaluated **exactly once**, on the final champion, after the generation loop;
- never used for selection and never read per-generation;
- recorded as `champion["locked_holdout"]`.

Selection stays **train-only**, so the champion and its train score are unchanged
(pinned in the tests). Backward-compatible: `champion["holdout"]` keeps its
original meaning (the per-gen search-validation holdout); `locked_holdout` is
purely additive. No config change is required — `n_locked` is read with a default.

## 3. `Problem.from_pairs` (`problems.py`)

`Problem.from_pairs(inputs, targets, name=..., metric=..., unit=..., in_sort=...,
hand_stages=...)` builds a Problem from explicit `(input, target)` numpy arrays
instead of the synthetic `_synth` generator, so **real captured frames can drive
evolution**. Purely additive — `PROBLEMS` and `_synth` are untouched.

- `make(n, size, seed)` returns a deterministic `n`-item subset via a seed-based
  rotation over the pool, so `evolve.run`'s train (seed) and holdout (seed+10000)
  draw different orderings.
- Default metric: PSNR for 2-D image targets, else `1/(1+|count_err|)`.
- `evolve.run` now accepts either a registered problem **name** (str) or a
  `Problem` instance, so a `from_pairs` problem drives evolution without being
  registered globally.

**Caveat:** a genuinely disjoint locked/holdout split needs enough distinct pairs;
a tiny pool cannot yield a clean holdout (train/holdout/locked will overlap).
