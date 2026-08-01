# imgevolve — operator research provenance

Seminal references for the 107 operators (families collapse many variants). The point: a designed pipeline is traceable to the literature, and the RAD image corpus is the mining source for *new* operators.

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
| `tophat` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `bothat` | morphology | Serra, J. (1982). Image Analysis and Mathematical Morphology. (Matheron 1975). |
| `morph_grad` | morphology | - |
| `sobel_mag` | edges | Sobel & Feldman (1968). A 3x3 isotropic gradient operator for image processing. |
| `laplace` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `prewitt_mag` | edges | Prewitt, J. (1970). Object enhancement and extraction. Picture Processing and Psychopictorics. |
| `roberts_mag` | edges | - |
| `dog` | edges | Marr & Hildreth (1980). Theory of edge detection. Proc. R. Soc. Lond. B. |
| `gamma` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `invert` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `scale_clip` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `equalize` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `sigmoid` | gray | Gonzalez & Woods, Digital Image Processing — intensity transformations. |
| `lowpass` | frequency | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `highpass` | frequency | Gonzalez & Woods, Digital Image Processing — frequency-domain filtering (Butterworth 1930). |
| `std_filter` | texture | - |
| `threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `otsu` | segmentation | Otsu, N. (1979). A threshold selection method from gray-level histograms. IEEE TSMC. |
| `dyn_threshold` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
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
| `local_max` | segmentation | - |
| `dist_transform` | region | Rosenfeld & Pfaltz (1966). Sequential operations in digital picture processing. JACM. |
| `region_boundary` | region | - |
| `convex_fill` | region | - |
| `edges_sub_pix` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `select_contours` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `smooth_contours` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `fit_line_contours` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `contours_to_region` | contour | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `count_contours` | features | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `total_length` | features | Steger, C. (1998). An unbiased detector of curvilinear structures (subpixel edges). IEEE TPAMI. |
| `ncc_locate` | matching | Lewis, J.P. (1995). Fast normalized cross-correlation. Vision Interface. |
| `rotate_img` | geometry | Wolberg, G. (1990). Digital Image Warping. IEEE CS Press. |
| `rescale_img` | geometry | Wolberg, G. (1990). Digital Image Warping. IEEE CS Press. |
| `affine_warp` | geometry | Wolberg, G. (1990). Digital Image Warping. IEEE CS Press. |
| `gabor` | texture | Daugman, J. (1985). Uncertainty relation for resolution... 2D visual cortical filters. JOSA A. |
| `clahe` | gray | Zuiderveld, K. (1994). Contrast Limited Adaptive Histogram Equalization. Graphics Gems IV. |
| `corner_response` | edges | Harris & Stephens (1988). A combined corner and edge detector. Alvey Vision Conf. |
| `adaptive_gauss_thresh` | segmentation | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
| `shape_locate` | matching | Steger, C. (2002). Occlusion-, clutter-, and illumination-invariant object recognition (shape-based matching). |
| `classify_shape` | classification | Danielsson, P.-E. (1978). A new shape factor (circularity). Computer Graphics and Image Processing. |
| `decode_barcode` | barcode | Wang & Srihari (1988). Object recognition in structured / barcode reading. (1D symbology). |
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

**Provenance coverage: 83/107 operators cite a seminal paper.**

## Mining new operators from research (RAD)
- RAD image / diffusion / deep_learning corpora (thousands of papers) = the source for operators beyond the classics: modern denoisers (BM3D, DnCNN), learned edges (HED), superpixels (SLIC), diffusion priors, foundation segmenters (SAM).
- Workflow: mine a paper -> add a typed Op (fn + sort + analogs + this reference) -> evolution/codegen/catalog pick it up automatically.
