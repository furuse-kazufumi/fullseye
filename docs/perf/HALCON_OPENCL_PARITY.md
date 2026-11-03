# HALCON 26.05 OpenCL 84 演算子 — Fullseye 対応行列

HALCON 26.05 で「Supports OpenCL compute devices」が付く古典演算子 84 件(正本 `docs/perf/halcon_2605_opencl_ops.json`)を、Fullseye の機械可読索引(`docs/OP_INDEX.json` の `halcon` 欄)と実装台帳(`accel.ACCEL` ほか)に対応づけた。

- **Fullseye 対応あり N1 = 71**
- **そのうち GPU 経路あり N2 = 36**
- **未対応 N3 = 13**

門: N1 + N3 = 71 + 13 = **84**。

「HALCON より速い」等、測っていない比較は書かない。

| HALCON 名 | 章 | Fullseye 対応 op | GPU 経路 | 備考 |
|---|---|---|:---:|---|
| `binocular_disparity_ms` | 3DRECONSTRUCTION | — | — | Fullseye 未対応 |
| `binocular_distance_ms` | 3DRECONSTRUCTION | — | — | Fullseye 未対応 |
| `depth_from_focus` | 3DRECONSTRUCTION | — | — | Fullseye 未対応 |
| `reconstruct_surface_stereo` | 3DRECONSTRUCTION | — | — | Fullseye 未対応 |
| `change_radial_distortion_image` | CALIBRATION | — | — | Fullseye 未対応 |
| `image_to_world_plane` | CALIBRATION | — | — | Fullseye 未対応 |
| `abs_diff_image` | FILTERS | `abs_diff_image` | なし | Fullseye 対応あり(CPU のみ) |
| `abs_image` | FILTERS | `abs_image` | なし | Fullseye 対応あり(CPU のみ) |
| `acos_image` | FILTERS | `acos_image` | なし | Fullseye 対応あり(CPU のみ) |
| `add_image` | FILTERS | `add_image` | なし | Fullseye 対応あり(CPU のみ) |
| `affine_trans_image` | FILTERS | `affine_trans_image`, `affine_warp` | あり | Fullseye 対応あり(GPU 経路あり) |
| `affine_trans_image_size` | FILTERS | `affine_trans_image_size` | あり | Fullseye 対応あり(GPU 経路あり) |
| `asin_image` | FILTERS | `asin_image` | なし | Fullseye 対応あり(CPU のみ) |
| `atan2_image` | FILTERS | — | — | Fullseye 未対応 |
| `atan_image` | FILTERS | `atan_image` | なし | Fullseye 対応あり(CPU のみ) |
| `binomial_filter` | FILTERS | `binomial_filter` | あり | Fullseye 対応あり(GPU 経路あり) |
| `cfa_to_rgb` | FILTERS | `cfa_to_rgb` | なし | Fullseye 対応あり(CPU のみ) |
| `convol_image` | FILTERS | `convol_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `cos_image` | FILTERS | `cos_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `derivate_gauss` | FILTERS | `derivate_gauss` | あり | Fullseye 対応あり(GPU 経路あり) |
| `deviation_image` | FILTERS | `deviation_image`, `std_filter` | あり | Fullseye 対応あり(GPU 経路あり) |
| `div_image` | FILTERS | `div_image` | なし | Fullseye 対応あり(CPU のみ) |
| `edges_image` | FILTERS | `canny`, `cv_canny`, `cv_scharr`, `edges_image`, `sk_canny`, `sk_farid`, `sk_scharr` | あり | Fullseye 対応あり(GPU 経路あり) |
| `edges_sub_pix` | FILTERS | `edges_sub_pix` | なし | Fullseye 対応あり(CPU のみ) |
| `exp_image` | FILTERS | `exp_image` | なし | Fullseye 対応あり(CPU のみ) |
| `gamma_image` | FILTERS | `gamma_image` | なし | Fullseye 対応あり(CPU のみ) |
| `gauss_filter` | FILTERS | `cv_gaussian`, `gauss_filter`, `gaussian` | あり | Fullseye 対応あり(GPU 経路あり) |
| `highpass_image` | FILTERS | `highpass`, `highpass_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `invert_image` | FILTERS | `invert`, `invert_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `linear_trans_color` | FILTERS | `linear_trans_color` | なし | Fullseye 対応あり(CPU のみ) |
| `lines_gauss` | FILTERS | `lines_gauss`, `sk_frangi`, `sk_hessian`, `sk_meijering` | なし | Fullseye 対応あり(CPU のみ) |
| `log_image` | FILTERS | `log_image`, `sk_adjust_log` | なし | Fullseye 対応あり(CPU のみ) |
| `lut_trans` | FILTERS | `f2_lut_trans` | あり | Fullseye 対応あり(GPU 経路あり) |
| `map_image` | FILTERS | — | — | Fullseye 未対応 |
| `max_image` | FILTERS | `max_image` | なし | Fullseye 対応あり(CPU のみ) |
| `mean_image` | FILTERS | `cv_box`, `mean_box`, `mean_box_wh`, `mean_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `median_image` | FILTERS | `cv_median`, `median`, `median_image`, `sk_median_disk` | あり | Fullseye 対応あり(GPU 経路あり) |
| `median_rect` | FILTERS | `median_rect` | あり | Fullseye 対応あり(GPU 経路あり) |
| `min_image` | FILTERS | `min_image` | なし | Fullseye 対応あり(CPU のみ) |
| `mirror_image` | FILTERS | `mirror_image` | なし | Fullseye 対応あり(CPU のみ) |
| `mult_image` | FILTERS | `mult_image` | なし | Fullseye 対応あり(CPU のみ) |
| `points_harris` | FILTERS | `corner_response`, `cv_corner_harris`, `cv_min_eigen`, `sk_corner_harris` | あり | Fullseye 対応あり(GPU 経路あり) |
| `polar_trans_image_ext` | FILTERS | `polar_trans_image_ext` | なし | Fullseye 対応あり(CPU のみ) |
| `polar_trans_image_inv` | FILTERS | `polar_trans_image_inv` | なし | Fullseye 対応あり(CPU のみ) |
| `pow_image` | FILTERS | `gamma`, `pow_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `principal_comp` | FILTERS | `principal_comp` | あり | Fullseye 対応あり(GPU 経路あり) |
| `projective_trans_image` | FILTERS | `projective_trans_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `projective_trans_image_size` | FILTERS | `projective_trans_image_size` | あり | Fullseye 対応あり(GPU 経路あり) |
| `rgb1_to_gray` | FILTERS | `rgb1_to_gray` | なし | Fullseye 対応あり(CPU のみ) |
| `rgb3_to_gray` | FILTERS | `rgb3_to_gray` | なし | Fullseye 対応あり(CPU のみ) |
| `rotate_image` | FILTERS | `rotate_image`, `rotate_img` | あり | Fullseye 対応あり(GPU 経路あり) |
| `scale_image` | FILTERS | `cv_trunc`, `scale_clip`, `scale_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `sin_image` | FILTERS | `sin_image` | なし | Fullseye 対応あり(CPU のみ) |
| `sobel_amp` | FILTERS | `sobel_amp`, `sobel_mag` | あり | Fullseye 対応あり(GPU 経路あり) |
| `sobel_dir` | FILTERS | `sobel_dir` | あり | Fullseye 対応あり(GPU 経路あり) |
| `sqrt_image` | FILTERS | `sqrt_image` | なし | Fullseye 対応あり(CPU のみ) |
| `sub_image` | FILTERS | `sub_image` | なし | Fullseye 対応あり(CPU のみ) |
| `tan_image` | FILTERS | `tan_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `texture_laws` | FILTERS | `texture_laws` | あり | Fullseye 対応あり(GPU 経路あり) |
| `trans_from_rgb` | FILTERS | `trans_from_rgb` | なし | Fullseye 対応あり(CPU のみ) |
| `trans_to_rgb` | FILTERS | `trans_to_rgb` | なし | Fullseye 対応あり(CPU のみ) |
| `zoom_image_factor` | FILTERS | `rescale_img`, `zoom_image_factor` | あり | Fullseye 対応あり(GPU 経路あり) |
| `zoom_image_size` | FILTERS | `zoom_image_size` | なし | Fullseye 対応あり(CPU のみ) |
| `area_center_gray` | IMAGE | — | — | Fullseye 未対応 |
| `convert_image_type` | IMAGE | `it_convert_image_type` | なし | Fullseye 対応あり(CPU のみ) |
| `crop_domain` | IMAGE | `it_crop_domain` | なし | Fullseye 対応あり(CPU のみ) |
| `crop_part` | IMAGE | `it_crop_part` | あり | Fullseye 対応あり(GPU 経路あり) |
| `crop_rectangle1` | IMAGE | `it_crop_rectangle1` | あり | Fullseye 対応あり(GPU 経路あり) |
| `crop_rectangle2` | IMAGE | — | — | Fullseye 未対応 |
| `gray_histo` | IMAGE | — | — | Fullseye 未対応 |
| `gray_projections` | IMAGE | — | — | Fullseye 未対応 |
| `gauss_image` | LEGACY | `gauss_image` | あり | Fullseye 対応あり(GPU 経路あり) |
| `polar_trans_image` | LEGACY | `polar_trans_image`, `sk_swirl` | なし | Fullseye 対応あり(CPU のみ) |
| `find_ncc_model` | MATCHING | `ncc_locate` | あり | Fullseye 対応あり(GPU 経路あり) |
| `find_ncc_models` | MATCHING | — | — | Fullseye 未対応 |
| `gray_closing_rect` | MORPHOLOGY | `gray_closing_rect` | あり | Fullseye 対応あり(GPU 経路あり) |
| `gray_closing_shape` | MORPHOLOGY | `gray_closing_shape` | なし | Fullseye 対応あり(CPU のみ) |
| `gray_dilation_rect` | MORPHOLOGY | `gray_dilation_rect`, `max_filter` | あり | Fullseye 対応あり(GPU 経路あり) |
| `gray_dilation_shape` | MORPHOLOGY | `gray_dilation_shape` | なし | Fullseye 対応あり(CPU のみ) |
| `gray_erosion_rect` | MORPHOLOGY | `gray_erosion_rect`, `min_filter` | あり | Fullseye 対応あり(GPU 経路あり) |
| `gray_erosion_shape` | MORPHOLOGY | `gray_erosion_shape` | なし | Fullseye 対応あり(CPU のみ) |
| `gray_opening_rect` | MORPHOLOGY | `gray_opening_rect` | あり | Fullseye 対応あり(GPU 経路あり) |
| `gray_opening_shape` | MORPHOLOGY | `gray_opening_shape` | なし | Fullseye 対応あり(CPU のみ) |
| `gray_range_rect` | MORPHOLOGY | `cv_gradient`, `gray_range_rect`, `morph_grad` | あり | Fullseye 対応あり(GPU 経路あり) |
