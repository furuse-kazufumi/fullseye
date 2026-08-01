# imgevolve — cross-library operator catalog

42 operators across 11 categories, typed by sort (image/region/feature). Each maps to the nearest single-call API in HALCON / OpenCV / scikit-image / MATLAB. `-` = no direct one-call analog.

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

## Coverage (ops with a direct analog)
- opencv: 35/42
- skimage: 40/42
- matlab: 38/42

## Roadmap toward full coverage
- HALCON ~2100 operators: add regions/XLD-contours/matching/OCR/calibration sorts.
- OpenCV ~2500 functions, scikit-image ~300: extend registry per family; analogs auto-tracked here.
- Adding an op with its ANALOGS row extends the catalog + search + codegen automatically.
