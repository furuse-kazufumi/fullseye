# imgevolve — cross-library operator catalog

67 operators across 16 categories, typed by sort (image/region/feature). Each maps to the nearest single-call API in HALCON / OpenCV / scikit-image / MATLAB. `-` = no direct one-call analog.

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
| `prewitt_mag` | image | edges | prewitt | - | filters.prewitt | edge(...,'prewitt') |
| `roberts_mag` | image | edges | roberts | - | filters.roberts | edge(...,'roberts') |
| `dog` | image | edges | diff_of_gauss | - | filters.difference_of_gaussians | - |
| `gamma` | image | gray | pow_image | LUT | exposure.adjust_gamma | imadjust |
| `invert` | image | gray | invert_image | bitwise_not | util.invert | imcomplement |
| `scale_clip` | image | gray | scale_image | convertScaleAbs | exposure.rescale_intensity | imadjust |
| `equalize` | image | gray | equ_histo_image | equalizeHist | exposure.equalize_hist | histeq |
| `sigmoid` | image | gray | scale_image_max | - | exposure.adjust_sigmoid | - |
| `lowpass` | image | frequency | lowpass | dft+mask | fft+mask | fft2+mask |
| `highpass` | image | frequency | highpass | dft+mask | fft+mask | fft2+mask |
| `std_filter` | image | texture | deviation_image | - | filters.rank (std) | stdfilt |
| `threshold` | image->region | segmentation | threshold | threshold | img>t | imbinarize |
| `otsu` | image->region | segmentation | binary_threshold | threshold(OTSU) | filters.threshold_otsu | otsuthresh/graythresh |
| `dyn_threshold` | image->region | segmentation | dyn_threshold | adaptiveThreshold | filters.threshold_local | adaptthresh |
| `reg_erode` | region | region | erosion_circle | erode | morphology.binary_erosion | imerode |
| `reg_dilate` | region | region | dilation_circle | dilate | morphology.binary_dilation | imdilate |
| `reg_open` | region | region | opening_circle | morphologyEx(OPEN) | morphology.binary_opening | imopen |
| `reg_close` | region | region | closing_circle | morphologyEx(CLOSE) | morphology.binary_closing | imclose |
| `fill_holes` | region | region | fill_up | floodFill | ndi.binary_fill_holes | imfill('holes') |
| `select_largest` | region | region | select_shape_largest | connectedComponents+max | measure.label+regionprops | bwareafilt |
| `remove_small` | region | region | select_shape_area | - | morphology.remove_small_objects | bwareaopen |
| `invert_region` | region | region | complement | bitwise_not | util.invert | imcomplement |
| `blob_count` | region->feature | features | count_obj | connectedComponents | measure.label | bwconncomp |
| `area_frac` | region->feature | features | area_center | countNonZero | regionprops(area) | bwarea |
| `grad_dir` | image | edges | direction_gradient | phase | - | imgradient |
| `log` | image | edges | laplace_of_gauss | - | filters.laplace(gaussian) | fspecial('log') |
| `canny` | image->region | segmentation | edges_image | Canny | feature.canny | edge(...,'canny') |
| `local_max` | image->region | segmentation | local_max_sub_pix | - | feature.peak_local_max | imregionalmax |
| `dist_transform` | region->image | region | distance_transform | distanceTransform | ndi.distance_transform_edt | bwdist |
| `region_boundary` | region | region | boundary | findContours | segmentation.find_boundaries | bwperim |
| `convex_fill` | region | region | shape_trans_convex | convexHull | morphology.convex_hull_image | bwconvhull |
| `edges_sub_pix` | image->contour | contour | edges_sub_pix | - | measure.find_contours | - |
| `select_contours` | contour | contour | select_contours_xld | (filter contours) | - | - |
| `smooth_contours` | contour | contour | smooth_contours_xld | approxPolyDP | - | - |
| `fit_line_contours` | contour | contour | fit_line_contour_xld | fitLine | measure.LineModelND | polyfit |
| `contours_to_region` | contour->region | contour | gen_region_contour_xld | drawContours/fillPoly | draw.polygon | poly2mask |
| `count_contours` | contour->feature | features | count_obj_contours | len(findContours) | len(find_contours) | - |
| `total_length` | contour->feature | features | length_xld | arcLength | - | - |
| `ncc_locate` | image->match | matching | find_ncc_model | matchTemplate | feature.match_template | normxcorr2 |
| `rotate_img` | image | geometry | rotate_image | warpAffine(rot) | transform.rotate | imrotate |
| `rescale_img` | image | geometry | zoom_image_size | resize | transform.rescale | imresize |
| `affine_warp` | image | geometry | affine_trans_image | warpAffine | transform.warp(Affine) | imwarp |
| `gabor` | image | texture | gen_gabor | getGaborKernel+filter2D | filters.gabor | imgaborfilt |
| `clahe` | image | gray | emphasize_adaptive | createCLAHE | exposure.equalize_adapthist | adapthisteq |
| `corner_response` | image | edges | points_harris | cornerHarris | feature.corner_harris | detectHarrisFeatures |
| `adaptive_gauss_thresh` | image->region | segmentation | local_threshold | adaptiveThreshold(GAUSSIAN) | filters.threshold_local | adaptthresh |
| `shape_locate` | image->match | matching | find_shape_model | matchTemplate+rotations | - | - |
| `classify_shape` | region->feature | classification | select_shape_circularity | - | regionprops(circularity) | regionprops('Circularity') |
| `decode_barcode` | image->feature | barcode | decode_bar_code | barcode.BarcodeDetector | - | readBarcode |

## Coverage (ops with a direct analog)
- opencv: 56/67
- skimage: 59/67
- matlab: 57/67

## Roadmap toward full coverage
- HALCON ~2100 operators: add regions/XLD-contours/matching/OCR/calibration sorts.
- OpenCV ~2500 functions, scikit-image ~300: extend registry per family; analogs auto-tracked here.
- Adding an op with its ANALOGS row extends the catalog + search + codegen automatically.
