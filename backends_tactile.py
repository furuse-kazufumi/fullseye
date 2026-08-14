"""Tactile / contact-from-shading operators (registry cluster ``tac_``).

This cluster treats the input 2-D image as a **tactile sensor frame** of the
GelSight / DIGIT family: an elastomer pad is pressed against an object, its
membrane deforms, and internal illumination turns that deformation into
*shading*. Everything a vision-based tactile sensor reports -- where contact
happened, how deep the indentation is, which way the surface tilts, how hard it
is pressed, whether the gel is being sheared -- is therefore recovered from a
grayscale image by classical photometric / variational methods.

None of these operators reproduces a HALCON operator -- MVTec HALCON has no
tactile, contact-mask, height-from-shading, GelSight or gel-shear operator of
any kind. Every op here therefore carries ``halcon = ""`` and makes **NO**
coverage claim; this is a brand-new capability, not a re-implementation.

  tac_contact_mask          Contact segmentation by background subtraction: the
                            large-scale Gaussian background of the frame is the
                            *pseudo-reference* (undeformed gel), and pixels whose
                            deviation |v - G_sigma(v)| exceeds a threshold are in
                            contact, cleaned by binary opening + closing.
                            a = deviation threshold (0.005..0.15 gray levels),
                            b = morphological cleanup iterations (0..3).
                            Returns a BINARY 0/1 region; a flat frame -> empty.
  tac_height_from_shading   Poisson height-from-gradient (the integration step of
                            GelSight depth reconstruction / photometric stereo):
                            image gradients are read as surface slopes and the
                            Poisson equation lap(h) = div(grad v) is solved in the
                            FFT domain, i.e. h_hat = div_hat / lap_hat with the DC
                            mode pinned to 0. a = gradient gain (slope scale),
                            b = pre-smoothing sigma of the gradient field.
                            Output min-max normalised to [0,1].
  tac_surface_normal        Normal-z (slope) map from shading gradients, the
                            Horn shape-from-shading normal parameterisation
                            nz = 1/sqrt(1 + gx^2 + gy^2): flat gel -> 1, steep
                            indentation walls -> 0. a = gradient gain (1..21x),
                            b = pre-smoothing sigma. Already in [0,1].
  tac_pressure_proxy        Contact-pressure proxy: rectified deviation from the
                            pseudo-reference background, gated to the
                            high-deviation (contact) area and Gaussian-smoothed
                            -- the standard "indentation depth ~ normal force"
                            surrogate used when no force sensor is available.
                            a = sensitivity (gain 1..10x), b = smoothing radius.
  tac_shear_field           In-plane shear proxy from the structure tensor
                            (Foerstner / Bigun-Granlund coherence):
                            coh = sqrt((J11-J22)^2 + 4 J12^2) / (J11 + J22),
                            which is high where the gel texture is stretched into
                            one dominant orientation, as it is under tangential
                            load. a = tensor integration sigma, b = output gain.

Honest caveat: a real GelSight recovers contact, depth and shear from a
REFERENCE (undeformed) frame plus optical-flow of the printed marker dots across
two frames. These single-image operators have neither, so they use the image's
own large-scale Gaussian background as a *pseudo*-reference and can only report
a shear **magnitude/anisotropy proxy** -- the true shear direction and sign are
unrecoverable from one frame, and absolute depth/force units are not calibrated
(outputs are relative, min-max normalised maps).

Contract: ``fn(v, a, b)`` maps a 2-D float64 image in [0,1] (knobs a,b in [0,1])
to a 2-D float64 array in [0,1] of the declared sort, refit to the input HxW.
Deterministic, finite on every battery input (including const0 / const1 /
const_mid / tiny4 / single_bright), fail-soft via the shared ``sanitize``.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

_EPS = 1e-12


# --------------------------------------------------------------------------- #
# safety wrapper (shared pattern with the other backends)                     #
# --------------------------------------------------------------------------- #
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
# small helpers                                                               #
# --------------------------------------------------------------------------- #
def _img(v):
    """Coerce input to a finite 2-D float64 image in [0,1] (fail-soft)."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:                       # accidental colour -> luma
        x = x.mean(axis=-1)
    elif x.ndim != 2:
        x = np.atleast_2d(x).astype(np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


def _knob(k):
    """Clamp a knob to [0,1] and make it finite."""
    try:
        f = float(k)
    except Exception:  # noqa: BLE001 - knobs come from an evolving genome
        return 0.0
    if not np.isfinite(f):
        return 0.0
    return float(np.clip(f, 0.0, 1.0))


def _norm01(x):
    """Finite-safe min-max normalisation of an array into [0,1]."""
    x = np.asarray(x, np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    if x.size == 0:
        return x
    lo = float(x.min())
    hi = float(x.max())
    if not np.isfinite(lo) or not np.isfinite(hi) or (hi - lo) <= 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def _blur(x, sigma):
    """Gaussian blur with a sigma clamped to something sane for the image."""
    s = float(sigma)
    if not np.isfinite(s) or s <= 1e-6:
        return np.asarray(x, np.float64).copy()
    h, w = x.shape[:2]
    s = min(s, max(1.0, 0.5 * max(h, w)))          # never blur wider than the image
    return ndimage.gaussian_filter(np.asarray(x, np.float64), sigma=s, mode="nearest")


def _background(x):
    """Large-scale Gaussian background = the *pseudo-reference* (undeformed gel).

    A real GelSight subtracts a captured reference frame; with a single image the
    low-frequency illumination envelope is the best available stand-in."""
    h, w = x.shape[:2]
    sigma = max(2.0, min(h, w) / 6.0)
    return _blur(x, sigma)


def _grad(x):
    """Central-difference image gradients (gy, gx), edge-replicated."""
    x = np.asarray(x, np.float64)
    gy = np.gradient(x, axis=0) if x.shape[0] > 1 else np.zeros_like(x)
    gx = np.gradient(x, axis=1) if x.shape[1] > 1 else np.zeros_like(x)
    gy = np.nan_to_num(gy, nan=0.0, posinf=0.0, neginf=0.0)
    gx = np.nan_to_num(gx, nan=0.0, posinf=0.0, neginf=0.0)
    return gy, gx


def _struct3():
    """3x3 8-connected structuring element for the morphological cleanup."""
    return np.ones((3, 3), bool)


# --------------------------------------------------------------------------- #
# operators (module-level so tests can call them directly)                    #
# --------------------------------------------------------------------------- #
def tac_contact_mask(v, a, b):
    """Contact region of a tactile frame by pseudo-reference background
    subtraction: ``dev = |v - G_sigma(v)|`` with ``sigma = max(2, min(H,W)/6)``
    (the low-frequency envelope stands in for the undeformed reference frame),
    thresholded at ``thr = 0.005 + 0.145*a`` gray levels, then cleaned with
    ``round(3*b)`` iterations of binary opening followed by binary closing
    (3x3, 8-connected). ``a`` = deviation threshold (sensitivity), ``b`` =
    morphological cleanup strength. Returns a BINARY 0/1 float64 region of the
    input HxW; a perfectly flat (constant) frame has zero deviation everywhere
    and therefore yields an EMPTY mask."""
    x = _img(v)
    H, W = x.shape[:2]
    a = _knob(a)
    b = _knob(b)
    dev = np.abs(x - _background(x))
    thr = 0.005 + 0.145 * a
    mask = dev > thr                                   # strict: dev == 0 -> False
    iters = int(round(3.0 * b))
    if iters > 0 and mask.any() and min(H, W) >= 3:
        st = _struct3()
        mask = ndimage.binary_opening(mask, structure=st, iterations=iters, border_value=0)
        mask = ndimage.binary_closing(mask, structure=st, iterations=iters, border_value=0)
    return mask.astype(np.float64).reshape(H, W)


def tac_height_from_shading(v, a, b):
    """Height/relief map by Poisson integration of the shading gradients -- the
    integration stage of GelSight depth reconstruction (and of photometric
    stereo): the image gradients are read as surface slopes ``p = gain*gx``,
    ``q = gain*gy`` and the Poisson equation ``lap(h) = div(p,q)`` is solved
    spectrally, ``h_hat = div_hat / lap_hat`` with the discrete Laplacian symbol
    ``2cos(2*pi*u/W)+2cos(2*pi*v/H)-4`` and the (undetermined) DC mode pinned to
    zero. ``a`` = gradient gain (0.25..4.25x), ``b`` = pre-smoothing sigma of the
    gradient field (0..3). Output is min-max normalised to [0,1] and refit to
    HxW; a constant frame integrates to a flat (all-zero) relief."""
    x = _img(v)
    H, W = x.shape[:2]
    a = _knob(a)
    b = _knob(b)
    if H < 2 or W < 2:
        return np.clip(x, 0.0, 1.0)
    gain = 0.25 + 4.0 * a
    src = _blur(x, 3.0 * b)
    gy, gx = _grad(src)
    p = gain * gx
    q = gain * gy
    # divergence of the (gain-scaled) gradient field
    dpx = np.gradient(p, axis=1) if W > 1 else np.zeros_like(p)
    dqy = np.gradient(q, axis=0) if H > 1 else np.zeros_like(q)
    div = np.nan_to_num(dpx + dqy, nan=0.0, posinf=0.0, neginf=0.0)
    if not np.any(np.abs(div) > 1e-15):
        return np.zeros((H, W), np.float64)
    # spectral Poisson solve
    u = np.arange(W, dtype=np.float64)
    w_ = np.arange(H, dtype=np.float64)
    lap = (2.0 * np.cos(2.0 * np.pi * u / W)).reshape(1, W) \
        + (2.0 * np.cos(2.0 * np.pi * w_ / H)).reshape(H, 1) - 4.0
    lap[0, 0] = 1.0                                    # guard the singular DC mode
    Dh = np.fft.fft2(div)
    Hh = Dh / lap
    Hh[0, 0] = 0.0                                     # gauge fix: mean height = 0
    h = np.real(np.fft.ifft2(Hh))
    h = np.nan_to_num(h, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(_norm01(h), 0.0, 1.0).reshape(H, W)


def tac_surface_normal(v, a, b):
    """Surface-normal z-component (slope map) from the shading gradients, using
    Horn's shape-from-shading normal parameterisation
    ``n = (-p, -q, 1)/sqrt(1+p^2+q^2)`` so that ``nz = 1/sqrt(1+p^2+q^2)`` with
    ``p = gain*gx``, ``q = gain*gy``. Flat (uncontacted) gel gives nz = 1, steep
    indentation walls tend to 0, so the map is already a valid [0,1] encoding.
    ``a`` = gradient gain (1..21x -- how steep the shading is taken to be),
    ``b`` = pre-smoothing sigma of the image (0..3) to tame sensor noise.
    Constant input -> all-ones (perfectly flat gel)."""
    x = _img(v)
    H, W = x.shape[:2]
    a = _knob(a)
    b = _knob(b)
    gain = 1.0 + 20.0 * a
    src = _blur(x, 3.0 * b)
    gy, gx = _grad(src)
    p = gain * gx
    q = gain * gy
    denom = np.sqrt(1.0 + p * p + q * q)
    denom = np.where(np.isfinite(denom) & (denom > 1.0), denom, 1.0)
    nz = 1.0 / denom
    nz = np.nan_to_num(nz, nan=1.0, posinf=1.0, neginf=0.0)
    return np.clip(nz, 0.0, 1.0).reshape(H, W)


def tac_pressure_proxy(v, a, b):
    """Contact-pressure proxy map: the rectified deviation from the
    pseudo-reference background ``dev = |v - G_sigma(v)|`` is gated to the
    high-deviation (contact) area -- a relative gate at ``0.15 * max(dev)`` plus
    an absolute floor of 0.005 -- amplified by the sensitivity gain and
    Gaussian-smoothed, which is the standard "indentation depth is monotone in
    normal force" surrogate used when a tactile pad carries no force sensor.
    ``a`` = sensitivity (gain 1..10x), ``b`` = smoothing radius (sigma 0.5..4.5).
    Output clipped to [0,1], HxW; a flat frame yields an all-zero pressure map
    (no contact, no force)."""
    x = _img(v)
    H, W = x.shape[:2]
    a = _knob(a)
    b = _knob(b)
    dev = np.abs(x - _background(x))
    dmax = float(dev.max()) if dev.size else 0.0
    if not np.isfinite(dmax) or dmax <= 1e-9:
        return np.zeros((H, W), np.float64)
    gate = dev > max(0.005, 0.15 * dmax)
    gain = 1.0 + 9.0 * a
    pressure = _blur(dev * gate.astype(np.float64), 0.5 + 4.0 * b) * gain
    pressure = np.nan_to_num(pressure, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(pressure, 0.0, 1.0).reshape(H, W)


def tac_shear_field(v, a, b):
    """In-plane shear proxy from the 2-D structure tensor (Foerstner /
    Bigun-Granlund orientation coherence). The tensor
    ``J = G_sigma(grad v * grad v^T)`` has eigenvalues l1 >= l2, and the
    coherence ``(l1-l2)/(l1+l2) = sqrt((J11-J22)^2 + 4*J12^2) / (J11+J22)``
    is 1 where the gel texture is stretched into a single dominant orientation
    (as it is under tangential/shear load) and 0 where it is isotropic. The
    result is additionally weighted by the tensor trace (gradient energy) so
    that texture-free, un-contacted gel stays dark instead of amplifying noise
    orientation. ``a`` = tensor integration sigma (0.6..4.6), ``b`` = output gain
    (0.5..2.5). Output clipped to [0,1], HxW; a constant frame has zero gradient
    energy and yields an all-zero shear field."""
    x = _img(v)
    H, W = x.shape[:2]
    a = _knob(a)
    b = _knob(b)
    gy, gx = _grad(x)
    sigma = 0.6 + 4.0 * a
    j11 = _blur(gx * gx, sigma)
    j22 = _blur(gy * gy, sigma)
    j12 = _blur(gx * gy, sigma)
    trace = j11 + j22
    diff = np.sqrt(np.maximum((j11 - j22) ** 2 + 4.0 * j12 * j12, 0.0))
    coh = np.where(trace > 1e-10, diff / np.maximum(trace, _EPS), 0.0)
    coh = np.clip(np.nan_to_num(coh, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    tmax = float(trace.max()) if trace.size else 0.0
    if not np.isfinite(tmax) or tmax <= 1e-12:
        return np.zeros((H, W), np.float64)
    energy = np.clip(trace / tmax, 0.0, 1.0)           # de-emphasise flat gel
    gain = 0.5 + 2.0 * b
    out = np.nan_to_num(coh * energy * gain, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(out, 0.0, 1.0).reshape(H, W)


# --------------------------------------------------------------------------- #
# registry                                                                    #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" for every op: MVTec HALCON has no tactile / GelSight / contact
    # / height-from-shading operator at all, so this whole cluster is a new
    # capability and makes NO coverage claim.
    defs = [
        ("tac_contact_mask", "tactile", IMAGE, REGION, tac_contact_mask),
        ("tac_height_from_shading", "tactile", IMAGE, IMAGE, tac_height_from_shading),
        ("tac_surface_normal", "tactile", IMAGE, IMAGE, tac_surface_normal),
        ("tac_pressure_proxy", "tactile", IMAGE, IMAGE, tac_pressure_proxy),
        ("tac_shear_field", "tactile", IMAGE, IMAGE, tac_shear_field),
    ]
    return [Op(n, c, "", i, o, _safe(f, o)) for (n, c, i, o, f) in defs]
