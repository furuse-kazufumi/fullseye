# imgevolve — cross-library operator catalog

326 operators across 18 categories, typed by sort (image/region/feature). Each maps to the nearest single-call API in HALCON / OpenCV / scikit-image / MATLAB. `-` = no direct one-call analog.

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
| `laplace` | image | edges | laplace | Laplacian | filters.laplace | fspecial('laplacian') |
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
| `dyn_threshold` | image->region | segmentation | dyn_threshold | adaptiveThreshold | filters.threshold_local | adaptthresh |
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
| `local_max` | image->region | segmentation | local_max_sub_pix | - | feature.peak_local_max | imregionalmax |
| `dist_transform` | region->image | region | distance_transform | distanceTransform | ndi.distance_transform_edt | bwdist |
| `region_boundary` | region | region | boundary | findContours | segmentation.find_boundaries | bwperim |
| `convex_fill` | region | region | shape_trans | convexHull | morphology.convex_hull_image | bwconvhull |
| `edges_sub_pix` | image->contour | contour | edges_sub_pix | - | measure.find_contours | - |
| `select_contours` | contour | contour | select_contours_xld | (filter contours) | - | - |
| `smooth_contours` | contour | contour | smooth_contours_xld | approxPolyDP | - | - |
| `fit_line_contours` | contour | contour | fit_line_contour_xld | fitLine | measure.LineModelND | polyfit |
| `contours_to_region` | contour->region | contour | gen_region_contour_xld | drawContours/fillPoly | draw.polygon | poly2mask |
| `count_contours` | contour->feature | features | count_obj | len(findContours) | len(find_contours) | - |
| `total_length` | contour->feature | features | length_xld | arcLength | - | - |
| `ncc_locate` | image->match | matching | find_ncc_model | matchTemplate | feature.match_template | normxcorr2 |
| `rotate_img` | image | geometry | rotate_image | warpAffine(rot) | transform.rotate | imrotate |
| `rescale_img` | image | geometry | zoom_image_size | resize | transform.rescale | imresize |
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
| `area_center` | region->feature | features | area_center | - | measure.regionprops | regionprops |
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
| `gen_contour_region_xld` | region->contour | contour | gen_contour_region_xld | findContours | measure.find_contours | - |
| `select_shape_xld` | contour | contour | select_shape_xld | findContours | measure.find_contours | - |

## Coverage (ops with a direct analog)
- opencv: 239/326
- skimage: 277/326
- matlab: 216/326

## Roadmap toward full coverage
- HALCON ~2100 operators: add regions/XLD-contours/matching/OCR/calibration sorts.
- OpenCV ~2500 functions, scikit-image ~300: extend registry per family; analogs auto-tracked here.
- Adding an op with its ANALOGS row extends the catalog + search + codegen automatically.
