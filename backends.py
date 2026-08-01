"""Optional library backends — scale the registry by WRAPPING ecosystems.

Reimplementing thousands of HALCON/OpenCV/skimage operators is the wrong move; the
right one is to *wrap* what already exists and keep only the differentiating layer
(typed IR + evolution + honest gate + codegen) in-house. If scikit-image / OpenCV
are installed, `build()` returns typed Op wrappers that the registry appends — so
op count scales with library coverage and evolution/codegen/catalog pick them up
for free. Every wrapper is exception-safe (a failing call degrades to identity)
because these are best-effort adapters over large APIs.

Backend ops are prefixed (`sk_`, `cv_`) so they never shadow the always-available
numpy/scipy core; the core keeps working when neither library is present.
"""
from __future__ import annotations

import numpy as np


def _safe(fn):
    def w(v, a, b):
        try:
            out = fn(v, a, b)
            return out if out is not None else v
        except Exception:
            return v
    return w


def _u8(v):
    return (np.clip(v, 0, 1) * 255).astype(np.uint8)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    ops_out = []

    # ---- scikit-image -------------------------------------------------------- #
    try:
        from skimage import filters, morphology, restoration, exposure, feature, measure

        def _disk(a):
            return morphology.disk(1 + int(a * 3))

        sk = [
            ("sk_scharr", "edges", "edges_image", IMAGE, IMAGE, lambda v, a, b: norm(filters.scharr(v))),
            ("sk_farid", "edges", "edges_image", IMAGE, IMAGE, lambda v, a, b: norm(filters.farid(v))),
            ("sk_frangi", "texture", "lines_gauss", IMAGE, IMAGE,
             lambda v, a, b: norm(filters.frangi(v, sigmas=range(1, 4)))),
            ("sk_meijering", "texture", "lines_gauss", IMAGE, IMAGE,
             lambda v, a, b: norm(filters.meijering(v, sigmas=range(1, 4)))),
            ("sk_hessian", "texture", "lines_gauss", IMAGE, IMAGE,
             lambda v, a, b: norm(filters.hessian(v, sigmas=range(1, 4)))),
            ("sk_dog", "edges", "diff_of_gauss", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(filters.difference_of_gaussians(v, 1.0, 1.0 + 3.0 * a)))),
            ("sk_gabor", "texture", "gen_gabor", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(filters.gabor(v, frequency=0.1 + 0.3 * a)[0]))),
            ("sk_butterworth", "frequency", "butterworth", IMAGE, IMAGE,
             lambda v, a, b: np.clip(filters.butterworth(v, cutoff_frequency_ratio=0.05 + 0.3 * a), 0, 1)),
            ("sk_tv", "smoothing", "tv_denoise", IMAGE, IMAGE,
             lambda v, a, b: restoration.denoise_tv_chambolle(v, weight=0.02 + 0.3 * a)),
            ("sk_wavelet", "smoothing", "wavelet_denoise", IMAGE, IMAGE,
             lambda v, a, b: np.clip(restoration.denoise_wavelet(v), 0, 1)),
            ("sk_adapthist", "gray", "emphasize_adaptive", IMAGE, IMAGE,
             lambda v, a, b: exposure.equalize_adapthist(np.clip(v, 0, 1), clip_limit=0.01 + 0.05 * a)),
            ("sk_median_disk", "rank", "median_image", IMAGE, IMAGE,
             lambda v, a, b: filters.median(v, footprint=_disk(a))),
            ("sk_otsu", "segmentation", "binary_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_otsu(v)).astype(np.float64)),
            ("sk_li", "segmentation", "binary_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_li(v)).astype(np.float64)),
            ("sk_yen", "segmentation", "binary_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_yen(v)).astype(np.float64)),
            ("sk_sauvola", "segmentation", "var_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_sauvola(v, window_size=2 * int(a * 6) + 3)).astype(np.float64)),
            ("sk_niblack", "segmentation", "var_threshold", IMAGE, REGION,
             lambda v, a, b: (v > filters.threshold_niblack(v, window_size=2 * int(a * 6) + 3)).astype(np.float64)),
            ("sk_canny", "segmentation", "edges_image", IMAGE, REGION,
             lambda v, a, b: feature.canny(v, sigma=0.5 + 2.0 * a).astype(np.float64)),
            ("sk_skeleton", "region", "skeleton", REGION, REGION,
             lambda v, a, b: morphology.skeletonize(binm(v)).astype(np.float64)),
            ("sk_medial", "region", "skeleton", REGION, REGION,
             lambda v, a, b: morphology.medial_axis(binm(v)).astype(np.float64)),
            ("sk_convex", "region", "shape_trans_convex", REGION, REGION,
             lambda v, a, b: morphology.convex_hull_image(binm(v)).astype(np.float64)),
            ("sk_thin", "region", "thinning", REGION, REGION,
             lambda v, a, b: morphology.thin(binm(v)).astype(np.float64)),
            ("sk_remove_holes", "region", "fill_up", REGION, REGION,
             lambda v, a, b: morphology.remove_small_holes(binm(v), area_threshold=int(8 + a * 60)).astype(np.float64)),
            ("sk_euler", "features", "euler_number", REGION, FEATURE,
             lambda v, a, b: np.float64(measure.euler_number(binm(v)))),
            ("sk_find_contours", "contour", "find_contours", IMAGE, CONTOUR,
             lambda v, a, b: {"shape": v.shape,
                              "cs": [c for c in measure.find_contours(v, 0.2 + 0.5 * a) if len(c) >= 3]}),
        ]
        ops_out += [Op(n, c, h, i, o, _safe(f)) for (n, c, h, i, o, f) in sk]
    except Exception:
        pass

    # ---- OpenCV -------------------------------------------------------------- #
    try:
        import cv2

        def _se(a):
            k = 3 + 2 * int(a * 3)
            return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))

        cv = [
            ("cv_bilateral", "smoothing", "bilateral_filter", IMAGE, IMAGE,
             lambda v, a, b: cv2.bilateralFilter(v.astype(np.float32), 5, 0.05 + 0.4 * b, 1.0 + 3.0 * a).astype(np.float64)),
            ("cv_median", "rank", "median_image", IMAGE, IMAGE,
             lambda v, a, b: cv2.medianBlur(_u8(v), 3 + 2 * int(a * 3)).astype(np.float64) / 255),
            ("cv_box", "smoothing", "mean_image", IMAGE, IMAGE,
             lambda v, a, b: cv2.blur(v, (3 + 2 * int(a * 3),) * 2)),
            ("cv_gaussian", "smoothing", "gauss_filter", IMAGE, IMAGE,
             lambda v, a, b: cv2.GaussianBlur(v, (0, 0), 0.3 + 2.7 * a)),
            ("cv_scharr", "edges", "edges_image", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(cv2.Scharr(v, cv2.CV_64F, 1, 0)) + np.abs(cv2.Scharr(v, cv2.CV_64F, 0, 1)))),
            ("cv_laplacian", "edges", "laplace", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(cv2.Laplacian(v, cv2.CV_64F)))),
            ("cv_clahe", "gray", "emphasize_adaptive", IMAGE, IMAGE,
             lambda v, a, b: cv2.createCLAHE(clipLimit=1.0 + 4.0 * a).apply(_u8(v)).astype(np.float64) / 255),
            ("cv_open", "morphology", "gray_opening", IMAGE, IMAGE,
             lambda v, a, b: cv2.morphologyEx(v, cv2.MORPH_OPEN, _se(a))),
            ("cv_close", "morphology", "gray_closing", IMAGE, IMAGE,
             lambda v, a, b: cv2.morphologyEx(v, cv2.MORPH_CLOSE, _se(a))),
            ("cv_tophat", "morphology", "gray_tophat", IMAGE, IMAGE,
             lambda v, a, b: norm(cv2.morphologyEx(v, cv2.MORPH_TOPHAT, _se(a)))),
            ("cv_gradient", "morphology", "gray_range_rect", IMAGE, IMAGE,
             lambda v, a, b: norm(cv2.morphologyEx(v, cv2.MORPH_GRADIENT, _se(a)))),
            ("cv_otsu", "segmentation", "binary_threshold", IMAGE, REGION,
             lambda v, a, b: (cv2.threshold(_u8(v), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1] > 0).astype(np.float64)),
            ("cv_adaptive_mean", "segmentation", "dyn_threshold", IMAGE, REGION,
             lambda v, a, b: (cv2.adaptiveThreshold(_u8(v), 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                                     cv2.THRESH_BINARY, 2 * int(a * 6) + 3, int(b * 10)) > 0).astype(np.float64)),
            ("cv_adaptive_gauss", "segmentation", "local_threshold", IMAGE, REGION,
             lambda v, a, b: (cv2.adaptiveThreshold(_u8(v), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                    cv2.THRESH_BINARY, 2 * int(a * 6) + 3, int(b * 10)) > 0).astype(np.float64)),
            ("cv_canny", "segmentation", "edges_image", IMAGE, REGION,
             lambda v, a, b: (cv2.Canny(_u8(v), int(50 + 100 * a), int(100 + 150 * b)) > 0).astype(np.float64)),
        ]
        ops_out += [Op(n, c, h, i, o, _safe(f)) for (n, c, h, i, o, f) in cv]
    except Exception:
        pass

    return ops_out
