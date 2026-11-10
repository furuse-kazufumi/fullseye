# Contributing to Fullseye

Feedback and contributions are welcome — the project is built to improve from user
input. The fastest routes:

- **Bug / accuracy report**: open a GitHub issue with the matching template. The
  *accuracy / honesty* template exists because "the number is subtly wrong" reports
  are the most valuable ones here — they have found real bugs (a 32× curvature scale,
  an inverted normal sign) that ratio-style tests could not see.
- **Real-hardware / real-data validation** (data may stay private; results-only is
  accepted): use the [validation report form](https://github.com/furuse-kazufumi/fullseye/issues/new?template=real_validation_report.yml), or post informally in
  [Discussions › Show and tell](https://github.com/furuse-kazufumi/fullseye/discussions/categories/show-and-tell). How reports move the maturity
  ledger: `docs/VALIDATION_CONTRIBUTING.en.md` (日本語: `docs/VALIDATION_CONTRIBUTING.md`).
- **Operator request**: name the algorithm, its public reference (paper / OSS), and
  the type contract. Fullseye reimplements from **public knowledge only**.
- **Pull request**: see below.

## Ground rules (the honesty discipline)

1. **Measured, not asserted** — any performance/coverage/accuracy claim in code,
   docs or a PR description must come from something you actually ran.
2. **Honest gates** — a new op needs: a docstring stating its contract *and its
   limits* (units, approximations, fail-soft values), a worked example asserting
   ground truth, and tests that check **signed values / absolute scales / the
   conditions under which it breaks** — not just ratios or `abs()`.
3. **Held-out is sacred** — evolutionary results are selected on train only.
4. **No fabricated citations** — real authors, real years; write `-` when there is
   no canonical reference.
5. **Fail-closed** — invalid input raises or returns the documented fail-soft value;
   never a silently wrong answer.
6. **Language policy** (see `docs/I18N.md`) — exception/CLI messages are **English**
   (optionally via `fsi18n.msg()` so users can supply translation tables); UI text
   goes through the i18n tables; comments and docstrings are **bilingual ja+en**
   in new code.

## Figures, videos and exhibits

They are judged by whether a reader gets the claim from the picture, which CI cannot
check. `docs/POC_QUALITY_CRITERIA.md` (English: `docs/POC_QUALITY_CRITERIA.en.md`) holds
the gate table, the brief skeleton and the report form; coding agents read the short
version in `AGENTS.md`.

## Adding an operator

`docs/ADDING_OPS.md` has the full walkthrough. Short version: implement + register
→ docstring with contract → worked example → tests → `py -3.11 tools/opdocs.py all`
(regenerates the per-op note + Studio help; CI enforces doc↔code drift) →
`py -3.11 -m pytest -q`.

## Versioning (what makes a release 0.1.x vs 0.2.0)

SemVer says a `0.x` project may change anything at any time. We give up that freedom
on purpose, because people install this from PyPI: **the minor slot is our breaking
signal.**

A release becomes **0.2.0** (breaking) when any of these ships:

- an operator is **removed or renamed** (adding an alias does not count);
- an existing operator's **signature, return type, units, or numeric scale** changes;
- `apply()` / `run_pipeline()` **semantics** change;
- **the default numbers change** — e.g. turning `FULLSEYE_FAST` on by default,
  unifying `_norm`, or swapping a backend whose output is not bit-identical;
- the **typed registry contract** changes (sort names, declared in/out types);
- the **Python floor** is raised, or a public root module leaves `py-modules`;
- behaviour a caller relied on flips from **fail-soft to fail-closed**.

A release stays **0.1.x** (patch) for: new operators and families, new docs, guides and
translations, new Studio features, **speed-ups that keep results bit-identical**, and
bug fixes — including fixes that make a previously broken path work.

**1.0.0** is the point where we can promise the above without a major bump, *and* the
documentation gate in `docs/I18N.md` is met (English and Chinese for `OP_CATALOG` and
the knowledge guides).

Worked example of the rule: `FULLSEYE_FAST` stays **off** by default even though it is
1.3–10× faster on ten table operators, because the cv2 twin differs internally by 5e-3
and that silently breaks the SHA-256 reproducibility pins (`docs/NEXT_SESSION.md`).
Turning it on is not a tuning change — **it is 0.2.0**.

## Cutting a release (GitHub Release, fixed format)

Pushing a tag publishes to PyPI (`.github/workflows/release.yml`). **A tag is not a
release**: until v0.1.10 this repository had eleven tags and zero GitHub Releases, so
an outside engineer could not tell *what was usable, and verified how, at a given point
in time*. Every tag now gets a Release, and it uses the same headings every time —
a release note whose shape changes from version to version cannot be compared.

Order of operations:

1. Suite green locally, then `master` green in CI. **Never tag a red tree.**
2. Bump `version` in `pyproject.toml` **and** `CITATION.cff` (`version`, `date-released`).
3. Record the release's numbers for the top-page "How it is checked" block — **measured, with the
   new version, never retyped**. `tests/test_trust_block.py` fails until all three carry the
   version from `pyproject.toml`:
   - append a row for the version to `docs/op_count_history.json` (counted as its `method` says;
     past rows are pinned and must not change);
   - re-measure the regression-test count into `docs/test_count.json` (`count`, `version`, `date`,
     `commit`): `PYTHONPATH=. python -m pytest --collect-only -q -p no:cacheprovider tests`, with
     every optional backend installed;
   - re-run the mutation probe, or confirm nothing it measures changed, and set
     `valid_for_version` in `docs/gate_inventory.json`.

   Then `py -3.11 tools/regen_all.py` and `py -3.11 tools/gen_trust_block.py --release-check`
   (the new row must equal `docs/OP_INDEX.json` tier by tier).
4. `git tag vX.Y.Z && git push origin vX.Y.Z` — this publishes to PyPI.
5. Wait for the PyPI job to succeed, then publish the Release with the sections below.

The sections, in this order (see the v0.1.10 release for a worked example):

| Section | What goes in it |
|---|---|
| Title | `Fullseye vX.Y.Z — <short capability line>` |
| Scope | Which areas this release covers (2-D, 3-D, point cloud, mesh, CT, optics, interferometry, acoustics, RAG, workbench) |
| Added / Changed / Fixed / Breaking | Four separate headings. **Breaking says "None" explicitly** when there is none — silence reads as "unknown" |
| Minimum environment | Python floor, OS, required dependencies, the full list of optional extras, whether a GPU is needed |
| Quickstart | Must **run as written** on a clean install with no data files. Run it before pasting it |
| Verification & known limitations | How the release is checked (which gates), representative measured numbers, and what is *not* covered |
| Maturity | **Copy it from `docs/MATURITY.md`** — that ledger is generated from what the repository can actually prove (which examples a gate runs, which of those are driven by real measured data). Do not retype it from memory: the v0.1.10 note claimed real-data validation that did not exist at the tag |
| Citation | Per `CITATION.cff`; state plainly if no DOI has been minted rather than writing a placeholder |
| Links | Docs site, PyPI, operator corpus, articles, changelog, known issues, Zenodo (or "not yet registered") |

Two rules that matter more than the format:

- **Numbers in a release note are measured, not remembered.** If a figure cannot be
  reproduced by running something in the repository, leave it out.
- **A citation that does not resolve is worse than none.** No placeholder DOIs.

### Zenodo (a DOI that outlives the repository)

A GitHub Release says *what was usable when*; a DOI says *this exact thing is still
retrievable in ten years, whoever owns the account*. Checked against Zenodo's and
GitHub's own documentation on 2026-09-09; re-read it before the first run, because the
GitHub integration is on Zenodo's 2026 roadmap.

**The one thing that surprises people:** if a repository has **both** `.zenodo.json` and
`CITATION.cff`, Zenodo uses **only** `.zenodo.json` and ignores `CITATION.cff` entirely
(<https://help.zenodo.org/docs/github/describe-software/zenodo-json/>). This repository
has both, so the archived record is described by `.zenodo.json` alone —
`tests/test_packaging_foundation.py` keeps the two from drifting apart, because a DOI
**cannot be edited after minting** and a stale version there is permanent.

One-time hookup (browser + account owner; it cannot be scripted):

1. Sign in at <https://zenodo.org/> with GitHub and authorise it. The repository must be
   **public** and carry a licence; for an organisation-owned repository the org owner has
   to approve Zenodo's OAuth access
   (<https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content>).
2. Profile menu → **GitHub** → **Sync now** → find `furuse-kazufumi/fullseye` → flip the
   toggle **On**. "Once connected, new releases from the repository will be automatically
   ingested and archived."
3. Confirm the licence id in `.zenodo.json` resolves. Done on 2026-09-09:
   `curl -L 'https://zenodo.org/api/licenses/?q=apache&size=50'` returns four ids, of which
   **`apache-2.0` = "Apache License 2.0"** — our spelling is correct. Worth re-checking if
   the licence ever changes: the id is Zenodo's own vocabulary, not SPDX (its documented
   example is lower-case, `"license": "mit"`), and what an *unknown* id does is undocumented
   — it may fail the release with "Extra metadata load failed" or fall back to a default.
   Note the `-L`: the API answers 301 without it.

Then, per release:

4. **Publishing the Release fires the ingest** — a bare tag does not. Zenodo archives the
   repository as of that tag and mints a *version* DOI plus a *concept* DOI that always
   resolves to the newest version. A DOI **cannot be pre-reserved** through the GitHub
   integration (only through a manual upload), so the release note cannot contain its own
   DOI — put it in on the next edit of the note.
5. If the release fails, the error text names the file: **"Extra metadata load failed."**
   is `.zenodo.json`, **"Citation metadata load failed."** is `CITATION.cff`; an *empty*
   error is a known Zenodo bug. There is no in-place fix — correct the file and cut
   another release.
6. Put the **concept** DOI in the README badge and the **version** DOI in the release
   note, add both to `CITATION.cff` (`doi:` plus an `identifiers:` entry) and re-run the
   packaging gate. Check **External resources → Archived in** on the record: Zenodo passes
   software records on to Software Heritage.

Two limits worth writing down: only releases published **after** the toggle are ingested
— v0.1.10 will not be archived retroactively unless it is uploaded by hand — and Zenodo
takes the repository *as of the tag*, so anything uncommitted at that moment is not in
the DOI.

**First run, as observed (v0.1.11, 2026-09-15).** `gh release create` fired three webhook
deliveries within 50 ms: `release/created` and `release/published` came back **409** and
`release/released` **202** — the 409s are Zenodo refusing the duplicate notifications of
the same release, not a failure, so do not redeliver them. The record existed 30 s after
the Release was published (version DOI 10.5281/zenodo.22761196, concept DOI
10.5281/zenodo.22761195). Two things to know before trusting the record: Zenodo's API and
badge endpoints answered nothing from the author's network for several minutes while the
record already existed (a plain `https://zenodo.org/api/records?q=fullseye` query timed
out; a fetch through a different route succeeded) — an API timeout is not "no DOI yet";
and the archived file is the whole repository snapshot (585 MB for v0.1.11, because
`docs/` carries the operator notes and figures), which is what the DOI points at. The
`related_identifiers` on the record are exactly the two from `.zenodo.json`; the GitHub
tag is shown on the record page but is not among them.

## Dev quickstart

```bash
git clone <repo> && cd fullseye
pip install -e ".[all,dev]"
py -3.11 -m pytest -q          # full suite (~6200 tests)
py -3.11 -m pytest -q --cov    # + coverage (what CI reports)
py -3.11 -m ruff check .       # style — match the surrounding code
py -3.11 studio.py             # the IDE
```

CI (GitHub Actions) runs on every push/PR: a **minimal numpy+scipy job** that
executes the "core runs without extras" claim, plus the full suite with coverage
on Python 3.11 / 3.12 / 3.14 (3.13 in the weekly scheduled run; 3.15 as an
allowed-to-fail preview of the core). Tags `vX.Y.Z` build from a clean checkout and publish to
PyPI automatically.

## Before you push: run the CI-equivalent checks locally (Linux / WSL2)

`tools/ci_local.py` runs, on your own Linux (WSL2 on Windows), the checks that most often turn a
push red: the `lint` job, `regen_all --check`, the gate tests, the `core-minimal` job and the
Python 3.11 full suite. It reduces round trips; **it is not a replacement for GitHub CI**, and a
local green is not a CI green (see "What it does not check").

```
py -3.11 tools/ci_local.py                 # Windows: HEAD merged with origin/master, in WSL2
python3 tools/ci_local.py                  # Linux: the same, without WSL
py -3.11 tools/ci_local.py --only core     # one stage (the summary then says "partial run")
```

**What is tested.** By default the tool fetches `origin/master` and tests the *merge* of your
commit with it — a GitHub pull request tests that merge commit, not your branch tip. The merge is
made inside a separate clone on the Linux side (`--state-dir`, default `~/fullseye-ci-local`);
nothing is written to your working tree. A conflict fails the run (merge master first).
`--no-merge` tests the tip only. If master is already an ancestor of your commit the merge is the
same tree as the tip; if your commit is an ancestor of master (or is master) the tip is tested as
it is. The summary always names both commits. Uncommitted changes are not tested (the summary
gives their count).

**Stages**, in order, each stopping the run unless `--keep-going` (times: 24-CPU WSL2, `-n 12`):

| stage | what | time |
|---|---|---|
| `lint` | `ruff check .` with the newest `ruff>=0.4`, then `tools/pip_audit_gate.py` (needs the network; `--no-pip-audit` skips it) | ~1 min |
| `regen` | `tools/regen_all.py --check` | ~9 min |
| `gates` | the files in `tools/ci_always_run.txt` if the tested tree has it, else the built-in copy (the summary says which) | ~1 min |
| `core` | the `core-minimal` job in the same order, in a venv rebuilt every run | ~2 min |
| `tests` | the whole suite with the `test` job's dependencies and environment, under pytest-xdist | ~20 min |

The first run also builds the environment (several minutes), and a full venv older than
`--refresh-hours` (24) is upgraded first.

**Things the tool refuses to call green.** No stage selected (`--only X --skip X`) is exit code 2.
With `--only`, `--skip`, `--no-pip-audit` or extra pytest arguments the title and the conclusion say
"partial run (not the full suite)" and the stages that did not run stay in the table as "not run".
A missing, broken or empty JUnit file fails its stage. Without extra pytest arguments the full
suite must execute at least 90 % of the number of entries in `.test_durations`. The Python of each
venv is read back and must be 3.11.

**One run per state directory.** The state directory is locked; a second run prints the owner
(pid, start time, commit) and exits with code 3 at once. A directory without the tool's marker
file is never cleaned. Pass `--state-dir` (a Linux path) for a second location. The environment
variables `FULLSEYE_CI_LOCAL_DIR` and `FULLSEYE_CI_LOCAL_WORKERS` are read on the side you start
the tool from and handed to the Linux side as arguments (a Windows variable does not reach WSL by
itself).

**Environment.** Nothing is inherited from your shell: fresh `HOME`, no `PYTHONPATH`, no
`FULLSEYE_*_DATA`. The tool sets what the runner and `ci.yml` set. `CI=true` is deliberate — it is
the value GitHub's runner really sets, and two examples branch on `CI == "1"`; setting `CI=1`
locally would test a branch GitHub does not take.

### What it does not check

- Python 3.12 and 3.14 (run on master), 3.13 (weekly) and the 3.15 preview. Local is 3.11 only.
- The per-shard view. CI splits the suite into 6 shards, each its own session; a gate whose answer
  depends on the session (`test_test_durations_is_fresh`) can pass in one local session and fail in
  one shard (PR #294, shard 6, 94.8 %).
- Serial order. A shard runs serially, the local run is parallel; order dependence is the nightly
  `order-shuffle` job's business. Conversely a few tests fail only under local parallelism now and
  then (known: `test_example_scripts_run[gallery2d_smoothing_rank.py]` and the planner test in
  `test_op_facets_2026_10_28`) — rerun the file before believing them.
- Tests that need tools the runner has and your machine may not: cargo, node, Chrome. The tool
  probes them at start, lists the missing ones at the top of the summary, and counts from the JUnit
  skip reasons how many tests only GitHub can confirm. `--require-tools` turns a missing tool into a
  failure. The tool installs nothing into your system (`--install-apt` is the one opt-in).
- The second, warning-only pip-audit of the CI's own tools; the coverage combine job (`--cov` only
  measures); the `docs-only` job.
- Dependency versions newer than your last venv refresh, and a master that moved after the fetch.
- Lines *added* to `ci.yml`. The dependency lists in the tool are hand copies; a test checks that
  each copy still appears in `ci.yml`, not the reverse.

BLAS threads are capped at `CPUs / workers` during the parallel run; the handful of tests that skip
because of that cap are rerun serially without it afterwards, and the summary reports how many ran.
