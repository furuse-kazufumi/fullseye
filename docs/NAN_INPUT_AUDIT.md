# 非有限入力監査

## 方法

登録表の全 942 件を列挙し、適用可能な op へ有限な基準入力、中央の1要素だけを NaN、+inf にした入力を渡した。
各呼出しは 20 秒で打ち切り、入れ子の数値出力も検査した。基準入力が失敗した行は注入結果から除外した。

## 結果

| outcome | NaN | +inf |
|---|---:|---:|
| `raises_fsvalueerror` | 0 | 0 |
| `raises_other` | 34 | 27 |
| `propagates_nan` | 300 | 225 |
| `silent_finite` | 282 | 392 |
| `silent_identical` | 258 | 230 |
| `timeout` | 0 | 0 |
| `baseline_failed` | 1 | 1 |
| `not_applicable` | 67 | 67 |

## 包み紙(fullseye.apply)経由

上の表は生の実装(登録表の関数を直接呼んだ結果)で、そちらは変えていない。公開の入口 `fullseye.apply` は 非有限な浮動小数の入力を op を呼ぶ前に `FsValueError` で拒否する(2026-10-23 の契約変更、逃げ道は `allow_nonfinite=True`)。適用可能な 875 op を同じ注入入力で入口経由に通した結果:

| behaviour | NaN | +inf |
|---|---:|---:|
| `raised_FsValueError` | 875 | 875 |

入口が拒否しなかった op(silent_finite の包み紙版): なし。

## silent_finite

### `backends`

- `sk_adapthist`: nan, inf
- `sk_median_disk`: nan, inf
- `sk_li`: nan
- `sk_sauvola`: nan, inf
- `sk_niblack`: nan, inf
- `sk_canny`: nan, inf
- `sk_skeleton`: inf
- `sk_medial`: inf
- `sk_convex`: inf
- `sk_thin`: inf
- `sk_remove_holes`: inf
- `sk_euler`: inf
- `sk_find_contours`: nan
- `sk_lbp`: nan, inf
- `sk_entropy`: inf
- `sk_enhance_contrast`: nan, inf
- `sk_autolevel`: nan, inf
- `sk_shape_index`: nan, inf
- `sk_hessian_det`: nan, inf
- `sk_corner_harris`: nan, inf
- `sk_adjust_log`: inf
- `sk_rolling_ball`: inf
- `sk_swirl`: inf
- `sk_felzenszwalb`: nan, inf
- `sk_chan_vese`: nan, inf
- `sk_local_maxima`: nan, inf
- `sk_hysteresis`: nan
- `sk_find_boundaries`: inf
- `cv_median`: nan, inf
- `cv_clahe`: nan, inf
- `cv_close`: inf
- `cv_otsu`: nan, inf
- `cv_adaptive_mean`: nan, inf
- `cv_adaptive_gauss`: nan, inf
- `cv_canny`: nan, inf
- `cv_corner_harris`: nan, inf
- `cv_nlmeans`: nan, inf
- `cv_sharpen`: inf
- `cv_dist`: inf

### `backends_alife`

- `alife_gray_scott`: nan, inf
- `alife_turing`: nan, inf
- `alife_life_step`: nan
- `alife_cyclic_ca`: nan, inf
- `alife_perona_malik`: nan, inf
- `alife_curvature_flow`: nan, inf
- `alife_dla`: nan, inf
- `alife_reaction_bz`: nan, inf

### `backends_alife2`

- `alife_langton_ant`: nan
- `alife_lenia`: nan, inf
- `alife_sandpile`: nan, inf

### `backends_aug`

- `aug_shot_noise`: nan, inf
- `aug_read_noise`: nan, inf
- `aug_fixed_pattern`: nan, inf
- `aug_motion_blur`: nan, inf
- `aug_vignette`: nan, inf
- `aug_chromatic`: nan, inf
- `aug_rolling_shutter`: nan, inf
- `aug_jpeg_blocks`: nan, inf
- `aug_cutout`: nan, inf

### `backends_auto`

- `sqrt_image`: inf
- `exp_image`: inf
- `log_image`: inf
- `sin_image`: inf
- `cos_image`: inf
- `asin_image`: inf
- `acos_image`: inf
- `atan_image`: inf
- `gamma_image`: inf
- `pow_image`: inf
- `invert_image`: inf
- `scale_image`: inf
- `equ_histo_image`: inf
- `illuminate`: inf
- `scale_image_max`: inf
- `laplace_of_gauss`: nan, inf
- `trimmed_mean`: inf
- `kirsch_dir`: nan, inf
- `phase_rad`: inf
- `highpass_image`: nan, inf
- `bandpass_image`: nan, inf
- `transpose_region`: inf
- `polar_trans_image`: inf
- `h_threshold`: nan
- `dyn_threshold`: nan
- `var_threshold`: nan
- `local_threshold`: nan
- `hysteresis_threshold`: nan
- `edges_image`: nan, inf
- `watersheds`: nan
- `watersheds_threshold`: nan
- `local_max`: inf
- `dilation_circle`: inf
- `dilation_rectangle1`: inf
- `closing_rectangle1`: inf
- `fill_up`: inf
- `boundary`: inf
- `skeleton`: inf
- `thinning`: inf
- `shape_trans`: inf
- `distance_transform`: inf
- `area_center`: inf
- `count_obj`: inf
- `euler_number`: inf
- `min_max_gray`: inf
- `intensity`: inf
- `gray_histo_abs`: inf
- `entropy_gray`: nan, inf
- `edges_sub_pix`: nan, inf
- `lines_gauss`: nan, inf
- `cooc_feature_matrix`: nan, inf
- `equ_histo_image_rect`: inf
- `projective_trans_region`: inf
- `fft_image_inv`: nan
- `add_noise_white`: inf
- `dual_threshold`: inf
- `estimate_noise`: nan, inf
- `points_foerstner`: nan, inf
- `points_harris_binomial`: nan, inf
- `zero_crossing`: nan, inf
- `hough_line_trans`: nan, inf
- `hough_circle_trans`: nan, inf
- `threshold_sub_pix`: nan
- `zero_crossing_sub_pix`: nan, inf
- `closest_point_transform`: inf
- `tan_image`: nan, inf
- `bit_not`: inf
- `monotony`: nan, inf
- `mean_sp`: inf
- `dots_image`: nan, inf
- `frei_dir`: nan, inf
- `robinson_dir`: nan, inf
- `phase_deg`: inf
- `polar_trans_image_ext`: inf
- `lines_facet`: nan, inf
- `add_noise_distribution`: inf
- `dilation_golay`: inf
- `dilation_seq`: inf
- `morph_skeleton`: inf
- `thinning_golay`: inf
- `thinning_seq`: inf
- `fast_threshold`: nan
- `nonmax_suppression_amp`: inf
- `pouring`: nan
- `affine_trans_region`: nan, inf
- `mirror_region`: inf
- `zoom_region`: nan, inf
- `fill_up_shape`: inf
- `smallest_rectangle1`: inf
- `get_region_contour`: inf
- `get_region_convex`: inf
- `connect_and_holes`: inf
- `gen_contour_region_xld`: inf

### `backends_color`

- `cfa_to_rgb`: nan, inf
- `trans_from_rgb`: nan, inf
- `trans_to_rgb`: nan, inf
- `linear_trans_color`: inf
- `principal_comp`: inf
- `rgb1_to_gray`: inf
- `rgb3_to_gray`: inf
- `edges_color`: inf
- `edges_color_sub_pix`: nan, inf
- `lines_color`: nan

### `backends_cv2b`

- `xcv2_meanshift`: nan, inf

### `backends_decomp`

- `dc_structure_texture`: nan, inf
- `dc_texture_residual`: nan, inf
- `dc_rpca_lowrank`: nan, inf
- `dc_rpca_sparse`: nan, inf
- `dc_retinex`: nan, inf
- `dc_local_contrast_norm`: nan, inf
- `dc_homomorphic`: nan, inf

### `backends_deform`

- `deform_tps`: nan, inf
- `deform_ffd`: nan, inf

### `backends_extra`

- `xsk_inpaint`: inf
- `xsk_richardson_lucy`: inf
- `xsk_unwrap_phase`: nan, inf
- `xsk_struct_coherence`: nan, inf
- `xsk_hessian_eig`: inf
- `xsk_blob_log`: nan
- `xsk_blob_dog`: nan
- `xsk_meijering`: inf
- `xsk_sato`: inf
- `xcv_stylization`: nan, inf
- `xcv_edge_preserving`: nan, inf
- `xcv_detail_enhance`: nan, inf
- `xcv_inpaint`: nan, inf

### `backends_filters2`

- `f2_shock`: nan, inf
- `f2_shock_diffuse`: nan, inf
- `f2_gray_skeleton`: nan
- `f2_lut_trans`: nan, inf
- `f2_topographic`: nan, inf
- `f2_expand_domain`: nan, inf
- `f2_symmetry`: nan, inf
- `f2_gauss_pyramid`: nan, inf
- `f2_gray_inside`: nan, inf
- `f2_bit_slice`: nan

### `backends_halcon_ext`

- `hx_gabor`: inf
- `hx_fit_surface1`: nan, inf
- `hx_fit_surface2`: nan, inf
- `hx_cooc_feature`: nan, inf
- `hx_expand_region`: inf
- `hx_nonmax_dir`: nan
- `hx_char_threshold`: nan, inf
- `hx_histo_to_thresh`: nan, inf
- `hx_dilation1`: inf
- `hx_closing`: inf
- `hx_dilation2`: inf
- `hx_clip_region_rel`: inf
- `hx_shade_height_field`: nan, inf
- `hx_detect_edge_segments`: nan, inf
- `hx_region_to_label`: nan
- `hx_lowlands`: nan
- `hx_plateaus_center`: nan, inf
- `hx_move_region`: inf
- `hx_split_skeleton_region`: inf
- `hx_test_region_points`: inf
- `hx_estimate_sl_al_lr`: inf
- `hx_estimate_al_am`: inf
- `hx_disparity_to_xyz`: nan, inf

### `backends_imgtools`

- `it_add_image_border`: nan, inf
- `it_bit_lshift`: nan, inf
- `it_bit_rshift`: nan, inf
- `it_bit_mask`: nan
- `it_convert_image_type`: nan, inf
- `it_change_format`: nan, inf
- `it_region_to_bin`: nan
- `it_full_domain`: nan, inf

### `backends_inverse`

- `iv_richardson_lucy`: nan, inf
- `iv_wiener_deconv_spatial`: nan, inf
- `iv_unsharp_deblur`: nan, inf
- `iv_motion_deblur`: nan, inf
- `iv_backproject_superres`: nan, inf
- `iv_gradient_inpaint`: nan, inf

### `backends_kornia`

- `xkor_gaussian`: inf
- `xkor_bilateral`: inf
- `xkor_unsharp`: inf
- `xkor_motion_blur`: inf
- `xkor_canny`: inf
- `xkor_clahe`: inf
- `xkor_laplacian`: nan, inf
- `xkor_harris`: nan, inf
- `xkor_gftt`: nan, inf
- `xkor_hessian`: nan, inf
- `xkor_dog`: nan, inf

### `backends_macro`

- `macro_denoise`: nan, inf
- `macro_edge`: nan, inf
- `macro_binarize`: nan, inf
- `macro_vol_denoise`: inf

### `backends_physics`

- `ph_perona_malik`: nan, inf
- `ph_coherence_enhancing_diffusion`: nan, inf
- `ph_reaction_diffusion`: nan, inf
- `ph_heat_flow`: nan, inf
- `ph_mean_curvature_motion`: nan, inf
- `ph_total_variation_flow`: nan, inf

### `backends_pil`

- `xpil_emboss`: nan, inf
- `xpil_contour`: nan, inf
- `xpil_find_edges`: nan, inf
- `xpil_edge_enhance`: nan, inf
- `xpil_smooth_more`: nan, inf
- `xpil_detail`: nan, inf
- `xpil_mode_filter`: nan, inf
- `xpil_unsharp_mask`: nan, inf
- `xpil_posterize`: nan, inf
- `xpil_solarize`: nan, inf
- `xpil_autocontrast`: nan, inf
- `xpil_offset`: nan, inf
- `xpil_contrast`: nan, inf

### `backends_r3`

- `xmh_zernike`: nan, inf
- `xmh_pftas`: nan, inf
- `xmh_bernsen`: inf
- `xmh_haar`: nan, inf
- `xmh_daubechies`: nan, inf
- `xmh_soft`: nan, inf
- `xmh_bwperim`: inf
- `xmh_regmin`: nan, inf
- `xmh_selfmatch`: nan, inf
- `xwt_subband_tile`: nan, inf
- `xwt_visushrink`: nan, inf
- `xwt_firm_denoise`: nan, inf
- `xwt_detail_energy`: nan, inf
- `xwt_hf_reconstruct`: nan, inf
- `xwt_lf_reconstruct`: nan, inf
- `xwt_directional_detail`: nan, inf
- `xwt_packet_entropy`: nan, inf
- `xwt_mra_component`: nan, inf
- `xsitk_curvature_flow`: nan, inf
- `xsitk_curv_aniso_diff`: nan, inf
- `xsitk_laplacian_sharpen`: nan, inf
- `xsitk_grayscale_fillhole`: nan, inf
- `xsitk_grayscale_grindpeak`: nan, inf
- `xsitk_opening_by_recon`: nan
- `xsitk_closing_by_recon`: inf
- `xsitk_signed_maurer_dist`: inf
- `xsitk_confidence_connected`: nan, inf
- `xsitk_maxentropy_thresh`: inf
- `xsitk_moments_thresh`: inf
- `xsitk_huang_thresh`: nan, inf
- `xsk3_rank_otsu`: nan
- `xsk3_rank_subtract_mean`: nan, inf
- `xsk3_rank_equalize`: nan, inf
- `xsk3_rank_mean_bilateral`: nan, inf
- `xsk3_area_closing`: nan, inf
- `xsk3_diameter_closing`: nan, inf
- `xsk3_corner_moravec`: nan
- `xsk3_integral_image`: nan, inf
- `xsk3_threshold_local_median`: nan
- `xsk3_peak_local_max`: nan
- `xcv3_denoise_tvl1`: nan, inf
- `xcv3_inpaint_ns`: nan, inf
- `xcv3_pyr_laplacian`: nan, inf
- `xcv3_gray_hu1`: nan, inf
- `xcv3_lsd_count`: nan, inf

### `backends_regions3`

- `r3_label_to_region`: inf

### `backends_scipy`

- `xsp_wiener`: inf
- `xsp_savgol`: inf
- `xsp_hilbert_env`: inf
- `xsp_dct`: inf
- `xsp_dct_lowpass`: inf
- `xsp_dct_denoise`: nan, inf
- `xsp_cspline_smooth`: inf
- `xsp_detrend_flatten`: inf
- `xsp_morph_laplace`: nan, inf
- `xsp_chamfer_dist`: inf
- `xsp_gauss_grad_mag`: inf

### `backends_segment2`

- `sg_gmm_segment`: nan, inf
- `sg_kmeans_intensity`: inf
- `sg_region_growing_seeded`: nan
- `sg_normalized_cut_2`: nan
- `sg_watershed_gradient`: nan

### `backends_ski2`

- `xsk2_multiotsu`: inf
- `xsk2_rank_geomean`: nan, inf
- `xsk2_isotropic_close`: inf
- `xsk2_hog`: inf
- `xsk2_corner_kr`: nan, inf
- `xsk2_radon`: inf
- `xsk2_inv_gauss_grad`: inf
- `xsk2_wiener`: inf

### `backends_subpix`

- `sp_local_max_sub_pix`: nan, inf
- `sp_local_min_sub_pix`: nan, inf
- `sp_saddle_points_sub_pix`: nan, inf
- `sp_critical_points_sub_pix`: nan, inf
- `sp_lowlands_center`: nan

### `backends_tactile`

- `tac_contact_mask`: inf
- `tac_height_from_shading`: nan, inf
- `tac_surface_normal`: nan, inf
- `tac_pressure_proxy`: nan, inf
- `tac_shear_field`: nan, inf

### `backends_texture`

- `fractal_dimension`: nan

### `backends_tomo`

- `tm_radon_forward`: nan, inf
- `tm_fbp_reconstruct`: nan, inf
- `tm_backproject_unfiltered`: nan, inf
- `tm_sinogram_denoise`: nan, inf

### `backends_transform2`

- `tf_radon_sinogram`: nan, inf
- `tf_steerable_filter`: nan, inf
- `tf_phase_congruency`: nan, inf
- `tf_gradient_domain_reintegrate`: nan, inf
- `tf_census_transform`: nan, inf
- `tf_rank_transform`: nan, inf

### `backends_typed`

- `tb_points_to_voxel`: nan, inf
- `tb_iss_keypoints`: nan, inf
- `tb_points_render`: nan, inf
- `tb_alpha_shape_boundary`: nan, inf
- `tb_mean_curvature`: nan, inf
- `tb_gaussian_curvature`: nan, inf
- `tb_inertia_tensor`: nan, inf
- `tb_geodesic_distances`: nan, inf
- `tb_farthest_point_sampling`: nan, inf
- `tb_region_growing`: nan, inf
- `tb_euclidean_cluster`: nan, inf
- `tb_plane_segmentation`: nan, inf
- `tb_project_cylindrical`: nan, inf
- `tb_sphere_sdf`: nan, inf
- `tb_box_sdf`: nan, inf
- `tb_plane_sdf`: nan, inf
- `tb_cylinder_sdf`: nan, inf
- `tb_torus_sdf`: nan, inf
- `tb_capsule_sdf`: nan, inf
- `tb_spectrogram`: nan, inf
- `tb_env_studio`: nan, inf
- `tb_env_lightbox`: nan, inf
- `tb_lf_to_mla`: nan, inf
- `tb_lf_subaperture`: nan, inf
- `tb_lf_center_view`: nan, inf
- `tb_lf_epi`: nan, inf
- `tb_lf_refocus`: nan, inf
- `tb_lf_synthetic_aperture`: nan, inf
- `tb_lf_depth_from_focus`: nan, inf
- `tb_lf_epi_slope`: nan, inf
- `tb_temporal_band_power`: nan, inf
- `tb_rgb_to_quaternion`: nan, inf
- `tb_quat_norm`: nan, inf
- `tb_magnus_lift_coefficient`: nan, inf
- `tb_normals_to_egi`: nan, inf
- `tb_points_zyx_to_keypoints_uv`: nan, inf
- `tb_mirror_plane_from_pairs`: nan, inf
- `tb_landmark_asymmetry`: nan, inf

### `ops`

- `runlength_smear`: inf
- `edge_transition_width`: nan, inf
- `gamma`: inf
- `quantize_uniform`: inf
- `quantize_lloyd_max`: inf
- `quantization_error`: inf
- `dither_ordered`: inf
- `dither_floyd_steinberg`: inf
- `companding_mu_law`: inf
- `effective_bit_depth`: inf
- `invert`: inf
- `scale_clip`: inf
- `sigmoid`: inf
- `highpass`: nan, inf
- `local_bimodality`: nan, inf
- `xdog`: nan, inf
- `local_thickness`: nan
- `threshold`: nan
- `otsu`: nan
- `reg_dilate`: inf
- `reg_close`: inf
- `fill_holes`: inf
- `invert_region`: inf
- `blob_count`: inf
- `area_frac`: inf
- `canny`: nan, inf
- `dist_transform`: inf
- `dist_transform_abs`: inf
- `region_boundary`: inf
- `gabor`: inf
- `clahe`: inf
- `corner_response`: nan, inf
- `adaptive_gauss_thresh`: nan, inf
- `vol_median`: nan, inf
- `vol_threshold`: inf
- `vol_slice`: inf

## contaminated

基準入力が失敗したため、次の行は注入結果を判定していない: `xsk_orb_count`
