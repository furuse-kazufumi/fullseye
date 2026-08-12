"""SciPy signal/fft incorporation — filters beyond ndimage.

scipy.signal and scipy.fft carry operators the ndimage-based core does not:
the adaptive Wiener filter, the 2-D discrete cosine transform, Savitzky-Golay
smoothing, and Gaussian gradient magnitude. `build()` wraps the distinctive,
single-gray-image ones; exception-safe, output in [0,1]. Prefixed `xsp_`.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _safe(fn):
    def w(v, a, b):
        try:
            out = fn(v, a, b)
            return out if out is not None else v
        except Exception:
            return v
    return w


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    out = []
    try:
        from scipy import signal

        def _wiener(v, a, b):
            k = 3 + 2 * int(a * 3)
            return np.clip(signal.wiener(np.clip(v, 0, 1), (k, k)), 0, 1)

        def _savgol(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            w = 5 + 2 * int(a * 4)
            y = signal.savgol_filter(x, w, 2, axis=1)
            return np.clip(signal.savgol_filter(y, w, 2, axis=0), 0, 1)

        def _hilbert_env(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1) - 0.5
            return _norm(np.abs(signal.hilbert(x, axis=1)))

        out += [Op(n, c, "", i, o, _safe(f)) for (n, c, i, o, f) in [
            ("xsp_wiener", "smoothing", IMAGE, IMAGE, _wiener),
            ("xsp_savgol", "smoothing", IMAGE, IMAGE, _savgol),
            ("xsp_hilbert_env", "texture", IMAGE, IMAGE, _hilbert_env),
        ]]
    except Exception:
        pass

    try:
        from scipy import fft as sfft

        def _dct(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            return _norm(np.log1p(np.abs(sfft.dctn(x, norm="ortho"))))

        def _dct_lowpass(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            C = sfft.dctn(x, norm="ortho")
            keep = max(2, int((0.15 + 0.6 * a) * min(x.shape)))
            M = np.zeros_like(C)
            M[:keep, :keep] = C[:keep, :keep]
            return np.clip(sfft.idctn(M, norm="ortho"), 0, 1)

        def _dct_denoise(v, a, b):
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            C = sfft.dctn(x, norm="ortho")
            thr = (0.01 + 0.2 * a) * np.abs(C).max()
            return np.clip(sfft.idctn(np.where(np.abs(C) > thr, C, 0.0), norm="ortho"), 0, 1)

        out += [Op("xsp_dct", "frequency", "", IMAGE, IMAGE, _safe(_dct)),
                Op("xsp_dct_lowpass", "frequency", "", IMAGE, IMAGE, _safe(_dct_lowpass)),
                Op("xsp_dct_denoise", "smoothing", "", IMAGE, IMAGE, _safe(_dct_denoise))]
    except Exception:
        pass

    # scipy.signal spline / detrend + ndimage morphological laplace / chamfer distance
    try:
        from scipy import signal as _sig

        out += [
            Op("xsp_cspline_smooth", "smoothing", "", IMAGE, IMAGE, _safe(
                lambda v, a, b: np.clip(_sig.cspline2d(np.clip(np.asarray(v, np.float64), 0, 1),
                                                       1.0 + 40.0 * a), 0, 1))),
            Op("xsp_detrend_flatten", "gray", "", IMAGE, IMAGE, _safe(
                lambda v, a, b: _norm(_sig.detrend(_sig.detrend(
                    np.clip(np.asarray(v, np.float64), 0, 1), axis=0), axis=1)) * 0.5 + 0.5)),
        ]
    except Exception:
        pass
    out += [
        Op("xsp_morph_laplace", "edges", "", IMAGE, IMAGE, _safe(
            lambda v, a, b: _norm(ndimage.morphological_laplace(
                np.clip(v, 0, 1), size=3 + 2 * int(a * 3))))),
        Op("xsp_chamfer_dist", "region", "", "region", IMAGE, _safe(
            lambda v, a, b: _norm(ndimage.distance_transform_cdt(np.asarray(v) > 0.5).astype(np.float64)))),
    ]

    # Gaussian gradient magnitude (ndimage, but a distinct operator vs plain sobel)
    out += [Op("xsp_gauss_grad_mag", "edges", "", IMAGE, IMAGE, _safe(
        lambda v, a, b: _norm(ndimage.gaussian_gradient_magnitude(
            np.clip(v, 0, 1), sigma=0.5 + 2.5 * a))))]
    return out
