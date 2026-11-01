<!-- i18n-source-sha: f60f75509ee5 -->
# Quality criteria for PoCs, figures, videos and exhibits (for whoever asks and whoever builds)

A Fullseye PoC (`examples/poc_*.py`) or an exhibit figure/video passes on two counts: **it runs and prints PASS**, and **a reader gets the claim from the picture**.
This document turns the second count into checkable gates. Use it when you write the PoC yourself and when you delegate it to a coding agent (Codex, Claude, Copilot, ...).

Languages: [日本語](POC_QUALITY_CRITERIA.md) / English (this file).

## Before and after

CI gates (type checks, ledger agreement, regeneration drift) act **after** the fact: they reject what was built. This document acts **before**: it decides what gets built.
If the five points below are settled before work starts, there is no room left for a cheap deliverable to reach the gates.

1. **The claim in one line** ("cutting the fit window to 4 s shrinks the depth error of shallow defects to a few ten percent"). No claim, no deliverable.
2. **Where the ground truth comes from** (closed form, published value, second implementation, measurement). Without truth it is a picture, not a PoC.
3. **How the failing side is shown** (noise, window, angle, subsampling). Success alone carries no claim.
4. **What goes on the screen** (operator input → output → truth, number cards, limit lines) in pixel coordinates.
5. **Who builds which part** (see "Who does what"). Parts decided by judgement are written by the requester.

## Why

A coding agent passes the gates written in the brief with the least effort. Quality that is not written down does not appear.
"Make it look nice", "clear", "realistic" are not gates. Counts, language, function names, coordinates, lower bounds and the origin of every number are.
Example: for the same subject, a brief without gates returned "a box-shaped car on an endless grid of roads for five minutes"; a brief with a point list for the body, zero interpenetration and the list of evaluation items returned a video that shows the eight driving-school tasks.

## Template A — the quality gates to paste at the end of a brief

Every row must be answerable by a measurement or an `assert`. A row you cannot fill means the spec is not finished.

| Aspect | Gate (example; adapt to the subject) | How it is judged |
|---|---|---|
| What is shown | The subject is on screen (a car if it is about cars, a defect if about defects). **Operator input → output → ground truth** share one screen | Inspect the first, middle and last frame by name |
| The failing side | Limits and failure conditions (more noise, a different window, other angles) are shown too; success-only figures carry no claim | At least one frame under a failure condition |
| Shape | Built to a dimension table or a coordinate point list; boxes, spheres and sticks as stand-ins fail | Three-view with the spec points overlaid; maximum deviation [m] |
| Physics | Zero interpenetration, ground contact, time order, conservation laws (whichever apply) | Numeric gates on every frame (`gates.json`) |
| Numbers | Numbers on screen and in captions come from **the same run**; if a ledger (`figures.json`, `exhibits.json`) holds the same quantity they must agree | `assert`; stop on mismatch |
| Scale | Pseudo-colour uses fixed `vmin`/`vmax`; per-frame normalisation is forbidden (it destroys the claim) | Implementation note plus two frames compared |
| Resolution | Width×height, fps and frame count as numbers; no nearest-neighbour enlargement of data (integer-factor insets labelled "×N" are allowed) | Measured |
| Text | Language (ja / en), minimum size (22 px at 1080p), zero overflow, never on top of data (bands or margins) | Measure text width before drawing |
| Styling | Figures go through the `examplefig` helpers (plain default matplotlib fails) | Report the function names |
| Determinism | Render twice, SHA-256 identical | Measured |
| Samples | Lower bounds on points, images, tasks (no "losing" by subsampling) | Measured |
| Regeneration | All generated files rebuilt with `py -3.11 tools/regen_all.py`; `--check` green | Measured |
| Inspection output | First / middle / last frames and a contact sheet written outside the repo | Report the location |
| Time gates | Seconds come from the **measured distribution** (longest local run × a 2–3× margin for shared runners). Several time gates (test timeout, hang-detection dump, per-PoC limit) must be **ordered from short to long**. "Slow" and "stuck" are not judged by the same gate | Table of each gate's value and its reason |

A time gate changes meaning with its value: too short and correct work fails on a busy day, too long and a hang goes unnoticed. The existing order is per-PoC limit → PoC batch timeout (5400 s) → hang-detection dump (6000 s). When you change one, look at its neighbours.

## Template B — acceptance by the person who asked

1. Open the frames at **full resolution** before reading the numbers. Downscaled contact sheets hide defects (a box-shaped car was missed that way).
2. Can you tell in one second that the subject looks like the subject?
3. Does every gate row carry a **measured value**? A row that only says "passed" is not accepted.
4. Is the before/after direction right (the slower or worse variant must not be the one adopted)?
5. For a ten-second pilot, show it to the requester before producing the full piece.
6. Look at the list of added files, not only the screen and the numbers.

## Template C — skeleton of a brief

```
# Brief: <subject> — <one-line claim>
Location: <worktree>; write only here. Read-only: <references>.
## Structure (<duration, resolution, fps, frames>)
<what is shown when; camera; panel layout in px>
## Fullseye's work (shown on screen)
<op name → input → output → ground truth, and where it is overlaid>
## Do not change
<existing figures, captions, numbers, gates>
## Gates (as a table in README)
<Template A filled for this subject>
## Outputs (for inspection)
<file names, where the frames go>
## Report
<for each gate: which frame proves it; tables of numbers; render time>
```

## Template D — the builder's procedure (from start to report)

1. Read the brief and first write Template A into the README **with the values for this subject** (leave a row "undecided" in the report rather than guessing).
2. Do not touch existing figures, captions, numbers or ledgers; only add.
3. Produce a ten-second (or one-frame) pilot first and write its first/middle/last frames outside the repo.
4. Produce the full piece and fill every gate row with a measured value. If an `assert` stops you, fix the cause or report the stop; never loosen the gate.
5. `py -3.11 tools/regen_all.py` → `--check` → the relevant tests; paste the results into the report.
6. Report in the order of Template E.

## Template E — the report (in the order the requester inspects)

```
## What was fixed or added (per numbered item in the brief, with the frame that proves it)
## Gate table (each Template A row: gate | measured value | verdict | evidence file)
## Numbers on screen vs ledgers (quantity | value from the run | ledger value | match)
## Where the inspection frames are (absolute paths)
## Render time, frame count, resolution (measured)
## Open points and anything not filled in by guessing
## Commit list (nothing pushed)
```

## Trusting sources and stopping a verification

Papers, standards and official documents are where ground truth comes from, but they are **not trusted wholesale**: typos, unit mix-ups and numbers nobody can reproduce are common.
The opposite failure is a verification that never ends because a source refuses to agree. These rules stop it.

| Situation | Rule |
|---|---|
| Choosing a source | Prefer sources with public data or code, and values that several independent sources agree on. A number with a single source is labelled "single source" |
| Strength of evidence | Always tag: verified (checked in the primary text) / secondary (textbook, review, official document) / practitioner (rule of thumb, own experiment) |
| Reproducing | Reproduce only the number the claim needs, never the whole paper |
| Stop rule | After **three** attempts on the same number (or the time budget written in the brief), stop; record "not reproduced: source X, ours Y, conditions tried" and move on with your own synthetic truth |
| Too good | If you match the source to the last digit, first suspect that both sides got the same input or that the source's value was copied into the code |
| A dubious source | Units do not add up, figure and table disagree, an order of magnitude off from others: drop it from the evidence and write down why; never keep using it silently |

A stopped verification is a record, not a failure. Keep it in `KNOWN_ISSUES.md` or in the PoC findings as "not reproduced" and return to it when another source appears.

## Who does what

| Decided by judgement (the requester writes it) | Volume and plumbing (delegate it) |
|---|---|
| Storyboard (what is shown, which op's input/output/truth) | Rendering pipeline |
| Layout, camera path, amount of text | Data acquisition and preprocessing |
| Figure composition and styling, first line of the caption | Operator implementation and tests |
| Evaluation design (ground truth, ablations, sample lower bounds) | Ledgers, regeneration, merging master, fixing red CI |
| Checking the physics | |

## See also

- `CONTRIBUTING.md` (the honesty discipline: measured, not asserted)
- `docs/ADDING_OPS.md`, `docs/VALIDATION_CONTRIBUTING.en.md`
- `tools/regen_all.py` (the single entry point for generated files)
