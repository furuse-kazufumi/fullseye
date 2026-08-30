---
name: fullseye-ops
description: >-
  Use when a task involves image processing or geometric vision (denoise, threshold,
  morphology, edges/corners/blobs, texture/shape features, contours, stereo depth,
  point clouds, 6-DoF pose, meshes, volumes) and the fullseye library is available.
  Look operators up in the machine-readable corpus (docs/ops), chain them by type
  (sort), and verify with the shipped worked examples instead of writing ad-hoc
  cv2/skimage code.
---

# Fullseye operator corpus — how to use it as your RAG

Fullseye ships ~1000 typed classical-vision operators (2-D: 731, 3-D: 265) and, for
every one of them, a generated Markdown note. **Those notes are your knowledge base**
— retrieve first, then write code.

## Where the corpus lives

FULLSEYE_REPO = (not pinned — locate the repo as described below, or install this
skill with `py -3.11 tools/setup_claude_rag.py`, which rewrites this line to the
absolute repo path)

Locate the repo root (contains `fullseye/` facade, `docs/ops/`, `examples/`,
`examples_3d/`). If only the pip package is installed, clone the repo to get
`docs/ops` — the corpus is repo content, not wheel content.

| What | Where |
|---|---|
| Per-op note (contract, call form, HALCON alias, references, related ops) | `docs/ops/2d/<category>/<op>.md`, `docs/ops/3d/<category>/<op>.md` |
| Tables of contents (auto-generated, category-walked) | `docs/ops/INDEX.md`, `docs/ops/2d/INDEX.md`, `docs/ops/3d/INDEX.md` |
| Family how-to guides (13, with math + mermaid + citations) | `docs/ops/2d/guides/<family>.md` |
| Sample-data catalog (real download URLs) | `docs/ops/SAMPLES.md` |
| Machine index of the registry | `docs/OP_INDEX.json` |
| Ground-truth-checked runnable examples | `examples/*.py` (2-D), `examples_3d/*.py` (3-D) |

## Retrieval recipes

- Find an op by concept: `Grep docs/ops -i "<keyword>"` then open the note.
- Find by HALCON name: notes carry a `halcon:` frontmatter field — grep it.
- Chain by type: each note lists `in:`/`out:` sorts and **related ops whose types
  connect** — follow those links instead of guessing.
- Before implementing anything from scratch, check `docs/ops/INDEX.md`: with ~1000
  ops the thing you need usually exists.

## Calling conventions

```python
import fullseye, numpy as np
out = fullseye.apply(img, "gaussian", 0.5, 0.5)        # 2 knobs in [0,1]
out = fullseye.run_pipeline(img, ["gaussian", "sobel_amp", "otsu"])
fullseye.list_ops(sort="region"); fullseye.op_names()  # discover programmatically
```

3-D ops are plain functions re-exported through the facade (see each note's call
line). Perception stack: `fs.disparity_map / depth_from_disparity /
reproject_to_points / elevation_map / segment_objects / ...`.

## Verify, don't trust

- Every op has a worked example; run it (`py -3.11 examples/<id>.py`) — examples
  assert ground truth and print PASS.
- Honest-disclosure notes in docstrings (units, approximation limits, fail-soft
  values) are normative: respect them in generated code.

## Showing results to a human

Launch Fullseye Studio (`py -3.11 studio.py`) to display images / 3-D results in
graphics windows the user can inspect; programs can open and place multiple windows
(`dev_open_window` etc. — see `docs/HDEVELOP_DEV_OPS.md` and `docs/STUDIO_GUIDE.md`).
