# Chain Fuzzer (chain fuzz) — a third quality-assurance layer that shakes ops by wiring them into chains

`tools/chain_fuzz.py`. The third layer, following unit tests and adversarial validation. The defects it targets are
**"the ones that pass everything in isolation but surface only when ops are wired into a chain."**

- Unit test = whether the inputs/outputs of a single op match the spec
- Adversarial validation = humans (and AI) attacking a single op's boundaries, degeneracies, signs, and division-by-zero
- **Chain fuzzer = whether things break when the next op consumes the previous op's output**

Lies in the type contract, mismatched tuple/list packing, NaN leakage, unexpected exception kinds, exponential
blow-up in expanding families — none of these are within the field of view of unit tests.

## Usage

```bash
# Diffuse: randomly wire 2000 chains and collect signatures
py -3.11 tools/chain_fuzz.py --chains 2000 --length 8 --seed 1 --out out/chain_fuzz.jsonl

# Converge: shrink each finding down to "the minimal op sequence that produces that signature"
py -3.11 tools/chain_fuzz.py --minimize out/chain_fuzz.jsonl
py -3.11 tools/chain_fuzz.py --minimize out/chain_fuzz.jsonl --only compute_fpfh

# Replay: run the minimal reproduction as-is (the entry point for attaching a debugger)
py -3.11 tools/chain_fuzz.py --replay 5000312 --script random_dropout,compute_fpfh

# Coverage breakdown: write out which ops ran and which ops never ran even once
py -3.11 tools/chain_fuzz.py --chains 1500 --coverage-out out/coverage.json

# Strength of targeted diffusion (0 = uniform, default 0.5)
py -3.11 tools/chain_fuzz.py --chains 1500 --explore 0.7
```

## Classification (kinds of signature)

| Kind | Meaning | Handling |
|---|---|---|
| `CONTRACT` | a documented `ValueError` | **White**. fail-closed did its job |
| `SUSPECT` | any other exception (TypeError/IndexError/…) | a hole in the contract. Add entry-point validation |
| `TYPEMISS` | the catalog's declared out type differs from what actually came back | a type lie. Fix the adapter or the declaration |
| `NONFINITE` | NaN/Inf silently came out of finite input | poison leakage. **But suspect the contract first** |
| `GROWTH` | the product exceeds the pool cap (exponential blow-up in an expanding family) | record and discard (**never cut it silently**) |
| `SLOW` | a single op exceeds the threshold (default 10s) | a performance smell |
| `OPTIONAL` | an ImportError from an optional dependency | white (not recorded) |

For `NONFINITE`, chase down the **origin and the contract** before blaming "the op that produced the non-finite value." A concrete example:
the `inf` from `sdf_subtract` was innocent — min/max algebra merely propagated `esdf`'s documented contract of
"+inf when fully free" accurately — whereas only `sdf_smooth_union` in the same family produced all-NaN through
arithmetic (inf − inf), which was a genuine bug. Non-finite values that are correct by contract are registered in
`NONFINITE_BY_CONTRACT` **with a reason**.

## Design essentials (why this shape)

### Typed pool
Following each op's declaration (in type → out type), it pulls arguments from the pool and returns the product.
The type vocabulary is shared with the catalog (`voxel`/`points`/`signal`/`matrix`/`table`/`pairs`/`roots`…).
`TYPE_CHECKS` holds a predicate function for each vocabulary term and **mechanically verifies that the declaration
matches what was actually returned**.

### Chain-specific seed
Chain *i* runs with `seed * 1_000_003 + i`. With a shared rng you cannot "replay only the *i*-th chain later,"
so minimization does not hold.

### Make the randomness of argument selection independent of position (the lifeline of minimization)
Candidate selection (which op to pull next) uses the chain rng, **while argument selection uses a separate random
source derived from `(chain seed, op name, that op's occurrence count)`**.
If you do not separate these, dropping a single unrelated op shifts every subsequent draw, and the minimization
replay is in principle unreproducible. **Measured: before separation, reproduction was 48/65 (74%);
after separation, 58/58 (100%)**. For the same reason, the pool's type selection is pinned to `sorted(pool)`
(because a dict's insertion order changes when an op is dropped).

### Caps and self-reported stalls
- `MAX_POOL_BYTES` (128MB): stops exponential blow-up in expanding-family chains. An overrun is **recorded** as
  `GROWTH` (silent cap forbidden).
- Inputs over 32MB are printed as `big-input:` before execution. Even in the event of a stall, the log alone
  reveals the culprit (measured, this was helpful twice).

## The operating pattern (repeat diffuse and converge)

1. Diffuse (2000 chains) → obtain a list of signatures
2. `--minimize` to reduce each signature to its minimal op sequence
3. **Prove it by running the minimal reproduction by hand, then** fix it (do not patch on a guess)
4. Once you fix one bug, **sweep the same class across sibling code**
   (e.g. for float32 overflow, actually run 1e39 through the 20 casts of the same kind and fix only the
   4 ops that hit it — measured, do not touch the ones that do not hit)
5. Re-run with the same seed and confirm the signature is gone

## Results so far (measured)

| Wave | Signature count | Main findings |
|---|---|---|
| Wave 3 | — | 22 type lies; promoted `RESULT_ADAPTERS`+`call()` to a first-class feature |
| wave-4 | 103 | TYPEMISS on 7 ops, 9 kinds of SUSPECT, a 6th family "small input → huge internal allocation" (TPS 12GB / PSF 64GB / CPD) |
| wave-5 | 4 | silent NaN from float32 overflow, `sdf_smooth_union`'s inf→NaN, 2 lineages of entry-point contract holes |
| math addition | 2 | detected the type lies of `mat_svd`/`mat_eigh` immediately on the first run |
| wave-7 | 172 (NONFINITE 2) | made argument-selection randomness position-independent = **the exploration path changed and produced new findings**. `poly_eval`'s silent inf from float64 overflow, `chamfer_distance`'s silent NaN from an empty point cloud (→ swept the 5 siblings in metrics3d) |
| optics addition | 18 (all CONTRACT) | registered 18 optics ops (`opsoptics`, new vocabularies `jones`/`stokes`). **Non-CONTRACT 0** — the bugs had all been caught, 6 of them, in the pre-registration adversarial audit (a string passing as a length / MTF's silent NaN / determinant's silent inf / cancellation in high-order Zernike bases / a 108GB internal allocation / an unreported quadrature error). For ops with fixed matrix shapes — `abcd_trace`/`jones_apply`/`mueller_apply` — uniform selection never once traverses the real path (measured: 0 times in 800 chains), so `OP_ARG_BUILDERS` synthesizes valid matrices for half of them |

| light-field + photon-counting addition (2026-09-01) | 40 | registered 34 new ops. **Non-CONTRACT 0** (the bugs had all been caught, 8 of them, in the pre-registration adversarial audit). The focus of this wave was not the ops but **3 holes in the fuzzer itself** (below) |
| unearthing the unexecuted (2026-09-01) | 62 | after fixing "silently skipping ops whose required arguments could not be bound," **5 non-CONTRACT findings came out of 3d ops that had never once been executed** (mismatches between the type declaration and the implementation) |

### Do not mistake "zero findings" for robustness — 4 holes in the fuzzer itself (2026-09-01)

This is a measured record that this layer itself can lie. All 4 were shaped so they could not distinguish
"**there is no bug**" from "**it was never executed in the first place**."

1. **Arguments with defaults could not be overridden.** An op whose default does not mesh with the pool's
   dimensions is rejected with a ValueError every time and is counted as "zero findings" without ever being
   executed (`lf_from_mla`'s default `angular=(5,5)` does not evenly divide 32x32, so 0 times in 1200 chains).
   → Made it so that only `OP_PARAM_HINTS` (targeted by op name) can override defaults too.
   Letting the name-level `PARAM_HINTS` act on defaults would change the behavior of existing ops all at once,
   so that one was left as-is.
2. **Coverage only reported a number.** "304/417" does not tell you whether the remaining 113 are robust or
   unreachable. → `--coverage-out` and a per-family breakdown. The moment it was emitted, the photon family
   10/17 = "fail-closed is so strong that 7 ops never execute at all" became clear.
3. **Signatures were splintering on numbers.** The better the error message, the more it contains
   run-specific numbers, so identifying them by raw string makes the same one finding a different signature
   every time (nearly all of the increment from 99 → 238 signatures was this). → Mask the numbers before
   forming the signature. Converged 238 → 40.
4. **Required arguments could not be bound and were silently skipped.** When the breakdown of the 100 unreached
   ops was actually measured, **70 of them were this**, and no record of it had been kept either. What was
   missing were the camera intrinsic matrix `K`, poses `R`/`t`, the RANSAC threshold `thresh`, voxelization's
   `bounds`/`res`, and so on. → Added hints. **Coverage 321 → 336, and 5 hidden non-CONTRACT findings.**

Type reachability can be solved as a fixed point (starting from the initial pool's types, keep adding the output
types of ops whose inputs are all available). Measured, of 434 ops only `refine_peak_newton` was structurally
unreachable due to the absence of a producer for the `score` type → added a seed. `tests/test_chain_fuzz_minimize.py`
pins down this invariant.

### The effect of targeted diffusion (do not mix the breakdowns)

With hundreds of candidates, the probability of a specific op landing in a length-6 slot is low. So a scheme was
added that, per chain, **picks a single target op and biases toward it** (the target is drawn from the chain-specific
seed, so it does not break the premises of `--minimize`/`--replay`). Measured on the same code, 1500 chains, length 6:

| explore | Coverage | Signature count |
|---|---|---|
| 0.0 (uniform) | 336/434 | 55 |
| 0.3 | 340/434 | 68 |
| 0.7 | 341/434 | 62 |

**The contribution of targeting is +5 ops.** The 321 → 336 gain is the effect of item 4 above (argument hints),
not the effect of targeting, so do not report them mixed together. Note that **at small scale, targeting is
worse** (60 chains × length 5: 67 ops vs 167 ops for uniform) — because it is a trade that gives up the breadth
of a single chain to buy reach into rare ops, the ordering of the aggregate flips with the run scale.

The type-space bias I tried first — "prioritize ops that produce types not yet in the pool" — **did not work**
(321 → 322 over 1500 chains). Because the pool is filled with every generator type from the start, the set of
prioritization targets is exhausted immediately. I keep the ideas that did not work rather than deleting them.

Both of wave-7's 2 findings were shrunk by `--minimize` to 5→2 / 4→2 ops, and only by running that minimal
reproduction by hand was the cause pinned down (the former was "a long signal mistaken for coefficients,"
the latter was "upstream outlier removal emptied the cloud"). **Without the shrinking, one would have had to
read the cause out of an 8-op chain** — that is where the practical value of the convergence phase lies.

## When extending

- **Adding a new op family to the catalog**: add the listing to `catalog()`. If the type vocabulary grows,
  add to `TYPE_CHECKS` and `make_generators()` as well.
- **Inputs with fixed shapes or physical constraints** (a 2x2 ABCD, a 4x4 Mueller, a length-4 Stokes with
  degree of polarization <= 1) will almost never land on valid values under uniform selection even when the type
  matches, and so **only CONTRACT comes out = the real path never runs**. Add a builder to `OP_ARG_BUILDERS`
  that "synthesizes valid values for half, adversarial input from the pool for the other half"
  (precedents: `abcd_matrix` / `wavefront_stats` / `abcd_trace` / `jones_apply` / `mueller_apply`).
- **Ops that return a documented non-finite value** go in `NONFINITE_BY_CONTRACT`
  (precedents: `mat_cond`, optics' `depth_of_field` / `gaussian_beam`).
- **If the return differs from the declared type**, keep the bare function returning the mathematically/
  conventionally correct value (a tuple, etc.), and register a `RESULT_ADAPTERS` on the catalog side so that
  `call()` returns the declared type (precedent: `mat_svd` → `{"U","s","Vt"}`).
- Regressions live in `tests/test_chain_fuzz_minimize.py` (the contract of the convergence phase) and
  `tests/test_chain_type_contracts.py` (agreement of declared types).
