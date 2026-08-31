"""3-D volume intensity-transform operators (numpy only).

The *grey-value* side of the ``volume`` sort. :mod:`volops` gave a CT / MRI /
industrial-laminography volume its analysis primitives (vesselness, distance
transform, labelling, region props); this module fills the confirmed gap on the
*intensity* axis — the 2-D operator set carries 41 grey-value ops while the voxel
world had **zero**. Four everyday transforms, straight from radiology and
industrial-CT practice:

  * :func:`vol_window_level` — CT Hounsfield-unit *windowing*, the single most
    common interactive operation in radiology: map ``[center - width/2,
    center + width/2]`` linearly onto an output range and clip everything
    outside. The HALCON analogue is ``scale_image`` (mult/add form of the same
    linear map, without the clip).
  * :func:`vol_equalize` — histogram equalisation, the volume version of
    HALCON ``equ_histo_image``; an optional *mask* restricts the histogram to a
    domain while the LUT is applied to the whole volume (the ``reduce_domain``
    + ``equ_histo_image`` behaviour).
  * :func:`vol_gamma` — gamma (power-law) correction on the volume's own
    ``[min, max]`` range, the volume version of HALCON ``pow_image`` /
    ``gamma_image``.
  * :func:`vol_stretch` — percentile contrast stretch to ``[0, 1]``, the
    robust-to-outliers cousin of HALCON ``scale_image_max``.

Frame convention (shared with :mod:`volio` / :mod:`volops`): a volume is a
``(D, H, W)`` float64 array indexed ``[z, y, x]``. These are point-wise
transforms — *spacing* is irrelevant and deliberately absent.

Honest limitations (nothing here claims more than a real test in
``tests/test_volgray.py`` proves):

  * **Equalisation is an nbins-discretised approximation.** The LUT is built
    from an *nbins*-bin histogram, so the mapping is piecewise-constant: values
    inside one bin become indistinguishable, and the minimum voxel maps to the
    first bin's CDF value (a small positive number), not exactly 0 — the same
    behaviour as ``skimage.exposure.equalize_hist``. A uniform distribution is
    therefore only *approximately* unchanged (to ~1/nbins).
  * **Constant volumes pass through unchanged** (equalise / gamma / stretch).
    Normalising a flat volume's ``[min, max]`` range would divide by zero, or —
    worse — amplify floating-point rounding dust to full scale (the flat-image
    PITFALL this project has been bitten by before). A constant volume is
    returned as-is, honestly, rather than manufactured into contrast.
  * **Windowing clips.** Everything below/above the window saturates to the
    output-range ends by design (that is what a CT window *is*); information
    outside the window is discarded, not compressed.
  * A *mask* that is not already ``{0, 1}`` is thresholded at ``> 0.5`` — the
    same documented convention as :mod:`volops` / ``ops.vol_count``.

Fail-closed on untrusted input: every entry point requires a 3-D ``(D, H, W)``
array, coerces to float64, rejects NaN / Inf, and caps the voxel count
(``MAX_VOXELS``) *before* any heavy allocation. A malformed input or parameter
raises ``ValueError`` naming the problem.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "vol_window_level", "vol_equalize", "vol_gamma", "vol_stretch",
    "VOLGRAY_OPS", "MAX_VOXELS",
]

#: The public 3-D intensity-transform operators, by name (facade wiring).
VOLGRAY_OPS = [
    "vol_window_level", "vol_equalize", "vol_gamma", "vol_stretch",
]

#: Refuse a volume larger than this. ~134 M voxels = 1 GiB as float64
#: (the same budget as ``volops.MAX_VOXELS`` — kept module-local so volgray
#: stays independent of volops).
MAX_VOXELS = 1 << 27


# --------------------------------------------------------------------------- #
# fail-closed input helpers (module-local twins of the volops helpers)         #
# --------------------------------------------------------------------------- #
def _require_volume(vol, name: str = "vol", check_finite: bool = True) -> np.ndarray:
    """Coerce to a contiguous ``(D, H, W)`` float64 array or raise ``ValueError``.

    Rejects anything that is not exactly 3-D, and (by default) any NaN / Inf —
    a poisoned voxel would corrupt every histogram / percentile / range
    computation downstream silently."""
    v = np.ascontiguousarray(vol, dtype=np.float64)
    if v.ndim != 3:
        raise ValueError("%s must be a 3-D (D, H, W) volume, got a %d-D array of shape %r"
                         % (name, v.ndim, tuple(np.shape(vol))))
    if check_finite and not np.isfinite(v).all():
        n = int((~np.isfinite(v)).sum())
        raise ValueError("%s has %d non-finite voxel(s) (NaN/Inf) — refusing "
                         "(the intensity transforms would propagate them)" % (name, n))
    return v


def _check_voxels(v: np.ndarray, cap: int, op: str, cap_name: str) -> None:
    if v.size > cap:
        raise ValueError("%s: a %d-voxel volume (shape %r) exceeds the %d cap "
                         "(volgray.%s) — crop to an ROI or downsample first"
                         % (op, v.size, v.shape, cap, cap_name))


def _finite_scalar(x, name: str) -> float:
    try:
        f = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s must be a finite number, got %r" % (name, x)) from None
    if not np.isfinite(f):
        raise ValueError("%s must be a finite number, got %r" % (name, x))
    return f


# --------------------------------------------------------------------------- #
# vol_window_level                                                             #
# --------------------------------------------------------------------------- #
def vol_window_level(vol, center, width, out_range=(0.0, 1.0)):
    """CT window/level (HU windowing) — the radiologist's daily linear remap.

    Maps the intensity window ``[center - width/2, center + width/2]`` linearly
    onto *out_range* ``(lo, hi)``; voxels below the window saturate at ``lo``,
    voxels above at ``hi`` (clipped, by design — that is what a CT window
    *does*). A bone window and a soft-tissue window on the same Hounsfield
    volume make entirely different structures visible. HALCON analogue:
    ``scale_image`` (the linear part), plus the clip.

    Parameters
    ----------
    vol : array_like, shape (D, H, W)
        Input volume (coerced to float64; NaN/Inf rejected). Hounsfield units
        or any other physical scale — *center* / *width* live on the same scale.
    center, width : float
        Window centre and full width. ``width`` must be ``> 0`` (fail-closed).
    out_range : (float, float)
        Output ``(lo, hi)`` with ``lo < hi``. Default ``(0.0, 1.0)``.

    Returns
    -------
    ndarray, shape (D, H, W), float64
        The windowed volume, everywhere inside ``[lo, hi]``.

    Raises
    ------
    ValueError
        Non-3-D / non-finite input, ``width <= 0``, or a malformed *out_range*.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_window_level", "MAX_VOXELS")
    c = _finite_scalar(center, "center")
    w = _finite_scalar(width, "width")
    if w <= 0.0:
        raise ValueError("width must be > 0 (a zero/negative CT window is "
                         "meaningless), got %r" % (width,))
    try:
        lo, hi = (float(out_range[0]), float(out_range[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("out_range must be a (lo, hi) pair, got %r"
                         % (out_range,)) from None
    if not (np.isfinite(lo) and np.isfinite(hi)) or not lo < hi:
        raise ValueError("out_range must be finite with lo < hi, got %r" % (out_range,))
    # linear map of [c - w/2, c + w/2] -> [0, 1], clip, then -> [lo, hi]
    t = (v - (c - w / 2.0)) / w
    np.clip(t, 0.0, 1.0, out=t)
    return lo + t * (hi - lo)


# --------------------------------------------------------------------------- #
# vol_equalize                                                                 #
# --------------------------------------------------------------------------- #
def vol_equalize(vol, nbins=256, mask=None):
    """Histogram equalisation of a volume (HALCON ``equ_histo_image``).

    Builds an *nbins*-bin histogram over the volume's ``[min, max]`` range,
    takes its cumulative distribution as a monotone LUT, and maps every voxel
    through it — the output lives in ``(0, 1]`` and its histogram is
    (approximately) flat. With *mask* (thresholded at ``> 0.5``, the volops
    convention) the **histogram is computed from the masked voxels only while
    the LUT is applied to the whole volume** — exactly the HALCON
    ``reduce_domain`` + ``equ_histo_image`` domain behaviour, and the right
    tool when a dominant background (e.g. air around a CT subject) would
    otherwise swallow the whole dynamic range.

    A **constant volume is returned unchanged** — normalising a flat volume
    would amplify floating-point dust into full-scale garbage (fail-honest,
    not fail-loud; see the module docstring).

    Parameters
    ----------
    vol : array_like, shape (D, H, W)
        Input volume (coerced to float64; NaN/Inf rejected).
    nbins : int
        Histogram bins, ``>= 2``. More bins = finer LUT (the mapping is
        piecewise-constant per bin — an approximation, documented above).
    mask : array_like, shape (D, H, W), optional
        Histogram domain. Must match *vol*'s shape and select at least one
        voxel (an empty domain has no histogram — fail-closed).

    Returns
    -------
    ndarray, shape (D, H, W), float64
        The equalised volume in ``[0, 1]`` (constant input: the input itself).

    Raises
    ------
    ValueError
        Non-3-D / non-finite input, ``nbins < 2``, a mask shape mismatch, or
        an empty mask.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_equalize", "MAX_VOXELS")
    nb = int(nbins)
    if nb < 2:
        raise ValueError("nbins must be an integer >= 2, got %r" % (nbins,))
    vmin = float(v.min())
    vmax = float(v.max())
    if vmax <= vmin:
        # constant volume: no contrast to redistribute — pass through unchanged
        return v.copy()
    if mask is not None:
        m = _require_volume(mask, "mask") > 0.5
        if m.shape != v.shape:
            raise ValueError("mask shape %r does not match vol shape %r"
                             % (m.shape, v.shape))
        sample = v[m]
        if sample.size == 0:
            raise ValueError("mask selects no voxels — an empty domain has no "
                             "histogram to equalise against")
    else:
        sample = v.ravel()
    # histogram over the *full* volume range so the LUT covers every voxel,
    # even when the mask spans a narrower intensity band
    hist, _ = np.histogram(sample, bins=nb, range=(vmin, vmax))
    cdf = np.cumsum(hist, dtype=np.float64)
    lut = cdf / cdf[-1]                               # monotone, ends at 1.0
    idx = ((v - vmin) / (vmax - vmin) * nb).astype(np.int64)
    np.clip(idx, 0, nb - 1, out=idx)                  # vmax lands in the last bin
    return lut[idx]


# --------------------------------------------------------------------------- #
# vol_gamma                                                                    #
# --------------------------------------------------------------------------- #
def vol_gamma(vol, gamma):
    """Gamma (power-law) correction on the volume's own range (HALCON ``pow_image``).

    Normalises ``[min, max]`` to ``[0, 1]``, applies ``t**gamma``, and maps the
    result back to the original ``[min, max]`` — so the volume's extremes are
    fixed points and only the mid-tones move: ``gamma > 1`` darkens them,
    ``gamma < 1`` brightens them, ``gamma == 1`` is the identity. The transform
    is strictly monotone, so intensity *ordering* is always preserved.

    A **constant volume is returned unchanged** (no range to normalise —
    see the module docstring's flat-volume note).

    Parameters
    ----------
    vol : array_like, shape (D, H, W)
        Input volume (coerced to float64; NaN/Inf rejected).
    gamma : float
        Exponent, ``> 0`` (fail-closed: ``gamma <= 0`` is not a monotone
        intensity map).

    Returns
    -------
    ndarray, shape (D, H, W), float64
        The gamma-corrected volume, same ``[min, max]`` range as the input.

    Raises
    ------
    ValueError
        Non-3-D / non-finite input, or ``gamma <= 0``.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_gamma", "MAX_VOXELS")
    g = _finite_scalar(gamma, "gamma")
    if g <= 0.0:
        raise ValueError("gamma must be > 0 (a non-positive exponent is not a "
                         "monotone intensity map), got %r" % (gamma,))
    vmin = float(v.min())
    vmax = float(v.max())
    if vmax <= vmin:
        return v.copy()                               # constant: pass through
    t = (v - vmin) / (vmax - vmin)
    return vmin + np.power(t, g) * (vmax - vmin)


# --------------------------------------------------------------------------- #
# vol_stretch                                                                  #
# --------------------------------------------------------------------------- #
def vol_stretch(vol, p_low=1.0, p_high=99.0):
    """Percentile contrast stretch to ``[0, 1]`` (robust ``scale_image_max``).

    Computes the *p_low*-th and *p_high*-th intensity percentiles and maps
    ``[P(p_low), P(p_high)]`` linearly onto ``[0, 1]``, clipping outside — so a
    handful of hot/cold outlier voxels (a metal artefact, a dead detector
    element) no longer dictates the display range, unlike a plain min/max
    normalisation. The defaults (1 % / 99 %) are the usual display-stretch
    choice.

    If the two percentile values coincide (a constant — or near-constant —
    volume), the input is **returned unchanged** rather than divided by zero
    (see the module docstring's flat-volume note).

    Parameters
    ----------
    vol : array_like, shape (D, H, W)
        Input volume (coerced to float64; NaN/Inf rejected).
    p_low, p_high : float
        Percentiles in ``[0, 100]`` with ``p_low < p_high`` (fail-closed).

    Returns
    -------
    ndarray, shape (D, H, W), float64
        The stretched volume in ``[0, 1]`` (degenerate percentiles: the input
        itself).

    Raises
    ------
    ValueError
        Non-3-D / non-finite input, percentiles out of ``[0, 100]``, or
        ``p_low >= p_high``.
    """
    v = _require_volume(vol)
    _check_voxels(v, MAX_VOXELS, "vol_stretch", "MAX_VOXELS")
    pl = _finite_scalar(p_low, "p_low")
    ph = _finite_scalar(p_high, "p_high")
    if not (0.0 <= pl <= 100.0) or not (0.0 <= ph <= 100.0):
        raise ValueError("percentiles must lie in [0, 100], got p_low=%r p_high=%r"
                         % (p_low, p_high))
    if pl >= ph:
        raise ValueError("p_low must be < p_high, got p_low=%r p_high=%r"
                         % (p_low, p_high))
    lo, hi = np.percentile(v, [pl, ph])
    lo = float(lo)
    hi = float(hi)
    if hi <= lo:
        return v.copy()                               # degenerate: pass through
    out = (v - lo) / (hi - lo)
    np.clip(out, 0.0, 1.0, out=out)
    return out
