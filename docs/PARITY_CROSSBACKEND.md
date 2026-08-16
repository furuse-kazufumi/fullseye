# Cross-backend parity — independent implementations agree at the tested points

For HALCON operators imgevolve implements with >=2 INDEPENDENT backends
(scipy / OpenCV / scikit-image), we run them on 6 holdout images at 4 knob
operating points — (0.50, 0.40), (0.00, 0.00), (1.00, 1.00), (0.15, 0.85) — and measure the worst pairwise
disagreement over all of them (raw max-abs, not clipped to [0,1]).

| band | meaning | count |
|---|---|---|
| agree (<=0.02) | independent backends match at every tested point | 20 |
| close (<=0.10) | minor numeric/library differences | 4 |
| differ (>0.10) | different algorithm behind a shared name — disclosed | 42 |
| incomparable | a backend raised or outputs cannot be diffed — not evidence | 0 |

**66 HALCON ops with >=2 backends; 66 comparable (20 agree, 4 close, 42 differ), 0 incomparable (honest).**

## Detail
| halcon | sort | #impl | backends | max disagreement | worst (a,b) | band |
|---|---|---|---|---|---|---|
| `anisotropic_diffusion` | image->image | 2 | dl_aniso_diffusion, anisotropic_diffusion | 0.2082 | 1.00/1.00 | differ |
| `binary_threshold` | image->region | 6 | otsu, sk_otsu, sk_li, sk_yen, cv_otsu, binary_threshold | 1.0000 | 0.50/0.40 | differ |
| `boundary` | region->region | 3 | region_boundary, sk_find_boundaries, boundary | 1.0000 | 0.50/0.40 | differ |
| `closing_circle` | region->region | 2 | reg_close, closing_circle | 1.0000 | 0.50/0.40 | differ |
| `diff_of_gauss` | image->image | 3 | dog, sk_dog, diff_of_gauss | 1.0000 | 0.00/0.00 | differ |
| `dilation_circle` | region->region | 2 | reg_dilate, dilation_circle | 1.0000 | 1.00/1.00 | differ |
| `dyn_threshold` | image->region | 3 | dyn_threshold, cv_adaptive_mean, dyn_threshold | 1.0000 | 0.50/0.40 | differ |
| `edges_image` | image->image | 3 | sk_scharr, sk_farid, cv_scharr | 0.4104 | 0.50/0.40 | differ |
| `edges_image` | image->region | 4 | canny, sk_canny, cv_canny, edges_image | 1.0000 | 0.50/0.40 | differ |
| `emphasize` | image->image | 2 | unsharp, cv_sharpen | 0.6511 | 1.00/1.00 | differ |
| `entropy_gray` | image->feature | 2 | sk_entropy_feat, entropy_gray | 10.8490 | 0.50/0.40 | differ |
| `erosion_circle` | region->region | 2 | reg_erode, erosion_circle | 1.0000 | 1.00/1.00 | differ |
| `fill_up` | region->region | 3 | fill_holes, sk_remove_holes, fill_up | 1.0000 | 0.00/0.00 | differ |
| `gen_gabor` | image->image | 3 | gabor, sk_gabor, gen_gabor | 0.9971 | 0.15/0.85 | differ |
| `gray_bothat` | image->image | 3 | bothat, cv_blackhat, gray_bothat | 0.7810 | 0.00/0.00 | differ |
| `gray_closing` | image->image | 3 | gclose, cv_close, gray_closing | 0.2226 | 1.00/1.00 | differ |
| `gray_dilation` | image->image | 3 | gdilate, cv_dilate, gray_dilation | 0.5471 | 0.50/0.40 | differ |
| `gray_erosion` | image->image | 3 | gerode, cv_erode, gray_erosion | 0.5233 | 0.50/0.40 | differ |
| `gray_opening` | image->image | 3 | gopen, cv_open, gray_opening | 0.4151 | 0.50/0.40 | differ |
| `gray_range_rect` | image->image | 3 | morph_grad, cv_gradient, gray_range_rect | 0.8917 | 0.00/0.00 | differ |
| `gray_tophat` | image->image | 3 | tophat, cv_tophat, gray_tophat | 0.6723 | 0.50/0.40 | differ |
| `guided_filter` | image->image | 2 | dl_guided_filter, guided_filter | 0.1649 | 1.00/1.00 | differ |
| `highpass_image` | image->image | 2 | highpass, highpass_image | 1.0000 | 0.50/0.40 | differ |
| `laplace` | image->image | 3 | laplace, cv_laplacian, laplace | 0.1938 | 0.50/0.40 | differ |
| `laplace_of_gauss` | image->image | 2 | log, laplace_of_gauss | 1.0000 | 0.50/0.40 | differ |
| `lines_gauss` | image->image | 3 | sk_frangi, sk_meijering, sk_hessian | 1.0000 | 0.50/0.40 | differ |
| `local_max` | image->region | 2 | sk_local_maxima, local_max | 1.0000 | 0.50/0.40 | differ |
| `local_threshold` | image->region | 3 | adaptive_gauss_thresh, cv_adaptive_gauss, local_threshold | 1.0000 | 0.50/0.40 | differ |
| `log_image` | image->image | 2 | sk_adjust_log, log_image | 0.8576 | 1.00/1.00 | differ |
| `median_image` | image->image | 4 | median, sk_median_disk, cv_median, median_image | 0.3376 | 0.50/0.40 | differ |
| `opening_circle` | region->region | 2 | reg_open, opening_circle | 1.0000 | 1.00/1.00 | differ |
| `points_harris` | image->image | 4 | corner_response, sk_corner_harris, cv_corner_harris, cv_min_eigen | 0.9822 | 0.15/0.85 | differ |
| `polar_trans_image` | image->image | 2 | sk_swirl, polar_trans_image | 0.8058 | 0.00/0.00 | differ |
| `pow_image` | image->image | 2 | gamma, pow_image | 0.1859 | 0.00/0.00 | differ |
| `scale_image` | image->image | 3 | scale_clip, cv_trunc, scale_image | 0.7887 | 0.15/0.85 | differ |
| `scale_image_max` | image->image | 3 | sigmoid, sk_autolevel, scale_image_max | 1.0000 | 1.00/1.00 | differ |
| `select_shape` | region->region | 2 | remove_small, select_shape | 1.0000 | 0.50/0.40 | differ |
| `shape_trans` | region->region | 3 | convex_fill, sk_convex, shape_trans | 1.0000 | 0.50/0.40 | differ |
| `skeleton` | region->region | 3 | sk_skeleton, sk_medial, skeleton | 1.0000 | 0.50/0.40 | differ |
| `threshold` | image->region | 2 | threshold, h_threshold | 1.0000 | 0.00/0.00 | differ |
| `var_threshold` | image->region | 3 | sk_sauvola, sk_niblack, var_threshold | 1.0000 | 0.50/0.40 | differ |
| `watersheds` | image->region | 2 | watersheds, xcv_watershed_markers | 1.0000 | 0.50/0.40 | differ |
| `bilateral_filter` | image->image | 3 | bilateral, cv_bilateral, bilateral_filter | 0.0638 | 1.00/1.00 | close |
| `distance_transform` | region->image | 3 | dist_transform, cv_dist, distance_transform | 0.0750 | 0.50/0.40 | close |
| `gauss_filter` | image->image | 3 | gaussian, cv_gaussian, gauss_filter | 0.0284 | 0.15/0.85 | close |
| `mean_image` | image->image | 3 | mean_box, cv_box, mean_image | 0.0849 | 0.50/0.40 | close |
| `affine_trans_image` | image->image | 2 | affine_warp, affine_trans_image | 0.0000 | 0.50/0.40 | agree |
| `area_center` | region->feature | 2 | area_frac, area_center | 0.0000 | 0.50/0.40 | agree |
| `count_obj` | region->feature | 2 | blob_count, count_obj | 0.0000 | 0.50/0.40 | agree |
| `deviation_image` | image->image | 2 | std_filter, deviation_image | 0.0000 | 0.50/0.40 | agree |
| `edges_sub_pix` | image->contour | 2 | edges_sub_pix, edges_sub_pix | 0.0000 | 0.50/0.40 | agree |
| `entropy_image` | image->image | 2 | sk_entropy, entropy_image | 0.0000 | 0.50/0.40 | agree |
| `equ_histo_image` | image->image | 2 | equalize, equ_histo_image | 0.0000 | 0.50/0.40 | agree |
| `euler_number` | region->feature | 2 | sk_euler, euler_number | 0.0000 | 0.50/0.40 | agree |
| `gray_dilation_rect` | image->image | 2 | max_filter, gray_dilation_rect | 0.0000 | 0.50/0.40 | agree |
| `gray_erosion_rect` | image->image | 2 | min_filter, gray_erosion_rect | 0.0000 | 0.50/0.40 | agree |
| `hysteresis_threshold` | image->region | 2 | sk_hysteresis, hysteresis_threshold | 0.0000 | 0.50/0.40 | agree |
| `invert_image` | image->image | 2 | invert, invert_image | 0.0000 | 0.50/0.40 | agree |
| `prewitt_amp` | image->image | 2 | prewitt_mag, prewitt_amp | 0.0000 | 0.50/0.40 | agree |
| `rank_image` | image->image | 2 | percentile, rank_image | 0.0000 | 0.50/0.40 | agree |
| `roberts` | image->image | 2 | roberts_mag, roberts | 0.0000 | 0.50/0.40 | agree |
| `rotate_image` | image->image | 2 | rotate_img, rotate_image | 0.0000 | 0.50/0.40 | agree |
| `select_shape_std` | region->region | 2 | select_largest, select_shape_std | 0.0000 | 0.50/0.40 | agree |
| `sobel_amp` | image->image | 2 | sobel_mag, sobel_amp | 0.0000 | 0.50/0.40 | agree |
| `thinning` | region->region | 2 | sk_thin, thinning | 0.0000 | 0.50/0.40 | agree |
| `zoom_image_size` | image->image | 2 | rescale_img, zoom_image_size | 0.0000 | 1.00/1.00 | agree |

## Honest reading
- 'agree' means the backends agreed **at the 4 operating points sampled**, on
  these 6 holdout images. It is evidence of agreement, not a proof the operation
  is faithfully implemented: the knob space is not exhausted. Sampling one point
  was not enough — 5 ops agreed exactly at (0.50, 0.40) and diverged by 1.0 at a
  corner, which is why the sweep exists.
- A shared `Op.halcon` is a nearest analogue; two libraries need not implement
  it identically. 'differ' rows are disclosed, not hidden — they show where the
  name is shared but the algorithm/parameters differ (e.g. Canny hysteresis,
  adaptive thresholds, corner kernels).
- 'incomparable' rows are counted, not dropped: an op we could not compare is
  not an op that agreed.
- Parity here is cross-backend, not vs HALCON itself (no license/binary).
