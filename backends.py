"""Optional library backends — scale the registry by WRAPPING ecosystems.

Reimplementing thousands of HALCON/OpenCV/skimage operators is the wrong move; the
right one is to *wrap* what already exists and keep only the differentiating layer
(typed IR + evolution + honest gate + codegen) in-house. If scikit-image / OpenCV
are installed, `build()` returns typed Op wrappers that the registry appends — so
op count scales with library coverage and evolution/codegen/catalog pick them up
for free. Every wrapper is exception-safe (a failing call degrades to identity)
because these are best-effort adapters over large APIs — see `_safe` for why that
degradation is a LAST RESORT and how to make it detectable.

Backend ops are prefixed (`sk_`, `cv_`) so they never shadow the always-available
numpy/scipy core; the core keeps working when neither library is present.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager

import numpy as np

from backend_safe import signed01

# ★The _safe fallback is a LAST RESORT and it can MASK A DEAD OP. For
# out_sort=="image" `backend_safe.fallback` returns the clipped INPUT, so a
# wrapper whose library call raises on every input looks to evolution / difftest
# / coverage like a working identity op instead of a failure — and the swallow is
# unconditional (bare Exception), so API drift in skimage/cv2 is invisible.
# Runtime robustness is kept, but the degradation is now DETECTABLE two ways:
# every swallowed exception is recorded, and strict mode re-raises instead.
_ERR_LOCK = threading.Lock()
_ERRORS: list[dict] = []          # bounded ring, most recent last
_ERR_MAX = 64
_STRICT = os.environ.get("IMGEVOLVE_STRICT_BACKENDS", "") not in ("", "0", "false", "False")


def is_strict() -> bool:
    """True when wrapped ops re-raise instead of degrading to a fallback."""
    return _STRICT


def set_strict(on: bool = True) -> bool:
    """Turn strict mode on/off; returns the PREVIOUS value so callers can restore it."""
    global _STRICT
    prev, _STRICT = _STRICT, bool(on)
    return prev


@contextmanager
def strict_mode(on: bool = True):
    """Scoped strict mode — a verifier wraps a probe call in this to tell a dead op
    (raises) from an op that genuinely returns its input (does not)."""
    prev = set_strict(on)
    try:
        yield
    finally:
        set_strict(prev)


def swallowed_errors() -> list[dict]:
    """Copy of the recorded swallowed-exception ring (oldest first, max `_ERR_MAX`)."""
    with _ERR_LOCK:
        return [dict(e) for e in _ERRORS]


def last_error():
    """The most recently swallowed wrapper exception as a dict, or None."""
    with _ERR_LOCK:
        return dict(_ERRORS[-1]) if _ERRORS else None


def clear_errors() -> None:
    """Drop the recorded swallowed exceptions (call before a probe run)."""
    with _ERR_LOCK:
        _ERRORS.clear()


def _record_error(fn, exc, out_sort) -> None:
    with _ERR_LOCK:
        _ERRORS.append({"fn": getattr(fn, "__qualname__", repr(fn)), "out_sort": out_sort,
                        "error": "%s: %s" % (type(exc).__name__, exc)})
        del _ERRORS[:-_ERR_MAX]


def _safe(fn, out_sort=None):
    """Wrap `fn` so a library failure degrades to a sort-valid fallback.

    HONEST CAVEAT: that fallback is a last resort — for out_sort=="image" it is
    the clipped input, i.e. a permanently broken wrapper is indistinguishable
    from a working identity op. Use `strict_mode()` (or IMGEVOLVE_STRICT_BACKENDS=1)
    to make failures RAISE, and `last_error()`/`swallowed_errors()` to see what the
    non-strict path swallowed.
    """
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception as e:
            if _STRICT:
                raise
            _record_error(fn, e, out_sort)
            out = None
        return sanitize(out, v, out_sort)
    return w


def _u8(v):
    return (np.clip(v, 0, 1) * 255).astype(np.uint8)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    ops_out = []

    # ---- scikit-image -------------------------------------------------------- #
    try:
        from skimage import (filters, morphology, restoration, exposure, feature,
                             measure, segmentation, transform)

        def _disk(a):
            return morphology.disk(1 + int(a * 3))

        def _u8s(v):
            return (np.clip(v, 0, 1) * 255).astype(np.uint8)

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
            ("sk_butterworth", "frequency", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(filters.butterworth(v, cutoff_frequency_ratio=0.05 + 0.3 * a), 0, 1)),
            ("sk_tv", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: restoration.denoise_tv_chambolle(v, weight=0.02 + 0.3 * a)),
            ("sk_wavelet", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(restoration.denoise_wavelet(v), 0, 1)),
            ("sk_adapthist", "gray", "", IMAGE, IMAGE,
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
             lambda v, a, b: morphology.medial_axis(binm(v), rng=0).astype(np.float64)),
            ("sk_convex", "region", "shape_trans", REGION, REGION,
             lambda v, a, b: morphology.convex_hull_image(binm(v)).astype(np.float64)),
            ("sk_thin", "region", "thinning", REGION, REGION,
             lambda v, a, b: morphology.thin(binm(v)).astype(np.float64)),
            ("sk_remove_holes", "region", "fill_up", REGION, REGION,
             lambda v, a, b: morphology.remove_small_holes(binm(v), area_threshold=int(8 + a * 60)).astype(np.float64)),
            ("sk_euler", "features", "euler_number", REGION, FEATURE,
             lambda v, a, b: np.float64(measure.euler_number(binm(v)))),
            ("sk_find_contours", "contour", "", IMAGE, CONTOUR,
             lambda v, a, b: {"shape": v.shape,
                              "cs": [c for c in measure.find_contours(v, 0.2 + 0.5 * a) if len(c) >= 3]}),
            # more image->image
            ("sk_lbp", "texture", "", IMAGE, IMAGE,
             lambda v, a, b: norm(feature.local_binary_pattern(v, 8, 1 + int(a * 3)))),
            ("sk_entropy", "texture", "entropy_image", IMAGE, IMAGE,
             lambda v, a, b: norm(filters.rank.entropy(_u8s(v), _disk(a)).astype(np.float64))),
            ("sk_enhance_contrast", "gray", "", IMAGE, IMAGE,
             lambda v, a, b: filters.rank.enhance_contrast(_u8s(v), _disk(a)).astype(np.float64) / 255),
            ("sk_autolevel", "gray", "scale_image_max", IMAGE, IMAGE,
             lambda v, a, b: filters.rank.autolevel(_u8s(v), _disk(a)).astype(np.float64) / 255),
            ("sk_shape_index", "texture", "", IMAGE, IMAGE,
             lambda v, a, b: signed01(np.nan_to_num(feature.shape_index(v, sigma=0.5 + 2.0 * a)))),
            ("sk_hessian_det", "edges", "", IMAGE, IMAGE,
             lambda v, a, b: signed01(feature.hessian_matrix_det(v, sigma=0.5 + 2.5 * a))),
            ("sk_corner_harris", "edges", "points_harris", IMAGE, IMAGE,
             lambda v, a, b: signed01(feature.corner_harris(v, sigma=0.5 + 2.0 * a))),
            ("sk_adjust_log", "gray", "log_image", IMAGE, IMAGE,
             lambda v, a, b: exposure.adjust_log(np.clip(v, 0, 1), gain=0.5 + 1.5 * a)),
            ("sk_rolling_ball", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(v - restoration.rolling_ball(v, radius=5 + int(a * 20)), 0, 1)),
            ("sk_nlm", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: restoration.denoise_nl_means(v, patch_size=5, h=0.02 + 0.2 * a)),
            ("sk_tv_bregman", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(restoration.denoise_tv_bregman(v, weight=1.0 + 8.0 * a), 0, 1)),
            ("sk_swirl", "geometry", "polar_trans_image", IMAGE, IMAGE,
             lambda v, a, b: np.clip(transform.swirl(v, strength=1 + 4 * a, radius=30), 0, 1)),
            ("sk_area_opening", "morphology", "", IMAGE, IMAGE,
             lambda v, a, b: morphology.area_opening(v, area_threshold=int(16 + a * 100))),
            # image->region
            ("sk_felzenszwalb", "segmentation", "", IMAGE, REGION,
             lambda v, a, b: segmentation.find_boundaries(
                 segmentation.felzenszwalb(v, scale=20 + 200 * a, channel_axis=None)).astype(np.float64)),
            ("sk_slic", "segmentation", "", IMAGE, REGION,
             lambda v, a, b: segmentation.find_boundaries(
                 segmentation.slic(v, n_segments=int(10 + 80 * a), channel_axis=None)).astype(np.float64)),
            ("sk_chan_vese", "segmentation", "", IMAGE, REGION,
             lambda v, a, b: segmentation.chan_vese(v, mu=0.1 + 0.4 * a, max_num_iter=60).astype(np.float64)),
            ("sk_local_maxima", "segmentation", "local_max", IMAGE, REGION,
             lambda v, a, b: morphology.local_maxima(v).astype(np.float64)),
            ("sk_hysteresis", "segmentation", "hysteresis_threshold", IMAGE, REGION,
             lambda v, a, b: filters.apply_hysteresis_threshold(v, 0.2 + 0.3 * a, 0.5 + 0.3 * b).astype(np.float64)),
            # region->region / feature
            ("sk_clear_border", "region", "", REGION, REGION,
             lambda v, a, b: segmentation.clear_border(binm(v)).astype(np.float64)),
            ("sk_find_boundaries", "region", "boundary", REGION, REGION,
             lambda v, a, b: segmentation.find_boundaries(binm(v)).astype(np.float64)),
            ("sk_entropy_feat", "features", "entropy_gray", IMAGE, FEATURE,
             lambda v, a, b: np.float64(measure.shannon_entropy(v))),
            ("sk_blur_effect", "features", "", IMAGE, FEATURE,
             lambda v, a, b: np.float64(measure.blur_effect(v))),
        ]
        ops_out += [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in sk]
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
            ("cv_clahe", "gray", "", IMAGE, IMAGE,
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
            # more image->image
            ("cv_corner_harris", "edges", "points_harris", IMAGE, IMAGE,
             lambda v, a, b: signed01(cv2.cornerHarris(v.astype(np.float32), 2, 3, 0.04))),
            ("cv_min_eigen", "edges", "points_harris", IMAGE, IMAGE,
             lambda v, a, b: norm(cv2.cornerMinEigenVal(v.astype(np.float32), 3 + 2 * int(a * 2)))),
            ("cv_precorner", "edges", "corner_response", IMAGE, IMAGE,
             lambda v, a, b: norm(np.abs(cv2.preCornerDetect(v.astype(np.float32), 3)))),
            ("cv_nlmeans", "smoothing", "", IMAGE, IMAGE,
             lambda v, a, b: cv2.fastNlMeansDenoising(_u8(v), None, 3 + 20 * a, 7, 21).astype(np.float64) / 255),
            ("cv_blackhat", "morphology", "gray_bothat", IMAGE, IMAGE,
             lambda v, a, b: norm(cv2.morphologyEx(v, cv2.MORPH_BLACKHAT, _se(a)))),
            ("cv_erode", "morphology", "gray_erosion", IMAGE, IMAGE,
             lambda v, a, b: cv2.erode(v, _se(a))),
            ("cv_dilate", "morphology", "gray_dilation", IMAGE, IMAGE,
             lambda v, a, b: cv2.dilate(v, _se(a))),
            ("cv_sharpen", "smoothing", "emphasize", IMAGE, IMAGE,
             lambda v, a, b: np.clip(cv2.filter2D(
                 v, -1, np.array([[0, -a, 0], [-a, 1 + 4 * a, -a], [0, -a, 0]])), 0, 1)),
            ("cv_trunc", "gray", "scale_image", IMAGE, IMAGE,
             lambda v, a, b: cv2.threshold(v, a, 1.0, cv2.THRESH_TRUNC)[1]),
            # region->image / feature
            ("cv_dist", "region", "distance_transform", REGION, IMAGE,
             lambda v, a, b: norm(cv2.distanceTransform(_u8(binm(v).astype(np.float64)), cv2.DIST_L2, 3))),
            ("cv_cc_count", "features", "connection", REGION, FEATURE,
             lambda v, a, b: np.float64(cv2.connectedComponents(_u8(binm(v).astype(np.float64)))[0] - 1)),
            # image->feature (Hough / features)
            ("cv_hough_lines", "features", "hough_lines", IMAGE, FEATURE,
             lambda v, a, b: np.float64(0 if (ll := cv2.HoughLinesP(
                 cv2.Canny(_u8(v), 50, 150), 1, np.pi / 180, int(20 + 40 * a),
                 minLineLength=int(10 + 20 * b), maxLineGap=5)) is None else len(ll))),
            ("cv_hough_circles", "features", "hough_circles", IMAGE, FEATURE,
             lambda v, a, b: np.float64(0 if (cc := cv2.HoughCircles(
                 _u8(v), cv2.HOUGH_GRADIENT, 1, 10 + int(a * 20), param1=100, param2=20 + int(b * 20),
                 minRadius=3, maxRadius=20)) is None else cc.shape[1])),
            ("cv_good_features", "features", "", IMAGE, FEATURE,
             lambda v, a, b: np.float64(0 if (pp := cv2.goodFeaturesToTrack(
                 v.astype(np.float32), int(10 + 40 * a), 0.01 + 0.1 * b, 5)) is None else len(pp))),
        ]
        ops_out += [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in cv]
    except Exception:
        pass

    return ops_out
