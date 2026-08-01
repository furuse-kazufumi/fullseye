# imgevolve — HALCON coverage (honest, partial)

I don't have all ~2100 HALCON operators memorised. Below is HALCON's chapter structure with **estimated** counts and a **curated** (non-exhaustive) operator list, mapped against our registry's `halcon` analog names. The authoritative list is the **MVTec HALCON Operator Reference** — ingesting it (RAD) is how we drive exhaustive coverage.

Our registry currently exposes **153 operators**; HALCON is estimated at **~2330** (of which a large share is non-algorithmic infrastructure — graphics/tuple/system/file).

| chapter | est. count | curated known | ours (matched) |
|---|---|---|---|
| Filters | ~150 | 26 | 18: anisotropic_diffusion, bilateral_filter, butterworth, diff_of_gauss, dyn_threshold, edges_image, emphasize, gauss_filter, gen_gabor, gray_range_rect, highpass, laplace, laplace_of_gauss, lowpass, mean_image, median_image, rank_image, sobel_amp |
| Morphology | ~90 | 17 | 13: boundary, closing_circle, connection, fill_up, gray_bothat, gray_closing, gray_dilation, gray_erosion, gray_opening, gray_range_rect, gray_tophat, opening_circle, skeleton |
| Regions | ~140 | 19 | 13: area_center, binary_threshold, clear_border, complement, connection, dilation_circle, dyn_threshold, erosion_circle, fill_up, select_shape_area, select_shape_largest, threshold, var_threshold |
| XLD / Contours | ~180 | 14 | 7: edges_sub_pix, find_contours, fit_line_contour_xld, gen_region_contour_xld, length_xld, select_contours_xld, smooth_contours_xld |
| Matching | ~120 | 8 | 2: find_ncc_model, find_shape_model |
| Measuring | ~60 | 4 | 0: — |
| Identification (Bar/Data code, OCR) | ~120 | 8 | 1: decode_bar_code |
| Calibration | ~90 | 4 | 0: — |
| 3D (object model / reconstruction / metrology / matching) | ~330 | 8 | 0: — |
| Classification | ~120 | 6 | 1: select_shape_circularity |
| Deep Learning | ~150 | 4 | 0: — |
| Image (channels / access / generation) | ~120 | 11 | 7: affine_trans_image, equ_histo_image, invert_image, pow_image, rotate_image, scale_image, zoom_image_size |
| Graphics / Visualization | ~200 | 3 | 0: — |
| Tuple / System / File / Tools | ~460 | 4 | 1: count_obj |

**Matched 63 curated HALCON operators** across chapters (the imgevolve registry has 153 ops incl. OpenCV/skimage/torch analogs).

## Honest reading
- Algorithmic chapters ~1670 operators; ~660 are infrastructure (graphics/tuple/system/file) that an algorithm-design engine does not target.
- Many HALCON operators are parametric variants of a family (collapse to fewer).
- **Gap to full coverage**: 3D/DL/OCR/calibration/matching need heavy deps (Open3D/torch/models) or the official reference for exact signatures. Next: fetch the MVTec Operator Reference into RAD, then generate typed stubs per operator so coverage is tracked against the real 2100, not memory.
