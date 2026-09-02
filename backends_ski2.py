"""scikit-image incorporation (round 2) — distinctive functions not yet wrapped.

Mined from skimage's submodules: multi-Otsu, geometric-mean rank filter,
morphological reconstruction, h-maxima, diameter opening, isotropic closing, HOG
visualisation, Kitchen-Rosenfeld corners, the Radon transform, the inverse
Gaussian gradient, and Wiener deconvolution. `xsk2_` prefix; exception-safe;
outputs in the pipeline convention.
"""
from __future__ import annotations

import numpy as np

from backend_safe import signed01


def _safe(fn, out_sort=None):
    """Fail-soft wrapper -> the shared, RECORDING guard (backend_safe.guard).

    A failure degrades to a sort-valid fallback exactly as before, but the event
    is now written to the fallback ledger and strict mode re-raises, so a
    permanently broken op can no longer masquerade as a working identity.
    """
    from backend_safe import guard
    return guard(fn, out_sort)


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    try:
        from skimage import filters, morphology, feature, segmentation, transform, restoration
    except Exception:
        return []

    def _u8(v):
        return (np.clip(np.asarray(v, np.float64), 0, 1) * 255).astype(np.uint8)

    def _multiotsu(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        # クラス数は 3..4。**5 は入れない**: skimage の多値大津は閾値の全探索で
        # コストが O(bins^(classes-1)) なので、1 段増やすだけで桁が変わる。
        # 実測 2026-09-02(128x128): a=1.0 で 5 クラス = 2.435 秒、a=0.0 の
        # 3 クラス = 0.0008 秒 —— **3239 倍**。画像サイズには依らない
        # (32/128/512 px でどれも約 1.6 秒)ので、大きさを絞っても効かない。
        # 進化ループは 1 世代で数百回 op を叩くため、この 1 op だけで実行が
        # 止まって見える。4 クラスなら 0.025 秒で、階調も十分に増える。
        cls = 3 + int(a > 0.5)                        # 3..4 classes
        th = filters.threshold_multiotsu(x, classes=cls)
        return np.digitize(x, th).astype(np.float64) / (cls - 1)

    def _reconstruction(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        seed = np.clip(x - (0.05 + 0.25 * a), 0, 1)
        return morphology.reconstruction(seed, x, method="dilation")

    def _h_maxima(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        return morphology.h_maxima(x, 0.05 + 0.3 * a).astype(np.float64)

    def _radon(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        theta = np.linspace(0.0, 180.0, max(x.shape), endpoint=False)
        sino = transform.radon(x, theta=theta)
        return _norm(transform.resize(sino, x.shape, anti_aliasing=True))

    def _wiener(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        yy, xx = np.mgrid[-2:3, -2:3]
        psf = np.exp(-(xx * xx + yy * yy) / (2 * (0.5 + 1.5 * a) ** 2))
        psf /= psf.sum()
        return np.clip(restoration.wiener(x, psf, balance=0.05 + 0.5 * b), 0, 1)

    def _hog(v, a, b):
        x = np.clip(np.asarray(v, np.float64), 0, 1)
        _, hog_img = feature.hog(x, orientations=8, pixels_per_cell=(6 + 2 * int(a * 3),) * 2,
                                 cells_per_block=(2, 2), visualize=True)
        return _norm(hog_img)

    defs = [
        ("xsk2_multiotsu", "segmentation", IMAGE, IMAGE, _multiotsu),
        ("xsk2_rank_geomean", "rank", IMAGE, IMAGE,
         lambda v, a, b: filters.rank.geometric_mean(_u8(v), morphology.disk(1 + int(a * 3))).astype(np.float64) / 255),
        ("xsk2_reconstruction", "morphology", IMAGE, IMAGE, _reconstruction),
        ("xsk2_h_maxima", "segmentation", IMAGE, REGION, _h_maxima),
        ("xsk2_diameter_opening", "morphology", IMAGE, IMAGE,
         lambda v, a, b: morphology.diameter_opening(np.clip(v, 0, 1), diameter_threshold=4 + int(a * 30))),
        ("xsk2_isotropic_close", "region", REGION, REGION,
         lambda v, a, b: morphology.isotropic_closing(binm(v), 1 + a * 4).astype(np.float64)),
        ("xsk2_hog", "texture", IMAGE, IMAGE, _hog),
        ("xsk2_corner_kr", "edges", IMAGE, IMAGE,
         lambda v, a, b: signed01(np.nan_to_num(feature.corner_kitchen_rosenfeld(np.clip(v, 0, 1))))),
        ("xsk2_radon", "frequency", IMAGE, IMAGE, _radon),
        ("xsk2_inv_gauss_grad", "edges", IMAGE, IMAGE,
         lambda v, a, b: segmentation.inverse_gaussian_gradient(np.clip(v, 0, 1), alpha=50 + 150 * a)),
        ("xsk2_wiener", "restoration", IMAGE, IMAGE, _wiener),
    ]
    return [Op(n, c, "", i, o, _safe(f, o)) for (n, c, i, o, f) in defs]
