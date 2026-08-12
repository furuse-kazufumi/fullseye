"""Shared safety net for library-backed operators.

Every backend wraps its op functions with an exception guard. The old fallback
was `return v` (the input), which had two defects the 2026-08-12 audit found:

  * it does NOT strip NaN/Inf that libraries emit on degenerate inputs (e.g.
    scipy.signal.wiener / skimage.denoise_wavelet / SimpleITK.LaplacianSharpening
    on a constant image) — np.clip does not remove NaN, so the whole pipeline
    score becomes NaN;
  * it returns the *input* even when the declared out_sort is region / feature /
    contour, so a failed segmentation returns a continuous grayscale image where
    a binary region is required (a type-contract violation).

`sanitize` centralises a finite-safe, sort-aware fallback: a failed or non-finite
op degrades to a valid, benign value of the DECLARED sort, derived from the input.
"""
from __future__ import annotations

import numpy as np


def _as_arr(v):
    return v if isinstance(v, np.ndarray) else None


def fallback(v, out_sort):
    """A valid, benign value of `out_sort`, derived from the input `v`."""
    vv = _as_arr(v)
    if out_sort == "feature":
        return np.float64(0.0)
    if out_sort == "contour":
        shape = tuple(vv.shape[:2]) if vv is not None and vv.ndim >= 2 else (1, 1)
        return {"shape": shape, "cs": []}
    if out_sort == "region":
        return np.zeros(vv.shape[:2], np.float64) if vv is not None and vv.ndim >= 2 else np.zeros((1, 1))
    if out_sort == "color":
        if vv is not None and vv.ndim == 3 and vv.shape[-1] == 3:
            return np.clip(vv, 0, 1)
        if vv is not None and vv.ndim == 2:
            return np.clip(np.stack([vv] * 3, -1), 0, 1)
        return np.zeros((1, 1, 3))
    if out_sort == "match":
        return np.array([0.0, 0.0, 0.0])
    # image / volume / any / unknown -> the clipped input if it is an array
    return np.clip(vv, 0, 1) if vv is not None else v


def sanitize(out, v, out_sort=None):
    """Return a finite, sort-valid result.

    * out is None (op raised)                 -> sort fallback
    * out is a float/complex array w/ NaN/Inf -> keep finite pixels, patch the
      rest from the sort fallback (or nan_to_num when shapes differ)
    * complex output for a real sort          -> take the real part
    otherwise the op's own output is returned unchanged.
    """
    if out is None:
        return fallback(v, out_sort)
    if isinstance(out, np.ndarray) and out.size and out.dtype.kind in "fc":
        real = out.real if out.dtype.kind == "c" else out
        if np.all(np.isfinite(real)):
            return real if out.dtype.kind == "c" else out
        fb = fallback(v, out_sort)
        if isinstance(fb, np.ndarray) and fb.shape == real.shape:
            return np.where(np.isfinite(real), real, fb)
        return np.nan_to_num(real, nan=0.0, posinf=1.0, neginf=0.0)
    return out
