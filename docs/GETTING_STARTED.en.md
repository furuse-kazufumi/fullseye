<!-- i18n-source-sha: d72686b2f766 -->
# Getting started (running in 5 minutes)

[日本語](./GETTING_STARTED.md) · **English**

## Which one is your job? (three ways in)

Fullseye is broad, so if you can't decide **which single file to open first** you stall. What
follows are not freshly written demos but **examples a gate already runs every time** (if one
breaks, CI goes red).

| Way in | Who it's for | 5 min: just run it | 30 min: follow the internals | Half a day: on your own data |
|---|---|---|---|---|
| **Explainable visual inspection** | inspection / QA | `py -3.11 examples/poc_solder_fillet_aoi.py` — AOI of a solder fillet | `py -3.11 examples/poc_fabric_defect.py` — count misses and false alarms separately | "Detect" in [CAPABILITIES.md](CAPABILITIES.md) → your own image in Studio |
| **3-D for robots** | robotics / 3-D metrology | `py -3.11 examples/perception_pipeline.py` — stereo → depth → point cloud → traversability | `py -3.11 examples/grasp_pose.py` — fit a point cloud to a model for 6-DoF pose and grasp direction | [EXAMPLES_3D.md](EXAMPLES_3D.md) → feed your own cloud/mesh |
| **Physics-based NDT** | X-ray / optics / metrology | `py -3.11 examples/ct_reconstruction.py` — projection → reconstruction → dimensions in mm and defect count | `py -3.11 examples/poc_ct_void_morphology.py` — why a single pass/fail number is blind to shape | "Shape" in [CAPABILITIES.md](CAPABILITIES.md) → your own volume |

Every example **carries ground truth** (closed-form or synthetic). It always prints the null case
(doing nothing), so you can judge for yourself whether something "worked". The ledger of how far
each thing is actually validated is [MATURITY.md](MATURITY.md) — not written by hand, but counted
from the gates that run and whether real data was involved.

---

This guide gets Fullseye (working name imgevolve) running by the shortest path: **install → build
your first pipeline → run it → look at the result**, in an order that doesn't get you stuck. For
fuller setup see [INSTALL.md](INSTALL.md), for everything Studio does see
[STUDIO_GUIDE.md](STUDIO_GUIDE.md), and for running from code see [ENGINE.md](ENGINE.md).

Fullseye is an **image-processing operator library whose inputs and outputs are numpy arrays**,
with an **HDevelop-style visual pipeline-design environment (Fullseye Studio)** and an **execution
runtime (FullseyeEngine)** on top. In HALCON/HDevelop terms, it reproduces the two-stage
"assemble the procedure in HDevelop, call it from your own app via HDevEngine" shape directly in
Python + numpy.

---

## 1. Install (1 minute)

Prerequisite: **Python 3.11** (`py -3.11` on Windows, `python3.11` on Linux).

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .          # numpy + scipy core only (~885 operators)
```

The core runs on **numpy and scipy alone**. Extra backends such as OpenCV / scikit-image / Pillow
are optional; if one isn't installed, only that backend's own operators are disabled (graceful
degradation). In practice you need at least OpenCV or Pillow for reading and writing image files,
so adding one of these makes life easier:

```powershell
py -3.11 -m pip install -e ".[opencv]"    # image I/O + OpenCV-derived operators
py -3.11 -m pip install -e ".[all]"       # all backends (opencv, skimage, pil, wavelets, gpu, extra)
py -3.11 -m pip install -e ".[gui]"       # if you want Fullseye Studio (PySide6)
```

The list of extras and what each means is collected in [INSTALL.md](INSTALL.md). To use the GUI
you need `[gui]` (or `[all]` + `[gui]`).

> You can also try it without installing. Make the repository root (`<path-to-fullseye>`) your
> working directory and put that path on the `PYTHONPATH` environment variable, and `import
> fullseye` will work. The `fullseye` / `fullseye-studio` commands (console scripts), however,
> only become available once you run `pip install -e .`.

---

## 2. Run a single operator first (Python)

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

edges = fullseye.apply(frame, "sobel_amp")     # image → image (gradient magnitude)
seg   = fullseye.apply(frame, "otsu")          # image → region (0/1 binary)
n     = fullseye.apply(seg,   "count_obj")     # region → feature (object count = Python float)
print(n)                                       # e.g. 316.0
```

> **The argument order is `apply(image, name, a, b)`** — the first argument is the array, the
> second is the op name. Passing them the other way stops with `TypeError: ... arguments look
> swapped` from 0.1.9 on (up to 0.1.8 it became numpy's unrelated "truth value of an array is
> ambiguous" error). `a`/`b` are finite values in 0..1. A string / `None` / NaN is an immediate
> `TypeError`/`ValueError`; out-of-range values are clamped and recorded in the ledger.

- `apply(image, name, a=0.5, b=0.5)` applies **one operator**. `name` resolves as either the
  **operator name** (e.g. `gaussian`) or the **HALCON alias** (e.g. `gauss_filter`).
- `a`, `b` are the **two knobs (0.0–1.0)** each operator carries. Their meaning differs per
  operator (radius / threshold / σ, etc.).
- The output type (sort) is determined by the operator: `image` (gray) / `region` (binary) /
  `feature` (scalar float) / `color` (RGB) / `contour` (XLD) / `volume` (3D).
- **What happens on failure** (from 2026-09-03): under the default `on_error="fallback"`, even if
  an op fails internally it returns a harmless value matching the type (a copy of the input for an
  image, etc.), and a **`FullseyeFallbackWarning` is emitted just once per op**. What fell back and
  how often is available via `fullseye.fallbacks()` / `fullseye.fallback_counts()`. Passing
  `on_error="raise"` (or the environment variable `FULLSEYE_ON_ERROR=raise`) makes it
  **fail-closed**: the op's real exception, dtype contract violations (integer/bool images), and
  GPU-kernel failures propagate as-is. **Sort mismatches are only partially checked** (e.g. passing
  an RGB `(H,W,3)` to a 2-D op is treated as a volume and does not raise even under `raise` —
  `docs/KNOWN_ISSUES.md` #32-4). `raise` is recommended for CI and validation.
- **Multi-input ops** (`add_image` / `union2` etc., `tier == "nary"` in `list_ops()`) take their
  **inputs as a list**: `fullseye.apply([img1, img2], "add_image")`.
- **Template matching** (`ncc_locate` / `shape_locate`) takes the image to search for via
  `template=`: `corr, row, col = fullseye.apply(img, "ncc_locate", template=patch)` (the returned
  row/col is the **center** of the match). Without a template it returns the no-match `[0, 0, 0]`.

You can discover what operators exist like this:

```python
fullseye.op_names()                 # all registry operator names (860, as of 2026-09-03)
fullseye.list_ops(search="edge")    # substring search over name / HALCON name / category
fullseye.list_ops(sort="region")    # filter by input sort
fullseye.categories()               # 47 categories
```

---

## 3. Build a pipeline (chaining several operators)

Passing an array through several operators in sequence is a "pipeline": it threads the array
through each stage and returns the final result.

```python
# same a, b across all stages (same shape as the CLI)
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

# when you want different knobs per stage (specify as (name, a, b) tuples)
out = fullseye.run_pipeline(frame, [("gaussian", 0.3, 0.5), ("otsu", 0.4, 0.5)])
```

This is "smooth → edge magnitude → Otsu threshold", a typical example of turning an image into a
binary edge map. **20** ready-to-use combinations (recipes) ship with it.

```python
import recipes
recipes.names()                                   # list of recipe names
stages = recipes.stages("Edge — Sobel + Otsu")    # [(op, a, b), ...]
out = fullseye.run_pipeline(frame, stages)
```

---

## 4. Build it visually (Fullseye Studio)

Without writing code, you can search for operators and lay them out, turn the knobs with sliders,
run them one stage at a time, and assemble the pipeline while watching the intermediate results.
The GUI extras (`pip install -e ".[gui]"` = PySide6) are required.

```powershell
py -3.11 studio.py          # or, if installed: fullseye-studio
```

It has three panels.

- **Left (Operators)**: filter operators by category / search and **double-click to insert**
  (Edit ▸ Focus operator search = **Ctrl+F** jumps to the search box). Sample pipelines load from
  here too. **Insert (＋) works like HDevelop's operator window**: adding a stage to the pipeline
  also writes a `op (a, b)` line at the cursor position in the Program window (values at full
  `repr` precision; when the Program has unapplied hand-edits it inserts only the line, reflected on
  Apply).
- **Center (Pipeline)**: the list of laid-out stages. Reorder by drag or Ctrl+↑/↓, and adjust the
  **knobs a / b** of the selected stage. The knobs are always 0..1 values, but **ops that have a
  display spec (`param_specs.py`) can be operated in their real units** — for `gaussian`, σ in px
  (slider + unit spinbox); for `median`, the kernel size in a 3/5/7/9 combo; for `reg_erode`, the
  iteration count in an integer spin; for `aug_barrel`, b as a "pincushion" checkbox. The 0..1 spin
  on the right is always the raw value (for exact input). The specs are hand-written from the
  conversion formulas in ops.py (`0.3 + 2.7·a`, etc.) and cross-checked against the implementation
  by tests (`tests/test_studio_params.py`). Ops with no spec keep the two 0..1 sliders as before.
  The stage list is written in display units too (`gaussian (blur σ=1.08 px, b=–)`). **Reset
  (Home) → Step (Ctrl+→) → Run all (Ctrl+Enter)** runs one stage at a time or all at once.
- **Right (Image / Perception / Analysis)**: the result image zoomed/panned, a histogram, the
  Inspector (examine image / region / feature values), and the v14 perception panel (optical flow /
  stereo depth, etc.). **Right-click the image view** for Fit / 1:1 / Zoom / Save result / Save
  view as shown / Copy / Display mode / 3D surface (the same actions as the menu). Extra graphics
  windows you open also get a small strip of Fit·1:1·±·Save and the same right-click menu, and the
  3-D viewer (Ctrl+4) has right-click Reset view / toggle first-person (perspective) / Wireframe /
  Save screenshot.

You can **Export (Ctrl+E)** the assembled pipeline as an `--ops` string or Python code, and **Save
pipeline (Ctrl+Shift+S)** it as JSON. All features and shortcuts are in
[STUDIO_GUIDE.md](STUDIO_GUIDE.md); inside the app, **F1** shows the list.

---

## 5. Run a saved pipeline (CLI / code)

A JSON you `Save pipeline`d in Studio (or an `--ops` string) runs directly against a file. This is
the HDevEngine-equivalent path of "run what you designed without rewriting it".

```powershell
# check the saved JSON's I/O and stages (structure check, no image)
py -3.11 imgevolve.py run edge.json --describe

# apply to an image and save the result
py -3.11 imgevolve.py run edge.json in.png --out result.png

# save the result of each stage (result_00.png, result_01.png, ...)
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png

# export the pipeline as a standalone Python function
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python
```

To run from code, use `FullseyeEngine` (details in [ENGINE.md](ENGINE.md)).

```python
import fullseye
eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # intermediate result of each stage (list)
```

---

## 6. Apply one at a time on the CLI

When you want to process an image file directly, the CLI is the quickest (OpenCV or Pillow needed
for image I/O).

```powershell
py -3.11 imgevolve.py ops --search edge                    # search operators
py -3.11 imgevolve.py has gauss_filter                     # is the HALCON name implemented + how to call it
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gaussian,sobel_amp,otsu"
```

`apply` / `pipeline` take a common `--a` / `--b` for every stage. When you want different knobs per
stage, use `run_pipeline` (Python) above, or Studio.

---

## If you get stuck

| Symptom | What to do |
|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | run `pip install -e .`, or put the repo root on `PYTHONPATH` |
| no `fullseye` / `fullseye-studio` command | console scripts are registered by `pip install -e .`. If not installed, use `py -3.11 imgevolve.py ...` / `py -3.11 studio.py` |
| Studio won't start | GUI extras not installed. `pip install -e ".[gui]"` (PySide6) |
| `cannot read ...` in `apply` / `pipeline` | install OpenCV (`[opencv]`) or Pillow (`[pil]`) for image I/O |
| an extra backend's operator is "unknown" | that backend isn't installed. Add `.[skimage]` `.[wavelets]` `.[extra]`, etc. |

For fuller troubleshooting see [INSTALL.md](INSTALL.md).

## What to read next

- **[INSTALL.md](INSTALL.md)** — complete setup guide (choosing extras, Windows/Linux installers, minimal/embedded configs)
- **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** — complete Fullseye Studio guide
- **[ENGINE.md](ENGINE.md)** — FullseyeEngine (design → run) guide
- **[README.md](README.md)** — documentation index
