"""Cross-library incorporation — distinctive operators HALCON doesn't emphasise.

imgevolve started HALCON-centric; this module widens it to genuine features from
the broader ecosystem (scikit-image, OpenCV) that have no clean HALCON analogue —
inpainting, blob detectors, keypoint counts, graph/random-walker segmentation,
flood fill, structure/Hessian tensors, and OpenCV's photo/NPR filters (stylization,
pencil sketch, edge-preserving, detail enhance, grabCut, marker watershed).

Same contract as backends.py: `build()` returns typed Op wrappers the registry
appends; every wrapper is exception-safe (degrades to identity) and returns values
in the pipeline's conventions. Names are prefixed `xsk_` / `xcv_` so they never
shadow the core or the existing sk_/cv_ ops. `Op.halcon` is left empty when there
is no faithful HALCON name — these lift *other-library* coverage, not HALCON's.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:
            out = None
        return sanitize(out, v, out_sort)
    return w


def _u8(v):
    return (np.clip(np.asarray(v, np.float64), 0, 1) * 255).astype(np.uint8)


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    out = []

    # ---- scikit-image distinctive ------------------------------------------ #
    try:
        from skimage import restoration, feature, segmentation, filters

        def _inpaint(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            mask = (x > 0.92) | (x < 0.08)
            if not mask.any():
                return x
            return restoration.inpaint_biharmonic(x, mask)

        def _blob(kind):
            def fn(v, a, b):
                x = np.clip(np.asarray(v, np.float64), 0, 1)
                f = {"log": feature.blob_log, "dog": feature.blob_dog, "doh": feature.blob_doh}[kind]
                bl = f(x, max_sigma=5 + 20 * a, threshold=0.02 + 0.15 * b)
                return np.float64(len(bl))
            return fn

        def _orb_count(v, a, b):
            orb = feature.ORB(n_keypoints=int(50 + 400 * a))
            orb.detect_and_extract(np.clip(np.asarray(v, np.float64), 0, 1))
            return np.float64(len(orb.keypoints))

        def _random_walker(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            markers = np.zeros(x.shape, np.int32)
            markers[x < (0.3 + 0.2 * a)] = 1
            markers[x > (0.7 - 0.2 * a)] = 2
            lab = segmentation.random_walker(x, markers, beta=10 + 200 * b)
            return segmentation.find_boundaries(lab).astype(np.float64)

        def _flood(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            c = (x.shape[0] // 2, x.shape[1] // 2)
            return segmentation.flood(x, c, tolerance=0.05 + 0.3 * a).astype(np.float64)

        def _struct_coh(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            axx, axy, ayy = feature.structure_tensor(x, sigma=0.5 + 2 * a, order="rc")
            l1, l2 = feature.structure_tensor_eigenvalues([axx, axy, ayy])
            return _norm(np.nan_to_num((l1 - l2) / (l1 + l2 + 1e-8)))

        def _hessian_eig(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            H = feature.hessian_matrix(x, sigma=0.5 + 2.5 * a, order="rc", use_gaussian_derivatives=True)
            ev = feature.hessian_matrix_eigvals(H)
            return _norm(np.abs(ev[0]))

        sk = [
            ("xsk_inpaint", "restoration", "", IMAGE, IMAGE, _inpaint),
            ("xsk_richardson_lucy", "restoration", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(restoration.richardson_lucy(
                 np.clip(v, 0, 1), np.ones((3, 3)) / 9, num_iter=2 + int(a * 15)), 0, 1)),
            ("xsk_unwrap_phase", "restoration", "", IMAGE, IMAGE,
             lambda v, a, b: _norm(restoration.unwrap_phase(
                 (np.clip(v, 0, 1) - 0.5) * 2 * np.pi))),
            ("xsk_struct_coherence", "texture", "", IMAGE, IMAGE, _struct_coh),
            ("xsk_hessian_eig", "edges", "", IMAGE, IMAGE, _hessian_eig),
            ("xsk_random_walker", "segmentation", "", IMAGE, REGION, _random_walker),
            ("xsk_flood", "segmentation", "", IMAGE, REGION, _flood),
            ("xsk_blob_log", "features", "", IMAGE, FEATURE, _blob("log")),
            ("xsk_blob_dog", "features", "", IMAGE, FEATURE, _blob("dog")),
            ("xsk_blob_doh", "features", "", IMAGE, FEATURE, _blob("doh")),
            ("xsk_orb_count", "features", "", IMAGE, FEATURE, _orb_count),
            ("xsk_meijering", "texture", "", IMAGE, IMAGE,
             lambda v, a, b: _norm(filters.meijering(np.clip(v, 0, 1), sigmas=range(1, 4)))),
            ("xsk_sato", "texture", "", IMAGE, IMAGE,
             lambda v, a, b: _norm(filters.sato(np.clip(v, 0, 1), sigmas=range(1, 4)))),
        ]
        out += [Op(n, c, h, i, o, _safe(f)) for (n, c, h, i, o, f) in sk]
    except Exception:
        pass

    # ---- OpenCV photo / NPR / segmentation --------------------------------- #
    try:
        import cv2

        def _to3(v):
            return cv2.cvtColor(_u8(v), cv2.COLOR_GRAY2BGR)

        def _gray(im):
            return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float64) / 255

        def _stylize(v, a, b):
            return _gray(cv2.stylization(_to3(v), sigma_s=20 + 100 * a, sigma_r=0.1 + 0.4 * b))

        def _pencil(v, a, b):
            g, _ = cv2.pencilSketch(_to3(v), sigma_s=20 + 80 * a, sigma_r=0.05 + 0.15 * b,
                                    shade_factor=0.02 + 0.06 * b)
            return g.astype(np.float64) / 255

        def _edge_preserve(v, a, b):
            return _gray(cv2.edgePreservingFilter(_to3(v), flags=1, sigma_s=20 + 100 * a,
                                                  sigma_r=0.1 + 0.5 * b))

        def _detail(v, a, b):
            return _gray(cv2.detailEnhance(_to3(v), sigma_s=10 + 40 * a, sigma_r=0.1 + 0.3 * b))

        def _inpaint_cv(v, a, b):
            x = _u8(v)
            mask = (((x > 235) | (x < 20)) * 255).astype(np.uint8)
            return cv2.inpaint(x, mask, 3, cv2.INPAINT_TELEA).astype(np.float64) / 255

        def _grabcut(v, a, b):
            img = _to3(v)
            h, w = img.shape[:2]
            mask = np.zeros((h, w), np.uint8)
            rect = (int(w * 0.15), int(h * 0.15), int(w * 0.7), int(h * 0.7))
            bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
            cv2.grabCut(img, mask, rect, bg, fg, 2 + int(a * 3), cv2.GC_INIT_WITH_RECT)
            return ((mask == 1) | (mask == 3)).astype(np.float64)

        def _watershed_markers(v, a, b):
            img = _to3(v)
            x = _u8(v)
            _, thr = cv2.threshold(x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            sure_bg = cv2.dilate(thr, np.ones((3, 3), np.uint8), iterations=3)
            dist = cv2.distanceTransform(thr, cv2.DIST_L2, 5)
            _, sure_fg = cv2.threshold(dist, (0.3 + 0.4 * a) * dist.max(), 255, 0)
            unknown = cv2.subtract(sure_bg, sure_fg.astype(np.uint8))
            _, markers = cv2.connectedComponents(sure_fg.astype(np.uint8))
            markers = markers + 1
            markers[unknown == 255] = 0
            markers = cv2.watershed(img, markers)
            return (markers == -1).astype(np.float64)

        def _orb_cv(v, a, b):
            orb = cv2.ORB_create(nfeatures=int(50 + 450 * a))
            kp = orb.detect(_u8(v), None)
            return np.float64(len(kp))

        cv = [
            ("xcv_stylization", "artistic", "", IMAGE, IMAGE, _stylize),
            ("xcv_pencil_sketch", "artistic", "", IMAGE, IMAGE, _pencil),
            ("xcv_edge_preserving", "smoothing", "", IMAGE, IMAGE, _edge_preserve),
            ("xcv_detail_enhance", "gray", "", IMAGE, IMAGE, _detail),
            ("xcv_inpaint", "restoration", "", IMAGE, IMAGE, _inpaint_cv),
            ("xcv_grabcut", "segmentation", "", IMAGE, REGION, _grabcut),
            ("xcv_watershed_markers", "segmentation", "watersheds", IMAGE, REGION, _watershed_markers),
            ("xcv_orb_count", "features", "", IMAGE, FEATURE, _orb_cv),
        ]
        out += [Op(n, c, h, i, o, _safe(f)) for (n, c, h, i, o, f) in cv]
    except Exception:
        pass

    return out
