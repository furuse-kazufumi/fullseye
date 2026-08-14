"""Inverse-problem image operators (registry cluster ``inverse`` / ``iv_``).

Every operator here is a self-contained, genuine image-restoration algorithm that
takes a degraded image and estimates a sharper one. They are NEW capabilities with
no single MVTec HALCON analog, so every ``Op.halcon`` field is ``""`` (no coverage
claim is made): HALCON has no ``richardson_lucy`` / ``wiener_deconv`` / motion
deblur / back-projection super-resolution / harmonic-inpaint operator, and the
frequency-domain Wiener variant already living in ``complexops`` (``cx_wiener_*``)
is a different, kernel-supplied op — the ``iv_wiener_deconv_spatial`` here assumes
its own small Gaussian PSF and keeps a distinct name.

  iv_richardson_lucy        Richardson-Lucy deconvolution of an assumed small
                            Gaussian PSF (a = iteration count).
  iv_wiener_deconv_spatial  Regularized (parametric Wiener) inverse of an assumed
                            small Gaussian PSF; a = assumed blur, b = noise ratio.
  iv_unsharp_deblur         Iterative unsharp-mask sharpening (approximate deblur);
                            a = iteration count, b = amount.
  iv_motion_deblur          Wiener deconvolution of an assumed linear motion blur
                            (a = length, b = angle).
  iv_backproject_superres   Single-image iterative back-projection super-resolution
                            (upscale -> blur-down -> residual -> back-project ->
                            downscale to HxW); a = iterations, b = step gain.
  iv_gradient_inpaint       Harmonic (Laplace) inpainting of a central masked
                            window sized by a (Jacobi relaxation of nabla^2 u = 0).

Contract: ``fn(v, a, b)`` takes a 2-D float64 image in [0,1] plus two evolution
knobs a,b in [0,1] and returns a 2-D float64 image in [0,1]. Deterministic, finite,
HxW-preserving, and fail-soft (never raises on odd input).

References:
* W. H. Richardson, "Bayesian-Based Iterative Method of Image Restoration",
  JOSA 62(1), 1972; L. B. Lucy, AJ 79, 1974.
* N. Wiener, "Extrapolation, Interpolation, and Smoothing of Stationary Time
  Series", 1949; Gonzalez & Woods, "Digital Image Processing" (parametric Wiener).
* M. Irani & S. Peleg, "Improving Resolution by Image Registration", CVGIP 1991
  (iterative back-projection).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

# Assumed point-spread widths / defaults (small, as the ops advertise). Exposed as
# module constants so ground-truth tests can degrade an image with the SAME model
# the op inverts.
RL_SIGMA = 1.2          # assumed Gaussian PSF sigma for Richardson-Lucy
WIENER_SIGMA_MAX = 2.0  # a scales the assumed Gaussian blur to invert (Wiener)
_EPS = 1e-6


def _safe(fn, out_sort=None):
    from backend_safe import sanitize

    def w(v, a, b):
        try:
            out = fn(v, a, b)
        except Exception:  # noqa: BLE001 - fail-soft per op contract
            out = None
        return sanitize(out, v, out_sort)

    return w


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce input to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _clip01(x):
    return np.clip(np.asarray(x, np.float64), 0.0, 1.0)


def _resize(x, H, W):
    """Deterministic bilinear resample of a 2-D image to exactly (H, W)."""
    x = np.asarray(x, np.float64)
    h, w = x.shape[:2]
    if h < 1 or w < 1:
        return np.zeros((H, W), np.float64)
    if (h, w) == (H, W):
        return x.copy()
    rr = np.linspace(0.0, h - 1, H)
    cc = np.linspace(0.0, w - 1, W)
    R, C = np.meshgrid(rr, cc, indexing="ij")
    out = ndimage.map_coordinates(
        x, np.vstack([R.ravel(), C.ravel()]), order=1, mode="nearest",
    )
    return out.reshape(H, W)


def _amt(a, lo, hi):
    """Map a in [0,1] to [lo,hi]."""
    return lo + float(np.clip(a, 0.0, 1.0)) * (hi - lo)


def _psf2otf(psf, shape):
    """Optical transfer function of a small spatial PSF for an image of ``shape``.

    Zero-pads the kernel, then circularly shifts its centre to the (0,0) origin
    so the FFT carries no linear-phase term (the standard psf2otf convention).
    """
    kh, kw = psf.shape
    pad = np.zeros(shape, np.float64)
    pad[:kh, :kw] = psf
    pad = np.roll(pad, -(kh // 2), axis=0)
    pad = np.roll(pad, -(kw // 2), axis=1)
    return np.fft.fft2(pad)


def _gauss_psf(sigma, radius=None):
    """A normalised 2-D Gaussian PSF kernel."""
    sigma = max(1e-3, float(sigma))
    if radius is None:
        radius = max(1, int(round(3.0 * sigma)))
    ax = np.arange(-radius, radius + 1, dtype=np.float64)
    xx, yy = np.meshgrid(ax, ax)
    k = np.exp(-(xx * xx + yy * yy) / (2.0 * sigma * sigma))
    s = k.sum()
    return k / s if s > 0 else k


def _motion_psf(length, angle_deg):
    """A normalised linear-motion-blur PSF: a unit line of ``length`` pixels
    through the kernel centre at ``angle_deg`` (0 deg = horizontal)."""
    length = max(1, int(round(length)))
    rad = np.deg2rad(float(angle_deg))
    dx, dy = np.cos(rad), np.sin(rad)
    ksize = length if (length % 2 == 1) else length + 1
    ksize = max(3, ksize)
    k = np.zeros((ksize, ksize), np.float64)
    c = ksize // 2
    n = max(2, length * 4)
    for t in np.linspace(-(length - 1) / 2.0, (length - 1) / 2.0, n):
        ix = int(round(c + t * dx))
        iy = int(round(c + t * dy))
        if 0 <= iy < ksize and 0 <= ix < ksize:
            k[iy, ix] += 1.0
    s = k.sum()
    if s <= 0:
        k[c, c] = 1.0
        s = 1.0
    return k / s


def _wiener_deconv(x, psf, nsr):
    """Parametric Wiener deconvolution of ``x`` by a spatial PSF.

    G(f)*conj(H(f)) / (|H(f)|^2 + nsr). nsr -> 0 approaches the inverse filter
    (max sharpening, max noise); large nsr -> gentle restoration.
    """
    H = _psf2otf(psf, x.shape)
    G = np.fft.fft2(x)
    Hc = np.conj(H)
    denom = (H * Hc).real + max(_EPS, float(nsr))
    F = G * Hc / denom
    return np.fft.ifft2(F).real


# --------------------------------------------------------------------------- #
# operators                                                                    #
# --------------------------------------------------------------------------- #
def iv_richardson_lucy(v, a, b):
    """Richardson-Lucy deconvolution assuming a small Gaussian PSF (sigma =
    ``RL_SIGMA``). ``a`` sets the iteration count n = 1 + round(a*14) (1..15);
    ``b`` is ignored. RL multiplicatively drives the estimate ``u`` so that
    ``u (*) psf`` matches the blurred measurement, sharpening real edges."""
    d = _img(v)
    if min(d.shape[:2]) < 3:
        return d
    iters = 1 + int(round(float(np.clip(a, 0.0, 1.0)) * 14))
    sigma = RL_SIGMA
    u = np.clip(d.copy(), _EPS, 1.0)
    d_pos = np.clip(d, 0.0, 1.0)
    for _ in range(iters):
        conv = ndimage.gaussian_filter(u, sigma, mode="reflect")
        conv = np.maximum(conv, _EPS)
        ratio = d_pos / conv
        # Gaussian PSF is symmetric, so the flipped PSF equals the PSF itself.
        u = u * ndimage.gaussian_filter(ratio, sigma, mode="reflect")
        u = np.clip(u, 0.0, 4.0)
    return _clip01(u)


def iv_wiener_deconv_spatial(v, a, b):
    """Self-contained spatial Wiener deconvolution of an assumed small Gaussian
    PSF. ``a`` sets the assumed blur sigma in (0, ``WIENER_SIGMA_MAX``] to invert
    (larger a -> stronger sharpening); ``b`` sets the noise-to-signal ratio nsr =
    1e-3 + b*0.15 (larger b -> gentler, more regularized restoration)."""
    x = _img(v)
    H, W = x.shape[:2]
    if min(H, W) < 3:
        return x
    sigma = _amt(a, 0.4, WIENER_SIGMA_MAX)
    nsr = 1e-3 + float(np.clip(b, 0.0, 1.0)) * 0.15
    max_r = max(1, (min(H, W) - 1) // 2)          # keep the PSF no larger than the image
    radius = min(max(1, int(round(3.0 * sigma))), max_r)
    psf = _gauss_psf(sigma, radius=radius)
    out = _wiener_deconv(x, psf, nsr)
    return _clip01(out)


def iv_unsharp_deblur(v, a, b):
    """Iterative unsharp masking as an approximate deblur. Each pass adds a scaled
    high-pass (image minus its Gaussian blur) back to the image. ``a`` sets the
    iteration count n = 1 + round(a*5) (1..6); ``b`` sets the per-pass amount
    amt = 0.4 + b (0.4..1.4). More iterations / larger amount -> sharper."""
    x = _img(v)
    if min(x.shape[:2]) < 3:
        return x
    iters = 1 + int(round(float(np.clip(a, 0.0, 1.0)) * 5))
    amt = _amt(b, 0.4, 1.4)
    sigma = 1.0
    out = x.copy()
    for _ in range(iters):
        blur = ndimage.gaussian_filter(out, sigma, mode="reflect")
        out = _clip01(out + amt * (out - blur))
    return out


def iv_motion_deblur(v, a, b):
    """Wiener deconvolution of an assumed LINEAR MOTION blur. ``a`` sets the blur
    length L = 3 + round(a*10) (3..13 px); ``b`` sets the blur angle theta =
    b*180 deg (b=0 -> horizontal). The op builds that motion PSF and inverts it,
    narrowing a bar that was smeared along the motion direction."""
    x = _img(v)
    if min(x.shape[:2]) < 3:
        return x
    length = 3 + int(round(float(np.clip(a, 0.0, 1.0)) * 10))
    angle = float(np.clip(b, 0.0, 1.0)) * 180.0
    psf = _motion_psf(length, angle)
    if min(x.shape[:2]) <= psf.shape[0]:
        return x
    nsr = 1e-2
    out = _wiener_deconv(x, psf, nsr)
    return _clip01(out)


def iv_backproject_superres(v, a, b):
    """Single-image iterative back-projection super-resolution (Irani-Peleg).
    Upscale to a higher grid, simulate the low-res observation by blurring and
    downscaling, back-project the residual into the high grid, then downscale the
    consistent estimate back to HxW. Net effect: high-frequency detail is boosted
    (sharpening-by-consistency). ``a`` sets iterations n = 1 + round(a*4) (1..5);
    ``b`` sets the back-projection step gain g = 0.5 + b (0.5..1.5)."""
    x = _img(v)
    H, W = x.shape[:2]
    if min(H, W) < 4:
        return x
    factor = 2
    Hh, Ww = H * factor, W * factor
    iters = 1 + int(round(float(np.clip(a, 0.0, 1.0)) * 4))
    gain = _amt(b, 0.5, 1.5)
    sigma = 1.0
    hi = _resize(x, Hh, Ww)                    # initial upsample
    for _ in range(iters):
        sim = _resize(ndimage.gaussian_filter(hi, sigma, mode="reflect"), H, W)
        residual = x - sim                     # low-res consistency error
        hi = hi + gain * _resize(residual, Hh, Ww)
    out = _resize(hi, H, W)
    return _clip01(out)


def iv_gradient_inpaint(v, a, b):
    """Harmonic (Laplace) inpainting of a central masked window. The interior of a
    centred window (side fraction from ``a``) is discarded and refilled by solving
    nabla^2 u = 0 with Dirichlet boundary equal to the surrounding known pixels
    (Jacobi relaxation = repeatedly replacing each masked pixel by its 4-neighbour
    mean). The recovered interior is the smoothest (minimum-gradient) fill of the
    hole. ``a`` sets the window size; ``b`` is ignored."""
    x = _img(v)
    H, W = x.shape[:2]
    if min(H, W) < 5:
        return x
    frac = _amt(a, 0.2, 0.6)
    wh = int(round(H * frac))
    ww = int(round(W * frac))
    wh = max(1, min(wh, H - 2))                 # keep a boundary ring
    ww = max(1, min(ww, W - 2))
    r0 = (H - wh) // 2
    c0 = (W - ww) // 2
    mask = np.zeros((H, W), dtype=bool)
    mask[r0:r0 + wh, c0:c0 + ww] = True
    if not mask.any():
        return x
    u = x.copy()
    # seed the hole with the boundary mean so relaxation converges quickly
    known = x[~mask]
    u[mask] = float(known.mean()) if known.size else 0.0
    iters = 2 * (wh + ww)                       # enough sweeps to propagate boundary
    iters = int(np.clip(iters, 32, 400))
    for _ in range(iters):
        lap = (
            np.roll(u, 1, axis=0) + np.roll(u, -1, axis=0)
            + np.roll(u, 1, axis=1) + np.roll(u, -1, axis=1)
        ) * 0.25
        u = np.where(mask, lap, x)              # Dirichlet: keep known pixels fixed
    return _clip01(u)


# --------------------------------------------------------------------------- #
# registry                                                                     #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" for every op: these inverse-problem restorers have no single
    # uncovered MVTec HALCON operator to reproduce (RL / spatial-Wiener / motion
    # deblur / back-projection SR / harmonic inpaint are not HALCON operators),
    # so no coverage claim is made.
    defs = [
        ("iv_richardson_lucy", "restoration", iv_richardson_lucy),
        ("iv_wiener_deconv_spatial", "restoration", iv_wiener_deconv_spatial),
        ("iv_unsharp_deblur", "restoration", iv_unsharp_deblur),
        ("iv_motion_deblur", "restoration", iv_motion_deblur),
        ("iv_backproject_superres", "restoration", iv_backproject_superres),
        ("iv_gradient_inpaint", "restoration", iv_gradient_inpaint),
    ]
    return [Op(n, c, "", IMAGE, IMAGE, _safe(f, IMAGE)) for (n, c, f) in defs]
