<!-- i18n-source-sha: 9fa4a77c68d2 -->
# Fullseye Unified Interface — Requirements Specification (v0.1, 2026-08-18)

[日本語](./UNIFIED_API_REQUIREMENTS.md) · **English**

> Requirements specification based on the direction from 2026-08-17–18. Canonical policy = raptor memory
> `project_fullseye_mission_unified_vision_2026_08_18`, gap analysis = `EVIS_VISION_OSS_GAP.md`.
> This document defines the **what and why** (requirements). The **how to build it** (implementation) comes from design/spike after this document is agreed.

## 1. Background and Purpose

Fullseye = **a comprehensive library that holds every image-processing/vision algorithm as a "skill" and makes it immediately usable**
(= a dedicated HALCON). The goal is **HALCON-class coverage** (measured 979/2313 = 42.3% (2026-09-06), growing `HALCON_COVERAGE.md`).
Currently, the algorithms are split across three separate interfaces, so they **cannot be called consistently from the user side (humans, Studio, evis vision, agents)**. The purpose of this work is to **unify the interface for using them**, so that every algorithm can be discovered, called, introspected, and exposed in Studio in the same natural manner.

## 2. Target Users and Use Scenes

| User | Scene | Implication |
|---|---|---|
| **The user (human)** | Hand-writing in REPL / scripts, using it for work | ★**Sample code that looks natural to a human** (top priority) |
| **Fullseye Studio** | Grasp/test ops and tune parameters from a GUI | Operate the same op consistently from the GUI too (needs introspection/meta) |
| **evis vision pipeline** | stereo→cloud→6D pose→(MoveIt2)→muscle realization | Assemble perception ops with a unified I/F |
| **Agents/automation** | Enumerate and execute ops programmatically | Discoverable (registry), types/meta machine-readable |

## 3. Scope

**In**: Put image-processing ops (currently 654 in the registry) + vision/perception ops (currently 116 in the facade) onto a unified I/F.
Both hand-written numpy implementations and OSS adapters use the same I/F. Studio exposure. Unification of introspection/meta/honest gate.
**Out**: General-purpose CS (algo-c: sort/CRC/Huffman/palindrome = 39 ops. Not image/vision knowledge = out of scope, frozen).
Re-implementing OSS internals (PCL/grid_map/OpenCV/MoveIt2 sit behind thin adapters; don't reinvent).

## 4. Current State and Issues (measured 2026-08-18)

Split across 3 layers and 3 conventions:

| Layer | Count | Current call | Naturalness |
|---|---|---|---|
| Image registry | 654 | `apply(image, "gaussian", a=0.5, b=0.5)` = **string name + generic 2 knobs a/b** | ✗ Most unnatural (encoding for evolution) |
| algo (out of scope) | 39 | `run_algo("name", seq)` = string dispatch | ✗ (but off-mission) |
| Perception facade | 116 | `fs.disparity_sgm(left, right, max_disp=16, ...)` = named arguments | △ Relatively natural but no registry/introspection |

- **No single op discovery/registry that spans the layers** (only images have a REGISTRY; perception is plain functions).
- **Call conventions are asymmetric** (evolution's a/b 2 knobs vs named arguments).
- **How meta (in/out types, doc, honest gate, provenance) is held differs per layer, or is absent**.
- The existing 770 ops (654+116) must be migrated **without breaking them** (backward compatibility).

## 5. Functional Requirements

- **F1 Unified call**: Every op can be called in the same natural manner. Image ops have **meaningful named arguments**
  (don't expose the raw evolution a/b to the user side).
- **F2 Unified discovery (registry)**: A single index that can enumerate, search, and categorize ops across the layers.
- **F3 introspection/meta**: Each op holds, machine-readably, name / input-output types / parameters (name, type, default, range) / doc / provenance /
  honest-gate state (Studio and agents use the same meta). **+ Render hints** (how to visualize the output
  in Studio: `image` / `point_cloud` / `pose` / `grid_map_layer` / `scalar`, etc.), so that
  Studio can automatically select RViz2-equivalent 3D/2D rendering.
- **F4 OSS/sim adapter contract**: Ops that hold OSS (PCL/OpenCV/grid_map, etc.) behind them also appear via the same I/F satisfying F1–F3.
  When OSS is absent, an explicit error or a hand-written fallback (optional-extras policy). **sim sources** (`sim.MuJoCo`/`sim.Gazebo`/
  `sim.IsaacSim`) also follow the same contract, feeding inputs to vision ops through common verbs (`.frames()`/`.depth()`/`.intrinsics()`/`.ground_truth()`)
  (ops can be assembled regardless of the input source; ground_truth is the truth source for honest evaluation).
- **F5 Composition**: Ops can be pipelined and chained (image chains / perception stages).
- **F6 Studio exposure**: From the same meta (F3), Studio can auto-enumerate ops, generate parameter UI, and execute them.
  **Studio = a fusion of HDevelop (2D image-processing IDE) + RViz2 (3D perception visualization)**: in addition to a 2D image panel,
  display point clouds / depth / 6D pose axes / TF tree / grid_map layers in 3D (auto-selected via F3's render hints).
  The 3D viewer is not reimplemented; an existing one (Open3D/RViz2 integration or thin rendering) sits behind it.
  **★ Domain separation (user request 2026-08-18)**: Studio presents ops/samples **cleanly split** into 2 domains ──
  **vision (vision ops = what fullseye "computes")** and **sim-source (what physics "supplies": RGB/depth/
  LiDAR/truth)**. This division of labor (fullseye does not do physics = same as F4/gap analysis) must not be collapsed in the UI either
  (tabs/category separation). **Both domains attach executable sample code to each entry**
  (Qt-style, natural for a human to read. In Studio you can "see it, read the code, and run it on the spot").
  Seed = `spikes/studio_sample_catalog.py` (vision: image.chain / cloud.perceive, sim-source: sim.lidar /
  sim.to_vision. Each sample has name/domain/summary/**code**/run = a mini version of F3 introspection).
- **F7 Backward compatibility**: Don't break the existing 770 ops and the current API (`apply`/facade functions) (the unified I/F is a thin layer on top).

## 6. Non-Functional Requirements

- **N1 Human readability (top priority)**: Sample code reads naturally. **Reference a Qt-style toolkit design** (§7).
- **N2 discoverable**: Namespaces, consistent naming, IDE completion works.
- **N3 Self-contained**: The basics run on stdlib+numpy. Only heavy pieces (GPU SGM/deep pose) are optional extras.
- **N4 Coverage**: Use the HALCON coverage map (`HALCON_COVERAGE.md`) / ROS2 standards (PCL/grid_map/image_pipeline)
  as **a map of the gaps**, with a structure that can grow coverage on the unified I/F.
- **N5 Verifiability**: Keep the honest gate (reference == independent oracle; C-codegen family is bit-exact) on the unified I/F too.
- **N6 Fidelity**: Match naming/behavior to the practical vocabulary and semantics of OSS/ROS2 (low transfer-learning cost).

## 7. API Design Policy (Qt-style, natural for a human to write)

**Bad example (current)**: `apply(image, "gaussian", a=0.5, b=0.5)` / `run_algo("name", seq)` = machine-oriented string-dispatch.

**The naturalness we aim for (proposal; needs user judgment in §9)**:
```python
import fullseye as fs
# Chain on a core object (image ops): reads like a sentence
edges = fs.Image.load("scene.png").to_gray().gaussian(sigma=1.4).sobel()
# Namespace module + config object + verb method (perception ops): Qt-widget style
depth = fs.stereo.SGM(max_disp=128, window=5).compute(left, right)
cloud = fs.camera.Pinhole(K).backproject(depth)
plane = fs.pcseg.PlaneRANSAC(thresh=0.01).fit(cloud)
```
Borrowed from Qt: **namespace modules** (`fs.stereo`/`fs.camera` = QtWidgets-style), **config object + verb method**
(`.compute()`/`.fit()`/`.apply()`), **chaining on a core object** (`Image`), **sensible defaults**, and
**discoverable**. String names / raw registry / evolution's a/b are **hidden behind the scenes**.

## 8. Constraints and Premises

- Don't break the existing 770 ops and the evolution engine (the op registry is the foundation of evolution) → the unified I/F is **a layer laid on top**.
- Don't reinvent OSS (thin adapters). Don't include general-purpose CS (algo-c).
- Classification/naming is faithful to the practical vocabulary of HALCON/ROS2 (N6).

## 9. Needs User Judgment (want to settle before implementation)

1. **Image op manner**: **Chaining** with `fs.Image(...).sobel()`, or unify on the same **config-object approach** as perception?
2. **Execution model**: **eager** (immediate compute; suited to REPL/Studio), or **lazy pipeline** (finalized with `.run()`)?
3. **Naming**: HALCON-leaning vocabulary (`dyn_threshold`, etc.), or general vocabulary (`adaptive_threshold`)?
4. **Studio exposure**: Include it in the first spike, or lead with the Python API?

## 10. Acceptance Criteria (the unified I/F's "done")

- Image ops and perception ops can be called in the **same natural manner** (samples are natural, Qt-style).
- All ops are discoverable in a single registry and hold F3's meta (shared with Studio).
- The existing 770 ops / current API are not broken (0 regressions).
- An OSS adapter works via the same I/F in at least 1 example (e.g., stereo or pcseg with PCL/OpenCV behind).
- The honest gate runs on the unified I/F too.

## 11. Phased Plan (proposal)

1. **Agree on this requirements spec** (the 4 judgments in §9).
2. **Design + a small spike**: `Image` chain + one perception module (e.g., `fs.stereo`) as **thin wrappers** over existing implementations. Additive, 0 regressions.
3. **Unify meta/registry** (F2/F3) → put existing ops on it in stages.
4. **Studio exposure** (F6).
5. **Prove the OSS adapter contract** (F4) in one domain (stereo=image_pipeline / pcseg=PCL).
6. **Grow coverage** (N4; fill gaps in the HALCON/ROS2 map with an honest gate attached).

## 12. Decision Log

- **2026-08-18 Agreed on the requirements spec (user)**. The 4 judgments in §9 adopt the defaults:
  ① **Mixed** (image = `Image().gaussian()` chain / vision = `stereo.SGM().compute()` config object)
  ② **eager** ③ **general vocabulary primary + HALCON aliases** ④ **Python API first** (Studio is the next stage).
- **F1 realization policy = approach B (single implementation)**: The natural API calls the lower layer (scipy.ndimage, etc.) **directly with natural parameters**
  (gaussian is `ndimage.gaussian_filter(v, sigma)` = the same lower layer as the evolution op, so no drift). The evolution registry's
  generic a/b knobs (normalized, bounded encoding for search; e.g., `sigma=0.3+2.7*a`) are **not leaked into the human API's parameter ranges**;
  they remain only in the `Image.op(name, a, b)` escape hatch to access the long tail of 654 ops.
- **Spike proven**: `spikes/unified_api_spike.py` (image chain + vision config object + long-tail escape).
  Existing 809 ops unchanged, additive. pcseg RANSAC detected 400/400 points of a synthetic plane as inliers = confirmed real delegation.

- **2026-08-18 F1/F2/F3 implementation complete (the unified vision I/F body) = `unified.py`**:
  Put the **600 HALCON facade ops** implemented this session (genuine numpy, `data/halcon_facade_map.json`)
  onto a **single registry + introspection meta + chapter-wise namespaces**. Additive; the existing ops / evolution registry /
  fullseye package facade were not changed at all (F7).
  - **F2 unified discovery**: `Registry` (`ops`) indexes 600 ops across layers. `ops.find(q)` (full-text search over name/doc/chapter) /
    `ops.list(namespace=…)` / `ops.stats()`.
  - **F3 introspection**: Each op is a `UnifiedOp` (name / the implementation function's **natural signature** (inspect) / primary chapter /
    namespace / doc / **render_hint** (image/region/contour/pose/point_cloud/matches/scalar/matrix) / provenance).
    `ops.describe(name)` returns a machine-readable dict (shared by Studio/agents). **Render hints are the 2D/3D
    auto-render selection meta of F6 (Studio)**.
  - **F1 natural call**: **17 chapter-wise namespaces** (`contour`/`calib`/`recon3d`/`region`/`match`/`transform`/
    `filter`/`image`/`tools`/`object3d`/`match3d`/`segment`/`measure`/`metrology`/`morph`/`matrix`/`inspection`).
    E.g., `u.calib.camera_calibration(obj, views)` recovers the true K via Zhang calibration. The evolution a/b are not exposed
    (each op has natural named arguments).
  - **fullseye integration**: Additive exposure in `fullseye/__init__.py` → `fs.vision.<ns>.<op>(...)` / `fs.vision_ops`.
    Coexists with the evolution REGISTRY (735) and the perception facade (fs.stereo, etc.).
  - **Verification**: Working demo `spikes/unified_vision_demo.py` (runs F1/F2/F3/F7 live). Test `tests/test_unified.py`
    9 pass. Regression `test_op_contracts` 3113 pass 0 fail (F7 confirmed).
- **2026-08-18 F6 Studio exposure implementation complete**: From the unified registry (`fs.vision_ops`), Studio **auto-enumerates 600 ops,
  auto-generates parameter UI, executes, and auto-selects rendering** via 2 primitives in `spikes/studio_ops_browser.py`:
  - **`render_by_hint(result, hint, fig)`** = **auto-select 2D/3D rendering** by F3's render_hint (image=imshow /
    region=mask / contour=lines / point_cloud=3D scatter / pose=RGB axes / matrix·scalar·matches=cards). All 8 kinds verified.
  - **`synthesize_args(op)` / `scalar_param_specs(op)`** = build synthetic inputs and slider specs from F3's **natural param names**
    (the param name carries meaning = F1's design pays off). **Honest auto-execution coverage = 364/600 (60%)**
    execute and render immediately on synthetic input alone. The rest are the dedicated inputs that create_* produces (model handles, etc.) (209) + those outside the synthesizer's
    shape heuristic (27), and all of them display an **F3 introspection card** (signature/doc/params/render_hint) =
    all 600 can be "discovered + meta-grasped".
  - **GUI integration** = the tree in `spikes/studio_app.py` **auto-expands `vision-ops (600)` by chapter-wise namespace**;
    selecting an op yields an F3 card + auto-generated sliders + `render_op_into` (slider override→synthetic input→render_hint rendering).
    Coexists with the existing 9 samples (vision/sim-source separation). smoke = 9/9 samples OK + representative op path + coverage display.
  - **Verification** = test `tests/test_studio_ops_browser.py` 7 pass (render_hint 8 kinds · synthetic input · coverage>=300 ·
    override reflected). Gallery `spikes/out_gallery/studio_f6_render_hints.png` (rendering list of the 8 hints).
- **2026-08-18 F2 all-ops single-index integration complete (3-layer merge)**: `unified.py` **integrates 3 layers into a single registry**:
  ① **facade 600** (this session's genuine HALCON implementations) ② **evolution registry 729** (`fs.REGISTRY`, a/b knobs,
  natural caller `(image, a=0.5, b=0.5)` for the long tail, provenance=evolution) ③ **perception facade 240** (`fs.stereo`/
  `pcseg`/`camera`/`terrain`/… public functions, natural signatures, provenance=perception). **Total 1569 ops / 57 namespaces**.
  - **Collision handling**: The facade is registered first = a bare-name collision prefers the genuine facade (preserves existing behavior). Each op has `provenance`.
  - **render_hint**: Evolution ops derive the hint from `out_sort` (image/region/contour/feature/match/volume/color). Perception ops use
    the module default hint. → Studio (F6) auto-renders all 3 layers via render_hint. **Auto-execution coverage 1129/1569 (72%)**.
  - **Circular-import resolution**: Because fullseye reads unified and unified reads fs.REGISTRY/the perception facade, lazy construction
    (PEP 562 `__getattr__`) + publish-before-load makes re-entrancy safe. Works in both import orders.
  - **Verification**: 1569 ops via both `import fullseye`/`import unified`; `fs.vision.smooth.<op>(img,a,b)` (evolution) /
    `fs.vision.camera.intrinsic_matrix(...)` (perception) / `fs.vision.calib.camera_calibration(...)` (facade) can
    be called in the same manner. Test `tests/test_unified.py` 9 pass (verifying 3-layer provenance) + browser 7 pass,
    regression `test_op_contracts` 3113 pass 0 fail (F7).
- **2026-08-18 Studio 3D viewer = Open3D integration implemented (the RViz2-equivalent 3D of F6)**: The `spikes/viewer3d.py` adapter
  converts the unified registry's op outputs (render_hint) into Open3D geometry and shows them in 3 ways (Open3D behind, not reimplemented):
  - **`to_geometries(result, hint)`** = point_cloud→PointCloud (z coloring) + coordinate frame / pose→coordinate frame
    (equivalent to RViz2's pose axes) / mesh→TriangleMesh. **No GL needed = testable**. image/region/contour are empty (→ drawn on the 2D side).
  - **`show_interactive(geoms)`** = Open3D interactive window (mouse navigation = RViz2 equivalent). Runs on desktop GL.
  - **`render_offscreen`** = to a numpy image (if EGL is available). **This Windows machine does not support EGL headless**
    ([[reference_mujoco_gl_remote_desktop]]) → returns None, and **Studio falls back to matplotlib 3D** (graceful).
  - **`export_ply`** = .ply export (no GL needed = always possible; can be opened in external Open3D/CloudCompare). **`ground_grid`** (equivalent to Grid Display).
  - **Studio integration** = an "**Open in 3D (Open3D) 🧊**" button in `studio_app.py`. Enabled when a registry op emits point_cloud/pose
    → click opens an interactive window. Inline continues with matplotlib 3D (because EGL is unavailable). `compute_op` retains the result.
  - **honest**: Open3D is an optional extra (graceful degradation if not installed). **Offscreen is GL-impossible in this environment; the interactive window runs
    on the user's desktop GL** (since it can't be verified in my headless environment, presented as an alternative with .ply + matplotlib preview).
  - **Verification** = `tests/test_viewer3d.py` 8 pass (geometry/PLY/graceful fallback), demo `spikes/viewer3d_demo.py`
    (an evis perception scene = point cloud→object→6D pose, generating .ply + preview PNG; `--show` for an interactive window).
- **2026-08-18 F4 OSS adapter contract implementation complete → all §10 acceptance criteria achieved**: `oss_adapter.py`
  implements the same I/F (config object + verb method) that **puts OSS (OpenCV 4.11 / scikit-image 0.26) behind it and gracefully falls back to genuine numpy when absent**.
  5 adapters:
  - `stereo.BlockMatching` / `stereo.SGBM` (cv2.StereoBM/SGBM ↔ fs.disparity_map/sgm numpy)
  - `filter.Bilateral` (cv2.bilateralFilter ↔ numpy, fallback mean difference 0.012)
  - `features.ORB` (cv2.ORB ↔ Harris numpy)
  - `contour.FindContours` (cv2.findContours ↔ skimage ↔ numpy, circle contour radius 14.3≈15)
  - **Contract**: each adapter satisfies (1) a config with meaningful named arguments (2) a verb method (.compute/.apply/.detect/.find)
    (3) a `.backend` property (opencv/skimage/numpy(fallback)) (4) forced fallback via `prefer='numpy'`.
  - **Unified registry integration**: `unified._load_oss` registers with provenance=oss-adapter → **total 1574 ops / 4 layers**
    (facade 600 / evolution 729 / perception 240 / OSS 5). `fs.vision.stereo.SGBM(max_disp=32).compute(l,r)` (F1),
    with backend shown in `find`/`describe` (F3). In Studio (F6) too, config generation → auto-execution via verb method.
  - **Verification**: `tests/test_oss_adapter.py` 7 pass (both backends / fallback approximation / registry integration).
    Regression unified 9 + browser 7 + viewer3d 8 + op_contracts 3113 = all pass.
  - **All §10 "done" items achieved**: ① image ops and perception ops in the same manner ② all ops in a single registry + F3 meta
    ③ 0 regressions on existing ops ④ an OSS adapter works via the same I/F (5 examples: stereo/filter/features/contour) ⑤ honest gate maintained.
- **Next** (§11-6 coverage expansion and polish): synthesizer per-op input hints (raise Studio auto-execution from 72%) /
  OSS adapter expansion (watershed/SIFT/PnP, etc.) / continue naturalizing the API of the 654 image registry / make Studio 3D routine on the desktop.

- **2026-08-19 F5 composition implementation complete (pipelining ops) = `unified.py`**: Implemented §7's 2 forms conforming to a single registry (F2) + F3 meta.
  - **`Pipeline`** (generic): `pipeline('median', ('step_edges', {'min_rise':0.008}))` arranges stages, flowing the previous stage's output into the next stage's first argument.
    Op name/`UnifiedOp`/raw callable are resolved by `_resolve_op`. `run(x, trace=True)` also returns intermediate outputs.
    **introspection**: `steps` / `render_hint` (final stage) / `describe()` (per-stage F3 meta + bound kwargs) = shared by Studio/agents.
  - **`Image`** (§7 "like a sentence"): `fs.Image(arr).median().sobel_amp().invert()` ── resolves an attribute to a registry op name,
    applies it to the current array, and **returns a new Image (immutable)**. For tuple output (elevation_map→(grid,extent)), the leading ndarray becomes the chain's value. `history` for the applied sequence.
  - **Perception stages** = the same mechanism as image chains (elevation_map→slope_map→step_edges). The same flow as walker2d visual-adaptation perception, expressed as composition.
  - **honest UX**: An unknown op is an explicit error with candidates (`Image`→AttributeError / `Pipeline`→KeyError).
  - **F7**: The fullseye facade is unmodified. `fs.Image`/`fs.Pipeline`/`fs.pipeline` are exposed at top level (also available via `fs.vision.*`).
  - **Verification**: demo `spikes/unified_pipeline_demo.py` (① image chain ② perception stages ③ introspection ④ Image==Pipeline agreement).
    Test `tests/test_unified_pipeline.py` 9 pass. Regression `test_unified`+`test_op_contracts`+`test_oss_adapter` = **3129 pass 0 fail** (F7).
  - **State**: F1/F2/F3/F4/F5/F6/F7 = **all functional requirements implemented**. What remains is §11-6 coverage expansion and polish (sim-source adapter / synthesizer expansion / continued API naturalization).

- **2026-08-19 §11-6 polish, 3 items complete**:
  - **sim-source adapter (the unimplemented side of F4) = `sim_source.py`**: the same contract by which a physics sim supplies inputs to vision ops
    (config + verb + `.backend`/`.available` + raise when absent). **MuJoCo supplies for real, headless**:
    `.intrinsics()` (fovy→K) / `.rgb()` / `.depth()` / `.ground_truth()` (truth source) / `.point_cloud()` (depth back-projection→world point cloud).
    **The sim→vision bridge is proven**: `MuJoCo(xml).point_cloud('top')` → perceives block height with `fs.elevation_map`.
    Gazebo/IsaacSim are honest scaffolds (`available=False`; verbs raise explicitly). Registered in the unified registry with namespace `sim`/
    provenance `sim-source` (`_load_sim`). Test `tests/test_sim_source.py` 8 pass.
  - **synthesizer expansion (raise F6 auto-execution rate) = `spikes/studio_ops_browser.py`**: added synthesizers (video/cube/volume/mask/
    mesh V,F/grid/dst/uv/correspondence points/matrix list/scalar). **Auto-execution coverage 72%→79% (1139→1249/1580, +110 ops)**.
    The remaining ~331 are model (heterogeneous: MjModel vs metrology handle) / path (IO boundary) / single-character ambiguity (u/B), **honestly capped** (don't fabricate).
  - **Naturalizing the evolution layer's API (F1) = `unified.py`**: the evolution op's (v,a,b) natural signature becomes **just `op(image)`** (the search knobs
    a/b unexposed). a/b are kept as a keyword-only escape hatch (adjustable via `op(image, a=0.2)` = expressiveness unchanged).
    `describe('median')['signature']` = `median(image)`.
  - **Regression**: `test_unified` (added sim-source to valid provenance) + `test_op_contracts` = 3122 pass. New-feature tests total 40 pass.

- **2026-08-19 Making Studio 3D routine on the desktop (the 3D side of F6) = `spikes/viewer3d.py` + `viewer3d_launch.py`**:
  Currently `_open3d` **blocks Qt** via `draw_geometries` (Studio freezes until the 3D window is closed) = not usable routinely.
  - **Separate-process launch `launch_detached(geometries, title)`**: writes geometry to a temporary PLY bundle (`save_scene`/`load_scene`) and
    **launches `viewer3d_launch.py` detached** (pythonw + DETACHED|CREATE_NO_WINDOW = no console flash).
    Studio returns immediately and **doesn't freeze** / GL crashes are isolated to the child process / multiple windows possible. Measured: parent exits immediately (exit 0); the child pythonw owns and keeps the GL window alive.
  - **Routine-usable quality `show_interactive`**: updated to the Visualizer API (dark background / point_size 3 / world origin axes / an easy-to-read initial view front-up-zoom).
  - **Avoid mojibake in Japanese titles**: pass the title via a **manifest (UTF-8)** (`scene_title`) rather than argv.
  - Switched `studio_app._open3d` to `launch_detached` ("launch in a separate process; Studio operation can continue").
  - Full-path demo sim→vision→3D: a MuJoCo sim-source point cloud of 56824 points displayed in a desktop 3D window (separate process).
  - Added save/load round-trip · UTF-8 title · empty→False to `tests/test_viewer3d.py`, total 11 pass.

- **2026-08-19 Studio 3D window management + displaying models in their real shapes**:
  - **`viewer3d.ViewerManager`**: tracks open 3D windows (separate processes), lists them (liveness pruning), closes them individually/all.
    Added a window-manager UI to Studio (list QListWidget / close selected / close all / refresh / environment-status label),
    and `_open3d` launches under tracking via `viewer_mgr.launch`. **Simultaneous management of multiple windows measured** (launch→list→individual/all close).
  - **`sim_source.MuJoCo.scene_geometries()`**: turns MuJoCo geoms into **real-shape Open3D meshes** (sphere/box/capsule/
    cylinder/ellipsoid/mesh with world transforms and color; plane/hfield skipped). **evis/rocket and other models can be seen in a 3D window
    in their actual form**. Measured: meshed walker2d walking 7 geoms / rocket 7 geoms and displayed them in a separate-process window.
  - Tests: `test_viewer3d` (ViewerManager lifecycle · launch failure) + `test_sim_source` (scene_geometries) added, total 22 pass.

- **2026-08-19 Goal "Studio feature expansion" batch**:
  - **Posture animation playback** (watch the rollout's qpos trajectory as motion) = `sim_source.save_animation/play_animation/launch_animation`
    + `spikes/anim_launch.py`. Each frame updates only qpos→mj_forward→each geom's world transform (reusing meshes), playing back
    in an Open3D window. **Rocket landing (400 frames, soft 0.83m/s) played back in a separate-process window** measured. `ViewerManager.track`
    also brings externally launched processes under management.
  - **op search/filtering**: a search box on Studio's left; `_populate_tree(filter)` filters 1580 ops instantly by name/doc/namespace (`reg.find`)
    (the total of expanded namespaces = the number of matches, measured to agree).
  - **sim-source panel**: display any MJCF in a 3D window via "see in real shape (scene_geometries)" / "see as point cloud (point_cloud)"
    (F6 sim domain, managed by viewer_mgr).
  - **Result saving**: 3D output→PLY, 2D figure→PNG (`export_ply`/`savefig`).
  - Regression: all related 56 pass + 3137 pass including op_contracts. studio_app/anim_launch/sim_source syntax OK.

## 3DGS (3D Gaussian Splatting) support — first half (data acquisition) complete 2026-08-19

**Question**: Can 3DGS be done with Fullseye/sim-source?

**Measured environment**: RTX 5090 (32GB) present / torch=**2.11.0+cpu** (CPU build) / CUDA toolkit · gsplat · nerfstudio **not installed**. → Training (GPU) is currently impossible; the stack needs setting up.

**sim-source's advantage**: The biggest front stage of 3DGS = camera-pose estimation from multi-view images (COLMAP) is **unnecessary in sim, because the ground-truth pose is available directly**.

**Implementation (GPU-free, verified on CPU)**: `sim_source.MuJoCo`
- `camera_to_world(cam)` / `extrinsics(cam)` — the MuJoCo camera frame follows the OpenGL convention (-Z forward / +Y up) = identical to nerfstudio's `transform_matrix`.
- `project(pts, cam)` — pose self-verification. **top camera reprojection diff 0.0000**, oblique 0.0034 (the residual is explained by occlusion).
- `save_gsplat_dataset(out, cams)` — named cameras → `transforms.json` (PINHOLE) + `images/`.
- module function `capture_orbit(base_xml, out, n_views, radius, elevation_deg, lookat, fovy, ...)` — injects a ring of multi-views into the XML and turns them into c2w via the verified cam_xpos/cam_xmat path. **All 12 views have a lookat-reprojection center offset of 0.000px**, real rendering confirmed, depth can be bundled.
- test: `test_camera_pose_reprojection_exact` / `test_capture_orbit_dataset` (test_sim_source 13 passed).

**Remaining (GPU half, needs judgment)**: setting up the training stack. On Windows there is friction with gsplat's CUDA build (VS build tools+CUDA toolkit). Candidates = (A) torch cu128+gsplat in a dedicated venv / (B) via WSL2 / (C) keep only the exporter and hand transforms.json to an external trainer (`ns-train splatfacto`). A dedicated environment is recommended to avoid affecting the shared py -3.11 env.

### Second half (GPU training) measured 2026-08-19 — end-to-end success with pure-torch 3DGS

**gsplat native verdict**: GPU works with torch 2.11.0+cu128 (RTX 5090 / capability(12,0)=sm_120). gsplat 1.5.3 can be imported, but the CUDA kernel, on its first JIT build, gives **"No CUDA toolkit found. gsplat will be disabled"**. nvcc/cl absent, and no prebuilt Windows wheel for cu128 either (pt2.7/2.8/2.9/2.11 all fail). → gsplat native requires CUDA Toolkit 12.8+VS Build Tools (not installed).

**Workaround = pure-PyTorch 3DGS (`gsplat_torch.py`)**: a compiler-free reference splatter (quat→R / 3D covariance→2D Jacobian projection / global-depth-sorted alpha compositing). OpenGL c2w to a CV camera via F=diag(1,-1,-1).
- Single Gaussian: rendered ±0px at image center (projection verification).
- Initialized a sim orbit of 12 viewpoints (10 train/2 test) with a colored point cloud of 2500 gaussians → Adam 300 iter.
- **Novel view (hold-out) PSNR: init 14.45 → 300iter 26.03 dB** (train 27.33). **48 it/s, 6.2s**. Visually too, the green box/blue capsule/red sphere are correctly reconstructed.
- Pose is the sim truth (capture_orbit) = COLMAP-free. test is an unlearned camera = generalization, not memorization.
- CPU regression `tests/test_gsplat_torch.py` (4 passed, math only). GPU training in venv `.venv-gsplat` (the shared py -3.11 is unchanged).

**Remaining**: making gsplat a fast backend (install CUDA Toolkit+VS Build Tools or WSL2) / densify · prune / SH color / SSIM loss. Pure torch is for PoC (non-tiled, slow at large scale).

### 3DGS productionization batch 2026-08-19 — trainer/real scene/CLI/Studio/article

- **Trainer `gsplat_train.py`**: SSIM+L1 loss, adaptive densify (clone high gradients)/prune (low opacity + huge floaters), early-stopping on hold-out best, turntable rendering. CPU regression `tests/test_gsplat_train.py` 4 passed.
- **Real scene**: `sim_source.orbit_scene`/`capture_orbit_scene` (camera injection with MjSpec = supports real MJCF with assets). go2 (Menagerie) at **novel-view PSNR 26.49dB (train 26.99 keeping pace = overfitting resolved) / 7978 gaussians / 61.7s** on RTX 5090.
- **Honest failure and fix**: the first 18 views degraded test 23.6→19.5 (overfitting). → improved to 26.5dB with 36 views + floater prune + early-stopping. The failure curve is included in the article.
- **CLI `gsplat_cli.py`**: `<scene.xml|builtin> <out>` runs capture→train→turntable.gif/novelview.png/gaussians.npz/report.json. builtin: go2/cassie/apollo. End-to-end measured (exit 0).
- **Studio wiring**: "3DGS training 🎇" in the sim panel = launch the venv's gsplat_cli as a separate process via QProcess → open the full-orbit GIF on completion (Studio non-blocking). Syntax OK (Qt not run headless).
- **gsplat native**: even after installing VS BuildTools, the VCTools workload (cl.exe) needs UAC elevation and can't be installed unattended. nvcc (CUDA13.3) is installed but cl is absent + a version mismatch with torch cu128 (12.8). → native is on hold; completed with pure torch.
- **Article**: `docs/articles/qiita_3dgs_sim_native.md` (glossary-first/honest/failure included) + `psnr_curve.svg` (overfitting vs fix).
