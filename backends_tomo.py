"""Tomographic reconstruction operators (registry cluster ``tm_``).

This cluster treats the input 2-D image as a **sinogram** -- the raw output of a
computed-tomography scan, whose rows are projection *angles* and whose columns
are *detector* positions -- and reconstructs the underlying slice, or runs the
forward Radon transform that produced such a sinogram in the first place. It is
the image-processing core of sparse-view / limited-angle CT.

Sinogram convention (used consistently by every op here):

    row index  = projection angle  (angles uniformly cover [0, span) degrees)
    col index  = detector position

None of these operators reproduces a HALCON operator -- MVTec HALCON has no
Radon / filtered-back-projection / algebraic-reconstruction operator (verified:
no ``radon``/``fbp``/``sart``/``backproject``/``sinogram`` node exists in
``data/halcon_graph.json``). Every op therefore carries ``halcon = ""`` and makes
NO coverage claim; this is a brand-new capability.

  tm_radon_forward         forward Radon transform of the input (treated as a
                           slice image) -> sinogram, fitted back to HxW.
                           a = angular density (sparse .. dense views),
                           b = angular span (limited-angle .. full 180 deg).
  tm_fbp_reconstruct       filtered back-projection of the input sinogram.
                           b < 0.5 -> Ram-Lak (ramp) filter, b >= 0.5 ->
                           Shepp-Logan filter. a is unused (b is the knob).
  tm_sart_reconstruct      a few SART / SIRT algebraic-reconstruction sweeps of
                           the input sinogram. a = iteration count (1..5),
                           b = relaxation factor.
  tm_backproject_unfiltered  plain (UN-filtered) back-projection of the input
                           sinogram -> the classic blurry reconstruction that
                           shows exactly why FBP needs its ramp filter. a,b
                           unused (this is the naive baseline).
  tm_sinogram_denoise      smoothing of the input sinogram along the angle
                           direction (a projection-consistency prior; adjacent
                           angles see almost the same object). a = angle-axis
                           sigma, b = a gentle detector-axis sigma.

Implementation honesty: when ``scikit-image`` is importable (the normal case in
this repo) the genuine ``skimage.transform.radon`` / ``iradon`` / ``iradon_sart``
are used. When it is absent the module falls back to a self-contained NumPy
``rotate-and-sum`` Radon transform and an FFT ramp/Shepp-Logan-filtered
back-projection -- both are real algorithms, not stubs (the tests exercise the
NumPy path directly). Either way the docstrings state which path ran.

Contract: ``fn(v, a, b)`` maps a 2-D float64 image in [0,1] (plus knobs
a,b in [0,1]) to a 2-D float64 image in [0,1]. Deterministic, finite, fail-soft
(never raises on the canonical battery); every output is refit to the input HxW.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

try:  # genuine library path (preferred)
    from skimage.transform import iradon, iradon_sart, radon

    _HAVE_SKI = True
except Exception:  # noqa: BLE001 - optional dependency; NumPy fallback below
    _HAVE_SKI = False


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


def _norm01(x):
    """Finite-safe min-max normalisation of an array into [0,1]."""
    x = np.asarray(x, np.float64)
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    lo = float(x.min())
    hi = float(x.max())
    if hi - lo <= 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def _thetas(n, span_deg):
    """``n`` projection angles uniformly covering ``[0, span_deg)`` degrees."""
    n = max(1, int(n))
    return np.linspace(0.0, float(span_deg), n, endpoint=False)


# --------------------------------------------------------------------------- #
# NumPy Radon / iRadon fallback (used only when scikit-image is unavailable)  #
# --------------------------------------------------------------------------- #
def _radon_np(img, thetas_deg):
    """Rotate-and-sum forward Radon transform -> sinogram (angles x detector).

    For each angle the image is rotated and summed down its columns; this is the
    textbook discrete Radon transform (line integrals across the slice)."""
    rows = []
    for t in thetas_deg:
        rot = ndimage.rotate(img, -float(t), reshape=False, order=1, mode="constant", cval=0.0)
        rows.append(rot.sum(axis=0))
    return np.asarray(rows, np.float64)          # (n_angles, W)


def _ramp_1d(n, kind):
    """1-D frequency response of the FBP filter (Ram-Lak or Shepp-Logan)."""
    f = np.fft.fftfreq(n)
    H = 2.0 * np.abs(f)                           # Ram-Lak (|omega|)
    if kind == "shepp-logan":
        with np.errstate(invalid="ignore", divide="ignore"):
            H = H * np.sinc(f)                    # Shepp-Logan window = ramp * sinc
    return np.nan_to_num(H, nan=0.0, posinf=0.0, neginf=0.0).reshape(1, -1)


def _iradon_np(sino, thetas_deg, filt):
    """Back-projection of a sinogram (angles x detector).

    ``filt`` is ``None`` (plain back-projection), ``"ramp"`` (Ram-Lak FBP) or
    ``"shepp-logan"`` (Shepp-Logan FBP)."""
    sino = np.asarray(sino, np.float64)
    n_ang, det = sino.shape
    if filt in ("ramp", "shepp-logan"):
        H = _ramp_1d(det, filt)
        S = np.fft.fft(sino, axis=-1)
        proj = np.real(np.fft.ifft(S * H, axis=-1))
    else:
        proj = sino
    recon = np.zeros((det, det), np.float64)
    for i, t in enumerate(thetas_deg):
        smear = np.tile(proj[i], (det, 1))
        recon += ndimage.rotate(smear, float(t), reshape=False, order=1, mode="constant", cval=0.0)
    return recon * (np.pi / (2.0 * max(n_ang, 1)))


# --------------------------------------------------------------------------- #
# operators (module-level so tests can call them directly)                    #
# --------------------------------------------------------------------------- #
def tm_radon_forward(v, a, b):
    """Forward Radon projection: treat ``v`` as a slice image and integrate it
    along parallel rays to build a sinogram (rows = angles, cols = detector),
    refit to the original HxW. ``a`` sets how many angles are acquired
    (``n = round(H*a)`` clamped to 8..360 -- the sparse-view knob), ``b`` sets the
    angular span (``span = 180*(0.5+0.5*b)`` deg -- b<1 is limited-angle CT).
    Uses ``skimage.transform.radon`` when available, else the NumPy
    rotate-and-sum Radon transform."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 3 or W < 3:
        return x
    n_ang = int(np.clip(round(H * float(np.clip(a, 0.05, 1.0))), 8, 360))
    span = 180.0 * float(np.clip(0.5 + 0.5 * b, 0.5, 1.0))
    thetas = _thetas(n_ang, span)
    if _HAVE_SKI:
        sino = radon(x, theta=thetas, circle=True).T        # (angles, detector)
    else:
        sino = _radon_np(x, thetas)
    sino = _norm01(sino)
    return np.clip(_resize(sino, H, W), 0.0, 1.0)


def tm_fbp_reconstruct(v, a, b):
    """Filtered back-projection: treat ``v`` as a sinogram (rows = angles,
    cols = detector, angles assumed uniform over [0,180)) and reconstruct the
    slice. ``b`` picks the reconstruction filter -- b < 0.5 -> Ram-Lak (ramp),
    b >= 0.5 -> Shepp-Logan. ``a`` is unused (the filter is the meaningful knob).
    Uses ``skimage.transform.iradon`` when available, else the NumPy
    FFT-ramp-filtered back-projection. Output refit to HxW."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 3 or W < 3:
        return x
    kind = "ramp" if float(b) < 0.5 else "shepp-logan"
    thetas = _thetas(H, 180.0)
    if _HAVE_SKI:
        recon = iradon(x.T, theta=thetas, filter_name=kind, circle=True, output_size=W)
    else:
        recon = _iradon_np(x, thetas, kind)
    return np.clip(_resize(_norm01(recon), H, W), 0.0, 1.0)


def tm_sart_reconstruct(v, a, b):
    """Algebraic reconstruction: run a few SART/SIRT sweeps on the input
    sinogram (rows = angles). ``a`` sets the iteration count
    (``round(1+a*4)`` -> 1..5), ``b`` sets the relaxation factor
    (``0.05 + b*0.35``). Uses ``skimage.transform.iradon_sart`` when available,
    else a self-contained NumPy SIRT (project -> residual -> weighted
    back-projection) loop. Output refit to HxW."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 3 or W < 3:
        return x
    n_iter = int(np.clip(round(1 + float(np.clip(a, 0.0, 1.0)) * 4), 1, 5))
    relax = float(np.clip(0.05 + float(np.clip(b, 0.0, 1.0)) * 0.35, 0.05, 0.4))
    thetas = _thetas(H, 180.0)
    if _HAVE_SKI:
        est = None
        for _ in range(n_iter):
            est = iradon_sart(x.T, theta=thetas, image=est, relaxation=relax)
        recon = est
    else:
        det = W
        est = np.zeros((det, det), np.float64)
        weight = _iradon_np(_radon_np(np.ones((det, det)), thetas), thetas, None) + 1e-6
        for _ in range(n_iter):
            resid = x - _radon_np(est, thetas)
            est = est + relax * _iradon_np(resid, thetas, None) / weight
        recon = est
    return np.clip(_resize(_norm01(recon), H, W), 0.0, 1.0)


def tm_backproject_unfiltered(v, a, b):
    """Plain (UN-filtered) back-projection of the input sinogram -- the classic
    blurry reconstruction. No ramp filter is applied, so high frequencies are
    suppressed and every point spreads a 1/r blur: this deliberately shows why
    FBP's filter is needed. ``a``/``b`` are unused (this is the fixed naive
    baseline). Uses ``skimage.transform.iradon`` with ``filter_name=None`` when
    available, else the NumPy plain back-projection. Output refit to HxW."""
    x = _img(v)
    H, W = x.shape[:2]
    if H < 3 or W < 3:
        return x
    thetas = _thetas(H, 180.0)
    if _HAVE_SKI:
        recon = iradon(x.T, theta=thetas, filter_name=None, circle=True, output_size=W)
    else:
        recon = _iradon_np(x, thetas, None)
    return np.clip(_resize(_norm01(recon), H, W), 0.0, 1.0)


def tm_sinogram_denoise(v, a, b):
    """Smooth the input sinogram along the ANGLE direction (rows). Neighbouring
    projection angles view almost the same object, so angle-direction smoothing
    is a genuine consistency prior that suppresses per-angle detector noise while
    preserving the sinusoidal traces. ``a`` sets the angle-axis Gaussian sigma
    (``a*4``), ``b`` adds a gentle detector-axis sigma (``b*1.5``). Output stays
    a same-shape sinogram in [0,1]."""
    x = _img(v)
    sig_ang = float(np.clip(a, 0.0, 1.0)) * 4.0
    sig_det = float(np.clip(b, 0.0, 1.0)) * 1.5
    out = x
    if sig_ang > 1e-6:
        out = ndimage.gaussian_filter1d(out, sigma=sig_ang, axis=0, mode="nearest")
    if sig_det > 1e-6:
        out = ndimage.gaussian_filter1d(out, sigma=sig_det, axis=1, mode="nearest")
    return np.clip(out, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# registry                                                                    #
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" for every op: MVTec HALCON has no Radon / FBP / SART /
    # back-projection / sinogram operator (none of these names exist in
    # data/halcon_graph.json), so this whole cluster is a new capability and
    # makes no coverage claim.
    defs = [
        ("tm_radon_forward", "tomography", tm_radon_forward),
        ("tm_fbp_reconstruct", "tomography", tm_fbp_reconstruct),
        ("tm_sart_reconstruct", "tomography", tm_sart_reconstruct),
        ("tm_backproject_unfiltered", "tomography", tm_backproject_unfiltered),
        ("tm_sinogram_denoise", "tomography", tm_sinogram_denoise),
    ]
    return [Op(n, c, "", IMAGE, IMAGE, _safe(f, IMAGE)) for (n, c, f) in defs]
