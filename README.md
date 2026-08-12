# Fullseye

**An in-house, numpy-native image-processing operator library and evolutionary
pipeline designer.** Every operator is reimplemented from published algorithms and
open-source libraries (OpenCV, scikit-image, SciPy, Pillow, PyWavelets, SimpleITK,
mahotas, kornia/torch), given a single typed interface, and contract-tested
(finite, deterministic, sort-typed). On top of the operators sits an evolutionary
search that *designs* pipelines and gates them honestly on a held-out set.

Two ways to use it: **apply known operators** (most of the time), or **evolve a new
pipeline** when no single operator solves the task. It is `pip`-installable and works
on plain numpy arrays, so other projects can drop it into a vision pipeline directly.

## Install

```bash
pip install -e .            # numpy + scipy core (≈75 operators)
pip install -e ".[all]"     # + opencv, scikit-image, Pillow, PyWavelets, SimpleITK, kornia/torch
# or per-backend: .[opencv] .[skimage] .[pil] .[wavelets] .[gpu] .[extra]
```

Only numpy and scipy are required; every other backend is optional and only its own
operators are affected when it is absent (graceful degradation). GPU is opt-in.

## Quickstart (programmatic API)

```python
import fullseye, numpy as np

frame = np.asarray(img, np.float64)                 # gray H×W in [0,1] (H×W×3 for color)
edges = fullseye.apply(frame, "sobel_amp")          # numpy in, numpy out
seg   = fullseye.apply(frame, "otsu")               # image → region (binary {0,1})
n     = fullseye.apply(seg,   "count_obj")          # region → feature → a float
out   = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])          # shared knobs
out   = fullseye.run_pipeline(frame, [("gaussian",0.3,0.5), ("otsu",0.4,0.5)])   # per-stage knobs
fullseye.list_ops(sort="region"); fullseye.op_names()   # discover
```

`apply(image, name, a=0.5, b=0.5)` and `run_pipeline` take an operator name and two
knobs in `[0, 1]`. Feature operators return a Python float; contour operators a dict.

## Operator library

Roughly **520 typed operators** across ten backends, covering denoising, smoothing,
sharpening, thresholding/segmentation, morphology, edge/corner/blob detection,
distance transforms, color-space conversion, texture/shape features, contours, and
volume (3-D) ops. Sorts: `image` (gray `[0,1]`), `color` (RGB), `region` (binary),
`feature` (scalar), `contour`, `volume`.

```bash
py -3.11 imgevolve.py ops --search edge      # search implemented operators
py -3.11 imgevolve.py apply gaussian in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gaussian,sobel_amp,otsu"
py -3.11 imgevolve.py coverage               # honest coverage numbers
```

Adding one operator makes evolution, code generation, the catalog, and the
machine-readable index (`docs/OP_INDEX.json`) follow automatically.

## Perception stack (robotics-friendly)

Building blocks that turn frames into geometry and objects — the pieces a robot
needs to perceive, measure, and act:

```python
import fullseye as fs
disp  = fs.disparity_map(left, right, max_disp=16)         # dense stereo (block matching)
Z     = fs.depth_from_disparity(disp, focal=f, baseline=B) # Z = f·B/d
pts   = fs.reproject_to_points(Z, fx=f, fy=f)              # point cloud (N,3)
grid,_= fs.elevation_map(world_pts, cell=0.05)            # 2.5-D terrain heightmap
ok    = fs.traversability(grid, cell=0.05, max_step=0.1)  # foothold / obstacle mask
objs  = fs.segment_objects(frame, threshold="otsu")       # per-object records (geometry + descriptors)
rgb   = fs.colorize_depth(Z); fs.save_ply("cloud.ply", pts)   # visualise / export (no matplotlib)
```

`fs.to_float01(x)` coerces uint8/uint16/bool/PIL/path inputs to float64 `[0,1]`.

## Evolutionary pipeline design

When the task is "find an algorithm that maximizes metric *M* on my data", evolve one.
Fitness is measured on the **training** split only; a **held-out** split is tracked but
**never selected on**, so the reported generalization is honest rather than a fit to the
evaluation set.

```bash
py -3.11 baseline.py --problem denoise --workdir out/mine     # honest floor first
py -3.11 evolve.py   --problem denoise --workdir out/mine --gens 40 --pop 24
py -3.11 robust.py   --problem denoise --workdir out/mine --seeds 5   # best-of-N, train-selected
```

## Performance (optional GPU batch backend)

The default per-image path uses scipy/OpenCV. A batched `torch` fast path (`accel.py`,
`--device cuda`) accelerates the compute-heavy vectorizable operators. Honest note: on
CPU the batch path speeds up heavy operators (≈1.6–2.2×) but *loses* on trivial
pointwise ops (tensor-conversion overhead); the real win is on GPU, where that overhead
amortizes over large parallelism.

## Design principles

- **Reimplemented from public knowledge** — published algorithms and open-source
  libraries, unified behind one typed interface; not derived from any proprietary product.
- **Honest by construction** — held-out data is never used for selection; coverage and
  benchmark numbers are measured, not asserted; limitations are disclosed, not hidden.
- **Optional heavy dependencies** — a numpy+scipy core always works; richer backends and
  GPU are opt-in.

## License

Apache-2.0.
