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


def signed01(x):
    """Map a SIGNED filter response to [0,1] with the zero-crossing at 0.5.

    Signed responses (Harris R, Laplacian-of-Gaussian, morphological Laplace,
    high/band-pass, phase) carry information in their sign. `_norm(x)=x/max|x|`
    yields [-1,1]; the pipeline's [0,1] clip then discards the entire negative
    half. This preserves it: 0 -> 0.5, ±max -> 0/1.
    """
    x = np.asarray(x, np.float64)
    m = float(np.max(np.abs(x))) if x.size else 0.0
    return np.clip(x / (2 * m) + 0.5, 0, 1) if m > 1e-8 else np.full_like(x, 0.5)


def subpixel_refine_edges(pts, mag, ny, nx):
    """Move edge points onto the gradient-magnitude ridge with sub-pixel accuracy.

    勾配の**法線方向**に 1 px 離れた 3 点 (p-n, p, p+n) の勾配強度に放物線を当て、
    その頂点まで点をずらす(古典的なサブピクセル・エッジ位置決め。Devernay 1995 /
    HALCON ``edges_sub_pix`` と同じ考え方)。オフセットは ±1 px に制限する
    (3 点補間の外挿は当てにならない)。

    引数はすべて (row, col) 規約: ``pts`` (N,2)、``mag`` 勾配強度画像、
    ``ny``/``nx`` 単位勾配ベクトルの行/列成分(``mag`` と同 shape)。

    ★``ops._edges_sub_pix`` と ``backends_auto._sh_xld(kind="edges_sub_pix")`` の
    **両方**がこれを使う。以前は 2 つが別々に「``np.where`` の整数座標をそのまま
    返す」実装を持っており(レジストリは同名の **後勝ち** なので実際に走るのは
    backends_auto 側)、``sub_pix`` を名乗りながら画素精度しか無かった。
    """
    from scipy import ndimage as _nd

    pts = np.asarray(pts, np.float64)
    if pts.size == 0:
        return pts
    r, c = pts[:, 0], pts[:, 1]
    ri = np.clip(r.astype(int), 0, mag.shape[0] - 1)
    ci = np.clip(c.astype(int), 0, mag.shape[1] - 1)
    nyv, nxv = ny[ri, ci], nx[ri, ci]

    def _s(rr, cc):
        return _nd.map_coordinates(mag, [rr, cc], order=1, mode="nearest")

    m0, mm, mp = _s(r, c), _s(r - nyv, c - nxv), _s(r + nyv, c + nxv)
    den = mm - 2.0 * m0 + mp
    ok = np.abs(den) > 1e-12
    t = np.zeros_like(m0)
    t[ok] = 0.5 * (mm[ok] - mp[ok]) / den[ok]
    t = np.clip(np.nan_to_num(t), -1.0, 1.0)
    out = np.stack([r + t * nyv, c + t * nxv], 1)
    return np.where(np.isfinite(out), out, pts)


def gradient_normals(x):
    """Sobel gradient magnitude and the UNIT gradient (= edge normal), (mag, ny, nx)."""
    from scipy import ndimage as _nd

    x = np.asarray(x, np.float64)
    gy, gx = _nd.sobel(x, 0), _nd.sobel(x, 1)
    g = np.hypot(gx, gy)
    gs = np.where(g < 1e-12, 1e-12, g)
    return g, gy / gs, gx / gs


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


def region01(out):
    """Coerce a `region` result to the declared {0,1} contract.

    ★`sanitize` guaranteed FINITENESS but never RANGE: on the success path a
    finite float region whose values fell outside {0,1} — or an int/bool one —
    was returned untouched, so the "sort-valid" half of its promise held only by
    convention.  Every current region producer `astype`s from a bool mask, so
    this is an identity for all of them; it closes the contract for any future
    producer (a label map, a soft mask) that is not already binary.

    Out-of-range values are binarised at 0.5, the same rule `api._coerce_input`
    applies on the INPUT side.  Non-array / non-numeric outputs are left alone:
    a region op returning those is a sort bug, not a range one.
    """
    if not isinstance(out, np.ndarray) or not out.size or out.dtype.kind not in "biufc":
        return out
    r = out.real if out.dtype.kind == "c" else out
    if out.dtype.kind == "f" and np.all((r == 0) | (r == 1)):
        return out                              # already {0,1} float -> unchanged
    return (r > 0.5).astype(np.float64)


def sanitize(out, v, out_sort=None):
    """Return a finite, sort-valid result.

    Finiteness is handled by `_finite`; for out_sort=="region" the result is
    additionally forced onto the {0,1} contract by `region01`.
    """
    out = _finite(out, v, out_sort)
    return region01(out) if out_sort == "region" else out


def _finite(out, v, out_sort=None):
    """Return a finite result of the declared sort.

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
    # ★A feature op returns a numpy SCALAR, not an ndarray, so the branch above
    # never saw it: a NaN/Inf measurement (e.g. a 0/0 inside sk_blur_effect on a
    # degenerate frame) used to flow straight out of api.apply.  Scrub non-finite
    # scalars to the sort fallback so the declared "finite, sort-valid" guarantee
    # actually holds for feature/contour scalars too.
    if isinstance(out, (float, int, np.floating, np.integer, np.complexfloating, complex)):
        if not np.isfinite(float(np.real(out))):
            return fallback(v, out_sort)
    return out
