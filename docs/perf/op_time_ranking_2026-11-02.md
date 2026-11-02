# Op time ranking — 2026-11-02

実行したPoCで `ops.RT` に到達した呼び出しだけを実測した。総時間順。

| rank | op | 族 | GPU | calls | 1回 ms | 合計 s |
|---:|---|---|---|---:|---:|---:|
| 1 | `xsk_meijering` | texture | なし | 52 | 63.699 | 3.312 |
| 2 | `xsk2_h_maxima` | segmentation | なし | 2751 | 0.939 | 2.583 |
| 3 | `sk_area_opening` | morphology | なし | 61 | 35.918 | 2.191 |
| 4 | `fill_holes` | region | fill_holes | 498 | 1.207 | 0.601 |
| 5 | `select_largest` | region | なし | 378 | 1.214 | 0.459 |
| 6 | `xsk2_multiotsu` | segmentation | なし | 434 | 1.020 | 0.443 |
| 7 | `gray_bothat` | morphology | gray_bothat@twin | 47 | 9.375 | 0.441 |
| 8 | `opening_circle` | region | opening_circle | 38 | 10.381 | 0.394 |
| 9 | `hx_close_edges` | halcon_ext | なし | 41 | 8.960 | 0.367 |
| 10 | `sk_otsu` | segmentation | なし | 585 | 0.508 | 0.297 |
| 11 | `trans_from_rgb` | color | なし | 120 | 2.220 | 0.266 |
| 12 | `thinning` | region | なし | 29 | 8.306 | 0.241 |
| 13 | `sk_frangi` | texture | なし | 3 | 76.303 | 0.229 |
| 14 | `otsu` | segmentation | otsu | 60 | 3.384 | 0.203 |
| 15 | `sobel_dir` | edges | sobel_dir | 41 | 4.760 | 0.195 |
| 16 | `xsk_sato` | texture | なし | 3 | 62.569 | 0.188 |
| 17 | `dyn_threshold` | segmentation | dyn_threshold | 47 | 3.856 | 0.181 |
| 18 | `reg_close` | region | なし | 340 | 0.531 | 0.180 |
| 19 | `gauss_filter` | smoothing | gauss_filter@twin | 89 | 1.993 | 0.177 |
| 20 | `gaussian` | smoothing | gauss_filter | 451 | 0.392 | 0.177 |
| 21 | `get_region_contour` | region | なし | 33 | 4.833 | 0.159 |
| 22 | `bin_threshold` | segmentation | なし | 46 | 3.371 | 0.155 |
| 23 | `r2_endpoints_skeleton` | region | なし | 61 | 2.393 | 0.146 |
| 24 | `sobel_amp` | edges | sobel_amp@twin | 57 | 2.407 | 0.137 |
| 25 | `cv_blackhat` | morphology | なし | 64 | 1.822 | 0.117 |
| 26 | `pruning` | region | なし | 61 | 1.334 | 0.081 |
| 27 | `junctions_skeleton` | region | なし | 61 | 1.179 | 0.072 |
| 28 | `hysteresis_threshold` | segmentation | なし | 61 | 1.165 | 0.071 |
| 29 | `corner_response` | edges | なし | 2 | 30.774 | 0.062 |
| 30 | `skeleton` | region | なし | 61 | 1.008 | 0.061 |
| 31 | `invert_image` | gray | invert_image@twin | 47 | 1.199 | 0.056 |
| 32 | `access_channel` | color | なし | 115 | 0.383 | 0.044 |
| 33 | `threshold` | segmentation | threshold | 108 | 0.385 | 0.042 |
| 34 | `dc_homomorphic` | decomposition | なし | 5 | 8.080 | 0.040 |
| 35 | `hx_split_skeleton_region` | halcon_ext | なし | 61 | 0.565 | 0.034 |
| 36 | `mean_image` | smoothing | mean_image@twin | 302 | 0.112 | 0.034 |
| 37 | `var_threshold` | segmentation | なし | 1 | 14.981 | 0.015 |
| 38 | `illuminate` | gray | illuminate | 1 | 10.863 | 0.011 |
| 39 | `sg_gmm_segment` | segment | なし | 5 | 1.644 | 0.008 |
| 40 | `gray_tophat` | morphology | gray_tophat@twin | 1 | 7.162 | 0.007 |

## 上位40のGPU未対応内訳

| 族 | op数 | 合計 s |
|---|---:|---:|
| texture | 3 | 3.729 |
| segmentation | 6 | 3.563 |
| morphology | 2 | 2.308 |
| region | 8 | 1.401 |
| halcon_ext | 2 | 0.402 |
| color | 2 | 0.310 |
| edges | 1 | 0.062 |
| decomposition | 1 | 0.040 |
| segment | 1 | 0.008 |

## 所見

実行した 20 本の PoC で `ops.RT` に到達した op は 48 種、総時間は合計 14.5 s。
最も重い op でも合計 **3.3 s**(`xsk_meijering`)で、時間×頻度の順位では GPU の出番は見えない。
既存 PoC は CPU 前提の寸法で作られているから小さいだけで、**GPU の価値は「実寸」で決まる**(`docs/perf/gpu_required_2026-11-02.md` の寸法×時間表を参照)。

MCP e2e 20 課題(#224)の op 時間は未計測(この便ではローカルに実行器を立てていない)。立てた回に同じ JSON へ追記する。

## Workloads

- `examples/poc_cell_counting.py`: ok, 16.829 s
- `examples/poc_crack_width.py`: ok, 12.346 s
- `examples/poc_crop_phenotyping.py`: ok, 47.450 s
- `examples/poc_ct_void_morphology.py`: ok, 124.017 s
- `examples/poc_dehazing.py`: ok, 16.606 s
- `examples/poc_document_scan.py`: ok, 14.760 s
- `examples/poc_fabric_defect.py`: ok, 7.533 s
- `examples/poc_fiber_orientation.py`: ok, 14.087 s
- `examples/poc_focus_stacking.py`: ok, 21.996 s
- `examples/poc_fresco_craquelure.py`: ok, 74.355 s
- `examples/poc_leaf_disease_area.py`: ok, 58.475 s
- `examples/poc_metal_grain_size.py`: ok, 27.287 s
- `examples/poc_mri_bias_field.py`: ok, 44.396 s
- `examples/poc_nuclei_ploidy.py`: ok, 12.787 s
- `examples/poc_particle_sizing.py`: ok, 33.836 s
- `examples/poc_photoelasticity.py`: ok, 18.913 s
- `examples/poc_pipe_wall_loss.py`: ok, 31.660 s
- `examples/poc_print_registration.py`: ok, 64.833 s
- `examples/poc_recycling_sorting.py`: ok, 137.974 s
- `examples/poc_safety_clearance.py`: ok, 45.824 s
