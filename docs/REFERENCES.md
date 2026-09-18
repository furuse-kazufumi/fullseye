# imgevolve — operator research provenance

Seminal references for the 153 operators (families collapse many variants). The point: a designed pipeline is traceable to the literature, and the RAD image corpus is the mining source for *new* operators.

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
| `vol_gaussian` | 3d | - |
| `vol_median` | 3d | Tukey, J. (1977). Exploratory Data Analysis (running median smoothing). |
| `vol_erode` | 3d | - |
| `vol_dilate` | 3d | - |
| `vol_threshold` | 3d | Sauvola & Pietikäinen (2000). Adaptive document image binarization. Pattern Recognition. |
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

**Provenance coverage: 98/153 operators cite a seminal paper.**

## 2026-09-17 additions — measured against the primary sources

The local RAD corpus returned **zero** papers for document skew estimation, projection
profiles and the bimodality coefficient (113 corpora, 57,858 docs; it holds almost no
pre-2020 document-analysis literature). These were checked against the primary sources
directly, so the provenance below is not "not found in our corpus" — it is *found, and
the operator is a member of that family*.

| op | category | seminal reference |
|---|---|---|
| `deskew` | geometry | Postl, W. (1986). Detection of linear oblique structures and skew scan in digitized documents. ICPR — **projection-profile variance criterion**. Baird, H. S. (1987). The skew angle of printed documents. SPSE — **sum-of-squares objective with coarse-to-fine angular search**, which is the family this op belongs to. |
| `local_bimodality` | texture | Pfister, R., Schwarz, K. A., Janczyk, M., Dale, R., & Freeman, J. B. (2013). Good things peak in pairs: a note on the bimodality coefficient. *Frontiers in Psychology*, 4, 700. doi:10.3389/fpsyg.2013.00700 — BC = (m3^2+1)/kurtosis, BCcrit = 5/9, **and the skewed-unimodal false positive this op inherits**. Adjacent: Barron, J. T. (2020). A Generalization of Otsu's Method and Minimum Error Thresholding. arXiv:2007.07350 — GHT generalises *which* threshold to pick; `local_bimodality` measures *whether one exists*. |
| `img_to_projection_profile` | bridge | The plain (mean) projection profile is the classic document-analysis primitive used by Postl/Baird above; HALCON packages it as `gray_projections`. The upper-trimmed-mean family that interpolates to maximum-intensity projection follows the quantile-projection idea used for temporal fusion in fluorescence microscopy (arXiv:2601.10392). |
| `signal_to_img` · `counts_to_img` · `matrix_to_img` · `contour_to_img` · `feature_to_img` | bridge | No literature claim — these are **return bridges** that give non-image sorts a typed path back to an image. They reuse this repo's own closed-form plotting layer (`annotate.axes_transform` / `plot_series`) and `imagedraw`. |

## 2026-09-18 additions — polarisation camera (re-implemented from the primary definitions)

| op | category | seminal reference |
|---|---|---|
| `polarization_demosaic` | optics / polarization | Mosaic convention `[[90, 45], [135, 0]]` of the Sony IMX250MZR block and the "four Bayer planes" reading as documented by **Polanalyser** (Maeda, R., github.com/elerac/polanalyser, MIT). Interpolation = the classic bilinear Bayer demosaic (`[[1,2,1],[2,4,2],[1,2,1]]/4` on the masked plane); the border mirrors the mosaic with an even, non-duplicating reflection to keep the 2x2 phase. No code copied; no OpenCV. |
| `mueller_from_intensities` | optics / polarization | Chipman, R. A., *Polarimetry*, Handbook of Optics vol. II ch. 15 — `I_i = a_i^T M g_i` is linear in vec(M) with observation rows `outer(a_i, g_i)`. Polanalyser's `calcMueller` is the pseudo-inverse form of the same system; ours adds an explicit rank check (linear polarisers only → rank 9, refused). |
| `mueller_checks` | optics / polarization | Cloude, S. R. (1986). Group theory and polarisation algebra. *Optik* 75, 26–36 (coherency matrix ≥ 0 ⇔ physical); Gil, J. J. (2007). Polarimetric characterization of light and media. *Eur. Phys. J. Appl. Phys.* 40, 1–47; Gil, J. J. & Bernabeu, E. (1986). Depolarization and polarization indices of an optical system. *Optica Acta* 33, 185–189. The check set mirrors what **py-pol** (del Hoyo & Sánchez Brea, MIT) exposes; re-implemented. |

## Mining new operators from research (RAD)
- RAD image / diffusion / deep_learning corpora (thousands of papers) = the source for operators beyond the classics: modern denoisers (BM3D, DnCNN), learned edges (HED), superpixels (SLIC), diffusion priors, foundation segmenters (SAM).
- Workflow: mine a paper -> add a typed Op (fn + sort + analogs + this reference) -> evolution/codegen/catalog pick it up automatically.
