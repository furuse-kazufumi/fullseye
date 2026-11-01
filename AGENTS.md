# Notes for coding agents working in this repository

Read this before changing code, figures, docs or exhibits. It is short on purpose; the linked files hold the detail.

## Rules that are enforced by CI

- **One entry point for generated files**: `py -3.11 tools/regen_all.py` rebuilds everything; `py -3.11 tools/regen_all.py --check` must be green. Never hand-edit generated files (`docs/ops/**`, `OP_CATALOG.md`, galleries, ViEW pages, thumbnails).
- **Measured, not asserted**: any number in code, docs, captions or a PR body must come from a run you made. A quantity that also lives in a ledger (`figures.json`, `docs/view2026/exhibits.json`) must agree with it.
- **Honest gates**: a new operator ships with a docstring stating contract and limits, a worked example asserting ground truth, and tests that check signed values and the conditions under which it breaks. Public reachability, vacuous-assertion and docstring-shape gates run in CI.
- **Run examples against this checkout**: `examples/` import the editable install, which may be another checkout. Use `PYTHONPATH=<this checkout> py -3.11 examples/<poc>.py`.
- **Fail-closed**: invalid input raises or returns the documented fail-soft value; never a silently wrong answer.
- **Language**: exception and CLI messages in English; comments and docstrings bilingual ja+en; ViEW pages ja and en first.

## Quality that CI cannot check

Figures, videos and exhibits are judged by whether a reader gets the claim from the picture. Before producing any of them, read **`docs/POC_QUALITY_CRITERIA.md`** (English: `docs/POC_QUALITY_CRITERIA.en.md`) and apply Template A as your gate table. In short:

- show the subject, the operator's input → output → ground truth, and the failing side, on one screen;
- shapes from dimension tables or point lists (no boxes or spheres as stand-ins), zero interpenetration;
- fixed colour scales, no nearest-neighbour enlargement of data, text in ja/en at readable size and never on top of data;
- numbers on screen from the same run, asserted against the ledgers;
- render deterministically; write first/middle/last frames and a contact sheet outside the repo for inspection;
- report each gate with the frame that proves it and the measured value, not "passed".

## Where to look

- `CONTRIBUTING.md` — the honesty discipline and how to add an operator.
- `docs/ADDING_OPS.md` — operator walkthrough; `tools/preflight_op_add.py <op>` for the ledgers (never `--all`).
- `docs/VALIDATION_CONTRIBUTING.md` — real-data validation reports and the maturity ledger.
- `docs/AI_RAG_GUIDE.md` — operator search (`fullseye-rag search`, MCP `fullseye_find_ops`).
