# HALCON parity — what imgevolve genuinely DOES (not just names)

Grounded in the scraped MVTec reference (2313 real operators, v2605). Counts
below are real numpy/scipy/skimage/cv2 implementations that run: core ops
are regression-tested; auto ops must pass the functional gate (which rejects
anything not returning the declared sort — 1 gate-failing auto op(s) are
excluded here, not counted).

## Headline
- **965 / 2313 distinct real HALCON operators implemented (41.7%)**
  = 965 evolvable registry ops (of which 17 are also reachable through the
  n-ary capability tier — a subset, not an addition; 0 n-ary-only).
- dangling registry `Op.halcon` (fake names): **0** (fail-closed).
- partial analogues (the name is claimed but only part of the job is done): **16**, not counted above — apply_bead_inspection_model, apply_texture_inspection_model, binocular_calibration, calibrate_sheet_of_light, camera_calibration, create_bead_inspection_model, create_local_deformable_model, create_ocv_proj, create_shape_model_3d, create_texture_inspection_model, find_box_3d, find_deformable_surface_model, find_local_deformable_model, find_planar_uncalib_deformable_model, find_shape_model_3d, measure_profile_sheet_of_light (what each does and does not do: docs/HALCON_COVERAGE.md).

## Evolvable registry (single-image pipeline, coverage-counted)
- registry ops: 942 ; distinct real HALCON ops covered: **966**
- auto-generated ops passing the functional gate: 226 / 227
- auto ops counted in coverage but FAILING the gate: 1 ['abs_image']

## N-ary capability tier (multi-input; genuine, not evolvable)
- ops: 17 (all pass functional gate) — abs_diff_image, add_image, bit_and, bit_or, convol_image, difference, div_image, intersection, max_image, min_image, mult_image, overpaint_region, paint_gray, reduce_domain, sub_image, symm_difference, union2

## Color (multichannel) sort — first-class, in the evolvable registry
- ops: 12 (color functional gate 12/12 pass; reached via cfa_to_rgb bridge) — access_channel, cfa_to_rgb, count_channels, edges_color, edges_color_sub_pix, linear_trans_color, lines_color, principal_comp, rgb1_to_gray, rgb3_to_gray, trans_from_rgb, trans_to_rgb
- color ops counted in coverage but FAILING their gate: 0 (none — honest)

## Honest scope
- In scope = algorithmic operators (Filters/Image/Regions/Morphology/
  Segmentation/Transformations/XLD/Matching/Inspection). Out of scope =
  HDevelop plumbing (Graphics/Tuple/System/File/Develop/Control/Matrix) and
  trained-model/proprietary chapters (OCR/Classification/Deep-Learning/3D/
  Calibration), where only generic approximations are possible.
- Coverage counts a nearest functional analogue, not signature-level parity.

## Compatibility profile (H15)

| profile | ops |
|---|---:|
| contract_verified | 2 |
| functional_analogue | 510 |
| unknown | 0 |

Unknown is never promoted to PASS.
