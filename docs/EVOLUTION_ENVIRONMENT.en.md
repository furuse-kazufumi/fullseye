<!-- i18n-source-sha: 335f07da75d7 -->
# Evolutionary Algorithm Development Environment — Expand, Contract, Promote

[日本語](./EVOLUTION_ENVIRONMENT.md) · **English**

Instead of composing ops by hand, **compose them mechanically (expand), narrow down
to the useful ones (contract), and add the ones that pass into the vocabulary
(promote)**. A promoted op can be selected as one stage by the next search, so the
vocabulary builds up on top of its own discoveries.

```
  expand            contract               promote
  chain_mine   →   evolve / promote  →   backends_macro
  (combine)        (narrow by problem)   (add to vocabulary)
      ↑                                        │
      └────────── next search uses grown vocab ─┘
```

The conductor is `tools/evolve_loop.py`.

## The heart of this environment is "discipline," not automation

If the only goal is to grow the vocabulary, you can synthesize compositions without
limit. But that merely dilutes the search space, and **a single bad op, once it gets
in, poisons every future search that draws it**. That is why the path that grows the
vocabulary (expand) and the discipline that refuses entry (the gate) live in the same
loop.

Do not blur the responsibilities of the stages:

| Stage | Responsibility | What it does NOT do |
|---|---|---|
| `mine` | Emit candidates. Keep descriptors **multi-dimensional** | Judge good vs. bad |
| `screen` | Cheap judgment of whether it belongs in the ring (empty, too long, non-deterministic, a type the problem does not accept) | Judge usefulness |
| `gate` | counterfactual utility + de-duplication + capacity cap | Generate candidates |
| `report` | Emit what passed **and what was rejected** with reasons | Convenient summaries |

If usefulness judgment leaks into `screen`, no one can notice when a cheap check
throws away a genuine discovery. So even near-identity chains are not dropped by
`screen`; they are passed on to `gate`.

## Expand — sweep the combination space

`tools/chain_mine.py`. It randomly chains ops from a typed pool and records the
**successful chains** together with behavioral descriptors (`tools/chain_fuzz.py` is a
bug finder using the same mechanism, picking up the failures instead; its operation is
in `docs/CHAIN_FUZZ.md`).

The key is not to collapse the descriptors into a single score. "Changes a lot" and
"useful" are different things, and collapsing them lets ops that merely add noise win.

## Contract — narrow by problem

`evolve.py` / `robust.py` optimize a pipeline against the problem's fitness. Selection
uses train only; holdout is tracked but never used for selection; the locked holdout is
used exactly once at the very end — this three-way split is the guarantee of honesty
against the "pseudo-equation trap" (`docs/WAVE0_STABLE_SLOTS.md`).

**Always compare against the three baselines identity / random / hand-designed.** In a
past measurement, evolution reached 0.041 while random search reached 0.042, a narrow
margin — when the search space is small, evolution's edge disappears.

## Promote — the decision to add to the vocabulary

`tools/promote_gate.py`. A candidate must pass all three judgments.

**1. counterfactual utility**
The question is not "is this op strong on that problem" but "**how much does the whole
workload improve when this op is in the vocabulary**". The implementation compares the
score when the candidate is used as one stage against the **best single stage from the
existing vocabulary** across all problems. The point is to subtract off what the
existing vocabulary can already reach, and to pass ops that "**reach where the existing
vocabulary cannot**" rather than ops that are merely "strong."

*Limitation (honestly)*: Ideally you would measure "the improvement when you put the
candidate into the vocabulary and re-run evolution," but that takes tens of minutes per
candidate. The single-stage substitution is an approximation of that, stated explicitly
in `utility_method` in the output.

**2. Behavioral de-duplication**
If the output on a fixed probe matches an existing op, it is rejected. This is the
numerical version of a device that collapses expression equivalence (e-graph /
equality saturation). It is judged a duplicate **only when it matches on every probe**
(so that a single coincidental match does not throw away a genuine discovery). It means
indistinguishable on the probes, not a proof of mathematical equivalence.

**3. capacity bound**
If promotion continues without limit, the reachable model family stops being
capacity-bounded and the generalization guarantee breaks. When the cap (default 32) is
reached, an eviction is required, and **what was dropped must always be recorded**.

The judgments are tilted toward the strict side — if the improvement is within
measurement error (+0.5% relative to the existing best), it is rejected.

## Two op universes and the bridge between them (2026-09-01 measurement)

At the outset, fullseye had two universes of ops, and **only 3 names overlapped**.

| | op count | who uses it | convention |
|---|---|---|---|
| `ops.py` REGISTRY | 742 | evolution | `fn(v, a, b)`, sort = image/region/… |
| typed catalog | 382 | fuzzer, facade | declared input/output types, multiple args |

That means evolution had never once combined a point-cloud op with a 1-D op or a math
op, and the self-extending registry had only grown on the narrow side. `backends_typed.py`
is that bridge.

**The safety argument**: `ops._candidates(sort)` only filters by `in_sort`, so **adding
only newly created sorts leaves the candidate-list length of existing sorts unchanged**.
If the length changes, the genome→op mapping shifts and silently rewrites existing
champions (`docs/WAVE0_STABLE_SLOTS.md`). The default is only the 58 ops whose input is a
new sort (points / signal / matrix / cimage). Ops that take an existing sort as input
expand up to 125 ops under the opt-in `IMGEVOLVE_WIDE_VOCAB=1`.

**Knobs**: At first, following the DNA op, we froze a and b, but measurement showed a
tuning margin of 0/58 — an op whose default is identity was a literally meaningless
slot. Yet deciding an absolute range would be fabricating parameters of unknown origin,
so we allowed only a relative scale of **1/4 to 2× the default value the author wrote
themselves** (which made 21/58 tunable).

## Usage

```bash
# Run only the judgment (using existing mining results)
py -3.11 tools/evolve_loop.py --skip-mine --mine-out out/chain_mine_smoke.jsonl

# Run through from expand. With the wide vocabulary
IMGEVOLVE_WIDE_VOCAB=1 py -3.11 tools/evolve_loop.py --chains 1500 --length 4 --seed 7

# Promotion judgment for a single op
py -3.11 tools/promote_gate.py --op macro_denoise --max-existing 120

# Champion into the vocabulary (2-stage gate: hand baseline + counterfactual utility)
py -3.11 champion_to_macro.py --champion out/…/champion_denoise.json \
    --name macro_x --utility-gate
```

Writing to the vocabulary happens only when `--write` is given explicitly. The default
is "go as far as emitting the list of passing candidates," and it never implicitly
executes a near-irreversible operation.

## Narrow sorts — the "fraction that stays in the same type" matters more than vocabulary size

The first thing we learned when opening a new sort is that **you cannot search just by
growing the vocabulary**. What decides it is not the number of ops but **the fraction of
ops that stay in that sort**.

| sort | candidates | returns same type | probability all 6 stages stay |
|---|---|---|---|
| points | 25 | 13 (52%) | **2.0%** |
| signal | 23 | 17 (74%) | 16.3% |

With a 6-slot fixed encoding, most individuals escape the sort and score 0, so
evolution gets no gradient. Measurement: even after running 3200 evaluations, the
point-cloud locked was 0.436, **below the do-nothing value of 0.675** — because evolution
cannot reach the baseline, the very comparison "did it beat the baseline" did not hold.

There are two remedies, both of which came out of measurement.

**1. Start the search from a known baseline** — we added `ops.genome_for_names` (the
inverse mapping of `decode`) and place trivial and hand in the initial population via
`evolve.run(seed_baselines=True)`. The probability of hitting all-identity is 4e-9 for
point clouds, so random draws will never get there. **The default is off**, so existing
runs are byte-identical, selection is train-only, and locked stays untouched — the
honesty guard is not loosened (it only seeds).

**2. Eliminate the path discrepancy** — the same "do-nothing pipeline" scored 0.2016 via
the genome path and 0.6616 via the name path. Because `identity`'s `out_sort` is `ANY`,
it slipped past the "do not clip new sorts" exclusion, and only the genome path got
clipped 6 times. Since `ANY` means "keep the sort that came in," we resolved it in
`_effective_out_sort`.

Result (locked holdout, measured):

| problem | before fix | after fix | trivial | hand |
|---|---|---|---|---|
| points_denoise | 0.193 | **0.7182** | 0.6748 | 0.7298 |
| signal_denoise | 0.834 | **0.9736** | 0.9452 | 0.9810 |

On point clouds, evolution reached **statistical outlier removal** on its own — the
textbook approach to point-cloud denoising. It has not yet reached hand (it found the
same op with slightly worse parameters), but it got onto a ring where the comparison is
meaningful.

## End-to-end demonstration (2026-09-01, measured)

We confirmed with a single full run that the environment works as designed. **To put the
conclusion first, the vocabulary did not grow — because nothing was worth promoting.**
That is the correct behavior of this environment.

1. **Expand** — mined 1500 chains in 30 seconds, obtaining 205 representatives from 988
   complete chains (two runs with the same seed matched bit-for-bit by sha256).
2. **Contract** — ran 3 seeds × 60 generations × population 32 on the point-cloud
   problem, converging to the same solution all 3 times. Evolution reached **statistical
   outlier removal** on its own (the textbook approach to point-cloud denoising).
3. **Judgment** — the champion beat hand on train (0.7223 vs. 0.7163). But **it lost on
   the never-before-seen locked** (0.7182 vs. 0.7209).
4. **Promotion gate** — rejected. `beats_hand_on_locked_holdout=False`.

+0.6% on train, −0.4% on locked. This is the "pseudo-equation trap" itself, the very
phenomenon the three-way-split honesty guard exists to catch. Had we looked only at
train, a non-generalizing op would have entered the vocabulary and **poisoned every
future search that draws it**.

The promotion gate's `MIN_RELATIVE_GAIN` (+0.5% relative to the existing best) is set to
reject the same margin, so two independent criteria arrived at the same decision.

## Even if you widen the vocabulary, it spins idle without usable work (2026-09-01 measurement)

We added new op families (light field / photon counting / specular separation / motion
amplification / quaternion), and the catalog went from 400 → 475 ops, but **evolution
could never use them once**. When we ran `evolve_loop`, the leading rejection reason was
this:

```
rejected  5  problem does not accept the input type (histcube)
rejected  4  problem does not accept the input type (lightfield)
rejected  2  problem does not accept the input type (counts)
   ...
did not pass  2  op not in the evolution registry: 'fraunhofer_pattern'
```

This is because **all 12 problems were old types (image / volume / points / signal)**,
and the design of "putting the path that grows the vocabulary (expand) and the discipline
that refuses entry (the gate) in the same loop" **spins idle when there is no work that
can use that vocabulary**.

### One judgment corrected

Initially we kept `lightfield` / `counts` / `histcube` out of the default vocabulary. The
reason was "the entry op of that family (`lf_from_mla`: image→lightfield, etc.) takes an
existing image sort as input, so putting it in the default moves image's candidate list."
The first half is correct, but **the conclusion was excessive** — since `_candidates`
only filters by in_sort, what should be excluded is only the entry op, and adding the
consumer side **only moves the candidate list of the newly created sort**. Measured:

| sort | before | after |
|---|---|---|
| image | 523 | 523 |
| region | 130 | 130 |
| points | 33 | 33 |
| (all existing sorts) | unchanged | unchanged |
| whole registry | 809 | **824** |

The concern that "no one produces it, so it becomes dead vocabulary" is also **limited to
searches that start from image**; if `Problem.in_sort` is that sort, the problem supplies
the input.

However, **we did not add `histcube`**: its only consuming op is `dtof_cube_depth` and the
exit is image, so even if added to the default, "it just steps out in one move" = zero room
to evolve. **Do not add vocabulary that has no usable work.**

### Result of adding 2 new-type problems

A small run of 3 seeds / 12 generations / 12 individuals. **We put both the locked holdout
(seed+20000, a truly untouched split scored exactly once against the champion) and the
observed holdout (seed+10000, scored every generation but never used for selection)** —
these two are not interchangeable, and neither alone decides win or loss.

| problem (input sort) | split | identity | hand (best single existing op) | evolution (train-selected) | vs. hand | evolution seed min / max / std | beats hand |
|---|---|---|---|---|---|---|---|
| `photon_denoise` (`counts`) | **locked** | 0.4174 | 0.5536 | **0.7845** | **+41.7%** | 0.6517 / 0.7845 / **0.0608** | 3/3 |
| | observed | 0.3265 | 0.4433 | 0.7944 | +79.2% | 0.5254 / 0.7944 / 0.1263 | 3/3 |
| `vibration_map` (`video`) | **locked** | 0.0000 | 0.7163 | **0.8941** | **+24.8%** | 0.8940 / 0.8953 / **0.0006** | 3/3 |
| | observed | 0.0000 | 0.6791 | 0.8783 | +29.3% | 0.8769 / 0.8870 / 0.0045 | 3/3 |
| `lf_slope` (`lightfield`) | **locked** | 0.0000 | 0.5219 | 0.5465 | +4.7% | 0.4930 / 0.5465 / **0.0224** | 1/3 |
| | observed | 0.0000 | 0.4882 | 0.5075 | +4.0% | 0.4489 / 0.5075 / 0.0241 | 1/3 |
| `specular_removal` (`rgbimage`) | **locked** | 0.4905 | 0.8343 | 0.6277 | **−24.8%** | 0.3037 / 0.7549 / **0.1900** | 0/3 |
| | observed | 0.4422 | 0.8730 | 0.7761 | −11.1% | 0.3020 / 0.7761 / 0.2177 | 0/3 |

Reproduce (one line, running each seed in a pristine child process):

```powershell
foreach ($p in 'photon_denoise','vibration_map','lf_slope','specular_removal') { py -3.11 robust.py --problem $p --seeds 3 --gens 12 --pop 12 --isolate --workdir out/rb_2026_09_02_A }
```

**Do not place `baseline_<problem>.json` in the workdir** (run in an empty directory). If
that file exists, `evolve.run` will ① read the split config from it and ② replace
individual 0 of the initial population with the random-best genome in the file. In other
words, **the result of evolution changes** depending on whether you ran `baseline.py`
first. The table above uses the "do not place it" numbers.

The artifact is `out/rb_2026_09_02_A/robust_<problem>.json`. **The identity and hand
baselines are in that JSON too** (`baseline_trivial*` / `baseline_hand*`), so the table
above can be read straight off the artifact. Each row carries the `commit` /
`measured_at` / `split_config` at the time of measurement. On 2026-09-02 we measured
**independently 3 times** (`out/rb_2026_09_02_A` / `_B` / re-run overwriting A), and every
field matched except time and commit. Meanwhile commits from other work kept landing and
HEAD moved through 10-plus states, but **none of these 12 numbers moved**. So each row's
`commit` is the mark of "the point at which this number was alive."

**Looking at the identity row, locked and observed differ by 0.09** (`photon_denoise`:
0.4174 vs. 0.3265). Since a value that applies not a single op moves, this is the
variance of the extraction itself (one split has only 8 items), not a difference between
methods. For the same reason, vs. hand also differs widely, locked +41.7% / observed
+79.2%. **A table carrying only one of the two reports the extraction luck of the chosen
side as performance.**

#### Correction (2026-09-02)

**The previous version of this table (identity 0.2664 / hand 0.5371 / evolution 0.7760,
etc.) no longer reproduces with the same code today.** Of the 12 numbers, **10 do not
match** (the 2 that match are the identity of `vibration_map` and `lf_slope`, both
0.0000 — a value where correlation is undefined and rounds to 0, so a match carries no
information). The cause was not on the number side but **on the recording side**:

* The `out/rb_*/robust_*.json` of the time had `baseline_hand` / `baseline_trivial` /
  `baseline_hand_locked` / `baseline_trivial_locked` **all `null`**. `robust.py` was built
  to write the baselines as `null` and proceed if `baseline_<problem>.json` was absent, and
  in that run no one had run `baseline.py` in that workdir. **The baseline columns of the
  table are recorded nowhere in the artifact.**
* The evolution column also differs from the artifact. The artifact of the time recorded
  `photon_denoise` locked as **0.7845** and `specular_removal` as **0.6277**, and these
  match today's re-measurement to 4 digits. **Only the table came from a different
  computation** (the same cause underlies the discrepancy where the article body wrote
  0.628 separately while the table showed 0.6039).

**We identified where the baselines came from.** For all 4 problems the generator does not
use `size` (the shape is fixed at 32×32 / 256 bin), so the only things you can vary are the
count `n` and the split seed. Brute-forcing `n` 1–16 × cfg seed 0–5 × 3 splits, the old
table's baselines reproduce in **exactly one way with today's code**:

| old table value | reproducing condition |
|---|---|
| `photon_denoise` identity 0.2664 / hand 0.5371 | n=8, **cfg seed 2** locked (=`prob.make(8,64,20002)`) |
| `vibration_map` hand 0.6973 | n=8, **cfg seed 1** locked |
| `lf_slope` hand 0.5794 | n=8, **cfg seed 1** locked |
| `specular_removal` identity 0.4115 / hand 0.8406 | n=8, **cfg seed 1** locked |

Meanwhile, the saved champion is from the **cfg seed 0** run (`out/rb_*/`). So **within one
row the baseline and the champion are different extractions**, and moreover the cfg seed
differed per problem. We backed this with measurement: `py -3.11 baseline.py --problem
photon_denoise --seed 2` → running `robust.py` yields identity 0.2664 / hand 0.5371 as-is
(`out/rb_probe_cs2/`). `lf_slope --seed 1` also reproduces hand 0.5794 (`out/rb_probe_cs1/`).
**Only the evolution column reproduces at no cfg seed** — cfg seed 1's `lf_slope` is 0.557,
cfg seed 0 is 0.5465, and the old table's 0.5907 is neither. Since the artifact is gone, how
this column was built can no longer be traced. **That is the price of "not writing baselines
into the artifact,"** the very hole this fix closed.

Now `robust.py` **measures the baselines itself before starting evolution and writes them
into the JSON**. It aborts rather than writing out `null` baselines. The on-disk
`baseline_<problem>.json` is for cross-checking, and on discrepancy leaves both values in
`baseline_file_mismatch` (neither silently wins). Regression test =
`tests/test_robust.py::test_floors_are_never_null_even_without_a_baseline_file`.

#### Measure in pristine child processes

`--isolate` starts `evolve.py` in a fresh interpreter for each seed. Because the chain
fuzzer's reach count **depends on what was run earlier in the same process** (445/515 when
pristine vs. 433/515 after running `evolve.run` 20 times, same seed and same args), we do
not measure quoted numbers in a co-resident process. That isolation does not change the
result is fixed by
`tests/test_robust.py::test_isolated_seeds_reproduce_the_in_process_result` (**only the
place it runs may change, not the value it returns**).

**The one that lost was the most educational.** The champion of `specular_removal` found a
**cross-family path passing through the quaternion family**:

```
tb_rgb_to_quaternion -> tb_quat_color_rotate -> tb_quaternion_to_rgb -> ...
```

On the observed holdout it looked to be closing in on hand (0.8730) at 0.7761, yet on
**locked it fell to 0.6277** (hand 0.8343). Moreover the seed-to-seed variance on locked
was large, min 0.3037 / max 0.7549 / std 0.1900. This is a textbook case of a
train-selected champion failing to generalize, and **had we looked only at the observed
holdout we would have read it as "close."** The winner `vibration_map`, conversely, has an
extremely small locked variance of std 0.0006. We keep it as **a concrete example where
disclosing the variance mattered**.

The champion of `photon_denoise` was a **composition closed within the photon family
alone**:

```
tb_tcspc_irf_convolve -> tb_tcspc_background_subtract -> tb_spad_deadtime_correct
```

= the first example where a new family delivered value not as a "standalone usable op" but
as **a procedure that chains ops**. The champion of `lf_slope` starts with the same
`tb_lf_epi_slope` as hand and adds 3 image-filter stages, and its gain stays at +4.7% on
locked. Moreover **it beat hand in only 1 of 3 seeds** (seed-to-seed std 0.0224, difference
from hand +0.0246), so to say "it won" is to be buried in the variance.

### A trap I nearly fell into here (for the record)

I nearly wrote `lf_slope` as a **+38% improvement** at first. That was because I compared
hand's baseline 0.3945 with evolution's 0.5465, but **these two are numbers measured on
different extractions**. Re-measuring on the same locked split, hand is **0.5219**, and the
actual difference is **+4.7%**. **Always take the comparison on the identical split** —
comparing different extractions inflates the number by nearly 8×. Related:
[[feedback_beat_the_null_before_claiming]].

(This very section fell into the same trap twice. The 0.5794 "re-measured hand" above is
**the locked of cfg seed 1**, while the champion's 0.5465 is **the locked of cfg seed 0**.
Aligned to the same locked split, hand becomes 0.5219. **Even the correction number was yet
another extraction** — the very person who wrote "re-measured on the same split" had matched
only the split's name and not the cfg seed. As long as baselines are not written into the
artifact, this will keep happening.)

One more. The hand baseline for `lf_slope` initially placed `tb_lf_depth_from_focus`, but
the promotion gate exhaustively searched the best single existing op and showed that
**`tb_lf_epi_slope` is more than 2× stronger**. Placing the weaker one as hand makes the
problem look easier than it is, so we swapped it. **The baseline is not "the first approach
I thought of" but "the best existing approach."**

## Known limitations (next moves)

- **The bridge covers 58 (default) / 125 (wide) of the 382 catalog ops.** Multi-input ops
  (99 of them) do not fit the 1-input-1-output composition model, so a different composition
  model is needed.
- **There are 16 problems.** We added `counts` / `lightfield` / `rgbimage` / `video`, but
  problems starting from `qimage` / `beatcube` do not exist yet (they are in the vocabulary).
  `polsweep` has 3 consumers and 0 self-loops, so it is close to "just steps out in one move,"
  and for the same reason as `histcube` it is not in the vocabulary.
- **counterfactual utility is a single-stage-substitution approximation** (above).
- **On problems where the existing best is 0, relative improvement (ratio) is undefined.**
  `denom = abs(best) + 1e-12` returns `rel = +724476067514.28` without raising, and the
  judgment was **PROMOTE** (measured 2026-09-02: `vibration_map`'s only existing video op is
  the single `tb_temporal_bandpass`, whose locked score is exactly 0.0000). Now it sets the
  ratio to `None`, marks it "ratio undefined," judges by **absolute improvement** against that
  problem's own yardstick (hand / identity baselines), and excludes it from the relative
  aggregation. Not a single relative value of the non-degenerate cases moves. Regression test =
  `test_zero_baseline_no_longer_explodes_the_relative_gain` and 5 others in
  `tests/test_promote_gate.py`.
- **Actual writing of promotions is via champion only.** A path to DNA-ify mining candidates
  directly is unimplemented; for now the intended operation is "use passing candidates as the
  initial values of evolution."

## Related

- `docs/CHAIN_FUZZ.md` — the side that uses the same expansion mechanism for bug finding
- `docs/WAVE0_STABLE_SLOTS.md` — the danger of registry extension and name-pinned champions
- `backends_macro.py` — the reader side where promoted ops enter the vocabulary
