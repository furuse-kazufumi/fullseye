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
  the next one is tried). "Gates first" is therefore not "every gate first": the order is by failed
  runs, so an always-run gate that does not fit the budget is left to its shard (the job's log and
  summary name each one with the reason; on 2026-11-10 three of the ten were left out). **Nothing is removed from the shards**: every test of the `gates` job also
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
merges cannot pile up 18-job runs. The kept run takes over the commits of the ones it replaced
because a push run does not look at its own push alone: both the documentation-only check and the
failure record take their commit range from the last run whose tests really ran (the run that
uploaded `ci-result-<sha>`), so a documentation-only push that replaces a waiting code push still
runs the full suite. If no such run can be found, the run is a full one. The failure record also
keeps the results of the `regen` and `gates` jobs (`regen_result`, `gates_result`).
Adding a label never starts a run -- a run whose jobs are all skipped would show as passing on
top of a real failure -- so `ci:full` is read from the API when a run starts, and an unreadable
label state means the full suite.

When `master` or the nightly run fails, the `failure-record` job keeps `ci_result.json` (failed
node ids + the commits since the previous full run that completed, so a run that was stopped
leaves no gap) for 90 days. To find the culprit: the commits listed
since the previous green run are the candidates; if there are several, bisect with
`git bisect run py -3.11 -m pytest -q <failing node id>`. (Proposal, not enabled: open an Issue
automatically from that job; it would need `issues: write`.)

## Before you push: run the CI-equivalent checks locally (Linux / WSL2)

`tools/ci_local.py` runs, on your own Linux (WSL2 on Windows), the checks that most often turn a
push red: the `lint` job, `regen_all --check`, the gate tests, the `core-minimal` job and the
Python 3.11 full suite. It reduces round trips; **it is not a replacement for GitHub CI**, and a
local green is not a CI green (see "What it does not check").

```
py -3.11 tools/ci_local.py                 # Windows: HEAD merged with origin/master, in WSL2
python3 tools/ci_local.py                  # Linux: the same, without WSL
py -3.11 tools/ci_local.py --only core     # one stage (the summary then says "partial run")
py -3.11 tools/ci_local.py --accept-skips "added 60 tests that skip without the dataset"
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
| `regen` | `tools/regen_all.py --check` | ~11 min |
| `gates` | the files in `tools/ci_always_run.txt` if the tested tree has it, else the built-in copy (the summary says which) | ~1 min |
| `core` | the `core-minimal` job in the same order, in a venv rebuilt every run | ~2 min |
| `tests` | the whole suite with the `test` job's dependencies and environment, under pytest-xdist | ~20 min |

The first run also builds the environment (several minutes), and a full venv older than
`--refresh-hours` (24) is upgraded first.

**Things the tool refuses to call green.** No stage selected (`--only X --skip X`) is exit code 2.
With `--only`, `--skip`, `--no-pip-audit` or extra pytest arguments the title and the conclusion say
"partial run (not the full suite)" and the stages that did not run stay in the table as "not run".
A missing, broken or empty JUnit file fails its stage. Without extra pytest arguments the full
suite must execute at least 95 % of the number of entries in `.test_durations` (skipped tests do
not count as executed). The Python of each venv is read back and must be 3.11, unless you pass
both `--python` and `--allow-other-python`.

`--no-merge`, `--no-fetch`, a `--base` that is not `<remote>/<branch>` (so nothing is fetched) and
`--allow-other-python` make the tested tree or the interpreter differ from what GitHub tests. The
title and the conclusion then say "different conditions from GitHub's CI" instead of "all stages
ok", name the difference, and say that the result is not evidence that GitHub's CI passes.

A run in which a tool the runner has is missing on your machine (cargo, node, Chrome or one of the
apt packages) is not called a full green either, even when all five stages pass: the conclusion
reads "all stages ok — but N tests can only be confirmed on GitHub, because tools are missing here"
and the verdict is `ok_missing_tools`. `--require-tools` instead fails such a run at the start
(exit 1, verdict `failed`); pass it when you want either `full_ok` or a failure.

**Exit code and verdict.** 0 means "everything that ran passed"; 1 a failure, 2 a usage error, 3 a
busy state directory, 130 an interrupt (Ctrl-C). A partial run, a run under different conditions and a run with missing tools
also exit 0 — the exit code keeps that meaning so that `--only lint` or an offline `--no-fetch` run
is not mistaken for a failure. What the 0 means is in `verdict` in `result.json` (`full_ok`,
`ok_missing_tools`, `partial_ok`, `deviating_ok`, `failed` or `busy`), and the tool prints it as its
last line, e.g. `verdict: deviating_ok — GitHub と違う条件。緑の証拠にしない`. **If you chain the tool
into `&& git push`, check the verdict in `result.json`, not just the exit code** — `ci_local && git
push` pushes after a partial or a different-conditions run too. Only `full_ok` says "every stage,
under GitHub's conditions". The last line is a verdict line even when the tool stops before the
Linux side runs: a usage error — an unknown option, an option without its value, a value that is
not one of the choices, or an argument the tool rejects — ends with `verdict: usage — …` (exit 2),
and a missing `wsl.exe`, an exception or Ctrl-C with `verdict: failed — …` (the traceback, if any,
comes before it). These two
words exist only on the last line; `result.json` keeps its six verdicts. A skip notice (see below)
is appended to the last line after the verdict, e.g. `verdict: full_ok — …。skip が基準より +21 件…`;
the `verdict: <word> — ` prefix itself never changes.

**Skips.** The state directory keeps a skip record (`skip_baseline.json`), written only by runs
whose verdict is `full_ok` or `ok_missing_tools` — every stage passed, no extra pytest arguments,
GitHub's conditions, the BLAS rerun included. Failed, partial and different-conditions runs are
compared but never recorded. What is compared is the total skip count. Only when the set of
missing tools (cargo, node, Chrome) differs between the baseline and this run are the skips of the
tools that differ taken out — from the baseline the skips of tools missing only there, from this
run the skips of tools missing only here (estimated from the reason text) — so a run with cargo and
a run without it share one baseline. A run with the same tools is judged exactly as before: nothing
is taken out, so every skip counts. When the tools differ, what is taken out per tool is the number
of skips whose reason names the tool on the side without it minus the number on the side with it
(never below zero), so reasons both sides share are not taken out; a tool's name is matched only as
a whole word, so a name that merely continues it (`node2vec`, `chrome-trace`, `rust_ext`) is not
taken for the tool. A reason that names the tool as a word (`Rust 拡張`) cannot be told apart from a
real tool skip and is taken out while that tool differs. The line is taken
from the compared baseline count. A record without skip reasons cannot have tool skips taken out;
it is then compared by its total, and the summary says so. Skips that depend on apt packages cannot
be told from their reason text and are not subtracted; when the missing apt packages (or tools)
differ from the baseline, the summary says so, also on the line that reports a jump. The baseline is the smallest such count recorded so far: it
only moves down, so a series of small increases cannot raise it step by step — they are caught once
their sum crosses the line. A run whose missing tools are the same as the baseline's can lower it,
and so can a run that only has more tools installed (its missing tools are a strict subset of the
baseline's): nothing is taken out of such a run's count, so when its compared count is below the
baseline's, its total count and its set of missing tools become the baseline, and the summary says
the tools were installed. A run missing a tool the baseline had leaves the baseline where it was (its
compared count is an estimate, and taking it in would hide a breakage from every later run with
those tools); the summary says so and says how to make that run the baseline (`--accept-skips`). When a run skips more than the baseline by over 10 % (and by over 20
tests) the summary says so near the top, lists the skip reasons that grew and names the record's
location, and the last line gets a short notice; the baseline is left as it was. This is a notice,
not a failure — the 95 % floor is the failure. A record written by the first version of the tool
(no `format` field; it may come from a failed run) is read as the baseline and moved to the new
form by the next recording run, by the same smallest-count rule. A record that cannot be read
(empty, with a BOM, not JSON, another format version, or fields of the wrong type) is not compared
and not overwritten; the summary says why and where the file is, and the run is not failed for it.
If an increase is legitimate, run again with `--accept-skips "<reason>"` (the reason is required):
if that run's verdict is one that may record and it jumped, found the record unreadable, or has
other missing tools than the baseline, its count becomes the new baseline, and the record keeps a history entry (previous and new
baseline, the compared counts, reason, commit, time). A run that did not jump and has the baseline's missing tools has nothing to accept:
it says so, and the baseline follows the usual rule (it can only move down). A failed, partial or
different-conditions run does not accept, and says so. A run whose summary cannot be made is a
failed run too: whatever it had already written to the record (including an accepted baseline) is
put back. An unreadable record is kept under another
name (`skip_baseline.json.unreadable-<time>`) before it is replaced; if the new record then cannot be
written, the kept record is moved back, and the summary and the last line say that the record could
not be written. Accepting a run whose missing tools differ from the baseline's makes that run's total
count and its set of missing tools the new baseline (nothing taken out), and the summary says so. `--accept-skips` does not
change what is checked, so it does not change the verdict; the summary always says that the
baseline was accepted. The record is written to a temporary file and renamed into place, so an
interrupted write leaves the previous record.

**One run per state directory.** The state directory is locked; a second run prints the owner
(pid, start time, commit) and exits with code 3 at once. A directory without the tool's marker
file is not cleaned, with one exception: a directory made by the first version of the tool (it
holds the tool's venv stamp but no marker) is adopted, and only if its `repo/` is absent or is a
git clone whose origin is the repository being tested and whose `pyproject.toml` names Fullseye.
Anything else stops the run before `checkout -f` / `clean -fdx`. Pass `--state-dir` (a Linux path)
for a second location. The environment
variables `FULLSEYE_CI_LOCAL_DIR` and `FULLSEYE_CI_LOCAL_WORKERS` are read on the side you start
the tool from and handed to the Linux side as arguments (a Windows variable does not reach WSL by
itself).

**Environment.** The tests get a fresh `HOME` and an environment built from scratch: no
`PYTHONPATH`, no `FULLSEYE_*_DATA`, no `PYTEST_ADDOPTS`. Two things do come from your machine.
The tool looks for cargo, node and Chrome on your `PATH` (and in `~/.cargo/bin`) and appends the
directories where it finds them to the tests' `PATH` — everything else in those directories comes
along. If `~/.cargo/bin/cargo` exists, `CARGO_HOME` and `RUSTUP_HOME` point at your own `~/.cargo`
and `~/.rustup`. Otherwise the tool sets what the runner and `ci.yml` set. `CI=true` is deliberate — it is
the value GitHub's runner really sets, and two examples branch on `CI == "1"`; setting `CI=1`
locally would test a branch GitHub does not take.

### What it does not check

- Python 3.12 and 3.14 (run on master), 3.13 (weekly) and the 3.15 preview. Local is 3.11 only.
- The per-shard view. CI splits the suite into 6 shards, each its own session; a gate whose answer
  depends on the session (`test_test_durations_is_fresh`) can pass in one local session and fail in
  one shard.
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
- Leftover processes of a killed run. The lock belongs to the tool's own process. If that process
  is killed (`kill -9`, a closed terminal) while pytest is running, the lock is released but the
  pytest children may live on, and the next run cleans the tree under them. After killing a run,
  check that no pytest is left before starting the next one.

BLAS threads are capped at `CPUs / workers` during the parallel run; the handful of tests that skip
because of that cap are rerun serially without it afterwards. The summary reports how many ran, and
the stage fails if the rerun fails or if any of them still did not run (still skipped, or missing
from the rerun).
