# HALCON parity — what imgevolve genuinely DOES (not just names)

Grounded in the scraped MVTec reference (2313 real operators, v2605). Every
count below is a real numpy/scipy/skimage/cv2 implementation that runs; the
functional gate rejects anything that does not return the declared sort.

## Headline
- **203 / 2313 distinct real HALCON operators implemented (8.8%)**
  = 186 evolvable registry ops + 17 n-ary capability ops (disjoint).
- dangling registry `Op.halcon` (fake names): **0** (fail-closed).

## Evolvable registry (single-image pipeline, coverage-counted)
- registry ops: 326 ; distinct real HALCON ops covered: **186**
- auto-generated ops passing the functional gate: 173 / 173
- auto ops counted in coverage but FAILING the gate: 0 (none — honest)

## N-ary capability tier (multi-input; genuine, not evolvable)
- ops: 17 (all pass functional gate) — abs_diff_image, add_image, bit_and, bit_or, convol_image, difference, div_image, intersection, max_image, min_image, mult_image, overpaint_region, paint_gray, reduce_domain, sub_image, symm_difference, union2

## Honest scope
- In scope = algorithmic operators (Filters/Image/Regions/Morphology/
  Segmentation/Transformations/XLD/Matching/Inspection). Out of scope =
  HDevelop plumbing (Graphics/Tuple/System/File/Develop/Control/Matrix) and
  trained-model/proprietary chapters (OCR/Classification/Deep-Learning/3D/
  Calibration), where only generic approximations are possible.
- Coverage counts a nearest functional analogue, not signature-level parity.
