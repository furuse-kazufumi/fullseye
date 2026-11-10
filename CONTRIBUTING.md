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
executes the "core runs without extras" claim, plus the test suite with coverage
on Python 3.11 / 3.12 / 3.14 (3.13 in the weekly scheduled run; 3.15 as an
allowed-to-fail preview of the core). Tags `vX.Y.Z` build from a clean checkout and publish to
PyPI automatically.

### CI: which tests run where (2026-11-10)

The suite is ~26,600 tests and ~4.7 CPU-hours (`.test_durations`). Running all of it on
every PR took 1-2 hours per PR and starved the free runners, so **a PR runs only the tests
related to its change**. This narrows *where* a test runs, never *what* it asserts:
**no gate, threshold, floor or ledger is relaxed**, and everything a PR skips is run in full
on every push to `master` and every night.

| Event | What runs |
|---|---|
| PR (default) | tests selected by `tools/ci_select_tests.py` + the always-run gates (`tools/ci_always_run.txt`), py3.11, 1-6 shards sized by the selection's recorded duration |
| PR with label `ci:full` | the full suite (the label is read when a run starts: add it, then "Re-run all jobs" or push) |
| PR that touches a core file / an unmapped file / > 1,500 files, or the selector fails | the full suite (fail-safe) |
| push to `master` | the full suite on 3.11 / 3.12 / 3.14 |
| nightly (`0 18 * * *` UTC) | the full suite on 3.11 / 3.12 / 3.14 |
| weekly (Monday) | the full suite on 3.11-3.14 + order-shuffle / parallel |

How the selection works (`py -3.11 tools/ci_select_tests.py --base origin/master` shows it locally):

* **Import graph.** Every `*.py` is parsed (AST); `import`, `from … import`,
  `importlib.import_module("x")` / `__import__("x")` with a literal name, and the backend
  names `ops.py` imports by string are edges. A test depends on everything it reaches.
* **Path references.** String literals that look like paths (`ROOT / "docs" / "x.json"` and
  `os.path.join(…)` are folded, `glob` patterns are matched with `fnmatch`) count as "this file
  reads that path". A file that runs scripts (`subprocess`, `runpy`, …) and names `*.py` targets
  also depends on those scripts' import graphs. The two PoC/example runners
  (`test_poc_scripts_run.py`, `test_example_scripts_run.py`) are narrowed to the scripts whose
  dependencies changed (their session fixture runs only the selected parameters).
* **When in doubt, run everything.** Core files (`ops.py`, `backends.py`, `backend_safe.py`,
  `api.py`, `fslib.py`, `fullseye/__init__.py`, conftest, CI config, `pyproject.toml`,
  `tools/regen_all.py`, the selector itself — see `CORE_PATTERNS`), any changed file that no
  test is known to depend on, a deleted file nobody references, or an unparsable `.py` turn the
  PR into a full run. So does a change to the selection tooling itself (`tools/ci_select_tests.py`,
  `tools/ci_always_run.txt`, `tools/ci_deps_drift.py`, conftest, `.github/`): that check is done in
  the workflow, and for every other PR the rules are taken from the **base** branch's copy of the
  selector, not the PR's.
* **What counts as a reference.** In *library* modules (repo root, `fullseye/`, `examples/`) a
  directory reference with at most one literal component (`"docs"`, `ROOT / "examples"`, `*.md`) is
  ignored (otherwise every docs change would select ~93 % of the suite); file-specific references
  and directory references with two or more literal components (`data/auto_specs`, `docs/ops`)
  count. In `tests/` and `tools/` every path literal counts, but a test that walks from the repo
  root with a variable (`os.walk(ROOT)`, `ROOT.rglob(...)`, `git ls-files`) produces no path
  literal at all, so the graph cannot see what it reads: those tests are always-run (next item).
  A bare string equal to a repo-root module name (string-keyed registries such as
  `("opsfileio", "OPSFILEIO")` in `opassist.py`) counts as an import of that module.
* **Always-run gates.** Repo-wide gates that can fail on any change run on every PR regardless of
  the selection: the ones listed in `tools/ci_always_run.txt` (`test_vacuous_assertions`,
  `test_type_alias_ledger`, `test_test_durations_is_fresh`, `test_provenance_naming`,
  `test_no_invalid_escape_sequences`, …) **plus every test the selector finds walking the repo**
  (`walks_repo`: `os.walk` / `os.listdir` / `rglob` / `iterdir` / `glob("**")` whose start is not a
  literal sub-directory, and `git ls-files`). `tests/test_ci_select_tests_2026_11_10.py` checks with
  an independent probe that every such test is always-run. `regen_all --check` runs in its own job
  (`regen`, in parallel with the shards) on every run that is not docs-only: PR, push to `master`,
  nightly, weekly and manual. Until 2026-11-10 it was the last step of shard 1, so it did not run
  when that shard's tests failed and added 13-20 minutes behind them.
* **Gates first (`gates` job).** In parallel with the shards, one py3.11 job runs the tests that are
  most likely to fail, so a red result shows in minutes instead of when a shard ends (30-45 minutes).
  The list is computed, not hand-picked: `python tools/ci_select_tests.py --early-list <file>` takes
  the always-run gates plus every test file that failed on two or more branches in the recent failed
  runs (`tools/ci_failure_history.json`), orders them by the number of failed runs, and keeps what
  fits in 8 minutes of recorded time (`EARLY_BUDGET_SECONDS`; a file that does not fit is skipped and
  the next one is tried). **Nothing is removed from the shards**: every test of the `gates` job also
  runs in its shard, so the job pays for its tests twice. The two script runners are never in the
  list. `test_test_durations_is_fresh` answers a different question on a small session, so the job
  does not pass it to pytest: it collects the suite, rebuilds the session of the shard that holds the
  gate and calls the gate's own function (`--freshness-forecast`). The history is counted by hand,
  not in CI (it downloads one log per run): `python tools/ci_failure_history.py --runs 60` (read-only
  `gh`), then commit the JSON. A stale history only means a stale order.
* **How much the replay proves.** In the replay of #270-#295, six PRs had a failing CI run (seven
  runs); four of them (#270, #272, #294, #295) went full because of the core-file rule, and only
  #271 and #276 were in selected mode. #276's failure was
  an always-run gate, and #271's (a dependency released that day) is caught only by the
  dependency-version check, not by the graph. The graph itself is therefore checked mainly by
  re-running it without the core rule (it reached every failure) and by the tests above.
* **Sharding is per file.** `tests/conftest.py` splits the (selected) tests into shards by
  whole test files (LPT on `.test_durations`), so module/session fixtures are built once per run
  instead of once per shard. pytest-split is used only to record durations.

A full run that has started is never cancelled by a newer run; only PR runs cancel their
predecessor. Scheduled and manual runs each get their own concurrency group. Pushes to `master`
share one group: the running one finishes and only the newest waiting one is kept, so a burst of
merges cannot pile up 18-job runs (the kept run contains the commits of the ones it replaced).
Adding a label never starts a run -- a run whose jobs are all skipped would show as passing on
top of a real failure -- so `ci:full` is read from the API when a run starts, and an unreadable
label state means the full suite.

When `master` or the nightly run fails, the `failure-record` job keeps `ci_result.json` (failed
node ids + the commits since the previous full run that completed, so a run that was stopped
leaves no gap) for 90 days. To find the culprit: the commits listed
since the previous green run are the candidates; if there are several, bisect with
`git bisect run py -3.11 -m pytest -q <failing node id>`. (Proposal, not enabled: open an Issue
automatically from that job; it would need `issues: write`.)
