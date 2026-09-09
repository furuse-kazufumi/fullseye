<!-- i18n-source-sha: bd321cfbdaaa -->
# Making general algorithms implementable — the algo-c support roadmap

[日本語](./GENERAL_ALGORITHMS.md) · **English**

> User request (2026-08-16): make **general algorithms** like those in
> <https://github.com/okumuralab/algo-c> (Haruhiko Okumura, *[Revised new edition] A Dictionary of
> Standard Algorithms in C*, full source) implementable in Fullseye too.
>
> **An honest read of where we are**: Fullseye is currently an **image-algorithm design AI** (an op
> registry of image/region/feature/contour/volume sorts; evolution + a holdout gate + Python→C
> codegen). General algorithms (sorting/searching/graphs/number theory/crypto/compression) do not
> ride on image sorts, so they need an **extension of the language, types and codegen**. This is
> multi-session work. This doc is its **confirmed plan** (the source of truth the next session
> executes with full context).

## The categories of algo-c (the book's TOC, a map of implementation targets)
※ The strict inventory is the repo's `/src` as source of truth.

| Field | Representative algorithms | Where it lands in Fullseye |
|---|---|---|
| Numerics | equations (bisection/Newton), numerical integration (Simpson/Romberg), linear systems (Gauss/LU), interpolation (spline), FFT | existing `dsp` (FFT) + a new `numeric` op family |
| RNG / statistics | Mersenne Twister, distributions, statistics | new `rng`/`stat` ops (deterministic seed) |
| Sorting | quick/heap/merge/shell/radix | a new `array` sort + a `seq` type |
| Searching | binary search, hashing, BST/AVL/B-tree | new `array`/`map` ops |
| Strings | KMP/BM/Rabin-Karp, edit distance, regular expressions | a new `text` type + ops |
| Graphs | DFS/BFS, Dijkstra, Warshall-Floyd, MST, max flow | a new `graph` type + ops |
| Geometry | convex hull, segment intersection, Voronoi | existing `pcseg`/geometry + a new `geom2d` |
| Number theory / crypto | primes, GCD, RSA, MD5/SHA, AES | new `numtheory`/`crypto` (educational, honest disclosure) |
| Compression | Huffman, LZ/LZW, arithmetic coding | a new `compress` op |
| DP / search | 8-queens, knapsack, DP | fscript's control flow + `array` |

## Implementation architecture (confirmed policy)
Extend Fullseye's existing assets to the general case. **Do not dilute the focus on the image AI**
(general ops are a separate tier / opt-in).

1. **Type-system extension**: to the current 6+1 sorts (image/region/feature/contour/match/any/
   volume), add **`seq` (1-D array) / `text` (string) / `graph` / `scalar`** (the sorts in `ops.py`,
   the `fslib` types).
2. **Making fscript a general language**: it already has if/for/while, assignment and tuples. Add
   **array/string literals, indexing and procedures (functions)** in stages (the current decision was
   to narrow the language scope, so the general tier is unlocked under a separate profile). Source of
   truth = revisit the A/B branch in `docs/FSCRIPT_DECISION.md`.
3. **Op-registry extension**: register each algorithm of algo-c as an **op** (name/in-out sort/params/
   **c_stmt**). Reuse the existing Python→C codegen (`engine.to_python`/`to_c`) + **difftest** (an
   honest gate: Python is the oracle, the C is differentially verified) as is → **guarantee "it can be
   implemented in C" by actual measurement**.
4. **honest gate**: feed algo-c's C to `difftest` as the reference implementation and verify the
   numeric/bit match with Fullseye codegen's C (an extension of the existing gate). Respect the
   **license of the original code** (algo-c ships with the book; the terms of use need checking) and
   **reimplement from the specification, not by copying verbatim** (the public-disclosure policy).

## The staged plan (from the next session onward)
- **P1**: `seq`/`scalar` types + 3 sorts (quick/heap/merge) as ops + C codegen + difftest.
  = the minimal proof that "Fullseye can generate C for general algorithms too".
- **P2**: a numerics (bisection/Newton/Simpson/Gauss) op family.
- **P3**: strings (KMP/BM/edit distance) + a `text` type.
- **P4**: graphs (Dijkstra/BFS/MST) + a `graph` type.
- **P5**: compression/number theory/crypto (educational, honest disclosure, no verbatim copying).
- In each P: the evolution gate is out of scope (general ops are deterministic, they don't evolve by
  holdout), **the C match is measured honestly by difftest**, and a new tier is shown in Studio's op
  browser.

## Honest limits and discipline
- **No verbatim copying**: **reimplement from the specification** while referring to algo-c's C
  (`feedback_provenance_research_method`). Do not ingest code before the license is checked.
- **Do not dilute the focus on the image AI**: general ops are an opt-in tier. The north star
  (covering HALCON-grade image ops + honest holdout) is unchanged.

---

## P1 completion record (2026-08-16, Opus5[1m]/ultracode)
**Achieved the minimal proof that "Fullseye can generate C for general algorithms too, and can
measure the C match honestly".**

- **A new tier (fully separated from the image REGISTRY, opt-in)** = `algo.py`. Newly introduces the
  `seq` (1-D sequence) / `scalar` (single real) types. Because it never touches the image
  `ops.REGISTRY`, evolution search and Wave-0 champion pin are unaffected (proven by tests).
- **op (5)**: 3 sorts `quicksort` (Hoare/median-of-three/Lomuto/explicit stack), `heapsort` (Williams
  1964 binary max-heap), `mergesort` (von Neumann 1945 top-down stable) = `seq→seq`. Plus, giving the
  `scalar` type a role, the reductions `seq_max`/`seq_min` (`seq→scalar`, order-independent and exact).
  **All reimplemented from the specification** (the algo-c source is not copied; each op states its
  `provenance`).
- **A single source of truth**: each op **holds its Python body and C body as strings**; the in-process
  reference has `algo.py_fn` compile the same string, and `algo_codegen` emits the same string as a
  standalone `.py`/`.c`. → the tested oracle and the shipped artifact don't drift (proven by the test
  `test_emitted_python_*`).
- **codegen** = `algo_codegen.py` (`emit_python`/`emit_c`. The C is a function + a binary-I/O driver = a
  fully compilable standalone program).
- **honest gate** = `algo_difftest.py` (two actual measurements, not a deferred skip):
  (1) the Python reference **== a numpy oracle** (`np.sort`/`np.max`/`np.min`), (2) codegen **C ==
  Python, bit-for-bit** (holdout = 10 edge cases + 40 random). Because these ops only move/select
  existing doubles, a correct implementation is a bit-exact match (tol=0.0).
- **★measured (2026-08-16, `zig cc` = `python -m ziglang cc`, ziglang 0.16.0 installed via pip)**: all 5
  ops **python diff 0.00e+00 / C-vs-Python diff 0.00e+00 / passed=True** (real compile → real run →
  bit compare). = "measure the C match honestly" achieved as **a real measurement, not a deferred
  skip**.
- **fail-closed**: no toolchain → the C half is an honest skip (the Python half runs). compile/run
  failure → gate FAIL (not a neutral skip; proven by the test
  `test_difftest_compile_error_fails_closed`).
- **facade**: `fullseye.algo_ops()/run_algo()/algo_to_c()/algo_to_python()/algo_difftest()` (+ `api.py`).
  **skill** = a "General algorithms (algo-c tier)" section added to
  `~/.claude/skills/image-processing/SKILL.md` (usable from a subagent).
- **tests**: `tests/test_algo.py` (42 = registry consistency, Python==sorted/oracle, stability, single
  source of truth, C bit match [when a toolchain exists], compile-error fail-closed, no image-registry
  contamination, facade).
- **honest limits**: ① a sequence containing NaN is excluded from the holdout because the convention of
  a comparison sort diverges between Python/C/numpy (disclosed). ② ops whose **accumulation becomes
  order-dependent** (like a sum of floats) are not included in P1 (seq_max/min are exact). ③ CLI
  subcommand integration (`imgevolve.py algo ...`) and the Studio op-browser tier display are the next
  step (P1.5). ④ Making fscript's array/procedure a language (architecture item 2 of the design doc) is
  out of P1 scope (a separate track).

## P1 hardening after adversarial review (2026-08-16, [[feedback_no_solo_ai_judgment]])
Carried out an independent adversarial review of this session's own code (a Workflow of 4 lenses =
algorithm correctness / codegen·C safety / gate soundness / integration·focus safety, 22 findings). I
did first-hand code verification of every one (the v11 discipline) and fixed the true defects:
- **[HIGH] the gate's fail-open (NaN/signed zero)**: `_max_diff_*` was swallowing a NaN diff with
  `max(0.0, nan)=0.0` and falsely certifying a "bit match" (reproduced by measurement) → split into
  **(1) Python×oracle = value comparison but fail-closed on non-finite (inf, doesn't pass with tol),
  (2) C×Python = a true bit comparison (the raw bytes of IEEE float64 = detects signed zero / NaN
  payloads too)**. A `c_verified` field distinguishes a "pass verified by a real compile" from a "pass
  unverified because there's no toolchain".
- **[HIGH] quicksort is O(n²) on many-duplicate input** (Lomuto `<=` puts all equal values on one side;
  a binary = a flattened binary mask is realistic input, measured quadratic) → rewrote both Python and C
  to **3-way (Dutch national flag) partition + median-of-three** (all-equal is O(n)). Added a
  performance-guard test (20000 all-equal < 2s).
- **[HIGH] the emitted C `heapsort` collides with BSD `<stdlib.h>`'s `heapsort()`** (uncompilable on
  macOS/BSD; measured with `zig cc -target x86_64-macos`) → renamed the C symbol to **`heapsort_asc`**
  (unified with `mergesort_asc`). Added **a macOS cross-compile test for every op** (a regression
  guard).
- **[LOW] 3 fail-open/UB issues in the C**: mergesort's malloc failure = unsorted output → **an in-place
  insertion-sort fallback (fail-closed, keeps stable)** / heapsort's `2*root+1` int overflow → made
  **long long** / the driver's len in 32-bit and size_t wrap → **a `SIZE_MAX/sizeof(double)` upper-bound
  check + `<stdint.h>`**.
- **[MED] test_mergesort_is_stable was vacuous** (a value comparison = any sort passes) → rewrote it to
  observe stability from **the order preservation of signed zero** (detects a regression to `<` =
  unstable). Also added a **no-mutation test** (`run(a)` doesn't destroy the caller's list).
- **[MED] the holdout was small, duplicates thin** → added large all-equal (300) / binary (300) /
  few-distinct (300) + duplicate-heavy random (the C gate now actually inspects the duplicate/size
  regimes).
- **[MED/honesty] the NaN convention was undocumented** → stated "NaN-free assumed; non-finite is
  fail-closed at the gate" in the module docstring and each op docstring. seq_max/min's
  "order-independent" → "order-independent for NaN-free input".
- **An adjacent existing ship-bug**: `sample_images` (which studio imports at runtime) was missing from
  `pyproject.toml` py-modules = it disappears in a non-editable wheel → added it (confirmed by a real
  wheel build).
- Tests **43→58** (added bit-check, fail-closed, macOS cross-compile, duplicate performance, no-mutation,
  c_verified, stability observation). A re-run of every op's difftest = python/C both diff 0.0, bit
  match, passed=True.
- **Not fixed (the user's call, existing issues outside P1 scope)**: (a) `pyproject.toml`'s
  `[tool.setuptools.package-data]` `"*"` glob can't put root-level flat `studio_assets/` and `data/`
  into the wheel (studio i18n/op-help/sample images are missing in the installed wheel = existing;
  needs a MANIFEST.in or a package-ization design change) / (b) `fullseye.__all__` lacks the 18
  pcseg-family names of api (missing on star-import = existing). **The algo tier is unrelated (algo* is
  reliably bundled as py-modules; the facade is consistent).**

## Next (P2 onward)
- **P1.5a (done, 2026-08-16)**: added the `imgevolve.py algo <list|run|emit-c|emit-py|difftest>`
  subcommand (a unified CLI entry point. `algo run quicksort --seq 3,1,2` / `algo emit-c mergesort` /
  `algo difftest all`). 2 CLI regression tests + updated the skill's CLI examples.
- **P1.5b (completed 2026-08-17)**: shows the general(algo) tier in Studio's op browser as
  **read-only** (recorded below).
- **P2 (completed 2026-08-16)**: numerics ops on the seq/scalar type base. **simpson / bisection /
  newton** (a seq→scalar that embeds the polynomial/samples in the input seq, riding the existing reduce
  driver) + **gauss_solve** (Gauss elimination for a linear system, partial pivoting = the P2 completion
  record below). honest gate = **C-vs-Python is a bit match** (the same algorithm + `-ffp-contract=off`
  to suppress FMA) / **Python-vs-oracle is a numeric tolerance** (`AlgoOp.tol`) checked against an
  independent oracle (simpson = scipy / root-finding = the residual |p(root)| / gauss = `np.linalg.solve`).
  fail-soft is documented honestly.
- **P3 (completed 2026-08-17)**: string ops (the P3 completion record below). The `text` type rides the
  existing float64 harness under the convention "carry a codepoint sequence as float64"
  (`text_to_seq`/`seq_to_text`), achieved without adding a new wire type.
- **P4 (completed 2026-08-17)**: graph ops (components/mst_weight/dijkstra, the P4 completion record
  below). `graph` rides the existing harness packed as `[n, m, (u,v,w)*m]` (no new wire type needed).
- **P5 (completed 2026-08-17)**: number theory, compression, educational hashing (gcd_seq / sieve_primes
  / pow_mod / crc32 / rle_encode, the P5 completion record below). Carries integers as float64 (exact
  <2^53) so no new wire type is needed. Every op is **exact** (C bit match, and Python == an independent
  oracle at tol 0). **Crypto is primitives only** (modular exponentiation / CRC) = full RSA/AES/SHA don't
  ride the float64 seq harness due to bignums/large state, disclosed honestly as out of scope.

## P3 completion record — string ops (2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**Added 3 string algorithms to the algo tier.** "A string = carry a codepoint sequence as float64" (a
Unicode scalar is < 2^53 so it's exact) so it **rides the existing float64 binary harness unmodified**
(no new wire type). Values are compared only for equality (exact with integer codes); positions/distances
are exact integers → **C-vs-Python bit match, and Python-vs-oracle is EXACT (tol 0)**.

- **op (3)**: `strfind` (Knuth-Morris-Pratt = a failure-function prefix automaton. Input
  `[m, pattern(m), text]` → the ascending list of all occurrence start positions, including overlapping
  = **variable-length KIND_MAP**, reusing the variable-length wire made for gauss) / `edit_distance`
  (Wagner-Fischer/Levenshtein 2-row DP = **KIND_REDUCE**, exact integer) / `lcs_length` (longest common
  subsequence length, 2-row DP = KIND_REDUCE). All reimplemented from the specification (provenance
  stated). fail-soft = an empty pattern/truncation/pattern > text is `[]`; na<0/truncation is `0.0`.
- **A single source of truth + text-type helpers**: added `text_to_seq(s)`/`seq_to_text(seq)`
  (codepoint ↔ float64).
- **honest gate measured (all 3 ops passed=True, c_verified=true)**: Python == **an independent oracle**
  (strfind = a naive all-occurrences scan [independent of KMP] / edit, lcs = a **top-down memoized
  recursion** [a different code path from the bottom-up 2-row DP]) at **diff 0.0 (exact)** / codegen
  **C == Python bit match** (ziglang cc).
- **A work-graph op wave (a demonstration of candidate d)**: for each new op, stack an `algo_gate` gate
  node = **1 op = 1 node**. Put the 3 ops on `raptor-worklog add --capability tool` → `run-once
  --available tool:command` for **unattended done** (generating gate_ok.json).
- **regression**: a test group for strfind/edit_distance/lcs_length in `tests/test_algo.py` (known
  solutions, random × independent oracle, fail-soft, variable-length output, no-mutation, python exact, C
  bit match). Whole suite **4669 passed / 0 failed** (+20 from 4649 after P2), ruff clean, mypy regression
  0. commit + push was done in this session (the user's approval 2026-08-16 at bedtime = the push gate
  opened).

### P3 string hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
The independent adversarial review Workflow (4 lenses; each finding confirmed by a verification agent
against real code / a real compile) = **3 findings all CONFIRMED** (2 of them report the same root cause
from different lenses). After first-hand verification I fixed them all:
- **[MED] Python runs `int(a[0])` before the range check → doesn't match C**: edit_distance/lcs_length's
  Python evaluates `na = int(a[0])` first (truncation), while C guards the raw double first. For
  **`a[0]` ∈ (-1.0, 0.0)** (e.g. -0.5), Python continues with na=0 (a valid empty string) and returns a
  real distance, whereas C rejects it at the raw guard → 0.0 → **a bit-match contract violation** (measured
  with ziglang cc: `[-0.5,65,66]` = Python 2.0 vs C 0.0). The holdout has only non-negative integer na so
  the gate didn't detect it.
- **[LOW] Python crashes on a NaN header** (C is fail-soft): `int(nan)` raises a ValueError, violating the
  op docstring's fail-soft promise (C returns 0.0/`[]` at a NaN-false guard). ※NaN is out of contract under
  "NaN-free assumed", but it's the same defect in guard ordering.
- **Fix (one fixes both)**: moved the **raw-value guard before `int()`** in all 3 ops' Python
  (`not (x >= lo and x <= hi)` = NaN-false) = **an exact mirror of the C**. gauss was already correct with
  its raw guard (unified into the same shape).
- **Boundary coverage**: because it's outside the oracle's verified domain (the oracle emits a different
  value under truncation = exactly this bug), **pin the C-vs-Python parity on fractional-negative/NaN/
  over-limit headers directly with a dedicated test** (`test_string_c_python_parity_on_bad_headers`) + a
  Python fail-soft no-crash test. The core algorithm-correctness/c-safety findings were 0 (KMP/DP/memory
  safety are clean).
- After review: all 3 ops' difftest = python exact / C bit match / c_verified=true, whole suite green
  (below), ruff/mypy regression 0.

## P2 completion record — gauss_solve (2026-08-16, Opus5[1m]/ultracode, `graph-loop-engineering`)
**Added Gauss elimination for a linear system (partial pivoting), completing the P2 numerics.** As the
user instructed, made it a node in the raptor work-graph with the `graph-loop-engineering` skill and had
a tool driver run it unattended (the two-layer policy = breadth is the work-graph's difftest gate; the
acceptance of adversarial findings and the push are the session's human checkpoint).

- **A new kind `KIND_MAP` (`map_varlen`) = variable-length seq→seq**: the existing ops are only sort
  (input length = output length) or reduce (→1 value), but a linear-system solution (input `[n, the n×(n+1)
  augmented coefficient matrix row-major]` → the solution vector of length n) has input length ≠ output
  length. The C boundary = `int f(const double* a, int n, double* out)` writes out_len (≤ n) values into
  out and returns out_len (fail-soft = 0).
- **A variable-length output mode in the `algo_codegen` driver**: the KIND_MAP branch writes
  `{int32 out_len, out_len*float64}` (the same wire as sort, but out_len ≠ input length). The out buffer is
  allocated at input length (the contract out_len≤n guarantees the upper bound) + a **fail-closed clamp** to
  `out_len ∈ [0,len]` (a runaway op won't make the reader over-read).
- **gauss_solve (`algo.py`)**: the Python reference (stdlib only, index-by-index mirroring the C) and the C
  reference are a single source. Forward elimination (partial pivot = pick the max |element| row) + back
  substitution. Singular (a pivot 0 remains)/malformed is fail-soft with **[] / 0** (no exception).
  **Exactly matching the FP operation order of Python/C** (the same division, subtract-then-multiply, an
  exact `0.0` assignment to the eliminated element, abs via inline sign-flip so no dependence on `math.h`/
  `-lm`) so it's a bit match. int overflow is prevented with `n≤46340` + `long long need`.
- **The honest gate in two stages (measured)**: (1) Python **== `np.linalg.solve`** (an independent
  oracle; a well-conditioned holdout of 34 cases = diagonally dominant + row permutation + **cases that
  require a pivot** [exact-zero (0,0), tiny (0,0), a 3×3 zero diagonal]) → **max abs diff 3.55e-15** (tol
  1e-9). (2) codegen **C == Python bit match** (`ziglang cc`, `-ffp-contract=off`) → **diff 0.0 /
  c_verified=true**. The **C fail-soft on singular/malformed is verified to match Python exactly** by a
  separate test (a C-vs-Python direct comparison rather than a holdout, because it's a region the oracle
  doesn't support).
- **`tools/algo_gate.py` (a reusable gated-stage runner)**: the work-graph's `CommandWorker` decides done
  by produces being generated or exit0, so in the current state where difftest writes JSON even on FAIL,
  it's **fail-open** (a failing gate is done). Close this = **write the marker `gate_ok.json` only on pass,
  the exit code = the verdict**. Point the node's produces at the marker and a failing gate becomes a node
  failure **fail-closed**. Usable as-is for the op waves from P3 onward (1 op = 1 node).
- **Work-graph node-ization**: `raptor-worklog add --capability tool --project imgevolve --priority 0`
  (spec = `tools/algo_gate.py --op gauss_solve --out <OUT>`, produces = `<OUT>/gate_ok.json`) → `run-once
  --available tool:command` for **unattended run → status=done** (exit0, c_verified=true, a bit-match
  marker generated).
- **regression**: added gauss + algo_gate + C fail-soft + require_c test groups to `tests/test_algo.py`
  (the algo tests **93 passed**), whole suite **4649 passed / 0 failed** (+12 from 4637 before review). All
  my files **ruff clean**, mypy regression 0 (the existing baseline = only the scipy/ziglang stub absence
  and the existing quirk of the difftest signature; 0 from my added lines). All local commits, **not pushed
  = human-gate**.

### P2 gauss hardening after adversarial review (2026-08-16, [[feedback_no_solo_ai_judgment]])
An independent adversarial review Workflow of the gauss code I wrote (4 lenses = numeric correctness / C
safety / gate soundness / integration·coverage; each finding **reproduced by running** by a verification
agent). Fixed all **4 CONFIRMED of 5 findings** after first-hand code verification:
- **[HIGH] algo_gate's fail-open (unknown op)**: `find_algo`'s `SystemExit` was **before** `marker.unlink()`,
  so an old pass's `gate_ok.json` remained → CommandWorker **wrongly decides done** on produces existing
  (surfaces on a re-run after an op rename/typo). → moved **mkdir + stale-marker unlink before the registry
  check** (no early exit inherits an old pass). Added a regression test.
- **[MED] the gate can't disprove partial pivoting**: the holdout was diagonally dominant only (no
  exact-zero pivot) → even a mutant with the pivot search removed matched `np.linalg.solve` to 2.2e-14 and
  **PASSED** (pytest catches it, but the algo_gate the work-graph runs is a difftest holdout so it doesn't).
  → added **pivot-required cases** (exact-zero (0,0) = `[[0,1],[1,0]]`, tiny (0,0) = `[[1e-14,1],[1,1]]`, a
  3×3 zero diagonal) to the holdout = the no-pivot mutant is falsified by a **structural mismatch → inf →
  FAIL** (confirmed by my own measurement). Also corrected a misleading comment.
- **[MED] a pass marker even on a C skip**: even when the C half skips due to no toolchain (honest but
  **unverified**), it wrote the marker on `res["passed"]` alone, and the graph reads only the marker's
  existence → **certifies uncompiled C**. → added `require_c` (default True) = an unverified pass doesn't
  write `gate_ok.json` (writes diagnostics to `gate_unverified.json`) **fail-closed**. `--allow-unverified-c`
  is an explicit opt-out; `--no-c` is an intentionally weak Python-only gate.
- **[REFUTED] "the out_len==0 wire is untested"**: the `test_gauss_c_fail_soft_matches_python` I had added
  proactively already covers it by compiling/running real C → the verification agent confirmed its
  soundness by mutation and **rejected** it. Only the remaining minor macOS cross-compile-guard nit
  (`_ALL`→`_ALL_OPS` so numeric/gauss are covered too) was adopted.
After review, gauss difftest = python 3.55e-15 / C bit match / c_verified=true, and the work-graph node
(hardened) = done.

## P1.5b completion record — showing the general tier read-only in Studio (2026-08-17, Opus5[1m]/ultracode)
**Shows the general(algo) tier in the op browser.** A design that doesn't dilute the image focus = general
ops are a separate compute model of seq/scalar, so **read-only** (can't be put in an image pipeline).
- An opt-in parameter on `api.list_ops(include_algo=False)` + `api.algo_rows()` (backend="general",
  category "algo:*", sorted to the end at tier "z_algo", halcon None, with provenance). **The default is
  unchanged** (existing callers get image ops only = focus preserved).
- studio: `all_ops = list_ops(include_algo=True)` shows them in the browser / `_op_row` has an algo
  fallback / `op_signature_detail`, `op_tooltip` branch for general ("a seq/scalar op, not an image op, run
  via CLI" + provenance) / `on_op_selected` disables Insert, Run once, Help and the a/b knobs when a general
  op is selected / `add_op`, `run_op_once`, the palette reject a general op with a flash. Defence in depth =
  **`PipelineModel.add_stage` is KeyError fail-closed on the image REGISTRY**.
- **Adversarial review (2 lenses, execution-verified) = 3 CONFIRMED (2 the same root cause), all fixed**:
  - **[HIGH/MED] the Program (HDevelop code) editor's "Apply → pipeline" was unguarded**: `op_names` was
    derived from `list_ops(include_algo=True)`, so general names propagated into the code parser/completion/
    Help picker → `apply_program` writes `model.stages=` directly, **bypassing the add_stage backstop** →
    general ops entered the pipeline. → made **`op_names` image-only** (excluded on `backend != "general"`;
    the browser's `all_ops` keeps general) + a general-stage-rejection guard in `apply_program` (defence in
    depth).
  - **[MED] the Help dialog's picker misrepresented general** ("Two knobs a,b tune this operator") → the same
    image-only `op_names` excludes it from the Help picker too (the root fix resolves both).
- Regression tests: the general branches of `_op_row`/signature/tooltip, offscreen that the browser shows
  general while Insert etc. are disabled, that `win._op_names` excludes general, that the code parser rejects
  a general row. Whole suite green, ruff net-new 0 (the new tests are clean; studio.py's flash is consistent
  with the file's `%`-format idiom), mypy regression 0. **Candidate (d) op wave** demonstrated too = put all
  12 algo ops on the work-graph as 1 op = 1 node and `run-once` for unattended done.

## P4 completion record — graph ops (2026-08-17, Opus5[1m]/ultracode, bonus)
**Added 3 graph algorithms to the algo tier** (out of the candidate set but a bonus in line with the user's
"proceed with all of it" + 7-8h of autonomy). Pack the graph into an input seq (`[n, m, (u,v,w)*m]`,
undirected; dijkstra prefixes src as `[n, m, src, ...]`) to ride the existing float64 harness.
- **op (3)**: `graph_components` (union-find, the number of connected components = KIND_REDUCE, exact
  integer) / `graph_mst_weight` (Kruskal, the total weight of the minimum spanning forest = KIND_REDUCE) /
  `graph_dijkstra` (single-source shortest distances = **KIND_MAP**, -1.0 = unreachable). A deterministic
  union rule + a (weight,index) sort + a settle order of min-distance·min-index make **C == Python bit
  match**.
- **★made the KIND_MAP driver two-stage (size-probe)**: dijkstra's output length n **can exceed** the input
  length 3+3m (a sparse graph). The old driver allocated out at the input length, so it had a heap-OOB defect
  → changed to a two-stage protocol where the driver asks the out_len upper bound via `f(a,n,NULL)`,
  allocates exactly that much, then does the real write (added `if(!out) return <bound>` to
  gauss/strfind/dijkstra).
- **honest gate**: Python == the independent oracle **scipy.sparse.csgraph**
  (connected_components/minimum_spanning_tree/dijkstra). On an integer-weight holdout, **components exact
  (tol 0) / mst, dijkstra tol 1e-9 (measured 0)**. C == Python bit match (ziglang cc). The MST/Dijkstra
  holdout is a simple graph (avoiding csr duplicate summation); components allows multi-edges (connectivity
  only).
- **Adversarial review (3 lenses, execution-verified) = 2 CONFIRMED (both HIGH, dijkstra memory safety), all
  fixed**: (#2) the out buffer was input-length size → OOB write for n>3+3m → resolved by the **two-stage
  driver** (fixed proactively before discovery). (#1) the src guard was raw `sd < nd` → for a fractional nd,
  src==n passes and out[n] is OOB → **bounded by the integer n** (`sd < n`). 1 REFUTED (unreachable nodes
  untested ← covered by the known-answer/sparse tests). No other findings from the numeric/oracle lenses.
- **op wave**: the 3 graph ops are also work-graph-gated (all 15 algo ops done unattended as 1 op = 1 node).
  Whole suite green, ruff clean, mypy regression 0. push in-session (the user's approval).

## P5 completion record — number theory, compression, educational hashing (2026-08-17, Opus5[1m]/ultracode, `graph-loop-engineering`)
**Added 5 general algorithms to the algo tier, completing the algo-c roadmap (P1→P5).** Carries integers as
float64 (exact < 2^53) so no new wire type is needed. Bit/integer arithmetic is done C-side by casting to
`unsigned long long`/`unsigned int` and back to double (the result is < 2^53 and exact). **All 5 ops are
exact** (C == Python bit match, and Python == an independent oracle at tol 0).
- **op (5)**:
  - `gcd_seq` (KIND_REDUCE): the GCD of a non-negative integer sequence (Euclid, folded over the sequence).
    oracle = `math.gcd`.
  - `sieve_primes` (**KIND_MAP**): the sieve of Eratosthenes. Input `[n]` (length 1) → primes ≤ n ascending =
    **a representative example where the output greatly exceeds the input length**. size-probe upper bound
    `π(n) ≤ n/2 + 1` (2 and the count of odds, no log needed = no dependence on `math.h`). oracle = trial
    division (an independent path).
  - `pow_mod` (KIND_REDUCE): modular exponentiation base^exp mod m (square-and-multiply = the primitive of
    RSA/DH, educational). oracle = builtin `pow`.
  - `crc32` (KIND_REDUCE): CRC-32 (IEEE 802.3, reflected, poly 0xEDB88320). **c_func is `crc32_ieee`**
    (defensively avoiding a symbol collision with zlib/BSD's `crc32`, cf. heapsort_asc). oracle = `zlib.crc32`
    (the zlib C library = fully independent).
  - `rle_encode` (**KIND_MAP**): run-length encoding → `[value, count, ...]` (**output at most 2× the
    input**, 2n if all distinct). reversible, oracle = `itertools.groupby`.
- **★disclosure of the honest domain (pow_mod)**: to keep the intermediate uint64 product from overflowing,
  **mod ≤ 2^32−1** (the product < mod² < 2^64), base/exp ≤ 2^53. The result < mod < 2^53 is float64 exact.
  Out of domain is fail-soft 0.0 (the raw guard before int(), NaN-safe).
- **★crypto is primitives only (honest scope)**: full RSA/AES/SHA don't ride the float64 seq harness due to
  bignums/large state, stated as out of scope. Provided the primitives that do ride (modular exponentiation /
  CRC checksum) as an **algorithm disclosure** (not a cipher).
- **★an integrality guard (new, an honest improvement)**: gcd_seq/pow_mod/crc32 take **data values** so a
  non-integer is malformed → fail-soft. `x == float(int(x))` / `x == (double)(long long)x` is
  **short-circuited after the range check** (for NaN/over-limit values the cast isn't reached, avoiding an
  `int(nan)` crash / the C `(long long)nan` UB). Header values (sieve's n) use the same truncation convention
  as the existing gauss/dijkstra.
- **★using the KIND_MAP two-stage size-probe in the two new ops**: for both sieve (output ≫ input) and rle
  (output ≤ 2× input), `if(!out) return <upper bound>` has the driver ask the upper bound → allocate → do the
  real write. A dedicated test pins by real compile/run that **the C output doesn't heap-OOB even when it
  exceeds the input length**.
- **honest gate measured (all 5 ops passed=True, c_verified=true, ziglang cc)**: Python == the independent
  oracle **diff 0.0 (exact)** / codegen **C == Python bit match diff 0.0**. crc32 was confirmed to match
  `zlib.crc32` on every byte value, "Hello", and all 256 bytes.
- **work-graph op wave**: made the 5 P5 ops `algo_gate` gate nodes (`1 op = 1 node`, priority 0, tool
  capability) → `run-once --available tool:command` for **5 nodes unattended done** (each `gate_ok.json` = a
  c_verified/bit-match marker generated). = **all 20 algo ops are work-graph-gated** (15→20).
- **regression**: a P5 test group in `tests/test_algo.py` (known solutions, independent-oracle check
  over-random, fail-soft, integrality, the two-stage probe's output overrun, bad-input C-vs-Python parity,
  no-mutation, python exact, C bit match). Whole suite **4700 → 4736 passed / 0 failed** (+36), my new files
  ruff clean, mypy new errors 0 (existing baseline only).

### P5 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
An independent adversarial review Workflow of the P5 code I wrote (4 lenses = algorithm-correctness /
C-safety-codegen / gate-honesty / integration-focus; each finding **reproduced by a real compile/run** by a
verification agent, 18 agents). **14 raw → 9 CONFIRMED / 5 REFUTED**. After first-hand reproduction of every
CONFIRMED (compiling/running with ziglang myself), I fixed them. **Notable is the deep probe into "can the
gate falsify my own guards"**:
- **[MED] pow_mod's honest domain (base/exp ≤ 2^53) was unmeasured by the holdout** → a C mutant that
  truncates exp to uint32 passes the gate (the top ~33 bits unmeasured at base/exp max 1e6/1e5). **Fix** =
  added 2^53-boundary cases ([2,2^53,7], [2^53,2^53,2^32-1] etc.) to the holdout + widened random to the full
  [0,2^53]. **Reproduction confirmed**: after the fix, the exp→uint32 mutant is `passed=False`.
- **[LOW] gcd (2^53 guard) / sieve (5,000,000 cap) have the same kind of unmeasured boundary** → added a gcd
  boundary to the holdout (mutant falsify confirmed); because the Python reference is slow at the sieve cap
  (~7.7s), a **dedicated C-only test** measures accepting n=5,000,000 (π=348513, cross-checked with an
  independent numpy sieve) and rejecting n=5,000,001.
- **[MED] -ffast-math / -ffinite-math-only erase the NaN guard** → compiling the shipped C artifact with
  fast-math omits the NaN rejection of `x >= 0.0` and executes the `(long long)NaN` UB (**self-reproduced**:
  `gcd_seq([NaN,6])` is 2.0 under `-ffinite-math-only`, 0.0 under the gate default `-ffp-contract=off`). **Fix**
  = inject `#if __FAST_MATH__ || __FINITE_MATH_ONLY__ → #error` into `algo_codegen.emit_c` (the artifact
  **refuses to build** rather than silently miscompiling = fail-closed) + honestly corrected the C comment's
  "UB unreachable" to be under an IEEE assumption + added a fast-math build-refusal test.
- **[MED] the C's short-input guards (pow_mod `n<3` / sieve `n_in<1`) are un-falsifiable** → because every
  holdout is fixed-length, removing the guard admits an OOB heap read yet every test stays green. **Fix** =
  added empty/short arrays to the holdout / parity tests to exercise the boundary path. **Honest disclosure**:
  a black-box value comparison **can't deterministically** catch a safety-guard removal (the OOB read value is
  non-deterministic). Properly ASan is the right approach, but **ziglang's ASan can't link in this Windows
  environment** (`__asan_shadow_memory_dynamic_address` undefined). The Python guard is deterministically
  falsifiable; the C guard is catchable with boundary exercise + a sanitizer (automation held off due to the
  environment constraint).
- **[MED] pow_mod's `1 % mod` special branch is un-falsifiable** (no simultaneous exp==0 and mod==1 case
  anywhere) → added [7,0,1], [0,0,1] to the holdout + a known-solution assert (**reproduction confirmed**: the
  `1%mod→1` mutant is `passed=False`).
- **[MED] the P5 oracles crash on out-of-domain input** (zlib.crc32 / pow() / int(nan) raise) → adding
  out-of-domain cases to the holdout makes difftest throw = the gate **can't structurally cover** the guard
  convention (only a single unit test catches it). **Fix** = made each P5 oracle **domain-aware** (`_int_in`
  mirrors the op's declared domain → out of domain returns the op's fail-soft value 0.0/[] = crash avoided).
  This makes the gate itself able to falsify a guard divergence (**reproduction confirmed**: mutants removing
  crc integrality / narrowing the gcd guard are each `passed=False`).
- **[LOW] Studio's Operator-help card misrepresents a general op as "Two knobs a,b"** (P1.5b closed the picker
  but the browser-selection `op_help_html` fall-through was unguarded, affecting all 20 algo ops) → added a
  general branch to `op_help_html` (shows provenance + the packed-input contract + CLI execution) + added
  `desc` (op.doc) to `_op_row`/`api.algo_rows` + a regression test.
- **[LOW] the image-processing skill's YAML frontmatter description (the auto-trigger surface) advertises P1
  only** (the body is updated for 20 ops) → expanded the description's algo section to the full P2–P5 scope +
  trigger words (primes/modular exponentiation/CRC-32/RLE/shortest path).
- **5 REFUTED** (rejected on verification): in each case the current code is correct and the finding misreads
  the real behaviour (the verification agent disproved it by running).
- After review: all 5 P5 ops' difftest = python exact / C bit match / c_verified=true, whole suite **4742
  passed / 0 failed** (+6 review-fix tests), my new files ruff clean, mypy new 0. The 5 work-graph nodes were
  re-gated post-fix (done).

## P6 completion record — computational geometry (2026-08-17, Opus5[1m]/ultracode, 12h autonomous, `graph-loop-engineering`)
**Added 3 geometry algorithms to the algo tier** (an extension after completing the algo-c roadmap P1→P5 = P6.
Corresponds to the initial TOC's "geometry = convex hull / segment intersection"). It is also **a bridge to
the image tier's contour/region processing**. Pack 2-D points into an input seq and, with **integer
coordinates** (each in [-100000, 100000]), make every orientation test / shoelace sum an **exact integer** (no
floating-point division at all) = C bit match, and Python == an independent oracle at tol 0.
- **op (3)**:
  - `polygon_area2` (KIND_REDUCE): the **2× signed area** of a polygon by the shoelace formula (the sign = the
    winding). oracle = a numpy-vectorized shoelace (`dot`+`roll` = a different code path). **honest domain**:
    for coordinates ≤1e5, n ≤1e5, the sum is at most 2e15 < 2^53 (measured exact on a box-circling spiral).
  - `point_in_polygon` (KIND_REDUCE): inside/outside by crossing number (ray casting). Crossings are decided by
    an integer cross product (no division). oracle = the **winding-number algorithm** (a different method from
    crossing number; the two agree on the exact inside/outside of a simple polygon). Correct on a concave
    polygon too (verified notch = outside). Discloses that **a point on the boundary (on an edge) is
    implementation-dependent** and excludes it from the holdout (crossing vs winding can diverge on the
    boundary).
  - `convex_hull` (**KIND_MAP**): a convex hull by Andrew's monotone chain. Output = the vertex list **CCW from
    the lex-min vertex** (collinear points excluded = a strict hull, agreeing with scipy). oracle = a comparison
    of the **vertex set** of `scipy.spatial.ConvexHull` (the order is separately guaranteed by the C-vs-Python
    bit match). Degenerate (fewer than 3 distinct / all collinear) is fail-soft with [] for both. **Measured 0
    mismatches vs scipy on 2000 random point sets** beforehand.
- **KIND_MAP**: convex_hull's output ≤ input length (vertices ≤ n) but follows the two-stage size-probe (upper
  bound 2n).
- **honest gate measured (all 3 ops passed=True, c_verified=true, ziglang cc)**: Python == the independent
  oracle diff 0.0 / C == Python bit match diff 0.0.
- **work-graph op wave**: the 3 geometry ops are also `algo_gate` nodes (`1 op = 1 node`) → `run-once` for
  unattended done (all 23 algo ops gated).
- **regression**: a geometry test group in `tests/test_algo.py` (known solutions, checks against multiple
  independent oracles scipy/numpy/matplotlib/winding, structural verification of convexity/CCW/point
  containment, fail-soft, degenerate, no-mutation, python exact, C bit match). Whole suite **4742 → 4765 passed
  / 0 failed** (+23), ruff clean, mypy new 0.

### P6 adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
Ran two independent adversarial review Workflows in parallel (each finding reproduced by a verification agent
via real compile/run/stress):
- **P6a (polygon_area2 / point_in_polygon, 4 lenses, 102 tool uses) = 0 findings**. geometry-correctness /
  C-safety / gate-honesty / integration-focus all zero (integer-exact, boundary disclosed, the 2^53 domain
  measured beforehand). I too measured on the worst case (a box-circling spiral n=1e5) that 2× area = 2.0e15 <
  2^53 and confirmed op==numpy==C agree.
- **P6b (convex_hull, 3 lenses, 85 tool uses) = 1 raw → 0 CONFIRMED** (1 REFUTED). The sole finding "a
  dedup-removal mutant passes difftest" was rejected on verification as **a non-defect**: dedup is
  **defensive redundancy** already guaranteed by the strict `<=0` monotone-chain pop + the `hv<3` post-check
  (removing it in either backend is equivalent = 0 divergence on a 200,000-duplicate point set). The
  verification agent independently confirmed = **the 2n size-probe is a tight non-overrun upper bound**
  (out_len=2n on a parabola input) / **ASan+UBSan clean on 1104 hostile cases** (no OOB out[] write, no long
  long cross-product overflow) / C == Python bit match, Python == scipy vertex set full match / the
  CCW-from-lex-min order is guaranteed by a test too / qsort instability has no effect thanks to the (x,y)
  total-order comparator + adjacent dedup (= `sorted(set())`). → only added an explanatory comment that dedup
  is defensive redundancy (behaviour unchanged).
- **Conclusion**: no shipped bug in the 3 P6 geometry ops. commit + push in this session (`24bc8ad`).

## P7 completion record — segment intersection (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Extended the geometry toolkit by 1 op**: `segments_intersect` (KIND_REDUCE) = whether 2 closed segments
`[x1,y1,x2,y2,x3,y3,x4,y4]` intersect (1.0/0.0). **A bridge to the image's line/contour analysis.** CLRS 33.1's
integer orientation method (proper crossing = the endpoints strictly straddle the other's line + 4 collinear
on-segment special cases). With integer coordinates [-100000,100000] the cross product is exact (|cross| ≤ 8e10
fits in long long) = C bit match. **oracle = `sympy.geometry`'s Segment intersection** (symbolic computation = a
wholly different method from orientation). Measured: 8 fixed cases correct + **0 mismatches vs sympy on 2970
random integer segment pairs** (including collinear overlap/T-junction/shared endpoint/near-miss). Degenerate
(point) segments are excluded from the holdout because sympy can't make a Segment (the op works with the general
orientation logic but is ungated = disclosed). difftest passed (python exact / C bit match / c_verified),
work-graph node unattended done (all 24 algo ops gated).

### P7 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 3-lens adversarial review (reproduced by a verification agent via real compile/run) = **1 raw → 1 CONFIRMED**
(MED, gate-honesty). **The op itself is correct** (fully agrees with sympy), but **the difftest holdout never
once drives the on-segment special cases of d1/d3/d4 (an endpoint lands inside the other segment, no shared
endpoint) as the sole reason for a 1.0 verdict**, so the gate passes a wrong op that drops that branch (not one
of the 50 holdout verdicts changes). Confirmed by self-reproduction (a d3+d4-drop mutant is passed=True,
`[0,0,10,0,3,0,3,5]`→0.0 wrong). **Fix** = added fixed holdout cases that make each on_seg branch (d1/d2/d3/d4)
the sole reason (an endpoint inside the other, 4 axis-parallel + 2 diagonal) → self-confirmed that **dropping any
branch makes difftest FAIL** (d1/d2/d3/d4 all passed=False). Added the 4 endpoint-inside cases to the
known-solution test too. Whole suite **4765 → 4772 passed / 0 failed** (+7), ruff clean, mypy new 0.

## P8 completion record — search/selection (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Added 2 search/selection algorithms to the algo tier** (moving from geometry to a different domain to even out
the tiers). Comparison-based, handling any (NaN-free) double = the result is an index or an existing element so
it's exact (tol 0), C bit match.
- **op (2)**: `binary_search` (KIND_REDUCE): the **leftmost index** (lower bound) of target in a sorted sequence
  `[target, v0..v_{n-1}]`, or -1.0 if absent. oracle = `bisect_left` + an existence check (independent). /
  `kth_smallest` (KIND_REDUCE): the k-th smallest value (0-indexed order statistic) of `[k, v0..]` by
  **quickselect** (median-of-three pivot, Lomuto). **The k-th value is order-independent** so even with a
  different pivot order, C == Python bit match. oracle = `sorted()[k]` (Timsort = a different algorithm).
  median-of-three makes sorted input O(n) too (n=40001 in <2s).
- **honest gate measured**: both ops passed=True, python exact / C bit match / c_verified. **Measured 0
  mismatches vs the oracle on 5000 random cases each** beforehand. fail-soft = binary_search on empty/absent →
  -1.0, kth_smallest on k-out-of-range/non-integer/empty → 0.0.
- **work-graph**: the 2 ops are also `algo_gate` nodes unattended done (all 26 algo ops gated). regression = a P8
  group in `tests/test_algo.py` (known solutions, bisect/sorted check, O(n²) guard, fail-soft, no-mutation,
  python exact, C bit match). ruff clean, mypy new 0.

### P8 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 2-lens adversarial review (real compile/run verification) = **1 raw → 1 CONFIRMED** (LOW, correctness).
**Correctness unchanged but a performance defect**: kth_smallest's quickselect is single-pivot Lomuto so it's
**O(n²) on large all-equal/low-cardinality input** (median-of-three doesn't protect duplicates; n=40000 all-equal
at 7.44s, sorted/reverse fast). The test didn't catch it (holdout n≤30, the timing test on sorted only). The
sibling quicksort already uses a 3-way (Dutch flag) partition. **Fix** = rewrote kth_smallest to a **3-way (Dutch
national flag) partition** (folds duplicates in the equal band → all-equal becomes O(n); comparison-only +
order-independent so **C == Python == sorted()[k] parity is preserved**). Self-confirmed = **all-equal n=40000
from 7.44s → 0.0019s** (O(n)), correctness 5000 cases mism 0, difftest bit match. Extended the timing test to
sorted/reverse/**all_equal/few_distinct** (actually guarding the regression).

## P9 completion record — statistics/aggregation (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Added 2 statistics ops to the algo tier**: `count_distinct` (the number of distinct values = an integer count)
/ `mode_value` (the mode, the smaller value wins a tie). Comparison-based (any NaN-free double), the result is a
count or an existing element so it's exact (tol 0). Both ops copy → sort → run-scan (the result is
order-independent so C's qsort and Python's sorted differing is still a bit match). oracle = `len(set())` /
`collections.Counter` (independent mechanisms). **★proactive hardening**: with a zero mode and mixed ±0.0,
C's unstable qsort and Python's stable sort can make the return value's sign diverge → a bit mismatch → **canonicalize
−0.0→+0.0 with `+ 0.0`** (other values unchanged) to make C==Python robust (the same family as rle_encode's
signed-zero disclosure). Measured: 0 oracle mismatches on 5000 random cases each, difftest passed (python exact /
C bit match / c_verified). All 28 algo ops gated. ruff clean, mypy new 0.

### P9 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 2-lens adversarial review (real compile/run/mutation verification) = **1 raw → 1 CONFIRMED** (MED, gate-safety).
**Correctness unchanged but a gate coverage gap**: the holdout can't falsify a mutant that drops mode_value's
`+0.0` canonicalization (the sole signed-zero case `[0.0,-0.0,0.0]` sorts to +0.0-last in both backends → still a
bit match even with canonicalization removed). The bit-check the comment claims as the guarantee never actually
drives the canonicalization. **Fix** = added `[0.0,-0.0]`, `[-0.0,0.0]` where `-0.0` doesn't come last in the run
to the holdout (both orders = regardless of qsort tie order, one of them must diverge). Self-confirmed = **a
canonicalization-removal mutant makes difftest FAIL**, the current (canonicalized) code passes the added cases as
a bit match. Whole suite **4787 → 4796 passed / 0 failed**.

## P10 completion record — number theory (part 2) (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Added 2 number-theory ops** (on top of P5's integer machinery, sharing the numtheory category). Carries integers
as float64 (exact <2^53); in the honest domain every modular product fits in uint64/long long = C bit match, and
Python == an independent oracle at tol 0.
- **op (2)**: `is_prime` (KIND_REDUCE): **deterministic Miller-Rabin** (witnesses {2..37}). Honest domain
  0≤n≤2^32−1 (a·a mod n fits in uint64 and the witness set is deterministic = a primality proof up to n<3.3e24).
  oracle = `sympy.isprime`. ★Correctly judges Carmichael numbers (561/1105/1729/2465…) composite. /
  `modular_inverse` (KIND_REDUCE): a^−1 mod m by the **extended Euclidean** (gcd≠1 is −1.0). Domain a≤2^53, m≤2^53
  (the Bezout coefficient is the invariant |q·s|=|old_s−new_s|≤2m, fitting in long long), m=1→0. Normalizes the C's
  truncated mod to [0,m−1] (+m) to match Python's floor mod. oracle = builtin `pow(a,−1,m)`.
- **honest gate measured**: both ops passed=True, python exact / C bit match / c_verified. **Measured is_prime vs
  sympy on 8000 random + 2000 exhaustive (including 561 Carmichael) mism 0 / modular_inverse vs pow on 8000 mism 0**
  beforehand. All 30 algo ops gated. ruff clean, mypy new 0.

### P10 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 2-lens adversarial review (real compile/run/mutation verification) = **1 raw → 1 CONFIRMED** (MED, c-safety-gate).
**The op itself is correct and overflow-safe** (verified on 353 adversarial cases), but **modular_inverse's holdout
doesn't drive the declared domain 2^53** (in-domain m stops around ~1e9), so a C `long long→int` width-narrowing
mutant (which breaks the 2^53 domain) passes the gate as a bit match. The siblings pow_mod (pins base=exp=2^53) /
gcd_seq (the 2^53 guard edge) / is_prime (near-2^32) catch the same kind of mutant, but only modular_inverse didn't.
**Fix** = added 2^53-edge cases (`[2, 2^53−1]` coprime→inverse, large coprime near 2^53, `[2^52, 2^53]` both
even→−1) to the holdout (the Bezout arithmetic drives |q·s|~2m~2^54). Self-confirmed = **the `long long→int` mutant
makes difftest FAIL**, the baseline passes as a bit match. The oracle (pow) already covered it so only the holdout
was added. Whole suite green.

## P11 completion record — bit manipulation (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Added 2 bit-manipulation ops**: `xor_reduce` (the bitwise XOR of all elements) / `popcount_total` (the total
count of 1 bits over all elements = Kernighan). Carries non-negative integers as float64; in the domain [0, 2^53−1]
every value fits in 53 bits (the XOR result is also < 2^53 = exact; popcount is a small integer) = C bit match, and
Python == an independent oracle (`functools.reduce(operator.xor)` / builtin `int.bit_count()` = a different
mechanism from Kernighan) at tol 0. Both ops passed=True, python exact / C bit match / c_verified. Measured 0 oracle
mismatches on 3000 random cases each beforehand. fail-soft = negative/non-integer/≥2^53 → 0.0. All 32 algo ops
gated. ruff clean (FURB161 changed `bin().count('1')`→`.bit_count()`), mypy new 0.

### P11 adversarial review result (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 2-lens adversarial review Workflow (correctness + gate-safety, `wf_7d130631-c0f`) = **0 findings (no defects)**.
Reviewer 1 returned `{findings:[]}`; reviewer 2 was interrupted by a window compaction mid "gate mutation testing
(break the implementation and see if the gate catches it)" (produced no result). **Following the discipline, I did
not revive the dead background but completed the same mutation test by first-hand verification**: ran 7
representative mutants for xor_reduce/popcount_total (empty init acc=1 / OR misuse / a 2^53-domain-boundary
off-by-one / negative-guard removal / Kernighan→shift [popcount≠bitlength] / a +2 error / admitting 2^53) against
the holdout → **the independent oracle catches all 7 mutants** (oracle_err > 0). **Conclusion = the P11 gate is
falsifying, no confirmed defect** (`fed093a` is sound, no follow-up commit needed).

## P12 completion record — the extended Euclidean algorithm (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Added 1 number-theory op** (on top of P5's integer machinery + P10's Bezout invariant, sharing the numtheory
category = P5+P10+P12). `extended_gcd` (**KIND_MAP**): input `[a, b]` (non-negative integers ≤ 2^53) → output
`[g, x, y]` (**exactly 3 values**, `a·x + b·y = g = gcd(a,b)`), out of domain is `[]` fail-soft. Computes the
coefficients by an iterative two-variable sweep. **The coefficients are exact** (the invariant
`|q·s| = |old_s − new_s| ≤ 2·max(a,b) ≤ 2^54` fits in the C long long) so C == Python bit match. The domain is
**[0, 2^53] inclusive** (2^53 is exact; the coefficients |x|,|y| ≲ 2^52 are also exact in float64).
- **★the point of oracle independence (the lesson of P10)**: the Bezout (x,y) is non-unique, so an **identity check
  of "`a·x+b·y==g`" can't have the gate falsify a sign/canonical-form divergence**. → the oracle **computes (g,x,y)
  with an independent recursive extended Euclidean `_ext_gcd_rec` (a different code path) and matches element by
  element**. The iterative and recursive versions return the same canonical coefficients (unrolling the recursion
  gives the iteration = mathematically identical; confirmed to agree on all ends `[0,b]`/`[a,0]`/`[0,0]`/equal).
- **honest gate measured (passed=True, c_verified=true, ziglang cc, 70 cases)**: python == the independent recursive
  oracle **diff 0.0 (exact)** / codegen **C == Python bit match diff 0.0**. Measured beforehand = **on 200,000 random
  (including 2^53-domain ends), iterative op == recursive oracle mism 0, and 0 failures of the identity
  `a·x+b·y==g==math.gcd(a,b)` (independently cross-checked in bignum)**. fail-soft = short/non-integer/negative/NaN/
  >2^53 → `[]`.
- **★gate mutation test (self-verification)**: swap x,y / negate x / drop the old_s update / widen the guard (admit
  >2^53) / wrong-length — all 5 terminal mutants **caught** (element mismatch or a structural mismatch inf). A wrong
  quotient q+1 makes the op itself loop forever (the difftest harness's timeout detects the failure) = every
  terminating wrong implementation is falsified.
- **holdout (drives the domain ends and every branch as a sole reason)**: known `[35,15]→(5,1,-2)` etc. + coprime/
  non-coprime + equal `[7,7]` + one side 0 (`[0,5]`/`[5,0]`/`[0,0]`) + a=1 + **the 2^53 domain ends** (`[2, 2^53−1]`
  coprime, large coprime near 2^53, `[2^52, 2^53]` gcd 2^52, `[2^53, 6]` inclusive upper end) + out-of-domain
  fail-soft (short/`>2^53`=`[2^53+2,3]`/non-integer/negative/NaN) + 48 random.
- **work-graph op wave**: made extended_gcd an `algo_difftest --op` gate node (`1 op = 1 node`, priority 0, tool
  capability, produces = the gate JSON) → `run-once --available tool:command` for **unattended done**
  (passed:true, c_verified, a bit-match marker generated). = **all 33 algo ops are work-graph-gated** (32→33).
- **regression**: a P12 group in `tests/test_algo.py` (known values, Bezout identity random×5000, independent
  recursive-oracle match random×5000, fail-soft, category grouping [numtheory=P5+P10+P12], difftest python exact, C
  bit match). Whole suite **4827 passed / 0 failed** (test_algo.py alone 260), all my changes ruff clean, mypy new 0
  (same count as origin/master=15 = net-new 0).

### P12 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 3-lens adversarial review Workflow (correctness / c-safety+gate-honesty / integration; each finding **reproduced
by a real compile/run mutation** by a verification agent, 5 agents, 125 tool uses) = **2 raw (same root cause) → 1
CONFIRMED** (MED, gate-cannot-falsify). **The op itself is correct** (verified on 200k + all ends, non-divergent vs
the recursive oracle, no long long overflow in-domain), but **all of difftest's out-of-domain cases are on operand
`a`** (`[2^53+2,3]`/`[2.5,7]`/`[-1,7]`), and the sole bad-`b` case `[7,NaN]` has NaN short-circuit at `bd>=0.0` and
never drives any of b's 3 guard clauses alone → **a one-sided regression of the `b`-side guard (plausible since a/b
are copy-paste symmetric) passes both gate halves** (the same gate-coverage lesson as P5/P7/P9/P10). **Confirmed by
self-reproduction**: removing `bd>=0` / `bd<=2^53` / `bd==int` from both _PY/_C → **all `passed=True` (MISSED)**, the
symmetric `a`-side removal is all `passed=False` (CAUGHT, because a's domain ends are in the holdout). **Fix** =
added `[valid_a, finite_bad_b]` cases (`[3, 2^53+2]`, `[7,-1]`, `[7,2.5]`) to the holdout and the fail-soft test →
on re-measurement the 3 b-side removals are all CAUGHT (passed=False, pydiff=inf), the baseline is a bit match pass
on 70 cases. ★**Adopted the verification agent's honest correction** (rejecting the finding's overclaim): "removing
`bd<=2^53` is C long long overflow UB at b=2^62" is **inaccurate** — at b=2^62 the C (long long) and Python (bignum)
bit-match (no overflow). The true error is **a loss of output precision** (the Bezout coefficient can't be
represented exactly in float64 above 2^53 so `a·x+b·y==g` breaks), and the `b<=2^53` bound protects this precision.
The mechanism was wrong but the defect and remedy stand = adopted.

## P13 completion record — closest pair of points (divide and conquer) (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Extended computational geometry by 1 op (the 2nd geometry installment after P6/P7)**: `closest_pair`
(KIND_REDUCE) = the **minimum squared distance** of a 2-D integer point set by **divide and conquer** (CLRS 33.4).
Input `[x0,y0,x1,y1,...]` (2n values, integer coordinates [-1e5,1e5]) → output = the minimum squared Euclidean
distance (integer-exact). **Squared distance only (no sqrt)** so it stays within long long/integer float64, C ==
Python bit match. The maximum squared distance = (2e5)²×2 = 8e10 < 2^53 = exact. fail-soft = fewer than 2 points
(n<4) / odd length / non-integer coordinates or out of [-1e5,1e5] → -1.0.
- **Algorithm**: sort by x (tie by y) → recurse on the left/right halves → d=min(dl,dr) → build a strip of points
  with (x−midx)²<d from the center line → sort the strip by y → forward-scan from each point (only while
  `(yj−yi)²<d` = the 7-neighbor upper bound). The base (m≤3) is brute force. Duplicate points (dist 0) sort adjacent
  by the same x, and the strip picks them up even across the split line. The C defines a `CpPt` struct + `cp_rec`
  recursion + `cp_cmp_x/cp_cmp_y` (qsort) inside op.c_code (codegen inserts c_code verbatim so static helpers are
  allowed). One strip buffer is shared across the recursion (the child finishes first = post-order, so no aliasing).
  The recursion depth ~log2(n) (17 for n=1e5) = stack-safe.
- **honest gate measured (passed=True, c_verified=true, ziglang cc, 58 cases)**: python == **an independent brute-force
  O(n²) oracle** (a different code path with no sort/strip) **diff 0.0 (exact)** / codegen **C == Python bit match diff
  0.0**. Measured beforehand = **0 mismatches vs brute force on 30,000 random (clusters R=3/8/30 to drive the strip
  depth) + 16,000 adversarial layouts (dense grid / horizontal-vertical lines [all points in the strip] / tiny
  clusters / boundary coordinates)**.
- **★gate mutation test (self-verification)**: skip the strip scan / sq ignores y / remove the coordinate upper limit
  / remove the lower limit / remove integrality / an empty strip — all 6 mutants **caught** (passed=False). A minimal
  cross-strip case ([-5,-5,-1,0,1,0,5,5]→4) drives the strip logic; out-of-domain cases in both coordinate slots
  drive the guards alone (reflecting P12's one-sided-guard lesson).
- **holdout**: known (a single pair 25, 3 points, duplicate dist0, a vertical column, **the minimal cross-strip**) +
  extreme in-domain coordinates (the 8e10 upper end) + out of domain made a sole reason in **both coordinate slots**
  (odd length / 1 point / non-integer x·y / over-±1e5 x·y / NaN x·y) + 40 random (clusters).
- **work-graph op wave**: made closest_pair an `algo_difftest --op` gate node (`1 op = 1 node`) → `run-once` for
  unattended done. = **all 34 algo ops are work-graph-gated** (33→34).
- **regression**: a P13 group in `tests/test_algo.py` (known values, brute-force match random×4000, fail-soft [both
  coordinate slots], category grouping [geometry=P6+P7+P13], difftest python exact, C bit match). Whole suite **4834
  passed / 0 failed** (+7), ruff clean, mypy new 0 (same count as origin/master=15). The adversarial review result =
  below (1 CONFIRMED self-reproduced and fixed).

### P13 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 3-lens adversarial review Workflow (correctness / c-safety+gate-honesty / integration; each finding **reproduced by
a real compile/run mutation** by a verification agent) = **all 3 lenses converged on the same root cause → 1
CONFIRMED** (severity = my initial rating MED / **the verification agent HIGH**, weighting a gate-honesty failure
[the gate green-lights a wrong op] heavily. As honest disclosure both are stated; the fix is identical). **The op
itself is correct** (mism 0 vs brute force on 30k+16k adversarial cases), but **the difftest holdout doesn't drive
the strip's y-scan past the immediate neighbor (j==i+1)** → the gate can't falsify a regression that **truncates the
strip forward scan to only j==i+1** (the 7-neighbor theorem is "at most 7", not "1", so a nearest pair non-adjacent
in y order can really exist). **Confirmed by self-reproduction**: a mutation truncating the scan to `range(i+1,
min(i+2, sc))` applied to both _PY/_C → `passed=True` (MISSED). Searched an integer lattice for the minimal case that
falsifies and found it (e.g. `[0,-6,-2,-2,4,-3,-5,3]` = the nearest pair is 2 apart in y order → full/brute force 20
but j==i+1-only 25). **Fix** = added 3 cases where the nearest pair is non-adjacent when y-sorted in the strip
(`[0,-6,-2,-2,4,-3,-5,3]`→20 / `[-4,5,-1,-3,0,-1,3,-3]`→5 / `[-1,-6,-1,0,-5,-4,1,-4,4,4]`→8) to the holdout and the
known-value test → on re-measurement the j==i+1-only mutation is CAUGHT (passed=False, pydiff=12), the baseline is a
bit match pass on 61 cases, and no regression in the other 5 mutations. In addition to the existing 6 mutations (strip
skip / sq ignores y / coordinate upper-lower limit / integrality / empty strip), the strip scan depth is now
falsifiable too (extending P12's gate-coverage lesson to geometry's strip scan).

## P14 completion record — the Huffman optimal prefix-code cost (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Extended data compression by 1 op (the 2nd compress installment after P5 rle_encode)**: `huffman_cost`
(KIND_REDUCE) = the **minimum total cost of the optimal prefix (Huffman) code** for symbol frequencies `[f0,f1,...]`
(non-negative integers ≤2^40) = the sum of the merge weights of all internal nodes (= Σ freq×code length). **★The
core = the optimal cost is tie-invariant** (per-symbol code lengths change with tie-breaking, but the total cost is
unique for the frequency multiset), so even if C and Python pop equal-weight elements in a different order, **the
grand total is identical = the bit match holds cleanly**. Carries integers in long long (bounded < 2^54 by the
domain guard = no overflow).
- **Algorithm = the two-queue method** (Huffman O(n log n)): sort the frequencies ascending into q1[leaves], and
  q2[merge nodes] is generated non-decreasing → take the 2 minimums from the fronts of q1/q2, add the merge sum s to
  total, append to the back of q2 (n−1 times). The C implements the same with 2 arrays + 2 front indices (qsort
  comparator hc_cmp).
- **Domain and fail-soft**: each frequency 0≤f≤2^40 (integer), else -1.0. **If the merge total exceeds 2^53, -1.0**
  (not exactly representable in float64) = **a value-critical exactness branch (falsifiable)**. Accumulates
  total_freq during the guard and returns -1.0 early if >2^53 = long long safety (each s≤total_freq≤2^53,
  total≤2^54<2^63). n=0/1 → 0.0. ★**Honest disclosure**: the upstream total_freq guard is a safety guard for the
  "extreme n (>~4M symbols) where the frequency sum itself overflows long long"; for realistic n it returns the same
  -1.0 as the merge bail = hard to falsify alone by value comparison (the same shape as P5's OOB guard disclosure).
  The merge-total bail that protects exactness is driven alone by the holdout's `[2^40]×1024` (the sum 2^50<2^53
  passes upstream; the cost ~2^53.3 hits the merge bail) = falsifiable.
- **honest gate measured (passed=True, c_verified=true, ziglang cc)**: python == **an independent heapq (min-heap)
  Huffman cost** (a different code path from the two queues) **diff 0.0 (exact)** / codegen **C == Python bit match
  diff 0.0**. Measured beforehand = **mism 0 vs heapq on 50k random (all-equal freq/0 freq/2^40-domain-end to drive
  ties)** / **mism 0 vs the brute-force optimum (true optimum) over all merge orders on 4k tiny cases** (= greedy
  achieves the optimum) / **mism 0 vs a reverse-tie-order heap on 20k** (= proving tie-invariance).
- **★gate mutation test (self-verification)**: remove the frequency upper limit / remove the negative guard / remove
  integrality / **disable the merge-total bail** (falsified by `[2^40]×1024`) / a merge that drops x2 / n==1 returns
  1.0 — all 6 value-branch mutants **caught** (passed=False).
- **work-graph op wave**: made huffman_cost an `algo_difftest --op` gate node (`1 op = 1 node`) → `run-once` for
  unattended done. = **all 35 algo ops are work-graph-gated** (34→35).
- **regression**: a P14 group in `tests/test_algo.py` (known values, heapq match random×5000, fail-soft/overflow,
  category grouping [compress=P5+P14], difftest python exact, C bit match). Whole suite **4841 passed / 0 failed**
  (+7), ruff clean, mypy new 0 (same count as origin/master=15).

### P14 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 3-lens adversarial review Workflow (correctness / c-safety+gate-honesty / integration; each finding **reproduced by
a real mutation** by a verification agent) = **3 CONFIRMED** (all gate-coverage of the overflow-bail boundary; the op
itself is correct and tie-invariance is already established on 50k+4k+20k). **0 correctness-family findings**
(tie-invariance claim, the two-queue optimality are robust). The CONFIRMED are all coverage of the "merge-total>2^53
fail-soft boundary":
- **[MED] the threshold is unpinned across ~6 decades** (a mutant that narrows the merge-total threshold 2^53 to 2^50
  etc. passes the gate) = **confirmed by self-reproduction** (the 2^53→2^50 mutant is passed=True). **Fix** = added
  `[2^40]×837` (cost 8997303650091008 ≈ 2^52.998, VALID, returned exactly) + `[2^40]×838` (cost > 2^53 → -1.0) to
  the holdout, pinning the threshold **tightly to 2^53 ±~1e13** → on re-measurement the threshold-narrowing mutants
  (2^53→2^50, →8e15) are all CAUGHT. Added 837/838 to the known-value test too.
- **[MED] cost == exactly 2^53 wasn't in the holdout so a `>`→`>=` off-by-one was uncaught → fixed by a WITNESS**:
  initially I started to disclose "for freq ≤ 2^40 the cost can't be exactly 2^53", but **the verification agent
  found a construction** = `2^16 symbols × freq 2^33` (= 2^33 ≤ 2^40) each at depth 16 gives **cost = 2^16 · 2^33 ·
  16 = exactly 2^53**. 2^53 is representable so it's VALID (returns 2^53), and the `>=` mutant wrongly drops it to
  -1.0. **After my own first-hand verification** (confirming cost==2^53 in bignum, that the op returns 2^53, that
  total_freq=2^49<2^53 passes upstream), I **adopted** this witness case into the holdout and the known-value test →
  the `>`→`>=` off-by-one is now falsifiable (pinning this single-value boundary alone). **A fine example of the
  adversarial review finding not just the gap but the fix itself** (disproving my initial "unreachable" judgment).
- **[LOW] the upstream `total_freq > 2^53` guard branch is undriven/un-falsifiable** = **honest disclosure**: this is
  a safety guard for the "extreme n (>~4M symbols) where the frequency sum itself overflows long long". For realistic
  n the merge bail returns the same -1.0 (removing it doesn't overflow long long, the result is unchanged) so it
  can't be falsified alone by value comparison (the same shape as P5's OOB guard disclosure). An extreme-n holdout is
  unrealistically slow so it's not added.
- The verification agent CONFIRMED the 3 as real defects of "the gate can't falsify a specific wrong implementation".
  **The op's correctness is unchanged** (no wrong op shipped); the gate's coverage is strengthened in #2 and #1/#3 are
  honestly disclosed.

## P15 completion record — the length of the longest increasing subsequence (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Extended search/selection by 1 op (the 2nd search installment after P8 binary_search/kth_smallest, a new DP/patience
sorting algorithm family)**: `lis_length` (KIND_REDUCE) = the **length of the longest strictly-increasing subsequence
(LIS)** of any NaN-free double sequence by **patience sorting**. Comparison-only (no arithmetic on the values) so the
length is intrinsic to the array and unique = **C == Python bit match**. tails[k] holds the minimum tail of an
increasing subsequence of length k+1, and each element replaces at the `tails[mid] < x` (bisect_left, **strict**)
position or extends the end (O(n log n)). empty→0.0, NaN present→-1.0 fail-soft (detected by `x != x`).
- **honest gate measured (passed=True, c_verified=true, ziglang cc)**: python == **an independent O(n²) DP oracle**
  (`dp[i]=1+max(dp[j]|j<i,a[j]<a[i])` = a different code path from patience sorting) **diff 0.0 (exact)** / codegen **C
  == Python bit match diff 0.0**. Measured beforehand = **mism 0 vs DP on 40k random (integer+float, small ranges to
  generate many ties = driving the strict comparison)**.
- **★gate mutation test (self-verification)**: strict `<`→`<=` (non-decreasing = a different answer) / remove the NaN
  guard / reverse the binary-search direction — all 3 mutants **caught** (passed=False). The all-equal `[2,2,2,2]`→1
  and duplicate-alternating cases drive the strict comparison alone; the NaN holdout drives the guard.
- **holdout**: known (`[3,1,2,4]`→3, `[5,4,3,2,1]`→1, all-increasing→n, empty→0, single→1) + **all-equal→1 (no
  extension for duplicates under strict)** + duplicate-alternating + -0.0/+0.0 equal + ±inf + float ties + NaN at
  **head/middle/tail** fail-soft + random (integer tie-heavy + float).
- **C safety**: tails buffer malloc(n), the write tails[lo] is no-OOB for lo≤len<n, n=0 is malloc(1)+the loop not
  running → 0.0, malloc failure is -1.0, the NaN guard is before every comparison (NaN-safe).
- **work-graph op wave**: made lis_length an `algo_difftest --op` gate node (`1 op = 1 node`) → `run-once` for
  unattended done. = **all 36 algo ops are work-graph-gated** (35→36).
- **regression**: a P15 group in `tests/test_algo.py` (known values, DP match random×5000, NaN fail-soft [3
  positions], category grouping [search=P8+P15], difftest python exact, C bit match). Whole suite **4848 passed / 0
  failed** (+7), ruff clean, mypy new 0 (same count as origin/master=15).

### P15 adversarial review result (2026-08-17, [[feedback_no_solo_ai_judgment]])
A 3-lens adversarial review Workflow (correctness / c-safety+gate-honesty / integration, mutation-verified) = **0
findings** (no findings from any lens). Verified patience sorting's strict comparison, the NaN guard, the tails buffer
safety, the independence of the O(n²) DP oracle, and that the holdout drives the strict comparison alone; no
falsifiable defect was detected. The prior mutation 3/3 caught (strict `<`→`<=`/NaN guard/binary-search direction)
and the 40k DP match show the gate is robust.

## P16 completion record — the inversion count (merge-sort method) (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Extended statistics by 1 op (the 2nd stat installment after P9 count_distinct/mode_value)**: `count_inversions`
(KIND_REDUCE) = the **inversion count** (the number of **strict** pairs with i<j and a[i] > a[j]) of any NaN-free
double sequence by a **counting merge sort** in O(n log n). Comparison-only (no arithmetic on the values) so the count
is intrinsic to the array and unique = **C == Python bit match**. On a merge, add the remaining left-side count each
time the right side is taken first (classic). The count is a non-negative integer so **-1.0 is a safe sentinel**:
NaN→-1.0 fail-soft, empty/single→0.0. Equal values are not inversions (on a tie take the left first =
`arr[i] <= arr[j]`).
- **honest gate measured (passed=True, c_verified=true, ziglang cc)**: python == **an independent O(n²) brute-force
  count** (a different code path from merge sort) **diff 0.0 (exact)** / codegen **C == Python bit match diff 0.0**.
  Measured beforehand = **mism 0 vs brute force on 40k random (integer+float, small ranges = many ties, driving the
  strict comparison)**.
- **★gate mutation test (self-verification)**: tie handling `<=`→`<` (miscounts equals as inversions) / an inv-count
  off-by-one / remove the NaN guard / no-counting (inv=0) — all 4 mutants **caught** (passed=False). The all-equal
  `[2,2,2]`→0 and duplicate cases drive the strict comparison alone.
- **holdout**: known (sorted→0, reversed→n(n-1)/2, `[2,1,3]`→1, `[3,1,2]`→2, empty/single→0) + **all-equal→0 (strict)**
  + duplicates (sorted→0, `[2,1,2,1]`→3) + -0.0/+0.0 equal (both orders) + ±inf + NaN at **head/middle/tail** fail-soft
  + random (integer tie-heavy + float).
- **C safety**: arr/tmp malloc(n), recursion depth O(log n), malloc failure is -1.0, the NaN guard is before every
  comparison. The count is long long (n(n-1)/2 < 2^63 for n < 4.3e9), the returned double is exact for n(n-1)/2 < 2^53
  (honest: it can become non-exact for extreme n, but it's exact in the holdout/practical domain).
- **work-graph op wave**: made count_inversions an `algo_difftest --op` gate node (`1 op = 1 node`) → `run-once` for
  unattended done. = **all 37 algo ops are work-graph-gated** (36→37).
- **regression**: a P16 group in `tests/test_algo.py` (known values, brute-force match random×5000, NaN fail-soft [3
  positions], category grouping [stat=P9+P16], difftest python exact, C bit match). Whole suite **4855 passed / 0
  failed** (+7), ruff clean, mypy new 0 (same count as origin/master=15). **The adversarial review runs under worktree
  isolation** (the lesson from P14 where a review agent mutated the target repo's algo.py = after commit, review in an
  isolated worktree → the result is a follow-up).

### P16 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
**★The first application of worktree-isolated review succeeded**: 3 lenses × isolated git worktree (each agent makes
its own copy from cd76da0 and mutates) → **this repo's algo.py stayed clean throughout** (the verification agent too
states "the real repo is read-only, mutation in an isolated worktree, cleaned up"). Structurally resolves P14's
contamination problem. Result = **2 CONFIRMED (both LOW), 0 correctness-family (the op is correct)**:
- **[LOW gate-coverage] the long long width is un-falsified**: the holdout's maximum inversion count is below INT_MAX
  (len ≤ 40 → max ~700), so a mutant narrowing the C accumulator from `long long`→`int` passes the gate (the shipped is
  correctly long long). **Confirmed by self-reproduction** (the int-narrowing mutant is passed=True; a strict-descending
  n=65537 has a true value 2147516416 > INT_MAX that int wraps to -2147450880). **Fix** = (1) an **independent Fenwick
  (BIT) oracle `_fenwick_inversions`** (O(n log n), a different algorithm from merge sort = can cross-check large n
  where the O(n²) brute force is too slow), (2) added a **strict-descending witness (n=65537, inversion count
  2147516416 > INT_MAX)** to the holdout+known-value test → on re-measurement the int-narrowing mutant is **CAUGHT**
  (passed=False).
- **[LOW annotation] a comment error**: `[inf,1,-inf]` was annotated `-> 2` but is actually 3 (all 3 pairs are
  inversions). The gate compares against the oracle (agrees at 3) so it doesn't pass a wrong implementation = **an
  annotation-only inaccuracy**. **Fix** = corrected the comment to `-> 3` (confirmed op/oracle/Fenwick all agree at 3).
- **★demonstration of an operational improvement**: from here on, review defaults to worktree isolation. Whole suite
  green, ruff clean, mypy new 0.

## P17 completion record — the maximum subarray sum (Kadane's method) (2026-08-17, Opus5[1m]/ultracode, 12h autonomous)
**Extended search/optimization by 1 op (the 3rd search installment after P8 binary_search/kth_smallest, P15
lis_length)**: `max_subarray` (KIND_REDUCE) = the **maximum sum of a contiguous subarray** of an integer-valued double
sequence by **Kadane's O(n) reset scan** (`cur = max(0, cur+x); best = max(best, cur)`). **Allows the empty subarray**
(sum 0) so the answer is **always ≥ 0** (all-negative→0.0) = **-1.0 is a safe sentinel**. In the integer domain (each
`|x| ≤ 2^52` and the running sum of absolute values ≤ 2^52) it keeps every partial sum an exact integer < 2^53 → the
answer is exact, **C == Python bit match**. The independent oracle (the brute-force max over all O(n²) subarrays)
agrees exactly with Kadane thanks to the **associativity of integer addition**. fail-soft -1.0 = NaN / inf /
non-integer / `|x| > 2^52` / running-sum overflow.
- **honest gate measured (passed=True, c_verified=true, ziglang cc)**: python == **an independent O(n²) brute force** (a
  different code path from Kadane) **diff 0.0 (exact)** / codegen **C == Python bit match diff 0.0**. Measured
  beforehand = **mism 0 vs brute force on 5000 random (integer, mixed sign, small ranges to drive many ties/resets)**.
- **★gate mutation test (self-verification)**: (1) the overflow guard `>`→`>=` (wrongly bails on the exact-2^52
  witness) → **CAUGHT**, (2) removing the reset `if cur<0: cur=0` (becomes a suffix sum = wrong) → **CAUGHT**, (3)
  removing the domain guard (an `int()` crash on inf) → **CAUGHT**, (4) **a true non-empty Kadane** (no empty option) →
  **CAUGHT** on the all-negative holdout `[-1,-2,-3]` (correct 0.0) (err=5.0), (5) the best update `>`→`>=` (equivalent)
  → not-caught as expected.
- **★backing up the design rationale**: a true non-empty Kadane returns the max element -1.0 on all-negative
  `[-1,-2,-3]` = **collides with the fail-soft sentinel -1.0**. The mutation test demonstrates that the design "empty
  allowed so the answer ≥ 0 → -1.0 is safe" functions precisely as this collision avoidance (empty allowed = the
  premise of the sentinel's soundness).
- **holdout**: empty/single-positive (5)/single-negative (0), **all-negative→0 (pins empty-allowed alone)**, classic
  Kadane `[-2,1,-3,4,-1,2,1,-5,4]`→6, a mid drop that resets, 0/-0.0 signed zero, **the overflow boundary pinned at
  2^52** (`[2^52]`=running sum 2^52 → **valid** (pins `>` vs `>=` alone) / `[2^52,1]`=2^52+1 → -1.0 / `[2^51,2^51]`=2^52
  → valid / single `[2^52+1]` > 2^52 → -1.0), non-integer/±inf (head/middle)/NaN (head/middle/tail) fail-soft, random
  integer.
- **C safety**: the domain check `x >= -LIM && x <= LIM` rejects NaN/inf/huge **before the (long long) cast** (NaN→int
  is UB). The accumulation is long long; the running sum ≤ 2^52 so every partial sum < 2^63 (no overflow), the returned
  double is exact for best < 2^53.
- **work-graph op wave**: made max_subarray an `algo_difftest --op` gate node (`1 op = 1 node`) → `run-once --available
  tool:command` for unattended done (gate JSON passed=True, c_verified=true). = **all 38 algo ops are work-graph-gated**
  (37→38).
- **regression**: a P17 group in `tests/test_algo.py` (registered_kind, known values, brute-force match random×5000,
  fail-soft/overflow, difftest python exact, C bit match). **honest**: on the first full run
  `test_search_ops_registered_kinds` was 1 failed (I had updated the search-category set in only one of **2 places**
  [`test_categories_grouping`]) → detected and fixed immediately, re-run **test_algo.py 295 passed / 0 failed**, ruff
  clean, mypy new 0 (same count as origin/master=15). **The adversarial review runs under worktree isolation**
  (established at P16).

### P17 hardening after adversarial review (2026-08-17, [[feedback_no_solo_ai_judgment]])
**Worktree-isolated review (4 agents, 3 lenses + an adversarial verify) = 1 CONFIRMED (LOW, gate-honesty) / 0
refuted**. The verification agent reproduced everything in an isolated worktree and states this repo's algo.py stayed
uncontaminated (`status --porcelain` shows only the auto SESSION_SUMMARY). 0 correctness/integration-family (the op is
correct):
- **[LOW gate-honesty] the C's "reject NaN before the cast" is un-falsifiable at the gate**: the honest gate only
  compiles the C with `-O2 -std=c99 -ffp-contract=off` (no UBSan). Rewriting the C's domain guard by **De Morgan**
  `if (!(x>=-LIM && x<=LIM))` → `if (x<-LIM || x>LIM)` (for NaN both comparisons are false = NaN slips through) makes
  the next line's `x != (double)(long long)x` execute the **`(long long)NaN` UB**, which under -O2 happens to land at
  something like -1.0 and bit-matches Python → the gate is passed=True. But the same mutation is a **hard-trap under a
  UBSan/ReleaseSafe build** (`panic: nan is outside the range of representable values of type 'long long'`). **The
  shipped op is correct** (the guard `!(x>=-LIM && x<=LIM)` rejects NaN before the cast) = a hole in gate coverage (not
  a production bug). The Python half is already pinned (removing the domain guard makes `int(nan)` raise ValueError →
  the gate errors, doesn't pass) = only the C side is asymmetrically unpinned.
- **first-hand verification (self-reproduction)**: a standalone probe with the same flags as the gate `-O2 -std=c99
  -ffp-contract=off`: the shipped guard = NaN→-1.0 normal / De Morgan+UBSan = `(long long)NaN` traps (matching the
  finding's panic) / the shipped guard+UBSan = no trap (rejects NaN before the cast = **UBSan-clean**). **An honest
  discrepancy**: my standalone De Morgan+-O2 exited 3, but in the **real gate** (`algo_difftest --op`) I confirmed it
  passes as the verification agent reported = -O2's UB behaviour is undefined either way, so "with -O2 alone you can't
  reliably pin reject-before-cast".
- **Fix (hardening every op)**: added a **UBSan pass** to `run_c_backend` — after the -O2 bit comparison, recompile the
  same C with `-fsanitize=undefined -fno-sanitize-recover=all` and re-run the same holdout. If a NaN/inf/out-of-domain
  value reaches the integer cast it traps → **gate fail** (a UBSan-unsupported toolchain is `"unsupported"` = neutral,
  no false positives). **Measured beforehand**: all 38 ops are UBSan-clean (0 traps) = safe to adopt with no false
  fail. **Measured after the fix**: the shipped op = passed=True/ubsan=ok, **the De Morgan mutant =
  passed=False/ubsan=trap** (bit is True under -O2 but caught under UBSan), no regression in the other ops. = **making
  "reject-before-cast" load-bearing in C too** (symmetric to Python's `int(nan)` raise). Added the regression pytest
  `test_ubsan_pass_catches_nan_slip_through_cast`. Whole suite **295→296 passed / 0 failed**, ruff clean, mypy new 0.
- **★This is not specific to max_subarray but a strengthening of the gate foundation** = from here on, every algo op
  makes "a non-finite value reaching the cast is UB" falsifiable at the gate.

## 2026-09-03: adversarial review (algo + C codegen), 8 fixes

- **[HIGH] the C `unsharp` (`sharpen`) lacks the [0,1] clip, so downstream ops diverge from Python** (unsharp→gaussian
  max diff 6.6e-2; unsharp→threshold(1.0) inverts 512 px). Clamp at the `sharpen` exit + have `codegen.py` emit
  `clamp01()` after each stage of a clip-target sort (double insurance). After the fix ≤ 3e-7.
- `difftest.py` looked only for gcc/cc/clang, so **the C gate silently skipped in this environment** (= the divergence
  above was invisible). Shared `algo_difftest.find_c_compiler()` (ziglang fallback). Records `compiler` in the result
  dict.
- graph ops' `n` was unbounded up to the int32 limit (`graph_components([2147483000,0])` allocates 17 GB) → **`n ≤
  5,000,000`** (the same explicit limit as sieve), `m ≤ 2147483000`, both Python/C.
- endpoints were `(int)`-cast before the range check (float→int overflow UB, a UBSan trap) → check the range/integrality
  on the raw double first. UBSan traps 3 → 0, 39/39 bit match.
- **a sentinel-value change (ABI)**: for ops where "0.0 is also a valid answer", changed the fail-soft sentinel from
  **0.0 → −1.0** — `is_prime` / `segments_intersect` / `edit_distance` / `point_in_polygon` / `lcs_length` (the same
  convention as P13–P18). E.g. `is_prime([4294967311])` (out of domain) is −1.0, not 0.0 "composite". Unchanged
  (possibility of collision, needs consideration): `pow_mod` / `gcd_seq` / `popcount_total` / `polygon_area2`.
- `run_algo` was rounding an int over 2^53 with `float()` before the domain check → `wire_float()` makes an integer
  input with |x|>2^53 a `ValueError` (fail-closed).
- `box` with an even k was tapping k+1 / dividing by k (gain 1.25) → k taps with the same origin as scipy
  `uniform_filter`.
- `difftest`'s NaN passed via `max(0.0, nan)=0.0` → a non-finite is a non-pass as inf.
- regression: `tests/test_imgops_c.py` (11 new) plus 35 added, 5 files 355 passed (the C tests all run with ziglang).
