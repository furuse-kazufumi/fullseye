"""Kornia incorporation — GPU-native (torch) differentiable image operators.

Kornia runs on torch tensors, so these operators execute on the GPU when a CUDA
device is available (set IMGEVOLVE_KORNIA_DEVICE=cuda on the RTX 5090). They add
distinctive detectors/filters (Harris/GFTT/Hessian/DoG responses, motion &
bilateral blur, guided blur, CLAHE) and are the torch-native path for those ops.
Registry use is per-image; honest note: on CPU this is not faster than scipy —
the speed is on GPU / in batch. Exception-safe; `xkor_` prefix; halcon="".
"""
from __future__ import annotations

import os

import numpy as np

try:
    import torch
    import kornia
    _HAS = True
    _DEV = os.environ.get("IMGEVOLVE_KORNIA_DEVICE", "cpu")
    if _DEV == "cuda" and not torch.cuda.is_available():
        _DEV = "cpu"
except Exception:  # pragma: no cover
    _HAS = False


def _safe(fn):
    def w(v, a, b):
        try:
            return fn(v, a, b)
        except Exception:
            return v
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
    import kornia.filters as KF
    import kornia.feature as KfeatMod
    import kornia.enhance as KE

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
        mag, edges = KF.canny(_t(v), low_threshold=0.1 + 0.3 * a, high_threshold=0.3 + 0.4 * b)
        return _np(edges)

    def _harris(v, a, b):
        return _norm(_np(KfeatMod.harris_response(_t(v), k=0.04 + 0.02 * a)))

    def _gftt(v, a, b):
        return _norm(_np(KeatSafe(KeatMod_gftt, _t(v))))

    def _hessian(v, a, b):
        return _norm(np.abs(_np(KfeatSafe(KfeatMod_hessian, _t(v)))))

    def _dog(v, a, b):
        return _norm(np.abs(_np(KfeatSafe(KfeatMod_dog, _t(v)))))

    def _clahe(v, a, b):
        return np.clip(_np(KE.equalize_clahe(_t(v), clip_limit=1.0 + 4.0 * a)), 0, 1)

    def _laplacian(v, a, b):
        return _norm(np.abs(_np(KF.laplacian(_t(v), _k(a)))))

    # some kornia feature responses are named slightly differently across versions
    KeatMod_gftt = getattr(KeatModAlias(), "gftt_response", None)
    KfeatMod_hessian = getattr(KeatModAlias(), "hessian_response", None)
    KfeatMod_dog = getattr(KeatModAlias(), "dog_response_single", None) or getattr(KeatModAlias(), "dog_response", None)

    defs = [
        ("xkor_gaussian", "smoothing", IMAGE, IMAGE, _gauss),
        ("xkor_bilateral", "smoothing", IMAGE, IMAGE, _bilateral),
        ("xkor_median", "rank", IMAGE, IMAGE, _median),
        ("xkor_unsharp", "smoothing", IMAGE, IMAGE, _unsharp),
        ("xkor_motion_blur", "smoothing", IMAGE, IMAGE, _motion),
        ("xkor_canny", "segmentation", IMAGE, REGION, _canny),
        ("xkor_harris", "edges", IMAGE, IMAGE, _harris),
        ("xkor_clahe", "gray", IMAGE, IMAGE, _clahe),
        ("xkor_laplacian", "edges", IMAGE, IMAGE, _laplacian),
    ]
    if KeatMod_gftt is not None:
        defs.append(("xkor_gftt", "edges", IMAGE, IMAGE, _gftt))
    if KfeatMod_hessian is not None:
        defs.append(("xkor_hessian", "edges", IMAGE, IMAGE, _hessian))
    if KfeatMod_dog is not None:
        defs.append(("xkor_dog", "edges", IMAGE, IMAGE, _dog))
    return [Op(n, c, "", i, o, _safe(f)) for (n, c, i, o, f) in defs]


def KeatModAlias():
    import kornia.feature as KF
    return KF


def KeatSafe(fn, t):
    return fn(t)


def KfeatSafe(fn, t):
    return fn(t)
