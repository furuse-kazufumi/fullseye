# Contributing to Fullseye

Feedback and contributions are welcome — the project is built to improve from user
input. The fastest routes:

- **Bug / accuracy report**: open a GitHub issue with the matching template. The
  *accuracy / honesty* template exists because "the number is subtly wrong" reports
  are the most valuable ones here — they have found real bugs (a 32× curvature scale,
  an inverted normal sign) that ratio-style tests could not see.
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

## Adding an operator

`docs/ADDING_OPS.md` has the full walkthrough. Short version: implement + register
→ docstring with contract → worked example → tests → `py -3.11 tools/opdocs.py all`
(regenerates the per-op note + Studio help; CI enforces doc↔code drift) →
`py -3.11 -m pytest -q`.

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
on Python 3.10–3.12. Tags `vX.Y.Z` build from a clean checkout and publish to
PyPI automatically.
