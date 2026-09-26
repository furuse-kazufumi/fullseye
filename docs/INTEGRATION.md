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

## From an LLM (MCP server, 0.1.11 PoC)

`py -3.11 -m fullseye.mcp` is a stdio Model Context Protocol server (protocol
`2025-06-18`). It exposes **9 tools, not 1,942**: search the catalog, read an operator's
knowledge-layer note (with its pre-rendered, gate-verified figures as `resource_link`s),
load a sample or a sandboxed image into a handle, apply one operator or a pipeline, and
inspect a handle, and fix the text inside an image against the string it should read
(`fullseye_fix_text`: repair only the flagged glyphs or redraw the whole line; the report
says `typo` or `unrelated` when the original text has nothing to do with the intended one).
Images travel as `fullseye://img/<sha16>` handles; every result carries
raw statistics **and** a verdict (`ok / constant / flat / saturated / nonfinite /
out_of_range / empty`), and a small input-vs-output figure is attached automatically only
when the verdict is not `ok`. The default is strict (`on_error="raise"`): a degraded
operator is refused with the reason; `allow_degraded=true` opts into fail-soft and then the
degradation ledger is always in the result. Paths outside the sandbox roots, unknown
operator names, sort mismatches, out-of-range knobs and unknown arguments are all refused
explicitly — nothing is coerced to "the nearest thing".

It runs from the wheel (0.2.0+). The catalog's sources of truth are `docs/OP_INDEX.json`
and the front matter of `docs/ops/**/*.md`, which are not inside the package; so
`tools/gen_mcp_data.py` copies the index and the six front-matter keys the server reads
(op / dim / category / in / out / halcon, plus the note's relative path — not the bodies)
into `fullseye/data/OP_INDEX.json` and `fullseye/data/OP_NOTES.json`, which ship as
package data (about 0.8 MB). Resolution order: index = package copy, then a repo `docs/`
if present, else `CatalogError`; notes = repo `docs/ops` (bodies available), then the
packaged front matter, else `CatalogError`. It never serves an empty catalog. From a
`pip install`, `fullseye_op_help` returns the shipped Studio help HTML instead of the
note body and says so (`note_body_unavailable`), and `fullseye_catalog_coverage` reports
`index_source` / `notes_source`. Regenerate the copies with `py -3.11 tools/gen_mcp_data.py`
(part of `tools/regen_all.py`); `tests/test_mcp_wheel.py` (`FULLSEYE_WHEEL_GATE=1`) builds
the wheel, installs it into a fresh venv and counts the catalog from outside the repo.
Details: [`MCP.md`](MCP.md).

## From other languages (C ABI)

`fullseye_abi.h` is a **specification-only C ABI** — 25 typed functions around 5 contract
operators (`fs_gauss`, `fs_threshold`, `fs_connection`, `fs_measure_all`, `fs_select_shape`),
plus the generic `fs_apply` (0.2.0, below) that reaches the 2-D registry by name — with a
Rust `cdylib` reference implementation in `rust/fullseye_core`. Because the library is a
plain C ABI there are no per-language bindings to maintain: Python (`ctypes`,
`python_ctypes.py`), C# (`DllImport`, `csharp/Program.cs`), C / C++ (`#include
"fullseye_abi.h"`, `c/main.c`) and LuaJIT (`ffi.cdef`, `luajit_ffi.lua`) all call the same
`.dll` / `.so` and, in the checked-in examples, print the same five lines. The examples in
[`rust/fullseye_core/examples/`](../rust/fullseye_core/examples/README.md) record which
toolchains were actually run (clang, gcc/MinGW, MSVC, .NET SDK 9, LuaJIT 2.1, CPython 3.11
as of 2026-09-15) rather than which ones exist.

What this is **not**: it is not the Python library (2,189 operators in the machine-readable
index) in another language. Its
purpose is to be a *second implementation* of a small contract, so that a differential
fuzzer and a header-including C caller can find specification bugs the Python tests cannot
— nine were found this way in 0.1.11 (connectivity, border mode, object ordering, status
codes, a missing ABI argument, a header that MSVC read as cp932, …). Speed is not the point:
the wins measured against Python were representation wins (run-length regions), not
language wins, and the losses were SIMD losses; see `CHANGELOG.md` 0.1.11.

### Every operator through one function: `fs_apply`

**Every operator of the 2-D registry (901 single-input operators; the 918 2-D operators of the
index minus the 17 n-ary ones; those whose backend is installed) is reachable through
`fs_apply`; the five contract operators also have a native route. Look at `route`.** The typed
ledgers (1,240 operators whose inputs are point clouds, signals, tables …) and the n-ary
operators cannot be carried by one image / region handle and are refused with a status code and
a reason — a later stage, not a silent gap. `fs_apply(op, inputs, n_in, params_json, route_pref, outputs,
out_cap, n_out, info)` names the operator as a string and takes its parameters as a JSON
object. Behind it are two routes — `"native"` (the Rust implementation of the five contract
operators) and `"python"` (an embedded CPython running the Python registry, present only when
the cdylib is built with `cargo build --release --features embed`; otherwise that route
answers `FS_E_NO_PYTHON` with the reason). `route_pref` is `0` auto / `1` native only /
`2` python only, and `fs_apply_info_t.route` always reports which one ran, `backend` which
Python implementation ran (`numpy`, `cv2`, …), `degraded` whether the fallback ledger recorded
anything, `message` the reason on failure or the resolved parameters (typed — `5` and `5.0`
are kept apart) on success. Parameters are validated in one place, the Python registry, with
the same fail-closed validator the MCP server uses (unknown key, wrong type, out-of-range, NaN
are refused; JSON must be RFC 8259). `fs_catalog_json` returns every name, its routes, input
kinds and parameter table. Forcing route 1 and 2 on the same input is the differential gate
(`tests/test_abi_apply.py`); the Python side is `fullseye/abi_bridge.py`.

Runtime requirements, stated plainly (nothing is bundled yet): `python311.dll` must be found
by the OS loader (next to the executable or on `PATH`) — it is a static import, because pyo3
imports data symbols and `/DELAYLOAD` cannot link them; the standard library location is
resolved from `FULLSEYE_PYTHON_HOME`, then the PEP 514 registry, then the loaded DLL's
directory; the bridge (`fullseye/abi_bridge.py`) is imported from that interpreter's
`site-packages` — since 0.2.0 the wheel ships it (`tests/test_abi_wheel.py` installs the wheel
into a fresh venv and drives `fs_apply` from outside the repo) — or from a checkout named by
`FULLSEYE_ROOT` (found automatically when the DLL lives under the checkout's `target/`). Note
that `FULLSEYE_PYTHON_HOME` names an *installation*, not a venv, so a non-Python host uses that
installation's `site-packages`. When the host process already
is CPython (`ctypes`), nothing is started and the host's interpreter — a venv included — is
used; a host running a
different CPython version is refused. Arrays cross the boundary by copy (measured on a
512×512 float64 Gaussian, σ=2, warm: native 7.0 ms; python route 4.8 ms of which the cv2 kernel
is 1.6 ms — the rest is the copy and the dictionary round trip).

Next stage, not done: bundle a CPython so the cdylib is self-contained. The plan is
python-build-standalone (`cpython-3.11.*-x86_64-pc-windows-msvc-install_only_stripped`,
about 24 MB) unpacked next to the cdylib, `fs_python_init("<that dir>")` as the home, and the
`fullseye` package plus its numpy/scipy/cv2 wheels installed into it; zero-copy arrays are a
separate step (a borrowed numpy view must not outlive the Rust buffer it wraps —
`borrow_from_array` and friends make that easy to get wrong, so the copy stays until a test
pins the lifetime).

## Honest boundary

Fullseye is classical (numpy/scipy, no learned detectors/segmenters/priors). It
covers geometry, filtering, measurement, classical stereo/point-cloud/pose/terrain/
odometry/occupancy — not learned recognition. Consumers needing learned models pair
Fullseye with their own model; Fullseye supplies the measurement/geometry substrate.
