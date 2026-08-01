# imgevolve — cross-library operator catalog

153 operators across 17 categories, typed by sort (image/region/feature). Each maps to the nearest single-call API in HALCON / OpenCV / scikit-image / MATLAB. `-` = no direct one-call analog.

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

## Coverage (ops with a direct analog)
- opencv: 85/153
- skimage: 114/153
- matlab: 57/153

## Roadmap toward full coverage
- HALCON ~2100 operators: add regions/XLD-contours/matching/OCR/calibration sorts.
- OpenCV ~2500 functions, scikit-image ~300: extend registry per family; analogs auto-tracked here.
- Adding an op with its ANALOGS row extends the catalog + search + codegen automatically.
