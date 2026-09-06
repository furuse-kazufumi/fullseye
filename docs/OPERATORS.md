# imgevolve — cross-library operator catalog

885 operators across 47 categories, typed by sort (image/region/feature). Each maps to the nearest single-call API in HALCON / OpenCV / scikit-image / MATLAB. `-` = no direct one-call analog.

| op | sort | category | halcon | opencv | skimage | matlab |
|---|---|---|---|---|---|---|
| `identity` | any | misc | copy_image | copyTo | - | - |
| `gaussian` | image | smoothing | gauss_filter | GaussianBlur | filters.gaussian | imgaussfilt |
| `mean_box` | image | smoothing | mean_image | blur/boxFilter | filters.rank.mean | imboxfilt |
| `bilateral` | image | smoothing | bilateral_filter | bilateralFilter | restoration.denoise_bilateral | imbilatfilt |
| `unsharp` | image | smoothing | emphasize | addWeighted | filters.unsharp_mask | imsharpen |
| `median` | image | rank | median_image | medianBlur | filters.median | medfilt2 |
| `min_filter` | image | rank | gray_erosion_rect | erode | filters.rank.minimum | ordfilt2 |
| `max_filter` | image | rank | gray_dilation_rect | dilate | filters.rank.maximum | ordfilt2 |
| `percentile` | image | rank | rank_image | - | filters.rank.percentile | ordfilt2 |
| `gerode` | image | morphology | gray_erosion | erode | morphology.erosion | imerode |
| `gdilate` | image | morphology | gray_dilation | dilate | morphology.dilation | imdilate |
| `gopen` | image | morphology | gray_opening | morphologyEx(OPEN) | morphology.opening | imopen |
| `gclose` | image | morphology | gray_closing | morphologyEx(CLOSE) | morphology.closing | imclose |
| `tophat` | image | morphology | gray_tophat | morphologyEx(TOPHAT) | morphology.white_tophat | imtophat |
| `bothat` | image | morphology | gray_bothat | morphologyEx(BLACKHAT) | morphology.black_tophat | imbothat |
| `morph_grad` | image | morphology | gray_range_rect | morphologyEx(GRADIENT) | - | - |
| `sobel_mag` | image | edges | sobel_amp | Sobel | filters.sobel | edge(...,'sobel') |
| `prewitt_mag` | image | edges | prewitt_amp | - | filters.prewitt | edge(...,'prewitt') |
| `roberts_mag` | image | edges | roberts | - | filters.roberts | edge(...,'roberts') |
| `dog` | image | edges | diff_of_gauss | - | filters.difference_of_gaussians | - |
| `gamma` | image | gray | pow_image | LUT | exposure.adjust_gamma | imadjust |
| `invert` | image | gray | invert_image | bitwise_not | util.invert | imcomplement |
| `scale_clip` | image | gray | scale_image | convertScaleAbs | exposure.rescale_intensity | imadjust |
| `equalize` | image | gray | equ_histo_image | equalizeHist | exposure.equalize_hist | histeq |
| `sigmoid` | image | gray | scale_image_max | - | exposure.adjust_sigmoid | - |
| `lowpass` | image | frequency |  | dft+mask | fft+mask | fft2+mask |
| `highpass` | image | frequency | highpass_image | dft+mask | fft+mask | fft2+mask |
| `std_filter` | image | texture | deviation_image | - | filters.rank (std) | stdfilt |
| `threshold` | image->region | segmentation | threshold | threshold | img>t | imbinarize |
| `otsu` | image->region | segmentation | binary_threshold | threshold(OTSU) | filters.threshold_otsu | otsuthresh/graythresh |
| `reg_erode` | region | region | erosion_circle | erode | morphology.binary_erosion | imerode |
| `reg_dilate` | region | region | dilation_circle | dilate | morphology.binary_dilation | imdilate |
| `reg_open` | region | region | opening_circle | morphologyEx(OPEN) | morphology.binary_opening | imopen |
| `reg_close` | region | region | closing_circle | morphologyEx(CLOSE) | morphology.binary_closing | imclose |
| `fill_holes` | region | region | fill_up | floodFill | ndi.binary_fill_holes | imfill('holes') |
| `select_largest` | region | region | select_shape_std | connectedComponents+max | measure.label+regionprops | bwareafilt |
| `remove_small` | region | region | select_shape | - | morphology.remove_small_objects | bwareaopen |
| `invert_region` | region | region | complement | bitwise_not | util.invert | imcomplement |
| `blob_count` | region->feature | features | count_obj | connectedComponents | measure.label | bwconncomp |
| `area_frac` | region->feature | features | area_center | countNonZero | regionprops(area) | bwarea |
| `grad_dir` | image | edges |  | phase | - | imgradient |
| `log` | image | edges | laplace_of_gauss | - | filters.laplace(gaussian) | fspecial('log') |
| `canny` | image->region | segmentation | edges_image | Canny | feature.canny | edge(...,'canny') |
| `dist_transform` | region->image | region | distance_transform | distanceTransform | ndi.distance_transform_edt | bwdist |
| `region_boundary` | region | region | boundary | findContours | segmentation.find_boundaries | bwperim |
| `convex_fill` | region | region | shape_trans | convexHull | morphology.convex_hull_image | bwconvhull |
| `select_contours` | contour | contour | select_contours_xld | (filter contours) | - | - |
| `smooth_contours` | contour | contour | smooth_contours_xld | approxPolyDP | - | - |
| `fit_line_contours` | contour | contour | fit_line_contour_xld | fitLine | measure.LineModelND | polyfit |
| `contours_to_region` | contour->region | contour | gen_region_contour_xld | drawContours/fillPoly | draw.polygon | poly2mask |
| `count_contours` | contour->feature | features | count_obj | len(findContours) | len(find_contours) | - |
| `total_length` | contour->feature | features | length_xld | arcLength | - | - |
| `ncc_locate` | image->match | matching | find_ncc_model | matchTemplate | feature.match_template | normxcorr2 |
| `rotate_img` | image | geometry | rotate_image | warpAffine(rot) | transform.rotate | imrotate |
| `rescale_img` | image | geometry | zoom_image_factor | resize | transform.rescale | imresize |
| `affine_warp` | image | geometry | affine_trans_image | warpAffine | transform.warp(Affine) | imwarp |
| `gabor` | image | texture | gen_gabor | getGaborKernel+filter2D | filters.gabor | imgaborfilt |
| `clahe` | image | gray |  | createCLAHE | exposure.equalize_adapthist | adapthisteq |
| `corner_response` | image | edges | points_harris | cornerHarris | feature.corner_harris | detectHarrisFeatures |
| `adaptive_gauss_thresh` | image->region | segmentation | local_threshold | adaptiveThreshold(GAUSSIAN) | filters.threshold_local | adaptthresh |
| `shape_locate` | image->match | matching | find_shape_model | matchTemplate+rotations | - | - |
| `classify_shape` | region->feature | classification |  | - | regionprops(circularity) | regionprops('Circularity') |
| `decode_barcode` | image->feature | barcode | find_bar_code | barcode.BarcodeDetector | - | readBarcode |
| `vol_gaussian` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_median` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_erode` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_dilate` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_threshold` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_reg_dilate` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_reg_erode` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_dilation_ball` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_erosion_ball` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_opening_ball` | volume | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_mip` | volume->image | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_slice` | volume->image | 3d |  | - | scipy.ndimage (N-D) | - |
| `vol_count` | volume->feature | features |  | - | scipy.ndimage (N-D) | - |
| `sk_scharr` | image | edges | edges_image | - | skimage.scharr | - |
| `sk_farid` | image | edges | edges_image | - | skimage.farid | - |
| `sk_frangi` | image | texture | lines_gauss | - | skimage.frangi | - |
| `sk_meijering` | image | texture | lines_gauss | - | skimage.meijering | - |
| `sk_hessian` | image | texture | lines_gauss | - | skimage.hessian | - |
| `sk_dog` | image | edges | diff_of_gauss | - | skimage.dog | - |
| `sk_gabor` | image | texture | gen_gabor | - | skimage.gabor | - |
| `sk_butterworth` | image | frequency |  | - | skimage.butterworth | - |
| `sk_tv` | image | smoothing |  | - | skimage.tv | - |
| `sk_wavelet` | image | smoothing |  | - | skimage.wavelet | - |
| `sk_adapthist` | image | gray |  | - | skimage.adapthist | - |
| `sk_median_disk` | image | rank | median_image | - | skimage.median_disk | - |
| `sk_otsu` | image->region | segmentation | binary_threshold | - | skimage.otsu | - |
| `sk_li` | image->region | segmentation | binary_threshold | - | skimage.li | - |
| `sk_yen` | image->region | segmentation | binary_threshold | - | skimage.yen | - |
| `sk_sauvola` | image->region | segmentation | var_threshold | - | skimage.sauvola | - |
| `sk_niblack` | image->region | segmentation | var_threshold | - | skimage.niblack | - |
| `sk_canny` | image->region | segmentation | edges_image | - | skimage.canny | - |
| `sk_skeleton` | region | region | skeleton | - | skimage.skeleton | - |
| `sk_medial` | region | region | skeleton | - | skimage.medial | - |
| `sk_convex` | region | region | shape_trans | - | skimage.convex | - |
| `sk_thin` | region | region | thinning | - | skimage.thin | - |
| `sk_remove_holes` | region | region | fill_up | - | skimage.remove_holes | - |
| `sk_euler` | region->feature | features | euler_number | - | skimage.euler | - |
| `sk_find_contours` | image->contour | contour |  | - | skimage.find_contours | - |
| `sk_lbp` | image | texture |  | - | skimage.lbp | - |
| `sk_entropy` | image | texture | entropy_image | - | skimage.entropy | - |
| `sk_enhance_contrast` | image | gray |  | - | skimage.enhance_contrast | - |
| `sk_autolevel` | image | gray | scale_image_max | - | skimage.autolevel | - |
| `sk_shape_index` | image | texture |  | - | skimage.shape_index | - |
| `sk_hessian_det` | image | edges |  | - | skimage.hessian_det | - |
| `sk_corner_harris` | image | edges | points_harris | - | skimage.corner_harris | - |
| `sk_adjust_log` | image | gray | log_image | - | skimage.adjust_log | - |
| `sk_rolling_ball` | image | smoothing |  | - | skimage.rolling_ball | - |
| `sk_nlm` | image | smoothing |  | - | skimage.nlm | - |
| `sk_tv_bregman` | image | smoothing |  | - | skimage.tv_bregman | - |
| `sk_swirl` | image | geometry | polar_trans_image | - | skimage.swirl | - |
| `sk_area_opening` | image | morphology |  | - | skimage.area_opening | - |
| `sk_felzenszwalb` | image->region | segmentation |  | - | skimage.felzenszwalb | - |
| `sk_slic` | image->region | segmentation |  | - | skimage.slic | - |
| `sk_chan_vese` | image->region | segmentation |  | - | skimage.chan_vese | - |
| `sk_local_maxima` | image->region | segmentation | local_max | - | skimage.local_maxima | - |
| `sk_hysteresis` | image->region | segmentation | hysteresis_threshold | - | skimage.hysteresis | - |
| `sk_clear_border` | region | region |  | - | skimage.clear_border | - |
| `sk_find_boundaries` | region | region | boundary | - | skimage.find_boundaries | - |
| `sk_entropy_feat` | image->feature | features | entropy_gray | - | skimage.entropy_feat | - |
| `sk_blur_effect` | image->feature | features |  | - | skimage.blur_effect | - |
| `cv_bilateral` | image | smoothing | bilateral_filter | cv2.bilateral | - | - |
| `cv_median` | image | rank | median_image | cv2.median | - | - |
| `cv_box` | image | smoothing | mean_image | cv2.box | - | - |
| `cv_gaussian` | image | smoothing | gauss_filter | cv2.gaussian | - | - |
| `cv_scharr` | image | edges | edges_image | cv2.scharr | - | - |
| `cv_laplacian` | image | edges | laplace | cv2.laplacian | - | - |
| `cv_clahe` | image | gray |  | cv2.clahe | - | - |
| `cv_open` | image | morphology | gray_opening | cv2.open | - | - |
| `cv_close` | image | morphology | gray_closing | cv2.close | - | - |
| `cv_tophat` | image | morphology | gray_tophat | cv2.tophat | - | - |
| `cv_gradient` | image | morphology | gray_range_rect | cv2.gradient | - | - |
| `cv_otsu` | image->region | segmentation | binary_threshold | cv2.otsu | - | - |
| `cv_adaptive_mean` | image->region | segmentation | dyn_threshold | cv2.adaptive_mean | - | - |
| `cv_adaptive_gauss` | image->region | segmentation | local_threshold | cv2.adaptive_gauss | - | - |
| `cv_canny` | image->region | segmentation | edges_image | cv2.canny | - | - |
| `cv_corner_harris` | image | edges | points_harris | cv2.corner_harris | - | - |
| `cv_min_eigen` | image | edges | points_harris | cv2.min_eigen | - | - |
| `cv_precorner` | image | edges | corner_response | cv2.precorner | - | - |
| `cv_nlmeans` | image | smoothing |  | cv2.nlmeans | - | - |
| `cv_blackhat` | image | morphology | gray_bothat | cv2.blackhat | - | - |
| `cv_erode` | image | morphology | gray_erosion | cv2.erode | - | - |
| `cv_dilate` | image | morphology | gray_dilation | cv2.dilate | - | - |
| `cv_sharpen` | image | smoothing | emphasize | cv2.sharpen | - | - |
| `cv_trunc` | image | gray | scale_image | cv2.trunc | - | - |
| `cv_dist` | region->image | region | distance_transform | cv2.dist | - | - |
| `cv_cc_count` | region->feature | features | connection | cv2.cc_count | - | - |
| `cv_hough_lines` | image->feature | features | hough_lines | cv2.hough_lines | - | - |
| `cv_hough_circles` | image->feature | features | hough_circles | cv2.hough_circles | - | - |
| `cv_good_features` | image->feature | features |  | cv2.good_features | - | - |
| `dl_aniso_diffusion` | image | smoothing | anisotropic_diffusion | - | - | - |
| `dl_guided_filter` | image | smoothing | guided_filter | - | - | - |
| `abs_image` | image | arithmetic | abs_image | pointwise/LUT | - | imadjust |
| `sqrt_image` | image | arithmetic | sqrt_image | pointwise/LUT | - | imadjust |
| `exp_image` | image | arithmetic | exp_image | pointwise/LUT | - | imadjust |
| `log_image` | image | arithmetic | log_image | pointwise/LUT | - | imadjust |
| `sin_image` | image | arithmetic | sin_image | pointwise/LUT | - | imadjust |
| `cos_image` | image | arithmetic | cos_image | pointwise/LUT | - | imadjust |
| `asin_image` | image | arithmetic | asin_image | pointwise/LUT | - | imadjust |
| `acos_image` | image | arithmetic | acos_image | pointwise/LUT | - | imadjust |
| `atan_image` | image | arithmetic | atan_image | pointwise/LUT | - | imadjust |
| `gamma_image` | image | gray | gamma_image | LUT | exposure/util | imadjust |
| `pow_image` | image | gray | pow_image | LUT | exposure/util | imadjust |
| `invert_image` | image | gray | invert_image | LUT | exposure/util | imadjust |
| `scale_image` | image | gray | scale_image | LUT | exposure/util | imadjust |
| `equ_histo_image` | image | gray | equ_histo_image | LUT | exposure/util | imadjust |
| `illuminate` | image | gray | illuminate | LUT | exposure/util | imadjust |
| `scale_image_max` | image | gray | scale_image_max | LUT | exposure/util | imadjust |
| `gauss_filter` | image | smoothing | gauss_filter | GaussianBlur/blur | filters.gaussian | imfilter |
| `gauss_image` | image | smoothing | gauss_image | GaussianBlur/blur | filters.gaussian | imfilter |
| `mean_image` | image | smoothing | mean_image | GaussianBlur/blur | filters.gaussian | imfilter |
| `binomial_filter` | image | smoothing | binomial_filter | GaussianBlur/blur | filters.gaussian | imfilter |
| `smooth_image` | image | smoothing | smooth_image | GaussianBlur/blur | filters.gaussian | imfilter |
| `derivate_gauss` | image | edges | derivate_gauss | GaussianBlur/blur | filters.gaussian | imfilter |
| `laplace_of_gauss` | image | edges | laplace_of_gauss | GaussianBlur/blur | filters.gaussian | imfilter |
| `diff_of_gauss` | image | edges | diff_of_gauss | GaussianBlur/blur | filters.gaussian | imfilter |
| `mean_curvature_flow` | image | smoothing | mean_curvature_flow | GaussianBlur/blur | filters.gaussian | imfilter |
| `median_image` | image | rank | median_image | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `median_rect` | image | rank | median_rect | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `median_separate` | image | rank | median_separate | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `gray_erosion_rect` | image | rank | gray_erosion_rect | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `gray_dilation_rect` | image | rank | gray_dilation_rect | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `gray_range_rect` | image | rank | gray_range_rect | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `rank_image` | image | rank | rank_image | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `rank_rect` | image | rank | rank_rect | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `sigma_image` | image | smoothing | sigma_image | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `trimmed_mean` | image | rank | trimmed_mean | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `gray_erosion` | image | morphology | gray_erosion | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_dilation` | image | morphology | gray_dilation | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_opening` | image | morphology | gray_opening | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_closing` | image | morphology | gray_closing | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_opening_shape` | image | morphology | gray_opening_shape | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_closing_shape` | image | morphology | gray_closing_shape | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_tophat` | image | morphology | gray_tophat | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_bothat` | image | morphology | gray_bothat | morphologyEx | morphology (gray) | imtophat/imopen |
| `sobel_amp` | image | edges | sobel_amp | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `sobel_dir` | image | edges | sobel_dir | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `prewitt_amp` | image | edges | prewitt_amp | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `prewitt_dir` | image | edges | prewitt_dir | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `roberts` | image | edges | roberts | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `kirsch_amp` | image | edges | kirsch_amp | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `kirsch_dir` | image | edges | kirsch_dir | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `frei_amp` | image | edges | frei_amp | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `robinson_amp` | image | edges | robinson_amp | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `laplace` | image | edges | laplace | Laplacian | filters.laplace | fspecial('laplacian') |
| `fft_image` | image | frequency | fft_image | dft+mask | fft+mask | fft2 |
| `power_real` | image | frequency | power_real | dft+mask | fft+mask | fft2 |
| `power_byte` | image | frequency | power_byte | dft+mask | fft+mask | fft2 |
| `phase_rad` | image | frequency | phase_rad | dft+mask | fft+mask | fft2 |
| `highpass_image` | image | frequency | highpass_image | dft+mask | fft+mask | fft2 |
| `bandpass_image` | image | frequency | bandpass_image | dft+mask | fft+mask | fft2 |
| `anisotropic_diffusion` | image | smoothing | anisotropic_diffusion | bilateralFilter/fastNlMeans | restoration | imdiffusefilt |
| `isotropic_diffusion` | image | smoothing | isotropic_diffusion | bilateralFilter/fastNlMeans | restoration | imdiffusefilt |
| `coherence_enhancing_diff` | image | smoothing | coherence_enhancing_diff | bilateralFilter/fastNlMeans | restoration | imdiffusefilt |
| `bilateral_filter` | image | smoothing | bilateral_filter | bilateralFilter/fastNlMeans | restoration | imdiffusefilt |
| `guided_filter` | image | smoothing | guided_filter | bilateralFilter/fastNlMeans | restoration | imdiffusefilt |
| `deviation_image` | image | texture | deviation_image | - | filters.rank/feature | stdfilt/entropyfilt |
| `texture_laws` | image | texture | texture_laws | - | filters.rank/feature | stdfilt/entropyfilt |
| `entropy_image` | image | texture | entropy_image | - | filters.rank/feature | stdfilt/entropyfilt |
| `gen_gabor` | image | texture | gen_gabor | - | filters.rank/feature | stdfilt/entropyfilt |
| `mirror_image` | image | geometry | mirror_image | warpAffine/warpPolar | transform | imwarp |
| `transpose_region` | region | geometry | transpose_region | warpAffine/warpPolar | transform | imwarp |
| `rotate_image` | image | geometry | rotate_image | warpAffine/warpPolar | transform | imwarp |
| `zoom_image_factor` | image | geometry | zoom_image_factor | warpAffine/warpPolar | transform | imwarp |
| `zoom_image_size` | image | geometry | zoom_image_size | warpAffine/warpPolar | transform | imwarp |
| `affine_trans_image` | image | geometry | affine_trans_image | warpAffine/warpPolar | transform | imwarp |
| `polar_trans_image` | image | geometry | polar_trans_image | warpAffine/warpPolar | transform | imwarp |
| `h_threshold` | image->region | segmentation | threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `binary_threshold` | image->region | segmentation | binary_threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `auto_threshold` | image->region | segmentation | auto_threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `dyn_threshold` | image->region | segmentation | dyn_threshold | adaptiveThreshold | filters.threshold_local | adaptthresh |
| `var_threshold` | image->region | segmentation | var_threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `local_threshold` | image->region | segmentation | local_threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `hysteresis_threshold` | image->region | segmentation | hysteresis_threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `edges_image` | image->region | segmentation | edges_image | Canny/watershed | segmentation | watershed |
| `watersheds` | image->region | segmentation | watersheds | Canny/watershed | segmentation | watershed |
| `watersheds_threshold` | image->region | segmentation | watersheds_threshold | Canny/watershed | segmentation | watershed |
| `regiongrowing` | image->region | segmentation | regiongrowing | Canny/watershed | segmentation | watershed |
| `local_max` | image->region | segmentation | local_max | - | feature.peak_local_max | imregionalmax |
| `erosion_circle` | region | region | erosion_circle | morphologyEx | morphology.binary_* | imopen/imclose |
| `dilation_circle` | region | region | dilation_circle | morphologyEx | morphology.binary_* | imopen/imclose |
| `opening_circle` | region | region | opening_circle | morphologyEx | morphology.binary_* | imopen/imclose |
| `closing_circle` | region | region | closing_circle | morphologyEx | morphology.binary_* | imopen/imclose |
| `erosion_rectangle1` | region | region | erosion_rectangle1 | morphologyEx | morphology.binary_* | imopen/imclose |
| `dilation_rectangle1` | region | region | dilation_rectangle1 | morphologyEx | morphology.binary_* | imopen/imclose |
| `opening_rectangle1` | region | region | opening_rectangle1 | morphologyEx | morphology.binary_* | imopen/imclose |
| `closing_rectangle1` | region | region | closing_rectangle1 | morphologyEx | morphology.binary_* | imopen/imclose |
| `fill_up` | region | region | fill_up | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `boundary` | region | region | boundary | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `skeleton` | region | region | skeleton | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `thinning` | region | region | thinning | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `shape_trans` | region | region | shape_trans | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `select_shape_std` | region | region | select_shape_std | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `select_shape` | region | region | select_shape | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `distance_transform` | region->image | region | distance_transform | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `area_center` | region->match | features | area_center | - | measure.regionprops | regionprops |
| `count_obj` | region->feature | features | count_obj | - | measure.regionprops | regionprops |
| `circularity` | region->feature | features | circularity | - | measure.regionprops | regionprops |
| `compactness` | region->feature | features | compactness | - | measure.regionprops | regionprops |
| `convexity` | region->feature | features | convexity | - | measure.regionprops | regionprops |
| `rectangularity` | region->feature | features | rectangularity | - | measure.regionprops | regionprops |
| `eccentricity` | region->feature | features | eccentricity | - | measure.regionprops | regionprops |
| `orientation_region` | region->feature | features | orientation_region | - | measure.regionprops | regionprops |
| `roundness` | region->feature | features | roundness | - | measure.regionprops | regionprops |
| `diameter_region` | region->feature | features | diameter_region | - | measure.regionprops | regionprops |
| `euler_number` | region->feature | features | euler_number | - | measure.regionprops | regionprops |
| `min_max_gray` | image->feature | features | min_max_gray | minMaxLoc/meanStdDev | measure | - |
| `intensity` | image->feature | features | intensity | minMaxLoc/meanStdDev | measure | - |
| `gray_histo_abs` | image->feature | features | gray_histo_abs | minMaxLoc/meanStdDev | measure | - |
| `entropy_gray` | image->feature | features | entropy_gray | minMaxLoc/meanStdDev | measure | - |
| `edges_sub_pix` | image->contour | contour | edges_sub_pix | - | measure.find_contours | - |
| `lines_gauss` | image->contour | contour | lines_gauss | findContours | measure.find_contours | - |
| `select_contours_xld` | contour | contour | select_contours_xld | findContours | measure.find_contours | - |
| `smooth_contours_xld` | contour | contour | smooth_contours_xld | findContours | measure.find_contours | - |
| `gen_region_contour_xld` | contour->region | contour | gen_region_contour_xld | findContours | measure.find_contours | - |
| `length_xld` | contour->feature | features | length_xld | findContours | measure.find_contours | - |
| `contlength` | region->feature | features | contlength | - | measure.regionprops | regionprops |
| `area_holes` | region->feature | features | area_holes | - | measure.regionprops | regionprops |
| `height_width_ratio` | region->feature | features | height_width_ratio | - | measure.regionprops | regionprops |
| `moments_region_2nd` | region->feature | features | moments_region_2nd | - | measure.regionprops | regionprops |
| `moments_region_2nd_invar` | region->feature | features | moments_region_2nd_invar | - | measure.regionprops | regionprops |
| `cooc_feature_matrix` | image->feature | texture | cooc_feature_matrix | - | feature.graycomatrix/graycoprops | graycomatrix/graycoprops |
| `equ_histo_image_rect` | image | gray | equ_histo_image_rect | LUT | exposure/util | imadjust |
| `simulate_motion` | image | smoothing | simulate_motion | GaussianBlur/blur | filters.gaussian | imfilter |
| `projective_trans_image` | image | geometry | projective_trans_image | warpAffine/warpPolar | transform | imwarp |
| `projective_trans_image_size` | image | geometry | projective_trans_image_size | warpAffine/warpPolar | transform | imwarp |
| `projective_trans_region` | region | geometry | projective_trans_region | warpAffine/warpPolar | transform | imwarp |
| `polar_trans_image_inv` | image | geometry | polar_trans_image_inv | warpAffine/warpPolar | transform | imwarp |
| `fft_image_inv` | image | frequency | fft_image_inv | dft+mask | fft+mask | fft2 |
| `add_noise_white` | image | noise | add_noise_white | - | util.random_noise | imnoise |
| `area_center_xld` | contour->feature | features | area_center_xld | findContours | measure.find_contours | - |
| `circularity_xld` | contour->feature | features | circularity_xld | findContours | measure.find_contours | - |
| `compactness_xld` | contour->feature | features | compactness_xld | findContours | measure.find_contours | - |
| `convexity_xld` | contour->feature | features | convexity_xld | findContours | measure.find_contours | - |
| `close_contours_xld` | contour | contour | close_contours_xld | findContours | measure.find_contours | - |
| `affine_trans_contour_xld` | contour | contour | affine_trans_contour_xld | findContours | measure.find_contours | - |
| `projective_trans_contour_xld` | contour | contour | projective_trans_contour_xld | findContours | measure.find_contours | - |
| `polar_trans_contour_xld` | contour | contour | polar_trans_contour_xld | findContours | measure.find_contours | - |
| `moments_region_3rd` | region->feature | features | moments_region_3rd | - | measure.regionprops | regionprops |
| `moments_region_central` | region->feature | features | moments_region_central | - | measure.regionprops | regionprops |
| `moments_region_central_invar` | region->feature | features | moments_region_central_invar | - | measure.regionprops | regionprops |
| `moments_region_2nd_rel_invar` | region->feature | features | moments_region_2nd_rel_invar | - | measure.regionprops | regionprops |
| `moments_region_3rd_invar` | region->feature | features | moments_region_3rd_invar | - | measure.regionprops | regionprops |
| `dual_threshold` | image->region | segmentation | dual_threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `segment_image_mser` | image->region | segmentation | segment_image_mser | Canny/watershed | segmentation | watershed |
| `regiongrowing_mean` | image->region | segmentation | regiongrowing_mean | Canny/watershed | segmentation | watershed |
| `estimate_noise` | image->feature | features | estimate_noise | minMaxLoc/meanStdDev | measure | - |
| `points_foerstner` | image | edges | points_foerstner | cornerHarris/goodFeaturesToTrack | feature.corner_* | detectHarrisFeatures |
| `points_harris_binomial` | image | edges | points_harris_binomial | cornerHarris/goodFeaturesToTrack | feature.corner_* | detectHarrisFeatures |
| `eccentricity_xld` | contour->feature | features | eccentricity_xld | findContours | measure.find_contours | - |
| `orientation_xld` | contour->feature | features | orientation_xld | findContours | measure.find_contours | - |
| `elliptic_axis_xld` | contour->feature | features | elliptic_axis_xld | findContours | measure.find_contours | - |
| `diameter_xld` | contour->feature | features | diameter_xld | findContours | measure.find_contours | - |
| `rectangularity_xld` | contour->feature | features | rectangularity_xld | findContours | measure.find_contours | - |
| `moments_xld` | contour->feature | features | moments_xld | findContours | measure.find_contours | - |
| `shape_trans_xld` | contour | contour | shape_trans_xld | findContours | measure.find_contours | - |
| `zero_crossing` | image->region | segmentation | zero_crossing | Canny/watershed | segmentation | watershed |
| `local_min` | image->region | segmentation | local_min | Canny/watershed | segmentation | watershed |
| `pruning` | region | region | pruning | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `hough_line_trans` | image | features | hough_line_trans | HoughLines/HoughCircles | transform.hough_line/hough_circle | hough |
| `hough_circle_trans` | image | features | hough_circle_trans | HoughLines/HoughCircles | transform.hough_line/hough_circle | hough |
| `threshold_sub_pix` | image->contour | contour | threshold_sub_pix | findContours | measure.find_contours | - |
| `zero_crossing_sub_pix` | image->contour | contour | zero_crossing_sub_pix | findContours | measure.find_contours | - |
| `closest_point_transform` | region->image | region | closest_point_transform | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `junctions_skeleton` | region | region | junctions_skeleton | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `get_region_thickness` | region->feature | features | get_region_thickness | - | measure.regionprops | regionprops |
| `tan_image` | image | arithmetic | tan_image | pointwise/LUT | - | imadjust |
| `bit_not` | image | gray | bit_not | LUT | exposure/util | imadjust |
| `monotony` | image | gray | monotony | LUT | exposure/util | imadjust |
| `eliminate_min_max` | image | rank | eliminate_min_max | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `median_weighted` | image | rank | median_weighted | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `mean_sp` | image | rank | mean_sp | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `eliminate_sp` | image | rank | eliminate_sp | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `simulate_defocus` | image | smoothing | simulate_defocus | GaussianBlur/blur | filters.gaussian | imfilter |
| `dots_image` | image | edges | dots_image | GaussianBlur/blur | filters.gaussian | imfilter |
| `frei_dir` | image | edges | frei_dir | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `robinson_dir` | image | edges | robinson_dir | Sobel/Scharr/Laplacian | filters.sobel/prewitt | edge |
| `fft_generic` | image | frequency | fft_generic | dft+mask | fft+mask | fft2 |
| `power_ln` | image | frequency | power_ln | dft+mask | fft+mask | fft2 |
| `rft_generic` | image | frequency | rft_generic | dft+mask | fft+mask | fft2 |
| `phase_deg` | image | frequency | phase_deg | dft+mask | fft+mask | fft2 |
| `affine_trans_image_size` | image | geometry | affine_trans_image_size | warpAffine/warpPolar | transform | imwarp |
| `polar_trans_image_ext` | image | geometry | polar_trans_image_ext | warpAffine/warpPolar | transform | imwarp |
| `lines_facet` | image->contour | contour | lines_facet | findContours | measure.find_contours | - |
| `add_noise_distribution` | image | noise | add_noise_distribution | - | util.random_noise | imnoise |
| `bin_threshold` | image->region | segmentation | bin_threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `erosion_golay` | region | region | erosion_golay | morphologyEx | morphology.binary_* | imopen/imclose |
| `dilation_golay` | region | region | dilation_golay | morphologyEx | morphology.binary_* | imopen/imclose |
| `opening_golay` | region | region | opening_golay | morphologyEx | morphology.binary_* | imopen/imclose |
| `closing_golay` | region | region | closing_golay | morphologyEx | morphology.binary_* | imopen/imclose |
| `erosion_seq` | region | region | erosion_seq | morphologyEx | morphology.binary_* | imopen/imclose |
| `dilation_seq` | region | region | dilation_seq | morphologyEx | morphology.binary_* | imopen/imclose |
| `morph_skeleton` | region | region | morph_skeleton | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `thinning_golay` | region | region | thinning_golay | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `thinning_seq` | region | region | thinning_seq | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `gray_erosion_shape` | image | morphology | gray_erosion_shape | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_dilation_shape` | image | morphology | gray_dilation_shape | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_opening_rect` | image | morphology | gray_opening_rect | morphologyEx | morphology (gray) | imtophat/imopen |
| `gray_closing_rect` | image | morphology | gray_closing_rect | morphologyEx | morphology (gray) | imtophat/imopen |
| `dual_rank` | image | rank | dual_rank | medianBlur/erode/dilate | filters.rank | ordfilt2 |
| `fast_threshold` | image->region | segmentation | fast_threshold | threshold/adaptiveThreshold | filters.threshold_* | imbinarize |
| `nonmax_suppression_amp` | image->region | segmentation | nonmax_suppression_amp | Canny/watershed | segmentation | watershed |
| `pouring` | image->region | segmentation | pouring | Canny/watershed | segmentation | watershed |
| `affine_trans_region` | region | geometry | affine_trans_region | warpAffine/warpPolar | transform | imwarp |
| `mirror_region` | region | geometry | mirror_region | warpAffine/warpPolar | transform | imwarp |
| `zoom_region` | region | geometry | zoom_region | warpAffine/warpPolar | transform | imwarp |
| `fill_up_shape` | region | region | fill_up_shape | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `remove_noise_region` | region | region | remove_noise_region | morphologyEx | morphology.binary_* | imopen/imclose |
| `smallest_rectangle1` | region | region | smallest_rectangle1 | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `get_region_contour` | region | region | get_region_contour | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `get_region_convex` | region | region | get_region_convex | distanceTransform/findContours | morphology/segmentation | bwmorph |
| `gen_region_polygon_xld` | contour->region | contour | gen_region_polygon_xld | findContours | measure.find_contours | - |
| `connect_and_holes` | region->feature | features | connect_and_holes | - | measure.regionprops | regionprops |
| `elliptic_axis` | region->feature | features | elliptic_axis | - | measure.regionprops | regionprops |
| `polar_trans_region_inv` | region | geometry | polar_trans_region_inv | warpAffine/warpPolar | transform | imwarp |
| `affine_trans_polygon_xld` | contour | contour | affine_trans_polygon_xld | findContours | measure.find_contours | - |
| `gen_contour_region_xld` | region->contour | contour | gen_contour_region_xld | findContours | measure.find_contours | - |
| `select_shape_xld` | contour | contour | select_shape_xld | findContours | measure.find_contours | - |
| `contour_point_num_xld` | contour->feature | contour | contour_point_num_xld | findContours | measure.find_contours | - |
| `cfa_to_rgb` | image->color | color | cfa_to_rgb | cvtColor/mixChannels | color | rgb2*/imsplit |
| `trans_from_rgb` | color | color | trans_from_rgb | cvtColor/mixChannels | color | rgb2*/imsplit |
| `trans_to_rgb` | color | color | trans_to_rgb | cvtColor/mixChannels | color | rgb2*/imsplit |
| `linear_trans_color` | color | color | linear_trans_color | cvtColor/mixChannels | color | rgb2*/imsplit |
| `principal_comp` | color | color | principal_comp | cvtColor/mixChannels | color | rgb2*/imsplit |
| `rgb1_to_gray` | color->image | color | rgb1_to_gray | cvtColor/mixChannels | color | rgb2*/imsplit |
| `rgb3_to_gray` | color->image | color | rgb3_to_gray | cvtColor/mixChannels | color | rgb2*/imsplit |
| `access_channel` | color->image | color | access_channel | cvtColor/mixChannels | color | rgb2*/imsplit |
| `edges_color` | color->image | edges | edges_color | cvtColor/mixChannels | color | rgb2*/imsplit |
| `edges_color_sub_pix` | color->contour | contour | edges_color_sub_pix | cvtColor/mixChannels | color | rgb2*/imsplit |
| `lines_color` | color->contour | contour | lines_color | cvtColor/mixChannels | color | rgb2*/imsplit |
| `count_channels` | color->feature | features | count_channels | cvtColor/mixChannels | color | rgb2*/imsplit |
| `xsk_inpaint` | image | restoration |  | - | skimage.inpaint | - |
| `xsk_richardson_lucy` | image | restoration |  | - | skimage.richardson_lucy | - |
| `xsk_unwrap_phase` | image | restoration |  | - | skimage.unwrap_phase | - |
| `xsk_struct_coherence` | image | texture |  | - | skimage.struct_coherence | - |
| `xsk_hessian_eig` | image | edges |  | - | skimage.hessian_eig | - |
| `xsk_random_walker` | image->region | segmentation |  | - | skimage.random_walker | - |
| `xsk_flood` | image->region | segmentation |  | - | skimage.flood | - |
| `xsk_blob_log` | image->feature | features |  | - | skimage.blob_log | - |
| `xsk_blob_dog` | image->feature | features |  | - | skimage.blob_dog | - |
| `xsk_blob_doh` | image->feature | features |  | - | skimage.blob_doh | - |
| `xsk_orb_count` | image->feature | features |  | - | skimage.orb_count | - |
| `xsk_meijering` | image | texture |  | - | skimage.meijering | - |
| `xsk_sato` | image | texture |  | - | skimage.sato | - |
| `xcv_stylization` | image | artistic |  | cv2.stylization | - | - |
| `xcv_pencil_sketch` | image | artistic |  | cv2.pencil_sketch | - | - |
| `xcv_edge_preserving` | image | smoothing |  | cv2.edge_preserving | - | - |
| `xcv_detail_enhance` | image | gray |  | cv2.detail_enhance | - | - |
| `xcv_inpaint` | image | restoration |  | cv2.inpaint | - | - |
| `xcv_grabcut` | image->region | segmentation |  | cv2.grabcut | - | - |
| `xcv_watershed_markers` | image->region | segmentation | watersheds | cv2.watershed_markers | - | - |
| `xcv_orb_count` | image->feature | features |  | cv2.orb_count | - | - |
| `xpil_emboss` | image | artistic |  | - | - | - |
| `xpil_contour` | image | edges |  | - | - | - |
| `xpil_find_edges` | image | edges |  | - | - | - |
| `xpil_edge_enhance` | image | gray |  | - | - | - |
| `xpil_smooth_more` | image | smoothing |  | - | - | - |
| `xpil_detail` | image | gray |  | - | - | - |
| `xpil_mode_filter` | image | rank |  | - | - | - |
| `xpil_unsharp_mask` | image | smoothing |  | - | - | - |
| `xpil_posterize` | image | gray |  | - | - | - |
| `xpil_solarize` | image | gray |  | - | - | - |
| `xpil_autocontrast` | image | gray |  | - | - | - |
| `xpil_offset` | image | geometry |  | - | - | - |
| `xpil_contrast` | image | gray |  | - | - | - |
| `xsp_wiener` | image | smoothing |  | - | - | - |
| `xsp_savgol` | image | smoothing |  | - | - | - |
| `xsp_hilbert_env` | image | texture |  | - | - | - |
| `xsp_dct` | image | frequency |  | - | - | - |
| `xsp_dct_lowpass` | image | frequency |  | - | - | - |
| `xsp_dct_denoise` | image | smoothing |  | - | - | - |
| `xsp_cspline_smooth` | image | smoothing |  | - | - | - |
| `xsp_detrend_flatten` | image | gray |  | - | - | - |
| `xsp_morph_laplace` | image | edges |  | - | - | - |
| `xsp_chamfer_dist` | region->image | region |  | - | - | - |
| `xsp_gauss_grad_mag` | image | edges |  | - | - | - |
| `xsk2_multiotsu` | image | segmentation |  | - | skimage.multiotsu | - |
| `xsk2_rank_geomean` | image | rank |  | - | skimage.rank_geomean | - |
| `xsk2_reconstruction` | image | morphology |  | - | skimage.reconstruction | - |
| `xsk2_h_maxima` | image->region | segmentation |  | - | skimage.h_maxima | - |
| `xsk2_diameter_opening` | image | morphology |  | - | skimage.diameter_opening | - |
| `xsk2_isotropic_close` | region | region |  | - | skimage.isotropic_close | - |
| `xsk2_hog` | image | texture |  | - | skimage.hog | - |
| `xsk2_corner_kr` | image | edges |  | - | skimage.corner_kr | - |
| `xsk2_radon` | image | frequency |  | - | skimage.radon | - |
| `xsk2_inv_gauss_grad` | image | edges |  | - | skimage.inv_gauss_grad | - |
| `xsk2_wiener` | image | restoration |  | - | skimage.wiener | - |
| `xcv2_warp_logpolar` | image | geometry |  | cv2.warp_logpolar | - | - |
| `xcv2_meanshift` | image | segmentation |  | cv2.meanshift | - | - |
| `xcv2_hitmiss` | region | region |  | cv2.hitmiss | - | - |
| `xcv2_lap_var` | image->feature | features |  | cv2.lap_var | - | - |
| `xcv2_fast_count` | image->feature | features |  | cv2.fast_count | - | - |
| `xmh_zernike` | image->feature | texture/shape-feature |  | - | - | - |
| `xmh_pftas` | image->feature | texture-feature |  | - | - | - |
| `xmh_bernsen` | image->region | segmentation |  | - | - | - |
| `xmh_majority` | region | region-morphology |  | - | - | - |
| `xmh_haar` | image | transform |  | - | - | - |
| `xmh_daubechies` | image | transform |  | - | - | - |
| `xmh_soft` | image | intensity-transform |  | - | - | - |
| `xmh_bwperim` | region | region-transform |  | - | - | - |
| `xmh_regmin` | image->region | morphology/markers |  | - | - | - |
| `xmh_selfmatch` | image | self-similarity |  | - | - | - |
| `xwt_subband_tile` | image | frequency |  | - | - | - |
| `xwt_visushrink` | image | smoothing |  | - | - | - |
| `xwt_firm_denoise` | image | smoothing |  | - | - | - |
| `xwt_detail_energy` | image->feature | features |  | - | - | - |
| `xwt_hf_reconstruct` | image | edges |  | - | - | - |
| `xwt_lf_reconstruct` | image | smoothing |  | - | - | - |
| `xwt_directional_detail` | image | edges |  | - | - | - |
| `xwt_packet_entropy` | image->feature | features |  | - | - | - |
| `xwt_mra_component` | image | frequency |  | - | - | - |
| `xsitk_curvature_flow` | image | extra |  | - | - | - |
| `xsitk_minmax_curv_flow` | image | extra |  | - | - | - |
| `xsitk_curv_aniso_diff` | image | extra |  | - | - | - |
| `xsitk_laplacian_sharpen` | image | extra |  | - | - | - |
| `xsitk_grayscale_fillhole` | image | extra |  | - | - | - |
| `xsitk_grayscale_grindpeak` | image | extra |  | - | - | - |
| `xsitk_opening_by_recon` | image | extra |  | - | - | - |
| `xsitk_closing_by_recon` | image | extra |  | - | - | - |
| `xsitk_signed_maurer_dist` | region->image | extra |  | - | - | - |
| `xsitk_connected_threshold` | image->region | extra |  | - | - | - |
| `xsitk_confidence_connected` | image->region | extra |  | - | - | - |
| `xsitk_maxentropy_thresh` | image->region | extra |  | - | - | - |
| `xsitk_moments_thresh` | image->region | extra |  | - | - | - |
| `xsitk_huang_thresh` | image->region | extra |  | - | - | - |
| `xsk3_rank_otsu` | image->region | segmentation |  | - | skimage.rank_otsu | - |
| `xsk3_rank_majority` | region | region |  | - | skimage.rank_majority | - |
| `xsk3_rank_subtract_mean` | image | gray |  | - | skimage.rank_subtract_mean | - |
| `xsk3_rank_equalize` | image | gray |  | - | skimage.rank_equalize | - |
| `xsk3_rank_mean_bilateral` | image | smoothing |  | - | skimage.rank_mean_bilateral | - |
| `xsk3_h_minima` | image->region | segmentation |  | - | skimage.h_minima | - |
| `xsk3_area_closing` | image | morphology |  | - | skimage.area_closing | - |
| `xsk3_diameter_closing` | image | morphology |  | - | skimage.diameter_closing | - |
| `xsk3_corner_moravec` | image | edges |  | - | skimage.corner_moravec | - |
| `xsk3_corner_fast` | image | edges |  | - | skimage.corner_fast | - |
| `xsk3_integral_image` | image | gray |  | - | skimage.integral_image | - |
| `xsk3_threshold_local_median` | image->region | segmentation |  | - | skimage.threshold_local_median | - |
| `xsk3_is_low_contrast` | image->feature | features |  | - | skimage.is_low_contrast | - |
| `xsk3_estimate_sigma` | image->feature | features |  | - | skimage.estimate_sigma | - |
| `xsk3_peak_local_max` | image->region | segmentation |  | - | skimage.peak_local_max | - |
| `xcv3_denoise_tvl1` | image | smoothing |  | cv2.denoise_tvl1 | - | - |
| `xcv3_inpaint_ns` | image | restoration |  | cv2.inpaint_ns | - | - |
| `xcv3_pyr_laplacian` | image | smoothing |  | cv2.pyr_laplacian | - | - |
| `xcv3_gray_hu1` | image->feature | features |  | cv2.gray_hu1 | - | - |
| `xcv3_sift_count` | image->feature | features |  | cv2.sift_count | - | - |
| `xcv3_brisk_count` | image->feature | features |  | cv2.brisk_count | - | - |
| `xcv3_agast_count` | image->feature | features |  | cv2.agast_count | - | - |
| `xcv3_lsd_count` | image->feature | features |  | cv2.lsd_count | - | - |
| `xkor_gaussian` | image | smoothing |  | - | - | - |
| `xkor_bilateral` | image | smoothing |  | - | - | - |
| `xkor_median` | image | rank |  | - | - | - |
| `xkor_unsharp` | image | smoothing |  | - | - | - |
| `xkor_motion_blur` | image | smoothing |  | - | - | - |
| `xkor_canny` | image->region | segmentation |  | - | - | - |
| `xkor_clahe` | image | gray |  | - | - | - |
| `xkor_laplacian` | image | edges |  | - | - | - |
| `xkor_harris` | image | edges |  | - | - | - |
| `xkor_gftt` | image | edges |  | - | - | - |
| `xkor_hessian` | image | edges |  | - | - | - |
| `xkor_dog` | image | edges |  | - | - | - |
| `f2_shock` | image | edges | shock_filter | - | - | - |
| `f2_gray_skeleton` | image | morphology | gray_skeleton | - | - | - |
| `f2_lut_trans` | image | gray | lut_trans | - | - | - |
| `f2_topographic` | image | edges | topographic_sketch | - | - | - |
| `f2_expand_domain` | image | gray | expand_domain_gray | - | - | - |
| `f2_symmetry` | image | texture | symmetry | - | - | - |
| `f2_gauss_pyramid` | image | smoothing | gen_gauss_pyramid | - | - | - |
| `f2_gray_inside` | image | morphology | gray_inside | - | - | - |
| `f2_bit_slice` | image | gray | bit_slice | - | - | - |
| `r2_inner_circle` | region | region | inner_circle | - | - | - |
| `r2_inner_rectangle1` | region | region | inner_rectangle1 | - | - | - |
| `r2_smallest_rectangle1` | region | region |  | - | - | - |
| `r2_smallest_circle` | region | region | smallest_circle | - | - | - |
| `r2_smallest_rectangle2` | region | region | smallest_rectangle2 | - | - | - |
| `r2_sort_region` | region | region | sort_region | - | - | - |
| `r2_union1` | region | region | union1 | - | - | - |
| `r2_partition_rectangle` | region | region | partition_rectangle | - | - | - |
| `r2_runlength_features` | region->feature | region | runlength_features | - | - | - |
| `r2_split_skeleton_lines` | region | region | split_skeleton_lines | - | - | - |
| `em_skeleton` | region | region |  | - | - | - |
| `r2_endpoints_skeleton` | region | region |  | - | - | - |
| `sp_local_max_sub_pix` | image->contour | subpix |  | - | - | - |
| `sp_local_min_sub_pix` | image->contour | subpix | local_min_sub_pix | - | - | - |
| `sp_saddle_points_sub_pix` | image->contour | subpix | saddle_points_sub_pix | - | - | - |
| `sp_critical_points_sub_pix` | image->contour | subpix | critical_points_sub_pix | - | - | - |
| `sp_plateaus` | image->contour | subpix | plateaus | - | - | - |
| `sp_lowlands_center` | image->contour | subpix | lowlands_center | - | - | - |
| `xg_moments` | contour->feature | xldgeom | moments_points_xld | - | - | - |
| `xg_area_center` | contour->feature | xldgeom | area_center_points_xld | - | - | - |
| `xg_eccentricity` | contour->feature | xldgeom | eccentricity_points_xld | - | - | - |
| `xg_orientation` | contour->feature | xldgeom | orientation_points_xld | - | - | - |
| `xg_elliptic_axis` | contour->feature | xldgeom | elliptic_axis_points_xld | - | - | - |
| `xg_height_width_ratio` | contour->feature | xldgeom | height_width_ratio_xld | - | - | - |
| `xg_regress_contours` | contour->feature | xldgeom |  | - | - | - |
| `xg_clip_contours` | contour | xldgeom |  | - | - | - |
| `xg_gen_polygons` | contour | xldgeom | gen_polygons_xld | - | - | - |
| `xg_crop_contours` | contour | xldgeom |  | - | - | - |
| `r3_background_seg` | region | region | background_seg | - | - | - |
| `r3_clip_region` | region | region | clip_region | - | - | - |
| `r3_eliminate_runs` | region | region | eliminate_runs | - | - | - |
| `r3_rank_region` | region | region | rank_region | - | - | - |
| `r3_region_features` | region->feature | region | region_features | - | - | - |
| `r3_runlength_distribution` | region->feature | region | runlength_distribution | - | - | - |
| `r3_select_region_point` | region | region | select_region_point | - | - | - |
| `r3_partition_dynamic` | region | region | partition_dynamic | - | - | - |
| `r3_polar_trans_region` | region | region | polar_trans_region | - | - | - |
| `r3_label_to_region` | region | region | label_to_region | - | - | - |
| `it_add_image_border` | image | geometry | add_image_border | - | - | - |
| `it_crop_part` | image | geometry | crop_part | - | - | - |
| `it_crop_rectangle1` | image | geometry | crop_rectangle1 | - | - | - |
| `it_bit_lshift` | image | gray | bit_lshift | - | - | - |
| `it_bit_rshift` | image | gray | bit_rshift | - | - | - |
| `it_bit_mask` | image | gray | bit_mask | - | - | - |
| `it_convert_image_type` | image | gray | convert_image_type | - | - | - |
| `it_change_format` | image | geometry | change_format | - | - | - |
| `it_region_to_bin` | image | segmentation | region_to_bin | - | - | - |
| `it_full_domain` | image | domain |  | - | - | - |
| `it_crop_domain` | image | domain | crop_domain | - | - | - |
| `m1_measure_projection` | image->feature | measure1d | measure_projection | - | - | - |
| `m1_measure_pos` | image->contour | measure1d | measure_pos | - | - | - |
| `m1_measure_thresh` | image->feature | measure1d | measure_thresh | - | - | - |
| `m1_measure_pairs` | image->feature | measure1d | measure_pairs | - | - | - |
| `m1_fuzzy_measure_pos` | image->contour | measure1d | fuzzy_measure_pos | - | - | - |
| `ph_perona_malik` | image | physics |  | - | - | - |
| `ph_coherence_enhancing_diffusion` | image | physics |  | - | - | - |
| `ph_reaction_diffusion` | image | physics |  | - | - | - |
| `ph_heat_flow` | image | physics |  | - | - | - |
| `ph_mean_curvature_motion` | image | physics |  | - | - | - |
| `ph_total_variation_flow` | image | physics |  | - | - | - |
| `dc_structure_texture` | image | decomposition |  | - | - | - |
| `dc_texture_residual` | image | decomposition |  | - | - | - |
| `dc_rpca_lowrank` | image | decomposition |  | - | - | - |
| `dc_rpca_sparse` | image | decomposition |  | - | - | - |
| `dc_retinex` | image | decomposition |  | - | - | - |
| `dc_local_contrast_norm` | image | decomposition |  | - | - | - |
| `dc_homomorphic` | image | decomposition |  | - | - | - |
| `iv_richardson_lucy` | image | restoration |  | - | - | - |
| `iv_wiener_deconv_spatial` | image | restoration |  | - | - | - |
| `iv_unsharp_deblur` | image | restoration |  | - | - | - |
| `iv_motion_deblur` | image | restoration |  | - | - | - |
| `iv_backproject_superres` | image | restoration |  | - | - | - |
| `iv_gradient_inpaint` | image | restoration |  | - | - | - |
| `tf_log_polar` | image | geometry |  | - | - | - |
| `tf_radon_sinogram` | image | transform |  | - | - | - |
| `tf_steerable_filter` | image | edges |  | - | - | - |
| `tf_phase_congruency` | image | edges |  | - | - | - |
| `tf_gradient_domain_reintegrate` | image | filtering |  | - | - | - |
| `tf_census_transform` | image | texture |  | - | - | - |
| `tf_rank_transform` | image | texture |  | - | - | - |
| `sg_slic_superpixels` | image->region | segment |  | - | - | - |
| `sg_felzenszwalb` | image->region | segment |  | - | - | - |
| `sg_gmm_segment` | image->region | segment |  | - | - | - |
| `sg_kmeans_intensity` | image->region | segment |  | - | - | - |
| `sg_region_growing_seeded` | image->region | segment |  | - | - | - |
| `sg_normalized_cut_2` | image->region | segment |  | - | - | - |
| `sg_watershed_gradient` | image->region | segment |  | - | - | - |
| `tm_radon_forward` | image | tomography |  | - | - | - |
| `tm_fbp_reconstruct` | image | tomography |  | - | - | - |
| `tm_sart_reconstruct` | image | tomography |  | - | - | - |
| `tm_backproject_unfiltered` | image | tomography |  | - | - | - |
| `tm_sinogram_denoise` | image | tomography |  | - | - | - |
| `aug_shot_noise` | image | augmentation |  | - | - | - |
| `aug_read_noise` | image | augmentation |  | - | - | - |
| `aug_fixed_pattern` | image | augmentation |  | - | - | - |
| `aug_motion_blur` | image | augmentation |  | - | - | - |
| `aug_vignette` | image | augmentation |  | - | - | - |
| `aug_chromatic` | image | augmentation |  | - | - | - |
| `aug_rolling_shutter` | image | augmentation |  | - | - | - |
| `aug_jpeg_blocks` | image | augmentation |  | - | - | - |
| `aug_cutout` | image | augmentation |  | - | - | - |
| `aug_barrel` | image | augmentation |  | - | - | - |
| `alife_gray_scott` | image | artificial-life |  | - | - | - |
| `alife_turing` | image | artificial-life |  | - | - | - |
| `alife_life_step` | image | artificial-life |  | - | - | - |
| `alife_cyclic_ca` | image | artificial-life |  | - | - | - |
| `alife_perona_malik` | image | artificial-life |  | - | - | - |
| `alife_curvature_flow` | image | artificial-life |  | - | - | - |
| `alife_dla` | image | artificial-life |  | - | - | - |
| `alife_reaction_bz` | image | artificial-life |  | - | - | - |
| `tac_contact_mask` | image->region | tactile |  | - | - | - |
| `tac_height_from_shading` | image | tactile |  | - | - | - |
| `tac_surface_normal` | image | tactile |  | - | - | - |
| `tac_pressure_proxy` | image | tactile |  | - | - | - |
| `tac_shear_field` | image | tactile |  | - | - | - |
| `alife_wolfram1d` | image | artificial-life |  | - | - | - |
| `alife_langton_ant` | image | artificial-life |  | - | - | - |
| `alife_lenia` | image | artificial-life |  | - | - | - |
| `alife_sandpile` | image | artificial-life |  | - | - | - |
| `deform_tps` | image | deformation |  | - | - | - |
| `deform_ffd` | image | deformation |  | - | - | - |
| `deform_mls` | image | deformation |  | - | - | - |
| `hx_gen_circle` | image->region | halcon_ext | gen_circle | - | - | - |
| `hx_gen_ellipse` | image->region | halcon_ext | gen_ellipse | - | - | - |
| `hx_gen_rectangle2` | image->region | halcon_ext | gen_rectangle2 | - | - | - |
| `hx_gen_checker_region` | image->region | halcon_ext | gen_checker_region | - | - | - |
| `hx_gen_grid_region` | image->region | halcon_ext | gen_grid_region | - | - | - |
| `hx_gabor` | image | halcon_ext | convol_gabor | - | - | - |
| `hx_fit_surface1` | image | halcon_ext | fit_surface_first_order | - | - | - |
| `hx_fit_surface2` | image | halcon_ext | fit_surface_second_order | - | - | - |
| `hx_cooc_feature` | image->feature | halcon_ext | cooc_feature_image | - | - | - |
| `hx_full_domain` | image->region | halcon_ext | full_domain | - | - | - |
| `hx_mean_shape` | image | halcon_ext | mean_image_shape | - | - | - |
| `hx_close_edges` | image | halcon_ext | close_edges | - | - | - |
| `hx_close_edges_length` | image | halcon_ext | close_edges_length | - | - | - |
| `hx_expand_region` | region | halcon_ext | expand_region | - | - | - |
| `hx_region_to_mean` | image | halcon_ext | region_to_mean | - | - | - |
| `hx_nonmax_dir` | image | halcon_ext | nonmax_suppression_dir | - | - | - |
| `hx_char_threshold` | image->region | halcon_ext | char_threshold | - | - | - |
| `hx_histo_to_thresh` | image->region | halcon_ext | histo_to_thresh | - | - | - |
| `hx_gen_lowpass` | image | halcon_ext | gen_lowpass | - | - | - |
| `hx_gen_highpass` | image | halcon_ext | gen_highpass | - | - | - |
| `hx_gen_bandpass` | image | halcon_ext | gen_bandpass | - | - | - |
| `hx_erosion1` | region | halcon_ext | erosion1 | - | - | - |
| `hx_dilation1` | region | halcon_ext | dilation1 | - | - | - |
| `hx_opening` | region | halcon_ext | opening | - | - | - |
| `hx_closing` | region | halcon_ext | closing | - | - | - |
| `hx_dilation2` | region | halcon_ext | dilation2 | - | - | - |
| `hx_gen_disc_se` | image->region | halcon_ext | gen_disc_se | - | - | - |
| `hx_gen_circle_sector` | image->region | halcon_ext | gen_circle_sector | - | - | - |
| `hx_gen_ellipse_sector` | image->region | halcon_ext | gen_ellipse_sector | - | - | - |
| `hx_gen_empty_region` | image->region | halcon_ext | gen_empty_region | - | - | - |
| `hx_clip_region_rel` | region | halcon_ext | clip_region_rel | - | - | - |
| `hx_gen_bandfilter` | image | halcon_ext | gen_bandfilter | - | - | - |
| `hx_gen_derivative_filter` | image | halcon_ext | gen_derivative_filter | - | - | - |
| `hx_fill_interlace` | image | halcon_ext | fill_interlace | - | - | - |
| `hx_shade_height_field` | image | halcon_ext | shade_height_field | - | - | - |
| `hx_plane_deviation` | image | halcon_ext | plane_deviation | - | - | - |
| `hx_detect_edge_segments` | image->region | halcon_ext | detect_edge_segments | - | - | - |
| `hx_gen_image_proto` | image | halcon_ext | gen_image_proto | - | - | - |
| `hx_get_domain` | image->region | halcon_ext | get_domain | - | - | - |
| `hx_region_to_label` | image | halcon_ext | region_to_label | - | - | - |
| `hx_rectangle1_domain` | image->region | halcon_ext | rectangle1_domain | - | - | - |
| `hx_lowlands` | image->region | halcon_ext | lowlands | - | - | - |
| `hx_plateaus_center` | image->region | halcon_ext | plateaus_center | - | - | - |
| `hx_move_region` | region | halcon_ext | move_region | - | - | - |
| `hx_split_skeleton_region` | region | halcon_ext | split_skeleton_region | - | - | - |
| `hx_test_region_point` | region->feature | halcon_ext | test_region_point | - | - | - |
| `hx_test_region_points` | region->feature | halcon_ext | test_region_points | - | - | - |
| `hx_sort_contours` | contour | halcon_ext | sort_contours_xld | - | - | - |
| `hx_clip_contours` | contour | halcon_ext | clip_contours_xld | - | - | - |
| `hx_clip_end_points` | contour | halcon_ext | clip_end_points_contours_xld | - | - | - |
| `hx_smallest_circle_xld` | contour->feature | halcon_ext | smallest_circle_xld | - | - | - |
| `hx_smallest_rect1_xld` | contour->feature | halcon_ext | smallest_rectangle1_xld | - | - | - |
| `hx_test_closed_xld` | contour->feature | halcon_ext | test_closed_xld | - | - | - |
| `hx_regress_contours` | contour->feature | halcon_ext | regress_contours_xld | - | - | - |
| `hx_moments_any_xld` | contour->feature | halcon_ext | moments_any_xld | - | - | - |
| `hx_split_contours` | contour | halcon_ext | split_contours_xld | - | - | - |
| `hx_gen_parallel_contour` | contour | halcon_ext | gen_parallel_contour_xld | - | - | - |
| `hx_fit_circle_contour` | contour->feature | halcon_ext | fit_circle_contour_xld | - | - | - |
| `hx_fit_ellipse_contour` | contour->feature | halcon_ext | fit_ellipse_contour_xld | - | - | - |
| `hx_fit_rectangle2_contour` | contour->feature | halcon_ext | fit_rectangle2_contour_xld | - | - | - |
| `hx_smallest_rect2_xld` | contour->feature | halcon_ext | smallest_rectangle2_xld | - | - | - |
| `hx_crop_contours` | contour | halcon_ext | crop_contours_xld | - | - | - |
| `hx_dist_ellipse_contour` | contour->feature | halcon_ext | dist_ellipse_contour_xld | - | - | - |
| `hx_test_self_intersect` | contour->feature | halcon_ext | test_self_intersection_xld | - | - | - |
| `hx_union_adjacent` | contour | halcon_ext | union_adjacent_contours_xld | - | - | - |
| `hx_polar_trans_inv` | contour | halcon_ext | polar_trans_contour_xld_inv | - | - | - |
| `hx_select_xld_point` | contour | halcon_ext | select_xld_point | - | - | - |
| `hx_estimate_tilt_lr` | image->feature | halcon_ext | estimate_tilt_lr | - | - | - |
| `hx_estimate_tilt_zc` | image->feature | halcon_ext | estimate_tilt_zc | - | - | - |
| `hx_estimate_sl_al_lr` | image->feature | halcon_ext | estimate_sl_al_lr | - | - | - |
| `hx_estimate_sl_al_zc` | image->feature | halcon_ext | estimate_sl_al_zc | - | - | - |
| `hx_estimate_al_am` | image->feature | halcon_ext | estimate_al_am | - | - | - |
| `hx_add_noise_contour` | contour | halcon_ext | add_noise_white_contour_xld | - | - | - |
| `hx_radial_distort_contour` | contour | halcon_ext | change_radial_distortion_contours_xld | - | - | - |
| `hx_dist_ellipse_points` | contour->feature | halcon_ext | dist_ellipse_contour_points_xld | - | - | - |
| `hx_dist_rect2_points` | contour->feature | halcon_ext | dist_rectangle2_contour_points_xld | - | - | - |
| `hx_distance_pc` | contour->feature | halcon_ext | distance_pc | - | - | - |
| `hx_disparity_to_xyz` | image | halcon_ext | disparity_image_to_xyz | - | - | - |
| `hx_distance_pr` | region->feature | halcon_ext | distance_pr | - | - | - |
| `hx_distance_sc` | contour->feature | halcon_ext | distance_sc | - | - | - |
| `hx_fuzzy_measure_pairs` | image->feature | halcon_ext | fuzzy_measure_pairs | - | - | - |
| `macro_denoise` | image | macro |  | - | - | - |
| `macro_edge` | image->region | macro |  | - | - | - |
| `macro_binarize` | image | macro |  | - | - | - |
| `macro_vol_denoise` | volume | macro |  | - | - | - |
| `tb_points_to_voxel` | points->volume | typed |  | - | - | - |
| `tb_estimate_point_normals` | points | typed |  | - | - | - |
| `tb_iss_keypoints` | points->signal | typed |  | - | - | - |
| `tb_angle_3points` | points->feature | typed |  | - | - | - |
| `tb_project_points` | points->keypoints | typed |  | - | - | - |
| `tb_render_point_depth` | points->image | typed |  | - | - | - |
| `tb_statistical_outlier_removal` | points | typed |  | - | - | - |
| `tb_radius_outlier_removal` | points | typed |  | - | - | - |
| `tb_voxel_grid_downsample` | points | typed |  | - | - | - |
| `tb_mls_smooth` | points | typed |  | - | - | - |
| `tb_alpha_shape_boundary` | points->signal | typed |  | - | - | - |
| `tb_estimate_alpha` | points->feature | typed |  | - | - | - |
| `tb_arc_length` | points->feature | typed |  | - | - | - |
| `tb_resample_uniform` | points | typed |  | - | - | - |
| `tb_fit_spline_curve` | points | typed |  | - | - | - |
| `tb_mean_curvature` | points->signal | typed |  | - | - | - |
| `tb_gaussian_curvature` | points->signal | typed |  | - | - | - |
| `tb_estimate_normals` | points | typed |  | - | - | - |
| `tb_inertia_tensor` | points->matrix | typed |  | - | - | - |
| `tb_geodesic_distances` | points->signal | typed |  | - | - | - |
| `tb_farthest_point_sampling` | points->signal | typed |  | - | - | - |
| `tb_synthesize_silhouette` | points->image | typed |  | - | - | - |
| `tb_inside_outside` | points->signal | typed |  | - | - | - |
| `tb_superquadric_residual` | points->feature | typed |  | - | - | - |
| `tb_project` | points->image | typed |  | - | - | - |
| `tb_jitter` | points | typed |  | - | - | - |
| `tb_random_rotation` | points | typed |  | - | - | - |
| `tb_random_scale` | points | typed |  | - | - | - |
| `tb_random_dropout` | points | typed |  | - | - | - |
| `tb_elastic_deform` | points | typed |  | - | - | - |
| `tb_cutout` | points | typed |  | - | - | - |
| `tb_region_growing` | points->volume | typed |  | - | - | - |
| `tb_euclidean_cluster` | points->volume | typed |  | - | - | - |
| `tb_plane_segmentation` | points->volume | typed |  | - | - | - |
| `tb_estimate_oriented_normals` | points | typed |  | - | - | - |
| `tb_occupancy_grid` | points->volume | typed |  | - | - | - |
| `tb_reflect_points` | points | typed |  | - | - | - |
| `tb_reflection_symmetry_score` | points->feature | typed |  | - | - | - |
| `tb_project_spherical` | points->image | typed |  | - | - | - |
| `tb_project_cylindrical` | points->image | typed |  | - | - | - |
| `tb_sphere_sdf` | points->volume | typed |  | - | - | - |
| `tb_box_sdf` | points->volume | typed |  | - | - | - |
| `tb_pc_poisson_disk` | points | typed |  | - | - | - |
| `tb_pc_fill_sparse` | points | typed |  | - | - | - |
| `tb_pc_density_equalize` | points | typed |  | - | - | - |
| `tb_create_funct_1d_array` | signal | typed |  | - | - | - |
| `tb_smooth_funct_1d_gauss` | signal | typed |  | - | - | - |
| `tb_smooth_funct_1d_mean` | signal | typed |  | - | - | - |
| `tb_derivate_funct_1d` | signal | typed |  | - | - | - |
| `tb_integrate_funct_1d` | signal | typed |  | - | - | - |
| `tb_zero_crossings_funct_1d` | signal | typed |  | - | - | - |
| `tb_abs_funct_1d` | signal | typed |  | - | - | - |
| `tb_negate_funct_1d` | signal | typed |  | - | - | - |
| `tb_scale_y_funct_1d` | signal | typed |  | - | - | - |
| `tb_sample_funct_1d` | signal | typed |  | - | - | - |
| `tb_num_points_funct_1d` | signal->feature | typed |  | - | - | - |
| `tb_get_y_value_funct_1d` | signal->feature | typed |  | - | - | - |
| `tb_lowpass` | signal | typed |  | - | - | - |
| `tb_highpass` | signal | typed |  | - | - | - |
| `tb_bandpass` | signal | typed |  | - | - | - |
| `tb_envelope` | signal | typed |  | - | - | - |
| `tb_rms` | signal->feature | typed |  | - | - | - |
| `tb_resample` | signal | typed |  | - | - | - |
| `tb_spectrogram` | signal->image | typed |  | - | - | - |
| `tb_zero_crossing_rate` | signal->feature | typed |  | - | - | - |
| `tb_find_peaks` | signal | typed |  | - | - | - |
| `tb_cx_ifft` | cimage->image | typed |  | - | - | - |
| `tb_cx_magnitude` | cimage->image | typed |  | - | - | - |
| `tb_cx_phase` | cimage->image | typed |  | - | - | - |
| `tb_cx_real` | cimage->image | typed |  | - | - | - |
| `tb_cx_imag` | cimage->image | typed |  | - | - | - |
| `tb_cx_log_magnitude` | cimage->image | typed |  | - | - | - |
| `tb_cx_apply_transfer_function` | cimage | typed |  | - | - | - |
| `tb_mat_pinv` | matrix | typed |  | - | - | - |
| `tb_mat_cond` | matrix->feature | typed |  | - | - | - |
| `tb_stat_covariance` | matrix | typed |  | - | - | - |
| `tb_stat_correlation` | matrix | typed |  | - | - | - |
| `tb_stat_zscore` | signal | typed |  | - | - | - |
| `tb_cplx_cr_residual` | cimage->feature | typed |  | - | - | - |
| `tb_angular_spectrum_propagate` | cimage | typed |  | - | - | - |
| `tb_wetness` | rgbimage | typed |  | - | - | - |
| `tb_env_studio` | points->signal | typed |  | - | - | - |
| `tb_env_lightbox` | points->signal | typed |  | - | - | - |
| `tb_sensor_capture` | rgbimage | typed |  | - | - | - |
| `tb_lf_to_mla` | lightfield->image | typed |  | - | - | - |
| `tb_lf_subaperture` | lightfield->image | typed |  | - | - | - |
| `tb_lf_center_view` | lightfield->image | typed |  | - | - | - |
| `tb_lf_epi` | lightfield->image | typed |  | - | - | - |
| `tb_lf_refocus` | lightfield->image | typed |  | - | - | - |
| `tb_lf_synthetic_aperture` | lightfield->image | typed |  | - | - | - |
| `tb_lf_depth_from_focus` | lightfield->image | typed |  | - | - | - |
| `tb_lf_epi_slope` | lightfield->image | typed |  | - | - | - |
| `tb_spad_deadtime_apply` | counts | typed |  | - | - | - |
| `tb_spad_deadtime_correct` | counts | typed |  | - | - | - |
| `tb_tcspc_coates_correct` | counts | typed |  | - | - | - |
| `tb_tcspc_irf_convolve` | counts | typed |  | - | - | - |
| `tb_tcspc_background_subtract` | counts | typed |  | - | - | - |
| `tb_dtof_depth` | counts->feature | typed |  | - | - | - |
| `tb_specular_diffuse_split` | rgbimage | typed |  | - | - | - |
| `tb_specular_coefficient_map` | rgbimage->image | typed |  | - | - | - |
| `tb_specular_free_transform` | rgbimage | typed |  | - | - | - |
| `tb_temporal_bandpass` | video | typed |  | - | - | - |
| `tb_temporal_band_power` | video->image | typed |  | - | - | - |
| `tb_rgb_to_quaternion` | rgbimage->qimage | typed |  | - | - | - |
| `tb_quaternion_to_rgb` | qimage->rgbimage | typed |  | - | - | - |
| `tb_quat_norm` | qimage->image | typed |  | - | - | - |
| `tb_quat_conjugate_image` | qimage | typed |  | - | - | - |
| `tb_quat_normalize_image` | qimage | typed |  | - | - | - |
| `tb_monogenic_amplitude` | qimage->image | typed |  | - | - | - |
| `tb_monogenic_phase` | qimage->image | typed |  | - | - | - |
| `tb_monogenic_orientation` | qimage->image | typed |  | - | - | - |
| `tb_quat_color_rotate` | qimage | typed |  | - | - | - |
| `tb_quat_color_filter` | qimage | typed |  | - | - | - |
| `tb_qft2` | qimage | typed |  | - | - | - |
| `tb_iqft2` | qimage | typed |  | - | - | - |
| `tb_fmcw_window_apply` | beatcube | typed |  | - | - | - |
| `tb_range_doppler_map` | beatcube->image | typed |  | - | - | - |
| `tb_fmcw_range_profile` | beatcube->signal | typed |  | - | - | - |
| `tb_beamform_delay_sum` | beatcube->signal | typed |  | - | - | - |
| `tb_weighting_response` | signal | typed |  | - | - | - |
| `tb_apply_weighting` | signal | typed |  | - | - | - |
| `tb_equivalent_level` | signal->feature | typed |  | - | - | - |
| `tb_normals_to_egi` | points->image | typed |  | - | - | - |
| `tb_keypoints_uv_to_points` | keypoints->points | typed |  | - | - | - |
| `tb_points_zyx_to_keypoints_uv` | points->keypoints | typed |  | - | - | - |
| `tb_keypoints_to_image2d` | keypoints->image | typed |  | - | - | - |
| `tb_indices_to_labels` | signal->volume | typed |  | - | - | - |
| `tb_countrate_to_counts` | counts | typed |  | - | - | - |
| `tb_counts_to_countrate` | counts | typed |  | - | - | - |
| `tb_temporal_median_window` | video | typed |  | - | - | - |
| `tb_moving_average_window` | video | typed |  | - | - | - |
| `tb_background_subtraction_window` | video | typed |  | - | - | - |
| `tb_frame_difference_causal` | video | typed |  | - | - | - |
| `tb_exponential_background` | video | typed |  | - | - | - |
| `tb_exponential_foreground` | video | typed |  | - | - | - |
| `tb_optical_flow_magnitude_stream` | video | typed |  | - | - | - |
| `tb_motion_history_image` | video | typed |  | - | - | - |
| `tb_motion_energy_image` | video | typed |  | - | - | - |
| `tb_three_frame_difference` | video | typed |  | - | - | - |
| `tb_running_gaussian_foreground` | video | typed |  | - | - | - |
| `tb_running_gaussian_background` | video | typed |  | - | - | - |
| `tb_temporal_bilateral` | video | typed |  | - | - | - |
| `tb_deflicker` | video | typed |  | - | - | - |
| `tb_shape_perturb` | points | typed |  | - | - | - |
| `tb_mirror_plane_from_pairs` | points->matrix | typed |  | - | - | - |
| `tb_landmark_asymmetry` | points->signal | typed |  | - | - | - |
| `tb_dem_ecef_to_geodetic` | points | typed |  | - | - | - |

## Coverage (ops with a direct analog)
- opencv: 310/885
- skimage: 383/885
- matlab: 259/885

## Roadmap toward full coverage
- HALCON ~2100 operators: add regions/XLD-contours/matching/OCR/calibration sorts.
- OpenCV ~2500 functions, scikit-image ~300: extend registry per family; analogs auto-tracked here.
- Adding an op with its ANALOGS row extends the catalog + search + codegen automatically.
