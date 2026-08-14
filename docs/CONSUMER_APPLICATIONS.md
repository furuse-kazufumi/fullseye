# Fullseye — per-project applications (honest, 2026-08-15)

What **Fullseye** (working name imgevolve — the HALCON-parity op library + Physical-AI
perception stack, all classical / numpy-scipy, **no learned models**) can concretely do
for each FullSense-family project. Derived per-project from each project's brain file by a
parallel analysis pass, then verified. Honest tiers: **high** = core direct fit, **medium**
= useful adjunct, **low** = marginal, **none** = no honest fit. This is the detail behind the
one-line `★Fullseye応用` note in each project's `claude-projects.json` next_plan.

Capability catalog: [`docs/PERCEPTION_PHYSICAL_AI.md`](PERCEPTION_PHYSICAL_AI.md) (perception
modules) + [`docs/STATUS.md`](STATUS.md) (op waves incl. `backends_tomo` FBP, `vol_*` 3D CT).

## high

### xct — sparse-view 2D X-ray → 3D CT
`backends_tomo` (radon forward / FBP / SART / unfiltered-BP / sinogram-denoise) is the classical
baseline layer of XCT itself: simulate a sparse-view sinogram → FBP (streaks appear) → SART /
iterative, all on the home CPU (matches the next_plan "reproduce ASTRA/TIGRE FBP+iterative on
public data"). `volio.read_volume` (DICOM series / NIfTI / NRRD / MetaImage, raw HU preserved)
loads public CT (LoDoPaB-CT, Walnut) into the `volume` sort; `backends_physics` TV-flow (the
standard compressed-sensing TV regularizer) + sinogram-denoise as preprocessing; and the
reconstructed 3-D volume is evaluated with `volops` (`vol_frangi`/`vol_sato` = tube/fiber
enhancement, `vol_label`/`vol_count` = defect counting for NDT/micro-CT, `vol_gradient_magnitude`,
MIP/slice viz). **Honest limit:** Fullseye's FBP/SART is a CPU parallel-beam classical
implementation — Walnut's cone-beam geometry and GPU-scale reconstruction need ASTRA/TIGRE/LEAP,
and the real objective (learned/optimization priors: R²-Gaussian / NAF / diffusion) is out of
scope for classical-only Fullseye. Fullseye covers the *classical baseline + data I/O + 3-D
volume evaluation* front half, not the sparse-view prior itself.

## medium

### onocollo — CPU world-models toolkit
The learning core (V/M/C, Dreamer, RL controller) is learned and cannot be replaced by
classical Fullseye. Two honest touch-points, both **evaluation/verification**: (1) gaitlab
locomotion static stability straight from MuJoCo state via `locomotion.support_polygon` /
`com_support_margin` (is the COM inside the foot support polygon) / `contact_points` /
`gait_phase` — feeds the "forward progress is foot-referenced, no dive cheat" honest-gait
discipline directly. (2) physics-render video motion verification via `sceneflow.time_to_contact`
/ `looming` / `focus_of_expansion` / `scene_flow` (+ optical flow) to quantify "did it really
approach, what is the 3-D speed" (aligns with the evis physics-video cheat detection).
`terrain.elevation_map`/`foothold_candidates` assume a depth input and the sim has ground-truth
state, so their role is thin here.

### onocollo-complete (hillco) — body-language model (evis)
MuJoCo state (qpos / contacts / COM) is known, so the stereo→depth→cloud→ppf-6DoF→grasp
perception chain is mostly redundant. Two honest fits: (1) `locomotion.support_polygon` /
`com_support_margin` / `gait_phase` (McGhee&Frank, Alexander) as a *literature-grounded
independent double-check* of the COM–support-polygon margin the QP already computes — backs up
track E ("frontal-plane / lateral stabilization is the real problem"); `com_from_silhouette`
gets COM from the skeleton-viewer's rendered pose. (2) run `sceneflow.time_to_contact` / `looming`
/ `scene_flow` + `flow` (`focus_of_expansion`) and `features.match_keypoints` /
`odometry.integrate_trajectory` on the video gallery (hillco_media mp4s, labeled achieved/failed)
to quantify from the image side whether forward motion is real or a "dive cheat" — a refutation
tool for `feedback_honest_gait_foot_based_progress`. Track D ("hill climbing") can reuse
`terrain.foothold_candidates` / `slope_map` / `step_edges` for foot placement, but the heightfield
is known so it stays a helper. No learned detector → cannot do chopstick object/pose recognition;
`grasp.force_closure` is already self-implemented in the QP so replacement value is thin.

### ossa — own anatomically-correct skeleton platform
The core (MuJoCo physics + MJCF + mass/inertia) is not perception, so Fullseye's core fit is thin,
but the current next_plan's manual "drape CC0/CC-BY bone meshes on each body, match scale/orient"
can be automated: sample points from both the mesh and the parametric solid surfaces, take
principal axes + extent with `pcseg.principal_axes` / `pcseg.obb` / `aabb` for a coarse
orientation+scale, initialize with `registration.pca_align`, then refine the rigid fit with
`registration.icp` / `point_to_plane_icp` (or `kabsch` if correspondences are known), with
`pcseg.farthest_point_sampling` to keep it light. A secondary, speculative angle: to get an
"owned" bone shape without mesh-license constraints, cut bone from public CT via `vol_label`
(3-D connected components) or `backends_tomo` FBP — but ossa deliberately chose a scan-independent
parametric route, so this is investigative. (No learned detector/segmenter in Fullseye.)

### mcp-3d — 3D / spatial-asset MCP server
The core (spatial-asset schema, Python/TS SDK, MCP interop) is out of scope, but the
demo/reference-implementation layer and the v3 perception plans fit directly: depth-image assets
→ `camera.depth_to_points` + `normals_from_depth` → point cloud, and demo_depth_seg /
demo_segmentation replaced/strengthened by `pcseg.fit_plane_ransac` / `remove_ground` /
`euclidean_clusters` / `obb`. The v3 hand-written `triangulator.py` (2-ray intersection +
reprojection error) maps to `camera.triangulate` / `solve_pnp` / `recover_pose`; event→3-D
tracklet motion evidence maps to `features.match_keypoints` frame correspondence +
`sceneflow.time_to_contact` / `looming` / `scene_flow`. (Classical only — no learned detector,
so true DVS-event detection itself is out of scope; contribution is the reference-impl layer.)

### fullsense — umbrella brand + portal/articles
The LLM triad (llmesh/llive/llove) and the portal need no perception (the real destination for
the perception stack is the physical-AI children onocollo/evis/hillco, which are high). But the
evis/onocollo/hillco physics-AI demo-article stream that dominates the next_plan benefits
concretely: run `sceneflow` (`focus_of_expansion` / `time_to_contact` / `looming` / `scene_flow`)
+ `features.match_keypoints` + `odometry.integrate_trajectory` on MuJoCo-rendered physics-video
frames to independently measure "did it really move forward/approach, what is the 3-D speed" —
backing the honest-disclosure discipline (slip / dive-cheat detection) and doubling as quantified
article figures. Walking articles: `locomotion.support_polygon` / `com_support_margin` /
`gait_phase` + `terrain.foothold_candidates` to chart the stability margin; `apply` / `run_pipeline`
image ops to enhance / edge-extract / annotation-overlay demo frames into illustrations. (No
learned detector, so recognition/segmentation is out.)

## low

### manga-md-poc — declarative manga → self-contained SVG
Core (declarative DSL → vector SVG) and the north star (VLM manga understanding = "glasses" layer)
are both outside Fullseye's domain (understanding needs learned models Fullseye lacks). The honest
angle is raster asset preprocessing only: convert embedded photos to a manga look via
`apply`/`run_pipeline` (NPR `xcv_stylization`/`pencil`/`edge_preserving`, Sobel/Canny line art,
posterize/solarize/emboss/contour, threshold binarize / halftone), and bridge raster sketches to
the DSL by contour extraction (`threshold_sub_pix`) → Douglas-Peucker simplification
(`backends_xldgeom`) → DSL polygon/spline coordinates. Both are art/asset helpers, not the L0
rendering core; fit is thin.

### llmesh — on-prem secure LLM hub
No image/vision requirement in the brain file → no core fit (honestly marginal). The one realistic
seam is the industrial-IoT/SPC junction: use Fullseye as a *classical machine-vision inspection
edge node* whose operator net (`apply`/`run_pipeline`: blob/edge/threshold/morphology/measure; CT
via `vol_frangi` or `backends_tomo` FBP; dimensional via `pcseg` `fit_plane`/`cylinder_ransac`)
produces numeric metrics (defect rate, dimensions) that llmesh's SPC monitors and MQTT/OPC-UA
transports. But llmesh itself moves data, it does not process pixels — this is an auxiliary
sensor-side role, not a core llmesh need.

### raptor — security research framework
Core (source analysis, fuzz, exploit, SCA, OSS forensics, Mermaid diagram gen) is text/code, so
image processing barely applies; CAPTCHA/visual OCR need learned models, impossible for
classical-only Fullseye. Two realistic angles (both extension *proposals*, not current brain
needs → low): (1) `/web` `browser_agent.run_full_scan` screenshots → n-ary `abs_diff`/`sub_image`
+ threshold + connected/region features to localize a defacement diff; `match`-sort template
correlation to compare a phishing page against a brand reference. (2) a new "image forensics"
capability: `estimate_noise` (noise residual), `fft_image`/DCT spectrum, pywt subband/detail-energy,
`cooc_feature_matrix` (Haralick texture) for steganalysis / resampling-trace / tamper detection.

### llove — TUI dashboard / HITL workbench
Fit is thin. llove is a Textual TUI/HITL workbench (LLM game arena + real LLM runtime + terminal
SVG/Mermaid/Markdown rendering) with no camera/depth/cloud input surface; the whole physical-AI
stack is irrelevant. The one realistic angle is the generic image-op layer (620 ops via
`apply`/`run_pipeline`) for terminal-preview raster preprocessing — resize/resample, RGB→palette
color quantization, grayscale, Sobel/Canny/threshold → dropping an image or an animated-SVG static
frame onto terminal cells (block chars / ANSI color / ASCII art). But llove renders vectors
(SVG/Mermaid) primarily; raster display is not a stated need, so this is hypothetical.

## none (honest — no fit)

### browser-use-project
No fit. Despite the directory name ("browser-use / browser automation"), the actual project is an
**Alpaca paper-trading stock bot** (remote=alpaca-trading-system): screener / strategies (MA/RSI/BB/
XGBoost) / risk (VIX, HMM) / autotrader + Perplexity·DuckDuckGo research + Telegram. All decisions
are on OHLCV numbers (DuckDB/numba); no images, screenshots, DOM, depth or clouds are handled, so
neither Fullseye's perception stack nor its 2-D op library has a real need. Financial time series
is outside Fullseye's classical-image scope. (The only far-fetched angle — running edge/threshold
on the chart PNG `alpaca_chart_cmd.py` emits — is post-processing a human/Telegram *output*, not an
input.) tier = none.

### 2ndbrain
No fit. 2ndBrain is Obsidian-Canvas / knowledge-graph text tooling (.canvas JSON, nodes tied to
vault markdown, named edges, capture→mature→organize→visualize loop, global recall skill); no
images, depth, clouds or camera geometry appear. Every Fullseye module targets pixels/depth/3-D
points and it has no graph-layout or NLP function, so no function matches a real need. (The only
contrivance — reusing `occupancy_grid_2d` + `inflate_obstacles` + `clearance_map` to lay out Canvas
nodes without overlap — is a robot-nav primitive misapplied; a force-directed graph-layout library
is the right tool.) tier = none.

## none/marginal (LLM / loop / terminal — assessed inline)

- **llive** (self-evolving modular memory LLM framework) — **none**: no visual input surface; at most
  `apply`/`run_pipeline` to render evolution-benchmark figures.
- **llcore** (Transformer core evolution × Z3 verifier) — **none**: pure LLM/formal-methods research,
  no image processing role.
- **llloop** (MAPE-K loop engineering environment) — **none**: a control-loop / safety-layer framework,
  no visual element.
- **llterm** (Claude Code terminal, self-driving control channel + shell) — **low**: like llove, the
  only hypothetical seam is the generic image-op layer for raster→terminal preview; the control
  channel / shell itself is untouched.
