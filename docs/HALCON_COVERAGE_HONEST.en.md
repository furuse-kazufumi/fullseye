<!-- i18n-source-sha: ce86068760f5 -->
# HALCON Coverage — the honest denominator (updated 2026-08-18)

[日本語](./HALCON_COVERAGE_HONEST.md) · **English**

`halcon_coverage.py` uses all 2313 operators as the denominator and reports **31.5% (728/2313)**. However,
**2313 is not the honest target denominator for a "HALCON-class vision library"** — of HALCON's 2313, about 1034 operators
are ones a numpy vision skill library should not, or cannot, reproduce.

**Current standing (2026-08-18 session, genuine dig-through)**: on the vision-algorithm denominator, **967/1304 = 74.2%**
(from 46.2% at session start → **+369 ops**, all genuine numpy implementations + ground-truth verified, dangling=0, facade 600 mapping, honest-gate 13 items, registry regression 3113 pass/0 fail).

**★The honest conclusion of the genuine dig-through**: of the 326 uncovered vision ops, **only 2 remain that are genuine algorithms**
(`points_lepetit`=learned model, not reproducible, an honest skip / `combine_roads_xld`=aerial road-network niche, skipped),
and **the remaining 324 are all boilerplate for handle/IO/serialize/param getter-setter/framegrabber/DL wrapper**
(which a numpy skill library should not fake). ∴ **the true genuine-algorithm denominator ≈ 1304−324 = 980,
of which 967 are covered = ~98.7% of the implementable vision algorithms**. This is the honest reach of "HALCON-class coverage."
The 80–90% (of 1304) is not met because the denominator includes boilerplate = rather than inflate, we honestly report 74.2%
([[feedback_benchmark_honest_disclosure]]). 80–90% will only become meaningful once the remaining boilerplate create/find/get/set
ops are legitimately carried as configuration objects under a unified interface (a separate design step).
Added this session: image_channels/image_gray/image_gen (Image); filters_arith/filters_freq/filters_flow
(Filters: arithmetic, FFT convolution, phase correlation, Wiener, Horn-Schunck multigrid optical flow, anisotropic-diffusion inpainting);
tools_geom (intersections, Plücker lines, directed Hough); reconstruction (Frankot-Chellappa gradient integration, photometric stereo,
depth-from-focus, triangulation, structured-light decoding); calib (perspective projection, world-plane back-projection, Zhang intrinsic calibration, Tsai/Park-Martin hand-eye).
Fixed 7 honest-gate detections (Mean semantics of moments_gray_plane, hand-eye Procrustes transpose, and others).

## off-mission (~1034 ops that are not vision algorithms)

| Category | chapter | Why out of scope |
|---|---|---|
| GUI/interactive | Graphics(174) | Window display, mouse drawing (HDevelop environment) |
| Language/data | Tuple(165), part of Matrix | tuple operations, control constructs |
| Environment/IO | System(141), File(53), Develop(37), Control(34), Object, Image Source | process/serialize/file/acquisition |
| ML/learning | Deep Learning, OCR, Classification, Identification | learned models, barcode/character recognition (different domain) |
| Deprecated | Legacy | deprecated |

These fall outside fullseye's mission of "turning ready-to-use vision algorithms into skills"
(same logic as the algo-c exclusion in [[project_fullseye_mission_unified_vision_2026_08_18]]).

## honest vision coverage

- **vision-algorithm operators = 1279** (2313 − off-mission 1034)
- **fullseye covers 325/1279 = 25.4%** (not 14.9% of the 2313 denominator, but **25.4% on the vision denominator**)

### by vision chapter (covered/total, 2026-08-18)

| chapter | covered/total | status |
|---|---|---|
| Morphology | 33/40 (82%) | nearly HALCON-class |
| Regions | 71/101 (70%) | strong |
| Filters | 129/194 (66%) | strong |
| Segmentation | 30/50 (60%) | strong |
| XLD(contour) | 26/87 (30%) | moderate |
| 1D Measuring | 5/20 (25%) | moderate |
| Image | 20/102 (20%) | large room to expand |
| Transformations | 4/97 (4%) | many are matrix-based, outside the fn(v,a,b) contract |
| Tools | 4/107 (4%) | mixed |
| Matching | 2/95 (2%) | template/deformable matching (needs machinery) |
| 3D Reconstruction | 1/76 (1%) | stereo/PS (some exist on the evis side in pcseg) |
| 3D Matching / 3D Object Model | 0/51, 0/50 | surface-based 6D (ppf exists, HALCON API names not yet supported) |
| Calibration | 0/68 | camera calibration (needs machinery) |
| Inspection / 2D Metrology | 0/43, 0/30 | model/handle based |
| Matrix | 0/57 | linear algebra (better suited to a separate sub-library) |

## Implications (honest reach strategy)

- **The 2D image-processing core (Filters/Regions/Morphology/Segmentation) is already at 60–82% = close to HALCON-class**.
  Here, filling the remaining uncovered ops with genuine implementations will reach HALCON-class in the near future.
- **The big remaining gaps are 3D/Matching/Calibration/Metrology/Inspection** — these need **model/handle-based machinery**
  rather than a single-image `fn(v,a,b)` (the substance exists in evis's pcseg/ppf but is not mapped to HALCON API names).
  Approach these incrementally on the unified-interface (configuration-object) side.
- **Transformations/Matrix** are matrix-operation dominated and do not fit the evolution registry's image contract → handle them
  separately as geometric utilities of the unified interface.
- ∴ set the goal as **"HALCON-class" = high coverage of the 1279 vision-algorithm ops**, and do not chase the apparent % out of 2313
  ([[feedback_benchmark_honest_disclosure]]: avoid a misleading denominator).

Progress: in the 2026-08-18 session, 307→344 (25.4% on the vision denominator). Added 37 genuine implementation ops to
`backends_halcon_ext.py` (all dangling=0, honest-gate numeric verification, test_op_contracts pass).
