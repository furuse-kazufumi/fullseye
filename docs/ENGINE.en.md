<!-- i18n-source-sha: 8d925234d62d -->
# FullseyeEngine — the runtime that executes a pipeline you designed

[日本語](./ENGINE.md) · **English** · [简体中文](./ENGINE.zh.md) · [繁體中文](./ENGINE.tw.md) · [한국어](./ENGINE.ko.md) · [Deutsch](./ENGINE.de.md)

`FullseyeEngine` (`engine.py`) is the runtime for **executing** — from your own code or the CLI —
an image-operator pipeline you **built** in Fullseye Studio. It is the counterpart of MVTec's
**HDevEngine**: it plays the second half of the two-step story where you design the procedure in
a visual tool and then call it straight from your app without rewriting it.

- **Author**: Fullseye Studio → `Save pipeline` writes out JSON ([STUDIO_GUIDE.md](STUDIO_GUIDE.md)).
- **Execute**: `FullseyeEngine.load("pipeline.json").run(frame)` — **numpy array in, numpy array
  out**. No file I/O and no GUI needed.

A pipeline is a list of `(op, a, b)` stages. The engine can load it from Studio JSON, an `--ops`
string, or a Python list; it inspects the input/output sorts, adjusts each stage's knobs, and can
run against a numpy frame (whole, partway, or one stage at a time). It also does structural
validation (unknown operators, sort mismatches) — the same checks as Studio's diagnostics panel.

---

## The shortest way to use it

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # intermediate result of each stage (a list)
```

`FullseyeEngine` and `diagnose_stages` are exported from `fullseye` (and from `engine`).

---

## Four ways to load

| How to build | Signature | Use |
|---|---|---|
| JSON file | `FullseyeEngine.load(path)` | Read the output of Studio's `Save pipeline` |
| ops string | `FullseyeEngine.from_ops(ops, a=0.5, b=0.5, name="pipeline")` | Comma-separated like `"gaussian,sobel_amp,otsu"` (shared knobs) |
| dict | `FullseyeEngine.from_dict(d, name="pipeline")` | From a dict that has `{"stages": [...]}` |
| list of stages | `FullseyeEngine(stages=None, name="pipeline")` | Directly, like `[("gaussian",0.4,0.5), "otsu"]` (a name-only stage is a=b=0.5) |

`from_dict` raises `ValueError` without a `"stages"` key. `load` reads the JSON and passes it to
`from_dict`, using the file name (without extension) as the `name`.

---

## Method list

| Method | Returns | Description |
|---|---|---|
| `load(path)` *(classmethod)* | `FullseyeEngine` | Load from Studio JSON |
| `from_ops(ops, a=0.5, b=0.5, name=…)` *(classmethod)* | `FullseyeEngine` | From a comma-separated ops string (shared knobs) |
| `from_dict(d, name=…)` *(classmethod)* | `FullseyeEngine` | Load from `{"stages": [...]}` |
| `describe()` | `list[dict]` | Per stage: `{index, op, a, b, in_sort, out_sort, halcon, known}` |
| `op_names()` | `list[str]` | The operator name of each stage |
| `input_sort()` | `str \| None` | The input sort the pipeline expects (the in_sort of the first known op) |
| `output_sort()` | `str \| None` | The output sort the pipeline returns (the out_sort of the last known op) |
| `validate()` | `list[dict]` | Structural problems `{index, op, severity, message}`. `[]` means healthy |
| `is_runnable()` | `bool` | `True` if every stage resolves to a known operator (no errors) |
| `get_knobs(i)` | `tuple` | The knobs `(a, b)` of stage `i` |
| `set_knobs(i, a=None, b=None)` | `self` | Change the knobs of stage `i` (chainable) |
| `run(image, upto=None, coerce=True)` | ndarray / float / dict | Run the pipeline; `upto` runs only stages 0..upto |
| `run_stepwise(image, coerce=True)` | `list` | The intermediate result after each stage (length = number of stages) |
| `run_file(in_path, out_path=None, upto=None)` | raw result | Read an image, run, and optionally save if the result is a raster |
| `to_dict()` | `dict` | `{"fullseye_pipeline": 1, "name", "stages"}` |
| `to_ops()` | `str` | A comma-separated ops string |
| `to_python()` | `str` | Source of a standalone Python function (identical to Studio's Export) |
| `save(path)` | `None` | Save `to_dict()` as JSON |
| `len(eng)` | `int` | Number of stages |

`diagnose_stages(stages)` is a function that validates a stage list without building an engine;
it is what `validate()` is built on. `severity` is `"error"` for an unknown operator and
`"warning"` for a sort mismatch between adjacent stages.

### About sort (the type)

Each operator declares an input/output **sort**: `image` (gray H×W float64 [0,1]) / `region`
(binary {0,1}) / `color` (H×W×3 RGB) / `feature` (scalar float) / `contour` (XLD dict) / `volume`
(3D stack) / `any` (connects to anything). `validate()` emits a warning when an adjacent stage's
out→in disagree (`any` always matches).

---

## Examples of use from Python

### Validate, then run

```python
import fullseye

eng = fullseye.FullseyeEngine.from_ops("gaussian,sobel_amp,otsu")
problems = eng.validate()
if not eng.is_runnable():                      # stop if there is an error (unknown op)
    raise SystemExit(problems)
result = eng.run(frame)                         # returns a region (binary)
```

### Partway / one stage at a time

```python
mid = eng.run(frame, upto=1)                    # up to stage 0..1 (gaussian → sobel_amp)
for i, s in enumerate(eng.run_stepwise(frame)):  # the intermediate result of each stage
    print(i, eng.stages[i][0], getattr(s, "shape", s))
```

### Adjust the knobs and re-run

```python
eng.set_knobs(0, a=0.3).set_knobs(2, a=0.4)     # chainable
out = eng.run(frame)
```

### File I/O (self-contained in code)

```python
eng = fullseye.FullseyeEngine.load("edge.json")
result = eng.run_file("in.png", "out.png")      # load → run → save if raster
```

### Save / export

```python
eng.save("edge.json")                           # save JSON (reopenable in Studio)
print(eng.to_ops())                             # "gaussian,sobel_amp,otsu"
print(eng.to_python())                          # output as a standalone Python function
```

Example output of `to_python()`:

```python
import fullseye, numpy as np

def pipeline(frame):
    return fullseye.run_pipeline(frame, [
        ('gaussian', 0.500, 0.500),
        ('sobel_amp', 0.500, 0.500),
        ('otsu', 0.500, 0.500),
    ])
```

---

## CLI: `imgevolve.py run`

You can run a saved pipeline (JSON or ops string) from the CLI. It uses `FullseyeEngine`
internally.

```
py -3.11 imgevolve.py run <pipeline.json|ops> [inp] [--out PATH]
                          [--upto N] [--stepwise] [--describe] [--to-python] [--a A] [--b B]
```

| Argument / option | Meaning |
|---|---|
| `pipeline` | A pipeline `.json` (Studio's Save pipeline) or a comma-separated ops string |
| `inp` | Input image (if omitted, only `--describe` / `--to-python` can run) |
| `--out PATH` | Where to save the result (only raster results are saved) |
| `--upto N` | Run up to stage 0..N |
| `--stepwise` | Report each stage's result, and with `--out` save them as `PATH_00`, `PATH_01`, … |
| `--describe` | Show the pipeline's I/O, each stage, and validation results (with no input, just shows and exits) |
| `--to-python` | Output the pipeline as a Python function |
| `--a` / `--b` | Shared knobs when building from an ops string (default 0.5) |

Examples:

```powershell
# check structure only (no image needed)
py -3.11 imgevolve.py run edge.json --describe
#   pipeline 'edge': image -> region
#     0. gaussian      a=0.50 b=0.50   [image -> image]
#     1. sobel_amp     a=0.50 b=0.50   [image -> image]
#     2. otsu          a=0.50 b=0.50   [image -> region]

py -3.11 imgevolve.py run edge.json in.png --out result.png       # run and save
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png  # save each stage
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python   # ops string → Python
```

A pipeline that contains an unknown operator (an error) can still be shown with `--describe`, but
at run time it stops and reports the problem.

---

## Calling from other projects (onocollo / evis / hillco, etc.)

Because `fullseye` is self-contained on numpy arrays for input and output, you can drop it
straight into a robotics/vision pipeline. The division of labour **design in Studio, execute in
each project** is possible.

```python
import fullseye

# load once at startup (lightweight; it holds only the op resolution and the knobs)
PIPELINE = fullseye.FullseyeEngine.load("assets/segment.json")

def perceive(frame):                            # frame: a float64 gray [0,1] you prepared yourself
    seg = PIPELINE.run(frame)                   # numpy in, numpy out (no disk needed)
    return seg
```

Key points:

- **No file I/O needed**: pass a numpy frame from a sensor/simulator directly and receive numpy.
  It works on embedded or GPU-simulation environments without an I/O backend.
- **Lightweight**: `load` / `from_ops` only hold the operator names and knobs. The heavy compute
  happens only on the `run` call.
- **Version-independent**: the pipeline JSON is data, so swapping the pipeline leaves the calling
  code unchanged. A research iteration (tune the pipeline in Studio → update the JSON) does not
  ripple out to the caller.
- **If a single operator is enough**, you can call `fullseye.apply(frame, "otsu")` directly, or
  `fullseye.run_pipeline(frame, [...])` for multiple stages (a light path that doesn't go through
  the engine).

The perception stack (stereo / terrain / flow / detect / registration / pose) also runs on numpy
in the same way (`fullseye.disparity_map`, etc.). For usage examples see `examples/`
([../examples/README.md](../examples/README.md)) and [PERCEPTION.md](PERCEPTION.md) /
[PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md).

---

## Related documents

- [STUDIO_GUIDE.md](STUDIO_GUIDE.md) — build a pipeline and write out the JSON
- [GETTING_STARTED.md](GETTING_STARTED.md) — get going in 5 minutes
- [INSTALL.md](INSTALL.md) — environment setup (including embedded and minimal configurations)
