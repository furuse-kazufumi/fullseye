# imgevolve — operator research provenance

Seminal references for the 936 operators (families collapse many variants). The point: a designed pipeline is traceable to the literature, and the RAD image corpus is the mining source for *new* operators.

| op | category | seminal reference |
|---|---|---|
| `identity` | misc | - |
| `gaussian` | smoothing | - |
| `mean_box` | smoothing | - |
| `bilateral` | smoothing | Tomasi & Manduchi (1998). Bilateral filtering for gray and color images. ICCV. |
| `unsharp` | smoothing | - |
| `median` | rank | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `min_filter` | rank | - |
| `max_filter` | rank | - |
| `percentile` | rank | - |
| `gerode` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `gdilate` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `gopen` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `gclose` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `runlength_smear` | morphology | - |
| `tophat` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `bothat` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `morph_grad` | morphology | - |
| `sobel_mag` | edges | Sobel & Feldman (1968). A 3x3 isotropic gradient operator for image processing. |
| `prewitt_mag` | edges | Prewitt, J. (1970). Object enhancement and extraction. Picture Processing and Psychopictorics. |
| `roberts_mag` | edges | - |
| `dog` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `edge_transition_width` | edges | - |
| `gamma` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `quantize_uniform` | gray | - |
| `quantize_lloyd_max` | gray | - |
| `quantization_error` | gray | - |
| `dither_ordered` | gray | - |
| `dither_floyd_steinberg` | gray | - |
| `companding_mu_law` | gray | - |
| `banding_map` | gray | - |
| `effective_bit_depth` | features | - |
| `invert` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `scale_clip` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `equalize` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `sigmoid` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `lowpass` | frequency | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `highpass` | frequency | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `std_filter` | texture | - |
| `local_bimodality` | texture | - |
| `local_std` | texture | - |
| `scale_select_std` | texture | - |
| `bootstrap_std_error` | texture | - |
| `persistence_map` | morphology | - |
| `structure_tensor_orientation` | texture | - |
| `structure_tensor_coherence` | texture | - |
| `local_thickness` | morphology | - |
| `threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `otsu` | segmentation | Otsu, N. (1979). A threshold selection method from gray-level histograms. IEEE TSMC. |
| `reg_erode` | region | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `reg_dilate` | region | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `reg_open` | region | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `reg_close` | region | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `fill_holes` | region | - |
| `select_largest` | region | Rosenfeld & Pfaltz (1966). Connected components labeling. JACM. |
| `remove_small` | region | Rosenfeld & Pfaltz (1966). Connected components labeling. JACM. |
| `invert_region` | region | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `blob_count` | features | Rosenfeld & Pfaltz (1966). Connected components labeling. JACM. |
| `area_frac` | features | Rosenfeld & Pfaltz (1966). Connected components labeling. JACM. |
| `grad_dir` | edges | - |
| `log` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `canny` | segmentation | Canny, J. (1986). A computational approach to edge detection. IEEE TPAMI. |
| `dist_transform` | region | Rosenfeld & Pfaltz (1966). Sequential operations in digital picture processing. JACM. |
| `region_boundary` | region | - |
| `convex_fill` | region | - |
| `select_contours` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `smooth_contours` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `fit_line_contours` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `contours_to_region` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `count_contours` | features | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `total_length` | features | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `ncc_locate` | matching | Lewis, J.P. (1995). Fast normalized cross-correlation. Vision Interface. |
| `rotate_img` | geometry | Wolberg, G. (1990). Digital Image Warping. IEEE CS Press. |
| `deskew` | geometry | - |
| `rescale_img` | geometry | Wolberg, G. (1990). Digital Image Warping. IEEE CS Press. |
| `affine_warp` | geometry | Wolberg, G. (1990). Digital Image Warping. IEEE CS Press. |
| `gabor` | texture | Daugman, J. (1985). Uncertainty relation for resolution... 2D visual cortical filters. JOSA A. |
| `clahe` | gray | Zuiderveld, K. (1994). Contrast Limited Adaptive Histogram Equalization. Graphics Gems IV. |
| `corner_response` | edges | Harris & Stephens (1988). A combined corner and edge detector. Alvey Vision Conf. |
| `adaptive_gauss_thresh` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `shape_locate` | matching | Steger, C. (2002). Occlusion-, clutter-, and illumination-invariant object recognition (shape-based matching). |
| `classify_shape` | classification | Danielsson, P.-E. (1978). A new shape factor (circularity). Computer Graphics and Image Processing. |
| `decode_barcode` | barcode | Wang & Srihari (1988). Object recognition in structured / barcode reading. (1D symbology). |
| `vol_gaussian` | 3d | - |
| `vol_median` | 3d | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `vol_erode` | 3d | - |
| `vol_dilate` | 3d | - |
| `vol_threshold` | 3d | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `vol_reg_dilate` | 3d | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `vol_reg_erode` | 3d | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `vol_dilation_ball` | 3d | - |
| `vol_erosion_ball` | 3d | - |
| `vol_opening_ball` | 3d | - |
| `vol_mip` | 3d | - |
| `vol_slice` | 3d | - |
| `vol_count` | features | - |
| `sk_scharr` | edges | - |
| `sk_farid` | edges | - |
| `sk_frangi` | texture | Frangi et al. (1998). Multiscale vessel enhancement filtering. MICCAI. |
| `sk_meijering` | texture | Meijering et al. (2004). Design and validation of a tool for neurite tracing. Cytometry A. |
| `sk_hessian` | texture | - |
| `sk_dog` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `sk_gabor` | texture | Daugman, J. (1985). Uncertainty relation for resolution... 2D visual cortical filters. JOSA A. |
| `sk_butterworth` | frequency | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `sk_tv` | smoothing | Rudin, Osher & Fatemi (1992). Nonlinear total variation based noise removal (ROF). Physica D. |
| `sk_wavelet` | smoothing | Donoho & Johnstone (1994). Ideal spatial adaptation by wavelet shrinkage. Biometrika. |
| `sk_adapthist` | gray | Zuiderveld, K. (1994). Contrast Limited Adaptive Histogram Equalization. Graphics Gems IV. |
| `sk_median_disk` | rank | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `sk_otsu` | segmentation | Otsu, N. (1979). A threshold selection method from gray-level histograms. IEEE TSMC. |
| `sk_li` | segmentation | Li & Lee (1993). Minimum cross entropy thresholding. Pattern Recognition. |
| `sk_yen` | segmentation | Yen, Chang & Chang (1995). A new criterion for automatic multilevel thresholding. IEEE TIP. |
| `sk_sauvola` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `sk_niblack` | segmentation | Niblack, W. (1986). An Introduction to Digital Image Processing. |
| `sk_canny` | segmentation | Canny, J. (1986). A computational approach to edge detection. IEEE TPAMI. |
| `sk_skeleton` | region | Zhang & Suen (1984). A fast parallel algorithm for thinning digital patterns. CACM. |
| `sk_medial` | region | Blum, H. (1967). A transformation for extracting new descriptors of shape. |
| `sk_convex` | region | Blum, H. (1967). A transformation for extracting new descriptors of shape. |
| `sk_thin` | region | Zhang & Suen (1984). A fast parallel algorithm for thinning digital patterns. CACM. |
| `sk_remove_holes` | region | - |
| `sk_euler` | features | Rosenfeld & Pfaltz (1966). Connected components labeling. JACM. |
| `sk_find_contours` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `sk_lbp` | texture | Ojala, Pietikainen & Maenpaa (2002). Multiresolution gray-scale... local binary patterns. IEEE TPAMI. |
| `sk_entropy` | texture | - |
| `sk_enhance_contrast` | gray | - |
| `sk_autolevel` | gray | - |
| `sk_shape_index` | texture | - |
| `sk_hessian_det` | edges | - |
| `sk_corner_harris` | edges | - |
| `sk_adjust_log` | gray | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `sk_rolling_ball` | smoothing | Sternberg (1983). Biomedical image processing (rolling ball background). IEEE Computer. |
| `sk_nlm` | smoothing | Buades, Coll & Morel (2005). A non-local algorithm for image denoising. CVPR. |
| `sk_tv_bregman` | smoothing | Rudin, Osher & Fatemi (1992). Nonlinear total variation based noise removal (ROF). Physica D. |
| `sk_swirl` | geometry | - |
| `sk_area_opening` | morphology | - |
| `sk_felzenszwalb` | segmentation | Felzenszwalb & Huttenlocher (2004). Efficient graph-based image segmentation. IJCV. |
| `sk_slic` | segmentation | Achanta et al. (2012). SLIC superpixels compared to state-of-the-art. IEEE TPAMI. |
| `sk_chan_vese` | segmentation | Chan & Vese (2001). Active contours without edges. IEEE TIP. |
| `sk_local_maxima` | segmentation | - |
| `sk_hysteresis` | segmentation | - |
| `sk_clear_border` | region | - |
| `sk_find_boundaries` | region | - |
| `sk_entropy_feat` | features | - |
| `sk_blur_effect` | features | - |
| `cv_bilateral` | smoothing | Tomasi & Manduchi (1998). Bilateral filtering for gray and color images. ICCV. |
| `cv_median` | rank | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `cv_box` | smoothing | - |
| `cv_gaussian` | smoothing | - |
| `cv_scharr` | edges | - |
| `cv_laplacian` | edges | - |
| `cv_clahe` | gray | Zuiderveld, K. (1994). Contrast Limited Adaptive Histogram Equalization. Graphics Gems IV. |
| `cv_open` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `cv_close` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `cv_tophat` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `cv_gradient` | morphology | - |
| `cv_otsu` | segmentation | Otsu, N. (1979). A threshold selection method from gray-level histograms. IEEE TSMC. |
| `cv_adaptive_mean` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `cv_adaptive_gauss` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `cv_canny` | segmentation | Canny, J. (1986). A computational approach to edge detection. IEEE TPAMI. |
| `cv_corner_harris` | edges | - |
| `cv_min_eigen` | edges | - |
| `cv_precorner` | edges | - |
| `cv_nlmeans` | smoothing | Buades, Coll & Morel (2005). A non-local algorithm for image denoising. CVPR. |
| `cv_blackhat` | morphology | - |
| `cv_erode` | morphology | - |
| `cv_dilate` | morphology | - |
| `cv_sharpen` | smoothing | - |
| `cv_trunc` | gray | - |
| `cv_dist` | region | - |
| `cv_cc_count` | features | - |
| `cv_hough_lines` | features | Duda & Hart (1972). Use of the Hough transformation to detect lines and curves. CACM. |
| `cv_hough_circles` | features | Duda & Hart (1972). Use of the Hough transformation to detect lines and curves. CACM. |
| `cv_good_features` | features | - |
| `dl_aniso_diffusion` | smoothing | Perona & Malik (1990). Scale-space and edge detection using anisotropic diffusion. IEEE TPAMI. |
| `dl_guided_filter` | smoothing | He, Sun & Tang (2010). Guided image filtering. ECCV. |
| `abs_image` | arithmetic | - |
| `sqrt_image` | arithmetic | - |
| `exp_image` | arithmetic | - |
| `log_image` | arithmetic | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `sin_image` | arithmetic | - |
| `cos_image` | arithmetic | - |
| `asin_image` | arithmetic | - |
| `acos_image` | arithmetic | - |
| `atan_image` | arithmetic | - |
| `gamma_image` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `pow_image` | gray | - |
| `invert_image` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `scale_image` | gray | - |
| `equ_histo_image` | gray | - |
| `illuminate` | gray | - |
| `scale_image_max` | gray | - |
| `gauss_filter` | smoothing | - |
| `gauss_image` | smoothing | - |
| `mean_image` | smoothing | - |
| `binomial_filter` | smoothing | - |
| `smooth_image` | smoothing | - |
| `derivate_gauss` | edges | - |
| `laplace_of_gauss` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `diff_of_gauss` | edges | - |
| `mean_curvature_flow` | smoothing | - |
| `median_image` | rank | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `median_rect` | rank | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `median_separate` | rank | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `gray_erosion_rect` | rank | - |
| `gray_dilation_rect` | rank | - |
| `gray_range_rect` | rank | - |
| `rank_image` | rank | - |
| `rank_rect` | rank | - |
| `sigma_image` | smoothing | - |
| `trimmed_mean` | rank | - |
| `gray_erosion` | morphology | - |
| `gray_dilation` | morphology | - |
| `gray_opening` | morphology | - |
| `gray_closing` | morphology | - |
| `gray_opening_shape` | morphology | - |
| `gray_closing_shape` | morphology | - |
| `gray_tophat` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `gray_bothat` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `sobel_amp` | edges | Sobel & Feldman (1968). A 3x3 isotropic gradient operator for image processing. |
| `sobel_dir` | edges | Sobel & Feldman (1968). A 3x3 isotropic gradient operator for image processing. |
| `prewitt_amp` | edges | Prewitt, J. (1970). Object enhancement and extraction. Picture Processing and Psychopictorics. |
| `prewitt_dir` | edges | Prewitt, J. (1970). Object enhancement and extraction. Picture Processing and Psychopictorics. |
| `roberts` | edges | - |
| `kirsch_amp` | edges | - |
| `kirsch_dir` | edges | - |
| `frei_amp` | edges | - |
| `robinson_amp` | edges | - |
| `laplace` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `fft_image` | frequency | - |
| `power_real` | frequency | - |
| `power_byte` | frequency | - |
| `phase_rad` | frequency | - |
| `highpass_image` | frequency | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `bandpass_image` | frequency | - |
| `anisotropic_diffusion` | smoothing | - |
| `isotropic_diffusion` | smoothing | - |
| `coherence_enhancing_diff` | smoothing | - |
| `bilateral_filter` | smoothing | Tomasi & Manduchi (1998). Bilateral filtering for gray and color images. ICCV. |
| `guided_filter` | smoothing | He, Sun & Tang (2010). Guided image filtering. ECCV. |
| `deviation_image` | texture | - |
| `texture_laws` | texture | - |
| `entropy_image` | texture | - |
| `gen_gabor` | texture | Daugman, J. (1985). Uncertainty relation for resolution... 2D visual cortical filters. JOSA A. |
| `mirror_image` | geometry | - |
| `transpose_region` | geometry | - |
| `rotate_image` | geometry | - |
| `zoom_image_factor` | geometry | - |
| `zoom_image_size` | geometry | - |
| `affine_trans_image` | geometry | - |
| `polar_trans_image` | geometry | - |
| `h_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `binary_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `auto_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `dyn_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `var_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `local_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `hysteresis_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `edges_image` | segmentation | - |
| `watersheds` | segmentation | - |
| `watersheds_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `regiongrowing` | segmentation | - |
| `local_max` | segmentation | - |
| `erosion_circle` | region | - |
| `dilation_circle` | region | - |
| `opening_circle` | region | - |
| `closing_circle` | region | - |
| `erosion_rectangle1` | region | - |
| `dilation_rectangle1` | region | - |
| `opening_rectangle1` | region | - |
| `closing_rectangle1` | region | - |
| `fill_up` | region | - |
| `boundary` | region | - |
| `skeleton` | region | - |
| `thinning` | region | Zhang & Suen (1984). A fast parallel algorithm for thinning digital patterns. CACM. |
| `shape_trans` | region | - |
| `select_shape_std` | region | - |
| `select_shape` | region | - |
| `distance_transform` | region | - |
| `area_center` | features | - |
| `count_obj` | features | - |
| `circularity` | features | - |
| `compactness` | features | - |
| `convexity` | features | - |
| `rectangularity` | features | - |
| `eccentricity` | features | - |
| `orientation_region` | features | - |
| `roundness` | features | - |
| `diameter_region` | features | - |
| `euler_number` | features | - |
| `min_max_gray` | features | - |
| `intensity` | features | - |
| `gray_histo_abs` | features | - |
| `entropy_gray` | features | - |
| `edges_sub_pix` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `lines_gauss` | contour | - |
| `select_contours_xld` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `smooth_contours_xld` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `gen_region_contour_xld` | contour | - |
| `length_xld` | features | - |
| `contlength` | features | - |
| `area_holes` | features | - |
| `height_width_ratio` | features | - |
| `moments_region_2nd` | features | - |
| `moments_region_2nd_invar` | features | - |
| `cooc_feature_matrix` | texture | - |
| `equ_histo_image_rect` | gray | - |
| `simulate_motion` | smoothing | - |
| `projective_trans_image` | geometry | - |
| `projective_trans_image_size` | geometry | - |
| `projective_trans_region` | geometry | - |
| `polar_trans_image_inv` | geometry | - |
| `fft_image_inv` | frequency | - |
| `add_noise_white` | noise | - |
| `area_center_xld` | features | - |
| `circularity_xld` | features | - |
| `compactness_xld` | features | - |
| `convexity_xld` | features | - |
| `close_contours_xld` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `affine_trans_contour_xld` | contour | - |
| `projective_trans_contour_xld` | contour | - |
| `polar_trans_contour_xld` | contour | - |
| `moments_region_3rd` | features | - |
| `moments_region_central` | features | - |
| `moments_region_central_invar` | features | - |
| `moments_region_2nd_rel_invar` | features | - |
| `moments_region_3rd_invar` | features | - |
| `dual_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `segment_image_mser` | segmentation | - |
| `regiongrowing_mean` | segmentation | - |
| `estimate_noise` | features | - |
| `points_foerstner` | edges | - |
| `points_harris_binomial` | edges | - |
| `eccentricity_xld` | features | - |
| `orientation_xld` | features | - |
| `elliptic_axis_xld` | features | - |
| `diameter_xld` | features | - |
| `rectangularity_xld` | features | - |
| `moments_xld` | features | - |
| `shape_trans_xld` | contour | - |
| `zero_crossing` | segmentation | - |
| `local_min` | segmentation | - |
| `pruning` | region | - |
| `hough_line_trans` | features | Duda & Hart (1972). Use of the Hough transformation to detect lines and curves. CACM. |
| `hough_circle_trans` | features | Duda & Hart (1972). Use of the Hough transformation to detect lines and curves. CACM. |
| `threshold_sub_pix` | contour | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `zero_crossing_sub_pix` | contour | - |
| `closest_point_transform` | region | - |
| `junctions_skeleton` | region | - |
| `get_region_thickness` | features | - |
| `tan_image` | arithmetic | - |
| `bit_not` | gray | - |
| `monotony` | gray | - |
| `eliminate_min_max` | rank | - |
| `median_weighted` | rank | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `mean_sp` | rank | - |
| `eliminate_sp` | rank | - |
| `simulate_defocus` | smoothing | - |
| `dots_image` | edges | - |
| `frei_dir` | edges | - |
| `robinson_dir` | edges | - |
| `fft_generic` | frequency | - |
| `power_ln` | frequency | - |
| `rft_generic` | frequency | - |
| `phase_deg` | frequency | - |
| `affine_trans_image_size` | geometry | - |
| `polar_trans_image_ext` | geometry | - |
| `lines_facet` | contour | - |
| `add_noise_distribution` | noise | - |
| `bin_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `erosion_golay` | region | - |
| `dilation_golay` | region | - |
| `opening_golay` | region | - |
| `closing_golay` | region | - |
| `erosion_seq` | region | - |
| `dilation_seq` | region | - |
| `morph_skeleton` | region | - |
| `thinning_golay` | region | Zhang & Suen (1984). A fast parallel algorithm for thinning digital patterns. CACM. |
| `thinning_seq` | region | Zhang & Suen (1984). A fast parallel algorithm for thinning digital patterns. CACM. |
| `gray_erosion_shape` | morphology | - |
| `gray_dilation_shape` | morphology | - |
| `gray_opening_rect` | morphology | - |
| `gray_closing_rect` | morphology | - |
| `dual_rank` | rank | - |
| `fast_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `nonmax_suppression_amp` | segmentation | - |
| `pouring` | segmentation | - |
| `affine_trans_region` | geometry | - |
| `mirror_region` | geometry | - |
| `zoom_region` | geometry | - |
| `fill_up_shape` | region | - |
| `remove_noise_region` | region | - |
| `smallest_rectangle1` | region | - |
| `get_region_contour` | region | - |
| `get_region_convex` | region | - |
| `gen_region_polygon_xld` | contour | - |
| `connect_and_holes` | features | - |
| `elliptic_axis` | features | - |
| `polar_trans_region_inv` | geometry | - |
| `affine_trans_polygon_xld` | contour | - |
| `gen_contour_region_xld` | contour | - |
| `select_shape_xld` | contour | - |
| `contour_point_num_xld` | contour | - |
| `cfa_to_rgb` | color | - |
| `trans_from_rgb` | color | - |
| `trans_to_rgb` | color | - |
| `linear_trans_color` | color | - |
| `principal_comp` | color | - |
| `rgb1_to_gray` | color | - |
| `rgb3_to_gray` | color | - |
| `access_channel` | color | - |
| `edges_color` | edges | - |
| `edges_color_sub_pix` | contour | - |
| `lines_color` | contour | - |
| `count_channels` | features | - |
| `xsk_inpaint` | restoration | - |
| `xsk_richardson_lucy` | restoration | - |
| `xsk_unwrap_phase` | restoration | - |
| `xsk_struct_coherence` | texture | - |
| `xsk_hessian_eig` | edges | - |
| `xsk_random_walker` | segmentation | - |
| `xsk_flood` | segmentation | - |
| `xsk_blob_log` | features | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `xsk_blob_dog` | features | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `xsk_blob_doh` | features | - |
| `xsk_orb_count` | features | - |
| `xsk_meijering` | texture | Meijering et al. (2004). Design and validation of a tool for neurite tracing. Cytometry A. |
| `xsk_sato` | texture | - |
| `xcv_stylization` | artistic | - |
| `xcv_pencil_sketch` | artistic | - |
| `xcv_edge_preserving` | smoothing | - |
| `xcv_detail_enhance` | gray | - |
| `xcv_inpaint` | restoration | - |
| `xcv_grabcut` | segmentation | - |
| `xcv_watershed_markers` | segmentation | - |
| `xcv_orb_count` | features | - |
| `xpil_emboss` | artistic | - |
| `xpil_contour` | edges | - |
| `xpil_find_edges` | edges | - |
| `xpil_edge_enhance` | gray | - |
| `xpil_smooth_more` | smoothing | - |
| `xpil_detail` | gray | - |
| `xpil_mode_filter` | rank | - |
| `xpil_unsharp_mask` | smoothing | - |
| `xpil_posterize` | gray | - |
| `xpil_solarize` | gray | - |
| `xpil_autocontrast` | gray | - |
| `xpil_offset` | geometry | - |
| `xpil_contrast` | gray | - |
| `xsp_wiener` | smoothing | - |
| `xsp_savgol` | smoothing | - |
| `xsp_hilbert_env` | texture | - |
| `xsp_dct` | frequency | - |
| `xsp_dct_lowpass` | frequency | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `xsp_dct_denoise` | smoothing | - |
| `xsp_cspline_smooth` | smoothing | - |
| `xsp_detrend_flatten` | gray | - |
| `xsp_morph_laplace` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `xsp_chamfer_dist` | region | - |
| `xsp_gauss_grad_mag` | edges | - |
| `xsk2_multiotsu` | segmentation | Otsu, N. (1979). A threshold selection method from gray-level histograms. IEEE TSMC. |
| `xsk2_rank_geomean` | rank | - |
| `xsk2_reconstruction` | morphology | - |
| `xsk2_h_maxima` | segmentation | - |
| `xsk2_diameter_opening` | morphology | - |
| `xsk2_isotropic_close` | region | - |
| `xsk2_hog` | texture | - |
| `xsk2_corner_kr` | edges | - |
| `xsk2_radon` | frequency | - |
| `xsk2_inv_gauss_grad` | edges | - |
| `xsk2_wiener` | restoration | - |
| `xcv2_warp_logpolar` | geometry | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `xcv2_meanshift` | segmentation | - |
| `xcv2_hitmiss` | region | - |
| `xcv2_lap_var` | features | - |
| `xcv2_fast_count` | features | - |
| `xmh_zernike` | texture/shape-feature | - |
| `xmh_pftas` | texture-feature | - |
| `xmh_bernsen` | segmentation | - |
| `xmh_majority` | region-morphology | - |
| `xmh_haar` | transform | - |
| `xmh_daubechies` | transform | - |
| `xmh_soft` | intensity-transform | - |
| `xmh_bwperim` | region-transform | - |
| `xmh_regmin` | morphology/markers | - |
| `xmh_selfmatch` | self-similarity | - |
| `xwt_subband_tile` | frequency | - |
| `xwt_visushrink` | smoothing | - |
| `xwt_firm_denoise` | smoothing | - |
| `xwt_detail_energy` | features | - |
| `xwt_hf_reconstruct` | edges | - |
| `xwt_lf_reconstruct` | smoothing | - |
| `xwt_directional_detail` | edges | - |
| `xwt_packet_entropy` | features | - |
| `xwt_mra_component` | frequency | - |
| `xsitk_curvature_flow` | extra | - |
| `xsitk_minmax_curv_flow` | extra | - |
| `xsitk_curv_aniso_diff` | extra | - |
| `xsitk_laplacian_sharpen` | extra | - |
| `xsitk_grayscale_fillhole` | extra | - |
| `xsitk_grayscale_grindpeak` | extra | - |
| `xsitk_opening_by_recon` | extra | - |
| `xsitk_closing_by_recon` | extra | - |
| `xsitk_signed_maurer_dist` | extra | - |
| `xsitk_connected_threshold` | extra | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `xsitk_confidence_connected` | extra | - |
| `xsitk_maxentropy_thresh` | extra | - |
| `xsitk_moments_thresh` | extra | - |
| `xsitk_huang_thresh` | extra | - |
| `xsk3_rank_otsu` | segmentation | Otsu, N. (1979). A threshold selection method from gray-level histograms. IEEE TSMC. |
| `xsk3_rank_majority` | region | - |
| `xsk3_rank_subtract_mean` | gray | - |
| `xsk3_rank_equalize` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `xsk3_rank_mean_bilateral` | smoothing | Tomasi & Manduchi (1998). Bilateral filtering for gray and color images. ICCV. |
| `xsk3_h_minima` | segmentation | - |
| `xsk3_area_closing` | morphology | - |
| `xsk3_diameter_closing` | morphology | - |
| `xsk3_corner_moravec` | edges | - |
| `xsk3_corner_fast` | edges | - |
| `xsk3_integral_image` | gray | - |
| `xsk3_threshold_local_median` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `xsk3_is_low_contrast` | features | - |
| `xsk3_estimate_sigma` | features | - |
| `xsk3_peak_local_max` | segmentation | - |
| `xcv3_denoise_tvl1` | smoothing | - |
| `xcv3_inpaint_ns` | restoration | - |
| `xcv3_pyr_laplacian` | smoothing | - |
| `xcv3_gray_hu1` | features | - |
| `xcv3_sift_count` | features | - |
| `xcv3_brisk_count` | features | - |
| `xcv3_agast_count` | features | - |
| `xcv3_lsd_count` | features | - |
| `xkor_gaussian` | smoothing | - |
| `xkor_bilateral` | smoothing | Tomasi & Manduchi (1998). Bilateral filtering for gray and color images. ICCV. |
| `xkor_median` | rank | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `xkor_unsharp` | smoothing | - |
| `xkor_motion_blur` | smoothing | - |
| `xkor_canny` | segmentation | Canny, J. (1986). A computational approach to edge detection. IEEE TPAMI. |
| `xkor_clahe` | gray | Zuiderveld, K. (1994). Contrast Limited Adaptive Histogram Equalization. Graphics Gems IV. |
| `xkor_laplacian` | edges | - |
| `xkor_harris` | edges | - |
| `xkor_gftt` | edges | - |
| `xkor_hessian` | edges | - |
| `xkor_dog` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `f2_shock` | edges | - |
| `f2_shock_diffuse` | edges | - |
| `f2_gray_skeleton` | morphology | - |
| `f2_lut_trans` | gray | - |
| `f2_topographic` | edges | - |
| `f2_expand_domain` | gray | - |
| `f2_symmetry` | texture | - |
| `f2_gauss_pyramid` | smoothing | - |
| `f2_gray_inside` | morphology | - |
| `f2_bit_slice` | gray | - |
| `r2_inner_circle` | region | - |
| `r2_inner_rectangle1` | region | - |
| `r2_smallest_rectangle1` | region | - |
| `r2_smallest_circle` | region | - |
| `r2_smallest_rectangle2` | region | - |
| `r2_sort_region` | region | - |
| `r2_union1` | region | - |
| `r2_partition_rectangle` | region | - |
| `r2_runlength_features` | region | - |
| `r2_split_skeleton_lines` | region | - |
| `em_skeleton` | region | - |
| `r2_endpoints_skeleton` | region | - |
| `sp_local_max_sub_pix` | subpix | - |
| `sp_local_min_sub_pix` | subpix | - |
| `sp_saddle_points_sub_pix` | subpix | - |
| `sp_critical_points_sub_pix` | subpix | - |
| `sp_plateaus` | subpix | - |
| `sp_lowlands_center` | subpix | - |
| `xg_moments` | xldgeom | - |
| `xg_area_center` | xldgeom | - |
| `xg_eccentricity` | xldgeom | - |
| `xg_orientation` | xldgeom | - |
| `xg_elliptic_axis` | xldgeom | - |
| `xg_height_width_ratio` | xldgeom | - |
| `xg_regress_contours` | xldgeom | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `xg_clip_contours` | xldgeom | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `xg_gen_polygons` | xldgeom | - |
| `xg_crop_contours` | xldgeom | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `r3_background_seg` | region | - |
| `r3_clip_region` | region | - |
| `r3_eliminate_runs` | region | - |
| `r3_rank_region` | region | - |
| `r3_region_features` | region | - |
| `r3_runlength_distribution` | region | - |
| `r3_select_region_point` | region | - |
| `r3_partition_dynamic` | region | - |
| `r3_polar_trans_region` | region | - |
| `r3_label_to_region` | region | - |
| `it_add_image_border` | geometry | - |
| `it_crop_part` | geometry | - |
| `it_crop_rectangle1` | geometry | - |
| `it_bit_lshift` | gray | - |
| `it_bit_rshift` | gray | - |
| `it_bit_mask` | gray | - |
| `it_convert_image_type` | gray | - |
| `it_change_format` | geometry | - |
| `it_region_to_bin` | segmentation | - |
| `it_full_domain` | domain | - |
| `it_crop_domain` | domain | - |
| `m1_measure_projection` | measure1d | - |
| `m1_measure_pos` | measure1d | - |
| `m1_measure_thresh` | measure1d | - |
| `m1_measure_pairs` | measure1d | - |
| `m1_fuzzy_measure_pos` | measure1d | - |
| `ph_perona_malik` | physics | - |
| `ph_coherence_enhancing_diffusion` | physics | - |
| `ph_reaction_diffusion` | physics | - |
| `ph_heat_flow` | physics | - |
| `ph_mean_curvature_motion` | physics | - |
| `ph_total_variation_flow` | physics | - |
| `dc_structure_texture` | decomposition | - |
| `dc_texture_residual` | decomposition | - |
| `dc_rpca_lowrank` | decomposition | - |
| `dc_rpca_sparse` | decomposition | - |
| `dc_retinex` | decomposition | - |
| `dc_local_contrast_norm` | decomposition | - |
| `dc_homomorphic` | decomposition | - |
| `iv_richardson_lucy` | restoration | - |
| `iv_wiener_deconv_spatial` | restoration | - |
| `iv_unsharp_deblur` | restoration | - |
| `iv_motion_deblur` | restoration | - |
| `iv_backproject_superres` | restoration | - |
| `iv_gradient_inpaint` | restoration | - |
| `tf_log_polar` | geometry | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `tf_radon_sinogram` | transform | - |
| `tf_steerable_filter` | edges | - |
| `tf_phase_congruency` | edges | - |
| `tf_gradient_domain_reintegrate` | filtering | - |
| `tf_census_transform` | texture | - |
| `tf_rank_transform` | texture | - |
| `sg_slic_superpixels` | segment | - |
| `sg_felzenszwalb` | segment | - |
| `sg_gmm_segment` | segment | - |
| `sg_kmeans_intensity` | segment | - |
| `sg_region_growing_seeded` | segment | - |
| `sg_normalized_cut_2` | segment | - |
| `sg_watershed_gradient` | segment | - |
| `tm_radon_forward` | tomography | - |
| `tm_fbp_reconstruct` | tomography | - |
| `tm_sart_reconstruct` | tomography | - |
| `tm_backproject_unfiltered` | tomography | - |
| `tm_sinogram_denoise` | tomography | - |
| `aug_shot_noise` | augmentation | - |
| `aug_read_noise` | augmentation | - |
| `aug_fixed_pattern` | augmentation | - |
| `aug_motion_blur` | augmentation | - |
| `aug_vignette` | augmentation | - |
| `aug_chromatic` | augmentation | - |
| `aug_rolling_shutter` | augmentation | - |
| `aug_jpeg_blocks` | augmentation | - |
| `aug_cutout` | augmentation | - |
| `aug_barrel` | augmentation | - |
| `alife_gray_scott` | artificial-life | - |
| `alife_turing` | artificial-life | - |
| `alife_life_step` | artificial-life | - |
| `alife_cyclic_ca` | artificial-life | - |
| `alife_perona_malik` | artificial-life | - |
| `alife_curvature_flow` | artificial-life | - |
| `alife_dla` | artificial-life | - |
| `alife_reaction_bz` | artificial-life | - |
| `tac_contact_mask` | tactile | - |
| `tac_height_from_shading` | tactile | - |
| `tac_surface_normal` | tactile | - |
| `tac_pressure_proxy` | tactile | - |
| `tac_shear_field` | tactile | - |
| `fractal_dimension` | features | - |
| `alife_wolfram1d` | artificial-life | - |
| `alife_langton_ant` | artificial-life | - |
| `alife_lenia` | artificial-life | - |
| `alife_sandpile` | artificial-life | - |
| `deform_tps` | deformation | - |
| `deform_ffd` | deformation | - |
| `deform_mls` | deformation | - |
| `hx_gen_circle` | halcon_ext | - |
| `hx_gen_ellipse` | halcon_ext | - |
| `hx_gen_rectangle2` | halcon_ext | - |
| `hx_gen_checker_region` | halcon_ext | - |
| `hx_gen_grid_region` | halcon_ext | - |
| `hx_gabor` | halcon_ext | Daugman, J. (1985). Uncertainty relation for resolution... 2D visual cortical filters. JOSA A. |
| `hx_fit_surface1` | halcon_ext | - |
| `hx_fit_surface2` | halcon_ext | - |
| `hx_cooc_feature` | halcon_ext | - |
| `hx_full_domain` | halcon_ext | - |
| `hx_mean_shape` | halcon_ext | - |
| `hx_close_edges` | halcon_ext | - |
| `hx_close_edges_length` | halcon_ext | - |
| `hx_expand_region` | halcon_ext | - |
| `hx_region_to_mean` | halcon_ext | - |
| `hx_nonmax_dir` | halcon_ext | - |
| `hx_char_threshold` | halcon_ext | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `hx_histo_to_thresh` | halcon_ext | - |
| `hx_gen_lowpass` | halcon_ext | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `hx_gen_highpass` | halcon_ext | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `hx_gen_bandpass` | halcon_ext | - |
| `hx_erosion1` | halcon_ext | - |
| `hx_dilation1` | halcon_ext | - |
| `hx_opening` | halcon_ext | - |
| `hx_closing` | halcon_ext | - |
| `hx_dilation2` | halcon_ext | - |
| `hx_gen_disc_se` | halcon_ext | - |
| `hx_gen_circle_sector` | halcon_ext | - |
| `hx_gen_ellipse_sector` | halcon_ext | - |
| `hx_gen_empty_region` | halcon_ext | - |
| `hx_clip_region_rel` | halcon_ext | - |
| `hx_gen_bandfilter` | halcon_ext | - |
| `hx_gen_derivative_filter` | halcon_ext | - |
| `hx_fill_interlace` | halcon_ext | - |
| `hx_shade_height_field` | halcon_ext | - |
| `hx_plane_deviation` | halcon_ext | - |
| `hx_detect_edge_segments` | halcon_ext | - |
| `hx_gen_image_proto` | halcon_ext | - |
| `hx_get_domain` | halcon_ext | - |
| `hx_region_to_label` | halcon_ext | - |
| `hx_rectangle1_domain` | halcon_ext | - |
| `hx_lowlands` | halcon_ext | - |
| `hx_plateaus_center` | halcon_ext | - |
| `hx_move_region` | halcon_ext | - |
| `hx_split_skeleton_region` | halcon_ext | - |
| `hx_test_region_point` | halcon_ext | - |
| `hx_test_region_points` | halcon_ext | - |
| `hx_sort_contours` | halcon_ext | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `hx_clip_contours` | halcon_ext | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `hx_clip_end_points` | halcon_ext | - |
| `hx_smallest_circle_xld` | halcon_ext | - |
| `hx_smallest_rect1_xld` | halcon_ext | - |
| `hx_test_closed_xld` | halcon_ext | - |
| `hx_regress_contours` | halcon_ext | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `hx_moments_any_xld` | halcon_ext | - |
| `hx_split_contours` | halcon_ext | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `hx_gen_parallel_contour` | halcon_ext | - |
| `hx_fit_circle_contour` | halcon_ext | - |
| `hx_fit_ellipse_contour` | halcon_ext | - |
| `hx_fit_rectangle2_contour` | halcon_ext | - |
| `hx_smallest_rect2_xld` | halcon_ext | - |
| `hx_crop_contours` | halcon_ext | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `hx_dist_ellipse_contour` | halcon_ext | - |
| `hx_test_self_intersect` | halcon_ext | - |
| `hx_union_adjacent` | halcon_ext | - |
| `hx_polar_trans_inv` | halcon_ext | - |
| `hx_select_xld_point` | halcon_ext | - |
| `hx_estimate_tilt_lr` | halcon_ext | - |
| `hx_estimate_tilt_zc` | halcon_ext | - |
| `hx_estimate_sl_al_lr` | halcon_ext | - |
| `hx_estimate_sl_al_zc` | halcon_ext | - |
| `hx_estimate_al_am` | halcon_ext | - |
| `hx_add_noise_contour` | halcon_ext | - |
| `hx_radial_distort_contour` | halcon_ext | - |
| `hx_dist_ellipse_points` | halcon_ext | - |
| `hx_dist_rect2_points` | halcon_ext | - |
| `hx_distance_pc` | halcon_ext | - |
| `hx_disparity_to_xyz` | halcon_ext | - |
| `hx_distance_pr` | halcon_ext | - |
| `hx_distance_sc` | halcon_ext | - |
| `hx_fuzzy_measure_pairs` | halcon_ext | - |
| `macro_denoise` | macro | - |
| `macro_edge` | macro | - |
| `macro_binarize` | macro | - |
| `macro_vol_denoise` | macro | - |
| `tb_points_to_voxel` | typed | - |
| `tb_estimate_point_normals` | typed | - |
| `tb_iss_keypoints` | typed | - |
| `tb_project_points` | typed | - |
| `tb_render_point_depth` | typed | - |
| `tb_statistical_outlier_removal` | typed | - |
| `tb_radius_outlier_removal` | typed | - |
| `tb_voxel_grid_downsample` | typed | - |
| `tb_mls_smooth` | typed | - |
| `tb_alpha_shape_boundary` | typed | - |
| `tb_estimate_alpha` | typed | - |
| `tb_arc_length` | typed | - |
| `tb_resample_uniform` | typed | - |
| `tb_fit_spline_curve` | typed | - |
| `tb_mean_curvature` | typed | - |
| `tb_gaussian_curvature` | typed | - |
| `tb_estimate_normals` | typed | - |
| `tb_inertia_tensor` | typed | - |
| `tb_geodesic_distances` | typed | - |
| `tb_farthest_point_sampling` | typed | - |
| `tb_synthesize_silhouette` | typed | - |
| `tb_inside_outside` | typed | - |
| `tb_superquadric_residual` | typed | - |
| `tb_project` | typed | - |
| `tb_jitter` | typed | - |
| `tb_random_rotation` | typed | - |
| `tb_random_scale` | typed | - |
| `tb_random_dropout` | typed | - |
| `tb_elastic_deform` | typed | - |
| `tb_cutout` | typed | - |
| `tb_region_growing` | typed | - |
| `tb_euclidean_cluster` | typed | - |
| `tb_plane_segmentation` | typed | - |
| `tb_estimate_oriented_normals` | typed | - |
| `tb_occupancy_grid` | typed | - |
| `tb_reflect_points` | typed | - |
| `tb_reflection_symmetry_score` | typed | - |
| `tb_project_spherical` | typed | - |
| `tb_project_cylindrical` | typed | - |
| `tb_sphere_sdf` | typed | - |
| `tb_box_sdf` | typed | - |
| `tb_plane_sdf` | typed | - |
| `tb_cylinder_sdf` | typed | - |
| `tb_torus_sdf` | typed | - |
| `tb_capsule_sdf` | typed | - |
| `tb_pc_poisson_disk` | typed | - |
| `tb_pc_fill_sparse` | typed | - |
| `tb_pc_density_equalize` | typed | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `tb_create_funct_1d_array` | typed | - |
| `tb_smooth_funct_1d_gauss` | typed | - |
| `tb_smooth_funct_1d_mean` | typed | - |
| `tb_derivate_funct_1d` | typed | - |
| `tb_integrate_funct_1d` | typed | - |
| `tb_zero_crossings_funct_1d` | typed | - |
| `tb_abs_funct_1d` | typed | - |
| `tb_negate_funct_1d` | typed | - |
| `tb_scale_y_funct_1d` | typed | - |
| `tb_sample_funct_1d` | typed | - |
| `tb_num_points_funct_1d` | typed | - |
| `tb_get_y_value_funct_1d` | typed | - |
| `tb_lowpass` | typed | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `tb_highpass` | typed | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `tb_bandpass` | typed | - |
| `tb_envelope` | typed | - |
| `tb_rms` | typed | - |
| `tb_local_std` | typed | - |
| `tb_quantize` | typed | - |
| `tb_companding_mu_law` | typed | - |
| `tb_resample` | typed | - |
| `tb_spectrogram` | typed | - |
| `tb_zero_crossing_rate` | typed | - |
| `tb_find_peaks` | typed | - |
| `tb_cx_ifft` | typed | - |
| `tb_cx_magnitude` | typed | - |
| `tb_cx_phase` | typed | - |
| `tb_cx_real` | typed | - |
| `tb_cx_imag` | typed | - |
| `tb_cx_log_magnitude` | typed | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `tb_cx_apply_transfer_function` | typed | - |
| `tb_mat_pinv` | typed | - |
| `tb_mat_cond` | typed | - |
| `tb_stat_covariance` | typed | - |
| `tb_stat_correlation` | typed | - |
| `tb_stat_zscore` | typed | - |
| `tb_cplx_cr_residual` | typed | - |
| `tb_dynsys_correlation_dimension` | typed | - |
| `tb_angular_spectrum_propagate` | typed | - |
| `tb_wetness` | typed | - |
| `tb_env_studio` | typed | - |
| `tb_env_lightbox` | typed | - |
| `tb_sensor_capture` | typed | - |
| `tb_lf_to_mla` | typed | - |
| `tb_lf_subaperture` | typed | - |
| `tb_lf_center_view` | typed | - |
| `tb_lf_epi` | typed | - |
| `tb_lf_refocus` | typed | - |
| `tb_lf_synthetic_aperture` | typed | - |
| `tb_lf_depth_from_focus` | typed | - |
| `tb_lf_epi_slope` | typed | - |
| `tb_spad_deadtime_apply` | typed | - |
| `tb_spad_deadtime_correct` | typed | - |
| `tb_tcspc_coates_correct` | typed | - |
| `tb_tcspc_irf_convolve` | typed | - |
| `tb_tcspc_background_subtract` | typed | - |
| `tb_dtof_depth` | typed | - |
| `tb_specular_diffuse_split` | typed | - |
| `tb_specular_coefficient_map` | typed | - |
| `tb_specular_free_transform` | typed | - |
| `tb_temporal_bandpass` | typed | - |
| `tb_temporal_band_power` | typed | - |
| `tb_rgb_to_quaternion` | typed | - |
| `tb_quaternion_to_rgb` | typed | - |
| `tb_quat_norm` | typed | - |
| `tb_quat_conjugate_image` | typed | - |
| `tb_quat_normalize_image` | typed | - |
| `tb_monogenic_amplitude` | typed | - |
| `tb_monogenic_phase` | typed | - |
| `tb_monogenic_orientation` | typed | - |
| `tb_quat_color_rotate` | typed | - |
| `tb_quat_color_filter` | typed | - |
| `tb_qft2` | typed | - |
| `tb_iqft2` | typed | - |
| `tb_fmcw_window_apply` | typed | - |
| `tb_range_doppler_map` | typed | - |
| `tb_fmcw_range_profile` | typed | - |
| `tb_beamform_delay_sum` | typed | - |
| `tb_weighting_response` | typed | - |
| `tb_apply_weighting` | typed | - |
| `tb_equivalent_level` | typed | - |
| `tb_fly_lgmd_eta` | typed | - |
| `tb_fly_tau_from_expansion` | typed | - |
| `tb_magnus_lift_coefficient` | typed | - |
| `tb_drag_coefficient_sphere` | typed | - |
| `tb_intrinsics_to_fullseye` | typed | - |
| `tb_intrinsics_to_carla` | typed | - |
| `tb_normals_to_egi` | typed | - |
| `tb_keypoints_uv_to_points` | typed | - |
| `tb_points_zyx_to_keypoints_uv` | typed | - |
| `tb_keypoints_to_image2d` | typed | - |
| `tb_countrate_to_counts` | typed | - |
| `tb_counts_to_countrate` | typed | - |
| `tb_temporal_median_window` | typed | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `tb_moving_average_window` | typed | - |
| `tb_background_subtraction_window` | typed | - |
| `tb_frame_difference_causal` | typed | - |
| `tb_exponential_background` | typed | - |
| `tb_exponential_foreground` | typed | - |
| `tb_optical_flow_magnitude_stream` | typed | - |
| `tb_motion_history_image` | typed | - |
| `tb_motion_energy_image` | typed | - |
| `tb_three_frame_difference` | typed | - |
| `tb_running_gaussian_foreground` | typed | - |
| `tb_running_gaussian_background` | typed | - |
| `tb_temporal_bilateral` | typed | Tomasi & Manduchi (1998). Bilateral filtering for gray and color images. ICCV. |
| `tb_deflicker` | typed | - |
| `tb_shape_perturb` | typed | - |
| `tb_mirror_plane_from_pairs` | typed | - |
| `tb_landmark_asymmetry` | typed | - |
| `tb_dem_ecef_to_geodetic` | typed | - |
| `img_to_points` | bridge | - |
| `img_to_keypoints` | bridge | - |
| `img_to_signal` | bridge | - |
| `img_to_projection_profile` | bridge | - |
| `img_to_counts` | bridge | - |
| `img_to_matrix` | bridge | - |
| `img_to_video` | bridge | - |
| `img_to_volume` | bridge | - |
| `img_to_lightfield` | bridge | - |
| `img_to_rgb` | bridge | - |
| `img_to_cimage` | bridge | - |
| `img_to_beatcube` | bridge | - |
| `img_to_monogenic` | bridge | - |
| `signal_to_img` | bridge | - |
| `counts_to_img` | bridge | - |
| `matrix_to_img` | bridge | - |
| `contour_to_img` | bridge | - |
| `feature_to_img` | bridge | - |

**Provenance coverage: 173/936 operators cite a seminal paper.**

## Mining new operators from research (RAD)
- RAD image / diffusion / deep_learning corpora (thousands of papers) = the source for operators beyond the classics: modern denoisers (BM3D, DnCNN), learned edges (HED), superpixels (SLIC), diffusion priors, foundation segmenters (SAM).
- Workflow: mine a paper -> add a typed Op (fn + sort + analogs + this reference) -> evolution/codegen/catalog pick it up automatically.
