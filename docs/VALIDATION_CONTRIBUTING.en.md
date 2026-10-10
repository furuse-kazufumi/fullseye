<!-- i18n-source-sha: f2fb401659c3 -->
# Reporting validation on real hardware or real data

**English** · [日本語](VALIDATION_CONTRIBUTING.md)

Fullseye is developed by one person without physical measurement rigs. What CI can
check stops at virtual optical systems, synthesised ground truth and ground truth that
can be computed in closed form. Part of the reason it is released under Apache-2.0 is
so that people who do have real hardware or real data can check it. Each report makes
the verification in the [maturity ledger](MATURITY.md) a little more accurate.

**You do not have to share your data.** Company images, CAD and measurements usually
cannot leave the building. Results-only reports are accepted as a proper route (they
carry less weight than reproducible reports; see "Promotion rules" below).

## Two routes

| Route | When to use it |
|---|---|
| [Validation report form](https://github.com/furuse-kazufumi/fullseye/issues/new?template=real_validation_report.yml) (GitHub issue) | Reports meant to move a capability's stage (`verified-synthetic` → `validated-public-real-data` → `validated-hardware`) |
| [Discussions › Show and tell](https://github.com/furuse-kazufumi/fullseye/discussions/categories/show-and-tell) | Informal "I tried it on my rig" results and questions. They do not move a stage, but they can grow into a formal report |

If you would rather not post in public, you can email the maintainer
(kazufumi@furuse.work, the same address as the author entry in `pyproject.toml`). In that
case **only aggregate numbers, and only with your consent,** are published, and the
ledger's `source` field records `private-submission`.

## What reports are welcome

- Real hardware: you built a camera / sensor / optics / lighting setup, ran a Fullseye
  capability, PoC or operator, and compared it with an independent reference
- Public real data: you ran it on a dataset with a clear licence and URL
- Private real data: numbers only, or numbers plus a synthetic re-creation of the data
- **Failure conditions**: where it broke or degraded (lighting, surface, size, noise, ...).
  These are as useful as successes

Ground truth should come from a reference instrument, a calibration target, a certified
artefact or published values, with its **uncertainty stated in units** (for example
±0.005 mm, k=2).

## Privacy and data handling

- **Do not post confidential data, images or product names.** A generic description of
  the setup is enough ("1/2-inch monochrome sensor, 0.5x telecentric lens, coaxial
  light").
- Employer or affiliation is never asked for, and the ledger has no field for it
  (`tools/gen_maturity.py` refuses records with unknown fields).
- There are three ways to handle data:

| `data_sharing` | Form option | Meaning |
|---|---|---|
| `shared` | Can share the data | The data is shared (give licence and URL) |
| `synthetic-recreation` | Can share a synthetic re-creation | Instead of the real data, a synthetic re-creation of the same conditions is shared. **Welcome** — the maintainer can reproduce the result and the original data never leaves |
| `results-only` | Results only (data stays private) | Only the numbers are reported |

## Validation kit

A tool that produces numbers in a fixed, comparable way without your data leaving your
machine.

```text
python -m fullseye.validation_kit list
python -m fullseye.validation_kit run blob-count --manifest truth.csv --out result.json
```

`truth.csv` has two columns, `file,truth` (`file` is relative to the CSV's folder;
`truth` is the value from your reference). The output JSON contains only the item count,
error statistics (mean, signed mean, RMS, maximum, exact-match rate and so on), the
Fullseye version and commit, Python / numpy versions, the OS type, and the SHA-256 of
each input file. **No pixels, file names or paths** (add `--no-hashes` to drop the hashes
as well). Paste the JSON into the form's "Results" field.

There is one kit so far: `blob-count` (capability `blob-and-region`: count objects and
compare with the reference count). To add one, add a `Kit` to `KITS` in
`fullseye/validation_kit.py` (`measure` takes a greyscale image and the parameters and
returns one scalar) and a known-truth test to `tests/test_validation_kit.py`.

## Promotion rules

**The maintainer decides.** The maintainer reads each report, decides whether to accept
it (`accepted`), and records accepted reports in `docs/validation_reports.json`. Accepting
alone does not move a stage: `tools/gen_maturity.py` applies the rules below
**mechanically**, and a stage moves only when one is met. The rules are also written out
in [MATURITY.md](MATURITY.md).

| Rule | Promotes to | Condition |
|---|---|---|
| `hardware-reproducible` | `validated-hardware` | **One** hardware report: accepted; traceable ground truth (calibrated instrument, certified artefact or published values); data or a synthetic re-creation shared together with the procedure; the maintainer re-ran it and got the same numbers within the stated uncertainty |
| `hardware-independent-results` | `validated-hardware` | **Two or more** hardware reports (results-only is fine): accepted; different reporters; different setups; each with traceable ground truth; each agreeing within its stated uncertainty |
| `public-data-reproduced` | `validated-public-real-data` | **One** report on public real data: accepted; dataset URL and licence given; the maintainer re-ran it on the same data and got the reported numbers |

A single results-only report does not move a stage on its own. Because it cannot be
reproduced, agreement from a different person on a different setup is required. It is
still recorded, credited and counted together with the next report. External reports
never **lower** a stage (a report that could not be reproduced stays on record as
`not-reproduced`).

`validated-public-real-data` can also be reached the existing way: an example driven by
public real data (`data: real`) that a CI gate runs.

## How reports are recorded

One entry per report in the `reports` array of `docs/validation_reports.json`.

| Field | Content |
|---|---|
| `id` / `capability` / `kind` | Report id / capability id (`docs/capabilities/`) / `hardware` or `public-real-data` |
| `review` | `pending` / `accepted` / `not-reproduced` / `withdrawn` |
| `source` | Issue URL, or `private-submission` |
| `reporter` / `setup` | A short key to tell reports apart (a handle, `anon-1`, ...) / a short description of the setup |
| `ground_truth` / `ground_truth_uncertainty` | How ground truth was obtained / its uncertainty |
| `procedure` / `fullseye_version` / `result` | Procedure / version / summary of results (with units and n) |
| `data_sharing` | `shared` / `synthetic-recreation` / `results-only` |
| `credit` | Name or handle to credit (optional; `null` means anonymous) |
| Optional | `traceable_reference` / `reproduced_by_maintainer` / `within_stated_uncertainty` / `data_licence` / `data_url` / `reviewed_on` / `failure_conditions` / `note` |

After recording, regenerate the ledger with `py -3.11 tools/gen_maturity.py`
(`tests/test_maturity.py` and `tests/test_validation_reports.py` check the shape and the
rules).

## Credit

Reports with a `credit` value are credited by name (or handle) in the "External
validation reports" table of [MATURITY.md](MATURITY.md) and in the release notes. Leave
it empty to stay anonymous. To withdraw a report, say so in the issue or by email; it is
marked `withdrawn` and drops out of the stage calculation.
