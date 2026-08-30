# Depending on Fullseye from another project (stability contract)

Fullseye (working name imgevolve) is meant to be a **durable foundation** other
FullSense projects (onocollo / evis / hillco / xct / mcp-3d …) build on: it keeps
growing (more ops, more perception features), and consumers must keep working across
that growth. This document is the contract that makes that safe.

## How to depend on it

```powershell
pip install -e <path-to-fullseye>                 # editable; or add the dir to sys.path
```
```python
import fullseye as fs                              # the ONE public entry point
out = fs.apply(frame, "gaussian", 0.6)             # op library
cloud = fs.depth_to_points(depth, K)               # perception stack
```
Consumers import **`fullseye`** only — never the flat internal modules
(`ops`, `backends_*`, `api`, …) directly; those are implementation detail and may
be reorganised. Everything a consumer needs is re-exported from `fullseye`.

## The stability contract (what will NOT break)

1. **Additive growth.** New operators and functions are added freely. Existing
   public names in `fullseye.__all__` are **not removed or renamed** without an
   explicit, reviewed change.
2. **`fullseye` re-exports the whole public API.** Whatever `api.py` declares public
   is reachable from `import fullseye`.
3. **Enforced by a test.** `tests/test_public_api.py` runs in the full suite and
   **fails** if (a) any consumer-critical GOLDEN name disappears, (b) a name in
   `fullseye.__all__` stops resolving, (c) the facade drops an `api` public name, or
   (d) the core `apply` path breaks. So a change that would break a downstream
   project is caught before it lands. To intentionally rename/remove a public
   function, update `GOLDEN` in that test in the same commit (makes it explicit).
4. **Versioning.** `fullseye.__version__` / `fs.version()`. Consumers may pin.
5. **No heavy hard deps.** Core is numpy + scipy; opencv/skimage/torch/SimpleITK/etc.
   are optional extras — a consumer that only needs core perception installs nothing
   extra. Missing optional backends only disable their own ops (fail-closed).

## Discovering what's available (as it grows)

- **Agents / humans:** the `image-processing` skill (`~/.claude/skills/image-processing/`)
  — the agent-facing entry with the full API + worked pipelines; auto-triggers on
  image/perception tasks.
- **Perception catalog:** [`docs/PERCEPTION_PHYSICAL_AI.md`](PERCEPTION_PHYSICAL_AI.md)
  (module/function/reference table + pipelines).
- **Per-project applications:** [`docs/CONSUMER_APPLICATIONS.md`](CONSUMER_APPLICATIONS.md).
- **Op library programmatically:** `fs.list_ops()` / `fs.op_names()` / `fs.find_op(name)`
  / `imgevolve.py has <halcon_op>` / `docs/OP_INDEX.json`.
- **Runtime device/comm/acquire menu:** `fs.capabilities()`.
- **Runnable template:** `examples/physical_ai_perception.py`.

## Two runtimes for composing ops

- `fs.FullseyeEngine` — a **linear** saved pipeline (JSON/ops → run/step/to_python).
- `fs.FullseyeGraph` — a **DAG** (branch + merge, e.g. residual = raw vs blurred, or
  a stereo pair through a 2-input op), same operator catalog.

## Honest boundary

Fullseye is classical (numpy/scipy, no learned detectors/segmenters/priors). It
covers geometry, filtering, measurement, classical stereo/point-cloud/pose/terrain/
odometry/occupancy — not learned recognition. Consumers needing learned models pair
Fullseye with their own model; Fullseye supplies the measurement/geometry substrate.
