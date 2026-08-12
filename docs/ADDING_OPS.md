# Adding an operator

Adding one operator makes it available to `apply`/`run_pipeline`, the evolutionary
search, code generation, the catalog, and the machine-readable index — no other
change is needed. There are two ways in.

## The operator contract

Every operator is an `Op` (see `ops.py`):

| field | meaning |
|---|---|
| `name` | unique registry name — the identifier `apply` takes |
| `category` | grouping label (e.g. `smoothing`, `edges`, `segmentation`) |
| `halcon` | reference alias (may be empty) |
| `in_sort` / `out_sort` | one of `image`, `color`, `region`, `feature`, `contour`, `volume` |
| `fn(v, a, b)` | the implementation; `a, b ∈ [0, 1]` are the two knobs |
| `c_stmt(a, b)` | optional — a C statement for the C backend (else the op is C-gated) |

**Sort contract** (enforced by `tests/test_op_contracts.py`):
- `image` / `color` → float in `[0, 1]` (2-D gray, or H×W×3 RGB).
- `region` → binary `{0, 1}`.
- `feature` → a scalar float.
- `contour` → the XLD dict `{"shape", "cs"}`.
- `volume` → a 3-D float stack.
Output must be **finite** and **deterministic** for a given input and `(a, b)`.

## Path A — a hand-written op (`ops.py`)

1. Write `def _myop(v, a, b): ...` returning the declared sort. Use `_norm` to
   rescale a magnitude to `[0, 1]`, or `_signed01` for a signed response (0 → 0.5).
2. Add a tuple to `_DEFS`: `("myop", "category", "halcon_or_''", IN_SORT, OUT_SORT, _myop)`.
3. (Optional) add a C statement in `_c()` for the C backend.

That's it — `REGISTRY` is rebuilt from `_DEFS`, and everything downstream follows.

## Path B — a data-driven spec (`backends_auto.py`)

For operators that fit one of the verified shape factories (pointwise, linfilter,
rank, graymorph, edge, freq, diffusion, texture, geom, threshold, segment, binmorph,
region_trans, region_feat, img_feat, xld), add a **spec** — a name + shape + params —
rather than code. A reference alias is validated against `data/halcon_operators.json`
and dropped fail-closed if it does not exist (no padding the count with fake names).

## The functional gate

`verify_auto.py` runs every generated op on real image/region/contour inputs and
counts only those that return their declared sort without raising. An op that
crashes or returns the wrong sort is not counted — coverage stays honest.

## Provenance

Each operator is reimplemented from a published algorithm or an open-source library;
record the source in the code comment (see `docs/PROVENANCE.md`).
