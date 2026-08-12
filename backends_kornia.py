"""Kornia incorporation — GPU-native (torch) differentiable image operators.

Kornia runs on torch tensors, so these operators execute on the GPU when a CUDA
device is available (set IMGEVOLVE_KORNIA_DEVICE=cuda on the RTX 5090). They add
distinctive detectors/filters (Harris/GFTT/Hessian/DoG responses, motion &
bilateral blur, CLAHE) and are the torch-native path for those ops. Registry use
is per-image; honest note: on CPU this is not faster than scipy — the speed is on
GPU / in batch. Exception-safe; `xkor_` prefix; halcon="".
"""
from __future__ import annotations

import os

import numpy as np

from backend_safe import signed01

try:
    import torch
    import kornia
    import kornia.filters as KF
    import kornia.feature as KFEAT
    import kornia.enhance as KE
    _HAS = True
    _DEV = os.environ.get("IMGEVOLVE_KORNIA_DEVICE", "cpu")
    if _DEV == "cuda" and not torch.cuda.is_available():
        _DEV = "cpu"
except Exception:  # pragma: no cover
    _HAS = False


def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:
            out = None
        return sanitize(out, v, out_sort)
    return w


def _t(v):
    x = np.clip(np.asarray(v, np.float64), 0, 1).astype(np.float32)
    return torch.as_tensor(x, device=_DEV)[None, None]


def _np(t):
    return t.detach().cpu().numpy()[0, 0].astype(np.float64)


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


def _k(a):
    return (3, 5, 7, 9)[min(3, int(a * 4))]


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    if not _HAS:
        return []

    def _gauss(v, a, b):
        s = 0.3 + 2.7 * a
        return _np(KF.gaussian_blur2d(_t(v), (5, 5), (s, s)))

    def _bilateral(v, a, b):
        return np.clip(_np(KF.bilateral_blur(_t(v), (5, 5), 0.05 + 0.4 * b, (1.0 + 3.0 * a,) * 2)), 0, 1)

    def _median(v, a, b):
        k = _k(a)
        return _np(KF.median_blur(_t(v), (k, k)))

    def _unsharp(v, a, b):
        s = 0.5 + 2.0 * b
        return np.clip(_np(KF.unsharp_mask(_t(v), (5, 5), (s, s))), 0, 1)

    def _motion(v, a, b):
        ks = 2 * int(2 + a * 6) + 1
        return _np(KF.motion_blur(_t(v), ks, float(360 * a), float(2 * b - 1)))

    def _canny(v, a, b):
        low = 0.1 + 0.3 * a
        _, edges = KF.canny(_t(v), low_threshold=low, high_threshold=max(low + 1e-3, 0.3 + 0.4 * b))
        return _np(edges)

    def _clahe(v, a, b):
        return np.clip(_np(KE.equalize_clahe(_t(v), clip_limit=1.0 + 4.0 * a)), 0, 1)

    def _laplacian(v, a, b):
        return _norm(np.abs(_np(KF.laplacian(_t(v), _k(a)))))

    def _resp(fn):
        return lambda v, a, b: _norm(np.abs(_np(fn(_t(v)))))

    defs = [
        ("xkor_gaussian", "smoothing", IMAGE, IMAGE, _gauss),
        ("xkor_bilateral", "smoothing", IMAGE, IMAGE, _bilateral),
        ("xkor_median", "rank", IMAGE, IMAGE, _median),
        ("xkor_unsharp", "smoothing", IMAGE, IMAGE, _unsharp),
        ("xkor_motion_blur", "smoothing", IMAGE, IMAGE, _motion),
        ("xkor_canny", "segmentation", IMAGE, REGION, _canny),
        ("xkor_clahe", "gray", IMAGE, IMAGE, _clahe),
        ("xkor_laplacian", "edges", IMAGE, IMAGE, _laplacian),
        ("xkor_harris", "edges", IMAGE, IMAGE,
         lambda v, a, b: signed01(_np(KFEAT.harris_response(_t(v), k=0.04 + 0.02 * a)))),
    ]
    for name, attr in (("xkor_gftt", "gftt_response"), ("xkor_hessian", "hessian_response"),
                       ("xkor_dog", "dog_response_single"), ("xkor_dog", "dog_response")):
        fn = getattr(KFEAT, attr, None)
        if fn is not None and name not in {d[0] for d in defs}:
            defs.append((name, "edges", IMAGE, IMAGE, _resp(fn)))
    return [Op(n, c, "", i, o, _safe(f, o)) for (n, c, i, o, f) in defs]
