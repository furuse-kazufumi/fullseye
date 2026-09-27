---
title: 'Every Test Is Green and the Gates Still Lie — What the Gates of an Image-Measurement Library Missed, and How to Build Ones That Do Not'
tags:
  - Python
  - テスト
  - QualityAssurance
  - ImageProcessing
  - CI
public_private: true
public_id: 90e76b71095279a11b12
---

> **Language / 言語**: **English** · [日本語](https://qiita.com/furuse-kazufumi/private/35601d8f6d19e78bc16a)

# Every Test Is Green and the Gates Still Lie — What the Gates of an Image-Measurement Library Missed, and How to Build Ones That Do Not

<!--
  How to extend (add to ja and en in the same order):
    1. A new incident goes into the section of one of the four patterns; if it fits none, open a new pattern.
    2. Numbers come from commits and run logs, never from memory.
    3. "Caught this round" grows by dated sections; existing sections do not move.
    4. Post with fullsense tools/qiita_public_post.py (idempotency key = public_id).
-->

I am growing **Fullseye**, a personal library of about 2,200 image-processing and measurement functions ("ops"). Here I call every check that decides whether an op's result may pass a **gate**: pytest tests, checks that generated files are up to date, CI jobs — all of them exist to stop what should not pass.

The gates run about 15,000 test cases over more than 7,000 test functions, and they are all green. Even so, **the gates were green while the results were false** more than once. This article sorts those lies into four patterns and gives, for each, real incidents and how the gate was rebuilt. None of the patterns is specific to Fullseye; anyone who writes tests steps on them.

## The conclusion first

| Pattern | What happens | How to rebuild |
|---|---|---|
| The gate exists but does not run where the accident happens | Green on the development checkout, red in the distribution or on Linux | Count where the accident happens (wheel, Linux, CI) |
| Green, but the content is empty | Empty output, an empty list or a discarded verdict counts as "agreement" | Count the amount of content separately; break the gate on purpose and watch it fire |
| Ran on everything, covered nothing | One input or one parameter set feels like "we looked at all of it" | Add structurally different inputs; when the exemption list is long, suspect the gate first |
| It only agrees with its own spec | The answer key is the formula you wrote yourself | Bring in independent ground truth: published values, a second implementation, invariance under a transformation |

## Terms

- **Gate** — a check that passes or stops a result: a test function, a diff check on generated files, a CI job.
- **Ground truth** — a value known to be correct that a gate compares with: a closed form from a theorem, a worked example printed in a standard, the output of a second implementation written in another language.
- **Fail-closed** — on a failed check, refuse loudly instead of passing; never silently repair what cannot be repaired.
- **Drift** — generated files (indexes, help pages, translations) disagreeing with their source.
- **Probe** — the test input used to call every op at once.

## Pattern 1: the gate exists but does not run where the accident happens

**26 % of the ops were missing from the wheel.** When rebuilding the distribution wheel, a module was left out of `py-modules` in `pyproject.toml`, and 224 ops were gone in an environment that installed the wheel. A gate checking "zero backends failed to load" **existed** — but it only ran on the development checkout, where every file is present, so in principle it could never reproduce this accident.

The fix was a CI job that actually builds the wheel, installs it into a separate virtual environment and compares the op set against the checkout. Later, the same mistake (`backends_texture` left out) turned that job red at once, and the fix was one line.

Three more incidents of the same pattern:

- **Generated files hitting `.gitignore`**: a ledger category named `build` matched `build/` in `.gitignore`, so three notes were never committed. Everything was green locally; CI alone had 10 failures. The "file exists" gate never asked whether git tracked the file. → A gate that generated paths never match an ignore rule.
- **Directory walk order**: `highpass.md` existed for both 2-D and 1-D ops; Windows found the 2-D one first and Linux the 1-D one, so a gate failed only in CI. `os.walk` order depends on the file system, and the same lookup had been copied into four gates and one tool.
- **Exit 0 with nothing run**: when an assert fails while a test module is being imported, pytest stops the whole session. A 37-minute suite finished in 21 seconds with exit code 0.

**Lesson**: after writing a gate, check that it runs where the accident happens. Green on the development machine is not evidence of a fix.

## Pattern 2: green, but the content is empty

**Empty output agrees with everything.** The drift gate (regenerate everything and check the working tree does not change) stays green even if a generator **stops producing anything**. It actually let through an index claiming "0 op notes" in six languages and help pages with 0 images and 60 pages of raw Markdown. → A separate gate counts the amount of content (notes with examples, body length, zero empty cells).

Three more:

- **A verdict computed and then discarded**: the gate that runs the PoC scripts correctly detected "exit 0 but no PASS printed" — then did not return it, and the following `assert code == 0` always passed, so three PoCs without a single assert went unnoticed.
- **Vacuous asserts**: `assert all(x for x in xs)` and `for x in xs: assert ...` pass unconditionally when `xs` is empty. After three rounds of tightening, 126 remained (in 84 files); the count is now pinned in a ledger and **turns red if it grows** — a ratchet that only moves down.
- **Identical figures**: of 318 exhibit figures, 317 had distinct content. The GIFs for two opposite claims, "rational" and "irrational", were byte-identical (the projection made the rotation component exactly zero).

**Lesson**: a gate needs a gate that checks it does not pass emptiness. The surest way is to **break the gate on purpose and watch it turn red**. In Fullseye, gates come with tests such as "the gate really sees every PoC" and "the public-name gate is not empty".

## Pattern 3: ran on everything, covered nothing

**One probe is not coverage.** The gate that calls every op with a probe stood in the right place. Still, the threshold op `xsitk_huang_thresh` succeeded 4 of 4 times on a sin/cos stripe probe and **failed 4 of 4 times** (all-zero output) on gradient, circle and checkerboard probes. With three structurally different probes, the ledger of ops exempted as "degenerate input" shrank **from 27 to 12**. Most exemptions were not properties of the ops but the blind spot of a single probe.

Parameters do the same. 168 ops declared that splitting the image into tiles does not change the result, and the gate checked them with one setting, `tile=64, halo=16`. With other settings **18** of them broke.

The most painful one: a differential fuzzer reported 0 findings over 60,000 cases. It compared how many objects were found but never observed their order. A deliberate mutation that reversed the order survived 3,000 cases; adding one line of observation killed it at the second case. **Zero findings was not robustness; it was a sign of not looking.**

**Lesson**: "ran on all of them" is not "covered all of them". When an exemption list is long, suspect the probe and the observation before the op. Trust a fuzzer's zero only after it has killed a planted mutation.

## Pattern 4: it only agrees with its own spec

**52 synthetic gates stayed green; the standard's worked example found 5 defects.** Nine ops for measurement system analysis (gauge R&R) and measurement uncertainty (GUM) were checked by 52 gates on synthetic data, all green. Adding the worked examples printed in the standards as ground truth exposed five defects: no path for pooling the interaction term (EV off by 7.3 %), a missing truncation of the effective degrees of freedom (coverage factor 2.1132 against the standard's 2.12), and so on. **All five were of the kind "the spec never mentions it"**, which synthetic data built from one's own spec can never find.

**A second implementation finds what single-implementation tests cannot.** When the image-processing C ABI was rewritten in Rust, the first 8 cases all agreed — read as "the probe is weak", not "passed". Nine cases aimed at the places where the spec is silent showed that the connected-components op was 4-connected on the numpy path and 8-connected on the OpenCV path: **32 components versus 1** on an 8×8 checkerboard. Each path passed its own tests.

**Invariance under a transformation is a gate even without ground truth.** A point-cloud descriptor claimed to be rotation-invariant flipped sign at 42.4 % of points after a 90-degree rotation, because its helper chose normal signs arbitrarily. A gate per claim — "unchanged under 12 random rotations" — exposes the lie without knowing a single true value.

**Lesson**: do not grade with the formula you wrote. Bring ground truth from outside: published values, a second implementation in another language, invariance and scale laws (scale by k and the feature changes by k^p).

## Caught this round (2026-09-27)

On the day of writing I added ops and PoCs that measure the *C. elegans* connectome (the wiring diagram of a worm's nervous system). Here is what the gates caught that day, next to the patterns.

- **The rotation gate caught a boundary of one ulp (a pattern-4 gate closing a pattern-3 hole).** Sholl analysis of a neuron tree (grow concentric spheres from the centre and count the branches crossing each) should not move a single integer under rotation in 3-D. The test turned red: the default outer radius was exactly the distance to the farthest node, so that node sat on the shell, and a rotation moving a float by one ulp flipped "inside/outside" and dropped a crossing from 1 to 0. The default shells now sit at the mid-points of the intervals.
- **A translation was silently not read (pattern 2).** I added a Japanese summary for an op whose docstring is English. The fingerprint matched, yet no Japanese help page was generated: the entry sat at the top level instead of under the required key, so the reader never found it. Regeneration exited 0 and said nothing.
- **A 9-point gap to a paper, split completely by matching a classification table one connection at a time (pattern 4).** For 8 genetically identical worms, "connections present in at least 7 worms" were 34 % of the adult's connections, against about 43 % in the paper. Instead of fitting, I matched against the authors' published per-connection table. The paper labels every connection of a left/right pair stable once the pooled pair connection is present in at least 7 worms; that rule alone reproduces 789 of the paper's 792 stable connections. Neither count is wrong; they differ in what counts as one connection.
- **A zigzag in a figure was rounding.** A histogram of the rounded mean synapse count of two animals went up and down between odd and even bins. numpy's `round` rounds half to even (2.5 → 2), so half-integers pile into even bins — dangerously easy to read as a biological periodicity. Counting the integer sum removed it.
- **I nearly used an author's field as ground truth (pattern 4).** For the neuron skeletons of the 8 worms, I started a gate comparing the op's cable length with the "length" field the authors wrote into the file — and 1,360 of 1,586 disagreed. That field is not the sum of segment lengths (median 0.89 of it); it was computed upstream with a definition that cannot be checked. I switched to the per-node "distance from the root" field instead; it also lists nodes without coordinates, and comparing only nodes with coordinates, all 1,586 matched to a relative 1.75e-9. **Ground truth brought in from outside is not ground truth until its definition is checked.**
- **The second implementation had its names swapped (pattern 4).** Checking the segmentation score (CREMI's adapted Rand error) against scikit-image, the error agreed but precision and recall came out swapped. scikit-image's code divides its precision by the truth pairs, the opposite of its docstring ("divided by the number in the test image"). The F-score is symmetric, so the error itself is right; only separate precision and recall disagree. **A second implementation exposes the other side's defects too.**
- **One preprocessing step flipped the conclusion (pattern 2).** Scoring a neuron segmentation from electron microscopy by VOI split (over-splitting) and merge (over-merging), every threshold first looked over-merged. The cause was leaving membrane pixels as background (label 0): the whole background counted as one huge region and inflated merge 2.4-fold. Assigning membrane pixels to the nearest cell, the segmentation crosses cleanly from over-split to over-merged between the 65th and 70th percentiles.

## Kinds of gates (the ones Fullseye uses)

| Kind | Ground truth | Example tests |
|---|---|---|
| Closed form / identity | theorems, analytic solutions | sum of degrees = number of edges / mean curvature of a minimal surface = 0 |
| Second implementation | another language, another backend, brute force | Rust agrees with Python / brute-force 3-cycles / generated C is bit-identical |
| Published values | worked examples and figures in standards | gauge R&R worked example / the 59 GenICam pixel formats |
| Fail-closed | refuse out-of-contract input | unknown type names, non-positive σ, never return identity when alignment fails |
| Invariance / scale law | unchanged under a transformation, or changed by a declared exponent | invariant under 12 rotations / scale by k gives k^p |
| Controls (nulls) | chance with the degrees kept | every null sample keeps the degree sequence exactly |
| Degenerate / uniform input | empty, constant, one pixel | a uniform image never becomes a full-frame detection |
| Probes | call every op with structurally different inputs | zero fallbacks / every knob has an effect |
| Drift | regenerate everything, the tree does not change | `regen_all --check` |
| Counting registration surfaces | numbers counted from the real thing | counts in the README, the index, `__all__` |
| Counting from the distribution | the wheel, `py-modules` | functions without a public path do not grow |
| Translation fingerprints | fingerprint of the source text | a stale translation is detected when the source changes |
| Running the deliverables | exit 0 and PASS in a separate process | more than 150 PoCs, code samples in the docs |
| Environment / git | tracked, no local paths, order | never matched by ignore / no private paths in published files |
| Gates of gates | the gate itself fires | does not pass emptiness / turns red when broken / ledger of vacuous asserts |

Scale is given for reference, not as a headline: 420 test files, 7,192 test functions, about 15,000 cases, and about 35 minutes for the full suite. CI runs Python 3.10 / 3.11 / 3.12 × 4 shards = 12 jobs, plus a job that actually builds and counts the wheel, the drift check, and a weekly order shuffle; a release can only be cut from a commit whose CI is green.

## Steps when adding a gate

1. Decide **where the ground truth comes from** first. Never grade with your own formula.
2. Check that it **runs where the accident happens** (distribution, Linux, CI).
3. **Break the gate and watch it turn red.** A gate that cannot turn red is not a gate.
4. Separately count that it **does not pass emptiness** (amount of output, number of items seen).
5. **Never a single input or parameter set.** At least two structurally different inputs.
6. Write exemptions into a **ledger with reasons**, as a ratchet that only moves down.
7. **Keep the detail, not only the verdict.** Write the full output of long checks to a file; a bare verdict makes you pay for the same run again.

## Limits

- More gates take more time. 80 % of the full suite's time was spent in the top 80 stages (such as the gate that runs every PoC in a separate process). Measure before speeding up.
- Gates only stop lies they know about. Many incidents here passed gates that already existed. A new kind of lie passes until another gate is added.
- Published values exist only where standards or papers exist. Elsewhere, second implementations and invariances carry the load.

## About the author

I set the questions and the direction; implementation, new gates and adversarial review went to Claude Code. Many of the incidents here are records of that review.
