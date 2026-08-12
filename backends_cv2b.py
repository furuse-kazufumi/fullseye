"""OpenCV incorporation (round 2) — distinctive functions not yet wrapped.

Log-polar warp, mean-shift filtering (pyrMeanShiftFiltering), hit-or-miss
morphology, the Laplacian-variance focus measure, and a FAST keypoint count.
`xcv2_` prefix; exception-safe; pipeline-convention outputs.
"""
from __future__ import annotations

import numpy as np


def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:
            out = None
        return sanitize(out, v, out_sort)
    return w


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    try:
        import cv2
    except Exception:
        return []

    def _u8(v):
        return (np.clip(np.asarray(v, np.float64), 0, 1) * 255).astype(np.uint8)

    def _logpolar(v, a, b):
        x = np.asarray(v, np.float32)
        h, w = x.shape
        return cv2.warpPolar(x, (w, h), (w / 2, h / 2), min(h, w) / 2,
                             cv2.WARP_POLAR_LOG + cv2.INTER_LINEAR).astype(np.float64)

    def _meanshift(v, a, b):
        bgr = cv2.cvtColor(_u8(v), cv2.COLOR_GRAY2BGR)
        out = cv2.pyrMeanShiftFiltering(bgr, sp=5 + 25 * a, sr=10 + 40 * b)
        return cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).astype(np.float64) / 255

    def _hitmiss(v, a, b):
        m = (np.asarray(v) > 0.5).astype(np.uint8)
        ker = np.array([[0, 1, 0], [1, -1, 1], [0, 1, 0]], np.int8)
        return (cv2.morphologyEx(m, cv2.MORPH_HITMISS, ker) > 0).astype(np.float64)

    def _lap_var(v, a, b):
        lv = float(cv2.Laplacian(np.clip(np.asarray(v, np.float64), 0, 1), cv2.CV_64F).var())
        return np.float64(min(1.0, lv * 20))          # focus / blur measure

    def _fast_count(v, a, b):
        fast = cv2.FastFeatureDetector_create(threshold=int(5 + 40 * a))
        return np.float64(len(fast.detect(_u8(v), None)))

    defs = [
        ("xcv2_warp_logpolar", "geometry", "", IMAGE, IMAGE, _logpolar),
        ("xcv2_meanshift", "segmentation", "", IMAGE, IMAGE, _meanshift),
        ("xcv2_hitmiss", "region", "", REGION, REGION, _hitmiss),
        ("xcv2_lap_var", "features", "", IMAGE, FEATURE, _lap_var),
        ("xcv2_fast_count", "features", "", IMAGE, FEATURE, _fast_count),
    ]
    return [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in defs]
